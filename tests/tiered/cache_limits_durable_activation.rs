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
//   - Root-tree regression coverage for durable cache-limit activation.
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
//   - Proves durable cache-limit activation behavior from the root test tree.
// - Description:
//   - Loaded as a test-only child module to retain private-item access.
// - Usage:
//   - Selected by the parent module only when Rust test configuration is set.
// - Defaults:
//   - Production builds never compile this regression module.
//

//! Root-tree regression coverage for durable cache-limit activation.

use super::*;
use crate::blob_persistence::NativeContinuationBlobPersistenceError;
use crate::blob_store::{
    NativeContinuationBlobConditionalPublication,
    NativeContinuationBlobConditionalPublicationResult,
};
use crate::execution_native::{
    NativeExecutableAllocationRequest, NativeExecutableCodeCopyReport,
    NativeExecutableMappingReport, NativeExecutableReleaseRequest,
    NativeInstructionSyncReport, NativeInstructionSyncRequest,
    encode_native_executable_sequence_cache_limits,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum AdapterError {
    UnexpectedOperation,
}

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
    fail_durability: bool,
    fail_store: bool,
}

#[derive(Debug, Default)]
struct NoOpAdapter {
    calls: usize,
}

impl BlobStore for MemoryStore {
    type Error = StoreError;

    fn load(
        &mut self,
        _maximum_bytes: NonZeroUsize,
    ) -> Result<Option<Vec<u8>>, Self::Error> {
        if self.fail_store {
            Err(StoreError::Failed)
        } else {
            Ok(self.bytes.clone())
        }
    }

    fn replace(&mut self, bytes: &[u8]) -> Result<(), Self::Error> {
        if self.fail_store {
            Err(StoreError::Failed)
        } else {
            self.bytes = Some(bytes.to_vec());
            Ok(())
        }
    }
}

impl ConditionalBlobStore for MemoryStore {
    fn compare_and_swap(
        &mut self,
        expected: Option<&[u8]>,
        replacement: &[u8],
        _maximum_bytes: NonZeroUsize,
    ) -> NativeContinuationBlobConditionalPublicationResult<Self::Error> {
        if self.fail_store {
            return Err(StoreError::Failed);
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
        if self.fail_durability {
            Err(DurabilityError::Failed)
        } else {
            Ok(())
        }
    }
}

impl NativeExecutableMemoryAdapter for NoOpAdapter {
    type Error = AdapterError;

    fn allocate_writable(
        &mut self,
        _request: NativeExecutableAllocationRequest,
    ) -> Result<NativeExecutableMappingReport, Self::Error> {
        self.calls = self.calls.saturating_add(1);
        Err(AdapterError::UnexpectedOperation)
    }

    fn copy_code(
        &mut self,
        _mapping: NativeExecutableMappingReport,
        _code: &[u8],
    ) -> Result<NativeExecutableCodeCopyReport, Self::Error> {
        self.calls = self.calls.saturating_add(1);
        Err(AdapterError::UnexpectedOperation)
    }

    fn protect_read_execute(
        &mut self,
        _mapping: NativeExecutableMappingReport,
    ) -> Result<NativeExecutableMappingReport, Self::Error> {
        self.calls = self.calls.saturating_add(1);
        Err(AdapterError::UnexpectedOperation)
    }

    fn release(
        &mut self,
        _request: NativeExecutableReleaseRequest,
    ) -> Result<(), Self::Error> {
        self.calls = self.calls.saturating_add(1);
        Err(AdapterError::UnexpectedOperation)
    }

    fn synchronize_instructions(
        &mut self,
        _request: NativeInstructionSyncRequest,
    ) -> Result<NativeInstructionSyncReport, Self::Error> {
        self.calls = self.calls.saturating_add(1);
        Err(AdapterError::UnexpectedOperation)
    }
}

fn activation_request(
    expected: Option<NativeExecutableSequenceCacheLimits>,
    candidate: NativeExecutableSequenceCacheLimits,
) -> Result<NativeExecutableSequenceCacheLimitsDurableActivationRequest, String>
{
    Ok(
        NativeExecutableSequenceCacheLimitsDurableActivationRequest::new(
            expected,
            candidate,
            positive(40)?,
        ),
    )
}

fn limits(
    entries: usize,
) -> Result<NativeExecutableSequenceCacheLimits, String> {
    NonZeroUsize::new(entries)
        .map(NativeExecutableSequenceCacheLimits::new)
        .ok_or_else(|| String::from("test cache entry limit missing"))
}

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test positive value missing"))
}

#[test]
fn committed_failure_retains_live_failure() -> Result<(), String> {
    let previous = limits(2)?;
    let candidate = limits(3)?;
    let publication = NativeExecutableSequenceCacheLimitsCas::Published {
        bytes: 40,
        current: candidate,
        durability_error: DurabilityError::Failed,
        previous: Some(previous),
    };
    let outcome = activate_committed_limits(publication, |limits| {
        if limits == candidate {
            Err::<(), &'static str>("blocked")
        } else {
            Err::<(), &'static str>("wrong limits")
        }
    });
    match outcome {
        NativeExecutableSequenceCacheLimitsDurableActivation::
            ReconfigurationFailed {
                publication:
                    NativeExecutableSequenceCacheLimitsCas::Published {
                        current,
                        durability_error,
                        previous: retained_previous,
                        ..
                    },
                failure,
            } if current == candidate
                && durability_error == DurabilityError::Failed
                && retained_previous == Some(previous)
                && failure == "blocked" =>
        {
            Ok(())
        },
        _ => Err(String::from(
            "committed live failure lost durable publication evidence",
        )),
    }
}

#[test]
fn conflict_leaves_ordinary_cache_untouched() -> Result<(), String> {
    let expected = limits(2)?;
    let current = limits(3)?;
    let candidate = limits(4)?;
    let initial = limits(5)?;
    let mut store = MemoryStore {
        bytes: Some(
            encode_native_executable_sequence_cache_limits(current)
                .map_err(|error| format!("{error:?}"))?,
        ),
        ..MemoryStore::default()
    };
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let outcome = publish_and_apply_executable_sequence_cache_limits_durably(
        &mut store,
        &mut cache,
        &mut adapter,
        activation_request(Some(expected), candidate)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if matches!(
        outcome,
        NativeExecutableSequenceCacheLimitsDurableActivation::Conflict {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Conflict {
                    current: Some(observed),
                    ..
                },
        } if observed == current
    ) && cache.limits() == initial
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("CAS conflict changed ordinary live cache"))
    }
}

#[test]
fn durable_commit_reconfigures_lease_cache() -> Result<(), String> {
    let initial = limits(5)?;
    let candidate = limits(2)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceLeaseCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let outcome =
        publish_and_apply_executable_sequence_lease_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            activation_request(None, candidate)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    match outcome {
        NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Durable {
                    current,
                    ..
                },
            reconfiguration,
        } if current == candidate
            && reconfiguration.limit_transition()
                == (initial, candidate)
            && reconfiguration.evicted_keys().is_empty()
            && reconfiguration.retired_keys().is_empty()
            && cache.limits() == candidate
            && adapter.calls == 0 =>
        {
            Ok(())
        },
        _ => Err(String::from(
            "durable commit did not reconfigure lease cache",
        )),
    }
}

#[test]
fn durable_commit_reconfigures_ordinary_cache() -> Result<(), String> {
    let initial = limits(5)?;
    let candidate = limits(2)?;
    let mut store = MemoryStore::default();
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let outcome = publish_and_apply_executable_sequence_cache_limits_durably(
        &mut store,
        &mut cache,
        &mut adapter,
        activation_request(None, candidate)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    match outcome {
        NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Durable {
                    current,
                    ..
                },
            reconfiguration,
        } if current == candidate
            && reconfiguration.limit_transition()
                == (initial, candidate)
            && reconfiguration.evicted_keys().is_empty()
            && cache.limits() == candidate
            && adapter.calls == 0 =>
        {
            Ok(())
        },
        _ => Err(String::from(
            "durable commit did not reconfigure ordinary cache",
        )),
    }
}

#[test]
fn file_store_publication_and_live_activation_stay_aligned()
-> Result<(), String> {
    use std::fs::{create_dir, remove_dir_all};
    use std::process;

    use crate::executable_cache_limits_persistence::{
        NativeExecutableSequenceCacheLimitsPersistenceLoad,
        restore_native_executable_sequence_cache_limits,
    };
    use crate::file_blob_store::NativeContinuationFileBlobStore;

    let directory = std::env::temp_dir()
        .join(format!("malbolge-cache-limit-live-{}", process::id(),));
    match remove_dir_all(&directory) {
        Ok(()) => {},
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {},
        Err(error) => {
            return Err(format!("test directory cleanup failed: {error}"));
        },
    }
    create_dir(&directory)
        .map_err(|error| format!("test directory create failed: {error}"))?;
    let destination = directory.join("limits.bin");
    let mut store = NativeContinuationFileBlobStore::new(destination);
    let initial = limits(5)?;
    let first = limits(3)?;
    let second = limits(2)?;
    let stale = limits(4)?;
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();

    let initialized =
        publish_and_apply_executable_sequence_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            activation_request(None, first)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    let updated = publish_and_apply_executable_sequence_cache_limits_durably(
        &mut store,
        &mut cache,
        &mut adapter,
        activation_request(Some(first), second)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    let conflicted =
        publish_and_apply_executable_sequence_cache_limits_durably(
            &mut store,
            &mut cache,
            &mut adapter,
            activation_request(Some(first), stale)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    let restored = restore_native_executable_sequence_cache_limits(
        &mut store,
        positive(40)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    let expected_restored =
        NativeExecutableSequenceCacheLimitsPersistenceLoad::Restored {
            bytes: 40,
            limits: second,
        };
    let valid = matches!(
        initialized,
        NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Durable {
                    current,
                    ..
                },
            ..
        } if current == first
    ) && matches!(
        updated,
        NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Durable {
                    current,
                    ..
                },
            ..
        } if current == second
    ) && matches!(
        conflicted,
        NativeExecutableSequenceCacheLimitsDurableActivation::Conflict {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Conflict {
                    current: Some(observed),
                    ..
                },
        } if observed == second
    ) && cache.limits() == second
        && restored == expected_restored
        && adapter.calls == 0;
    drop(store);
    remove_dir_all(&directory)
        .map_err(|error| format!("test directory removal failed: {error}"))?;
    if valid {
        Ok(())
    } else {
        Err(String::from(
            "file durable publication and live cache drifted",
        ))
    }
}

#[test]
fn post_commit_durability_failure_still_reconfigures_live_cache()
-> Result<(), String> {
    let initial = limits(5)?;
    let candidate = limits(2)?;
    let mut store = MemoryStore {
        fail_durability: true,
        ..MemoryStore::default()
    };
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let outcome = publish_and_apply_executable_sequence_cache_limits_durably(
        &mut store,
        &mut cache,
        &mut adapter,
        activation_request(None, candidate)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    match outcome {
        NativeExecutableSequenceCacheLimitsDurableActivation::Reconfigured {
            publication:
                NativeExecutableSequenceCacheLimitsCas::Published {
                    current,
                    durability_error,
                    ..
                },
            reconfiguration,
        } if current == candidate
            && durability_error == DurabilityError::Failed
            && reconfiguration.limit_transition()
                == (initial, candidate)
            && cache.limits() == candidate
            && adapter.calls == 0 =>
        {
            Ok(())
        },
        _ => Err(String::from(
            "committed sync failure did not activate live cache",
        )),
    }
}

#[test]
fn prepublication_store_failure_leaves_live_cache_untouched()
-> Result<(), String> {
    let initial = limits(5)?;
    let candidate = limits(2)?;
    let mut store = MemoryStore {
        fail_store: true,
        ..MemoryStore::default()
    };
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let result = publish_and_apply_executable_sequence_cache_limits_durably(
        &mut store,
        &mut cache,
        &mut adapter,
        activation_request(None, candidate)?,
    );
    if matches!(
        result,
        Err(NativeExecutableSequenceCacheLimitsCasError::Blob(
            NativeContinuationBlobPersistenceError::Store(StoreError::Failed,),
        ))
    ) && cache.limits() == initial
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "prepublication store failure changed live cache",
        ))
    }
}
