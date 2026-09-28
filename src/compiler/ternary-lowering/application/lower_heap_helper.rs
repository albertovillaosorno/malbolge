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
//   - Fail-closed semantic lowering of canonical heap helpers.
// - Must-Not:
//   - Choose arena addresses, execute heap writes, or allocate host memory.
// - Allows:
//   - Inputs: exact heap-helper requests.
//   - Outputs: declarative heap initialization/allocation semantics.
//   - Side effects: none.
// - Split-When:
//   - Another stateful heap helper gains independently owned lowering policy.
// - Merge-When:
//   - Another application boundary owns these exact heap-helper recipes.
// - Summary:
//   - Binds heap helper identities to exact ABI/runtime constants.
// - Description:
//   - Geometry and allocator policy mirror the version-one runtime contract.
// - Usage:
//   - Called before explicit heap-helper execution realization.
// - Defaults:
//   - Only reviewed version-one initialization/allocation helpers are admitted.
//

//! Semantic lowering for canonical guest heap helpers.

use super::heap_helper_input::HeapHelperRequest;
use super::model::{
    HeapAllocateSemantics, HeapHelperOperation, HeapInitSemantics,
};

const ALLOCATED_STATE: u32 = 1;
const ABI_ID: &str = "malbolge-c32-v1";
const CORRUPT_STATE_STATUS: u32 = 3;
const HEAP_ALIGNMENT: u32 = 16;
const HEAP_ALLOCATE_ID: &str = "malbolge_guest_heap_allocate";
const HEAP_HEADER_BYTES: u32 = 16;
const HEAP_INIT_ID: &str = "malbolge_guest_heap_init";
const INVALID_ARGUMENT_STATUS: u32 = 1;
const MIN_BLOCK_SPAN: u32 = 32;
const OUT_OF_MEMORY_STATUS: u32 = 2;
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

/// Lowers exact version-one heap helpers to declarative semantics.
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
    match request.identity.as_str() {
        HEAP_ALLOCATE_ID => {
            Ok(HeapHelperOperation::Allocate(HeapAllocateSemantics {
                alignment: HEAP_ALIGNMENT,
                allocated_state: ALLOCATED_STATE,
                corrupt_state_status: CORRUPT_STATE_STATUS,
                header_bytes: HEAP_HEADER_BYTES,
                invalid_argument_status: INVALID_ARGUMENT_STATUS,
                minimum_block_span: MIN_BLOCK_SPAN,
                out_of_memory_status: OUT_OF_MEMORY_STATUS,
                reserved_value: 0,
                valid_status: VALID_STATUS,
            }))
        },
        HEAP_INIT_ID => {
            Ok(HeapHelperOperation::Initialize(HeapInitSemantics {
                alignment: HEAP_ALIGNMENT,
                invalid_argument_status: INVALID_ARGUMENT_STATUS,
                minimum_capacity: MIN_BLOCK_SPAN,
                valid_status: VALID_STATUS,
            }))
        },
        _ => Err(HeapHelperLoweringError::UnsupportedIdentity),
    }
}
