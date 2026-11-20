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
//   - Reproducible graphical construction of the reached signed EOF branch.
// - Must-Not:
//   - Claim arbitrary input loops, C lowering, or verified source publication.
// - Allows:
//   - Inputs: exact current N15 target profile identity.
//   - Outputs: one bounded two-arm graphical source candidate for VM admission.
//   - Side effects: none.
// - Split-When:
//   - The general conditional guest linker can place these exact operations.
// - Merge-When:
//   - The nonlinear layout planner emits signed EOF control directly.
// - Summary:
//   - Moves the executed physical EOF/byte branch out of test-only assembly.
//
//! Bounded N15 physical signed byte/EOF branch source construction.
//!
//! The one-read classifier sends all 256 successful bytes to C=45 and the
//! signed EOF word to C=126. Its two arms output distinct fixed marker bytes
//! and halt. This is not a loop or a general C source lowering rule; callers
//! must verify actual guest paths before publishing an artifact.

use malbolge::{
    ProfileDescriptor, current_profile, decode_profile_instruction,
    encrypt_profile_cell,
};

const SOURCE_LENGTH: usize = 132;

/// Failure to construct the exact experimental N15 branch candidate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SignedEofBranchSourceError {
    /// A source edit escaped the fixed 132-cell candidate bounds.
    InvalidPosition {
        /// Source position outside the fixed candidate.
        position: usize,
    },
    /// No printable source byte decodes to the requested instruction.
    MissingGraphicalEncoding {
        /// Assigned source position.
        position: usize,
        /// Requested decoded instruction.
        opcode: u8,
    },
    /// No graphical byte executes two required opcodes across encryption.
    MissingRevisitedEncoding {
        /// Source position reached on both passes.
        position: usize,
        /// Opcode executed before the first post-step encryption.
        first: u8,
        /// Opcode decoded from the encrypted cell on its next visit.
        second: u8,
    },
    /// This assembly depends on current-profile geometry and loader words.
    UnsupportedProfile,
}

fn encode(
    position: usize,
    opcode: u8,
) -> Result<u8, SignedEofBranchSourceError> {
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(
                u32::from(*byte),
                u32::try_from(position).unwrap_or(u32::MAX),
            ) == Some(opcode)
        })
        .ok_or(SignedEofBranchSourceError::MissingGraphicalEncoding {
            position,
            opcode,
        })
}

fn put(
    source: &mut [u8],
    position: usize,
    opcode: u8,
) -> Result<(), SignedEofBranchSourceError> {
    let byte = encode(position, opcode)?;
    let cell = source
        .get_mut(position)
        .ok_or(SignedEofBranchSourceError::InvalidPosition { position })?;
    *cell = byte;
    Ok(())
}

/// Change one graphical code cell into a checked two-pass instruction.
///
/// The current VM encrypts the code cell on its first execution. A revisit
/// must decode the encrypted byte at the *same* code pointer, so selecting
/// the first opcode alone is not sufficient.
fn put_revisited(
    source: &mut [u8],
    position: usize,
    first: u8,
    second: u8,
) -> Result<(), SignedEofBranchSourceError> {
    // A second-pass decode is worthless unless the first-pass source byte
    // itself is a loader-valid target instruction. A graphical byte that
    // first decodes to an unknown opcode is rejected during source loading,
    // even when its encrypted successor decodes to the requested opcode.
    if !b"oijp*/<v".contains(&first) {
        return Err(SignedEofBranchSourceError::MissingRevisitedEncoding {
            position,
            first,
            second,
        });
    }
    let code_pointer = u32::try_from(position).unwrap_or(u32::MAX);
    let byte = (33..=126u8)
        .find(|candidate| {
            decode_profile_instruction(u32::from(*candidate), code_pointer)
                == Some(first)
                && encrypt_profile_cell(u32::from(*candidate)).is_some_and(
                    |encrypted| {
                        decode_profile_instruction(encrypted, code_pointer)
                            == Some(second)
                    },
                )
        })
        .ok_or(SignedEofBranchSourceError::MissingRevisitedEncoding {
            position,
            first,
            second,
        })?;
    *source
        .get_mut(position)
        .ok_or(SignedEofBranchSourceError::InvalidPosition { position })? =
        byte;
    Ok(())
}

/// Build a physically executable EOF-guarded second signed input.
///
/// A first successful byte executes the original byte arm, revisits C=101,
/// and reads the next byte (or true EOF) via an encrypted first-pass p.
/// A first EOF instead reaches the terminal EOF arm before that revisit,
/// so it never issues a second read. Both arms still output fixed markers;
/// this is bounded physical control, not a C checksum or an arbitrary loop.
///
/// # Errors
///
/// Refuses other target profiles and positions lacking a valid two-pass
/// graphical source cell. Actual VM path admission is required separately.
pub fn build_guarded_signed_eof_second_read_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, SignedEofBranchSourceError> {
    let mut source = build_signed_eof_branch_source(profile)?;
    // The first traversal of C=101 is p, after the classifier has already
    // formed its branch word. Only the byte arm revisits C=101; XLAT2 then
    // decodes the same cell as /, while the EOF arm skips it entirely.
    put_revisited(&mut source, 101, b'p', profile.input_instruction())?;
    Ok(source)
}

/// Build a physical signed-byte echo with an EOF-guarded second input.
///
/// C=53 reads one byte (or the actual N15 EOF sentinel). C=54 then emits
/// that input word's low byte before any classifier arithmetic. On the byte
/// arm C=54 is revisited after encryption, where it decodes as an inactive
/// instruction instead of echoing the stale accumulator a second time.
/// The existing branch then emits its fixed class marker and conditionally
/// reads the next physical input at C=101. On initial EOF it halts without
/// reading again. This is not source-C EOF normalization, a checksum, or
/// an unbounded loop; every candidate requires independent VM admission.
///
/// # Errors
///
/// Rejects other target profiles and invalid graphical encodings.
pub fn build_guarded_signed_eof_echo_and_second_read_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, SignedEofBranchSourceError> {
    let mut source = build_guarded_signed_eof_second_read_source(profile)?;
    // C=54's first-pass < encrypts into a no-op at its byte-arm revisit.
    // Thus the first signed input is emitted once without disturbing A/D
    // before the existing exact EOF discriminator runs.
    put(&mut source, 54, profile.output_instruction())?;
    Ok(source)
}

/// Emit two signed input words, then a guest-selected first-input EOF marker.
///
/// C53/C99 perform two separate real `/` instructions. C54/C100 emit their
/// input accumulators before the classifier's remaining control executes.
/// The first input still selects the encrypted success-arm C57 output (0x9a)
/// or the EOF-arm C128 output (0x1e). Both arms terminate: 175 steps for a
/// first byte and 119 for first EOF. Missing inputs echo the N15 EOF low
/// byte (0x6a), **not** the C23 unsigned-char conversion of EOF.
///
/// This is physical two-read byte dataflow plus dynamic control, not a
/// source-C lowering, mutable local, or repeatable EOF loop. The normative
/// VM and independent bounded path oracles must still admit every case.
///
/// # Errors
///
/// Refuses unsupported profiles or unavailable graphical source positions.
pub fn build_two_input_eof_classified_echo_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, SignedEofBranchSourceError> {
    let mut source = build_signed_eof_branch_source(profile)?;
    for (position, opcode) in [
        (54, profile.output_instruction()),
        (99, profile.input_instruction()),
        (100, profile.output_instruction()),
    ] {
        put(&mut source, position, opcode)?;
    }
    Ok(source)
}

/// Build two real, distinct signed-input echoes in one physical guest path.
///
/// The source's C=53 classifier still performs input-dependent arithmetic,
/// but the later branch jump is replaced with a second physical `/` at C=104.
/// C=54 and C=114 output the first and second input accumulator words,
/// respectively, and the former fixed class marker at C=128 is suppressed.
/// Both actual EOF attempts use the target's low byte (not C23 `EOF`).
/// This is a bounded, unconditional two-read primitive, not checksum
/// lowering, a source-C output conversion or a general EOF loop.
///
/// # Errors
///
/// Rejects noncanonical target profiles or missing graphical encodings.
/// The exact source must still be independently checked in the normative VM.
pub fn build_two_signed_guest_echo_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, SignedEofBranchSourceError> {
    let mut source = build_signed_eof_branch_source(profile)?;
    put(&mut source, 54, profile.output_instruction())?;
    put(&mut source, 104, profile.input_instruction())?;
    put(&mut source, 114, profile.output_instruction())?;
    put(&mut source, 128, b'o')?;
    Ok(source)
}

/// Build a physical, bounded N15 byte-versus-EOF branch candidate.
///
/// This is the already-executed *one-read* control skeleton. Its fixed
/// output markers are `0x9a` on a byte and `0x1e` on EOF. It is not
/// source-C lowering and is not permitted to masquerade as a checksum.
///
/// # Errors
///
/// Rejects noncanonical target profiles or an unavailable position-sensitive
/// graphical encoding. Normative VM admission remains a separate requirement.
pub fn build_signed_eof_branch_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, SignedEofBranchSourceError> {
    if profile != current_profile() {
        return Err(SignedEofBranchSourceError::UnsupportedProfile);
    }
    let mut source = (0..SOURCE_LENGTH)
        .map(|position| encode(position, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    put(&mut source, 8, b'j')?;
    // Rotate M[135] twelve times while relocating D after each rotation.
    for round in 0usize..12 {
        let position = 17usize.saturating_add(round.saturating_mul(3));
        put(&mut source, position, b'*')?;
        put(&mut source, position.saturating_add(1), b'j')?;
        put(&mut source, position.saturating_add(2), b'j')?;
    }
    put(&mut source, 53, profile.input_instruction())?;
    put(&mut source, 55, b'j')?;
    // The fourth write at C=67, rather than C=69, prevents an encrypted
    // second read of the next stdin byte on the backward success arm.
    for position in [64, 65, 66, 67, 79, 82] {
        put(&mut source, position, b'p')?;
    }
    for position in [72, 73, 83, 84, 98, 105] {
        put(&mut source, position, b'j')?;
    }
    for position in [76, 104, 127] {
        put(&mut source, position, b'*')?;
    }
    put(&mut source, 114, b'i')?;
    put(&mut source, 128, profile.output_instruction())?;
    put(&mut source, 129, b'v')?;
    // The untouched loader recurrence depends on both final source bytes.
    source
        .get_mut(130..)
        .ok_or(SignedEofBranchSourceError::InvalidPosition { position: 130 })?
        .copy_from_slice(b"-}");
    // First pass at C=104 encrypts this opcode to the success-arm halt;
    // C=126 starts the EOF arm, which skips the earlier success output.
    Ok(source)
}
