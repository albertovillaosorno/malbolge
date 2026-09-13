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
//   - Semantic rebase of exact fused native retry execution evidence.
// - Must-Not:
//   - Execute tiers, infer retry plans, mutate caches, or discard failures.
// - Allows:
//   - Inputs: fused retry execution plus complete continuation authority.
//   - Outputs: verified completion or scheduler-ready normative resumption.
//   - Side effects: normative checkpoint reconstruction only.
// - Split-When:
//   - Retry routing, cached retry, or completion policy gains ownership.
// - Merge-When:
//   - Fused retry execution and semantic publication become one boundary.
// - Summary:
//   - Rebases fused retry evidence onto original continuation authority.
// - Description:
//   - Native failure ownership remains independent from semantic disposition.
// - Usage:
//   - Rebase successful or failed fused retry execution before scheduling.
// - Defaults:
//   - Every rebase rejection restores the complete supplied execution owner.
//

//! Semantic rebase for fused native retry execution evidence.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{ProfileMachineState, RunOutcome};

use super::fused_sequence_continuation::{
    DirectFusedContinuationAdvance, DirectFusedNativeContinuationError,
    DirectFusedNativeContinuationReason,
};
use super::fused_sequence_execution::DirectFusedNativeSequenceExecutionOutcome;
use super::fused_sequence_handoff::{
    DirectFusedNativeHandoffAdmissionError, DirectFusedNativeInterpreterHandoff,
};
use super::fused_sequence_plan::DirectFusedNativeSequencePlan;
use super::fused_sequence_retry_execution::{
    DirectFusedNativeRetryExecution, DirectFusedNativeRetryExecutionFailure,
    DirectFusedNativeRetryTransfer, DirectFusedNativeRetryTransferError,
};
use super::fused_sequence_scheduler::DirectFusedNativeScheduleSuspension;
use super::fused_sequence_transaction as transaction;

type RetryTransactionFailure<MemoryError, RunnerError> =
    transaction::DirectFusedNativeSequenceTransactionFailure<
        MemoryError,
        RunnerError,
    >;

/// Semantic result after rebasing one fused native retry.
#[derive(Debug, Eq, PartialEq)]
pub enum DirectFusedNativeRetryDisposition {
    /// The original complete semantic plan reached its verified final state.
    Completed(Box<DirectFusedNativeRetryCompletion>),
    /// Remaining work returned as a normative interpreter handoff.
    Resumable(Box<DirectFusedNativeRetryResumption>),
}

/// Complete mixed-tier result after one fused native retry.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryCompletion {
    interpreter_steps: usize,
    outcome: RunOutcome,
    retry_steps: usize,
    state: ProfileMachineState,
}

/// Exact scheduler-ready handoff after incomplete fused retry work.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryResumption {
    handoff: DirectFusedNativeInterpreterHandoff,
    interpreter_steps: usize,
    resume_region: usize,
    resume_step: usize,
    retry_steps: usize,
}

/// Why fused retry evidence could not be semantically rebased.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeRetryRebaseError {
    /// Complete continuation authority rejected fused-region progress.
    Continuation(DirectFusedNativeContinuationError),
    /// Rebased continuation/checkpoint failed normative handoff admission.
    Handoff(DirectFusedNativeHandoffAdmissionError),
    /// Exact transferred buffers could not become a normative checkpoint.
    Transfer(DirectFusedNativeRetryTransferError),
}

/// Rebase rejection retaining one successful fused retry execution owner.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryRebaseFailure {
    error: DirectFusedNativeRetryRebaseError,
    execution: DirectFusedNativeRetryExecution,
}

/// Failed fused retry plus independently owned semantic disposition.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryFailureDisposition<MemoryError, RunnerError> {
    disposition: DirectFusedNativeRetryDisposition,
    failure: Box<RetryTransactionFailure<MemoryError, RunnerError>>,
}

/// Rebase rejection retaining one complete failed fused retry execution.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryFailureRebaseFailure<MemoryError, RunnerError>
{
    error: DirectFusedNativeRetryRebaseError,
    execution:
        Box<DirectFusedNativeRetryExecutionFailure<MemoryError, RunnerError>>,
}

/// Independent semantic and native-failure owners after failed retry rebase.
pub type DirectFusedNativeRetryRebasedFailureParts<MemoryError, RunnerError> = (
    DirectFusedNativeRetryDisposition,
    Box<RetryTransactionFailure<MemoryError, RunnerError>>,
);

/// Result of semantically rebasing one failed fused native retry.
pub type DirectFusedNativeRetryFailureRebaseResult<MemoryError, RunnerError> =
    Result<
        DirectFusedNativeRetryFailureDisposition<MemoryError, RunnerError>,
        Box<
            DirectFusedNativeRetryFailureRebaseFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    >;

type DirectFusedNativeSemanticRebaseResult = Result<
    DirectFusedNativeRetryDisposition,
    DirectFusedNativeRetryRebaseError,
>;

#[derive(Clone, Copy)]
struct DirectFusedNativeRetryRebaseEvidence<'evidence> {
    observation: malbolge::ProfileMachineObservation,
    plan: &'evidence DirectFusedNativeSequencePlan,
    reason: DirectFusedNativeContinuationReason,
    retry_regions: usize,
    retry_steps: usize,
    suspension: &'evidence DirectFusedNativeScheduleSuspension,
    transfer: &'evidence DirectFusedNativeRetryTransfer,
}

impl Display for DirectFusedNativeRetryRebaseError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Continuation(error) => {
                write!(f, "fused retry continuation rebase failed: {error}")
            },
            Self::Handoff(error) => {
                write!(f, "fused retry handoff rebase failed: {error}")
            },
            Self::Transfer(error) => {
                write!(f, "fused retry transfer rebase failed: {error}")
            },
        }
    }
}

impl DirectFusedNativeRetryCompletion {
    /// Returns interpreter steps committed before this retry attempt.
    #[must_use]
    pub const fn interpreter_steps(&self) -> usize {
        self.interpreter_steps
    }

    /// Returns the complete original semantic outcome.
    #[must_use]
    pub const fn outcome(&self) -> RunOutcome {
        self.outcome
    }

    /// Returns native source steps committed by this retry attempt.
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

impl DirectFusedNativeRetryResumption {
    /// Returns interpreter steps committed before this retry attempt.
    #[must_use]
    pub const fn interpreter_steps(&self) -> usize {
        self.interpreter_steps
    }

    /// Consumes this exact resumption and returns its normative handoff.
    #[must_use]
    pub fn into_handoff(self) -> DirectFusedNativeInterpreterHandoff {
        self.handoff
    }

    /// Returns the complete-plan fused-region resume index.
    #[must_use]
    pub const fn resume_region(&self) -> usize {
        self.resume_region
    }

    /// Returns the complete-plan source semantic-step resume index.
    #[must_use]
    pub const fn resume_step(&self) -> usize {
        self.resume_step
    }

    /// Returns native source steps committed by this retry attempt.
    #[must_use]
    pub const fn retry_steps(&self) -> usize {
        self.retry_steps
    }
}

impl DirectFusedNativeRetryRebaseFailure {
    /// Returns the exact semantic rebase rejection.
    #[must_use]
    pub const fn error(&self) -> DirectFusedNativeRetryRebaseError {
        self.error
    }

    /// Consumes this rejection and restores the successful execution owner.
    #[must_use]
    pub fn into_execution(self) -> DirectFusedNativeRetryExecution {
        self.execution
    }
}

impl<MemoryError, RunnerError>
    DirectFusedNativeRetryFailureDisposition<MemoryError, RunnerError>
{
    /// Returns the independently owned semantic mixed-tier result.
    #[must_use]
    pub const fn disposition(&self) -> &DirectFusedNativeRetryDisposition {
        &self.disposition
    }

    /// Returns the retained fused transaction/release failure owner.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &RetryTransactionFailure<MemoryError, RunnerError> {
        &self.failure
    }

    /// Consumes this result into semantic and native-failure owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> DirectFusedNativeRetryRebasedFailureParts<MemoryError, RunnerError>
    {
        (self.disposition, self.failure)
    }
}

impl<MemoryError, RunnerError>
    DirectFusedNativeRetryFailureRebaseFailure<MemoryError, RunnerError>
{
    /// Returns the exact semantic rebase rejection.
    #[must_use]
    pub const fn error(&self) -> DirectFusedNativeRetryRebaseError {
        self.error
    }

    /// Consumes this rejection and restores the failed execution owner.
    #[must_use]
    pub fn into_execution(
        self,
    ) -> Box<DirectFusedNativeRetryExecutionFailure<MemoryError, RunnerError>>
    {
        self.execution
    }
}

/// Semantically rebases one successful fused native retry execution.
///
/// # Errors
///
/// Returns ownership-preserving rejection when continuation advance, transfer
/// reconstruction, or normative handoff admission fails closed.
pub fn rebase_direct_fused_native_retry(
    execution: DirectFusedNativeRetryExecution,
) -> Result<
    DirectFusedNativeRetryDisposition,
    Box<DirectFusedNativeRetryRebaseFailure>,
> {
    let outcome = execution.outcome();
    let reason = match outcome {
        DirectFusedNativeSequenceExecutionOutcome::GuardMiss { .. } => {
            DirectFusedNativeContinuationReason::GuardMiss
        },
        DirectFusedNativeSequenceExecutionOutcome::Applied { .. } => {
            execution.suspension().continuation().reason()
        },
    };
    let evidence = DirectFusedNativeRetryRebaseEvidence {
        observation: outcome.observation(),
        plan: execution.plan(),
        reason,
        retry_regions: outcome.completed_regions(),
        retry_steps: outcome.completed_steps(),
        suspension: execution.suspension(),
        transfer: execution.transfer(),
    };
    match retry_rebase_evidence(evidence) {
        Ok(disposition) => Ok(disposition),
        Err(error) => Err(Box::new(DirectFusedNativeRetryRebaseFailure {
            error,
            execution,
        })),
    }
}

/// Semantically rebases one failed fused native retry execution.
///
/// Native transaction/release ownership becomes independent from the semantic
/// completion or normative resumption so cleanup can be retried separately.
///
/// # Errors
///
/// Returns ownership-preserving rejection when semantic rebase fails closed.
pub fn rebase_direct_fused_native_retry_failure<MemoryError, RunnerError>(
    execution: Box<
        DirectFusedNativeRetryExecutionFailure<MemoryError, RunnerError>,
    >,
) -> DirectFusedNativeRetryFailureRebaseResult<MemoryError, RunnerError> {
    match retry_failure_rebase_disposition(&execution) {
        Ok(disposition) => {
            let (_, _, failure, _) = (*execution).into_parts();
            Ok(DirectFusedNativeRetryFailureDisposition {
                disposition,
                failure,
            })
        },
        Err(error) => {
            Err(Box::new(DirectFusedNativeRetryFailureRebaseFailure {
                error,
                execution,
            }))
        },
    }
}

fn retry_failure_rebase_disposition<MemoryError, RunnerError>(
    execution: &DirectFusedNativeRetryExecutionFailure<
        MemoryError,
        RunnerError,
    >,
) -> DirectFusedNativeSemanticRebaseResult {
    let (observation, reason, retry_regions, retry_steps) =
        failed_retry_semantic_evidence(execution);
    retry_rebase_evidence(DirectFusedNativeRetryRebaseEvidence {
        observation,
        plan: execution.plan(),
        reason,
        retry_regions,
        retry_steps,
        suspension: execution.suspension(),
        transfer: execution.transfer(),
    })
}

fn failed_retry_semantic_evidence<MemoryError, RunnerError>(
    execution: &DirectFusedNativeRetryExecutionFailure<
        MemoryError,
        RunnerError,
    >,
) -> (
    malbolge::ProfileMachineObservation,
    DirectFusedNativeContinuationReason,
    usize,
    usize,
) {
    execution.failure().committed_outcome().map_or_else(
        || {
            execution.failure().execution_failure().map_or_else(
                || {
                    (
                        execution.plan().entry(),
                        DirectFusedNativeContinuationReason::ExecutionFailure,
                        0,
                        0,
                    )
                },
                |failure| {
                    (
                        failure.observation(),
                        DirectFusedNativeContinuationReason::ExecutionFailure,
                        failure.completed_regions(),
                        failure.completed_steps(),
                    )
                },
            )
        },
        |outcome| {
            let reason = match outcome {
                DirectFusedNativeSequenceExecutionOutcome::GuardMiss {
                    ..
                } => DirectFusedNativeContinuationReason::GuardMiss,
                DirectFusedNativeSequenceExecutionOutcome::Applied {
                    ..
                } => execution.suspension().continuation().reason(),
            };
            (
                outcome.observation(),
                reason,
                outcome.completed_regions(),
                outcome.completed_steps(),
            )
        },
    )
}

fn retry_rebase_evidence(
    evidence: DirectFusedNativeRetryRebaseEvidence<'_>,
) -> DirectFusedNativeSemanticRebaseResult {
    let checkpoint = evidence
        .transfer
        .clone()
        .into_checkpoint()
        .map_err(DirectFusedNativeRetryRebaseError::Transfer)?;
    let advanced = evidence
        .suspension
        .continuation()
        .advance_regions(evidence.plan, DirectFusedContinuationAdvance {
            completed_regions: evidence.retry_regions,
            completed_steps: evidence.retry_steps,
            observation: evidence.observation,
            reason: evidence.reason,
        })
        .map_err(DirectFusedNativeRetryRebaseError::Continuation)?;
    let interpreter_steps = evidence.suspension.interpreter_steps();
    let Some(continuation) = advanced else {
        return Ok(DirectFusedNativeRetryDisposition::Completed(Box::new(
            DirectFusedNativeRetryCompletion {
                interpreter_steps,
                outcome: evidence.suspension.continuation().expected_outcome(),
                retry_steps: evidence.retry_steps,
                state: checkpoint,
            },
        )));
    };
    let resume_region = continuation.resume_region();
    let resume_step = continuation.resume_step();
    let handoff = DirectFusedNativeInterpreterHandoff::from_checkpoint(
        continuation,
        checkpoint,
    )
    .map_err(DirectFusedNativeRetryRebaseError::Handoff)?;
    Ok(DirectFusedNativeRetryDisposition::Resumable(Box::new(
        DirectFusedNativeRetryResumption {
            handoff,
            interpreter_steps,
            resume_region,
            resume_step,
            retry_steps: evidence.retry_steps,
        },
    )))
}
