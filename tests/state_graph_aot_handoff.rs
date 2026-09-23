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
    ProfileMachine, RegisterMaskedRegionEffectProgram, current_profile,
    safe_rust_profiled_capability,
};
use region_artifact::{UntrustedRegionArtifact, VerifiedRegionArtifact};
use region_certificate::ExactRegionCertificate;

const MULTI_STEP_SOURCE: &[u8] = b"(=%`qL";

type HandoffResult<T> = Result<T, String>;

fn verified_artifact(
    source: &[u8],
    step_budget: usize,
) -> HandoffResult<VerifiedRegionArtifact> {
    let machine =
        ProfileMachine::from_source(current_profile(), source, vec![0x41])
            .map_err(|error| format!("handoff source load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("handoff entry indexing failed: {error:?}"))?;
    let region = ExactRegionCertificate::record(&entry, step_budget)
        .and_then(|certificate| certificate.verify())
        .map_err(|error| {
            format!("handoff region verification failed: {error:?}")
        })?;
    UntrustedRegionArtifact::from_verified_region(&region)
        .verify_against(&region)
        .map_err(|error| {
            format!("handoff artifact verification failed: {error:?}")
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
