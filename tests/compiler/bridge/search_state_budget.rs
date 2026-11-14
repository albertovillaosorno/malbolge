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
//   - Dense source-independent output-search beam capacity regression.
// - Must-Not:
//   - Replace independent guest layout and VM admission with beam guesses.
// - Allows:
//   - Inputs: deterministic full-word states and future loader operands.
//   - Outputs: bounded proposal states with retained progress diversity.
//   - Side effects: none.
// - Split-When:
//   - The output beam becomes a standalone proposal algorithm.
// - Merge-When:
//   - The general guest search verifier subsumes bounded frontier tests.
// - Summary:
//   - A dense reachable beam never aborts because its hints exceed budget.

use super::*;

#[test]
fn dense_output_beam_stays_within_its_global_budget() {
    // A single progress/byte group may preserve up to ten different full
    // words. Their sum across twelve progress counts can exceed the global
    // state cap, although a useful smaller proposal beam still exists.
    let states = (0..12usize)
        .flat_map(|emitted| {
            (0u32..=255).flat_map(move |byte| {
                (0u32..180)
                    .map(move |high| ((emitted, high * 256 + byte), 0usize))
            })
        })
        .collect::<SearchStates>();
    let mut history = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let successors = append_successors(
        &states,
        &mut history,
        SearchWord {
            remaining: 20,
            target_emitted: 12,
            value: 1,
            next_value: Some(2),
            next_next_value: Some(3),
            next_next_next_value: Some(4),
            fourth_future_value: Some(5),
        },
        [17; 12],
    );
    assert!(!successors.is_empty());
    assert!(
        successors.len() <= MAX_STATES_PER_POSITION,
        "{} > {} proposal states",
        successors.len(),
        MAX_STATES_PER_POSITION,
    );
    assert_eq!(history.len(), 1 + successors.len());
    for emitted in 0..=12 {
        assert!(
            successors.keys().any(|&(progress, _)| progress == emitted),
            "lost all candidates at output progress {emitted}",
        );
    }
}
