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
//   - Source-loaded, full-byte-injective N15 input-dependent memory writes.
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
//   - Retains independently all 256 bytes and true EOF through real guest p.

//! Source-loaded guest writes retaining all 257 raw-input classes.
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
    /// No bounded graphical tail yields the requested injective data stores.
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

/// Two separately retained, source-loaded raw input words in a real N15 guest.
///
/// The second `j` reads an untouched loader-expanded word two cells past the
/// first store, then moves D to a second, disjoint destination. Each `p`
/// retains every byte and true EOF without a host-provided memory seed.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LiveTwoInputEncodedStoreSource {
    /// Address written by the first reached `p`.
    pub first_data_address: u32,
    /// Unmodified loader word read by the first `p`.
    pub first_initial_data_word: u32,
    /// First reached `/` code address.
    pub first_input_code_address: u32,
    /// First reached `p` code address.
    pub first_store_code_address: u32,
    /// Address written by the second reached `p`, distinct from the first.
    pub second_data_address: u32,
    /// Unmodified loader word read by the second `p`.
    pub second_initial_data_word: u32,
    /// Second reached `/` code address.
    pub second_input_code_address: u32,
    /// Second reached `p` code address.
    pub second_store_code_address: u32,
    /// Complete graphical source, including two unreachable loader-tail cells.
    pub source: Vec<u8>,
}

/// Predicate for lossless raw 0..255 and EOF in a single guest crazy word.
///
/// Five low seed trits must be one. Since successful input values occupy
/// only trits 0 and 1 at position five, its seed trit must not equal two.
#[expect(
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "exact ternary byte and EOF input encoding test"
)]
const fn retains_all_raw_inputs(seed: u32) -> bool {
    seed % FIVE_TRIT_MODULUS == LOWER_FIVE_ONES
        && (seed / FIVE_TRIT_MODULUS) % SIXTH_TRIT_RADIX != 2
}

/// Reuse the same finite graphical source/loader-tail census for one or two
/// source-backed input stores. The callback may require an additional, truly
/// disjoint address but cannot substitute a synthetic loader word.
#[expect(
    clippy::excessive_nesting,
    clippy::too_many_lines,
    reason = "exact bounded loader seed and graphical phase enumeration"
)]
fn find_injective_source<T>(
    profile: &ProfileDescriptor,
    suffix: &[LinearOpcode],
    mut accept: impl FnMut(
        &[u8],
        usize,
        u32,
        usize,
    ) -> Result<Option<T>, LiveInputEncodedStoreError>,
) -> Result<T, LiveInputEncodedStoreError> {
    use LiveInputEncodedStoreError::{NoLoadableSeed, UnsupportedProfile};
    if profile != current_profile() {
        return Err(UnsupportedProfile);
    }
    let memory_words = usize::try_from(profile.memory_words())
        .map_err(|_error| NoLoadableSeed)?;
    for prefix in 0..PHASE_BOUND {
        let mut source = Vec::with_capacity(
            prefix.saturating_add(suffix.len()).saturating_add(2),
        );
        for operation in repeat_n(LinearOpcode::NoOperation, prefix)
            .chain(suffix.iter().copied())
        {
            let cell = unique_graphical_cell(profile, operation, source.len())
                .map_err(|_error| NoLoadableSeed)?;
            source.push(cell);
        }
        let Some(&jump_byte) = source.get(prefix.saturating_add(1)) else {
            return Err(NoLoadableSeed);
        };
        let first_data_address = usize::from(jump_byte).saturating_add(1);
        if first_data_address <= source.len().saturating_add(2)
            || first_data_address >= memory_words
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
                    unwritten_loader_word(&source, first_data_address, profile)
                        .map_err(|_error| NoLoadableSeed)?;
                if retains_all_raw_inputs(seed)
                    && let Some(plan) =
                        accept(&source, first_data_address, seed, prefix)?
                {
                    return Ok(plan);
                }
                _ = source.pop();
            }
            _ = source.pop();
        }
    }
    Err(NoLoadableSeed)
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
pub fn build_live_input_injective_store_source(
    profile: &ProfileDescriptor,
) -> Result<LiveInputEncodedStoreSource, LiveInputEncodedStoreError> {
    use LiveInputEncodedStoreError::NoLoadableSeed;
    find_injective_source(
        profile,
        &[
            LinearOpcode::InputWord,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::Halt,
        ],
        |source, data_address, seed, prefix| {
            Ok(Some(LiveInputEncodedStoreSource {
                data_address: u32::try_from(data_address)
                    .map_err(|_error| NoLoadableSeed)?,
                initial_data_word: seed,
                input_code_address: u32::try_from(prefix)
                    .map_err(|_error| NoLoadableSeed)?,
                source: source.to_vec(),
                store_code_address: u32::try_from(prefix.saturating_add(2))
                    .map_err(|_error| NoLoadableSeed)?,
            }))
        },
    )
}

/// Build a bounded source preserving two independent raw input observations.
///
/// Exhausts 0..93 no-op prefixes and at most 94² legal graphical tails of
/// `/;j;p;/;j;p;v`. No data word is host-seeded. The second `j` reads the
/// original loader word at `first_data_address + 2`, never the first written
/// cell. Both stores must admit all 257 byte/EOF classes independently.
///
/// This does not normalize signed C23 input, implement a source-C local,
/// branch on EOF, combine the words into arithmetic, or link the checksum.
///
/// # Errors
///
/// Refuses noncurrent profiles and the absence of a safe two-store layout.
pub fn build_live_two_input_injective_store_source(
    profile: &ProfileDescriptor,
) -> Result<LiveTwoInputEncodedStoreSource, LiveInputEncodedStoreError> {
    use LiveInputEncodedStoreError::NoLoadableSeed;
    find_injective_source(
        profile,
        &[
            LinearOpcode::InputWord,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::InputWord,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::Halt,
        ],
        |source, first_data_address, first_seed, prefix| {
            let memory_words =
                usize::try_from(profile.memory_words()).unwrap_or(0);
            let word = |value: usize| {
                u32::try_from(value).map_err(|_error| NoLoadableSeed)
            };
            let jump_address = first_data_address.saturating_add(2);
            if jump_address >= memory_words {
                return Ok(None);
            }
            let second_jump =
                unwritten_loader_word(source, jump_address, profile)
                    .map_err(|_error| NoLoadableSeed)?;
            let second_data_address =
                usize::try_from(second_jump.saturating_add(1))
                    .map_err(|_error| NoLoadableSeed)?;
            if second_data_address <= source.len().saturating_add(2)
                || second_data_address >= memory_words
                || second_data_address == first_data_address
            {
                return Ok(None);
            }
            let second_seed =
                unwritten_loader_word(source, second_data_address, profile)
                    .map_err(|_error| NoLoadableSeed)?;
            if !retains_all_raw_inputs(second_seed) {
                return Ok(None);
            }
            Ok(Some(LiveTwoInputEncodedStoreSource {
                first_data_address: word(first_data_address)?,
                first_initial_data_word: first_seed,
                first_input_code_address: word(prefix)?,
                first_store_code_address: word(prefix.saturating_add(2))?,
                second_data_address: word(second_data_address)?,
                second_initial_data_word: second_seed,
                second_input_code_address: word(prefix.saturating_add(3))?,
                second_store_code_address: word(prefix.saturating_add(5))?,
                source: source.to_vec(),
            }))
        },
    )
}
