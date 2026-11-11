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
//   - A bounded source-separated CEB2 indirect-branch feasibility experiment.
// - Must-Not:
//   - Claim bytecode opcode decode, a guest interpreter, or echo equivalence.
// - Allows:
//   - Inputs: separately trusted canonical ternary source/profile/CEB2.
//   - Outputs: loader-valid, host-verifiable graphical Malbolge source.
//   - Side effects: bounded allocation, normative VM execution in tests.
// - Split-When:
//   - A real reusable bytecode decoder, loop or linker is implemented.
// - Merge-When:
//   - The production runtime can verify equivalent protected data dispatch.
// - Summary:
//   - Moves CEB2 data beyond all eight reachable count-selected jump targets.
// - Description:
//   - True guest-indirect control transfer without modifying the CEB2 tail.
// - Usage:
//   - Compact-guest bytecode research pilot v5; never production compilation.
// - Defaults:
//   - All eight graphical glyph ordinals are accepted with no guest decoding.

//! Strict separation of the original CEB2 graphical tail from branch targets.
//!
//! `j@0` makes D=41; eighty reached `o` cells advance D to 121, the
//! thirteenth (zero-based ordinal 12) CEB2 payload cell. A real reached `i`
//! at code position 81 reads this byte and encrypts source cell M[M[121]],
//! then C advances to M[121]+1. A fixed 27-cell inert code interval positions
//! 82..108 separates 102 descriptor glyphs at positions 109..210. At count
//! cell position 121 all eight graphical glyphs have numeric values no
//! greater than 107, ensuring that the mandatory indirect-jump XLAT2 only
//! writes *code* and never damages the resident CEB2 payload. Data remains
//! host-authenticated; no guest SHA-256 or bytecode opcode decode is present.

use malbolge::ProfileDescriptor;

use crate::binding::BOUND_ECHO_MACRO_BYTES;
use crate::guest_probe::{
    GuestPayloadProbeError, admit_guest_payload_probe, alphabet, embed_guest_payload_probe,
    guest_prefix, instruction_at,
};
use crate::strategy::bridge::ternary::TernaryProgram;

/// Number of reached `o` steps after the first Malbolge `j` relocation.
pub const ISOLATED_NO_OPS: usize = 80;
/// Exact reached `i` instruction source position.
pub const ISOLATED_JUMP_POSITION: usize = 81;
/// Beginning of the untouched graphical descriptor after code padding.
pub const ISOLATED_PAYLOAD_START: usize = 109;
/// Exact data-address operand used by the reached guest `i`.
pub const ISOLATED_COUNT_ADDRESS: usize = 121;
/// Loaded Malbolge source cells, including 102 position-packed CEB2 glyphs.
pub const ISOLATED_TOTAL_CELLS: usize = 211;
const OLD_PAYLOAD_START: usize = 41;
const PAYLOAD_CELLS: usize = 102;

// Reached code addresses 91..93 execute `/`, `<`, `v` for rank five.
// Ranks six and seven jump directly to code address 107 or 108 and halt.
// These handlers are a bounded *native instruction* demonstration, not a
// decoder for arbitrary bytecode instructions nor a count-controlled loop.
const HANDLER_OPCODES: [(usize, u8); 5] =
    [(91, b'/'), (92, b'<'), (93, b'v'), (107, b'v'), (108, b'v')];

/// Validates that every legal loaded count glyph points only to code cells.
///
/// # Errors
///
/// Rejects unsupported profile decode or code/data layout geometry.
pub fn validate_isolated_dispatch_geometry() -> Result<(), GuestPayloadProbeError> {
    let options = alphabet(ISOLATED_COUNT_ADDRESS)?;
    if options
        .iter()
        .any(|&glyph| usize::from(glyph) >= ISOLATED_PAYLOAD_START)
        || ISOLATED_COUNT_ADDRESS != ISOLATED_PAYLOAD_START.saturating_add(12)
        || ISOLATED_JUMP_POSITION != ISOLATED_NO_OPS.saturating_add(1)
        || ISOLATED_TOTAL_CELLS != ISOLATED_PAYLOAD_START.saturating_add(PAYLOAD_CELLS)
    {
        return Err(GuestPayloadProbeError::UnsupportedPosition);
    }
    Ok(())
}

fn source_prefix() -> Result<Vec<u8>, GuestPayloadProbeError> {
    validate_isolated_dispatch_geometry()?;
    // The unique `j@0` source glyph must be 40 so the first post-jump D=41.
    let first = instruction_at(0, b'j')?;
    if first != 40 || ISOLATED_JUMP_POSITION >= ISOLATED_PAYLOAD_START {
        return Err(GuestPayloadProbeError::UnsupportedPosition);
    }
    let mut source = Vec::with_capacity(ISOLATED_TOTAL_CELLS);
    source.push(first);
    for position in 1..ISOLATED_PAYLOAD_START {
        let opcode = if position == ISOLATED_JUMP_POSITION {
            b'i'
        } else {
            b'o'
        };
        source.push(instruction_at(position, opcode)?);
    }
    Ok(source)
}

/// Emits an independently host-bound CEB2 candidate with isolated guest code.
///
/// The 102 payload cells are **re-encoded at their new source positions**;
/// graphical glyph bytes cannot be copied unchanged because loader admission
/// is phase dependent. Only each independently decoded three-bit ordinal is
/// preserved. The guest does not decode it, authenticate it, or echo input.
///
/// # Errors
///
/// Rejects unsupported programs, provenance mismatch, illegal loader glyphs,
/// or a layout with any count-selected jump target inside the CEB2 region.
pub fn embed_isolated_guest_dispatch(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    candidate: &[u8],
) -> Result<Vec<u8>, GuestPayloadProbeError> {
    // Delegate source/profile SHA-256 admission to the established CEB2
    // verifier before proposing any new graphical source.
    let old = embed_guest_payload_probe(program, profile, candidate)?;
    let mut source = source_prefix()?;
    let old_tail = old
        .get(OLD_PAYLOAD_START..)
        .ok_or(GuestPayloadProbeError::InvalidSource)?;
    for (index, &glyph) in old_tail.iter().enumerate() {
        let old_pos = OLD_PAYLOAD_START.saturating_add(index);
        let new_pos = ISOLATED_PAYLOAD_START.saturating_add(index);
        let rank = alphabet(old_pos)?
            .iter()
            .position(|&option| option == glyph)
            .ok_or(GuestPayloadProbeError::InvalidGlyph { position: old_pos })?;
        source.push(
            *alphabet(new_pos)?
                .get(rank)
                .ok_or(GuestPayloadProbeError::UnsupportedPosition)?,
        );
    }
    if source.len() != ISOLATED_TOTAL_CELLS {
        return Err(GuestPayloadProbeError::UnsupportedPosition);
    }
    Ok(source)
}

/// Host-only independent full descriptor/source admission for the v5 image.
///
/// This independently checks the exact fixed code, all new-position glyph
/// ranks and their source/profile provenance. It maps those ranks back to
/// the earlier separately tested CEB2 admission helper. The guest itself
/// performs none of these SHA-256/profile/canonical-padding checks.
///
/// # Errors
///
/// Rejects missing/excess cells, code mutation, malformed graphical payload,
/// foreign source, invalid digest, or noncanonical CEB2 trailing pad bits.
pub fn admit_isolated_guest_dispatch(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<[u8; BOUND_ECHO_MACRO_BYTES], GuestPayloadProbeError> {
    let prefix = source_prefix()?;
    if source.len() != ISOLATED_TOTAL_CELLS || source.get(..prefix.len()) != Some(prefix.as_slice())
    {
        return Err(GuestPayloadProbeError::InvalidSource);
    }
    let mut recovered = guest_prefix(profile)?;
    let Some(tail) = source.get(prefix.len()..) else {
        return Err(GuestPayloadProbeError::InvalidSource);
    };
    for (index, &glyph) in tail.iter().enumerate() {
        let new_pos = ISOLATED_PAYLOAD_START.saturating_add(index);
        let old_pos = OLD_PAYLOAD_START.saturating_add(index);
        let rank = alphabet(new_pos)?
            .iter()
            .position(|&option| option == glyph)
            .ok_or(GuestPayloadProbeError::InvalidGlyph { position: new_pos })?;
        recovered.push(
            *alphabet(old_pos)?
                .get(rank)
                .ok_or(GuestPayloadProbeError::UnsupportedPosition)?,
        );
    }
    admit_guest_payload_probe(program, profile, &recovered)
}

fn admitted_handler_rank(source: &[u8]) -> Result<usize, GuestPayloadProbeError> {
    let glyph = *source
        .get(ISOLATED_COUNT_ADDRESS)
        .ok_or(GuestPayloadProbeError::InvalidSource)?;
    let rank = alphabet(ISOLATED_COUNT_ADDRESS)?
        .iter()
        .position(|&option| option == glyph)
        .ok_or(GuestPayloadProbeError::InvalidGlyph {
            position: ISOLATED_COUNT_ADDRESS,
        })?;
    if !(5..=7).contains(&rank) {
        return Err(GuestPayloadProbeError::UnsupportedGuestHandlerRank { rank });
    }
    Ok(rank)
}

/// Emits three distinct real guest control-flow destinations for CEB2 ranks.
///
/// Rank five (`M[121]=90`) lands on real guest `/`, `<`, `v` at 91..93 and
/// echoes **one** supplied byte. Rank six (`M[121]=106`) reaches `v@107`;
/// rank seven (`M[121]=107`) reaches `v@108`. These are carefully placed
/// native Malbolge handlers and do not decode the CEB2 rank *inside* the
/// guest, nor execute the advertised number of echo operations. All five
/// reached handler code glyphs live strictly before the 102-cell payload.
///
/// # Errors
///
/// Rejects source/profile mismatch, unsupported three-bit ranks 0..4,
/// or unavailable positional instruction encodings.
pub fn embed_isolated_guest_handlers(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    candidate: &[u8],
) -> Result<Vec<u8>, GuestPayloadProbeError> {
    let mut source = embed_isolated_guest_dispatch(program, profile, candidate)?;
    let _rank = admitted_handler_rank(&source)?;
    for (position, opcode) in HANDLER_OPCODES {
        let cell = source
            .get_mut(position)
            .ok_or(GuestPayloadProbeError::InvalidSource)?;
        *cell = instruction_at(position, opcode)?;
    }
    Ok(source)
}

/// Independently admits exact guest handler code, payload and source binding.
///
/// Reconstitutes the fixed v5 no-op code from an untrusted handler source,
/// delegates all source/profile SHA-256 checking to the established CEB2
/// verifier, and admits only count ranks five through seven. The guest never
/// performs any of these admission checks or computes a bytecode ordinal.
///
/// # Errors
///
/// Rejects changed handlers, altered graphical data, forged provenance,
/// malformed source length, or an unsupported count selected for this pilot.
pub fn admit_isolated_guest_handlers(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<[u8; BOUND_ECHO_MACRO_BYTES], GuestPayloadProbeError> {
    if source.len() != ISOLATED_TOTAL_CELLS {
        return Err(GuestPayloadProbeError::InvalidSource);
    }
    for (position, opcode) in HANDLER_OPCODES {
        if source.get(position) != Some(&instruction_at(position, opcode)?) {
            return Err(GuestPayloadProbeError::InvalidSource);
        }
    }
    let _rank = admitted_handler_rank(source)?;
    let mut restored = source.to_vec();
    for (position, _opcode) in HANDLER_OPCODES {
        let cell = restored
            .get_mut(position)
            .ok_or(GuestPayloadProbeError::InvalidSource)?;
        *cell = instruction_at(position, b'o')?;
    }
    admit_isolated_guest_dispatch(program, profile, &restored)
}
