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
//   - Pinned unsigned C loop source-to-typed byte I/O admission evidence.
// - Must-Not:
//   - Trust an unsigned Clang integer annotation without original C bytes.
// - Allows:
//   - Inputs: pinned Clang JSON and same-source byte witnesses.
//   - Outputs: verified four-read/four-write typed trace or explicit refusal.
//   - Side effects: none.
// - Split-When:
//   - Generic source-C for-loop parser subsumes this regression.
// - Merge-When:
//   - Full guest C runtime state/control replaces finite source iteration.
// - Summary:
//   - Prove bounded unsigned iteration preserves live stdin provenance.

use super::super::typed::{Instruction, canonical_module};
use super::super::{
    FrontendGuestMode, FrontendJsonError, canonical_guest_typed_ir_with_source,
};

// Guest output count alone cannot prove the selected C induction effect trace.
// Decode independently validated typed bytes and require exactly four fresh
// reads and the five ordered writes of the third resident SSA value twice.
fn assert_four_reads_five_writes(wire: &[u8]) {
    let decoded = canonical_module(wire).expect("canonical typed wire");
    let block = decoded
        .functions()
        .first()
        .unwrap()
        .blocks()
        .first()
        .unwrap();
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in block.instructions() {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected guest effect: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 4);
    assert_eq!(writes, vec![
        reads[0], reads[1], reads[2], reads[2], reads[3]
    ]);
}

const JSON: &[u8] =
    include_bytes!("c-frontend/golden/input_unsigned_loop.json");
const SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/input_unsigned_loop.c");

#[test]
fn unsigned_loop_projects_four_runtime_input_output_pairs() {
    let (_typed, mode) =
        canonical_guest_typed_ir_with_source(JSON, Some(SOURCE)).expect(
            "pinned unsigned loop should preserve four runtime input effects",
        );
    assert_eq!(mode, FrontendGuestMode::LatestRead);
}

#[test]
fn unsigned_loop_refuses_modified_source_bound_and_counter_type() {
    let mut changed = SOURCE.to_vec();
    let at = changed.windows(2).position(|part| part == b"4U").unwrap();
    changed[at] = b'5';
    assert!(matches!(
        canonical_guest_typed_ir_with_source(JSON, Some(&changed)),
        Err(FrontendJsonError::Unsupported)
    ));
    let mut changed = SOURCE.to_vec();
    let at = changed
        .windows(13)
        .position(|part| part == b"for (unsigned")
        .unwrap();
    changed[at + 5] = b'X';
    assert!(matches!(
        canonical_guest_typed_ir_with_source(JSON, Some(&changed)),
        Err(FrontendJsonError::Unsupported)
    ));
}

#[test]
fn unsigned_decrement_must_not_treat_wraparound_as_loop_exit() {
    let json =
        include_bytes!("c-frontend/golden/unsigned_wrapping_down_loop.json");
    let source =
        include_bytes!("c-frontend/rejected/unsigned_wrapping_down_loop.c");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(json, Some(source)),
        Err(FrontendJsonError::Unsupported)
    ));
}

const CONDITIONAL_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_conditional_live_input.c");
const CONDITIONAL_JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_conditional_live_input.json");

#[test]
fn unsigned_branch_repeats_one_runtime_byte_without_folding_input() {
    let (_typed, mode) = canonical_guest_typed_ir_with_source(
        CONDITIONAL_JSON,
        Some(CONDITIONAL_SOURCE),
    )
    .expect("source-proven unsigned counter branch must preserve live reads");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
}

#[test]
fn unsigned_branch_requires_original_literal_and_operator_tokens() {
    let mut source = CONDITIONAL_SOURCE.to_vec();
    let at = source
        .windows(7)
        .position(|text| text == b"i == 2U")
        .unwrap();
    source[at + 5] = b'3';
    assert!(matches!(
        canonical_guest_typed_ir_with_source(CONDITIONAL_JSON, Some(&source)),
        Err(FrontendJsonError::Unsupported)
    ));

    let mut value: serde_json::Value =
        serde_json::from_slice(CONDITIONAL_JSON).unwrap();
    let nodes = value["nodes"].as_array_mut().unwrap();
    let comparison = nodes
        .iter_mut()
        .find(|node| {
            node["kind"] == "binary-expression" && node["operation"] == "=="
        })
        .unwrap();
    comparison["operation"] = serde_json::json!("!=");
    let forged = serde_json::to_vec(&value).unwrap();
    assert!(matches!(
        canonical_guest_typed_ir_with_source(&forged, Some(CONDITIONAL_SOURCE)),
        Err(FrontendJsonError::Unsupported)
    ));
}

#[test]
fn unsigned_branch_rejects_forged_counter_type_and_identity() {
    let baseline: serde_json::Value =
        serde_json::from_slice(CONDITIONAL_JSON).unwrap();
    let nodes = baseline["nodes"].as_array().unwrap();
    let condition = nodes
        .iter()
        .position(|node| {
            node["kind"] == "binary-expression" && node["operation"] == "=="
        })
        .unwrap();
    assert_eq!(nodes[condition + 1]["kind"], "cast-expression");
    assert_eq!(
        nodes[condition + 2]["kind"],
        "declaration-reference-expression"
    );
    assert_eq!(nodes[condition + 3]["kind"], "integer-literal");
    for (offset, field, replacement) in [
        (1, "type", "i32"),
        (2, "type", "i32"),
        (2, "reference", "other@0"),
        (3, "type", "i32"),
        (3, "literal", "3"),
        (3, "constant_integer", "3"),
    ] {
        let mut changed = baseline.clone();
        changed["nodes"][condition + offset][field] =
            serde_json::json!(replacement);
        let forged = serde_json::to_vec(&changed).unwrap();
        assert!(
            matches!(
                canonical_guest_typed_ir_with_source(
                    &forged,
                    Some(CONDITIONAL_SOURCE)
                ),
                Err(FrontendJsonError::Unsupported)
            ),
            "forged node {offset} field {field} was admitted"
        );
    }

    let mut source = CONDITIONAL_SOURCE.to_vec();
    let at = source
        .windows(7)
        .position(|part| part == b"i == 2U")
        .unwrap();
    source[at + 6] = b'L';
    assert!(matches!(
        canonical_guest_typed_ir_with_source(CONDITIONAL_JSON, Some(&source)),
        Err(FrontendJsonError::Unsupported)
    ));
}

const STRIDE_SOURCE: &[u8] = include_bytes!(
    "c-frontend/accepted/unsigned_stride_conditional_live_input.c"
);
const STRIDE_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_stride_conditional_live_input.json"
);

#[test]
fn unsigned_compound_stride_selects_live_third_byte_twice() {
    let (typed, mode) =
        canonical_guest_typed_ir_with_source(STRIDE_JSON, Some(STRIDE_SOURCE))
            .expect(
                "source-proven unsigned non-unit stride preserves live input",
            );
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    assert_four_reads_five_writes(&typed);
}

#[test]
fn unsigned_compound_stride_must_not_wrap_at_zero() {
    let json = include_bytes!(
        "c-frontend/golden/unsigned_wrapping_stride_down_loop.json"
    );
    let source = include_bytes!(
        "c-frontend/rejected/unsigned_wrapping_stride_down_loop.c"
    );
    assert!(matches!(
        canonical_guest_typed_ir_with_source(json, Some(source)),
        Err(FrontendJsonError::Unsupported)
    ));
}

#[test]
fn unsigned_compound_stride_authenticates_literal_and_operator() {
    for replacement in [51u8, 32, 76] {
        let mut source = STRIDE_SOURCE.to_vec();
        let at = source
            .windows(7)
            .position(|text| text == b"i += 2U")
            .unwrap();
        source[at + 5] = replacement;
        assert!(matches!(
            canonical_guest_typed_ir_with_source(STRIDE_JSON, Some(&source)),
            Err(FrontendJsonError::Unsupported)
        ));
    }

    let baseline: serde_json::Value =
        serde_json::from_slice(STRIDE_JSON).unwrap();
    let increment = baseline["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .position(|node| node["kind"] == "compound-assignment-expression")
        .unwrap();
    for (offset, field, value) in [
        (0, "operation", "-="),
        (0, "type", "i32"),
        (1, "reference", "other@0"),
        (2, "literal", "3"),
        (2, "type", "i32"),
    ] {
        let mut forged = baseline.clone();
        forged["nodes"][increment + offset][field] = serde_json::json!(value);
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                &serde_json::to_vec(&forged).unwrap(),
                Some(STRIDE_SOURCE)
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
}

const ASSIGNED_STRIDE_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_assigned_stride_live_input.c");
const ASSIGNED_STRIDE_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_assigned_stride_live_input.json"
);

#[test]
fn unsigned_assigned_stride_preserves_live_input() {
    let (typed, mode) = canonical_guest_typed_ir_with_source(
        ASSIGNED_STRIDE_JSON,
        Some(ASSIGNED_STRIDE_SOURCE),
    )
    .expect("source-proven unsigned assignment step preserves live input");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    assert_four_reads_five_writes(&typed);
}

#[test]
fn unsigned_assigned_stride_authenticates_arithmetic_ancestry() {
    let baseline: serde_json::Value =
        serde_json::from_slice(ASSIGNED_STRIDE_JSON).unwrap();
    let increment = baseline["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .position(|node| {
            node["kind"] == "binary-expression" && node["operation"] == "="
        })
        .unwrap();
    for (offset, field, value) in [
        (0, "type", "i32"),
        (2, "operation", "-"),
        (2, "type", "i32"),
        (3, "type", "i32"),
        (4, "reference", "other@0"),
        (5, "literal", "3"),
        (5, "type", "i32"),
    ] {
        let mut forged = baseline.clone();
        forged["nodes"][increment + offset][field] = serde_json::json!(value);
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                &serde_json::to_vec(&forged).unwrap(),
                Some(ASSIGNED_STRIDE_SOURCE)
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
}

#[test]
fn unsigned_descending_stride_stops_at_zero_before_wrapping() {
    let json = include_bytes!(
        "c-frontend/golden/unsigned_descending_stride_live_input.json"
    );
    let source = include_bytes!(
        "c-frontend/accepted/unsigned_descending_stride_live_input.c"
    );
    let (typed, mode) =
        canonical_guest_typed_ir_with_source(json, Some(source))
            .expect("40, 30, 20, 10 must terminate at zero after four reads");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    assert_four_reads_five_writes(&typed);
}

fn assert_five_reads_six_writes(wire: &[u8]) {
    let decoded = canonical_module(wire).expect("canonical typed wire");
    let block = decoded.functions()[0].blocks()[0].instructions();
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for instruction in block {
        match instruction.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected guest effect: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 5);
    assert_eq!(writes, vec![
        reads[0], reads[1], reads[2], reads[2], reads[3], reads[4],
    ]);
}

const EARLY_BREAK_SOURCE: &[u8] = include_bytes!(
    "c-frontend/accepted/unsigned_break_before_wrap_live_input.c"
);
const EARLY_BREAK_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_break_before_wrap_live_input.json"
);

#[test]
fn unsigned_selected_break_prevents_post_body_wrap_and_keeps_guest_bytes() {
    let (typed, mode) = canonical_guest_typed_ir_with_source(
        EARLY_BREAK_JSON,
        Some(EARLY_BREAK_SOURCE),
    )
    .expect("the selected break must skip the otherwise wrapping decrement");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    assert_five_reads_six_writes(&typed);
}

#[test]
fn unsigned_break_exit_requires_original_break_keyword() {
    let mut altered = EARLY_BREAK_SOURCE.to_vec();
    let start = altered
        .windows(6)
        .position(|fragment| fragment == b"break;")
        .expect("selected break exists");
    altered[start..start + 5].copy_from_slice(b"false");
    // C23 `false;` has no exit effect, so the next unsigned decrement wraps.
    // The normalized break metadata alone must never manufacture that exit.
    assert!(matches!(
        canonical_guest_typed_ir_with_source(EARLY_BREAK_JSON, Some(&altered)),
        Err(FrontendJsonError::Unsupported)
    ));
}

const INCLUSIVE_ZERO_BREAK_SOURCE: &[u8] = include_bytes!(
    "c-frontend/accepted/unsigned_inclusive_zero_break_live_input.c"
);
const INCLUSIVE_ZERO_BREAK_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_inclusive_zero_break_live_input.json"
);

#[test]
fn unsigned_zero_inclusive_guard_needs_break_before_wrap() {
    let (typed, mode) = canonical_guest_typed_ir_with_source(
        INCLUSIVE_ZERO_BREAK_JSON,
        Some(INCLUSIVE_ZERO_BREAK_SOURCE),
    )
    .expect("break at zero must make the unsigned >= 0U guard finite");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    assert_five_reads_six_writes(&typed);
}

#[test]
fn unsigned_continue_at_zero_must_not_skip_wrapping_decrement() {
    let json = include_bytes!(
        "c-frontend/golden/unsigned_inclusive_zero_continue_live_input.json"
    );
    let source = include_bytes!(
        "c-frontend/rejected/unsigned_inclusive_zero_continue_live_input.c"
    );
    assert!(matches!(
        canonical_guest_typed_ir_with_source(json, Some(source)),
        Err(FrontendJsonError::Unsupported)
    ));
}

const RADIX_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_radix_live_input.c");
const RADIX_JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_radix_live_input.json");

#[test]
fn unsigned_radix_counter_and_predicate_keep_seven_live_byte_writes() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(
        RADIX_JSON,
        Some(RADIX_SOURCE),
    )
    .expect(
        "source-checked C23 radix induction and branch must preserve guest IO",
    );
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let decoded = canonical_module(&wire).expect("canonical typed module");
    let block = decoded.functions()[0].blocks()[0].instructions();
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in block {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected guest effect: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 5);
    assert_eq!(writes, vec![
        reads[0], reads[1], reads[1], reads[2], reads[3], reads[3], reads[4],
    ]);
}

#[test]
fn unsigned_radix_counter_refuses_source_token_and_clang_forgeries() {
    for (original, forged) in [
        (b"0b1U".as_slice(), b"0b0U".as_slice()),
        (b"0X5u".as_slice(), b"0X6u".as_slice()),
        (b"01u".as_slice(), b"00u".as_slice()),
        (b"0x2U".as_slice(), b"0x3U".as_slice()),
        (b"0u".as_slice(), b"1u".as_slice()),
        (b"0x5U".as_slice(), b"0x5L".as_slice()),
        (b"0b1U".as_slice(), b"0y1U".as_slice()),
    ] {
        let mut changed = RADIX_SOURCE.to_vec();
        let at = changed
            .windows(original.len())
            .position(|part| part == original)
            .expect("radix token exists");
        changed[at..at + original.len()].copy_from_slice(forged);
        assert!(
            matches!(
                canonical_guest_typed_ir_with_source(
                    RADIX_JSON,
                    Some(&changed),
                ),
                Err(FrontendJsonError::Unsupported)
            ),
            "forged source token {} was admitted",
            String::from_utf8_lossy(forged)
        );
    }

    let baseline: serde_json::Value =
        serde_json::from_slice(RADIX_JSON).unwrap();
    let literal = baseline["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .position(|node| node["kind"] == "integer-literal")
        .unwrap();
    for (field, forged_value) in
        [("literal", "2"), ("constant_integer", "2"), ("type", "i32")]
    {
        let mut forged = baseline.clone();
        forged["nodes"][literal][field] = serde_json::json!(forged_value);
        assert!(
            matches!(
                canonical_guest_typed_ir_with_source(
                    &serde_json::to_vec(&forged).unwrap(),
                    Some(RADIX_SOURCE),
                ),
                Err(FrontendJsonError::Unsupported)
            ),
            "forged radix AST field {field} was admitted"
        );
    }
}

const UNSIGNED_MODULO_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_modulo_live_input.c");
const UNSIGNED_MODULO_JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_modulo_live_input.json");

#[test]
fn unsigned_remainder_branch_repeats_even_input_bytes() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(
        UNSIGNED_MODULO_JSON,
        Some(UNSIGNED_MODULO_SOURCE),
    )
    .expect("source-proven unsigned remainder must select live byte effects");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let decoded = canonical_module(&wire).expect("canonical typed module");
    let block = decoded.functions()[0].blocks()[0].instructions();
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in block {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected guest effect: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 5);
    assert_eq!(writes, vec![
        reads[0], reads[1], reads[1], reads[2], reads[3], reads[3], reads[4],
    ]);
}

#[test]
fn unsigned_remainder_proof_refuses_forged_source_and_clang_types() {
    for (original, replacement) in [
        (b"i % 2U".as_slice(), b"i / 2U".as_slice()),
        (b"i % 2U".as_slice(), b"i % 0U".as_slice()),
        (b"i % 2U".as_slice(), b"i % 3U".as_slice()),
        (b"== 0U".as_slice(), b"!= 0U".as_slice()),
    ] {
        let mut source = UNSIGNED_MODULO_SOURCE.to_vec();
        let start = source
            .windows(original.len())
            .position(|fragment| fragment == original)
            .expect("original token in source fixture");
        source[start..start + replacement.len()].copy_from_slice(replacement);
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                UNSIGNED_MODULO_JSON,
                Some(&source)
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }

    let baseline: serde_json::Value =
        serde_json::from_slice(UNSIGNED_MODULO_JSON).unwrap();
    let nodes = baseline["nodes"].as_array().unwrap();
    let remainder = nodes
        .iter()
        .position(|node| {
            node["kind"] == "binary-expression" && node["operation"] == "%"
        })
        .unwrap();
    for (offset, field, replacement) in [
        (0, "type", "i32"),
        (0, "operation", "/"),
        (1, "type", "i32"),
        (2, "reference", "other@0"),
        (3, "type", "i32"),
        (3, "literal", "3"),
        (3, "constant_integer", "3"),
    ] {
        let mut forged = baseline.clone();
        forged["nodes"][remainder + offset][field] =
            serde_json::json!(replacement);
        let wire = serde_json::to_vec(&forged).unwrap();
        assert!(
            matches!(
                canonical_guest_typed_ir_with_source(
                    &wire,
                    Some(UNSIGNED_MODULO_SOURCE)
                ),
                Err(FrontendJsonError::Unsupported)
            ),
            "forged node {offset} field {field} admitted"
        );
    }
}

const UNSIGNED_WRAP_SOURCE: &[u8] = include_bytes!(
    "c-frontend/accepted/unsigned_wrapping_predicate_live_input.c"
);
const UNSIGNED_WRAP_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_wrapping_predicate_live_input.json"
);

#[test]
fn unsigned_subtraction_wraps_before_counter_branch_selection() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(
        UNSIGNED_WRAP_JSON,
        Some(UNSIGNED_WRAP_SOURCE),
    )
    .expect("unsigned 1U - 2U wraps and selects the first extra output");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let decoded = canonical_module(&wire).expect("canonical typed module");
    let block = decoded.functions()[0].blocks()[0].instructions();
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in block {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected guest effect: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 4);
    assert_eq!(writes, vec![
        reads[0], reads[0], reads[1], reads[2], reads[3],
    ]);
}

#[test]
fn unsigned_wrap_guard_authenticates_source_tokens_and_comparison_type() {
    for (original, replacement) in [
        (b"i - 2U".as_slice(), b"i + 2U".as_slice()),
        (b"i - 2U".as_slice(), b"i - 3U".as_slice()),
        (b"> 99U".as_slice(), b"< 99U".as_slice()),
    ] {
        let mut source = UNSIGNED_WRAP_SOURCE.to_vec();
        let start = source
            .windows(original.len())
            .position(|fragment| fragment == original)
            .unwrap();
        source[start..start + replacement.len()].copy_from_slice(replacement);
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                UNSIGNED_WRAP_JSON,
                Some(&source)
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
    let baseline: serde_json::Value =
        serde_json::from_slice(UNSIGNED_WRAP_JSON).unwrap();
    let subtraction = baseline["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .position(|node| {
            node["kind"] == "binary-expression" && node["operation"] == "-"
        })
        .unwrap();
    for (offset, field, replacement) in [
        (0, "type", "i32"),
        (0, "operation", "+"),
        (1, "type", "i32"),
        (2, "reference", "other@0"),
        (3, "type", "i32"),
        (3, "literal", "3"),
    ] {
        let mut forged = baseline.clone();
        forged["nodes"][subtraction + offset][field] =
            serde_json::json!(replacement);
        let wire = serde_json::to_vec(&forged).unwrap();
        assert!(
            matches!(
                canonical_guest_typed_ir_with_source(
                    &wire,
                    Some(UNSIGNED_WRAP_SOURCE)
                ),
                Err(FrontendJsonError::Unsupported)
            ),
            "forged node {offset} field {field} admitted"
        );
    }
}

const UNSIGNED_SKIPPED_DIVISION_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_short_circuit_zero_divisor.c");
const UNSIGNED_SKIPPED_DIVISION_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_short_circuit_zero_divisor.json"
);

#[test]
fn unsigned_short_circuit_skips_unreachable_zero_divisor() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(
        UNSIGNED_SKIPPED_DIVISION_JSON,
        Some(UNSIGNED_SKIPPED_DIVISION_SOURCE),
    )
    .expect("source-proven break skips undefined unsigned division");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let decoded = canonical_module(&wire).expect("canonical typed module");
    let block = decoded.functions()[0].blocks()[0].instructions();
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in block {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected guest effect: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 1);
    assert_eq!(writes, reads);
}

#[test]
fn unsigned_reachable_zero_divisor_refuses_without_guest_artifact() {
    let json = include_bytes!(
        "c-frontend/golden/unsigned_reachable_zero_divisor.json"
    );
    let source =
        include_bytes!("c-frontend/rejected/unsigned_reachable_zero_divisor.c");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(json, Some(source)),
        Err(FrontendJsonError::Unsupported)
    ));
}

#[test]
fn skipped_unsigned_zero_divisor_still_checks_source_and_clang() {
    for (original, replacement) in [
        (b"i / 0U".as_slice(), b"i % 0U".as_slice()),
        (b"i / 0U".as_slice(), b"i / 1U".as_slice()),
        (b"i == 1U".as_slice(), b"i == 2U".as_slice()),
        (b"1U ||".as_slice(), b"1U &&".as_slice()),
    ] {
        let mut source = UNSIGNED_SKIPPED_DIVISION_SOURCE.to_vec();
        let start = source
            .windows(original.len())
            .position(|part| part == original)
            .unwrap();
        source[start..start + replacement.len()].copy_from_slice(replacement);
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                UNSIGNED_SKIPPED_DIVISION_JSON,
                Some(&source)
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
    let baseline: serde_json::Value =
        serde_json::from_slice(UNSIGNED_SKIPPED_DIVISION_JSON).unwrap();
    let division = baseline["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .position(|node| {
            node["kind"] == "binary-expression" && node["operation"] == "/"
        })
        .unwrap();
    for (offset, field, replacement) in [
        (0, "type", "i32"),
        (0, "operation", "%"),
        (1, "type", "i32"),
        (2, "reference", "other@0"),
        (3, "type", "i32"),
        (3, "literal", "1"),
    ] {
        let mut forged = baseline.clone();
        forged["nodes"][division + offset][field] =
            serde_json::json!(replacement);
        let wire = serde_json::to_vec(&forged).unwrap();
        assert!(
            matches!(
                canonical_guest_typed_ir_with_source(
                    &wire,
                    Some(UNSIGNED_SKIPPED_DIVISION_SOURCE)
                ),
                Err(FrontendJsonError::Unsupported)
            ),
            "skipped forged node {offset} field {field} admitted"
        );
    }
}

const NESTED_OUTER_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/nested_outer_induction_live_input.c");
const NESTED_OUTER_JSON: &[u8] =
    include_bytes!("c-frontend/golden/nested_outer_induction_live_input.json");

#[test]
fn nested_unsigned_loop_can_select_outer_counter_without_folding_input() {
    let (typed, mode) = canonical_guest_typed_ir_with_source(
        NESTED_OUTER_JSON,
        Some(NESTED_OUTER_SOURCE),
    )
    .expect("inner loop should preserve authenticated enclosing induction");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let decoded = canonical_module(&typed).unwrap();
    let effects = decoded.functions()[0].blocks()[0].instructions();
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in effects {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected effect: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 6);
    assert_eq!(writes, vec![
        reads[0], reads[1], reads[2], reads[2], reads[3], reads[3], reads[4],
        reads[5]
    ]);
}

#[test]
fn nested_outer_guard_refuses_source_and_clang_counter_forgeries() {
    // `row` and `col` have the same width. A source-only rewrite of the
    // selected predicate changes C behavior without changing Clang metadata.
    let mut source = NESTED_OUTER_SOURCE.to_vec();
    let at = source
        .windows(11)
        .position(|part| part == b"row == 2U) ")
        .unwrap();
    source[at..at + 3].copy_from_slice(b"col");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(NESTED_OUTER_JSON, Some(&source)),
        Err(FrontendJsonError::Unsupported)
    ));

    let mut forged: serde_json::Value =
        serde_json::from_slice(NESTED_OUTER_JSON).unwrap();
    let reference = forged["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .position(|node| {
            node["kind"] == "declaration-reference-expression"
                && node["reference"]
                    .as_str()
                    .is_some_and(|value| value.starts_with("row@"))
                && node["span"]["begin"]["line"] == 31
        })
        .unwrap();
    forged["nodes"][reference]["reference"] = serde_json::json!("col@0");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            &serde_json::to_vec(&forged).unwrap(),
            Some(NESTED_OUTER_SOURCE)
        ),
        Err(FrontendJsonError::Unsupported)
    ));
}

const NESTED_MIXED_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/nested_mixed_induction_live_input.c");
const NESTED_MIXED_JSON: &[u8] =
    include_bytes!("c-frontend/golden/nested_mixed_induction_live_input.json");

#[test]
fn nested_unsigned_mixed_counter_guard_uses_two_source_bound_values() {
    let (typed, mode) = canonical_guest_typed_ir_with_source(
        NESTED_MIXED_JSON,
        Some(NESTED_MIXED_SOURCE),
    )
    .expect("both nested counters must be source and Clang authenticated");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let decoded = canonical_module(&typed).unwrap();
    let effects = decoded.functions()[0].blocks()[0].instructions();
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in effects {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected effect: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 6);
    assert_eq!(writes, vec![
        reads[0], reads[1], reads[2], reads[2], reads[3], reads[4], reads[5]
    ]);
}

#[test]
fn nested_mixed_counter_guard_refuses_forged_source_and_ast() {
    let mut source = NESTED_MIXED_SOURCE.to_vec();
    let at = source.windows(2).position(|part| part == b"&&").unwrap();
    source[at..at + 2].copy_from_slice(b"||");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(NESTED_MIXED_JSON, Some(&source)),
        Err(FrontendJsonError::Unsupported)
    ));
    let baseline: serde_json::Value =
        serde_json::from_slice(NESTED_MIXED_JSON).unwrap();
    let nodes = baseline["nodes"].as_array().unwrap();
    let combined = nodes
        .iter()
        .position(|node| {
            node["kind"] == "binary-expression" && node["operation"] == "&&"
        })
        .unwrap();
    let child = nodes
        .iter()
        .position(|node| {
            node["kind"] == "declaration-reference-expression"
                && node["reference"]
                    .as_str()
                    .is_some_and(|value| value.starts_with("col@"))
                && node["span"]["begin"]["line"] == 31
        })
        .unwrap();
    for (index, field, value) in [
        (combined, "operation", "||"),
        (child, "reference", "row@0"),
        (child, "type", "i32"),
    ] {
        let mut forged = baseline.clone();
        forged["nodes"][index][field] = serde_json::json!(value);
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                &serde_json::to_vec(&forged).unwrap(),
                Some(NESTED_MIXED_SOURCE)
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
}

const TRIPLE_INDUCTION_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/triple_induction_live_input.c");
const TRIPLE_INDUCTION_JSON: &[u8] =
    include_bytes!("c-frontend/golden/triple_induction_live_input.json");

#[test]
fn three_nested_unsigned_counters_select_one_live_guest_byte() {
    let (typed, mode) = canonical_guest_typed_ir_with_source(
        TRIPLE_INDUCTION_JSON,
        Some(TRIPLE_INDUCTION_SOURCE),
    )
    .expect("all three finite C counters must remain source authenticated");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let decoded = canonical_module(&typed).unwrap();
    let effects = decoded.functions()[0].blocks()[0].instructions();
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in effects {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected guest effect: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 8);
    assert_eq!(writes, vec![
        reads[0], reads[1], reads[2], reads[3], reads[4], reads[5], reads[5],
        reads[6], reads[7]
    ]);
}

#[test]
fn three_nested_unsigned_counters_reject_source_and_clang_forgeries() {
    // A valid Clang predicate about row would mean a different selection
    // than a forged source predicate about col, even at the same byte width.
    let mut changed = TRIPLE_INDUCTION_SOURCE.to_vec();
    let predicate = changed
        .windows(9)
        .position(|part| part == b"row == 1U")
        .unwrap();
    changed[predicate..predicate + 3].copy_from_slice(b"col");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            TRIPLE_INDUCTION_JSON,
            Some(&changed),
        ),
        Err(FrontendJsonError::Unsupported)
    ));

    let baseline: serde_json::Value =
        serde_json::from_slice(TRIPLE_INDUCTION_JSON).unwrap();
    let nodes = baseline["nodes"].as_array().unwrap();
    let ancestor = nodes
        .iter()
        .position(|node| {
            node["kind"] == "declaration-reference-expression"
                && node["reference"]
                    .as_str()
                    .is_some_and(|reference| reference.starts_with("plane@"))
                && node["span"]["begin"]["line"] == 32
        })
        .unwrap();
    for (field, value) in [("reference", "other@0"), ("type", "i32")] {
        let mut forged = baseline.clone();
        forged["nodes"][ancestor][field] = serde_json::json!(value);
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                &serde_json::to_vec(&forged).unwrap(),
                Some(TRIPLE_INDUCTION_SOURCE),
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
}

const TRIPLE_CONTROL_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/triple_control_live_input.c");
const TRIPLE_CONTROL_JSON: &[u8] =
    include_bytes!("c-frontend/golden/triple_control_live_input.json");

#[test]
fn triple_induction_inner_break_and_continue_do_not_exit_outer_loop() {
    let (typed, mode) = canonical_guest_typed_ir_with_source(
        TRIPLE_CONTROL_JSON,
        Some(TRIPLE_CONTROL_SOURCE),
    )
    .expect("selected inner exits must preserve later outer loop reads");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let decoded = canonical_module(&typed).unwrap();
    let effects = decoded.functions()[0].blocks()[0].instructions();
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in effects {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected guest effect: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 7);
    assert_eq!(writes, vec![
        reads[0], reads[1], reads[2], reads[2], reads[3], reads[4], reads[5],
        reads[6]
    ]);
}

#[test]
fn triple_induction_break_exit_checks_original_c_keyword() {
    let mut changed = TRIPLE_CONTROL_SOURCE.to_vec();
    let at = changed
        .windows(6)
        .rposition(|word| word == b"break;")
        .unwrap();
    changed[at..at + 5].copy_from_slice(b"false");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            TRIPLE_CONTROL_JSON,
            Some(&changed),
        ),
        Err(FrontendJsonError::Unsupported)
    ));
}
