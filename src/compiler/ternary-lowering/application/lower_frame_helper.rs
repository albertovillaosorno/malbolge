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
//   - Fail-closed semantic lowering of canonical frame codec helpers.
// - Must-Not:
//   - Evaluate frame values, assign addresses, or mutate guest memory.
// - Allows:
//   - Inputs: exact frame-helper requests.
//   - Outputs: declarative frame-validation semantics.
//   - Side effects: none.
// - Split-When:
//   - Another frame helper gains independently executable lowering policy.
// - Merge-When:
//   - Another application boundary owns these exact frame-helper recipes.
// - Summary:
//   - Binds frame codec identities to exact ABI/runtime constants.
// - Description:
//   - Validation and wire layout mirror the version-one frame contract.
// - Usage:
//   - Called before explicit frame-helper control-flow realization.
// - Defaults:
//   - Only reviewed version-one validate/encode/decode helpers are admitted.
//

//! Semantic lowering for canonical guest call-frame helpers.

use super::frame_helper_input::FrameHelperRequest;
use super::model::{
    FrameCodecSemantics, FrameField, FrameFieldLayout, FrameHelperOperation,
    FrameValidationSemantics,
};

const ABI_ID: &str = "malbolge-c32-v1";
const FRAME_ALIGNMENT: u32 = 16;
const FRAME_HEADER_BYTES: u32 = 32;
const FRAME_DECODE_ID: &str = "malbolge_guest_frame_decode";
const FRAME_ENCODE_ID: &str = "malbolge_guest_frame_encode";
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

/// Lowers exact version-one frame helpers to declarative semantics.
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
    let validation = frame_validation_semantics();
    match request.identity.as_str() {
        FRAME_DECODE_ID => Ok(FrameHelperOperation::Decode(
            frame_codec_semantics(validation),
        )),
        FRAME_ENCODE_ID => Ok(FrameHelperOperation::Encode(
            frame_codec_semantics(validation),
        )),
        FRAME_VALIDATE_ID => Ok(FrameHelperOperation::Validate(validation)),
        _ => Err(FrameHelperLoweringError::UnsupportedIdentity),
    }
}

const fn frame_codec_semantics(
    validation: FrameValidationSemantics,
) -> FrameCodecSemantics {
    FrameCodecSemantics {
        fields: [
            FrameFieldLayout {
                field: FrameField::PreviousFrame,
                offset: 0,
            },
            FrameFieldLayout {
                field: FrameField::ContinuationId,
                offset: 4,
            },
            FrameFieldLayout {
                field: FrameField::FunctionId,
                offset: 8,
            },
            FrameFieldLayout {
                field: FrameField::FrameExtent,
                offset: 12,
            },
            FrameFieldLayout {
                field: FrameField::ArgumentBlock,
                offset: 16,
            },
            FrameFieldLayout {
                field: FrameField::ResultBlock,
                offset: 20,
            },
            FrameFieldLayout {
                field: FrameField::VariadicBegin,
                offset: 24,
            },
            FrameFieldLayout {
                field: FrameField::Flags,
                offset: 28,
            },
        ],
        header_bytes: FRAME_HEADER_BYTES,
        invalid_argument_status: INVALID_ARGUMENT_STATUS,
        valid_status: VALID_STATUS,
        validation,
    }
}

const fn frame_validation_semantics() -> FrameValidationSemantics {
    FrameValidationSemantics {
        alignment: FRAME_ALIGNMENT,
        header_bytes: FRAME_HEADER_BYTES,
        invalid_argument_status: INVALID_ARGUMENT_STATUS,
        invalid_frame_status: INVALID_FRAME_STATUS,
        required_flags: 0,
        valid_status: VALID_STATUS,
    }
}
