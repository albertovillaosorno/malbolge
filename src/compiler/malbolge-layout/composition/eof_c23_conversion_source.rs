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

//! Physical loader/operand precursor, **not** signed C23 I/O conversion.
//!
//! The `Iy` graphical tail makes loader words M[283]=7,174,404 and
//! M[284]=121. The first word needs nine **actual** rotations before this
//! pair can convert C23 signed getchar to a byte; this source does not
//! perform those rotations. It runs one real input and two genuine `p`
//! writes and emits their deliberately nonconforming low byte. The source
//! must not be published as a lowered C program.

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
    Ok(source)
}
