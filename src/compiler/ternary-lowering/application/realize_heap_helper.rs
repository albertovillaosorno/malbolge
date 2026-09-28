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
//   - Explicit pre-layout execution for canonical heap helpers.
// - Must-Not:
//   - Choose arena addresses, evaluate guest arguments, or allocate host
//     memory.
// - Allows:
//   - Inputs: admitted heap initialization/allocation semantics.
//   - Outputs: ordered guards, allocator branches, and publication steps.
//   - Side effects: none.
// - Split-When:
//   - Another heap helper gains independent state-transition policy.
// - Merge-When:
//   - Semantic heap-helper lowering directly owns exact execution realization.
// - Summary:
//   - Expands heap-helper semantics into explicit target-oriented steps.
// - Description:
//   - Guard, first-fit, mutation, and publication order mirror guest C.
// - Usage:
//   - Consumed before target memory layout or direct helper-call integration.
// - Defaults:
//   - Result/state publication follows the checked-in fail-closed ordering.
//

//! Pre-layout execution realization for canonical guest heap helpers.

use super::model::{
    HeapAllocateSemantics, HeapAllocateStep, HeapAllocateZeroedSemantics,
    HeapAllocateZeroedStep, HeapHelperExecutionPlan, HeapHelperOperation,
    HeapInitStep, HeapReleaseSemantics, HeapReleaseStep,
};

/// Expands one admitted heap helper into explicit pre-layout execution.
#[must_use]
pub fn realize_heap_helper(
    operation: HeapHelperOperation,
) -> HeapHelperExecutionPlan {
    match operation {
        HeapHelperOperation::Allocate(semantics) => {
            HeapHelperExecutionPlan::Allocate {
                steps: allocate_steps(semantics),
            }
        },
        HeapHelperOperation::AllocateZeroed(semantics) => {
            HeapHelperExecutionPlan::AllocateZeroed {
                steps: allocate_zeroed_steps(semantics),
            }
        },
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
        HeapHelperOperation::Release(semantics) => {
            HeapHelperExecutionPlan::Release {
                steps: release_steps(semantics),
            }
        },
    }
}

fn allocate_steps(semantics: HeapAllocateSemantics) -> Vec<HeapAllocateStep> {
    let matched = vec![
        HeapAllocateStep::SplitOrClaimFreeBlock {
            allocated_state: semantics.allocated_state,
            minimum_remainder: semantics.minimum_block_span,
            reserved_value: semantics.reserved_value,
        },
        HeapAllocateStep::PublishResultFromBlock {
            header_bytes: semantics.header_bytes,
        },
        HeapAllocateStep::ReturnStatus(semantics.valid_status),
    ];
    vec![
        HeapAllocateStep::GuardResultPointerNonNull {
            failure_status: semantics.invalid_argument_status,
        },
        HeapAllocateStep::GuardHeapShape {
            failure_status: semantics.invalid_argument_status,
        },
        HeapAllocateStep::PublishResultNull,
        HeapAllocateStep::ValidateHeapChain {
            failure_status: semantics.corrupt_state_status,
        },
        HeapAllocateStep::ReturnIfSizeZero {
            status: semantics.valid_status,
        },
        HeapAllocateStep::ComputeRequiredSpan {
            alignment: semantics.alignment,
            header_bytes: semantics.header_bytes,
            overflow_status: semantics.out_of_memory_status,
        },
        HeapAllocateStep::ScanFirstFitFreeBlock {
            free_state: 0,
            on_match: matched,
            read_failure_status: semantics.corrupt_state_status,
        },
        HeapAllocateStep::GuardTailExtentFits {
            failure_status: semantics.out_of_memory_status,
        },
        HeapAllocateStep::WriteAllocatedTailBlock {
            allocated_state: semantics.allocated_state,
            reserved_value: semantics.reserved_value,
        },
        HeapAllocateStep::PublishResultFromTail {
            header_bytes: semantics.header_bytes,
        },
        HeapAllocateStep::PublishTailUsed,
        HeapAllocateStep::ReturnStatus(semantics.valid_status),
    ]
}

fn allocate_zeroed_steps(
    semantics: HeapAllocateZeroedSemantics,
) -> Vec<HeapAllocateZeroedStep> {
    let allocation = HeapHelperExecutionPlan::Allocate {
        steps: allocate_steps(semantics.allocation),
    };
    vec![
        HeapAllocateZeroedStep::GuardResultPointerNonNull {
            failure_status: semantics.invalid_argument_status,
        },
        HeapAllocateZeroedStep::PublishResultNull,
        HeapAllocateZeroedStep::DelegateZeroSizeAllocation(Box::new(
            allocation.clone(),
        )),
        HeapAllocateZeroedStep::GuardProductFitsU32 {
            failure_status: semantics.out_of_memory_status,
        },
        HeapAllocateZeroedStep::AllocateTotalOrReturn(Box::new(allocation)),
        HeapAllocateZeroedStep::ReturnUnlessAllocatedNonNull {
            valid_status: semantics.valid_status,
        },
        HeapAllocateZeroedStep::ZeroAllocatedPayloadBytes,
        HeapAllocateZeroedStep::ReturnStatus(semantics.valid_status),
    ]
}

fn release_steps(semantics: HeapReleaseSemantics) -> Vec<HeapReleaseStep> {
    vec![
        HeapReleaseStep::GuardHeapShape {
            failure_status: semantics.invalid_argument_status,
        },
        HeapReleaseStep::ValidateHeapChain {
            failure_status: semantics.corrupt_state_status,
        },
        HeapReleaseStep::ReturnIfPointerNull {
            status: semantics.valid_status,
        },
        HeapReleaseStep::FindAllocatedBlockOrReturn {
            allocated_state: semantics.allocated_state,
            corrupt_status: semantics.corrupt_state_status,
            header_bytes: semantics.header_bytes,
            invalid_argument_status: semantics.invalid_argument_status,
        },
        HeapReleaseStep::WriteLocatedBlockFree {
            free_state: semantics.free_state,
            zero_metadata_value: semantics.zero_metadata_value,
        },
        HeapReleaseStep::CoalesceFreeBlocksOrReturn {
            corrupt_status: semantics.corrupt_state_status,
            free_state: semantics.free_state,
        },
        HeapReleaseStep::TrimFreeTailOrReturn {
            corrupt_status: semantics.corrupt_state_status,
            free_state: semantics.free_state,
            valid_status: semantics.valid_status,
        },
    ]
}
