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
//   - Executable conformance evidence for the first safe-Rust classic VM slice.
// - Must-Not:
//   - Reproduce undefined historical C behavior or duplicate production
//   - internals.
// - Allows:
//   - Inputs: public VM APIs and classic interpreter-authority fixtures.
//   - Outputs: deterministic assertions over loading, words, state, and byte
//   - I/O.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when one semantic family requires independently maintained
//   - fixtures.
// - Merge-When:
//   - Merge when another VM test owns the same public conformance obligation.
// - Summary:
//   - Verifies word primitives, loader boundaries, I/O, and atomic transitions.
// - Description:
//   - Exercises interpreter-authority behavior rather than internals.
// - Usage:
//   - Runs under the `vm` Cargo integration-test composition target.
// - Defaults:
//   - Any mismatch with the active interpreter fixture is a hard test
//   - failure.
//

//! Conformance tests for the first safe-Rust classic VM implementation slice.

use malbolge::{
    InterpreterUndefinedBehavior, LoadError, Machine, MachineError, Memory,
    Registers, StepOutcome, Termination, Word, load, profile_cell_is_graphical,
};

use super::{TestResult, check_equal, normalize_result};

const IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/interpreter-io-roundtrip.malbolge");

#[test]
fn invalid_jump_encryption_target_is_atomic() -> TestResult {
    let mut memory = Memory::filled(Word::ZERO);
    normalize_result(memory.replace(Word::ZERO, Word::from_byte(b'b')))?;
    normalize_result(memory.replace(Word::from_byte(1), Word::from_byte(2)))?;
    let registers = Registers {
        accumulator: Word::from_byte(7),
        code_pointer: Word::ZERO,
        data_pointer: Word::from_byte(1),
    };
    let mut machine = Machine::with_registers(memory, vec![0x44], registers);
    let before_registers = machine.registers();
    let before_input = machine.input_consumed();
    let before_target =
        normalize_result(machine.memory_word(Word::from_byte(2)))?;
    let error = machine.step();
    check_equal(
        &error,
        &Err(MachineError::UnsupportedInterpreterBehavior(
            InterpreterUndefinedBehavior::InvalidSelfEncryptionTarget {
                pointer: Word::from_byte(2),
                value: Word::ZERO,
            },
        )),
        "jump rejects non-graphical encryption target",
    )?;
    check_equal(
        &machine.registers(),
        &before_registers,
        "failed step preserves registers",
    )?;
    check_equal(
        &machine.input_consumed(),
        &before_input,
        "failed step preserves input",
    )?;
    check_equal(machine.output(), &[], "failed step preserves output")?;
    check_equal(
        &normalize_result(machine.memory_word(Word::from_byte(2)))?,
        &before_target,
        "target remains unchanged",
    )
}

#[test]
fn loader_enforces_recurrence_base_and_accepts_roundtrip_fixture() -> TestResult
{
    check_equal(
        &load(b""),
        &Err(LoadError::InsufficientRecurrenceBase),
        "empty source is rejected",
    )?;
    check_equal(
        &load(b"D"),
        &Err(LoadError::InsufficientRecurrenceBase),
        "one-word source is rejected",
    )?;
    let memory = normalize_result(load(IO_ROUNDTRIP))?;
    check_equal(
        &normalize_result(memory.read(Word::ZERO))?,
        &Word::from_byte(b'u'),
        "first interpreter-roundtrip word",
    )?;
    check_equal(
        &normalize_result(memory.read(Word::from_byte(1)))?,
        &Word::from_byte(b'b'),
        "second interpreter-roundtrip word",
    )?;
    check_equal(
        &normalize_result(memory.read(Word::from_byte(2)))?,
        &Word::from_byte(b'O'),
        "third loaded word",
    )
}

#[test]
fn profile_graphical_cell_boundary_is_public_and_exact() -> TestResult {
    check_equal(
        &profile_cell_is_graphical(32),
        &false,
        "cell below graphical ASCII is rejected",
    )?;
    check_equal(
        &profile_cell_is_graphical(33),
        &true,
        "graphical ASCII lower bound is admitted",
    )?;
    check_equal(
        &profile_cell_is_graphical(126),
        &true,
        "graphical ASCII upper bound is admitted",
    )?;
    check_equal(
        &profile_cell_is_graphical(127),
        &false,
        "cell above graphical ASCII is rejected",
    )
}

#[test]
fn non_graphical_current_cell_does_not_progress() -> TestResult {
    let memory = Memory::filled(Word::ZERO);
    let mut machine = Machine::new(memory, Vec::new());
    let before = machine.registers();
    let outcome = normalize_result(machine.step())?;
    check_equal(
        &outcome,
        &StepOutcome::Continued,
        "non-graphical current cell does not progress",
    )?;
    check_equal(
        &machine.registers(),
        &before,
        "termination does not advance registers",
    )
}

#[test]
fn roundtrip_fixture_uses_interpreter_byte_io() -> TestResult {
    let mut machine =
        normalize_result(Machine::from_source(IO_ROUNDTRIP, vec![0x41]))?;
    let termination = run_to_termination(&mut machine)?;
    check_equal(&termination, &Termination::HaltInstruction, "fixture halts")?;
    check_equal(
        machine.output(),
        &[0x41],
        "fixture emits consumed input byte",
    )?;
    check_equal(
        &machine.input_consumed(),
        &1usize,
        "fixture consumes one input byte",
    )
}

fn run_to_termination(machine: &mut Machine) -> TestResult<Termination> {
    for _step in 0..16u8 {
        match normalize_result(machine.step())? {
            StepOutcome::Continued => {},
            StepOutcome::Terminated(reason) => return Ok(reason),
        }
    }
    Err(String::from(
        "VM did not terminate within the conformance step budget",
    ))
}

#[test]
fn word_rotation_and_crazy_match_normative_vectors() -> TestResult {
    check_equal(
        &Word::from_byte(1).rotate().value(),
        &19_683u16,
        "rotate one low trit",
    )?;
    check_equal(
        &Word::from_byte(3).rotate().value(),
        &1u16,
        "rotate ternary ten",
    )?;
    check_equal(&Word::MAX.rotate(), &Word::MAX, "rotate all-two word")?;
    check_equal(
        &Word::ZERO.crazy(Word::ZERO).value(),
        &29_524u16,
        "crazy all-zero words",
    )?;
    check_equal(
        &Word::MAX.crazy(Word::ZERO),
        &Word::MAX,
        "crazy all-two data",
    )?;
    check_equal(
        &Word::ZERO.crazy(Word::MAX),
        &Word::ZERO,
        "crazy all-two accumulator",
    )?;
    check_equal(
        &Word::MAX.low_byte(),
        &0xa8u8,
        "output is accumulator modulo 256",
    )
}
