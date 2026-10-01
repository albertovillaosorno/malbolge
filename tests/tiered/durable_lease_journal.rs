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
//   - Root-tree regression coverage for durable executable lease journaling.
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
//   - Proves durable executable lease journaling behavior from the root test
//     tree.
// - Description:
//   - Loaded as a test-only child module to retain private-item access.
// - Usage:
//   - Selected by the parent module only when Rust test configuration is set.
// - Defaults:
//   - Production builds never compile this regression module.
//

//! Root-tree regression coverage for durable executable lease journaling.

use std::fs::{create_dir_all, remove_dir_all};
use std::io::ErrorKind;
use std::{env, process};

use super::*;
use crate::blob_store::{
    NativeContinuationBlobConditionalPublication,
    NativeContinuationBlobConditionalPublicationResult,
    NativeContinuationBlobConditionalRemoval,
    NativeContinuationBlobConditionalRemovalResult,
    NativeContinuationBlobRemoval, NativeContinuationBlobRemovalResult,
    NativeContinuationBlobStore, NativeContinuationConditionalBlobStore,
    NativeContinuationConditionalRemovableBlobStore,
    NativeContinuationDurableBlobStore, NativeContinuationRemovableBlobStore,
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
struct TransitionStore {
    bytes: Option<Vec<u8>>,
    durability_calls: usize,
    fail_durability: bool,
    race_bytes: Option<Vec<u8>>,
}

impl NativeContinuationBlobStore for TransitionStore {
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

impl NativeContinuationConditionalBlobStore for TransitionStore {
    fn compare_and_swap(
        &mut self,
        expected: Option<&[u8]>,
        replacement: &[u8],
        _maximum_bytes: NonZeroUsize,
    ) -> NativeContinuationBlobConditionalPublicationResult<Self::Error> {
        if let Some(race_bytes) = self.race_bytes.take() {
            self.bytes = Some(race_bytes);
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

impl NativeContinuationRemovableBlobStore for TransitionStore {
    fn remove(&mut self) -> NativeContinuationBlobRemovalResult<Self::Error> {
        if self.bytes.take().is_some() {
            Ok(NativeContinuationBlobRemoval::Removed)
        } else {
            Ok(NativeContinuationBlobRemoval::Missing)
        }
    }
}

impl NativeContinuationConditionalRemovableBlobStore for TransitionStore {
    fn compare_and_remove(
        &mut self,
        expected: Option<&[u8]>,
        _maximum_bytes: NonZeroUsize,
    ) -> NativeContinuationBlobConditionalRemovalResult<Self::Error> {
        if self.bytes.as_deref() != expected {
            return Ok(NativeContinuationBlobConditionalRemoval::Conflict {
                current: self.bytes.clone(),
            });
        }
        if self.bytes.take().is_some() {
            Ok(NativeContinuationBlobConditionalRemoval::Removed)
        } else {
            Ok(NativeContinuationBlobConditionalRemoval::Missing)
        }
    }
}

impl NativeContinuationDurableBlobStore for TransitionStore {
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

const fn owner(value: u8) -> NativeExecutableDurableLeaseOwnerId {
    NativeExecutableDurableLeaseOwnerId::new([value; OWNER_BYTES])
}

fn transition_request(
    owner: NativeExecutableDurableLeaseOwnerId,
    maximum_owners: usize,
) -> Result<NativeExecutableDurableLeaseTransitionRequest, String> {
    Ok(NativeExecutableDurableLeaseTransitionRequest::new(
        owner,
        decode_limits(maximum_owners)?,
        maximum_bytes()?,
    ))
}

#[test]
fn acquire_capacity_failure_preserves_durable_registry() -> TestResult {
    let bound = NonZeroUsize::new(1).ok_or("owner bound")?;
    let mut current = NativeExecutableDurableLeaseRegistry::new();
    let _inserted = current
        .acquire(owner(1), bound)
        .map_err(|error| format!("{error:?}"))?;
    let current_bytes = encode_executable_durable_lease_registry(&current)
        .map_err(|error| format!("{error:?}"))?;
    let mut store = TransitionStore {
        bytes: Some(current_bytes.clone()),
        ..TransitionStore::default()
    };
    let result = acquire_executable_durable_lease_once(
        &mut store,
        transition_request(owner(2), 1)?,
    );
    if matches!(
        result,
        Err(NativeExecutableDurableLeaseTransitionError::Capacity(error))
            if error.maximum_owners() == bound
                && error.observed_owners() == 2
    ) && store.bytes == Some(current_bytes)
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "capacity failure changed durable lease registry",
        ))
    }
}

#[test]
fn acquire_conflict_returns_current_without_retry() -> TestResult {
    let bound = NonZeroUsize::new(4).ok_or("owner bound")?;
    let mut first = NativeExecutableDurableLeaseRegistry::new();
    let _inserted = first
        .acquire(owner(1), bound)
        .map_err(|error| format!("{error:?}"))?;
    let mut raced = first.clone();
    let _inserted = raced
        .acquire(owner(2), bound)
        .map_err(|error| format!("{error:?}"))?;
    let first_bytes = encode_executable_durable_lease_registry(&first)
        .map_err(|error| format!("{error:?}"))?;
    let raced_bytes = encode_executable_durable_lease_registry(&raced)
        .map_err(|error| format!("{error:?}"))?;
    let mut store = TransitionStore {
        bytes: Some(first_bytes),
        race_bytes: Some(raced_bytes.clone()),
        ..TransitionStore::default()
    };
    let outcome = acquire_executable_durable_lease_once(
        &mut store,
        transition_request(owner(3), 4)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if outcome
        == (NativeExecutableDurableLeaseTransition::Conflict {
            current: Some(raced),
        })
        && store.bytes == Some(raced_bytes)
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("lease acquire conflict retried or drifted"))
    }
}

#[test]
fn acquire_post_commit_durability_failure_keeps_registry() -> TestResult {
    let mut store = TransitionStore {
        fail_durability: true,
        ..TransitionStore::default()
    };
    let request = transition_request(owner(4), 4)?;
    let outcome = acquire_executable_durable_lease_once(&mut store, request)
        .map_err(|error| format!("{error:?}"))?;
    let bytes = store
        .bytes
        .as_deref()
        .ok_or_else(|| String::from("committed lease journal missing"))?;
    let restored =
        decode_executable_durable_lease_registry(bytes, decode_limits(4)?)
            .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableDurableLeaseTransition::Published {
            bytes: 32,
            durability_error: TestDurabilityError::Failed,
            ref registry,
        } if registry == &restored && restored.contains(owner(4))
    ) && store.durability_calls == 1
    {
        Ok(())
    } else {
        Err(String::from(
            "post-commit durability failure lost lease registry",
        ))
    }
}

#[test]
fn file_owner_transitions_are_idempotent() -> TestResult {
    let directory = env::temp_dir().join(format!(
        "malbolge-durable-lease-transition-{}",
        process::id(),
    ));
    match remove_dir_all(&directory) {
        Ok(()) => {},
        Err(error) if error.kind() == ErrorKind::NotFound => {},
        Err(error) => {
            return Err(format!("test cleanup failed: {error}"));
        },
    }
    create_dir_all(&directory)
        .map_err(|error| format!("test create failed: {error}"))?;
    let mut store =
        NativeContinuationFileBlobStore::new(directory.join("leases.bin"));
    let request = transition_request(owner(7), 4)?;
    let acquired = acquire_executable_durable_lease_once(&mut store, request)
        .map_err(|error| format!("{error:?}"))?;
    let duplicate = acquire_executable_durable_lease_once(&mut store, request)
        .map_err(|error| format!("{error:?}"))?;
    let released = release_executable_durable_lease_once(&mut store, request)
        .map_err(|error| format!("{error:?}"))?;
    let duplicate_release =
        release_executable_durable_lease_once(&mut store, request)
            .map_err(|error| format!("{error:?}"))?;
    let restored = restore_executable_durable_lease_journal(
        &mut store,
        request.decode_limits,
        request.maximum_bytes,
    )
    .map_err(|error| format!("{error:?}"))?;
    drop(store);
    remove_dir_all(&directory)
        .map_err(|error| format!("test removal failed: {error}"))?;
    let empty = NativeExecutableDurableLeaseRegistry::new();
    if matches!(
        acquired,
        NativeExecutableDurableLeaseTransition::Durable {
            ref registry,
            ..
        } if registry.contains(owner(7))
    ) && matches!(
        duplicate,
        NativeExecutableDurableLeaseTransition::Unchanged {
            current: Some(ref registry),
        } if registry.contains(owner(7))
    ) && matches!(
        released,
        NativeExecutableDurableLeaseTransition::Durable {
            ref registry,
            ..
        } if registry.is_empty()
    ) && duplicate_release
        == (NativeExecutableDurableLeaseTransition::Unchanged {
            current: Some(empty.clone()),
        })
        && restored
            == (NativeExecutableDurableLeaseJournalLoad::Present {
                registry: empty,
            })
    {
        Ok(())
    } else {
        Err(String::from("one-shot lease transitions drifted"))
    }
}

#[test]
fn empty_removal_durability_failure_retains_absence() -> TestResult {
    let empty = NativeExecutableDurableLeaseRegistry::new();
    let empty_bytes = encode_executable_durable_lease_registry(&empty)
        .map_err(|error| format!("{error:?}"))?;
    let mut store = TransitionStore {
        bytes: Some(empty_bytes),
        fail_durability: true,
        ..TransitionStore::default()
    };
    let removal = remove_empty_executable_durable_lease_journal_durably(
        &mut store,
        decode_limits(4)?,
        maximum_bytes()?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if removal
        == (NativeExecutableDurableLeaseJournalRemoval::Removed {
            durability_error: TestDurabilityError::Failed,
        })
        && store.bytes.is_none()
        && store.durability_calls == 1
    {
        Ok(())
    } else {
        Err(String::from(
            "post-removal durability failure restored lease journal",
        ))
    }
}

#[test]
fn empty_file_journal_can_be_removed_durably() -> TestResult {
    let directory = env::temp_dir().join(format!(
        "malbolge-durable-lease-empty-remove-{}",
        process::id(),
    ));
    match remove_dir_all(&directory) {
        Ok(()) => {},
        Err(error) if error.kind() == ErrorKind::NotFound => {},
        Err(error) => {
            return Err(format!("test cleanup failed: {error}"));
        },
    }
    create_dir_all(&directory)
        .map_err(|error| format!("test create failed: {error}"))?;
    let mut store =
        NativeContinuationFileBlobStore::new(directory.join("leases.bin"));
    let request = transition_request(owner(8), 4)?;
    let _acquired = acquire_executable_durable_lease_once(&mut store, request)
        .map_err(|error| format!("{error:?}"))?;
    let _released = release_executable_durable_lease_once(&mut store, request)
        .map_err(|error| format!("{error:?}"))?;
    let removed = remove_empty_executable_durable_lease_journal_durably(
        &mut store,
        request.decode_limits,
        request.maximum_bytes,
    )
    .map_err(|error| format!("{error:?}"))?;
    let restored = restore_executable_durable_lease_journal(
        &mut store,
        request.decode_limits,
        request.maximum_bytes,
    )
    .map_err(|error| format!("{error:?}"))?;
    drop(store);
    remove_dir_all(&directory)
        .map_err(|error| format!("test removal failed: {error}"))?;
    if removed == NativeExecutableDurableLeaseJournalRemoval::Durable
        && restored == NativeExecutableDurableLeaseJournalLoad::Missing
    {
        Ok(())
    } else {
        Err(String::from("empty lease journal removal drifted"))
    }
}

#[test]
fn nonempty_file_journal_blocks_empty_removal() -> TestResult {
    let directory = env::temp_dir().join(format!(
        "malbolge-durable-lease-nonempty-remove-{}",
        process::id(),
    ));
    match remove_dir_all(&directory) {
        Ok(()) => {},
        Err(error) if error.kind() == ErrorKind::NotFound => {},
        Err(error) => {
            return Err(format!("test cleanup failed: {error}"));
        },
    }
    create_dir_all(&directory)
        .map_err(|error| format!("test create failed: {error}"))?;
    let mut store =
        NativeContinuationFileBlobStore::new(directory.join("leases.bin"));
    let request = transition_request(owner(8), 4)?;
    let acquired = acquire_executable_durable_lease_once(&mut store, request)
        .map_err(|error| format!("{error:?}"))?;
    let expected = match acquired {
        NativeExecutableDurableLeaseTransition::Durable {
            registry, ..
        }
        | NativeExecutableDurableLeaseTransition::Published {
            registry, ..
        } => registry,
        _ => {
            return Err(String::from("test lease acquisition did not commit"));
        },
    };
    let removal = remove_empty_executable_durable_lease_journal_durably(
        &mut store,
        request.decode_limits,
        request.maximum_bytes,
    )
    .map_err(|error| format!("{error:?}"))?;
    let restored = restore_executable_durable_lease_journal(
        &mut store,
        request.decode_limits,
        request.maximum_bytes,
    )
    .map_err(|error| format!("{error:?}"))?;
    drop(store);
    remove_dir_all(&directory)
        .map_err(|error| format!("test removal failed: {error}"))?;
    if removal
        == (NativeExecutableDurableLeaseJournalRemoval::Conflict {
            current: Some(expected.clone()),
        })
        && restored
            == (NativeExecutableDurableLeaseJournalLoad::Present {
                registry: expected,
            })
    {
        Ok(())
    } else {
        Err(String::from("nonempty lease journal was removed"))
    }
}

#[test]
fn release_missing_journal_is_unchanged() -> TestResult {
    let mut store = TransitionStore::default();
    let outcome = release_executable_durable_lease_once(
        &mut store,
        transition_request(owner(9), 4)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if outcome
        == (NativeExecutableDurableLeaseTransition::Unchanged { current: None })
        && store.bytes.is_none()
        && store.durability_calls == 0
    {
        Ok(())
    } else {
        Err(String::from("missing lease release mutated storage"))
    }
}

#[test]
fn canonical_codec_round_trip_is_sorted() -> TestResult {
    let mut registry = NativeExecutableDurableLeaseRegistry::new();
    let _first = registry
        .acquire(owner(9), NonZeroUsize::new(4).ok_or("owner bound")?)
        .map_err(|error| format!("{error:?}"))?;
    let _second = registry
        .acquire(owner(2), NonZeroUsize::new(4).ok_or("owner bound")?)
        .map_err(|error| format!("{error:?}"))?;
    let bytes = encode_executable_durable_lease_registry(&registry)
        .map_err(|error| format!("{error:?}"))?;
    let decoded =
        decode_executable_durable_lease_registry(&bytes, decode_limits(4)?)
            .map_err(|error| format!("{error:?}"))?;
    if decoded == registry
        && decoded.owners() == [owner(2), owner(9)].as_slice()
    {
        Ok(())
    } else {
        Err(String::from("lease registry canonical round trip drifted"))
    }
}

#[test]
fn decoder_rejects_noncanonical_owner_order() -> TestResult {
    let mut registry = NativeExecutableDurableLeaseRegistry::new();
    let bound = NonZeroUsize::new(4).ok_or("owner bound")?;
    let _first = registry
        .acquire(owner(2), bound)
        .map_err(|error| format!("{error:?}"))?;
    let _second = registry
        .acquire(owner(9), bound)
        .map_err(|error| format!("{error:?}"))?;
    let mut bytes = encode_executable_durable_lease_registry(&registry)
        .map_err(|error| format!("{error:?}"))?;
    bytes[HEADER_BYTES..HEADER_BYTES + OWNER_BYTES]
        .copy_from_slice(&owner(9).bytes());
    bytes[HEADER_BYTES + OWNER_BYTES..].copy_from_slice(&owner(2).bytes());
    let result =
        decode_executable_durable_lease_registry(&bytes, decode_limits(4)?);
    if result == Err(NativeExecutableDurableLeaseRegistryCodecError::OwnerOrder)
    {
        Ok(())
    } else {
        Err(String::from("noncanonical lease owners were admitted"))
    }
}

#[test]
fn file_journal_coordinates_acquire_release_and_conflict() -> TestResult {
    let directory = env::temp_dir()
        .join(format!("malbolge-durable-lease-journal-{}", process::id(),));
    match remove_dir_all(&directory) {
        Ok(()) => {},
        Err(error) if error.kind() == ErrorKind::NotFound => {},
        Err(error) => {
            return Err(format!("test cleanup failed: {error}"));
        },
    }
    create_dir_all(&directory)
        .map_err(|error| format!("test create failed: {error}"))?;
    let destination = directory.join("leases.bin");
    let mut first_store =
        NativeContinuationFileBlobStore::new(destination.clone());
    let mut second_store = NativeContinuationFileBlobStore::new(destination);
    let limits = decode_limits(8)?;
    let bytes = maximum_bytes()?;
    let empty = NativeExecutableDurableLeaseRegistry::new();
    let mut one = empty.clone();
    let _acquired = one
        .acquire(owner(1), limits.maximum_owners())
        .map_err(|error| format!("{error:?}"))?;
    let initialized = compare_and_swap_executable_durable_lease_journal(
        &mut first_store,
        NativeExecutableDurableLeaseJournalCasRequest::new(
            None, &one, limits, bytes,
        ),
    )
    .map_err(|error| format!("{error:?}"))?;
    let mut two = one.clone();
    let _acquired = two
        .acquire(owner(2), limits.maximum_owners())
        .map_err(|error| format!("{error:?}"))?;
    let expanded = compare_and_swap_executable_durable_lease_journal(
        &mut second_store,
        NativeExecutableDurableLeaseJournalCasRequest::new(
            Some(&one),
            &two,
            limits,
            bytes,
        ),
    )
    .map_err(|error| format!("{error:?}"))?;
    let stale = compare_and_swap_executable_durable_lease_journal(
        &mut first_store,
        NativeExecutableDurableLeaseJournalCasRequest::new(
            Some(&one),
            &empty,
            limits,
            bytes,
        ),
    )
    .map_err(|error| format!("{error:?}"))?;
    let restored = restore_executable_durable_lease_journal(
        &mut second_store,
        limits,
        bytes,
    )
    .map_err(|error| format!("{error:?}"))?;
    drop(first_store);
    drop(second_store);
    remove_dir_all(&directory)
        .map_err(|error| format!("test removal failed: {error}"))?;
    if initialized
        == (NativeExecutableDurableLeaseJournalCas::Durable { bytes: 32 })
        && expanded
            == (NativeExecutableDurableLeaseJournalCas::Durable { bytes: 48 })
        && matches!(
            stale,
            NativeExecutableDurableLeaseJournalCas::Conflict {
                current: Some(ref current),
            } if current == &two
        )
        && restored
            == (NativeExecutableDurableLeaseJournalLoad::Present {
                registry: two,
            })
    {
        Ok(())
    } else {
        Err(String::from("durable lease journal coordination drifted"))
    }
}

#[test]
fn missing_file_journal_is_explicit() -> TestResult {
    let directory = env::temp_dir()
        .join(format!("malbolge-durable-lease-missing-{}", process::id(),));
    match remove_dir_all(&directory) {
        Ok(()) => {},
        Err(error) if error.kind() == ErrorKind::NotFound => {},
        Err(error) => {
            return Err(format!("test cleanup failed: {error}"));
        },
    }
    create_dir_all(&directory)
        .map_err(|error| format!("test create failed: {error}"))?;
    let mut store =
        NativeContinuationFileBlobStore::new(directory.join("leases.bin"));
    let load = restore_executable_durable_lease_journal(
        &mut store,
        decode_limits(2)?,
        maximum_bytes()?,
    )
    .map_err(|error| format!("{error:?}"))?;
    drop(store);
    remove_dir_all(&directory)
        .map_err(|error| format!("test removal failed: {error}"))?;
    if load == NativeExecutableDurableLeaseJournalLoad::Missing {
        Ok(())
    } else {
        Err(String::from("missing lease journal invented owners"))
    }
}

#[test]
fn owner_decode_limit_fails_closed() -> TestResult {
    let mut registry = NativeExecutableDurableLeaseRegistry::new();
    let bound = NonZeroUsize::new(2).ok_or("owner bound")?;
    let _first = registry
        .acquire(owner(1), bound)
        .map_err(|error| format!("{error:?}"))?;
    let _second = registry
        .acquire(owner(2), bound)
        .map_err(|error| format!("{error:?}"))?;
    let bytes = encode_executable_durable_lease_registry(&registry)
        .map_err(|error| format!("{error:?}"))?;
    let maximum_owners = NonZeroUsize::new(1).ok_or("decode bound")?;
    let result = decode_executable_durable_lease_registry(
        &bytes,
        NativeExecutableDurableLeaseRegistryDecodeLimits::new(maximum_owners),
    );
    if result
        == Err(NativeExecutableDurableLeaseRegistryCodecError::OwnerLimit {
            maximum_owners,
            observed_owners: 2,
        })
    {
        Ok(())
    } else {
        Err(String::from("lease journal owner bound was bypassed"))
    }
}

#[test]
fn owner_capacity_fails_before_registry_mutation() -> TestResult {
    let mut registry = NativeExecutableDurableLeaseRegistry::new();
    let maximum = NonZeroUsize::new(1).ok_or("owner bound")?;
    let _acquired = registry
        .acquire(owner(1), maximum)
        .map_err(|error| format!("{error:?}"))?;
    let error = registry
        .acquire(owner(2), maximum)
        .expect_err("second owner must exceed bound");
    if error.maximum_owners() == maximum
        && error.observed_owners() == 2
        && registry.owners() == [owner(1)].as_slice()
    {
        Ok(())
    } else {
        Err(String::from("lease owner bound mutated registry"))
    }
}

#[test]
fn replacement_owner_limit_fails_before_publication() -> TestResult {
    let directory = env::temp_dir()
        .join(format!("malbolge-durable-lease-bound-{}", process::id(),));
    match remove_dir_all(&directory) {
        Ok(()) => {},
        Err(error) if error.kind() == ErrorKind::NotFound => {},
        Err(error) => {
            return Err(format!("test cleanup failed: {error}"));
        },
    }
    create_dir_all(&directory)
        .map_err(|error| format!("test create failed: {error}"))?;
    let mut store =
        NativeContinuationFileBlobStore::new(directory.join("leases.bin"));
    let construction_bound = NonZeroUsize::new(2).ok_or("owner bound")?;
    let mut replacement = NativeExecutableDurableLeaseRegistry::new();
    let _first = replacement
        .acquire(owner(1), construction_bound)
        .map_err(|error| format!("{error:?}"))?;
    let _second = replacement
        .acquire(owner(2), construction_bound)
        .map_err(|error| format!("{error:?}"))?;
    let maximum_owners = NonZeroUsize::new(1).ok_or("CAS owner bound")?;
    let decode_limits =
        NativeExecutableDurableLeaseRegistryDecodeLimits::new(maximum_owners);
    let result = compare_and_swap_executable_durable_lease_journal(
        &mut store,
        NativeExecutableDurableLeaseJournalCasRequest::new(
            None,
            &replacement,
            decode_limits,
            maximum_bytes()?,
        ),
    );
    let load = restore_executable_durable_lease_journal(
        &mut store,
        decode_limits,
        maximum_bytes()?,
    )
    .map_err(|error| format!("{error:?}"))?;
    drop(store);
    remove_dir_all(&directory)
        .map_err(|error| format!("test removal failed: {error}"))?;
    if result
        == Err(NativeExecutableDurableLeaseJournalError::Codec(
            NativeExecutableDurableLeaseRegistryCodecError::OwnerLimit {
                maximum_owners,
                observed_owners: 2,
            },
        ))
        && load == NativeExecutableDurableLeaseJournalLoad::Missing
    {
        Ok(())
    } else {
        Err(String::from(
            "over-limit durable lease replacement reached storage",
        ))
    }
}

#[test]
fn release_to_explicit_empty_journal_is_durable() -> TestResult {
    let directory = env::temp_dir()
        .join(format!("malbolge-durable-lease-release-{}", process::id(),));
    match remove_dir_all(&directory) {
        Ok(()) => {},
        Err(error) if error.kind() == ErrorKind::NotFound => {},
        Err(error) => {
            return Err(format!("test cleanup failed: {error}"));
        },
    }
    create_dir_all(&directory)
        .map_err(|error| format!("test create failed: {error}"))?;
    let mut store =
        NativeContinuationFileBlobStore::new(directory.join("leases.bin"));
    let limits = decode_limits(2)?;
    let bytes = maximum_bytes()?;
    let mut held = NativeExecutableDurableLeaseRegistry::new();
    let _acquired = held
        .acquire(owner(7), limits.maximum_owners())
        .map_err(|error| format!("{error:?}"))?;
    let _initialized = compare_and_swap_executable_durable_lease_journal(
        &mut store,
        NativeExecutableDurableLeaseJournalCasRequest::new(
            None, &held, limits, bytes,
        ),
    )
    .map_err(|error| format!("{error:?}"))?;
    let mut released = held.clone();
    if !released.release(owner(7)) {
        return Err(String::from("test owner was not released"));
    }
    let publication = compare_and_swap_executable_durable_lease_journal(
        &mut store,
        NativeExecutableDurableLeaseJournalCasRequest::new(
            Some(&held),
            &released,
            limits,
            bytes,
        ),
    )
    .map_err(|error| format!("{error:?}"))?;
    let restored =
        restore_executable_durable_lease_journal(&mut store, limits, bytes)
            .map_err(|error| format!("{error:?}"))?;
    drop(store);
    remove_dir_all(&directory)
        .map_err(|error| format!("test removal failed: {error}"))?;
    if publication
        == (NativeExecutableDurableLeaseJournalCas::Durable { bytes: 16 })
        && restored
            == (NativeExecutableDurableLeaseJournalLoad::Present {
                registry: released,
            })
    {
        Ok(())
    } else {
        Err(String::from("empty durable lease journal drifted"))
    }
}
