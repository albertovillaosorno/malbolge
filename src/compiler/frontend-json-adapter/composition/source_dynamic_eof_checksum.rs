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
//   - Source-locked, effectful EOF-checksum typed CFG experiment.
// - Must-Not:
//   - Publish a guest without verified layout or replace EOF with byte input.
// - Allows:
//   - Inputs: frozen whole C23 checksum and exact pinned Clang subtree.
//   - Outputs: canonical typed SSA with EOF branches, mutable phi and C I/O.
//   - Side effects: none.
// - Split-When:
//   - General source C CFG lowering supersedes this bounded first witness.
// - Merge-When:
//   - Native typed source CFG lowering implements the same semantic contract.
// - Summary:
//   - Proves source and normalized tree before building dynamic checksum IR.

//! First complete mutable EOF checksum at the typed-CFG boundary.
//! The positional proof is intentionally narrow; no guest artifact is implied.

use super::typed::{
    BasicBlock, BasicBlockSpec, BinaryOp, BlockId, CastOp, CompareOp,
    FrontendArtifact, FrontendArtifactSpec,
    FrontendFallthroughVoidFunctionSpec, FrontendReturnVoidFunction, Function,
    FunctionSpec, Instruction, IntegerConstant, LocatedInstruction, Module,
    ModuleSpec, Phi, PhiIncoming, Terminator, TypeDef, TypeEntry, TypeId,
    ValueId,
};
use super::{
    Artifact, FrontendJsonError, Node, canonical_bytes, canonical_module,
    lower_frontend_artifact, source_digest, typed_span,
};

const FROZEN_SHA256: &str =
    "9ae147a9d0e824bafb9322ee4787cdc8a7f45cb84c3f8691ad74f9eef32553c7";

// The AST preorder and byte-relative spans are the pinned Clang 22.1.8 C23
// witness. Any extra node, hidden effect, changed operator or forged reference
// must fail rather than silently disappear from the typed effect trace.
struct NodeShape {
    parent: u32,
    kind: Option<&'static str>,
    ty: Option<&'static str>,
    op: Option<&'static str>,
    reference: Option<&'static str>,
    literal: Option<&'static str>,
    constant: Option<&'static str>,
    start: u32,
    end: u32,
}

const SHAPES: &[NodeShape] = &[
    NodeShape {
        parent: 0,
        kind: Some("function-declaration"),
        ty: Some("fn()->void"),
        op: None,
        reference: None,
        literal: None,
        constant: None,
        start: 0,
        end: 358,
    },
    NodeShape {
        parent: 1,
        kind: Some("compound-statement"),
        ty: None,
        op: None,
        reference: None,
        literal: None,
        constant: None,
        start: 16,
        end: 358,
    },
    NodeShape {
        parent: 2,
        kind: Some("declaration-statement"),
        ty: None,
        op: None,
        reference: None,
        literal: None,
        constant: None,
        start: 22,
        end: 45,
    },
    NodeShape {
        parent: 3,
        kind: Some("variable-declaration"),
        ty: Some("u32"),
        op: None,
        reference: Some("checksum@885"),
        literal: None,
        constant: None,
        start: 22,
        end: 44,
    },
    NodeShape {
        parent: 4,
        kind: Some("integer-literal"),
        ty: Some("u32"),
        op: None,
        reference: None,
        literal: Some("0"),
        constant: Some("0"),
        start: 42,
        end: 44,
    },
    NodeShape {
        parent: 2,
        kind: Some("declaration-statement"),
        ty: None,
        op: None,
        reference: None,
        literal: None,
        constant: None,
        start: 50,
        end: 74,
    },
    NodeShape {
        parent: 6,
        kind: Some("variable-declaration"),
        ty: Some("i32"),
        op: None,
        reference: Some("current@908"),
        literal: None,
        constant: None,
        start: 50,
        end: 73,
    },
    NodeShape {
        parent: 7,
        kind: Some("call-expression"),
        ty: Some("i32"),
        op: None,
        reference: Some("external:getchar"),
        literal: None,
        constant: None,
        start: 64,
        end: 73,
    },
    NodeShape {
        parent: 8,
        kind: Some("cast-expression"),
        ty: Some("ptr(fn()->i32)"),
        op: Some("function-to-pointer"),
        reference: None,
        literal: None,
        constant: None,
        start: 64,
        end: 71,
    },
    NodeShape {
        parent: 9,
        kind: Some("declaration-reference-expression"),
        ty: Some("fn()->i32"),
        op: None,
        reference: Some("external:getchar"),
        literal: None,
        constant: None,
        start: 64,
        end: 71,
    },
    NodeShape {
        parent: 2,
        kind: Some("while-statement"),
        ty: None,
        op: None,
        reference: None,
        literal: None,
        constant: None,
        start: 79,
        end: 328,
    },
    NodeShape {
        parent: 11,
        kind: Some("binary-expression"),
        ty: Some("i32"),
        op: Some("!="),
        reference: None,
        literal: None,
        constant: None,
        start: 86,
        end: 100,
    },
    NodeShape {
        parent: 12,
        kind: Some("cast-expression"),
        ty: Some("i32"),
        op: Some("lvalue-to-rvalue"),
        reference: None,
        literal: None,
        constant: None,
        start: 86,
        end: 93,
    },
    NodeShape {
        parent: 13,
        kind: Some("declaration-reference-expression"),
        ty: Some("i32"),
        op: None,
        reference: Some("current@908"),
        literal: None,
        constant: None,
        start: 86,
        end: 93,
    },
    NodeShape {
        parent: 12,
        kind: Some("parenthesized-expression"),
        ty: Some("i32"),
        op: None,
        reference: None,
        literal: None,
        constant: Some("-1"),
        start: 97,
        end: 100,
    },
    NodeShape {
        parent: 15,
        kind: Some("unary-expression"),
        ty: Some("i32"),
        op: Some("-"),
        reference: None,
        literal: None,
        constant: Some("-1"),
        start: 97,
        end: 100,
    },
    NodeShape {
        parent: 16,
        kind: Some("integer-literal"),
        ty: Some("i32"),
        op: None,
        reference: None,
        literal: Some("1"),
        constant: Some("1"),
        start: 97,
        end: 100,
    },
    NodeShape {
        parent: 11,
        kind: Some("compound-statement"),
        ty: None,
        op: None,
        reference: None,
        literal: None,
        constant: None,
        start: 102,
        end: 328,
    },
    NodeShape {
        parent: 18,
        kind: Some("if-statement"),
        ty: None,
        op: None,
        reference: None,
        literal: None,
        constant: None,
        start: 112,
        end: 250,
    },
    NodeShape {
        parent: 19,
        kind: Some("binary-expression"),
        ty: Some("i32"),
        op: Some("!="),
        reference: None,
        literal: None,
        constant: None,
        start: 116,
        end: 134,
    },
    NodeShape {
        parent: 20,
        kind: Some("parenthesized-expression"),
        ty: Some("i32"),
        op: None,
        reference: None,
        literal: None,
        constant: None,
        start: 116,
        end: 129,
    },
    NodeShape {
        parent: 21,
        kind: Some("binary-expression"),
        ty: Some("i32"),
        op: Some("&"),
        reference: None,
        literal: None,
        constant: None,
        start: 117,
        end: 128,
    },
    NodeShape {
        parent: 22,
        kind: Some("cast-expression"),
        ty: Some("i32"),
        op: Some("lvalue-to-rvalue"),
        reference: None,
        literal: None,
        constant: None,
        start: 117,
        end: 124,
    },
    NodeShape {
        parent: 23,
        kind: Some("declaration-reference-expression"),
        ty: Some("i32"),
        op: None,
        reference: Some("current@908"),
        literal: None,
        constant: None,
        start: 117,
        end: 124,
    },
    NodeShape {
        parent: 22,
        kind: Some("integer-literal"),
        ty: Some("i32"),
        op: None,
        reference: None,
        literal: Some("1"),
        constant: Some("1"),
        start: 127,
        end: 128,
    },
    NodeShape {
        parent: 20,
        kind: Some("integer-literal"),
        ty: Some("i32"),
        op: None,
        reference: None,
        literal: Some("0"),
        constant: Some("0"),
        start: 133,
        end: 134,
    },
    NodeShape {
        parent: 19,
        kind: Some("compound-statement"),
        ty: None,
        op: None,
        reference: None,
        literal: None,
        constant: None,
        start: 136,
        end: 190,
    },
    NodeShape {
        parent: 27,
        kind: Some("compound-assignment-expression"),
        ty: Some("u32"),
        op: Some("^="),
        reference: None,
        literal: None,
        constant: None,
        start: 150,
        end: 179,
    },
    NodeShape {
        parent: 28,
        kind: Some("declaration-reference-expression"),
        ty: Some("u32"),
        op: None,
        reference: Some("checksum@885"),
        literal: None,
        constant: None,
        start: 150,
        end: 158,
    },
    NodeShape {
        parent: 28,
        kind: Some("cast-expression"),
        ty: Some("u32"),
        op: Some("integral-cast"),
        reference: None,
        literal: None,
        constant: None,
        start: 162,
        end: 179,
    },
    NodeShape {
        parent: 30,
        kind: Some("cast-expression"),
        ty: Some("i32"),
        op: Some("lvalue-to-rvalue"),
        reference: None,
        literal: None,
        constant: None,
        start: 172,
        end: 179,
    },
    NodeShape {
        parent: 31,
        kind: Some("declaration-reference-expression"),
        ty: Some("i32"),
        op: None,
        reference: Some("current@908"),
        literal: None,
        constant: None,
        start: 172,
        end: 179,
    },
    NodeShape {
        parent: 19,
        kind: Some("compound-statement"),
        ty: None,
        op: None,
        reference: None,
        literal: None,
        constant: None,
        start: 196,
        end: 250,
    },
    NodeShape {
        parent: 33,
        kind: Some("compound-assignment-expression"),
        ty: Some("u32"),
        op: Some("+="),
        reference: None,
        literal: None,
        constant: None,
        start: 210,
        end: 239,
    },
    NodeShape {
        parent: 34,
        kind: Some("declaration-reference-expression"),
        ty: Some("u32"),
        op: None,
        reference: Some("checksum@885"),
        literal: None,
        constant: None,
        start: 210,
        end: 218,
    },
    NodeShape {
        parent: 34,
        kind: Some("cast-expression"),
        ty: Some("u32"),
        op: Some("integral-cast"),
        reference: None,
        literal: None,
        constant: None,
        start: 222,
        end: 239,
    },
    NodeShape {
        parent: 36,
        kind: Some("cast-expression"),
        ty: Some("i32"),
        op: Some("lvalue-to-rvalue"),
        reference: None,
        literal: None,
        constant: None,
        start: 232,
        end: 239,
    },
    NodeShape {
        parent: 37,
        kind: Some("declaration-reference-expression"),
        ty: Some("i32"),
        op: None,
        reference: Some("current@908"),
        literal: None,
        constant: None,
        start: 232,
        end: 239,
    },
    NodeShape {
        parent: 18,
        kind: Some("binary-expression"),
        ty: Some("u32"),
        op: Some("="),
        reference: None,
        literal: None,
        constant: None,
        start: 259,
        end: 292,
    },
    NodeShape {
        parent: 39,
        kind: Some("declaration-reference-expression"),
        ty: Some("u32"),
        op: None,
        reference: Some("checksum@885"),
        literal: None,
        constant: None,
        start: 259,
        end: 267,
    },
    NodeShape {
        parent: 39,
        kind: Some("binary-expression"),
        ty: Some("u32"),
        op: Some("&"),
        reference: None,
        literal: None,
        constant: None,
        start: 270,
        end: 292,
    },
    NodeShape {
        parent: 41,
        kind: Some("parenthesized-expression"),
        ty: Some("u32"),
        op: None,
        reference: None,
        literal: None,
        constant: None,
        start: 270,
        end: 285,
    },
    NodeShape {
        parent: 42,
        kind: Some("binary-expression"),
        ty: Some("u32"),
        op: Some("+"),
        reference: None,
        literal: None,
        constant: None,
        start: 271,
        end: 284,
    },
    NodeShape {
        parent: 43,
        kind: Some("cast-expression"),
        ty: Some("u32"),
        op: Some("lvalue-to-rvalue"),
        reference: None,
        literal: None,
        constant: None,
        start: 271,
        end: 279,
    },
    NodeShape {
        parent: 44,
        kind: Some("declaration-reference-expression"),
        ty: Some("u32"),
        op: None,
        reference: Some("checksum@885"),
        literal: None,
        constant: None,
        start: 271,
        end: 279,
    },
    NodeShape {
        parent: 43,
        kind: Some("integer-literal"),
        ty: Some("u32"),
        op: None,
        reference: None,
        literal: Some("3"),
        constant: Some("3"),
        start: 282,
        end: 284,
    },
    NodeShape {
        parent: 41,
        kind: Some("integer-literal"),
        ty: Some("u32"),
        op: None,
        reference: None,
        literal: Some("255"),
        constant: Some("255"),
        start: 288,
        end: 292,
    },
    NodeShape {
        parent: 18,
        kind: Some("binary-expression"),
        ty: Some("i32"),
        op: Some("="),
        reference: None,
        literal: None,
        constant: None,
        start: 302,
        end: 321,
    },
    NodeShape {
        parent: 48,
        kind: Some("declaration-reference-expression"),
        ty: Some("i32"),
        op: None,
        reference: Some("current@908"),
        literal: None,
        constant: None,
        start: 302,
        end: 309,
    },
    NodeShape {
        parent: 48,
        kind: Some("call-expression"),
        ty: Some("i32"),
        op: None,
        reference: Some("external:getchar"),
        literal: None,
        constant: None,
        start: 312,
        end: 321,
    },
    NodeShape {
        parent: 50,
        kind: Some("cast-expression"),
        ty: Some("ptr(fn()->i32)"),
        op: Some("function-to-pointer"),
        reference: None,
        literal: None,
        constant: None,
        start: 312,
        end: 319,
    },
    NodeShape {
        parent: 51,
        kind: Some("declaration-reference-expression"),
        ty: Some("fn()->i32"),
        op: None,
        reference: Some("external:getchar"),
        literal: None,
        constant: None,
        start: 312,
        end: 319,
    },
    NodeShape {
        parent: 2,
        kind: Some("call-expression"),
        ty: Some("i32"),
        op: None,
        reference: Some("external:putchar"),
        literal: None,
        constant: None,
        start: 333,
        end: 355,
    },
    NodeShape {
        parent: 53,
        kind: Some("cast-expression"),
        ty: Some("ptr(fn(i32)->i32)"),
        op: Some("function-to-pointer"),
        reference: None,
        literal: None,
        constant: None,
        start: 333,
        end: 340,
    },
    NodeShape {
        parent: 54,
        kind: Some("declaration-reference-expression"),
        ty: Some("fn(i32)->i32"),
        op: None,
        reference: Some("external:putchar"),
        literal: None,
        constant: None,
        start: 333,
        end: 340,
    },
    NodeShape {
        parent: 53,
        kind: Some("cast-expression"),
        ty: Some("i32"),
        op: Some("integral-cast"),
        reference: None,
        literal: None,
        constant: None,
        start: 341,
        end: 354,
    },
    NodeShape {
        parent: 56,
        kind: Some("cast-expression"),
        ty: Some("u32"),
        op: Some("lvalue-to-rvalue"),
        reference: None,
        literal: None,
        constant: None,
        start: 346,
        end: 354,
    },
    NodeShape {
        parent: 57,
        kind: Some("declaration-reference-expression"),
        ty: Some("u32"),
        op: None,
        reference: Some("checksum@885"),
        literal: None,
        constant: None,
        start: 346,
        end: 354,
    },
];

const FUNCTION_SOURCE: &str = concat!(
    "void emit(void) {\n",
    "    unsigned checksum = 0U;\n",
    "    int current = getchar();\n",
    "    while (current != EOF) {\n",
    "        if ((current & 1) != 0) {\n",
    "            checksum ^= (unsigned)current;\n",
    "        } else {\n",
    "            checksum += (unsigned)current;\n",
    "        }\n",
    "        checksum = (checksum + 3U) & 255U;\n",
    "        current = getchar();\n",
    "    }\n",
    "    putchar((int)checksum);\n",
    "}",
);

fn matches_pinned_frontend(input: &Artifact, source: &[u8]) -> bool {
    let Some(function) = input.nodes.first() else {
        return false;
    };
    if input.schema_version != 1
        || input.identity != "malbolge-c-frontend-v1"
        || input.profile.abi_id != "malbolge-c32-v1"
        || input.profile.target_profile != "malbolge-2026"
        || input.clang.version != "22.1.8"
        || input.clang.target != "wasm32-unknown-unknown"
        || input.clang.language != "c23"
        || input.source.sha256 != FROZEN_SHA256
        || input.nodes.len() != SHAPES.len()
        || source.get(
            usize::try_from(function.span.begin.byte).unwrap_or(usize::MAX)
                ..usize::try_from(function.span.end.byte).unwrap_or(usize::MAX),
        ) != Some(FUNCTION_SOURCE.as_bytes())
    {
        return false;
    }
    input
        .nodes
        .iter()
        .zip(SHAPES)
        .enumerate()
        .all(|(idx, (node, shape))| {
            let Some(start) = function.span.begin.byte.checked_add(shape.start)
            else {
                return false;
            };
            let Some(end) = function.span.begin.byte.checked_add(shape.end)
            else {
                return false;
            };
            let expected_start = source_position(source, start);
            let expected_end = source_position(source, end);
            let fields = node.id == (idx as u32) + 1
                && node.parent == shape.parent
                && node.kind == shape.kind.unwrap_or("")
                && node.type_name.as_deref() == shape.ty
                && node.operation.as_deref() == shape.op
                && node.reference.as_deref() == shape.reference
                && node.literal.as_deref() == shape.literal
                && node.constant_integer.as_deref() == shape.constant
                && expected_start.is_some_and(|(line, column)| {
                    node.span.begin.byte == start
                        && node.span.begin.line == line
                        && node.span.begin.column == column
                })
                && expected_end.is_some_and(|(line, column)| {
                    node.span.end.byte == end
                        && node.span.end.line == line
                        && node.span.end.column == column
                });
            if !fields {
                return false;
            }
            match node.id {
                1 => {
                    node.name.as_deref() == Some("emit")
                        && node.definition.as_deref() == Some("definition")
                        && node.linkage.as_deref() == Some("external")
                        && node.storage_class.as_deref() == Some("none")
                        && node.inline_specified == Some(false)
                        && node.storage_duration.is_none()
                },
                4 | 7 => {
                    node.name.as_deref()
                        == Some(if node.id == 4 {
                            "checksum"
                        } else {
                            "current"
                        })
                        && node.definition.as_deref() == Some("definition")
                        && node.linkage.as_deref() == Some("none")
                        && node.storage_class.as_deref() == Some("none")
                        && matches!(
                            node.storage_duration,
                            Some(super::StorageDuration::Automatic)
                        )
                        && node.inline_specified.is_none()
                },
                _ => {
                    node.name.is_none()
                        && node.definition.is_none()
                        && node.inline_specified.is_none()
                        && node.linkage.is_none()
                        && node.storage_class.is_none()
                        && node.storage_duration.is_none()
                },
            }
        })
}

fn source_position(source: &[u8], byte: u32) -> Option<(u32, u32)> {
    let prefix = source.get(..usize::try_from(byte).ok()?)?;
    let line =
        1 + u32::try_from(prefix.iter().filter(|b| **b == b'\n').count())
            .ok()?;
    let column = 1 + u32::try_from(
        prefix.iter().rev().take_while(|b| **b != b'\n').count(),
    )
    .ok()?;
    Some((line, column))
}

fn instruction(operation: Instruction, node: &Node) -> LocatedInstruction {
    LocatedInstruction::new(operation, typed_span(&node.span))
}

fn id(n: u32) -> ValueId {
    ValueId::new(n)
}

fn block_id(n: u32) -> BlockId {
    BlockId::new(n)
}

fn make_block(
    index: u32,
    source_node: &Node,
    instructions: Vec<LocatedInstruction>,
    phis: Vec<Phi>,
    terminator: Terminator,
    terminator_node: &Node,
) -> BasicBlock {
    BasicBlock::new(BasicBlockSpec {
        id: block_id(index),
        instructions,
        phis,
        span: typed_span(&source_node.span),
        terminator,
        terminator_span: typed_span(&terminator_node.span),
    })
}

/// Lower the frozen *complete* dynamic checksum to typed SSA and re-admit it.
///
/// Unlike the independent-byte projections, the input value is live: EOF
/// selects exit, parity selects a distinct arithmetic arm, and phi edges
/// preserve the evolving checksum and the next signed `getchar` result.
/// This routine never produces an executable Malbolge guest; dynamic layout
/// remains a separately diagnosed, unsupported compilation stage.
///
/// # Errors
///
/// Refuses missing original C, drifted Clang tree, mismatched ABI and invalid
/// typed SSA before a target backend may publish anything.
#[expect(
    clippy::too_many_lines,
    reason = "one complete, source-locked dynamic CFG witness"
)]
pub(super) fn canonical_dynamic_eof_checksum(
    bytes: &[u8],
    source: &[u8],
) -> Result<Vec<u8>, FrontendJsonError> {
    if bytes.is_empty() || bytes.len() > 1_048_576 {
        return Err(FrontendJsonError::Malformed);
    }
    let input: Artifact = serde_json::from_slice(bytes)
        .map_err(|_error| FrontendJsonError::Malformed)?;
    if !matches_pinned_frontend(&input, source) {
        return Err(FrontendJsonError::Unsupported);
    }
    let n = &input.nodes;
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
                body_span: super::span(&n[1].span),
                definition: String::from("definition"),
                function_span: super::span(&n[0].span),
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
    let mut types = base.types().to_vec();
    if types.len() != 2 || types[0].id() != TypeId::new(0) {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    types[0] = TypeEntry::new(TypeId::new(0), TypeDef::I32);
    types.push(TypeEntry::new(TypeId::new(2), TypeDef::U32));
    types.push(TypeEntry::new(TypeId::new(3), TypeDef::Bool));
    types.push(TypeEntry::new(TypeId::new(4), TypeDef::U8));
    let i32_type = TypeId::new(0);
    let u32_type = TypeId::new(2);
    let bool_type = TypeId::new(3);
    let u8_type = TypeId::new(4);

    let entry = make_block(
        0,
        &n[1],
        vec![
            instruction(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(32, vec![0, 0, 0, 0]),
                    result: id(0),
                    type_id: u32_type,
                },
                &n[4],
            ),
            instruction(
                Instruction::Getchar {
                    result: id(1),
                    type_id: i32_type,
                },
                &n[7],
            ),
            instruction(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(32, vec![
                        255, 255, 255, 255,
                    ]),
                    result: id(2),
                    type_id: i32_type,
                },
                &n[16],
            ),
            instruction(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(32, vec![1, 0, 0, 0]),
                    result: id(3),
                    type_id: i32_type,
                },
                &n[24],
            ),
            instruction(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(32, vec![0, 0, 0, 0]),
                    result: id(4),
                    type_id: i32_type,
                },
                &n[25],
            ),
            instruction(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(32, vec![3, 0, 0, 0]),
                    result: id(5),
                    type_id: u32_type,
                },
                &n[45],
            ),
            instruction(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(32, vec![255, 0, 0, 0]),
                    result: id(6),
                    type_id: u32_type,
                },
                &n[46],
            ),
        ],
        vec![],
        Terminator::Jump { target: block_id(1) },
        &n[10],
    );

    let header = make_block(
        1,
        &n[10],
        vec![instruction(
            Instruction::Compare {
                left: id(7),
                right: id(2),
                operation: CompareOp::NotEqual,
                result: id(9),
                type_id: bool_type,
            },
            &n[11],
        )],
        vec![
            Phi::new(
                id(7),
                i32_type,
                vec![
                    PhiIncoming::new(block_id(0), id(1)),
                    PhiIncoming::new(block_id(5), id(19)),
                ],
                typed_span(&n[13].span),
            ),
            Phi::new(
                id(8),
                u32_type,
                vec![
                    PhiIncoming::new(block_id(0), id(0)),
                    PhiIncoming::new(block_id(5), id(18)),
                ],
                typed_span(&n[11].span),
            ),
        ],
        Terminator::Branch {
            condition: id(9),
            false_target: block_id(6),
            true_target: block_id(2),
        },
        &n[11],
    );

    let parity = make_block(
        2,
        &n[18],
        vec![
            instruction(
                Instruction::Binary {
                    left: id(7),
                    right: id(3),
                    operation: BinaryOp::And,
                    result: id(10),
                    type_id: i32_type,
                },
                &n[21],
            ),
            instruction(
                Instruction::Compare {
                    left: id(10),
                    right: id(4),
                    operation: CompareOp::NotEqual,
                    result: id(11),
                    type_id: bool_type,
                },
                &n[19],
            ),
        ],
        vec![],
        Terminator::Branch {
            condition: id(11),
            false_target: block_id(4),
            true_target: block_id(3),
        },
        &n[19],
    );

    let xor_arm = make_block(
        3,
        &n[26],
        vec![
            instruction(
                Instruction::Cast {
                    operation: CastOp::IntegerBitcast,
                    result: id(12),
                    type_id: u32_type,
                    value: id(7),
                },
                &n[29],
            ),
            instruction(
                Instruction::Binary {
                    left: id(8),
                    right: id(12),
                    operation: BinaryOp::Xor,
                    result: id(13),
                    type_id: u32_type,
                },
                &n[27],
            ),
        ],
        vec![],
        Terminator::Jump { target: block_id(5) },
        &n[27],
    );

    let add_arm = make_block(
        4,
        &n[32],
        vec![
            instruction(
                Instruction::Cast {
                    operation: CastOp::IntegerBitcast,
                    result: id(14),
                    type_id: u32_type,
                    value: id(7),
                },
                &n[35],
            ),
            instruction(
                Instruction::Binary {
                    left: id(8),
                    right: id(14),
                    operation: BinaryOp::Add,
                    result: id(15),
                    type_id: u32_type,
                },
                &n[33],
            ),
        ],
        vec![],
        Terminator::Jump { target: block_id(5) },
        &n[33],
    );

    let backedge = make_block(
        5,
        &n[17],
        vec![
            instruction(
                Instruction::Binary {
                    left: id(16),
                    right: id(5),
                    operation: BinaryOp::Add,
                    result: id(17),
                    type_id: u32_type,
                },
                &n[42],
            ),
            instruction(
                Instruction::Binary {
                    left: id(17),
                    right: id(6),
                    operation: BinaryOp::And,
                    result: id(18),
                    type_id: u32_type,
                },
                &n[40],
            ),
            instruction(
                Instruction::Getchar {
                    result: id(19),
                    type_id: i32_type,
                },
                &n[49],
            ),
        ],
        vec![Phi::new(
            id(16),
            u32_type,
            vec![
                PhiIncoming::new(block_id(3), id(13)),
                PhiIncoming::new(block_id(4), id(15)),
            ],
            typed_span(&n[38].span),
        )],
        Terminator::Jump { target: block_id(1) },
        &n[47],
    );

    let exit = make_block(
        6,
        &n[52],
        vec![
            instruction(
                Instruction::Cast {
                    operation: CastOp::Truncate,
                    result: id(20),
                    type_id: u8_type,
                    value: id(8),
                },
                &n[55],
            ),
            instruction(Instruction::ByteOutput { value: id(20) }, &n[52]),
        ],
        vec![],
        Terminator::Return { value: None },
        &n[52],
    );

    let function = Function::new(FunctionSpec {
        blocks: vec![entry, header, parity, xor_arm, add_arm, backedge, exit],
        entry: block_id(0),
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
    let encoded = canonical_bytes(&module)
        .map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    if canonical_module(&encoded)
        .map_err(|_error| FrontendJsonError::InvalidTypedIr)?
        != module
    {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    Ok(encoded)
}
