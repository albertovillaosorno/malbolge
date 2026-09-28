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
//   - Fail-closed semantic lowering of the canonical frame validator.
// - Must-Not:
//   - Evaluate frame values, assign addresses, or mutate guest memory.
// - Allows:
//   - Inputs: exact frame-helper requests.
//   - Outputs: declarative frame-validation semantics.
//   - Side effects: none.
// - Split-When:
//   - Frame encode/decode gain independently executable lowering policy.
// - Merge-When:
//   - Another application boundary owns this exact validator recipe.
// - Summary:
//   - Binds frame validation identity to exact ABI/runtime constants.
// - Description:
//   - Shape checks mirror the version-one hidden frame contract.
// - Usage:
//   - Called before explicit frame-validator control-flow realization.
// - Defaults:
//   - Only the reviewed version-one frame validator is admitted.
//

//! Semantic lowering for the guest call-frame validator.

use super::frame_helper_input::FrameHelperRequest;
use super::model::{FrameHelperOperation, FrameValidationSemantics};

const ABI_ID: &str = "malbolge-c32-v1";
const FRAME_ALIGNMENT: u32 = 16;
const FRAME_HEADER_BYTES: u32 = 32;
const FRAME_VALIDATE_ID: &str = "malbolge_guest_frame_validate";
const INVALID_ARGUMENT_STATUS: u32 = 1;
const INVALID_FRAME_STATUS: u32 = 5;
const RUNTIME_ID: &str = "malbolge-guest-runtime-v1";
const VALID_STATUS: u32 = 0;

/// Stable failures for frame-helper semantic lowering.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FrameHelperLoweringError {
    /// ABI or runtime contract identity drifted.
    InvalidAuthority,
    /// Helper declaration identity is outside this lowering slice.
    UnsupportedIdentity,
}

/// Lowers the exact version-one frame validator to declarative semantics.
///
/// # Errors
///
/// Returns [`FrameHelperLoweringError`] when ABI/runtime/helper identity
/// drifts.
pub fn lower_frame_helper(
    request: &FrameHelperRequest,
) -> Result<FrameHelperOperation, FrameHelperLoweringError> {
    if request.abi_id != ABI_ID || request.runtime_id != RUNTIME_ID {
        return Err(FrameHelperLoweringError::InvalidAuthority);
    }
    if request.identity != FRAME_VALIDATE_ID {
        return Err(FrameHelperLoweringError::UnsupportedIdentity);
    }
    Ok(FrameHelperOperation::Validate(FrameValidationSemantics {
        alignment: FRAME_ALIGNMENT,
        header_bytes: FRAME_HEADER_BYTES,
        invalid_argument_status: INVALID_ARGUMENT_STATUS,
        invalid_frame_status: INVALID_FRAME_STATUS,
        required_flags: 0,
        valid_status: VALID_STATUS,
    }))
}
