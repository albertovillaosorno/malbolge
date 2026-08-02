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
//   - Ordering, join, failure, and state-equality evidence for logical tasks.
// - Must-Not:
//   - Treat host scheduling as guest semantics or share mutable machine state.
// - Allows:
//   - Inputs: public logical/batch APIs and normative roundtrip source fixture.
//   - Outputs: equality assertions over task order, state, I/O, and
//   - diagnostics.
//   - Side effects: test-process host threads and memory only.
// - Split-When:
//   - Split when another logical artifact join requires independent fixtures.
// - Merge-When:
//   - Merge when batch tests own explicit logical identity and joins directly.
// - Summary:
//   - Proves logical identity dominates physical input and host completion
//   - order.
// - Description:
//   - Compares full machine snapshots and joined output across worker
//   - schedules.
// - Usage:
//   - Composed by `tests/vm.rs` under the normal Cargo integration test target.
// - Defaults:
//   - Sequential logical execution is the semantic and artifact baseline.
//

//! Deterministic logical task ordering, joining, and independence fixtures.

use malbolge::{
    BatchError, BatchRequest, BatchResult, ExecutionError, ExecutionErrorKind,
    ExecutionMachine, ExecutionMode, LoadError, LogicalConcurrencyError,
    LogicalJoinError, LogicalTask, LogicalTaskId, LogicalTaskResult,
    MAX_WORD_VALUE, Registers, RunOutcome, Word, execute_logical_tasks,
    execute_logical_tasks_parallel, join_logical_outputs,
};

use super::{TestResult, check_equal, normalize_result};

const FNV_OFFSET: u64 = 14_695_981_039_346_656_037;
const FNV_PRIME: u64 = 1_099_511_628_211;
const IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/spec-io-roundtrip.malbolge");
const STEP_BUDGET: usize = 16;
const TASK_A: u64 = 10;
const TASK_B: u64 = 20;
const TASK_C: u64 = 30;

#[derive(Debug, Eq, PartialEq)]
struct LogicalSnapshot {
    error: Option<ExecutionError>,
    id: LogicalTaskId,
    input_consumed: Option<usize>,
    memory_hash: Option<u64>,
    outcome: Option<RunOutcome>,
    output: Option<Vec<u8>>,
    registers: Option<Registers>,
}

fn hash_memory(result: &BatchResult) -> TestResult<Option<u64>> {
    let Some(machine) = result.machine() else {
        return Ok(None);
    };
    let mut hash = FNV_OFFSET;
    for raw in 0..=MAX_WORD_VALUE {
        let address = normalize_result(Word::new(raw))?;
        let value = normalize_result(machine.memory_word(address))?;
        for byte in value.value().to_le_bytes() {
            hash = (hash ^ u64::from(byte)).wrapping_mul(FNV_PRIME);
        }
    }
    Ok(Some(hash))
}

fn logical_task(id: u64, input: u8) -> LogicalTask {
    LogicalTask::new(
        LogicalTaskId::new(id),
        BatchRequest::from_source(
            IO_ROUNDTRIP.to_vec(),
            vec![input],
            ExecutionMode::Specification,
            STEP_BUDGET,
        ),
    )
}

fn reordered_tasks() -> Vec<LogicalTask> {
    vec![
        logical_task(TASK_C, b'C'),
        logical_task(TASK_A, b'A'),
        logical_task(TASK_B, b'B'),
    ]
}

fn snapshot(item: &LogicalTaskResult) -> TestResult<LogicalSnapshot> {
    let result = item.result();
    let maybe_machine = result.machine();
    Ok(LogicalSnapshot {
        error: result.error(),
        id: item.id(),
        input_consumed: maybe_machine.map(ExecutionMachine::input_consumed),
        memory_hash: hash_memory(result)?,
        outcome: result.outcome(),
        output: maybe_machine.map(|machine| machine.output().to_vec()),
        registers: maybe_machine.map(ExecutionMachine::registers),
    })
}

fn snapshots(
    results: &[LogicalTaskResult],
) -> TestResult<Vec<LogicalSnapshot>> {
    results.iter().map(snapshot).collect()
}

#[test]
fn duplicate_identity_fails_before_parallel_scheduler() -> TestResult {
    let tasks = vec![logical_task(TASK_A, b'A'), logical_task(TASK_A, b'B')];
    let Err(error) = execute_logical_tasks_parallel(tasks, 0) else {
        return Err(String::from("duplicate logical identity was accepted"));
    };
    check_equal(
        &error,
        &LogicalConcurrencyError::DuplicateTaskId {
            task_id: LogicalTaskId::new(TASK_A),
        },
        "duplicate identity precedes worker validation",
    )
}

#[test]
fn join_rejects_reordered_results() -> TestResult {
    let mut results =
        normalize_result(execute_logical_tasks(reordered_tasks()))?;
    results.swap(0, 1);
    let Err(error) = join_logical_outputs(&results) else {
        return Err(String::from("reordered logical results were joined"));
    };
    check_equal(
        &error,
        &LogicalJoinError::OutOfOrder {
            current: LogicalTaskId::new(TASK_A),
            previous: LogicalTaskId::new(TASK_B),
        },
        "join order validation",
    )
}

#[test]
fn logical_order_controls_join_not_physical_input_order() -> TestResult {
    let results = normalize_result(execute_logical_tasks(reordered_tasks()))?;
    let ids: Vec<u64> = results.iter().map(|item| item.id().value()).collect();
    check_equal(&ids, &vec![TASK_A, TASK_B, TASK_C], "logical result order")?;
    check_equal(
        &normalize_result(join_logical_outputs(&results))?,
        &b"ABC".to_vec(),
        "logical joined output",
    )
}

#[test]
fn parallel_workers_match_sequential_logical_baseline() -> TestResult {
    let baseline_results =
        normalize_result(execute_logical_tasks(reordered_tasks()))?;
    let baseline_snapshots = snapshots(&baseline_results)?;
    let baseline_join =
        normalize_result(join_logical_outputs(&baseline_results))?;
    for workers in [1usize, 2, 8] {
        let parallel = normalize_result(execute_logical_tasks_parallel(
            reordered_tasks(),
            workers,
        ))?;
        check_equal(
            &snapshots(&parallel)?,
            &baseline_snapshots,
            "parallel logical state equals sequential baseline",
        )?;
        check_equal(
            &normalize_result(join_logical_outputs(&parallel))?,
            &baseline_join,
            "parallel logical join equals sequential baseline",
        )?;
    }
    Ok(())
}

#[test]
fn rejected_task_blocks_join_but_not_neighbor_execution() -> TestResult {
    let tasks = vec![
        logical_task(TASK_C, b'C'),
        LogicalTask::new(
            LogicalTaskId::new(TASK_B),
            BatchRequest::from_source(
                b"D".to_vec(),
                Vec::new(),
                ExecutionMode::Specification,
                STEP_BUDGET,
            ),
        ),
        logical_task(TASK_A, b'A'),
    ];
    let results = normalize_result(execute_logical_tasks_parallel(tasks, 3))?;
    let rejected = results
        .get(1)
        .ok_or_else(|| String::from("missing rejected logical task"))?;
    check_equal(
        &rejected.result().error().map(ExecutionError::kind),
        &Some(ExecutionErrorKind::Load(
            LoadError::InsufficientRecurrenceBase,
        )),
        "middle logical task rejection",
    )?;
    let later = results
        .get(2)
        .and_then(|item| item.result().machine())
        .ok_or_else(|| String::from("later logical task did not execute"))?;
    check_equal(later.output(), b"C".as_slice(), "later task output")?;

    let Err(error) = join_logical_outputs(&results) else {
        return Err(String::from("join ignored rejected logical task"));
    };
    check_equal(
        &error,
        &LogicalJoinError::RejectedTask {
            error: rejected
                .result()
                .error()
                .ok_or_else(|| String::from("rejection lost error"))?,
            task_id: LogicalTaskId::new(TASK_B),
        },
        "join reports first rejected task in logical order",
    )
}

#[test]
fn unique_tasks_preserve_zero_worker_scheduler_error() -> TestResult {
    let Err(error) = execute_logical_tasks_parallel(reordered_tasks(), 0)
    else {
        return Err(String::from("zero-worker logical execution succeeded"));
    };
    check_equal(
        &error,
        &LogicalConcurrencyError::Batch(BatchError::ZeroWorkers),
        "logical scheduler preserves batch error",
    )
}
