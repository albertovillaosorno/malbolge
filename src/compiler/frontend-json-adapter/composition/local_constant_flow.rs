// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Closed source-backed constant propagation across automatic C locals.
// - Must-Not:
//   - Emulate dynamic guest state or discard unrecognized C side effects.
// - Allows:
//   - Inputs: byte-range unsigned writes and closed source-proven branches.
//   - Outputs: one source-derived typed byte and a normative guest output.
//   - Side effects: none during compilation.
// - Split-When:
//   - Symbolic local-state and control-flow IR supersede constant propagation.
// - Merge-When:
//   - A general source-to-typed-SSA projection replaces this bounded path.
// - Summary:
//   - Reconcile distinct canonical Clang symbols before folding arithmetic.
// - Description:
//   - Reject aliases, unknown effects, dynamic loops and excess statements.
// - Usage:
//   - Invoked after the original single-local proof fails.
// - Defaults:
//   - At least two independently declared locals are required.

//! Source-backed constant propagation with bounded conditional selection.

use super::local_initialized_output::{
    assigned_local_reference, clean, correct_node, emit_verified_local_bytes,
    literal_byte, span_within, typed_operator,
};
use super::{Artifact, FrontendJsonError, Node, StorageDuration};

const MAX_LOCALS: usize = 8;
const MAX_WRITES: usize = 16;
const MAX_STATIC_LOOP_ITERATIONS: u8 = 12;
const MAX_EXPRESSION_DEPTH: usize = 8;
// Bound the lexical prefix on an explicit source-proven `(int)` cast.
const MAX_EXPLICIT_CAST_PREFIX_BYTES: u32 = 16;

#[derive(Clone)]
struct Local<'node> {
    byte: u8,
    declaration: &'node Node,
    name: &'node str,
    source: &'node Node,
    symbol: &'node str,
}

struct Flow<'node> {
    locals: Vec<Local<'node>>,
    loop_counter: Option<&'node str>,
    nodes: &'node [Node],
    outputs: Vec<OutputCall<'node>>,
    position: usize,
}

#[derive(Clone, Copy)]
struct OutputCall<'node> {
    byte: u8,
    call: &'node Node,
    source: &'node Node,
}

impl<'node> Flow<'node> {
    fn assignment(
        &mut self,
        body: &Node,
        previous_end: u32,
    ) -> Option<(u32, &'node Node)> {
        let assignment = self.take(body.id, "binary-expression")?;
        if !typed_operator(assignment, "=")
            || !span_within(&body.span, &assignment.span)
            || previous_end > assignment.span.begin.byte
        {
            return None;
        }
        let left =
            self.take(assignment.id, "declaration-reference-expression")?;
        let symbol = left.reference.as_deref()?;
        let destination = self
            .locals
            .iter()
            .position(|local| local.symbol == symbol)?;
        if self.loop_counter == Some(symbol)
            || !assigned_local_reference(left, symbol)
            || !span_within(&assignment.span, &left.span)
            || assignment.span.begin.byte != left.span.begin.byte
        {
            return None;
        }
        let (value, value_source) = self.expression(assignment.id, 0)?;
        let byte = u8::try_from(value).ok()?;
        if !span_within(&assignment.span, &value_source.span)
            || left.span.end.byte >= value_source.span.begin.byte
            || value_source.span.end.byte != assignment.span.end.byte
        {
            return None;
        }
        let local = self.locals.get_mut(destination)?;
        local.byte = byte;
        local.source = value_source;
        Some((assignment.span.end.byte, value_source))
    }

    /// Prove a pure C Boolean tree over exact unsigned comparisons.
    /// Both operands are proven even when `&&`/`||` would short-circuit;
    /// the admitted subtree contains no side effects or undefined operations.
    fn condition(&mut self, statement: &Node) -> Option<(bool, &'node Node)> {
        let (selected, expression) =
            self.condition_expression(statement.id, 0)?;
        span_within(&statement.span, &expression.span)
            .then_some((selected, expression))
    }

    fn condition_expression(
        &mut self,
        parent: u32,
        depth: usize,
    ) -> Option<(bool, &'node Node)> {
        if depth > MAX_EXPRESSION_DEPTH {
            return None;
        }
        if self.peek()?.kind == "parenthesized-expression" {
            let grouped = self.take(parent, "parenthesized-expression")?;
            let (value, expression) =
                self.condition_expression(grouped.id, depth.checked_add(1)?)?;
            if grouped.type_name.as_deref() != Some("i32")
                || !bare_typed_node(grouped)
                || !span_within(&grouped.span, &expression.span)
                || grouped.span.begin.byte >= expression.span.begin.byte
                || expression.span.end.byte >= grouped.span.end.byte
            {
                return None;
            }
            return Some((value, grouped));
        }
        let comparison = self.take(parent, "binary-expression")?;
        if matches!(comparison.operation.as_deref(), Some("&&" | "||")) {
            let (left_value, left) = self
                .condition_expression(comparison.id, depth.checked_add(1)?)?;
            let (right_value, right) = self
                .condition_expression(comparison.id, depth.checked_add(1)?)?;
            if !clean_i32_binary(comparison)
                || !ordered_binary_spans(comparison, left, right)
            {
                return None;
            }
            return Some((
                if comparison.operation.as_deref() == Some("&&") {
                    left_value && right_value
                } else {
                    left_value || right_value
                },
                comparison,
            ));
        }
        self.masked_comparison(comparison)
    }

    /// Parse both arms completely, but retain only the proven selected state.
    /// No output, declarations or nested control flow are discarded.
    fn conditional(&mut self, body: &Node, previous_end: u32) -> Option<u32> {
        let statement = self.take(body.id, "if-statement")?;
        if !clean(statement)
            || !span_within(&body.span, &statement.span)
            || previous_end > statement.span.begin.byte
        {
            return None;
        }
        let (take_then, condition) = self.condition(statement)?;
        let then_body = self.take(statement.id, "compound-statement")?;
        if !clean(then_body)
            || !span_within(&statement.span, &then_body.span)
            || condition.span.end.byte >= then_body.span.begin.byte
        {
            return None;
        }
        let starting = self.locals.clone();
        let (then_end, _) =
            self.assignment(then_body, then_body.span.begin.byte)?;
        if then_end >= then_body.span.end.byte {
            return None;
        }
        let then_state = self.locals.clone();
        self.locals = starting;
        let else_body = self.take(statement.id, "compound-statement")?;
        if !clean(else_body)
            || !span_within(&statement.span, &else_body.span)
            || then_body.span.end.byte > else_body.span.begin.byte
            || else_body.span.end.byte != statement.span.end.byte
        {
            return None;
        }
        let (else_end, _) =
            self.assignment(else_body, else_body.span.begin.byte)?;
        if else_end >= else_body.span.end.byte {
            return None;
        }
        if take_then {
            self.locals = then_state;
        }
        Some(statement.span.end.byte)
    }

    /// Check both branches of a source-constant conditional output, retaining
    /// exactly the selected `putchar` effect for each loop iteration.
    fn conditional_output(
        &mut self,
        body: &Node,
        previous_end: u32,
    ) -> Option<(u32, OutputCall<'node>)> {
        let statement = self.take(body.id, "if-statement")?;
        if !clean(statement)
            || !span_within(&body.span, &statement.span)
            || previous_end > statement.span.begin.byte
        {
            return None;
        }
        let (take_then, condition) = self.condition(statement)?;
        let then_body = self.take(statement.id, "compound-statement")?;
        if !clean(then_body)
            || !span_within(&statement.span, &then_body.span)
            || condition.span.end.byte >= then_body.span.begin.byte
        {
            return None;
        }
        let then_call =
            checked_call(self, then_body, then_body.span.begin.byte)?;
        if then_call.call.span.end.byte >= then_body.span.end.byte {
            return None;
        }
        let else_body = self.take(statement.id, "compound-statement")?;
        if !clean(else_body)
            || !span_within(&statement.span, &else_body.span)
            || then_body.span.end.byte > else_body.span.begin.byte
            || else_body.span.end.byte != statement.span.end.byte
        {
            return None;
        }
        let else_call =
            checked_call(self, else_body, else_body.span.begin.byte)?;
        if else_call.call.span.end.byte >= else_body.span.end.byte {
            return None;
        }
        Some((
            statement.span.end.byte,
            if take_then {
                then_call
            } else {
                else_call
            },
        ))
    }

    fn declaration(
        &mut self,
        body: &Node,
        previous_end: u32,
    ) -> Option<(u32, &'node Node)> {
        let statement = self.take(body.id, "declaration-statement")?;
        let variable = self.take(statement.id, "variable-declaration")?;
        let name = variable.name.as_deref()?;
        let symbol = variable.reference.as_deref()?;
        if self.locals.len() >= MAX_LOCALS
            || self
                .locals
                .iter()
                .any(|local| local.symbol == symbol || local.name == name)
            || !clean(statement)
            || variable.type_name.as_deref() != Some("u32")
            || variable.definition.as_deref() != Some("definition")
            || variable.linkage.as_deref() != Some("none")
            || variable.storage_class.as_deref() != Some("none")
            || !matches!(
                variable.storage_duration,
                Some(StorageDuration::Automatic)
            )
            || variable.inline_specified.is_some()
            || variable.operation.is_some()
            || variable.literal.is_some()
            || variable.constant_integer.is_some()
            || !symbol_location(variable, name, symbol)
            || !span_within(&body.span, &statement.span)
            || !span_within(&statement.span, &variable.span)
            || previous_end > statement.span.begin.byte
        {
            return None;
        }
        let (value, initializer) = self.expression(variable.id, 0)?;
        let byte = u8::try_from(value).ok()?;
        if !span_within(&variable.span, &initializer.span)
            || initializer.span.end.byte != variable.span.end.byte
            || initializer.span.begin.byte <= variable.span.begin.byte
        {
            return None;
        }
        self.locals.push(Local {
            byte,
            declaration: variable,
            name,
            source: initializer,
            symbol,
        });
        Some((statement.span.end.byte, initializer))
    }

    /// Evaluate checked `u32` temporaries; narrow only at local stores/output.
    /// Consume the complete exact Clang expression subtree, never a prefix.
    #[expect(
        clippy::cognitive_complexity,
        reason = "bounded AST expression proof"
    )]
    fn expression(
        &mut self,
        parent: u32,
        depth: usize,
    ) -> Option<(u32, &'node Node)> {
        if depth > MAX_EXPRESSION_DEPTH {
            return None;
        }
        let node = self.peek()?;
        match node.kind.as_str() {
            "integer-literal" => {
                let leaf = self.take(parent, "integer-literal")?;
                Some((u32::from(literal_byte(leaf)?), leaf))
            },
            "parenthesized-expression" => {
                let grouped = self.take(parent, "parenthesized-expression")?;
                let (value, expression) =
                    self.expression(grouped.id, depth.checked_add(1)?)?;
                if !bare_typed_node(grouped)
                    || grouped.type_name.as_deref() != Some("u32")
                    || !span_within(&grouped.span, &expression.span)
                    || grouped.span.begin.byte >= expression.span.begin.byte
                    || expression.span.end.byte >= grouped.span.end.byte
                {
                    return None;
                }
                Some((value, grouped))
            },
            "cast-expression" => {
                let load = self.take(parent, "cast-expression")?;
                if !typed_operator(load, "lvalue-to-rvalue") {
                    return None;
                }
                let read =
                    self.take(load.id, "declaration-reference-expression")?;
                if !span_within(&load.span, &read.span)
                    || load.span != read.span
                {
                    return None;
                }
                Some((u32::from(self.referenced(read)?.0), load))
            },
            "binary-expression" => {
                let expression = self.take(parent, "binary-expression")?;
                let operation = expression.operation.as_deref()?;
                if !typed_operator(expression, operation) {
                    return None;
                }
                let child_depth = depth.checked_add(1)?;
                let (left_value, left) =
                    self.expression(expression.id, child_depth)?;
                let (right_value, right) =
                    self.expression(expression.id, child_depth)?;
                if !ordered_binary_spans(expression, left, right) {
                    return None;
                }
                let value =
                    checked_u32_binary(operation, left_value, right_value)?;
                Some((value, expression))
            },
            _ => None,
        }
    }

    /// Replay a closed loop body with checked state and selected outputs.
    /// Each lexical inner declaration dies at the end of its iteration.
    fn loop_body(&mut self, body: &Node) -> Option<()> {
        let mut last_end = body.span.begin.byte;
        let mut writes = 0;
        while let Some(node) = self.peek() {
            if node.span.begin.byte >= body.span.end.byte {
                break;
            }
            let expected_parent = body.id;
            if node.parent != expected_parent || writes >= MAX_WRITES {
                return None;
            }
            last_end = match node.kind.as_str() {
                "declaration-statement" => self.declaration(body, last_end)?.0,
                "binary-expression" => self.assignment(body, last_end)?.0,
                "if-statement" => self.loop_conditional(body, last_end)?,
                "call-expression" => {
                    let output = checked_call(self, body, last_end)?;
                    let end = output.call.span.end.byte;
                    self.outputs.push(output);
                    end
                },
                _ => return None,
            };
            writes = writes.checked_add(1)?;
        }
        (writes > 0 && last_end < body.span.end.byte).then_some(())
    }

    fn loop_conditional(&mut self, body: &Node, last_end: u32) -> Option<u32> {
        let position = self.position;
        let locals = self.locals.clone();
        if let Some(end) = self.conditional(body, last_end) {
            return Some(end);
        }
        self.position = position;
        self.locals = locals;
        let (end, output) = self.conditional_output(body, last_end)?;
        self.outputs.push(output);
        Some(end)
    }

    fn masked_comparison(
        &mut self,
        comparison: &'node Node,
    ) -> Option<(bool, &'node Node)> {
        let parentheses =
            self.take(comparison.id, "parenthesized-expression")?;
        let (left, expression) = self.expression(parentheses.id, 0)?;
        let right = self.take(comparison.id, "integer-literal")?;
        let right_value = literal_byte(right)?;
        let selected = checked_condition_comparison(
            comparison,
            left,
            u32::from(right_value),
        )?;
        if parentheses.type_name.as_deref() != Some("u32")
            || !bare_typed_node(parentheses)
            || !span_within(&comparison.span, &parentheses.span)
            || !span_within(&parentheses.span, &expression.span)
            || expression.operation.as_deref() != Some("&")
            || !span_within(&comparison.span, &right.span)
            || comparison.span.begin.byte != parentheses.span.begin.byte
            || parentheses.span.begin.byte >= expression.span.begin.byte
            || expression.span.end.byte >= parentheses.span.end.byte
            || !ordered_binary_spans(comparison, parentheses, right)
        {
            return None;
        }
        Some((selected, comparison))
    }

    fn peek(&self) -> Option<&'node Node> {
        self.nodes.get(self.position)
    }

    fn referenced(&self, read: &Node) -> Option<(u8, &'node Node)> {
        let symbol = read.reference.as_deref()?;
        let local = self.locals.iter().find(|local| local.symbol == symbol)?;
        if !assigned_local_reference(read, symbol)
            || !symbol_location(local.declaration, local.name, symbol)
            || read.span.begin.byte < local.declaration.span.end.byte
        {
            return None;
        }
        Some((local.byte, local.source))
    }

    /// Prove one `for (unsigned i = 0U; i < N; ++i)` and replay its
    /// source-checked body, never synthesizing guest control flow.
    /// Neither the loop counter nor any other local may escape its C scope.
    #[expect(
        clippy::cognitive_complexity,
        reason = "bounded exact Clang loop proof"
    )]
    #[expect(
        clippy::too_many_lines,
        reason = "closed Clang for-loop proof"
    )]
    fn static_for(&mut self, body: &Node, previous_end: u32) -> Option<u32> {
        let statement = self.take(body.id, "for-statement")?;
        if !clean(statement)
            || !span_within(&body.span, &statement.span)
            || previous_end > statement.span.begin.byte
            || self.loop_counter.is_some()
        {
            return None;
        }
        let outer_len = self.locals.len();
        let (declaration_end, _) =
            self.declaration(statement, statement.span.begin.byte)?;
        let counter = self.locals.get(outer_len)?;
        if counter.byte != 0 {
            return None;
        }
        let symbol = counter.symbol;
        let comparison = self.take(statement.id, "binary-expression")?;
        let load = self.take(comparison.id, "cast-expression")?;
        let read = self.take(load.id, "declaration-reference-expression")?;
        let bound_node = self.take(comparison.id, "integer-literal")?;
        let bound = literal_byte(bound_node)?;
        if !typed_less_than(comparison)
            || !typed_operator(load, "lvalue-to-rvalue")
            || !assigned_local_reference(read, symbol)
            || !span_within(&statement.span, &comparison.span)
            || !span_within(&comparison.span, &load.span)
            || !span_within(&comparison.span, &bound_node.span)
            || load.span != read.span
            || comparison.span.begin.byte != load.span.begin.byte
            || load.span.end.byte >= bound_node.span.begin.byte
            || comparison.span.end.byte != bound_node.span.end.byte
            || declaration_end >= comparison.span.begin.byte
            || !(1..=MAX_STATIC_LOOP_ITERATIONS).contains(&bound)
        {
            return None;
        }
        let separated = comparison.span.end.byte < self.peek()?.span.begin.byte;
        let increment = self.take(statement.id, "unary-expression")?;
        let increment_read =
            self.take(increment.id, "declaration-reference-expression")?;
        if !typed_operator(increment, "++")
            || !assigned_local_reference(increment_read, symbol)
            || !span_within(&statement.span, &increment.span)
            || !span_within(&increment.span, &increment_read.span)
            || !separated
            || increment.span.end.byte != increment_read.span.end.byte
            || increment.span.begin.byte >= increment_read.span.begin.byte
        {
            return None;
        }
        let loop_body = self.take(statement.id, "compound-statement")?;
        if !clean(loop_body)
            || !span_within(&statement.span, &loop_body.span)
            || increment.span.end.byte >= loop_body.span.begin.byte
            || loop_body.span.end.byte != statement.span.end.byte
        {
            return None;
        }
        let body_start = self.position;
        self.loop_counter = Some(symbol);
        let mut body_end = None;
        for iteration in 0..bound {
            self.position = body_start;
            self.loop_body(loop_body)?;
            if body_end
                .is_some_and(|expected_end| self.position != expected_end)
            {
                return None;
            }
            body_end = Some(self.position);
            // Inner automatic locals must not remain visible after the brace.
            self.locals.truncate(outer_len.checked_add(1)?);
            let current_counter = self.locals.get_mut(outer_len)?;
            if current_counter.byte != iteration {
                return None;
            }
            current_counter.byte = current_counter.byte.checked_add(1)?;
            current_counter.source = increment;
        }
        self.position = body_end?;
        self.locals.truncate(outer_len);
        self.loop_counter = None;
        Some(statement.span.end.byte)
    }

    fn take(&mut self, parent: u32, kind: &str) -> Option<&'node Node> {
        let node = self.peek()?;
        let id = u32::try_from(self.position).ok()?.checked_add(1)?;
        if !correct_node(node, id, parent, kind) {
            return None;
        }
        self.position = self.position.checked_add(1)?;
        Some(node)
    }
}

/// Require a fully covered source-ordered binary expression, not a
/// detached operand or an unchecked trailing effect.
const fn ordered_binary_spans(
    expression: &Node,
    left: &Node,
    right: &Node,
) -> bool {
    span_within(&expression.span, &left.span)
        && span_within(&expression.span, &right.span)
        && expression.span.begin.byte == left.span.begin.byte
        && left.span.end.byte < right.span.begin.byte
        && right.span.end.byte == expression.span.end.byte
}

/// Evaluate only exact unsigned-C operators after both source operands
/// have been independently checked. State narrowing happens at stores.
fn checked_u32_binary(operator: &str, left: u32, right: u32) -> Option<u32> {
    match operator {
        "+" => left.checked_add(right),
        "-" => left.checked_sub(right),
        "*" => left.checked_mul(right),
        "/" => left.checked_div(right),
        "%" => left.checked_rem(right),
        // C unsigned shifts discard high bits; counts must be below 32.
        "<<" => left.checked_shl(right),
        ">>" => left.checked_shr(right),
        "^" => Some(left ^ right),
        "&" => Some(left & right),
        "|" => Some(left | right),
        _ => None,
    }
}

/// No expression metadata beyond a single exact integer result category.
const fn bare_typed_node(node: &Node) -> bool {
    node.name.is_none()
        && node.reference.is_none()
        && node.operation.is_none()
        && node.constant_integer.is_none()
        && node.literal.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
}

fn typed_less_than(node: &Node) -> bool {
    node.operation.as_deref() == Some("<")
        && node.type_name.as_deref() == Some("i32")
        && node.name.is_none()
        && node.reference.is_none()
        && node.constant_integer.is_none()
        && node.literal.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
}

/// Accept no instruction metadata other than an i32 binary operator.
fn clean_i32_binary(node: &Node) -> bool {
    node.type_name.as_deref() == Some("i32")
        && node.operation.is_some()
        && node.name.is_none()
        && node.reference.is_none()
        && node.constant_integer.is_none()
        && node.literal.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
}

/// Compare source-backed unsigned operands. C comparison results are `int`,
/// but both checked operands retain their unsigned type and value.
fn checked_condition_comparison(
    node: &Node,
    left: u32,
    right: u32,
) -> Option<bool> {
    if !clean_i32_binary(node) {
        return None;
    }
    Some(match node.operation.as_deref()? {
        "==" => left == right,
        "!=" => left != right,
        "<" => left < right,
        "<=" => left <= right,
        ">" => left > right,
        ">=" => left >= right,
        _ => return None,
    })
}

fn symbol_location(declaration: &Node, name: &str, symbol: &str) -> bool {
    let Some((reference_name, offset_text)) = symbol.rsplit_once('@') else {
        return false;
    };
    let Ok(offset) = offset_text.parse::<u32>() else {
        return false;
    };
    !name.is_empty()
        && reference_name == name
        && offset >= declaration.span.begin.byte
        && offset
            .checked_add(u32::try_from(name.len()).unwrap_or(u32::MAX))
            .is_some_and(|end| end <= declaration.span.end.byte)
}

/// Re-admit the two exact pinned-Clang `putchar` argument shapes.
/// A parenthesized unsigned expression is folded only after every operand,
/// symbol reference and operator is accounted for in the same source tree.
fn checked_argument<'node>(
    flow: &mut Flow<'node>,
    conversion: &Node,
) -> Option<(u8, &'node Node)> {
    match flow.peek()?.kind.as_str() {
        "cast-expression" => {
            let load = flow.take(conversion.id, "cast-expression")?;
            let read =
                flow.take(load.id, "declaration-reference-expression")?;
            if !typed_operator(load, "lvalue-to-rvalue")
                || !span_within(&conversion.span, &load.span)
                || !span_within(&load.span, &read.span)
                || load.span != read.span
                || conversion.span.end.byte != load.span.end.byte
                || load.span.begin.byte < conversion.span.begin.byte
                || load
                    .span
                    .begin
                    .byte
                    .checked_sub(conversion.span.begin.byte)
                    .is_none_or(|width| width > MAX_EXPLICIT_CAST_PREFIX_BYTES)
            {
                return None;
            }
            flow.referenced(read)
        },
        "parenthesized-expression" => {
            let grouped =
                flow.take(conversion.id, "parenthesized-expression")?;
            let (byte, expression) = flow.expression(grouped.id, 0)?;
            if !bare_typed_node(grouped)
                || grouped.type_name.as_deref() != Some("u32")
                || !span_within(&conversion.span, &grouped.span)
                || !span_within(&grouped.span, &expression.span)
                || conversion.span.begin.byte >= grouped.span.begin.byte
                || grouped.span.begin.byte >= expression.span.begin.byte
                || expression.span.end.byte >= grouped.span.end.byte
                || grouped.span.end.byte != conversion.span.end.byte
            {
                return None;
            }
            Some((u8::try_from(byte).ok()?, expression))
        },
        _ => None,
    }
}

/// Admit one source-proven call, including its replay in a bounded loop.
fn checked_call<'node>(
    flow: &mut Flow<'node>,
    body: &Node,
    last_end: u32,
) -> Option<OutputCall<'node>> {
    let call = flow.take(body.id, "call-expression")?;
    let cast = flow.take(call.id, "cast-expression")?;
    let callee = flow.take(cast.id, "declaration-reference-expression")?;
    let conversion = flow.take(call.id, "cast-expression")?;
    if call.type_name.as_deref() != Some("i32")
        || call.reference.as_deref() != Some("external:putchar")
        || call.name.is_some()
        || call.operation.is_some()
        || cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
        || callee.type_name.as_deref() != Some("fn(i32)->i32")
        || callee.reference.as_deref() != Some("external:putchar")
        || conversion.type_name.as_deref() != Some("i32")
        || cast.operation.as_deref() != Some("function-to-pointer")
        || conversion.operation.as_deref() != Some("integral-cast")
        || !span_within(&body.span, &call.span)
        || !span_within(&call.span, &cast.span)
        || !span_within(&cast.span, &callee.span)
        || !span_within(&call.span, &conversion.span)
        || last_end > call.span.begin.byte
    {
        return None;
    }
    for node in [call, cast, callee, conversion] {
        if node.constant_integer.is_some()
            || node.literal.is_some()
            || node.definition.is_some()
            || node.inline_specified.is_some()
            || node.linkage.is_some()
            || node.storage_class.is_some()
            || node.storage_duration.is_some()
            || node.name.is_some()
        {
            return None;
        }
    }
    if cast.reference.is_some()
        || conversion.reference.is_some()
        || callee.operation.is_some()
        || cast.span != callee.span
        || call.span.begin.byte != cast.span.begin.byte
        || conversion.span.begin.byte <= callee.span.end.byte
        || conversion.span.end.byte >= call.span.end.byte
    {
        return None;
    }
    let (byte, source) = checked_argument(flow, conversion)?;
    Some(OutputCall { byte, call, source })
}

/// Project multiple automatic locals only when every source effect is proven.
///
/// # Errors
///
/// Rejects incomplete Clang trees, aliases, control flow, unbounded unsigned
/// arithmetic, extra calls, and any unsupported operation before publishing IR.
#[expect(
    clippy::too_many_lines,
    reason = "closed multi-local preorder proof"
)]
#[expect(
    clippy::redundant_pub_crate,
    reason = "closed sibling projection"
)]
pub(super) fn canonical_multi_local_output(
    bytes: &[u8],
) -> Result<super::CanonicalGuestProjection, FrontendJsonError> {
    if bytes.is_empty() || bytes.len() > super::MAX_FRONTEND_JSON_BYTES {
        return Err(FrontendJsonError::Malformed);
    }
    let input: Artifact = serde_json::from_slice(bytes)
        .map_err(|_error| FrontendJsonError::Malformed)?;
    if input.schema_version != 1
        || input.identity != super::EXPECTED_ARTIFACT
        || input.profile.abi_id != super::EXPECTED_ABI
        || input.profile.target_profile != super::EXPECTED_PROFILE
        || input.clang.version != "22.1.8"
        || input.clang.target != "wasm32-unknown-unknown"
        || input.clang.language != "c23"
        || input.source.id.is_empty()
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let [function, body, ..] = input.nodes.as_slice() else {
        return Err(FrontendJsonError::Unsupported);
    };
    if !correct_node(function, 1, 0, "function-declaration")
        || function.name.as_deref().is_none_or(str::is_empty)
        || function.type_name.as_deref() != Some("fn()->void")
        || function.definition.as_deref() != Some("definition")
        || function.inline_specified != Some(false)
        || function.linkage.as_deref() != Some("external")
        || function.storage_class.as_deref() != Some("none")
        || function.reference.is_some()
        || function.operation.is_some()
        || function.constant_integer.is_some()
        || function.literal.is_some()
        || function.storage_duration.is_some()
        || !correct_node(body, 2, 1, "compound-statement")
        || !clean(body)
        || !span_within(&function.span, &body.span)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let mut flow = Flow {
        locals: Vec::new(),
        loop_counter: None,
        nodes: &input.nodes,
        outputs: Vec::new(),
        position: 2,
    };
    let mut last_end = body.span.begin.byte;
    let mut remaining_writes = MAX_WRITES;
    while remaining_writes > 0 {
        let Some(node) = flow.peek() else {
            break;
        };
        match node.kind.as_str() {
            "declaration-statement" => {
                let (end, _source) = flow
                    .declaration(body, last_end)
                    .ok_or(FrontendJsonError::Unsupported)?;
                last_end = end;
            },
            "binary-expression" => {
                let (end, _source) = flow
                    .assignment(body, last_end)
                    .ok_or(FrontendJsonError::Unsupported)?;
                last_end = end;
            },
            "for-statement" => {
                last_end = flow
                    .static_for(body, last_end)
                    .ok_or(FrontendJsonError::Unsupported)?;
            },
            "if-statement" if remaining_writes >= 2 => {
                last_end = flow
                    .conditional(body, last_end)
                    .ok_or(FrontendJsonError::Unsupported)?;
                remaining_writes = remaining_writes
                    .checked_sub(1)
                    .ok_or(FrontendJsonError::Unsupported)?;
            },
            _ => break,
        }
        remaining_writes = remaining_writes
            .checked_sub(1)
            .ok_or(FrontendJsonError::Unsupported)?;
    }
    if flow.locals.len() < 2 {
        return Err(FrontendJsonError::Unsupported);
    }
    if flow.outputs.is_empty()
        || flow
            .peek()
            .is_some_and(|node| node.kind == "call-expression")
    {
        let output = checked_call(&mut flow, body, last_end)
            .ok_or(FrontendJsonError::Unsupported)?;
        last_end = output.call.span.end.byte;
        flow.outputs.push(output);
    }
    let returned = if flow.peek().is_some() {
        let node = flow
            .take(body.id, "return-statement")
            .ok_or(FrontendJsonError::Unsupported)?;
        if !clean(node)
            || !span_within(&body.span, &node.span)
            || last_end > node.span.begin.byte
        {
            return Err(FrontendJsonError::Unsupported);
        }
        Some(node)
    } else {
        None
    };
    if flow.peek().is_some() {
        return Err(FrontendJsonError::Unsupported);
    }
    let proven: Vec<_> = flow
        .outputs
        .iter()
        .map(
            |output| super::local_initialized_output::ProvenLocalOutput {
                body,
                byte: output.byte,
                call: output.call,
                function,
                returned,
                source: output.source,
            },
        )
        .collect();
    emit_verified_local_bytes(&input, &proven)
}
