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
//   - Clang- and source-bound one discarded signed input then literal output.
// - Must-Not:
//   - Substitute byte-only EOF, skip an input, or interpret unproved source.
// - Allows:
//   - Inputs: pinned C23 AST, SHA-256 matched C source and exact nine nodes.
//   - Outputs: canonical MCTI Getchar(i32), constant(u8), output, void return.
//   - Side effects: none.
// - Split-When:
//   - General mixed effect SSA lowering replaces this closed source grammar.
// - Merge-When:
//   - General mutable EOF checksum compiles with authentic runtime semantics.
// - Summary:
//   - Source-checked input side effect precedes independent byte publication.

//! Closed mixed-effect C source proof; no host input or output interpretation.

use super::typed::{
    BasicBlock, BasicBlockSpec, CastOp, FrontendArtifact, FrontendArtifactSpec,
    FrontendFallthroughVoidFunctionSpec, FrontendReturnVoidFunction, Function,
    FunctionSpec, Instruction, IntegerConstant, LocatedInstruction, Module,
    ModuleSpec, TypeDef, TypeEntry, TypeId, ValueId,
};
use super::{
    Artifact, CanonicalGuestProjection, FrontendGuestMode, FrontendJsonError,
    Node, canonical_bytes, canonical_module, lower_frontend_artifact,
    source_digest, typed_span,
};

// Authenticate every normalized subtree and source slice. A matching token
// and AST parent alone do not authorize any unrecognized sibling effect.
pub(super) fn node_is(
    node: &Node,
    id: u32,
    parent: u32,
    kind: &str,
    type_name: Option<&str>,
    reference: Option<&str>,
    operation: Option<&str>,
) -> bool {
    node.id == id
        && node.parent == parent
        && node.kind == kind
        && node.type_name.as_deref() == type_name
        && node.reference.as_deref() == reference
        && node.operation.as_deref() == operation
        && node.span.begin.byte < node.span.end.byte
        && node.span.begin.line > 0
        && node.span.begin.column > 0
        && node.span.begin.line == node.span.end.line
        && node.span.end.column.checked_sub(node.span.begin.column)
            == node.span.end.byte.checked_sub(node.span.begin.byte)
        && node.name.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
        && (kind == "integer-literal"
            || (node.constant_integer.is_none() && node.literal.is_none()))
}

pub(super) fn source_slice<'a>(
    source: &'a [u8],
    node: &Node,
) -> Option<&'a [u8]> {
    let start = usize::try_from(node.span.begin.byte).ok()?;
    let end = usize::try_from(node.span.end.byte).ok()?;
    source.get(start..end)
}

/// Construct the same re-admitted signed read/independent output trace
/// from separate complete source/Clang proofs.
pub(super) fn emit_signed_input_literal(
    input: &Artifact,
    function: &Node,
    body: &Node,
    read_calls: &[&Node],
    literal: &Node,
    write: &Node,
    byte: u8,
) -> Result<CanonicalGuestProjection, FrontendJsonError> {
    let read_count = read_calls.len();
    let frontend = FrontendArtifact::new_void(
        FrontendArtifactSpec {
            abi_id: input.profile.abi_id.clone(),
            artifact_id: input.identity.clone(),
            clang_target: input.clang.target.clone(),
            clang_version: input.clang.version.clone(),
            functions: Vec::new(),
            language: input.clang.language.clone(),
            schema_version: input.schema_version,
            source_id: input.source.id.clone(),
            source_sha256: source_digest(&input.source.sha256)?,
            target_profile: input.profile.target_profile.clone(),
        },
        FrontendReturnVoidFunction::new_fallthrough(
            FrontendFallthroughVoidFunctionSpec {
                body_span: super::span(&body.span),
                definition: String::from("definition"),
                function_span: super::span(&function.span),
                inline_specified: false,
                linkage: String::from("external"),
                name: String::from("emit"),
                signature: String::from("fn()->void"),
                storage_class: String::from("none"),
            },
        ),
    );
    let base = lower_frontend_artifact(&frontend)
        .map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    let original = base
        .functions()
        .first()
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    let block = original
        .blocks()
        .first()
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    let mut types = base.types().to_vec();
    if types.len() != 2 || types[0].id() != TypeId::new(0) {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    types[0] = TypeEntry::new(TypeId::new(0), TypeDef::I32);
    types.push(TypeEntry::new(TypeId::new(2), TypeDef::U8));
    let mut instructions = Vec::with_capacity(read_count + 2);
    for (index, read) in read_calls.iter().enumerate() {
        instructions.push(LocatedInstruction::new(
            Instruction::Getchar {
                result: ValueId::new(
                    u32::try_from(index)
                        .map_err(|_error| FrontendJsonError::Unsupported)?,
                ),
                type_id: TypeId::new(0),
            },
            typed_span(&read.span),
        ));
    }
    let literal_id = ValueId::new(
        u32::try_from(read_count)
            .map_err(|_error| FrontendJsonError::Unsupported)?,
    );
    instructions.push(LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: IntegerConstant::new(8, vec![byte]),
            result: literal_id,
            type_id: TypeId::new(2),
        },
        typed_span(&literal.span),
    ));
    instructions.push(LocatedInstruction::new(
        Instruction::ByteOutput { value: literal_id },
        typed_span(&write.span),
    ));
    let function = Function::new(FunctionSpec {
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
        functions: vec![function],
        globals: base.globals().to_vec(),
        proof_obligations: base.proof_obligations().to_vec(),
        source_id: String::from(base.source_id()),
        source_sha256: *base.source_sha256(),
        target_profile: String::from(base.target_profile()),
        types,
    });
    let wire = canonical_bytes(&module)
        .map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    if canonical_module(&wire)
        .map_err(|_error| FrontendJsonError::InvalidTypedIr)?
        != module
    {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    Ok((wire, FrontendGuestMode::DiscardedInputLiteral))
}

/// Recognize only one `void emit(void)` body with one or two discarded
/// signed reads followed by a source-spelled decimal literal `putchar`. The
/// ordinary frontend source SHA-256 check is also repeated by the caller.
///
/// # Errors
///
/// Refuses any drift in pinned Clang metadata, source spelling, AST ancestry,
/// signed EOF representation, SSA identity or canonical typed admission.
#[expect(
    clippy::too_many_lines,
    reason = "closed Clang source proof and typed reconstruction"
)]
pub(super) fn canonical_signed_input_literal(
    bytes: &[u8],
    source: &[u8],
) -> Result<CanonicalGuestProjection, FrontendJsonError> {
    if bytes.len() > 1_048_576 {
        return Err(FrontendJsonError::Malformed);
    }
    let input: Artifact = serde_json::from_slice(bytes)
        .map_err(|_error| FrontendJsonError::Malformed)?;
    if input.schema_version != 1
        || input.identity != "malbolge-c-frontend-v1"
        || input.profile.abi_id != "malbolge-c32-v1"
        || input.profile.target_profile != "malbolge-2026"
        || input.clang.version != "22.1.8"
        || input.clang.target != "wasm32-unknown-unknown"
        || input.clang.language != "c23"
        || input.source.id.is_empty()
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let [function, body, tail @ ..] = input.nodes.as_slice() else {
        return Err(FrontendJsonError::Unsupported);
    };
    // One or two complete signed reads are currently bounded by a proven
    // graphical layout. No other sibling effects are admitted.
    if tail.len() != 7 && tail.len() != 10 {
        return Err(FrontendJsonError::Unsupported);
    }
    let read_count = (tail.len() - 4) / 3;
    let (reads, output) = tail.split_at(read_count * 3);
    let [write, write_decay, write_callee, literal] = output else {
        return Err(FrontendJsonError::Unsupported);
    };
    let function_ok = function.id == 1
        && function.parent == 0
        && function.kind == "function-declaration"
        && function.name.as_deref() == Some("emit")
        && function.type_name.as_deref() == Some("fn()->void")
        && function.definition.as_deref() == Some("definition")
        && function.inline_specified == Some(false)
        && function.linkage.as_deref() == Some("external")
        && function.storage_class.as_deref() == Some("none")
        && function.storage_duration.is_none()
        && function.reference.is_none()
        && function.operation.is_none()
        && function.constant_integer.is_none()
        && function.literal.is_none()
        && function.span.begin.byte < function.span.end.byte
        && function.span.begin.line > 0;
    let mut read_calls = Vec::with_capacity(read_count);
    let mut preceding_end = body.span.begin.byte;
    for (index, nodes) in reads.chunks_exact(3).enumerate() {
        let [read, decay, callee] = nodes else {
            return Err(FrontendJsonError::Unsupported);
        };
        let id = 3 + u32::try_from(index * 3)
            .map_err(|_error| FrontendJsonError::Unsupported)?;
        if !node_is(
            read,
            id,
            2,
            "call-expression",
            Some("i32"),
            Some("external:getchar"),
            None,
        ) || !node_is(
            decay,
            id + 1,
            id,
            "cast-expression",
            Some("ptr(fn()->i32)"),
            None,
            Some("function-to-pointer"),
        ) || !node_is(
            callee,
            id + 2,
            id + 1,
            "declaration-reference-expression",
            Some("fn()->i32"),
            Some("external:getchar"),
            None,
        ) || preceding_end >= read.span.begin.byte
            || read.span.begin != decay.span.begin
            || decay.span != callee.span
            || source_slice(source, read) != Some(b"getchar()")
            || source_slice(source, decay) != Some(b"getchar")
        {
            return Err(FrontendJsonError::Unsupported);
        }
        preceding_end = read.span.end.byte;
        read_calls.push(read);
    }
    let write_id = 3 + u32::try_from(read_count * 3)
        .map_err(|_error| FrontendJsonError::Unsupported)?;
    if !function_ok
        || !node_is(body, 2, 1, "compound-statement", None, None, None)
        || !node_is(
            write,
            write_id,
            2,
            "call-expression",
            Some("i32"),
            Some("external:putchar"),
            None,
        )
        || !node_is(
            write_decay,
            write_id + 1,
            write_id,
            "cast-expression",
            Some("ptr(fn(i32)->i32)"),
            None,
            Some("function-to-pointer"),
        )
        || !node_is(
            write_callee,
            write_id + 2,
            write_id + 1,
            "declaration-reference-expression",
            Some("fn(i32)->i32"),
            Some("external:putchar"),
            None,
        )
        || !node_is(
            literal,
            write_id + 3,
            write_id,
            "integer-literal",
            Some("i32"),
            None,
            None,
        )
        || body.span.end != function.span.end
        || body.span.begin.byte <= function.span.begin.byte
        || preceding_end >= write.span.begin.byte
        || write.span.end.byte >= body.span.end.byte
        || write.span.begin != write_decay.span.begin
        || write_decay.span != write_callee.span
        || literal.span.begin.byte
            != write_decay.span.end.byte.checked_add(1).unwrap_or(0)
        || literal.span.end.byte.checked_add(1) != Some(write.span.end.byte)
        || source_slice(source, write_decay) != Some(b"putchar")
        || source_slice(source, body).is_none_or(|bytes| {
            !bytes.starts_with(b"{") || !bytes.ends_with(b"}")
        })
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let digits =
        source_slice(source, literal).ok_or(FrontendJsonError::Unsupported)?;
    if digits.is_empty()
        || !digits.iter().all(u8::is_ascii_digit)
        || (digits.len() > 1 && digits[0] == b'0')
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let decimal = str::from_utf8(digits)
        .map_err(|_error| FrontendJsonError::Unsupported)?;
    let byte = decimal
        .parse::<u8>()
        .map_err(|_error| FrontendJsonError::Unsupported)?;
    if literal.constant_integer.as_deref() != Some(decimal)
        || literal.literal.as_deref() != Some(decimal)
        || source_slice(source, write)
            != Some(format!("putchar({decimal})").as_bytes())
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let body_bytes =
        source_slice(source, body).ok_or(FrontendJsonError::Unsupported)?;
    let expected = format!(
        "{{ {}putchar({decimal}); }}",
        "getchar(); ".repeat(read_count)
    );
    if body_bytes != expected.as_bytes() {
        return Err(FrontendJsonError::Unsupported);
    }
    emit_signed_input_literal(
        &input,
        function,
        body,
        &read_calls,
        literal,
        write,
        byte,
    )
}

/// Authenticate a discarded signed read followed by one signed read fed to
/// putchar. EOF must be converted from signed C -1 to byte 255 in the guest.
/// No host-provided input, source output bytes or general C echo is inferred.
///
/// # Errors
/// Rejects all but the closed two-call source/Clang C23 effect grammar.
#[expect(
    clippy::too_many_lines,
    reason = "source AST, typed SSA and guest EOF conversion gate"
)]
pub(super) fn canonical_signed_second_echo(
    bytes: &[u8],
    source: &[u8],
) -> Result<CanonicalGuestProjection, FrontendJsonError> {
    if bytes.len() > super::MAX_FRONTEND_JSON_BYTES {
        return Err(FrontendJsonError::Malformed);
    }
    let input: Artifact = serde_json::from_slice(bytes)
        .map_err(|_error| FrontendJsonError::Malformed)?;
    if input.nodes.len() == 15 {
        return canonical_signed_second_local_echo(&input, source);
    }
    let [
        function,
        body,
        first,
        first_decay,
        first_callee,
        write,
        write_decay,
        write_callee,
        second,
        second_decay,
        second_callee,
    ] = input.nodes.as_slice()
    else {
        return Err(FrontendJsonError::Unsupported);
    };
    if input.schema_version != 1
        || input.identity != super::EXPECTED_ARTIFACT
        || input.profile.abi_id != super::EXPECTED_ABI
        || input.profile.target_profile != super::EXPECTED_PROFILE
        || input.clang.version != "22.1.8"
        || input.clang.target != "wasm32-unknown-unknown"
        || input.clang.language != "c23"
        || input.source.id.is_empty()
        || function.name.as_deref() != Some("emit")
        || function.type_name.as_deref() != Some("fn()->void")
        || function.definition.as_deref() != Some("definition")
        || function.inline_specified != Some(false)
        || function.linkage.as_deref() != Some("external")
        || function.storage_class.as_deref() != Some("none")
        || function.storage_duration.is_some()
        || function.reference.is_some()
        || function.operation.is_some()
        || function.literal.is_some()
        || function.constant_integer.is_some()
        || function.id != 1
        || function.parent != 0
        || function.kind != "function-declaration"
        || !node_is(body, 2, 1, "compound-statement", None, None, None)
        || !node_is(
            first,
            3,
            2,
            "call-expression",
            Some("i32"),
            Some("external:getchar"),
            None,
        )
        || !node_is(
            first_decay,
            4,
            3,
            "cast-expression",
            Some("ptr(fn()->i32)"),
            None,
            Some("function-to-pointer"),
        )
        || !node_is(
            first_callee,
            5,
            4,
            "declaration-reference-expression",
            Some("fn()->i32"),
            Some("external:getchar"),
            None,
        )
        || !node_is(
            write,
            6,
            2,
            "call-expression",
            Some("i32"),
            Some("external:putchar"),
            None,
        )
        || !node_is(
            write_decay,
            7,
            6,
            "cast-expression",
            Some("ptr(fn(i32)->i32)"),
            None,
            Some("function-to-pointer"),
        )
        || !node_is(
            write_callee,
            8,
            7,
            "declaration-reference-expression",
            Some("fn(i32)->i32"),
            Some("external:putchar"),
            None,
        )
        || !node_is(
            second,
            9,
            6,
            "call-expression",
            Some("i32"),
            Some("external:getchar"),
            None,
        )
        || !node_is(
            second_decay,
            10,
            9,
            "cast-expression",
            Some("ptr(fn()->i32)"),
            None,
            Some("function-to-pointer"),
        )
        || !node_is(
            second_callee,
            11,
            10,
            "declaration-reference-expression",
            Some("fn()->i32"),
            Some("external:getchar"),
            None,
        )
        || body.span.end != function.span.end
        || function.span.begin.byte >= body.span.begin.byte
        || !(body.span.begin.byte < first.span.begin.byte
            && first.span.end.byte < write.span.begin.byte
            && write.span.end.byte < body.span.end.byte)
        || first.span.begin != first_decay.span.begin
        || first_decay.span != first_callee.span
        || write.span.begin != write_decay.span.begin
        || write_decay.span != write_callee.span
        || second.span.begin != second_decay.span.begin
        || second_decay.span != second_callee.span
        || source_slice(source, body)
            != Some(b"{ getchar(); putchar(getchar()); }")
        || source_slice(source, first) != Some(b"getchar()")
        || source_slice(source, first_decay) != Some(b"getchar")
        || source_slice(source, write) != Some(b"putchar(getchar())")
        || source_slice(source, write_decay) != Some(b"putchar")
        || source_slice(source, second) != Some(b"getchar()")
        || source_slice(source, second_decay) != Some(b"getchar")
    {
        return Err(FrontendJsonError::Unsupported);
    }
    emit_signed_second_echo(&input, function, body, first, second, write)
}

fn emit_signed_second_echo(
    input: &Artifact,
    function: &Node,
    body: &Node,
    first: &Node,
    second: &Node,
    write: &Node,
) -> Result<CanonicalGuestProjection, FrontendJsonError> {
    // Source SHA is independently rechecked in the caller, before admission.
    let frontend = FrontendArtifact::new_void(
        FrontendArtifactSpec {
            abi_id: input.profile.abi_id.clone(),
            artifact_id: input.identity.clone(),
            clang_target: input.clang.target.clone(),
            clang_version: input.clang.version.clone(),
            functions: Vec::new(),
            language: input.clang.language.clone(),
            schema_version: input.schema_version,
            source_id: input.source.id.clone(),
            source_sha256: source_digest(&input.source.sha256)?,
            target_profile: input.profile.target_profile.clone(),
        },
        FrontendReturnVoidFunction::new_fallthrough(
            FrontendFallthroughVoidFunctionSpec {
                body_span: super::span(&body.span),
                definition: String::from("definition"),
                function_span: super::span(&function.span),
                inline_specified: false,
                linkage: String::from("external"),
                name: String::from("emit"),
                signature: String::from("fn()->void"),
                storage_class: String::from("none"),
            },
        ),
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
    let mut types = base.types().to_vec();
    if types.len() != 2 || types[0].id() != TypeId::new(0) {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    types[0] = TypeEntry::new(TypeId::new(0), TypeDef::I32);
    types.push(TypeEntry::new(TypeId::new(2), TypeDef::U8));
    let instructions = vec![
        LocatedInstruction::new(
            Instruction::Getchar {
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            typed_span(&first.span),
        ),
        LocatedInstruction::new(
            Instruction::Getchar {
                result: ValueId::new(1),
                type_id: TypeId::new(0),
            },
            typed_span(&second.span),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::Truncate,
                result: ValueId::new(2),
                type_id: TypeId::new(2),
                value: ValueId::new(1),
            },
            typed_span(&second.span),
        ),
        LocatedInstruction::new(
            Instruction::ByteOutput { value: ValueId::new(2) },
            typed_span(&write.span),
        ),
    ];
    let function = Function::new(FunctionSpec {
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
        functions: vec![function],
        globals: base.globals().to_vec(),
        proof_obligations: base.proof_obligations().to_vec(),
        source_id: String::from(base.source_id()),
        source_sha256: *base.source_sha256(),
        target_profile: String::from(base.target_profile()),
        types,
    });
    let wire = canonical_bytes(&module)
        .map_err(|_| FrontendJsonError::InvalidTypedIr)?;
    if canonical_module(&wire).map_err(|_| FrontendJsonError::InvalidTypedIr)?
        != module
    {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    Ok((wire, FrontendGuestMode::SignedSecondEcho))
}

/// Source-checked automatic `int` alias for the already-linked second signed
/// guest input. The local must contain exactly the second `getchar()` result;
/// no reassignment, extra call, integer arithmetic, or host-computed value
/// is allowed to bypass the physical EOF converter.
fn canonical_signed_second_local_echo(
    input: &Artifact,
    source: &[u8],
) -> Result<CanonicalGuestProjection, FrontendJsonError> {
    let [
        function,
        body,
        first,
        first_decay,
        first_callee,
        declaration,
        local,
        second,
        second_decay,
        second_callee,
        write,
        write_decay,
        write_callee,
        load,
        reference,
    ] = input.nodes.as_slice()
    else {
        return Err(FrontendJsonError::Unsupported);
    };
    let name = local
        .name
        .as_deref()
        .ok_or(FrontendJsonError::Unsupported)?;
    let name_bytes = name.as_bytes();
    if name_bytes.is_empty()
        || name_bytes.len() > 32
        || !(name_bytes[0].is_ascii_alphabetic() || name_bytes[0] == b'_')
        || !name_bytes[1..]
            .iter()
            .all(|byte| byte.is_ascii_alphanumeric() || *byte == b'_')
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let declared_at = local
        .span
        .begin
        .byte
        .checked_add(4)
        .ok_or(FrontendJsonError::Unsupported)?;
    let identity = format!("{name}@{declared_at}");
    let expected_body =
        format!("{{ getchar(); int {name} = getchar(); putchar({name}); }}");
    let expected_local = format!("int {name} = getchar()");
    let expected_write = format!("putchar({name})");
    if input.schema_version != 1
        || input.identity != super::EXPECTED_ARTIFACT
        || input.profile.abi_id != super::EXPECTED_ABI
        || input.profile.target_profile != super::EXPECTED_PROFILE
        || input.clang.version != "22.1.8"
        || input.clang.target != "wasm32-unknown-unknown"
        || input.clang.language != "c23"
        || input.source.id.is_empty()
        || function.id != 1
        || function.parent != 0
        || function.kind != "function-declaration"
        || function.name.as_deref() != Some("emit")
        || function.type_name.as_deref() != Some("fn()->void")
        || function.definition.as_deref() != Some("definition")
        || function.inline_specified != Some(false)
        || function.linkage.as_deref() != Some("external")
        || function.storage_class.as_deref() != Some("none")
        || function.storage_duration.is_some()
        || function.reference.is_some()
        || function.operation.is_some()
        || function.literal.is_some()
        || function.constant_integer.is_some()
        || !node_is(body, 2, 1, "compound-statement", None, None, None)
        || !node_is(
            first,
            3,
            2,
            "call-expression",
            Some("i32"),
            Some("external:getchar"),
            None,
        )
        || !node_is(
            first_decay,
            4,
            3,
            "cast-expression",
            Some("ptr(fn()->i32)"),
            None,
            Some("function-to-pointer"),
        )
        || !node_is(
            first_callee,
            5,
            4,
            "declaration-reference-expression",
            Some("fn()->i32"),
            Some("external:getchar"),
            None,
        )
        || !node_is(
            declaration,
            6,
            2,
            "declaration-statement",
            None,
            None,
            None,
        )
        || local.id != 7
        || local.parent != 6
        || local.kind != "variable-declaration"
        || local.type_name.as_deref() != Some("i32")
        || local.reference.as_deref() != Some(identity.as_str())
        || local.definition.as_deref() != Some("definition")
        || local.linkage.as_deref() != Some("none")
        || local.storage_class.as_deref() != Some("none")
        || !matches!(
            local.storage_duration,
            Some(super::StorageDuration::Automatic)
        )
        || local.inline_specified.is_some()
        || local.operation.is_some()
        || local.constant_integer.is_some()
        || local.literal.is_some()
        || !node_is(
            second,
            8,
            7,
            "call-expression",
            Some("i32"),
            Some("external:getchar"),
            None,
        )
        || !node_is(
            second_decay,
            9,
            8,
            "cast-expression",
            Some("ptr(fn()->i32)"),
            None,
            Some("function-to-pointer"),
        )
        || !node_is(
            second_callee,
            10,
            9,
            "declaration-reference-expression",
            Some("fn()->i32"),
            Some("external:getchar"),
            None,
        )
        || !node_is(
            write,
            11,
            2,
            "call-expression",
            Some("i32"),
            Some("external:putchar"),
            None,
        )
        || !node_is(
            write_decay,
            12,
            11,
            "cast-expression",
            Some("ptr(fn(i32)->i32)"),
            None,
            Some("function-to-pointer"),
        )
        || !node_is(
            write_callee,
            13,
            12,
            "declaration-reference-expression",
            Some("fn(i32)->i32"),
            Some("external:putchar"),
            None,
        )
        || !node_is(
            load,
            14,
            11,
            "cast-expression",
            Some("i32"),
            None,
            Some("lvalue-to-rvalue"),
        )
        || !node_is(
            reference,
            15,
            14,
            "declaration-reference-expression",
            Some("i32"),
            Some(identity.as_str()),
            None,
        )
        || function.span.end != body.span.end
        || !(function.span.begin.byte < body.span.begin.byte
            && body.span.begin.byte < first.span.begin.byte
            && first.span.end.byte < declaration.span.begin.byte
            && declaration.span.end.byte < write.span.begin.byte
            && write.span.end.byte < body.span.end.byte)
        || local.span.begin != declaration.span.begin
        || local.span.end.byte.checked_add(1) != Some(declaration.span.end.byte)
        || second.span.begin.byte <= local.span.begin.byte
        || second.span.end != local.span.end
        || first.span.begin != first_decay.span.begin
        || first_decay.span != first_callee.span
        || second.span.begin != second_decay.span.begin
        || second_decay.span != second_callee.span
        || write.span.begin != write_decay.span.begin
        || write_decay.span != write_callee.span
        || load.span != reference.span
        || source_slice(source, body) != Some(expected_body.as_bytes())
        || source_slice(source, first) != Some(b"getchar()")
        || source_slice(source, first_decay) != Some(b"getchar")
        || source_slice(source, local) != Some(expected_local.as_bytes())
        || source_slice(source, second) != Some(b"getchar()")
        || source_slice(source, second_decay) != Some(b"getchar")
        || source_slice(source, write) != Some(expected_write.as_bytes())
        || source_slice(source, write_decay) != Some(b"putchar")
        || source_slice(source, load) != Some(name_bytes)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    emit_signed_second_echo(input, function, body, first, second, write)
}
