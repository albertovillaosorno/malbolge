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
//   - Exact current-profile checkpoint replay and collision fixtures.
// - Must-Not:
//   - Claim scalable memory reduction or benchmark checkpoint storage cost.
// - Allows:
//   - Inputs: public `ProfileMachine` checkpoint API and current profile.
//   - Outputs: exact dedup/collision correctness evidence.
//   - Side effects: test-process allocation of current-profile memory images.
// - Split-When:
//   - Split when a scalable reduced-state key gains independent evidence.
// - Merge-When:
//   - Merge when exact classic/profile identity shares one generic owner.
// - Summary:
//   - Proves current checkpoints use exact collision-safe graph identity.
// - Description:
//   - Exercises 14,348,907-word checkpoints without weakening equality.
// - Usage:
//   - Composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Full checkpoints are correctness evidence, not a performance design.
//

//! Exact current-profile checkpoint graph fixtures.

use malbolge::{
    ProfileMachine, ProfileMachineIoState, ProfileMachineState,
    ProfileRegisters, StepOutcome, Termination, current_profile,
    verify_minimum_initial_halt_profile_width,
};

use crate::profile_graph::{
    ProfileStateGraph, ProfileStateGraphError, ProfileTerminalFutureSnapshot,
    constant_profile_collision_digest, profile_terminal_future_snapshot,
};

const CURRENT_SOURCE: &[u8] = b"(=%`qL";

fn current_checkpoint(input: u8) -> Result<ProfileMachineState, String> {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            input,
        ])
        .map_err(|error| {
            format!("current graph fixture load failed: {error}")
        })?;
    Ok(machine.snapshot_state())
}

#[test]
fn current_checkpoint_replay_deduplicates_exactly() -> Result<(), String> {
    let checkpoint = current_checkpoint(0x41)?;
    let mut graph = ProfileStateGraph::new();
    let first = graph.observe(checkpoint.clone()).map_err(|error| {
        format!("first current observation failed: {error:?}")
    })?;
    let second = graph
        .observe(checkpoint)
        .map_err(|error| format!("current replay failed: {error:?}"))?;
    if first != second || graph.node_count() != 1 {
        return Err(String::from(
            "exact current checkpoint did not deduplicate",
        ));
    }
    if graph.deduplicated_observations() != 1 || graph.observations() != 2 {
        return Err(String::from("current replay statistics mismatch"));
    }
    Ok(())
}

#[test]
fn current_forced_collision_keeps_distinct_checkpoints() -> Result<(), String> {
    let mut graph =
        ProfileStateGraph::with_digest(constant_profile_collision_digest);
    let first = graph
        .observe(current_checkpoint(0x41)?)
        .map_err(|error| format!("first collision checkpoint: {error:?}"))?;
    let second = graph
        .observe(current_checkpoint(0x42)?)
        .map_err(|error| format!("second collision checkpoint: {error:?}"))?;
    if first == second || graph.node_count() != 2 {
        return Err(String::from(
            "current collision merged unequal checkpoints",
        ));
    }
    Ok(())
}

fn terminal_variant(
    base: &ProfileMachineState,
    marker: u8,
) -> Result<ProfileMachineState, String> {
    let mut memory = base.memory().to_vec();
    let word = memory
        .get_mut(1)
        .ok_or_else(|| String::from("profile terminal memory missing"))?;
    *word = u32::from(marker);
    let registers = ProfileRegisters {
        accumulator: u32::from(marker),
        code_pointer: u32::from(marker).min(2),
        data_pointer: u32::from(marker).min(3),
    };
    let io = ProfileMachineIoState::new(
        vec![marker],
        0,
        Vec::new(),
        Some(Termination::HaltInstruction),
    )
    .map_err(|error| format!("profile terminal I/O failed: {error}"))?;
    ProfileMachineState::new_with_geometry(
        base.geometry(),
        memory,
        registers,
        io,
    )
    .map_err(|error| format!("profile terminal state failed: {error}"))
}

fn check_profile_terminal_reference(
    expected: &mut Option<ProfileTerminalFutureSnapshot>,
    observed: ProfileTerminalFutureSnapshot,
) -> Result<(), String> {
    match expected {
        Some(reference) if reference != &observed => {
            Err(String::from("profile terminal key retained dead state"))
        },
        Some(_reference) => Ok(()),
        None => {
            *expected = Some(observed);
            Ok(())
        },
    }
}

#[test]
fn terminated_profile_drops_dead_memory_registers_and_input()
-> Result<(), String> {
    let verified =
        verify_minimum_initial_halt_profile_width(current_profile(), b"QP")
            .map_err(|error| {
                format!("profile terminal width failed: {error}")
            })?;
    let mut live = ProfileMachine::from_verified_source(&verified, Vec::new())
        .map_err(|error| format!("profile terminal load failed: {error}"))?;
    if profile_terminal_future_snapshot(&live.snapshot_state())
        != Err(ProfileStateGraphError::StateNotTerminated)
    {
        return Err(String::from("live profile produced terminal future key"));
    }
    let outcome = live
        .step()
        .map_err(|error| format!("profile terminal halt: {error}"))?;
    if outcome != StepOutcome::Terminated(Termination::HaltInstruction) {
        return Err(format!(
            "profile terminal fixture did not halt: {outcome:?}"
        ));
    }
    let base = live.snapshot_state();
    let mut expected = None;
    for marker in [1u8, 2, 3] {
        let state = terminal_variant(&base, marker)?;
        let reduced =
            profile_terminal_future_snapshot(&state).map_err(|error| {
                format!("profile terminal projection: {error:?}")
            })?;
        check_profile_terminal_reference(&mut expected, reduced)?;
        let mut restored = ProfileMachine::from_snapshot(state.clone());
        let repeated = restored.step().map_err(|error| {
            format!("profile repeated terminal step: {error}")
        })?;
        if repeated != StepOutcome::Terminated(Termination::HaltInstruction)
            || restored.snapshot_state() != state
        {
            return Err(String::from("profile terminal future state changed"));
        }
    }
    Ok(())
}
