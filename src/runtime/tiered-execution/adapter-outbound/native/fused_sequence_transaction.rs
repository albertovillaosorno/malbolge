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
//   - One-shot load, ordered execution, and release of fused native sequences.
// - Must-Not:
//   - Own cache policy, fuse new regions, or implement platform operations.
// - Allows:
//   - Inputs: admitted fused sequence plan, memory adapter, runner, and
//     buffers.
//   - Outputs: semantic outcome or exact load/execution/release failure
//     evidence.
//   - Side effects: those of supplied memory and runner adapters only.
// - Split-When:
//   - Sequence cache reuse or continuation scheduling gains separate authority.
// - Merge-When:
//   - Loaded and one-shot fused execution share one transactional coordinator.
// - Summary:
//   - Composes exact fused sequence load, execution, and aggregate release.
// - Description:
//   - Cleanup failures retain retry ownership without erasing semantic
//     evidence.
// - Usage:
//   - Use when residency is not intended to survive the sequence call.
// - Defaults:
//   - Final release failure preserves an already committed semantic outcome.
//

//! One-shot orchestration for admitted fused native sequences.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::fused_loaded_sequence::{
    DirectFusedNativeSequenceLoadFailure,
    DirectFusedNativeSequenceReleaseFailure, load_direct_fused_native_sequence,
};
use super::fused_sequence_execution::{
    DirectFusedNativeSequenceExecutionFailure,
    DirectFusedNativeSequenceExecutionOutcome,
    execute_loaded_direct_fused_native_sequence,
};
use super::fused_sequence_plan::DirectFusedNativeSequencePlan;
use super::invocation::NativeRegionBuffers;
use super::platform::NativeExecutableMemoryAdapter;
use super::runner::DirectFusedNativeRunner;

#[derive(Debug, Eq, PartialEq)]
enum DirectFusedNativeSequenceTransactionCause<MemoryError, RunnerError> {
    Execution(Box<DirectFusedNativeSequenceExecutionFailure<RunnerError>>),
    Load(Box<DirectFusedNativeSequenceLoadFailure<MemoryError>>),
    Release(DirectFusedNativeSequenceExecutionOutcome),
}

/// One-shot fused sequence failure with independent cleanup retry evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeSequenceTransactionFailure<MemoryError, RunnerError>
{
    cause: DirectFusedNativeSequenceTransactionCause<MemoryError, RunnerError>,
    release_failure:
        Option<Box<DirectFusedNativeSequenceReleaseFailure<MemoryError>>>,
}

/// Result of one complete fused-sequence load/execute/release transaction.
pub type DirectFusedNativeSequenceTransactionResult<MemoryError, RunnerError> =
    Result<
        DirectFusedNativeSequenceExecutionOutcome,
        Box<
            DirectFusedNativeSequenceTransactionFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    >;

type DirectFusedNativeSequenceAdapterResult<MemoryAdapter, Runner> =
    DirectFusedNativeSequenceTransactionResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as DirectFusedNativeRunner>::Error,
    >;

impl<MemoryError, RunnerError>
    DirectFusedNativeSequenceTransactionFailure<MemoryError, RunnerError>
{
    /// Returns the committed semantic outcome when only final release failed.
    #[must_use]
    pub const fn committed_outcome(
        &self,
    ) -> Option<DirectFusedNativeSequenceExecutionOutcome> {
        match &self.cause {
            DirectFusedNativeSequenceTransactionCause::Release(outcome) => {
                Some(*outcome)
            },
            DirectFusedNativeSequenceTransactionCause::Execution(_)
            | DirectFusedNativeSequenceTransactionCause::Load(_) => None,
        }
    }

    /// Returns ordered loaded-execution failure, when execution failed.
    #[must_use]
    pub const fn execution_failure(
        &self,
    ) -> Option<&DirectFusedNativeSequenceExecutionFailure<RunnerError>> {
        match &self.cause {
            DirectFusedNativeSequenceTransactionCause::Execution(error) => {
                Some(error)
            },
            DirectFusedNativeSequenceTransactionCause::Load(_)
            | DirectFusedNativeSequenceTransactionCause::Release(_) => None,
        }
    }

    /// Consumes this failure and returns aggregate release retry ownership.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<DirectFusedNativeSequenceReleaseFailure<MemoryError>> {
        self.release_failure.map(|failure| *failure)
    }

    /// Returns whole-plan load failure, when loading failed before execution.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&DirectFusedNativeSequenceLoadFailure<MemoryError>> {
        match &self.cause {
            DirectFusedNativeSequenceTransactionCause::Load(error) => {
                Some(error)
            },
            DirectFusedNativeSequenceTransactionCause::Execution(_)
            | DirectFusedNativeSequenceTransactionCause::Release(_) => None,
        }
    }

    /// Returns aggregate final or post-failure cleanup retry evidence.
    #[must_use]
    pub const fn release_failure(
        &self,
    ) -> Option<&DirectFusedNativeSequenceReleaseFailure<MemoryError>> {
        match &self.release_failure {
            Some(failure) => Some(failure),
            None => None,
        }
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for DirectFusedNativeSequenceTransactionFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match &self.cause {
            DirectFusedNativeSequenceTransactionCause::Execution(error) => {
                write!(f, "fused sequence execution failed: {error}")?;
            },
            DirectFusedNativeSequenceTransactionCause::Load(error) => {
                write!(f, "fused sequence load failed: {error}")?;
            },
            DirectFusedNativeSequenceTransactionCause::Release(outcome) => {
                let label = match outcome {
                    DirectFusedNativeSequenceExecutionOutcome::Applied {
                        ..
                    } => "applied",
                    DirectFusedNativeSequenceExecutionOutcome::GuardMiss {
                        ..
                    } => "guard-miss",
                };
                write!(
                    f,
                    "fused sequence committed {label} but release failed"
                )?;
            },
        }
        if self.release_failure.is_some() {
            f.write_str("; executable cleanup remains retryable")?;
        }
        Ok(())
    }
}

/// Loads, executes, and releases one admitted fused native sequence.
///
/// Loading publishes no partial owner. An execution failure retains its exact
/// region/semantic progress while all loaded mappings are released in reverse;
/// cleanup failure is preserved independently. A final release failure after an
/// `Applied` or `GuardMiss` result retains that committed semantic outcome and
/// exact aggregate retry ownership.
///
/// # Errors
///
/// Returns exact load, execution, or final-release evidence with retry
/// ownership whenever executable cleanup does not complete.
pub fn execute_direct_fused_native_sequence<MemoryAdapter, Runner>(
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    plan: &DirectFusedNativeSequencePlan,
    buffers: NativeRegionBuffers<'_>,
) -> DirectFusedNativeSequenceAdapterResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: DirectFusedNativeRunner,
{
    let loaded = load_direct_fused_native_sequence(plan, memory_adapter)
        .map_err(|error| {
            Box::new(DirectFusedNativeSequenceTransactionFailure {
                cause: DirectFusedNativeSequenceTransactionCause::Load(error),
                release_failure: None,
            })
        })?;
    let outcome = match execute_loaded_direct_fused_native_sequence(
        &loaded, runner, buffers,
    ) {
        Ok(outcome) => outcome,
        Err(error) => {
            let release_failure = loaded.release(memory_adapter).err();
            return Err(Box::new(
                DirectFusedNativeSequenceTransactionFailure {
                    cause: DirectFusedNativeSequenceTransactionCause::Execution(
                        error,
                    ),
                    release_failure,
                },
            ));
        },
    };
    match loaded.release(memory_adapter) {
        Ok(()) => Ok(outcome),
        Err(release_failure) => {
            Err(Box::new(DirectFusedNativeSequenceTransactionFailure {
                cause: DirectFusedNativeSequenceTransactionCause::Release(
                    outcome,
                ),
                release_failure: Some(release_failure),
            }))
        },
    }
}
