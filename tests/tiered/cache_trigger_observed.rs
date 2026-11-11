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
//   - Regression coverage for one-shot and bounded-retry claim-gated
//     activation.
// - Must-Not:
//   - Redefine cache policy, retry committed claims, or spawn unattended work.
// - Allows:
//   - Inputs: deterministic observed publications and in-memory cursor CAS.
//   - Outputs: exact unpublished/withheld/claimed/failure evidence.
//   - Side effects: test-local cursor-store and activation-call mutation only.
// - Split-When:
//   - Latency-aware claim gating gains independent regression scope.
// - Merge-When:
//   - Parent coordinator no longer requires private regression access.
// - Summary:
//   - Proves activation runs only after one committed durable cadence claim.
// - Description:
//   - A committed claim survives downstream activation failure.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Non-publication and uncommitted claims never invoke activation.
//

//! Regression coverage for durable-claim gating of observed activation.

use std::collections::VecDeque;
use std::convert::Infallible;
use std::num::NonZeroU64;

use super::*;
use crate::blob_store::{
    NativeContinuationBlobConditionalPublication,
    NativeContinuationBlobConditionalPublicationResult,
};
use crate::cached_cycle::{
    NativeContinuationCachedRetryLatencyHistogram,
    NativeContinuationCachedRetryLatencySample,
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryWindow,
};
use crate::execution_native::{
    NativeExecutableAllocationRequest, NativeExecutableCodeCopyReport,
    NativeExecutableMappingReport, NativeExecutableReleaseRequest,
    NativeExecutableSequenceCacheLimits, NativeInstructionSyncReport,
    NativeInstructionSyncRequest,
};
use crate::{
    executable_cache_limits_latency as cache_latency,
    executable_cache_limits_precedence as cache_select,
    executable_cache_limits_recommendation as cache_rec,
    executable_cache_limits_retry_lifecycle as retry_lifecycle,
    executable_cache_limits_retry_reason as retry_reason,
    executable_cache_limits_trigger_cadence_codec as cursor_codec,
};

type RetryLifecycle =
    retry_lifecycle::NativeExecutableCacheLimitsRetryLifecycle;
type StopReason = retry_reason::NativeExecutableCacheLimitsRetryStopReason;

type ClaimedActivation<'publication, Activation> =
    NativeExecutableCacheLimitsClaimedObservedActivation<
        'publication,
        DurabilityError,
        Activation,
        ClockError,
    >;
type ClaimedError<ActivationError> =
    NativeExecutableCacheLimitsClaimedObservedActivationError<
        Infallible,
        DurabilityError,
        ActivationError,
    >;
type CursorCas =
    cursor_cas::NativeExecutableCacheLimitsTriggerCadenceCas<DurabilityError>;
type RetriedActivation<'publication, Activation> =
    NativeExecutableCacheLimitsRetriedObservedActivation<
        'publication,
        DurabilityError,
        Activation,
        ClockError,
    >;
type RetriedError<ActivationError> =
    NativeExecutableCacheLimitsRetriedObservedActivationError<
        Infallible,
        DurabilityError,
        ActivationError,
    >;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ClockError {
    Failed,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DurabilityError {
    Failed,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum AdapterError {
    UnexpectedOperation,
}

#[derive(Debug, Default)]
struct NoOpAdapter {
    calls: usize,
}

#[derive(Debug, Default)]
struct MemoryStore {
    bytes: Option<Vec<u8>>,
    compare_calls: usize,
    durability_calls: usize,
    fail_durability: bool,
    forced_conflicts: VecDeque<Option<Vec<u8>>>,
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

impl BlobStore for MemoryStore {
    type Error = Infallible;

    fn load(
        &mut self,
        _maximum_bytes: NonZeroUsize,
    ) -> Result<Option<Vec<u8>>, Self::Error> {
        Ok(self.bytes.clone())
    }

    fn replace(&mut self, bytes: &[u8]) -> Result<(), Self::Error> {
        self.bytes = Some(bytes.to_vec());
        Ok(())
    }
}

impl ConditionalBlobStore for MemoryStore {
    fn compare_and_swap(
        &mut self,
        expected: Option<&[u8]>,
        replacement: &[u8],
        _maximum_bytes: NonZeroUsize,
    ) -> NativeContinuationBlobConditionalPublicationResult<Self::Error> {
        self.compare_calls = self.compare_calls.saturating_add(1);
        if let Some(current) = self.forced_conflicts.pop_front() {
            self.bytes = current.clone();
            return Ok(
                NativeContinuationBlobConditionalPublication::Conflict {
                    current,
                },
            );
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
        self.durability_calls = self.durability_calls.saturating_add(1);
        if self.fail_durability {
            Err(DurabilityError::Failed)
        } else {
            Ok(())
        }
    }
}

fn cursor(due_value: u64, interval_value: u64) -> Result<Cursor, String> {
    let due = NonZeroU64::new(due_value)
        .ok_or_else(|| String::from("test due sequence must be positive"))?;
    let interval = NonZeroU64::new(interval_value)
        .ok_or_else(|| String::from("test interval must be positive"))?;
    Ok(Cursor::new(due, interval))
}

fn encode_cursor(value: Cursor) -> Vec<u8> {
    cursor_codec::encode_native_executable_cache_limits_trigger_cadence(value)
}

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test positive value missing"))
}

fn cache_limits(
    entries: usize,
) -> Result<NativeExecutableSequenceCacheLimits, String> {
    positive(entries).map(NativeExecutableSequenceCacheLimits::new)
}

fn observed_request()
-> Result<obs::NativeExecutableCacheLimitsObservedActivationRequest, String> {
    let one = NonZeroU64::new(1)
        .ok_or_else(|| String::from("test ratio must be positive"))?;
    let policy = cache_rec::NativeExecutableCacheLimitsTwoSignalRequest::new(
        cache_rec::NativeExecutableCacheLimitsReuseThreshold::new(
            positive(4)?,
            one,
            one,
        ),
        cache_rec::NativeExecutableCacheLimitsRecommendationSet::new(
            cache_limits(3)?,
            cache_limits(8)?,
        ),
        cache_rec::NativeExecutableCacheLimitsPressureThreshold::new(
            positive(4)?,
            2,
            1,
        ),
        cache_rec::NativeExecutableCacheLimitsRecommendationSet::new(
            cache_limits(3)?,
            cache_limits(2)?,
        ),
    );
    Ok(
        obs::NativeExecutableCacheLimitsObservedActivationRequest::new(
            &policy,
            cache_select::NativeExecutableCacheLimitsPrecedence::Pressure,
            None,
            positive(40)?,
        ),
    )
}

fn observed_latency_request() -> Result<
    obs::NativeExecutableCacheLimitsObservedLatencyActivationRequest,
    String,
> {
    let activation = observed_request()?;
    let latency = cache_latency::NativeExecutableCacheLimitsLatencyRequest::new(
        cache_latency::NativeExecutableCacheLimitsLatencyThreshold::new(
            positive(1)?,
            10,
            10,
        ),
        cache_rec::NativeExecutableCacheLimitsRecommendationSet::new(
            cache_limits(3)?,
            cache_limits(2)?,
        ),
    );
    Ok(
        obs::NativeExecutableCacheLimitsObservedLatencyActivationRequest::new(
            &activation,
            latency,
        ),
    )
}

fn retry_request(
    expected: Cursor,
    maximum_attempts: usize,
) -> Result<NativeExecutableCacheLimitsRetriedObservedRequest, String> {
    Ok(NativeExecutableCacheLimitsRetriedObservedRequest::new(
        expected,
        positive(32)?,
        positive(maximum_attempts)?,
    ))
}

fn published(
    sequence: usize,
) -> Result<TelemetryPublication<ClockError>, String> {
    let mut window = NativeContinuationCachedRetryTelemetryWindow::new(
        positive(sequence.max(1))?,
    );
    let telemetry = NativeContinuationCachedRetryTelemetry::default();
    let mut append = None;
    for _ in 0..sequence {
        append = Some(
            window
                .append(telemetry)
                .map_err(|error| error.to_string())?,
        );
    }
    let append = append.ok_or_else(|| {
        String::from("test publication sequence must be positive")
    })?;
    let sample = NativeContinuationCachedRetryLatencySample::new(10);
    let mut histogram =
        NativeContinuationCachedRetryLatencyHistogram::new(vec![20])
            .map_err(|error| error.to_string())?;
    let latency = histogram
        .record(sample)
        .map_err(|error| error.to_string())?;
    Ok(TelemetryPublication::Published {
        latency,
        sample,
        telemetry,
        window: Box::new(append),
    })
}

#[test]
fn committed_claim_invokes_activation_once() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let candidate = cursor(3, 2)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let outcome = activate_after_claim(
        &publication,
        &mut store,
        NativeExecutableCacheLimitsClaimedObservedRequest::new(
            expected,
            positive(32)?,
        ),
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(17)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        ClaimedActivation::Claimed {
            claim,
            observed: 17,
        } if claim.is_committed()
    ) && calls == 1
        && store.compare_calls == 1
        && store.durability_calls == 1
        && store.bytes == Some(encode_cursor(candidate))
    {
        Ok(())
    } else {
        Err(String::from("committed claim did not gate one activation"))
    }
}

#[test]
fn durability_failure_claim_still_invokes_activation() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let candidate = cursor(3, 2)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        fail_durability: true,
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let outcome = activate_after_claim(
        &publication,
        &mut store,
        NativeExecutableCacheLimitsClaimedObservedRequest::new(
            expected,
            positive(32)?,
        ),
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(19)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        ClaimedActivation::Claimed {
            claim,
            observed: 19,
        } if claim.is_committed()
    ) && calls == 1
        && store.compare_calls == 1
        && store.durability_calls == 1
        && store.bytes == Some(encode_cursor(candidate))
    {
        Ok(())
    } else {
        Err(String::from(
            "committed durability failure withheld activation",
        ))
    }
}

#[test]
fn activation_failure_retains_committed_claim() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let candidate = cursor(3, 2)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        ..MemoryStore::default()
    };
    let result = activate_after_claim(
        &publication,
        &mut store,
        NativeExecutableCacheLimitsClaimedObservedRequest::new(
            expected,
            positive(32)?,
        ),
        || Err::<u8, &'static str>("activation failed"),
    );
    if matches!(
        result,
        Err(error)
            if matches!(
                &*error,
                ClaimedError::Observed {
                    claim,
                    error: "activation failed",
                } if claim.is_committed()
            )
    ) && store.compare_calls == 1
        && store.durability_calls == 1
        && store.bytes == Some(encode_cursor(candidate))
    {
        Ok(())
    } else {
        Err(String::from("activation failure lost committed claim"))
    }
}

#[test]
fn early_claim_withholds_activation_without_store_work() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(2, 2)?;
    let expected_bytes = encode_cursor(expected);
    let mut store = MemoryStore {
        bytes: Some(expected_bytes.clone()),
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let outcome = activate_after_claim(
        &publication,
        &mut store,
        NativeExecutableCacheLimitsClaimedObservedRequest::new(
            expected,
            positive(32)?,
        ),
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(23)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        ClaimedActivation::ClaimWithheld {
            claim,
        } if !claim.is_committed()
    ) && calls == 0
        && store.compare_calls == 0
        && store.durability_calls == 0
        && store.bytes == Some(expected_bytes)
    {
        Ok(())
    } else {
        Err(String::from("early claim reached activation"))
    }
}

#[test]
fn stale_claim_conflict_withholds_activation() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let current = cursor(5, 2)?;
    let current_bytes = encode_cursor(current);
    let mut store = MemoryStore {
        bytes: Some(current_bytes.clone()),
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let outcome = activate_after_claim(
        &publication,
        &mut store,
        NativeExecutableCacheLimitsClaimedObservedRequest::new(
            expected,
            positive(32)?,
        ),
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(29)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        ClaimedActivation::ClaimWithheld {
            claim: Claim::Attempted {
                publication: CursorCas::Conflict {
                    current: Some(observed),
                    ..
                },
                ..
            },
        } if observed == current
    ) && calls == 0
        && store.compare_calls == 1
        && store.durability_calls == 0
        && store.bytes == Some(current_bytes)
    {
        Ok(())
    } else {
        Err(String::from("stale claim conflict reached activation"))
    }
}

#[test]
fn unpublished_telemetry_skips_claim_and_activation() -> Result<(), String> {
    let publication = TelemetryPublication::ClockFailure {
        error: ClockError::Failed,
    };
    let mut store = MemoryStore::default();
    let mut calls = 0_usize;
    let outcome = activate_after_claim(
        &publication,
        &mut store,
        NativeExecutableCacheLimitsClaimedObservedRequest::new(
            cursor(1, 2)?,
            positive(32)?,
        ),
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(31)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        ClaimedActivation::TelemetryUnpublished {
            publication: observed,
        } if core::ptr::eq(observed, &publication)
    ) && calls == 0
        && store.compare_calls == 0
        && store.durability_calls == 0
        && store.bytes.is_none()
    {
        Ok(())
    } else {
        Err(String::from(
            "unpublished telemetry reached claim or activation",
        ))
    }
}

#[test]
fn retry_conflict_then_commit_invokes_activation_once() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let candidate = cursor(4, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let outcome = activate_after_claim_retries(
        &publication,
        &mut store,
        retry_request(expected, 3)?,
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(37)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        RetriedActivation::Claimed {
            retry,
            observed: 37,
        } if retry.attempts() == 2
            && retry.outcome().is_committed()
    ) && calls == 1
        && store.compare_calls == 2
        && store.durability_calls == 1
        && store.bytes == Some(encode_cursor(candidate))
    {
        Ok(())
    } else {
        Err(String::from(
            "retried committed claim did not gate activation",
        ))
    }
}

#[test]
fn retry_refresh_non_due_withholds_activation() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(3, 2)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let outcome = activate_after_claim_retries(
        &publication,
        &mut store,
        retry_request(expected, 3)?,
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(41)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 2
                && !retry.outcome().is_committed()
    ) && calls == 0
        && store.compare_calls == 1
        && store.durability_calls == 0
        && store.bytes == Some(encode_cursor(refreshed))
    {
        Ok(())
    } else {
        Err(String::from("refreshed non-due retry reached activation"))
    }
}

#[test]
fn retry_budget_exhaustion_withholds_activation() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let outcome = activate_after_claim_retries(
        &publication,
        &mut store,
        retry_request(expected, 1)?,
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(43)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 1
                && !retry.outcome().is_committed()
    ) && calls == 0
        && store.compare_calls == 1
        && store.durability_calls == 0
        && store.bytes == Some(encode_cursor(refreshed))
    {
        Ok(())
    } else {
        Err(String::from("exhausted retry budget reached activation"))
    }
}

#[test]
fn retry_durability_failure_invokes_activation_once() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let candidate = cursor(3, 2)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        fail_durability: true,
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let outcome = activate_after_claim_retries(
        &publication,
        &mut store,
        retry_request(expected, 3)?,
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(47)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        RetriedActivation::Claimed {
            retry,
            observed: 47,
        } if retry.attempts() == 1
            && retry.outcome().is_committed()
    ) && calls == 1
        && store.compare_calls == 1
        && store.durability_calls == 1
        && store.bytes == Some(encode_cursor(candidate))
    {
        Ok(())
    } else {
        Err(String::from(
            "committed retry durability failure withheld activation",
        ))
    }
}

#[test]
fn retry_activation_failure_retains_full_retry_evidence() -> Result<(), String>
{
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let candidate = cursor(4, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let result = activate_after_claim_retries(
        &publication,
        &mut store,
        retry_request(expected, 3)?,
        || Err::<u8, &'static str>("activation failed after retry"),
    );
    if matches!(
        result,
        Err(error)
            if matches!(
                &*error,
                RetriedError::Observed {
                    retry,
                    error: "activation failed after retry",
                } if retry.attempts() == 2
                    && retry.outcome().is_committed()
            )
    ) && store.compare_calls == 2
        && store.durability_calls == 1
        && store.bytes == Some(encode_cursor(candidate))
    {
        Ok(())
    } else {
        Err(String::from("activation failure lost claim retry evidence"))
    }
}

#[test]
fn controlled_retry_stop_withholds_activation() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let mut seen = None;
    let controlled =
        NativeExecutableCacheLimitsControlledRetriedObservedRequest::new(
            retry_request(expected, 3)?,
            |conflict: NativeContinuationRetryConflict| {
                seen = Some(conflict.completed_attempts());
                NativeContinuationRetryDirective::Stop
            },
        );
    let outcome = activate_after_controlled_claim_retries(
        &publication,
        &mut store,
        controlled,
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(53)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 1
                && !retry.outcome().is_committed()
    ) && seen == Some(1)
        && calls == 0
        && store.compare_calls == 1
        && store.durability_calls == 0
        && store.bytes == Some(encode_cursor(refreshed))
    {
        Ok(())
    } else {
        Err(String::from("caller stop reached activation"))
    }
}

#[test]
fn controlled_retry_continue_commits_then_activates_once() -> Result<(), String>
{
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let candidate = cursor(4, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let mut seen = None;
    let controlled =
        NativeExecutableCacheLimitsControlledRetriedObservedRequest::new(
            retry_request(expected, 3)?,
            |conflict: NativeContinuationRetryConflict| {
                seen = Some(conflict.completed_attempts());
                NativeContinuationRetryDirective::Continue
            },
        );
    let outcome = activate_after_controlled_claim_retries(
        &publication,
        &mut store,
        controlled,
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(59)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        RetriedActivation::Claimed {
            retry,
            observed: 59,
        } if retry.attempts() == 2
            && retry.outcome().is_committed()
    ) && seen == Some(1)
        && calls == 1
        && store.compare_calls == 2
        && store.durability_calls == 1
        && store.bytes == Some(encode_cursor(candidate))
    {
        Ok(())
    } else {
        Err(String::from("caller continue did not reach one activation"))
    }
}

#[test]
fn reasoned_retry_stop_preserves_reason_and_withholds_activation()
-> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let mut stop_state = NativeContinuationRetryStopState::<StopReason>::new();
    let reasoned =
        NativeExecutableCacheLimitsReasonedRetriedObservedRequest::new(
            retry_request(expected, 3)?,
            &mut stop_state,
            |_conflict| {
                NativeContinuationRetryDecision::Stop(
                    StopReason::ContentionObserved,
                )
            },
        );
    let outcome = activate_after_reasoned_claim_retries(
        &publication,
        &mut store,
        reasoned,
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(61)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    let stop = stop_state
        .stop()
        .ok_or_else(|| String::from("typed stop reason disappeared"))?;
    if matches!(
        outcome,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 1
                && !retry.outcome().is_committed()
    ) && stop.conflict().completed_attempts() == 1
        && stop.reason() == &StopReason::ContentionObserved
        && stop.reason().id() == "contention-observed"
        && calls == 0
        && store.compare_calls == 1
        && store.durability_calls == 0
        && store.bytes == Some(encode_cursor(refreshed))
    {
        Ok(())
    } else {
        Err(String::from(
            "typed caller stop did not remain bound to withheld activation",
        ))
    }
}

#[test]
fn reasoned_retry_continue_commits_without_stop_and_activates_once()
-> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let candidate = cursor(4, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let mut stop_state = NativeContinuationRetryStopState::<StopReason>::new();
    let reasoned =
        NativeExecutableCacheLimitsReasonedRetriedObservedRequest::new(
            retry_request(expected, 3)?,
            &mut stop_state,
            |_conflict| NativeContinuationRetryDecision::Continue,
        );
    let outcome = activate_after_reasoned_claim_retries(
        &publication,
        &mut store,
        reasoned,
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(67)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        RetriedActivation::Claimed {
            retry,
            observed: 67,
        } if retry.attempts() == 2
            && retry.outcome().is_committed()
    ) && stop_state.stop().is_none()
        && calls == 1
        && store.compare_calls == 2
        && store.durability_calls == 1
        && store.bytes == Some(encode_cursor(candidate))
    {
        Ok(())
    } else {
        Err(String::from(
            "typed continue invented stop evidence or skipped activation",
        ))
    }
}

#[test]
fn reasoned_retry_unpublished_clears_stop_reason_without_claim()
-> Result<(), String> {
    let publication = TelemetryPublication::ClockFailure {
        error: ClockError::Failed,
    };
    let expected = cursor(1, 2)?;
    let mut store = MemoryStore::default();
    let mut calls = 0_usize;
    let mut decisions = 0_usize;
    let mut stop_state = NativeContinuationRetryStopState::<StopReason>::new();
    let stale_directive = stop_state.resolve(
        NativeContinuationRetryConflict::new(7),
        NativeContinuationRetryDecision::Stop(StopReason::PolicyLimit),
    );
    let reasoned =
        NativeExecutableCacheLimitsReasonedRetriedObservedRequest::new(
            retry_request(expected, 3)?,
            &mut stop_state,
            |_conflict| {
                decisions = decisions.saturating_add(1);
                NativeContinuationRetryDecision::Stop(StopReason::PolicyLimit)
            },
        );
    let outcome = activate_after_reasoned_claim_retries(
        &publication,
        &mut store,
        reasoned,
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(73)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        RetriedActivation::TelemetryUnpublished {
            publication: observed,
        } if core::ptr::eq(observed, &publication)
    ) && stale_directive == NativeContinuationRetryDirective::Stop
        && stop_state.stop().is_none()
        && decisions == 0
        && calls == 0
        && store.compare_calls == 0
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "unpublished retry retained stop evidence or touched claim state",
        ))
    }
}

#[test]
fn reasoned_retry_budget_exhaustion_has_no_stop_reason() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let mut decisions = 0_usize;
    let mut stop_state = NativeContinuationRetryStopState::<StopReason>::new();
    let stale_directive = stop_state.resolve(
        NativeContinuationRetryConflict::new(9),
        NativeContinuationRetryDecision::Stop(StopReason::PolicyLimit),
    );
    let reasoned =
        NativeExecutableCacheLimitsReasonedRetriedObservedRequest::new(
            retry_request(expected, 1)?,
            &mut stop_state,
            |_conflict| {
                decisions = decisions.saturating_add(1);
                NativeContinuationRetryDecision::Stop(StopReason::PolicyLimit)
            },
        );
    let outcome = activate_after_reasoned_claim_retries(
        &publication,
        &mut store,
        reasoned,
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(71)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 1
                && !retry.outcome().is_committed()
    ) && stale_directive == NativeContinuationRetryDirective::Stop
        && stop_state.stop().is_none()
        && decisions == 0
        && calls == 0
        && store.compare_calls == 1
        && store.durability_calls == 0
        && store.bytes == Some(encode_cursor(refreshed))
    {
        Ok(())
    } else {
        Err(String::from(
            "retry budget exhaustion invented caller stop evidence",
        ))
    }
}

#[test]
fn policy_retry_return_on_contention_preserves_reason() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let mut stop_state =
        NativeContinuationRetryStopState::<RetryStopReason>::new();
    let policy_request =
        NativeExecutableCacheLimitsPolicyRetriedObservedRequest::new(
            retry_request(expected, 3)?,
            &mut stop_state,
            RetryConflictPolicy::return_on_contention(),
        );
    let outcome = activate_after_policy_claim_retries(
        &publication,
        &mut store,
        policy_request,
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(79)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    let stop = stop_state
        .stop()
        .ok_or_else(|| String::from("product stop reason disappeared"))?;
    if matches!(
        outcome,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 1
                && !retry.outcome().is_committed()
    ) && stop.conflict().completed_attempts() == 1
        && stop.reason() == &RetryStopReason::ContentionObserved
        && calls == 0
        && store.compare_calls == 1
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "return-on-contention policy did not retain exact stop evidence",
        ))
    }
}

#[test]
fn policy_retry_attempt_limit_stops_second_conflict() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let first = cursor(1, 3)?;
    let second = cursor(1, 4)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([
            Some(encode_cursor(first)),
            Some(encode_cursor(second)),
        ]),
        ..MemoryStore::default()
    };
    let mut calls = 0_usize;
    let mut stop_state =
        NativeContinuationRetryStopState::<RetryStopReason>::new();
    let policy_request =
        NativeExecutableCacheLimitsPolicyRetriedObservedRequest::new(
            retry_request(expected, 3)?,
            &mut stop_state,
            RetryConflictPolicy::attempt_limit(positive(2)?),
        );
    let outcome = activate_after_policy_claim_retries(
        &publication,
        &mut store,
        policy_request,
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(83)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    let stop = stop_state
        .stop()
        .ok_or_else(|| String::from("policy-limit reason disappeared"))?;
    if matches!(
        outcome,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 2
                && !retry.outcome().is_committed()
    ) && stop.conflict().completed_attempts() == 2
        && stop.reason() == &RetryStopReason::PolicyLimit
        && calls == 0
        && store.compare_calls == 2
        && store.durability_calls == 0
        && store.bytes == Some(encode_cursor(second))
    {
        Ok(())
    } else {
        Err(String::from(
            "attempt-limit policy did not stop exact second conflict",
        ))
    }
}

#[test]
fn policy_retry_lifecycle_reuses_state_and_clears_stop_on_success()
-> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let candidate = cursor(4, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut lifecycle = RetryLifecycle::new(
        positive(32)?,
        positive(3)?,
        RetryConflictPolicy::return_on_contention(),
    );
    let mut calls = 0_usize;
    let first = activate_after_policy_claim_retries(
        &publication,
        &mut store,
        NativeExecutableCacheLimitsPolicyRetriedObservedRequest::from_lifecycle(
            &mut lifecycle,
            expected,
        ),
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(89)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    let first_stop = lifecycle
        .stop()
        .ok_or_else(|| String::from("lifecycle stop evidence disappeared"))?;
    if !matches!(
        first,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 1
                && !retry.outcome().is_committed()
    ) || first_stop.reason() != &RetryStopReason::ContentionObserved
        || first_stop.conflict().completed_attempts() != 1
        || calls != 0
    {
        return Err(String::from("lifecycle first stop evidence drifted"));
    }
    let second = activate_after_policy_claim_retries(
        &publication,
        &mut store,
        NativeExecutableCacheLimitsPolicyRetriedObservedRequest::from_lifecycle(
            &mut lifecycle,
            refreshed,
        ),
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(97)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        second,
        RetriedActivation::Claimed {
            retry,
            observed: 97,
        } if retry.attempts() == 1
            && retry.outcome().is_committed()
    ) && lifecycle.stop().is_none()
        && lifecycle.maximum_bytes() == positive(32)?
        && lifecycle.maximum_attempts() == positive(3)?
        && lifecycle.policy() == RetryConflictPolicy::return_on_contention()
        && calls == 1
        && store.compare_calls == 2
        && store.durability_calls == 1
        && store.bytes == Some(encode_cursor(candidate))
    {
        Ok(())
    } else {
        Err(String::from(
            "lifecycle reuse did not clear stop state on committed success",
        ))
    }
}

#[test]
fn policy_public_wrappers_skip_all_resources_when_unpublished()
-> Result<(), String> {
    let publication = TelemetryPublication::ClockFailure {
        error: ClockError::Failed,
    };
    let expected = cursor(1, 2)?;
    let current = cache_limits(4)?;

    {
        let mut cursor_store = MemoryStore::default();
        let mut policy_store = MemoryStore::default();
        let mut cache = NativeExecutableSequenceCache::with_limits(current);
        let mut adapter = NoOpAdapter::default();
        let mut lifecycle = RetryLifecycle::new(
            positive(32)?,
            positive(3)?,
            RetryConflictPolicy::return_on_contention(),
        );
        let mut context =
            NativeExecutableCacheLimitsClaimedObservedCacheContext::new(
                &mut cursor_store,
                &mut policy_store,
                &mut cache,
                &mut adapter,
            );
        let outcome = activate_policy_retried_observed_cache_limits_durably(
            &publication,
            &mut context,
            NativeExecutableCacheLimitsPolicyRetriedObservedRequest::
                from_lifecycle(&mut lifecycle, expected),
                &observed_request()?,
            )
            .map_err(|error| format!("{error:?}"))?;
        if !matches!(
            outcome,
            RetriedActivation::TelemetryUnpublished {
                publication: observed,
            } if core::ptr::eq(observed, &publication)
        ) || cursor_store.compare_calls != 0
            || policy_store.compare_calls != 0
            || cache.limits() != current
            || adapter.calls != 0
            || lifecycle.stop().is_some()
        {
            return Err(String::from(
                "ordinary policy wrapper touched unpublished resources",
            ));
        }
    }

    {
        let mut cursor_store = MemoryStore::default();
        let mut policy_store = MemoryStore::default();
        let mut cache = NativeExecutableSequenceCache::with_limits(current);
        let mut adapter = NoOpAdapter::default();
        let mut lifecycle = RetryLifecycle::new(
            positive(32)?,
            positive(3)?,
            RetryConflictPolicy::return_on_contention(),
        );
        let mut context =
            NativeExecutableCacheLimitsClaimedObservedCacheContext::new(
                &mut cursor_store,
                &mut policy_store,
                &mut cache,
                &mut adapter,
            );
        let outcome =
            activate_policy_retried_observed_cache_limits_with_latency_durably(
                &publication,
                &mut context,
                NativeExecutableCacheLimitsPolicyRetriedObservedRequest::
                    from_lifecycle(&mut lifecycle, expected),
                &observed_latency_request()?,
            )
            .map_err(|error| format!("{error:?}"))?;
        if !matches!(
            outcome,
            RetriedActivation::TelemetryUnpublished {
                publication: observed,
            } if core::ptr::eq(observed, &publication)
        ) || cursor_store.compare_calls != 0
            || policy_store.compare_calls != 0
            || cache.limits() != current
            || adapter.calls != 0
            || lifecycle.stop().is_some()
        {
            return Err(String::from(
                "latency policy wrapper touched unpublished resources",
            ));
        }
    }

    {
        let mut cursor_store = MemoryStore::default();
        let mut policy_store = MemoryStore::default();
        let mut cache =
            NativeExecutableSequenceLeaseCache::with_limits(current);
        let mut adapter = NoOpAdapter::default();
        let mut lifecycle = RetryLifecycle::new(
            positive(32)?,
            positive(3)?,
            RetryConflictPolicy::return_on_contention(),
        );
        let mut context =
            NativeExecutableCacheLimitsClaimedObservedLeaseContext::new(
                &mut cursor_store,
                &mut policy_store,
                &mut cache,
                &mut adapter,
            );
        let outcome =
            activate_policy_retried_observed_lease_cache_limits_durably(
                &publication,
            &mut context,
            NativeExecutableCacheLimitsPolicyRetriedObservedRequest::
                from_lifecycle(&mut lifecycle, expected),
            &observed_request()?,
        )
        .map_err(|error| format!("{error:?}"))?;
        if !matches!(
            outcome,
            RetriedActivation::TelemetryUnpublished {
                publication: observed,
            } if core::ptr::eq(observed, &publication)
        ) || cursor_store.compare_calls != 0
            || policy_store.compare_calls != 0
            || cache.limits() != current
            || adapter.calls != 0
            || lifecycle.stop().is_some()
        {
            return Err(String::from(
                "lease policy wrapper touched unpublished resources",
            ));
        }
    }

    {
        let mut cursor_store = MemoryStore::default();
        let mut policy_store = MemoryStore::default();
        let mut cache =
            NativeExecutableSequenceLeaseCache::with_limits(current);
        let mut adapter = NoOpAdapter::default();
        let mut lifecycle = RetryLifecycle::new(
            positive(32)?,
            positive(3)?,
            RetryConflictPolicy::return_on_contention(),
        );
        let mut context =
            NativeExecutableCacheLimitsClaimedObservedLeaseContext::new(
                &mut cursor_store,
                &mut policy_store,
                &mut cache,
                &mut adapter,
            );
        let outcome =
            activate_policy_retried_lease_cache_limits_with_latency_durably(
                &publication,
                &mut context,
                NativeExecutableCacheLimitsPolicyRetriedObservedRequest::
                    from_lifecycle(&mut lifecycle, expected),
                &observed_latency_request()?,
            )
            .map_err(|error| format!("{error:?}"))?;
        if !matches!(
            outcome,
            RetriedActivation::TelemetryUnpublished {
                publication: observed,
            } if core::ptr::eq(observed, &publication)
        ) || cursor_store.compare_calls != 0
            || policy_store.compare_calls != 0
            || cache.limits() != current
            || adapter.calls != 0
            || lifecycle.stop().is_some()
        {
            return Err(String::from(
                "latency lease wrapper touched unpublished resources",
            ));
        }
    }

    Ok(())
}

#[test]
fn retained_lifecycle_request_requires_and_uses_safe_cursor()
-> Result<(), String> {
    let policy = RetryConflictPolicy::return_on_contention();
    let mut empty = RetryLifecycle::new(positive(32)?, positive(3)?, policy);
    if NativeExecutableCacheLimitsPolicyRetriedObservedRequest::
        from_retained_lifecycle(&mut empty)
        .is_some()
    {
        return Err(String::from(
            "cursorless lifecycle constructed retry authority",
        ));
    }

    let expected = cursor(5, 2)?;
    let publication = published(1)?;
    let expected_bytes = encode_cursor(expected);
    let mut store = MemoryStore {
        bytes: Some(expected_bytes.clone()),
        ..MemoryStore::default()
    };
    let mut lifecycle = RetryLifecycle::new_with_cursor(
        expected,
        positive(32)?,
        positive(3)?,
        policy,
    );
    let request =
        NativeExecutableCacheLimitsPolicyRetriedObservedRequest::
            from_retained_lifecycle(&mut lifecycle)
            .ok_or_else(|| String::from("retained cursor was not consumable"))?;
    let mut calls = 0_usize;
    let outcome = activate_after_policy_claim_retries(
        &publication,
        &mut store,
        request,
        || {
            calls = calls.saturating_add(1);
            Ok::<u8, &'static str>(101)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 1
                && !retry.outcome().is_committed()
    ) && calls == 0
        && store.compare_calls == 0
        && store.durability_calls == 0
        && store.bytes == Some(expected_bytes)
        && lifecycle.expected_cursor() == Some(expected)
    {
        Ok(())
    } else {
        Err(String::from(
            "retained lifecycle cursor did not bind exact retry request",
        ))
    }
}

#[test]
fn lifecycle_observes_withheld_retry_cursor() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut lifecycle = RetryLifecycle::new_with_cursor(
        expected,
        positive(32)?,
        positive(3)?,
        RetryConflictPolicy::return_on_contention(),
    );
    let request =
        NativeExecutableCacheLimitsPolicyRetriedObservedRequest::
            from_retained_lifecycle(&mut lifecycle)
            .ok_or_else(|| String::from("retained cursor disappeared"))?;
    let outcome = activate_after_policy_claim_retries(
        &publication,
        &mut store,
        request,
        || Ok::<u8, &'static str>(103),
    )
    .map_err(|error| format!("{error:?}"))?;
    lifecycle.observe_activation(&outcome);
    if matches!(
        outcome,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 1
                && !retry.outcome().is_committed()
    ) && lifecycle.expected_cursor() == Some(refreshed)
        && lifecycle.stop().is_some_and(|stop| {
            stop.reason() == &RetryStopReason::ContentionObserved
        })
    {
        Ok(())
    } else {
        Err(String::from(
            "withheld activation did not advance lifecycle cursor exactly",
        ))
    }
}

#[test]
fn lifecycle_observes_committed_retry_on_activation_failure()
-> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let candidate = cursor(3, 2)?;
    let mut store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        ..MemoryStore::default()
    };
    let mut lifecycle = RetryLifecycle::new_with_cursor(
        expected,
        positive(32)?,
        positive(3)?,
        RetryConflictPolicy::return_on_contention(),
    );
    let request =
        NativeExecutableCacheLimitsPolicyRetriedObservedRequest::
            from_retained_lifecycle(&mut lifecycle)
            .ok_or_else(|| String::from("retained cursor disappeared"))?;
    let result = activate_after_policy_claim_retries(
        &publication,
        &mut store,
        request,
        || Err::<u8, &'static str>("activation failed"),
    );
    let error = result
        .err()
        .ok_or_else(|| String::from("activation failure disappeared"))?;
    lifecycle.observe_activation_error(&error);
    if matches!(
        &*error,
        RetriedError::Observed { retry, error: "activation failed" }
            if retry.attempts() == 1 && retry.outcome().is_committed()
    ) && lifecycle.expected_cursor() == Some(candidate)
        && lifecycle.stop().is_none()
        && store.compare_calls == 1
        && store.durability_calls == 1
        && store.bytes == Some(encode_cursor(candidate))
    {
        Ok(())
    } else {
        Err(String::from(
            "post-claim failure did not preserve lifecycle cursor progress",
        ))
    }
}

#[test]
fn retained_lifecycle_wrapper_fails_closed_and_observes_conflict()
-> Result<(), String> {
    let publication = published(1)?;
    let current = cache_limits(4)?;
    let mut empty_cursor_store = MemoryStore::default();
    let mut empty_policy_store = MemoryStore::default();
    let mut empty_cache = NativeExecutableSequenceCache::with_limits(current);
    let mut empty_adapter = NoOpAdapter::default();
    let mut empty_lifecycle = RetryLifecycle::new(
        positive(32)?,
        positive(3)?,
        RetryConflictPolicy::return_on_contention(),
    );
    let mut empty_context =
        NativeExecutableCacheLimitsClaimedObservedCacheContext::new(
            &mut empty_cursor_store,
            &mut empty_policy_store,
            &mut empty_cache,
            &mut empty_adapter,
        );
    if activate_retained_lifecycle_observed_cache_limits_durably(
        &publication,
        &mut empty_context,
        &mut empty_lifecycle,
        &observed_request()?,
    )
    .is_some()
        || empty_cursor_store.compare_calls != 0
        || empty_policy_store.compare_calls != 0
        || empty_adapter.calls != 0
    {
        return Err(String::from(
            "cursorless retained lifecycle touched activation resources",
        ));
    }

    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let mut cursor_store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut policy_store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let mut lifecycle = RetryLifecycle::new_with_cursor(
        expected,
        positive(32)?,
        positive(3)?,
        RetryConflictPolicy::return_on_contention(),
    );
    let mut context =
        NativeExecutableCacheLimitsClaimedObservedCacheContext::new(
            &mut cursor_store,
            &mut policy_store,
            &mut cache,
            &mut adapter,
        );
    let result = activate_retained_lifecycle_observed_cache_limits_durably(
        &publication,
        &mut context,
        &mut lifecycle,
        &observed_request()?,
    )
    .ok_or_else(|| String::from("retained cursor authority disappeared"))?
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        result,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 1 && !retry.outcome().is_committed()
    ) && lifecycle.expected_cursor() == Some(refreshed)
        && lifecycle.stop().is_some_and(|stop| {
            stop.reason() == &RetryStopReason::ContentionObserved
        })
        && cursor_store.compare_calls == 1
        && cursor_store.durability_calls == 0
        && policy_store.compare_calls == 0
        && cache.limits() == current
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "retained lifecycle wrapper did not observe exact conflict",
        ))
    }
}

#[test]
fn retained_latency_cache_wrapper_observes_conflict() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let current = cache_limits(4)?;
    let mut cursor_store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut policy_store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let mut lifecycle = RetryLifecycle::new_with_cursor(
        expected,
        positive(32)?,
        positive(3)?,
        RetryConflictPolicy::return_on_contention(),
    );
    let mut context =
        NativeExecutableCacheLimitsClaimedObservedCacheContext::new(
            &mut cursor_store,
            &mut policy_store,
            &mut cache,
            &mut adapter,
        );
    let result =
        activate_retained_lifecycle_observed_cache_limits_with_latency_durably(
            &publication,
            &mut context,
            &mut lifecycle,
            &observed_latency_request()?,
        )
        .ok_or_else(|| String::from("retained latency cursor disappeared"))?
        .map_err(|error| format!("{error:?}"))?;
    if matches!(
        result,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 1 && !retry.outcome().is_committed()
    ) && lifecycle.expected_cursor() == Some(refreshed)
        && lifecycle.stop().is_some_and(|stop| {
            stop.reason() == &RetryStopReason::ContentionObserved
        })
        && cursor_store.compare_calls == 1
        && cursor_store.durability_calls == 0
        && policy_store.compare_calls == 0
        && cache.limits() == current
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "retained latency cache wrapper did not observe exact conflict",
        ))
    }
}

#[test]
fn retained_lease_cache_wrapper_observes_conflict() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let current = cache_limits(4)?;
    let mut cursor_store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut policy_store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceLeaseCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let mut lifecycle = RetryLifecycle::new_with_cursor(
        expected,
        positive(32)?,
        positive(3)?,
        RetryConflictPolicy::return_on_contention(),
    );
    let mut context =
        NativeExecutableCacheLimitsClaimedObservedLeaseContext::new(
            &mut cursor_store,
            &mut policy_store,
            &mut cache,
            &mut adapter,
        );
    let result =
        activate_retained_lifecycle_observed_lease_cache_limits_durably(
            &publication,
            &mut context,
            &mut lifecycle,
            &observed_request()?,
        )
        .ok_or_else(|| String::from("retained lease cursor disappeared"))?
        .map_err(|error| format!("{error:?}"))?;
    if matches!(
        result,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 1 && !retry.outcome().is_committed()
    ) && lifecycle.expected_cursor() == Some(refreshed)
        && lifecycle.stop().is_some_and(|stop| {
            stop.reason() == &RetryStopReason::ContentionObserved
        })
        && cursor_store.compare_calls == 1
        && cursor_store.durability_calls == 0
        && policy_store.compare_calls == 0
        && cache.limits() == current
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "retained lease wrapper did not observe exact conflict",
        ))
    }
}

#[test]
fn retained_latency_lease_wrapper_observes_conflict() -> Result<(), String> {
    let publication = published(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let current = cache_limits(4)?;
    let mut cursor_store = MemoryStore {
        bytes: Some(encode_cursor(expected)),
        forced_conflicts: VecDeque::from([Some(encode_cursor(refreshed))]),
        ..MemoryStore::default()
    };
    let mut policy_store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceLeaseCache::with_limits(current);
    let mut adapter = NoOpAdapter::default();
    let mut lifecycle = RetryLifecycle::new_with_cursor(
        expected,
        positive(32)?,
        positive(3)?,
        RetryConflictPolicy::return_on_contention(),
    );
    let mut context =
        NativeExecutableCacheLimitsClaimedObservedLeaseContext::new(
            &mut cursor_store,
            &mut policy_store,
            &mut cache,
            &mut adapter,
        );
    let result =
        activate_retained_lifecycle_lease_cache_limits_with_latency_durably(
            &publication,
            &mut context,
            &mut lifecycle,
            &observed_latency_request()?,
        )
        .ok_or_else(|| {
            String::from("retained latency lease cursor disappeared")
        })?
        .map_err(|error| format!("{error:?}"))?;
    if matches!(
        result,
        RetriedActivation::ClaimWithheld { retry }
            if retry.attempts() == 1 && !retry.outcome().is_committed()
    ) && lifecycle.expected_cursor() == Some(refreshed)
        && lifecycle.stop().is_some_and(|stop| {
            stop.reason() == &RetryStopReason::ContentionObserved
        })
        && cursor_store.compare_calls == 1
        && cursor_store.durability_calls == 0
        && policy_store.compare_calls == 0
        && cache.limits() == current
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "retained latency lease wrapper did not observe exact conflict",
        ))
    }
}
