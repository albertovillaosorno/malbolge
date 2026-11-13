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
const MAX_STATIC_IF_DEPTH: usize = 4;
const MAX_STATIC_FOR_DEPTH: usize = 2;
const MAX_STATIC_PREDICATE_DEPTH: usize = 8;
const MAX_STATIC_PREDICATE_NODES: usize = 31;

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
    parent: u32,
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
        || output.parent != parent
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
    parent: u32,
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
        && declaration.parent == parent
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

// A plain C `int alias = live;` copies the currently resident input byte.
// It creates a new source binding but no guest instruction or host-time byte.
// Requiring original source bytes prevents a forged normalized AST from
// asserting an identity copy where the C expression performs other work.
#[expect(
    clippy::too_many_lines,
    reason = "authenticate every bound C alias node and its source spelling"
)]
fn prove_local_alias<'node>(
    nodes: &'node [Node],
    scope: (&Node, u32, u32),
    bound_local: &LocalDeclaration<'node>,
    source: &[u8],
) -> Option<LocalDeclaration<'node>> {
    let (body, previous, parent) = scope;
    let [declaration, variable, cast, reference] = nodes else {
        return None;
    };
    let name = variable.name.as_deref()?;
    if !valid_local_name(name) || name == bound_local.name {
        return None;
    }
    let start = declaration.span.begin.byte;
    let line = declaration.span.begin.line;
    let column = declaration.span.begin.column;
    let name_start = start.checked_add(4)?;
    let value_start = name_start
        .checked_add(u32::try_from(name.len()).ok()?)?
        .checked_add(3)?;
    let end =
        value_start.checked_add(u32::try_from(bound_local.name.len()).ok()?)?;
    let alias_reference = format!("{name}@{name_start}");
    let spelling = format!("int {name} = {};", bound_local.name);
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
    {
        return None;
    }
    let verified = start > previous
        && start > bound_local.declaration_end
        && end < body.span.end.byte
        && line > bound_local.line
        && column > 0
        && declaration.parent == parent
        && declaration.kind == "declaration-statement"
        && declaration.type_name.is_none()
        && declaration.reference.is_none()
        && declaration.operation.is_none()
        && metadata_empty(declaration)
        && source_word(declaration, start, end.checked_add(1)?, line, column)
        && valid_local_variable(variable, declaration, &alias_reference, end)
        && cast.id == variable.id.checked_add(1)?
        && cast.parent == variable.id
        && cast.kind == "cast-expression"
        && cast.type_name.as_deref() == Some("i32")
        && cast.operation.as_deref() == Some("lvalue-to-rvalue")
        && cast.reference.is_none()
        && metadata_empty(cast)
        && source_word(
            cast,
            value_start,
            end,
            line,
            column.checked_add(value_start.checked_sub(start)?)?,
        )
        && reference.id == cast.id.checked_add(1)?
        && reference.parent == cast.id
        && reference.kind == "declaration-reference-expression"
        && reference.type_name.as_deref() == Some("i32")
        && reference.reference.as_deref()
            == Some(bound_local.variable_reference.as_str())
        && reference.operation.is_none()
        && metadata_empty(reference)
        && source_word(
            reference,
            value_start,
            end,
            line,
            column.checked_add(value_start.checked_sub(start)?)?,
        );
    verified.then_some(LocalDeclaration {
        declaration_end: declaration.span.end.byte,
        input: bound_local.input,
        line,
        name,
        variable_reference: alias_reference,
    })
}

// A source-local `name = getchar();` overwrites the live byte with a fresh
// *guest* input. It is not a host-time write or a general assignable C object:
// the destination must still be the one resident accumulator-local binding.
// Prove all five pinned Clang nodes and the exact source bytes before emitting.
fn prove_local_input_reassignment<'node>(
    nodes: &'node [Node],
    scope: (&Node, u32, u32),
    local: &LocalDeclaration<'_>,
    source: &[u8],
) -> Option<&'node Node> {
    let (body, previous, parent) = scope;
    let [assignment, destination, input, _, _] = nodes else {
        return None;
    };
    let start = assignment.span.begin.byte;
    let line = assignment.span.begin.line;
    let column = assignment.span.begin.column;
    let input_start = start
        .checked_add(u32::try_from(local.name.len()).ok()?)?
        .checked_add(3)?;
    let end = input_start.checked_add(9)?;
    let spelling = format!("{} = getchar();", local.name);
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
        || start <= previous
        || start <= local.declaration_end
        || end >= body.span.end.byte
        || line <= local.line
        || column == 0
        || assignment.parent != parent
        || assignment.kind != "binary-expression"
        || assignment.type_name.as_deref() != Some("i32")
        || assignment.operation.as_deref() != Some("=")
        || assignment.reference.is_some()
        || !metadata_empty(assignment)
        || !source_word(assignment, start, end, line, column)
        || destination.id != assignment.id.checked_add(1)?
        || destination.parent != assignment.id
        || destination.kind != "declaration-reference-expression"
        || destination.type_name.as_deref() != Some("i32")
        || destination.reference.as_deref()
            != Some(local.variable_reference.as_str())
        || destination.operation.is_some()
        || !metadata_empty(destination)
        || !source_word(
            destination,
            start,
            input_start.checked_sub(3)?,
            line,
            column,
        )
        || input.id != destination.id.checked_add(1)?
        || prove_input_call(
            nodes.get(2..5)?,
            body,
            destination.span.end.byte,
            (input.id, assignment.id),
        )
        .is_none()
        || input.span.begin.byte != input_start
        || input.span.begin.line != line
        || input.span.begin.column
            != column.checked_add(input_start.checked_sub(start)?)?
    {
        return None;
    }
    Some(input)
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

// A successful getchar() returns a byte in [0, 255]. C's explicit
// `(unsigned char)` narrowing and integer promotion therefore preserve the
// exact runtime byte: the guest must not synthesize a second read or
// arithmetic. Authenticate both conversion nodes and the underlying live local
// read.
#[expect(
    clippy::too_many_lines,
    reason = "seven source-ordered Clang nodes constitute one cast proof"
)]
fn prove_unsigned_cast_local_output<'node>(
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
        promoted,
        narrowed,
        value_cast,
        value_reference,
    ] = nodes
    else {
        return None;
    };
    let name_len = u32::try_from(local.name.len()).ok()?;
    let start = output.span.begin.byte;
    let line = output.span.begin.line;
    let column = output.span.begin.column;
    let argument_start = start.checked_add(8)?;
    let value_start = argument_start.checked_add(15)?;
    let argument_end = value_start.checked_add(name_len)?;
    let end = argument_end.checked_add(1)?;
    if start <= previous
        || start <= local.declaration_end
        || line <= local.line
        || end >= body.span.end.byte
        || output.id != expected_id
        || output.parent != parent
        || output.kind != "call-expression"
        || output.type_name.as_deref() != Some("i32")
        || output.reference.as_deref() != Some("external:putchar")
        || output.operation.is_some()
        || !metadata_empty(output)
        || !source_word(output, start, end, line, column)
        || output_cast.id != output.id.checked_add(1)?
        || output_cast.parent != output.id
        || output_cast.kind != "cast-expression"
        || output_cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
        || output_cast.operation.as_deref() != Some("function-to-pointer")
        || output_cast.reference.is_some()
        || !metadata_empty(output_cast)
        || !source_word(output_cast, start, start.checked_add(7)?, line, column)
        || output_callee.id != output_cast.id.checked_add(1)?
        || output_callee.parent != output_cast.id
        || output_callee.kind != "declaration-reference-expression"
        || output_callee.type_name.as_deref() != Some("fn(i32)->i32")
        || output_callee.reference.as_deref() != Some("external:putchar")
        || output_callee.operation.is_some()
        || !metadata_empty(output_callee)
        || !source_word(
            output_callee,
            start,
            start.checked_add(7)?,
            line,
            column,
        )
        || promoted.id != output_callee.id.checked_add(1)?
        || promoted.parent != output.id
        || promoted.kind != "cast-expression"
        || promoted.type_name.as_deref() != Some("i32")
        || promoted.operation.as_deref() != Some("integral-cast")
        || promoted.reference.is_some()
        || !metadata_empty(promoted)
        || !source_word(
            promoted,
            argument_start,
            argument_end,
            line,
            column.checked_add(8)?,
        )
        || narrowed.id != promoted.id.checked_add(1)?
        || narrowed.parent != promoted.id
        || narrowed.kind != "cast-expression"
        || narrowed.type_name.as_deref() != Some("u8")
        || narrowed.operation.as_deref() != Some("integral-cast")
        || narrowed.reference.is_some()
        || !metadata_empty(narrowed)
        || !source_word(
            narrowed,
            argument_start,
            argument_end,
            line,
            column.checked_add(8)?,
        )
        || value_cast.id != narrowed.id.checked_add(1)?
        || value_cast.parent != narrowed.id
        || value_cast.kind != "cast-expression"
        || value_cast.type_name.as_deref() != Some("i32")
        || value_cast.operation.as_deref() != Some("lvalue-to-rvalue")
        || value_cast.reference.is_some()
        || !metadata_empty(value_cast)
        || !source_word(
            value_cast,
            value_start,
            argument_end,
            line,
            column.checked_add(23)?,
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
            value_start,
            argument_end,
            line,
            column.checked_add(23)?,
        )
    {
        return None;
    }
    Some(output)
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
    if let Some(first) = nodes.get(..7)
        && let Some(call) = prove_unsigned_cast_local_output(
            first,
            body,
            local,
            expected_id,
            previous,
            parent,
        )
    {
        return Some((7, vec![call]));
    }
    prove_nested_local_output(nodes, body, local, expected_id, previous, parent)
}

// A constant arm can contain several ordered, independently authenticated
// byte effects. A successful read invalidates any preceding guest-local alias.
#[derive(Clone, Copy)]
struct StaticInduction<'name> {
    reference: &'name str,
    value: i32,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum StaticLoopExit {
    Break,
    Continue,
    Return,
}

#[derive(Clone)]
struct StaticIfEffect<'node> {
    input: Option<&'node Node>,
    // Outer-to-inner Clang preorder; reverse to emit successful call returns.
    outputs: Vec<&'node Node>,
    // Return propagates to the function; break/continue stop at the inner
    // loop.
    loop_exit: Option<StaticLoopExit>,
}

struct StaticIfArm<'node> {
    width: usize,
    effects: Vec<StaticIfEffect<'node>>,
    begin: u32,
    begin_line: u32,
    begin_column: u32,
    end: u32,
    end_line: u32,
    end_column: u32,
    braced: bool,
}

// Both discarded comma statements and comma-argument calls use the same
// verified operand trace. Only the latter adds one final outer output.
fn static_comma_effects<'node>(
    comma_effects: Vec<CommaEffect<'node>>,
    outer_output: Option<&'node Node>,
    local: Option<&LocalDeclaration<'node>>,
) -> Option<Vec<StaticIfEffect<'node>>> {
    let last = comma_effects.len().checked_sub(1)?;
    Some(
        comma_effects
            .into_iter()
            .enumerate()
            .map(|(index, effect)| {
                let input = if local.is_some_and(|declaration| {
                    declaration.input.id == effect.input.id
                }) {
                    None
                } else {
                    Some(effect.input)
                };
                let mut outputs = effect.outputs;
                if index == last
                    && let Some(output) = outer_output
                {
                    outputs.insert(0, output);
                }
                StaticIfEffect {
                    input,
                    outputs,
                    loop_exit: None,
                }
            })
            .collect(),
    )
}

fn prove_static_if_statement<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    parent: u32,
    local: Option<&LocalDeclaration<'node>>,
    depth: usize,
    allow_new_local: bool,
    for_depth: usize,
    induction: Option<StaticInduction<'_>>,
    source: Option<&[u8]>,
) -> Option<(usize, Vec<StaticIfEffect<'node>>, u32)> {
    let child = nodes.first()?;
    if child.kind == "for-statement" {
        if for_depth >= MAX_STATIC_FOR_DEPTH {
            return None;
        }
        let proof = prove_static_for(
            nodes,
            body,
            previous,
            expected_id,
            parent,
            for_depth.checked_add(1)?,
            source,
        )?;
        if proof.effects.len() > 16 {
            return None;
        }
        return Some((proof.width, proof.effects, proof.end));
    }
    if matches!(
        child.kind.as_str(),
        "break-statement" | "continue-statement" | "return-statement"
    ) {
        // The semicolon lies outside the Clang keyword extent. Only a
        // void `return;` can terminate the containing function from any depth.
        let (keyword_width, exit) = match child.kind.as_str() {
            "break-statement" => (5, StaticLoopExit::Break),
            "continue-statement" => (8, StaticLoopExit::Continue),
            "return-statement" => (6, StaticLoopExit::Return),
            _ => return None,
        };
        let start = child.span.begin.byte;
        let end = start.checked_add(keyword_width)?;
        if (for_depth == 0 && exit != StaticLoopExit::Return)
            || start <= previous
            || end >= body.span.end.byte
            || child.id != expected_id
            || child.parent != parent
            || child.type_name.is_some()
            || child.reference.is_some()
            || child.operation.is_some()
            || !metadata_empty(child)
            || !source_word(
                child,
                start,
                end,
                child.span.begin.line,
                child.span.begin.column,
            )
        {
            return None;
        }
        return Some((
            1,
            vec![StaticIfEffect {
                input: None,
                outputs: Vec::new(),
                loop_exit: Some(exit),
            }],
            end,
        ));
    }
    if child.kind == "if-statement" {
        let proof = prove_static_if(
            nodes,
            body,
            previous,
            expected_id,
            parent,
            local,
            depth.checked_add(1)?,
            allow_new_local,
            for_depth,
            induction,
            source,
        )?;
        return Some((
            proof.width,
            if proof.selected {
                proof.effects
            } else {
                Vec::new()
            },
            proof.end,
        ));
    }
    // Authenticate a complete comma argument in the same branch parent as
    // ordinary calls; materialize each operand in C evaluation order.
    let comma_proof = if child.kind == "call-expression"
        && child.reference.as_deref() == Some("external:putchar")
    {
        prove_comma_output_effects(
            nodes,
            body,
            previous,
            expected_id,
            parent,
            local,
        )
    } else {
        None
    };
    if let Some((width, comma_effects, output)) = comma_proof {
        let effects = static_comma_effects(comma_effects, Some(output), local)?;
        return Some((width, effects, output.span.end.byte));
    }
    if child.kind == "binary-expression"
        && child.operation.as_deref() == Some("=")
    {
        let read = prove_local_input_reassignment(
            nodes.get(..5)?,
            (body, previous, parent),
            local?,
            source?,
        )?;
        return (child.id == expected_id).then_some((
            5,
            vec![StaticIfEffect {
                input: Some(read),
                outputs: Vec::new(),
                loop_exit: None,
            }],
            child.span.end.byte,
        ));
    }
    if child.kind == "binary-expression" {
        let (width, comma_effects, end) = prove_discarded_comma_effects(
            nodes,
            body,
            previous,
            expected_id,
            parent,
            local,
        )?;
        return Some((
            width,
            static_comma_effects(comma_effects, None, local)?,
            end,
        ));
    }
    let (width, input, outputs) = if child.kind == "call-expression"
        && child.reference.as_deref() == Some("external:putchar")
    {
        if let Some(local) = local
            && let Some((width, calls)) = prove_local_output_chain(
                nodes,
                body,
                local,
                expected_id,
                previous,
                parent,
            )
        {
            (width, None, calls)
        } else {
            let (width, input, calls) =
                super::nested_byte_echo::nested_call_in_parent(
                    nodes,
                    body,
                    previous,
                    expected_id,
                    parent,
                )?;
            (width, Some(input), calls)
        }
    } else {
        let read = prove_input_call(
            nodes.get(..3)?,
            body,
            previous,
            (expected_id, parent),
        )?;
        (3, Some(read), Vec::new())
    };
    let end = outputs.first().copied().or(input)?.span.end.byte;
    (child.id == expected_id).then_some((
        width,
        vec![StaticIfEffect {
            input,
            outputs,
            loop_exit: None,
        }],
        end,
    ))
}

// Source-authenticate both one-line and canonical one-statement-per-line
// compound arms, including the unselected branch. Each effect must have an
// exact byte gap, line, column, ID and parent; no other C statement is erased.
fn prove_static_if_arm<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    parent: u32,
    local: Option<&LocalDeclaration<'node>>,
    depth: usize,
    conditional_column: u32,
    allow_new_local: bool,
    for_depth: usize,
    induction: Option<StaticInduction<'_>>,
    source: Option<&[u8]>,
) -> Option<StaticIfArm<'node>> {
    let child = nodes.first()?;
    if child.kind == "if-statement" {
        let proof = prove_static_if(
            nodes,
            body,
            previous,
            expected_id,
            parent,
            local,
            depth.checked_add(1)?,
            allow_new_local,
            for_depth,
            induction,
            source,
        )?;
        return Some(StaticIfArm {
            width: proof.width,
            effects: if proof.selected {
                proof.effects
            } else {
                Vec::new()
            },
            begin: child.span.begin.byte,
            begin_line: child.span.begin.line,
            begin_column: child.span.begin.column,
            end: proof.end,
            end_line: child.span.end.line,
            end_column: child.span.end.column,
            braced: false,
        });
    }
    if child.kind != "compound-statement" {
        let (width, effects, end) = prove_static_if_statement(
            nodes,
            body,
            previous,
            expected_id,
            parent,
            local,
            depth,
            allow_new_local,
            for_depth,
            induction,
            source,
        )?;
        return Some(StaticIfArm {
            width,
            effects,
            begin: child.span.begin.byte,
            begin_line: child.span.begin.line,
            begin_column: child.span.begin.column,
            end,
            end_line: child.span.end.line,
            end_column: child.span.end.column,
            braced: false,
        });
    }
    let begin = child.span.begin.byte;
    let end = child.span.end.byte;
    let line = child.span.begin.line;
    let column = child.span.begin.column;
    let multiline = child.span.end.line > line;
    let span_is_canonical = if multiline {
        child.span.end.column == conditional_column.checked_add(1)?
    } else {
        source_word(child, begin, end, line, column)
    };
    if begin <= previous
        || end >= body.span.end.byte
        || line == 0
        || column == 0
        || child.id != expected_id
        || child.parent != parent
        || child.type_name.is_some()
        || child.reference.is_some()
        || child.operation.is_some()
        || !metadata_empty(child)
        || !span_is_canonical
    {
        return None;
    }
    let mut cursor = 1usize;
    let mut effect_end = begin;
    let mut effects = Vec::new();
    let mut statement_count = 0usize;
    let mut expected_line = line.checked_add(1)?;
    let mut previous_includes_terminator = false;
    let mut local_is_live = local.is_some();
    let mut declared_local: Option<LocalDeclaration<'node>> = None;
    loop {
        if statement_count >= 16 || effects.len() >= 16 {
            return None;
        }
        let statement = nodes.get(cursor)?;
        let gap = if multiline {
            conditional_column
                .checked_add(5)?
                .checked_sub(u32::from(previous_includes_terminator))?
        } else {
            2
        };
        if statement.span.begin.byte != effect_end.checked_add(gap)?
            || (multiline
                && (statement.span.begin.line != expected_line
                    || statement.span.begin.column
                        != conditional_column.checked_add(4)?))
        {
            return None;
        }
        let declares_local =
            allow_new_local && statement.kind == "declaration-statement";
        let alias = if declares_local && local_is_live {
            declared_local.as_ref().or(local).and_then(|live| {
                source.and_then(|witness| {
                    prove_local_alias(
                        nodes.get(cursor..cursor.checked_add(4)?)?,
                        (body, effect_end, child.id),
                        live,
                        witness,
                    )
                })
            })
        } else {
            None
        };
        let (width, statement_effects, statement_end) =
            if let Some(alias) = alias {
                let end = alias.declaration_end;
                declared_local = Some(alias);
                (4, Vec::new(), end)
            } else if declares_local {
                // One new automatic local is initialized by an actual guest
                // input on every loop iteration, never once at compile time.
                // It is valid only until a later input overwrites the guest A.
                if local.is_some() || declared_local.is_some() {
                    return None;
                }
                let declaration = prove_local_declaration(
                    nodes.get(cursor..cursor.checked_add(5)?)?,
                    body,
                    effect_end,
                    child.id,
                )?;
                if declaration.input.id != statement.id.checked_add(2)? {
                    return None;
                }
                let end = declaration.declaration_end;
                let read = declaration.input;
                declared_local = Some(declaration);
                local_is_live = true;
                (
                    5,
                    vec![StaticIfEffect {
                        input: Some(read),
                        outputs: Vec::new(),
                        loop_exit: None,
                    }],
                    end,
                )
            } else {
                prove_static_if_statement(
                    nodes.get(cursor..)?,
                    body,
                    effect_end,
                    expected_id.checked_add(u32::try_from(cursor).ok()?)?,
                    child.id,
                    declared_local.as_ref().or(local).filter(|_| local_is_live),
                    depth,
                    allow_new_local,
                    for_depth,
                    induction,
                    source,
                )?
            };
        if statement_end >= end {
            return None;
        }
        // Declarations include their trailing `;` in the Clang extent;
        // braced nested ifs end at `}`. Both leave one less separator byte
        // than an expression whose terminating `;` is outside its span.
        previous_includes_terminator = statement.kind
            == "declaration-statement"
            || (matches!(
                statement.kind.as_str(),
                "if-statement" | "for-statement"
            ) && statement.span.end.line > statement.span.begin.line);
        expected_line = statement.span.end.line.checked_add(1)?;
        if !declares_local
            && !(statement.kind == "binary-expression"
                && statement.operation.as_deref() == Some("="))
        {
            local_is_live &= statement_effects
                .iter()
                .all(|effect| effect.input.is_none());
        }
        effects.extend(statement_effects);
        statement_count = statement_count.checked_add(1)?;
        if effects.len() > 16 {
            return None;
        }
        cursor = cursor.checked_add(width)?;
        effect_end = statement_end;
        let end_gap = if multiline {
            conditional_column
                .checked_add(2)?
                .checked_sub(u32::from(previous_includes_terminator))?
        } else {
            3
        };
        if effect_end.checked_add(end_gap)? == end {
            if multiline && child.span.end.line != expected_line {
                return None;
            }
            break;
        }
    }
    Some(StaticIfArm {
        width: cursor,
        effects,
        begin,
        begin_line: line,
        begin_column: column,
        end,
        end_line: child.span.end.line,
        end_column: child.span.end.column,
        braced: true,
    })
}

// The induction value is statically proven for a canonical finite C loop.
// Only the loop body effects are repeated: guest input and output still run
// at execution time, with no host-side byte computation or replay.
struct StaticForProof<'node> {
    width: usize,
    effects: Vec<StaticIfEffect<'node>>,
    end: u32,
}

// A closed, unit-step for loop with a fresh automatic `i`:
//     for (int i = 0; i < N; ++i) {
//     for (int i = 1; i <= N; i++) {
//     for (int i = 4; i >= 1; i--) {
//     for (int i = 4; i > 0; --i) {
//     for (int i = 4; i >= 1; i -= 1) {
//         <source-proven byte-effect statements>
//     }
// Ascending starts may be 0–99; descending starts remain 1–99.
// Both directions admit 0–16 finite trips.
// Equal-width `!=` is
// intentionally refused: its normalized operator alone cannot authenticate
// the spelling of an inclusive bound.
// Both the induction arithmetic and all body statements are authenticated
// against the pinned Clang preorder before any target instructions exist.
#[expect(
    clippy::too_many_lines,
    reason = "the complete Clang induction and body ancestry is one proof"
)]
fn prove_static_for<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    parent: u32,
    for_depth: usize,
    source: Option<&[u8]>,
) -> Option<StaticForProof<'node>> {
    let [
        loop_node,
        declaration,
        variable,
        initial,
        condition,
        read_cast,
        read_variable,
        bound,
        increment,
        increment_variable,
        rest @ ..,
    ] = nodes
    else {
        return None;
    };
    let start = loop_node.span.begin.byte;
    let line = loop_node.span.begin.line;
    let column = loop_node.span.begin.column;
    let declaration_start = start.checked_add(5)?;
    // The pinned single `int i` declarator has a fixed prefix, but the
    // canonical decimal initializer may occupy one or two source columns.
    let initial_width =
        u32::try_from(initial.literal.as_deref()?.len()).ok()?;
    if !(1..=2).contains(&initial_width) {
        return None;
    }
    let declaration_end = start.checked_add(14)?.checked_add(initial_width)?;
    let variable_end = declaration_end.checked_sub(1)?;
    let condition_start = declaration_end.checked_add(1)?;
    let condition_column =
        column.checked_add(15)?.checked_add(initial_width)?;
    let condition_operator = condition.operation.as_deref()?;
    let (ascending, inclusive, operator_width) = match condition_operator {
        "<" => (true, false, 1u32),
        "<=" => (true, true, 2u32),
        ">" => (false, false, 1u32),
        ">=" => (false, true, 2u32),
        _ => return None,
    };
    let bound_start = condition_start.checked_add(3 + operator_width)?;
    let increment_start = bound.span.end.byte.checked_add(2)?;
    let compound_increment = increment.kind == "compound-assignment-expression";
    let assigned_increment = increment.kind == "binary-expression";
    let increment_length = if assigned_increment {
        9
    } else if compound_increment {
        6
    } else {
        3
    };
    let increment_end = increment_start.checked_add(increment_length)?;
    let arm_start = increment_end.checked_add(2)?;
    let variable_reference = format!("i@{}", declaration_start.checked_add(4)?);
    let initial_value = prove_decimal_condition_operand(
        initial,
        expected_id.checked_add(3)?,
        variable.id,
        start.checked_add(13)?,
        line,
        column.checked_add(13)?,
    )?;
    // Only source-shaped unit steps in the comparison's direction are
    // admitted: ++i, i++, i += 1, i = i + 1 and their reverse forms.
    if start <= previous
        || start <= body.span.begin.byte
        || line == 0
        || column == 0
        || loop_node.id != expected_id
        || loop_node.parent != parent
        || for_depth == 0
        || for_depth > MAX_STATIC_FOR_DEPTH
        || loop_node.kind != "for-statement"
        || loop_node.type_name.is_some()
        || loop_node.reference.is_some()
        || loop_node.operation.is_some()
        || !metadata_empty(loop_node)
        || declaration.id != expected_id.checked_add(1)?
        || declaration.parent != loop_node.id
        || declaration.kind != "declaration-statement"
        || declaration.type_name.is_some()
        || declaration.reference.is_some()
        || declaration.operation.is_some()
        || !metadata_empty(declaration)
        || !source_word(
            declaration,
            declaration_start,
            declaration_end,
            line,
            column.checked_add(5)?,
        )
        || variable.id != expected_id.checked_add(2)?
        || variable.parent != declaration.id
        || variable.kind != "variable-declaration"
        || variable.name.as_deref() != Some("i")
        || variable.type_name.as_deref() != Some("i32")
        || variable.reference.as_deref() != Some(variable_reference.as_str())
        || variable.definition.as_deref() != Some("definition")
        || variable.linkage.as_deref() != Some("none")
        || variable.storage_class.as_deref() != Some("none")
        || !matches!(
            variable.storage_duration,
            Some(super::StorageDuration::Automatic)
        )
        || variable.operation.is_some()
        || variable.literal.is_some()
        || variable.constant_integer.is_some()
        || variable.inline_specified.is_some()
        || !source_word(
            variable,
            declaration_start,
            variable_end,
            line,
            column.checked_add(5)?,
        )
        || if ascending {
            !(0..=99).contains(&initial_value)
        } else {
            !(1..=99).contains(&initial_value)
        }
        || condition.id != expected_id.checked_add(4)?
        || condition.parent != loop_node.id
        || condition.kind != "binary-expression"
        || condition.type_name.as_deref() != Some("i32")
        || !metadata_empty(condition)
        || !source_word(
            condition,
            condition_start,
            bound.span.end.byte,
            line,
            condition_column,
        )
        || read_cast.id != expected_id.checked_add(5)?
        || read_cast.parent != condition.id
        || read_cast.kind != "cast-expression"
        || read_cast.type_name.as_deref() != Some("i32")
        || read_cast.operation.as_deref() != Some("lvalue-to-rvalue")
        || !metadata_empty(read_cast)
        || !source_word(
            read_cast,
            condition_start,
            condition_start.checked_add(1)?,
            line,
            condition_column,
        )
        || read_variable.id != expected_id.checked_add(6)?
        || read_variable.parent != read_cast.id
        || read_variable.kind != "declaration-reference-expression"
        || read_variable.type_name.as_deref() != Some("i32")
        || read_variable.reference.as_deref()
            != Some(variable_reference.as_str())
        || read_variable.operation.is_some()
        || !metadata_empty(read_variable)
        || read_variable.span != read_cast.span
        || bound.span.begin.byte != bound_start
        || bound.span.begin.column
            != condition_column.checked_add(3 + operator_width)?
        || increment.id != expected_id.checked_add(8)?
        || increment.parent != loop_node.id
        || increment.kind
            != if assigned_increment {
                "binary-expression"
            } else if compound_increment {
                "compound-assignment-expression"
            } else {
                "unary-expression"
            }
        || increment.type_name.as_deref() != Some("i32")
        || increment.operation.as_deref()
            != Some(if assigned_increment {
                "="
            } else {
                match (ascending, compound_increment) {
                    (true, true) => "+=",
                    (true, false) => "++",
                    (false, true) => "-=",
                    (false, false) => "--",
                }
            })
        || !metadata_empty(increment)
        || !source_word(
            increment,
            increment_start,
            increment_end,
            line,
            bound.span.end.column.checked_add(2)?,
        )
        || increment_variable.id != expected_id.checked_add(9)?
        || increment_variable.parent != increment.id
        || increment_variable.kind != "declaration-reference-expression"
        || increment_variable.type_name.as_deref() != Some("i32")
        || increment_variable.reference.as_deref()
            != Some(variable_reference.as_str())
        || increment_variable.operation.is_some()
        || !metadata_empty(increment_variable)
        || !(source_word(
            increment_variable,
            increment_start,
            increment_start.checked_add(1)?,
            line,
            bound.span.end.column.checked_add(2)?,
        ) || (!compound_increment
            && source_word(
                increment_variable,
                increment_start.checked_add(2)?,
                increment_end,
                line,
                bound.span.end.column.checked_add(4)?,
            )))
    {
        return None;
    }
    // For `i = i + 1`, authenticate every child of the assignment and
    // arithmetic subtree: neither an unrelated local nor a hidden effect
    // can supply the right-hand side. Guest values remain runtime bytes.
    let (rest, arm_id_offset) = if assigned_increment {
        let [arithmetic, read, variable, one, tail @ ..] = rest else {
            return None;
        };
        let rhs_start = increment_start.checked_add(4)?;
        let rhs_column = bound.span.end.column.checked_add(6)?;
        if arithmetic.id != expected_id.checked_add(10)?
            || arithmetic.parent != increment.id
            || arithmetic.kind != "binary-expression"
            || arithmetic.type_name.as_deref() != Some("i32")
            || arithmetic.operation.as_deref()
                != Some(if ascending {
                    "+"
                } else {
                    "-"
                })
            || arithmetic.reference.is_some()
            || !metadata_empty(arithmetic)
            || !source_word(
                arithmetic,
                rhs_start,
                increment_end,
                line,
                rhs_column,
            )
            || read.id != expected_id.checked_add(11)?
            || read.parent != arithmetic.id
            || read.kind != "cast-expression"
            || read.type_name.as_deref() != Some("i32")
            || read.operation.as_deref() != Some("lvalue-to-rvalue")
            || read.reference.is_some()
            || !metadata_empty(read)
            || !source_word(
                read,
                rhs_start,
                rhs_start.checked_add(1)?,
                line,
                rhs_column,
            )
            || variable.id != expected_id.checked_add(12)?
            || variable.parent != read.id
            || variable.kind != "declaration-reference-expression"
            || variable.type_name.as_deref() != Some("i32")
            || variable.reference.as_deref()
                != Some(variable_reference.as_str())
            || variable.operation.is_some()
            || !metadata_empty(variable)
            || variable.span != read.span
            || prove_decimal_condition_operand(
                one,
                expected_id.checked_add(13)?,
                arithmetic.id,
                increment_start.checked_add(8)?,
                line,
                bound.span.end.column.checked_add(10)?,
            )? != 1
        {
            return None;
        }
        (tail, 14)
    } else if compound_increment {
        // The additional compound-assignment child must be exactly one.
        let (one, tail) = rest.split_first()?;
        if prove_decimal_condition_operand(
            one,
            expected_id.checked_add(10)?,
            increment.id,
            increment_start.checked_add(5)?,
            line,
            bound.span.end.column.checked_add(7)?,
        )? != 1
        {
            return None;
        }
        (tail, 11)
    } else {
        (rest, 10)
    };
    let bound_value = prove_decimal_condition_operand(
        bound,
        expected_id.checked_add(7)?,
        condition.id,
        bound_start,
        line,
        condition_column.checked_add(3 + operator_width)?,
    )?;
    // Include the bound on either signed direction only for <= or >=.
    // A false initial condition is a real, finite zero-trip loop.
    let trip_count = if ascending {
        bound_value.checked_sub(initial_value)?
    } else {
        initial_value.checked_sub(bound_value)?
    }
    .checked_add(i32::from(inclusive))?;
    let iterations = usize::try_from(trip_count.max(0)).ok()?;
    if iterations > 16 {
        return None;
    }
    // Authenticate the whole body even when the source condition is false
    // initially. Its Clang nodes cannot be skipped as an untrusted island;
    // only zero guest effects may be emitted for that validation pass.
    let mut effects = Vec::new();
    let mut arm_width = None;
    let mut arm_end = None;
    for iteration in 0..iterations.max(1) {
        let arm = prove_static_if_arm(
            rest,
            body,
            increment_end,
            expected_id.checked_add(arm_id_offset)?,
            loop_node.id,
            None,
            0,
            column,
            true,
            for_depth,
            Some(StaticInduction {
                reference: &variable_reference,
                value: if ascending {
                    initial_value.checked_add(i32::try_from(iteration).ok()?)?
                } else {
                    initial_value.checked_sub(i32::try_from(iteration).ok()?)?
                },
            }),
            source,
        )?;
        if !arm.braced
            || arm.begin != arm_start
            || arm.begin_line != line
            || arm.begin_column
                != bound.span.end.column.checked_add(increment_length + 4)?
            || loop_node.span.end.byte != arm.end
            || loop_node.span.end.line != arm.end_line
            || loop_node.span.end.column != arm.end_column
            || arm.end >= body.span.end.byte
        {
            return None;
        }
        arm_width = Some(arm.width);
        arm_end = Some(arm.end);
        if iterations == 0 {
            continue;
        }
        // The nearest selected exit decides this trip. A continue skips
        // only this trip's suffix; a break stops all later trips.
        let mut trip = arm.effects;
        let exit = trip.iter().position(|effect| effect.loop_exit.is_some());
        let exit_kind = if let Some(index) = exit {
            let exit = trip[index].clone();
            let kind = exit.loop_exit;
            trip.truncate(index);
            // A selected return must survive inner loops to stop the entire
            // function. Break and continue are consumed at this loop level.
            if exit.loop_exit == Some(StaticLoopExit::Return) {
                trip.push(exit);
            }
            kind
        } else {
            None
        };
        effects.extend(trip);
        if effects.len() > MAX_SOURCE_OUTPUTS {
            return None;
        }
        if matches!(
            exit_kind,
            Some(StaticLoopExit::Break | StaticLoopExit::Return)
        ) {
            break;
        }
    }
    Some(StaticForProof {
        width: usize::try_from(arm_id_offset)
            .ok()?
            .checked_add(arm_width?)?,
        effects,
        end: arm_end?,
    })
}

struct StaticIfProof<'node> {
    width: usize,
    selected: bool,
    effects: Vec<StaticIfEffect<'node>>,
    end: u32,
}

// Match a source-spelled nonnegative decimal i32 operand, rather than
// accepting an evaluated constant divorced from its source coordinates.
fn prove_decimal_condition_operand(
    node: &Node,
    expected_id: u32,
    parent: u32,
    start: u32,
    line: u32,
    column: u32,
) -> Option<i32> {
    let spelling = node.literal.as_deref()?;
    let value = spelling.parse::<i32>().ok()?;
    let end = start.checked_add(u32::try_from(spelling.len()).ok()?)?;
    (value >= 0
        && value.to_string() == spelling
        && node.id == expected_id
        && node.parent == parent
        && node.kind == "integer-literal"
        && node.type_name.as_deref() == Some("i32")
        && node.operation.is_none()
        && node.reference.is_none()
        && node.name.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
        && node.constant_integer.as_deref() == Some(spelling)
        && source_word(node, start, end, line, column))
    .then_some(value)
}

// A recursive C predicate is bound to both its Clang ancestry and exact
// source coordinates. No interpreter reads source bytes or guest input.
#[derive(Clone, Copy)]
struct StaticValueLocation {
    id: u32,
    parent: u32,
    start: u32,
    line: u32,
    column: u32,
    depth: usize,
}

impl StaticValueLocation {
    fn child(self, id: u32, start: u32, column: u32) -> Option<Self> {
        Some(Self {
            id,
            parent: self.id,
            start,
            column,
            depth: self.depth.checked_add(1)?,
            ..self
        })
    }
}

// The source extent of a parenthesized value differs from its final leaf.
fn prove_static_prefix(
    nodes: &[Node],
    at: StaticValueLocation,
) -> Option<(usize, i32, u32)> {
    let node = nodes.first()?;
    let parenthesized = node.kind == "parenthesized-expression";
    if !parenthesized
        && (node.kind != "unary-expression"
            || node.operation.as_deref() != Some("!"))
    {
        return None;
    }
    if parenthesized && node.operation.is_some() {
        return None;
    }
    let child = at.child(
        at.id.checked_add(1)?,
        at.start.checked_add(1)?,
        at.column.checked_add(1)?,
    )?;
    let (inner_width, inner_value) =
        prove_static_value(nodes.get(1..)?, child)?;
    let value = if parenthesized {
        inner_value
    } else {
        i32::from(inner_value == 0_i32)
    };
    let end = nodes.get(1)?.span.end.byte;
    Some((
        inner_width.checked_add(1)?,
        value,
        if parenthesized {
            end.checked_add(1)?
        } else {
            end
        },
    ))
}

// Reconstruct both branches of a pure binary predicate, even when C would
// short-circuit the second value. Unknown/effectful operands reject.
fn prove_static_binary(
    nodes: &[Node],
    at: StaticValueLocation,
) -> Option<(usize, i32, u32)> {
    let node = nodes.first()?;
    if node.kind != "binary-expression" {
        return None;
    }
    let operator = node.operation.as_deref()?;
    if !matches!(
        operator,
        "==" | "!=" | "<" | "<=" | ">" | ">=" | "&&" | "||"
    ) {
        return None;
    }
    let left_at = at.child(at.id.checked_add(1)?, at.start, at.column)?;
    let (left_width, left) = prove_static_value(nodes.get(1..)?, left_at)?;
    let right_index = left_width.checked_add(1)?;
    let left_root = nodes.get(1)?;
    let gap = u32::try_from(operator.len()).ok()?.checked_add(2)?;
    let right_at = at.child(
        at.id.checked_add(u32::try_from(right_index).ok()?)?,
        left_root.span.end.byte.checked_add(gap)?,
        left_root.span.end.column.checked_add(gap)?,
    )?;
    let (right_width, right) =
        prove_static_value(nodes.get(right_index..)?, right_at)?;
    let value = match operator {
        "==" => left == right,
        "!=" => left != right,
        "<" => left < right,
        "<=" => left <= right,
        ">" => left > right,
        ">=" => left >= right,
        "&&" => left != 0_i32 && right != 0_i32,
        "||" => left != 0_i32 || right != 0_i32,
        _ => return None,
    };
    Some((
        right_index.checked_add(right_width)?,
        i32::from(value),
        nodes.get(right_index)?.span.end.byte,
    ))
}

// Only bound, pure, pinned Clang expressions can select guest branch effects.
fn prove_static_value(
    nodes: &[Node],
    at: StaticValueLocation,
) -> Option<(usize, i32)> {
    if at.depth >= MAX_STATIC_PREDICATE_DEPTH {
        return None;
    }
    let node = nodes.first()?;
    if node.kind == "integer-literal" {
        return prove_decimal_condition_operand(
            node, at.id, at.parent, at.start, at.line, at.column,
        )
        .map(|value| (1, value));
    }
    if node.id != at.id
        || node.parent != at.parent
        || node.type_name.as_deref() != Some("i32")
        || node.reference.is_some()
        || node.literal.is_some()
        || node.name.is_some()
        || node.definition.is_some()
        || node.inline_specified.is_some()
        || node.linkage.is_some()
        || node.storage_class.is_some()
        || node.storage_duration.is_some()
    {
        return None;
    }
    let (width, value, end) = if node.kind == "binary-expression" {
        prove_static_binary(nodes, at)?
    } else {
        prove_static_prefix(nodes, at)?
    };
    (width <= MAX_STATIC_PREDICATE_NODES
        && node.constant_integer.as_deref() == Some(value.to_string().as_str())
        && source_word(node, at.start, end, at.line, at.column))
    .then_some((width, value))
}

// An authenticated remainder of the protected induction counter is a pure
// source-time value. The full pinned Clang subtree must spell `i % N`, with a
// nonzero canonical decimal N; no guest byte may participate in its value.
fn prove_induction_remainder(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, i32, u32)> {
    let [remainder, cast, variable, divisor, ..] = nodes else {
        return None;
    };
    let rhs_start = at.start.checked_add(4)?;
    let rhs_column = at.column.checked_add(4)?;
    if remainder.id != at.id
        || remainder.parent != at.parent
        || remainder.kind != "binary-expression"
        || remainder.type_name.as_deref() != Some("i32")
        || remainder.operation.as_deref() != Some("%")
        || remainder.reference.is_some()
        || !metadata_empty(remainder)
        || cast.id != remainder.id.checked_add(1)?
        || cast.parent != remainder.id
        || cast.kind != "cast-expression"
        || cast.type_name.as_deref() != Some("i32")
        || cast.operation.as_deref() != Some("lvalue-to-rvalue")
        || cast.reference.is_some()
        || !metadata_empty(cast)
        || !source_word(
            cast,
            at.start,
            at.start.checked_add(1)?,
            at.line,
            at.column,
        )
        || variable.id != cast.id.checked_add(1)?
        || variable.parent != cast.id
        || variable.kind != "declaration-reference-expression"
        || variable.type_name.as_deref() != Some("i32")
        || variable.reference.as_deref() != Some(induction.reference)
        || variable.operation.is_some()
        || !metadata_empty(variable)
        || variable.span != cast.span
    {
        return None;
    }
    let divisor_value = prove_decimal_condition_operand(
        divisor,
        variable.id.checked_add(1)?,
        remainder.id,
        rhs_start,
        at.line,
        rhs_column,
    )?;
    let end = divisor.span.end.byte;
    if divisor_value == 0
        || !source_word(remainder, at.start, end, at.line, at.column)
    {
        return None;
    }
    Some((4, induction.value.checked_rem(divisor_value)?, end))
}

// Compare an independently authenticated counter remainder with a canonical
// decimal integer. Every child, offset, type and declaration binding is
// checked before its source-time result selects real guest I/O effects.
fn prove_induction_remainder_comparison(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool, u32)> {
    let comparison = nodes.first()?;
    let operator = comparison.operation.as_deref()?;
    if !matches!(operator, "==" | "!=" | "<" | "<=" | ">" | ">=")
        || comparison.id != at.id
        || comparison.parent != at.parent
        || comparison.kind != "binary-expression"
        || comparison.type_name.as_deref() != Some("i32")
        || comparison.reference.is_some()
        || !metadata_empty(comparison)
    {
        return None;
    }
    let remainder_at = at.child(at.id.checked_add(1)?, at.start, at.column)?;
    let (left_width, value, left_end) =
        prove_induction_remainder(nodes.get(1..)?, remainder_at, induction)?;
    let right_index = left_width.checked_add(1)?;
    let right = nodes.get(right_index)?;
    let right_offset = u32::try_from(operator.len()).ok()?.checked_add(2)?;
    let rhs = prove_decimal_condition_operand(
        right,
        at.id.checked_add(u32::try_from(right_index).ok()?)?,
        comparison.id,
        left_end.checked_add(right_offset)?,
        at.line,
        at.column
            .checked_add(left_end.checked_sub(at.start)?)?
            .checked_add(right_offset)?,
    )?;
    if !source_word(
        comparison,
        at.start,
        right.span.end.byte,
        at.line,
        at.column,
    ) {
        return None;
    }
    let selected = match operator {
        "==" => value == rhs,
        "!=" => value != rhs,
        "<" => value < rhs,
        "<=" => value <= rhs,
        ">" => value > rhs,
        ">=" => value >= rhs,
        _ => return None,
    };
    Some((right_index.checked_add(1)?, selected, right.span.end.byte))
}

// This is source-time C induction, not a guest read. A leaf comparison
// must prove the same loop-local declaration, canonical token geometry and
// Clang ancestry on every unrolled trip. No C storage is projected.
fn prove_induction_comparison(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool, u32)> {
    let [comparison, cast, variable, bound, ..] = nodes else {
        return None;
    };
    let operator = comparison.operation.as_deref()?;
    if !matches!(operator, "==" | "!=" | "<" | "<=" | ">" | ">=") {
        return None;
    }
    let right_offset = 3u32.checked_add(u32::try_from(operator.len()).ok()?)?;
    let right_start = at.start.checked_add(right_offset)?;
    let right_column = at.column.checked_add(right_offset)?;
    if comparison.id != at.id
        || comparison.parent != at.parent
        || comparison.kind != "binary-expression"
        || comparison.type_name.as_deref() != Some("i32")
        || comparison.reference.is_some()
        || !metadata_empty(comparison)
        || cast.id != comparison.id.checked_add(1)?
        || cast.parent != comparison.id
        || cast.kind != "cast-expression"
        || cast.type_name.as_deref() != Some("i32")
        || cast.operation.as_deref() != Some("lvalue-to-rvalue")
        || cast.reference.is_some()
        || !metadata_empty(cast)
        || !source_word(
            cast,
            at.start,
            at.start.checked_add(1)?,
            at.line,
            at.column,
        )
        || variable.id != cast.id.checked_add(1)?
        || variable.parent != cast.id
        || variable.kind != "declaration-reference-expression"
        || variable.type_name.as_deref() != Some("i32")
        || variable.operation.is_some()
        || variable.reference.as_deref() != Some(induction.reference)
        || !metadata_empty(variable)
        || variable.span != cast.span
    {
        return None;
    }
    let rhs = prove_decimal_condition_operand(
        bound,
        variable.id.checked_add(1)?,
        comparison.id,
        right_start,
        at.line,
        right_column,
    )?;
    if !source_word(
        comparison,
        at.start,
        bound.span.end.byte,
        at.line,
        at.column,
    ) {
        return None;
    }
    let selected = match operator {
        "==" => induction.value == rhs,
        "!=" => induction.value != rhs,
        "<" => induction.value < rhs,
        "<=" => induction.value <= rhs,
        ">" => induction.value > rhs,
        ">=" => induction.value >= rhs,
        _ => return None,
    };
    Some((4, selected, bound.span.end.byte))
}

// A C scalar test of the protected loop counter is pure even without an
// explicit comparison. Only the authenticated induction declaration is known;
// the latest byte read from the guest is never available to this proof.
fn prove_induction_truth(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool, u32)> {
    let [read, variable, ..] = nodes else {
        return None;
    };
    let end = at.start.checked_add(1)?;
    if read.id != at.id
        || read.parent != at.parent
        || read.kind != "cast-expression"
        || read.type_name.as_deref() != Some("i32")
        || read.operation.as_deref() != Some("lvalue-to-rvalue")
        || read.reference.is_some()
        || !metadata_empty(read)
        || !source_word(read, at.start, end, at.line, at.column)
        || variable.id != read.id.checked_add(1)?
        || variable.parent != read.id
        || variable.kind != "declaration-reference-expression"
        || variable.type_name.as_deref() != Some("i32")
        || variable.reference.as_deref() != Some(induction.reference)
        || variable.operation.is_some()
        || !metadata_empty(variable)
        || !source_word(variable, at.start, end, at.line, at.column)
    {
        return None;
    }
    Some((2, induction.value != 0, end))
}

// Parentheses and Boolean negation are checked against their exact Clang
// child and source extent. Their operand can itself contain induction
// comparisons; a runtime guest value is never evaluated at compile time.
fn prove_induction_prefix(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool, u32)> {
    let node = nodes.first()?;
    let parenthesized = node.kind == "parenthesized-expression";
    if !parenthesized
        && (node.kind != "unary-expression"
            || node.operation.as_deref() != Some("!"))
    {
        return None;
    }
    if node.id != at.id
        || node.parent != at.parent
        || node.type_name.as_deref() != Some("i32")
        || node.reference.is_some()
        || !metadata_empty(node)
        || (parenthesized && node.operation.is_some())
    {
        return None;
    }
    let child_at = at.child(
        at.id.checked_add(1)?,
        at.start.checked_add(1)?,
        at.column.checked_add(1)?,
    )?;
    let (inner_width, inner_value, inner_end) =
        prove_induction_value(nodes.get(1..)?, child_at, induction)?;
    let width = inner_width.checked_add(1)?;
    let end = if parenthesized {
        inner_end.checked_add(1)?
    } else {
        inner_end
    };
    (width <= MAX_STATIC_PREDICATE_NODES
        && source_word(node, at.start, end, at.line, at.column))
    .then_some((
        width,
        if parenthesized {
            inner_value
        } else {
            !inner_value
        },
        end,
    ))
}

// Clang's conditional-expression has three direct subtrees in preorder.
// Every arm must be independently source-proven even if that arm is never
// selected by the finite induction value. ` ? ` and ` : ` are exact token
// gaps; guest input and side effects cannot participate in these branches.
fn prove_induction_ternary(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool, u32)> {
    let ternary = nodes.first()?;
    if ternary.id != at.id
        || ternary.parent != at.parent
        || ternary.kind != "conditional-expression"
        || ternary.type_name.as_deref() != Some("i32")
        || ternary.operation.is_some()
        || ternary.reference.is_some()
        || !metadata_empty(ternary)
    {
        return None;
    }
    let condition_at = at.child(at.id.checked_add(1)?, at.start, at.column)?;
    let (condition_width, condition, condition_end) =
        prove_induction_value(nodes.get(1..)?, condition_at, induction)?;
    let true_index = condition_width.checked_add(1)?;
    let true_start = condition_end.checked_add(3)?;
    let true_at = at.child(
        at.id.checked_add(u32::try_from(true_index).ok()?)?,
        true_start,
        at.column.checked_add(true_start.checked_sub(at.start)?)?,
    )?;
    let (true_width, true_value, true_end) =
        prove_induction_value(nodes.get(true_index..)?, true_at, induction)?;
    let false_index = true_index.checked_add(true_width)?;
    let false_start = true_end.checked_add(3)?;
    let false_at = at.child(
        at.id.checked_add(u32::try_from(false_index).ok()?)?,
        false_start,
        at.column.checked_add(false_start.checked_sub(at.start)?)?,
    )?;
    let (false_width, false_value, false_end) =
        prove_induction_value(nodes.get(false_index..)?, false_at, induction)?;
    let width = false_index.checked_add(false_width)?;
    (width <= MAX_STATIC_PREDICATE_NODES
        && source_word(ternary, at.start, false_end, at.line, at.column))
    .then_some((
        width,
        if condition {
            true_value
        } else {
            false_value
        },
        false_end,
    ))
}

// Admit only fully proven, pure logical combinations of exact induction
// comparisons or already-proven source constants. Both sides are authenticated
// regardless of short-circuit selection, so no effect can hide on an arm.
fn prove_induction_value(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool, u32)> {
    if at.depth >= MAX_STATIC_PREDICATE_DEPTH {
        return None;
    }
    let node = nodes.first()?;
    if node.kind == "binary-expression"
        && matches!(node.operation.as_deref(), Some("&&" | "||"))
    {
        if node.id != at.id
            || node.parent != at.parent
            || node.type_name.as_deref() != Some("i32")
            || node.reference.is_some()
            || !metadata_empty(node)
        {
            return None;
        }
        let left_at = at.child(at.id.checked_add(1)?, at.start, at.column)?;
        let (left_width, left, left_end) =
            prove_induction_value(nodes.get(1..)?, left_at, induction)?;
        let right_index = left_width.checked_add(1)?;
        let gap = 4;
        let right_at = at.child(
            at.id.checked_add(u32::try_from(right_index).ok()?)?,
            left_end.checked_add(gap)?,
            at.column
                .checked_add(left_end.checked_sub(at.start)?)?
                .checked_add(gap)?,
        )?;
        let (right_width, right, right_end) = prove_induction_value(
            nodes.get(right_index..)?,
            right_at,
            induction,
        )?;
        let width = right_index.checked_add(right_width)?;
        if width > MAX_STATIC_PREDICATE_NODES
            || !source_word(node, at.start, right_end, at.line, at.column)
        {
            return None;
        }
        let selected = if node.operation.as_deref() == Some("&&") {
            left && right
        } else {
            left || right
        };
        return Some((width, selected, right_end));
    }
    if node.kind == "conditional-expression" {
        return prove_induction_ternary(nodes, at, induction);
    }
    if node.kind == "cast-expression" {
        return prove_induction_truth(nodes, at, induction);
    }
    if node.kind == "binary-expression"
        && node.operation.as_deref() == Some("%")
    {
        let (width, value, end) =
            prove_induction_remainder(nodes, at, induction)?;
        return Some((width, value != 0, end));
    }
    if let Some((width, value)) = prove_static_value(nodes, at) {
        return Some((width, value != 0, node.span.end.byte));
    }
    if matches!(
        node.kind.as_str(),
        "unary-expression" | "parenthesized-expression"
    ) {
        return prove_induction_prefix(nodes, at, induction);
    }
    prove_induction_remainder_comparison(nodes, at, induction)
        .or_else(|| prove_induction_comparison(nodes, at, induction))
}

fn prove_induction_predicate(
    nodes: &[Node],
    conditional: &Node,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool)> {
    let begin = &conditional.span.begin;
    let (width, selected, _) = prove_induction_value(
        nodes,
        StaticValueLocation {
            id: conditional.id.checked_add(1)?,
            parent: conditional.id,
            start: begin.byte.checked_add(4)?,
            line: begin.line,
            column: begin.column.checked_add(4)?,
            depth: 0,
        },
        induction,
    )?;
    Some((width, selected))
}

// All static predicates are pure, bounded expression trees. Prove every
// operand even for `&&` and `||`: skipping an unknown side effect is unsafe.
fn prove_static_predicate(
    nodes: &[Node],
    conditional: &Node,
    induction: Option<StaticInduction<'_>>,
) -> Option<(usize, bool)> {
    if let Some(induction) = induction
        && let Some(result) =
            prove_induction_predicate(nodes, conditional, induction)
    {
        return Some(result);
    }
    let begin = &conditional.span.begin;
    let (width, value) = prove_static_value(nodes, StaticValueLocation {
        id: conditional.id.checked_add(1)?,
        parent: conditional.id,
        start: begin.byte.checked_add(4)?,
        line: begin.line,
        column: begin.column.checked_add(4)?,
        depth: 0,
    })?;
    Some((width, value != 0))
}

// Exact folded source-C predicates. Each bounded C call in both arms
// is authenticated before selecting guest effects.
// Runtime-dependent predicates still have no lowering.

#[expect(
    clippy::too_many_lines,
    reason = "prove literal condition, both branch children and source spans"
)]
fn prove_static_if<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    parent: u32,
    local: Option<&LocalDeclaration<'node>>,
    depth: usize,
    allow_new_local: bool,
    for_depth: usize,
    induction: Option<StaticInduction<'_>>,
    source: Option<&[u8]>,
) -> Option<StaticIfProof<'node>> {
    let [conditional, ..] = nodes else {
        return None;
    };
    let start = conditional.span.begin.byte;
    let line = conditional.span.begin.line;
    let column = conditional.span.begin.column;
    if depth >= MAX_STATIC_IF_DEPTH
        || start <= previous
        || start <= body.span.begin.byte
        || line == 0
        || column == 0
        || conditional.id != expected_id
        || conditional.parent != parent
        || conditional.kind != "if-statement"
        || conditional.type_name.is_some()
        || conditional.reference.is_some()
        || conditional.operation.is_some()
        || !metadata_empty(conditional)
    {
        return None;
    }
    let (predicate_width, condition_true) =
        prove_static_predicate(nodes.get(1..)?, conditional, induction)?;
    let predicate_root = nodes.get(1)?;
    let predicate_last = nodes.get(predicate_width)?;
    let arm_offset = 1usize.checked_add(predicate_width)?;
    let rest = nodes.get(arm_offset..)?;
    let then_arm = prove_static_if_arm(
        rest,
        body,
        previous,
        predicate_last.id.checked_add(1)?,
        conditional.id,
        local,
        depth,
        column,
        allow_new_local,
        for_depth,
        induction,
        source,
    )?;
    if then_arm.begin != predicate_root.span.end.byte.checked_add(2)?
        || then_arm.begin_line != line
        || then_arm.begin_column
            != predicate_root.span.end.column.checked_add(2)?
    {
        return None;
    }
    let mut width = arm_offset.checked_add(then_arm.width)?;
    let mut end = then_arm.end;
    let mut end_line = then_arm.end_line;
    let mut end_column = then_arm.end_column;
    let mut selected = condition_true;
    let mut effects = then_arm.effects;
    if conditional.span.end.byte != then_arm.end {
        let else_arm = prove_static_if_arm(
            nodes.get(width..)?,
            body,
            then_arm.end,
            expected_id.checked_add(u32::try_from(width).ok()?)?,
            conditional.id,
            local,
            depth,
            column,
            allow_new_local,
            for_depth,
            induction,
            source,
        )?;
        let else_gap = if then_arm.braced {
            6
        } else {
            7
        };
        if else_arm.begin != then_arm.end.checked_add(else_gap)? {
            return None;
        }
        width = width.checked_add(else_arm.width)?;
        end = else_arm.end;
        end_line = else_arm.end_line;
        end_column = else_arm.end_column;
        selected = true;
        if !condition_true {
            effects = else_arm.effects;
        }
    }
    let span_is_canonical = if end_line == line {
        source_word(conditional, start, end, line, column)
    } else {
        conditional.span.end.byte == end
            && conditional.span.end.line == end_line
            && conditional.span.end.column == end_column
    };
    if end >= body.span.end.byte || !span_is_canonical {
        return None;
    }
    Some(StaticIfProof {
        width,
        selected,
        effects,
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
    source: Option<&[u8]>,
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
    // A forged signed-char Clang node can have exactly the same extent as
    // `(unsigned char)`. The typed AST alone cannot prove the source token.
    // Require an explicitly supplied source witness for every narrowed u8
    // cast, and verify its literal spelling at the actual byte offset.
    let casts = input.nodes.iter().filter(|node| {
        node.kind == "cast-expression"
            && node.type_name.as_deref() == Some("u8")
    });
    for cast in casts {
        let start = usize::try_from(cast.span.begin.byte)
            .map_err(|_| FrontendJsonError::Unsupported)?;
        let end = start
            .checked_add(15)
            .ok_or(FrontendJsonError::Unsupported)?;
        if source.and_then(|bytes| bytes.get(start..end))
            != Some(b"(unsigned char)")
        {
            return Err(FrontendJsonError::Unsupported);
        }
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
    let mut terminated = false;
    while consumed < rest.len() {
        let first = rest.get(consumed).ok_or(FrontendJsonError::Unsupported)?;
        if outputs == MAX_SOURCE_OUTPUTS || first.id != next_id {
            return Err(FrontendJsonError::Unsupported);
        }
        if terminated || first.kind == "return-statement" {
            // Still authenticate every dead suffix node. Do not publish its
            // guest effects or treat an unverified effect as harmless.
            let (width, effects, end) = prove_static_if_statement(
                rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?,
                body,
                previous,
                next_id,
                body.id,
                None,
                0,
                false,
                0,
                None,
                source,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
            if !terminated
                && (effects.len() != 1
                    || effects[0].loop_exit != Some(StaticLoopExit::Return))
            {
                return Err(FrontendJsonError::Unsupported);
            }
            terminated = true;
            previous = end;
            consumed = consumed
                .checked_add(width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            continue;
        }
        if first.kind == "for-statement" {
            let proof = prove_static_for(
                rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?,
                body,
                previous,
                next_id,
                body.id,
                1,
                source,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
            // Each static trip has already been source-proven with its
            // induction value; the ordered trace still reads from the guest.
            let mut iteration_byte = None;
            for effect in &proof.effects {
                if let Some(exit) = effect.loop_exit {
                    if exit != StaticLoopExit::Return {
                        return Err(FrontendJsonError::Unsupported);
                    }
                    terminated = true;
                    break;
                }
                if inputs
                    .checked_add(usize::from(effect.input.is_some()))
                    .is_none_or(|count| count > MAX_ECHO_CALLS)
                    || outputs
                        .checked_add(effect.outputs.len())
                        .is_none_or(|total| total > MAX_SOURCE_OUTPUTS)
                {
                    return Err(FrontendJsonError::Unsupported);
                }
                let value = if let Some(input) = effect.input {
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
                    iteration_byte = Some(value);
                    value
                } else {
                    iteration_byte.ok_or(FrontendJsonError::Unsupported)?
                };
                latest_local = None;
                for output in effect.outputs.iter().rev() {
                    instructions.push(LocatedInstruction::new(
                        Instruction::ByteOutput { value },
                        typed_span(&output.span),
                    ));
                }
                outputs += effect.outputs.len();
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
        if first.kind == "if-statement" {
            let proof = prove_static_if(
                rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?,
                body,
                previous,
                next_id,
                body.id,
                latest_local.as_ref().map(|(local, _)| local),
                0,
                false,
                0,
                None,
                source,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
            if proof.selected {
                // A selected branch may contain a counted loop whose local
                // initializer reads a fresh byte on *each* unrolled pass.
                // Keep the latest guest SSA value inside this effect trace;
                // an outer-scope local is not its identity.
                let mut branch_byte =
                    latest_local.as_ref().map(|(_, value)| *value);
                for effect in &proof.effects {
                    if let Some(exit) = effect.loop_exit {
                        if exit != StaticLoopExit::Return {
                            return Err(FrontendJsonError::Unsupported);
                        }
                        terminated = true;
                        break;
                    }
                    if inputs + usize::from(effect.input.is_some())
                        > MAX_ECHO_CALLS
                        || outputs + effect.outputs.len() > MAX_SOURCE_OUTPUTS
                    {
                        return Err(FrontendJsonError::Unsupported);
                    }
                    let value = if let Some(input) = effect.input {
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
                        branch_byte = Some(value);
                        value
                    } else {
                        branch_byte.ok_or(FrontendJsonError::Unsupported)?
                    };
                    for output in effect.outputs.iter().rev() {
                        instructions.push(LocatedInstruction::new(
                            Instruction::ByteOutput { value },
                            typed_span(&output.span),
                        ));
                    }
                    outputs += effect.outputs.len();
                    requires_latest = true;
                }
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
                body.id,
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
            && first.operation.as_deref() == Some("=")
            && let Some((local, _)) = latest_local.as_ref()
            && let Some(read) = source.and_then(|witness| {
                rest.get(consumed..consumed.saturating_add(5)).and_then(
                    |nodes| {
                        prove_local_input_reassignment(
                            nodes,
                            (body, previous, body.id),
                            local,
                            witness,
                        )
                    },
                )
            })
        {
            if inputs == MAX_ECHO_CALLS {
                return Err(FrontendJsonError::Unsupported);
            }
            let id = ValueId::new(
                u32::try_from(inputs)
                    .map_err(|_| FrontendJsonError::Unsupported)?,
            );
            instructions.push(LocatedInstruction::new(
                Instruction::ByteInput {
                    result: id,
                    type_id: TypeId::new(0),
                },
                typed_span(&read.span),
            ));
            if let Some((_, value)) = latest_local.as_mut() {
                *value = id;
            }
            inputs += 1;
            previous = first.span.end.byte;
            consumed += 5;
            next_id = next_id
                .checked_add(5)
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
        if first.kind == "declaration-statement"
            && let Some((live, value)) = latest_local.as_ref()
            && let Some(alias) = source.and_then(|witness| {
                rest.get(consumed..consumed.saturating_add(4)).and_then(
                    |nodes| {
                        prove_local_alias(
                            nodes,
                            (body, previous, body.id),
                            live,
                            witness,
                        )
                    },
                )
            })
        {
            if !local_names.insert(alias.name) {
                return Err(FrontendJsonError::Unsupported);
            }
            previous = alias.declaration_end;
            latest_local = Some((alias, *value));
            consumed = consumed
                .checked_add(4)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(4)
                .ok_or(FrontendJsonError::Unsupported)?;
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
            let local = prove_local_declaration(
                declaration_nodes,
                body,
                previous,
                body.id,
            )
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
