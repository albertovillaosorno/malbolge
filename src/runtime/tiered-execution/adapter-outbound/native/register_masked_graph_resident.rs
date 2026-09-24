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
//   - Whole-graph executable residency for verified reduced v6 AOT graphs.
// - Must-Not:
//   - Reverify graph semantics, invent native identity, execute guest code,
//     release mappings without ownership, or publish partial graph residency.
// - Allows:
//   - Inputs: one verified reduced graph, sealed exact AOT set, current
//     runtime/host assumptions, and caller-owned executable-memory adapter.
//   - Outputs: one complete node-to-resident binding, aggregate resident
//     weight, or exact load/cleanup failure ownership.
//   - Side effects: executable load/release only through the supplied adapter.
// - Split-When:
//   - Graph execution, eviction, leasing, or concurrent residency gains policy.
// - Merge-When:
//   - One general v6 graph executable store subsumes reduced-graph ownership.
// - Summary:
//   - Loads every exact reduced-graph artifact before publishing residency.
// - Description:
//   - Exact duplicate native keys share one mapping; late failure releases the
//     already loaded unique mappings in reverse load order.
// - Usage:
//   - Load after reduced-graph/AOT verification and release before adapter
//     loss.
// - Defaults:
//   - Missing, interpreter-only, selection-failed, or load-failed nodes reject
//     the whole resident; failed cleanup remains explicitly retryable.
//

//! Whole-graph executable residency for dependency-reduced v6 AOT graphs.

use std::sync::Arc;

use malbolge::{RegisterMaskedRegionEffectProgram, RuntimeCapability};

use super::direct::{
    AheadOfExecutionRegisterMaskedSelectionError,
    AheadOfExecutionRegisterMaskedTier, DirectHost,
    VerifiedAheadOfExecutionRegisterMaskedArtifact,
    VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
    VerifiedAheadOfExecutionRegisterMaskedSet,
    VerifiedRegisterMaskedHaltFetchNativeObjectArtifact,
    VerifiedRegisterMaskedNoOperationNativeObjectArtifact,
    VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact,
    select_ahead_of_execution_register_masked_tier,
};
use super::platform::{
    NativeExecutableMemoryAdapter,
    RegisterMaskedCrazyNativeExecutableReleaseFailure,
    RegisterMaskedNativeExecutableReleaseFailure,
    RegisterMaskedNoOperationNativeExecutableReleaseFailure,
    RegisterMaskedNonGraphicalNativeExecutableReleaseFailure,
    RegisterMaskedOutputNativeExecutableReleaseFailure,
    RegisterMaskedRotateNativeExecutableReleaseFailure,
};
use super::register_masked_resident::{
    RegisterMaskedCrazyNativeExecutableOwner,
    RegisterMaskedCrazyNativeOwnerLoadFailure,
    RegisterMaskedNativeExecutableOwner, RegisterMaskedNativeOwnerLoadFailure,
    RegisterMaskedNativeResidentWeight,
    RegisterMaskedNoOperationNativeExecutableOwner,
    RegisterMaskedNoOperationNativeOwnerLoadFailure,
    RegisterMaskedNonGraphicalNativeExecutableOwner,
    RegisterMaskedNonGraphicalNativeOwnerLoadFailure,
    RegisterMaskedOutputNativeExecutableOwner,
    RegisterMaskedOutputNativeOwnerLoadFailure,
    RegisterMaskedRotateNativeExecutableOwner,
    RegisterMaskedRotateNativeOwnerLoadFailure,
};
use crate::execution_cache::NativeArtifactKey;

/// One unique ready mapping retained by a complete reduced-graph resident.
#[derive(Debug)]
pub enum RegisterMaskedReducedGraphResidentOwner {
    /// One reusable v6 Crazy mapping.
    Crazy(Box<RegisterMaskedCrazyNativeExecutableOwner>),
    /// One reusable graphical halt-fetch mapping.
    HaltFetch(Box<RegisterMaskedNativeExecutableOwner>),
    /// One reusable v6 no-operation mapping.
    NoOperation(Box<RegisterMaskedNoOperationNativeExecutableOwner>),
    /// One reusable v6 non-graphical termination mapping.
    NonGraphical(Box<RegisterMaskedNonGraphicalNativeExecutableOwner>),
    /// One reusable v6 output mapping.
    Output(Box<RegisterMaskedOutputNativeExecutableOwner>),
    /// One reusable v6 rotate mapping.
    Rotate(Box<RegisterMaskedRotateNativeExecutableOwner>),
}

/// Typed load failure for one unique resident mapping.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedReducedGraphResidentOwnerLoadFailure<MemoryError> {
    /// Crazy owner load failed.
    Crazy(Box<RegisterMaskedCrazyNativeOwnerLoadFailure<MemoryError>>),
    /// Halt-fetch owner load failed.
    HaltFetch(Box<RegisterMaskedNativeOwnerLoadFailure<MemoryError>>),
    /// No-operation owner load failed.
    NoOperation(
        Box<RegisterMaskedNoOperationNativeOwnerLoadFailure<MemoryError>>,
    ),
    /// Non-graphical owner load failed.
    NonGraphical(
        Box<RegisterMaskedNonGraphicalNativeOwnerLoadFailure<MemoryError>>,
    ),
    /// Output owner load failed.
    Output(Box<RegisterMaskedOutputNativeOwnerLoadFailure<MemoryError>>),
    /// Rotate owner load failed.
    Rotate(Box<RegisterMaskedRotateNativeOwnerLoadFailure<MemoryError>>),
}

/// Exact ready executable retained when graph cleanup could not release it.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedReducedGraphResidentReleaseFailure<MemoryError> {
    /// Crazy mapping release failed.
    Crazy(Box<RegisterMaskedCrazyNativeExecutableReleaseFailure<MemoryError>>),
    /// Halt-fetch mapping release failed.
    HaltFetch(Box<RegisterMaskedNativeExecutableReleaseFailure<MemoryError>>),
    /// No-operation mapping release failed.
    NoOperation(
        Box<
            RegisterMaskedNoOperationNativeExecutableReleaseFailure<
                MemoryError,
            >,
        >,
    ),
    /// Non-graphical mapping release failed.
    NonGraphical(
        Box<
            RegisterMaskedNonGraphicalNativeExecutableReleaseFailure<
                MemoryError,
            >,
        >,
    ),
    /// Output mapping release failed.
    Output(
        Box<RegisterMaskedOutputNativeExecutableReleaseFailure<MemoryError>>,
    ),
    /// Rotate mapping release failed.
    Rotate(
        Box<RegisterMaskedRotateNativeExecutableReleaseFailure<MemoryError>>,
    ),
}

/// Why one graph node could not join complete executable residency.
#[derive(Debug, Eq, PartialEq)]
pub enum RegisterMaskedReducedGraphResidentLoadCause<'requirement, MemoryError>
{
    /// Current host has no supported direct object format.
    Interpreter,
    /// Selected exact object failed executable owner loading.
    Owner(Box<RegisterMaskedReducedGraphResidentOwnerLoadFailure<MemoryError>>),
    /// Exact object selection failed under current runtime/host assumptions.
    Selection(Box<AheadOfExecutionRegisterMaskedSelectionError<'requirement>>),
    /// Verified graph node lookup unexpectedly failed.
    Topology,
    /// Exact object is absent from the supplied sealed AOT set.
    Uncovered,
}

/// Failed all-or-nothing reduced-graph residency preparation.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedReducedGraphResidentLoadFailure<
    'requirement,
    MemoryError,
> {
    cause:
        RegisterMaskedReducedGraphResidentLoadCause<'requirement, MemoryError>,
    cleanup_failures:
        Vec<RegisterMaskedReducedGraphResidentReleaseFailure<MemoryError>>,
    index: usize,
}

/// Failed whole-graph release retaining every mapping that still needs cleanup.
#[derive(Debug, Eq, PartialEq)]
pub struct RegisterMaskedReducedGraphResidentReleaseAllFailure<MemoryError> {
    failures:
        Vec<RegisterMaskedReducedGraphResidentReleaseFailure<MemoryError>>,
}

/// Exact aggregate whole-graph executable residency weight.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RegisterMaskedReducedGraphResidentWeight {
    mapped_bytes: usize,
    mappings: usize,
    nodes: usize,
    unique_artifacts: usize,
}

/// Immutable native environment for whole reduced-graph residency loading.
#[derive(Clone, Copy, Debug)]
pub struct RegisterMaskedReducedGraphResidentEnvironment<'aot> {
    aot: &'aot VerifiedAheadOfExecutionRegisterMaskedSet,
    host: DirectHost,
    runtime: &'static RuntimeCapability,
}

/// Complete executable residency for one verified reduced v6 graph.
#[derive(Debug)]
pub struct LoadedRegisterMaskedReducedStateGraph {
    graph: ReducedGraph,
    node_owners: Vec<usize>,
    owners: Vec<RegisterMaskedReducedGraphResidentOwner>,
}

type ArtifactSelectionFailure<'requirement> =
    RegisterMaskedReducedGraphResidentLoadCause<'requirement, ()>;
type ArtifactSelectionResult<'requirement> = Result<
    Arc<VerifiedAheadOfExecutionRegisterMaskedArtifact>,
    ArtifactSelectionFailure<'requirement>,
>;
type OwnerLoadResult<MemoryError> = Result<
    RegisterMaskedReducedGraphResidentOwner,
    RegisterMaskedReducedGraphResidentOwnerLoadFailure<MemoryError>,
>;
type OwnerReleaseResult<MemoryError> =
    Result<(), RegisterMaskedReducedGraphResidentReleaseFailure<MemoryError>>;
type ReducedGraph = VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph;

/// Result of complete reduced-graph executable residency preparation.
pub type RegisterMaskedReducedGraphResidentLoadResult<
    'requirement,
    MemoryError,
> = Result<
    LoadedRegisterMaskedReducedStateGraph,
    Box<
        RegisterMaskedReducedGraphResidentLoadFailure<
            'requirement,
            MemoryError,
        >,
    >,
>;

/// Result of releasing every unique mapping retained by one graph resident.
pub type RegisterMaskedReducedGraphResidentReleaseAllResult<MemoryError> =
    Result<
        (),
        Box<RegisterMaskedReducedGraphResidentReleaseAllFailure<MemoryError>>,
    >;

impl RegisterMaskedReducedGraphResidentOwner {
    /// Returns the exact native key retained by this unique resident.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        match self {
            Self::Crazy(owner) => owner.key(),
            Self::HaltFetch(owner) => owner.key(),
            Self::NoOperation(owner) => owner.key(),
            Self::NonGraphical(owner) => owner.key(),
            Self::Output(owner) => owner.key(),
            Self::Rotate(owner) => owner.key(),
        }
    }

    fn release<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> OwnerReleaseResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        match self {
            Self::Crazy(owner) => owner.release(adapter).map_err(
                RegisterMaskedReducedGraphResidentReleaseFailure::Crazy,
            ),
            Self::HaltFetch(owner) => owner.release(adapter).map_err(
                RegisterMaskedReducedGraphResidentReleaseFailure::HaltFetch,
            ),
            Self::NoOperation(owner) => owner.release(adapter).map_err(
                RegisterMaskedReducedGraphResidentReleaseFailure::NoOperation,
            ),
            Self::NonGraphical(owner) => owner.release(adapter).map_err(
                RegisterMaskedReducedGraphResidentReleaseFailure::NonGraphical,
            ),
            Self::Output(owner) => owner.release(adapter).map_err(
                RegisterMaskedReducedGraphResidentReleaseFailure::Output,
            ),
            Self::Rotate(owner) => owner.release(adapter).map_err(
                RegisterMaskedReducedGraphResidentReleaseFailure::Rotate,
            ),
        }
    }

    /// Returns exact synchronized mapping weight for this unique resident.
    #[must_use]
    pub const fn resident_weight(&self) -> RegisterMaskedNativeResidentWeight {
        match self {
            Self::Crazy(owner) => owner.resident_weight(),
            Self::HaltFetch(owner) => owner.resident_weight(),
            Self::NoOperation(owner) => owner.resident_weight(),
            Self::NonGraphical(owner) => owner.resident_weight(),
            Self::Output(owner) => owner.resident_weight(),
            Self::Rotate(owner) => owner.resident_weight(),
        }
    }
}

impl<MemoryError>
    RegisterMaskedReducedGraphResidentLoadFailure<'_, MemoryError>
{
    /// Returns the exact node-specific primary failure.
    #[must_use]
    pub const fn cause(
        &self,
    ) -> &RegisterMaskedReducedGraphResidentLoadCause<'_, MemoryError> {
        &self.cause
    }

    /// Returns cleanup failures retained after rolling back earlier mappings.
    #[must_use]
    pub fn cleanup_failures(
        &self,
    ) -> &[RegisterMaskedReducedGraphResidentReleaseFailure<MemoryError>] {
        &self.cleanup_failures
    }

    /// Returns the zero-based graph node whose residency preparation failed.
    #[must_use]
    pub const fn index(&self) -> usize {
        self.index
    }

    /// Consumes the failure and returns retryable cleanup ownership.
    #[must_use]
    pub fn into_cleanup_failures(
        self,
    ) -> Vec<RegisterMaskedReducedGraphResidentReleaseFailure<MemoryError>>
    {
        self.cleanup_failures
    }
}

impl<'aot> RegisterMaskedReducedGraphResidentEnvironment<'aot> {
    /// Binds one sealed AOT set to current runtime and host assumptions.
    #[must_use]
    pub const fn new(
        aot: &'aot VerifiedAheadOfExecutionRegisterMaskedSet,
        runtime: &'static RuntimeCapability,
        host: DirectHost,
    ) -> Self {
        Self { aot, host, runtime }
    }
}

impl<MemoryError>
    RegisterMaskedReducedGraphResidentReleaseAllFailure<MemoryError>
{
    /// Returns mappings that still need explicit release retry.
    #[must_use]
    pub fn failures(
        &self,
    ) -> &[RegisterMaskedReducedGraphResidentReleaseFailure<MemoryError>] {
        &self.failures
    }

    /// Consumes aggregate failure into exact retryable mapping ownership.
    #[must_use]
    pub fn into_failures(
        self,
    ) -> Vec<RegisterMaskedReducedGraphResidentReleaseFailure<MemoryError>>
    {
        self.failures
    }
}

impl<MemoryError>
    RegisterMaskedReducedGraphResidentReleaseFailure<MemoryError>
{
    /// Retries release while retaining the same ready mapping on failure.
    ///
    /// # Errors
    ///
    /// Returns refreshed exact mapping ownership when the adapter fails again.
    pub fn retry<Adapter>(self, adapter: &mut Adapter) -> Result<(), Self>
    where
        Adapter: NativeExecutableMemoryAdapter<Error = MemoryError>,
    {
        match self {
            Self::Crazy(current) => current
                .retry(adapter)
                .map_err(|next| Self::Crazy(Box::new(next))),
            Self::HaltFetch(current) => current
                .retry(adapter)
                .map_err(|next| Self::HaltFetch(Box::new(next))),
            Self::NoOperation(current) => current
                .retry(adapter)
                .map_err(|next| Self::NoOperation(Box::new(next))),
            Self::NonGraphical(current) => current
                .retry(adapter)
                .map_err(|next| Self::NonGraphical(Box::new(next))),
            Self::Output(current) => current
                .retry(adapter)
                .map_err(|next| Self::Output(Box::new(next))),
            Self::Rotate(current) => current
                .retry(adapter)
                .map_err(|next| Self::Rotate(Box::new(next))),
        }
    }
}

impl RegisterMaskedReducedGraphResidentWeight {
    /// Returns exact synchronized bytes across unique resident mappings.
    #[must_use]
    pub const fn mapped_bytes(self) -> usize {
        self.mapped_bytes
    }

    /// Returns exact number of unique live executable mappings.
    #[must_use]
    pub const fn mappings(self) -> usize {
        self.mappings
    }

    /// Returns exact number of graph nodes bound to resident mappings.
    #[must_use]
    pub const fn nodes(self) -> usize {
        self.nodes
    }

    /// Returns exact number of unique exact native artifacts retained.
    #[must_use]
    pub const fn unique_artifacts(self) -> usize {
        self.unique_artifacts
    }
}

impl LoadedRegisterMaskedReducedStateGraph {
    /// Returns the verifier-admitted reduced graph bound to these mappings.
    #[must_use]
    pub const fn graph(&self) -> &ReducedGraph {
        &self.graph
    }

    /// Returns exact number of graph nodes with resident bindings.
    #[must_use]
    pub const fn node_count(&self) -> usize {
        self.node_owners.len()
    }

    /// Returns the exact resident key selected for one graph node.
    #[must_use]
    pub fn node_key(&self, index: usize) -> Option<&NativeArtifactKey> {
        let owner = *self.node_owners.get(index)?;
        self.owners
            .get(owner)
            .map(RegisterMaskedReducedGraphResidentOwner::key)
    }

    /// Returns exact number of unique resident mappings.
    #[must_use]
    pub const fn owner_count(&self) -> usize {
        self.owners.len()
    }

    /// Releases every unique mapping in reverse load order.
    ///
    /// Successfully released mappings remain released. Failures retain exact
    /// ready executable ownership for retry and no mapping is silently dropped.
    ///
    /// # Errors
    ///
    /// Returns all exact mappings whose adapter release failed.
    pub fn release<Adapter>(
        self,
        adapter: &mut Adapter,
    ) -> RegisterMaskedReducedGraphResidentReleaseAllResult<Adapter::Error>
    where
        Adapter: NativeExecutableMemoryAdapter,
    {
        let failures = release_owners(self.owners, adapter);
        if failures.is_empty() {
            Ok(())
        } else {
            Err(Box::new(
                RegisterMaskedReducedGraphResidentReleaseAllFailure {
                    failures,
                },
            ))
        }
    }

    /// Returns checked aggregate resident weight for this complete graph.
    #[must_use]
    pub fn resident_weight(
        &self,
    ) -> Option<RegisterMaskedReducedGraphResidentWeight> {
        let mut mapped_bytes = 0usize;
        let mut mappings = 0usize;
        for owner in &self.owners {
            let weight = owner.resident_weight();
            mapped_bytes = mapped_bytes.checked_add(weight.mapped_bytes())?;
            mappings = mappings.checked_add(weight.mappings())?;
        }
        Some(RegisterMaskedReducedGraphResidentWeight {
            mapped_bytes,
            mappings,
            nodes: self.node_owners.len(),
            unique_artifacts: self.owners.len(),
        })
    }
}

/// Loads complete executable residency for one verified reduced AOT graph.
///
/// Exact duplicate keys share one ready mapping. Every unique mapping is loaded
/// before the resident is published. A later failure releases prior mappings in
/// reverse load order and transfers any failed cleanup ownership to the caller.
///
/// # Errors
///
/// Returns indexed selection/load failure plus exact pending rollback
/// ownership.
pub fn load_ahead_of_execution_register_masked_reduced_state_graph<
    'requirement,
    Adapter,
>(
    adapter: &mut Adapter,
    graph: &'requirement ReducedGraph,
    environment: RegisterMaskedReducedGraphResidentEnvironment<'requirement>,
) -> RegisterMaskedReducedGraphResidentLoadResult<'requirement, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut owners = Vec::new();
    let mut node_owners = Vec::with_capacity(graph.len());
    for index in 0..graph.len() {
        let Some(node) = graph.node(index) else {
            let cause = RegisterMaskedReducedGraphResidentLoadCause::Topology;
            return Err(Box::new(load_failure(index, cause, owners, adapter)));
        };
        let selected = match select_artifact(node.program(), environment) {
            Ok(artifact) => artifact,
            Err(error) => {
                let cause = convert_selection_failure(error);
                return Err(Box::new(load_failure(
                    index, cause, owners, adapter,
                )));
            },
        };
        if let Some(owner_index) = find_owner(&owners, selected.key()) {
            node_owners.push(owner_index);
            continue;
        }
        let owner = match load_owner(adapter, node.program(), selected.as_ref())
        {
            Ok(owner) => owner,
            Err(error) => {
                let cause = RegisterMaskedReducedGraphResidentLoadCause::Owner(
                    Box::new(error),
                );
                return Err(Box::new(load_failure(
                    index, cause, owners, adapter,
                )));
            },
        };
        let owner_index = owners.len();
        owners.push(owner);
        node_owners.push(owner_index);
    }
    Ok(LoadedRegisterMaskedReducedStateGraph {
        graph: graph.clone(),
        node_owners,
        owners,
    })
}

fn convert_selection_failure<MemoryError>(
    failure: ArtifactSelectionFailure<'_>,
) -> RegisterMaskedReducedGraphResidentLoadCause<'_, MemoryError> {
    match failure {
        RegisterMaskedReducedGraphResidentLoadCause::Interpreter => {
            RegisterMaskedReducedGraphResidentLoadCause::Interpreter
        },
        RegisterMaskedReducedGraphResidentLoadCause::Selection(selection) => {
            RegisterMaskedReducedGraphResidentLoadCause::Selection(selection)
        },
        RegisterMaskedReducedGraphResidentLoadCause::Uncovered => {
            RegisterMaskedReducedGraphResidentLoadCause::Uncovered
        },
        RegisterMaskedReducedGraphResidentLoadCause::Owner(_)
        | RegisterMaskedReducedGraphResidentLoadCause::Topology => {
            RegisterMaskedReducedGraphResidentLoadCause::Topology
        },
    }
}

fn find_owner(
    owners: &[RegisterMaskedReducedGraphResidentOwner],
    key: &NativeArtifactKey,
) -> Option<usize> {
    owners.iter().position(|owner| owner.key() == key)
}

fn load_failure<'requirement, Adapter>(
    index: usize,
    cause: RegisterMaskedReducedGraphResidentLoadCause<
        'requirement,
        Adapter::Error,
    >,
    owners: Vec<RegisterMaskedReducedGraphResidentOwner>,
    adapter: &mut Adapter,
) -> RegisterMaskedReducedGraphResidentLoadFailure<'requirement, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    RegisterMaskedReducedGraphResidentLoadFailure {
        cause,
        cleanup_failures: release_owners(owners, adapter),
        index,
    }
}

fn load_owner<Adapter>(
    adapter: &mut Adapter,
    program: &RegisterMaskedRegionEffectProgram,
    selected: &VerifiedAheadOfExecutionRegisterMaskedArtifact,
) -> OwnerLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    match selected {
        VerifiedAheadOfExecutionRegisterMaskedArtifact::Crazy(concrete) => {
            load_crazy(adapter, program, concrete)
        },
        VerifiedAheadOfExecutionRegisterMaskedArtifact::HaltFetch(concrete) => {
            load_halt_fetch(adapter, program, concrete)
        },
        VerifiedAheadOfExecutionRegisterMaskedArtifact::NoOperation(
            concrete,
        ) => load_no_operation(adapter, program, concrete),
        VerifiedAheadOfExecutionRegisterMaskedArtifact::NonGraphical(
            concrete,
        ) => load_non_graphical(adapter, program, concrete),
        VerifiedAheadOfExecutionRegisterMaskedArtifact::Output(concrete) => {
            load_output(adapter, program, concrete)
        },
        VerifiedAheadOfExecutionRegisterMaskedArtifact::Rotate(concrete) => {
            load_rotate(adapter, program, concrete)
        },
    }
}

fn load_crazy<Adapter>(
    adapter: &mut Adapter,
    program: &RegisterMaskedRegionEffectProgram,
    artifact: &super::direct::VerifiedRegisterMaskedCrazyNativeObjectArtifact,
) -> OwnerLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    RegisterMaskedCrazyNativeExecutableOwner::load(adapter, program, artifact)
        .map(|owner| {
            RegisterMaskedReducedGraphResidentOwner::Crazy(Box::new(owner))
        })
        .map_err(RegisterMaskedReducedGraphResidentOwnerLoadFailure::Crazy)
}

fn load_halt_fetch<Adapter>(
    adapter: &mut Adapter,
    program: &RegisterMaskedRegionEffectProgram,
    artifact: &VerifiedRegisterMaskedHaltFetchNativeObjectArtifact,
) -> OwnerLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    RegisterMaskedNativeExecutableOwner::load(adapter, program, artifact)
        .map(|owner| {
            RegisterMaskedReducedGraphResidentOwner::HaltFetch(Box::new(owner))
        })
        .map_err(RegisterMaskedReducedGraphResidentOwnerLoadFailure::HaltFetch)
}

fn load_no_operation<Adapter>(
    adapter: &mut Adapter,
    program: &RegisterMaskedRegionEffectProgram,
    artifact: &VerifiedRegisterMaskedNoOperationNativeObjectArtifact,
) -> OwnerLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    RegisterMaskedNoOperationNativeExecutableOwner::load(
        adapter, program, artifact,
    )
    .map(|owner| {
        RegisterMaskedReducedGraphResidentOwner::NoOperation(Box::new(owner))
    })
    .map_err(RegisterMaskedReducedGraphResidentOwnerLoadFailure::NoOperation)
}

fn load_non_graphical<Adapter>(
    adapter: &mut Adapter,
    program: &RegisterMaskedRegionEffectProgram,
    artifact: &VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact,
) -> OwnerLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    RegisterMaskedNonGraphicalNativeExecutableOwner::load(
        adapter, program, artifact,
    )
    .map(|owner| {
        RegisterMaskedReducedGraphResidentOwner::NonGraphical(Box::new(owner))
    })
    .map_err(RegisterMaskedReducedGraphResidentOwnerLoadFailure::NonGraphical)
}

fn load_output<Adapter>(
    adapter: &mut Adapter,
    program: &RegisterMaskedRegionEffectProgram,
    artifact: &super::direct::VerifiedRegisterMaskedOutputNativeObjectArtifact,
) -> OwnerLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    RegisterMaskedOutputNativeExecutableOwner::load(adapter, program, artifact)
        .map(|owner| {
            RegisterMaskedReducedGraphResidentOwner::Output(Box::new(owner))
        })
        .map_err(RegisterMaskedReducedGraphResidentOwnerLoadFailure::Output)
}

fn load_rotate<Adapter>(
    adapter: &mut Adapter,
    program: &RegisterMaskedRegionEffectProgram,
    artifact: &super::direct::VerifiedRegisterMaskedRotateNativeObjectArtifact,
) -> OwnerLoadResult<Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    RegisterMaskedRotateNativeExecutableOwner::load(adapter, program, artifact)
        .map(|owner| {
            RegisterMaskedReducedGraphResidentOwner::Rotate(Box::new(owner))
        })
        .map_err(RegisterMaskedReducedGraphResidentOwnerLoadFailure::Rotate)
}

fn release_owners<Adapter>(
    owners: Vec<RegisterMaskedReducedGraphResidentOwner>,
    adapter: &mut Adapter,
) -> Vec<RegisterMaskedReducedGraphResidentReleaseFailure<Adapter::Error>>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let mut failures = Vec::new();
    for owner in owners.into_iter().rev() {
        if let Err(failure) = owner.release(adapter) {
            failures.push(failure);
        }
    }
    failures
}

fn select_artifact<'requirement>(
    program: &'requirement RegisterMaskedRegionEffectProgram,
    environment: RegisterMaskedReducedGraphResidentEnvironment<'requirement>,
) -> ArtifactSelectionResult<'requirement> {
    let tier = select_ahead_of_execution_register_masked_tier(
        program,
        environment.runtime,
        environment.host,
        environment.aot,
    )
    .map_err(|error| {
        RegisterMaskedReducedGraphResidentLoadCause::Selection(Box::new(error))
    })?;
    match tier {
        AheadOfExecutionRegisterMaskedTier::Direct(artifact) => Ok(artifact),
        AheadOfExecutionRegisterMaskedTier::Interpreter => {
            Err(RegisterMaskedReducedGraphResidentLoadCause::Interpreter)
        },
        AheadOfExecutionRegisterMaskedTier::Uncovered => {
            Err(RegisterMaskedReducedGraphResidentLoadCause::Uncovered)
        },
    }
}
