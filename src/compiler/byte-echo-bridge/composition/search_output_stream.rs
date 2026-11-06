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
//   - Bounded state-space proposals for source-proven guest byte streams.
// - Must-Not:
//   - Publish a proposal without independent layout and normative VM proof.
// - Allows:
//   - Inputs: canonical current-profile decoder phases and expected bytes.
//   - Outputs: one optional bounded linear guest proposal.
//   - Side effects: none.
// - Split-When:
//   - General layout synthesis becomes an independently owned algorithm.
// - Merge-When:
//   - The production verifier directly consumes equivalent search proposals.
// - Summary:
//   - Search byte effects by guest accumulator state, not fixture identity.

//! Bounded, deterministic proposals for relocated linear guest byte streams.

use std::collections::BTreeMap;

use super::{
    HIGH_TRIT_WEIGHT, LinearLayout, LinearOpcode, ProfileDescriptor,
    cached_output_tail, verified_output_stream_layout,
};

// Source address relocation uses a graphical code byte in 33..=126.
// Every data write must be outside the entire source. State and work bounds
// prevent unpredictable negative-case search amplification.
const MAX_SOURCE_LENGTH: usize = 94;
const MAX_STATES_PER_POSITION: usize = 16_384;
const MAX_STEPS_PER_GEOMETRY: usize = 700_000;

/// Every step owns one already-synthesized instruction and its predecessor.
/// A per-position state retains only one path for each output index and exact
/// accumulator word; no source bytes are admitted by this proposal structure.
struct SearchStep {
    operation: LinearOpcode,
    predecessor: usize,
}

type SearchStates = BTreeMap<(usize, u32), usize>;

struct SearchGeometry<'memory> {
    memory: &'memory [u32],
    prefix: usize,
    source_length: usize,
}

#[derive(Clone, Copy)]
struct SearchWord {
    remaining: usize,
    value: u32,
}

fn matches_byte(accumulator: u32, expected: u8) -> bool {
    u8::try_from(accumulator & 255).ok() == Some(expected)
}

fn append_successors<const N: usize>(
    states: &SearchStates,
    steps: &mut Vec<SearchStep>,
    word: SearchWord,
    expected: [u8; N],
) -> SearchStates {
    let SearchWord { value, remaining } = word;
    let mut successors = BTreeMap::new();
    let rotated = value
        .div_euclid(3)
        .saturating_add(value.rem_euclid(3).saturating_mul(HIGH_TRIT_WEIGHT));
    for (&(emitted, accumulator), &predecessor) in states {
        let crazy = malbolge::profile_crazy(value, accumulator, 15);
        for (operation, count, candidate_accumulator) in [
            (LinearOpcode::CrazyData, emitted, crazy),
            (LinearOpcode::RotateData, emitted, rotated),
            (LinearOpcode::NoOperation, emitted, accumulator),
            (
                LinearOpcode::OutputByte,
                emitted.saturating_add(1),
                accumulator,
            ),
        ] {
            if operation == LinearOpcode::OutputByte
                && (emitted >= N.saturating_sub(1)
                    || !expected
                        .get(emitted)
                        .is_some_and(|&byte| matches_byte(accumulator, byte)))
            {
                continue;
            }
            if count.saturating_add(remaining) < N.saturating_sub(1)
                || successors.contains_key(&(count, candidate_accumulator))
            {
                continue;
            }
            let index = steps.len();
            steps.push(SearchStep { operation, predecessor });
            let _previous =
                successors.insert((count, candidate_accumulator), index);
        }
    }
    successors
}

fn proposed_geometry<const N: usize>(
    source_cells: &[[u8; 6]],
    geometry: &SearchGeometry<'_>,
    expected: [u8; N],
) -> Option<Vec<LinearOpcode>> {
    let SearchGeometry {
        memory,
        prefix,
        source_length,
    } = *geometry;
    let relocation = usize::from(*source_cells.get(prefix)?.get(1)?);
    if relocation < source_length
        || relocation.saturating_add(source_length) >= 4096
        || source_length < prefix.saturating_add(4)
    {
        return None;
    }
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let mut states = BTreeMap::from([((0usize, 0u32), 0usize)]);
    // The final output/halt pair fixes the loader-expanded tail.
    for position in prefix.saturating_add(1)..source_length.saturating_sub(2) {
        let address =
            relocation.saturating_add(position).saturating_sub(prefix);
        let remaining =
            source_length.saturating_sub(position).saturating_sub(3);
        states = append_successors(
            &states,
            &mut steps,
            SearchWord {
                remaining,
                value: *memory.get(address)?,
            },
            expected,
        );
        if states.is_empty()
            || states.len() > MAX_STATES_PER_POSITION
            || steps.len() > MAX_STEPS_PER_GEOMETRY
        {
            return None;
        }
    }
    let target = expected.last().copied()?;
    let (_, &last_index) = states.iter().find(|(key, _)| {
        key.0 == N.saturating_sub(1) && matches_byte(key.1, target)
    })?;
    let mut cursor = last_index;
    let mut suffix = Vec::with_capacity(source_length.saturating_sub(prefix));
    while cursor != 0 {
        let step = steps.get(cursor)?;
        suffix.push(step.operation);
        cursor = step.predecessor;
    }
    suffix.reverse();
    let mut operations = vec![LinearOpcode::NoOperation; prefix];
    operations.push(LinearOpcode::RelocateDataPointer);
    operations.extend(suffix);
    operations.extend([LinearOpcode::OutputByte, LinearOpcode::Halt]);
    (operations.len() == source_length).then_some(operations)
}

/// Try a complete output stream with no count-specific hard-coded bytes.
///
/// This is only a proposal grammar: all accepted code is independently
/// decoded, checked for disjoint writes and replayed in the normative VM.
/// Search exhaustion is not a proof of guest-language impossibility.
pub(super) fn verified_state_space_output_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    if N == 0 {
        return None;
    }
    let mut memory_by_length = BTreeMap::new();
    for length in N.saturating_add(4)..=MAX_SOURCE_LENGTH {
        let max_prefix = length.saturating_sub(N.saturating_add(3)).min(30);
        for prefix in 0..=max_prefix {
            let relocation = usize::from(*source_cells.get(prefix)?.get(1)?);
            if relocation < length || relocation.saturating_add(length) >= 4096
            {
                continue;
            }
            let memory = cached_output_tail(
                source_cells,
                &mut memory_by_length,
                length,
                relocation.saturating_add(length),
            )?;
            let Some(operations) = proposed_geometry(
                source_cells,
                &SearchGeometry {
                    memory,
                    prefix,
                    source_length: length,
                },
                expected,
            ) else {
                continue;
            };
            if let Some(layout) = verified_output_stream_layout(
                profile,
                &operations,
                expected,
                source_cells,
            ) {
                return Some(layout);
            }
        }
    }
    None
}
