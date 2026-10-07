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
//   - Regression coverage for claim-gated observed activation sequencing.
// - Must-Not:
//   - Redefine cache policy, retry conflicts, or spawn unattended work.
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
use crate::executable_cache_limits_trigger_cadence_codec as cursor_codec;

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

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ClockError {
    Failed,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DurabilityError {
    Failed,
}

#[derive(Debug, Default)]
struct MemoryStore {
    bytes: Option<Vec<u8>>,
    compare_calls: usize,
    durability_calls: usize,
    fail_durability: bool,
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
