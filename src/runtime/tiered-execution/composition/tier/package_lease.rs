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
//   - One filesystem coordination domain spanning durable package-lease owner
//     transitions, lease snapshot capture, package verification, and
//     reclamation.
// - Must-Not:
//   - Choose lease storage paths, generate owner identities, infer revision
//     chronology, expire leases, or schedule cleanup.
// - Allows:
//   - Inputs: one shared coordinator, caller-selected lease/package stores,
//     bounded owner transitions, restore authority, and guarded snapshots.
//   - Outputs: exact durable lease transition or package reclamation evidence.
//   - Side effects: exclusive lock acquisition, bounded lease CAS publication,
//     package reads, caller-owned snapshot reads, and optional reclamation.
// - Split-When:
//   - Temporal scheduling or non-filesystem distributed coordination gains
//     independent authority.
// - Merge-When:
//   - A package lifecycle owner subsumes this exact guarded transaction domain.
// - Summary:
//   - Coordinates durable package lease owners with generation cleanup.
// - Description:
//   - Lease publication and cleanup use the same non-nesting advisory-lock
//     domain; current package authority is reverified before deletion.
// - Usage:
//   - Configure package and per-revision lease stores with the same
//     coordinator, use guarded acquire/release, and capture snapshots during
//     guarded cleanup.
// - Defaults:
//   - Missing package performs no snapshot capture and no deletion; missing
//     lease state is an empty owner registry.
//

//! Guarded durable package leases and generation reclamation.

use std::num::NonZeroUsize;

use crate::blob_pair_retention::NativeContinuationBlobPairRetention;
use crate::blob_persistence::NativeContinuationBlobPersistenceError;
use crate::blob_store::{
    NativeContinuationBlobConditionalPublication,
    NativeContinuationDurableBlobStore as _,
};
use crate::executable_durable_lease_journal::{
    NativeExecutableDurableLeaseJournalError,
    NativeExecutableDurableLeaseRegistry,
    NativeExecutableDurableLeaseRegistryCapacityError,
    NativeExecutableDurableLeaseTransition,
    NativeExecutableDurableLeaseTransitionError,
    NativeExecutableDurableLeaseTransitionRequest,
    NativeExecutableDurableLeaseTransitionStoreResult,
    decode_executable_durable_lease_registry,
    encode_executable_durable_lease_registry,
};
use crate::file_blob_pair_store::{
    NativeContinuationFileBlobPairReclamation,
    NativeContinuationFileBlobPairReclamationError,
    NativeContinuationFileBlobPairRevision,
    NativeContinuationFileBlobPairStore,
    NativeContinuationFileBlobPairStoreError,
};
use crate::file_blob_store::{
    NativeContinuationFileBlobDurabilityError,
    NativeContinuationFileBlobPrelockedCasRequest,
    NativeContinuationFileBlobStore, NativeContinuationFileBlobStoreError,
};
use crate::file_coordination::{
    NativeContinuationFileCoordination,
    NativeContinuationFileCoordinationError,
    NativeContinuationFileExclusiveGuard,
};
use crate::register_masked_aot_package_persistence::{
    RegisterMaskedAotPackageLeaseSnapshot, RegisterMaskedAotPackageReclamation,
    RegisterMaskedAotPackageRestoreError,
    RegisterMaskedAotPackageRestoreRequest,
    verify_register_masked_aot_package_bytes,
};

struct FileAotPackageLeasePublication {
    expected_bytes: Option<Vec<u8>>,
    replacement: NativeExecutableDurableLeaseRegistry,
    replacement_bytes: Vec<u8>,
    request: NativeExecutableDurableLeaseTransitionRequest,
}

type FileAotPackageLeaseRestoreResult = Result<
    Option<NativeExecutableDurableLeaseRegistry>,
    NativeExecutableDurableLeaseTransitionError<
        NativeContinuationFileBlobStoreError,
    >,
>;

/// Why one coordinated package reclamation pass failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotPackageCoordinatedReclamationError<
    'requirement,
    SnapshotError,
> {
    /// Acquiring the shared filesystem coordination guard failed.
    Coordination(NativeContinuationFileCoordinationError),
    /// Current package bytes failed semantic reverification before cleanup.
    Package(
        RegisterMaskedAotPackageRestoreError<
            'requirement,
            NativeContinuationFileBlobPairStoreError,
        >,
    ),
    /// Current package loading failed under the held guard.
    Pair(NativeContinuationFileBlobPairStoreError),
    /// Pair reclamation failed before cleanup could proceed.
    Reclamation(NativeContinuationFileBlobPairReclamationError),
    /// Caller snapshot capture failed while the guard was held.
    Snapshot(SnapshotError),
}

/// Why one guarded durable package lease transition failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotPackageLeaseTransitionError {
    /// Acquiring the package coordination guard failed.
    Coordination(NativeContinuationFileCoordinationError),
    /// Bounded lease journal transition failed under the held guard.
    Lease(
        NativeExecutableDurableLeaseTransitionError<
            NativeContinuationFileBlobStoreError,
        >,
    ),
}

/// Coordinated package reclamation result specialized to filesystem storage.
pub type RegisterMaskedAotPackageCoordinatedReclamationResult<
    'requirement,
    SnapshotError,
> = Result<
    RegisterMaskedAotPackageReclamation<
        NativeContinuationFileBlobPairRevision,
        NativeContinuationFileBlobPairReclamation,
    >,
    RegisterMaskedAotPackageCoordinatedReclamationError<
        'requirement,
        SnapshotError,
    >,
>;

/// One package-revision lease snapshot captured under filesystem coordination.
pub type RegisterMaskedAotPackageLeaseSnapshotResult = Result<
    RegisterMaskedAotPackageLeaseSnapshot<
        NativeContinuationFileBlobPairRevision,
    >,
    NativeExecutableDurableLeaseJournalError<
        NativeContinuationFileBlobStoreError,
    >,
>;

/// Guarded durable lease transition specialized to filesystem storage.
pub type RegisterMaskedAotPackageLeaseTransitionResult = Result<
    NativeExecutableDurableLeaseTransition<
        NativeContinuationFileBlobDurabilityError,
    >,
    RegisterMaskedAotPackageLeaseTransitionError,
>;

/// Acquires one durable package lease owner under the shared package guard.
///
/// The lease store must be configured with the same coordination identity as
/// `coordination`; mismatch fails before mutation. The held guard is reused by
/// bounded load and CAS, so this path never recursively acquires the lock.
///
/// # Errors
///
/// Returns coordination, bounded journal, codec, capacity, or filesystem
/// failure. Post-publication durability failure remains typed committed state.
pub fn acquire_file_aot_package_durable_lease(
    coordination: &NativeContinuationFileCoordination,
    lease: &mut NativeContinuationFileBlobStore,
    request: NativeExecutableDurableLeaseTransitionRequest,
) -> RegisterMaskedAotPackageLeaseTransitionResult {
    use RegisterMaskedAotPackageLeaseTransitionError as Error;

    let guard = coordination
        .acquire_exclusive()
        .map_err(Error::Coordination)?;
    transition_file_aot_package_durable_lease_prelocked(
        lease,
        &guard,
        request,
        |registry, transition| {
            registry.acquire(
                transition.owner(),
                transition.decode_limits().maximum_owners(),
            )
        },
    )
    .map_err(Error::Lease)
}

/// Captures one exact package-revision lease snapshot under an existing guard.
///
/// Missing durable journal state maps to zero owners. Present state is decoded
/// under the supplied owner and byte bounds before its exact cardinality is
/// exposed to package reclamation policy.
///
/// # Errors
///
/// Returns guard mismatch, bounded filesystem read, or canonical decode
/// failure.
pub fn capture_file_aot_package_lease_snapshot(
    lease: &NativeContinuationFileBlobStore,
    guard: &NativeContinuationFileExclusiveGuard,
    revision: NativeContinuationFileBlobPairRevision,
    request: NativeExecutableDurableLeaseTransitionRequest,
) -> RegisterMaskedAotPackageLeaseSnapshotResult {
    let current = lease
        .load_prelocked(guard, request.maximum_bytes())
        .map_err(|error| {
            NativeExecutableDurableLeaseJournalError::Blob(
                NativeContinuationBlobPersistenceError::Store(error),
            )
        })?;
    let owners = current.map_or(Ok(0), |bytes| {
        decode_executable_durable_lease_registry(
            &bytes,
            request.decode_limits(),
        )
        .map(|registry| registry.len())
        .map_err(NativeExecutableDurableLeaseJournalError::Codec)
    })?;
    Ok(RegisterMaskedAotPackageLeaseSnapshot::new(revision, owners))
}

/// Reclaims package generations from lease snapshots captured under one lock.
///
/// The callback executes only after the current package bytes have been loaded
/// and reverified under the same exclusive guard later used for reclamation.
/// Any positive-owner snapshot preserves its exact revision; duplicate
/// revisions collapse by equality. The verified current revision is always
/// preserved.
///
/// # Errors
///
/// Returns coordination, package read/reverification, snapshot capture, or
/// pre-cleanup reclamation failure. Snapshot failure performs no deletion.
pub fn reclaim_file_aot_package_from_lease_snapshot<
    'requirement,
    SnapshotError,
    Capture,
>(
    coordination: &NativeContinuationFileCoordination,
    package: &mut NativeContinuationFileBlobPairStore,
    request: RegisterMaskedAotPackageRestoreRequest<'requirement>,
    capture: Capture,
) -> RegisterMaskedAotPackageCoordinatedReclamationResult<
    'requirement,
    SnapshotError,
>
where
    Capture: FnOnce(
        &NativeContinuationFileExclusiveGuard,
    ) -> Result<
        Vec<
            RegisterMaskedAotPackageLeaseSnapshot<
                NativeContinuationFileBlobPairRevision,
            >,
        >,
        SnapshotError,
    >,
{
    use RegisterMaskedAotPackageCoordinatedReclamationError as Error;

    let guard = coordination
        .acquire_exclusive()
        .map_err(Error::Coordination)?;
    let (graph_maximum_bytes, bundle_maximum_bytes) =
        request.member_maximum_bytes();
    let Some(current) = package
        .load_pair_versioned_prelocked(
            &guard,
            graph_maximum_bytes,
            bundle_maximum_bytes,
        )
        .map_err(Error::Pair)?
    else {
        return Ok(RegisterMaskedAotPackageReclamation::Missing);
    };
    let _verified = verify_register_masked_aot_package_bytes::<
        NativeContinuationFileBlobPairStoreError,
    >(&current.pair.first, &current.pair.second, request)
    .map_err(Error::Package)?;
    let snapshots = capture(&guard).map_err(Error::Snapshot)?;
    let mut retention = NativeContinuationBlobPairRetention::new();
    for snapshot in snapshots {
        if snapshot.owners() > 0 {
            let _retained = retention.retain(*snapshot.revision());
        }
    }
    let retained_revisions = retention.revisions().len();
    if !retention.revisions().contains(&current.revision) {
        let _current = retention.retain(current.revision);
    }
    let reclamation = package
        .reclaim_generations_preserving_prelocked(&guard, retention.revisions())
        .map_err(Error::Reclamation)?;
    Ok(RegisterMaskedAotPackageReclamation::Reclaimed {
        current_revision: current.revision,
        reclamation,
        retained_revisions,
    })
}

/// Releases one durable package lease owner under the shared package guard.
///
/// Missing state and absent membership remain idempotent. Last-owner release
/// publishes an explicit empty registry so guarded cleanup can observe zero
/// owners before optional journal reclamation.
///
/// # Errors
///
/// Returns coordination, bounded journal, codec, or filesystem failure.
/// Post-publication durability failure remains typed committed state.
pub fn release_file_aot_package_durable_lease(
    coordination: &NativeContinuationFileCoordination,
    lease: &mut NativeContinuationFileBlobStore,
    request: NativeExecutableDurableLeaseTransitionRequest,
) -> RegisterMaskedAotPackageLeaseTransitionResult {
    use RegisterMaskedAotPackageLeaseTransitionError as Error;

    let guard = coordination
        .acquire_exclusive()
        .map_err(Error::Coordination)?;
    transition_file_aot_package_durable_lease_prelocked(
        lease,
        &guard,
        request,
        |registry, transition| Ok(registry.release(transition.owner())),
    )
    .map_err(Error::Lease)
}

fn restore_file_aot_package_lease_registry_prelocked(
    lease: &NativeContinuationFileBlobStore,
    guard: &NativeContinuationFileExclusiveGuard,
    request: NativeExecutableDurableLeaseTransitionRequest,
) -> FileAotPackageLeaseRestoreResult {
    use NativeExecutableDurableLeaseJournalError as JournalError;
    use NativeExecutableDurableLeaseTransitionError as TransitionError;

    let loaded_bytes = lease
        .load_prelocked(guard, request.maximum_bytes())
        .map_err(|error| {
            TransitionError::Journal(JournalError::Blob(
                NativeContinuationBlobPersistenceError::Store(error),
            ))
        })?;
    loaded_bytes
        .as_deref()
        .map(|bytes| {
            decode_executable_durable_lease_registry(
                bytes,
                request.decode_limits(),
            )
        })
        .transpose()
        .map_err(|error| TransitionError::Journal(JournalError::Codec(error)))
}

fn transition_file_aot_package_durable_lease_prelocked<Mutate>(
    lease: &mut NativeContinuationFileBlobStore,
    guard: &NativeContinuationFileExclusiveGuard,
    request: NativeExecutableDurableLeaseTransitionRequest,
    mutate: Mutate,
) -> NativeExecutableDurableLeaseTransitionStoreResult<
    NativeContinuationFileBlobStore,
>
where
    Mutate: FnOnce(
        &mut NativeExecutableDurableLeaseRegistry,
        NativeExecutableDurableLeaseTransitionRequest,
    ) -> Result<
        bool,
        NativeExecutableDurableLeaseRegistryCapacityError,
    >,
{
    use NativeExecutableDurableLeaseJournalError as JournalError;
    use NativeExecutableDurableLeaseTransition as Transition;
    use NativeExecutableDurableLeaseTransitionError as TransitionError;

    let expected = restore_file_aot_package_lease_registry_prelocked(
        lease, guard, request,
    )?;
    let mut replacement = expected.clone().unwrap_or_default();
    let changed =
        mutate(&mut replacement, request).map_err(TransitionError::Capacity)?;
    if !changed {
        return Ok(Transition::Unchanged { current: expected });
    }
    let expected_bytes = expected
        .as_ref()
        .map(encode_executable_durable_lease_registry)
        .transpose()
        .map_err(|error| {
            TransitionError::Journal(JournalError::Codec(error))
        })?;
    let replacement_bytes = encode_executable_durable_lease_registry(
        &replacement,
    )
    .map_err(|error| TransitionError::Journal(JournalError::Codec(error)))?;
    if let Some(bytes) = &expected_bytes {
        validate_file_aot_package_lease_bytes(bytes, request.maximum_bytes())?;
    }
    validate_file_aot_package_lease_bytes(
        &replacement_bytes,
        request.maximum_bytes(),
    )?;
    transition_file_aot_package_durable_lease_publication(
        lease,
        guard,
        FileAotPackageLeasePublication {
            expected_bytes,
            replacement,
            replacement_bytes,
            request,
        },
    )
}

fn transition_file_aot_package_durable_lease_publication(
    lease: &mut NativeContinuationFileBlobStore,
    guard: &NativeContinuationFileExclusiveGuard,
    publication: FileAotPackageLeasePublication,
) -> NativeExecutableDurableLeaseTransitionStoreResult<
    NativeContinuationFileBlobStore,
> {
    use NativeExecutableDurableLeaseJournalError as JournalError;
    use NativeExecutableDurableLeaseTransition as Transition;
    use NativeExecutableDurableLeaseTransitionError as TransitionError;

    let outcome = lease
        .compare_and_swap_prelocked(
            guard,
            NativeContinuationFileBlobPrelockedCasRequest::new(
                publication.expected_bytes.as_deref(),
                &publication.replacement_bytes,
                publication.request.maximum_bytes(),
            ),
        )
        .map_err(|error| {
            TransitionError::Journal(JournalError::Blob(
                NativeContinuationBlobPersistenceError::Store(error),
            ))
        })?;
    match outcome {
        NativeContinuationBlobConditionalPublication::Conflict {
            current: conflict_bytes,
        } => {
            let conflict_registry = conflict_bytes
                .as_deref()
                .map(|bytes| {
                    decode_executable_durable_lease_registry(
                        bytes,
                        publication.request.decode_limits(),
                    )
                })
                .transpose()
                .map_err(|error| {
                    TransitionError::Journal(JournalError::Codec(error))
                })?;
            Ok(Transition::Conflict {
                current: conflict_registry,
            })
        },
        NativeContinuationBlobConditionalPublication::Published => {
            let bytes = publication.replacement_bytes.len();
            match lease.confirm_durability() {
                Ok(()) => Ok(Transition::Durable {
                    bytes,
                    registry: publication.replacement,
                }),
                Err(durability_error) => Ok(Transition::Published {
                    bytes,
                    durability_error,
                    registry: publication.replacement,
                }),
            }
        },
    }
}

const fn validate_file_aot_package_lease_bytes(
    bytes: &[u8],
    maximum_bytes: NonZeroUsize,
) -> Result<
    (),
    NativeExecutableDurableLeaseTransitionError<
        NativeContinuationFileBlobStoreError,
    >,
> {
    if bytes.len() <= maximum_bytes.get() {
        Ok(())
    } else {
        Err(NativeExecutableDurableLeaseTransitionError::Journal(
            NativeExecutableDurableLeaseJournalError::Blob(
                NativeContinuationBlobPersistenceError::ByteLimit {
                    maximum_bytes,
                    observed_bytes: bytes.len(),
                },
            ),
        ))
    }
}
