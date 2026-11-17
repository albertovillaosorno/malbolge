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
//   - Source-proven unsigned local constant update with signed getchar input.
// - Must-Not:
//   - Fold a live getchar into a byte, discard effects, or infer dynamic state.
// - Allows:
//   - Inputs: exact C23 declaration, one signed read, checked += and output.
//   - Outputs: independently re-admitted signed Getchar and byte output IR.
//   - Side effects: none.
// - Split-When:
//   - General source-C local SSA lowering supports mutable input-dependent
//     data.
// - Merge-When:
//   - Complete EOF-checksum source lowering supersedes the closed proof.
// - Summary:
//   - Reuses guest mixed-effect emission after source-bound local propagation.

//! One complete, closed Clang/source C expression path to a live guest effect.

use super::signed_input_literal::{
    emit_signed_input_literal, node_is, source_slice,
};
use super::{
    Artifact, CanonicalGuestProjection, FrontendJsonError, Node,
    StorageDuration,
};

fn local_name(node: &Node, type_name: &str, prefix: &str) -> Option<String> {
    let name = node.name.as_deref()?;
    if name.is_empty()
        || !name
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
        || !name.as_bytes()[0].is_ascii_alphabetic()
        || node.kind != "variable-declaration"
        || node.type_name.as_deref() != Some(type_name)
        || node.parent == 0
        || node.definition.as_deref() != Some("definition")
        || node.linkage.as_deref() != Some("none")
        || node.storage_class.as_deref() != Some("none")
        || !matches!(node.storage_duration, Some(StorageDuration::Automatic))
        || node.inline_specified.is_some()
        || node.operation.is_some()
        || node.literal.is_some()
        || node.constant_integer.is_some()
    {
        return None;
    }
    let expected = format!("{prefix}{name}");
    let reference = format!(
        "{name}@{}",
        node.span
            .begin
            .byte
            .checked_add(u32::try_from(prefix.len()).ok()?)?
    );
    (node.reference.as_deref() == Some(reference.as_str())
        && node.span.end.byte > node.span.begin.byte
        && expected.len() < 128)
        .then_some(name.to_owned())
}

/// Authenticate one actual Clang+source C mutation and preserve getchar.
///
/// # Errors
///
/// Rejects every unrecognized effect, spelling, span, tree, and target drift.
#[expect(
    clippy::too_many_lines,
    reason = "all nineteen Clang nodes are checked together with their source"
)]
pub(super) fn canonical_mutable_input_literal(
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
        initial_decl,
        checksum,
        zero,
        input_decl,
        current,
        read,
        read_decay,
        read_callee,
        increment,
        assigned,
        delta,
        write,
        write_decay,
        write_callee,
        integral_cast,
        value_cast,
        value_ref,
    ] = input.nodes.as_slice()
    else {
        return Err(FrontendJsonError::Unsupported);
    };
    let checksum_name = local_name(checksum, "u32", "unsigned ")
        .ok_or(FrontendJsonError::Unsupported)?;
    let current_name = local_name(current, "i32", "int ")
        .ok_or(FrontendJsonError::Unsupported)?;
    if checksum_name == current_name {
        return Err(FrontendJsonError::Unsupported);
    }
    let checksum_symbol = checksum.reference.as_deref();
    let current_symbol = current.reference.as_deref();
    let decimal = delta
        .constant_integer
        .as_deref()
        .ok_or(FrontendJsonError::Unsupported)?;
    let byte = decimal
        .parse::<u8>()
        .map_err(|_error| FrontendJsonError::Unsupported)?;
    // Authenticate the complete C statements, not just isolated AST tokens.
    // A single signed getchar is an effect; its value never enters arithmetic.
    let expected_body = format!(
        concat!(
            "{{\n    unsigned {checksum_name} = 0U;\n",
            "    int {current_name} = getchar();\n",
            "    {checksum_name} += {decimal}U;\n",
            "    putchar((int){checksum_name});\n}}",
        ),
        checksum_name = checksum_name,
        current_name = current_name,
        decimal = decimal
    );
    let good = function.id == 1
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
        && node_is(
            initial_decl,
            3,
            2,
            "declaration-statement",
            None,
            None,
            None,
        )
        && checksum.id == 4
        && checksum.parent == 3
        && node_is(zero, 5, 4, "integer-literal", Some("u32"), None, None)
        && zero.constant_integer.as_deref() == Some("0")
        && zero.literal.as_deref() == Some("0")
        && node_is(input_decl, 6, 2, "declaration-statement", None, None, None)
        && current.id == 7
        && current.parent == 6
        && node_is(
            read,
            8,
            7,
            "call-expression",
            Some("i32"),
            Some("external:getchar"),
            None,
        )
        && node_is(
            read_decay,
            9,
            8,
            "cast-expression",
            Some("ptr(fn()->i32)"),
            None,
            Some("function-to-pointer"),
        )
        && node_is(
            read_callee,
            10,
            9,
            "declaration-reference-expression",
            Some("fn()->i32"),
            Some("external:getchar"),
            None,
        )
        && node_is(
            increment,
            11,
            2,
            "compound-assignment-expression",
            Some("u32"),
            None,
            Some("+="),
        )
        && node_is(
            assigned,
            12,
            11,
            "declaration-reference-expression",
            Some("u32"),
            checksum_symbol,
            None,
        )
        && node_is(delta, 13, 11, "integer-literal", Some("u32"), None, None)
        && delta.literal.as_deref() == Some(decimal)
        && node_is(
            write,
            14,
            2,
            "call-expression",
            Some("i32"),
            Some("external:putchar"),
            None,
        )
        && node_is(
            write_decay,
            15,
            14,
            "cast-expression",
            Some("ptr(fn(i32)->i32)"),
            None,
            Some("function-to-pointer"),
        )
        && node_is(
            write_callee,
            16,
            15,
            "declaration-reference-expression",
            Some("fn(i32)->i32"),
            Some("external:putchar"),
            None,
        )
        && node_is(
            integral_cast,
            17,
            14,
            "cast-expression",
            Some("i32"),
            None,
            Some("integral-cast"),
        )
        && node_is(
            value_cast,
            18,
            17,
            "cast-expression",
            Some("u32"),
            None,
            Some("lvalue-to-rvalue"),
        )
        && node_is(
            value_ref,
            19,
            18,
            "declaration-reference-expression",
            Some("u32"),
            checksum_symbol,
            None,
        )
        && current_symbol.is_some()
        && body.id == 2
        && body.parent == 1
        && body.kind == "compound-statement"
        && body.span.end == function.span.end
        && body.span.begin.byte > function.span.begin.byte
        && body.name.is_none()
        && body.type_name.is_none()
        && body.reference.is_none()
        && body.operation.is_none()
        && source_slice(source, body) == Some(expected_body.as_bytes())
        && source_slice(source, initial_decl)
            == Some(format!("unsigned {checksum_name} = 0U;").as_bytes())
        && source_slice(source, checksum)
            == Some(format!("unsigned {checksum_name} = 0U").as_bytes())
        && source_slice(source, zero) == Some(b"0U")
        && source_slice(source, input_decl)
            == Some(format!("int {current_name} = getchar();").as_bytes())
        && source_slice(source, current)
            == Some(format!("int {current_name} = getchar()").as_bytes())
        && source_slice(source, read) == Some(b"getchar()")
        && source_slice(source, read_decay) == Some(b"getchar")
        && read_decay.span == read_callee.span
        && source_slice(source, assigned) == Some(checksum_name.as_bytes())
        && source_slice(source, increment)
            == Some(format!("{checksum_name} += {decimal}U").as_bytes())
        && source_slice(source, delta)
            == Some(format!("{decimal}U").as_bytes())
        && source_slice(source, write)
            == Some(format!("putchar((int){checksum_name})").as_bytes())
        && source_slice(source, write_decay) == Some(b"putchar")
        && write_decay.span == write_callee.span
        && source_slice(source, integral_cast)
            == Some(format!("(int){checksum_name}").as_bytes())
        && source_slice(source, value_cast) == Some(checksum_name.as_bytes())
        && value_cast.span == value_ref.span
        && source_slice(source, value_ref) == Some(checksum_name.as_bytes())
        && initial_decl.span.end.byte < input_decl.span.begin.byte
        && input_decl.span.end.byte < increment.span.begin.byte
        && increment.span.end.byte < write.span.begin.byte
        && write.span.end.byte < body.span.end.byte
        && function.span.begin.byte < body.span.begin.byte;
    if !good {
        return Err(FrontendJsonError::Unsupported);
    }
    emit_signed_input_literal(
        &input,
        function,
        body,
        &[read],
        delta,
        write,
        byte,
    )
}
