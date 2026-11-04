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
//   - Closed normalized Clang-JSON to typed frontend no-effect void adapter.
// - Must-Not:
//   - Parse C, reinterpret Clang semantics, or bypass typed-IR admission.
// - Allows:
//   - Inputs: bounded version-one normalized frontend JSON bytes.
//   - Outputs: canonical MCTI for one admitted no-effect void function.
//   - Side effects: none.
// - Split-When:
//   - Another normalized function family gains an executable typed lowering.
// - Merge-When:
//   - Native frontend composition owns equivalent validated JSON decoding.
// - Summary:
//   - Connects exact frontend semantics to the tested typed-IR void slice.
// - Description:
//   - Unknown nodes, fields, extra effects, identities and profile drift fail.
// - Usage:
//   - `canonical_void_typed_ir(frontend_json)` yields independently decoded MCTI.
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
    FrontendArtifact, FrontendArtifactSpec, FrontendFallthroughVoidFunctionSpec, FrontendPosition,
    FrontendReturnVoidFunction, FrontendReturnVoidFunctionSpec, FrontendSpan, canonical_bytes,
    canonical_module, lower_frontend_artifact,
};

const EXPECTED_ABI: &str = "malbolge-c32-v1";
const EXPECTED_ARTIFACT: &str = "malbolge-c-frontend-v1";
const EXPECTED_PROFILE: &str = "malbolge-2026";
const MAX_FRONTEND_JSON_BYTES: usize = 1_048_576;
const MAX_EFFECT_FREE_BODY_NODES: usize = 4_094;
const MAX_COMPOUND_DEPTH: usize = 64;

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
    parent: u32,
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

// Clang's semantic preorder contains compound scopes and their children.
// Discard only proven effect-free nulls, literal zero and compound scopes,
// checking actual ancestor IDs and nonoverlapping source ranges at every depth. A
// terminal ReturnStmt may belong to any active compound scope, but no node
// can follow it. Scope bounds include braces; child ranges must be interior.
#[expect(
    clippy::too_many_lines,
    reason = "nested source-preorder and no-effect statements share one admission gate"
)]
fn admit_effect_free_body(body: &Node, statements: &[Node]) -> Result<(), FrontendJsonError> {
    let mut scopes = vec![(body, body.span.begin.byte)];
    for (index, node) in statements.iter().enumerate() {
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
        || body.kind != "compound-statement"
        || body.parent != function.id
        || body.id != 2
        || once(body).chain(statements.iter()).any(|node| {
            let is_standalone_zero = node.kind == "integer-literal";
            node.name.is_some()
                || (!is_standalone_zero && node.type_name.is_some())
                || (!is_standalone_zero && node.constant_integer.is_some())
                || (!is_standalone_zero && node.literal.is_some())
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
