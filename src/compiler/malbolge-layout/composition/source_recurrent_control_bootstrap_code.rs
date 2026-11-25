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
//   - Bootstrap preservation of every reserved recurrent code word.
// - Must-Not:
//   - Infer whole-program publication authority from a finite code census.
// - Allows:
//   - Inputs: admitted envelope geometry and normative pre-input traces.
//   - Outputs: preserved code footprint and exact initial entry indices.
//   - Side effects: none.
// - Split-When:
//   - Other layouts require non-virgin code on entry.
// - Merge-When:
//   - A general source-frame verifier owns bootstrap code admission.

use std::collections::BTreeMap;

use malbolge::ProfileStepTrace;

use super::super::source_recurrent_terminal_trace::OPS;
use super::{Error, INVALID, MISMATCH, Plan, encrypted};

pub(super) struct BootstrapCode {
    cells: BTreeMap<u32, u32>,
    entry: u32,
    touches: [Option<usize>; 2],
}

impl BootstrapCode {
    pub(super) fn complete(&self, input_index: usize) -> Result<(), Error> {
        let expected = [input_index.checked_sub(2), input_index.checked_sub(1)];
        if self.touches != expected {
            return Err(MISMATCH);
        }
        Ok(())
    }

    pub(super) fn new(plan: &Plan, source: &[u8]) -> Result<Self, Error> {
        let first = plan.main.first().ok_or(INVALID)?;
        let entry = plan.envelopes.get(&first.site).ok_or(INVALID)?.start;
        let end = plan
            .terminal
            .checked_add(u32::try_from(OPS.len()).map_err(|_error| INVALID)?)
            .ok_or(INVALID)?;
        let terminal = plan.terminal.checked_sub(1).ok_or(INVALID)?..end;
        let addresses = plan
            .envelopes
            .values()
            .flat_map(|envelope| {
                envelope.start.saturating_sub(1)..=envelope.exit
            })
            .chain(terminal);
        let mut cells = BTreeMap::new();
        for address in addresses {
            let cell = source
                .get(usize::try_from(address).map_err(|_error| INVALID)?)
                .copied()
                .ok_or(INVALID)?;
            if cells.insert(address, u32::from(cell)).is_some() {
                return Err(INVALID);
            }
        }
        Ok(Self {
            cells,
            entry,
            touches: [None; 2],
        })
    }

    pub(super) fn observe(
        &mut self,
        trace: &ProfileStepTrace,
        index: usize,
    ) -> Result<(), Error> {
        let reserved = |address| self.cells.contains_key(&address);
        if trace
            .memory_reads
            .data
            .is_some_and(|read| reserved(read.address))
            || trace
                .memory_delta
                .data
                .is_some_and(|write| reserved(write.address))
        {
            return Err(MISMATCH);
        }
        let fetch = trace
            .memory_reads
            .fetch
            .filter(|read| reserved(read.address));
        let encryption = trace
            .memory_reads
            .encryption
            .filter(|read| reserved(read.address));
        let changed = trace
            .memory_delta
            .encryption
            .is_some_and(|write| reserved(write.address));
        if fetch.is_none()
            && encryption.is_none()
            && !changed
            && !reserved(trace.before.registers.code_pointer)
        {
            return Ok(());
        }
        let read = encryption.ok_or(MISMATCH)?;
        if self.cells.get(&read.address) != Some(&read.value) {
            return Err(MISMATCH);
        }
        let [indirect, entry] = self.touches;
        if read.address.checked_add(1) == Some(self.entry)
            && trace.decoded == Some(b'i')
            && fetch.is_none()
            && !reserved(trace.before.registers.code_pointer)
            && indirect.is_none()
            && entry.is_none()
        {
            self.touches = [Some(index), None];
        } else if read.address == self.entry
            && trace.before.registers.code_pointer == self.entry
            && trace.decoded == Some(b'j')
            && fetch == Some(read)
            && indirect.and_then(|previous| previous.checked_add(1))
                == Some(index)
            && entry.is_none()
        {
            self.touches = [indirect, Some(index)];
        } else {
            return Err(MISMATCH);
        }
        let _dirty = encrypted(trace, read.address, read.value)?;
        Ok(())
    }

    pub(super) fn words(&self) -> usize {
        self.cells.len()
    }
}
