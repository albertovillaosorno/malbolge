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
//   - Host-parallel mapping contract for independent deterministic work items.
// - Must-Not:
//   - Select a threading runtime, reorder results, or inspect VM semantics.
// - Allows:
//   - Inputs: owned independent items, an explicit worker count, and one pure
//     item executor.
//   - Outputs: input-ordered results or stable scheduler failure evidence.
//   - Side effects: delegated entirely to the implementing outbound adapter.
// - Split-When:
//   - Async, process, or distributed execution requires separate semantics.
// - Merge-When:
//   - One host execution contract owns every independent mapping strategy.
// - Summary:
//   - Defines deterministic input-ordered host parallelism for VM application
//     orchestration.
// - Description:
//   - Application policy depends on this contract rather than `std::thread`.
// - Usage:
//   - Implemented by the scoped-thread adapter and consumed by batch services.
// - Defaults:
//   - Zero workers and worker panic fail explicitly without partial ordering.
//

//! Outbound contract for deterministic host-parallel item execution.

/// Stable failure exposed by a host-parallel execution adapter.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ParallelExecutionError {
    /// One host worker panicked instead of returning its deterministic chunk.
    WorkerPanicked {
        /// Zero-based worker index in deterministic spawn order.
        worker: usize,
    },
    /// Parallel execution was requested with zero workers.
    ZeroWorkers,
}

/// Outbound port for input-ordered execution of independent owned items.
pub trait ParallelExecutionPort {
    /// Executes each item exactly once and returns results in input order.
    ///
    /// # Errors
    ///
    /// Returns a stable scheduler failure when no worker exists or one worker
    /// panics.
    fn execute<Request, Output>(
        requests: Vec<Request>,
        worker_count: usize,
        execute: fn(Request) -> Output,
    ) -> Result<Vec<Output>, ParallelExecutionError>
    where
        Request: Send,
        Output: Send;
}
