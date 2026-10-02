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
//   - One filesystem coordination guard spanning package verification, lease
//     snapshot capture, and exact generation reclamation.
// - Must-Not:
//   - Choose lease storage, generate owners, infer revision chronology, expire
//     leases, or schedule cleanup.
// - Allows:
//   - Inputs: one shared coordinator, package pair store, restore authority,
//     and one caller snapshot callback executed under the exclusive guard.
//   - Outputs: missing-package no-op or exact package reclamation evidence.
//   - Side effects: one exclusive lock, one package read, callback-owned
//     guarded reads, and one optional pair reclamation pass.
// - Split-When:
//   - Lease acquisition/publication or temporal scheduling gains authority.
// - Merge-When:
//   - A package lifecycle owner subsumes this exact guarded cleanup
//     transaction.
// - Summary:
//   - Reclaims package generations from lease evidence captured under one lock.
// - Description:
//   - Current package authority is reverified before snapshots can authorize
//     deletion; current revision remains preserved regardless of snapshots.
// - Usage:
//   - Configure participating filesystem adapters with the same coordinator.
// - Defaults:
//   - Missing package performs no snapshot capture and no deletion.
//

//! Guarded package reclamation from caller-captured durable lease snapshots.

use crate::blob_pair_retention::NativeContinuationBlobPairRetention;
use crate::file_blob_pair_store::{
    NativeContinuationFileBlobPairReclamation,
    NativeContinuationFileBlobPairReclamationError,
    NativeContinuationFileBlobPairRevision,
    NativeContinuationFileBlobPairStore,
    NativeContinuationFileBlobPairStoreError,
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
