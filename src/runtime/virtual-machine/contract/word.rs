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
//   - Classic ten-trit word representation and primitive ternary operations.
// - Must-Not:
//   - Admit values outside the classic word domain or depend on host overflow.
// - Allows:
//   - Inputs: classic word values and byte values.
//   - Outputs: validated words, rotate, crazy, successor, and low-byte results.
//   - Side effects: none.
// - Split-When:
//   - Split when extended profiles require a different word representation.
// - Merge-When:
//   - Merge when another module owns identical classic word arithmetic.
// - Summary:
//   - Value-safe implementation of the 59049-value classic word domain.
// - Description:
//   - Encodes the mathematical word contract without unsafe or host ambiguity.
// - Usage:
//   - Used by memory, loader, machine execution, and semantic verification.
// - Defaults:
//   - Rejects construction above 59048 and preserves exact classic arithmetic.
//

//! Classic Malbolge ten-trit words and primitive operations.

use std::fmt::{Display, Formatter, Result as FormatResult};

/// Number of words in the classic Malbolge memory domain.
pub const MEMORY_WORDS: usize = 59_049;
/// Largest value representable by one classic ten-trit word.
pub const MAX_WORD_VALUE: u16 = 59_048;

const CRAZY_CHUNK_TRITS: u8 = 5;
const CHUNK_VALUES: u16 = 243;
const ROTATE_HIGH_TRIT_WEIGHT: u16 = 19_683;

include!(concat!(env!("OUT_DIR"), "/classic_word_tables.rs"));
include!(concat!(env!("OUT_DIR"), "/ternary_tables.rs"));

const OUTPUT_MODULUS: u32 = 256;
const TERNARY_RADIX: u32 = 3;

/// Error returned when a value is outside the classic word domain.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WordError {
    value: u16,
}

impl Display for WordError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        let value = self.value;
        write!(
            f,
            "classic Malbolge word value {value} exceeds {MAX_WORD_VALUE}"
        )
    }
}

/// One classic Malbolge ten-trit word in `0..=59048`.
#[derive(Clone, Copy, Debug, Default, Eq, Ord, PartialEq, PartialOrd)]
pub struct Word(u16);

impl Word {
    /// Maximum-valued classic word.
    pub const MAX: Self = Self(MAX_WORD_VALUE);
    /// Zero-valued classic word.
    pub const ZERO: Self = Self(0);

    /// Applies the normative crazy operation using this word as data.
    #[must_use]
    pub fn crazy(self, accumulator: Self) -> Self {
        Self(crazy_lookup(self.0, accumulator.0))
    }

    /// Creates a classic word from one byte without loss.
    #[must_use]
    pub fn from_byte(value: u8) -> Self {
        Self(u16::from(value))
    }

    /// Returns whether this word is a graphical ASCII instruction cell.
    #[must_use]
    pub const fn is_graphical(self) -> bool {
        self.0 >= 33 && self.0 <= 126
    }

    /// Returns the normative output byte, equal to this word modulo 256.
    #[must_use]
    pub fn low_byte(self) -> u8 {
        self.0.to_le_bytes().first().copied().unwrap_or(0)
    }

    /// Creates a classic word when `value` is inside the ten-trit domain.
    ///
    /// # Errors
    ///
    /// Returns [`WordError`] when `value` exceeds the classic maximum 59048.
    pub const fn new(value: u16) -> Result<Self, WordError> {
        if value <= MAX_WORD_VALUE {
            Ok(Self(value))
        } else {
            Err(WordError { value })
        }
    }

    /// Rotates the least-significant trit into the most-significant position.
    #[must_use]
    pub fn rotate(self) -> Self {
        Self(rotate_lookup(self.0))
    }

    /// Advances one classic address with 59049-word wraparound.
    #[must_use]
    pub const fn successor(self) -> Self {
        if self.0 == MAX_WORD_VALUE {
            Self::ZERO
        } else {
            Self(self.0.saturating_add(1))
        }
    }

    /// Returns the exact numeric value of this word.
    #[must_use]
    pub const fn value(self) -> u16 {
        self.0
    }
}

/// Returns the all-two-trit EOF word for one profile width.
///
/// Returns `None` for a zero-width profile or when `3^trits` exceeds `u32`.
#[must_use]
pub const fn profile_eof_word(trits: u8) -> Option<u32> {
    if trits == 0 {
        return None;
    }
    let mut modulus = 1u32;
    let mut index = 0u8;
    while index < trits {
        modulus = match modulus.checked_mul(TERNARY_RADIX) {
            Some(value) => value,
            None => return None,
        };
        index = index.saturating_add(1);
    }
    modulus.checked_sub(1)
}

/// Returns the normative output byte for one profile-width word.
///
/// This is the exact unsigned value modulo 256 used by profile execution.
#[must_use]
pub fn profile_low_byte(value: u32) -> u8 {
    let reduced = value.rem_euclid(OUTPUT_MODULUS);
    u8::try_from(reduced).ok().unwrap_or(0)
}

/// Applies the canonical Malbolge crazy operation to two profile words.
///
/// The caller supplies the canonical profile width in ternary digits. Values
/// outside that profile domain are outside this helper's contract.
#[must_use]
pub fn profile_crazy(mut data: u32, mut accumulator: u32, trits: u8) -> u32 {
    let mut place = 1u32;
    let mut remaining_trits = trits;
    let mut result = 0u32;
    while remaining_trits > 0 {
        let chunk_trits = remaining_trits.min(CRAZY_CHUNK_TRITS);
        let chunk_modulus = ternary_modulus(chunk_trits);
        let data_chunk = u16::try_from(data.rem_euclid(chunk_modulus))
            .ok()
            .unwrap_or(0);
        let accumulator_chunk =
            u16::try_from(accumulator.rem_euclid(chunk_modulus))
                .ok()
                .unwrap_or(0);
        let chunk =
            u32::from(crazy_chunk_lookup(data_chunk, accumulator_chunk))
                .rem_euclid(chunk_modulus);
        result = result.saturating_add(chunk.saturating_mul(place));
        data = data.div_euclid(chunk_modulus);
        accumulator = accumulator.div_euclid(chunk_modulus);
        place = place.saturating_mul(chunk_modulus);
        remaining_trits = remaining_trits.saturating_sub(chunk_trits);
    }
    result
}

const fn ternary_modulus(trits: u8) -> u32 {
    let mut value = 1u32;
    let mut index = 0u8;
    while index < trits {
        value = value.saturating_mul(TERNARY_RADIX);
        index = index.saturating_add(1);
    }
    value
}

fn crazy_lookup(data: u16, accumulator: u16) -> u16 {
    let low_data = data.rem_euclid(CHUNK_VALUES);
    let low_accumulator = accumulator.rem_euclid(CHUNK_VALUES);
    let high_data = data.div_euclid(CHUNK_VALUES);
    let high_accumulator = accumulator.div_euclid(CHUNK_VALUES);
    let low = crazy_chunk_lookup(low_data, low_accumulator);
    let high = crazy_chunk_lookup(high_data, high_accumulator);
    low.saturating_add(high.saturating_mul(CHUNK_VALUES))
}

fn rotate_lookup(value: u16) -> u16 {
    ROTATE_TABLE
        .get(usize::from(value))
        .copied()
        .unwrap_or_else(|| rotate_scalar(value))
}

const fn rotate_scalar(value: u16) -> u16 {
    let quotient = value.div_euclid(3);
    let low_trit = value.rem_euclid(3);
    let high_trit = low_trit.saturating_mul(ROTATE_HIGH_TRIT_WEIGHT);
    quotient.saturating_add(high_trit)
}

fn crazy_chunk_lookup(data: u16, accumulator: u16) -> u16 {
    let index = usize::from(data)
        .saturating_mul(usize::from(CHUNK_VALUES))
        .saturating_add(usize::from(accumulator));
    CRAZY_CHUNK_TABLE
        .get(index)
        .copied()
        .unwrap_or_else(|| crazy_chunk_scalar(data, accumulator))
}

const fn crazy_chunk_scalar(data: u16, accumulator: u16) -> u16 {
    let mut remaining_data = data;
    let mut remaining_accumulator = accumulator;
    let mut result = 0u16;
    let mut place = 1u16;
    let mut trit = 0u8;
    while trit < CRAZY_CHUNK_TRITS {
        let output = crazy_trit(
            remaining_data.rem_euclid(3),
            remaining_accumulator.rem_euclid(3),
        );
        result = result.saturating_add(output.saturating_mul(place));
        place = place.saturating_mul(3);
        remaining_data = remaining_data.div_euclid(3);
        remaining_accumulator = remaining_accumulator.div_euclid(3);
        trit = trit.saturating_add(1);
    }
    result
}

const fn crazy_trit(data: u16, accumulator: u16) -> u16 {
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
