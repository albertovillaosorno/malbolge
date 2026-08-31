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
//   - Checkpoint-bound semantic admission and load-image authority for v5
//     crazy.
// - Must-Not:
//   - Map executable memory, prepare ABI buffers, invoke native code, or cache.
// - Allows:
//   - Inputs: exact v5 crazy IR, verified artifact, and opaque checkpoint.
//   - Outputs: normatively replayed crazy admission and relocation-free image.
//   - Side effects: none.
// - Split-When:
//   - Crazy invocation or reusable residency gains independent lifecycle
//     policy.
// - Merge-When:
//   - One reviewed geometry-native operation framework preserves equal proofs.
// - Summary:
//   - Admits v5 crazy only after exact checkpoint replay.
// - Description:
//   - Binds crazy artifact identity to opaque geometry and replayed exit state.
// - Usage:
//   - Construct before any future mapping or invocation boundary.
// - Defaults:
//   - Checkpoint, replay, identity, artifact, or load-image drift fails closed.
//

//! Checkpoint-bound semantic admission for explicit-geometry crazy.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use malbolge::{ExecutionGeometryRegionEffectProgram, ProfileMachineState};

use crate::execution_cache::{NativeArtifactKey, NativeIdentityError};
use crate::execution_native::{
    ExecutionGeometryNativeExecutableReleaseFailure,
    ExecutionGeometryNativeRunner, NativeExecutableLoadFailure,
    NativeExecutableMemoryAdapter, NativeRegionBuffers,
    NativeRegionInvocationError, NativeRegionInvocationOutcome,
    PreparedExecutionGeometryNativeInvocation, PreparedNativeRegionInvocation,
    ReadyExecutionGeometryNativeExecutable, VerifiedDirectLoadError,
    VerifiedExecutionGeometryCrazyNativeObjectArtifact,
    VerifiedExecutionGeometryLoadImage,
    load_execution_geometry_native_executable,
    release_execution_geometry_native_executable,
};
use crate::geometry_interpreter_handoff::{
    ExecutionGeometryHandoffAdmissionError,
    ExecutionGeometryHandoffExecutionCause,
    ExecutionGeometryInterpreterHandoff,
};

type CrazyBindingError = ExecutionGeometryNativeCrazyBindingError;

/// Failure before one verified v5 crazy can retain checkpoint authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyAdmissionError {
    /// Verified artifact identity differs from the exact requested v5 program.
    ArtifactIdentity,
    /// Opaque checkpoint authority disagrees with the requested v5 program.
    Checkpoint(ExecutionGeometryHandoffAdmissionError),
    /// Exact v5 native identity could not be reconstructed.
    Identity(NativeIdentityError),
    /// Verified COFF could not become one relocation-free aligned load image.
    Load(VerifiedDirectLoadError),
    /// Normative one-step replay disagreed with the supplied v5 program.
    NormativeReplay(ExecutionGeometryHandoffExecutionCause),
}

/// Failure while binding one prepared v5 crazy to synchronized code.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyBindingError {
    /// Synchronized executable image differs from checkpoint-bound admission.
    ExecutableIdentity,
}

/// Failure while admitting one completed v5 crazy ABI transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyCompletionError {
    /// Native result disagreed with the exact prepared transition.
    Invocation(NativeRegionInvocationError),
}

/// Failure after a checkpoint-bound v5 crazy enters the runner.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyExecutionError<RunnerError> {
    /// Returned status or caller-visible state failed exact completion.
    Completion(ExecutionGeometryNativeCrazyCompletionError),
    /// External runner failed before returning a raw ABI status.
    Runner(Box<RunnerError>),
}

/// Failure while executing one reusable owned crazy mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyOwnedFailure<RunnerError> {
    /// Prepared caller buffers could not bind to the retained ready mapping.
    Binding(ExecutionGeometryNativeCrazyBindingError),
    /// Bound runner/completion admission failed.
    Execution(Box<ExecutionGeometryNativeCrazyExecutionError<RunnerError>>),
    /// Caller buffers drifted from the admitted entry checkpoint.
    Preparation(ExecutionGeometryNativeCrazyPreparationError),
}

/// Result of one dedicated checkpoint-bound v5 crazy runner call.
pub type ExecutionGeometryNativeCrazyExecutionResult<RunnerError> = Result<
    ExecutionGeometryNativeCrazyCompletion,
    Box<ExecutionGeometryNativeCrazyExecutionError<RunnerError>>,
>;

/// Result of executing one reusable owned crazy mapping.
pub type ExecutionGeometryNativeCrazyOwnedResult<RunnerError> = Result<
    ExecutionGeometryNativeCrazyCompletion,
    Box<ExecutionGeometryNativeCrazyOwnedFailure<RunnerError>>,
>;

/// Failure while preparing checkpoint-exact buffers for v5 crazy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyPreparationError {
    /// Borrowed input bytes differ from the admitted checkpoint.
    Input,
    /// Native ABI preparation rejected the exact v5 crazy contract.
    Invocation(NativeRegionInvocationError),
    /// Borrowed memory differs from the admitted checkpoint.
    Memory,
    /// Borrowed output bytes differ from the admitted checkpoint.
    Output,
}

/// Failure from complete v5 crazy load/call/admit/release composition.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeCrazyTransactionFailure<
    MemoryError,
    RunnerError,
> {
    /// Exact prepared call could not bind to the loaded v5 executable.
    Binding {
        /// Exact binding rejection.
        error: ExecutionGeometryNativeCrazyBindingError,
        /// Failed cleanup retaining the ready mapping when release also
        /// failed.
        release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// Bound v5 runner or completion admission failed.
    Execution {
        /// Exact runner/completion failure.
        error: Box<ExecutionGeometryNativeCrazyExecutionError<RunnerError>>,
        /// Failed cleanup retaining the ready mapping when release also
        /// failed.
        release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// Executable mapping/lifecycle failed before runner entry.
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    /// Checkpoint-exact caller buffers failed preparation before mapping.
    Preparation(ExecutionGeometryNativeCrazyPreparationError),
    /// Completion committed, but final mapping release failed.
    Release {
        /// Exact committed checkpoint/outcome retained despite cleanup
        /// failure.
        completion: Box<ExecutionGeometryNativeCrazyCompletion>,
        /// Retryable ready executable and platform release error.
        release_failure:
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    },
}

/// Result of one complete guarded crazy transaction for adapter ports.
pub type ExecutionGeometryNativeCrazyAdapterTransactionResult<
    MemoryAdapter,
    Runner,
> = ExecutionGeometryNativeCrazyTransactionResult<
    <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
    <Runner as ExecutionGeometryNativeRunner>::Error,
>;

/// Result of one complete guarded v5 crazy transaction.
pub type ExecutionGeometryNativeCrazyTransactionResult<
    MemoryError,
    RunnerError,
> = Result<
    ExecutionGeometryNativeCrazyCompletion,
    Box<
        ExecutionGeometryNativeCrazyTransactionFailure<
            MemoryError,
            RunnerError,
        >,
    >,
>;

/// Result of loading one reusable exact crazy mapping.
pub type GeometryNativeCrazyOwnedLoadResult<MemoryError> = Result<
    LoadedExecutionGeometryNativeCrazy,
    Box<NativeExecutableLoadFailure<MemoryError>>,
>;

/// Result of releasing one reusable exact crazy mapping.
pub type GeometryNativeCrazyOwnedReleaseResult<MemoryError> = Result<
    (),
    Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
>;

/// Verified v5 crazy bound to one opaque checkpoint and normative exit.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyAdmission {
    artifact: VerifiedExecutionGeometryCrazyNativeObjectArtifact,
    checkpoint: ProfileMachineState,
    expected_state: ProfileMachineState,
    load_image: VerifiedExecutionGeometryLoadImage,
    program: ExecutionGeometryRegionEffectProgram,
}

/// Exact synchronized mapping weight retained by one owned crazy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyResidentWeight {
    mapped_bytes: usize,
    mappings: usize,
}

/// One reusable ready crazy mapping beside exact admission.
#[derive(Debug)]
pub struct LoadedExecutionGeometryNativeCrazy {
    admission: Box<ExecutionGeometryNativeCrazyAdmission>,
    executable: ReadyExecutionGeometryNativeExecutable,
}

/// Prepared checkpoint-owned crazy bound to exact synchronized v5 code.
#[derive(Debug)]
pub struct ExecutionGeometryNativeCrazyBoundCall<
    'admission,
    'buffers,
    'executable,
> {
    executable: &'executable ReadyExecutionGeometryNativeExecutable,
    prepared: PreparedExecutionGeometryNativeCrazy<'admission, 'buffers>,
}

/// One admitted crazy result retaining opaque geometry authority.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeCrazyCompletion {
    outcome: NativeRegionInvocationOutcome,
    state: ProfileMachineState,
}

/// Borrow-scoped crazy ABI contract retaining checkpoint admission.
#[derive(Debug)]
pub struct PreparedExecutionGeometryNativeCrazy<'admission, 'buffers> {
    admission: &'admission ExecutionGeometryNativeCrazyAdmission,
    invocation: PreparedNativeRegionInvocation<'buffers>,
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeCrazyOwnedFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Binding(error) => Display::fmt(error, f),
            Self::Execution(error) => Display::fmt(error, f),
            Self::Preparation(error) => Display::fmt(error, f),
        }
    }
}

impl Display for ExecutionGeometryNativeCrazyAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => {
                f.write_str("verified v5 crazy artifact identity drifted")
            },
            Self::Checkpoint(error) => Display::fmt(error, f),
            Self::Identity(_error) => {
                f.write_str("v5 crazy identity reconstruction failed")
            },
            Self::Load(error) => Display::fmt(error, f),
            Self::NormativeReplay(error) => Display::fmt(error, f),
        }
    }
}

impl Display for ExecutionGeometryNativeCrazyBindingError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("v5 crazy executable identity differs from call")
    }
}

impl Display for ExecutionGeometryNativeCrazyCompletionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Invocation(error) => Display::fmt(error, f),
        }
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeCrazyExecutionError<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Completion(error) => Display::fmt(error, f),
            Self::Runner(error) => write!(f, "v5 crazy runner failed: {error}"),
        }
    }
}

impl Display for ExecutionGeometryNativeCrazyPreparationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Input => {
                f.write_str("v5 crazy input differs from checkpoint")
            },
            Self::Invocation(error) => Display::fmt(error, f),
            Self::Memory => {
                f.write_str("v5 crazy memory differs from checkpoint")
            },
            Self::Output => {
                f.write_str("v5 crazy output differs from checkpoint")
            },
        }
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for ExecutionGeometryNativeCrazyTransactionFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Binding { error, .. } => {
                write!(f, "v5 crazy transaction binding failed: {error}")
            },
            Self::Execution { error, .. } => {
                write!(f, "v5 crazy transaction execution failed: {error}")
            },
            Self::Load(error) => {
                write!(f, "v5 crazy transaction load failed: {error}")
            },
            Self::Preparation(error) => {
                write!(f, "v5 crazy transaction preparation failed: {error}")
            },
            Self::Release { release_failure, .. } => {
                write!(f, "v5 crazy transaction {release_failure}")
            },
        }
    }
}

impl ExecutionGeometryNativeCrazyAdmission {
    /// Returns the exact verified v5 crazy artifact retained by admission.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedExecutionGeometryCrazyNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the normative entry checkpoint carrying opaque geometry
    /// authority.
    #[must_use]
    pub const fn checkpoint(&self) -> &ProfileMachineState {
        &self.checkpoint
    }

    /// Loads, binds, runs, admits, and releases one guarded v5 crazy.
    ///
    /// Preparation occurs before mapping. Every failure after a ready mapping
    /// exists attempts exact release, while cleanup failure retains the ready
    /// executable for retry. A post-commit cleanup failure also retains the
    /// normatively proven opaque-geometry completion.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeCrazyTransactionFailure`] with exact
    /// primary failure and any retryable cleanup ownership.
    pub fn execute_transactionally<MemoryAdapter, Runner>(
        &self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeCrazyAdapterTransactionResult<
        MemoryAdapter,
        Runner,
    >
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeCrazyTransactionFailure as Failure;

        let prepared = self
            .prepare(buffers)
            .map_err(|error| Box::new(Failure::Preparation(error)))?;
        let ready = match load_execution_geometry_native_executable(
            memory_adapter,
            self.load_image(),
        ) {
            Ok(ready) => ready,
            Err(error) => {
                prepared.abort();
                return Err(Box::new(Failure::Load(Box::new(error))));
            },
        };
        let bound = match prepared.bind_executable(&ready) {
            Ok(bound) => bound,
            Err(error) => {
                let release_failure =
                    release_execution_geometry_native_executable(
                        memory_adapter,
                        ready,
                    )
                    .err()
                    .map(Box::new);
                return Err(Box::new(Failure::Binding {
                    error,
                    release_failure,
                }));
            },
        };
        let completion = match bound.execute(runner) {
            Ok(completion) => completion,
            Err(error) => {
                let release_failure =
                    release_execution_geometry_native_executable(
                        memory_adapter,
                        ready,
                    )
                    .err()
                    .map(Box::new);
                return Err(Box::new(Failure::Execution {
                    error,
                    release_failure,
                }));
            },
        };
        match release_execution_geometry_native_executable(
            memory_adapter,
            ready,
        ) {
            Ok(()) => Ok(completion),
            Err(release_failure) => Err(Box::new(Failure::Release {
                completion: Box::new(completion),
                release_failure: Box::new(release_failure),
            })),
        }
    }

    /// Returns the exact normative state accepted by future Applied execution.
    #[must_use]
    pub const fn expected_state(&self) -> &ProfileMachineState {
        &self.expected_state
    }

    /// Returns the relocation-free load image retaining exact v5 identity.
    #[must_use]
    pub const fn load_image(&self) -> &VerifiedExecutionGeometryLoadImage {
        &self.load_image
    }

    /// Loads and retains one reusable synchronized crazy mapping.
    ///
    /// # Errors
    ///
    /// Returns the exact native executable load failure without publishing a
    /// partial owner.
    pub fn load_owned<Adapter>(
        &self,
        adapter: &mut Adapter,
    ) -> GeometryNativeCrazyOwnedLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let executable = load_execution_geometry_native_executable(
            adapter,
            self.load_image(),
        )
        .map_err(Box::new)?;
        Ok(LoadedExecutionGeometryNativeCrazy {
            admission: Box::new(self.clone()),
            executable,
        })
    }

    /// Binds verified crazy evidence to a normatively replayed checkpoint.
    ///
    /// Admission first checks opaque geometry/effect continuity through the
    /// interpreter handoff. Only after exact replay succeeds does it rebuild
    /// native identity and extract a relocation-free code image.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeCrazyAdmissionError`] for checkpoint,
    /// replay, identity, artifact, or load-image disagreement.
    pub fn new(
        program: ExecutionGeometryRegionEffectProgram,
        checkpoint: ProfileMachineState,
        artifact: VerifiedExecutionGeometryCrazyNativeObjectArtifact,
    ) -> Result<Self, ExecutionGeometryNativeCrazyAdmissionError> {
        let replay = ExecutionGeometryInterpreterHandoff::new(
            program.clone(),
            checkpoint.clone(),
        )
        .map_err(ExecutionGeometryNativeCrazyAdmissionError::Checkpoint)?;
        let completion = replay.execute().map_err(|failure| {
            ExecutionGeometryNativeCrazyAdmissionError::NormativeReplay(
                failure.cause(),
            )
        })?;
        let expected_key = NativeArtifactKey::new_execution_geometry(
            &program,
            artifact.key().target().clone(),
        )
        .map_err(ExecutionGeometryNativeCrazyAdmissionError::Identity)?;
        if artifact.key() != &expected_key {
            return Err(
                ExecutionGeometryNativeCrazyAdmissionError::ArtifactIdentity,
            );
        }
        let load_image =
            VerifiedExecutionGeometryLoadImage::from_crazy(&artifact)
                .map_err(ExecutionGeometryNativeCrazyAdmissionError::Load)?;
        Ok(Self {
            artifact,
            checkpoint,
            expected_state: completion.state().clone(),
            load_image,
            program,
        })
    }

    /// Prepares exact checkpoint-owned buffers for guarded v5 crazy.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeCrazyPreparationError`] when any caller
    /// buffer drifts or ABI preparation rejects the exact crazy effect.
    pub fn prepare<'admission, 'buffers>(
        &'admission self,
        buffers: NativeRegionBuffers<'buffers>,
    ) -> Result<
        PreparedExecutionGeometryNativeCrazy<'admission, 'buffers>,
        ExecutionGeometryNativeCrazyPreparationError,
    > {
        let (memory, input, output) = buffers.into_parts();
        if input != self.checkpoint.io().input() {
            return Err(ExecutionGeometryNativeCrazyPreparationError::Input);
        }
        if memory != self.checkpoint.memory() {
            return Err(ExecutionGeometryNativeCrazyPreparationError::Memory);
        }
        if output != self.checkpoint.io().output() {
            return Err(ExecutionGeometryNativeCrazyPreparationError::Output);
        }
        let invocation =
            PreparedNativeRegionInvocation::new_execution_geometry_crazy(
                &self.program,
                memory,
                input,
                output,
            )
            .map_err(
                ExecutionGeometryNativeCrazyPreparationError::Invocation,
            )?;
        Ok(PreparedExecutionGeometryNativeCrazy {
            admission: self,
            invocation,
        })
    }

    /// Returns the exact v5 crazy IR retained by admission.
    #[must_use]
    pub const fn program(&self) -> &ExecutionGeometryRegionEffectProgram {
        &self.program
    }
}
impl ExecutionGeometryNativeCrazyResidentWeight {
    /// Returns exact synchronized mapped bytes retained by this owner.
    #[must_use]
    pub const fn mapped_bytes(self) -> usize {
        self.mapped_bytes
    }

    /// Returns the exact number of live executable mappings.
    #[must_use]
    pub const fn mappings(self) -> usize {
        self.mappings
    }
}

impl LoadedExecutionGeometryNativeCrazy {
    /// Returns the exact admission retained beside the ready mapping.
    #[must_use]
    pub const fn admission(&self) -> &ExecutionGeometryNativeCrazyAdmission {
        &self.admission
    }

    /// Returns the retained synchronized executable mapping.
    #[must_use]
    pub const fn executable(&self) -> &ReadyExecutionGeometryNativeExecutable {
        &self.executable
    }

    /// Executes the retained mapping without executable-memory adapter work.
    ///
    /// # Errors
    ///
    /// Returns exact preparation, binding, runner, or completion failure while
    /// retaining this reusable mapping.
    pub fn execute<Runner>(
        &self,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeCrazyOwnedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let prepared = self.admission.prepare(buffers).map_err(|error| {
            Box::new(ExecutionGeometryNativeCrazyOwnedFailure::Preparation(
                error,
            ))
        })?;
        let bound =
            prepared
                .bind_executable(&self.executable)
                .map_err(|error| {
                    Box::new(ExecutionGeometryNativeCrazyOwnedFailure::Binding(
                        error,
                    ))
                })?;
        bound.execute(runner).map_err(|error| {
            Box::new(ExecutionGeometryNativeCrazyOwnedFailure::Execution(error))
        })
    }

    /// Releases the exact retained ready mapping.
    ///
    /// # Errors
    ///
    /// Returns retryable ready-executable ownership when platform release
    /// fails.
    pub fn release<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> GeometryNativeCrazyOwnedReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        release_execution_geometry_native_executable(adapter, self.executable)
            .map_err(Box::new)
    }

    /// Returns exact synchronized mapping weight reported by the adapter.
    #[must_use]
    pub const fn resident_weight(
        &self,
    ) -> ExecutionGeometryNativeCrazyResidentWeight {
        ExecutionGeometryNativeCrazyResidentWeight {
            mapped_bytes: self.executable.mapping().mapped_len(),
            mappings: 1,
        }
    }
}

impl ExecutionGeometryNativeCrazyBoundCall<'_, '_, '_> {
    /// Simulates the exact expected foreign transition for contract tests.
    #[cfg(test)]
    #[doc(hidden)]
    pub fn apply_expected_for_test(&mut self) {
        self.prepared.apply_expected_for_test();
    }

    /// Admits one raw status without invoking machine code.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeCrazyCompletionError`] when the
    /// completed transition violates exact prepared evidence.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeCrazyCompletion,
        ExecutionGeometryNativeCrazyCompletionError,
    > {
        self.prepared.complete(raw_status)
    }

    /// Returns the synchronized entrypoint retained by exact identity binding.
    #[must_use]
    pub const fn entry_address(&self) -> NonZeroUsize {
        self.executable.entry_address()
    }

    /// Returns the exact synchronized v5 executable bound to this call.
    #[must_use]
    pub const fn executable(&self) -> &ReadyExecutionGeometryNativeExecutable {
        self.executable
    }

    /// Executes this checkpoint-bound call through the dedicated v5 runner.
    ///
    /// Runner failure restores the complete entry snapshot. Returned status and
    /// caller-visible state still pass exact completion admission.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeCrazyExecutionError`] for runner or
    /// completion failure.
    pub fn execute<Runner>(
        self,
        runner: &mut Runner,
    ) -> ExecutionGeometryNativeCrazyExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let Self { executable, prepared } = self;
        let PreparedExecutionGeometryNativeCrazy { admission, invocation } =
            prepared;
        let mut runner_invocation =
            PreparedExecutionGeometryNativeInvocation::new(
                executable, invocation,
            );
        let raw_status = match runner.run(&mut runner_invocation) {
            Ok(raw_status) => raw_status,
            Err(error) => {
                runner_invocation.abort();
                return Err(Box::new(
                    ExecutionGeometryNativeCrazyExecutionError::Runner(
                        Box::new(error),
                    ),
                ));
            },
        };
        let outcome =
            runner_invocation.complete(raw_status).map_err(|error| {
                use ExecutionGeometryNativeCrazyCompletionError as Completion;
                use ExecutionGeometryNativeCrazyExecutionError as Execution;
                Box::new(Execution::Completion(Completion::Invocation(error)))
            })?;
        Ok(ExecutionGeometryNativeCrazyCompletion {
            outcome,
            state: completion_state(admission, outcome),
        })
    }
}

impl ExecutionGeometryNativeCrazyCompletion {
    /// Returns the exact admitted native call outcome.
    #[must_use]
    pub const fn outcome(&self) -> NativeRegionInvocationOutcome {
        self.outcome
    }

    /// Returns the exact checkpoint after applied crazy or preserved miss.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl<'admission, 'buffers>
    PreparedExecutionGeometryNativeCrazy<'admission, 'buffers>
{
    /// Restores the complete checkpoint-owned entry snapshot.
    pub fn abort(self) {
        self.invocation.abort();
    }

    /// Simulates the exact expected foreign transition for contract tests.
    #[cfg(test)]
    #[doc(hidden)]
    pub fn apply_expected_for_test(&mut self) {
        self.invocation.apply_expected_for_test();
    }

    /// Binds prepared checkpoint state only to the exact synchronized v5 image.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeCrazyBindingError`] when the executable
    /// carries any different verified load image.
    pub fn bind_executable<'executable>(
        self,
        executable: &'executable ReadyExecutionGeometryNativeExecutable,
    ) -> Result<
        ExecutionGeometryNativeCrazyBoundCall<
            'admission,
            'buffers,
            'executable,
        >,
        ExecutionGeometryNativeCrazyBindingError,
    > {
        let Self { admission, invocation } = self;
        if admission.load_image() != executable.image() {
            let error = CrazyBindingError::ExecutableIdentity;
            invocation.abort();
            return Err(error);
        }
        Ok(ExecutionGeometryNativeCrazyBoundCall {
            executable,
            prepared: Self { admission, invocation },
        })
    }

    /// Admits raw native status and selects the already proven crazy
    /// checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeCrazyCompletionError`] when exact ABI
    /// completion fails.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeCrazyCompletion,
        ExecutionGeometryNativeCrazyCompletionError,
    > {
        let outcome = self
            .invocation
            .complete(raw_status)
            .map_err(ExecutionGeometryNativeCrazyCompletionError::Invocation)?;
        Ok(ExecutionGeometryNativeCrazyCompletion {
            outcome,
            state: completion_state(self.admission, outcome),
        })
    }
}

fn completion_state(
    admission: &ExecutionGeometryNativeCrazyAdmission,
    outcome: NativeRegionInvocationOutcome,
) -> ProfileMachineState {
    match outcome {
        NativeRegionInvocationOutcome::Applied(_observation) => {
            admission.expected_state().clone()
        },
        NativeRegionInvocationOutcome::GuardMiss => {
            admission.checkpoint().clone()
        },
    }
}
