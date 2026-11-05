// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Versioned Clang storage-duration metadata admission and refusal.
// - Must-Not:
//   - Discard local declarations or claim unsupported C state is lowered.
// - Allows:
//   - Inputs: closed normalized Clang JSON with declaration metadata.
//   - Outputs: typed refusal and accurate construct attribution.
//   - Side effects: none.
// - Split-When:
//   - Stateful guest C lowering has a production lowering path.
// - Merge-When:
//   - Full C pipeline diagnostics replace the closed-adapter smoke tests.
// - Summary:
//   - Valid Clang automatic storage is not malformed JSON or executable IR.
// - Description:
//   - Preserve both exact schema and explicit unsupported-semantic boundaries.
// - Usage:
//   - cargo test -p malbolge-c-frontend-json-adapter --test
//     normalized_storage_duration
// - Defaults:
//   - No host-side execution or guessed guest output.

//! Distinguish valid Clang local-state metadata from unsupported lowering.

use malbolge as _;
use malbolge_c_frontend_json_adapter::{
    FrontendJsonError, UnloweredCNode, canonical_guest_typed_ir,
    canonical_void_typed_ir, first_unlowered_c_node,
};
use serde as _;
use serde_json::{Value, json};

fn span(begin: u32, end: u32) -> Value {
    json!({"begin":{"byte":begin,"line":4,"column":begin + 1},
           "end":{"byte":end,"line":4,"column":end + 1}})
}

fn source() -> Value {
    json!({
        "schema_version":1,"artifact_id":"malbolge-c-frontend-v1",
        "clang":{"version":"22.1.8","target":"wasm32-unknown-unknown",
                 "language":"c23"},
        "profile":{"abi_id":"malbolge-c32-v1","target_profile":"malbolge-2026"},
        "source":{"id":"fixtures/local-state.c","sha256":
            "d374bb94b03d6902deb8b5cb25cf2913d63e215d1a3ead8f758b4a514c24c584"},
        "nodes":[
            {"id":1,"parent":0,"kind":"function-declaration",
             "span":span(0,65),"name":"emit","type":"fn()->void",
             "definition":"definition","inline_specified":false,
             "linkage":"external","storage_class":"none"},
            {"id":2,"parent":1,"kind":"compound-statement","span":span(16,65)},
            {"id":3,"parent":2,"kind":"declaration-statement",
             "span":span(19,34)},
            {"id":4,"parent":3,"kind":"variable-declaration",
             "span":span(19,33),"name":"value","type":"u32",
             "definition":"definition","linkage":"none",
             "storage_class":"none","storage_duration":"automatic"},
            {"id":5,"parent":4,"kind":"integer-literal","span":span(32,33),
             "type":"u32","constant_integer":"1","literal":"1"}
        ]
    })
}

#[expect(
    clippy::expect_used,
    reason = "fixed synthetic JSON fixture serializes"
)]
fn encode(value: &Value) -> Vec<u8> {
    serde_json::to_vec(value).expect("fixture JSON")
}

#[test]
#[expect(
    clippy::indexing_slicing,
    reason = "fixed synthetic JSON node indices"
)]
fn automatic_local_state_is_supported_schema_but_unsupported_semantics() {
    let input = source();
    assert_eq!(
        first_unlowered_c_node(&encode(&input)),
        Some(UnloweredCNode {
            kind: String::from("declaration-statement"),
            id: 3,
            line: 4,
            column: 20,
        })
    );
    assert_eq!(
        canonical_guest_typed_ir(&encode(&input)),
        Err(FrontendJsonError::Unsupported)
    );
    for duration in ["static", "thread"] {
        let mut other = input.clone();
        other["nodes"][3]["storage_duration"] = json!(duration);
        assert_eq!(
            canonical_guest_typed_ir(&encode(&other)),
            Err(FrontendJsonError::Unsupported)
        );
    }
}

#[test]
#[expect(
    clippy::indexing_slicing,
    reason = "explicit forged Clang metadata tests"
)]
fn known_metadata_on_effect_free_nodes_is_not_silently_discarded() {
    let mut without_state = source();
    without_state["nodes"]
        .as_array_mut()
        .expect("nodes array")
        .truncate(2);
    for node in [0, 1] {
        for duration in ["automatic", "static", "thread"] {
            let mut forged = without_state.clone();
            forged["nodes"][node]["storage_duration"] = json!(duration);
            assert_eq!(
                canonical_void_typed_ir(&encode(&forged)),
                Err(FrontendJsonError::Unsupported)
            );
        }
    }
    let mut unknown = source();
    unknown["nodes"][3]["storage_duration"] = json!("imaginary");
    assert_eq!(
        canonical_guest_typed_ir(&encode(&unknown)),
        Err(FrontendJsonError::Malformed)
    );
    assert_eq!(first_unlowered_c_node(&encode(&unknown)), None);
    let mut unknown_field = source();
    unknown_field["nodes"][3]["storage_duration_extra"] = json!("automatic");
    assert_eq!(
        canonical_guest_typed_ir(&encode(&unknown_field)),
        Err(FrontendJsonError::Malformed)
    );
    assert_eq!(first_unlowered_c_node(&encode(&unknown_field)), None);
}
