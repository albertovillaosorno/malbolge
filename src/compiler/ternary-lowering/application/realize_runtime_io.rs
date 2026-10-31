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

use super::model::{MachineIoKind, MachineIoOperation, RuntimeIntrinsicOperation};
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

// An all-two-trit word has value 3^n - 1. Check its geometry without
// importing a VM descriptor or treating the supplied profile as authenticated.
const fn is_all_two_trit_word(word: u32) -> bool {
    let Some(mut memory_words) = word.checked_add(1) else {
        return false;
    };
    while memory_words > 1 {
        if !memory_words.is_multiple_of(3) {
            return false;
        }
        memory_words = memory_words.div_euclid(3);
    }
    true
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
    // Successful input bytes occupy 0..=255. The raw profile EOF sentinel
    // must not alias one of them and must be an all-two-trit word. Enforce
    // both even for output-only effects: downstream operations still carry
    // this projection, which is not full profile descriptor authentication.
    if profile.input_instruction == profile.output_instruction
        || u8::try_from(profile.eof_word).is_ok()
        || !is_all_two_trit_word(profile.eof_word)
    {
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
