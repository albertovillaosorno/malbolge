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
//   - Loader-valid source placement for two actual signed-input crazy writes.
// - Must-Not:
//   - Present unrotated loader operands as C23 byte conversion or C codegen.
// - Allows:
//   - Inputs: exact current 15-trit target profile.
//   - Outputs: one physical /,p,p,<,v candidate with bounded addresses.
//   - Side effects: none; downstream normative execution proves the source.
// - Split-When:
//   - General guest operand synthesis replaces fixed graphical placement.
// - Merge-When:
//   - The real C23 converter realizes nine pre-input operand rotations.
// - Summary:
//   - Connects real loader words to input-dependent physical crazy writes.

//! Physical guest loader, byte-I/O and arithmetic experiments, **not** C23
//! source-language compilation or signed byte normalization.
//!
//! The `Iy` graphical seed supplies operands for nine genuine rotations
//! and real input-dependent crazy operations. Source/data intersections
//! still prevent correct C23 conversion from reaching a guest output.
//! Partial probes are never published as lowered C programs.

use malbolge::{
    ProfileDescriptor, current_profile, decode_profile_instruction,
};

use super::loader_rotation_source::{
    RepeatedLoaderRotationError, build_c23_seed_nine_rotated_operand_source,
    build_c23_seed_rotated_input_echo_source,
};

const SOURCE_CELLS: usize = 279;

/// Failure to construct the exact graphical input/operand experiment.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum C23OperandProbeSourceError {
    /// A graphical probe needs two source cells for loader expansion.
    InsufficientSourceCells {
        /// Number of provided source words.
        cells: usize,
    },
    /// Source words must fit the current profile's memory domain.
    SourceExceedsMemory {
        /// Number of provided source words.
        cells: usize,
        /// Maximum loaded word count.
        limit: u32,
    },
    /// An operation escaped the frozen source length.
    InvalidPosition {
        /// Rejected source position.
        position: usize,
    },
    /// Source position has no valid graphical encoding for its opcode.
    MissingGraphicalEncoding {
        /// Exact attempted code position.
        position: usize,
        /// Requested decoded opcode.
        opcode: u8,
    },
    /// The source-locked Iy rotation seed could not be prepared.
    RotationPreparation {
        /// Exact failure in the source-locked rotation stage.
        error: RepeatedLoaderRotationError,
    },
    /// A generated graphical cell cannot pass the strict VM loader.
    InvalidGraphicalSourceCell {
        /// Invalid exact source position.
        position: usize,
        /// Source byte the loader would reject.
        byte: u8,
    },
    /// Current 15-trit profile is the only supported loader geometry.
    UnsupportedProfile,
}

fn graphical(
    position: usize,
    opcode: u8,
) -> Result<u8, C23OperandProbeSourceError> {
    let address = u32::try_from(position).unwrap_or(u32::MAX);
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), address)
                == Some(opcode)
        })
        .ok_or(C23OperandProbeSourceError::MissingGraphicalEncoding {
            position,
            opcode,
        })
}

fn set(
    source: &mut [u8],
    position: usize,
    opcode: u8,
) -> Result<(), C23OperandProbeSourceError> {
    let byte = graphical(position, opcode)?;
    *source
        .get_mut(position)
        .ok_or(C23OperandProbeSourceError::InvalidPosition { position })? =
        byte;
    Ok(())
}

/// Reject cells that the strict graphical profile loader would reject.
///
/// This checks lexical source admission only. In particular, an instruction
/// that is valid at its *source* position may encrypt into a different opcode
/// before a subsequent execution; VM path verification remains separate.
///
/// # Errors
///
/// Reports the first non-graphical or illegal decoded source cell.
pub fn admit_c23_probe_graphical_source(
    source: &[u8],
) -> Result<(), C23OperandProbeSourceError> {
    if source.len() < 2 {
        return Err(C23OperandProbeSourceError::InsufficientSourceCells {
            cells: source.len(),
        });
    }
    let limit = current_profile().word_modulus();
    if source.len() > usize::try_from(limit).unwrap_or(usize::MAX) {
        return Err(C23OperandProbeSourceError::SourceExceedsMemory {
            cells: source.len(),
            limit,
        });
    }
    for (position, &byte) in source.iter().enumerate() {
        let address = u32::try_from(position).unwrap_or(u32::MAX);
        if !decode_profile_instruction(u32::from(byte), address)
            .is_some_and(|opcode| b"oijp*/<v".contains(&opcode))
        {
            return Err(
                C23OperandProbeSourceError::InvalidGraphicalSourceCell {
                    position,
                    byte,
                },
            );
        }
    }
    Ok(())
}

/// Construct a VM-executable signed-input/two-crazy **probe** source.
///
/// The first `j` at C=8 relocates D to 127; by C=164, D=282.
/// The `/` reads the actual byte or target EOF word; `p` at C=165,166
/// then reads loader-expanded M[283], M[284], and `<` emits at C=167.
/// A 169-step halt occurs at C=168. The output is **not** the C23 byte.
///
/// # Errors
///
/// Rejects wrong profiles or a missing graphical source encoding. The
/// resulting candidate still requires independent normative VM admission.
pub fn build_c23_operand_probe_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    if profile != current_profile() {
        return Err(C23OperandProbeSourceError::UnsupportedProfile);
    }
    let mut source = (0..SOURCE_CELLS)
        .map(|position| graphical(position, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (position, opcode) in [
        (8, b'j'),
        (164, profile.input_instruction()),
        (165, b'p'),
        (166, b'p'),
        (167, profile.output_instruction()),
        (168, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    source
        .get_mut(277..279)
        .ok_or(C23OperandProbeSourceError::InvalidPosition { position: 277 })?
        .copy_from_slice(b"Iy");
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Compose five actual rotations of the correct Iy seed with signed I/O.
///
/// The checked loader initializes M95=7,174,404 and M96=121. Five real
/// `*` instructions reach M95=4,281,052; the mandatory C37 `/` reads a
/// genuine input byte or EOF. Five data-pointer `j` operations then return
/// to M95 through the *encrypted* M37=66, M67=67 and M68=94 chain.
/// Two physical `p` instructions consume both prepared loader operands,
/// followed by a real output and halt. All successful bytes echo exactly,
/// but target EOF emits 0x0f rather than C23 0xff. Four further rotations
/// and input-preserving linkage remain open; this is not a C artifact.
///
/// # Errors
///
/// Refuses noncanonical profiles, a rejected rotation precursor or an
/// unavailable position-sensitive graphical opcode. Normative execution
/// is still required to establish actual instruction effects.
pub fn build_c23_five_rotated_signed_crazy_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    if profile != current_profile() {
        return Err(C23OperandProbeSourceError::UnsupportedProfile);
    }
    let mut source = build_c23_seed_rotated_input_echo_source(profile)
        .map_err(|error| C23OperandProbeSourceError::RotationPreparation {
            error,
        })?;
    // The source-locked input at C37 encrypts M37 from 80 into 66.
    // M67 and M68 are not reached code in this 48-step experiment.
    *source.get_mut(67).ok_or(
        C23OperandProbeSourceError::InvalidPosition { position: 67 },
    )? = 67;
    *source.get_mut(68).ok_or(
        C23OperandProbeSourceError::InvalidPosition { position: 68 },
    )? = 94;
    set(&mut source, 38, b'o')?;
    for position in 39..=43 {
        set(&mut source, position, b'j')?;
    }
    for (position, opcode) in [
        (44, b'p'),
        (45, b'p'),
        (46, profile.output_instruction()),
        (47, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Observe a second signed input after nine physical Iy rotations.
///
/// The `Iy` seed undergoes nine actual M95 rotations and the source's
/// mandatory first `/` at C37. After the last `*`, C66/C67 follow M96
/// and M122; the source-locked M68=94 then executes as a no-op at C68,
/// where self-encryption changes it into 57. C69 advances D to M160,
/// and C70..C72 reset D via M158 and the encrypted M37. C73 reads the
/// *second* input. C74 `j` follows the now-encrypted M68=57 to M58,
/// not the originally intended M95. Two genuine `p` writes therefore
/// consume M58=104 and M59=104, before `<` and `v` at C77/C78.
/// This source is a **negative C23 conversion probe**: it never links
/// mutable C state and cannot implement ordinary single-read getchar.
///
/// # Errors
///
/// Refuses noncanonical profiles, malformed loader preparation or an
/// unavailable graphical opcode. Normative guest execution remains the
/// independent evidence for all physical effects.
pub fn build_c23_nine_rotated_second_input_crazy_probe_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    if profile != current_profile() {
        return Err(C23OperandProbeSourceError::UnsupportedProfile);
    }
    let mut source = build_c23_seed_nine_rotated_operand_source(profile)
        .map_err(|error| C23OperandProbeSourceError::RotationPreparation {
            error,
        })?;
    for (position, opcode) in [
        (66, b'j'),
        (69, b'o'),
        (70, b'j'),
        (71, b'j'),
        (72, b'j'),
        (73, profile.input_instruction()),
        (74, b'j'),
        (75, b'p'),
        (76, b'p'),
        (77, profile.output_instruction()),
        (78, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Execute the complete signed C23 two-crazy conversion **without output**.
///
/// Nine real `*` instructions prepare M95=7,138,732 from the `Iy` seed.
/// The mandatory earlier input at C37 is discarded by later rotations.
/// A second physical `/` at C69 reads the value to convert. After two
/// reset jumps and a five-jump source/encryption-aware pointer chain,
/// C79 and C80 execute `p` against M95 and M96=121 respectively.
/// Source-required M81=94 decodes as `v` and halts at C81 before `<` can
/// emit the converted result. This is guest arithmetic, **not** C I/O
/// lowering or the P2 checksum; relocating the output remains necessary.
///
/// # Errors
///
/// Refuses unsupported profiles and invalid source encoding. Normative
/// VM execution must verify input provenance and both actual writes.
pub fn build_c23_nine_rotated_signed_conversion_without_output_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    if profile != current_profile() {
        return Err(C23OperandProbeSourceError::UnsupportedProfile);
    }
    let mut source = build_c23_seed_nine_rotated_operand_source(profile)
        .map_err(|error| C23OperandProbeSourceError::RotationPreparation {
            error,
        })?;
    for (position, opcode) in [
        (66, b'j'),
        (69, profile.input_instruction()),
        (70, b'j'),
        (71, b'j'),
        (72, b'j'),
        (73, b'j'),
        (74, b'o'),
        (75, b'j'),
        (76, b'j'),
        (77, b'j'),
        (78, b'j'),
        (79, b'p'),
        (80, b'p'),
        // This unexecuted source/data cell supplies the C75 j operand.
        (87, b'p'),
    ] {
        set(&mut source, position, opcode)?;
    }
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Preserve a live signed input across a physical output and C23 conversion.
///
/// The second actual guest `/` at C69 reads a signed byte or target EOF.
/// C74 emits its *raw* low byte before C79/C80 perform the two correct
/// C23 `p` conversions against M95/M96. This output does not represent the
/// converted result: at EOF it is the N15 sentinel's low byte, not 0xff.
/// C81 still halts without emitting the final converted accumulator, and the
/// earlier C37 `/` still consumes an input attempt. No C source is compiled.
///
/// This candidate tests whether guest I/O can checkpoint an accumulator
/// without clobbering the subsequent source-authentic conversion path.
/// The exact code/data trace still requires independent normative admission.
///
/// # Errors
///
/// Refuses other profiles, missing source encodings and invalid graphical
/// source. It never publishes a source-C artifact.
pub fn build_c23_nine_rotated_input_checkpoint_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source =
        build_c23_nine_rotated_signed_conversion_without_output_source(
            profile,
        )?;
    // Original C74 is a no-op whose data pointer is M86; changing it to
    // output leaves A and D intact for C75..C80's exact pointer chain.
    set(&mut source, 74, profile.output_instruction())?;
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Bypass the frozen C81 pointer/halt cell using a real indirect guest jump.
///
/// The nine Iy rotations and C37/C69 signed input attempts remain unchanged.
/// After C78 resets D to M80, the C79 `i` reads M80=82 and enters C83,
/// encrypting *M82* rather than C79 before the following `o` executes.
/// C84 then halts cleanly without reading again, output or C23 conversion.
/// This is a physical code-pointer relocation probe, not a C translator.
///
/// # Errors
///
/// Refuses unsupported profiles and loader-invalid source cells. VM replay
/// is still required to establish the indirect self-encryption transition.
pub fn build_c23_nine_rotated_indirect_halt_probe_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source =
        build_c23_nine_rotated_signed_conversion_without_output_source(
            profile,
        )?;
    for (position, opcode) in [
        (74, b'o'),
        (75, b'j'),
        (76, b'j'),
        (77, b'o'),
        (78, b'j'),
        (79, b'i'),
        (83, b'o'),
        (84, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    // C78 j reads M83=79, and C79 i reads M80=82. The latter
    // intentionally encrypts M82=80 to 66, a state change any later
    // data-pointer routing must account for.
    *source.get_mut(80).ok_or(
        C23OperandProbeSourceError::InvalidPosition { position: 80 },
    )? = 82;
    *source.get_mut(82).ok_or(
        C23OperandProbeSourceError::InvalidPosition { position: 82 },
    )? = 80;
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Execute an input-dependent guest crazy write *after* the C81 bypass.
///
/// The source preserves all nine rotations and both signed guest input
/// attempts. C79 indirectly enters C83, encrypting the skipped M82 from
/// 80 to 66. C84 follows that encrypted word to D=67; C85 applies `p`
/// to the earlier encrypted M67=85, and C86 emits the result's low byte.
/// C87 is source-fixed to `p` by the earlier M87=69 pointer read, so its
/// separate write occurs *after* output. C88 then halts in 86 VM steps.
///
/// This demonstrates a real live-input arithmetic/output continuation
/// across an indirect code transfer. The operands are **85 and 123**,
/// not the C23 signed converter's 7,138,732 and 121, and the EOF byte
/// is not C23 `0xff`. It is not source-C compilation or a checksum.
///
/// # Errors
///
/// Rejects unsupported profiles or absent graphical source opcodes. The
/// normative VM must still verify the real output and write sequence.
pub fn build_c23_nine_rotated_indirect_crazy_output_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source =
        build_c23_nine_rotated_indirect_halt_probe_source(profile)?;
    for (position, opcode) in [
        (84, b'j'),
        (85, b'p'),
        (86, profile.output_instruction()),
        (88, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    // M87 must remain 69: C75 reads it to reach the subsequent C79 `i`.
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}
