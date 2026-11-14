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
//   - Bounded source-state collision preferences for guest byte emission.
// - Must-Not:
//   - Treat a predicted accumulator value as a verified guest source.
// - Allows:
//   - Inputs: equal full-word successor proposals with different write effects.
//   - Outputs: a preserved source-independent no-op path.
//   - Side effects: none.
// - Split-When:
//   - Complete history diversity replaces bounded exact-word search.
// - Merge-When:
//   - Canonical guest layout search directly resolves source encodability.
// - Summary:
//   - Preserve deterministic history selection across equal-state paths.

use super::super::pair_source_cells;
use super::*;

#[test]
fn equal_state_collision_keeps_rotation_candidate() -> Result<(), String> {
    // A zero operand gives an identical accumulator for rotation/no-op,
    // but the decoded code bytes and memory writes are not equivalent.
    // Retain the first candidate pending independent positional VM proof.
    let states = BTreeMap::from([((0usize, 0u32), 0usize)]);
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let successors = append_successors(
        &states,
        &mut steps,
        SearchWord {
            remaining: 2,
            target_emitted: 1,
            value: 0,
            next_value: Some(0),
            next_next_value: None,
            next_next_next_value: None,
            fourth_future_value: None,
        },
        [0],
    );
    let step = steps
        .get(*successors.get(&(0, 0)).ok_or("missing zero state")?)
        .ok_or("missing predecessor history")?;
    if step.operation != LinearOpcode::RotateData {
        return Err(format!(
            "equal-state merge rewrote candidate history: {:?}",
            step.operation
        ));
    }
    Ok(())
}

#[test]
fn later_no_op_does_not_rewrite_existing_candidate() -> Result<(), String> {
    // Another exact-word predecessor can leave the accumulator intact
    // after an earlier rotation reached the same state. The histories
    // differ in guest writes and source encoding; do not silently swap them.
    let rotated = HIGH_TRIT_WEIGHT;
    let states =
        BTreeMap::from([((0usize, 0u32), 0usize), ((0usize, rotated), 1usize)]);
    let mut steps = vec![
        SearchStep {
            operation: LinearOpcode::NoOperation,
            predecessor: 0,
        },
        SearchStep {
            operation: LinearOpcode::NoOperation,
            predecessor: 0,
        },
    ];
    let successors = append_successors(
        &states,
        &mut steps,
        SearchWord {
            remaining: 2,
            target_emitted: 1,
            value: 1,
            next_value: Some(0),
            next_next_value: None,
            next_next_next_value: None,
            fourth_future_value: None,
        },
        [0],
    );
    let step = steps
        .get(
            *successors
                .get(&(0, rotated))
                .ok_or("missing rotated word")?,
        )
        .ok_or("missing path history")?;
    assert_eq!(step.operation, LinearOpcode::RotateData);
    assert_eq!(step.predecessor, 0);
    Ok(())
}

#[test]
fn no_op_zero_source_runs_without_data_writes() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or("no graphical positional source encodings")?;
    // These two candidate shapes both leave the accumulator at zero for
    // a zero operand, but the unrelocated rotation would write source code.
    // The independent layout and two-input normative VM accept only no-op.
    let unchanged = [
        LinearOpcode::NoOperation,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ];
    let source =
        verified_output_stream_layout(profile, &unchanged, [0], &cells)
            .ok_or("real zero-output no-op guest was rejected")?;
    assert!(source.data_write_positions().iter().all(Option::is_none));
    let writing = [
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ];
    assert!(
        verified_output_stream_layout(profile, &writing, [0], &cells).is_none()
    );
    Ok(())
}
