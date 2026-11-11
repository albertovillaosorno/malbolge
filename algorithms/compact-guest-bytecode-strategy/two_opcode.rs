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
//   - Two sequential source-bound guest echo operations and independent admission.
// - Must-Not:
//   - Claim a reusable bytecode interpreter, general loop or guest SHA-256.
// - Allows:
//   - Inputs: trusted canonical ternary source, profile and source-bound CEB2.
//   - Outputs: fixed phase-correct Malbolge source with a protected data tail.
//   - Side effects: bounded in-memory allocation only.
// - Split-When:
//   - General bytecode handlers, a repeat loop, or dynamic operands are supported.
// - Merge-When:
//   - A reusable guest bytecode execution contract is proven equivalent.
// - Summary:
//   - Demonstrates two actual guest-side indirect opcode dispatches in sequence.
// - Description:
//   - Two separate data-loaded graphical words drive two independent echo I/O.
// - Usage:
//   - Research-only CEB2 pilot v7; never production guest compilation.
// - Defaults:
//   - Exact source-bound two-pair echo shape only; reject all other counts.

//! Two independently reached guest opcode reads, complete two-byte echo trace.
//!
//! After `j@0` and eighty reached no-ops, `i@81` reads opcode M[121]=90,
//! which branches to `/@91`, `<@92`, then `i@93`. D advances to 124 after
//! the first reached input/output pair; `i@93` therefore reads the *second*
//! graphical opcode M[124]=104 and branches to `/@105`, `<@106`, `v@107`.
//! The current profile VM commits **88 guest steps**, reading/outputting
//! exactly two input bytes. Both opcodes live outside the source-bound 102
//! glyph CEB2 tail at positions 125..226; reached XLAT2 only writes code
//! cells 90 and 104. The guest reads both opcodes from physical source data.
//!
//! Host admission rejects all original repeat counts other than two and
//! fully rechecks the separately bound SHA-256 CEB2 source/profile identity.
//! The two graphical opcodes are hand placed, not dynamically decoded as
//! ternary ordinals. This is a two-op unrolled guest interpreter witness,
//! **not** a general bytecode runtime or a count-controlled loop.

use malbolge::ProfileDescriptor;

use crate::binding::BOUND_ECHO_MACRO_BYTES;
use crate::guest_probe::{GuestPayloadProbeError, alphabet, instruction_at};
use crate::isolated::{
    ISOLATED_PAYLOAD_START, ISOLATED_TOTAL_CELLS, admit_isolated_guest_dispatch,
    embed_isolated_guest_dispatch,
};
use crate::strategy::bridge::ternary::TernaryProgram;

/// First source-backed guest operation at D=121.
pub const FIRST_OPCODE_ADDRESS: usize = 121;
/// Second source-backed guest operation reached at D=124.
pub const SECOND_OPCODE_ADDRESS: usize = 124;
/// First descriptor source glyph, after both disjoint guest operations.
pub const TWO_CEB2_START: usize = 125;
/// Source image cell count, including both opcodes and descriptor.
pub const TWO_SOURCE_CELLS: usize = 227;
/// Real profiled VM steps to consume and echo two inputs, then halt.
pub const TWO_GUEST_STEPS: usize = 88;
const DESCRIPTOR_CELLS: usize = 102;
const TWO_PAIRS: [u8; 2] = [2, 0];
const OPERATION_CELLS: [GraphicalOperation; 2] = [
    (FIRST_OPCODE_ADDRESS, 5, 90),
    (SECOND_OPCODE_ADDRESS, 6, 104),
];
type GraphicalOperation = (usize, usize, u8);

/// Fail-closed research source or descriptor rejection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TwoOpcodeError {
    /// Invalid loader phase, canonical source, digest or profile.
    Guest(GuestPayloadProbeError),
    /// Source shape, a graphical operation or a source glyph was changed.
    InvalidSource,
    /// This bounded executable design accepts exactly two original pairs.
    UnsupportedEchoCount,
}

impl From<GuestPayloadProbeError> for TwoOpcodeError {
    fn from(value: GuestPayloadProbeError) -> Self {
        Self::Guest(value)
    }
}

fn required_count(candidate: &[u8]) -> Result<(), TwoOpcodeError> {
    if candidate.get(4..6) == Some(TWO_PAIRS.as_slice()) {
        Ok(())
    } else {
        Err(TwoOpcodeError::UnsupportedEchoCount)
    }
}

fn exact_code_prefix() -> Result<Vec<u8>, TwoOpcodeError> {
    if TWO_CEB2_START != SECOND_OPCODE_ADDRESS.saturating_add(1)
        || TWO_SOURCE_CELLS != TWO_CEB2_START.saturating_add(DESCRIPTOR_CELLS)
    {
        return Err(TwoOpcodeError::InvalidSource);
    }
    for (address, rank, expected_word) in OPERATION_CELLS {
        let glyph = *alphabet(address)?
            .get(rank)
            .ok_or(TwoOpcodeError::InvalidSource)?;
        if glyph != expected_word || usize::from(glyph) >= TWO_CEB2_START {
            return Err(TwoOpcodeError::InvalidSource);
        }
    }
    let mut code = Vec::with_capacity(TWO_CEB2_START);
    for position in 0..TWO_CEB2_START {
        let glyph = match position {
            0 => instruction_at(position, b'j')?,
            81 | 93 => instruction_at(position, b'i')?,
            91 | 105 => instruction_at(position, b'/')?,
            92 | 106 => instruction_at(position, b'<')?,
            107 => instruction_at(position, b'v')?,
            FIRST_OPCODE_ADDRESS => 90,
            SECOND_OPCODE_ADDRESS => 104,
            _ => instruction_at(position, b'o')?,
        };
        code.push(glyph);
    }
    Ok(code)
}

/// Emit two consecutive source-bound graphical guest operations.
///
/// The canonical CEB2 descriptor is admitted before the candidate is built.
/// Its 102 graphical data cells are re-ranked at their new loader positions,
/// rather than copied as phase-dependent ASCII bytes from the v5 source.
///
/// # Errors
///
/// Refuses noncanonical source/profile, unsupported count, malformed CEB2,
/// impossible graphical layout or numeric jump that aliases descriptor data.
pub fn embed_two_echo_opcodes(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    candidate: &[u8],
) -> Result<Vec<u8>, TwoOpcodeError> {
    let admitted_old = embed_isolated_guest_dispatch(program, profile, candidate)?;
    required_count(candidate)?;
    let mut source = exact_code_prefix()?;
    let tail = admitted_old
        .get(ISOLATED_PAYLOAD_START..ISOLATED_TOTAL_CELLS)
        .ok_or(TwoOpcodeError::InvalidSource)?;
    for (index, &glyph) in tail.iter().enumerate() {
        let from_address = ISOLATED_PAYLOAD_START.saturating_add(index);
        let to_address = TWO_CEB2_START.saturating_add(index);
        let rank = alphabet(from_address)?
            .iter()
            .position(|&option| option == glyph)
            .ok_or(TwoOpcodeError::InvalidSource)?;
        source.push(
            *alphabet(to_address)?
                .get(rank)
                .ok_or(TwoOpcodeError::InvalidSource)?,
        );
    }
    if source.len() != TWO_SOURCE_CELLS {
        return Err(TwoOpcodeError::InvalidSource);
    }
    Ok(source)
}

/// Independently admit code, both actual graphical opcodes and exact CEB2 data.
///
/// Reconstructs the original v5 isolated source representation from the
/// **supplied** guest bytes, then delegates the complete source/profile CEB2
/// binding and canonical-padding check to its separate verifier. Neither
/// this nor any source admission takes place inside guest Malbolge execution.
///
/// # Errors
///
/// Rejects all wrong-size/phase, changed code or opcode, descriptor mutation,
/// forged source identity, profile mismatch or unsupported repeat count.
pub fn admit_two_echo_opcodes(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<[u8; BOUND_ECHO_MACRO_BYTES], TwoOpcodeError> {
    let prefix = exact_code_prefix()?;
    if source.len() != TWO_SOURCE_CELLS || source.get(..TWO_CEB2_START) != Some(prefix.as_slice()) {
        return Err(TwoOpcodeError::InvalidSource);
    }
    let mut reconstructed = Vec::with_capacity(ISOLATED_TOTAL_CELLS);
    for position in 0..ISOLATED_PAYLOAD_START {
        let opcode = match position {
            0 => b'j',
            81 => b'i',
            _ => b'o',
        };
        reconstructed.push(instruction_at(position, opcode)?);
    }
    for (index, &glyph) in source
        .get(TWO_CEB2_START..)
        .ok_or(TwoOpcodeError::InvalidSource)?
        .iter()
        .enumerate()
    {
        let from_address = TWO_CEB2_START.saturating_add(index);
        let to_address = ISOLATED_PAYLOAD_START.saturating_add(index);
        let rank = alphabet(from_address)?
            .iter()
            .position(|&option| option == glyph)
            .ok_or(TwoOpcodeError::InvalidSource)?;
        reconstructed.push(
            *alphabet(to_address)?
                .get(rank)
                .ok_or(TwoOpcodeError::InvalidSource)?,
        );
    }
    let candidate = admit_isolated_guest_dispatch(program, profile, &reconstructed)?;
    required_count(&candidate)?;
    Ok(candidate)
}
