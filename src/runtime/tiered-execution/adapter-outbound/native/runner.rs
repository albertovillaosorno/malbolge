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
//   - Safe orchestration of one loaded, bound, executed, admitted native call.
// - Must-Not:
//   - Implement the unsafe foreign-call mechanism or retain borrowed ABI state.
// - Allows:
//   - Inputs: prepared verified calls, executable-memory adapters, and runners.
//   - Outputs: admitted outcomes or phase-tagged failures with release retry.
//   - Side effects: only those explicitly performed by supplied adapters.
// - Split-When:
//   - Concrete architecture call shims gain independent platform ownership.
// - Merge-When:
//   - One platform adapter owns loading, calling, and release transactionally.
// - Summary:
//   - Loads, binds, runs, admits, and releases one verified native effect.
// - Description:
//   - Restores caller buffers on runner or admission failure before cleanup.
// - Usage:
//   - Supply external memory and runner implementations to the safe core.
// - Defaults:
//   - Committed outcomes survive release failure; mappings remain retryable.
//

//! Safe orchestration around an externally implemented native call runner.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::invocation::{
    NativeExecutableInvocationBindingError, NativeRegionInvocationError,
    NativeRegionInvocationOutcome, PreparedExecutionGeometryNativeInvocation,
    PreparedNativeExecutableInvocation,
    PreparedRegisterMaskedHaltFetchInvocation,
    PreparedRegisterMaskedNativeInvocation,
    PreparedRegisterMaskedNonGraphicalInvocation,
    PreparedRegisterMaskedNonGraphicalNativeInvocation,
    PreparedVerifiedDirectInvocation,
    PreparedVerifiedExecutionGeometryInvocation, VerifiedDirectInvocationError,
    VerifiedRegisterMaskedInvocationError,
};
use super::lifecycle::{
    NativeExecutableReleaseRequest, ReadyExecutionGeometryNativeExecutable,
    ReadyNativeExecutable, ReadyRegisterMaskedNativeExecutable,
    ReadyRegisterMaskedNonGraphicalNativeExecutable,
};
use super::platform::{
    NativeExecutableLoadFailure, NativeExecutableMemoryAdapter,
    NativeExecutableReleaseFailure,
    RegisterMaskedNativeExecutableReleaseFailure,
    RegisterMaskedNonGraphicalNativeExecutableReleaseFailure,
    load_native_executable, load_register_masked_native_executable,
    load_register_masked_non_graphical_native_executable,
    release_native_executable, release_register_masked_native_executable,
    release_register_masked_non_graphical_native_executable,
};

/// Ordered phase whose native execution transaction failed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableExecutionPhase {
    /// Exact ready-image to prepared-call binding.
    Bind,
    /// Raw status and caller-visible state admission.
    Complete,
    /// Executable image loading and lifecycle admission.
    Load,
    /// Final executable mapping release after a committed outcome.
    Release,
    /// External runner call.
    Run,
}

#[derive(Debug, Eq, PartialEq)]
enum NativeExecutableExecutionFailureCause<MemoryError, RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(Box<VerifiedDirectInvocationError>),
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    Release(NativeRegionInvocationOutcome),
    Runner(Box<RunnerError>),
}

/// Phase-tagged execution failure retaining cleanup and committed-state
/// evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableExecutionFailure<MemoryError, RunnerError> {
    cause: NativeExecutableExecutionFailureCause<MemoryError, RunnerError>,
    phase: NativeExecutableExecutionPhase,
    release_failure: Option<Box<NativeExecutableReleaseFailure<MemoryError>>>,
    release_request: Option<NativeExecutableReleaseRequest>,
}

/// Result of one complete verified native load, call, admission, and release.
pub type NativeExecutableExecutionResult<MemoryError, RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<NativeExecutableExecutionFailure<MemoryError, RunnerError>>,
>;

type NativeExecutableAdapterExecutionResult<MemoryAdapter, Runner> =
    NativeExecutableExecutionResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as NativeExecutableRunner>::Error,
    >;

#[derive(Debug, Eq, PartialEq)]
enum NativeExecutableCallFailure<RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(Box<VerifiedDirectInvocationError>),
    Runner(Box<RunnerError>),
}

#[derive(Debug, Eq, PartialEq)]
enum ExecutionGeometryNativeCallFailure<RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(NativeRegionInvocationError),
    Runner(Box<RunnerError>),
}

/// Failure while executing one verified v5 call against a loaded mapping.
#[derive(Debug, Eq, PartialEq)]
pub struct ExecutionGeometryLoadedExecutionFailure<RunnerError> {
    cause: ExecutionGeometryNativeCallFailure<RunnerError>,
}

/// Result of one loaded verified-v5 call.
pub type ExecutionGeometryLoadedExecutionResult<RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<ExecutionGeometryLoadedExecutionFailure<RunnerError>>,
>;

#[derive(Debug, Eq, PartialEq)]
enum RegisterMaskedNativeCallFailure<RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Runner(Box<RunnerError>),
}

/// Failure while executing one verified register-masked v6 call.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedLoadedExecutionFailure<RunnerError> {
    cause: RegisterMaskedNativeCallFailure<RunnerError>,
}

/// Result of one loaded verified register-masked v6 call.
pub type RegisterMaskedLoadedExecutionResult<RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<RegisterMaskedLoadedExecutionFailure<RunnerError>>,
>;

#[derive(Debug, Eq, PartialEq)]
enum RegisterMaskedNonGraphicalNativeCallFailure<RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Runner(Box<RunnerError>),
}

/// Failure while executing one loaded non-graphical register-masked v6 call.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNonGraphicalLoadedExecutionFailure<RunnerError> {
    cause: RegisterMaskedNonGraphicalNativeCallFailure<RunnerError>,
}

/// Result of one loaded verified non-graphical register-masked v6 call.
pub type RegisterMaskedNonGraphicalLoadedExecutionResult<RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<RegisterMaskedNonGraphicalLoadedExecutionFailure<RunnerError>>,
>;

#[derive(Debug, Eq, PartialEq)]
enum NonGraphicalNativeExecutionFailureCause<MemoryError, RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    Release(NativeRegionInvocationOutcome),
    Runner(Box<RunnerError>),
}

/// Phase-tagged non-graphical v6 transaction failure with cleanup evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNonGraphicalNativeExecutionFailure<
    MemoryError,
    RunnerError,
> {
    cause: NonGraphicalNativeExecutionFailureCause<MemoryError, RunnerError>,
    phase: NativeExecutableExecutionPhase,
    release_failure: Option<
        Box<
            RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<
                MemoryError,
            >,
        >,
    >,
    release_request: Option<NativeExecutableReleaseRequest>,
}

/// Result of one complete non-graphical v6 load/call/release transaction.
pub type RegisterMaskedNonGraphicalNativeExecutionResult<
    MemoryError,
    RunnerError,
> = Result<
    NativeRegionInvocationOutcome,
    Box<
        RegisterMaskedNonGraphicalNativeExecutionFailure<
            MemoryError,
            RunnerError,
        >,
    >,
>;

type NonGraphicalNativeAdapterExecutionResult<MemoryAdapter, Runner> =
    RegisterMaskedNonGraphicalNativeExecutionResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as RegisterMaskedNonGraphicalNativeRunner>::Error,
    >;

type RegisterMaskedNonGraphicalNativeCallResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    RegisterMaskedNonGraphicalNativeCallFailure<
        <Runner as RegisterMaskedNonGraphicalNativeRunner>::Error,
    >,
>;

#[derive(Debug, Eq, PartialEq)]
enum RegisterMaskedNativeExecutionFailureCause<MemoryError, RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    Release(NativeRegionInvocationOutcome),
    Runner(Box<RunnerError>),
}

/// Phase-tagged v6 transaction failure retaining cleanup/commit evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNativeExecutionFailure<MemoryError, RunnerError> {
    cause: RegisterMaskedNativeExecutionFailureCause<MemoryError, RunnerError>,
    phase: NativeExecutableExecutionPhase,
    release_failure:
        Option<Box<RegisterMaskedNativeExecutableReleaseFailure<MemoryError>>>,
    release_request: Option<NativeExecutableReleaseRequest>,
}

/// Result of one complete register-masked v6 load/call/release transaction.
pub type RegisterMaskedNativeExecutionResult<MemoryError, RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<RegisterMaskedNativeExecutionFailure<MemoryError, RunnerError>>,
>;

type RegisterMaskedNativeAdapterExecutionResult<MemoryAdapter, Runner> =
    RegisterMaskedNativeExecutionResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as RegisterMaskedNativeRunner>::Error,
    >;

type RegisterMaskedNativeCallResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    RegisterMaskedNativeCallFailure<
        <Runner as RegisterMaskedNativeRunner>::Error,
    >,
>;

/// Failure while executing against one already loaded exact mapping.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeLoadedExecutionFailure<RunnerError> {
    cause: NativeExecutableCallFailure<RunnerError>,
}

/// Result of binding, running, and admitting one already loaded executable.
pub type NativeLoadedExecutionResult<RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<NativeLoadedExecutionFailure<RunnerError>>,
>;

#[derive(Debug)]
struct LoadedNativeExecution<'artifact, 'buffers> {
    executable: ReadyNativeExecutable,
    prepared: PreparedVerifiedDirectInvocation<'artifact, 'buffers>,
    release_request: NativeExecutableReleaseRequest,
}

type LoadedNativeExecutionResult<'artifact, 'buffers, MemoryAdapter, Runner> =
    Result<
        LoadedNativeExecution<'artifact, 'buffers>,
        Box<
            NativeExecutableExecutionFailure<
                <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
                <Runner as NativeExecutableRunner>::Error,
            >,
        >,
    >;

type NativeExecutableCallResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    NativeExecutableCallFailure<<Runner as NativeExecutableRunner>::Error>,
>;

/// Caller-owned implementation of one checkpoint-bound v5 entrypoint call.
///
/// This port is deliberately separate from [`NativeExecutableRunner`]. The
/// runner can inspect only a view that the crate constructs after explicit
/// geometry authority and synchronized executable identity have been bound.
pub trait ExecutionGeometryNativeRunner {
    /// Stable runner-specific failure.
    type Error;

    /// Calls one exact synchronized v5 executable and returns its raw ABI
    /// status.
    ///
    /// The implementation may inspect entry address, mapping identity, and the
    /// mutable ABI state pointer. It must not retain borrowed state after
    /// return.
    ///
    /// # Errors
    ///
    /// Returns the runner's stable call failure.
    fn run(
        &mut self,
        invocation: &mut PreparedExecutionGeometryNativeInvocation<'_, '_>,
    ) -> Result<i32, Self::Error>;
}

/// Caller-owned implementation of one exact register-masked v6 call.
///
/// This port is distinct from legacy and explicit-geometry runners. It receives
/// only a view constructed after complete v6 image/executable identity binding.
pub trait RegisterMaskedNativeRunner {
    /// Stable runner-specific failure.
    type Error;

    /// Calls one exact synchronized register-masked v6 executable.
    ///
    /// The implementation may inspect entry address, mapping identity, and the
    /// mutable ABI state pointer. It must not retain borrowed state after
    /// return.
    ///
    /// # Errors
    ///
    /// Returns the runner's stable call failure.
    fn run(
        &mut self,
        invocation: &mut PreparedRegisterMaskedNativeInvocation<'_, '_>,
    ) -> Result<i32, Self::Error>;
}

/// Caller-owned implementation of one exact non-graphical v6 call.
///
/// This port receives only a view constructed after complete non-graphical v6
/// image/executable identity binding and cannot accept halt-only call views.
pub trait RegisterMaskedNonGraphicalNativeRunner {
    /// Stable runner-specific failure.
    type Error;

    /// Calls one exact synchronized non-graphical v6 executable.
    ///
    /// The implementation may inspect entry address, mapping identity, and the
    /// mutable ABI state pointer. It must not retain borrowed state after
    /// return.
    ///
    /// # Errors
    ///
    /// Returns the runner's stable call failure.
    fn run(
        &mut self,
        invocation: &mut PreparedRegisterMaskedNonGraphicalNativeInvocation<
            '_,
            '_,
        >,
    ) -> Result<i32, Self::Error>;
}

/// Caller-owned implementation of the actual native entrypoint call.
pub trait NativeExecutableRunner {
    /// Stable runner-specific failure.
    type Error;

    /// Calls one exact synchronized executable and returns its raw ABI status.
    ///
    /// The implementation may inspect the entry address, mapping identity, and
    /// mutable ABI state pointer through `invocation`. It must not retain any
    /// borrowed pointer or reference after returning.
    ///
    /// # Errors
    ///
    /// Returns the runner's stable call failure.
    fn run(
        &mut self,
        invocation: &mut PreparedNativeExecutableInvocation<'_, '_, '_>,
    ) -> Result<i32, Self::Error>;
}

impl<RunnerError> ExecutionGeometryLoadedExecutionFailure<RunnerError> {
    /// Returns exact ready-image binding failure, when identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            ExecutionGeometryNativeCallFailure::Binding(error) => Some(*error),
            ExecutionGeometryNativeCallFailure::Completion(_)
            | ExecutionGeometryNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns v5 result-admission failure after the runner returned.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<NativeRegionInvocationError> {
        match &self.cause {
            ExecutionGeometryNativeCallFailure::Completion(error) => {
                Some(*error)
            },
            ExecutionGeometryNativeCallFailure::Binding(_)
            | ExecutionGeometryNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns the exact call phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        match &self.cause {
            ExecutionGeometryNativeCallFailure::Binding(_) => {
                NativeExecutableExecutionPhase::Bind
            },
            ExecutionGeometryNativeCallFailure::Completion(_) => {
                NativeExecutableExecutionPhase::Complete
            },
            ExecutionGeometryNativeCallFailure::Runner(_) => {
                NativeExecutableExecutionPhase::Run
            },
        }
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            ExecutionGeometryNativeCallFailure::Runner(error) => Some(error),
            ExecutionGeometryNativeCallFailure::Binding(_)
            | ExecutionGeometryNativeCallFailure::Completion(_) => None,
        }
    }
}

impl<RunnerError> RegisterMaskedLoadedExecutionFailure<RunnerError> {
    /// Returns exact ready-image binding failure, when v6 identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            RegisterMaskedNativeCallFailure::Binding(error) => Some(*error),
            RegisterMaskedNativeCallFailure::Completion(_)
            | RegisterMaskedNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns v6 result-admission failure after the runner returned.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            RegisterMaskedNativeCallFailure::Completion(error) => Some(*error),
            RegisterMaskedNativeCallFailure::Binding(_)
            | RegisterMaskedNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns the exact call phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        match &self.cause {
            RegisterMaskedNativeCallFailure::Binding(_) => {
                NativeExecutableExecutionPhase::Bind
            },
            RegisterMaskedNativeCallFailure::Completion(_) => {
                NativeExecutableExecutionPhase::Complete
            },
            RegisterMaskedNativeCallFailure::Runner(_) => {
                NativeExecutableExecutionPhase::Run
            },
        }
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            RegisterMaskedNativeCallFailure::Runner(error) => Some(error),
            RegisterMaskedNativeCallFailure::Binding(_)
            | RegisterMaskedNativeCallFailure::Completion(_) => None,
        }
    }
}

impl<RunnerError>
    RegisterMaskedNonGraphicalLoadedExecutionFailure<RunnerError>
{
    /// Returns exact ready-image binding failure, when v6 identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            RegisterMaskedNonGraphicalNativeCallFailure::Binding(error) => {
                Some(*error)
            },
            RegisterMaskedNonGraphicalNativeCallFailure::Completion(_)
            | RegisterMaskedNonGraphicalNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns non-graphical v6 result-admission failure.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            RegisterMaskedNonGraphicalNativeCallFailure::Completion(error) => {
                Some(*error)
            },
            RegisterMaskedNonGraphicalNativeCallFailure::Binding(_)
            | RegisterMaskedNonGraphicalNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns the exact call phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        match &self.cause {
            RegisterMaskedNonGraphicalNativeCallFailure::Binding(_) => {
                NativeExecutableExecutionPhase::Bind
            },
            RegisterMaskedNonGraphicalNativeCallFailure::Completion(_) => {
                NativeExecutableExecutionPhase::Complete
            },
            RegisterMaskedNonGraphicalNativeCallFailure::Runner(_) => {
                NativeExecutableExecutionPhase::Run
            },
        }
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            RegisterMaskedNonGraphicalNativeCallFailure::Runner(error) => {
                Some(error)
            },
            RegisterMaskedNonGraphicalNativeCallFailure::Binding(_)
            | RegisterMaskedNonGraphicalNativeCallFailure::Completion(_) => {
                None
            },
        }
    }
}

impl<RunnerError> NativeLoadedExecutionFailure<RunnerError> {
    /// Returns ready-image binding failure, when identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            NativeExecutableCallFailure::Binding(error) => Some(*error),
            NativeExecutableCallFailure::Completion(_)
            | NativeExecutableCallFailure::Runner(_) => None,
        }
    }

    /// Returns result-admission failure after the runner returned.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<&VerifiedDirectInvocationError> {
        match &self.cause {
            NativeExecutableCallFailure::Completion(error) => Some(error),
            NativeExecutableCallFailure::Binding(_)
            | NativeExecutableCallFailure::Runner(_) => None,
        }
    }

    /// Returns the exact call phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        self.cause.phase()
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            NativeExecutableCallFailure::Runner(error) => Some(error),
            NativeExecutableCallFailure::Binding(_)
            | NativeExecutableCallFailure::Completion(_) => None,
        }
    }
}

impl<RunnerError> RegisterMaskedNativeCallFailure<RunnerError> {
    fn into_cause<MemoryError>(
        self,
    ) -> RegisterMaskedNativeExecutionFailureCause<MemoryError, RunnerError>
    {
        match self {
            Self::Binding(error) => {
                RegisterMaskedNativeExecutionFailureCause::Binding(error)
            },
            Self::Completion(error) => {
                RegisterMaskedNativeExecutionFailureCause::Completion(error)
            },
            Self::Runner(error) => {
                RegisterMaskedNativeExecutionFailureCause::Runner(error)
            },
        }
    }

    const fn phase(&self) -> NativeExecutableExecutionPhase {
        match self {
            Self::Binding(_) => NativeExecutableExecutionPhase::Bind,
            Self::Completion(_) => NativeExecutableExecutionPhase::Complete,
            Self::Runner(_) => NativeExecutableExecutionPhase::Run,
        }
    }
}

impl<RunnerError> RegisterMaskedNonGraphicalNativeCallFailure<RunnerError> {
    fn into_cause<MemoryError>(
        self,
    ) -> NonGraphicalNativeExecutionFailureCause<MemoryError, RunnerError> {
        match self {
            Self::Binding(error) => {
                NonGraphicalNativeExecutionFailureCause::Binding(error)
            },
            Self::Completion(error) => {
                NonGraphicalNativeExecutionFailureCause::Completion(error)
            },
            Self::Runner(error) => {
                NonGraphicalNativeExecutionFailureCause::Runner(error)
            },
        }
    }

    const fn phase(&self) -> NativeExecutableExecutionPhase {
        match self {
            Self::Binding(_) => NativeExecutableExecutionPhase::Bind,
            Self::Completion(_) => NativeExecutableExecutionPhase::Complete,
            Self::Runner(_) => NativeExecutableExecutionPhase::Run,
        }
    }
}

impl<RunnerError> NativeExecutableCallFailure<RunnerError> {
    fn into_cause<MemoryError>(
        self,
    ) -> NativeExecutableExecutionFailureCause<MemoryError, RunnerError> {
        match self {
            Self::Binding(error) => {
                NativeExecutableExecutionFailureCause::Binding(error)
            },
            Self::Completion(error) => {
                NativeExecutableExecutionFailureCause::Completion(error)
            },
            Self::Runner(error) => {
                NativeExecutableExecutionFailureCause::Runner(error)
            },
        }
    }

    const fn phase(&self) -> NativeExecutableExecutionPhase {
        match self {
            Self::Binding(_) => NativeExecutableExecutionPhase::Bind,
            Self::Completion(_) => NativeExecutableExecutionPhase::Complete,
            Self::Runner(_) => NativeExecutableExecutionPhase::Run,
        }
    }
}

impl<MemoryError, RunnerError>
    RegisterMaskedNonGraphicalNativeExecutionFailure<MemoryError, RunnerError>
{
    /// Returns ready-image binding failure, when exact v6 identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            NonGraphicalNativeExecutionFailureCause::Binding(error) => {
                Some(*error)
            },
            NonGraphicalNativeExecutionFailureCause::Completion(_)
            | NonGraphicalNativeExecutionFailureCause::Load(_)
            | NonGraphicalNativeExecutionFailureCause::Release(_)
            | NonGraphicalNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns the outcome committed before final release failed.
    #[must_use]
    pub const fn committed_outcome(
        &self,
    ) -> Option<NativeRegionInvocationOutcome> {
        match &self.cause {
            NonGraphicalNativeExecutionFailureCause::Release(outcome) => {
                Some(*outcome)
            },
            NonGraphicalNativeExecutionFailureCause::Binding(_)
            | NonGraphicalNativeExecutionFailureCause::Completion(_)
            | NonGraphicalNativeExecutionFailureCause::Load(_)
            | NonGraphicalNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns result-admission failure, when native state drifted.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            NonGraphicalNativeExecutionFailureCause::Completion(error) => {
                Some(*error)
            },
            NonGraphicalNativeExecutionFailureCause::Binding(_)
            | NonGraphicalNativeExecutionFailureCause::Load(_)
            | NonGraphicalNativeExecutionFailureCause::Release(_)
            | NonGraphicalNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Consumes this failure and returns retryable mapping cleanup.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<
        RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<MemoryError>,
    > {
        self.release_failure.map(|failure| *failure)
    }

    /// Returns executable loading failure, when no ready image was produced.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&NativeExecutableLoadFailure<MemoryError>> {
        match &self.cause {
            NonGraphicalNativeExecutionFailureCause::Load(error) => Some(error),
            NonGraphicalNativeExecutionFailureCause::Binding(_)
            | NonGraphicalNativeExecutionFailureCause::Completion(_)
            | NonGraphicalNativeExecutionFailureCause::Release(_)
            | NonGraphicalNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns the exact transaction phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        self.phase
    }

    /// Returns failed cleanup with the ready executable retained for retry.
    #[must_use]
    pub const fn release_failure(
        &self,
    ) -> Option<
        &RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<MemoryError>,
    > {
        match &self.release_failure {
            Some(error) => Some(error),
            None => None,
        }
    }

    /// Returns the exact mapping release request attempted after loading.
    #[must_use]
    pub const fn release_request(
        &self,
    ) -> Option<NativeExecutableReleaseRequest> {
        self.release_request
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            NonGraphicalNativeExecutionFailureCause::Runner(error) => {
                Some(error)
            },
            NonGraphicalNativeExecutionFailureCause::Binding(_)
            | NonGraphicalNativeExecutionFailureCause::Completion(_)
            | NonGraphicalNativeExecutionFailureCause::Load(_)
            | NonGraphicalNativeExecutionFailureCause::Release(_) => None,
        }
    }
}

impl<MemoryError, RunnerError>
    RegisterMaskedNativeExecutionFailure<MemoryError, RunnerError>
{
    /// Returns ready-image binding failure, when exact v6 identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            RegisterMaskedNativeExecutionFailureCause::Binding(error) => {
                Some(*error)
            },
            RegisterMaskedNativeExecutionFailureCause::Completion(_)
            | RegisterMaskedNativeExecutionFailureCause::Load(_)
            | RegisterMaskedNativeExecutionFailureCause::Release(_)
            | RegisterMaskedNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns the outcome committed before final release failed.
    #[must_use]
    pub const fn committed_outcome(
        &self,
    ) -> Option<NativeRegionInvocationOutcome> {
        match &self.cause {
            RegisterMaskedNativeExecutionFailureCause::Release(outcome) => {
                Some(*outcome)
            },
            RegisterMaskedNativeExecutionFailureCause::Binding(_)
            | RegisterMaskedNativeExecutionFailureCause::Completion(_)
            | RegisterMaskedNativeExecutionFailureCause::Load(_)
            | RegisterMaskedNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns v6 result-admission failure, when native state drifted.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            RegisterMaskedNativeExecutionFailureCause::Completion(error) => {
                Some(*error)
            },
            RegisterMaskedNativeExecutionFailureCause::Binding(_)
            | RegisterMaskedNativeExecutionFailureCause::Load(_)
            | RegisterMaskedNativeExecutionFailureCause::Release(_)
            | RegisterMaskedNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Consumes this failure and returns retryable v6 mapping cleanup.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<RegisterMaskedNativeExecutableReleaseFailure<MemoryError>> {
        self.release_failure.map(|failure| *failure)
    }

    /// Returns executable loading failure, when no ready v6 image was produced.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&NativeExecutableLoadFailure<MemoryError>> {
        match &self.cause {
            RegisterMaskedNativeExecutionFailureCause::Load(error) => {
                Some(error)
            },
            RegisterMaskedNativeExecutionFailureCause::Binding(_)
            | RegisterMaskedNativeExecutionFailureCause::Completion(_)
            | RegisterMaskedNativeExecutionFailureCause::Release(_)
            | RegisterMaskedNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns the exact transaction phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        self.phase
    }

    /// Returns failed v6 cleanup with the ready executable retained for retry.
    #[must_use]
    pub const fn release_failure(
        &self,
    ) -> Option<&RegisterMaskedNativeExecutableReleaseFailure<MemoryError>>
    {
        match &self.release_failure {
            Some(error) => Some(error),
            None => None,
        }
    }

    /// Returns the exact mapping release request attempted after loading.
    #[must_use]
    pub const fn release_request(
        &self,
    ) -> Option<NativeExecutableReleaseRequest> {
        self.release_request
    }

    /// Returns external runner failure, when the v6 call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            RegisterMaskedNativeExecutionFailureCause::Runner(error) => {
                Some(error)
            },
            RegisterMaskedNativeExecutionFailureCause::Binding(_)
            | RegisterMaskedNativeExecutionFailureCause::Completion(_)
            | RegisterMaskedNativeExecutionFailureCause::Load(_)
            | RegisterMaskedNativeExecutionFailureCause::Release(_) => None,
        }
    }
}

impl<MemoryError, RunnerError>
    NativeExecutableExecutionFailure<MemoryError, RunnerError>
{
    /// Returns ready-image binding failure, when exact identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            NativeExecutableExecutionFailureCause::Binding(error) => {
                Some(*error)
            },
            NativeExecutableExecutionFailureCause::Completion(_)
            | NativeExecutableExecutionFailureCause::Load(_)
            | NativeExecutableExecutionFailureCause::Release(_)
            | NativeExecutableExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns the outcome committed before final release failed.
    #[must_use]
    pub const fn committed_outcome(
        &self,
    ) -> Option<NativeRegionInvocationOutcome> {
        match &self.cause {
            NativeExecutableExecutionFailureCause::Release(outcome) => {
                Some(*outcome)
            },
            NativeExecutableExecutionFailureCause::Binding(_)
            | NativeExecutableExecutionFailureCause::Completion(_)
            | NativeExecutableExecutionFailureCause::Load(_)
            | NativeExecutableExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns result-admission failure, when native state drifted.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<&VerifiedDirectInvocationError> {
        match &self.cause {
            NativeExecutableExecutionFailureCause::Completion(error) => {
                Some(error)
            },
            NativeExecutableExecutionFailureCause::Binding(_)
            | NativeExecutableExecutionFailureCause::Load(_)
            | NativeExecutableExecutionFailureCause::Release(_)
            | NativeExecutableExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Consumes this failure and returns retryable mapping cleanup.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<NativeExecutableReleaseFailure<MemoryError>> {
        self.release_failure.map(|failure| *failure)
    }

    /// Returns executable loading failure, when no ready image was produced.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&NativeExecutableLoadFailure<MemoryError>> {
        match &self.cause {
            NativeExecutableExecutionFailureCause::Load(error) => Some(error),
            NativeExecutableExecutionFailureCause::Binding(_)
            | NativeExecutableExecutionFailureCause::Completion(_)
            | NativeExecutableExecutionFailureCause::Release(_)
            | NativeExecutableExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns the exact transaction phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        self.phase
    }

    /// Returns failed mapping cleanup with executable retained for retry.
    #[must_use]
    pub const fn release_failure(
        &self,
    ) -> Option<&NativeExecutableReleaseFailure<MemoryError>> {
        match &self.release_failure {
            Some(error) => Some(error),
            None => None,
        }
    }

    /// Returns the exact mapping release request attempted after loading.
    #[must_use]
    pub const fn release_request(
        &self,
    ) -> Option<NativeExecutableReleaseRequest> {
        self.release_request
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            NativeExecutableExecutionFailureCause::Runner(error) => Some(error),
            NativeExecutableExecutionFailureCause::Binding(_)
            | NativeExecutableExecutionFailureCause::Completion(_)
            | NativeExecutableExecutionFailureCause::Load(_)
            | NativeExecutableExecutionFailureCause::Release(_) => None,
        }
    }
}

impl<RunnerError: Display> Display
    for ExecutionGeometryLoadedExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "loaded v5 execution failed during {}: ", self.phase())?;
        match &self.cause {
            ExecutionGeometryNativeCallFailure::Binding(error) => {
                write!(f, "binding: {error}")
            },
            ExecutionGeometryNativeCallFailure::Completion(error) => {
                write!(f, "completion: {error}")
            },
            ExecutionGeometryNativeCallFailure::Runner(error) => {
                write!(f, "runner: {error}")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for RegisterMaskedLoadedExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "loaded v6 execution failed during {}: ", self.phase())?;
        match &self.cause {
            RegisterMaskedNativeCallFailure::Binding(error) => {
                write!(f, "binding: {error}")
            },
            RegisterMaskedNativeCallFailure::Completion(error) => {
                write!(f, "completion: {error}")
            },
            RegisterMaskedNativeCallFailure::Runner(error) => {
                write!(f, "runner: {error}")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for NativeLoadedExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "loaded native execution failed during {}: ",
            self.phase()
        )?;
        match &self.cause {
            NativeExecutableCallFailure::Binding(error) => {
                write!(f, "binding: {error}")
            },
            NativeExecutableCallFailure::Completion(error) => {
                write!(f, "completion: {error}")
            },
            NativeExecutableCallFailure::Runner(error) => {
                write!(f, "runner: {error}")
            },
        }
    }
}

impl Display for NativeExecutableExecutionPhase {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Bind => "bind",
            Self::Complete => "complete",
            Self::Load => "load",
            Self::Release => "release",
            Self::Run => "run",
        })
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for RegisterMaskedNativeExecutionFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v6 native execution failed during {}: ", self.phase)?;
        match &self.cause {
            RegisterMaskedNativeExecutionFailureCause::Binding(error) => {
                write!(f, "binding: {error}")?;
            },
            RegisterMaskedNativeExecutionFailureCause::Completion(error) => {
                write!(f, "completion: {error}")?;
            },
            RegisterMaskedNativeExecutionFailureCause::Load(error) => {
                write!(f, "loading: {error}")?;
            },
            RegisterMaskedNativeExecutionFailureCause::Release(outcome) => {
                let label = match outcome {
                    NativeRegionInvocationOutcome::Applied(_) => "applied",
                    NativeRegionInvocationOutcome::GuardMiss => "guard-miss",
                };
                write!(f, "committed {label} outcome could not release")?;
            },
            RegisterMaskedNativeExecutionFailureCause::Runner(error) => {
                write!(f, "runner: {error}")?;
            },
        }
        if let Some(release_failure) = &self.release_failure {
            write!(f, "; {release_failure}")?;
        }
        Ok(())
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for NativeExecutableExecutionFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "native executable execution failed during {}: ",
            self.phase
        )?;
        match &self.cause {
            NativeExecutableExecutionFailureCause::Binding(error) => {
                write!(f, "binding: {error}")?;
            },
            NativeExecutableExecutionFailureCause::Completion(error) => {
                write!(f, "completion: {error}")?;
            },
            NativeExecutableExecutionFailureCause::Load(error) => {
                write!(f, "loading: {error}")?;
            },
            NativeExecutableExecutionFailureCause::Release(outcome) => {
                let label = match outcome {
                    NativeRegionInvocationOutcome::Applied(_) => "applied",
                    NativeRegionInvocationOutcome::GuardMiss => "guard-miss",
                };
                write!(f, "committed {label} outcome could not release")?;
            },
            NativeExecutableExecutionFailureCause::Runner(error) => {
                write!(f, "runner: {error}")?;
            },
        }
        if let Some(release_failure) = &self.release_failure {
            write!(f, "; {release_failure}")?;
        }
        Ok(())
    }
}

/// Binds, runs, and admits one verified-v5 call against a loaded mapping.
///
/// Runner failure aborts and restores the complete current-step entry snapshot.
/// Completion rejection performs the same restoration through the invocation
/// contract. This function neither loads nor releases executable memory.
///
/// # Errors
///
/// Returns [`ExecutionGeometryLoadedExecutionFailure`] for binding, runner, or
/// completion failure.
pub fn execute_loaded_verified_execution_geometry_native<Runner>(
    runner: &mut Runner,
    executable: &ReadyExecutionGeometryNativeExecutable,
    prepared: PreparedVerifiedExecutionGeometryInvocation<'_, '_>,
) -> ExecutionGeometryLoadedExecutionResult<Runner::Error>
where
    Runner: ExecutionGeometryNativeRunner,
{
    let mut bound = prepared.bind_executable(executable).map_err(|error| {
        Box::new(ExecutionGeometryLoadedExecutionFailure {
            cause: ExecutionGeometryNativeCallFailure::Binding(error),
        })
    })?;
    let raw_status = match runner.run(&mut bound) {
        Ok(status) => status,
        Err(error) => {
            bound.abort();
            return Err(Box::new(ExecutionGeometryLoadedExecutionFailure {
                cause: ExecutionGeometryNativeCallFailure::Runner(Box::new(
                    error,
                )),
            }));
        },
    };
    bound.complete(raw_status).map_err(|error| {
        Box::new(ExecutionGeometryLoadedExecutionFailure {
            cause: ExecutionGeometryNativeCallFailure::Completion(error),
        })
    })
}

/// Binds, runs, and admits one non-graphical v6 call against a loaded mapping.
///
/// Runner failure restores the complete rebased entry snapshot. Completion
/// rejection performs the same restoration through the invocation contract.
/// This function neither loads nor releases executable memory.
///
/// # Errors
///
/// Returns [`RegisterMaskedNonGraphicalLoadedExecutionFailure`] for binding,
/// runner, or completion failure.
pub fn execute_loaded_verified_register_masked_non_graphical_native<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedNonGraphicalNativeExecutable,
    prepared: PreparedRegisterMaskedNonGraphicalInvocation<'_, '_>,
) -> RegisterMaskedNonGraphicalLoadedExecutionResult<Runner::Error>
where
    Runner: RegisterMaskedNonGraphicalNativeRunner,
{
    run_register_masked_non_graphical_prepared(runner, executable, prepared)
        .map_err(|cause| {
            Box::new(RegisterMaskedNonGraphicalLoadedExecutionFailure { cause })
        })
}

/// Binds, runs, and admits one register-masked v6 call against a loaded
/// mapping.
///
/// Runner failure restores the complete rebased entry snapshot. Completion
/// rejection performs the same restoration through the v6 invocation contract.
/// This function neither loads nor releases executable memory.
///
/// # Errors
///
/// Returns [`RegisterMaskedLoadedExecutionFailure`] for binding, runner, or
/// completion failure.
pub fn execute_loaded_verified_register_masked_native<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedNativeExecutable,
    prepared: PreparedRegisterMaskedHaltFetchInvocation<'_, '_>,
) -> RegisterMaskedLoadedExecutionResult<Runner::Error>
where
    Runner: RegisterMaskedNativeRunner,
{
    run_register_masked_prepared(runner, executable, prepared).map_err(
        |cause| Box::new(RegisterMaskedLoadedExecutionFailure { cause }),
    )
}

fn non_graphical_load_failure<MemoryError, RunnerError>(
    error: NativeExecutableLoadFailure<MemoryError>,
) -> RegisterMaskedNonGraphicalNativeExecutionFailure<MemoryError, RunnerError>
{
    let release_request = error.release_request();
    RegisterMaskedNonGraphicalNativeExecutionFailure {
        cause: NonGraphicalNativeExecutionFailureCause::Load(Box::new(error)),
        phase: NativeExecutableExecutionPhase::Load,
        release_failure: None,
        release_request,
    }
}

/// Loads, binds, runs, admits, and releases one non-graphical v6 call.
///
/// Load/call failures restore the prepared rebased snapshot and attempt exact
/// mapping cleanup. A release failure after a committed result retains both the
/// outcome and exact ready executable for retry.
///
/// # Errors
///
/// Returns [`RegisterMaskedNonGraphicalNativeExecutionFailure`] with
/// phase-specific primary and cleanup evidence.
pub fn execute_verified_register_masked_non_graphical_native<
    MemoryAdapter,
    Runner,
>(
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    prepared: PreparedRegisterMaskedNonGraphicalInvocation<'_, '_>,
) -> NonGraphicalNativeAdapterExecutionResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: RegisterMaskedNonGraphicalNativeRunner,
{
    let executable = match load_register_masked_non_graphical_native_executable(
        memory_adapter,
        prepared.load_image(),
    ) {
        Ok(executable) => executable,
        Err(error) => {
            prepared.abort();
            return Err(Box::new(non_graphical_load_failure(error)));
        },
    };
    let release_request = executable.release_request();
    let outcome = match run_register_masked_non_graphical_prepared(
        runner,
        &executable,
        prepared,
    ) {
        Ok(outcome) => outcome,
        Err(error) => {
            let phase = error.phase();
            let release_failure =
                release_register_masked_non_graphical_native_executable(
                    memory_adapter,
                    executable,
                )
                .err()
                .map(Box::new);
            return Err(Box::new(
                RegisterMaskedNonGraphicalNativeExecutionFailure {
                    cause: error.into_cause(),
                    phase,
                    release_failure,
                    release_request: Some(release_request),
                },
            ));
        },
    };
    match release_register_masked_non_graphical_native_executable(
        memory_adapter,
        executable,
    ) {
        Ok(()) => Ok(outcome),
        Err(release_failure) => {
            Err(Box::new(RegisterMaskedNonGraphicalNativeExecutionFailure {
                cause: NonGraphicalNativeExecutionFailureCause::Release(
                    outcome,
                ),
                phase: NativeExecutableExecutionPhase::Release,
                release_failure: Some(Box::new(release_failure)),
                release_request: Some(release_request),
            }))
        },
    }
}

/// Loads, binds, runs, admits, and releases one register-masked v6 call.
///
/// Load/call failures restore the prepared rebased snapshot and attempt exact
/// mapping cleanup. A release failure after a committed result retains both the
/// outcome and exact ready v6 executable for retry.
///
/// # Errors
///
/// Returns [`RegisterMaskedNativeExecutionFailure`] with phase-specific primary
/// and cleanup evidence.
pub fn execute_verified_register_masked_native<MemoryAdapter, Runner>(
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    prepared: PreparedRegisterMaskedHaltFetchInvocation<'_, '_>,
) -> RegisterMaskedNativeAdapterExecutionResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: RegisterMaskedNativeRunner,
{
    let executable = match load_register_masked_native_executable(
        memory_adapter,
        prepared.load_image(),
    ) {
        Ok(executable) => executable,
        Err(error) => {
            prepared.abort();
            let release_request = error.release_request();
            return Err(Box::new(RegisterMaskedNativeExecutionFailure {
                cause: RegisterMaskedNativeExecutionFailureCause::Load(
                    Box::new(error),
                ),
                phase: NativeExecutableExecutionPhase::Load,
                release_failure: None,
                release_request,
            }));
        },
    };
    let release_request = executable.release_request();
    let outcome =
        match run_register_masked_prepared(runner, &executable, prepared) {
            Ok(outcome) => outcome,
            Err(error) => {
                let phase = error.phase();
                let release_failure =
                    release_register_masked_native_executable(
                        memory_adapter,
                        executable,
                    )
                    .err()
                    .map(Box::new);
                return Err(Box::new(RegisterMaskedNativeExecutionFailure {
                    cause: error.into_cause(),
                    phase,
                    release_failure,
                    release_request: Some(release_request),
                }));
            },
        };
    match release_register_masked_native_executable(memory_adapter, executable)
    {
        Ok(()) => Ok(outcome),
        Err(release_failure) => {
            Err(Box::new(RegisterMaskedNativeExecutionFailure {
                cause: RegisterMaskedNativeExecutionFailureCause::Release(
                    outcome,
                ),
                phase: NativeExecutableExecutionPhase::Release,
                release_failure: Some(Box::new(release_failure)),
                release_request: Some(release_request),
            }))
        },
    }
}

fn run_register_masked_non_graphical_prepared<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedNonGraphicalNativeExecutable,
    prepared: PreparedRegisterMaskedNonGraphicalInvocation<'_, '_>,
) -> RegisterMaskedNonGraphicalNativeCallResult<Runner>
where
    Runner: RegisterMaskedNonGraphicalNativeRunner,
{
    let mut bound = prepared
        .bind_executable(executable)
        .map_err(RegisterMaskedNonGraphicalNativeCallFailure::Binding)?;
    let raw_status = match runner.run(&mut bound) {
        Ok(status) => status,
        Err(error) => {
            bound.abort();
            return Err(RegisterMaskedNonGraphicalNativeCallFailure::Runner(
                Box::new(error),
            ));
        },
    };
    bound
        .complete(raw_status)
        .map_err(RegisterMaskedNonGraphicalNativeCallFailure::Completion)
}

fn run_register_masked_prepared<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedNativeExecutable,
    prepared: PreparedRegisterMaskedHaltFetchInvocation<'_, '_>,
) -> RegisterMaskedNativeCallResult<Runner>
where
    Runner: RegisterMaskedNativeRunner,
{
    let mut bound = prepared
        .bind_executable(executable)
        .map_err(RegisterMaskedNativeCallFailure::Binding)?;
    let raw_status = match runner.run(&mut bound) {
        Ok(status) => status,
        Err(error) => {
            bound.abort();
            return Err(RegisterMaskedNativeCallFailure::Runner(Box::new(
                error,
            )));
        },
    };
    bound
        .complete(raw_status)
        .map_err(RegisterMaskedNativeCallFailure::Completion)
}

/// Binds, runs, and admits one call against an already loaded executable.
///
/// Runner failure aborts and restores the complete current-step entry snapshot.
/// Completion rejection performs the same restoration through the invocation
/// contract. This function neither loads nor releases executable memory.
///
/// # Errors
///
/// Returns [`NativeLoadedExecutionFailure`] for binding, runner, or completion
/// failure.
pub fn execute_loaded_verified_native<Runner>(
    runner: &mut Runner,
    executable: &ReadyNativeExecutable,
    prepared_call: PreparedVerifiedDirectInvocation<'_, '_>,
) -> NativeLoadedExecutionResult<Runner::Error>
where
    Runner: NativeExecutableRunner,
{
    run_prepared(runner, executable, prepared_call)
        .map_err(|cause| Box::new(NativeLoadedExecutionFailure { cause }))
}

/// Loads, binds, runs, admits, and releases one verified direct invocation.
///
/// Runner failure aborts the prepared call and restores all caller-visible
/// buffers before release. Completion failure already performs the same
/// rollback. A release failure after successful completion retains both the
/// committed outcome and the ready executable for exact retry.
///
/// # Errors
///
/// Returns [`NativeExecutableExecutionFailure`] with phase-specific primary and
/// cleanup evidence.
pub fn execute_verified_native<MemoryAdapter, Runner>(
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    prepared_call: PreparedVerifiedDirectInvocation<'_, '_>,
) -> NativeExecutableAdapterExecutionResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: NativeExecutableRunner,
{
    let LoadedNativeExecution {
        executable,
        prepared,
        release_request,
    } = load_prepared::<MemoryAdapter, Runner>(memory_adapter, prepared_call)?;
    let outcome = match run_prepared(runner, &executable, prepared) {
        Ok(outcome) => outcome,
        Err(error) => {
            return Err(Box::new(fail_after_ready(
                memory_adapter,
                executable,
                release_request,
                error,
            )));
        },
    };
    release_committed(memory_adapter, executable, release_request, outcome)
}

fn fail_after_ready<MemoryAdapter, RunnerError>(
    memory_adapter: &mut MemoryAdapter,
    executable: ReadyNativeExecutable,
    release_request: NativeExecutableReleaseRequest,
    error: NativeExecutableCallFailure<RunnerError>,
) -> NativeExecutableExecutionFailure<MemoryAdapter::Error, RunnerError>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
{
    let phase = error.phase();
    NativeExecutableExecutionFailure {
        cause: error.into_cause(),
        phase,
        release_failure: release_native_executable(memory_adapter, executable)
            .err()
            .map(Box::new),
        release_request: Some(release_request),
    }
}

fn load_prepared<'artifact, 'buffers, MemoryAdapter, Runner>(
    memory_adapter: &mut MemoryAdapter,
    prepared: PreparedVerifiedDirectInvocation<'artifact, 'buffers>,
) -> LoadedNativeExecutionResult<'artifact, 'buffers, MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: NativeExecutableRunner,
{
    let executable =
        match load_native_executable(memory_adapter, prepared.load_image()) {
            Ok(executable) => executable,
            Err(error) => {
                prepared.abort();
                let release_request = error.release_request();
                return Err(Box::new(NativeExecutableExecutionFailure {
                    cause: NativeExecutableExecutionFailureCause::Load(
                        Box::new(error),
                    ),
                    phase: NativeExecutableExecutionPhase::Load,
                    release_failure: None,
                    release_request,
                }));
            },
        };
    let release_request = executable.release_request();
    Ok(LoadedNativeExecution {
        executable,
        prepared,
        release_request,
    })
}

fn release_committed<MemoryAdapter, RunnerError>(
    memory_adapter: &mut MemoryAdapter,
    executable: ReadyNativeExecutable,
    release_request: NativeExecutableReleaseRequest,
    outcome: NativeRegionInvocationOutcome,
) -> NativeExecutableExecutionResult<MemoryAdapter::Error, RunnerError>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
{
    match release_native_executable(memory_adapter, executable) {
        Ok(()) => Ok(outcome),
        Err(release_failure) => {
            Err(Box::new(NativeExecutableExecutionFailure {
                cause: NativeExecutableExecutionFailureCause::Release(outcome),
                phase: NativeExecutableExecutionPhase::Release,
                release_failure: Some(Box::new(release_failure)),
                release_request: Some(release_request),
            }))
        },
    }
}

fn run_prepared<Runner>(
    runner: &mut Runner,
    executable: &ReadyNativeExecutable,
    prepared: PreparedVerifiedDirectInvocation<'_, '_>,
) -> NativeExecutableCallResult<Runner>
where
    Runner: NativeExecutableRunner,
{
    let mut invocation = prepared
        .bind_executable(executable)
        .map_err(NativeExecutableCallFailure::Binding)?;
    let raw_status = match runner.run(&mut invocation) {
        Ok(raw_status) => raw_status,
        Err(error) => {
            invocation.abort();
            return Err(NativeExecutableCallFailure::Runner(Box::new(error)));
        },
    };
    invocation.complete(raw_status).map_err(|error| {
        NativeExecutableCallFailure::Completion(Box::new(error))
    })
}
