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
//   - Integration evidence from verified research region artifacts to product
//     register-masked AOT admission.
// - Must-Not:
//   - Make production runtime depend on research modules or grant invocation
//     authority from research verification alone.
// - Allows:
//   - Inputs: verifier-admitted research artifacts and product-owned v6 IR.
//   - Outputs: AOT object-admission handoff assertions and fail-closed
//     evidence.
//   - Side effects: test-process allocation and canonical object emission only.
// - Split-When:
//   - Reduced graph import gains a product-owned serialization boundary.
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

#[path = "../src/runtime/tiered-execution/adapter-outbound/cache/main.rs"]
pub mod execution_cache;
#[path = "../src/runtime/tiered-execution/adapter-outbound/native/main.rs"]
pub mod execution_native;
#[path = "../src/research/algorithms/composition/state-graph/index.rs"]
pub mod indexed;
#[path = "../src/research/algorithms/composition/state-graph/state.rs"]
pub mod indexed_state;
#[path = "../src/research/algorithms/composition/state-graph/output.rs"]
pub mod persistent_output;
#[path = "../src/research/algorithms/composition/state-graph/artifact.rs"]
pub mod region_artifact;
#[path = "../src/research/algorithms/composition/state-graph/region.rs"]
pub mod region_certificate;

use std::slice::from_ref;

use execution_cache::{HostIsa, HostOperatingSystem};
use execution_native::{
    AheadOfExecutionRegisterMaskedPreparationError,
    AheadOfExecutionRegisterMaskedReducedStateGraphError,
    AheadOfExecutionRegisterMaskedReducedStateGraphNodeClaim,
    AheadOfExecutionRegisterMaskedTier, DirectHost, DirectNativeKind,
    RegisterMaskedDependencyIdentityClaim,
    RegisterMaskedDirectAdmissionErrorKind,
    UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
    prepare_ahead_of_execution_register_masked_set,
    select_ahead_of_execution_register_masked_tier,
};
use indexed_state::IndexedMachineState;
use malbolge::{
    ProfileMachine, ProfileMachineIoState, ProfileMachineState,
    ProfileRegisters, ProfileStepTrace, RegisterMaskedRegionEffectProgram,
    RegisterMaskedRegionProjectionError, RunOutcome,
    StepProgramProjectionError, current_profile, decode_profile_instruction,
    safe_rust_profiled_capability, verify_minimum_initial_halt_profile_width,
};
use region_artifact::{UntrustedRegionArtifact, VerifiedRegionArtifact};
use region_certificate::{ExactRegionCertificate, VerifiedExactRegion};

const MULTI_STEP_SOURCE: &[u8] = b"(=%`qL";

type HandoffResult<T> = Result<T, String>;
type ReducedGraphError = AheadOfExecutionRegisterMaskedReducedStateGraphError;

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

const fn windows_x86_64() -> DirectHost {
    DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64)
}

fn prepare_one(
    program: &RegisterMaskedRegionEffectProgram,
) -> Result<
    execution_native::VerifiedAheadOfExecutionRegisterMaskedSet,
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
