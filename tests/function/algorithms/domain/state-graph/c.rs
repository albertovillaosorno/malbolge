// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
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
//   - Exercises 4,782,969-word checkpoints without weakening equality.
// - Usage:
//   - Composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Full checkpoints are correctness evidence, not a performance design.
//

//! Exact current-profile checkpoint graph fixtures.

use malbolge::{ProfileMachine, current_profile};

use crate::profile_graph::{
    ProfileStateGraph, constant_profile_collision_digest,
};

const CURRENT_SOURCE: &[u8] = b"(=%`qL";

fn current_checkpoint(
    input: u8,
) -> Result<malbolge::ProfileMachineState, String> {
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
