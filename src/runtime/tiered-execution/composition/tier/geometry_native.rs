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
//   - Admission and safe runner orchestration binding one verified v5 native
//   - initial-halt artifact to one opaque validated VM checkpoint geometry.
// - Must-Not:
//   - Implement executable-memory platform operations or the foreign call,
//     forge
//   - geometry tokens, or route v5 through legacy direct-native execution APIs.
// - Allows:
//   - Inputs: exact v5 IR/artifact/checkpoint, caller buffers,
//     executable-memory
//   - adapter, synchronized exact executable, and geometry-native runner port.
//   - Outputs: checkpoint-bound admission, prepared/bound call, or completion.
//   - Side effects: process-local allocation plus supplied adapter/runner work.
// - Split-When:
//   - Split when geometry-aware executable lifecycle or invocation gains
//   - independent policy.
// - Merge-When:
//   - Merge when one geometry-native owner subsumes admission and execution.
// - Summary:
//   - Makes opaque checkpoint geometry prerequisite to guarded v5 native calls.
// - Description:
//   - Rechecks v5 identity, binds exact synchronized code, and restores
//     prepared
//   - state on runner/completion failure before reconstructing opaque state.
// - Usage:
//   - Admit first, then transact or manually prepare/bind/execute through v5.
// - Defaults:
//   - Identity, geometry, buffer, runner, or completion drift fails closed and
//   - restores the exact prepared entry snapshot where mutation was possible.
//

//! Checkpoint-bound admission for explicit-geometry native artifacts.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::num::NonZeroUsize;

use malbolge::{
    ExecutionGeometryRegionEffectProgram, ProfileMachineError,
    ProfileMachineIoState, ProfileMachineState,
};

use crate::execution_cache::{NativeArtifactKey, NativeIdentityError};
use crate::execution_native::{
    ExecutionGeometryNativeExecutableReleaseFailure,
    ExecutionGeometryNativeRunner, NativeExecutableLoadFailure,
    NativeExecutableMemoryAdapter, NativeRegionBuffers,
    NativeRegionInvocationError, NativeRegionInvocationOutcome,
    PreparedExecutionGeometryNativeInvocation, PreparedNativeRegionInvocation,
    ReadyExecutionGeometryNativeExecutable, VerifiedDirectLoadError,
    VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    VerifiedExecutionGeometryLoadImage,
    load_execution_geometry_native_executable,
    release_execution_geometry_native_executable,
};
use crate::geometry_interpreter_handoff::{
    ExecutionGeometryHandoffAdmissionError, ExecutionGeometryInterpreterHandoff,
};

type InitialHaltBindingError = ExecutionGeometryNativeInitialHaltBindingError;

/// Failure before one v5 native artifact can retain checkpoint-bound authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInitialHaltAdmissionError {
    /// Verified artifact identity differs from the exact requested v5 program.
    ArtifactIdentity,
    /// Opaque checkpoint authority disagrees with the requested v5 program.
    Checkpoint(ExecutionGeometryHandoffAdmissionError),
    /// Exact v5 native identity could not be reconstructed.
    Identity(NativeIdentityError),
    /// Verified COFF could not become one relocation-free aligned load image.
    Load(VerifiedDirectLoadError),
}

/// Failure while binding one prepared v5 call to synchronized code.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInitialHaltBindingError {
    /// Synchronized executable image differs from checkpoint-bound admission.
    ExecutableIdentity,
}

/// Failure while admitting one completed geometry-bound ABI transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInitialHaltCompletionError {
    /// Native result disagreed with the exact prepared transition.
    Invocation(NativeRegionInvocationError),
    /// Reconstructing the opaque-geometry checkpoint failed validation.
    State(ProfileMachineError),
}

/// Failure after a checkpoint-bound v5 call enters the runner boundary.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInitialHaltExecutionError<RunnerError> {
    /// Returned status or caller-visible state failed exact completion
    /// admission.
    Completion(ExecutionGeometryNativeInitialHaltCompletionError),
    /// External runner failed before returning a raw ABI status.
    Runner(Box<RunnerError>),
}

/// Failure while executing one reusable owned initial-halt mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInitialHaltOwnedFailure<RunnerError> {
    /// Prepared caller buffers could not bind to the retained ready mapping.
    Binding(ExecutionGeometryNativeInitialHaltBindingError),
    /// Bound runner/completion admission failed.
    Execution(
        Box<ExecutionGeometryNativeInitialHaltExecutionError<RunnerError>>,
    ),
    /// Caller buffers drifted from the admitted entry checkpoint.
    Preparation(ExecutionGeometryNativeInitialHaltPreparationError),
}

/// Result of one dedicated checkpoint-bound v5 runner call.
pub type ExecutionGeometryNativeInitialHaltExecutionResult<RunnerError> =
    Result<
        ExecutionGeometryNativeInitialHaltCompletion,
        Box<ExecutionGeometryNativeInitialHaltExecutionError<RunnerError>>,
    >;

/// Result of executing one reusable owned initial-halt mapping.
pub type ExecutionGeometryNativeInitialHaltOwnedResult<RunnerError> = Result<
    ExecutionGeometryNativeInitialHaltCompletion,
    Box<ExecutionGeometryNativeInitialHaltOwnedFailure<RunnerError>>,
>;

/// Failure from one complete v5 load, call, admission, and release transaction.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInitialHaltTransactionFailure<
    MemoryError,
    RunnerError,
> {
    /// Exact prepared call could not bind to the loaded v5 executable.
    Binding {
        /// Exact binding rejection.
        error: ExecutionGeometryNativeInitialHaltBindingError,
        /// Failed cleanup retaining the ready mapping, when release also
        /// failed.
        release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// Bound v5 runner or completion admission failed.
    Execution {
        /// Exact runner/completion failure.
        error:
            Box<ExecutionGeometryNativeInitialHaltExecutionError<RunnerError>>,
        /// Failed cleanup retaining the ready mapping, when release also
        /// failed.
        release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// Executable mapping/lifecycle failed before the runner was called.
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    /// Checkpoint-exact caller buffers failed preparation before mapping.
    Preparation(ExecutionGeometryNativeInitialHaltPreparationError),
    /// Native completion committed, but final mapping release failed.
    Release {
        /// Exact committed checkpoint/outcome retained despite cleanup
        /// failure.
        completion: Box<ExecutionGeometryNativeInitialHaltCompletion>,
        /// Retryable ready executable and platform release error.
        release_failure:
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    },
}

/// Result of one complete guarded v5 transaction for concrete adapter ports.
pub type ExecutionGeometryNativeInitialHaltAdapterTransactionResult<
    MemoryAdapter,
    Runner,
> = ExecutionGeometryNativeInitialHaltTransactionResult<
    <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
    <Runner as ExecutionGeometryNativeRunner>::Error,
>;

/// Result of one complete guarded v5 native transaction.
pub type ExecutionGeometryNativeInitialHaltTransactionResult<
    MemoryError,
    RunnerError,
> = Result<
    ExecutionGeometryNativeInitialHaltCompletion,
    Box<
        ExecutionGeometryNativeInitialHaltTransactionFailure<
            MemoryError,
            RunnerError,
        >,
    >,
>;

/// Result of loading one reusable exact initial-halt mapping.
pub type GeometryNativeInitialHaltOwnedLoadResult<MemoryError> = Result<
    LoadedExecutionGeometryNativeInitialHalt,
    Box<NativeExecutableLoadFailure<MemoryError>>,
>;

/// Result of releasing one reusable exact initial-halt mapping.
pub type GeometryNativeInitialHaltOwnedReleaseResult<MemoryError> = Result<
    (),
    Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
>;

/// Failure while preparing checkpoint-exact caller buffers for the v5 ABI.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInitialHaltPreparationError {
    /// Borrowed input bytes differ from the admitted checkpoint.
    Input,
    /// Native ABI preparation rejected the exact v5 halt contract.
    Invocation(NativeRegionInvocationError),
    /// Borrowed memory differs from the admitted checkpoint.
    Memory,
    /// Borrowed output bytes differ from the admitted checkpoint.
    Output,
}

/// Verified v5 initial-halt artifact inseparably bound to one opaque
/// checkpoint.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeInitialHaltAdmission {
    artifact: VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    checkpoint: ProfileMachineState,
    load_image: VerifiedExecutionGeometryLoadImage,
    program: ExecutionGeometryRegionEffectProgram,
}

/// Exact synchronized mapping weight retained by one owned initial halt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeInitialHaltResidentWeight {
    mapped_bytes: usize,
    mappings: usize,
}

/// One reusable ready initial-halt mapping beside exact admission.
#[derive(Debug)]
pub struct LoadedExecutionGeometryNativeInitialHalt {
    admission: Box<ExecutionGeometryNativeInitialHaltAdmission>,
    executable: ReadyExecutionGeometryNativeExecutable,
}

/// Prepared checkpoint-owned ABI call bound to exact synchronized v5 code.
#[derive(Debug)]
pub struct ExecutionGeometryNativeInitialHaltBoundCall<
    'admission,
    'buffers,
    'executable,
> {
    executable: &'executable ReadyExecutionGeometryNativeExecutable,
    prepared: PreparedExecutionGeometryNativeInitialHalt<'admission, 'buffers>,
}

/// One admitted result retaining the opaque checkpoint geometry token.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeInitialHaltCompletion {
    outcome: NativeRegionInvocationOutcome,
    state: ProfileMachineState,
}

/// Borrow-scoped v5 ABI contract retaining checkpoint-bound admission.
#[derive(Debug)]
pub struct PreparedExecutionGeometryNativeInitialHalt<'admission, 'buffers> {
    admission: &'admission ExecutionGeometryNativeInitialHaltAdmission,
    invocation: PreparedNativeRegionInvocation<'buffers>,
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeInitialHaltOwnedFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Binding(error) => Display::fmt(error, f),
            Self::Execution(error) => Display::fmt(error, f),
            Self::Preparation(error) => Display::fmt(error, f),
        }
    }
}

impl Display for ExecutionGeometryNativeInitialHaltAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => {
                f.write_str("v5 native artifact identity differs from program")
            },
            Self::Checkpoint(error) => Display::fmt(error, f),
            Self::Identity(_error) => {
                f.write_str("v5 native identity reconstruction failed")
            },
            Self::Load(error) => Display::fmt(error, f),
        }
    }
}

impl Display for ExecutionGeometryNativeInitialHaltBindingError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("v5 synchronized executable identity differs from call")
    }
}

impl Display for ExecutionGeometryNativeInitialHaltCompletionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Invocation(error) => Display::fmt(error, f),
            Self::State(error) => Display::fmt(error, f),
        }
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeInitialHaltExecutionError<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Completion(error) => Display::fmt(error, f),
            Self::Runner(error) => {
                write!(f, "v5 native runner failed: {error}")
            },
        }
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for ExecutionGeometryNativeInitialHaltTransactionFailure<
        MemoryError,
        RunnerError,
    >
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Binding { error, .. } => {
                write!(f, "v5 native transaction binding failed: {error}")
            },
            Self::Execution { error, .. } => {
                write!(f, "v5 native transaction execution failed: {error}")
            },
            Self::Load(error) => {
                write!(f, "v5 native transaction load failed: {error}")
            },
            Self::Preparation(error) => {
                write!(f, "v5 native transaction preparation failed: {error}")
            },
            Self::Release { release_failure, .. } => {
                write!(f, "v5 native transaction {release_failure}")
            },
        }
    }
}

impl Display for ExecutionGeometryNativeInitialHaltPreparationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Input => {
                f.write_str("v5 native input differs from checkpoint")
            },
            Self::Invocation(error) => Display::fmt(error, f),
            Self::Memory => {
                f.write_str("v5 native memory differs from checkpoint")
            },
            Self::Output => {
                f.write_str("v5 native output differs from checkpoint")
            },
        }
    }
}

impl ExecutionGeometryNativeInitialHaltAdmission {
    /// Returns the exact verified v5 native artifact retained by admission.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedExecutionGeometryInitialHaltNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the normative checkpoint carrying opaque geometry authority.
    #[must_use]
    pub const fn checkpoint(&self) -> &ProfileMachineState {
        &self.checkpoint
    }

    /// Loads, binds, runs, admits, and releases one guarded v5 halt.
    ///
    /// Buffer preparation happens before executable mapping. Every failure
    /// after a ready mapping exists attempts exact release; cleanup failure
    /// retains the ready executable for retry. Release failure after
    /// successful completion also retains the committed opaque-geometry
    /// checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInitialHaltTransactionFailure`] with
    /// the exact failing phase and any retryable mapping cleanup ownership.
    pub fn execute_transactionally<MemoryAdapter, Runner>(
        &self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeInitialHaltAdapterTransactionResult<
        MemoryAdapter,
        Runner,
    >
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeInitialHaltTransactionFailure as Failure;

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

    /// Returns the relocation-free load image bound to the same exact v5 key.
    #[must_use]
    pub const fn load_image(&self) -> &VerifiedExecutionGeometryLoadImage {
        &self.load_image
    }

    /// Loads and retains one reusable synchronized initial-halt mapping.
    ///
    /// # Errors
    ///
    /// Returns the exact native executable load failure without publishing a
    /// partial owner.
    pub fn load_owned<Adapter>(
        &self,
        adapter: &mut Adapter,
    ) -> GeometryNativeInitialHaltOwnedLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let executable = load_execution_geometry_native_executable(
            adapter,
            self.load_image(),
        )
        .map_err(Box::new)?;
        Ok(LoadedExecutionGeometryNativeInitialHalt {
            admission: Box::new(self.clone()),
            executable,
        })
    }

    /// Binds verified v5 native evidence to one already validated checkpoint.
    ///
    /// The checkpoint's opaque geometry token remains the execution authority.
    /// Exact program/artifact identity is reconstructed independently before a
    /// load image is retained. No executable mapping or call is performed.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInitialHaltAdmissionError`] when
    /// checkpoint admission, exact v5 artifact identity, or load-image
    /// extraction fails.
    pub fn new(
        program: ExecutionGeometryRegionEffectProgram,
        checkpoint: ProfileMachineState,
        artifact: VerifiedExecutionGeometryInitialHaltNativeObjectArtifact,
    ) -> Result<Self, ExecutionGeometryNativeInitialHaltAdmissionError> {
        let _checkpoint_admission = ExecutionGeometryInterpreterHandoff::new(
            program.clone(),
            checkpoint.clone(),
        )
        .map_err(
            ExecutionGeometryNativeInitialHaltAdmissionError::Checkpoint,
        )?;
        let expected_key = NativeArtifactKey::new_execution_geometry(
            &program,
            artifact.key().target().clone(),
        )
        .map_err(ExecutionGeometryNativeInitialHaltAdmissionError::Identity)?;
        if artifact.key() != &expected_key {
            use ExecutionGeometryNativeInitialHaltAdmissionError as Error;
            return Err(Error::ArtifactIdentity);
        }
        let load_image =
            VerifiedExecutionGeometryLoadImage::from_initial_halt(&artifact)
                .map_err(
                    ExecutionGeometryNativeInitialHaltAdmissionError::Load,
                )?;
        Ok(Self {
            artifact,
            checkpoint,
            load_image,
            program,
        })
    }

    /// Prepares exact checkpoint-owned buffers for the guarded v5 halt ABI.
    ///
    /// Borrowed memory, input, and committed output must match the admitted
    /// checkpoint byte-for-byte. The resulting value retains this admission and
    /// deliberately exposes no raw state pointer or executable-call method.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInitialHaltPreparationError`] when any
    /// caller buffer drifts or native ABI preparation rejects the exact halt.
    pub fn prepare<'admission, 'buffers>(
        &'admission self,
        buffers: NativeRegionBuffers<'buffers>,
    ) -> Result<
        PreparedExecutionGeometryNativeInitialHalt<'admission, 'buffers>,
        ExecutionGeometryNativeInitialHaltPreparationError,
    > {
        let (memory, input, output) = buffers.into_parts();
        if input != self.checkpoint.io().input() {
            return Err(
                ExecutionGeometryNativeInitialHaltPreparationError::Input,
            );
        }
        if memory != self.checkpoint.memory() {
            return Err(
                ExecutionGeometryNativeInitialHaltPreparationError::Memory,
            );
        }
        if output != self.checkpoint.io().output() {
            return Err(
                ExecutionGeometryNativeInitialHaltPreparationError::Output,
            );
        }
        let invocation =
            PreparedNativeRegionInvocation::new_execution_geometry_initial_halt(
                &self.program,
                memory,
                input,
                output,
            )
            .map_err(
                ExecutionGeometryNativeInitialHaltPreparationError::Invocation,
            )?;
        Ok(PreparedExecutionGeometryNativeInitialHalt {
            admission: self,
            invocation,
        })
    }

    /// Returns the exact v5 program whose declarative geometry was admitted.
    #[must_use]
    pub const fn program(&self) -> &ExecutionGeometryRegionEffectProgram {
        &self.program
    }
}

impl ExecutionGeometryNativeInitialHaltResidentWeight {
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

impl LoadedExecutionGeometryNativeInitialHalt {
    /// Returns the exact admission retained beside the ready mapping.
    #[must_use]
    pub const fn admission(
        &self,
    ) -> &ExecutionGeometryNativeInitialHaltAdmission {
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
    ) -> ExecutionGeometryNativeInitialHaltOwnedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let prepared = self.admission.prepare(buffers).map_err(|error| {
            Box::new(
                ExecutionGeometryNativeInitialHaltOwnedFailure::Preparation(
                    error,
                ),
            )
        })?;
        let bound =
            prepared
                .bind_executable(&self.executable)
                .map_err(|error| {
                    Box::new(
                        ExecutionGeometryNativeInitialHaltOwnedFailure::Binding(
                            error,
                        ),
                    )
                })?;
        bound.execute(runner).map_err(|error| {
            Box::new(ExecutionGeometryNativeInitialHaltOwnedFailure::Execution(
                error,
            ))
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
    ) -> GeometryNativeInitialHaltOwnedReleaseResult<Adapter::Error>
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
    ) -> ExecutionGeometryNativeInitialHaltResidentWeight {
        ExecutionGeometryNativeInitialHaltResidentWeight {
            mapped_bytes: self.executable.mapping().mapped_len(),
            mappings: 1,
        }
    }
}

impl ExecutionGeometryNativeInitialHaltBoundCall<'_, '_, '_> {
    /// Simulates the exact expected foreign transition for contract tests.
    #[cfg(test)]
    #[doc(hidden)]
    pub fn apply_expected_for_test(&mut self) {
        self.prepared.apply_expected_for_test();
    }

    /// Admits one raw status through the checkpoint-owned prepared call.
    ///
    /// This method does not invoke machine code. It only verifies a status and
    /// caller-visible state after some future geometry-specific runner call.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInitialHaltCompletionError`] when the
    /// completed transition or reconstructed checkpoint fails admission.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeInitialHaltCompletion,
        ExecutionGeometryNativeInitialHaltCompletionError,
    > {
        self.prepared.complete(raw_status)
    }

    /// Returns the synchronized entrypoint retained by this identity binding.
    #[must_use]
    pub const fn entry_address(&self) -> NonZeroUsize {
        self.executable.entry_address()
    }

    /// Returns the exact synchronized v5 executable bound to this call.
    #[must_use]
    pub const fn executable(&self) -> &ReadyExecutionGeometryNativeExecutable {
        self.executable
    }

    /// Executes only this checkpoint-bound call through the dedicated v5 port.
    ///
    /// Runner failure restores the complete prepared entry snapshot before the
    /// error escapes. A returned status still passes through exact native
    /// result admission and opaque-geometry checkpoint reconstruction.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInitialHaltExecutionError`] when the
    /// external runner fails or the returned transition fails admission.
    pub fn execute<Runner>(
        self,
        runner: &mut Runner,
    ) -> ExecutionGeometryNativeInitialHaltExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let Self { executable, prepared } = self;
        let PreparedExecutionGeometryNativeInitialHalt {
            admission,
            invocation,
        } = prepared;
        let mut runner_invocation =
            PreparedExecutionGeometryNativeInvocation::new(
                executable, invocation,
            );
        let raw_status = match runner.run(&mut runner_invocation) {
            Ok(raw_status) => raw_status,
            Err(error) => {
                runner_invocation.abort();
                return Err(Box::new(
                    ExecutionGeometryNativeInitialHaltExecutionError::Runner(
                        Box::new(error),
                    ),
                ));
            },
        };
        let outcome = runner_invocation.complete(raw_status).map_err(|error| {
            use ExecutionGeometryNativeInitialHaltCompletionError as Completion;
            use ExecutionGeometryNativeInitialHaltExecutionError as Execution;
            Box::new(Execution::Completion(Completion::Invocation(error)))
        })?;
        let state = completion_state(admission, outcome).map_err(|error| {
            Box::new(
                ExecutionGeometryNativeInitialHaltExecutionError::Completion(
                    error,
                ),
            )
        })?;
        Ok(ExecutionGeometryNativeInitialHaltCompletion { outcome, state })
    }
}

impl ExecutionGeometryNativeInitialHaltCompletion {
    /// Returns the exact admitted native call outcome.
    #[must_use]
    pub const fn outcome(&self) -> NativeRegionInvocationOutcome {
        self.outcome
    }

    /// Returns the complete checkpoint retaining opaque geometry authority.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl<'admission, 'buffers>
    PreparedExecutionGeometryNativeInitialHalt<'admission, 'buffers>
{
    fn abort(self) {
        self.invocation.abort();
    }

    /// Simulates the exact expected foreign transition for contract tests.
    #[cfg(test)]
    #[doc(hidden)]
    pub fn apply_expected_for_test(&mut self) {
        self.invocation.apply_expected_for_test();
    }

    /// Binds this prepared checkpoint-owned call to exact synchronized v5 code.
    ///
    /// Identity mismatch consumes and aborts the prepared call, restoring its
    /// entry snapshot. The returned bound value still exposes no raw state
    /// pointer and has no machine-code invocation method.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInitialHaltBindingError`] when the
    /// ready executable carries any different verified load image.
    pub fn bind_executable<'executable>(
        self,
        executable: &'executable ReadyExecutionGeometryNativeExecutable,
    ) -> Result<
        ExecutionGeometryNativeInitialHaltBoundCall<
            'admission,
            'buffers,
            'executable,
        >,
        ExecutionGeometryNativeInitialHaltBindingError,
    > {
        let Self { admission, invocation } = self;
        if admission.load_image() != executable.image() {
            let error = InitialHaltBindingError::ExecutableIdentity;
            invocation.abort();
            return Err(error);
        }
        let prepared = Self { admission, invocation };
        Ok(
            ExecutionGeometryNativeInitialHaltBoundCall {
                executable,
                prepared,
            },
        )
    }

    /// Admits one raw status and reconstructs the opaque-geometry checkpoint.
    ///
    /// `Applied` can succeed only after the underlying ABI verifier observes
    /// the exact halt transition. `GuardMiss` retains the untouched entry
    /// checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInitialHaltCompletionError`] when
    /// native result admission or checkpoint reconstruction fails.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeInitialHaltCompletion,
        ExecutionGeometryNativeInitialHaltCompletionError,
    > {
        let outcome = self.invocation.complete(raw_status).map_err(
            ExecutionGeometryNativeInitialHaltCompletionError::Invocation,
        )?;
        let state = completion_state(self.admission, outcome)?;
        Ok(ExecutionGeometryNativeInitialHaltCompletion { outcome, state })
    }
}

fn completion_state(
    admission: &ExecutionGeometryNativeInitialHaltAdmission,
    outcome: NativeRegionInvocationOutcome,
) -> Result<
    ProfileMachineState,
    ExecutionGeometryNativeInitialHaltCompletionError,
> {
    let checkpoint = admission.checkpoint();
    let NativeRegionInvocationOutcome::Applied(observation) = outcome else {
        return Ok(checkpoint.clone());
    };
    let io = ProfileMachineIoState::new(
        checkpoint.io().input().to_vec(),
        observation.input_consumed,
        checkpoint.io().output().to_vec(),
        observation.termination,
    )
    .map_err(ExecutionGeometryNativeInitialHaltCompletionError::State)?;
    ProfileMachineState::new_with_geometry(
        checkpoint.geometry(),
        checkpoint.memory().to_vec(),
        observation.registers,
        io,
    )
    .map_err(ExecutionGeometryNativeInitialHaltCompletionError::State)
}
