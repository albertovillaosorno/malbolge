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
//   - Explicit pre-layout execution for canonical frame codec helpers.
// - Must-Not:
//   - Evaluate guest frame values, choose branch addresses, or mutate memory.
// - Allows:
//   - Inputs: admitted frame-validator semantics.
//   - Outputs: ordered validator branch/status exits.
//   - Side effects: none.
// - Split-When:
//   - Another frame-codec phase gains independent target-memory policy.
// - Merge-When:
//   - Semantic frame-helper lowering directly owns exact branch realization.
// - Summary:
//   - Expands frame codec semantics into explicit target-oriented steps.
// - Description:
//   - Validation, field order, and deferred publication mirror checked-in C.
// - Usage:
//   - Consumed before target branch layout or helper-call integration.
// - Defaults:
//   - Frame/wire publication occurs only after validation succeeds.
//

//! Pre-layout execution realization for canonical guest call-frame helpers.

use super::model::{
    FrameCodecExecutionStep, FrameCodecSemantics, FrameHelperExecutionPlan,
    FrameHelperOperation, FrameValidationArm, FrameValidationCondition,
    FrameValidationSemantics,
};

/// Expands one admitted frame helper into explicit pre-layout control flow.
#[must_use]
pub fn realize_frame_helper(
    operation: FrameHelperOperation,
) -> FrameHelperExecutionPlan {
    match operation {
        FrameHelperOperation::Decode(semantics) => {
            FrameHelperExecutionPlan::Decode {
                steps: decode_steps(semantics),
            }
        },
        FrameHelperOperation::Encode(semantics) => {
            FrameHelperExecutionPlan::Encode {
                steps: encode_steps(semantics),
            }
        },
        FrameHelperOperation::Validate(semantics) => validate_plan(semantics),
    }
}

fn decode_steps(
    semantics: FrameCodecSemantics,
) -> Vec<FrameCodecExecutionStep> {
    let mut steps = vec![
        FrameCodecExecutionStep::GuardWirePointerNonNull {
            failure_status: semantics.invalid_argument_status,
        },
        FrameCodecExecutionStep::GuardFramePointerNonNull {
            failure_status: semantics.invalid_argument_status,
        },
        FrameCodecExecutionStep::GuardWireSizeExact {
            bytes: semantics.header_bytes,
            failure_status: semantics.invalid_argument_status,
        },
    ];
    steps.extend(
        semantics
            .fields
            .into_iter()
            .map(FrameCodecExecutionStep::DecodeFieldLittleEndian),
    );
    steps.push(FrameCodecExecutionStep::ValidateFrameOrReturn(Box::new(
        validate_plan(semantics.validation),
    )));
    steps.push(FrameCodecExecutionStep::PublishDecodedFrameAtomically);
    steps.push(FrameCodecExecutionStep::ReturnStatus(
        semantics.valid_status,
    ));
    steps
}

fn encode_steps(
    semantics: FrameCodecSemantics,
) -> Vec<FrameCodecExecutionStep> {
    let mut steps = vec![
        FrameCodecExecutionStep::GuardWirePointerNonNull {
            failure_status: semantics.invalid_argument_status,
        },
        FrameCodecExecutionStep::GuardWireSizeExact {
            bytes: semantics.header_bytes,
            failure_status: semantics.invalid_argument_status,
        },
        FrameCodecExecutionStep::ValidateFrameOrReturn(Box::new(
            validate_plan(semantics.validation),
        )),
    ];
    steps.extend(
        semantics
            .fields
            .into_iter()
            .map(FrameCodecExecutionStep::EncodeFieldLittleEndian),
    );
    steps.push(FrameCodecExecutionStep::PublishEncodedWireAtomically);
    steps.push(FrameCodecExecutionStep::ReturnStatus(
        semantics.valid_status,
    ));
    steps
}

fn validate_plan(
    semantics: FrameValidationSemantics,
) -> FrameHelperExecutionPlan {
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
                condition: FrameValidationCondition::FrameExtentMisaligned(
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
}
