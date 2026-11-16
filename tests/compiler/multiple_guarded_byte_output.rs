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
//   - Source-bound ordered guarded byte writes across two C branch arms.
// - Must-Not:
//   - Suppress guest I/O effects or accept changed-byte C outputs.
// - Allows:
//   - Inputs: pinned Clang JSON and exact C23 source bytes.
//   - Outputs: four real reads followed by two matching writes per read.
//   - Side effects: none.
// - Split-When:
//   - General executable C control flow supersedes static arm equality.
// - Merge-When:
//   - All source-level byte-effect proof tests share one harness.
// - Summary:
//   - Authenticate two byte identities per reachable C arm.

use super::super::typed::{Instruction, canonical_module};
use super::super::{
    FrontendGuestMode, FrontendJsonError, canonical_guest_typed_ir_with_source,
};

const SOURCE: &[u8] = include_bytes!(
    "c-frontend/accepted/unsigned_multiple_guarded_live_input.c"
);
const JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_multiple_guarded_live_input.json"
);

#[test]
fn two_guarded_outputs_preserve_each_real_input_byte() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(JSON, Some(SOURCE))
        .expect("two source-authenticated writes per live input");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let module = canonical_module(&wire).expect("canonical typed artifact");
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for instruction in module.functions()[0].blocks()[0].instructions() {
        match instruction.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected guest instruction: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 4);
    assert_eq!(writes.len(), 8);
    assert_eq!(
        writes,
        reads
            .iter()
            .flat_map(|value| [*value; 2])
            .collect::<Vec<_>>()
    );
}

#[test]
fn two_guarded_outputs_reject_modified_source_and_clang() {
    let mut changed = SOURCE.to_vec();
    let old = b"current & -2";
    let at = changed
        .windows(old.len())
        .position(|part| part == old)
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
        .expect("guarded OR operator");
    operator["operation"] = serde_json::json!("^");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            &serde_json::to_vec(&parsed).unwrap(),
            Some(SOURCE)
        ),
        Err(FrontendJsonError::Unsupported)
    ));
}
