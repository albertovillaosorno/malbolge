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
//   - Finite signed source-input phi and physical EOF dispatch correspondence.
// - Must-Not:
//   - Authorize unrestricted guest control, source frames or publication.
// - Allows:
//   - Inputs: canonical typed CFG, physical guard placement and finite stdin.
//   - Outputs: matched source guard and actual capture/classifier effects.
// - Split-When:
//   - General recurrent source control requires additional guard shapes.
// - Merge-When:
//   - Full source-frame/control verification owns this correspondence.
// - Summary:
//   - Authenticate a signed EOF predicate through actual recurrent dispatch.

//! A narrow witness for a lossless signed input and its physical EOF guard.

use std::collections::{BTreeMap, BTreeSet};

use malbolge::{ProfileStepTrace, TraceInput, current_profile, profile_crazy};

use super::super::super::typed_cfg_adapter::ternary::{
    TernaryCfgBlock, TernaryCfgPhi,
};
use super::{
    Effect, Error, ProjectedIo, ReplayAudits, SourceInputWalkState,
    SourceRecurrentIoProbe, SourceRecurrentIoProof, TernaryCfgFunction,
    TernaryCfgScalarKind, TernaryCfgTerminator, TernaryOperation, admit_probe,
    project_function_with_guard, replay_guest,
};

/// Proposed physical sites for a coalesced signed input and EOF dispatch.
#[derive(Clone, Copy, Debug)]
pub struct SourceRecurrentGuardProbe<'source> {
    /// Actual data-jump instruction used to dispatch the classifier result.
    pub branch_address: u32,
    /// Data pointer after the successful-byte dispatch.
    pub byte_landing: u32,
    /// Expanded memory holding the losslessly transformed raw input.
    pub capture_word: u32,
    /// Six distinct classifier words visited in this order.
    pub classifier_words: [u32; 6],
    /// Data pointer after EOF, allowing two equivalent dirty-state routes.
    pub eof_landings: [u32; 2],
    /// Shared physical crazy instruction for capture and the six folds.
    pub fold_address: u32,
    /// Shared physical signed input site.
    pub input_address: u32,
    /// Independently admitted source and complete physical replay request.
    pub io: SourceRecurrentIoProbe<'source>,
    /// Canonical loop header with a signed input phi and inequality to -1.
    pub source_header: u32,
}

/// One source guard and the matched physical data-dependent transfer.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceRecurrentGuardCheckpoint {
    /// Source Boolean SSA result controlling the guard.
    pub condition: u32,
    /// Raw input after the first actual crazy store.
    pub encoded_input: u32,
    /// Actual trace indices of the capture and six classifier folds.
    pub fold_indices: [usize; 7],
    /// The six actual classifier results in execution order.
    pub fold_results: [u32; 6],
    /// Actual trace index of the class-dependent data jump.
    pub guard_index: usize,
    /// Actual post-dispatch data pointer.
    pub guest_landing: u32,
    /// Actual trace index of the corresponding input.
    pub input_index: usize,
    /// Original guest input word, including the profile's distinct EOF.
    pub raw_input: u32,
    /// Source predecessor's signed input SSA identity.
    pub read_result: u32,
    /// Source signed bits (0..255 or all 32 bits set).
    pub signed_bits: u32,
    /// Independently selected source successor block.
    pub target: u32,
}

/// Complete finite I/O plus one physical EOF guard for every signed read.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceRecurrentGuardProof {
    /// Actual physical input/guard occurrences in chronological order.
    pub checkpoints: Vec<SourceRecurrentGuardCheckpoint>,
    /// Complete independent I/O correspondence and real guest termination.
    pub io: SourceRecurrentIoProof,
    /// Canonical source header containing the signed predicate.
    pub source_header: u32,
    /// Canonical signed input phi result.
    pub source_phi: u32,
}

type ReadSite = (u32, u32);
type GuardSites = BTreeMap<ReadSite, u32>;
type SignedGuardPhi<'cfg> = (&'cfg TernaryCfgPhi, u32);

#[derive(Clone, Copy)]
pub(super) struct SourceGuardValue {
    condition: u32,
    read_result: u32,
    signed_bits: u32,
    target: u32,
}

pub(super) struct GuardPlan {
    condition: u32,
    false_target: u32,
    header: u32,
    literal: u32,
    phi: u32,
    reads: GuardSites,
    true_target: u32,
}

impl GuardPlan {
    pub(super) fn checkpoint(
        &self,
        state: &SourceInputWalkState,
        target: u32,
        events: &mut [ProjectedIo],
    ) -> Result<(), Error> {
        if state.block != self.header {
            return Ok(());
        }
        let event = events.last_mut().ok_or(Error::InvalidGuardBinding)?;
        let Effect::Input(input) = event.effect else {
            return Err(Error::InvalidGuardBinding);
        };
        let read_result = *self
            .reads
            .get(&(event.block, event.ordinal))
            .ok_or(Error::InvalidGuardBinding)?;
        let signed_bits = match input {
            TraceInput::Byte(byte) => u32::from(byte),
            TraceInput::EndOfInput => u32::MAX,
        };
        let successful = signed_bits != u32::MAX;
        if event.guard.is_some()
            || state.known.get(&read_result) != Some(&signed_bits)
            || state.known.get(&self.phi) != Some(&signed_bits)
            || state.known.get(&self.literal) != Some(&u32::MAX)
            || state.known.get(&self.condition) != Some(&u32::from(successful))
            || target
                != if successful {
                    self.true_target
                } else {
                    self.false_target
                }
        {
            return Err(Error::InvalidGuardBinding);
        }
        event.guard = Some(SourceGuardValue {
            condition: self.condition,
            read_result,
            signed_bits,
            target,
        });
        Ok(())
    }

    pub(super) fn finish(events: &[ProjectedIo]) -> Result<(), Error> {
        if events.iter().all(|event| {
            matches!(event.effect, Effect::Input(_)) == event.guard.is_some()
        }) {
            Ok(())
        } else {
            Err(Error::InvalidGuardBinding)
        }
    }

    fn new(function: &TernaryCfgFunction, header: u32) -> Result<Self, Error> {
        let block = function
            .blocks
            .iter()
            .find(|candidate| candidate.id == header)
            .ok_or(Error::InvalidGuardBinding)?;
        let TernaryCfgTerminator::Branch {
            condition,
            false_target,
            true_target,
            ..
        } = block.terminator
        else {
            return Err(Error::InvalidGuardBinding);
        };
        if false_target == true_target {
            return Err(Error::InvalidGuardBinding);
        }
        let (phi, literal) = signed_guard_phi(function, block, condition)?;
        let [initial, recurrent] = phi.incoming.as_slice() else {
            return Err(Error::InvalidGuardBinding);
        };
        if initial.0 != function.entry || recurrent.0 == function.entry {
            return Err(Error::InvalidGuardBinding);
        }
        let reads = signed_read_sites(function, &phi.incoming, header)?;
        Ok(Self {
            condition,
            false_target,
            header,
            literal,
            phi: phi.result,
            reads,
            true_target,
        })
    }
}

#[derive(Clone, Copy)]
struct PendingGuard {
    accumulator: u32,
    encoded_input: Option<u32>,
    fold_indices: [usize; 7],
    fold_results: [u32; 6],
    folds: usize,
    input_index: usize,
    raw: u32,
    source: SourceGuardValue,
}

impl PendingGuard {
    fn dispatch(
        self,
        geometry: &GuardGeometry,
        step: &ProfileStepTrace,
        index: usize,
    ) -> Result<SourceRecurrentGuardCheckpoint, Error> {
        let before = step.before.registers;
        let after = step.after.registers;
        let read = step.memory_reads.data.ok_or(Error::GuestGuardMismatch)?;
        let landing = after.data_pointer;
        let valid_landing = if self.source.signed_bits == u32::MAX {
            geometry.eof_landings.contains(&landing)
        } else {
            landing == geometry.byte_landing
        };
        let class_word =
            *geometry.words.last().ok_or(Error::InvalidGuardBinding)?;
        if self.folds != geometry.words.len()
            || step.fetched_cell != Some(geometry.branch_cell)
            || step.result.is_err()
            || before.data_pointer != class_word
            || read.address != class_word
            || read.value != self.accumulator
            || before.accumulator != self.accumulator
            || after.accumulator != self.accumulator
            || read.value.checked_add(1) != Some(landing)
            || step.memory_delta.data.is_some()
            || !valid_landing
        {
            return Err(Error::GuestGuardMismatch);
        }
        Ok(SourceRecurrentGuardCheckpoint {
            condition: self.source.condition,
            encoded_input: self
                .encoded_input
                .ok_or(Error::GuestGuardMismatch)?,
            fold_indices: self.fold_indices,
            fold_results: self.fold_results,
            guard_index: index,
            guest_landing: landing,
            input_index: self.input_index,
            raw_input: self.raw,
            read_result: self.source.read_result,
            signed_bits: self.source.signed_bits,
            target: self.source.target,
        })
    }

    fn fold(
        &mut self,
        geometry: &GuardGeometry,
        step: &ProfileStepTrace,
        index: usize,
    ) -> Result<(), Error> {
        let address = *geometry
            .words
            .get(self.folds)
            .ok_or(Error::GuestGuardMismatch)?;
        let profile = current_profile();
        let before = step.before.registers;
        let after = step.after.registers;
        let read = step.memory_reads.data.ok_or(Error::GuestGuardMismatch)?;
        let new =
            profile_crazy(read.value, self.accumulator, profile.word_trits());
        let ones = profile.eof_word().div_euclid(2);
        if step.decoded != Some(b'p')
            || step.fetched_cell != Some(geometry.fold_cell)
            || step.result.is_err()
            || before.code_pointer != geometry.fold_address
            || before.data_pointer != address
            || before.accumulator != self.accumulator
            || read.address != address
            || after.accumulator != new
            || step
                .memory_delta
                .data
                .map(|delta| (delta.address, delta.before, delta.after))
                != (read.value != new).then_some((address, read.value, new))
        {
            return Err(Error::GuestGuardMismatch);
        }
        if self.folds == 0 {
            if read.value != ones
                || profile_crazy(ones, new, profile.word_trits()) != self.raw
            {
                return Err(Error::GuestGuardMismatch);
            }
            self.encoded_input = Some(new);
        } else {
            *self
                .fold_results
                .get_mut(self.folds.saturating_sub(1))
                .ok_or(Error::GuestGuardMismatch)? = new;
        }
        *self
            .fold_indices
            .get_mut(self.folds)
            .ok_or(Error::GuestGuardMismatch)? = index;
        self.folds = self.folds.saturating_add(1);
        self.accumulator = new;
        Ok(())
    }

    const fn new(
        source: SourceGuardValue,
        raw: u32,
        input_index: usize,
    ) -> Self {
        Self {
            accumulator: raw,
            encoded_input: None,
            fold_indices: [0; 7],
            fold_results: [0; 6],
            folds: 0,
            input_index,
            raw,
            source,
        }
    }
}

struct GuardGeometry {
    branch_address: u32,
    branch_cell: u32,
    byte_landing: u32,
    eof_landings: [u32; 2],
    fold_address: u32,
    fold_cell: u32,
    input_address: u32,
    input_cell: u32,
    words: [u32; 7],
}

impl GuardGeometry {
    fn new(probe: &SourceRecurrentGuardProbe<'_>) -> Result<Self, Error> {
        let [first, second, third, fourth, fifth, sixth] =
            probe.classifier_words;
        let words = [
            probe.capture_word,
            first,
            second,
            third,
            fourth,
            fifth,
            sixth,
        ];
        let sites = [
            probe.branch_address,
            probe.fold_address,
            probe.input_address,
        ];
        let [eof_first, eof_second] = probe.eof_landings;
        let data = words.into_iter().chain([
            probe.byte_landing,
            eof_first,
            eof_second,
        ]);
        let extent = u32::try_from(probe.io.physical_source.len())
            .map_err(|_error| Error::InvalidGuardBinding)?;
        if sites.into_iter().collect::<BTreeSet<_>>().len() != sites.len()
            || data.clone().collect::<BTreeSet<_>>().len() != 10
            || data.into_iter().any(|address| {
                address < extent || address >= current_profile().memory_words()
            })
        {
            return Err(Error::InvalidGuardBinding);
        }
        let cell = |site| {
            usize::try_from(site)
                .ok()
                .and_then(|index| probe.io.physical_source.get(index))
                .copied()
                .map(u32::from)
                .ok_or(Error::InvalidGuardBinding)
        };
        Ok(Self {
            branch_address: probe.branch_address,
            branch_cell: cell(probe.branch_address)?,
            byte_landing: probe.byte_landing,
            eof_landings: probe.eof_landings,
            fold_address: probe.fold_address,
            fold_cell: cell(probe.fold_address)?,
            input_address: probe.input_address,
            input_cell: cell(probe.input_address)?,
            words,
        })
    }
}

pub(super) struct GuardTrace {
    checkpoints: Vec<SourceRecurrentGuardCheckpoint>,
    geometry: GuardGeometry,
    pending: Option<PendingGuard>,
}

impl GuardTrace {
    pub(super) fn finish(&self, events: &[ProjectedIo]) -> Result<(), Error> {
        let reads = events.iter().filter(|event| event.guard.is_some()).count();
        if self.pending.is_none() && self.checkpoints.len() == reads {
            Ok(())
        } else {
            Err(Error::GuestGuardMismatch)
        }
    }

    pub(super) fn new(
        probe: &SourceRecurrentGuardProbe<'_>,
    ) -> Result<Self, Error> {
        Ok(Self {
            checkpoints: Vec::new(),
            geometry: GuardGeometry::new(probe)?,
            pending: None,
        })
    }

    pub(super) fn observe(
        &mut self,
        step: &ProfileStepTrace,
        index: usize,
        event: Option<ProjectedIo>,
    ) -> Result<(), Error> {
        if let Some(observation) = event {
            return self.observe_io(step, index, observation);
        }
        let Some(pending) = self.pending.as_mut() else {
            return Ok(());
        };
        if self
            .geometry
            .words
            .contains(&step.before.registers.code_pointer)
            || step
                .memory_reads
                .encryption
                .is_some_and(|read| self.geometry.words.contains(&read.address))
            || step.memory_delta.encryption.is_some_and(|write| {
                self.geometry.words.contains(&write.address)
            })
        {
            return Err(Error::GuestGuardMismatch);
        }
        if matches!(step.decoded, Some(b'p' | b'*')) {
            return pending.fold(&self.geometry, step, index);
        }
        if step.before.registers.code_pointer == self.geometry.branch_address
            && step.decoded == Some(b'j')
        {
            let checkpoint = self
                .pending
                .take()
                .ok_or(Error::GuestGuardMismatch)?
                .dispatch(&self.geometry, step, index)?;
            self.checkpoints.push(checkpoint);
        } else if step.memory_delta.data.is_some()
            || step.before.registers.accumulator
                != step.after.registers.accumulator
            || step.result.is_err()
        {
            return Err(Error::GuestGuardMismatch);
        }
        Ok(())
    }

    fn observe_io(
        &mut self,
        step: &ProfileStepTrace,
        index: usize,
        observation: ProjectedIo,
    ) -> Result<(), Error> {
        if self.pending.is_some() {
            return Err(Error::GuestGuardMismatch);
        }
        if matches!(observation.effect, Effect::Input(_)) {
            if step.before.registers.code_pointer != self.geometry.input_address
                || step.fetched_cell != Some(self.geometry.input_cell)
            {
                return Err(Error::GuestGuardMismatch);
            }
            self.pending = Some(PendingGuard::new(
                observation.guard.ok_or(Error::InvalidGuardBinding)?,
                step.after.registers.accumulator,
                index,
            ));
        }
        Ok(())
    }
}

fn signed_guard_phi<'cfg>(
    function: &'cfg TernaryCfgFunction,
    block: &'cfg TernaryCfgBlock,
    condition: u32,
) -> Result<SignedGuardPhi<'cfg>, Error> {
    let (left, right) = block
        .operations
        .iter()
        .find_map(|operation| {
            if let TernaryOperation::NotEqualI32 { left, result, right, .. } =
                *operation
                && result == condition
            {
                Some((left, right))
            } else {
                None
            }
        })
        .ok_or(Error::InvalidGuardBinding)?;
    let phi = block
        .phis
        .iter()
        .find(|candidate| {
            candidate.type_kind == TernaryCfgScalarKind::I32
                && [left, right].contains(&candidate.result)
        })
        .ok_or(Error::InvalidGuardBinding)?;
    let literal = if phi.result == left {
        right
    } else {
        left
    };
    // The canonical frontend hoists constants to the entry block.
    // Canonical admission verifies SSA dominance; also check the actual
    // literal at each reached guard rather than assuming the value.
    if !function
        .blocks
        .iter()
        .flat_map(|candidate| &candidate.operations)
        .any(|operation| {
            matches!(
                *operation,
                TernaryOperation::MaterializeI32 { result, scalar, .. }
                    if result == literal && scalar.bits() == u32::MAX
            )
        })
    {
        return Err(Error::InvalidGuardBinding);
    }
    Ok((phi, literal))
}

fn signed_read_sites(
    function: &TernaryCfgFunction,
    incoming: &[(u32, u32)],
    header: u32,
) -> Result<GuardSites, Error> {
    let mut reads = BTreeMap::new();
    for &(predecessor, result) in incoming {
        let block = function
            .blocks
            .iter()
            .find(|candidate| candidate.id == predecessor)
            .ok_or(Error::InvalidGuardBinding)?;
        if !matches!(
            block.terminator,
            TernaryCfgTerminator::Jump { target, .. } if target == header
        ) {
            return Err(Error::InvalidGuardBinding);
        }
        let (position, _) = block
            .operations
            .iter()
            .enumerate()
            .find(|(_, operation)| {
                matches!(
                    **operation,
                    TernaryOperation::GetcharI32 { result: read, .. }
                        if read == result
                )
            })
            .ok_or(Error::InvalidGuardBinding)?;
        let ordinal = u32::try_from(position)
            .map_err(|_error| Error::InvalidGuardBinding)?;
        if reads.insert((predecessor, ordinal), result).is_some() {
            return Err(Error::InvalidGuardBinding);
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
    if reads.len() != all_reads {
        return Err(Error::InvalidGuardBinding);
    }
    Ok(reads)
}

/// Verify each source signed read and EOF guard against actual guest capture,
/// classifier folds and the selected physical data-pointer landing.
///
/// The source guard must be a signed input phi compared to a canonical -1
/// literal. Each incoming value must originate in the corresponding
/// predecessor's real signed read. The guest must preserve the raw word
/// through a reversible encoding, perform the six ordered classifier folds
/// and dispatch to the proper class before any later I/O.
///
/// # Errors
/// Refuses ordinary source/guest I/O failures, invalid guard bindings, missing
/// or incorrect guest folds or an unmatched dispatch. This finite result is
/// not a complete source-frame or publication certificate.
pub fn verify_source_recurrent_guard(
    probe: &SourceRecurrentGuardProbe<'_>,
) -> Result<SourceRecurrentGuardProof, Error> {
    let cfg = admit_probe(probe.io)?;
    let [function] = cfg.functions.as_slice() else {
        return Err(Error::UnsupportedSourceExecution);
    };
    let plan = GuardPlan::new(function, probe.source_header)?;
    let projected = project_function_with_guard(
        function,
        probe.io.input,
        None,
        Some(&plan),
    )?;
    let replay =
        replay_guest(probe.io, &projected, cfg.source_sha256, &ReplayAudits {
            guard: Some(probe),
            state: None,
        })?;
    let guard = replay.guard.ok_or(Error::InvalidGuardBinding)?;
    Ok(SourceRecurrentGuardProof {
        checkpoints: guard.checkpoints,
        io: replay.io,
        source_header: plan.header,
        source_phi: plan.phi,
    })
}

#[cfg(test)]
#[path = "../../../../tests/compiler/source_recurrent_guard.rs"]
mod source_recurrent_guard_tests;
