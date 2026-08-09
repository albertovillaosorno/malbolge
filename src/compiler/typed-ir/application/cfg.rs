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
//   - Typed-IR block identity, reachability, predecessors, phi shape, and
//     dominance.
// - Must-Not:
//   - Validate arithmetic/call semantics or rewrite malformed control flow.
// - Allows:
//   - Inputs: one explicit function CFG plus its typed SSA definition
//     inventory.
//   - Outputs: deterministic predecessor/dominator analysis for later checks.
//   - Side effects: ordered validation-set/map allocation only.
// - Split-When:
//   - Loop analysis or optimization CFG transforms gain independent ownership.
// - Merge-When:
//   - Instruction admission owns all control-flow policy directly.
// - Summary:
//   - Proves explicit CFG and phi/SSA edge semantics before lowering.
// - Description:
//   - Dominance is computed from repository block IDs, never container
//     addresses.
// - Usage:
//   - Shared by instruction, terminator, phi, and proof validation.
// - Defaults:
//   - Every declared block must be reachable from the explicit entry block.
//

//! Control-flow graph, phi-edge, and SSA dominance admission.

use std::collections::{BTreeMap, BTreeSet, VecDeque};

use super::control::{BasicBlock, Phi, SwitchCase, Terminator};
use super::error::ValidationError;
use super::ids::{BlockId, TypeId, ValueId};
use super::module::Function;
use super::values::{DefinitionSite, ValueTable};

type BlockRelations = BTreeMap<BlockId, BlockSet>;
type BlockSet = BTreeSet<BlockId>;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct InstructionPoint {
    pub(super) block: BlockId,
    pub(super) order: u32,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(super) struct ControlFlow {
    dominators: BlockRelations,
}

impl ControlFlow {
    pub(super) fn dominates(&self, candidate: BlockId, block: BlockId) -> bool {
        self.dominators
            .get(&block)
            .is_some_and(|dominators| dominators.contains(&candidate))
    }
}

pub(super) fn analyze_cfg(
    function: &Function,
    values: &ValueTable,
) -> Result<ControlFlow, ValidationError> {
    validate_block_ids(function)?;
    let predecessors = build_predecessors(function)?;
    validate_reachability(function)?;
    validate_phis(function, values, &predecessors)?;
    let dominators = compute_dominators(function, &predecessors)?;
    let flow = ControlFlow { dominators };
    validate_phi_dominance(function, values, &flow)?;
    Ok(flow)
}

pub(super) fn available_at_instruction(
    flow: &ControlFlow,
    values: &ValueTable,
    value: ValueId,
    point: InstructionPoint,
) -> bool {
    let Some(info) = values.get(&value) else {
        return false;
    };
    match info.site {
        DefinitionSite::Parameter => true,
        DefinitionSite::Instruction {
            block: definition,
            order: definition_order,
        } if definition == point.block => definition_order < point.order,
        DefinitionSite::Instruction { block: definition, .. }
        | DefinitionSite::Phi { block: definition } => {
            flow.dominates(definition, point.block)
        },
    }
}

pub(super) fn available_at_terminator(
    flow: &ControlFlow,
    values: &ValueTable,
    value: ValueId,
    block: BlockId,
) -> bool {
    let Some(info) = values.get(&value) else {
        return false;
    };
    match info.site {
        DefinitionSite::Parameter => true,
        DefinitionSite::Phi { block: definition }
        | DefinitionSite::Instruction { block: definition, .. } => {
            flow.dominates(definition, block)
        },
    }
}

pub(super) fn value_type(
    values: &ValueTable,
    value: ValueId,
) -> Result<TypeId, ValidationError> {
    values
        .get(&value)
        .map(|info| info.type_id)
        .ok_or(ValidationError::ValueIdentity)
}

fn block_by_id(function: &Function, block_id: BlockId) -> Option<&BasicBlock> {
    let index = usize::try_from(block_id.value()).ok()?;
    function
        .blocks()
        .get(index)
        .filter(|block| block.id() == block_id)
}

fn build_predecessors(
    function: &Function,
) -> Result<BlockRelations, ValidationError> {
    let mut predecessors = function
        .blocks()
        .iter()
        .map(|block| (block.id(), BTreeSet::new()))
        .collect::<BTreeMap<_, _>>();
    for block in function.blocks() {
        for target in terminator_targets(block.terminator()) {
            if block_by_id(function, target).is_none() {
                return Err(ValidationError::BlockIdentity);
            }
            let incoming = predecessors
                .get_mut(&target)
                .ok_or(ValidationError::BlockIdentity)?;
            _ = incoming.insert(block.id());
        }
    }
    Ok(predecessors)
}

fn compute_dominators(
    function: &Function,
    predecessors: &BlockRelations,
) -> Result<BlockRelations, ValidationError> {
    let all_blocks = function
        .blocks()
        .iter()
        .map(BasicBlock::id)
        .collect::<BTreeSet<_>>();
    let mut dominators = function
        .blocks()
        .iter()
        .map(|block| {
            let initial = if block.id() == function.entry() {
                BTreeSet::from([block.id()])
            } else {
                all_blocks.clone()
            };
            (block.id(), initial)
        })
        .collect::<BTreeMap<_, _>>();
    let mut changed = true;
    while changed {
        changed = update_dominators(function, predecessors, &mut dominators)?;
    }
    Ok(dominators)
}

fn intersect_predecessor_dominators(
    predecessor_ids: &BlockSet,
    dominators: &BlockRelations,
) -> Result<BlockSet, ValidationError> {
    let mut predecessor_iter = predecessor_ids.iter();
    let first = predecessor_iter
        .next()
        .ok_or(ValidationError::Reachability)?;
    let mut intersection = dominators
        .get(first)
        .cloned()
        .ok_or(ValidationError::BlockIdentity)?;
    for predecessor in predecessor_iter {
        let predecessor_dominators = dominators
            .get(predecessor)
            .ok_or(ValidationError::BlockIdentity)?;
        intersection.retain(|block| predecessor_dominators.contains(block));
    }
    Ok(intersection)
}

fn terminator_targets(terminator: &Terminator) -> Vec<BlockId> {
    match terminator {
        Terminator::Branch {
            false_target,
            true_target,
            ..
        } => vec![*true_target, *false_target],
        Terminator::Jump { target } => vec![*target],
        Terminator::Return { .. } => Vec::new(),
        Terminator::Switch {
            cases, default_target, ..
        } => {
            let mut targets = Vec::with_capacity(cases.len().saturating_add(1));
            targets.push(*default_target);
            targets.extend(cases.iter().map(SwitchCase::target));
            targets
        },
    }
}

fn update_dominators(
    function: &Function,
    predecessors: &BlockRelations,
    dominators: &mut BlockRelations,
) -> Result<bool, ValidationError> {
    let mut changed = false;
    for block in function.blocks() {
        if block.id() == function.entry() {
            continue;
        }
        let predecessor_ids = predecessors
            .get(&block.id())
            .ok_or(ValidationError::BlockIdentity)?;
        let mut updated =
            intersect_predecessor_dominators(predecessor_ids, dominators)?;
        _ = updated.insert(block.id());
        if dominators.get(&block.id()) != Some(&updated) {
            let _previous = dominators.insert(block.id(), updated);
            changed = true;
        }
    }
    Ok(changed)
}

fn validate_block_ids(function: &Function) -> Result<(), ValidationError> {
    if function.blocks().is_empty()
        || block_by_id(function, function.entry()).is_none()
    {
        return Err(ValidationError::BlockIdentity);
    }
    for (index, block) in function.blocks().iter().enumerate() {
        let expected = u32::try_from(index)
            .map_err(|_error| ValidationError::BlockIdentity)?;
        if block.id().value() != expected {
            return Err(ValidationError::BlockIdentity);
        }
    }
    Ok(())
}

fn validate_phis(
    function: &Function,
    values: &ValueTable,
    predecessors: &BlockRelations,
) -> Result<(), ValidationError> {
    for block in function.blocks() {
        if block.id() == function.entry() && !block.phis().is_empty() {
            return Err(ValidationError::PhiPredecessors);
        }
        let expected = predecessors
            .get(&block.id())
            .ok_or(ValidationError::BlockIdentity)?;
        validate_block_phis(block, values, expected)?;
    }
    Ok(())
}

fn validate_block_phis(
    block: &BasicBlock,
    values: &ValueTable,
    expected: &BlockSet,
) -> Result<(), ValidationError> {
    for phi in block.phis() {
        if phi.incoming().is_empty() {
            return Err(ValidationError::PhiPredecessors);
        }
        let incoming_blocks = phi
            .incoming()
            .iter()
            .map(|incoming| incoming.block())
            .collect::<BlockSet>();
        if incoming_blocks.len() != phi.incoming().len()
            || &incoming_blocks != expected
        {
            return Err(ValidationError::PhiPredecessors);
        }
        validate_phi_types(phi, values)?;
    }
    Ok(())
}

fn validate_phi_types(
    phi: &Phi,
    values: &ValueTable,
) -> Result<(), ValidationError> {
    for incoming in phi.incoming() {
        if value_type(values, incoming.value())? != phi.type_id() {
            return Err(ValidationError::OperandType);
        }
    }
    Ok(())
}

fn validate_phi_dominance(
    function: &Function,
    values: &ValueTable,
    flow: &ControlFlow,
) -> Result<(), ValidationError> {
    for block in function.blocks() {
        for phi in block.phis() {
            validate_phi_edges(phi, values, flow)?;
        }
    }
    Ok(())
}

fn validate_phi_edges(
    phi: &Phi,
    values: &ValueTable,
    flow: &ControlFlow,
) -> Result<(), ValidationError> {
    for incoming in phi.incoming() {
        if !available_at_terminator(
            flow,
            values,
            incoming.value(),
            incoming.block(),
        ) {
            return Err(ValidationError::SsaDominance);
        }
    }
    Ok(())
}

fn validate_reachability(function: &Function) -> Result<(), ValidationError> {
    let mut reachable = BTreeSet::new();
    let mut queue = VecDeque::from([function.entry()]);
    while let Some(block_id) = queue.pop_front() {
        if !reachable.insert(block_id) {
            continue;
        }
        let block = block_by_id(function, block_id)
            .ok_or(ValidationError::BlockIdentity)?;
        queue.extend(terminator_targets(block.terminator()));
    }
    if reachable.len() != function.blocks().len() {
        return Err(ValidationError::Reachability);
    }
    Ok(())
}
