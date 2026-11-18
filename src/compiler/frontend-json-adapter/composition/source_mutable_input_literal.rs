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
//   - Source-proven ordered unsigned local constant updates with signed
//     getchar.
// - Must-Not:
//   - Fold a live getchar into a byte, discard effects, or infer dynamic state.
// - Allows:
//   - Inputs: source-exact C23 locals, signed read and 1-2 checked updates.
//   - Outputs: independently re-admitted signed Getchar and byte output IR.
//   - Side effects: none.
// - Split-When:
//   - General source-C local SSA lowering supports mutable input-dependent
//     data.
// - Merge-When:
//   - Complete EOF-checksum source lowering supersedes the closed proof.
// - Summary:
//   - Constant-folds ordered local updates after source-authenticated input.

//! Bounded source-authenticated mutable constant flow and live signed input.

use super::signed_input_literal::{
    emit_signed_input_literal, node_is, source_slice,
};
use super::{
    Artifact, CanonicalGuestProjection, FrontendJsonError, Node,
    StorageDuration,
};

const MAX_UNSIGNED_UPDATES: usize = 2;

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

/// Authenticate the entire local operation trace from pinned Clang and source.
///
/// The signed getchar is always emitted as a real guest effect, but its
/// unused result cannot influence the independent unsigned accumulator.
/// This is constant propagation, not guest execution of arithmetic or
/// support for dynamic mutable storage.
///
/// # Errors
///
/// Refuses any unrecognized effect, spelling, span, tree or target drift.
#[expect(
    clippy::too_many_lines,
    reason = "complete source/Clang proof must reject all extra effects"
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
        initial_value,
        input_decl,
        current,
        read,
        read_decay,
        read_callee,
        remaining @ ..,
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
    let initial_decimal = initial_value
        .constant_integer
        .as_deref()
        .ok_or(FrontendJsonError::Unsupported)?;
    let mut result = initial_decimal
        .parse::<u32>()
        .map_err(|_error| FrontendJsonError::Unsupported)?;
    let mut expected_body = format!(
        concat!(
            "{{\n    unsigned {checksum_name} = {initial_decimal}U;\n",
            "    int {current_name} = getchar();\n",
        ),
        checksum_name = checksum_name,
        initial_decimal = initial_decimal,
        current_name = current_name
    );
    let mut last_end = input_decl.span.end.byte;
    let mut last_literal = initial_value;
    let mut read_calls = vec![read];
    let mut update_count = 0_usize;
    let mut next_id = 11_u32;
    let mut remaining = remaining;
    // Pure, unobserved accumulator changes may cross an input effect;
    // two actual signed guest reads must retain their source order.
    while remaining.len() > 6 {
        if remaining[0].kind == "declaration-statement" && read_calls.len() == 1
        {
            let Some((group, rest)) = remaining.split_first_chunk::<5>() else {
                return Err(FrontendJsonError::Unsupported);
            };
            let [declaration, local, second_read, second_decay, second_callee] =
                group;
            let second_name = local_name(local, "i32", "int ")
                .ok_or(FrontendJsonError::Unsupported)?;
            let spelling = format!("int {second_name} = getchar()");
            if second_name == checksum_name
                || second_name == current_name
                || !node_is(
                    declaration,
                    next_id,
                    2,
                    "declaration-statement",
                    None,
                    None,
                    None,
                )
                || local.id != next_id + 1
                || local.parent != next_id
                || !node_is(
                    second_read,
                    next_id + 2,
                    next_id + 1,
                    "call-expression",
                    Some("i32"),
                    Some("external:getchar"),
                    None,
                )
                || !node_is(
                    second_decay,
                    next_id + 3,
                    next_id + 2,
                    "cast-expression",
                    Some("ptr(fn()->i32)"),
                    None,
                    Some("function-to-pointer"),
                )
                || !node_is(
                    second_callee,
                    next_id + 4,
                    next_id + 3,
                    "declaration-reference-expression",
                    Some("fn()->i32"),
                    Some("external:getchar"),
                    None,
                )
                || source_slice(source, declaration)
                    != Some(format!("{spelling};").as_bytes())
                || source_slice(source, local) != Some(spelling.as_bytes())
                || source_slice(source, second_read) != Some(b"getchar()")
                || source_slice(source, second_decay) != Some(b"getchar")
                || second_decay.span != second_callee.span
                || last_end >= declaration.span.begin.byte
            {
                return Err(FrontendJsonError::Unsupported);
            }
            expected_body.push_str(&format!("    {spelling};\n"));
            read_calls.push(second_read);
            last_end = declaration.span.end.byte;
            remaining = rest;
            next_id += 5;
            continue;
        }
        if update_count >= MAX_UNSIGNED_UPDATES {
            return Err(FrontendJsonError::Unsupported);
        }
        let Some((nodes, rest)) = remaining.split_first_chunk::<3>() else {
            return Err(FrontendJsonError::Unsupported);
        };
        let [update, assigned, delta] = nodes;
        if update.kind != "compound-assignment-expression" {
            return Err(FrontendJsonError::Unsupported);
        }
        let id = next_id;
        let operator = update
            .operation
            .as_deref()
            .ok_or(FrontendJsonError::Unsupported)?;
        let decimal = delta
            .constant_integer
            .as_deref()
            .ok_or(FrontendJsonError::Unsupported)?;
        let operand = decimal
            .parse::<u32>()
            .map_err(|_error| FrontendJsonError::Unsupported)?;
        // Both operators are defined on u32, including wrapping addition.
        result = match operator {
            "+=" => result.wrapping_add(operand),
            "^=" => result ^ operand,
            _ => return Err(FrontendJsonError::Unsupported),
        };
        if !node_is(
            update,
            id,
            2,
            "compound-assignment-expression",
            Some("u32"),
            None,
            Some(operator),
        ) || !node_is(
            assigned,
            id + 1,
            id,
            "declaration-reference-expression",
            Some("u32"),
            checksum_symbol,
            None,
        ) || !node_is(
            delta,
            id + 2,
            id,
            "integer-literal",
            Some("u32"),
            None,
            None,
        ) || delta.literal.as_deref() != Some(decimal)
            || source_slice(source, update)
                != Some(
                    format!("{checksum_name} {operator} {decimal}U").as_bytes(),
                )
            || source_slice(source, assigned) != Some(checksum_name.as_bytes())
            || source_slice(source, delta)
                != Some(format!("{decimal}U").as_bytes())
            || last_end >= update.span.begin.byte
        {
            return Err(FrontendJsonError::Unsupported);
        }
        expected_body
            .push_str(&format!("    {checksum_name} {operator} {decimal}U;\n"));
        last_end = update.span.end.byte;
        last_literal = delta;
        next_id += 3;
        update_count += 1;
        remaining = rest;
    }
    // Source spans of typed instructions must remain in effect order.
    if update_count == 0
        || last_literal.span.begin.byte
            < read_calls[read_calls.len() - 1].span.end.byte
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // Do not project an out-of-range integer through a guest byte.
    // That would collapse an otherwise observable C conversion distinction.
    let byte = u8::try_from(result)
        .map_err(|_error| FrontendJsonError::Unsupported)?;
    expected_body.push_str(&format!("    putchar((int){checksum_name});\n}}"));
    let [
        write,
        write_decay,
        write_callee,
        integral_cast,
        value_cast,
        value_ref,
    ] = remaining
    else {
        return Err(FrontendJsonError::Unsupported);
    };
    let write_id = next_id;
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
        && node_is(
            initial_value,
            5,
            4,
            "integer-literal",
            Some("u32"),
            None,
            None,
        )
        && initial_value.literal.as_deref() == Some(initial_decimal)
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
            write,
            write_id,
            2,
            "call-expression",
            Some("i32"),
            Some("external:putchar"),
            None,
        )
        && node_is(
            write_decay,
            write_id + 1,
            write_id,
            "cast-expression",
            Some("ptr(fn(i32)->i32)"),
            None,
            Some("function-to-pointer"),
        )
        && node_is(
            write_callee,
            write_id + 2,
            write_id + 1,
            "declaration-reference-expression",
            Some("fn(i32)->i32"),
            Some("external:putchar"),
            None,
        )
        && node_is(
            integral_cast,
            write_id + 3,
            write_id,
            "cast-expression",
            Some("i32"),
            None,
            Some("integral-cast"),
        )
        && node_is(
            value_cast,
            write_id + 4,
            write_id + 3,
            "cast-expression",
            Some("u32"),
            None,
            Some("lvalue-to-rvalue"),
        )
        && node_is(
            value_ref,
            write_id + 5,
            write_id + 4,
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
            == Some(
                format!("unsigned {checksum_name} = {initial_decimal}U;")
                    .as_bytes(),
            )
        && source_slice(source, checksum)
            == Some(
                format!("unsigned {checksum_name} = {initial_decimal}U")
                    .as_bytes(),
            )
        && source_slice(source, initial_value)
            == Some(format!("{initial_decimal}U").as_bytes())
        && source_slice(source, input_decl)
            == Some(format!("int {current_name} = getchar();").as_bytes())
        && source_slice(source, current)
            == Some(format!("int {current_name} = getchar()").as_bytes())
        && source_slice(source, read) == Some(b"getchar()")
        && source_slice(source, read_decay) == Some(b"getchar")
        && read_decay.span == read_callee.span
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
        && last_end < write.span.begin.byte
        && write.span.end.byte < body.span.end.byte
        && function.span.begin.byte < body.span.begin.byte;
    if !good {
        return Err(FrontendJsonError::Unsupported);
    }
    emit_signed_input_literal(
        &input,
        function,
        body,
        &read_calls,
        last_literal,
        write,
        byte,
    )
}
