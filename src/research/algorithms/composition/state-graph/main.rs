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

//! Cargo composition root for the state-graph research benchmark.

#[path = "artifact.rs"]
pub mod artifact;
#[path = "bench.rs"]
pub mod benchmark;
#[path = "index.rs"]
pub mod indexed;
#[path = "state.rs"]
pub mod indexed_state;
#[path = "memory.rs"]
pub mod persistent;
#[path = "output.rs"]
pub mod persistent_output;
#[path = "profile.rs"]
pub mod profile_graph;
#[path = "region.rs"]
pub mod region_certificate;
#[path = "state_graph.rs"]
pub mod state_graph;

use std::io::Result as IoResult;

fn main() -> IoResult<()> {
    benchmark::run()
}
