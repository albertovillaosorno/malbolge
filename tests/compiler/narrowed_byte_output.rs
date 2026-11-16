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
//   - Exact C unsigned-byte conversion with guarded live input.
// - Must-Not:
//   - Infer guest values or admit source/Clang cast disagreement.
// - Allows:
//   - Inputs: original source and pinned normalized Clang JSON.
//   - Outputs: authenticated byte-preserving typed I/O effects.
//   - Side effects: none.
// - Split-When:
//   - Executable integer conversion subsumes this static equality proof.
// - Merge-When:
//   - All pure byte-domain output proofs share one regression harness.
// - Summary:
//   - Preserve four dynamic guest bytes across plus/minus 256 and u8 cast.

use super::super::typed::{Instruction, canonical_module};
use super::super::{
    FrontendGuestMode, FrontendJsonError, canonical_guest_typed_ir_with_source,
};

const SOURCE: &[u8] = include_bytes!(
    "c-frontend/accepted/unsigned_narrowed_guarded_live_input.c"
);
const JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_narrowed_guarded_live_input.json"
);

#[test]
fn signed_offsets_narrow_to_same_live_guest_byte() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(JSON, Some(SOURCE))
        .expect("proven C u8 conversion preserves every live guest byte");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let module = canonical_module(&wire).expect("canonical typed module");
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
    assert_eq!(writes, reads);
}

#[test]
fn narrowing_requires_source_and_clang_and_exact_identity() {
    let mut changed = SOURCE.to_vec();
    let old = b"current - 256";
    let at = changed
        .windows(old.len())
        .position(|part| part == old)
        .unwrap();
    changed[at + 10] = b'5';
    assert!(matches!(
        canonical_guest_typed_ir_with_source(JSON, Some(&changed)),
        Err(FrontendJsonError::Unsupported)
    ));
    let mut parsed: serde_json::Value = serde_json::from_slice(JSON).unwrap();
    let conversion = parsed["nodes"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|node| node["kind"] == "cast-expression" && node["type"] == "u8")
        .expect("source-bound u8 narrowing");
    conversion["type"] = serde_json::json!("i8");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            &serde_json::to_vec(&parsed).unwrap(),
            Some(SOURCE)
        ),
        Err(FrontendJsonError::Unsupported)
    ));
}
