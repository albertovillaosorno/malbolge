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
//   - Normalized JSON to typed wire and real two-step guest VM regressions.
// - Must-Not:
//   - Substitute host output or assume arbitrary C compilation is supported.
// - Allows:
//   - Inputs: synthetic exact Clang JSON nodes for one C void return.
//   - Outputs: admission/refusal and guest execution evidence.
//   - Side effects: isolated test execution only.
// - Split-When:
//   - Another frontend semantic family needs independent evidence.
// - Merge-When:
//   - Actual Clang generated void-return fixtures replace these boundaries.
// - Summary:
//   - Proves source-shaped JSON can reach canonical MCTI and guest VM.
// - Description:
//   - Refuses dropped/duplicated node meaning and source/profile drift.
// - Usage:
//   - `cargo test -p malbolge-c-frontend-json-adapter --test normalized_void`.
// - Defaults:
//   - The native pinned Clang binary is not needed by this test.
//

//! Real-VM and canonical-IR evidence for the normalized void JSON adapter.

#[path = "../../typed-echo-adapter/composition/lib.rs"]
pub mod adapter;

use adapter::compile_canonical_typed_empty_void;
use malbolge::{ProfileMachine, RunOutcome, target_profile};
use malbolge_c_frontend_json_adapter::{
    FrontendJsonError, canonical_void_typed_ir, decode_void_frontend_json, typed,
};
use serde as _;
use serde_json::{Value, json};

fn input() -> Value {
    json!({
        "schema_version": 1,
        "artifact_id": "malbolge-c-frontend-v1",
        "clang": {"version":"22.1.8", "target":"wasm32-unknown-unknown", "language":"c23"},
        "profile": {"abi_id":"malbolge-c32-v1", "target_profile":"malbolge-2026"},
        "source": {"id":"fixtures/void-return.c", "sha256":
            "d374bb94b03d6902deb8b5cb25cf2913d63e215d1a3ead8f758b4a514c24c584"},
        "nodes": [
            {"id":1, "parent":0, "kind":"function-declaration",
             "span": span(0,27), "name":"noop", "type":"fn()->void",
             "definition":"definition", "inline_specified":false,
             "linkage":"external", "storage_class":"none"},
            {"id":2, "parent":1, "kind":"compound-statement", "span":span(16,27)},
            {"id":3, "parent":2, "kind":"return-statement", "span":span(18,25)}
        ]
    })
}

fn span(begin: u32, end: u32) -> Value {
    json!({"begin":{"byte":begin,"line":1,"column":begin.saturating_add(1)},
           "end":{"byte":end,"line":1,"column":end.saturating_add(1)}})
}

#[expect(
    clippy::expect_used,
    reason = "test-only JSON Value serialization is infallible"
)]
fn bytes(source: &Value) -> Vec<u8> {
    serde_json::to_vec(source).expect("test JSON serializes")
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real guest and source assertions"
)]
fn normalized_clang_void_json_reaches_canonical_typed_ir_and_real_guest() -> Result<(), String> {
    let input = input();
    let projection = decode_void_frontend_json(&bytes(&input))
        .map_err(|error| format!("normalized JSON projection: {error:?}"))?;
    assert_eq!(projection.source_id(), "fixtures/void-return.c");
    let typed_wire = canonical_void_typed_ir(&bytes(&input))
        .map_err(|error| format!("canonical MCTI: {error:?}"))?;
    let decoded = typed::canonical_module(&typed_wire)
        .map_err(|error| format!("decode canonical MCTI: {error:?}"))?;
    assert_eq!(decoded.source_sha256(), projection.source_sha256());
    assert_eq!(
        decoded.functions().first().map(typed::Function::name),
        Some("noop")
    );
    let profile = target_profile("malbolge-2026").ok_or("missing current target profile")?;
    let compiled = compile_canonical_typed_empty_void(&typed_wire, profile)
        .map_err(|error| format!("compile canonical MCTI to VM: {error:?}"))?;
    let mut vm = ProfileMachine::from_source(profile, compiled.layout().source(), Vec::new())
        .map_err(|error| format!("load emitted guest: {error:?}"))?;
    assert!(matches!(
        vm.run(2),
        Ok(RunOutcome::Terminated { steps: 2, .. })
    ));
    assert!(vm.output().is_empty());
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::shadow_unrelated,
    clippy::default_numeric_fallback,
    clippy::expect_used,
    clippy::too_many_lines,
    reason = "adversarial test JSON mutations target fixed fixture node paths"
)]
fn normalized_clang_json_rejects_effects_schema_drift_and_duplicate_fields() {
    let base = input();
    let mut cases = Vec::new();
    let mut changed = base.clone();
    changed["nodes"][1]["kind"] = json!("call-expression");
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][2]["parent"] = json!(1);
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][0]["type"] = json!("fn()->i32");
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][0]["inline_specified"] = json!(true);
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][0]["id"] = json!(12);
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][1]["id"] = json!(12);
    cases.push(changed);
    let mut changed = base.clone();
    changed["source"]["sha256"] =
        json!("AB74bb94b03d6902deb8b5cb25cf2913d63e215d1a3ead8f758b4a514c24c584");
    cases.push(changed);
    let mut changed = base.clone();
    changed["source"]["sha256"] =
        json!("zz74bb94b03d6902deb8b5cb25cf2913d63e215d1a3ead8f758b4a514c24c584");
    cases.push(changed);
    let mut changed = base.clone();
    changed["source"]["id"] = json!("../outside.c");
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][2]["type"] = json!("void");
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][2]["span"]["end"]["byte"] = json!(29);
    cases.push(changed);
    let mut changed = base.clone();
    changed["profile"]["target_profile"] = json!("malbolge-1998");
    cases.push(changed);
    let mut changed = base.clone();
    changed["clang"]["version"] = json!("23.1.2");
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][0]["extra"] = json!("ignored-by-wrong-parser");
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"]
        .as_array_mut()
        .expect("nodes are array")
        .push(json!({
            "id":4, "parent":2, "kind":"call-expression", "span":span(18,25)
        }));
    cases.push(changed);
    for (index, candidate) in cases.iter().enumerate() {
        assert!(
            canonical_void_typed_ir(&bytes(candidate)).is_err(),
            "forged case {index}"
        );
    }
    let raw = bytes(&base);
    let original = String::from_utf8(raw).expect("compact JSON is UTF-8");
    let duplicated = original.replacen(
        "\"schema_version\":1",
        "\"schema_version\":1,\"schema_version\":1",
        1,
    );
    assert_ne!(duplicated, original);
    assert_eq!(
        canonical_void_typed_ir(duplicated.as_bytes()),
        Err(FrontendJsonError::Malformed)
    );
    assert_eq!(
        canonical_void_typed_ir(&vec![b' '; 1_048_577]),
        Err(FrontendJsonError::Malformed)
    );
}
