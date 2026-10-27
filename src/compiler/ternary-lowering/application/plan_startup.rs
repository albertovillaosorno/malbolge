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
//   - Fail-closed sequencing of one-shot guest heap binding before user entry.
// - Must-Not:
//   - Choose heap layout, execute runtime code, or weaken ABI pointer
//     semantics.
// - Allows:
//   - Inputs: layout-resolved startup requests from the owned inbound port.
//   - Outputs: ordered startup plans retaining the exact runtime identity.
//   - Side effects: none.
// - Split-When:
//   - Startup gains another independently ordered runtime lifecycle.
// - Merge-When:
//   - Another application module owns this exact startup sequencing policy.
// - Summary:
//   - Proves one heap bind precedes user code in the pre-layout startup plan.
// - Description:
//   - Validates ABI object-pointer alignment and runtime heap extent geometry.
// - Usage:
//   - Called only after a later layout stage resolves the guest heap extent.
// - Defaults:
//   - Current ABI/profile/runtime identities and 16-byte heap geometry are
//     exact.
//

//! One-shot guest heap startup sequencing after layout resolution.

use super::model::{StartupAction, StartupPlan, TernaryProgram};
use super::program_codec::{TernaryProgramValidationError, validate_ternary_program};
use super::startup_input::StartupRequest;

const ABI_ID: &str = "malbolge-c32-v1";
const BIND_ID: &str = "malbolge_guest_runtime_bind_heap";
const HEAP_ALIGNMENT: u32 = 16;
const HEAP_HEADER_BYTES: u32 = 16;
const TARGET_PROFILE: &str = "malbolge-2026";

/// Stable failures for startup-plan admission.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StartupPlanningError {
    /// ABI, runtime symbol, or target-profile identity drifted.
    InvalidIdentity,
    /// Layout supplied an invalid guest heap extent.
    InvalidLayout,
    /// The provided pre-layout program failed independent stage admission.
    InvalidProgram(TernaryProgramValidationError),
    /// The selected entry does not identify a function in the admitted program.
    MissingUserEntry,
}

/// Builds one ordered heap-bind-before-user-entry startup plan.
///
/// # Errors
///
/// Returns [`StartupPlanningError`] when identities or layout geometry do not
/// match the current guest runtime and ABI contracts.
pub fn plan_startup(
    request: &StartupRequest,
) -> Result<StartupPlan, StartupPlanningError> {
    if request.abi_id != ABI_ID
        || request.bind_identity != BIND_ID
        || request.target_profile != TARGET_PROFILE
    {
        return Err(StartupPlanningError::InvalidIdentity);
    }
    validate_heap_layout(request)?;
    Ok(StartupPlan {
        actions: vec![
            StartupAction::BindHeap {
                arena_pointer: request.arena_pointer,
                capacity: request.capacity,
            },
            StartupAction::EnterUserCode {
                function: request.user_entry_function,
            },
        ],
        bind_identity: request.bind_identity.clone(),
    })
}

/// Binds a resolved startup request to one independently admitted target program.
///
/// This does not choose addresses or realize guest runtime calls. It prevents
/// a valid heap extent from authorizing transfer to a non-existent function.
///
/// # Errors
///
/// Rejects malformed startup identity/layout, invalid program state, or an
/// entry function not present in the admitted program.
pub fn plan_startup_for_program(
    request: &StartupRequest,
    program: &TernaryProgram,
) -> Result<StartupPlan, StartupPlanningError> {
    let plan = plan_startup(request)?;
    validate_ternary_program(program).map_err(StartupPlanningError::InvalidProgram)?;
    if !program
        .functions
        .iter()
        .any(|function| function.id == request.user_entry_function)
    {
        return Err(StartupPlanningError::MissingUserEntry);
    }
    Ok(plan)
}

const fn validate_heap_layout(
    request: &StartupRequest,
) -> Result<(), StartupPlanningError> {
    let Some(arena_offset) = request.arena_pointer.checked_sub(1) else {
        return Err(StartupPlanningError::InvalidLayout);
    };
    let minimum_capacity = HEAP_HEADER_BYTES.saturating_add(HEAP_ALIGNMENT);
    if !arena_offset.is_multiple_of(HEAP_ALIGNMENT)
        || request.capacity < minimum_capacity
        || !request.capacity.is_multiple_of(HEAP_ALIGNMENT)
        || arena_offset.checked_add(request.capacity).is_none()
    {
        return Err(StartupPlanningError::InvalidLayout);
    }
    Ok(())
}
