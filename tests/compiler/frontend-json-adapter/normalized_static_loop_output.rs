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
const LOOP_OUTPUT: &[u8] =
    include_bytes!("../c-frontend/golden/local_loop_branch_output.json");
const LOOP_DISTINCT: &[u8] =
    include_bytes!("../c-frontend/golden/local_loop_distinct_output.json");
const SHIFT_RECURRENCE: &[u8] =
    include_bytes!("../c-frontend/golden/local_shift_recurrence_output.json");

const UNBRACED_WHILE_FIBONACCI: &[u8] =
    include_bytes!("../c-frontend/golden/local_unbraced_while_fibonacci.json");

#[test]
fn unbraced_while_updates_local_parity_before_twelve_selected_effects() {
    let (wire, mode) =
        canonical_guest_typed_ir(UNBRACED_WHILE_FIBONACCI).unwrap();
    assert_eq!(mode, FrontendGuestMode::DistinctLiteralTwelve);
    let module = typed::canonical_module(&wire).unwrap();
    assert_eq!(module.source_id(), "tests/unbraced-while-fibonacci-v1");
    let effects = module.functions()[0].blocks()[0].instructions();
    assert_eq!(effects.len(), 24);
    let expected = [
        0x02, 0x19, 0x1f, 0x08, 0x17, 0x0f, 0x02, 0x0d, 0x03, 0x10, 0x13, 0x03,
    ];
    for (index, (pair, expected_byte)) in
        effects.chunks_exact(2).zip(expected).enumerate()
    {
        let [constant, output] = pair else {
            panic!("expected one source-bound byte and output per iteration");
        };
        assert!(matches!(
            constant.instruction(),
            typed::Instruction::ConstantInteger {
                constant, result, ..
            } if constant.bit_width() == 8
                && constant.little_endian() == [expected_byte]
                && usize::try_from(result.value()) == Ok(index)
        ));
        assert!(matches!(
            output.instruction(),
            typed::Instruction::ByteOutput { value }
                if usize::try_from(value.value()) == Ok(index)
        ));
    }
    assert_eq!(typed::canonical_bytes(&module), Ok(wire));
}

#[test]
fn unbraced_while_rejects_forged_source_steps() {
    let original: Value =
        serde_json::from_slice(UNBRACED_WHILE_FIBONACCI).unwrap();
    for (id, key, replacement) in [
        (42, "parent", json!(19)),
        (43, "reference", json!("foreign@0")),
        (33, "kind", json!("do-statement")),
    ] {
        let mut altered = original.clone();
        altered["nodes"][id - 1][key] = replacement;
        assert!(
            matches!(
                canonical_guest_typed_ir(
                    &serde_json::to_vec(&altered).unwrap()
                ),
                Err(FrontendJsonError::Unsupported)
            ),
            "unbraced while accepted forged node {id} field {key}"
        );
    }
}

#[test]
fn selected_loop_output_calls_preserve_twelve_real_effects() {
    let (wire, mode) = canonical_guest_typed_ir(LOOP_OUTPUT).unwrap();
    assert_eq!(mode, FrontendGuestMode::InitialZeroOutput);
    let module = typed::canonical_module(&wire).unwrap();
    assert_eq!(module.source_id(), "tests/local-loop-branch-output-v1");
    let instructions = module.functions()[0].blocks()[0].instructions();
    assert_eq!(instructions.len(), 13);
    assert!(matches!(
        instructions[0].instruction(),
        typed::Instruction::ConstantInteger { constant, .. }
            if constant.bit_width() == 8 && constant.little_endian() == [0]
    ));
    // Independently computed next values: 2, 3, 5, 8, 13, 21,
    // 34, 55, 89, 144, 233, 121. Only four select the even arm.
    let lines: Vec<_> = instructions[1..]
        .iter()
        .map(|instruction| {
            assert!(matches!(
                instruction.instruction(),
                typed::Instruction::ByteOutput { value } if value.value() == 0
            ));
            instruction.span().begin().line()
        })
        .collect();
    assert_eq!(lines, [40, 42, 42, 40, 42, 42, 40, 42, 42, 40, 42, 42]);
    assert_eq!(typed::canonical_bytes(&module), Ok(wire));
}

#[test]
fn different_source_derived_loop_outputs_keep_distinct_ssa_and_spans() {
    let (wire, mode) = canonical_guest_typed_ir(LOOP_DISTINCT).unwrap();
    assert_eq!(mode, FrontendGuestMode::DistinctLiteralPair);
    let module = typed::canonical_module(&wire).unwrap();
    assert_eq!(module.source_id(), "tests/local-loop-distinct-output-v1");
    let instructions = module.functions()[0].blocks()[0].instructions();
    assert_eq!(instructions.len(), 4);
    for (index, (pair, (expected_byte, expected_line))) in instructions
        .chunks_exact(2)
        .zip([(81, 40), (46, 42)])
        .enumerate()
    {
        let [constant, output] = pair else {
            panic!(
                "expected one independent constant and putchar per iteration"
            );
        };
        assert!(matches!(
            constant.instruction(),
            typed::Instruction::ConstantInteger { constant, result, .. }
                if constant.bit_width() == 8
                    && constant.little_endian() == [expected_byte]
                    && usize::try_from(result.value()) == Ok(index)
        ));
        assert!(matches!(
            output.instruction(),
            typed::Instruction::ByteOutput { value }
                if usize::try_from(value.value()) == Ok(index)
        ));
        assert_eq!(constant.span().begin().line(), expected_line);
        assert_eq!(output.span().begin().line(), expected_line);
    }
    assert_eq!(typed::canonical_bytes(&module), Ok(wire));
}

#[test]
fn equal_branch_values_still_keep_two_source_bound_ssa_effects() {
    // Two same-width C literal substitutions retain pinned Clang ancestry.
    // The independent C pipeline also rechecks actual source SHA and VM parity.
    let mut modified: Value = serde_json::from_slice(LOOP_DISTINCT).unwrap();
    for (id, value) in [(47usize, "58"), (57, "59")] {
        let node = &mut modified["nodes"][id - 1];
        node["literal"] = json!(value);
        node["constant_integer"] = json!(value);
    }
    let (wire, mode) =
        canonical_guest_typed_ir(&serde_json::to_vec(&modified).unwrap())
            .unwrap();
    assert_eq!(mode, FrontendGuestMode::DistinctLiteralPair);
    let module = typed::canonical_module(&wire).unwrap();
    let instructions = module.functions()[0].blocks()[0].instructions();
    assert_eq!(instructions.len(), 4);
    for (index, pair) in instructions.chunks_exact(2).enumerate() {
        let [constant, output] = pair else {
            panic!("expected one independent SSA per branch-selected output");
        };
        assert!(matches!(
            constant.instruction(),
            typed::Instruction::ConstantInteger { constant, result, .. }
                if constant.bit_width() == 8
                    && constant.little_endian() == [0x38]
                    && usize::try_from(result.value()) == Ok(index)
        ));
        assert!(matches!(
            output.instruction(),
            typed::Instruction::ByteOutput { value }
                if usize::try_from(value.value()) == Ok(index)
        ));
        assert_eq!(constant.span().begin().line(), [40, 42][index]);
        assert_eq!(output.span().begin().line(), [40, 42][index]);
    }
    assert_eq!(typed::canonical_bytes(&module), Ok(wire));
}

#[test]
fn distinct_loop_output_must_prove_both_branches_and_all_symbols() {
    let original: Value = serde_json::from_slice(LOOP_DISTINCT).unwrap();
    for (id, key, replacement) in [
        (16, "constant_integer", json!("13")),
        (31, "operation", json!("&&")),
        (39, "reference", json!("external:puts")),
        (44, "operation", json!(">>")),
        (46, "reference", json!("b@1161")),
        (47, "literal", json!("84")),
        (49, "reference", json!("external:puts")),
        (54, "operation", json!(">>")),
        (56, "reference", json!("foreign@0")),
        (57, "literal", json!("46")),
    ] {
        let mut changed = original.clone();
        changed["nodes"][id - 1][key] = replacement;
        assert_eq!(
            canonical_guest_typed_ir(&serde_json::to_vec(&changed).unwrap()),
            Err(FrontendJsonError::Unsupported),
            "mutated loop node {id} field {key} was admitted"
        );
    }
}

#[test]
fn unsafe_or_nonzero_loop_effects_refuse_promotion() {
    let original: Value = serde_json::from_slice(LOOP_OUTPUT).unwrap();
    for (id, key, value) in [
        (31, "operation", json!("&&")),
        (39, "reference", json!("external:puts")),
        (44, "operation", json!(">>")),
        (50, "reference", json!("external:puts")),
        (55, "operation", json!("+")),
        (16, "constant_integer", json!("13")),
    ] {
        let mut changed = original.clone();
        changed["nodes"][id - 1][key] = value;
        assert_eq!(
            canonical_guest_typed_ir(&serde_json::to_vec(&changed).unwrap()),
            Err(FrontendJsonError::Unsupported),
            "unexpected admission for mutation at node {id}"
        );
    }
    let mut extra = original;
    // Both selected and unselected arms must be checked in full.
    extra["nodes"][49]["reference"] = json!("external:puts");
    assert_eq!(
        canonical_guest_typed_ir(&serde_json::to_vec(&extra).unwrap()),
        Err(FrontendJsonError::Unsupported)
    );
}

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
        (30, "operation", json!("&&")),
        (51, "operation", json!("+=")),
        (55, "operation", json!(">>")),
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

#[test]
fn unsigned_shift_recurrence_projects_checked_source_byte() {
    let (wire, mode) = canonical_guest_typed_ir(SHIFT_RECURRENCE).unwrap();
    assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
    let module = typed::canonical_module(&wire).unwrap();
    assert_eq!(module.source_id(), "tests/local-shift-recurrence-v1");
    let [constant, output] = module.functions()[0].blocks()[0].instructions()
    else {
        panic!("expected exactly one proven output after the recurrence");
    };
    assert!(matches!(
        constant.instruction(),
        typed::Instruction::ConstantInteger { constant, .. }
            if constant.bit_width() == 8 && constant.little_endian() == [65]
    ));
    assert_eq!(constant.span().begin().line(), 46);
    assert!(matches!(
        output.instruction(),
        typed::Instruction::ByteOutput { value } if value.value() == 0
    ));
    assert_eq!(typed::canonical_bytes(&module), Ok(wire));
}

#[test]
fn unsigned_shift_counts_and_ast_metadata_fail_closed() {
    let original: Value = serde_json::from_slice(SHIFT_RECURRENCE).unwrap();
    for (id, key, replacement) in [
        (24, "operation", json!("<<<")),
        (46, "operation", json!(">>>")),
        (24, "type", json!("i32")),
        (46, "type", json!("i32")),
        (31, "constant_integer", json!("32")),
        (49, "constant_integer", json!("32")),
        (28, "reference", json!("foreign@0")),
        (48, "parent", json!(44)),
    ] {
        let mut changed = original.clone();
        changed["nodes"][id - 1][key] = replacement;
        assert_eq!(
            canonical_guest_typed_ir(&serde_json::to_vec(&changed).unwrap()),
            Err(FrontendJsonError::Unsupported),
            "mutated shift node {id} field {key} was admitted"
        );
    }
    for id in [31usize, 49] {
        let mut changed = original.clone();
        changed["nodes"][id - 1]["constant_integer"] = json!("32");
        changed["nodes"][id - 1]["literal"] = json!("32");
        assert_eq!(
            canonical_guest_typed_ir(&serde_json::to_vec(&changed).unwrap()),
            Err(FrontendJsonError::Unsupported),
            "out-of-width unsigned shift count at node {id} was admitted"
        );
    }
}
