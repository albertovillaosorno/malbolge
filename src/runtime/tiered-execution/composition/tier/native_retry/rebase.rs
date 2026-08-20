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
//   - Semantic rebase of successful and failed native retry evidence.
// - Must-Not:
//   - Execute either tier, infer plans, or discard native failure ownership.
// - Allows:
//   - Inputs: exact retry execution evidence and complete continuation
//     authority.
//   - Outputs: verified completion, normative resumption, or retained
//     rejection.
//   - Side effects: normative checkpoint reconstruction only.
// - Split-When:
//   - Completion and resumption policies gain independent ownership.
// - Merge-When:
//   - Retry execution and semantic publication become one atomic boundary.
// - Summary:
//   - Rebases per-attempt native evidence onto complete mixed-tier authority.
// - Description:
//   - Keeps semantic disposition independent from indexed native failure
//     owners.
// - Usage:
//   - Consume successful or failed retry execution through `rebase()`.
// - Defaults:
//   - Every rejection retains the complete supplied execution owner.
//

//! Semantic rebase for exact native continuation retry evidence.

use malbolge::RunOutcome;

use super::*;
use crate::execution_native::NativeInterpreterContinuationError;
use crate::interpreter_handoff::{
    NativeInterpreterHandoff, NativeInterpreterHandoffAdmissionError,
};

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

pub(super) fn retry_rebase_evidence(
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
