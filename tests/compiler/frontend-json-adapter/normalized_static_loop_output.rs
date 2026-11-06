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
//   - Pinned Clang bounded-loop state and AST rejection regression.
// - Must-Not:
//   - Assert dynamic guest loops from folded output or trust mutated ASTs.
// - Allows:
//   - Inputs: source-bound loop AST and controlled JSON mutations.
//   - Outputs: one proven typed byte or typed refusal.
//   - Side effects: none.
// - Split-When:
//   - Guest runtime loop lowering owns source and guest parity.
// - Merge-When:
//   - General loop compilation and verification supersede this projection.
// - Summary:
//   - Exercise lexical local lifetime and loop state carried across iterations.
// - Description:
//   - Reject altered counter, iteration guard, branch and output effects.
// - Usage:
//   - cargo test -p malbolge-c-frontend-json-adapter --test
//     normalized_static_loop_output
// - Defaults:
//   - Source JSON is pinned to the Clang frontend, not inferred from text.

//! Verify a source-proven bounded unsigned C loop through typed byte output.

use malbolge as _;
use malbolge_c_frontend_json_adapter::{
    FrontendGuestMode, FrontendJsonError, canonical_guest_typed_ir, typed,
};
use serde as _;
use serde_json::{Value, json};

const LOOP: &[u8] =
    include_bytes!("../c-frontend/golden/local_static_loop_output.json");

#[test]
fn bounded_loop_yields_one_source_proven_guest_byte() {
    let (wire, mode) = canonical_guest_typed_ir(LOOP).unwrap();
    assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
    let module = typed::canonical_module(&wire).unwrap();
    assert_eq!(module.source_id(), "tests/local-static-loop-output-v1");
    let [constant, output] = module.functions()[0].blocks()[0].instructions()
    else {
        panic!("expected one folded byte and real guest output");
    };
    assert!(matches!(
        constant.instruction(),
        typed::Instruction::ConstantInteger { constant, .. }
            if constant.bit_width() == 8 && constant.little_endian() == [65]
    ));
    assert_eq!(constant.span().begin().line(), 47);
    assert!(matches!(
        output.instruction(),
        typed::Instruction::ByteOutput { value } if value.value() == 0
    ));
    assert_eq!(typed::canonical_bytes(&module), Ok(wire));
}

#[test]
#[expect(
    clippy::indexing_slicing,
    reason = "fixed pinned-Clang AST indices"
)]
fn changed_loop_counter_control_and_effects_reject() {
    let original: Value = serde_json::from_slice(LOOP).unwrap();
    for (index, key, value) in [
        (8, "kind", json!("while-statement")),
        (12, "operation", json!("<=")),
        (14, "reference", json!("b@72")),
        (15, "constant_integer", json!("13")),
        (16, "operation", json!("--")),
        (17, "reference", json!("a@51")),
        (18, "kind", json!("call-expression")),
        (20, "reference", json!("a@51")),
        (30, "operation", json!("!=")),
        (51, "operation", json!("+=")),
        (55, "operation", json!("*")),
    ] {
        let mut changed = original.clone();
        changed["nodes"][index][key] = value;
        let bytes = serde_json::to_vec(&changed).unwrap();
        assert_eq!(
            canonical_guest_typed_ir(&bytes),
            Err(FrontendJsonError::Unsupported),
            "mutated loop node {} field {key} was admitted",
            index + 1
        );
    }
    let mut extra = original;
    // An extra output inside the loop cannot be dropped as a dead effect.
    let span = extra["nodes"][51]["span"].clone();
    extra["nodes"].as_array_mut().unwrap().insert(
        52,
        json!({"id":53,"parent":19,"kind":"call-expression",
               "span":span,"type":"i32",
               "reference":"external:putchar"}),
    );
    // Missing contiguous IDs are also a closed-parse refusal.
    assert!(matches!(
        canonical_guest_typed_ir(&serde_json::to_vec(&extra).unwrap()),
        Err(FrontendJsonError::Unsupported)
    ));
}
