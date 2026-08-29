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
//   - Exact full-state oracle evidence for scalable resident CUDA execution.
// - Must-Not:
//   - Treat CUDA or Python as profile identity or semantic authority.
// - Allows:
//   - Inputs: admitted Rust profile geometry and complete profiled VM states.
//   - Outputs: exact registers, memory, I/O, termination, and error assertions.
//   - Side effects: one optional repository-local Python CUDA worker process.
// - Split-When:
//   - Split when another memory model is admitted beyond single-word modular.
// - Merge-When:
//   - Merge when classic and scalable resident protocols share one Rust client.
// - Summary:
//   - Checks admitted profile resident CUDA runs against normative Rust states.
// - Description:
//   - Compares complete observable state and full memory at canonical or
//   - independently verified derived execution geometry.
// - Usage:
//   - Composed by `tests/vm.rs`; unavailable CUDA remains an optional-path
//   - pass.
// - Defaults:
//   - Safe Rust supplies every oracle; unavailable CUDA remains
//     performance-only.
//

//! Full-state admitted-profile differential checks for resident CUDA execution.

use std::ffi::OsString;
use std::io::{Read as _, Write as _};
use std::path::Path;
use std::process::{Command, Stdio};

use malbolge::{
    DifferentialCandidate, PROFILE_RESIDENT_WIRE_MAGIC,
    ProfileBatchBackendCompletion, ProfileBatchBackendRequest,
    ProfileBatchExecutionBackend, ProfileBatchRequest, ProfileBatchResult,
    ProfileMachine, ProfileMachineError, ProfileRegisters,
    ProfileResidentProcessTransport, ProfileResidentTransportBackend,
    ProfileResidentWireGeometry, ProfileResidentWireResponse,
    ProfileResidentWireResult, StepOutcome, Termination,
    VerifiedProfileExecutionGeometry, current_profile,
    decode_profile_instruction, decode_profile_resident_response,
    encode_profile_resident_batch, execute_profile_batch,
    execute_profile_batch_with_backend_report, verify_differential_candidates,
    verify_initial_halt_profile_width, verify_input_then_halt_profile_width,
    verify_jump_code_halt_profile_width,
    verify_jump_code_io_halt_profile_width,
    verify_jump_code_rotate_halt_profile_width,
    verify_jump_crazy_halt_profile_width,
    verify_jump_crazy_io_halt_profile_width,
    verify_jump_rotate_halt_profile_width,
    verify_minimum_initial_halt_profile_width,
    verify_minimum_input_output_halt_profile_width,
    verify_minimum_input_then_halt_profile_width,
    verify_minimum_jump_code_halt_profile_width,
    verify_minimum_jump_code_io_halt_profile_width,
    verify_minimum_jump_code_rotate_halt_profile_width,
    verify_minimum_jump_crazy_halt_profile_width,
    verify_minimum_jump_crazy_io_halt_profile_width,
    verify_minimum_jump_rotate_halt_profile_width,
    verify_minimum_noop_prefix_halt_profile_width,
    verify_minimum_repeated_jump_data_profile_width,
    verify_minimum_straight_line_io_profile_width,
    verify_straight_line_io_profile_width,
};

use crate::{
    TestResult, accelerator_python_path, check_equal, cuda_test_guard,
    normalize_result, validation_python,
};

const RUN_BUDGET_EXHAUSTED: u32 = 0;
const RUN_TERMINATED: u32 = 1;
const RUN_ERROR: u32 = 2;
const ERROR_NONE: u32 = 0;
const ERROR_INVALID_ENCRYPTION: u32 = 1;
const CURRENT_INPUT: u8 = 0xa5;
const CURRENT_SOURCE: &[u8] = b"(=%r_L";
const REJECTING_JUMP_SOURCE: &[u8] = b"b'";
const TABLE_LEN: usize = 94;
const TEST_XLAT1: &[u8; TABLE_LEN] =
    b"+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI\
.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha";

type EncodedProfileProductBatch = (ProfileResidentWireGeometry, Vec<u8>);
type WorkerBatch = Option<Vec<RunSnapshot>>;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct OracleExecution {
    error: u32,
    error_pointer: u32,
    error_value: u32,
    status: u32,
    steps: u32,
}

#[derive(Clone)]
struct RunFixture {
    machine: ProfileMachine,
    step_budget: u32,
}

type RunSnapshot = ProfileResidentWireResult;

struct CudaProfileProductBackend {
    backend: ProfileResidentTransportBackend<ProfileResidentProcessTransport>,
    used_cuda: bool,
}

impl CudaProfileProductBackend {
    fn new() -> TestResult<Self> {
        Ok(Self {
            backend: cuda_profile_process_backend()?,
            used_cuda: false,
        })
    }
}

struct ProfileProductEncodingProbe {
    encoded: Option<EncodedProfileProductBatch>,
    error: Option<String>,
}

impl ProfileBatchExecutionBackend for ProfileProductEncodingProbe {
    fn execute(
        &mut self,
        requests: &[ProfileBatchBackendRequest<'_>],
    ) -> Option<Vec<Option<ProfileBatchBackendCompletion>>> {
        match homogeneous_product_geometry(requests)
            .map(|value| {
                encode_profile_product_batch(requests, value)
                    .map(|bytes| (value, bytes))
            })
            .transpose()
        {
            Ok(encoded) => self.encoded = encoded,
            Err(error) => self.error = Some(error),
        }
        None
    }
}

impl ProfileBatchExecutionBackend for CudaProfileProductBackend {
    fn execute(
        &mut self,
        requests: &[ProfileBatchBackendRequest<'_>],
    ) -> Option<Vec<Option<ProfileBatchBackendCompletion>>> {
        let results = self.backend.execute(requests);
        if results.is_some() {
            self.used_cuda = true;
        }
        results
    }
}

#[test]
fn cuda_resident_current_profile_matches_complete_normative_states()
-> TestResult {
    let fixtures = fixtures()?;
    let request = encode_batch(&fixtures)?;
    let expected = fixtures
        .into_iter()
        .map(oracle_run)
        .collect::<TestResult<Vec<_>>>()?;
    let _cuda_guard = cuda_test_guard()?;
    let Some(observed) =
        run_cuda_worker(request, current_profile().memory_words())?
    else {
        return Ok(());
    };
    compare_batches(&observed, &expected)
}

#[test]
fn cuda_current_profile_routes_through_product_batch_port() -> TestResult {
    let requests = product_profile_requests()?;
    let expected = execute_profile_batch(requests.clone());
    let _cuda_guard = cuda_test_guard()?;
    let mut backend = CudaProfileProductBackend::new()?;
    let (observed, report) =
        execute_profile_batch_with_backend_report(requests, &mut backend);
    if !backend.used_cuda {
        return Ok(());
    }
    if report.backend_count() == 0 {
        return Err(String::from(
            "profile CUDA worker ran but no completion was accepted",
        ));
    }
    compare_profile_product_batch(&observed, &expected)
}

fn check_derived_profile_product_encoding(
    word_trits: u8,
    memory_words: u32,
) -> TestResult {
    let verified = normalize_result(verify_initial_halt_profile_width(
        current_profile(),
        b"QP",
        word_trits,
    ))?;
    let machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    let request = ProfileBatchRequest::from_machine(machine, 1);
    let mut backend = ProfileProductEncodingProbe {
        encoded: None,
        error: None,
    };
    let (_results, report) =
        execute_profile_batch_with_backend_report(vec![request], &mut backend);
    if let Some(error) = backend.error {
        return Err(format!("derived profile encoding probe: {error}"));
    }
    let (geometry, encoded) = backend
        .encoded
        .ok_or_else(|| String::from("derived profile encoding missing"))?;
    check_equal(
        &geometry,
        &ProfileResidentWireGeometry {
            eof_word: memory_words.saturating_sub(1),
            input_instruction: b'/',
            memory_words,
            output_instruction: b'<',
            word_modulus: memory_words,
            word_trits,
        },
        "derived profile wire geometry",
    )?;
    if !encoded.starts_with(&PROFILE_RESIDENT_WIRE_MAGIC) {
        return Err(String::from("derived profile wire magic mismatch"));
    }
    check_equal(
        &report.fallback_count(),
        &1usize,
        "derived encoding probe fallback",
    )
}

#[test]
fn derived_profile_product_encoding_uses_every_admitted_geometry() -> TestResult
{
    for (word_trits, memory_words) in [
        (10u8, 59_049u32),
        (11, 177_147),
        (12, 531_441),
        (13, 1_594_323),
        (14, 4_782_969),
    ] {
        check_derived_profile_product_encoding(word_trits, memory_words)?;
    }
    Ok(())
}

fn reviewed_width_cuda_requests(
    word_trits: u8,
) -> TestResult<Vec<ProfileBatchRequest>> {
    let profile = current_profile();
    let initial = normalize_result(verify_initial_halt_profile_width(
        profile, b"QP", word_trits,
    ))?;
    let input = normalize_result(verify_input_then_halt_profile_width(
        profile, b"uP", word_trits,
    ))?;
    let jump_code_source = source_backed_jump_code_chain()?;
    let jump_code = normalize_result(verify_jump_code_halt_profile_width(
        profile,
        &jump_code_source,
        word_trits,
    ))?;
    let jump_code_io_source = source_backed_jump_code_io_chain()?;
    let jump_code_io =
        normalize_result(verify_jump_code_io_halt_profile_width(
            profile,
            &jump_code_io_source,
            word_trits,
        ))?;
    let jump_code_rotate_source = source_backed_jump_code_rotate_chain()?;
    let jump_code_rotate =
        normalize_result(verify_jump_code_rotate_halt_profile_width(
            profile,
            &jump_code_rotate_source,
            word_trits,
        ))?;
    let straight = normalize_result(verify_straight_line_io_profile_width(
        profile, b"uCar_L", word_trits,
    ))?;
    let crazy = normalize_result(verify_jump_crazy_halt_profile_width(
        profile, b"(=<N", word_trits,
    ))?;
    let recovered = normalize_result(verify_jump_crazy_io_halt_profile_width(
        profile, b"(=<r_L", word_trits,
    ))?;
    let rotate = normalize_result(verify_jump_rotate_halt_profile_width(
        profile, b"(&O", word_trits,
    ))?;
    Ok(vec![
        verified_profile_request(&initial, Vec::new(), 1)?,
        verified_profile_request(&input, Vec::new(), 2)?,
        verified_profile_request(&jump_code, Vec::new(), 5)?,
        verified_profile_request(&jump_code_io, vec![0xa5, 0x3c], 9)?,
        verified_profile_request(&jump_code_rotate, Vec::new(), 6)?,
        verified_profile_request(&straight, vec![0xa5, 0x3c], 6)?,
        verified_profile_request(&crazy, Vec::new(), 4)?,
        verified_profile_request(&recovered, vec![0xa5], 6)?,
        verified_profile_request(&rotate, Vec::new(), 3)?,
    ])
}

#[test]
fn cuda_reviewed_profile_widths_route_through_product_batch_port() -> TestResult
{
    let _cuda_guard = cuda_test_guard()?;
    for word_trits in 10u8..=14 {
        let requests = reviewed_width_cuda_requests(word_trits)?;
        let expected_count = requests.len();
        let expected = execute_profile_batch(requests.clone());
        let mut backend = CudaProfileProductBackend::new()?;
        let (observed, report) =
            execute_profile_batch_with_backend_report(requests, &mut backend);
        if !backend.used_cuda {
            continue;
        }
        check_equal(
            &report.backend_count(),
            &expected_count,
            "reviewed-width CUDA completion",
        )?;
        compare_profile_product_batch(&observed, &expected)?;
    }
    Ok(())
}

#[test]
fn cuda_same_resident_shape_retains_distinct_width_authority() -> TestResult {
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
        "CUDA authority shared word width",
    )?;
    check_equal(
        &any_input.memory_words(),
        &nonempty_input.memory_words(),
        "CUDA authority shared memory words",
    )?;
    if any_input.geometry() == nonempty_input.geometry() {
        return Err(String::from("CUDA authority fixtures lost hidden policy"));
    }
    let any_machine = normalize_result(ProfileMachine::from_verified_source(
        &any_input,
        vec![0xa5],
    ))?;
    let nonempty_machine = normalize_result(
        ProfileMachine::from_verified_source(&nonempty_input, vec![0xa5]),
    )?;
    let requests = vec![
        ProfileBatchRequest::from_machine(any_machine, 2),
        ProfileBatchRequest::from_machine(nonempty_machine, 3),
    ];
    let expected = execute_profile_batch(requests.clone());
    let _cuda_guard = cuda_test_guard()?;
    let mut backend = CudaProfileProductBackend::new()?;
    let (observed, report) =
        execute_profile_batch_with_backend_report(requests, &mut backend);
    if !backend.used_cuda {
        return Ok(());
    }
    check_equal(
        &report.backend_count(),
        &2usize,
        "same-shape CUDA completions",
    )?;
    compare_profile_product_batch(&observed, &expected)
}

fn encoded_profile_instruction(decoded: u8, position: usize) -> TestResult<u8> {
    let pointer = u32::try_from(position)
        .map_err(|error| format!("profile instruction position: {error}"))?;
    (33u8..=126u8)
        .find(|cell| {
            decode_profile_instruction(u32::from(*cell), pointer)
                == Some(decoded)
        })
        .ok_or_else(|| format!("missing encoded {decoded} at {position}"))
}

fn source_backed_jump_code_chain() -> TestResult<Vec<u8>> {
    let first_target = encoded_profile_instruction(b'i', 0)?;
    let mutated_target = encoded_profile_instruction(b'*', 1)?;
    let return_target = encoded_profile_instruction(b'*', 2)?;
    let halt_target = encoded_profile_instruction(b'v', 3)?;
    let second_jump = usize::from(first_target).saturating_add(1);
    let third_jump = usize::from(mutated_target).saturating_add(1);
    let mutated_jump = usize::from(return_target).saturating_add(1);
    let halt_position = usize::from(halt_target).saturating_add(1);
    let source_len = second_jump.saturating_add(1);
    let mut source = Vec::with_capacity(source_len);
    for position in 0..source_len {
        source.push(encoded_profile_instruction(b'o', position)?);
    }
    for (position, value) in [
        (0usize, first_target),
        (1usize, mutated_target),
        (2usize, return_target),
        (3usize, halt_target),
        (
            mutated_jump,
            encoded_profile_instruction(b'j', mutated_jump)?,
        ),
        (third_jump, encoded_profile_instruction(b'i', third_jump)?),
        (
            halt_position,
            encoded_profile_instruction(b'v', halt_position)?,
        ),
        (second_jump, encoded_profile_instruction(b'i', second_jump)?),
    ] {
        let cell = source.get_mut(position).ok_or_else(|| {
            format!("missing shadow jump-code cell {position}")
        })?;
        *cell = value;
    }
    Ok(source)
}

fn source_backed_jump_code_io_chain() -> TestResult<Vec<u8>> {
    let mut source = source_backed_jump_code_chain()?;
    let profile = current_profile();
    for (position, decoded) in [
        (79usize, profile.input_instruction()),
        (80usize, profile.output_instruction()),
        (81usize, profile.input_instruction()),
        (82usize, profile.output_instruction()),
        (83usize, b'v'),
    ] {
        let cell = source.get_mut(position).ok_or_else(|| {
            format!("missing CUDA jump-code I/O cell {position}")
        })?;
        *cell = encoded_profile_instruction(decoded, position)?;
    }
    Ok(source)
}

fn source_backed_jump_code_rotate_chain() -> TestResult<Vec<u8>> {
    let mut source = source_backed_jump_code_chain()?;
    for (position, decoded) in
        [(4usize, b'j'), (79usize, b'*'), (80usize, b'v')]
    {
        let cell = source.get_mut(position).ok_or_else(|| {
            format!("missing CUDA jump-code rotate cell {position}")
        })?;
        *cell = encoded_profile_instruction(decoded, position)?;
    }
    Ok(source)
}

fn verified_profile_request(
    verified: &VerifiedProfileExecutionGeometry,
    input: Vec<u8>,
    step_budget: usize,
) -> TestResult<ProfileBatchRequest> {
    let machine = normalize_result(ProfileMachine::from_verified_source(
        verified, input,
    ))?;
    Ok(ProfileBatchRequest::from_machine(machine, step_budget))
}

fn verified_n10_cuda_requests() -> TestResult<Vec<ProfileBatchRequest>> {
    let profile = current_profile();
    let initial = normalize_result(verify_minimum_initial_halt_profile_width(
        profile, b"QP",
    ))?;
    let noop = normalize_result(
        verify_minimum_noop_prefix_halt_profile_width(profile, b"DP"),
    )?;
    let input = normalize_result(
        verify_minimum_input_then_halt_profile_width(profile, b"uP"),
    )?;
    let jump_code_source = source_backed_jump_code_chain()?;
    let jump_code = normalize_result(
        verify_minimum_jump_code_halt_profile_width(profile, &jump_code_source),
    )?;
    let jump_code_io_source = source_backed_jump_code_io_chain()?;
    let jump_code_io =
        normalize_result(verify_minimum_jump_code_io_halt_profile_width(
            profile,
            &jump_code_io_source,
        ))?;
    let jump_code_rotate_source = source_backed_jump_code_rotate_chain()?;
    let jump_code_rotate =
        normalize_result(verify_minimum_jump_code_rotate_halt_profile_width(
            profile,
            &jump_code_rotate_source,
        ))?;
    let io = normalize_result(verify_minimum_input_output_halt_profile_width(
        profile, b"ubO",
    ))?;
    let straight = normalize_result(
        verify_minimum_straight_line_io_profile_width(profile, b"uCar_L"),
    )?;
    let jumps = normalize_result(
        verify_minimum_repeated_jump_data_profile_width(profile, b"('&N"),
    )?;
    let crazy = normalize_result(
        verify_minimum_jump_crazy_halt_profile_width(profile, b"(=<N"),
    )?;
    let recovered = normalize_result(
        verify_minimum_jump_crazy_io_halt_profile_width(profile, b"(=<r_L"),
    )?;
    let rotate = normalize_result(
        verify_minimum_jump_rotate_halt_profile_width(profile, b"(&O"),
    )?;
    Ok(vec![
        verified_profile_request(&initial, Vec::new(), 1)?,
        verified_profile_request(&noop, Vec::new(), 2)?,
        verified_profile_request(&input, Vec::new(), 2)?,
        verified_profile_request(&jump_code, Vec::new(), 5)?,
        verified_profile_request(&jump_code_io, vec![0xa5, 0x3c], 9)?,
        verified_profile_request(&jump_code_rotate, Vec::new(), 6)?,
        verified_profile_request(&io, vec![0xa5], 3)?,
        verified_profile_request(&straight, vec![0xa5, 0x3c], 6)?,
        verified_profile_request(&jumps, Vec::new(), 4)?,
        verified_profile_request(&crazy, Vec::new(), 4)?,
        verified_profile_request(&recovered, vec![0xa5], 6)?,
        verified_profile_request(&rotate, Vec::new(), 3)?,
    ])
}

#[test]
fn cuda_verified_n10_families_match_safe_rust() -> TestResult {
    let requests = verified_n10_cuda_requests()?;
    let expected_count = requests.len();
    let expected = execute_profile_batch(requests.clone());
    let _cuda_guard = cuda_test_guard()?;
    let mut backend = CudaProfileProductBackend::new()?;
    let (observed, report) =
        execute_profile_batch_with_backend_report(requests, &mut backend);
    if !backend.used_cuda {
        return Ok(());
    }
    check_equal(
        &report.backend_count(),
        &expected_count,
        "verified N10 CUDA completion count",
    )?;
    compare_profile_product_batch(&observed, &expected)
}

#[test]
fn mixed_resident_geometries_fail_closed_before_worker_encoding() -> TestResult
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
    let requests = vec![
        ProfileBatchRequest::from_machine(derived, 0),
        ProfileBatchRequest::from_machine(canonical, 0),
    ];
    let expected = execute_profile_batch(requests.clone());
    let mut backend = ProfileProductEncodingProbe {
        encoded: None,
        error: None,
    };
    let (observed, report) =
        execute_profile_batch_with_backend_report(requests, &mut backend);
    check_equal(&backend.error, &None, "mixed geometry encoding error")?;
    check_equal(&backend.encoded, &None, "mixed geometry encoded payload")?;
    check_equal(
        &report.backend_count(),
        &0usize,
        "mixed geometry backend count",
    )?;
    check_equal(
        &report.fallback_count(),
        &2usize,
        "mixed geometry fallback count",
    )?;
    compare_profile_product_batch(&observed, &expected)
}

fn cuda_profile_process_backend()
-> TestResult<ProfileResidentTransportBackend<ProfileResidentProcessTransport>>
{
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let transport =
        ProfileResidentProcessTransport::new(validation_python(root))
            .argument(OsString::from("-m"))
            .argument(OsString::from("accelerator.cuda.profile_run_worker"))
            .environment(
                OsString::from("PYTHONPATH"),
                accelerator_python_path(root)?,
            )
            .working_directory(root.to_path_buf());
    Ok(ProfileResidentTransportBackend::new(transport))
}

fn product_profile_requests() -> TestResult<Vec<ProfileBatchRequest>> {
    let profile = current_profile();
    let machine = normalize_result(ProfileMachine::from_source(
        profile,
        CURRENT_SOURCE,
        vec![CURRENT_INPUT],
    ))?;
    Ok(vec![
        ProfileBatchRequest::from_machine(machine, 2),
        ProfileBatchRequest::from_source(profile, b"D".to_vec(), Vec::new(), 4),
    ])
}

fn homogeneous_product_geometry(
    requests: &[ProfileBatchBackendRequest<'_>],
) -> Option<ProfileResidentWireGeometry> {
    let first = requests.first()?;
    let geometry = first.resident_wire_request().geometry;
    if requests
        .iter()
        .any(|request| request.resident_wire_request().geometry != geometry)
    {
        return None;
    }
    Some(geometry)
}

fn encode_profile_product_batch(
    requests: &[ProfileBatchBackendRequest<'_>],
    _geometry: ProfileResidentWireGeometry,
) -> TestResult<Vec<u8>> {
    let wire_requests = requests
        .iter()
        .map(ProfileBatchBackendRequest::resident_wire_request)
        .collect::<Vec<_>>();
    encode_profile_resident_batch(&wire_requests)
        .map_err(|error| format!("profile product wire encoding: {error}"))
}

fn compare_profile_product_batch(
    observed: &[ProfileBatchResult],
    expected: &[ProfileBatchResult],
) -> TestResult {
    check_equal(
        &observed.len(),
        &expected.len(),
        "profile product batch length",
    )?;
    for (index, (actual, oracle)) in observed.iter().zip(expected).enumerate() {
        let context =
            |field: &str| format!("profile product case {index} {field}");
        check_equal(&actual.error(), &oracle.error(), &context("error"))?;
        check_equal(&actual.outcome(), &oracle.outcome(), &context("outcome"))?;
        match (actual.machine(), oracle.machine()) {
            (Some(actual_machine), Some(oracle_machine)) => {
                let candidates = [
                    DifferentialCandidate::new(
                        "rust",
                        oracle_machine.snapshot_state(),
                    ),
                    DifferentialCandidate::new(
                        "cuda",
                        actual_machine.snapshot_state(),
                    ),
                ];
                verify_differential_candidates(&candidates).map_err(
                    |error| format!("{}: {error}", context("state")),
                )?;
            },
            (None, None) => {},
            _ => return Err(context("machine presence")),
        }
    }
    Ok(())
}

fn fixtures() -> TestResult<Vec<RunFixture>> {
    let profile = current_profile();
    let source_input = normalize_result(ProfileMachine::from_source(
        profile,
        CURRENT_SOURCE,
        vec![CURRENT_INPUT],
    ))?;
    let source_eof = normalize_result(ProfileMachine::from_source(
        profile,
        CURRENT_SOURCE,
        Vec::new(),
    ))?;
    let rejecting = normalize_result(ProfileMachine::from_source(
        profile,
        REJECTING_JUMP_SOURCE,
        Vec::new(),
    ))?;
    let partial = source_input.clone();
    let mut resumed = source_input.clone();
    let _resume_prefix = normalize_result(resumed.run(2))?;
    let mut terminated = source_input.clone();
    let _terminated_outcome = normalize_result(terminated.run(8))?;
    Ok(vec![
        RunFixture {
            machine: source_input,
            step_budget: 8,
        },
        RunFixture {
            machine: partial,
            step_budget: 2,
        },
        RunFixture {
            machine: resumed,
            step_budget: 8,
        },
        RunFixture {
            machine: source_eof,
            step_budget: 8,
        },
        RunFixture {
            machine: rejecting,
            step_budget: 1,
        },
        RunFixture {
            machine: current_non_graphical()?,
            step_budget: 4,
        },
        RunFixture {
            machine: current_wrap()?,
            step_budget: 1,
        },
        RunFixture {
            machine: terminated,
            step_budget: 100,
        },
    ])
}

fn current_non_graphical() -> TestResult<ProfileMachine> {
    let profile = current_profile();
    let memory_len = usize::try_from(profile.memory_words())
        .map_err(|error| format!("current memory length: {error}"))?;
    normalize_result(ProfileMachine::from_state(
        profile,
        vec![0u32; memory_len],
        Vec::new(),
        ProfileRegisters {
            accumulator: 7,
            code_pointer: 0,
            data_pointer: 1,
        },
    ))
}

fn current_wrap() -> TestResult<ProfileMachine> {
    let profile = current_profile();
    let maximum = profile.memory_words().saturating_sub(1);
    let memory_len = usize::try_from(profile.memory_words())
        .map_err(|error| format!("current memory length: {error}"))?;
    let mut memory = vec![0u32; memory_len];
    let index = usize::try_from(maximum)
        .map_err(|error| format!("current maximum index: {error}"))?;
    let slot = memory
        .get_mut(index)
        .ok_or_else(|| String::from("current maximum memory slot missing"))?;
    *slot = u32::from(noop_cell(maximum)?);
    normalize_result(ProfileMachine::from_state(
        profile,
        memory,
        Vec::new(),
        ProfileRegisters {
            accumulator: 7,
            code_pointer: maximum,
            data_pointer: maximum,
        },
    ))
}

fn noop_cell(pointer: u32) -> TestResult<u8> {
    let table_len = u32::try_from(TABLE_LEN)
        .map_err(|error| format!("decode table length: {error}"))?;
    let phase = usize::try_from(pointer.rem_euclid(table_len))
        .map_err(|error| format!("decode phase: {error}"))?;
    for cell in 33u8..=126u8 {
        let offset = usize::from(cell.saturating_sub(33));
        let index = offset.saturating_add(phase).rem_euclid(TABLE_LEN);
        if TEST_XLAT1.get(index).copied() == Some(b'o') {
            return Ok(cell);
        }
    }
    Err(format!("no current no-op cell at pointer {pointer}"))
}

fn oracle_run(fixture: RunFixture) -> TestResult<RunSnapshot> {
    let RunFixture { mut machine, step_budget } = fixture;
    let mut execution = OracleExecution {
        error: ERROR_NONE,
        error_pointer: 0,
        error_value: 0,
        status: RUN_BUDGET_EXHAUSTED,
        steps: 0,
    };
    if machine.termination().is_some() {
        execution.status = RUN_TERMINATED;
    } else {
        for _step in 0..step_budget {
            match machine.step() {
                Ok(StepOutcome::Continued) => {
                    execution.steps = execution.steps.saturating_add(1);
                },
                Ok(StepOutcome::Terminated(_reason)) => {
                    execution.steps = execution.steps.saturating_add(1);
                    execution.status = RUN_TERMINATED;
                    break;
                },
                Err(ProfileMachineError::InvalidEncryptionTarget {
                    pointer,
                    value,
                }) => {
                    execution.status = RUN_ERROR;
                    execution.error = ERROR_INVALID_ENCRYPTION;
                    execution.error_pointer = pointer;
                    execution.error_value = value;
                    break;
                },
                Err(other) => {
                    return Err(format!(
                        "unsupported profile CUDA oracle error: {other}"
                    ));
                },
            }
        }
    }
    snapshot(&machine, execution)
}

fn snapshot(
    machine: &ProfileMachine,
    execution: OracleExecution,
) -> TestResult<RunSnapshot> {
    let state = machine.snapshot_state();
    let registers = state.registers();
    Ok(RunSnapshot {
        accumulator: registers.accumulator,
        code_pointer: registers.code_pointer,
        data_pointer: registers.data_pointer,
        error: execution.error,
        error_pointer: execution.error_pointer,
        error_value: execution.error_value,
        input_consumed: usize_u32(state.io().input_consumed())?,
        memory: state.memory().to_vec(),
        output: state.io().output().to_vec(),
        status: execution.status,
        steps: execution.steps,
        termination: termination_code(state.io().termination()),
    })
}

fn encode_batch(fixtures: &[RunFixture]) -> TestResult<Vec<u8>> {
    let profile = current_profile();
    let memory_words = profile.memory_words();
    let capacity = fixtures
        .len()
        .saturating_mul(
            usize::try_from(memory_words)
                .map_err(|error| format!("profile memory capacity: {error}"))?
                .saturating_mul(size_of::<u32>()),
        )
        .saturating_add(1024);
    let mut bytes = Vec::with_capacity(capacity);
    bytes.extend_from_slice(&PROFILE_RESIDENT_WIRE_MAGIC);
    for value in [
        profile.eof_word(),
        u32::from(profile.input_instruction()),
        profile.memory_words(),
        u32::from(profile.output_instruction()),
        profile.word_modulus(),
        u32::from(profile.word_trits()),
        usize_u32(fixtures.len())?,
    ] {
        push_u32(&mut bytes, value);
    }
    for fixture in fixtures {
        encode_request(&mut bytes, fixture)?;
    }
    Ok(bytes)
}

fn encode_request(bytes: &mut Vec<u8>, fixture: &RunFixture) -> TestResult {
    let state = fixture.machine.snapshot_state();
    let registers = state.registers();
    for value in [
        registers.accumulator,
        registers.code_pointer,
        registers.data_pointer,
        usize_u32(state.io().input().len())?,
        usize_u32(state.io().input_consumed())?,
        usize_u32(state.io().output().len())?,
        fixture.step_budget,
        termination_code(state.io().termination()),
    ] {
        push_u32(bytes, value);
    }
    for value in state.memory() {
        push_u32(bytes, *value);
    }
    bytes.extend_from_slice(state.io().input());
    bytes.extend_from_slice(state.io().output());
    Ok(())
}

fn run_cuda_worker(
    request: Vec<u8>,
    memory_words: u32,
) -> TestResult<WorkerBatch> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let python = validation_python(root);
    let mut child = Command::new(&python)
        .args(["-m", "accelerator.cuda.profile_run_worker"])
        .current_dir(root)
        .env("PYTHONPATH", accelerator_python_path(root)?)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("profile CUDA worker spawn: {error}"))?;
    let mut stdin = child
        .stdin
        .take()
        .ok_or_else(|| String::from("profile CUDA worker stdin unavailable"))?;
    stdin
        .write_all(&request)
        .map_err(|error| format!("profile CUDA worker stdin: {error}"))?;
    drop(request);
    drop(stdin);
    let mut stdout = child.stdout.take().ok_or_else(|| {
        String::from("profile CUDA worker stdout unavailable")
    })?;
    let mut stderr = child.stderr.take().ok_or_else(|| {
        String::from("profile CUDA worker stderr unavailable")
    })?;
    let mut response = Vec::new();
    let _: usize = stdout
        .read_to_end(&mut response)
        .map_err(|error| format!("profile CUDA worker stdout: {error}"))?;
    let parsed = parse_worker_output(&response, memory_words);
    let status = child
        .wait()
        .map_err(|error| format!("profile CUDA worker wait: {error}"))?;
    let mut diagnostics = Vec::new();
    let _: usize = stderr
        .read_to_end(&mut diagnostics)
        .map_err(|error| format!("profile CUDA worker stderr: {error}"))?;
    if !status.success() {
        return Err(format!(
            "profile CUDA worker failed: {}",
            String::from_utf8_lossy(&diagnostics)
        ));
    }
    parsed
}

fn parse_worker_output(
    bytes: &[u8],
    memory_words: u32,
) -> TestResult<WorkerBatch> {
    match decode_profile_resident_response(bytes, memory_words)
        .map_err(|error| format!("profile CUDA response: {error}"))?
    {
        ProfileResidentWireResponse::Results(results) => Ok(Some(results)),
        ProfileResidentWireResponse::Unavailable => Ok(None),
    }
}

fn compare_batches(
    observed: &[RunSnapshot],
    expected: &[RunSnapshot],
) -> TestResult {
    check_equal(
        &observed.len(),
        &expected.len(),
        "profile CUDA result count",
    )?;
    for (index, (actual, oracle)) in observed.iter().zip(expected).enumerate() {
        compare_snapshot(index, actual, oracle)?;
    }
    Ok(())
}

fn compare_snapshot(
    index: usize,
    observed: &RunSnapshot,
    expected: &RunSnapshot,
) -> TestResult {
    let context = |field: &str| format!("profile CUDA case {index} {field}");
    check_equal(
        &observed.accumulator,
        &expected.accumulator,
        &context("accumulator"),
    )?;
    check_equal(
        &observed.code_pointer,
        &expected.code_pointer,
        &context("code pointer"),
    )?;
    check_equal(
        &observed.data_pointer,
        &expected.data_pointer,
        &context("data pointer"),
    )?;
    check_equal(&observed.error, &expected.error, &context("error"))?;
    check_equal(
        &observed.error_pointer,
        &expected.error_pointer,
        &context("error pointer"),
    )?;
    check_equal(
        &observed.error_value,
        &expected.error_value,
        &context("error value"),
    )?;
    check_equal(
        &observed.input_consumed,
        &expected.input_consumed,
        &context("input consumed"),
    )?;
    check_equal(&observed.output, &expected.output, &context("output"))?;
    check_equal(&observed.status, &expected.status, &context("status"))?;
    check_equal(&observed.steps, &expected.steps, &context("steps"))?;
    check_equal(
        &observed.termination,
        &expected.termination,
        &context("termination"),
    )?;
    compare_memory(index, &observed.memory, &expected.memory)
}

fn compare_memory(
    index: usize,
    observed: &[u32],
    expected: &[u32],
) -> TestResult {
    check_equal(
        &observed.len(),
        &expected.len(),
        "profile CUDA memory length",
    )?;
    for (address, (actual, oracle)) in observed.iter().zip(expected).enumerate()
    {
        if actual != oracle {
            return Err(format!(
                "profile CUDA case {index} memory[{address}]: expected \
                 {oracle}, observed {actual}"
            ));
        }
    }
    Ok(())
}

fn push_u32(bytes: &mut Vec<u8>, value: u32) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

const fn termination_code(termination: Option<Termination>) -> u32 {
    match termination {
        None => 0,
        Some(Termination::HaltInstruction) => 1,
        Some(Termination::NonGraphicalCell) => 2,
    }
}

fn usize_u32(value: usize) -> TestResult<u32> {
    u32::try_from(value)
        .map_err(|_error| String::from("profile resident counter exceeds u32"))
}
