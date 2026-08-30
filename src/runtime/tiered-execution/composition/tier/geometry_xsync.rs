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
use std::sync::{Mutex, MutexGuard};

use crate::execution_native::NativeExecutableMemoryAdapter;
use crate::geometry_native_cross_template_cache::{
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
type ConcurrentStateGuard<'cache, Adapter> =
    MutexGuard<'cache, GeometryNativeConcurrentCrossTemplateState<Adapter>>;

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
