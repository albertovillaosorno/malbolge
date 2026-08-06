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
//   - Exact full-state oracle evidence for resident CUDA classic execution.
// - Must-Not:
//   - Treat CUDA as semantic authority or require a GPU for CPU correctness.
// - Allows:
//   - Inputs: complete interpreter-authority states and bounded budgets.
//   - Outputs: exact register, memory, I/O, termination, and error assertions.
//   - Side effects: one optional repository-local Python CUDA worker process.
// - Split-When:
//   - Split when scalable-profile resident execution needs separate evidence.
// - Merge-When:
//   - Merge when one accelerator protocol owns all complete-state execution.
// - Summary:
//   - Checks resident CUDA runs against interpreter-authority Rust states.
// - Description:
//   - Compares every one of the 59049 classic memory words plus complete I/O
//   - and execution state after multi-step, resumed, and rejected runs.
// - Usage:
//   - Composed by `tests/vm.rs`; unavailable CUDA remains an optional-path
//   - pass.
// - Defaults:
//   - Interpreter-authority Rust execution is the expected-result oracle.
//

//! Exact full-state checks for resident classic CUDA bounded execution.

use std::io::Write as _;
use std::iter::repeat_n;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use malbolge::{
    BatchBackendCompletion, BatchBackendRequest, BatchExecutionBackend,
    BatchRequest, BatchResult, DifferentialCandidate, ExecutionMachine,
    ExecutionMode, InterpreterUndefinedBehavior, MAX_WORD_VALUE, MEMORY_WORDS,
    Machine, MachineError, MachineIoState, MachineState, Memory, Registers,
    RunOutcome, StepOutcome, Termination, Word, execute_batch,
    execute_batch_with_backend_report, historical_profile,
    verify_differential_candidates,
};

use crate::{
    TestResult, accelerator_python_path, check_equal, normalize_result,
};

const MAGIC: &[u8; 8] = b"MBRUN1\0\0";
const RESPONSE_RESULTS: u32 = 0;
const RESPONSE_UNAVAILABLE: u32 = 1;
const RUN_BUDGET_EXHAUSTED: u32 = 0;
const RUN_TERMINATED: u32 = 1;
const RUN_ERROR: u32 = 2;
const ERROR_NONE: u32 = 0;
const ERROR_INVALID_ENCRYPTION: u32 = 1;
const IO_ROUNDTRIP: &[u8] = include_bytes!(concat!(
    "../compatibility/specification/",
    "interpreter-io-roundtrip.malbolge",
));

type ProductBackendBatch = Option<Vec<Option<BatchBackendCompletion>>>;
type WorkerBatch = Option<Vec<RunSnapshot>>;

struct BinaryReader<'data> {
    data: &'data [u8],
    offset: usize,
}

impl<'data> BinaryReader<'data> {
    fn finish(&self) -> TestResult {
        check_equal(
            &self.offset,
            &self.data.len(),
            "resident CUDA trailing response bytes",
        )
    }

    const fn new(data: &'data [u8]) -> Self {
        Self { data, offset: 0 }
    }

    fn take(&mut self, count: usize) -> TestResult<&'data [u8]> {
        let end = self.offset.checked_add(count).ok_or_else(|| {
            String::from("resident CUDA response offset overflow")
        })?;
        let value = self
            .data
            .get(self.offset..end)
            .ok_or_else(|| String::from("truncated resident CUDA response"))?;
        self.offset = end;
        Ok(value)
    }

    fn u32(&mut self) -> TestResult<u32> {
        let raw = self.take(size_of::<u32>())?;
        let bytes: [u8; 4] = raw
            .try_into()
            .map_err(|_error| String::from("resident CUDA u32 width"))?;
        Ok(u32::from_le_bytes(bytes))
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
    input: Vec<u8>,
    machine: Machine,
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

struct CudaProductBackend {
    error: Option<String>,
    used_cuda: bool,
}

impl CudaProductBackend {
    const fn new() -> Self {
        Self {
            error: None,
            used_cuda: false,
        }
    }
}

impl BatchExecutionBackend for CudaProductBackend {
    fn execute(
        &mut self,
        requests: &[BatchBackendRequest<'_>],
    ) -> Option<Vec<Option<BatchBackendCompletion>>> {
        match try_cuda_product_batch(requests) {
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
fn cuda_resident_classic_runs_match_complete_interpreter_states() -> TestResult
{
    let fixtures = fixtures()?;
    let request = encode_batch(&fixtures)?;
    let expected = fixtures
        .iter()
        .cloned()
        .map(oracle_run)
        .collect::<TestResult<Vec<_>>>()?;
    let Some(observed) = run_cuda_worker(&request)? else {
        return Ok(());
    };
    compare_batches(&observed, &expected)
}

#[test]
fn cuda_classic_routes_through_product_batch_port() -> TestResult {
    let requests = product_batch_requests()?;
    let expected = execute_batch(requests.clone());
    let mut backend = CudaProductBackend::new();
    let (observed, report) =
        execute_batch_with_backend_report(requests, &mut backend);
    if let Some(error) = backend.error {
        return Err(format!("classic CUDA product backend: {error}"));
    }
    if !backend.used_cuda {
        return Ok(());
    }
    if report.backend_count() == 0 {
        return Err(String::from(
            "classic CUDA worker ran but no completion was accepted",
        ));
    }
    compare_product_batch(&observed, &expected)
}

fn product_batch_requests() -> TestResult<Vec<BatchRequest>> {
    let mut resumed = normalize_result(ExecutionMachine::from_source(
        IO_ROUNDTRIP,
        vec![0x51],
        ExecutionMode::Interpreter,
    ))?;
    let _prefix = normalize_result(resumed.run(2))?;
    let invalid = invalid_jump_fixture(1)?;
    let invalid_machine = normalize_result(ExecutionMachine::from_snapshot(
        invalid.machine.snapshot_state(),
        ExecutionMode::Interpreter,
        historical_profile(),
    ))?;
    Ok(vec![
        BatchRequest::from_machine(resumed, 1),
        BatchRequest::from_source(
            IO_ROUNDTRIP.to_vec(),
            vec![0x62],
            ExecutionMode::Interpreter,
            3,
        ),
        BatchRequest::from_machine(invalid_machine, 1),
        BatchRequest::from_source(
            b"D".to_vec(),
            Vec::new(),
            ExecutionMode::Interpreter,
            4,
        ),
    ])
}

fn try_cuda_product_batch(
    requests: &[BatchBackendRequest<'_>],
) -> TestResult<ProductBackendBatch> {
    if requests
        .iter()
        .any(|request| request.machine().mode() != ExecutionMode::Interpreter)
    {
        return Ok(Some(repeat_n(None, requests.len()).collect()));
    }
    let encoded = encode_product_batch(requests)?;
    let Some(snapshots) = run_cuda_worker(&encoded)? else {
        return Ok(None);
    };
    check_equal(
        &snapshots.len(),
        &requests.len(),
        "classic product CUDA result count",
    )?;
    requests
        .iter()
        .zip(snapshots)
        .map(|(request, snapshot)| product_completion(request, snapshot))
        .collect::<TestResult<Vec<_>>>()
        .map(Some)
}

fn encode_product_batch(
    requests: &[BatchBackendRequest<'_>],
) -> TestResult<Vec<u8>> {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(MAGIC);
    push_u32(&mut bytes, usize_u32(requests.len())?);
    for request in requests {
        encode_product_request(&mut bytes, request)?;
    }
    Ok(bytes)
}

fn encode_product_request(
    bytes: &mut Vec<u8>,
    request: &BatchBackendRequest<'_>,
) -> TestResult {
    let machine = request.machine();
    let registers = machine.registers();
    for value in [
        u32::from(registers.accumulator.value()),
        u32::from(registers.code_pointer.value()),
        u32::from(registers.data_pointer.value()),
        usize_u32(machine.input().len())?,
        usize_u32(machine.input_consumed())?,
        usize_u32(machine.output().len())?,
        usize_u32(request.step_budget())?,
        termination_code(machine.termination()),
    ] {
        push_u32(bytes, value);
    }
    for value in machine.memory().words() {
        push_u32(bytes, u32::from(value.value()));
    }
    bytes.extend_from_slice(machine.input());
    bytes.extend_from_slice(machine.output());
    Ok(())
}

fn product_completion(
    request: &BatchBackendRequest<'_>,
    snapshot: RunSnapshot,
) -> TestResult<Option<BatchBackendCompletion>> {
    if snapshot.status == RUN_ERROR {
        return Ok(None);
    }
    check_equal(
        &snapshot.error,
        &ERROR_NONE,
        "classic product completion error code",
    )?;
    let termination = decode_termination(snapshot.termination)?;
    let outcome = decode_outcome(snapshot.status, snapshot.steps, termination)?;
    let words = snapshot
        .memory
        .into_iter()
        .map(|value| {
            let raw = u16::try_from(value).map_err(|error| {
                format!("classic product word width: {error}")
            })?;
            normalize_result(Word::new(raw))
        })
        .collect::<TestResult<Vec<_>>>()?;
    let memory = normalize_result(Memory::from_words(words))?;
    let registers = Registers {
        accumulator: word_u32(snapshot.accumulator)?,
        code_pointer: word_u32(snapshot.code_pointer)?,
        data_pointer: word_u32(snapshot.data_pointer)?,
    };
    let io = normalize_result(MachineIoState::new(
        request.machine().input().to_vec(),
        usize::try_from(snapshot.input_consumed).map_err(|error| {
            format!("classic product input cursor: {error}")
        })?,
        snapshot.output,
        termination,
    ))?;
    Ok(Some(BatchBackendCompletion::new(
        MachineState::new(memory, registers, io),
        outcome,
    )))
}

fn decode_outcome(
    status: u32,
    steps: u32,
    termination: Option<Termination>,
) -> TestResult<RunOutcome> {
    let step_count = usize::try_from(steps)
        .map_err(|error| format!("classic product step count: {error}"))?;
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
                String::from("classic product terminated without reason")
            }),
        other => Err(format!("classic product unsupported status {other}")),
    }
}

fn decode_termination(code: u32) -> TestResult<Option<Termination>> {
    match code {
        0 => Ok(None),
        1 => Ok(Some(Termination::HaltInstruction)),
        2 => Ok(Some(Termination::NonGraphicalCell)),
        other => Err(format!("classic product termination code {other}")),
    }
}

fn word_u32(value: u32) -> TestResult<Word> {
    let raw = u16::try_from(value)
        .map_err(|error| format!("classic product register width: {error}"))?;
    normalize_result(Word::new(raw))
}

fn compare_product_batch(
    observed: &[BatchResult],
    expected: &[BatchResult],
) -> TestResult {
    check_equal(
        &observed.len(),
        &expected.len(),
        "classic product batch length",
    )?;
    for (index, (actual, oracle)) in observed.iter().zip(expected).enumerate() {
        let context =
            |field: &str| format!("classic product case {index} {field}");
        check_equal(&actual.error(), &oracle.error(), &context("error"))?;
        check_equal(&actual.outcome(), &oracle.outcome(), &context("outcome"))?;
        match (actual.machine(), oracle.machine()) {
            (Some(actual_machine), Some(oracle_machine)) => {
                check_equal(
                    &actual_machine.mode(),
                    &oracle_machine.mode(),
                    &context("mode"),
                )?;
                check_equal(
                    actual_machine.profile(),
                    oracle_machine.profile(),
                    &context("profile"),
                )?;
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
    let mut cases = vec![
        source_fixture(vec![0x41], 2)?,
        source_fixture(vec![0x41], 3)?,
        source_fixture(Vec::new(), 3)?,
        non_graphical_fixture(4),
        invalid_jump_fixture(4)?,
        wrap_fixture(1)?,
        alias_rotate_fixture(1)?,
    ];

    let input = vec![0x41];
    let mut resumed =
        normalize_result(Machine::from_source(IO_ROUNDTRIP, input.clone()))?;
    let _resumed_outcome = normalize_result(resumed.run(2))?;
    cases.push(RunFixture {
        input: input.clone(),
        machine: resumed,
        step_budget: 1,
    });

    let mut terminated =
        normalize_result(Machine::from_source(IO_ROUNDTRIP, input.clone()))?;
    let _terminated_outcome = normalize_result(terminated.run(3))?;
    cases.push(RunFixture {
        input,
        machine: terminated,
        step_budget: 100,
    });
    Ok(cases)
}

fn source_fixture(input: Vec<u8>, step_budget: u32) -> TestResult<RunFixture> {
    let machine =
        normalize_result(Machine::from_source(IO_ROUNDTRIP, input.clone()))?;
    Ok(RunFixture {
        input,
        machine,
        step_budget,
    })
}

fn non_graphical_fixture(step_budget: u32) -> RunFixture {
    RunFixture {
        input: Vec::new(),
        machine: Machine::with_registers(
            Memory::filled(Word::ZERO),
            Vec::new(),
            Registers {
                accumulator: Word::from_byte(7),
                code_pointer: Word::ZERO,
                data_pointer: Word::from_byte(1),
            },
        ),
        step_budget,
    }
}

fn invalid_jump_fixture(step_budget: u32) -> TestResult<RunFixture> {
    let mut memory = Memory::filled(Word::ZERO);
    normalize_result(memory.replace(Word::ZERO, Word::from_byte(b'b')))?;
    normalize_result(memory.replace(Word::from_byte(1), Word::from_byte(2)))?;
    Ok(RunFixture {
        input: vec![0x44],
        machine: Machine::with_registers(memory, vec![0x44], Registers {
            accumulator: Word::from_byte(7),
            code_pointer: Word::ZERO,
            data_pointer: Word::from_byte(1),
        }),
        step_budget,
    })
}

fn wrap_fixture(step_budget: u32) -> TestResult<RunFixture> {
    let mut memory = Memory::filled(Word::ZERO);
    normalize_result(memory.replace(Word::MAX, Word::from_byte(52)))?;
    Ok(RunFixture {
        input: Vec::new(),
        machine: Machine::with_registers(memory, Vec::new(), Registers {
            accumulator: Word::from_byte(7),
            code_pointer: Word::MAX,
            data_pointer: Word::MAX,
        }),
        step_budget,
    })
}

fn alias_rotate_fixture(step_budget: u32) -> TestResult<RunFixture> {
    let mut memory = Memory::filled(Word::ZERO);
    normalize_result(memory.replace(Word::MAX, Word::from_byte(b'u')))?;
    Ok(RunFixture {
        input: Vec::new(),
        machine: Machine::with_registers(memory, Vec::new(), Registers {
            accumulator: Word::ZERO,
            code_pointer: Word::MAX,
            data_pointer: Word::MAX,
        }),
        step_budget,
    })
}

fn oracle_run(fixture: RunFixture) -> TestResult<RunSnapshot> {
    let RunFixture {
        input: _input,
        mut machine,
        step_budget,
    } = fixture;
    let mut status = RUN_BUDGET_EXHAUSTED;
    let mut error = ERROR_NONE;
    let mut error_pointer = 0;
    let mut error_value = 0;
    let mut steps = 0u32;

    if machine.termination().is_some() {
        status = RUN_TERMINATED;
    } else {
        for _step in 0..step_budget {
            match machine.step() {
                Ok(StepOutcome::Continued) => {
                    steps = steps.saturating_add(1);
                },
                Ok(StepOutcome::Terminated(_reason)) => {
                    steps = steps.saturating_add(1);
                    status = RUN_TERMINATED;
                    break;
                },
                Err(MachineError::UnsupportedInterpreterBehavior(
                    InterpreterUndefinedBehavior::InvalidSelfEncryptionTarget {
                        pointer,
                        value,
                    },
                )) => {
                    status = RUN_ERROR;
                    error = ERROR_INVALID_ENCRYPTION;
                    error_pointer = u32::from(pointer.value());
                    error_value = u32::from(value.value());
                    break;
                },
                Err(other) => {
                    return Err(format!(
                        "unsupported resident CUDA oracle error: {other}"
                    ));
                },
            }
        }
    }
    snapshot(&machine, OracleExecution {
        error,
        error_pointer,
        error_value,
        status,
        steps,
    })
}

fn snapshot(
    machine: &Machine,
    execution: OracleExecution,
) -> TestResult<RunSnapshot> {
    let registers = machine.registers();
    Ok(RunSnapshot {
        accumulator: u32::from(registers.accumulator.value()),
        code_pointer: u32::from(registers.code_pointer.value()),
        data_pointer: u32::from(registers.data_pointer.value()),
        error: execution.error,
        error_pointer: execution.error_pointer,
        error_value: execution.error_value,
        input_consumed: usize_u32(machine.input_consumed())?,
        memory: memory_words(machine)?,
        output: machine.output().to_vec(),
        status: execution.status,
        steps: execution.steps,
        termination: termination_code(machine.termination()),
    })
}

fn memory_words(machine: &Machine) -> TestResult<Vec<u32>> {
    let mut words = Vec::with_capacity(MEMORY_WORDS);
    for raw in 0..=MAX_WORD_VALUE {
        let address = normalize_result(Word::new(raw))?;
        let value = normalize_result(machine.memory_word(address))?;
        words.push(u32::from(value.value()));
    }
    Ok(words)
}

fn encode_batch(fixtures: &[RunFixture]) -> TestResult<Vec<u8>> {
    let mut bytes = Vec::new();
    bytes.extend_from_slice(MAGIC);
    push_u32(&mut bytes, usize_u32(fixtures.len())?);
    for fixture in fixtures {
        encode_request(&mut bytes, fixture)?;
    }
    Ok(bytes)
}

fn encode_request(bytes: &mut Vec<u8>, fixture: &RunFixture) -> TestResult {
    let registers = fixture.machine.registers();
    for value in [
        u32::from(registers.accumulator.value()),
        u32::from(registers.code_pointer.value()),
        u32::from(registers.data_pointer.value()),
        usize_u32(fixture.input.len())?,
        usize_u32(fixture.machine.input_consumed())?,
        usize_u32(fixture.machine.output().len())?,
        fixture.step_budget,
        termination_code(fixture.machine.termination()),
    ] {
        push_u32(bytes, value);
    }
    for value in memory_words(&fixture.machine)? {
        push_u32(bytes, value);
    }
    bytes.extend_from_slice(&fixture.input);
    bytes.extend_from_slice(fixture.machine.output());
    Ok(())
}

fn run_cuda_worker(request: &[u8]) -> TestResult<WorkerBatch> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let python = python_wrapper(root);
    let mut child = Command::new(&python)
        .args(["-m", "accelerator.cuda.classic_run_worker"])
        .current_dir(root)
        .env("PYTHONPATH", accelerator_python_path(root)?)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("resident CUDA worker spawn: {error}"))?;
    let mut stdin = child.stdin.take().ok_or_else(|| {
        String::from("resident CUDA worker stdin unavailable")
    })?;
    stdin
        .write_all(request)
        .map_err(|error| format!("resident CUDA worker stdin: {error}"))?;
    drop(stdin);
    let output = child
        .wait_with_output()
        .map_err(|error| format!("resident CUDA worker wait: {error}"))?;
    if !output.status.success() {
        return Err(format!(
            "resident CUDA worker failed: {}",
            String::from_utf8_lossy(&output.stderr)
        ));
    }
    parse_worker_output(&output.stdout)
}

fn parse_worker_output(data: &[u8]) -> TestResult<WorkerBatch> {
    let mut reader = BinaryReader::new(data);
    check_equal(
        &reader.take(MAGIC.len())?,
        &MAGIC.as_slice(),
        "resident CUDA response magic",
    )?;
    let kind = reader.u32()?;
    let count = usize::try_from(reader.u32()?)
        .map_err(|_error| String::from("resident CUDA response count"))?;
    if kind == RESPONSE_UNAVAILABLE {
        check_equal(&count, &0usize, "unavailable response count")?;
        reader.finish()?;
        return Ok(None);
    }
    check_equal(&kind, &RESPONSE_RESULTS, "resident CUDA response kind")?;
    let mut results = Vec::with_capacity(count);
    for _item in 0..count {
        results.push(parse_result(&mut reader)?);
    }
    reader.finish()?;
    Ok(Some(results))
}

fn parse_result(reader: &mut BinaryReader<'_>) -> TestResult<RunSnapshot> {
    let status = reader.u32()?;
    let error = reader.u32()?;
    let accumulator = reader.u32()?;
    let code_pointer = reader.u32()?;
    let data_pointer = reader.u32()?;
    let input_consumed = reader.u32()?;
    let output_len = usize::try_from(reader.u32()?)
        .map_err(|_error| String::from("resident output length"))?;
    let termination = reader.u32()?;
    let error_pointer = reader.u32()?;
    let error_value = reader.u32()?;
    let steps = reader.u32()?;
    let mut memory = Vec::with_capacity(MEMORY_WORDS);
    for _word in 0..MEMORY_WORDS {
        memory.push(reader.u32()?);
    }
    let output = reader.take(output_len)?.to_vec();
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
        "resident CUDA result count",
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
    let context = |field: &str| format!("resident CUDA case {index} {field}");
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
        "resident CUDA memory length",
    )?;
    for (address, (actual, oracle)) in observed.iter().zip(expected).enumerate()
    {
        if actual != oracle {
            return Err(format!(
                "resident CUDA case {index} memory[{address}]: expected \
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
        .map_err(|_error| String::from("resident classic counter exceeds u32"))
}

fn python_wrapper(root: &Path) -> PathBuf {
    root.join(".dependencies/python/3.14.6/Scripts/python-jig.cmd")
}
