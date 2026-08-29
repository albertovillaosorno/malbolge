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
//   - Width-generic profile-word values represented as five-trit chunks.
// - Must-Not:
//   - Define memory addressing, profile admission, or a fixed maximum width.
// - Allows:
//   - Inputs: nonzero ternary widths, base-243 chunks, and bounded integers.
//   - Outputs: validated words, crazy, rotate, projection, and byte projection.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when another chunk encoding requires independent arithmetic rules.
// - Merge-When:
//   - Merge when profile execution universally uses this representation.
// - Summary:
//   - Product representation for profile words beyond primitive integer widths.
// - Description:
//   - Stores ceil(N/5) little-endian base-243 chunks with an exact tail width.
// - Usage:
//   - Used to prove and stage width-generic value semantics before VM
//     migration.
// - Defaults:
//   - No semantic maximum width; profile admission owns any minimum width.
//

//! Width-generic Malbolge profile words in five-trit chunks.

use std::fmt::{Display, Formatter, Result as FormatResult};

use crate::semantic_width::{
    SEMANTIC_WIDTH_CHUNK_CARDINALITY, SEMANTIC_WIDTH_CHUNK_TRITS,
    SEMANTIC_WIDTH_RADIX,
};
use crate::word::profile_crazy;

/// Number of ternary digits represented by one complete profile-word chunk.
pub const PROFILE_WORD_CHUNK_TRITS: usize = SEMANTIC_WIDTH_CHUNK_TRITS;
/// Number of distinct values represented by one complete profile-word chunk.
pub const PROFILE_WORD_CHUNK_CARDINALITY: u16 =
    SEMANTIC_WIDTH_CHUNK_CARDINALITY;

const OUTPUT_MODULUS: u16 = 256;
const TERNARY_RADIX: u8 = SEMANTIC_WIDTH_RADIX;

/// Failure while constructing or combining chunked profile words.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ChunkedProfileWordError {
    /// The supplied chunk count disagrees with `ceil(trits / 5)`.
    ChunkCount {
        /// Observed number of chunks.
        observed: usize,
        /// Required number of chunks.
        required: usize,
    },
    /// One chunk contains a value outside its full or tail domain.
    ChunkValue {
        /// Zero-based little-endian chunk index.
        index: usize,
        /// Largest value admitted at this chunk index.
        maximum: u8,
        /// Observed chunk value.
        value: u8,
    },
    /// A projection target is zero or wider than its source word.
    ProjectionWidth {
        /// Source width in trits.
        source_trits: usize,
        /// Requested projected width in trits.
        target_trits: usize,
    },
    /// A bounded integer is outside the requested ternary width.
    ValueOutsideWidth {
        /// Requested width in trits.
        trits: usize,
        /// Input integer value.
        value: u64,
    },
    /// Binary word operation operands have different widths.
    WidthMismatch {
        /// Accumulator width in trits.
        accumulator_trits: usize,
        /// Data width in trits.
        data_trits: usize,
    },
    /// Zero is not a valid profile-word width.
    ZeroWidth,
}

impl Display for ChunkedProfileWordError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match *self {
            Self::ChunkCount { observed, required } => {
                write!(
                    f,
                    "profile word needs {required} chunks, observed {observed}"
                )
            },
            Self::ChunkValue { index, maximum, value } => write!(
                f,
                "profile word chunk {index} value {value} exceeds {maximum}"
            ),
            Self::ProjectionWidth {
                source_trits,
                target_trits,
            } => write!(
                f,
                "projection source={source_trits} target={target_trits}"
            ),
            Self::ValueOutsideWidth { trits, value } => {
                write!(f, "value {value} exceeds {trits}-trit word domain")
            },
            Self::WidthMismatch {
                accumulator_trits,
                data_trits,
            } => write!(
                f,
                "crazy widths data={data_trits} acc={accumulator_trits}"
            ),
            Self::ZeroWidth => {
                f.write_str("profile word width must be nonzero")
            },
        }
    }
}

/// One width-generic Malbolge profile word stored in little-endian base 243.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ChunkedProfileWord {
    chunks: Box<[u8]>,
    trits: usize,
}

impl ChunkedProfileWord {
    /// Returns the physical chunk count `ceil(trits / 5)`.
    #[must_use]
    pub const fn chunk_count(&self) -> usize {
        self.chunks.len()
    }

    /// Returns little-endian base-243 chunks.
    #[must_use]
    pub const fn chunks(&self) -> &[u8] {
        &self.chunks
    }

    /// Applies the normative Malbolge crazy operation at this exact width.
    ///
    /// # Errors
    ///
    /// Returns [`ChunkedProfileWordError::WidthMismatch`] for different widths.
    pub fn crazy(
        &self,
        accumulator: &Self,
    ) -> Result<Self, ChunkedProfileWordError> {
        if self.trits != accumulator.trits {
            return Err(ChunkedProfileWordError::WidthMismatch {
                accumulator_trits: accumulator.trits,
                data_trits: self.trits,
            });
        }
        let mut chunks = Vec::with_capacity(self.chunk_count());
        for (index, (data_chunk, accumulator_chunk)) in self
            .chunks
            .iter()
            .zip(accumulator.chunks.iter())
            .enumerate()
        {
            chunks.push(crazy_chunk_at_width(
                *data_chunk,
                *accumulator_chunk,
                chunk_trits(self.trits, index),
            ));
        }
        Ok(Self {
            chunks: chunks.into_boxed_slice(),
            trits: self.trits,
        })
    }

    /// Constructs the all-two-trit EOF word at any nonzero width.
    ///
    /// # Errors
    ///
    /// Returns [`ChunkedProfileWordError::ZeroWidth`] for `trits == 0`.
    pub fn eof(trits: usize) -> Result<Self, ChunkedProfileWordError> {
        let chunk_count = checked_chunk_count(trits)?;
        let mut chunks = Vec::with_capacity(chunk_count);
        for index in 0..chunk_count {
            chunks.push(chunk_maximum(chunk_trits(trits, index)));
        }
        Ok(Self {
            chunks: chunks.into_boxed_slice(),
            trits,
        })
    }

    /// Constructs one word from exact little-endian base-243 chunks.
    ///
    /// # Errors
    ///
    /// Rejects zero width, wrong chunk count, full chunks above 242, or a tail
    /// chunk containing non-semantic high trits.
    pub fn from_chunks(
        trits: usize,
        chunks: Vec<u8>,
    ) -> Result<Self, ChunkedProfileWordError> {
        let required = checked_chunk_count(trits)?;
        if chunks.len() != required {
            return Err(ChunkedProfileWordError::ChunkCount {
                observed: chunks.len(),
                required,
            });
        }
        validate_chunks(trits, &chunks)?;
        Ok(Self {
            chunks: chunks.into_boxed_slice(),
            trits,
        })
    }

    /// Constructs one word from a bounded integer without choosing a host-wide
    /// representation for the resulting word type.
    ///
    /// # Errors
    ///
    /// Returns [`ChunkedProfileWordError::ValueOutsideWidth`] when `value` has
    /// nonzero trits above the requested width.
    pub fn from_u64(
        trits: usize,
        value: u64,
    ) -> Result<Self, ChunkedProfileWordError> {
        let chunk_count = checked_chunk_count(trits)?;
        let mut chunks = Vec::with_capacity(chunk_count);
        let mut remaining = value;
        for index in 0..chunk_count {
            let modulus = u64::from(chunk_modulus(chunk_trits(trits, index)));
            let chunk = remaining.rem_euclid(modulus);
            chunks.push(u8::try_from(chunk).ok().unwrap_or(0));
            remaining = remaining.div_euclid(modulus);
        }
        if remaining != 0 {
            return Err(ChunkedProfileWordError::ValueOutsideWidth {
                trits,
                value,
            });
        }
        Ok(Self {
            chunks: chunks.into_boxed_slice(),
            trits,
        })
    }

    /// Returns the normative output byte, equal to the complete word modulo
    /// 256.
    #[must_use]
    pub fn low_byte(&self) -> u8 {
        self.residue(OUTPUT_MODULUS)
            .and_then(|value| u8::try_from(value).ok())
            .unwrap_or(0)
    }

    /// Projects this word onto its least-significant `target_trits` trits.
    ///
    /// # Errors
    ///
    /// Rejects zero-width projection or any projection wider than the source.
    pub fn project(
        &self,
        target_trits: usize,
    ) -> Result<Self, ChunkedProfileWordError> {
        if target_trits == 0 || target_trits > self.trits {
            return Err(ChunkedProfileWordError::ProjectionWidth {
                source_trits: self.trits,
                target_trits,
            });
        }
        let target_chunks = target_trits.div_ceil(PROFILE_WORD_CHUNK_TRITS);
        let source = self.chunks.get(..target_chunks).ok_or(
            ChunkedProfileWordError::ProjectionWidth {
                source_trits: self.trits,
                target_trits,
            },
        )?;
        let mut chunks = source.to_vec();
        let top = target_chunks.saturating_sub(1);
        let modulus = chunk_modulus(chunk_trits(target_trits, top));
        if let Some(value) = chunks.get_mut(top) {
            *value = u8::try_from(u16::from(*value).rem_euclid(modulus))
                .ok()
                .unwrap_or(0);
        }
        Ok(Self {
            chunks: chunks.into_boxed_slice(),
            trits: target_trits,
        })
    }

    /// Returns the complete word modulo one nonzero small integer.
    ///
    /// This is sufficient for instruction decode modulo 94 and output modulo
    /// 256 without converting the full word into a primitive integer.
    #[must_use]
    pub fn residue(&self, modulus: u16) -> Option<u16> {
        if modulus == 0 {
            return None;
        }
        let modulus_u32 = u32::from(modulus);
        let mut result = 0u32;
        for chunk in self.chunks.iter().rev() {
            result = result
                .saturating_mul(u32::from(PROFILE_WORD_CHUNK_CARDINALITY))
                .saturating_add(u32::from(*chunk))
                .rem_euclid(modulus_u32);
        }
        u16::try_from(result).ok()
    }

    /// Rotates the least-significant trit into the exact highest semantic trit.
    #[must_use]
    pub fn rotate(&self) -> Self {
        let mut chunks = vec![0u8; self.chunk_count()];
        for index in 0..self.chunk_count() {
            let current = self.chunks.get(index).copied().unwrap_or(0);
            let higher_low = self
                .chunks
                .get(index.saturating_add(1))
                .copied()
                .unwrap_or(0)
                .rem_euclid(TERNARY_RADIX);
            let shifted = current.div_euclid(TERNARY_RADIX).saturating_add(
                higher_low.saturating_mul(chunk_high_trit_weight()),
            );
            if let Some(target) = chunks.get_mut(index) {
                *target = shifted;
            }
        }
        let low_trit = self
            .chunks
            .first()
            .copied()
            .unwrap_or(0)
            .rem_euclid(TERNARY_RADIX);
        let top = self.chunk_count().saturating_sub(1);
        let high_weight =
            trit_weight(chunk_trits(self.trits, top).saturating_sub(1));
        if let Some(value) = chunks.get_mut(top) {
            *value = value.saturating_add(low_trit.saturating_mul(high_weight));
        }
        Self {
            chunks: chunks.into_boxed_slice(),
            trits: self.trits,
        }
    }

    /// Advances this word by one with exact wraparound at `3^N`.
    #[must_use]
    pub fn successor(&self) -> Self {
        let mut chunks = self.chunks.to_vec();
        let mut carry = true;
        for index in 0..chunks.len() {
            if !carry {
                break;
            }
            let modulus = chunk_modulus(chunk_trits(self.trits, index));
            let Some(chunk) = chunks.get_mut(index) else {
                break;
            };
            let current = u16::from(*chunk).saturating_add(1);
            carry = current >= modulus;
            *chunk = if carry {
                0
            } else {
                u8::try_from(current).ok().unwrap_or(0)
            };
        }
        Self {
            chunks: chunks.into_boxed_slice(),
            trits: self.trits,
        }
    }

    /// Returns the exact integer when it fits in `u32`.
    #[must_use]
    pub fn to_u32(&self) -> Option<u32> {
        self.to_u64().and_then(|value| u32::try_from(value).ok())
    }

    /// Returns the exact integer when it fits in `u64`.
    #[must_use]
    pub fn to_u64(&self) -> Option<u64> {
        let mut result = 0u64;
        for chunk in self.chunks.iter().rev() {
            result = result
                .checked_mul(u64::from(PROFILE_WORD_CHUNK_CARDINALITY))?
                .checked_add(u64::from(*chunk))?;
        }
        Some(result)
    }

    /// Returns this word's exact semantic width in trits.
    #[must_use]
    pub const fn trits(&self) -> usize {
        self.trits
    }

    /// Constructs the all-zero word at any nonzero width.
    ///
    /// # Errors
    ///
    /// Returns [`ChunkedProfileWordError::ZeroWidth`] for `trits == 0`.
    pub fn zero(trits: usize) -> Result<Self, ChunkedProfileWordError> {
        let chunk_count = checked_chunk_count(trits)?;
        Ok(Self {
            chunks: vec![0; chunk_count].into_boxed_slice(),
            trits,
        })
    }
}

const fn checked_chunk_count(
    trits: usize,
) -> Result<usize, ChunkedProfileWordError> {
    if trits == 0 {
        Err(ChunkedProfileWordError::ZeroWidth)
    } else {
        Ok(trits.div_ceil(PROFILE_WORD_CHUNK_TRITS))
    }
}

const fn chunk_high_trit_weight() -> u8 {
    trit_weight(PROFILE_WORD_CHUNK_TRITS.saturating_sub(1))
}

const fn chunk_maximum(trits: usize) -> u8 {
    match trits {
        1 => 2,
        2 => 8,
        3 => 26,
        4 => 80,
        _ => 242,
    }
}

const fn chunk_modulus(trits: usize) -> u16 {
    match trits {
        1 => 3,
        2 => 9,
        3 => 27,
        4 => 81,
        _ => PROFILE_WORD_CHUNK_CARDINALITY,
    }
}

const fn chunk_trits(trits: usize, index: usize) -> usize {
    let chunk_count = trits.div_ceil(PROFILE_WORD_CHUNK_TRITS);
    if index.saturating_add(1) == chunk_count {
        let tail = trits.rem_euclid(PROFILE_WORD_CHUNK_TRITS);
        if tail == 0 {
            PROFILE_WORD_CHUNK_TRITS
        } else {
            tail
        }
    } else {
        PROFILE_WORD_CHUNK_TRITS
    }
}

fn crazy_chunk_at_width(data: u8, accumulator: u8, trits: usize) -> u8 {
    let chunk_trits = u8::try_from(trits).ok().unwrap_or(0);
    let value =
        profile_crazy(u32::from(data), u32::from(accumulator), chunk_trits);
    let reduced = value.rem_euclid(u32::from(chunk_modulus(trits)));
    u8::try_from(reduced).ok().unwrap_or(0)
}

const fn trit_weight(exponent: usize) -> u8 {
    match exponent {
        0 => 1,
        1 => 3,
        2 => 9,
        3 => 27,
        _ => 81,
    }
}

fn validate_chunks(
    trits: usize,
    chunks: &[u8],
) -> Result<(), ChunkedProfileWordError> {
    for (index, value) in chunks.iter().copied().enumerate() {
        let maximum = chunk_maximum(chunk_trits(trits, index));
        if value > maximum {
            return Err(ChunkedProfileWordError::ChunkValue {
                index,
                maximum,
                value,
            });
        }
    }
    Ok(())
}
