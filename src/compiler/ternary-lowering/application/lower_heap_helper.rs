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
//   - Fail-closed semantic lowering of canonical heap initialization.
// - Must-Not:
//   - Choose arena addresses, execute heap writes, or allocate host memory.
// - Allows:
//   - Inputs: exact heap-helper requests.
//   - Outputs: declarative heap initialization semantics.
//   - Side effects: none.
// - Split-When:
//   - Stateful allocation helpers gain independently owned lowering policy.
// - Merge-When:
//   - Another application boundary owns this exact heap-init recipe.
// - Summary:
//   - Binds heap initialization to exact ABI/runtime constants.
// - Description:
//   - Geometry mirrors the version-one heap initialization contract.
// - Usage:
//   - Called before explicit heap-init execution realization.
// - Defaults:
//   - Only the reviewed version-one heap initializer is admitted.
//

//! Semantic lowering for canonical guest heap initialization.

use super::heap_helper_input::HeapHelperRequest;
use super::model::{HeapHelperOperation, HeapInitSemantics};

const ABI_ID: &str = "malbolge-c32-v1";
const HEAP_ALIGNMENT: u32 = 16;
const HEAP_INIT_ID: &str = "malbolge_guest_heap_init";
const INVALID_ARGUMENT_STATUS: u32 = 1;
const MIN_BLOCK_SPAN: u32 = 32;
const RUNTIME_ID: &str = "malbolge-guest-runtime-v1";
const VALID_STATUS: u32 = 0;

/// Stable failures for heap-helper semantic lowering.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum HeapHelperLoweringError {
    /// ABI or runtime contract identity drifted.
    InvalidAuthority,
    /// Helper declaration identity is outside this lowering slice.
    UnsupportedIdentity,
}

/// Lowers the exact version-one heap initializer to declarative semantics.
///
/// # Errors
///
/// Returns [`HeapHelperLoweringError`] when ABI/runtime/helper identity drifts.
pub fn lower_heap_helper(
    request: &HeapHelperRequest,
) -> Result<HeapHelperOperation, HeapHelperLoweringError> {
    if request.abi_id != ABI_ID || request.runtime_id != RUNTIME_ID {
        return Err(HeapHelperLoweringError::InvalidAuthority);
    }
    if request.identity != HEAP_INIT_ID {
        return Err(HeapHelperLoweringError::UnsupportedIdentity);
    }
    Ok(HeapHelperOperation::Initialize(HeapInitSemantics {
        alignment: HEAP_ALIGNMENT,
        invalid_argument_status: INVALID_ARGUMENT_STATUS,
        minimum_capacity: MIN_BLOCK_SPAN,
        valid_status: VALID_STATUS,
    }))
}
