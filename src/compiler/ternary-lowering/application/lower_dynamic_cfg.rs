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
    InputDynamicBlockPhis, InputDynamicPhi, InputFunction, InputScalarType,
    InputSourcePosition, InputSourceSpan, InputTerminator, TypedIrInput,
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
use super::validate_dynamic_cfg_ssa::validate_dynamic_cfg_ssa;

const MAX_DYNAMIC_BLOCKS: usize = 256;

// Phi source locations are copied independently from the typed verifier.
// Require their shared offsets to agree with every anchored function,
// instruction and terminator position; source ranges alone are insufficient.
fn register_position(
    anchors: &mut BTreeMap<u32, (u32, u32)>,
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
    anchors: &mut BTreeMap<u32, (u32, u32)>,
    span: InputSourceSpan,
) -> Result<(), TernaryLoweringError> {
    register_position(anchors, span.begin)?;
    register_position(anchors, span.end)
}

fn validate_dynamic_phi_source_positions(
    input: &TypedIrInput,
    bindings: &[InputDynamicBlockPhis],
) -> Result<(), TernaryLoweringError> {
    let mut anchors = BTreeMap::new();
    for function in &input.functions {
        register_span(&mut anchors, function.span)?;
        for block in &function.blocks {
            let span = match block.terminator {
                InputTerminator::Branch { span, .. }
                | InputTerminator::Jump { span, .. }
                | InputTerminator::Return { span, .. } => Some(span),
                InputTerminator::Unsupported => None,
            };
            if let Some(span) = span {
                register_span(&mut anchors, span)?;
            }
            for instruction in &block.instructions {
                if let Some(span) = projected_instruction_span(instruction) {
                    register_span(&mut anchors, span)?;
                }
            }
        }
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
        InputScalarType::I32 => Ok(TernaryCfgScalarKind::I32),
        InputScalarType::U32 => Ok(TernaryCfgScalarKind::U32),
        InputScalarType::U8 => Ok(TernaryCfgScalarKind::U8),
        _ => Err(TernaryLoweringError::UnsupportedInstruction),
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
) -> Result<Vec<BTreeSet<u32>>, TernaryLoweringError> {
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
    if !predecessors[0].is_empty() {
        return Err(TernaryLoweringError::InvalidProjection);
    }
    let mut visited = BTreeSet::new();
    let mut pending = vec![function.entry];
    while let Some(block) = pending.pop() {
        if visited.insert(block) {
            pending.extend(successors(
                function.blocks[block as usize].terminator,
            )?);
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
    function: &InputFunction,
) -> Result<(), TernaryLoweringError> {
    if !valid_projection_span(phi.span)
        || !projection_span_contains(function.span, phi.span)
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

fn lower_function_cfg(
    function: &InputFunction,
    phi_bindings: &BTreeMap<(u32, u32), &[InputDynamicPhi]>,
) -> Result<TernaryCfgFunction, TernaryLoweringError> {
    let predecessors = predecessor_sets(function)?;
    validate_dynamic_cfg_ssa(function, &predecessors, phi_bindings)?;
    let mut state = LoweringState::default();
    let mut blocks = Vec::with_capacity(function.blocks.len());
    let mut pending_edges = Vec::new();
    for block in &function.blocks {
        let binding = phi_bindings
            .get(&(function.id, block.id))
            .copied()
            .unwrap_or(&[]);
        if binding.len() != block.phi_count {
            return Err(TernaryLoweringError::InvalidProjection);
        }
        let mut phis = Vec::new();
        for phi in binding {
            check_phi(phi, &predecessors[block.id as usize], function)?;
            state.define_phi(phi.result, phi.type_kind)?;
            let kind = phi_kind(phi.type_kind)?;
            for edge in &phi.incoming {
                pending_edges.push((edge.value, phi.type_kind));
            }
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
        let operations = block
            .instructions
            .iter()
            .map(|instruction| lower_instruction(instruction, &mut state))
            .collect::<Result<Vec<_>, _>>()?;
        let terminator = match block.terminator {
            InputTerminator::Jump { target, span } => {
                TernaryCfgTerminator::Jump {
                    span: copy_span(span),
                    target,
                }
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
                        &state,
                        value.ok_or(
                            TernaryLoweringError::UnsupportedTerminator,
                        )?,
                        copy_span(span),
                    )?
                };
                TernaryCfgTerminator::Return(operation)
            },
            InputTerminator::Unsupported => {
                return Err(TernaryLoweringError::UnsupportedTerminator);
            },
        };
        blocks.push(TernaryCfgBlock {
            id: block.id,
            operations,
            phis,
            terminator,
        });
    }
    for (value, kind) in pending_edges {
        if !state.has_kind(value, kind) {
            return Err(TernaryLoweringError::InvalidProjection);
        }
    }
    Ok(TernaryCfgFunction {
        blocks,
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
    let mut phi_bindings = BTreeMap::<(u32, u32), &[InputDynamicPhi]>::new();
    for binding in bindings {
        if binding.phis.is_empty()
            || !input.functions.iter().any(|function| {
                function.id == binding.function
                    && usize::try_from(binding.block).ok().is_some_and(
                        |index| function.blocks.get(index).is_some(),
                    )
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
