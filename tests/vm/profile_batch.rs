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
//   - Determinism/isolation evidence for profile-driven host batch execution.
// - Must-Not:
//   - Treat host worker scheduling as guest semantics or drop profile identity.
// - Allows:
//   - Inputs: public profile batch APIs and canonical profile/source fixtures.
//   - Outputs: sequential/parallel equality over state, errors, I/O, profiles.
//   - Side effects: test-process host threads and independently owned memory.
// - Split-When:
//   - Split when accelerator profile batches require independent lifecycle
//   - tests.
// - Merge-When:
//   - Merge when classic/profile batch result types become width-safe unified
//   - API.
// - Summary:
//   - Proves current-profile batch execution preserves deterministic input
//   - order.
// - Description:
//   - Compares sampled full-profile state while sharing the classic host
//   - scheduler.
// - Usage:
//   - Composed by `tests/vm.rs` under the normal Cargo integration test target.
// - Defaults:
//   - Sequential profile batches are the baseline for host-parallel execution.
//

//! Current-profile batch scheduling and per-request isolation fixtures.

use malbolge::{
    BatchError, ProfileBatchRequest, ProfileBatchResult, ProfileLoadError,
    ProfileMachine, ProfileMachineError, ProfileRegisters, RunOutcome,
    current_profile, execute_profile_batch, execute_profile_batch_parallel,
    historical_profile,
};

use super::{TestResult, check_equal, normalize_result};

const IO_ROUNDTRIP: &[u8] = include_bytes!(concat!(
    "../compatibility/specification/",
    "interpreter-io-roundtrip.malbolge",
));
const STEP_BUDGET: usize = 8;
const HISTORICAL_OVERSIZED_WORDS: usize = 59_050;
const HISTORICAL_OVERSIZED_MEMORY_WORDS: u64 = 59_050;
const PROFILE_CAPACITY_CODE: &str = "MALBOLGE-PROFILE-002";

type MemorySamples = Vec<(u32, u32)>;

#[derive(Debug, Eq, PartialEq)]
struct ProfileBatchSnapshot {
    error: Option<ProfileMachineError>,
    input_consumed: Option<usize>,
    memory_samples: Option<MemorySamples>,
    outcome: Option<RunOutcome>,
    output: Option<Vec<u8>>,
    profile_id: Option<&'static str>,
    registers: Option<ProfileRegisters>,
}

fn current_requests() -> Vec<ProfileBatchRequest> {
    vec![
        ProfileBatchRequest::from_source(
            current_profile(),
            IO_ROUNDTRIP.to_vec(),
            vec![b'A'],
            STEP_BUDGET,
        ),
        ProfileBatchRequest::from_source(
            current_profile(),
            b"D".to_vec(),
            Vec::new(),
            STEP_BUDGET,
        ),
        ProfileBatchRequest::from_source(
            current_profile(),
            IO_ROUNDTRIP.to_vec(),
            vec![b'B'],
            STEP_BUDGET,
        ),
        ProfileBatchRequest::from_source(
            current_profile(),
            b"D".to_vec(),
            Vec::new(),
            STEP_BUDGET,
        ),
    ]
}

fn sample_memory(machine: &ProfileMachine) -> TestResult<MemorySamples> {
    let maximum = machine.profile().memory_words().saturating_sub(1);
    let addresses = [0u32, 1, 2, 59_049, maximum];
    addresses
        .into_iter()
        .map(|address| {
            normalize_result(machine.memory_word(address))
                .map(|value| (address, value))
        })
        .collect()
}

fn snapshot(result: &ProfileBatchResult) -> TestResult<ProfileBatchSnapshot> {
    let machine = result.machine();
    Ok(ProfileBatchSnapshot {
        error: result.error(),
        input_consumed: machine.map(ProfileMachine::input_consumed),
        memory_samples: match machine {
            Some(value) => Some(sample_memory(value)?),
            None => None,
        },
        outcome: result.outcome(),
        output: machine.map(|value| value.output().to_vec()),
        profile_id: machine.map(|value| value.profile().id()),
        registers: machine.map(ProfileMachine::registers),
    })
}

fn snapshots(
    results: &[ProfileBatchResult],
) -> TestResult<Vec<ProfileBatchSnapshot>> {
    results.iter().map(snapshot).collect()
}

#[test]
fn current_profile_batch_parallel_matches_sequential_baseline() -> TestResult {
    let requests = current_requests();
    let sequential = snapshots(&execute_profile_batch(requests.clone()))?;
    let parallel =
        normalize_result(execute_profile_batch_parallel(requests, 2))?;
    let parallel_snapshots = snapshots(&parallel)?;
    check_equal(
        &parallel_snapshots,
        &sequential,
        "current profile parallel batch baseline",
    )?;
    check_equal(
        &parallel
            .first()
            .and_then(ProfileBatchResult::machine)
            .map(|machine| machine.output().to_vec()),
        &Some(vec![b'A']),
        "current first output",
    )?;
    check_equal(
        &parallel
            .get(2)
            .and_then(ProfileBatchResult::machine)
            .map(|machine| machine.output().to_vec()),
        &Some(vec![b'B']),
        "current later output",
    )?;
    check_equal(
        &parallel.get(1).and_then(ProfileBatchResult::error),
        &Some(ProfileMachineError::Load(
            ProfileLoadError::InsufficientRecurrenceBase,
        )),
        "current middle load rejection",
    )
}

#[test]
fn historical_capacity_rejection_matches_parallel_batch() -> TestResult {
    let request = ProfileBatchRequest::from_source(
        historical_profile(),
        vec![b'!'; HISTORICAL_OVERSIZED_WORDS],
        Vec::new(),
        STEP_BUDGET,
    );
    let sequential = execute_profile_batch(vec![request.clone()]);
    let parallel =
        normalize_result(execute_profile_batch_parallel(vec![request], 2))?;
    let sequential_error = sequential
        .first()
        .and_then(ProfileBatchResult::error)
        .ok_or_else(|| String::from("missing sequential capacity rejection"))?;
    let parallel_error = parallel
        .first()
        .and_then(ProfileBatchResult::error)
        .ok_or_else(|| {
        String::from("missing parallel capacity rejection")
    })?;
    check_equal(
        &parallel_error,
        &sequential_error,
        "parallel profile capacity rejection",
    )?;
    let ProfileMachineError::Profile(requirement) = sequential_error else {
        return Err(format!(
            "profile batch capacity changed category: {sequential_error}"
        ));
    };
    check_equal(
        &requirement.code(),
        &PROFILE_CAPACITY_CODE,
        "profile batch capacity diagnostic",
    )?;
    check_equal(
        &requirement.required_memory_words(),
        &HISTORICAL_OVERSIZED_MEMORY_WORDS,
        "profile batch required memory",
    )
}

#[test]
fn profile_batch_result_can_resume_owned_machine() -> TestResult {
    let request = ProfileBatchRequest::from_source(
        current_profile(),
        IO_ROUNDTRIP.to_vec(),
        vec![b'Q'],
        1,
    );
    let mut results = execute_profile_batch(vec![request]);
    let result = results
        .pop()
        .ok_or_else(|| String::from("profile owned result missing"))?;
    let expected_outcome = result
        .outcome()
        .ok_or_else(|| String::from("profile owned result outcome missing"))?;
    let machine = normalize_result(result.into_machine())?;
    check_equal(
        &machine.profile().fingerprint(),
        &current_profile().fingerprint(),
        "profile owned result identity",
    )?;
    check_equal(
        &expected_outcome,
        &RunOutcome::BudgetExhausted { steps: 1 },
        "profile owned result outcome",
    )?;

    let rejected =
        execute_profile_batch(vec![ProfileBatchRequest::from_source(
            current_profile(),
            b"D".to_vec(),
            Vec::new(),
            1,
        )])
        .pop()
        .ok_or_else(|| String::from("profile rejected owned result missing"))?;
    let Err(error) = rejected.into_machine() else {
        return Err(String::from("profile rejected owned result resumed"));
    };
    check_equal(
        &error,
        &ProfileMachineError::Load(
            ProfileLoadError::InsufficientRecurrenceBase,
        ),
        "profile rejected owned result",
    )
}

#[test]
fn profile_batch_request_identity_is_explicit() -> TestResult {
    let request = ProfileBatchRequest::from_source(
        current_profile(),
        IO_ROUNDTRIP.to_vec(),
        vec![b'Q'],
        19,
    );
    check_equal(
        &request.profile().fingerprint(),
        &current_profile().fingerprint(),
        "profile batch fingerprint",
    )?;
    check_equal(&request.step_budget(), &19usize, "profile batch budget")
}

#[test]
fn profile_parallel_batch_validates_worker_count() -> TestResult {
    let Err(error) = execute_profile_batch_parallel(Vec::new(), 0) else {
        return Err(String::from("zero-worker profile batch succeeded"));
    };
    check_equal(
        &error,
        &BatchError::ZeroWorkers,
        "profile zero workers fail closed",
    )?;
    let empty =
        normalize_result(execute_profile_batch_parallel(Vec::new(), 3))?;
    check_equal(&empty.len(), &0usize, "empty profile batch")
}
