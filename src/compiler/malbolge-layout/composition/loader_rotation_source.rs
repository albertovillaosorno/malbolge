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
//   - Repeated rotations and live-input writes with loader-seed relocation.
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
//   - Constructs real repeated rotations and same-cell state updates.

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
    /// The fixed reset chain admits one through three sequential input folds.
    InvalidInputCount {
        /// Requested number of actual guest input attempts.
        inputs: u8,
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

/// Physically write one input-dependent guest word twice in the *same* cell.
///
/// This is a physical mutable-state **precursor**, not C32 arithmetic or a
/// compiled C loop. Nine genuine `*` instructions prepare loader M95; `/`
/// at C39 reads a real byte or profile EOF. `p` at C43 updates M95. Three
/// reached `j` operations at C44..C46 follow M96=72, M73=61, M62=94 and
/// reset D to M95. A second `p` at C47 reads the **first write** and updates
/// the same cell again. C48 outputs the final accumulator; C49 halts. No
/// branch, phi edge, C variable binding, or C23 conversion is implemented.
///
/// # Errors
///
/// Rejects unavailable graphical encodings, non-current profiles or loader
/// tails outside the independently checked pointer-reset seed family. Actual
/// state writes require independent normative VM trace admission.
pub fn build_seeded_repeated_state_write_source(
    profile: &ProfileDescriptor,
    tail: [u8; 2],
) -> Result<Vec<u8>, RepeatedLoaderRotationError> {
    let mut source = build_seeded_rotated_input_crazy_source(profile, tail)?;
    for (position, opcode) in [
        (44, b'j'),
        (45, b'j'),
        (46, b'j'),
        (47, b'p'),
        (48, profile.output_instruction()),
        (49, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    Ok(source)
}

/// Build a bounded guest stream fold over one mutable N15 memory cell.
///
/// Each input attempt is an actual `/`, and each subsequent `p` consumes
/// the previous guest write at M95 before updating that same cell. This is
/// *not* C arithmetic: the fold uses Malbolge `crazy` and raw N15 EOF.
///
/// The 91-cell source supports one, two or three input events. Every event
/// after the first requires a three-`j` pointer reset, one read, another
/// three-`j` reset and one `p` write. A fourth event would execute source
/// cell 62, encrypting its mandatory `94` pointer constant before the next
/// reset; extending this geometry without a new physical proof is forbidden.
/// The caller must independently admit the guest path in the normative VM.
///
/// # Errors
///
/// Refuses unsupported profiles, unknown loader tails, a count outside the
/// exact physical geometry or an unavailable graphical instruction byte.
pub fn build_seeded_guest_input_state_fold_source(
    profile: &ProfileDescriptor,
    tail: [u8; 2],
    inputs: u8,
) -> Result<Vec<u8>, RepeatedLoaderRotationError> {
    if !(1..=3).contains(&inputs) {
        return Err(RepeatedLoaderRotationError::InvalidInputCount { inputs });
    }
    let mut source = build_seeded_repeated_state_write_source(profile, tail)?;
    for event in 1..usize::from(inputs) {
        let start = 44 + (event - 1) * 8;
        for position in start..=start + 2 {
            set(&mut source, position, b'j')?;
        }
        set(&mut source, start + 3, profile.input_instruction())?;
        for position in start + 4..=start + 6 {
            set(&mut source, position, b'j')?;
        }
        set(&mut source, start + 7, b'p')?;
    }
    let output = 44 + (usize::from(inputs) - 1) * 8;
    set(&mut source, output, profile.output_instruction())?;
    set(&mut source, output + 1, b'v')?;
    Ok(source)
}

/// Update one physical guest data word using two distinct input events.
///
/// Nine reached `*` instructions prepare M95. The first `/` at C39 and
/// `p` at C43 write a function of that input to M95. The C44..46
/// reset follows M96=72, M73=61 and M62=94, then C47 reads the second
/// input. A second C48..50 reset restores D to M95, allowing C51 `p` to
/// read the first stored result and overwrite the **same** word with a
/// function of both inputs. C52 `<` emits the final word's low byte and
/// C53 `v` halts. EOF uses the selected profile's raw word, not C23 -1.
/// This is physical state and I/O linkage, not a C loop, conditional,
/// signed byte conversion or compiled mutable checksum.
///
/// # Errors
///
/// Rejects unsupported profiles, invalid seed tails and missing graphical
/// encodings. Independent normative VM traces still prove guest effects.
pub fn build_seeded_two_input_state_update_source(
    profile: &ProfileDescriptor,
    tail: [u8; 2],
) -> Result<Vec<u8>, RepeatedLoaderRotationError> {
    build_seeded_guest_input_state_fold_source(profile, tail, 2)
}

/// Preserve a lossless encoded first signed input across a second guest read.
///
/// Nine physical rotations of loader M95 give 7,177,369, whose lowest six
/// trits are all 1. The first real `/` at C39 and `p` at C43 therefore save
/// **every** byte and the distinct signed EOF word injectively in M95.
/// The C44..C46 reset and C47 second `/` remain real guest operations.
/// A three-jump reset at C48..C50 leaves D at M95, but C51 deliberately
/// executes an inert operation instead of overwriting the saved word.
/// C52 outputs the second input's low byte and C53 halts. The first word is
/// recoverable from guest memory, not yet decoded to C23 `int` or linked to
/// source-variable assignments, arithmetic, EOF control, or a guest loop.
///
/// # Errors
///
/// Rejects unsupported profile, an invalid reset tail, or an unavailable
/// graphical encoding. Actual 257-class storage and second-read paths
/// require independent normative VM verification.
pub fn build_seeded_preserved_first_input_source(
    profile: &ProfileDescriptor,
    tail: [u8; 2],
) -> Result<Vec<u8>, RepeatedLoaderRotationError> {
    let mut source = build_seeded_two_input_state_update_source(profile, tail)?;
    set(&mut source, 51, b'o')?;
    Ok(source)
}

/// Emit a saved first signed word *after* a real second-input output.
///
/// The C39/C43 input and lossless `p` fold save the first word in M95.
/// C47 reads the second input, and C51 outputs its actual low byte after
/// resetting D to M95. A second three-`j` reset at C52..C54 returns to
/// that same saved M95, where C55 `*` reloads it into A by a bijective
/// rotation and C56 `<` emits the derived first-word low byte.
/// Both EOF reads remain real N15 signed reads. A rotated encoding remains
/// lossless in the guest cell; its output byte alone is not a C23 `int`.
/// The source has no C23 arithmetic, conditional or dynamic loop linker.
///
/// # Errors
///
/// Rejects invalid profile, loader seed or unavailable graphical opcodes.
/// Independent VM verification must establish the state and I/O ordering.
pub fn build_seeded_delayed_first_output_source(
    profile: &ProfileDescriptor,
    tail: [u8; 2],
) -> Result<Vec<u8>, RepeatedLoaderRotationError> {
    let mut source = build_seeded_preserved_first_input_source(profile, tail)?;
    for (position, opcode) in [
        (51, profile.output_instruction()),
        (52, b'j'),
        (53, b'j'),
        (54, b'j'),
        (55, b'*'),
        (56, profile.output_instruction()),
        (57, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    Ok(source)
}

/// Retain both physical signed input words in disjoint N15 memory cells.
///
/// The fixed `IH` loader tail provides M95=7,174,489, whose nine rotations
/// yield 7,200,697, and virgin M97=7,174,453. Both seeds have six low
/// trits equal to one. C39 `/` and C43 `p` save the entire first input at
/// M95. C47 `/` reads the second input, C48..C50 reset D to M95, and two
/// inert instructions advance to M97 for C53 `p`. C54 emits the second
/// saved *encoding* and C55 halts. The first word is never overwritten.
/// Each encoded cell distinguishes all 256 bytes and signed EOF, but the
/// output is not a decoded C23 byte. No dynamic source control or C32 state
/// operation is implied by the two physical stores.
///
/// # Errors
///
/// Refuses incompatible profile or unavailable position-sensitive opcodes.
/// The exact initial M97 seed must be preserved by the loader, and all
/// physical paths require independent VM proof.
pub fn build_two_retained_signed_inputs_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, RepeatedLoaderRotationError> {
    const TAIL: [u8; 2] = *b"IH";
    let mut source = build_seeded_preserved_first_input_source(profile, TAIL)?;
    if unwritten_loader_word(&source, 97, profile) != Ok(7_174_453) {
        return Err(RepeatedLoaderRotationError::InvalidResetSeed {
            tail: TAIL,
        });
    }
    for (position, opcode) in [
        (52, b'o'),
        (53, b'p'),
        (54, profile.output_instruction()),
        (55, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    Ok(source)
}

/// Apply a genuine two-operand guest crazy operation after two signed reads.
///
/// The fixed IH loader seeds two disjoint 257-class storage words. C43
/// saves the first input at M95, C53 saves the second at M97, and A retains
/// the second encoding. The loader then gives M98=72, M73=61 and M62=94:
/// three real jumps at C54..C56 reset D from M98 to M95.
/// C57 overwrites M95 with `crazy(saved_first, saved_second)`, while M97
/// remains unchanged. C58 outputs this joint result's low byte, and C59
/// halts. The source has neither host-computed output nor a replayed input.
///
/// This is binary Malbolge arithmetic on two stored input-dependent
/// words, not C23 addition/XOR, signed decoding, a C variable or an EOF loop.
/// The bounded source must be admitted by normative guest trace verification.
///
/// # Errors
///
/// Refuses historical profiles or a broken loader/encoding geometry.
pub fn build_two_retained_inputs_cross_fold_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, RepeatedLoaderRotationError> {
    let mut source = build_two_retained_signed_inputs_source(profile)?;
    if unwritten_loader_word(&source, 98, profile) != Ok(72) {
        return Err(RepeatedLoaderRotationError::InvalidResetSeed {
            tail: *b"IH",
        });
    }
    for (position, opcode) in [
        (54, b'j'),
        (55, b'j'),
        (56, b'j'),
        (57, b'p'),
        (58, profile.output_instruction()),
        (59, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    Ok(source)
}

/// Emit two guest-visible prefixes of a mutable two-input N15 fold.
///
/// Both input attempts execute real `/` instructions. Each `p` reads and
/// overwrites M95, and each following `<` emits that freshly stored state.
/// The first output requires an additional three-`j` reset to M95 before
/// the second input can be read: after a `p`, D is M96, but `<` also advances
/// D. The sequence has physical events at C39/43/47 and C51/55/56 and
/// halts at C57 (58 normative steps). M62 and M73 remain source constants,
/// never reached as code. This is a fixed-length guest prefix operation,
/// not a dynamic C loop, signed C23 conversion or C arithmetic.
///
/// # Errors
///
/// Refuses unsupported profiles, invalid loader seeds and any missing
/// position-sensitive opcode encoding. Independent VM paths must still
/// establish the read/write/output semantics.
pub fn build_seeded_two_input_prefix_fold_source(
    profile: &ProfileDescriptor,
    tail: [u8; 2],
) -> Result<Vec<u8>, RepeatedLoaderRotationError> {
    let mut source = build_seeded_two_input_state_update_source(profile, tail)?;
    for (position, opcode) in [
        (44, b'j'),
        (45, b'j'),
        (46, b'j'),
        (47, profile.output_instruction()),
        (48, b'j'),
        (49, b'j'),
        (50, b'j'),
        (51, profile.input_instruction()),
        (52, b'j'),
        (53, b'j'),
        (54, b'j'),
        (55, b'p'),
        (56, profile.output_instruction()),
        (57, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    Ok(source)
}

/// Emit one checkpoint before two more input-driven guest state updates.
///
/// Nine reached rotations prepare M95. The first read at C39 and write at
/// C43 produce a real output at C47. The next two independent reads at
/// C51/C59 update that *same* guest memory word at C55/C63. C64 emits the
/// final state and C65 halts. The middle read does not produce an output;
/// guest state survives across the first output and multiple later writes.
/// The M96=66 reset through M67/M68 is essential: source C62 executes as
/// `j`, so the older M62=94 pointer constant would be destroyed.
/// These are Malbolge `crazy` folds, not C23 arithmetic or an EOF branch.
///
/// # Errors
///
/// Refuses tails without the protected 66/67/68 reset chain, non-current
/// profiles and unavailable source encodings. VM execution must independently
/// verify the exact source's read/write/output sequence.
pub fn build_seeded_three_input_checkpoint_fold_source(
    profile: &ProfileDescriptor,
    tail: [u8; 2],
) -> Result<Vec<u8>, RepeatedLoaderRotationError> {
    // Start from the independently checked nine-rotation C39/C43/C47 path.
    // Relocate only its pointer reset to the alternate loader-66 chain.
    let mut source =
        build_seeded_two_input_prefix_fold_source(profile, *b",H")?;
    source[89..91].copy_from_slice(&tail);
    let decodable = tail.iter().enumerate().all(|(offset, &byte)| {
        unique_graphical_cell(
            profile,
            LinearOpcode::SkippedDataByte { byte: u32::from(byte) },
            89 + offset,
        ) == Ok(byte)
    });
    if !decodable || unwritten_loader_word(&source, 96, profile) != Ok(66) {
        return Err(RepeatedLoaderRotationError::InvalidResetSeed { tail });
    }
    source[67] = 67;
    source[68] = 94;
    for (position, opcode) in [
        (56, b'j'),
        (57, b'j'),
        (58, b'j'),
        (59, profile.input_instruction()),
        (60, b'j'),
        (61, b'j'),
        (62, b'j'),
        (63, b'p'),
        (64, profile.output_instruction()),
        (65, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    Ok(source)
}

/// Repair the C23 seed's loader pointer trap and perform physical rotations.
///
/// The `Iy` tail initializes M[95]=7,174,404 and M[96]=121. A reached
/// `p` at C2 changes loader M[94] into 7,174,489; a second `p` at C6
/// then changes M[158]=157 into 36. Five physical `j` operations can now
/// reset D from M[96] through M[122], M[158], M[37], and M[81] to M[95].
/// This source physically rotates the **correct initial** converter operand
/// five times before one real signed input and raw echo. C37 is both the
/// needed source pointer byte 80 and an executed `/`, so the loop cannot
/// simply be extended to nine rotations. The nine-rotation C23 converter,
/// two input-dependent `p` operations, and compiled checksum remain absent.
///
/// # Errors
///
/// Only the current 15-trit profile has this loader recurrence and graphical
/// layout. Normative VM execution must independently prove all effects.
pub fn build_c23_seed_rotated_input_echo_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, RepeatedLoaderRotationError> {
    if profile != current_profile() {
        return Err(RepeatedLoaderRotationError::UnsupportedProfile);
    }
    let mut source = (0..SOURCE_CELLS)
        .map(|position| encode(position, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (position, opcode) in [
        (0, b'j'),
        (1, b'j'),
        (2, b'p'),
        (4, b'j'),
        (5, b'j'),
        (6, b'p'),
        (8, b'j'),
        (9, b'j'),
        (10, b'j'),
        (11, b'j'),
        (37, profile.input_instruction()),
        (38, profile.output_instruction()),
        (39, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    for round in 0..5usize {
        let position = 12 + round * 6;
        set(&mut source, position, b'*')?;
        if round != 4 {
            for reset in position + 1..=position + 5 {
                set(&mut source, reset, b'j')?;
            }
        }
    }
    // Source/data overlap is deliberate and each byte is loader-admissible.
    // M[37]=80 is also the physical `/` at C37 on this forward path.
    source[0] = 40;
    source[37] = 80;
    source[41] = 93;
    source[81] = 94;
    source[89..91].copy_from_slice(b"Iy");
    Ok(source)
}

/// Physically rotate the correct C23 `Iy` loader operand nine times.
///
/// The exact source-required M[37]=80 is `/` at C37. This necessarily
/// consumes an extra input attempt after five rotations and encrypts M37
/// to 66. The *post-encryption* pointer return therefore needs M[67]=67
/// (`j` when reached) and M[68]=94 (`o` when reached), instead of the
/// original M[81]=94. After the intermediate input, five `j` operations
/// return D to M95; subsequent six-jump resets complete nine physical
/// `*` writes, whose last result is output with `<` and halted with `v`.
/// All source cells are loadable; the ninth physical operand reaches
/// 7,138,732. This is **not** C23 byte conversion: the forced input is
/// discarded by later rotations, no two input-dependent `p` operations
/// execute, and the resulting output is a fixed operand probe byte.
///
/// # Errors
///
/// Refuses other profiles. Independently admitted normative VM execution is
/// necessary to establish all pointer returns and physical writes.
pub fn build_c23_seed_nine_rotated_operand_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, RepeatedLoaderRotationError> {
    if profile != current_profile() {
        return Err(RepeatedLoaderRotationError::UnsupportedProfile);
    }
    let mut source = (0..SOURCE_CELLS)
        .map(|position| encode(position, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (position, opcode) in [
        (0, b'j'),
        (1, b'j'),
        (2, b'p'),
        (4, b'j'),
        (5, b'j'),
        (6, b'p'),
        (8, b'j'),
        (9, b'j'),
        (10, b'j'),
        (11, b'j'),
        (37, profile.input_instruction()),
        (39, b'j'),
        (40, b'j'),
        (41, b'j'),
        (42, b'j'),
        (43, b'j'),
        (66, profile.output_instruction()),
        (67, b'j'),
        (69, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    for (round, position) in [12usize, 18, 24, 30, 36, 44, 51, 58, 65]
        .into_iter()
        .enumerate()
    {
        set(&mut source, position, b'*')?;
        if round != 4 && round != 8 {
            let reset_count = if round < 4 {
                5
            } else {
                6
            };
            for reset in position + 1..=position + reset_count {
                set(&mut source, reset, b'j')?;
            }
        }
    }
    source[0] = 40;
    source[37] = 80;
    source[41] = 93;
    source[67] = 67;
    source[68] = 94;
    source[81] = 94;
    source[89..91].copy_from_slice(b"Iy");
    Ok(source)
}
