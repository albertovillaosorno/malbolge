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
//   - Multiline else-if C23 guard-domain identity admission regression.
// - Must-Not:
//   - Fold input-dependent outputs with unequal byte values.
// - Allows:
//   - Inputs: original C23 source and normalized pinned-Clang JSON.
//   - Outputs: four real guest reads and their four matching writes.
//   - Side effects: none.
// - Split-When:
//   - General executable guest branches replace path-domain equivalence.
// - Merge-When:
//   - Source branch statement forms share regression coverage.
// - Summary:
//   - Authenticate three byte-preserving low-bit C branch domains.

use super::super::{FrontendJsonError, canonical_guest_typed_ir_with_source};

const SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_else_if_guarded_live_input.c");
const JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_else_if_guarded_live_input.json"
);

#[test]
fn else_if_indented_guard_preserves_live_guest_byte() {
    // Successful-byte identities do not implement signed C23 EOF output.
    assert!(matches!(
        canonical_guest_typed_ir_with_source(JSON, Some(SOURCE)),
        Err(FrontendJsonError::Unsupported)
    ));
}

#[test]
fn else_if_guard_refuses_changed_c_and_forged_clang() {
    let mut changed = SOURCE.to_vec();
    let old = b"current & -4";
    let at = changed
        .windows(old.len())
        .position(|window| window == old)
        .unwrap();
    changed[at + 8] = b'|';
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
        .expect("guarded branch arithmetic exists");
    operator["operation"] = serde_json::json!("^");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            &serde_json::to_vec(&parsed).unwrap(),
            Some(SOURCE)
        ),
        Err(FrontendJsonError::Unsupported)
    ));

    // The inner `if` has a different begin column from the aligned
    // `else` and its calls. A forged coordinate must not bypass the
    // source-authenticated indentation and byte-domain proof.
    let mut parsed: serde_json::Value = serde_json::from_slice(JSON).unwrap();
    let inner_if = parsed["nodes"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .filter(|node| node["kind"] == "if-statement")
        .nth(1)
        .expect("the second low-bit condition");
    inner_if["span"]["begin"]["column"] = serde_json::json!(15);
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            &serde_json::to_vec(&parsed).unwrap(),
            Some(SOURCE)
        ),
        Err(FrontendJsonError::Unsupported)
    ));
}
