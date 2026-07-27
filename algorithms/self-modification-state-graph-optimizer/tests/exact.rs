// File:
//   - exact.rs
// Path:
//   - algorithms/self-modification-state-graph-optimizer/tests/exact.rs
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
//   - Exact-state deduplication, collision, and input-separation fixtures.
// - Must-Not:
//   - Assert reduced-state equivalence or performance improvement.
// - Allows:
//   - Inputs: public exact-state graph research API and classic fixtures.
//   - Outputs: collision-safe baseline correctness evidence.
//   - Side effects: test-process CPU and memory only.
// - Split-When:
//   - Split when a reduced graph key gains separate falsification fixtures.
// - Merge-When:
//   - Merge when exact and reduced graph models share one proved key.
// - Summary:
//   - Proves exact merges survive forced hash collision and replay.
// - Description:
//   - Identical runs deduplicate while distinct inputs remain distinct states.
// - Usage:
//   - Composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Uses classic specification mode and bounded deterministic execution.
//
// Related documents:
// - math/algorithms/self-modification-state-graph-optimizer.tex
//
// Large file:
//   - false

//! Exact-state graph baseline correctness fixtures.

use malbolge::ExecutionMode;

use crate::state_graph::{
    ExactStateGraph, admitted_mode, constant_collision_digest,
};

const BUDGET: usize = 8;
const ROUNDTRIP: &[u8] = include_bytes!(
    "../../../tests/compatibility/specification/spec-io-roundtrip.malbolge"
);

#[test]
fn exact_replay_deduplicates_nodes_and_edges() -> Result<(), String> {
    let mut graph = ExactStateGraph::new();
    graph
        .record_run(ROUNDTRIP, &[0x41], BUDGET)
        .map_err(|error| format!("first graph run failed: {error:?}"))?;
    let nodes = graph.node_count();
    let edges = graph.edge_count();
    let observations = graph.observations();
    graph
        .record_run(ROUNDTRIP, &[0x41], BUDGET)
        .map_err(|error| format!("replay graph run failed: {error:?}"))?;
    if graph.node_count() != nodes || graph.edge_count() != edges {
        return Err(String::from(
            "identical replay changed unique graph shape",
        ));
    }
    if graph.observations() <= observations {
        return Err(String::from("replay did not add state observations"));
    }
    if graph.deduplicated_observations() == 0 {
        return Err(String::from("replay did not confirm exact deduplication"));
    }
    Ok(())
}

#[test]
fn forced_digest_collision_keeps_distinct_inputs() -> Result<(), String> {
    let mut graph = ExactStateGraph::with_digest(constant_collision_digest);
    graph
        .record_run(ROUNDTRIP, &[0x41], 0)
        .map_err(|error| format!("first collision run failed: {error:?}"))?;
    graph
        .record_run(ROUNDTRIP, &[0x42], 0)
        .map_err(|error| format!("second collision run failed: {error:?}"))?;
    if graph.node_count() != 2 {
        return Err(format!(
            "forced digest collision merged exact states: nodes={}",
            graph.node_count()
        ));
    }
    Ok(())
}

#[test]
fn exact_baseline_admits_specification_mode_only() -> Result<(), String> {
    if admitted_mode() == ExecutionMode::Specification {
        Ok(())
    } else {
        Err(String::from(
            "exact graph baseline selected non-specification mode",
        ))
    }
}
