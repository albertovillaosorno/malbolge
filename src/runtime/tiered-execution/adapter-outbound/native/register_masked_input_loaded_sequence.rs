// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Loaded mapping ownership and reverse cleanup for admitted Input
//     register-masked v6 sequence plans.
// - Must-Not:
//   - Execute native code, call runners, own lease caches, or alter plan
//     admission semantics.
// - Allows:
//   - Inputs: admitted Input plans and a memory adapter.
//   - Inputs: fully loaded sequence owners or indexed load/cleanup evidence.
//   - Side effects: executable load/release only through the supplied adapter.
// - Split-When:
//   - Loaded runner execution gains independent semantic authority.
// - Merge-When:
//   - One reviewed Input sequence coordinator owns load and execution.
// - Summary:
//   - Publishes only fully loaded Input plans and releases in reverse.
// - Description:
//   - Partial loads clean their complete ready prefix before returning failure.
// - Usage:
//   - Load an admitted plan, inspect retained mapping weight, then release.
// - Defaults:
//   - No execution or buffer mutation occurs in this boundary.
//

//! Loaded ownership for admitted Input register-masked v6 plans.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::platform::{
    NativeExecutableMemoryAdapter,
    RegisterMaskedInputNativeExecutableReleaseFailure,
};
use super::register_masked_input_sequence as sequence;
use super::register_masked_resident::{
    RegisterMaskedInputNativeExecutableOwner,
    RegisterMaskedInputNativeOwnerLoadFailure,
};

/// Indexed failure while loading one admitted Input v6 sequence.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedInputNativeSequenceLoadFailure<MemoryError> {
    cause: Box<RegisterMaskedInputNativeOwnerLoadFailure<MemoryError>>,
    cleanup_failure: Option<
        Box<RegisterMaskedInputNativeSequenceReleaseFailure<MemoryError>>,
    >,
    index: usize,
    loaded_count: usize,
}

/// Aggregate reverse-release failure retaining exact ready executables.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedInputNativeSequenceReleaseFailure<MemoryError> {
    attempted_count: usize,
    failures:
        Vec<RegisterMaskedInputNativeExecutableReleaseFailure<MemoryError>>,
    released_count: usize,
}

/// Result of loading every mapping for one admitted Input v6 plan.
pub type RegisterMaskedInputNativeSequenceLoadResult<MemoryError> = Result<
    LoadedRegisterMaskedInputNativeSequence,
    Box<RegisterMaskedInputNativeSequenceLoadFailure<MemoryError>>,
>;

/// Result of releasing every mapping retained by a Input sequence.
pub type RegisterMaskedInputNativeSequenceReleaseResult<MemoryError> = Result<
    (),
    Box<RegisterMaskedInputNativeSequenceReleaseFailure<MemoryError>>,
>;

/// Fully loaded admitted Input v6 sequence without runner authority.
#[derive(Debug)]
pub struct LoadedRegisterMaskedInputNativeSequence {
    owners: Vec<RegisterMaskedInputNativeExecutableOwner>,
    plan: sequence::RegisterMaskedInputNativeSequencePlan,
}

impl<MemoryError> RegisterMaskedInputNativeSequenceLoadFailure<MemoryError> {
    /// Returns retryable prefix-cleanup failure, when cleanup also failed.
    #[must_use]
    pub const fn cleanup_failure(
        &self,
    ) -> Option<&RegisterMaskedInputNativeSequenceReleaseFailure<MemoryError>>
    {
        match &self.cleanup_failure {
            Some(failure) => Some(failure),
            None => None,
        }
    }

    /// Returns the zero-based sequence position whose load failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Consumes this failure and returns retryable prefix cleanup ownership.
    #[must_use]
    pub fn into_cleanup_failure(
        self,
    ) -> Option<RegisterMaskedInputNativeSequenceReleaseFailure<MemoryError>>
    {
        self.cleanup_failure.map(|failure| *failure)
    }

    /// Returns the number of mappings ready before the failed position.
    #[must_use]
    pub const fn loaded_count(&self) -> usize {
        self.loaded_count
    }

    /// Returns the exact owner-load failure at the failed position.
    #[must_use]
    pub const fn owner_failure(
        &self,
    ) -> &RegisterMaskedInputNativeOwnerLoadFailure<MemoryError> {
        &self.cause
    }
}

impl<MemoryError: Display> Display
    for RegisterMaskedInputNativeSequenceLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "Input v6 sequence load failed at step {}: {}",
            self.index, self.cause,
        )?;
        if self.cleanup_failure.is_some() {
            f.write_str("; loaded-prefix cleanup also failed")?;
        }
        Ok(())
    }
}

impl<MemoryError> RegisterMaskedInputNativeSequenceReleaseFailure<MemoryError> {
    /// Returns the number of mappings attempted by this release pass.
    #[must_use]
    pub const fn attempted_count(&self) -> usize {
        self.attempted_count
    }

    /// Returns the number of mappings still retained after this pass.
    #[must_use]
    pub const fn failed_count(&self) -> usize {
        self.failures.len()
    }

    /// Returns all exact ready-executable failures retained for retry.
    #[must_use]
    pub fn failures(
        &self,
    ) -> &[RegisterMaskedInputNativeExecutableReleaseFailure<MemoryError>] {
        &self.failures
    }

    /// Returns the number of mappings released by this pass.
    #[must_use]
    pub const fn released_count(&self) -> usize {
        self.released_count
    }

    /// Retries every still-owned mapping and retains repeated failures only.
    ///
    /// # Errors
    ///
    /// Returns another aggregate failure while at least one release still
    /// fails.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedInputNativeSequenceReleaseResult<MemoryError>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        retry_input_release_failures(adapter, self.failures)
    }
}

impl<MemoryError: Display> Display
    for RegisterMaskedInputNativeSequenceReleaseFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "Input v6 sequence release retained {} of {} mappings",
            self.failed_count(),
            self.attempted_count,
        )
    }
}

impl LoadedRegisterMaskedInputNativeSequence {
    /// Returns whether this loaded sequence owns no executable mappings.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.owners.is_empty()
    }

    /// Returns the number of retained executable mappings.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.owners.len()
    }

    /// Returns exact total mapped bytes, or `None` on host-size overflow.
    #[must_use]
    pub fn mapped_bytes(&self) -> Option<usize> {
        self.owners.iter().try_fold(0usize, |total, owner| {
            total.checked_add(owner.resident_weight().mapped_bytes())
        })
    }

    /// Returns retained owners to sibling native sequence coordinators only.
    #[must_use]
    pub(super) fn owners(&self) -> &[RegisterMaskedInputNativeExecutableOwner] {
        &self.owners
    }

    /// Returns the exact admitted sequence plan retained beside the mappings.
    #[must_use]
    pub const fn plan(
        &self,
    ) -> &sequence::RegisterMaskedInputNativeSequencePlan {
        &self.plan
    }

    /// Releases every retained mapping in reverse semantic order.
    ///
    /// Every mapping is attempted after an earlier cleanup failure. Failed
    /// releases retain exact ready-executable ownership for explicit retry.
    ///
    /// # Errors
    ///
    /// Returns aggregate retry ownership while at least one mapping remains.
    pub fn release<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedInputNativeSequenceReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        release_input_owners(adapter, self.owners)
    }
}

/// Loads every exact sequence mapping before publishing loaded ownership.
///
/// A later load failure releases the complete ready prefix in reverse order.
/// Any failed prefix cleanup remains retryable through the returned failure.
/// This function grants mapping ownership only; it never executes code.
///
/// # Errors
///
/// Returns indexed owner-load failure and optional prefix cleanup ownership.
pub fn load_register_masked_input_native_sequence<Adapter>(
    plan: &sequence::RegisterMaskedInputNativeSequencePlan,
    adapter: &mut Adapter,
) -> RegisterMaskedInputNativeSequenceLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut owners = Vec::with_capacity(plan.len());
    for (index, (program, artifact)) in
        plan.programs().iter().zip(plan.artifacts()).enumerate()
    {
        match RegisterMaskedInputNativeExecutableOwner::load(
            adapter, program, artifact,
        ) {
            Ok(owner) => owners.push(owner),
            Err(cause) => {
                let loaded_count = owners.len();
                let cleanup_failure =
                    release_input_owners(adapter, owners).err();
                return Err(Box::new(
                    RegisterMaskedInputNativeSequenceLoadFailure {
                        cause,
                        cleanup_failure,
                        index,
                        loaded_count,
                    },
                ));
            },
        }
    }
    Ok(LoadedRegisterMaskedInputNativeSequence {
        owners,
        plan: plan.clone(),
    })
}

fn release_input_owners<Adapter>(
    adapter: &mut Adapter,
    owners: Vec<RegisterMaskedInputNativeExecutableOwner>,
) -> RegisterMaskedInputNativeSequenceReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let attempted_count = owners.len();
    let mut failures = Vec::new();
    let mut released_count = 0usize;
    for owner in owners.into_iter().rev() {
        match owner.release(adapter) {
            Ok(()) => released_count = released_count.saturating_add(1),
            Err(failure) => failures.push(*failure),
        }
    }
    release_pass_result(attempted_count, released_count, failures)
}

fn retry_input_release_failures<Adapter>(
    adapter: &mut Adapter,
    pending: Vec<
        RegisterMaskedInputNativeExecutableReleaseFailure<Adapter::Error>,
    >,
) -> RegisterMaskedInputNativeSequenceReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let attempted_count = pending.len();
    let mut failures = Vec::new();
    let mut released_count = 0usize;
    for failure in pending {
        match failure.retry(adapter) {
            Ok(()) => released_count = released_count.saturating_add(1),
            Err(retry_failure) => failures.push(retry_failure),
        }
    }
    release_pass_result(attempted_count, released_count, failures)
}

fn release_pass_result<MemoryError>(
    attempted_count: usize,
    released_count: usize,
    failures: Vec<
        RegisterMaskedInputNativeExecutableReleaseFailure<MemoryError>,
    >,
) -> RegisterMaskedInputNativeSequenceReleaseResult<MemoryError> {
    if failures.is_empty() {
        Ok(())
    } else {
        Err(Box::new(RegisterMaskedInputNativeSequenceReleaseFailure {
            attempted_count,
            failures,
            released_count,
        }))
    }
}
