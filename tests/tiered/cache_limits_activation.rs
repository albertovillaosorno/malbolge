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
//   - Root-tree regression coverage for cache-limit activation.
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
//   - Proves cache-limit activation behavior from the root test tree.
// - Description:
//   - Loaded as a test-only child module to retain private-item access.
// - Usage:
//   - Selected by the parent module only when Rust test configuration is set.
// - Defaults:
//   - Production builds never compile this regression module.
//

//! Root-tree regression coverage for cache-limit activation.

use std::convert::Infallible;

use super::*;
use crate::blob_store::{
    NativeContinuationBlobRemoval, NativeContinuationBlobRemovalResult,
    NativeContinuationDurableBlobStore, NativeContinuationRemovableBlobStore,
};
use crate::executable_cache_limits_persistence::{
    NativeExecutableSequenceCacheLimitsDurableRemoval,
    evict_native_executable_sequence_cache_limits_durably,
};
use crate::execution_native::{
    NativeExecutableAllocationRequest, NativeExecutableCodeCopyReport,
    NativeExecutableMappingReport, NativeExecutableReleaseRequest,
    NativeExecutableSequenceCacheLimits, NativeInstructionSyncReport,
    NativeInstructionSyncRequest,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum AdapterError {
    UnexpectedOperation,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum StoreError {
    Replace,
}

#[derive(Debug, Default)]
struct NoOpAdapter {
    calls: usize,
}

#[derive(Debug, Default)]
struct MemoryStore {
    bytes: Option<Vec<u8>>,
}

impl BlobStore for MemoryStore {
    type Error = StoreError;

    fn load(
        &mut self,
        _maximum_bytes: NonZeroUsize,
    ) -> Result<Option<Vec<u8>>, Self::Error> {
        Ok(self.bytes.clone())
    }

    fn replace(&mut self, _bytes: &[u8]) -> Result<(), Self::Error> {
        Err(StoreError::Replace)
    }
}

impl NativeContinuationDurableBlobStore for MemoryStore {
    type DurabilityError = Infallible;

    fn confirm_durability(&mut self) -> Result<(), Self::DurabilityError> {
        Ok(())
    }
}

impl NativeContinuationRemovableBlobStore for MemoryStore {
    fn remove(&mut self) -> NativeContinuationBlobRemovalResult<Self::Error> {
        if self.bytes.take().is_some() {
            Ok(NativeContinuationBlobRemoval::Removed)
        } else {
            Ok(NativeContinuationBlobRemoval::Missing)
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

fn encoded_limits(entry_limit: usize) -> Result<Vec<u8>, String> {
    let entry_limit = NonZeroUsize::new(entry_limit)
        .ok_or_else(|| String::from("test entry limit missing"))?;
    crate::execution_native::encode_native_executable_sequence_cache_limits(
        NativeExecutableSequenceCacheLimits::new(entry_limit),
    )
    .map_err(|error| format!("{error:?}"))
}

fn positive(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test positive value missing"))
}

#[test]
fn lease_cache_missing_policy_is_no_op() -> Result<(), String> {
    let initial = NativeExecutableSequenceCacheLimits::new(positive(5)?);
    let mut cache = NativeExecutableSequenceLeaseCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let mut store = MemoryStore::default();
    let activation =
        restore_and_apply_native_executable_sequence_lease_cache_limits(
            &mut store,
            &mut cache,
            &mut adapter,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    if activation == NativeExecutableSequenceLeaseCacheLimitsActivation::Missing
        && cache.limits() == initial
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("missing lease-cache policy changed state"))
    }
}

#[test]
fn lease_cache_restored_policy_reconfigures_empty_cache() -> Result<(), String>
{
    let initial = NativeExecutableSequenceCacheLimits::new(positive(5)?);
    let requested = NativeExecutableSequenceCacheLimits::new(positive(2)?);
    let mut cache = NativeExecutableSequenceLeaseCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let mut store = MemoryStore {
        bytes: Some(encoded_limits(2)?),
    };
    let activation =
        restore_and_apply_native_executable_sequence_lease_cache_limits(
            &mut store,
            &mut cache,
            &mut adapter,
            positive(40)?,
        )
        .map_err(|error| format!("{error:?}"))?;
    let NativeExecutableSequenceLeaseCacheLimitsActivation::Reconfigured {
        bytes,
        reconfiguration,
    } = activation
    else {
        return Err(String::from("restored lease policy stayed missing"));
    };
    if bytes == 40
        && reconfiguration.limit_transition() == (initial, requested)
        && reconfiguration.evicted_keys().is_empty()
        && reconfiguration.retired_keys().is_empty()
        && cache.limits() == requested
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("lease-cache policy activation drifted"))
    }
}

#[test]
fn ordinary_cache_invalid_policy_fails_before_mutation() -> Result<(), String> {
    let initial = NativeExecutableSequenceCacheLimits::new(positive(4)?);
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let mut store = MemoryStore { bytes: Some(vec![0; 40]) };
    let activation = restore_and_apply_native_executable_sequence_cache_limits(
        &mut store,
        &mut cache,
        &mut adapter,
        positive(40)?,
    );
    if matches!(
        activation,
        Err(NativeExecutableSequenceCacheLimitsActivationError::Persistence(_),)
    ) && cache.limits() == initial
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "invalid durable policy changed ordinary cache",
        ))
    }
}

#[test]
fn evicted_policy_does_not_change_live_cache() -> Result<(), String> {
    let initial = NativeExecutableSequenceCacheLimits::new(positive(5)?);
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let mut store = MemoryStore {
        bytes: Some(encoded_limits(2)?),
    };
    let eviction =
        evict_native_executable_sequence_cache_limits_durably(&mut store)
            .map_err(|error| format!("{error:?}"))?;
    let activation = restore_and_apply_native_executable_sequence_cache_limits(
        &mut store,
        &mut cache,
        &mut adapter,
        positive(40)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if eviction == NativeExecutableSequenceCacheLimitsDurableRemoval::Durable
        && activation == NativeExecutableSequenceCacheLimitsActivation::Missing
        && cache.limits() == initial
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "durable policy eviction changed live cache state",
        ))
    }
}

#[test]
fn ordinary_cache_missing_policy_is_no_op() -> Result<(), String> {
    let initial = NativeExecutableSequenceCacheLimits::new(positive(4)?);
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let mut store = MemoryStore::default();
    let activation = restore_and_apply_native_executable_sequence_cache_limits(
        &mut store,
        &mut cache,
        &mut adapter,
        positive(40)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    if activation == NativeExecutableSequenceCacheLimitsActivation::Missing
        && cache.limits() == initial
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("missing ordinary-cache policy changed state"))
    }
}

#[test]
fn ordinary_cache_restored_policy_reconfigures_empty_cache()
-> Result<(), String> {
    let initial = NativeExecutableSequenceCacheLimits::new(positive(4)?);
    let requested = NativeExecutableSequenceCacheLimits::new(positive(2)?);
    let mut cache = NativeExecutableSequenceCache::with_limits(initial);
    let mut adapter = NoOpAdapter::default();
    let mut store = MemoryStore {
        bytes: Some(encoded_limits(2)?),
    };
    let activation = restore_and_apply_native_executable_sequence_cache_limits(
        &mut store,
        &mut cache,
        &mut adapter,
        positive(40)?,
    )
    .map_err(|error| format!("{error:?}"))?;
    let NativeExecutableSequenceCacheLimitsActivation::Reconfigured {
        bytes,
        reconfiguration,
    } = activation
    else {
        return Err(String::from("restored ordinary policy stayed missing"));
    };
    if bytes == 40
        && reconfiguration.limit_transition() == (initial, requested)
        && reconfiguration.evicted_keys().is_empty()
        && cache.limits() == requested
        && adapter.calls == 0
    {
        Ok(())
    } else {
        Err(String::from("ordinary-cache policy activation drifted"))
    }
}
