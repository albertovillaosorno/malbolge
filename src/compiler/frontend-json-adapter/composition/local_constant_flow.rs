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
//   - Reject aliases, unknown expressions, loops and excess statements.
// - Usage:
//   - Invoked after the original single-local proof fails.
// - Defaults:
//   - At least two independently declared locals are required.

//! Source-backed constant propagation with bounded conditional selection.

use super::local_initialized_output::{
    assigned_local_reference, clean, correct_node, emit_verified_local_byte,
    literal_byte, span_within, typed_operator,
};
use super::{Artifact, FrontendJsonError, Node, StorageDuration};

const MAX_LOCALS: usize = 8;
const MAX_WRITES: usize = 16;
const MAX_EXPRESSION_DEPTH: usize = 8;

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
    nodes: &'node [Node],
    position: usize,
}

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
        if !assigned_local_reference(left, symbol)
            || !span_within(&assignment.span, &left.span)
            || assignment.span.begin.byte != left.span.begin.byte
        {
            return None;
        }
        let (byte, value_source) = self.expression(assignment.id, 0)?;
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

    /// Prove the complete `if ((byte & mask) == literal)` condition.
    fn condition(&mut self, statement: &Node) -> Option<(bool, &'node Node)> {
        let comparison = self.take(statement.id, "binary-expression")?;
        let parentheses =
            self.take(comparison.id, "parenthesized-expression")?;
        let (left, expression) = self.expression(parentheses.id, 0)?;
        let right = self.take(comparison.id, "integer-literal")?;
        let right_value = literal_byte(right)?;
        let separated = parentheses.span.end.byte < right.span.begin.byte;
        if !typed_equality(comparison)
            || parentheses.type_name.as_deref() != Some("u32")
            || !bare_typed_node(parentheses)
            || !span_within(&statement.span, &comparison.span)
            || !span_within(&comparison.span, &parentheses.span)
            || !span_within(&parentheses.span, &expression.span)
            || expression.operation.as_deref() != Some("&")
            || !span_within(&comparison.span, &right.span)
            || comparison.span.begin.byte != parentheses.span.begin.byte
            || parentheses.span.begin.byte >= expression.span.begin.byte
            || expression.span.end.byte >= parentheses.span.end.byte
            || !separated
            || right.span.end.byte != comparison.span.end.byte
        {
            return None;
        }
        Some((left == right_value, comparison))
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
        let (byte, initializer) = self.expression(variable.id, 0)?;
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

    /// Consume the complete exact Clang expression subtree, never a prefix.
    #[expect(
        clippy::cognitive_complexity,
        reason = "bounded AST expression proof"
    )]
    fn expression(
        &mut self,
        parent: u32,
        depth: usize,
    ) -> Option<(u8, &'node Node)> {
        if depth > MAX_EXPRESSION_DEPTH {
            return None;
        }
        let node = self.peek()?;
        match node.kind.as_str() {
            "integer-literal" => {
                let leaf = self.take(parent, "integer-literal")?;
                Some((literal_byte(leaf)?, leaf))
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
                Some((self.referenced(read)?.0, load))
            },
            "binary-expression" => {
                let expression = self.take(parent, "binary-expression")?;
                let operation = expression.operation.as_deref()?;
                if !matches!(operation, "+" | "-" | "^" | "&")
                    || !typed_operator(expression, operation)
                {
                    return None;
                }
                let (left_value, left) =
                    self.expression(expression.id, depth.checked_add(1)?)?;
                let (right_value, right) =
                    self.expression(expression.id, depth.checked_add(1)?)?;
                if !span_within(&expression.span, &left.span)
                    || !span_within(&expression.span, &right.span)
                    || expression.span.begin.byte != left.span.begin.byte
                    || left.span.end.byte >= right.span.begin.byte
                    || right.span.end.byte != expression.span.end.byte
                {
                    return None;
                }
                let value = match operation {
                    "+" => left_value.checked_add(right_value)?,
                    "-" => left_value.checked_sub(right_value)?,
                    "^" => left_value ^ right_value,
                    "&" => left_value & right_value,
                    _ => return None,
                };
                Some((value, expression))
            },
            _ => None,
        }
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

fn typed_equality(node: &Node) -> bool {
    node.type_name.as_deref() == Some("i32")
        && node.operation.as_deref() == Some("==")
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
                || conversion.span != load.span
                || load.span != read.span
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
            Some((byte, expression))
        },
        _ => None,
    }
}

/// Admit exactly one source-proven output effect after the local writes.
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
        nodes: &input.nodes,
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
    let OutputCall { byte, call, source } =
        checked_call(&mut flow, body, last_end)
            .ok_or(FrontendJsonError::Unsupported)?;
    let returned = if flow.peek().is_some() {
        let node = flow
            .take(body.id, "return-statement")
            .ok_or(FrontendJsonError::Unsupported)?;
        if !clean(node)
            || !span_within(&body.span, &node.span)
            || call.span.end.byte > node.span.begin.byte
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
    emit_verified_local_byte(
        &input,
        super::local_initialized_output::ProvenLocalOutput {
            body,
            byte,
            call,
            function,
            returned,
            source,
        },
    )
}
