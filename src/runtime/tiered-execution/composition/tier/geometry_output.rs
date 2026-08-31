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
//   - Checkpoint-bound admission and transactional execution of v5 output.
// - Must-Not:
//   - Implement platform mapping or the foreign call, forge geometry authority,
//   - or route explicit geometry through legacy direct-native APIs.
// - Allows:
//   - Inputs: exact v5 output IR/artifact/checkpoint and caller adapter/runner.
//   - Outputs: prepared/bound calls and exact opaque-geometry completion.
//   - Side effects: supplied executable-memory and runner operations only.
// - Split-When:
//   - Reusable mapping ownership or residency introduces lifecycle policy.
// - Merge-When:
//   - One reviewed geometry-native operation framework preserves equal proofs.
// - Summary:
//   - Executes only normatively replayed explicit-geometry output.
// - Description:
//   - Binds exact output identity to opaque checkpoint and exact byte append.
// - Usage:
//   - Admit first, then transact or manually prepare/bind/execute.
// - Defaults:
//   - Geometry, identity, buffer, runner, completion, or cleanup drift fails
//   - closed with entry rollback where mutation was possible.
//

//! Checkpoint-bound native execution for explicit-geometry output.

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
    VerifiedExecutionGeometryLoadImage,
    VerifiedExecutionGeometryOutputNativeObjectArtifact,
    load_execution_geometry_native_executable,
    release_execution_geometry_native_executable,
};
use crate::geometry_interpreter_handoff::{
    ExecutionGeometryHandoffAdmissionError,
    ExecutionGeometryHandoffExecutionCause,
    ExecutionGeometryInterpreterHandoff,
};

type OutputBindingError = ExecutionGeometryNativeOutputBindingError;

/// Failure before one verified v5 output can retain checkpoint authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeOutputAdmissionError {
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

/// Failure while binding one prepared v5 output to synchronized code.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeOutputBindingError {
    /// Synchronized executable image differs from checkpoint-bound admission.
    ExecutableIdentity,
}

/// Failure while admitting one completed v5 output ABI transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeOutputCompletionError {
    /// Native result disagreed with the exact prepared transition.
    Invocation(NativeRegionInvocationError),
}

/// Failure after a checkpoint-bound v5 output enters the runner.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeOutputExecutionError<RunnerError> {
    /// Returned status or caller-visible state failed exact completion.
    Completion(ExecutionGeometryNativeOutputCompletionError),
    /// External runner failed before returning a raw ABI status.
    Runner(Box<RunnerError>),
}

/// Failure while executing one reusable owned output mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeOutputOwnedFailure<RunnerError> {
    /// Prepared caller buffers could not bind to the retained ready mapping.
    Binding(ExecutionGeometryNativeOutputBindingError),
    /// Bound runner/completion admission failed.
    Execution(Box<ExecutionGeometryNativeOutputExecutionError<RunnerError>>),
    /// Caller buffers drifted from the admitted entry checkpoint.
    Preparation(ExecutionGeometryNativeOutputPreparationError),
}

/// Result of one dedicated checkpoint-bound v5 output runner call.
pub type ExecutionGeometryNativeOutputExecutionResult<RunnerError> = Result<
    ExecutionGeometryNativeOutputCompletion,
    Box<ExecutionGeometryNativeOutputExecutionError<RunnerError>>,
>;

/// Result of executing one reusable owned output mapping.
pub type ExecutionGeometryNativeOutputOwnedResult<RunnerError> = Result<
    ExecutionGeometryNativeOutputCompletion,
    Box<ExecutionGeometryNativeOutputOwnedFailure<RunnerError>>,
>;

/// Failure while preparing checkpoint-exact buffers for v5 output.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeOutputPreparationError {
    /// Borrowed input bytes differ from the admitted checkpoint.
    Input,
    /// Native ABI preparation rejected the exact v5 output contract.
    Invocation(NativeRegionInvocationError),
    /// Borrowed memory differs from the admitted checkpoint.
    Memory,
    /// Borrowed output prefix differs from the admitted checkpoint.
    Output,
}

/// Failure from complete v5 output load/call/admit/release composition.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeOutputTransactionFailure<
    MemoryError,
    RunnerError,
> {
    /// Exact prepared call could not bind to the loaded v5 executable.
    Binding {
        /// Exact binding rejection.
        error: ExecutionGeometryNativeOutputBindingError,
        /// Failed cleanup retaining the ready mapping, when release also
        /// failed.
        release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// Bound v5 runner or completion admission failed.
    Execution {
        /// Exact runner/completion failure.
        error: Box<ExecutionGeometryNativeOutputExecutionError<RunnerError>>,
        /// Failed cleanup retaining the ready mapping, when release also
        /// failed.
        release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// Executable mapping/lifecycle failed before runner entry.
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    /// Checkpoint-exact caller buffers failed preparation before mapping.
    Preparation(ExecutionGeometryNativeOutputPreparationError),
    /// Completion committed, but final mapping release failed.
    Release {
        /// Exact committed checkpoint/outcome retained despite cleanup
        /// failure.
        completion: Box<ExecutionGeometryNativeOutputCompletion>,
        /// Retryable ready executable and platform release error.
        release_failure:
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    },
}

/// Result of one complete guarded output transaction for adapter ports.
pub type ExecutionGeometryNativeOutputAdapterTransactionResult<
    MemoryAdapter,
    Runner,
> = ExecutionGeometryNativeOutputTransactionResult<
    <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
    <Runner as ExecutionGeometryNativeRunner>::Error,
>;

/// Result of one complete guarded v5 output transaction.
pub type ExecutionGeometryNativeOutputTransactionResult<
    MemoryError,
    RunnerError,
> = Result<
    ExecutionGeometryNativeOutputCompletion,
    Box<
        ExecutionGeometryNativeOutputTransactionFailure<
            MemoryError,
            RunnerError,
        >,
    >,
>;

/// Result of loading one reusable exact output mapping.
pub type GeometryNativeOutputOwnedLoadResult<MemoryError> = Result<
    LoadedExecutionGeometryNativeOutput,
    Box<NativeExecutableLoadFailure<MemoryError>>,
>;

/// Result of releasing one reusable exact output mapping.
pub type GeometryNativeOutputOwnedReleaseResult<MemoryError> = Result<
    (),
    Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
>;

/// Verified v5 output bound to one opaque checkpoint and normative exit.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeOutputAdmission {
    artifact: VerifiedExecutionGeometryOutputNativeObjectArtifact,
    checkpoint: ProfileMachineState,
    expected_state: ProfileMachineState,
    load_image: VerifiedExecutionGeometryLoadImage,
    program: ExecutionGeometryRegionEffectProgram,
}

/// Exact synchronized mapping weight retained by one owned output.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeOutputResidentWeight {
    mapped_bytes: usize,
    mappings: usize,
}

/// One reusable ready output mapping beside exact admission.
#[derive(Debug)]
pub struct LoadedExecutionGeometryNativeOutput {
    admission: Box<ExecutionGeometryNativeOutputAdmission>,
    executable: ReadyExecutionGeometryNativeExecutable,
}

/// Prepared checkpoint-owned output bound to exact synchronized v5 code.
#[derive(Debug)]
pub struct ExecutionGeometryNativeOutputBoundCall<
    'admission,
    'buffers,
    'executable,
> {
    executable: &'executable ReadyExecutionGeometryNativeExecutable,
    prepared: PreparedExecutionGeometryNativeOutput<'admission, 'buffers>,
}

/// One admitted output result retaining opaque geometry authority.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeOutputCompletion {
    outcome: NativeRegionInvocationOutcome,
    state: ProfileMachineState,
}

/// Borrow-scoped output ABI contract retaining checkpoint admission.
#[derive(Debug)]
pub struct PreparedExecutionGeometryNativeOutput<'admission, 'buffers> {
    admission: &'admission ExecutionGeometryNativeOutputAdmission,
    invocation: PreparedNativeRegionInvocation<'buffers>,
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeOutputOwnedFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Binding(error) => Display::fmt(error, f),
            Self::Execution(error) => Display::fmt(error, f),
            Self::Preparation(error) => Display::fmt(error, f),
        }
    }
}

impl Display for ExecutionGeometryNativeOutputAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => {
                f.write_str("verified v5 output artifact identity drifted")
            },
            Self::Checkpoint(error) => Display::fmt(error, f),
            Self::Identity(_error) => {
                f.write_str("v5 output identity reconstruction failed")
            },
            Self::Load(error) => Display::fmt(error, f),
            Self::NormativeReplay(error) => Display::fmt(error, f),
        }
    }
}

impl Display for ExecutionGeometryNativeOutputBindingError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("v5 output executable identity differs from call")
    }
}

impl Display for ExecutionGeometryNativeOutputCompletionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Invocation(error) => Display::fmt(error, f),
        }
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeOutputExecutionError<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Completion(error) => Display::fmt(error, f),
            Self::Runner(error) => {
                write!(f, "v5 output runner failed: {error}")
            },
        }
    }
}

impl Display for ExecutionGeometryNativeOutputPreparationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Input => {
                f.write_str("v5 output input differs from checkpoint")
            },
            Self::Invocation(error) => Display::fmt(error, f),
            Self::Memory => {
                f.write_str("v5 output memory differs from checkpoint")
            },
            Self::Output => {
                f.write_str("v5 output prefix differs from checkpoint")
            },
        }
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for ExecutionGeometryNativeOutputTransactionFailure<
        MemoryError,
        RunnerError,
    >
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Binding { error, .. } => {
                write!(f, "v5 output transaction binding failed: {error}")
            },
            Self::Execution { error, .. } => {
                write!(f, "v5 output transaction execution failed: {error}")
            },
            Self::Load(error) => {
                write!(f, "v5 output transaction load failed: {error}")
            },
            Self::Preparation(error) => {
                write!(f, "v5 output transaction preparation failed: {error}")
            },
            Self::Release { release_failure, .. } => {
                write!(f, "v5 output transaction {release_failure}")
            },
        }
    }
}

impl ExecutionGeometryNativeOutputAdmission {
    /// Returns the exact verified v5 output artifact retained by admission.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedExecutionGeometryOutputNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the normative entry checkpoint carrying opaque geometry
    /// authority.
    #[must_use]
    pub const fn checkpoint(&self) -> &ProfileMachineState {
        &self.checkpoint
    }

    /// Loads, binds, runs, admits, and releases one guarded v5 output.
    ///
    /// Preparation occurs before mapping. Every failure after a ready mapping
    /// exists attempts exact release, while cleanup failure retains the ready
    /// executable for retry. A post-commit cleanup failure also retains the
    /// normatively proven opaque-geometry completion.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeOutputTransactionFailure`] with exact
    /// primary failure and any retryable cleanup ownership.
    pub fn execute_transactionally<MemoryAdapter, Runner>(
        &self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeOutputAdapterTransactionResult<
        MemoryAdapter,
        Runner,
    >
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeOutputTransactionFailure as Failure;

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

    /// Loads and retains one reusable synchronized output mapping.
    ///
    /// # Errors
    ///
    /// Returns the exact native executable load failure without publishing a
    /// partial owner.
    pub fn load_owned<Adapter>(
        &self,
        adapter: &mut Adapter,
    ) -> GeometryNativeOutputOwnedLoadResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let executable = load_execution_geometry_native_executable(
            adapter,
            self.load_image(),
        )
        .map_err(Box::new)?;
        Ok(LoadedExecutionGeometryNativeOutput {
            admission: Box::new(self.clone()),
            executable,
        })
    }

    /// Binds verified output evidence to a normatively replayed checkpoint.
    ///
    /// Admission first checks opaque geometry/effect continuity through the
    /// interpreter handoff. Only after exact replay succeeds does it rebuild
    /// native identity and extract a relocation-free code image.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeOutputAdmissionError`] for checkpoint,
    /// replay, identity, artifact, or load-image disagreement.
    pub fn new(
        program: ExecutionGeometryRegionEffectProgram,
        checkpoint: ProfileMachineState,
        artifact: VerifiedExecutionGeometryOutputNativeObjectArtifact,
    ) -> Result<Self, ExecutionGeometryNativeOutputAdmissionError> {
        let replay = ExecutionGeometryInterpreterHandoff::new(
            program.clone(),
            checkpoint.clone(),
        )
        .map_err(ExecutionGeometryNativeOutputAdmissionError::Checkpoint)?;
        let completion = replay.execute().map_err(|failure| {
            ExecutionGeometryNativeOutputAdmissionError::NormativeReplay(
                failure.cause(),
            )
        })?;
        let expected_key = NativeArtifactKey::new_execution_geometry(
            &program,
            artifact.key().target().clone(),
        )
        .map_err(ExecutionGeometryNativeOutputAdmissionError::Identity)?;
        if artifact.key() != &expected_key {
            return Err(
                ExecutionGeometryNativeOutputAdmissionError::ArtifactIdentity,
            );
        }
        let load_image =
            VerifiedExecutionGeometryLoadImage::from_output(&artifact)
                .map_err(ExecutionGeometryNativeOutputAdmissionError::Load)?;
        Ok(Self {
            artifact,
            checkpoint,
            expected_state: completion.state().clone(),
            load_image,
            program,
        })
    }

    /// Prepares exact checkpoint-owned buffers for guarded v5 output.
    ///
    /// The mutable output slice is physical capacity. Only its logical prefix
    /// at the checkpoint's `output_len` is semantic entry state; remaining
    /// bytes are caller-owned capacity and are preserved except for the exact
    /// appended byte selected by the verified effect.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeOutputPreparationError`] when caller
    /// memory/input/prefix drifts or the ABI rejects capacity/effect evidence.
    pub fn prepare<'admission, 'buffers>(
        &'admission self,
        buffers: NativeRegionBuffers<'buffers>,
    ) -> Result<
        PreparedExecutionGeometryNativeOutput<'admission, 'buffers>,
        ExecutionGeometryNativeOutputPreparationError,
    > {
        let (memory, input, output) = buffers.into_parts();
        if input != self.checkpoint.io().input() {
            return Err(ExecutionGeometryNativeOutputPreparationError::Input);
        }
        if memory != self.checkpoint.memory() {
            return Err(ExecutionGeometryNativeOutputPreparationError::Memory);
        }
        let checkpoint_output = self.checkpoint.io().output();
        if output.get(..checkpoint_output.len()) != Some(checkpoint_output) {
            return Err(ExecutionGeometryNativeOutputPreparationError::Output);
        }
        let invocation =
            PreparedNativeRegionInvocation::new_execution_geometry_output(
                &self.program,
                memory,
                input,
                output,
            )
            .map_err(
                ExecutionGeometryNativeOutputPreparationError::Invocation,
            )?;
        Ok(PreparedExecutionGeometryNativeOutput {
            admission: self,
            invocation,
        })
    }

    /// Returns the exact v5 output IR retained by admission.
    #[must_use]
    pub const fn program(&self) -> &ExecutionGeometryRegionEffectProgram {
        &self.program
    }
}

impl ExecutionGeometryNativeOutputResidentWeight {
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

impl LoadedExecutionGeometryNativeOutput {
    /// Returns the exact admission retained beside the ready mapping.
    #[must_use]
    pub const fn admission(&self) -> &ExecutionGeometryNativeOutputAdmission {
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
    ) -> ExecutionGeometryNativeOutputOwnedResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let prepared = self.admission.prepare(buffers).map_err(|error| {
            Box::new(ExecutionGeometryNativeOutputOwnedFailure::Preparation(
                error,
            ))
        })?;
        let bound =
            prepared
                .bind_executable(&self.executable)
                .map_err(|error| {
                    Box::new(
                        ExecutionGeometryNativeOutputOwnedFailure::Binding(
                            error,
                        ),
                    )
                })?;
        bound.execute(runner).map_err(|error| {
            Box::new(ExecutionGeometryNativeOutputOwnedFailure::Execution(
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
    ) -> GeometryNativeOutputOwnedReleaseResult<Adapter::Error>
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
    ) -> ExecutionGeometryNativeOutputResidentWeight {
        ExecutionGeometryNativeOutputResidentWeight {
            mapped_bytes: self.executable.mapping().mapped_len(),
            mappings: 1,
        }
    }
}

impl ExecutionGeometryNativeOutputBoundCall<'_, '_, '_> {
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
    /// Returns [`ExecutionGeometryNativeOutputCompletionError`] when the
    /// completed transition violates exact prepared evidence.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeOutputCompletion,
        ExecutionGeometryNativeOutputCompletionError,
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
    /// Returns [`ExecutionGeometryNativeOutputExecutionError`] for runner or
    /// completion failure.
    pub fn execute<Runner>(
        self,
        runner: &mut Runner,
    ) -> ExecutionGeometryNativeOutputExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let Self { executable, prepared } = self;
        let PreparedExecutionGeometryNativeOutput { admission, invocation } =
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
                    ExecutionGeometryNativeOutputExecutionError::Runner(
                        Box::new(error),
                    ),
                ));
            },
        };
        let outcome =
            runner_invocation.complete(raw_status).map_err(|error| {
                use ExecutionGeometryNativeOutputCompletionError as Completion;
                use ExecutionGeometryNativeOutputExecutionError as Execution;
                Box::new(Execution::Completion(Completion::Invocation(error)))
            })?;
        Ok(ExecutionGeometryNativeOutputCompletion {
            outcome,
            state: completion_state(admission, outcome),
        })
    }
}

impl ExecutionGeometryNativeOutputCompletion {
    /// Returns the exact admitted native call outcome.
    #[must_use]
    pub const fn outcome(&self) -> NativeRegionInvocationOutcome {
        self.outcome
    }

    /// Returns the exact checkpoint after applied output or preserved miss.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl<'admission, 'buffers>
    PreparedExecutionGeometryNativeOutput<'admission, 'buffers>
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
    /// Returns [`ExecutionGeometryNativeOutputBindingError`] when the
    /// executable carries any different verified load image.
    pub fn bind_executable<'executable>(
        self,
        executable: &'executable ReadyExecutionGeometryNativeExecutable,
    ) -> Result<
        ExecutionGeometryNativeOutputBoundCall<
            'admission,
            'buffers,
            'executable,
        >,
        ExecutionGeometryNativeOutputBindingError,
    > {
        let Self { admission, invocation } = self;
        if admission.load_image() != executable.image() {
            let error = OutputBindingError::ExecutableIdentity;
            invocation.abort();
            return Err(error);
        }
        Ok(ExecutionGeometryNativeOutputBoundCall {
            executable,
            prepared: Self { admission, invocation },
        })
    }

    /// Admits raw native status and selects the already proven output
    /// checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeOutputCompletionError`] when exact ABI
    /// completion fails.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeOutputCompletion,
        ExecutionGeometryNativeOutputCompletionError,
    > {
        let outcome = self.invocation.complete(raw_status).map_err(
            ExecutionGeometryNativeOutputCompletionError::Invocation,
        )?;
        Ok(ExecutionGeometryNativeOutputCompletion {
            outcome,
            state: completion_state(self.admission, outcome),
        })
    }
}

fn completion_state(
    admission: &ExecutionGeometryNativeOutputAdmission,
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
