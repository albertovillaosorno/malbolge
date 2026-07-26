// File:
//   - word.rs
// Path:
//   - vm/src/word.rs
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
// Related documents:
// - math/specification/malbolge-1998.tex
// - docs/technical/specification/malbolge-1998.md
//
// Large file:
//   - false
//

//! Classic Malbolge ten-trit words and primitive operations.

use std::fmt::{Display, Formatter, Result as FormatResult};

/// Number of words in the classic Malbolge memory domain.
pub const MEMORY_WORDS: usize = 59_049;
/// Largest value representable by one classic ten-trit word.
pub const MAX_WORD_VALUE: u16 = 59_048;
const ROTATE_HIGH_TRIT_WEIGHT: u16 = 19_683;
const TRIT_COUNT: u8 = 10;

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
        let mut data = self.0;
        let mut acc = accumulator.0;
        let mut result = 0u16;
        let mut place = 1u16;
        for _trit in 0..TRIT_COUNT {
            let output = crazy_trit(data.rem_euclid(3), acc.rem_euclid(3));
            result = result.saturating_add(output.saturating_mul(place));
            place = place.saturating_mul(3);
            data = data.div_euclid(3);
            acc = acc.div_euclid(3);
        }
        Self(result)
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
    pub const fn rotate(self) -> Self {
        let quotient = self.0.div_euclid(3);
        let low_trit = self.0.rem_euclid(3);
        let high_trit = low_trit.saturating_mul(ROTATE_HIGH_TRIT_WEIGHT);
        Self(quotient.saturating_add(high_trit))
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
