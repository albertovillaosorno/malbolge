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
//   - Ordered semantic plans for public guest getchar/putchar wrappers.
// - Must-Not:
//   - Mark libc available, evaluate guest values, or choose target code layout.
// - Allows:
//   - Inputs: exact wrapper requests and canonical target-profile projection.
//   - Outputs: helper/intrinsic composition with explicit order and return
//     rule.
//   - Side effects: none.
// - Split-When:
//   - Wrapper control flow gains independently executable target
//     representation.
// - Merge-When:
//   - Another application module owns this exact byte-stream composition
//     policy.
// - Summary:
//   - Composes verified helper and raw I/O semantics for getchar and putchar.
// - Description:
//   - Plans preserve source wrapper order without host callback substitution.
// - Usage:
//   - Consumed before executable helper branching and target source sequencing.
// - Defaults:
//   - Canonical libc routines remain unavailable until later executable proof.
//

//! Ordered semantic planning for guest `getchar` and `putchar`.

use super::byte_stream_wrapper_input::ByteStreamWrapperRequest;
use super::lower_runtime_helper::{
    RuntimeHelperLoweringError, lower_runtime_helper,
};
use super::lower_runtime_intrinsic::{
    RuntimeIntrinsicLoweringError, lower_runtime_intrinsic,
};
use super::model::{
    ByteStreamWrapperOrder, ByteStreamWrapperPlan, ByteStreamWrapperReturn,
};
use super::runtime_helper_input::RuntimeHelperRequest;
use super::runtime_intrinsic_input::RuntimeIntrinsicRequest;
use super::target_profile_input::TargetProfileIo;

const GETCHAR_ID: &str = "getchar";
const INPUT_HELPER_ID: &str = "malbolge_guest_decode_input_word";
const INPUT_INTRINSIC_ID: &str = "malbolge_guest_intrinsic_input_word";
const OUTPUT_HELPER_ID: &str = "malbolge_guest_output_byte";
const OUTPUT_INTRINSIC_ID: &str = "malbolge_guest_intrinsic_output_byte";
const PUTCHAR_ID: &str = "putchar";
const TARGET_PROFILE: &str = "malbolge-2026";

#[derive(Clone, Copy)]
enum WrapperKind {
    Getchar,
    Putchar,
}

/// Stable failures for public byte-stream wrapper planning.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ByteStreamWrapperPlanningError {
    /// Helper/profile projection is inconsistent with reviewed semantics.
    InvalidProfileProjection,
    /// Public wrapper identity is outside this planning slice.
    UnsupportedIdentity,
    /// Wrapper request is not for the reviewed current target profile.
    UnsupportedProfile,
}

/// Builds the ordered semantic plan for one public byte-stream wrapper.
///
/// # Errors
///
/// Returns [`ByteStreamWrapperPlanningError`] when wrapper/profile identity or
/// dependent helper/intrinsic semantics fail closed.
pub fn plan_byte_stream_wrapper(
    request: &ByteStreamWrapperRequest,
    profile: &TargetProfileIo,
) -> Result<ByteStreamWrapperPlan, ByteStreamWrapperPlanningError> {
    if request.target_profile != TARGET_PROFILE {
        return Err(ByteStreamWrapperPlanningError::UnsupportedProfile);
    }
    match request.identity.as_str() {
        GETCHAR_ID => build_plan(request, profile, WrapperKind::Getchar),
        PUTCHAR_ID => build_plan(request, profile, WrapperKind::Putchar),
        _ => Err(ByteStreamWrapperPlanningError::UnsupportedIdentity),
    }
}

fn build_plan(
    request: &ByteStreamWrapperRequest,
    profile: &TargetProfileIo,
    kind: WrapperKind,
) -> Result<ByteStreamWrapperPlan, ByteStreamWrapperPlanningError> {
    let (helper_id, intrinsic_id, order, return_kind) = match kind {
        WrapperKind::Getchar => (
            INPUT_HELPER_ID,
            INPUT_INTRINSIC_ID,
            ByteStreamWrapperOrder::IntrinsicThenHelper,
            ByteStreamWrapperReturn::DecodedI32OrEof,
        ),
        WrapperKind::Putchar => (
            OUTPUT_HELPER_ID,
            OUTPUT_INTRINSIC_ID,
            ByteStreamWrapperOrder::HelperThenIntrinsic,
            ByteStreamWrapperReturn::EmittedByteAsI32,
        ),
    };
    let helper = lower_runtime_helper(
        &RuntimeHelperRequest {
            identity: String::from(helper_id),
            target_profile: request.target_profile.clone(),
        },
        profile,
    )
    .map_err(map_helper_error)?;
    let intrinsic = lower_runtime_intrinsic(&RuntimeIntrinsicRequest {
        identity: String::from(intrinsic_id),
        target_profile: request.target_profile.clone(),
    })
    .map_err(map_intrinsic_error)?;
    Ok(ByteStreamWrapperPlan {
        helper,
        identity: request.identity.clone(),
        intrinsic,
        order,
        return_kind,
    })
}

const fn map_helper_error(
    error: RuntimeHelperLoweringError,
) -> ByteStreamWrapperPlanningError {
    match error {
        RuntimeHelperLoweringError::UnsupportedIdentity
        | RuntimeHelperLoweringError::UnsupportedProfile => {
            ByteStreamWrapperPlanningError::InvalidProfileProjection
        },
    }
}

const fn map_intrinsic_error(
    error: RuntimeIntrinsicLoweringError,
) -> ByteStreamWrapperPlanningError {
    match error {
        RuntimeIntrinsicLoweringError::UnsupportedIdentity
        | RuntimeIntrinsicLoweringError::UnsupportedProfile => {
            ByteStreamWrapperPlanningError::InvalidProfileProjection
        },
    }
}
