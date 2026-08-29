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

use std::io::{BufReader, Cursor, Read, Write as _};
use std::iter::repeat_n;
use std::path::Path;
use std::process::{Command, Stdio};

use malbolge::{
    DifferentialCandidate, ProfileBatchBackendCompletion,
    ProfileBatchBackendRequest, ProfileBatchExecutionBackend,
    ProfileBatchRequest, ProfileBatchResult, ProfileMachine,
    ProfileMachineError, ProfileMachineIoState, ProfileMachineState,
    ProfileRegisters, RunOutcome, StepOutcome, Termination, current_profile,
    execute_profile_batch, execute_profile_batch_with_backend_report,
    verify_differential_candidates, verify_minimum_initial_halt_profile_width,
};

use crate::{
    TestResult, accelerator_python_path, check_equal, cuda_test_guard,
    normalize_result, validation_python,
};

const MAGIC: &[u8; 8] = b"MBPRN2\0\0";
const RESPONSE_RESULTS: u32 = 0;
const RESPONSE_UNAVAILABLE: u32 = 1;
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

type EncodedProfileProductBatch = (ResidentWireGeometry, Vec<u8>);
type ProductBackendBatch = Option<Vec<Option<ProfileBatchBackendCompletion>>>;
type WorkerBatch = Option<Vec<RunSnapshot>>;

struct BinaryReader<Reader> {
    reader: Reader,
}

impl<Reader: Read> BinaryReader<Reader> {
    fn finish(&mut self) -> TestResult {
        let mut trailing = [0u8; 1];
        match self.reader.read(&mut trailing) {
            Ok(0) => Ok(()),
            Ok(_count) => {
                Err(String::from("profile CUDA trailing response bytes"))
            },
            Err(error) => Err(format!("profile CUDA response finish: {error}")),
        }
    }

    const fn new(reader: Reader) -> Self {
        Self { reader }
    }

    fn take(&mut self, count: usize) -> TestResult<Vec<u8>> {
        let mut value = vec![0u8; count];
        self.reader.read_exact(&mut value).map_err(|error| {
            format!("truncated profile CUDA response: {error}")
        })?;
        Ok(value)
    }

    fn u32(&mut self) -> TestResult<u32> {
        let mut bytes = [0u8; size_of::<u32>()];
        self.reader
            .read_exact(&mut bytes)
            .map_err(|error| format!("truncated profile CUDA u32: {error}"))?;
        Ok(u32::from_le_bytes(bytes))
    }

    fn words(&mut self, count: usize) -> TestResult<Vec<u32>> {
        let mut words = Vec::with_capacity(count);
        for _word in 0..count {
            words.push(self.u32()?);
        }
        Ok(words)
    }
}

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

#[derive(Clone, Debug, Eq, PartialEq)]
struct RunSnapshot {
    accumulator: u32,
    code_pointer: u32,
    data_pointer: u32,
    error: u32,
    error_pointer: u32,
    error_value: u32,
    input_consumed: u32,
    memory: Vec<u32>,
    output: Vec<u8>,
    status: u32,
    steps: u32,
    termination: u32,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ResidentWireGeometry {
    eof_word: u32,
    input_instruction: u32,
    memory_words: u32,
    output_instruction: u32,
    word_modulus: u32,
    word_trits: u32,
}

impl ResidentWireGeometry {
    fn from_request(request: &ProfileBatchBackendRequest<'_>) -> Self {
        Self {
            eof_word: request.eof_word(),
            input_instruction: u32::from(request.input_instruction()),
            memory_words: request.memory_words(),
            output_instruction: u32::from(request.output_instruction()),
            word_modulus: request.word_modulus(),
            word_trits: u32::from(request.word_trits()),
        }
    }

    fn memory_len(self) -> TestResult<usize> {
        usize::try_from(self.memory_words)
            .map_err(|error| format!("profile resident memory words: {error}"))
    }

    const fn wire_values(self) -> [u32; 6] {
        [
            self.eof_word,
            self.input_instruction,
            self.memory_words,
            self.output_instruction,
            self.word_modulus,
            self.word_trits,
        ]
    }
}

struct CudaProfileProductBackend {
    error: Option<String>,
    used_cuda: bool,
}

impl CudaProfileProductBackend {
    const fn new() -> Self {
        Self {
            error: None,
            used_cuda: false,
        }
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
        match homogeneous_product_geometry(requests).and_then(|geometry| {
            geometry
                .map(|value| {
                    encode_profile_product_batch(requests, value)
                        .map(|bytes| (value, bytes))
                })
                .transpose()
        }) {
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
        match try_cuda_profile_product_batch(requests) {
            Ok(Some(results)) => {
                self.used_cuda = true;
                Some(results)
            },
            Ok(None) => None,
            Err(error) => {
                self.error = Some(error);
                None
            },
        }
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
    let mut backend = CudaProfileProductBackend::new();
    let (observed, report) =
        execute_profile_batch_with_backend_report(requests, &mut backend);
    if let Some(error) = backend.error {
        return Err(format!("profile CUDA product backend: {error}"));
    }
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

#[test]
fn derived_profile_product_encoding_uses_admitted_geometry() -> TestResult {
    let verified = normalize_result(
        verify_minimum_initial_halt_profile_width(current_profile(), b"QP"),
    )?;
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
        &ResidentWireGeometry {
            eof_word: 59_048,
            input_instruction: u32::from(b'/'),
            memory_words: 59_049,
            output_instruction: u32::from(b'<'),
            word_modulus: 59_049,
            word_trits: 10,
        },
        "derived profile wire geometry",
    )?;
    let mut reader = BinaryReader::new(Cursor::new(encoded));
    check_equal(
        &reader.take(MAGIC.len())?.as_slice(),
        &MAGIC.as_slice(),
        "derived profile wire magic",
    )?;
    for expected in geometry.wire_values() {
        check_equal(
            &reader.u32()?,
            &expected,
            "derived profile wire geometry field",
        )?;
    }
    check_equal(&reader.u32()?, &1u32, "derived profile wire count")?;
    check_equal(
        &report.fallback_count(),
        &1usize,
        "derived encoding probe fallback",
    )
}

#[test]
fn cuda_derived_profile_routes_through_product_batch_port() -> TestResult {
    let verified = normalize_result(
        verify_minimum_initial_halt_profile_width(current_profile(), b"QP"),
    )?;
    let machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    let requests = vec![ProfileBatchRequest::from_machine(machine, 1)];
    let expected = execute_profile_batch(requests.clone());
    let _cuda_guard = cuda_test_guard()?;
    let mut backend = CudaProfileProductBackend::new();
    let (observed, report) =
        execute_profile_batch_with_backend_report(requests, &mut backend);
    if let Some(error) = backend.error {
        return Err(format!("derived profile CUDA product backend: {error}"));
    }
    if !backend.used_cuda {
        return Ok(());
    }
    check_equal(&report.backend_count(), &1usize, "derived CUDA completion")?;
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

fn try_cuda_profile_product_batch(
    requests: &[ProfileBatchBackendRequest<'_>],
) -> TestResult<ProductBackendBatch> {
    if requests.is_empty() {
        return Ok(Some(Vec::new()));
    }
    let profile = current_profile();
    if requests
        .iter()
        .any(|request| request.machine().profile() != profile)
    {
        return Ok(Some(repeat_n(None, requests.len()).collect()));
    }
    let Some(geometry) = homogeneous_product_geometry(requests)? else {
        return Ok(Some(repeat_n(None, requests.len()).collect()));
    };
    let encoded = encode_profile_product_batch(requests, geometry)?;
    let Some(snapshots) = run_cuda_worker(encoded, geometry.memory_words)?
    else {
        return Ok(None);
    };
    check_equal(
        &snapshots.len(),
        &requests.len(),
        "profile product CUDA result count",
    )?;
    requests
        .iter()
        .zip(snapshots)
        .map(|(request, snapshot)| {
            profile_product_completion(request, snapshot)
        })
        .collect::<TestResult<Vec<_>>>()
        .map(Some)
}

fn homogeneous_product_geometry(
    requests: &[ProfileBatchBackendRequest<'_>],
) -> TestResult<Option<ResidentWireGeometry>> {
    let Some(first) = requests.first() else {
        return Ok(None);
    };
    let geometry = ResidentWireGeometry::from_request(first);
    if requests
        .iter()
        .any(|request| ResidentWireGeometry::from_request(request) != geometry)
    {
        return Ok(None);
    }
    let _memory_len = geometry.memory_len()?;
    Ok(Some(geometry))
}

fn encode_profile_product_batch(
    requests: &[ProfileBatchBackendRequest<'_>],
    geometry: ResidentWireGeometry,
) -> TestResult<Vec<u8>> {
    let memory_words = geometry.memory_len()?;
    let capacity = requests
        .len()
        .saturating_mul(memory_words.saturating_mul(size_of::<u32>()))
        .saturating_add(1024);
    let mut bytes = Vec::with_capacity(capacity);
    bytes.extend_from_slice(MAGIC);
    for value in geometry
        .wire_values()
        .into_iter()
        .chain([usize_u32(requests.len())?])
    {
        push_u32(&mut bytes, value);
    }
    for request in requests {
        encode_profile_product_request(&mut bytes, request)?;
    }
    Ok(bytes)
}

fn encode_profile_product_request(
    bytes: &mut Vec<u8>,
    request: &ProfileBatchBackendRequest<'_>,
) -> TestResult {
    let machine = request.machine();
    let registers = machine.registers();
    for value in [
        registers.accumulator,
        registers.code_pointer,
        registers.data_pointer,
        usize_u32(machine.input().len())?,
        usize_u32(machine.input_consumed())?,
        usize_u32(machine.output().len())?,
        usize_u32(request.step_budget())?,
        termination_code(machine.termination()),
    ] {
        push_u32(bytes, value);
    }
    for value in machine.memory() {
        push_u32(bytes, *value);
    }
    bytes.extend_from_slice(machine.input());
    bytes.extend_from_slice(machine.output());
    Ok(())
}

fn profile_product_completion(
    request: &ProfileBatchBackendRequest<'_>,
    snapshot: RunSnapshot,
) -> TestResult<Option<ProfileBatchBackendCompletion>> {
    if snapshot.status == RUN_ERROR {
        return Ok(None);
    }
    check_equal(
        &snapshot.error,
        &ERROR_NONE,
        "profile product completion error code",
    )?;
    let termination = decode_product_termination(snapshot.termination)?;
    let outcome =
        decode_product_outcome(snapshot.status, snapshot.steps, termination)?;
    let io = normalize_result(ProfileMachineIoState::new(
        request.machine().input().to_vec(),
        usize::try_from(snapshot.input_consumed).map_err(|error| {
            format!("profile product input cursor: {error}")
        })?,
        snapshot.output,
        termination,
    ))?;
    let state = normalize_result(ProfileMachineState::new_with_geometry(
        request.machine().geometry(),
        snapshot.memory,
        ProfileRegisters {
            accumulator: snapshot.accumulator,
            code_pointer: snapshot.code_pointer,
            data_pointer: snapshot.data_pointer,
        },
        io,
    ))?;
    Ok(Some(ProfileBatchBackendCompletion::new(state, outcome)))
}

fn decode_product_outcome(
    status: u32,
    steps: u32,
    termination: Option<Termination>,
) -> TestResult<RunOutcome> {
    let step_count = usize::try_from(steps)
        .map_err(|error| format!("profile product step count: {error}"))?;
    match status {
        RUN_BUDGET_EXHAUSTED => {
            Ok(RunOutcome::BudgetExhausted { steps: step_count })
        },
        RUN_TERMINATED => termination
            .map(|reason| RunOutcome::Terminated {
                reason,
                steps: step_count,
            })
            .ok_or_else(|| {
                String::from("profile product terminated without reason")
            }),
        other => Err(format!("profile product unsupported status {other}")),
    }
}

fn decode_product_termination(code: u32) -> TestResult<Option<Termination>> {
    match code {
        0 => Ok(None),
        1 => Ok(Some(Termination::HaltInstruction)),
        2 => Ok(Some(Termination::NonGraphicalCell)),
        other => Err(format!("profile product termination code {other}")),
    }
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
    bytes.extend_from_slice(MAGIC);
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
    let stdout = child.stdout.take().ok_or_else(|| {
        String::from("profile CUDA worker stdout unavailable")
    })?;
    let mut stderr = child.stderr.take().ok_or_else(|| {
        String::from("profile CUDA worker stderr unavailable")
    })?;
    let parsed = parse_worker_output(BufReader::new(stdout), memory_words);
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

fn parse_worker_output<Reader>(
    stream: Reader,
    memory_words: u32,
) -> TestResult<WorkerBatch>
where
    Reader: Read,
{
    let mut reader = BinaryReader::new(stream);
    let magic = reader.take(MAGIC.len())?;
    check_equal(
        &magic.as_slice(),
        &MAGIC.as_slice(),
        "profile CUDA response magic",
    )?;
    let kind = reader.u32()?;
    let count = usize::try_from(reader.u32()?)
        .map_err(|_error| String::from("profile CUDA response count"))?;
    if kind == RESPONSE_UNAVAILABLE {
        check_equal(
            &count,
            &0usize,
            "profile CUDA unavailable response count",
        )?;
        reader.finish()?;
        return Ok(None);
    }
    check_equal(&kind, &RESPONSE_RESULTS, "profile CUDA response kind")?;
    let memory_len = usize::try_from(memory_words)
        .map_err(|error| format!("profile response memory words: {error}"))?;
    let mut results = Vec::with_capacity(count);
    for _item in 0..count {
        results.push(parse_result(&mut reader, memory_len)?);
    }
    reader.finish()?;
    Ok(Some(results))
}

fn parse_result<Reader>(
    reader: &mut BinaryReader<Reader>,
    memory_words: usize,
) -> TestResult<RunSnapshot>
where
    Reader: Read,
{
    let status = reader.u32()?;
    let error = reader.u32()?;
    let accumulator = reader.u32()?;
    let code_pointer = reader.u32()?;
    let data_pointer = reader.u32()?;
    let input_consumed = reader.u32()?;
    let output_len = usize::try_from(reader.u32()?)
        .map_err(|_error| String::from("profile output length"))?;
    let termination = reader.u32()?;
    let error_pointer = reader.u32()?;
    let error_value = reader.u32()?;
    let steps = reader.u32()?;
    let memory = reader.words(memory_words)?;
    let output = reader.take(output_len)?;
    Ok(RunSnapshot {
        accumulator,
        code_pointer,
        data_pointer,
        error,
        error_pointer,
        error_value,
        input_consumed,
        memory,
        output,
        status,
        steps,
        termination,
    })
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
