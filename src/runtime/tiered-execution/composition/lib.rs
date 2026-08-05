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

#[path = "../application/cached_cycle.rs"]
pub mod cached_cycle;
#[path = "../application/cached_retry.rs"]
pub mod cached_retry;
#[path = "../application/scheduler.rs"]
pub mod continuation_scheduler;
#[path = "../adapter-outbound/cache/main.rs"]
pub mod execution_cache;
#[path = "../adapter-outbound/native/main.rs"]
pub mod execution_native;
#[path = "../application/interpreter_handoff.rs"]
pub mod interpreter_handoff;
#[path = "../application/leased_retry.rs"]
pub mod leased_retry;
#[path = "../application/native_retry.rs"]
pub mod native_retry;
#[path = "../application/retry_cycle.rs"]
pub mod retry_cycle;
#[path = "../application/retry_planner.rs"]
pub mod retry_planner;
#[path = "../application/retry_policy.rs"]
pub mod retry_policy;
#[path = "../application/retry_router.rs"]
pub mod retry_router;
#[path = "../application/retry_turn.rs"]
pub mod retry_turn;
