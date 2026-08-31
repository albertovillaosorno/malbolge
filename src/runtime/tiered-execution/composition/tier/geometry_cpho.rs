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
//   - Reusable five-mapping ownership for the exact `p p p p v` theorem suffix.
// - Must-Not:
//   - Generalize suffix length, remap during execution, duplicate child mapping
//     ownership, or discard failed cleanup evidence.
// - Allows:
//   - Inputs: one admitted prefix/halt sequence, adapter, runner, and buffers.
//   - Outputs: reusable owner, exact suffix outcome/failure, and exact weight.
//   - Side effects: delegated four-prefix plus one-halt loads/releases only.
// - Split-When:
//   - Suffix cache policy or preceding jump/rotate ownership needs a boundary.
// - Merge-When:
//   - Generic fixed-sequence ownership preserves child cleanup contracts.
// - Summary:
//   - Owns the four-crazy prefix and final halt as five reusable mappings.
// - Description:
//   - Composes the prefix owner with the reusable initial-halt owner.
// - Usage:
//   - Load once from an admitted suffix, execute repeatedly, then release.
// - Defaults:
//   - Halt load rolls back the prefix; final release attempts both child
//     owners.
//

//! Reusable five-mapping ownership for the theorem-derived crazy/halt suffix.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::ProfileMachineState;

use crate::execution_native::{
    ExecutionGeometryNativeExecutableReleaseFailure,
    ExecutionGeometryNativeRunner, NativeExecutableLoadFailure,
    NativeExecutableMemoryAdapter, NativeRegionBuffers,
    NativeRegionInvocationOutcome,
};
use crate::geometry_native_admission::{
    ExecutionGeometryNativeInitialHaltOwnedFailure,
    LoadedExecutionGeometryNativeInitialHalt,
};
use crate::geometry_native_crazy_prefix as prefix_sequence;
use crate::geometry_native_crazy_prefix_halt_sequence::{
    ExecutionGeometryNativeCrazyPrefixHaltOutcome,
    ExecutionGeometryNativeCrazyPrefixHaltSequence,
};
use crate::geometry_native_crazy_prefix_owner::{
    ExecutionGeometryNativeCrazyPrefixLoadFailure,
    ExecutionGeometryNativeCrazyPrefixOwnedFailure,
    ExecutionGeometryNativeCrazyPrefixReleaseFailure,
    ExecutionGeometryNativeCrazyPrefixResidentWeightError,
    LoadedExecutionGeometryNativeCrazyPrefix,
};

type ExecutableReleaseFailure<MemoryError> =
    ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>;
type LoadFailure<MemoryError> = NativeExecutableLoadFailure<MemoryError>;
type WeightError = ExecutionGeometryNativeCrazyPrefixHaltResidentWeightError;
type PrefixOutcome = prefix_sequence::ExecutionGeometryNativeCrazyPrefixOutcome;
type OwnedCause<RunnerError> =
    ExecutionGeometryNativeCrazyPrefixHaltOwnedFailureCause<RunnerError>;
type PrefixWeightError = ExecutionGeometryNativeCrazyPrefixResidentWeightError;

/// Exact synchronized mapping weight retained by one loaded five-step suffix.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixHaltResidentWeight {
    mapped_bytes: usize,
    mappings: usize,
}

/// Overflow while composing prefix and halt owner mapping reports.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyPrefixHaltResidentWeightError {
    /// Mapped byte capacities overflowed host `usize`.
    MappedBytesOverflow,
    /// Live mapping counts overflowed host `usize`.
    MappingsOverflow,
}

/// Specialized failure from one reusable child owner in the five-step suffix.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyPrefixHaltOwnedFailureCause<RunnerError> {
    /// Final halt owner failed at suffix index four.
    Halt(Box<ExecutionGeometryNativeInitialHaltOwnedFailure<RunnerError>>),
    /// One of the four prefix owners failed at its exact prefix index.
    Prefix(Box<ExecutionGeometryNativeCrazyPrefixOwnedFailure<RunnerError>>),
}

/// Indexed reusable-suffix failure retaining the last committed checkpoint.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixHaltOwnedFailure<RunnerError> {
    cause: ExecutionGeometryNativeCrazyPrefixHaltOwnedFailureCause<RunnerError>,
    index: usize,
    state: ProfileMachineState,
}

/// Aggregate failed release ownership for prefix and halt child owners.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyPrefixHaltReleaseFailure<MemoryError> {
    halt_failure: Option<Box<ExecutableReleaseFailure<MemoryError>>>,
    prefix_failure: Option<
        Box<ExecutionGeometryNativeCrazyPrefixReleaseFailure<MemoryError>>,
    >,
}

/// Load failure retaining exact child rollback ownership.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyPrefixHaltLoadFailure<MemoryError> {
    /// Halt failed after the complete prefix was loaded.
    Halt {
        /// Exact halt executable load failure.
        error: Box<LoadFailure<MemoryError>>,
        /// Prefix cleanup still pending after halt-load rollback.
        prefix_release_failure: Option<
            Box<ExecutionGeometryNativeCrazyPrefixReleaseFailure<MemoryError>>,
        >,
    },
    /// The reusable four-crazy prefix failed to load.
    Prefix(Box<ExecutionGeometryNativeCrazyPrefixLoadFailure<MemoryError>>),
}

/// Reusable exact five-step suffix owner.
#[derive(Debug)]
pub struct LoadedExecutionGeometryNativeCrazyPrefixHaltSequence {
    halt: LoadedExecutionGeometryNativeInitialHalt,
    prefix: LoadedExecutionGeometryNativeCrazyPrefix,
    sequence: Box<ExecutionGeometryNativeCrazyPrefixHaltSequence>,
}

/// Result of loading all five suffix mappings or rolling back partial
/// ownership.
pub type GeometryNativeCrazyPrefixHaltLoadResult<MemoryError> = Result<
    LoadedExecutionGeometryNativeCrazyPrefixHaltSequence,
    Box<ExecutionGeometryNativeCrazyPrefixHaltLoadFailure<MemoryError>>,
>;

/// Result of executing one reusable five-step suffix owner.
pub type GeometryNativeCrazyPrefixHaltOwnedResult<RunnerError> = Result<
    ExecutionGeometryNativeCrazyPrefixHaltOutcome,
    Box<ExecutionGeometryNativeCrazyPrefixHaltOwnedFailure<RunnerError>>,
>;

/// Result of releasing every mapping retained by one five-step suffix owner.
pub type GeometryNativeCrazyPrefixHaltReleaseResult<MemoryError> = Result<
    (),
    Box<ExecutionGeometryNativeCrazyPrefixHaltReleaseFailure<MemoryError>>,
>;

impl Display for ExecutionGeometryNativeCrazyPrefixHaltResidentWeightError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::MappedBytesOverflow => f.write_str(
                "v5 crazy-prefix/halt mapped-byte weight overflowed",
            ),
            Self::MappingsOverflow => f.write_str(
                "v5 crazy-prefix/halt mapping-count weight overflowed",
            ),
        }
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeCrazyPrefixHaltOwnedFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v5 owned crazy-prefix/halt failed at {}: ", self.index)?;
        match &self.cause {
            OwnedCause::Halt(error) => Display::fmt(error, f),
            OwnedCause::Prefix(error) => Display::fmt(error, f),
        }
    }
}

impl<MemoryError: Display> Display
    for ExecutionGeometryNativeCrazyPrefixHaltLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Prefix(error) => Display::fmt(error, f),
            Self::Halt { error, .. } => {
                write!(f, "v5 crazy-prefix/halt load failed at 4: {error}")
            },
        }
    }
}

impl<MemoryError: Display> Display
    for ExecutionGeometryNativeCrazyPrefixHaltReleaseFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "v5 crazy-prefix/halt release incomplete ({} mappings)",
            self.failure_count()
        )
    }
}

impl<MemoryError>
    ExecutionGeometryNativeCrazyPrefixHaltLoadFailure<MemoryError>
{
    /// Reports whether primary or rollback cleanup remains pending.
    #[must_use]
    pub fn cleanup_pending(&self) -> bool {
        match self {
            Self::Prefix(error) => error.cleanup_pending(),
            Self::Halt {
                error,
                prefix_release_failure,
            } => error.cleanup_pending() || prefix_release_failure.is_some(),
        }
    }

    /// Returns the zero-based suffix index whose mapping failed to load.
    #[must_use]
    pub fn index(&self) -> usize {
        match self {
            Self::Prefix(error) => error.index(),
            Self::Halt { .. } => 4,
        }
    }

    /// Retries child rollback cleanup while preserving primary failure
    /// identity.
    #[must_use]
    pub fn retry_cleanup<Adapter>(self, adapter: &mut Adapter) -> Self
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        match self {
            Self::Prefix(error) => {
                Self::Prefix(Box::new((*error).retry_cleanup(adapter)))
            },
            Self::Halt {
                error,
                prefix_release_failure,
            } => Self::Halt {
                error: Box::new((*error).retry_cleanup(adapter)),
                prefix_release_failure: prefix_release_failure
                    .and_then(|failure| (*failure).retry(adapter).err()),
            },
        }
    }
}

impl<RunnerError>
    ExecutionGeometryNativeCrazyPrefixHaltOwnedFailure<RunnerError>
{
    /// Borrows the exact child-owner failure cause.
    #[must_use]
    pub const fn cause(
        &self,
    ) -> &ExecutionGeometryNativeCrazyPrefixHaltOwnedFailureCause<RunnerError>
    {
        &self.cause
    }

    /// Returns the zero-based global suffix index that failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Returns the last fully committed suffix checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl<MemoryError>
    ExecutionGeometryNativeCrazyPrefixHaltReleaseFailure<MemoryError>
{
    /// Returns the number of mappings whose cleanup remains pending.
    #[must_use]
    pub fn failure_count(&self) -> usize {
        self.prefix_failure
            .as_ref()
            .map_or(0, |failure| failure.failure_count())
            .saturating_add(usize::from(self.halt_failure.is_some()))
    }

    /// Retries all failed child releases and retains only remaining failures.
    ///
    /// # Errors
    ///
    /// Returns refreshed exact cleanup ownership while any mapping still fails.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeCrazyPrefixHaltReleaseResult<MemoryError>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        let prefix_failure = self
            .prefix_failure
            .and_then(|failure| (*failure).retry(adapter).err());
        let halt_failure = self
            .halt_failure
            .and_then(|failure| (*failure).retry(adapter).err().map(Box::new));
        release_result(Self {
            halt_failure,
            prefix_failure,
        })
    }
}

impl ExecutionGeometryNativeCrazyPrefixHaltResidentWeight {
    /// Returns exact mapped bytes retained by prefix plus halt.
    #[must_use]
    pub const fn mapped_bytes(self) -> usize {
        self.mapped_bytes
    }

    /// Returns exact live mapping count retained by prefix plus halt.
    #[must_use]
    pub const fn mappings(self) -> usize {
        self.mappings
    }
}

impl LoadedExecutionGeometryNativeCrazyPrefixHaltSequence {
    /// Executes all five retained mappings without executable-memory work.
    ///
    /// # Errors
    ///
    /// Returns exact global suffix index, last committed state, and specialized
    /// child-owner failure while preserving all mappings for reuse.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeCrazyPrefixHaltOwnedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeCrazyPrefixHaltOutcome as Outcome;

        let (memory, input, output) = buffers.into_parts();
        let prefix_outcome = self
            .prefix
            .execute(
                runner,
                NativeRegionBuffers::new(&mut *memory, input, &mut *output),
            )
            .map_err(|error| {
                let index = error.index();
                let state = error.state().clone();
                Box::new(ExecutionGeometryNativeCrazyPrefixHaltOwnedFailure {
                    cause: OwnedCause::Prefix(error),
                    index,
                    state,
                })
            })?;
        let prefix_state = prefix_outcome.state().clone();
        if let PrefixOutcome::GuardMiss { index, state } = prefix_outcome {
            return Ok(Outcome::GuardMiss { index, state });
        }
        let halt_completion = self
            .halt
            .execute(
                runner,
                NativeRegionBuffers::new(&mut *memory, input, &mut *output),
            )
            .map_err(|error| {
                Box::new(ExecutionGeometryNativeCrazyPrefixHaltOwnedFailure {
                    cause: OwnedCause::Halt(error),
                    index: 4,
                    state: prefix_state.clone(),
                })
            })?;
        let state = halt_completion.state().clone();
        if halt_completion.outcome() == NativeRegionInvocationOutcome::GuardMiss
        {
            Ok(Outcome::GuardMiss { index: 4, state })
        } else {
            Ok(Outcome::Completed(state))
        }
    }

    /// Loads prefix then halt, rolling the prefix back if halt loading fails.
    ///
    /// # Errors
    ///
    /// Returns exact child load and rollback evidence without publishing a
    /// partial five-step owner.
    pub fn load<Adapter>(
        sequence: &ExecutionGeometryNativeCrazyPrefixHaltSequence,
        adapter: &mut Adapter,
    ) -> GeometryNativeCrazyPrefixHaltLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let prefix = LoadedExecutionGeometryNativeCrazyPrefix::load(
            sequence.prefix(),
            adapter,
        )
        .map_err(|error| {
            Box::new(ExecutionGeometryNativeCrazyPrefixHaltLoadFailure::Prefix(
                error,
            ))
        })?;
        let halt = match sequence.halt().load_owned(adapter) {
            Ok(halt) => halt,
            Err(error) => {
                let prefix_release_failure = prefix.release(adapter).err();
                return Err(Box::new(
                    ExecutionGeometryNativeCrazyPrefixHaltLoadFailure::Halt {
                        error,
                        prefix_release_failure,
                    },
                ));
            },
        };
        Ok(Self {
            halt,
            prefix,
            sequence: Box::new(sequence.clone()),
        })
    }

    /// Releases prefix and halt, attempting both even after child failure.
    ///
    /// # Errors
    ///
    /// Returns exact retry ownership for every child mapping still unreleased.
    pub fn release<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeCrazyPrefixHaltReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let prefix_failure = self.prefix.release(adapter).err();
        let halt_failure = self.halt.release(adapter).err();
        release_result(ExecutionGeometryNativeCrazyPrefixHaltReleaseFailure {
            halt_failure,
            prefix_failure,
        })
    }

    /// Returns exact resident weight composed from prefix and halt reports.
    ///
    /// # Errors
    ///
    /// Returns overflow instead of publishing truncated aggregate weight.
    pub fn resident_weight(
        &self,
    ) -> Result<
        ExecutionGeometryNativeCrazyPrefixHaltResidentWeight,
        ExecutionGeometryNativeCrazyPrefixHaltResidentWeightError,
    > {
        let prefix = self
            .prefix
            .resident_weight()
            .map_err(map_prefix_weight_error)?;
        let halt = self.halt.resident_weight();
        let mapped_bytes = prefix
            .mapped_bytes()
            .checked_add(halt.mapped_bytes())
            .ok_or(WeightError::MappedBytesOverflow)?;
        let mappings = prefix
            .mappings()
            .checked_add(halt.mappings())
            .ok_or(WeightError::MappingsOverflow)?;
        Ok(ExecutionGeometryNativeCrazyPrefixHaltResidentWeight {
            mapped_bytes,
            mappings,
        })
    }

    /// Returns the exact admitted five-step sequence owned with the mappings.
    #[must_use]
    pub const fn sequence(
        &self,
    ) -> &ExecutionGeometryNativeCrazyPrefixHaltSequence {
        &self.sequence
    }
}

const fn map_prefix_weight_error(
    error: PrefixWeightError,
) -> ExecutionGeometryNativeCrazyPrefixHaltResidentWeightError {
    match error {
        PrefixWeightError::MappedBytesOverflow => {
            WeightError::MappedBytesOverflow
        },
        PrefixWeightError::MappingsOverflow => WeightError::MappingsOverflow,
    }
}

fn release_result<MemoryError>(
    failure: ExecutionGeometryNativeCrazyPrefixHaltReleaseFailure<MemoryError>,
) -> GeometryNativeCrazyPrefixHaltReleaseResult<MemoryError> {
    if failure.failure_count() == 0 {
        Ok(())
    } else {
        Err(Box::new(failure))
    }
}
