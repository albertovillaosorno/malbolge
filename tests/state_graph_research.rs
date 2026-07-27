// File:
//   - state_graph_research.rs
// Path:
//   - tests/state_graph_research.rs
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
// Related documents:
// - docs/research/algorithms/self-modification-state-graph-optimizer/research.
//   md
//
// Large file:
//   - false

//! Cargo composition root for self-modification state-graph research.

#[path = "../algorithms/self-modification-state-graph-optimizer/tests/exact.rs"]
mod exact_state;
#[path = "../algorithms/self-modification-state-graph-optimizer/state_graph.rs"]
pub mod state_graph;
