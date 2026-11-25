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
//   - Finite physical factored lookup and commit trace.
// - Must-Not:
//   - Authorize the complete SSA frame or relax publication limits.
// - Allows:
//   - Inputs: source transition values, table geometry and normative trace.
//   - Outputs: ordered physical transition receipts.
// - Split-When:
//   - Additional table or commit shapes are needed.
// - Merge-When:
//   - Full source-frame verification owns recurrent transition semantics.
// - Summary:

//! Check the straight-line EOF terminal effects in the same normative replay.

use malbolge::{
    ProfileStepTrace, StepOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, profile_crazy,
};

use super::super::{
    Effect, Error, ProjectedIo, SourceRecurrentTerminalCheckpoint,
    SourceRecurrentTransitionProbe,
};

const OPS: &[u8; 33] = b"*jpj*jpooooooj*jjpjpj*jpj*jjpjp<v";

pub(in super::super) struct TerminalTrace {
    branch: u32,
    byte: Option<u8>,
    cells: Vec<u32>,
    dispatch: Option<(usize, u32)>,
    eof_landings: [u32; 2],
    lookup_bases: [u32; 2],
    output_word: Option<u32>,
    scratch: u32,
    start_index: Option<usize>,
    terminal: u32,
}

impl TerminalTrace {
    fn lookup_addresses(&self, byte: u8) -> [u32; 2] {
        let [high, low] = self.lookup_bases;
        [
            high.saturating_add(504)
                .saturating_add(u32::from(byte >> 4u32).saturating_mul(729)),
            low.saturating_add(5)
                .saturating_add(u32::from(byte & 15).saturating_mul(27)),
        ]
    }

    pub(in super::super) fn new(
        probe: &SourceRecurrentTransitionProbe<'_>,
    ) -> Result<Self, Error> {
        let guard = &probe.loop_probe.guard;
        let source = guard.io.physical_source;
        let terminal = probe.terminal_address;
        let scratch = probe.output_scratch;
        let offset = usize::try_from(terminal)
            .map_err(|_error| Error::InvalidTransitionBinding)?;
        if usize::try_from(scratch)
            .map_or(true, |address| address < source.len())
            || scratch >= current_profile().memory_words()
            || probe.loop_probe.state.words.contains(&scratch)
            || guard.classifier_words.contains(&scratch)
            || guard.eof_landings.contains(&scratch)
            || [guard.capture_word, guard.byte_landing].contains(&scratch)
        {
            return Err(Error::InvalidTransitionBinding);
        }
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
        let [_, low, _, high] = probe.tables;
        Ok(Self {
            branch: guard.branch_address,
            byte: None,
            cells: cells.iter().map(|cell| u32::from(*cell)).collect(),
            dispatch: None,
            eof_landings: guard.eof_landings,
            lookup_bases: [high, low],
            output_word: None,
            scratch,
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
            lookup_addresses: self.lookup_addresses(byte),
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
        let after = trace.after.registers;
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
        let [high, low] = self.lookup_addresses(byte);
        let address = match offset {
            17 => Some(high),
            28 => Some(low),
            19 | 30 => Some(self.scratch),
            _ => None,
        };
        if let Some(expected) = address {
            verify_crazy(trace, expected)?;
        }
        if offset == 30 && after.accumulator.rem_euclid(256) != u32::from(byte)
        {
            return Err(Error::GuestTransitionMismatch);
        }
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
}

fn verify_crazy(trace: &ProfileStepTrace, address: u32) -> Result<(), Error> {
    let before = trace.before.registers;
    let after = trace.after.registers;
    let data = trace
        .memory_reads
        .data
        .ok_or(Error::GuestTransitionMismatch)?;
    if before.data_pointer != address
        || data.address != address
        || profile_crazy(
            data.value,
            before.accumulator,
            current_profile().word_trits(),
        ) != after.accumulator
        || trace.memory_delta.data.map_or(
            data.value != after.accumulator,
            |write| {
                write.address != address
                    || write.before != data.value
                    || write.after != after.accumulator
            },
        )
    {
        return Err(Error::GuestTransitionMismatch);
    }
    Ok(())
}
