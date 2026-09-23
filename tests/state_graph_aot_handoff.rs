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
//   - Native object-bundle persistence or executable residency gains
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

#[path = "../src/runtime/tiered-execution/application/blob_persistence.rs"]
pub mod blob_persistence;
#[path = "../src/runtime/tiered-execution/port-outbound/blob_store.rs"]
pub mod blob_store;
#[path = "../src/runtime/tiered-execution/adapter-outbound/cache/main.rs"]
pub mod execution_cache;
#[path = "../src/runtime/tiered-execution/adapter-outbound/native/main.rs"]
pub mod execution_native;
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

use std::fs;
use std::io::ErrorKind;
use std::num::NonZeroUsize;
use std::path::{Path, PathBuf};
use std::process::id as process_id;
use std::slice::from_ref;

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
use file_blob_store::NativeContinuationFileBlobStore;
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
    persist_register_masked_reduced_graph_durably,
    restore_register_masked_reduced_graph,
};
use region_artifact::{UntrustedRegionArtifact, VerifiedRegionArtifact};
use region_certificate::{ExactRegionCertificate, VerifiedExactRegion};

const MULTI_STEP_SOURCE: &[u8] = b"(=%`qL";

type HandoffResult<T> = Result<T, String>;
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

fn prepare_reduced_dispatch_aot(
    graph: &VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
) -> HandoffResult<VerifiedAheadOfExecutionRegisterMaskedSet> {
    let programs = (0..graph.len())
        .map(|index| {
            graph
                .node(index)
                .map(|node| node.program().clone())
                .ok_or_else(|| format!("dispatch graph lost node {index}"))
        })
        .collect::<HandoffResult<Vec<_>>>()?;
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
        )
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
