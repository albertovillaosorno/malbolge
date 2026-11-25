// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Boundary-Contract:
// - Owns:
//   - Finite physical EOF terminal trace.
// - Must-Not:
//   - Authorize the complete SSA frame or relax publication limits.
// - Allows:
//   - Inputs: final source state, terminal geometry and normative trace.
//   - Outputs: exact terminal data-route and output receipt.
// - Split-When:
//   - Additional table or commit shapes are needed.
// - Merge-When:
//   - Full source-frame verification owns recurrent transition semantics.
// - Summary:
//   - Authenticate both EOF contribution paths and their joined byte.

//! Check the straight-line EOF terminal effects in the same normative replay.

use std::collections::BTreeSet;

use malbolge::{
    ProfileStepTrace, StepOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, profile_crazy, profile_rotate,
};

use super::super::{
    Effect, Error, ProjectedIo, SourceRecurrentTerminalCheckpoint,
    SourceRecurrentTransitionProbe,
};

const OPS: &[u8; 33] = b"*jpj*jpooooooj*jjpjpj*jpj*jjpjp<v";
// The terminal combines residues on disjoint seven/eight-trit fields.
const SPLIT: u32 = 2_187;

#[derive(Clone, Copy)]
struct TerminalGeometry {
    constants: [[u32; 2]; 2],
    encoding: [[u32; 16]; 2],
    scratch: u32,
    state: [u32; 2],
    tables: [u32; 2],
}

impl TerminalGeometry {
    fn data_route(self, byte: u8, landing: u32) -> [u32; 33] {
        let [[low_select, low_twos], [high_select, high_twos]] = self.constants;
        let [low, high] = self.state;
        let [high_result, low_result] = self.lookup_addresses(byte);
        let scratch = self.scratch;
        [
            landing.saturating_add(1),
            landing.saturating_add(2),
            high,
            high.saturating_add(1),
            high_select,
            high_select.saturating_add(1),
            high,
            high.saturating_add(1),
            high.saturating_add(2),
            high.saturating_add(3),
            high.saturating_add(4),
            high.saturating_add(5),
            high.saturating_add(6),
            high.saturating_add(7),
            high_twos,
            high_twos.saturating_add(1),
            high,
            high_result,
            high_result.saturating_add(1),
            scratch,
            scratch.saturating_add(1),
            low_select,
            low_select.saturating_add(1),
            low,
            low.saturating_add(1),
            low_twos,
            low_twos.saturating_add(1),
            low,
            low_result,
            low_result.saturating_add(1),
            scratch,
            scratch.saturating_add(1),
            scratch.saturating_add(2),
        ]
    }

    fn high_selector(self) -> u32 {
        // A three-field mask selects raw column 17 with parity/carry zero.
        let ones = current_profile().eof_word().div_euclid(2);
        let [_, high] = self.tables;
        crazy(ones, high)
            .div_euclid(19_683)
            .saturating_mul(19_683)
            .saturating_add(19_602)
            .saturating_add(crazy(ones, 17).rem_euclid(81))
    }

    fn lookup_addresses(self, byte: u8) -> [u32; 2] {
        let [low, high] = self.tables;
        [
            high.saturating_add(504)
                .saturating_add(u32::from(byte >> 4u32).saturating_mul(729)),
            low.saturating_add(5)
                .saturating_add(u32::from(byte & 15).saturating_mul(27)),
        ]
    }

    fn new(probe: &SourceRecurrentTransitionProbe<'_>) -> Result<Self, Error> {
        let guard = &probe.loop_probe.guard;
        let extent = guard.io.physical_source.len();
        let scratch = probe.output_scratch;
        let state = probe.loop_probe.state.words;
        let [low, high] = state;
        let mut reserved = [low, low.saturating_add(1)]
            .into_iter()
            .chain((0..=7).map(|offset| high.saturating_add(offset)))
            .chain(guard.classifier_words)
            .chain(guard.eof_landings.into_iter().flat_map(|address| {
                [
                    address,
                    address.saturating_add(1),
                    address.saturating_add(2),
                    address.saturating_add(3),
                ]
            }))
            .chain([guard.capture_word, guard.byte_landing])
            .chain(probe.scratch_words)
            .chain(probe.reset_constants.into_iter().flatten())
            .chain(probe.route.data_words())
            .collect::<BTreeSet<_>>();
        for address in [scratch, scratch.saturating_add(1)].into_iter().chain(
            probe
                .output_constants
                .into_iter()
                .flatten()
                .flat_map(|address| [address, address.saturating_add(1)]),
        ) {
            if usize::try_from(address).map_or(true, |offset| offset < extent)
                || address >= current_profile().memory_words()
                || !reserved.insert(address)
            {
                return Err(Error::InvalidTransitionBinding);
            }
        }
        let [_, low_table, _, high_table] = probe.tables;
        Ok(Self {
            constants: probe.output_constants,
            encoding: probe.loop_probe.state.encoding,
            scratch,
            state,
            tables: [low_table, high_table],
        })
    }

    fn state_values(self, byte: u8) -> Result<[u32; 2], Error> {
        let [low, high] = self.encoding;
        Ok([
            *low.get(usize::from(byte & 15))
                .ok_or(Error::InvalidTransitionBinding)?,
            *high
                .get(usize::from(byte >> 4u32))
                .ok_or(Error::InvalidTransitionBinding)?,
        ])
    }
}

pub(in super::super) struct TerminalTrace {
    branch: u32,
    byte: Option<u8>,
    cells: Vec<u32>,
    dispatch: Option<(usize, u32)>,
    eof_landings: [u32; 2],
    geometry: TerminalGeometry,
    high_word: Option<u32>,
    output_word: Option<u32>,
    start_index: Option<usize>,
    terminal: u32,
}

impl TerminalTrace {
    pub(in super::super) fn new(
        probe: &SourceRecurrentTransitionProbe<'_>,
    ) -> Result<Self, Error> {
        let guard = &probe.loop_probe.guard;
        let source = guard.io.physical_source;
        let terminal = probe.terminal_address;
        let offset = usize::try_from(terminal)
            .map_err(|_error| Error::InvalidTransitionBinding)?;
        let geometry = TerminalGeometry::new(probe)?;
        let cells = source
            .get(offset..offset.saturating_add(OPS.len()))
            .ok_or(Error::InvalidTransitionBinding)?;
        for (index, (cell, op)) in cells.iter().zip(OPS).enumerate() {
            let address = terminal.saturating_add(
                u32::try_from(index)
                    .map_err(|_error| Error::InvalidTransitionBinding)?,
            );
            if decode_profile_instruction(u32::from(*cell), address)
                != Some(*op)
            {
                return Err(Error::InvalidTransitionBinding);
            }
        }
        Ok(Self {
            branch: guard.branch_address,
            byte: None,
            cells: cells.iter().map(|cell| u32::from(*cell)).collect(),
            dispatch: None,
            eof_landings: guard.eof_landings,
            geometry,
            high_word: None,
            output_word: None,
            start_index: None,
            terminal,
        })
    }

    pub(in super::super) fn observe(
        &mut self,
        trace: &ProfileStepTrace,
        index: usize,
        event: Option<ProjectedIo>,
    ) -> Result<(), Error> {
        if let Some(eof) = event.filter(|value| {
            value.effect == Effect::Input(TraceInput::EndOfInput)
        }) {
            if self.byte.is_some() {
                return Err(Error::GuestTransitionMismatch);
            }
            self.byte =
                Some(eof.state.ok_or(Error::InvalidTransitionBinding)?.value);
        }
        if self.byte.is_some()
            && trace.before.registers.code_pointer == self.branch
            && trace.decoded == Some(b'j')
        {
            let landing = trace.after.registers.data_pointer;
            if !self.eof_landings.contains(&landing)
                || self.dispatch.replace((index, landing)).is_some()
            {
                return Err(Error::GuestTransitionMismatch);
            }
        }
        if let Some((dispatch, landing)) = self.dispatch
            && index == dispatch.saturating_add(1)
        {
            self.verify_entry(trace, landing)?;
        }
        if self.start_index.is_none()
            && trace.before.registers.code_pointer == self.terminal
        {
            let (dispatch, _) =
                self.dispatch.ok_or(Error::GuestTransitionMismatch)?;
            if index != dispatch.saturating_add(2) {
                return Err(Error::GuestTransitionMismatch);
            }
            self.start_index = Some(index);
        }
        if let Some(start) = self.start_index {
            let offset = index
                .checked_sub(start)
                .ok_or(Error::GuestTransitionMismatch)?;
            self.step(trace, offset)?;
        } else if trace.output.is_some() {
            return Err(Error::GuestTransitionMismatch);
        }
        Ok(())
    }

    pub(in super::super) fn receipt(
        &self,
    ) -> Result<SourceRecurrentTerminalCheckpoint, Error> {
        let byte = self.byte.ok_or(Error::GuestTransitionMismatch)?;
        let start = self.start_index.ok_or(Error::GuestTransitionMismatch)?;
        let output_word =
            self.output_word.ok_or(Error::GuestTransitionMismatch)?;
        Ok(SourceRecurrentTerminalCheckpoint {
            byte,
            halt_index: start.saturating_add(32),
            lookup_addresses: self.geometry.lookup_addresses(byte),
            output_word,
            scratch_indices: [
                start.saturating_add(19),
                start.saturating_add(30),
            ],
            terminal_index: start,
        })
    }

    fn step(
        &mut self,
        trace: &ProfileStepTrace,
        offset: usize,
    ) -> Result<(), Error> {
        let before = trace.before.registers;
        let byte = self.byte.ok_or(Error::GuestTransitionMismatch)?;
        let expected_result = if offset == 32 {
            StepOutcome::Terminated(Termination::HaltInstruction)
        } else {
            StepOutcome::Continued
        };
        if before.code_pointer
            != self.terminal.saturating_add(
                u32::try_from(offset)
                    .map_err(|_error| Error::GuestTransitionMismatch)?,
            )
            || trace.fetched_cell != self.cells.get(offset).copied()
            || trace.decoded != OPS.get(offset).copied()
            || trace.result != Ok(expected_result)
            || trace.input.is_some()
        {
            return Err(Error::GuestTransitionMismatch);
        }
        let (_, landing) =
            self.dispatch.ok_or(Error::GuestTransitionMismatch)?;
        let route = self.geometry.data_route(byte, landing);
        verify_route(trace, offset, &route)?;
        self.verify_operands(trace, offset, byte)?;
        if offset == 31 {
            if trace.output != Some(byte)
                || before.accumulator.rem_euclid(256) != u32::from(byte)
            {
                return Err(Error::GuestTransitionMismatch);
            }
            self.output_word = Some(before.accumulator);
        } else if trace.output.is_some() {
            return Err(Error::GuestTransitionMismatch);
        }
        Ok(())
    }

    fn verify_entry(
        &self,
        trace: &ProfileStepTrace,
        landing: u32,
    ) -> Result<(), Error> {
        let before = trace.before.registers;
        let after = trace.after.registers;
        let read = trace
            .memory_reads
            .data
            .ok_or(Error::GuestTransitionMismatch)?;
        if before.code_pointer != self.branch.saturating_add(1)
            || trace.decoded != Some(b'i')
            || before.data_pointer != landing
            || read.address != landing
            || read.value.checked_add(1) != Some(self.terminal)
            || after.code_pointer != self.terminal
            || after.data_pointer != landing.saturating_add(1)
            || before.accumulator != after.accumulator
            || trace.memory_delta.data.is_some()
            || trace.result != Ok(StepOutcome::Continued)
        {
            return Err(Error::GuestTransitionMismatch);
        }
        Ok(())
    }

    fn verify_operands(
        &mut self,
        trace: &ProfileStepTrace,
        offset: usize,
        byte: u8,
    ) -> Result<(), Error> {
        let twos = current_profile().eof_word();
        let ones = twos.div_euclid(2);
        let carry = twos.saturating_sub(81);
        let [low, high] = self.geometry.state_values(byte)?;
        let [high_address, low_address] = self.geometry.lookup_addresses(byte);
        let high_selector = self.geometry.high_selector();
        let after = trace.after.registers.accumulator;
        let before = trace.before.registers.accumulator;
        let old = trace.memory_reads.data.map(|data| data.value);
        let valid = match offset {
            0 => after == carry,
            2 => old == Some(high) && before == carry,
            4 => after == high_selector,
            6 => {
                old == Some(crazy(high, carry))
                    && before == high_selector
                    && after.checked_add(1) == Some(high_address)
            },
            14 | 25 => old == Some(twos) && after == twos,
            17 | 28 => before == twos,
            19 => {
                // The high contribution occupies only the low seven trits;
                // the final low selector supplies twos on this field.
                let valid = old == Some(ones)
                    && after.div_euclid(SPLIT) == ones.div_euclid(SPLIT)
                    && crazy(after, twos).rem_euclid(SPLIT).rem_euclid(256)
                        == u32::from(byte & 0xf0);
                if valid {
                    self.high_word = Some(after);
                }
                valid
            },
            21 => after == twos.saturating_sub(17),
            23 => {
                old == Some(low)
                    && before == twos.saturating_sub(17)
                    && after.checked_add(1) == Some(low_address)
            },
            30 => {
                // The low contribution must provide exactly the low nibble
                // using the other eight trits, not cancel a wrong high one.
                old == self.high_word
                    && self.high_word.is_some()
                    && before.rem_euclid(SPLIT) == SPLIT.saturating_sub(1)
                    && crazy(ones, before)
                        .div_euclid(SPLIT)
                        .saturating_mul(SPLIT)
                        .rem_euclid(256)
                        == u32::from(byte & 15)
                    && after.rem_euclid(256) == u32::from(byte)
            },
            _ => true,
        };
        if !valid {
            return Err(Error::GuestTransitionMismatch);
        }
        Ok(())
    }
}

fn crazy(data: u32, accumulator: u32) -> u32 {
    profile_crazy(data, accumulator, current_profile().word_trits())
}

fn verify_route(
    trace: &ProfileStepTrace,
    offset: usize,
    route: &[u32; 33],
) -> Result<(), Error> {
    let before = trace.before.registers;
    let after = trace.after.registers;
    let address = *route.get(offset).ok_or(Error::GuestTransitionMismatch)?;
    let next = route
        .get(offset.saturating_add(1))
        .copied()
        .unwrap_or(address);
    if before.data_pointer != address || after.data_pointer != next {
        return Err(Error::GuestTransitionMismatch);
    }
    match trace.decoded {
        Some(b'p' | b'*') => {
            let data = trace
                .memory_reads
                .data
                .ok_or(Error::GuestTransitionMismatch)?;
            let result = if trace.decoded == Some(b'p') {
                crazy(data.value, before.accumulator)
            } else {
                profile_rotate(data.value, current_profile().memory_words())
            };
            if data.address != address
                || after.accumulator != result
                || trace
                    .memory_delta
                    .data
                    .map(|write| (write.address, write.before, write.after))
                    != (data.value != result)
                        .then_some((address, data.value, result))
            {
                return Err(Error::GuestTransitionMismatch);
            }
        },
        Some(b'j') => {
            let data = trace
                .memory_reads
                .data
                .ok_or(Error::GuestTransitionMismatch)?;
            if data.address != address
                || data.value.checked_add(1) != Some(next)
                || after.accumulator != before.accumulator
                || trace.memory_delta.data.is_some()
            {
                return Err(Error::GuestTransitionMismatch);
            }
        },
        _ => {
            if trace.memory_reads.data.is_some()
                || trace.memory_delta.data.is_some()
                || after.accumulator != before.accumulator
            {
                return Err(Error::GuestTransitionMismatch);
            }
        },
    }
    Ok(())
}
