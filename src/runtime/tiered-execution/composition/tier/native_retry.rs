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
//   - Exact admission of caller-replanned native continuation suffixes.
// - Must-Not:
//   - Execute mappings, infer a plan, or discard affine checkpoint ownership.
// - Allows:
//   - Inputs: one native-retry suspension and one verified direct plan.
//   - Outputs: an admitted retry owner or a retryable ownership-preserving
//     error.
//   - Side effects: process-local comparison only.
// - Split-When:
//   - Retry execution, cached planning, or fallback policy gains ownership.
// - Merge-When:
//   - One product coordinator owns both retry admission and execution.
// - Summary:
//   - Binds one exact replanned native suffix to its affine checkpoint owner.
// - Description:
//   - Rejects reason, programs, key, or entry drift before buffer movement.
// - Usage:
//   - Admit a scheduler `NativeRetry` suspension before native execution.
// - Defaults:
//   - Every rejection returns both supplied owners unchanged.
//

//! Exact admission for caller-replanned native continuation suffixes.

#[path = "native_retry/rebase.rs"]
mod rebase;

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    ProfileDescriptor, ProfileMachineError, ProfileMachineIoState,
    ProfileMachineObservation, ProfileMachineState,
};
pub use rebase::{
    NativeContinuationRetryCompletion, NativeContinuationRetryDisposition,
    NativeContinuationRetryFailureDisposition,
    NativeContinuationRetryFailureParts,
    NativeContinuationRetryFailureRebaseFailure,
    NativeContinuationRetryFailureRebaseResult,
    NativeContinuationRetryRebaseError, NativeContinuationRetryRebaseFailure,
    NativeContinuationRetryResumption,
};

use crate::continuation_scheduler::{
    NativeContinuationScheduleStopReason, NativeContinuationScheduleSuspension,
};
use crate::execution_native::{
    NativeExecutableMemoryAdapter, NativeExecutableRunner,
    NativeExecutableSequenceKey, NativeInterpreterContinuationReason,
    NativeRegionBuffers, NativeSequenceExecutionFailure,
    NativeSequenceExecutionOutcome, VerifiedDirectSequencePlan,
    execute_verified_native_sequence,
};
/// Why one replanned native retry was rejected before buffer movement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryAdmissionError {
    /// Replanned entry observation differs from the owned checkpoint.
    EntryObservation,
    /// Replanned ordered artifact identity differs from the remaining suffix.
    PlanKey,
    /// Replanned one-step programs differ from the remaining semantic suffix.
    PlanPrograms,
    /// The suspension was not explicitly yielded for native retry.
    ScheduleReason {
        /// Exact scheduler reason supplied by the caller.
        observed: NativeContinuationScheduleStopReason,
    },
}

/// Exact owned state transferred out of one native retry attempt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryTransfer {
    input: Vec<u8>,
    memory: Vec<u32>,
    observation: ProfileMachineObservation,
    output: Vec<u8>,
    profile: &'static ProfileDescriptor,
}

/// Failure while converting retry transfer buffers to a normative checkpoint.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryTransferError {
    /// Native observation names more committed output than the owned capacity.
    OutputLength {
        /// Exact committed output length declared by the observation.
        expected: usize,
        /// Owned output capacity returned by native execution.
        observed: usize,
    },
    /// Normative checkpoint validation rejected the transferred state.
    State(ProfileMachineError),
}

/// Successful native execution attempt retaining exact entry ownership.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryExecution {
    outcome: NativeSequenceExecutionOutcome,
    plan: VerifiedDirectSequencePlan,
    suspension: NativeContinuationScheduleSuspension,
    transfer: NativeContinuationRetryTransfer,
}

/// Failed native execution attempt retaining exact state and cleanup evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryExecutionFailure<MemoryError, RunnerError> {
    failure: Box<NativeSequenceExecutionFailure<MemoryError, RunnerError>>,
    plan: VerifiedDirectSequencePlan,
    suspension: NativeContinuationScheduleSuspension,
    transfer: NativeContinuationRetryTransfer,
}

/// Result of executing one admitted native continuation retry.
pub type NativeContinuationRetryExecutionResult<MemoryError, RunnerError> =
    Result<
        NativeContinuationRetryExecution,
        Box<NativeContinuationRetryExecutionFailure<MemoryError, RunnerError>>,
    >;

/// Exact owners restored from one failed retry execution.
pub type NativeContinuationRetryExecutionFailureParts<
    MemoryError,
    RunnerError,
> = (
    NativeContinuationScheduleSuspension,
    VerifiedDirectSequencePlan,
    Box<NativeSequenceExecutionFailure<MemoryError, RunnerError>>,
    NativeContinuationRetryTransfer,
);

type NativeContinuationRetryAdapterResult<MemoryAdapter, Runner> =
    NativeContinuationRetryExecutionResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as NativeExecutableRunner>::Error,
    >;

#[derive(Clone, Copy)]
pub(crate) struct NativeContinuationRetryRebaseEvidence<'evidence> {
    pub(crate) observation: ProfileMachineObservation,
    pub(crate) reason: NativeInterpreterContinuationReason,
    pub(crate) retry_steps: usize,
    pub(crate) suspension: &'evidence NativeContinuationScheduleSuspension,
    pub(crate) transfer: &'evidence NativeContinuationRetryTransfer,
}

pub(crate) struct NativeContinuationRetryTransferParts {
    pub(crate) input: Vec<u8>,
    pub(crate) memory: Vec<u32>,
    pub(crate) observation: ProfileMachineObservation,
    pub(crate) output: Vec<u8>,
    pub(crate) profile: &'static ProfileDescriptor,
}

struct NativeContinuationRetryOwnedBuffers {
    input: Vec<u8>,
    memory: Vec<u32>,
    output: Vec<u8>,
    profile: &'static ProfileDescriptor,
}

impl NativeContinuationRetryOwnedBuffers {
    fn into_transfer(
        self,
        observation: ProfileMachineObservation,
    ) -> NativeContinuationRetryTransfer {
        NativeContinuationRetryTransfer {
            input: self.input,
            memory: self.memory,
            observation,
            output: self.output,
            profile: self.profile,
        }
    }
}

/// Rejected retry admission retaining every supplied affine owner.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryAdmissionFailure {
    error: NativeContinuationRetryAdmissionError,
    plan: VerifiedDirectSequencePlan,
    suspension: NativeContinuationScheduleSuspension,
}

/// Exact verified native retry plan bound to one affine checkpoint owner.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationNativeRetry {
    plan: VerifiedDirectSequencePlan,
    suspension: NativeContinuationScheduleSuspension,
}

impl Display for NativeContinuationRetryTransferError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::OutputLength { expected, observed } => write!(
                f,
                "native retry output has {observed} of {expected} bytes",
            ),
            Self::State(error) => {
                write!(f, "native retry checkpoint rejected: {error}")
            },
        }
    }
}

impl Display for NativeContinuationRetryAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::EntryObservation => {
                f.write_str("native retry plan entry differs from checkpoint")
            },
            Self::PlanKey => {
                f.write_str("native retry plan key differs from suffix")
            },
            Self::PlanPrograms => {
                f.write_str("native retry programs differ from suffix")
            },
            Self::ScheduleReason { observed } => write!(
                f,
                "native retry requires native-retry yield, got {}",
                stop_reason_id(*observed),
            ),
        }
    }
}

impl NativeContinuationRetryTransfer {
    pub(crate) fn from_parts(
        parts: NativeContinuationRetryTransferParts,
    ) -> Self {
        Self {
            input: parts.input,
            memory: parts.memory,
            observation: parts.observation,
            output: parts.output,
            profile: parts.profile,
        }
    }

    /// Returns the full immutable input stream retained by this retry.
    #[must_use]
    pub fn input(&self) -> &[u8] {
        &self.input
    }

    /// Converts this exact transfer into a normative profile checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`NativeContinuationRetryTransferError`] when committed output
    /// exceeds capacity or normative state validation rejects the transfer.
    pub fn into_checkpoint(
        self,
    ) -> Result<ProfileMachineState, NativeContinuationRetryTransferError> {
        let committed = self.output.get(..self.observation.output_len).ok_or(
            NativeContinuationRetryTransferError::OutputLength {
                expected: self.observation.output_len,
                observed: self.output.len(),
            },
        )?;
        let io = ProfileMachineIoState::new(
            self.input,
            self.observation.input_consumed,
            committed.to_vec(),
            self.observation.termination,
        )
        .map_err(NativeContinuationRetryTransferError::State)?;
        ProfileMachineState::new(
            self.profile,
            self.memory,
            self.observation.registers,
            io,
        )
        .map_err(NativeContinuationRetryTransferError::State)
    }

    /// Returns the exact mutated guest memory image.
    #[must_use]
    pub fn memory(&self) -> &[u32] {
        &self.memory
    }

    /// Returns the admitted observation after this retry attempt.
    #[must_use]
    pub const fn observation(&self) -> ProfileMachineObservation {
        self.observation
    }

    /// Returns the complete output capacity used by native execution.
    #[must_use]
    pub fn output(&self) -> &[u8] {
        &self.output
    }

    /// Returns the canonical profile retained from the entry checkpoint.
    #[must_use]
    pub const fn profile(&self) -> &'static ProfileDescriptor {
        self.profile
    }
}

impl NativeContinuationNativeRetry {
    /// Executes this admitted retry through the existing native sequence path.
    ///
    /// The entry checkpoint is copied into owned native buffers. Both success
    /// and failure return exact transferred state plus the original admitted
    /// plan and scheduler suspension. No scheduling or fallback decision
    /// occurs.
    ///
    /// # Errors
    ///
    /// Returns [`NativeContinuationRetryExecutionFailure`] with exact mutated
    /// or rolled-back state plus the underlying indexed native sequence
    /// failure.
    pub fn execute<MemoryAdapter, Runner>(
        self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
    ) -> NativeContinuationRetryAdapterResult<MemoryAdapter, Runner>
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: NativeExecutableRunner,
    {
        let Self { plan, suspension } = self;
        let entry = suspension.state();
        let profile = entry.profile();
        let input = entry.io().input().to_vec();
        let mut memory = entry.memory().to_vec();
        let output_capacity =
            plan.exit().output_len.max(entry.io().output().len());
        let mut output = vec![0u8; output_capacity];
        if let Some(prefix) = output.get_mut(..entry.io().output().len()) {
            prefix.copy_from_slice(entry.io().output());
        }
        let result = execute_verified_native_sequence(
            memory_adapter,
            runner,
            &plan,
            NativeRegionBuffers::new(&mut memory, &input, &mut output),
        );
        let buffers = NativeContinuationRetryOwnedBuffers {
            input,
            memory,
            output,
            profile,
        };
        match result {
            Ok(outcome) => Ok(NativeContinuationRetryExecution {
                outcome,
                plan,
                suspension,
                transfer: buffers.into_transfer(outcome.observation()),
            }),
            Err(failure) => {
                let observation = failure.observation();
                Err(Box::new(NativeContinuationRetryExecutionFailure {
                    failure,
                    plan,
                    suspension,
                    transfer: buffers.into_transfer(observation),
                }))
            },
        }
    }

    /// Consumes this admission and returns exact suspension plus verified plan.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        NativeContinuationScheduleSuspension,
        VerifiedDirectSequencePlan,
    ) {
        (self.suspension, self.plan)
    }

    /// Admits one verified plan against an exact native-retry suspension.
    ///
    /// # Errors
    ///
    /// Returns [`NativeContinuationRetryAdmissionFailure`] while retaining both
    /// supplied owners when reason, program suffix, key, or entry state drifts.
    pub fn new(
        suspension: NativeContinuationScheduleSuspension,
        plan: VerifiedDirectSequencePlan,
    ) -> Result<Self, Box<NativeContinuationRetryAdmissionFailure>> {
        let rejection = retry_admission_error(&suspension, &plan);
        match rejection {
            Some(error) => {
                Err(Box::new(NativeContinuationRetryAdmissionFailure {
                    error,
                    plan,
                    suspension,
                }))
            },
            None => Ok(Self { plan, suspension }),
        }
    }

    /// Returns the exact verified direct plan selected for this retry.
    #[must_use]
    pub const fn plan(&self) -> &VerifiedDirectSequencePlan {
        &self.plan
    }

    /// Returns the exact normative checkpoint owned by this retry.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        self.suspension.state()
    }

    /// Returns the scheduler suspension whose ownership this retry consumes.
    #[must_use]
    pub const fn suspension(&self) -> &NativeContinuationScheduleSuspension {
        &self.suspension
    }
}

impl NativeContinuationRetryAdmissionFailure {
    /// Returns the exact admission rejection.
    #[must_use]
    pub const fn error(&self) -> NativeContinuationRetryAdmissionError {
        self.error
    }

    /// Consumes this failure and restores every supplied affine owner.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        NativeContinuationScheduleSuspension,
        VerifiedDirectSequencePlan,
    ) {
        (self.suspension, self.plan)
    }

    /// Returns the rejected verified direct plan.
    #[must_use]
    pub const fn plan(&self) -> &VerifiedDirectSequencePlan {
        &self.plan
    }

    /// Returns the exact scheduler suspension retained after rejection.
    #[must_use]
    pub const fn suspension(&self) -> &NativeContinuationScheduleSuspension {
        &self.suspension
    }
}

pub(crate) fn retry_rebase_evidence(
    evidence: NativeContinuationRetryRebaseEvidence<'_>,
) -> Result<
    NativeContinuationRetryDisposition,
    NativeContinuationRetryRebaseError,
> {
    rebase::retry_rebase_evidence(evidence)
}

fn retry_admission_error(
    suspension: &NativeContinuationScheduleSuspension,
    plan: &VerifiedDirectSequencePlan,
) -> Option<NativeContinuationRetryAdmissionError> {
    if suspension.reason() != NativeContinuationScheduleStopReason::NativeRetry
    {
        return Some(NativeContinuationRetryAdmissionError::ScheduleReason {
            observed: suspension.reason(),
        });
    }
    if plan.programs() != suspension.remaining_programs() {
        return Some(NativeContinuationRetryAdmissionError::PlanPrograms);
    }
    if NativeExecutableSequenceKey::from_plan(plan)
        != *suspension.remaining_key()
    {
        return Some(NativeContinuationRetryAdmissionError::PlanKey);
    }
    if plan.entry() != state_observation(suspension.state()) {
        return Some(NativeContinuationRetryAdmissionError::EntryObservation);
    }
    None
}

fn state_observation(state: &ProfileMachineState) -> ProfileMachineObservation {
    ProfileMachineObservation {
        input_consumed: state.io().input_consumed(),
        output_len: state.io().output().len(),
        registers: state.registers(),
        termination: state.io().termination(),
    }
}

const fn stop_reason_id(
    reason: NativeContinuationScheduleStopReason,
) -> &'static str {
    match reason {
        NativeContinuationScheduleStopReason::BudgetExhausted => {
            "budget-exhausted"
        },
        NativeContinuationScheduleStopReason::CallerYield => "caller-yield",
        NativeContinuationScheduleStopReason::NativeRetry => "native-retry",
    }
}
