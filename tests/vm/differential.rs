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
//   - Durable differential fingerprint between independent Rust and C VMs.
// - Must-Not:
//   - Call C implementation code from Rust or share transition internals.
// - Allows:
//   - Inputs: public Rust VM API and interpreter-derived fingerprint
//   - protocol.
//   - Outputs: deterministic equality evidence against the independent C VM.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when fingerprint families require independent lifecycle evidence.
// - Merge-When:
//   - Merge when one independent VM owns the same differential protocol.
// - Summary:
//   - Recomputes the independent C semantic signature through the Rust VM.
// - Description:
//   - Hashes interpreter-authority behavior through only the public Rust API.
// - Usage:
//   - Run by the Cargo VM integration-test target.
// - Defaults:
//   - Uses the fixed classic-profile fingerprint protocol and no C FFI.
//

//! Differential semantic fingerprint shared with the independent pure-C VM.

use malbolge::{
    InterpreterUndefinedBehavior, MAX_WORD_VALUE, Machine, MachineError,
    Memory, Registers, RunOutcome, StepOutcome, Termination, Word, load,
};

use super::{TestResult, check_equal, normalize_result};

const C_VM_SEMANTIC_SIGNATURE: u64 = 0xa9da_bd8f_c51d_13c9;
const FNV_OFFSET: u64 = 14_695_981_039_346_656_037;
const FNV_PRIME: u64 = 1_099_511_628_211;
const IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/interpreter-io-roundtrip.malbolge");
const SIGNATURE_HALT: u8 = 0xb1;
const SIGNATURE_INCREMENT: u32 = 23;
const SIGNATURE_INVALID_ENCRYPTION: u8 = 0xc1;
const SIGNATURE_MULTIPLIER: u32 = 17;
const SIGNATURE_NON_GRAPHICAL: u8 = 0xb2;
const SIGNATURE_CONTINUED: u8 = 0xa2;
const SIGNATURE_TERMINATED: u8 = 0xa1;

fn hash_byte(hash: u64, value: u8) -> u64 {
    (hash ^ u64::from(value)).wrapping_mul(FNV_PRIME)
}

fn hash_loaded_memory(mut hash: u64, memory: &Memory) -> TestResult<u64> {
    for raw_value in 0..=MAX_WORD_VALUE {
        let address = normalize_result(Word::new(raw_value))?;
        let value = normalize_result(memory.read(address))?;
        hash = hash_word(hash, value);
    }
    Ok(hash)
}

fn hash_non_graphical_non_progress(mut hash: u64) -> TestResult<u64> {
    let memory = Memory::filled(Word::ZERO);
    let mut machine = Machine::new(memory, Vec::new());
    let outcome = normalize_result(machine.step())?;
    check_equal(
        &outcome,
        &StepOutcome::Continued,
        "signature non-graphical non-progress",
    )?;
    hash = hash_byte(hash, SIGNATURE_CONTINUED);
    hash = hash_byte(hash, SIGNATURE_NON_GRAPHICAL);
    Ok(hash_registers(hash, machine.registers()))
}

fn hash_registers(mut hash: u64, registers: Registers) -> u64 {
    hash = hash_word(hash, registers.accumulator);
    hash = hash_word(hash, registers.code_pointer);
    hash_word(hash, registers.data_pointer)
}

fn hash_rejected_jump(mut hash: u64) -> TestResult<u64> {
    let mut memory = Memory::filled(Word::ZERO);
    normalize_result(memory.replace(Word::ZERO, Word::from_byte(b'b')))?;
    normalize_result(memory.replace(Word::from_byte(1), Word::from_byte(2)))?;
    let registers = Registers {
        accumulator: Word::from_byte(7),
        code_pointer: Word::ZERO,
        data_pointer: Word::from_byte(1),
    };
    let mut machine = Machine::with_registers(memory, Vec::new(), registers);
    let result = machine.step();
    check_equal(
        &result,
        &Err(MachineError::UnsupportedInterpreterBehavior(
            InterpreterUndefinedBehavior::InvalidSelfEncryptionTarget {
                pointer: Word::from_byte(2),
                value: Word::ZERO,
            },
        )),
        "signature rejected jump",
    )?;
    hash = hash_byte(hash, SIGNATURE_INVALID_ENCRYPTION);
    hash = hash_word(hash, Word::from_byte(2));
    hash = hash_word(hash, Word::ZERO);
    hash = hash_registers(hash, machine.registers());
    let instruction = normalize_result(machine.memory_word(Word::ZERO))?;
    Ok(hash_word(hash, instruction))
}

fn hash_roundtrip_execution(mut hash: u64) -> TestResult<u64> {
    let mut machine =
        normalize_result(Machine::from_source(IO_ROUNDTRIP, vec![0x41]))?;
    let outcome = normalize_result(machine.run(16))?;
    let RunOutcome::Terminated { reason, steps } = outcome else {
        return Err(format!(
            "roundtrip signature did not terminate: {outcome:?}"
        ));
    };
    check_equal(
        &reason,
        &Termination::HaltInstruction,
        "signature roundtrip halt reason",
    )?;
    hash = hash_byte(hash, SIGNATURE_TERMINATED);
    hash = hash_byte(hash, SIGNATURE_HALT);
    hash = hash_registers(hash, machine.registers());
    let input_consumed = u16::try_from(machine.input_consumed())
        .map_err(|error| format!("input cursor conversion failed: {error}"))?;
    hash = hash_word(hash, normalize_result(Word::new(input_consumed))?);
    let output_length = u8::try_from(machine.output().len())
        .map_err(|error| format!("output length conversion failed: {error}"))?;
    hash = hash_byte(hash, output_length);
    let [output_byte] = machine.output() else {
        return Err(format!(
            "roundtrip signature expected one output byte, got {:?}",
            machine.output()
        ));
    };
    hash = hash_byte(hash, *output_byte);
    let step_byte = u8::try_from(steps)
        .map_err(|error| format!("step count conversion failed: {error}"))?;
    Ok(hash_byte(hash, step_byte))
}

fn hash_word(hash: u64, value: Word) -> u64 {
    let [low, high] = value.value().to_le_bytes();
    hash_byte(hash_byte(hash, low), high)
}

#[test]
fn independent_c_signature_matches_rust_vm() -> TestResult {
    let observed = rust_semantic_signature()?;
    check_equal(
        &observed,
        &C_VM_SEMANTIC_SIGNATURE,
        "Rust VM matches independent C semantic signature",
    )
}

fn rust_semantic_signature() -> TestResult<u64> {
    let mut hash = FNV_OFFSET;
    for raw_value in 0..=MAX_WORD_VALUE {
        let value = normalize_result(Word::new(raw_value))?;
        let raw_u32 = u32::from(raw_value);
        let paired_raw = raw_u32
            .saturating_mul(SIGNATURE_MULTIPLIER)
            .saturating_add(SIGNATURE_INCREMENT)
            .rem_euclid(59_049);
        let paired_u16 = u16::try_from(paired_raw).map_err(|error| {
            format!("paired word conversion failed: {error}")
        })?;
        let paired = normalize_result(Word::new(paired_u16))?;
        hash = hash_word(hash, value.rotate());
        hash = hash_word(hash, value.crazy(paired));
    }
    let memory = normalize_result(load(IO_ROUNDTRIP))?;
    hash = hash_loaded_memory(hash, &memory)?;
    hash = hash_roundtrip_execution(hash)?;
    hash = hash_rejected_jump(hash)?;
    hash_non_graphical_non_progress(hash)
}
