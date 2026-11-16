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
//   - Nested guard-domain preservation across source-authenticated C arms.
// - Must-Not:
//   - Assume that an inactive expression preserves an unknown guest byte.
// - Allows:
//   - Inputs: original C23 source and pinned Clang normalized JSON.
//   - Outputs: four source-bound guest input/output effects or refusal.
//   - Side effects: none.
// - Split-When:
//   - Dynamic guest arithmetic and branch lowering are implemented.
// - Merge-When:
//   - Nested guard proof shares complete domain constraints with siblings.
// - Summary:
//   - Prove all 256 C paths, reject a changed reachable byte.

use super::super::typed::{Instruction, canonical_module};
use super::super::{
    FrontendGuestMode, FrontendJsonError, canonical_guest_typed_ir_with_source,
};

const SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_nested_guarded_live_input.c");
const JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_nested_guarded_live_input.json");

#[test]
fn nested_guards_prove_live_byte_identity_on_every_reachable_path() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(JSON, Some(SOURCE))
        .expect(
            "nested source-authenticated C domains preserve the guest byte",
        );
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let module = canonical_module(&wire).expect("canonical typed bytes");
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in module.functions()[0].blocks()[0].instructions() {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected instruction: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 4);
    assert_eq!(writes, reads);
}

#[test]
fn nested_guards_refuse_reachable_source_and_clang_mismatches() {
    let mut changed = SOURCE.to_vec();
    let needle = b"current - (current & 3) + 3";
    let at = changed
        .windows(needle.len())
        .position(|part| part == needle)
        .expect("source arithmetic in the true inner arm");
    changed[at + needle.len() - 1] = b'2';
    assert!(matches!(
        canonical_guest_typed_ir_with_source(JSON, Some(&changed)),
        Err(FrontendJsonError::Unsupported)
    ));
    let mut parsed: serde_json::Value = serde_json::from_slice(JSON).unwrap();
    let operation = parsed["nodes"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|node| {
            node["kind"] == "binary-expression"
                && node["operation"] == "-"
                && node["span"]["begin"]["line"] == 34
        })
        .expect("nested inner arithmetic subtraction");
    operation["operation"] = serde_json::json!("+");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            &serde_json::to_vec(&parsed).unwrap(),
            Some(SOURCE)
        ),
        Err(FrontendJsonError::Unsupported)
    ));
}
