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
//   - Closed normalized Clang-JSON to typed void/one-zero-output adapter.
// - Must-Not:
//   - Parse C, reinterpret calls, silently drop effects, or bypass typed
//     admission.
// - Allows:
//   - Inputs: bounded version-one normalized frontend JSON bytes.
//   - Outputs: canonical MCTI for no-effect void or exact putchar(0) source.
//   - Side effects: none.
// - Split-When:
//   - General C byte-I/O gains independently modeled effect semantics.
// - Merge-When:
//   - Native frontend composition owns equivalent validated JSON decoding.
// - Summary:
//   - Connects exact C semantics to tested typed void and zero-output slices.
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
const MAX_ZERO_OUTPUT_CALLS: usize = 32;

/// Which independently checked guest effect trace can realize this C source.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FrontendGuestMode {
    /// No byte effects, then a guest halt.
    EmptyVoid,
    /// Emit a literal zero byte, then a guest halt.
    InitialZeroOutput,
}

/// Canonical typed-IR bytes paired with their independently checked guest mode.
pub type CanonicalGuestProjection = (Vec<u8>, FrontendGuestMode);

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

struct ZeroOutputNodes<'node> {
    body: &'node Node,
    calls: Vec<(&'node Node, &'node Node)>,
    function: &'node Node,
    returned: &'node Node,
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

// Each direct `putchar(0)` child must have the exact source-bound Clang
// four-node preorder: call -> function decay -> declaration ref, and call
// -> literal. Calls are ordered siblings, never reordered or discarded.
#[expect(
    clippy::too_many_lines,
    reason = "exact Clang node metadata and positional proof stay together"
)]
fn valid_zero_output_call(
    group: &[Node],
    body: &Node,
    previous_end: u32,
    expected_id: u32,
) -> bool {
    let [call, cast, callee, zero] = group else {
        return false;
    };
    let call_span = &call.span;
    let cast_span = &cast.span;
    let callee_span = &callee.span;
    let literal_span = &zero.span;
    call.id == expected_id
        && call.parent == body.id
        && call.kind == "call-expression"
        && call.type_name.as_deref() == Some("i32")
        && call.reference.as_deref() == Some("external:putchar")
        && cast.id == expected_id.saturating_add(1)
        && cast.parent == call.id
        && cast.kind == "cast-expression"
        && cast.type_name.as_deref() == Some("ptr(fn(i32)->i32)")
        && cast.operation.as_deref() == Some("function-to-pointer")
        && callee.id == expected_id.saturating_add(2)
        && callee.parent == cast.id
        && callee.kind == "declaration-reference-expression"
        && callee.type_name.as_deref() == Some("fn(i32)->i32")
        && callee.reference.as_deref() == Some("external:putchar")
        && zero.id == expected_id.saturating_add(3)
        && zero.parent == call.id
        && zero.kind == "integer-literal"
        && zero.type_name.as_deref() == Some("i32")
        && zero.constant_integer.as_deref() == Some("0")
        && zero.literal.as_deref() == Some("0")
        && [call, cast, callee, zero].iter().all(|node| {
            node.name.is_none()
                && node.definition.is_none()
                && node.inline_specified.is_none()
                && node.linkage.is_none()
                && node.storage_class.is_none()
        })
        && [call, cast, callee]
            .iter()
            .all(|node| node.constant_integer.is_none() && node.literal.is_none())
        && [call, callee, zero]
            .iter()
            .all(|node| node.operation.is_none())
        && [cast, zero].iter().all(|node| node.reference.is_none())
        && call_span.begin.byte > previous_end
        && call_span.end.byte < body.span.end.byte
        && call_span.begin.byte == cast_span.begin.byte
        && cast_span.begin.byte == callee_span.begin.byte
        && cast_span.end.byte == callee_span.end.byte
        && cast_span.end.byte.checked_add(1) == Some(literal_span.begin.byte)
        && literal_span.end.byte < call_span.end.byte
        && cast_span.begin.byte.checked_add(7) == Some(cast_span.end.byte)
        && literal_span.begin.byte.checked_add(1) == Some(literal_span.end.byte)
        && call_span.begin.byte.checked_add(10) == Some(call_span.end.byte)
        && [call_span, cast_span, callee_span, literal_span]
            .iter()
            .all(|span| {
                span.begin.line != 0
                    && span.begin.column != 0
                    && span.end.line != 0
                    && span.end.column != 0
                    && span.begin.byte < span.end.byte
                    && (span.begin.line != span.end.line || span.begin.column < span.end.column)
            })
}

// A bounded sequence of direct calls keeps the same exact metadata and
// span proof as one call, with no gap in preorder IDs or intervening effects.
#[expect(
    clippy::too_many_lines,
    reason = "closed bounded C zero-output preorder admission"
)]
fn admit_zero_output_nodes(nodes: &[Node]) -> Result<ZeroOutputNodes<'_>, FrontendJsonError> {
    let [function, body, rest @ ..] = nodes else {
        return Err(FrontendJsonError::Unsupported);
    };
    let Some((returned, call_nodes)) = rest.split_last() else {
        return Err(FrontendJsonError::Unsupported);
    };
    let (groups, leftover) = call_nodes.as_chunks::<4>();
    if groups.is_empty()
        || !leftover.is_empty()
        || groups.len() > MAX_ZERO_OUTPUT_CALLS
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
        || returned.id != u32::try_from(nodes.len()).unwrap_or(u32::MAX)
        || returned.parent != body.id
        || returned.kind != "return-statement"
        || [body, returned].iter().any(|node| {
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
        || body.span.begin.byte >= returned.span.begin.byte
        || returned.span.end.byte >= body.span.end.byte
        || [body, returned].iter().any(|node| {
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
    let mut calls = Vec::with_capacity(groups.len());
    let mut previous_end = body.span.begin.byte;
    for (index, group) in groups.iter().enumerate() {
        let id = u32::try_from(index)
            .ok()
            .and_then(|value| value.checked_mul(4))
            .and_then(|value| value.checked_add(3))
            .ok_or(FrontendJsonError::Unsupported)?;
        if !valid_zero_output_call(group, body, previous_end, id) {
            return Err(FrontendJsonError::Unsupported);
        }
        let [call, _, _, zero] = group;
        previous_end = call.span.end.byte;
        calls.push((call, zero));
    }
    if previous_end >= returned.span.begin.byte {
        return Err(FrontendJsonError::Unsupported);
    }
    Ok(ZeroOutputNodes {
        body,
        calls,
        function,
        returned,
    })
}

/// Compile one through 32 source-proven `putchar(0)` calls and final return
/// into a successful-output trace, retaining exact source provenance.
#[expect(
    clippy::too_many_lines,
    reason = "canonical typed-effect projection and re-admission"
)]
fn canonical_zero_output_typed_ir(bytes: &[u8]) -> Result<Vec<u8>, FrontendJsonError> {
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
    let ZeroOutputNodes {
        function,
        body,
        calls,
        returned,
    } = admit_zero_output_nodes(&input.nodes)?;
    let void_function = FrontendReturnVoidFunction::new(FrontendReturnVoidFunctionSpec {
        body_span: span(&body.span),
        definition: String::from("definition"),
        function_span: span(&function.span),
        inline_specified: false,
        linkage: String::from("external"),
        name: function
            .name
            .clone()
            .ok_or(FrontendJsonError::Unsupported)?,
        return_span: span(&returned.span),
        signature: String::from("fn()->void"),
        storage_class: String::from("none"),
    });
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
    let first_literal = calls.first().ok_or(FrontendJsonError::Unsupported)?.1;
    let mut instructions = Vec::with_capacity(calls.len().saturating_add(1));
    instructions.push(LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: IntegerConstant::new(8, vec![0]),
            result: ValueId::new(0),
            type_id: TypeId::new(0),
        },
        typed_span(&first_literal.span),
    ));
    for (call, _literal) in calls {
        instructions.push(LocatedInstruction::new(
            Instruction::ByteOutput {
                value: ValueId::new(0),
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
    Ok(encoded)
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
    canonical_zero_output_typed_ir(bytes).map(|wire| (wire, FrontendGuestMode::InitialZeroOutput))
}
