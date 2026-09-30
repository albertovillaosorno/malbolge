// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE-APACHE-2.0
//
// Boundary-Contract:
// - Owns:
//   - Fail-closed admission of exact byte-I/O runtime intrinsic identities.
// - Must-Not:
//   - Decode EOF, implement host I/O, choose layout, or encode machine opcodes.
// - Allows:
//   - Inputs: runtime intrinsic requests from the owned inbound port.
//   - Outputs: explicit pre-layout runtime intrinsic operations.
//   - Side effects: none.
// - Split-When:
//   - Another runtime intrinsic family requires independent policy.
// - Merge-When:
//   - Another application module owns these exact identity checks.
// - Summary:
//   - Preserves raw byte-I/O declaration identities for later target
//     realization.
// - Description:
//   - Keeps raw input-word/EOF semantics distinct from successful typed bytes.
// - Usage:
//   - Called before profile opcode and runtime-helper realization.
// - Defaults:
//   - Only the current reviewed profile and exact declarations are admitted.
//

//! Exact guest-runtime byte-I/O intrinsic identity lowering.

use super::model::RuntimeIntrinsicOperation;
use super::runtime_intrinsic_input::RuntimeIntrinsicRequest;

const INPUT_WORD_ID: &str = "malbolge_guest_intrinsic_input_word";
const OUTPUT_BYTE_ID: &str = "malbolge_guest_intrinsic_output_byte";
const TARGET_PROFILE: &str = "malbolge-2026";

/// Stable failures for raw runtime-intrinsic identity lowering.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RuntimeIntrinsicLoweringError {
    /// Declaration identity is not owned by this lowering slice.
    UnsupportedIdentity,
    /// Target profile is not the reviewed current profile.
    UnsupportedProfile,
}

/// Lowers one exact runtime intrinsic identity to a pre-layout semantic
/// operation.
///
/// # Errors
///
/// Returns [`RuntimeIntrinsicLoweringError`] for any unknown declaration or
/// target-profile identity.
pub fn lower_runtime_intrinsic(
    request: &RuntimeIntrinsicRequest,
) -> Result<RuntimeIntrinsicOperation, RuntimeIntrinsicLoweringError> {
    if request.target_profile != TARGET_PROFILE {
        return Err(RuntimeIntrinsicLoweringError::UnsupportedProfile);
    }
    if request.identity == INPUT_WORD_ID {
        return Ok(RuntimeIntrinsicOperation::InputWord);
    }
    if request.identity == OUTPUT_BYTE_ID {
        return Ok(RuntimeIntrinsicOperation::OutputByte);
    }
    Err(RuntimeIntrinsicLoweringError::UnsupportedIdentity)
}
