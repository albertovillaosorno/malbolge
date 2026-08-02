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
//   - Determinism and isolation evidence for independent VM batch execution.
// - Must-Not:
//   - Treat host scheduling as guest semantics or inspect private batch state.
// - Allows:
//   - Inputs: public batch/execution APIs and normative specification fixtures.
//   - Outputs:
//   - Equality assertions across sequential and explicit host-worker execution.
//   - Side effects:
//   - Test-process threads and memory only.
// - Split-When:
//   - Split when accelerator batch execution requires independent fixtures.
// - Merge-When:
//   - Merge when another VM test owns identical batch-isolation obligations.
// - Summary:
//   - Proves input ordering, state isolation, and per-item failure identity.
// - Description:
//   - Hashes full final memory to compare sequential and parallel machine
//   - state.
// - Usage:
//   - Runs under the Cargo VM integration-test composition target.
// - Defaults:
//   - Worker-count changes must never alter an input-ordered result snapshot.
//

//! Deterministic batch execution and per-instance isolation tests.

use malbolge::{
    BatchError, BatchRequest, BatchResult, ExecutionError, ExecutionErrorKind,
    ExecutionMachine, ExecutionMode, LoadError, MAX_WORD_VALUE, MachineError,
    Memory, Registers, RunOutcome, Termination, Word, execute_batch,
    execute_batch_parallel,
};

use super::{TestResult, check_equal, normalize_result};

const FNV_OFFSET: u64 = 14_695_981_039_346_656_037;
const FNV_PRIME: u64 = 1_099_511_628_211;
const IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/spec-io-roundtrip.malbolge");

#[derive(Debug, Eq, PartialEq)]
struct ResultSnapshot {
    error: Option<ExecutionError>,
    input_consumed: Option<usize>,
    machine_present: bool,
    memory_hash: Option<u64>,
    mode: Option<ExecutionMode>,
    outcome: Option<RunOutcome>,
    output: Option<Vec<u8>>,
    registers: Option<Registers>,
    termination: Option<Termination>,
}

fn batch_requests() -> TestResult<Vec<BatchRequest>> {
    let rejected_machine = invalid_jump_machine()?;
    Ok(vec![
        BatchRequest::from_source(
            IO_ROUNDTRIP.to_vec(),
            vec![0x11],
            ExecutionMode::Specification,
            16,
        ),
        BatchRequest::from_source(
            b"D".to_vec(),
            Vec::new(),
            ExecutionMode::Specification,
            16,
        ),
        BatchRequest::from_source(
            IO_ROUNDTRIP.to_vec(),
            vec![0xa7],
            ExecutionMode::Specification,
            16,
        ),
        BatchRequest::from_machine(rejected_machine, 1),
    ])
}

fn hash_machine_memory(machine: &ExecutionMachine) -> TestResult<u64> {
    let mut hash = FNV_OFFSET;
    for raw in 0..=MAX_WORD_VALUE {
        let address = normalize_result(Word::new(raw))?;
        let value = normalize_result(machine.memory_word(address))?;
        for byte in value.value().to_le_bytes() {
            hash = (hash ^ u64::from(byte)).wrapping_mul(FNV_PRIME);
        }
    }
    Ok(hash)
}

fn invalid_jump_machine() -> TestResult<ExecutionMachine> {
    let mut memory = Memory::filled(Word::ZERO);
    normalize_result(memory.replace(Word::ZERO, Word::from_byte(b'b')))?;
    normalize_result(memory.replace(Word::from_byte(1), Word::from_byte(2)))?;
    let registers = Registers {
        accumulator: Word::from_byte(7),
        code_pointer: Word::ZERO,
        data_pointer: Word::from_byte(1),
    };
    normalize_result(ExecutionMachine::from_state(
        memory,
        Vec::new(),
        registers,
        ExecutionMode::Specification,
    ))
}

fn result_snapshots(
    results: &[BatchResult],
) -> TestResult<Vec<ResultSnapshot>> {
    results.iter().map(snapshot).collect()
}

fn snapshot(result: &BatchResult) -> TestResult<ResultSnapshot> {
    let maybe_machine = result.machine();
    let memory_hash = match maybe_machine {
        Some(execution_machine) => {
            Some(hash_machine_memory(execution_machine)?)
        },
        None => None,
    };
    Ok(ResultSnapshot {
        error: result.error(),
        input_consumed: maybe_machine.map(ExecutionMachine::input_consumed),
        machine_present: maybe_machine.is_some(),
        memory_hash,
        mode: maybe_machine.map(ExecutionMachine::mode),
        outcome: result.outcome(),
        output: maybe_machine.map(|item| item.output().to_vec()),
        registers: maybe_machine.map(ExecutionMachine::registers),
        termination: maybe_machine.and_then(ExecutionMachine::termination),
    })
}

#[test]
fn batch_request_identity_is_explicit() -> TestResult {
    let source = BatchRequest::from_source(
        IO_ROUNDTRIP.to_vec(),
        vec![0x31],
        ExecutionMode::Specification,
        19,
    );
    check_equal(
        &source.mode(),
        &ExecutionMode::Specification,
        "source request mode",
    )?;
    check_equal(&source.step_budget(), &19usize, "source request budget")?;

    let machine = invalid_jump_machine()?;
    let machine_request = BatchRequest::from_machine(machine, 3);
    check_equal(
        &machine_request.mode(),
        &ExecutionMode::Specification,
        "machine request mode",
    )?;
    check_equal(
        &machine_request.step_budget(),
        &3usize,
        "machine request budget",
    )
}

#[test]
fn parallel_batch_matches_sequential_for_multiple_worker_counts() -> TestResult
{
    let requests = batch_requests()?;
    let sequential = result_snapshots(&execute_batch(requests.clone()))?;
    for worker_count in [1usize, 2, 8] {
        let parallel = normalize_result(execute_batch_parallel(
            requests.clone(),
            worker_count,
        ))?;
        check_equal(
            &result_snapshots(&parallel)?,
            &sequential,
            "parallel batch equals sequential baseline",
        )?;
    }
    Ok(())
}

#[test]
fn per_item_failures_do_not_abort_or_contaminate_neighbors() -> TestResult {
    let results = execute_batch(batch_requests()?);
    let first = results
        .first()
        .ok_or_else(|| String::from("missing first batch result"))?;
    let second = results
        .get(1)
        .ok_or_else(|| String::from("missing load-rejection result"))?;
    let third = results
        .get(2)
        .ok_or_else(|| String::from("missing third batch result"))?;
    let fourth = results
        .get(3)
        .ok_or_else(|| String::from("missing runtime-rejection result"))?;

    check_equal(
        &first.machine().map(|machine| machine.output().to_vec()),
        &Some(vec![0x11]),
        "first output remains isolated",
    )?;
    check_equal(
        &second.error().map(ExecutionError::kind),
        &Some(ExecutionErrorKind::Load(
            LoadError::InsufficientRecurrenceBase,
        )),
        "invalid source rejects only its item",
    )?;
    check_equal(
        &second.machine().is_none(),
        &true,
        "load rejection has no machine",
    )?;
    check_equal(
        &third.machine().map(|machine| machine.output().to_vec()),
        &Some(vec![0xa7]),
        "later output is unaffected by earlier rejection",
    )?;
    check_equal(
        &fourth.error().map(ExecutionError::kind),
        &Some(ExecutionErrorKind::Machine(
            MachineError::InvalidEncryptionTarget {
                pointer: Word::from_byte(2),
                value: Word::ZERO,
            },
        )),
        "runtime rejection keeps exact machine diagnostic",
    )?;
    let rejected_machine = fourth
        .machine()
        .ok_or_else(|| String::from("runtime rejection lost machine state"))?;
    check_equal(
        &rejected_machine.registers(),
        &Registers {
            accumulator: Word::from_byte(7),
            code_pointer: Word::ZERO,
            data_pointer: Word::from_byte(1),
        },
        "runtime rejection preserves atomic registers",
    )
}

#[test]
fn parallel_batch_validates_worker_count_and_empty_input() -> TestResult {
    let Err(error) = execute_batch_parallel(Vec::new(), 0) else {
        return Err(String::from("zero-worker batch unexpectedly succeeded"));
    };
    check_equal(&error, &BatchError::ZeroWorkers, "zero workers fail closed")?;
    let empty = normalize_result(execute_batch_parallel(Vec::new(), 4))?;
    check_equal(&empty.len(), &0usize, "empty batch succeeds with workers")
}
