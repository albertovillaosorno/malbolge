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
//   - Deterministic execution of independent classic/profiled machine batches.
// - Must-Not:
//   - Introduce guest-visible parallel semantics or share mutable machine
//   - state.
// - Allows:
//   - Inputs: owned source/machine requests and explicit step budgets/workers.
//   - Outputs: input-ordered completed or rejected per-instance results.
//   - Side effects: host threads and independently owned machine mutation only.
// - Split-When:
//   - Split when an accelerator backend gains an independent batch lifecycle.
// - Merge-When:
//   - Merge when another execution module owns identical independent batching.
// - Summary:
//   - Sequential and host-parallel batch execution with deterministic ordering.
// - Description:
//   - One host scheduler processes disjoint classic or profiled owned requests.
// - Usage:
//   - Used by fuzzing, verification, synthesis, and independent candidate runs.
// - Defaults:
//   - Sequential APIs are baselines; parallel worker count is always explicit.
//
// Related documents:
// - docs/technical/runtime/execution/batch-vm-execution.md
// - docs/technical/adr/verification-trust-boundary.md
//
// Large file:
//   - false
//

//! Deterministic batching for independent classic and profile-driven machines.

#[path = "batch_backend.rs"]
mod backend;

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::thread;

pub use backend::{
    BatchBackendCompletion, BatchBackendRequest, BatchExecutionBackend,
    BatchExecutionOrigin, BatchExecutionReport, ProfileBatchBackendCompletion,
    ProfileBatchBackendRequest, ProfileBatchExecutionBackend,
    execute_batch_with_backend, execute_batch_with_backend_report,
    execute_profile_batch_with_backend,
    execute_profile_batch_with_backend_report,
};

use crate::{
    ExecutionError, ExecutionMachine, ExecutionMode, ProfileDescriptor,
    ProfileMachine, ProfileMachineError, RunOutcome,
};

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
struct BuiltProfileRequest {
    machine: ProfileMachine,
    step_budget: usize,
}

#[derive(Clone, Debug)]
struct BuiltRequest {
    machine: ExecutionMachine,
    step_budget: usize,
}

#[derive(Clone, Debug)]
enum ProfileBatchSeed {
    Machine(ProfileMachine),
    Source {
        input: Vec<u8>,
        profile: &'static ProfileDescriptor,
        source: Vec<u8>,
    },
}

/// Host-level failure of the shared batch scheduler itself.
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

/// One owned independent classic batch execution request.
#[derive(Clone, Debug)]
pub struct BatchRequest {
    seed: BatchSeed,
    step_budget: usize,
}

/// One input-ordered independent classic batch execution result.
#[derive(Clone, Debug)]
pub enum BatchResult {
    /// Construction and bounded execution completed without a machine error.
    Completed {
        /// Final owned classic machine state for inspection or resumed
        /// execution.
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

/// One owned independent profile-driven batch execution request.
#[derive(Clone, Debug)]
pub struct ProfileBatchRequest {
    seed: ProfileBatchSeed,
    step_budget: usize,
}

/// One input-ordered independent profile-driven batch execution result.
#[derive(Clone, Debug)]
pub enum ProfileBatchResult {
    /// Construction and bounded execution completed without a machine error.
    Completed {
        /// Final owned profile-driven machine state for inspection/resume.
        machine: ProfileMachine,
        /// Bounded run outcome returned by the machine.
        outcome: RunOutcome,
    },
    /// Construction or execution rejected this one request.
    Rejected {
        /// Deterministic profile-driven rejection.
        error: ProfileMachineError,
        /// Final state when construction succeeded before execution failed.
        machine: Option<ProfileMachine>,
    },
}

impl BatchError {
    const fn worker_panicked(worker: usize) -> Self {
        Self::WorkerPanicked { worker }
    }
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

    /// Creates a batch request from an already constructed classic machine.
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

    /// Creates a classic request from source bytes and deterministic byte
    /// input.
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

    /// Returns the immutable execution mode selected for this classic request.
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

impl BatchResult {
    /// Returns the deterministic rejection, when this classic item failed.
    #[must_use]
    pub const fn error(&self) -> Option<ExecutionError> {
        match self {
            Self::Completed { .. } => None,
            Self::Rejected { error, .. } => Some(*error),
        }
    }

    /// Returns the owned classic machine state when construction succeeded.
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

impl ProfileBatchRequest {
    fn build(self) -> Result<BuiltProfileRequest, ProfileMachineError> {
        let Self { seed, step_budget } = self;
        let machine = match seed {
            ProfileBatchSeed::Machine(machine) => machine,
            ProfileBatchSeed::Source { input, profile, source } => {
                ProfileMachine::from_source(profile, &source, input)?
            },
        };
        Ok(BuiltProfileRequest { machine, step_budget })
    }

    /// Creates a request from an already constructed profile-driven machine.
    #[must_use]
    pub const fn from_machine(
        machine: ProfileMachine,
        step_budget: usize,
    ) -> Self {
        Self {
            seed: ProfileBatchSeed::Machine(machine),
            step_budget,
        }
    }

    /// Creates a request from source and one explicit canonical profile.
    #[must_use]
    pub const fn from_source(
        profile: &'static ProfileDescriptor,
        source: Vec<u8>,
        input: Vec<u8>,
        step_budget: usize,
    ) -> Self {
        Self {
            seed: ProfileBatchSeed::Source { input, profile, source },
            step_budget,
        }
    }

    /// Returns the exact canonical profile selected for this request.
    #[must_use]
    pub const fn profile(&self) -> &'static ProfileDescriptor {
        match &self.seed {
            ProfileBatchSeed::Machine(machine) => machine.profile(),
            ProfileBatchSeed::Source { profile, .. } => profile,
        }
    }

    /// Returns the maximum semantic steps requested for this instance.
    #[must_use]
    pub const fn step_budget(&self) -> usize {
        self.step_budget
    }
}

impl ProfileBatchResult {
    /// Returns the deterministic rejection, when this profiled item failed.
    #[must_use]
    pub const fn error(&self) -> Option<ProfileMachineError> {
        match self {
            Self::Completed { .. } => None,
            Self::Rejected { error, .. } => Some(*error),
        }
    }

    /// Returns the owned profile machine state when construction succeeded.
    #[must_use]
    pub const fn machine(&self) -> Option<&ProfileMachine> {
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

/// Executes all independent classic requests sequentially in exact input order.
#[must_use]
pub fn execute_batch(requests: Vec<BatchRequest>) -> Vec<BatchResult> {
    requests.into_iter().map(execute_one).collect()
}

/// Executes independent classic requests across explicit host workers.
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
    execute_parallel(requests, worker_count, execute_one)
}

fn execute_one(request: BatchRequest) -> BatchResult {
    match request.build() {
        Ok(built) => execute_built(built),
        Err(error) => BatchResult::Rejected { error, machine: None },
    }
}

fn execute_built(request: BuiltRequest) -> BatchResult {
    let BuiltRequest { mut machine, step_budget } = request;
    match machine.run(step_budget) {
        Ok(outcome) => BatchResult::Completed { machine, outcome },
        Err(error) => BatchResult::Rejected {
            error,
            machine: Some(machine),
        },
    }
}

fn execute_parallel<Request, Output>(
    requests: Vec<Request>,
    worker_count: usize,
    execute: fn(Request) -> Output,
) -> Result<Vec<Output>, BatchError>
where
    Request: Send,
    Output: Send,
{
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
                        chunk.into_iter().map(execute).collect::<Vec<_>>()
                    }),
                )
            })
            .collect::<Vec<_>>();
        let mut results = Vec::new();
        for (worker, handle) in handles {
            let mut chunk_results = handle
                .join()
                .map_err(|_panic| BatchError::worker_panicked(worker))?;
            results.append(&mut chunk_results);
        }
        Ok(results)
    })
}

/// Executes all independent profile requests sequentially in exact input order.
#[must_use]
pub fn execute_profile_batch(
    requests: Vec<ProfileBatchRequest>,
) -> Vec<ProfileBatchResult> {
    requests.into_iter().map(execute_profile_one).collect()
}

/// Executes independent profile-driven requests across explicit host workers.
///
/// Results remain in exact input order and each machine retains its exact
/// canonical profile descriptor regardless of host scheduling.
///
/// # Errors
///
/// Returns the same host scheduler failures as [`execute_batch_parallel`].
pub fn execute_profile_batch_parallel(
    requests: Vec<ProfileBatchRequest>,
    worker_count: usize,
) -> Result<Vec<ProfileBatchResult>, BatchError> {
    execute_parallel(requests, worker_count, execute_profile_one)
}

fn execute_profile_one(request: ProfileBatchRequest) -> ProfileBatchResult {
    match request.build() {
        Ok(built) => execute_profile_built(built),
        Err(error) => ProfileBatchResult::Rejected { error, machine: None },
    }
}

fn execute_profile_built(request: BuiltProfileRequest) -> ProfileBatchResult {
    let BuiltProfileRequest { mut machine, step_budget } = request;
    match machine.run(step_budget) {
        Ok(outcome) => ProfileBatchResult::Completed { machine, outcome },
        Err(error) => ProfileBatchResult::Rejected {
            error,
            machine: Some(machine),
        },
    }
}

fn owned_chunks<Request>(
    requests: Vec<Request>,
    chunk_size: usize,
) -> Vec<Vec<Request>> {
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
