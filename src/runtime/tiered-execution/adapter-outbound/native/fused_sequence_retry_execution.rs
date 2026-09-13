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
//   - One uncached native execution attempt for an admitted fused retry.
// - Must-Not:
//   - Rebase semantic continuation, schedule fallback, or mutate caches.
// - Allows:
//   - Inputs: admitted fused retry, memory adapter, and fused runner.
//   - Outputs: exact transfer state plus success/failure ownership.
//   - Side effects: existing fused sequence transaction adapter/runner effects.
// - Split-When:
//   - Semantic rebase, cached retry, or retry routing gains policy.
// - Merge-When:
//   - One fused coordinator owns admission, execution, and rebase.
// - Summary:
//   - Executes one admitted fused native retry through the existing
//     transaction.
// - Description:
//   - Preserves transfer state at the exact semantic boundary on every result.
// - Usage:
//   - Call `execute_direct_fused_native_retry()` after exact retry admission.
// - Defaults:
//   - No fallback or second native attempt is inferred here.
//

//! Uncached execution for admitted fused native retry ownership.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    ProfileExecutionGeometry, ProfileMachineError, ProfileMachineIoState,
    ProfileMachineObservation, ProfileMachineState,
};

use super::DirectFusedNativeSequencePlan;
use super::fused_sequence_execution::DirectFusedNativeSequenceExecutionOutcome;
use super::fused_sequence_retry::DirectFusedNativeRetry;
use super::fused_sequence_scheduler::DirectFusedNativeScheduleSuspension;
use super::fused_sequence_transaction::{
    DirectFusedNativeSequenceTransactionFailure,
    execute_direct_fused_native_sequence,
};
use super::invocation::NativeRegionBuffers;
use super::platform::NativeExecutableMemoryAdapter;
use super::runner::DirectFusedNativeRunner;

/// Exact owned state transferred out of one fused native retry attempt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryTransfer {
    geometry: ProfileExecutionGeometry,
    input: Vec<u8>,
    memory: Vec<u32>,
    observation: ProfileMachineObservation,
    output: Vec<u8>,
}

/// Failure converting fused retry transfer buffers to a normative checkpoint.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedNativeRetryTransferError {
    /// Native observation names more committed output than owned capacity.
    OutputLength {
        /// Exact committed output length declared by the observation.
        expected: usize,
        /// Owned output capacity returned by native execution.
        observed: usize,
    },
    /// Normative checkpoint validation rejected transferred state.
    State(ProfileMachineError),
}

/// Successful fused native retry execution retaining exact entry ownership.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryExecution {
    outcome: DirectFusedNativeSequenceExecutionOutcome,
    plan: DirectFusedNativeSequencePlan,
    suspension: DirectFusedNativeScheduleSuspension,
    transfer: DirectFusedNativeRetryTransfer,
}

/// Failed fused native retry execution retaining state and cleanup evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeRetryExecutionFailure<MemoryError, RunnerError> {
    failure: Box<
        DirectFusedNativeSequenceTransactionFailure<MemoryError, RunnerError>,
    >,
    plan: DirectFusedNativeSequencePlan,
    suspension: DirectFusedNativeScheduleSuspension,
    transfer: DirectFusedNativeRetryTransfer,
}

/// Result of executing one admitted fused native retry.
pub type DirectFusedNativeRetryExecutionResult<MemoryError, RunnerError> =
    Result<
        DirectFusedNativeRetryExecution,
        Box<DirectFusedNativeRetryExecutionFailure<MemoryError, RunnerError>>,
    >;

/// Exact owners restored from one failed fused retry execution.
pub type DirectFusedNativeRetryFailureParts<MemoryError, RunnerError> = (
    DirectFusedNativeScheduleSuspension,
    DirectFusedNativeSequencePlan,
    Box<DirectFusedNativeSequenceTransactionFailure<MemoryError, RunnerError>>,
    DirectFusedNativeRetryTransfer,
);

type DirectFusedNativeRetryAdapterResult<MemoryAdapter, Runner> =
    DirectFusedNativeRetryExecutionResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as DirectFusedNativeRunner>::Error,
    >;

struct DirectFusedNativeRetryOwnedBuffers {
    geometry: ProfileExecutionGeometry,
    input: Vec<u8>,
    memory: Vec<u32>,
    output: Vec<u8>,
}

impl DirectFusedNativeRetryOwnedBuffers {
    fn into_transfer(
        self,
        observation: ProfileMachineObservation,
    ) -> DirectFusedNativeRetryTransfer {
        DirectFusedNativeRetryTransfer {
            geometry: self.geometry,
            input: self.input,
            memory: self.memory,
            observation,
            output: self.output,
        }
    }
}

impl Display for DirectFusedNativeRetryTransferError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::OutputLength { expected, observed } => write!(
                f,
                "fused retry output has {observed} of {expected} bytes",
            ),
            Self::State(error) => {
                write!(f, "fused retry checkpoint rejected: {error}")
            },
        }
    }
}

impl DirectFusedNativeRetryTransfer {
    /// Returns the exact execution geometry retained from the entry checkpoint.
    #[must_use]
    pub const fn geometry(&self) -> ProfileExecutionGeometry {
        self.geometry
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
    /// Returns exact output-length or normative state validation rejection.
    pub fn into_checkpoint(
        self,
    ) -> Result<ProfileMachineState, DirectFusedNativeRetryTransferError> {
        let committed = self.output.get(..self.observation.output_len).ok_or(
            DirectFusedNativeRetryTransferError::OutputLength {
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
        .map_err(DirectFusedNativeRetryTransferError::State)?;
        ProfileMachineState::new_with_geometry(
            self.geometry,
            self.memory,
            self.observation.registers,
            io,
        )
        .map_err(DirectFusedNativeRetryTransferError::State)
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
}

impl DirectFusedNativeRetryExecution {
    /// Consumes this success into suspension, plan, outcome, and transfer.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        DirectFusedNativeScheduleSuspension,
        DirectFusedNativeSequencePlan,
        DirectFusedNativeSequenceExecutionOutcome,
        DirectFusedNativeRetryTransfer,
    ) {
        (self.suspension, self.plan, self.outcome, self.transfer)
    }

    /// Returns the exact admitted fused retry outcome.
    #[must_use]
    pub const fn outcome(&self) -> DirectFusedNativeSequenceExecutionOutcome {
        self.outcome
    }

    /// Returns the exact verified fused plan executed by this retry.
    #[must_use]
    pub const fn plan(&self) -> &DirectFusedNativeSequencePlan {
        &self.plan
    }

    /// Returns the entry suspension consumed by this retry attempt.
    #[must_use]
    pub const fn suspension(&self) -> &DirectFusedNativeScheduleSuspension {
        &self.suspension
    }

    /// Returns exact state transferred out of native execution.
    #[must_use]
    pub const fn transfer(&self) -> &DirectFusedNativeRetryTransfer {
        &self.transfer
    }
}

impl<MemoryError, RunnerError>
    DirectFusedNativeRetryExecutionFailure<MemoryError, RunnerError>
{
    /// Returns the fused sequence transaction failure and cleanup evidence.
    #[must_use]
    pub const fn failure(
        &self,
    ) -> &DirectFusedNativeSequenceTransactionFailure<MemoryError, RunnerError>
    {
        &self.failure
    }

    /// Consumes this failure and restores every exact retained owner.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> DirectFusedNativeRetryFailureParts<MemoryError, RunnerError> {
        (self.suspension, self.plan, self.failure, self.transfer)
    }

    /// Returns the exact verified fused plan attempted by this retry.
    #[must_use]
    pub const fn plan(&self) -> &DirectFusedNativeSequencePlan {
        &self.plan
    }

    /// Returns the entry suspension consumed by this failed attempt.
    #[must_use]
    pub const fn suspension(&self) -> &DirectFusedNativeScheduleSuspension {
        &self.suspension
    }

    /// Returns exact rollback or committed state after the failed attempt.
    #[must_use]
    pub const fn transfer(&self) -> &DirectFusedNativeRetryTransfer {
        &self.transfer
    }
}

/// Executes one admitted fused retry through the fused sequence transaction.
///
/// The entry checkpoint is copied into owned native buffers. Success and
/// failure retain exact transferred state plus the original plan and scheduler
/// suspension. No semantic rebase or fallback decision occurs.
///
/// # Errors
///
/// Returns fused transaction failure with exact rollback or committed state.
pub fn execute_direct_fused_native_retry<MemoryAdapter, Runner>(
    retry: DirectFusedNativeRetry,
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
) -> DirectFusedNativeRetryAdapterResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: DirectFusedNativeRunner,
{
    let (suspension, plan) = retry.into_parts();
    let entry = suspension.state();
    let geometry = entry.geometry();
    let input = entry.io().input().to_vec();
    let mut memory = entry.memory().to_vec();
    let output_capacity = plan.exit().output_len.max(entry.io().output().len());
    let mut output = vec![0u8; output_capacity];
    if let Some(prefix) = output.get_mut(..entry.io().output().len()) {
        prefix.copy_from_slice(entry.io().output());
    }
    let result = execute_direct_fused_native_sequence(
        memory_adapter,
        runner,
        &plan,
        NativeRegionBuffers::new(&mut memory, &input, &mut output),
    );
    let buffers = DirectFusedNativeRetryOwnedBuffers {
        geometry,
        input,
        memory,
        output,
    };
    match result {
        Ok(outcome) => Ok(DirectFusedNativeRetryExecution {
            outcome,
            plan,
            suspension,
            transfer: buffers.into_transfer(outcome.observation()),
        }),
        Err(failure) => {
            let observation =
                transaction_failure_observation(&failure, plan.entry());
            Err(Box::new(DirectFusedNativeRetryExecutionFailure {
                failure,
                plan,
                suspension,
                transfer: buffers.into_transfer(observation),
            }))
        },
    }
}

const fn transaction_failure_observation<MemoryError, RunnerError>(
    failure: &DirectFusedNativeSequenceTransactionFailure<
        MemoryError,
        RunnerError,
    >,
    entry: ProfileMachineObservation,
) -> ProfileMachineObservation {
    if let Some(outcome) = failure.committed_outcome() {
        return outcome.observation();
    }
    if let Some(execution) = failure.execution_failure() {
        return execution.observation();
    }
    entry
}
