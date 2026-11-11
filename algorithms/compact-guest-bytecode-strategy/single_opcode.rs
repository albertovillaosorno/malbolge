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
//   - One source-bound guest bytecode operation with complete one-byte echo.
// - Must-Not:
//   - Claim a general guest interpreter, loop, efficient runtime or guest hash.
// - Allows:
//   - Inputs: separately trusted canonical ternary IR/profile/CEB2 candidate.
//   - Outputs: exact loader-valid, independently host-admitted Malbolge source.
//   - Side effects: bounded memory allocation; no host I/O.
// - Split-When:
//   - More than one independently meaningful guest bytecode opcode is handled.
// - Merge-When:
//   - An actual bytecode loop with protected data is semantically verified.
// - Summary:
//   - First executable guest echo-one opcode, with bound CEB2 data kept intact.
// - Description:
//   - A phase-specific graphical opcode jumps to reached native /, < and v.
// - Usage:
//   - Research-only single-echo interpreter-boundary test, never production.
// - Defaults:
//   - Rejects any original source containing other than one exact echo pair.

//! A complete, *single operation* equivalent to one canonical echo pair.
//!
//! The instruction at data address 121 is an explicit three-bit opcode,
//! not a CEB2 count glyph. Its loader-valid fifth rank maps to graphical
//! cell 90. After `j@0` and 80 reached no-ops, `i@81` reads the opcode
//! and dynamically jumps to code address 91. Guest `/@91`, `<@92`, `v@93`
//! echo one byte and halt. The full SHA-256-bound 38-byte CEB2 remains
//! loaded as 102 separate graphical data cells at positions 122..223.
//! Guest self-encryption never reaches these data cells on this execution.
//!
//! Host admission requires exact one-pair echo canonical IR, fixed opcode,
//! fixed code, exact CEB2 data and profile binding. The guest does not verify
//! SHA-256 or decode ordinal 5 numerically; it uses direct graphical-cell
//! indirect dispatch. This is **not** a multi-op interpreter or repeat loop.

use malbolge::ProfileDescriptor;

use crate::binding::BOUND_ECHO_MACRO_BYTES;
use crate::guest_probe::{GuestPayloadProbeError, alphabet, instruction_at};
use crate::isolated::{
    ISOLATED_PAYLOAD_START, ISOLATED_TOTAL_CELLS, admit_isolated_guest_dispatch,
    embed_isolated_guest_dispatch,
};
use crate::strategy::bridge::ternary::TernaryProgram;

/// The explicit graphical single-operation opcode word lives at D=121.
pub const SINGLE_OPCODE_ADDRESS: usize = 121;
/// Beginning of the independently source-bound, untouched 102-cell CEB2 tail.
pub const SINGLE_CEB2_START: usize = 122;
/// Physical complete guest source extent, including code, opcode and data.
pub const SINGLE_SOURCE_CELLS: usize = 224;
/// The loader rank five in this one-operation instruction set means echo once.
pub const SINGLE_ECHO_OPCODE_RANK: usize = 5;
/// Number of actual VM instructions to echo exactly one byte and halt.
pub const SINGLE_ECHO_GUEST_STEPS: usize = 85;
const ORIGINAL_CEB2_CELLS: usize = 102;
const ONE_PAIR: [u8; 2] = [1, 0];

/// Host admission failures for the isolated single-opcode experiment.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SingleOpcodeError {
    /// Exact positional glyph or digest/provenance validation failed.
    Guest(GuestPayloadProbeError),
    /// Code, separate opcode, source size or graphical ordinal was changed.
    InvalidSource,
    /// This research program only represents exactly one original echo pair.
    UnsupportedEchoCount,
}

impl From<GuestPayloadProbeError> for SingleOpcodeError {
    fn from(value: GuestPayloadProbeError) -> Self {
        Self::Guest(value)
    }
}

fn one_pair_candidate(candidate: &[u8]) -> Result<(), SingleOpcodeError> {
    if candidate.get(4..6) == Some(ONE_PAIR.as_slice()) {
        Ok(())
    } else {
        Err(SingleOpcodeError::UnsupportedEchoCount)
    }
}

fn prefix() -> Result<Vec<u8>, SingleOpcodeError> {
    if SINGLE_CEB2_START != SINGLE_OPCODE_ADDRESS.saturating_add(1)
        || SINGLE_SOURCE_CELLS != SINGLE_CEB2_START.saturating_add(ORIGINAL_CEB2_CELLS)
        || SINGLE_CEB2_START <= ISOLATED_PAYLOAD_START
        || SINGLE_OPCODE_ADDRESS >= SINGLE_CEB2_START
    {
        return Err(SingleOpcodeError::InvalidSource);
    }
    let opcode = *alphabet(SINGLE_OPCODE_ADDRESS)?
        .get(SINGLE_ECHO_OPCODE_RANK)
        .ok_or(SingleOpcodeError::InvalidSource)?;
    if opcode != 90 || usize::from(opcode) >= SINGLE_CEB2_START {
        return Err(SingleOpcodeError::InvalidSource);
    }
    let mut source = Vec::with_capacity(SINGLE_SOURCE_CELLS);
    for position in 0..SINGLE_CEB2_START {
        let glyph = match position {
            0 => instruction_at(position, b'j')?,
            81 => instruction_at(position, b'i')?,
            91 => instruction_at(position, b'/')?,
            92 => instruction_at(position, b'<')?,
            93 => instruction_at(position, b'v')?,
            SINGLE_OPCODE_ADDRESS => opcode,
            _ => instruction_at(position, b'o')?,
        };
        source.push(glyph);
    }
    Ok(source)
}

/// Emit one actual guest-dispatched echo opcode with a separately bound CEB2.
///
/// All 102 descriptor glyphs are *re-encoded for their exact new positions*.
/// The source is only proposed after the old CEB2 host verifier has admitted
/// the candidate against the trusted original canonical one-pair program.
///
/// # Errors
///
/// Rejects any unsupported pair count, forged bound descriptor or impossible
/// positional opcode/source glyph.
pub fn embed_single_echo_opcode(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    candidate: &[u8],
) -> Result<Vec<u8>, SingleOpcodeError> {
    // Check the complete independent CEB2 candidate first, before producing
    // any source. The pair-count byte alone has no provenance authority.
    let old = embed_isolated_guest_dispatch(program, profile, candidate)?;
    one_pair_candidate(candidate)?;
    let mut source = prefix()?;
    let old_payload = old
        .get(ISOLATED_PAYLOAD_START..ISOLATED_TOTAL_CELLS)
        .ok_or(SingleOpcodeError::InvalidSource)?;
    for (index, &glyph) in old_payload.iter().enumerate() {
        let old_address = ISOLATED_PAYLOAD_START.saturating_add(index);
        let new_address = SINGLE_CEB2_START.saturating_add(index);
        let rank = alphabet(old_address)?
            .iter()
            .position(|&option| option == glyph)
            .ok_or(SingleOpcodeError::InvalidSource)?;
        source.push(
            *alphabet(new_address)?
                .get(rank)
                .ok_or(SingleOpcodeError::InvalidSource)?,
        );
    }
    if source.len() != SINGLE_SOURCE_CELLS {
        return Err(SingleOpcodeError::InvalidSource);
    }
    Ok(source)
}

/// Independently re-admit the actual guest opcode, code and bound descriptor.
///
/// This reconstructs CEB2's old graphical ordinals from the **supplied**
/// untrusted 102 loaded data glyphs, not from a caller-proposed descriptor.
/// The original isolated admission then independently validates the complete
/// source/profile digest against the original trusted canonical input.
/// Neither this host verifier nor the guest accepts an unsupported count.
///
/// # Errors
///
/// Rejects any changed code/opcode, shifted/truncated source, altered CEB2,
/// foreign source identity, or a candidate that is not exactly one echo pair.
pub fn admit_single_echo_opcode(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<[u8; BOUND_ECHO_MACRO_BYTES], SingleOpcodeError> {
    let expected_prefix = prefix()?;
    if source.len() != SINGLE_SOURCE_CELLS
        || source.get(..SINGLE_CEB2_START) != Some(expected_prefix.as_slice())
    {
        return Err(SingleOpcodeError::InvalidSource);
    }
    // Recover the former v5 exact-phase image, whose verifier re-admits all
    // code cells and all 102 CEB2 glyph ranks against the canonical source.
    let mut original = Vec::with_capacity(ISOLATED_TOTAL_CELLS);
    for position in 0..ISOLATED_PAYLOAD_START {
        let opcode = match position {
            0 => b'j',
            81 => b'i',
            _ => b'o',
        };
        original.push(instruction_at(position, opcode)?);
    }
    let tail = source
        .get(SINGLE_CEB2_START..)
        .ok_or(SingleOpcodeError::InvalidSource)?;
    for (index, &glyph) in tail.iter().enumerate() {
        let new_address = SINGLE_CEB2_START.saturating_add(index);
        let old_address = ISOLATED_PAYLOAD_START.saturating_add(index);
        let rank = alphabet(new_address)?
            .iter()
            .position(|&option| option == glyph)
            .ok_or(SingleOpcodeError::InvalidSource)?;
        original.push(
            *alphabet(old_address)?
                .get(rank)
                .ok_or(SingleOpcodeError::InvalidSource)?,
        );
    }
    let recovered = admit_isolated_guest_dispatch(program, profile, &original)?;
    one_pair_candidate(&recovered)?;
    Ok(recovered)
}
