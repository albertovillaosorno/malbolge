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
//   - Source- and Clang-authenticated reflexive signed-input branch folding.
// - Must-Not:
//   - Substitute host stdin, discard input, or evaluate live guest operands.
// - Allows:
//   - Inputs: one signed getchar and exact zero-identity C23 if/else.
//   - Outputs: one source-proved byte through the existing real guest bridge.
//   - Side effects: none.
// - Split-When:
//   - General signed C CFG lowering replaces this closed source proof.
// - Merge-When:
//   - Mutable EOF checksum runs with runtime guest control and storage.
// - Summary:
//   - Same-SSA subtraction/XOR is zero for all i32 values including EOF.

//! A closed, signed-EOF-safe guard proof, not dynamic guest branching.

use super::signed_input_literal::{
    emit_signed_input_literal, node_is, source_slice,
};
use super::source_mutable_input_literal::local_name;
use super::{Artifact, CanonicalGuestProjection, FrontendJsonError, Node};

fn decimal_byte(node: &Node, source: &[u8]) -> Option<u8> {
    let digits = source_slice(source, node)?;
    if digits.is_empty()
        || (digits.len() > 1 && digits[0] == b'0')
        || !digits.iter().all(u8::is_ascii_digit)
    {
        return None;
    }
    let decimal = str::from_utf8(digits).ok()?;
    let byte = decimal.parse::<u8>().ok()?;
    (node.literal.as_deref() == Some(decimal)
        && node.constant_integer.as_deref() == Some(decimal))
    .then_some(byte)
}

fn output_arm(
    source: &[u8],
    nodes: [&Node; 5],
    body_id: u32,
    write_id: u32,
) -> Option<u8> {
    let [body, write, decay, callee, literal] = nodes;
    let byte = decimal_byte(literal, source)?;
    let decimal = byte.to_string();
    (node_is(
        write,
        write_id,
        body_id,
        "call-expression",
        Some("i32"),
        Some("external:putchar"),
        None,
    ) && node_is(
        decay,
        write_id + 1,
        write_id,
        "cast-expression",
        Some("ptr(fn(i32)->i32)"),
        None,
        Some("function-to-pointer"),
    ) && node_is(
        callee,
        write_id + 2,
        write_id + 1,
        "declaration-reference-expression",
        Some("fn(i32)->i32"),
        Some("external:putchar"),
        None,
    ) && node_is(
        literal,
        write_id + 3,
        write_id,
        "integer-literal",
        Some("i32"),
        None,
        None,
    ))
    .then_some(byte)
    .filter(|_| {
        body.id == body_id
            && body.parent == 8
            && body.kind == "compound-statement"
            && body.name.is_none()
            && body.type_name.is_none()
            && body.reference.is_none()
            && body.operation.is_none()
            && body.definition.is_none()
            && body.literal.is_none()
            && body.constant_integer.is_none()
            && body.span.begin.byte < write.span.begin.byte
            && write.span.end.byte < body.span.end.byte
            && write.span.begin == decay.span.begin
            && decay.span == callee.span
            && source_slice(source, decay) == Some(b"putchar")
            && source_slice(source, literal) == Some(decimal.as_bytes())
            && source_slice(source, write)
                == Some(format!("putchar({decimal})").as_bytes())
            && source_slice(source, body)
                == Some(
                    format!("{{\n        putchar({decimal});\n    }}")
                        .as_bytes(),
                )
    })
}

/// Recognize a complete source and normalized C23 AST with a live signed
/// `getchar` and an exact same-SSA subtraction/XOR zero guard.
///
/// Both operands are the very same local and no state mutation intervenes;
/// `x - x` and `x ^ x` are zero for every i32, including `EOF == -1`.
/// The chosen arm is a *source-time* mathematical proof, while the input
/// remains a real, ordered guest effect. No other source effects are dropped.
///
/// # Errors
///
/// Rejects unrecognized source, Clang tree, live guard, or conversion.
#[expect(
    clippy::too_many_lines,
    reason = "closed full-source and AST admission"
)]
pub(super) fn canonical_signed_guarded_output(
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
        declaration,
        current,
        read,
        read_decay,
        read_callee,
        guard,
        compare,
        grouped,
        arithmetic,
        left_cast,
        left_ref,
        right_cast,
        right_ref,
        zero,
        true_body,
        true_write,
        true_decay,
        true_callee,
        true_literal,
        false_body,
        false_write,
        false_decay,
        false_callee,
        false_literal,
    ] = input.nodes.as_slice()
    else {
        return Err(FrontendJsonError::Unsupported);
    };
    let name = local_name(current, "i32", "int ")
        .ok_or(FrontendJsonError::Unsupported)?;
    let symbol = current.reference.as_deref();
    let operator = arithmetic
        .operation
        .as_deref()
        .filter(|operation| matches!(*operation, "-" | "^"))
        .ok_or(FrontendJsonError::Unsupported)?;
    let comparison = compare
        .operation
        .as_deref()
        .filter(|operation| matches!(*operation, "==" | "!="))
        .ok_or(FrontendJsonError::Unsupported)?;
    let true_byte = output_arm(
        source,
        [true_body, true_write, true_decay, true_callee, true_literal],
        17,
        18,
    )
    .ok_or(FrontendJsonError::Unsupported)?;
    let false_byte = output_arm(
        source,
        [
            false_body,
            false_write,
            false_decay,
            false_callee,
            false_literal,
        ],
        22,
        23,
    )
    .ok_or(FrontendJsonError::Unsupported)?;
    let selected = if comparison == "==" {
        (true_write, true_literal, true_byte)
    } else {
        (false_write, false_literal, false_byte)
    };
    let expected_body = format!(
        concat!(
            "{{\n    int {name} = getchar();\n",
            "    if (({name} {operator} {name}) {comparison} 0) {{\n",
            "        putchar({true_byte});\n",
            "    }} else {{\n",
            "        putchar({false_byte});\n",
            "    }}\n}}",
        ),
        name = name,
        operator = operator,
        comparison = comparison,
        true_byte = true_byte,
        false_byte = false_byte,
    );
    let function_good = function.id == 1
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
        && function.span.begin.byte < body.span.begin.byte
        && function.span.end == body.span.end;
    let good = function_good
        && body.id == 2
        && body.parent == 1
        && body.kind == "compound-statement"
        && body.name.is_none()
        && body.type_name.is_none()
        && body.reference.is_none()
        && body.operation.is_none()
        && body.span.begin.byte < declaration.span.begin.byte
        && source_slice(source, function)
            == Some(format!("void emit(void) {expected_body}").as_bytes())
        && source_slice(source, body) == Some(expected_body.as_bytes())
        && node_is(
            declaration,
            3,
            2,
            "declaration-statement",
            None,
            None,
            None,
        )
        && current.id == 4
        && current.parent == 3
        && node_is(
            read,
            5,
            4,
            "call-expression",
            Some("i32"),
            Some("external:getchar"),
            None,
        )
        && node_is(
            read_decay,
            6,
            5,
            "cast-expression",
            Some("ptr(fn()->i32)"),
            None,
            Some("function-to-pointer"),
        )
        && node_is(
            read_callee,
            7,
            6,
            "declaration-reference-expression",
            Some("fn()->i32"),
            Some("external:getchar"),
            None,
        )
        && source_slice(source, declaration)
            == Some(format!("int {name} = getchar();").as_bytes())
        && source_slice(source, current)
            == Some(format!("int {name} = getchar()").as_bytes())
        && source_slice(source, read) == Some(b"getchar()")
        && source_slice(source, read_decay) == Some(b"getchar")
        && read_decay.span == read_callee.span
        && guard.id == 8
        && guard.parent == 2
        && guard.kind == "if-statement"
        && guard.type_name.is_none()
        && guard.operation.is_none()
        && guard.reference.is_none()
        && node_is(
            compare,
            9,
            8,
            "binary-expression",
            Some("i32"),
            None,
            Some(comparison),
        )
        && node_is(
            grouped,
            10,
            9,
            "parenthesized-expression",
            Some("i32"),
            None,
            None,
        )
        && node_is(
            arithmetic,
            11,
            10,
            "binary-expression",
            Some("i32"),
            None,
            Some(operator),
        )
        && node_is(
            left_cast,
            12,
            11,
            "cast-expression",
            Some("i32"),
            None,
            Some("lvalue-to-rvalue"),
        )
        && node_is(
            left_ref,
            13,
            12,
            "declaration-reference-expression",
            Some("i32"),
            symbol,
            None,
        )
        && node_is(
            right_cast,
            14,
            11,
            "cast-expression",
            Some("i32"),
            None,
            Some("lvalue-to-rvalue"),
        )
        && node_is(
            right_ref,
            15,
            14,
            "declaration-reference-expression",
            Some("i32"),
            symbol,
            None,
        )
        && node_is(zero, 16, 9, "integer-literal", Some("i32"), None, None)
        && zero.constant_integer.as_deref() == Some("0")
        && zero.literal.as_deref() == Some("0")
        && source_slice(source, zero) == Some(b"0")
        && left_cast.span == left_ref.span
        && right_cast.span == right_ref.span
        && source_slice(source, left_ref) == Some(name.as_bytes())
        && source_slice(source, right_ref) == Some(name.as_bytes())
        && source_slice(source, grouped)
            == Some(format!("({name} {operator} {name})").as_bytes())
        && source_slice(source, arithmetic)
            == Some(format!("{name} {operator} {name}").as_bytes())
        && source_slice(source, compare)
            == Some(
                format!("({name} {operator} {name}) {comparison} 0").as_bytes(),
            )
        && declaration.span.end.byte < guard.span.begin.byte
        && guard.span.begin.byte < true_body.span.begin.byte
        && true_body.span.end.byte < false_body.span.begin.byte
        && false_body.span.end == guard.span.end;
    if !good {
        return Err(FrontendJsonError::Unsupported);
    }
    emit_signed_input_literal(
        &input,
        function,
        body,
        &[read],
        selected.1,
        selected.0,
        selected.2,
    )
}
