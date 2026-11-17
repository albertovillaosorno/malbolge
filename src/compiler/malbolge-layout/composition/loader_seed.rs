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
//   - Exact graphical source-tail selection for loader-derived data words.
// - Must-Not:
//   - Claim a guest performed requested rotations or rewound its data pointer.
// - Allows:
//   - Inputs: fixed source length, expanded operand address and word targets.
//   - Outputs: loadable two-byte tail or bounded, explicit failure.
//   - Side effects: none.
// - Split-When:
//   - Source-loaded data placement requires arbitrary initialized memory.
// - Merge-When:
//   - General linkage proves all source-tail and guest data preparations.
// - Summary:
//   - Rejects source-position-invalid EOF conversion seeds before layout.

//! Construct an exact graphical loader seed, not guest-executed arithmetic.
//!
//! The last two source cells determine the untouched expanded-memory image.
//! This finite search chooses only source-loadable bytes at their *physical*
//! addresses. A requested rotation is a target word constraint: no guest
//! instruction is synthesized or executed here. The normal layout and VM
//! must separately prove the requested writes and input/output behavior.

use malbolge::{ProfileDescriptor, profile_rotate};

use super::{
    GRAPHICAL_END, GRAPHICAL_START, LinearOpcode, MAX_LINEAR_CELLS,
    MIN_SOURCE_CELLS, unique_graphical_cell, unwritten_loader_word,
};

/// Exact failure before generating a graphical loader-data suffix.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LoaderSeedSelectionError {
    /// Source size, data address or rotation budget lies outside the profile.
    InvalidGeometry,
    /// At least one requested data word lies outside profile memory values.
    InvalidOperand,
    /// Every printable two-byte tail failed source decode or data identity.
    NoLoadableSeed,
}

/// Find a two-byte graphical source suffix matching one rotated data word
/// and its untouched adjacent successor at known expanded addresses.
///
/// This does not rotate memory. The caller must emit and independently
/// verify the guest `*` instructions that would prepare `required[0]`,
/// and must preserve the adjacent `required[1]` until its guest read.
/// Search order is byte-lexicographic and independent of host randomness.
///
/// # Errors
///
/// Rejects impossible physical lengths/addresses, invalid word values,
/// or failure of the complete 94-by-94 printable-tail search.
pub fn select_rotated_loader_seed(
    profile: &ProfileDescriptor,
    source_length: usize,
    first_data_address: u32,
    first_rotations: u8,
    required: [u32; 2],
) -> Result<[u8; 2], LoaderSeedSelectionError> {
    let memory_words = usize::try_from(profile.memory_words())
        .map_err(|_error| LoaderSeedSelectionError::InvalidGeometry)?;
    let first_address = usize::try_from(first_data_address)
        .map_err(|_error| LoaderSeedSelectionError::InvalidGeometry)?;
    if !(MIN_SOURCE_CELLS..=MAX_LINEAR_CELLS).contains(&source_length)
        || source_length > memory_words
        || first_address < source_length
        || first_address.saturating_add(1) >= memory_words
        || first_rotations >= profile.word_trits()
    {
        return Err(LoaderSeedSelectionError::InvalidGeometry);
    }
    if required.iter().any(|&word| word >= profile.word_modulus()) {
        return Err(LoaderSeedSelectionError::InvalidOperand);
    }

    let first_position = source_length - 2;
    let last_position = source_length - 1;
    // The two-cell virtual source has the same loader recurrence and its
    // first expanded address is virtual address two. The real source prefix
    // is irrelevant to the recurrence but still fixes decode positions.
    let offset = first_address - source_length;
    let virtual_address = offset
        .checked_add(2)
        .ok_or(LoaderSeedSelectionError::InvalidGeometry)?;
    for first in GRAPHICAL_START..=GRAPHICAL_END {
        if unique_graphical_cell(
            profile,
            LinearOpcode::SkippedDataByte { byte: u32::from(first) },
            first_position,
        ) != Ok(first)
        {
            continue;
        }
        for second in GRAPHICAL_START..=GRAPHICAL_END {
            if unique_graphical_cell(
                profile,
                LinearOpcode::SkippedDataByte { byte: u32::from(second) },
                last_position,
            ) != Ok(second)
            {
                continue;
            }
            let seed = [first, second];
            let first_word =
                unwritten_loader_word(&seed, virtual_address, profile)
                    .map_err(|_error| {
                        LoaderSeedSelectionError::InvalidGeometry
                    })?;
            let adjacent =
                unwritten_loader_word(&seed, virtual_address + 1, profile)
                    .map_err(|_error| {
                        LoaderSeedSelectionError::InvalidGeometry
                    })?;
            if adjacent != required[1] {
                continue;
            }
            let mut rotated = first_word;
            for _ in 0..first_rotations {
                rotated = profile_rotate(rotated, profile.word_modulus());
            }
            if rotated == required[0] {
                return Ok(seed);
            }
        }
    }
    Err(LoaderSeedSelectionError::NoLoadableSeed)
}
