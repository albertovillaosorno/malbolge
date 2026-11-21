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
//   - Source-linked reentry of the exact raw input data cell by guest j.
// - Must-Not:
//   - Confuse data-pointer reentry with code branching or signed C32 EOF.
// - Allows:
//   - Inputs: current N15 profile and bounded source/loader geometry.
//   - Outputs: graphical guest source with two stores and two final jumps.
//   - Side effects: none; real VM execution is tested independently.
// - Split-When:
//   - A verified dynamic-CFG guest data/branch linker consumes this primitive.
// - Merge-When:
//   - The exact byte-state writer owns physical relocation after the store.
// - Summary:
//   - A second j reads genuinely overwritten byte state to relocate D.
//
//! Physical input-dependent *data* relocation after an exact raw word store.

use std::iter::repeat_n;

use malbolge::{ProfileDescriptor, current_profile};

use super::byte_exact_input_store::{IDENTITY_OPERAND, exact_store_address};
use super::{
    ByteExactInputStoreError, ByteExactInputStoreSource, LinearOpcode,
    unique_graphical_cell, unwritten_loader_word,
};

const CODE_PHASES: usize = 94;
const MAX_RESET_PADDING: usize = 14;
const GRAPHICAL_START: u8 = 33;
const GRAPHICAL_END: u8 = 126;

/// Physical exact byte store followed by two real D relocations.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ByteExactInputReentrySource {
    /// Final `j` reads the input-overwritten store cell itself.
    pub input_reentry_code_address: u32,
    /// First `j` after the store returns D to the overwritten address.
    pub reset_code_address: u32,
    /// Untouched loader cell read by the reset `j`.
    pub reset_data_address: u32,
    /// Source-loadable pointer back to the raw input cell, minus one.
    pub reset_loader_word: u32,
    /// No-effect instructions before the final two jumps.
    pub reset_padding: usize,
    /// Actual two crazy stores, source and data addresses.
    pub store: ByteExactInputStoreSource,
}

struct SourceGeometry<'source> {
    first_address: usize,
    padding: usize,
    prefix: usize,
    source: &'source [u8],
}

struct ReentryPlacement {
    exact_data_address: usize,
    reset_data_address: usize,
    reset_loader_word: u32,
}

// Source arithmetic is performed only after a complete, virgin loader chain
// has independently met its exact data and return-pointer constraints.
fn complete_reentry_plan(
    geometry: &SourceGeometry<'_>,
    source: Vec<u8>,
    placement: &ReentryPlacement,
) -> Result<ByteExactInputReentrySource, ByteExactInputStoreError> {
    use ByteExactInputStoreError::NoLoadablePlacement;
    let word = |address: usize| {
        u32::try_from(address).map_err(|_error| NoLoadablePlacement)
    };
    let reset_code_address = geometry
        .prefix
        .saturating_add(5)
        .saturating_add(geometry.padding);
    Ok(ByteExactInputReentrySource {
        input_reentry_code_address: word(reset_code_address.saturating_add(1))?,
        reset_code_address: word(reset_code_address)?,
        reset_data_address: word(placement.reset_data_address)?,
        reset_loader_word: placement.reset_loader_word,
        reset_padding: geometry.padding,
        store: ByteExactInputStoreSource {
            exact_data_address: word(placement.exact_data_address)?,
            exact_initial_word: IDENTITY_OPERAND,
            exact_store_code_address: word(geometry.prefix.saturating_add(4))?,
            first_data_address: word(geometry.first_address)?,
            first_initial_word: IDENTITY_OPERAND,
            first_store_code_address: word(geometry.prefix.saturating_add(2))?,
            input_code_address: word(geometry.prefix)?,
            source,
        },
    })
}

// Only virgin words may authorize this return. A later j will then read the
// *overwritten* second p destination, never an assumed source loader value.
fn candidate_with_reentry(
    profile: &ProfileDescriptor,
    geometry: &SourceGeometry<'_>,
) -> Result<Option<ByteExactInputReentrySource>, ByteExactInputStoreError> {
    use ByteExactInputStoreError::NoLoadablePlacement;
    let tail_start = geometry.source.len();
    let pairs = (GRAPHICAL_START..=GRAPHICAL_END).flat_map(|first| {
        (GRAPHICAL_START..=GRAPHICAL_END).map(move |last| (first, last))
    });
    for (first, last) in pairs {
        let first_opcode =
            LinearOpcode::SkippedDataByte { byte: u32::from(first) };
        let second_opcode =
            LinearOpcode::SkippedDataByte { byte: u32::from(last) };
        if unique_graphical_cell(profile, first_opcode, tail_start) != Ok(first)
            || unique_graphical_cell(
                profile,
                second_opcode,
                tail_start.saturating_add(1),
            ) != Ok(last)
        {
            continue;
        }
        let mut source = geometry.source.to_vec();
        source.extend([first, last]);
        let Some(exact_data_address) = exact_store_address(
            &source,
            geometry.first_address,
            profile,
            IDENTITY_OPERAND,
        )?
        else {
            continue;
        };
        let reset_data_address = exact_data_address
            .saturating_add(1)
            .saturating_add(geometry.padding);
        if reset_data_address <= source.len().saturating_add(2)
            || reset_data_address
                >= usize::try_from(profile.memory_words()).unwrap_or(0)
            || reset_data_address == geometry.first_address
        {
            continue;
        }
        let reset_loader_word =
            unwritten_loader_word(&source, reset_data_address, profile)
                .map_err(|_error| NoLoadablePlacement)?;
        if usize::try_from(reset_loader_word).ok()
            != Some(exact_data_address.saturating_sub(1))
        {
            continue;
        }
        return complete_reentry_plan(geometry, source, &ReentryPlacement {
            exact_data_address,
            reset_data_address,
            reset_loader_word,
        })
        .map(Some);
    }
    Ok(None)
}

/// Search an exact input-store source with two physical D relocations after p.
///
/// The first trailing j reads a virgin loader cell that returns D to the
/// exact data address. The next j reads the *written* input word and makes D
/// equal to `raw_input + 1` modulo the physical N15 memory size. This is not
/// a branch of the code pointer, a C32 signed getchar value, or a C loop.
///
/// The finite search bounds are 0..=14 trailing no-ops, 94 prefix phases,
/// and 94 squared printable two-cell loader tails per phase.
///
/// # Errors
///
/// Refuses noncurrent profiles or a missing loadable reset and store chain.
pub fn build_byte_exact_input_reentry_source(
    profile: &ProfileDescriptor,
) -> Result<ByteExactInputReentrySource, ByteExactInputStoreError> {
    use ByteExactInputStoreError::{NoLoadablePlacement, UnsupportedProfile};
    if profile != current_profile() {
        return Err(UnsupportedProfile);
    }
    let memory_words = usize::try_from(profile.memory_words())
        .map_err(|_error| NoLoadablePlacement)?;
    for padding in 0..=MAX_RESET_PADDING {
        for prefix in 0..CODE_PHASES {
            let mut source = Vec::new();
            let tail = [
                LinearOpcode::InputWord,
                LinearOpcode::RelocateDataPointer,
                LinearOpcode::CrazyData,
                LinearOpcode::RelocateDataPointer,
                LinearOpcode::CrazyData,
            ];
            for opcode in repeat_n(LinearOpcode::NoOperation, prefix)
                .chain(tail)
                .chain(repeat_n(LinearOpcode::NoOperation, padding))
                .chain([
                    LinearOpcode::RelocateDataPointer,
                    LinearOpcode::RelocateDataPointer,
                    LinearOpcode::Halt,
                ])
            {
                source.push(
                    unique_graphical_cell(profile, opcode, source.len())
                        .map_err(|_error| NoLoadablePlacement)?,
                );
            }
            let first_byte = source
                .get(prefix.saturating_add(1))
                .copied()
                .ok_or(NoLoadablePlacement)?;
            let first_address = usize::from(first_byte).saturating_add(1);
            if first_address <= source.len().saturating_add(2)
                || first_address.saturating_add(1) >= memory_words
            {
                continue;
            }
            let geometry = SourceGeometry {
                first_address,
                padding,
                prefix,
                source: &source,
            };
            if let Some(plan) = candidate_with_reentry(profile, &geometry)? {
                return Ok(plan);
            }
        }
    }
    Err(NoLoadablePlacement)
}

/// A fixed source-loaded continuation that reloads the first input after `/`.
///
/// The first read is copied to M73 at C17 using two physical crazy stores.
/// The second read at C25 replaces A, but C28 repositions D using virgin
/// M78=72, then C29 reads the *previously written* M73. Consequently the
/// data pointer after C29 depends on the first input, while A retains the
/// second input (or raw N15 EOF). C24/C26 output the raw accumulator bytes
/// and C60 halts. The terminal C61/C62 tail seeds the two identity stores.
/// This does not implement C23 EOF normalization, an input-controlled branch,
/// arithmetic or a repeatable source-C loop.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ByteExactTwoInputReentrySource {
    /// Exact graphical N15 source; the last two cells are never fetched.
    pub source: Vec<u8>,
    /// First input's exact raw word is physically stored here.
    pub first_input_data_address: u32,
    /// Actual second input opcode source address.
    pub second_input_code_address: u32,
    /// First `j` after second input, reading the untouched reset word.
    pub reset_code_address: u32,
    /// Second `j` after second input, reading the first input's stored word.
    pub reload_code_address: u32,
    /// Terminal reached halt code address (not including loader-tail cells).
    pub halt_code_address: u32,
}

/// Link the exact first raw input store to another physical guest input.
///
/// This fixed 63-cell continuation extends the existing exact first-input
/// identity store. Its source-loaded C59/C60 tail must reproduce the virgin
/// M73 and M121 all-one words and M78=72. No host input or target memory
/// mutations participate in construction; all actual guest operations need
/// separate normative VM verification. Only the canonical N15 profile and
/// the exact checked first-input geometry are accepted.
///
/// # Errors
///
/// Refuses other profiles, altered original store placement, an unavailable
/// graphical instruction encoding, invalid skipped data bytes or loader
/// words that do not satisfy the fixed exact-store/reentry contract.
pub fn build_byte_exact_two_input_reentry_source(
    profile: &ProfileDescriptor,
) -> Result<ByteExactTwoInputReentrySource, ByteExactInputStoreError> {
    use ByteExactInputStoreError::NoLoadablePlacement;
    use LinearOpcode as Opcode;

    let original = build_byte_exact_input_reentry_source(profile)?;
    if original.store.source.len() != 27
        || original.store.input_code_address != 13
        || original.store.first_store_code_address != 15
        || original.store.exact_store_code_address != 17
        || original.store.exact_data_address != 73
        || original.reset_code_address != 22
        || original.reset_data_address != 78
        || original.reset_loader_word != 72
    {
        return Err(NoLoadablePlacement);
    }
    let mut source = original.store.source;
    source.truncate(23);
    for position in 23..=60usize {
        let operation = match position {
            24 | 26 => Opcode::OutputByte,
            25 => Opcode::InputWord,
            28 | 29 => Opcode::RelocateDataPointer,
            60 => Opcode::Halt,
            _ => Opcode::NoOperation,
        };
        source.push(
            unique_graphical_cell(profile, operation, position)
                .map_err(|_error| NoLoadablePlacement)?,
        );
    }
    for (position, byte) in [(61, b'%'), (62, b'H')] {
        source.push(
            unique_graphical_cell(
                profile,
                Opcode::SkippedDataByte { byte: u32::from(byte) },
                position,
            )
            .map_err(|_error| NoLoadablePlacement)?,
        );
    }
    if source.len() != 63
        || unwritten_loader_word(&source, 73, profile)
            .map_err(|_error| NoLoadablePlacement)?
            != IDENTITY_OPERAND
        || unwritten_loader_word(&source, 78, profile)
            .map_err(|_error| NoLoadablePlacement)?
            != 72
        || unwritten_loader_word(&source, 121, profile)
            .map_err(|_error| NoLoadablePlacement)?
            != IDENTITY_OPERAND
    {
        return Err(NoLoadablePlacement);
    }
    Ok(ByteExactTwoInputReentrySource {
        source,
        first_input_data_address: 73,
        second_input_code_address: 25,
        reset_code_address: 28,
        reload_code_address: 29,
        halt_code_address: 60,
    })
}
