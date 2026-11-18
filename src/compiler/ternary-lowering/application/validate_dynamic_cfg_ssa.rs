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
type DefinitionTable = BTreeMap<u32, Definition>;
/// Source-authenticated incoming phi bindings keyed by function/block IDs.
pub(super) type PhiBindings<'source> =
    BTreeMap<(u32, u32), &'source [InputDynamicPhi]>;
/// Exact inbound static predecessor sets, validated before SSA admission.
pub(super) type PredecessorSets = Vec<BTreeSet<u32>>;

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

fn predecessor_intersection(
    incoming: &BTreeSet<u32>,
    dominators: &[BTreeSet<u32>],
) -> Result<BTreeSet<u32>, TernaryLoweringError> {
    let mut remaining = incoming.iter();
    let first = remaining
        .next()
        .ok_or(TernaryLoweringError::InvalidProjection)?;
    let first_index = usize::try_from(*first)
        .map_err(|_error| TernaryLoweringError::InvalidProjection)?;
    let mut intersection = dominators
        .get(first_index)
        .ok_or(TernaryLoweringError::InvalidProjection)?
        .clone();
    for predecessor in remaining {
        let index = usize::try_from(*predecessor)
            .map_err(|_error| TernaryLoweringError::InvalidProjection)?;
        let other = dominators
            .get(index)
            .ok_or(TernaryLoweringError::InvalidProjection)?;
        intersection.retain(|candidate| other.contains(candidate));
    }
    Ok(intersection)
}

fn dominators(
    predecessors: &[BTreeSet<u32>],
) -> Result<PredecessorSets, TernaryLoweringError> {
    let all = (0..predecessors.len())
        .map(|index| {
            u32::try_from(index)
                .map_err(|_error| TernaryLoweringError::InvalidProjection)
        })
        .collect::<Result<BTreeSet<_>, _>>()?;
    let mut sets = vec![all; predecessors.len()];
    let entry = sets
        .first_mut()
        .ok_or(TernaryLoweringError::InvalidProjection)?;
    *entry = BTreeSet::from([0]);
    loop {
        let mut changed = false;
        for (index, incoming) in predecessors.iter().enumerate().skip(1) {
            let mut members = predecessor_intersection(incoming, &sets)?;
            let block = u32::try_from(index)
                .map_err(|_error| TernaryLoweringError::InvalidProjection)?;
            _ = members.insert(block);
            let old = sets
                .get_mut(index)
                .ok_or(TernaryLoweringError::InvalidProjection)?;
            if *old != members {
                *old = members;
                changed = true;
            }
        }
        if !changed {
            return Ok(sets);
        }
    }
}

fn check_use(
    definitions: &DefinitionTable,
    dominators: &[BTreeSet<u32>],
    value: u32,
    use_at: Definition,
) -> Result<(), TernaryLoweringError> {
    let &(defined_in, defined_at) = definitions
        .get(&value)
        .ok_or(TernaryLoweringError::InvalidProjection)?;
    let (block, position) = use_at;
    let block_index = usize::try_from(block)
        .map_err(|_error| TernaryLoweringError::InvalidProjection)?;
    let block_dominators = dominators
        .get(block_index)
        .ok_or(TernaryLoweringError::InvalidProjection)?;
    if (defined_in == block && defined_at < position)
        || (defined_in != block && block_dominators.contains(&defined_in))
    {
        Ok(())
    } else {
        Err(TernaryLoweringError::InvalidProjection)
    }
}

fn definitions_for(
    function: &InputFunction,
    bindings: &PhiBindings<'_>,
) -> Result<DefinitionTable, TernaryLoweringError> {
    let mut definitions = DefinitionTable::new();
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
            let Some(result) = instruction_definition(instruction) else {
                continue;
            };
            let position = index
                .checked_add(1)
                .ok_or(TernaryLoweringError::InvalidProjection)?;
            if definitions.insert(result, (block.id, position)).is_some() {
                return Err(TernaryLoweringError::InvalidProjection);
            }
        }
    }
    // Numeric result identities must still form a dense per-function set;
    // only their lowering order may differ from those numeric identities.
    for (expected, &actual) in definitions.keys().enumerate() {
        if u32::try_from(expected).ok() != Some(actual) {
            return Err(TernaryLoweringError::InvalidProjection);
        }
    }
    Ok(definitions)
}

fn validate_block_uses(
    function: &InputFunction,
    definitions: &DefinitionTable,
    dominators: &[BTreeSet<u32>],
) -> Result<(), TernaryLoweringError> {
    for block in &function.blocks {
        for (index, instruction) in block.instructions.iter().enumerate() {
            let position = index
                .checked_add(1)
                .ok_or(TernaryLoweringError::InvalidProjection)?;
            for operand in instruction_uses(instruction) {
                check_use(
                    definitions,
                    dominators,
                    operand,
                    (block.id, position),
                )?;
            }
        }
        let terminator_value = match block.terminator {
            InputTerminator::Branch { condition, .. } => Some(condition),
            InputTerminator::Return { value, .. } => value,
            InputTerminator::Jump { .. } | InputTerminator::Unsupported => None,
        };
        if let Some(value) = terminator_value {
            let position = block
                .instructions
                .len()
                .checked_add(1)
                .ok_or(TernaryLoweringError::InvalidProjection)?;
            check_use(definitions, dominators, value, (block.id, position))?;
        }
    }
    Ok(())
}

fn validate_phi_edge_uses(
    function: &InputFunction,
    definitions: &DefinitionTable,
    dominators: &[BTreeSet<u32>],
    bindings: &PhiBindings<'_>,
) -> Result<(), TernaryLoweringError> {
    for block in &function.blocks {
        let Some(phis) = bindings.get(&(function.id, block.id)) else {
            continue;
        };
        for phi in *phis {
            validate_phi_incoming(function, definitions, dominators, phi)?;
        }
    }
    Ok(())
}

fn validate_phi_incoming(
    function: &InputFunction,
    definitions: &DefinitionTable,
    dominators: &[BTreeSet<u32>],
    phi: &InputDynamicPhi,
) -> Result<(), TernaryLoweringError> {
    for edge in &phi.incoming {
        let index = usize::try_from(edge.block)
            .map_err(|_error| TernaryLoweringError::InvalidProjection)?;
        let source = function
            .blocks
            .get(index)
            .ok_or(TernaryLoweringError::InvalidProjection)?;
        let position = source
            .instructions
            .len()
            .checked_add(1)
            .ok_or(TernaryLoweringError::InvalidProjection)?;
        check_use(definitions, dominators, edge.value, (edge.block, position))?;
    }
    Ok(())
}

/// Validate SSA definitions, per-block ordering, phi incoming edge availability
/// and guest-dependent Boolean branch uses before emitting symbolic target IR.
/// Return a deterministic dominator-first *lowering schedule*, not a
/// renumbering of the public CFG or a choice of runtime branch or input path.
///
/// # Errors
///
/// Rejects duplicate or nonexistent definitions and any operand whose SSA
/// definition does not dominate its use or exact incoming predecessor edge.
pub(super) fn validate_dynamic_cfg_ssa(
    function: &InputFunction,
    predecessors: &[BTreeSet<u32>],
    bindings: &PhiBindings<'_>,
) -> Result<Vec<usize>, TernaryLoweringError> {
    let definitions = definitions_for(function, bindings)?;
    let dominators = dominators(predecessors)?;
    validate_block_uses(function, &definitions, &dominators)?;
    validate_phi_edge_uses(function, &definitions, &dominators, bindings)?;

    // Strict dominators always have fewer dominators than the blocks they
    // dominate. This deterministic order is a lowering schedule only: the
    // public target CFG must retain its canonical block IDs and ordering.
    let mut lowering_order = dominators
        .iter()
        .enumerate()
        .map(|(index, members)| (index, members.len()))
        .collect::<Vec<_>>();
    lowering_order.sort_by_key(|(index, depth)| (*depth, *index));
    Ok(lowering_order
        .into_iter()
        .map(|(index, _depth)| index)
        .collect())
}
