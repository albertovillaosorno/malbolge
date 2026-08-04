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
//   - Exact binding and execution of admitted retries through immutable leases.
// - Must-Not:
//   - Acquire cache entries, release mappings, infer fallback, or hide leases.
// - Allows:
//   - Inputs: admitted retry, exact acquisition, and explicit native runner.
//   - Outputs: semantic disposition plus cache/lease and loaded-failure owners.
//   - Side effects: execution through already loaded exact mappings only.
// - Split-When:
//   - Cache acquisition or multi-turn orchestration gains separate ownership.
// - Merge-When:
//   - One product coordinator owns cache admission, execution, and return.
// - Summary:
//   - Executes exact native retries without allocation or implicit cleanup.
// - Description:
//   - Loaded success/failure keeps the immutable lease independently reusable.
// - Usage:
//   - Bind an exact lease-cache acquisition to an admitted continuation retry.
// - Defaults:
//   - Lease-key drift fails before buffer movement and returns both owners.
//

//! Exact native continuation retry execution through immutable loaded leases.

use malbolge::{ProfileDescriptor, ProfileMachineObservation};

use crate::continuation_scheduler::NativeContinuationScheduleSuspension;
use crate::execution_native::{
    NativeExecutableRunner, NativeExecutableSequenceKey,
    NativeExecutableSequenceLease,
    NativeExecutableSequenceLeaseCacheAcquisition,
    NativeExecutableSequenceLeaseCacheDisposition,
    NativeInterpreterContinuationReason, NativeLoadedSequenceExecutionFailure,
    NativeRegionBuffers, NativeSequenceExecutionOutcome,
    VerifiedDirectSequencePlan, execute_loaded_verified_native_sequence,
};
use crate::native_retry::{
    NativeContinuationNativeRetry, NativeContinuationRetryDisposition,
    NativeContinuationRetryRebaseError, NativeContinuationRetryRebaseEvidence,
    NativeContinuationRetryTransfer, NativeContinuationRetryTransferParts,
    retry_rebase_evidence,
};

/// Why one acquired executable lease was rejected before retry execution.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationLeasedRetryAdmissionError {
    /// Acquired ready sequence identity differs from the admitted retry plan.
    LeaseKey,
}

/// Rejected leased retry binding retaining both exact supplied owners.
#[derive(Debug)]
pub struct NativeContinuationLeasedRetryAdmissionFailure {
    acquisition: NativeExecutableSequenceLeaseCacheAcquisition,
    error: NativeContinuationLeasedRetryAdmissionError,
    retry: NativeContinuationNativeRetry,
}

/// Exact admitted retry bound to one immutable executable lease.
#[derive(Debug)]
pub struct NativeContinuationLeasedRetry {
    cache_disposition: NativeExecutableSequenceLeaseCacheDisposition,
    lease: NativeExecutableSequenceLease,
    plan: VerifiedDirectSequencePlan,
    suspension: NativeContinuationScheduleSuspension,
}

/// Successful loaded retry execution retaining cache and lease ownership.
#[derive(Debug)]
pub struct NativeContinuationLeasedRetryExecution {
    cache_disposition: NativeExecutableSequenceLeaseCacheDisposition,
    lease: NativeExecutableSequenceLease,
    outcome: NativeSequenceExecutionOutcome,
    plan: VerifiedDirectSequencePlan,
    suspension: NativeContinuationScheduleSuspension,
    transfer: NativeContinuationRetryTransfer,
}

/// Failed loaded retry execution retaining cache and lease ownership.
#[derive(Debug)]
pub struct NativeContinuationLeasedRetryExecutionFailure<RunnerError> {
    cache_disposition: NativeExecutableSequenceLeaseCacheDisposition,
    failure: Box<NativeLoadedSequenceExecutionFailure<RunnerError>>,
    lease: NativeExecutableSequenceLease,
    plan: VerifiedDirectSequencePlan,
    suspension: NativeContinuationScheduleSuspension,
    transfer: NativeContinuationRetryTransfer,
}

/// Successful semantic rebase with its independently reusable lease.
#[derive(Debug)]
pub struct NativeContinuationLeasedRetryDisposition {
    cache_disposition: NativeExecutableSequenceLeaseCacheDisposition,
    disposition: NativeContinuationRetryDisposition,
    lease: NativeExecutableSequenceLease,
}

/// Failed loaded execution plus independently rebased semantic disposition.
#[derive(Debug)]
pub struct NativeContinuationLeasedRetryFailureDisposition<RunnerError> {
    cache_disposition: NativeExecutableSequenceLeaseCacheDisposition,
    disposition: NativeContinuationRetryDisposition,
    failure: Box<NativeLoadedSequenceExecutionFailure<RunnerError>>,
    lease: NativeExecutableSequenceLease,
}

/// Rebase rejection retaining the complete successful leased execution owner.
#[derive(Debug)]
pub struct NativeContinuationLeasedRetryRebaseFailure {
    error: NativeContinuationRetryRebaseError,
    execution: NativeContinuationLeasedRetryExecution,
}

/// Rebase rejection retaining the complete failed leased execution owner.
#[derive(Debug)]
pub struct NativeContinuationLeasedRetryFailureRebaseFailure<RunnerError> {
    error: NativeContinuationRetryRebaseError,
    execution: Box<NativeContinuationLeasedRetryExecutionFailure<RunnerError>>,
}

/// Semantic, loaded failure, cache evidence, and immutable lease owners.
pub type NativeContinuationLeasedRetryFailureParts<RunnerError> = (
    NativeContinuationRetryDisposition,
    Box<NativeLoadedSequenceExecutionFailure<RunnerError>>,
    NativeExecutableSequenceLeaseCacheDisposition,
    NativeExecutableSequenceLease,
);

/// Result of one loaded retry attempt.
pub type NativeContinuationLeasedRetryExecutionResult<RunnerError> = Result<
    NativeContinuationLeasedRetryExecution,
    Box<NativeContinuationLeasedRetryExecutionFailure<RunnerError>>,
>;

/// Result of rebasing one failed loaded retry attempt.
pub type NativeContinuationLeasedRetryFailureRebaseResult<RunnerError> = Result<
    NativeContinuationLeasedRetryFailureDisposition<RunnerError>,
    Box<NativeContinuationLeasedRetryFailureRebaseFailure<RunnerError>>,
>;

struct NativeContinuationLeasedRetryBuffers {
    input: Vec<u8>,
    memory: Vec<u32>,
    output: Vec<u8>,
    profile: &'static ProfileDescriptor,
}

impl NativeContinuationLeasedRetryAdmissionFailure {
    /// Returns the exact lease binding rejection.
    #[must_use]
    pub const fn error(&self) -> NativeContinuationLeasedRetryAdmissionError {
        self.error
    }

    /// Consumes this failure and restores retry plus cache acquisition owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        NativeContinuationNativeRetry,
        NativeExecutableSequenceLeaseCacheAcquisition,
    ) {
        (self.retry, self.acquisition)
    }
}

impl NativeContinuationLeasedRetry {
    /// Returns exact cache hit/insertion evidence for the bound lease.
    #[must_use]
    pub const fn cache_disposition(
        &self,
    ) -> &NativeExecutableSequenceLeaseCacheDisposition {
        &self.cache_disposition
    }

    /// Executes this retry through its already loaded immutable sequence.
    ///
    /// No executable allocation or release occurs. Success and failure retain
    /// the lease, cache disposition, complete plan, and transferred guest
    /// state.
    ///
    /// # Errors
    ///
    /// Returns [`NativeContinuationLeasedRetryExecutionFailure`] for loaded
    /// chain admission, preparation, runner, or completion failure.
    pub fn execute<Runner>(
        self,
        runner: &mut Runner,
    ) -> NativeContinuationLeasedRetryExecutionResult<Runner::Error>
    where
        Runner: NativeExecutableRunner,
    {
        let Self {
            cache_disposition,
            lease,
            plan,
            suspension,
        } = self;
        let mut buffers = leased_retry_buffers(&suspension, &plan);
        let result = execute_loaded_verified_native_sequence(
            runner,
            &plan,
            lease.sequence(),
            NativeRegionBuffers::new(
                &mut buffers.memory,
                &buffers.input,
                &mut buffers.output,
            ),
        );
        match result {
            Ok(outcome) => {
                let transfer = buffers.into_transfer(outcome.observation());
                Ok(NativeContinuationLeasedRetryExecution {
                    cache_disposition,
                    lease,
                    outcome,
                    plan,
                    suspension,
                    transfer,
                })
            },
            Err(failure) => {
                let observation = failure.observation();
                let transfer = buffers.into_transfer(observation);
                Err(Box::new(NativeContinuationLeasedRetryExecutionFailure {
                    cache_disposition,
                    failure,
                    lease,
                    plan,
                    suspension,
                    transfer,
                }))
            },
        }
    }

    /// Returns the immutable executable lease bound to this retry.
    #[must_use]
    pub const fn lease(&self) -> &NativeExecutableSequenceLease {
        &self.lease
    }

    /// Binds one exact lease-cache acquisition to an admitted retry.
    ///
    /// # Errors
    ///
    /// Returns [`NativeContinuationLeasedRetryAdmissionFailure`] before buffer
    /// movement when the acquired lease key differs from the retry plan key.
    pub fn new(
        retry: NativeContinuationNativeRetry,
        acquisition: NativeExecutableSequenceLeaseCacheAcquisition,
    ) -> Result<Self, Box<NativeContinuationLeasedRetryAdmissionFailure>> {
        let expected = NativeExecutableSequenceKey::from_plan(retry.plan());
        if acquisition.lease().key() != &expected {
            return Err(Box::new(
                NativeContinuationLeasedRetryAdmissionFailure {
                    acquisition,
                    error:
                        NativeContinuationLeasedRetryAdmissionError::LeaseKey,
                    retry,
                },
            ));
        }
        let cache_disposition = acquisition.disposition().clone();
        let lease = acquisition.into_lease();
        let (suspension, plan) = retry.into_parts();
        Ok(Self {
            cache_disposition,
            lease,
            plan,
            suspension,
        })
    }

    /// Returns the exact admitted retry plan.
    #[must_use]
    pub const fn plan(&self) -> &VerifiedDirectSequencePlan {
        &self.plan
    }
}

impl NativeContinuationLeasedRetryBuffers {
    fn into_transfer(
        self,
        observation: ProfileMachineObservation,
    ) -> NativeContinuationRetryTransfer {
        NativeContinuationRetryTransfer::from_parts(
            NativeContinuationRetryTransferParts {
                input: self.input,
                memory: self.memory,
                observation,
                output: self.output,
                profile: self.profile,
            },
        )
    }
}

impl NativeContinuationLeasedRetryDisposition {
    /// Returns cache hit/insertion evidence retained after semantic rebase.
    #[must_use]
    pub const fn cache_disposition(
        &self,
    ) -> &NativeExecutableSequenceLeaseCacheDisposition {
        &self.cache_disposition
    }

    /// Returns the exact mixed-tier semantic disposition.
    #[must_use]
    pub const fn disposition(&self) -> &NativeContinuationRetryDisposition {
        &self.disposition
    }

    /// Consumes this result into semantic and immutable lease owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        NativeContinuationRetryDisposition,
        NativeExecutableSequenceLeaseCacheDisposition,
        NativeExecutableSequenceLease,
    ) {
        (self.disposition, self.cache_disposition, self.lease)
    }

    /// Returns the independently reusable executable lease.
    #[must_use]
    pub const fn lease(&self) -> &NativeExecutableSequenceLease {
        &self.lease
    }
}

impl<RunnerError> NativeContinuationLeasedRetryFailureDisposition<RunnerError> {
    /// Returns cache hit/insertion evidence retained after failed execution.
    #[must_use]
    pub const fn cache_disposition(
        &self,
    ) -> &NativeExecutableSequenceLeaseCacheDisposition {
        &self.cache_disposition
    }

    /// Returns the exact mixed-tier semantic disposition.
    #[must_use]
    pub const fn disposition(&self) -> &NativeContinuationRetryDisposition {
        &self.disposition
    }

    /// Returns the loaded runner/admission failure.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &NativeLoadedSequenceExecutionFailure<RunnerError> {
        &self.failure
    }

    /// Consumes this result into semantic, failure, cache, and lease owners.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> NativeContinuationLeasedRetryFailureParts<RunnerError> {
        (
            self.disposition,
            self.failure,
            self.cache_disposition,
            self.lease,
        )
    }

    /// Returns the independently reusable executable lease.
    #[must_use]
    pub const fn lease(&self) -> &NativeExecutableSequenceLease {
        &self.lease
    }
}

impl NativeContinuationLeasedRetryExecution {
    /// Returns cache hit/insertion evidence for the executed lease.
    #[must_use]
    pub const fn cache_disposition(
        &self,
    ) -> &NativeExecutableSequenceLeaseCacheDisposition {
        &self.cache_disposition
    }

    /// Returns the immutable executable lease used by this attempt.
    #[must_use]
    pub const fn lease(&self) -> &NativeExecutableSequenceLease {
        &self.lease
    }

    /// Returns the exact loaded sequence outcome.
    #[must_use]
    pub const fn outcome(&self) -> NativeSequenceExecutionOutcome {
        self.outcome
    }

    /// Returns the exact verified plan executed through this lease.
    #[must_use]
    pub const fn plan(&self) -> &VerifiedDirectSequencePlan {
        &self.plan
    }

    /// Rebases this successful loaded retry onto complete semantic authority.
    ///
    /// # Errors
    ///
    /// Returns [`NativeContinuationLeasedRetryRebaseFailure`] while retaining
    /// the complete execution and lease owners.
    pub fn rebase(
        self,
    ) -> Result<
        NativeContinuationLeasedRetryDisposition,
        Box<NativeContinuationLeasedRetryRebaseFailure>,
    > {
        let reason = match self.outcome {
            NativeSequenceExecutionOutcome::GuardMiss { .. } => {
                NativeInterpreterContinuationReason::GuardMiss
            },
            NativeSequenceExecutionOutcome::Applied { .. } => {
                self.suspension.continuation().reason()
            },
        };
        match retry_rebase_evidence(NativeContinuationRetryRebaseEvidence {
            observation: self.outcome.observation(),
            reason,
            retry_steps: self.outcome.completed_steps(),
            suspension: &self.suspension,
            transfer: &self.transfer,
        }) {
            Ok(disposition) => Ok(NativeContinuationLeasedRetryDisposition {
                cache_disposition: self.cache_disposition,
                disposition,
                lease: self.lease,
            }),
            Err(error) => {
                Err(Box::new(NativeContinuationLeasedRetryRebaseFailure {
                    error,
                    execution: self,
                }))
            },
        }
    }

    /// Returns exact state transferred out of loaded execution.
    #[must_use]
    pub const fn transfer(&self) -> &NativeContinuationRetryTransfer {
        &self.transfer
    }
}

impl<RunnerError> NativeContinuationLeasedRetryExecutionFailure<RunnerError> {
    /// Returns cache hit/insertion evidence for the failed attempt.
    #[must_use]
    pub const fn cache_disposition(
        &self,
    ) -> &NativeExecutableSequenceLeaseCacheDisposition {
        &self.cache_disposition
    }

    /// Returns the exact loaded sequence failure.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &NativeLoadedSequenceExecutionFailure<RunnerError> {
        &self.failure
    }

    /// Returns the immutable executable lease used by this attempt.
    #[must_use]
    pub const fn lease(&self) -> &NativeExecutableSequenceLease {
        &self.lease
    }

    /// Returns the exact verified plan attempted through this lease.
    #[must_use]
    pub const fn plan(&self) -> &VerifiedDirectSequencePlan {
        &self.plan
    }

    /// Rebases failed loaded execution while preserving failure and lease
    /// owners.
    ///
    /// # Errors
    ///
    /// Returns [`NativeContinuationLeasedRetryFailureRebaseFailure`] while
    /// retaining this complete failed execution owner.
    pub fn rebase(
        self: Box<Self>,
    ) -> NativeContinuationLeasedRetryFailureRebaseResult<RunnerError> {
        match retry_rebase_evidence(NativeContinuationRetryRebaseEvidence {
            observation: self.failure.observation(),
            reason: NativeInterpreterContinuationReason::ExecutionFailure,
            retry_steps: self.failure.completed_steps(),
            suspension: &self.suspension,
            transfer: &self.transfer,
        }) {
            Ok(disposition) => {
                let Self {
                    cache_disposition,
                    failure,
                    lease,
                    ..
                } = *self;
                Ok(NativeContinuationLeasedRetryFailureDisposition {
                    cache_disposition,
                    disposition,
                    failure,
                    lease,
                })
            },
            Err(error) => Err(Box::new(
                NativeContinuationLeasedRetryFailureRebaseFailure {
                    error,
                    execution: self,
                },
            )),
        }
    }

    /// Returns exact state transferred out of failed loaded execution.
    #[must_use]
    pub const fn transfer(&self) -> &NativeContinuationRetryTransfer {
        &self.transfer
    }
}

impl NativeContinuationLeasedRetryRebaseFailure {
    /// Returns the exact semantic rebase rejection.
    #[must_use]
    pub const fn error(&self) -> NativeContinuationRetryRebaseError {
        self.error
    }

    /// Consumes this rejection and restores the successful execution owner.
    #[must_use]
    pub fn into_execution(self) -> NativeContinuationLeasedRetryExecution {
        self.execution
    }
}

impl<RunnerError>
    NativeContinuationLeasedRetryFailureRebaseFailure<RunnerError>
{
    /// Returns the exact semantic rebase rejection.
    #[must_use]
    pub const fn error(&self) -> NativeContinuationRetryRebaseError {
        self.error
    }

    /// Consumes this rejection and restores the failed execution owner.
    #[must_use]
    pub fn into_execution(
        self,
    ) -> Box<NativeContinuationLeasedRetryExecutionFailure<RunnerError>> {
        self.execution
    }
}

fn leased_retry_buffers(
    suspension: &NativeContinuationScheduleSuspension,
    plan: &VerifiedDirectSequencePlan,
) -> NativeContinuationLeasedRetryBuffers {
    let entry = suspension.state();
    let input = entry.io().input().to_vec();
    let memory = entry.memory().to_vec();
    let output_capacity = plan.exit().output_len.max(entry.io().output().len());
    let mut output = vec![0u8; output_capacity];
    if let Some(prefix) = output.get_mut(..entry.io().output().len()) {
        prefix.copy_from_slice(entry.io().output());
    }
    NativeContinuationLeasedRetryBuffers {
        input,
        memory,
        output,
        profile: entry.profile(),
    }
}
