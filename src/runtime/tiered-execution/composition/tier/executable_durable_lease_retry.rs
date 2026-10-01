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
mod tests {
    use std::collections::VecDeque;
    use std::fs::{create_dir_all, remove_dir_all};
    use std::io::ErrorKind;
    use std::{env, process};

    use super::*;
    use crate::blob_store::{
        NativeContinuationBlobConditionalPublication,
        NativeContinuationBlobConditionalPublicationResult,
        NativeContinuationBlobStore, NativeContinuationConditionalBlobStore,
        NativeContinuationDurableBlobStore,
    };
    use crate::executable_durable_lease_journal::{
        NativeExecutableDurableLeaseOwnerId,
        NativeExecutableDurableLeaseRegistry,
        NativeExecutableDurableLeaseRegistryDecodeLimits,
        encode_executable_durable_lease_registry,
    };
    use crate::file_blob_store::NativeContinuationFileBlobStore;

    type TestResult = Result<(), String>;

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum TestDurabilityError {
        Failed,
    }

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum TestStoreError {
        Failed,
    }

    #[derive(Debug, Default)]
    struct RacingStore {
        bytes: Option<Vec<u8>>,
        compare_calls: usize,
        durability_calls: usize,
        fail_durability: bool,
        races: VecDeque<Vec<u8>>,
    }

    impl NativeContinuationBlobStore for RacingStore {
        type Error = TestStoreError;

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

    impl NativeContinuationConditionalBlobStore for RacingStore {
        fn compare_and_swap(
            &mut self,
            expected: Option<&[u8]>,
            replacement: &[u8],
            _maximum_bytes: NonZeroUsize,
        ) -> NativeContinuationBlobConditionalPublicationResult<Self::Error>
        {
            self.compare_calls = self.compare_calls.saturating_add(1);
            if let Some(race) = self.races.pop_front() {
                self.bytes = Some(race);
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

    impl NativeContinuationDurableBlobStore for RacingStore {
        type DurabilityError = TestDurabilityError;

        fn confirm_durability(&mut self) -> Result<(), Self::DurabilityError> {
            self.durability_calls = self.durability_calls.saturating_add(1);
            if self.fail_durability {
                Err(TestDurabilityError::Failed)
            } else {
                Ok(())
            }
        }
    }

    fn decode_limits(
        maximum: usize,
    ) -> Result<NativeExecutableDurableLeaseRegistryDecodeLimits, String> {
        NonZeroUsize::new(maximum)
            .map(NativeExecutableDurableLeaseRegistryDecodeLimits::new)
            .ok_or_else(|| String::from("test owner limit missing"))
    }

    fn maximum_bytes() -> Result<NonZeroUsize, String> {
        NonZeroUsize::new(4096)
            .ok_or_else(|| String::from("test byte limit missing"))
    }

    fn maximum_attempts(value: usize) -> Result<NonZeroUsize, String> {
        NonZeroUsize::new(value)
            .ok_or_else(|| String::from("test attempt budget missing"))
    }

    const fn owner(value: u8) -> NativeExecutableDurableLeaseOwnerId {
        NativeExecutableDurableLeaseOwnerId::new([value; 16])
    }

    fn registry(
        owners: &[u8],
    ) -> Result<NativeExecutableDurableLeaseRegistry, String> {
        let mut registry = NativeExecutableDurableLeaseRegistry::new();
        let bound = NonZeroUsize::new(16)
            .ok_or_else(|| String::from("test owner bound missing"))?;
        for value in owners {
            let _inserted = registry
                .acquire(owner(*value), bound)
                .map_err(|error| format!("{error:?}"))?;
        }
        Ok(registry)
    }

    fn registry_bytes(owners: &[u8]) -> Result<Vec<u8>, String> {
        encode_executable_durable_lease_registry(&registry(owners)?)
            .map_err(|error| format!("{error:?}"))
    }

    fn retry_request(
        owner: NativeExecutableDurableLeaseOwnerId,
        attempts: usize,
    ) -> Result<NativeExecutableDurableLeaseRetryRequest, String> {
        let transition = NativeExecutableDurableLeaseTransitionRequest::new(
            owner,
            decode_limits(16)?,
            maximum_bytes()?,
        );
        Ok(NativeExecutableDurableLeaseRetryRequest::new(
            transition,
            maximum_attempts(attempts)?,
        ))
    }

    #[test]
    fn acquire_retries_conflict_to_durable() -> TestResult {
        let mut store = RacingStore {
            races: VecDeque::from([registry_bytes(&[9])?]),
            ..RacingStore::default()
        };
        let evidence = acquire_executable_durable_lease_with_retries(
            &mut store,
            retry_request(owner(1), 3)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        let expected = registry(&[1, 9])?;
        if evidence.attempts() == 2
            && matches!(
                evidence.outcome(),
                NativeExecutableDurableLeaseTransition::Durable {
                    registry,
                    ..
                } if registry == &expected
            )
            && store.compare_calls == 2
            && store.durability_calls == 1
        {
            Ok(())
        } else {
            Err(String::from("acquire retry evidence drifted"))
        }
    }

    #[test]
    fn acquire_retry_budget_preserves_latest_conflict() -> TestResult {
        let mut store = RacingStore {
            races: VecDeque::from([
                registry_bytes(&[8])?,
                registry_bytes(&[9])?,
            ]),
            ..RacingStore::default()
        };
        let evidence = acquire_executable_durable_lease_with_retries(
            &mut store,
            retry_request(owner(1), 2)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        let expected = registry(&[9])?;
        if evidence.attempts() == 2
            && matches!(
                evidence.outcome(),
                NativeExecutableDurableLeaseTransition::Conflict {
                    current: Some(current),
                } if current == &expected
            )
            && store.compare_calls == 2
            && store.durability_calls == 0
        {
            Ok(())
        } else {
            Err(String::from("retry exhaustion evidence drifted"))
        }
    }

    #[test]
    fn capacity_error_is_not_retried() -> TestResult {
        let mut store = RacingStore {
            bytes: Some(registry_bytes(&[9])?),
            ..RacingStore::default()
        };
        let transition = NativeExecutableDurableLeaseTransitionRequest::new(
            owner(1),
            decode_limits(1)?,
            maximum_bytes()?,
        );
        let request = NativeExecutableDurableLeaseRetryRequest::new(
            transition,
            maximum_attempts(3)?,
        );
        let result =
            acquire_executable_durable_lease_with_retries(&mut store, request);
        if matches!(
            result,
            Err(NativeExecutableDurableLeaseTransitionError::Capacity(_))
        ) && store.compare_calls == 0
            && store.durability_calls == 0
        {
            Ok(())
        } else {
            Err(String::from("capacity error consumed retry work"))
        }
    }

    #[test]
    fn caller_stop_preserves_first_conflict() -> TestResult {
        let mut store = RacingStore {
            races: VecDeque::from([registry_bytes(&[9])?]),
            ..RacingStore::default()
        };
        let mut observed = Vec::new();
        let evidence = acquire_executable_durable_lease_with_retry_control(
            &mut store,
            retry_request(owner(1), 3)?,
            |conflict| {
                observed.push(conflict.completed_attempts());
                NativeContinuationRetryDirective::Stop
            },
        )
        .map_err(|error| format!("{error:?}"))?;
        if evidence.attempts() == 1
            && matches!(
                evidence.outcome(),
                NativeExecutableDurableLeaseTransition::Conflict { .. }
            )
            && observed == vec![1]
            && store.compare_calls == 1
            && store.durability_calls == 0
        {
            Ok(())
        } else {
            Err(String::from("caller stop retry evidence drifted"))
        }
    }

    #[test]
    fn file_store_retry_wrapper_round_trip() -> TestResult {
        let directory = env::temp_dir()
            .join(format!("malbolge-durable-lease-retry-{}", process::id(),));
        match remove_dir_all(&directory) {
            Ok(()) => {},
            Err(error) if error.kind() == ErrorKind::NotFound => {},
            Err(error) => {
                return Err(format!("test directory cleanup failed: {error}"));
            },
        }
        create_dir_all(&directory).map_err(|error| {
            format!("test directory create failed: {error}")
        })?;
        let destination = directory.join("lease.bin");
        let mut store = NativeContinuationFileBlobStore::new(destination);
        let request = retry_request(owner(1), 3)?;
        let acquired =
            acquire_executable_durable_lease_with_retries(&mut store, request)
                .map_err(|error| format!("{error:?}"))?;
        let unchanged =
            acquire_executable_durable_lease_with_retries(&mut store, request)
                .map_err(|error| format!("{error:?}"))?;
        let released =
            release_executable_durable_lease_with_retries(&mut store, request)
                .map_err(|error| format!("{error:?}"))?;
        drop(store);
        remove_dir_all(&directory).map_err(|error| {
            format!("test directory removal failed: {error}")
        })?;
        if acquired.attempts() == 1
            && matches!(
                acquired.outcome(),
                NativeExecutableDurableLeaseTransition::Durable { .. }
            )
            && unchanged.attempts() == 1
            && matches!(
                unchanged.outcome(),
                NativeExecutableDurableLeaseTransition::Unchanged { .. }
            )
            && released.attempts() == 1
            && matches!(
                released.outcome(),
                NativeExecutableDurableLeaseTransition::Durable {
                    registry,
                    ..
                } if registry.is_empty()
            )
        {
            Ok(())
        } else {
            Err(String::from("file lease retry wrapper round trip drifted"))
        }
    }

    #[test]
    fn published_acquire_is_terminal() -> TestResult {
        let mut store = RacingStore {
            fail_durability: true,
            ..RacingStore::default()
        };
        let evidence = acquire_executable_durable_lease_with_retries(
            &mut store,
            retry_request(owner(1), 3)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        if evidence.attempts() == 1
            && matches!(
                evidence.outcome(),
                NativeExecutableDurableLeaseTransition::Published {
                    durability_error: TestDurabilityError::Failed,
                    ..
                }
            )
            && store.compare_calls == 1
            && store.durability_calls == 1
        {
            Ok(())
        } else {
            Err(String::from("published transition was retried"))
        }
    }

    #[test]
    fn release_retries_conflict_to_durable() -> TestResult {
        let mut store = RacingStore {
            bytes: Some(registry_bytes(&[1, 9])?),
            races: VecDeque::from([registry_bytes(&[1, 8, 9])?]),
            ..RacingStore::default()
        };
        let evidence = release_executable_durable_lease_with_retries(
            &mut store,
            retry_request(owner(1), 3)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        let expected = registry(&[8, 9])?;
        if evidence.attempts() == 2
            && matches!(
                evidence.outcome(),
                NativeExecutableDurableLeaseTransition::Durable {
                    registry,
                    ..
                } if registry == &expected
            )
            && store.compare_calls == 2
            && store.durability_calls == 1
        {
            Ok(())
        } else {
            Err(String::from("release retry evidence drifted"))
        }
    }

    #[test]
    fn unchanged_acquire_skips_cas_and_retry() -> TestResult {
        let mut store = RacingStore {
            bytes: Some(registry_bytes(&[1])?),
            ..RacingStore::default()
        };
        let evidence = acquire_executable_durable_lease_with_retries(
            &mut store,
            retry_request(owner(1), 3)?,
        )
        .map_err(|error| format!("{error:?}"))?;
        if evidence.attempts() == 1
            && matches!(
                evidence.outcome(),
                NativeExecutableDurableLeaseTransition::Unchanged {
                    current: Some(_),
                }
            )
            && store.compare_calls == 0
            && store.durability_calls == 0
        {
            Ok(())
        } else {
            Err(String::from("unchanged acquire performed retry work"))
        }
    }
}
