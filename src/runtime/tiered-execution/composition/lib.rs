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
//   - Canonical module topology for the complete tiered-execution function.
// - Must-Not:
//   - Implement retry policy, native lowering, cache semantics, or VM behavior.
// - Allows:
//   - Inputs: responsibility-owned domain, application, and adapter modules.
//   - Outputs: one logical crate root for tooling and future packaging.
//   - Side effects: composition only.
// - Split-When:
//   - Split when independently packaged tiered capabilities gain separate
//     roots.
// - Merge-When:
//   - Merge when another root owns the exact same module topology.
// - Summary:
//   - Declares the canonical tiered-execution module tree.
// - Description:
//   - Mirrors the product wiring exercised by the integration-test crate.
// - Usage:
//   - Consumed by repository architecture analysis and future crate packaging.
// - Defaults:
//   - Every production module has one same-function logical parent.
//

//! Canonical module topology for the complete tiered-execution function.

#[path = "tier/cached_cycle.rs"]
pub mod cached_cycle;
#[path = "tier/cached_retry.rs"]
pub mod cached_retry;
#[path = "tier/scheduler.rs"]
pub mod continuation_scheduler;
#[path = "../adapter-outbound/cache/main.rs"]
pub mod execution_cache;
#[path = "../adapter-outbound/native/main.rs"]
pub mod execution_native;
#[path = "tier/geometry_handoff.rs"]
pub mod geometry_interpreter_handoff;
#[path = "tier/geometry_native.rs"]
pub mod geometry_native_admission;
#[path = "tier/geometry_noop.rs"]
pub mod geometry_native_no_operation;
#[path = "tier/geometry_rotate.rs"]
pub mod geometry_native_rotate;
#[path = "tier/geometry_rotseq.rs"]
pub mod geometry_native_rotate_sequence;
#[path = "tier/geometry_cache.rs"]
pub mod geometry_native_pair_cache;
#[path = "tier/geometry_seq.rs"]
pub mod geometry_native_sequence;
#[path = "tier/handoff.rs"]
pub mod interpreter_handoff;
#[path = "tier/leased_retry.rs"]
pub mod leased_retry;
#[path = "tier/native_retry.rs"]
pub mod native_retry;
#[path = "tier/retry_cycle.rs"]
pub mod retry_cycle;
#[path = "tier/retry_planner.rs"]
pub mod retry_planner;
#[path = "tier/retry_policy.rs"]
pub mod retry_policy;
#[path = "tier/retry_router.rs"]
pub mod retry_router;
#[path = "tier/retry_turn.rs"]
pub mod retry_turn;
