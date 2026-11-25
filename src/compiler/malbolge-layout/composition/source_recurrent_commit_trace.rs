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
//   - Finite physical scratch transfer and dirty reset correspondence.
// - Must-Not:
//   - Authorize a complete source frame or publication.
// - Allows:
//   - Inputs: selected source nibble, physical geometry and normative trace.
//   - Outputs: ordered scratch-transfer and dirty-reset receipts.
// - Split-When:
//   - Additional physical commit shapes require separate policies.
// - Merge-When:
//   - Full source-frame verification owns these physical effects.
// - Summary:
//   - Authenticate both scratch-to-state transfers and scratch restoration.

//! Independently verify the nine arithmetic effects of a nibble commit.

use std::collections::{BTreeMap, BTreeSet};

use malbolge::{ProfileStepTrace, StepOutcome, current_profile, profile_crazy};

use super::super::{Error, SourceRecurrentTransitionProbe};
use super::validate_site;

#[derive(Clone, Copy)]
struct Site {
    address: u32,
    cell: u32,
    opcode: u8,
}

impl Site {
    fn new(
        source: &[u8],
        occupied: &mut BTreeMap<u32, u32>,
        address: u32,
        opcode: u8,
    ) -> Result<Self, Error> {
        Ok(Self {
            address,
            cell: validate_site(source, occupied, address, opcode)?,
            opcode,
        })
    }
}

type Operands = (Option<u32>, Option<u32>, Option<u32>);

struct Expected {
    address: u32,
    input: Option<u32>,
    old: Option<u32>,
    output: Option<u32>,
    site: Site,
}

impl Expected {
    const fn new(
        site: Site,
        address: u32,
        (old, input, output): Operands,
    ) -> Self {
        Self {
            address,
            input,
            old,
            output,
            site,
        }
    }

    fn verify(self, trace: &ProfileStepTrace) -> Result<u32, Error> {
        let before = trace.before.registers;
        let after = trace.after.registers;
        let read = trace
            .memory_reads
            .data
            .ok_or(Error::GuestTransitionMismatch)?;
        let output = match self.site.opcode {
            b'p' => crazy(read.value, before.accumulator),
            b'*' => read.value.div_euclid(3).saturating_add(
                read.value.rem_euclid(3).saturating_mul(4_782_969),
            ),
            _ => return Err(Error::InvalidTransitionBinding),
        };
        if before.code_pointer != self.site.address
            || before.data_pointer != self.address
            || trace.fetched_cell != Some(self.site.cell)
            || trace.decoded != Some(self.site.opcode)
            || trace.result != Ok(StepOutcome::Continued)
            || read.address != self.address
            || self.old.is_some_and(|old| old != read.value)
            || self.input.is_some_and(|input| input != before.accumulator)
            || self.output.is_some_and(|expected| expected != output)
            || after.accumulator != output
            || trace
                .memory_delta
                .data
                .map(|delta| (delta.address, delta.before, delta.after))
                != (read.value != output).then_some((
                    self.address,
                    read.value,
                    output,
                ))
        {
            return Err(Error::GuestTransitionMismatch);
        }
        Ok(output)
    }
}

pub(super) struct CommitGeometry {
    constants: [[u32; 2]; 2],
    scratch: [u32; 2],
    sites: [Site; 6],
    words: [u32; 2],
}

impl CommitGeometry {
    pub(super) fn is_unbound_effect(&self, trace: &ProfileStepTrace) -> bool {
        let before = trace.before.registers;
        let [_, _, _, _, rotate, commit] = self.sites;
        matches!(trace.decoded, Some(b'p' | b'*'))
            && (self.scratch.contains(&before.data_pointer)
                || self
                    .constants
                    .iter()
                    .flatten()
                    .any(|constant| *constant == before.data_pointer)
                || before.code_pointer == rotate.address
                || (before.code_pointer == commit.address
                    && self.words.contains(&before.data_pointer)))
    }

    pub(super) fn new(
        probe: &SourceRecurrentTransitionProbe<'_>,
        lookup_sites: &BTreeMap<u32, u32>,
    ) -> Result<Self, Error> {
        let guard = &probe.loop_probe.guard;
        let source = guard.io.physical_source;
        let mut occupied = lookup_sites.clone();
        let [first, second] = probe.reset_addresses;
        let sites = [
            Site::new(source, &mut occupied, guard.fold_address, b'p')?,
            Site::new(source, &mut occupied, probe.rotate_address, b'*')?,
            Site::new(source, &mut occupied, first, b'p')?,
            Site::new(source, &mut occupied, second, b'p')?,
            Site::new(
                source,
                &mut occupied,
                probe.scratch_rotate_address,
                b'*',
            )?,
            Site::new(source, &mut occupied, probe.commit_address, b'p')?,
        ];
        let words = probe.loop_probe.state.words;
        let mut reserved = words
            .into_iter()
            .chain(guard.classifier_words)
            .chain(guard.eof_landings)
            .chain([
                guard.capture_word,
                guard.byte_landing,
                probe.output_scratch,
            ])
            .collect::<BTreeSet<_>>();
        for address in probe
            .scratch_words
            .into_iter()
            .chain(probe.reset_constants.into_iter().flatten())
        {
            if usize::try_from(address)
                .map_or(true, |value| value < source.len())
                || address >= current_profile().memory_words()
                || !reserved.insert(address)
            {
                return Err(Error::InvalidTransitionBinding);
            }
        }
        Ok(Self {
            constants: probe.reset_constants,
            scratch: probe.scratch_words,
            sites,
            words,
        })
    }
}

type CommitIndices = [usize; 9];

pub(super) struct CommitTrace {
    dirty_state: u32,
    indices: CommitIndices,
    last: u32,
    lookup: u32,
    position: usize,
    pub(super) slot: usize,
    value: u32,
}

impl CommitTrace {
    fn expected(&self, geometry: &CommitGeometry) -> Result<Expected, Error> {
        let ones = current_profile().eof_word().div_euclid(2);
        let scratch_value = crazy(ones, self.lookup);
        let inverse = crazy(ones, self.value);
        let state = *geometry
            .words
            .get(self.slot)
            .ok_or(Error::InvalidTransitionBinding)?;
        let scratch = *geometry
            .scratch
            .get(self.slot)
            .ok_or(Error::InvalidTransitionBinding)?;
        let [state_constant, scratch_constant] = *geometry
            .constants
            .get(self.slot)
            .ok_or(Error::InvalidTransitionBinding)?;
        let [store, constant, first, second, rotate, commit] = geometry.sites;
        let uniform = (Some(ones), None, Some(ones));
        let reset = (Some(self.last), Some(self.last), Some(ones));
        let expected = match self.position {
            0 => Expected::new(
                store,
                scratch,
                (Some(ones), Some(self.lookup), Some(scratch_value)),
            ),
            1 => Expected::new(constant, state_constant, uniform),
            2 => Expected::new(
                first,
                state,
                (Some(self.dirty_state), Some(ones), None),
            ),
            3 => Expected::new(second, state, reset),
            4 => Expected::new(
                rotate,
                scratch,
                (Some(scratch_value), None, Some(inverse)),
            ),
            5 => Expected::new(
                commit,
                state,
                (Some(ones), Some(inverse), Some(self.value)),
            ),
            6 => Expected::new(constant, scratch_constant, uniform),
            7 => {
                Expected::new(first, scratch, (Some(inverse), Some(ones), None))
            },
            8 => Expected::new(second, scratch, reset),
            _ => return Err(Error::GuestTransitionMismatch),
        };
        Ok(expected)
    }

    pub(super) const fn new(
        slot: usize,
        value: u32,
        lookup: u32,
        dirty_state: u32,
    ) -> Self {
        Self {
            dirty_state,
            indices: [0; 9],
            last: 0,
            lookup,
            position: 0,
            slot,
            value,
        }
    }

    pub(super) fn observe(
        &mut self,
        geometry: &CommitGeometry,
        trace: &ProfileStepTrace,
        index: usize,
    ) -> Result<Option<CommitIndices>, Error> {
        self.last = self.expected(geometry)?.verify(trace)?;
        *self
            .indices
            .get_mut(self.position)
            .ok_or(Error::GuestTransitionMismatch)? = index;
        self.position = self.position.saturating_add(1);
        Ok((self.position == self.indices.len()).then_some(self.indices))
    }
}

fn crazy(data: u32, accumulator: u32) -> u32 {
    profile_crazy(data, accumulator, current_profile().word_trits())
}
