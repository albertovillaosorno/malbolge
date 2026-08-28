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
//   - Incremental state reconstruction, collision, and lineage fixtures.
// - Must-Not:
//   - Infer state from private runtime internals or accept digest-only merges.
// - Allows:
//   - Inputs: complete root checkpoints and public current-profile traces.
//   - Outputs: exact oracle equality and collision-safe node identities.
//   - Side effects: test-process allocation only.
// - Split-When:
//   - Split when cross-lineage content-addressed roots gain separate evidence.
// - Merge-When:
//   - Merge when production graph identity owns the same correctness boundary.
// - Summary:
//   - Proves incremental state identity without full-memory hash per
//   - observation.
// - Description:
//   - Replays current traces, forces digest collisions, and rejects foreign
//   - roots.
// - Usage:
//   - Composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Complete runtime checkpoints remain the independent materialization
//   - oracle.
//

//! Correctness fixtures for incremental exact indexed-state identity.

use malbolge::{
    ProfileMachine, ProfileStepTrace, StepOutcome, current_profile,
    verify_minimum_initial_halt_profile_width,
};

use crate::indexed_state::{
    IndexedMachineState, IndexedStateGraph, IndexedStateGraphError,
    constant_indexed_collision_digest,
};

const CURRENT_SOURCE: &[u8] = b"(=%`qL";
const STEP_BUDGET: usize = 8;

#[test]
fn derived_width_checkpoint_survives_indexed_state_roundtrip()
-> Result<(), String> {
    let verified =
        verify_minimum_initial_halt_profile_width(current_profile(), b"QP")
            .map_err(|error| {
                format!("derived width verification failed: {error}")
            })?;
    let mut machine =
        ProfileMachine::from_verified_source(&verified, Vec::new())
            .map_err(|error| format!("derived machine load failed: {error}"))?;
    let root = machine.snapshot_state();
    let mut indexed = IndexedMachineState::from_checkpoint(&root)
        .map_err(|error| format!("derived indexed root failed: {error:?}"))?;
    let mut trace_record = None;
    let _outcome = machine
        .step_traced(&mut |trace: &ProfileStepTrace| {
            trace_record = Some(*trace);
        })
        .map_err(|error| format!("derived trace step failed: {error}"))?;
    let trace =
        trace_record.ok_or_else(|| String::from("derived trace missing"))?;
    indexed = indexed
        .apply_trace(&trace)
        .map_err(|error| format!("derived indexed apply failed: {error:?}"))?;
    let materialized = indexed
        .materialize_checkpoint()
        .map_err(|error| format!("derived materialize failed: {error:?}"))?;
    if materialized != machine.snapshot_state() {
        return Err(String::from("derived indexed roundtrip drifted"));
    }
    if materialized.geometry() != verified.geometry() {
        return Err(String::from("derived geometry was not preserved"));
    }
    Ok(())
}

#[test]
fn current_trace_reconstructs_and_replay_deduplicates() -> Result<(), String> {
    let mut machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| {
            format!("indexed state fixture load failed: {error}")
        })?;
    let checkpoint = machine.snapshot_state();
    let mut state = IndexedMachineState::from_checkpoint(&checkpoint)
        .map_err(|error| format!("indexed state root failed: {error:?}"))?;
    let mut graph = IndexedStateGraph::new(state.clone());
    for _step in 0..STEP_BUDGET {
        let mut trace_record = None;
        let outcome = machine
            .step_traced(&mut |trace: &ProfileStepTrace| {
                trace_record = Some(*trace);
            })
            .map_err(|error| format!("indexed state step failed: {error}"))?;
        let trace = trace_record
            .ok_or_else(|| String::from("indexed state trace missing"))?;
        state = state.apply_trace(&trace).map_err(|error| {
            format!("indexed state apply failed: {error:?}")
        })?;
        let materialized = state.materialize_checkpoint().map_err(|error| {
            format!("indexed state materialize failed: {error:?}")
        })?;
        if materialized != machine.snapshot_state() {
            return Err(String::from(
                "incremental state diverged from runtime",
            ));
        }
        let first = graph.observe(state.clone()).map_err(|error| {
            format!("indexed state observe failed: {error:?}")
        })?;
        let replay = graph.observe(state.clone()).map_err(|error| {
            format!("indexed state replay failed: {error:?}")
        })?;
        if first != replay {
            return Err(String::from(
                "exact incremental replay did not deduplicate",
            ));
        }
        if outcome != StepOutcome::Continued {
            break;
        }
    }
    if graph.deduplicated_observations() == 0 {
        return Err(String::from(
            "incremental graph recorded no deduplication",
        ));
    }
    Ok(())
}

#[test]
fn forced_digest_collision_never_merges_distinct_states() -> Result<(), String>
{
    let mut machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| {
            format!("indexed collision fixture failed: {error}")
        })?;
    let seed = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("indexed collision root failed: {error:?}"))?;
    let mut graph = IndexedStateGraph::with_digest(
        seed.clone(),
        constant_indexed_collision_digest,
    );
    let mut trace_record = None;
    let _outcome = machine
        .step_traced(&mut |trace: &ProfileStepTrace| {
            trace_record = Some(*trace);
        })
        .map_err(|error| format!("indexed collision step failed: {error}"))?;
    let trace = trace_record
        .ok_or_else(|| String::from("indexed collision trace missing"))?;
    let next = seed.apply_trace(&trace).map_err(|error| {
        format!("indexed collision apply failed: {error:?}")
    })?;
    let next_id = graph.observe(next).map_err(|error| {
        format!("indexed collision observe failed: {error:?}")
    })?;
    if next_id.value() == 0 || graph.node_count() != 2 {
        return Err(String::from(
            "forced digest collision merged distinct states",
        ));
    }
    Ok(())
}

#[test]
fn independently_constructed_root_is_foreign_lineage() -> Result<(), String> {
    let machine = ProfileMachine::from_source(
        current_profile(),
        CURRENT_SOURCE,
        Vec::new(),
    )
    .map_err(|error| format!("indexed lineage fixture failed: {error}"))?;
    let checkpoint = machine.snapshot_state();
    let seed = IndexedMachineState::from_checkpoint(&checkpoint)
        .map_err(|error| format!("indexed lineage seed failed: {error:?}"))?;
    let foreign =
        IndexedMachineState::from_checkpoint(&checkpoint).map_err(|error| {
            format!("indexed lineage foreign failed: {error:?}")
        })?;
    let mut graph = IndexedStateGraph::new(seed);
    let result = graph.observe(foreign);
    if result == Err(IndexedStateGraphError::ForeignLineage) {
        Ok(())
    } else {
        Err(format!("foreign lineage was not rejected: {result:?}"))
    }
}
