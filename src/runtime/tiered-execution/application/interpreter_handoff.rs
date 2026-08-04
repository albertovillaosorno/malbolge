// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Normative interpreter consumption of admitted native continuations.
// - Must-Not:
//   - Call executable mappings, infer omitted state, or bypass traced VM steps.
// - Allows:
//   - Inputs: an exact continuation plus owned checkpoint or transfer buffers.
//   - Outputs: completed checkpoint/outcome or resumable indexed failure.
//   - Side effects: owned safe-Rust interpreter mutation only.
// - Split-When:
//   - Scheduling across multiple tiers or async ownership gains policy.
// - Merge-When:
//   - Native orchestration owns the complete interpreter fallback lifecycle.
// - Summary:
//   - Restores and executes the exact remaining semantic suffix normatively.
// - Description:
//   - Admits checkpoint identity and validates every traced step against IR.
// - Usage:
//   - Called after `NativeInterpreterContinuation` construction.
// - Defaults:
//   - Each mismatching step restores its entry checkpoint and fails closed.
//

//! Normative interpreter handoff for admitted native sequence continuations.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    ProfileDescriptor, ProfileMachine, ProfileMachineError,
    ProfileMachineIoState, ProfileMachineObservation, ProfileMachineState,
    RunOutcome, StepOutcome, TargetProfileRequirement, target_profile,
};

use crate::execution_ir::{RegionEffectProgram, StepProgramProjectionError};
use crate::execution_native::NativeInterpreterContinuation;

/// Failure before any interpreter transition can begin.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeInterpreterHandoffAdmissionError {
    /// The supplied checkpoint does not match the continuation observation.
    CheckpointObservation,
    /// The supplied checkpoint selected a different canonical profile.
    CheckpointProfile,
    /// A required first-step memory value differs before interpreter work.
    LiveIn {
        /// Exact guest address checked before execution.
        address: u32,
        /// Value retained by the verified one-step program.
        expected: u32,
        /// Value supplied by the transferred checkpoint.
        observed: u32,
    },
    /// One required first-step address is outside the checkpoint image.
    LiveInAddress {
        /// Exact guest address that could not be inspected.
        address: u32,
    },
    /// The continuation unexpectedly retained no semantic work.
    NoRemainingWork,
    /// A remaining program changed canonical profile identity.
    ProfileDrift {
        /// Zero-based position within the remaining suffix.
        index: usize,
    },
    /// The canonical profile fingerprint differs from the retained IR.
    ProfileFingerprint,
    /// Canonical profile geometry/features differ from the retained IR.
    ProfileRequirement,
    /// The transferred output buffer is shorter than committed output.
    ShortOutput {
        /// Committed output length declared by the continuation.
        expected: usize,
        /// Supplied transfer-buffer length.
        observed: usize,
    },
    /// Complete checkpoint construction rejected transferred state.
    State(ProfileMachineError),
    /// The continuation names no canonical profile in the runtime registry.
    UnknownProfile,
}

/// Why normative continuation execution stopped without completion.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeInterpreterHandoffExecutionCause {
    /// Final interpreter observation differs from the verified plan exit.
    FinalObservation,
    /// One step's entry memory no longer matches its verified live-ins.
    LiveIn {
        /// Exact guest address checked at this step boundary.
        address: u32,
        /// Value retained by the verified one-step program.
        expected: u32,
        /// Value observed in the last admitted checkpoint.
        observed: u32,
    },
    /// One required live-in address is outside the transferred image.
    LiveInAddress {
        /// Exact guest address that could not be inspected.
        address: u32,
    },
    /// The normative profile machine rejected one requested step.
    Machine(ProfileMachineError),
    /// Combined native/interpreter outcome differs from the verified plan.
    Outcome,
    /// A terminating step occurred before all remaining programs were consumed.
    PrematureTermination,
    /// The traced normative transition differs from the retained program.
    ProgramMismatch,
    /// The normative trace could not project to one complete portable program.
    Projection(StepProgramProjectionError),
}

/// Owned application boundary ready to execute one continuation normatively.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeInterpreterHandoff {
    checkpoint: ProfileMachineState,
    continuation: NativeInterpreterContinuation,
}

/// Successful normative consumption of one native continuation.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeInterpreterHandoffCompletion {
    continuation: NativeInterpreterContinuation,
    interpreter_outcome: RunOutcome,
    outcome: RunOutcome,
    state: ProfileMachineState,
}

/// Indexed fail-closed result retaining the last admitted interpreter state.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeInterpreterHandoffExecutionFailure {
    cause: NativeInterpreterHandoffExecutionCause,
    continuation: NativeInterpreterContinuation,
    interpreter_steps: usize,
    resume_index: usize,
    state: ProfileMachineState,
}

#[derive(Debug, Eq, PartialEq)]
struct NativeInterpreterStepFailure {
    cause: NativeInterpreterHandoffExecutionCause,
    state: ProfileMachineState,
}

/// Result of consuming one exact continuation in the normative interpreter.
pub type NativeInterpreterHandoffExecutionResult = Result<
    NativeInterpreterHandoffCompletion,
    Box<NativeInterpreterHandoffExecutionFailure>,
>;

impl Display for NativeInterpreterHandoffAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::CheckpointObservation => {
                f.write_str("interpreter checkpoint observation drifted")
            },
            Self::CheckpointProfile => {
                f.write_str("interpreter checkpoint profile drifted")
            },
            Self::LiveInAddress { address } => {
                write!(
                    f,
                    "interpreter live-in address {address} is unavailable"
                )
            },
            Self::LiveIn {
                address,
                expected,
                observed,
            } => write!(
                f,
                "live-in {address}: expected {expected}, got {observed}",
            ),
            Self::NoRemainingWork => {
                f.write_str("interpreter handoff has no remaining work")
            },
            Self::ProfileDrift { index } => {
                write!(f, "interpreter profile drifted at suffix step {index}")
            },
            Self::ProfileFingerprint => {
                f.write_str("interpreter profile fingerprint drifted")
            },
            Self::ProfileRequirement => {
                f.write_str("interpreter profile requirement drifted")
            },
            Self::ShortOutput { expected, observed } => {
                write!(f, "output transfer has {observed} of {expected} bytes")
            },
            Self::State(error) => {
                write!(f, "interpreter checkpoint rejected: {error}")
            },
            Self::UnknownProfile => {
                f.write_str("interpreter continuation profile is unknown")
            },
        }
    }
}

impl Display for NativeInterpreterHandoffExecutionCause {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::FinalObservation => {
                f.write_str("interpreter final observation drifted")
            },
            Self::LiveInAddress { address } => {
                write!(
                    f,
                    "interpreter live-in address {address} is unavailable"
                )
            },
            Self::LiveIn {
                address,
                expected,
                observed,
            } => write!(
                f,
                "live-in {address}: expected {expected}, got {observed}",
            ),
            Self::Machine(error) => {
                write!(f, "interpreter step failed: {error}")
            },
            Self::Outcome => {
                f.write_str("interpreter combined outcome drifted")
            },
            Self::PrematureTermination => {
                f.write_str("interpreter terminated before suffix completion")
            },
            Self::ProgramMismatch => {
                f.write_str("interpreter trace differs from retained IR")
            },
            Self::Projection(error) => {
                write!(
                    f,
                    "interpreter trace projection failed: {}",
                    projection_error_id(*error),
                )
            },
        }
    }
}

impl Display for NativeInterpreterHandoffExecutionFailure {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "interpreter handoff failed after {} steps at index {}: {}",
            self.interpreter_steps, self.resume_index, self.cause,
        )
    }
}

impl NativeInterpreterHandoff {
    /// Executes all remaining verified programs in the normative interpreter.
    ///
    /// Each requested step is traced and reprojected to portable IR. A machine
    /// error, live-in mismatch, projection failure, or IR drift returns the
    /// current-step entry checkpoint rather than publishing partial mutation.
    ///
    /// # Errors
    ///
    /// Returns [`NativeInterpreterHandoffExecutionFailure`] with the exact last
    /// admitted checkpoint and resume index.
    pub fn execute(self) -> NativeInterpreterHandoffExecutionResult {
        let Self { checkpoint, continuation } = self;
        let mut machine = ProfileMachine::from_snapshot(checkpoint);
        let remaining_steps = continuation.remaining_steps();
        let mut interpreter_steps = 0usize;
        let mut termination = None;
        for offset in 0..remaining_steps {
            let Some(expected) =
                continuation.remaining_programs().get(offset).cloned()
            else {
                return Err(execution_failure(
                    NativeInterpreterHandoffExecutionCause::ProgramMismatch,
                    continuation,
                    interpreter_steps,
                    machine.snapshot_state(),
                ));
            };
            let outcome = match execute_handoff_step(&mut machine, &expected) {
                Ok(outcome) => outcome,
                Err(failure) => {
                    let NativeInterpreterStepFailure { cause, state } =
                        *failure;
                    return Err(execution_failure(
                        cause,
                        continuation,
                        interpreter_steps,
                        state,
                    ));
                },
            };
            interpreter_steps = interpreter_steps.saturating_add(1);
            termination = termination_after_step(termination, outcome);
            if termination.is_some() && interpreter_steps != remaining_steps {
                return Err(execution_failure(
                    NativeInterpreterHandoffExecutionCause::
                        PrematureTermination,
                    continuation,
                    interpreter_steps,
                    machine.snapshot_state(),
                ));
            }
        }
        complete_handoff(
            continuation,
            interpreter_steps,
            machine.snapshot_state(),
            termination,
        )
    }

    /// Constructs a handoff from native transfer buffers.
    ///
    /// Only the output prefix declared committed by the continuation is copied
    /// into the interpreter checkpoint. Trailing output capacity is ignored.
    ///
    /// # Errors
    ///
    /// Returns [`NativeInterpreterHandoffAdmissionError`] when profile
    /// identity, buffer shape, checkpoint observation, or first-step
    /// live-ins drift.
    pub fn from_buffers(
        continuation: NativeInterpreterContinuation,
        memory: Vec<u32>,
        input: Vec<u8>,
        output: &[u8],
    ) -> Result<Self, NativeInterpreterHandoffAdmissionError> {
        let profile = continuation_profile(&continuation)?;
        let observation = continuation.observation();
        let committed_output = output.get(..observation.output_len).ok_or(
            NativeInterpreterHandoffAdmissionError::ShortOutput {
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
        .map_err(NativeInterpreterHandoffAdmissionError::State)?;
        let state = ProfileMachineState::new(
            profile,
            memory,
            observation.registers,
            io,
        )
        .map_err(NativeInterpreterHandoffAdmissionError::State)?;
        admit_handoff(continuation, state, profile)
    }

    /// Constructs a handoff from one already validated complete checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`NativeInterpreterHandoffAdmissionError`] when profile
    /// identity, checkpoint observation, or first-step live-ins drift.
    pub fn from_checkpoint(
        continuation: NativeInterpreterContinuation,
        checkpoint: ProfileMachineState,
    ) -> Result<Self, NativeInterpreterHandoffAdmissionError> {
        let profile = continuation_profile(&continuation)?;
        admit_handoff(continuation, checkpoint, profile)
    }
}

impl NativeInterpreterHandoffCompletion {
    /// Returns the exact continuation consumed by this completion.
    #[must_use]
    pub const fn continuation(&self) -> &NativeInterpreterContinuation {
        &self.continuation
    }

    /// Returns the relative outcome produced by interpreter-only work.
    #[must_use]
    pub const fn interpreter_outcome(&self) -> RunOutcome {
        self.interpreter_outcome
    }

    /// Returns the combined native-prefix and interpreter-suffix outcome.
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

impl NativeInterpreterHandoffExecutionFailure {
    /// Returns the exact reason interpreter handoff failed.
    #[must_use]
    pub const fn cause(&self) -> NativeInterpreterHandoffExecutionCause {
        self.cause
    }

    /// Returns the original exact semantic continuation.
    #[must_use]
    pub const fn continuation(&self) -> &NativeInterpreterContinuation {
        &self.continuation
    }

    /// Returns normative interpreter steps committed after native progress.
    #[must_use]
    pub const fn interpreter_steps(&self) -> usize {
        self.interpreter_steps
    }

    /// Returns the next complete-plan semantic index for later execution.
    #[must_use]
    pub const fn resume_index(&self) -> usize {
        self.resume_index
    }

    /// Returns the last fully admitted normative checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

fn admission_live_in_error(
    program: &RegionEffectProgram,
    memory: &[u32],
) -> Option<NativeInterpreterHandoffAdmissionError> {
    for live_in in &program.memory_live_ins {
        let Ok(index) = usize::try_from(live_in.address) else {
            return Some(
                NativeInterpreterHandoffAdmissionError::LiveInAddress {
                    address: live_in.address,
                },
            );
        };
        let Some(observed) = memory.get(index).copied() else {
            return Some(
                NativeInterpreterHandoffAdmissionError::LiveInAddress {
                    address: live_in.address,
                },
            );
        };
        if observed != live_in.value {
            return Some(NativeInterpreterHandoffAdmissionError::LiveIn {
                address: live_in.address,
                expected: live_in.value,
                observed,
            });
        }
    }
    None
}

fn admit_handoff(
    continuation: NativeInterpreterContinuation,
    checkpoint: ProfileMachineState,
    profile: &'static ProfileDescriptor,
) -> Result<NativeInterpreterHandoff, NativeInterpreterHandoffAdmissionError> {
    if checkpoint.profile() != profile {
        return Err(NativeInterpreterHandoffAdmissionError::CheckpointProfile);
    }
    if state_observation(&checkpoint) != continuation.observation() {
        return Err(
            NativeInterpreterHandoffAdmissionError::CheckpointObservation,
        );
    }
    let Some(first) = continuation.remaining_programs().first() else {
        return Err(NativeInterpreterHandoffAdmissionError::NoRemainingWork);
    };
    if let Some(error) = admission_live_in_error(first, checkpoint.memory()) {
        return Err(error);
    }
    Ok(NativeInterpreterHandoff { checkpoint, continuation })
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

fn complete_handoff(
    continuation: NativeInterpreterContinuation,
    interpreter_steps: usize,
    state: ProfileMachineState,
    termination: Option<malbolge::Termination>,
) -> NativeInterpreterHandoffExecutionResult {
    let interpreter_outcome = termination.map_or(
        RunOutcome::BudgetExhausted { steps: interpreter_steps },
        |reason| RunOutcome::Terminated {
            reason,
            steps: interpreter_steps,
        },
    );
    let outcome =
        combined_outcome(interpreter_outcome, continuation.completed_steps());
    if state_observation(&state) != continuation.expected_exit() {
        return Err(execution_failure(
            NativeInterpreterHandoffExecutionCause::FinalObservation,
            continuation,
            interpreter_steps,
            state,
        ));
    }
    if outcome != continuation.expected_outcome() {
        return Err(execution_failure(
            NativeInterpreterHandoffExecutionCause::Outcome,
            continuation,
            interpreter_steps,
            state,
        ));
    }
    Ok(NativeInterpreterHandoffCompletion {
        continuation,
        interpreter_outcome,
        outcome,
        state,
    })
}

fn continuation_profile(
    continuation: &NativeInterpreterContinuation,
) -> Result<&'static ProfileDescriptor, NativeInterpreterHandoffAdmissionError>
{
    let Some(first) = continuation.remaining_programs().first() else {
        return Err(NativeInterpreterHandoffAdmissionError::NoRemainingWork);
    };
    let Some(profile) = target_profile(&first.profile_id) else {
        return Err(NativeInterpreterHandoffAdmissionError::UnknownProfile);
    };
    if profile.fingerprint() != first.profile_fingerprint {
        return Err(NativeInterpreterHandoffAdmissionError::ProfileFingerprint);
    }
    if TargetProfileRequirement::from_descriptor(profile)
        != first.profile_requirement
    {
        return Err(NativeInterpreterHandoffAdmissionError::ProfileRequirement);
    }
    for (index, program) in continuation.remaining_programs().iter().enumerate()
    {
        if program.profile_id != first.profile_id
            || program.profile_fingerprint != first.profile_fingerprint
            || program.profile_requirement != first.profile_requirement
        {
            return Err(NativeInterpreterHandoffAdmissionError::ProfileDrift {
                index,
            });
        }
    }
    Ok(profile)
}

fn execute_handoff_step(
    machine: &mut ProfileMachine,
    expected: &RegionEffectProgram,
) -> Result<StepOutcome, Box<NativeInterpreterStepFailure>> {
    let entry = machine.snapshot_state();
    if let Some(cause) = live_in_cause(expected, entry.memory()) {
        return Err(Box::new(NativeInterpreterStepFailure {
            cause,
            state: entry,
        }));
    }
    let mut trace_slot = None;
    let outcome = machine
        .step_traced(&mut |trace| trace_slot = Some(*trace))
        .map_err(|error| {
            Box::new(NativeInterpreterStepFailure {
                cause: NativeInterpreterHandoffExecutionCause::Machine(error),
                state: entry.clone(),
            })
        })?;
    let Some(observed_trace) = trace_slot else {
        return Err(Box::new(NativeInterpreterStepFailure {
            cause: NativeInterpreterHandoffExecutionCause::ProgramMismatch,
            state: entry,
        }));
    };
    let projected = RegionEffectProgram::from_profile_step_trace(
        &observed_trace,
    )
    .map_err(|error| {
        Box::new(NativeInterpreterStepFailure {
            cause: NativeInterpreterHandoffExecutionCause::Projection(error),
            state: entry.clone(),
        })
    })?;
    if projected != *expected {
        return Err(Box::new(NativeInterpreterStepFailure {
            cause: NativeInterpreterHandoffExecutionCause::ProgramMismatch,
            state: entry,
        }));
    }
    Ok(outcome)
}

fn execution_failure(
    cause: NativeInterpreterHandoffExecutionCause,
    continuation: NativeInterpreterContinuation,
    interpreter_steps: usize,
    state: ProfileMachineState,
) -> Box<NativeInterpreterHandoffExecutionFailure> {
    let resume_index = continuation
        .completed_steps()
        .saturating_add(interpreter_steps);
    Box::new(NativeInterpreterHandoffExecutionFailure {
        cause,
        continuation,
        interpreter_steps,
        resume_index,
        state,
    })
}

fn live_in_cause(
    program: &RegionEffectProgram,
    memory: &[u32],
) -> Option<NativeInterpreterHandoffExecutionCause> {
    for live_in in &program.memory_live_ins {
        let Ok(index) = usize::try_from(live_in.address) else {
            return Some(
                NativeInterpreterHandoffExecutionCause::LiveInAddress {
                    address: live_in.address,
                },
            );
        };
        let Some(observed) = memory.get(index).copied() else {
            return Some(
                NativeInterpreterHandoffExecutionCause::LiveInAddress {
                    address: live_in.address,
                },
            );
        };
        if observed != live_in.value {
            return Some(NativeInterpreterHandoffExecutionCause::LiveIn {
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
