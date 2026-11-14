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
