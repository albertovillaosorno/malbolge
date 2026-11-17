// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Unbraced source-authenticated byte-guard identity regression.
// - Must-Not:
//   - Assume both C output arms preserve arbitrary bytes globally.
// - Allows:
//   - Inputs: original C23 source and normalized pinned-Clang JSON.
//   - Outputs: four guest byte inputs and four corresponding outputs.
//   - Side effects: none.
// - Split-When:
//   - Runtime guest C conditionals replace source proof.
// - Merge-When:
//   - Unbraced and compound statement evidence share one regression matrix.
// - Summary:
//   - Prove odd/even output identities only where each C arm executes.

use super::super::{FrontendJsonError, canonical_guest_typed_ir_with_source};

const SOURCE: &[u8] = include_bytes!(
    "c-frontend/accepted/unsigned_unbraced_guarded_live_input.c"
);
const JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_unbraced_guarded_live_input.json"
);
const MULTILINE_SOURCE: &[u8] = include_bytes!(
    "c-frontend/accepted/unsigned_multiline_guarded_live_input.c"
);
const MULTILINE_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_multiline_guarded_live_input.json"
);

#[test]
fn unbraced_guarded_calls_emit_one_resident_byte_per_read() {
    for (source, json) in [(SOURCE, JSON), (MULTILINE_SOURCE, MULTILINE_JSON)] {
        assert!(matches!(
            canonical_guest_typed_ir_with_source(json, Some(source)),
            Err(FrontendJsonError::Unsupported)
        ));
    }
}

#[test]
fn unbraced_guarded_calls_reject_forged_source_and_clang() {
    let mut changed = SOURCE.to_vec();
    let old = b"current | 1";
    let at = changed
        .windows(old.len())
        .position(|part| part == old)
        .unwrap();
    changed[at + 8] = b'^';
    assert!(matches!(
        canonical_guest_typed_ir_with_source(JSON, Some(&changed)),
        Err(FrontendJsonError::Unsupported)
    ));
    let mut parsed: serde_json::Value = serde_json::from_slice(JSON).unwrap();
    let operator = parsed["nodes"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|node| {
            node["kind"] == "binary-expression" && node["operation"] == "|"
        })
        .expect("the true arm's bitwise OR");
    operator["operation"] = serde_json::json!("^");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            &serde_json::to_vec(&parsed).unwrap(),
            Some(SOURCE)
        ),
        Err(FrontendJsonError::Unsupported)
    ));
}
