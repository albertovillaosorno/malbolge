// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Regression coverage for explicit post-observation cache-limit activation.
// - Must-Not:
//   - Execute product cycles or redefine recommendation/activation semantics.
// - Allows:
//   - Inputs: deterministic telemetry publications and in-memory stores/caches.
//   - Outputs: deterministic orchestration evidence.
//   - Side effects: test-local in-memory durable/cache mutation only.
// - Split-When:
//   - Orchestration requires an independent integration lifecycle.
// - Merge-When:
//   - Parent orchestration no longer requires private regression access.
// - Summary:
//   - Proves only published telemetry can trigger cache-limit activation.
// - Description:
//   - Planning evidence is retained across no-authority and failure outcomes.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Failed/deferred telemetry performs zero durable/cache work.
//

//! Regression coverage for post-observation cache-limit activation.

use std::num::NonZeroU64;

use super::*;
use crate::blob_store::{
    NativeContinuationBlobConditionalPublication,
    NativeContinuationBlobConditionalPublicationResult,
};
use crate::cached_cycle::{
    NativeContinuationCachedRetryCycleTelemetryPublication,
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencySample,
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryWindow,
};
use crate::executable_cache_limits_durable_activation::{
    NativeExecutableCacheLimitsRecommendedActivation,
    NativeExecutableSequenceCacheLimitsDurableActivation,
};
use crate::executable_cache_limits_recommendation::{
    NativeExecutableCacheLimitsPressureThreshold,
    NativeExecutableCacheLimitsRecommendationSet,
    NativeExecutableCacheLimitsReuseThreshold,
    NativeExecutableCacheLimitsTwoSignalRequest,
};
use crate::execution_native::{
    NativeExecutableAllocationRequest, NativeExecutableCodeCopyReport,
    NativeExecutableMappingReport, NativeExecutableReleaseRequest,
    NativeInstructionSyncReport, NativeInstructionSyncRequest,
};
use crate::{
    executable_cache_limits_cas as cache_cas,
    executable_cache_limits_precedence as cache_select,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum AdapterError {
    UnexpectedOperation,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ClockError {
    Failed,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DurabilityError {
    Failed,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum StoreError {
    Failed,
}

#[derive(Debug, Default)]
struct MemoryStore {
    bytes: Option<Vec<u8>>,
    compare_and_swap_calls: usize,
    fail_store: bool,
}

#[derive(Debug, Default)]
struct NoOpAdapter {
    calls: usize,
}

type LimitsCas =
    cache_cas::NativeExecutableSequenceCacheLimitsCas<DurabilityError>;

type CachePrecedence = cache_select::NativeExecutableCacheLimitsPrecedence;

impl BlobStore for MemoryStore {
    type Error = StoreError;

    fn load(
        &mut self,
        _maximum_bytes: NonZeroUsize,
    ) -> Result<Option<Vec<u8>>, Self::Error> {
        if self.fail_store {
            Err(StoreError::Failed)
        } else {
            Ok(self.bytes.clone())
        }
    }

    fn replace(&mut self, bytes: &[u8]) -> Result<(), Self::Error> {
        if self.fail_store {
            Err(StoreError::Failed)
        } else {
            self.bytes = Some(bytes.to_vec());
            Ok(())
        }
    }
}

impl ConditionalBlobStore for MemoryStore {
    fn compare_and_swap(
        &mut self,
        expected: Option<&[u8]>,
        replacement: &[u8],
        _maximum_bytes: NonZeroUsize,
    ) -> NativeContinuationBlobConditionalPublicationResult<Self::Error> {
        self.compare_and_swap_calls =
            self.compare_and_swap_calls.saturating_add(1);
        if self.fail_store {
            return Err(StoreError::Failed);
        }
        if self.bytes.as_deref() != expected {
            return Ok(
                NativeContinuationBlobConditionalPublication::Conflict {
                    current: self.bytes.clone(),
                },
            );
        }
        self.bytes = Some(replacement.to_vec());
        Ok(NativeContinuationBlobConditionalPublication::Published)
    }
}

impl DurableBlobStore for MemoryStore {
    type DurabilityError = DurabilityError;

    fn confirm_durability(&mut self) -> Result<(), Self::DurabilityError> {
        Ok(())
    }
}

impl NativeExecutableMemoryAdapter for NoOpAdapter {
    type Error = AdapterError;

    fn allocate_writable(
        &mut self,
        _request: NativeExecutableAllocationRequest,
    ) -> Result<NativeExecutableMappingReport, Self::Error> {
        self.calls = self.calls.saturating_add(1);
        Err(AdapterError::UnexpectedOperation)
    }

    fn copy_code(
        &mut self,
        _mapping: NativeExecutableMappingReport,
        _code: &[u8],
    ) -> Result<NativeExecutableCodeCopyReport, Self::Error> {
        self.calls = self.calls.saturating_add(1);
        Err(AdapterError::UnexpectedOperation)
    }

    fn protect_read_execute(
        &mut self,
        _mapping: NativeExecutableMappingReport,
    ) -> Result<NativeExecutableMappingReport, Self::Error> {
        self.calls = self.calls.saturating_add(1);
        Err(AdapterError::UnexpectedOperation)
    }

    fn release(
        &mut self,
        _request: NativeExecutableReleaseRequest,
    ) -> Result<(), Self::Error> {
        self.calls = self.calls.saturating_add(1);
        Err(AdapterError::UnexpectedOperation)
    }

    fn synchronize_instructions(
        &mut self,
        _request: NativeInstructionSyncRequest,
    ) -> Result<NativeInstructionSyncReport, Self::Error> {
        self.calls = self.calls.saturating_add(1);
        Err(AdapterError::UnexpectedOperation)
    }
}

fn limits(
    entries: usize,
) -> Result<NativeExecutableSequenceCacheLimits, String> {
    NonZeroUsize::new(entries)
        .map(NativeExecutableSequenceCacheLimits::new)
        .ok_or_else(|| String::from("cache limit must be positive"))
}

fn nonzero(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test value must be positive"))
}

fn policy_request()
-> Result<NativeExecutableCacheLimitsTwoSignalRequest, String> {
    let one = NonZeroU64::new(1)
        .ok_or_else(|| String::from("test ratio must be positive"))?;
    Ok(NativeExecutableCacheLimitsTwoSignalRequest::new(
        NativeExecutableCacheLimitsReuseThreshold::new(nonzero(4)?, one, one),
        NativeExecutableCacheLimitsRecommendationSet::new(
            limits(3)?,
            limits(8)?,
        ),
        NativeExecutableCacheLimitsPressureThreshold::new(nonzero(4)?, 2, 1),
        NativeExecutableCacheLimitsRecommendationSet::new(
            limits(3)?,
            limits(2)?,
        ),
    ))
}

fn request()
-> Result<NativeExecutableCacheLimitsObservedActivationRequest, String> {
    let policy = policy_request()?;
    Ok(NativeExecutableCacheLimitsObservedActivationRequest::new(
        &policy,
        CachePrecedence::Pressure,
        None,
        nonzero(40)?,
    ))
}

fn published(
    counts: [usize; 6],
) -> Result<
    NativeContinuationCachedRetryCycleTelemetryPublication<ClockError>,
    String,
> {
    let telemetry =
        NativeContinuationCachedRetryTelemetry::from_test_counts(counts);
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(nonzero(2)?);
    let append = window
        .append(telemetry)
        .map_err(|error| error.to_string())?;
    let sample = NativeContinuationCachedRetryLatencySample::new(10);
    let mut histogram =
        NativeContinuationCachedRetryLatencyHistogram::new(vec![20])
            .map_err(|error| error.to_string())?;
    let latency = histogram
        .record(sample)
        .map_err(|error| error.to_string())?;
    Ok(
        NativeContinuationCachedRetryCycleTelemetryPublication::Published {
            latency,
            sample,
            telemetry,
            window: Box::new(append),
        },
    )
}

#[test]
fn unpublished_telemetry_skips_store_and_cache() -> Result<(), String> {
    let publication =
        NativeContinuationCachedRetryCycleTelemetryPublication::ClockFailure {
            error: ClockError::Failed,
        };
    let current = limits(4)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let mut context = NativeExecutableCacheLimitsObservedCacheContext::new(
        &mut store,
        &mut cache,
        &mut adapter,
    );
    let outcome = activate_observed_executable_sequence_cache_limits_durably(
        &publication,
        &mut context,
        &request()?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableCacheLimitsObservedActivation::TelemetryUnpublished {
            publication: observed,
        } if core::ptr::eq(observed, &publication)
    ) && store.compare_and_swap_calls == 0
        && cache.limits() == current
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("unpublished telemetry triggered cache policy"))
    }
}

#[test]
fn deferred_published_telemetry_skips_store_and_cache() -> Result<(), String> {
    let publication = published([2, 4, 1, 0, 2, 1])?;
    let current = limits(4)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let mut context = NativeExecutableCacheLimitsObservedCacheContext::new(
        &mut store,
        &mut cache,
        &mut adapter,
    );
    let outcome = activate_observed_executable_sequence_cache_limits_durably(
        &publication,
        &mut context,
        &request()?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableCacheLimitsObservedActivation::Planned { plan }
            if plan.recommendation().is_none()
    ) && store.compare_and_swap_calls == 0
        && cache.limits() == current
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("deferred observed policy reached activation"))
    }
}

#[test]
fn published_pressure_precedence_activates_cache() -> Result<(), String> {
    let publication = published([4, 8, 3, 0, 4, 2])?;
    let current = limits(4)?;
    let candidate = limits(2)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let mut context = NativeExecutableCacheLimitsObservedCacheContext::new(
        &mut store,
        &mut cache,
        &mut adapter,
    );
    let outcome = activate_observed_executable_sequence_cache_limits_durably(
        &publication,
        &mut context,
        &request()?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableCacheLimitsObservedActivation::Activated {
            activation:
                NativeExecutableCacheLimitsRecommendedActivation::Ready {
                    activation:
                        NativeExecutableSequenceCacheLimitsDurableActivation::
                            Reconfigured {
                                publication:
                                    LimitsCas::Durable {
                                        current: published,
                                        previous: None,
                                        ..
                                    },
                                ..
                            },
                    ..
                },
            plan,
        } if published == candidate && plan.recommendation().is_some()
    ) && store.compare_and_swap_calls == 1
        && cache.limits() == candidate
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "published pressure policy did not activate cache",
        ))
    }
}

#[test]
fn published_pressure_precedence_activates_lease_cache() -> Result<(), String> {
    let publication = published([4, 8, 3, 0, 4, 2])?;
    let current = limits(4)?;
    let candidate = limits(2)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceLeaseCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let mut context = NativeExecutableCacheLimitsObservedLeaseContext::new(
        &mut store,
        &mut cache,
        &mut adapter,
    );
    let outcome =
        activate_observed_executable_sequence_lease_cache_limits_durably(
            &publication,
            &mut context,
            &request()?,
        )
        .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableCacheLimitsObservedActivation::Activated {
            activation:
                NativeExecutableCacheLimitsRecommendedActivation::Ready {
                    activation:
                        NativeExecutableSequenceCacheLimitsDurableActivation::
                            Reconfigured {
                                publication:
                                    LimitsCas::Durable {
                                        current: published,
                                        previous: None,
                                        ..
                                    },
                                ..
                            },
                    ..
                },
            ..
        } if published == candidate
    ) && store.compare_and_swap_calls == 1
        && cache.limits() == candidate
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "published pressure policy did not activate lease",
        ))
    }
}

#[test]
fn prepublication_store_failure_retains_window_plan() -> Result<(), String> {
    let publication = published([4, 8, 3, 0, 4, 2])?;
    let current = limits(4)?;
    let mut store = MemoryStore {
        fail_store: true,
        ..MemoryStore::default()
    };
    let mut cache = NativeExecutableSequenceCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let mut context = NativeExecutableCacheLimitsObservedCacheContext::new(
        &mut store,
        &mut cache,
        &mut adapter,
    );
    let failure = activate_observed_executable_sequence_cache_limits_durably(
        &publication,
        &mut context,
        &request()?,
    )
    .err()
    .ok_or_else(|| String::from("observed store failure disappeared"))?;
    if failure.plan().recommendation().is_some()
        && failure.activation().recommendation().limits() == Some(limits(2)?)
        && store.compare_and_swap_calls == 1
        && cache.limits() == current
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "observed activation failure lost plan evidence",
        ))
    }
}
