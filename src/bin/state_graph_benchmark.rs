// File:
//   - state_graph_benchmark.rs
// Path:
//   - src/bin/state_graph_benchmark.rs
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
//   - Cargo composition for the state-graph research benchmark executable.
// - Must-Not:
//   - Contain benchmark logic or expose research code as library API.
// - Allows:
//   - Inputs: responsibility-owned benchmark and exact profile graph modules.
//   - Outputs: one Cargo auto-discovered benchmark executable.
//   - Side effects: delegated benchmark process behavior only.
// - Split-When:
//   - Split when another research benchmark needs an independent executable.
// - Merge-When:
//   - Merge when Cargo no longer requires this composition surface.
// - Summary:
//   - Thin Cargo entrypoint for scalable state-graph benchmark research.
// - Description:
//   - Keeps exact graph and benchmark logic under the algorithm owner.
// - Usage:
//   - Invoked with `cargo run --release --bin state_graph_benchmark`.
// - Defaults:
//   - Adds no benchmark behavior beyond delegated modules.
//
// Related documents:
// - algorithms/self-modification-state-graph-optimizer/bench.rs
//
// Large file:
//   - false

//! Cargo composition root for the state-graph research benchmark.

#[path = "../../algorithms/self-modification-state-graph-optimizer/bench.rs"]
pub mod benchmark;
#[path = "../../algorithms/self-modification-state-graph-optimizer/index.rs"]
pub mod indexed;
#[path = "../../algorithms/self-modification-state-graph-optimizer/state.rs"]
pub mod indexed_state;
#[path = "../../algorithms/self-modification-state-graph-optimizer/memory.rs"]
pub mod persistent;
#[path = "../../algorithms/self-modification-state-graph-optimizer/output.rs"]
pub mod persistent_output;
#[path = "../../algorithms/self-modification-state-graph-optimizer/profile.rs"]
pub mod profile_graph;
#[path = "../../algorithms/self-modification-state-graph-optimizer/region.rs"]
pub mod region_certificate;

use std::io::Result as IoResult;

fn main() -> IoResult<()> {
    benchmark::run()
}
