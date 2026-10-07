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
//   - Root-tree regression coverage for durable cache-limit activation.
// - Must-Not:
//   - Define production semantics or replace the parent module's authority.
// - Allows:
//   - Inputs: the parent module's test-visible implementation surface.
//   - Outputs: deterministic regression evidence.
//   - Side effects: test-only in-memory or filesystem fixture effects.
// - Split-When:
//   - The regression surface requires an independent integration lifecycle.
// - Merge-When:
//   - The parent boundary no longer requires private regression access.
// - Summary:
//   - Proves durable cache-limit activation behavior from the root test tree.
// - Description:
//   - Loaded as a test-only child module to retain private-item access.
// - Usage:
//   - Selected by the parent module only when Rust test configuration is set.
// - Defaults:
//   - Production builds never compile this regression module.
//

//! Root-tree regression coverage for durable cache-limit activation.

use std::num::NonZeroU64;

use super::*;
use crate::blob_persistence::NativeContinuationBlobPersistenceError;
use crate::blob_store::{
    NativeContinuationBlobConditionalPublication,
    NativeContinuationBlobConditionalPublicationResult,
};
use crate::cached_cycle::{
    NativeContinuationCachedRetryAttempt, summarize_cached_retry_attempts,
};
use crate::executable_cache_limits_precedence::{
    NativeExecutableCacheLimitsPrecedence,
    select_native_executable_cache_limits_precedence,
};
use crate::executable_cache_limits_recommendation::{
    NativeExecutableCacheLimitsPressureThreshold,
    NativeExecutableCacheLimitsRecommendation,
    NativeExecutableCacheLimitsRecommendationSet,
    NativeExecutableCacheLimitsReuseThreshold,
    NativeExecutableCacheLimitsTwoSignalRequest,
    recommend_native_executable_cache_limits_from_reuse,
    recommend_native_executable_cache_limits_from_reuse_and_pressure,
};
use crate::execution_native::{
    NativeExecutableAllocationRequest, NativeExecutableCodeCopyReport,
    NativeExecutableMappingReport, NativeExecutableReleaseRequest,
    NativeExecutableSequenceLeaseCacheDisposition, NativeInstructionSyncReport,
    NativeInstructionSyncRequest,
    encode_native_executable_sequence_cache_limits,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum AdapterError {
    UnexpectedOperation,
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
    fail_durability: bool,
    fail_store: bool,
}

#[derive(Debug, Default)]
struct NoOpAdapter {
    calls: usize,
}

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
        if self.fail_durability {
            Err(DurabilityError::Failed)
        } else {
            Ok(())
        }
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

fn agreed_recommendation(
    current: NativeExecutableSequenceCacheLimits,
    candidate: NativeExecutableSequenceCacheLimits,
) -> Result<NativeExecutableCacheLimitsRecommendation, String> {
    let telemetry = summarize_cached_retry_attempts(&[
        NativeContinuationCachedRetryAttempt::from_test_evidence(
            1,
            2,
            NativeExecutableSequenceLeaseCacheDisposition::Hit,
        ),
        NativeContinuationCachedRetryAttempt::from_test_evidence(
            2,
            3,
            NativeExecutableSequenceLeaseCacheDisposition::Hit,
        ),
    ])
    .map_err(|error| error.to_string())?;
    let one = NonZeroU64::new(1)
        .ok_or_else(|| String::from("test agreement ratio missing"))?;
    let candidates = NativeExecutableCacheLimitsRecommendationSet::new(
        candidate,
        limits(1)?,
    );
    let request = NativeExecutableCacheLimitsTwoSignalRequest::new(
        NativeExecutableCacheLimitsReuseThreshold::new(positive(2)?, one, one),
        candidates,
        NativeExecutableCacheLimitsPressureThreshold::new(positive(2)?, 0, 0),
        candidates,
    );
    recommend_native_executable_cache_limits_from_reuse_and_pressure(
        telemetry, current, &request,
    )
    .recommendation()
    .ok_or_else(|| String::from("test cache signals did not agree"))
}

fn precedence_recommendation(
    current: NativeExecutableSequenceCacheLimits,
    reuse_candidate: NativeExecutableSequenceCacheLimits,
    pressure_candidate: NativeExecutableSequenceCacheLimits,
) -> Result<NativeExecutableCacheLimitsRecommendation, String> {
    let one = NonZeroU64::new(1)
        .ok_or_else(|| String::from("test precedence ratio missing"))?;
    let request = NativeExecutableCacheLimitsTwoSignalRequest::new(
        NativeExecutableCacheLimitsReuseThreshold::new(positive(4)?, one, one),
        NativeExecutableCacheLimitsRecommendationSet::new(
            limits(3)?,
            reuse_candidate,
        ),
        NativeExecutableCacheLimitsPressureThreshold::new(positive(4)?, 2, 1),
        NativeExecutableCacheLimitsRecommendationSet::new(
            limits(3)?,
            pressure_candidate,
        ),
    );
    let arbitration =
        recommend_native_executable_cache_limits_from_reuse_and_pressure(
            crate::cached_cycle::NativeContinuationCachedRetryTelemetry::
                from_test_counts([4, 8, 3, 0, 4, 2]),
            current,
            &request,
        );
    select_native_executable_cache_limits_precedence(
        &arbitration,
        NativeExecutableCacheLimitsPrecedence::Pressure,
    )
    .recommendation()
    .ok_or_else(|| String::from("test pressure precedence withheld policy"))
}

fn activation_request(
    expected: Option<NativeExecutableSequenceCacheLimits>,
    candidate: NativeExecutableSequenceCacheLimits,
) -> Result<NativeExecutableSequenceCacheLimitsDurableActivationRequest, String>
{
    Ok(
        NativeExecutableSequenceCacheLimitsDurableActivationRequest::new(
            expected,
            candidate,
            positive(40)?,
        ),
    )
}

fn limits(
    entries: usize,
) -> Result<NativeExecutableSequenceCacheLimits, String> {
    NonZeroUsize::new(entries)
        .map(NativeExecutableSequenceCacheLimits::new)
        .ok_or_else(|| String::from("test cache entry limit missing"))
}

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test positive value missing"))
}

fn recommendation(
    current: NativeExecutableSequenceCacheLimits,
    meets: NativeExecutableSequenceCacheLimits,
    misses: NativeExecutableSequenceCacheLimits,
    required_attempts: usize,
) -> Result<NativeExecutableCacheLimitsRecommendation, String> {
    let telemetry = summarize_cached_retry_attempts(&[
        NativeContinuationCachedRetryAttempt::from_test_evidence(
            1,
            2,
            NativeExecutableSequenceLeaseCacheDisposition::Hit,
        ),
        NativeContinuationCachedRetryAttempt::from_test_evidence(
            2,
            3,
            NativeExecutableSequenceLeaseCacheDisposition::Hit,
        ),
    ])
    .map_err(|error| error.to_string())?;
    let numerator = NonZeroU64::new(1)
        .ok_or_else(|| String::from("test reuse numerator missing"))?;
    let denominator = NonZeroU64::new(1)
        .ok_or_else(|| String::from("test reuse denominator missing"))?;
    Ok(recommend_native_executable_cache_limits_from_reuse(
        telemetry,
        current,
        NativeExecutableCacheLimitsReuseThreshold::new(
            positive(required_attempts)?,
            numerator,
            denominator,
        ),
        NativeExecutableCacheLimitsRecommendationSet::new(meets, misses),
    ))
}

fn recommended_request(
    expected: Option<NativeExecutableSequenceCacheLimits>,
    recommendation: NativeExecutableCacheLimitsRecommendation,
) -> Result<NativeExecutableCacheLimitsRecommendedActivationRequest, String> {
    Ok(
        NativeExecutableCacheLimitsRecommendedActivationRequest::new(
            expected,
            recommendation,
            positive(40)?,
        ),
    )
}

#[test]
fn precedence_selected_recommendation_activates() -> Result<(), String> {
    let current = limits(4)?;
    let candidate = limits(2)?;
    let recommendation =
        precedence_recommendation(current, limits(8)?, candidate)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let outcome =
        activate_recommended_executable_sequence_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            &recommended_request(None, recommendation)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableCacheLimitsRecommendedActivation::Ready {
            activation:
                NativeExecutableSequenceCacheLimitsDurableActivation::
                    Reconfigured {
                        publication:
                            NativeExecutableSequenceCacheLimitsCas::Durable {
                                current: published,
                                previous: None,
                                ..
                            },
                        ..
                    },
            recommendation: observed,
        } if published == candidate && observed == recommendation
    ) && cache.limits() == candidate
        && store.compare_and_swap_calls == 1
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("precedence recommendation did not activate"))
    }
}

#[test]
fn recommended_agreement_activates_combined_evidence() -> Result<(), String> {
    let current = limits(2)?;
    let candidate = limits(3)?;
    let recommendation = agreed_recommendation(current, candidate)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let outcome =
        activate_recommended_executable_sequence_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            &recommended_request(None, recommendation)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableCacheLimitsRecommendedActivation::Ready {
            activation:
                NativeExecutableSequenceCacheLimitsDurableActivation::
                    Reconfigured {
                        publication:
                            NativeExecutableSequenceCacheLimitsCas::Durable {
                                current: published,
                                previous: None,
                                ..
                            },
                        ..
                    },
            recommendation: observed,
        } if published == candidate && observed == recommendation
    ) && cache.limits() == candidate
        && store.compare_and_swap_calls == 1
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("agreed recommendation did not activate"))
    }
}

#[test]
fn recommended_deferred_skips_store_and_cache() -> Result<(), String> {
    let current = limits(2)?;
    let recommendation = recommendation(current, limits(3)?, limits(1)?, 3)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let outcome =
        activate_recommended_executable_sequence_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            &recommended_request(None, recommendation)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableCacheLimitsRecommendedActivation::Deferred {
            recommendation: observed,
        } if observed == recommendation
    ) && cache.limits() == current
        && store.compare_and_swap_calls == 0
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("deferred recommendation performed activation"))
    }
}

#[test]
fn recommended_retain_skips_store_and_cache() -> Result<(), String> {
    let current = limits(2)?;
    let recommendation = recommendation(current, current, limits(1)?, 2)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let outcome =
        activate_recommended_executable_sequence_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            &recommended_request(None, recommendation)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableCacheLimitsRecommendedActivation::Retained {
            current: observed,
            recommendation: observed_recommendation,
        } if observed == current && observed_recommendation == recommendation
    ) && cache.limits() == current
        && store.compare_and_swap_calls == 0
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("retained recommendation performed activation"))
    }
}

#[test]
fn recommended_local_drift_rejects_before_store() -> Result<(), String> {
    let expected_live = limits(2)?;
    let actual_live = limits(4)?;
    let recommendation =
        recommendation(expected_live, limits(3)?, limits(1)?, 2)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceCache::with_limits(actual_live);
    let mut adapter = NoOpAdapter::default();
    let outcome =
        activate_recommended_executable_sequence_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            &recommended_request(None, recommendation)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableCacheLimitsRecommendedActivation::LocalStateMismatch {
            current,
            expected,
            recommendation: observed,
        } if current == actual_live
            && expected == expected_live
            && observed == recommendation
    ) && cache.limits() == actual_live
        && store.compare_and_swap_calls == 0
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("stale recommendation reached storage"))
    }
}

#[test]
fn recommended_initial_commit_reconfigures_cache() -> Result<(), String> {
    let current = limits(2)?;
    let candidate = limits(3)?;
    let recommendation = recommendation(current, candidate, limits(1)?, 2)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let outcome =
        activate_recommended_executable_sequence_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            &recommended_request(None, recommendation)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableCacheLimitsRecommendedActivation::Ready {
            activation:
                NativeExecutableSequenceCacheLimitsDurableActivation::
                    Reconfigured {
                        publication:
                            NativeExecutableSequenceCacheLimitsCas::Durable {
                                current: published,
                                previous: None,
                                ..
                            },
                        ..
                    },
            recommendation: observed,
        } if published == candidate && observed == recommendation
    ) && cache.limits() == candidate
        && store.compare_and_swap_calls == 1
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("recommended initial commit did not activate"))
    }
}

#[test]
fn recommended_durable_conflict_preserves_live_cache() -> Result<(), String> {
    let current = limits(2)?;
    let durable = limits(4)?;
    let candidate = limits(3)?;
    let recommendation = recommendation(current, candidate, limits(1)?, 2)?;
    let mut store = MemoryStore {
        bytes: Some(
            encode_native_executable_sequence_cache_limits(durable)
                .map_err(|error| format!("{error:?}"))?,
        ),
        ..MemoryStore::default()
    };
    let mut cache = NativeExecutableSequenceCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let outcome =
        activate_recommended_executable_sequence_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            &recommended_request(Some(current), recommendation)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableCacheLimitsRecommendedActivation::Ready {
            activation:
                NativeExecutableSequenceCacheLimitsDurableActivation::Conflict {
                    publication:
                        NativeExecutableSequenceCacheLimitsCas::Conflict {
                            current: Some(observed),
                            expected: Some(expected),
                            ..
                        },
                },
            recommendation: observed_recommendation,
        } if observed == durable
            && expected == current
            && observed_recommendation == recommendation
    ) && cache.limits() == current
        && store.compare_and_swap_calls == 1
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("recommended CAS conflict changed live cache"))
    }
}

#[test]
fn recommended_prepublication_failure_retains_evidence() -> Result<(), String> {
    let current = limits(2)?;
    let recommendation = recommendation(current, limits(3)?, limits(1)?, 2)?;
    let mut store = MemoryStore {
        fail_store: true,
        ..MemoryStore::default()
    };
    let mut cache = NativeExecutableSequenceCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let failure =
        activate_recommended_executable_sequence_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            &recommended_request(None, recommendation)?,
        )
        .err()
        .ok_or_else(|| {
            String::from("recommendation store failure disappeared")
        })?;
    if failure.recommendation() == recommendation
        && matches!(
            failure.error(),
            NativeExecutableSequenceCacheLimitsCasError::Blob(_)
        )
        && cache.limits() == current
        && store.compare_and_swap_calls == 1
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("recommendation failure evidence drifted"))
    }
}

#[test]
fn recommended_initial_commit_reconfigures_lease_cache() -> Result<(), String> {
    let current = limits(2)?;
    let candidate = limits(3)?;
    let recommendation = recommendation(current, candidate, limits(1)?, 2)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceLeaseCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let outcome =
        activate_recommended_executable_sequence_lease_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            &recommended_request(None, recommendation)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableCacheLimitsRecommendedActivation::Ready {
            activation:
                NativeExecutableSequenceCacheLimitsDurableActivation::
                    Reconfigured {
                        publication:
                            NativeExecutableSequenceCacheLimitsCas::Durable {
                                current: published,
                                previous: None,
                                ..
                            },
                        ..
                    },
            recommendation: observed,
        } if published == candidate && observed == recommendation
    ) && cache.limits() == candidate
        && store.compare_and_swap_calls == 1
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("recommended lease commit did not activate"))
    }
}

#[test]
fn committed_failure_retains_live_failure() -> Result<(), String> {
    let previous = limits(2)?;
    let candidate = limits(3)?;
    let publication = NativeExecutableSequenceCacheLimitsCas::Published {
        bytes: 40,
        current: candidate,
        durability_error: DurabilityError::Failed,
        previous: Some(previous),
    };
    let outcome = activate_committed_limits(publication, |limits| {
        if limits == candidate {
            Err::<(), &'static str>("blocked")
        } else {
            Err::<(), &'static str>("wrong limits")
        }
    });
    match outcome {
        NativeExecutableSequenceCacheLimitsDurableActivation::
            ReconfigurationFailed {
                publication:
                    NativeExecutableSequenceCacheLimitsCas::Published {
                        current,
                        durability_error,
                        previous: retained_previous,
                        ..
                    },
                failure,
            } if current == candidate
                && durability_error == DurabilityError::Failed
                && retained_previous == Some(previous)
                && failure == "blocked" =>
        {
            Ok(())
        },
        _ => Err(String::from(
            "committed live failure lost durable publication evidence",
        )),
    }
}

#[test]
fn conflict_leaves_ordinary_cache_untouched() -> Result<(), String> {
    let expected = limits(2)?;
    let current = limits(3)?;
    let candidate = limits(4)?;
    let initial = limits(5)?;
    let mut store = MemoryStore {
        bytes: Some(
            encode_native_executable_sequence_cache_limits(current)
                .map_err(|error| format!("{error:?}"))?,
        ),
        ..MemoryStore::default()
    };
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let outcome = publish_and_apply_executable_sequence_cache_limits_durably(
        &mut store,
        &mut cache,
        &mut adapter,
        activation_request(Some(expected), candidate)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableSequenceCacheLimitsDurableActivation::Conflict {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Conflict {
                    current: Some(observed),
                    ..
                },
        } if observed == current
    ) && cache.limits() == initial
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("CAS conflict changed ordinary live cache"))
    }
}

#[test]
fn durable_commit_reconfigures_lease_cache() -> Result<(), String> {
    let initial = limits(5)?;
    let candidate = limits(2)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceLeaseCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let outcome =
        publish_and_apply_executable_sequence_lease_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            activation_request(None, candidate)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    match outcome {
        NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Durable {
                    current,
                    ..
                },
            reconfiguration,
        } if current == candidate
            && reconfiguration.limit_transition()
                == (initial, candidate)
            && reconfiguration.evicted_keys().is_empty()
            && reconfiguration.retired_keys().is_empty()
            && cache.limits() == candidate
            && adapter.calls == 0 =>
        {
            Ok(())
        },
        _ => Err(String::from(
            "durable commit did not reconfigure lease cache",
        )),
    }
}

#[test]
fn durable_commit_reconfigures_ordinary_cache() -> Result<(), String> {
    let initial = limits(5)?;
    let candidate = limits(2)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let outcome = publish_and_apply_executable_sequence_cache_limits_durably(
        &mut store,
        &mut cache,
        &mut adapter,
        activation_request(None, candidate)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    match outcome {
        NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Durable {
                    current,
                    ..
                },
            reconfiguration,
        } if current == candidate
            && reconfiguration.limit_transition()
                == (initial, candidate)
            && reconfiguration.evicted_keys().is_empty()
            && cache.limits() == candidate
            && adapter.calls == 0 =>
        {
            Ok(())
        },
        _ => Err(String::from(
            "durable commit did not reconfigure ordinary cache",
        )),
    }
}

#[test]
fn file_store_publication_and_live_activation_stay_aligned()
-> Result<(), String> {
    use std::fs::{create_dir, remove_dir_all};
    use std::process;

    use crate::executable_cache_limits_persistence::{
        NativeExecutableSequenceCacheLimitsPersistenceLoad,
        restore_native_executable_sequence_cache_limits,
    };
    use crate::file_blob_store::NativeContinuationFileBlobStore;

    let directory = std::env::temp_dir()
        .join(format!("malbolge-cache-limit-live-{}", process::id(),));
    match remove_dir_all(&directory) {
        Ok(()) => {},
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {},
        Err(error) => {
            return Err(format!("test directory cleanup failed: {error}"));
        },
    }
    create_dir(&directory)
        .map_err(|error| format!("test directory create failed: {error}"))?;
    let destination = directory.join("limits.bin");
    let mut store = NativeContinuationFileBlobStore::new(destination);
    let initial = limits(5)?;
    let first = limits(3)?;
    let second = limits(2)?;
    let stale = limits(4)?;
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();

    let initialized =
        publish_and_apply_executable_sequence_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            activation_request(None, first)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    let updated = publish_and_apply_executable_sequence_cache_limits_durably(
        &mut store,
        &mut cache,
        &mut adapter,
        activation_request(Some(first), second)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    let conflicted =
        publish_and_apply_executable_sequence_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            activation_request(Some(first), stale)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    let restored = restore_native_executable_sequence_cache_limits(
        &mut store,
        positive(40)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    let expected_restored =
        NativeExecutableSequenceCacheLimitsPersistenceLoad::Restored {
            bytes: 40,
            limits: second,
        };
    let valid = matches!(
        initialized,
        NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Durable {
                    current,
                    ..
                },
            ..
        } if current == first
    ) && matches!(
        updated,
        NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Durable {
                    current,
                    ..
                },
            ..
        } if current == second
    ) && matches!(
        conflicted,
        NativeExecutableSequenceCacheLimitsDurableActivation::Conflict {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Conflict {
                    current: Some(observed),
                    ..
                },
        } if observed == second
    ) && cache.limits() == second
        && restored == expected_restored
        && adapter.calls == 0;
    drop(store);
    remove_dir_all(&directory)
        .map_err(|error| format!("test directory removal failed: {error}"))?;
    if valid {
        Ok(())
    } else {
        Err(String::from(
            "file durable publication and live cache drifted",
        ))
    }
}

#[test]
fn post_commit_durability_failure_still_reconfigures_live_cache()
-> Result<(), String> {
    let initial = limits(5)?;
    let candidate = limits(2)?;
    let mut store = MemoryStore {
        fail_durability: true,
        ..MemoryStore::default()
    };
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let outcome = publish_and_apply_executable_sequence_cache_limits_durably(
        &mut store,
        &mut cache,
        &mut adapter,
        activation_request(None, candidate)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    match outcome {
        NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Published {
                    current,
                    durability_error,
                    ..
                },
            reconfiguration,
        } if current == candidate
            && durability_error == DurabilityError::Failed
            && reconfiguration.limit_transition()
                == (initial, candidate)
            && cache.limits() == candidate
            && adapter.calls == 0 =>
        {
            Ok(())
        },
        _ => Err(String::from(
            "committed sync failure did not activate live cache",
        )),
    }
}

#[test]
fn prepublication_store_failure_leaves_live_cache_untouched()
-> Result<(), String> {
    let initial = limits(5)?;
    let candidate = limits(2)?;
    let mut store = MemoryStore {
        fail_store: true,
        ..MemoryStore::default()
    };
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let result = publish_and_apply_executable_sequence_cache_limits_durably(
        &mut store,
        &mut cache,
        &mut adapter,
        activation_request(None, candidate)?,
    );
    if matches!(
        result,
        Err(NativeExecutableSequenceCacheLimitsCasError::Blob(
            NativeContinuationBlobPersistenceError::Store(StoreError::Failed,),
        ))
    ) && cache.limits() == initial
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "prepublication store failure changed live cache",
        ))
    }
}
