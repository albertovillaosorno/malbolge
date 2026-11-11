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

use super::lower_runtime_helper::lower_runtime_helper;
use super::model::{
    InputDecodeArm, InputDecodeCondition, InputDecodeResult, InputWordDecodeControlFlow,
    RuntimeHelperExecutionPlan, RuntimeHelperOperation,
};
use super::runtime_helper_input::RuntimeHelperRequest;
use super::target_profile_input::TargetProfileIo;

/// Stable failures for independently checked runtime-helper realization.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RuntimeHelperRealizationError {
    /// The supplied helper recipe differs from its canonical identity.
    InvalidPlan,
    /// The selected profile cannot admit the authoritative helper recipe.
    InvalidProfile,
}

/// Expands one runtime-helper recipe into exact pre-layout control flow.
///
/// # Errors
///
/// Rejects fabricated helper semantics or unsupported profile projections
/// before publishing any execution plan.
pub fn realize_runtime_helper(
    operation: &RuntimeHelperOperation,
    profile: &TargetProfileIo,
) -> Result<RuntimeHelperExecutionPlan, RuntimeHelperRealizationError> {
    let identity = match operation {
        RuntimeHelperOperation::DecodeInputWord(_) => "malbolge_guest_decode_input_word",
        RuntimeHelperOperation::OutputByte { .. } => "malbolge_guest_output_byte",
    };
    let expected = lower_runtime_helper(
        &RuntimeHelperRequest {
            identity: String::from(identity),
            target_profile: profile.profile_id.clone(),
        },
        profile,
    )
    .map_err(|_error| RuntimeHelperRealizationError::InvalidProfile)?;
    if *operation != expected {
        return Err(RuntimeHelperRealizationError::InvalidPlan);
    }
    Ok(match operation {
        RuntimeHelperOperation::DecodeInputWord(semantics) => {
            RuntimeHelperExecutionPlan::DecodeInputWord(Box::new(InputWordDecodeControlFlow {
                exits: vec![
                    InputDecodeArm {
                        condition: InputDecodeCondition::ResultPointerNull,
                        result: InputDecodeResult::Unchanged,
                        status: semantics.invalid_argument_status,
                    },
                    InputDecodeArm {
                        condition: InputDecodeCondition::WordAtMost(semantics.byte_max),
                        result: InputDecodeResult::InputWordAsI32,
                        status: semantics.valid_status,
                    },
                    InputDecodeArm {
                        condition: InputDecodeCondition::WordEquals(semantics.eof_word),
                        result: InputDecodeResult::ConstantI32Bits(semantics.eof_value_bits),
                        status: semantics.valid_status,
                    },
                    InputDecodeArm {
                        condition: InputDecodeCondition::Otherwise,
                        result: InputDecodeResult::Unchanged,
                        status: semantics.invalid_input_status,
                    },
                ],
            }))
        }
        RuntimeHelperOperation::OutputByte { mask } => {
            RuntimeHelperExecutionPlan::OutputByte { mask: *mask }
        }
    })
}
