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
//   - Explicit pre-layout execution sequencing for public getchar/putchar.
// - Must-Not:
//   - Assign branch addresses, encode source cells, or mark libc available.
// - Allows:
//   - Inputs: canonical profile-realized wrapper plans and target-profile
//     state.
//   - Outputs: ordered wrapper execution steps with explicit status branching.
//   - Side effects: none.
// - Split-When:
//   - Wrapper source layout becomes independently owned target-linkage policy.
// - Merge-When:
//   - Profile wrapper realization directly owns exact wrapper control flow.
// - Summary:
//   - Makes stdio helper/I/O/return control flow explicit before layout.
// - Description:
//   - Getchar guards helper status; putchar returns the emitted widened byte.
// - Usage:
//   - Consumed after profile I/O realization and before target source layout.
// - Defaults:
//   - Wrapper semantics are re-derived before a supplied machine plan is used.
//

//! Explicit pre-layout control flow for public byte-stream wrappers.

use super::byte_stream_wrapper_input::ByteStreamWrapperRequest;
use super::model::{
    ByteStreamWrapperExecutionPlan, ByteStreamWrapperExecutionStep,
    MachineByteStreamWrapperPlan,
};
use super::plan_byte_stream_wrapper::{
    ByteStreamWrapperPlanningError, plan_byte_stream_wrapper,
};
use super::realize_byte_stream_wrapper::{
    ByteStreamWrapperRealizationError, realize_byte_stream_wrapper,
};
use super::target_profile_input::TargetProfileIo;

const GETCHAR_ID: &str = "getchar";
const PUTCHAR_ID: &str = "putchar";
const EOF_BITS: u32 = u32::MAX;
const VALID_STATUS: u32 = 0;

/// Stable failures for public wrapper control-flow realization.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ByteStreamControlFlowError {
    /// Supplied machine plan does not match canonical wrapper semantics.
    InvalidPlan,
    /// Target-profile projection cannot reproduce the supplied machine plan.
    InvalidProfile,
}

/// Expands one canonical machine wrapper plan into explicit execution steps.
///
/// # Errors
///
/// Returns [`ByteStreamControlFlowError`] when the supplied plan cannot be
/// re-derived exactly from canonical wrapper/profile semantics.
pub fn realize_byte_stream_control_flow(
    plan: &MachineByteStreamWrapperPlan,
    profile: &TargetProfileIo,
) -> Result<ByteStreamWrapperExecutionPlan, ByteStreamControlFlowError> {
    let semantic = plan_byte_stream_wrapper(
        &ByteStreamWrapperRequest {
            identity: plan.identity.clone(),
            target_profile: profile.profile_id.clone(),
        },
        profile,
    )
    .map_err(map_planning_error)?;
    let expected = realize_byte_stream_wrapper(&semantic, profile)
        .map_err(map_realization_error)?;
    if expected != *plan {
        return Err(ByteStreamControlFlowError::InvalidPlan);
    }
    let steps = match plan.identity.as_str() {
        GETCHAR_ID => getchar_steps(plan),
        PUTCHAR_ID => putchar_steps(plan),
        _ => return Err(ByteStreamControlFlowError::InvalidPlan),
    };
    Ok(ByteStreamWrapperExecutionPlan {
        identity: plan.identity.clone(),
        steps,
    })
}

fn getchar_steps(
    plan: &MachineByteStreamWrapperPlan,
) -> Vec<ByteStreamWrapperExecutionStep> {
    vec![
        ByteStreamWrapperExecutionStep::InitializeI32 { bits: EOF_BITS },
        ByteStreamWrapperExecutionStep::MachineIo(plan.machine_io),
        ByteStreamWrapperExecutionStep::RuntimeHelper(Box::new(
            plan.helper_execution.clone(),
        )),
        ByteStreamWrapperExecutionStep::StatusGuard {
            accepted_status: VALID_STATUS,
            failure_return_bits: EOF_BITS,
        },
        ByteStreamWrapperExecutionStep::ReturnDecodedI32,
    ]
}

const fn map_planning_error(
    error: ByteStreamWrapperPlanningError,
) -> ByteStreamControlFlowError {
    match error {
        ByteStreamWrapperPlanningError::UnsupportedIdentity => {
            ByteStreamControlFlowError::InvalidPlan
        },
        ByteStreamWrapperPlanningError::InvalidProfileProjection
        | ByteStreamWrapperPlanningError::UnsupportedProfile => {
            ByteStreamControlFlowError::InvalidProfile
        },
    }
}

const fn map_realization_error(
    error: ByteStreamWrapperRealizationError,
) -> ByteStreamControlFlowError {
    match error {
        ByteStreamWrapperRealizationError::InvalidPlan => {
            ByteStreamControlFlowError::InvalidPlan
        },
        ByteStreamWrapperRealizationError::InvalidProfile => {
            ByteStreamControlFlowError::InvalidProfile
        },
    }
}

fn putchar_steps(
    plan: &MachineByteStreamWrapperPlan,
) -> Vec<ByteStreamWrapperExecutionStep> {
    vec![
        ByteStreamWrapperExecutionStep::RuntimeHelper(Box::new(
            plan.helper_execution.clone(),
        )),
        ByteStreamWrapperExecutionStep::MachineIo(plan.machine_io),
        ByteStreamWrapperExecutionStep::ReturnEmittedByteAsI32,
    ]
}
