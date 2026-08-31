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
//   - Checkpoint-bound admission and transactional execution of v5 input.
// - Must-Not:
//   - Implement platform mapping or the foreign call, forge geometry authority,
//   - or route explicit geometry through legacy direct-native APIs.
// - Allows:
//   - Inputs: exact v5 input IR/artifact/checkpoint and caller adapter/runner.
//   - Outputs: prepared/bound calls and exact opaque-geometry completion.
//   - Side effects: supplied executable-memory and runner operations only.
// - Split-When:
//   - Reusable mapping ownership or residency introduces lifecycle policy.
// - Merge-When:
//   - One reviewed geometry-native operation framework preserves equal proofs.
// - Summary:
//   - Executes only normatively replayed explicit-geometry input.
// - Description:
//   - Binds byte/EOF input identity to opaque checkpoint and exact cursor
//     state.
// - Usage:
//   - Admit first, then transact or manually prepare/bind/execute.
// - Defaults:
//   - Geometry, identity, buffer, runner, completion, or cleanup drift fails
//   - closed with entry rollback where mutation was possible.
//

//! Checkpoint-bound native execution for explicit-geometry input.

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
    VerifiedExecutionGeometryInputNativeObjectArtifact,
    VerifiedExecutionGeometryLoadImage,
    load_execution_geometry_native_executable,
    release_execution_geometry_native_executable,
};
use crate::geometry_interpreter_handoff::{
    ExecutionGeometryHandoffAdmissionError,
    ExecutionGeometryHandoffExecutionCause,
    ExecutionGeometryInterpreterHandoff,
};

type InputBindingError = ExecutionGeometryNativeInputBindingError;

/// Failure before one verified v5 input can retain checkpoint authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInputAdmissionError {
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

/// Failure while binding one prepared v5 input to synchronized code.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInputBindingError {
    /// Synchronized executable image differs from checkpoint-bound admission.
    ExecutableIdentity,
}

/// Failure while admitting one completed v5 input ABI transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInputCompletionError {
    /// Native result disagreed with the exact prepared transition.
    Invocation(NativeRegionInvocationError),
}

/// Failure after a checkpoint-bound v5 input enters the runner.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInputExecutionError<RunnerError> {
    /// Returned status or caller-visible state failed exact completion.
    Completion(ExecutionGeometryNativeInputCompletionError),
    /// External runner failed before returning a raw ABI status.
    Runner(Box<RunnerError>),
}

/// Result of one dedicated checkpoint-bound v5 input runner call.
pub type ExecutionGeometryNativeInputExecutionResult<RunnerError> = Result<
    ExecutionGeometryNativeInputCompletion,
    Box<ExecutionGeometryNativeInputExecutionError<RunnerError>>,
>;

/// Failure while preparing checkpoint-exact buffers for v5 input.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInputPreparationError {
    /// Borrowed input bytes differ from the admitted checkpoint.
    Input,
    /// Native ABI preparation rejected the exact v5 input contract.
    Invocation(NativeRegionInvocationError),
    /// Borrowed memory differs from the admitted checkpoint.
    Memory,
    /// Borrowed output bytes differ from the admitted checkpoint.
    Output,
}

/// Failure from complete v5 input load/call/admit/release composition.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeInputTransactionFailure<
    MemoryError,
    RunnerError,
> {
    /// Exact prepared call could not bind to the loaded v5 executable.
    Binding {
        /// Exact binding rejection.
        error: ExecutionGeometryNativeInputBindingError,
        /// Failed cleanup retaining the ready mapping, when release also
        /// failed.
        release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// Bound v5 runner or completion admission failed.
    Execution {
        /// Exact runner/completion failure.
        error: Box<ExecutionGeometryNativeInputExecutionError<RunnerError>>,
        /// Failed cleanup retaining the ready mapping, when release also
        /// failed.
        release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// Executable mapping/lifecycle failed before runner entry.
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    /// Checkpoint-exact caller buffers failed preparation before mapping.
    Preparation(ExecutionGeometryNativeInputPreparationError),
    /// Completion committed, but final mapping release failed.
    Release {
        /// Exact committed checkpoint/outcome retained despite cleanup
        /// failure.
        completion: Box<ExecutionGeometryNativeInputCompletion>,
        /// Retryable ready executable and platform release error.
        release_failure:
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    },
}

/// Result of one complete guarded input transaction for adapter ports.
pub type ExecutionGeometryNativeInputAdapterTransactionResult<
    MemoryAdapter,
    Runner,
> = ExecutionGeometryNativeInputTransactionResult<
    <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
    <Runner as ExecutionGeometryNativeRunner>::Error,
>;

/// Result of one complete guarded v5 input transaction.
pub type ExecutionGeometryNativeInputTransactionResult<
    MemoryError,
    RunnerError,
> = Result<
    ExecutionGeometryNativeInputCompletion,
    Box<
        ExecutionGeometryNativeInputTransactionFailure<
            MemoryError,
            RunnerError,
        >,
    >,
>;

/// Verified v5 input bound to one opaque checkpoint and normative exit.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeInputAdmission {
    artifact: VerifiedExecutionGeometryInputNativeObjectArtifact,
    checkpoint: ProfileMachineState,
    expected_state: ProfileMachineState,
    load_image: VerifiedExecutionGeometryLoadImage,
    program: ExecutionGeometryRegionEffectProgram,
}

/// Prepared checkpoint-owned input bound to exact synchronized v5 code.
#[derive(Debug)]
pub struct ExecutionGeometryNativeInputBoundCall<
    'admission,
    'buffers,
    'executable,
> {
    executable: &'executable ReadyExecutionGeometryNativeExecutable,
    prepared: PreparedExecutionGeometryNativeInput<'admission, 'buffers>,
}

/// One admitted input result retaining opaque geometry authority.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeInputCompletion {
    outcome: NativeRegionInvocationOutcome,
    state: ProfileMachineState,
}

/// Borrow-scoped input ABI contract retaining checkpoint admission.
#[derive(Debug)]
pub struct PreparedExecutionGeometryNativeInput<'admission, 'buffers> {
    admission: &'admission ExecutionGeometryNativeInputAdmission,
    invocation: PreparedNativeRegionInvocation<'buffers>,
}

impl Display for ExecutionGeometryNativeInputAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => {
                f.write_str("verified v5 input artifact identity drifted")
            },
            Self::Checkpoint(error) => Display::fmt(error, f),
            Self::Identity(_error) => {
                f.write_str("v5 input identity reconstruction failed")
            },
            Self::Load(error) => Display::fmt(error, f),
            Self::NormativeReplay(error) => Display::fmt(error, f),
        }
    }
}

impl Display for ExecutionGeometryNativeInputBindingError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("v5 input executable identity differs from call")
    }
}

impl Display for ExecutionGeometryNativeInputCompletionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Invocation(error) => Display::fmt(error, f),
        }
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeInputExecutionError<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Completion(error) => Display::fmt(error, f),
            Self::Runner(error) => write!(f, "v5 input runner failed: {error}"),
        }
    }
}

impl Display for ExecutionGeometryNativeInputPreparationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Input => f.write_str("v5 input bytes differ from checkpoint"),
            Self::Invocation(error) => Display::fmt(error, f),
            Self::Memory => {
                f.write_str("v5 input memory differs from checkpoint")
            },
            Self::Output => {
                f.write_str("v5 input output differs from checkpoint")
            },
        }
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for ExecutionGeometryNativeInputTransactionFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Binding { error, .. } => {
                write!(f, "v5 input transaction binding failed: {error}")
            },
            Self::Execution { error, .. } => {
                write!(f, "v5 input transaction execution failed: {error}")
            },
            Self::Load(error) => {
                write!(f, "v5 input transaction load failed: {error}")
            },
            Self::Preparation(error) => {
                write!(f, "v5 input transaction preparation failed: {error}")
            },
            Self::Release { release_failure, .. } => {
                write!(f, "v5 input transaction {release_failure}")
            },
        }
    }
}

impl ExecutionGeometryNativeInputAdmission {
    /// Returns the exact verified v5 input artifact retained by admission.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedExecutionGeometryInputNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the normative entry checkpoint carrying opaque geometry
    /// authority.
    #[must_use]
    pub const fn checkpoint(&self) -> &ProfileMachineState {
        &self.checkpoint
    }

    /// Loads, binds, runs, admits, and releases one guarded v5 input.
    ///
    /// Preparation occurs before mapping. Every failure after a ready mapping
    /// exists attempts exact release, while cleanup failure retains the ready
    /// executable for retry. A post-commit cleanup failure also retains the
    /// normatively proven opaque-geometry completion.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInputTransactionFailure`] with exact
    /// primary failure and any retryable cleanup ownership.
    pub fn execute_transactionally<MemoryAdapter, Runner>(
        &self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeInputAdapterTransactionResult<
        MemoryAdapter,
        Runner,
    >
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeInputTransactionFailure as Failure;

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

    /// Binds verified input evidence to a normatively replayed checkpoint.
    ///
    /// Admission first checks opaque geometry/effect continuity through the
    /// interpreter handoff. Only after exact replay succeeds does it rebuild
    /// native identity and extract a relocation-free code image.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInputAdmissionError`] for checkpoint,
    /// replay, identity, artifact, or load-image disagreement.
    pub fn new(
        program: ExecutionGeometryRegionEffectProgram,
        checkpoint: ProfileMachineState,
        artifact: VerifiedExecutionGeometryInputNativeObjectArtifact,
    ) -> Result<Self, ExecutionGeometryNativeInputAdmissionError> {
        let replay = ExecutionGeometryInterpreterHandoff::new(
            program.clone(),
            checkpoint.clone(),
        )
        .map_err(ExecutionGeometryNativeInputAdmissionError::Checkpoint)?;
        let completion = replay.execute().map_err(|failure| {
            ExecutionGeometryNativeInputAdmissionError::NormativeReplay(
                failure.cause(),
            )
        })?;
        let expected_key = NativeArtifactKey::new_execution_geometry(
            &program,
            artifact.key().target().clone(),
        )
        .map_err(ExecutionGeometryNativeInputAdmissionError::Identity)?;
        if artifact.key() != &expected_key {
            return Err(
                ExecutionGeometryNativeInputAdmissionError::ArtifactIdentity,
            );
        }
        let load_image =
            VerifiedExecutionGeometryLoadImage::from_input(&artifact)
                .map_err(ExecutionGeometryNativeInputAdmissionError::Load)?;
        Ok(Self {
            artifact,
            checkpoint,
            expected_state: completion.state().clone(),
            load_image,
            program,
        })
    }

    /// Prepares exact checkpoint-owned buffers for guarded v5 input.
    ///
    /// The checkpoint owns the complete immutable input bytes and its logical
    /// cursor. Byte-versus-EOF interpretation is delegated to the common ABI
    /// effect validator after exact checkpoint buffer equality is established.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInputPreparationError`] when any caller
    /// buffer drifts or ABI preparation rejects the exact input effect.
    pub fn prepare<'admission, 'buffers>(
        &'admission self,
        buffers: NativeRegionBuffers<'buffers>,
    ) -> Result<
        PreparedExecutionGeometryNativeInput<'admission, 'buffers>,
        ExecutionGeometryNativeInputPreparationError,
    > {
        let (memory, input, output) = buffers.into_parts();
        if input != self.checkpoint.io().input() {
            return Err(ExecutionGeometryNativeInputPreparationError::Input);
        }
        if memory != self.checkpoint.memory() {
            return Err(ExecutionGeometryNativeInputPreparationError::Memory);
        }
        if output != self.checkpoint.io().output() {
            return Err(ExecutionGeometryNativeInputPreparationError::Output);
        }
        let invocation =
            PreparedNativeRegionInvocation::new_execution_geometry_input(
                &self.program,
                memory,
                input,
                output,
            )
            .map_err(
                ExecutionGeometryNativeInputPreparationError::Invocation,
            )?;
        Ok(PreparedExecutionGeometryNativeInput {
            admission: self,
            invocation,
        })
    }

    /// Returns the exact v5 input IR retained by admission.
    #[must_use]
    pub const fn program(&self) -> &ExecutionGeometryRegionEffectProgram {
        &self.program
    }
}

impl ExecutionGeometryNativeInputBoundCall<'_, '_, '_> {
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
    /// Returns [`ExecutionGeometryNativeInputCompletionError`] when the
    /// completed transition violates exact prepared evidence.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeInputCompletion,
        ExecutionGeometryNativeInputCompletionError,
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
    /// Returns [`ExecutionGeometryNativeInputExecutionError`] for runner or
    /// completion failure.
    pub fn execute<Runner>(
        self,
        runner: &mut Runner,
    ) -> ExecutionGeometryNativeInputExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let Self { executable, prepared } = self;
        let PreparedExecutionGeometryNativeInput { admission, invocation } =
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
                    ExecutionGeometryNativeInputExecutionError::Runner(
                        Box::new(error),
                    ),
                ));
            },
        };
        let outcome =
            runner_invocation.complete(raw_status).map_err(|error| {
                use ExecutionGeometryNativeInputCompletionError as Completion;
                use ExecutionGeometryNativeInputExecutionError as Execution;
                Box::new(Execution::Completion(Completion::Invocation(error)))
            })?;
        Ok(ExecutionGeometryNativeInputCompletion {
            outcome,
            state: completion_state(admission, outcome),
        })
    }
}

impl ExecutionGeometryNativeInputCompletion {
    /// Returns the exact admitted native call outcome.
    #[must_use]
    pub const fn outcome(&self) -> NativeRegionInvocationOutcome {
        self.outcome
    }

    /// Returns the exact checkpoint after applied input or preserved miss.
    #[must_use]
    pub const fn state(&self) -> &ProfileMachineState {
        &self.state
    }
}

impl<'admission, 'buffers>
    PreparedExecutionGeometryNativeInput<'admission, 'buffers>
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
    /// Returns [`ExecutionGeometryNativeInputBindingError`] when the executable
    /// carries any different verified load image.
    pub fn bind_executable<'executable>(
        self,
        executable: &'executable ReadyExecutionGeometryNativeExecutable,
    ) -> Result<
        ExecutionGeometryNativeInputBoundCall<
            'admission,
            'buffers,
            'executable,
        >,
        ExecutionGeometryNativeInputBindingError,
    > {
        let Self { admission, invocation } = self;
        if admission.load_image() != executable.image() {
            let error = InputBindingError::ExecutableIdentity;
            invocation.abort();
            return Err(error);
        }
        Ok(ExecutionGeometryNativeInputBoundCall {
            executable,
            prepared: Self { admission, invocation },
        })
    }

    /// Admits raw native status and selects the already proven input
    /// checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeInputCompletionError`] when exact ABI
    /// completion fails.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeInputCompletion,
        ExecutionGeometryNativeInputCompletionError,
    > {
        let outcome = self
            .invocation
            .complete(raw_status)
            .map_err(ExecutionGeometryNativeInputCompletionError::Invocation)?;
        Ok(ExecutionGeometryNativeInputCompletion {
            outcome,
            state: completion_state(self.admission, outcome),
        })
    }
}

fn completion_state(
    admission: &ExecutionGeometryNativeInputAdmission,
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
