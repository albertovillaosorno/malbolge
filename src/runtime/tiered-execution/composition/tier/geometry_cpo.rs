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
//   - Reusable four-mapping ownership for the exact theorem-derived crazy
//     prefix.
// - Must-Not:
//   - Generalize prefix length, remap during execution, publish partial loads,
//     or discard failed cleanup ownership.
// - Allows:
//   - Inputs: one admitted four-crazy prefix, adapter, runner, and buffers.
//   - Outputs: reusable owner, indexed outcome/failure, and exact weight.
//   - Side effects: four executable loads/releases; execution itself has none.
// - Split-When:
//   - Prefix cache policy or the following halt needs independent lifecycle.
// - Merge-When:
//   - Generic fixed-sequence ownership preserves indexed rollback exactly.
// - Summary:
//   - Owns, reuses, weighs, and releases all four crazy-prefix mappings.
// - Description:
//   - Composes existing one-step crazy owners without new mapping semantics.
// - Usage:
//   - Load once from an admitted prefix, execute repeatedly, then release.
// - Defaults:
//   - Partial load and final release retain exact failed cleanup ownership.
//

//! Reusable four-mapping ownership for the theorem-derived crazy prefix.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::ProfileMachineState;

use crate::execution_native::{
    ExecutionGeometryNativeExecutableReleaseFailure,
    ExecutionGeometryNativeRunner, NativeExecutableLoadFailure,
    NativeExecutableMemoryAdapter, NativeRegionBuffers,
    NativeRegionInvocationOutcome,
};
use crate::geometry_native_crazy::{
    ExecutionGeometryNativeCrazyOwnedFailure,
    LoadedExecutionGeometryNativeCrazy,
};
use crate::geometry_native_crazy_prefix::{
    ExecutionGeometryNativeCrazyPrefix,
    ExecutionGeometryNativeCrazyPrefixOutcome,
};

type ExecutableReleaseFailure<MemoryError> =
    ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>;
type ReleaseFailureSlot<MemoryError> =
    Option<Box<ExecutableReleaseFailure<MemoryError>>>;
type LoadFailure<MemoryError> = NativeExecutableLoadFailure<MemoryError>;
type WeightError = ExecutionGeometryNativeCrazyPrefixResidentWeightError;

/// Exact synchronized mapping weight retained by one loaded crazy prefix.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixResidentWeight {
    mapped_bytes: usize,
    mappings: usize,
}

/// Overflow while summing the four child-owner mapping reports.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyPrefixResidentWeightError {
    /// Mapped byte capacities overflowed host `usize`.
    MappedBytesOverflow,
    /// Live mapping counts overflowed host `usize`.
    MappingsOverflow,
}

/// Indexed reusable-prefix execution failure retaining committed state.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixOwnedFailure<RunnerError> {
    error: Box<ExecutionGeometryNativeCrazyOwnedFailure<RunnerError>>,
    index: usize,
    state: ProfileMachineState,
}

/// Aggregate failed release ownership for the four fixed prefix mappings.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixReleaseFailure<MemoryError> {
    failures: [ReleaseFailureSlot<MemoryError>; 4],
}

/// Primary load failure plus rollback ownership for earlier prefix mappings.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixLoadFailure<MemoryError> {
    error: Box<LoadFailure<MemoryError>>,
    index: usize,
    rollback_failure: Option<
        Box<ExecutionGeometryNativeCrazyPrefixReleaseFailure<MemoryError>>,
    >,
}

/// Reusable exact four-crazy owner retaining all synchronized child mappings.
#[derive(Debug)]
pub struct LoadedExecutionGeometryNativeCrazyPrefix {
    prefix: Box<ExecutionGeometryNativeCrazyPrefix>,
    steps: [LoadedExecutionGeometryNativeCrazy; 4],
}

/// Result of loading all four prefix mappings or rolling back partial loads.
pub type GeometryNativeCrazyPrefixLoadResult<MemoryError> = Result<
    LoadedExecutionGeometryNativeCrazyPrefix,
    Box<ExecutionGeometryNativeCrazyPrefixLoadFailure<MemoryError>>,
>;

/// Result of executing one reusable four-crazy prefix owner.
pub type GeometryNativeCrazyPrefixOwnedResult<RunnerError> = Result<
    ExecutionGeometryNativeCrazyPrefixOutcome,
    Box<ExecutionGeometryNativeCrazyPrefixOwnedFailure<RunnerError>>,
>;

/// Result of releasing every mapping retained by one loaded crazy prefix.
pub type GeometryNativeCrazyPrefixReleaseResult<MemoryError> = Result<
    (),
    Box<ExecutionGeometryNativeCrazyPrefixReleaseFailure<MemoryError>>,
>;

struct ExecutionProgress<'buffers> {
    input: &'buffers [u8],
    memory: &'buffers mut [u32],
    output: &'buffers mut [u8],
    state: ProfileMachineState,
}

impl Display for ExecutionGeometryNativeCrazyPrefixResidentWeightError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::MappedBytesOverflow => {
                f.write_str("v5 crazy-prefix mapped-byte weight overflowed")
            },
            Self::MappingsOverflow => {
                f.write_str("v5 crazy-prefix mapping-count weight overflowed")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeCrazyPrefixOwnedFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "v5 owned crazy prefix failed at {}: {}",
            self.index, self.error
        )
    }
}

impl<MemoryError: Display> Display
    for ExecutionGeometryNativeCrazyPrefixLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "v5 crazy-prefix load failed at {}: {}",
            self.index, self.error
        )
    }
}

impl<MemoryError: Display> Display
    for ExecutionGeometryNativeCrazyPrefixReleaseFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "v5 crazy-prefix release incomplete ({} mappings)",
            self.failure_count()
        )
    }
}

impl<MemoryError> ExecutionGeometryNativeCrazyPrefixLoadFailure<MemoryError> {
    /// Reports whether primary load or rollback still owns cleanup work.
    #[must_use]
    pub fn cleanup_pending(&self) -> bool {
        self.error.cleanup_pending() || self.rollback_failure.is_some()
    }

    /// Returns the zero-based prefix step whose mapping failed to load.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Retries primary and rollback cleanup without changing failure identity.
    #[must_use]
    pub fn retry_cleanup<Adapter>(self, adapter: &mut Adapter) -> Self
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        let rollback_failure = self
            .rollback_failure
            .and_then(|failure| (*failure).retry(adapter).err());
        Self {
            error: Box::new((*self.error).retry_cleanup(adapter)),
            index: self.index,
            rollback_failure,
        }
    }
}

impl<RunnerError> ExecutionGeometryNativeCrazyPrefixOwnedFailure<RunnerError> {
    /// Borrows the exact one-step owner failure.
    #[must_use]
    pub const fn error(
        &self,
    ) -> &ExecutionGeometryNativeCrazyOwnedFailure<RunnerError> {
        &self.error
    }

    /// Returns the zero-based prefix step that failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Returns the last fully committed prefix checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl<MemoryError>
    ExecutionGeometryNativeCrazyPrefixReleaseFailure<MemoryError>
{
    /// Returns the number of prefix mappings whose cleanup remains pending.
    #[must_use]
    pub fn failure_count(&self) -> usize {
        self.failures
            .iter()
            .filter(|failure| failure.is_some())
            .count()
    }

    /// Retries every failed release and retains only still-failing mappings.
    ///
    /// # Errors
    ///
    /// Returns refreshed exact cleanup ownership when any release still fails.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeCrazyPrefixReleaseResult<MemoryError>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        release_result(Self {
            failures: self
                .failures
                .map(|failure| retry_release(failure, adapter)),
        })
    }
}

impl ExecutionGeometryNativeCrazyPrefixResidentWeight {
    /// Returns exact mapped bytes retained by all four child owners.
    #[must_use]
    pub const fn mapped_bytes(self) -> usize {
        self.mapped_bytes
    }

    /// Returns exact live mapping count retained by all four child owners.
    #[must_use]
    pub const fn mappings(self) -> usize {
        self.mappings
    }
}

impl LoadedExecutionGeometryNativeCrazyPrefix {
    /// Executes all four retained mappings without executable-memory work.
    ///
    /// # Errors
    ///
    /// Returns exact prefix index, last committed state, and one-step failure
    /// while retaining all mappings for reuse.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeCrazyPrefixOwnedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeCrazyPrefixOutcome as Outcome;

        let (memory, input, output) = buffers.into_parts();
        let mut progress = ExecutionProgress {
            input,
            memory,
            output,
            state: self.prefix.entry_state().clone(),
        };
        for (index, step) in self.steps.iter().enumerate() {
            let completion =
                step.execute(runner, progress.buffers()).map_err(|error| {
                    Box::new(ExecutionGeometryNativeCrazyPrefixOwnedFailure {
                        error,
                        index,
                        state: progress.state.clone(),
                    })
                })?;
            progress.state = completion.state().clone();
            if completion.outcome() == NativeRegionInvocationOutcome::GuardMiss
            {
                return Ok(Outcome::GuardMiss {
                    index,
                    state: progress.state,
                });
            }
        }
        Ok(Outcome::Completed(progress.state))
    }

    /// Loads all four exact prefix mappings and rolls back earlier mappings.
    ///
    /// # Errors
    ///
    /// Returns the failing prefix index, primary load evidence, and rollback
    /// cleanup ownership from any earlier mappings.
    pub fn load<Adapter>(
        prefix: &ExecutionGeometryNativeCrazyPrefix,
        adapter: &mut Adapter,
    ) -> GeometryNativeCrazyPrefixLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let [step0, step1, step2, step3] = prefix.steps();
        let loaded0 = step0
            .load_owned(adapter)
            .map_err(|error| Box::new(load_failure(0, error, None)))?;
        let loaded1 = match step1.load_owned(adapter) {
            Ok(owner) => owner,
            Err(error) => {
                let rollback =
                    release_loaded([Some(loaded0), None, None, None], adapter)
                        .err();
                return Err(Box::new(load_failure(1, error, rollback)));
            },
        };
        let loaded2 = match step2.load_owned(adapter) {
            Ok(owner) => owner,
            Err(error) => {
                let rollback = release_loaded(
                    [Some(loaded0), Some(loaded1), None, None],
                    adapter,
                )
                .err();
                return Err(Box::new(load_failure(2, error, rollback)));
            },
        };
        let loaded3 = match step3.load_owned(adapter) {
            Ok(owner) => owner,
            Err(error) => {
                let rollback = release_loaded(
                    [Some(loaded0), Some(loaded1), Some(loaded2), None],
                    adapter,
                )
                .err();
                return Err(Box::new(load_failure(3, error, rollback)));
            },
        };
        Ok(Self {
            prefix: Box::new(prefix.clone()),
            steps: [loaded0, loaded1, loaded2, loaded3],
        })
    }

    /// Returns the exact admitted prefix owned beside the four mappings.
    #[must_use]
    pub const fn prefix(&self) -> &ExecutionGeometryNativeCrazyPrefix {
        &self.prefix
    }

    /// Releases all four mappings and aggregates every failed cleanup token.
    ///
    /// # Errors
    ///
    /// Attempts every mapping even after failure and returns exact retry
    /// ownership for only those releases that remain incomplete.
    pub fn release<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeCrazyPrefixReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        release_loaded(self.steps.map(Some), adapter)
    }

    /// Returns exact resident weight checked across all four child owners.
    ///
    /// # Errors
    ///
    /// Returns overflow instead of publishing truncated aggregate weight.
    pub fn resident_weight(
        &self,
    ) -> Result<
        ExecutionGeometryNativeCrazyPrefixResidentWeight,
        ExecutionGeometryNativeCrazyPrefixResidentWeightError,
    > {
        let mapped_bytes = self
            .steps
            .iter()
            .map(|step| step.resident_weight().mapped_bytes())
            .try_fold(0usize, usize::checked_add)
            .ok_or(WeightError::MappedBytesOverflow)?;
        let mappings = self
            .steps
            .iter()
            .map(|step| step.resident_weight().mappings())
            .try_fold(0usize, usize::checked_add)
            .ok_or(WeightError::MappingsOverflow)?;
        Ok(ExecutionGeometryNativeCrazyPrefixResidentWeight {
            mapped_bytes,
            mappings,
        })
    }
}

impl ExecutionProgress<'_> {
    const fn buffers(&mut self) -> NativeRegionBuffers<'_> {
        NativeRegionBuffers::new(
            &mut *self.memory,
            self.input,
            &mut *self.output,
        )
    }
}

const fn load_failure<MemoryError>(
    index: usize,
    error: Box<LoadFailure<MemoryError>>,
    rollback_failure: Option<
        Box<ExecutionGeometryNativeCrazyPrefixReleaseFailure<MemoryError>>,
    >,
) -> ExecutionGeometryNativeCrazyPrefixLoadFailure<MemoryError> {
    ExecutionGeometryNativeCrazyPrefixLoadFailure {
        error,
        index,
        rollback_failure,
    }
}

fn release_loaded<Adapter>(
    steps: [Option<LoadedExecutionGeometryNativeCrazy>; 4],
    adapter: &mut Adapter,
) -> GeometryNativeCrazyPrefixReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    release_result(ExecutionGeometryNativeCrazyPrefixReleaseFailure {
        failures: steps
            .map(|step| step.and_then(|loaded| loaded.release(adapter).err())),
    })
}

fn release_result<MemoryError>(
    failure: ExecutionGeometryNativeCrazyPrefixReleaseFailure<MemoryError>,
) -> GeometryNativeCrazyPrefixReleaseResult<MemoryError> {
    if failure.failure_count() == 0 {
        Ok(())
    } else {
        Err(Box::new(failure))
    }
}

fn retry_release<Adapter>(
    failure: ReleaseFailureSlot<Adapter::Error>,
    adapter: &mut Adapter,
) -> ReleaseFailureSlot<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    failure.and_then(|error| (*error).retry(adapter).err().map(Box::new))
}
