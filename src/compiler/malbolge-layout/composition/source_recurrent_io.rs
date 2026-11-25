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
//   - Finite source-CFG and normative guest I/O correspondence.
// - Must-Not:
//   - Authorize physical SSA stores, guest arithmetic or publication.
// - Allows:
//   - Inputs: canonical typed source, graphical guest and finite stdin.
//   - Outputs: matched chronological source and physical I/O occurrences.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - Independently linked recurrent state effects supersede I/O-only proof.
// - Merge-When:
//   - General translation verification admits coalesced source effects.
// - Summary:
//   - Compare concrete I/O without requiring distinct physical read sites.

//! Finite observational correspondence for coalesced physical I/O sites.
//!
//! The strict source evaluator never supplies data to the guest. It projects
//! one deterministic source path independently, then a fresh normative VM
//! must actually perform precisely the same ordered I/O and halt. This is
//! not a physical SSA/control certificate or a compiler publication gate.

#[path = "source_recurrent_state.rs"]
mod source_recurrent_state;

use std::collections::BTreeMap;

use malbolge::{
    ProfileMachine, ProfileStepTrace, RunOutcome, Termination, TraceInput,
    current_profile,
};
use source_recurrent_state::{SourceCheckpointValue, StatePlan, StateTrace};
pub use source_recurrent_state::{
    SourceRecurrentStateCheckpoint, SourceRecurrentStateProbe,
    SourceRecurrentStateProof, verify_source_recurrent_state,
};

use super::{
    MAX_SOURCE_INPUT_CFG_SEARCH_STATES, SourceInputWalkState,
    TernaryCfgFunction, TernaryCfgPlan, TernaryCfgScalarKind,
    TernaryCfgTerminator, TernaryOperation, known_source_binary,
    known_source_cast, known_source_shift, known_source_threshold,
    lower_canonical_dynamic_cfg, source_successor_state,
};

/// Separate experimental envelope, not the P2 publication resource limit.
pub const MAX_RECURRENT_IO_SOURCE_CELLS: usize = 3_000_000;
/// Includes every bootstrap instruction; the P2 publication limit is unchanged.
pub const MAX_RECURRENT_IO_STEPS: usize = 3_000_000;
const MAX_IO_EVENTS: usize = 512;

/// One complete source/guest observable I/O event.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SourceRecurrentIoEffect {
    /// A successful input byte or a true exhausted-stream observation.
    Input(TraceInput),
    /// One byte actually emitted by the guest.
    Output(u8),
}

/// One dynamic source I/O occurrence matched to a real physical instruction.
///
/// Different static source operations may map to the same physical code cell.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceRecurrentIoObservation {
    /// Source block identity.
    pub block: u32,
    /// Matched actual guest code pointer.
    pub code_address: u32,
    /// The observable I/O effect on both sides.
    pub effect: SourceRecurrentIoEffect,
    /// Source function identity.
    pub function: u32,
    /// Source operation ordinal within its block.
    pub ordinal: u32,
    /// Raw guest accumulator after input or before output.
    pub raw_accumulator: u32,
    /// Zero-based normative execution index, including bootstrap.
    pub trace_index: usize,
}

/// One finite, isolated recurrent I/O replay request.
#[derive(Clone, Copy, Debug)]
pub struct SourceRecurrentIoProbe<'source> {
    /// Canonical, independently admitted typed source.
    pub canonical: &'source [u8],
    /// Identical finite binary stdin on both independent executions.
    pub input: &'source [u8],
    /// Complete graphical current-profile guest.
    pub physical_source: &'source [u8],
    /// Positive guest instruction ceiling including initialization.
    pub step_budget: usize,
}

/// Observational evidence only, not authority to publish compiled guest code.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceRecurrentIoProof {
    /// Actual bytes consumed (true EOF does not count).
    pub bytes_consumed: usize,
    /// Executed physical halt cell.
    pub guest_halt_address: u32,
    /// Executed guest instructions, including initialization and halt.
    pub guest_steps: usize,
    /// Exact matched effects, in occurrence order.
    pub observations: Vec<SourceRecurrentIoObservation>,
    /// Source block that actually returns.
    pub source_return_block: u32,
    /// Original source identity obtained from the canonical typed wire.
    pub source_sha256: [u8; 32],
    /// Counted source operations and terminators, including the return.
    pub source_steps: usize,
}

/// Refusals of the finite observational correspondence checker.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SourceRecurrentIoError {
    /// Full guest execution did not halt within the declared ceiling.
    GuestBudgetExhausted,
    /// Missing, additional, reordered or different physical I/O.
    GuestIoMismatch,
    /// A carried state word differs from the independently evaluated source.
    GuestStateMismatch,
    /// Guest halt did not correspond to the source's void return.
    GuestTerminationMismatch,
    /// Canonical typed source failed independent admission.
    InvalidCanonicalSource,
    /// Normative VM loading or execution failed.
    InvalidGuestExecution,
    /// Invalid resource bound, non-graphical source or excessive input.
    InvalidProbeBound,
    /// The proposed phi, input sites or split-state representation is invalid.
    InvalidStateBinding,
    /// A recurrent state word lacked a physical arithmetic store.
    MissingGuestStateStore,
    /// Source evaluation or event journal exhausted its separate finite limit.
    SourceBudgetExhausted,
    /// Source operation, phi, branch or return is not fully modeled.
    UnsupportedSourceExecution,
}

type Error = SourceRecurrentIoError;
type Effect = SourceRecurrentIoEffect;
type PhysicalIo = (Effect, u32);

#[derive(Clone, Copy)]
struct ProjectedIo {
    block: u32,
    effect: Effect,
    ordinal: u32,
    state: Option<SourceCheckpointValue>,
}

struct ProjectionJournal<'plan> {
    events: Vec<ProjectedIo>,
    state_plan: Option<&'plan StatePlan>,
}

struct ReplayJournal {
    failed: Option<Error>,
    last_code: Option<u32>,
    observations: Vec<SourceRecurrentIoObservation>,
    source_sha256: [u8; 32],
    state: Option<StateTrace>,
    trace_index: usize,
}

struct ReplayProof {
    io: SourceRecurrentIoProof,
    state: Option<StateTrace>,
}

struct SourceProjection {
    bytes_consumed: usize,
    events: Vec<ProjectedIo>,
    function: u32,
    return_block: u32,
    steps: usize,
}

impl ReplayJournal {
    fn finish(
        self,
        outcome: RunOutcome,
        projected: &SourceProjection,
        vm: &ProfileMachine,
    ) -> Result<ReplayProof, Error> {
        if let Some(error) = self.failed {
            return Err(error);
        }
        let guest_steps = match outcome {
            RunOutcome::BudgetExhausted { .. } => {
                return Err(Error::GuestBudgetExhausted);
            },
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps,
            } => steps,
            RunOutcome::Terminated { .. } => {
                return Err(Error::GuestTerminationMismatch);
            },
        };
        if guest_steps != self.trace_index
            || self.observations.len() != projected.events.len()
            || vm.input_consumed() != projected.bytes_consumed
        {
            return Err(Error::GuestIoMismatch);
        }
        if let Some(audit) = self.state.as_ref() {
            audit.finish(vm)?;
        }
        Ok(ReplayProof {
            io: SourceRecurrentIoProof {
                bytes_consumed: projected.bytes_consumed,
                guest_halt_address: self
                    .last_code
                    .ok_or(Error::GuestTerminationMismatch)?,
                guest_steps,
                observations: self.observations,
                source_return_block: projected.return_block,
                source_sha256: self.source_sha256,
                source_steps: projected.steps,
            },
            state: self.state,
        })
    }

    const fn new(state: Option<StateTrace>, source_sha256: [u8; 32]) -> Self {
        Self {
            failed: None,
            last_code: None,
            observations: Vec::new(),
            source_sha256,
            state,
            trace_index: 0,
        }
    }

    fn observe(
        &mut self,
        step: &ProfileStepTrace,
        projected: &SourceProjection,
    ) {
        if self.failed.is_none() {
            self.failed = self.reconcile(step, projected).err();
        }
        self.last_code = Some(step.before.registers.code_pointer);
        self.trace_index = self.trace_index.saturating_add(1);
    }

    fn reconcile(
        &mut self,
        step: &ProfileStepTrace,
        projected: &SourceProjection,
    ) -> Result<(), Error> {
        let event = reconcile_effect(
            step,
            self.trace_index,
            projected,
            &mut self.observations,
        )?;
        if let Some(audit) = self.state.as_mut() {
            audit.observe(step, self.trace_index, event)?;
        }
        Ok(())
    }
}

// Unlike the conservative source-path feasibility walker, this checker
// refuses every unmodeled or unknown scalar, even if its result is unused.
// Checked arithmetic failures and implementation-defined shifts also refuse.
fn exact_scalar(
    operation: &TernaryOperation,
    known: &BTreeMap<u32, u32>,
) -> Option<(u32, u32)> {
    if let Some((result, value)) = known_source_cast(operation, known)
        .or_else(|| known_source_binary(operation, known))
        .or_else(|| known_source_threshold(operation, known))
    {
        return value.map(|bits| (result, bits));
    }
    let (result, shifted) = known_source_shift(operation, known)?;
    shifted.ok().flatten().map(|bits| (result, bits))
}

fn input_effect(
    state: &mut SourceInputWalkState,
    input: &[u8],
    signed: bool,
    result: u32,
) -> Result<Effect, Error> {
    let (effect, bits) = if let Some(byte) = input.get(state.consumed) {
        state.consumed = state.consumed.saturating_add(1);
        (TraceInput::Byte(*byte), u32::from(*byte))
    } else if signed {
        (TraceInput::EndOfInput, u32::MAX)
    } else {
        return Err(Error::UnsupportedSourceExecution);
    };
    let _previous = state.known.insert(result, bits);
    Ok(Effect::Input(effect))
}

fn project_operation(
    state: &mut SourceInputWalkState,
    operation: &TernaryOperation,
    input: &[u8],
) -> Result<Option<Effect>, Error> {
    if let TernaryOperation::GetcharI32 { result, .. } = *operation {
        return input_effect(state, input, true, result).map(Some);
    }
    if let TernaryOperation::ByteInput { result, .. } = *operation {
        return input_effect(state, input, false, result).map(Some);
    }
    if let TernaryOperation::ByteOutput { value, .. } = *operation {
        let byte = state
            .known
            .get(&value)
            .and_then(|bits| u8::try_from(*bits).ok())
            .ok_or(Error::UnsupportedSourceExecution)?;
        return Ok(Some(Effect::Output(byte)));
    }
    let (result, bits) = exact_scalar(operation, &state.known)
        .ok_or(Error::UnsupportedSourceExecution)?;
    let _previous = state.known.insert(result, bits);
    Ok(None)
}

fn next_target(
    state: &SourceInputWalkState,
    terminator: TernaryCfgTerminator,
) -> Result<Option<u32>, Error> {
    match terminator {
        TernaryCfgTerminator::Jump { target, .. } => Ok(Some(target)),
        TernaryCfgTerminator::Branch {
            condition,
            false_target,
            true_target,
            ..
        } => match state.known.get(&condition) {
            Some(0) => Ok(Some(false_target)),
            Some(1) => Ok(Some(true_target)),
            _ => Err(Error::UnsupportedSourceExecution),
        },
        TernaryCfgTerminator::Return(TernaryOperation::ReturnVoid {
            ..
        }) => Ok(None),
        TernaryCfgTerminator::Return(_) => {
            Err(Error::UnsupportedSourceExecution)
        },
    }
}

fn project_reached_operation(
    state: &mut SourceInputWalkState,
    operation: &TernaryOperation,
    input: &[u8],
    journal: &mut ProjectionJournal<'_>,
) -> Result<(), Error> {
    let checkpoint = journal
        .state_plan
        .map(|plan| plan.checkpoint(state, operation))
        .transpose()?
        .flatten();
    if let Some(effect) = project_operation(state, operation, input)? {
        if journal.events.len() >= MAX_IO_EVENTS {
            return Err(Error::SourceBudgetExhausted);
        }
        journal.events.push(ProjectedIo {
            block: state.block,
            effect,
            ordinal: u32::try_from(state.operation)
                .map_err(|_error| Error::UnsupportedSourceExecution)?,
            state: checkpoint,
        });
    }
    state.operation = state.operation.saturating_add(1);
    Ok(())
}

fn project_function(
    function: &TernaryCfgFunction,
    input: &[u8],
    state_plan: Option<&StatePlan>,
) -> Result<SourceProjection, Error> {
    let mut state = SourceInputWalkState::entry(function.entry);
    let mut journal = ProjectionJournal {
        events: Vec::new(),
        state_plan,
    };
    for step in 1..=MAX_SOURCE_INPUT_CFG_SEARCH_STATES {
        let block = usize::try_from(state.block)
            .ok()
            .and_then(|index| function.blocks.get(index))
            .filter(|block| block.id == state.block)
            .ok_or(Error::UnsupportedSourceExecution)?;
        if block
            .phis
            .iter()
            .any(|phi| !state.known.contains_key(&phi.result))
        {
            return Err(Error::UnsupportedSourceExecution);
        }
        if let Some(operation) = block.operations.get(state.operation) {
            project_reached_operation(
                &mut state,
                operation,
                input,
                &mut journal,
            )?;
        } else if let Some(target) = next_target(&state, block.terminator)? {
            // Shared source semantics take every phi input from the old
            // state before committing any destination (parallel edge copy).
            state = source_successor_state(function, &state, target)
                .ok_or(Error::UnsupportedSourceExecution)?;
        } else {
            return Ok(SourceProjection {
                bytes_consumed: state.consumed,
                events: journal.events,
                function: function.id,
                return_block: block.id,
                steps: step,
            });
        }
    }
    Err(Error::SourceBudgetExhausted)
}

fn physical_effect(
    step: &ProfileStepTrace,
) -> Result<Option<PhysicalIo>, Error> {
    let profile = current_profile();
    match (step.input, step.output) {
        (Some(input), None) => {
            let raw = match input {
                TraceInput::Byte(byte) => u32::from(byte),
                TraceInput::EndOfInput => profile.eof_word(),
            };
            if step.decoded != Some(profile.input_instruction())
                || step.after.registers.accumulator != raw
                || step.result.is_err()
            {
                return Err(Error::InvalidGuestExecution);
            }
            Ok(Some((Effect::Input(input), raw)))
        },
        (None, Some(byte)) => {
            let raw = step.before.registers.accumulator;
            if step.decoded != Some(profile.output_instruction())
                || raw.rem_euclid(256) != u32::from(byte)
                || step.result.is_err()
            {
                return Err(Error::InvalidGuestExecution);
            }
            Ok(Some((Effect::Output(byte), raw)))
        },
        (None, None) => Ok(None),
        (Some(_), Some(_)) => Err(Error::InvalidGuestExecution),
    }
}

fn reconcile_effect(
    step: &ProfileStepTrace,
    trace_index: usize,
    projected: &SourceProjection,
    observations: &mut Vec<SourceRecurrentIoObservation>,
) -> Result<Option<ProjectedIo>, Error> {
    let Some((effect, raw_accumulator)) = physical_effect(step)? else {
        return Ok(None);
    };
    let expected = projected
        .events
        .get(observations.len())
        .filter(|expected| expected.effect == effect)
        .ok_or(Error::GuestIoMismatch)?;
    observations.push(SourceRecurrentIoObservation {
        block: expected.block,
        code_address: step.before.registers.code_pointer,
        effect,
        function: projected.function,
        ordinal: expected.ordinal,
        raw_accumulator,
        trace_index,
    });
    Ok(Some(*expected))
}

fn replay_guest(
    probe: SourceRecurrentIoProbe<'_>,
    projected: &SourceProjection,
    source_sha256: [u8; 32],
    state_probe: Option<&SourceRecurrentStateProbe<'_>>,
) -> Result<ReplayProof, Error> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        probe.physical_source,
        probe.input.to_vec(),
    )
    .map_err(|_error| Error::InvalidGuestExecution)?;
    let state = state_probe
        .map(|proposal| StateTrace::new(proposal, &vm))
        .transpose()?;
    let mut journal = ReplayJournal::new(state, source_sha256);
    let outcome = vm
        .run_traced(probe.step_budget, &mut |step| {
            journal.observe(step, projected);
        })
        .map_err(|_error| Error::InvalidGuestExecution)?;
    journal.finish(outcome, projected, &vm)
}

fn admit_probe(
    probe: SourceRecurrentIoProbe<'_>,
) -> Result<TernaryCfgPlan, Error> {
    if probe.step_budget == 0
        || probe.step_budget > MAX_RECURRENT_IO_STEPS
        || probe.physical_source.len() > MAX_RECURRENT_IO_SOURCE_CELLS
        || probe.physical_source.is_empty()
        || probe
            .physical_source
            .iter()
            .any(|byte| !(33..=126).contains(byte))
        || probe.input.len() > MAX_IO_EVENTS
    {
        return Err(Error::InvalidProbeBound);
    }
    lower_canonical_dynamic_cfg(probe.canonical)
        .map_err(|_error| Error::InvalidCanonicalSource)
}

/// Compare one deterministic source-CFG path against a fresh normative guest.
///
/// The canonical source independently selects all known branches, executes
/// parallel phis and projects byte/EOF effects. The guest is then executed
/// from its actual source image with the same input; no projected output or
/// source value is fed to the VM. Repeated physical code addresses can match
/// distinct logical source I/O occurrences, without modifying the stricter
/// source-placement verifier. Only a void source return is currently modeled.
///
/// # Errors
///
/// Refuses invalid/oversized probes, unsupported or unknown source semantics,
/// source and guest budget exhaustion, non-halt termination and any I/O
/// mismatch. This is not an authorization to publish a compiler artifact.
pub fn verify_source_recurrent_io(
    probe: SourceRecurrentIoProbe<'_>,
) -> Result<SourceRecurrentIoProof, SourceRecurrentIoError> {
    let cfg = admit_probe(probe)?;
    let [function] = cfg.functions.as_slice() else {
        return Err(Error::UnsupportedSourceExecution);
    };
    let projected = project_function(function, probe.input, None)?;
    replay_guest(probe, &projected, cfg.source_sha256, None)
        .map(|proof| proof.io)
}

#[cfg(test)]
#[path = "../../../../tests/compiler/source_recurrent_io.rs"]
mod source_recurrent_io_tests;
