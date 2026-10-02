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
//   - Integration evidence from verified research regions through product v6
//     AOT admission and dependency-reduced runtime dispatch.
// - Must-Not:
//   - Make production runtime depend on research modules or grant invocation
//     authority from research verification alone.
// - Allows:
//   - Inputs: verifier-admitted research artifacts and product-owned v6 IR.
//   - Outputs: AOT object-admission handoff assertions and fail-closed
//     evidence.
//   - Side effects: test-process allocation, canonical object emission, and
//     isolated temporary blob persistence only.
// - Split-When:
//   - Executable residency or verified collapsed multi-step effects gain
//     integration policy.
// - Merge-When:
//   - State-graph optimization becomes production runtime infrastructure.
// - Summary:
//   - Proves the research optimizer crosses AOT only through product-owned IR.
// - Description:
//   - Composes both boundaries without introducing a production dependency on
//   - the research implementation.
// - Usage:
//   - Auto-discovered by Cargo workspace tests.
// - Defaults:
//   - Unsupported multi-step reductions fail closed before native publication.
//

//! Research-to-product register-masked AOT handoff integration evidence.

#[path = "../src/runtime/tiered-execution/application/blob_pair_persistence.rs"]
pub mod blob_pair_persistence;
#[path = "../src/runtime/tiered-execution/application/blob_pair_reclamation.rs"]
pub mod blob_pair_reclamation;
#[path = "../src/runtime/tiered-execution/application/blob_pair_retention.rs"]
pub mod blob_pair_retention;
#[path = "../src/runtime/tiered-execution/port-outbound/blob_pair_store.rs"]
pub mod blob_pair_store;
#[path = "../src/runtime/tiered-execution/application/blob_persistence.rs"]
pub mod blob_persistence;
#[path = "../src/runtime/tiered-execution/port-outbound/blob_store.rs"]
pub mod blob_store;
#[path = "../src/runtime/tiered-execution/composition/tier/lease_journal.rs"]
pub mod executable_durable_lease_journal;
#[path = "../src/runtime/tiered-execution/adapter-outbound/cache/main.rs"]
pub mod execution_cache;
#[path = "../src/runtime/tiered-execution/adapter-outbound/native/main.rs"]
pub mod execution_native;
#[path = "../src/runtime/tiered-execution/adapter-outbound/blob_pair/main.rs"]
pub mod file_blob_pair_store;
#[path = "../src/runtime/tiered-execution/adapter-outbound/blob/main.rs"]
pub mod file_blob_store;
#[path = "../src/runtime/tiered-execution/adapter-outbound/fs_coord/main.rs"]
pub mod file_coordination;
#[path = "../src/research/algorithms/composition/state-graph/index.rs"]
pub mod indexed;
#[path = "../src/research/algorithms/composition/state-graph/state.rs"]
pub mod indexed_state;
#[path = "../src/research/algorithms/composition/state-graph/output.rs"]
pub mod persistent_output;
#[path = "../src/runtime/tiered-execution/composition/tier/graph_store.rs"]
pub mod reduced_graph_persistence;
#[path = "../src/research/algorithms/composition/state-graph/artifact.rs"]
pub mod region_artifact;
#[path = "../src/research/algorithms/composition/state-graph/region.rs"]
pub mod region_certificate;
#[path = "../src/runtime/tiered-execution/composition/tier/aot_bundle.rs"]
pub mod register_masked_aot_bundle_persistence;
#[path = "../src/runtime/tiered-execution/composition/tier/object_store.rs"]
pub mod register_masked_aot_object_persistence;
#[path = "../src/runtime/tiered-execution/composition/tier/package_lease.rs"]
pub mod register_masked_aot_package_lease_reclamation;
#[path = "../src/runtime/tiered-execution/composition/tier/aot_package.rs"]
pub mod register_masked_aot_package_persistence;

use std::fs;
use std::io::ErrorKind;
use std::num::NonZeroUsize;
use std::path::{Path, PathBuf};
use std::process::id as process_id;
use std::slice::from_ref;
use std::sync::Arc;

use blob_pair_retention::NativeContinuationBlobPairRetention;
use blob_pair_store::NativeContinuationBlobPairStore as BlobPairStore;
use executable_durable_lease_journal::{
    NativeExecutableDurableLeaseJournalError as LeaseJournalError,
    NativeExecutableDurableLeaseJournalLoad as LeaseJournalLoad,
    NativeExecutableDurableLeaseOwnerId,
    NativeExecutableDurableLeaseRegistryDecodeLimits,
    NativeExecutableDurableLeaseTransition,
    NativeExecutableDurableLeaseTransitionError as LeaseTransitionError,
    NativeExecutableDurableLeaseTransitionRequest,
};
use execution_cache::{HostIsa, HostOperatingSystem};
use execution_native::{
    AheadOfExecutionRegisterMaskedPreparationError,
    AheadOfExecutionRegisterMaskedReducedStateGraphCodecError,
    AheadOfExecutionRegisterMaskedReducedStateGraphDecodeLimits,
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchEnvironment,
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchFailure,
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchFallback,
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchOutcome,
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchRequest,
    AheadOfExecutionRegisterMaskedReducedStateGraphError,
    AheadOfExecutionRegisterMaskedReducedStateGraphNodeClaim,
    AheadOfExecutionRegisterMaskedTier, DirectHost, DirectNativeKind,
    RegisterMaskedDependencyIdentityClaim,
    RegisterMaskedDirectAdmissionErrorKind,
    RegisterMaskedReducedStateGraphNativeExecution,
    RegisterMaskedReducedStateGraphNativeExecutionRequest,
    RegisterMaskedReducedStateGraphNativeExecutor,
    UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
    VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
    VerifiedAheadOfExecutionRegisterMaskedSet,
    decode_ahead_of_execution_register_masked_reduced_state_graph,
    dispatch_ahead_of_execution_register_masked_reduced_state_graph,
    encode_ahead_of_execution_register_masked_reduced_state_graph,
    prepare_ahead_of_execution_register_masked_set,
    select_ahead_of_execution_register_masked_tier,
};
use file_blob_pair_store::{
    NativeContinuationFileBlobPairDurabilityError,
    NativeContinuationFileBlobPairReclamation,
    NativeContinuationFileBlobPairRevision,
    NativeContinuationFileBlobPairStore,
};
use file_blob_store::{
    NativeContinuationFileBlobStore,
    NativeContinuationFileBlobStoreError as FileBlobStoreError,
};
use file_coordination::NativeContinuationFileCoordination;
use indexed_state::IndexedMachineState;
use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileMachineIoState,
    ProfileMachineState, ProfileRegisters, ProfileStepTrace,
    RegisterMaskedRegionEffectProgram, RegisterMaskedRegionProjectionError,
    RunOutcome, StepProgramProjectionError, Termination, current_profile,
    decode_profile_instruction, safe_rust_profiled_capability,
    verify_minimum_initial_halt_profile_width,
};
use reduced_graph_persistence::{
    RegisterMaskedReducedGraphPersistenceError,
    RegisterMaskedReducedGraphPersistenceLoad,
    evict_register_masked_reduced_graph_if_current_durably,
    persist_register_masked_reduced_graph_durably,
    restore_register_masked_reduced_graph,
};
use region_artifact::{UntrustedRegionArtifact, VerifiedRegionArtifact};
use region_certificate::{ExactRegionCertificate, VerifiedExactRegion};
use register_masked_aot_bundle_persistence::{
    RegisterMaskedAotBundleFramingError, RegisterMaskedAotBundlePersistRequest,
    RegisterMaskedAotBundlePersistenceLoad,
    RegisterMaskedAotBundlePreparationError,
    RegisterMaskedAotBundleRestorePersistenceError,
    RegisterMaskedAotBundleRestoreRequest, RegisterMaskedAotBundleSource,
    RegisterMaskedAotBundleStoreError,
    evict_register_masked_aot_bundle_durably,
    evict_register_masked_aot_bundle_if_current_durably,
    persist_register_masked_aot_bundle,
    persist_register_masked_aot_bundle_durably,
    restore_register_masked_aot_bundle,
};
use register_masked_aot_object_persistence::{
    RegisterMaskedAotObjectPersistenceLoad,
    RegisterMaskedAotObjectRestorePersistenceError,
    RegisterMaskedAotObjectRestoreRequest,
    evict_register_masked_aot_object_durably,
    evict_register_masked_aot_object_if_current_durably,
    persist_register_masked_aot_object_durably,
    restore_register_masked_aot_object,
};
use register_masked_aot_package_lease_reclamation as package_lease;
use register_masked_aot_package_persistence::{
    RegisterMaskedAotPackageConditionalDurablePersistence,
    RegisterMaskedAotPackageLeaseSnapshot,
    RegisterMaskedAotPackagePersistRequest,
    RegisterMaskedAotPackagePersistenceLoad,
    RegisterMaskedAotPackagePreparationError,
    RegisterMaskedAotPackageReclamation,
    RegisterMaskedAotPackageReclamationError,
    RegisterMaskedAotPackageRestoreRequest, RegisterMaskedAotPackageSource,
    RegisterMaskedAotPackageStoreError,
    RegisterMaskedAotPackageVersionedPersistenceLoad,
    compare_and_swap_register_masked_aot_package_durably,
    persist_register_masked_aot_package_durably,
    reclaim_register_masked_aot_package_generations,
    reclaim_register_masked_aot_package_generations_from_lease_snapshot,
    restore_register_masked_aot_package,
    restore_register_masked_aot_package_versioned,
};

const MULTI_STEP_SOURCE: &[u8] = b"(=%`qL";

#[derive(Clone, Copy, Debug)]
struct GuardedAotPackageLeaseContext<'context> {
    bounds: AotPackageBounds,
    coordination: &'context NativeContinuationFileCoordination,
    lease_request: NativeExecutableDurableLeaseTransitionRequest,
    programs: &'context [RegisterMaskedRegionEffectProgram],
    revision: NativeContinuationFileBlobPairRevision,
}

type HandoffResult<T> = Result<T, String>;
type BlobPersistenceError<StoreError> =
    blob_persistence::NativeContinuationBlobPersistenceError<StoreError>;
type AotPackageLeaseTransitionError =
    package_lease::RegisterMaskedAotPackageLeaseTransitionError;
type FileAotPackageLeaseTransition = NativeExecutableDurableLeaseTransition<
    file_blob_store::NativeContinuationFileBlobDurabilityError,
>;
type AotPackageFileConditional =
    RegisterMaskedAotPackageConditionalDurablePersistence<
        NativeContinuationFileBlobPairRevision,
        NativeContinuationFileBlobPairDurabilityError,
    >;
type AotPackageFileReclamation = RegisterMaskedAotPackageReclamation<
    NativeContinuationFileBlobPairRevision,
    NativeContinuationFileBlobPairReclamation,
>;
type AotPackageMaterial = (
    ReducedGraphClaim,
    ReducedGraph,
    Vec<RegisterMaskedRegionEffectProgram>,
    VerifiedAheadOfExecutionRegisterMaskedSet,
);
type ReducedCodecError =
    AheadOfExecutionRegisterMaskedReducedStateGraphCodecError;
type ReducedCodecLimits =
    AheadOfExecutionRegisterMaskedReducedStateGraphDecodeLimits;
type ReducedDispatchFailure<'graph> =
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchFailure<
        'graph,
        ProfileMachineError,
    >;
type ReducedDispatchEnvironment<'aot> =
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchEnvironment<'aot>;
type ReducedDispatchFallback =
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchFallback;
type ReducedDispatchOutcome =
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchOutcome;
type ReducedDispatchRequest<'graph, 'aot> =
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchRequest<
        'graph,
        'aot,
    >;
type ReducedGraphError = AheadOfExecutionRegisterMaskedReducedStateGraphError;
type ReducedGraph = VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph;
type ReducedGraphClaim =
    UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph;

#[derive(Clone, Copy, Debug)]
struct AotPackageBounds {
    bundle: NonZeroUsize,
    graph: NonZeroUsize,
}

#[derive(Debug, Eq, PartialEq)]
struct ReducedGraphStoreFixture {
    destination: PathBuf,
    directory: PathBuf,
}
type ReducedNativeExecution = RegisterMaskedReducedStateGraphNativeExecution;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ReducedExecutorMode {
    Apply,
    GuardMiss,
    MutatedGuardMiss,
    TamperSuccessor,
    TamperTerminal,
}

#[derive(Debug)]
struct NormativeReducedGraphExecutor {
    calls: usize,
    kinds: Vec<DirectNativeKind>,
    mode: ReducedExecutorMode,
}

impl NormativeReducedGraphExecutor {
    const fn new(mode: ReducedExecutorMode) -> Self {
        Self {
            calls: 0,
            kinds: Vec::new(),
            mode,
        }
    }
}

impl RegisterMaskedReducedStateGraphNativeExecutor
    for NormativeReducedGraphExecutor
{
    type Error = ProfileMachineError;

    fn execute(
        &mut self,
        request: RegisterMaskedReducedStateGraphNativeExecutionRequest<'_>,
    ) -> Result<ReducedNativeExecution, Self::Error> {
        let artifact = request.artifact();
        let entry = request.entry();
        let index = request.index();
        let program = request.program();
        self.calls = self.calls.saturating_add(1);
        self.kinds.push(artifact.kind());
        match self.mode {
            ReducedExecutorMode::GuardMiss => {
                return Ok(ReducedNativeExecution::GuardMiss(entry.clone()));
            },
            ReducedExecutorMode::MutatedGuardMiss => {
                return Ok(ReducedNativeExecution::GuardMiss(
                    checkpoint_with_registers(entry, ProfileRegisters {
                        accumulator: entry
                            .registers()
                            .accumulator
                            .saturating_add(1),
                        ..entry.registers()
                    })?,
                ));
            },
            ReducedExecutorMode::Apply
            | ReducedExecutorMode::TamperSuccessor
            | ReducedExecutorMode::TamperTerminal => {},
        }
        let mut machine = ProfileMachine::from_snapshot(entry.clone());
        let _outcome = machine.run(program.program.step_budget)?;
        let mut exit = machine.snapshot_state();
        if self.mode == ReducedExecutorMode::TamperSuccessor && index == 0 {
            exit = checkpoint_with_registers(&exit, ProfileRegisters {
                code_pointer: exit.registers().code_pointer.saturating_add(1),
                ..exit.registers()
            })?;
        }
        if self.mode == ReducedExecutorMode::TamperTerminal && index == 1 {
            exit = checkpoint_with_termination(&exit, None)?;
        }
        Ok(ReducedNativeExecution::Applied(exit))
    }
}

fn verified_artifact(
    source: &[u8],
    step_budget: usize,
) -> HandoffResult<VerifiedRegionArtifact> {
    let region = verified_region(source, step_budget)?;
    UntrustedRegionArtifact::from_verified_region(&region)
        .verify_against(&region)
        .map_err(|error| {
            format!("handoff artifact verification failed: {error:?}")
        })
}

fn verified_region(
    source: &[u8],
    step_budget: usize,
) -> HandoffResult<VerifiedExactRegion> {
    let machine =
        ProfileMachine::from_source(current_profile(), source, vec![0x41])
            .map_err(|error| format!("handoff source load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("handoff entry indexing failed: {error:?}"))?;
    ExactRegionCertificate::record(&entry, step_budget)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| {
            format!("handoff region verification failed: {error:?}")
        })
}

fn verified_region_from_entry(
    entry: &IndexedMachineState,
    step_budget: usize,
) -> HandoffResult<VerifiedExactRegion> {
    ExactRegionCertificate::record(entry, step_budget)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| format!("reduced graph region failed: {error:?}"))
}

fn reduced_graph_entry() -> HandoffResult<IndexedMachineState> {
    let no_operation = (33u32..=126u32)
        .find(|cell| decode_profile_instruction(*cell, 0) == Some(b'o'))
        .ok_or_else(|| String::from("reduced graph no-op cell missing"))?;
    let halt = (33u32..=126u32)
        .find(|cell| decode_profile_instruction(*cell, 1) == Some(b'v'))
        .ok_or_else(|| String::from("reduced graph halt cell missing"))?;
    let source = [
        u8::try_from(no_operation)
            .map_err(|error| format!("no-op byte conversion: {error}"))?,
        u8::try_from(halt)
            .map_err(|error| format!("halt byte conversion: {error}"))?,
    ];
    let machine =
        ProfileMachine::from_source(current_profile(), &source, Vec::new())
            .map_err(|error| {
                format!("reduced graph source load failed: {error}")
            })?;
    IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("reduced graph entry failed: {error:?}"))
}

fn reduced_graph_node(
    region: &VerifiedExactRegion,
    successor: Option<usize>,
) -> HandoffResult<AheadOfExecutionRegisterMaskedReducedStateGraphNodeClaim> {
    let artifact = UntrustedRegionArtifact::from_verified_region(region)
        .verify_against(region)
        .map_err(|error| format!("reduced graph artifact failed: {error:?}"))?;
    let witness = region
        .entry()
        .materialize_checkpoint()
        .map_err(|error| format!("reduced graph witness failed: {error:?}"))?;
    let program = artifact.program().clone();
    let identity =
        RegisterMaskedDependencyIdentityClaim::from_witness_and_program(
            &witness, &program,
        );
    Ok(AheadOfExecutionRegisterMaskedReducedStateGraphNodeClaim {
        identity,
        program,
        successor,
        witness,
    })
}

fn checkpoint_with_termination(
    state: &ProfileMachineState,
    termination: Option<Termination>,
) -> Result<ProfileMachineState, ProfileMachineError> {
    let io = ProfileMachineIoState::new(
        state.io().input().to_vec(),
        state.io().input_consumed(),
        state.io().output().to_vec(),
        termination,
    )?;
    ProfileMachineState::new_with_geometry(
        state.geometry(),
        state.memory().to_vec(),
        state.registers(),
        io,
    )
}

fn checkpoint_with_registers(
    state: &ProfileMachineState,
    registers: ProfileRegisters,
) -> Result<ProfileMachineState, ProfileMachineError> {
    ProfileMachineState::new_with_geometry(
        state.geometry(),
        state.memory().to_vec(),
        registers,
        state.io().clone(),
    )
}

fn reduced_graph_store_fixture(
    case_name: &str,
) -> HandoffResult<ReducedGraphStoreFixture> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let directory = root
        .join(".temp/state_graph_aot_handoff_store")
        .join(process_id().to_string())
        .join(case_name);
    match fs::remove_dir_all(&directory) {
        Ok(()) => {},
        Err(error) if error.kind() == ErrorKind::NotFound => {},
        Err(error) => {
            return Err(format!("cannot clear reduced graph store: {error}"));
        },
    }
    fs::create_dir_all(&directory).map_err(|error| {
        format!("cannot create reduced graph store: {error}")
    })?;
    let destination = directory.join("reduced-graph.bin");
    Ok(ReducedGraphStoreFixture { destination, directory })
}

fn remove_reduced_graph_store_fixture(directory: &Path) -> HandoffResult<()> {
    match fs::remove_dir_all(directory) {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == ErrorKind::NotFound => Ok(()),
        Err(error) => {
            Err(format!("cannot remove reduced graph store: {error}"))
        },
    }
}

fn reduced_dispatch_claim() -> HandoffResult<(
    UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
    ProfileMachineState,
)> {
    let first_entry = reduced_graph_entry()?;
    let first = verified_region_from_entry(&first_entry, 1)?;
    let exact_successor = first.exit().clone();
    let checkpoint = exact_successor
        .materialize_checkpoint()
        .map_err(|error| format!("dispatch successor checkpoint: {error:?}"))?;
    let before = checkpoint.registers();
    let changed_successor = exact_successor
        .with_validated_registers(ProfileRegisters {
            accumulator: before.accumulator.saturating_add(1),
            code_pointer: before.code_pointer,
            data_pointer: before.data_pointer,
        })
        .map_err(|error| format!("dispatch successor rebase: {error:?}"))?;
    let second = verified_region_from_entry(&changed_successor, 1)?;
    let claim =
        UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph::new(0, vec![
            reduced_graph_node(&first, Some(1))?,
            reduced_graph_node(&second, None)?,
        ]);
    let entry = first
        .entry()
        .materialize_checkpoint()
        .map_err(|error| format!("dispatch entry checkpoint: {error:?}"))?;
    Ok((claim, entry))
}

fn reduced_dispatch_fixture() -> HandoffResult<(
    VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
    ProfileMachineState,
)> {
    let (claim, entry) = reduced_dispatch_claim()?;
    let graph = claim.verify().map_err(|error| error.to_string())?;
    Ok((graph, entry))
}

fn reduced_dispatch_programs(
    graph: &VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
) -> HandoffResult<Vec<RegisterMaskedRegionEffectProgram>> {
    (0..graph.len())
        .map(|index| {
            graph
                .node(index)
                .map(|node| node.program().clone())
                .ok_or_else(|| format!("dispatch graph lost node {index}"))
        })
        .collect()
}

fn prepare_reduced_dispatch_aot(
    graph: &VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
) -> HandoffResult<VerifiedAheadOfExecutionRegisterMaskedSet> {
    let programs = reduced_dispatch_programs(graph)?;
    prepare_ahead_of_execution_register_masked_set(
        &programs,
        safe_rust_profiled_capability(),
        windows_x86_64(),
    )
    .map_err(|error| error.to_string())
}

const fn reduced_codec_limits() -> ReducedCodecLimits {
    ReducedCodecLimits::new(1)
}

const fn reduced_dispatch_request<'graph, 'aot>(
    graph: &'graph VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
    aot: &'aot VerifiedAheadOfExecutionRegisterMaskedSet,
    entry: ProfileMachineState,
    transition_budget: usize,
) -> ReducedDispatchRequest<'graph, 'aot> {
    let environment = ReducedDispatchEnvironment::new(
        aot,
        safe_rust_profiled_capability(),
        windows_x86_64(),
    );
    AheadOfExecutionRegisterMaskedReducedStateGraphDispatchRequest::new(
        graph,
        environment,
        entry,
        transition_budget,
    )
}

const fn windows_x86_64() -> DirectHost {
    DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64)
}

fn prepare_one(
    program: &RegisterMaskedRegionEffectProgram,
) -> Result<
    VerifiedAheadOfExecutionRegisterMaskedSet,
    AheadOfExecutionRegisterMaskedPreparationError<'_>,
> {
    prepare_ahead_of_execution_register_masked_set(
        from_ref(program),
        safe_rust_profiled_capability(),
        windows_x86_64(),
    )
}

#[test]
fn product_region_projection_rejects_derived_geometry_without_v6_token()
-> HandoffResult<()> {
    let width =
        verify_minimum_initial_halt_profile_width(current_profile(), b"QP")
            .map_err(|error| {
                format!("derived handoff width failed: {error}")
            })?;
    let mut machine = ProfileMachine::from_verified_source(&width, Vec::new())
        .map_err(|error| format!("derived handoff load failed: {error}"))?;
    let mut traces = Vec::new();
    let outcome = machine
        .run_traced(1, &mut |trace: &ProfileStepTrace| traces.push(*trace))
        .map_err(|error| format!("derived handoff run failed: {error}"))?;
    if RegisterMaskedRegionEffectProgram::from_profile_region_traces(
        current_profile(),
        &traces,
        1,
        outcome,
    ) == Err(RegisterMaskedRegionProjectionError::Step {
        error: StepProgramProjectionError::ExecutionGeometry,
        index: 0,
    }) {
        Ok(())
    } else {
        Err(String::from(
            "v6 product handoff admitted unrepresented derived geometry",
        ))
    }
}

#[test]
fn product_region_projection_matches_verified_research_artifact()
-> HandoffResult<()> {
    let region = verified_region(MULTI_STEP_SOURCE, 8)?;
    let artifact = UntrustedRegionArtifact::from_verified_region(&region)
        .verify_against(&region)
        .map_err(|error| format!("artifact verification failed: {error:?}"))?;
    let projected =
        RegisterMaskedRegionEffectProgram::from_profile_region_traces(
            region.entry().profile_descriptor(),
            region.traces(),
            region.step_budget(),
            region.outcome(),
        )
        .map_err(|error| {
            format!("product region projection failed: {error:?}")
        })?;
    if artifact.program() == &projected {
        Ok(())
    } else {
        Err(String::from("product and research v6 projection diverged"))
    }
}

#[test]
fn product_region_projection_rejects_cross_profile_trace() -> HandoffResult<()>
{
    let region = verified_region(MULTI_STEP_SOURCE, 8)?;
    let mut traces = region.traces().to_vec();
    let first = traces
        .first_mut()
        .ok_or_else(|| String::from("multi-step region lacked first trace"))?;
    first.profile = malbolge::historical_profile();
    if RegisterMaskedRegionEffectProgram::from_profile_region_traces(
        region.entry().profile_descriptor(),
        &traces,
        region.step_budget(),
        region.outcome(),
    ) == Err(RegisterMaskedRegionProjectionError::ProfileMismatch {
        index: 0,
    }) {
        Ok(())
    } else {
        Err(String::from("cross-profile region trace was admitted"))
    }
}

#[test]
fn product_region_projection_rejects_discontinuous_and_false_outcome()
-> HandoffResult<()> {
    let region = verified_region(MULTI_STEP_SOURCE, 8)?;
    let mut traces = region.traces().to_vec();
    let second = traces
        .get_mut(1)
        .ok_or_else(|| String::from("multi-step region lacked second trace"))?;
    second.before.input_consumed =
        second.before.input_consumed.saturating_add(1);
    if RegisterMaskedRegionEffectProgram::from_profile_region_traces(
        region.entry().profile_descriptor(),
        &traces,
        region.step_budget(),
        region.outcome(),
    ) != Err(RegisterMaskedRegionProjectionError::DiscontinuousTrace {
        index: 1,
    }) {
        return Err(String::from(
            "discontinuous region projection was admitted",
        ));
    }
    if RegisterMaskedRegionEffectProgram::from_profile_region_traces(
        region.entry().profile_descriptor(),
        region.traces(),
        region.step_budget(),
        RunOutcome::BudgetExhausted { steps: 0 },
    ) == Err(RegisterMaskedRegionProjectionError::Outcome)
    {
        Ok(())
    } else {
        Err(String::from("false region outcome was admitted"))
    }
}

#[test]
fn verified_research_halt_artifact_crosses_product_v6_aot_boundary()
-> HandoffResult<()> {
    let artifact = verified_artifact(b"QP", 1)?;
    let program = artifact.program();
    let aot = prepare_one(program).map_err(|error| error.to_string())?;
    let selected = select_ahead_of_execution_register_masked_tier(
        program,
        safe_rust_profiled_capability(),
        windows_x86_64(),
        &aot,
    )
    .map_err(|error| error.to_string())?;
    let AheadOfExecutionRegisterMaskedTier::Direct(native) = selected else {
        return Err(String::from(
            "verified research v6 IR missed prepared AOT",
        ));
    };
    if native.kind() == DirectNativeKind::HaltFetch && aot.len() == 1 {
        Ok(())
    } else {
        Err(String::from(
            "research handoff changed admitted native shape",
        ))
    }
}

#[test]
fn verified_multi_step_research_artifact_fails_closed_at_current_aot_boundary()
-> HandoffResult<()> {
    let artifact = verified_artifact(MULTI_STEP_SOURCE, 8)?;
    let Err(AheadOfExecutionRegisterMaskedPreparationError::Admission {
        error,
        index: 0,
    }) = prepare_one(artifact.program())
    else {
        return Err(String::from(concat!(
            "multi-step research artifact unexpectedly gained native AOT ",
            "authority",
        )));
    };
    if error.kind()
        == RegisterMaskedDirectAdmissionErrorKind::UnsupportedProgram
    {
        Ok(())
    } else {
        Err(String::from(
            "multi-step research handoff changed fail-closed admission reason",
        ))
    }
}

#[test]
fn verified_research_regions_import_as_product_reduced_graph()
-> HandoffResult<()> {
    let first_entry = reduced_graph_entry()?;
    let first = verified_region_from_entry(&first_entry, 1)?;
    if first.outcome() != (RunOutcome::BudgetExhausted { steps: 1 }) {
        return Err(format!(
            "reduced graph first outcome: {:?}",
            first.outcome()
        ));
    }

    let exact_successor = first.exit().clone();
    let checkpoint = exact_successor
        .materialize_checkpoint()
        .map_err(|error| format!("reduced successor checkpoint: {error:?}"))?;
    let before = checkpoint.registers();
    let changed_successor = exact_successor
        .with_validated_registers(ProfileRegisters {
            accumulator: before.accumulator.saturating_add(1),
            code_pointer: before.code_pointer,
            data_pointer: before.data_pointer,
        })
        .map_err(|error| format!("reduced successor rebase: {error:?}"))?;
    if exact_successor.exact_state_eq(&changed_successor) {
        return Err(String::from("reduced successor remained exact-equal"));
    }
    let second = verified_region_from_entry(&changed_successor, 1)?;
    if !matches!(second.outcome(), RunOutcome::Terminated { steps: 1, .. }) {
        return Err(format!(
            "reduced graph second outcome: {:?}",
            second.outcome()
        ));
    }

    let nodes = vec![
        reduced_graph_node(&first, Some(1))?,
        reduced_graph_node(&second, None)?,
    ];
    let claim =
        UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph::new(0, nodes);
    let graph = claim.verify().map_err(|error| error.to_string())?;
    let successor = graph
        .node(1)
        .ok_or_else(|| String::from("reduced successor node missing"))?;
    let exact_exit = first
        .exit()
        .materialize_checkpoint()
        .map_err(|error| format!("reduced first exit: {error:?}"))?;
    if graph.entry() == 0
        && graph.len() == 2
        && !graph.is_empty()
        && successor.identity().matches(&exact_exit)
        && !successor.identity().register_live_ins().accumulator
        && successor.identity().register_values().accumulator == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "reduced graph import lost dependency identity",
        ))
    }
}

#[test]
fn product_reduced_graph_rejects_false_identity_and_edge() -> HandoffResult<()>
{
    let first_entry = reduced_graph_entry()?;
    let first = verified_region_from_entry(&first_entry, 1)?;
    let second = verified_region_from_entry(first.exit(), 1)?;
    let mut identity_nodes = vec![
        reduced_graph_node(&first, Some(1))?,
        reduced_graph_node(&second, None)?,
    ];
    let first_claim = identity_nodes
        .first_mut()
        .ok_or_else(|| String::from("reduced first claim missing"))?;
    first_claim.identity.register_values.code_pointer = first_claim
        .identity
        .register_values
        .code_pointer
        .saturating_add(1);
    let false_identity =
        UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph::new(
            0,
            identity_nodes,
        );
    if false_identity.verify()
        != Err(ReducedGraphError::IdentityMismatch { index: 0 })
    {
        return Err(String::from("reduced graph admitted false identity"));
    }

    let terminal_entry = reduced_graph_entry()?;
    let prefix = verified_region_from_entry(&terminal_entry, 1)?;
    let terminal = verified_region_from_entry(prefix.exit(), 1)?;
    let unrelated = verified_region(b"QP", 1)?;
    let false_edge =
        UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph::new(0, vec![
            reduced_graph_node(&prefix, Some(2))?,
            reduced_graph_node(&terminal, None)?,
            reduced_graph_node(&unrelated, None)?,
        ]);
    if false_edge.verify()
        == Err(ReducedGraphError::SuccessorIdentityMismatch {
            index: 0,
            successor: 2,
        })
    {
        Ok(())
    } else {
        Err(String::from("reduced graph admitted false successor guard"))
    }
}

fn rebased_checkpoint(
    witness: &ProfileMachineState,
    input: Vec<u8>,
    input_cursor: usize,
    output: Vec<u8>,
) -> HandoffResult<ProfileMachineState> {
    let io = ProfileMachineIoState::new(
        input,
        input_cursor,
        output,
        witness.io().termination(),
    )
    .map_err(|error| format!("reduced rebase IO failed: {error}"))?;
    ProfileMachineState::new(
        witness.profile(),
        witness.memory().to_vec(),
        witness.registers(),
        io,
    )
    .map_err(|error| format!("reduced rebase checkpoint failed: {error}"))
}

#[test]
fn product_reduced_identity_rebases_relative_input_and_history()
-> HandoffResult<()> {
    let machine =
        ProfileMachine::from_source(current_profile(), b"uP", vec![0x41, 0x55])
            .map_err(|error| {
                format!("input reduced source load failed: {error}")
            })?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("input reduced entry failed: {error:?}"))?;
    let first = verified_region_from_entry(&entry, 1)?;
    let second = verified_region_from_entry(first.exit(), 1)?;
    let claim =
        UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph::new(0, vec![
            reduced_graph_node(&first, Some(1))?,
            reduced_graph_node(&second, None)?,
        ]);
    let graph = claim.verify().map_err(|error| error.to_string())?;
    let identity = graph
        .node(0)
        .ok_or_else(|| String::from("input reduced node missing"))?
        .identity();
    let witness = first
        .entry()
        .materialize_checkpoint()
        .map_err(|error| format!("input reduced witness failed: {error:?}"))?;
    let rebased =
        rebased_checkpoint(&witness, vec![0x99, 0x41, 0x77], 1, vec![0xee])?;
    let mismatched =
        rebased_checkpoint(&witness, vec![0x99, 0x42, 0x77], 1, vec![0xee])?;
    if identity.matches(&rebased)
        && !identity.matches(&mismatched)
        && identity.relative_inputs().len() == 1
    {
        Ok(())
    } else {
        Err(String::from(
            "reduced identity lost relative-input semantics",
        ))
    }
}

#[test]
fn product_reduced_graph_durable_codec_replays_authority() -> HandoffResult<()>
{
    let (claim, _entry) = reduced_dispatch_claim()?;
    let expected = claim.verify().map_err(|error| error.to_string())?;
    let first =
        encode_ahead_of_execution_register_masked_reduced_state_graph(&claim)
            .map_err(|error| error.to_string())?;
    let second =
        encode_ahead_of_execution_register_masked_reduced_state_graph(&claim)
            .map_err(|error| error.to_string())?;
    let loaded = decode_ahead_of_execution_register_masked_reduced_state_graph(
        &first,
        reduced_codec_limits(),
    )
    .map_err(|error| error.to_string())?;
    if first == second && loaded == expected {
        Ok(())
    } else {
        Err(String::from(
            "durable reduced graph bytes changed replayed authority",
        ))
    }
}

#[test]
fn product_reduced_durable_codec_rejects_bad_framing() -> HandoffResult<()> {
    let (claim, _entry) = reduced_dispatch_claim()?;
    let bytes =
        encode_ahead_of_execution_register_masked_reduced_state_graph(&claim)
            .map_err(|error| error.to_string())?;

    let mut bad_magic = bytes.clone();
    let first = bad_magic
        .first_mut()
        .ok_or_else(|| String::from("durable graph bytes were empty"))?;
    *first ^= 0xff;
    if decode_ahead_of_execution_register_masked_reduced_state_graph(
        &bad_magic,
        reduced_codec_limits(),
    ) != Err(ReducedCodecError::Magic)
    {
        return Err(String::from("durable graph accepted wrong magic"));
    }

    let fingerprint = current_profile().fingerprint().as_bytes();
    let mut bad_fingerprint = bytes.clone();
    let fingerprint_offset = bad_fingerprint
        .windows(fingerprint.len())
        .position(|window| window == fingerprint)
        .ok_or_else(|| {
            String::from("durable graph omitted profile fingerprint")
        })?;
    let fingerprint_byte =
        bad_fingerprint.get_mut(fingerprint_offset).ok_or_else(|| {
            String::from("durable graph fingerprint offset vanished")
        })?;
    *fingerprint_byte ^= 0xff;
    if decode_ahead_of_execution_register_masked_reduced_state_graph(
        &bad_fingerprint,
        reduced_codec_limits(),
    ) != Err(ReducedCodecError::ProfileFingerprint)
    {
        return Err(String::from(
            "durable graph accepted wrong profile fingerprint",
        ));
    }

    let mut trailing = bytes.clone();
    trailing.push(0);
    if decode_ahead_of_execution_register_masked_reduced_state_graph(
        &trailing,
        reduced_codec_limits(),
    ) != Err(ReducedCodecError::TrailingBytes)
    {
        return Err(String::from("durable graph accepted trailing bytes"));
    }

    let mut truncated = bytes;
    let _last = truncated
        .pop()
        .ok_or_else(|| String::from("durable graph bytes were empty"))?;
    if decode_ahead_of_execution_register_masked_reduced_state_graph(
        &truncated,
        reduced_codec_limits(),
    ) == Err(ReducedCodecError::Truncated)
    {
        Ok(())
    } else {
        Err(String::from("durable graph accepted truncated bytes"))
    }
}

#[test]
fn product_reduced_durable_codec_bounds_replay_work() -> HandoffResult<()> {
    let (claim, _entry) = reduced_dispatch_claim()?;
    let bytes =
        encode_ahead_of_execution_register_masked_reduced_state_graph(&claim)
            .map_err(|error| error.to_string())?;
    let result = decode_ahead_of_execution_register_masked_reduced_state_graph(
        &bytes,
        ReducedCodecLimits::new(0),
    );
    if matches!(
        result,
        Err(ReducedCodecError::ReplayStepLimit {
            index: 0,
            limit: 0,
            observed: 1,
        })
    ) {
        Ok(())
    } else {
        Err(format!("durable graph ignored replay limit: {result:?}"))
    }
}

#[test]
fn product_reduced_graph_durable_encoder_requires_admission()
-> HandoffResult<()> {
    let entry = reduced_graph_entry()?;
    let region = verified_region_from_entry(&entry, 1)?;
    let mut node = reduced_graph_node(&region, Some(0))?;
    node.identity.register_values.accumulator =
        node.identity.register_values.accumulator.saturating_add(1);
    let claim =
        UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph::new(0, vec![
            node,
        ]);
    if matches!(
        encode_ahead_of_execution_register_masked_reduced_state_graph(&claim),
        Err(ReducedCodecError::Graph(
            ReducedGraphError::IdentityMismatch { index: 0 }
        ))
    ) {
        Ok(())
    } else {
        Err(String::from(
            "durable graph encoder serialized unadmitted evidence",
        ))
    }
}

fn first_reduced_aot_program()
-> HandoffResult<RegisterMaskedRegionEffectProgram> {
    let (graph, _entry) = reduced_dispatch_fixture()?;
    graph
        .node(0)
        .map(|node| node.program().clone())
        .ok_or_else(|| {
            String::from("reduced AOT object fixture lost first node")
        })
}

fn select_prepared_reduced_artifact(
    program: &RegisterMaskedRegionEffectProgram,
) -> HandoffResult<
    Arc<execution_native::VerifiedAheadOfExecutionRegisterMaskedArtifact>,
> {
    let aot = prepare_one(program).map_err(|error| error.to_string())?;
    match select_ahead_of_execution_register_masked_tier(
        program,
        safe_rust_profiled_capability(),
        windows_x86_64(),
        &aot,
    )
    .map_err(|error| error.to_string())?
    {
        AheadOfExecutionRegisterMaskedTier::Direct(artifact) => Ok(artifact),
        AheadOfExecutionRegisterMaskedTier::Interpreter => Err(String::from(
            "object fixture unexpectedly selected interpreter",
        )),
        AheadOfExecutionRegisterMaskedTier::Uncovered => {
            Err(String::from("object fixture was absent after preparation"))
        },
    }
}

const fn bundle_persist_request<'bundle>(
    programs: &'bundle [RegisterMaskedRegionEffectProgram],
    aot: &'bundle VerifiedAheadOfExecutionRegisterMaskedSet,
    maximum_bytes: NonZeroUsize,
) -> RegisterMaskedAotBundlePersistRequest<'bundle> {
    let source = RegisterMaskedAotBundleSource::new(
        programs,
        aot,
        safe_rust_profiled_capability(),
        windows_x86_64(),
    );
    RegisterMaskedAotBundlePersistRequest::new(source, maximum_bytes)
}

const fn bundle_restore_request(
    programs: &[RegisterMaskedRegionEffectProgram],
    maximum_bytes: NonZeroUsize,
) -> RegisterMaskedAotBundleRestoreRequest<'_> {
    RegisterMaskedAotBundleRestoreRequest::new(
        programs,
        safe_rust_profiled_capability(),
        windows_x86_64(),
        maximum_bytes,
    )
}

fn aot_package_bounds() -> HandoffResult<AotPackageBounds> {
    Ok(AotPackageBounds {
        bundle: NonZeroUsize::new(65_536).ok_or_else(|| {
            String::from("AOT package bundle bound became zero")
        })?,
        graph: NonZeroUsize::new(128 * 1024 * 1024).ok_or_else(|| {
            String::from("AOT package graph bound became zero")
        })?,
    })
}

fn aot_package_material() -> HandoffResult<AotPackageMaterial> {
    let (claim, _entry) = reduced_dispatch_claim()?;
    let graph = claim.verify().map_err(|error| error.to_string())?;
    let programs = reduced_dispatch_programs(&graph)?;
    let aot = prepare_reduced_dispatch_aot(&graph)?;
    Ok((claim, graph, programs, aot))
}

const fn package_persist_request<'package>(
    claim: &'package ReducedGraphClaim,
    programs: &'package [RegisterMaskedRegionEffectProgram],
    aot: &'package VerifiedAheadOfExecutionRegisterMaskedSet,
    bounds: AotPackageBounds,
) -> RegisterMaskedAotPackagePersistRequest<'package> {
    let bundle = RegisterMaskedAotBundleSource::new(
        programs,
        aot,
        safe_rust_profiled_capability(),
        windows_x86_64(),
    );
    let source = RegisterMaskedAotPackageSource::new(claim, bundle);
    RegisterMaskedAotPackagePersistRequest::new(
        source,
        bounds.graph,
        bounds.bundle,
    )
}

const fn package_restore_request(
    programs: &[RegisterMaskedRegionEffectProgram],
    bounds: AotPackageBounds,
) -> RegisterMaskedAotPackageRestoreRequest<'_> {
    let bundle = RegisterMaskedAotBundleRestoreRequest::new(
        programs,
        safe_rust_profiled_capability(),
        windows_x86_64(),
        bounds.bundle,
    );
    RegisterMaskedAotPackageRestoreRequest::new(
        bundle,
        reduced_codec_limits(),
        bounds.graph,
    )
}

const fn object_restore_request(
    program: &RegisterMaskedRegionEffectProgram,
    maximum_bytes: NonZeroUsize,
) -> RegisterMaskedAotObjectRestoreRequest<'_> {
    RegisterMaskedAotObjectRestoreRequest::new(
        program,
        safe_rust_profiled_capability(),
        windows_x86_64(),
        maximum_bytes,
    )
}

fn expect_reduced_graph_blob_missing(
    store: &mut NativeContinuationFileBlobStore,
    maximum_bytes: NonZeroUsize,
) -> HandoffResult<()> {
    let result = restore_register_masked_reduced_graph(
        store,
        maximum_bytes,
        reduced_codec_limits(),
    )
    .map_err(|error| format!("missing graph restore: {error:?}"))?;
    if result == RegisterMaskedReducedGraphPersistenceLoad::Missing {
        Ok(())
    } else {
        Err(String::from("missing graph blob invented state"))
    }
}

fn persist_and_restore_register_masked_reduced_graph(
    store: &mut NativeContinuationFileBlobStore,
    claim: &ReducedGraphClaim,
    expected: &ReducedGraph,
    maximum_bytes: NonZeroUsize,
) -> HandoffResult<()> {
    let durable = persist_register_masked_reduced_graph_durably(
        store,
        claim,
        maximum_bytes,
    )
    .map_err(|error| format!("durable graph persist: {error:?}"))?;
    if !durable.is_durable() || durable.bytes() == 0 {
        return Err(String::from("graph blob durability was not confirmed"));
    }
    let restored = restore_register_masked_reduced_graph(
        store,
        maximum_bytes,
        reduced_codec_limits(),
    )
    .map_err(|error| format!("durable graph restore: {error:?}"))?;
    match restored {
        RegisterMaskedReducedGraphPersistenceLoad::Restored {
            bytes,
            graph,
        } if bytes == durable.bytes() && graph == *expected => Ok(()),
        RegisterMaskedReducedGraphPersistenceLoad::Missing => {
            Err(String::from("durable graph disappeared after publication"))
        },
        RegisterMaskedReducedGraphPersistenceLoad::Restored {
            bytes,
            graph,
        } => Err(format!(
            "durable graph round-trip drifted: bytes={bytes} graph={graph:?}"
        )),
    }
}

fn expect_hostile_bundle_count_rejected(
    store: &mut NativeContinuationFileBlobStore,
    canonical: &[u8],
    programs: &[RegisterMaskedRegionEffectProgram],
    maximum_bytes: NonZeroUsize,
) -> HandoffResult<()> {
    let mut hostile_count = canonical.to_vec();
    hostile_count
        .get_mut(6..10)
        .ok_or_else(|| String::from("AOT bundle count framing missing"))?
        .copy_from_slice(&u32::MAX.to_le_bytes());
    blob_store::NativeContinuationBlobStore::replace(store, &hostile_count)
        .map_err(|error| {
            format!("cannot seed hostile bundle count: {error:?}")
        })?;
    let hostile = restore_register_masked_aot_bundle(
        store,
        bundle_restore_request(programs, maximum_bytes),
    );
    if hostile
        == Err(RegisterMaskedAotBundleRestorePersistenceError::Framing(
            RegisterMaskedAotBundleFramingError::CountMismatch {
                expected: programs.len(),
                observed: u32::MAX,
            },
        ))
    {
        Ok(())
    } else {
        Err(format!("hostile bundle count was accepted: {hostile:?}"))
    }
}

fn expect_trailing_bundle_rejected(
    store: &mut NativeContinuationFileBlobStore,
    canonical: &[u8],
    programs: &[RegisterMaskedRegionEffectProgram],
    maximum_bytes: NonZeroUsize,
) -> HandoffResult<()> {
    let mut trailing = canonical.to_vec();
    trailing.push(0);
    blob_store::NativeContinuationBlobStore::replace(store, &trailing)
        .map_err(|error| format!("cannot seed trailing bundle: {error:?}"))?;
    let result = restore_register_masked_aot_bundle(
        store,
        bundle_restore_request(programs, maximum_bytes),
    );
    if result
        == Err(RegisterMaskedAotBundleRestorePersistenceError::Framing(
            RegisterMaskedAotBundleFramingError::Trailing,
        ))
    {
        Ok(())
    } else {
        Err(format!("trailing AOT bundle was accepted: {result:?}"))
    }
}

fn evict_bundle_and_require_missing(
    store: &mut NativeContinuationFileBlobStore,
    programs: &[RegisterMaskedRegionEffectProgram],
    maximum_bytes: NonZeroUsize,
) -> HandoffResult<()> {
    let eviction = evict_register_masked_aot_bundle_durably(store)
        .map_err(|error| format!("durable AOT bundle eviction: {error:?}"))?;
    if !eviction.is_removed() {
        return Err(String::from("durable AOT bundle was not evicted"));
    }
    let load = restore_register_masked_aot_bundle(
        store,
        bundle_restore_request(programs, maximum_bytes),
    )
    .map_err(|error| format!("post-eviction AOT bundle restore: {error:?}"))?;
    if load == RegisterMaskedAotBundlePersistenceLoad::Missing {
        Ok(())
    } else {
        Err(String::from("evicted AOT bundle remained restorable"))
    }
}

fn evict_object_and_require_missing(
    store: &mut NativeContinuationFileBlobStore,
    program: &RegisterMaskedRegionEffectProgram,
    maximum_bytes: NonZeroUsize,
) -> HandoffResult<()> {
    let eviction = evict_register_masked_aot_object_durably(store)
        .map_err(|error| format!("durable AOT object eviction: {error:?}"))?;
    if !eviction.is_removed() {
        return Err(String::from("durable AOT object was not evicted"));
    }
    let load = restore_register_masked_aot_object(
        store,
        object_restore_request(program, maximum_bytes),
    )
    .map_err(|error| format!("post-eviction AOT object restore: {error:?}"))?;
    if load == RegisterMaskedAotObjectPersistenceLoad::Missing {
        Ok(())
    } else {
        Err(String::from("evicted AOT object remained restorable"))
    }
}

fn load_aot_package_pair(
    store: &mut NativeContinuationFileBlobPairStore,
    bounds: AotPackageBounds,
) -> HandoffResult<blob_pair_store::NativeContinuationBlobPair> {
    BlobPairStore::load_pair(store, bounds.graph, bounds.bundle)
        .map_err(|error| format!("load AOT package pair: {error:?}"))?
        .ok_or_else(|| String::from("AOT package pair disappeared"))
}

fn verify_restored_aot_package(
    restored: RegisterMaskedAotPackagePersistenceLoad,
    expected_graph: &ReducedGraph,
    programs: &[RegisterMaskedRegionEffectProgram],
    expected_bytes: (usize, usize),
) -> HandoffResult<()> {
    let RegisterMaskedAotPackagePersistenceLoad::Restored {
        bundle_bytes,
        graph,
        graph_bytes,
        objects,
        set,
    } = restored
    else {
        return Err(String::from("durable AOT package disappeared"));
    };
    if (graph_bytes, bundle_bytes) != expected_bytes
        || objects != programs.len()
        || graph != *expected_graph
    {
        return Err(String::from("AOT package round-trip evidence drifted"));
    }
    for program in programs {
        let selected = select_ahead_of_execution_register_masked_tier(
            program,
            safe_rust_profiled_capability(),
            windows_x86_64(),
            &set,
        )
        .map_err(|error| error.to_string())?;
        if !matches!(selected, AheadOfExecutionRegisterMaskedTier::Direct(_)) {
            return Err(String::from(
                "restored AOT package lost exact native coverage",
            ));
        }
    }
    Ok(())
}

fn restore_versioned_aot_package_revision(
    store: &mut NativeContinuationFileBlobPairStore,
    expected_graph: &ReducedGraph,
    programs: &[RegisterMaskedRegionEffectProgram],
    bounds: AotPackageBounds,
) -> HandoffResult<NativeContinuationFileBlobPairRevision> {
    let restored = restore_register_masked_aot_package_versioned(
        store,
        package_restore_request(programs, bounds),
    )
    .map_err(|error| format!("versioned AOT package restore: {error:?}"))?;
    let RegisterMaskedAotPackageVersionedPersistenceLoad::Restored {
        graph,
        objects,
        revision,
        set,
        ..
    } = restored
    else {
        return Err(String::from("versioned AOT package disappeared"));
    };
    if graph != *expected_graph || objects != programs.len() {
        return Err(String::from("versioned AOT package authority drifted"));
    }
    for program in programs {
        let selected = select_ahead_of_execution_register_masked_tier(
            program,
            safe_rust_profiled_capability(),
            windows_x86_64(),
            &set,
        )
        .map_err(|error| error.to_string())?;
        if !matches!(selected, AheadOfExecutionRegisterMaskedTier::Direct(_)) {
            return Err(String::from(
                "versioned AOT package lost exact native coverage",
            ));
        }
    }
    Ok(revision)
}

#[test]
fn product_register_masked_aot_package_round_trips_atomically()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("aot_package_round_trip")?;
    let result = (|| -> HandoffResult<()> {
        let (claim, graph, programs, aot) = aot_package_material()?;
        let bounds = aot_package_bounds()?;
        let manifest = fixture.directory.join("aot-package.manifest");
        let mut store = NativeContinuationFileBlobPairStore::new(manifest);
        let read_guard = store
            .open_read_lock_for_test()
            .map_err(|error| format!("AOT package read lock: {error:?}"))?;
        drop(read_guard);
        let durable = persist_register_masked_aot_package_durably(
            &mut store,
            package_persist_request(&claim, &programs, &aot, bounds),
        )
        .map_err(|error| format!("durable AOT package persist: {error:?}"))?;
        let expected_bytes = (
            durable.write().first_bytes(),
            durable.write().second_bytes(),
        );
        if !durable.is_durable()
            || expected_bytes.0 == 0
            || expected_bytes.1 == 0
        {
            return Err(String::from(
                "AOT package durability evidence was incomplete",
            ));
        }
        let restored = restore_register_masked_aot_package(
            &mut store,
            package_restore_request(&programs, bounds),
        )
        .map_err(|error| format!("durable AOT package restore: {error:?}"))?;
        verify_restored_aot_package(restored, &graph, &programs, expected_bytes)
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

fn require_durable_aot_package_publication(
    outcome: &AotPackageFileConditional,
) -> HandoffResult<NativeContinuationFileBlobPairRevision> {
    match outcome {
        RegisterMaskedAotPackageConditionalDurablePersistence::Durable {
            revision,
            ..
        } => Ok(*revision),
        RegisterMaskedAotPackageConditionalDurablePersistence::Conflict => {
            Err(String::from("AOT package publication conflicted"))
        },
        RegisterMaskedAotPackageConditionalDurablePersistence::Published {
            ..
        } => Err(String::from("AOT package publication was not durable")),
    }
}

fn publish_aot_package_conditionally(
    store: &mut NativeContinuationFileBlobPairStore,
    expected: Option<&NativeContinuationFileBlobPairRevision>,
    request: RegisterMaskedAotPackagePersistRequest<'_>,
) -> HandoffResult<NativeContinuationFileBlobPairRevision> {
    let outcome = compare_and_swap_register_masked_aot_package_durably(
        store, expected, request,
    )
    .map_err(|error| format!("AOT package conditional publish: {error:?}"))?;
    require_durable_aot_package_publication(&outcome)
}

fn require_stale_aot_package_conflict(
    store: &mut NativeContinuationFileBlobPairStore,
    expected: &NativeContinuationFileBlobPairRevision,
    request: RegisterMaskedAotPackagePersistRequest<'_>,
) -> HandoffResult<()> {
    let outcome = compare_and_swap_register_masked_aot_package_durably(
        store,
        Some(expected),
        request,
    )
    .map_err(|error| format!("stale AOT package CAS: {error:?}"))?;
    if outcome
        == RegisterMaskedAotPackageConditionalDurablePersistence::Conflict
    {
        Ok(())
    } else {
        Err(String::from("stale AOT package revision was accepted"))
    }
}

fn aot_package_lease_transition_request(
    owner: u8,
) -> HandoffResult<NativeExecutableDurableLeaseTransitionRequest> {
    aot_package_lease_transition_request_with_limit(owner, 4)
}

fn aot_package_lease_transition_request_with_limit(
    owner: u8,
    maximum_owner_count: usize,
) -> HandoffResult<NativeExecutableDurableLeaseTransitionRequest> {
    let maximum_owners = NonZeroUsize::new(maximum_owner_count)
        .ok_or_else(|| String::from("AOT package lease owner bound missing"))?;
    let maximum_bytes = NonZeroUsize::new(4096)
        .ok_or_else(|| String::from("AOT package lease byte bound missing"))?;
    Ok(NativeExecutableDurableLeaseTransitionRequest::new(
        NativeExecutableDurableLeaseOwnerId::new([owner; 16]),
        NativeExecutableDurableLeaseRegistryDecodeLimits::new(maximum_owners),
        maximum_bytes,
    ))
}

fn acquire_guarded_aot_package_lease(
    coordination: &NativeContinuationFileCoordination,
    lease: &mut NativeContinuationFileBlobStore,
    request: NativeExecutableDurableLeaseTransitionRequest,
) -> HandoffResult<()> {
    let outcome = package_lease::acquire_file_aot_package_durable_lease(
        coordination,
        lease,
        request,
    )
    .map_err(|error| format!("guarded lease acquire: {error:?}"))?;
    require_aot_package_lease_owners(&outcome, 1)
}

fn release_guarded_aot_package_lease(
    coordination: &NativeContinuationFileCoordination,
    lease: &mut NativeContinuationFileBlobStore,
    request: NativeExecutableDurableLeaseTransitionRequest,
) -> HandoffResult<()> {
    let outcome = package_lease::release_file_aot_package_durable_lease(
        coordination,
        lease,
        request,
    )
    .map_err(|error| format!("guarded lease release: {error:?}"))?;
    require_aot_package_lease_owners(&outcome, 0)
}

fn require_aot_package_lease_owners(
    outcome: &FileAotPackageLeaseTransition,
    expected_owners: usize,
) -> HandoffResult<()> {
    if matches!(
        outcome,
        NativeExecutableDurableLeaseTransition::Durable { registry, .. }
            if registry.len() == expected_owners
    ) {
        Ok(())
    } else {
        Err(String::from("guarded package lease owner count drifted"))
    }
}

fn reclaim_guarded_aot_package_from_lease(
    package: &mut NativeContinuationFileBlobPairStore,
    lease: &NativeContinuationFileBlobStore,
    context: GuardedAotPackageLeaseContext<'_>,
) -> HandoffResult<AotPackageFileReclamation> {
    package_lease::reclaim_file_aot_package_from_lease_snapshot(
        context.coordination,
        package,
        package_restore_request(context.programs, context.bounds),
        |guard| {
            package_lease::capture_file_aot_package_lease_snapshot(
                lease,
                guard,
                context.revision,
                context.lease_request,
            )
            .map(|snapshot| vec![snapshot])
        },
    )
    .map_err(|error| format!("guarded AOT package reclaim: {error:?}"))
}

fn aot_package_generation_member(
    manifest: &Path,
    revision: NativeContinuationFileBlobPairRevision,
    member: &str,
) -> HandoffResult<PathBuf> {
    let encoded = revision.encode();
    let epoch: [u8; 8] = encoded[8..16]
        .try_into()
        .map_err(|_error| String::from("AOT package epoch decode failed"))?;
    let generation: [u8; 8] = encoded[16..24].try_into().map_err(|_error| {
        String::from("AOT package generation decode failed")
    })?;
    let name = manifest
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or_else(|| String::from("AOT package manifest name missing"))?;
    Ok(manifest.with_file_name(format!(
        "{name}.generation.{}.{generation_id}.{member}",
        u64::from_le_bytes(epoch),
        generation_id = u64::from_le_bytes(generation),
    )))
}

fn require_aot_package_reclamation(
    outcome: AotPackageFileReclamation,
    expected_revision: NativeContinuationFileBlobPairRevision,
    expected_retained: usize,
    expected_removed: usize,
) -> HandoffResult<()> {
    let RegisterMaskedAotPackageReclamation::Reclaimed {
        current_revision,
        reclamation,
        retained_revisions,
    } = outcome
    else {
        return Err(String::from("current AOT package disappeared"));
    };
    if current_revision == expected_revision
        && retained_revisions == expected_retained
        && reclamation.removed().len() == expected_removed
    {
        Ok(())
    } else {
        Err(String::from("AOT package reclamation evidence drifted"))
    }
}

#[test]
fn product_register_masked_aot_package_reclaim_rejects_corrupt_current()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("aot_package_reclaim_corrupt")?;
    let result = (|| -> HandoffResult<()> {
        let (claim, graph, programs, aot) = aot_package_material()?;
        let bounds = aot_package_bounds()?;
        let manifest = fixture.directory.join("aot-package.manifest");
        let mut store =
            NativeContinuationFileBlobPairStore::new(manifest.clone());
        let _first = persist_register_masked_aot_package_durably(
            &mut store,
            package_persist_request(&claim, &programs, &aot, bounds),
        )
        .map_err(|error| format!("first corrupt-case persist: {error:?}"))?;
        let first_revision = restore_versioned_aot_package_revision(
            &mut store, &graph, &programs, bounds,
        )?;
        let _second = persist_register_masked_aot_package_durably(
            &mut store,
            package_persist_request(&claim, &programs, &aot, bounds),
        )
        .map_err(|error| format!("second corrupt-case persist: {error:?}"))?;
        let current_revision = restore_versioned_aot_package_revision(
            &mut store, &graph, &programs, bounds,
        )?;
        let current_bundle = aot_package_generation_member(
            &manifest,
            current_revision,
            "second",
        )?;
        fs::write(current_bundle, b"corrupt-package-bundle")
            .map_err(|error| format!("corrupt current AOT package: {error}"))?;
        let retention = NativeContinuationBlobPairRetention::new();
        let error = reclaim_register_masked_aot_package_generations(
            &mut store,
            package_restore_request(&programs, bounds),
            &retention,
        )
        .err()
        .ok_or_else(|| String::from("corrupt current package was reclaimed"))?;
        let first_graph =
            aot_package_generation_member(&manifest, first_revision, "first")?;
        let first_bundle =
            aot_package_generation_member(&manifest, first_revision, "second")?;
        if matches!(error, RegisterMaskedAotPackageReclamationError::Restore(_))
            && first_graph.exists()
            && first_bundle.exists()
        {
            Ok(())
        } else {
            Err(String::from("corrupt package reclamation failed open"))
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_package_lease_is_idempotent_under_guard()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("aot_package_lease_idempotent")?;
    let result = (|| -> HandoffResult<()> {
        let coordination = NativeContinuationFileCoordination::new(
            fixture.directory.join("package.lock"),
        );
        let mut lease = NativeContinuationFileBlobStore::with_coordination(
            fixture.directory.join("lease.bin"),
            coordination.clone(),
        );
        let request = aot_package_lease_transition_request(5)?;
        let first = package_lease::acquire_file_aot_package_durable_lease(
            &coordination,
            &mut lease,
            request,
        )
        .map_err(|error| format!("first guarded acquire: {error:?}"))?;
        require_aot_package_lease_owners(&first, 1)?;
        let duplicate = package_lease::acquire_file_aot_package_durable_lease(
            &coordination,
            &mut lease,
            request,
        )
        .map_err(|error| format!("duplicate guarded acquire: {error:?}"))?;
        let duplicate_ok = matches!(
            &duplicate,
            NativeExecutableDurableLeaseTransition::Unchanged {
                current: Some(registry),
            } if registry.len() == 1
        );
        release_guarded_aot_package_lease(&coordination, &mut lease, request)?;
        let duplicate_release =
            package_lease::release_file_aot_package_durable_lease(
                &coordination,
                &mut lease,
                request,
            )
            .map_err(|error| format!("duplicate guarded release: {error:?}"))?;
        let release_ok = matches!(
            &duplicate_release,
            NativeExecutableDurableLeaseTransition::Unchanged {
                current: Some(registry),
            } if registry.is_empty()
        );
        if duplicate_ok && release_ok {
            Ok(())
        } else {
            Err(String::from("guarded package lease idempotence drifted"))
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_package_lease_capacity_preserves_registry()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("aot_package_lease_capacity")?;
    let result = (|| -> HandoffResult<()> {
        let coordination = NativeContinuationFileCoordination::new(
            fixture.directory.join("package.lock"),
        );
        let mut lease = NativeContinuationFileBlobStore::with_coordination(
            fixture.directory.join("lease.bin"),
            coordination.clone(),
        );
        let first = aot_package_lease_transition_request_with_limit(1, 1)?;
        acquire_guarded_aot_package_lease(&coordination, &mut lease, first)?;
        let second = aot_package_lease_transition_request_with_limit(2, 1)?;
        let outcome = package_lease::acquire_file_aot_package_durable_lease(
            &coordination,
            &mut lease,
            second,
        );
        let capacity = matches!(
            outcome,
            Err(AotPackageLeaseTransitionError::Lease(
                LeaseTransitionError::Capacity(error),
            )) if error.observed_owners() == 2
        );
        let restored = executable_durable_lease_journal::
            restore_executable_durable_lease_journal(
                &mut lease,
                first.decode_limits(),
                first.maximum_bytes(),
            )
            .map_err(|error| format!("capacity restore: {error:?}"))?;
        let preserved = matches!(
            &restored,
            LeaseJournalLoad::Present { registry } if registry.len() == 1
        );
        if capacity && preserved {
            Ok(())
        } else {
            Err(String::from("lease capacity failure changed registry"))
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_package_lease_rejects_foreign_guard()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("aot_package_foreign_guard")?;
    let result = (|| -> HandoffResult<()> {
        let expected = NativeContinuationFileCoordination::new(
            fixture.directory.join("package.lock"),
        );
        let foreign = NativeContinuationFileCoordination::new(
            fixture.directory.join("foreign.lock"),
        );
        let lease_path = fixture.directory.join("lease.bin");
        let mut lease = NativeContinuationFileBlobStore::with_coordination(
            lease_path.clone(),
            foreign,
        );
        let outcome = package_lease::acquire_file_aot_package_durable_lease(
            &expected,
            &mut lease,
            aot_package_lease_transition_request(11)?,
        );
        let mismatch = matches!(
            outcome,
            Err(AotPackageLeaseTransitionError::Lease(
                LeaseTransitionError::Journal(LeaseJournalError::Blob(
                    BlobPersistenceError::Store(
                        FileBlobStoreError::CoordinationMismatch,
                    ),
                ),),
            )),
        );
        if mismatch && !lease_path.exists() {
            Ok(())
        } else {
            Err(String::from("foreign lease coordination mutated storage"))
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_package_reclaims_under_one_lease_guard()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("aot_package_guarded_lease")?;
    let result = (|| -> HandoffResult<()> {
        let (claim, _graph, programs, aot) = aot_package_material()?;
        let bounds = aot_package_bounds()?;
        let coordination = NativeContinuationFileCoordination::new(
            fixture.directory.join("aot-package.lock"),
        );
        let mut package =
            NativeContinuationFileBlobPairStore::with_coordination(
                fixture.directory.join("aot-package.manifest"),
                coordination.clone(),
            );
        let first = publish_aot_package_conditionally(
            &mut package,
            None,
            package_persist_request(&claim, &programs, &aot, bounds),
        )?;
        let second = publish_aot_package_conditionally(
            &mut package,
            Some(&first),
            package_persist_request(&claim, &programs, &aot, bounds),
        )?;
        let lease_request = aot_package_lease_transition_request(7)?;
        let mut lease = NativeContinuationFileBlobStore::with_coordination(
            fixture.directory.join("aot-package.first.lease"),
            coordination.clone(),
        );
        acquire_guarded_aot_package_lease(
            &coordination,
            &mut lease,
            lease_request,
        )?;
        let reclaim_context = GuardedAotPackageLeaseContext {
            bounds,
            coordination: &coordination,
            lease_request,
            programs: &programs,
            revision: first,
        };
        let preserved = reclaim_guarded_aot_package_from_lease(
            &mut package,
            &lease,
            reclaim_context,
        )?;
        require_aot_package_reclamation(preserved, second, 1, 0)?;
        release_guarded_aot_package_lease(
            &coordination,
            &mut lease,
            lease_request,
        )?;
        let reclaimed = reclaim_guarded_aot_package_from_lease(
            &mut package,
            &lease,
            reclaim_context,
        )?;
        require_aot_package_reclamation(reclaimed, second, 0, 2)
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_package_reclaims_from_durable_lease_snapshot()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("aot_package_durable_lease")?;
    let result = (|| -> HandoffResult<()> {
        let (claim, graph, programs, aot) = aot_package_material()?;
        let bounds = aot_package_bounds()?;
        let manifest = fixture.directory.join("aot-package.manifest");
        let mut package = NativeContinuationFileBlobPairStore::new(manifest);
        let first = publish_aot_package_conditionally(
            &mut package,
            None,
            package_persist_request(&claim, &programs, &aot, bounds),
        )?;
        let second = publish_aot_package_conditionally(
            &mut package,
            Some(&first),
            package_persist_request(&claim, &programs, &aot, bounds),
        )?;
        let leased = [
            RegisterMaskedAotPackageLeaseSnapshot::new(first, 0),
            RegisterMaskedAotPackageLeaseSnapshot::new(first, 2),
        ];
        let preserved =
            reclaim_register_masked_aot_package_generations_from_lease_snapshot(
                &mut package,
                package_restore_request(&programs, bounds),
                &leased,
            )
            .map_err(|error| format!("leased package reclaim: {error:?}"))?;
        require_aot_package_reclamation(preserved, second, 1, 0)?;
        let released = [RegisterMaskedAotPackageLeaseSnapshot::new(first, 0)];
        let reclaimed =
            reclaim_register_masked_aot_package_generations_from_lease_snapshot(
                &mut package,
                package_restore_request(&programs, bounds),
                &released,
            )
            .map_err(|error| format!("released package reclaim: {error:?}"))?;
        require_aot_package_reclamation(reclaimed, second, 0, 2)?;
        let current = restore_versioned_aot_package_revision(
            &mut package,
            &graph,
            &programs,
            bounds,
        )?;
        (current == second).then_some(()).ok_or_else(|| {
            String::from("lease-snapshot reclamation changed current package")
        })
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_package_retains_exact_revisions_before_reclaim()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("aot_package_retention_reclaim")?;
    let result = (|| -> HandoffResult<()> {
        let (claim, graph, programs, aot) = aot_package_material()?;
        let bounds = aot_package_bounds()?;
        let manifest = fixture.directory.join("aot-package.manifest");
        let mut store = NativeContinuationFileBlobPairStore::new(manifest);
        let first_revision = publish_aot_package_conditionally(
            &mut store,
            None,
            package_persist_request(&claim, &programs, &aot, bounds),
        )?;
        let mut retention = NativeContinuationBlobPairRetention::new();
        let _retained = retention.retain(first_revision);
        let second_revision = publish_aot_package_conditionally(
            &mut store,
            Some(&first_revision),
            package_persist_request(&claim, &programs, &aot, bounds),
        )?;
        if first_revision == second_revision {
            return Err(String::from("AOT package revision did not advance"));
        }
        require_stale_aot_package_conflict(
            &mut store,
            &first_revision,
            package_persist_request(&claim, &programs, &aot, bounds),
        )?;
        let preserved = reclaim_register_masked_aot_package_generations(
            &mut store,
            package_restore_request(&programs, bounds),
            &retention,
        )
        .map_err(|error| format!("preserved package reclaim: {error:?}"))?;
        require_aot_package_reclamation(preserved, second_revision, 1, 0)?;
        let _released = retention.release(&first_revision);
        let reclaimed = reclaim_register_masked_aot_package_generations(
            &mut store,
            package_restore_request(&programs, bounds),
            &retention,
        )
        .map_err(|error| format!("released package reclaim: {error:?}"))?;
        require_aot_package_reclamation(reclaimed, second_revision, 0, 2)?;
        let final_revision = restore_versioned_aot_package_revision(
            &mut store, &graph, &programs, bounds,
        )?;
        if final_revision == second_revision {
            Ok(())
        } else {
            Err(String::from(
                "current AOT package changed during reclamation",
            ))
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_package_rejects_partial_replacement()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("aot_package_atomic_reject")?;
    let result = (|| -> HandoffResult<()> {
        let (claim, _graph, programs, aot) = aot_package_material()?;
        let bounds = aot_package_bounds()?;
        let manifest = fixture.directory.join("aot-package.manifest");
        let mut store = NativeContinuationFileBlobPairStore::new(manifest);
        let _durable = persist_register_masked_aot_package_durably(
            &mut store,
            package_persist_request(&claim, &programs, &aot, bounds),
        )
        .map_err(|error| format!("initial AOT package persist: {error:?}"))?;
        let before = load_aot_package_pair(&mut store, bounds)?;
        let first = programs
            .first()
            .ok_or_else(|| String::from("AOT package graph was empty"))?;
        let incomplete =
            prepare_one(first).map_err(|error| error.to_string())?;
        let replacement = persist_register_masked_aot_package_durably(
            &mut store,
            package_persist_request(&claim, &programs, &incomplete, bounds),
        );
        let rejected = matches!(
            &replacement,
            Err(RegisterMaskedAotPackageStoreError::Preparation(error))
                if matches!(
                    error.as_ref(),
                    RegisterMaskedAotPackagePreparationError::Bundle(bundle)
                        if matches!(
                            bundle.as_ref(),
                            RegisterMaskedAotBundlePreparationError::Uncovered {
                                index: 1,
                            }
                        )
                )
        );
        if !rejected {
            return Err(format!(
                "incomplete package accepted: {replacement:?}"
            ));
        }
        let after = load_aot_package_pair(&mut store, bounds)?;
        if after != before {
            return Err(String::from(
                "rejected AOT package replacement changed committed pair",
            ));
        }
        Ok(())
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_bundle_rejects_untrusted_framing()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("bundle_framing")?;
    let result = (|| -> HandoffResult<()> {
        let (graph, _entry) = reduced_dispatch_fixture()?;
        let programs = reduced_dispatch_programs(&graph)?;
        let aot = prepare_reduced_dispatch_aot(&graph)?;
        let maximum_bytes = NonZeroUsize::new(65_536)
            .ok_or_else(|| String::from("AOT bundle bound became zero"))?;
        let mut store =
            NativeContinuationFileBlobStore::new(fixture.destination.clone());
        let _write = persist_register_masked_aot_bundle(
            &mut store,
            bundle_persist_request(&programs, &aot, maximum_bytes),
        )
        .map_err(|error| format!("AOT bundle persist: {error:?}"))?;
        let canonical = blob_store::NativeContinuationBlobStore::load(
            &mut store,
            maximum_bytes,
        )
        .map_err(|error| format!("cannot load canonical bundle: {error:?}"))?
        .ok_or_else(|| String::from("canonical AOT bundle disappeared"))?;
        expect_hostile_bundle_count_rejected(
            &mut store,
            &canonical,
            &programs,
            maximum_bytes,
        )?;
        expect_trailing_bundle_rejected(
            &mut store,
            &canonical,
            &programs,
            maximum_bytes,
        )
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_bundle_conditional_eviction_rejects_stale()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("bundle_conditional_evict")?;
    let result = (|| -> HandoffResult<()> {
        let (graph, _entry) = reduced_dispatch_fixture()?;
        let programs = reduced_dispatch_programs(&graph)?;
        let aot = prepare_reduced_dispatch_aot(&graph)?;
        let maximum_bytes = NonZeroUsize::new(65_536)
            .ok_or_else(|| String::from("AOT bundle bound became zero"))?;
        let mut store =
            NativeContinuationFileBlobStore::new(fixture.destination.clone());
        let request = bundle_persist_request(&programs, &aot, maximum_bytes);
        let _write = persist_register_masked_aot_bundle(&mut store, request)
            .map_err(|error| format!("AOT bundle persist: {error:?}"))?;
        let mut current = blob_store::NativeContinuationBlobStore::load(
            &mut store,
            maximum_bytes,
        )
        .map_err(|error| format!("load AOT bundle: {error:?}"))?
        .ok_or_else(|| String::from("AOT bundle disappeared"))?;
        let last = current
            .last_mut()
            .ok_or_else(|| String::from("AOT bundle unexpectedly empty"))?;
        *last ^= 1;
        blob_store::NativeContinuationBlobStore::replace(&mut store, &current)
            .map_err(|error| format!("replace AOT bundle: {error:?}"))?;
        let outcome = evict_register_masked_aot_bundle_if_current_durably(
            &mut store, request,
        )
        .map_err(|error| {
            format!("conditional AOT bundle eviction: {error:?}")
        })?;
        let retained = blob_store::NativeContinuationBlobStore::load(
            &mut store,
            maximum_bytes,
        )
        .map_err(|error| format!("reload AOT bundle: {error:?}"))?;
        if outcome.conflict() == Some(current.as_slice())
            && retained.as_deref() == Some(current.as_slice())
        {
            Ok(())
        } else {
            Err(String::from("stale bundle eviction changed publication"))
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_bundle_missing_is_explicit() -> HandoffResult<()>
{
    let fixture = reduced_graph_store_fixture("bundle_missing")?;
    let result = (|| -> HandoffResult<()> {
        let (graph, _entry) = reduced_dispatch_fixture()?;
        let programs = reduced_dispatch_programs(&graph)?;
        let maximum_bytes = NonZeroUsize::new(65_536)
            .ok_or_else(|| String::from("AOT bundle bound became zero"))?;
        let mut store =
            NativeContinuationFileBlobStore::new(fixture.destination.clone());
        let restored = restore_register_masked_aot_bundle(
            &mut store,
            bundle_restore_request(&programs, maximum_bytes),
        )
        .map_err(|error| format!("missing AOT bundle restore: {error:?}"))?;
        if restored == RegisterMaskedAotBundlePersistenceLoad::Missing {
            Ok(())
        } else {
            Err(String::from("missing AOT bundle invented authority"))
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_bundle_rejects_reorder() -> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("bundle_reordered")?;
    let result = (|| -> HandoffResult<()> {
        let (graph, _entry) = reduced_dispatch_fixture()?;
        let programs = reduced_dispatch_programs(&graph)?;
        let aot = prepare_reduced_dispatch_aot(&graph)?;
        let maximum_bytes = NonZeroUsize::new(65_536)
            .ok_or_else(|| String::from("AOT bundle bound became zero"))?;
        let mut store =
            NativeContinuationFileBlobStore::new(fixture.destination.clone());
        let _write = persist_register_masked_aot_bundle(
            &mut store,
            bundle_persist_request(&programs, &aot, maximum_bytes),
        )
        .map_err(|error| format!("AOT bundle persist: {error:?}"))?;
        let mut reordered = programs.clone();
        reordered.reverse();
        match restore_register_masked_aot_bundle(
            &mut store,
            bundle_restore_request(&reordered, maximum_bytes),
        ) {
            Err(RegisterMaskedAotBundleRestorePersistenceError::Native {
                index: 0,
                ..
            }) => Ok(()),
            other => {
                Err(format!("reordered AOT bundle was accepted: {other:?}"))
            },
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_bundle_requires_complete_set_before_publish()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("bundle_incomplete")?;
    let result = (|| -> HandoffResult<()> {
        let (graph, _entry) = reduced_dispatch_fixture()?;
        let programs = reduced_dispatch_programs(&graph)?;
        let first = programs
            .first()
            .ok_or_else(|| String::from("AOT bundle graph was empty"))?;
        let incomplete =
            prepare_one(first).map_err(|error| error.to_string())?;
        let maximum_bytes = NonZeroUsize::new(65_536)
            .ok_or_else(|| String::from("AOT bundle bound became zero"))?;
        let mut store =
            NativeContinuationFileBlobStore::new(fixture.destination.clone());
        blob_store::NativeContinuationBlobStore::replace(&mut store, b"before")
            .map_err(|error| format!("cannot seed prior bundle: {error:?}"))?;
        let result = persist_register_masked_aot_bundle(
            &mut store,
            bundle_persist_request(&programs, &incomplete, maximum_bytes),
        );
        if !matches!(
            &result,
            Err(RegisterMaskedAotBundleStoreError::Preparation(error))
                if **error
                    == RegisterMaskedAotBundlePreparationError::Uncovered {
                        index: 1,
                    }
        ) {
            return Err(format!(
                "incomplete AOT bundle was published: {result:?}"
            ));
        }
        let retained = blob_store::NativeContinuationBlobStore::load(
            &mut store,
            maximum_bytes,
        )
        .map_err(|error| format!("cannot reload prior bundle: {error:?}"))?;
        if retained.as_deref() == Some(b"before") {
            Ok(())
        } else {
            Err(String::from("failed bundle replaced prior atomic blob"))
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_bundle_round_trips_reduced_graph()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("bundle_round_trip")?;
    let result = (|| -> HandoffResult<()> {
        let (graph, _entry) = reduced_dispatch_fixture()?;
        let programs = reduced_dispatch_programs(&graph)?;
        let aot = prepare_reduced_dispatch_aot(&graph)?;
        let maximum_bytes = NonZeroUsize::new(65_536)
            .ok_or_else(|| String::from("AOT bundle bound became zero"))?;
        let mut store =
            NativeContinuationFileBlobStore::new(fixture.destination.clone());
        let durable = persist_register_masked_aot_bundle_durably(
            &mut store,
            bundle_persist_request(&programs, &aot, maximum_bytes),
        )
        .map_err(|error| format!("durable AOT bundle persist: {error:?}"))?;
        if !durable.is_durable() || durable.bytes() == 0 {
            return Err(String::from(
                "AOT bundle durability was not confirmed",
            ));
        }
        let restored = restore_register_masked_aot_bundle(
            &mut store,
            bundle_restore_request(&programs, maximum_bytes),
        )
        .map_err(|error| format!("durable AOT bundle restore: {error:?}"))?;
        let RegisterMaskedAotBundlePersistenceLoad::Restored {
            bytes,
            objects,
            set,
        } = restored
        else {
            return Err(String::from("durable AOT bundle disappeared"));
        };
        if bytes != durable.bytes() || objects != programs.len() {
            return Err(String::from(
                "AOT bundle publication evidence drifted",
            ));
        }
        for program in &programs {
            let selected = select_ahead_of_execution_register_masked_tier(
                program,
                safe_rust_profiled_capability(),
                windows_x86_64(),
                &set,
            )
            .map_err(|error| error.to_string())?;
            if !matches!(
                selected,
                AheadOfExecutionRegisterMaskedTier::Direct(_)
            ) {
                return Err(String::from(
                    "restored bundle lost exact coverage",
                ));
            }
        }
        evict_bundle_and_require_missing(&mut store, &programs, maximum_bytes)
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_object_conditional_eviction_matches_current()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("object_conditional_evict")?;
    let result = (|| -> HandoffResult<()> {
        let program = first_reduced_aot_program()?;
        let source = select_prepared_reduced_artifact(&program)?;
        let maximum_bytes = NonZeroUsize::new(4096)
            .ok_or_else(|| String::from("AOT object bound became zero"))?;
        let mut store =
            NativeContinuationFileBlobStore::new(fixture.destination.clone());
        let _durable = persist_register_masked_aot_object_durably(
            &mut store,
            &source,
            maximum_bytes,
        )
        .map_err(|error| format!("durable AOT object persist: {error:?}"))?;
        let outcome = evict_register_masked_aot_object_if_current_durably(
            &mut store,
            &source,
            maximum_bytes,
        )
        .map_err(|error| {
            format!("conditional AOT object eviction: {error:?}")
        })?;
        let load = restore_register_masked_aot_object(
            &mut store,
            object_restore_request(&program, maximum_bytes),
        )
        .map_err(|error| {
            format!("post-eviction AOT object restore: {error:?}")
        })?;
        if outcome.is_removed()
            && load == RegisterMaskedAotObjectPersistenceLoad::Missing
        {
            Ok(())
        } else {
            Err(String::from("current object eviction did not commit"))
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_object_store_rejects_wrong_ir()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("object_wrong_ir")?;
    let result = (|| -> HandoffResult<()> {
        let (graph, _entry) = reduced_dispatch_fixture()?;
        let source_program =
            graph
                .node(0)
                .map(|node| node.program().clone())
                .ok_or_else(|| String::from("object source program missing"))?;
        let expected_program = graph
            .node(1)
            .map(|node| node.program().clone())
            .ok_or_else(|| String::from("object expected program missing"))?;
        let artifact = select_prepared_reduced_artifact(&source_program)?;
        let maximum_bytes = NonZeroUsize::new(4096)
            .ok_or_else(|| String::from("AOT object bound became zero"))?;
        let mut store =
            NativeContinuationFileBlobStore::new(fixture.destination.clone());
        blob_store::NativeContinuationBlobStore::replace(
            &mut store,
            artifact.object(),
        )
        .map_err(|error| {
            format!("cannot seed mismatched AOT object: {error:?}")
        })?;
        match restore_register_masked_aot_object(
            &mut store,
            object_restore_request(&expected_program, maximum_bytes),
        ) {
            Err(RegisterMaskedAotObjectRestorePersistenceError::Native(_)) => {
                Ok(())
            },
            other => {
                Err(format!("wrong-IR AOT object was accepted: {other:?}"))
            },
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_object_store_rejects_wrong_bytes()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("object_wrong_bytes")?;
    let result = (|| -> HandoffResult<()> {
        let program = first_reduced_aot_program()?;
        let artifact = select_prepared_reduced_artifact(&program)?;
        let mut corrupt = artifact.object().to_vec();
        let last = corrupt
            .last_mut()
            .ok_or_else(|| String::from("verified AOT object was empty"))?;
        *last ^= 1;
        let mut store =
            NativeContinuationFileBlobStore::new(fixture.destination.clone());
        blob_store::NativeContinuationBlobStore::replace(&mut store, &corrupt)
            .map_err(|error| {
                format!("cannot seed corrupt AOT object: {error:?}")
            })?;
        let maximum_bytes = NonZeroUsize::new(4096)
            .ok_or_else(|| String::from("AOT object bound became zero"))?;
        match restore_register_masked_aot_object(
            &mut store,
            object_restore_request(&program, maximum_bytes),
        ) {
            Err(RegisterMaskedAotObjectRestorePersistenceError::Native(_)) => {
                Ok(())
            },
            other => Err(format!("corrupt AOT object was accepted: {other:?}")),
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_register_masked_aot_object_store_round_trips_file_blob()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("object_round_trip")?;
    let result = (|| -> HandoffResult<()> {
        let program = first_reduced_aot_program()?;
        let source = select_prepared_reduced_artifact(&program)?;
        let maximum_bytes = NonZeroUsize::new(4096)
            .ok_or_else(|| String::from("AOT object bound became zero"))?;
        let mut store =
            NativeContinuationFileBlobStore::new(fixture.destination.clone());
        let missing = restore_register_masked_aot_object(
            &mut store,
            object_restore_request(&program, maximum_bytes),
        )
        .map_err(|error| format!("missing AOT object restore: {error:?}"))?;
        if missing != RegisterMaskedAotObjectPersistenceLoad::Missing {
            return Err(String::from("missing AOT object invented authority"));
        }
        let durable = persist_register_masked_aot_object_durably(
            &mut store,
            &source,
            maximum_bytes,
        )
        .map_err(|error| format!("durable AOT object persist: {error:?}"))?;
        if !durable.is_durable() || durable.bytes() != source.object().len() {
            return Err(String::from("AOT object durability evidence drifted"));
        }
        let restored = restore_register_masked_aot_object(
            &mut store,
            object_restore_request(&program, maximum_bytes),
        )
        .map_err(|error| format!("durable AOT object restore: {error:?}"))?;
        let RegisterMaskedAotObjectPersistenceLoad::Restored {
            bytes,
            artifact,
        } = restored
        else {
            return Err(String::from("durable AOT object disappeared"));
        };
        if bytes != durable.bytes() || artifact.as_ref() != source.as_ref() {
            return Err(String::from("durable AOT object round-trip drifted"));
        }
        let restored_set =
            VerifiedAheadOfExecutionRegisterMaskedSet::from_verified_artifacts(
                vec![*artifact],
            );
        let selected = select_ahead_of_execution_register_masked_tier(
            &program,
            safe_rust_profiled_capability(),
            windows_x86_64(),
            &restored_set,
        )
        .map_err(|error| error.to_string())?;
        if !matches!(selected, AheadOfExecutionRegisterMaskedTier::Direct(_)) {
            return Err(String::from("restored AOT object was not selectable"));
        }
        evict_object_and_require_missing(&mut store, &program, maximum_bytes)
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_reduced_graph_store_rejects_corrupt_file_blob() -> HandoffResult<()>
{
    let fixture = reduced_graph_store_fixture("corrupt")?;
    let result = (|| -> HandoffResult<()> {
        let mut store =
            NativeContinuationFileBlobStore::new(fixture.destination.clone());
        blob_store::NativeContinuationBlobStore::replace(&mut store, b"BAD!")
            .map_err(|error| format!("cannot seed corrupt graph: {error:?}"))?;
        let maximum_bytes = NonZeroUsize::new(64)
            .ok_or_else(|| String::from("corrupt graph bound became zero"))?;
        match restore_register_masked_reduced_graph(
            &mut store,
            maximum_bytes,
            reduced_codec_limits(),
        ) {
            Err(RegisterMaskedReducedGraphPersistenceError::Codec(
                ReducedCodecError::Magic,
            )) => Ok(()),
            other => Err(format!("corrupt graph blob was accepted: {other:?}")),
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_reduced_graph_conditional_eviction_rejects_stale()
-> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("conditional_evict_stale")?;
    let result = (|| -> HandoffResult<()> {
        let (claim, _entry) = reduced_dispatch_claim()?;
        let maximum_bytes = NonZeroUsize::new(134_217_728)
            .ok_or_else(|| String::from("graph blob bound became zero"))?;
        let mut store =
            NativeContinuationFileBlobStore::new(fixture.destination.clone());
        let durable = persist_register_masked_reduced_graph_durably(
            &mut store,
            &claim,
            maximum_bytes,
        )
        .map_err(|error| format!("durable graph persist: {error:?}"))?;
        if !durable.is_durable() {
            return Err(String::from("graph durability not confirmed"));
        }
        let mut current = blob_store::NativeContinuationBlobStore::load(
            &mut store,
            maximum_bytes,
        )
        .map_err(|error| format!("load graph blob: {error:?}"))?
        .ok_or_else(|| String::from("graph blob disappeared"))?;
        let last = current
            .last_mut()
            .ok_or_else(|| String::from("graph blob unexpectedly empty"))?;
        *last ^= 1;
        blob_store::NativeContinuationBlobStore::replace(&mut store, &current)
            .map_err(|error| format!("replace graph blob: {error:?}"))?;
        let outcome = evict_register_masked_reduced_graph_if_current_durably(
            &mut store,
            &claim,
            maximum_bytes,
        )
        .map_err(|error| format!("conditional graph eviction: {error:?}"))?;
        let retained = blob_store::NativeContinuationBlobStore::load(
            &mut store,
            maximum_bytes,
        )
        .map_err(|error| format!("reload graph blob: {error:?}"))?;
        if outcome.conflict() == Some(current.as_slice())
            && retained.as_deref() == Some(current.as_slice())
        {
            Ok(())
        } else {
            Err(String::from("stale graph eviction changed publication"))
        }
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_reduced_graph_store_round_trips_file_blob() -> HandoffResult<()> {
    let fixture = reduced_graph_store_fixture("round_trip")?;
    let result = (|| -> HandoffResult<()> {
        let (claim, _entry) = reduced_dispatch_claim()?;
        let expected = claim.verify().map_err(|error| error.to_string())?;
        let maximum_bytes = NonZeroUsize::new(134_217_728)
            .ok_or_else(|| String::from("graph blob bound became zero"))?;
        let mut store =
            NativeContinuationFileBlobStore::new(fixture.destination.clone());
        expect_reduced_graph_blob_missing(&mut store, maximum_bytes)?;
        persist_and_restore_register_masked_reduced_graph(
            &mut store,
            &claim,
            &expected,
            maximum_bytes,
        )?;
        let outcome = evict_register_masked_reduced_graph_if_current_durably(
            &mut store,
            &claim,
            maximum_bytes,
        )
        .map_err(|error| format!("conditional graph eviction: {error:?}"))?;
        if !outcome.is_removed() {
            return Err(String::from("current graph eviction did not commit"));
        }
        expect_reduced_graph_blob_missing(&mut store, maximum_bytes)
    })();
    let cleanup = remove_reduced_graph_store_fixture(&fixture.directory);
    result?;
    cleanup
}

#[test]
fn product_reduced_graph_dispatch_rechecks_actual_successor_state()
-> HandoffResult<()> {
    let (graph, entry) = reduced_dispatch_fixture()?;
    let aot = prepare_reduced_dispatch_aot(&graph)?;
    let mut executor =
        NormativeReducedGraphExecutor::new(ReducedExecutorMode::Apply);
    let outcome =
        dispatch_ahead_of_execution_register_masked_reduced_state_graph(
            reduced_dispatch_request(&graph, &aot, entry, 2),
            &mut executor,
        )
        .map_err(|error| error.to_string())?;
    let ReducedDispatchOutcome::Completed { state, transitions } = outcome
    else {
        return Err(format!("reduced dispatch did not complete: {outcome:?}"));
    };
    if transitions == 2
        && state.io().termination() == Some(Termination::HaltInstruction)
        && executor.calls == 2
        && executor.kinds
            == vec![DirectNativeKind::NoOperation, DirectNativeKind::HaltFetch]
    {
        Ok(())
    } else {
        Err(String::from("reduced dispatch changed exact AOT route"))
    }
}

#[test]
fn product_reduced_graph_dispatch_fails_closed_without_guessing()
-> HandoffResult<()> {
    let (graph, entry) = reduced_dispatch_fixture()?;
    let aot = prepare_reduced_dispatch_aot(&graph)?;

    let mut tampered = NormativeReducedGraphExecutor::new(
        ReducedExecutorMode::TamperSuccessor,
    );
    let tampered_outcome =
        dispatch_ahead_of_execution_register_masked_reduced_state_graph(
            reduced_dispatch_request(&graph, &aot, entry.clone(), 2),
            &mut tampered,
        )
        .map_err(|error| error.to_string())?;
    if !matches!(tampered_outcome, ReducedDispatchOutcome::Fallback {
        reason: ReducedDispatchFallback::SuccessorGuardMiss {
            index: 0,
            successor: 1,
        },
        transitions: 1,
        ..
    }) || tampered.calls != 1
    {
        return Err(String::from(
            "reduced dispatch guessed after successor miss",
        ));
    }

    let mut budgeted =
        NormativeReducedGraphExecutor::new(ReducedExecutorMode::Apply);
    let budget_outcome =
        dispatch_ahead_of_execution_register_masked_reduced_state_graph(
            reduced_dispatch_request(&graph, &aot, entry, 1),
            &mut budgeted,
        )
        .map_err(|error| error.to_string())?;
    if !matches!(budget_outcome, ReducedDispatchOutcome::Fallback {
        reason: ReducedDispatchFallback::TransitionBudgetExhausted { index: 1 },
        transitions: 1,
        ..
    }) || budgeted.calls != 1
    {
        return Err(String::from("reduced dispatch ignored transition budget"));
    }

    Ok(())
}

#[test]
fn product_reduced_dispatch_rejects_entry_guard_miss() -> HandoffResult<()> {
    let (graph, entry) = reduced_dispatch_fixture()?;
    let aot = prepare_reduced_dispatch_aot(&graph)?;
    let bad_entry = checkpoint_with_registers(&entry, ProfileRegisters {
        code_pointer: entry.registers().code_pointer.saturating_add(1),
        ..entry.registers()
    })
    .map_err(|error| format!("dispatch bad entry failed: {error}"))?;
    let mut executor =
        NormativeReducedGraphExecutor::new(ReducedExecutorMode::Apply);
    let outcome =
        dispatch_ahead_of_execution_register_masked_reduced_state_graph(
            reduced_dispatch_request(&graph, &aot, bad_entry, 2),
            &mut executor,
        )
        .map_err(|error| error.to_string())?;
    if matches!(outcome, ReducedDispatchOutcome::Fallback {
        reason: ReducedDispatchFallback::NodeGuardMiss { index: 0 },
        transitions: 0,
        ..
    }) && executor.calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "reduced dispatch executed outside entry guard",
        ))
    }
}

#[test]
fn product_reduced_graph_dispatch_preserves_guard_miss_atomicity()
-> HandoffResult<()> {
    let (graph, entry) = reduced_dispatch_fixture()?;
    let aot = prepare_reduced_dispatch_aot(&graph)?;

    let mut guard_miss =
        NormativeReducedGraphExecutor::new(ReducedExecutorMode::GuardMiss);
    let outcome =
        dispatch_ahead_of_execution_register_masked_reduced_state_graph(
            reduced_dispatch_request(&graph, &aot, entry.clone(), 2),
            &mut guard_miss,
        )
        .map_err(|error| error.to_string())?;
    if !matches!(outcome, ReducedDispatchOutcome::Fallback {
        reason: ReducedDispatchFallback::NativeGuardMiss { index: 0 },
        transitions: 0,
        ..
    }) {
        return Err(String::from("native guard miss did not fall back"));
    }

    let mut mutated = NormativeReducedGraphExecutor::new(
        ReducedExecutorMode::MutatedGuardMiss,
    );
    match dispatch_ahead_of_execution_register_masked_reduced_state_graph(
        reduced_dispatch_request(&graph, &aot, entry, 2),
        &mut mutated,
    ) {
        Err(ReducedDispatchFailure::GuardMissMutation { index: 0 }) => Ok(()),
        result => {
            Err(format!("unexpected mutated guard-miss result: {result:?}"))
        },
    }
}

#[test]
fn product_reduced_dispatch_rejects_terminal_state_mismatch()
-> HandoffResult<()> {
    let (graph, entry) = reduced_dispatch_fixture()?;
    let aot = prepare_reduced_dispatch_aot(&graph)?;
    let mut executor =
        NormativeReducedGraphExecutor::new(ReducedExecutorMode::TamperTerminal);
    let result =
        dispatch_ahead_of_execution_register_masked_reduced_state_graph(
            reduced_dispatch_request(&graph, &aot, entry, 2),
            &mut executor,
        );
    if matches!(
        result,
        Err(ReducedDispatchFailure::TerminalStateMismatch { index: 1 })
    ) && executor.calls == 2
    {
        Ok(())
    } else {
        Err(format!("unexpected terminal mismatch result: {result:?}"))
    }
}

#[test]
fn product_reduced_graph_dispatch_exposes_lower_tier_boundaries()
-> HandoffResult<()> {
    let (graph, entry) = reduced_dispatch_fixture()?;
    let empty = VerifiedAheadOfExecutionRegisterMaskedSet::default();
    let mut uncovered =
        NormativeReducedGraphExecutor::new(ReducedExecutorMode::Apply);
    let uncovered_outcome =
        dispatch_ahead_of_execution_register_masked_reduced_state_graph(
            reduced_dispatch_request(&graph, &empty, entry.clone(), 2),
            &mut uncovered,
        )
        .map_err(|error| error.to_string())?;
    if !matches!(uncovered_outcome, ReducedDispatchOutcome::Fallback {
        reason: ReducedDispatchFallback::Uncovered { index: 0 },
        transitions: 0,
        ..
    }) || uncovered.calls != 0
    {
        return Err(String::from("uncovered reduced node attempted execution"));
    }

    let aot = prepare_reduced_dispatch_aot(&graph)?;
    let mut host_fallback =
        NormativeReducedGraphExecutor::new(ReducedExecutorMode::Apply);
    let linux = DirectHost::new(HostOperatingSystem::Linux, HostIsa::X86_64);
    let host_outcome =
        dispatch_ahead_of_execution_register_masked_reduced_state_graph(
            AheadOfExecutionRegisterMaskedReducedStateGraphDispatchRequest::new(
                &graph,
                ReducedDispatchEnvironment::new(
                    &aot,
                    safe_rust_profiled_capability(),
                    linux,
                ),
                entry,
                2,
            ),
            &mut host_fallback,
        )
        .map_err(|error| error.to_string())?;
    if matches!(host_outcome, ReducedDispatchOutcome::Fallback {
        reason: ReducedDispatchFallback::TargetInterpreter { index: 0 },
        transitions: 0,
        ..
    }) && host_fallback.calls == 0
    {
        Ok(())
    } else {
        Err(String::from(
            "host fallback attempted reduced native execution",
        ))
    }
}
