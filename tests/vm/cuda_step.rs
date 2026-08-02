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
//   - Differential evidence for optional compact CUDA classic transitions.
// - Must-Not:
//   - Treat CUDA output as semantic authority or require a GPU for correctness.
// - Allows:
//   - Inputs: normative classic Machine traces and compact memory snapshots.
//   - Outputs: exact transition-projection equality assertions.
//   - Side effects: one optional repository-local Python CUDA worker process.
// - Split-When:
//   - Split when resident full-memory GPU VM evidence gains its own lifecycle.
// - Merge-When:
//   - Merge when all accelerator VM evidence shares one protocol owner.
// - Summary:
//   - Requires CUDA one-step proposals to equal normative Rust StepTrace data.
// - Description:
//   - Exercises all classic instruction families, rejection, wrap, and
//   - aliasing.
// - Usage:
//   - Composed by `tests/vm.rs`; unavailable CUDA is an optional-path pass.
// - Defaults:
//   - The safe-Rust specification machine is always the expected-result oracle.
//

//! CUDA compact-step proposals checked against normative classic Rust traces.

use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use malbolge::{
    Machine, MachineError, Memory, MemoryWrite, Registers, StepOutcome,
    StepTrace, Termination, TraceInput, Word,
};

use crate::{
    TestResult, accelerator_python_path, check_equal, normalize_result,
};

const PROTOCOL: &str = "MBSTEP1";
const REQUEST_WORDS: usize = 20;
const RESULT_WORDS: usize = 26;
const MAX_SLOTS: usize = 4;

type ErrorProjection = (u32, u32, u32);
type ResultBatch = Vec<Vec<u32>>;
type WorkerBatch = Option<ResultBatch>;
type OracleBatch = (String, ResultBatch);

#[derive(Clone)]
struct OracleFixture {
    cells: Vec<(Word, Word)>,
    machine: Machine,
    next_input: Option<u8>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ProtocolRequest {
    words: Vec<u32>,
}

#[test]
fn cuda_compact_classic_steps_match_normative_rust_traces() -> TestResult {
    let mut fixtures = fixtures()?;
    let (request_text, expected) = normative_batch(&mut fixtures)?;
    let Some(observed) = run_cuda_worker(&request_text)? else {
        return Ok(());
    };
    check_equal(&observed, &expected, "CUDA classic-step differential batch")
}

fn fixture(
    registers: Registers,
    input: &[u8],
    cells: &[(u16, u16)],
) -> TestResult<OracleFixture> {
    let mut memory = Memory::filled(Word::ZERO);
    let mut canonical_cells = Vec::new();
    for (raw_address, raw_value) in cells {
        let address = word(*raw_address)?;
        let value = word(*raw_value)?;
        normalize_result(memory.replace(address, value))?;
        canonical_cells.push((address, value));
    }
    Ok(OracleFixture {
        cells: canonical_cells,
        machine: Machine::with_registers(memory, input.to_vec(), registers),
        next_input: input.first().copied(),
    })
}

fn fixtures() -> TestResult<Vec<OracleFixture>> {
    let mut cases = vec![
        fixture(registers(0, 0, 1)?, &[], &[(0, 62), (1, 0)])?,
        fixture(registers(0, 0, 1)?, &[], &[(0, 39), (1, 1)])?,
        fixture(registers(0, 0, 1)?, &[65], &[(0, 99)])?,
        fixture(registers(0, 0, 1)?, &[], &[(0, 99)])?,
        fixture(registers(59_048, 0, 1)?, &[], &[(0, 117)])?,
        fixture(registers(0, 0, 1)?, &[], &[(0, 98), (1, 2), (2, 68)])?,
        fixture(registers(0, 0, 1)?, &[], &[(0, 40), (1, 5)])?,
        fixture(registers(7, 0, 1)?, &[], &[(0, 68)])?,
        fixture(registers(7, 0, 1)?, &[], &[(0, 81)])?,
        fixture(registers(7, 0, 1)?, &[], &[(0, 0)])?,
        fixture(registers(0, 0, 1)?, &[], &[(0, 98), (1, 2), (2, 0)])?,
        fixture(registers(7, 59_048, 59_048)?, &[], &[(59_048, 52)])?,
        fixture(registers(0, 59_048, 59_048)?, &[], &[(59_048, 117)])?,
    ];
    let mut terminated = fixture(registers(7, 0, 1)?, &[], &[(0, 81)])?;
    let _outcome = normalize_result(terminated.machine.step())?;
    cases.push(terminated);
    Ok(cases)
}

fn normative_batch(fixtures: &mut [OracleFixture]) -> TestResult<OracleBatch> {
    let mut request_lines = Vec::with_capacity(fixtures.len());
    let mut expected = Vec::with_capacity(fixtures.len());
    for fixture in fixtures {
        let request_cells = fixture.cells.clone();
        let next_input = fixture.next_input;
        let mut observed_trace = None;
        let _step = fixture
            .machine
            .step_traced(&mut |observed| observed_trace = Some(*observed));
        let trace = observed_trace
            .ok_or_else(|| String::from("normative step emitted no trace"))?;
        let request = protocol_request(&trace, next_input, &request_cells)?;
        request_lines.push(request_line(&request));
        expected.push(expected_words(&trace)?);
    }
    let mut text = format!("{PROTOCOL} {}\n", request_lines.len());
    text.push_str(&request_lines.join("\n"));
    text.push('\n');
    Ok((text, expected))
}

fn protocol_request(
    trace: &StepTrace,
    next_input: Option<u8>,
    cells: &[(Word, Word)],
) -> TestResult<ProtocolRequest> {
    if cells.len() > MAX_SLOTS {
        return Err(String::from("compact Rust fixture exceeds memory slots"));
    }
    let mut words = vec![
        u32::from(trace.before.registers.accumulator.value()),
        u32::from(trace.before.registers.code_pointer.value()),
        u32::from(trace.before.registers.data_pointer.value()),
        usize_u32(trace.before.input_consumed)?,
        usize_u32(trace.before.output_len)?,
        termination_code(trace.before.termination),
        u32::from(next_input.is_some()),
        u32::from(next_input.unwrap_or(0)),
    ];
    for (address, value) in cells {
        words.extend([1, u32::from(address.value()), u32::from(value.value())]);
    }
    for _unused in cells.len()..MAX_SLOTS {
        words.extend([0, 0, 0]);
    }
    if words.len() == REQUEST_WORDS {
        Ok(ProtocolRequest { words })
    } else {
        Err(String::from("compact request encoding width drifted"))
    }
}

fn expected_words(trace: &StepTrace) -> TestResult<Vec<u32>> {
    let (error, pointer, value) = error_code(trace.result)?;
    let (input_kind, input_value) = input_code(trace.input);
    let mut words = vec![
        status_code(trace.result),
        error,
        u32::from(trace.after.registers.accumulator.value()),
        u32::from(trace.after.registers.code_pointer.value()),
        u32::from(trace.after.registers.data_pointer.value()),
        usize_u32(trace.after.input_consumed)?,
        usize_u32(trace.after.output_len)?,
        termination_code(trace.after.termination),
    ];
    words.extend(optional_word_words(trace.fetched_cell));
    words.extend(optional_byte_words(trace.decoded));
    let input_words: [u32; 2] = (input_kind, input_value).into();
    words.extend(input_words);
    words.extend(optional_byte_words(trace.output));
    words.extend(memory_write_words(trace.memory_delta.data));
    words.extend(memory_write_words(trace.memory_delta.encryption));
    let error_words: [u32; 2] = (pointer, value).into();
    words.extend(error_words);
    if words.len() == RESULT_WORDS {
        Ok(words)
    } else {
        Err(String::from("normative result encoding width drifted"))
    }
}

fn run_cuda_worker(request: &str) -> TestResult<WorkerBatch> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let python = python_wrapper(root);
    let mut child = Command::new(&python)
        .args(["-m", "accelerator.cuda.classic_step_worker"])
        .current_dir(root)
        .env("PYTHONPATH", accelerator_python_path(root)?)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("CUDA worker spawn: {error}"))?;
    let mut stdin = child
        .stdin
        .take()
        .ok_or_else(|| String::from("CUDA worker stdin unavailable"))?;
    stdin
        .write_all(request.as_bytes())
        .map_err(|error| format!("CUDA worker stdin: {error}"))?;
    drop(stdin);
    let output = child
        .wait_with_output()
        .map_err(|error| format!("CUDA worker wait: {error}"))?;
    if !output.status.success() {
        return Err(format!(
            "CUDA worker failed: {}",
            String::from_utf8_lossy(&output.stderr)
        ));
    }
    parse_worker_output(&String::from_utf8_lossy(&output.stdout))
}

fn parse_worker_output(text: &str) -> TestResult<WorkerBatch> {
    let mut lines = text.lines();
    let header = lines
        .next()
        .ok_or_else(|| String::from("CUDA worker returned no header"))?;
    let header_words = header.split_whitespace().collect::<Vec<_>>();
    if header_words.first().copied() != Some(PROTOCOL) {
        return Err(format!("unexpected CUDA worker header: {header}"));
    }
    if header_words.get(1).copied() == Some("UNAVAILABLE") {
        return Ok(None);
    }
    let count = header_words
        .get(1)
        .ok_or_else(|| String::from("CUDA worker header has no count"))?
        .parse::<usize>()
        .map_err(|error| format!("CUDA worker count: {error}"))?;
    let rows = lines
        .map(parse_result_row)
        .collect::<TestResult<Vec<_>>>()?;
    if rows.len() != count {
        return Err(format!(
            "CUDA worker row count mismatch: expected {count}, got {}",
            rows.len()
        ));
    }
    Ok(Some(rows))
}

fn parse_result_row(line: &str) -> TestResult<Vec<u32>> {
    let words = line
        .split_whitespace()
        .map(|value| {
            value
                .parse::<u32>()
                .map_err(|error| format!("CUDA result word: {error}"))
        })
        .collect::<TestResult<Vec<_>>>()?;
    if words.len() == RESULT_WORDS {
        Ok(words)
    } else {
        Err(format!(
            "CUDA result requires {RESULT_WORDS} words, got {}",
            words.len()
        ))
    }
}

fn error_code(
    result: Result<StepOutcome, MachineError>,
) -> TestResult<ErrorProjection> {
    match result {
        Ok(_outcome) => Ok((0, 0, 0)),
        Err(MachineError::InvalidEncryptionTarget { pointer, value }) => {
            Ok((1, u32::from(pointer.value()), u32::from(value.value())))
        },
        Err(error) => {
            Err(format!("unsupported CUDA oracle error fixture: {error}"))
        },
    }
}

fn input_code(input: Option<TraceInput>) -> (u32, u32) {
    match input {
        None => (0, 0),
        Some(TraceInput::Byte(value)) => (1, u32::from(value)),
        Some(TraceInput::EndOfInput) => (2, 0),
    }
}

fn memory_write_words(write: Option<MemoryWrite>) -> [u32; 4] {
    write.map_or([0, 0, 0, 0], |change| {
        [
            1,
            u32::from(change.address.value()),
            u32::from(change.before.value()),
            u32::from(change.after.value()),
        ]
    })
}

fn optional_byte_words(value: Option<u8>) -> [u32; 2] {
    value.map_or([0, 0], |byte| [1, u32::from(byte)])
}

fn optional_word_words(value: Option<Word>) -> [u32; 2] {
    value.map_or([0, 0], |word| [1, u32::from(word.value())])
}

fn python_wrapper(root: &Path) -> PathBuf {
    root.join(".dependencies/python/3.14.6/Scripts/python-jig.cmd")
}

fn registers(
    accumulator: u16,
    code_pointer: u16,
    data_pointer: u16,
) -> TestResult<Registers> {
    Ok(Registers {
        accumulator: word(accumulator)?,
        code_pointer: word(code_pointer)?,
        data_pointer: word(data_pointer)?,
    })
}

const fn status_code(result: Result<StepOutcome, MachineError>) -> u32 {
    match result {
        Ok(StepOutcome::Continued) => 0,
        Ok(StepOutcome::Terminated(_reason)) => 1,
        Err(_error) => 2,
    }
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
        .map_err(|_error| String::from("trace counter exceeds u32"))
}

fn word(value: u16) -> TestResult<Word> {
    normalize_result(Word::new(value))
}

fn request_line(request: &ProtocolRequest) -> String {
    request
        .words
        .iter()
        .map(u32::to_string)
        .collect::<Vec<_>>()
        .join(" ")
}
