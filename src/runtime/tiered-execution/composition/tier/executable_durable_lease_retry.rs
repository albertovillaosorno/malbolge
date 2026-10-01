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
//   - Bounded synchronous retry of exact durable executable lease conflicts.
// - Must-Not:
//   - Sleep, select backoff, expire owners, infer artifact identity, choose
//     storage locations, or retry non-conflict failures.
// - Allows:
//   - Inputs: one one-shot lease transition, positive attempt budget, and
//     optional caller direction after retryable conflicts.
//   - Outputs: exact terminal lease transition plus consumed attempt count.
//   - Side effects: repeated delegated restore/CAS attempts only after
//     conflict.
// - Split-When:
//   - Asynchronous scheduling or temporal lease expiry gains authority.
// - Merge-When:
//   - One distributed lease recovery owner subsumes synchronous conflict retry.
// - Summary:
//   - Retries durable lease owner conflicts under caller-selected bounds.
// - Description:
//   - Durable, published, unchanged, and error outcomes terminate immediately.
// - Usage:
//   - Wrap one-shot acquire or release when synchronous conflict retry is safe.
// - Defaults:
//   - Convenience entry points retry every conflict until budget exhaustion.
//
//! Bounded synchronous retry for durable executable lease owner transitions.

use std::num::NonZeroUsize;

use crate::blob_store::{
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
};
use crate::executable_durable_lease_journal::{
    NativeExecutableDurableLeaseTransition,
    NativeExecutableDurableLeaseTransitionError,
    NativeExecutableDurableLeaseTransitionRequest,
    NativeExecutableDurableLeaseTransitionStoreResult,
    acquire_executable_durable_lease_once,
    release_executable_durable_lease_once,
};
use crate::retry_control::{
    NativeContinuationRetryAttemptCursor, NativeContinuationRetryConflict,
    NativeContinuationRetryDirective, NativeContinuationRetryEvidence,
};

/// Positive retry budget bound to one exact durable lease transition request.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeExecutableDurableLeaseRetryRequest {
    maximum_attempts: NonZeroUsize,
    transition: NativeExecutableDurableLeaseTransitionRequest,
}

/// Terminal durable lease transition plus exact attempts consumed.
pub type NativeExecutableDurableLeaseRetry<DurabilityError> =
    NativeContinuationRetryEvidence<
        NativeExecutableDurableLeaseTransition<DurabilityError>,
    >;

/// Retry result specialized to one conditional durable blob store.
pub type NativeExecutableDurableLeaseRetryStoreResult<Store> = Result<
    NativeExecutableDurableLeaseRetry<
        <Store as DurableBlobStore>::DurabilityError,
    >,
    NativeExecutableDurableLeaseTransitionError<<Store as BlobStore>::Error>,
>;

impl NativeExecutableDurableLeaseRetryRequest {
    /// Returns the positive total attempt budget.
    #[must_use]
    pub const fn maximum_attempts(self) -> NonZeroUsize {
        self.maximum_attempts
    }

    /// Binds one exact transition to a positive total attempt budget.
    #[must_use]
    pub const fn new(
        transition: NativeExecutableDurableLeaseTransitionRequest,
        maximum_attempts: NonZeroUsize,
    ) -> Self {
        Self {
            maximum_attempts,
            transition,
        }
    }

    /// Returns the exact one-shot transition repeated after conflicts.
    #[must_use]
    pub const fn transition(
        self,
    ) -> NativeExecutableDurableLeaseTransitionRequest {
        self.transition
    }
}

fn transition_with_retry_control<Store, Attempt, Control>(
    store: &mut Store,
    request: NativeExecutableDurableLeaseRetryRequest,
    mut attempt: Attempt,
    mut control: Control,
) -> NativeExecutableDurableLeaseRetryStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Attempt: FnMut(
        &mut Store,
        NativeExecutableDurableLeaseTransitionRequest,
    )
        -> NativeExecutableDurableLeaseTransitionStoreResult<Store>,
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
{
    let mut attempts = NativeContinuationRetryAttemptCursor::after_first(
        request.maximum_attempts,
    );
    loop {
        let outcome = attempt(store, request.transition)?;
        match outcome {
            conflict @ NativeExecutableDurableLeaseTransition::Conflict {
                ..
            } if attempts.can_retry() => {
                if control(attempts.conflict())
                    == NativeContinuationRetryDirective::Stop
                    || !attempts.advance()
                {
                    return Ok(NativeContinuationRetryEvidence::new(
                        attempts.completed_attempts(),
                        conflict,
                    ));
                }
            },
            terminal @ (NativeExecutableDurableLeaseTransition::Conflict {
                ..
            }
            | NativeExecutableDurableLeaseTransition::Durable {
                ..
            }
            | NativeExecutableDurableLeaseTransition::Published {
                ..
            }
            | NativeExecutableDurableLeaseTransition::Unchanged {
                ..
            }) => {
                return Ok(NativeContinuationRetryEvidence::new(
                    attempts.completed_attempts(),
                    terminal,
                ));
            },
        }
    }
}

/// Acquires one durable lease owner and retries only exact CAS conflicts.
///
/// # Errors
///
/// Returns one-shot restore/CAS, codec, store, or capacity failure. Errors are
/// never retried.
pub fn acquire_executable_durable_lease_with_retries<Store>(
    store: &mut Store,
    request: NativeExecutableDurableLeaseRetryRequest,
) -> NativeExecutableDurableLeaseRetryStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    acquire_executable_durable_lease_with_retry_control(
        store,
        request,
        |_conflict| NativeContinuationRetryDirective::Continue,
    )
}

/// Acquires one durable lease owner with caller direction after each conflict.
///
/// The callback runs only while another attempt remains in the positive budget.
///
/// # Errors
///
/// Returns one-shot restore/CAS, codec, store, or capacity failure. Errors are
/// never retried.
pub fn acquire_executable_durable_lease_with_retry_control<Store, Control>(
    store: &mut Store,
    request: NativeExecutableDurableLeaseRetryRequest,
    control: Control,
) -> NativeExecutableDurableLeaseRetryStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
{
    transition_with_retry_control(
        store,
        request,
        acquire_executable_durable_lease_once::<Store>,
        control,
    )
}

/// Releases one durable lease owner and retries only exact CAS conflicts.
///
/// # Errors
///
/// Returns one-shot restore/CAS, codec, or store failure. Errors are never
/// retried.
pub fn release_executable_durable_lease_with_retries<Store>(
    store: &mut Store,
    request: NativeExecutableDurableLeaseRetryRequest,
) -> NativeExecutableDurableLeaseRetryStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    release_executable_durable_lease_with_retry_control(
        store,
        request,
        |_conflict| NativeContinuationRetryDirective::Continue,
    )
}

/// Releases one durable lease owner with caller direction after each conflict.
///
/// The callback runs only while another attempt remains in the positive budget.
///
/// # Errors
///
/// Returns one-shot restore/CAS, codec, or store failure. Errors are never
/// retried.
pub fn release_executable_durable_lease_with_retry_control<Store, Control>(
    store: &mut Store,
    request: NativeExecutableDurableLeaseRetryRequest,
    control: Control,
) -> NativeExecutableDurableLeaseRetryStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
    Control: FnMut(
        NativeContinuationRetryConflict,
    ) -> NativeContinuationRetryDirective,
{
    transition_with_retry_control(
        store,
        request,
        release_executable_durable_lease_once::<Store>,
        control,
    )
}

#[cfg(test)]
#[path = "../../../../../tests/tiered/durable_lease_retry.rs"]
mod tests;
