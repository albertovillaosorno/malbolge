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
//   - Checkpoint-bound admission and execution of verified v5 non-aliasing
//     jump-data.
// - Must-Not:
//   - Implement platform mapping or the foreign call, forge geometry authority,
//   - or route explicit geometry through legacy direct-native APIs.
// - Allows:
//   - Inputs: exact v5 no-op IR/artifact/checkpoint and caller adapter/runner.
//   - Outputs: prepared/bound calls and exact opaque-geometry completion.
//   - Side effects: supplied executable-memory and runner operations only.
// - Split-When:
//   - Another derived-geometry operation needs materially different policy.
// - Merge-When:
//   - One reviewed geometry-native operation framework preserves equal proofs.
// - Summary:
//   - Executes only normatively replayed explicit-geometry non-aliasing
//     jump-data.
// - Description:
//   - Binds v5 identity to opaque state and exact aliasing jump/self-encryption
//     transition.
// - Usage:
//   - Admit first, then transact or manually prepare/bind/execute.
// - Defaults:
//   - Geometry, identity, buffer, runner, completion, or cleanup drift fails
//   - closed with entry rollback where mutation was possible.
//

//! Checkpoint-bound native execution for explicit-geometry non-aliasing
//! jump-data.

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
    VerifiedExecutionGeometryJumpDataNativeObjectArtifact,
    VerifiedExecutionGeometryLoadImage,
    load_execution_geometry_native_executable,
    release_execution_geometry_native_executable,
};
use crate::geometry_interpreter_handoff::{
    ExecutionGeometryHandoffAdmissionError,
    ExecutionGeometryHandoffExecutionCause,
    ExecutionGeometryInterpreterHandoff,
};

type JumpDataBindingError = ExecutionGeometryNativeJumpDataBindingError;
type JumpAdmissionError = ExecutionGeometryNativeJumpDataAdmissionError;
type JumpCompletionError = ExecutionGeometryNativeJumpDataCompletionError;
type JumpExecutionError<RunnerError> =
    ExecutionGeometryNativeJumpDataExecutionError<RunnerError>;
type JumpPreparationError = ExecutionGeometryNativeJumpDataPreparationError;
type PreparedInvocation<'buffers> = PreparedNativeRegionInvocation<'buffers>;

/// Failure before one verified v5 jump-data can retain checkpoint
/// authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpDataAdmissionError {
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

/// Failure while binding one prepared v5 jump-data to synchronized
/// code.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpDataBindingError {
    /// Synchronized executable image differs from checkpoint-bound admission.
    ExecutableIdentity,
}

/// Failure while admitting one completed v5 jump-data ABI transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpDataCompletionError {
    /// Native result disagreed with the exact prepared transition.
    Invocation(NativeRegionInvocationError),
}

/// Failure after a checkpoint-bound v5 jump-data enters the runner.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpDataExecutionError<RunnerError> {
    /// Returned status or caller-visible state failed exact completion.
    Completion(ExecutionGeometryNativeJumpDataCompletionError),
    /// External runner failed before returning a raw ABI status.
    Runner(Box<RunnerError>),
}

/// Failure while executing one reusable owned jump-data mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpDataOwnedFailure<RunnerError> {
    /// Prepared caller buffers could not bind to the retained ready mapping.
    Binding(ExecutionGeometryNativeJumpDataBindingError),
    /// Bound runner/completion admission failed.
    Execution(Box<ExecutionGeometryNativeJumpDataExecutionError<RunnerError>>),
    /// Caller buffers drifted from the admitted entry checkpoint.
    Preparation(ExecutionGeometryNativeJumpDataPreparationError),
}

/// Result of one dedicated checkpoint-bound v5 jump-data runner call.
pub type ExecutionGeometryNativeJumpDataExecutionResult<RunnerError> = Result<
    ExecutionGeometryNativeJumpDataCompletion,
    Box<ExecutionGeometryNativeJumpDataExecutionError<RunnerError>>,
>;

/// Result of executing one reusable owned jump-data mapping.
pub type ExecutionGeometryNativeJumpDataOwnedResult<RunnerError> = Result<
    ExecutionGeometryNativeJumpDataCompletion,
    Box<ExecutionGeometryNativeJumpDataOwnedFailure<RunnerError>>,
>;

/// Failure while preparing checkpoint-exact buffers for v5 jump-data.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpDataPreparationError {
    /// Borrowed input bytes differ from the admitted checkpoint.
    Input,
    /// Native ABI preparation rejected the exact v5 jump-data contract.
    Invocation(NativeRegionInvocationError),
    /// Borrowed memory differs from the admitted checkpoint.
    Memory,
    /// Borrowed output bytes differ from the admitted checkpoint.
    Output,
}

/// Failure from complete v5 jump-data load/call/admit/release
/// composition.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeJumpDataTransactionFailure<
    MemoryError,
    RunnerError,
> {
    /// Exact prepared call could not bind to the loaded v5 executable.
    Binding {
        /// Exact binding rejection.
        error: ExecutionGeometryNativeJumpDataBindingError,
        /// Failed cleanup retaining the ready mapping, when release also
        /// failed.
        release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// Bound v5 runner or completion admission failed.
    Execution {
        /// Exact runner/completion failure.
        error: Box<ExecutionGeometryNativeJumpDataExecutionError<RunnerError>>,
        /// Failed cleanup retaining the ready mapping, when release also
        /// failed.
        release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// Executable mapping/lifecycle failed before runner entry.
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    /// Checkpoint-exact caller buffers failed preparation before mapping.
    Preparation(ExecutionGeometryNativeJumpDataPreparationError),
    /// Completion committed, but final mapping release failed.
    Release {
        /// Exact committed checkpoint/outcome retained despite cleanup
        /// failure.
        completion: Box<ExecutionGeometryNativeJumpDataCompletion>,
        /// Retryable ready executable and platform release error.
        release_failure:
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    },
}

/// Result of one complete guarded jump-data transaction for adapter
/// ports.
pub type ExecutionGeometryNativeJumpDataAdapterTransactionResult<
    MemoryAdapter,
    Runner,
> = ExecutionGeometryNativeJumpDataTransactionResult<
    <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
    <Runner as ExecutionGeometryNativeRunner>::Error,
>;

/// Result of one complete guarded v5 jump-data transaction.
pub type ExecutionGeometryNativeJumpDataTransactionResult<
    MemoryError,
    RunnerError,
> = Result<
    ExecutionGeometryNativeJumpDataCompletion,
    Box<
        ExecutionGeometryNativeJumpDataTransactionFailure<
            MemoryError,
            RunnerError,
        >,
    >,
>;

/// Result of loading one reusable exact jump-data mapping.
pub type GeometryNativeJumpDataOwnedLoadResult<MemoryError> = Result<
    LoadedExecutionGeometryNativeJumpData,
    Box<NativeExecutableLoadFailure<MemoryError>>,
>;

/// Result of releasing one reusable exact jump-data mapping.
pub type GeometryNativeJumpDataOwnedReleaseResult<MemoryError> = Result<
    (),
    Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
>;

/// Verified v5 jump-data bound to one opaque checkpoint and normative
/// exit.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpDataAdmission {
    artifact: VerifiedExecutionGeometryJumpDataNativeObjectArtifact,
    checkpoint: ProfileMachineState,
    expected_state: ProfileMachineState,
    load_image: VerifiedExecutionGeometryLoadImage,
    program: ExecutionGeometryRegionEffectProgram,
}

/// Exact synchronized mapping weight retained by one owned jump-data.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpDataResidentWeight {
    mapped_bytes: usize,
    mappings: usize,
}

/// One reusable ready jump-data mapping beside exact admission.
#[derive(Debug)]
pub struct LoadedExecutionGeometryNativeJumpData {
    admission: ExecutionGeometryNativeJumpDataAdmission,
    executable: ReadyExecutionGeometryNativeExecutable,
}

/// Prepared checkpoint-owned jump-data bound to exact synchronized v5
/// code.
#[derive(Debug)]
pub struct ExecutionGeometryNativeJumpDataBoundCall<
    'admission,
    'buffers,
    'executable,
> {
    executable: &'executable ReadyExecutionGeometryNativeExecutable,
    prepared: PreparedExecutionGeometryNativeJumpData<'admission, 'buffers>,
}

/// One admitted jump-data result retaining opaque geometry authority.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeJumpDataCompletion {
    outcome: NativeRegionInvocationOutcome,
    state: ProfileMachineState,
}

/// Borrow-scoped jump-data ABI contract retaining checkpoint admission.
#[derive(Debug)]
pub struct PreparedExecutionGeometryNativeJumpData<'admission, 'buffers> {
    admission: &'admission ExecutionGeometryNativeJumpDataAdmission,
    invocation: PreparedNativeRegionInvocation<'buffers>,
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeJumpDataOwnedFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Binding(error) => Display::fmt(error, f),
            Self::Execution(error) => Display::fmt(error, f),
            Self::Preparation(error) => Display::fmt(error, f),
        }
    }
}

impl Display for ExecutionGeometryNativeJumpDataAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => f.write_str(
                "v5 jump-data artifact identity differs from program",
            ),
            Self::Checkpoint(error) => Display::fmt(error, f),
            Self::Identity(_error) => {
                f.write_str("v5 jump-data identity reconstruction failed")
            },
            Self::Load(error) => Display::fmt(error, f),
            Self::NormativeReplay(error) => Display::fmt(error, f),
        }
    }
}

impl Display for ExecutionGeometryNativeJumpDataBindingError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("v5 jump-data executable identity differs from call")
    }
}

impl Display for ExecutionGeometryNativeJumpDataCompletionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Invocation(error) => Display::fmt(error, f),
        }
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeJumpDataExecutionError<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Completion(error) => Display::fmt(error, f),
            Self::Runner(error) => {
                write!(f, "v5 jump-data runner failed: {error}")
            },
        }
    }
}

impl Display for ExecutionGeometryNativeJumpDataPreparationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Input => {
                f.write_str("v5 jump-data input differs from checkpoint")
            },
            Self::Invocation(error) => Display::fmt(error, f),
            Self::Memory => {
                f.write_str("v5 jump-data memory differs from checkpoint")
            },
            Self::Output => {
                f.write_str("v5 jump-data output differs from checkpoint")
            },
        }
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for ExecutionGeometryNativeJumpDataTransactionFailure<
        MemoryError,
        RunnerError,
    >
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Binding { error, .. } => {
                write!(f, "v5 jump-data transaction binding failed: {error}")
            },
            Self::Execution { error, .. } => {
                write!(f, "v5 jump-data transaction execution failed: {error}")
            },
            Self::Load(error) => {
                write!(f, "v5 jump-data transaction load failed: {error}")
            },
            Self::Preparation(error) => {
                write!(f, "v5 jump-data preparation failed: {error}")
            },
            Self::Release { release_failure, .. } => {
                write!(f, "v5 jump-data transaction {release_failure}")
            },
        }
    }
}

impl ExecutionGeometryNativeJumpDataAdmission {
    /// Returns the exact verified v5 jump-data artifact retained by
    /// admission.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedExecutionGeometryJumpDataNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the normative entry checkpoint carrying opaque geometry
    /// authority.
    #[must_use]
    pub const fn checkpoint(&self) -> &ProfileMachineState {
        &self.checkpoint
    }

    /// Loads, binds, runs, admits, and releases one guarded v5 initial
    /// non-aliasing jump-data.
    ///
    /// Preparation occurs before mapping. Every failure after a ready mapping
    /// exists attempts exact release, while cleanup failure retains the ready
    /// executable for retry. A post-commit cleanup failure also retains the
    /// normatively proven opaque-geometry completion.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeJumpDataTransactionFailure`]
    /// with exact primary failure and any retryable cleanup ownership.
    pub fn execute_transactionally<MemoryAdapter, Runner>(
        &self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeJumpDataAdapterTransactionResult<
        MemoryAdapter,
        Runner,
    >
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeJumpDataTransactionFailure as Failure;

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

    /// Returns the exact normative state accepted for an applied native call.
    #[must_use]
    pub const fn expected_state(&self) -> &ProfileMachineState {
        &self.expected_state
    }

    /// Returns the relocation-free load image retaining exact v5 identity.
    #[must_use]
    pub const fn load_image(&self) -> &VerifiedExecutionGeometryLoadImage {
        &self.load_image
    }

    /// Loads and retains one reusable synchronized jump-data mapping.
    ///
    /// # Errors
    ///
    /// Returns the exact native executable load failure without publishing a
    /// partial owner.
    pub fn load_owned<Adapter>(
        &self,
        adapter: &mut Adapter,
    ) -> GeometryNativeJumpDataOwnedLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let executable = load_execution_geometry_native_executable(
            adapter,
            self.load_image(),
        )
        .map_err(Box::new)?;
        Ok(LoadedExecutionGeometryNativeJumpData {
            admission: self.clone(),
            executable,
        })
    }

    /// Binds verified non-aliasing jump-data evidence to a normatively replayed
    /// checkpoint.
    ///
    /// Admission first checks opaque geometry/live-ins, then executes one
    /// cloned checkpoint through the normative interpreter and requires
    /// exact v5 reprojection. Native identity and load-image extraction
    /// happen only after that independent semantic replay succeeds.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeJumpDataAdmissionError`] for
    /// checkpoint, replay, identity, or load-image disagreement.
    pub fn new(
        program: ExecutionGeometryRegionEffectProgram,
        checkpoint: ProfileMachineState,
        artifact: VerifiedExecutionGeometryJumpDataNativeObjectArtifact,
    ) -> Result<Self, ExecutionGeometryNativeJumpDataAdmissionError> {
        let replay = ExecutionGeometryInterpreterHandoff::new(
            program.clone(),
            checkpoint.clone(),
        )
        .map_err(JumpAdmissionError::Checkpoint)?;
        let completion = replay.execute().map_err(|failure| {
            JumpAdmissionError::NormativeReplay(failure.cause())
        })?;
        let expected_key = NativeArtifactKey::new_execution_geometry(
            &program,
            artifact.key().target().clone(),
        )
        .map_err(JumpAdmissionError::Identity)?;
        if artifact.key() != &expected_key {
            use JumpAdmissionError as Error;
            return Err(Error::ArtifactIdentity);
        }
        let load_image =
            VerifiedExecutionGeometryLoadImage::from_jump_data(&artifact)
                .map_err(JumpAdmissionError::Load)?;
        Ok(Self {
            artifact,
            checkpoint,
            expected_state: completion.state().clone(),
            load_image,
            program,
        })
    }

    /// Prepares exact checkpoint-owned buffers for guarded v5 initial
    /// non-aliasing jump-data.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeJumpDataPreparationError`] when
    /// any caller buffer drifts or ABI preparation rejects the exact
    /// effect.
    pub fn prepare<'admission, 'buffers>(
        &'admission self,
        buffers: NativeRegionBuffers<'buffers>,
    ) -> Result<
        PreparedExecutionGeometryNativeJumpData<'admission, 'buffers>,
        ExecutionGeometryNativeJumpDataPreparationError,
    > {
        let (memory, input, output) = buffers.into_parts();
        if input != self.checkpoint.io().input() {
            return Err(JumpPreparationError::Input);
        }
        if memory != self.checkpoint.memory() {
            return Err(JumpPreparationError::Memory);
        }
        if output != self.checkpoint.io().output() {
            return Err(JumpPreparationError::Output);
        }
        let invocation = PreparedInvocation::new_execution_geometry_jump_data(
            &self.program,
            memory,
            input,
            output,
        )
        .map_err(JumpPreparationError::Invocation)?;
        Ok(PreparedExecutionGeometryNativeJumpData {
            admission: self,
            invocation,
        })
    }

    /// Returns the exact v5 program whose jump-data was normatively
    /// replayed.
    #[must_use]
    pub const fn program(&self) -> &ExecutionGeometryRegionEffectProgram {
        &self.program
    }
}

impl ExecutionGeometryNativeJumpDataResidentWeight {
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

impl LoadedExecutionGeometryNativeJumpData {
    /// Returns the exact admission retained beside the ready mapping.
    #[must_use]
    pub const fn admission(&self) -> &ExecutionGeometryNativeJumpDataAdmission {
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
    ) -> ExecutionGeometryNativeJumpDataOwnedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let prepared = self.admission.prepare(buffers).map_err(|error| {
            Box::new(ExecutionGeometryNativeJumpDataOwnedFailure::Preparation(
                error,
            ))
        })?;
        let bound =
            prepared
                .bind_executable(&self.executable)
                .map_err(|error| {
                    Box::new(
                        ExecutionGeometryNativeJumpDataOwnedFailure::Binding(
                            error,
                        ),
                    )
                })?;
        bound.execute(runner).map_err(|error| {
            Box::new(ExecutionGeometryNativeJumpDataOwnedFailure::Execution(
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
    ) -> GeometryNativeJumpDataOwnedReleaseResult<Adapter::Error>
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
    ) -> ExecutionGeometryNativeJumpDataResidentWeight {
        ExecutionGeometryNativeJumpDataResidentWeight {
            mapped_bytes: self.executable.mapping().mapped_len(),
            mappings: 1,
        }
    }
}

impl ExecutionGeometryNativeJumpDataBoundCall<'_, '_, '_> {
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
    /// Returns [`ExecutionGeometryNativeJumpDataCompletionError`] when
    /// the completed transition violates exact prepared evidence.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeJumpDataCompletion,
        ExecutionGeometryNativeJumpDataCompletionError,
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
    /// Returns [`ExecutionGeometryNativeJumpDataExecutionError`] for
    /// runner or completion failure.
    pub fn execute<Runner>(
        self,
        runner: &mut Runner,
    ) -> ExecutionGeometryNativeJumpDataExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let Self { executable, prepared } = self;
        let PreparedExecutionGeometryNativeJumpData { admission, invocation } =
            prepared;
        let mut runner_invocation =
            PreparedExecutionGeometryNativeInvocation::new(
                executable, invocation,
            );
        let raw_status = match runner.run(&mut runner_invocation) {
            Ok(raw_status) => raw_status,
            Err(error) => {
                runner_invocation.abort();
                return Err(Box::new(JumpExecutionError::Runner(Box::new(
                    error,
                ))));
            },
        };
        let outcome =
            runner_invocation.complete(raw_status).map_err(|error| {
                use JumpCompletionError as Completion;
                use JumpExecutionError as Execution;
                Box::new(Execution::Completion(Completion::Invocation(error)))
            })?;
        Ok(ExecutionGeometryNativeJumpDataCompletion {
            outcome,
            state: completion_state(admission, outcome),
        })
    }
}

impl ExecutionGeometryNativeJumpDataCompletion {
    /// Returns the exact admitted native call outcome.
    #[must_use]
    pub const fn outcome(&self) -> NativeRegionInvocationOutcome {
        self.outcome
    }

    /// Returns the exact checkpoint after applied no-op or preserved guard
    /// miss.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl<'admission, 'buffers>
    PreparedExecutionGeometryNativeJumpData<'admission, 'buffers>
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
    /// Returns [`ExecutionGeometryNativeJumpDataBindingError`] when the
    /// executable carries any different verified load image.
    pub fn bind_executable<'executable>(
        self,
        executable: &'executable ReadyExecutionGeometryNativeExecutable,
    ) -> Result<
        ExecutionGeometryNativeJumpDataBoundCall<
            'admission,
            'buffers,
            'executable,
        >,
        ExecutionGeometryNativeJumpDataBindingError,
    > {
        let Self { admission, invocation } = self;
        if admission.load_image() != executable.image() {
            let error = JumpDataBindingError::ExecutableIdentity;
            invocation.abort();
            return Err(error);
        }
        Ok(ExecutionGeometryNativeJumpDataBoundCall {
            executable,
            prepared: Self { admission, invocation },
        })
    }

    /// Admits raw native status and selects the already proven output
    /// checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeJumpDataCompletionError`] when
    /// exact ABI completion fails.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeJumpDataCompletion,
        ExecutionGeometryNativeJumpDataCompletionError,
    > {
        let outcome = self.invocation.complete(raw_status).map_err(
            ExecutionGeometryNativeJumpDataCompletionError::Invocation,
        )?;
        Ok(ExecutionGeometryNativeJumpDataCompletion {
            outcome,
            state: completion_state(self.admission, outcome),
        })
    }
}

fn completion_state(
    admission: &ExecutionGeometryNativeJumpDataAdmission,
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
