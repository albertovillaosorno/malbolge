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

#[path = "../../../research/algorithms/composition/state-graph/bench.rs"]
pub mod benchmark;
#[path = "../../../runtime/tiered-execution/domain/ir/main.rs"]
pub mod execution_ir;
#[path = "../../../research/algorithms/composition/state-graph/index.rs"]
pub mod indexed;
#[path = "../../../research/algorithms/composition/state-graph/state.rs"]
pub mod indexed_state;
#[path = "../../../research/algorithms/composition/state-graph/memory.rs"]
pub mod persistent;
#[path = "../../../research/algorithms/composition/state-graph/output.rs"]
pub mod persistent_output;
#[path = "../../../research/algorithms/composition/state-graph/profile.rs"]
pub mod profile_graph;
#[path = "../../../research/algorithms/composition/state-graph/region.rs"]
pub mod region_certificate;

use std::io::Result as IoResult;

fn main() -> IoResult<()> {
    benchmark::run()
}
