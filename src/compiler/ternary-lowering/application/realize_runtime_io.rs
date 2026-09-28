// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Profile-bound machine realization of admitted raw byte-I/O intrinsics.
// - Must-Not:
//   - Hardcode profile opcode characters, decode C EOF, choose layout, or emit
//     encoded Malbolge cells.
// - Allows:
//   - Inputs: admitted runtime intrinsic semantics and target-profile I/O view.
//   - Outputs: decoded machine-I/O operations bound to exact profile semantics.
//   - Side effects: none.
// - Split-When:
//   - Another machine-effect family requires independent profile realization.
// - Merge-When:
//   - Another application module owns this exact profile-bound I/O step.
// - Summary:
//   - Derives input/output machine operations from profile authority.
// - Description:
//   - Carries raw EOF only on input and never substitutes host I/O behavior.
// - Usage:
//   - Called after runtime intrinsic identity admission and profile projection.
// - Defaults:
//   - Only canonical current-profile identity and distinct opcodes are
//     accepted.
//

//! Profile-bound realization of raw byte-I/O runtime semantics.

use super::model::{
    MachineIoKind, MachineIoOperation, RuntimeIntrinsicOperation,
};
use super::target_profile_input::TargetProfileIo;

const TARGET_PROFILE: &str = "malbolge-2026";

/// Stable failures for target-profile I/O realization.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RuntimeIoRealizationError {
    /// Projected I/O semantics are internally contradictory.
    InvalidProjection,
    /// Target profile is not the reviewed current language profile.
    UnsupportedProfile,
}

/// Realizes one raw runtime intrinsic semantic operation under a target
/// profile.
///
/// # Errors
///
/// Returns [`RuntimeIoRealizationError`] when profile identity or projected I/O
/// semantics are not valid for current-profile realization.
pub fn realize_runtime_io(
    operation: RuntimeIntrinsicOperation,
    profile: &TargetProfileIo,
) -> Result<MachineIoOperation, RuntimeIoRealizationError> {
    if profile.profile_id != TARGET_PROFILE {
        return Err(RuntimeIoRealizationError::UnsupportedProfile);
    }
    if profile.input_instruction == profile.output_instruction {
        return Err(RuntimeIoRealizationError::InvalidProjection);
    }
    match operation {
        RuntimeIntrinsicOperation::InputWord => Ok(MachineIoOperation {
            eof_word: Some(profile.eof_word),
            instruction: profile.input_instruction,
            kind: MachineIoKind::InputWord,
        }),
        RuntimeIntrinsicOperation::OutputByte => Ok(MachineIoOperation {
            eof_word: None,
            instruction: profile.output_instruction,
            kind: MachineIoKind::OutputByte,
        }),
    }
}
