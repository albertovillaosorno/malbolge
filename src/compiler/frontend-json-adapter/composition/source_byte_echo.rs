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
//   - Source-authenticated straight-line C input-to-output lowering.
// - Must-Not:
//   - Fold runtime input, claim EOF behavior or accept hidden C effects.
// - Allows:
//   - Inputs: exact pinned Clang call ancestry and source locations.
//   - Outputs: validated typed SSA byte input/output effect pairs.
//   - Side effects: none.
// - Split-When:
//   - General source-C guest runtime I/O replaces this bounded grammar.
// - Merge-When:
//   - Source control-flow lowering proves the same call composition.
// - Summary:
//   - Retains live successful guest input instead of host-time projection.

//! Closed dynamic-byte input provenance from normalized source C to typed IR.

use std::collections::HashSet;

use super::typed::{
    BasicBlock, BasicBlockSpec, FrontendArtifact, FrontendArtifactSpec,
    FrontendFallthroughVoidFunctionSpec, FrontendReturnVoidFunction, Function,
    FunctionSpec, Instruction, LocatedInstruction, Module, ModuleSpec, TypeId,
    ValueId,
};
use super::{
    Artifact, FrontendGuestMode, FrontendJsonError, Node, canonical_bytes,
    canonical_module, lower_frontend_artifact, source_digest, span, typed_span,
};

const MAX_ECHO_CALLS: usize = 128;
const CALL_NODE_COUNT: usize = 6;
const MAX_SOURCE_OUTPUTS: usize = 256;
const MAX_NESTED_LOCAL_DEPTH: usize = 16;

/// The exact source-local input initializer, with no intervening effects.
struct LocalDeclaration<'node> {
    declaration_end: u32,
    input: &'node Node,
    line: u32,
    name: &'node str,
    variable_reference: String,
}

// A comma operand selects the latest live input or consumes a fresh one.
// Source extent differs from the input when a local value is read without I/O.
struct CommaEffect<'node> {
    input: &'node Node,
    extent: &'node Node,
    // Outer-to-inner preorder, emitted in inner-to-outer C evaluation order.
    outputs: Vec<&'node Node>,
}

type OutputCallProof<'node> = (usize, Vec<&'node Node>);

// The nested successful-byte return is not recomputed: every write uses the
// same already-read guest SSA identity, in innermost-first C evaluation order.
fn emit_comma_outputs(
    effect: &CommaEffect<'_>,
    value: ValueId,
    instructions: &mut Vec<LocatedInstruction>,
) {
    for write in effect.outputs.iter().rev() {
        instructions.push(LocatedInstruction::new(
            Instruction::ByteOutput { value },
            typed_span(&write.span),
        ));
    }
}

// A comma operand proven to read the current local is a reuse of its live
// guest SSA byte, not a second input. Once any operand reads new stdin, that
// old local can no longer be materialized by this accumulator-only backend.
fn emit_comma_effects(
    effects: &[CommaEffect<'_>],
    local: Option<&(LocalDeclaration<'_>, ValueId)>,
    inputs: &mut usize,
    outputs: &mut usize,
    instructions: &mut Vec<LocatedInstruction>,
) -> Option<(ValueId, bool)> {
    let mut selected = None;
    let mut read_new_input = false;
    for effect in effects {
        let value = if let Some((declaration, value)) = local
            && effect.input.id == declaration.input.id
        {
            if read_new_input {
                return None;
            }
            *value
        } else {
            if *inputs == MAX_ECHO_CALLS {
                return None;
            }
            let value = ValueId::new(u32::try_from(*inputs).ok()?);
            instructions.push(LocatedInstruction::new(
                Instruction::ByteInput {
                    result: value,
                    type_id: TypeId::new(0),
                },
                typed_span(&effect.input.span),
            ));
            *inputs = inputs.checked_add(1)?;
            read_new_input = true;
            value
        };
        *outputs = outputs.checked_add(effect.outputs.len())?;
        if *outputs > MAX_SOURCE_OUTPUTS {
            return None;
        }
        emit_comma_outputs(effect, value, instructions);
        selected = Some(value);
    }
    Some((selected?, read_new_input))
}

const fn metadata_empty(node: &Node) -> bool {
    node.name.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
        && node.constant_integer.is_none()
        && node.literal.is_none()
}

// Exact spelling boundaries of `putchar(getchar())` as Clang 22.1.8
// normalizes it, with no wrappers, alternate evaluation or hidden calls.
#[expect(
    clippy::too_many_arguments,
    reason = "a source word has four independent checked Clang coordinates"
)]
const fn source_word(
    node: &Node,
    start: u32,
    end: u32,
    line: u32,
    column: u32,
) -> bool {
    node.span.begin.byte == start
        && node.span.end.byte == end
        && node.span.begin.line == line
        && node.span.end.line == line
        && node.span.begin.column == column
        && node.span.end.column
            == column.saturating_add(end.saturating_sub(start))
}

#[expect(
    clippy::too_many_lines,
    reason = "full six-node Clang call ancestry is checked as one closed unit"
)]
fn prove_call<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    parent: u32,
) -> Option<(&'node Node, &'node Node)> {
    let [
        output,
        output_cast,
        output_callee,
        input,
        input_cast,
        input_callee,
    ] = nodes
    else {
        return None;
    };
    let base = output.id;
    let start = output.span.begin.byte;
    let line = output.span.begin.line;
    let column = output.span.begin.column;
    let well_formed = start > previous
        && start > body.span.begin.byte
        && start.checked_add(18)? < body.span.end.byte
        && line > 0
        && column > 0
        && output.parent == parent
        && output.kind == "call-expression"
        && output.type_name.as_deref() == Some("i32")
        && output.reference.as_deref() == Some("external:putchar")
        && output.operation.is_none()
        && source_word(output, start, start.checked_add(18)?, line, column)
        && output_cast.id == base.checked_add(1)?
        && output_cast.parent == base
        && output_cast.kind == "cast-expression"
        && output_cast.type_name.as_deref() == Some("ptr(fn(i32)->i32)")
        && output_cast.operation.as_deref() == Some("function-to-pointer")
        && output_cast.reference.is_none()
        && source_word(output_cast, start, start.checked_add(7)?, line, column)
        && output_callee.id == base.checked_add(2)?
        && output_callee.parent == output_cast.id
        && output_callee.kind == "declaration-reference-expression"
        && output_callee.type_name.as_deref() == Some("fn(i32)->i32")
        && output_callee.reference.as_deref() == Some("external:putchar")
        && output_callee.operation.is_none()
        && source_word(
            output_callee,
            start,
            start.checked_add(7)?,
            line,
            column,
        )
        && input.id == base.checked_add(3)?
        && input.parent == base
        && input.kind == "call-expression"
        && input.type_name.as_deref() == Some("i32")
        && input.reference.as_deref() == Some("external:getchar")
        && input.operation.is_none()
        && source_word(
            input,
            start.checked_add(8)?,
            start.checked_add(17)?,
            line,
            column.checked_add(8)?,
        )
        && input_cast.id == base.checked_add(4)?
        && input_cast.parent == input.id
        && input_cast.kind == "cast-expression"
        && input_cast.type_name.as_deref() == Some("ptr(fn()->i32)")
        && input_cast.operation.as_deref() == Some("function-to-pointer")
        && input_cast.reference.is_none()
        && source_word(
            input_cast,
            start.checked_add(8)?,
            start.checked_add(15)?,
            line,
            column.checked_add(8)?,
        )
        && input_callee.id == base.checked_add(5)?
        && input_callee.parent == input_cast.id
        && input_callee.kind == "declaration-reference-expression"
        && input_callee.type_name.as_deref() == Some("fn()->i32")
        && input_callee.reference.as_deref() == Some("external:getchar")
        && input_callee.operation.is_none()
        && source_word(
            input_callee,
            start.checked_add(8)?,
            start.checked_add(15)?,
            line,
            column.checked_add(8)?,
        )
        && [
            output,
            output_cast,
            output_callee,
            input,
            input_cast,
            input_callee,
        ]
        .iter()
        .all(|node| metadata_empty(node));
    well_formed.then_some((input, output))
}

// A source-proven getchar() is a guest effect even when its result
// is discarded. Both standalone and comma-child calls use the same exact
// three-node proof to preserve input ordering and prevent hidden effects.
fn prove_input_call<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    identity: (u32, u32),
) -> Option<&'node Node> {
    let [call, cast, callee] = nodes else {
        return None;
    };
    let start = call.span.begin.byte;
    let line = call.span.begin.line;
    let column = call.span.begin.column;
    let end = start.checked_add(9)?;
    let source_ok = start > previous
        && start > body.span.begin.byte
        && end < body.span.end.byte
        && line > 0
        && column > 0
        && call.id == identity.0
        && call.parent == identity.1
        && call.kind == "call-expression"
        && call.type_name.as_deref() == Some("i32")
        && call.reference.as_deref() == Some("external:getchar")
        && call.operation.is_none()
        && metadata_empty(call)
        && source_word(call, start, end, line, column)
        && cast.id == call.id.checked_add(1)?
        && cast.parent == call.id
        && cast.kind == "cast-expression"
        && cast.type_name.as_deref() == Some("ptr(fn()->i32)")
        && cast.operation.as_deref() == Some("function-to-pointer")
        && cast.reference.is_none()
        && metadata_empty(cast)
        && source_word(cast, start, start.checked_add(7)?, line, column)
        && callee.id == cast.id.checked_add(1)?
        && callee.parent == cast.id
        && callee.kind == "declaration-reference-expression"
        && callee.type_name.as_deref() == Some("fn()->i32")
        && callee.reference.as_deref() == Some("external:getchar")
        && callee.operation.is_none()
        && metadata_empty(callee)
        && source_word(callee, start, start.checked_add(7)?, line, column);
    source_ok.then_some(call)
}

// The value of an entire comma expression is its rightmost successful
// input or putchar return. Every earlier operand is evaluated in the guest,
// and the enclosing putchar writes the last live byte one more time.
#[expect(
    clippy::too_many_lines,
    reason = "authenticate the complete comma-argument source and ancestry"
)]
fn prove_comma_output_effects<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    local: Option<&LocalDeclaration<'node>>,
) -> Option<(usize, Vec<CommaEffect<'node>>, &'node Node)> {
    let [output, cast, callee, paren, comma, ..] = nodes else {
        return None;
    };
    let start = output.span.begin.byte;
    let line = output.span.begin.line;
    let column = output.span.begin.column;
    if start <= previous
        || start <= body.span.begin.byte
        || line == 0
        || column == 0
        || output.id != expected_id
        || output.parent != body.id
        || output.kind != "call-expression"
        || output.type_name.as_deref() != Some("i32")
        || output.reference.as_deref() != Some("external:putchar")
        || output.operation.is_some()
        || !metadata_empty(output)
        || cast.id != output.id.checked_add(1)?
        || cast.parent != output.id
        || cast.kind != "cast-expression"
        || cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
        || cast.operation.as_deref() != Some("function-to-pointer")
        || cast.reference.is_some()
        || !metadata_empty(cast)
        || callee.id != cast.id.checked_add(1)?
        || callee.parent != cast.id
        || callee.kind != "declaration-reference-expression"
        || callee.type_name.as_deref() != Some("fn(i32)->i32")
        || callee.reference.as_deref() != Some("external:putchar")
        || callee.operation.is_some()
        || !metadata_empty(callee)
        || paren.id != callee.id.checked_add(1)?
        || paren.parent != output.id
        || paren.kind != "parenthesized-expression"
        || paren.type_name.as_deref() != Some("i32")
        || paren.reference.is_some()
        || paren.operation.is_some()
        || !metadata_empty(paren)
        || comma.id != paren.id.checked_add(1)?
    {
        return None;
    }
    let (comma_width, effects, last_end) = prove_discarded_comma_effects(
        nodes.get(4..)?,
        body,
        previous,
        comma.id,
        paren.id,
        local,
    )?;
    let end = last_end.checked_add(2)?;
    let width = 4usize.checked_add(comma_width)?;
    if end >= body.span.end.byte
        || !source_word(output, start, end, line, column)
        || !source_word(cast, start, start.checked_add(7)?, line, column)
        || !source_word(callee, start, start.checked_add(7)?, line, column)
        || !source_word(
            paren,
            start.checked_add(8)?,
            last_end.checked_add(1)?,
            line,
            column.checked_add(8)?,
        )
        || comma.span.begin.byte != start.checked_add(9)?
    {
        return None;
    }
    Some((width, effects, output))
}

// Pure local operands have no new guest input or output effect. Both Clang
// nodes must denote the current source-proven local and the same C extent.
fn prove_comma_local_value<'node>(
    nodes: &'node [Node],
    body: &Node,
    local: &LocalDeclaration<'_>,
    previous: u32,
    expected_id: u32,
    parent: u32,
) -> Option<&'node Node> {
    let [cast, reference] = nodes else {
        return None;
    };
    let start = cast.span.begin.byte;
    let end = start.checked_add(u32::try_from(local.name.len()).ok()?)?;
    let line = cast.span.begin.line;
    let column = cast.span.begin.column;
    (start > previous
        && start > local.declaration_end
        && end < body.span.end.byte
        && line > local.line
        && cast.id == expected_id
        && cast.parent == parent
        && cast.kind == "cast-expression"
        && cast.type_name.as_deref() == Some("i32")
        && cast.operation.as_deref() == Some("lvalue-to-rvalue")
        && cast.reference.is_none()
        && metadata_empty(cast)
        && source_word(cast, start, end, line, column)
        && reference.id == cast.id.checked_add(1)?
        && reference.parent == cast.id
        && reference.kind == "declaration-reference-expression"
        && reference.type_name.as_deref() == Some("i32")
        && reference.reference.as_deref()
            == Some(local.variable_reference.as_str())
        && reference.operation.is_none()
        && metadata_empty(reference)
        && source_word(reference, start, end, line, column))
    .then_some(cast)
}

// A left-associative C comma chain executes every operand, including
// discarded putchar(getchar()) results. The bounded grammar checks every
// call, source byte and Clang ancestor before admitting its guest effects.
#[expect(
    clippy::too_many_lines,
    reason = "verify each comma operand and Clang source coordinate"
)]
fn prove_discarded_comma_effects<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    first_parent: u32,
    local: Option<&LocalDeclaration<'node>>,
) -> Option<(usize, Vec<CommaEffect<'node>>, u32)> {
    let binary_count = nodes
        .iter()
        .take(16)
        .take_while(|node| node.kind == "binary-expression")
        .count();
    if binary_count == 0 || binary_count >= 16 {
        return None;
    }
    let operand_count = binary_count.checked_add(1)?;
    let binary_nodes = nodes.get(..binary_count)?;
    let first = binary_nodes.first()?;
    let start = first.span.begin.byte;
    let line = first.span.begin.line;
    let column = first.span.begin.column;
    if start <= previous
        || start <= body.span.begin.byte
        || line == 0
        || column == 0
    {
        return None;
    }
    for (index, node) in binary_nodes.iter().enumerate() {
        let parent = if index == 0 {
            first_parent
        } else {
            binary_nodes.get(index.checked_sub(1)?)?.id
        };
        if node.id != expected_id.checked_add(u32::try_from(index).ok()?)?
            || node.parent != parent
            || node.kind != "binary-expression"
            || node.type_name.as_deref() != Some("i32")
            || node.operation.as_deref() != Some(",")
            || node.reference.is_some()
            || !metadata_empty(node)
        {
            return None;
        }
    }
    let mut effects = Vec::with_capacity(operand_count);
    let mut cursor = binary_count;
    let mut last_end = previous;
    let mut seen_new_input = false;
    for index in 0..operand_count {
        let parent = if index < 2 {
            binary_nodes.last()?.id
        } else {
            binary_nodes.get(binary_count.checked_sub(index)?)?.id
        };
        let expected_leaf_id =
            expected_id.checked_add(u32::try_from(cursor).ok()?)?;
        let leaf = nodes.get(cursor)?;
        let (width, input, outputs, extent) =
            if leaf.reference.as_deref() == Some("external:putchar") {
                if !seen_new_input
                    && let Some(current_local) = local
                    && let Some((width, calls)) = prove_local_output_chain(
                        nodes.get(cursor..)?,
                        body,
                        current_local,
                        expected_leaf_id,
                        last_end,
                        parent,
                    )
                {
                    let extent = *calls.first()?;
                    (width, current_local.input, calls, extent)
                } else {
                    let (width, input, calls) =
                        super::nested_byte_echo::nested_call_in_parent(
                            nodes.get(cursor..)?,
                            body,
                            last_end,
                            expected_leaf_id,
                            parent,
                        )?;
                    seen_new_input = true;
                    let extent = *calls.first()?;
                    (width, input, calls, extent)
                }
            } else if leaf.kind == "cast-expression" {
                let current_local = local.filter(|_| !seen_new_input)?;
                let extent = prove_comma_local_value(
                    nodes.get(cursor..cursor.checked_add(2)?)?,
                    body,
                    current_local,
                    last_end,
                    expected_leaf_id,
                    parent,
                )?;
                (2, current_local.input, Vec::new(), extent)
            } else {
                let input = prove_input_call(
                    nodes.get(cursor..cursor.checked_add(3)?)?,
                    body,
                    last_end,
                    (expected_leaf_id, parent),
                )?;
                seen_new_input = true;
                (3, input, Vec::new(), input)
            };
        if extent.id != expected_leaf_id
            || extent.span.begin.line != line
            || extent.span.end.line != line
            || extent.span.begin.column
                != column
                    .checked_add(extent.span.begin.byte.checked_sub(start)?)?
            || (index > 0
                && !matches!(
                    extent.span.begin.byte.checked_sub(last_end)?,
                    1 | 2
                ))
        {
            return None;
        }
        cursor = cursor.checked_add(width)?;
        last_end = extent.span.end.byte;
        effects.push(CommaEffect { input, extent, outputs });
    }
    for (index, binary) in binary_nodes.iter().enumerate() {
        let right = effects.get(binary_count.checked_sub(index)?)?;
        let right_span = right.extent;
        if !source_word(binary, start, right_span.span.end.byte, line, column) {
            return None;
        }
    }
    Some((cursor, effects, last_end))
}

fn valid_local_variable(
    variable: &Node,
    declaration: &Node,
    reference: &str,
    input_end: u32,
) -> bool {
    variable.id == declaration.id.saturating_add(1)
        && variable.parent == declaration.id
        && variable.kind == "variable-declaration"
        && variable.type_name.as_deref() == Some("i32")
        && variable.reference.as_deref() == Some(reference)
        && variable.definition.as_deref() == Some("definition")
        && variable.linkage.as_deref() == Some("none")
        && variable.storage_class.as_deref() == Some("none")
        && matches!(
            variable.storage_duration,
            Some(super::StorageDuration::Automatic)
        )
        && variable.inline_specified.is_none()
        && variable.operation.is_none()
        && variable.literal.is_none()
        && variable.constant_integer.is_none()
        && source_word(
            variable,
            declaration.span.begin.byte,
            input_end,
            declaration.span.begin.line,
            declaration.span.begin.column,
        )
}

fn valid_local_name(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 64
        && name
            .bytes()
            .next()
            .is_some_and(|byte| byte.is_ascii_alphabetic() || byte == b'_')
        && name
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
}

#[expect(
    clippy::too_many_lines,
    reason = "check all five pinned Clang declaration nodes atomically"
)]
fn prove_local_declaration<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
) -> Option<LocalDeclaration<'node>> {
    let [declaration, variable, input, input_cast, input_callee] = nodes else {
        return None;
    };
    let start = declaration.span.begin.byte;
    let line = declaration.span.begin.line;
    let column = declaration.span.begin.column;
    let name = variable.name.as_deref()?;
    if !valid_local_name(name) {
        return None;
    }
    let name_len = u32::try_from(name.len()).ok()?;
    let name_start = start.checked_add(4)?;
    let input_start = name_start.checked_add(name_len)?.checked_add(3)?;
    let input_end = input_start.checked_add(9)?;
    let variable_reference = format!("{name}@{name_start}");
    let source_ok = start > previous
        && start > body.span.begin.byte
        && input_end < body.span.end.byte
        && declaration.parent == body.id
        && declaration.kind == "declaration-statement"
        && declaration.type_name.is_none()
        && declaration.reference.is_none()
        && declaration.operation.is_none()
        && metadata_empty(declaration)
        && source_word(
            declaration,
            start,
            input_end.checked_add(1)?,
            line,
            column,
        )
        && valid_local_variable(
            variable,
            declaration,
            &variable_reference,
            input_end,
        )
        && input.id == variable.id.checked_add(1)?
        && input.parent == variable.id
        && input.kind == "call-expression"
        && input.type_name.as_deref() == Some("i32")
        && input.reference.as_deref() == Some("external:getchar")
        && input.operation.is_none()
        && metadata_empty(input)
        && source_word(
            input,
            input_start,
            input_end,
            line,
            column.checked_add(input_start.checked_sub(start)?)?,
        )
        && input_cast.id == input.id.checked_add(1)?
        && input_cast.parent == input.id
        && input_cast.kind == "cast-expression"
        && input_cast.type_name.as_deref() == Some("ptr(fn()->i32)")
        && input_cast.operation.as_deref() == Some("function-to-pointer")
        && input_cast.reference.is_none()
        && metadata_empty(input_cast)
        && source_word(
            input_cast,
            input_start,
            input_start.checked_add(7)?,
            line,
            column.checked_add(input_start.checked_sub(start)?)?,
        )
        && input_callee.id == input_cast.id.checked_add(1)?
        && input_callee.parent == input_cast.id
        && input_callee.kind == "declaration-reference-expression"
        && input_callee.type_name.as_deref() == Some("fn()->i32")
        && input_callee.reference.as_deref() == Some("external:getchar")
        && input_callee.operation.is_none()
        && metadata_empty(input_callee)
        && source_word(
            input_callee,
            input_start,
            input_start.checked_add(7)?,
            line,
            column.checked_add(input_start.checked_sub(start)?)?,
        );
    source_ok.then_some(LocalDeclaration {
        declaration_end: declaration.span.end.byte,
        input,
        line,
        name,
        variable_reference,
    })
}

/// The exact read of the source-local value in the following output call.
#[expect(
    clippy::too_many_lines,
    reason = "check all five pinned Clang output nodes atomically"
)]
fn prove_local_output<'node>(
    nodes: &'node [Node],
    body: &Node,
    local: &LocalDeclaration<'_>,
    expected_id: u32,
    previous: u32,
    parent: u32,
) -> Option<&'node Node> {
    let [
        output,
        output_cast,
        output_callee,
        value_cast,
        value_reference,
    ] = nodes
    else {
        return None;
    };
    let name_len = u32::try_from(local.name.len()).ok()?;
    let output_start = output.span.begin.byte;
    let output_line = output.span.begin.line;
    let output_column = output.span.begin.column;
    let output_end = output_start.checked_add(9)?.checked_add(name_len)?;
    let arg_start = output_start.checked_add(8)?;
    let arg_end = arg_start.checked_add(name_len)?;
    let argument_column = output_column.checked_add(8)?;
    let source_ok = output_end < body.span.end.byte
        && output.id == expected_id
        && output.parent == parent
        && output.kind == "call-expression"
        && output.type_name.as_deref() == Some("i32")
        && output.reference.as_deref() == Some("external:putchar")
        && output.operation.is_none()
        && metadata_empty(output)
        && output_start > local.declaration_end
        && output_start > previous
        && output_line > local.line
        && source_word(
            output,
            output_start,
            output_end,
            output_line,
            output_column,
        )
        && output_cast.id == output.id.checked_add(1)?
        && output_cast.parent == output.id
        && output_cast.kind == "cast-expression"
        && output_cast.type_name.as_deref() == Some("ptr(fn(i32)->i32)")
        && output_cast.operation.as_deref() == Some("function-to-pointer")
        && output_cast.reference.is_none()
        && metadata_empty(output_cast)
        && source_word(
            output_cast,
            output_start,
            output_start.checked_add(7)?,
            output_line,
            output_column,
        )
        && output_callee.id == output_cast.id.checked_add(1)?
        && output_callee.parent == output_cast.id
        && output_callee.kind == "declaration-reference-expression"
        && output_callee.type_name.as_deref() == Some("fn(i32)->i32")
        && output_callee.reference.as_deref() == Some("external:putchar")
        && output_callee.operation.is_none()
        && metadata_empty(output_callee)
        && source_word(
            output_callee,
            output_start,
            output_start.checked_add(7)?,
            output_line,
            output_column,
        )
        && value_cast.id == output_callee.id.checked_add(1)?
        && value_cast.parent == output.id
        && value_cast.kind == "cast-expression"
        && value_cast.type_name.as_deref() == Some("i32")
        && value_cast.operation.as_deref() == Some("lvalue-to-rvalue")
        && value_cast.reference.is_none()
        && metadata_empty(value_cast)
        && source_word(
            value_cast,
            arg_start,
            arg_end,
            output_line,
            argument_column,
        )
        && value_reference.id == value_cast.id.checked_add(1)?
        && value_reference.parent == value_cast.id
        && value_reference.kind == "declaration-reference-expression"
        && value_reference.type_name.as_deref() == Some("i32")
        && value_reference.reference.as_deref()
            == Some(local.variable_reference.as_str())
        && value_reference.operation.is_none()
        && metadata_empty(value_reference)
        && source_word(
            value_reference,
            arg_start,
            arg_end,
            output_line,
            argument_column,
        );
    source_ok.then_some(output)
}

#[expect(
    clippy::too_many_lines,
    reason = "check nested source coordinates and ancestry together"
)]
fn prove_nested_local_output<'node>(
    nodes: &'node [Node],
    body: &Node,
    local: &LocalDeclaration<'_>,
    expected_id: u32,
    previous: u32,
    first_parent: u32,
) -> Option<OutputCallProof<'node>> {
    let outer = nodes.first()?;
    let start = outer.span.begin.byte;
    let line = outer.span.begin.line;
    let column = outer.span.begin.column;
    if start <= previous
        || start <= local.declaration_end
        || line <= local.line
        || start <= body.span.begin.byte
        || line == 0
        || column == 0
    {
        return None;
    }
    let depth = (0..MAX_NESTED_LOCAL_DEPTH)
        .take_while(|level| {
            nodes.get(level.saturating_mul(3)).is_some_and(|node| {
                node.kind == "call-expression"
                    && node.reference.as_deref() == Some("external:putchar")
            })
        })
        .count();
    if depth < 2 {
        return None;
    }
    let depth_u32 = u32::try_from(depth).ok()?;
    let name_len = u32::try_from(local.name.len()).ok()?;
    let argument_start = start.checked_add(depth_u32.checked_mul(8)?)?;
    let argument_end = argument_start.checked_add(name_len)?;
    let output_end = argument_end.checked_add(depth_u32)?;
    if output_end >= body.span.end.byte {
        return None;
    }
    let mut calls = Vec::with_capacity(depth);
    let mut parent = first_parent;
    for level in 0..depth {
        let offset = level.checked_mul(3)?;
        let [call, cast, reference] =
            nodes.get(offset..offset.checked_add(3)?)?
        else {
            return None;
        };
        let level_u32 = u32::try_from(level).ok()?;
        let call_start = start.checked_add(level_u32.checked_mul(8)?)?;
        let call_end = output_end.checked_sub(level_u32)?;
        let call_column = column.checked_add(level_u32.checked_mul(8)?)?;
        if call.id != expected_id.checked_add(u32::try_from(offset).ok()?)?
            || call.parent != parent
            || call.kind != "call-expression"
            || call.type_name.as_deref() != Some("i32")
            || call.reference.as_deref() != Some("external:putchar")
            || call.operation.is_some()
            || !metadata_empty(call)
            || !source_word(call, call_start, call_end, line, call_column)
            || cast.id != call.id.checked_add(1)?
            || cast.parent != call.id
            || cast.kind != "cast-expression"
            || cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
            || cast.operation.as_deref() != Some("function-to-pointer")
            || cast.reference.is_some()
            || !metadata_empty(cast)
            || !source_word(
                cast,
                call_start,
                call_start.checked_add(7)?,
                line,
                call_column,
            )
            || reference.id != cast.id.checked_add(1)?
            || reference.parent != cast.id
            || reference.kind != "declaration-reference-expression"
            || reference.type_name.as_deref() != Some("fn(i32)->i32")
            || reference.reference.as_deref() != Some("external:putchar")
            || reference.operation.is_some()
            || !metadata_empty(reference)
            || !source_word(
                reference,
                call_start,
                call_start.checked_add(7)?,
                line,
                call_column,
            )
        {
            return None;
        }
        calls.push(call);
        parent = call.id;
    }
    let offset = depth.checked_mul(3)?;
    let [value_cast, value_reference] =
        nodes.get(offset..offset.checked_add(2)?)?
    else {
        return None;
    };
    let argument_column = column.checked_add(depth_u32.checked_mul(8)?)?;
    if value_cast.id != expected_id.checked_add(u32::try_from(offset).ok()?)?
        || value_cast.parent != parent
        || value_cast.kind != "cast-expression"
        || value_cast.type_name.as_deref() != Some("i32")
        || value_cast.operation.as_deref() != Some("lvalue-to-rvalue")
        || value_cast.reference.is_some()
        || !metadata_empty(value_cast)
        || !source_word(
            value_cast,
            argument_start,
            argument_end,
            line,
            argument_column,
        )
        || value_reference.id != value_cast.id.checked_add(1)?
        || value_reference.parent != value_cast.id
        || value_reference.kind != "declaration-reference-expression"
        || value_reference.type_name.as_deref() != Some("i32")
        || value_reference.reference.as_deref()
            != Some(local.variable_reference.as_str())
        || value_reference.operation.is_some()
        || !metadata_empty(value_reference)
        || !source_word(
            value_reference,
            argument_start,
            argument_end,
            line,
            argument_column,
        )
    {
        return None;
    }
    Some((offset.checked_add(2)?, calls))
}

fn prove_local_output_chain<'node>(
    nodes: &'node [Node],
    body: &Node,
    local: &LocalDeclaration<'_>,
    expected_id: u32,
    previous: u32,
    parent: u32,
) -> Option<OutputCallProof<'node>> {
    if let Some(first) = nodes.get(..5)
        && let Some(call) = prove_local_output(
            first,
            body,
            local,
            expected_id,
            previous,
            parent,
        )
    {
        return Some((5, vec![call]));
    }
    prove_nested_local_output(nodes, body, local, expected_id, previous, parent)
}

// Only a source-proven `if (0)` or `if (1)` with one unbraced I/O
// statement can be projected. The selected arm still executes its input and
// output in Malbolge; a skipped arm executes neither, including getchar().
struct StaticIfProof<'node> {
    width: usize,
    selected: bool,
    input: Option<&'node Node>,
    // Source order is outer-to-inner for nested output calls.
    outputs: Vec<&'node Node>,
    end: u32,
}

#[expect(
    clippy::too_many_lines,
    reason = "prove the literal condition and every selected or skipped child"
)]
fn prove_static_if<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    local: Option<&LocalDeclaration<'node>>,
) -> Option<StaticIfProof<'node>> {
    let [conditional, literal, rest @ ..] = nodes else {
        return None;
    };
    let start = conditional.span.begin.byte;
    let line = conditional.span.begin.line;
    let column = conditional.span.begin.column;
    let value = literal.literal.as_deref()?;
    if start <= previous
        || start <= body.span.begin.byte
        || line == 0
        || column == 0
        || conditional.id != expected_id
        || conditional.parent != body.id
        || conditional.kind != "if-statement"
        || conditional.type_name.is_some()
        || conditional.reference.is_some()
        || conditional.operation.is_some()
        || !metadata_empty(conditional)
        || literal.id != conditional.id.checked_add(1)?
        || literal.parent != conditional.id
        || literal.kind != "integer-literal"
        || literal.type_name.as_deref() != Some("i32")
        || literal.operation.is_some()
        || literal.reference.is_some()
        || literal.name.is_some()
        || literal.definition.is_some()
        || literal.inline_specified.is_some()
        || literal.linkage.is_some()
        || literal.storage_class.is_some()
        || literal.storage_duration.is_some()
        || !matches!(value, "0" | "1")
        || literal.constant_integer.as_deref() != Some(value)
        || !source_word(
            literal,
            start.checked_add(4)?,
            start.checked_add(5)?,
            line,
            column.checked_add(4)?,
        )
    {
        return None;
    }
    let child = rest.first()?;
    let child_id = literal.id.checked_add(1)?;
    let (width, input, outputs) = if child.kind == "call-expression"
        && child.reference.as_deref() == Some("external:putchar")
    {
        if let Some(local) = local
            && let Some((width, calls)) = prove_local_output_chain(
                rest,
                body,
                local,
                child_id,
                previous,
                conditional.id,
            )
        {
            (width, None, calls)
        } else {
            let (width, input, calls) =
                super::nested_byte_echo::nested_call_in_parent(
                    rest,
                    body,
                    previous,
                    child_id,
                    conditional.id,
                )?;
            (width, Some(input), calls)
        }
    } else {
        let read = prove_input_call(
            rest.get(..3)?,
            body,
            previous,
            (child_id, conditional.id),
        )?;
        (3, Some(read), Vec::new())
    };
    let extent = outputs.first().copied().or(input)?;
    let end = extent.span.end.byte;
    if child.id != child_id
        || extent.span.begin.line != line
        || extent.span.end.line != line
        || child.span.begin.byte != start.checked_add(7)?
        || end >= body.span.end.byte
        || !source_word(conditional, start, end, line, column)
    {
        return None;
    }
    Some(StaticIfProof {
        width: width.checked_add(2)?,
        selected: value == "1",
        input,
        outputs,
        end,
    })
}

fn valid_envelope(input: &Artifact, function: &Node, body: &Node) -> bool {
    input.schema_version == 1
        && input.identity == super::EXPECTED_ARTIFACT
        && input.profile.abi_id == super::EXPECTED_ABI
        && input.profile.target_profile == super::EXPECTED_PROFILE
        && input.clang.version == "22.1.8"
        && input.clang.target == "wasm32-unknown-unknown"
        && input.clang.language == "c23"
        && !input.source.id.is_empty()
        && function.id == 1
        && function.parent == 0
        && function.kind == "function-declaration"
        && function
            .name
            .as_deref()
            .is_some_and(|name| !name.is_empty())
        && function.type_name.as_deref() == Some("fn()->void")
        && function.definition.as_deref() == Some("definition")
        && function.inline_specified == Some(false)
        && function.linkage.as_deref() == Some("external")
        && function.storage_class.as_deref() == Some("none")
        && function.storage_duration.is_none()
        && function.reference.is_none()
        && function.operation.is_none()
        && function.literal.is_none()
        && function.constant_integer.is_none()
        && body.id == 2
        && body.parent == 1
        && body.kind == "compound-statement"
        && body.type_name.is_none()
        && body.reference.is_none()
        && body.operation.is_none()
        && metadata_empty(body)
        && function.span.begin.byte < body.span.begin.byte
        && function.span.end == body.span.end
        && body.span.begin.line > 0
        && body.span.begin.column > 0
        && body.span.begin.byte < body.span.end.byte
}

/// Admit a source-authenticated successful-byte input/output trace.
///
/// Repeated local outputs do not read input again, but a discarded read
/// and the left operand of a comma expression consume input without writing
/// output. A later input invalidates any earlier live SSA identity. No
/// other guest effects or EOF behavior are admitted.
///
/// # Errors
///
/// Rejects missing source ancestry, noncanonical LLVM metadata, extra effects,
/// invalid source bounds and malformed canonical typed IR.
#[expect(
    clippy::redundant_pub_crate,
    clippy::too_many_lines,
    reason = "private source-checked typed SSA proof remains a single gate"
)]
pub(super) fn canonical_source_byte_echo(
    bytes: &[u8],
) -> Result<super::CanonicalGuestProjection, FrontendJsonError> {
    if bytes.is_empty() || bytes.len() > super::MAX_FRONTEND_JSON_BYTES {
        return Err(FrontendJsonError::Malformed);
    }
    let input: Artifact = serde_json::from_slice(bytes)
        .map_err(|_error| FrontendJsonError::Malformed)?;
    let [function, body, rest @ ..] = input.nodes.as_slice() else {
        return Err(FrontendJsonError::Unsupported);
    };
    if !valid_envelope(&input, function, body) || rest.is_empty() {
        return Err(FrontendJsonError::Unsupported);
    }
    let mut previous = body.span.begin.byte;
    let mut next_id = 3u32;
    let mut consumed = 0usize;
    let mut inputs = 0usize;
    let mut outputs = 0usize;
    let mut requires_latest = false;
    let mut local_names = HashSet::new();
    let mut latest_local: Option<(LocalDeclaration<'_>, ValueId)> = None;
    let mut instructions = Vec::new();
    while consumed < rest.len() {
        let first = rest.get(consumed).ok_or(FrontendJsonError::Unsupported)?;
        if outputs == MAX_SOURCE_OUTPUTS || first.id != next_id {
            return Err(FrontendJsonError::Unsupported);
        }
        if first.kind == "if-statement" {
            let proof = prove_static_if(
                rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?,
                body,
                previous,
                next_id,
                latest_local.as_ref().map(|(local, _)| local),
            )
            .ok_or(FrontendJsonError::Unsupported)?;
            if proof.selected {
                if inputs + usize::from(proof.input.is_some()) > MAX_ECHO_CALLS
                    || outputs + proof.outputs.len() > MAX_SOURCE_OUTPUTS
                {
                    return Err(FrontendJsonError::Unsupported);
                }
                let value = if let Some(input) = proof.input {
                    let value = ValueId::new(
                        u32::try_from(inputs)
                            .map_err(|_| FrontendJsonError::Unsupported)?,
                    );
                    instructions.push(LocatedInstruction::new(
                        Instruction::ByteInput {
                            result: value,
                            type_id: TypeId::new(0),
                        },
                        typed_span(&input.span),
                    ));
                    inputs += 1;
                    latest_local = None;
                    value
                } else {
                    latest_local
                        .as_ref()
                        .ok_or(FrontendJsonError::Unsupported)?
                        .1
                };
                for output in proof.outputs.iter().rev() {
                    instructions.push(LocatedInstruction::new(
                        Instruction::ByteOutput { value },
                        typed_span(&output.span),
                    ));
                }
                outputs += proof.outputs.len();
                requires_latest = true;
            }
            previous = proof.end;
            consumed = consumed
                .checked_add(proof.width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(proof.width)
                        .map_err(|_| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            continue;
        }
        if first.kind == "call-expression"
            && let Some((local, value)) = latest_local.as_ref()
            && let Some((width, calls)) = prove_local_output_chain(
                rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?,
                body,
                local,
                next_id,
                previous,
                body.id,
            )
        {
            if outputs
                .checked_add(calls.len())
                .is_none_or(|total| total > MAX_SOURCE_OUTPUTS)
            {
                return Err(FrontendJsonError::Unsupported);
            }
            // Reuse the same live input SSA, with no new guest read.
            for call in calls.iter().rev() {
                instructions.push(LocatedInstruction::new(
                    Instruction::ByteOutput { value: *value },
                    typed_span(&call.span),
                ));
            }
            requires_latest = true;
            outputs = outputs
                .checked_add(calls.len())
                .ok_or(FrontendJsonError::Unsupported)?;
            previous = calls
                .first()
                .ok_or(FrontendJsonError::Unsupported)?
                .span
                .end
                .byte;
            consumed = consumed
                .checked_add(width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_error| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            continue;
        }
        if first.kind == "call-expression"
            && first.reference.as_deref() == Some("external:putchar")
            && let Some((width, effects, output)) = prove_comma_output_effects(
                rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?,
                body,
                previous,
                next_id,
                latest_local.as_ref().map(|(local, _value)| local),
            )
        {
            let inner_outputs =
                effects.iter().map(|e| e.outputs.len()).sum::<usize>();
            if inputs
                .checked_add(effects.len())
                .is_none_or(|count| count > MAX_ECHO_CALLS)
                || outputs
                    .checked_add(inner_outputs)
                    .and_then(|count| count.checked_add(1))
                    .is_none_or(|count| count > MAX_SOURCE_OUTPUTS)
            {
                return Err(FrontendJsonError::Unsupported);
            }
            let (selected, read_new_input) = emit_comma_effects(
                &effects,
                latest_local.as_ref(),
                &mut inputs,
                &mut outputs,
                &mut instructions,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
            instructions.push(LocatedInstruction::new(
                Instruction::ByteOutput { value: selected },
                typed_span(&output.span),
            ));
            if read_new_input {
                latest_local = None;
            }
            previous = output.span.end.byte;
            consumed = consumed
                .checked_add(width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_error| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            outputs = outputs
                .checked_add(1)
                .ok_or(FrontendJsonError::Unsupported)?;
            requires_latest = true;
            continue;
        }
        if first.kind == "binary-expression"
            && let Some((width, effects, end)) = prove_discarded_comma_effects(
                rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?,
                body,
                previous,
                next_id,
                body.id,
                latest_local.as_ref().map(|(local, _value)| local),
            )
        {
            if inputs
                .checked_add(effects.len())
                .is_none_or(|count| count > MAX_ECHO_CALLS)
                || outputs
                    .checked_add(
                        effects.iter().map(|e| e.outputs.len()).sum::<usize>(),
                    )
                    .is_none_or(|count| count > MAX_SOURCE_OUTPUTS)
            {
                return Err(FrontendJsonError::Unsupported);
            }
            let (_selected, read_new_input) = emit_comma_effects(
                &effects,
                latest_local.as_ref(),
                &mut inputs,
                &mut outputs,
                &mut instructions,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
            // Only a fresh input clobbers the live accumulator-local value.
            if read_new_input {
                latest_local = None;
            }
            previous = end;
            consumed = consumed
                .checked_add(width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_error| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            requires_latest = true;
            continue;
        }
        if inputs == MAX_ECHO_CALLS {
            return Err(FrontendJsonError::Unsupported);
        }
        let id = ValueId::new(
            u32::try_from(inputs)
                .map_err(|_error| FrontendJsonError::Unsupported)?,
        );
        if first.kind == "call-expression"
            && first.reference.as_deref() == Some("external:getchar")
            && let Some(read) = rest
                .get(consumed..consumed.saturating_add(3))
                .and_then(|nodes| {
                    prove_input_call(nodes, body, previous, (next_id, body.id))
                })
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ByteInput {
                    result: id,
                    type_id: TypeId::new(0),
                },
                typed_span(&read.span),
            ));
            // This input overwrites the accumulator, so any preceding
            // local can no longer be materialized by the guest.
            latest_local = None;
            previous = read.span.end.byte;
            consumed = consumed
                .checked_add(3)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(3)
                .ok_or(FrontendJsonError::Unsupported)?;
            inputs = inputs
                .checked_add(1)
                .ok_or(FrontendJsonError::Unsupported)?;
            // Adjacent echo cannot represent an input without output.
            requires_latest = true;
            continue;
        }
        // A declaration is an input effect, not a declaration/output pair.
        // Keep its live byte until a genuinely newer input overwrites A;
        // the next source statement can be any separately proven consumer.
        if first.kind == "declaration-statement" {
            let declaration_nodes = rest
                .get(consumed..consumed.saturating_add(5))
                .ok_or(FrontendJsonError::Unsupported)?;
            let local =
                prove_local_declaration(declaration_nodes, body, previous)
                    .ok_or(FrontendJsonError::Unsupported)?;
            if !local_names.insert(local.name) {
                return Err(FrontendJsonError::Unsupported);
            }
            instructions.push(LocatedInstruction::new(
                Instruction::ByteInput {
                    result: id,
                    type_id: TypeId::new(0),
                },
                typed_span(&local.input.span),
            ));
            previous = local.declaration_end;
            latest_local = Some((local, id));
            consumed = consumed
                .checked_add(5)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(5)
                .ok_or(FrontendJsonError::Unsupported)?;
            inputs = inputs
                .checked_add(1)
                .ok_or(FrontendJsonError::Unsupported)?;
            requires_latest = true;
            continue;
        }
        let nodes =
            rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?;
        let (width, input_call, output_calls) = if let Some((read, write)) =
            nodes
                .get(..CALL_NODE_COUNT)
                .and_then(|slice| prove_call(slice, body, previous, body.id))
        {
            (CALL_NODE_COUNT, read, vec![write])
        } else {
            super::nested_byte_echo::nested_call(nodes, body, previous, next_id)
                .ok_or(FrontendJsonError::Unsupported)?
        };
        // A newer input destroys the previous live accumulator value.
        latest_local = None;
        if outputs
            .checked_add(output_calls.len())
            .is_none_or(|total| total > MAX_SOURCE_OUTPUTS)
        {
            return Err(FrontendJsonError::Unsupported);
        }
        instructions.push(LocatedInstruction::new(
            Instruction::ByteInput {
                result: id,
                type_id: TypeId::new(0),
            },
            typed_span(&input_call.span),
        ));
        for call in output_calls.iter().rev() {
            instructions.push(LocatedInstruction::new(
                Instruction::ByteOutput { value: id },
                typed_span(&call.span),
            ));
        }
        requires_latest |= output_calls.len() > 1;
        previous = output_calls
            .first()
            .ok_or(FrontendJsonError::Unsupported)?
            .span
            .end
            .byte;
        consumed = consumed.saturating_add(width);
        next_id = next_id
            .checked_add(
                u32::try_from(width)
                    .map_err(|_error| FrontendJsonError::Unsupported)?,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
        inputs = inputs.saturating_add(1);
        outputs = outputs
            .checked_add(output_calls.len())
            .ok_or(FrontendJsonError::Unsupported)?;
    }
    if previous >= body.span.end.byte {
        return Err(FrontendJsonError::Unsupported);
    }
    let void_function = FrontendReturnVoidFunction::new_fallthrough(
        FrontendFallthroughVoidFunctionSpec {
            body_span: span(&body.span),
            definition: String::from("definition"),
            function_span: span(&function.span),
            inline_specified: false,
            linkage: String::from("external"),
            name: function
                .name
                .clone()
                .ok_or(FrontendJsonError::Unsupported)?,
            signature: String::from("fn()->void"),
            storage_class: String::from("none"),
        },
    );
    let artifact = FrontendArtifact::new_void(
        FrontendArtifactSpec {
            abi_id: input.profile.abi_id,
            artifact_id: input.identity,
            clang_target: input.clang.target,
            clang_version: input.clang.version,
            functions: Vec::new(),
            language: input.clang.language,
            schema_version: input.schema_version,
            source_id: input.source.id,
            source_sha256: source_digest(&input.source.sha256)?,
            target_profile: input.profile.target_profile,
        },
        void_function,
    );
    let base = lower_frontend_artifact(&artifact)
        .map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    let original = base
        .functions()
        .first()
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    let block = original
        .blocks()
        .first()
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    let compiled = Function::new(FunctionSpec {
        blocks: vec![BasicBlock::new(BasicBlockSpec {
            id: block.id(),
            instructions,
            phis: block.phis().to_vec(),
            span: block.span(),
            terminator: block.terminator().clone(),
            terminator_span: block.terminator_span(),
        })],
        entry: original.entry(),
        id: original.id(),
        name: String::from(original.name()),
        parameters: original.parameters().to_vec(),
        signature: original.signature(),
        span: original.span(),
    });
    let module = Module::new(ModuleSpec {
        abi_id: String::from(base.abi_id()),
        format_version: base.format_version(),
        functions: vec![compiled],
        globals: base.globals().to_vec(),
        proof_obligations: base.proof_obligations().to_vec(),
        source_id: String::from(base.source_id()),
        source_sha256: *base.source_sha256(),
        target_profile: String::from(base.target_profile()),
        types: base.types().to_vec(),
    });
    let wire = canonical_bytes(&module)
        .map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    if canonical_module(&wire)
        .map_err(|_error| FrontendJsonError::InvalidTypedIr)?
        != module
    {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    Ok((
        wire,
        if requires_latest {
            FrontendGuestMode::LatestRead
        } else {
            FrontendGuestMode::AdjacentEcho
        },
    ))
}
