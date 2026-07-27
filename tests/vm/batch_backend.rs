// File:
//   - batch_backend.rs
// Path:
//   - tests/vm/batch_backend.rs
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
//   - CPU fallback and checkpoint-preservation evidence for optional batch
//     ports.
// - Must-Not:
//   - Depend on CUDA APIs or treat backend unavailability as guest failure.
// - Allows:
//   - Inputs: public classic/profile backend ports and deterministic fixtures.
//   - Outputs: full-state equality against the sequential safe-Rust baseline.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when concrete accelerator routing needs backend-specific evidence.
// - Merge-When:
//   - Merge when backend fallback becomes part of ordinary batch fixtures.
// - Summary:
//   - Proves neutral backend completion and fallback preserve exact batch
//     state.
// - Description:
//   - Uses CPU-clone backends to exercise the product routing contract itself.
// - Usage:
//   - Composed by `tests/vm.rs` under the normal VM integration target.
// - Defaults:
//   - Safe-Rust sequential results are the expected semantic baseline.
//
// Related documents:
// - docs/technical/runtime/execution/batch-vm-execution.md
// - docs/technical/adr/replaceable-accelerator-and-algorithm-ports.md
//
// Large file:
//   - false
//

//! Hardware-neutral batch backend routing and deterministic CPU fallback tests.

use malbolge::{
    BatchBackendCompletion, BatchBackendRequest, BatchExecutionBackend,
    BatchRequest, BatchResult, ExecutionMachine, ExecutionMode, MachineIoState,
    MachineState, MachineStateError, ProfileBatchBackendCompletion,
    ProfileBatchBackendRequest, ProfileBatchExecutionBackend,
    ProfileBatchRequest, ProfileBatchResult, ProfileMachineState, RunOutcome,
    current_profile, execute_batch, execute_batch_with_backend,
    execute_profile_batch, execute_profile_batch_with_backend,
    historical_profile,
};

use super::{TestResult, check_equal, normalize_result};

const IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/spec-io-roundtrip.malbolge");

#[derive(Debug, Eq, PartialEq)]
struct ClassicSnapshot {
    error: Option<malbolge::ExecutionError>,
    machine: Option<MachineState>,
    outcome: Option<RunOutcome>,
}

#[derive(Debug, Eq, PartialEq)]
struct ProfileSnapshot {
    error: Option<malbolge::ProfileMachineError>,
    machine: Option<ProfileMachineState>,
    outcome: Option<RunOutcome>,
}

struct CpuCloneBackend;

impl BatchExecutionBackend for CpuCloneBackend {
    fn execute(
        &mut self,
        requests: &[BatchBackendRequest<'_>],
    ) -> Option<Vec<Option<BatchBackendCompletion>>> {
        Some(
            requests
                .iter()
                .map(|request| {
                    let mut machine = request.machine().clone();
                    machine.run(request.step_budget()).ok().map(|outcome| {
                        BatchBackendCompletion::new(
                            machine.snapshot_state(),
                            outcome,
                        )
                    })
                })
                .collect(),
        )
    }
}

impl ProfileBatchExecutionBackend for CpuCloneBackend {
    fn execute(
        &mut self,
        requests: &[ProfileBatchBackendRequest<'_>],
    ) -> Option<Vec<Option<ProfileBatchBackendCompletion>>> {
        Some(
            requests
                .iter()
                .map(|request| {
                    let mut machine = request.machine().clone();
                    machine.run(request.step_budget()).ok().map(|outcome| {
                        ProfileBatchBackendCompletion::new(
                            machine.snapshot_state(),
                            outcome,
                        )
                    })
                })
                .collect(),
        )
    }
}

struct UnavailableBackend;

impl BatchExecutionBackend for UnavailableBackend {
    fn execute(
        &mut self,
        _requests: &[BatchBackendRequest<'_>],
    ) -> Option<Vec<Option<BatchBackendCompletion>>> {
        None
    }
}

impl ProfileBatchExecutionBackend for UnavailableBackend {
    fn execute(
        &mut self,
        _requests: &[ProfileBatchBackendRequest<'_>],
    ) -> Option<Vec<Option<ProfileBatchBackendCompletion>>> {
        None
    }
}

struct CountingBackend {
    calls: usize,
}

impl BatchExecutionBackend for CountingBackend {
    fn execute(
        &mut self,
        _requests: &[BatchBackendRequest<'_>],
    ) -> Option<Vec<Option<BatchBackendCompletion>>> {
        self.calls = self.calls.saturating_add(1);
        None
    }
}

impl ProfileBatchExecutionBackend for CountingBackend {
    fn execute(
        &mut self,
        _requests: &[ProfileBatchBackendRequest<'_>],
    ) -> Option<Vec<Option<ProfileBatchBackendCompletion>>> {
        self.calls = self.calls.saturating_add(1);
        None
    }
}

struct MalformedBackend;

impl BatchExecutionBackend for MalformedBackend {
    fn execute(
        &mut self,
        _requests: &[BatchBackendRequest<'_>],
    ) -> Option<Vec<Option<BatchBackendCompletion>>> {
        Some(Vec::new())
    }
}

fn classic_requests() -> TestResult<Vec<BatchRequest>> {
    let mut resumed = normalize_result(ExecutionMachine::from_source(
        IO_ROUNDTRIP,
        vec![0x61],
        ExecutionMode::Specification,
    ))?;
    let _prefix = normalize_result(resumed.run(2))?;
    Ok(vec![
        BatchRequest::from_machine(resumed, 1),
        BatchRequest::from_source(
            b"D".to_vec(),
            Vec::new(),
            ExecutionMode::Specification,
            8,
        ),
        BatchRequest::from_source(
            IO_ROUNDTRIP.to_vec(),
            vec![0x72],
            ExecutionMode::Specification,
            3,
        ),
    ])
}

fn profile_requests() -> Vec<ProfileBatchRequest> {
    vec![
        ProfileBatchRequest::from_source(
            historical_profile(),
            IO_ROUNDTRIP.to_vec(),
            vec![0x41],
            3,
        ),
        ProfileBatchRequest::from_source(
            historical_profile(),
            b"D".to_vec(),
            Vec::new(),
            8,
        ),
    ]
}

fn classic_snapshots(results: &[BatchResult]) -> Vec<ClassicSnapshot> {
    results
        .iter()
        .map(|result| ClassicSnapshot {
            error: result.error(),
            machine: result.machine().map(ExecutionMachine::snapshot_state),
            outcome: result.outcome(),
        })
        .collect()
}

fn profile_snapshots(results: &[ProfileBatchResult]) -> Vec<ProfileSnapshot> {
    results
        .iter()
        .map(|result| ProfileSnapshot {
            error: result.error(),
            machine: result
                .machine()
                .map(malbolge::ProfileMachine::snapshot_state),
            outcome: result.outcome(),
        })
        .collect()
}

#[test]
fn classic_checkpoint_rejects_cursor_beyond_input() -> TestResult {
    let observed = MachineIoState::new(vec![0x11], 2, Vec::new(), None);
    check_equal(
        &observed.map(|_state| ()),
        &Err(MachineStateError::InputCursorOutOfRange {
            input_len: 1,
            observed: 2,
        }),
        "classic checkpoint input cursor rejection",
    )
}

#[test]
fn classic_backend_route_matches_sequential_complete_state() -> TestResult {
    let requests = classic_requests()?;
    let expected = classic_snapshots(&execute_batch(requests.clone()));
    let mut backend = CpuCloneBackend;
    let observed =
        classic_snapshots(&execute_batch_with_backend(requests, &mut backend));
    check_equal(&observed, &expected, "classic backend complete state")
}

#[test]
fn unavailable_and_malformed_classic_backends_fall_back_exactly() -> TestResult
{
    let requests = classic_requests()?;
    let expected = classic_snapshots(&execute_batch(requests.clone()));
    let mut unavailable = UnavailableBackend;
    let unavailable_results = classic_snapshots(&execute_batch_with_backend(
        requests.clone(),
        &mut unavailable,
    ));
    check_equal(
        &unavailable_results,
        &expected,
        "unavailable backend CPU fallback",
    )?;
    let mut malformed = MalformedBackend;
    let malformed_results = classic_snapshots(&execute_batch_with_backend(
        requests,
        &mut malformed,
    ));
    check_equal(
        &malformed_results,
        &expected,
        "malformed backend CPU fallback",
    )
}

#[test]
fn rejected_only_batches_never_invoke_optional_backend() -> TestResult {
    let mut classic_backend = CountingBackend { calls: 0 };
    let classic = execute_batch_with_backend(
        vec![BatchRequest::from_source(
            b"D".to_vec(),
            Vec::new(),
            ExecutionMode::Specification,
            8,
        )],
        &mut classic_backend,
    );
    check_equal(&classic_backend.calls, &0usize, "classic backend calls")?;
    check_equal(
        &classic.first().and_then(BatchResult::error).is_some(),
        &true,
        "classic rejected-only result",
    )?;

    let mut profile_backend = CountingBackend { calls: 0 };
    let profile = execute_profile_batch_with_backend(
        vec![ProfileBatchRequest::from_source(
            current_profile(),
            b"D".to_vec(),
            Vec::new(),
            8,
        )],
        &mut profile_backend,
    );
    check_equal(&profile_backend.calls, &0usize, "profile backend calls")?;
    check_equal(
        &profile
            .first()
            .and_then(ProfileBatchResult::error)
            .is_some(),
        &true,
        "profile rejected-only result",
    )
}

#[test]
fn profile_backend_route_and_unavailability_match_sequential_state()
-> TestResult {
    let requests = profile_requests();
    let expected = profile_snapshots(&execute_profile_batch(requests.clone()));
    let mut backend = CpuCloneBackend;
    let observed = profile_snapshots(&execute_profile_batch_with_backend(
        requests.clone(),
        &mut backend,
    ));
    check_equal(&observed, &expected, "profile backend complete state")?;
    let mut unavailable = UnavailableBackend;
    let fallback = profile_snapshots(&execute_profile_batch_with_backend(
        requests,
        &mut unavailable,
    ));
    check_equal(&fallback, &expected, "profile backend CPU fallback")
}

#[test]
fn profile_backend_views_retain_canonical_profile_identity() -> TestResult {
    let request = ProfileBatchRequest::from_source(
        current_profile(),
        IO_ROUNDTRIP.to_vec(),
        vec![0x33],
        0,
    );
    let mut backend = CpuCloneBackend;
    let results =
        execute_profile_batch_with_backend(vec![request], &mut backend);
    let profile = results
        .first()
        .and_then(ProfileBatchResult::machine)
        .map(malbolge::ProfileMachine::profile);
    check_equal(
        &profile,
        &Some(current_profile()),
        "current backend profile",
    )
}
