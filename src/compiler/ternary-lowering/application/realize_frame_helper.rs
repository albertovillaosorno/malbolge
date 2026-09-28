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
//   - Explicit pre-layout control flow for canonical frame validation.
// - Must-Not:
//   - Evaluate guest frame values, choose branch addresses, or mutate memory.
// - Allows:
//   - Inputs: admitted frame-validator semantics.
//   - Outputs: ordered validator branch/status exits.
//   - Side effects: none.
// - Split-When:
//   - Frame codec memory reads/writes gain a separate execution model.
// - Merge-When:
//   - Semantic frame-helper lowering directly owns exact branch realization.
// - Summary:
//   - Expands frame-validator semantics into explicit target control flow.
// - Description:
//   - Branch order mirrors the checked-in C validator expression order.
// - Usage:
//   - Consumed before target branch layout or helper-call integration.
// - Defaults:
//   - The final unmatched branch returns the canonical valid status.
//

//! Pre-layout control-flow realization for guest call-frame validation.

use super::model::{
    FrameHelperExecutionPlan, FrameHelperOperation, FrameValidationArm,
    FrameValidationCondition,
};

/// Expands one admitted frame helper into explicit pre-layout control flow.
#[must_use]
pub fn realize_frame_helper(
    operation: FrameHelperOperation,
) -> FrameHelperExecutionPlan {
    match operation {
        FrameHelperOperation::Validate(semantics) => {
            FrameHelperExecutionPlan::Validate {
                exits: vec![
                    FrameValidationArm {
                        condition: FrameValidationCondition::FramePointerNull,
                        status: semantics.invalid_argument_status,
                    },
                    FrameValidationArm {
                        condition: FrameValidationCondition::FrameExtentBelow(
                            semantics.header_bytes,
                        ),
                        status: semantics.invalid_frame_status,
                    },
                    FrameValidationArm {
                        condition:
                            FrameValidationCondition::FrameExtentMisaligned(
                                semantics.alignment,
                            ),
                        status: semantics.invalid_frame_status,
                    },
                    FrameValidationArm {
                        condition: FrameValidationCondition::ArgumentBlockNull,
                        status: semantics.invalid_frame_status,
                    },
                    FrameValidationArm {
                        condition: FrameValidationCondition::FlagsNotEqual(
                            semantics.required_flags,
                        ),
                        status: semantics.invalid_frame_status,
                    },
                    FrameValidationArm {
                        condition: FrameValidationCondition::Otherwise,
                        status: semantics.valid_status,
                    },
                ],
            }
        },
    }
}
