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
    BasicBlock, BasicBlockSpec, FrontendArtifact, FrontendArtifactSpec,
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
fn node_is(
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

fn source_slice<'a>(source: &'a [u8], node: &Node) -> Option<&'a [u8]> {
    let start = usize::try_from(node.span.begin.byte).ok()?;
    let end = usize::try_from(node.span.end.byte).ok()?;
    source.get(start..end)
}

/// Recognize only one `void emit(void)` body with a discarded signed read
/// followed by a source-spelled decimal literal `putchar`. The ordinary
/// frontend source SHA-256 check is also repeated by the caller.
///
/// # Errors
///
/// Refuses any drift in pinned Clang metadata, source spelling, AST ancestry,
/// signed EOF representation, SSA identity or canonical typed admission.
#[expect(
    clippy::too_many_lines,
    reason = "exact nine-node Clang source proof and typed reconstruction"
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
    let [
        function,
        body,
        read,
        read_decay,
        read_callee,
        write,
        write_decay,
        write_callee,
        literal,
    ] = input.nodes.as_slice()
    else {
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
    if !function_ok
        || !node_is(body, 2, 1, "compound-statement", None, None, None)
        || !node_is(
            read,
            3,
            2,
            "call-expression",
            Some("i32"),
            Some("external:getchar"),
            None,
        )
        || !node_is(
            read_decay,
            4,
            3,
            "cast-expression",
            Some("ptr(fn()->i32)"),
            None,
            Some("function-to-pointer"),
        )
        || !node_is(
            read_callee,
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
        || !node_is(literal, 9, 6, "integer-literal", Some("i32"), None, None)
        || body.span.end != function.span.end
        || body.span.begin.byte <= function.span.begin.byte
        || !(body.span.begin.byte < read.span.begin.byte
            && read.span.end.byte < write.span.begin.byte
            && write.span.end.byte < body.span.end.byte)
        || read.span.begin != read_decay.span.begin
        || read_decay.span != read_callee.span
        || write.span.begin != write_decay.span.begin
        || write_decay.span != write_callee.span
        || literal.span.begin.byte
            != write_decay.span.end.byte.checked_add(1).unwrap_or(0)
        || literal.span.end.byte.checked_add(1) != Some(write.span.end.byte)
        || source_slice(source, read) != Some(b"getchar()")
        || source_slice(source, read_decay) != Some(b"getchar")
        || source_slice(source, write_decay) != Some(b"putchar")
        || source_slice(source, body)
            .is_none_or(|body| !body.starts_with(b"{") || !body.ends_with(b"}"))
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
    let expected = format!("{{ getchar(); putchar({decimal}); }}");
    if body_bytes != expected.as_bytes() {
        return Err(FrontendJsonError::Unsupported);
    }
    let frontend = FrontendArtifact::new_void(
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
    let function = Function::new(FunctionSpec {
        blocks: vec![BasicBlock::new(BasicBlockSpec {
            id: block.id(),
            instructions: vec![
                LocatedInstruction::new(
                    Instruction::Getchar {
                        result: ValueId::new(0),
                        type_id: TypeId::new(0),
                    },
                    typed_span(&read.span),
                ),
                LocatedInstruction::new(
                    Instruction::ConstantInteger {
                        constant: IntegerConstant::new(8, vec![byte]),
                        result: ValueId::new(1),
                        type_id: TypeId::new(2),
                    },
                    typed_span(&literal.span),
                ),
                LocatedInstruction::new(
                    Instruction::ByteOutput { value: ValueId::new(1) },
                    typed_span(&write.span),
                ),
            ],
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
