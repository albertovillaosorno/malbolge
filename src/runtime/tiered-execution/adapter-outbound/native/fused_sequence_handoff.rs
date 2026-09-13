// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Complete normative interpreter consumption of one fused continuation.
// - Must-Not:
//   - Call native mappings, mutate caches, budget/schedule, or infer omitted
//     IR.
// - Allows:
//   - Inputs: fused continuation plus owned checkpoint or transfer buffers.
//   - Outputs: exact completion or indexed fail-closed interpreter evidence.
//   - Side effects: owned safe-Rust interpreter mutation only.
// - Split-When:
//   - Budget suspension, scheduling, or native retry gains policy.
// - Merge-When:
//   - One fused coordinator owns the complete fallback lifecycle.
// - Summary:
//   - Executes fused continuation source programs in the normative interpreter.
// - Description:
//   - Every step is traced/reprojected and mismatches restore its entry state.
// - Usage:
//   - Construct from exact buffers/checkpoint, then execute to completion.
// - Defaults:
//   - Admission checks profile, observation, and first-step live-ins exactly.
//

//! Complete normative interpreter handoff for fused native continuations.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    ProfileDescriptor, ProfileMachine, ProfileMachineError,
    ProfileMachineIoState, ProfileMachineObservation, ProfileMachineState,
    RegionEffectProgram, RunOutcome, StepOutcome, StepProgramProjectionError,
    TargetProfileRequirement, target_profile,
};

use super::fused_sequence_continuation::DirectFusedNativeContinuation;

/// Rejection before fused continuation interpreter work can begin.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeHandoffAdmissionError {
    /// Checkpoint geometry differs from continuation authority.
    CheckpointGeometry,
    /// Checkpoint observation differs from continuation authority.
    CheckpointObservation,
    /// Checkpoint profile differs from the continuation's canonical profile.
    CheckpointProfile,
    /// Required first-step memory differs before interpreter work.
    LiveIn {
        /// Exact guest address checked before execution.
        address: u32,
        /// Verified required value.
        expected: u32,
        /// Supplied checkpoint value.
        observed: u32,
    },
    /// Required first-step address is unavailable in the checkpoint.
    LiveInAddress {
        /// Exact guest address that could not be inspected.
        address: u32,
    },
    /// Continuation unexpectedly retains no semantic work.
    NoRemainingWork,
    /// One remaining source program changed canonical profile identity.
    ProfileDrift {
        /// Zero-based remaining source-program position.
        index: usize,
    },
    /// Canonical profile fingerprint differs from retained source IR.
    ProfileFingerprint,
    /// Canonical profile requirement differs from retained source IR.
    ProfileRequirement,
    /// Transfer output is shorter than already committed output.
    ShortOutput {
        /// Exact committed output length.
        expected: usize,
        /// Supplied transfer output length.
        observed: usize,
    },
    /// Checkpoint construction rejected transferred state.
    State(ProfileMachineError),
    /// Continuation names no canonical runtime profile.
    UnknownProfile,
}

/// Why normative fused-continuation execution failed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeHandoffExecutionCause {
    /// Final interpreter observation differs from the verified plan exit.
    FinalObservation,
    /// One step's entry memory differs from retained verified live-ins.
    LiveIn {
        /// Exact guest address checked at this step boundary.
        address: u32,
        /// Verified required value.
        expected: u32,
        /// Observed checkpoint value.
        observed: u32,
    },
    /// One required live-in address is outside the transferred image.
    LiveInAddress {
        /// Exact guest address that could not be inspected.
        address: u32,
    },
    /// The normative profile machine rejected one requested step.
    Machine(ProfileMachineError),
    /// Combined native-prefix/interpreter-suffix outcome differs from the plan.
    Outcome,
    /// A terminating step occurred before all remaining source programs ran.
    PrematureTermination,
    /// Normative trace differs from the retained verified source program.
    ProgramMismatch,
    /// Normative trace could not project to one complete portable program.
    Projection(StepProgramProjectionError),
}

/// Owned fused continuation ready for complete normative interpreter execution.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeInterpreterHandoff {
    checkpoint: ProfileMachineState,
    continuation: DirectFusedNativeContinuation,
}

/// Successful complete normative fused fallback.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeHandoffCompletion {
    continuation: DirectFusedNativeContinuation,
    interpreter_outcome: RunOutcome,
    outcome: RunOutcome,
    state: ProfileMachineState,
}

/// Fail-closed fused interpreter result retaining last admitted state.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeHandoffExecutionFailure {
    cause: DirectFusedNativeHandoffExecutionCause,
    continuation: DirectFusedNativeContinuation,
    interpreter_steps: usize,
    resume_step: usize,
    state: ProfileMachineState,
}

#[derive(Debug, Eq, PartialEq)]
struct DirectFusedNativeStepFailure {
    cause: DirectFusedNativeHandoffExecutionCause,
    state: ProfileMachineState,
}

/// Result of completely consuming one fused continuation normatively.
pub type DirectFusedNativeHandoffExecutionResult = Result<
    DirectFusedNativeHandoffCompletion,
    Box<DirectFusedNativeHandoffExecutionFailure>,
>;

impl Display for DirectFusedNativeHandoffAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::CheckpointGeometry => {
                f.write_str("fused checkpoint geometry drifted")
            },
            Self::CheckpointObservation => {
                f.write_str("fused checkpoint observation drifted")
            },
            Self::CheckpointProfile => {
                f.write_str("fused checkpoint profile drifted")
            },
            Self::LiveIn {
                address,
                expected,
                observed,
            } => write!(
                f,
                "fused live-in {address}: expected {expected}, got {observed}",
            ),
            Self::LiveInAddress { address } => {
                write!(f, "fused live-in address {address} is unavailable")
            },
            Self::NoRemainingWork => {
                f.write_str("fused handoff has no remaining work")
            },
            Self::ProfileDrift { index } => {
                write!(
                    f,
                    "fused handoff profile drifted at source step {index}"
                )
            },
            Self::ProfileFingerprint => {
                f.write_str("fused handoff profile fingerprint drifted")
            },
            Self::ProfileRequirement => {
                f.write_str("fused handoff profile requirement drifted")
            },
            Self::ShortOutput { expected, observed } => {
                write!(
                    f,
                    "fused output transfer has {observed} of {expected} bytes"
                )
            },
            Self::State(error) => {
                write!(f, "fused checkpoint rejected: {error}")
            },
            Self::UnknownProfile => {
                f.write_str("fused handoff profile is unknown")
            },
        }
    }
}

impl Display for DirectFusedNativeHandoffExecutionCause {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::FinalObservation => {
                f.write_str("fused handoff final observation drifted")
            },
            Self::LiveIn {
                address,
                expected,
                observed,
            } => write!(
                f,
                "fused live-in {address}: expected {expected}, got {observed}",
            ),
            Self::LiveInAddress { address } => {
                write!(f, "fused live-in address {address} is unavailable")
            },
            Self::Machine(error) => {
                write!(f, "fused interpreter step failed: {error}")
            },
            Self::Outcome => {
                f.write_str("fused handoff combined outcome drifted")
            },
            Self::PrematureTermination => f.write_str(
                "fused interpreter terminated before suffix completion",
            ),
            Self::ProgramMismatch => {
                f.write_str("fused interpreter trace differs from retained IR")
            },
            Self::Projection(error) => write!(
                f,
                "fused interpreter projection failed: {}",
                projection_error_id(*error),
            ),
        }
    }
}

impl Display for DirectFusedNativeHandoffExecutionFailure {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "fused interpreter handoff failed after {} steps at {}: {}",
            self.interpreter_steps, self.resume_step, self.cause,
        )
    }
}

impl DirectFusedNativeHandoffCompletion {
    /// Returns the exact continuation consumed by this completion.
    #[must_use]
    pub const fn continuation(&self) -> &DirectFusedNativeContinuation {
        &self.continuation
    }

    /// Returns the outcome produced by interpreter-only suffix work.
    #[must_use]
    pub const fn interpreter_outcome(&self) -> RunOutcome {
        self.interpreter_outcome
    }

    /// Returns the complete native-prefix plus interpreter-suffix outcome.
    #[must_use]
    pub const fn outcome(&self) -> RunOutcome {
        self.outcome
    }

    /// Returns the final validated normative machine checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl DirectFusedNativeHandoffExecutionFailure {
    /// Returns the exact reason fused interpreter handoff failed.
    #[must_use]
    pub const fn cause(&self) -> DirectFusedNativeHandoffExecutionCause {
        self.cause
    }

    /// Returns the original fused semantic continuation.
    #[must_use]
    pub const fn continuation(&self) -> &DirectFusedNativeContinuation {
        &self.continuation
    }

    /// Returns interpreter steps committed after native fused progress.
    #[must_use]
    pub const fn interpreter_steps(&self) -> usize {
        self.interpreter_steps
    }

    /// Returns the next complete-plan source semantic-step index.
    #[must_use]
    pub const fn resume_step(&self) -> usize {
        self.resume_step
    }

    /// Returns the last fully admitted normative checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl DirectFusedNativeInterpreterHandoff {
    /// Executes every remaining verified source program normatively.
    ///
    /// # Errors
    ///
    /// Returns indexed failure with the exact current-step entry checkpoint.
    pub fn execute(self) -> DirectFusedNativeHandoffExecutionResult {
        let Self { checkpoint, continuation } = self;
        execute_handoff(continuation, checkpoint)
    }

    /// Constructs a fused handoff from native transfer buffers.
    ///
    /// # Errors
    ///
    /// Returns exact profile, shape, observation, or first-live-in rejection.
    pub fn from_buffers(
        continuation: DirectFusedNativeContinuation,
        memory: Vec<u32>,
        input: Vec<u8>,
        output: &[u8],
    ) -> Result<Self, DirectFusedNativeHandoffAdmissionError> {
        let profile = continuation_profile(&continuation)?;
        let observation = continuation.observation();
        let committed_output = output.get(..observation.output_len).ok_or(
            DirectFusedNativeHandoffAdmissionError::ShortOutput {
                expected: observation.output_len,
                observed: output.len(),
            },
        )?;
        let io = ProfileMachineIoState::new(
            input,
            observation.input_consumed,
            committed_output.to_vec(),
            observation.termination,
        )
        .map_err(DirectFusedNativeHandoffAdmissionError::State)?;
        let state = ProfileMachineState::new_with_geometry(
            continuation.geometry(),
            memory,
            observation.registers,
            io,
        )
        .map_err(DirectFusedNativeHandoffAdmissionError::State)?;
        admit_handoff(continuation, state, profile)
    }

    /// Constructs a fused handoff from one complete checkpoint.
    ///
    /// # Errors
    ///
    /// Returns exact profile, geometry, observation, or first-live-in
    /// rejection.
    pub fn from_checkpoint(
        continuation: DirectFusedNativeContinuation,
        checkpoint: ProfileMachineState,
    ) -> Result<Self, DirectFusedNativeHandoffAdmissionError> {
        let profile = continuation_profile(&continuation)?;
        admit_handoff(continuation, checkpoint, profile)
    }
}

fn admit_handoff(
    continuation: DirectFusedNativeContinuation,
    checkpoint: ProfileMachineState,
    profile: &'static ProfileDescriptor,
) -> Result<
    DirectFusedNativeInterpreterHandoff,
    DirectFusedNativeHandoffAdmissionError,
> {
    if checkpoint.profile() != profile {
        return Err(DirectFusedNativeHandoffAdmissionError::CheckpointProfile);
    }
    if checkpoint.geometry() != continuation.geometry() {
        return Err(DirectFusedNativeHandoffAdmissionError::CheckpointGeometry);
    }
    if state_observation(&checkpoint) != continuation.observation() {
        return Err(
            DirectFusedNativeHandoffAdmissionError::CheckpointObservation,
        );
    }
    let Some(first) = continuation.remaining_programs().first() else {
        return Err(DirectFusedNativeHandoffAdmissionError::NoRemainingWork);
    };
    if let Some(error) = admission_live_in_error(first, checkpoint.memory()) {
        return Err(error);
    }
    Ok(DirectFusedNativeInterpreterHandoff { checkpoint, continuation })
}

fn admission_live_in_error(
    program: &RegionEffectProgram,
    memory: &[u32],
) -> Option<DirectFusedNativeHandoffAdmissionError> {
    for live_in in &program.memory_live_ins {
        let Ok(index) = usize::try_from(live_in.address) else {
            return Some(
                DirectFusedNativeHandoffAdmissionError::LiveInAddress {
                    address: live_in.address,
                },
            );
        };
        let Some(observed) = memory.get(index).copied() else {
            return Some(
                DirectFusedNativeHandoffAdmissionError::LiveInAddress {
                    address: live_in.address,
                },
            );
        };
        if observed != live_in.value {
            return Some(DirectFusedNativeHandoffAdmissionError::LiveIn {
                address: live_in.address,
                expected: live_in.value,
                observed,
            });
        }
    }
    None
}

const fn combined_outcome(outcome: RunOutcome, completed: usize) -> RunOutcome {
    match outcome {
        RunOutcome::BudgetExhausted { steps } => RunOutcome::BudgetExhausted {
            steps: completed.saturating_add(steps),
        },
        RunOutcome::Terminated { reason, steps } => RunOutcome::Terminated {
            reason,
            steps: completed.saturating_add(steps),
        },
    }
}

fn continuation_profile(
    continuation: &DirectFusedNativeContinuation,
) -> Result<&'static ProfileDescriptor, DirectFusedNativeHandoffAdmissionError>
{
    let Some(first) = continuation.remaining_programs().first() else {
        return Err(DirectFusedNativeHandoffAdmissionError::NoRemainingWork);
    };
    let Some(profile) = target_profile(&first.profile_id) else {
        return Err(DirectFusedNativeHandoffAdmissionError::UnknownProfile);
    };
    if profile.fingerprint() != first.profile_fingerprint {
        return Err(DirectFusedNativeHandoffAdmissionError::ProfileFingerprint);
    }
    if TargetProfileRequirement::from_descriptor(profile)
        != first.profile_requirement
    {
        return Err(DirectFusedNativeHandoffAdmissionError::ProfileRequirement);
    }
    for (index, program) in continuation.remaining_programs().iter().enumerate()
    {
        if program.profile_id != first.profile_id
            || program.profile_fingerprint != first.profile_fingerprint
            || program.profile_requirement != first.profile_requirement
        {
            return Err(DirectFusedNativeHandoffAdmissionError::ProfileDrift {
                index,
            });
        }
    }
    Ok(profile)
}

fn execute_handoff(
    continuation: DirectFusedNativeContinuation,
    checkpoint: ProfileMachineState,
) -> DirectFusedNativeHandoffExecutionResult {
    let mut machine = ProfileMachine::from_snapshot(checkpoint);
    let mut termination = machine.snapshot_state().io().termination();
    let programs = continuation.remaining_programs().to_vec();
    for (index, expected) in programs.iter().enumerate() {
        let outcome = match execute_step(&mut machine, expected) {
            Ok(outcome) => outcome,
            Err(failure) => {
                return Err(execution_failure(
                    failure.cause,
                    continuation,
                    index,
                    failure.state,
                ));
            },
        };
        termination = termination_after_step(termination, outcome);
        if termination.is_some() && index.saturating_add(1) != programs.len() {
            return Err(execution_failure(
                DirectFusedNativeHandoffExecutionCause::PrematureTermination,
                continuation,
                index.saturating_add(1),
                machine.snapshot_state(),
            ));
        }
    }
    complete_handoff(
        continuation,
        programs.len(),
        machine.snapshot_state(),
        termination,
    )
}

fn execute_step(
    machine: &mut ProfileMachine,
    expected: &RegionEffectProgram,
) -> Result<StepOutcome, Box<DirectFusedNativeStepFailure>> {
    let entry = machine.snapshot_state();
    if let Some(cause) = live_in_cause(expected, entry.memory()) {
        return Err(Box::new(DirectFusedNativeStepFailure {
            cause,
            state: entry,
        }));
    }
    let mut trace_slot = None;
    let outcome = machine
        .step_traced(&mut |trace| trace_slot = Some(*trace))
        .map_err(|error| {
            Box::new(DirectFusedNativeStepFailure {
                cause: DirectFusedNativeHandoffExecutionCause::Machine(error),
                state: entry.clone(),
            })
        })?;
    let Some(trace) = trace_slot else {
        return Err(Box::new(DirectFusedNativeStepFailure {
            cause: DirectFusedNativeHandoffExecutionCause::ProgramMismatch,
            state: entry,
        }));
    };
    let projected = RegionEffectProgram::from_profile_step_trace(&trace)
        .map_err(|error| DirectFusedNativeStepFailure {
            cause: DirectFusedNativeHandoffExecutionCause::Projection(error),
            state: entry.clone(),
        })?;
    if projected != *expected {
        return Err(Box::new(DirectFusedNativeStepFailure {
            cause: DirectFusedNativeHandoffExecutionCause::ProgramMismatch,
            state: entry,
        }));
    }
    Ok(outcome)
}

fn complete_handoff(
    continuation: DirectFusedNativeContinuation,
    interpreter_steps: usize,
    state: ProfileMachineState,
    termination: Option<malbolge::Termination>,
) -> DirectFusedNativeHandoffExecutionResult {
    let interpreter_outcome = termination.map_or(
        RunOutcome::BudgetExhausted { steps: interpreter_steps },
        |reason| RunOutcome::Terminated {
            reason,
            steps: interpreter_steps,
        },
    );
    let outcome =
        combined_outcome(interpreter_outcome, continuation.resume_step());
    if state_observation(&state) != continuation.expected_exit() {
        return Err(execution_failure(
            DirectFusedNativeHandoffExecutionCause::FinalObservation,
            continuation,
            interpreter_steps,
            state,
        ));
    }
    if outcome != continuation.expected_outcome() {
        return Err(execution_failure(
            DirectFusedNativeHandoffExecutionCause::Outcome,
            continuation,
            interpreter_steps,
            state,
        ));
    }
    Ok(DirectFusedNativeHandoffCompletion {
        continuation,
        interpreter_outcome,
        outcome,
        state,
    })
}

fn execution_failure(
    cause: DirectFusedNativeHandoffExecutionCause,
    continuation: DirectFusedNativeContinuation,
    interpreter_steps: usize,
    state: ProfileMachineState,
) -> Box<DirectFusedNativeHandoffExecutionFailure> {
    let resume_step =
        continuation.resume_step().saturating_add(interpreter_steps);
    Box::new(DirectFusedNativeHandoffExecutionFailure {
        cause,
        continuation,
        interpreter_steps,
        resume_step,
        state,
    })
}

fn live_in_cause(
    program: &RegionEffectProgram,
    memory: &[u32],
) -> Option<DirectFusedNativeHandoffExecutionCause> {
    for live_in in &program.memory_live_ins {
        let Ok(index) = usize::try_from(live_in.address) else {
            return Some(
                DirectFusedNativeHandoffExecutionCause::LiveInAddress {
                    address: live_in.address,
                },
            );
        };
        let Some(observed) = memory.get(index).copied() else {
            return Some(
                DirectFusedNativeHandoffExecutionCause::LiveInAddress {
                    address: live_in.address,
                },
            );
        };
        if observed != live_in.value {
            return Some(DirectFusedNativeHandoffExecutionCause::LiveIn {
                address: live_in.address,
                expected: live_in.value,
                observed,
            });
        }
    }
    None
}

const fn projection_error_id(
    error: StepProgramProjectionError,
) -> &'static str {
    match error {
        StepProgramProjectionError::ConflictingMemoryRead => {
            "conflicting-memory-read"
        },
        StepProgramProjectionError::ExecutionGeometry => "execution-geometry",
        StepProgramProjectionError::FetchAddress => "fetch-address",
        StepProgramProjectionError::FetchValue => "fetch-value",
        StepProgramProjectionError::MissingFetch => "missing-fetch",
        StepProgramProjectionError::Outcome => "outcome",
        StepProgramProjectionError::RejectedTrace => "rejected-trace",
        StepProgramProjectionError::TerminatedEntry => "terminated-entry",
    }
}

fn state_observation(state: &ProfileMachineState) -> ProfileMachineObservation {
    ProfileMachineObservation {
        input_consumed: state.io().input_consumed(),
        output_len: state.io().output().len(),
        registers: state.registers(),
        termination: state.io().termination(),
    }
}

const fn termination_after_step(
    prior: Option<malbolge::Termination>,
    outcome: StepOutcome,
) -> Option<malbolge::Termination> {
    match outcome {
        StepOutcome::Continued => prior,
        StepOutcome::Terminated(reason) => Some(reason),
    }
}
