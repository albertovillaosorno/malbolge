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
//   - Regression coverage for exact durable cache-trigger slot claims.
// - Must-Not:
//   - Activate policy, retry conflicts, spawn work, or define product cadence.
// - Allows:
//   - Inputs: deterministic append evidence, cursor state, and in-memory CAS.
//   - Outputs: exact withheld, conflict, and committed claim evidence.
//   - Side effects: test-local window/store mutation only.
// - Split-When:
//   - Activation coupling or conflict retry gains independent regression scope.
// - Merge-When:
//   - Parent claim module no longer requires private regression access.
// - Summary:
//   - Proves only exact due transitions can reach durable cursor CAS.
// - Description:
//   - Stale conflicts never mutate the caller-owned expected cursor.
// - Usage:
//   - Compiled only under Rust test configuration.
// - Defaults:
//   - Deferred and missed append evidence performs zero store work.
//

//! Regression coverage for transition-validating cache-trigger slot claims.

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

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum DurabilityError {
    Failed,
}

type StoreError = Infallible;

#[derive(Debug, Default)]
struct MemoryStore {
    bytes: Option<Vec<u8>>,
    compare_calls: usize,
    durability_calls: usize,
    fail_durability: bool,
}

impl BlobStore for MemoryStore {
    type Error = StoreError;

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

fn append_at(
    sequence: usize,
) -> Result<NativeContinuationCachedRetryTelemetryWindowAppend, String> {
    let capacity = NonZeroUsize::new(sequence.max(1))
        .ok_or_else(|| String::from("test window capacity must be positive"))?;
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
    latest.ok_or_else(|| String::from("test append sequence must be positive"))
}

fn positive_u64(value: u64) -> Result<NonZeroU64, String> {
    NonZeroU64::new(value)
        .ok_or_else(|| String::from("test value must be positive"))
}

fn cursor(due_value: u64, interval_value: u64) -> Result<Cursor, String> {
    let due = positive_u64(due_value)?;
    let interval = positive_u64(interval_value)?;
    Ok(Cursor::new(due, interval))
}

fn encode(value: Cursor) -> Vec<u8> {
    codec::encode_native_executable_cache_limits_trigger_cadence(value)
}

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test byte bound must be positive"))
}

#[test]
fn exact_due_claim_commits_validated_candidate() -> Result<(), String> {
    let expected = cursor(2, 3)?;
    let candidate = cursor(5, 3)?;
    let append = append_at(2)?;
    let observed_due = positive_u64(2)?;
    let next_due = positive_u64(5)?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        ..MemoryStore::default()
    };
    let claim = claim_cache_trigger_cadence_slot_durably(
        &mut store,
        expected,
        &append,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if claim.is_committed()
        && matches!(
            claim,
            NativeExecutableCacheLimitsTriggerCadenceClaim::Attempted {
                decision: Decision::Due {
                    observed_sequence,
                    next_due_sequence: Some(next),
                },
                publication: CursorCas::Durable {
                    bytes: 32,
                    current,
                    previous: Some(previous),
                },
            } if observed_sequence == observed_due
                && next == next_due
                && current == candidate
                && previous == expected
        )
        && store.bytes == Some(encode(candidate))
        && store.compare_calls == 1
        && store.durability_calls == 1
    {
        Ok(())
    } else {
        Err(String::from(
            "exact due claim did not commit one transition",
        ))
    }
}

#[test]
fn early_publication_withholds_without_store_work() -> Result<(), String> {
    let expected = cursor(2, 3)?;
    let append = append_at(1)?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        ..MemoryStore::default()
    };
    let claim = claim_cache_trigger_cadence_slot_durably(
        &mut store,
        expected,
        &append,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if !claim.is_committed()
        && matches!(
            claim,
            NativeExecutableCacheLimitsTriggerCadenceClaim::Withheld {
                decision: Decision::Deferred { .. },
            }
        )
        && store.compare_calls == 0
        && store.durability_calls == 0
        && store.bytes == Some(encode(expected))
    {
        Ok(())
    } else {
        Err(String::from("early append reached cursor CAS"))
    }
}

#[test]
fn missed_due_withholds_without_catch_up() -> Result<(), String> {
    let expected = cursor(2, 3)?;
    let append = append_at(3)?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        ..MemoryStore::default()
    };
    let claim = claim_cache_trigger_cadence_slot_durably(
        &mut store,
        expected,
        &append,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if !claim.is_committed()
        && matches!(
            claim,
            NativeExecutableCacheLimitsTriggerCadenceClaim::Withheld {
                decision: Decision::Missed { .. },
            }
        )
        && store.compare_calls == 0
        && store.durability_calls == 0
        && store.bytes == Some(encode(expected))
    {
        Ok(())
    } else {
        Err(String::from("missed due slot was caught up implicitly"))
    }
}

#[test]
fn stale_due_claim_returns_conflict_without_commit() -> Result<(), String> {
    let expected = cursor(2, 3)?;
    let current = cursor(8, 3)?;
    let candidate = cursor(5, 3)?;
    let append = append_at(2)?;
    let current_bytes = encode(current);
    let mut store = MemoryStore {
        bytes: Some(current_bytes.clone()),
        ..MemoryStore::default()
    };
    let claim = claim_cache_trigger_cadence_slot_durably(
        &mut store,
        expected,
        &append,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if !claim.is_committed()
        && matches!(
            claim,
            NativeExecutableCacheLimitsTriggerCadenceClaim::Attempted {
                decision: Decision::Due { .. },
                publication: CursorCas::Conflict {
                    candidate: observed_candidate,
                    current: Some(observed_current),
                    expected: Some(observed_expected),
                },
            } if observed_candidate == candidate
                && observed_current == current
                && observed_expected == expected
        )
        && store.bytes == Some(current_bytes)
        && store.compare_calls == 1
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("stale due claim acquired cursor ownership"))
    }
}

#[test]
fn durability_failure_keeps_due_claim_committed() -> Result<(), String> {
    let expected = cursor(2, 3)?;
    let candidate = cursor(5, 3)?;
    let append = append_at(2)?;
    let mut store = MemoryStore {
        bytes: Some(encode(expected)),
        fail_durability: true,
        ..MemoryStore::default()
    };
    let claim = claim_cache_trigger_cadence_slot_durably(
        &mut store,
        expected,
        &append,
        positive(32)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if claim.is_committed()
        && matches!(
            claim,
            NativeExecutableCacheLimitsTriggerCadenceClaim::Attempted {
                publication: CursorCas::Published {
                    bytes: 32,
                    current,
                    durability_error: DurabilityError::Failed,
                    previous: Some(previous),
                },
                ..
            } if current == candidate && previous == expected
        )
        && store.bytes == Some(encode(candidate))
        && store.compare_calls == 1
        && store.durability_calls == 1
    {
        Ok(())
    } else {
        Err(String::from("durability failure lost committed due claim"))
    }
}
