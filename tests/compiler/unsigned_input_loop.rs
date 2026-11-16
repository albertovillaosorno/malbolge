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
