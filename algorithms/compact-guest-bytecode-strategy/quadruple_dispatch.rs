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
//   - Four-way guest-data-selected one/two/three/four-pair source-bound echo.
// - Must-Not:
//   - Claim a reusable loop, general opcode decoder or guest-side SHA-256.
// - Allows:
//   - Inputs: admitted canonical echo source, profile and bound CEB2 bytes.
//   - Outputs: fixed native handlers, four data operands and protected CEB2.
//   - Side effects: bounded memory allocation only.
// - Split-When:
//   - A loop or arbitrary program-counter-driven bytecode is implemented.
// - Merge-When:
//   - A verified reusable guest interpreter supersedes this native witness.
// - Summary:
//   - Four source-bound programs choose between one, two, three or four echoes.
// - Description:
//   - Three conditional data words select three successive native guest branches.
// - Usage:
//   - Research v10 only, not integrated into production guest compilation.
// - Defaults:
//   - Rejects every canonical echo count other than one, two, three or four.

//! Four bounded echo workloads select immutable native Malbolge handlers.
//!
//! Source bytes vary at exactly three native branch operands 124, 127, 130.
//! `i@81` reads M[121]=90 and enters /@91, <@92, i@93. M[124]=87
//! halts at 88 (one echo) or 104 enters /@105, <@106, i@107.
//! M[127]=101 halts at 102 (two echoes) or 84 enters /@85, <@86,
//! i@87. The fourth reached `i` reads M[130]=81 and halts at 82
//! (three echoes), or M[130]=97 and enters /@98, <@99, v@100.
//!
//! Native `i` XLAT2 writes code cells 90, 87/104, 101/84, 81/97.
//! All three conditional branch words and 102 SHA-256-bound CEB2 data cells
//! at 131..232 remain intact. Hand-placed native handlers are not a
//! generic bytecode interpreter, loop or guest-side source authentication.

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
/// Fourth guest graphical word (81 for HALT, 97 for fourth echo).
pub const FOURTH_WORD_ADDRESS: usize = 130;
/// First 3-bit glyph of the independently source-bound CEB2 descriptor.
pub const CEB2_START: usize = 131;
/// Full graphical source image, including 102 CEB2 glyphs.
pub const SOURCE_CELLS: usize = 233;
/// Expected steps for one, two, three and four echoed guest byte pairs.
pub const GUEST_STEPS: [usize; 4] = [86, 89, 92, 94];
const BOUND_GLYPHS: usize = 102;
const FIRST_WORD: u8 = 90;
const SECOND_HALT: u8 = 87;
const SECOND_CONTINUE: u8 = 104;
const THIRD_HALT: u8 = 101;
const THIRD_CONTINUE: u8 = 84;
const FOURTH_HALT: u8 = 81;
const FOURTH_CONTINUE: u8 = 97;

/// Host-admission failures for this exact bounded four-way guest source.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum QuadrupleDispatchError {
    /// Underlying canonical source/profile CEB2 verification rejected.
    Guest(GuestPayloadProbeError),
    /// Source extent, code, graphical branch word or CEB2 data changed.
    InvalidSource,
    /// Original canonical echo count exceeds this unrolled four-way design.
    UnsupportedEchoCount,
}

impl From<GuestPayloadProbeError> for QuadrupleDispatchError {
    fn from(value: GuestPayloadProbeError) -> Self {
        Self::Guest(value)
    }
}

type GraphicalBranchOperands = (u8, u8, u8);

fn expected_operands(candidate: &[u8]) -> Result<GraphicalBranchOperands, QuadrupleDispatchError> {
    match candidate.get(4..6) {
        Some([1, 0]) => Ok((SECOND_HALT, THIRD_HALT, FOURTH_HALT)),
        Some([2, 0]) => Ok((SECOND_CONTINUE, THIRD_HALT, FOURTH_HALT)),
        Some([3, 0]) => Ok((SECOND_CONTINUE, THIRD_CONTINUE, FOURTH_HALT)),
        Some([4, 0]) => Ok((SECOND_CONTINUE, THIRD_CONTINUE, FOURTH_CONTINUE)),
        _ => Err(QuadrupleDispatchError::UnsupportedEchoCount),
    }
}

fn code_prefix(second: u8, third: u8, fourth: u8) -> Result<Vec<u8>, QuadrupleDispatchError> {
    if SOURCE_CELLS != CEB2_START.saturating_add(BOUND_GLYPHS)
        || CEB2_START != FOURTH_WORD_ADDRESS.saturating_add(1)
        || alphabet(FIRST_WORD_ADDRESS)?.get(5) != Some(&FIRST_WORD)
        || alphabet(SECOND_WORD_ADDRESS)?.get(4) != Some(&SECOND_HALT)
        || alphabet(SECOND_WORD_ADDRESS)?.get(6) != Some(&SECOND_CONTINUE)
        || alphabet(THIRD_WORD_ADDRESS)?.get(6) != Some(&THIRD_HALT)
        || alphabet(THIRD_WORD_ADDRESS)?.get(4) != Some(&THIRD_CONTINUE)
        || alphabet(FOURTH_WORD_ADDRESS)?.get(3) != Some(&FOURTH_HALT)
        || alphabet(FOURTH_WORD_ADDRESS)?.get(4) != Some(&FOURTH_CONTINUE)
        || ![SECOND_HALT, SECOND_CONTINUE].contains(&second)
        || ![THIRD_HALT, THIRD_CONTINUE].contains(&third)
        || ![FOURTH_HALT, FOURTH_CONTINUE].contains(&fourth)
    {
        return Err(QuadrupleDispatchError::InvalidSource);
    }
    let mut code = Vec::with_capacity(CEB2_START);
    for position in 0..CEB2_START {
        let glyph = match position {
            0 => instruction_at(position, b'j')?,
            81 | 87 | 93 | 107 => instruction_at(position, b'i')?,
            85 | 91 | 98 | 105 => instruction_at(position, b'/')?,
            86 | 92 | 99 | 106 => instruction_at(position, b'<')?,
            82 | 88 | 100 | 102 => instruction_at(position, b'v')?,
            FIRST_WORD_ADDRESS => FIRST_WORD,
            SECOND_WORD_ADDRESS => second,
            THIRD_WORD_ADDRESS => third,
            FOURTH_WORD_ADDRESS => fourth,
            _ => instruction_at(position, b'o')?,
        };
        code.push(glyph);
    }
    Ok(code)
}

/// Emit loader-phase-correct guest source for one to four echo pairs.
///
/// Source/profile CEB2 identity is admitted *before* choosing the graphical
/// native operands; packed CEB2 source cells are re-ranked for their new
/// physical addresses, preserving all 102 independently checked ordinals.
///
/// # Errors
///
/// Rejects invalid canonical programs, failed CEB2 admission, unsupported
/// pair counts or unavailable loader-position instruction encodings.
pub fn embed_quadruple_echo_dispatch(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    candidate: &[u8],
) -> Result<Vec<u8>, QuadrupleDispatchError> {
    let source_bound = embed_isolated_guest_dispatch(program, profile, candidate)?;
    let (second, third, fourth) = expected_operands(candidate)?;
    let mut source = code_prefix(second, third, fourth)?;
    let original_tail = source_bound
        .get(ISOLATED_PAYLOAD_START..ISOLATED_TOTAL_CELLS)
        .ok_or(QuadrupleDispatchError::InvalidSource)?;
    for (index, &glyph) in original_tail.iter().enumerate() {
        let old_address = ISOLATED_PAYLOAD_START.saturating_add(index);
        let new_address = CEB2_START.saturating_add(index);
        let rank = alphabet(old_address)?
            .iter()
            .position(|&option| option == glyph)
            .ok_or(QuadrupleDispatchError::InvalidSource)?;
        source.push(
            *alphabet(new_address)?
                .get(rank)
                .ok_or(QuadrupleDispatchError::InvalidSource)?,
        );
    }
    if source.len() != SOURCE_CELLS {
        return Err(QuadrupleDispatchError::InvalidSource);
    }
    Ok(source)
}

/// Independently verify exact code, three conditional operands, CEB2 and canonical count.
///
/// Recovers the candidate from the **supplied** physical source, then applies
/// the canonical source/profile SHA-256 binding and checks all three operands
/// against the recovered original count. No host callback executes during
/// the guest's actual indirect dispatch, and the guest does not compute SHA.
///
/// # Errors
///
/// Rejects changes to code, any operand, source extents or descriptor;
/// foreign original sources and unsupported counts are refused closed.
pub fn admit_quadruple_echo_dispatch(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<[u8; BOUND_ECHO_MACRO_BYTES], QuadrupleDispatchError> {
    if source.len() != SOURCE_CELLS {
        return Err(QuadrupleDispatchError::InvalidSource);
    }
    let second = *source
        .get(SECOND_WORD_ADDRESS)
        .ok_or(QuadrupleDispatchError::InvalidSource)?;
    let third = *source
        .get(THIRD_WORD_ADDRESS)
        .ok_or(QuadrupleDispatchError::InvalidSource)?;
    let fourth = *source
        .get(FOURTH_WORD_ADDRESS)
        .ok_or(QuadrupleDispatchError::InvalidSource)?;
    let code = code_prefix(second, third, fourth)?;
    if source.get(..CEB2_START) != Some(code.as_slice()) {
        return Err(QuadrupleDispatchError::InvalidSource);
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
        .ok_or(QuadrupleDispatchError::InvalidSource)?
        .iter()
        .enumerate()
    {
        let new_address = CEB2_START.saturating_add(index);
        let old_address = ISOLATED_PAYLOAD_START.saturating_add(index);
        let rank = alphabet(new_address)?
            .iter()
            .position(|&option| option == glyph)
            .ok_or(QuadrupleDispatchError::InvalidSource)?;
        reconstructed.push(
            *alphabet(old_address)?
                .get(rank)
                .ok_or(QuadrupleDispatchError::InvalidSource)?,
        );
    }
    let recovered = admit_isolated_guest_dispatch(program, profile, &reconstructed)?;
    if expected_operands(&recovered)? != (second, third, fourth) {
        return Err(QuadrupleDispatchError::InvalidSource);
    }
    Ok(recovered)
}
