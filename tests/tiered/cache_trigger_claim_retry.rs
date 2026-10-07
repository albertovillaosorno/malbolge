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
//   - Regression coverage for bounded cache-trigger claim conflict retry.
// - Must-Not:
//   - Activate policy, infer backoff, retry committed claims, or invent
//     cadence.
// - Allows:
//   - Inputs: deterministic append evidence and scripted conditional conflicts.
//   - Outputs: exact terminal claim and completed-attempt evidence.
//   - Side effects: test-local cursor-store mutation only.
// - Split-When:
//   - Product contention policy gains independent regression lifecycle.
// - Merge-When:
//   - Parent retry module no longer requires private regression access.
// - Summary:
//   - Proves conflict refresh revalidates due-slot authority before retry CAS.
// - Description:
//   - Missing or refreshed non-due state stops without invented catch-up.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Committed durability failure is terminal evidence, never retryable.
//

//! Regression coverage for bounded trigger-cadence claim conflict retries.

use std::collections::VecDeque;
use std::convert::Infallible;
use std::num::NonZeroU64;

use super::*;
use crate::blob_store::{
    NativeContinuationBlobConditionalPublication,
    NativeContinuationBlobConditionalPublicationResult,
};
use crate::cached_cycle::{
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryWindow,
};
use crate::executable_cache_limits_trigger_cadence_codec as codec;

type Decision = trigger::NativeExecutableCacheLimitsTriggerCadenceDecision;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DurabilityError {
    Failed,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum StopReason {
    ContentionObserved,
    PolicyLimit,
}

#[derive(Debug, Default)]
struct MemoryStore {
    bytes: Option<Vec<u8>>,
    compare_calls: usize,
    durability_calls: usize,
    fail_durability: bool,
    forced_conflicts: VecDeque<Option<Vec<u8>>>,
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

fn append_at(
    sequence: usize,
) -> Result<NativeContinuationCachedRetryTelemetryWindowAppend, String> {
    let capacity = NonZeroUsize::new(sequence.max(1))
        .ok_or_else(|| String::from("test capacity must be positive"))?;
    let mut window =
        NativeContinuationCachedRetryTelemetryWindow::new(capacity);
    let mut latest = None;
    for _ in 0..sequence {
        latest = Some(
            window
                .append(NativeContinuationCachedRetryTelemetry::default())
                .map_err(|error| error.to_string())?,
        );
    }
    latest.ok_or_else(|| String::from("test sequence must be positive"))
}

fn cursor(due_value: u64, interval_value: u64) -> Result<Cursor, String> {
    let due = NonZeroU64::new(due_value)
        .ok_or_else(|| String::from("test due sequence must be positive"))?;
    let interval = NonZeroU64::new(interval_value)
        .ok_or_else(|| String::from("test interval must be positive"))?;
    Ok(Cursor::new(due, interval))
}

fn encode(value: Cursor) -> Vec<u8> {
    codec::encode_native_executable_cache_limits_trigger_cadence(value)
}

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test bound must be positive"))
}

fn request(
    expected: Cursor,
    append: &NativeContinuationCachedRetryTelemetryWindowAppend,
    maximum_attempts: usize,
) -> Result<
    NativeExecutableCacheLimitsTriggerCadenceClaimRetryRequest<'_>,
    String,
> {
    Ok(
        NativeExecutableCacheLimitsTriggerCadenceClaimRetryRequest::new(
            expected,
            append,
            positive(32)?,
            positive(maximum_attempts)?,
        ),
    )
}

#[test]
fn retry_refreshes_conflict_then_commits_exact_due() -> Result<(), String> {
    let append = append_at(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let candidate = cursor(4, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        forced_conflicts: VecDeque::from([Some(encode(refreshed))]),
        ..MemoryStore::default()
    };
    let evidence = claim_cache_trigger_cadence_slot_durably_with_retries(
        &mut store,
        request(expected, &append, 3)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if evidence.attempts() == 2
        && matches!(
            evidence.outcome(),
            Claim::Attempted {
                publication: CursorCas::Durable {
                    current,
                    previous: Some(previous),
                    ..
                },
                ..
            } if *current == candidate && *previous == refreshed
        )
        && store.compare_calls == 2
        && store.durability_calls == 1
        && store.bytes == Some(encode(candidate))
    {
        Ok(())
    } else {
        Err(String::from("refreshed exact-due conflict did not commit"))
    }
}

#[test]
fn retry_refresh_consumed_slot_withholds_without_second_cas()
-> Result<(), String> {
    let append = append_at(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(3, 2)?;
    let due_sequence = NonZeroU64::new(3)
        .ok_or_else(|| String::from("test due sequence must be positive"))?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        forced_conflicts: VecDeque::from([Some(encode(refreshed))]),
        ..MemoryStore::default()
    };
    let evidence = claim_cache_trigger_cadence_slot_durably_with_retries(
        &mut store,
        request(expected, &append, 3)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if evidence.attempts() == 2
        && matches!(
            evidence.outcome(),
            Claim::Withheld {
                decision: Decision::Deferred {
                    observed_sequence: 1,
                    due_sequence: observed_due,
                },
            } if observed_due == &due_sequence
        )
        && store.compare_calls == 1
        && store.durability_calls == 0
        && store.bytes == Some(encode(refreshed))
    {
        Ok(())
    } else {
        Err(String::from("consumed conflict slot retried durable CAS"))
    }
}

#[test]
fn missing_conflict_state_is_terminal() -> Result<(), String> {
    let append = append_at(1)?;
    let expected = cursor(1, 2)?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        forced_conflicts: VecDeque::from([None]),
        ..MemoryStore::default()
    };
    let evidence = claim_cache_trigger_cadence_slot_durably_with_retries(
        &mut store,
        request(expected, &append, 3)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if evidence.attempts() == 1
        && matches!(evidence.outcome(), Claim::Attempted {
            publication: CursorCas::Conflict { current: None, .. },
            ..
        })
        && store.compare_calls == 1
        && store.durability_calls == 0
        && store.bytes.is_none()
    {
        Ok(())
    } else {
        Err(String::from(
            "missing conflict state invented retry cadence",
        ))
    }
}

#[test]
fn exhausted_attempt_budget_preserves_conflict() -> Result<(), String> {
    let append = append_at(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        forced_conflicts: VecDeque::from([Some(encode(refreshed))]),
        ..MemoryStore::default()
    };
    let evidence = claim_cache_trigger_cadence_slot_durably_with_retries(
        &mut store,
        request(expected, &append, 1)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if evidence.attempts() == 1
        && matches!(
            evidence.outcome(),
            Claim::Attempted {
                publication: CursorCas::Conflict {
                    current: Some(current),
                    ..
                },
                ..
            } if *current == refreshed
        )
        && store.compare_calls == 1
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("exhausted claim retry budget advanced"))
    }
}

#[test]
fn caller_stop_preserves_first_conflict() -> Result<(), String> {
    let append = append_at(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        forced_conflicts: VecDeque::from([Some(encode(refreshed))]),
        ..MemoryStore::default()
    };
    let mut seen = None;
    let evidence = claim_cache_trigger_cadence_slot_with_retry_control(
        &mut store,
        request(expected, &append, 3)?,
        |conflict| {
            seen = Some(conflict.completed_attempts());
            NativeContinuationRetryDirective::Stop
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if evidence.attempts() == 1
        && seen == Some(1)
        && matches!(evidence.outcome(), Claim::Attempted {
            publication: CursorCas::Conflict { .. },
            ..
        })
        && store.compare_calls == 1
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("caller stop did not preserve first conflict"))
    }
}

#[test]
fn committed_durability_failure_is_never_retried() -> Result<(), String> {
    let append = append_at(1)?;
    let expected = cursor(1, 2)?;
    let candidate = cursor(3, 2)?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        fail_durability: true,
        ..MemoryStore::default()
    };
    let evidence = claim_cache_trigger_cadence_slot_durably_with_retries(
        &mut store,
        request(expected, &append, 3)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if evidence.attempts() == 1
        && matches!(
            evidence.outcome(),
            Claim::Attempted {
                publication: CursorCas::Published {
                    current,
                    durability_error: DurabilityError::Failed,
                    ..
                },
                ..
            } if *current == candidate
        )
        && store.compare_calls == 1
        && store.durability_calls == 1
        && store.bytes == Some(encode(candidate))
    {
        Ok(())
    } else {
        Err(String::from("committed durability failure was retried"))
    }
}

#[test]
fn typed_stop_preserves_reason_and_conflict_attempt() -> Result<(), String> {
    let append = append_at(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        forced_conflicts: VecDeque::from([Some(encode(refreshed))]),
        ..MemoryStore::default()
    };
    let evidence = claim_cache_trigger_cadence_slot_with_retry_decision(
        &mut store,
        request(expected, &append, 3)?,
        |_conflict| {
            NativeContinuationRetryDecision::Stop(
                StopReason::ContentionObserved,
            )
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    let stop = evidence
        .stop()
        .ok_or_else(|| String::from("typed stop reason disappeared"))?;
    if evidence.attempts() == 1
        && stop.conflict().completed_attempts() == 1
        && stop.reason() == &StopReason::ContentionObserved
        && matches!(evidence.outcome(), Claim::Attempted {
            publication: CursorCas::Conflict { .. },
            ..
        })
        && store.compare_calls == 1
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("typed retry stop evidence drifted"))
    }
}

#[test]
fn typed_continue_then_stop_binds_later_conflict() -> Result<(), String> {
    let append = append_at(1)?;
    let expected = cursor(1, 2)?;
    let first = cursor(1, 3)?;
    let second = cursor(1, 4)?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        forced_conflicts: VecDeque::from([
            Some(encode(first)),
            Some(encode(second)),
        ]),
        ..MemoryStore::default()
    };
    let evidence = claim_cache_trigger_cadence_slot_with_retry_decision(
        &mut store,
        request(expected, &append, 3)?,
        |conflict| {
            if conflict.completed_attempts() == 1 {
                NativeContinuationRetryDecision::Continue
            } else {
                NativeContinuationRetryDecision::Stop(StopReason::PolicyLimit)
            }
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    let stop = evidence
        .stop()
        .ok_or_else(|| String::from("later typed stop reason disappeared"))?;
    if evidence.attempts() == 2
        && stop.conflict().completed_attempts() == 2
        && stop.reason() == &StopReason::PolicyLimit
        && store.compare_calls == 2
        && store.durability_calls == 0
        && store.bytes == Some(encode(second))
    {
        Ok(())
    } else {
        Err(String::from("later conflict stop evidence drifted"))
    }
}

#[test]
fn budget_exhaustion_does_not_invent_typed_stop() -> Result<(), String> {
    let append = append_at(1)?;
    let expected = cursor(1, 2)?;
    let refreshed = cursor(1, 3)?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        forced_conflicts: VecDeque::from([Some(encode(refreshed))]),
        ..MemoryStore::default()
    };
    let mut decisions = 0usize;
    let evidence = claim_cache_trigger_cadence_slot_with_retry_decision(
        &mut store,
        request(expected, &append, 1)?,
        |_conflict| {
            decisions = decisions.saturating_add(1);
            NativeContinuationRetryDecision::Stop(StopReason::PolicyLimit)
        },
    )
    .map_err(|error| format!("{error:?}"))?;
    if evidence.attempts() == 1
        && evidence.stop().is_none()
        && decisions == 0
        && store.compare_calls == 1
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("budget exhaustion invented typed stop"))
    }
}
