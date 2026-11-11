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
//   - Inputs: checked u32 unsigned writes and closed source-proven branches.
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
    literal_u32, span_within, typed_operator,
};
use super::{Artifact, FrontendJsonError, Node, StorageDuration};

const MAX_LOCALS: usize = 8;
const MAX_WRITES: usize = 16;
const MAX_STATIC_LOOP_ITERATIONS: u8 = 12;
const MAX_NESTED_FOR_LOOPS: usize = 2;
const MAX_NESTED_LOOP_BLOCKS: usize = 4;
const MAX_NESTED_CONDITIONAL_DEPTH: u8 = 3;
const MAX_EXPRESSION_DEPTH: usize = 8;
// Bound the lexical prefix on an explicit source-proven `(int)` cast.
const MAX_EXPLICIT_CAST_PREFIX_BYTES: u32 = 16;

#[derive(Clone)]
struct Local<'node> {
    // C unsigned locals retain all 32 bits; only guest output and bounded
    // induction counters have narrower admission requirements.
    value: Option<u32>,
    declaration: &'node Node,
    name: &'node str,
    source: &'node Node,
    symbol: &'node str,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum LoopExit {
    Break,
    Continue,
    Return,
}

struct Flow<'node> {
    locals: Vec<Local<'node>>,
    loop_counters: Vec<&'node str>,
    within_while_body: bool,
    loop_exit: Option<LoopExit>,
    return_node: Option<&'node Node>,
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
        let kind = self.peek()?.kind.as_str();
        if !matches!(
            kind,
            "binary-expression" | "compound-assignment-expression"
        ) {
            return None;
        }
        let assignment = self.take(body.id, kind)?;
        let operator = assignment.operation.as_deref()?;
        let compound_operation = match (kind, operator) {
            ("binary-expression", "=") => None,
            ("compound-assignment-expression", "+=") => Some("+"),
            ("compound-assignment-expression", "-=") => Some("-"),
            ("compound-assignment-expression", "^=") => Some("^"),
            ("compound-assignment-expression", "&=") => Some("&"),
            ("compound-assignment-expression", "|=") => Some("|"),
            ("compound-assignment-expression", "*=") => Some("*"),
            ("compound-assignment-expression", "/=") => Some("/"),
            ("compound-assignment-expression", "%=") => Some("%"),
            ("compound-assignment-expression", "<<=") => Some("<<"),
            ("compound-assignment-expression", ">>=") => Some(">>"),
            _ => return None,
        };
        if !typed_operator(assignment, operator)
            || !span_within(&body.span, &assignment.span)
            || previous_end > assignment.span.begin.byte
        {
            return None;
        }
        let left =
            self.take(assignment.id, "declaration-reference-expression")?;
        let symbol = left.reference.as_deref()?;
        // Only the innermost active declaration of this source name can
        // receive a C write. A forged Clang symbol cannot bypass shadowing.
        let (name, _) = symbol.rsplit_once('@')?;
        let destination =
            self.locals.iter().rposition(|local| local.name == name)?;
        if self.locals.get(destination)?.symbol != symbol {
            return None;
        }
        if self.loop_counters.contains(&symbol)
            || !source_name_span(left, name)
            || !assigned_local_reference(left, symbol)
            || !span_within(&assignment.span, &left.span)
            || assignment.span.begin.byte != left.span.begin.byte
        {
            return None;
        }
        let (rhs, value_source) = self.expression(assignment.id, 0)?;
        let value = if let Some(operation) = compound_operation {
            // The C compound assignment reads the old unsigned value and
            // stores the checked result exactly once. Only canonical
            // same-line two- or three-character tokens with one space on
            // either side are admitted by this finite source-backed proof.
            let token_gap = if matches!(operator, "<<=" | ">>=") {
                5
            } else {
                4
            };
            if left.span.end.line != value_source.span.begin.line
                || value_source.span.begin.byte.checked_sub(left.span.end.byte)
                    != Some(token_gap)
                || value_source
                    .span
                    .begin
                    .column
                    .checked_sub(left.span.end.column)
                    != Some(token_gap)
            {
                return None;
            }
            checked_u32_binary(
                operation,
                self.locals.get(destination)?.value?,
                rhs,
            )?
        } else {
            rhs
        };
        if !span_within(&assignment.span, &value_source.span)
            || left.span.end.byte >= value_source.span.begin.byte
            || value_source.span.end.byte != assignment.span.end.byte
        {
            return None;
        }
        let local = self.locals.get_mut(destination)?;
        local.value = Some(value);
        local.source = value_source;
        Some((assignment.span.end.byte, value_source))
    }

    /// Prove both operands of a pure, checked `u32` binary operator.
    fn binary_expression(
        &mut self,
        parent: u32,
        depth: usize,
    ) -> Option<(u32, &'node Node)> {
        let expression = self.take(parent, "binary-expression")?;
        let operation = expression.operation.as_deref()?;
        if !typed_operator(expression, operation) {
            return None;
        }
        let child_depth = depth.checked_add(1)?;
        let (left_value, left) = self.expression(expression.id, child_depth)?;
        let (right_value, right) =
            self.expression(expression.id, child_depth)?;
        if !ordered_binary_spans(expression, left, right) {
            return None;
        }
        let value = checked_u32_binary(operation, left_value, right_value)?;
        Some((value, expression))
    }

    /// Prove ordered effects in either braced C arm, including its local
    /// declarations. Branch-local names die at scope exit, while enclosing
    /// writes and output effects survive only for the selected arm.
    fn branch_effects(&mut self, body: &Node, depth: u8) -> Option<()> {
        self.branch_effects_depth(body, (depth, 0))
    }

    fn branch_effects_depth(
        &mut self,
        body: &Node,
        depth: (u8, usize),
    ) -> Option<()> {
        let conditional_depth = depth.0;
        let outer_len = self.locals.len();
        let mut last_end = body.span.begin.byte;
        let mut effects = 0;
        while let Some(node) = self.peek() {
            if node.span.begin.byte >= body.span.end.byte {
                break;
            }
            let expected_parent = body.id;
            if node.parent != expected_parent
                || effects >= MAX_WRITES
                || self.loop_exit.is_some()
            {
                return None;
            }
            last_end = match node.kind.as_str() {
                "declaration-statement" => self.declaration(body, last_end)?.0,
                "binary-expression" | "compound-assignment-expression" => {
                    self.assignment(body, last_end)?.0
                },
                "unary-expression" => self.standalone_step(body, last_end)?,
                "break-statement" | "continue-statement" => {
                    self.loop_exit_statement(body, last_end)?
                },
                "return-statement" => self.return_statement(body, last_end)?,
                "if-statement" => self.conditional(
                    body,
                    last_end,
                    conditional_depth.checked_add(1)?,
                )?,
                "compound-statement" => {
                    self.scoped_branch_effects(body, last_end, depth)?
                },
                "call-expression" => {
                    let output = checked_call(self, body, last_end)?;
                    self.outputs.push(output);
                    output.call.span.end.byte
                },
                _ => return None,
            };
            effects = effects.checked_add(1)?;
        }
        if effects == 0 || last_end >= body.span.end.byte {
            return None;
        }
        self.locals.truncate(outer_len);
        Some(())
    }

    /// Prove unsigned unary operators over one complete expression subtree.
    /// C negation wraps modulo 2^32, just as unsigned binary subtraction.
    /// The newly admitted `+` and `-` require an adjacent parenthesized
    /// operand; unparenthesized `~next` cannot be forged into a new sign.
    /// This is a deliberately bounded source topology, not C token parsing.
    fn complement_or_sign_expression(
        &mut self,
        parent: u32,
        depth: usize,
    ) -> Option<(u32, &'node Node)> {
        let unary = self.take(parent, "unary-expression")?;
        let operation = unary.operation.as_deref()?;
        let (value, operand) =
            self.expression(unary.id, depth.checked_add(1)?)?;
        if !matches!(operation, "~" | "+" | "-")
            || !typed_operator(unary, operation)
            || !span_within(&unary.span, &operand.span)
            || unary.span.begin.byte >= operand.span.begin.byte
            || unary.span.end.byte != operand.span.end.byte
            || (operation != "~"
                && (operand.kind != "parenthesized-expression"
                    || unary.span.begin.line != operand.span.begin.line
                    || operand
                        .span
                        .begin
                        .byte
                        .checked_sub(unary.span.begin.byte)
                        != Some(1)
                    || operand
                        .span
                        .begin
                        .column
                        .checked_sub(unary.span.begin.column)
                        != Some(1)))
        {
            return None;
        }
        Some((
            match operation {
                "~" => !value,
                "+" => value,
                "-" => value.wrapping_neg(),
                _ => return None,
            },
            unary,
        ))
    }

    /// Prove a pure C Boolean tree, including negated comparisons.
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
        // C conditions test whether a scalar is zero, not just the result
        // of an explicit comparison. Admit only a complete source-proven
        // unsigned expression; the ordinary walker rejects side effects,
        // unsupported casts and undefined operations in every subtree.
        if self.peek()?.type_name.as_deref() == Some("u32") {
            let (value, expression) = self.expression(parent, depth)?;
            return Some((value != 0, expression));
        }
        if self.peek()?.kind == "parenthesized-expression" {
            return self.grouped_condition(parent, depth);
        }
        if self.peek()?.kind == "unary-expression" {
            return self.negated_condition(parent, depth);
        }
        let comparison = self.take(parent, "binary-expression")?;
        if matches!(comparison.operation.as_deref(), Some("&&" | "||")) {
            // Restrict logical trees to int-valued Boolean subexpressions.
            // A forged equal-width `==` -> `&&` must not reinterpret two
            // unsigned operands as a different source predicate.
            if self.peek()?.type_name.as_deref() != Some("i32") {
                return None;
            }
            let (left_value, left) = self
                .condition_expression(comparison.id, depth.checked_add(1)?)?;
            if self.peek()?.type_name.as_deref() != Some("i32") {
                return None;
            }
            let (right_value, right) = self
                .condition_expression(comparison.id, depth.checked_add(1)?)?;
            if !clean_i32_operator(comparison)
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
        self.unsigned_comparison(comparison)
    }

    /// A bounded for-loop admits only a literal unsigned bound/stride, or
    /// an exact implicit conversion of a nonnegative int literal.
    fn loop_literal(&mut self, parent: u32) -> Option<(u8, &'node Node)> {
        if !matches!(
            self.peek()?.kind.as_str(),
            "integer-literal" | "cast-expression"
        ) {
            return None;
        }
        let (value, node) = self.expression(parent, 0)?;
        if node.kind == "cast-expression"
            && (node.operation.as_deref() != Some("integral-cast")
                || node.constant_integer.is_none())
        {
            return None;
        }
        Some((u8::try_from(value).ok()?, node))
    }

    /// Admit a braced scope or one direct checked effect as a C branch arm.
    /// Unbraced calls and unsigned assignments have no declaration scope;
    /// both alternatives still receive independent state/output proof.
    fn conditional_arm(
        &mut self,
        statement: &Node,
        previous_end: u32,
        depth: u8,
    ) -> Option<u32> {
        let arm = self.peek()?;
        if arm.parent != statement.id
            || !span_within(&statement.span, &arm.span)
            || previous_end >= arm.span.begin.byte
        {
            return None;
        }
        match arm.kind.as_str() {
            "compound-statement" => {
                let scope = self.take(statement.id, "compound-statement")?;
                if !clean(scope) {
                    return None;
                }
                self.branch_effects(scope, depth)?;
                Some(scope.span.end.byte)
            },
            "call-expression" => {
                let output = checked_call(self, statement, previous_end)?;
                let end = output.call.span.end.byte;
                self.outputs.push(output);
                Some(end)
            },
            "binary-expression" | "compound-assignment-expression" => {
                Some(self.assignment(statement, previous_end)?.0)
            },
            "break-statement" | "continue-statement" => {
                self.loop_exit_statement(statement, previous_end)
            },
            _ => None,
        }
    }

    /// Prove ordered effects in both arms against the same incoming state.
    /// Commit only selected writes and guest output effects.
    fn conditional(
        &mut self,
        body: &Node,
        previous_end: u32,
        depth: u8,
    ) -> Option<u32> {
        let statement = self.take(body.id, "if-statement")?;
        if depth > MAX_NESTED_CONDITIONAL_DEPTH
            || !clean(statement)
            || !span_within(&body.span, &statement.span)
            || previous_end > statement.span.begin.byte
        {
            return None;
        }
        let (take_then, condition) = self.condition(statement)?;
        let starting = self.locals.clone();
        let starting_exit = self.loop_exit;
        let starting_return = self.return_node;
        let output_count = self.outputs.len();
        let then_end =
            self.conditional_arm(statement, condition.span.end.byte, depth)?;
        let then_state = self.locals.clone();
        let then_exit = self.loop_exit;
        let then_return = self.return_node;
        let then_outputs = self.outputs.get(output_count..)?.to_vec();
        self.locals = starting;
        self.loop_exit = starting_exit;
        self.return_node = starting_return;
        self.outputs.truncate(output_count);
        // Without an else, both braced bodies and direct calls end at the
        // Clang if span. A following sibling cannot be swallowed into it.
        if then_end == statement.span.end.byte {
            if self
                .peek()
                .is_some_and(|node| node.span.begin.byte < then_end)
            {
                return None;
            }
            if take_then {
                self.locals = then_state;
                self.loop_exit = then_exit;
                self.return_node = then_return;
                self.outputs.extend(then_outputs);
            }
            return Some(statement.span.end.byte);
        }
        // Clang represents `else if` as an if-statement directly parented
        // to the preceding if, not as a synthetic compound else body.
        // Reprove the entire nested chain against the same incoming state
        // before choosing either arm; no speculative effects may escape.
        let else_arm = self.peek()?;
        if then_end >= else_arm.span.begin.byte {
            return None;
        }
        match else_arm.kind.as_str() {
            "compound-statement"
            | "call-expression"
            | "binary-expression"
            | "compound-assignment-expression" => {
                let end = self.conditional_arm(statement, then_end, depth)?;
                if end != statement.span.end.byte {
                    return None;
                }
            },
            "if-statement" => {
                if else_arm.parent != statement.id
                    || else_arm.span.end.byte != statement.span.end.byte
                {
                    return None;
                }
                let end = self.conditional(
                    statement,
                    then_end,
                    depth.checked_add(1)?,
                )?;
                if end != statement.span.end.byte {
                    return None;
                }
            },
            _ => return None,
        }
        if take_then {
            self.locals = then_state;
            self.loop_exit = then_exit;
            self.return_node = then_return;
            self.outputs.truncate(output_count);
            self.outputs.extend(then_outputs);
        }
        Some(statement.span.end.byte)
    }

    /// Prove a source-ordered conditional, including the unselected pure arm.
    fn conditional_expression(
        &mut self,
        parent: u32,
        depth: usize,
    ) -> Option<(u32, &'node Node)> {
        let conditional = self.take(parent, "conditional-expression")?;
        if !bare_typed_node(conditional)
            || conditional.type_name.as_deref() != Some("u32")
        {
            return None;
        }
        let child_depth = depth.checked_add(1)?;
        let (take_then, condition) =
            self.condition_expression(conditional.id, child_depth)?;
        let (then_value, then_expression) =
            self.expression(conditional.id, child_depth)?;
        let (else_value, else_expression) =
            self.expression(conditional.id, child_depth)?;
        if !ordered_ternary_spans(
            conditional,
            condition,
            then_expression,
            else_expression,
        ) {
            return None;
        }
        // Both alternatives must be pure and defined, even if the
        // C conditional selects only one at runtime.
        Some((
            if take_then {
                then_value
            } else {
                else_value
            },
            conditional,
        ))
    }

    /// Prove one source-ordered declaration list; later initializers may read
    /// earlier initialized names but not later or uninitialized names.
    fn declaration(
        &mut self,
        body: &Node,
        previous_end: u32,
    ) -> Option<(u32, &'node Node)> {
        let statement = self.take(body.id, "declaration-statement")?;
        if !clean(statement)
            || !span_within(&body.span, &statement.span)
            || previous_end > statement.span.begin.byte
        {
            return None;
        }
        let mut previous_variable: Option<&Node> = None;
        let mut first_name_start = None;
        let mut multiple_declarators = false;
        let mut last_source;
        loop {
            let variable = self.take(statement.id, "variable-declaration")?;
            let name = variable.name.as_deref()?;
            let symbol = variable.reference.as_deref()?;
            let (_, offset) = symbol.rsplit_once('@')?;
            let name_start = offset.parse::<u32>().ok()?;
            let name_width = u32::try_from(name.len()).ok()?;
            let name_end = name_start.checked_add(name_width)?;
            if self.locals.len() >= MAX_LOCALS
                || self.locals.iter().any(|local| {
                    local.symbol == symbol
                        || (local.name == name
                            && span_within(&body.span, &local.declaration.span))
                })
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
                || !span_within(&statement.span, &variable.span)
                || statement.span.begin != variable.span.begin
            {
                return None;
            }
            // Pinned Clang shares the declaration's `unsigned ` prefix
            // across every declarator. Comma-separated names begin exactly
            // two source bytes after the previous declarator's end.
            if let Some(previous) = previous_variable {
                multiple_declarators = true;
                if previous.span.end.line != variable.span.end.line
                    || previous.span.end.line != statement.span.begin.line
                    || previous.span.end.byte.checked_add(2) != Some(name_start)
                    || previous.span.end.column.checked_add(2)
                        != name_start
                            .checked_sub(statement.span.begin.byte)?
                            .checked_add(statement.span.begin.column)
                {
                    return None;
                }
            } else {
                first_name_start = Some(name_start);
            }
            // A bare unsigned local stays indeterminate until its first
            // selected plain write. An initializer is proven in C order.
            let (value, source) =
                if self.peek().is_some_and(|node| node.parent == variable.id) {
                    let (value, initializer) =
                        self.expression(variable.id, 0)?;
                    if !span_within(&variable.span, &initializer.span)
                        || initializer.span.end.byte != variable.span.end.byte
                        || initializer.span.begin.byte <= name_start
                    {
                        return None;
                    }
                    (Some(value), initializer)
                } else {
                    if variable.span.begin.line != variable.span.end.line
                        || name_end != variable.span.end.byte
                        || name_width
                            != variable.span.end.column.checked_sub(
                                name_start
                                    .checked_sub(statement.span.begin.byte)?
                                    .checked_add(statement.span.begin.column)?,
                            )?
                    {
                        return None;
                    }
                    (None, variable)
                };
            self.locals.push(Local {
                value,
                declaration: variable,
                name,
                source,
                symbol,
            });
            previous_variable = Some(variable);
            last_source = source;
            if self.peek().is_none_or(|node| node.parent != statement.id) {
                break;
            }
        }
        let last = previous_variable?;
        // A valid C declaration closes with exactly one semicolon. For
        // multi-declarations also pin the shared first `unsigned ` prefix.
        if (multiple_declarators || last_source.kind == "variable-declaration")
            && (last.span.end.byte.checked_add(1)
                != Some(statement.span.end.byte)
                || last.span.end.column.checked_add(1)
                    != Some(statement.span.end.column)
                || last.span.end.line != statement.span.end.line
                || first_name_start != statement.span.begin.byte.checked_add(9))
        {
            return None;
        }
        Some((statement.span.end.byte, last_source))
    }

    /// Evaluate checked `u32` temporaries; narrow only at local stores/output.
    /// Consume the complete exact Clang expression subtree, never a prefix.
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
                Some((literal_u32(leaf)?, leaf))
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
                let cast = self.take(parent, "cast-expression")?;
                if cast.operation.as_deref() == Some("integral-cast") {
                    // Pinned Clang attaches the evaluated unsigned value to
                    // an implicit cast from an unsuffixed, nonnegative int
                    // literal. Prove both the i32 leaf and its exact shared
                    // source span; no signed arithmetic or explicit cast is
                    // admitted by this narrow conversion.
                    if self.peek()?.kind == "integer-literal" {
                        let leaf = self.take(cast.id, "integer-literal")?;
                        let signed = leaf
                            .constant_integer
                            .as_deref()?
                            .parse::<i32>()
                            .ok()?;
                        let value = u32::try_from(signed).ok()?;
                        if leaf.type_name.as_deref() != Some("i32")
                            || leaf.literal.as_deref()
                                != leaf.constant_integer.as_deref()
                            || !bare_literal_metadata(leaf)
                            || cast.type_name.as_deref() != Some("u32")
                            || cast.constant_integer.as_deref()
                                != leaf.constant_integer.as_deref()
                            || !bare_cast_metadata(cast)
                            || cast.span != leaf.span
                            || !span_within(&cast.span, &leaf.span)
                        {
                            return None;
                        }
                        return Some((value, cast));
                    }
                    // Clang's implicit int -> unsigned conversion for a C
                    // comparison stores exactly 0U or 1U. Require an i32
                    // Boolean subtree and identical source spans: an
                    // explicit cast or unrelated signed conversion must
                    // not acquire this proof by being truthy.
                    if !typed_operator(cast, "integral-cast")
                        || self.peek()?.type_name.as_deref() != Some("i32")
                    {
                        return None;
                    }
                    let (selected, predicate) = self
                        .condition_expression(cast.id, depth.checked_add(1)?)?;
                    return (cast.span == predicate.span)
                        .then_some((u32::from(selected), cast));
                }
                if !typed_operator(cast, "lvalue-to-rvalue") {
                    return None;
                }
                let read =
                    self.take(cast.id, "declaration-reference-expression")?;
                if !span_within(&cast.span, &read.span)
                    || cast.span != read.span
                {
                    return None;
                }
                Some((self.referenced(read)?.0, cast))
            },
            "conditional-expression" => {
                self.conditional_expression(parent, depth)
            },
            "unary-expression" => {
                self.complement_or_sign_expression(parent, depth)
            },
            "binary-expression" => self.binary_expression(parent, depth),
            _ => None,
        }
    }

    /// Prove grouping around a complete pure Boolean expression.
    fn grouped_condition(
        &mut self,
        parent: u32,
        depth: usize,
    ) -> Option<(bool, &'node Node)> {
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
        Some((value, grouped))
    }

    /// Replay a closed loop body with checked state and selected outputs.
    /// Each lexical inner declaration dies at the end of its iteration.
    fn loop_body(&mut self, body: &Node) -> Option<()> {
        self.loop_body_depth(body, 0)
    }

    /// Nested C braces preserve writes to enclosing locals, but names
    /// declared inside a brace cannot leak into the following statement.
    fn loop_body_depth(&mut self, body: &Node, depth: usize) -> Option<()> {
        let mut last_end = body.span.begin.byte;
        let mut writes = 0;
        while let Some(node) = self.peek() {
            // One direct `if` or `for` is the whole unbraced `do` body.
            // The trailing condition is not another body effect.
            if node.span.begin.byte >= body.span.end.byte
                || (body.kind == "do-statement" && writes != 0)
            {
                break;
            }
            let expected_parent = body.id;
            if node.parent != expected_parent
                || writes >= MAX_WRITES
                || self.loop_exit.is_some()
            {
                return None;
            }
            last_end = match node.kind.as_str() {
                "declaration-statement" => self.declaration(body, last_end)?.0,
                "binary-expression" | "compound-assignment-expression" => {
                    self.assignment(body, last_end)?.0
                },
                "unary-expression" => self.standalone_step(body, last_end)?,
                "break-statement" | "continue-statement" => {
                    self.loop_exit_statement(body, last_end)?
                },
                "return-statement" => self.return_statement(body, last_end)?,
                "if-statement" => self.conditional(body, last_end, 0)?,
                "switch-statement" => self.static_switch(body, last_end)?,
                "for-statement" => self.static_for(body, last_end)?,
                "compound-statement" => {
                    self.scoped_lexical_body(body, last_end, depth)?
                },
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
        // An unbraced `for` or `while` directly parents exactly one
        // proven control effect; its tail must fill the loop statement.
        // A braced scope instead ends after its final child.
        if matches!(body.kind.as_str(), "for-statement" | "while-statement") {
            (writes == 1 && last_end == body.span.end.byte).then_some(())
        } else if body.kind == "do-statement" {
            (writes == 1 && last_end < body.span.end.byte).then_some(())
        } else {
            (writes > 0 && last_end < body.span.end.byte).then_some(())
        }
    }

    /// A source-proven void return exits the whole function, not just the
    /// innermost loop. Its selected effect is carried through every replay.
    fn return_statement(
        &mut self,
        body: &Node,
        previous_end: u32,
    ) -> Option<u32> {
        if self.loop_exit.is_some() || self.return_node.is_some() {
            return None;
        }
        let statement = self.take(body.id, "return-statement")?;
        if !clean(statement)
            || !span_within(&body.span, &statement.span)
            || previous_end > statement.span.begin.byte
            || statement.span.begin.line != statement.span.end.line
            || statement
                .span
                .end
                .byte
                .checked_sub(statement.span.begin.byte)
                != Some(6)
            || statement
                .span
                .end
                .column
                .checked_sub(statement.span.begin.column)
                != Some(6)
        {
            return None;
        }
        self.return_node = Some(statement);
        self.loop_exit = Some(LoopExit::Return);
        Some(statement.span.end.byte)
    }

    /// Only an exact Clang keyword span may terminate a bounded loop body.
    /// A selected exit must be the last effect in its lexical block; dead
    /// suffixes are not silently discarded without a separate source proof.
    fn loop_exit_statement(
        &mut self,
        body: &Node,
        previous_end: u32,
    ) -> Option<u32> {
        let (kind, exit, width) = match self.peek()?.kind.as_str() {
            "break-statement" => ("break-statement", LoopExit::Break, 5),
            "continue-statement" => {
                ("continue-statement", LoopExit::Continue, 8)
            },
            _ => return None,
        };
        if (self.loop_counters.is_empty() && !self.within_while_body)
            || self.loop_exit.is_some()
        {
            return None;
        }
        let statement = self.take(body.id, kind)?;
        if !clean(statement)
            || !span_within(&body.span, &statement.span)
            || previous_end > statement.span.begin.byte
            || statement.span.begin.line != statement.span.end.line
            || statement
                .span
                .end
                .byte
                .checked_sub(statement.span.begin.byte)
                != Some(width)
            || statement
                .span
                .end
                .column
                .checked_sub(statement.span.begin.column)
                != Some(width)
        {
            return None;
        }
        self.loop_exit = Some(exit);
        Some(statement.span.end.byte)
    }

    /// Prove one pure `!` operand against its complete source-backed subtree.
    fn negated_condition(
        &mut self,
        parent: u32,
        depth: usize,
    ) -> Option<(bool, &'node Node)> {
        let negation = self.take(parent, "unary-expression")?;
        let (value, operand) =
            self.condition_expression(negation.id, depth.checked_add(1)?)?;
        if negation.operation.as_deref() != Some("!")
            || !clean_i32_operator(negation)
            || !span_within(&negation.span, &operand.span)
            || negation.span.begin.byte >= operand.span.begin.byte
            || negation.span.end.byte != operand.span.end.byte
        {
            return None;
        }
        Some((!value, negation))
    }

    fn peek(&self) -> Option<&'node Node> {
        self.nodes.get(self.position)
    }

    fn referenced(&self, read: &Node) -> Option<(u32, &'node Node)> {
        let symbol = read.reference.as_deref()?;
        // Symbol identity alone is insufficient: the AST could falsely
        // bind an inner-source read to an active outer declaration.
        let (name, _) = symbol.rsplit_once('@')?;
        let local =
            self.locals.iter().rev().find(|local| local.name == name)?;
        if local.symbol != symbol {
            return None;
        }
        if !assigned_local_reference(read, symbol)
            || !source_name_span(read, local.name)
            || !symbol_location(local.declaration, local.name, symbol)
            || read.span.begin.byte < local.declaration.span.end.byte
        {
            return None;
        }
        Some((local.value?, local.source))
    }

    fn scoped_branch_effects(
        &mut self,
        body: &Node,
        previous_end: u32,
        depth: (u8, usize),
    ) -> Option<u32> {
        let (conditional_depth, scope_depth) = depth;
        let scope = self.take(body.id, "compound-statement")?;
        if scope_depth >= MAX_NESTED_LOOP_BLOCKS
            || !clean(scope)
            || !span_within(&body.span, &scope.span)
            || previous_end > scope.span.begin.byte
            || scope.span.begin.byte >= scope.span.end.byte
            || scope.span.end.byte >= body.span.end.byte
        {
            return None;
        }
        self.branch_effects_depth(
            scope,
            (conditional_depth, scope_depth.checked_add(1)?),
        )?;
        Some(scope.span.end.byte)
    }

    /// Replay one lexical C block, preserving enclosing writes while
    /// discarding declarations whose lifetimes end at its closing brace.
    fn scoped_lexical_body(
        &mut self,
        body: &Node,
        previous_end: u32,
        depth: usize,
    ) -> Option<u32> {
        let scope = self.take(body.id, "compound-statement")?;
        if depth >= MAX_NESTED_LOOP_BLOCKS
            || !clean(scope)
            || !span_within(&body.span, &scope.span)
            || previous_end > scope.span.begin.byte
            || scope.span.begin.byte >= scope.span.end.byte
            || scope.span.end.byte >= body.span.end.byte
        {
            return None;
        }
        let outer_len = self.locals.len();
        self.loop_body_depth(scope, depth.checked_add(1)?)?;
        self.locals.truncate(outer_len);
        Some(scope.span.end.byte)
    }

    /// Admit discarded prefix/postfix unsigned steps on an active local.
    /// The whole unary expression must be one contiguous source token:
    /// `++name`, `name++`, `--name` or `name--`, with no hidden operand.
    fn standalone_step(
        &mut self,
        body: &Node,
        previous_end: u32,
    ) -> Option<u32> {
        let step = self.take(body.id, "unary-expression")?;
        let operation = step.operation.as_deref()?;
        if !matches!(operation, "++" | "--")
            || !typed_operator(step, operation)
            || !span_within(&body.span, &step.span)
            || previous_end > step.span.begin.byte
        {
            return None;
        }
        let read = self.take(step.id, "declaration-reference-expression")?;
        let symbol = read.reference.as_deref()?;
        let (name, _) = symbol.rsplit_once('@')?;
        let destination =
            self.locals.iter().rposition(|local| local.name == name)?;
        if self.locals.get(destination)?.symbol != symbol
            || self.loop_counters.contains(&symbol)
            || !assigned_local_reference(read, symbol)
            || !source_name_span(read, name)
            || !symbol_location(
                self.locals.get(destination)?.declaration,
                name,
                symbol,
            )
            || !span_within(&step.span, &read.span)
            || step.span.begin.line != step.span.end.line
            || read.span.begin.line != read.span.end.line
            || step.span.begin.line != read.span.begin.line
        {
            return None;
        }
        let prefix = read.span.begin.byte.checked_sub(step.span.begin.byte)
            == Some(2)
            && read.span.begin.column.checked_sub(step.span.begin.column)
                == Some(2)
            && read.span.end == step.span.end;
        let postfix = step.span.begin == read.span.begin
            && step.span.end.byte.checked_sub(read.span.end.byte) == Some(2)
            && step.span.end.column.checked_sub(read.span.end.column)
                == Some(2);
        if !prefix && !postfix {
            return None;
        }
        let previous = self.locals.get(destination)?.value?;
        let updated = if operation == "++" {
            previous.wrapping_add(1)
        } else {
            previous.wrapping_sub(1)
        };
        let local = self.locals.get_mut(destination)?;
        local.value = Some(updated);
        local.source = step;
        Some(step.span.end.byte)
    }

    /// Prove a bounded unsigned `for` induction in either direction
    /// and replay its source-checked body, or discard a zero-trip shadow.
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
            || self.loop_counters.len() >= MAX_NESTED_FOR_LOOPS
        {
            return None;
        }
        let outer_len = self.locals.len();
        let (declaration_end, _) =
            self.declaration(statement, statement.span.begin.byte)?;
        let counter = self.locals.get(outer_len)?;
        // The finite induction proof still admits only byte-range counters.
        let start = u8::try_from(counter.value?).ok()?;
        let symbol = counter.symbol;
        let (counter_name, _) = symbol.rsplit_once('@')?;
        let comparison = self.take(statement.id, "binary-expression")?;
        let load = self.take(comparison.id, "cast-expression")?;
        let read = self.take(load.id, "declaration-reference-expression")?;
        let (bound, bound_node) = self.loop_literal(comparison.id)?;
        if !typed_bounded_loop_comparison(comparison, load, bound_node)
            || (comparison.operation.as_deref() == Some("<")
                && start > MAX_STATIC_LOOP_ITERATIONS)
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
        {
            return None;
        }
        let not_equal = comparison.operation.as_deref() == Some("!=");
        let inclusive =
            matches!(comparison.operation.as_deref(), Some("<=" | ">="));
        let separated = comparison.span.end.byte < self.peek()?.span.begin.byte;
        let increment_kind = self.peek()?.kind.as_str();
        if !matches!(
            increment_kind,
            "unary-expression"
                | "compound-assignment-expression"
                | "binary-expression"
        ) {
            return None;
        }
        let increment = self.take(statement.id, increment_kind)?;
        let operation = increment.operation.as_deref()?;
        let increment_read =
            self.take(increment.id, "declaration-reference-expression")?;
        let (stride, step_descending) = match increment_kind {
            "unary-expression" => {
                // A discarded prefix/postfix increment or decrement has
                // no observable result beyond the proven counter update.
                let prefix = increment.span.end == increment_read.span.end
                    && increment.span.begin.byte
                        < increment_read.span.begin.byte;
                let postfix = increment.span.begin == increment_read.span.begin
                    && increment.span.end.line == increment_read.span.end.line
                    && increment
                        .span
                        .end
                        .byte
                        .checked_sub(increment_read.span.end.byte)
                        == Some(2)
                    && increment
                        .span
                        .end
                        .column
                        .checked_sub(increment_read.span.end.column)
                        == Some(2);
                (typed_operator(increment, operation)
                    && matches!(operation, "++" | "--")
                    && (prefix || postfix))
                    .then_some((1, operation == "--"))?
            },
            "compound-assignment-expression" => {
                // Prove a positive, bounded literal stride from the exact
                // typed right operand and source span, not from the bound.
                let (stride, step) = self.loop_literal(increment.id)?;
                (typed_operator(increment, increment.operation.as_deref()?)
                    && matches!(
                        increment.operation.as_deref(),
                        Some("+=" | "-=")
                    )
                    && (1..=MAX_STATIC_LOOP_ITERATIONS).contains(&stride)
                    && increment.span.begin.byte
                        == increment_read.span.begin.byte
                    && increment.span.end == step.span.end
                    && increment_read.span.end.line == step.span.end.line
                    && step.span.begin.line == step.span.end.line
                    && increment_read
                        .span
                        .end
                        .byte
                        .checked_add(2)
                        .is_some_and(|minimum| minimum <= step.span.begin.byte)
                    && step
                        .span
                        .begin
                        .byte
                        .checked_sub(increment_read.span.end.byte)
                        .is_some_and(|gap| gap <= 16)
                    && span_within(&increment.span, &step.span))
                .then_some((
                    stride,
                    increment.operation.as_deref() == Some("-="),
                ))?
            },
            "binary-expression" => {
                // A conventional `i = i + 1U` or `i = i - 2U` step
                // reads the same induction variable exactly once. The
                // two source operators each have one adjacent space;
                // neither reassignment from another local nor a nested
                // effect can masquerade as an induction update.
                let rhs = self.take(increment.id, "binary-expression")?;
                let step_operator = rhs.operation.as_deref()?;
                let step_load = self.take(rhs.id, "cast-expression")?;
                let rhs_read = self
                    .take(step_load.id, "declaration-reference-expression")?;
                let (stride, step) = self.loop_literal(rhs.id)?;
                let step_line = rhs.span.begin.line;
                (typed_operator(increment, "=")
                    && matches!(step_operator, "+" | "-")
                    && typed_operator(rhs, step_operator)
                    && typed_operator(step_load, "lvalue-to-rvalue")
                    && assigned_local_reference(rhs_read, symbol)
                    && source_name_span(rhs_read, counter_name)
                    && (1..=MAX_STATIC_LOOP_ITERATIONS).contains(&stride)
                    && increment.span.begin == increment_read.span.begin
                    && increment.span.end == rhs.span.end
                    && step_load.span == rhs_read.span
                    && rhs.span.begin == step_load.span.begin
                    && rhs.span.end == step.span.end
                    && span_within(&increment.span, &rhs.span)
                    && span_within(&rhs.span, &step.span)
                    && increment_read.span.end.line == step_line
                    && rhs.span.end.line == step_line
                    && step.span.begin.line == step_line
                    && step.span.end.line == step_line
                    && rhs
                        .span
                        .begin
                        .byte
                        .checked_sub(increment_read.span.end.byte)
                        == Some(3)
                    && rhs
                        .span
                        .begin
                        .column
                        .checked_sub(increment_read.span.end.column)
                        == Some(3)
                    && step
                        .span
                        .begin
                        .byte
                        .checked_sub(step_load.span.end.byte)
                        == Some(3)
                    && step
                        .span
                        .begin
                        .column
                        .checked_sub(step_load.span.end.column)
                        == Some(3))
                .then_some((stride, step_operator == "-"))?
            },
            _ => return None,
        };
        // `!=` determines direction from its proven step. For ordered
        // comparisons the step must agree with the guard's direction.
        let descending = if not_equal {
            step_descending
        } else {
            matches!(comparison.operation.as_deref(), Some(">" | ">="))
        };
        if step_descending != descending {
            return None;
        }
        if !assigned_local_reference(increment_read, symbol)
            || !span_within(&statement.span, &increment.span)
            || !span_within(&increment.span, &increment_read.span)
            || !separated
        {
            return None;
        }
        // Clang directly parents an unbraced nested `for` or `if` to
        // its outer `for`, without an invented compound scope. The single
        // child must fill the entire remainder of the outer statement.
        let unbraced_control = matches!(
            self.peek()?.kind.as_str(),
            "for-statement" | "if-statement"
        );
        let loop_body = if unbraced_control {
            statement
        } else {
            self.take(statement.id, "compound-statement")?
        };
        if (!unbraced_control && !clean(loop_body))
            || !span_within(&statement.span, &loop_body.span)
            || increment.span.end.byte >= self.peek()?.span.begin.byte
            || (!unbraced_control
                && loop_body.span.end.byte != statement.span.end.byte)
            || (unbraced_control
                && (self.peek()?.parent != statement.id
                    || self.peek()?.span.end.byte != statement.span.end.byte))
        {
            return None;
        }
        let body_start = self.position;
        self.loop_counters.push(symbol);
        let mut body_end = None;
        let continues = |value: u8| {
            if not_equal {
                value != bound
            } else if descending {
                value > bound || (inclusive && value == bound)
            } else {
                value < bound || (inclusive && value == bound)
            }
        };
        if !continues(start) {
            // Even a nonexecuted for body must be a complete, admissible
            // source subtree. No speculative state or output may escape.
            let starting_locals = self.locals.clone();
            let starting_outputs = self.outputs.len();
            let starting_return = self.return_node;
            self.loop_body(loop_body)?;
            body_end = Some(self.position);
            self.locals = starting_locals;
            self.loop_exit = None;
            self.return_node = starting_return;
            self.outputs.truncate(starting_outputs);
        }
        let mut counter_value = start;
        let mut trips = 0;
        while continues(counter_value) {
            if trips >= MAX_STATIC_LOOP_ITERATIONS
                || (not_equal
                    && ((descending && counter_value < bound)
                        || (!descending && counter_value > bound)))
            {
                // `!=` must reach the bound without crossing it; a
                // would-be unsigned wrap or nondivisible stride refuses.
                return None;
            }
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
            if current_counter.value != Some(u32::from(counter_value)) {
                return None;
            }
            match self.loop_exit {
                Some(LoopExit::Break) => {
                    self.loop_exit = None;
                    break;
                },
                Some(LoopExit::Return) => break,
                _ => self.loop_exit = None,
            }
            counter_value = if descending {
                counter_value.checked_sub(stride)?
            } else {
                counter_value.checked_add(stride)?
            };
            current_counter.value = Some(u32::from(counter_value));
            current_counter.source = increment;
            trips = trips.checked_add(1)?;
        }
        self.position = body_end?;
        self.locals.truncate(outer_len);
        (self.loop_counters.pop()? == symbol).then_some(statement.span.end.byte)
    }

    /// Replay a source-proven `while (predicate) { ... }` over known locals.
    /// Recheck each condition after a body execution, or validate a skipped
    /// body on shadow state without publishing its writes or output effects.
    /// Unsupported bodies and unbounded loops refuse.
    fn static_while(&mut self, body: &Node, previous_end: u32) -> Option<u32> {
        let statement = self.take(body.id, "while-statement")?;
        if !clean(statement)
            || !span_within(&body.span, &statement.span)
            || previous_end > statement.span.begin.byte
            || !self.loop_counters.is_empty()
            || self.within_while_body
        {
            return None;
        }
        let condition_start = self.position;
        let outer_len = self.locals.len();
        let mut body_end = None;
        self.within_while_body = true;
        for iteration in 0..=MAX_STATIC_LOOP_ITERATIONS {
            self.position = condition_start;
            let (continue_loop, condition) = self.condition(statement)?;
            // For an unbraced `while`, Clang parents its sole `if`
            // directly to the loop. There is no synthetic brace scope.
            let unbraced_if = self.peek()?.kind == "if-statement";
            let first_body_byte = self.peek()?.span.begin.byte;
            let loop_body = if unbraced_if {
                statement
            } else {
                self.take(statement.id, "compound-statement")?
            };
            if (!unbraced_if && !clean(loop_body))
                || !span_within(&statement.span, &loop_body.span)
                || condition.span.end.byte
                    >= if unbraced_if {
                        first_body_byte
                    } else {
                        loop_body.span.begin.byte
                    }
                || (!unbraced_if
                    && loop_body.span.end.byte != statement.span.end.byte)
                || (unbraced_if
                    && (self.peek()?.parent != statement.id
                        || self.peek()?.span.end.byte
                            != statement.span.end.byte))
            {
                return None;
            }
            if !continue_loop {
                if let Some(end) = body_end {
                    self.position = end;
                } else {
                    // A skipped body is still a complete Clang subtree.
                    // Prove it against shadow state, then discard every
                    // speculative local write and guest output effect.
                    let starting_locals = self.locals.clone();
                    let starting_outputs = self.outputs.len();
                    let starting_return = self.return_node;
                    self.loop_body(loop_body)?;
                    self.locals = starting_locals;
                    self.outputs.truncate(starting_outputs);
                    self.loop_exit = None;
                    self.return_node = starting_return;
                }
                self.within_while_body = false;
                return Some(statement.span.end.byte);
            }
            if iteration == MAX_STATIC_LOOP_ITERATIONS {
                return None;
            }
            self.loop_body(loop_body)?;
            if body_end.is_some_and(|end| self.position != end) {
                return None;
            }
            body_end = Some(self.position);
            // Locals declared in the braces never escape an iteration.
            self.locals.truncate(outer_len);
            if matches!(
                self.loop_exit,
                Some(LoopExit::Break | LoopExit::Return)
            ) {
                if self.loop_exit == Some(LoopExit::Break) {
                    self.loop_exit = None;
                }
                self.within_while_body = false;
                return Some(statement.span.end.byte);
            }
            self.loop_exit = None;
            // A source-proven `continue` goes to the next predicate check.
        }
        None
    }

    /// Prove C `do { ... } while (predicate);`: the body executes first,
    /// and its pure condition is evaluated against each updated state.
    /// Reject only after a complete source-backed bounded exit is witnessed.
    fn static_do_while(
        &mut self,
        body: &Node,
        previous_end: u32,
    ) -> Option<u32> {
        let statement = self.take(body.id, "do-statement")?;
        if !clean(statement)
            || !span_within(&body.span, &statement.span)
            || previous_end > statement.span.begin.byte
            || !self.loop_counters.is_empty()
            || self.within_while_body
        {
            return None;
        }
        // Clang parents an unbraced `if` or `for` directly to `do`,
        // followed by its condition. Never invent a compound scope.
        let unbraced_control = matches!(
            self.peek()?.kind.as_str(),
            "if-statement" | "for-statement"
        );
        let first_body_byte = self.peek()?.span.begin.byte;
        let direct_body_end = self.peek()?.span.end.byte;
        let loop_body = if unbraced_control {
            statement
        } else {
            self.take(statement.id, "compound-statement")?
        };
        if (!unbraced_control && !clean(loop_body))
            || !span_within(&statement.span, &loop_body.span)
            || statement.span.begin.byte >= first_body_byte
            || (unbraced_control
                && (self.peek()?.parent != statement.id
                    || direct_body_end >= statement.span.end.byte))
        {
            return None;
        }
        let body_start = self.position;
        let outer_len = self.locals.len();
        let mut body_end = None;
        let mut condition_end = None;
        self.within_while_body = true;
        for _ in 0..MAX_STATIC_LOOP_ITERATIONS {
            self.position = body_start;
            self.loop_body(loop_body)?;
            if body_end.is_some_and(|end| self.position != end) {
                return None;
            }
            body_end = Some(self.position);
            // Braced declarations are not visible to the trailing test.
            self.locals.truncate(outer_len);
            let selected_exit = self.loop_exit.take();
            // The trailing condition is a complete source subtree even if
            // `break` skips it at runtime. `continue` must check it.
            let (continue_loop, condition) = self.condition(statement)?;
            if !span_within(&statement.span, &condition.span)
                || (if unbraced_control {
                    direct_body_end
                } else {
                    loop_body.span.end.byte
                }) >= condition.span.begin.byte
                || statement
                    .span
                    .end
                    .byte
                    .checked_sub(condition.span.end.byte)?
                    != 1
                || condition_end.is_some_and(|end| self.position != end)
            {
                return None;
            }
            condition_end = Some(self.position);
            if matches!(selected_exit, Some(LoopExit::Break | LoopExit::Return))
                || !continue_loop
            {
                self.loop_exit = (selected_exit == Some(LoopExit::Return))
                    .then_some(LoopExit::Return);
                self.within_while_body = false;
                return Some(statement.span.end.byte);
            }
        }
        None
    }

    /// Admit up to eight distinct source-ordered case labels, including
    /// nested empty-label groups, and one final default. Each group must
    /// prove one pure output and its own switch-local break; only the
    /// selected effect escapes into the enclosing C loop.
    #[expect(
        clippy::cognitive_complexity,
        reason = "closed Clang ancestry and source-ordered switch outputs"
    )]
    #[expect(
        clippy::too_many_lines,
        reason = "closed source-ordered grouped switch proof"
    )]
    fn static_switch(&mut self, body: &Node, previous_end: u32) -> Option<u32> {
        let statement = self.take(body.id, "switch-statement")?;
        if !clean(statement)
            || !span_within(&body.span, &statement.span)
            || previous_end > statement.span.begin.byte
            || self.loop_exit.is_some()
        {
            return None;
        }
        let (selected, condition) = self.expression(statement.id, 0)?;
        // Require ordinary `switch (` punctuation. A Clang AST supplied
        // without source text cannot silently invent a different construct.
        if condition.span.begin.line != statement.span.begin.line
            || condition
                .span
                .begin
                .byte
                .checked_sub(statement.span.begin.byte)
                != Some(8)
            || condition
                .span
                .begin
                .column
                .checked_sub(statement.span.begin.column)
                != Some(8)
        {
            return None;
        }
        let scope = self.take(statement.id, "compound-statement")?;
        if !clean(scope)
            || !span_within(&statement.span, &scope.span)
            || scope.span.end != statement.span.end
            || condition.span.end.byte >= scope.span.begin.byte
        {
            return None;
        }
        let mut previous_arm_end = scope.span.begin.byte;
        let mut case_values = Vec::new();
        let mut selected_output = None;
        while self.peek()?.kind == "case-statement" {
            let mut case = self.take(scope.id, "case-statement")?;
            let outer_case_end = &case.span.end;
            let mut previous_label_end = previous_arm_end;
            let mut group_selected = false;
            loop {
                if case_values.len() >= 8
                    || !clean(case)
                    || !span_within(&scope.span, &case.span)
                    || previous_label_end >= case.span.begin.byte
                    || case.span.end != *outer_case_end
                {
                    return None;
                }
                let constant = self.take(case.id, "constant-expression")?;
                let label = self.take(constant.id, "integer-literal")?;
                let case_value = literal_u32(label)?;
                if constant.type_name.as_deref() != Some("u32")
                    || !bare_cast_metadata(constant)
                    || constant.operation.is_some()
                    || constant.constant_integer.as_deref()
                        != Some(case_value.to_string().as_str())
                    || !span_within(&case.span, &constant.span)
                    || constant.span != label.span
                    || constant.span.begin.byte.checked_sub(case.span.begin.byte)
                        != Some(5)
                    || constant
                        .span
                        .begin
                        .column
                        .checked_sub(case.span.begin.column)
                        != Some(5)
                    || constant.span.begin.line != case.span.begin.line
                    || case_values.contains(&case_value)
                {
                    return None;
                }
                case_values.push(case_value);
                group_selected |= selected == case_value;
                previous_label_end = constant.span.end.byte;
                // Clang nests adjacent labels with no intervening statement:
                // `case 0U: case 2U: putchar(...);` is a single C arm.
                // A case with any preceding effect is *not* a label group.
                if !self.peek().is_some_and(|node| {
                    node.kind == "case-statement" && node.parent == case.id
                }) {
                    break;
                }
                let nested = self.take(case.id, "case-statement")?;
                if !span_within(&case.span, &nested.span)
                    || nested.span.end != case.span.end
                    || nested.span.begin.byte <= previous_label_end
                {
                    return None;
                }
                case = nested;
            }
            let output = checked_call(self, case, previous_label_end)?;
            if output.call.span.end != *outer_case_end {
                return None;
            }
            previous_arm_end = self.switch_break(scope, outer_case_end.byte)?;
            if group_selected {
                selected_output = Some(output);
            }
        }
        if case_values.is_empty() {
            return None;
        }
        let default = self.take(scope.id, "default-statement")?;
        if !clean(default)
            || !span_within(&scope.span, &default.span)
            || previous_arm_end >= default.span.begin.byte
        {
            return None;
        }
        let default_output =
            checked_call(self, default, default.span.begin.byte)?;
        if default_output.call.span.end != default.span.end
            || default_output.call.span.begin.line <= default.span.begin.line
        {
            return None;
        }
        let last_break = self.switch_break(scope, default.span.end.byte)?;
        if last_break >= scope.span.end.byte
            || self
                .peek()
                .is_some_and(|node| node.span.begin.byte < scope.span.end.byte)
        {
            return None;
        }
        self.outputs.push(selected_output.unwrap_or(default_output));
        Some(statement.span.end.byte)
    }

    /// Clang parents switch-local break statements to the switch's braces;
    /// unlike a loop break, they must not alter the enclosing loop state.
    fn switch_break(&mut self, scope: &Node, previous_end: u32) -> Option<u32> {
        let statement = self.take(scope.id, "break-statement")?;
        if !clean(statement)
            || !span_within(&scope.span, &statement.span)
            || previous_end >= statement.span.begin.byte
            || statement.span.begin.line != statement.span.end.line
            || statement
                .span
                .end
                .byte
                .checked_sub(statement.span.begin.byte)
                != Some(5)
            || statement
                .span
                .end
                .column
                .checked_sub(statement.span.begin.column)
                != Some(5)
        {
            return None;
        }
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

    /// Prove both C unsigned comparison operands as complete pure expressions.
    /// Their source order, checked arithmetic, and exact Clang types are
    /// required even when a branch is determined at compile time.
    fn unsigned_comparison(
        &mut self,
        comparison: &'node Node,
    ) -> Option<(bool, &'node Node)> {
        let (left_value, left) = self.expression(comparison.id, 0)?;
        let (right_value, right) = self.expression(comparison.id, 0)?;
        if !ordered_binary_spans(comparison, left, right) {
            return None;
        }
        let selected =
            checked_condition_comparison(comparison, left_value, right_value)?;
        Some((selected, comparison))
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

/// Require all three operands of `condition ? then : else` in exact C
/// lexical order, including the complete selected and unselected subtrees.
const fn ordered_ternary_spans(
    expression: &Node,
    condition: &Node,
    then_expression: &Node,
    else_expression: &Node,
) -> bool {
    span_within(&expression.span, &condition.span)
        && span_within(&expression.span, &then_expression.span)
        && span_within(&expression.span, &else_expression.span)
        && expression.span.begin.byte == condition.span.begin.byte
        && condition.span.end.byte < then_expression.span.begin.byte
        && then_expression.span.end.byte < else_expression.span.begin.byte
        && else_expression.span.end.byte == expression.span.end.byte
}

/// Evaluate exact unsigned-C operators after both source operands are proven.
/// C `unsigned` arithmetic wraps modulo 2^32; narrowing happens at stores.
fn checked_u32_binary(operator: &str, left: u32, right: u32) -> Option<u32> {
    match operator {
        "+" => Some(left.wrapping_add(right)),
        "-" => Some(left.wrapping_sub(right)),
        "*" => Some(left.wrapping_mul(right)),
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

/// An implicit C integral conversion must not hide side effects or unrelated
/// Clang fields. Its evaluated value is checked separately against the leaf.
const fn bare_cast_metadata(node: &Node) -> bool {
    node.name.is_none()
        && node.reference.is_none()
        && node.literal.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
}

/// The i32 leaf is solely a normalized integer literal, not a symbol or cast.
const fn bare_literal_metadata(node: &Node) -> bool {
    node.name.is_none()
        && node.reference.is_none()
        && node.operation.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
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

fn typed_bounded_loop_comparison(
    node: &Node,
    counter: &Node,
    bound: &Node,
) -> bool {
    // This bounded source shape admits one ASCII space on either side of
    // the comparison token. In particular, a forged `<=` -> `<` or `>` ->
    // `>=` AST mutation cannot change the trip count while reusing the
    // same token geometry. Other whitespace spellings fail closed.
    let separator = match node.operation.as_deref() {
        Some("<" | ">") => 3,
        Some("<=" | ">=" | "!=") => 4,
        _ => return false,
    };
    bound.span.begin.byte.checked_sub(counter.span.end.byte) == Some(separator)
        && bound.span.begin.column.checked_sub(counter.span.end.column)
            == Some(separator)
        && node.span.begin.line == counter.span.end.line
        && counter.span.end.line == bound.span.begin.line
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

/// Accept no extraneous metadata on an i32 unary or binary operator.
fn clean_i32_operator(node: &Node) -> bool {
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
    if !clean_i32_operator(node) {
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

/// A plain Clang local read/write occupies exactly its source identifier
/// width. This is necessary but cannot recover the spelling from a JSON-only
/// artifact; same-width forged names need upstream source-digest validation.
fn source_name_span(reference: &Node, name: &str) -> bool {
    reference.span.begin.line == reference.span.end.line
        && reference
            .span
            .end
            .byte
            .checked_sub(reference.span.begin.byte)
            == u32::try_from(name.len()).ok()
        && reference
            .span
            .end
            .column
            .checked_sub(reference.span.begin.column)
            == u32::try_from(name.len()).ok()
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
            let (value, source) = flow.referenced(read)?;
            Some((u8::try_from(value).ok()?, source))
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
        loop_counters: Vec::new(),
        within_while_body: false,
        loop_exit: None,
        return_node: None,
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
            "binary-expression" | "compound-assignment-expression" => {
                let (end, _source) = flow
                    .assignment(body, last_end)
                    .ok_or(FrontendJsonError::Unsupported)?;
                last_end = end;
            },
            "unary-expression" => {
                last_end = flow
                    .standalone_step(body, last_end)
                    .ok_or(FrontendJsonError::Unsupported)?;
            },
            "switch-statement" => {
                last_end = flow
                    .static_switch(body, last_end)
                    .ok_or(FrontendJsonError::Unsupported)?;
            },
            "for-statement" => {
                last_end = flow
                    .static_for(body, last_end)
                    .ok_or(FrontendJsonError::Unsupported)?;
            },
            "while-statement" => {
                last_end = flow
                    .static_while(body, last_end)
                    .ok_or(FrontendJsonError::Unsupported)?;
            },
            "do-statement" => {
                last_end = flow
                    .static_do_while(body, last_end)
                    .ok_or(FrontendJsonError::Unsupported)?;
            },
            "compound-statement" => {
                last_end = flow
                    .scoped_lexical_body(body, last_end, 0)
                    .ok_or(FrontendJsonError::Unsupported)?;
            },
            "if-statement" if remaining_writes >= 2 => {
                last_end = flow
                    .conditional(body, last_end, 0)
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
        if flow.loop_exit == Some(LoopExit::Return) {
            break;
        }
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
    let returned = if flow.loop_exit == Some(LoopExit::Return) {
        if flow.peek().is_some() {
            return Err(FrontendJsonError::Unsupported);
        }
        flow.return_node
    } else if flow.peek().is_some() {
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
