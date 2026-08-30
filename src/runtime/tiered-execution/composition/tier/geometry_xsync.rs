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
    GeometryNativeCrossTemplateLruRelease, GeometryNativeCrossTemplateLruUsage,
};
use crate::geometry_native_cross_template_resident::{
    GeometryNativeResidentPlan, GeometryNativeResidentReleaseFailure,
    GeometryNativeResidentWeightError,
};

type CacheAcquireFailure<MemoryError> =
    GeometryNativeCrossTemplateLruAcquireFailure<MemoryError>;
type CacheReconfigurationFailure<MemoryError> =
    GeometryNativeCrossTemplateLruReconfigurationFailure<MemoryError>;
type CacheReleaseFailure<MemoryError> =
    GeometryNativeResidentReleaseFailure<MemoryError>;
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

/// Result of publishing synchronized replacement resource limits.
pub type GeometryNativeConcurrentCrossTemplateReconfigurationResult<
    MemoryError,
> = Result<
    GeometryNativeCrossTemplateLruReconfiguration,
    GeometryNativeConcurrentCrossTemplateFailure<
        Box<CacheReconfigurationFailure<MemoryError>>,
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
