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
//   - Fail-closed semantic realization of pure byte-stream runtime helpers.
// - Must-Not:
//   - Execute guest values on the host, choose control-flow layout, or perform
//     I/O.
// - Allows:
//   - Inputs: exact helper requests and canonical target-profile I/O
//     projection.
//   - Outputs: declarative pre-layout helper operations.
//   - Side effects: none.
// - Split-When:
//   - Another helper family requires independent semantic policy.
// - Merge-When:
//   - Another application module owns these exact helper recipes.
// - Summary:
//   - Binds byte-stream helpers to explicit profile-aware target semantics.
// - Description:
//   - EOF is copied from profile authority; byte/status constants are
//     ABI/runtime semantics.
// - Usage:
//   - Called before direct helper-call integration and target control-flow
//     layout.
// - Defaults:
//   - Only current reviewed helper/profile identities are admitted.
//

//! Pure guest-runtime byte-stream helper semantic lowering.

use super::model::{InputWordDecodeSemantics, RuntimeHelperOperation};
use super::runtime_helper_input::RuntimeHelperRequest;
use super::target_profile_input::TargetProfileIo;

const DECODE_INPUT_ID: &str = "malbolge_guest_decode_input_word";
const OUTPUT_BYTE_ID: &str = "malbolge_guest_output_byte";
const TARGET_PROFILE: &str = "malbolge-2026";

/// Stable failures for pure runtime-helper semantic lowering.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RuntimeHelperLoweringError {
    /// Helper declaration identity is outside this lowering slice.
    UnsupportedIdentity,
    /// Request/profile identity is not the reviewed current target.
    UnsupportedProfile,
}

/// Lowers one exact pure runtime helper to a declarative target semantic
/// recipe.
///
/// # Errors
///
/// Returns [`RuntimeHelperLoweringError`] when helper or profile identity
/// drifts.
pub fn lower_runtime_helper(
    request: &RuntimeHelperRequest,
    profile: &TargetProfileIo,
) -> Result<RuntimeHelperOperation, RuntimeHelperLoweringError> {
    if request.target_profile != TARGET_PROFILE
        || profile.profile_id != TARGET_PROFILE
        || request.target_profile != profile.profile_id
        || profile.eof_word <= 255
    {
        return Err(RuntimeHelperLoweringError::UnsupportedProfile);
    }
    match request.identity.as_str() {
        DECODE_INPUT_ID => Ok(RuntimeHelperOperation::DecodeInputWord(
            Box::new(InputWordDecodeSemantics {
                byte_max: 255,
                eof_value_bits: u32::MAX,
                eof_word: profile.eof_word,
                invalid_input_status: 4,
                valid_status: 0,
            }),
        )),
        OUTPUT_BYTE_ID => Ok(RuntimeHelperOperation::OutputByte { mask: 255 }),
        _ => Err(RuntimeHelperLoweringError::UnsupportedIdentity),
    }
}
