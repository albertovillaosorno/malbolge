// File:
//   - tables.rs
// Path:
//   - tests/vm/tables.rs
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
//   - Independent equivalence evidence for classic VM word lookup tables.
// - Must-Not:
//   - Reuse generated table data or production scalar fallback helpers.
// - Allows:
//   - Inputs: public classic Word API and independent normative formulas.
//   - Outputs: exhaustive rotate, crazy, and positional-decode equivalence.
//   - Side effects: test-process CPU and memory only.
// - Split-When:
//   - Split when another target profile requires independent table evidence.
// - Merge-When:
//   - Merge when another VM test owns the same lookup-table equivalence proof.
// - Summary:
//   - Proves optimized word tables equal independent scalar ternary
//     definitions.
// - Description:
//   - Covers every rotate/crazy entry and every graphical decode position.
// - Usage:
//   - Runs under the Cargo VM integration-test composition target.
// - Defaults:
//   - Any optimized/scalar mismatch is a hard deterministic test failure.
//
// Related documents:
// - docs/technical/runtime/vm/cpu-vm-table-optimization.md
// - docs/technical/specification/malbolge-1998.md
//
// Large file:
//   - false
//

//! Independent scalar equivalence tests for optimized classic word operations.

use malbolge::{MAX_WORD_VALUE, Word, decode_instruction};

use super::{TestResult, check_equal, normalize_result};

const CHUNK_VALUES: u16 = 243;
const DECODE_TABLE_LEN: usize = 94;
const GRAPHICAL_START: u16 = 33;
const TEST_XLAT1: &[u8; DECODE_TABLE_LEN] =
    b"+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI\
.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha";
const ROTATE_HIGH_TRIT_WEIGHT: u16 = 19_683;
const TRIT_COUNT: u8 = 10;

fn crazy_scalar(data: Word, accumulator: Word) -> TestResult<Word> {
    let mut remaining_data = data.value();
    let mut remaining_accumulator = accumulator.value();
    let mut result = 0u16;
    let mut place = 1u16;
    let mut trit = 0u8;
    while trit < TRIT_COUNT {
        let output = crazy_trit_scalar(
            remaining_data.rem_euclid(3),
            remaining_accumulator.rem_euclid(3),
        );
        result = result.saturating_add(output.saturating_mul(place));
        place = place.saturating_mul(3);
        remaining_data = remaining_data.div_euclid(3);
        remaining_accumulator = remaining_accumulator.div_euclid(3);
        trit = trit.saturating_add(1);
    }
    normalize_result(Word::new(result))
}

const fn crazy_trit_scalar(data: u16, accumulator: u16) -> u16 {
    if ((data == 0 || data == 1) && accumulator == 0)
        || (data == 2 && accumulator == 2)
    {
        1
    } else if (data == 1 && accumulator == 2)
        || (data == 2 && (accumulator == 0 || accumulator == 1))
    {
        2
    } else {
        0
    }
}

fn check_decode(cell: Word, code_pointer: Word) -> TestResult {
    let cell_offset = usize::from(cell.value().saturating_sub(GRAPHICAL_START));
    let combined =
        cell_offset.saturating_add(usize::from(code_pointer.value()));
    let translation_index = combined.rem_euclid(DECODE_TABLE_LEN);
    let expected = TEST_XLAT1
        .get(translation_index)
        .copied()
        .ok_or_else(|| String::from("scalar decode index escaped XLAT1"))?;
    let observed = decode_instruction(cell, code_pointer).ok_or_else(|| {
        String::from("optimized decode rejected graphical cell")
    })?;
    check_equal(
        &observed,
        &expected,
        "optimized decode equals independent scalar definition",
    )
}

fn check_crazy_pair(data_value: u16, accumulator_value: u16) -> TestResult {
    let data = normalize_result(Word::new(data_value))?;
    let accumulator = normalize_result(Word::new(accumulator_value))?;
    let expected = crazy_scalar(data, accumulator)?;
    let observed = data.crazy(accumulator);
    check_equal(
        &observed,
        &expected,
        "optimized crazy equals independent scalar definition",
    )
}

fn rotate_scalar(value: Word) -> TestResult<Word> {
    let raw = value.value();
    let quotient = raw.div_euclid(3);
    let low_trit = raw.rem_euclid(3);
    let rotated = quotient
        .saturating_add(low_trit.saturating_mul(ROTATE_HIGH_TRIT_WEIGHT));
    normalize_result(Word::new(rotated))
}

#[test]
fn crazy_chunks_match_scalar_definition_in_both_positions() -> TestResult {
    let mut data_chunk = 0u16;
    while data_chunk < CHUNK_VALUES {
        let mut accumulator_chunk = 0u16;
        while accumulator_chunk < CHUNK_VALUES {
            check_crazy_pair(data_chunk, accumulator_chunk)?;
            check_crazy_pair(
                data_chunk.saturating_mul(CHUNK_VALUES),
                accumulator_chunk.saturating_mul(CHUNK_VALUES),
            )?;
            accumulator_chunk = accumulator_chunk.saturating_add(1);
        }
        data_chunk = data_chunk.saturating_add(1);
    }
    Ok(())
}

#[test]
fn decode_table_matches_scalar_definition_for_every_position() -> TestResult {
    let mut pointer_raw = 0u16;
    loop {
        let code_pointer = normalize_result(Word::new(pointer_raw))?;
        let mut cell_raw = GRAPHICAL_START;
        while cell_raw <= 126 {
            let cell = normalize_result(Word::new(cell_raw))?;
            check_decode(cell, code_pointer)?;
            cell_raw = cell_raw.saturating_add(1);
        }
        if pointer_raw == MAX_WORD_VALUE {
            break;
        }
        pointer_raw = pointer_raw.saturating_add(1);
    }
    Ok(())
}

#[test]
fn rotate_table_matches_scalar_definition_for_every_word() -> TestResult {
    let mut raw = 0u16;
    loop {
        let word = normalize_result(Word::new(raw))?;
        check_equal(
            &word.rotate(),
            &rotate_scalar(word)?,
            "optimized rotate equals independent scalar definition",
        )?;
        if raw == MAX_WORD_VALUE {
            break;
        }
        raw = raw.saturating_add(1);
    }
    Ok(())
}
