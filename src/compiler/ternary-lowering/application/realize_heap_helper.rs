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
//   - Explicit pre-layout execution for canonical heap initialization.
// - Must-Not:
//   - Choose arena addresses, evaluate guest arguments, or allocate host
//     memory.
// - Allows:
//   - Inputs: admitted heap-initialization semantics.
//   - Outputs: ordered guard/state-publication/zeroing steps.
//   - Side effects: none.
// - Split-When:
//   - Another heap helper gains independent state-transition policy.
// - Merge-When:
//   - Semantic heap-helper lowering directly owns exact execution realization.
// - Summary:
//   - Expands heap-init semantics into explicit target-oriented steps.
// - Description:
//   - Guard order and post-guard mutations mirror checked-in guest C.
// - Usage:
//   - Consumed before target memory layout or direct helper-call integration.
// - Defaults:
//   - No state publication occurs before all argument/geometry guards pass.
//

//! Pre-layout execution realization for canonical guest heap initialization.

use super::model::{
    HeapHelperExecutionPlan, HeapHelperOperation, HeapInitStep,
};

/// Expands one admitted heap helper into explicit pre-layout execution.
#[must_use]
pub fn realize_heap_helper(
    operation: HeapHelperOperation,
) -> HeapHelperExecutionPlan {
    match operation {
        HeapHelperOperation::Initialize(semantics) => {
            HeapHelperExecutionPlan::Initialize {
                steps: vec![
                    HeapInitStep::GuardHeapPointerNonNull {
                        failure_status: semantics.invalid_argument_status,
                    },
                    HeapInitStep::GuardArenaPointerNonNull {
                        failure_status: semantics.invalid_argument_status,
                    },
                    HeapInitStep::GuardCapacityAtLeast {
                        minimum: semantics.minimum_capacity,
                        failure_status: semantics.invalid_argument_status,
                    },
                    HeapInitStep::GuardCapacityAligned {
                        alignment: semantics.alignment,
                        failure_status: semantics.invalid_argument_status,
                    },
                    HeapInitStep::GuardArenaPointerAligned {
                        alignment: semantics.alignment,
                        failure_status: semantics.invalid_argument_status,
                    },
                    HeapInitStep::PublishArenaPointer,
                    HeapInitStep::PublishCapacity,
                    HeapInitStep::PublishUsedZero,
                    HeapInitStep::ZeroArenaCapacityBytes,
                    HeapInitStep::ReturnStatus(semantics.valid_status),
                ],
            }
        },
    }
}
