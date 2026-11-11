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
//   - Root-tree regression coverage for durable executable lease retry.
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
//   - Proves durable executable lease retry behavior from the root test tree.
// - Description:
//   - Loaded as a test-only child module to retain private-item access.
// - Usage:
//   - Selected by the parent module only when Rust test configuration is set.
// - Defaults:
//   - Production builds never compile this regression module.
//

//! Root-tree regression coverage for durable executable lease retry.

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
    NativeExecutableDurableLeaseOwnerId, NativeExecutableDurableLeaseRegistry,
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
    ) -> NativeContinuationBlobConditionalPublicationResult<Self::Error> {
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
        races: VecDeque::from([registry_bytes(&[8])?, registry_bytes(&[9])?]),
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
    create_dir_all(&directory)
        .map_err(|error| format!("test directory create failed: {error}"))?;
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
    remove_dir_all(&directory)
        .map_err(|error| format!("test directory removal failed: {error}"))?;
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
