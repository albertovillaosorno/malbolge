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
//   - Necessary remaining-instruction bounds for short output searches.
// - Must-Not:
//   - Turn search exhaustion into a guest-language impossibility claim.
// - Allows:
//   - Inputs: exact output bytes and one bounded synthesis frontier.
//   - Outputs: only states that can fit necessary guest byte effects.
//   - Side effects: none.
// - Split-When:
//   - A general admissible search lower-bound component is warranted.
// - Merge-When:
//   - All byte-stream search strategies share the same lower bound.
// - Summary:
//   - Short traces must not skip the output/write instruction bound.

use super::*;

#[test]
fn short_streams_drop_states_with_insufficient_remaining_instructions() {
    let states = BTreeMap::from([((0usize, 0u32), 0usize)]);
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let word = SearchWord {
        remaining: 4,
        target_emitted: 5,
        value: 0,
        next_value: 0,
        next_next_value: 0,
        next_next_next_value: 0,
        fourth_future_value: None,
    };
    // Five output instructions and at least four arithmetic changes are
    // required. An output at this position still cannot fit the suffix.
    let next = append_successors(&states, &mut steps, word, [0, 1, 2, 3, 4]);
    assert!(
        next.is_empty(),
        "impossible short-byte states must be pruned"
    );
}

#[test]
fn short_streams_retain_output_only_paths_at_the_exact_lower_bound() {
    let states = BTreeMap::from([((0usize, 0u32), 0usize)]);
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let word = SearchWord {
        remaining: 3,
        target_emitted: 4,
        value: 0,
        next_value: 0,
        next_next_value: 0,
        next_next_next_value: 0,
        fourth_future_value: None,
    };
    let next = append_successors(&states, &mut steps, word, [0, 0, 0, 0]);
    assert!(
        next.contains_key(&(1, 0)),
        "a matching first output leaves exactly three remaining outputs"
    );
    assert!(!next.contains_key(&(0, 0)), "no-op cannot fit four outputs");
}
