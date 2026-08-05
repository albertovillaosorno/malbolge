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
//   - Logical ordering/join evidence across canonical profile-driven tasks.
// - Must-Not:
//   - Merge guest state or infer artifact order from host completion order.
// - Allows:
//   - Inputs: public profile logical APIs and canonical profile fixtures.
//   - Outputs: exact logical IDs, profile identities, join bytes, typed
//   - failures.
//   - Side effects: test-process host threads and independently owned memory.
// - Split-When:
//   - Split when cross-backend logical tasks require another join artifact
//   - type.
// - Merge-When:
//   - Merge when classic/profile logical result types become width-safe
//   - unified.
// - Summary:
//   - Proves current and transition profiles coexist under deterministic join
//   - order.
// - Description:
//   - Physical order is scrambled while logical IDs control profile-tagged
//   - output.
// - Usage:
//   - Composed by `tests/vm.rs` under the normal Cargo integration test target.
// - Defaults:
//   - Sequential profile logical execution is the deterministic artifact
//   - baseline.
//

//! Deterministic logical ordering for current and transition profile tasks.

use malbolge::{
    LogicalConcurrencyError, LogicalTaskId, ProfileBatchRequest,
    ProfileLoadError, ProfileLogicalJoinError, ProfileLogicalTask,
    ProfileLogicalTaskResult, ProfileMachineError, current_profile,
    execute_profile_logical_tasks, execute_profile_logical_tasks_parallel,
    join_profile_logical_outputs, target_profile,
};

use super::{TestResult, check_equal, normalize_result};

const CURRENT_IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/interpreter-io-roundtrip.malbolge");
const TRANSITION_IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/spec-io-roundtrip.malbolge");
const STEP_BUDGET: usize = 8;
const TRANSITION_ID: &str = "malbolge-2026.1";

fn profile_task(
    id: u64,
    profile: &'static malbolge::ProfileDescriptor,
    source: &[u8],
    input: u8,
) -> ProfileLogicalTask {
    ProfileLogicalTask::new(
        LogicalTaskId::new(id),
        ProfileBatchRequest::from_source(
            profile,
            source.to_vec(),
            vec![input],
            STEP_BUDGET,
        ),
    )
}

fn result_profile_id(item: &ProfileLogicalTaskResult) -> Option<&'static str> {
    item.result()
        .machine()
        .map(|machine| machine.profile().id())
}

fn transition_profile() -> TestResult<&'static malbolge::ProfileDescriptor> {
    target_profile(TRANSITION_ID)
        .ok_or_else(|| String::from("missing transition profile"))
}

#[test]
fn mixed_profiles_keep_identity_under_parallel_logical_join() -> TestResult {
    let transition = transition_profile()?;
    let tasks = vec![
        profile_task(20, current_profile(), CURRENT_IO_ROUNDTRIP, b'B'),
        profile_task(10, transition, TRANSITION_IO_ROUNDTRIP, b'A'),
    ];
    let sequential =
        normalize_result(execute_profile_logical_tasks(tasks.clone()))?;
    let parallel =
        normalize_result(execute_profile_logical_tasks_parallel(tasks, 2))?;
    let sequential_ids: Vec<u64> =
        sequential.iter().map(|item| item.id().value()).collect();
    let parallel_ids: Vec<u64> =
        parallel.iter().map(|item| item.id().value()).collect();
    check_equal(&sequential_ids, &vec![10, 20], "profile logical IDs")?;
    check_equal(
        &parallel_ids,
        &sequential_ids,
        "parallel profile logical IDs",
    )?;
    check_equal(
        &result_profile_id(parallel.first().ok_or_else(|| {
            String::from("missing transition logical result")
        })?),
        &Some(TRANSITION_ID),
        "transition profile identity",
    )?;
    check_equal(
        &result_profile_id(
            parallel.get(1).ok_or_else(|| {
                String::from("missing current logical result")
            })?,
        ),
        &Some(current_profile().id()),
        "current profile identity",
    )?;
    let sequential_join =
        normalize_result(join_profile_logical_outputs(&sequential))?;
    let parallel_join =
        normalize_result(join_profile_logical_outputs(&parallel))?;
    check_equal(&sequential_join, &b"AB".to_vec(), "profile logical join")?;
    check_equal(
        &parallel_join,
        &sequential_join,
        "parallel profile logical join baseline",
    )
}

#[test]
fn profile_duplicate_identity_fails_before_scheduler() -> TestResult {
    let transition = transition_profile()?;
    let tasks = vec![
        profile_task(10, transition, TRANSITION_IO_ROUNDTRIP, b'A'),
        profile_task(10, transition, TRANSITION_IO_ROUNDTRIP, b'B'),
    ];
    let Err(error) = execute_profile_logical_tasks_parallel(tasks, 0) else {
        return Err(String::from("duplicate profile logical ID succeeded"));
    };
    check_equal(
        &error,
        &LogicalConcurrencyError::DuplicateTaskId {
            task_id: LogicalTaskId::new(10),
        },
        "profile duplicate ID precedes worker validation",
    )
}

#[test]
fn profile_rejection_blocks_join_but_not_later_task() -> TestResult {
    let transition = transition_profile()?;
    let tasks = vec![
        profile_task(30, transition, TRANSITION_IO_ROUNDTRIP, b'C'),
        ProfileLogicalTask::new(
            LogicalTaskId::new(20),
            ProfileBatchRequest::from_source(
                transition,
                b"D".to_vec(),
                Vec::new(),
                STEP_BUDGET,
            ),
        ),
        profile_task(10, transition, TRANSITION_IO_ROUNDTRIP, b'A'),
    ];
    let results =
        normalize_result(execute_profile_logical_tasks_parallel(tasks, 3))?;
    let rejected = results
        .get(1)
        .ok_or_else(|| String::from("missing profile rejection"))?;
    let expected_error =
        ProfileMachineError::Load(ProfileLoadError::InsufficientRecurrenceBase);
    check_equal(
        &rejected.result().error(),
        &Some(expected_error),
        "profile logical rejection",
    )?;
    let later_output = results
        .get(2)
        .and_then(|item| item.result().machine())
        .map(|machine| machine.output().to_vec());
    check_equal(
        &later_output,
        &Some(vec![b'C']),
        "later profile task output",
    )?;
    let Err(error) = join_profile_logical_outputs(&results) else {
        return Err(String::from("profile join ignored rejection"));
    };
    check_equal(
        &error,
        &ProfileLogicalJoinError::RejectedTask {
            error: expected_error,
            task_id: LogicalTaskId::new(20),
        },
        "profile join rejection identity",
    )
}

#[test]
fn profile_join_rejects_reordered_results() -> TestResult {
    let transition = transition_profile()?;
    let mut results = normalize_result(execute_profile_logical_tasks(vec![
        profile_task(20, transition, TRANSITION_IO_ROUNDTRIP, b'B'),
        profile_task(10, transition, TRANSITION_IO_ROUNDTRIP, b'A'),
    ]))?;
    results.swap(0, 1);
    let Err(error) = join_profile_logical_outputs(&results) else {
        return Err(String::from("reordered profile results were joined"));
    };
    check_equal(
        &error,
        &ProfileLogicalJoinError::OutOfOrder {
            current: LogicalTaskId::new(10),
            previous: LogicalTaskId::new(20),
        },
        "profile logical join order validation",
    )
}
