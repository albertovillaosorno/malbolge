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
//   - Loaded mapping ownership and reverse cleanup for admitted JumpCode
//     register-masked v6 sequence plans.
// - Must-Not:
//   - Execute native code, call runners, own lease caches, or alter plan
//     admission semantics.
// - Allows:
//   - JumpCodes: admitted JumpCode plans and a memory adapter.
//   - JumpCodes: fully loaded sequence owners or indexed load/cleanup evidence.
//   - Side effects: executable load/release only through the supplied adapter.
// - Split-When:
//   - Loaded runner execution gains independent semantic authority.
// - Merge-When:
//   - One reviewed JumpCode sequence coordinator owns load and execution.
// - Summary:
//   - Publishes only fully loaded JumpCode plans and releases in reverse.
// - Description:
//   - Partial loads clean their complete ready prefix before returning failure.
// - Usage:
//   - Load an admitted plan, inspect retained mapping weight, then release.
// - Defaults:
//   - No execution or buffer mutation occurs in this boundary.
//

//! Loaded ownership for admitted `JumpCode` register-masked v6 plans.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::platform::{
    NativeExecutableMemoryAdapter,
    RegisterMaskedJumpCodeNativeExecutableReleaseFailure,
};
use super::register_masked_jump_code_sequence as sequence;
use super::register_masked_resident::{
    RegisterMaskedJumpCodeNativeExecutableOwner,
    RegisterMaskedJumpCodeNativeOwnerLoadFailure,
};

/// Indexed failure while loading one admitted `JumpCode` v6 sequence.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedJumpCodeNativeSequenceLoadFailure<MemoryError> {
    cause: Box<RegisterMaskedJumpCodeNativeOwnerLoadFailure<MemoryError>>,
    cleanup_failure: Option<
        Box<RegisterMaskedJumpCodeNativeSequenceReleaseFailure<MemoryError>>,
    >,
    index: usize,
    loaded_count: usize,
}

/// Aggregate reverse-release failure retaining exact ready executables.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedJumpCodeNativeSequenceReleaseFailure<MemoryError> {
    attempted_count: usize,
    failures:
        Vec<RegisterMaskedJumpCodeNativeExecutableReleaseFailure<MemoryError>>,
    released_count: usize,
}

/// Result of loading every mapping for one admitted `JumpCode` v6 plan.
pub type RegisterMaskedJumpCodeNativeSequenceLoadResult<MemoryError> = Result<
    LoadedRegisterMaskedJumpCodeNativeSequence,
    Box<RegisterMaskedJumpCodeNativeSequenceLoadFailure<MemoryError>>,
>;

/// Result of releasing every mapping retained by a `JumpCode` sequence.
pub type RegisterMaskedJumpCodeNativeSequenceReleaseResult<MemoryError> =
    Result<
        (),
        Box<RegisterMaskedJumpCodeNativeSequenceReleaseFailure<MemoryError>>,
    >;

/// Fully loaded admitted `JumpCode` v6 sequence without runner authority.
#[derive(Debug)]
pub struct LoadedRegisterMaskedJumpCodeNativeSequence {
    owners: Vec<RegisterMaskedJumpCodeNativeExecutableOwner>,
    plan: sequence::RegisterMaskedJumpCodeNativeSequencePlan,
}

impl<MemoryError> RegisterMaskedJumpCodeNativeSequenceLoadFailure<MemoryError> {
    /// Returns whether loaded-prefix cleanup also failed.
    #[must_use]
    pub const fn cleanup_failed(&self) -> bool {
        self.cleanup_failure.is_some()
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
    ) -> Option<RegisterMaskedJumpCodeNativeSequenceReleaseFailure<MemoryError>>
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
    ) -> &RegisterMaskedJumpCodeNativeOwnerLoadFailure<MemoryError> {
        &self.cause
    }
}

impl<MemoryError: Display> Display
    for RegisterMaskedJumpCodeNativeSequenceLoadFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "JumpCode v6 sequence load failed at step {}: {}",
            self.index, self.cause,
        )?;
        if self.cleanup_failure.is_some() {
            f.write_str("; loaded-prefix cleanup also failed")?;
        }
        Ok(())
    }
}

impl<MemoryError>
    RegisterMaskedJumpCodeNativeSequenceReleaseFailure<MemoryError>
{
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
    ) -> &[RegisterMaskedJumpCodeNativeExecutableReleaseFailure<MemoryError>]
    {
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
    ) -> RegisterMaskedJumpCodeNativeSequenceReleaseResult<MemoryError>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        retry_jump_code_release_failures(adapter, self.failures)
    }
}

impl<MemoryError: Display> Display
    for RegisterMaskedJumpCodeNativeSequenceReleaseFailure<MemoryError>
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "JumpCode v6 sequence release retained {} of {} mappings",
            self.failed_count(),
            self.attempted_count,
        )
    }
}

impl LoadedRegisterMaskedJumpCodeNativeSequence {
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

    /// Returns retained owners for execution by the sibling coordinator.
    #[must_use]
    pub(super) fn owners(
        &self,
    ) -> &[RegisterMaskedJumpCodeNativeExecutableOwner] {
        &self.owners
    }

    /// Returns the exact admitted sequence plan retained beside the mappings.
    #[must_use]
    pub const fn plan(
        &self,
    ) -> &sequence::RegisterMaskedJumpCodeNativeSequencePlan {
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
    ) -> RegisterMaskedJumpCodeNativeSequenceReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        release_jump_code_owners(adapter, self.owners)
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
pub fn load_register_masked_jump_code_native_sequence<Adapter>(
    plan: &sequence::RegisterMaskedJumpCodeNativeSequencePlan,
    adapter: &mut Adapter,
) -> RegisterMaskedJumpCodeNativeSequenceLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut owners = Vec::with_capacity(plan.len());
    for (index, (program, artifact)) in
        plan.programs().iter().zip(plan.artifacts()).enumerate()
    {
        match RegisterMaskedJumpCodeNativeExecutableOwner::load(
            adapter, program, artifact,
        ) {
            Ok(owner) => owners.push(owner),
            Err(cause) => {
                let loaded_count = owners.len();
                let cleanup_failure =
                    release_jump_code_owners(adapter, owners).err();
                return Err(Box::new(
                    RegisterMaskedJumpCodeNativeSequenceLoadFailure {
                        cause,
                        cleanup_failure,
                        index,
                        loaded_count,
                    },
                ));
            },
        }
    }
    Ok(LoadedRegisterMaskedJumpCodeNativeSequence {
        owners,
        plan: plan.clone(),
    })
}

fn release_jump_code_owners<Adapter>(
    adapter: &mut Adapter,
    owners: Vec<RegisterMaskedJumpCodeNativeExecutableOwner>,
) -> RegisterMaskedJumpCodeNativeSequenceReleaseResult<Adapter::Error>
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

fn retry_jump_code_release_failures<Adapter>(
    adapter: &mut Adapter,
    pending: Vec<
        RegisterMaskedJumpCodeNativeExecutableReleaseFailure<Adapter::Error>,
    >,
) -> RegisterMaskedJumpCodeNativeSequenceReleaseResult<Adapter::Error>
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
        RegisterMaskedJumpCodeNativeExecutableReleaseFailure<MemoryError>,
    >,
) -> RegisterMaskedJumpCodeNativeSequenceReleaseResult<MemoryError> {
    if failures.is_empty() {
        Ok(())
    } else {
        Err(Box::new(
            RegisterMaskedJumpCodeNativeSequenceReleaseFailure {
                attempted_count,
                failures,
                released_count,
            },
        ))
    }
}
