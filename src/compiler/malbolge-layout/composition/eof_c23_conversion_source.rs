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
