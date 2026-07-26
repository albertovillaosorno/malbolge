// File:
//   - batch.rs
// Path:
//   - vm/src/batch.rs
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
//   - Deterministic execution of independent Malbolge machine batches.
// - Must-Not:
//   - Introduce guest-visible parallel semantics or share mutable machine
//     state.
// - Allows:
//   - Inputs: owned source/machine requests and explicit step budgets/workers.
// - Outputs:
//   - Input-ordered completed or rejected per-instance execution results.
// - Side effects:
//   - Host threads and mutation only of each independently owned machine.
// - Split-When:
//   - Split when an accelerator backend gains an independent batch lifecycle.
// - Merge-When:
//   - Merge when another execution module owns identical independent batching.
// - Summary:
//   - Sequential and host-parallel batch execution with deterministic ordering.
// - Description:
//   - Parallel workers process disjoint owned requests and join in input order.
// - Usage:
//   - Used by fuzzing, verification, synthesis, and independent candidate runs.
// - Defaults:
//   - `execute_batch` is sequential; parallel worker count is always explicit.
//
// Related documents:
// - docs/technical/runtime/execution/batch-vm-execution.md
// - docs/technical/adr/verification-trust-boundary.md
//
// Large file:
//   - false
//

//! Deterministic batching for independent Malbolge machine executions.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::thread;

use crate::{ExecutionError, ExecutionMachine, ExecutionMode, RunOutcome};

#[derive(Clone, Debug)]
enum BatchSeed {
    Machine(ExecutionMachine),
    Source {
        input: Vec<u8>,
        mode: ExecutionMode,
        source: Vec<u8>,
    },
}

#[derive(Clone, Debug)]
struct BuiltRequest {
    machine: ExecutionMachine,
    step_budget: usize,
}

/// Host-level failure of the batch scheduler itself.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BatchError {
    /// A host worker panicked instead of returning deterministic results.
    WorkerPanicked {
        /// Zero-based worker index in deterministic spawn order.
        worker: usize,
    },
    /// Parallel execution was requested with zero workers.
    ZeroWorkers,
}

impl Display for BatchError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::WorkerPanicked { worker } => {
                write!(f, "batch worker {worker} panicked")
            },
            Self::ZeroWorkers => {
                f.write_str("batch execution requires at least one worker")
            },
        }
    }
}

/// One owned independent batch execution request.
#[derive(Clone, Debug)]
pub struct BatchRequest {
    seed: BatchSeed,
    step_budget: usize,
}

impl BatchRequest {
    fn build(self) -> Result<BuiltRequest, ExecutionError> {
        let Self { seed, step_budget } = self;
        let machine = match seed {
            BatchSeed::Machine(machine) => machine,
            BatchSeed::Source { input, mode, source } => {
                ExecutionMachine::from_source(&source, input, mode)?
            },
        };
        Ok(BuiltRequest { machine, step_budget })
    }

    /// Creates a batch request from an already constructed execution machine.
    #[must_use]
    pub const fn from_machine(
        machine: ExecutionMachine,
        step_budget: usize,
    ) -> Self {
        Self {
            seed: BatchSeed::Machine(machine),
            step_budget,
        }
    }

    /// Creates a request from source bytes and deterministic byte input.
    #[must_use]
    pub const fn from_source(
        source: Vec<u8>,
        input: Vec<u8>,
        mode: ExecutionMode,
        step_budget: usize,
    ) -> Self {
        Self {
            seed: BatchSeed::Source { input, mode, source },
            step_budget,
        }
    }

    /// Returns the immutable execution mode selected for this request.
    #[must_use]
    pub const fn mode(&self) -> ExecutionMode {
        match &self.seed {
            BatchSeed::Machine(machine) => machine.mode(),
            BatchSeed::Source { mode, .. } => *mode,
        }
    }

    /// Returns the maximum semantic steps requested for this instance.
    #[must_use]
    pub const fn step_budget(&self) -> usize {
        self.step_budget
    }
}

/// One input-ordered independent batch execution result.
#[derive(Clone, Debug)]
pub enum BatchResult {
    /// Construction and bounded execution completed without a machine error.
    Completed {
        /// Final owned machine state for inspection or resumed execution.
        machine: ExecutionMachine,
        /// Bounded run outcome returned by the machine.
        outcome: RunOutcome,
    },
    /// Construction or execution rejected this one request.
    Rejected {
        /// Mode-tagged deterministic rejection.
        error: ExecutionError,
        /// Final state when construction succeeded before execution failed.
        machine: Option<ExecutionMachine>,
    },
}

impl BatchResult {
    /// Returns the deterministic rejection, when this item failed.
    #[must_use]
    pub const fn error(&self) -> Option<ExecutionError> {
        match self {
            Self::Completed { .. } => None,
            Self::Rejected { error, .. } => Some(*error),
        }
    }

    /// Returns the owned machine state when construction succeeded.
    #[must_use]
    pub const fn machine(&self) -> Option<&ExecutionMachine> {
        match self {
            Self::Completed { machine, .. }
            | Self::Rejected {
                machine: Some(machine), ..
            } => Some(machine),
            Self::Rejected { machine: None, .. } => None,
        }
    }

    /// Returns the bounded run outcome for successfully completed execution.
    #[must_use]
    pub const fn outcome(&self) -> Option<RunOutcome> {
        match self {
            Self::Completed { outcome, .. } => Some(*outcome),
            Self::Rejected { .. } => None,
        }
    }
}

/// Executes all independent requests sequentially in exact input order.
#[must_use]
pub fn execute_batch(requests: Vec<BatchRequest>) -> Vec<BatchResult> {
    requests.into_iter().map(execute_one).collect()
}

/// Executes independent requests across explicit host workers.
///
/// Results are always returned in exact input order. Worker scheduling cannot
/// change per-instance machine state, I/O, diagnostics, or result ordering.
///
/// # Errors
///
/// Returns [`BatchError::ZeroWorkers`] for `worker_count == 0`, or
/// [`BatchError::WorkerPanicked`] if a host worker panics.
pub fn execute_batch_parallel(
    requests: Vec<BatchRequest>,
    worker_count: usize,
) -> Result<Vec<BatchResult>, BatchError> {
    if worker_count == 0 {
        return Err(BatchError::ZeroWorkers);
    }
    if requests.is_empty() {
        return Ok(Vec::new());
    }

    let workers = worker_count.min(requests.len());
    let chunk_size = requests.len().div_ceil(workers);
    let chunks = owned_chunks(requests, chunk_size);
    thread::scope(|scope| {
        let handles = chunks
            .into_iter()
            .enumerate()
            .map(|(worker, chunk)| {
                (
                    worker,
                    scope.spawn(move || {
                        chunk.into_iter().map(execute_one).collect::<Vec<_>>()
                    }),
                )
            })
            .collect::<Vec<_>>();
        let mut results = Vec::new();
        for (worker, handle) in handles {
            let mut chunk_results = handle
                .join()
                .map_err(|_panic| BatchError::WorkerPanicked { worker })?;
            results.append(&mut chunk_results);
        }
        Ok(results)
    })
}

fn execute_one(request: BatchRequest) -> BatchResult {
    let BuiltRequest { mut machine, step_budget } = match request.build() {
        Ok(built) => built,
        Err(error) => {
            return BatchResult::Rejected { error, machine: None };
        },
    };
    match machine.run(step_budget) {
        Ok(outcome) => BatchResult::Completed { machine, outcome },
        Err(error) => BatchResult::Rejected {
            error,
            machine: Some(machine),
        },
    }
}

fn owned_chunks(
    requests: Vec<BatchRequest>,
    chunk_size: usize,
) -> Vec<Vec<BatchRequest>> {
    let mut remaining = requests.into_iter();
    let mut chunks = Vec::new();
    loop {
        let chunk = remaining.by_ref().take(chunk_size).collect::<Vec<_>>();
        if chunk.is_empty() {
            break;
        }
        chunks.push(chunk);
    }
    chunks
}
