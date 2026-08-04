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

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    ProfileDescriptor, ProfileMachineError, ProfileMachineIoState,
    ProfileMachineObservation, ProfileMachineState, RunOutcome,
};

use crate::continuation_scheduler::{
    NativeContinuationScheduleStopReason, NativeContinuationScheduleSuspension,
};
use crate::execution_native::{
    NativeExecutableMemoryAdapter, NativeExecutableRunner,
    NativeExecutableSequenceKey, NativeInterpreterContinuationError,
    NativeInterpreterContinuationReason, NativeRegionBuffers,
    NativeSequenceExecutionFailure, NativeSequenceExecutionOutcome,
    VerifiedDirectSequencePlan, execute_verified_native_sequence,
};
use crate::interpreter_handoff::{
    NativeInterpreterHandoff, NativeInterpreterHandoffAdmissionError,
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

/// Semantic result after rebasing one successful native retry.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryDisposition {
    /// The complete original plan reached its verified final checkpoint.
    Completed(Box<NativeContinuationRetryCompletion>),
    /// Exact remaining work returned as a normative interpreter handoff.
    Resumable(Box<NativeContinuationRetryResumption>),
}

/// Complete mixed-tier result after one successful native retry.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryCompletion {
    interpreter_steps: usize,
    outcome: RunOutcome,
    retry_steps: usize,
    state: ProfileMachineState,
}

/// Exact scheduler-ready handoff after a retry guard miss.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryResumption {
    handoff: NativeInterpreterHandoff,
    interpreter_steps: usize,
    resume_index: usize,
    retry_steps: usize,
}

/// Why successful retry evidence could not be semantically rebased.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationRetryRebaseError {
    /// Mixed-tier progress disagreed with complete continuation authority.
    Continuation(NativeInterpreterContinuationError),
    /// The rebased continuation/checkpoint pair failed handoff admission.
    Handoff(NativeInterpreterHandoffAdmissionError),
    /// Interpreter and retry progress overflowed host indexing.
    ProgressOverflow,
    /// Exact transferred buffers could not become a normative checkpoint.
    Transfer(NativeContinuationRetryTransferError),
}

/// Rebase rejection retaining the complete successful execution owner.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryRebaseFailure {
    error: NativeContinuationRetryRebaseError,
    execution: NativeContinuationRetryExecution,
}

/// Failed native execution attempt retaining exact state and cleanup evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryExecutionFailure<MemoryError, RunnerError> {
    failure: Box<NativeSequenceExecutionFailure<MemoryError, RunnerError>>,
    plan: VerifiedDirectSequencePlan,
    suspension: NativeContinuationScheduleSuspension,
    transfer: NativeContinuationRetryTransfer,
}

/// Failed native retry plus its independently owned semantic disposition.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryFailureDisposition<MemoryError, RunnerError> {
    disposition: NativeContinuationRetryDisposition,
    failure: Box<NativeSequenceExecutionFailure<MemoryError, RunnerError>>,
}

/// Rebase rejection retaining the complete failed execution owner.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeContinuationRetryFailureRebaseFailure<MemoryError, RunnerError>
{
    error: NativeContinuationRetryRebaseError,
    execution:
        Box<NativeContinuationRetryExecutionFailure<MemoryError, RunnerError>>,
}

/// Independent semantic and native-failure owners after a failed retry rebase.
pub type NativeContinuationRetryFailureParts<MemoryError, RunnerError> = (
    NativeContinuationRetryDisposition,
    Box<NativeSequenceExecutionFailure<MemoryError, RunnerError>>,
);

/// Result of semantically rebasing one failed native retry.
pub type NativeContinuationRetryFailureRebaseResult<MemoryError, RunnerError> =
    Result<
        NativeContinuationRetryFailureDisposition<MemoryError, RunnerError>,
        Box<
            NativeContinuationRetryFailureRebaseFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    >;

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
struct NativeContinuationRetryRebaseEvidence<'evidence> {
    observation: ProfileMachineObservation,
    reason: NativeInterpreterContinuationReason,
    retry_steps: usize,
    suspension: &'evidence NativeContinuationScheduleSuspension,
    transfer: &'evidence NativeContinuationRetryTransfer,
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

impl Display for NativeContinuationRetryRebaseError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Continuation(error) => {
                write!(f, "native retry continuation rebase failed: {error}")
            },
            Self::Handoff(error) => {
                write!(f, "native retry handoff rebase failed: {error}")
            },
            Self::ProgressOverflow => {
                f.write_str("native retry mixed-tier progress overflowed")
            },
            Self::Transfer(error) => {
                write!(f, "native retry transfer rebase failed: {error}")
            },
        }
    }
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

impl NativeContinuationRetryCompletion {
    /// Returns interpreter steps committed before this retry attempt.
    #[must_use]
    pub const fn interpreter_steps(&self) -> usize {
        self.interpreter_steps
    }

    /// Returns the complete original plan outcome.
    #[must_use]
    pub const fn outcome(&self) -> RunOutcome {
        self.outcome
    }

    /// Returns native retry steps committed by this attempt.
    #[must_use]
    pub const fn retry_steps(&self) -> usize {
        self.retry_steps
    }

    /// Returns the exact verified final normative checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl NativeContinuationRetryResumption {
    /// Returns interpreter steps committed before this retry attempt.
    #[must_use]
    pub const fn interpreter_steps(&self) -> usize {
        self.interpreter_steps
    }

    /// Consumes this exact resumption and returns its normative handoff.
    #[must_use]
    pub fn into_handoff(self) -> NativeInterpreterHandoff {
        self.handoff
    }

    /// Returns the complete-plan index at which the handoff resumes.
    #[must_use]
    pub const fn resume_index(&self) -> usize {
        self.resume_index
    }

    /// Returns native retry steps committed by this attempt.
    #[must_use]
    pub const fn retry_steps(&self) -> usize {
        self.retry_steps
    }
}

impl NativeContinuationRetryRebaseFailure {
    /// Returns the exact semantic rebase rejection.
    #[must_use]
    pub const fn error(&self) -> NativeContinuationRetryRebaseError {
        self.error
    }

    /// Consumes this rejection and restores the successful execution owner.
    #[must_use]
    pub fn into_execution(self) -> NativeContinuationRetryExecution {
        self.execution
    }
}

impl<MemoryError, RunnerError>
    NativeContinuationRetryFailureDisposition<MemoryError, RunnerError>
{
    /// Returns the independently owned semantic mixed-tier result.
    #[must_use]
    pub const fn disposition(&self) -> &NativeContinuationRetryDisposition {
        &self.disposition
    }

    /// Returns the underlying indexed native failure and cleanup ownership.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &NativeSequenceExecutionFailure<MemoryError, RunnerError> {
        &self.failure
    }

    /// Consumes this result into semantic and native-failure owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> NativeContinuationRetryFailureParts<MemoryError, RunnerError> {
        (self.disposition, self.failure)
    }
}

impl<MemoryError, RunnerError>
    NativeContinuationRetryFailureRebaseFailure<MemoryError, RunnerError>
{
    /// Returns the exact semantic rebase rejection.
    #[must_use]
    pub const fn error(&self) -> NativeContinuationRetryRebaseError {
        self.error
    }

    /// Consumes this rejection and restores the complete failed execution.
    #[must_use]
    pub fn into_execution(
        self,
    ) -> Box<NativeContinuationRetryExecutionFailure<MemoryError, RunnerError>>
    {
        self.execution
    }
}

impl NativeContinuationRetryExecution {
    /// Consumes this success and returns entry owner, plan, outcome, and state.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        NativeContinuationScheduleSuspension,
        VerifiedDirectSequencePlan,
        NativeSequenceExecutionOutcome,
        NativeContinuationRetryTransfer,
    ) {
        (self.suspension, self.plan, self.outcome, self.transfer)
    }

    /// Returns the exact admitted retry outcome.
    #[must_use]
    pub const fn outcome(&self) -> NativeSequenceExecutionOutcome {
        self.outcome
    }

    /// Returns the exact verified plan executed by this retry.
    #[must_use]
    pub const fn plan(&self) -> &VerifiedDirectSequencePlan {
        &self.plan
    }

    /// Rebases successful retry evidence onto complete semantic authority.
    ///
    /// Applied completion yields the original plan outcome and final
    /// checkpoint. Guard miss yields a new normative handoff whose
    /// continuation index includes both prior interpreter progress and
    /// newly committed retry steps.
    ///
    /// # Errors
    ///
    /// Returns [`NativeContinuationRetryRebaseFailure`] while retaining this
    /// complete execution owner when transfer, continuation, or handoff
    /// admission fails closed.
    pub fn rebase(
        self,
    ) -> Result<
        NativeContinuationRetryDisposition,
        Box<NativeContinuationRetryRebaseFailure>,
    > {
        match retry_rebase_disposition(&self) {
            Ok(disposition) => Ok(disposition),
            Err(error) => Err(Box::new(NativeContinuationRetryRebaseFailure {
                error,
                execution: self,
            })),
        }
    }

    /// Returns the entry suspension consumed by this retry attempt.
    #[must_use]
    pub const fn suspension(&self) -> &NativeContinuationScheduleSuspension {
        &self.suspension
    }

    /// Returns exact state transferred out of native execution.
    #[must_use]
    pub const fn transfer(&self) -> &NativeContinuationRetryTransfer {
        &self.transfer
    }
}

impl<MemoryError, RunnerError>
    NativeContinuationRetryExecutionFailure<MemoryError, RunnerError>
{
    /// Returns the indexed native sequence failure and cleanup evidence.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &NativeSequenceExecutionFailure<MemoryError, RunnerError> {
        &self.failure
    }

    /// Consumes this failure and restores every exact retained owner.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> NativeContinuationRetryExecutionFailureParts<MemoryError, RunnerError>
    {
        (self.suspension, self.plan, self.failure, self.transfer)
    }

    /// Returns the exact verified plan attempted by this retry.
    #[must_use]
    pub const fn plan(&self) -> &VerifiedDirectSequencePlan {
        &self.plan
    }

    /// Rebases failed retry progress while retaining native failure ownership.
    ///
    /// The semantic disposition and indexed native failure become independent
    /// owners. This permits normative fallback or completion before retrying
    /// executable cleanup.
    ///
    /// # Errors
    ///
    /// Returns [`NativeContinuationRetryFailureRebaseFailure`] while retaining
    /// this complete failed execution when transfer, continuation, or handoff
    /// admission fails closed.
    pub fn rebase(
        self: Box<Self>,
    ) -> NativeContinuationRetryFailureRebaseResult<MemoryError, RunnerError>
    {
        match retry_failure_rebase_disposition(&self) {
            Ok(disposition) => {
                let Self { failure, .. } = *self;
                Ok(NativeContinuationRetryFailureDisposition {
                    disposition,
                    failure,
                })
            },
            Err(error) => {
                Err(Box::new(NativeContinuationRetryFailureRebaseFailure {
                    error,
                    execution: self,
                }))
            },
        }
    }

    /// Returns the entry suspension consumed by this failed attempt.
    #[must_use]
    pub const fn suspension(&self) -> &NativeContinuationScheduleSuspension {
        &self.suspension
    }

    /// Returns exact rollback or committed state after the failed attempt.
    #[must_use]
    pub const fn transfer(&self) -> &NativeContinuationRetryTransfer {
        &self.transfer
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

fn retry_failure_rebase_disposition<MemoryError, RunnerError>(
    execution: &NativeContinuationRetryExecutionFailure<
        MemoryError,
        RunnerError,
    >,
) -> Result<
    NativeContinuationRetryDisposition,
    NativeContinuationRetryRebaseError,
> {
    retry_rebase_evidence(NativeContinuationRetryRebaseEvidence {
        observation: execution.failure.observation(),
        reason: NativeInterpreterContinuationReason::ExecutionFailure,
        retry_steps: execution.failure.completed_steps(),
        suspension: &execution.suspension,
        transfer: &execution.transfer,
    })
}

fn retry_rebase_disposition(
    execution: &NativeContinuationRetryExecution,
) -> Result<
    NativeContinuationRetryDisposition,
    NativeContinuationRetryRebaseError,
> {
    let reason = match execution.outcome {
        NativeSequenceExecutionOutcome::GuardMiss { .. } => {
            NativeInterpreterContinuationReason::GuardMiss
        },
        NativeSequenceExecutionOutcome::Applied { .. } => {
            execution.suspension.continuation().reason()
        },
    };
    retry_rebase_evidence(NativeContinuationRetryRebaseEvidence {
        observation: execution.outcome.observation(),
        reason,
        retry_steps: execution.outcome.completed_steps(),
        suspension: &execution.suspension,
        transfer: &execution.transfer,
    })
}

fn retry_rebase_evidence(
    evidence: NativeContinuationRetryRebaseEvidence<'_>,
) -> Result<
    NativeContinuationRetryDisposition,
    NativeContinuationRetryRebaseError,
> {
    let checkpoint = evidence
        .transfer
        .clone()
        .into_checkpoint()
        .map_err(NativeContinuationRetryRebaseError::Transfer)?;
    let interpreter_steps = evidence.suspension.interpreter_steps();
    let additional_steps = interpreter_steps
        .checked_add(evidence.retry_steps)
        .ok_or(NativeContinuationRetryRebaseError::ProgressOverflow)?;
    let advanced = evidence
        .suspension
        .continuation()
        .advance(additional_steps, evidence.observation, evidence.reason)
        .map_err(NativeContinuationRetryRebaseError::Continuation)?;
    let Some(continuation) = advanced else {
        return Ok(NativeContinuationRetryDisposition::Completed(Box::new(
            NativeContinuationRetryCompletion {
                interpreter_steps,
                outcome: evidence.suspension.continuation().expected_outcome(),
                retry_steps: evidence.retry_steps,
                state: checkpoint,
            },
        )));
    };
    let resume_index = continuation.resume_index();
    let handoff =
        NativeInterpreterHandoff::from_checkpoint(continuation, checkpoint)
            .map_err(NativeContinuationRetryRebaseError::Handoff)?;
    Ok(NativeContinuationRetryDisposition::Resumable(Box::new(
        NativeContinuationRetryResumption {
            handoff,
            interpreter_steps,
            resume_index,
            retry_steps: evidence.retry_steps,
        },
    )))
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
