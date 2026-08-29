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
//   - CPU fallback and checkpoint-preservation evidence for optional batch
//   - ports.
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
//   - state.
// - Description:
//   - Uses CPU-clone backends to exercise the product routing contract itself.
// - Usage:
//   - Composed by `tests/vm.rs` under the normal VM integration target.
// - Defaults:
//   - Safe-Rust sequential results are the expected semantic baseline.
//

//! Hardware-neutral batch backend routing and deterministic CPU fallback tests.

use malbolge::{
    BatchBackendCompletion, BatchBackendRequest, BatchExecutionBackend,
    BatchExecutionOrigin, BatchRequest, BatchResult, ExecutionMachine,
    ExecutionMode, MachineIoState, MachineState, MachineStateError,
    ProfileBatchBackendCompletion, ProfileBatchBackendRequest,
    ProfileBatchExecutionBackend, ProfileBatchRequest, ProfileBatchResult,
    ProfileMachine, ProfileMachineError, ProfileMachineState,
    ProfileResidentWireResult, RunOutcome, current_profile, execute_batch,
    execute_batch_with_backend_report, execute_profile_batch,
    execute_profile_batch_with_backend,
    execute_profile_batch_with_backend_report, historical_profile,
    profile_backend_completion_from_resident_wire,
    verify_initial_halt_profile_width,
    verify_minimum_initial_halt_profile_width,
    verify_minimum_input_output_halt_profile_width,
    verify_minimum_input_then_halt_profile_width,
};

use super::{TestResult, check_equal, normalize_result};

const INTERPRETER_IO_ROUNDTRIP: &[u8] = include_bytes!(concat!(
    "../compatibility/specification/",
    "interpreter-io-roundtrip.malbolge",
));
const HISTORICAL_OVERSIZED_WORDS: usize = 59_050;
const PROFILE_CAPACITY_CODE: &str = "MALBOLGE-PROFILE-002";

const SPECIFICATION_IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/spec-io-roundtrip.malbolge");

#[derive(Debug, Eq, PartialEq)]
struct ClassicSnapshot {
    error: Option<malbolge::ExecutionError>,
    machine: Option<MachineState>,
    outcome: Option<RunOutcome>,
}

#[derive(Debug, Eq, PartialEq)]
struct ProfileSnapshot {
    error: Option<ProfileMachineError>,
    machine: Option<ProfileMachineState>,
    outcome: Option<RunOutcome>,
}

struct CpuCloneBackend;

struct ProfileCompletionBackend {
    completion: Option<ProfileBatchBackendCompletion>,
}

#[derive(Debug, Eq, PartialEq)]
struct ProfileResidentGeometrySnapshot {
    eof_word: u32,
    input_instruction: u8,
    memory_words: u32,
    output_instruction: u8,
    word_modulus: u32,
    word_trits: u8,
}

struct ProfileResidentGeometryProbe {
    observed: Vec<ProfileResidentGeometrySnapshot>,
}

struct ProfileResidentWireCompletionBackend {
    error: u32,
    status: u32,
    termination: u32,
}

impl ProfileBatchExecutionBackend for ProfileResidentGeometryProbe {
    fn execute(
        &mut self,
        requests: &[ProfileBatchBackendRequest<'_>],
    ) -> Option<Vec<Option<ProfileBatchBackendCompletion>>> {
        self.observed = requests
            .iter()
            .map(|request| ProfileResidentGeometrySnapshot {
                eof_word: request.eof_word(),
                input_instruction: request.input_instruction(),
                memory_words: request.memory_words(),
                output_instruction: request.output_instruction(),
                word_modulus: request.word_modulus(),
                word_trits: request.word_trits(),
            })
            .collect();
        None
    }
}

impl ProfileBatchExecutionBackend for ProfileCompletionBackend {
    fn execute(
        &mut self,
        requests: &[ProfileBatchBackendRequest<'_>],
    ) -> Option<Vec<Option<ProfileBatchBackendCompletion>>> {
        Some(
            requests
                .iter()
                .map(|_request| self.completion.clone())
                .collect(),
        )
    }
}

impl ProfileBatchExecutionBackend for ProfileResidentWireCompletionBackend {
    fn execute(
        &mut self,
        requests: &[ProfileBatchBackendRequest<'_>],
    ) -> Option<Vec<Option<ProfileBatchBackendCompletion>>> {
        Some(
            requests
                .iter()
                .map(|request| {
                    let machine = request.machine();
                    let registers = machine.registers();
                    profile_backend_completion_from_resident_wire(
                        request,
                        ProfileResidentWireResult {
                            accumulator: registers.accumulator,
                            code_pointer: registers.code_pointer,
                            data_pointer: registers.data_pointer,
                            error: self.error,
                            error_pointer: 0,
                            error_value: 0,
                            input_consumed: u32::try_from(
                                machine.input_consumed(),
                            )
                            .ok()
                            .unwrap_or(u32::MAX),
                            memory: machine.memory().to_vec(),
                            output: machine.output().to_vec(),
                            status: self.status,
                            steps: 0,
                            termination: self.termination,
                        },
                    )
                })
                .collect(),
        )
    }
}

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
        SPECIFICATION_IO_ROUNDTRIP,
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
            SPECIFICATION_IO_ROUNDTRIP.to_vec(),
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
            INTERPRETER_IO_ROUNDTRIP.to_vec(),
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
            machine: result.machine().map(ProfileMachine::snapshot_state),
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
    let (results, report) =
        execute_batch_with_backend_report(requests, &mut backend);
    let observed = classic_snapshots(&results);
    check_equal(&observed, &expected, "classic backend complete state")?;
    let expected_origins: &[BatchExecutionOrigin] = &[
        BatchExecutionOrigin::Backend,
        BatchExecutionOrigin::SafeRustAdmissionRejection,
        BatchExecutionOrigin::Backend,
    ];
    check_equal(
        &report.origins(),
        &expected_origins,
        "classic backend origin report",
    )?;
    check_equal(&report.backend_count(), &2usize, "classic backend count")?;
    check_equal(&report.fallback_count(), &0usize, "classic fallback count")?;
    check_equal(
        &report.admission_rejection_count(),
        &1usize,
        "classic admission rejection count",
    )
}

#[test]
fn unavailable_and_malformed_classic_backends_fall_back_exactly() -> TestResult
{
    let requests = classic_requests()?;
    let expected = classic_snapshots(&execute_batch(requests.clone()));
    let mut unavailable = UnavailableBackend;
    let (unavailable_items, unavailable_report) =
        execute_batch_with_backend_report(requests.clone(), &mut unavailable);
    let unavailable_results = classic_snapshots(&unavailable_items);
    check_equal(
        &unavailable_results,
        &expected,
        "unavailable backend CPU fallback",
    )?;
    let expected_fallback_origins: &[BatchExecutionOrigin] = &[
        BatchExecutionOrigin::SafeRustFallback,
        BatchExecutionOrigin::SafeRustAdmissionRejection,
        BatchExecutionOrigin::SafeRustFallback,
    ];
    check_equal(
        &unavailable_report.origins(),
        &expected_fallback_origins,
        "unavailable backend origins",
    )?;
    let mut malformed = MalformedBackend;
    let (malformed_items, malformed_report) =
        execute_batch_with_backend_report(requests, &mut malformed);
    let malformed_results = classic_snapshots(&malformed_items);
    check_equal(
        &malformed_results,
        &expected,
        "malformed backend CPU fallback",
    )?;
    check_equal(
        &malformed_report.origins(),
        &unavailable_report.origins(),
        "malformed backend origins match full fallback",
    )
}

#[test]
fn rejected_only_batches_never_invoke_optional_backend() -> TestResult {
    let mut classic_backend = CountingBackend { calls: 0 };
    let (classic, classic_report) = execute_batch_with_backend_report(
        vec![BatchRequest::from_source(
            b"D".to_vec(),
            Vec::new(),
            ExecutionMode::Specification,
            8,
        )],
        &mut classic_backend,
    );
    check_equal(&classic_backend.calls, &0usize, "classic backend calls")?;
    let admission_only: &[BatchExecutionOrigin] =
        &[BatchExecutionOrigin::SafeRustAdmissionRejection];
    check_equal(
        &classic_report.origins(),
        &admission_only,
        "classic rejected-only origin",
    )?;
    check_equal(
        &classic.first().and_then(BatchResult::error).is_some(),
        &true,
        "classic rejected-only result",
    )?;

    let mut profile_backend = CountingBackend { calls: 0 };
    let (profile, profile_report) = execute_profile_batch_with_backend_report(
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
        &profile_report.origins(),
        &admission_only,
        "profile rejected-only origin",
    )?;
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
fn profile_capacity_rejection_never_reaches_optional_backend() -> TestResult {
    let mut backend = CountingBackend { calls: 0 };
    let (results, report) = execute_profile_batch_with_backend_report(
        vec![ProfileBatchRequest::from_source(
            historical_profile(),
            vec![b'!'; HISTORICAL_OVERSIZED_WORDS],
            Vec::new(),
            1,
        )],
        &mut backend,
    );
    check_equal(&backend.calls, &0usize, "profile capacity backend calls")?;
    let admission_only: &[BatchExecutionOrigin] =
        &[BatchExecutionOrigin::SafeRustAdmissionRejection];
    check_equal(
        &report.origins(),
        &admission_only,
        "profile capacity rejected-only origin",
    )?;
    let error = results
        .first()
        .and_then(ProfileBatchResult::error)
        .ok_or_else(|| String::from("profile capacity rejection lost error"))?;
    let ProfileMachineError::Profile(requirement) = error else {
        return Err(format!(
            "profile capacity rejection changed category: {error}"
        ));
    };
    check_equal(
        &requirement.code(),
        &PROFILE_CAPACITY_CODE,
        "profile capacity backend diagnostic",
    )
}

#[test]
fn profile_backend_route_and_unavailability_match_sequential_state()
-> TestResult {
    let requests = profile_requests();
    let expected = profile_snapshots(&execute_profile_batch(requests.clone()));
    let mut backend = CpuCloneBackend;
    let (observed_items, observed_report) =
        execute_profile_batch_with_backend_report(
            requests.clone(),
            &mut backend,
        );
    let observed = profile_snapshots(&observed_items);
    check_equal(&observed, &expected, "profile backend complete state")?;
    let expected_profile_origins: &[BatchExecutionOrigin] = &[
        BatchExecutionOrigin::Backend,
        BatchExecutionOrigin::SafeRustAdmissionRejection,
    ];
    check_equal(
        &observed_report.origins(),
        &expected_profile_origins,
        "profile backend origins",
    )?;
    let mut unavailable = UnavailableBackend;
    let (fallback_items, fallback_report) =
        execute_profile_batch_with_backend_report(requests, &mut unavailable);
    let fallback = profile_snapshots(&fallback_items);
    check_equal(&fallback, &expected, "profile backend CPU fallback")?;
    let expected_profile_fallback: &[BatchExecutionOrigin] = &[
        BatchExecutionOrigin::SafeRustFallback,
        BatchExecutionOrigin::SafeRustAdmissionRejection,
    ];
    check_equal(
        &fallback_report.origins(),
        &expected_profile_fallback,
        "profile fallback origins",
    )
}

#[test]
fn profile_backend_request_exposes_every_admitted_resident_geometry()
-> TestResult {
    let checked = [
        (10u8, 59_049u32),
        (11, 177_147),
        (12, 531_441),
        (13, 1_594_323),
        (14, 4_782_969),
        (15, 14_348_907),
    ];
    let mut requests = Vec::with_capacity(checked.len());
    let mut expected = Vec::with_capacity(checked.len());
    for (word_trits, memory_words) in checked {
        let verified = normalize_result(verify_initial_halt_profile_width(
            current_profile(),
            b"QP",
            word_trits,
        ))?;
        let machine = normalize_result(ProfileMachine::from_verified_source(
            &verified,
            Vec::new(),
        ))?;
        requests.push(ProfileBatchRequest::from_machine(machine, 0));
        expected.push(ProfileResidentGeometrySnapshot {
            eof_word: memory_words.saturating_sub(1),
            input_instruction: b'/',
            memory_words,
            output_instruction: b'<',
            word_modulus: memory_words,
            word_trits,
        });
    }
    let mut backend = ProfileResidentGeometryProbe { observed: Vec::new() };
    let (_results, report) =
        execute_profile_batch_with_backend_report(requests, &mut backend);
    check_equal(&backend.observed, &expected, "backend resident geometries")?;
    check_equal(
        &report.fallback_count(),
        &checked.len(),
        "geometry probe fallback count",
    )
}

#[test]
fn profile_backend_rejects_same_profile_with_different_geometry() -> TestResult
{
    let verified = normalize_result(
        verify_minimum_initial_halt_profile_width(current_profile(), b"QP"),
    )?;
    let derived = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    let canonical = normalize_result(ProfileMachine::from_source(
        current_profile(),
        b"QP",
        Vec::new(),
    ))?;
    let completion = ProfileBatchBackendCompletion::new(
        canonical.snapshot_state(),
        RunOutcome::BudgetExhausted { steps: 0 },
    );
    let mut backend = ProfileCompletionBackend {
        completion: Some(completion),
    };
    let request = ProfileBatchRequest::from_machine(derived, 0);
    let (results, report) =
        execute_profile_batch_with_backend_report(vec![request], &mut backend);
    let result = results
        .first()
        .and_then(ProfileBatchResult::machine)
        .ok_or_else(|| String::from("derived fallback machine missing"))?;
    let expected_origins: &[BatchExecutionOrigin] =
        &[BatchExecutionOrigin::SafeRustFallback];
    check_equal(
        &report.origins(),
        &expected_origins,
        "geometry mismatch fallback origin",
    )?;
    check_equal(
        &result.geometry(),
        &verified.geometry(),
        "derived fallback geometry",
    )?;
    check_equal(
        &result.memory().len(),
        &59_049usize,
        "derived fallback memory length",
    )
}

#[test]
fn profile_backend_rejects_same_numeric_geometry_with_different_authority()
-> TestResult {
    let any_input = normalize_result(
        verify_minimum_input_then_halt_profile_width(current_profile(), b"uP"),
    )?;
    let nonempty_input =
        normalize_result(verify_minimum_input_output_halt_profile_width(
            current_profile(),
            b"ubO",
        ))?;
    check_equal(
        &any_input.word_trits(),
        &nonempty_input.word_trits(),
        "authority fixture word width",
    )?;
    check_equal(
        &any_input.memory_words(),
        &nonempty_input.memory_words(),
        "authority fixture memory words",
    )?;
    check_equal(
        &any_input.profile(),
        &nonempty_input.profile(),
        "authority fixture canonical profile",
    )?;
    if any_input.geometry() == nonempty_input.geometry() {
        return Err(String::from("hidden input authority was erased"));
    }
    let requested = normalize_result(ProfileMachine::from_verified_source(
        &nonempty_input,
        vec![0xa5],
    ))?;
    let weaker = normalize_result(ProfileMachine::from_verified_source(
        &any_input,
        vec![0xa5],
    ))?;
    let completion = ProfileBatchBackendCompletion::new(
        weaker.snapshot_state(),
        RunOutcome::BudgetExhausted { steps: 0 },
    );
    let mut backend = ProfileCompletionBackend {
        completion: Some(completion),
    };
    let request = ProfileBatchRequest::from_machine(requested, 0);
    let (results, report) =
        execute_profile_batch_with_backend_report(vec![request], &mut backend);
    let result = results
        .first()
        .and_then(ProfileBatchResult::machine)
        .ok_or_else(|| String::from("authority fallback machine missing"))?;
    check_equal(
        &report.origins(),
        &(&[BatchExecutionOrigin::SafeRustFallback][..]),
        "authority mismatch fallback origin",
    )?;
    check_equal(
        &result.geometry(),
        &nonempty_input.geometry(),
        "authority-preserving fallback geometry",
    )
}

#[test]
fn profile_resident_wire_completion_preserves_derived_authority() -> TestResult
{
    let verified = normalize_result(
        verify_minimum_initial_halt_profile_width(current_profile(), b"QP"),
    )?;
    let machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    let expected_geometry = machine.geometry();
    let mut backend = ProfileResidentWireCompletionBackend {
        error: 0,
        status: 0,
        termination: 0,
    };
    let request = ProfileBatchRequest::from_machine(machine, 0);
    let (results, report) =
        execute_profile_batch_with_backend_report(vec![request], &mut backend);
    check_equal(
        &report.backend_count(),
        &1usize,
        "resident completion backend count",
    )?;
    check_equal(
        &report.fallback_count(),
        &0usize,
        "resident completion fallback count",
    )?;
    let result = results
        .first()
        .and_then(ProfileBatchResult::machine)
        .ok_or_else(|| String::from("resident completion machine missing"))?;
    check_equal(
        &result.geometry(),
        &expected_geometry,
        "resident completion derived authority",
    )
}

#[test]
fn profile_resident_wire_completion_rejects_malformed_metadata() -> TestResult {
    let profile = current_profile();
    let verified = normalize_result(
        verify_minimum_initial_halt_profile_width(profile, b"QP"),
    )?;
    let machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    let request = ProfileBatchRequest::from_machine(machine, 0);
    let expected = execute_profile_batch(vec![request.clone()]);
    for (status, error, termination) in
        [(99u32, 0u32, 0u32), (0, 1, 0), (0, 0, 99), (2, 1, 0)]
    {
        let mut backend = ProfileResidentWireCompletionBackend {
            error,
            status,
            termination,
        };
        let (observed, report) = execute_profile_batch_with_backend_report(
            vec![request.clone()],
            &mut backend,
        );
        check_equal(
            &report.backend_count(),
            &0usize,
            "malformed resident completion backend count",
        )?;
        check_equal(
            &report.fallback_count(),
            &1usize,
            "malformed resident completion fallback count",
        )?;
        check_equal(
            &profile_snapshots(&observed),
            &profile_snapshots(&expected),
            "malformed resident completion fallback state",
        )?;
    }
    Ok(())
}

#[test]
fn profile_backend_views_retain_canonical_profile_identity() -> TestResult {
    let request = ProfileBatchRequest::from_source(
        current_profile(),
        INTERPRETER_IO_ROUNDTRIP.to_vec(),
        vec![0x33],
        0,
    );
    let mut backend = CpuCloneBackend;
    let results =
        execute_profile_batch_with_backend(vec![request], &mut backend);
    let profile = results
        .first()
        .and_then(ProfileBatchResult::machine)
        .map(ProfileMachine::profile);
    check_equal(
        &profile,
        &Some(current_profile()),
        "current backend profile",
    )
}
