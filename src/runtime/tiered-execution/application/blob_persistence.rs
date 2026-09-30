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
//   - Explicit bounded persistence use cases for one opaque byte blob.
// - Must-Not:
//   - Choose storage locations, interpret application bytes, select policy, or
//     coordinate multiple blobs.
// - Allows:
//   - Inputs: immutable admitted bytes, positive byte limit, and blob store.
//   - Outputs: missing/present owned bytes or exact publication evidence.
//   - Side effects: one delegated bounded load or atomic replacement per call.
// - Split-When:
//   - Multi-blob transactions or migration gains application authority.
// - Merge-When:
//   - Another application service owns the exact bounded blob use case.
// - Summary:
//   - Coordinates byte bounds with replaceable durable blob storage.
// - Description:
//   - Size is checked before publication and again after every adapter load.
// - Usage:
//   - Called by typed composition after canonical encoding.
// - Defaults:
//   - Missing durable state is explicit and never invents empty bytes.
//

//! Explicit bounded persistence orchestration for one opaque byte blob.

use std::num::NonZeroUsize;

use store_port::{
    NativeContinuationBlobConditionalRemoval as BlobConditionalRemoval,
    NativeContinuationBlobRemoval as BlobRemoval,
    NativeContinuationBlobStore as BlobStore,
    NativeContinuationConditionalBlobStore as ConditionalBlobStore,
    NativeContinuationConditionalRemovableBlobStore as ConditionalRemoveStore,
    NativeContinuationDurableBlobStore as DurableBlobStore,
    NativeContinuationRemovableBlobStore as RemovableBlobStore,
};

use crate::blob_store as store_port;

type BlobConditionalPublication =
    store_port::NativeContinuationBlobConditionalPublication;
type BlobConditionalPersistence = NativeContinuationBlobConditionalPersistence;

/// Outcome of conditional removal plus explicit durability confirmation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobConditionalDurableRemoval<DurabilityError> {
    /// Expected bytes differed; no removal or durability check occurred.
    Conflict {
        /// Exact bounded current publication observed by the outbound store.
        current: Option<Vec<u8>>,
    },
    /// Removal committed and durability confirmation completed.
    Durable,
    /// Expected absence matched; no removal or durability check was required.
    Missing,
    /// Removal committed, but durability confirmation failed afterward.
    Removed {
        /// Exact post-removal durability failure.
        durability_error: DurabilityError,
    },
}

/// Outcome of one admitted optimistic-concurrency blob removal.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobConditionalRemoval {
    /// Expected bytes differed and no removal occurred.
    Conflict {
        /// Exact bounded current publication observed by the outbound store.
        current: Option<Vec<u8>>,
    },
    /// Expected absence matched and no publication required removal.
    Missing,
    /// Expected bytes matched and the publication was removed.
    Removed,
}

/// Outcome of conditional publication plus explicit durability confirmation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobConditionalDurablePersistence<DurabilityError> {
    /// Expected bytes differed; no replacement or durability check occurred.
    Conflict {
        /// Exact bounded current publication observed by the outbound store.
        current: Option<Vec<u8>>,
    },
    /// Conditional publication and durability confirmation both completed.
    Durable {
        /// Exact committed byte count.
        write: NativeContinuationBlobPersistenceWrite,
    },
    /// Conditional publication committed, then durability confirmation failed.
    Published {
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact committed byte count.
        write: NativeContinuationBlobPersistenceWrite,
    },
}

/// Outcome of one admitted optimistic-concurrency blob publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobConditionalPersistence {
    /// Expected bytes differed; no replacement occurred.
    Conflict {
        /// Exact bounded current publication observed by the outbound store.
        current: Option<Vec<u8>>,
    },
    /// Expected bytes matched and replacement committed.
    Published {
        /// Exact committed byte count.
        write: NativeContinuationBlobPersistenceWrite,
    },
}

/// Outcome after publication plus explicit durability confirmation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobDurablePersistence<DurabilityError> {
    /// Publication and the adapter's durability confirmation both completed.
    Durable {
        /// Exact committed byte count.
        write: NativeContinuationBlobPersistenceWrite,
    },
    /// Publication committed, but durability confirmation failed afterward.
    Published {
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Exact committed byte count.
        write: NativeContinuationBlobPersistenceWrite,
    },
}

/// Why one explicit blob persistence use case failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobPersistenceError<StoreError> {
    /// Admitted or adapter-returned bytes exceed the caller's positive bound.
    ByteLimit {
        /// Positive caller-configured byte limit.
        maximum_bytes: NonZeroUsize,
        /// Exact supplied or returned byte count.
        observed_bytes: usize,
    },
    /// The selected outbound store failed after application admission.
    Store(StoreError),
}

/// Outcome of one explicit blob removal.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobPersistenceRemoval {
    /// No publication existed when removal authority was held.
    Missing,
    /// One existing publication was removed.
    Removed,
}

/// Outcome after removal plus explicit durability confirmation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobDurableRemoval<DurabilityError> {
    /// Removal committed and directory/storage durability was confirmed.
    Durable,
    /// No publication existed; no durability confirmation was required.
    Missing,
    /// Removal committed, but durability confirmation failed afterward.
    Removed {
        /// Exact post-removal durability failure.
        durability_error: DurabilityError,
    },
}

/// Result of one bounded blob load.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum NativeContinuationBlobPersistenceLoad {
    /// No durable blob currently exists at the adapter-configured location.
    Missing,
    /// One bounded durable blob was loaded without interpreting its bytes.
    Present {
        /// Exact bytes returned by the outbound adapter.
        bytes: Vec<u8>,
    },
}

/// Result of one persistence use case with exact application failure evidence.
pub type NativeContinuationBlobPersistenceResult<Value, StoreError> =
    Result<Value, NativeContinuationBlobPersistenceError<StoreError>>;

/// Conditional durable removal result specialized to one outbound store type.
pub type NativeContinuationBlobConditionalDurableRemovalStoreResult<Store> =
    Result<
        NativeContinuationBlobConditionalDurableRemoval<
            <Store as DurableBlobStore>::DurabilityError,
        >,
        NativeContinuationBlobPersistenceError<<Store as BlobStore>::Error>,
    >;

/// Result of conditional publication plus optional durability confirmation.
pub type NativeContinuationBlobConditionalDurablePersistenceResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeContinuationBlobConditionalDurablePersistence<DurabilityError>,
    NativeContinuationBlobPersistenceError<StoreError>,
>;

/// Conditional durable result specialized to one outbound store type.
pub type NativeContinuationBlobConditionalDurableStoreResult<Store> =
    NativeContinuationBlobConditionalDurablePersistenceResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

/// Durable removal result specialized to one outbound store type.
pub type NativeContinuationBlobDurableRemovalStoreResult<Store> = Result<
    NativeContinuationBlobDurableRemoval<
        <Store as DurableBlobStore>::DurabilityError,
    >,
    NativeContinuationBlobPersistenceError<<Store as BlobStore>::Error>,
>;

/// Result of publication plus optional durability confirmation.
pub type NativeContinuationBlobDurablePersistenceResult<
    StoreError,
    DurabilityError,
> = Result<
    NativeContinuationBlobDurablePersistence<DurabilityError>,
    NativeContinuationBlobPersistenceError<StoreError>,
>;

/// Durable publication result specialized to one outbound store type.
pub type NativeContinuationBlobDurableStoreResult<Store> =
    NativeContinuationBlobDurablePersistenceResult<
        <Store as BlobStore>::Error,
        <Store as DurableBlobStore>::DurabilityError,
    >;

/// Publication evidence from one successful blob replacement.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationBlobPersistenceWrite {
    bytes: usize,
}

impl<DurabilityError>
    NativeContinuationBlobConditionalDurableRemoval<DurabilityError>
{
    /// Returns exact bounded current bytes when conditional removal conflicted.
    #[must_use]
    pub fn conflict(&self) -> Option<&[u8]> {
        match self {
            Self::Conflict { current } => current.as_deref(),
            Self::Durable | Self::Missing | Self::Removed { .. } => None,
        }
    }

    /// Returns post-removal durability failure when confirmation failed.
    #[must_use]
    pub const fn durability_error(&self) -> Option<&DurabilityError> {
        match self {
            Self::Removed { durability_error } => Some(durability_error),
            Self::Conflict { .. } | Self::Durable | Self::Missing => None,
        }
    }

    /// Reports whether one publication was actually removed.
    #[must_use]
    pub const fn is_removed(&self) -> bool {
        matches!(self, Self::Durable | Self::Removed { .. })
    }
}

impl<DurabilityError>
    NativeContinuationBlobConditionalDurablePersistence<DurabilityError>
{
    /// Returns committed byte count, or `None` when comparison conflicted.
    #[must_use]
    pub const fn bytes(&self) -> Option<usize> {
        match self {
            Self::Conflict { .. } => None,
            Self::Durable { write } | Self::Published { write, .. } => {
                Some(write.bytes())
            },
        }
    }

    /// Returns the exact bounded conflict publication, when comparison failed.
    #[must_use]
    pub fn conflict(&self) -> Option<&[u8]> {
        match self {
            Self::Conflict { current } => current.as_deref(),
            Self::Durable { .. } | Self::Published { .. } => None,
        }
    }

    /// Returns post-publication durability failure when confirmation failed.
    #[must_use]
    pub const fn durability_error(&self) -> Option<&DurabilityError> {
        match self {
            Self::Published { durability_error, .. } => Some(durability_error),
            Self::Conflict { .. } | Self::Durable { .. } => None,
        }
    }

    /// Reports whether conditional publication committed durably.
    #[must_use]
    pub const fn is_durable(&self) -> bool {
        matches!(self, Self::Durable { .. })
    }
}

impl<DurabilityError>
    NativeContinuationBlobDurablePersistence<DurabilityError>
{
    /// Returns the exact committed byte count in either durability state.
    #[must_use]
    pub const fn bytes(&self) -> usize {
        match self {
            Self::Durable { write } | Self::Published { write, .. } => {
                write.bytes()
            },
        }
    }

    /// Returns post-publication durability failure when confirmation failed.
    #[must_use]
    pub const fn durability_error(&self) -> Option<&DurabilityError> {
        match self {
            Self::Durable { .. } => None,
            Self::Published { durability_error, .. } => Some(durability_error),
        }
    }

    /// Reports whether publication durability was explicitly confirmed.
    #[must_use]
    pub const fn is_durable(&self) -> bool {
        matches!(self, Self::Durable { .. })
    }
}

impl<DurabilityError> NativeContinuationBlobDurableRemoval<DurabilityError> {
    /// Returns post-removal durability failure when confirmation failed.
    #[must_use]
    pub const fn durability_error(&self) -> Option<&DurabilityError> {
        match self {
            Self::Removed { durability_error } => Some(durability_error),
            Self::Durable | Self::Missing => None,
        }
    }

    /// Reports whether one publication was actually removed.
    #[must_use]
    pub const fn is_removed(&self) -> bool {
        matches!(self, Self::Durable | Self::Removed { .. })
    }
}

impl NativeContinuationBlobPersistenceWrite {
    /// Returns the exact admitted byte count passed to the outbound store.
    #[must_use]
    pub const fn bytes(self) -> usize {
        self.bytes
    }
}

/// Conditionally removes one blob and confirms committed absence durability.
///
/// Conflict and matched absence are non-mutating and skip durability
/// confirmation. Once removal commits, later durability failure is retained as
/// committed absence evidence rather than reported as rollback.
///
/// # Errors
///
/// Returns byte-limit or outbound coordination/removal failure before absence
/// commits.
pub fn compare_and_remove_blob_durably<Store>(
    store: &mut Store,
    expected: Option<&[u8]>,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobConditionalDurableRemovalStoreResult<Store>
where
    Store: ConditionalRemoveStore + DurableBlobStore,
{
    match compare_and_remove_blob(store, expected, maximum_bytes)? {
        NativeContinuationBlobConditionalRemoval::Conflict { current } => {
            Ok(NativeContinuationBlobConditionalDurableRemoval::Conflict {
                current,
            })
        },
        NativeContinuationBlobConditionalRemoval::Missing => {
            Ok(NativeContinuationBlobConditionalDurableRemoval::Missing)
        },
        NativeContinuationBlobConditionalRemoval::Removed => {
            match store.confirm_durability() {
                Ok(()) => {
                    Ok(NativeContinuationBlobConditionalDurableRemoval::Durable)
                },
                Err(durability_error) => Ok(
                    NativeContinuationBlobConditionalDurableRemoval::Removed {
                        durability_error,
                    },
                ),
            }
        },
    }
}

/// Conditionally removes one blob under an explicit positive byte bound.
///
/// # Errors
///
/// Returns byte-limit or outbound coordination/removal failure. Conflict is
/// successful evidence and never mutates the current publication.
pub fn compare_and_remove_blob<Store>(
    store: &mut Store,
    expected: Option<&[u8]>,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobPersistenceResult<
    NativeContinuationBlobConditionalRemoval,
    Store::Error,
>
where
    Store: ConditionalRemoveStore,
{
    if let Some(expected_bytes) = expected {
        admit_byte_limit(expected_bytes.len(), maximum_bytes)?;
    }
    let outcome = store
        .compare_and_remove(expected, maximum_bytes)
        .map_err(NativeContinuationBlobPersistenceError::Store)?;
    match outcome {
        BlobConditionalRemoval::Conflict { current } => {
            if let Some(current_bytes) = &current {
                admit_byte_limit(current_bytes.len(), maximum_bytes)?;
            }
            Ok(NativeContinuationBlobConditionalRemoval::Conflict { current })
        },
        BlobConditionalRemoval::Missing => {
            Ok(NativeContinuationBlobConditionalRemoval::Missing)
        },
        BlobConditionalRemoval::Removed => {
            Ok(NativeContinuationBlobConditionalRemoval::Removed)
        },
    }
}

/// Conditionally persists one blob and confirms durability after commit.
///
/// # Errors
///
/// Returns only byte-limit or store failure before publication. Conflict is
/// non-mutating evidence; post-publication durability failure remains
/// committed.
pub fn compare_and_swap_blob_durably<Store>(
    store: &mut Store,
    expected: Option<&[u8]>,
    replacement: &[u8],
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobConditionalDurableStoreResult<Store>
where
    Store: ConditionalBlobStore + DurableBlobStore,
{
    let write = match compare_and_swap_blob(
        store,
        expected,
        replacement,
        maximum_bytes,
    )? {
        BlobConditionalPersistence::Conflict { current } => {
            return Ok(
                NativeContinuationBlobConditionalDurablePersistence::Conflict {
                    current,
                },
            );
        },
        NativeContinuationBlobConditionalPersistence::Published { write } => {
            write
        },
    };
    match store.confirm_durability() {
        Ok(()) => Ok(
            NativeContinuationBlobConditionalDurablePersistence::Durable {
                write,
            },
        ),
        Err(durability_error) => Ok(
            NativeContinuationBlobConditionalDurablePersistence::Published {
                durability_error,
                write,
            },
        ),
    }
}

/// Conditionally persists one blob under an explicit positive byte bound.
///
/// # Errors
///
/// Returns byte-limit or outbound coordination/publication failure. Conflict is
/// successful evidence and never mutates the current publication.
pub fn compare_and_swap_blob<Store>(
    store: &mut Store,
    expected: Option<&[u8]>,
    replacement: &[u8],
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobPersistenceResult<
    NativeContinuationBlobConditionalPersistence,
    Store::Error,
>
where
    Store: ConditionalBlobStore,
{
    if let Some(expected_bytes) = expected {
        admit_byte_limit(expected_bytes.len(), maximum_bytes)?;
    }
    admit_byte_limit(replacement.len(), maximum_bytes)?;
    let outcome = store
        .compare_and_swap(expected, replacement, maximum_bytes)
        .map_err(NativeContinuationBlobPersistenceError::Store)?;
    match outcome {
        store_port::NativeContinuationBlobConditionalPublication::Published => {
            Ok(NativeContinuationBlobConditionalPersistence::Published {
                write: NativeContinuationBlobPersistenceWrite {
                    bytes: replacement.len(),
                },
            })
        },
        BlobConditionalPublication::Conflict { current } => {
            if let Some(current_bytes) = &current {
                admit_byte_limit(current_bytes.len(), maximum_bytes)?;
            }
            Ok(NativeContinuationBlobConditionalPersistence::Conflict {
                current,
            })
        },
    }
}

/// Persists one blob and then explicitly confirms publication durability.
///
/// # Errors
///
/// Returns only prepublication byte-limit or store failures. A durability
/// confirmation failure is returned as committed `Published` evidence.
pub fn persist_blob_durably<Store>(
    store: &mut Store,
    bytes: &[u8],
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobDurableStoreResult<Store>
where
    Store: DurableBlobStore,
{
    let write = persist_blob(store, bytes, maximum_bytes)?;
    match store.confirm_durability() {
        Ok(()) => {
            Ok(NativeContinuationBlobDurablePersistence::Durable { write })
        },
        Err(durability_error) => {
            Ok(NativeContinuationBlobDurablePersistence::Published {
                durability_error,
                write,
            })
        },
    }
}

/// Persists one admitted blob under an explicit positive byte bound.
///
/// # Errors
///
/// Returns byte-limit or outbound-store failure before claiming publication.
pub fn persist_blob<Store>(
    store: &mut Store,
    bytes: &[u8],
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobPersistenceResult<
    NativeContinuationBlobPersistenceWrite,
    Store::Error,
>
where
    Store: BlobStore,
{
    admit_byte_limit(bytes.len(), maximum_bytes)?;
    store
        .replace(bytes)
        .map_err(NativeContinuationBlobPersistenceError::Store)?;
    Ok(NativeContinuationBlobPersistenceWrite { bytes: bytes.len() })
}

/// Removes one configured blob and then confirms committed absence durability.
///
/// Missing state is a successful no-op and does not request durability
/// confirmation. Once removal returns Removed, a later durability failure is
/// retained as committed removal evidence rather than reported as rollback.
///
/// # Errors
///
/// Returns outbound coordination/removal failure before absence commits.
pub fn remove_blob_durably<Store>(
    store: &mut Store,
) -> NativeContinuationBlobDurableRemovalStoreResult<Store>
where
    Store: DurableBlobStore + RemovableBlobStore,
{
    match remove_blob(store)? {
        NativeContinuationBlobPersistenceRemoval::Missing => {
            Ok(NativeContinuationBlobDurableRemoval::Missing)
        },
        NativeContinuationBlobPersistenceRemoval::Removed => {
            match store.confirm_durability() {
                Ok(()) => Ok(NativeContinuationBlobDurableRemoval::Durable),
                Err(durability_error) => {
                    Ok(NativeContinuationBlobDurableRemoval::Removed {
                        durability_error,
                    })
                },
            }
        },
    }
}

/// Removes one configured blob publication when present.
///
/// # Errors
///
/// Returns outbound coordination/removal failure before absence is claimed.
pub fn remove_blob<Store>(
    store: &mut Store,
) -> NativeContinuationBlobPersistenceResult<
    NativeContinuationBlobPersistenceRemoval,
    Store::Error,
>
where
    Store: RemovableBlobStore,
{
    store
        .remove()
        .map(|outcome| match outcome {
            BlobRemoval::Missing => {
                NativeContinuationBlobPersistenceRemoval::Missing
            },
            BlobRemoval::Removed => {
                NativeContinuationBlobPersistenceRemoval::Removed
            },
        })
        .map_err(NativeContinuationBlobPersistenceError::Store)
}

/// Restores one bounded blob without interpreting its bytes.
///
/// # Errors
///
/// Returns store or byte-limit evidence. The application rechecks the adapter
/// result before exposing bytes to telemetry-specific decoding.
pub fn restore_blob<Store>(
    store: &mut Store,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobPersistenceResult<
    NativeContinuationBlobPersistenceLoad,
    Store::Error,
>
where
    Store: BlobStore,
{
    let Some(bytes) = store
        .load(maximum_bytes)
        .map_err(NativeContinuationBlobPersistenceError::Store)?
    else {
        return Ok(NativeContinuationBlobPersistenceLoad::Missing);
    };
    admit_byte_limit(bytes.len(), maximum_bytes)?;
    Ok(NativeContinuationBlobPersistenceLoad::Present { bytes })
}

const fn admit_byte_limit<StoreError>(
    observed_bytes: usize,
    maximum_bytes: NonZeroUsize,
) -> NativeContinuationBlobPersistenceResult<(), StoreError> {
    if observed_bytes <= maximum_bytes.get() {
        Ok(())
    } else {
        Err(NativeContinuationBlobPersistenceError::ByteLimit {
            maximum_bytes,
            observed_bytes,
        })
    }
}

#[cfg(test)]
mod tests {
    use std::fs::{create_dir_all, remove_dir_all};
    use std::io::ErrorKind;
    use std::{env, process};

    use super::*;
    use crate::blob_store::{
        NativeContinuationBlobConditionalRemoval,
        NativeContinuationBlobConditionalRemovalResult,
        NativeContinuationBlobRemoval, NativeContinuationBlobRemovalResult,
        NativeContinuationBlobStore,
        NativeContinuationConditionalRemovableBlobStore,
        NativeContinuationDurableBlobStore,
        NativeContinuationRemovableBlobStore,
    };
    use crate::file_blob_store::NativeContinuationFileBlobStore;

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum DurabilityError {
        Failed,
    }

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum StoreError {
        Failed,
    }

    #[derive(Debug, Default)]
    struct MemoryStore {
        bytes: Option<Vec<u8>>,
        durability_calls: usize,
        fail_durability: bool,
        fail_remove: bool,
    }

    impl NativeContinuationBlobStore for MemoryStore {
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

    impl NativeContinuationConditionalRemovableBlobStore for MemoryStore {
        fn compare_and_remove(
            &mut self,
            expected: Option<&[u8]>,
            _maximum_bytes: NonZeroUsize,
        ) -> NativeContinuationBlobConditionalRemovalResult<Self::Error>
        {
            if self.bytes.as_deref() != expected {
                return Ok(
                    NativeContinuationBlobConditionalRemoval::Conflict {
                        current: self.bytes.clone(),
                    },
                );
            }
            if self.fail_remove {
                return Err(StoreError::Failed);
            }
            if self.bytes.take().is_some() {
                Ok(NativeContinuationBlobConditionalRemoval::Removed)
            } else {
                Ok(NativeContinuationBlobConditionalRemoval::Missing)
            }
        }
    }

    impl NativeContinuationRemovableBlobStore for MemoryStore {
        fn remove(
            &mut self,
        ) -> NativeContinuationBlobRemovalResult<Self::Error> {
            if self.fail_remove {
                return Err(StoreError::Failed);
            }
            if self.bytes.take().is_some() {
                Ok(NativeContinuationBlobRemoval::Removed)
            } else {
                Ok(NativeContinuationBlobRemoval::Missing)
            }
        }
    }

    impl NativeContinuationDurableBlobStore for MemoryStore {
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

    #[test]
    fn conditional_durability_failure_retains_removal() -> Result<(), String> {
        let expected = vec![4, 5, 6];
        let mut store = MemoryStore {
            bytes: Some(expected.clone()),
            fail_durability: true,
            ..MemoryStore::default()
        };
        let maximum_bytes = NonZeroUsize::new(expected.len())
            .ok_or_else(|| String::from("test bound missing"))?;
        let outcome = compare_and_remove_blob_durably(
            &mut store,
            Some(&expected),
            maximum_bytes,
        )
        .map_err(|error| format!("{error:?}"))?;
        if outcome
            == (NativeContinuationBlobConditionalDurableRemoval::Removed {
                durability_error: DurabilityError::Failed,
            })
            && store.bytes.is_none()
            && store.durability_calls == 1
        {
            Ok(())
        } else {
            Err(String::from(
                "conditional durability failure lost committed removal",
            ))
        }
    }

    #[test]
    fn conditional_missing_skips_durability_confirmation() -> Result<(), String>
    {
        let mut store = MemoryStore::default();
        let maximum_bytes = NonZeroUsize::new(8)
            .ok_or_else(|| String::from("test bound missing"))?;
        let outcome =
            compare_and_remove_blob_durably(&mut store, None, maximum_bytes)
                .map_err(|error| format!("{error:?}"))?;
        if outcome == NativeContinuationBlobConditionalDurableRemoval::Missing
            && store.durability_calls == 0
        {
            Ok(())
        } else {
            Err(String::from(
                "conditional missing removal requested durability",
            ))
        }
    }

    #[test]
    fn conditional_conflict_preserves_publication() -> Result<(), String> {
        let current = vec![7, 8, 9];
        let expected = vec![1, 2, 3];
        let mut store = MemoryStore {
            bytes: Some(current.clone()),
            ..MemoryStore::default()
        };
        let maximum_bytes = NonZeroUsize::new(current.len())
            .ok_or_else(|| String::from("test bound missing"))?;
        let outcome = compare_and_remove_blob_durably(
            &mut store,
            Some(&expected),
            maximum_bytes,
        )
        .map_err(|error| format!("{error:?}"))?;
        if outcome.conflict() == Some(current.as_slice())
            && store.bytes == Some(current)
            && store.durability_calls == 0
        {
            Ok(())
        } else {
            Err(String::from(
                "conditional removal conflict changed publication",
            ))
        }
    }

    #[test]
    fn conditional_removal_match_confirms_absence() -> Result<(), String> {
        let expected = vec![10, 11, 12];
        let mut store = MemoryStore {
            bytes: Some(expected.clone()),
            ..MemoryStore::default()
        };
        let maximum_bytes = NonZeroUsize::new(expected.len())
            .ok_or_else(|| String::from("test bound missing"))?;
        let outcome = compare_and_remove_blob_durably(
            &mut store,
            Some(&expected),
            maximum_bytes,
        )
        .map_err(|error| format!("{error:?}"))?;
        if outcome == NativeContinuationBlobConditionalDurableRemoval::Durable
            && store.bytes.is_none()
            && store.durability_calls == 1
        {
            Ok(())
        } else {
            Err(String::from("conditional removal did not confirm absence"))
        }
    }

    #[test]
    fn conditional_file_store_rejects_stale_removal() -> Result<(), String> {
        let directory = env::temp_dir().join(format!(
            "malbolge-blob-conditional-remove-{}",
            process::id(),
        ));
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
        let current = [13, 14, 15];
        let stale = [1, 2, 3];
        let maximum_bytes = NonZeroUsize::new(current.len())
            .ok_or_else(|| String::from("test bound missing"))?;
        let destination = directory.join("blob.bin");
        let mut store = NativeContinuationFileBlobStore::new(destination);
        let _write = persist_blob(&mut store, &current, maximum_bytes)
            .map_err(|error| format!("{error:?}"))?;
        let conflict = compare_and_remove_blob_durably(
            &mut store,
            Some(&stale),
            maximum_bytes,
        )
        .map_err(|error| format!("{error:?}"))?;
        let removed = compare_and_remove_blob_durably(
            &mut store,
            Some(&current),
            maximum_bytes,
        )
        .map_err(|error| format!("{error:?}"))?;
        let load = restore_blob(&mut store, maximum_bytes)
            .map_err(|error| format!("{error:?}"))?;
        drop(store);
        remove_dir_all(&directory).map_err(|error| {
            format!("test directory removal failed: {error}")
        })?;
        if conflict.conflict() == Some(current.as_slice())
            && removed
                == NativeContinuationBlobConditionalDurableRemoval::Durable
            && load == NativeContinuationBlobPersistenceLoad::Missing
        {
            Ok(())
        } else {
            Err(String::from("file conditional removal evidence drifted"))
        }
    }

    #[test]
    fn durable_removal_confirms_committed_absence() -> Result<(), String> {
        let mut store = MemoryStore {
            bytes: Some(vec![1, 2, 3]),
            ..MemoryStore::default()
        };
        let outcome = remove_blob_durably(&mut store)
            .map_err(|error| format!("{error:?}"))?;
        if outcome == NativeContinuationBlobDurableRemoval::Durable
            && store.bytes.is_none()
            && store.durability_calls == 1
        {
            Ok(())
        } else {
            Err(String::from("durable removal evidence drifted"))
        }
    }

    #[test]
    fn durability_failure_keeps_removed_state() -> Result<(), String> {
        let mut store = MemoryStore {
            bytes: Some(vec![4, 5, 6]),
            fail_durability: true,
            ..MemoryStore::default()
        };
        let outcome = remove_blob_durably(&mut store)
            .map_err(|error| format!("{error:?}"))?;
        if outcome
            == (NativeContinuationBlobDurableRemoval::Removed {
                durability_error: DurabilityError::Failed,
            })
            && store.bytes.is_none()
            && store.durability_calls == 1
        {
            Ok(())
        } else {
            Err(String::from(
                "durability failure did not retain committed removal",
            ))
        }
    }

    #[test]
    fn file_store_removal_round_trip() -> Result<(), String> {
        let directory = env::temp_dir()
            .join(format!("malbolge-blob-remove-{}", process::id()));
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
        let destination = directory.join("blob.bin");
        let mut store = NativeContinuationFileBlobStore::new(destination);
        let _write = persist_blob(
            &mut store,
            &[7, 8, 9],
            NonZeroUsize::new(3)
                .ok_or_else(|| String::from("test bound missing"))?,
        )
        .map_err(|error| format!("{error:?}"))?;
        let removed = remove_blob_durably(&mut store)
            .map_err(|error| format!("{error:?}"))?;
        let missing = remove_blob_durably(&mut store)
            .map_err(|error| format!("{error:?}"))?;
        let load = restore_blob(
            &mut store,
            NonZeroUsize::new(3)
                .ok_or_else(|| String::from("test bound missing"))?,
        )
        .map_err(|error| format!("{error:?}"))?;
        drop(store);
        remove_dir_all(&directory).map_err(|error| {
            format!("test directory removal failed: {error}")
        })?;
        if removed == NativeContinuationBlobDurableRemoval::Durable
            && missing == NativeContinuationBlobDurableRemoval::Missing
            && load == NativeContinuationBlobPersistenceLoad::Missing
        {
            Ok(())
        } else {
            Err(String::from("file blob removal round trip drifted"))
        }
    }

    #[test]
    fn missing_removal_skips_durability_confirmation() -> Result<(), String> {
        let mut store = MemoryStore::default();
        let outcome = remove_blob_durably(&mut store)
            .map_err(|error| format!("{error:?}"))?;
        if outcome == NativeContinuationBlobDurableRemoval::Missing
            && store.durability_calls == 0
        {
            Ok(())
        } else {
            Err(String::from("missing removal requested durability"))
        }
    }

    #[test]
    fn removal_failure_preserves_publication() -> Result<(), String> {
        let original = vec![10, 11, 12];
        let mut store = MemoryStore {
            bytes: Some(original.clone()),
            fail_remove: true,
            ..MemoryStore::default()
        };
        let outcome = remove_blob_durably(&mut store);
        if matches!(
            outcome,
            Err(NativeContinuationBlobPersistenceError::Store(
                StoreError::Failed,
            ))
        ) && store.bytes == Some(original)
            && store.durability_calls == 0
        {
            Ok(())
        } else {
            Err(String::from("failed removal changed publication"))
        }
    }
}
