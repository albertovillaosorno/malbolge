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

use super::super::{
    FrontendGuestMode, FrontendJsonError, canonical_guest_typed_ir_with_source,
};

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
