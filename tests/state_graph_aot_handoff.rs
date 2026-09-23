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
    AheadOfExecutionRegisterMaskedTier, DirectHost, DirectNativeKind,
    RegisterMaskedDirectAdmissionErrorKind,
    prepare_ahead_of_execution_register_masked_set,
    select_ahead_of_execution_register_masked_tier,
};
use indexed_state::IndexedMachineState;
use malbolge::{
    ProfileMachine, ProfileStepTrace, RegisterMaskedRegionEffectProgram,
    RegisterMaskedRegionProjectionError, RunOutcome,
    StepProgramProjectionError, current_profile, safe_rust_profiled_capability,
    verify_minimum_initial_halt_profile_width,
};
use region_artifact::{UntrustedRegionArtifact, VerifiedRegionArtifact};
use region_certificate::{ExactRegionCertificate, VerifiedExactRegion};

const MULTI_STEP_SOURCE: &[u8] = b"(=%`qL";

type HandoffResult<T> = Result<T, String>;

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
