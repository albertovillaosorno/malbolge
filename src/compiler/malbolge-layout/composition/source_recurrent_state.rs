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
//   - Finite loop-phi state correspondence at coalesced physical input sites.
// - Must-Not:
//   - Authorize unrestricted guest arithmetic, SSA placement or publication.
// - Allows:
//   - Inputs: canonical typed CFG, split-state encoding, real guest trace.
//   - Outputs: independently evaluated state and actual write checkpoints.
// - Split-When:
//   - More than one carried source value requires independent tracking.
// - Merge-When:
//   - General recurrent source-frame verification covers these obligations.
// - Summary:
//   - Authenticate both persistent guest words against a source loop phi.

//! Optional narrow source-state witness on the same finite I/O execution.

use std::collections::{BTreeMap, BTreeSet};

use malbolge::{ProfileMachine, ProfileStepTrace, current_profile};

use super::{
    Effect, Error, ProjectedIo, ReplayAudits, SourceInputWalkState,
    SourceRecurrentIoProbe, SourceRecurrentIoProof, TernaryCfgFunction,
    TernaryCfgScalarKind, TernaryCfgTerminator, TernaryOperation, admit_probe,
    known_source_binary, known_source_cast, known_source_shift,
    known_source_threshold, project_function, replay_guest,
};

/// Proposed encoding of one unsigned source loop-phi in two physical words.
#[derive(Clone, Copy, Debug)]
pub struct SourceRecurrentStateProbe<'source> {
    /// Low- and high-nibble words, each injective over the 16 nibble values.
    pub encoding: [[u32; 16]; 2],
    /// Shared physical input instruction reached by both source read sites.
    pub input_address: u32,
    /// Independently admitted source and complete physical execution request.
    pub io: SourceRecurrentIoProbe<'source>,
    /// Canonical loop-header block containing the selected phi.
    pub loop_header: u32,
    /// Selected unsigned 32-bit phi result identity, not a physical address.
    pub phi_result: u32,
    /// Distinct low- and high-nibble memory addresses outside the source.
    pub words: [u32; 2],
}

/// Carried source state at one real input occurrence, including true EOF.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceRecurrentStateCheckpoint {
    /// Source predecessor containing the matched logical read.
    pub block: u32,
    /// Actual shared physical read address.
    pub code_address: u32,
    /// Source read operation ordinal.
    pub ordinal: u32,
    /// Actual source SSA incoming value identity for the selected phi.
    pub source_value: u32,
    /// Zero-based normative step index of the input.
    pub trace_index: usize,
    /// Independently evaluated source value, required to fit one byte.
    pub value: u8,
    /// Exact observed low- and high-nibble memory words before the read.
    pub words: [u32; 2],
    /// Last arithmetic store to each word since the previous input or load.
    pub write_indices: [usize; 2],
    /// Code address of each of those actual arithmetic instructions.
    pub write_sites: [u32; 2],
}

/// A finite state and I/O witness, not a full source-frame certificate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceRecurrentStateProof {
    /// Exact checkpoints in the same chronological guest I/O trace.
    pub checkpoints: Vec<SourceRecurrentStateCheckpoint>,
    /// Complete source/guest I/O correspondence including halt.
    pub io: SourceRecurrentIoProof,
    /// Selected canonical loop header.
    pub loop_header: u32,
    /// Selected canonical source phi result identity.
    pub phi_result: u32,
    /// Physical low and high memory addresses authenticated by the trace.
    pub word_addresses: [u32; 2],
}

type ReadSite = (u32, u32);
type StateSites = BTreeMap<ReadSite, u32>;

#[derive(Clone, Copy)]
pub(super) struct SourceCheckpointValue {
    source_value: u32,
    pub(super) value: u8,
}

pub(super) struct StatePlan {
    header: u32,
    phi: u32,
    sites: StateSites,
}

#[derive(Clone, Copy)]
struct TrackedCell {
    address: u32,
    last_store: Option<(usize, u32)>,
    value: u32,
}

pub(super) struct StateTrace {
    cells: [TrackedCell; 2],
    pub(super) checkpoints: Vec<SourceRecurrentStateCheckpoint>,
    encoding: [[u32; 16]; 2],
    input_address: u32,
}

impl StatePlan {
    pub(super) fn checkpoint(
        &self,
        state: &SourceInputWalkState,
        operation: &TernaryOperation,
    ) -> Result<Option<SourceCheckpointValue>, Error> {
        if !matches!(
            operation,
            TernaryOperation::GetcharI32 { .. }
                | TernaryOperation::ByteInput { .. }
        ) {
            return Ok(None);
        }
        let ordinal = u32::try_from(state.operation)
            .map_err(|_error| Error::InvalidStateBinding)?;
        let source_value = *self
            .sites
            .get(&(state.block, ordinal))
            .ok_or(Error::InvalidStateBinding)?;
        let value = state
            .known
            .get(&source_value)
            .and_then(|bits| u8::try_from(*bits).ok())
            .ok_or(Error::InvalidStateBinding)?;
        Ok(Some(SourceCheckpointValue { source_value, value }))
    }

    pub(super) fn merge(
        &self,
        state: &SourceInputWalkState,
        events: &[ProjectedIo],
    ) -> Result<(), Error> {
        if state.block != self.header {
            return Ok(());
        }
        let checkpoint = events
            .last()
            .and_then(|event| event.state)
            .ok_or(Error::InvalidStateBinding)?;
        if state.known.get(&self.phi) != Some(&u32::from(checkpoint.value)) {
            return Err(Error::InvalidStateBinding);
        }
        Ok(())
    }

    pub(super) fn new(
        function: &TernaryCfgFunction,
        probe: &SourceRecurrentStateProbe<'_>,
    ) -> Result<Self, Error> {
        let phi = function
            .blocks
            .iter()
            .find(|block| block.id == probe.loop_header)
            .and_then(|block| {
                block.phis.iter().find(|phi| phi.result == probe.phi_result)
            })
            .filter(|phi| phi.type_kind == TernaryCfgScalarKind::U32)
            .ok_or(Error::InvalidStateBinding)?;
        let [initial, recurrent] = phi.incoming.as_slice() else {
            return Err(Error::InvalidStateBinding);
        };
        if initial.0 != function.entry || recurrent.0 == function.entry {
            return Err(Error::InvalidStateBinding);
        }
        let mut sites = BTreeMap::new();
        for incoming in phi.incoming.iter().copied() {
            let site = read_site(function, incoming, probe.loop_header)?;
            if sites.insert(site, incoming.1).is_some() {
                return Err(Error::InvalidStateBinding);
            }
        }
        let all_reads = function
            .blocks
            .iter()
            .flat_map(|block| &block.operations)
            .filter(|operation| {
                matches!(
                    operation,
                    TernaryOperation::GetcharI32 { .. }
                        | TernaryOperation::ByteInput { .. }
                )
            })
            .count();
        if all_reads != sites.len() {
            return Err(Error::InvalidStateBinding);
        }
        Ok(Self {
            header: probe.loop_header,
            phi: probe.phi_result,
            sites,
        })
    }
}

impl TrackedCell {
    fn new(address: u32, vm: &ProfileMachine) -> Result<Self, Error> {
        Ok(Self {
            address,
            last_store: None,
            value: vm
                .memory_word(address)
                .map_err(|_error| Error::InvalidGuestExecution)?,
        })
    }

    fn observe(
        &mut self,
        step: &ProfileStepTrace,
        index: usize,
    ) -> Result<(), Error> {
        if step.before.registers.code_pointer == self.address
            || step
                .memory_reads
                .encryption
                .is_some_and(|read| read.address == self.address)
            || step
                .memory_delta
                .encryption
                .is_some_and(|write| write.address == self.address)
        {
            return Err(Error::GuestStateMismatch);
        }
        let write = step
            .memory_delta
            .data
            .filter(|write| write.address == self.address);
        let arithmetic = matches!(step.decoded, Some(b'p' | b'*'))
            && step
                .memory_reads
                .data
                .is_some_and(|read| read.address == self.address);
        if !arithmetic {
            return if write.is_none() {
                Ok(())
            } else {
                Err(Error::GuestStateMismatch)
            };
        }
        let before = step
            .memory_reads
            .data
            .ok_or(Error::GuestStateMismatch)?
            .value;
        let after = step.after.registers.accumulator;
        if step.result.is_err()
            || before != self.value
            || write.map_or(before != after, |delta| {
                delta.before != before || delta.after != after
            })
        {
            return Err(Error::GuestStateMismatch);
        }
        self.value = after;
        self.last_store = Some((index, step.before.registers.code_pointer));
        Ok(())
    }
}

impl StateTrace {
    fn checkpoint(
        &mut self,
        event: ProjectedIo,
        step: &ProfileStepTrace,
        index: usize,
    ) -> Result<(), Error> {
        let expected = event.state.ok_or(Error::InvalidStateBinding)?;
        let [low_encoding, high_encoding] = self.encoding;
        let words = [
            *low_encoding
                .get(usize::from(expected.value & 15))
                .ok_or(Error::InvalidStateBinding)?,
            *high_encoding
                .get(usize::from(expected.value >> 4u32))
                .ok_or(Error::InvalidStateBinding)?,
        ];
        let [low, high] = self.cells;
        let code_address = step.before.registers.code_pointer;
        if code_address != self.input_address
            || [low.value, high.value] != words
        {
            return Err(Error::GuestStateMismatch);
        }
        let (low_index, low_site) =
            low.last_store.ok_or(Error::MissingGuestStateStore)?;
        let (high_index, high_site) =
            high.last_store.ok_or(Error::MissingGuestStateStore)?;
        self.checkpoints.push(SourceRecurrentStateCheckpoint {
            block: event.block,
            code_address,
            ordinal: event.ordinal,
            source_value: expected.source_value,
            trace_index: index,
            value: expected.value,
            words,
            write_indices: [low_index, high_index],
            write_sites: [low_site, high_site],
        });
        for cell in &mut self.cells {
            cell.last_store = None;
        }
        Ok(())
    }

    pub(super) fn finish(&self, vm: &ProfileMachine) -> Result<(), Error> {
        for cell in self.cells {
            if vm
                .memory_word(cell.address)
                .map_err(|_error| Error::InvalidGuestExecution)?
                != cell.value
            {
                return Err(Error::GuestStateMismatch);
            }
        }
        Ok(())
    }

    pub(super) fn new(
        probe: &SourceRecurrentStateProbe<'_>,
        vm: &ProfileMachine,
    ) -> Result<Self, Error> {
        let [low, high] = probe.words;
        Ok(Self {
            cells: [TrackedCell::new(low, vm)?, TrackedCell::new(high, vm)?],
            checkpoints: Vec::new(),
            encoding: probe.encoding,
            input_address: probe.input_address,
        })
    }

    pub(super) fn observe(
        &mut self,
        step: &ProfileStepTrace,
        index: usize,
        event: Option<ProjectedIo>,
    ) -> Result<(), Error> {
        if let Some(read) =
            event.filter(|reached| matches!(reached.effect, Effect::Input(_)))
        {
            self.checkpoint(read, step, index)?;
        }
        for cell in &mut self.cells {
            cell.observe(step, index)?;
        }
        Ok(())
    }
}

fn source_result(operation: &TernaryOperation) -> Option<u32> {
    let empty = BTreeMap::new();
    known_source_cast(operation, &empty)
        .or_else(|| known_source_binary(operation, &empty))
        .or_else(|| known_source_threshold(operation, &empty))
        .map(|(result, _value)| result)
        .or_else(|| {
            known_source_shift(operation, &empty).map(|(result, _value)| result)
        })
}

fn read_site(
    function: &TernaryCfgFunction,
    (predecessor, source_value): (u32, u32),
    header: u32,
) -> Result<ReadSite, Error> {
    let block = function
        .blocks
        .iter()
        .find(|block| block.id == predecessor)
        .ok_or(Error::InvalidStateBinding)?;
    let TernaryCfgTerminator::Jump { target, .. } = block.terminator else {
        return Err(Error::InvalidStateBinding);
    };
    if target != header {
        return Err(Error::InvalidStateBinding);
    }
    let mut read = None;
    let mut defined = false;
    for (ordinal, operation) in block.operations.iter().enumerate() {
        if matches!(operation, TernaryOperation::GetcharI32 { .. }) {
            if !defined || read.is_some() {
                return Err(Error::InvalidStateBinding);
            }
            read = Some(
                u32::try_from(ordinal)
                    .map_err(|_error| Error::InvalidStateBinding)?,
            );
        }
        if source_result(operation) == Some(source_value) {
            defined = true;
        }
    }
    Ok((predecessor, read.ok_or(Error::InvalidStateBinding)?))
}

pub(super) fn validate_geometry(
    probe: &SourceRecurrentStateProbe<'_>,
) -> Result<(), Error> {
    let [low, high] = probe.words;
    let extent = u32::try_from(probe.io.physical_source.len())
        .map_err(|_error| Error::InvalidStateBinding)?;
    if probe.input_address >= extent
        || low == high
        || [low, high].iter().any(|address| {
            *address < extent || *address >= current_profile().memory_words()
        })
    {
        return Err(Error::InvalidStateBinding);
    }
    for words in probe.encoding {
        if words
            .iter()
            .any(|word| *word > current_profile().eof_word())
            || words.into_iter().collect::<BTreeSet<_>>().len() != 16
        {
            return Err(Error::InvalidStateBinding);
        }
    }
    Ok(())
}

/// Verify the selected source loop phi at each real recurrent read.
///
/// The two signed read sites must be in the phi's entry and backedge
/// predecessors, and the incoming byte-state values must be defined before
/// the corresponding reads. No candidate value is supplied to the VM.
/// Both physical words require a real arithmetic store in every interval.
///
/// # Errors
///
/// Refuses any ordinary I/O verification failure, invalid split-state
/// geometry, invalid source binding, incorrect state or missing stores.
/// This finite result is not a full source-frame or publication certificate.
pub fn verify_source_recurrent_state(
    probe: &SourceRecurrentStateProbe<'_>,
) -> Result<SourceRecurrentStateProof, Error> {
    let cfg = admit_probe(probe.io)?;
    validate_geometry(probe)?;
    let [function] = cfg.functions.as_slice() else {
        return Err(Error::UnsupportedSourceExecution);
    };
    let plan = StatePlan::new(function, probe)?;
    let projection = project_function(function, probe.io.input, Some(&plan))?;
    let replay = replay_guest(
        probe.io,
        &projection,
        cfg.source_sha256,
        &ReplayAudits {
            guard: None,
            state: Some(probe),
            transition: None,
        },
    )?;
    let trace = replay.state.ok_or(Error::InvalidStateBinding)?;
    Ok(SourceRecurrentStateProof {
        checkpoints: trace.checkpoints,
        io: replay.io,
        loop_header: probe.loop_header,
        phi_result: probe.phi_result,
        word_addresses: probe.words,
    })
}

#[cfg(test)]
#[path = "../../../../tests/compiler/source_recurrent_state.rs"]
pub(super) mod source_recurrent_state_tests;
