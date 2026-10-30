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
//   - A bounded research Malbolge source whose guest reads one CEB2 data cell.
// - Must-Not:
//   - Claim a decoder, guest interpreter, source authentication or echo loop.
// - Allows:
//   - Inputs: separately trusted canonical ternary source and bound descriptor.
//   - Outputs: source-position-valid graphical bytes and host-only admission.
//   - Side effects: bounded allocation only; actual VM execution in tests.
// - Split-When:
//   - The guest decodes and executes descriptor operations, not only a cell.
// - Merge-When:
//   - A production Malbolge runtime linker supports verified data residence.
// - Summary:
//   - Proves an actual guest rotate and output reads resident CEB2 count bits.
// - Description:
//   - A positional `j`, twelve no-ops, `*`, `<`, `v` probes payload slot 12.
// - Usage:
//   - Bounded compact_guest_bytecode_strategy test-only version-three pilot.
// - Defaults:
//   - The guest reads one cell and halts; it does not execute the echo macro.
//
//! Genuine guest *data read* of one CEB2 count-bit cell; no bytecode decoder.
//!
//! Unlike the v2 halt-before-data probe, `j` at address zero relocates D to
//! the beginning of resident graphical data. Twelve reached no-ops advance D
//! to payload ordinal 12, the low echo-count field's high-varying bits. Guest
//! `*` rotates that **source memory** cell into A; `<` writes A modulo 256;
//! `v` halts. The source remains position-valid and all other descriptor
//! bytes are host-verifiable only. The guest does not inspect or authenticate
//! the CEB2 envelope, count repetitions or interpret bytecode instructions.

use malbolge::{ProfileDescriptor, decode_profile_instruction};

use crate::binding::{BOUND_ECHO_MACRO_BYTES, BoundEchoError, admit_bound_echo_macro};
use crate::strategy::bridge::ternary::TernaryProgram;

const GRAPHICAL_START: u8 = 33;
const GRAPHICAL_END: u8 = 126;
const VALID_LOADER_OPCODES: &[u8; 8] = b"ji*p</vo";
const PREFIX_INSTRUCTIONS: usize = 16;
const NO_OP_COUNT: usize = 12;
const READ_PAYLOAD_ORDINAL: usize = 12;
const PAYLOAD_CELLS: usize = 102;

/// Failure at the host-side literal CEB2 read-probe boundary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GuestPayloadProbeError {
    /// Original canonical source or CEB2 candidate failed independent checks.
    Binding(BoundEchoError),
    /// The payload glyph is not admitted by the selected loader at its address.
    InvalidGlyph {
        /// Loaded position containing a non-loader-admissible glyph.
        position: usize,
    },
    /// Expected exact code/padding or literal CEB2 positions were not present.
    InvalidSource,
    /// The selected instruction has no unique canonical graphical encoding.
    MissingOpcode {
        /// Loaded position at which a unique graphical opcode is absent.
        position: usize,
    },
    /// All two pad bits on the final payload glyph must be zero.
    NoncanonicalPadding,
    /// Code/data regions would overlap or exceed a bounded graphical source.
    UnsupportedPosition,
}

fn instruction_at(position: usize, opcode: u8) -> Result<u8, GuestPayloadProbeError> {
    let pos =
        u32::try_from(position).map_err(|_error| GuestPayloadProbeError::UnsupportedPosition)?;
    let mut allowed = (GRAPHICAL_START..=GRAPHICAL_END)
        .filter(|byte| decode_profile_instruction(u32::from(*byte), pos) == Some(opcode));
    let Some(glyph) = allowed.next() else {
        return Err(GuestPayloadProbeError::MissingOpcode { position });
    };
    if allowed.next().is_some() {
        return Err(GuestPayloadProbeError::MissingOpcode { position });
    }
    Ok(glyph)
}

fn alphabet(position: usize) -> Result<[u8; 8], GuestPayloadProbeError> {
    let pos =
        u32::try_from(position).map_err(|_error| GuestPayloadProbeError::UnsupportedPosition)?;
    let mut glyphs = [0u8; 8];
    let mut count = 0usize;
    for byte in GRAPHICAL_START..=GRAPHICAL_END {
        if decode_profile_instruction(u32::from(byte), pos)
            .is_some_and(|code| VALID_LOADER_OPCODES.contains(&code))
        {
            let Some(slot) = glyphs.get_mut(count) else {
                return Err(GuestPayloadProbeError::UnsupportedPosition);
            };
            *slot = byte;
            count = count.saturating_add(1);
        }
    }
    if count != glyphs.len() {
        return Err(GuestPayloadProbeError::UnsupportedPosition);
    }
    Ok(glyphs)
}

fn guest_prefix(profile: &'static ProfileDescriptor) -> Result<Vec<u8>, GuestPayloadProbeError> {
    let first = instruction_at(0, b'j')?;
    let base = usize::from(first).saturating_add(1);
    if base <= PREFIX_INSTRUCTIONS {
        return Err(GuestPayloadProbeError::UnsupportedPosition);
    }
    let mut source = Vec::with_capacity(base);
    source.push(first);
    // `D = M[0] + 1` after reached `j`; each no-op then advances D once.
    for position in 1..=NO_OP_COUNT {
        source.push(instruction_at(position, b'o')?);
    }
    source.push(instruction_at(NO_OP_COUNT.saturating_add(1), b'*')?);
    source.push(instruction_at(
        NO_OP_COUNT.saturating_add(2),
        profile.output_instruction(),
    )?);
    source.push(instruction_at(NO_OP_COUNT.saturating_add(3), b'v')?);
    for position in source.len()..base {
        source.push(instruction_at(position, b'o')?);
    }
    Ok(source)
}

/// Exact guest data address reached by the single guest rotation.
///
/// The first valid `j` character determines the data pointer after the
/// relocation; no arbitrary host-selected memory pointer is installed.
///
/// # Errors
///
/// Refuses any profile source whose first graphical `j` cannot be resolved.
pub fn guest_read_address(
    profile: &'static ProfileDescriptor,
) -> Result<u32, GuestPayloadProbeError> {
    let prefix = guest_prefix(profile)?;
    u32::try_from(prefix.len().saturating_add(READ_PAYLOAD_ORDINAL))
        .map_err(|_error| GuestPayloadProbeError::UnsupportedPosition)
}

/// Counts the entire position-valid source including inert padding and data.
///
/// # Errors
///
/// Refuses an unrepresentable or non-unique first relocation instruction.
pub fn guest_probe_source_cells(
    profile: &'static ProfileDescriptor,
) -> Result<usize, GuestPayloadProbeError> {
    Ok(guest_prefix(profile)?.len().saturating_add(PAYLOAD_CELLS))
}

/// Proposes the resident CEB2 source with one genuine guest data-dependent read.
///
/// The descriptor is admitted against a separately trusted source and profile
/// before any source image is made. The source's guest code still only rotates
/// one count-bearing loaded word and outputs its low byte, then halts.
///
/// # Errors
///
/// Rejects forged candidates, unsupported address layout and insufficient
/// loader-valid glyph capacity at any position.
#[expect(clippy::integer_division, reason = "exact three-bit descriptor groups")]
#[expect(clippy::integer_division_remainder_used, reason = "octet bit indexing")]
#[expect(clippy::arithmetic_side_effects, reason = "fixed bounded bit offsets")]
pub fn embed_guest_payload_probe(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    candidate: &[u8],
) -> Result<Vec<u8>, GuestPayloadProbeError> {
    let _admitted = admit_bound_echo_macro(program, profile, candidate)
        .map_err(GuestPayloadProbeError::Binding)?;
    let mut source = guest_prefix(profile)?;
    for index in 0..PAYLOAD_CELLS {
        let mut ordinal = 0u8;
        for digit in 0..3usize {
            let bit = index.saturating_mul(3).saturating_add(digit);
            let one = candidate
                .get(bit / 8)
                .map_or(0, |byte| (byte >> (7 - bit % 8)) & 1);
            ordinal = (ordinal << 1u32) | one;
        }
        let options = alphabet(source.len())?;
        source.push(
            *options
                .get(usize::from(ordinal))
                .ok_or(GuestPayloadProbeError::UnsupportedPosition)?,
        );
    }
    Ok(source)
}

/// Host-only independent reader of the guest's CEB2 source memory image.
///
/// This validates exact code/filler positions and reconstructs the complete
/// original 38-byte descriptor from the loader glyph ranks. Guest `j/*/</v`
/// **does not** execute these checks or dispatch any embedded operations.
///
/// # Errors
///
/// Rejects shifted/mutated code, altered data, malformed pad bits or a
/// candidate unbound to the separately supplied canonical original source.
#[expect(clippy::integer_division, reason = "exact octet bit reconstruction")]
#[expect(clippy::integer_division_remainder_used, reason = "octet bit indexing")]
#[expect(clippy::arithmetic_side_effects, reason = "fixed bounded bit offsets")]
pub fn admit_guest_payload_probe(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<[u8; BOUND_ECHO_MACRO_BYTES], GuestPayloadProbeError> {
    let prefix = guest_prefix(profile)?;
    if source.len() != prefix.len().saturating_add(PAYLOAD_CELLS)
        || source.get(..prefix.len()) != Some(prefix.as_slice())
    {
        return Err(GuestPayloadProbeError::InvalidSource);
    }
    let mut candidate = [0u8; BOUND_ECHO_MACRO_BYTES];
    let Some(payload) = source.get(prefix.len()..) else {
        return Err(GuestPayloadProbeError::InvalidSource);
    };
    for (position_offset, &glyph) in payload.iter().enumerate() {
        let position = prefix.len().saturating_add(position_offset);
        let options = alphabet(position)?;
        let rank = options
            .iter()
            .position(|&option| option == glyph)
            .ok_or(GuestPayloadProbeError::InvalidGlyph { position })?;
        for digit in 0..3usize {
            let bit = position_offset.saturating_mul(3).saturating_add(digit);
            let one = (rank >> (2 - digit)) & 1;
            if let Some(byte) = candidate.get_mut(bit / 8) {
                *byte |= u8::from(one != 0) << (7 - bit % 8);
            } else if one != 0 {
                return Err(GuestPayloadProbeError::NoncanonicalPadding);
            }
        }
    }
    let _admitted = admit_bound_echo_macro(program, profile, &candidate)
        .map_err(GuestPayloadProbeError::Binding)?;
    Ok(candidate)
}

/// Publishes a bounded guest-indirect-dispatch experiment based on CEB2 data.
///
/// After the same real `j` relocation and twelve no-ops as the v3 probe,
/// position 13 executes `i` instead of `*`. This reads `M[53]` from the
/// resident descriptor and relocates C to that *graphical glyph's numeric
/// word*. The profile VM encrypts `M[C]`, then increments C. Its very next
/// fetched instruction is at `M[53] + 1`, a position in the original CEB2
/// descriptor tail, not an opcode chosen by the host. It is an exploratory
/// **indirect data-dependent code fetch**, not decoding the packed rank or
/// implementing an echo interpreter. Host-side provenance must be verified
/// separately; this guest code does not authenticate the descriptor.
///
/// # Errors
///
/// Rejects noncanonical upstream source/candidate, or an unsupported exact
/// graphical encoding of `i` at the fixed dispatch instruction position.
pub fn embed_guest_indirect_dispatch_probe(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    candidate: &[u8],
) -> Result<Vec<u8>, GuestPayloadProbeError> {
    let mut source = embed_guest_payload_probe(program, profile, candidate)?;
    let dispatch = instruction_at(NO_OP_COUNT.saturating_add(1), b'i')?;
    let slot = source
        .get_mut(NO_OP_COUNT.saturating_add(1))
        .ok_or(GuestPayloadProbeError::InvalidSource)?;
    *slot = dispatch;
    Ok(source)
}

/// Separately verifies the exact CEB2-bearing source used for guest dispatch.
///
/// Unlike the guest, the host re-admits the full descriptor against a trusted
/// canonical ternary program and selected profile. The only permitted
/// difference from the v3 resident source is code position 13, where `i`
/// replaces the original `*`. This function is **not** a guest interpreter.
///
/// # Errors
///
/// Rejects a wrong dispatch cell, all mutated suffix/code glyphs, shifted
/// source, foreign profile or unbound source identity.
pub fn admit_guest_indirect_dispatch_probe(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<[u8; BOUND_ECHO_MACRO_BYTES], GuestPayloadProbeError> {
    let position = NO_OP_COUNT.saturating_add(1);
    if source.get(position) != Some(&instruction_at(position, b'i')?) {
        return Err(GuestPayloadProbeError::InvalidSource);
    }
    let mut reverted = source.to_vec();
    let slot = reverted
        .get_mut(position)
        .ok_or(GuestPayloadProbeError::InvalidSource)?;
    *slot = instruction_at(position, b'*')?;
    admit_guest_payload_probe(program, profile, &reverted)
}
