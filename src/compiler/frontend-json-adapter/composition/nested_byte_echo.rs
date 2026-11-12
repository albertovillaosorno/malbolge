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
//   - Exact nested source-C putchar return-value forwarding to guest I/O.
// - Must-Not:
//   - Assume EOF, failed putchar success, or guest-side C storage.
// - Allows:
//   - Inputs: source-checked pinned Clang nested call expression ancestry.
//   - Outputs: successful-byte guest input and repeated real guest output.
//   - Side effects: none.
// - Split-When:
//   - General call/return guest dataflow owns these semantics.
// - Merge-When:
//   - Source byte echo also verifies nested call-return identities.
// - Summary:
//   - Preserve inner-to-outer putchar evaluation and return semantics.

//! Admit complete C call chains only when every byte read/write succeeds.

use super::typed::{
    BasicBlock, BasicBlockSpec, FrontendArtifact, FrontendArtifactSpec,
    FrontendFallthroughVoidFunctionSpec, FrontendReturnVoidFunction, Function,
    FunctionSpec, Instruction, LocatedInstruction, Module, ModuleSpec, TypeId,
    ValueId,
};
use super::{
    Artifact, CanonicalGuestProjection, FrontendGuestMode, FrontendJsonError,
    Node, canonical_bytes, canonical_module, lower_frontend_artifact,
    source_digest, span, typed_span,
};

const MAX_READS: usize = 128;
const MAX_OUTPUTS: usize = 256;
const MAX_DEPTH: usize = 16;

fn clean(node: &Node) -> bool {
    node.name.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
        && node.constant_integer.is_none()
        && node.literal.is_none()
}

#[expect(
    clippy::too_many_arguments,
    reason = "all four source coordinates are essential for Clang source proof"
)]
fn source_word(node: &Node, start: u32, end: u32, line: u32, col: u32) -> bool {
    node.span.begin.byte == start
        && node.span.end.byte == end
        && node.span.begin.line == line
        && node.span.end.line == line
        && node.span.begin.column == col
        && node.span.end.column
            == col.checked_add(end.saturating_sub(start)).unwrap_or(0)
}

fn envelope(artifact: &Artifact, function: &Node, body: &Node) -> bool {
    artifact.schema_version == 1
        && artifact.identity == super::EXPECTED_ARTIFACT
        && artifact.profile.abi_id == super::EXPECTED_ABI
        && artifact.profile.target_profile == super::EXPECTED_PROFILE
        && artifact.clang.version == "22.1.8"
        && artifact.clang.target == "wasm32-unknown-unknown"
        && artifact.clang.language == "c23"
        && !artifact.source.id.is_empty()
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
        && body.parent == function.id
        && body.kind == "compound-statement"
        && body.type_name.is_none()
        && body.operation.is_none()
        && body.reference.is_none()
        && clean(body)
        && function.span.begin.byte < body.span.begin.byte
        && function.span.end == body.span.end
        && body.span.begin.line > 0
        && body.span.begin.column > 0
        && body.span.begin.byte < body.span.end.byte
}

// One C expression: putchar(putchar(...putchar(getchar())...)).
// The nested output calls return the successful byte in reverse preorder.
// The canonical guest needs exactly one input instruction, then `depth`
// output instructions operating on the same accumulator value.
pub(super) fn nested_call<'a>(
    rest: &'a [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
) -> Option<(usize, &'a Node, Vec<&'a Node>)> {
    let outer = rest.first()?;
    let start = outer.span.begin.byte;
    let line = outer.span.begin.line;
    let col = outer.span.begin.column;
    if outer.id != expected_id
        || outer.parent != body.id
        || start <= previous
        || start <= body.span.begin.byte
        || line <= body.span.begin.line
        || col == 0
    {
        return None;
    }
    let mut depth = 0usize;
    let mut calls = Vec::new();
    let mut expected_parent = body.id;
    while depth < MAX_DEPTH {
        let offset = depth.checked_mul(3)?;
        let [call, cast, reference] =
            rest.get(offset..offset.checked_add(3)?)?
        else {
            return None;
        };
        if call.kind != "call-expression"
            || call.parent != expected_parent
            || call.type_name.as_deref() != Some("i32")
            || call.reference.as_deref() != Some("external:putchar")
            || call.operation.is_some()
            || !clean(call)
            || cast.id != call.id.checked_add(1)?
            || cast.parent != call.id
            || cast.kind != "cast-expression"
            || cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
            || cast.operation.as_deref() != Some("function-to-pointer")
            || cast.reference.is_some()
            || !clean(cast)
            || reference.id != cast.id.checked_add(1)?
            || reference.parent != cast.id
            || reference.kind != "declaration-reference-expression"
            || reference.type_name.as_deref() != Some("fn(i32)->i32")
            || reference.reference.as_deref() != Some("external:putchar")
            || reference.operation.is_some()
            || !clean(reference)
        {
            return None;
        }
        calls.push(call);
        depth = depth.checked_add(1)?;
        expected_parent = call.id;
        if rest.get(depth.checked_mul(3)?)?.reference.as_deref()
            == Some("external:getchar")
        {
            break;
        }
    }
    if depth == 0 || depth > MAX_DEPTH {
        return None;
    }
    let input_offset = depth.checked_mul(3)?;
    let [input, cast, reference] =
        rest.get(input_offset..input_offset.checked_add(3)?)?
    else {
        return None;
    };
    let depth_u32 = u32::try_from(depth).ok()?;
    let input_start = start.checked_add(depth_u32.checked_mul(8)?)?;
    let input_end = input_start.checked_add(9)?;
    let total_end = input_end.checked_add(depth_u32)?;
    if total_end >= body.span.end.byte {
        return None;
    }
    for (index, call) in calls.iter().enumerate() {
        let index_u32 = u32::try_from(index).ok()?;
        let call_start = start.checked_add(index_u32.checked_mul(8)?)?;
        let call_end = total_end.checked_sub(index_u32)?;
        let call_col = col.checked_add(index_u32.checked_mul(8)?)?;
        let offset = index.checked_mul(3)?;
        let cast = rest.get(offset.checked_add(1)?)?;
        let reference = rest.get(offset.checked_add(2)?)?;
        if !source_word(call, call_start, call_end, line, call_col)
            || !source_word(
                cast,
                call_start,
                call_start.checked_add(7)?,
                line,
                call_col,
            )
            || !source_word(
                reference,
                call_start,
                call_start.checked_add(7)?,
                line,
                call_col,
            )
        {
            return None;
        }
    }
    let input_col = col.checked_add(depth_u32.checked_mul(8)?)?;
    if input.id != expected_id.checked_add(u32::try_from(input_offset).ok()?)?
        || input.parent != expected_parent
        || input.kind != "call-expression"
        || input.type_name.as_deref() != Some("i32")
        || input.reference.as_deref() != Some("external:getchar")
        || input.operation.is_some()
        || !clean(input)
        || !source_word(input, input_start, input_end, line, input_col)
        || cast.id != input.id.checked_add(1)?
        || cast.parent != input.id
        || cast.kind != "cast-expression"
        || cast.type_name.as_deref() != Some("ptr(fn()->i32)")
        || cast.operation.as_deref() != Some("function-to-pointer")
        || cast.reference.is_some()
        || !clean(cast)
        || !source_word(
            cast,
            input_start,
            input_start.checked_add(7)?,
            line,
            input_col,
        )
        || reference.id != cast.id.checked_add(1)?
        || reference.parent != cast.id
        || reference.kind != "declaration-reference-expression"
        || reference.type_name.as_deref() != Some("fn()->i32")
        || reference.reference.as_deref() != Some("external:getchar")
        || reference.operation.is_some()
        || !clean(reference)
        || !source_word(
            reference,
            input_start,
            input_start.checked_add(7)?,
            line,
            input_col,
        )
    {
        return None;
    }
    Some((input_offset.checked_add(3)?, input, calls))
}

/// Prove complete nested successful-byte expression calls to canonical MCTI.
///
/// # Errors
/// Refuses any other C effect, stale Clang location, invalid source ancestry,
/// profile drift or typed IR which cannot be independently re-admitted.
#[expect(
    clippy::too_many_lines,
    reason = "one source-proof gate creates the exact nested byte effect trace"
)]
pub(super) fn canonical_nested_byte_echo(
    bytes: &[u8],
) -> Result<CanonicalGuestProjection, FrontendJsonError> {
    if bytes.is_empty() || bytes.len() > super::MAX_FRONTEND_JSON_BYTES {
        return Err(FrontendJsonError::Malformed);
    }
    let artifact: Artifact = serde_json::from_slice(bytes)
        .map_err(|_| FrontendJsonError::Malformed)?;
    let [function, body, rest @ ..] = artifact.nodes.as_slice() else {
        return Err(FrontendJsonError::Unsupported);
    };
    if !envelope(&artifact, function, body) || rest.is_empty() {
        return Err(FrontendJsonError::Unsupported);
    }
    let mut previous = body.span.begin.byte;
    let mut next_id = 3u32;
    let mut consumed = 0usize;
    let mut read_count = 0usize;
    let mut output_count = 0usize;
    let mut nested = false;
    let mut instructions = Vec::new();
    while consumed < rest.len() {
        if read_count >= MAX_READS || output_count >= MAX_OUTPUTS {
            return Err(FrontendJsonError::Unsupported);
        }
        let (width, input, calls) = nested_call(
            rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?,
            body,
            previous,
            next_id,
        )
        .ok_or(FrontendJsonError::Unsupported)?;
        if output_count
            .checked_add(calls.len())
            .is_none_or(|count| count > MAX_OUTPUTS)
        {
            return Err(FrontendJsonError::Unsupported);
        }
        nested |= calls.len() > 1;
        let id = ValueId::new(
            u32::try_from(read_count)
                .map_err(|_| FrontendJsonError::Unsupported)?,
        );
        instructions.push(LocatedInstruction::new(
            Instruction::ByteInput {
                result: id,
                type_id: TypeId::new(0),
            },
            typed_span(&input.span),
        ));
        for call in calls.iter().rev() {
            instructions.push(LocatedInstruction::new(
                Instruction::ByteOutput { value: id },
                typed_span(&call.span),
            ));
        }
        previous = calls
            .first()
            .ok_or(FrontendJsonError::Unsupported)?
            .span
            .end
            .byte;
        next_id = next_id
            .checked_add(
                u32::try_from(width)
                    .map_err(|_| FrontendJsonError::Unsupported)?,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
        consumed = consumed
            .checked_add(width)
            .ok_or(FrontendJsonError::Unsupported)?;
        output_count += calls.len();
        read_count += 1;
    }
    if !nested || previous >= body.span.end.byte {
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
    let frontend = FrontendArtifact::new_void(
        FrontendArtifactSpec {
            abi_id: artifact.profile.abi_id,
            artifact_id: artifact.identity,
            clang_target: artifact.clang.target,
            clang_version: artifact.clang.version,
            functions: Vec::new(),
            language: artifact.clang.language,
            schema_version: artifact.schema_version,
            source_id: artifact.source.id,
            source_sha256: source_digest(&artifact.source.sha256)?,
            target_profile: artifact.profile.target_profile,
        },
        void_function,
    );
    let base = lower_frontend_artifact(&frontend)
        .map_err(|_| FrontendJsonError::InvalidTypedIr)?;
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
        .map_err(|_| FrontendJsonError::InvalidTypedIr)?;
    if canonical_module(&wire).map_err(|_| FrontendJsonError::InvalidTypedIr)?
        != module
    {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    Ok((wire, FrontendGuestMode::LatestRead))
}
