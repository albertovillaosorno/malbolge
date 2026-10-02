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
//   - Atomic durable publication/restoration of reduced-graph provenance with
//     its complete register-masked AOT bundle, plus explicit exact-revision
//     generation reclamation.
// - Must-Not:
//   - Choose storage paths, trust persisted graph/object authority, publish one
//     member independently, load executable memory, infer revision chronology,
//     or choose automatic retention/eviction policy.
// - Allows:
//   - Inputs: exact graph claim, graph-ordered programs, sealed AOT set,
//     runtime/host assumptions, decode limits, and independent positive bounds.
//   - Outputs: atomic publication, reverified versioned package authority, or
//     exact adapter-owned generation-reclamation evidence.
//   - Side effects: delegated through bounded atomic pair persistence/reclaim.
// - Split-When:
//   - Package migration, temporal retention scheduling, cross-resource lease
//     coordination, or executable residency gains independent authority.
// - Merge-When:
//   - One general durable native-cache package owner subsumes this pair.
// - Summary:
//   - Keeps graph/native generations atomic and reclaims only explicitly safe
//     superseded revisions.
// - Description:
//   - Both canonical payloads are prepared before commit. Versioned restore
//     exposes revision identity only after verification, and reclamation first
//     protects the package revision it just reverified.
// - Usage:
//   - Persist/restore exact graph+AOT packages, retain verified or durably
//     leased revisions, and explicitly reclaim unretained superseded
//     generations.
// - Defaults:
//   - Missing pair state is explicit; any graph/program/object drift fails
//     closed without partial authority.
//

//! Atomic durable package for reduced graph provenance plus its AOT bundle.

use std::num::NonZeroUsize;

use malbolge::RegisterMaskedRegionEffectProgram;
use pair_port::{
    NativeContinuationBlobPairStore as PairStore,
    NativeContinuationConditionalBlobPairStore as ConditionalPairStore,
    NativeContinuationDurableBlobPairStore as DurablePairStore,
    NativeContinuationReclaimableBlobPairStore as ReclaimablePairStore,
};

use crate::blob_pair_retention::NativeContinuationBlobPairRetention;
use crate::execution_native::{
    AheadOfExecutionRegisterMaskedReducedStateGraphCodecError,
    AheadOfExecutionRegisterMaskedReducedStateGraphDecodeLimits,
    UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
    VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
    VerifiedAheadOfExecutionRegisterMaskedSet,
    decode_ahead_of_execution_register_masked_reduced_state_graph,
    encode_ahead_of_execution_register_masked_reduced_state_graph,
};
use crate::register_masked_aot_bundle_persistence::{
    RegisterMaskedAotBundlePersistRequest,
    RegisterMaskedAotBundlePersistenceLoad,
    RegisterMaskedAotBundlePreparationError,
    RegisterMaskedAotBundleRestorePersistenceError,
    RegisterMaskedAotBundleRestoreRequest, RegisterMaskedAotBundleSource,
    decode_register_masked_aot_bundle, encode_register_masked_aot_bundle,
};
use crate::{
    blob_pair_persistence as pair_persistence,
    blob_pair_reclamation as pair_reclamation, blob_pair_store as pair_port,
};

type PackageGraphClaim =
    UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph;
type PackageGraphDecodeLimits =
    AheadOfExecutionRegisterMaskedReducedStateGraphDecodeLimits;
type PairConditionalDurable<Revision, DurabilityError> =
    pair_persistence::NativeContinuationBlobPairConditionalDurablePersistence<
        Revision,
        DurabilityError,
    >;

/// Exact source authority for one graph-plus-native package publication.
#[derive(Clone, Copy, Debug)]
pub struct RegisterMaskedAotPackageSource<'requirement> {
    bundle: RegisterMaskedAotBundleSource<'requirement>,
    claim: &'requirement PackageGraphClaim,
}

/// Bounded request for one atomic graph-plus-native package publication.
#[derive(Clone, Copy, Debug)]
pub struct RegisterMaskedAotPackagePersistRequest<'requirement> {
    bundle_maximum_bytes: NonZeroUsize,
    graph_maximum_bytes: NonZeroUsize,
    source: RegisterMaskedAotPackageSource<'requirement>,
}

/// Caller authority required to restore one atomic graph-plus-native package.
#[derive(Clone, Copy, Debug)]
pub struct RegisterMaskedAotPackageRestoreRequest<'requirement> {
    bundle: RegisterMaskedAotBundleRestoreRequest<'requirement>,
    decode_limits: PackageGraphDecodeLimits,
    graph_maximum_bytes: NonZeroUsize,
}

/// One caller-coordinated durable lease snapshot for a package revision.
#[derive(Clone, Copy, Debug)]
pub struct RegisterMaskedAotPackageLeaseSnapshot<Revision> {
    owners: usize,
    revision: Revision,
}

/// Slice of caller-coordinated package lease snapshots for one cleanup pass.
pub type RegisterMaskedAotPackageLeaseSnapshots<Revision> =
    [RegisterMaskedAotPackageLeaseSnapshot<Revision>];

impl<Revision> RegisterMaskedAotPackageLeaseSnapshot<Revision> {
    /// Binds one exact package revision to its durable lease-owner count.
    #[must_use]
    pub const fn new(revision: Revision, owners: usize) -> Self {
        Self { owners, revision }
    }

    /// Returns the exact durable owner count captured for this revision.
    #[must_use]
    pub const fn owners(&self) -> usize {
        self.owners
    }

    /// Borrows the exact opaque package revision captured by this snapshot.
    #[must_use]
    pub const fn revision(&self) -> &Revision {
        &self.revision
    }
}

/// Why graph topology and the supplied ordered program list disagreed.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotPackageProgramError {
    /// Admitted graph and caller-owned program counts differ.
    Count {
        /// Exact admitted graph node count.
        graph: usize,
        /// Exact caller-owned program count.
        programs: usize,
    },
    /// One graph node program differs from the same ordered caller program.
    Mismatch {
        /// Zero-based mismatching graph/program index.
        index: usize,
    },
}

/// Why one atomic package could not be prepared before publication.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotPackagePreparationError<'requirement> {
    /// Complete native bundle preparation failed before publication.
    Bundle(Box<RegisterMaskedAotBundlePreparationError<'requirement>>),
    /// Graph claim failed canonical encoding or replay admission.
    Graph(AheadOfExecutionRegisterMaskedReducedStateGraphCodecError),
    /// Graph-derived program order disagreed with package object order.
    Programs(RegisterMaskedAotPackageProgramError),
}

/// Why one package publication failed before or after pair commit.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotPackageStoreError<'requirement, StoreError> {
    /// Atomic pair storage rejected the prepared payloads.
    Pair(
        pair_persistence::NativeContinuationBlobPairPersistenceError<
            StoreError,
        >,
    ),
    /// One payload could not be prepared without mutation.
    Preparation(Box<RegisterMaskedAotPackagePreparationError<'requirement>>),
}

/// Why one atomic package restore failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotPackageRestoreError<'requirement, StoreError> {
    /// Persisted object bundle failed framing or current native verification.
    Bundle(
        Box<
            RegisterMaskedAotBundleRestorePersistenceError<
                'requirement,
                StoreError,
            >,
        >,
    ),
    /// Direct bundle decoding unexpectedly produced a missing-storage outcome.
    BundleMissing,
    /// Persisted graph provenance failed replay/canonical admission.
    Graph(AheadOfExecutionRegisterMaskedReducedStateGraphCodecError),
    /// Atomic pair loading or independent member bounds failed.
    Pair(
        pair_persistence::NativeContinuationBlobPairPersistenceError<
            StoreError,
        >,
    ),
    /// Restored graph order disagreed with caller-owned expected programs.
    Programs(RegisterMaskedAotPackageProgramError),
}

/// Durable outcome of one revision-conditional package publication.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotPackageConditionalDurablePersistence<
    Revision,
    DurabilityError,
> {
    /// Expected revision differed; no package publication occurred.
    Conflict,
    /// Conditional package publication and durability confirmation completed.
    Durable {
        /// Fresh adapter-owned revision assigned to the committed package.
        revision: Revision,
        /// Exact committed member byte counts.
        write: pair_persistence::NativeContinuationBlobPairPersistenceWrite,
    },
    /// Package publication committed, then durability confirmation failed.
    Published {
        /// Exact post-publication durability failure.
        durability_error: DurabilityError,
        /// Fresh adapter-owned revision assigned to the committed package.
        revision: Revision,
        /// Exact committed member byte counts.
        write: pair_persistence::NativeContinuationBlobPairPersistenceWrite,
    },
}

/// Result of one bounded atomic package restoration.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotPackagePersistenceLoad {
    /// No atomically published graph/object package exists.
    Missing,
    /// Both members independently rebuilt current authority.
    Restored {
        /// Exact AOT bundle byte count loaded from the atomic pair.
        bundle_bytes: usize,
        /// Freshly replay-verified reduced graph.
        graph: VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
        /// Exact graph provenance byte count loaded from the atomic pair.
        graph_bytes: usize,
        /// Exact object count independently reverified from the bundle.
        objects: usize,
        /// Fresh sealed AOT set rebuilt only after complete object
        /// verification.
        set: VerifiedAheadOfExecutionRegisterMaskedSet,
    },
}

/// Result of one bounded versioned atomic package restoration.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotPackageVersionedPersistenceLoad<Revision> {
    /// No atomically published graph/object package exists.
    Missing,
    /// Both members independently rebuilt current authority at one revision.
    Restored {
        /// Exact AOT bundle byte count loaded from the atomic pair.
        bundle_bytes: usize,
        /// Freshly replay-verified reduced graph.
        graph: VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
        /// Exact graph provenance byte count loaded from the atomic pair.
        graph_bytes: usize,
        /// Exact object count independently reverified from the bundle.
        objects: usize,
        /// Opaque adapter-owned publication revision verified with this
        /// package.
        revision: Revision,
        /// Fresh sealed AOT set rebuilt only after complete object
        /// verification.
        set: VerifiedAheadOfExecutionRegisterMaskedSet,
    },
}

/// Result of one package-aware generation reclamation pass.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotPackageReclamation<Revision, Reclamation> {
    /// No current package exists, so no generation deletion was attempted.
    Missing,
    /// A current package was reverified before explicit reclamation.
    Reclaimed {
        /// Exact verified revision retained across the reclamation call.
        current_revision: Revision,
        /// Adapter-owned reclamation evidence.
        reclamation: Reclamation,
        /// Caller-selected exact retained revision count.
        retained_revisions: usize,
    },
}

/// Why package-aware generation reclamation failed closed.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedAotPackageReclamationError<
    'requirement,
    StoreError,
    ReclamationError,
> {
    /// Pair generation reclamation failed before cleanup could proceed.
    Reclamation(ReclamationError),
    /// Current package bytes failed bounded restore or semantic reverification.
    Restore(RegisterMaskedAotPackageRestoreError<'requirement, StoreError>),
}

/// Conditional durable package result specialized to one pair store.
pub type RegisterMaskedAotPackageConditionalDurableStoreResult<
    'requirement,
    Store,
> = Result<
    RegisterMaskedAotPackageConditionalDurablePersistence<
        <Store as ConditionalPairStore>::Revision,
        <Store as DurablePairStore>::DurabilityError,
    >,
    RegisterMaskedAotPackageStoreError<
        'requirement,
        <Store as PairStore>::Error,
    >,
>;

/// Durable package publication result specialized to one pair store.
pub type RegisterMaskedAotPackageDurableStoreResult<'requirement, Store> =
    Result<
        pair_persistence::NativeContinuationBlobPairDurablePersistence<
            <Store as DurablePairStore>::DurabilityError,
        >,
        RegisterMaskedAotPackageStoreError<
            'requirement,
            <Store as PairStore>::Error,
        >,
    >;

/// Package restore result specialized to one pair store.
pub type RegisterMaskedAotPackageRestoreStoreResult<'requirement, Store> =
    Result<
        RegisterMaskedAotPackagePersistenceLoad,
        RegisterMaskedAotPackageRestoreError<
            'requirement,
            <Store as PairStore>::Error,
        >,
    >;

/// Package-aware reclamation result specialized to one pair store.
pub type RegisterMaskedAotPackageReclamationStoreResult<'requirement, Store> =
    Result<
        RegisterMaskedAotPackageReclamation<
            <Store as ConditionalPairStore>::Revision,
            <Store as ReclaimablePairStore>::Reclamation,
        >,
        RegisterMaskedAotPackageReclamationError<
            'requirement,
            <Store as PairStore>::Error,
            <Store as ReclaimablePairStore>::ReclamationError,
        >,
    >;

/// Versioned package restore result specialized to one pair store.
pub type RegisterMaskedAotPackageVersionedStoreResult<'requirement, Store> =
    Result<
        RegisterMaskedAotPackageVersionedPersistenceLoad<
            <Store as ConditionalPairStore>::Revision,
        >,
        RegisterMaskedAotPackageRestoreError<
            'requirement,
            <Store as PairStore>::Error,
        >,
    >;

impl<'requirement> RegisterMaskedAotPackageSource<'requirement> {
    /// Binds graph provenance to one exact complete native bundle source.
    #[must_use]
    pub const fn new(
        claim: &'requirement PackageGraphClaim,
        bundle: RegisterMaskedAotBundleSource<'requirement>,
    ) -> Self {
        Self { bundle, claim }
    }
}

impl<'requirement> RegisterMaskedAotPackagePersistRequest<'requirement> {
    /// Binds package source authority to independent positive member bounds.
    #[must_use]
    pub const fn new(
        source: RegisterMaskedAotPackageSource<'requirement>,
        graph_maximum_bytes: NonZeroUsize,
        bundle_maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            bundle_maximum_bytes,
            graph_maximum_bytes,
            source,
        }
    }
}

impl<'requirement> RegisterMaskedAotPackageRestoreRequest<'requirement> {
    pub(crate) const fn member_maximum_bytes(
        self,
    ) -> (NonZeroUsize, NonZeroUsize) {
        (self.graph_maximum_bytes, self.bundle.maximum_bytes())
    }

    /// Binds bundle restore authority to graph replay and provenance bounds.
    #[must_use]
    pub const fn new(
        bundle: RegisterMaskedAotBundleRestoreRequest<'requirement>,
        decode_limits: PackageGraphDecodeLimits,
        graph_maximum_bytes: NonZeroUsize,
    ) -> Self {
        Self {
            bundle,
            decode_limits,
            graph_maximum_bytes,
        }
    }
}

type PackagePreparationResult<'requirement> = Result<
    (Vec<u8>, Vec<u8>),
    RegisterMaskedAotPackagePreparationError<'requirement>,
>;

fn validate_program_order(
    graph: &VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
    programs: &[RegisterMaskedRegionEffectProgram],
) -> Result<(), RegisterMaskedAotPackageProgramError> {
    if graph.len() != programs.len() {
        return Err(RegisterMaskedAotPackageProgramError::Count {
            graph: graph.len(),
            programs: programs.len(),
        });
    }
    for (index, program) in programs.iter().enumerate() {
        let matches = graph
            .node(index)
            .is_some_and(|node| node.program() == program);
        if !matches {
            return Err(RegisterMaskedAotPackageProgramError::Mismatch {
                index,
            });
        }
    }
    Ok(())
}

fn prepare_package(
    request: RegisterMaskedAotPackagePersistRequest<'_>,
) -> PackagePreparationResult<'_> {
    let graph = request.source.claim.verify().map_err(|error| {
        RegisterMaskedAotPackagePreparationError::Graph(
            AheadOfExecutionRegisterMaskedReducedStateGraphCodecError::Graph(
                error,
            ),
        )
    })?;
    validate_program_order(&graph, request.source.bundle.programs())
        .map_err(RegisterMaskedAotPackagePreparationError::Programs)?;
    let graph_bytes =
        encode_ahead_of_execution_register_masked_reduced_state_graph(
            request.source.claim,
        )
        .map_err(RegisterMaskedAotPackagePreparationError::Graph)?;
    let bundle_bytes = encode_register_masked_aot_bundle(
        RegisterMaskedAotBundlePersistRequest::new(
            request.source.bundle,
            request.bundle_maximum_bytes,
        ),
    )
    .map_err(|error| {
        RegisterMaskedAotPackagePreparationError::Bundle(Box::new(error))
    })?;
    Ok((graph_bytes, bundle_bytes))
}

/// Conditionally publishes one package and returns its exact fresh revision.
///
/// Both members are fully prepared before the pair compare-and-swap. Conflict
/// discards the store's raw current bytes and revision; callers must use typed
/// versioned restore before treating current state as package authority.
///
/// # Errors
///
/// Returns package preparation, byte-limit, or pair-store failure before a
/// typed conflict/publication outcome exists. Post-commit durability failure
/// remains a committed `Published` outcome with the fresh revision.
pub fn compare_and_swap_register_masked_aot_package_durably<
    'requirement,
    Store,
>(
    store: &mut Store,
    expected: Option<&Store::Revision>,
    request: RegisterMaskedAotPackagePersistRequest<'requirement>,
) -> RegisterMaskedAotPackageConditionalDurableStoreResult<'requirement, Store>
where
    Store: ConditionalPairStore + DurablePairStore,
{
    use RegisterMaskedAotPackageConditionalDurablePersistence as Outcome;

    let (graph_bytes, bundle_bytes) =
        prepare_package(request).map_err(|error| {
            RegisterMaskedAotPackageStoreError::Preparation(Box::new(error))
        })?;
    let pair_request =
        pair_persistence::NativeContinuationBlobPairPersistenceRequest::new(
            &graph_bytes,
            &bundle_bytes,
            request.graph_maximum_bytes,
            request.bundle_maximum_bytes,
        );
    let outcome = pair_persistence::compare_and_swap_blob_pair_durably(
        store,
        expected,
        pair_request,
    )
    .map_err(RegisterMaskedAotPackageStoreError::Pair)?;
    match outcome {
        PairConditionalDurable::Conflict { .. } => Ok(Outcome::Conflict),
        PairConditionalDurable::Durable { revision, write } => {
            Ok(Outcome::Durable { revision, write })
        },
        PairConditionalDurable::Published {
            durability_error,
            revision,
            write,
        } => Ok(Outcome::Published {
            durability_error,
            revision,
            write,
        }),
    }
}

/// Atomically publishes graph provenance and its complete AOT bundle durably.
///
/// Both members are fully prepared before the atomic pair store is touched.
/// Therefore graph rejection, program-order drift, or incomplete native
/// coverage preserves the previous package generation exactly.
///
/// # Errors
///
/// Returns preparation or bounded pair-store failure before claiming commit.
/// Post-commit durability failure remains committed `Published` evidence.
pub fn persist_register_masked_aot_package_durably<'requirement, Store>(
    store: &mut Store,
    request: RegisterMaskedAotPackagePersistRequest<'requirement>,
) -> RegisterMaskedAotPackageDurableStoreResult<'requirement, Store>
where
    Store: DurablePairStore,
{
    let (graph_bytes, bundle_bytes) =
        prepare_package(request).map_err(|error| {
            RegisterMaskedAotPackageStoreError::Preparation(Box::new(error))
        })?;
    pair_persistence::persist_blob_pair_durably(
        store,
        pair_persistence::NativeContinuationBlobPairPersistenceRequest::new(
            &graph_bytes,
            &bundle_bytes,
            request.graph_maximum_bytes,
            request.bundle_maximum_bytes,
        ),
    )
    .map_err(RegisterMaskedAotPackageStoreError::Pair)
}

pub(crate) fn verify_register_masked_aot_package_bytes<
    'requirement,
    StoreError,
>(
    graph_bytes: &[u8],
    bundle_bytes: &[u8],
    request: RegisterMaskedAotPackageRestoreRequest<'requirement>,
) -> Result<
    RegisterMaskedAotPackagePersistenceLoad,
    RegisterMaskedAotPackageRestoreError<'requirement, StoreError>,
> {
    let graph = decode_ahead_of_execution_register_masked_reduced_state_graph(
        graph_bytes,
        request.decode_limits,
    )
    .map_err(RegisterMaskedAotPackageRestoreError::Graph)?;
    validate_program_order(&graph, request.bundle.programs())
        .map_err(RegisterMaskedAotPackageRestoreError::Programs)?;
    let bundle = decode_register_masked_aot_bundle::<StoreError>(
        bundle_bytes,
        request.bundle,
    )
    .map_err(|error| {
        RegisterMaskedAotPackageRestoreError::Bundle(Box::new(error))
    })?;
    let RegisterMaskedAotBundlePersistenceLoad::Restored {
        objects, set, ..
    } = bundle
    else {
        return Err(RegisterMaskedAotPackageRestoreError::BundleMissing);
    };
    Ok(RegisterMaskedAotPackagePersistenceLoad::Restored {
        bundle_bytes: bundle_bytes.len(),
        graph,
        graph_bytes: graph_bytes.len(),
        objects,
        set,
    })
}

/// Atomically restores graph provenance and its complete AOT bundle.
///
/// Pair atomicity prevents cross-generation member mixing. The graph is
/// replayed first, its exact ordered programs are compared with caller
/// authority, and every native object is then independently reverified before
/// either restored owner is returned.
///
/// # Errors
///
/// Returns bounded pair load, graph replay, program-order, framing, or native
/// verification failure without exposing partial authority.
pub fn restore_register_masked_aot_package<'requirement, Store>(
    store: &mut Store,
    request: RegisterMaskedAotPackageRestoreRequest<'requirement>,
) -> RegisterMaskedAotPackageRestoreStoreResult<'requirement, Store>
where
    Store: PairStore,
{
    let load = pair_persistence::restore_blob_pair(
        store,
        request.graph_maximum_bytes,
        request.bundle.maximum_bytes(),
    )
    .map_err(RegisterMaskedAotPackageRestoreError::Pair)?;
    let pair_persistence::NativeContinuationBlobPairPersistenceLoad::Present {
        first: graph_bytes,
        second: bundle_bytes,
    } = load
    else {
        return Ok(RegisterMaskedAotPackagePersistenceLoad::Missing);
    };
    verify_register_masked_aot_package_bytes(
        &graph_bytes,
        &bundle_bytes,
        request,
    )
}

/// Restores one package together with its exact opaque publication revision.
///
/// The revision is exposed only after the graph and complete native bundle have
/// rebuilt current authority. Callers may therefore retain only a revision that
/// crossed the same semantic verification boundary as an ordinary restore.
///
/// # Errors
///
/// Returns bounded pair load, graph replay, program-order, framing, or native
/// verification failure without exposing an unverified revision.
pub fn restore_register_masked_aot_package_versioned<'requirement, Store>(
    store: &mut Store,
    request: RegisterMaskedAotPackageRestoreRequest<'requirement>,
) -> RegisterMaskedAotPackageVersionedStoreResult<'requirement, Store>
where
    Store: ConditionalPairStore,
{
    let Some(versioned) = pair_persistence::restore_blob_pair_versioned(
        store,
        request.graph_maximum_bytes,
        request.bundle.maximum_bytes(),
    )
    .map_err(RegisterMaskedAotPackageRestoreError::Pair)?
    else {
        return Ok(RegisterMaskedAotPackageVersionedPersistenceLoad::Missing);
    };
    let restored = verify_register_masked_aot_package_bytes::<Store::Error>(
        &versioned.first,
        &versioned.second,
        request,
    )?;
    let RegisterMaskedAotPackagePersistenceLoad::Restored {
        bundle_bytes,
        graph,
        graph_bytes,
        objects,
        set,
    } = restored
    else {
        return Err(RegisterMaskedAotPackageRestoreError::BundleMissing);
    };
    Ok(RegisterMaskedAotPackageVersionedPersistenceLoad::Restored {
        bundle_bytes,
        graph,
        graph_bytes,
        objects,
        revision: versioned.revision,
        set,
    })
}

/// Reclaims package generations from caller-coordinated durable lease
/// snapshots.
///
/// Every positive durable owner count contributes its exact package revision to
/// the preservation set. Zero-owner snapshots contribute nothing. Duplicate
/// revisions collapse through exact equality and no revision order, age, or
/// expiry semantics are inferred.
///
/// The snapshots must come from coordination that prevents a new durable lease
/// from becoming authoritative for a generation concurrently deleted by this
/// reclamation pass. This function derives retention policy from those
/// snapshots but does not itself create that cross-resource lock domain.
///
/// # Errors
///
/// Returns current-package verification failure before deletion, or adapter
/// reclamation failure from the explicit cleanup pass.
pub fn reclaim_register_masked_aot_package_generations_from_lease_snapshot<
    'requirement,
    Store,
>(
    store: &mut Store,
    request: RegisterMaskedAotPackageRestoreRequest<'requirement>,
    leases: &RegisterMaskedAotPackageLeaseSnapshots<Store::Revision>,
) -> RegisterMaskedAotPackageReclamationStoreResult<'requirement, Store>
where
    Store: ReclaimablePairStore,
{
    let mut retention = NativeContinuationBlobPairRetention::new();
    for lease in leases {
        if lease.owners > 0 {
            let _retained = retention.retain(lease.revision().clone());
        }
    }
    reclaim_register_masked_aot_package_generations(store, request, &retention)
}

/// Reclaims superseded package generations under exact caller retention.
///
/// The current package is first restored and reverified with its opaque
/// revision. That verified revision is added to the preservation set for this
/// pass, so a concurrent newer publication cannot cause the last package this
/// call verified to be deleted. The adapter also preserves whatever generation
/// is current when reclamation actually acquires storage authority.
///
/// Missing package state performs no deletion. No chronology, expiry, or
/// capacity policy is inferred from opaque revisions.
///
/// # Errors
///
/// Returns current-package verification failure before deletion, or adapter
/// reclamation failure from the explicit cleanup pass.
pub fn reclaim_register_masked_aot_package_generations<'requirement, Store>(
    store: &mut Store,
    request: RegisterMaskedAotPackageRestoreRequest<'requirement>,
    retention: &NativeContinuationBlobPairRetention<Store::Revision>,
) -> RegisterMaskedAotPackageReclamationStoreResult<'requirement, Store>
where
    Store: ReclaimablePairStore,
{
    let current = restore_register_masked_aot_package_versioned(store, request)
        .map_err(RegisterMaskedAotPackageReclamationError::Restore)?;
    let RegisterMaskedAotPackageVersionedPersistenceLoad::Restored {
        revision: current_revision,
        ..
    } = current
    else {
        return Ok(RegisterMaskedAotPackageReclamation::Missing);
    };
    let mut preserved = retention.revisions().to_vec();
    if !preserved.contains(&current_revision) {
        preserved.push(current_revision.clone());
    }
    let reclamation_request =
        pair_reclamation::NativeContinuationBlobPairReclamationRequest::new(
            &preserved,
        );
    let reclamation = pair_reclamation::reclaim_blob_pair_generations(
        store,
        &reclamation_request,
    )
    .map_err(RegisterMaskedAotPackageReclamationError::Reclamation)?;
    Ok(RegisterMaskedAotPackageReclamation::Reclaimed {
        current_revision,
        reclamation,
        retained_revisions: retention.revisions().len(),
    })
}
