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
//   - Checkpoint-bound admission and execution of verified v5 rotate.
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
//   - Executes only normatively replayed explicit-geometry rotate.
// - Description:
//   - Binds v5 identity to opaque state and exact rotate/data-write transition.
// - Usage:
//   - Admit first, then transact or manually prepare/bind/execute.
// - Defaults:
//   - Geometry, identity, buffer, runner, completion, or cleanup drift fails
//   - closed with entry rollback where mutation was possible.
//

//! Checkpoint-bound native execution for explicit-geometry rotate.

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
    VerifiedExecutionGeometryRotateNativeObjectArtifact,
    load_execution_geometry_native_executable,
    release_execution_geometry_native_executable,
};
use crate::geometry_interpreter_handoff::{
    ExecutionGeometryHandoffAdmissionError,
    ExecutionGeometryHandoffExecutionCause,
    ExecutionGeometryInterpreterHandoff,
};

type RotateBindingError = ExecutionGeometryNativeRotateBindingError;

/// Failure before one verified v5 rotate can retain checkpoint authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeRotateAdmissionError {
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

/// Failure while binding one prepared v5 rotate to synchronized code.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeRotateBindingError {
    /// Synchronized executable image differs from checkpoint-bound admission.
    ExecutableIdentity,
}

/// Failure while admitting one completed v5 rotate ABI transition.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeRotateCompletionError {
    /// Native result disagreed with the exact prepared transition.
    Invocation(NativeRegionInvocationError),
}

/// Failure after a checkpoint-bound v5 rotate enters the runner.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeRotateExecutionError<RunnerError> {
    /// Returned status or caller-visible state failed exact completion.
    Completion(ExecutionGeometryNativeRotateCompletionError),
    /// External runner failed before returning a raw ABI status.
    Runner(Box<RunnerError>),
}

/// Result of one dedicated checkpoint-bound v5 rotate runner call.
pub type ExecutionGeometryNativeRotateExecutionResult<RunnerError> = Result<
    ExecutionGeometryNativeRotateCompletion,
    Box<ExecutionGeometryNativeRotateExecutionError<RunnerError>>,
>;

/// Failure while preparing checkpoint-exact buffers for v5 rotate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeRotatePreparationError {
    /// Borrowed input bytes differ from the admitted checkpoint.
    Input,
    /// Native ABI preparation rejected the exact v5 rotate contract.
    Invocation(NativeRegionInvocationError),
    /// Borrowed memory differs from the admitted checkpoint.
    Memory,
    /// Borrowed output bytes differ from the admitted checkpoint.
    Output,
}

/// Failure from complete v5 rotate load/call/admit/release composition.
#[derive(Debug, Eq, PartialEq)]
pub enum ExecutionGeometryNativeRotateTransactionFailure<
    MemoryError,
    RunnerError,
> {
    /// Exact prepared call could not bind to the loaded v5 executable.
    Binding {
        /// Exact binding rejection.
        error: ExecutionGeometryNativeRotateBindingError,
        /// Failed cleanup retaining the ready mapping, when release also
        /// failed.
        release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// Bound v5 runner or completion admission failed.
    Execution {
        /// Exact runner/completion failure.
        error: Box<ExecutionGeometryNativeRotateExecutionError<RunnerError>>,
        /// Failed cleanup retaining the ready mapping, when release also
        /// failed.
        release_failure: Option<
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
        >,
    },
    /// Executable mapping/lifecycle failed before runner entry.
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    /// Checkpoint-exact caller buffers failed preparation before mapping.
    Preparation(ExecutionGeometryNativeRotatePreparationError),
    /// Completion committed, but final mapping release failed.
    Release {
        /// Exact committed checkpoint/outcome retained despite cleanup
        /// failure.
        completion: Box<ExecutionGeometryNativeRotateCompletion>,
        /// Retryable ready executable and platform release error.
        release_failure:
            Box<ExecutionGeometryNativeExecutableReleaseFailure<MemoryError>>,
    },
}

/// Result of one complete guarded rotate transaction for adapter ports.
pub type ExecutionGeometryNativeRotateAdapterTransactionResult<
    MemoryAdapter,
    Runner,
> = ExecutionGeometryNativeRotateTransactionResult<
    <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
    <Runner as ExecutionGeometryNativeRunner>::Error,
>;

/// Result of one complete guarded v5 rotate transaction.
pub type ExecutionGeometryNativeRotateTransactionResult<
    MemoryError,
    RunnerError,
> = Result<
    ExecutionGeometryNativeRotateCompletion,
    Box<
        ExecutionGeometryNativeRotateTransactionFailure<
            MemoryError,
            RunnerError,
        >,
    >,
>;

/// Verified v5 rotate bound to one opaque checkpoint and normative exit.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeRotateAdmission {
    artifact: VerifiedExecutionGeometryRotateNativeObjectArtifact,
    checkpoint: ProfileMachineState,
    expected_state: ProfileMachineState,
    load_image: VerifiedExecutionGeometryLoadImage,
    program: ExecutionGeometryRegionEffectProgram,
}

/// Prepared checkpoint-owned rotate bound to exact synchronized v5 code.
#[derive(Debug)]
pub struct ExecutionGeometryNativeRotateBoundCall<
    'admission,
    'buffers,
    'executable,
> {
    executable: &'executable ReadyExecutionGeometryNativeExecutable,
    prepared: PreparedExecutionGeometryNativeRotate<'admission, 'buffers>,
}

/// One admitted rotate result retaining opaque geometry authority.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryNativeRotateCompletion {
    outcome: NativeRegionInvocationOutcome,
    state: ProfileMachineState,
}

/// Borrow-scoped rotate ABI contract retaining checkpoint admission.
#[derive(Debug)]
pub struct PreparedExecutionGeometryNativeRotate<'admission, 'buffers> {
    admission: &'admission ExecutionGeometryNativeRotateAdmission,
    invocation: PreparedNativeRegionInvocation<'buffers>,
}

impl Display for ExecutionGeometryNativeRotateAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ArtifactIdentity => {
                f.write_str("v5 rotate artifact identity differs from program")
            },
            Self::Checkpoint(error) => Display::fmt(error, f),
            Self::Identity(_error) => {
                f.write_str("v5 rotate identity reconstruction failed")
            },
            Self::Load(error) => Display::fmt(error, f),
            Self::NormativeReplay(error) => Display::fmt(error, f),
        }
    }
}

impl Display for ExecutionGeometryNativeRotateBindingError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str("v5 rotate executable identity differs from call")
    }
}

impl Display for ExecutionGeometryNativeRotateCompletionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Invocation(error) => Display::fmt(error, f),
        }
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryNativeRotateExecutionError<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Completion(error) => Display::fmt(error, f),
            Self::Runner(error) => {
                write!(f, "v5 rotate runner failed: {error}")
            },
        }
    }
}

impl Display for ExecutionGeometryNativeRotatePreparationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Input => {
                f.write_str("v5 rotate input differs from checkpoint")
            },
            Self::Invocation(error) => Display::fmt(error, f),
            Self::Memory => {
                f.write_str("v5 rotate memory differs from checkpoint")
            },
            Self::Output => {
                f.write_str("v5 rotate output differs from checkpoint")
            },
        }
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for ExecutionGeometryNativeRotateTransactionFailure<
        MemoryError,
        RunnerError,
    >
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Binding { error, .. } => {
                write!(f, "v5 rotate transaction binding failed: {error}")
            },
            Self::Execution { error, .. } => {
                write!(f, "v5 rotate transaction execution failed: {error}")
            },
            Self::Load(error) => {
                write!(f, "v5 rotate transaction load failed: {error}")
            },
            Self::Preparation(error) => {
                write!(f, "v5 rotate transaction preparation failed: {error}")
            },
            Self::Release { release_failure, .. } => {
                write!(f, "v5 rotate transaction {release_failure}")
            },
        }
    }
}

impl ExecutionGeometryNativeRotateAdmission {
    /// Returns the exact verified v5 rotate artifact retained by
    /// admission.
    #[must_use]
    pub const fn artifact(
        &self,
    ) -> &VerifiedExecutionGeometryRotateNativeObjectArtifact {
        &self.artifact
    }

    /// Returns the normative entry checkpoint carrying opaque geometry
    /// authority.
    #[must_use]
    pub const fn checkpoint(&self) -> &ProfileMachineState {
        &self.checkpoint
    }

    /// Loads, binds, runs, admits, and releases one guarded v5 rotate.
    ///
    /// Preparation occurs before mapping. Every failure after a ready mapping
    /// exists attempts exact release, while cleanup failure retains the ready
    /// executable for retry. A post-commit cleanup failure also retains the
    /// normatively proven opaque-geometry completion.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeRotateTransactionFailure`] with
    /// exact primary failure and any retryable cleanup ownership.
    pub fn execute_transactionally<MemoryAdapter, Runner>(
        &self,
        memory_adapter: &mut MemoryAdapter,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ExecutionGeometryNativeRotateAdapterTransactionResult<
        MemoryAdapter,
        Runner,
    >
    where
        MemoryAdapter: NativeExecutableMemoryAdapter,
        Runner: ExecutionGeometryNativeRunner,
    {
        use ExecutionGeometryNativeRotateTransactionFailure as Failure;

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

    /// Binds verified rotate evidence to a normatively replayed
    /// checkpoint.
    ///
    /// Admission first checks opaque geometry/live-ins, then executes one
    /// cloned checkpoint through the normative interpreter and requires
    /// exact v5 reprojection. Native identity and load-image extraction
    /// happen only after that independent semantic replay succeeds.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeRotateAdmissionError`] for
    /// checkpoint, replay, identity, or load-image disagreement.
    pub fn new(
        program: ExecutionGeometryRegionEffectProgram,
        checkpoint: ProfileMachineState,
        artifact: VerifiedExecutionGeometryRotateNativeObjectArtifact,
    ) -> Result<Self, ExecutionGeometryNativeRotateAdmissionError> {
        let replay = ExecutionGeometryInterpreterHandoff::new(
            program.clone(),
            checkpoint.clone(),
        )
        .map_err(ExecutionGeometryNativeRotateAdmissionError::Checkpoint)?;
        let completion = replay.execute().map_err(|failure| {
            ExecutionGeometryNativeRotateAdmissionError::NormativeReplay(
                failure.cause(),
            )
        })?;
        let expected_key = NativeArtifactKey::new_execution_geometry(
            &program,
            artifact.key().target().clone(),
        )
        .map_err(ExecutionGeometryNativeRotateAdmissionError::Identity)?;
        if artifact.key() != &expected_key {
            use ExecutionGeometryNativeRotateAdmissionError as Error;
            return Err(Error::ArtifactIdentity);
        }
        let load_image =
            VerifiedExecutionGeometryLoadImage::from_rotate(&artifact)
                .map_err(ExecutionGeometryNativeRotateAdmissionError::Load)?;
        Ok(Self {
            artifact,
            checkpoint,
            expected_state: completion.state().clone(),
            load_image,
            program,
        })
    }

    /// Prepares exact checkpoint-owned buffers for guarded v5 rotate.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeRotatePreparationError`] when any
    /// caller buffer drifts or ABI preparation rejects the exact effect.
    pub fn prepare<'admission, 'buffers>(
        &'admission self,
        buffers: NativeRegionBuffers<'buffers>,
    ) -> Result<
        PreparedExecutionGeometryNativeRotate<'admission, 'buffers>,
        ExecutionGeometryNativeRotatePreparationError,
    > {
        let (memory, input, output) = buffers.into_parts();
        if input != self.checkpoint.io().input() {
            return Err(ExecutionGeometryNativeRotatePreparationError::Input);
        }
        if memory != self.checkpoint.memory() {
            return Err(ExecutionGeometryNativeRotatePreparationError::Memory);
        }
        if output != self.checkpoint.io().output() {
            return Err(ExecutionGeometryNativeRotatePreparationError::Output);
        }
        let invocation =
            PreparedNativeRegionInvocation::new_execution_geometry_rotate(
                &self.program,
                memory,
                input,
                output,
            )
            .map_err(|error| {
                ExecutionGeometryNativeRotatePreparationError::Invocation(error)
            })?;
        Ok(PreparedExecutionGeometryNativeRotate {
            admission: self,
            invocation,
        })
    }

    /// Returns the exact v5 program whose rotate was normatively
    /// replayed.
    #[must_use]
    pub const fn program(&self) -> &ExecutionGeometryRegionEffectProgram {
        &self.program
    }
}

impl ExecutionGeometryNativeRotateBoundCall<'_, '_, '_> {
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
    /// Returns [`ExecutionGeometryNativeRotateCompletionError`] when the
    /// completed transition violates exact prepared evidence.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeRotateCompletion,
        ExecutionGeometryNativeRotateCompletionError,
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
    /// Returns [`ExecutionGeometryNativeRotateExecutionError`] for runner
    /// or completion failure.
    pub fn execute<Runner>(
        self,
        runner: &mut Runner,
    ) -> ExecutionGeometryNativeRotateExecutionResult<Runner::Error>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let Self { executable, prepared } = self;
        let PreparedExecutionGeometryNativeRotate { admission, invocation } =
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
                    ExecutionGeometryNativeRotateExecutionError::Runner(
                        Box::new(error),
                    ),
                ));
            },
        };
        let outcome =
            runner_invocation.complete(raw_status).map_err(|error| {
                use ExecutionGeometryNativeRotateCompletionError as Completion;
                use ExecutionGeometryNativeRotateExecutionError as Execution;
                Box::new(Execution::Completion(Completion::Invocation(error)))
            })?;
        Ok(ExecutionGeometryNativeRotateCompletion {
            outcome,
            state: completion_state(admission, outcome),
        })
    }
}

impl ExecutionGeometryNativeRotateCompletion {
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
    PreparedExecutionGeometryNativeRotate<'admission, 'buffers>
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
    /// Returns [`ExecutionGeometryNativeRotateBindingError`] when the
    /// executable carries any different verified load image.
    pub fn bind_executable<'executable>(
        self,
        executable: &'executable ReadyExecutionGeometryNativeExecutable,
    ) -> Result<
        ExecutionGeometryNativeRotateBoundCall<
            'admission,
            'buffers,
            'executable,
        >,
        ExecutionGeometryNativeRotateBindingError,
    > {
        let Self { admission, invocation } = self;
        if admission.load_image() != executable.image() {
            let error = RotateBindingError::ExecutableIdentity;
            invocation.abort();
            return Err(error);
        }
        Ok(ExecutionGeometryNativeRotateBoundCall {
            executable,
            prepared: Self { admission, invocation },
        })
    }

    /// Admits raw native status and selects the already proven output
    /// checkpoint.
    ///
    /// # Errors
    ///
    /// Returns [`ExecutionGeometryNativeRotateCompletionError`] when exact
    /// ABI completion fails.
    pub fn complete(
        self,
        raw_status: i32,
    ) -> Result<
        ExecutionGeometryNativeRotateCompletion,
        ExecutionGeometryNativeRotateCompletionError,
    > {
        let outcome = self.invocation.complete(raw_status).map_err(
            ExecutionGeometryNativeRotateCompletionError::Invocation,
        )?;
        Ok(ExecutionGeometryNativeRotateCompletion {
            outcome,
            state: completion_state(self.admission, outcome),
        })
    }
}

fn completion_state(
    admission: &ExecutionGeometryNativeRotateAdmission,
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
