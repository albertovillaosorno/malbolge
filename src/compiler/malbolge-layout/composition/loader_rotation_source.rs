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
//   - Physical N15 repeated rotations with source-bound pointer relocation.
// - Must-Not:
//   - Treat the rotated seed as a signed C23 converter or source-C compiler.
// - Allows:
//   - Inputs: current profile and 1..=15 exact rotation rounds.
//   - Outputs: printable 91-cell candidate for independent normative VM proof.
//   - Side effects: none; code generation does not execute guest instructions.
// - Split-When:
//   - General operand synthesis replaces this fixed loader/reset geometry.
// - Merge-When:
//   - A verified physical arithmetic linker uses generic relocatable blocks.
// - Summary:
//   - Moves repeatable real pointer-reset rotation out of test-only source.

//! Physically repeat one loader-cell rotation through a three-jump reset.
//!
//! Source tail `,H` expands M[95]=7,174,457, M[96]=72. Executed `j`
//! instructions reset D through M[96]=72, M[73]=61 and M[62]=94, returning
//! to M[95] for each subsequent `*`. Source[40]=94 sets up the original
//! jump from D=40 and can itself execute as a `j` after the tenth rotate.
//! This is a bounded guest arithmetic primitive, not C23 input conversion.

use malbolge::{
    ProfileDescriptor, current_profile, decode_profile_instruction,
};

const SOURCE_CELLS: usize = 91;
const MAX_ROTATIONS: u8 = 15;

/// Failure to construct a source-valid physical rotation candidate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RepeatedLoaderRotationError {
    /// One through fifteen rotations are independently admitted.
    InvalidRotationCount {
        /// Requested number of data writes.
        rotations: u8,
    },
    /// A source position cannot encode the requested opcode.
    MissingGraphicalEncoding {
        /// Source position.
        position: u8,
        /// Requested decoded instruction.
        opcode: u8,
    },
    /// The fixed geometry belongs to the current 15-trit profile.
    UnsupportedProfile,
}

fn encode(
    position: usize,
    opcode: u8,
) -> Result<u8, RepeatedLoaderRotationError> {
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(
                u32::from(*byte),
                u32::try_from(position).unwrap_or(u32::MAX),
            ) == Some(opcode)
        })
        .ok_or(RepeatedLoaderRotationError::MissingGraphicalEncoding {
            position: u8::try_from(position).unwrap_or(u8::MAX),
            opcode,
        })
}

fn set(
    source: &mut [u8],
    position: usize,
    opcode: u8,
) -> Result<(), RepeatedLoaderRotationError> {
    source[position] = encode(position, opcode)?;
    Ok(())
}

/// Build one physical repeated-rotation guest source for a fixed loader seed.
///
/// Nine rounds here rotate `7,174,457`, **not** the `7,174,404` operand
/// required by the independently proved signed C23 converter. The source
/// outputs the last rotated word's low byte and halts without reading stdin.
/// A caller must admit the exact real VM effects before using this as proof.
///
/// # Errors
///
/// Refuses other profiles and counts outside the independently covered
/// finite window. Each authored opcode must have a graphical encoding.
pub fn build_repeated_loader_rotation_source(
    profile: &ProfileDescriptor,
    rotations: u8,
) -> Result<Vec<u8>, RepeatedLoaderRotationError> {
    if profile != current_profile() {
        return Err(RepeatedLoaderRotationError::UnsupportedProfile);
    }
    if !(1..=MAX_ROTATIONS).contains(&rotations) {
        return Err(RepeatedLoaderRotationError::InvalidRotationCount {
            rotations,
        });
    }
    let mut source = (0..SOURCE_CELLS)
        .map(|position| encode(position, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    source[1] = 39;
    set(&mut source, 2, b'j')?;
    for round in 0..usize::from(rotations) {
        let position = 3 + round * 4;
        set(&mut source, position, b'*')?;
        if round + 1 < usize::from(rotations) {
            for reset in position + 1..=position + 3 {
                set(&mut source, reset, b'j')?;
            }
        }
    }
    // C40 is a mandatory source-side pointer constant. After round ten it
    // is also a reached j, so the terminal output must move to C41.
    let output = if rotations == 10 {
        set(&mut source, 40, b'j')?;
        41
    } else {
        usize::from(rotations) * 4
    };
    set(&mut source, output, profile.output_instruction())?;
    set(&mut source, output + 1, b'v')?;
    source[40] = 94;
    source[62] = 94;
    source[73] = 61;
    source[89..91].copy_from_slice(b",H");
    Ok(source)
}
