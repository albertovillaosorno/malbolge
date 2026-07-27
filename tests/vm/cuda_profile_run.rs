// File:
//   - cuda_profile_run.rs
// Path:
//   - tests/vm/cuda_profile_run.rs
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
//   - Exact full-state oracle evidence for scalable resident CUDA execution.
// - Must-Not:
//   - Treat CUDA or Python as profile identity or semantic authority.
// - Allows:
//   - Inputs: canonical Rust profile geometry and complete current VM states.
//   - Outputs: exact registers, memory, I/O, termination, and error assertions.
//   - Side effects: one optional repository-local Python CUDA worker process.
// - Split-When:
//   - Split when another memory model is admitted beyond single-word modular.
// - Merge-When:
//   - Merge when classic and scalable resident protocols share one Rust client.
// - Summary:
//   - Checks current-profile resident CUDA runs against normative Rust states.
// - Description:
//   - Compares all 4,782,969 current memory words plus complete observable
//     state.
// - Usage:
//   - Composed by `tests/vm.rs`; unavailable CUDA remains an optional-path
//     pass.
// - Defaults:
//   - `current_profile()` supplies geometry and safe Rust supplies every
//     oracle.
//
// Related documents:
// - docs/technical/integrations/accelerators/cuda-exact-vm-adapter.md
// - docs/technical/compatibility/scalable-malbolge-memory-model.md
//
// Large file:
//   - false
//

//! Full-state current-profile differential checks for resident CUDA execution.

use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileRegisters, StepOutcome,
    Termination, current_profile,
};

use crate::{TestResult, check_equal, normalize_result};

const MAGIC: &[u8; 8] = b"MBPRN1\0\0";
const RESPONSE_RESULTS: u32 = 0;
const RESPONSE_UNAVAILABLE: u32 = 1;
const RUN_BUDGET_EXHAUSTED: u32 = 0;
const RUN_TERMINATED: u32 = 1;
const RUN_ERROR: u32 = 2;
const ERROR_NONE: u32 = 0;
const ERROR_INVALID_ENCRYPTION: u32 = 1;
const CURRENT_INPUT: u8 = 0xa5;
const CURRENT_SOURCE: &[u8] = b"(=%`qL";
const REJECTING_JUMP_SOURCE: &[u8] = b"b'";
const TABLE_LEN: usize = 94;
const TEST_XLAT1: &[u8; TABLE_LEN] =
    b"+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI\
.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha";

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
            "profile CUDA trailing response bytes",
        )
    }

    const fn new(data: &'data [u8]) -> Self {
        Self { data, offset: 0 }
    }

    fn take(&mut self, count: usize) -> TestResult<&'data [u8]> {
        let end = self.offset.checked_add(count).ok_or_else(|| {
            String::from("profile CUDA response offset overflow")
        })?;
        let value = self
            .data
            .get(self.offset..end)
            .ok_or_else(|| String::from("truncated profile CUDA response"))?;
        self.offset = end;
        Ok(value)
    }

    fn u32(&mut self) -> TestResult<u32> {
        let raw = self.take(size_of::<u32>())?;
        let bytes: [u8; 4] = raw
            .try_into()
            .map_err(|_error| String::from("profile CUDA u32 width"))?;
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

#[test]
fn cuda_resident_current_profile_matches_complete_normative_states()
-> TestResult {
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
        profile.memory_words(),
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

fn run_cuda_worker(request: &[u8]) -> TestResult<WorkerBatch> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let python = python_wrapper(root);
    let mut child = Command::new(&python)
        .args(["-m", "accelerator.cuda.profile_run_worker"])
        .current_dir(root)
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
        .write_all(request)
        .map_err(|error| format!("profile CUDA worker stdin: {error}"))?;
    drop(stdin);
    let output = child
        .wait_with_output()
        .map_err(|error| format!("profile CUDA worker wait: {error}"))?;
    if !output.status.success() {
        return Err(format!(
            "profile CUDA worker failed: {}",
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
    let memory_words = usize::try_from(current_profile().memory_words())
        .map_err(|error| format!("profile response memory words: {error}"))?;
    let mut results = Vec::with_capacity(count);
    for _item in 0..count {
        results.push(parse_result(&mut reader, memory_words)?);
    }
    reader.finish()?;
    Ok(Some(results))
}

fn parse_result(
    reader: &mut BinaryReader<'_>,
    memory_words: usize,
) -> TestResult<RunSnapshot> {
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
    let mut memory = Vec::with_capacity(memory_words);
    for _word in 0..memory_words {
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

fn python_wrapper(root: &Path) -> PathBuf {
    root.join(".dependencies/python/3.14.6/Scripts/python-jig.cmd")
}
