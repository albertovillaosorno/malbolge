// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Independent evidence for the width-generic chunked profile-word contract.
// - Must-Not:
//   - Reuse production rotate/crazy formulas as the wide-width oracle.
// - Allows:
//   - Inputs: public chunked words plus independent ternary digit formulas.
//   - Outputs: round-trip, projection, crazy, rotate, and compatibility proofs.
//   - Side effects: test-process allocation only.
// - Split-When:
//   - Split when chunked memory addressing gains a separate public contract.
// - Merge-When:
//   - Merge when another test owns the same profile-word equivalence evidence.
// - Summary:
//   - Proves five-trit chunks preserve exact words beyond primitive integers.
// - Description:
//   - Cross-checks N10..N41 operations and represents N100 without a big int.
// - Usage:
//   - Runs under the Cargo VM integration-test composition target.
// - Defaults:
//   - Wide semantics use independent trit vectors, not production scalar paths.
//

//! Independent conformance for width-generic chunked profile words.

use malbolge::{
    ChunkedProfileWord, ChunkedProfileWordError,
    PROFILE_WORD_CHUNK_CARDINALITY, PROFILE_WORD_CHUNK_TRITS,
    SEMANTIC_WIDTH_CHUNK_CARDINALITY, SEMANTIC_WIDTH_CHUNK_TRITS,
    SEMANTIC_WIDTH_MAXIMUM_TRITS, SEMANTIC_WIDTH_MINIMUM_TRITS,
    SEMANTIC_WIDTH_RADIX, profile_crazy, profile_rotate,
};

use super::{TestResult, check_equal};

const OUTPUT_MODULUS: u16 = 256;
const TERNARY_RADIX: u8 = 3;

const fn crazy_trit(data: u8, accumulator: u8) -> u8 {
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

fn from_trits(trits: &[u8]) -> TestResult<ChunkedProfileWord> {
    if trits.is_empty() {
        return Err(String::from("test oracle requires nonzero width"));
    }
    let mut chunks =
        Vec::with_capacity(trits.len().div_ceil(PROFILE_WORD_CHUNK_TRITS));
    for digits in trits.chunks(PROFILE_WORD_CHUNK_TRITS) {
        let mut chunk = 0u16;
        let mut place = 1u16;
        for digit in digits {
            chunk =
                chunk.saturating_add(u16::from(*digit).saturating_mul(place));
            place = place.saturating_mul(u16::from(TERNARY_RADIX));
        }
        chunks
            .push(u8::try_from(chunk).map_err(|error| {
                format!("oracle chunk conversion: {error}")
            })?);
    }
    ChunkedProfileWord::from_chunks(trits.len(), chunks)
        .map_err(|error| error.to_string())
}

fn patterned_word(trits: usize, seed: usize) -> TestResult<ChunkedProfileWord> {
    let mut digits = Vec::with_capacity(trits);
    for index in 0..trits {
        let digit = u8::try_from(index.saturating_add(seed).rem_euclid(3))
            .map_err(|error| format!("pattern trit conversion: {error}"))?;
        digits.push(digit);
    }
    from_trits(&digits)
}

fn ternary_modulus_u64(trits: usize) -> Option<u64> {
    let mut value = 1u64;
    for _index in 0..trits {
        value = value.checked_mul(u64::from(TERNARY_RADIX))?;
    }
    Some(value)
}

fn trits_of(word: &ChunkedProfileWord) -> Vec<u8> {
    let mut digits = Vec::with_capacity(
        word.chunk_count().saturating_mul(PROFILE_WORD_CHUNK_TRITS),
    );
    for chunk in word.chunks() {
        let mut remaining = *chunk;
        for _index in 0..PROFILE_WORD_CHUNK_TRITS {
            digits.push(remaining.rem_euclid(TERNARY_RADIX));
            remaining = remaining.div_euclid(TERNARY_RADIX);
        }
    }
    digits.truncate(word.trits());
    digits
}

fn wide_crazy_oracle(
    data: &ChunkedProfileWord,
    accumulator: &ChunkedProfileWord,
) -> TestResult<ChunkedProfileWord> {
    if data.trits() != accumulator.trits() {
        return Err(String::from("oracle crazy width mismatch"));
    }
    let digits: Vec<u8> = trits_of(data)
        .into_iter()
        .zip(trits_of(accumulator))
        .map(|(data_trit, accumulator_trit)| {
            crazy_trit(data_trit, accumulator_trit)
        })
        .collect();
    from_trits(&digits)
}

fn wide_low_byte_oracle(word: &ChunkedProfileWord) -> TestResult<u8> {
    let mut result = 0u16;
    let mut place = 1u16;
    for digit in trits_of(word) {
        result = result
            .saturating_add(u16::from(digit).saturating_mul(place))
            .rem_euclid(OUTPUT_MODULUS);
        place = place
            .saturating_mul(u16::from(TERNARY_RADIX))
            .rem_euclid(OUTPUT_MODULUS);
    }
    u8::try_from(result).map_err(|error| format!("low-byte oracle: {error}"))
}

fn wide_rotate_oracle(
    word: &ChunkedProfileWord,
) -> TestResult<ChunkedProfileWord> {
    let digits = trits_of(word);
    let low = digits
        .first()
        .copied()
        .ok_or_else(|| String::from("rotate oracle lost low trit"))?;
    let mut rotated: Vec<u8> = digits.into_iter().skip(1).collect();
    rotated.push(low);
    from_trits(&rotated)
}

fn assert_u32_crazy_bridge(
    trits: usize,
    data: &ChunkedProfileWord,
    data_value: u64,
    accumulator_value: u64,
) -> TestResult {
    let accumulator = ChunkedProfileWord::from_u64(trits, accumulator_value)
        .map_err(|error| error.to_string())?;
    let data_u32 = u32::try_from(data_value)
        .map_err(|error| format!("u32 bridge data: {error}"))?;
    let accumulator_u32 = u32::try_from(accumulator_value)
        .map_err(|error| format!("u32 bridge accumulator: {error}"))?;
    let trits_u8 = u8::try_from(trits)
        .map_err(|error| format!("u32 bridge trits: {error}"))?;
    let observed = data
        .crazy(&accumulator)
        .map_err(|error| error.to_string())?
        .to_u64();
    let expected =
        u64::from(profile_crazy(data_u32, accumulator_u32, trits_u8));
    check_equal(
        &observed,
        &Some(expected),
        "chunked crazy equals u32 primitive",
    )
}

#[test]
fn chunked_profile_word_uses_generated_semantic_width_model() -> TestResult {
    check_equal(&SEMANTIC_WIDTH_RADIX, &3, "semantic radix projection")?;
    check_equal(
        &SEMANTIC_WIDTH_MINIMUM_TRITS,
        &10,
        "semantic minimum-width projection",
    )?;
    check_equal(
        &SEMANTIC_WIDTH_CHUNK_TRITS,
        &PROFILE_WORD_CHUNK_TRITS,
        "chunk width comes from canonical projection",
    )?;
    check_equal(
        &SEMANTIC_WIDTH_CHUNK_CARDINALITY,
        &PROFILE_WORD_CHUNK_CARDINALITY,
        "chunk cardinality comes from canonical projection",
    )?;
    check_equal(
        &SEMANTIC_WIDTH_MAXIMUM_TRITS,
        &None,
        "semantic width model remains unbounded",
    )
}

#[test]
fn chunked_profile_word_matches_u32_primitives_through_n20() -> TestResult {
    for trits in [10usize, 14, 15, 16, 20] {
        let modulus = ternary_modulus_u64(trits)
            .ok_or_else(|| String::from("u32 bridge modulus overflow"))?;
        let modulus_u32 = u32::try_from(modulus)
            .map_err(|error| format!("u32 bridge modulus: {error}"))?;
        let maximum = modulus.saturating_sub(1);
        let values = [0u64, 1, 2, 10, maximum.div_euclid(2), maximum];
        for data_value in values {
            let data = ChunkedProfileWord::from_u64(trits, data_value)
                .map_err(|error| error.to_string())?;
            let data_u32 = u32::try_from(data_value)
                .map_err(|error| format!("u32 bridge data: {error}"))?;
            check_equal(
                &data.rotate().to_u64(),
                &Some(u64::from(profile_rotate(data_u32, modulus_u32))),
                "chunked rotate equals u32 primitive",
            )?;
            for accumulator_value in values {
                assert_u32_crazy_bridge(
                    trits,
                    &data,
                    data_value,
                    accumulator_value,
                )?;
            }
        }
    }
    Ok(())
}

#[test]
fn chunked_profile_word_projects_only_high_trits() -> TestResult {
    let source =
        ChunkedProfileWord::from_chunks(21, vec![241, 242, 200, 17, 2])
            .map_err(|error| error.to_string())?;
    check_equal(
        &source
            .project(14)
            .map_err(|error| error.to_string())?
            .chunks(),
        &&[241, 242, 38][..],
        "N21 to N14 truncates the third chunk modulo 3^4",
    )?;
    check_equal(
        &source
            .project(15)
            .map_err(|error| error.to_string())?
            .chunks(),
        &&[241, 242, 200][..],
        "N21 to N15 keeps three full chunks",
    )?;
    check_equal(
        &source
            .project(16)
            .map_err(|error| error.to_string())?
            .chunks(),
        &&[241, 242, 200, 2][..],
        "N21 to N16 keeps one trit of the fourth chunk",
    )
}

#[test]
fn chunked_profile_word_represents_widths_beyond_u64() -> TestResult {
    for trits in [21usize, 31, 41, 100] {
        let eof = ChunkedProfileWord::eof(trits)
            .map_err(|error| error.to_string())?;
        check_equal(
            &trits_of(&eof),
            &vec![2u8; trits],
            "chunked EOF is all two trits",
        )?;
        check_equal(
            &eof.chunk_count(),
            &trits.div_ceil(PROFILE_WORD_CHUNK_TRITS),
            "chunk count is ceil(N/5)",
        )?;
        check_equal(
            &eof.low_byte(),
            &wide_low_byte_oracle(&eof)?,
            "wide low byte uses the complete word",
        )?;
    }
    if ChunkedProfileWord::eof(41)
        .map_err(|error| error.to_string())?
        .to_u64()
        .is_none()
        && ChunkedProfileWord::eof(100)
            .map_err(|error| error.to_string())?
            .to_u64()
            .is_none()
    {
        Ok(())
    } else {
        Err(String::from("wide EOF unexpectedly fit in u64"))
    }
}

#[test]
fn chunked_profile_word_wide_crazy_matches_trit_oracle() -> TestResult {
    for trits in [21usize, 31, 41, 100] {
        let data = patterned_word(trits, 0)?;
        let accumulator = patterned_word(trits, 1)?;
        let observed = data
            .crazy(&accumulator)
            .map_err(|error| error.to_string())?;
        let expected = wide_crazy_oracle(&data, &accumulator)?;
        check_equal(&observed, &expected, "wide crazy equals trit oracle")?;
    }
    Ok(())
}

#[test]
fn chunked_profile_word_wide_rotate_matches_trit_oracle() -> TestResult {
    for trits in [21usize, 31, 41, 100] {
        for seed in 0..3usize {
            let word = patterned_word(trits, seed)?;
            check_equal(
                &word.rotate(),
                &wide_rotate_oracle(&word)?,
                "wide rotate equals trit oracle",
            )?;
        }
    }
    Ok(())
}

#[test]
fn chunked_profile_word_rejects_invalid_shapes() -> TestResult {
    check_equal(
        &ChunkedProfileWord::eof(0),
        &Err(ChunkedProfileWordError::ZeroWidth),
        "zero-width EOF is rejected",
    )?;
    check_equal(
        &ChunkedProfileWord::from_chunks(6, vec![0]),
        &Err(ChunkedProfileWordError::ChunkCount { observed: 1, required: 2 }),
        "chunk count must equal ceil(N/5)",
    )?;
    check_equal(
        &ChunkedProfileWord::from_chunks(6, vec![0, 3]),
        &Err(ChunkedProfileWordError::ChunkValue {
            index: 1,
            maximum: 2,
            value: 3,
        }),
        "tail chunk rejects non-semantic high trits",
    )?;
    let n10 =
        ChunkedProfileWord::zero(10).map_err(|error| error.to_string())?;
    let n11 =
        ChunkedProfileWord::zero(11).map_err(|error| error.to_string())?;
    check_equal(
        &n10.crazy(&n11),
        &Err(ChunkedProfileWordError::WidthMismatch {
            accumulator_trits: 11,
            data_trits: 10,
        }),
        "crazy rejects different widths",
    )?;
    check_equal(
        &n10.project(11),
        &Err(ChunkedProfileWordError::ProjectionWidth {
            source_trits: 10,
            target_trits: 11,
        }),
        "projection cannot widen",
    )?;
    check_equal(
        &ChunkedProfileWord::from_u64(10, 59_049),
        &Err(ChunkedProfileWordError::ValueOutsideWidth {
            trits: 10,
            value: 59_049,
        }),
        "bounded constructor rejects value at modulus",
    )?;
    check_equal(
        &PROFILE_WORD_CHUNK_CARDINALITY,
        &243,
        "chunk cardinality remains 3^5",
    )
}
