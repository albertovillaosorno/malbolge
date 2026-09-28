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
//   - Explicit pre-layout execution plans for admitted pure runtime helpers.
// - Must-Not:
//   - Evaluate guest values on the host, choose branch addresses, or perform
//     I/O.
// - Allows:
//   - Inputs: previously admitted declarative runtime-helper semantics.
//   - Outputs: ordered branch/result/status publication plans.
//   - Side effects: none.
// - Split-When:
//   - Another helper family needs independently owned executable control flow.
// - Merge-When:
//   - Declarative helper lowering directly owns this exact control-flow model.
// - Summary:
//   - Expands pure helper semantics into explicit target control flow.
// - Description:
//   - Input decoding preserves null, byte, EOF, and invalid-word exits exactly.
// - Usage:
//   - Consumed after helper authority admission and before global branch
//     layout.
// - Defaults:
//   - Branch order is semantically significant and preserved in the plan.
//

//! Pre-layout control-flow realization for pure guest-runtime helpers.

use super::model::{
    InputDecodeArm, InputDecodeCondition, InputDecodeResult,
    InputWordDecodeControlFlow, RuntimeHelperExecutionPlan,
    RuntimeHelperOperation,
};

/// Expands one admitted runtime-helper recipe into explicit pre-layout control
/// flow.
#[must_use]
pub fn realize_runtime_helper(
    operation: &RuntimeHelperOperation,
) -> RuntimeHelperExecutionPlan {
    match operation {
        RuntimeHelperOperation::DecodeInputWord(semantics) => {
            RuntimeHelperExecutionPlan::DecodeInputWord(Box::new(
                InputWordDecodeControlFlow {
                    exits: vec![
                        InputDecodeArm {
                            condition: InputDecodeCondition::ResultPointerNull,
                            result: InputDecodeResult::Unchanged,
                            status: semantics.invalid_argument_status,
                        },
                        InputDecodeArm {
                            condition: InputDecodeCondition::WordAtMost(
                                semantics.byte_max,
                            ),
                            result: InputDecodeResult::InputWordAsI32,
                            status: semantics.valid_status,
                        },
                        InputDecodeArm {
                            condition: InputDecodeCondition::WordEquals(
                                semantics.eof_word,
                            ),
                            result: InputDecodeResult::ConstantI32Bits(
                                semantics.eof_value_bits,
                            ),
                            status: semantics.valid_status,
                        },
                        InputDecodeArm {
                            condition: InputDecodeCondition::Otherwise,
                            result: InputDecodeResult::Unchanged,
                            status: semantics.invalid_input_status,
                        },
                    ],
                },
            ))
        },
        RuntimeHelperOperation::OutputByte { mask } => {
            RuntimeHelperExecutionPlan::OutputByte { mask: *mask }
        },
    }
}
