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
//   - definitions.
// - Description:
//   - Covers every rotate/crazy entry and every graphical decode position.
// - Usage:
//   - Runs under the Cargo VM integration-test composition target.
// - Defaults:
//   - Any optimized/scalar mismatch is a hard deterministic test failure.
//

//! Independent scalar equivalence tests for optimized classic word operations.

use malbolge::{
    MAX_WORD_VALUE, Word, current_profile, decode_instruction,
    decode_profile_instruction, encrypt_profile_cell, historical_profile,
    profile_cell_decodes_to_no_operation, profile_crazy,
    profile_pointer_successor, profile_rotate,
};

use super::{TestResult, check_equal, normalize_result};

const CHUNK_VALUES: u16 = 243;
const DECODE_TABLE_LEN: usize = 94;
const GRAPHICAL_START: u16 = 33;
const TEST_XLAT2: &[u8; DECODE_TABLE_LEN] =
    b"5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1C\
B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";
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

fn profile_crazy_scalar(mut data: u32, mut accumulator: u32, trits: u8) -> u32 {
    let mut place = 1u32;
    let mut result = 0u32;
    let mut trit = 0u8;
    while trit < trits {
        let data_digit = u16::try_from(data.rem_euclid(3)).ok().unwrap_or(0);
        let accumulator_digit =
            u16::try_from(accumulator.rem_euclid(3)).ok().unwrap_or(0);
        let output =
            u32::from(crazy_trit_scalar(data_digit, accumulator_digit));
        result = result.saturating_add(output.saturating_mul(place));
        place = place.saturating_mul(3);
        data = data.div_euclid(3);
        accumulator = accumulator.div_euclid(3);
        trit = trit.saturating_add(1);
    }
    result
}

const fn structured_profile_words(modulus: u32) -> [u32; 12] {
    let maximum = modulus.saturating_sub(1);
    [
        0,
        1,
        2,
        3,
        10,
        123,
        modulus.div_euclid(3),
        modulus.div_euclid(2),
        maximum.saturating_sub(2),
        maximum.saturating_sub(1),
        maximum,
        maximum.div_euclid(2).saturating_mul(2),
    ]
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
fn profile_noop_classification_matches_every_decode_phase() -> TestResult {
    let operation_bytes = b"*/<ijpv";
    let mut pointer = 0u16;
    while pointer < u16::try_from(DECODE_TABLE_LEN).unwrap_or(0) {
        let mut cell = GRAPHICAL_START;
        while cell <= 126 {
            let decoded =
                decode_profile_instruction(u32::from(cell), u32::from(pointer))
                    .ok_or_else(|| {
                        String::from("graphical profile decode failed")
                    })?;
            let expected = !operation_bytes.contains(&decoded);
            check_equal(
                &profile_cell_decodes_to_no_operation(
                    u32::from(cell),
                    u32::from(pointer),
                ),
                &expected,
                "profile no-op classification equals decoded opcode set",
            )?;
            cell = cell.saturating_add(1);
        }
        pointer = pointer.saturating_add(1);
    }
    check_equal(
        &profile_cell_decodes_to_no_operation(32, u32::MAX),
        &false,
        "non-graphical cell is not no-op",
    )
}

#[test]
fn public_profile_crazy_matches_independent_formula() -> TestResult {
    for data in 0..3u32 {
        for accumulator in 0..3u32 {
            check_equal(
                &profile_crazy(data, accumulator, 1),
                &profile_crazy_scalar(data, accumulator, 1),
                "profile crazy exhausts the ternary digit table",
            )?;
        }
    }
    for profile in [historical_profile(), current_profile()] {
        let trits = profile.word_trits();
        let words = structured_profile_words(profile.word_modulus());
        for data in words {
            for accumulator in words {
                check_equal(
                    &profile_crazy(data, accumulator, trits),
                    &profile_crazy_scalar(data, accumulator, trits),
                    "profile crazy equals independent word formula",
                )?;
            }
        }
    }
    Ok(())
}

#[test]
fn profile_pointer_successor_wraps_exact_domains() -> TestResult {
    for profile in [historical_profile(), current_profile()] {
        let modulus = profile.memory_words();
        check_equal(
            &profile_pointer_successor(0, modulus),
            &Some(1),
            "profile pointer advances from zero",
        )?;
        check_equal(
            &profile_pointer_successor(modulus.saturating_sub(1), modulus),
            &Some(0),
            "profile pointer wraps at maximum",
        )?;
        check_equal(
            &profile_pointer_successor(modulus, modulus),
            &None,
            "out-of-domain profile pointer is rejected",
        )?;
    }
    check_equal(
        &profile_pointer_successor(0, 0),
        &None,
        "zero profile modulus is rejected",
    )
}

#[test]
fn profile_rotate_matches_independent_formula() -> TestResult {
    for modulus in [59_049u32, 4_782_969u32] {
        let high_weight = modulus.div_euclid(3);
        for value in [0, 1, 2, 10, 123, modulus.saturating_sub(1)] {
            let expected =
                value.div_euclid(3) + value.rem_euclid(3) * high_weight;
            check_equal(
                &profile_rotate(value, modulus),
                &expected,
                "profile rotate formula",
            )?;
        }
    }
    Ok(())
}

#[test]
fn profile_encryption_matches_independent_table() -> TestResult {
    for cell in GRAPHICAL_START..=126 {
        let index = usize::from(cell.saturating_sub(GRAPHICAL_START));
        let expected = TEST_XLAT2
            .get(index)
            .copied()
            .map(u32::from)
            .ok_or_else(|| String::from("profile encryption index escaped"))?;
        check_equal(
            &encrypt_profile_cell(u32::from(cell)),
            &Some(expected),
            "profile encryption equals independent XLAT2",
        )?;
    }
    check_equal(
        &encrypt_profile_cell(32),
        &None,
        "profile encryption rejects below graphical range",
    )?;
    check_equal(
        &encrypt_profile_cell(127),
        &None,
        "profile encryption rejects above graphical range",
    )
}

#[test]
fn profile_decode_matches_classic_for_every_graphical_phase() -> TestResult {
    let mut pointer = 0u16;
    while pointer < u16::try_from(DECODE_TABLE_LEN).unwrap_or(0) {
        let classic_pointer = normalize_result(Word::new(pointer))?;
        let mut cell = GRAPHICAL_START;
        while cell <= 126 {
            let classic_cell = normalize_result(Word::new(cell))?;
            check_equal(
                &decode_profile_instruction(
                    u32::from(cell),
                    u32::from(pointer),
                ),
                &decode_instruction(classic_cell, classic_pointer),
                "profile decode equals classic phase",
            )?;
            cell = cell.saturating_add(1);
        }
        pointer = pointer.saturating_add(1);
    }
    check_equal(
        &decode_profile_instruction(32, u32::MAX),
        &None,
        "profile decode rejects below graphical range",
    )?;
    check_equal(
        &decode_profile_instruction(127, u32::MAX),
        &None,
        "profile decode rejects above graphical range",
    )
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
