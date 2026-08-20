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
//   - Transactional loading and aggregate release of executable sequences.
// - Must-Not:
//   - Invoke code, fuse images, or implement platform memory operations.
// - Allows:
//   - Inputs: verified cached or uncached direct sequence plans.
//   - Outputs: ordered ready mappings or indexed load/cleanup failures.
//   - Side effects: only those performed by the supplied memory adapter.
// - Split-When:
//   - Shared executable caches or eviction policy gain independent ownership.
// - Merge-When:
//   - One platform owner subsumes loading, execution, and release.
// - Summary:
//   - Keeps every sequence mapping ready across multiple ordered calls.
// - Description:
//   - Prederives all images, rolls back partial loads, and releases in reverse.
// - Usage:
//   - Load once, execute through sequence_runner, then release explicitly.
// - Defaults:
//   - Every mapping is attempted during cleanup; failures remain retryable.
//

//! Persistent executable mapping ownership for verified direct sequences.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::direct::{
    CachedVerifiedDirectSequencePlan, VerifiedDirectNativeArtifact,
    VerifiedDirectSequencePlan,
};
use super::lifecycle::ReadyNativeExecutable;
use super::loader::{VerifiedDirectLoadError, VerifiedDirectLoadImage};
use super::platform::{
    NativeExecutableLoadFailure, NativeExecutableMemoryAdapter,
    NativeExecutableReleaseFailure, load_native_executable,
    release_native_executable,
};

/// Ordered ready mappings retaining the exact images of one sequence plan.
#[derive(Debug, Eq, PartialEq)]
pub struct ReadyNativeExecutableSequence {
    executables: Vec<ReadyNativeExecutable>,
}

#[derive(Debug, Eq, PartialEq)]
enum NativeExecutableSequenceLoadFailureCause<E> {
    Image(Box<VerifiedDirectLoadError>),
    Load(Box<NativeExecutableLoadFailure<E>>),
}

/// Indexed sequence-load failure with partial-load cleanup evidence.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceLoadFailure<E> {
    cause: NativeExecutableSequenceLoadFailureCause<E>,
    cleanup_failure: Option<Box<NativeExecutableSequenceReleaseFailure<E>>>,
    index: usize,
    loaded_count: usize,
}

/// Aggregate release failure retaining every mapping whose release failed.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeExecutableSequenceReleaseFailure<E> {
    attempted_count: usize,
    failures: Vec<NativeExecutableReleaseFailure<E>>,
    released_count: usize,
}

/// Result of loading all mappings for one verified sequence.
pub type NativeExecutableSequenceLoadResult<E> = Result<
    ReadyNativeExecutableSequence,
    Box<NativeExecutableSequenceLoadFailure<E>>,
>;

/// Result of releasing every mapping owned by one executable sequence.
pub type NativeExecutableSequenceReleaseResult<E> =
    Result<(), Box<NativeExecutableSequenceReleaseFailure<E>>>;

type DerivedSequenceImagesResult<E> = Result<
    Vec<VerifiedDirectLoadImage>,
    Box<NativeExecutableSequenceLoadFailure<E>>,
>;

struct NativeSequenceLoadFailureContext<E> {
    cause: NativeExecutableSequenceLoadFailureCause<E>,
    executables: Vec<ReadyNativeExecutable>,
    index: usize,
    loaded_count: usize,
}

impl ReadyNativeExecutableSequence {
    /// Returns all ready mappings in semantic execution order.
    #[must_use]
    pub fn executables(&self) -> &[ReadyNativeExecutable] {
        &self.executables
    }

    /// Returns whether this sequence owns no ready mappings.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.executables.is_empty()
    }

    /// Returns the number of ready mappings retained by this sequence.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.executables.len()
    }
}

impl<E> NativeExecutableSequenceLoadFailure<E> {
    /// Returns aggregate cleanup failure for already loaded prefix mappings.
    #[must_use]
    pub const fn cleanup_failure(
        &self,
    ) -> Option<&NativeExecutableSequenceReleaseFailure<E>> {
        match &self.cleanup_failure {
            Some(failure) => Some(failure),
            None => None,
        }
    }

    /// Returns loader-ready image derivation failure, when applicable.
    #[must_use]
    pub fn image_error(&self) -> Option<VerifiedDirectLoadError> {
        match &self.cause {
            NativeExecutableSequenceLoadFailureCause::Load(_) => None,
            NativeExecutableSequenceLoadFailureCause::Image(error) => {
                Some(**error)
            },
        }
    }

    /// Returns the zero-based sequence position whose load failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Consumes this failure and returns retryable prefix cleanup state.
    #[must_use]
    pub fn into_cleanup_failure(
        self,
    ) -> Option<NativeExecutableSequenceReleaseFailure<E>> {
        self.cleanup_failure.map(|failure| *failure)
    }

    /// Returns platform load failure, when image derivation succeeded.
    #[must_use]
    pub const fn load_failure(
        &self,
    ) -> Option<&NativeExecutableLoadFailure<E>> {
        match &self.cause {
            NativeExecutableSequenceLoadFailureCause::Image(_) => None,
            NativeExecutableSequenceLoadFailureCause::Load(error) => {
                Some(error)
            },
        }
    }

    /// Returns the number of mappings ready before the failed position.
    #[must_use]
    pub const fn loaded_count(&self) -> usize {
        self.loaded_count
    }
}

impl<E> NativeExecutableSequenceReleaseFailure<E> {
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

    /// Returns all failed releases retaining exact executable ownership.
    #[must_use]
    pub fn failures(&self) -> &[NativeExecutableReleaseFailure<E>] {
        &self.failures
    }

    /// Returns the number of mappings released by this pass.
    #[must_use]
    pub const fn released_count(&self) -> usize {
        self.released_count
    }

    /// Retries every still-owned mapping and retains only repeated failures.
    ///
    /// # Errors
    ///
    /// Returns another aggregate failure when at least one release still fails.
    pub fn retry<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> NativeExecutableSequenceReleaseResult<E>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = E>,
    {
        retry_release_failures(adapter, self.failures)
    }
}

impl<E: Display> Display for NativeExecutableSequenceLoadFailure<E> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "native sequence load failed at step {}: ", self.index)?;
        match &self.cause {
            NativeExecutableSequenceLoadFailureCause::Image(error) => {
                write!(f, "image: {error}")?;
            },
            NativeExecutableSequenceLoadFailureCause::Load(error) => {
                write!(f, "platform: {error}")?;
            },
        }
        if self.cleanup_failure.is_some() {
            f.write_str("; prefix cleanup also failed")?;
        }
        Ok(())
    }
}

impl<E: Display> Display for NativeExecutableSequenceReleaseFailure<E> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(
            f,
            "native sequence release retained {} of {} mappings",
            self.failed_count(),
            self.attempted_count
        )
    }
}

/// Loads every mapping for one cache-aware verified sequence before execution.
///
/// # Errors
///
/// Returns [`NativeExecutableSequenceLoadFailure`] when image derivation or one
/// platform load fails. Any ready prefix is released in reverse order.
pub fn load_cached_verified_native_sequence<Adapter>(
    adapter: &mut Adapter,
    plan: &CachedVerifiedDirectSequencePlan,
) -> NativeExecutableSequenceLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let artifacts = plan
        .artifacts()
        .iter()
        .map(AsRef::as_ref)
        .collect::<Vec<_>>();
    load_artifact_sequence(adapter, &artifacts)
}

/// Loads every mapping for one uncached verified sequence before execution.
///
/// # Errors
///
/// Returns [`NativeExecutableSequenceLoadFailure`] when image derivation or one
/// platform load fails. Any ready prefix is released in reverse order.
pub fn load_verified_native_sequence<Adapter>(
    adapter: &mut Adapter,
    plan: &VerifiedDirectSequencePlan,
) -> NativeExecutableSequenceLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let artifacts = plan.artifacts().iter().collect::<Vec<_>>();
    load_artifact_sequence(adapter, &artifacts)
}

/// Releases all mappings in reverse semantic order.
///
/// Every mapping is attempted even after an earlier release failure. Failed
/// mappings remain owned by the returned aggregate failure for exact retry.
///
/// # Errors
///
/// Returns [`NativeExecutableSequenceReleaseFailure`] when at least one mapping
/// remains owned after the release pass.
pub fn release_native_executable_sequence<Adapter>(
    adapter: &mut Adapter,
    sequence: ReadyNativeExecutableSequence,
) -> NativeExecutableSequenceReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    release_executables(adapter, sequence.executables)
}

fn load_artifact_sequence<Adapter>(
    adapter: &mut Adapter,
    artifacts: &[&VerifiedDirectNativeArtifact],
) -> NativeExecutableSequenceLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let images = derive_sequence_images(artifacts)?;
    load_sequence_images(adapter, &images)
}

fn derive_sequence_images<E>(
    artifacts: &[&VerifiedDirectNativeArtifact],
) -> DerivedSequenceImagesResult<E> {
    artifacts
        .iter()
        .enumerate()
        .map(|(index, artifact)| {
            VerifiedDirectLoadImage::new(artifact).map_err(|error| {
                Box::new(NativeExecutableSequenceLoadFailure {
                    cause: NativeExecutableSequenceLoadFailureCause::Image(
                        Box::new(error),
                    ),
                    cleanup_failure: None,
                    index,
                    loaded_count: 0,
                })
            })
        })
        .collect()
}

fn load_sequence_images<Adapter>(
    adapter: &mut Adapter,
    images: &[VerifiedDirectLoadImage],
) -> NativeExecutableSequenceLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut executables = Vec::with_capacity(images.len());
    for (index, image) in images.iter().enumerate() {
        match load_native_executable(adapter, image) {
            Ok(executable) => executables.push(executable),
            Err(error) => {
                let loaded_count = executables.len();
                return Err(Box::new(sequence_load_failure(
                    adapter,
                    NativeSequenceLoadFailureContext {
                        cause: NativeExecutableSequenceLoadFailureCause::Load(
                            Box::new(error),
                        ),
                        executables,
                        index,
                        loaded_count,
                    },
                )));
            },
        }
    }
    Ok(ReadyNativeExecutableSequence { executables })
}

fn sequence_load_failure<Adapter>(
    adapter: &mut Adapter,
    context: NativeSequenceLoadFailureContext<Adapter::Error>,
) -> NativeExecutableSequenceLoadFailure<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let cleanup_failure =
        release_executables(adapter, context.executables).err();
    NativeExecutableSequenceLoadFailure {
        cause: context.cause,
        cleanup_failure,
        index: context.index,
        loaded_count: context.loaded_count,
    }
}

fn release_executables<Adapter>(
    adapter: &mut Adapter,
    executables: Vec<ReadyNativeExecutable>,
) -> NativeExecutableSequenceReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let attempted_count = executables.len();
    let mut failures = Vec::new();
    let mut released_count = 0usize;
    for executable in executables.into_iter().rev() {
        match release_native_executable(adapter, executable) {
            Ok(()) => {
                released_count = released_count.saturating_add(1);
            },
            Err(failure) => failures.push(failure),
        }
    }
    release_pass_result(attempted_count, released_count, failures)
}

fn retry_release_failures<Adapter>(
    adapter: &mut Adapter,
    pending: Vec<NativeExecutableReleaseFailure<Adapter::Error>>,
) -> NativeExecutableSequenceReleaseResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let attempted_count = pending.len();
    let mut failures = Vec::new();
    let mut released_count = 0usize;
    for failure in pending {
        match failure.retry(adapter) {
            Ok(()) => {
                released_count = released_count.saturating_add(1);
            },
            Err(retry_failure) => failures.push(retry_failure),
        }
    }
    release_pass_result(attempted_count, released_count, failures)
}

fn release_pass_result<E>(
    attempted_count: usize,
    released_count: usize,
    failures: Vec<NativeExecutableReleaseFailure<E>>,
) -> NativeExecutableSequenceReleaseResult<E> {
    if failures.is_empty() {
        Ok(())
    } else {
        Err(Box::new(NativeExecutableSequenceReleaseFailure {
            attempted_count,
            failures,
            released_count,
        }))
    }
}
