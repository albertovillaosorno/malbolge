// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Integration evidence for typed-IR admission, SSA/CFG, and canonical
//     identity.
// - Must-Not:
//   - Parse C, execute Malbolge, or use LLVM IR as an implicit test oracle.
// - Allows:
//   - Inputs: explicit accepted and malformed portable typed-IR values.
//   - Outputs: deterministic validation/serialization regression assertions.
//   - Side effects: test-process allocation and tracked golden-file reads only.
// - Split-When:
//   - Frontend-to-IR lowering gains independently owned fixture lifecycle.
// - Merge-When:
//   - Another suite owns this exact typed-IR domain/application evidence.
// - Summary:
//   - Locks portable typed SSA/control flow and canonical version-one identity.
// - Description:
//   - Fixtures are built by constructors rather than mutating nested IR by
//     index.
// - Usage:
//   - Auto-discovered by the root Cargo workspace as an integration-test crate.
// - Defaults:
//   - Invalid IR must fail before canonical bytes/debug text are published.
//

//! Integration tests for portable typed compiler IR version one.

#[path = "../src/compiler/typed-ir/composition/lib.rs"]
pub mod typed_ir;

use std::fs::read_to_string;

use malbolge as _;
use typed_ir::{
    BasicBlock, BasicBlockSpec, BinaryOp, BlockId, CallTarget, CanonicalError,
    CastOp, CompareOp, FrontendArtifact, FrontendArtifactSpec,
    FrontendLoweringError, FrontendPosition, FrontendReturnIntegerFunction,
    FrontendReturnIntegerFunctionSpec, FrontendSpan, Function, FunctionId,
    FunctionSpec, Global, GlobalId, GlobalSpec, Instruction, IntegerConstant,
    LocatedInstruction, Module, ModuleSpec, Parameter, Phi, PhiIncoming,
    ProofObligation, SourcePosition, SourceSpan, Terminator, TypeDef,
    TypeEntry, TypeId, ValidationError, ValueId, canonical_bytes,
    canonical_debug_text, lower_frontend_artifact, validate_module,
};

const ABI_ID: &str = "malbolge-c32-v1";
const PROFILE_ID: &str = "malbolge-2026";
const SOURCE_ID: &str = "fixtures/select.c";
const GOLDEN_PATH: &str = "tests/compiler/typed-ir/golden/select.hex";
const EXTENDED_GOLDEN_PATH: &str =
    "tests/compiler/typed-ir/golden/extended-semantics.hex";
const LOWERING_GOLDEN_PATH: &str =
    "tests/compiler/typed-ir/golden/ir-return-constant.hex";
const LOWERING_SOURCE_ID: &str = "fixtures/ir-return.c";
const LOWERING_SOURCE_HASH: [u8; 32] = [
    0xe1, 0xa4, 0x2c, 0x56, 0xb3, 0x95, 0x1d, 0xf4, 0x5a, 0x2e, 0x2c, 0x27,
    0xc7, 0xb2, 0xdf, 0x69, 0xeb, 0x5b, 0x12, 0x61, 0xd5, 0x9d, 0xe2, 0xb0,
    0xc9, 0x63, 0xe0, 0x2e, 0x00, 0x1d, 0xbc, 0x93,
];
const SOURCE_HASH: [u8; 32] = [0x5a; 32];
const BOOL_TYPE: TypeId = TypeId::new(0);
const I32_TYPE: TypeId = TypeId::new(1);
const FUNCTION_TYPE: TypeId = TypeId::new(2);
const FUNCTION_ID: FunctionId = FunctionId::new(0);

const fn position(byte: u32) -> SourcePosition {
    SourcePosition::new(byte, 1, byte.saturating_add(1))
}

const fn span(begin: u32, end: u32) -> SourceSpan {
    SourceSpan::new(position(begin), position(end))
}

const fn frontend_position(
    byte: u32,
    line: u32,
    column: u32,
) -> FrontendPosition {
    FrontendPosition::new(byte, line, column)
}

const fn frontend_span(
    begin_byte: u32,
    begin_column: u32,
    end_byte: u32,
    end_column: u32,
) -> FrontendSpan {
    FrontendSpan::new(
        frontend_position(begin_byte, 35, begin_column),
        frontend_position(end_byte, 35, end_column),
    )
}

fn frontend_function(
    signature: &str,
    value_type: &str,
    constant_decimal: &str,
) -> FrontendReturnIntegerFunction {
    FrontendReturnIntegerFunction::new(FrontendReturnIntegerFunctionSpec {
        body_span: frontend_span(1222, 16, 1235, 29),
        constant_decimal: String::from(constant_decimal),
        definition: String::from("definition"),
        function_span: frontend_span(1207, 1, 1235, 29),
        inline_specified: false,
        linkage: String::from("external"),
        name: String::from("main"),
        return_span: frontend_span(1224, 18, 1232, 26),
        signature: String::from(signature),
        storage_class: String::from("none"),
        value_span: frontend_span(1231, 25, 1232, 26),
        value_type: String::from(value_type),
    })
}

fn frontend_artifact(
    artifact_id: &str,
    functions: Vec<FrontendReturnIntegerFunction>,
) -> FrontendArtifact {
    FrontendArtifact::new(FrontendArtifactSpec {
        abi_id: String::from(ABI_ID),
        artifact_id: String::from(artifact_id),
        clang_target: String::from("wasm32-unknown-unknown"),
        clang_version: String::from("22.1.8"),
        functions,
        language: String::from("c23"),
        schema_version: 1,
        source_id: String::from(LOWERING_SOURCE_ID),
        source_sha256: LOWERING_SOURCE_HASH,
        target_profile: String::from(PROFILE_ID),
    })
}

fn frontend_return_projection() -> FrontendArtifact {
    frontend_artifact("malbolge-c-frontend-v1", vec![frontend_function(
        "fn()->i32",
        "i32",
        "7",
    )])
}

fn constant(result: u32, value: u8, source_byte: u32) -> LocatedInstruction {
    LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: IntegerConstant::new(32, vec![value, 0, 0, 0]),
            result: ValueId::new(result),
            type_id: I32_TYPE,
        },
        span(source_byte, source_byte.saturating_add(1)),
    )
}

fn typed_constant(
    result: u32,
    type_id: TypeId,
    bytes: [u8; 4],
    source_byte: u32,
) -> LocatedInstruction {
    LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: IntegerConstant::new(32, Vec::from(bytes)),
            result: ValueId::new(result),
            type_id,
        },
        span(source_byte, source_byte.saturating_add(1)),
    )
}

const fn compare(result: u32, source: u32) -> LocatedInstruction {
    LocatedInstruction::new(
        Instruction::Compare {
            left: ValueId::new(0),
            operation: CompareOp::Equal,
            result: ValueId::new(result),
            right: ValueId::new(0),
            type_id: BOOL_TYPE,
        },
        span(source, source.saturating_add(1)),
    )
}

fn entry_block() -> BasicBlock {
    BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![constant(0, 5, 0), compare(1, 1)],
        phis: Vec::new(),
        span: span(0, 4),
        terminator: Terminator::Branch {
            condition: ValueId::new(1),
            false_target: BlockId::new(2),
            true_target: BlockId::new(1),
        },
        terminator_span: span(3, 4),
    })
}

fn left_block() -> BasicBlock {
    BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(1),
        instructions: vec![constant(2, 7, 4)],
        phis: Vec::new(),
        span: span(4, 8),
        terminator: Terminator::Jump { target: BlockId::new(3) },
        terminator_span: span(7, 8),
    })
}

fn right_block() -> BasicBlock {
    BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(2),
        instructions: vec![constant(3, 9, 8)],
        phis: Vec::new(),
        span: span(8, 12),
        terminator: Terminator::Jump { target: BlockId::new(3) },
        terminator_span: span(11, 12),
    })
}

fn merge_block(incoming: Vec<PhiIncoming>) -> BasicBlock {
    BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(3),
        instructions: Vec::new(),
        phis: vec![Phi::new(ValueId::new(4), I32_TYPE, incoming, span(12, 13))],
        span: span(12, 16),
        terminator: Terminator::Return {
            value: Some(ValueId::new(4)),
        },
        terminator_span: span(15, 16),
    })
}

fn valid_incoming() -> Vec<PhiIncoming> {
    vec![
        PhiIncoming::new(BlockId::new(1), ValueId::new(2)),
        PhiIncoming::new(BlockId::new(2), ValueId::new(3)),
    ]
}

fn function_with_identity(
    id: FunctionId,
    name: &str,
    signature: TypeId,
    blocks: Vec<BasicBlock>,
) -> Function {
    Function::new(FunctionSpec {
        blocks,
        entry: BlockId::new(0),
        id,
        name: String::from(name),
        parameters: Vec::new(),
        signature,
        span: span(0, 16),
    })
}

fn function_with_blocks(blocks: Vec<BasicBlock>) -> Function {
    function_with_identity(FUNCTION_ID, "select_value", FUNCTION_TYPE, blocks)
}

fn standard_types() -> Vec<TypeEntry> {
    vec![
        TypeEntry::new(BOOL_TYPE, TypeDef::Bool),
        TypeEntry::new(I32_TYPE, TypeDef::I32),
        TypeEntry::new(
            FUNCTION_TYPE,
            TypeDef::function(Vec::new(), Some(I32_TYPE), false),
        ),
    ]
}

fn module_with_parts(
    source_id: &str,
    types: Vec<TypeEntry>,
    functions: Vec<Function>,
    proofs: Vec<ProofObligation>,
) -> Module {
    Module::new(ModuleSpec {
        abi_id: String::from(ABI_ID),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions,
        globals: Vec::new(),
        proof_obligations: proofs,
        source_id: String::from(source_id),
        source_sha256: SOURCE_HASH,
        target_profile: String::from(PROFILE_ID),
        types,
    })
}

fn module_with_function(function: Function) -> Module {
    module_with_parts(SOURCE_ID, standard_types(), vec![function], Vec::new())
}

fn valid_module() -> Module {
    module_with_function(function_with_blocks(vec![
        entry_block(),
        left_block(),
        right_block(),
        merge_block(valid_incoming()),
    ]))
}

fn single_block(
    instructions: Vec<LocatedInstruction>,
    value: ValueId,
) -> Function {
    function_with_blocks(vec![BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions,
        phis: Vec::new(),
        span: span(0, 8),
        terminator: Terminator::Return { value: Some(value) },
        terminator_span: span(7, 8),
    })])
}

fn module_with_source(source_id: &str) -> Module {
    module_with_parts(
        source_id,
        standard_types(),
        vec![function_with_blocks(vec![
            entry_block(),
            left_block(),
            right_block(),
            merge_block(valid_incoming()),
        ])],
        Vec::new(),
    )
}

fn module_with_proofs(proofs: Vec<ProofObligation>) -> Module {
    module_with_parts(
        SOURCE_ID,
        standard_types(),
        vec![function_with_blocks(vec![
            entry_block(),
            left_block(),
            right_block(),
            merge_block(valid_incoming()),
        ])],
        proofs,
    )
}

#[test]
fn accepted_module_has_deterministic_canonical_identity() {
    let module = valid_module();
    assert_eq!(validate_module(&module), Ok(()));
    let first = canonical_bytes(&module);
    let second = canonical_bytes(&module);
    assert_eq!(first, second);
    assert!(matches!(
        &first,
        Ok(bytes) if bytes.starts_with(b"MCTI\x01\x00")
    ));
}

#[test]
fn duplicate_ssa_definition_fails_closed() {
    let function = single_block(
        vec![constant(0, 1, 0), constant(0, 2, 1)],
        ValueId::new(0),
    );
    assert_eq!(
        validate_module(&module_with_function(function)),
        Err(ValidationError::DuplicateValue)
    );
}

#[test]
fn entry_phi_without_predecessor_fails_closed() {
    let entry = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: Vec::new(),
        phis: vec![Phi::new(ValueId::new(0), I32_TYPE, Vec::new(), span(0, 1))],
        span: span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(0)),
        },
        terminator_span: span(3, 4),
    });
    let function = function_with_blocks(vec![entry]);
    assert_eq!(
        validate_module(&module_with_function(function)),
        Err(ValidationError::PhiPredecessors)
    );
}

#[test]
fn entry_phi_with_backedge_fails_closed() {
    let entry = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![constant(1, 7, 1)],
        phis: vec![Phi::new(
            ValueId::new(0),
            I32_TYPE,
            vec![PhiIncoming::new(BlockId::new(0), ValueId::new(1))],
            span(0, 1),
        )],
        span: span(0, 4),
        terminator: Terminator::Jump { target: BlockId::new(0) },
        terminator_span: span(3, 4),
    });
    let function = function_with_blocks(vec![entry]);
    assert_eq!(
        validate_module(&module_with_function(function)),
        Err(ValidationError::PhiPredecessors)
    );
}

#[test]
fn missing_phi_predecessor_fails_closed() {
    let function = function_with_blocks(vec![
        entry_block(),
        left_block(),
        right_block(),
        merge_block(vec![PhiIncoming::new(BlockId::new(1), ValueId::new(2))]),
    ]);
    assert_eq!(
        validate_module(&module_with_function(function)),
        Err(ValidationError::PhiPredecessors)
    );
}

#[test]
fn phi_value_must_dominate_its_predecessor_edge() {
    let function = function_with_blocks(vec![
        entry_block(),
        left_block(),
        right_block(),
        merge_block(vec![
            PhiIncoming::new(BlockId::new(1), ValueId::new(3)),
            PhiIncoming::new(BlockId::new(2), ValueId::new(3)),
        ]),
    ]);
    assert_eq!(
        validate_module(&module_with_function(function)),
        Err(ValidationError::SsaDominance)
    );
}

#[test]
fn same_block_use_before_definition_fails_closed() {
    let early_compare = LocatedInstruction::new(
        Instruction::Compare {
            left: ValueId::new(1),
            operation: CompareOp::Equal,
            result: ValueId::new(0),
            right: ValueId::new(1),
            type_id: BOOL_TYPE,
        },
        span(0, 1),
    );
    let function =
        single_block(vec![early_compare, constant(1, 5, 1)], ValueId::new(1));
    assert_eq!(
        validate_module(&module_with_function(function)),
        Err(ValidationError::SsaDominance)
    );
}

#[test]
fn unreachable_basic_block_fails_closed() {
    let first = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![constant(0, 1, 0)],
        phis: Vec::new(),
        span: span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(0)),
        },
        terminator_span: span(3, 4),
    });
    let second = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(1),
        instructions: vec![constant(1, 2, 4)],
        phis: Vec::new(),
        span: span(4, 8),
        terminator: Terminator::Return {
            value: Some(ValueId::new(1)),
        },
        terminator_span: span(7, 8),
    });
    assert_eq!(
        validate_module(&module_with_function(function_with_blocks(vec![
            first, second
        ]))),
        Err(ValidationError::Reachability)
    );
}

#[test]
fn call_signature_mismatch_fails_closed() {
    let call = LocatedInstruction::new(
        Instruction::Call {
            arguments: vec![ValueId::new(0)],
            callee: CallTarget::Direct(FUNCTION_ID),
            result: Some((ValueId::new(1), I32_TYPE)),
        },
        span(1, 2),
    );
    let function = single_block(vec![constant(0, 1, 0), call], ValueId::new(1));
    assert_eq!(
        validate_module(&module_with_function(function)),
        Err(ValidationError::CallSignature)
    );
}

#[test]
fn invalid_proof_reference_type_fails_closed() {
    let module = module_with_proofs(vec![ProofObligation::InBounds {
        bytes: 1,
        function: FUNCTION_ID,
        pointer: ValueId::new(0),
    }]);
    assert_eq!(
        validate_module(&module),
        Err(ValidationError::ProofObligation)
    );
}

#[test]
fn invalid_source_identity_blocks_canonicalization() {
    let module = module_with_source("../escape.c");
    assert_eq!(
        validate_module(&module),
        Err(ValidationError::SourceProvenance)
    );
    assert_eq!(
        canonical_bytes(&module),
        Err(CanonicalError::Validation(
            ValidationError::SourceProvenance
        ))
    );
}

#[test]
fn broken_type_reference_fails_closed() {
    let types = vec![TypeEntry::new(
        TypeId::new(0),
        TypeDef::pointer(TypeId::new(9)),
    )];
    let module = module_with_parts(SOURCE_ID, types, Vec::new(), Vec::new());
    assert_eq!(validate_module(&module), Err(ValidationError::TypeTable));
}

#[test]
fn canonical_debug_text_matches_tracked_golden() {
    let observed = canonical_debug_text(&valid_module());
    let expected = read_to_string(GOLDEN_PATH)
        .map(|text| text.lines().collect::<String>())
        .map_err(|_error| CanonicalError::TextFormatting);
    assert_eq!(observed, expected);
}

#[test]
fn branch_condition_must_be_boolean() {
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![constant(0, 1, 0)],
        phis: Vec::new(),
        span: span(0, 4),
        terminator: Terminator::Branch {
            condition: ValueId::new(0),
            false_target: BlockId::new(0),
            true_target: BlockId::new(0),
        },
        terminator_span: span(3, 4),
    });
    let function = function_with_blocks(vec![block]);
    assert_eq!(
        validate_module(&module_with_function(function)),
        Err(ValidationError::ControlType)
    );
}

#[test]
fn boolean_constant_bits_fail_closed() {
    let invalid_boolean = LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: IntegerConstant::new(1, vec![2]),
            result: ValueId::new(0),
            type_id: BOOL_TYPE,
        },
        span(0, 1),
    );
    let function =
        single_block(vec![invalid_boolean, constant(1, 5, 1)], ValueId::new(1));
    assert_eq!(
        validate_module(&module_with_function(function)),
        Err(ValidationError::IntegerConstant)
    );
}

#[test]
fn invalid_load_alignment_fails_closed() {
    let pointer_type = TypeId::new(2);
    let signature_type = TypeId::new(3);
    let types = vec![
        TypeEntry::new(BOOL_TYPE, TypeDef::Bool),
        TypeEntry::new(I32_TYPE, TypeDef::I32),
        TypeEntry::new(pointer_type, TypeDef::pointer(I32_TYPE)),
        TypeEntry::new(
            signature_type,
            TypeDef::function(vec![pointer_type], Some(I32_TYPE), false),
        ),
    ];
    let load = LocatedInstruction::new(
        Instruction::Load {
            alignment: 3,
            pointer: ValueId::new(0),
            result: ValueId::new(1),
            type_id: I32_TYPE,
        },
        span(1, 2),
    );
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![load],
        phis: Vec::new(),
        span: span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(1)),
        },
        terminator_span: span(3, 4),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FUNCTION_ID,
        name: String::from("load_bad_alignment"),
        parameters: vec![Parameter::new(ValueId::new(0), pointer_type)],
        signature: signature_type,
        span: span(0, 4),
    });
    let module =
        module_with_parts(SOURCE_ID, types, vec![function], Vec::new());
    assert_eq!(validate_module(&module), Err(ValidationError::OperandType));
}

fn indirect_call_types() -> Vec<TypeEntry> {
    let i32_type = TypeId::new(0);
    let signature_type = TypeId::new(1);
    vec![
        TypeEntry::new(i32_type, TypeDef::I32),
        TypeEntry::new(
            signature_type,
            TypeDef::function(Vec::new(), Some(i32_type), false),
        ),
        TypeEntry::new(TypeId::new(2), TypeDef::pointer(signature_type)),
        TypeEntry::new(TypeId::new(3), TypeDef::U32),
        TypeEntry::new(TypeId::new(4), TypeDef::pointer(i32_type)),
    ]
}

fn indirect_target_function() -> Function {
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![typed_constant(0, TypeId::new(0), [7, 0, 0, 0], 0)],
        phis: Vec::new(),
        span: span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(0)),
        },
        terminator_span: span(3, 4),
    });
    function_with_identity(FunctionId::new(0), "target", TypeId::new(1), vec![
        block,
    ])
}

fn indirect_dispatch_function() -> Function {
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![
            typed_constant(0, TypeId::new(3), [4, 0, 0, 0], 4),
            LocatedInstruction::new(
                Instruction::AutomaticAllocate {
                    alignment: 4,
                    byte_count: ValueId::new(0),
                    result: ValueId::new(1),
                    type_id: TypeId::new(4),
                },
                span(5, 6),
            ),
            LocatedInstruction::new(
                Instruction::FunctionAddress {
                    function: FunctionId::new(0),
                    result: ValueId::new(2),
                    type_id: TypeId::new(2),
                },
                span(6, 7),
            ),
            LocatedInstruction::new(
                Instruction::Call {
                    arguments: Vec::new(),
                    callee: CallTarget::Indirect(ValueId::new(2)),
                    result: Some((ValueId::new(3), TypeId::new(0))),
                },
                span(7, 8),
            ),
        ],
        phis: Vec::new(),
        span: span(4, 9),
        terminator: Terminator::Return {
            value: Some(ValueId::new(3)),
        },
        terminator_span: span(8, 9),
    });
    function_with_identity(
        FunctionId::new(1),
        "dispatch",
        TypeId::new(1),
        vec![block],
    )
}

fn indirect_call_module() -> Module {
    module_with_parts(
        SOURCE_ID,
        indirect_call_types(),
        vec![indirect_target_function(), indirect_dispatch_function()],
        Vec::new(),
    )
}

#[test]
fn indirect_call_through_function_address_is_admitted() {
    let module = indirect_call_module();
    assert_eq!(validate_module(&module), Ok(()));
    assert!(canonical_bytes(&module).is_ok());
}

#[test]
fn extended_semantics_debug_text_matches_tracked_golden() {
    let observed = canonical_debug_text(&indirect_call_module());
    let expected = read_to_string(EXTENDED_GOLDEN_PATH)
        .map(|text| text.lines().collect::<String>())
        .map_err(|_error| CanonicalError::TextFormatting);
    assert_eq!(observed, expected);
}

#[test]
fn indirect_call_requires_function_pointer_type() {
    let pointer_type = TypeId::new(3);
    let mut types = standard_types();
    types.push(TypeEntry::new(pointer_type, TypeDef::pointer(I32_TYPE)));
    let call = LocatedInstruction::new(
        Instruction::Call {
            arguments: Vec::new(),
            callee: CallTarget::Indirect(ValueId::new(0)),
            result: Some((ValueId::new(1), I32_TYPE)),
        },
        span(1, 2),
    );
    let function = single_block(vec![constant(0, 1, 0), call], ValueId::new(1));
    let module =
        module_with_parts(SOURCE_ID, types, vec![function], Vec::new());
    assert_eq!(
        validate_module(&module),
        Err(ValidationError::CallSignature)
    );
}

#[test]
fn automatic_allocation_with_u32_byte_count_is_admitted() {
    let u32_type = TypeId::new(0);
    let i32_type = TypeId::new(1);
    let pointer_type = TypeId::new(2);
    let signature_type = TypeId::new(3);
    let types = vec![
        TypeEntry::new(u32_type, TypeDef::U32),
        TypeEntry::new(i32_type, TypeDef::I32),
        TypeEntry::new(pointer_type, TypeDef::pointer(i32_type)),
        TypeEntry::new(
            signature_type,
            TypeDef::function(Vec::new(), Some(i32_type), false),
        ),
    ];
    let allocate = LocatedInstruction::new(
        Instruction::AutomaticAllocate {
            alignment: 4,
            byte_count: ValueId::new(0),
            result: ValueId::new(1),
            type_id: pointer_type,
        },
        span(1, 2),
    );
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![
            typed_constant(0, u32_type, [4, 0, 0, 0], 0),
            allocate,
            typed_constant(2, i32_type, [9, 0, 0, 0], 2),
        ],
        phis: Vec::new(),
        span: span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(2)),
        },
        terminator_span: span(3, 4),
    });
    let function =
        function_with_identity(FUNCTION_ID, "allocate", signature_type, vec![
            block,
        ]);
    let module =
        module_with_parts(SOURCE_ID, types, vec![function], Vec::new());
    assert_eq!(validate_module(&module), Ok(()));
}

#[test]
fn automatic_allocation_requires_u32_byte_count() {
    let pointer_type = TypeId::new(3);
    let mut types = standard_types();
    types.push(TypeEntry::new(pointer_type, TypeDef::pointer(I32_TYPE)));
    let allocate = LocatedInstruction::new(
        Instruction::AutomaticAllocate {
            alignment: 4,
            byte_count: ValueId::new(0),
            result: ValueId::new(1),
            type_id: pointer_type,
        },
        span(1, 2),
    );
    let function = single_block(
        vec![constant(0, 4, 0), allocate, constant(2, 7, 2)],
        ValueId::new(2),
    );
    let module =
        module_with_parts(SOURCE_ID, types, vec![function], Vec::new());
    assert_eq!(validate_module(&module), Err(ValidationError::OperandType));
}

#[test]
fn raw_function_typed_ssa_value_fails_closed() {
    let invalid_value = LocatedInstruction::new(
        Instruction::ByteInput {
            result: ValueId::new(0),
            type_id: FUNCTION_TYPE,
        },
        span(0, 1),
    );
    let function =
        single_block(vec![invalid_value, constant(1, 3, 1)], ValueId::new(1));
    assert_eq!(
        validate_module(&module_with_function(function)),
        Err(ValidationError::OperandType)
    );
}

#[test]
fn void_typed_global_fails_closed() {
    let void_type = TypeId::new(0);
    let i32_type = TypeId::new(1);
    let signature_type = TypeId::new(2);
    let types = vec![
        TypeEntry::new(void_type, TypeDef::Void),
        TypeEntry::new(i32_type, TypeDef::I32),
        TypeEntry::new(
            signature_type,
            TypeDef::function(Vec::new(), Some(i32_type), false),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![typed_constant(0, i32_type, [1, 0, 0, 0], 0)],
        phis: Vec::new(),
        span: span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(0)),
        },
        terminator_span: span(3, 4),
    });
    let function =
        function_with_identity(FUNCTION_ID, "main", signature_type, vec![
            block,
        ]);
    let global = Global::new(GlobalSpec {
        id: GlobalId::new(0),
        initializer: None,
        name: String::from("bad"),
        span: span(0, 1),
        type_id: void_type,
    });
    let module = Module::new(ModuleSpec {
        abi_id: String::from(ABI_ID),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![function],
        globals: vec![global],
        proof_obligations: Vec::new(),
        source_id: String::from(SOURCE_ID),
        source_sha256: SOURCE_HASH,
        target_profile: String::from(PROFILE_ID),
        types,
    });
    assert_eq!(
        validate_module(&module),
        Err(ValidationError::GlobalIdentity)
    );
}

#[test]
fn normalized_frontend_return_constant_lowers_with_exact_provenance() {
    let lowered =
        lower_frontend_artifact(&frontend_return_projection()).map(|module| {
            assert_eq!(module.source_id(), LOWERING_SOURCE_ID);
            assert_eq!(module.source_sha256(), &LOWERING_SOURCE_HASH);
            let functions = module.functions();
            assert_eq!(functions.len(), 1);
            let function = functions.first();
            assert_eq!(function.map(Function::name), Some("main"));
            assert_eq!(
                function.map(Function::span),
                Some(SourceSpan::new(
                    SourcePosition::new(1207, 35, 1),
                    SourcePosition::new(1235, 35, 29),
                ))
            );
            let blocks = function.map(Function::blocks).unwrap_or_default();
            let block = blocks.first();
            assert_eq!(
                block.map(BasicBlock::span),
                Some(SourceSpan::new(
                    SourcePosition::new(1222, 35, 16),
                    SourcePosition::new(1235, 35, 29),
                ))
            );
            canonical_debug_text(&module)
        });
    let expected = read_to_string(LOWERING_GOLDEN_PATH)
        .map(|text| text.lines().collect::<String>())
        .map_err(|_error| CanonicalError::TextFormatting);
    assert_eq!(lowered, Ok(expected));
}

#[test]
fn frontend_lowering_rejects_wrong_artifact_identity() {
    let artifact = frontend_artifact("other-frontend", Vec::new());
    assert_eq!(
        lower_frontend_artifact(&artifact),
        Err(FrontendLoweringError::Identity)
    );
}

#[test]
fn frontend_lowering_rejects_unsupported_signature() {
    let artifact =
        frontend_artifact("malbolge-c-frontend-v1", vec![frontend_function(
            "fn()->u32",
            "i32",
            "7",
        )]);
    assert_eq!(
        lower_frontend_artifact(&artifact),
        Err(FrontendLoweringError::UnsupportedSemantics)
    );
}

#[test]
fn frontend_lowering_rejects_out_of_range_i32_constant() {
    let artifact =
        frontend_artifact("malbolge-c-frontend-v1", vec![frontend_function(
            "fn()->i32",
            "i32",
            "2147483648",
        )]);
    assert_eq!(
        lower_frontend_artifact(&artifact),
        Err(FrontendLoweringError::IntegerConstant)
    );
}

fn pointer_bool_module(operation: CastOp) -> Module {
    let bool_type = TypeId::new(0);
    let i32_type = TypeId::new(1);
    let pointer_type = TypeId::new(2);
    let signature_type = TypeId::new(3);
    let types = vec![
        TypeEntry::new(bool_type, TypeDef::Bool),
        TypeEntry::new(i32_type, TypeDef::I32),
        TypeEntry::new(pointer_type, TypeDef::pointer(i32_type)),
        TypeEntry::new(
            signature_type,
            TypeDef::function(vec![pointer_type], Some(bool_type), false),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![LocatedInstruction::new(
            Instruction::Cast {
                operation,
                result: ValueId::new(1),
                type_id: bool_type,
                value: ValueId::new(0),
            },
            span(0, 1),
        )],
        phis: Vec::new(),
        span: span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(1)),
        },
        terminator_span: span(3, 4),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("pointer_truth"),
        parameters: vec![Parameter::new(ValueId::new(0), pointer_type)],
        signature: signature_type,
        span: span(0, 4),
    });
    module_with_parts(SOURCE_ID, types, vec![function], Vec::new())
}

#[test]
fn pointer_to_bool_has_explicit_truth_value_cast() {
    assert_eq!(
        validate_module(&pointer_bool_module(CastOp::PointerToBool)),
        Ok(())
    );
}

#[test]
fn pointer_to_integer_cannot_impersonate_pointer_to_bool() {
    assert_eq!(
        validate_module(&pointer_bool_module(CastOp::PointerToInteger)),
        Err(ValidationError::OperandType)
    );
}

#[test]
fn boolean_arithmetic_fails_closed_before_lowering() {
    let bool_type = TypeId::new(0);
    let signature_type = TypeId::new(1);
    let types = vec![
        TypeEntry::new(bool_type, TypeDef::Bool),
        TypeEntry::new(
            signature_type,
            TypeDef::function(Vec::new(), Some(bool_type), false),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![
            LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(1, vec![1]),
                    result: ValueId::new(0),
                    type_id: bool_type,
                },
                span(0, 1),
            ),
            LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(1, vec![0]),
                    result: ValueId::new(1),
                    type_id: bool_type,
                },
                span(1, 2),
            ),
            LocatedInstruction::new(
                Instruction::Binary {
                    left: ValueId::new(0),
                    operation: BinaryOp::Add,
                    result: ValueId::new(2),
                    right: ValueId::new(1),
                    type_id: bool_type,
                },
                span(2, 3),
            ),
        ],
        phis: Vec::new(),
        span: span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(2)),
        },
        terminator_span: span(3, 4),
    });
    let function = function_with_identity(
        FunctionId::new(0),
        "bad_bool_add",
        signature_type,
        vec![block],
    );
    let module =
        module_with_parts(SOURCE_ID, types, vec![function], Vec::new());
    assert_eq!(validate_module(&module), Err(ValidationError::OperandType));
}

#[test]
fn function_pointer_cannot_satisfy_memory_range_proof() {
    let module = module_with_parts(
        SOURCE_ID,
        indirect_call_types(),
        vec![indirect_target_function(), indirect_dispatch_function()],
        vec![ProofObligation::InBounds {
            bytes: 1,
            function: FunctionId::new(1),
            pointer: ValueId::new(2),
        }],
    );
    assert_eq!(
        validate_module(&module),
        Err(ValidationError::ProofObligation)
    );
}

fn initialized_i32_global_module(initializer: Vec<u8>) -> Module {
    let global = Global::new(GlobalSpec {
        id: GlobalId::new(0),
        initializer: Some(initializer),
        name: String::from("counter"),
        span: span(0, 1),
        type_id: TypeId::new(0),
    });
    Module::new(ModuleSpec {
        abi_id: String::from(ABI_ID),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: Vec::new(),
        globals: vec![global],
        proof_obligations: Vec::new(),
        source_id: String::from(SOURCE_ID),
        source_sha256: SOURCE_HASH,
        target_profile: String::from(PROFILE_ID),
        types: vec![TypeEntry::new(TypeId::new(0), TypeDef::I32)],
    })
}

#[test]
fn initialized_global_requires_exact_abi_object_extent() {
    assert_eq!(
        validate_module(&initialized_i32_global_module(vec![1, 0, 0, 0])),
        Ok(())
    );
    assert_eq!(
        validate_module(&initialized_i32_global_module(vec![1, 0])),
        Err(ValidationError::GlobalIdentity)
    );
}

#[test]
fn by_value_recursive_aggregate_fails_layout_admission() {
    let module = Module::new(ModuleSpec {
        abi_id: String::from(ABI_ID),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: Vec::new(),
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from(SOURCE_ID),
        source_sha256: SOURCE_HASH,
        target_profile: String::from(PROFILE_ID),
        types: vec![TypeEntry::new(
            TypeId::new(0),
            TypeDef::structure(vec![TypeId::new(0)]),
        )],
    });
    assert_eq!(validate_module(&module), Err(ValidationError::TypeTable));
}

#[test]
fn aggregate_layout_overflow_fails_closed() {
    let module = Module::new(ModuleSpec {
        abi_id: String::from(ABI_ID),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: Vec::new(),
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from(SOURCE_ID),
        source_sha256: SOURCE_HASH,
        target_profile: String::from(PROFILE_ID),
        types: vec![
            TypeEntry::new(TypeId::new(0), TypeDef::U64),
            TypeEntry::new(
                TypeId::new(1),
                TypeDef::array(TypeId::new(0), u32::MAX),
            ),
        ],
    });
    assert_eq!(validate_module(&module), Err(ValidationError::TypeTable));
}

#[test]
fn instruction_span_must_be_contained_by_owning_block() {
    let escaped = LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: IntegerConstant::new(32, vec![1, 0, 0, 0]),
            result: ValueId::new(0),
            type_id: I32_TYPE,
        },
        span(8, 9),
    );
    let function = single_block(vec![escaped], ValueId::new(0));
    assert_eq!(
        validate_module(&module_with_function(function)),
        Err(ValidationError::SourceProvenance)
    );
}

fn plain_char_extension_module(operation: CastOp) -> Module {
    let char_type = TypeId::new(0);
    let i32_type = TypeId::new(1);
    let signature_type = TypeId::new(2);
    let types = vec![
        TypeEntry::new(char_type, TypeDef::Char),
        TypeEntry::new(i32_type, TypeDef::I32),
        TypeEntry::new(
            signature_type,
            TypeDef::function(Vec::new(), Some(i32_type), false),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![
            LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![0xff]),
                    result: ValueId::new(0),
                    type_id: char_type,
                },
                span(0, 1),
            ),
            LocatedInstruction::new(
                Instruction::Cast {
                    operation,
                    result: ValueId::new(1),
                    type_id: i32_type,
                    value: ValueId::new(0),
                },
                span(1, 2),
            ),
        ],
        phis: Vec::new(),
        span: span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(1)),
        },
        terminator_span: span(3, 4),
    });
    let function = function_with_identity(
        FunctionId::new(0),
        "plain_char_extension",
        signature_type,
        vec![block],
    );
    module_with_parts(SOURCE_ID, types, vec![function], Vec::new())
}

#[test]
fn plain_char_uses_signed_abi_extension_semantics() {
    assert_eq!(
        validate_module(&plain_char_extension_module(CastOp::SignExtend)),
        Ok(())
    );
}

#[test]
fn plain_char_rejects_unsigned_extension_semantics() {
    assert_eq!(
        validate_module(&plain_char_extension_module(CastOp::ZeroExtend)),
        Err(ValidationError::OperandType)
    );
}

#[test]
fn void_pointer_bitcasts_within_object_pointer_namespace() {
    let void_type = TypeId::new(0);
    let i32_type = TypeId::new(1);
    let void_pointer = TypeId::new(2);
    let object_pointer = TypeId::new(3);
    let signature_type = TypeId::new(4);
    let types = vec![
        TypeEntry::new(void_type, TypeDef::Void),
        TypeEntry::new(i32_type, TypeDef::I32),
        TypeEntry::new(void_pointer, TypeDef::pointer(void_type)),
        TypeEntry::new(object_pointer, TypeDef::pointer(i32_type)),
        TypeEntry::new(
            signature_type,
            TypeDef::function(vec![void_pointer], Some(object_pointer), false),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::Bitcast,
                result: ValueId::new(1),
                type_id: object_pointer,
                value: ValueId::new(0),
            },
            span(0, 1),
        )],
        phis: Vec::new(),
        span: span(0, 3),
        terminator: Terminator::Return {
            value: Some(ValueId::new(1)),
        },
        terminator_span: span(2, 3),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("void_to_object_pointer"),
        parameters: vec![Parameter::new(ValueId::new(0), void_pointer)],
        signature: signature_type,
        span: span(0, 3),
    });
    let module =
        module_with_parts(SOURCE_ID, types, vec![function], Vec::new());
    assert_eq!(validate_module(&module), Ok(()));
}

#[test]
fn object_pointer_cannot_bitcast_to_function_pointer() {
    let i32_type = TypeId::new(0);
    let target_signature = TypeId::new(1);
    let function_pointer = TypeId::new(2);
    let object_pointer = TypeId::new(3);
    let caller_signature = TypeId::new(4);
    let types = vec![
        TypeEntry::new(i32_type, TypeDef::I32),
        TypeEntry::new(
            target_signature,
            TypeDef::function(Vec::new(), Some(i32_type), false),
        ),
        TypeEntry::new(function_pointer, TypeDef::pointer(target_signature)),
        TypeEntry::new(object_pointer, TypeDef::pointer(i32_type)),
        TypeEntry::new(
            caller_signature,
            TypeDef::function(vec![object_pointer], Some(i32_type), false),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![
            LocatedInstruction::new(
                Instruction::Cast {
                    operation: CastOp::Bitcast,
                    result: ValueId::new(1),
                    type_id: function_pointer,
                    value: ValueId::new(0),
                },
                span(0, 1),
            ),
            typed_constant(2, i32_type, [1, 0, 0, 0], 1),
        ],
        phis: Vec::new(),
        span: span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(2)),
        },
        terminator_span: span(3, 4),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("object_to_function_pointer"),
        parameters: vec![Parameter::new(ValueId::new(0), object_pointer)],
        signature: caller_signature,
        span: span(0, 4),
    });
    let module =
        module_with_parts(SOURCE_ID, types, vec![function], Vec::new());
    assert_eq!(validate_module(&module), Err(ValidationError::OperandType));
}

#[test]
fn function_pointer_cannot_cast_to_integer_encoding() {
    let i32_type = TypeId::new(0);
    let signature = TypeId::new(1);
    let function_pointer = TypeId::new(2);
    let types = vec![
        TypeEntry::new(i32_type, TypeDef::I32),
        TypeEntry::new(
            signature,
            TypeDef::function(Vec::new(), Some(i32_type), false),
        ),
        TypeEntry::new(function_pointer, TypeDef::pointer(signature)),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![
            LocatedInstruction::new(
                Instruction::FunctionAddress {
                    function: FunctionId::new(0),
                    result: ValueId::new(0),
                    type_id: function_pointer,
                },
                span(0, 1),
            ),
            LocatedInstruction::new(
                Instruction::Cast {
                    operation: CastOp::PointerToInteger,
                    result: ValueId::new(1),
                    type_id: i32_type,
                    value: ValueId::new(0),
                },
                span(1, 2),
            ),
            typed_constant(2, i32_type, [1, 0, 0, 0], 2),
        ],
        phis: Vec::new(),
        span: span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(2)),
        },
        terminator_span: span(3, 4),
    });
    let function = function_with_identity(
        FunctionId::new(0),
        "function_pointer_to_integer",
        signature,
        vec![block],
    );
    let module =
        module_with_parts(SOURCE_ID, types, vec![function], Vec::new());
    assert_eq!(validate_module(&module), Err(ValidationError::OperandType));
}

#[test]
fn integer_cannot_forge_function_pointer_identity() {
    let i32_type = TypeId::new(0);
    let signature = TypeId::new(1);
    let function_pointer = TypeId::new(2);
    let types = vec![
        TypeEntry::new(i32_type, TypeDef::I32),
        TypeEntry::new(
            signature,
            TypeDef::function(Vec::new(), Some(i32_type), false),
        ),
        TypeEntry::new(function_pointer, TypeDef::pointer(signature)),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![
            typed_constant(0, i32_type, [1, 0, 0, 0], 0),
            LocatedInstruction::new(
                Instruction::Cast {
                    operation: CastOp::IntegerToPointer,
                    result: ValueId::new(1),
                    type_id: function_pointer,
                    value: ValueId::new(0),
                },
                span(1, 2),
            ),
            typed_constant(2, i32_type, [1, 0, 0, 0], 2),
        ],
        phis: Vec::new(),
        span: span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(2)),
        },
        terminator_span: span(3, 4),
    });
    let function = function_with_identity(
        FunctionId::new(0),
        "integer_to_function_pointer",
        signature,
        vec![block],
    );
    let module =
        module_with_parts(SOURCE_ID, types, vec![function], Vec::new());
    assert_eq!(validate_module(&module), Err(ValidationError::OperandType));
}

fn scalar_cast_parameter_module(
    source_definition: TypeDef,
    destination_definition: TypeDef,
    operation: CastOp,
) -> Module {
    let source_type = TypeId::new(0);
    let destination_type = TypeId::new(1);
    let signature_type = TypeId::new(2);
    let types = vec![
        TypeEntry::new(source_type, source_definition),
        TypeEntry::new(destination_type, destination_definition),
        TypeEntry::new(
            signature_type,
            TypeDef::function(vec![source_type], Some(destination_type), false),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![LocatedInstruction::new(
            Instruction::Cast {
                operation,
                result: ValueId::new(1),
                type_id: destination_type,
                value: ValueId::new(0),
            },
            span(0, 1),
        )],
        phis: Vec::new(),
        span: span(0, 3),
        terminator: Terminator::Return {
            value: Some(ValueId::new(1)),
        },
        terminator_span: span(2, 3),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("scalar_cast_parameter"),
        parameters: vec![Parameter::new(ValueId::new(0), source_type)],
        signature: signature_type,
        span: span(0, 3),
    });
    module_with_parts(SOURCE_ID, types, vec![function], Vec::new())
}

#[test]
fn bool_to_signed_is_the_explicit_integer_promotion() {
    let module = scalar_cast_parameter_module(
        TypeDef::Bool,
        TypeDef::I32,
        CastOp::BoolToSigned,
    );
    assert_eq!(validate_module(&module), Ok(()));
}

#[test]
fn integer_truncation_cannot_impersonate_bool_conversion() {
    let module = scalar_cast_parameter_module(
        TypeDef::I32,
        TypeDef::Bool,
        CastOp::Truncate,
    );
    assert_eq!(validate_module(&module), Err(ValidationError::OperandType));
}

#[test]
fn bool_cannot_zero_extend_as_unsigned_integer() {
    let module = scalar_cast_parameter_module(
        TypeDef::Bool,
        TypeDef::U32,
        CastOp::ZeroExtend,
    );
    assert_eq!(validate_module(&module), Err(ValidationError::OperandType));
}

#[test]
fn bool_cannot_use_unsigned_to_float_conversion() {
    let module = scalar_cast_parameter_module(
        TypeDef::Bool,
        TypeDef::F64,
        CastOp::UnsignedToFloat,
    );
    assert_eq!(validate_module(&module), Err(ValidationError::OperandType));
}

#[test]
fn bool_relational_compare_requires_integer_promotion() {
    let bool_type = TypeId::new(0);
    let signature_type = TypeId::new(1);
    let types = vec![
        TypeEntry::new(bool_type, TypeDef::Bool),
        TypeEntry::new(
            signature_type,
            TypeDef::function(
                vec![bool_type, bool_type],
                Some(bool_type),
                false,
            ),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![LocatedInstruction::new(
            Instruction::Compare {
                left: ValueId::new(0),
                operation: CompareOp::LessUnsigned,
                result: ValueId::new(2),
                right: ValueId::new(1),
                type_id: bool_type,
            },
            span(0, 1),
        )],
        phis: Vec::new(),
        span: span(0, 3),
        terminator: Terminator::Return {
            value: Some(ValueId::new(2)),
        },
        terminator_span: span(2, 3),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("bool_relational_compare"),
        parameters: vec![
            Parameter::new(ValueId::new(0), bool_type),
            Parameter::new(ValueId::new(1), bool_type),
        ],
        signature: signature_type,
        span: span(0, 3),
    });
    let module =
        module_with_parts(SOURCE_ID, types, vec![function], Vec::new());
    assert_eq!(validate_module(&module), Err(ValidationError::OperandType));
}

fn variadic_target(i32_type: TypeId, signature_type: TypeId) -> Function {
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: Vec::new(),
        phis: Vec::new(),
        span: span(0, 2),
        terminator: Terminator::Return {
            value: Some(ValueId::new(0)),
        },
        terminator_span: span(1, 2),
    });
    Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("variadic_target"),
        parameters: vec![Parameter::new(ValueId::new(0), i32_type)],
        signature: signature_type,
        span: span(0, 2),
    })
}

fn variadic_invoker(
    i32_type: TypeId,
    argument_type: TypeId,
    signature_type: TypeId,
) -> Function {
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![
            typed_constant(1, i32_type, [7, 0, 0, 0], 2),
            LocatedInstruction::new(
                Instruction::Call {
                    arguments: vec![ValueId::new(1), ValueId::new(0)],
                    callee: CallTarget::Direct(FunctionId::new(0)),
                    result: Some((ValueId::new(2), i32_type)),
                },
                span(3, 4),
            ),
        ],
        phis: Vec::new(),
        span: span(2, 6),
        terminator: Terminator::Return {
            value: Some(ValueId::new(2)),
        },
        terminator_span: span(5, 6),
    });
    Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(1),
        name: String::from("variadic_invoker"),
        parameters: vec![Parameter::new(ValueId::new(0), argument_type)],
        signature: signature_type,
        span: span(2, 6),
    })
}

fn variadic_argument_module(argument_definition: TypeDef) -> Module {
    let i32_type = TypeId::new(0);
    let argument_type = TypeId::new(1);
    let target_signature = TypeId::new(2);
    let invoker_signature = TypeId::new(3);
    let types = vec![
        TypeEntry::new(i32_type, TypeDef::I32),
        TypeEntry::new(argument_type, argument_definition),
        TypeEntry::new(
            target_signature,
            TypeDef::function(vec![i32_type], Some(i32_type), true),
        ),
        TypeEntry::new(
            invoker_signature,
            TypeDef::function(vec![argument_type], Some(i32_type), false),
        ),
    ];
    module_with_parts(
        SOURCE_ID,
        types,
        vec![
            variadic_target(i32_type, target_signature),
            variadic_invoker(i32_type, argument_type, invoker_signature),
        ],
        Vec::new(),
    )
}

#[test]
fn variadic_bool_requires_default_argument_promotion() {
    assert_eq!(
        validate_module(&variadic_argument_module(TypeDef::Bool)),
        Err(ValidationError::CallSignature)
    );
}

#[test]
fn variadic_small_integer_requires_default_argument_promotion() {
    assert_eq!(
        validate_module(&variadic_argument_module(TypeDef::U16)),
        Err(ValidationError::CallSignature)
    );
}

#[test]
fn variadic_float_requires_default_argument_promotion() {
    assert_eq!(
        validate_module(&variadic_argument_module(TypeDef::F32)),
        Err(ValidationError::CallSignature)
    );
}

#[test]
fn variadic_promoted_integer_is_admitted() {
    assert_eq!(
        validate_module(&variadic_argument_module(TypeDef::I32)),
        Ok(())
    );
}

#[test]
fn variadic_promoted_float_is_admitted() {
    assert_eq!(
        validate_module(&variadic_argument_module(TypeDef::F64)),
        Ok(())
    );
}

#[test]
fn function_signature_rejects_array_parameter_before_adjustment() {
    let i32_type = TypeId::new(0);
    let array_type = TypeId::new(1);
    let signature_type = TypeId::new(2);
    let module = module_with_parts(
        SOURCE_ID,
        vec![
            TypeEntry::new(i32_type, TypeDef::I32),
            TypeEntry::new(array_type, TypeDef::array(i32_type, 4)),
            TypeEntry::new(
                signature_type,
                TypeDef::function(vec![array_type], Some(i32_type), false),
            ),
        ],
        Vec::new(),
        Vec::new(),
    );
    assert_eq!(validate_module(&module), Err(ValidationError::TypeTable));
}

#[test]
fn function_signature_rejects_array_result() {
    let i32_type = TypeId::new(0);
    let array_type = TypeId::new(1);
    let signature_type = TypeId::new(2);
    let module = module_with_parts(
        SOURCE_ID,
        vec![
            TypeEntry::new(i32_type, TypeDef::I32),
            TypeEntry::new(array_type, TypeDef::array(i32_type, 4)),
            TypeEntry::new(
                signature_type,
                TypeDef::function(Vec::new(), Some(array_type), false),
            ),
        ],
        Vec::new(),
        Vec::new(),
    );
    assert_eq!(validate_module(&module), Err(ValidationError::TypeTable));
}

fn switch_selector_module(selector_definition: TypeDef) -> Module {
    let selector_type = TypeId::new(0);
    let signature_type = TypeId::new(1);
    let types = vec![
        TypeEntry::new(selector_type, selector_definition),
        TypeEntry::new(
            signature_type,
            TypeDef::function(vec![selector_type], Some(selector_type), false),
        ),
    ];
    let entry = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: Vec::new(),
        phis: Vec::new(),
        span: span(0, 2),
        terminator: Terminator::Switch {
            cases: Vec::new(),
            default_target: BlockId::new(1),
            selector: ValueId::new(0),
        },
        terminator_span: span(1, 2),
    });
    let exit = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(1),
        instructions: Vec::new(),
        phis: Vec::new(),
        span: span(2, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(0)),
        },
        terminator_span: span(3, 4),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![entry, exit],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("switch_selector"),
        parameters: vec![Parameter::new(ValueId::new(0), selector_type)],
        signature: signature_type,
        span: span(0, 4),
    });
    module_with_parts(SOURCE_ID, types, vec![function], Vec::new())
}

#[test]
fn switch_bool_requires_integer_promotion() {
    assert_eq!(
        validate_module(&switch_selector_module(TypeDef::Bool)),
        Err(ValidationError::ControlType)
    );
}

#[test]
fn switch_small_integer_requires_integer_promotion() {
    assert_eq!(
        validate_module(&switch_selector_module(TypeDef::U16)),
        Err(ValidationError::ControlType)
    );
}

#[test]
fn switch_promoted_integer_is_admitted() {
    assert_eq!(
        validate_module(&switch_selector_module(TypeDef::I32)),
        Ok(())
    );
}

fn promoted_binary_parameter_module(
    operand_definition: TypeDef,
    operation: BinaryOp,
) -> Module {
    let operand_type = TypeId::new(0);
    let signature_type = TypeId::new(1);
    let types = vec![
        TypeEntry::new(operand_type, operand_definition),
        TypeEntry::new(
            signature_type,
            TypeDef::function(
                vec![operand_type, operand_type],
                Some(operand_type),
                false,
            ),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![LocatedInstruction::new(
            Instruction::Binary {
                left: ValueId::new(0),
                operation,
                result: ValueId::new(2),
                right: ValueId::new(1),
                type_id: operand_type,
            },
            span(0, 1),
        )],
        phis: Vec::new(),
        span: span(0, 3),
        terminator: Terminator::Return {
            value: Some(ValueId::new(2)),
        },
        terminator_span: span(2, 3),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("promoted_binary_parameter"),
        parameters: vec![
            Parameter::new(ValueId::new(0), operand_type),
            Parameter::new(ValueId::new(1), operand_type),
        ],
        signature: signature_type,
        span: span(0, 3),
    });
    module_with_parts(SOURCE_ID, types, vec![function], Vec::new())
}

fn promoted_compare_parameter_module(
    operand_definition: TypeDef,
    operation: CompareOp,
) -> Module {
    let operand_type = TypeId::new(0);
    let bool_type = TypeId::new(1);
    let signature_type = TypeId::new(2);
    let types = vec![
        TypeEntry::new(operand_type, operand_definition),
        TypeEntry::new(bool_type, TypeDef::Bool),
        TypeEntry::new(
            signature_type,
            TypeDef::function(
                vec![operand_type, operand_type],
                Some(bool_type),
                false,
            ),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![LocatedInstruction::new(
            Instruction::Compare {
                left: ValueId::new(0),
                operation,
                result: ValueId::new(2),
                right: ValueId::new(1),
                type_id: bool_type,
            },
            span(0, 1),
        )],
        phis: Vec::new(),
        span: span(0, 3),
        terminator: Terminator::Return {
            value: Some(ValueId::new(2)),
        },
        terminator_span: span(2, 3),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("promoted_compare_parameter"),
        parameters: vec![
            Parameter::new(ValueId::new(0), operand_type),
            Parameter::new(ValueId::new(1), operand_type),
        ],
        signature: signature_type,
        span: span(0, 3),
    });
    module_with_parts(SOURCE_ID, types, vec![function], Vec::new())
}

#[test]
fn small_signed_arithmetic_requires_integer_promotion() {
    assert_eq!(
        validate_module(&promoted_binary_parameter_module(
            TypeDef::I16,
            BinaryOp::Add,
        )),
        Err(ValidationError::OperandType)
    );
}

#[test]
fn small_unsigned_shift_requires_integer_promotion() {
    assert_eq!(
        validate_module(&promoted_binary_parameter_module(
            TypeDef::U8,
            BinaryOp::ShiftLeft,
        )),
        Err(ValidationError::OperandType)
    );
}

#[test]
fn promoted_integer_arithmetic_is_admitted() {
    assert_eq!(
        validate_module(&promoted_binary_parameter_module(
            TypeDef::I32,
            BinaryOp::Add,
        )),
        Ok(())
    );
}

#[test]
fn plain_char_equality_requires_integer_promotion() {
    assert_eq!(
        validate_module(&promoted_compare_parameter_module(
            TypeDef::Char,
            CompareOp::Equal,
        )),
        Err(ValidationError::OperandType)
    );
}

#[test]
fn small_unsigned_relational_requires_integer_promotion() {
    assert_eq!(
        validate_module(&promoted_compare_parameter_module(
            TypeDef::U16,
            CompareOp::LessUnsigned,
        )),
        Err(ValidationError::OperandType)
    );
}

#[test]
fn promoted_integer_relational_is_admitted() {
    assert_eq!(
        validate_module(&promoted_compare_parameter_module(
            TypeDef::I32,
            CompareOp::LessSigned,
        )),
        Ok(())
    );
}

fn overflow_proof_module(operation: BinaryOp, proof_result: ValueId) -> Module {
    let i32_type = TypeId::new(0);
    let signature_type = TypeId::new(1);
    let types = vec![
        TypeEntry::new(i32_type, TypeDef::I32),
        TypeEntry::new(
            signature_type,
            TypeDef::function(vec![i32_type, i32_type], Some(i32_type), false),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![LocatedInstruction::new(
            Instruction::Binary {
                left: ValueId::new(0),
                operation,
                result: ValueId::new(2),
                right: ValueId::new(1),
                type_id: i32_type,
            },
            span(0, 1),
        )],
        phis: Vec::new(),
        span: span(0, 3),
        terminator: Terminator::Return {
            value: Some(ValueId::new(2)),
        },
        terminator_span: span(2, 3),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("overflow_proof"),
        parameters: vec![
            Parameter::new(ValueId::new(0), i32_type),
            Parameter::new(ValueId::new(1), i32_type),
        ],
        signature: signature_type,
        span: span(0, 3),
    });
    module_with_parts(SOURCE_ID, types, vec![function], vec![
        ProofObligation::NoSignedOverflow {
            function: FunctionId::new(0),
            result: proof_result,
        },
    ])
}

#[test]
fn signed_add_result_accepts_overflow_obligation() {
    assert_eq!(
        validate_module(
            &overflow_proof_module(BinaryOp::Add, ValueId::new(2),)
        ),
        Ok(())
    );
}

#[test]
fn signed_parameter_cannot_impersonate_overflow_result() {
    assert_eq!(
        validate_module(
            &overflow_proof_module(BinaryOp::Add, ValueId::new(0),)
        ),
        Err(ValidationError::ProofObligation)
    );
}

#[test]
fn bitwise_result_cannot_carry_overflow_obligation() {
    assert_eq!(
        validate_module(
            &overflow_proof_module(BinaryOp::And, ValueId::new(2),)
        ),
        Err(ValidationError::ProofObligation)
    );
}

fn pointer_integer_width_module(integer_definition: TypeDef) -> Module {
    let i32_type = TypeId::new(0);
    let integer_type = TypeId::new(1);
    let pointer_type = TypeId::new(2);
    let signature_type = TypeId::new(3);
    let types = vec![
        TypeEntry::new(i32_type, TypeDef::I32),
        TypeEntry::new(integer_type, integer_definition),
        TypeEntry::new(pointer_type, TypeDef::pointer(i32_type)),
        TypeEntry::new(
            signature_type,
            TypeDef::function(vec![pointer_type], Some(integer_type), false),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::PointerToInteger,
                result: ValueId::new(1),
                type_id: integer_type,
                value: ValueId::new(0),
            },
            span(0, 1),
        )],
        phis: Vec::new(),
        span: span(0, 3),
        terminator: Terminator::Return {
            value: Some(ValueId::new(1)),
        },
        terminator_span: span(2, 3),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("pointer_integer_width"),
        parameters: vec![Parameter::new(ValueId::new(0), pointer_type)],
        signature: signature_type,
        span: span(0, 3),
    });
    module_with_parts(SOURCE_ID, types, vec![function], Vec::new())
}

fn integer_pointer_width_module(integer_definition: TypeDef) -> Module {
    let i32_type = TypeId::new(0);
    let integer_type = TypeId::new(1);
    let pointer_type = TypeId::new(2);
    let signature_type = TypeId::new(3);
    let types = vec![
        TypeEntry::new(i32_type, TypeDef::I32),
        TypeEntry::new(integer_type, integer_definition),
        TypeEntry::new(pointer_type, TypeDef::pointer(i32_type)),
        TypeEntry::new(
            signature_type,
            TypeDef::function(vec![integer_type], Some(pointer_type), false),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::IntegerToPointer,
                result: ValueId::new(1),
                type_id: pointer_type,
                value: ValueId::new(0),
            },
            span(0, 1),
        )],
        phis: Vec::new(),
        span: span(0, 3),
        terminator: Terminator::Return {
            value: Some(ValueId::new(1)),
        },
        terminator_span: span(2, 3),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("integer_pointer_width"),
        parameters: vec![Parameter::new(ValueId::new(0), integer_type)],
        signature: signature_type,
        span: span(0, 3),
    });
    module_with_parts(SOURCE_ID, types, vec![function], Vec::new())
}

#[test]
fn pointer_integer_conversion_preserves_32_bit_encoding() {
    assert_eq!(
        validate_module(&pointer_integer_width_module(TypeDef::U32)),
        Ok(())
    );
    assert_eq!(
        validate_module(&integer_pointer_width_module(TypeDef::I32)),
        Ok(())
    );
}

#[test]
fn pointer_integer_conversion_rejects_narrow_encoding() {
    assert_eq!(
        validate_module(&pointer_integer_width_module(TypeDef::U16)),
        Err(ValidationError::OperandType)
    );
    assert_eq!(
        validate_module(&integer_pointer_width_module(TypeDef::I16)),
        Err(ValidationError::OperandType)
    );
}

#[test]
fn pointer_integer_conversion_rejects_implicit_widening() {
    assert_eq!(
        validate_module(&pointer_integer_width_module(TypeDef::U64)),
        Err(ValidationError::OperandType)
    );
    assert_eq!(
        validate_module(&integer_pointer_width_module(TypeDef::I64)),
        Err(ValidationError::OperandType)
    );
}
