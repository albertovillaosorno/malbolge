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
use std::iter::repeat_n;

use super::{
    HIGH_TRIT_WEIGHT, LinearLayout, LinearOpcode, ProfileDescriptor,
    cached_output_tail, verified_output_stream_layout,
};

// Source address relocation uses a graphical code byte in 33..=126.
// Every data write must be outside the entire source. State and work bounds
// prevent unpredictable negative-case search amplification.
// Decoder phases wrap after 94 code cells. The second partial phase offers
// different loader-tail seeds but costs extra work for every rejected stream.
// Explore the full graphical relocation bound (126 source cells), with
// deterministic caps on the state search for each layout geometry.
const MAX_SOURCE_LENGTH: usize = 126;
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
    prefix_outputs: usize,
    source_length: usize,
}

#[derive(Clone, Copy)]
struct SearchWord {
    remaining: usize,
    target_emitted: usize,
    value: u32,
    next_value: u32,
    next_next_value: u32,
}

struct BeamRepresentatives {
    smallest: u32,
    largest: u32,
    next_smallest: Option<u32>,
    next_largest: Option<u32>,
    delayed_smallest: Option<u32>,
    delayed_largest: Option<u32>,
}

#[derive(Clone, Copy)]
enum TerminalSuffix {
    Crazy,
    Noop,
    Output,
    Rotate,
}

impl TerminalSuffix {
    const fn before_halt(self) -> (LinearOpcode, usize) {
        match self {
            Self::Output => (LinearOpcode::OutputByte, 4),
            Self::Noop => (LinearOpcode::NoOperation, 0),
            Self::Crazy => (LinearOpcode::CrazyData, 2),
            Self::Rotate => (LinearOpcode::RotateData, 3),
        }
    }

    const fn emitted_before_tail(self, total: usize) -> usize {
        match self {
            Self::Output => total.saturating_sub(1),
            Self::Noop | Self::Crazy | Self::Rotate => total,
        }
    }
}

fn matches_byte(accumulator: u32, expected: u8) -> bool {
    u8::try_from(accumulator & 255).ok() == Some(expected)
}

/// A change of output byte needs at least one genuine guest arithmetic write.
/// Repeated outputs may reuse the accumulator, including its initial zero.
fn required_writes(mut previous: u8, outputs: &[u8]) -> usize {
    let mut writes = 0;
    for &byte in outputs {
        if byte != previous {
            writes += 1;
            previous = byte;
        }
    }
    writes
}

fn can_fit_effects(available: usize, accumulator: u8, outputs: &[u8]) -> bool {
    outputs
        .len()
        .saturating_add(required_writes(accumulator, outputs))
        <= available
}

fn append_successors<const N: usize>(
    states: &SearchStates,
    steps: &mut Vec<SearchStep>,
    word: SearchWord,
    expected: [u8; N],
) -> SearchStates {
    let SearchWord {
        value,
        next_value,
        next_next_value,
        remaining,
        target_emitted,
    } = word;
    let mut proposals = BTreeMap::new();
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
                && (emitted >= target_emitted
                    || !expected
                        .get(emitted)
                        .is_some_and(|&byte| matches_byte(accumulator, byte)))
            {
                continue;
            }
            // For long streams, every remaining output costs one instruction;
            // each byte transition costs an additional p/* write.
            // A shortage is impossible to repair with padding or high trits.
            let pending = &expected[count..target_emitted];
            if (target_emitted >= 8
                && !can_fit_effects(
                    remaining,
                    candidate_accumulator as u8,
                    pending,
                ))
                || proposals.contains_key(&(count, candidate_accumulator))
            {
                continue;
            }
            let _previous =
                proposals.insert((count, candidate_accumulator), SearchStep {
                    operation,
                    predecessor,
                });
        }
    }
    // The low byte determines an output effect, but p observes the entire
    // fifteen-trit accumulator. In addition to the extreme full words,
    // preserve extreme words whose next p write reaches the pending byte.
    // Also preserve states that require one no-op before that write: the
    // next loader word can miss a byte which the word after it can reach.
    // The beam remains bounded and can miss longer or multi-write paths.
    if target_emitted >= 8 {
        let mut representatives =
            BTreeMap::<(usize, u8), BeamRepresentatives>::new();
        for &(emitted, accumulator) in proposals.keys() {
            let group = representatives
                .entry((emitted, accumulator as u8))
                .or_insert(BeamRepresentatives {
                    smallest: accumulator,
                    largest: accumulator,
                    next_smallest: None,
                    next_largest: None,
                    delayed_smallest: None,
                    delayed_largest: None,
                });
            group.largest = accumulator;
            if expected.get(emitted).is_some_and(|&byte| {
                byte != accumulator as u8
                    && matches_byte(
                        malbolge::profile_crazy(next_value, accumulator, 15),
                        byte,
                    )
            }) {
                let _previous = group.next_smallest.get_or_insert(accumulator);
                group.next_largest = Some(accumulator);
            }
            // After this instruction, a no-op and p must still leave an
            // instruction for the requested output. No-op advances D
            // without changing A, so use the actual later loader word.
            if remaining >= 3
                && expected.get(emitted).is_some_and(|&byte| {
                    byte != accumulator as u8
                        && matches_byte(
                            malbolge::profile_crazy(
                                next_next_value,
                                accumulator,
                                15,
                            ),
                            byte,
                        )
                })
            {
                let _previous =
                    group.delayed_smallest.get_or_insert(accumulator);
                group.delayed_largest = Some(accumulator);
            }
        }
        proposals.retain(|&(emitted, accumulator), _| {
            representatives
                .get(&(emitted, accumulator as u8))
                .is_some_and(|group| {
                    accumulator == group.smallest
                        || accumulator == group.largest
                        || group.next_smallest == Some(accumulator)
                        || group.next_largest == Some(accumulator)
                        || group.delayed_smallest == Some(accumulator)
                        || group.delayed_largest == Some(accumulator)
                })
        });
    }
    // Record only retained paths: candidate fan-out is not a completed
    // search step, and discards must not exhaust the history budget.
    let mut successors = BTreeMap::new();
    for (key, step) in proposals {
        let index = steps.len();
        steps.push(step);
        let _previous = successors.insert(key, index);
    }
    successors
}

fn reconstruct_path(
    steps: &[SearchStep],
    last_index: usize,
    geometry: &SearchGeometry<'_>,
    terminal: TerminalSuffix,
) -> Option<Vec<LinearOpcode>> {
    let mut cursor = last_index;
    let mut suffix = Vec::with_capacity(
        geometry.source_length.saturating_sub(geometry.prefix),
    );
    while cursor != 0 {
        let step = steps.get(cursor)?;
        suffix.push(step.operation);
        cursor = step.predecessor;
    }
    suffix.reverse();
    let mut operations =
        vec![LinearOpcode::OutputByte; geometry.prefix_outputs];
    operations.extend(repeat_n(
        LinearOpcode::NoOperation,
        geometry.prefix.checked_sub(geometry.prefix_outputs)?,
    ));
    operations.push(LinearOpcode::RelocateDataPointer);
    operations.extend(suffix);
    // Once every byte is emitted, remaining body cells may be no-ops.
    // The final source cells still fix the loader-expanded memory tail.
    while operations.len() < geometry.source_length.saturating_sub(2) {
        operations.push(LinearOpcode::NoOperation);
    }
    operations.extend([terminal.before_halt().0, LinearOpcode::Halt]);
    (operations.len() == geometry.source_length).then_some(operations)
}

fn proposed_geometry<const N: usize>(
    source_cells: &[[u8; 6]],
    geometry: &SearchGeometry<'_>,
    expected: [u8; N],
    terminal: TerminalSuffix,
) -> Option<Vec<LinearOpcode>> {
    let SearchGeometry {
        memory,
        prefix,
        prefix_outputs,
        source_length,
    } = *geometry;
    let target_emitted = terminal.emitted_before_tail(N);
    if prefix_outputs > prefix
        || prefix_outputs > target_emitted
        || expected[..prefix_outputs].iter().any(|&byte| byte != 0)
    {
        return None;
    }
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
    let mut states = BTreeMap::from([((prefix_outputs, 0u32), 0usize)]);
    // The chosen terminal/halt pair fixes the expanded memory tail.
    let target = expected.last().copied()?;
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
                target_emitted,
                value: *memory.get(address)?,
                next_value: *memory.get(address.checked_add(1)?)?,
                next_next_value: *memory.get(address.checked_add(2)?)?,
            },
            expected,
        );
        // No subsequent body instruction needs to change the accumulator
        // after the output target is complete. No-op padding preserves both
        // guest bytes and the terminal source seed, and is independently
        // decoded and replayed before a candidate can be admitted.
        if let Some((_, &last_index)) = states.iter().find(|(key, _)| {
            key.0 == target_emitted
                && (!matches!(terminal, TerminalSuffix::Output)
                    || matches_byte(key.1, target))
        }) {
            return reconstruct_path(&steps, last_index, geometry, terminal);
        }
        if states.is_empty()
            || states.len() > MAX_STATES_PER_POSITION
            || steps.len() > MAX_STEPS_PER_GEOMETRY
        {
            return None;
        }
    }
    None
}

fn verified_terminal_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
    terminal: TerminalSuffix,
    maximum_length: usize,
    maximum_prefix: usize,
) -> Option<LinearLayout> {
    let mut tails = BTreeMap::new();
    // Only the last two source cells seed expansion beyond source.
    // These substituted cells are proposal-only: the independent verifier
    // re-encodes and replays the complete positional source.
    let mut preview_cells = source_cells.to_vec();
    let (_, tail_slot) = terminal.before_halt();
    if tail_slot != 4 {
        for cell in &mut preview_cells {
            let encoded = *cell.get(tail_slot)?;
            *cell.get_mut(4)? = encoded;
        }
    }
    // Once body output is complete, this proposal pads with no-ops.
    // Thus no arithmetic write separates the last two output effects.
    if N >= 8
        && matches!(terminal, TerminalSuffix::Output)
        && expected[N - 1] != expected[N - 2]
    {
        return None;
    }
    let leading_zeros = expected.iter().take_while(|&&byte| byte == 0).count();
    // Source length must hold N output instructions, at least one j and v,
    // the necessary changes from initial accumulator zero, and the fixed
    // terminal instruction (unless it is already the final output).
    let minimum_length = N
        .saturating_add(required_writes(0, &expected))
        .saturating_add(2)
        .saturating_add(usize::from(!matches!(
            terminal,
            TerminalSuffix::Output
        )));
    // Retain the established short-stream witness-selection order.
    let initial_length = if N >= 8 {
        minimum_length.max(N.saturating_add(4))
    } else {
        N.saturating_add(4)
    };
    for length in initial_length..=maximum_length.min(MAX_SOURCE_LENGTH) {
        let max_prefix = length
            .saturating_sub(N.saturating_add(3))
            .min(maximum_prefix);
        for prefix in 0..=max_prefix {
            // The prefix and fixed j/tail/v consume prefix + 3 cells.
            // Source-encoded initial-zero outputs may occupy prefix cells;
            // all other effects and required writes must fit in the body.
            let body_slots = length.checked_sub(prefix.checked_add(3)?)?;
            let target_emitted = terminal.emitted_before_tail(N);
            let max_prefix_outputs =
                leading_zeros.min(prefix).min(target_emitted);
            if N >= 8
                && !can_fit_effects(
                    body_slots,
                    0,
                    &expected[max_prefix_outputs..target_emitted],
                )
            {
                continue;
            }
            let relocation = usize::from(*source_cells.get(prefix)?.get(1)?);
            if relocation < length || relocation.saturating_add(length) >= 4096
            {
                continue;
            }
            let memory = cached_output_tail(
                &preview_cells,
                &mut tails,
                length,
                relocation.saturating_add(length),
            )?;
            // Try maximal useful initial-zero outputs first, preserving
            // the historical all-no-op prefix as the last candidate.
            let verified =
                (0..=max_prefix_outputs).rev().find_map(|prefix_outputs| {
                    if N >= 8
                        && !can_fit_effects(
                            body_slots,
                            0,
                            &expected[prefix_outputs..target_emitted],
                        )
                    {
                        return None;
                    }
                    let geometry = SearchGeometry {
                        memory,
                        prefix,
                        prefix_outputs,
                        source_length: length,
                    };
                    let operations = proposed_geometry(
                        source_cells,
                        &geometry,
                        expected,
                        terminal,
                    )?;
                    verified_output_stream_layout(
                        profile,
                        &operations,
                        expected,
                        source_cells,
                    )
                });
            if verified.is_some() {
                return verified;
            }
        }
    }
    None
}

/// Search a bounded straight-through arithmetic grammar for proven bytes.
///
/// Unlike the state-space search, this finite preview explores at most twelve
/// distinct guest writes with one output immediately after each write. Only
/// the source tail is cached; every successful proposal still goes through
/// independent positional admission and two normative VM executions.
pub(super) fn verified_straight_write_output_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    if N == 0 || N > 12 {
        return None;
    }
    let mut tails = BTreeMap::new();
    let width = N.checked_mul(2)?.checked_add(2)?;
    for prefix in 0usize..94 {
        let length = prefix.checked_add(width)?;
        if length > source_cells.len() {
            break;
        }
        let relocation = usize::from(*source_cells.get(prefix)?.get(1)?);
        if relocation < length || relocation.checked_add(width)? >= 4096 {
            continue;
        }
        let memory = cached_output_tail(
            source_cells,
            &mut tails,
            length,
            relocation.checked_add(width)?,
        )?;
        let writes = (0..N)
            .map(|index| {
                memory.get(relocation.checked_add(1 + 2 * index)?).copied()
            })
            .collect::<Option<Vec<_>>>()?;
        // Expand only byte-matching prefixes. The original bitmask scan
        // repeatedly recalculated the same first guest write thousands of
        // times, even after that first output had already mismatched.
        let mut candidates = vec![(0u32, 0usize)];
        for (index, (&word, &target)) in
            writes.iter().zip(&expected).enumerate()
        {
            let mut next = Vec::new();
            let rotated = word.div_euclid(3).saturating_add(
                word.rem_euclid(3).saturating_mul(HIGH_TRIT_WEIGHT),
            );
            for &(accumulator, mask) in &candidates {
                let crazy = malbolge::profile_crazy(word, accumulator, 15);
                for (candidate, rotated_bit) in
                    [(crazy, false), (rotated, true)]
                {
                    if matches_byte(candidate, target) {
                        next.push((
                            candidate,
                            if rotated_bit {
                                mask | (1 << index)
                            } else {
                                mask
                            },
                        ));
                    }
                }
            }
            candidates = next;
            if candidates.is_empty() {
                break;
            }
        }
        for (_, mask) in candidates {
            let mut operations = vec![LinearOpcode::NoOperation; prefix];
            operations.push(LinearOpcode::RelocateDataPointer);
            for index in 0..N {
                operations.extend([
                    if mask & (1 << index) == 0 {
                        LinearOpcode::CrazyData
                    } else {
                        LinearOpcode::RotateData
                    },
                    LinearOpcode::OutputByte,
                ]);
            }
            operations.push(LinearOpcode::Halt);
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
    for terminal in [
        TerminalSuffix::Output,
        TerminalSuffix::Noop,
        TerminalSuffix::Crazy,
        TerminalSuffix::Rotate,
    ] {
        if let Some(layout) = verified_terminal_layout(
            profile,
            expected,
            source_cells,
            terminal,
            MAX_SOURCE_LENGTH,
            30,
        ) {
            return Some(layout);
        }
    }
    None
}

/// Try short multi-effect guest traces without extending hostile-input cost.
///
/// Unlike a fixed `p`/output ladder, this bounded beam admits repeated
/// outputs and intervening arithmetic and no-op strides. The beam may miss
/// valid guests; its proposals never bypass independent positional and VM
/// verification. Longer geometries remain future linker work.
pub(super) fn verified_short_output_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    if N == 0 || N > 12 {
        return None;
    }
    verified_terminal_layout(
        profile,
        expected,
        source_cells,
        TerminalSuffix::Noop,
        36,
        12,
    )
}

#[cfg(test)]
#[path = "../../../../tests/compiler/bridge/alternate_terminal.rs"]
mod alternate_terminal_tests;
