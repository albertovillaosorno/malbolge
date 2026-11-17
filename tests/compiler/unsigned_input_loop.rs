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
fn signed_loop_local_repeated_in_counter_branch_must_refuse_eof_output() {
    // The bounded loop really reads four signed getchar results. Its
    // induction-only branch repeats a signed local, so C writes 0xff at
    // EOF while the current byte-only guest would publish 0x6a.
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            CONDITIONAL_JSON,
            Some(CONDITIONAL_SOURCE),
        ),
        Err(FrontendJsonError::Unsupported)
    ));
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

const UNSIGNED_SCALAR_TRUTH_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_scalar_truth_live_input.c");
const UNSIGNED_SCALAR_TRUTH_JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_scalar_truth_live_input.json");

#[test]
fn unsigned_scalar_truth_preserves_four_live_bytes_and_seven_writes() {
    let (typed, mode) = canonical_guest_typed_ir_with_source(
        UNSIGNED_SCALAR_TRUTH_JSON,
        Some(UNSIGNED_SCALAR_TRUTH_SOURCE),
    )
    .expect("source-proven unsigned scalar guard must select real guest I/O");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let decoded =
        canonical_module(&typed).expect("canonical typed byte effects");
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
    assert_eq!(reads.len(), 4);
    assert_eq!(writes, vec![
        reads[0], reads[1], reads[1], reads[2], reads[2], reads[3], reads[3]
    ]);
}

#[test]
fn unsigned_scalar_truth_requires_original_counter_and_typed_reference() {
    for replacement in [b'1', b'0'] {
        let mut source = UNSIGNED_SCALAR_TRUTH_SOURCE.to_vec();
        let at = source
            .windows(6)
            .position(|part| part == b"if (i)")
            .expect("source contains scalar unsigned condition");
        source[at + 4] = replacement;
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                UNSIGNED_SCALAR_TRUTH_JSON,
                Some(&source)
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
    let baseline: serde_json::Value =
        serde_json::from_slice(UNSIGNED_SCALAR_TRUTH_JSON).unwrap();
    let nodes = baseline["nodes"].as_array().unwrap();
    let read = nodes
        .iter()
        .position(|node| node["kind"] == "if-statement" && node["id"] == 19)
        .unwrap()
        + 1;
    assert_eq!(nodes[read]["type"], "u32");
    assert_eq!(nodes[read + 1]["type"], "u32");
    for (offset, key, forged_value) in [
        (0, "type", "i32"),
        (1, "type", "i32"),
        (1, "reference", "other@0"),
    ] {
        let mut forged = baseline.clone();
        forged["nodes"][read + offset][key] = serde_json::json!(forged_value);
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                &serde_json::to_vec(&forged).unwrap(),
                Some(UNSIGNED_SCALAR_TRUTH_SOURCE)
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
}

const UNSIGNED_BITWISE_TRUTH_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_bitwise_truth_live_input.c");
const UNSIGNED_BITWISE_TRUTH_JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_bitwise_truth_live_input.json");

#[test]
fn unsigned_bitwise_predicates_preserve_runtime_byte_provenance() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(
        UNSIGNED_BITWISE_TRUTH_JSON,
        Some(UNSIGNED_BITWISE_TRUTH_SOURCE),
    )
    .expect("source-proven unsigned &, ^ and | guards should lower");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let module = canonical_module(&wire).expect("typed module must round-trip");
    let effects = module.functions()[0].blocks()[0].instructions();
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in effects {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected guest effect: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 4);
    assert_eq!(writes, vec![
        reads[0], reads[0], reads[1], reads[1], reads[1], reads[1], reads[2],
        reads[2], reads[3], reads[3], reads[3], reads[3],
    ]);
}

#[test]
fn unsigned_bitwise_predicates_require_original_source_and_clang_ops() {
    let baseline: serde_json::Value =
        serde_json::from_slice(UNSIGNED_BITWISE_TRUTH_JSON).unwrap();
    for (operator, forged) in
        [(b"i & 1U", b'|'), (b"i ^ 2U", b'&'), (b"i | 0U", b'^')]
    {
        let mut source = UNSIGNED_BITWISE_TRUTH_SOURCE.to_vec();
        let start = source
            .windows(operator.len())
            .position(|part| part == operator)
            .expect("source contains bitwise predicate");
        source[start + 2] = forged;
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                UNSIGNED_BITWISE_TRUTH_JSON,
                Some(&source)
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
    for (id, forged) in [(20, "|"), (31, "&"), (42, "^")] {
        let mut normalized = baseline.clone();
        normalized["nodes"][id - 1]["operation"] = serde_json::json!(forged);
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                &serde_json::to_vec(&normalized).unwrap(),
                Some(UNSIGNED_BITWISE_TRUTH_SOURCE)
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
    for (id, forged) in [(21, "i32"), (22, "i32"), (23, "i32")] {
        let mut normalized = baseline.clone();
        normalized["nodes"][id - 1]["type"] = serde_json::json!(forged);
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                &serde_json::to_vec(&normalized).unwrap(),
                Some(UNSIGNED_BITWISE_TRUTH_SOURCE)
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
}

const UNSIGNED_ALIAS_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_alias_induction_live_input.c");
const UNSIGNED_ALIAS_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_alias_induction_live_input.json"
);

#[test]
fn unsigned_alias_induction_preserves_one_live_guest_byte_across_names() {
    let (typed, mode) = canonical_guest_typed_ir_with_source(
        UNSIGNED_ALIAS_JSON,
        Some(UNSIGNED_ALIAS_SOURCE),
    )
    .expect("both C local names must select the same live guest byte");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let decoded =
        canonical_module(&typed).expect("canonical typed guest trace");
    let block = &decoded.functions()[0].blocks()[0];
    let instructions = block.instructions();
    assert_eq!(instructions.len(), 4);
    let Instruction::ByteInput { result, .. } = instructions[0].instruction()
    else {
        panic!("expected one live guest input");
    };
    for output in &instructions[1..] {
        assert!(matches!(
            output.instruction(),
            Instruction::ByteOutput { value } if value == result
        ));
    }

    let mut changed = UNSIGNED_ALIAS_SOURCE.to_vec();
    let at = changed
        .windows(18)
        .position(|part| part == b"int alias = first;")
        .unwrap();
    changed[at + 4] = b'X';
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            UNSIGNED_ALIAS_JSON,
            Some(&changed)
        ),
        Err(FrontendJsonError::Unsupported)
    ));

    // A same-width operand substitution must not reinterpret Clang's alias.
    let mut changed = UNSIGNED_ALIAS_SOURCE.to_vec();
    let at = changed
        .windows(15)
        .position(|part| part == b"putchar(alias);")
        .unwrap();
    changed[at + 8..at + 13].copy_from_slice(b"first");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            UNSIGNED_ALIAS_JSON,
            Some(&changed)
        ),
        Err(FrontendJsonError::Unsupported)
    ));
}

const STALE_ALIAS_SOURCE: &[u8] =
    include_bytes!("c-frontend/rejected/unsigned_stale_alias_induction.c");
const STALE_ALIAS_JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_stale_alias_induction.json");

#[test]
fn unsigned_alias_induction_refuses_clobbered_earlier_guest_byte() {
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            STALE_ALIAS_JSON,
            Some(STALE_ALIAS_SOURCE)
        ),
        Err(FrontendJsonError::Unsupported)
    ));
}

const NESTED_ALIAS_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_nested_alias_live_input.c");
const NESTED_ALIAS_JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_nested_alias_live_input.json");
const NESTED_STALE_ALIAS_SOURCE: &[u8] =
    include_bytes!("c-frontend/rejected/unsigned_nested_stale_alias.c");
const NESTED_STALE_ALIAS_JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_nested_stale_alias.json");

#[test]
fn nested_unsigned_local_alias_retains_one_live_guest_value() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(
        NESTED_ALIAS_JSON,
        Some(NESTED_ALIAS_SOURCE),
    )
    .expect("nested source-checked aliases must retain the resident byte");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let module = canonical_module(&wire).expect("canonical typed nested alias");
    let instructions = module.functions()[0].blocks()[0].instructions();
    assert_eq!(instructions.len(), 5);
    let Instruction::ByteInput { result, .. } = instructions[0].instruction()
    else {
        panic!("expected one guest byte read");
    };
    for instruction in &instructions[1..] {
        assert!(matches!(
            instruction.instruction(),
            Instruction::ByteOutput { value } if value == result
        ));
    }
}

#[test]
fn nested_unsigned_alias_refuses_forged_binding_and_stale_guest_state() {
    let mut edited = NESTED_ALIAS_SOURCE.to_vec();
    let token = b"int localcopy = alias;";
    let offset = edited
        .windows(token.len())
        .position(|bytes| bytes == token)
        .expect("source fixture contains inner alias");
    edited[offset + 4] = b'X';
    assert!(matches!(
        canonical_guest_typed_ir_with_source(NESTED_ALIAS_JSON, Some(&edited)),
        Err(FrontendJsonError::Unsupported)
    ));

    let original: serde_json::Value =
        serde_json::from_slice(NESTED_ALIAS_JSON).unwrap();
    // Clang's declaration provenance, nested loop counter, byte output
    // operands and source operator must all remain exactly source-bound.
    for (node, field, replacement) in [
        (26usize, "reference", serde_json::json!("first@905")),
        (41, "reference", serde_json::json!("j@1041")),
        (48, "reference", serde_json::json!("first@905")),
        (54, "reference", serde_json::json!("localcopy@1000")),
        (39, "operation", serde_json::json!("|")),
        (17, "type", serde_json::json!("i32")),
    ] {
        let mut forged = original.clone();
        forged["nodes"][node - 1][field] = replacement;
        assert!(
            matches!(
                canonical_guest_typed_ir_with_source(
                    &serde_json::to_vec(&forged).unwrap(),
                    Some(NESTED_ALIAS_SOURCE),
                ),
                Err(FrontendJsonError::Unsupported)
            ),
            "forged node {node} field {field} escaped source admission"
        );
    }

    // A later getchar inside the nested loop clobbers accumulator state;
    // names bound to the earlier input cannot be silently reinterpreted.
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            NESTED_STALE_ALIAS_JSON,
            Some(NESTED_STALE_ALIAS_SOURCE),
        ),
        Err(FrontendJsonError::Unsupported)
    ));
}

const NESTED_FRESH_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_nested_fresh_live_input.c");
const NESTED_FRESH_JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_nested_fresh_live_input.json");

#[test]
fn nested_unsigned_fresh_reads_preserve_current_ssa_without_old_alias() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(
        NESTED_FRESH_JSON,
        Some(NESTED_FRESH_SOURCE),
    )
    .expect("latest-byte nested source control must be accepted");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let module =
        canonical_module(&wire).expect("nested latest-byte typed module");
    let instructions = module.functions()[0].blocks()[0].instructions();
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for instruction in instructions {
        match instruction.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected nested guest effect {other:?}"),
        }
    }
    assert_eq!(reads.len(), 5);
    assert_eq!(writes.as_slice(), &reads[1..]);
}

const UNSIGNED_HEX_THRESHOLD_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_hex_threshold_live_input.c");
const UNSIGNED_HEX_THRESHOLD_JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_hex_threshold_live_input.json");

#[test]
fn signed_c23_hex_threshold_selects_all_live_guest_byte_outputs() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(
        UNSIGNED_HEX_THRESHOLD_JSON,
        Some(UNSIGNED_HEX_THRESHOLD_SOURCE),
    )
    .expect("the exact C23 threshold exceeds all successful guest bytes");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let module = canonical_module(&wire).expect("canonical live byte trace");
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in module.functions()[0].blocks()[0].instructions() {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected guest effect: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 4);
    assert_eq!(writes, vec![
        reads[0], reads[0], reads[1], reads[1], reads[2], reads[2], reads[3],
        reads[3],
    ]);
}

#[test]
fn signed_c23_hex_threshold_rejects_source_and_clang_literal_forgery() {
    let source = UNSIGNED_HEX_THRESHOLD_SOURCE;
    let start = source
        .windows(5)
        .rposition(|part| part == b"0x100")
        .expect("C23 hex predicate token");
    for digit in [b'1', b'2'] {
        let mut forged = source.to_vec();
        forged[start + 4] = digit;
        let observed = canonical_guest_typed_ir_with_source(
            UNSIGNED_HEX_THRESHOLD_JSON,
            Some(&forged),
        );
        assert!(
            matches!(observed, Err(FrontendJsonError::Unsupported)),
            "forged source final digit {digit}: {observed:?}"
        );
    }
    let baseline: serde_json::Value =
        serde_json::from_slice(UNSIGNED_HEX_THRESHOLD_JSON).unwrap();
    let index = baseline["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .position(|node| {
            node["kind"] == "integer-literal" && node["literal"] == "256"
        })
        .expect("Clang records normalized C23 0x100 literal");
    for field in ["literal", "constant_integer"] {
        let mut forged = baseline.clone();
        forged["nodes"][index][field] = serde_json::json!("257");
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                &serde_json::to_vec(&forged).unwrap(),
                Some(source),
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
}

const BYTE_ALGEBRA_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_byte_algebra_live_input.c");
const BYTE_ALGEBRA_JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_byte_algebra_live_input.json");

#[test]
fn source_proven_byte_algebra_selects_only_constant_guest_effects() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(
        BYTE_ALGEBRA_JSON,
        Some(BYTE_ALGEBRA_SOURCE),
    )
    .expect("both bitwise identities hold for all successful guest bytes");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let module = canonical_module(&wire).expect("canonical byte algebra IR");
    let mut reads = Vec::new();
    let mut writes = Vec::new();
    for effect in module.functions()[0].blocks()[0].instructions() {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => reads.push(*result),
            Instruction::ByteOutput { value } => writes.push(*value),
            other => panic!("unexpected byte algebra effect: {other:?}"),
        }
    }
    assert_eq!(reads.len(), 4);
    assert_eq!(
        writes,
        reads.iter().flat_map(|byte| [*byte; 3]).collect::<Vec<_>>()
    );
}

#[test]
fn source_proven_byte_algebra_rejects_forged_operator_and_dynamic_branch() {
    let original: serde_json::Value =
        serde_json::from_slice(BYTE_ALGEBRA_JSON).unwrap();
    let index = original["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .position(|node| {
            node["kind"] == "binary-expression" && node["operation"] == "^"
        })
        .expect("Clang retained the first XOR operator");
    let mut forged = original.clone();
    forged["nodes"][index]["operation"] = serde_json::json!("|");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            &serde_json::to_vec(&forged).unwrap(),
            Some(BYTE_ALGEBRA_SOURCE),
        ),
        Err(FrontendJsonError::Unsupported)
    ));
    let mut changed = BYTE_ALGEBRA_SOURCE.to_vec();
    let old = b"(current ^ current) == 0";
    let at = changed
        .windows(old.len())
        .position(|part| part == old)
        .unwrap();
    changed[at + 9] = b'|';
    assert!(matches!(
        canonical_guest_typed_ir_with_source(BYTE_ALGEBRA_JSON, Some(&changed)),
        Err(FrontendJsonError::Unsupported)
    ));
}

const BYTE_ALGEBRA_DYNAMIC_SOURCE: &[u8] =
    include_bytes!("c-frontend/rejected/unsigned_byte_algebra_dynamic.c");
const BYTE_ALGEBRA_DYNAMIC_JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_byte_algebra_dynamic.json");

#[test]
fn source_byte_algebra_never_folds_guest_dependent_parity() {
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            BYTE_ALGEBRA_DYNAMIC_JSON,
            Some(BYTE_ALGEBRA_DYNAMIC_SOURCE),
        ),
        Err(FrontendJsonError::Unsupported)
    ));
}

const REFLEXIVE_DEAD_PURE_SOURCE: &[u8] = include_bytes!(
    "c-frontend/accepted/unsigned_reflexive_dead_pure_live_input.c"
);
const REFLEXIVE_DEAD_PURE_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_reflexive_dead_pure_live_input.json"
);
const REFLEXIVE_DYNAMIC_PURE_SOURCE: &[u8] = include_bytes!(
    "c-frontend/rejected/unsigned_reflexive_dynamic_pure_live_input.c"
);
const REFLEXIVE_DYNAMIC_PURE_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_reflexive_dynamic_pure_live_input.json"
);
const REFLEXIVE_SELECTED_PURE_SOURCE: &[u8] = include_bytes!(
    "c-frontend/rejected/unsigned_reflexive_selected_pure_live_input.c"
);
const REFLEXIVE_SELECTED_PURE_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_reflexive_selected_pure_live_input.json"
);

#[test]
fn source_dead_pure_arithmetic_cannot_change_guest_input_or_output_counts() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(
        REFLEXIVE_DEAD_PURE_JSON,
        Some(REFLEXIVE_DEAD_PURE_SOURCE),
    )
    .expect("source-proven dead arithmetic may be discarded, not executed");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let module = canonical_module(&wire).expect("typed guest I/O proof");
    let mut latest = None;
    let mut reads = 0;
    let mut writes = 0;
    for effect in module.functions()[0].blocks()[0].instructions() {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => {
                latest = Some(*result);
                reads += 1;
            },
            Instruction::ByteOutput { value } => {
                assert_eq!(Some(*value), latest);
                writes += 1;
            },
            other => panic!("unexpected guest effect: {other:?}"),
        }
    }
    assert_eq!(reads, 4);
    assert_eq!(writes, 12);
}

#[test]
fn source_dead_pure_arithmetic_requires_original_source_and_clang_nodes() {
    let old = b"(current + 1) * 2";
    for (offset, replacement) in [(9, b'-'), (11, b'2'), (16, b'3')] {
        let mut forged = REFLEXIVE_DEAD_PURE_SOURCE.to_vec();
        let at = forged
            .windows(old.len())
            .position(|part| part == old)
            .expect("source witness for dead arithmetic");
        forged[at + offset] = replacement;
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                REFLEXIVE_DEAD_PURE_JSON,
                Some(&forged)
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
    let original: serde_json::Value =
        serde_json::from_slice(REFLEXIVE_DEAD_PURE_JSON).unwrap();
    let nodes = original["nodes"].as_array().unwrap();
    let multiply = nodes
        .iter()
        .position(|node| {
            node["kind"] == "binary-expression" && node["operation"] == "*"
        })
        .expect("normalized multiplication in dead C arm");
    let literal = nodes
        .iter()
        .position(|node| {
            node["kind"] == "integer-literal" && node["literal"] == "2"
        })
        .expect("source-anchored dead expression multiplier");
    for (index, field, forged_value) in [
        (multiply, "operation", serde_json::json!("+")),
        (multiply, "type", serde_json::json!("u32")),
        (literal, "literal", serde_json::json!("3")),
        (literal, "constant_integer", serde_json::json!("3")),
    ] {
        let mut changed = original.clone();
        changed["nodes"][index][field] = forged_value;
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                &serde_json::to_vec(&changed).unwrap(),
                Some(REFLEXIVE_DEAD_PURE_SOURCE)
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
}

#[test]
fn source_dead_pure_arithmetic_refuses_live_or_selected_effects() {
    for (json, source) in [
        (REFLEXIVE_DYNAMIC_PURE_JSON, REFLEXIVE_DYNAMIC_PURE_SOURCE),
        (REFLEXIVE_SELECTED_PURE_JSON, REFLEXIVE_SELECTED_PURE_SOURCE),
    ] {
        assert!(matches!(
            canonical_guest_typed_ir_with_source(json, Some(source)),
            Err(FrontendJsonError::Unsupported)
        ));
    }
}

const REFLEXIVE_DEAD_LITERAL_SOURCE: &[u8] = include_bytes!(
    "c-frontend/accepted/unsigned_reflexive_dead_literal_live_input.c"
);
const REFLEXIVE_DEAD_LITERAL_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_reflexive_dead_literal_live_input.json"
);

#[test]
fn source_reflexive_guard_authenticates_unreachable_literal_output() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(
        REFLEXIVE_DEAD_LITERAL_JSON,
        Some(REFLEXIVE_DEAD_LITERAL_SOURCE),
    )
    .expect("the source-bound self-comparison makes putchar(0) unreachable");
    assert_eq!(mode, FrontendGuestMode::LatestRead);
    let module = canonical_module(&wire).expect("typed guest I/O proof");
    let mut latest = None;
    let mut reads = 0;
    let mut writes = 0;
    for effect in module.functions()[0].blocks()[0].instructions() {
        match effect.instruction() {
            Instruction::ByteInput { result, .. } => {
                latest = Some(*result);
                reads += 1;
            },
            Instruction::ByteOutput { value } => {
                assert_eq!(Some(*value), latest);
                writes += 1;
            },
            other => panic!("unexpected guest effect: {other:?}"),
        }
    }
    assert_eq!(reads, 4);
    assert_eq!(writes, 12);
}

const REFLEXIVE_SELECTED_LITERAL_SOURCE: &[u8] = include_bytes!(
    "c-frontend/rejected/unsigned_reflexive_selected_literal_live_input.c"
);
const REFLEXIVE_SELECTED_LITERAL_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_reflexive_selected_literal_live_input.json"
);
const REFLEXIVE_DYNAMIC_LITERAL_SOURCE: &[u8] = include_bytes!(
    "c-frontend/rejected/unsigned_reflexive_dynamic_literal_live_input.c"
);
const REFLEXIVE_DYNAMIC_LITERAL_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_reflexive_dynamic_literal_live_input.json"
);

#[test]
fn source_reflexive_guard_never_discards_reachable_literal_output() {
    for (json, source) in [
        (
            REFLEXIVE_SELECTED_LITERAL_JSON,
            REFLEXIVE_SELECTED_LITERAL_SOURCE,
        ),
        (
            REFLEXIVE_DYNAMIC_LITERAL_JSON,
            REFLEXIVE_DYNAMIC_LITERAL_SOURCE,
        ),
    ] {
        assert!(matches!(
            canonical_guest_typed_ir_with_source(json, Some(source)),
            Err(FrontendJsonError::Unsupported)
        ));
    }
}

#[test]
fn source_reflexive_dead_literal_requires_exact_source_and_clang_proof() {
    for (needle, offset, replacement) in [
        (b"0xA5".as_slice(), 3, b'6'),
        (b"putchar(0);".as_slice(), 8, b'1'),
        (b"current == current".as_slice(), 9, b'!'),
    ] {
        let mut forged = REFLEXIVE_DEAD_LITERAL_SOURCE.to_vec();
        let at = forged
            .windows(needle.len())
            .position(|bytes| bytes == needle)
            .expect("source witness for discarded branch");
        forged[at + offset] = replacement;
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                REFLEXIVE_DEAD_LITERAL_JSON,
                Some(&forged),
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
    let original: serde_json::Value =
        serde_json::from_slice(REFLEXIVE_DEAD_LITERAL_JSON).unwrap();
    let nodes = original["nodes"].as_array().unwrap();
    let literal_index = nodes
        .iter()
        .position(|node| {
            node["kind"] == "integer-literal" && node["literal"] == "165"
        })
        .expect("normalized C23 hex integer literal");
    for (field, forged_value) in [
        ("literal", serde_json::json!("166")),
        ("constant_integer", serde_json::json!("166")),
        ("type", serde_json::json!("u32")),
    ] {
        let mut altered = original.clone();
        altered["nodes"][literal_index][field] = forged_value;
        assert!(matches!(
            canonical_guest_typed_ir_with_source(
                &serde_json::to_vec(&altered).unwrap(),
                Some(REFLEXIVE_DEAD_LITERAL_SOURCE),
            ),
            Err(FrontendJsonError::Unsupported)
        ));
    }
    let call_index = nodes
        .iter()
        .position(|node| {
            node["kind"] == "call-expression"
                && node["span"]["begin"]["line"] == 35
        })
        .expect("unreachable literal call");
    let mut altered = original.clone();
    altered["nodes"][call_index]["reference"] =
        serde_json::json!("external:getchar");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            &serde_json::to_vec(&altered).unwrap(),
            Some(REFLEXIVE_DEAD_LITERAL_SOURCE),
        ),
        Err(FrontendJsonError::Unsupported)
    ));
}

const MODULAR_OUTPUT_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_modular_output_live_input.c");
const MODULAR_OUTPUT_JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_modular_output_live_input.json");
const NONMODULAR_OUTPUT_SOURCE: &[u8] = include_bytes!(
    "c-frontend/rejected/unsigned_nonmodular_output_live_input.c"
);
const NONMODULAR_OUTPUT_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_nonmodular_output_live_input.json"
);
const OVERFLOWING_OUTPUT_SOURCE: &[u8] = include_bytes!(
    "c-frontend/rejected/unsigned_overflowing_output_live_input.c"
);
const OVERFLOWING_OUTPUT_JSON: &[u8] = include_bytes!(
    "c-frontend/golden/unsigned_overflowing_output_live_input.json"
);

#[test]
fn source_proven_modular_c_output_preserves_four_live_guest_bytes() {
    let (wire, mode) = canonical_guest_typed_ir_with_source(
        MODULAR_OUTPUT_JSON,
        Some(MODULAR_OUTPUT_SOURCE),
    )
    .expect("pure C arithmetic equivalent after putchar conversion");
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
    assert_eq!(
        writes,
        reads
            .iter()
            .copied()
            .flat_map(|v| [v; 5])
            .collect::<Vec<_>>()
    );
}

#[test]
fn source_proven_modular_output_rejects_nonidentity_and_forged_ast() {
    for (json, source) in [
        (NONMODULAR_OUTPUT_JSON, NONMODULAR_OUTPUT_SOURCE),
        (OVERFLOWING_OUTPUT_JSON, OVERFLOWING_OUTPUT_SOURCE),
    ] {
        assert!(matches!(
            canonical_guest_typed_ir_with_source(json, Some(source)),
            Err(FrontendJsonError::Unsupported)
        ));
    }

    let baseline: serde_json::Value =
        serde_json::from_slice(MODULAR_OUTPUT_JSON).unwrap();
    let nodes = baseline["nodes"].as_array().unwrap();
    let addition = nodes
        .iter()
        .position(|node| {
            node["kind"] == "binary-expression" && node["operation"] == "+"
        })
        .unwrap();
    let plus_literal = nodes
        .iter()
        .position(|node| {
            node["kind"] == "integer-literal" && node["literal"] == "256"
        })
        .unwrap();
    let local = nodes
        .iter()
        .position(|node| {
            node["kind"] == "declaration-reference-expression"
                && node["reference"]
                    .as_str()
                    .is_some_and(|reference| reference.starts_with("current@"))
        })
        .unwrap();
    for (index, field, replacement) in [
        (addition, "operation", "-"),
        (addition, "type", "u32"),
        (plus_literal, "literal", "257"),
        (plus_literal, "constant_integer", "257"),
        (local, "reference", "other@0"),
    ] {
        let mut forged = baseline.clone();
        forged["nodes"][index][field] = serde_json::json!(replacement);
        let result = canonical_guest_typed_ir_with_source(
            &serde_json::to_vec(&forged).unwrap(),
            Some(MODULAR_OUTPUT_SOURCE),
        );
        assert!(
            matches!(result, Err(FrontendJsonError::Unsupported)),
            "forged {field} at node {index} was admitted"
        );
    }
}
