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
//   - Independent SSA use dominance for bounded dynamic typed CFG projections.
// - Must-Not:
//   - Evaluate guest values, execute C branches, or choose source layout.
// - Allows:
//   - Inputs: bounded reachable CFG, exact predecessor and phi-edge records.
//   - Outputs: deterministic fail-closed def-use dominance admission.
//   - Side effects: owned allocation only.
// - Split-When:
//   - Independent whole-program value liveness requires separate analysis.
// - Merge-When:
//   - A general compiler CFG validator owns this exact incoming projection.
// - Summary:
//   - Rejects wrong-edge phi values and non-dominating branch or ALU operands.
//
//! Structural SSA def-use dominance independent of the target op lowerer.

use std::collections::{BTreeMap, BTreeSet};

use super::input::{
    InputDynamicPhi, InputFunction, InputInstruction, InputTerminator,
};
use super::lower::TernaryLoweringError;

/// SSA definition location: (basic block, position within block).
/// Position 0 means a phi at entry; instructions begin at position 1.
type Definition = (u32, usize);

fn instruction_definition(instruction: &InputInstruction) -> Option<u32> {
    match instruction {
        InputInstruction::BinaryAdd { result, .. }
        | InputInstruction::BinaryAnd { result, .. }
        | InputInstruction::BinaryDivideSigned { result, .. }
        | InputInstruction::BinaryDivideUnsigned { result, .. }
        | InputInstruction::BinaryMultiply { result, .. }
        | InputInstruction::BinaryOr { result, .. }
        | InputInstruction::BinaryRemainderSigned { result, .. }
        | InputInstruction::BinaryRemainderUnsigned { result, .. }
        | InputInstruction::BinaryShiftLeft { result, .. }
        | InputInstruction::BinaryShiftRightArithmetic { result, .. }
        | InputInstruction::BinaryShiftRightLogical { result, .. }
        | InputInstruction::BinarySubtract { result, .. }
        | InputInstruction::BinaryXor { result, .. }
        | InputInstruction::BoolToSigned { result, .. }
        | InputInstruction::ByteInput { result, .. }
        | InputInstruction::CompareEqual { result, .. }
        | InputInstruction::CompareNotEqual { result, .. }
        | InputInstruction::CompareOrdered { result, .. }
        | InputInstruction::ConstantInteger { result, .. }
        | InputInstruction::Getchar { result, .. }
        | InputInstruction::IntegerBitcast { result, .. }
        | InputInstruction::IntegerToBool { result, .. }
        | InputInstruction::SignExtendI8ToI32 { result, .. }
        | InputInstruction::TruncateInteger { result, .. }
        | InputInstruction::ZeroExtendInteger { result, .. } => Some(*result),
        InputInstruction::ByteOutput { .. } | InputInstruction::Unsupported => {
            None
        },
    }
}

fn instruction_uses(instruction: &InputInstruction) -> Vec<u32> {
    match instruction {
        InputInstruction::BinaryAdd { left, right, .. }
        | InputInstruction::BinaryAnd { left, right, .. }
        | InputInstruction::BinaryDivideSigned { left, right, .. }
        | InputInstruction::BinaryDivideUnsigned { left, right, .. }
        | InputInstruction::BinaryMultiply { left, right, .. }
        | InputInstruction::BinaryOr { left, right, .. }
        | InputInstruction::BinaryRemainderSigned { left, right, .. }
        | InputInstruction::BinaryRemainderUnsigned { left, right, .. }
        | InputInstruction::BinaryShiftLeft { left, right, .. }
        | InputInstruction::BinaryShiftRightArithmetic {
            left, right, ..
        }
        | InputInstruction::BinaryShiftRightLogical { left, right, .. }
        | InputInstruction::BinarySubtract { left, right, .. }
        | InputInstruction::BinaryXor { left, right, .. }
        | InputInstruction::CompareEqual { left, right, .. }
        | InputInstruction::CompareNotEqual { left, right, .. }
        | InputInstruction::CompareOrdered { left, right, .. } => {
            vec![*left, *right]
        },
        InputInstruction::BoolToSigned { value, .. }
        | InputInstruction::ByteOutput { value, .. }
        | InputInstruction::IntegerBitcast { value, .. }
        | InputInstruction::IntegerToBool { value, .. }
        | InputInstruction::SignExtendI8ToI32 { value, .. }
        | InputInstruction::TruncateInteger { value, .. }
        | InputInstruction::ZeroExtendInteger { value, .. } => vec![*value],
        InputInstruction::ByteInput { .. }
        | InputInstruction::Getchar { .. }
        | InputInstruction::ConstantInteger { .. }
        | InputInstruction::Unsupported => Vec::new(),
    }
}

fn dominators(predecessors: &[BTreeSet<u32>]) -> Vec<BTreeSet<u32>> {
    let all = (0..predecessors.len())
        .filter_map(|index| u32::try_from(index).ok())
        .collect::<BTreeSet<_>>();
    let mut sets = vec![all; predecessors.len()];
    sets[0] = BTreeSet::from([0]);
    loop {
        let mut changed = false;
        for (block, incoming) in predecessors.iter().enumerate().skip(1) {
            let mut intersection = incoming
                .iter()
                .map(|predecessor| &sets[*predecessor as usize]);
            let mut members = intersection.next().cloned().unwrap_or_default();
            for other in intersection {
                members.retain(|candidate| other.contains(candidate));
            }
            _ = members.insert(u32::try_from(block).unwrap_or(u32::MAX));
            if sets[block] != members {
                sets[block] = members;
                changed = true;
            }
        }
        if !changed {
            return sets;
        }
    }
}

fn check_use(
    definitions: &BTreeMap<u32, Definition>,
    dominators: &[BTreeSet<u32>],
    value: u32,
    block: u32,
    position: usize,
) -> Result<(), TernaryLoweringError> {
    let &(defined_in, defined_at) = definitions
        .get(&value)
        .ok_or(TernaryLoweringError::InvalidProjection)?;
    if (defined_in == block && defined_at < position)
        || (defined_in != block
            && dominators[block as usize].contains(&defined_in))
    {
        Ok(())
    } else {
        Err(TernaryLoweringError::InvalidProjection)
    }
}

/// Validate SSA definitions, per-block ordering, phi incoming edge availability
/// and guest-dependent Boolean branch uses before emitting symbolic target IR.
///
/// # Errors
///
/// Rejects duplicate or nonexistent definitions and any operand whose SSA
/// definition does not dominate its use or exact incoming predecessor edge.
pub(super) fn validate_dynamic_cfg_ssa(
    function: &InputFunction,
    predecessors: &[BTreeSet<u32>],
    bindings: &BTreeMap<(u32, u32), &[InputDynamicPhi]>,
) -> Result<(), TernaryLoweringError> {
    let mut definitions = BTreeMap::<u32, Definition>::new();
    for block in &function.blocks {
        let phis = bindings
            .get(&(function.id, block.id))
            .copied()
            .unwrap_or(&[]);
        for phi in phis {
            if definitions.insert(phi.result, (block.id, 0)).is_some() {
                return Err(TernaryLoweringError::InvalidProjection);
            }
        }
        for (index, instruction) in block.instructions.iter().enumerate() {
            if let Some(result) = instruction_definition(instruction)
                && definitions.insert(result, (block.id, index + 1)).is_some()
            {
                return Err(TernaryLoweringError::InvalidProjection);
            }
        }
    }
    let dominators = dominators(predecessors);
    for block in &function.blocks {
        for (index, instruction) in block.instructions.iter().enumerate() {
            for operand in instruction_uses(instruction) {
                check_use(
                    &definitions,
                    &dominators,
                    operand,
                    block.id,
                    index + 1,
                )?;
            }
        }
        let terminator_value = match block.terminator {
            InputTerminator::Branch { condition, .. } => Some(condition),
            InputTerminator::Return { value, .. } => value,
            _ => None,
        };
        if let Some(value) = terminator_value {
            check_use(
                &definitions,
                &dominators,
                value,
                block.id,
                block.instructions.len() + 1,
            )?;
        }
        if let Some(phis) = bindings.get(&(function.id, block.id)) {
            for phi in *phis {
                for edge in &phi.incoming {
                    let source = function
                        .blocks
                        .get(usize::try_from(edge.block).map_err(|_error| {
                            TernaryLoweringError::InvalidProjection
                        })?)
                        .ok_or(TernaryLoweringError::InvalidProjection)?;
                    check_use(
                        &definitions,
                        &dominators,
                        edge.value,
                        edge.block,
                        source.instructions.len() + 1,
                    )?;
                }
            }
        }
    }
    Ok(())
}
