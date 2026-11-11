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
//   - Exact due-slot transition validation plus conditional durable cursor
//     claim.
// - Must-Not:
//   - Spawn work, retry conflicts, activate cache policy, choose storage paths,
//     or invent catch-up for deferred/missed/exhausted cadence evidence.
// - Allows:
//   - Inputs: immutable expected cursor, one successful window append, positive
//     byte bound, and one conditional durable blob store.
//   - Outputs: withheld cadence evidence or exact attempted durable slot claim.
//   - Side effects: conditional durable cursor publication only for exact due.
// - Split-When:
//   - Conflict retry, activation coupling, or unattended lifecycle gains
//     independent authority.
// - Merge-When:
//   - One product trigger owner subsumes due-slot claim and policy activation.
// - Summary:
//   - Claims only one exact due publication by validated cursor advancement.
// - Description:
//   - Candidate advancement occurs on a copy before expected-to-candidate CAS.
// - Usage:
//   - Supply the last observed durable cursor plus the exact published append.
// - Defaults:
//   - Non-due evidence performs no durable mutation.
//

//! Transition-validating durable claim for one exact cache-trigger cadence
//! slot.

use std::num::NonZeroUsize;

use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::cached_cycle::NativeContinuationCachedRetryTelemetryWindowAppend;
use crate::{
    executable_cache_limits_trigger_cadence as trigger,
    executable_cache_limits_trigger_cadence_cas as cursor_cas,
};

type Cursor = trigger::NativeExecutableCacheLimitsTriggerCadence;
type Decision = trigger::NativeExecutableCacheLimitsTriggerCadenceDecision;
type CursorCas<DurabilityError> =
    cursor_cas::NativeExecutableCacheLimitsTriggerCadenceCas<DurabilityError>;

/// Result of validating and conditionally claiming one cadence slot.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeExecutableCacheLimitsTriggerCadenceClaim<DurabilityError> {
    /// Exact due transition was validated and conditional publication
    /// attempted.
    Attempted {
        /// Exact due evidence that generated the candidate cursor.
        decision: Decision,
        /// Durable commit, committed durability failure, or stale conflict.
        publication: CursorCas<DurabilityError>,
    },
    /// Publication was not exactly due; no store operation ran.
    Withheld {
        /// Exact deferred, missed, or exhausted cadence evidence.
        decision: Decision,
        /// Exact cursor revalidated without durable mutation.
        expected: Cursor,
    },
}

/// Claim result specialized to one conditional durable store.
pub type NativeExecutableCacheLimitsTriggerCadenceClaimStoreResult<Store> =
    Result<
        NativeExecutableCacheLimitsTriggerCadenceClaim<
            <Store as DurableBlobStore>::DurabilityError,
        >,
        cursor_cas::NativeExecutableCacheLimitsTriggerCadenceCasError<
            <Store as BlobStore>::Error,
        >,
    >;

impl<DurabilityError>
    NativeExecutableCacheLimitsTriggerCadenceClaim<DurabilityError>
{
    /// Reports whether this call committed the validated candidate cursor.
    #[must_use]
    pub const fn is_committed(&self) -> bool {
        matches!(self, Self::Attempted {
            publication: CursorCas::Durable { .. }
                | CursorCas::Published { .. },
            ..
        })
    }

    /// Returns the exact cursor safe to use as the next expected state.
    #[must_use]
    pub const fn next_expected_cursor(&self) -> Option<Cursor> {
        match self {
            Self::Attempted {
                publication: CursorCas::Conflict { current, .. },
                ..
            } => *current,
            Self::Attempted {
                publication:
                    CursorCas::Durable { current, .. }
                    | CursorCas::Published { current, .. },
                ..
            } => Some(*current),
            Self::Withheld { expected, .. } => Some(*expected),
        }
    }
}

/// Validates one exact due-slot transition and conditionally claims it durably.
///
/// The caller-owned `expected` cursor is never mutated. A copy advances only
/// when the supplied append sequence is exactly due, then canonical CAS
/// compares durable state against `expected` before publishing the validated
/// candidate.
///
/// # Errors
///
/// Returns conditional-store, byte-limit, or conflict-codec failure from the
/// underlying cursor CAS after exact due validation.
pub fn claim_cache_trigger_cadence_slot_durably<Store>(
    store: &mut Store,
    expected: Cursor,
    append: &NativeContinuationCachedRetryTelemetryWindowAppend,
    maximum_bytes: NonZeroUsize,
) -> NativeExecutableCacheLimitsTriggerCadenceClaimStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let mut candidate = expected;
    let decision = candidate.observe(append);
    if !matches!(decision, Decision::Due { .. }) {
        return Ok(NativeExecutableCacheLimitsTriggerCadenceClaim::Withheld {
            decision,
            expected,
        });
    }
    let publication =
        cursor_cas::compare_and_swap_cache_trigger_cadence_durably(
            store,
            Some(expected),
            candidate,
            maximum_bytes,
        )?;
    Ok(NativeExecutableCacheLimitsTriggerCadenceClaim::Attempted {
        decision,
        publication,
    })
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/cache_trigger_claim.rs"]
mod tests;
