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
//   - Instruction-level conformance evidence for classic Malbolge transitions.
// - Must-Not:
//   - Test private implementation details or historical C undefined behavior.
// - Allows:
//   - Inputs: public VM state construction and exact classic instruction cells.
//   - Outputs: deterministic evidence for instruction effects and sequencing.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when one instruction family needs independent fixture ownership.
// - Merge-When:
//   - Merge when instruction-level evidence becomes smaller than conformance.
// - Summary:
//   - Exact public-API tests for every classic Malbolge instruction family.
// - Description:
//   - Verifies operation effects, self-encryption, increments, EOF, and wrap.
// - Usage:
//   - Composed by `tests/vm.rs` into the Cargo VM integration-test target.
// - Defaults:
//   - Every non-halt transition must encrypt and then advance `C` and `D`.
//

//! Instruction-level conformance tests for the normative classic VM.

use malbolge::{Machine, Memory, Registers, StepOutcome, Termination, Word};

use super::{TestResult, check_equal, normalize_result};

#[test]
fn crazy_instruction_updates_accumulator_and_data() -> TestResult {
    let mut machine =
        machine_with_data(b'>', Word::ZERO, Word::ZERO, Vec::new())?;
    check_equal(
        &normalize_result(machine.step())?,
        &StepOutcome::Continued,
        "crazy instruction continues",
    )?;
    let registers = machine.registers();
    check_equal(
        &registers.accumulator.value(),
        &29_524u16,
        "crazy result enters accumulator",
    )?;
    check_equal(
        &registers.code_pointer,
        &Word::from_byte(1),
        "crazy advances code pointer",
    )?;
    check_equal(
        &registers.data_pointer,
        &Word::from_byte(2),
        "crazy advances data pointer",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(Word::from_byte(1)))?.value(),
        &29_524u16,
        "crazy result enters data cell",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(Word::ZERO))?,
        &Word::from_byte(b'L'),
        "crazy instruction cell self-encrypts",
    )
}

#[test]
fn halt_instruction_is_immediate() -> TestResult {
    let mut machine =
        machine_with_data(b'Q', Word::ZERO, Word::from_byte(7), vec![0x41])?;
    let before = machine.registers();
    check_equal(
        &normalize_result(machine.step())?,
        &StepOutcome::Terminated(Termination::HaltInstruction),
        "halt terminates immediately",
    )?;
    check_equal(&machine.registers(), &before, "halt preserves registers")?;
    check_equal(
        &normalize_result(machine.memory_word(Word::ZERO))?,
        &Word::from_byte(b'Q'),
        "halt skips self-encryption",
    )?;
    check_equal(&machine.input_consumed(), &0usize, "halt consumes no input")?;
    check_equal(machine.output(), &[], "halt emits no output")
}

#[test]
fn input_instruction_reads_byte_and_eof() -> TestResult {
    let mut byte_machine =
        machine_with_data(b'c', Word::ZERO, Word::ZERO, vec![0x41])?;
    check_equal(
        &normalize_result(byte_machine.step())?,
        &StepOutcome::Continued,
        "byte input continues",
    )?;
    check_equal(
        &byte_machine.registers().accumulator,
        &Word::from_byte(0x41),
        "input byte enters accumulator",
    )?;
    check_equal(
        &byte_machine.input_consumed(),
        &1usize,
        "byte input advances cursor",
    )?;
    check_equal(
        &normalize_result(byte_machine.memory_word(Word::ZERO))?,
        &Word::from_byte(b'V'),
        "input instruction self-encrypts",
    )?;

    let mut eof_machine =
        machine_with_data(b'c', Word::ZERO, Word::ZERO, Vec::new())?;
    check_equal(
        &normalize_result(eof_machine.step())?,
        &StepOutcome::Continued,
        "EOF input continues",
    )?;
    check_equal(
        &eof_machine.registers().accumulator,
        &Word::MAX,
        "EOF maps to classic maximum word",
    )?;
    check_equal(
        &eof_machine.input_consumed(),
        &0usize,
        "EOF does not advance byte cursor",
    )
}

#[test]
fn jump_code_encrypts_resulting_code_pointer() -> TestResult {
    let mut memory = Memory::filled(Word::ZERO);
    normalize_result(memory.replace(Word::ZERO, Word::from_byte(b'b')))?;
    normalize_result(memory.replace(Word::from_byte(1), Word::from_byte(2)))?;
    normalize_result(
        memory.replace(Word::from_byte(2), Word::from_byte(b'D')),
    )?;
    let registers = Registers {
        accumulator: Word::from_byte(7),
        code_pointer: Word::ZERO,
        data_pointer: Word::from_byte(1),
    };
    let mut machine = Machine::with_registers(memory, Vec::new(), registers);
    check_equal(
        &normalize_result(machine.step())?,
        &StepOutcome::Continued,
        "code jump continues",
    )?;
    check_equal(
        &machine.registers().code_pointer,
        &Word::from_byte(3),
        "code jump increments resulting code pointer",
    )?;
    check_equal(
        &machine.registers().data_pointer,
        &Word::from_byte(2),
        "code jump increments data pointer",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(Word::ZERO))?,
        &Word::from_byte(b'b'),
        "code jump leaves original instruction cell untouched",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(Word::from_byte(2)))?,
        &Word::from_byte(b'!'),
        "code jump encrypts the resulting code-pointer cell",
    )
}

#[test]
fn jump_data_replaces_data_pointer_before_increment() -> TestResult {
    let mut machine = machine_with_data(
        b'(',
        Word::from_byte(5),
        Word::from_byte(7),
        Vec::new(),
    )?;
    check_equal(
        &normalize_result(machine.step())?,
        &StepOutcome::Continued,
        "data jump continues",
    )?;
    check_equal(
        &machine.registers().data_pointer,
        &Word::from_byte(6),
        "data jump increments loaded pointer",
    )?;
    check_equal(
        &machine.registers().code_pointer,
        &Word::from_byte(1),
        "data jump advances code pointer",
    )?;
    check_equal(
        &machine.registers().accumulator,
        &Word::from_byte(7),
        "data jump preserves accumulator",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(Word::ZERO))?,
        &Word::from_byte(b'y'),
        "data jump instruction self-encrypts",
    )
}

fn machine_with_data(
    instruction_cell: u8,
    data: Word,
    accumulator: Word,
    input: Vec<u8>,
) -> TestResult<Machine> {
    let mut memory = Memory::filled(Word::ZERO);
    normalize_result(
        memory.replace(Word::ZERO, Word::from_byte(instruction_cell)),
    )?;
    normalize_result(memory.replace(Word::from_byte(1), data))?;
    Ok(Machine::with_registers(memory, input, Registers {
        accumulator,
        code_pointer: Word::ZERO,
        data_pointer: Word::from_byte(1),
    }))
}

#[test]
fn noop_instruction_only_encrypts_and_advances() -> TestResult {
    let mut machine = machine_with_data(
        b'D',
        Word::from_byte(9),
        Word::from_byte(7),
        Vec::new(),
    )?;
    check_equal(
        &normalize_result(machine.step())?,
        &StepOutcome::Continued,
        "no-op continues",
    )?;
    check_equal(
        &machine.registers(),
        &Registers {
            accumulator: Word::from_byte(7),
            code_pointer: Word::from_byte(1),
            data_pointer: Word::from_byte(2),
        },
        "no-op only advances pointers",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(Word::ZERO))?,
        &Word::from_byte(b'!'),
        "no-op instruction self-encrypts",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(Word::from_byte(1)))?,
        &Word::from_byte(9),
        "no-op preserves data cell",
    )
}

#[test]
fn output_instruction_emits_low_byte() -> TestResult {
    let mut machine =
        machine_with_data(b'u', Word::ZERO, Word::MAX, Vec::new())?;
    check_equal(
        &normalize_result(machine.step())?,
        &StepOutcome::Continued,
        "output continues",
    )?;
    check_equal(
        machine.output(),
        &[0xa8],
        "output emits accumulator modulo 256",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(Word::ZERO))?,
        &Word::from_byte(b'o'),
        "output instruction self-encrypts",
    )
}

#[test]
fn rotate_instruction_updates_accumulator_and_data() -> TestResult {
    let mut machine =
        machine_with_data(b'\'', Word::from_byte(1), Word::ZERO, Vec::new())?;
    check_equal(
        &normalize_result(machine.step())?,
        &StepOutcome::Continued,
        "rotate continues",
    )?;
    check_equal(
        &machine.registers().accumulator.value(),
        &19_683u16,
        "rotate result enters accumulator",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(Word::from_byte(1)))?.value(),
        &19_683u16,
        "rotate result enters data cell",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(Word::ZERO))?,
        &Word::from_byte(b't'),
        "rotate instruction self-encrypts",
    )
}

#[test]
fn word_addresses_wrap_after_post_instruction_increment() -> TestResult {
    let mut memory = Memory::filled(Word::ZERO);
    normalize_result(memory.replace(Word::MAX, Word::from_byte(b'4')))?;
    let registers = Registers {
        accumulator: Word::from_byte(7),
        code_pointer: Word::MAX,
        data_pointer: Word::MAX,
    };
    let mut machine = Machine::with_registers(memory, Vec::new(), registers);
    check_equal(
        &normalize_result(machine.step())?,
        &StepOutcome::Continued,
        "maximum-address no-op continues",
    )?;
    check_equal(
        &machine.registers(),
        &Registers {
            accumulator: Word::from_byte(7),
            code_pointer: Word::ZERO,
            data_pointer: Word::ZERO,
        },
        "post-instruction pointers wrap at 59048",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(Word::MAX))?,
        &Word::from_byte(b'H'),
        "maximum-address instruction self-encrypts before wrap",
    )
}
