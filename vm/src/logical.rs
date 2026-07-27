// File:
//   - logical.rs
// Path:
//   - vm/src/logical.rs
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
//   - Explicit logical task ordering and deterministic host-side result joins.
// - Must-Not:
//   - Introduce guest threads, shared guest state, or completion-order
//     semantics.
// - Allows:
//   - Inputs: owned independent batch requests plus stable logical task IDs.
//   - Outputs: task-ID-ordered results and deterministic joined output bytes.
//   - Side effects: delegates only to independent batch host execution.
// - Split-When:
//   - Split when another logical join artifact needs an independent contract.
// - Merge-When:
//   - Merge when batch execution itself gains explicit logical task identity.
// - Summary:
//   - Orders independent host work by logical identity before deterministic
//     join.
// - Description:
//   - Uses structural ownership as the independence boundary and never exposes
//     host completion order to guest-visible or generated-artifact ordering.
// - Usage:
//   - Wrap independent `BatchRequest` values in `LogicalTask` and execute them.
// - Defaults:
//   - Sequential execution is the semantic baseline; worker count is explicit.
//
// Related documents:
// - docs/technical/runtime/execution/deterministic-logical-concurrency.md
// - docs/technical/runtime/execution/batch-vm-execution.md
// - docs/technical/adr/verification-trust-boundary.md
//
// Large file:
//   - false

//! Deterministic logical ordering over structurally independent host VM tasks.

use std::fmt::{Display, Formatter, Result as FormatResult};

use crate::{
    BatchError, BatchRequest, BatchResult, ExecutionError, ProfileBatchRequest,
    ProfileBatchResult, ProfileMachineError, execute_batch,
    execute_batch_parallel, execute_profile_batch,
    execute_profile_batch_parallel,
};

/// Stable logical identity used to define task and join ordering.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct LogicalTaskId(u64);

/// One structurally independent owned VM task with explicit logical identity.
#[derive(Clone, Debug)]
pub struct LogicalTask {
    id: LogicalTaskId,
    request: BatchRequest,
}

/// One task-ID-tagged result returned in exact logical order.
#[derive(Clone, Debug)]
pub struct LogicalTaskResult {
    id: LogicalTaskId,
    result: BatchResult,
}

#[derive(Clone, Debug)]
struct LogicalPlan {
    ids: Vec<LogicalTaskId>,
    requests: Vec<BatchRequest>,
}

/// One structurally independent profile-driven task with logical identity.
#[derive(Clone, Debug)]
pub struct ProfileLogicalTask {
    id: LogicalTaskId,
    request: ProfileBatchRequest,
}

/// One profile batch result tagged with exact logical identity.
#[derive(Clone, Debug)]
pub struct ProfileLogicalTaskResult {
    id: LogicalTaskId,
    result: ProfileBatchResult,
}

#[derive(Clone, Debug)]
struct ProfileLogicalPlan {
    ids: Vec<LogicalTaskId>,
    requests: Vec<ProfileBatchRequest>,
}

/// Deterministic logical scheduling failure before or around batch execution.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LogicalConcurrencyError {
    /// Underlying host batch scheduling failed.
    Batch(BatchError),
    /// Two independent requests claimed the same logical identity.
    DuplicateTaskId {
        /// Repeated logical task identity.
        task_id: LogicalTaskId,
    },
}

/// Deterministic failure while serializing logical task outputs.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LogicalJoinError {
    /// Results were supplied outside strict ascending logical order.
    OutOfOrder {
        /// Current task identity that violated strict ascending order.
        current: LogicalTaskId,
        /// Previous task identity in the supplied result sequence.
        previous: LogicalTaskId,
    },
    /// One logical task was rejected, so a successful artifact join is invalid.
    RejectedTask {
        /// Deterministic execution rejection from the task.
        error: ExecutionError,
        /// Exact logical identity of the rejected task.
        task_id: LogicalTaskId,
    },
}

/// Deterministic failure while joining profile-driven logical outputs.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileLogicalJoinError {
    /// Results were supplied outside strict ascending logical order.
    OutOfOrder {
        /// Current task identity that violated strict ascending order.
        current: LogicalTaskId,
        /// Previous task identity in the supplied result sequence.
        previous: LogicalTaskId,
    },
    /// One profile-driven task rejected, so successful join is invalid.
    RejectedTask {
        /// Deterministic profile-driven execution rejection.
        error: ProfileMachineError,
        /// Exact logical identity of the rejected task.
        task_id: LogicalTaskId,
    },
}

impl Display for LogicalConcurrencyError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Batch(error) => write!(f, "logical concurrency: {error}"),
            Self::DuplicateTaskId { task_id } => write!(
                f,
                "logical concurrency duplicate task id={}",
                task_id.value()
            ),
        }
    }
}

impl Display for LogicalJoinError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::OutOfOrder { current, previous } => write!(
                f,
                "logical join order violation previous={} current={}",
                previous.value(),
                current.value()
            ),
            Self::RejectedTask { error, task_id } => write!(
                f,
                "logical join rejected task id={}: {error}",
                task_id.value()
            ),
        }
    }
}

impl Display for ProfileLogicalJoinError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::OutOfOrder { current, previous } => write!(
                f,
                "profile logical join order violation previous={} current={}",
                previous.value(),
                current.value()
            ),
            Self::RejectedTask { error, task_id } => write!(
                f,
                "profile logical join rejected task id={}: {error}",
                task_id.value()
            ),
        }
    }
}

impl From<BatchError> for LogicalConcurrencyError {
    fn from(error: BatchError) -> Self {
        Self::Batch(error)
    }
}

impl LogicalTask {
    /// Returns the stable logical identity that controls join order.
    #[must_use]
    pub const fn id(&self) -> LogicalTaskId {
        self.id
    }

    /// Creates one owned independent task with explicit logical identity.
    #[must_use]
    pub const fn new(id: LogicalTaskId, request: BatchRequest) -> Self {
        Self { id, request }
    }
}

impl LogicalTaskId {
    /// Creates one stable logical identity.
    #[must_use]
    pub const fn new(value: u64) -> Self {
        Self(value)
    }

    /// Returns the numeric identity used for deterministic ordering.
    #[must_use]
    pub const fn value(self) -> u64 {
        self.0
    }
}

impl LogicalTaskResult {
    /// Returns the stable logical identity attached to this result.
    #[must_use]
    pub const fn id(&self) -> LogicalTaskId {
        self.id
    }

    /// Returns the underlying independently executed batch result.
    #[must_use]
    pub const fn result(&self) -> &BatchResult {
        &self.result
    }
}

impl ProfileLogicalTask {
    /// Returns the stable logical identity that controls join order.
    #[must_use]
    pub const fn id(&self) -> LogicalTaskId {
        self.id
    }

    /// Creates one owned profile-driven task with explicit logical identity.
    #[must_use]
    pub const fn new(id: LogicalTaskId, request: ProfileBatchRequest) -> Self {
        Self { id, request }
    }
}

impl ProfileLogicalTaskResult {
    /// Returns the stable logical identity attached to this result.
    #[must_use]
    pub const fn id(&self) -> LogicalTaskId {
        self.id
    }

    /// Returns the underlying independently executed profile batch result.
    #[must_use]
    pub const fn result(&self) -> &ProfileBatchResult {
        &self.result
    }
}

/// Executes independent logical tasks sequentially in ascending task-ID order.
///
/// This is the semantic baseline for logical host concurrency. Physical input
/// order does not affect result or join ordering.
///
/// # Errors
///
/// Returns [`LogicalConcurrencyError::DuplicateTaskId`] before execution when
/// logical identity is ambiguous.
pub fn execute_logical_tasks(
    tasks: Vec<LogicalTask>,
) -> Result<Vec<LogicalTaskResult>, LogicalConcurrencyError> {
    let plan = logical_plan(tasks)?;
    Ok(tag_results(plan.ids, execute_batch(plan.requests)))
}

/// Executes independent logical tasks on explicit host workers.
///
/// Tasks are sorted by logical identity before the batch scheduler sees them,
/// and results are tagged in that same order. Host completion order therefore
/// cannot affect observable task ordering or deterministic joins.
///
/// # Errors
///
/// Returns duplicate-identity failure before execution, or propagates typed
/// batch scheduler failures such as zero workers or worker panic.
pub fn execute_logical_tasks_parallel(
    tasks: Vec<LogicalTask>,
    worker_count: usize,
) -> Result<Vec<LogicalTaskResult>, LogicalConcurrencyError> {
    let plan = logical_plan(tasks)?;
    let results = execute_batch_parallel(plan.requests, worker_count)?;
    Ok(tag_results(plan.ids, results))
}

/// Executes independent profile tasks in ascending logical-ID order.
///
/// # Errors
///
/// Returns duplicate-identity failure before profile batch execution.
pub fn execute_profile_logical_tasks(
    tasks: Vec<ProfileLogicalTask>,
) -> Result<Vec<ProfileLogicalTaskResult>, LogicalConcurrencyError> {
    let plan = profile_logical_plan(tasks)?;
    Ok(tag_profile_results(
        plan.ids,
        execute_profile_batch(plan.requests),
    ))
}

/// Executes independent profile tasks on explicit host workers.
///
/// # Errors
///
/// Returns duplicate-identity failure before scheduling, or the shared typed
/// batch scheduler failure.
pub fn execute_profile_logical_tasks_parallel(
    tasks: Vec<ProfileLogicalTask>,
    worker_count: usize,
) -> Result<Vec<ProfileLogicalTaskResult>, LogicalConcurrencyError> {
    let plan = profile_logical_plan(tasks)?;
    let results = execute_profile_batch_parallel(plan.requests, worker_count)?;
    Ok(tag_profile_results(plan.ids, results))
}

/// Serializes committed task outputs in strict ascending logical order.
///
/// The join is host-side artifact construction only. It does not merge guest
/// memory or create guest-visible shared state.
///
/// # Errors
///
/// Returns [`LogicalJoinError::OutOfOrder`] for a reordered/duplicated result
/// sequence, or [`LogicalJoinError::RejectedTask`] for the first rejected task
/// in logical order.
pub fn join_logical_outputs(
    results: &[LogicalTaskResult],
) -> Result<Vec<u8>, LogicalJoinError> {
    let mut joined = Vec::new();
    let mut previous = None;
    for item in results {
        if let Some(previous_id) = previous
            && item.id <= previous_id
        {
            return Err(LogicalJoinError::OutOfOrder {
                current: item.id,
                previous: previous_id,
            });
        }
        previous = Some(item.id);
        match &item.result {
            BatchResult::Completed { machine, .. } => {
                joined.extend_from_slice(machine.output());
            },
            BatchResult::Rejected { error, .. } => {
                return Err(LogicalJoinError::RejectedTask {
                    error: *error,
                    task_id: item.id,
                });
            },
        }
    }
    Ok(joined)
}

/// Serializes committed profile-task outputs in strict logical order.
///
/// Profiles remain attached to their independent machines; this host artifact
/// join concatenates only already committed output bytes.
///
/// # Errors
///
/// Returns order failure for reordered/duplicate results, or the first profile
/// task rejection in logical order.
pub fn join_profile_logical_outputs(
    results: &[ProfileLogicalTaskResult],
) -> Result<Vec<u8>, ProfileLogicalJoinError> {
    let mut joined = Vec::new();
    let mut previous = None;
    for item in results {
        if let Some(previous_id) = previous
            && item.id <= previous_id
        {
            return Err(ProfileLogicalJoinError::OutOfOrder {
                current: item.id,
                previous: previous_id,
            });
        }
        previous = Some(item.id);
        match &item.result {
            ProfileBatchResult::Completed { machine, .. } => {
                joined.extend_from_slice(machine.output());
            },
            ProfileBatchResult::Rejected { error, .. } => {
                return Err(ProfileLogicalJoinError::RejectedTask {
                    error: *error,
                    task_id: item.id,
                });
            },
        }
    }
    Ok(joined)
}

fn logical_plan(
    mut tasks: Vec<LogicalTask>,
) -> Result<LogicalPlan, LogicalConcurrencyError> {
    tasks.sort_unstable_by_key(|task| task.id);
    let mut previous = None;
    let mut ids = Vec::with_capacity(tasks.len());
    let mut requests = Vec::with_capacity(tasks.len());
    for task in tasks {
        if previous == Some(task.id) {
            return Err(LogicalConcurrencyError::DuplicateTaskId {
                task_id: task.id,
            });
        }
        previous = Some(task.id);
        ids.push(task.id);
        requests.push(task.request);
    }
    Ok(LogicalPlan { ids, requests })
}

fn profile_logical_plan(
    mut tasks: Vec<ProfileLogicalTask>,
) -> Result<ProfileLogicalPlan, LogicalConcurrencyError> {
    tasks.sort_unstable_by_key(|task| task.id);
    let mut previous = None;
    let mut ids = Vec::with_capacity(tasks.len());
    let mut requests = Vec::with_capacity(tasks.len());
    for task in tasks {
        if previous == Some(task.id) {
            return Err(LogicalConcurrencyError::DuplicateTaskId {
                task_id: task.id,
            });
        }
        previous = Some(task.id);
        ids.push(task.id);
        requests.push(task.request);
    }
    Ok(ProfileLogicalPlan { ids, requests })
}

fn tag_profile_results(
    ids: Vec<LogicalTaskId>,
    results: Vec<ProfileBatchResult>,
) -> Vec<ProfileLogicalTaskResult> {
    ids.into_iter()
        .zip(results)
        .map(|(id, result)| ProfileLogicalTaskResult { id, result })
        .collect()
}

fn tag_results(
    ids: Vec<LogicalTaskId>,
    results: Vec<BatchResult>,
) -> Vec<LogicalTaskResult> {
    ids.into_iter()
        .zip(results)
        .map(|(id, result)| LogicalTaskResult { id, result })
        .collect()
}
