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
//   - Exact binding and resident execution of one admitted fused native retry.
// - Must-Not:
//   - Acquire cache entries, mutate cache policy, release mappings, or rebase.
// - Allows:
//   - Inputs: admitted retry, exact fused-sequence cache acquisition, and
//     runner.
//   - Outputs: resident execution plus retained lease/disposition/state owners.
//   - Side effects: native runner calls through already-resident leases only.
// - Split-When:
//   - Cache acquisition or semantic rebase gains independent ownership.
// - Merge-When:
//   - One coordinator owns fused retry acquisition through semantic completion.
// - Summary:
//   - Executes one exact fused retry through already-resident immutable leases.
// - Description:
//   - Plan drift fails before buffer movement and restores both supplied
//     owners.
// - Usage:
//   - Bind after cache acquisition, execute once, then explicitly return
//     leases.
// - Defaults:
//   - No executable-memory adapter operation occurs after successful binding.
//

//! Lease-backed execution for exact fused native retry ownership.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::fused_lease_cache::DirectFusedNativeLeaseCacheDisposition;
use super::fused_sequence_cache::DirectFusedNativeSequenceCacheAcquisition;
use super::fused_sequence_continuation::DirectFusedNativeContinuationReason;
use super::fused_sequence_execution::{
    DirectFusedNativeSequenceExecutionFailure,
    DirectFusedNativeSequenceExecutionOutcome,
};
use super::fused_sequence_lease::DirectFusedNativeLeasedSequence;
use super::fused_sequence_retry::DirectFusedNativeRetry;
use super::fused_sequence_retry_execution::{
    DirectFusedNativeRetryTransfer, DirectFusedNativeRetryTransferParts,
};
use super::fused_sequence_retry_rebase::{
    DirectFusedNativeRetryDisposition, DirectFusedNativeRetryRebaseError,
    DirectFusedNativeRetryRebaseEvidence, retry_rebase_evidence,
};
use super::fused_sequence_scheduler::DirectFusedNativeScheduleSuspension;
use super::invocation::NativeRegionBuffers;
use super::runner::DirectFusedNativeRunner;

/// Why one cache acquisition was rejected before fused retry execution.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeLeasedRetryAdmissionError {
    /// Acquired leased-sequence plan differs from the admitted retry plan.
    PlanIdentity,
}

/// Binding rejection retaining retry and cache-acquisition ownership.
#[derive(Debug)]
pub struct DirectFusedNativeLeasedRetryAdmissionFailure {
    acquisition: DirectFusedNativeSequenceCacheAcquisition,
    error: DirectFusedNativeLeasedRetryAdmissionError,
    retry: DirectFusedNativeRetry,
}

/// Exact admitted fused retry bound to one leased resident sequence.
#[derive(Debug)]
pub struct DirectFusedNativeLeasedRetry {
    dispositions: Vec<DirectFusedNativeLeaseCacheDisposition>,
    sequence: DirectFusedNativeLeasedSequence,
    suspension: DirectFusedNativeScheduleSuspension,
}

/// Successful resident fused retry execution retaining all leases.
#[derive(Debug)]
pub struct DirectFusedNativeLeasedRetryExecution {
    dispositions: Vec<DirectFusedNativeLeaseCacheDisposition>,
    outcome: DirectFusedNativeSequenceExecutionOutcome,
    sequence: DirectFusedNativeLeasedSequence,
    suspension: DirectFusedNativeScheduleSuspension,
    transfer: DirectFusedNativeRetryTransfer,
}

/// Failed resident fused retry execution retaining all leases and state.
#[derive(Debug)]
pub struct DirectFusedNativeLeasedRetryExecutionFailure<RunnerError> {
    dispositions: Vec<DirectFusedNativeLeaseCacheDisposition>,
    failure: Box<DirectFusedNativeSequenceExecutionFailure<RunnerError>>,
    sequence: DirectFusedNativeLeasedSequence,
    suspension: DirectFusedNativeScheduleSuspension,
    transfer: DirectFusedNativeRetryTransfer,
}

/// Result of one resident fused native retry attempt.
pub type DirectFusedNativeLeasedRetryExecutionResult<RunnerError> = Result<
    DirectFusedNativeLeasedRetryExecution,
    Box<DirectFusedNativeLeasedRetryExecutionFailure<RunnerError>>,
>;

/// Successful semantic rebase retaining cache evidence and resident leases.
#[derive(Debug)]
pub struct DirectFusedNativeLeasedRetryDisposition {
    disposition: DirectFusedNativeRetryDisposition,
    dispositions: Vec<DirectFusedNativeLeaseCacheDisposition>,
    sequence: DirectFusedNativeLeasedSequence,
}

/// Failed resident execution plus independently rebased semantic disposition.
#[derive(Debug)]
pub struct DirectFusedNativeLeasedRetryFailureDisposition<RunnerError> {
    disposition: DirectFusedNativeRetryDisposition,
    dispositions: Vec<DirectFusedNativeLeaseCacheDisposition>,
    failure: Box<DirectFusedNativeSequenceExecutionFailure<RunnerError>>,
    sequence: DirectFusedNativeLeasedSequence,
}

/// Rebase rejection retaining the complete successful leased execution owner.
#[derive(Debug)]
pub struct DirectFusedNativeLeasedRetryRebaseFailure {
    error: DirectFusedNativeRetryRebaseError,
    execution: DirectFusedNativeLeasedRetryExecution,
}

/// Rebase rejection retaining the complete failed leased execution owner.
#[derive(Debug)]
pub struct DirectFusedNativeLeasedRetryFailureRebaseFailure<RunnerError> {
    error: DirectFusedNativeRetryRebaseError,
    execution: Box<DirectFusedNativeLeasedRetryExecutionFailure<RunnerError>>,
}

/// Result of rebasing one failed resident fused retry attempt.
pub type DirectFusedNativeLeasedRetryFailureRebaseResult<RunnerError> = Result<
    DirectFusedNativeLeasedRetryFailureDisposition<RunnerError>,
    Box<DirectFusedNativeLeasedRetryFailureRebaseFailure<RunnerError>>,
>;

/// Semantic, native failure, cache evidence, and resident lease owners.
pub type DirectFusedNativeLeasedRetryRebasedFailureParts<RunnerError> = (
    DirectFusedNativeRetryDisposition,
    Box<DirectFusedNativeSequenceExecutionFailure<RunnerError>>,
    Vec<DirectFusedNativeLeaseCacheDisposition>,
    DirectFusedNativeLeasedSequence,
);

/// Exact owners restored from one successful resident fused retry execution.
pub type DirectFusedNativeLeasedRetrySuccessParts = (
    DirectFusedNativeScheduleSuspension,
    Vec<DirectFusedNativeLeaseCacheDisposition>,
    DirectFusedNativeLeasedSequence,
    DirectFusedNativeSequenceExecutionOutcome,
    DirectFusedNativeRetryTransfer,
);

/// Exact owners restored from failed resident fused retry execution.
pub type DirectFusedNativeLeasedRetryFailureParts<RunnerError> = (
    DirectFusedNativeScheduleSuspension,
    Vec<DirectFusedNativeLeaseCacheDisposition>,
    DirectFusedNativeLeasedSequence,
    Box<DirectFusedNativeSequenceExecutionFailure<RunnerError>>,
    DirectFusedNativeRetryTransfer,
);

struct DirectFusedNativeLeasedRetryBuffers {
    geometry: malbolge::ProfileExecutionGeometry,
    input: Vec<u8>,
    memory: Vec<u32>,
    output: Vec<u8>,
}

impl Display for DirectFusedNativeLeasedRetryAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::PlanIdentity => {
                f.write_str("fused leased retry plan identity drifted")
            },
        }
    }
}

impl DirectFusedNativeLeasedRetryAdmissionFailure {
    /// Returns the exact lease-binding rejection.
    #[must_use]
    pub const fn error(&self) -> DirectFusedNativeLeasedRetryAdmissionError {
        self.error
    }

    /// Consumes this rejection and restores retry plus acquisition ownership.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        DirectFusedNativeRetry,
        DirectFusedNativeSequenceCacheAcquisition,
    ) {
        (self.retry, self.acquisition)
    }
}

impl DirectFusedNativeLeasedRetry {
    /// Returns exact cache dispositions retained by this retry binding.
    #[must_use]
    pub fn cache_dispositions(
        &self,
    ) -> &[DirectFusedNativeLeaseCacheDisposition] {
        &self.dispositions
    }

    /// Executes this retry through already-resident fused region leases.
    ///
    /// # Errors
    ///
    /// Returns indexed whole-region failure with exact rollback state and all
    /// lease/disposition ownership retained.
    pub fn execute<Runner>(
        self,
        runner: &mut Runner,
    ) -> DirectFusedNativeLeasedRetryExecutionResult<Runner::Error>
    where
        Runner: DirectFusedNativeRunner,
    {
        let Self {
            dispositions,
            sequence,
            suspension,
        } = self;
        let mut buffers = leased_retry_buffers(&suspension, &sequence);
        let result = sequence.execute(
            runner,
            NativeRegionBuffers::new(
                &mut buffers.memory,
                &buffers.input,
                &mut buffers.output,
            ),
        );
        match result {
            Ok(outcome) => {
                let transfer = buffers.into_transfer(outcome.observation());
                Ok(DirectFusedNativeLeasedRetryExecution {
                    dispositions,
                    outcome,
                    sequence,
                    suspension,
                    transfer,
                })
            },
            Err(failure) => {
                let observation = failure.observation();
                let transfer = buffers.into_transfer(observation);
                Err(Box::new(DirectFusedNativeLeasedRetryExecutionFailure {
                    dispositions,
                    failure,
                    sequence,
                    suspension,
                    transfer,
                }))
            },
        }
    }

    /// Binds an admitted retry to one exact fused sequence cache acquisition.
    ///
    /// # Errors
    ///
    /// Returns ownership-preserving rejection before buffer movement when the
    /// acquired sequence plan differs from the retry plan.
    pub fn new(
        retry: DirectFusedNativeRetry,
        acquisition: DirectFusedNativeSequenceCacheAcquisition,
    ) -> Result<Self, Box<DirectFusedNativeLeasedRetryAdmissionFailure>> {
        if acquisition.sequence().plan() != retry.plan() {
            let error =
                DirectFusedNativeLeasedRetryAdmissionError::PlanIdentity;
            return Err(Box::new(
                DirectFusedNativeLeasedRetryAdmissionFailure {
                    acquisition,
                    error,
                    retry,
                },
            ));
        }
        let (suspension, _plan) = retry.into_parts();
        let (dispositions, sequence) = acquisition.into_parts();
        Ok(Self {
            dispositions,
            sequence,
            suspension,
        })
    }

    /// Returns the exact leased fused sequence retained by this retry.
    #[must_use]
    pub const fn sequence(&self) -> &DirectFusedNativeLeasedSequence {
        &self.sequence
    }

    /// Returns the exact scheduler suspension bound to this retry.
    #[must_use]
    pub const fn suspension(&self) -> &DirectFusedNativeScheduleSuspension {
        &self.suspension
    }
}

impl DirectFusedNativeLeasedRetryExecution {
    /// Returns exact cache dispositions retained after execution.
    #[must_use]
    pub fn cache_dispositions(
        &self,
    ) -> &[DirectFusedNativeLeaseCacheDisposition] {
        &self.dispositions
    }

    /// Consumes this success and restores all retained owners.
    #[must_use]
    pub fn into_parts(self) -> DirectFusedNativeLeasedRetrySuccessParts {
        (
            self.suspension,
            self.dispositions,
            self.sequence,
            self.outcome,
            self.transfer,
        )
    }

    /// Returns the exact resident execution outcome.
    #[must_use]
    pub const fn outcome(&self) -> DirectFusedNativeSequenceExecutionOutcome {
        self.outcome
    }

    /// Rebases successful resident retry work while preserving every lease.
    ///
    /// # Errors
    ///
    /// Returns ownership-preserving rejection when semantic rebase fails
    /// closed.
    pub fn rebase(
        self,
    ) -> Result<
        DirectFusedNativeLeasedRetryDisposition,
        Box<DirectFusedNativeLeasedRetryRebaseFailure>,
    > {
        let reason = match self.outcome {
            DirectFusedNativeSequenceExecutionOutcome::GuardMiss { .. } => {
                DirectFusedNativeContinuationReason::GuardMiss
            },
            DirectFusedNativeSequenceExecutionOutcome::Applied { .. } => {
                self.suspension.continuation().reason()
            },
        };
        let evidence = DirectFusedNativeRetryRebaseEvidence {
            observation: self.outcome.observation(),
            plan: self.sequence.plan(),
            reason,
            retry_regions: self.outcome.completed_regions(),
            retry_steps: self.outcome.completed_steps(),
            suspension: &self.suspension,
            transfer: &self.transfer,
        };
        match retry_rebase_evidence(evidence) {
            Ok(disposition) => {
                let Self {
                    dispositions, sequence, ..
                } = self;
                Ok(DirectFusedNativeLeasedRetryDisposition {
                    disposition,
                    dispositions,
                    sequence,
                })
            },
            Err(error) => {
                Err(Box::new(DirectFusedNativeLeasedRetryRebaseFailure {
                    error,
                    execution: self,
                }))
            },
        }
    }

    /// Returns exact transferred state after resident execution.
    #[must_use]
    pub const fn transfer(&self) -> &DirectFusedNativeRetryTransfer {
        &self.transfer
    }
}

impl<RunnerError> DirectFusedNativeLeasedRetryExecutionFailure<RunnerError> {
    /// Returns exact cache dispositions retained after failed execution.
    #[must_use]
    pub fn cache_dispositions(
        &self,
    ) -> &[DirectFusedNativeLeaseCacheDisposition] {
        &self.dispositions
    }

    /// Returns the exact indexed resident execution failure.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &DirectFusedNativeSequenceExecutionFailure<RunnerError> {
        &self.failure
    }

    /// Consumes this failure and restores all retained owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> DirectFusedNativeLeasedRetryFailureParts<RunnerError> {
        (
            self.suspension,
            self.dispositions,
            self.sequence,
            self.failure,
            self.transfer,
        )
    }

    /// Rebases failed resident retry work while preserving failure and leases.
    ///
    /// # Errors
    ///
    /// Returns ownership-preserving rejection when semantic rebase fails
    /// closed.
    pub fn rebase(
        self: Box<Self>,
    ) -> DirectFusedNativeLeasedRetryFailureRebaseResult<RunnerError> {
        let evidence = DirectFusedNativeRetryRebaseEvidence {
            observation: self.failure.observation(),
            plan: self.sequence.plan(),
            reason: DirectFusedNativeContinuationReason::ExecutionFailure,
            retry_regions: self.failure.completed_regions(),
            retry_steps: self.failure.completed_steps(),
            suspension: &self.suspension,
            transfer: &self.transfer,
        };
        match retry_rebase_evidence(evidence) {
            Ok(disposition) => {
                let Self {
                    dispositions,
                    failure,
                    sequence,
                    ..
                } = *self;
                Ok(DirectFusedNativeLeasedRetryFailureDisposition {
                    disposition,
                    dispositions,
                    failure,
                    sequence,
                })
            },
            Err(error) => Err(Box::new(
                DirectFusedNativeLeasedRetryFailureRebaseFailure {
                    error,
                    execution: self,
                },
            )),
        }
    }

    /// Returns the exact leased sequence retained after failure.
    #[must_use]
    pub const fn sequence(&self) -> &DirectFusedNativeLeasedSequence {
        &self.sequence
    }

    /// Returns exact rollback state transferred after failure.
    #[must_use]
    pub const fn transfer(&self) -> &DirectFusedNativeRetryTransfer {
        &self.transfer
    }
}

impl DirectFusedNativeLeasedRetryDisposition {
    /// Returns every cache insertion/hit disposition retained after rebase.
    #[must_use]
    pub fn cache_dispositions(
        &self,
    ) -> &[DirectFusedNativeLeaseCacheDisposition] {
        &self.dispositions
    }

    /// Returns the exact mixed-tier semantic disposition.
    #[must_use]
    pub const fn disposition(&self) -> &DirectFusedNativeRetryDisposition {
        &self.disposition
    }

    /// Consumes this result into semantic, cache, and resident lease owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        DirectFusedNativeRetryDisposition,
        Vec<DirectFusedNativeLeaseCacheDisposition>,
        DirectFusedNativeLeasedSequence,
    ) {
        (self.disposition, self.dispositions, self.sequence)
    }

    /// Returns the independently reusable resident fused sequence.
    #[must_use]
    pub const fn sequence(&self) -> &DirectFusedNativeLeasedSequence {
        &self.sequence
    }
}

impl<RunnerError> DirectFusedNativeLeasedRetryFailureDisposition<RunnerError> {
    /// Returns every cache insertion/hit disposition retained after rebase.
    #[must_use]
    pub fn cache_dispositions(
        &self,
    ) -> &[DirectFusedNativeLeaseCacheDisposition] {
        &self.dispositions
    }

    /// Returns the exact mixed-tier semantic disposition.
    #[must_use]
    pub const fn disposition(&self) -> &DirectFusedNativeRetryDisposition {
        &self.disposition
    }

    /// Returns the exact resident execution failure retained after rebase.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &DirectFusedNativeSequenceExecutionFailure<RunnerError> {
        &self.failure
    }

    /// Consumes this result into semantic, failure, cache, and lease owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> DirectFusedNativeLeasedRetryRebasedFailureParts<RunnerError> {
        (
            self.disposition,
            self.failure,
            self.dispositions,
            self.sequence,
        )
    }

    /// Returns the independently reusable resident fused sequence.
    #[must_use]
    pub const fn sequence(&self) -> &DirectFusedNativeLeasedSequence {
        &self.sequence
    }
}

impl DirectFusedNativeLeasedRetryRebaseFailure {
    /// Returns the exact semantic rebase rejection.
    #[must_use]
    pub const fn error(&self) -> DirectFusedNativeRetryRebaseError {
        self.error
    }

    /// Consumes this rejection and restores the successful execution owner.
    #[must_use]
    pub fn into_execution(self) -> DirectFusedNativeLeasedRetryExecution {
        self.execution
    }
}

impl<RunnerError>
    DirectFusedNativeLeasedRetryFailureRebaseFailure<RunnerError>
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
    ) -> Box<DirectFusedNativeLeasedRetryExecutionFailure<RunnerError>> {
        self.execution
    }
}

impl DirectFusedNativeLeasedRetryBuffers {
    fn into_transfer(
        self,
        observation: malbolge::ProfileMachineObservation,
    ) -> DirectFusedNativeRetryTransfer {
        DirectFusedNativeRetryTransfer::from_owned_parts(
            DirectFusedNativeRetryTransferParts {
                geometry: self.geometry,
                input: self.input,
                memory: self.memory,
                observation,
                output: self.output,
            },
        )
    }
}

fn leased_retry_buffers(
    suspension: &DirectFusedNativeScheduleSuspension,
    sequence: &DirectFusedNativeLeasedSequence,
) -> DirectFusedNativeLeasedRetryBuffers {
    let entry = suspension.state();
    let mut output = vec![
        0u8;
        sequence
            .plan()
            .exit()
            .output_len
            .max(entry.io().output().len())
    ];
    for (slot, value) in output.iter_mut().zip(entry.io().output()) {
        *slot = *value;
    }
    DirectFusedNativeLeasedRetryBuffers {
        geometry: entry.geometry(),
        input: entry.io().input().to_vec(),
        memory: entry.memory().to_vec(),
        output,
    }
}
