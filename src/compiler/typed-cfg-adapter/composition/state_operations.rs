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
//   - Source-authenticated per-block operand-to-frame-cell binding.
// - Must-Not:
//   - Evaluate C expressions, choose guest branches or emit executable code.
// - Allows:
//   - Inputs: canonical typed SSA and its validated guest state frame.
//   - Outputs: ordered instructions, their exact cell slots and control uses.
//   - Side effects: none.
// - Split-When:
//   - The linker realizes guest instructions and relocates control edges.
// - Merge-When:
//   - A general verified backend consumes these bindings directly.
// - Summary:
//   - Every scalar input and destination has a disjoint frame-relative slot.
// - Description:
//   - In particular, signed getchar retains both C32 cells through control.
// - Usage:
//   - Prepared only from the independently decoded canonical typed module.
// - Defaults:
//   - No guest instructions or writable guest memory are produced.
//
//! Ordered, frame-relative runtime operands; not guest execution or layout.

use std::collections::BTreeMap;

use super::TypedCfgAdapterError;
use super::state_storage::{
    CURRENT_WORD_COUNT, GuestStateFrame, GuestStorageValue, bindable_slots,
    encode_i32_cells,
};
use super::ternary::TernaryCfgScalarKind;
use super::typed::{
    Function, Instruction, Module, SourceSpan, Terminator, ValueId,
};

/// One exact literal target cell in a future guest constant write sequence.
/// This is a required guest action, not initialized memory or host execution.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct GuestConstantCell {
    /// Frame-relative destination word offset.
    pub destination: u32,
    /// Exact target-profile word to materialize through real guest code.
    pub word: u32,
}

/// One ordered typed SSA instruction with its exact runtime cell operands.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestOperationBinding {
    /// Exact target cells required for literal materialization; empty for
    /// nonconstant instructions. The linker must implement these writes.
    pub constant_cells: Vec<GuestConstantCell>,
    /// Original admitted typed instruction, without host evaluation.
    pub instruction: Instruction,
    /// Source operands in canonical instruction order (never precomputed).
    pub reads: Vec<GuestStorageValue>,
    /// Exact original source coordinates.
    pub span: SourceSpan,
    /// Result location, absent for effects such as `putchar`.
    pub write: Option<GuestStorageValue>,
}

/// Frame-relative dynamic CFG terminator inputs, with symbolic targets.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestControlBinding {
    /// Boolean condition slot for branches; no host path selection.
    pub condition: Option<GuestStorageValue>,
    /// SSA return value slot, if the function returns a scalar.
    pub return_value: Option<GuestStorageValue>,
    /// Original jump, branch or return, including source block IDs.
    pub terminator: Terminator,
}

/// One canonical block's ordered operations and final control uses.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestOperationBlock {
    /// Source block identity.
    pub block: u32,
    /// Terminator with its actual frame-relative condition or return slot.
    pub control: GuestControlBinding,
    /// Source function identity.
    pub function: u32,
    /// Ordered, bound operations; all are runtime work for a future linker.
    pub instructions: Vec<GuestOperationBinding>,
}

type Slots<'frame> = BTreeMap<u32, &'frame GuestStorageValue>;
type OperandValues = (Vec<ValueId>, Option<ValueId>);

fn cell(
    slots: &Slots<'_>,
    value: ValueId,
) -> Result<GuestStorageValue, TypedCfgAdapterError> {
    slots
        .get(&value.value())
        .copied()
        .copied()
        .ok_or(TypedCfgAdapterError::GuestStateAllocation)
}

fn literal_cells(
    instruction: &Instruction,
    destination: Option<GuestStorageValue>,
) -> Result<Vec<GuestConstantCell>, TypedCfgAdapterError> {
    let Instruction::ConstantInteger { constant, .. } = instruction else {
        return Ok(Vec::new());
    };
    let slot = destination.ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
    let bytes = constant.little_endian();
    let words = match (slot.type_kind, constant.bit_width(), bytes) {
        (TernaryCfgScalarKind::Bool, 1, [value @ 0..=1])
        | (TernaryCfgScalarKind::I8 | TernaryCfgScalarKind::U8, 8, [value]) => {
            vec![u32::from(*value)]
        },
        (
            TernaryCfgScalarKind::I16 | TernaryCfgScalarKind::U16,
            16,
            [low, high],
        ) => vec![u32::from(u16::from_le_bytes([*low, *high]))],
        (
            TernaryCfgScalarKind::I32 | TernaryCfgScalarKind::U32,
            32,
            [byte_zero, byte_one, byte_two, byte_three],
        ) => encode_i32_cells(u32::from_le_bytes([
            *byte_zero,
            *byte_one,
            *byte_two,
            *byte_three,
        ]))
        .to_vec(),
        _ => return Err(TypedCfgAdapterError::GuestStateAllocation),
    };
    if words.len() != usize::try_from(slot.words).unwrap_or_default()
        || words.iter().any(|word| *word >= CURRENT_WORD_COUNT)
    {
        return Err(TypedCfgAdapterError::GuestStateAllocation);
    }
    words
        .into_iter()
        .enumerate()
        .map(|(i, word)| {
            Ok(GuestConstantCell {
                destination: u32::try_from(i)
                    .ok()
                    .and_then(|word_offset| {
                        slot.offset.checked_add(word_offset)
                    })
                    .ok_or(TypedCfgAdapterError::GuestStateAllocation)?,
                word,
            })
        })
        .collect()
}

fn operand_values(
    instruction: &Instruction,
) -> Result<OperandValues, TypedCfgAdapterError> {
    match instruction {
        Instruction::Binary { left, result, right, .. }
        | Instruction::Compare { left, result, right, .. } => {
            Ok((vec![*left, *right], Some(*result)))
        },
        Instruction::Cast { result, value, .. } => {
            Ok((vec![*value], Some(*result)))
        },
        Instruction::ConstantInteger { result, .. }
        | Instruction::ByteInput { result, .. }
        | Instruction::Getchar { result, .. } => {
            Ok((Vec::new(), Some(*result)))
        },
        Instruction::ByteOutput { value } => Ok((vec![*value], None)),
        Instruction::AddressOffset { .. }
        | Instruction::AutomaticAllocate { .. }
        | Instruction::Call { .. }
        | Instruction::FunctionAddress { .. }
        | Instruction::Load { .. }
        | Instruction::Store { .. } => {
            Err(TypedCfgAdapterError::UnsupportedTypedIr)
        },
    }
}

fn validate_operation_operands(
    instruction: &Instruction,
    reads: &[GuestStorageValue],
    write: Option<GuestStorageValue>,
) -> Result<(), TypedCfgAdapterError> {
    let valid = match instruction {
        Instruction::Getchar { .. } => write.is_some_and(|slot| {
            slot.type_kind == TernaryCfgScalarKind::I32 && slot.words == 2
        }),
        Instruction::ByteInput { .. } => write.is_some_and(|slot| {
            slot.type_kind == TernaryCfgScalarKind::U8 && slot.words == 1
        }),
        Instruction::ByteOutput { .. } => matches!(reads, [slot]
            if slot.type_kind == TernaryCfgScalarKind::U8 && slot.words == 1),
        Instruction::Binary { .. } => {
            reads.len() == 2
                && write.is_some_and(|output| {
                    reads
                        .iter()
                        .all(|input| input.type_kind == output.type_kind)
                })
        },
        Instruction::Compare { .. } => {
            reads.len() == 2
                && write.is_some_and(|slot| {
                    slot.type_kind == TernaryCfgScalarKind::Bool
                })
                && reads.first().map(|slot| slot.type_kind)
                    == reads.get(1).map(|slot| slot.type_kind)
        },
        Instruction::Cast { .. } | Instruction::ConstantInteger { .. } => true,
        Instruction::AddressOffset { .. }
        | Instruction::AutomaticAllocate { .. }
        | Instruction::Call { .. }
        | Instruction::FunctionAddress { .. }
        | Instruction::Load { .. }
        | Instruction::Store { .. } => false,
    };
    if !valid {
        return Err(TypedCfgAdapterError::GuestStateAllocation);
    }
    Ok(())
}

fn bind_instruction(
    instruction: &Instruction,
    span: SourceSpan,
    slots: &Slots<'_>,
) -> Result<GuestOperationBinding, TypedCfgAdapterError> {
    let (read_values, write_value) = operand_values(instruction)?;
    let reads = read_values
        .into_iter()
        .map(|value| cell(slots, value))
        .collect::<Result<Vec<_>, _>>()?;
    let write = write_value.map(|value| cell(slots, value)).transpose()?;
    validate_operation_operands(instruction, &reads, write)?;
    Ok(GuestOperationBinding {
        constant_cells: literal_cells(instruction, write)?,
        instruction: instruction.clone(),
        reads,
        span,
        write,
    })
}

/// Bind every typed operation and control use to the source-authenticated
/// frame.
///
/// # Errors
///
/// Refuses altered frame slots, missing SSA values, wrong scalar categories,
/// unsupported instructions and malformed control operands. Produces no guest
/// code and does not evaluate branches or arithmetic on the host.
pub fn bind_function_operations(
    module: &Module,
    function: &Function,
    frame: &GuestStateFrame,
) -> Result<Vec<GuestOperationBlock>, TypedCfgAdapterError> {
    let slots = bindable_slots(module, function, frame)?;
    let mut blocks = Vec::with_capacity(function.blocks().len());
    for block in function.blocks() {
        let instructions = block
            .instructions()
            .iter()
            .map(|located| {
                bind_instruction(located.instruction(), located.span(), &slots)
            })
            .collect::<Result<Vec<_>, _>>()?;
        let (condition, return_value) = match block.terminator() {
            Terminator::Branch { condition, .. } => {
                (Some(cell(&slots, *condition)?), None)
            },
            Terminator::Jump { .. } => (None, None),
            Terminator::Return { value } => {
                (None, value.map(|id| cell(&slots, id)).transpose()?)
            },
            Terminator::Switch { .. } => {
                return Err(TypedCfgAdapterError::UnsupportedTypedIr);
            },
        };
        if condition
            .is_some_and(|slot| slot.type_kind != TernaryCfgScalarKind::Bool)
        {
            return Err(TypedCfgAdapterError::GuestStateAllocation);
        }
        blocks.push(GuestOperationBlock {
            block: block.id().value(),
            control: GuestControlBinding {
                condition,
                return_value,
                terminator: block.terminator().clone(),
            },
            function: function.id().value(),
            instructions,
        });
    }
    Ok(blocks)
}
