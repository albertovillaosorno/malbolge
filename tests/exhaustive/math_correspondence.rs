// File:
//   - math_correspondence.rs
// Path:
//   - tests/exhaustive/math_correspondence.rs
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
//   - Exhaustive bounded correspondence for core mathematical equations.
// - Must-Not:
//   - Reuse private runtime helpers or claim proof outside declared domains.
// - Allows:
//   - Inputs: public VM/profile APIs and immutable specification tables.
//   - Outputs: exhaustive domain, successor, encryption, recurrence evidence.
//   - Side effects: test-process CPU and memory only.
// - Split-When:
//   - Split when another mathematical model requires a distinct bounded domain.
// - Merge-When:
//   - Merge when another suite owns identical equation correspondence evidence.
// - Summary:
//   - Checks core classic/profile equations against public executable behavior.
// - Description:
//   - Exhausts classic words/encryption and one full recurrence memory image.
// - Usage:
//   - Composed by `tests/property_verification.rs`.
// - Defaults:
//   - Any equation/implementation mismatch is a deterministic test failure.
//
// Related documents:
// - math/specification/correspondence.toml
// - math/specification/malbolge-1998.tex
// - math/specification/profile-model.tex
//
// Large file:
//   - false

//! Exhaustive bounded correspondence for promoted Malbolge equations.

use malbolge::{
    MAX_WORD_VALUE, MEMORY_WORDS, Machine, Memory, Registers, StepOutcome,
    Word, current_profile, decode_instruction, historical_profile, load,
};

const GRAPHICAL_END: u8 = 126;
const GRAPHICAL_START: u8 = 33;
const NO_OPERATION: u8 = b'o';
const TERNARY_RADIX: u32 = 3;
const TEST_XLAT2: &[u8; 94] =
    b"5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1C\
B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";
const IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/spec-io-roundtrip.malbolge");

type TestResult<Value = ()> = Result<Value, String>;

fn word(raw: usize) -> TestResult<Word> {
    let value = u16::try_from(raw)
        .map_err(|error| format!("word conversion failed: {error}"))?;
    Word::new(value)
        .map_err(|error| format!("word construction failed: {error}"))
}

const fn profile_modulus(trits: u8) -> u32 {
    let mut value = 1u32;
    let mut index = 0u8;
    while index < trits {
        value = value.saturating_mul(TERNARY_RADIX);
        index = index.saturating_add(1);
    }
    value
}

fn noop_pointer(cell: Word) -> TestResult<Word> {
    for raw in 0u16..94u16 {
        let pointer = Word::new(raw)
            .map_err(|error| format!("decode pointer failed: {error}"))?;
        if decode_instruction(cell, pointer) == Some(NO_OPERATION) {
            return Ok(pointer);
        }
    }
    Err(format!(
        "no no-op decode position for graphical cell {}",
        cell.value()
    ))
}

#[test]
fn canonical_profile_domains_match_power_of_three() -> TestResult {
    for profile in [historical_profile(), current_profile()] {
        let modulus = profile_modulus(profile.word_trits());
        if profile.word_modulus() != modulus {
            return Err(format!("{} word modulus mismatch", profile.id()));
        }
        if profile.memory_words() != modulus {
            return Err(format!("{} memory domain mismatch", profile.id()));
        }
        if profile.eof_word() != modulus.saturating_sub(1) {
            return Err(format!("{} EOF domain mismatch", profile.id()));
        }
    }
    Ok(())
}

#[test]
fn classic_encryption_matches_every_graphical_cell() -> TestResult {
    for raw in GRAPHICAL_START..=GRAPHICAL_END {
        let cell = Word::from_byte(raw);
        let pointer = noop_pointer(cell)?;
        let mut memory = Memory::filled(Word::from_byte(b'!'));
        memory
            .replace(pointer, cell)
            .map_err(|error| format!("memory setup failed: {error}"))?;
        let registers = Registers {
            accumulator: Word::ZERO,
            code_pointer: pointer,
            data_pointer: Word::ZERO,
        };
        let mut machine =
            Machine::with_registers(memory, Vec::new(), registers);
        let outcome = machine
            .step()
            .map_err(|error| format!("encryption step failed: {error}"))?;
        if outcome != StepOutcome::Continued {
            return Err(format!(
                "encryption step did not continue for cell {raw}"
            ));
        }
        let index = usize::from(raw.saturating_sub(GRAPHICAL_START));
        let expected_byte =
            TEST_XLAT2.get(index).copied().ok_or_else(|| {
                String::from("test encryption table escaped domain")
            })?;
        let observed = machine
            .memory_word(pointer)
            .map_err(|error| format!("encrypted read failed: {error}"))?;
        if observed != Word::from_byte(expected_byte) {
            let observed_value = observed.value();
            return Err(format!(
                "encrypt cell={raw}: got={observed_value} want={expected_byte}"
            ));
        }
    }
    Ok(())
}

#[test]
fn classic_loader_fill_matches_crazy_recurrence() -> TestResult {
    let memory = load(IO_ROUNDTRIP)
        .map_err(|error| format!("roundtrip load failed: {error}"))?;
    let loaded_words = IO_ROUNDTRIP
        .iter()
        .filter(|byte| !byte.is_ascii_whitespace())
        .count();
    for raw in loaded_words..MEMORY_WORDS {
        let older_address = word(raw.saturating_sub(2))?;
        let previous_address = word(raw.saturating_sub(1))?;
        let address = word(raw)?;
        let older = memory.read(older_address).map_err(|error| {
            format!("older recurrence read failed: {error}")
        })?;
        let previous = memory.read(previous_address).map_err(|error| {
            format!("previous recurrence read failed: {error}")
        })?;
        let observed = memory
            .read(address)
            .map_err(|error| format!("recurrence read failed: {error}"))?;
        let expected = older.crazy(previous);
        if observed != expected {
            return Err(format!("loader recurrence mismatch address={raw}"));
        }
    }
    Ok(())
}

#[test]
fn classic_successor_matches_modular_equation() -> TestResult {
    for raw in 0u16..=MAX_WORD_VALUE {
        let value = Word::new(raw)
            .map_err(|error| format!("successor word failed: {error}"))?;
        let expected = if raw == MAX_WORD_VALUE {
            0
        } else {
            raw.saturating_add(1)
        };
        if value.successor().value() != expected {
            return Err(format!("successor mismatch word={raw}"));
        }
    }
    Ok(())
}

#[test]
fn classic_word_domain_matches_ten_trit_modulus() -> TestResult {
    for raw in 0u16..=MAX_WORD_VALUE {
        if Word::new(raw).is_err() {
            return Err(format!("classic domain rejected word={raw}"));
        }
    }
    let first_outside = u16::try_from(MEMORY_WORDS).map_err(|error| {
        format!("domain ceiling conversion failed: {error}")
    })?;
    if Word::new(first_outside).is_ok() {
        return Err(String::from("classic domain accepted 59049"));
    }
    Ok(())
}
