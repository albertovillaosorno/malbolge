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

//! Exhaustive bounded correspondence for promoted Malbolge equations.

use malbolge::{
    current_profile, decode_instruction, encrypt_profile_cell, historical_profile, load, Machine,
    Memory, Registers, StepOutcome, Word, MAX_WORD_VALUE, MEMORY_WORDS,
};

const GRAPHICAL_END: u8 = 126;
const GRAPHICAL_START: u8 = 33;
const NO_OPERATION: u8 = b'o';
const TERNARY_RADIX: u32 = 3;
const CLASSIC_TRITS: usize = 10;
const CLASSIC_HIGH_TRIT_WEIGHT: u16 = 19_683;
const TEST_XLAT2: &[u8; 94] = b"5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1C\
B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";
const IO_ROUNDTRIP: &[u8] =
    include_bytes!("../compatibility/specification/spec-io-roundtrip.malbolge");

type TestResult<Value = ()> = Result<Value, String>;

fn word(raw: usize) -> TestResult<Word> {
    let value = u16::try_from(raw).map_err(|error| format!("word conversion failed: {error}"))?;
    Word::new(value).map_err(|error| format!("word construction failed: {error}"))
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
        let pointer = Word::new(raw).map_err(|error| format!("decode pointer failed: {error}"))?;
        if decode_instruction(cell, pointer) == Some(NO_OPERATION) {
            return Ok(pointer);
        }
    }
    Err(format!(
        "no no-op decode position for graphical cell {}",
        cell.value()
    ))
}

const fn independent_classic_rotate(value: u16) -> u16 {
    let quotient = value.div_euclid(3);
    let low_trit = value.rem_euclid(3);
    quotient.saturating_add(low_trit.saturating_mul(CLASSIC_HIGH_TRIT_WEIGHT))
}

const fn independent_classic_rotate_visits(value: u16, visits: usize) -> u16 {
    let mut current = value;
    let mut remaining = visits;
    while remaining > 0 {
        current = independent_classic_rotate(current);
        remaining = remaining.saturating_sub(1);
    }
    current
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
        let mut machine = Machine::with_registers(memory, Vec::new(), registers);
        let outcome = machine
            .step()
            .map_err(|error| format!("encryption step failed: {error}"))?;
        if outcome != StepOutcome::Continued {
            return Err(format!("encryption step did not continue for cell {raw}"));
        }
        let index = usize::from(raw.saturating_sub(GRAPHICAL_START));
        let expected_byte = TEST_XLAT2
            .get(index)
            .copied()
            .ok_or_else(|| String::from("test encryption table escaped domain"))?;
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

fn independent_encryption(cell: u8) -> TestResult<u8> {
    if !(GRAPHICAL_START..=GRAPHICAL_END).contains(&cell) {
        return Err(format!("encryption input is not graphical: {cell}"));
    }
    let index = usize::from(cell.saturating_sub(GRAPHICAL_START));
    TEST_XLAT2
        .get(index)
        .copied()
        .ok_or_else(|| String::from("test encryption table escaped domain"))
}

fn independent_encryption_orbit(start: u8) -> TestResult<Vec<u8>> {
    let mut orbit = Vec::new();
    let mut current = start;
    loop {
        if orbit.contains(&current) {
            if current == start {
                return Ok(orbit);
            }
            return Err(format!(
                "encryption orbit for {start} merged into {current}"
            ));
        }
        orbit.push(current);
        current = independent_encryption(current)?;
    }
}

fn orbit_cell(orbit: &[u8], visits: usize) -> TestResult<u8> {
    if orbit.is_empty() {
        return Err(String::from("cannot index an empty encryption orbit"));
    }
    let index = visits.rem_euclid(orbit.len());
    orbit
        .get(index)
        .copied()
        .ok_or_else(|| String::from("encryption orbit index escaped domain"))
}

fn encryption_cycle_lengths() -> TestResult<Vec<usize>> {
    let mut covered = [false; 94];
    let mut cycle_lengths = Vec::new();
    for start in GRAPHICAL_START..=GRAPHICAL_END {
        let index = usize::from(start.saturating_sub(GRAPHICAL_START));
        if covered
            .get(index)
            .copied()
            .ok_or_else(|| String::from("encryption coverage index escaped domain"))?
        {
            continue;
        }
        let orbit = independent_encryption_orbit(start)?;
        if orbit.is_empty() {
            return Err(format!("empty encryption orbit for {start}"));
        }
        for (visits, cell) in orbit.iter().copied().enumerate() {
            let cell_index = usize::from(cell.saturating_sub(GRAPHICAL_START));
            let seen = covered
                .get_mut(cell_index)
                .ok_or_else(|| String::from("encryption coverage cell escaped domain"))?;
            if *seen {
                return Err(format!("encryption orbit overlaps at {cell}"));
            }
            *seen = true;
            let runtime = encrypt_profile_cell(u32::from(cell))
                .ok_or_else(|| format!("runtime rejected graphical cell {cell}"))?;
            let expected = u32::from(independent_encryption(cell)?);
            if runtime != expected {
                return Err(format!(
                    "encrypt mismatch: {cell} got={runtime} want={expected}"
                ));
            }
            let next = orbit_cell(&orbit, visits.saturating_add(1))?;
            if expected != u32::from(next) {
                return Err(format!(
                    "orbit mismatch: cell={cell} got={expected} want={next}"
                ));
            }
        }
        cycle_lengths.push(orbit.len());
    }
    if covered.iter().any(|seen| !seen) {
        return Err(String::from("encryption orbit partition missed a cell"));
    }
    Ok(cycle_lengths)
}

fn verify_encryption_visit_reduction() -> TestResult {
    for start in GRAPHICAL_START..=GRAPHICAL_END {
        let orbit = independent_encryption_orbit(start)?;
        let period = orbit.len();
        let mut current = start;
        for visits in 1..=period.saturating_mul(2) {
            current = independent_encryption(current)?;
            let reduced = orbit_cell(&orbit, visits)?;
            if current != reduced {
                return Err(format!(
                    "modular orbit mismatch: start={start} visits={visits}"
                ));
            }
        }
    }
    Ok(())
}

#[test]
fn encryption_history_reduces_to_six_modular_orbits() -> TestResult {
    let mut cycle_lengths = encryption_cycle_lengths()?;
    cycle_lengths.sort_unstable();
    if cycle_lengths != [2, 4, 5, 6, 9, 68] {
        return Err(format!(
            "unexpected encryption cycle decomposition: {cycle_lengths:?}"
        ));
    }
    verify_encryption_visit_reduction()
}

#[test]
fn classic_rotation_history_reduces_modulo_ten_trits() -> TestResult {
    for raw in 0u16..=MAX_WORD_VALUE {
        let original = Word::new(raw).map_err(|error| format!("rotation word failed: {error}"))?;
        let mut runtime = original;
        let mut independent = raw;
        for visits in 1..=CLASSIC_TRITS.saturating_mul(2) {
            runtime = runtime.rotate();
            independent = independent_classic_rotate(independent);
            if runtime.value() != independent {
                return Err(format!("rotation mismatch word={raw} visits={visits}"));
            }
            let reduced = independent_classic_rotate_visits(raw, visits.rem_euclid(CLASSIC_TRITS));
            if runtime.value() != reduced {
                return Err(format!(
                    "modular rotation mismatch word={raw} visits={visits}"
                ));
            }
        }
    }
    Ok(())
}

#[test]
fn classic_loader_fill_matches_crazy_recurrence() -> TestResult {
    let memory = load(IO_ROUNDTRIP).map_err(|error| format!("roundtrip load failed: {error}"))?;
    let loaded_words = IO_ROUNDTRIP
        .iter()
        .filter(|byte| !byte.is_ascii_whitespace())
        .count();
    for raw in loaded_words..MEMORY_WORDS {
        let older_address = word(raw.saturating_sub(2))?;
        let previous_address = word(raw.saturating_sub(1))?;
        let address = word(raw)?;
        let older = memory
            .read(older_address)
            .map_err(|error| format!("older recurrence read failed: {error}"))?;
        let previous = memory
            .read(previous_address)
            .map_err(|error| format!("previous recurrence read failed: {error}"))?;
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
        let value = Word::new(raw).map_err(|error| format!("successor word failed: {error}"))?;
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
    let first_outside = u16::try_from(MEMORY_WORDS)
        .map_err(|error| format!("domain ceiling conversion failed: {error}"))?;
    if Word::new(first_outside).is_ok() {
        return Err(String::from("classic domain accepted 59049"));
    }
    Ok(())
}
