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
//   - Source-bound constant propagation of one automatic unsigned local.
// - Must-Not:
//   - Drop runtime state, aliasing, control flow, or opaque guest effects.
// - Allows:
//   - Inputs: one initialized u32 local with bounded ordered writes.
//   - Outputs: re-admitted typed byte SSA with a verified guest output mode.
//   - Side effects: none.
// - Split-When:
//   - General automatic C storage lowering owns SSA promotion.
// - Merge-When:
//   - A general frontend semantic projection subsumes this closed slice.
// - Summary:
//   - Promote source-proven constant and arithmetic writes to byte SSA.
// - Description:
//   - Arithmetic reads the prior local value; every result stays byte-sized.
// - Usage:
//   - Called after the effect-free frontend projection is ruled out.
// - Defaults:
//   - Anything beyond the admitted Clang topology remains unsupported.

//! Closed source-bound propagation of byte-sized automatic-local writes.

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

/// Admit only the exact source-backed Clang `u32` integer leaf.
fn literal_byte(node: &Node) -> Option<u8> {
    if node.kind != "integer-literal"
        || node.type_name.as_deref() != Some("u32")
        || node.literal.as_deref() != node.constant_integer.as_deref()
        || node.name.is_some()
        || node.reference.is_some()
        || node.operation.is_some()
        || node.definition.is_some()
        || node.inline_specified.is_some()
        || node.linkage.is_some()
        || node.storage_class.is_some()
        || node.storage_duration.is_some()
    {
        return None;
    }
    node.constant_integer.as_deref()?.parse::<u8>().ok()
}

fn assigned_local_reference(node: &Node, symbol: &str) -> bool {
    node.kind == "declaration-reference-expression"
        && node.type_name.as_deref() == Some("u32")
        && node.reference.as_deref() == Some(symbol)
        && node.name.is_none()
        && node.operation.is_none()
        && node.constant_integer.is_none()
        && node.literal.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
}

/// The type and operator are the only metadata permitted on an expression.
fn typed_operator(node: &Node, operation: &str) -> bool {
    node.type_name.as_deref() == Some("u32")
        && node.operation.as_deref() == Some(operation)
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

/// Evaluate a proven read of the previous local value and a u32 byte operand.
/// Each operation remains inside 0..255; wider or wrapping state is not yet
/// representable by the selected typed byte-output backend.
fn source_derived_byte(
    expression: &Node,
    tail: &[Node],
    symbol: &str,
    previous: u8,
) -> Option<u8> {
    let [load, read, operand, ..] = tail else {
        return None;
    };
    let load_id = expression.id.checked_add(1)?;
    let read_id = expression.id.checked_add(2)?;
    let operand_id = expression.id.checked_add(3)?;
    if expression.kind != "binary-expression"
        || !matches!(expression.operation.as_deref(), Some("+" | "-" | "^"))
        || !typed_operator(expression, expression.operation.as_deref()?)
        || !correct_node(load, load_id, expression.id, "cast-expression")
        || !typed_operator(load, "lvalue-to-rvalue")
        || !correct_node(
            read,
            read_id,
            load_id,
            "declaration-reference-expression",
        )
        || !assigned_local_reference(read, symbol)
        || !correct_node(operand, operand_id, expression.id, "integer-literal")
        || !span_within(&expression.span, &load.span)
        || !span_within(&load.span, &read.span)
        || !span_within(&expression.span, &operand.span)
        || load.span.begin.byte != expression.span.begin.byte
        || load.span.begin.byte != read.span.begin.byte
        || load.span.end.byte != read.span.end.byte
        || load.span.end.byte >= operand.span.begin.byte
        || operand.span.end.byte != expression.span.end.byte
    {
        return None;
    }
    let immediate = literal_byte(operand)?;
    let value = match expression.operation.as_deref()? {
        "+" => previous.checked_add(immediate)?,
        "-" => previous.checked_sub(immediate)?,
        "^" => previous ^ immediate,
        _ => return None,
    };
    Some(value)
}

/// Returns a verified typed SSA byte effect for a source-bound automatic local.
///
/// Clang has normalized the initializer, consecutive assignments and final
/// read. Verified assignments may use a literal or a read of the previous
/// value with bounded unsigned arithmetic. With no aliases or intervening
/// effects, these ordered definitions reduce to their final SSA value. The
/// `0..255` domain preserves the implicit `u32`-to-`i32` call conversion.
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
    let [function, body, statement, variable, literal, tail @ ..] =
        input.nodes.as_slice()
    else {
        return Err(FrontendJsonError::Unsupported);
    };
    let initial_byte =
        literal_byte(literal).ok_or(FrontendJsonError::Unsupported)?;
    // Each assignment is an ordered C side effect. Eliminate dead writes
    // only because the complete AST excludes aliases and earlier reads.
    // Attribute the live SSA value to its actual final source definition.
    let mut definitions = vec![(literal, initial_byte)];
    let mut remainder = tail;
    let mut next_id: u32 = 6;
    let mut last_end = statement.span.end.byte;
    while remainder
        .first()
        .is_some_and(|node| node.kind == "binary-expression")
    {
        let [assignment, left, right, rest @ ..] = remainder else {
            return Err(FrontendJsonError::Unsupported);
        };
        if definitions.len() >= 9 {
            return Err(FrontendJsonError::Unsupported);
        }
        let symbol = variable.reference.as_deref().unwrap_or_default();
        let left_id = next_id
            .checked_add(1)
            .ok_or(FrontendJsonError::Unsupported)?;
        let right_id = next_id
            .checked_add(2)
            .ok_or(FrontendJsonError::Unsupported)?;
        let (live_source, byte, consumed) = match right.kind.as_str() {
            "integer-literal" => (
                right,
                literal_byte(right).ok_or(FrontendJsonError::Unsupported)?,
                3usize,
            ),
            "binary-expression" => {
                let previous = definitions
                    .last()
                    .map(|(_source, value)| *value)
                    .ok_or(FrontendJsonError::Unsupported)?;
                let value = source_derived_byte(right, rest, symbol, previous)
                    .ok_or(FrontendJsonError::Unsupported)?;
                (right, value, 6usize)
            },
            _ => return Err(FrontendJsonError::Unsupported),
        };
        if !correct_node(assignment, next_id, 2, "binary-expression")
            || assignment.type_name.as_deref() != Some("u32")
            || assignment.operation.as_deref() != Some("=")
            || assignment.name.is_some()
            || assignment.reference.is_some()
            || assignment.constant_integer.is_some()
            || assignment.literal.is_some()
            || assignment.definition.is_some()
            || assignment.inline_specified.is_some()
            || assignment.linkage.is_some()
            || assignment.storage_class.is_some()
            || assignment.storage_duration.is_some()
            || !correct_node(
                left,
                left_id,
                next_id,
                "declaration-reference-expression",
            )
            || !assigned_local_reference(left, symbol)
            || !correct_node(right, right_id, next_id, &right.kind)
            || !span_within(&body.span, &assignment.span)
            || !span_within(&assignment.span, &left.span)
            || !span_within(&assignment.span, &right.span)
            || last_end > assignment.span.begin.byte
            || left.span.begin.byte != assignment.span.begin.byte
            || left.span.end.byte >= right.span.begin.byte
            || right.span.end.byte != assignment.span.end.byte
        {
            return Err(FrontendJsonError::Unsupported);
        }
        last_end = assignment.span.end.byte;
        definitions.push((live_source, byte));
        remainder = remainder
            .get(consumed..)
            .ok_or(FrontendJsonError::Unsupported)?;
        next_id = next_id
            .checked_add(
                u32::try_from(consumed)
                    .map_err(|_error| FrontendJsonError::Unsupported)?,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
    }
    let cast_id = next_id
        .checked_add(1)
        .ok_or(FrontendJsonError::Unsupported)?;
    let callee_id = next_id
        .checked_add(2)
        .ok_or(FrontendJsonError::Unsupported)?;
    let conversion_id = next_id
        .checked_add(3)
        .ok_or(FrontendJsonError::Unsupported)?;
    let load_id = next_id
        .checked_add(4)
        .ok_or(FrontendJsonError::Unsupported)?;
    let reference_id = next_id
        .checked_add(5)
        .ok_or(FrontendJsonError::Unsupported)?;
    let return_id = next_id
        .checked_add(6)
        .ok_or(FrontendJsonError::Unsupported)?;
    let [call, cast, callee, conversion, load, reference, rest @ ..] =
        remainder
    else {
        return Err(FrontendJsonError::Unsupported);
    };
    let returned = match rest {
        [] => None,
        [last]
            if correct_node(last, return_id, 2, "return-statement")
                && clean(last) =>
        {
            Some(last)
        },
        _ => return Err(FrontendJsonError::Unsupported),
    };
    let byte = definitions
        .last()
        .map(|(_node, value)| *value)
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
        || !correct_node(call, next_id, 2, "call-expression")
        || call.type_name.as_deref() != Some("i32")
        || call.reference.as_deref() != Some("external:putchar")
        || !correct_node(cast, cast_id, next_id, "cast-expression")
        || cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
        || cast.operation.as_deref() != Some("function-to-pointer")
        || !correct_node(
            callee,
            callee_id,
            cast_id,
            "declaration-reference-expression",
        )
        || callee.type_name.as_deref() != Some("fn(i32)->i32")
        || callee.reference.as_deref() != Some("external:putchar")
        || !correct_node(conversion, conversion_id, next_id, "cast-expression")
        || conversion.type_name.as_deref() != Some("i32")
        || conversion.operation.as_deref() != Some("integral-cast")
        || !correct_node(load, load_id, conversion_id, "cast-expression")
        || load.type_name.as_deref() != Some("u32")
        || load.operation.as_deref() != Some("lvalue-to-rvalue")
        || !correct_node(
            reference,
            reference_id,
            load_id,
            "declaration-reference-expression",
        )
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
                    && (node.id == next_id
                        || node.id == callee_id
                        || node.id == reference_id
                        || node.reference.is_none())
                    && (node.id == cast_id
                        || node.id == conversion_id
                        || node.id == load_id
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
        || last_end > call.span.begin.byte
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
    let live_source = definitions
        .last()
        .map(|(source, _value)| *source)
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    let instructions = vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(8, vec![byte]),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            typed_span(&live_source.span),
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
