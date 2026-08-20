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
//   - Admission of verifier-visible typed-IR proof obligations.
// - Must-Not:
//   - Discharge proofs, optimize checks away, or invent target capabilities.
// - Allows:
//   - Inputs: module proof records plus already validated function SSA tables.
//   - Outputs: deterministic proof-reference/type validity result.
//   - Side effects: none.
// - Split-When:
//   - Proof discharge or theorem evidence becomes a separate compiler artifact.
// - Merge-When:
//   - Module admission owns proof-reference checks directly.
// - Summary:
//   - Ensures every retained proof obligation names valid typed semantics.
// - Description:
//   - Proofs remain obligations; successful admission is not proof discharge.
// - Usage:
//   - Called after all function SSA tables have passed structural validation.
// - Defaults:
//   - Empty capability IDs and invalid value kinds fail closed.
//

//! Validation of retained typed compiler IR proof obligations.

use std::collections::BTreeMap;

use super::error::ValidationError;
use super::ids::{FunctionId, TypeId, ValueId};
use super::instruction::{BinaryOp, Instruction, LocatedInstruction};
use super::module::{Function, Module, ProofObligation};
use super::type_validation::{
    is_integer, is_object_pointer, is_signed_integer, pointee,
};
use super::values::{DefinitionSite, ValueTable};

pub(super) fn validate_proofs(
    module: &Module,
    value_tables: &BTreeMap<FunctionId, ValueTable>,
) -> Result<(), ValidationError> {
    for obligation in module.proof_obligations() {
        validate_proof(module, value_tables, obligation)?;
    }
    Ok(())
}

fn proof_value_type(
    value_tables: &BTreeMap<FunctionId, ValueTable>,
    function: FunctionId,
    value: ValueId,
) -> Result<TypeId, ValidationError> {
    value_tables
        .get(&function)
        .and_then(|values| values.get(&value))
        .map(|info| info.type_id)
        .ok_or(ValidationError::ProofObligation)
}

fn function_by_id(module: &Module, function: FunctionId) -> Option<&Function> {
    module
        .functions()
        .get(usize::try_from(function.value()).ok()?)
}

fn instruction_for_value<'module>(
    module: &'module Module,
    value_tables: &BTreeMap<FunctionId, ValueTable>,
    function: FunctionId,
    value: ValueId,
) -> Option<&'module Instruction> {
    let site = value_tables.get(&function)?.get(&value)?.site;
    let DefinitionSite::Instruction { block, order } = site else {
        return None;
    };
    function_by_id(module, function)?
        .blocks()
        .get(usize::try_from(block.value()).ok()?)?
        .instructions()
        .get(usize::try_from(order).ok()?)
        .map(LocatedInstruction::instruction)
}

const fn overflow_relevant_binary(operation: BinaryOp) -> bool {
    matches!(
        operation,
        BinaryOp::Add
            | BinaryOp::DivideSigned
            | BinaryOp::Multiply
            | BinaryOp::RemainderSigned
            | BinaryOp::ShiftLeft
            | BinaryOp::Subtract
    )
}

fn valid_capability(capability: &str) -> bool {
    !capability.is_empty()
        && capability.bytes().all(|byte| {
            byte.is_ascii_lowercase() || byte.is_ascii_digit() || byte == b'-'
        })
}

fn validate_proof(
    module: &Module,
    value_tables: &BTreeMap<FunctionId, ValueTable>,
    obligation: &ProofObligation,
) -> Result<(), ValidationError> {
    match obligation {
        ProofObligation::Aligned {
            alignment,
            function,
            pointer,
        } => {
            let type_id = proof_value_type(value_tables, *function, *pointer)?;
            if !alignment.is_power_of_two()
                || *alignment > 16
                || !is_object_pointer(module.types(), type_id)
            {
                return Err(ValidationError::ProofObligation);
            }
        },
        ProofObligation::InBounds { bytes, function, pointer } => {
            let type_id = proof_value_type(value_tables, *function, *pointer)?;
            if *bytes == 0 || !is_object_pointer(module.types(), type_id) {
                return Err(ValidationError::ProofObligation);
            }
        },
        ProofObligation::Nonzero { function, value } => {
            let type_id = proof_value_type(value_tables, *function, *value)?;
            if !is_integer(module.types(), type_id)
                && pointee(module.types(), type_id).is_none()
            {
                return Err(ValidationError::ProofObligation);
            }
        },
        ProofObligation::NoSignedOverflow { function, result } => {
            let type_id = proof_value_type(value_tables, *function, *result)?;
            let instruction =
                instruction_for_value(module, value_tables, *function, *result);
            let relevant = matches!(
                instruction,
                Some(Instruction::Binary { operation, .. })
                    if overflow_relevant_binary(*operation)
            );
            if !is_signed_integer(module.types(), type_id) || !relevant {
                return Err(ValidationError::ProofObligation);
            }
        },
        ProofObligation::ProfileCapability { capability } => {
            if !valid_capability(capability) {
                return Err(ValidationError::ProofObligation);
            }
        },
    }
    Ok(())
}
