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
//   - Cargo composition for exact-state graph research tests.
// - Must-Not:
//   - Implement state reduction or VM semantics.
// - Allows:
//   - Inputs: mirrored research implementation and deterministic fixtures.
//   - Outputs: one Cargo-discoverable research test target.
//   - Side effects: composition only.
// - Split-When:
//   - Split when reduced-state research gains an independent test lifecycle.
// - Merge-When:
//   - Merge when the state graph becomes production runtime infrastructure.
// - Summary:
//   - Composes the collision-safe state-graph research baseline.
// - Description:
//   - Keeps executable research code under its stable mirror owner.
// - Usage:
//   - Auto-discovered by Cargo workspace tests.
// - Defaults:
//   - No production API is exported from this integration target.
//

//! Cargo composition root for self-modification state-graph research.

#[path = "../tests/function/algorithms/domain/state-graph/a.rs"]
mod artifact_safety;
#[path = "../tests/function/algorithms/domain/state-graph/exact.rs"]
mod exact_state;
#[path = "../src/research/algorithms/composition/state-graph/index.rs"]
pub mod indexed;
#[path = "../tests/function/algorithms/domain/state-graph/i.rs"]
mod indexed_memory;
#[path = "../src/research/algorithms/composition/state-graph/state.rs"]
pub mod indexed_state;
#[path = "../tests/function/algorithms/domain/state-graph/o.rs"]
mod output_history;
#[path = "../src/research/algorithms/composition/state-graph/memory.rs"]
pub mod persistent;
#[path = "../tests/function/algorithms/domain/state-graph/p.rs"]
mod persistent_memory;
#[path = "../src/research/algorithms/composition/state-graph/output.rs"]
pub mod persistent_output;
#[path = "../src/research/algorithms/composition/state-graph/profile.rs"]
pub mod profile_graph;
#[path = "../tests/function/algorithms/domain/state-graph/c.rs"]
mod profile_state;
#[path = "../src/research/algorithms/composition/state-graph/artifact.rs"]
pub mod region_artifact;
#[path = "../src/research/algorithms/composition/state-graph/region.rs"]
pub mod region_certificate;
#[path = "../tests/function/algorithms/domain/state-graph/r.rs"]
mod region_safety;
#[path = "../src/research/algorithms/composition/state-graph/state_graph.rs"]
pub mod state_graph;
#[path = "../tests/function/algorithms/domain/state-graph/s.rs"]
mod state_identity;
#[path = "../tests/function/algorithms/domain/state-graph/d.rs"]
mod step_delta;
