// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - A source-loaded, full-byte-injective N15 input-dependent memory write.
// - Must-Not:
//   - Claim this encoded word is a canonical C32 signed getchar result.
// - Allows:
//   - Inputs: canonical N15 and 94 code phases with two graphical tail cells.
//   - Outputs: graphical /;j;p;v source and exact loader-backed store address.
//   - Side effects: none; target execution belongs to the independent VM.
// - Split-When:
//   - Source-C32 normalization and physical branch linking become general.
// - Merge-When:
//   - A source-linked C23 input-state allocator subsumes this intermediate.
// - Summary:
//   - Distinguishes all 256 real input bytes from true EOF after a guest p.

//! First source-loaded guest write retaining all 257 raw-input classes.
//!
//! For input bytes, the five lowest trits independently span all of 0,1,2.
//! `crazy(seed, input)` is bijective in each of these coordinates only when
//! the corresponding seed trit is one. Input bytes 0..255 use only 0/1 in
//! coordinate five, so its seed trit may be zero or one. EOF differs in
//! higher trits and stays distinct because every crazy seed distinguishes
//! right-operand trits zero and two. This is an *encoded* state, not C32.

use std::iter::repeat_n;

use malbolge::{ProfileDescriptor, current_profile};

use super::{LinearOpcode, unique_graphical_cell, unwritten_loader_word};

const PHASE_BOUND: usize = 94;
const LOWER_FIVE_ONES: u32 = 121;
const FIVE_TRIT_MODULUS: u32 = 243;
const SIXTH_TRIT_RADIX: u32 = 3;

/// Strictly physical N15 input-state search failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LiveInputEncodedStoreError {
    /// No bounded graphical tail yields an injective first data write.
    NoLoadableSeed,
    /// The caller supplied a noncanonical profile.
    UnsupportedProfile,
}

/// Full guest source and actual initial data operand for one encoded input.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LiveInputEncodedStoreSource {
    /// `p` writes its result here, after a real `j`.
    pub data_address: u32,
    /// Loader-initialized `p` operand, not a host-seeded VM word.
    pub initial_data_word: u32,
    /// Zero-based actual `/` code cell.
    pub input_code_address: u32,
    /// Loader-admitted graphical program, including two unreachable tail
    /// cells.
    pub source: Vec<u8>,
    /// Zero-based actual `p` code cell.
    pub store_code_address: u32,
}

/// Build a bounded N15 source retaining all 257 raw `getchar` classes.
///
/// The exhaustive search tries 0..93 `o` prefixes before `/;j;p;v` and
/// at most 94² graphical two-cell tails. Only tails admitted by the strict
/// layout decoder are considered; data operands are read from the six-phase
/// source loader. The first matching seed is canonical by search order.
///
/// This does not produce C23 signed `-1`, canonical C32 frame writes,
/// a second usable read, source arithmetic, or guest-controlled branching.
///
/// # Errors
///
/// Rejects noncanonical profiles or a missing source-loadable seed.
#[expect(
    clippy::excessive_nesting,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    clippy::too_many_lines,
    reason = "exact bounded ternary seed and graphical position search"
)]
pub fn build_live_input_injective_store_source(
    profile: &ProfileDescriptor,
) -> Result<LiveInputEncodedStoreSource, LiveInputEncodedStoreError> {
    use LiveInputEncodedStoreError::{NoLoadableSeed, UnsupportedProfile};
    if profile != current_profile() {
        return Err(UnsupportedProfile);
    }
    for prefix in 0..PHASE_BOUND {
        let mut source = Vec::with_capacity(prefix.saturating_add(6));
        for operation in repeat_n(LinearOpcode::NoOperation, prefix).chain([
            LinearOpcode::InputWord,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::Halt,
        ]) {
            let cell = unique_graphical_cell(profile, operation, source.len())
                .map_err(|_error| NoLoadableSeed)?;
            source.push(cell);
        }
        let Some(&jump_byte) = source.get(prefix.saturating_add(1)) else {
            return Err(NoLoadableSeed);
        };
        let data_address = usize::from(jump_byte).saturating_add(1);
        if data_address <= source.len().saturating_add(2)
            || data_address
                >= usize::try_from(profile.memory_words()).unwrap_or(0)
        {
            continue;
        }
        for first in 33..=126u8 {
            if unique_graphical_cell(
                profile,
                LinearOpcode::SkippedDataByte { byte: u32::from(first) },
                source.len(),
            ) != Ok(first)
            {
                continue;
            }
            source.push(first);
            for last in 33..=126u8 {
                if unique_graphical_cell(
                    profile,
                    LinearOpcode::SkippedDataByte { byte: u32::from(last) },
                    source.len(),
                ) != Ok(last)
                {
                    continue;
                }
                source.push(last);
                let seed =
                    unwritten_loader_word(&source, data_address, profile)
                        .map_err(|_error| NoLoadableSeed)?;
                if seed % FIVE_TRIT_MODULUS == LOWER_FIVE_ONES
                    && (seed / FIVE_TRIT_MODULUS) % SIXTH_TRIT_RADIX != 2
                {
                    return Ok(LiveInputEncodedStoreSource {
                        data_address: u32::try_from(data_address)
                            .map_err(|_error| NoLoadableSeed)?,
                        initial_data_word: seed,
                        input_code_address: u32::try_from(prefix)
                            .map_err(|_error| NoLoadableSeed)?,
                        source,
                        store_code_address: u32::try_from(
                            prefix.saturating_add(2),
                        )
                        .map_err(|_error| NoLoadableSeed)?,
                    });
                }
                _ = source.pop();
            }
            _ = source.pop();
        }
    }
    Err(NoLoadableSeed)
}
