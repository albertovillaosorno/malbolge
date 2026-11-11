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
//   - Two-way source-data-selected native guest dispatch for one/two echo pairs.
// - Must-Not:
//   - Claim runtime ordinal decode, a repeat loop, or guest SHA-256 admission.
// - Allows:
//   - Inputs: canonical ternary source, current profile, source-bound CEB2 bytes.
//   - Outputs: exact loader-valid resident code, two opcodes and bound CEB2.
//   - Side effects: bounded memory allocations only.
// - Split-When:
//   - Arbitrary operation lists or runtime iteration are supported.
// - Merge-When:
//   - A reusable decoder/loop is independently guest-verified.
// - Summary:
//   - One identical code island selects HALT or ECHO through a guest data cell.
// - Description:
//   - A second graphical bytecode opcode branches to two native handlers.
// - Usage:
//   - Research-only compact guest v8, not production compilation.
// - Defaults:
//   - Accepts exactly one or two canonical echo pairs; rejects all others.

//! Two distinct original workloads share **the same guest code island**.
//!
//! A reached `i@81` reads the first graphical opcode M[121]=90, executes
//! `/@91`, `<@92`, then a second reached `i@93` reads M[124]. If this
//! second opcode is graphical 87, C moves to `v@88`, halting after one echo.
//! If it is graphical 104, C moves to `/@105`, `<@106`, `v@107` and echoes
//! a second byte. Positions 0..123 (including both handlers, the first
//! bytecode opcode and all initial loader code) are **byte-identical**
//! between the two emitted sources. Only the second 3-bit graphical opcode
//! and the independently source-bound CEB2 data differ.
//!
//! All reached XLAT2 target writes are at code cells 90 and 87/104,
//! never into the two opcode words or the 102-cell CEB2 region 125..226.
//! The graphical bytecode numbers are phase-dependent and directly drive
//! guest C; the guest does not compute a ternary ordinal or read the CEB2
//! count, nor does it have a loop or verify the source SHA-256 itself.

use malbolge::ProfileDescriptor;

use crate::binding::BOUND_ECHO_MACRO_BYTES;
use crate::guest_probe::{GuestPayloadProbeError, alphabet, instruction_at};
use crate::isolated::{
    ISOLATED_PAYLOAD_START, ISOLATED_TOTAL_CELLS, admit_isolated_guest_dispatch,
    embed_isolated_guest_dispatch,
};
use crate::strategy::bridge::ternary::TernaryProgram;

/// Resident first graphical instruction cell for unconditional echo.
pub const FIRST_OPCODE_ADDRESS: usize = 121;
/// Resident second graphical instruction cell for conditional continuation.
pub const SECOND_OPCODE_ADDRESS: usize = 124;
/// The 102-cell CEB2 descriptor starts strictly after both instruction cells.
pub const CEB2_START: usize = 125;
/// Both source variants have the same 227-cell physical source footprint.
pub const SOURCE_CELLS: usize = 227;
/// An actual single echo + guest halt requires 86 committed guest steps.
pub const HALT_AFTER_ONE_STEPS: usize = 86;
/// Two actual guest echo operations + halt require 88 committed steps.
pub const ECHO_TWICE_STEPS: usize = 88;
/// The second loader-valid bytecode word for halt (`v@88`).
pub const HALT_OPCODE_WORD: u8 = 87;
/// The second loader-valid bytecode word for another echo (`/@105`).
pub const ECHO_OPCODE_WORD: u8 = 104;
const FIRST_OPCODE_WORD: u8 = 90;
const CEB2_GLYPHS: usize = 102;

/// Fail-closed host source and descriptor checking.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ConditionalDispatchError {
    /// The existing independent CEB2 source/profile admission failed.
    Guest(GuestPayloadProbeError),
    /// Code, opcode, descriptor or source extent is not canonical.
    InvalidSource,
    /// This bounded guest source accepts only original counts one and two.
    UnsupportedEchoCount,
}

impl From<GuestPayloadProbeError> for ConditionalDispatchError {
    fn from(value: GuestPayloadProbeError) -> Self {
        Self::Guest(value)
    }
}

fn expected_second_word(candidate: &[u8]) -> Result<u8, ConditionalDispatchError> {
    match candidate.get(4..6) {
        Some([1, 0]) => Ok(HALT_OPCODE_WORD),
        Some([2, 0]) => Ok(ECHO_OPCODE_WORD),
        _ => Err(ConditionalDispatchError::UnsupportedEchoCount),
    }
}

fn prefix(second_word: u8) -> Result<Vec<u8>, ConditionalDispatchError> {
    if SOURCE_CELLS != CEB2_START.saturating_add(CEB2_GLYPHS)
        || CEB2_START != SECOND_OPCODE_ADDRESS.saturating_add(1)
        || FIRST_OPCODE_ADDRESS >= SECOND_OPCODE_ADDRESS
        || alphabet(FIRST_OPCODE_ADDRESS)?.get(5) != Some(&FIRST_OPCODE_WORD)
        || alphabet(SECOND_OPCODE_ADDRESS)?.get(4) != Some(&HALT_OPCODE_WORD)
        || alphabet(SECOND_OPCODE_ADDRESS)?.get(6) != Some(&ECHO_OPCODE_WORD)
        || (second_word != HALT_OPCODE_WORD && second_word != ECHO_OPCODE_WORD)
    {
        return Err(ConditionalDispatchError::InvalidSource);
    }
    let mut result = Vec::with_capacity(CEB2_START);
    for position in 0..CEB2_START {
        let glyph = match position {
            0 => instruction_at(position, b'j')?,
            81 | 93 => instruction_at(position, b'i')?,
            88 | 107 => instruction_at(position, b'v')?,
            91 | 105 => instruction_at(position, b'/')?,
            92 | 106 => instruction_at(position, b'<')?,
            FIRST_OPCODE_ADDRESS => FIRST_OPCODE_WORD,
            SECOND_OPCODE_ADDRESS => second_word,
            _ => instruction_at(position, b'o')?,
        };
        result.push(glyph);
    }
    Ok(result)
}

/// Propose one of two shared-code graphical bytecode sources.
///
/// Existing CEB2 source/profile SHA-256 admission is mandatory *before*
/// emission. The payload is re-encoded to each new graphical source
/// position (rather than copying the old ASCII values without re-ranking).
///
/// # Errors
///
/// Rejects unsupported echo counts, invalid canonical CEB2 provenance or
/// unavailable position-dependent guest instructions.
pub fn embed_conditional_guest_dispatch(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    candidate: &[u8],
) -> Result<Vec<u8>, ConditionalDispatchError> {
    let source_bound = embed_isolated_guest_dispatch(program, profile, candidate)?;
    let choice = expected_second_word(candidate)?;
    let mut source = prefix(choice)?;
    let tail = source_bound
        .get(ISOLATED_PAYLOAD_START..ISOLATED_TOTAL_CELLS)
        .ok_or(ConditionalDispatchError::InvalidSource)?;
    for (index, &glyph) in tail.iter().enumerate() {
        let old_address = ISOLATED_PAYLOAD_START.saturating_add(index);
        let new_address = CEB2_START.saturating_add(index);
        let rank = alphabet(old_address)?
            .iter()
            .position(|&option| option == glyph)
            .ok_or(ConditionalDispatchError::InvalidSource)?;
        source.push(
            *alphabet(new_address)?
                .get(rank)
                .ok_or(ConditionalDispatchError::InvalidSource)?,
        );
    }
    if source.len() != SOURCE_CELLS {
        return Err(ConditionalDispatchError::InvalidSource);
    }
    Ok(source)
}

/// Independently re-admit a source-derived conditional operation.
///
/// This does not trust a host-supplied count or unverified opcode byte. It
/// verifies the actual opcode, all other exact code positions, all 102
/// *supplied* packed CEB2 glyphs, and their original source/profile digest.
/// In addition, the graphical HALT/ECHO choice must agree with the recovered
/// canonical count, so swapping only the opcode cannot change behavior
/// while retaining host admission.
///
/// # Errors
///
/// Rejects wrong source length, unknown opcode, mutated code, unsupported
/// original count, mismatched variant, or unbound/forged descriptor data.
pub fn admit_conditional_guest_dispatch(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<[u8; BOUND_ECHO_MACRO_BYTES], ConditionalDispatchError> {
    if source.len() != SOURCE_CELLS {
        return Err(ConditionalDispatchError::InvalidSource);
    }
    let actual_word = *source
        .get(SECOND_OPCODE_ADDRESS)
        .ok_or(ConditionalDispatchError::InvalidSource)?;
    let code = prefix(actual_word)?;
    if source.get(..CEB2_START) != Some(code.as_slice()) {
        return Err(ConditionalDispatchError::InvalidSource);
    }
    let mut reconstructed = Vec::with_capacity(ISOLATED_TOTAL_CELLS);
    for position in 0..ISOLATED_PAYLOAD_START {
        let instruction = match position {
            0 => b'j',
            81 => b'i',
            _ => b'o',
        };
        reconstructed.push(instruction_at(position, instruction)?);
    }
    let tail = source
        .get(CEB2_START..)
        .ok_or(ConditionalDispatchError::InvalidSource)?;
    for (index, &glyph) in tail.iter().enumerate() {
        let new_address = CEB2_START.saturating_add(index);
        let old_address = ISOLATED_PAYLOAD_START.saturating_add(index);
        let rank = alphabet(new_address)?
            .iter()
            .position(|&option| option == glyph)
            .ok_or(ConditionalDispatchError::InvalidSource)?;
        reconstructed.push(
            *alphabet(old_address)?
                .get(rank)
                .ok_or(ConditionalDispatchError::InvalidSource)?,
        );
    }
    let recovered = admit_isolated_guest_dispatch(program, profile, &reconstructed)?;
    if expected_second_word(&recovered)? != actual_word {
        return Err(ConditionalDispatchError::InvalidSource);
    }
    Ok(recovered)
}
