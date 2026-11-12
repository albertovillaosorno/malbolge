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
type LocalForward<'node> = (&'node Node, &'node Node, &'node str);

/// The exact source-local input initializer, with no intervening effects.
struct LocalDeclaration<'node> {
    declaration_end: u32,
    input: &'node Node,
    input_callee_id: u32,
    line: u32,
    name: &'node str,
    variable_reference: String,
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
        && output.parent == body.id
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
        input_callee_id: input_callee.id,
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
        && output.id == local.input_callee_id.checked_add(1)?
        && output.parent == body.id
        && output.kind == "call-expression"
        && output.type_name.as_deref() == Some("i32")
        && output.reference.as_deref() == Some("external:putchar")
        && output.operation.is_none()
        && metadata_empty(output)
        && output_start > local.declaration_end
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

/// A local input assignment followed by a source-proven read of that local.
///
/// The layout backend still receives adjacent input/output SSA effects. It
/// cannot observe the C automatic local, so this grammar admits no intervening
/// read, write, cast or change to the captured successful input byte.
fn prove_local_call<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
) -> Option<LocalForward<'node>> {
    if nodes.len() != 10 {
        return None;
    }
    let local = prove_local_declaration(nodes.get(..5)?, body, previous)?;
    let output = prove_local_output(nodes.get(5..10)?, body, &local)?;
    Some((local.input, output, local.name))
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

/// Admit one through 128 direct or local-forwarded input/output pairs.
///
/// No EOF-dependent C control or other guest effects are admitted; the
/// resulting typed program describes a *successful-byte* input trace.
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
    let mut count = 0usize;
    let mut local_names = HashSet::new();
    let mut instructions = Vec::new();
    while consumed < rest.len() {
        let first = rest.get(consumed).ok_or(FrontendJsonError::Unsupported)?;
        if count == MAX_ECHO_CALLS || first.id != next_id {
            return Err(FrontendJsonError::Unsupported);
        }
        let (width, input_call, output_call) = if first.kind
            == "declaration-statement"
        {
            let nodes = rest
                .get(consumed..consumed.saturating_add(10))
                .ok_or(FrontendJsonError::Unsupported)?;
            let (read, write, name) = prove_local_call(nodes, body, previous)
                .ok_or(FrontendJsonError::Unsupported)?;
            if !local_names.insert(name) {
                return Err(FrontendJsonError::Unsupported);
            }
            (10, read, write)
        } else {
            let nodes = rest
                .get(consumed..consumed.saturating_add(CALL_NODE_COUNT))
                .ok_or(FrontendJsonError::Unsupported)?;
            let (read, write) = prove_call(nodes, body, previous)
                .ok_or(FrontendJsonError::Unsupported)?;
            (CALL_NODE_COUNT, read, write)
        };
        let id = ValueId::new(
            u32::try_from(count)
                .map_err(|_error| FrontendJsonError::Unsupported)?,
        );
        instructions.push(LocatedInstruction::new(
            Instruction::ByteInput {
                result: id,
                type_id: TypeId::new(0),
            },
            typed_span(&input_call.span),
        ));
        instructions.push(LocatedInstruction::new(
            Instruction::ByteOutput { value: id },
            typed_span(&output_call.span),
        ));
        previous = output_call.span.end.byte;
        consumed = consumed.saturating_add(width);
        next_id = next_id
            .checked_add(
                u32::try_from(width)
                    .map_err(|_error| FrontendJsonError::Unsupported)?,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
        count = count.saturating_add(1);
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
    Ok((wire, FrontendGuestMode::AdjacentEcho))
}
