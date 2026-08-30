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
//   - Serialized mutation of one heterogeneous v5 resident cache and adapter.
// - Must-Not:
//   - Recover poisoned mutation authority or duplicate resident policy.
// - Allows:
//   - Inputs: typed plans, resource limits, and the owned memory adapter.
//   - Outputs: existing acquisitions, releases, usage, and reconfiguration.
//   - Side effects: serialized executable mapping lifecycle operations.
// - Split-When:
//   - Split when read-side concurrency requires policy beyond one mutex.
// - Merge-When:
//   - Merge when cache policy itself becomes intrinsically synchronized.
// - Summary:
//   - Serializes heterogeneous v5 cache mutation without serializing leases.
// - Description:
//   - Owns the cache and its memory adapter under one fail-closed mutex.
// - Usage:
//   - Share this owner with `Arc`; execute returned leases outside the lock.
// - Defaults:
//   - Mutex poisoning rejects future access instead of recovering authority.
//

//! Fail-closed concurrent owner for the heterogeneous explicit-geometry LRU.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::sync::{Mutex, MutexGuard, TryLockError};

use crate::execution_native::{
    ExecutionGeometryNativeRunner, NativeExecutableMemoryAdapter,
    NativeRegionBuffers,
};
use crate::geometry_native_cross_template_cache::{
    GeometryNativeCrossTemplateCachedExecution,
    GeometryNativeCrossTemplateCachedExecutionFailure,
    GeometryNativeCrossTemplateLruAcquireFailure,
    GeometryNativeCrossTemplateLruAcquisition,
    GeometryNativeCrossTemplateLruCache, GeometryNativeCrossTemplateLruLimits,
    GeometryNativeCrossTemplateLruReconfiguration,
    GeometryNativeCrossTemplateLruReconfigurationFailure,
    GeometryNativeCrossTemplateLruRelease,
    GeometryNativeCrossTemplateLruReleaseAll,
    GeometryNativeCrossTemplateLruReleaseAllFailure,
    GeometryNativeCrossTemplateLruUsage,
};
use crate::geometry_native_cross_template_resident::{
    GeometryNativeResidentLoadFailure, GeometryNativeResidentPlan,
    GeometryNativeResidentReleaseFailure, GeometryNativeResidentWeightError,
};

type CacheAcquireFailure<MemoryError> =
    GeometryNativeCrossTemplateLruAcquireFailure<MemoryError>;
type CacheReconfigurationFailure<MemoryError> =
    GeometryNativeCrossTemplateLruReconfigurationFailure<MemoryError>;
type CacheReleaseFailure<MemoryError> =
    GeometryNativeResidentReleaseFailure<MemoryError>;
type CacheReleaseAllFailure<MemoryError> =
    GeometryNativeCrossTemplateLruReleaseAllFailure<MemoryError>;
type CleanupRetryFailure<MemoryError> =
    GeometryNativeConcurrentCrossTemplateCleanupRetryFailure<MemoryError>;
type LoadCleanupFailure<MemoryError> =
    GeometryNativeConcurrentCrossTemplateLoadCleanupRetryFailure<MemoryError>;
type ResidentLoadFailure<MemoryError> =
    GeometryNativeResidentLoadFailure<MemoryError>;
type ReleaseAllRetryFailure<MemoryError> =
    GeometryNativeConcurrentCrossTemplateReleaseAllRetryFailure<MemoryError>;
type ConcurrentAcquireFailure<MemoryError> =
    GeometryNativeConcurrentCrossTemplateFailure<
        Box<CacheAcquireFailure<MemoryError>>,
    >;
type ConcurrentExecutionFailure<MemoryError, RunnerError> =
    GeometryNativeConcurrentCrossTemplateExecutionFailure<
        MemoryError,
        RunnerError,
    >;
type ConcurrentExecutionResult<Adapter, Runner> =
    GeometryNativeConcurrentCrossTemplateExecutionResult<
        <Adapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as ExecutionGeometryNativeRunner>::Error,
    >;
type ConcurrentStateGuard<'cache, Adapter> =
    MutexGuard<'cache, GeometryNativeConcurrentCrossTemplateState<Adapter>>;
type TryAcquireFailure<MemoryError> =
    GeometryNativeConcurrentCrossTemplateTryFailure<
        Box<CacheAcquireFailure<MemoryError>>,
    >;
type TryExecutionFailure<MemoryError, RunnerError> =
    GeometryNativeConcurrentCrossTemplateTryExecutionFailure<
        MemoryError,
        RunnerError,
    >;
type TryExecutionResult<Adapter, Runner> =
    GeometryNativeConcurrentCrossTemplateTryExecutionResult<
        <Adapter as NativeExecutableMemoryAdapter>::Error,
        <Runner as ExecutionGeometryNativeRunner>::Error,
    >;
type TryReconfigurationFailure<MemoryError> =
    GeometryNativeConcurrentCrossTemplateTryFailure<
        Box<CacheReconfigurationFailure<MemoryError>>,
    >;
type TryReleaseAllFailure<MemoryError> =
    GeometryNativeConcurrentCrossTemplateTryFailure<
        Box<CacheReleaseAllFailure<MemoryError>>,
    >;
type TryReleaseAllResult<Adapter> =
    GeometryNativeConcurrentCrossTemplateTryReleaseAllResult<
        <Adapter as NativeExecutableMemoryAdapter>::Error,
    >;
type TryReleaseFailure<MemoryError> =
    GeometryNativeConcurrentCrossTemplateTryFailure<
        Box<CacheReleaseFailure<MemoryError>>,
    >;
type TrySnapshotFailure =
    GeometryNativeConcurrentCrossTemplateTrySnapshotFailure;

/// Failure to acquire synchronized access to heterogeneous resident authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeConcurrentCrossTemplateAccessError {
    /// A prior panic may have interrupted mutation while authority was locked.
    Poisoned,
}

/// Failure from one serialized cache operation.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeConcurrentCrossTemplateFailure<OperationError> {
    /// Existing cache or adapter operation failed with its exact evidence.
    Operation(OperationError),
    /// A prior panic poisoned mutation authority, so access is rejected.
    Poisoned,
}

/// Failure from one nonblocking synchronized cache operation.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeConcurrentCrossTemplateTryFailure<OperationError> {
    /// Another thread currently owns the mutation mutex.
    Busy,
    /// Existing cache or adapter operation failed with exact evidence.
    Operation(OperationError),
    /// Prior mutation unwinding poisoned cache authority.
    Poisoned,
}

/// Failure while retrying transferred resident cleanup with the owned adapter.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeConcurrentCrossTemplateCleanupRetryFailure<MemoryError> {
    /// Another thread owns mutation authority; cleanup was not attempted.
    Busy(Box<CacheReleaseFailure<MemoryError>>),
    /// The cache was already poisoned, so cleanup was not attempted.
    Poisoned(Box<CacheReleaseFailure<MemoryError>>),
    /// Cleanup was retried and still retains mapping ownership.
    Release(Box<CacheReleaseFailure<MemoryError>>),
}

/// Outcome of retrying rollback retained by a primary resident load failure.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeConcurrentCrossTemplateLoadCleanupRetry<MemoryError> {
    /// All rollback is complete; the primary load failure remains evidence.
    Clean(Box<ResidentLoadFailure<MemoryError>>),
    /// Rollback still owns mappings after another failed release attempt.
    Pending(Box<ResidentLoadFailure<MemoryError>>),
}

/// Failure before resident load rollback could be retried.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeConcurrentCrossTemplateLoadCleanupRetryFailure<
    MemoryError,
> {
    /// Another thread owns mutation authority; the failure is untouched.
    Busy(Box<ResidentLoadFailure<MemoryError>>),
    /// Cache authority is poisoned; the original failure is untouched.
    Poisoned(Box<ResidentLoadFailure<MemoryError>>),
}

/// Failure while retrying one aggregate release-all cleanup token.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeConcurrentCrossTemplateReleaseAllRetryFailure<
    MemoryError,
> {
    /// Another thread owns mutation authority; the token is untouched.
    Busy(Box<CacheReleaseAllFailure<MemoryError>>),
    /// Cache authority is poisoned; the aggregate token is untouched.
    Poisoned(Box<CacheReleaseAllFailure<MemoryError>>),
    /// Retry still retains at least one exact resident cleanup owner.
    Release(Box<CacheReleaseAllFailure<MemoryError>>),
}

/// Failure from one acquire-then-execute concurrent cache request.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeConcurrentCrossTemplateExecutionFailure<
    MemoryError,
    RunnerError,
> {
    /// Resident acquisition failed before native execution began.
    Acquire(Box<ConcurrentAcquireFailure<MemoryError>>),
    /// Native execution failed after a resident acquisition completed.
    Execution(
        Box<GeometryNativeCrossTemplateCachedExecutionFailure<RunnerError>>,
    ),
}

/// Failure from one nonblocking acquire-then-execute cache request.
#[derive(Debug, Eq, PartialEq)]
pub enum GeometryNativeConcurrentCrossTemplateTryExecutionFailure<
    MemoryError,
    RunnerError,
> {
    /// Nonblocking resident acquisition failed before execution began.
    Acquire(Box<TryAcquireFailure<MemoryError>>),
    /// Native execution failed after nonblocking acquisition succeeded.
    Execution(
        Box<GeometryNativeCrossTemplateCachedExecutionFailure<RunnerError>>,
    ),
}

/// One coherent read-side observation taken under a single cache lock.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GeometryNativeConcurrentCrossTemplateSnapshot {
    leases: usize,
    limits: GeometryNativeCrossTemplateLruLimits,
    resident: bool,
    usage: GeometryNativeCrossTemplateLruUsage,
}

/// Failure from one nonblocking coherent snapshot attempt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GeometryNativeConcurrentCrossTemplateTrySnapshotFailure {
    /// Another thread currently owns the mutation mutex.
    Busy,
    /// Prior mutation unwinding poisoned cache authority.
    Poisoned,
    /// Exact resident-weight aggregation failed while reading the snapshot.
    ResidentWeight(GeometryNativeResidentWeightError),
}

/// One heterogeneous cache and its mapping adapter under a shared mutation
/// lock.
#[derive(Debug)]
pub struct GeometryNativeConcurrentCrossTemplateLruCache<Adapter> {
    inner: Mutex<GeometryNativeConcurrentCrossTemplateState<Adapter>>,
}

#[derive(Debug)]
struct GeometryNativeConcurrentCrossTemplateState<Adapter> {
    adapter: Adapter,
    cache: GeometryNativeCrossTemplateLruCache,
}

/// Result of one synchronized heterogeneous resident acquisition.
pub type GeometryNativeConcurrentCrossTemplateAcquireResult<MemoryError> =
    Result<
        GeometryNativeCrossTemplateLruAcquisition,
        GeometryNativeConcurrentCrossTemplateFailure<
            Box<CacheAcquireFailure<MemoryError>>,
        >,
    >;

/// Result of retrying one transferred heterogeneous cleanup token.
pub type GeometryNativeConcurrentCrossTemplateCleanupRetryResult<MemoryError> =
    Result<
        (),
        Box<
            GeometryNativeConcurrentCrossTemplateCleanupRetryFailure<
                MemoryError,
            >,
        >,
    >;

/// Result of acquiring and executing one synchronized resident request.
pub type GeometryNativeConcurrentCrossTemplateExecutionResult<
    MemoryError,
    RunnerError,
> = Result<
    GeometryNativeCrossTemplateCachedExecution,
    Box<
        GeometryNativeConcurrentCrossTemplateExecutionFailure<
            MemoryError,
            RunnerError,
        >,
    >,
>;

/// Result of retrying rollback retained by a primary resident load failure.
pub type GeometryNativeConcurrentCrossTemplateLoadCleanupRetryResult<
    MemoryError,
> = Result<
    GeometryNativeConcurrentCrossTemplateLoadCleanupRetry<MemoryError>,
    Box<
        GeometryNativeConcurrentCrossTemplateLoadCleanupRetryFailure<
            MemoryError,
        >,
    >,
>;

/// Result of publishing synchronized replacement resource limits.
pub type GeometryNativeConcurrentCrossTemplateReconfigurationResult<
    MemoryError,
> = Result<
    GeometryNativeCrossTemplateLruReconfiguration,
    GeometryNativeConcurrentCrossTemplateFailure<
        Box<CacheReconfigurationFailure<MemoryError>>,
    >,
>;

/// Result of releasing every currently unleased resident under one lock.
pub type GeometryNativeConcurrentCrossTemplateReleaseAllResult<MemoryError> =
    Result<
        GeometryNativeCrossTemplateLruReleaseAll,
        GeometryNativeConcurrentCrossTemplateFailure<
            Box<CacheReleaseAllFailure<MemoryError>>,
        >,
    >;

/// Result of retrying one aggregate release-all cleanup token.
pub type GeometryNativeConcurrentCrossTemplateReleaseAllRetryResult<
    MemoryError,
> = Result<
    GeometryNativeCrossTemplateLruReleaseAll,
    Box<
        GeometryNativeConcurrentCrossTemplateReleaseAllRetryFailure<
            MemoryError,
        >,
    >,
>;

/// Result of releasing one exact typed resident through synchronized mutation.
pub type GeometryNativeConcurrentCrossTemplateReleaseResult<MemoryError> =
    Result<
        GeometryNativeCrossTemplateLruRelease,
        GeometryNativeConcurrentCrossTemplateFailure<
            Box<CacheReleaseFailure<MemoryError>>,
        >,
    >;

/// Result of reading one coherent resident/cache snapshot.
pub type GeometryNativeConcurrentCrossTemplateSnapshotResult = Result<
    GeometryNativeConcurrentCrossTemplateSnapshot,
    GeometryNativeConcurrentCrossTemplateFailure<
        GeometryNativeResidentWeightError,
    >,
>;

/// Result of one nonblocking heterogeneous resident acquisition.
pub type GeometryNativeConcurrentCrossTemplateTryAcquireResult<MemoryError> =
    Result<
        GeometryNativeCrossTemplateLruAcquisition,
        TryAcquireFailure<MemoryError>,
    >;

/// Result of one nonblocking acquire-then-execute request.
pub type GeometryNativeConcurrentCrossTemplateTryExecutionResult<
    MemoryError,
    RunnerError,
> = Result<
    GeometryNativeCrossTemplateCachedExecution,
    Box<
        GeometryNativeConcurrentCrossTemplateTryExecutionFailure<
            MemoryError,
            RunnerError,
        >,
    >,
>;

/// Result of one nonblocking heterogeneous limit reconfiguration.
pub type GeometryNativeConcurrentCrossTemplateTryReconfigurationResult<
    MemoryError,
> = Result<
    GeometryNativeCrossTemplateLruReconfiguration,
    TryReconfigurationFailure<MemoryError>,
>;

/// Result of one nonblocking release-all request.
pub type GeometryNativeConcurrentCrossTemplateTryReleaseAllResult<MemoryError> =
    Result<
        GeometryNativeCrossTemplateLruReleaseAll,
        TryReleaseAllFailure<MemoryError>,
    >;

/// Result of one nonblocking exact resident release request.
pub type GeometryNativeConcurrentCrossTemplateTryReleaseResult<MemoryError> =
    Result<
        GeometryNativeCrossTemplateLruRelease,
        TryReleaseFailure<MemoryError>,
    >;

/// Result of one nonblocking coherent resident/cache snapshot.
pub type GeometryNativeConcurrentCrossTemplateTrySnapshotResult = Result<
    GeometryNativeConcurrentCrossTemplateSnapshot,
    GeometryNativeConcurrentCrossTemplateTrySnapshotFailure,
>;

/// Result of reading exact synchronized aggregate resident usage.
pub type GeometryNativeConcurrentCrossTemplateUsageResult = Result<
    GeometryNativeCrossTemplateLruUsage,
    GeometryNativeConcurrentCrossTemplateFailure<
        GeometryNativeResidentWeightError,
    >,
>;

impl Display for GeometryNativeConcurrentCrossTemplateAccessError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Poisoned => {
                f.write_str("heterogeneous v5 cache lock is poisoned")
            },
        }
    }
}

impl<OperationError: Display> Display
    for GeometryNativeConcurrentCrossTemplateFailure<OperationError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Operation(error) => Display::fmt(error, f),
            Self::Poisoned => {
                f.write_str("heterogeneous v5 cache lock is poisoned")
            },
        }
    }
}

impl<MemoryError: Display> Display
    for GeometryNativeConcurrentCrossTemplateCleanupRetryFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Busy(cleanup) => write!(
                f,
                "heterogeneous v5 cleanup blocked by busy cache: {cleanup}"
            ),
            Self::Poisoned(cleanup) => write!(
                f,
                "heterogeneous v5 cleanup blocked by poisoned cache: {cleanup}"
            ),
            Self::Release(cleanup) => {
                write!(f, "heterogeneous v5 cleanup retry failed: {cleanup}")
            },
        }
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for GeometryNativeConcurrentCrossTemplateExecutionFailure<
        MemoryError,
        RunnerError,
    >
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Acquire(error) => {
                write!(f, "heterogeneous v5 concurrent acquire failed: {error}")
            },
            Self::Execution(error) => {
                write!(
                    f,
                    "heterogeneous v5 concurrent execution failed: {error}"
                )
            },
        }
    }
}

impl<MemoryError: Display> Display
    for GeometryNativeConcurrentCrossTemplateLoadCleanupRetryFailure<
        MemoryError,
    >
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Busy(error) => write!(
                f,
                "v5 concurrent load cleanup blocked by busy cache: {error}"
            ),
            Self::Poisoned(error) => write!(
                f,
                "v5 concurrent load cleanup blocked by poisoned cache: {error}"
            ),
        }
    }
}

impl<MemoryError: Display> Display
    for GeometryNativeConcurrentCrossTemplateReleaseAllRetryFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Busy(error) => write!(
                f,
                "v5 concurrent release-all retry blocked by busy cache: {error}"
            ),
            Self::Poisoned(error) => write!(
                f,
                "v5 concurrent release-all retry blocked by poison: {error}"
            ),
            Self::Release(error) => write!(
                f,
                "v5 concurrent release-all retry retained cleanup: {error}"
            ),
        }
    }
}

impl<MemoryError: Display, RunnerError: Display> Display
    for GeometryNativeConcurrentCrossTemplateTryExecutionFailure<
        MemoryError,
        RunnerError,
    >
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Acquire(error) => {
                write!(f, "heterogeneous v5 try-acquire failed: {error}")
            },
            Self::Execution(error) => {
                write!(f, "heterogeneous v5 try-execution failed: {error}")
            },
        }
    }
}

impl<OperationError: Display> Display
    for GeometryNativeConcurrentCrossTemplateTryFailure<OperationError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Busy => {
                f.write_str("heterogeneous v5 cache mutation is busy")
            },
            Self::Operation(error) => Display::fmt(error, f),
            Self::Poisoned => {
                f.write_str("heterogeneous v5 cache lock is poisoned")
            },
        }
    }
}

impl Display for GeometryNativeConcurrentCrossTemplateTrySnapshotFailure {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Busy => {
                f.write_str("heterogeneous v5 cache snapshot is busy")
            },
            Self::Poisoned => {
                f.write_str("heterogeneous v5 cache lock is poisoned")
            },
            Self::ResidentWeight(error) => Display::fmt(error, f),
        }
    }
}

impl<MemoryError>
    GeometryNativeConcurrentCrossTemplateLoadCleanupRetry<MemoryError>
{
    /// Returns the preserved primary resident load failure.
    #[must_use]
    pub fn failure(&self) -> &ResidentLoadFailure<MemoryError> {
        match self {
            Self::Clean(failure) | Self::Pending(failure) => failure,
        }
    }

    /// Consumes the retry outcome and returns the primary load failure.
    #[must_use]
    pub fn into_failure(self) -> ResidentLoadFailure<MemoryError> {
        match self {
            Self::Clean(failure) | Self::Pending(failure) => *failure,
        }
    }
}

impl GeometryNativeConcurrentCrossTemplateSnapshot {
    /// Returns external leases currently retaining the observed identity.
    #[must_use]
    pub const fn leases(self) -> usize {
        self.leases
    }

    /// Returns the resource limits published in this observation.
    #[must_use]
    pub const fn limits(self) -> GeometryNativeCrossTemplateLruLimits {
        self.limits
    }

    /// Reports whether the observed exact identity is resident.
    #[must_use]
    pub const fn resident(self) -> bool {
        self.resident
    }

    /// Returns aggregate exact mapping usage from the same observation.
    #[must_use]
    pub const fn usage(self) -> GeometryNativeCrossTemplateLruUsage {
        self.usage
    }
}

impl<Adapter> GeometryNativeConcurrentCrossTemplateLruCache<Adapter>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    /// Reports whether one exact typed plan is currently resident.
    ///
    /// # Errors
    ///
    /// Returns poison when prior mutation may have unwound while locked.
    pub fn contains(
        &self,
        plan: &GeometryNativeResidentPlan,
    ) -> Result<bool, GeometryNativeConcurrentCrossTemplateAccessError> {
        Ok(self.lock()?.cache.contains(plan))
    }

    /// Serializes one exact heterogeneous resident acquisition.
    ///
    /// Returned leases outlive the mutex guard and therefore do not serialize
    /// native execution. The owned adapter remains paired with this cache for
    /// every later eviction or explicit release.
    ///
    /// # Errors
    ///
    /// Returns poison or the exact existing cache acquisition failure.
    pub fn ensure(
        &self,
        plan: &GeometryNativeResidentPlan,
    ) -> GeometryNativeConcurrentCrossTemplateAcquireResult<Adapter::Error>
    {
        let mut state = self.lock().map_err(|_error| {
            GeometryNativeConcurrentCrossTemplateFailure::Poisoned
        })?;
        let GeometryNativeConcurrentCrossTemplateState { adapter, cache } =
            &mut *state;
        let result = cache
            .ensure(adapter, plan)
            .map_err(GeometryNativeConcurrentCrossTemplateFailure::Operation);
        drop(state);
        result
    }

    /// Acquires under synchronized mutation, then executes outside the lock.
    ///
    /// The acquisition owns an `Arc` lease after [`Self::ensure`] releases its
    /// mutex guard. Native execution therefore does not block cache reads or
    /// other mutation attempts, while that lease still prevents illegal
    /// eviction of the executing resident.
    ///
    /// # Errors
    ///
    /// Returns an acquire-phase failure before execution, or the exact typed
    /// cached execution failure after successful acquisition.
    pub fn execute<Runner>(
        &self,
        plan: &GeometryNativeResidentPlan,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> ConcurrentExecutionResult<Adapter, Runner>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let acquisition = self.ensure(plan).map_err(|error| {
            Box::new(ConcurrentExecutionFailure::Acquire(Box::new(error)))
        })?;
        acquisition.execute(runner, buffers).map_err(|error| {
            Box::new(ConcurrentExecutionFailure::Execution(error))
        })
    }

    /// Returns the currently published resource limits.
    ///
    /// # Errors
    ///
    /// Returns poison when prior mutation may have unwound while locked.
    pub fn limits(
        &self,
    ) -> Result<
        GeometryNativeCrossTemplateLruLimits,
        GeometryNativeConcurrentCrossTemplateAccessError,
    > {
        Ok(self.lock()?.cache.limits())
    }

    fn lock(
        &self,
    ) -> Result<
        ConcurrentStateGuard<'_, Adapter>,
        GeometryNativeConcurrentCrossTemplateAccessError,
    > {
        self.inner.lock().map_err(|_error| {
            GeometryNativeConcurrentCrossTemplateAccessError::Poisoned
        })
    }

    /// Constructs one empty synchronized heterogeneous cache with its adapter.
    #[must_use]
    pub const fn new(
        adapter: Adapter,
        limits: GeometryNativeCrossTemplateLruLimits,
    ) -> Self {
        Self {
            inner: Mutex::new(GeometryNativeConcurrentCrossTemplateState {
                adapter,
                cache: GeometryNativeCrossTemplateLruCache::new_with_limits(
                    limits,
                ),
            }),
        }
    }

    /// Serializes transactional replacement of resident resource limits.
    ///
    /// # Errors
    ///
    /// Returns poison or the exact existing reconfiguration failure evidence.
    pub fn reconfigure_limits(
        &self,
        requested_limits: GeometryNativeCrossTemplateLruLimits,
    ) -> GeometryNativeConcurrentCrossTemplateReconfigurationResult<
        Adapter::Error,
    > {
        let mut state = self.lock().map_err(|_error| {
            GeometryNativeConcurrentCrossTemplateFailure::Poisoned
        })?;
        let GeometryNativeConcurrentCrossTemplateState { adapter, cache } =
            &mut *state;
        let result = cache
            .reconfigure_limits(adapter, requested_limits)
            .map_err(GeometryNativeConcurrentCrossTemplateFailure::Operation);
        drop(state);
        result
    }

    /// Releases every currently unleased heterogeneous resident under one lock.
    ///
    /// Leased identities remain resident and lookup-visible. Any failed release
    /// transfers exact plan plus typed cleanup ownership out of cache
    /// authority.
    ///
    /// # Errors
    ///
    /// Returns poison or the aggregate existing release-all failure evidence.
    pub fn release_all_unleased(
        &self,
    ) -> GeometryNativeConcurrentCrossTemplateReleaseAllResult<Adapter::Error>
    {
        let mut state = self.lock().map_err(|_error| {
            GeometryNativeConcurrentCrossTemplateFailure::Poisoned
        })?;
        let GeometryNativeConcurrentCrossTemplateState { adapter, cache } =
            &mut *state;
        let result = cache
            .release_all_unleased(adapter)
            .map_err(GeometryNativeConcurrentCrossTemplateFailure::Operation);
        drop(state);
        result
    }

    /// Releases one exact typed resident when external leases permit it.
    ///
    /// # Errors
    ///
    /// Returns poison or exact variant-specific cleanup ownership.
    pub fn release_if_unleased(
        &self,
        plan: &GeometryNativeResidentPlan,
    ) -> GeometryNativeConcurrentCrossTemplateReleaseResult<Adapter::Error>
    {
        let mut state = self.lock().map_err(|_error| {
            GeometryNativeConcurrentCrossTemplateFailure::Poisoned
        })?;
        let GeometryNativeConcurrentCrossTemplateState { adapter, cache } =
            &mut *state;
        let result = cache
            .release_if_unleased(adapter, plan)
            .map_err(GeometryNativeConcurrentCrossTemplateFailure::Operation);
        drop(state);
        result
    }

    /// Returns the number of currently resident typed owners.
    ///
    /// # Errors
    ///
    /// Returns poison when prior mutation may have unwound while locked.
    pub fn resident_count(
        &self,
    ) -> Result<usize, GeometryNativeConcurrentCrossTemplateAccessError> {
        Ok(self.lock()?.cache.resident_count())
    }

    /// Retries transferred resident cleanup with this cache's owned adapter.
    ///
    /// The cache itself no longer owns mappings represented by the cleanup
    /// token. This method only restores access to the exact adapter authority
    /// required by the token's existing
    /// [`GeometryNativeResidentReleaseFailure::retry`] contract.
    ///
    /// # Errors
    ///
    /// Returns the untouched cleanup token when authority is already poisoned,
    /// or refreshed cleanup ownership when release fails again.
    pub fn retry_cleanup(
        &self,
        cleanup: Box<CacheReleaseFailure<Adapter::Error>>,
    ) -> GeometryNativeConcurrentCrossTemplateCleanupRetryResult<Adapter::Error>
    {
        let mut state = match self.lock() {
            Ok(state) => state,
            Err(_error) => {
                return Err(Box::new(CleanupRetryFailure::Poisoned(cleanup)));
            },
        };
        let result = (*cleanup)
            .retry(&mut state.adapter)
            .map_err(|error| Box::new(CleanupRetryFailure::Release(error)));
        drop(state);
        result
    }

    /// Retries rollback retained by one primary resident load failure.
    ///
    /// The primary template, load phase, and load cause stay intact. This
    /// method only restores access to the owned adapter for rollback
    /// releases that failed during the original load transaction.
    ///
    /// # Errors
    ///
    /// Returns the untouched primary failure when cache authority is poisoned.
    pub fn retry_load_cleanup(
        &self,
        failure: Box<ResidentLoadFailure<Adapter::Error>>,
    ) -> GeometryNativeConcurrentCrossTemplateLoadCleanupRetryResult<
        Adapter::Error,
    > {
        let mut state = match self.lock() {
            Ok(state) => state,
            Err(_error) => {
                return Err(Box::new(LoadCleanupFailure::Poisoned(failure)));
            },
        };
        let retried = Box::new((*failure).retry_cleanup(&mut state.adapter));
        let outcome = if retried.cleanup_pending() {
            GeometryNativeConcurrentCrossTemplateLoadCleanupRetry::Pending(
                retried,
            )
        } else {
            GeometryNativeConcurrentCrossTemplateLoadCleanupRetry::Clean(
                retried,
            )
        };
        drop(state);
        Ok(outcome)
    }

    /// Retries aggregate release-all cleanup with this cache's owned adapter.
    ///
    /// # Errors
    ///
    /// Returns the untouched aggregate token after poison or a refreshed token
    /// when at least one release fails again.
    pub fn retry_release_all_cleanup(
        &self,
        failure: Box<CacheReleaseAllFailure<Adapter::Error>>,
    ) -> GeometryNativeConcurrentCrossTemplateReleaseAllRetryResult<
        Adapter::Error,
    > {
        let mut state = match self.lock() {
            Ok(state) => state,
            Err(_error) => {
                return Err(Box::new(ReleaseAllRetryFailure::Poisoned(
                    failure,
                )));
            },
        };
        let result = (*failure)
            .retry(&mut state.adapter)
            .map_err(|error| Box::new(ReleaseAllRetryFailure::Release(error)));
        drop(state);
        result
    }

    /// Reads identity state, limits, leases, and usage under one lock.
    ///
    /// This avoids composing separately locked reads that could observe
    /// different mutation epochs.
    ///
    /// # Errors
    ///
    /// Returns poison or exact resident-weight overflow evidence without
    /// publishing a partial snapshot.
    pub fn snapshot(
        &self,
        plan: &GeometryNativeResidentPlan,
    ) -> GeometryNativeConcurrentCrossTemplateSnapshotResult {
        let state = self.lock().map_err(|_error| {
            GeometryNativeConcurrentCrossTemplateFailure::Poisoned
        })?;
        let snapshot = Self::snapshot_from_state(&state, plan)
            .map_err(GeometryNativeConcurrentCrossTemplateFailure::Operation);
        drop(state);
        snapshot
    }

    fn snapshot_from_state(
        state: &GeometryNativeConcurrentCrossTemplateState<Adapter>,
        plan: &GeometryNativeResidentPlan,
    ) -> Result<
        GeometryNativeConcurrentCrossTemplateSnapshot,
        GeometryNativeResidentWeightError,
    > {
        let usage = state.cache.usage()?;
        Ok(GeometryNativeConcurrentCrossTemplateSnapshot {
            leases: state.cache.resident_lease_count(plan),
            limits: state.cache.limits(),
            resident: state.cache.contains(plan),
            usage,
        })
    }

    /// Attempts one exact resident acquisition without waiting for the mutex.
    ///
    /// Once mutation ownership is acquired, the normal cache transaction runs
    /// to completion with the same adapter, eviction, rollback, and cleanup
    /// semantics as [`Self::ensure`].
    ///
    /// # Errors
    ///
    /// Returns `Busy` before mutation when another thread owns the mutex,
    /// `Poisoned` after interrupted mutation, or the exact cache acquisition
    /// failure after ownership was acquired.
    pub fn try_ensure(
        &self,
        plan: &GeometryNativeResidentPlan,
    ) -> GeometryNativeConcurrentCrossTemplateTryAcquireResult<Adapter::Error>
    {
        let mut state = match self.inner.try_lock() {
            Ok(state) => state,
            Err(TryLockError::Poisoned(_error)) => {
                return Err(TryAcquireFailure::Poisoned);
            },
            Err(TryLockError::WouldBlock) => {
                return Err(TryAcquireFailure::Busy);
            },
        };
        let GeometryNativeConcurrentCrossTemplateState { adapter, cache } =
            &mut *state;
        let result = cache
            .ensure(adapter, plan)
            .map_err(TryAcquireFailure::Operation);
        drop(state);
        result
    }

    /// Attempts resident acquisition without waiting, then executes outside the
    /// lock.
    ///
    /// `Busy` and `Poisoned` are acquisition-phase failures and native
    /// execution never begins. After successful acquisition, the lease
    /// outlives the mutex exactly as in [`Self::execute`].
    ///
    /// # Errors
    ///
    /// Returns a nonblocking acquire-phase failure or the exact typed cached
    /// execution failure after acquisition succeeds.
    pub fn try_execute<Runner>(
        &self,
        plan: &GeometryNativeResidentPlan,
        runner: &mut Runner,
        buffers: NativeRegionBuffers<'_>,
    ) -> TryExecutionResult<Adapter, Runner>
    where
        Runner: ExecutionGeometryNativeRunner,
    {
        let acquisition = self.try_ensure(plan).map_err(|error| {
            Box::new(TryExecutionFailure::Acquire(Box::new(error)))
        })?;
        acquisition
            .execute(runner, buffers)
            .map_err(|error| Box::new(TryExecutionFailure::Execution(error)))
    }

    /// Attempts limit reconfiguration without waiting for mutation ownership.
    ///
    /// Once the mutex is acquired, the complete existing shrink/expand
    /// transaction runs to completion and preserves its typed cleanup evidence.
    ///
    /// # Errors
    ///
    /// Returns `Busy` before mutation, `Poisoned` after interrupted mutation,
    /// or the exact reconfiguration failure after ownership was acquired.
    pub fn try_reconfigure_limits(
        &self,
        requested_limits: GeometryNativeCrossTemplateLruLimits,
    ) -> GeometryNativeConcurrentCrossTemplateTryReconfigurationResult<
        Adapter::Error,
    > {
        let mut state = match self.inner.try_lock() {
            Ok(state) => state,
            Err(TryLockError::Poisoned(_error)) => {
                return Err(TryReconfigurationFailure::Poisoned);
            },
            Err(TryLockError::WouldBlock) => {
                return Err(TryReconfigurationFailure::Busy);
            },
        };
        let GeometryNativeConcurrentCrossTemplateState { adapter, cache } =
            &mut *state;
        let result = cache
            .reconfigure_limits(adapter, requested_limits)
            .map_err(TryReconfigurationFailure::Operation);
        drop(state);
        result
    }

    /// Attempts release-all without waiting for mutation ownership.
    ///
    /// # Errors
    ///
    /// Returns `Busy` before adapter work, `Poisoned` after interrupted
    /// mutation, or the exact aggregate release-all failure after lock acquire.
    pub fn try_release_all_unleased(&self) -> TryReleaseAllResult<Adapter> {
        let mut state = match self.inner.try_lock() {
            Ok(state) => state,
            Err(TryLockError::Poisoned(_error)) => {
                return Err(TryReleaseAllFailure::Poisoned);
            },
            Err(TryLockError::WouldBlock) => {
                return Err(TryReleaseAllFailure::Busy);
            },
        };
        let GeometryNativeConcurrentCrossTemplateState { adapter, cache } =
            &mut *state;
        let result = cache
            .release_all_unleased(adapter)
            .map_err(TryReleaseAllFailure::Operation);
        drop(state);
        result
    }

    /// Attempts one exact resident release without waiting for the mutex.
    ///
    /// Once the mutex is acquired, release uses the complete existing lease and
    /// cleanup ownership contract.
    ///
    /// # Errors
    ///
    /// Returns `Busy` before mutation, `Poisoned` after interrupted mutation,
    /// or exact variant-specific cleanup ownership after a failed release.
    pub fn try_release_if_unleased(
        &self,
        plan: &GeometryNativeResidentPlan,
    ) -> GeometryNativeConcurrentCrossTemplateTryReleaseResult<Adapter::Error>
    {
        let mut state = match self.inner.try_lock() {
            Ok(state) => state,
            Err(TryLockError::Poisoned(_error)) => {
                return Err(TryReleaseFailure::Poisoned);
            },
            Err(TryLockError::WouldBlock) => {
                return Err(TryReleaseFailure::Busy);
            },
        };
        let GeometryNativeConcurrentCrossTemplateState { adapter, cache } =
            &mut *state;
        let result = cache
            .release_if_unleased(adapter, plan)
            .map_err(TryReleaseFailure::Operation);
        drop(state);
        result
    }

    /// Attempts transferred resident cleanup without waiting for the mutex.
    ///
    /// # Errors
    ///
    /// Returns the untouched cleanup token on `Busy` or `Poisoned`, or
    /// refreshed cleanup ownership when the acquired retry release fails
    /// again.
    pub fn try_retry_cleanup(
        &self,
        cleanup: Box<CacheReleaseFailure<Adapter::Error>>,
    ) -> GeometryNativeConcurrentCrossTemplateCleanupRetryResult<Adapter::Error>
    {
        let mut state = match self.inner.try_lock() {
            Ok(state) => state,
            Err(TryLockError::Poisoned(_error)) => {
                return Err(Box::new(CleanupRetryFailure::Poisoned(cleanup)));
            },
            Err(TryLockError::WouldBlock) => {
                return Err(Box::new(CleanupRetryFailure::Busy(cleanup)));
            },
        };
        let result = (*cleanup)
            .retry(&mut state.adapter)
            .map_err(|error| Box::new(CleanupRetryFailure::Release(error)));
        drop(state);
        result
    }

    /// Attempts primary load rollback cleanup without waiting for the mutex.
    ///
    /// # Errors
    ///
    /// Returns the untouched primary failure on `Busy` or `Poisoned`.
    pub fn try_retry_load_cleanup(
        &self,
        failure: Box<ResidentLoadFailure<Adapter::Error>>,
    ) -> GeometryNativeConcurrentCrossTemplateLoadCleanupRetryResult<
        Adapter::Error,
    > {
        let mut state = match self.inner.try_lock() {
            Ok(state) => state,
            Err(TryLockError::Poisoned(_error)) => {
                return Err(Box::new(LoadCleanupFailure::Poisoned(failure)));
            },
            Err(TryLockError::WouldBlock) => {
                return Err(Box::new(LoadCleanupFailure::Busy(failure)));
            },
        };
        let retried = Box::new((*failure).retry_cleanup(&mut state.adapter));
        let outcome = if retried.cleanup_pending() {
            GeometryNativeConcurrentCrossTemplateLoadCleanupRetry::Pending(
                retried,
            )
        } else {
            GeometryNativeConcurrentCrossTemplateLoadCleanupRetry::Clean(
                retried,
            )
        };
        drop(state);
        Ok(outcome)
    }

    /// Attempts aggregate release-all cleanup without waiting for the mutex.
    ///
    /// # Errors
    ///
    /// Returns the untouched aggregate token on `Busy` or `Poisoned`, or a
    /// refreshed aggregate token when acquired retry still fails.
    pub fn try_retry_release_all_cleanup(
        &self,
        failure: Box<CacheReleaseAllFailure<Adapter::Error>>,
    ) -> GeometryNativeConcurrentCrossTemplateReleaseAllRetryResult<
        Adapter::Error,
    > {
        let mut state = match self.inner.try_lock() {
            Ok(state) => state,
            Err(TryLockError::Poisoned(_error)) => {
                return Err(Box::new(ReleaseAllRetryFailure::Poisoned(
                    failure,
                )));
            },
            Err(TryLockError::WouldBlock) => {
                return Err(Box::new(ReleaseAllRetryFailure::Busy(failure)));
            },
        };
        let result = (*failure)
            .retry(&mut state.adapter)
            .map_err(|error| Box::new(ReleaseAllRetryFailure::Release(error)));
        drop(state);
        result
    }

    /// Attempts one coherent snapshot without waiting for mutation ownership.
    ///
    /// # Errors
    ///
    /// Returns `Busy` when another thread owns the mutex, `Poisoned` after
    /// interrupted mutation, or exact resident-weight overflow evidence.
    pub fn try_snapshot(
        &self,
        plan: &GeometryNativeResidentPlan,
    ) -> GeometryNativeConcurrentCrossTemplateTrySnapshotResult {
        let state = match self.inner.try_lock() {
            Ok(state) => state,
            Err(TryLockError::Poisoned(_error)) => {
                return Err(TrySnapshotFailure::Poisoned);
            },
            Err(TryLockError::WouldBlock) => {
                return Err(TrySnapshotFailure::Busy);
            },
        };
        let snapshot = Self::snapshot_from_state(&state, plan)
            .map_err(TrySnapshotFailure::ResidentWeight);
        drop(state);
        snapshot
    }

    /// Returns exact aggregate mapping usage under synchronized cache access.
    ///
    /// # Errors
    ///
    /// Returns poison or exact resident-weight overflow evidence.
    pub fn usage(&self) -> GeometryNativeConcurrentCrossTemplateUsageResult {
        self.lock()
            .map_err(|_error| {
                GeometryNativeConcurrentCrossTemplateFailure::Poisoned
            })?
            .cache
            .usage()
            .map_err(GeometryNativeConcurrentCrossTemplateFailure::Operation)
    }
}
