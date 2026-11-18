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
};

const SOURCE_LENGTH: usize = 132;

/// Failure to construct the exact experimental N15 branch candidate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SignedEofBranchSourceError {
    /// This assembly depends on current-profile geometry and loader words.
    UnsupportedProfile,
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
