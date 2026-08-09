// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Dense SSA definition inventory and typed definition sites per function.
// - Must-Not:
//   - Decide CFG reachability, instruction semantics, or target register
//     allocation.
// - Allows:
//   - Inputs: explicit function parameters, phis, and value-producing
//     instructions.
//   - Outputs: deterministic value-to-type/definition-site lookup.
//   - Side effects: ordered validation-map allocation only.
// - Split-When:
//   - SSA renaming becomes an independently owned compiler transformation.
// - Merge-When:
//   - CFG admission owns all SSA inventory policy directly.
// - Summary:
//   - Proves single-definition dense SSA identity before use/dominance checks.
// - Description:
//   - Definition sites distinguish parameters, non-entry block phis, and
//     instruction order.
// - Usage:
//   - Shared by instruction, terminator, phi, proof, and dominance validation.
// - Defaults:
//   - Duplicate or sparse value IDs fail closed.
//

//! Typed SSA definition inventory for portable compiler IR.

use std::collections::BTreeMap;

use super::error::ValidationError;
use super::ids::{BlockId, TypeId, ValueId};
use super::instruction::Instruction;
use super::module::Function;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) enum DefinitionSite {
    Instruction { block: BlockId, order: u32 },
    Parameter,
    Phi { block: BlockId },
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct ValueInfo {
    pub(super) site: DefinitionSite,
    pub(super) type_id: TypeId,
}

pub(super) type ValueTable = BTreeMap<ValueId, ValueInfo>;

pub(super) fn collect_values(
    function: &Function,
) -> Result<ValueTable, ValidationError> {
    let mut values = ValueTable::new();
    for parameter in function.parameters() {
        insert_value(
            &mut values,
            parameter.value(),
            parameter.type_id(),
            DefinitionSite::Parameter,
        )?;
    }
    for block in function.blocks() {
        for phi in block.phis() {
            insert_value(
                &mut values,
                phi.result(),
                phi.type_id(),
                DefinitionSite::Phi { block: block.id() },
            )?;
        }
        for (index, instruction) in block.instructions().iter().enumerate() {
            let order = u32::try_from(index)
                .map_err(|_error| ValidationError::ValueIdentity)?;
            if let Some((value, type_id)) =
                instruction_result(instruction.instruction())
            {
                insert_value(
                    &mut values,
                    value,
                    type_id,
                    DefinitionSite::Instruction { block: block.id(), order },
                )?;
            }
        }
    }
    validate_dense_values(&values)?;
    Ok(values)
}

pub(super) const fn instruction_result(
    instruction: &Instruction,
) -> Option<(ValueId, TypeId)> {
    match instruction {
        Instruction::AddressOffset { result, type_id, .. }
        | Instruction::AutomaticAllocate { result, type_id, .. }
        | Instruction::Binary { result, type_id, .. }
        | Instruction::ByteInput { result, type_id }
        | Instruction::Cast { result, type_id, .. }
        | Instruction::Compare { result, type_id, .. }
        | Instruction::ConstantInteger { result, type_id, .. }
        | Instruction::FunctionAddress { result, type_id, .. }
        | Instruction::Load { result, type_id, .. } => {
            Some((*result, *type_id))
        },
        Instruction::Call { result, .. } => *result,
        Instruction::ByteOutput { .. } | Instruction::Store { .. } => None,
    }
}

fn insert_value(
    values: &mut ValueTable,
    value: ValueId,
    type_id: TypeId,
    site: DefinitionSite,
) -> Result<(), ValidationError> {
    if values.insert(value, ValueInfo { site, type_id }).is_some() {
        return Err(ValidationError::DuplicateValue);
    }
    Ok(())
}

fn validate_dense_values(values: &ValueTable) -> Result<(), ValidationError> {
    for (index, value) in values.keys().enumerate() {
        let expected = u32::try_from(index)
            .map_err(|_error| ValidationError::ValueIdentity)?;
        if value.value() != expected {
            return Err(ValidationError::ValueIdentity);
        }
    }
    Ok(())
}
