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

const CHUNK_VALUES: u16 = 243;
const ROTATE_HIGH_TRIT_WEIGHT: u16 = 19_683;

include!(concat!(env!("OUT_DIR"), "/classic_word_tables.rs"));

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

fn crazy_lookup(data: u16, accumulator: u16) -> u16 {
    let low_data = data.rem_euclid(CHUNK_VALUES);
    let low_accumulator = accumulator.rem_euclid(CHUNK_VALUES);
    let high_data = data.div_euclid(CHUNK_VALUES);
    let high_accumulator = accumulator.div_euclid(CHUNK_VALUES);
    let low = crate::crazy_chunk_lookup(low_data, low_accumulator);
    let high = crate::crazy_chunk_lookup(high_data, high_accumulator);
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
