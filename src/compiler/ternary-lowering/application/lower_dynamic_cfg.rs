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
//   - Lowering explicit mutable typed CFG and phi edges to symbolic ternary
//     CFG.
// - Must-Not:
//   - Select a host-dependent path, serialize MCTR-v1, place guest code or
//     claim the source C checksum executes on the normative Malbolge VM.
// - Allows:
//   - Inputs: validated typed projection and full typed predecessor merges.
//   - Outputs: ordered target scalar/IO operations and unresolved guest
//     control.
//   - Side effects: owned allocation only.
// - Split-When:
//   - Guest CFG layout has its own verified assembly and relocation policy.
// - Merge-When:
//   - MCTR gains a fully validated dynamic CFG wire and machine linker.
// - Summary:
//   - Preserves dynamic EOF branches and loop-carried SSA in pre-layout IR.
//
//! Source-bound dynamic CFG lowering; target branches remain unlinked.

use std::collections::{BTreeMap, BTreeSet};

use super::input::{
    InputBlock, InputDynamicBlockPhis, InputDynamicPhi, InputFunction,
    InputScalarType, InputSourcePosition, InputSourceSpan, InputTerminator,
    TypedIrInput,
};
use super::lower::{
    LoweringState, TernaryLoweringError, copy_span, lower_instruction,
    lower_return_operation, projected_instruction_span,
    projection_span_contains, valid_projection_span, validate_projection,
    validate_projection_source_positions,
};
use super::model::{
    TernaryCfgBlock, TernaryCfgFunction, TernaryCfgPhi, TernaryCfgPlan,
    TernaryCfgScalarKind, TernaryCfgTerminator, TernaryOperation,
};
use super::validate_dynamic_cfg_ssa::{
    PhiBindings, PredecessorSets, validate_dynamic_cfg_ssa,
};

const MAX_DYNAMIC_BLOCKS: usize = 256;
type SourceAnchors = BTreeMap<u32, (u32, u32)>;
type LoweredBlockPhis = (Vec<TernaryCfgPhi>, Vec<(u32, InputScalarType)>);

// Phi source locations are copied independently from the typed verifier.
// Require their shared offsets to agree with every anchored function,
// instruction and terminator position; source ranges alone are insufficient.
fn register_position(
    anchors: &mut SourceAnchors,
    position: InputSourcePosition,
) -> Result<(), TernaryLoweringError> {
    let location = (position.line, position.column);
    if anchors
        .insert(position.byte, location)
        .is_some_and(|old| old != location)
    {
        return Err(TernaryLoweringError::InvalidProjection);
    }
    Ok(())
}

fn register_span(
    anchors: &mut SourceAnchors,
    span: InputSourceSpan,
) -> Result<(), TernaryLoweringError> {
    register_position(anchors, span.begin)?;
    register_position(anchors, span.end)
}

fn register_function_positions(
    anchors: &mut SourceAnchors,
    function: &InputFunction,
) -> Result<(), TernaryLoweringError> {
    register_span(anchors, function.span)?;
    for block in &function.blocks {
        let terminator_span = match block.terminator {
            InputTerminator::Branch { span, .. }
            | InputTerminator::Jump { span, .. }
            | InputTerminator::Return { span, .. } => Some(span),
            InputTerminator::Unsupported => None,
        };
        if let Some(span) = terminator_span {
            register_span(anchors, span)?;
        }
        for instruction in &block.instructions {
            if let Some(instruction_span) =
                projected_instruction_span(instruction)
            {
                register_span(anchors, instruction_span)?;
            }
        }
    }
    Ok(())
}

fn validate_dynamic_phi_source_positions(
    input: &TypedIrInput,
    bindings: &[InputDynamicBlockPhis],
) -> Result<(), TernaryLoweringError> {
    let mut anchors = SourceAnchors::new();
    for function in &input.functions {
        register_function_positions(&mut anchors, function)?;
    }
    for binding in bindings {
        for phi in &binding.phis {
            register_span(&mut anchors, phi.span)?;
        }
    }
    let mut previous = None;
    for &coordinates in anchors.values() {
        if previous.is_some_and(|(line, column): (u32, u32)| {
            line > coordinates.0
                || (line == coordinates.0 && column > coordinates.1)
        }) {
            return Err(TernaryLoweringError::InvalidProjection);
        }
        previous = Some(coordinates);
    }
    Ok(())
}

fn phi_kind(
    kind: InputScalarType,
) -> Result<TernaryCfgScalarKind, TernaryLoweringError> {
    match kind {
        InputScalarType::Bool => Ok(TernaryCfgScalarKind::Bool),
        InputScalarType::I8 => Ok(TernaryCfgScalarKind::I8),
        InputScalarType::I16 => Ok(TernaryCfgScalarKind::I16),
        InputScalarType::I32 => Ok(TernaryCfgScalarKind::I32),
        InputScalarType::U8 => Ok(TernaryCfgScalarKind::U8),
        InputScalarType::U16 => Ok(TernaryCfgScalarKind::U16),
        InputScalarType::U32 => Ok(TernaryCfgScalarKind::U32),
        InputScalarType::Other | InputScalarType::Void => {
            Err(TernaryLoweringError::UnsupportedInstruction)
        },
    }
}

fn successors(
    terminator: InputTerminator,
) -> Result<Vec<u32>, TernaryLoweringError> {
    match terminator {
        InputTerminator::Jump { target, .. } => Ok(vec![target]),
        InputTerminator::Branch {
            false_target,
            true_target,
            ..
        } if false_target == true_target => Ok(vec![true_target]),
        InputTerminator::Branch {
            false_target,
            true_target,
            ..
        } => Ok(vec![false_target, true_target]),
        InputTerminator::Return { .. } => Ok(Vec::new()),
        InputTerminator::Unsupported => {
            Err(TernaryLoweringError::UnsupportedTerminator)
        },
    }
}

fn predecessor_sets(
    function: &InputFunction,
) -> Result<PredecessorSets, TernaryLoweringError> {
    let count = function.blocks.len();
    if count == 0 || count > MAX_DYNAMIC_BLOCKS || function.parameter_count != 0
    {
        return Err(TernaryLoweringError::UnsupportedFunction);
    }
    if function.entry != 0 {
        return Err(TernaryLoweringError::InvalidProjection);
    }
    let mut predecessors = vec![BTreeSet::new(); count];
    for (position, block) in function.blocks.iter().enumerate() {
        if usize::try_from(block.id).ok() != Some(position) {
            return Err(TernaryLoweringError::InvalidProjection);
        }
        for target in successors(block.terminator)? {
            let index = usize::try_from(target)
                .map_err(|_error| TernaryLoweringError::InvalidProjection)?;
            let incoming = predecessors
                .get_mut(index)
                .ok_or(TernaryLoweringError::InvalidProjection)?;
            _ = incoming.insert(block.id);
        }
    }
    if predecessors.first().is_some_and(|entry| !entry.is_empty()) {
        return Err(TernaryLoweringError::InvalidProjection);
    }
    let mut visited = BTreeSet::new();
    let mut pending = vec![function.entry];
    while let Some(block) = pending.pop() {
        if visited.insert(block) {
            let index = usize::try_from(block)
                .map_err(|_error| TernaryLoweringError::InvalidProjection)?;
            let current = function
                .blocks
                .get(index)
                .ok_or(TernaryLoweringError::InvalidProjection)?;
            pending.extend(successors(current.terminator)?);
        }
    }
    if visited.len() != count {
        return Err(TernaryLoweringError::UnsupportedFunction);
    }
    Ok(predecessors)
}

fn check_phi(
    phi: &InputDynamicPhi,
    predecessors: &BTreeSet<u32>,
    function_span: InputSourceSpan,
) -> Result<(), TernaryLoweringError> {
    if !valid_projection_span(phi.span)
        || !projection_span_contains(function_span, phi.span)
        || phi.incoming.len() != predecessors.len()
        || phi.incoming.is_empty()
    {
        return Err(TernaryLoweringError::InvalidProjection);
    }
    let actual = phi
        .incoming
        .iter()
        .map(|edge| edge.block)
        .collect::<Vec<_>>();
    if actual != predecessors.iter().copied().collect::<Vec<_>>() {
        return Err(TernaryLoweringError::InvalidProjection);
    }
    Ok(())
}

fn lower_cfg_terminator(
    function: &InputFunction,
    block: &InputBlock,
    state: &LoweringState,
) -> Result<TernaryCfgTerminator, TernaryLoweringError> {
    let terminator = match block.terminator {
        InputTerminator::Jump { target, span } => TernaryCfgTerminator::Jump {
            span: copy_span(span),
            target,
        },
        InputTerminator::Branch {
            condition,
            false_target,
            span,
            true_target,
        } => {
            if !state.has_kind(condition, InputScalarType::Bool) {
                return Err(TernaryLoweringError::UnsupportedTerminator);
            }
            TernaryCfgTerminator::Branch {
                condition,
                false_target,
                span: copy_span(span),
                true_target,
            }
        },
        InputTerminator::Return { value, span } => {
            let operation = if function.return_kind == InputScalarType::Void
                && value.is_none()
            {
                TernaryOperation::ReturnVoid { span: copy_span(span) }
            } else {
                lower_return_operation(
                    function.return_kind,
                    state,
                    value.ok_or(TernaryLoweringError::UnsupportedTerminator)?,
                    copy_span(span),
                )?
            };
            TernaryCfgTerminator::Return(operation)
        },
        InputTerminator::Unsupported => {
            return Err(TernaryLoweringError::UnsupportedTerminator);
        },
    };
    Ok(terminator)
}

fn lower_block_phis(
    function_span: InputSourceSpan,
    incoming: &BTreeSet<u32>,
    binding: &[InputDynamicPhi],
    state: &mut LoweringState,
) -> Result<LoweredBlockPhis, TernaryLoweringError> {
    let mut phis = Vec::with_capacity(binding.len());
    let mut edge_values = Vec::new();
    for phi in binding {
        check_phi(phi, incoming, function_span)?;
        state.define_phi(phi.result, phi.type_kind)?;
        let kind = phi_kind(phi.type_kind)?;
        edge_values.extend(
            phi.incoming.iter().map(|edge| (edge.value, phi.type_kind)),
        );
        phis.push(TernaryCfgPhi {
            incoming: phi
                .incoming
                .iter()
                .map(|edge| (edge.block, edge.value))
                .collect(),
            result: phi.result,
            span: copy_span(phi.span),
            type_kind: kind,
        });
    }
    Ok((phis, edge_values))
}

fn lower_function_cfg(
    function: &InputFunction,
    phi_bindings: &PhiBindings<'_>,
) -> Result<TernaryCfgFunction, TernaryLoweringError> {
    let predecessors = predecessor_sets(function)?;
    let lowering_order =
        validate_dynamic_cfg_ssa(function, &predecessors, phi_bindings)?;
    let mut state = LoweringState::for_dynamic_cfg();
    let mut blocks = BTreeMap::new();
    let mut pending_edges = Vec::new();
    for index in lowering_order {
        let block = function
            .blocks
            .get(index)
            .ok_or(TernaryLoweringError::InvalidProjection)?;
        let binding = phi_bindings
            .get(&(function.id, block.id))
            .copied()
            .unwrap_or(&[]);
        if binding.len() != block.phi_count {
            return Err(TernaryLoweringError::InvalidProjection);
        }
        let incoming = predecessors
            .get(index)
            .ok_or(TernaryLoweringError::InvalidProjection)?;
        let (phis, edge_values) =
            lower_block_phis(function.span, incoming, binding, &mut state)?;
        pending_edges.extend(edge_values);
        let operations = block
            .instructions
            .iter()
            .map(|instruction| lower_instruction(instruction, &mut state))
            .collect::<Result<Vec<_>, _>>()?;
        let terminator = lower_cfg_terminator(function, block, &state)?;
        if blocks
            .insert(block.id, TernaryCfgBlock {
                id: block.id,
                operations,
                phis,
                terminator,
            })
            .is_some()
        {
            return Err(TernaryLoweringError::InvalidProjection);
        }
    }
    for (value, kind) in pending_edges {
        if !state.has_kind(value, kind) {
            return Err(TernaryLoweringError::InvalidProjection);
        }
    }
    Ok(TernaryCfgFunction {
        blocks: blocks.into_values().collect(),
        entry: function.entry,
        id: function.id,
        name: function.name.clone(),
        span: copy_span(function.span),
    })
}

/// Preserves dynamic branches, loop-carried phi state and ordered machine IO
/// as a symbolic target graph without guessing guest addresses or execution.
///
/// # Errors
///
/// Refuses invalid identities, disconnected CFGs, incomplete/forged phi edges,
/// unsupported scalar operations and malformed control or source provenance.
/// The result is not a guest-executable artifact or MCTR-v1 checkpoint.
pub fn lower_dynamic_typed_cfg(
    input: &TypedIrInput,
    bindings: &[InputDynamicBlockPhis],
) -> Result<TernaryCfgPlan, TernaryLoweringError> {
    validate_projection(input)?;
    if input.global_count != 0 || input.proof_obligation_count != 0 {
        return Err(TernaryLoweringError::UnsupportedModule);
    }
    validate_projection_source_positions(input)?;
    validate_dynamic_phi_source_positions(input, bindings)?;
    let mut phi_bindings = PhiBindings::new();
    for binding in bindings {
        if binding.phis.is_empty()
            || !input.functions.iter().any(|function| {
                function.id == binding.function
                    && usize::try_from(binding.block)
                        .is_ok_and(|index| function.blocks.get(index).is_some())
            })
            || phi_bindings
                .insert((binding.function, binding.block), &binding.phis)
                .is_some()
        {
            return Err(TernaryLoweringError::InvalidProjection);
        }
    }
    let functions = input
        .functions
        .iter()
        .map(|function| lower_function_cfg(function, &phi_bindings))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(TernaryCfgPlan {
        abi_id: input.abi_id.clone(),
        functions,
        input_format_version: input.input_format_version,
        source_id: input.source_id.clone(),
        source_sha256: input.source_sha256,
        target_profile: input.target_profile.clone(),
    })
}
