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
//   - Reusable seven-mapping ownership for the exact `j * p p p p v` theorem
//     sequence.
// - Must-Not:
//   - Generalize theorem length, publish partial loads, remap during execution,
//     or discard failed cleanup ownership.
// - Allows:
//   - Inputs: one admitted theorem sequence, memory adapter, runner, and
//     buffers.
//   - Outputs: reusable owner, exact theorem outcome, or indexed typed failure.
//   - Side effects: seven executable loads/releases; execution itself has none.
// - Split-When:
//   - Cache residency or eviction policy for the complete theorem owner
//     appears.
// - Merge-When:
//   - Generic fixed-sequence ownership preserves exact indexed rollback
//     evidence.
// - Summary:
//   - Owns, reuses, weighs, and releases all seven theorem mappings exactly.
// - Description:
//   - Composes existing one-step owners and prebinding without raw remapping.
// - Usage:
//   - Load once from an admitted sequence, execute repeatedly, then release.
// - Defaults:
//   - Load rollback and final release attempt every mapping whose owner exists.
//

//! Reusable seven-mapping ownership for the complete crazy theorem path.

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
use crate::geometry_native_crazy::{
    ExecutionGeometryNativeCrazyOwnedFailure,
    LoadedExecutionGeometryNativeCrazy,
};
use crate::geometry_native_initial_jump_data::{
    ExecutionGeometryNativeInitialJumpDataOwnedFailure,
    LoadedExecutionGeometryNativeInitialJumpData,
};
use crate::geometry_native_jump_rotate_crazy_halt_sequence::{
    ExecutionGeometryNativeJumpRotateCrazyHaltExecutableBindingError,
    ExecutionGeometryNativeJumpRotateCrazyHaltExecutables,
    ExecutionGeometryNativeJumpRotateCrazyHaltOutcome,
    ExecutionGeometryNativeJumpRotateCrazyHaltSequence,
};
use crate::geometry_native_rotate::{
    ExecutionGeometryNativeRotateOwnedFailure,
    LoadedExecutionGeometryNativeRotate,
};

type ExecutableReleaseFailure<MemoryError> =
    ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>;
type ReleaseFailureSlot<MemoryError> =
    Option<Box<ExecutableReleaseFailure<MemoryError>>>;
type CrazyReleaseFailures<MemoryError> = [ReleaseFailureSlot<MemoryError>; 4];
type LoadFailure<MemoryError> = NativeExecutableLoadFailure<MemoryError>;
type OwnedBindingError =
    ExecutionGeometryNativeJumpRotateCrazyHaltExecutableBindingError;
type OwnedCause<RunnerError> =
    ExecutionGeometryNativeJumpRotateCrazyHaltOwnedFailureCause<RunnerError>;
type WeightError =
    ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeightError;

/// Exact resident weight of one complete loaded theorem owner.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeight {
    mapped_bytes: usize,
    mappings: usize,
}

/// Overflow while summing the seven child-owner mapping reports.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeightError {
    /// Mapped byte capacities overflowed host `usize`.
    MappedBytesOverflow,
    /// Live mapping counts overflowed host `usize`.
    MappingsOverflow,
}

/// Primary loaded execution failure after all images were prevalidated.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpRotateCrazyHaltOwnedFailureCause<
    RunnerError,
> {
    /// Complete ready set failed exact prebinding before mutation.
    Binding(ExecutionGeometryNativeJumpRotateCrazyHaltExecutableBindingError),
    /// One crazy owner failed at its fixed zero-based prefix index.
    Crazy {
        /// Zero-based crazy index within the four-step prefix.
        index: usize,
        /// Exact one-step owner failure.
        error: Box<ExecutionGeometryNativeCrazyOwnedFailure<RunnerError>>,
    },
    /// Final halt owner failed.
    Halt(Box<ExecutionGeometryNativeInitialHaltOwnedFailure<RunnerError>>),
    /// Initial jump owner failed.
    InitialJump(
        Box<ExecutionGeometryNativeInitialJumpDataOwnedFailure<RunnerError>>,
    ),
    /// Rotate owner failed.
    Rotate(Box<ExecutionGeometryNativeRotateOwnedFailure<RunnerError>>),
}

/// Short public alias for the exact theorem-owner execution failure cause.
pub type CrazyTheoremOwnedCause<RunnerError> =
    ExecutionGeometryNativeJumpRotateCrazyHaltOwnedFailureCause<RunnerError>;

/// Indexed loaded execution failure retaining the last committed checkpoint.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpRotateCrazyHaltOwnedFailure<RunnerError> {
    cause: ExecutionGeometryNativeJumpRotateCrazyHaltOwnedFailureCause<
        RunnerError,
    >,
    index: usize,
    state: ProfileMachineState,
}

/// Aggregate failed release ownership for the seven fixed theorem mappings.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpRotateCrazyHaltReleaseFailure<MemoryError>
{
    crazy_failures: CrazyReleaseFailures<MemoryError>,
    halt_failure: ReleaseFailureSlot<MemoryError>,
    initial_jump_failure: ReleaseFailureSlot<MemoryError>,
    rotate_failure: ReleaseFailureSlot<MemoryError>,
}

/// Primary load failure plus rollback ownership for already-loaded mappings.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpRotateCrazyHaltLoadFailure<MemoryError> {
    error: Box<LoadFailure<MemoryError>>,
    index: usize,
    rollback_failure: Option<
        Box<
            ExecutionGeometryNativeJumpRotateCrazyHaltReleaseFailure<
                MemoryError,
            >,
        >,
    >,
}

/// Reusable complete theorem owner retaining all seven specialized child
/// owners.
#[derive(Debug)]
pub struct LoadedExecutionGeometryNativeJumpRotateCrazyHaltSequence {
    crazy: [LoadedExecutionGeometryNativeCrazy; 4],
    halt: LoadedExecutionGeometryNativeInitialHalt,
    initial_jump: LoadedExecutionGeometryNativeInitialJumpData,
    rotate: LoadedExecutionGeometryNativeRotate,
    sequence: Box<ExecutionGeometryNativeJumpRotateCrazyHaltSequence>,
}

/// Short public alias for the reusable complete theorem owner.
pub type LoadedCrazyTheoremSequence =
    LoadedExecutionGeometryNativeJumpRotateCrazyHaltSequence;

/// Result of loading all seven theorem mappings or rolling back partial loads.
pub type GeometryNativeJumpRotateCrazyHaltLoadResult<MemoryError> = Result<
    LoadedExecutionGeometryNativeJumpRotateCrazyHaltSequence,
    Box<ExecutionGeometryNativeJumpRotateCrazyHaltLoadFailure<MemoryError>>,
>;

/// Result of executing one reusable complete theorem owner.
pub type GeometryNativeJumpRotateCrazyHaltOwnedResult<RunnerError> = Result<
    ExecutionGeometryNativeJumpRotateCrazyHaltOutcome,
    Box<ExecutionGeometryNativeJumpRotateCrazyHaltOwnedFailure<RunnerError>>,
>;

/// Result of releasing every mapping retained by one complete theorem owner.
pub type GeometryNativeJumpRotateCrazyHaltReleaseResult<MemoryError> = Result<
    (),
    Box<ExecutionGeometryNativeJumpRotateCrazyHaltReleaseFailure<MemoryError>>,
>;

#[derive(Debug, Default)]
struct PartialLoadedTheoremPath {
    crazy: [Option<LoadedExecutionGeometryNativeCrazy>; 4],
    halt: Option<LoadedExecutionGeometryNativeInitialHalt>,
    initial_jump: Option<LoadedExecutionGeometryNativeInitialJumpData>,
    rotate: Option<LoadedExecutionGeometryNativeRotate>,
}

struct ExecutionProgress<'buffers> {
    input: &'buffers [u8],
    memory: &'buffers mut [u32],
    output: &'buffers mut [u8],
    state: ProfileMachineState,
}

#[derive(Debug)]
struct LoadedJumpRotate {
    initial_jump: LoadedExecutionGeometryNativeInitialJumpData,
    rotate: LoadedExecutionGeometryNativeRotate,
}

#[derive(Debug)]
struct LoadedJumpRotateCrazyPair {
    crazy0: LoadedExecutionGeometryNativeCrazy,
    crazy1: LoadedExecutionGeometryNativeCrazy,
    initial_jump: LoadedExecutionGeometryNativeInitialJumpData,
    rotate: LoadedExecutionGeometryNativeRotate,
}

#[derive(Debug)]
struct LoadedJumpRotateCrazyQuad {
    crazy: [LoadedExecutionGeometryNativeCrazy; 4],
    initial_jump: LoadedExecutionGeometryNativeInitialJumpData,
    rotate: LoadedExecutionGeometryNativeRotate,
}

impl Display for ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeightError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::MappedBytesOverflow => {
                f.write_str("v5 crazy theorem mapped-byte weight overflowed")
            },
            Self::MappingsOverflow => {
                f.write_str("v5 crazy theorem mapping-count weight overflowed")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeJumpRotateCrazyHaltOwnedFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v5 owned crazy theorem failed at {}: ", self.index)?;
        match &self.cause {
            OwnedCause::Binding(error) => Display::fmt(error, f),
            OwnedCause::Crazy { error, .. } => Display::fmt(error, f),
            OwnedCause::Halt(error) => Display::fmt(error, f),
            OwnedCause::InitialJump(error) => Display::fmt(error, f),
            OwnedCause::Rotate(error) => Display::fmt(error, f),
        }
    }
}

impl<MemoryError: Display> Display
    for ExecutionGeometryNativeJumpRotateCrazyHaltLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "v5 crazy theorem load failed at {}: {}",
            self.index, self.error
        )
    }
}

impl<MemoryError: Display> Display
    for ExecutionGeometryNativeJumpRotateCrazyHaltReleaseFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "v5 crazy theorem release incomplete ({} mappings)",
            self.failure_count()
        )
    }
}

impl<MemoryError>
    ExecutionGeometryNativeJumpRotateCrazyHaltLoadFailure<MemoryError>
{
    /// Reports whether primary load or rollback still owns cleanup work.
    #[must_use]
    pub fn cleanup_pending(&self) -> bool {
        self.error.cleanup_pending() || self.rollback_failure.is_some()
    }

    /// Returns the global theorem index whose mapping failed to load.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Retries primary/rollback cleanup while preserving primary load evidence.
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

impl<RunnerError>
    ExecutionGeometryNativeJumpRotateCrazyHaltOwnedFailure<RunnerError>
{
    /// Borrows exact stage failure ownership.
    #[must_use]
    pub const fn cause(&self) -> &OwnedCause<RunnerError> {
        &self.cause
    }

    /// Returns the zero-based global theorem step that failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Returns the last fully committed theorem checkpoint.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl<MemoryError>
    ExecutionGeometryNativeJumpRotateCrazyHaltReleaseFailure<MemoryError>
{
    /// Returns the number of mappings whose cleanup remains owned here.
    #[must_use]
    pub fn failure_count(&self) -> usize {
        let [crazy0, crazy1, crazy2, crazy3] = &self.crazy_failures;
        [
            crazy0.is_some(),
            crazy1.is_some(),
            crazy2.is_some(),
            crazy3.is_some(),
            self.halt_failure.is_some(),
            self.initial_jump_failure.is_some(),
            self.rotate_failure.is_some(),
        ]
        .into_iter()
        .filter(|pending| *pending)
        .count()
    }

    /// Retries every failed mapping release and retains only remaining
    /// failures.
    ///
    /// # Errors
    ///
    /// Returns refreshed exact cleanup ownership when any release still fails.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeJumpRotateCrazyHaltReleaseResult<MemoryError>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        let [crazy0, crazy1, crazy2, crazy3] = self.crazy_failures;
        release_result(Self {
            crazy_failures: [
                retry_release(crazy0, adapter),
                retry_release(crazy1, adapter),
                retry_release(crazy2, adapter),
                retry_release(crazy3, adapter),
            ],
            halt_failure: retry_release(self.halt_failure, adapter),
            initial_jump_failure: retry_release(
                self.initial_jump_failure,
                adapter,
            ),
            rotate_failure: retry_release(self.rotate_failure, adapter),
        })
    }
}

impl ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeight {
    /// Returns exact mapped bytes retained by all seven child owners.
    #[must_use]
    pub const fn mapped_bytes(self) -> usize {
        self.mapped_bytes
    }

    /// Returns exact live mapping count retained by all seven child owners.
    #[must_use]
    pub const fn mappings(self) -> usize {
        self.mappings
    }
}

impl LoadedExecutionGeometryNativeJumpRotateCrazyHaltSequence {
    const fn executables(
        &self,
    ) -> ExecutionGeometryNativeJumpRotateCrazyHaltExecutables<'_> {
        let [crazy0, crazy1, crazy2, crazy3] = &self.crazy;
        ExecutionGeometryNativeJumpRotateCrazyHaltExecutables::new(
            self.initial_jump.executable(),
            self.rotate.executable(),
            [
                crazy0.executable(),
                crazy1.executable(),
                crazy2.executable(),
                crazy3.executable(),
            ],
            self.halt.executable(),
        )
    }

    /// Executes all seven prebound owner mappings without adapter work.
    ///
    /// # Errors
    ///
    /// Returns exact global step, last committed state, and specialized owner
    /// failure while retaining all seven mappings for reuse.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeJumpRotateCrazyHaltOwnedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let _prebound =
            self.sequence.bind_executables(self.executables()).map_err(
                |error| owned_binding_failure(self.sequence.as_ref(), error),
            )?;
        self.execute_prebound(runner, buffers)
    }

    fn execute_after_jump<Runner>(
        &self,
        runner: &mut Runner,
        mut progress: ExecutionProgress<'_>,
    ) -> GeometryNativeJumpRotateCrazyHaltOwnedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeJumpRotateCrazyHaltOutcome as Outcome;

        let rotate_result = self.rotate.execute(runner, progress.buffers());
        let rotate_completion = rotate_result.map_err(|error| {
            owned_failure(OwnedCause::Rotate(error), 1, progress.state.clone())
        })?;
        progress.state = rotate_completion.state().clone();
        if rotate_completion.outcome()
            == NativeRegionInvocationOutcome::GuardMiss
        {
            return Ok(Outcome::GuardMiss {
                index: 1,
                state: progress.state,
            });
        }
        self.execute_suffix_owners(runner, progress)
    }

    fn execute_prebound<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> GeometryNativeJumpRotateCrazyHaltOwnedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeJumpRotateCrazyHaltOutcome as Outcome;

        let (memory, input, output) = buffers.into_parts();
        let mut progress = ExecutionProgress {
            input,
            memory,
            output,
            state: self.sequence.initial_jump().checkpoint().clone(),
        };
        let jump_result = self.initial_jump.execute(runner, progress.buffers());
        let jump_completion = jump_result.map_err(|error| {
            owned_failure(
                OwnedCause::InitialJump(error),
                0,
                progress.state.clone(),
            )
        })?;
        progress.state = jump_completion.state().clone();
        if jump_completion.outcome() == NativeRegionInvocationOutcome::GuardMiss
        {
            return Ok(Outcome::GuardMiss {
                index: 0,
                state: progress.state,
            });
        }
        self.execute_after_jump(runner, progress)
    }

    fn execute_suffix_owners<Runner>(
        &self,
        runner: &mut Runner,
        mut progress: ExecutionProgress<'_>,
    ) -> GeometryNativeJumpRotateCrazyHaltOwnedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeJumpRotateCrazyHaltOutcome as Outcome;

        for (crazy_index, crazy) in self.crazy.iter().enumerate() {
            let global_index = crazy_index.saturating_add(2);
            let completion =
                crazy.execute(runner, progress.buffers()).map_err(|error| {
                    owned_failure(
                        OwnedCause::Crazy {
                            error,
                            index: crazy_index,
                        },
                        global_index,
                        progress.state.clone(),
                    )
                })?;
            progress.state = completion.state().clone();
            if completion.outcome() == NativeRegionInvocationOutcome::GuardMiss
            {
                return Ok(Outcome::GuardMiss {
                    index: global_index,
                    state: progress.state,
                });
            }
        }
        let halt_completion = self
            .halt
            .execute(runner, progress.buffers())
            .map_err(|error| {
                owned_failure(
                    OwnedCause::Halt(error),
                    6,
                    progress.state.clone(),
                )
            })?;
        let final_state = halt_completion.state().clone();
        if halt_completion.outcome() == NativeRegionInvocationOutcome::GuardMiss
        {
            Ok(Outcome::GuardMiss {
                index: 6,
                state: final_state,
            })
        } else {
            Ok(Outcome::Completed(final_state))
        }
    }

    /// Loads all seven exact theorem mappings and rolls back partial ownership.
    ///
    /// # Errors
    ///
    /// Returns global failing index, primary load evidence, and any rollback
    /// cleanup tokens from already-loaded child owners.
    pub fn load<Adapter>(
        sequence: &ExecutionGeometryNativeJumpRotateCrazyHaltSequence,
        adapter: &mut Adapter,
    ) -> GeometryNativeJumpRotateCrazyHaltLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let initial_jump = sequence
            .initial_jump()
            .load_owned(adapter)
            .map_err(|error| Box::new(load_failure(0, error, None)))?;
        let rotate = match sequence.rotate().load_owned(adapter) {
            Ok(owner) => owner,
            Err(error) => {
                let rollback = PartialLoadedTheoremPath {
                    initial_jump: Some(initial_jump),
                    ..PartialLoadedTheoremPath::default()
                }
                .release(adapter)
                .err();
                return Err(Box::new(load_failure(1, error, rollback)));
            },
        };
        let prefix = LoadedJumpRotate { initial_jump, rotate };
        Self::load_after_rotate(sequence, adapter, prefix)
    }

    fn load_after_rotate<Adapter>(
        sequence: &ExecutionGeometryNativeJumpRotateCrazyHaltSequence,
        adapter: &mut Adapter,
        prefix: LoadedJumpRotate,
    ) -> GeometryNativeJumpRotateCrazyHaltLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let [crazy0_plan, crazy1_plan, ..] = sequence.suffix().prefix().steps();
        let crazy0 = match crazy0_plan.load_owned(adapter) {
            Ok(owner) => owner,
            Err(error) => {
                let rollback = PartialLoadedTheoremPath {
                    initial_jump: Some(prefix.initial_jump),
                    rotate: Some(prefix.rotate),
                    ..PartialLoadedTheoremPath::default()
                }
                .release(adapter)
                .err();
                return Err(Box::new(load_failure(2, error, rollback)));
            },
        };
        let crazy1 = match crazy1_plan.load_owned(adapter) {
            Ok(owner) => owner,
            Err(error) => {
                let rollback = PartialLoadedTheoremPath {
                    crazy: [Some(crazy0), None, None, None],
                    initial_jump: Some(prefix.initial_jump),
                    rotate: Some(prefix.rotate),
                    ..PartialLoadedTheoremPath::default()
                }
                .release(adapter)
                .err();
                return Err(Box::new(load_failure(3, error, rollback)));
            },
        };
        let crazy_pair = LoadedJumpRotateCrazyPair {
            crazy0,
            crazy1,
            initial_jump: prefix.initial_jump,
            rotate: prefix.rotate,
        };
        Self::load_tail(sequence, adapter, crazy_pair)
    }

    fn load_halt<Adapter>(
        sequence: &ExecutionGeometryNativeJumpRotateCrazyHaltSequence,
        adapter: &mut Adapter,
        loaded: LoadedJumpRotateCrazyQuad,
    ) -> GeometryNativeJumpRotateCrazyHaltLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let halt = match sequence.suffix().halt().load_owned(adapter) {
            Ok(owner) => owner,
            Err(error) => {
                let rollback = PartialLoadedTheoremPath {
                    crazy: loaded.crazy.map(Some),
                    initial_jump: Some(loaded.initial_jump),
                    rotate: Some(loaded.rotate),
                    ..PartialLoadedTheoremPath::default()
                }
                .release(adapter)
                .err();
                return Err(Box::new(load_failure(6, error, rollback)));
            },
        };
        Ok(Self {
            crazy: loaded.crazy,
            halt,
            initial_jump: loaded.initial_jump,
            rotate: loaded.rotate,
            sequence: Box::new(sequence.clone()),
        })
    }

    fn load_tail<Adapter>(
        sequence: &ExecutionGeometryNativeJumpRotateCrazyHaltSequence,
        adapter: &mut Adapter,
        loaded: LoadedJumpRotateCrazyPair,
    ) -> GeometryNativeJumpRotateCrazyHaltLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let [_, _, crazy2_plan, crazy3_plan] =
            sequence.suffix().prefix().steps();
        let crazy2 = match crazy2_plan.load_owned(adapter) {
            Ok(owner) => owner,
            Err(error) => {
                let rollback = PartialLoadedTheoremPath {
                    crazy: [
                        Some(loaded.crazy0),
                        Some(loaded.crazy1),
                        None,
                        None,
                    ],
                    initial_jump: Some(loaded.initial_jump),
                    rotate: Some(loaded.rotate),
                    ..PartialLoadedTheoremPath::default()
                }
                .release(adapter)
                .err();
                return Err(Box::new(load_failure(4, error, rollback)));
            },
        };
        let crazy3 = match crazy3_plan.load_owned(adapter) {
            Ok(owner) => owner,
            Err(error) => {
                let rollback = PartialLoadedTheoremPath {
                    crazy: [
                        Some(loaded.crazy0),
                        Some(loaded.crazy1),
                        Some(crazy2),
                        None,
                    ],
                    initial_jump: Some(loaded.initial_jump),
                    rotate: Some(loaded.rotate),
                    ..PartialLoadedTheoremPath::default()
                }
                .release(adapter)
                .err();
                return Err(Box::new(load_failure(5, error, rollback)));
            },
        };
        let crazy_quad = LoadedJumpRotateCrazyQuad {
            crazy: [loaded.crazy0, loaded.crazy1, crazy2, crazy3],
            initial_jump: loaded.initial_jump,
            rotate: loaded.rotate,
        };
        Self::load_halt(sequence, adapter, crazy_quad)
    }

    /// Releases all seven mappings and returns every failed cleanup token.
    ///
    /// # Errors
    ///
    /// Attempts every mapping even after failure and returns aggregate retry
    /// ownership for exactly the mappings whose release remains incomplete.
    pub fn release<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeJumpRotateCrazyHaltReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let Self {
            crazy,
            halt,
            initial_jump,
            rotate,
            sequence: _sequence,
        } = self;
        PartialLoadedTheoremPath {
            crazy: crazy.map(Some),
            halt: Some(halt),
            initial_jump: Some(initial_jump),
            rotate: Some(rotate),
        }
        .release(adapter)
    }

    /// Returns exact resident weight composed from all seven child owners.
    ///
    /// # Errors
    ///
    /// Returns overflow rather than publishing truncated bytes or mapping
    /// count.
    pub fn resident_weight(
        &self,
    ) -> Result<
        ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeight,
        ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeightError,
    > {
        let [crazy0, crazy1, crazy2, crazy3] = &self.crazy;
        let mapped_bytes = [
            self.initial_jump.resident_weight().mapped_bytes(),
            self.rotate.resident_weight().mapped_bytes(),
            crazy0.resident_weight().mapped_bytes(),
            crazy1.resident_weight().mapped_bytes(),
            crazy2.resident_weight().mapped_bytes(),
            crazy3.resident_weight().mapped_bytes(),
            self.halt.resident_weight().mapped_bytes(),
        ]
        .into_iter()
        .try_fold(0usize, usize::checked_add)
        .ok_or(WeightError::MappedBytesOverflow)?;
        let mappings = [
            self.initial_jump.resident_weight().mappings(),
            self.rotate.resident_weight().mappings(),
            crazy0.resident_weight().mappings(),
            crazy1.resident_weight().mappings(),
            crazy2.resident_weight().mappings(),
            crazy3.resident_weight().mappings(),
            self.halt.resident_weight().mappings(),
        ]
        .into_iter()
        .try_fold(0usize, usize::checked_add)
        .ok_or(WeightError::MappingsOverflow)?;
        Ok(ExecutionGeometryNativeJumpRotateCrazyHaltResidentWeight {
            mapped_bytes,
            mappings,
        })
    }

    /// Returns the exact admitted theorem sequence owned beside the mappings.
    #[must_use]
    pub const fn sequence(
        &self,
    ) -> &ExecutionGeometryNativeJumpRotateCrazyHaltSequence {
        &self.sequence
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

impl PartialLoadedTheoremPath {
    fn release<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeJumpRotateCrazyHaltReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let [crazy0, crazy1, crazy2, crazy3] = self.crazy;
        release_result(
            ExecutionGeometryNativeJumpRotateCrazyHaltReleaseFailure {
                crazy_failures: [
                    release_crazy(crazy0, adapter),
                    release_crazy(crazy1, adapter),
                    release_crazy(crazy2, adapter),
                    release_crazy(crazy3, adapter),
                ],
                halt_failure: self
                    .halt
                    .and_then(|loaded| loaded.release(adapter).err()),
                initial_jump_failure: self
                    .initial_jump
                    .and_then(|loaded| loaded.release(adapter).err()),
                rotate_failure: self
                    .rotate
                    .and_then(|loaded| loaded.release(adapter).err()),
            },
        )
    }
}

const fn load_failure<MemoryError>(
    index: usize,
    error: Box<LoadFailure<MemoryError>>,
    rollback_failure: Option<
        Box<
            ExecutionGeometryNativeJumpRotateCrazyHaltReleaseFailure<
                MemoryError,
            >,
        >,
    >,
) -> ExecutionGeometryNativeJumpRotateCrazyHaltLoadFailure<MemoryError> {
    ExecutionGeometryNativeJumpRotateCrazyHaltLoadFailure {
        error,
        index,
        rollback_failure,
    }
}

fn owned_binding_failure<RunnerError>(
    sequence: &ExecutionGeometryNativeJumpRotateCrazyHaltSequence,
    error: OwnedBindingError,
) -> Box<ExecutionGeometryNativeJumpRotateCrazyHaltOwnedFailure<RunnerError>> {
    let index = match error {
        OwnedBindingError::InitialJump => 0,
        OwnedBindingError::Rotate => 1,
        OwnedBindingError::Crazy { index } => index.saturating_add(2),
        OwnedBindingError::Halt => 6,
    };
    owned_failure(
        OwnedCause::Binding(error),
        index,
        sequence.initial_jump().checkpoint().clone(),
    )
}

fn owned_failure<RunnerError>(
    cause: OwnedCause<RunnerError>,
    index: usize,
    state: ProfileMachineState,
) -> Box<ExecutionGeometryNativeJumpRotateCrazyHaltOwnedFailure<RunnerError>> {
    Box::new(ExecutionGeometryNativeJumpRotateCrazyHaltOwnedFailure {
        cause,
        index,
        state,
    })
}

fn release_crazy<Adapter>(
    owner: Option<LoadedExecutionGeometryNativeCrazy>,
    adapter: &mut Adapter,
) -> ReleaseFailureSlot<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    owner.and_then(|crazy| crazy.release(adapter).err())
}

fn retry_release<Adapter>(
    pending: ReleaseFailureSlot<Adapter::Error>,
    adapter: &mut Adapter,
) -> ReleaseFailureSlot<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    pending.and_then(|release_failure| {
        (*release_failure).retry(adapter).err().map(Box::new)
    })
}

fn release_result<MemoryError>(
    failure: ExecutionGeometryNativeJumpRotateCrazyHaltReleaseFailure<
        MemoryError,
    >,
) -> GeometryNativeJumpRotateCrazyHaltReleaseResult<MemoryError> {
    if failure.failure_count() == 0 {
        Ok(())
    } else {
        Err(Box::new(failure))
    }
}
