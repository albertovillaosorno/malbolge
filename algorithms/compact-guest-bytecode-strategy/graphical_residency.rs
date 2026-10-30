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
//   - Research-only, loader-admitted graphical data placement for CEB2 bytes.
// - Must-Not:
//   - Claim a Malbolge guest decoder, interpreter, or general bytecode backend.
// - Allows:
//   - Inputs: validated CEB2 candidate, original ternary source and profile.
//   - Outputs: a direct one-echo executable plus inert resident source payload.
//   - Side effects: bounded in-memory allocation only.
// - Split-When:
//   - A guest interpreter actually reads/dispatches the resident payload.
// - Merge-When:
//   - A verified production code/data linker owns literal payload residency.
// - Summary:
//   - Measures a concrete position-sensitive source-cell cost for CEB2 bytes.
// - Description:
//   - Packs three descriptor bits into each of eight loader-admissible glyphs.
// - Usage:
//   - Only the compact_guest_bytecode_strategy bounded research integration.
// - Defaults:
//   - A three-cell echo prefix halts before the resident graphical data tail.
//
//! CEB2 source residency experiment, **not** guest bytecode interpretation.
//!
//! Every graphical source cell has only eight choices that pass the real
//! position-sensitive Malbolge loader. A literal 38-byte CEB2 proposal thus
//! needs 102 three-bit graphical cells; a separate three-cell direct echo
//! prefix executes once and halts before reading the proposal. The host alone
//! checks and reconstructs the bytes. The VM loads those cells as memory, but
//! does not dispatch or authenticate a single bytecode operation.

use malbolge::{ProfileDescriptor, decode_profile_instruction};

use crate::binding::{BOUND_ECHO_MACRO_BYTES, BoundEchoError, admit_bound_echo_macro};
use crate::strategy::bridge::layout::{LinearLayoutError, LinearOpcode, encode_linear_layout};
use crate::strategy::bridge::ternary::TernaryProgram;

const GRAPHICAL_MIN: u8 = 33;
const GRAPHICAL_MAX: u8 = 126;
const LOADER_OPCODE_SET: [u8; 8] = *b"ji*p</vo";

/// Source-cell count for the 38-byte bound CEB2 payload, with two pad bits.
pub const GRAPHICAL_PAYLOAD_CELLS: usize = 102;
/// Three direct echo instructions plus the packed, never-executed data tail.
pub const GRAPHICAL_TOTAL_CELLS: usize = GRAPHICAL_PAYLOAD_CELLS + 3;
const PREFIX_CELLS: usize = 3;

/// Fail-closed descriptor-residency admission failures.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GraphicalResidencyError {
    /// The CEB2 descriptor or its canonical upstream source was not admitted.
    Binding(BoundEchoError),
    /// At least one data cell does not decode to a loader-permitted instruction.
    InvalidPayloadCell {
        /// Zero-based invalid source position.
        position: usize,
    },
    /// A fixed direct echo prefix cannot be constructed for this profile.
    Layout(LinearLayoutError),
    /// Host input length is not exactly the bounded CEB2 resident image.
    LengthMismatch,
    /// Every loader-admissible ordinal is unique; padding bits must be zero.
    NoncanonicalPadding,
    /// The executable prefix is not the independently admitted direct echo.
    PrefixMismatch,
    /// The profile's available graphical opcode alphabet is not exactly eight.
    UnexpectedAlphabet {
        /// Zero-based position where eight loader glyphs were not available.
        position: usize,
    },
}

fn alphabet(position: usize) -> Result<[u8; 8], GraphicalResidencyError> {
    let mut allowed = [0u8; 8];
    let mut count = 0usize;
    let position_u32 = u32::try_from(position)
        .map_err(|_error| GraphicalResidencyError::UnexpectedAlphabet { position })?;
    for glyph in GRAPHICAL_MIN..=GRAPHICAL_MAX {
        let decoded = decode_profile_instruction(u32::from(glyph), position_u32);
        if decoded.is_some_and(|instruction| LOADER_OPCODE_SET.contains(&instruction)) {
            let Some(slot) = allowed.get_mut(count) else {
                return Err(GraphicalResidencyError::UnexpectedAlphabet { position });
            };
            *slot = glyph;
            count = count.saturating_add(1);
        }
    }
    if count != allowed.len() {
        return Err(GraphicalResidencyError::UnexpectedAlphabet { position });
    }
    Ok(allowed)
}

fn prefix(profile: &'static ProfileDescriptor) -> Result<Vec<u8>, GraphicalResidencyError> {
    let source = encode_linear_layout(
        profile,
        &[
            LinearOpcode::InputWord,
            LinearOpcode::OutputByte,
            LinearOpcode::Halt,
        ],
    )
    .map_err(GraphicalResidencyError::Layout)?;
    if source.source().len() != PREFIX_CELLS {
        return Err(GraphicalResidencyError::LengthMismatch);
    }
    Ok(source.source().to_vec())
}

/// Returns the maximum missing full-runtime cells for a strict size win.
///
/// This replaces the v1 one-byte-per-cell assumption with 102 actually
/// loader-admissible literal payload cells. The still-unimplemented `runtime`
/// includes executable prefix, decoder, dispatch, source attestation and all
/// linker costs; the three-cell demonstration is **not** a reusable runtime.
#[must_use]
pub const fn maximum_packed_runtime_cells(direct_cells: usize) -> Option<usize> {
    direct_cells.checked_sub(GRAPHICAL_PAYLOAD_CELLS + 1)
}

/// Embeds an independently admitted CEB2 descriptor after a halt-only prefix.
///
/// All 105 emitted characters are valid at their *exact* loaded addresses.
/// Each descriptor bit is represented by the ordinal of one of eight allowed
/// source glyphs in ascending ASCII order. The last two pad bits are zero.
/// No memory beyond the loader's initial source is assumed to contain bytes.
///
/// # Errors
///
/// Rejects malformed/foreign CEB2 source, unsupported profile, or an
/// unexpected loader opcode alphabet before exposing a source image.
#[expect(
    clippy::integer_division,
    reason = "exact octet addressing of bounded bits"
)]
#[expect(clippy::integer_division_remainder_used, reason = "exact bit packing")]
#[expect(
    clippy::arithmetic_side_effects,
    reason = "bit offsets limited to 0..8"
)]
pub fn embed_bound_resident_source(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    candidate: &[u8],
) -> Result<Vec<u8>, GraphicalResidencyError> {
    let _validated_layout = admit_bound_echo_macro(program, profile, candidate)
        .map_err(GraphicalResidencyError::Binding)?;
    let mut source = prefix(profile)?;
    for cell in 0..GRAPHICAL_PAYLOAD_CELLS {
        let mut ordinal = 0u8;
        for bit in 0..3usize {
            let index = cell.saturating_mul(3).saturating_add(bit);
            let byte = candidate
                .get(index / 8)
                .map_or(0u8, |value| (value >> (7 - index % 8)) & 1);
            ordinal = (ordinal << 1u32) | byte;
        }
        let glyphs = alphabet(source.len())?;
        source.push(*glyphs.get(usize::from(ordinal)).ok_or(
            GraphicalResidencyError::UnexpectedAlphabet {
                position: source.len(),
            },
        )?);
    }
    if source.len() != GRAPHICAL_TOTAL_CELLS {
        return Err(GraphicalResidencyError::LengthMismatch);
    }
    Ok(source)
}

/// Independently re-admits a graphical memory image and its CEB2 bytes.
///
/// A valid encoded image *does not* prove that the guest uses the resident
/// cells. This host verifier checks exact direct prefix, valid loader glyphs,
/// canonical bit padding and source-bound CEB2 identity without trusting the
/// producer's claimed original binary descriptor.
///
/// # Errors
///
/// Rejects malformed, truncated, noncanonical, foreign-source, or
/// incorrectly positioned resident source bytes.
#[expect(
    clippy::integer_division,
    reason = "exact octet addressing of bounded bits"
)]
#[expect(
    clippy::integer_division_remainder_used,
    reason = "exact bit unpacking"
)]
#[expect(
    clippy::arithmetic_side_effects,
    reason = "bit offsets limited to 0..8"
)]
pub fn admit_bound_resident_source(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<[u8; BOUND_ECHO_MACRO_BYTES], GraphicalResidencyError> {
    if source.len() != GRAPHICAL_TOTAL_CELLS {
        return Err(GraphicalResidencyError::LengthMismatch);
    }
    let expected = prefix(profile)?;
    if source.get(..PREFIX_CELLS) != Some(expected.as_slice()) {
        return Err(GraphicalResidencyError::PrefixMismatch);
    }
    let mut reconstructed = [0u8; BOUND_ECHO_MACRO_BYTES];
    let tail = source
        .get(PREFIX_CELLS..)
        .ok_or(GraphicalResidencyError::LengthMismatch)?;
    for (offset, glyph) in tail.iter().copied().enumerate() {
        let position = offset.saturating_add(PREFIX_CELLS);
        let options = alphabet(position)?;
        let ordinal = options
            .iter()
            .position(|allowed| *allowed == glyph)
            .ok_or(GraphicalResidencyError::InvalidPayloadCell { position })?;
        for bit in 0..3usize {
            let index = offset.saturating_mul(3).saturating_add(bit);
            let value = (ordinal >> (2 - bit)) & 1;
            if let Some(byte) = reconstructed.get_mut(index / 8) {
                *byte |= u8::from(value != 0) << (7 - index % 8);
            } else if value != 0 {
                return Err(GraphicalResidencyError::NoncanonicalPadding);
            }
        }
    }
    let _validated_layout = admit_bound_echo_macro(program, profile, &reconstructed)
        .map_err(GraphicalResidencyError::Binding)?;
    Ok(reconstructed)
}
