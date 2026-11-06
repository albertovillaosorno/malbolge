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
//   - Source-bound automatic unsigned local SSA promotion for byte output.
// - Must-Not:
//   - Drop mutation, aliasing, control flow, or variable-derived guest effects.
// - Allows:
//   - Inputs: one initialized u32 automatic local, read once by putchar.
//   - Outputs: re-admitted typed byte SSA with a verified guest output mode.
//   - Side effects: none.
// - Split-When:
//   - General automatic C storage lowering owns SSA promotion.
// - Merge-When:
//   - A general frontend semantic projection subsumes this closed slice.
// - Summary:
//   - Promote one unmodified local to SSA, preserving its source dependencies.
// - Description:
//   - A constant initializer is converted only within the defined byte range.
// - Usage:
//   - Called after the effect-free frontend projection is ruled out.
// - Defaults:
//   - Anything beyond the admitted Clang topology remains unsupported.

//! Closed, source-bound mem2reg of one automatic unsigned local used by output.

use typed::{
    BasicBlock, BasicBlockSpec, FrontendArtifact, FrontendArtifactSpec,
    FrontendFallthroughVoidFunctionSpec, FrontendReturnVoidFunction,
    FrontendReturnVoidFunctionSpec, Function, FunctionSpec, Instruction,
    IntegerConstant, LocatedInstruction, Module, ModuleSpec, TypeId, ValueId,
};

use super::{
    Artifact, FrontendGuestMode, FrontendJsonError, Node, Span,
    StorageDuration, canonical_bytes, canonical_module,
    lower_frontend_artifact, source_digest, typed, typed_span,
};

const fn clean(node: &Node) -> bool {
    node.name.is_none()
        && node.type_name.is_none()
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

const fn span_within(parent: &Span, child: &Span) -> bool {
    let begin = &child.begin;
    let end = &child.end;
    begin.byte >= parent.begin.byte
        && end.byte <= parent.end.byte
        && begin.byte < end.byte
        && begin.line > 0
        && begin.column > 0
        && end.line >= begin.line
        && end.column > 0
        && (end.line > begin.line || end.column > begin.column)
}

fn correct_node(node: &Node, id: u32, parent: u32, kind: &str) -> bool {
    node.id == id && node.parent == parent && node.kind == kind
}

fn named_local_reference(
    declaration: &Node,
    read: &Node,
    literal: &Node,
) -> bool {
    let (Some(name), Some(symbol), Some(use_symbol)) = (
        declaration.name.as_deref(),
        declaration.reference.as_deref(),
        read.reference.as_deref(),
    ) else {
        return false;
    };
    let Some((reference_name, offset)) = use_symbol.rsplit_once('@') else {
        return false;
    };
    let Ok(name_byte) = offset.parse::<u32>() else {
        return false;
    };
    !name.is_empty()
        && reference_name == name
        && symbol == use_symbol
        && name_byte >= declaration.span.begin.byte
        && name_byte
            .checked_add(u32::try_from(name.len()).unwrap_or(u32::MAX))
            .is_some_and(|end| end <= literal.span.begin.byte)
}

/// Returns a verified typed SSA byte effect only for one unmodified local.
///
/// Clang has already normalized the initializer and use to an unsigned 32-bit
/// value. A source-bound single-definition/single-use local can be promoted
/// to SSA without guest storage; the narrowed `0..255` domain makes the
/// implicit `u32`-to-`i32` call conversion and byte output unambiguous.
///
/// # Errors
///
/// Rejects any extra C node, unsupported source semantics, invalid normalized
/// identity, or non-canonical typed IR. A guest witness is still mandatory.
#[expect(
    clippy::too_many_lines,
    clippy::redundant_pub_crate,
    reason = "closed Clang tree admission in a private module"
)]
pub(super) fn canonical_local_initialized_output(
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
    let [
        function,
        body,
        statement,
        variable,
        literal,
        call,
        cast,
        callee,
        conversion,
        load,
        reference,
        rest @ ..,
    ] = input.nodes.as_slice()
    else {
        return Err(FrontendJsonError::Unsupported);
    };
    let returned = match rest {
        [] => None,
        [last]
            if correct_node(last, 12, 2, "return-statement") && clean(last) =>
        {
            Some(last)
        },
        _ => return Err(FrontendJsonError::Unsupported),
    };
    let byte = literal
        .constant_integer
        .as_deref()
        .and_then(|value| value.parse::<u8>().ok())
        .ok_or(FrontendJsonError::Unsupported)?;
    if !correct_node(function, 1, 0, "function-declaration")
        || function.name.as_deref().is_none_or(str::is_empty)
        || function.type_name.as_deref() != Some("fn()->void")
        || function.definition.as_deref() != Some("definition")
        || function.inline_specified != Some(false)
        || function.linkage.as_deref() != Some("external")
        || function.storage_class.as_deref() != Some("none")
        || function.storage_duration.is_some()
        || function.reference.is_some()
        || function.operation.is_some()
        || function.constant_integer.is_some()
        || function.literal.is_some()
        || !correct_node(body, 2, 1, "compound-statement")
        || !clean(body)
        || !correct_node(statement, 3, 2, "declaration-statement")
        || !clean(statement)
        || !correct_node(variable, 4, 3, "variable-declaration")
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
        || !correct_node(literal, 5, 4, "integer-literal")
        || literal.type_name.as_deref() != Some("u32")
        || literal.literal.as_deref() != literal.constant_integer.as_deref()
        || literal.name.is_some()
        || literal.reference.is_some()
        || literal.operation.is_some()
        || literal.definition.is_some()
        || literal.inline_specified.is_some()
        || literal.linkage.is_some()
        || literal.storage_class.is_some()
        || literal.storage_duration.is_some()
        || !correct_node(call, 6, 2, "call-expression")
        || call.type_name.as_deref() != Some("i32")
        || call.reference.as_deref() != Some("external:putchar")
        || !correct_node(cast, 7, 6, "cast-expression")
        || cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
        || cast.operation.as_deref() != Some("function-to-pointer")
        || !correct_node(callee, 8, 7, "declaration-reference-expression")
        || callee.type_name.as_deref() != Some("fn(i32)->i32")
        || callee.reference.as_deref() != Some("external:putchar")
        || !correct_node(conversion, 9, 6, "cast-expression")
        || conversion.type_name.as_deref() != Some("i32")
        || conversion.operation.as_deref() != Some("integral-cast")
        || !correct_node(load, 10, 9, "cast-expression")
        || load.type_name.as_deref() != Some("u32")
        || load.operation.as_deref() != Some("lvalue-to-rvalue")
        || !correct_node(reference, 11, 10, "declaration-reference-expression")
        || reference.type_name.as_deref() != Some("u32")
        || ![call, cast, callee, conversion, load, reference]
            .iter()
            .all(|node| {
                node.name.is_none()
                    && node.constant_integer.is_none()
                    && node.literal.is_none()
                    && node.definition.is_none()
                    && node.inline_specified.is_none()
                    && node.linkage.is_none()
                    && node.storage_class.is_none()
                    && node.storage_duration.is_none()
                    && (node.id == 6
                        || node.id == 8
                        || node.id == 11
                        || node.reference.is_none())
                    && (node.id == 7
                        || node.id == 9
                        || node.id == 10
                        || node.operation.is_none())
            })
        || !named_local_reference(variable, reference, literal)
        || !span_within(&function.span, &body.span)
        || !span_within(&body.span, &statement.span)
        || !span_within(&statement.span, &variable.span)
        || !span_within(&variable.span, &literal.span)
        || !span_within(&body.span, &call.span)
        || !span_within(&call.span, &cast.span)
        || !span_within(&cast.span, &callee.span)
        || !span_within(&call.span, &conversion.span)
        || !span_within(&conversion.span, &load.span)
        || !span_within(&load.span, &reference.span)
        || statement.span.end.byte > call.span.begin.byte
        || returned.is_some_and(|node| {
            !span_within(&body.span, &node.span)
                || call.span.end.byte > node.span.begin.byte
        })
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let name = function
        .name
        .clone()
        .ok_or(FrontendJsonError::Unsupported)?;
    let void_function = if let Some(return_node) = returned {
        FrontendReturnVoidFunction::new(FrontendReturnVoidFunctionSpec {
            body_span: super::span(&body.span),
            definition: String::from("definition"),
            function_span: super::span(&function.span),
            inline_specified: false,
            linkage: String::from("external"),
            name,
            return_span: super::span(&return_node.span),
            signature: String::from("fn()->void"),
            storage_class: String::from("none"),
        })
    } else {
        FrontendReturnVoidFunction::new_fallthrough(
            FrontendFallthroughVoidFunctionSpec {
                body_span: super::span(&body.span),
                definition: String::from("definition"),
                function_span: super::span(&function.span),
                inline_specified: false,
                linkage: String::from("external"),
                name,
                signature: String::from("fn()->void"),
                storage_class: String::from("none"),
            },
        )
    };
    let projection = FrontendArtifact::new_void(
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
    let base = lower_frontend_artifact(&projection)
        .map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    let original = base
        .functions()
        .first()
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    let block = original
        .blocks()
        .first()
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    let instructions = vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(8, vec![byte]),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            typed_span(&literal.span),
        ),
        LocatedInstruction::new(
            Instruction::ByteOutput { value: ValueId::new(0) },
            typed_span(&call.span),
        ),
    ];
    let compiled_function = Function::new(FunctionSpec {
        blocks: vec![BasicBlock::new(BasicBlockSpec {
            id: block.id(),
            instructions,
            phis: Vec::new(),
            span: block.span(),
            terminator: block.terminator().clone(),
            terminator_span: block.terminator_span(),
        })],
        entry: original.entry(),
        id: original.id(),
        name: String::from(original.name()),
        parameters: Vec::new(),
        signature: original.signature(),
        span: original.span(),
    });
    let module = Module::new(ModuleSpec {
        abi_id: String::from(base.abi_id()),
        format_version: base.format_version(),
        functions: vec![compiled_function],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
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
    let mode = if byte == 0 {
        FrontendGuestMode::InitialZeroOutput
    } else {
        FrontendGuestMode::SeededByteLiteral
    };
    Ok((wire, mode))
}
