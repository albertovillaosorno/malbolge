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
//   - Physical N15 repeated rotations with checked loader-seed relocation.
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
//! The default `,H` tail expands M[95]=7,174,457, M[96]=72.
//! Other admitted graphical tails may supply different first operands as long
//! as the exact M[96]=72 reset chain remains valid. Executed `j`
//! instructions reset D through M[96]=72, M[73]=61 and M[62]=94, returning
//! to M[95] for each subsequent `*`. Source[40]=94 sets up the original
//! jump from D=40 and can itself execute as a `j` after the tenth rotate.
//! This is a bounded guest arithmetic primitive, not C23 input conversion.

use malbolge::{
    ProfileDescriptor, current_profile, decode_profile_instruction,
};

use super::{LinearOpcode, unique_graphical_cell, unwritten_loader_word};

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
    /// The supplied tail is unloadable or changes the exact pointer reset.
    InvalidResetSeed {
        /// Exact candidate source tail.
        tail: [u8; 2],
    },
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
    build_seeded_repeated_loader_rotation_source(profile, rotations, *b",H")
}

/// Build an exact same-cell rotation witness for a graphical loader tail.
///
/// The reset is valid only when the *actual* loader recurrence at M[96] is
/// 72: `j` then follows M[73]=61 and M[62]=94 back to operand M[95].
/// Both tail cells must decode as admitted source instructions at positions
/// 89 and 90. No host value substitutes for any executed rotation.
///
/// # Errors
///
/// Refuses invalid profiles, rotation budgets and source/loader tails whose
/// actual pointer chain cannot preserve the repeated operand address.
pub fn build_seeded_repeated_loader_rotation_source(
    profile: &ProfileDescriptor,
    rotations: u8,
    tail: [u8; 2],
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
    source[89..91].copy_from_slice(&tail);
    let decodable = tail.iter().enumerate().all(|(offset, &byte)| {
        unique_graphical_cell(
            profile,
            LinearOpcode::SkippedDataByte { byte: u32::from(byte) },
            89 + offset,
        ) == Ok(byte)
    });
    if !decodable || unwritten_loader_word(&source, 96, profile) != Ok(72) {
        return Err(RepeatedLoaderRotationError::InvalidResetSeed { tail });
    }
    Ok(source)
}

/// Compose nine physical loader rotations with one actual signed guest read.
///
/// After the ninth `*`, three reached `j` operations reset D to M[95]
/// for `/`. The unmodified source constant at C40 then executes as a `j`,
/// starting a second reset to M[95] for two adjacent input-dependent `p`
/// writes at M[95] and M[96]. `<` emits the resulting low byte and `v`
/// halts after 47 actual guest steps. The eight admitted graphical tails
/// leave M[96]=72, **not** the C23 conversion operand 121. Consequently
/// this source is an experimental signed-input arithmetic probe, never a
/// C23 conversion or a compiled mutable-C program.
///
/// # Errors
///
/// Rejects historical profiles, unloadable seed tails and positions with
/// no graphical encoding. Runtime behavior requires independent VM proof.
pub fn build_seeded_rotated_input_crazy_source(
    profile: &ProfileDescriptor,
    tail: [u8; 2],
) -> Result<Vec<u8>, RepeatedLoaderRotationError> {
    let mut source =
        build_seeded_repeated_loader_rotation_source(profile, 9, tail)?;
    for (position, opcode) in [
        (36, b'j'),
        (37, b'j'),
        (38, b'j'),
        (39, profile.input_instruction()),
        // Source[40]=94 is a reached `j` and a pointer constant.
        (41, b'j'),
        (42, b'j'),
        (43, b'p'),
        (44, b'p'),
        (45, profile.output_instruction()),
        (46, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    Ok(source)
}
