// File:
//   - r.rs
// Path:
//   - algorithms/self-modification-state-graph-optimizer/tests/r.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Exact-region verifier, guard invalidation, and rejection fixtures.
// - Must-Not:
//   - Trust recorded certificates without re-execution or use digest-only
//     guards.
// - Allows:
//   - Inputs: current-profile exact states and bounded normative execution.
//   - Outputs: verifier acceptance/rejection evidence for future native
//     shortcuts.
//   - Side effects: test-process allocation and normative VM execution only.
// - Split-When:
//   - Split when broader dependency guards gain separate certification
//     evidence.
// - Merge-When:
//   - Merge when a tiered native engine owns equivalent verifier fixtures.
// - Summary:
//   - Proves exact-state region certificates fail closed around
//     mutations/errors.
// - Description:
//   - Verifies current execution, tamper detection, guard invalidation,
//     rejection.
// - Usage:
//   - Composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Only verifier-produced `VerifiedExactRegion` is admitted as trusted.
//
// Related documents:
// - algorithms/self-modification-state-graph-optimizer/region.rs
//
// Large file:
//   - false

//! Verification evidence for exact-state guarded future native regions.

use malbolge::{
    ProfileMachine, ProfileMachineError, RunOutcome, current_profile,
};

use crate::indexed_state::IndexedMachineState;
use crate::region_certificate::{
    ExactRegionCertificate, ExactRegionError, UntrustedExactRegionClaim,
};

const CURRENT_SOURCE: &[u8] = b"(=%`qL";
const REGION_BUDGET: usize = 8;
const REJECTING_SOURCE: &[u8] = b"b'";

#[test]
fn current_region_reexecutes_to_exact_verified_exit() -> Result<(), String> {
    let mut direct =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("region direct load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&direct.snapshot_state())
        .map_err(|error| format!("region entry failed: {error:?}"))?;
    let certificate = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .map_err(|error| format!("region record failed: {error:?}"))?;
    let verified = certificate
        .verify()
        .map_err(|error| format!("region verify failed: {error:?}"))?;
    let direct_outcome = direct
        .run(REGION_BUDGET)
        .map_err(|error| format!("region direct run failed: {error}"))?;
    if verified.outcome() != direct_outcome {
        return Err(String::from(
            "verified region outcome differs from direct VM",
        ));
    }
    let exit = verified.exit().materialize_checkpoint().map_err(|error| {
        format!("region exit materialize failed: {error:?}")
    })?;
    if exit != direct.snapshot_state() {
        return Err(String::from(
            "verified region exit differs from direct VM",
        ));
    }
    if !verified.accepts_entry(&entry) {
        return Err(String::from("verified region rejected its exact entry"));
    }
    Ok(())
}

#[test]
fn exact_guard_rejects_mutated_entry_state() -> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("region guard load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("region guard entry failed: {error:?}"))?;
    let certificate = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .map_err(|error| format!("region guard record failed: {error:?}"))?;
    let verified = certificate
        .verify()
        .map_err(|error| format!("region guard verify failed: {error:?}"))?;
    let first_trace =
        verified.traces().first().copied().ok_or_else(|| {
            String::from("verified region has no first trace")
        })?;
    let mutated = entry
        .apply_trace(&first_trace)
        .map_err(|error| format!("region guard mutation failed: {error:?}"))?;
    if verified.accepts_entry(&mutated) {
        Err(String::from("exact region guard accepted a mutated entry"))
    } else {
        Ok(())
    }
}

#[test]
fn tampered_certificate_fails_normative_reverification() -> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("region tamper load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("region tamper entry failed: {error:?}"))?;
    let certificate = ExactRegionCertificate::record(&entry, REGION_BUDGET)
        .map_err(|error| format!("region tamper record failed: {error:?}"))?;
    let tampered = ExactRegionCertificate::from_untrusted_parts(
        UntrustedExactRegionClaim {
            entry: certificate.entry().clone(),
            exit: certificate.exit().clone(),
            outcome: RunOutcome::BudgetExhausted { steps: 0 },
            step_budget: certificate.step_budget(),
            traces: certificate.traces().to_vec(),
        },
    );
    match tampered.verify() {
        Err(ExactRegionError::VerificationMismatch) => Ok(()),
        other => Err(format!("tampered region certificate result: {other:?}")),
    }
}

#[test]
fn rejected_transition_never_records_verified_region() -> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), REJECTING_SOURCE, vec![
            0x44,
        ])
        .map_err(|error| format!("region reject load failed: {error}"))?;
    let entry = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("region reject entry failed: {error:?}"))?;
    let result = ExactRegionCertificate::record(&entry, 1);
    match result {
        Err(ExactRegionError::Machine(
            ProfileMachineError::InvalidEncryptionTarget { .. },
        )) => Ok(()),
        other => {
            Err(format!("rejected transition certificate result: {other:?}"))
        },
    }
}
