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
//   - Exact C23 first-input EOF coalescence and second-input EOF branch.
// - Must-Not:
//   - Replace live input with host data or elide signed EOF comparisons.
// - Allows:
//   - Inputs: one complete source and normalized pinned-Clang subtree.
//   - Outputs: typed two-read CFG for an independently linked real guest.
//   - Side effects: none.
// - Split-When:
//   - General typed conditional lowering implements the same effect trace.
// - Merge-When:
//   - General signed EOF branch linker supersedes source-bound proof.
// - Summary:
//   - Authenticates both C reads and both conditionals before guest linkage.

//! Closed source-C witness for two reads and a *real* second-input EOF arm.
//! The first ternary coalesces C EOF to the target EOF low byte (106).

use super::typed::{
    BasicBlock, BasicBlockSpec, BlockId, CastOp, CompareOp, FrontendArtifact,
    FrontendArtifactSpec, FrontendFallthroughVoidFunctionSpec,
    FrontendReturnVoidFunction, Function, FunctionSpec, Instruction,
    IntegerConstant, LocatedInstruction, Module, ModuleSpec, Phi, PhiIncoming,
    Terminator, TypeDef, TypeEntry, TypeId, ValueId,
};
use super::{
    Artifact, CanonicalGuestProjection, FrontendGuestMode, FrontendJsonError,
    Node, canonical_bytes, canonical_module, lower_frontend_artifact,
    source_digest, typed_span,
};

const SOURCE_SHA256: &str =
    "163a96c1724e0848a0a56bc9d6b69b04a45aabc29de58e83642325c6ffa418c3";
const GUARDED_SOURCE_SHA256: &str =
    "65c93f567b3460dfaa2588a1a4355312abfc469fa519b1d3bc697319a26ecd14";
const GUARDED_FUNCTION_SOURCE: &str = concat!(
    "void emit(void) {\n",
    "    int first = getchar();\n",
    "    putchar(first == EOF ? 106 : first);\n",
    "    int second = getchar();\n",
    "    if (second == EOF) {\n",
    "        putchar(30);\n",
    "    } else {\n",
    "        putchar(154);\n",
    "        getchar();\n",
    "    }\n",
    "}",
);

const FUNCTION_SOURCE: &str = concat!(
    "void emit(void) {\n",
    "    int first = getchar();\n",
    "    putchar(first == EOF ? 106 : first);\n",
    "    int second = getchar();\n",
    "    if (second == EOF) {\n",
    "        putchar(30);\n",
    "    } else {\n",
    "        putchar(154);\n",
    "    }\n",
    "}",
);

// parent, kind, type, operator, reference, literal, folded constant,
// source-relative begin and end. Every AST descendant is mandatory.
type Shape = (
    u32,
    &'static str,
    &'static str,
    &'static str,
    &'static str,
    &'static str,
    &'static str,
    u32,
    u32,
);
const SHAPES: &[Shape] = &[
    (
        0,
        "function-declaration",
        "fn()->void",
        "",
        "",
        "",
        "",
        0,
        202,
    ), // 1
    (1, "compound-statement", "", "", "", "", "", 16, 202), // 2
    (2, "declaration-statement", "", "", "", "", "", 22, 44), // 3
    (
        3,
        "variable-declaration",
        "i32",
        "",
        "first@862",
        "",
        "",
        22,
        43,
    ), // 4
    (
        4,
        "call-expression",
        "i32",
        "",
        "external:getchar",
        "",
        "",
        34,
        43,
    ), // 5
    (
        5,
        "cast-expression",
        "ptr(fn()->i32)",
        "function-to-pointer",
        "",
        "",
        "",
        34,
        41,
    ), // 6
    (
        6,
        "declaration-reference-expression",
        "fn()->i32",
        "",
        "external:getchar",
        "",
        "",
        34,
        41,
    ), // 7
    (
        2,
        "call-expression",
        "i32",
        "",
        "external:putchar",
        "",
        "",
        49,
        84,
    ), // 8
    (
        8,
        "cast-expression",
        "ptr(fn(i32)->i32)",
        "function-to-pointer",
        "",
        "",
        "",
        49,
        56,
    ), // 9
    (
        9,
        "declaration-reference-expression",
        "fn(i32)->i32",
        "",
        "external:putchar",
        "",
        "",
        49,
        56,
    ), // 10
    (8, "conditional-expression", "i32", "", "", "", "", 57, 83), // 11
    (11, "binary-expression", "i32", "==", "", "", "", 57, 69), // 12
    (
        12,
        "cast-expression",
        "i32",
        "lvalue-to-rvalue",
        "",
        "",
        "",
        57,
        62,
    ), // 13
    (
        13,
        "declaration-reference-expression",
        "i32",
        "",
        "first@862",
        "",
        "",
        57,
        62,
    ), // 14
    (
        12,
        "parenthesized-expression",
        "i32",
        "",
        "",
        "",
        "-1",
        66,
        69,
    ), // 15
    (15, "unary-expression", "i32", "-", "", "", "-1", 66, 69), // 16
    (16, "integer-literal", "i32", "", "", "1", "1", 66, 69), // 17
    (11, "integer-literal", "i32", "", "", "106", "106", 72, 75), // 18
    (
        11,
        "cast-expression",
        "i32",
        "lvalue-to-rvalue",
        "",
        "",
        "",
        78,
        83,
    ), // 19
    (
        19,
        "declaration-reference-expression",
        "i32",
        "",
        "first@862",
        "",
        "",
        78,
        83,
    ), // 20
    (2, "declaration-statement", "", "", "", "", "", 90, 113), // 21
    (
        21,
        "variable-declaration",
        "i32",
        "",
        "second@930",
        "",
        "",
        90,
        112,
    ), // 22
    (
        22,
        "call-expression",
        "i32",
        "",
        "external:getchar",
        "",
        "",
        103,
        112,
    ), // 23
    (
        23,
        "cast-expression",
        "ptr(fn()->i32)",
        "function-to-pointer",
        "",
        "",
        "",
        103,
        110,
    ), // 24
    (
        24,
        "declaration-reference-expression",
        "fn()->i32",
        "",
        "external:getchar",
        "",
        "",
        103,
        110,
    ), // 25
    (2, "if-statement", "", "", "", "", "", 118, 200),      // 26
    (26, "binary-expression", "i32", "==", "", "", "", 122, 135), // 27
    (
        27,
        "cast-expression",
        "i32",
        "lvalue-to-rvalue",
        "",
        "",
        "",
        122,
        128,
    ), // 28
    (
        28,
        "declaration-reference-expression",
        "i32",
        "",
        "second@930",
        "",
        "",
        122,
        128,
    ), // 29
    (
        27,
        "parenthesized-expression",
        "i32",
        "",
        "",
        "",
        "-1",
        132,
        135,
    ), // 30
    (30, "unary-expression", "i32", "-", "", "", "-1", 132, 135), // 31
    (31, "integer-literal", "i32", "", "", "1", "1", 132, 135), // 32
    (26, "compound-statement", "", "", "", "", "", 137, 165), // 33
    (
        33,
        "call-expression",
        "i32",
        "",
        "external:putchar",
        "",
        "",
        147,
        158,
    ), // 34
    (
        34,
        "cast-expression",
        "ptr(fn(i32)->i32)",
        "function-to-pointer",
        "",
        "",
        "",
        147,
        154,
    ), // 35
    (
        35,
        "declaration-reference-expression",
        "fn(i32)->i32",
        "",
        "external:putchar",
        "",
        "",
        147,
        154,
    ), // 36
    (34, "integer-literal", "i32", "", "", "30", "30", 155, 157), // 37
    (26, "compound-statement", "", "", "", "", "", 171, 200), // 38
    (
        38,
        "call-expression",
        "i32",
        "",
        "external:putchar",
        "",
        "",
        181,
        193,
    ), // 39
    (
        39,
        "cast-expression",
        "ptr(fn(i32)->i32)",
        "function-to-pointer",
        "",
        "",
        "",
        181,
        188,
    ), // 40
    (
        40,
        "declaration-reference-expression",
        "fn(i32)->i32",
        "",
        "external:putchar",
        "",
        "",
        181,
        188,
    ), // 41
    (39, "integer-literal", "i32", "", "", "154", "154", 189, 192), // 42
];

// Extra pinned Clang nodes from the successful second-read arm only.
const GUARDED_EXTRA_SHAPES: &[Shape] = &[
    (
        38,
        "call-expression",
        "i32",
        "",
        "external:getchar",
        "",
        "",
        203,
        212,
    ),
    (
        43,
        "cast-expression",
        "ptr(fn()->i32)",
        "function-to-pointer",
        "",
        "",
        "",
        203,
        210,
    ),
    (
        44,
        "declaration-reference-expression",
        "fn()->i32",
        "",
        "external:getchar",
        "",
        "",
        203,
        210,
    ),
];

fn position(source: &[u8], offset: u32) -> Option<(u32, u32)> {
    let prefix = source.get(..usize::try_from(offset).ok()?)?;
    let line =
        u32::try_from(prefix.iter().filter(|&&byte| byte == b'\n').count())
            .ok()?
            + 1;
    let column = u32::try_from(
        prefix
            .iter()
            .rev()
            .take_while(|&&byte| byte != b'\n')
            .count(),
    )
    .ok()?
        + 1;
    Some((line, column))
}

fn source_matches(input: &Artifact, source: &[u8]) -> bool {
    let Some(function) = input.nodes.first() else {
        return false;
    };
    let guarded = input.source.sha256 == GUARDED_SOURCE_SHA256;
    let expected_source = if guarded {
        GUARDED_FUNCTION_SOURCE
    } else {
        FUNCTION_SOURCE
    };
    if input.schema_version != 1
        || input.identity != "malbolge-c-frontend-v1"
        || input.profile.abi_id != "malbolge-c32-v1"
        || input.profile.target_profile != "malbolge-2026"
        || input.clang.version != "22.1.8"
        || input.clang.target != "wasm32-unknown-unknown"
        || input.clang.language != "c23"
        || (!guarded && input.source.sha256 != SOURCE_SHA256)
        || input.nodes.len()
            != SHAPES.len() + usize::from(guarded) * GUARDED_EXTRA_SHAPES.len()
        || source.get(
            usize::try_from(function.span.begin.byte).unwrap_or(usize::MAX)
                ..usize::try_from(function.span.end.byte).unwrap_or(usize::MAX),
        ) != Some(expected_source.as_bytes())
    {
        return false;
    }
    input
        .nodes
        .iter()
        .zip(SHAPES.iter().chain(GUARDED_EXTRA_SHAPES.iter().take(
            if guarded {
                GUARDED_EXTRA_SHAPES.len()
            } else {
                0
            },
        )))
        .enumerate()
        .all(|(index, (node, shape))| {
            let &(
                parent,
                kind,
                ty,
                op,
                reference,
                literal,
                constant,
                start,
                end,
            ) = shape;
            // Only the two containing blocks grow when the guarded
            // call is appended after the original success marker.
            let end = if guarded {
                match index {
                    0 | 1 => 221,
                    25 | 37 => 219,
                    _ => end,
                }
            } else {
                end
            };
            let reference = if guarded {
                match reference {
                    "first@862" => "first@836",
                    "second@930" => "second@904",
                    _ => reference,
                }
            } else {
                reference
            };
            let Some(begin) = function.span.begin.byte.checked_add(start)
            else {
                return false;
            };
            let Some(end) = function.span.begin.byte.checked_add(end) else {
                return false;
            };
            let semantic = node.id
                == u32::try_from(index).unwrap_or(u32::MAX) + 1
                && node.parent == parent
                && node.kind == kind
                && node.type_name.as_deref().unwrap_or("") == ty
                && node.operation.as_deref().unwrap_or("") == op
                && node.reference.as_deref().unwrap_or("") == reference
                && node.literal.as_deref().unwrap_or("") == literal
                && node.constant_integer.as_deref().unwrap_or("") == constant
                && position(source, begin).is_some_and(|(line, column)| {
                    node.span.begin.byte == begin
                        && node.span.begin.line == line
                        && node.span.begin.column == column
                })
                && position(source, end).is_some_and(|(line, column)| {
                    node.span.end.byte == end
                        && node.span.end.line == line
                        && node.span.end.column == column
                });
            if !semantic {
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
                4 | 22 => {
                    node.name.as_deref()
                        == Some(if node.id == 4 {
                            "first"
                        } else {
                            "second"
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
                        && node.linkage.is_none()
                        && node.storage_class.is_none()
                        && node.storage_duration.is_none()
                        && node.inline_specified.is_none()
                },
            }
        })
}

fn value(index: u32) -> ValueId {
    ValueId::new(index)
}
fn block(index: u32) -> BlockId {
    BlockId::new(index)
}
fn located(instruction: Instruction, provenance: &Node) -> LocatedInstruction {
    LocatedInstruction::new(instruction, typed_span(&provenance.span))
}
fn code_block(
    id: u32,
    scope: &Node,
    instructions: Vec<LocatedInstruction>,
    phis: Vec<Phi>,
    terminator: Terminator,
    control: &Node,
) -> BasicBlock {
    BasicBlock::new(BasicBlockSpec {
        id: block(id),
        instructions,
        phis,
        span: typed_span(&scope.span),
        terminator,
        terminator_span: typed_span(&control.span),
    })
}

/// Re-admit the two-read signed-EOF conditional as genuine canonical SSA.
///
/// # Errors
/// Refuses changed source, unauthorized Clang nodes, or untyped effects.
#[expect(
    clippy::too_many_lines,
    reason = "one complete source-locked conditional CFG"
)]
pub(super) fn canonical_two_read_eof_branch(
    bytes: &[u8],
    source: &[u8],
) -> Result<CanonicalGuestProjection, FrontendJsonError> {
    if bytes.is_empty() || bytes.len() > 1_048_576 {
        return Err(FrontendJsonError::Malformed);
    }
    let input: Artifact = serde_json::from_slice(bytes)
        .map_err(|_| FrontendJsonError::Malformed)?;
    if !source_matches(&input, source) {
        return Err(FrontendJsonError::Unsupported);
    }
    let n = &input.nodes;
    let guarded = input.source.sha256 == GUARDED_SOURCE_SHA256;
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
        .map_err(|_| FrontendJsonError::InvalidTypedIr)?;
    let original = base
        .functions()
        .first()
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    let mut types = base.types().to_vec();
    if types.len() != 2 || types[0].id() != TypeId::new(0) {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    types[0] = TypeEntry::new(TypeId::new(0), TypeDef::I32);
    types.push(TypeEntry::new(TypeId::new(2), TypeDef::Bool));
    types.push(TypeEntry::new(TypeId::new(3), TypeDef::U8));
    let i32_type = TypeId::new(0);
    let bool_type = TypeId::new(2);
    let byte_type = TypeId::new(3);
    let blocks = vec![
        code_block(
            0,
            &n[1],
            vec![
                located(
                    Instruction::Getchar {
                        result: value(0),
                        type_id: i32_type,
                    },
                    &n[4],
                ),
                located(
                    Instruction::ConstantInteger {
                        constant: IntegerConstant::new(32, vec![255; 4]),
                        result: value(1),
                        type_id: i32_type,
                    },
                    &n[15],
                ),
                located(
                    Instruction::Compare {
                        left: value(0),
                        right: value(1),
                        operation: CompareOp::Equal,
                        result: value(2),
                        type_id: bool_type,
                    },
                    &n[11],
                ),
            ],
            vec![],
            Terminator::Branch {
                condition: value(2),
                true_target: block(1),
                false_target: block(2),
            },
            &n[11],
        ),
        code_block(
            1,
            &n[17],
            vec![located(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![106]),
                    result: value(3),
                    type_id: byte_type,
                },
                &n[17],
            )],
            vec![],
            Terminator::Jump { target: block(3) },
            &n[17],
        ),
        code_block(
            2,
            &n[18],
            vec![located(
                Instruction::Cast {
                    operation: CastOp::Truncate,
                    result: value(4),
                    type_id: byte_type,
                    value: value(0),
                },
                &n[18],
            )],
            vec![],
            Terminator::Jump { target: block(3) },
            &n[18],
        ),
        code_block(
            3,
            &n[1],
            vec![
                located(Instruction::ByteOutput { value: value(5) }, &n[7]),
                located(
                    Instruction::Getchar {
                        result: value(6),
                        type_id: i32_type,
                    },
                    &n[22],
                ),
                located(
                    Instruction::Compare {
                        left: value(6),
                        right: value(1),
                        operation: CompareOp::Equal,
                        result: value(7),
                        type_id: bool_type,
                    },
                    &n[26],
                ),
            ],
            vec![Phi::new(
                value(5),
                byte_type,
                vec![
                    PhiIncoming::new(block(1), value(3)),
                    PhiIncoming::new(block(2), value(4)),
                ],
                typed_span(&n[10].span),
            )],
            Terminator::Branch {
                condition: value(7),
                true_target: block(4),
                false_target: block(5),
            },
            &n[26],
        ),
        code_block(
            4,
            &n[32],
            vec![
                located(
                    Instruction::ConstantInteger {
                        constant: IntegerConstant::new(8, vec![30]),
                        result: value(8),
                        type_id: byte_type,
                    },
                    &n[36],
                ),
                located(Instruction::ByteOutput { value: value(8) }, &n[33]),
            ],
            vec![],
            Terminator::Return { value: None },
            &n[32],
        ),
        code_block(
            5,
            &n[37],
            {
                let mut instructions = vec![
                    located(
                        Instruction::ConstantInteger {
                            constant: IntegerConstant::new(8, vec![154]),
                            result: value(9),
                            type_id: byte_type,
                        },
                        &n[41],
                    ),
                    located(
                        Instruction::ByteOutput { value: value(9) },
                        &n[38],
                    ),
                ];
                if guarded {
                    instructions.push(located(
                        Instruction::Getchar {
                            result: value(10),
                            type_id: i32_type,
                        },
                        &n[42],
                    ));
                }
                instructions
            },
            vec![],
            Terminator::Return { value: None },
            &n[37],
        ),
    ];
    let function = Function::new(FunctionSpec {
        blocks,
        entry: block(0),
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
    Ok((wire, FrontendGuestMode::TwoReadEofBranch))
}
