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
//   - Profile-machine realization of the raw I/O step in byte-stream plans.
// - Must-Not:
//   - Execute helper branching, encode source cells, or mark libc available.
// - Allows:
//   - Inputs: validated wrapper plans and canonical target-profile projection.
//   - Outputs: wrapper plans with one profile-bound machine I/O operation.
//   - Side effects: none.
// - Split-When:
//   - Helper control flow gains independently executable target realization.
// - Merge-When:
//   - Wrapper planning directly owns profile-machine realization.
// - Summary:
//   - Binds planned getchar/putchar raw I/O to selected-profile machine
//     opcodes.
// - Description:
//   - Revalidates the complete semantic plan before profile realization.
// - Usage:
//   - Consumed before address-sensitive source-cell encoding and helper layout.
// - Defaults:
//   - Forged plans and malformed profile projections fail closed.
//

//! Profile-machine realization for public guest byte-stream wrapper plans.

use super::byte_stream_wrapper_input::ByteStreamWrapperRequest;
use super::model::{ByteStreamWrapperPlan, MachineByteStreamWrapperPlan};
use super::plan_byte_stream_wrapper::{
    ByteStreamWrapperPlanningError, plan_byte_stream_wrapper,
};
use super::realize_runtime_helper::realize_runtime_helper;
use super::realize_runtime_io::{
    RuntimeIoRealizationError, realize_runtime_io,
};
use super::target_profile_input::TargetProfileIo;

/// Stable failures for wrapper profile-machine realization.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ByteStreamWrapperRealizationError {
    /// Input plan does not match canonical wrapper semantics.
    InvalidPlan,
    /// Target-profile projection cannot realize the planned raw I/O operation.
    InvalidProfile,
}

/// Realizes the raw I/O step in one canonical byte-stream wrapper plan.
///
/// # Errors
///
/// Returns [`ByteStreamWrapperRealizationError`] for forged plans or malformed
/// target-profile projections.
pub fn realize_byte_stream_wrapper(
    plan: &ByteStreamWrapperPlan,
    profile: &TargetProfileIo,
) -> Result<MachineByteStreamWrapperPlan, ByteStreamWrapperRealizationError> {
    let expected = plan_byte_stream_wrapper(
        &ByteStreamWrapperRequest {
            identity: plan.identity.clone(),
            target_profile: profile.profile_id.clone(),
        },
        profile,
    )
    .map_err(map_planning_error)?;
    if expected != *plan {
        return Err(ByteStreamWrapperRealizationError::InvalidPlan);
    }
    let machine_io = realize_runtime_io(plan.intrinsic, profile)
        .map_err(map_runtime_io_error)?;
    Ok(MachineByteStreamWrapperPlan {
        helper: plan.helper.clone(),
        helper_execution: realize_runtime_helper(&plan.helper),
        identity: plan.identity.clone(),
        machine_io,
        order: plan.order,
        return_kind: plan.return_kind,
    })
}

const fn map_planning_error(
    error: ByteStreamWrapperPlanningError,
) -> ByteStreamWrapperRealizationError {
    match error {
        ByteStreamWrapperPlanningError::UnsupportedIdentity => {
            ByteStreamWrapperRealizationError::InvalidPlan
        },
        ByteStreamWrapperPlanningError::InvalidProfileProjection
        | ByteStreamWrapperPlanningError::UnsupportedProfile => {
            ByteStreamWrapperRealizationError::InvalidProfile
        },
    }
}

const fn map_runtime_io_error(
    _error: RuntimeIoRealizationError,
) -> ByteStreamWrapperRealizationError {
    ByteStreamWrapperRealizationError::InvalidProfile
}
