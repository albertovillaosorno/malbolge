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

use std::collections::{BTreeMap, BTreeSet};
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
// A rejected completion may still succeed with later source-cell padding.
// Bound verifier work spent on complete proposals in each source geometry.
const MAX_COMPLETION_CHECKS_PER_GEOMETRY: usize = 4;

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
struct SplitSearchSpec<'geometry, 'memory> {
    additional_relocations: &'geometry [usize],
    geometry: &'geometry SearchGeometry<'memory>,
    step_budget: usize,
    terminal: TerminalSuffix,
}

#[derive(Clone, Copy)]
struct SearchWord {
    remaining: usize,
    target_emitted: usize,
    value: u32,
    next_value: Option<u32>,
    next_next_value: Option<u32>,
    next_next_next_value: Option<u32>,
    fourth_future_value: Option<u32>,
}

type ReachablePair = Option<(u32, u32)>;

struct BeamRepresentatives {
    largest: u32,
    reachable: [ReachablePair; 4],
    smallest: u32,
}

impl BeamRepresentatives {
    fn retains(&self, accumulator: u32) -> bool {
        accumulator == self.smallest
            || accumulator == self.largest
            || self.reachable.iter().flatten().any(|&(smallest, largest)| {
                accumulator == smallest || accumulator == largest
            })
    }
}

/// The only instructions that distinguish full accumulator words are p and
/// no-op: * replaces the accumulator with a value independent of its past.
/// Look ahead through real future loader words, bounded to four cells and
/// leaving one cell for the pending output instruction. These are beam hints,
/// not a claim that words with the same low byte are equivalent.
fn reachable_next_byte(
    accumulator: u32,
    future: &[u32],
    remaining: usize,
    target: u8,
) -> Option<usize> {
    let mut words = [accumulator; 16];
    let mut count = 1usize;
    for (offset, &data) in future
        .iter()
        .take(remaining.saturating_sub(1).min(4))
        .enumerate()
    {
        for index in 0..count {
            let previous = *words.get(index)?;
            let changed = malbolge::profile_crazy(data, previous, 15);
            if matches_byte(changed, target) {
                return Some(offset.saturating_add(1));
            }
            *words.get_mut(count.saturating_add(index))? = changed;
        }
        count = count.saturating_mul(2);
    }
    None
}

#[derive(Clone, Copy)]
enum TerminalSuffix {
    Crazy,
    Noop,
    Output,
    Relocate,
    Rotate,
}

impl TerminalSuffix {
    const fn before_halt(self) -> (LinearOpcode, usize) {
        match self {
            Self::Output => (LinearOpcode::OutputByte, 4),
            Self::Noop => (LinearOpcode::NoOperation, 0),
            Self::Crazy => (LinearOpcode::CrazyData, 2),
            Self::Rotate => (LinearOpcode::RotateData, 3),
            Self::Relocate => (LinearOpcode::RelocateDataPointer, 1),
        }
    }

    const fn emitted_before_tail(self, total: usize) -> usize {
        match self {
            Self::Output => total.saturating_sub(1),
            Self::Noop | Self::Crazy | Self::Rotate | Self::Relocate => total,
        }
    }
}

fn matches_byte(accumulator: u32, expected: u8) -> bool {
    u8::try_from(accumulator & 255).ok() == Some(expected)
}

// A data-pointer relocation reads the current word and then increments D.
// The operand may be the final graphical source word: the first subsequent
// arithmetic operation will read the first loader-expanded word instead.
fn points_into_loader_expansion(operand: usize, source_length: usize) -> bool {
    operand
        .checked_add(1)
        .is_some_and(|next_data| next_data >= source_length)
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
        next_next_next_value,
        fourth_future_value,
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
            // Every remaining output costs one instruction;
            // each byte transition costs an additional p/* write.
            // A shortage is impossible to repair with padding or high trits.
            let pending = &expected[count..target_emitted];
            if !can_fit_effects(remaining, candidate_accumulator as u8, pending)
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
    // An exact frontier below the state cap needs no heuristic pruning.
    // In particular, a valid next byte may require more than three
    // loader words, and the lookahead below cannot prove it unreachable.
    // Use bounded representatives only when the full frontier exceeds the
    // per-position budget; every resulting proposal is verified later.
    if proposals.len() > MAX_STATES_PER_POSITION {
        let mut representatives =
            BTreeMap::<(usize, u8), BeamRepresentatives>::new();
        for &(emitted, accumulator) in proposals.keys() {
            let byte = malbolge::profile_low_byte(accumulator);
            let group = representatives.entry((emitted, byte)).or_insert(
                BeamRepresentatives {
                    largest: accumulator,
                    reachable: [None; 4],
                    smallest: accumulator,
                },
            );
            group.largest = accumulator;
            // Equal pending outputs do not change the accumulator.
            // Preserve a state that can reach the next *different* byte,
            // even when one or more output instructions come first.
            // This is a heuristic hint, not a proof of future reachability.
            let Some(target) =
                expected.get(emitted..target_emitted).and_then(|pending| {
                    pending.iter().copied().find(|&target| target != byte)
                })
            else {
                continue;
            };
            let future = [
                next_value,
                next_next_value,
                next_next_next_value,
                fourth_future_value,
            ];
            // Missing operands are not zero-valued loader words. Stop at
            // the first unproven address rather than inventing a path.
            let known = future.iter().take_while(|word| word.is_some()).count();
            let values = future.map(Option::unwrap_or_default);
            let proven_future = &values[..known];
            let Some(distance) = reachable_next_byte(
                accumulator,
                proven_future,
                remaining,
                target,
            ) else {
                continue;
            };
            if let Some(slot) =
                group.reachable.get_mut(distance.saturating_sub(1))
            {
                match slot {
                    Some((_, largest)) => *largest = accumulator,
                    None => *slot = Some((accumulator, accumulator)),
                }
            }
        }
        proposals.retain(|&(emitted, accumulator), _| {
            representatives
                .get(&(emitted, malbolge::profile_low_byte(accumulator)))
                .is_some_and(|group| group.retains(accumulator))
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

fn proposed_geometry_with_budget_checked<const N: usize, T>(
    source_cells: &[[u8; 6]],
    geometry: &SearchGeometry<'_>,
    expected: [u8; N],
    terminal: TerminalSuffix,
    step_budget: usize,
    mut admit: impl FnMut(&[LinearOpcode]) -> Option<T>,
) -> Option<T> {
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
    if !points_into_loader_expansion(relocation, source_length)
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
    let mut completion_checks = 0usize;
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
                next_value: memory.get(address.checked_add(1)?).copied(),
                next_next_value: memory.get(address.checked_add(2)?).copied(),
                next_next_next_value: memory
                    .get(address.checked_add(3)?)
                    .copied(),
                fourth_future_value: memory
                    .get(address.checked_add(4)?)
                    .copied(),
            },
            expected,
        );
        // No subsequent body instruction needs to change the accumulator
        // after the output target is complete. No-op padding preserves both
        // guest bytes and the terminal source seed, and is independently
        // decoded and replayed before a candidate can be admitted.
        for (&(emitted, accumulator), &last_index) in &states {
            if emitted != target_emitted
                || (matches!(terminal, TerminalSuffix::Output)
                    && !matches_byte(accumulator, target))
            {
                continue;
            }
            let operations =
                reconstruct_path(&steps, last_index, geometry, terminal)?;
            if let Some(verified) = admit(&operations) {
                return Some(verified);
            }
            completion_checks += 1;
            if completion_checks >= MAX_COMPLETION_CHECKS_PER_GEOMETRY {
                return None;
            }
        }
        if states.is_empty()
            || states.len() > MAX_STATES_PER_POSITION
            || steps.len() > step_budget
        {
            return None;
        }
    }
    None
}

#[cfg(test)]
fn proposed_geometry_with_budget<const N: usize>(
    source_cells: &[[u8; 6]],
    geometry: &SearchGeometry<'_>,
    expected: [u8; N],
    terminal: TerminalSuffix,
    step_budget: usize,
) -> Option<Vec<LinearOpcode>> {
    proposed_geometry_with_budget_checked(
        source_cells,
        geometry,
        expected,
        terminal,
        step_budget,
        |operations| Some(operations.to_vec()),
    )
}

#[cfg(test)]
fn proposed_geometry<const N: usize>(
    source_cells: &[[u8; 6]],
    geometry: &SearchGeometry<'_>,
    expected: [u8; N],
    terminal: TerminalSuffix,
) -> Option<Vec<LinearOpcode>> {
    proposed_geometry_with_budget(
        source_cells,
        geometry,
        expected,
        terminal,
        MAX_STEPS_PER_GEOMETRY,
    )
}

fn split_unwritten_addresses<const N: usize>(
    profile: &'static ProfileDescriptor,
    source_cells: &[[u8; 6]],
    spec: &SplitSearchSpec<'_, '_>,
    expected: [u8; N],
) -> Option<(Vec<Option<usize>>, Vec<u8>)> {
    let SplitSearchSpec {
        geometry,
        additional_relocations,
        terminal,
        ..
    } = *spec;
    let SearchGeometry {
        prefix,
        prefix_outputs,
        source_length,
        ..
    } = *geometry;
    let target_emitted = terminal.emitted_before_tail(N);
    if prefix_outputs > prefix
        || prefix_outputs > target_emitted
        || expected
            .get(..prefix_outputs)?
            .iter()
            .any(|&byte| byte != 0)
        || !(1..=3).contains(&additional_relocations.len())
        || additional_relocations
            .first()
            .is_none_or(|&position| position <= prefix.saturating_add(1))
        || additional_relocations
            .last()
            .is_none_or(|&position| position >= source_length.saturating_sub(3))
        || additional_relocations.windows(2).any(|pair| {
            matches!(
                pair,
                [first, second] if first.saturating_add(1) >= *second
            )
        })
    {
        return None;
    }
    let memory_words = usize::try_from(profile.memory_words()).ok()?;
    let first_body = prefix.checked_add(1)?;
    let mut pointer =
        usize::from(*source_cells.get(prefix)?.get(1)?).checked_add(1)?;
    let (_, tail_slot) = terminal.before_halt();
    let mut source = vec![0u8; source_length];
    *source.get_mut(source_length.checked_sub(2)?)? = *source_cells
        .get(source_length.checked_sub(2)?)?
        .get(tail_slot)?;
    *source.get_mut(source_length.checked_sub(1)?)? =
        *source_cells.get(source_length.checked_sub(1)?)?.get(5)?;
    // Track every visited data address to keep future j operands untouched.
    // A no-op/output may revisit an earlier operand after relocation: it
    // does not write memory, and the independent verifier rechecks the
    // complete candidate's write footprint and actual VM trace.
    let mut reserved = BTreeSet::new();
    let mut addresses = vec![None; source_length];
    for position in first_body..source_length.saturating_sub(2) {
        if pointer < source_length || pointer >= memory_words {
            return None;
        }
        let untouched = reserved.insert(pointer);
        if additional_relocations.binary_search(&position).is_ok() {
            if !untouched {
                // This j may read a prior arithmetic write. Without a
                // path-specific memory version its operand is unknowable.
                return None;
            }
            let operand =
                super::layout::unwritten_loader_word(&source, pointer, profile)
                    .ok()?;
            pointer = usize::try_from(operand)
                .ok()?
                .checked_add(1)?
                .rem_euclid(memory_words);
        } else {
            *addresses.get_mut(position)? = Some(pointer);
            pointer = pointer.checked_add(1)?.rem_euclid(memory_words);
        }
    }
    Some((addresses, source))
}

// A later j changes D without changing A. Future crazy writes after that
// instruction consume the *relocated* loader words, not successive words
// from the preceding region. Skip j-only positions when forming beam hints.
// This is proposal guidance: the verifier still checks the complete guest.
fn future_split_words(
    addresses: &[Option<usize>],
    source: &[u8],
    profile: &ProfileDescriptor,
    position: usize,
) -> [Option<u32>; 4] {
    let mut future_addresses =
        addresses.iter().skip(position.saturating_add(1)).flatten();
    std::array::from_fn(|_| {
        let address = *future_addresses.next()?;
        super::layout::unwritten_loader_word(source, address, profile).ok()
    })
}

fn append_relocation_states(
    states: &SearchStates,
    steps: &mut Vec<SearchStep>,
) -> SearchStates {
    let mut successors = BTreeMap::new();
    for (&key, &predecessor) in states {
        let index = steps.len();
        steps.push(SearchStep {
            operation: LinearOpcode::RelocateDataPointer,
            predecessor,
        });
        let _previous = successors.insert(key, index);
    }
    successors
}

// Each extra live relocation re-seeds the next data region from an untouched
// loader word. Regions may contain no-ops, arithmetic and repeated outputs;
// the synthesis grammar does not assume one arithmetic write per byte effect.
fn proposed_split_geometry_with_budget_checked<const N: usize, T>(
    profile: &'static ProfileDescriptor,
    source_cells: &[[u8; 6]],
    spec: SplitSearchSpec<'_, '_>,
    expected: [u8; N],
    mut admit: impl FnMut(&[LinearOpcode]) -> Option<T>,
) -> Option<T> {
    let SplitSearchSpec {
        geometry,
        additional_relocations,
        terminal,
        step_budget,
    } = spec;
    let (addresses, source) =
        split_unwritten_addresses(profile, source_cells, &spec, expected)?;
    let SearchGeometry {
        prefix,
        prefix_outputs,
        source_length,
        ..
    } = *geometry;
    let first_body = prefix.checked_add(1)?;
    let target_emitted = terminal.emitted_before_tail(N);
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let mut states = BTreeMap::from([((prefix_outputs, 0u32), 0usize)]);
    let mut completion_checks = 0usize;
    for position in first_body..source_length.saturating_sub(2) {
        if additional_relocations.binary_search(&position).is_ok() {
            states = append_relocation_states(&states, &mut steps);
            continue;
        }
        let address = (*addresses.get(position)?)?;
        let remaining = source_length
            .saturating_sub(position.saturating_add(3))
            .saturating_sub(
                additional_relocations
                    .iter()
                    .filter(|&&future| future > position)
                    .count(),
            );
        let current =
            super::layout::unwritten_loader_word(&source, address, profile)
                .ok()?;
        let future = future_split_words(&addresses, &source, profile, position);
        states = append_successors(
            &states,
            &mut steps,
            SearchWord {
                remaining,
                target_emitted,
                value: current,
                next_value: future[0],
                next_next_value: future[1],
                next_next_next_value: future[2],
                fourth_future_value: future[3],
            },
            expected,
        );
        // Full output paths are still speculative: the positional decoder
        // and normative VM may reject one while accepting a later path.
        // Retry within this source geometry, with a finite verifier budget.
        if position > *additional_relocations.last()? {
            for (&(emitted, accumulator), &last_index) in &states {
                if emitted != target_emitted
                    || (matches!(terminal, TerminalSuffix::Output)
                        && !matches_byte(accumulator, *expected.last()?))
                {
                    continue;
                }
                let operations =
                    reconstruct_path(&steps, last_index, geometry, terminal)?;
                if let Some(verified) = admit(&operations) {
                    return Some(verified);
                }
                completion_checks += 1;
                if completion_checks >= MAX_COMPLETION_CHECKS_PER_GEOMETRY {
                    return None;
                }
            }
        }
        if states.is_empty()
            || states.len() > MAX_STATES_PER_POSITION
            || steps.len() > step_budget
        {
            return None;
        }
    }
    None
}

#[cfg(test)]
fn proposed_split_geometry_with_budget<const N: usize>(
    profile: &'static ProfileDescriptor,
    source_cells: &[[u8; 6]],
    spec: SplitSearchSpec<'_, '_>,
    expected: [u8; N],
) -> Option<Vec<LinearOpcode>> {
    proposed_split_geometry_with_budget_checked(
        profile,
        source_cells,
        spec,
        expected,
        |operations| Some(operations.to_vec()),
    )
}

fn verified_terminal_layout_range<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
    terminal: TerminalSuffix,
    length_floor: usize,
    maximum_length: usize,
    maximum_prefix: usize,
    step_budget: usize,
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
    // The body can end in a real data write before the terminal output.
    // Therefore the final output need not equal the previous body output.
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
    // Long zero-prefixed streams may fit in N+3 cells when the final
    // output is the terminal source instruction. Keep the historical
    // shorter-stream witness order, but do not exclude that valid layout.
    let initial_length = if N >= 8 {
        minimum_length
    } else {
        N.saturating_add(4)
    };
    let mut lengths = (initial_length.max(length_floor)
        ..=maximum_length.min(MAX_SOURCE_LENGTH))
        .collect::<Vec<_>>();
    if length_floor > 0 {
        // More room and later positional phases are preferred in a
        // separately bounded extension; preserve the baseline ordering.
        lengths.reverse();
    }
    for length in lengths {
        // Source-side leading zeros consume prefix cells instead of body
        // cells. The remaining body must hold every non-prefix output plus
        // its necessary accumulator changes, including any final output
        // supplied by the terminal opcode. Reserve a body cell even when
        // those effects fit entirely before relocation.
        let prefixable_zeros =
            leading_zeros.min(terminal.emitted_before_tail(N));
        let min_body_slots = terminal
            .emitted_before_tail(N)
            .saturating_sub(prefixable_zeros)
            .saturating_add(required_writes(0, &expected[prefixable_zeros..]))
            .max(1);
        let max_prefix = length
            .saturating_sub(min_body_slots.saturating_add(3))
            .min(maximum_prefix);
        let mut prefixes = (0..=max_prefix).collect::<Vec<_>>();
        if length_floor > 0 {
            prefixes.reverse();
        }
        for prefix in prefixes {
            // The prefix and fixed j/tail/v consume prefix + 3 cells.
            // Source-encoded initial-zero outputs may occupy prefix cells;
            // all other effects and required writes must fit in the body.
            let body_slots = length.checked_sub(prefix.checked_add(3)?)?;
            let target_emitted = terminal.emitted_before_tail(N);
            let max_prefix_outputs =
                leading_zeros.min(prefix).min(target_emitted);
            if !can_fit_effects(
                body_slots,
                0,
                &expected[max_prefix_outputs..target_emitted],
            ) {
                continue;
            }
            let relocation = usize::from(*source_cells.get(prefix)?.get(1)?);
            if !points_into_loader_expansion(relocation, length)
                || relocation.saturating_add(length) >= 4096
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
                    if !can_fit_effects(
                        body_slots,
                        0,
                        &expected[prefix_outputs..target_emitted],
                    ) {
                        return None;
                    }
                    let geometry = SearchGeometry {
                        memory,
                        prefix,
                        prefix_outputs,
                        source_length: length,
                    };
                    proposed_geometry_with_budget_checked(
                        source_cells,
                        &geometry,
                        expected,
                        terminal,
                        step_budget,
                        |operations| {
                            verified_output_stream_layout(
                                profile,
                                operations,
                                expected,
                                source_cells,
                            )
                        },
                    )
                });
            if verified.is_some() {
                return verified;
            }
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
    verified_terminal_layout_range(
        profile,
        expected,
        source_cells,
        terminal,
        0,
        maximum_length,
        maximum_prefix,
        MAX_STEPS_PER_GEOMETRY,
    )
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
        if !points_into_loader_expansion(relocation, length)
            || relocation.checked_add(width)? >= 4096
        {
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
        TerminalSuffix::Relocate,
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
    verified_two_relocation_write_layout(profile, expected, source_cells)
        .or_else(|| {
            verified_three_relocation_write_layout(
                profile,
                expected,
                source_cells,
            )
        })
        .or_else(|| {
            verified_four_relocation_write_layout(
                profile,
                expected,
                source_cells,
            )
        })
}

/// Search two live data regions without assuming one write per output.
///
/// This finite proposal search never authorizes publication: only independent
/// positional admission and normative VM replay may accept an artifact.
fn verified_split_relocation_output_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    if !(2..=12).contains(&N)
        || profile.id() != malbolge::current_profile().id()
    {
        return None;
    }
    let minimum = N
        .saturating_add(required_writes(0, &expected))
        .saturating_add(4);
    let mut attempts = 0usize;
    let mut compact_attempts = 0usize;
    for terminal in [
        TerminalSuffix::Noop,
        TerminalSuffix::Output,
        TerminalSuffix::Crazy,
        TerminalSuffix::Rotate,
    ] {
        // A separate small-source budget preserves every geometry from
        // the established descending scan if compact proposals all miss.
        let maximum = 52.min(source_cells.len());
        let compact_lengths =
            (minimum..=28.min(maximum)).map(|length| (length, true));
        let established_lengths =
            (minimum..=maximum).rev().map(|length| (length, false));
        for (length, compact_pass) in compact_lengths.chain(established_lengths)
        {
            for prefix in [8, 0, 4, 12, 16, 24] {
                if prefix + 6 >= length {
                    continue;
                }
                for second_position in (prefix + 2)..(length - 3) {
                    // The VM can output its initial zero directly from a
                    // graphical prefix before the first data relocation.
                    let leading_zeros = expected
                        .iter()
                        .take_while(|&&byte| byte == 0)
                        .count()
                        .min(prefix)
                        .min(terminal.emitted_before_tail(N));
                    for prefix_outputs in (0..=leading_zeros).rev() {
                        if compact_pass {
                            if compact_attempts >= 600 {
                                continue;
                            }
                            compact_attempts += 1;
                        } else {
                            attempts += 1;
                            if attempts > 1_500 {
                                return None;
                            }
                        }
                        let geometry = SearchGeometry {
                            memory: &[],
                            prefix,
                            prefix_outputs,
                            source_length: length,
                        };
                        let positions = [second_position];
                        let spec = SplitSearchSpec {
                            geometry: &geometry,
                            additional_relocations: &positions,
                            terminal,
                            step_budget: 16_384,
                        };
                        if let Some(layout) =
                            proposed_split_geometry_with_budget_checked(
                                profile,
                                source_cells,
                                spec,
                                expected,
                                |operations| {
                                    verified_output_stream_layout(
                                        profile,
                                        operations,
                                        expected,
                                        source_cells,
                                    )
                                },
                            )
                        {
                            return Some(layout);
                        }
                    }
                }
            }
        }
    }
    None
}

/// Bounded three-region beam fallback for guest streams with intervening
/// no-ops and repeated outputs. Its fixed geometry budget is a proposal
/// limit, never an assertion that unmatched streams cannot be implemented.
fn verified_three_split_relocation_output_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    if !(8..=12).contains(&N)
        || profile.id() != malbolge::current_profile().id()
    {
        return None;
    }
    // Three regions reserve code for their live j operands and for output
    // effects that may reuse an accumulator between real guest writes.
    let minimum = N
        .saturating_add(required_writes(0, &expected))
        .saturating_add(5);
    for terminal in [TerminalSuffix::Noop, TerminalSuffix::Output] {
        // The longer shape allows no-op strides to accumulate in an early
        // region, moving both later live relocations beyond balanced thirds.
        // Preserve the established short-geometry priority and work caps.
        for (length, [first_offset, second_offset]) in [
            (N.checked_mul(3)?.checked_add(4)?, [0, 0]),
            (N.checked_mul(3)?.checked_add(2)?, [0, 0]),
            (N.checked_mul(3)?.checked_add(6)?, [1, 1]),
            // Repeated outputs can remove multiple write cells while the
            // final data region still needs one extra stride. Explore a
            // compact, unequal split without replacing established shapes.
            (N.checked_mul(3)?, [0, 1]),
            // One extra no-op stride can shift the last relocation
            // independently of the first while keeping the guest compact.
            (N.checked_mul(3)?.checked_add(1)?, [0, 1]),
        ] {
            if length < minimum || length > source_cells.len() {
                continue;
            }
            for prefix in [8usize, 0, 4] {
                if prefix.saturating_add(9) >= length {
                    continue;
                }
                let body = length.checked_sub(prefix)?.checked_sub(3)?;
                let split_start = prefix.checked_add(1)?;
                let split_positions = [
                    split_start
                        .checked_add(body.div_euclid(3))?
                        .checked_add(first_offset)?,
                    split_start
                        .checked_add(body.checked_mul(2)?.div_euclid(3))?
                        .checked_add(second_offset)?,
                ];
                // Initial output instructions observe the VM's zero A
                // before the first j; they need no guest arithmetic write.
                // Previously the split proposer spent those prefix cells
                // exclusively on no-ops, missing a real source behavior.
                let leading_zeros = expected
                    .iter()
                    .take_while(|&&byte| byte == 0)
                    .count()
                    .min(prefix)
                    .min(terminal.emitted_before_tail(N));
                for prefix_outputs in (0..=leading_zeros).rev() {
                    let geometry = SearchGeometry {
                        memory: &[],
                        prefix,
                        prefix_outputs,
                        source_length: length,
                    };
                    let spec = SplitSearchSpec {
                        geometry: &geometry,
                        additional_relocations: &split_positions,
                        terminal,
                        step_budget: 32_768,
                    };
                    if let Some(layout) =
                        proposed_split_geometry_with_budget_checked(
                            profile,
                            source_cells,
                            spec,
                            expected,
                            |operations| {
                                verified_output_stream_layout(
                                    profile,
                                    operations,
                                    expected,
                                    source_cells,
                                )
                            },
                        )
                    {
                        return Some(layout);
                    }
                }
            }
        }
    }
    None
}

/// Explore four live data-pointer regions with outputs that may reuse A.
/// The extra source relocation can revisit an already read data cell as a
/// no-op/output, whereas each later j operand still must be untouched.
/// The prefix may output initial zero bytes or contain only no-ops; nonzero
/// first effects must follow an actual relocated arithmetic write.
/// This is a bounded proposal, never independent admission.
fn verified_four_split_relocation_output_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    if !(8..=12).contains(&N)
        || profile.id() != malbolge::current_profile().id()
    {
        return None;
    }
    // A longer compact shape can place an extra no-op immediately after
    // the first j, shifting the next two j operands independently of the
    // last. These are only proposal shapes, not admission rules.
    let prefix = 8usize;
    let leading_zeros = expected
        .iter()
        .take_while(|&&byte| byte == 0)
        .count()
        .min(prefix);
    for (length, offsets, quick_seed) in [
        // Terminal arithmetic changes the loader seed. Probe both known
        // split geometries before the original, more expensive fallback.
        (N.checked_mul(3)?.checked_add(2)?, [1, 1, 0], true),
        (N.checked_mul(3)?.checked_add(3)?, [2, 2, 0], true),
        (N.checked_mul(3)?.checked_add(2)?, [1, 1, 0], false),
        (N.checked_mul(3)?.checked_add(3)?, [2, 2, 0], false),
    ] {
        if length > source_cells.len()
            || length
                < N.saturating_add(required_writes(0, &expected))
                    .saturating_add(6)
        {
            continue;
        }
        let body = length.checked_sub(prefix)?.checked_sub(3)?;
        let start = prefix.checked_add(1)?;
        let positions = [
            start
                .checked_add(body.div_euclid(4))?
                .checked_add(offsets[0])?,
            start
                .checked_add(body.checked_mul(2)?.div_euclid(4))?
                .checked_add(offsets[1])?,
            start
                .checked_add(body.checked_mul(3)?.div_euclid(4))?
                .checked_add(offsets[2])?,
        ];
        // The source cell before halt is a real instruction. A terminal
        // output both supplies the last byte effect and changes the loader
        // seed, so the entire source must be re-verified for that variant.
        let terminals: &[(TerminalSuffix, usize)] = if quick_seed {
            &[(TerminalSuffix::Crazy, 64), (TerminalSuffix::Rotate, 64)]
        } else {
            &[
                (TerminalSuffix::Noop, 32_768),
                (TerminalSuffix::Output, 32_768),
            ]
        };
        for &(terminal, step_budget) in terminals {
            let layout = (0..=leading_zeros).rev().find_map(|prefix_outputs| {
                let geometry = SearchGeometry {
                    memory: &[],
                    prefix,
                    prefix_outputs,
                    source_length: length,
                };
                let spec = SplitSearchSpec {
                    additional_relocations: &positions,
                    geometry: &geometry,
                    step_budget,
                    terminal,
                };
                proposed_split_geometry_with_budget_checked(
                    profile,
                    source_cells,
                    spec,
                    expected,
                    |operations| {
                        verified_output_stream_layout(
                            profile,
                            operations,
                            expected,
                            source_cells,
                        )
                    },
                )
            });
            if layout.is_some() {
                return layout;
            }
        }
    }
    None
}

/// Search an acyclic source-scratch geometry after one forward code jump.
///
/// The initial `i` jumps over graphical no-op source cells. Before D reaches
/// the final skipped cell, every arithmetic instruction reads one untouched
/// padding word strictly behind C. The positional inverse decoder fixes each
/// operand, but the guest performs all crazy/rotate arithmetic itself. This
/// remains a bounded proposal; independent layout and VM checks decide.
pub(super) fn verified_source_scratch_output_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    if N == 0 || N > 12 || profile.id() != malbolge::current_profile().id() {
        return None;
    }
    let jump_cell = (33u8..=126).find(|&byte| {
        malbolge::decode_profile_instruction(u32::from(byte), 0) == Some(b'i')
    })?;
    let target = usize::from(jump_cell).checked_add(1)?;
    // The initial jump encrypts cell `target - 1` once. The guest may read
    // that already-encrypted scratch value; it never executes that cell.
    let body_limit = target.checked_sub(1)?;
    if body_limit < N || target > source_cells.len() {
        return None;
    }
    let mut states = BTreeMap::from([((0usize, 0u32), 0usize)]);
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    for index in 0..body_limit {
        let address = index.checked_add(1)?;
        let word = |offset: usize| {
            let at = address.checked_add(offset)?;
            let value = u32::from(*source_cells.get(at)?.first()?);
            if at == target - 1 {
                malbolge::encrypt_profile_cell(value)
            } else {
                Some(value)
            }
        };
        states = append_successors(
            &states,
            &mut steps,
            SearchWord {
                remaining: body_limit.saturating_sub(index.saturating_add(1)),
                target_emitted: N,
                value: word(0)?,
                next_value: word(1),
                next_next_value: word(2),
                next_next_next_value: word(3),
                fourth_future_value: word(4),
            },
            expected,
        );
        if let Some((_, &last)) = states.iter().find(|(key, _)| key.0 == N) {
            let mut body = Vec::new();
            let mut cursor = last;
            while cursor != 0 {
                let step = steps.get(cursor)?;
                body.push(step.operation);
                cursor = step.predecessor;
            }
            body.reverse();
            let mut operations = vec![LinearOpcode::NoOperation; target];
            *operations.first_mut()? = LinearOpcode::JumpForward {
                target: u32::try_from(target).ok()?,
            };
            operations.extend(body);
            operations.push(LinearOpcode::Halt);
            let layout =
                super::encode_linear_layout(profile, &operations).ok()?;
            // Scratch writes must be strictly behind the active code cell.
            for (code, write) in layout
                .executed_code_positions()
                .iter()
                .zip(layout.data_write_positions())
            {
                if write.is_some_and(|address| {
                    address >= *code || address >= layout.source().len() as u32
                }) {
                    return None;
                }
            }
            for input in [Vec::new(), vec![255, 0, 128]] {
                let mut vm = super::ProfileMachine::from_source(
                    profile,
                    layout.source(),
                    input,
                )
                .ok()?;
                if !matches!(vm.run(layout.executed_code_positions().len()),
                    Ok(super::RunOutcome::Terminated { steps, .. })
                        if steps == layout.executed_code_positions().len())
                    || vm.input_consumed() != 0
                    || vm.output() != expected
                {
                    return None;
                }
            }
            return Some(layout);
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

/// Give skipped forward-jump cells independent graphical data bytes.
///
/// The jump may follow reached no-ops or genuine initial-zero outputs.
/// Unlike fixed no-op padding, skipped data is never fetched as opcodes.
/// The guest reads them through D and really executes crazy/rotation writes
/// before each output. A bounded search retains the exact D phase with the
/// accumulator and tests up to five guest steps per effect. Source cells
/// still require valid loader opcodes even when skipped. Independent source
/// layout and two normative VM replays verify every accepted proposal.
pub(super) fn verified_variable_source_scratch_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
) -> Option<LinearLayout> {
    (0..=3).find_map(|jump_position| {
        let leading_zeros = expected
            .iter()
            .take_while(|&&byte| byte == 0)
            .count()
            .min(jump_position);
        (0..=leading_zeros).rev().find_map(|prefix_outputs| {
            verified_variable_source_scratch_at_jump(
                profile,
                expected,
                jump_position,
                prefix_outputs,
            )
        })
    })
}

fn verified_variable_source_scratch_at_jump<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    jump_position: usize,
    prefix_outputs: usize,
) -> Option<LinearLayout> {
    if prefix_outputs > jump_position
        || expected
            .get(..prefix_outputs)?
            .iter()
            .any(|&byte| byte != 0)
    {
        return None;
    }
    if N == 0 || N > 12 || profile.id() != malbolge::current_profile().id() {
        return None;
    }
    let jump_phase = u32::try_from(jump_position).ok()?;
    let jump_cell = (33u8..=126).find(|&byte| {
        malbolge::decode_profile_instruction(u32::from(byte), jump_phase)
            == Some(b'i')
    })?;
    let target = usize::from(jump_cell).checked_add(1)?;
    // No-ops before the jump move D forward. The jump encrypts target - 1;
    // leave it unused while selecting graphical scratch at D = jump + 1.
    let scratch_limit = target.checked_sub(jump_position)?.checked_sub(2)?;
    let source_cells = super::pair_source_cells(profile)?;
    // An unreachable source cell still must be loader-valid, but can
    // decode as a jump or input: those two bytes were missing from the
    // six-opcode reached-instruction cache. Resolve once per address,
    // rather than repeating 188 decodes for every candidate state.
    let operand_cells = source_cells
        .iter()
        .enumerate()
        .map(|(address, cells)| {
            let phase = u32::try_from(address).ok()?;
            let encoded = |opcode| {
                (33u8..=126).find(|&byte| {
                    malbolge::decode_profile_instruction(u32::from(byte), phase)
                        == Some(opcode)
                })
            };
            Some([
                cells[0],
                cells[1],
                cells[2],
                cells[3],
                cells[4],
                cells[5],
                encoded(b'i')?,
                encoded(profile.input_instruction())?,
            ])
        })
        .collect::<Option<Vec<_>>>()?;
    // Persist only predecessor indices. Copying full paths at every beam
    // successor multiplies the cost of complete, branch-derived C streams.
    #[derive(Clone, Copy)]
    struct ScratchLink {
        operation: LinearOpcode,
        operand: Option<u8>,
        predecessor: usize,
    }
    type ScratchStates = BTreeMap<(usize, u32), usize>;
    fn retain_first(
        states: &mut ScratchStates,
        links: &mut Vec<ScratchLink>,
        key: (usize, u32),
        predecessor: usize,
        operation: LinearOpcode,
        operand: Option<u8>,
    ) {
        if let std::collections::btree_map::Entry::Vacant(entry) =
            states.entry(key)
        {
            let index = links.len();
            links.push(ScratchLink {
                operation,
                operand,
                predecessor,
            });
            let _inserted = entry.insert(index);
        }
    }
    let mut links = vec![ScratchLink {
        operation: LinearOpcode::NoOperation,
        operand: None,
        predecessor: 0,
    }];
    // The same accumulator at different D phases has different future
    // graphical operands. Preserve both rather than merging by value alone.
    let mut states = ScratchStates::from([((0, 0u32), 0usize)]);
    for &byte in &expected[prefix_outputs..] {
        let mut frontier = states;
        let mut finished = ScratchStates::new();
        for depth in 0..=5 {
            for (&(length, accumulator), &predecessor) in &frontier {
                if matches_byte(accumulator, byte) && length < scratch_limit {
                    retain_first(
                        &mut finished,
                        &mut links,
                        (length + 1, accumulator),
                        predecessor,
                        LinearOpcode::OutputByte,
                        None,
                    );
                }
            }
            if depth == 5 {
                break;
            }
            let mut successors = ScratchStates::new();
            for (&(length, accumulator), &predecessor) in &frontier {
                if length.saturating_add(2) > scratch_limit {
                    continue;
                }
                let address =
                    jump_position.checked_add(length)?.checked_add(1)?;
                let options = operand_cells.get(address)?;
                retain_first(
                    &mut successors,
                    &mut links,
                    (length + 1, accumulator),
                    predecessor,
                    LinearOpcode::NoOperation,
                    None,
                );
                for &data in options {
                    let operand = u32::from(data);
                    for (operation, result) in [
                        (
                            LinearOpcode::CrazyData,
                            malbolge::profile_crazy(operand, accumulator, 15),
                        ),
                        (
                            LinearOpcode::RotateData,
                            malbolge::profile_rotate(
                                operand,
                                profile.memory_words(),
                            ),
                        ),
                    ] {
                        retain_first(
                            &mut successors,
                            &mut links,
                            (length + 1, result),
                            predecessor,
                            operation,
                            Some(data),
                        );
                    }
                }
            }
            frontier = successors;
            if frontier.is_empty() || frontier.len() > 50_000 {
                break;
            }
        }
        if finished.is_empty() {
            return None;
        }
        states = finished;
    }
    let (_, &last) = states.iter().min_by_key(|(key, _)| key.0)?;
    let mut cursor = last;
    let mut path = Vec::new();
    while cursor != 0 {
        let link = links.get(cursor)?;
        path.push((link.operation, link.operand));
        cursor = link.predecessor;
    }
    path.reverse();
    let mut operations = vec![LinearOpcode::NoOperation; target];
    for operation in operations.iter_mut().take(prefix_outputs) {
        *operation = LinearOpcode::OutputByte;
    }
    *operations.get_mut(jump_position)? = LinearOpcode::JumpForward {
        target: u32::try_from(target).ok()?,
    };
    for (index, (_, byte)) in path.iter().enumerate() {
        if let Some(byte) = byte {
            let address = jump_position.checked_add(index)?.checked_add(1)?;
            *operations.get_mut(address)? =
                LinearOpcode::SkippedDataByte { byte: u32::from(*byte) };
        }
    }
    operations.extend(path.into_iter().map(|(operation, _)| operation));
    operations.push(LinearOpcode::Halt);
    let layout = super::encode_linear_layout(profile, &operations).ok()?;
    if layout
        .data_write_positions()
        .iter()
        .flatten()
        .any(|&write| write >= layout.source().len() as u32)
    {
        return None;
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            super::ProfileMachine::from_source(profile, layout.source(), input)
                .ok()?;
        if !matches!(vm.run(layout.executed_code_positions().len()),
            Ok(super::RunOutcome::Terminated { steps, .. })
                if steps == layout.executed_code_positions().len())
            || vm.input_consumed() != 0
            || vm.output() != expected
        {
            return None;
        }
    }
    Some(layout)
}

/// Revisit one previously skipped source word after two real byte effects.
///
/// A first graphical rotation materializes a full-width word at `scratch`.
/// The next source byte then drives a real `j` back to that same address,
/// allowing a second rotation to consume the guest-evolved value. From there,
/// a bounded state search chooses fresh graphical operands for the final
/// arithmetic and output. This is a byte-parameterized proposal, not a
/// special-case transcript: the independent layout checker and normative VM
/// must admit every source and prove all three requested bytes.
pub(super) fn verified_revisited_source_scratch_triple(
    profile: &'static ProfileDescriptor,
    expected: [u8; 3],
) -> Option<LinearLayout> {
    if profile.id() != malbolge::current_profile().id() {
        return None;
    }
    let prefix = verified_variable_source_scratch_at_jump(
        profile,
        [expected[0], expected[1]],
        0,
        0,
    )?;
    let source = prefix.source();
    let target = usize::from(*source.first()?).checked_add(1)?;
    let mut vm =
        super::ProfileMachine::from_source(profile, source, Vec::new()).ok()?;
    let _ = vm
        .run(prefix.executed_code_positions().len().checked_sub(1)?)
        .ok()?;
    if vm.output() != &expected[..2] || vm.input_consumed() != 0 {
        return None;
    }
    let initial_data = usize::try_from(vm.registers().data_pointer).ok()?;
    if initial_data >= target || source.len() <= target {
        return None;
    }
    // Preserve the prefix's exact operands, including skipped loader-valid
    // jump/input bytes that are inert as code but active when D reads them.
    let mut prefix_operations = vec![LinearOpcode::NoOperation; source.len()];
    *prefix_operations.first_mut()? = LinearOpcode::JumpForward {
        target: u32::try_from(target).ok()?,
    };
    for (at, &byte) in source.iter().enumerate().take(target).skip(1) {
        prefix_operations[at] =
            LinearOpcode::SkippedDataByte { byte: u32::from(byte) };
    }
    for (at, &byte) in source.iter().enumerate().skip(target) {
        prefix_operations[at] = match malbolge::decode_profile_instruction(
            u32::from(byte),
            u32::try_from(at).ok()?,
        )? {
            b'o' => LinearOpcode::NoOperation,
            b'p' => LinearOpcode::CrazyData,
            b'*' => LinearOpcode::RotateData,
            b'<' => LinearOpcode::OutputByte,
            b'v' => LinearOpcode::Halt,
            _ => return None,
        };
    }
    if prefix_operations.pop()? != LinearOpcode::Halt {
        return None;
    }
    // Skipped source bytes may encode any of the eight loader opcodes, even
    // though they are never executed. Keep this fixed by source position.
    let operands = (0..target)
        .map(|at| {
            (33u8..=126)
                .filter(|&byte| {
                    matches!(
                        malbolge::decode_profile_instruction(
                            u32::from(byte),
                            u32::try_from(at).unwrap_or(u32::MAX),
                        ),
                        Some(
                            b'o' | b'j'
                                | b'p'
                                | b'*'
                                | b'i'
                                | b'v'
                                | b'<'
                                | b'/'
                        )
                    )
                })
                .collect::<Vec<_>>()
        })
        .collect::<Vec<_>>();
    #[derive(Clone, Copy)]
    struct Link {
        predecessor: usize,
        operation: LinearOpcode,
        operand: Option<u8>,
    }
    // A fixed D and A imply identical future behavior: save one predecessor
    // per accumulator instead of copying increasingly long operation paths.
    // Mid-gap revisits leave room for both the original prefix and fresh
    // tail operands. Check those high-yield geometries first; the bounded
    // search still considers the remaining safe source addresses.
    let mut scratch_positions =
        (initial_data.max(34)..target.saturating_sub(7)).collect::<Vec<_>>();
    let middle = target.saturating_mul(2) / 3;
    scratch_positions.sort_unstable_by_key(|&at| (at.abs_diff(middle), at));
    for scratch in scratch_positions {
        let jump_word = u8::try_from(scratch.checked_sub(1)?).ok()?;
        if !operands.get(scratch + 1)?.contains(&jump_word) {
            continue;
        }
        for &seed in operands.get(scratch)? {
            let rotated = malbolge::profile_rotate(
                u32::from(seed),
                profile.memory_words(),
            );
            let evolved =
                malbolge::profile_rotate(rotated, profile.memory_words());
            let mut links = vec![Link {
                predecessor: 0,
                operation: LinearOpcode::NoOperation,
                operand: None,
            }];
            let mut frontier = BTreeMap::from([(evolved, 0usize)]);
            for depth in 0..=5 {
                for (&accumulator, &last) in &frontier {
                    if !matches_byte(accumulator, expected[2]) {
                        continue;
                    }
                    let mut suffix = Vec::with_capacity(depth);
                    let mut cursor = last;
                    while cursor != 0 {
                        let link = links.get(cursor)?;
                        suffix.push((link.operation, link.operand));
                        cursor = link.predecessor;
                    }
                    suffix.reverse();
                    let mut operations = prefix_operations.clone();
                    operations[scratch] =
                        LinearOpcode::SkippedDataByte { byte: u32::from(seed) };
                    operations[scratch + 1] = LinearOpcode::SkippedDataByte {
                        byte: u32::from(jump_word),
                    };
                    for (index, (_, byte)) in suffix.iter().enumerate() {
                        if let Some(byte) = byte {
                            operations[scratch + index + 1] =
                                LinearOpcode::SkippedDataByte {
                                    byte: u32::from(*byte),
                                };
                        }
                    }
                    operations.extend(repeat_n(
                        LinearOpcode::NoOperation,
                        scratch.saturating_sub(initial_data),
                    ));
                    operations.extend([
                        LinearOpcode::RotateData,
                        LinearOpcode::RelocateDataPointer,
                        LinearOpcode::RotateData,
                    ]);
                    operations
                        .extend(suffix.iter().map(|(operation, _)| *operation));
                    operations
                        .extend([LinearOpcode::OutputByte, LinearOpcode::Halt]);
                    let Ok(layout) =
                        super::encode_linear_layout(profile, &operations)
                    else {
                        continue;
                    };
                    let steps = layout.executed_code_positions().len();
                    let verified = [Vec::new(), vec![255, 0, 128]]
                        .into_iter()
                        .all(|input| {
                            let vm = super::ProfileMachine::from_source(
                                profile,
                                layout.source(),
                                input,
                            );
                            let Ok(mut guest) = vm else {
                                return false;
                            };
                            let outcome = guest.run(steps);
                            let terminated = matches!(
                                outcome,
                                Ok(super::RunOutcome::Terminated {
                                    steps: actual,
                                    ..
                                }) if actual == steps
                            );
                            terminated
                                && guest.output() == expected
                                && guest.input_consumed() == 0
                        });
                    if verified {
                        return Some(layout);
                    }
                }
                if depth == 5 {
                    break;
                }
                let at = scratch + depth + 1;
                let mut next = BTreeMap::new();
                for (&accumulator, &predecessor) in &frontier {
                    let word_options: &[u8] = if depth == 0 {
                        std::slice::from_ref(&jump_word)
                    } else {
                        operands.get(at)?
                    };
                    let mut insert = |result, operation, operand| {
                        if let std::collections::btree_map::Entry::Vacant(
                            entry,
                        ) = next.entry(result)
                        {
                            let id = links.len();
                            links.push(Link {
                                predecessor,
                                operation,
                                operand,
                            });
                            let _ = entry.insert(id);
                        }
                    };
                    insert(accumulator, LinearOpcode::NoOperation, None);
                    for &byte in word_options {
                        insert(
                            malbolge::profile_crazy(
                                u32::from(byte),
                                accumulator,
                                profile.word_trits(),
                            ),
                            LinearOpcode::CrazyData,
                            Some(byte),
                        );
                        insert(
                            malbolge::profile_rotate(
                                u32::from(byte),
                                profile.memory_words(),
                            ),
                            LinearOpcode::RotateData,
                            Some(byte),
                        );
                    }
                }
                if next.is_empty() || next.len() > 16_384 {
                    break;
                }
                frontier = next;
            }
        }
    }
    None
}

// Revisited source operands may vary with the path, so there is no sound
// fixed-word lookahead for this grammar. Before spending the rest of the
// frontier budget on the most advanced output count, retain both extremes
// of every achieved output-progress/low-byte group, including streams
// that already emitted their final byte. A completed stream may need further
// no-op padding before a position-encoded halt passes independent admission.
// The full accumulator remains in the key; guest verification is unchanged.
fn bounded_revisit_states<T: Copy>(
    states: &BTreeMap<(usize, u32), T>,
    minimum_emitted: usize,
    maximum_emitted: usize,
    limit: usize,
) -> BTreeMap<(usize, u32), T> {
    let mut extremes = BTreeMap::<(usize, u8), (u32, u32)>::new();
    for &(emitted, accumulator) in states.keys() {
        if emitted < minimum_emitted || emitted > maximum_emitted {
            continue;
        }
        let group = extremes
            .entry((emitted, malbolge::profile_low_byte(accumulator)))
            .or_insert((accumulator, accumulator));
        group.1 = accumulator;
    }
    // A future crazy write can distinguish full words sharing an output
    // byte. Protect one word near the middle of each class's available
    // full-word range, before the per-progress quota fills with low words.
    let mut middles = extremes
        .iter()
        .map(|(&group, &(smallest, largest))| {
            (group, (smallest + (largest - smallest) / 2, smallest))
        })
        .collect::<BTreeMap<_, _>>();
    for &(emitted, accumulator) in states.keys() {
        let group = (emitted, malbolge::profile_low_byte(accumulator));
        if let Some((target, selected)) = middles.get_mut(&group) {
            if accumulator.abs_diff(*target) < selected.abs_diff(*target) {
                *selected = accumulator;
            }
        }
    }
    let active_counts = extremes
        .keys()
        .map(|&(emitted, _)| emitted)
        .collect::<BTreeSet<_>>();
    let mut bounded = BTreeMap::new();
    for ((emitted, byte), (smallest, largest)) in extremes.into_iter().rev() {
        let middle = middles
            .get(&(emitted, byte))
            .map_or(smallest, |&(_, value)| value);
        for accumulator in [smallest, middle, largest] {
            if bounded.len() >= limit {
                return bounded;
            }
            if let Some(&index) = states.get(&(emitted, accumulator)) {
                let _prior = bounded.insert((emitted, accumulator), index);
            }
        }
    }
    // Each active output-progress count may need a different full-word
    // continuation. Reserve a fair share of the remaining beam for middle
    // words at every count; extremes alone cannot represent them. Redistribute
    // unused shares in advanced-first order below, without changing the cap.
    let per_count = limit / active_counts.len().max(1);
    for &emitted in active_counts.iter().rev() {
        let already = bounded.range((emitted, 0)..=(emitted, u32::MAX)).count();
        let mut slots = per_count.saturating_sub(already);
        for (&key, &index) in states.range((emitted, 0)..=(emitted, u32::MAX)) {
            if slots == 0 || bounded.len() >= limit {
                break;
            }
            if let std::collections::btree_map::Entry::Vacant(entry) =
                bounded.entry(key)
            {
                let _inserted = entry.insert(index);
                slots -= 1;
            }
        }
    }
    // Near-complete paths still have first claim on genuinely unused space.
    for &emitted in active_counts.iter().rev() {
        for (&key, &index) in states.range((emitted, 0)..=(emitted, u32::MAX)) {
            if bounded.len() >= limit {
                return bounded;
            }
            let _prior = bounded.entry(key).or_insert(index);
        }
    }
    bounded
}

// Speculative successors are not reconstruction records. Discarded links
// otherwise accumulate at every searched source cell, even after beam pruning.
fn append_revisit_links<T: Copy>(
    links: &mut Vec<T>,
    candidates: BTreeMap<(usize, u32), T>,
    minimum_emitted: usize,
    maximum_emitted: usize,
    limit: usize,
) -> SearchStates {
    let retained = if candidates.len() > limit {
        bounded_revisit_states(
            &candidates,
            minimum_emitted,
            maximum_emitted,
            limit,
        )
    } else {
        candidates
    };
    let mut states = SearchStates::new();
    for (key, link) in retained {
        let index = links.len();
        links.push(link);
        let _prior = states.insert(key, index);
    }
    states
}

/// Explore one acyclic continuation after a proven source-cell revisit.
///
/// Every state carries the complete guest accumulator, rather than only its
/// output byte. Skipped source cells may supply fresh graphical operands;
/// executed and encrypted source cells instead retain their exact VM words.
/// Candidates receive independent positional admission and VM replay.
pub(super) fn verified_revisited_source_scratch_stream<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
) -> Option<LinearLayout> {
    if !(4..=12).contains(&N)
        || profile.id() != malbolge::current_profile().id()
    {
        return None;
    }
    let prefix = verified_revisited_source_scratch_triple(profile, [
        expected[0],
        expected[1],
        expected[2],
    ])?;
    let source = prefix.source();
    let target = usize::from(*source.first()?).checked_add(1)?;
    let mut vm =
        super::ProfileMachine::from_source(profile, source, Vec::new()).ok()?;
    let _ = vm
        .run(prefix.executed_code_positions().len().checked_sub(1)?)
        .ok()?;
    if vm.output() != &expected[..3] || vm.input_consumed() != 0 {
        return None;
    }
    let initial_data = usize::try_from(vm.registers().data_pointer).ok()?;
    let initial_accumulator = vm.registers().accumulator;
    if initial_data >= target || target >= source.len() {
        return None;
    }
    let last_code = source.len().checked_sub(1)?;
    let mut source_operations = Vec::with_capacity(source.len());
    source_operations.push(LinearOpcode::JumpForward {
        target: u32::try_from(target).ok()?,
    });
    for &byte in source.get(1..target)? {
        source_operations
            .push(LinearOpcode::SkippedDataByte { byte: u32::from(byte) });
    }
    for (position, &byte) in source.iter().enumerate().skip(target) {
        let code = malbolge::decode_profile_instruction(
            u32::from(byte),
            u32::try_from(position).ok()?,
        )?;
        source_operations.push(match code {
            b'o' => LinearOpcode::NoOperation,
            b'p' => LinearOpcode::CrazyData,
            b'*' => LinearOpcode::RotateData,
            b'j' => LinearOpcode::RelocateDataPointer,
            b'<' => LinearOpcode::OutputByte,
            b'v' => LinearOpcode::Halt,
            _ => return None,
        });
    }
    if source_operations.pop()? != LinearOpcode::Halt {
        return None;
    }
    // Read-only no-ops and outputs are insensitive to the source word at D.
    // Every other reached data read and every prior write pins its operand.
    let sensitive =
        prefix
            .executed_code_positions()
            .iter()
            .zip(prefix.data_pointer_positions())
            .take(prefix.executed_code_positions().len().checked_sub(1)?)
            .filter_map(|(&code, &data)| {
                let byte = *source.get(usize::try_from(code).ok()?)?;
                (!matches!(malbolge::decode_profile_instruction(
                u32::from(byte), code,
            ), Some(b'o' | b'<'))).then_some(data)
            })
            .collect::<BTreeSet<_>>();
    let written_data = prefix
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect::<BTreeSet<_>>();
    let jump_operands = (33u8..=126)
        .filter(|&byte| {
            let landing = usize::from(byte) + 1;
            landing >= 34
                && landing < initial_data
                && matches!(
                    malbolge::decode_profile_instruction(
                        u32::from(byte),
                        u32::try_from(initial_data).unwrap_or(u32::MAX),
                    ),
                    Some(b'o' | b'j' | b'p' | b'*' | b'i' | b'v' | b'<' | b'/')
                )
        })
        .collect::<Vec<_>>();
    for jump_operand in jump_operands {
        let suffix_start = usize::from(jump_operand) + 1;
        let mut starting_operations = source_operations.clone();
        starting_operations[initial_data] = LinearOpcode::SkippedDataByte {
            byte: u32::from(jump_operand),
        };
        starting_operations.push(LinearOpcode::RelocateDataPointer);
        #[derive(Clone, Copy)]
        struct Link {
            predecessor: usize,
            operation: LinearOpcode,
            operand: Option<u8>,
        }
        let mut links = vec![Link {
            predecessor: 0,
            operation: LinearOpcode::NoOperation,
            operand: None,
        }];
        let mut states =
            BTreeMap::from([((3usize, initial_accumulator), 0usize)]);
        for address in suffix_start..last_code {
            let slot = u32::try_from(address).ok()?;
            let fresh = address < target
                && !sensitive.contains(&slot)
                && !written_data.contains(&slot);
            let options = if fresh {
                (33u8..=126)
                    .filter(|&byte| {
                        matches!(
                            malbolge::decode_profile_instruction(
                                u32::from(byte),
                                slot,
                            ),
                            Some(
                                b'o' | b'j'
                                    | b'p'
                                    | b'*'
                                    | b'i'
                                    | b'v'
                                    | b'<'
                                    | b'/'
                            )
                        )
                    })
                    .collect::<Vec<_>>()
            } else {
                Vec::new()
            };
            let fixed = vm.memory_word(slot).ok()?;
            let mut next = BTreeMap::new();
            for (&(emitted, accumulator), &previous) in &states {
                let mut insert = |operation, value, operand| {
                    let new_emitted = emitted
                        + usize::from(operation == LinearOpcode::OutputByte);
                    if new_emitted > N
                        || !can_fit_effects(
                            last_code.saturating_sub(address + 1),
                            u8::try_from(value & 255).unwrap_or(0),
                            &expected[new_emitted..],
                        )
                        || next.contains_key(&(new_emitted, value))
                    {
                        return;
                    }
                    let _ = next.insert((new_emitted, value), Link {
                        predecessor: previous,
                        operation,
                        operand,
                    });
                };
                insert(LinearOpcode::NoOperation, accumulator, None);
                if emitted < N && matches_byte(accumulator, expected[emitted]) {
                    insert(LinearOpcode::OutputByte, accumulator, None);
                }
                if fresh {
                    for &operand in &options {
                        insert(
                            LinearOpcode::CrazyData,
                            malbolge::profile_crazy(
                                u32::from(operand),
                                accumulator,
                                profile.word_trits(),
                            ),
                            Some(operand),
                        );
                        insert(
                            LinearOpcode::RotateData,
                            malbolge::profile_rotate(
                                u32::from(operand),
                                profile.memory_words(),
                            ),
                            Some(operand),
                        );
                    }
                } else {
                    insert(
                        LinearOpcode::CrazyData,
                        malbolge::profile_crazy(
                            fixed,
                            accumulator,
                            profile.word_trits(),
                        ),
                        None,
                    );
                    insert(
                        LinearOpcode::RotateData,
                        malbolge::profile_rotate(fixed, profile.memory_words()),
                        None,
                    );
                }
            }
            for (&(emitted, _), &last) in &next {
                if emitted != N {
                    continue;
                }
                let mut suffix = Vec::new();
                let mut link = last;
                loop {
                    suffix.push((link.operation, link.operand));
                    if link.predecessor == 0 {
                        break;
                    }
                    link = *links.get(link.predecessor)?;
                }
                suffix.reverse();
                let mut operations = starting_operations.clone();
                for (at, &(operation, operand)) in suffix.iter().enumerate() {
                    if let Some(byte) = operand {
                        operations[suffix_start + at] =
                            LinearOpcode::SkippedDataByte {
                                byte: u32::from(byte),
                            };
                    }
                    operations.push(operation);
                }
                operations.push(LinearOpcode::Halt);
                let Ok(layout) =
                    super::encode_linear_layout(profile, &operations)
                else {
                    continue;
                };
                let accepted = [Vec::new(), vec![255, 0, 128]]
                    .into_iter()
                    .all(|input| {
                let Ok(mut guest) = super::ProfileMachine::from_source(
                    profile, layout.source(), input,
                ) else { return false; };
                matches!(guest.run(layout.executed_code_positions().len()),
                    Ok(super::RunOutcome::Terminated { steps, .. })
                        if steps == layout.executed_code_positions().len())
                    && guest.output() == expected
                    && guest.input_consumed() == 0
            });
                if accepted {
                    return Some(layout);
                }
            }
            // Exact high words at multiple output counts matter to later
            // crazy writes. Pruning is never an impossibility proof, and
            // only retained links consume permanent reconstruction history.
            states = append_revisit_links(&mut links, next, 3, N, 16_384);
            if states.is_empty() {
                break;
            }
        }
    }
    None
}

/// Continue a proven source-revisit stream with one new guest accumulator.
///
/// The third byte has already been computed using the same source cell
/// before and after a real data-pointer relocation. The following guest D
/// address is taken from the verified prefix layout, not inferred from the
/// requested bytes. A fresh skipped graphical source word may be rotated
/// after bounded no-op strides, producing an independently replayed fourth
/// output. Both the revisited write and the new output must remain genuine
/// guest effects; no C-side byte is copied into the emitted transcript.
pub(super) fn verified_revisited_source_scratch_quad(
    profile: &'static ProfileDescriptor,
    expected: [u8; 4],
) -> Option<LinearLayout> {
    if profile.id() != malbolge::current_profile().id() {
        return None;
    }
    let prefix = verified_revisited_source_scratch_triple(profile, [
        expected[0],
        expected[1],
        expected[2],
    ])?;
    let source = prefix.source();
    let target = usize::from(*source.first()?).checked_add(1)?;
    let last_data =
        usize::try_from(*prefix.data_pointer_positions().last()?).ok()?;
    if last_data == 0 || last_data >= target {
        return None;
    }
    let mut operations = source
        .iter()
        .enumerate()
        .map(|(address, &byte)| {
            if address == 0 {
                return Some(LinearOpcode::JumpForward {
                    target: u32::try_from(target).ok()?,
                });
            }
            if address < target {
                return Some(LinearOpcode::SkippedDataByte {
                    byte: u32::from(byte),
                });
            }
            match malbolge::decode_profile_instruction(
                u32::from(byte),
                u32::try_from(address).ok()?,
            )? {
                b'o' => Some(LinearOpcode::NoOperation),
                b'p' => Some(LinearOpcode::CrazyData),
                b'*' => Some(LinearOpcode::RotateData),
                b'j' => Some(LinearOpcode::RelocateDataPointer),
                b'<' => Some(LinearOpcode::OutputByte),
                b'v' => Some(LinearOpcode::Halt),
                _ => None,
            }
        })
        .collect::<Option<Vec<_>>>()?;
    if operations.pop()? != LinearOpcode::Halt {
        return None;
    }
    // The final D position belongs to the removed halt and was not read.
    // A new operand may only occupy unvisited, unmodified skipped source.
    let used_data = prefix
        .data_pointer_positions()
        .iter()
        .take(prefix.data_pointer_positions().len().saturating_sub(1))
        .copied()
        .collect::<BTreeSet<_>>();
    let written_data = prefix
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect::<BTreeSet<_>>();
    for stride in 0..target.saturating_sub(last_data).min(24) {
        let data = last_data.checked_add(stride)?;
        let address = u32::try_from(data).ok()?;
        if used_data.contains(&address) || written_data.contains(&address) {
            continue;
        }
        for byte in 33u8..=126 {
            if !matches_byte(
                malbolge::profile_rotate(
                    u32::from(byte),
                    profile.memory_words(),
                ),
                expected[3],
            ) || !matches!(
                malbolge::decode_profile_instruction(u32::from(byte), address,),
                Some(b'o' | b'j' | b'p' | b'*' | b'i' | b'v' | b'<' | b'/')
            ) {
                continue;
            }
            let mut candidate = operations.clone();
            *candidate.get_mut(data)? =
                LinearOpcode::SkippedDataByte { byte: u32::from(byte) };
            candidate.extend(repeat_n(LinearOpcode::NoOperation, stride));
            candidate.extend([
                LinearOpcode::RotateData,
                LinearOpcode::OutputByte,
                LinearOpcode::Halt,
            ]);
            let Ok(layout) = super::encode_linear_layout(profile, &candidate)
            else {
                continue;
            };
            let writes = layout
                .data_write_positions()
                .iter()
                .flatten()
                .copied()
                .collect::<Vec<_>>();
            if writes.iter().copied().collect::<BTreeSet<_>>().len() + 1
                != writes.len()
                || layout
                    .executed_code_positions()
                    .iter()
                    .zip(layout.data_write_positions())
                    .any(|(&code, &write)| write.is_some_and(|at| at >= code))
            {
                continue;
            }
            let accepted =
                [Vec::new(), vec![255, 0, 128]].into_iter().all(|input| {
                    let Ok(mut vm) = super::ProfileMachine::from_source(
                        profile,
                        layout.source(),
                        input,
                    ) else {
                        return false;
                    };
                    matches!(
                        vm.run(layout.executed_code_positions().len()),
                        Ok(super::RunOutcome::Terminated { steps, .. })
                            if steps == layout.executed_code_positions().len()
                    ) && vm.output() == expected
                        && vm.input_consumed() == 0
                });
            if accepted {
                return Some(layout);
            }
        }
    }
    None
}

/// Permit one forward data-pointer relocation within skipped graphical source
/// scratch. Each consumed operand is a fresh, previously unread source cell.
/// A relocation may skip ahead but never revisit a guest-written operand or
/// the cell encrypted by the initial jump. Candidate source and effects still
/// need independent positional-layout and normative VM verification.
/// This exploratory grammar is test-only until its negative-case cost and
/// complete-C applicability justify production adoption.
#[cfg(test)]
fn verified_relocated_source_scratch_at_jump<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    jump_position: usize,
) -> Option<LinearLayout> {
    if !(1..=3).contains(&N) || profile.id() != malbolge::current_profile().id()
    {
        return None;
    }
    let jump_phase = u32::try_from(jump_position).ok()?;
    let jump_cell = (33u8..=126).find(|&byte| {
        malbolge::decode_profile_instruction(u32::from(byte), jump_phase)
            == Some(b'i')
    })?;
    let target = usize::from(jump_cell).checked_add(1)?;
    let scratch_end = target.checked_sub(1)?;
    if scratch_end <= jump_position.checked_add(N.saturating_mul(2))? {
        return None;
    }
    let source_cells = super::pair_source_cells(profile)?;
    let operands = source_cells
        .iter()
        .enumerate()
        .map(|(position, cells)| {
            let phase = u32::try_from(position).ok()?;
            let opcode_byte = |opcode| {
                (33u8..=126).find(|&byte| {
                    malbolge::decode_profile_instruction(u32::from(byte), phase)
                        == Some(opcode)
                })
            };
            Some([
                cells[0],
                cells[1],
                cells[2],
                cells[3],
                cells[4],
                cells[5],
                opcode_byte(b'i')?,
                opcode_byte(profile.input_instruction())?,
            ])
        })
        .collect::<Option<Vec<_>>>()?;
    #[derive(Clone, Copy)]
    struct Link {
        opcode: LinearOpcode,
        operand: Option<(usize, u8)>,
        predecessor: usize,
    }
    type Key = (usize, u32, bool);
    type States = BTreeMap<Key, usize>;
    fn insert(
        states: &mut States,
        links: &mut Vec<Link>,
        key: Key,
        from: usize,
        opcode: LinearOpcode,
        operand: Option<(usize, u8)>,
    ) {
        if let std::collections::btree_map::Entry::Vacant(entry) =
            states.entry(key)
        {
            let id = links.len();
            links.push(Link {
                opcode,
                operand,
                predecessor: from,
            });
            let _ = entry.insert(id);
        }
    }
    let mut links = vec![Link {
        opcode: LinearOpcode::NoOperation,
        operand: None,
        predecessor: 0,
    }];
    let mut states = States::from([((jump_position + 1, 0u32, false), 0)]);
    for (emitted, &wanted) in expected.iter().enumerate() {
        let mut frontier = states;
        let mut completed = States::new();
        for depth in 0..=5 {
            for (&(data_at, accumulator, used), &prev) in &frontier {
                if data_at < scratch_end && matches_byte(accumulator, wanted) {
                    insert(
                        &mut completed,
                        &mut links,
                        (data_at + 1, accumulator, used),
                        prev,
                        LinearOpcode::OutputByte,
                        None,
                    );
                }
            }
            if depth == 5 {
                break;
            }
            let mut next = States::new();
            for (&(data_at, accumulator, used), &prev) in &frontier {
                if data_at.checked_add(2)? >= scratch_end {
                    continue;
                }
                insert(
                    &mut next,
                    &mut links,
                    (data_at + 1, accumulator, used),
                    prev,
                    LinearOpcode::NoOperation,
                    None,
                );
                for &byte in operands.get(data_at)? {
                    let word = u32::from(byte);
                    for (opcode, result) in [
                        (
                            LinearOpcode::CrazyData,
                            malbolge::profile_crazy(word, accumulator, 15),
                        ),
                        (
                            LinearOpcode::RotateData,
                            malbolge::profile_rotate(
                                word,
                                profile.memory_words(),
                            ),
                        ),
                    ] {
                        insert(
                            &mut next,
                            &mut links,
                            (data_at + 1, result, used),
                            prev,
                            opcode,
                            Some((data_at, byte)),
                        );
                    }
                    if !used {
                        let relocated = usize::from(byte) + 1;
                        if relocated > data_at + 1 && relocated < scratch_end {
                            insert(
                                &mut next,
                                &mut links,
                                (relocated, accumulator, true),
                                prev,
                                LinearOpcode::RelocateDataPointer,
                                Some((data_at, byte)),
                            );
                        }
                    }
                }
            }
            frontier = next;
            // This is a proposal search: exhausting the cap is not proof of
            // impossibility, and unverified candidates never reach the caller.
            if frontier.is_empty()
                || frontier.len() > 8_192
                || links.len() > 100_000
            {
                break;
            }
        }
        if completed.is_empty() {
            return None;
        }
        // The remaining outputs still need at least one source cell each.
        states = completed
            .into_iter()
            .filter(|(key, _)| {
                scratch_end.saturating_sub(key.0) >= N - emitted - 1
            })
            .collect();
        if states.is_empty() {
            return None;
        }
    }
    for (_, &last) in states.iter().filter(|(key, _)| key.2).take(64) {
        let mut path = Vec::new();
        let mut cursor = last;
        while cursor != 0 {
            let link = links.get(cursor)?;
            path.push((link.opcode, link.operand));
            cursor = link.predecessor;
        }
        path.reverse();
        let mut operations = vec![LinearOpcode::NoOperation; target];
        *operations.get_mut(jump_position)? = LinearOpcode::JumpForward {
            target: u32::try_from(target).ok()?,
        };
        for (_, operand) in &path {
            if let Some(&(at, byte)) = operand.as_ref() {
                *operations.get_mut(at)? =
                    LinearOpcode::SkippedDataByte { byte: u32::from(byte) };
            }
        }
        operations.extend(path.into_iter().map(|(opcode, _)| opcode));
        operations.push(LinearOpcode::Halt);
        let Ok(layout) = super::encode_linear_layout(profile, &operations)
        else {
            continue;
        };
        let valid = [Vec::new(), vec![255, 0, 128]].into_iter().all(|input| {
            let Ok(mut vm) = super::ProfileMachine::from_source(
                profile,
                layout.source(),
                input,
            ) else {
                return false;
            };
            matches!(
                vm.run(layout.executed_code_positions().len()),
                Ok(super::RunOutcome::Terminated { steps, .. })
                    if steps == layout.executed_code_positions().len()
            ) && vm.input_consumed() == 0
                && vm.output() == expected
        });
        if valid {
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
    // The final source opcode selects the loader seed. A real output can
    // follow a final body write, and need not repeat the preceding byte.
    // Preserve earlier witness order; every seed still needs independent
    // positional decoding and normative VM admission.
    [
        TerminalSuffix::Noop,
        TerminalSuffix::Crazy,
        TerminalSuffix::Rotate,
        TerminalSuffix::Output,
        TerminalSuffix::Relocate,
    ]
    .into_iter()
    .find_map(|terminal| {
        verified_terminal_layout(
            profile,
            expected,
            source_cells,
            terminal,
            36,
            12,
        )
    })
    .or_else(|| {
        if N == 12 {
            // Additional source positions can create different loader
            // words; bound this wider fallback more tightly than the
            // established 36-cell proposals.
            // A source-side terminal no-op also seeds distinct expanded
            // memory at these lengths. Preserve the established output,
            // crazy and rotation priorities before trying that seed.
            [
                TerminalSuffix::Output,
                TerminalSuffix::Crazy,
                TerminalSuffix::Rotate,
                TerminalSuffix::Noop,
            ]
            .into_iter()
            .find_map(|terminal| {
                verified_terminal_layout_range(
                    profile,
                    expected,
                    source_cells,
                    terminal,
                    37,
                    39,
                    8,
                    2_048,
                )
            })
        } else {
            None
        }
    })
    .or_else(|| {
        verified_two_relocation_write_layout(profile, expected, source_cells)
            .or_else(|| {
                verified_three_relocation_write_layout(
                    profile,
                    expected,
                    source_cells,
                )
            })
            .or_else(|| {
                verified_four_relocation_write_layout(
                    profile,
                    expected,
                    source_cells,
                )
            })
    })
    .or_else(|| {
        // Reserve additional fresh loader-data regions for long streams.
        // Keep the more expensive six-region scan behind the established
        // bounded searches, without widening shorter negative cases.
        let maximum_relocations = match N {
            12 => 6,
            10 | 11 => 5,
            _ => 4,
        };
        (5..=maximum_relocations).find_map(|relocations| {
            verified_relocated_write_layout(
                profile,
                expected,
                source_cells,
                relocations,
            )
        })
    })
    .or_else(|| {
        verified_split_relocation_output_layout(profile, expected, source_cells)
    })
    .or_else(|| {
        verified_three_split_relocation_output_layout(
            profile,
            expected,
            source_cells,
        )
    })
    .or_else(|| {
        verified_four_split_relocation_output_layout(
            profile,
            expected,
            source_cells,
        )
    })
}

/// Explore two genuine live data relocations separated by byte effects.
///
/// Each effect has an arithmetic write followed by an output. The second
/// `j` reads a fresh loader-tail operand, so its target is determined by the
/// source's last two cells rather than a host-selected destination. This is
/// only a bounded proposal; full layout/VM admission independently decides.
fn verified_two_relocation_write_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    if !(2..=12).contains(&N)
        || profile.id() != malbolge::current_profile().id()
    {
        return None;
    }
    let memory_words = usize::try_from(profile.memory_words()).ok()?;
    // The final output/halt cells are fixed for this geometry; all guest
    // writes and the second j operand read only untouched expanded memory.
    for prefix in 0..=32usize {
        let length = prefix.checked_add(N.checked_mul(2)?)?.checked_add(3)?;
        let first_base = usize::from(*source_cells.get(prefix)?.get(1)?);
        if !points_into_loader_expansion(first_base, length) {
            continue;
        }
        let mut source = vec![0u8; length];
        source[length - 2] = *source_cells.get(length - 2)?.get(4)?;
        source[length - 1] = *source_cells.get(length - 1)?.get(5)?;
        for split in 1..N {
            let second_operand = first_base.checked_add(1 + 2 * split)?;
            let second_base = usize::try_from(
                super::layout::unwritten_loader_word(
                    &source,
                    second_operand,
                    profile,
                )
                .ok()?,
            )
            .ok()?;
            let second_start = second_base.checked_add(1)? % memory_words;
            if second_start < length {
                continue;
            }
            let mut written = BTreeSet::new();
            let mut words = Vec::with_capacity(N);
            for index in 0..N {
                let address = if index < split {
                    first_base.checked_add(1 + 2 * index)?
                } else {
                    second_start.checked_add(2 * (index - split))?
                        % memory_words
                };
                if address < length || !written.insert(address) {
                    break;
                }
                words.push(
                    super::layout::unwritten_loader_word(
                        &source, address, profile,
                    )
                    .ok()?,
                );
            }
            if words.len() != N {
                continue;
            }
            let mut paths = vec![(0u32, 0u16)];
            for (index, (&word, &target)) in
                words.iter().zip(expected.iter()).enumerate()
            {
                let rotated = word / 3 + (word % 3) * HIGH_TRIT_WEIGHT;
                let mut next = Vec::new();
                for &(accumulator, mask) in &paths {
                    for (value, rotate) in [
                        (malbolge::profile_crazy(word, accumulator, 15), false),
                        (rotated, true),
                    ] {
                        if matches_byte(value, target) {
                            next.push((
                                value,
                                if rotate {
                                    mask | (1 << index)
                                } else {
                                    mask
                                },
                            ));
                        }
                    }
                }
                paths = next;
                if paths.is_empty() || paths.len() > 256 {
                    break;
                }
            }
            for (_, mask) in paths {
                let mut operations = vec![LinearOpcode::NoOperation; prefix];
                operations.push(LinearOpcode::RelocateDataPointer);
                for index in 0..N {
                    if index == split {
                        operations.push(LinearOpcode::RelocateDataPointer);
                    }
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
    }
    None
}

#[cfg(test)]
#[path = "../../../../tests/compiler/bridge/source_scratch.rs"]
mod source_scratch_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/bridge/alternate_terminal.rs"]
mod alternate_terminal_tests;
#[cfg(test)]
#[path = "../../../../tests/compiler/bridge/short_effect_lower_bound.rs"]
mod short_effect_lower_bound_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/bridge/repeated_relocation.rs"]
mod repeated_relocation_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/bridge/unmasked_fibonacci.rs"]
mod unmasked_fibonacci_tests;

/// Explore multiple live relocation regions using untouched loader words.
///
/// A split bit selects an additional `j` before the next arithmetic/output
/// pair. Every region must perform at least one real guest write and output;
/// no host-chosen D destinations, repeated writes, or source operands pass.
/// The proposal remains bounded to twelve effects and six relocation regions.
fn verified_relocated_write_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
    relocations: usize,
) -> Option<LinearLayout> {
    if !(3..=6).contains(&relocations)
        || !(3..=12).contains(&N)
        || relocations > N
        || profile.id() != malbolge::current_profile().id()
    {
        return None;
    }
    let memory_words = usize::try_from(profile.memory_words()).ok()?;
    for prefix in 0..=32usize {
        let length = prefix
            .checked_add(N.checked_mul(2)?)?
            .checked_add(relocations.checked_add(1)?)?;
        let first_base = usize::from(*source_cells.get(prefix)?.get(1)?);
        if !points_into_loader_expansion(first_base, length) {
            continue;
        }
        // The final output and halt independently fix the loader-tail seed.
        let mut source = vec![0u8; length];
        source[length - 2] = *source_cells.get(length - 2)?.get(4)?;
        source[length - 1] = *source_cells.get(length - 1)?.get(5)?;
        // N-1 possible internal splits; exact bit population bounds the
        // number of relocated regions without fixing the split positions.
        for splits in 1usize..(1usize << (N - 1)) {
            if usize::try_from(splits.count_ones()).ok()? != relocations - 1 {
                continue;
            }
            let mut address = (first_base + 1) % memory_words;
            let mut written = BTreeSet::new();
            let mut words = Vec::with_capacity(N);
            for index in 0..N {
                if index > 0 && (splits & (1 << (index - 1))) != 0 {
                    // A relocated `j` must not read a previously written
                    // cell or execute from an overlapping source location.
                    if address < length || written.contains(&address) {
                        break;
                    }
                    let relocated = super::layout::unwritten_loader_word(
                        &source, address, profile,
                    )
                    .ok()?;
                    address =
                        (usize::try_from(relocated).ok()? + 1) % memory_words;
                }
                if address < length || !written.insert(address) {
                    break;
                }
                words.push(
                    super::layout::unwritten_loader_word(
                        &source, address, profile,
                    )
                    .ok()?,
                );
                // Arithmetic and output each advance D by one position.
                address = (address + 2) % memory_words;
            }
            if words.len() != N {
                continue;
            }
            let mut paths = vec![(0u32, 0u16)];
            for (index, (&word, &target)) in
                words.iter().zip(expected.iter()).enumerate()
            {
                let rotated = word / 3 + (word % 3) * HIGH_TRIT_WEIGHT;
                let mut next = Vec::new();
                for &(accumulator, mask) in &paths {
                    for (value, rotate) in [
                        (malbolge::profile_crazy(word, accumulator, 15), false),
                        (rotated, true),
                    ] {
                        if matches_byte(value, target) {
                            next.push((
                                value,
                                if rotate {
                                    mask | (1 << index)
                                } else {
                                    mask
                                },
                            ));
                        }
                    }
                }
                paths = next;
                if paths.is_empty() || paths.len() > 256 {
                    break;
                }
            }
            for (_, mask) in paths {
                let mut operations = vec![LinearOpcode::NoOperation; prefix];
                operations.push(LinearOpcode::RelocateDataPointer);
                for index in 0..N {
                    if index > 0 && (splits & (1 << (index - 1))) != 0 {
                        operations.push(LinearOpcode::RelocateDataPointer);
                    }
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
    }
    None
}

/// Search a bounded three-relocation guest with arbitrary nonempty regions.
pub(super) fn verified_three_relocation_write_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    verified_relocated_write_layout(profile, expected, source_cells, 3)
}

/// Search a bounded four-relocation guest with arbitrary nonempty regions.
pub(super) fn verified_four_relocation_write_layout<const N: usize>(
    profile: &'static ProfileDescriptor,
    expected: [u8; N],
    source_cells: &[[u8; 6]],
) -> Option<LinearLayout> {
    verified_relocated_write_layout(profile, expected, source_cells, 4)
}
