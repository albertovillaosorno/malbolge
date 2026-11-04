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
//   - Closed normalized Clang-JSON to typed void/literal-output adapter.
// - Must-Not:
//   - Parse C, reinterpret calls, silently drop effects, or bypass typed
//     admission.
// - Allows:
//   - Inputs: bounded version-one normalized frontend JSON bytes.
//   - Outputs: canonical MCTI for no-effect void or witnessed literal output.
//   - Side effects: none.
// - Split-When:
//   - General C byte-I/O gains independently modeled effect semantics.
// - Merge-When:
//   - Native frontend composition owns equivalent validated JSON decoding.
// - Summary:
//   - Connects exact C semantics to tested typed void and literal-output slices.
// - Description:
//   - Unknown nodes, additional effects, identity/profile drift all fail closed.
// - Usage:
//   - `canonical_guest_typed_ir(json)` yields MCTI and verified effect mode.
// - Defaults:
//   - Does not infer missing Clang metadata or source identity.
//

//! Closed, dependency-isolated adapter from normalized C frontend JSON to MCTI.
//! This is an artifact boundary, not a native C frontend or executable entry ABI.

#[path = "../../typed-ir/composition/lib.rs"]
pub mod typed;

#[cfg(test)]
use malbolge as _;
use serde::Deserialize;
use std::iter::once;
use std::str;
use typed::{
    BasicBlock, BasicBlockSpec, FrontendArtifact, FrontendArtifactSpec,
    FrontendFallthroughVoidFunctionSpec, FrontendPosition, FrontendReturnVoidFunction,
    FrontendReturnVoidFunctionSpec, FrontendSpan, Function, FunctionSpec, Instruction,
    IntegerConstant, LocatedInstruction, Module, ModuleSpec, TypeId, ValueId, canonical_bytes,
    canonical_module, lower_frontend_artifact,
};

const EXPECTED_ABI: &str = "malbolge-c32-v1";
const EXPECTED_ARTIFACT: &str = "malbolge-c-frontend-v1";
const EXPECTED_PROFILE: &str = "malbolge-2026";
const MAX_FRONTEND_JSON_BYTES: usize = 1_048_576;
const MAX_EFFECT_FREE_BODY_NODES: usize = 4_094;
const MAX_COMPOUND_DEPTH: usize = 64;
const MAX_LITERAL_OUTPUT_CALLS: usize = 33;
const MAX_OUTPUT_PARENTHESES: usize = 3;
const MAX_OUTPUT_ARGUMENT_WRAPPERS: usize = MAX_OUTPUT_PARENTHESES + 1;
// Bound extra same-line source bytes between AST-delimited C tokens.
const MAX_OUTPUT_INLINE_PADDING: u32 = 16;
const MAX_INERT_OUTPUT_STATEMENTS: usize = 128;
const MAX_NESTED_OUTPUT_SCOPES: usize = 128;

/// Which independently checked guest effect trace can realize this C source.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FrontendGuestMode {
    /// Exactly two VM-witnessed distinct nonzero printable bytes.
    DistinctLiteralPair,
    /// Exactly three independently VM-witnessed different bytes.
    DistinctLiteralTriple,
    /// Exactly four independently VM-witnessed printable bytes.
    DistinctLiteralQuad,
    /// Five distinct source-proven bytes, including one escape byte.
    DistinctLiteralQuint,
    /// Six VM-computed distinct binary bytes.
    DistinctLiteralSix,
    /// Seven independent guest-computed binary bytes.
    DistinctLiteralSeven,
    /// No byte effects, then a guest halt.
    EmptyVoid,
    /// Emit a literal zero byte, then a guest halt.
    InitialZeroOutput,
    /// Emit an independently witnessed nonzero byte using guest rotation.
    SeededByteLiteral,
    /// Exactly two different outputs: initial zero then a VM-witnessed byte.
    ZeroThenLiteral,
}

/// Canonical typed-IR bytes paired with their independently checked guest mode.
pub type CanonicalGuestProjection = (Vec<u8>, FrontendGuestMode);
type LiteralOutputProjection = (Vec<u8>, FrontendGuestMode);

/// A rejected normalized frontend artifact or typed-IR projection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FrontendJsonError {
    /// The canonical typed-IR compiler rejected this semantic projection.
    InvalidTypedIr,
    /// JSON is malformed, has duplicate/unknown keys or exceeds the bound.
    Malformed,
    /// Metadata or semantic nodes are outside the admitted void-return slice.
    Unsupported,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Clang {
    language: String,
    target: String,
    version: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Target {
    abi_id: String,
    target_profile: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Source {
    id: String,
    sha256: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Position {
    byte: u32,
    column: u32,
    line: u32,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Span {
    begin: Position,
    end: Position,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Node {
    constant_integer: Option<String>,
    definition: Option<String>,
    id: u32,
    inline_specified: Option<bool>,
    kind: String,
    linkage: Option<String>,
    literal: Option<String>,
    name: Option<String>,
    operation: Option<String>,
    parent: u32,
    reference: Option<String>,
    span: Span,
    storage_class: Option<String>,
    #[serde(rename = "type")]
    type_name: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Artifact {
    clang: Clang,
    #[serde(rename = "artifact_id")]
    identity: String,
    nodes: Vec<Node>,
    profile: Target,
    schema_version: u16,
    source: Source,
}

struct LiteralOutputNodes<'node> {
    body: &'node Node,
    byte: u8,
    calls: Vec<(&'node Node, &'node Node)>,
    function: &'node Node,
    mixed_byte: Option<u8>,
    third_byte: Option<u8>,
    fourth_byte: Option<u8>,
    fifth_byte: Option<u8>,
    sixth_byte: Option<u8>,
    seventh_byte: Option<u8>,
    returned: Option<&'node Node>,
}

// Track the Clang semantic preorder through nested lexical compound blocks.
// Each scope owns its source cursor, so closing a block cannot re-admit
// a child outside its original parent span or reorder an emitted effect.
struct OutputScope<'node> {
    node: &'node Node,
    previous_end: u32,
    previous_span_has_terminator: bool,
}

const fn position(value: &Position) -> FrontendPosition {
    FrontendPosition::new(value.byte, value.line, value.column)
}

const fn span(value: &Span) -> FrontendSpan {
    FrontendSpan::new(position(&value.begin), position(&value.end))
}

fn source_digest(value: &str) -> Result<[u8; 32], FrontendJsonError> {
    if value.len() != 64 {
        return Err(FrontendJsonError::Unsupported);
    }
    let mut digest = [0; 32];
    let (pairs, remainder) = value.as_bytes().as_chunks::<2>();
    if !remainder.is_empty() {
        return Err(FrontendJsonError::Unsupported);
    }
    for (target, pair) in digest.iter_mut().zip(pairs) {
        let word = str::from_utf8(pair).map_err(|_error| FrontendJsonError::Unsupported)?;
        if pair.iter().any(u8::is_ascii_uppercase) {
            return Err(FrontendJsonError::Unsupported);
        }
        *target = u8::from_str_radix(word, 16).map_err(|_error| FrontendJsonError::Unsupported)?;
    }
    Ok(digest)
}

// Clang NullStmt spans one semicolon, and standalone integer zero spans one
// digit. Discard only their proven no-effect semantics, not source provenance.
fn valid_single_byte_statement_span(node: &Node, body: &Node, preceding_end: u32) -> bool {
    let start = &node.span.begin;
    let end = &node.span.end;
    start.byte >= preceding_end
        && start.byte >= body.span.begin.byte
        && end.byte <= body.span.end.byte
        && start.byte.checked_add(1) == Some(end.byte)
        && start.line != 0
        && start.column != 0
        && start.line == end.line
        && start.column.checked_add(1) == Some(end.column)
}

// Admit only the exact Clang semantic preorder for the source `(void)0`:
// one to-void cast with an immediately nested i32 zero literal. The cast's
// source end coincides with its literal child's end, unlike compound scopes.
fn valid_zero_void_cast(cast: &Node, operand: Option<&Node>) -> bool {
    let Some(child) = operand else { return false };
    cast.kind == "cast-expression"
        && cast.type_name.as_deref() == Some("void")
        && cast.operation.as_deref() == Some("to-void")
        && child.kind == "integer-literal"
        && child.parent == cast.id
        && cast.id.checked_add(1) == Some(child.id)
        && child.type_name.as_deref() == Some("i32")
        && child.constant_integer.as_deref() == Some("0")
        && child.literal.as_deref() == Some("0")
        && cast.span.begin.byte.checked_add(7) == Some(cast.span.end.byte)
        && cast.span.begin.line == cast.span.end.line
        && cast.span.begin.column.checked_add(7) == Some(cast.span.end.column)
        && child.span.begin.byte.checked_add(1) == Some(child.span.end.byte)
        && child.span.begin.byte.checked_add(1) == Some(cast.span.end.byte)
        && child.span.begin.line == cast.span.end.line
        && child.span.end.line == cast.span.end.line
        && child.span.begin.column.checked_add(1) == Some(cast.span.end.column)
        && child.span.end.column == cast.span.end.column
}

// Clang's semantic preorder contains compound scopes and their children.
// Discard only proven effect-free nulls, literal zero, cast of zero to
// void and compound scopes, checking actual ancestor IDs and nonoverlapping source ranges at every depth. A
// terminal ReturnStmt may belong to any active compound scope, but no node
// can follow it. Scope bounds include braces; child ranges must be interior.
#[expect(
    clippy::too_many_lines,
    reason = "nested source-preorder and no-effect statements share one admission gate"
)]
fn admit_effect_free_body(body: &Node, statements: &[Node]) -> Result<(), FrontendJsonError> {
    let mut scopes = vec![(body, body.span.begin.byte)];
    let mut index = 0;
    while let Some(node) = statements.get(index) {
        while scopes
            .last()
            .is_some_and(|(parent, _)| parent.id != node.parent)
        {
            let _popped = scopes.pop();
        }
        let Some((parent, next_child_byte)) = scopes.last_mut() else {
            return Err(FrontendJsonError::Unsupported);
        };
        let start = &node.span.begin;
        let end = &node.span.end;
        if node.id != u32::try_from(index).unwrap_or(u32::MAX).saturating_add(3)
            || start.byte < *next_child_byte
            || start.byte <= parent.span.begin.byte
            || end.byte >= parent.span.end.byte
            || start.line == 0
            || start.column == 0
            || end.line < start.line
            || end.column == 0
            || (end.line == start.line && end.column <= start.column)
        {
            return Err(FrontendJsonError::Unsupported);
        }
        match node.kind.as_str() {
            "null-statement"
                if valid_single_byte_statement_span(node, parent, *next_child_byte) =>
            {
                *next_child_byte = end.byte;
            }
            // A literal zero directly inside a compound statement is a
            // one-byte expression statement with no reads, writes or effects.
            // It is not safe to discard arbitrary literal descendants or casts.
            "integer-literal"
                if node.type_name.as_deref() == Some("i32")
                    && node.constant_integer.as_deref() == Some("0")
                    && node.literal.as_deref() == Some("0")
                    && valid_single_byte_statement_span(node, parent, *next_child_byte) =>
            {
                *next_child_byte = end.byte;
            }
            "cast-expression"
                if valid_zero_void_cast(node, statements.get(index.saturating_add(1))) =>
            {
                *next_child_byte = end.byte;
                index = index.saturating_add(1); // consume the literal child
            }
            "compound-statement"
                if start
                    .byte
                    .checked_add(2)
                    .is_some_and(|min_end| end.byte >= min_end)
                    && (end.line != start.line
                        || start
                            .column
                            .checked_add(2)
                            .is_some_and(|min_end| end.column >= min_end)) =>
            {
                *next_child_byte = end.byte;
                if scopes.len() >= MAX_COMPOUND_DEPTH {
                    return Err(FrontendJsonError::Unsupported);
                }
                scopes.push((node, start.byte));
            }
            "return-statement" if index == statements.len().saturating_sub(1) => {
                *next_child_byte = end.byte;
            }
            _ => return Err(FrontendJsonError::Unsupported),
        }
        index = index.saturating_add(1);
    }
    Ok(())
}

/// Decode one no-effect void C function with optional nested scopes and returns.
///
/// This validates the serialized Clang artifact shape, **not** the contents
/// of an independently supplied C source. Raw-source digest verification and
/// native frontend execution belong to the future process composition.
///
/// # Errors
///
/// Rejects malformed/duplicate/unknown JSON fields, version/profile drift,
/// extra statements or definitions, and invalid typed-IR source spans.
#[expect(
    clippy::too_many_lines,
    reason = "closed versioned Clang node and typed IR admission"
)]
pub fn decode_void_frontend_json(bytes: &[u8]) -> Result<FrontendArtifact, FrontendJsonError> {
    if bytes.is_empty() || bytes.len() > MAX_FRONTEND_JSON_BYTES {
        return Err(FrontendJsonError::Malformed);
    }
    let input: Artifact =
        serde_json::from_slice(bytes).map_err(|_error| FrontendJsonError::Malformed)?;
    if input.schema_version != 1
        || input.identity != EXPECTED_ARTIFACT
        || input.profile.abi_id != EXPECTED_ABI
        || input.profile.target_profile != EXPECTED_PROFILE
        || input.clang.version != "22.1.8"
        || input.clang.target != "wasm32-unknown-unknown"
        || input.clang.language != "c23"
        || input.source.id.is_empty()
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let [function, body, statements @ ..] = input.nodes.as_slice() else {
        return Err(FrontendJsonError::Unsupported);
    };
    let returned = statements
        .last()
        .filter(|node| node.kind == "return-statement");
    if statements.len() > MAX_EFFECT_FREE_BODY_NODES {
        return Err(FrontendJsonError::Unsupported);
    }
    if function.kind != "function-declaration"
        || function.parent != 0
        || function.id != 1
        || function.name.as_deref().is_none_or(str::is_empty)
        || function.type_name.as_deref() != Some("fn()->void")
        || function.definition.as_deref() != Some("definition")
        || function.inline_specified != Some(false)
        || function.linkage.as_deref() != Some("external")
        || function.storage_class.as_deref() != Some("none")
        || function.constant_integer.is_some()
        || function.literal.is_some()
        || function.operation.is_some()
        || body.kind != "compound-statement"
        || body.parent != function.id
        || body.id != 2
        || once(body).chain(statements.iter()).any(|node| {
            let is_zero = node.kind == "integer-literal";
            let is_zero_cast = node.kind == "cast-expression";
            node.name.is_some()
                || node.reference.is_some()
                || (!is_zero && !is_zero_cast && node.type_name.is_some())
                || (!is_zero && node.constant_integer.is_some())
                || (!is_zero && node.literal.is_some())
                || (!is_zero_cast && node.operation.is_some())
                || node.definition.is_some()
                || node.inline_specified.is_some()
                || node.linkage.is_some()
                || node.storage_class.is_some()
        })
    {
        return Err(FrontendJsonError::Unsupported);
    }
    admit_effect_free_body(body, statements)?;
    let void_function = if let Some(return_node) = returned {
        FrontendReturnVoidFunction::new(FrontendReturnVoidFunctionSpec {
            body_span: span(&body.span),
            definition: String::from("definition"),
            function_span: span(&function.span),
            inline_specified: false,
            linkage: String::from("external"),
            name: function
                .name
                .clone()
                .ok_or(FrontendJsonError::Unsupported)?,
            return_span: span(&return_node.span),
            signature: String::from("fn()->void"),
            storage_class: String::from("none"),
        })
    } else {
        FrontendReturnVoidFunction::new_fallthrough(FrontendFallthroughVoidFunctionSpec {
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
        })
    };
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
    let _validated =
        lower_frontend_artifact(&artifact).map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    Ok(artifact)
}

/// Produce canonical typed MCTI from a supported normalized C JSON artifact.
///
/// # Errors
///
/// Refuses any unsupported Clang structure or independently invalid typed wire.
pub fn canonical_void_typed_ir(bytes: &[u8]) -> Result<Vec<u8>, FrontendJsonError> {
    let artifact = decode_void_frontend_json(bytes)?;
    let module =
        lower_frontend_artifact(&artifact).map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    let encoded = canonical_bytes(&module).map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    let decoded = canonical_module(&encoded).map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    if decoded != module {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    Ok(encoded)
}

const fn typed_span(value: &Span) -> typed::SourceSpan {
    let begin = &value.begin;
    let end = &value.end;
    typed::SourceSpan::new(
        typed::SourcePosition::new(begin.byte, begin.line, begin.column),
        typed::SourcePosition::new(end.byte, end.line, end.column),
    )
}

// Clang's normalized preorder has complete semantic ancestry but carries only
// offsets, not source text. Accept short gaps around source delimiters only
// when byte and column distances agree on one line. The pinned AST, source
// digest check, and closed node grammar still prove the guest byte effect.
fn bounded_inline_gap(before: &Position, after: &Position, required: u32) -> bool {
    before.line != 0
        && before.line == after.line
        && before.column != 0
        && before
            .byte
            .checked_add(required)
            .is_some_and(|start| start <= after.byte)
        && after.byte.checked_sub(before.byte).is_some_and(|gap| {
            gap <= required.saturating_add(MAX_OUTPUT_INLINE_PADDING)
                && after.column.checked_sub(before.column) == Some(gap)
        })
}

// Each putchar expression has the pinned Clang semantic preorder:
// optional explicit to-void discard -> call -> function decay -> declaration
// ref -> bounded argument wrappers -> literal. One signed unary may occur in
// a checked parenthesis chain; a separate unsigned integral cast may surround
// the leaf. No folded arithmetic, nested discards or side effects are inferred.
#[expect(
    clippy::too_many_lines,
    clippy::too_many_arguments,
    clippy::cognitive_complexity,
    reason = "exact Clang node metadata and positional proof stay together"
)]
fn admitted_output_byte(
    group: &[Node],
    body: &Node,
    previous_end: u32,
    expected_id: u32,
    previous_span_has_terminator: bool,
) -> Option<u8> {
    let discard = group.first().filter(|node| {
        node.kind == "cast-expression" && node.operation.as_deref() == Some("to-void")
    });
    let call_group = if discard.is_some() {
        group.get(1..)?
    } else {
        group
    };
    let [call, cast, callee, rest @ ..] = call_group else {
        return None;
    };
    let statement = discard.unwrap_or(call);
    let call_id = expected_id.checked_add(u32::from(discard.is_some()))?;
    let discard_valid = discard.is_none_or(|outer| {
        outer.id == expected_id
            && outer.parent == body.id
            && outer.type_name.as_deref() == Some("void")
            && outer.name.is_none()
            && outer.reference.is_none()
            && outer.definition.is_none()
            && outer.inline_specified.is_none()
            && outer.linkage.is_none()
            && outer.storage_class.is_none()
            && outer.constant_integer.is_none()
            && outer.literal.is_none()
            && bounded_inline_gap(&outer.span.begin, &call.span.begin, 6)
            && outer.span.end.byte == call.span.end.byte
            && outer.span.end.line == call.span.end.line
            && outer.span.end.column == call.span.end.column
    });
    let (literal, wrappers) = rest.split_last()?;
    if wrappers.len() > MAX_OUTPUT_ARGUMENT_WRAPPERS {
        return None;
    }
    let integral_cast = wrappers.first().is_some_and(|node| {
        node.kind == "cast-expression" && node.operation.as_deref() == Some("integral-cast")
    });
    let unary_index = wrappers
        .iter()
        .position(|node| node.kind == "unary-expression");
    if (integral_cast && unary_index.is_some())
        || wrappers
            .iter()
            .filter(|node| node.kind == "unary-expression")
            .count()
            > 1
    {
        return None;
    }
    let unary = unary_index.and_then(|index| wrappers.get(index));
    let digits = literal.literal.as_deref()?;
    // The source-bound leaf must be a nonnegative representable i32 value,
    // even when Clang inferred unsigned u32 for the source token.
    let operand = digits.parse::<i32>().ok()?;
    if operand.is_negative()
        || digits != operand.to_string()
        || literal.constant_integer.as_deref() != Some(digits)
        || literal.type_name.as_deref() != Some(if integral_cast { "u32" } else { "i32" })
        || (integral_cast && literal.kind != "integer-literal")
    {
        return None;
    }
    let evaluated = match unary {
        Some(node) => match node.operation.as_deref() {
            Some("+") => operand,
            Some("-") => operand.checked_neg()?,
            _ => return None,
        },
        None => operand,
    };
    let evaluated_digits = evaluated.to_string();
    let [byte, ..] = evaluated.to_le_bytes();
    let call_span = &call.span;
    let cast_span = &cast.span;
    let callee_span = &callee.span;
    let literal_span = &literal.span;
    let argument_span = wrappers.first().map_or(literal_span, |node| &node.span);
    let source_width = literal_span.end.byte.checked_sub(literal_span.begin.byte)?;
    // Clang already decodes decimal, octal, hexadecimal, C23 binary and
    // character tokens. Retain its evaluated integer and exact source span;
    // never guess the spelling from a normalized decimal string.
    let width = match literal.kind.as_str() {
        "integer-literal"
            if (1..=32).contains(&source_width)
                && literal_span.begin.line == literal_span.end.line
                && literal_span
                    .end
                    .column
                    .checked_sub(literal_span.begin.column)
                    == Some(source_width) =>
        {
            source_width
        }
        "character-literal"
            if (3..=10).contains(&source_width)
                && literal_span.begin.line == literal_span.end.line
                && literal_span
                    .end
                    .column
                    .checked_sub(literal_span.begin.column)
                    == Some(source_width) =>
        {
            source_width
        }
        _ => return None,
    };

    let mut parent_id = call.id;
    let mut next_id = call_id.checked_add(3)?;
    let mut parentheses = 0usize;
    for (index, node) in wrappers.iter().enumerate() {
        let child = wrappers.get(index.saturating_add(1)).unwrap_or(literal);
        let node_span = &node.span;
        let child_span = &child.span;
        if node.id != next_id
            || node.parent != parent_id
            || node.name.is_some()
            || node.reference.is_some()
            || node.definition.is_some()
            || node.inline_specified.is_some()
            || node.linkage.is_some()
            || node.storage_class.is_some()
            || node.literal.is_some()
            || node.constant_integer.as_deref()
                != Some(
                    if unary_index.is_some_and(|unary_position| index > unary_position) {
                        digits
                    } else {
                        evaluated_digits.as_str()
                    },
                )
        {
            return None;
        }
        let shape = match node.kind.as_str() {
            "parenthesized-expression" => {
                parentheses = parentheses.checked_add(1)?;
                parentheses <= MAX_OUTPUT_PARENTHESES
                    && node.type_name == child.type_name
                    && node.operation.is_none()
                    && bounded_inline_gap(&node_span.begin, &child_span.begin, 1)
                    && bounded_inline_gap(&child_span.end, &node_span.end, 1)
            }
            "cast-expression" => {
                index == 0
                    && integral_cast
                    && node.type_name.as_deref() == Some("i32")
                    && child.type_name.as_deref() == Some("u32")
                    && node.operation.as_deref() == Some("integral-cast")
                    && node_span.begin.byte == child_span.begin.byte
                    && node_span.end.byte == child_span.end.byte
                    && node_span.begin.line == child_span.begin.line
                    && node_span.end.line == child_span.end.line
                    && node_span.begin.column == child_span.begin.column
                    && node_span.end.column == child_span.end.column
            }
            "unary-expression" => {
                unary_index == Some(index)
                    && !integral_cast
                    && node.type_name.as_deref() == Some("i32")
                    && child.type_name.as_deref() == Some("i32")
                    && matches!(node.operation.as_deref(), Some("+" | "-"))
                    && bounded_inline_gap(&node_span.begin, &child_span.begin, 1)
                    && node_span.end.byte == child_span.end.byte
                    && node_span.end.line == child_span.end.line
                    && node_span.end.column == child_span.end.column
            }
            _ => false,
        };
        if !shape {
            return None;
        }
        parent_id = node.id;
        next_id = next_id.checked_add(1)?;
    }
    let valid = discard_valid
        && literal.id == next_id
        && literal.parent == parent_id
        && call.id == call_id
        && call.parent == discard.map_or(body.id, |outer| outer.id)
        && call.kind == "call-expression"
        && call.type_name.as_deref() == Some("i32")
        && call.reference.as_deref() == Some("external:putchar")
        && cast.id == call_id.checked_add(1)?
        && cast.parent == call.id
        && cast.kind == "cast-expression"
        && cast.type_name.as_deref() == Some("ptr(fn(i32)->i32)")
        && cast.operation.as_deref() == Some("function-to-pointer")
        && callee.id == call_id.checked_add(2)?
        && callee.parent == cast.id
        && callee.kind == "declaration-reference-expression"
        && callee.type_name.as_deref() == Some("fn(i32)->i32")
        && callee.reference.as_deref() == Some("external:putchar")
        && [call, cast, callee, literal].iter().all(|node| {
            node.name.is_none()
                && node.definition.is_none()
                && node.inline_specified.is_none()
                && node.linkage.is_none()
                && node.storage_class.is_none()
        })
        && [call, cast, callee]
            .iter()
            .all(|node| node.constant_integer.is_none() && node.literal.is_none())
        && [call, callee, literal]
            .iter()
            .all(|node| node.operation.is_none())
        && [cast, literal].iter().all(|node| node.reference.is_none())
        // NullStmt and CompoundStmt spans include their final delimiter.
        && (statement.span.begin.byte > previous_end
            || (previous_span_has_terminator && statement.span.begin.byte == previous_end))
        && call_span.end.byte < body.span.end.byte
        && call_span.begin.byte == cast_span.begin.byte
        && cast_span.begin.byte == callee_span.begin.byte
        && cast_span.end.byte == callee_span.end.byte
        && bounded_inline_gap(&cast_span.end, &argument_span.begin, 1)
        && bounded_inline_gap(&argument_span.end, &call_span.end, 1)
        && cast_span.begin.column == call_span.begin.column
        && cast_span.begin.line == call_span.begin.line
        && cast_span.begin.byte.checked_add(7) == Some(cast_span.end.byte)
        && literal_span.begin.byte.checked_add(width) == Some(literal_span.end.byte)
        && [
            call_span,
            cast_span,
            callee_span,
            argument_span,
            literal_span,
        ]
        .iter()
        .all(|span| {
            span.begin.line != 0
                && span.begin.column != 0
                && span.end.line != 0
                && span.end.column != 0
                && span.begin.byte < span.end.byte
                && (span.begin.line != span.end.line || span.begin.column < span.end.column)
        });
    valid.then_some(byte)
}

// Between output calls, discard only the same exact source-bound
// no-effect statements admitted by the void-return frontend. Never infer that
// an unrecognized expression lacks observable effects.
fn inert_output_statement(
    nodes: &[Node],
    body: &Node,
    previous_end: u32,
    expected_id: u32,
) -> Option<(usize, u32)> {
    let node = nodes.first()?;
    let closed_metadata = |node: &Node| {
        node.name.is_none()
            && node.reference.is_none()
            && node.definition.is_none()
            && node.inline_specified.is_none()
            && node.linkage.is_none()
            && node.storage_class.is_none()
    };
    if node.id != expected_id
        || node.parent != body.id
        || !closed_metadata(node)
        || node.span.begin.byte <= body.span.begin.byte
        || node.span.begin.byte < previous_end
        || node.span.end.byte >= body.span.end.byte
    {
        return None;
    }
    let end = node.span.end.byte;
    match node.kind.as_str() {
        "null-statement"
            if node.type_name.is_none()
                && node.operation.is_none()
                && node.constant_integer.is_none()
                && node.literal.is_none()
                && valid_single_byte_statement_span(node, body, previous_end) =>
        {
            Some((1, end))
        }
        "integer-literal"
            if node.type_name.as_deref() == Some("i32")
                && node.operation.is_none()
                && node.constant_integer.as_deref() == Some("0")
                && node.literal.as_deref() == Some("0")
                && valid_single_byte_statement_span(node, body, previous_end) =>
        {
            Some((1, end))
        }
        "cast-expression" => {
            let child = nodes.get(1)?;
            (node.constant_integer.is_none()
                && node.literal.is_none()
                && closed_metadata(child)
                && child.operation.is_none()
                && child.id == expected_id.checked_add(1)?
                && valid_zero_void_cast(node, Some(child)))
            .then_some((2, end))
        }
        _ => None,
    }
}

// Bounded literal outputs are identical, except an exact witnessed zero-first pair.
#[expect(
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "closed bounded C literal-output preorder admission"
)]
fn admit_literal_output_nodes(nodes: &[Node]) -> Result<LiteralOutputNodes<'_>, FrontendJsonError> {
    let [function, body, rest @ ..] = nodes else {
        return Err(FrontendJsonError::Unsupported);
    };
    let (returned, call_nodes) = match rest.split_last() {
        Some((last, preceding)) if last.kind == "return-statement" => (Some(last), preceding),
        _ => (None, rest),
    };
    if call_nodes.is_empty()
        || call_nodes.len()
            > MAX_LITERAL_OUTPUT_CALLS
                .saturating_mul(5 + MAX_OUTPUT_ARGUMENT_WRAPPERS)
                .saturating_add(MAX_INERT_OUTPUT_STATEMENTS.saturating_mul(2))
                .saturating_add(MAX_NESTED_OUTPUT_SCOPES)
        || function.kind != "function-declaration"
        || function.id != 1
        || function.parent != 0
        || function.name.as_deref().is_none_or(str::is_empty)
        || function.type_name.as_deref() != Some("fn()->void")
        || function.definition.as_deref() != Some("definition")
        || function.inline_specified != Some(false)
        || function.linkage.as_deref() != Some("external")
        || function.storage_class.as_deref() != Some("none")
        || function.constant_integer.is_some()
        || function.literal.is_some()
        || function.operation.is_some()
        || function.reference.is_some()
        || body.id != 2
        || body.parent != 1
        || body.kind != "compound-statement"
        || returned.is_some_and(|node| {
            node.id != u32::try_from(nodes.len()).unwrap_or(u32::MAX)
                || node.parent != body.id
                || node.span.begin.byte <= body.span.begin.byte
                || node.span.end.byte >= body.span.end.byte
        })
        || once(body).chain(returned).any(|node| {
            node.name.is_some()
                || node.definition.is_some()
                || node.inline_specified.is_some()
                || node.linkage.is_some()
                || node.storage_class.is_some()
                || node.type_name.is_some()
                || node.reference.is_some()
                || node.operation.is_some()
                || node.constant_integer.is_some()
                || node.literal.is_some()
        })
        || function.span.begin.byte > body.span.begin.byte
        || function.span.end.byte < body.span.end.byte
        || body.span.begin.byte >= body.span.end.byte
        || once(body).chain(returned).any(|node| {
            node.span.begin.line == 0
                || node.span.begin.column == 0
                || node.span.end.line == 0
                || node.span.end.column == 0
                || node.span.begin.byte >= node.span.end.byte
                || (node.span.begin.line == node.span.end.line
                    && node.span.begin.column >= node.span.end.column)
        })
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let mut calls = Vec::new();
    let mut selected_byte = None;
    let mut mixed_byte = None;
    let mut third_byte = None;
    let mut fourth_byte = None;
    let mut fifth_byte = None;
    let mut sixth_byte = None;
    let mut seventh_byte = None;
    let mut scopes = vec![OutputScope {
        node: body,
        previous_end: body.span.begin.byte,
        previous_span_has_terminator: false,
    }];
    let mut inert_count = 0usize;
    let mut nested_count = 0usize;
    let mut offset = 0usize;
    while offset < call_nodes.len() {
        let id = u32::try_from(offset)
            .ok()
            .and_then(|value| value.checked_add(3))
            .ok_or(FrontendJsonError::Unsupported)?;
        let remaining = call_nodes
            .get(offset..)
            .ok_or(FrontendJsonError::Unsupported)?;
        let node = remaining.first().ok_or(FrontendJsonError::Unsupported)?;
        // A child of an earlier block cannot re-enter that closed block.
        while scopes
            .last()
            .is_some_and(|scope| scope.node.id != node.parent)
        {
            let _closed = scopes.pop();
        }
        let scope_depth = scopes.len();
        let scope = scopes.last_mut().ok_or(FrontendJsonError::Unsupported)?;
        if node.kind == "compound-statement" {
            let start = &node.span.begin;
            let end = &node.span.end;
            if node.id != id
                || node.name.is_some()
                || node.reference.is_some()
                || node.definition.is_some()
                || node.inline_specified.is_some()
                || node.linkage.is_some()
                || node.storage_class.is_some()
                || node.type_name.is_some()
                || node.operation.is_some()
                || node.constant_integer.is_some()
                || node.literal.is_some()
                || start.byte < scope.previous_end
                || start.byte <= scope.node.span.begin.byte
                || end.byte >= scope.node.span.end.byte
                || start.byte.checked_add(2).is_none_or(|min| end.byte < min)
                || start.line == 0
                || start.column == 0
                || end.line < start.line
                || end.column == 0
                || start.line < scope.node.span.begin.line
                || end.line > scope.node.span.end.line
                || (start.line == end.line
                    && (end.column.checked_sub(start.column) != end.byte.checked_sub(start.byte)))
                || scope_depth >= MAX_COMPOUND_DEPTH
            {
                return Err(FrontendJsonError::Unsupported);
            }
            nested_count = nested_count.saturating_add(1);
            if nested_count > MAX_NESTED_OUTPUT_SCOPES {
                return Err(FrontendJsonError::Unsupported);
            }
            scope.previous_end = end.byte;
            scope.previous_span_has_terminator = true;
            scopes.push(OutputScope {
                node,
                previous_end: start.byte,
                previous_span_has_terminator: false,
            });
            offset = offset.saturating_add(1);
            continue;
        }
        if let Some((consumed, end)) =
            inert_output_statement(remaining, scope.node, scope.previous_end, id)
        {
            inert_count = inert_count.saturating_add(1);
            if inert_count > MAX_INERT_OUTPUT_STATEMENTS {
                return Err(FrontendJsonError::Unsupported);
            }
            scope.previous_end = end;
            scope.previous_span_has_terminator = node.kind == "null-statement";
            offset = offset.saturating_add(consumed);
            continue;
        }
        if calls.len() >= MAX_LITERAL_OUTPUT_CALLS {
            return Err(FrontendJsonError::Unsupported);
        }
        let discards_return_value =
            node.kind == "cast-expression" && node.operation.as_deref() == Some("to-void");
        let mut argument_end = offset
            .checked_add(3usize.saturating_add(usize::from(discards_return_value)))
            .ok_or(FrontendJsonError::Unsupported)?;
        for _ in 0..MAX_OUTPUT_ARGUMENT_WRAPPERS {
            let Some(argument_node) = call_nodes.get(argument_end) else {
                return Err(FrontendJsonError::Unsupported);
            };
            if !matches!(
                argument_node.kind.as_str(),
                "parenthesized-expression" | "cast-expression" | "unary-expression"
            ) {
                break;
            }
            argument_end = argument_end
                .checked_add(1)
                .ok_or(FrontendJsonError::Unsupported)?;
        }
        let end = argument_end
            .checked_add(1)
            .ok_or(FrontendJsonError::Unsupported)?;
        let group = call_nodes
            .get(offset..end)
            .ok_or(FrontendJsonError::Unsupported)?;
        let byte = admitted_output_byte(
            group,
            scope.node,
            scope.previous_end,
            id,
            scope.previous_span_has_terminator,
        )
        .ok_or(FrontendJsonError::Unsupported)?;
        if selected_byte.is_some_and(|previous| previous != byte) {
            if calls.len() == 1 && mixed_byte.is_none() {
                let is_zero_then_literal =
                    selected_byte == Some(0) && matches!(byte, b'Z' | b'P' | b'T' | b'S');
                let is_distinct_nonzero = matches!(
                    (selected_byte, byte),
                    (Some(b'Y'), b'/' | b'$') | (Some(b'Q'), b'.')
                );
                let is_triple_prefix = matches!(
                    (selected_byte, byte),
                    (Some(b'Z'), b'%')
                        | (Some(b'Q'), b'.' | b'"' | 28)
                        | (Some(b'Y'), b'-')
                        | (Some(b'T'), b'"' | b'=')
                        | (Some(b'6'), b'>')
                );
                if !(is_zero_then_literal || is_distinct_nonzero || is_triple_prefix) {
                    return Err(FrontendJsonError::Unsupported);
                }
                mixed_byte = Some(byte);
            } else if calls.len() == 2 && third_byte.is_none() {
                if !matches!(
                    (selected_byte, mixed_byte, byte),
                    (Some(b'Z'), Some(b'%'), b'H')
                        | (Some(b'Q'), Some(b'.' | 28), b'O')
                        | (Some(b'Q'), Some(b'"'), 27)
                        | (Some(b'Y'), Some(b'-'), b'P')
                        | (Some(b'T'), Some(b'"'), b'O' | b'Q')
                        | (Some(b'T'), Some(b'='), b'4')
                        | (Some(b'6'), Some(b'>'), b'5')
                ) {
                    return Err(FrontendJsonError::Unsupported);
                }
                third_byte = Some(byte);
            } else if calls.len() == 3 && fourth_byte.is_none() {
                if !matches!(
                    (selected_byte, mixed_byte, third_byte, byte),
                    (Some(b'T'), Some(b'='), Some(b'4'), b'>')
                        | (Some(b'Q'), Some(b'"'), Some(27), b'7')
                        | (Some(b'Q'), Some(28), Some(b'O'), 29)
                        | (Some(b'6'), Some(b'>'), Some(b'5'), 2)
                ) {
                    return Err(FrontendJsonError::Unsupported);
                }
                fourth_byte = Some(byte);
            } else if calls.len() == 4 && fifth_byte.is_none() {
                if !matches!(
                    (selected_byte, mixed_byte, third_byte, fourth_byte, byte),
                    (Some(b'Q'), Some(b'"'), Some(27), Some(b'7'), b'9')
                        | (Some(b'Q'), Some(28), Some(b'O'), Some(29), b'P')
                        | (Some(b'6'), Some(b'>'), Some(b'5'), Some(2), b'T')
                ) {
                    return Err(FrontendJsonError::Unsupported);
                }
                fifth_byte = Some(byte);
            } else if calls.len() == 5 && sixth_byte.is_none() {
                if (
                    selected_byte,
                    mixed_byte,
                    third_byte,
                    fourth_byte,
                    fifth_byte,
                    byte,
                ) != (Some(b'Q'), Some(28), Some(b'O'), Some(29), Some(b'P'), 27)
                    && (
                        selected_byte,
                        mixed_byte,
                        third_byte,
                        fourth_byte,
                        fifth_byte,
                        byte,
                    ) != (Some(b'6'), Some(b'>'), Some(b'5'), Some(2), Some(b'T'), 31)
                {
                    return Err(FrontendJsonError::Unsupported);
                }
                sixth_byte = Some(byte);
            } else if calls.len() == 6 && seventh_byte.is_none() {
                if (
                    selected_byte,
                    mixed_byte,
                    third_byte,
                    fourth_byte,
                    fifth_byte,
                    sixth_byte,
                    byte,
                ) != (
                    Some(b'6'),
                    Some(b'>'),
                    Some(b'5'),
                    Some(2),
                    Some(b'T'),
                    Some(31),
                    24,
                ) {
                    return Err(FrontendJsonError::Unsupported);
                }
                seventh_byte = Some(byte);
            } else {
                return Err(FrontendJsonError::Unsupported);
            }
        } else if mixed_byte.is_some() {
            return Err(FrontendJsonError::Unsupported);
        }
        if selected_byte.is_none() {
            selected_byte = Some(byte);
        }
        let call = group
            .get(usize::from(discards_return_value))
            .ok_or(FrontendJsonError::Unsupported)?;
        let literal = group.last().ok_or(FrontendJsonError::Unsupported)?;
        // Attribute signed constants to their complete source sign rather
        // than the positive leaf; parentheses retain checked source spans.
        let argument = group
            .iter()
            .find(|argument_node| argument_node.kind == "unary-expression")
            .unwrap_or(literal);
        scope.previous_end = node.span.end.byte;
        scope.previous_span_has_terminator = false;
        calls.push((call, argument));
        offset = end;
    }
    let root = scopes.first().ok_or(FrontendJsonError::Unsupported)?;
    let next_begin = returned.map_or(body.span.end.byte, |node| node.span.begin.byte);
    if root.previous_end > next_begin
        || (root.previous_end == next_begin
            && (returned.is_none() || !root.previous_span_has_terminator))
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // A three-byte prefix alone is not an admitted two-byte guest recipe.
    if third_byte.is_none()
        && matches!(
            (selected_byte, mixed_byte),
            (Some(b'Z'), Some(b'%'))
                | (Some(b'Y'), Some(b'-'))
                | (Some(b'T'), Some(b'"' | b'='))
                | (Some(b'Q'), Some(b'"' | 28))
                | (Some(b'6'), Some(b'>'))
        )
    {
        return Err(FrontendJsonError::Unsupported);
    }
    if fourth_byte.is_none()
        && matches!(
            (selected_byte, mixed_byte, third_byte),
            (Some(b'T'), Some(b'='), Some(b'4'))
                | (Some(b'Q'), Some(b'"'), Some(27))
                | (Some(b'Q'), Some(28), Some(b'O'))
                | (Some(b'6'), Some(b'>'), Some(b'5'))
        )
    {
        return Err(FrontendJsonError::Unsupported);
    }
    if fifth_byte.is_none()
        && matches!(
            (selected_byte, mixed_byte, third_byte, fourth_byte),
            (Some(b'Q'), Some(b'"'), Some(27), Some(b'7'))
                | (Some(b'Q'), Some(28), Some(b'O'), Some(29))
                | (Some(b'6'), Some(b'>'), Some(b'5'), Some(2))
        )
    {
        return Err(FrontendJsonError::Unsupported);
    }
    if sixth_byte.is_none()
        && (
            selected_byte,
            mixed_byte,
            third_byte,
            fourth_byte,
            fifth_byte,
        ) == (Some(b'Q'), Some(28), Some(b'O'), Some(29), Some(b'P'))
    {
        return Err(FrontendJsonError::Unsupported);
    }
    if sixth_byte.is_none()
        && (
            selected_byte,
            mixed_byte,
            third_byte,
            fourth_byte,
            fifth_byte,
        ) == (Some(b'6'), Some(b'>'), Some(b'5'), Some(2), Some(b'T'))
    {
        return Err(FrontendJsonError::Unsupported);
    }
    if seventh_byte.is_none()
        && (
            selected_byte,
            mixed_byte,
            third_byte,
            fourth_byte,
            fifth_byte,
            sixth_byte,
        ) == (
            Some(b'6'),
            Some(b'>'),
            Some(b'5'),
            Some(2),
            Some(b'T'),
            Some(31),
        )
    {
        return Err(FrontendJsonError::Unsupported);
    }
    Ok(LiteralOutputNodes {
        body,
        byte: selected_byte.ok_or(FrontendJsonError::Unsupported)?,
        calls,
        function,
        mixed_byte,
        third_byte,
        fourth_byte,
        fifth_byte,
        sixth_byte,
        seventh_byte,
        returned,
    })
}

/// Compile one through 33 identical source-proven byte `putchar(N)` calls
/// with bounded inert statements and an explicit or implicit void return.
#[expect(
    clippy::too_many_lines,
    reason = "canonical typed-effect projection and re-admission"
)]
fn canonical_literal_output_typed_ir(
    bytes: &[u8],
) -> Result<LiteralOutputProjection, FrontendJsonError> {
    if bytes.is_empty() || bytes.len() > MAX_FRONTEND_JSON_BYTES {
        return Err(FrontendJsonError::Malformed);
    }
    let input: Artifact =
        serde_json::from_slice(bytes).map_err(|_error| FrontendJsonError::Malformed)?;
    if input.schema_version != 1
        || input.identity != EXPECTED_ARTIFACT
        || input.profile.abi_id != EXPECTED_ABI
        || input.profile.target_profile != EXPECTED_PROFILE
        || input.clang.version != "22.1.8"
        || input.clang.target != "wasm32-unknown-unknown"
        || input.clang.language != "c23"
        || input.source.id.is_empty()
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let LiteralOutputNodes {
        function,
        body,
        byte,
        mixed_byte,
        third_byte,
        fourth_byte,
        fifth_byte,
        sixth_byte,
        seventh_byte,
        calls,
        returned,
    } = admit_literal_output_nodes(&input.nodes)?;
    let name = function
        .name
        .clone()
        .ok_or(FrontendJsonError::Unsupported)?;
    let void_function = if let Some(returned) = returned {
        FrontendReturnVoidFunction::new(FrontendReturnVoidFunctionSpec {
            body_span: span(&body.span),
            definition: String::from("definition"),
            function_span: span(&function.span),
            inline_specified: false,
            linkage: String::from("external"),
            name,
            return_span: span(&returned.span),
            signature: String::from("fn()->void"),
            storage_class: String::from("none"),
        })
    } else {
        FrontendReturnVoidFunction::new_fallthrough(FrontendFallthroughVoidFunctionSpec {
            body_span: span(&body.span),
            definition: String::from("definition"),
            function_span: span(&function.span),
            inline_specified: false,
            linkage: String::from("external"),
            name,
            signature: String::from("fn()->void"),
            storage_class: String::from("none"),
        })
    };
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
    let base =
        lower_frontend_artifact(&artifact).map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    let original = base
        .functions()
        .first()
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    let block = original
        .blocks()
        .first()
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    let first_argument = calls.first().ok_or(FrontendJsonError::Unsupported)?.1;
    let mut instructions = Vec::with_capacity(calls.len().saturating_mul(2).saturating_add(1));
    instructions.push(LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: IntegerConstant::new(8, vec![byte]),
            result: ValueId::new(0),
            type_id: TypeId::new(0),
        },
        typed_span(&first_argument.span),
    ));
    for (index, (call, argument)) in calls.into_iter().enumerate() {
        if index == 1
            && let Some(second) = mixed_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![second]),
                    result: ValueId::new(1),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 2
            && let Some(third) = third_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![third]),
                    result: ValueId::new(2),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 3
            && let Some(fourth) = fourth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![fourth]),
                    result: ValueId::new(3),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 4
            && let Some(fifth) = fifth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![fifth]),
                    result: ValueId::new(4),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 5
            && let Some(sixth) = sixth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![sixth]),
                    result: ValueId::new(5),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 6
            && let Some(seventh) = seventh_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![seventh]),
                    result: ValueId::new(6),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        instructions.push(LocatedInstruction::new(
            Instruction::ByteOutput {
                value: ValueId::new(if index == 6 && seventh_byte.is_some() {
                    6
                } else if index == 5 && sixth_byte.is_some() {
                    5
                } else if index == 4 && fifth_byte.is_some() {
                    4
                } else if index == 3 && fourth_byte.is_some() {
                    3
                } else if index == 2 && third_byte.is_some() {
                    2
                } else {
                    u32::from(index == 1 && mixed_byte.is_some())
                }),
            },
            typed_span(&call.span),
        ));
    }
    let compiled_function = Function::new(FunctionSpec {
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
        functions: vec![compiled_function],
        globals: base.globals().to_vec(),
        proof_obligations: base.proof_obligations().to_vec(),
        source_id: String::from(base.source_id()),
        source_sha256: *base.source_sha256(),
        target_profile: String::from(base.target_profile()),
        types: base.types().to_vec(),
    });
    let encoded = canonical_bytes(&module).map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    if canonical_module(&encoded).map_err(|_error| FrontendJsonError::InvalidTypedIr)? != module {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    let mode = if seventh_byte.is_some() {
        FrontendGuestMode::DistinctLiteralSeven
    } else if sixth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralSix
    } else if fifth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralQuint
    } else if fourth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralQuad
    } else if third_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTriple
    } else if mixed_byte.is_some() && byte == 0 {
        FrontendGuestMode::ZeroThenLiteral
    } else if mixed_byte.is_some() {
        FrontendGuestMode::DistinctLiteralPair
    } else if byte == 0 {
        FrontendGuestMode::InitialZeroOutput
    } else {
        FrontendGuestMode::SeededByteLiteral
    };
    Ok((encoded, mode))
}

/// Project the two supported C families without dropping observable output.
///
/// # Errors
///
/// Refuses unsupported Clang shapes, metadata drift and invalid typed IR.
pub fn canonical_guest_typed_ir(
    bytes: &[u8],
) -> Result<CanonicalGuestProjection, FrontendJsonError> {
    if let Ok(wire) = canonical_void_typed_ir(bytes) {
        return Ok((wire, FrontendGuestMode::EmptyVoid));
    }
    canonical_literal_output_typed_ir(bytes)
}
