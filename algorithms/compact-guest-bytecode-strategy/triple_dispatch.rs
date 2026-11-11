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
//   - Three-way guest-data-selected one/two/three-pair source-bound echo.
// - Must-Not:
//   - Claim a reusable loop, general opcode decoder or guest-side SHA-256.
// - Allows:
//   - Inputs: admitted canonical echo source, profile and bound CEB2 bytes.
//   - Outputs: fixed native handlers, three data operands and protected CEB2.
//   - Side effects: bounded memory allocation only.
// - Split-When:
//   - A loop or arbitrary program-counter-driven bytecode is implemented.
// - Merge-When:
//   - A verified reusable guest interpreter supersedes this native witness.
// - Summary:
//   - Three source-bound programs choose between one, two or three echoes.
// - Description:
//   - Two conditional data words select two successive native guest branches.
// - Usage:
//   - Research v9 only, not integrated into production guest compilation.
// - Defaults:
//   - Rejects every canonical echo count other than one, two or three.

//! Three bounded echo workloads select immutable native Malbolge handlers.
//!
//! One loader-valid code image (excluding opcode data cells 124 and 127)
//! contains `j@0`, 80 reached `o`, `i@81`, `/@91`, `<@92`, `i@93`.
//! The physical graphical word M[124] is 87 for HALT at 88 (one echo) or
//! 104 for `/@105`, `<@106`, `i@107`. On the continuation path the native
//! third `i` reads M[127]=101 for `v@102` (two echoes), or 84 for
//! `/@85`, `<@86`, `v@87` (three echoes). M[127]=101 is also the
//! unused, loader-valid third word for the one-pair source.
//!
//! Mandatory native `i` XLAT2 writes code cells 90, 87/104, 101/84.
//! The reached guest never writes either data operand or the source-bound
//! 102-cell CEB2 payload at 128..229. All three versions share every
//! other code glyph byte for byte. Source-dependent graphical opcode words
//! are directly used as jump addresses, not decoded as abstract ordinals.
//! There is no loop, guest-side hash, or arbitrary bytecode interpreter.

use malbolge::ProfileDescriptor;

use crate::binding::BOUND_ECHO_MACRO_BYTES;
use crate::guest_probe::{GuestPayloadProbeError, alphabet, instruction_at};
use crate::isolated::{
    ISOLATED_PAYLOAD_START, ISOLATED_TOTAL_CELLS, admit_isolated_guest_dispatch,
    embed_isolated_guest_dispatch,
};
use crate::strategy::bridge::ternary::TernaryProgram;

/// Source-resident first guest graphical word (always 90).
pub const FIRST_WORD_ADDRESS: usize = 121;
/// Second guest graphical word (87 for HALT, otherwise 104).
pub const SECOND_WORD_ADDRESS: usize = 124;
/// Third guest graphical word (101 for HALT, 84 for third echo).
pub const THIRD_WORD_ADDRESS: usize = 127;
/// First 3-bit glyph of the independently source-bound CEB2 descriptor.
pub const CEB2_START: usize = 128;
/// Full graphical source image, including 102 CEB2 glyphs.
pub const SOURCE_CELLS: usize = 230;
/// Expected steps for one, two and three echoed guest byte pairs.
pub const GUEST_STEPS: [usize; 3] = [86, 89, 91];
const BOUND_GLYPHS: usize = 102;
const FIRST_WORD: u8 = 90;
const SECOND_HALT: u8 = 87;
const SECOND_CONTINUE: u8 = 104;
const THIRD_HALT: u8 = 101;
const THIRD_CONTINUE: u8 = 84;

/// Host-admission failures for this exact bounded three-way guest source.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TripleDispatchError {
    /// Underlying canonical source/profile CEB2 verification rejected.
    Guest(GuestPayloadProbeError),
    /// Source extent, code, graphical branch word or CEB2 data changed.
    InvalidSource,
    /// Original canonical echo count exceeds this unrolled three-way design.
    UnsupportedEchoCount,
}

impl From<GuestPayloadProbeError> for TripleDispatchError {
    fn from(value: GuestPayloadProbeError) -> Self {
        Self::Guest(value)
    }
}

type GraphicalBranchOperands = (u8, u8);

fn expected_operands(candidate: &[u8]) -> Result<GraphicalBranchOperands, TripleDispatchError> {
    match candidate.get(4..6) {
        Some([1, 0]) => Ok((SECOND_HALT, THIRD_HALT)),
        Some([2, 0]) => Ok((SECOND_CONTINUE, THIRD_HALT)),
        Some([3, 0]) => Ok((SECOND_CONTINUE, THIRD_CONTINUE)),
        _ => Err(TripleDispatchError::UnsupportedEchoCount),
    }
}

fn code_prefix(second: u8, third: u8) -> Result<Vec<u8>, TripleDispatchError> {
    if SOURCE_CELLS != CEB2_START.saturating_add(BOUND_GLYPHS)
        || CEB2_START != THIRD_WORD_ADDRESS.saturating_add(1)
        || alphabet(FIRST_WORD_ADDRESS)?.get(5) != Some(&FIRST_WORD)
        || alphabet(SECOND_WORD_ADDRESS)?.get(4) != Some(&SECOND_HALT)
        || alphabet(SECOND_WORD_ADDRESS)?.get(6) != Some(&SECOND_CONTINUE)
        || alphabet(THIRD_WORD_ADDRESS)?.get(6) != Some(&THIRD_HALT)
        || alphabet(THIRD_WORD_ADDRESS)?.get(4) != Some(&THIRD_CONTINUE)
        || ![SECOND_HALT, SECOND_CONTINUE].contains(&second)
        || ![THIRD_HALT, THIRD_CONTINUE].contains(&third)
    {
        return Err(TripleDispatchError::InvalidSource);
    }
    let mut code = Vec::with_capacity(CEB2_START);
    for position in 0..CEB2_START {
        let glyph = match position {
            0 => instruction_at(position, b'j')?,
            81 | 93 | 107 => instruction_at(position, b'i')?,
            85 | 91 | 105 => instruction_at(position, b'/')?,
            86 | 92 | 106 => instruction_at(position, b'<')?,
            87 | 88 | 102 => instruction_at(position, b'v')?,
            FIRST_WORD_ADDRESS => FIRST_WORD,
            SECOND_WORD_ADDRESS => second,
            THIRD_WORD_ADDRESS => third,
            _ => instruction_at(position, b'o')?,
        };
        code.push(glyph);
    }
    Ok(code)
}

/// Emit loader-phase-correct guest source for one, two or three echo pairs.
///
/// Source/profile CEB2 identity is admitted *before* choosing the graphical
/// native operands; packed CEB2 source cells are re-ranked for their new
/// physical addresses, preserving all 102 independently checked ordinals.
///
/// # Errors
///
/// Rejects invalid canonical programs, failed CEB2 admission, unsupported
/// pair counts or unavailable loader-position instruction encodings.
pub fn embed_triple_echo_dispatch(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    candidate: &[u8],
) -> Result<Vec<u8>, TripleDispatchError> {
    let source_bound = embed_isolated_guest_dispatch(program, profile, candidate)?;
    let (second, third) = expected_operands(candidate)?;
    let mut source = code_prefix(second, third)?;
    let original_tail = source_bound
        .get(ISOLATED_PAYLOAD_START..ISOLATED_TOTAL_CELLS)
        .ok_or(TripleDispatchError::InvalidSource)?;
    for (index, &glyph) in original_tail.iter().enumerate() {
        let old_address = ISOLATED_PAYLOAD_START.saturating_add(index);
        let new_address = CEB2_START.saturating_add(index);
        let rank = alphabet(old_address)?
            .iter()
            .position(|&option| option == glyph)
            .ok_or(TripleDispatchError::InvalidSource)?;
        source.push(
            *alphabet(new_address)?
                .get(rank)
                .ok_or(TripleDispatchError::InvalidSource)?,
        );
    }
    if source.len() != SOURCE_CELLS {
        return Err(TripleDispatchError::InvalidSource);
    }
    Ok(source)
}

/// Independently verify exact code, both operands, CEB2 and canonical count.
///
/// Recovers the candidate from the **supplied** physical source, then applies
/// the canonical source/profile SHA-256 binding and checks both operands
/// against the recovered original count. No host callback executes during
/// the guest's actual indirect dispatch, and the guest does not compute SHA.
///
/// # Errors
///
/// Rejects changes to code, either operand, source extents or descriptor;
/// foreign original sources and unsupported counts are refused closed.
pub fn admit_triple_echo_dispatch(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<[u8; BOUND_ECHO_MACRO_BYTES], TripleDispatchError> {
    if source.len() != SOURCE_CELLS {
        return Err(TripleDispatchError::InvalidSource);
    }
    let second = *source
        .get(SECOND_WORD_ADDRESS)
        .ok_or(TripleDispatchError::InvalidSource)?;
    let third = *source
        .get(THIRD_WORD_ADDRESS)
        .ok_or(TripleDispatchError::InvalidSource)?;
    let code = code_prefix(second, third)?;
    if source.get(..CEB2_START) != Some(code.as_slice()) {
        return Err(TripleDispatchError::InvalidSource);
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
    for (index, &glyph) in source
        .get(CEB2_START..)
        .ok_or(TripleDispatchError::InvalidSource)?
        .iter()
        .enumerate()
    {
        let new_address = CEB2_START.saturating_add(index);
        let old_address = ISOLATED_PAYLOAD_START.saturating_add(index);
        let rank = alphabet(new_address)?
            .iter()
            .position(|&option| option == glyph)
            .ok_or(TripleDispatchError::InvalidSource)?;
        reconstructed.push(
            *alphabet(old_address)?
                .get(rank)
                .ok_or(TripleDispatchError::InvalidSource)?,
        );
    }
    let recovered = admit_isolated_guest_dispatch(program, profile, &reconstructed)?;
    if expected_operands(&recovered)? != (second, third) {
        return Err(TripleDispatchError::InvalidSource);
    }
    Ok(recovered)
}
