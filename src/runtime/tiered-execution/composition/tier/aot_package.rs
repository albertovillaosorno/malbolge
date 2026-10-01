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
//   - Atomic durable publication and restoration of reduced-graph provenance
//     together with its complete register-masked AOT object bundle.
// - Must-Not:
//   - Choose storage paths, trust persisted graph/object authority, publish one
//     member independently, load executable memory, or infer eviction policy.
// - Allows:
//   - Inputs: exact graph claim, graph-ordered programs, sealed AOT set,
//     runtime/host assumptions, decode limits, and independent positive bounds.
//   - Outputs: one atomic pair publication or freshly replayed/reverified graph
//     and object authority.
//   - Side effects: delegated through bounded atomic blob-pair persistence.
// - Split-When:
//   - Package migration, retention scheduling, or executable residency gains
//     independent authority.
// - Merge-When:
//   - One general durable native-cache package owner subsumes this pair.
// - Summary:
//   - Prevents graph provenance and its native bundle from crossing
//     generations.
// - Description:
//   - Both canonical payloads are prepared before one pair commit; restore
//     rebuilds graph and native authority before returning either to callers.
// - Usage:
//   - Persist and restore one exact reduced graph plus its sealed AOT coverage.
// - Defaults:
//   - Missing pair state is explicit; any graph/program/object drift fails
//     closed without partial authority.
//

//! Atomic durable package for reduced graph provenance plus its AOT bundle.

use std::num::NonZeroUsize;

use malbolge::RegisterMaskedRegionEffectProgram;
use pair_port::{
    NativeContinuationBlobPairStore as PairStore,
    NativeContinuationDurableBlobPairStore as DurablePairStore,
};

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
    blob_pair_persistence as pair_persistence, blob_pair_store as pair_port,
};

type PackageGraphClaim =
    UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph;
type PackageGraphDecodeLimits =
    AheadOfExecutionRegisterMaskedReducedStateGraphDecodeLimits;

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
    let graph = decode_ahead_of_execution_register_masked_reduced_state_graph(
        &graph_bytes,
        request.decode_limits,
    )
    .map_err(RegisterMaskedAotPackageRestoreError::Graph)?;
    validate_program_order(&graph, request.bundle.programs())
        .map_err(RegisterMaskedAotPackageRestoreError::Programs)?;
    let bundle = decode_register_masked_aot_bundle::<Store::Error>(
        &bundle_bytes,
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
