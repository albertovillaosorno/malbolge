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
//   - Source-proven, path-sensitive guest byte identity tests.
// - Must-Not:
//   - Accept arithmetic merely because it matches a sampled stdin vector.
// - Allows:
//   - Inputs: original C23 source and normalized pinned-Clang AST.
//   - Outputs: four live byte input/output effects or explicit refusal.
//   - Side effects: none.
// - Split-When:
//   - General runtime C branch lowering takes ownership of these cases.
// - Merge-When:
//   - Input-domain C arithmetic is uniformly proved by the source adapter.
// - Summary:
//   - Conditional output identity follows the authenticated guard truth set.

use super::super::typed::{Instruction, canonical_module};
use super::super::{
    FrontendGuestMode, FrontendJsonError, canonical_guest_typed_ir_with_source,
};

const SOURCE: &[u8] = include_bytes!(
    "c-frontend/accepted/unsigned_guarded_modular_output_live_input.c"
);
const JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_guarded_modular_output_live_input.json"
);

#[test]
fn conditional_modular_output_preserves_four_distinct_guest_inputs() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(JSON, Some(SOURCE))
        .expect("guarded signed C arithmetic must retain the real input byte");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let module = canonical_module(&wire).expect("canonical typed bytes");
    let effects = module.functions()[0].blocks()[0].instructions();
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in effects {
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
fn conditional_modular_output_refuses_changed_source_and_ast() {
    let mut changed = SOURCE.to_vec();
    let needle = b"current + (current & 1)";
    let at = changed
        .windows(needle.len())
        .position(|part| part == needle)
        .unwrap();
    changed[at + 8] = b"-"[0];
    assert!(matches!(
        canonical_guest_typed_ir_with_source(JSON, Some(&changed)),
        Err(FrontendJsonError::Unsupported)
    ));
    let mut value: serde_json::Value = serde_json::from_slice(JSON).unwrap();
    let nodes = value["nodes"].as_array_mut().unwrap();
    let operation = nodes
        .iter_mut()
        .find(|node| {
            node["kind"] == "binary-expression"
                && node["operation"] == "+"
                && node["span"]["begin"]["line"] == 34
        })
        .expect("second source arm");
    operation["operation"] = serde_json::json!("-");
    let altered = serde_json::to_vec(&value).unwrap();
    assert!(matches!(
        canonical_guest_typed_ir_with_source(&altered, Some(SOURCE)),
        Err(FrontendJsonError::Unsupported)
    ));
}
