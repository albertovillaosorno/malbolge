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
//   - Pure caller-owned sequence cadence for cache-policy trigger eligibility.
// - Must-Not:
//   - Read clocks, sleep, spawn work, invoke cache policy, mutate
//     cache/storage, infer retry behavior, or hide missed trigger evidence.
// - Allows:
//   - Inputs: one exact published telemetry-window append and an explicit next
//     due sequence plus positive sequence interval.
//   - Outputs: deferred, due, missed, or exhausted trigger-cadence evidence.
//   - Side effects: advances only this process-local cursor on an exact due
//     sequence.
// - Split-When:
//   - Retry-after-activation-failure, durable cursor persistence, or background
//     lifecycle gains independent authority.
// - Merge-When:
//   - One product coordinator owns cadence, observed activation, and lifecycle.
// - Summary:
//   - Gates cache-policy trigger eligibility by exact publication sequence.
// - Description:
//   - Earlier publications defer; skipped due sequences fail closed as missed.
// - Usage:
//   - Observe only successful telemetry-window append evidence before deciding
//     whether caller-owned cache-policy orchestration may run.
// - Defaults:
//   - No clock or implicit first trigger exists; callers choose the first due
//     sequence explicitly.
//

//! Exact publication-sequence cadence for caller-driven cache-policy triggers.

use std::cmp::Ordering;
use std::num::NonZeroU64;

use crate::cached_cycle::NativeContinuationCachedRetryTelemetryWindowAppend;

/// Caller-owned process-local cursor for exact cache-policy trigger cadence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableCacheLimitsTriggerCadence {
    interval: NonZeroU64,
    next_due_sequence: Option<NonZeroU64>,
}

/// Exact eligibility result for one published telemetry-window append.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsTriggerCadenceDecision {
    /// Publication precedes the next due sequence; no cursor state changed.
    Deferred {
        /// Exact sequence observed from the successful append.
        observed_sequence: u64,
        /// Exact next sequence eligible to trigger policy.
        due_sequence: NonZeroU64,
    },
    /// Exact due sequence was observed and the cadence slot was consumed.
    Due {
        /// Exact sequence that consumed this cadence slot.
        observed_sequence: NonZeroU64,
        /// Next due sequence, or `None` when interval advancement exhausted.
        next_due_sequence: Option<NonZeroU64>,
    },
    /// No future due sequence can be represented after prior exact consumption.
    Exhausted {
        /// Exact publication sequence observed after cadence exhaustion.
        observed_sequence: u64,
    },
    /// Caller skipped past the exact due sequence; no cursor state changed.
    Missed {
        /// Exact publication sequence supplied by the caller.
        observed_sequence: u64,
        /// Exact earlier cadence sequence that remains unresolved.
        due_sequence: NonZeroU64,
    },
}

impl NativeExecutableCacheLimitsTriggerCadence {
    fn consume_due(
        &mut self,
        due_sequence: NonZeroU64,
    ) -> NativeExecutableCacheLimitsTriggerCadenceDecision {
        let next_due_sequence = due_sequence
            .get()
            .checked_add(self.interval.get())
            .and_then(NonZeroU64::new);
        self.next_due_sequence = next_due_sequence;
        NativeExecutableCacheLimitsTriggerCadenceDecision::Due {
            observed_sequence: due_sequence,
            next_due_sequence,
        }
    }

    /// Returns the positive sequence interval between eligible publications.
    #[must_use]
    pub const fn interval(self) -> NonZeroU64 {
        self.interval
    }

    /// Constructs one explicit sequence cadence and first due publication.
    #[must_use]
    pub const fn new(
        first_due_sequence: NonZeroU64,
        interval: NonZeroU64,
    ) -> Self {
        Self {
            interval,
            next_due_sequence: Some(first_due_sequence),
        }
    }

    /// Returns the next exact eligible sequence, or `None` after exhaustion.
    #[must_use]
    pub const fn next_due_sequence(self) -> Option<NonZeroU64> {
        self.next_due_sequence
    }

    /// Observes one successful window append and advances only on exact due.
    #[must_use]
    pub fn observe(
        &mut self,
        append: &NativeContinuationCachedRetryTelemetryWindowAppend,
    ) -> NativeExecutableCacheLimitsTriggerCadenceDecision {
        let observed_sequence = append.observation().sequence();
        let Some(due_sequence) = self.next_due_sequence else {
            return
                NativeExecutableCacheLimitsTriggerCadenceDecision::Exhausted {
                    observed_sequence,
                };
        };
        match observed_sequence.cmp(&due_sequence.get()) {
            Ordering::Equal => self.consume_due(due_sequence),
            Ordering::Greater => {
                NativeExecutableCacheLimitsTriggerCadenceDecision::Missed {
                    observed_sequence,
                    due_sequence,
                }
            },
            Ordering::Less => {
                NativeExecutableCacheLimitsTriggerCadenceDecision::Deferred {
                    observed_sequence,
                    due_sequence,
                }
            },
        }
    }
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_trigger_cadence.rs"]
mod tests;
