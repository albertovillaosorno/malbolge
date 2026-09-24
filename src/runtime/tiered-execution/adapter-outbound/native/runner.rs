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
    DirectFusedInvocationError, NativeExecutableInvocationBindingError,
    NativeRegionInvocationError, NativeRegionInvocationOutcome,
    PreparedDirectFusedInvocation, PreparedDirectFusedNativeInvocation,
    PreparedExecutionGeometryNativeInvocation,
    PreparedNativeExecutableInvocation, PreparedRegisterMaskedCrazyInvocation,
    PreparedRegisterMaskedCrazyNativeInvocation,
    PreparedRegisterMaskedHaltFetchInvocation,
    PreparedRegisterMaskedNativeInvocation,
    PreparedRegisterMaskedNoOperationHaltInvocation,
    PreparedRegisterMaskedNoOperationHaltNativeInvocation,
    PreparedRegisterMaskedNoOperationInvocation,
    PreparedRegisterMaskedNoOperationNativeInvocation,
    PreparedRegisterMaskedNoOperationPairInvocation,
    PreparedRegisterMaskedNoOperationPairNativeInvocation,
    PreparedRegisterMaskedNoOperationRotateInvocation,
    PreparedRegisterMaskedNoOperationRotateNativeInvocation,
    PreparedRegisterMaskedNonGraphicalInvocation,
    PreparedRegisterMaskedNonGraphicalNativeInvocation,
    PreparedRegisterMaskedOutputInvocation,
    PreparedRegisterMaskedOutputNativeInvocation,
    PreparedRegisterMaskedRotateInvocation,
    PreparedRegisterMaskedRotateNativeInvocation,
    PreparedVerifiedDirectInvocation,
    PreparedVerifiedExecutionGeometryInvocation, VerifiedDirectInvocationError,
    VerifiedRegisterMaskedInvocationError,
};
use super::lifecycle::{
    NativeExecutableReleaseRequest, ReadyDirectFusedNativeExecutable,
    ReadyExecutionGeometryNativeExecutable, ReadyNativeExecutable,
    ReadyRegisterMaskedCrazyNativeExecutable,
    ReadyRegisterMaskedNativeExecutable,
    ReadyRegisterMaskedNoOperationHaltNativeExecutable,
    ReadyRegisterMaskedNoOperationNativeExecutable,
    ReadyRegisterMaskedNoOperationPairNativeExecutable,
    ReadyRegisterMaskedNoOperationRotateNativeExecutable,
    ReadyRegisterMaskedNonGraphicalNativeExecutable,
    ReadyRegisterMaskedOutputNativeExecutable,
    ReadyRegisterMaskedRotateNativeExecutable,
};
use super::platform::{
    DirectFusedNativeExecutableReleaseFailure, NativeExecutableLoadFailure,
    NativeExecutableMemoryAdapter, NativeExecutableReleaseFailure,
    RegisterMaskedCrazyNativeExecutableReleaseFailure as CrazyReleaseFailure,
    RegisterMaskedNativeExecutableReleaseFailure,
    RegisterMaskedNoOperationNativeExecutableReleaseFailure,
    RegisterMaskedNonGraphicalNativeExecutableReleaseFailure,
    RegisterMaskedOutputNativeExecutableReleaseFailure as OutputReleaseFailure,
    RegisterMaskedRotateNativeExecutableReleaseFailure as RotateReleaseFailure,
    load_direct_fused_native_executable, load_native_executable,
    load_register_masked_crazy_native_executable,
    load_register_masked_native_executable,
    load_register_masked_no_operation_native_executable,
    load_register_masked_non_graphical_native_executable,
    load_register_masked_output_native_executable,
    load_register_masked_rotate_native_executable,
    release_direct_fused_native_executable, release_native_executable,
    release_register_masked_crazy_native_executable,
    release_register_masked_native_executable,
    release_register_masked_no_operation_native_executable,
    release_register_masked_non_graphical_native_executable,
    release_register_masked_output_native_executable,
    release_register_masked_rotate_native_executable,
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

/// Result of one complete call when one host owns memory and runner authority.
pub type NativeExecutableHostExecutionResult<Host> =
    NativeExecutableExecutionResult<
        <Host as NativeExecutableMemoryAdapter>::Error,
        <Host as NativeExecutableRunner>::Error,
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
enum DirectFusedNativeCallFailure<RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(DirectFusedInvocationError),
    Runner(Box<RunnerError>),
}

/// Failure while executing one verified fused call against a loaded mapping.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedLoadedExecutionFailure<RunnerError> {
    cause: DirectFusedNativeCallFailure<RunnerError>,
}

/// Result of one loaded verified fused whole-region call.
pub type DirectFusedLoadedExecutionResult<RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<DirectFusedLoadedExecutionFailure<RunnerError>>,
>;

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
enum RegisterMaskedCrazyNativeCallFailure<RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Runner(Box<RunnerError>),
}

/// Failure while executing one loaded v6 Crazy call.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedCrazyLoadedExecutionFailure<RunnerError> {
    cause: RegisterMaskedCrazyNativeCallFailure<RunnerError>,
}

/// Result of one loaded verified v6 Crazy call.
pub type RegisterMaskedCrazyLoadedExecutionResult<RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<RegisterMaskedCrazyLoadedExecutionFailure<RunnerError>>,
>;

#[derive(Debug, Eq, PartialEq)]
enum RegisterMaskedOutputNativeCallFailure<RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Runner(Box<RunnerError>),
}

/// Failure while executing one loaded v6 Output call.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedOutputLoadedExecutionFailure<RunnerError> {
    cause: RegisterMaskedOutputNativeCallFailure<RunnerError>,
}

/// Result of one loaded verified v6 Output call.
pub type RegisterMaskedOutputLoadedExecutionResult<RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<RegisterMaskedOutputLoadedExecutionFailure<RunnerError>>,
>;

#[derive(Debug, Eq, PartialEq)]
enum RegisterMaskedNoOperationNativeCallFailure<RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Runner(Box<RunnerError>),
}

/// Failure while executing one loaded v6 no-operation call.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNoOperationLoadedExecutionFailure<RunnerError> {
    cause: RegisterMaskedNoOperationNativeCallFailure<RunnerError>,
}

/// Result of one loaded verified v6 no-operation call.
pub type RegisterMaskedNoOperationLoadedExecutionResult<RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<RegisterMaskedNoOperationLoadedExecutionFailure<RunnerError>>,
>;

#[derive(Debug, Eq, PartialEq)]
enum RegisterMaskedNoOperationHaltNativeCallFailure<RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Runner(Box<RunnerError>),
}

/// Failure while executing one loaded collapsed v6 no-op/halt call.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNoOperationHaltLoadedExecutionFailure<RunnerError> {
    cause: RegisterMaskedNoOperationHaltNativeCallFailure<RunnerError>,
}

/// Result of one loaded verified collapsed v6 no-op/halt call.
pub type RegisterMaskedNoOperationHaltLoadedExecutionResult<RunnerError> =
    Result<
        NativeRegionInvocationOutcome,
        Box<RegisterMaskedNoOperationHaltLoadedExecutionFailure<RunnerError>>,
    >;

#[derive(Debug, Eq, PartialEq)]
enum RegisterMaskedNoOperationPairNativeCallFailure<RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Runner(Box<RunnerError>),
}

/// Failure while executing one loaded collapsed v6 no-operation pair call.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNoOperationPairLoadedExecutionFailure<RunnerError> {
    cause: RegisterMaskedNoOperationPairNativeCallFailure<RunnerError>,
}

/// Result of one loaded verified collapsed v6 no-operation pair call.
pub type RegisterMaskedNoOperationPairLoadedExecutionResult<RunnerError> =
    Result<
        NativeRegionInvocationOutcome,
        Box<RegisterMaskedNoOperationPairLoadedExecutionFailure<RunnerError>>,
    >;

#[derive(Debug, Eq, PartialEq)]
enum RegisterMaskedNoOperationRotateNativeCallFailure<RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Runner(Box<RunnerError>),
}

/// Failure while executing one loaded collapsed v6 no-operation/rotate call.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNoOperationRotateLoadedExecutionFailure<RunnerError> {
    cause: RegisterMaskedNoOperationRotateNativeCallFailure<RunnerError>,
}

/// Result of one loaded verified collapsed v6 no-operation/rotate call.
pub type RegisterMaskedNoOperationRotateLoadedExecutionResult<RunnerError> =
    Result<
        NativeRegionInvocationOutcome,
        Box<RegisterMaskedNoOperationRotateLoadedExecutionFailure<RunnerError>>,
    >;

#[derive(Debug, Eq, PartialEq)]
enum RegisterMaskedRotateNativeCallFailure<RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Runner(Box<RunnerError>),
}

/// Failure while executing one loaded v6 rotate call.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedRotateLoadedExecutionFailure<RunnerError> {
    cause: RegisterMaskedRotateNativeCallFailure<RunnerError>,
}

/// Result of one loaded verified v6 rotate call.
pub type RegisterMaskedRotateLoadedExecutionResult<RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<RegisterMaskedRotateLoadedExecutionFailure<RunnerError>>,
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
enum DirectFusedNativeExecutionFailureCause<MemoryError, RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(DirectFusedInvocationError),
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    Release(NativeRegionInvocationOutcome),
    Runner(Box<RunnerError>),
}

/// Phase-tagged fused transaction failure with cleanup and commit evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct DirectFusedNativeExecutionFailure<MemoryError, RunnerError> {
    cause: DirectFusedNativeExecutionFailureCause<MemoryError, RunnerError>,
    phase: NativeExecutableExecutionPhase,
    release_failure:
        Option<Box<DirectFusedNativeExecutableReleaseFailure<MemoryError>>>,
    release_request: Option<NativeExecutableReleaseRequest>,
}

/// Result of one complete fused load/call/admission/release transaction.
pub type DirectFusedNativeExecutionResult<MemoryError, RunnerError> = Result<
    NativeRegionInvocationOutcome,
    Box<DirectFusedNativeExecutionFailure<MemoryError, RunnerError>>,
>;

type DirectFusedNativeAdapterExecutionResult<MemoryAdapter, Runner> =
    DirectFusedNativeExecutionResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as DirectFusedNativeRunner>::Error,
    >;

#[derive(Debug, Eq, PartialEq)]
enum CrazyNativeExecutionFailureCause<MemoryError, RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    Release(NativeRegionInvocationOutcome),
    Runner(Box<RunnerError>),
}

/// Phase-tagged v6 Crazy transaction failure with cleanup evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedCrazyNativeExecutionFailure<MemoryError, RunnerError> {
    cause: CrazyNativeExecutionFailureCause<MemoryError, RunnerError>,
    phase: NativeExecutableExecutionPhase,
    release_failure: Option<Box<CrazyReleaseFailure<MemoryError>>>,
    release_request: Option<NativeExecutableReleaseRequest>,
}

/// Result of one complete v6 Crazy load/call/release transaction.
pub type RegisterMaskedCrazyNativeExecutionResult<MemoryError, RunnerError> =
    Result<
        NativeRegionInvocationOutcome,
        Box<
            RegisterMaskedCrazyNativeExecutionFailure<MemoryError, RunnerError>,
        >,
    >;

type CrazyNativeAdapterExecutionResult<MemoryAdapter, Runner> =
    RegisterMaskedCrazyNativeExecutionResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as RegisterMaskedCrazyNativeRunner>::Error,
    >;

#[derive(Debug, Eq, PartialEq)]
enum OutputNativeExecutionFailureCause<MemoryError, RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    Release(NativeRegionInvocationOutcome),
    Runner(Box<RunnerError>),
}

/// Phase-tagged v6 Output transaction failure with cleanup evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedOutputNativeExecutionFailure<MemoryError, RunnerError>
{
    cause: OutputNativeExecutionFailureCause<MemoryError, RunnerError>,
    phase: NativeExecutableExecutionPhase,
    release_failure: Option<Box<OutputReleaseFailure<MemoryError>>>,
    release_request: Option<NativeExecutableReleaseRequest>,
}

/// Result of one complete v6 Output load/call/release transaction.
pub type RegisterMaskedOutputNativeExecutionResult<MemoryError, RunnerError> =
    Result<
        NativeRegionInvocationOutcome,
        Box<
            RegisterMaskedOutputNativeExecutionFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    >;

type OutputNativeAdapterExecutionResult<MemoryAdapter, Runner> =
    RegisterMaskedOutputNativeExecutionResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as RegisterMaskedOutputNativeRunner>::Error,
    >;

#[derive(Debug, Eq, PartialEq)]
enum NoOperationNativeExecutionFailureCause<MemoryError, RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    Release(NativeRegionInvocationOutcome),
    Runner(Box<RunnerError>),
}

/// Phase-tagged v6 no-operation transaction failure with cleanup evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedNoOperationNativeExecutionFailure<
    MemoryError,
    RunnerError,
> {
    cause: NoOperationNativeExecutionFailureCause<MemoryError, RunnerError>,
    phase: NativeExecutableExecutionPhase,
    release_failure: Option<
        Box<
            RegisterMaskedNoOperationNativeExecutableReleaseFailure<
                MemoryError,
            >,
        >,
    >,
    release_request: Option<NativeExecutableReleaseRequest>,
}

/// Result of one complete v6 no-operation load/call/release transaction.
pub type RegisterMaskedNoOperationNativeExecutionResult<
    MemoryError,
    RunnerError,
> = Result<
    NativeRegionInvocationOutcome,
    Box<
        RegisterMaskedNoOperationNativeExecutionFailure<
            MemoryError,
            RunnerError,
        >,
    >,
>;

type NoOperationNativeAdapterExecutionResult<MemoryAdapter, Runner> =
    RegisterMaskedNoOperationNativeExecutionResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as RegisterMaskedNoOperationNativeRunner>::Error,
    >;

#[derive(Debug, Eq, PartialEq)]
enum RotateNativeExecutionFailureCause<MemoryError, RunnerError> {
    Binding(NativeExecutableInvocationBindingError),
    Completion(VerifiedRegisterMaskedInvocationError),
    Load(Box<NativeExecutableLoadFailure<MemoryError>>),
    Release(NativeRegionInvocationOutcome),
    Runner(Box<RunnerError>),
}

/// Phase-tagged v6 rotate transaction failure with cleanup evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedRotateNativeExecutionFailure<MemoryError, RunnerError>
{
    cause: RotateNativeExecutionFailureCause<MemoryError, RunnerError>,
    phase: NativeExecutableExecutionPhase,
    release_failure: Option<Box<RotateReleaseFailure<MemoryError>>>,
    release_request: Option<NativeExecutableReleaseRequest>,
}

/// Result of one complete v6 rotate load/call/release transaction.
pub type RegisterMaskedRotateNativeExecutionResult<MemoryError, RunnerError> =
    Result<
        NativeRegionInvocationOutcome,
        Box<
            RegisterMaskedRotateNativeExecutionFailure<
                MemoryError,
                RunnerError,
            >,
        >,
    >;

type RotateNativeAdapterExecutionResult<MemoryAdapter, Runner> =
    RegisterMaskedRotateNativeExecutionResult<
        <MemoryAdapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as RegisterMaskedRotateNativeRunner>::Error,
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

type RegisterMaskedCrazyNativeCallResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    RegisterMaskedCrazyNativeCallFailure<
        <Runner as RegisterMaskedCrazyNativeRunner>::Error,
    >,
>;

type RegisterMaskedOutputNativeCallResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    RegisterMaskedOutputNativeCallFailure<
        <Runner as RegisterMaskedOutputNativeRunner>::Error,
    >,
>;

type RegisterMaskedNoOperationNativeCallResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    RegisterMaskedNoOperationNativeCallFailure<
        <Runner as RegisterMaskedNoOperationNativeRunner>::Error,
    >,
>;

type RegisterMaskedNoOperationHaltNativeCallResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    RegisterMaskedNoOperationHaltNativeCallFailure<
        <Runner as RegisterMaskedNoOperationHaltNativeRunner>::Error,
    >,
>;

type RegisterMaskedNoOperationPairNativeCallResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    RegisterMaskedNoOperationPairNativeCallFailure<
        <Runner as RegisterMaskedNoOperationPairNativeRunner>::Error,
    >,
>;

type RegisterMaskedNoOperationRotateNativeCallResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    RegisterMaskedNoOperationRotateNativeCallFailure<
        <Runner as RegisterMaskedNoOperationRotateNativeRunner>::Error,
    >,
>;

type RegisterMaskedRotateNativeCallResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    RegisterMaskedRotateNativeCallFailure<
        <Runner as RegisterMaskedRotateNativeRunner>::Error,
    >,
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

type DirectFusedNativeCallResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    DirectFusedNativeCallFailure<<Runner as DirectFusedNativeRunner>::Error>,
>;

type NativeExecutableCallResult<Runner> = Result<
    NativeRegionInvocationOutcome,
    NativeExecutableCallFailure<<Runner as NativeExecutableRunner>::Error>,
>;

/// Caller-owned implementation of one exact fused whole-region call.
///
/// This port receives only a view constructed after fused semantic preparation
/// and synchronized executable identity have both been admitted.
pub trait DirectFusedNativeRunner {
    /// Stable runner-specific failure.
    type Error;

    /// Calls one exact synchronized fused executable and returns its raw ABI
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
        invocation: &mut PreparedDirectFusedNativeInvocation<'_, '_>,
    ) -> Result<i32, Self::Error>;
}

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

/// Caller-owned implementation of one exact v6 Crazy call.
///
/// This port receives only a view constructed after exact Crazy v6
/// image/executable identity binding.
pub trait RegisterMaskedCrazyNativeRunner {
    /// Stable runner-specific failure.
    type Error;

    /// Calls one exact synchronized v6 Crazy executable.
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
        invocation: &mut PreparedRegisterMaskedCrazyNativeInvocation<'_, '_>,
    ) -> Result<i32, Self::Error>;
}

/// Caller-owned implementation of one exact v6 Output call.
///
/// This port receives only a view constructed after exact Output v6
/// image/executable identity binding.
pub trait RegisterMaskedOutputNativeRunner {
    /// Stable runner-specific failure.
    type Error;

    /// Calls one exact synchronized v6 Output executable.
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
        invocation: &mut PreparedRegisterMaskedOutputNativeInvocation<'_, '_>,
    ) -> Result<i32, Self::Error>;
}

/// Caller-owned implementation of one exact v6 no-operation call.
///
/// This port receives only a view constructed after exact no-operation v6
/// image/executable identity binding.
pub trait RegisterMaskedNoOperationNativeRunner {
    /// Stable runner-specific failure.
    type Error;

    /// Calls one exact synchronized v6 no-operation executable.
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
        invocation: &mut PreparedRegisterMaskedNoOperationNativeInvocation<
            '_,
            '_,
        >,
    ) -> Result<i32, Self::Error>;
}

/// Caller-owned implementation of one exact collapsed v6 no-op/halt call.
///
/// This port receives only a view constructed after exact collapsed-v6
/// image/executable identity binding.
pub trait RegisterMaskedNoOperationHaltNativeRunner {
    /// Stable runner-specific failure.
    type Error;

    /// Calls one exact synchronized collapsed-v6 executable.
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
        invocation: &mut PreparedRegisterMaskedNoOperationHaltNativeInvocation<
            '_,
            '_,
        >,
    ) -> Result<i32, Self::Error>;
}

/// Caller-owned implementation of one exact collapsed v6 no-operation pair
/// call.
///
/// This port receives only a view constructed after exact collapsed-pair v6
/// image/executable identity binding.
pub trait RegisterMaskedNoOperationPairNativeRunner {
    /// Stable runner-specific failure.
    type Error;

    /// Calls one exact synchronized collapsed-pair v6 executable.
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
        invocation: &mut PreparedRegisterMaskedNoOperationPairNativeInvocation<
            '_,
            '_,
        >,
    ) -> Result<i32, Self::Error>;
}

/// Caller-owned implementation of one exact collapsed v6 no-operation/rotate
/// call.
///
/// This port receives only a view constructed after exact collapsed
/// no-op/rotate v6 image/executable identity binding.
pub trait RegisterMaskedNoOperationRotateNativeRunner {
    /// Stable runner-specific failure.
    type Error;

    /// Calls one exact synchronized collapsed no-op/rotate v6 executable.
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
        invocation:
            &mut PreparedRegisterMaskedNoOperationRotateNativeInvocation<
                '_,
                '_,
            >,
    ) -> Result<i32, Self::Error>;
}

/// Caller-owned implementation of one exact v6 rotate call.
///
/// This port receives only a view constructed after exact rotate v6
/// image/executable identity binding.
pub trait RegisterMaskedRotateNativeRunner {
    /// Stable runner-specific failure.
    type Error;

    /// Calls one exact synchronized v6 rotate executable.
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
        invocation: &mut PreparedRegisterMaskedRotateNativeInvocation<'_, '_>,
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

impl<RunnerError> DirectFusedLoadedExecutionFailure<RunnerError> {
    /// Returns exact ready-image binding failure, when identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            DirectFusedNativeCallFailure::Binding(error) => Some(*error),
            DirectFusedNativeCallFailure::Completion(_)
            | DirectFusedNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns fused result-admission failure after the runner returned.
    #[must_use]
    pub const fn completion_error(&self) -> Option<DirectFusedInvocationError> {
        match &self.cause {
            DirectFusedNativeCallFailure::Completion(error) => Some(*error),
            DirectFusedNativeCallFailure::Binding(_)
            | DirectFusedNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns the exact call phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        match &self.cause {
            DirectFusedNativeCallFailure::Binding(_) => {
                NativeExecutableExecutionPhase::Bind
            },
            DirectFusedNativeCallFailure::Completion(_) => {
                NativeExecutableExecutionPhase::Complete
            },
            DirectFusedNativeCallFailure::Runner(_) => {
                NativeExecutableExecutionPhase::Run
            },
        }
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            DirectFusedNativeCallFailure::Runner(error) => Some(error),
            DirectFusedNativeCallFailure::Binding(_)
            | DirectFusedNativeCallFailure::Completion(_) => None,
        }
    }
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

impl<RunnerError> RegisterMaskedCrazyLoadedExecutionFailure<RunnerError> {
    /// Returns exact ready-image binding failure, when v6 identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            RegisterMaskedCrazyNativeCallFailure::Binding(error) => {
                Some(*error)
            },
            RegisterMaskedCrazyNativeCallFailure::Completion(_)
            | RegisterMaskedCrazyNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns v6 Crazy result-admission failure.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            RegisterMaskedCrazyNativeCallFailure::Completion(error) => {
                Some(*error)
            },
            RegisterMaskedCrazyNativeCallFailure::Binding(_)
            | RegisterMaskedCrazyNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns the exact call phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        match &self.cause {
            RegisterMaskedCrazyNativeCallFailure::Binding(_) => {
                NativeExecutableExecutionPhase::Bind
            },
            RegisterMaskedCrazyNativeCallFailure::Completion(_) => {
                NativeExecutableExecutionPhase::Complete
            },
            RegisterMaskedCrazyNativeCallFailure::Runner(_) => {
                NativeExecutableExecutionPhase::Run
            },
        }
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            RegisterMaskedCrazyNativeCallFailure::Runner(error) => Some(error),
            RegisterMaskedCrazyNativeCallFailure::Binding(_)
            | RegisterMaskedCrazyNativeCallFailure::Completion(_) => None,
        }
    }
}

impl<RunnerError> RegisterMaskedOutputLoadedExecutionFailure<RunnerError> {
    /// Returns exact ready-image binding failure, when v6 identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            RegisterMaskedOutputNativeCallFailure::Binding(error) => {
                Some(*error)
            },
            RegisterMaskedOutputNativeCallFailure::Completion(_)
            | RegisterMaskedOutputNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns v6 Output result-admission failure.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            RegisterMaskedOutputNativeCallFailure::Completion(error) => {
                Some(*error)
            },
            RegisterMaskedOutputNativeCallFailure::Binding(_)
            | RegisterMaskedOutputNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns the exact call phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        match &self.cause {
            RegisterMaskedOutputNativeCallFailure::Binding(_) => {
                NativeExecutableExecutionPhase::Bind
            },
            RegisterMaskedOutputNativeCallFailure::Completion(_) => {
                NativeExecutableExecutionPhase::Complete
            },
            RegisterMaskedOutputNativeCallFailure::Runner(_) => {
                NativeExecutableExecutionPhase::Run
            },
        }
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            RegisterMaskedOutputNativeCallFailure::Runner(error) => Some(error),
            RegisterMaskedOutputNativeCallFailure::Binding(_)
            | RegisterMaskedOutputNativeCallFailure::Completion(_) => None,
        }
    }
}

impl<RunnerError> RegisterMaskedNoOperationLoadedExecutionFailure<RunnerError> {
    /// Returns exact ready-image binding failure, when v6 identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            RegisterMaskedNoOperationNativeCallFailure::Binding(error) => {
                Some(*error)
            },
            RegisterMaskedNoOperationNativeCallFailure::Completion(_)
            | RegisterMaskedNoOperationNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns v6 no-operation result-admission failure.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            RegisterMaskedNoOperationNativeCallFailure::Completion(error) => {
                Some(*error)
            },
            RegisterMaskedNoOperationNativeCallFailure::Binding(_)
            | RegisterMaskedNoOperationNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns the exact call phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        match &self.cause {
            RegisterMaskedNoOperationNativeCallFailure::Binding(_) => {
                NativeExecutableExecutionPhase::Bind
            },
            RegisterMaskedNoOperationNativeCallFailure::Completion(_) => {
                NativeExecutableExecutionPhase::Complete
            },
            RegisterMaskedNoOperationNativeCallFailure::Runner(_) => {
                NativeExecutableExecutionPhase::Run
            },
        }
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            RegisterMaskedNoOperationNativeCallFailure::Runner(error) => {
                Some(error)
            },
            RegisterMaskedNoOperationNativeCallFailure::Binding(_)
            | RegisterMaskedNoOperationNativeCallFailure::Completion(_) => None,
        }
    }
}

impl<RunnerError>
    RegisterMaskedNoOperationHaltLoadedExecutionFailure<RunnerError>
{
    /// Returns exact ready-image binding failure, when identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            RegisterMaskedNoOperationHaltNativeCallFailure::Binding(error) => {
                Some(*error)
            },
            RegisterMaskedNoOperationHaltNativeCallFailure::Completion(_)
            | RegisterMaskedNoOperationHaltNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns collapsed-v6 result-admission failure.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            RegisterMaskedNoOperationHaltNativeCallFailure::Completion(
                error,
            ) => Some(*error),
            RegisterMaskedNoOperationHaltNativeCallFailure::Binding(_)
            | RegisterMaskedNoOperationHaltNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns the exact call phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        match &self.cause {
            RegisterMaskedNoOperationHaltNativeCallFailure::Binding(_) => {
                NativeExecutableExecutionPhase::Bind
            },
            RegisterMaskedNoOperationHaltNativeCallFailure::Completion(_) => {
                NativeExecutableExecutionPhase::Complete
            },
            RegisterMaskedNoOperationHaltNativeCallFailure::Runner(_) => {
                NativeExecutableExecutionPhase::Run
            },
        }
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            RegisterMaskedNoOperationHaltNativeCallFailure::Runner(error) => {
                Some(error)
            },
            RegisterMaskedNoOperationHaltNativeCallFailure::Binding(_)
            | RegisterMaskedNoOperationHaltNativeCallFailure::Completion(_) => {
                None
            },
        }
    }
}

impl<RunnerError>
    RegisterMaskedNoOperationPairLoadedExecutionFailure<RunnerError>
{
    /// Returns exact ready-image binding failure, when identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            RegisterMaskedNoOperationPairNativeCallFailure::Binding(error) => {
                Some(*error)
            },
            RegisterMaskedNoOperationPairNativeCallFailure::Completion(_)
            | RegisterMaskedNoOperationPairNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns collapsed-pair v6 result-admission failure.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            RegisterMaskedNoOperationPairNativeCallFailure::Completion(
                error,
            ) => Some(*error),
            RegisterMaskedNoOperationPairNativeCallFailure::Binding(_)
            | RegisterMaskedNoOperationPairNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns the exact call phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        match &self.cause {
            RegisterMaskedNoOperationPairNativeCallFailure::Binding(_) => {
                NativeExecutableExecutionPhase::Bind
            },
            RegisterMaskedNoOperationPairNativeCallFailure::Completion(_) => {
                NativeExecutableExecutionPhase::Complete
            },
            RegisterMaskedNoOperationPairNativeCallFailure::Runner(_) => {
                NativeExecutableExecutionPhase::Run
            },
        }
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            RegisterMaskedNoOperationPairNativeCallFailure::Runner(error) => {
                Some(error)
            },
            RegisterMaskedNoOperationPairNativeCallFailure::Binding(_)
            | RegisterMaskedNoOperationPairNativeCallFailure::Completion(_) => {
                None
            },
        }
    }
}

impl<RunnerError>
    RegisterMaskedNoOperationRotateLoadedExecutionFailure<RunnerError>
{
    /// Returns exact ready-image binding failure, when identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            RegisterMaskedNoOperationRotateNativeCallFailure::Binding(
                error,
            ) => Some(*error),
            RegisterMaskedNoOperationRotateNativeCallFailure::Completion(_)
            | RegisterMaskedNoOperationRotateNativeCallFailure::Runner(_) => {
                None
            },
        }
    }

    /// Returns collapsed no-op/rotate v6 result-admission failure.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        if let RegisterMaskedNoOperationRotateNativeCallFailure::Completion(
            error,
        ) = &self.cause
        {
            Some(*error)
        } else {
            None
        }
    }

    /// Returns the exact call phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        match &self.cause {
            RegisterMaskedNoOperationRotateNativeCallFailure::Binding(_) => {
                NativeExecutableExecutionPhase::Bind
            },
            RegisterMaskedNoOperationRotateNativeCallFailure::Completion(_) => {
                NativeExecutableExecutionPhase::Complete
            },
            RegisterMaskedNoOperationRotateNativeCallFailure::Runner(_) => {
                NativeExecutableExecutionPhase::Run
            },
        }
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        if let RegisterMaskedNoOperationRotateNativeCallFailure::Runner(error) =
            &self.cause
        {
            Some(error)
        } else {
            None
        }
    }
}

impl<RunnerError> RegisterMaskedRotateLoadedExecutionFailure<RunnerError> {
    /// Returns exact ready-image binding failure, when v6 identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            RegisterMaskedRotateNativeCallFailure::Binding(error) => {
                Some(*error)
            },
            RegisterMaskedRotateNativeCallFailure::Completion(_)
            | RegisterMaskedRotateNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns v6 rotate result-admission failure.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            RegisterMaskedRotateNativeCallFailure::Completion(error) => {
                Some(*error)
            },
            RegisterMaskedRotateNativeCallFailure::Binding(_)
            | RegisterMaskedRotateNativeCallFailure::Runner(_) => None,
        }
    }

    /// Returns the exact call phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        match &self.cause {
            RegisterMaskedRotateNativeCallFailure::Binding(_) => {
                NativeExecutableExecutionPhase::Bind
            },
            RegisterMaskedRotateNativeCallFailure::Completion(_) => {
                NativeExecutableExecutionPhase::Complete
            },
            RegisterMaskedRotateNativeCallFailure::Runner(_) => {
                NativeExecutableExecutionPhase::Run
            },
        }
    }

    /// Returns external runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            RegisterMaskedRotateNativeCallFailure::Runner(error) => Some(error),
            RegisterMaskedRotateNativeCallFailure::Binding(_)
            | RegisterMaskedRotateNativeCallFailure::Completion(_) => None,
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

impl<RunnerError> DirectFusedNativeCallFailure<RunnerError> {
    fn into_cause<MemoryError>(
        self,
    ) -> DirectFusedNativeExecutionFailureCause<MemoryError, RunnerError> {
        match self {
            Self::Binding(error) => {
                DirectFusedNativeExecutionFailureCause::Binding(error)
            },
            Self::Completion(error) => {
                DirectFusedNativeExecutionFailureCause::Completion(error)
            },
            Self::Runner(error) => {
                DirectFusedNativeExecutionFailureCause::Runner(error)
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

impl<RunnerError> RegisterMaskedCrazyNativeCallFailure<RunnerError> {
    fn into_cause<MemoryError>(
        self,
    ) -> CrazyNativeExecutionFailureCause<MemoryError, RunnerError> {
        match self {
            Self::Binding(error) => {
                CrazyNativeExecutionFailureCause::Binding(error)
            },
            Self::Completion(error) => {
                CrazyNativeExecutionFailureCause::Completion(error)
            },
            Self::Runner(error) => {
                CrazyNativeExecutionFailureCause::Runner(error)
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

impl<RunnerError> RegisterMaskedOutputNativeCallFailure<RunnerError> {
    fn into_cause<MemoryError>(
        self,
    ) -> OutputNativeExecutionFailureCause<MemoryError, RunnerError> {
        match self {
            Self::Binding(error) => {
                OutputNativeExecutionFailureCause::Binding(error)
            },
            Self::Completion(error) => {
                OutputNativeExecutionFailureCause::Completion(error)
            },
            Self::Runner(error) => {
                OutputNativeExecutionFailureCause::Runner(error)
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

impl<RunnerError> RegisterMaskedNoOperationNativeCallFailure<RunnerError> {
    fn into_cause<MemoryError>(
        self,
    ) -> NoOperationNativeExecutionFailureCause<MemoryError, RunnerError> {
        match self {
            Self::Binding(error) => {
                NoOperationNativeExecutionFailureCause::Binding(error)
            },
            Self::Completion(error) => {
                NoOperationNativeExecutionFailureCause::Completion(error)
            },
            Self::Runner(error) => {
                NoOperationNativeExecutionFailureCause::Runner(error)
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

impl<RunnerError> RegisterMaskedRotateNativeCallFailure<RunnerError> {
    fn into_cause<MemoryError>(
        self,
    ) -> RotateNativeExecutionFailureCause<MemoryError, RunnerError> {
        match self {
            Self::Binding(error) => {
                RotateNativeExecutionFailureCause::Binding(error)
            },
            Self::Completion(error) => {
                RotateNativeExecutionFailureCause::Completion(error)
            },
            Self::Runner(error) => {
                RotateNativeExecutionFailureCause::Runner(error)
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
    DirectFusedNativeExecutionFailure<MemoryError, RunnerError>
{
    /// Returns exact ready-image binding failure, when identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            DirectFusedNativeExecutionFailureCause::Binding(error) => {
                Some(*error)
            },
            DirectFusedNativeExecutionFailureCause::Completion(_)
            | DirectFusedNativeExecutionFailureCause::Load(_)
            | DirectFusedNativeExecutionFailureCause::Release(_)
            | DirectFusedNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns the outcome committed before final fused release failed.
    #[must_use]
    pub const fn committed_outcome(
        &self,
    ) -> Option<NativeRegionInvocationOutcome> {
        match &self.cause {
            DirectFusedNativeExecutionFailureCause::Release(outcome) => {
                Some(*outcome)
            },
            DirectFusedNativeExecutionFailureCause::Binding(_)
            | DirectFusedNativeExecutionFailureCause::Completion(_)
            | DirectFusedNativeExecutionFailureCause::Load(_)
            | DirectFusedNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns fused completion failure after the runner returned.
    #[must_use]
    pub const fn completion_error(&self) -> Option<DirectFusedInvocationError> {
        match &self.cause {
            DirectFusedNativeExecutionFailureCause::Completion(error) => {
                Some(*error)
            },
            DirectFusedNativeExecutionFailureCause::Binding(_)
            | DirectFusedNativeExecutionFailureCause::Load(_)
            | DirectFusedNativeExecutionFailureCause::Release(_)
            | DirectFusedNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Consumes this failure and returns retryable fused mapping cleanup.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<DirectFusedNativeExecutableReleaseFailure<MemoryError>> {
        self.release_failure.map(|failure| *failure)
    }

    /// Returns fused executable loading failure, when no ready image was made.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&NativeExecutableLoadFailure<MemoryError>> {
        match &self.cause {
            DirectFusedNativeExecutionFailureCause::Load(error) => Some(error),
            DirectFusedNativeExecutionFailureCause::Binding(_)
            | DirectFusedNativeExecutionFailureCause::Completion(_)
            | DirectFusedNativeExecutionFailureCause::Release(_)
            | DirectFusedNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns the exact fused transaction phase that failed.
    #[must_use]
    pub const fn phase(&self) -> NativeExecutableExecutionPhase {
        self.phase
    }

    /// Returns failed cleanup retaining the fused ready executable for retry.
    #[must_use]
    pub const fn release_failure(
        &self,
    ) -> Option<&DirectFusedNativeExecutableReleaseFailure<MemoryError>> {
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

    /// Returns external fused runner failure, when the call mechanism failed.
    #[must_use]
    pub const fn runner_error(&self) -> Option<&RunnerError> {
        match &self.cause {
            DirectFusedNativeExecutionFailureCause::Runner(error) => {
                Some(error)
            },
            DirectFusedNativeExecutionFailureCause::Binding(_)
            | DirectFusedNativeExecutionFailureCause::Completion(_)
            | DirectFusedNativeExecutionFailureCause::Load(_)
            | DirectFusedNativeExecutionFailureCause::Release(_) => None,
        }
    }
}

impl<MemoryError, RunnerError>
    RegisterMaskedCrazyNativeExecutionFailure<MemoryError, RunnerError>
{
    /// Returns ready-image binding failure, when exact v6 identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            CrazyNativeExecutionFailureCause::Binding(error) => Some(*error),
            CrazyNativeExecutionFailureCause::Completion(_)
            | CrazyNativeExecutionFailureCause::Load(_)
            | CrazyNativeExecutionFailureCause::Release(_)
            | CrazyNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns the outcome committed before final release failed.
    #[must_use]
    pub const fn committed_outcome(
        &self,
    ) -> Option<NativeRegionInvocationOutcome> {
        match &self.cause {
            CrazyNativeExecutionFailureCause::Release(outcome) => {
                Some(*outcome)
            },
            CrazyNativeExecutionFailureCause::Binding(_)
            | CrazyNativeExecutionFailureCause::Completion(_)
            | CrazyNativeExecutionFailureCause::Load(_)
            | CrazyNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns result-admission failure, when native state drifted.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            CrazyNativeExecutionFailureCause::Completion(error) => Some(*error),
            CrazyNativeExecutionFailureCause::Binding(_)
            | CrazyNativeExecutionFailureCause::Load(_)
            | CrazyNativeExecutionFailureCause::Release(_)
            | CrazyNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Consumes this failure and returns retryable mapping cleanup.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<CrazyReleaseFailure<MemoryError>> {
        self.release_failure.map(|failure| *failure)
    }

    /// Returns executable loading failure, when no ready image was produced.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&NativeExecutableLoadFailure<MemoryError>> {
        match &self.cause {
            CrazyNativeExecutionFailureCause::Load(error) => Some(error),
            CrazyNativeExecutionFailureCause::Binding(_)
            | CrazyNativeExecutionFailureCause::Completion(_)
            | CrazyNativeExecutionFailureCause::Release(_)
            | CrazyNativeExecutionFailureCause::Runner(_) => None,
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
    ) -> Option<&CrazyReleaseFailure<MemoryError>> {
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
            CrazyNativeExecutionFailureCause::Runner(error) => Some(error),
            CrazyNativeExecutionFailureCause::Binding(_)
            | CrazyNativeExecutionFailureCause::Completion(_)
            | CrazyNativeExecutionFailureCause::Load(_)
            | CrazyNativeExecutionFailureCause::Release(_) => None,
        }
    }
}

impl<MemoryError, RunnerError>
    RegisterMaskedOutputNativeExecutionFailure<MemoryError, RunnerError>
{
    /// Returns ready-image binding failure, when exact v6 identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            OutputNativeExecutionFailureCause::Binding(error) => Some(*error),
            OutputNativeExecutionFailureCause::Completion(_)
            | OutputNativeExecutionFailureCause::Load(_)
            | OutputNativeExecutionFailureCause::Release(_)
            | OutputNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns the outcome committed before final release failed.
    #[must_use]
    pub const fn committed_outcome(
        &self,
    ) -> Option<NativeRegionInvocationOutcome> {
        match &self.cause {
            OutputNativeExecutionFailureCause::Release(outcome) => {
                Some(*outcome)
            },
            OutputNativeExecutionFailureCause::Binding(_)
            | OutputNativeExecutionFailureCause::Completion(_)
            | OutputNativeExecutionFailureCause::Load(_)
            | OutputNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns result-admission failure, when native state drifted.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            OutputNativeExecutionFailureCause::Completion(error) => {
                Some(*error)
            },
            OutputNativeExecutionFailureCause::Binding(_)
            | OutputNativeExecutionFailureCause::Load(_)
            | OutputNativeExecutionFailureCause::Release(_)
            | OutputNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Consumes this failure and returns retryable mapping cleanup.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<OutputReleaseFailure<MemoryError>> {
        self.release_failure.map(|failure| *failure)
    }

    /// Returns executable loading failure, when no ready image was produced.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&NativeExecutableLoadFailure<MemoryError>> {
        match &self.cause {
            OutputNativeExecutionFailureCause::Load(error) => Some(error),
            OutputNativeExecutionFailureCause::Binding(_)
            | OutputNativeExecutionFailureCause::Completion(_)
            | OutputNativeExecutionFailureCause::Release(_)
            | OutputNativeExecutionFailureCause::Runner(_) => None,
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
    ) -> Option<&OutputReleaseFailure<MemoryError>> {
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
            OutputNativeExecutionFailureCause::Runner(error) => Some(error),
            OutputNativeExecutionFailureCause::Binding(_)
            | OutputNativeExecutionFailureCause::Completion(_)
            | OutputNativeExecutionFailureCause::Load(_)
            | OutputNativeExecutionFailureCause::Release(_) => None,
        }
    }
}

impl<MemoryError, RunnerError>
    RegisterMaskedNoOperationNativeExecutionFailure<MemoryError, RunnerError>
{
    /// Returns ready-image binding failure, when exact v6 identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            NoOperationNativeExecutionFailureCause::Binding(error) => {
                Some(*error)
            },
            NoOperationNativeExecutionFailureCause::Completion(_)
            | NoOperationNativeExecutionFailureCause::Load(_)
            | NoOperationNativeExecutionFailureCause::Release(_)
            | NoOperationNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns the outcome committed before final release failed.
    #[must_use]
    pub const fn committed_outcome(
        &self,
    ) -> Option<NativeRegionInvocationOutcome> {
        match &self.cause {
            NoOperationNativeExecutionFailureCause::Release(outcome) => {
                Some(*outcome)
            },
            NoOperationNativeExecutionFailureCause::Binding(_)
            | NoOperationNativeExecutionFailureCause::Completion(_)
            | NoOperationNativeExecutionFailureCause::Load(_)
            | NoOperationNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns result-admission failure, when native state drifted.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            NoOperationNativeExecutionFailureCause::Completion(error) => {
                Some(*error)
            },
            NoOperationNativeExecutionFailureCause::Binding(_)
            | NoOperationNativeExecutionFailureCause::Load(_)
            | NoOperationNativeExecutionFailureCause::Release(_)
            | NoOperationNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Consumes this failure and returns retryable mapping cleanup.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<
        RegisterMaskedNoOperationNativeExecutableReleaseFailure<MemoryError>,
    > {
        self.release_failure.map(|failure| *failure)
    }

    /// Returns executable loading failure, when no ready image was produced.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&NativeExecutableLoadFailure<MemoryError>> {
        match &self.cause {
            NoOperationNativeExecutionFailureCause::Load(error) => Some(error),
            NoOperationNativeExecutionFailureCause::Binding(_)
            | NoOperationNativeExecutionFailureCause::Completion(_)
            | NoOperationNativeExecutionFailureCause::Release(_)
            | NoOperationNativeExecutionFailureCause::Runner(_) => None,
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
        &RegisterMaskedNoOperationNativeExecutableReleaseFailure<MemoryError>,
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
            NoOperationNativeExecutionFailureCause::Runner(error) => {
                Some(error)
            },
            NoOperationNativeExecutionFailureCause::Binding(_)
            | NoOperationNativeExecutionFailureCause::Completion(_)
            | NoOperationNativeExecutionFailureCause::Load(_)
            | NoOperationNativeExecutionFailureCause::Release(_) => None,
        }
    }
}

impl<MemoryError, RunnerError>
    RegisterMaskedRotateNativeExecutionFailure<MemoryError, RunnerError>
{
    /// Returns ready-image binding failure, when exact v6 identity disagreed.
    #[must_use]
    pub const fn binding_error(
        &self,
    ) -> Option<NativeExecutableInvocationBindingError> {
        match &self.cause {
            RotateNativeExecutionFailureCause::Binding(error) => Some(*error),
            RotateNativeExecutionFailureCause::Completion(_)
            | RotateNativeExecutionFailureCause::Load(_)
            | RotateNativeExecutionFailureCause::Release(_)
            | RotateNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns the outcome committed before final release failed.
    #[must_use]
    pub const fn committed_outcome(
        &self,
    ) -> Option<NativeRegionInvocationOutcome> {
        match &self.cause {
            RotateNativeExecutionFailureCause::Release(outcome) => {
                Some(*outcome)
            },
            RotateNativeExecutionFailureCause::Binding(_)
            | RotateNativeExecutionFailureCause::Completion(_)
            | RotateNativeExecutionFailureCause::Load(_)
            | RotateNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Returns result-admission failure, when native state drifted.
    #[must_use]
    pub const fn completion_error(
        &self,
    ) -> Option<VerifiedRegisterMaskedInvocationError> {
        match &self.cause {
            RotateNativeExecutionFailureCause::Completion(error) => {
                Some(*error)
            },
            RotateNativeExecutionFailureCause::Binding(_)
            | RotateNativeExecutionFailureCause::Load(_)
            | RotateNativeExecutionFailureCause::Release(_)
            | RotateNativeExecutionFailureCause::Runner(_) => None,
        }
    }

    /// Consumes this failure and returns retryable mapping cleanup.
    #[must_use]
    pub fn into_release_failure(
        self,
    ) -> Option<RotateReleaseFailure<MemoryError>> {
        self.release_failure.map(|failure| *failure)
    }

    /// Returns executable loading failure, when no ready image was produced.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&NativeExecutableLoadFailure<MemoryError>> {
        match &self.cause {
            RotateNativeExecutionFailureCause::Load(error) => Some(error),
            RotateNativeExecutionFailureCause::Binding(_)
            | RotateNativeExecutionFailureCause::Completion(_)
            | RotateNativeExecutionFailureCause::Release(_)
            | RotateNativeExecutionFailureCause::Runner(_) => None,
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
    ) -> Option<&RotateReleaseFailure<MemoryError>> {
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
            RotateNativeExecutionFailureCause::Runner(error) => Some(error),
            RotateNativeExecutionFailureCause::Binding(_)
            | RotateNativeExecutionFailureCause::Completion(_)
            | RotateNativeExecutionFailureCause::Load(_)
            | RotateNativeExecutionFailureCause::Release(_) => None,
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

impl<MemoryError: Display, RunnerError: Display> Display
    for DirectFusedNativeExecutionFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "fused native execution failed during {}: ", self.phase)?;
        match &self.cause {
            DirectFusedNativeExecutionFailureCause::Binding(error) => {
                write!(f, "binding: {error}")?;
            },
            DirectFusedNativeExecutionFailureCause::Completion(error) => {
                write!(f, "completion: {error}")?;
            },
            DirectFusedNativeExecutionFailureCause::Load(error) => {
                write!(f, "loading: {error}")?;
            },
            DirectFusedNativeExecutionFailureCause::Release(outcome) => {
                let label = match outcome {
                    NativeRegionInvocationOutcome::Applied(_) => "applied",
                    NativeRegionInvocationOutcome::GuardMiss => "guard-miss",
                };
                write!(f, "committed {label} outcome could not release")?;
            },
            DirectFusedNativeExecutionFailureCause::Runner(error) => {
                write!(f, "runner: {error}")?;
            },
        }
        if let Some(release_failure) = &self.release_failure {
            write!(f, "; {release_failure}")?;
        }
        Ok(())
    }
}

impl<RunnerError: Display> Display
    for DirectFusedLoadedExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "loaded fused execution failed during {}: ", self.phase())?;
        match &self.cause {
            DirectFusedNativeCallFailure::Binding(error) => {
                write!(f, "binding: {error}")
            },
            DirectFusedNativeCallFailure::Completion(error) => {
                write!(f, "completion: {error}")
            },
            DirectFusedNativeCallFailure::Runner(error) => {
                write!(f, "runner: {error}")
            },
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
    for RegisterMaskedCrazyLoadedExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "loaded v6 Crazy failed during {}: ", self.phase())?;
        match &self.cause {
            RegisterMaskedCrazyNativeCallFailure::Binding(error) => {
                write!(f, "binding: {error}")
            },
            RegisterMaskedCrazyNativeCallFailure::Completion(error) => {
                write!(f, "completion: {error}")
            },
            RegisterMaskedCrazyNativeCallFailure::Runner(error) => {
                write!(f, "runner: {error}")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for RegisterMaskedOutputLoadedExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "loaded v6 Output failed during {}: ", self.phase())?;
        match &self.cause {
            RegisterMaskedOutputNativeCallFailure::Binding(error) => {
                write!(f, "binding: {error}")
            },
            RegisterMaskedOutputNativeCallFailure::Completion(error) => {
                write!(f, "completion: {error}")
            },
            RegisterMaskedOutputNativeCallFailure::Runner(error) => {
                write!(f, "runner: {error}")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for RegisterMaskedNoOperationLoadedExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "loaded v6 no-operation failed during {}: ", self.phase())?;
        match &self.cause {
            RegisterMaskedNoOperationNativeCallFailure::Binding(error) => {
                write!(f, "binding: {error}")
            },
            RegisterMaskedNoOperationNativeCallFailure::Completion(error) => {
                write!(f, "completion: {error}")
            },
            RegisterMaskedNoOperationNativeCallFailure::Runner(error) => {
                write!(f, "runner: {error}")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for RegisterMaskedNoOperationHaltLoadedExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "loaded collapsed v6 no-op/halt failed during {}: ",
            self.phase()
        )?;
        match &self.cause {
            RegisterMaskedNoOperationHaltNativeCallFailure::Binding(error) => {
                write!(f, "binding: {error}")
            },
            RegisterMaskedNoOperationHaltNativeCallFailure::Completion(
                error,
            ) => {
                write!(f, "completion: {error}")
            },
            RegisterMaskedNoOperationHaltNativeCallFailure::Runner(error) => {
                write!(f, "runner: {error}")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for RegisterMaskedNoOperationPairLoadedExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "loaded collapsed v6 no-operation pair failed during {}: ",
            self.phase()
        )?;
        match &self.cause {
            RegisterMaskedNoOperationPairNativeCallFailure::Binding(error) => {
                write!(f, "binding: {error}")
            },
            RegisterMaskedNoOperationPairNativeCallFailure::Completion(
                error,
            ) => {
                write!(f, "completion: {error}")
            },
            RegisterMaskedNoOperationPairNativeCallFailure::Runner(error) => {
                write!(f, "runner: {error}")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for RegisterMaskedNoOperationRotateLoadedExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "loaded collapsed v6 no-operation/rotate failed during {}: ",
            self.phase()
        )?;
        match &self.cause {
            RegisterMaskedNoOperationRotateNativeCallFailure::Binding(
                error,
            ) => {
                write!(f, "binding: {error}")
            },
            RegisterMaskedNoOperationRotateNativeCallFailure::Completion(
                error,
            ) => {
                write!(f, "completion: {error}")
            },
            RegisterMaskedNoOperationRotateNativeCallFailure::Runner(error) => {
                write!(f, "runner: {error}")
            },
        }
    }
}

impl<RunnerError: Display> Display
    for RegisterMaskedRotateLoadedExecutionFailure<RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "loaded v6 rotate failed during {}: ", self.phase())?;
        match &self.cause {
            RegisterMaskedRotateNativeCallFailure::Binding(error) => {
                write!(f, "binding: {error}")
            },
            RegisterMaskedRotateNativeCallFailure::Completion(error) => {
                write!(f, "completion: {error}")
            },
            RegisterMaskedRotateNativeCallFailure::Runner(error) => {
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
    for RegisterMaskedCrazyNativeExecutionFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v6 Crazy failed during {}: ", self.phase)?;
        match &self.cause {
            CrazyNativeExecutionFailureCause::Binding(error) => {
                write!(f, "binding: {error}")?;
            },
            CrazyNativeExecutionFailureCause::Completion(error) => {
                write!(f, "completion: {error}")?;
            },
            CrazyNativeExecutionFailureCause::Load(error) => {
                write!(f, "loading: {error}")?;
            },
            CrazyNativeExecutionFailureCause::Release(outcome) => {
                let label = match outcome {
                    NativeRegionInvocationOutcome::Applied(_) => "applied",
                    NativeRegionInvocationOutcome::GuardMiss => "guard-miss",
                };
                write!(f, "committed {label} outcome could not release")?;
            },
            CrazyNativeExecutionFailureCause::Runner(error) => {
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
    for RegisterMaskedOutputNativeExecutionFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v6 Output failed during {}: ", self.phase)?;
        match &self.cause {
            OutputNativeExecutionFailureCause::Binding(error) => {
                write!(f, "binding: {error}")?;
            },
            OutputNativeExecutionFailureCause::Completion(error) => {
                write!(f, "completion: {error}")?;
            },
            OutputNativeExecutionFailureCause::Load(error) => {
                write!(f, "loading: {error}")?;
            },
            OutputNativeExecutionFailureCause::Release(outcome) => {
                let label = match outcome {
                    NativeRegionInvocationOutcome::Applied(_) => "applied",
                    NativeRegionInvocationOutcome::GuardMiss => "guard-miss",
                };
                write!(f, "committed {label} outcome could not release")?;
            },
            OutputNativeExecutionFailureCause::Runner(error) => {
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
    for RegisterMaskedNoOperationNativeExecutionFailure<
        MemoryError,
        RunnerError,
    >
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v6 no-operation failed during {}: ", self.phase)?;
        match &self.cause {
            NoOperationNativeExecutionFailureCause::Binding(error) => {
                write!(f, "binding: {error}")?;
            },
            NoOperationNativeExecutionFailureCause::Completion(error) => {
                write!(f, "completion: {error}")?;
            },
            NoOperationNativeExecutionFailureCause::Load(error) => {
                write!(f, "loading: {error}")?;
            },
            NoOperationNativeExecutionFailureCause::Release(outcome) => {
                let label = match outcome {
                    NativeRegionInvocationOutcome::Applied(_) => "applied",
                    NativeRegionInvocationOutcome::GuardMiss => "guard-miss",
                };
                write!(f, "committed {label} outcome could not release")?;
            },
            NoOperationNativeExecutionFailureCause::Runner(error) => {
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
    for RegisterMaskedRotateNativeExecutionFailure<MemoryError, RunnerError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "v6 rotate failed during {}: ", self.phase)?;
        match &self.cause {
            RotateNativeExecutionFailureCause::Binding(error) => {
                write!(f, "binding: {error}")?;
            },
            RotateNativeExecutionFailureCause::Completion(error) => {
                write!(f, "completion: {error}")?;
            },
            RotateNativeExecutionFailureCause::Load(error) => {
                write!(f, "loading: {error}")?;
            },
            RotateNativeExecutionFailureCause::Release(outcome) => {
                let label = match outcome {
                    NativeRegionInvocationOutcome::Applied(_) => "applied",
                    NativeRegionInvocationOutcome::GuardMiss => "guard-miss",
                };
                write!(f, "committed {label} outcome could not release")?;
            },
            RotateNativeExecutionFailureCause::Runner(error) => {
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

/// Binds, runs, and admits one fused call against an already loaded mapping.
///
/// Runner failure restores the complete whole-region entry snapshot. Completion
/// rejection performs the same restoration through the fused invocation
/// contract. This function neither loads nor releases executable memory.
///
/// # Errors
///
/// Returns [`DirectFusedLoadedExecutionFailure`] for binding, runner, or
/// completion failure.
pub fn execute_loaded_verified_direct_fused_native<Runner>(
    runner: &mut Runner,
    executable: &ReadyDirectFusedNativeExecutable,
    prepared: PreparedDirectFusedInvocation<'_, '_>,
) -> DirectFusedLoadedExecutionResult<Runner::Error>
where
    Runner: DirectFusedNativeRunner,
{
    run_direct_fused_prepared(runner, executable, prepared)
        .map_err(|cause| Box::new(DirectFusedLoadedExecutionFailure { cause }))
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

/// Binds, runs, and admits one v6 Crazy call against a loaded mapping.
///
/// Runner failure restores the complete rebased entry snapshot. Completion
/// rejection performs the same restoration through the invocation contract.
/// This function neither loads nor releases executable memory.
///
/// # Errors
///
/// Returns [`RegisterMaskedCrazyLoadedExecutionFailure`] for binding, runner,
/// or completion failure.
pub fn execute_loaded_verified_register_masked_crazy_native<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedCrazyNativeExecutable,
    prepared: PreparedRegisterMaskedCrazyInvocation<'_, '_>,
) -> RegisterMaskedCrazyLoadedExecutionResult<Runner::Error>
where
    Runner: RegisterMaskedCrazyNativeRunner,
{
    run_register_masked_crazy_prepared(runner, executable, prepared).map_err(
        |cause| Box::new(RegisterMaskedCrazyLoadedExecutionFailure { cause }),
    )
}

/// Binds, runs, and admits one v6 Output call against a loaded mapping.
///
/// Runner failure restores the complete rebased entry snapshot. Completion
/// rejection performs the same restoration through the invocation contract.
/// This function neither loads nor releases executable memory.
///
/// # Errors
///
/// Returns [`RegisterMaskedOutputLoadedExecutionFailure`] for binding, runner,
/// or completion failure.
pub fn execute_loaded_verified_register_masked_output_native<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedOutputNativeExecutable,
    prepared: PreparedRegisterMaskedOutputInvocation<'_, '_>,
) -> RegisterMaskedOutputLoadedExecutionResult<Runner::Error>
where
    Runner: RegisterMaskedOutputNativeRunner,
{
    run_register_masked_output_prepared(runner, executable, prepared).map_err(
        |cause| Box::new(RegisterMaskedOutputLoadedExecutionFailure { cause }),
    )
}

/// Binds, runs, and admits one v6 no-operation call against a loaded mapping.
///
/// Runner failure restores the complete rebased entry snapshot. Completion
/// rejection performs the same restoration through the invocation contract.
/// This function neither loads nor releases executable memory.
///
/// # Errors
///
/// Returns [`RegisterMaskedNoOperationLoadedExecutionFailure`] for binding,
/// runner, or completion failure.
pub fn execute_loaded_verified_register_masked_no_operation_native<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedNoOperationNativeExecutable,
    prepared: PreparedRegisterMaskedNoOperationInvocation<'_, '_>,
) -> RegisterMaskedNoOperationLoadedExecutionResult<Runner::Error>
where
    Runner: RegisterMaskedNoOperationNativeRunner,
{
    run_register_masked_no_operation_prepared(runner, executable, prepared)
        .map_err(|cause| {
            Box::new(RegisterMaskedNoOperationLoadedExecutionFailure { cause })
        })
}

/// Binds, runs, and admits one collapsed-v6 no-op/halt call.
///
/// Runner failure restores the complete rebased entry snapshot. Completion
/// rejection performs the same restoration through the invocation contract.
/// This function neither loads nor releases executable memory.
///
/// # Errors
///
/// Returns the collapsed loaded-execution failure for binding, runner, or
/// completion failure.
pub fn execute_loaded_verified_register_masked_no_operation_halt_native<
    Runner,
>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedNoOperationHaltNativeExecutable,
    prepared: PreparedRegisterMaskedNoOperationHaltInvocation<'_, '_>,
) -> RegisterMaskedNoOperationHaltLoadedExecutionResult<Runner::Error>
where
    Runner: RegisterMaskedNoOperationHaltNativeRunner,
{
    run_register_masked_no_operation_halt_prepared(runner, executable, prepared)
        .map_err(|cause| {
            Box::new(RegisterMaskedNoOperationHaltLoadedExecutionFailure {
                cause,
            })
        })
}

/// Binds, runs, and admits one collapsed-pair-v6 no-operation pair call.
///
/// Runner failure restores the complete rebased entry snapshot. Completion
/// rejection performs the same restoration through the invocation contract.
/// This function neither loads nor releases executable memory.
///
/// # Errors
///
/// Returns the collapsed loaded-execution failure for binding, runner, or
/// completion failure.
pub fn execute_loaded_verified_register_masked_no_operation_pair_native<
    Runner,
>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedNoOperationPairNativeExecutable,
    prepared: PreparedRegisterMaskedNoOperationPairInvocation<'_, '_>,
) -> RegisterMaskedNoOperationPairLoadedExecutionResult<Runner::Error>
where
    Runner: RegisterMaskedNoOperationPairNativeRunner,
{
    run_register_masked_no_operation_pair_prepared(runner, executable, prepared)
        .map_err(|cause| {
            Box::new(RegisterMaskedNoOperationPairLoadedExecutionFailure {
                cause,
            })
        })
}

/// Binds, runs, and admits one collapsed-v6 no-operation/rotate call.
///
/// Runner failure restores the complete rebased entry snapshot. Completion
/// rejection performs the same restoration through the invocation contract.
/// This function neither loads nor releases executable memory.
///
/// # Errors
///
/// Returns the collapsed no-op/rotate loaded-execution failure for binding,
/// runner, or completion failure.
pub fn execute_loaded_verified_register_masked_no_operation_rotate_native<
    Runner,
>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedNoOperationRotateNativeExecutable,
    prepared: PreparedRegisterMaskedNoOperationRotateInvocation<'_, '_>,
) -> RegisterMaskedNoOperationRotateLoadedExecutionResult<Runner::Error>
where
    Runner: RegisterMaskedNoOperationRotateNativeRunner,
{
    run_register_masked_no_operation_rotate_prepared(
        runner, executable, prepared,
    )
    .map_err(|cause| {
        Box::new(RegisterMaskedNoOperationRotateLoadedExecutionFailure {
            cause,
        })
    })
}

/// Binds, runs, and admits one v6 rotate call against a loaded mapping.
///
/// Runner failure restores the complete rebased entry snapshot. Completion
/// rejection performs the same restoration through the invocation contract.
/// This function neither loads nor releases executable memory.
///
/// # Errors
///
/// Returns the rotate loaded-execution failure for binding, runner, or
/// completion failure.
pub fn execute_loaded_verified_register_masked_rotate_native<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedRotateNativeExecutable,
    prepared: PreparedRegisterMaskedRotateInvocation<'_, '_>,
) -> RegisterMaskedRotateLoadedExecutionResult<Runner::Error>
where
    Runner: RegisterMaskedRotateNativeRunner,
{
    run_register_masked_rotate_prepared(runner, executable, prepared).map_err(
        |cause| Box::new(RegisterMaskedRotateLoadedExecutionFailure { cause }),
    )
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

fn crazy_load_failure<MemoryError, RunnerError>(
    error: NativeExecutableLoadFailure<MemoryError>,
) -> RegisterMaskedCrazyNativeExecutionFailure<MemoryError, RunnerError> {
    let release_request = error.release_request();
    RegisterMaskedCrazyNativeExecutionFailure {
        cause: CrazyNativeExecutionFailureCause::Load(Box::new(error)),
        phase: NativeExecutableExecutionPhase::Load,
        release_failure: None,
        release_request,
    }
}

fn output_load_failure<MemoryError, RunnerError>(
    error: NativeExecutableLoadFailure<MemoryError>,
) -> RegisterMaskedOutputNativeExecutionFailure<MemoryError, RunnerError> {
    let release_request = error.release_request();
    RegisterMaskedOutputNativeExecutionFailure {
        cause: OutputNativeExecutionFailureCause::Load(Box::new(error)),
        phase: NativeExecutableExecutionPhase::Load,
        release_failure: None,
        release_request,
    }
}

fn no_operation_load_failure<MemoryError, RunnerError>(
    error: NativeExecutableLoadFailure<MemoryError>,
) -> RegisterMaskedNoOperationNativeExecutionFailure<MemoryError, RunnerError> {
    let release_request = error.release_request();
    RegisterMaskedNoOperationNativeExecutionFailure {
        cause: NoOperationNativeExecutionFailureCause::Load(Box::new(error)),
        phase: NativeExecutableExecutionPhase::Load,
        release_failure: None,
        release_request,
    }
}

fn rotate_load_failure<MemoryError, RunnerError>(
    error: NativeExecutableLoadFailure<MemoryError>,
) -> RegisterMaskedRotateNativeExecutionFailure<MemoryError, RunnerError> {
    let release_request = error.release_request();
    RegisterMaskedRotateNativeExecutionFailure {
        cause: RotateNativeExecutionFailureCause::Load(Box::new(error)),
        phase: NativeExecutableExecutionPhase::Load,
        release_failure: None,
        release_request,
    }
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

fn direct_fused_load_failure<MemoryError, RunnerError>(
    error: NativeExecutableLoadFailure<MemoryError>,
) -> DirectFusedNativeExecutionFailure<MemoryError, RunnerError> {
    let release_request = error.release_request();
    DirectFusedNativeExecutionFailure {
        cause: DirectFusedNativeExecutionFailureCause::Load(Box::new(error)),
        phase: NativeExecutableExecutionPhase::Load,
        release_failure: None,
        release_request,
    }
}

/// Loads, binds, runs, admits, and releases one fused whole-region call.
///
/// Load/call failures restore the complete prepared region entry and attempt
/// exact mapping cleanup. A release failure after a committed result retains
/// both the outcome and exact ready fused executable for retry.
///
/// # Errors
///
/// Returns [`DirectFusedNativeExecutionFailure`] with phase-specific primary
/// and cleanup evidence.
pub fn execute_verified_direct_fused_native<MemoryAdapter, Runner>(
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    prepared: PreparedDirectFusedInvocation<'_, '_>,
) -> DirectFusedNativeAdapterExecutionResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: DirectFusedNativeRunner,
{
    let executable = match load_direct_fused_native_executable(
        memory_adapter,
        prepared.load_image(),
    ) {
        Ok(executable) => executable,
        Err(error) => {
            prepared.abort();
            return Err(Box::new(direct_fused_load_failure(error)));
        },
    };
    let release_request = executable.release_request();
    let outcome = match run_direct_fused_prepared(runner, &executable, prepared)
    {
        Ok(outcome) => outcome,
        Err(error) => {
            let phase = error.phase();
            let release_failure = release_direct_fused_native_executable(
                memory_adapter,
                executable,
            )
            .err()
            .map(Box::new);
            return Err(Box::new(DirectFusedNativeExecutionFailure {
                cause: error.into_cause(),
                phase,
                release_failure,
                release_request: Some(release_request),
            }));
        },
    };
    match release_direct_fused_native_executable(memory_adapter, executable) {
        Ok(()) => Ok(outcome),
        Err(release_failure) => {
            Err(Box::new(DirectFusedNativeExecutionFailure {
                cause: DirectFusedNativeExecutionFailureCause::Release(outcome),
                phase: NativeExecutableExecutionPhase::Release,
                release_failure: Some(Box::new(release_failure)),
                release_request: Some(release_request),
            }))
        },
    }
}

/// Loads, binds, runs, admits, and releases one v6 Crazy call.
///
/// Load/call failures restore the prepared rebased snapshot and attempt exact
/// mapping cleanup. A release failure after a committed result retains both the
/// outcome and exact ready executable for retry.
///
/// # Errors
///
/// Returns [`RegisterMaskedCrazyNativeExecutionFailure`] with phase-specific
/// primary and cleanup evidence.
pub fn execute_verified_register_masked_crazy_native<MemoryAdapter, Runner>(
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    prepared: PreparedRegisterMaskedCrazyInvocation<'_, '_>,
) -> CrazyNativeAdapterExecutionResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: RegisterMaskedCrazyNativeRunner,
{
    let executable = match load_register_masked_crazy_native_executable(
        memory_adapter,
        prepared.load_image(),
    ) {
        Ok(executable) => executable,
        Err(error) => {
            prepared.abort();
            return Err(Box::new(crazy_load_failure(error)));
        },
    };
    let release_request = executable.release_request();
    let outcome =
        match run_register_masked_crazy_prepared(runner, &executable, prepared)
        {
            Ok(outcome) => outcome,
            Err(error) => {
                let phase = error.phase();
                let release_failure =
                    release_register_masked_crazy_native_executable(
                        memory_adapter,
                        executable,
                    )
                    .err()
                    .map(Box::new);
                return Err(Box::new(
                    RegisterMaskedCrazyNativeExecutionFailure {
                        cause: error.into_cause(),
                        phase,
                        release_failure,
                        release_request: Some(release_request),
                    },
                ));
            },
        };
    match release_register_masked_crazy_native_executable(
        memory_adapter,
        executable,
    ) {
        Ok(()) => Ok(outcome),
        Err(release_failure) => {
            Err(Box::new(RegisterMaskedCrazyNativeExecutionFailure {
                cause: CrazyNativeExecutionFailureCause::Release(outcome),
                phase: NativeExecutableExecutionPhase::Release,
                release_failure: Some(Box::new(release_failure)),
                release_request: Some(release_request),
            }))
        },
    }
}

/// Loads, binds, runs, admits, and releases one v6 Output call.
///
/// Load/call failures restore the prepared rebased snapshot and attempt exact
/// mapping cleanup. A release failure after a committed result retains both the
/// outcome and exact ready executable for retry.
///
/// # Errors
///
/// Returns [`RegisterMaskedOutputNativeExecutionFailure`] with phase-specific
/// primary and cleanup evidence.
pub fn execute_verified_register_masked_output_native<MemoryAdapter, Runner>(
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    prepared: PreparedRegisterMaskedOutputInvocation<'_, '_>,
) -> OutputNativeAdapterExecutionResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: RegisterMaskedOutputNativeRunner,
{
    let executable = match load_register_masked_output_native_executable(
        memory_adapter,
        prepared.load_image(),
    ) {
        Ok(executable) => executable,
        Err(error) => {
            prepared.abort();
            return Err(Box::new(output_load_failure(error)));
        },
    };
    let release_request = executable.release_request();
    let outcome = match run_register_masked_output_prepared(
        runner,
        &executable,
        prepared,
    ) {
        Ok(outcome) => outcome,
        Err(error) => {
            let phase = error.phase();
            let release_failure =
                release_register_masked_output_native_executable(
                    memory_adapter,
                    executable,
                )
                .err()
                .map(Box::new);
            return Err(Box::new(RegisterMaskedOutputNativeExecutionFailure {
                cause: error.into_cause(),
                phase,
                release_failure,
                release_request: Some(release_request),
            }));
        },
    };
    match release_register_masked_output_native_executable(
        memory_adapter,
        executable,
    ) {
        Ok(()) => Ok(outcome),
        Err(release_failure) => {
            Err(Box::new(RegisterMaskedOutputNativeExecutionFailure {
                cause: OutputNativeExecutionFailureCause::Release(outcome),
                phase: NativeExecutableExecutionPhase::Release,
                release_failure: Some(Box::new(release_failure)),
                release_request: Some(release_request),
            }))
        },
    }
}

/// Loads, binds, runs, admits, and releases one v6 no-operation call.
///
/// Load/call failures restore the prepared rebased snapshot and attempt exact
/// mapping cleanup. A release failure after a committed result retains both the
/// outcome and exact ready executable for retry.
///
/// # Errors
///
/// Returns [`RegisterMaskedNoOperationNativeExecutionFailure`] with
/// phase-specific primary and cleanup evidence.
pub fn execute_verified_register_masked_no_operation_native<
    MemoryAdapter,
    Runner,
>(
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    prepared: PreparedRegisterMaskedNoOperationInvocation<'_, '_>,
) -> NoOperationNativeAdapterExecutionResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: RegisterMaskedNoOperationNativeRunner,
{
    let executable = match load_register_masked_no_operation_native_executable(
        memory_adapter,
        prepared.load_image(),
    ) {
        Ok(executable) => executable,
        Err(error) => {
            prepared.abort();
            return Err(Box::new(no_operation_load_failure(error)));
        },
    };
    let release_request = executable.release_request();
    let outcome = match run_register_masked_no_operation_prepared(
        runner,
        &executable,
        prepared,
    ) {
        Ok(outcome) => outcome,
        Err(error) => {
            let phase = error.phase();
            let release_failure =
                release_register_masked_no_operation_native_executable(
                    memory_adapter,
                    executable,
                )
                .err()
                .map(Box::new);
            return Err(Box::new(
                RegisterMaskedNoOperationNativeExecutionFailure {
                    cause: error.into_cause(),
                    phase,
                    release_failure,
                    release_request: Some(release_request),
                },
            ));
        },
    };
    match release_register_masked_no_operation_native_executable(
        memory_adapter,
        executable,
    ) {
        Ok(()) => Ok(outcome),
        Err(release_failure) => {
            Err(Box::new(RegisterMaskedNoOperationNativeExecutionFailure {
                cause: NoOperationNativeExecutionFailureCause::Release(outcome),
                phase: NativeExecutableExecutionPhase::Release,
                release_failure: Some(Box::new(release_failure)),
                release_request: Some(release_request),
            }))
        },
    }
}

/// Loads, binds, runs, admits, and releases one v6 rotate call.
///
/// Load/call failures restore the prepared rebased snapshot and attempt exact
/// mapping cleanup. A release failure after a committed result retains both the
/// outcome and exact ready executable for retry.
///
/// # Errors
///
/// Returns the rotate transaction failure with phase-specific primary and
/// cleanup evidence.
pub fn execute_verified_register_masked_rotate_native<MemoryAdapter, Runner>(
    memory_adapter: &mut MemoryAdapter,
    runner: &mut Runner,
    prepared: PreparedRegisterMaskedRotateInvocation<'_, '_>,
) -> RotateNativeAdapterExecutionResult<MemoryAdapter, Runner>
where
    MemoryAdapter: NativeExecutableMemoryAdapter,
    Runner: RegisterMaskedRotateNativeRunner,
{
    let executable = match load_register_masked_rotate_native_executable(
        memory_adapter,
        prepared.load_image(),
    ) {
        Ok(executable) => executable,
        Err(error) => {
            prepared.abort();
            return Err(Box::new(rotate_load_failure(error)));
        },
    };
    let release_request = executable.release_request();
    let outcome = match run_register_masked_rotate_prepared(
        runner,
        &executable,
        prepared,
    ) {
        Ok(outcome) => outcome,
        Err(error) => {
            let phase = error.phase();
            let release_failure =
                release_register_masked_rotate_native_executable(
                    memory_adapter,
                    executable,
                )
                .err()
                .map(Box::new);
            return Err(Box::new(RegisterMaskedRotateNativeExecutionFailure {
                cause: error.into_cause(),
                phase,
                release_failure,
                release_request: Some(release_request),
            }));
        },
    };
    match release_register_masked_rotate_native_executable(
        memory_adapter,
        executable,
    ) {
        Ok(()) => Ok(outcome),
        Err(release_failure) => {
            Err(Box::new(RegisterMaskedRotateNativeExecutionFailure {
                cause: RotateNativeExecutionFailureCause::Release(outcome),
                phase: NativeExecutableExecutionPhase::Release,
                release_failure: Some(Box::new(release_failure)),
                release_request: Some(release_request),
            }))
        },
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

fn run_direct_fused_prepared<Runner>(
    runner: &mut Runner,
    executable: &ReadyDirectFusedNativeExecutable,
    prepared: PreparedDirectFusedInvocation<'_, '_>,
) -> DirectFusedNativeCallResult<Runner>
where
    Runner: DirectFusedNativeRunner,
{
    let mut bound = prepared
        .bind_executable(executable)
        .map_err(DirectFusedNativeCallFailure::Binding)?;
    let raw_status = match runner.run(&mut bound) {
        Ok(status) => status,
        Err(error) => {
            bound.abort();
            return Err(DirectFusedNativeCallFailure::Runner(Box::new(error)));
        },
    };
    bound
        .complete(raw_status)
        .map_err(DirectFusedNativeCallFailure::Completion)
}

fn run_register_masked_crazy_prepared<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedCrazyNativeExecutable,
    prepared: PreparedRegisterMaskedCrazyInvocation<'_, '_>,
) -> RegisterMaskedCrazyNativeCallResult<Runner>
where
    Runner: RegisterMaskedCrazyNativeRunner,
{
    let mut bound = prepared
        .bind_executable(executable)
        .map_err(RegisterMaskedCrazyNativeCallFailure::Binding)?;
    let raw_status = match runner.run(&mut bound) {
        Ok(status) => status,
        Err(error) => {
            bound.abort();
            return Err(RegisterMaskedCrazyNativeCallFailure::Runner(
                Box::new(error),
            ));
        },
    };
    bound
        .complete(raw_status)
        .map_err(RegisterMaskedCrazyNativeCallFailure::Completion)
}

fn run_register_masked_output_prepared<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedOutputNativeExecutable,
    prepared: PreparedRegisterMaskedOutputInvocation<'_, '_>,
) -> RegisterMaskedOutputNativeCallResult<Runner>
where
    Runner: RegisterMaskedOutputNativeRunner,
{
    let mut bound = prepared
        .bind_executable(executable)
        .map_err(RegisterMaskedOutputNativeCallFailure::Binding)?;
    let raw_status = match runner.run(&mut bound) {
        Ok(status) => status,
        Err(error) => {
            bound.abort();
            return Err(RegisterMaskedOutputNativeCallFailure::Runner(
                Box::new(error),
            ));
        },
    };
    bound
        .complete(raw_status)
        .map_err(RegisterMaskedOutputNativeCallFailure::Completion)
}

fn run_register_masked_no_operation_prepared<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedNoOperationNativeExecutable,
    prepared: PreparedRegisterMaskedNoOperationInvocation<'_, '_>,
) -> RegisterMaskedNoOperationNativeCallResult<Runner>
where
    Runner: RegisterMaskedNoOperationNativeRunner,
{
    let mut bound = prepared
        .bind_executable(executable)
        .map_err(RegisterMaskedNoOperationNativeCallFailure::Binding)?;
    let raw_status = match runner.run(&mut bound) {
        Ok(status) => status,
        Err(error) => {
            bound.abort();
            return Err(RegisterMaskedNoOperationNativeCallFailure::Runner(
                Box::new(error),
            ));
        },
    };
    bound
        .complete(raw_status)
        .map_err(RegisterMaskedNoOperationNativeCallFailure::Completion)
}

fn run_register_masked_no_operation_halt_prepared<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedNoOperationHaltNativeExecutable,
    prepared: PreparedRegisterMaskedNoOperationHaltInvocation<'_, '_>,
) -> RegisterMaskedNoOperationHaltNativeCallResult<Runner>
where
    Runner: RegisterMaskedNoOperationHaltNativeRunner,
{
    let mut bound = prepared
        .bind_executable(executable)
        .map_err(RegisterMaskedNoOperationHaltNativeCallFailure::Binding)?;
    let raw_status = match runner.run(&mut bound) {
        Ok(status) => status,
        Err(error) => {
            bound.abort();
            return Err(
                RegisterMaskedNoOperationHaltNativeCallFailure::Runner(
                    Box::new(error),
                ),
            );
        },
    };
    bound
        .complete(raw_status)
        .map_err(RegisterMaskedNoOperationHaltNativeCallFailure::Completion)
}

fn run_register_masked_no_operation_pair_prepared<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedNoOperationPairNativeExecutable,
    prepared: PreparedRegisterMaskedNoOperationPairInvocation<'_, '_>,
) -> RegisterMaskedNoOperationPairNativeCallResult<Runner>
where
    Runner: RegisterMaskedNoOperationPairNativeRunner,
{
    let mut bound = prepared
        .bind_executable(executable)
        .map_err(RegisterMaskedNoOperationPairNativeCallFailure::Binding)?;
    let raw_status = match runner.run(&mut bound) {
        Ok(status) => status,
        Err(error) => {
            bound.abort();
            return Err(
                RegisterMaskedNoOperationPairNativeCallFailure::Runner(
                    Box::new(error),
                ),
            );
        },
    };
    bound
        .complete(raw_status)
        .map_err(RegisterMaskedNoOperationPairNativeCallFailure::Completion)
}

fn run_register_masked_no_operation_rotate_prepared<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedNoOperationRotateNativeExecutable,
    prepared: PreparedRegisterMaskedNoOperationRotateInvocation<'_, '_>,
) -> RegisterMaskedNoOperationRotateNativeCallResult<Runner>
where
    Runner: RegisterMaskedNoOperationRotateNativeRunner,
{
    let mut bound = prepared
        .bind_executable(executable)
        .map_err(RegisterMaskedNoOperationRotateNativeCallFailure::Binding)?;
    let raw_status = match runner.run(&mut bound) {
        Ok(status) => status,
        Err(error) => {
            bound.abort();
            return Err(
                RegisterMaskedNoOperationRotateNativeCallFailure::Runner(
                    Box::new(error),
                ),
            );
        },
    };
    bound
        .complete(raw_status)
        .map_err(RegisterMaskedNoOperationRotateNativeCallFailure::Completion)
}

fn run_register_masked_rotate_prepared<Runner>(
    runner: &mut Runner,
    executable: &ReadyRegisterMaskedRotateNativeExecutable,
    prepared: PreparedRegisterMaskedRotateInvocation<'_, '_>,
) -> RegisterMaskedRotateNativeCallResult<Runner>
where
    Runner: RegisterMaskedRotateNativeRunner,
{
    let mut bound = prepared
        .bind_executable(executable)
        .map_err(RegisterMaskedRotateNativeCallFailure::Binding)?;
    let raw_status = match runner.run(&mut bound) {
        Ok(status) => status,
        Err(error) => {
            bound.abort();
            return Err(RegisterMaskedRotateNativeCallFailure::Runner(
                Box::new(error),
            ));
        },
    };
    bound
        .complete(raw_status)
        .map_err(RegisterMaskedRotateNativeCallFailure::Completion)
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

/// Loads, calls, admits, and releases one fused whole-region call through one
/// stateful native host.
///
/// This is the ownership-safe fused counterpart to
/// `execute_verified_native_with_host`. A single mutable host therefore spans
/// executable-memory lifecycle and the MBNPC1 call exchange.
///
/// # Errors
///
/// Returns phase-specific load, call, or release evidence when the fused
/// native transaction cannot complete cleanly.
pub fn execute_verified_direct_fused_native_with_host<Host>(
    host: &mut Host,
    prepared: PreparedDirectFusedInvocation<'_, '_>,
) -> DirectFusedNativeAdapterExecutionResult<Host, Host>
where
    Host: NativeExecutableMemoryAdapter + DirectFusedNativeRunner,
{
    let executable = match load_direct_fused_native_executable(
        host,
        prepared.load_image(),
    ) {
        Ok(executable) => executable,
        Err(load_error) => {
            prepared.abort();
            return Err(Box::new(direct_fused_load_failure(load_error)));
        },
    };
    let release_request = executable.release_request();
    let outcome = match run_direct_fused_prepared(host, &executable, prepared) {
        Ok(outcome) => outcome,
        Err(call_failure) => {
            let phase = call_failure.phase();
            let release_failure =
                release_direct_fused_native_executable(host, executable)
                    .err()
                    .map(Box::new);
            return Err(Box::new(DirectFusedNativeExecutionFailure {
                cause: match call_failure {
                    DirectFusedNativeCallFailure::Binding(binding_error) => {
                        DirectFusedNativeExecutionFailureCause::Binding(
                            binding_error,
                        )
                    },
                    DirectFusedNativeCallFailure::Runner(runner_error) => {
                        DirectFusedNativeExecutionFailureCause::Runner(
                            runner_error,
                        )
                    },
                    DirectFusedNativeCallFailure::Completion(
                        completion_error,
                    ) => DirectFusedNativeExecutionFailureCause::Completion(
                        completion_error,
                    ),
                },
                phase,
                release_failure,
                release_request: Some(release_request),
            }));
        },
    };
    match release_direct_fused_native_executable(host, executable) {
        Ok(()) => Ok(outcome),
        Err(release_failure) => {
            Err(Box::new(DirectFusedNativeExecutionFailure {
                cause: DirectFusedNativeExecutionFailureCause::Release(outcome),
                phase: NativeExecutableExecutionPhase::Release,
                release_failure: Some(Box::new(release_failure)),
                release_request: Some(release_request),
            }))
        },
    }
}

/// Loads, calls, admits, and releases through one stateful native host.
///
/// This is the ownership-safe orchestration seam for adapters whose executable
/// mappings and calls must share one persistent session. It preserves the same
/// rollback and release semantics as [`execute_verified_native`] without
/// requiring two mutable aliases to the host.
///
/// # Errors
///
/// Returns [`NativeExecutableExecutionFailure`] with the same phase-specific
/// primary and cleanup evidence as the split-adapter orchestration.
pub fn execute_verified_native_with_host<Host>(
    host: &mut Host,
    prepared_call: PreparedVerifiedDirectInvocation<'_, '_>,
) -> NativeExecutableHostExecutionResult<Host>
where
    Host: NativeExecutableMemoryAdapter + NativeExecutableRunner,
{
    let LoadedNativeExecution {
        executable,
        prepared,
        release_request,
    } = load_prepared::<Host, Host>(host, prepared_call)?;
    let outcome = match run_prepared(host, &executable, prepared) {
        Ok(outcome) => outcome,
        Err(error) => {
            return Err(Box::new(fail_after_ready(
                host,
                executable,
                release_request,
                error,
            )));
        },
    };
    release_committed(host, executable, release_request, outcome)
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
