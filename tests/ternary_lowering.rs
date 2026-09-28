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
//   - Integration evidence for the first typed-IR-to-ternary lowering slice.
// - Must-Not:
//   - Claim layout, Malbolge encoding, or unsupported typed-IR semantics.
// - Allows:
//   - Inputs: tracked canonical typed-IR golden modules.
//   - Outputs: deterministic target-model and fail-closed assertions.
//   - Side effects: fixture reads only.
// - Split-When:
//   - Another lowering family needs an independent integration harness.
// - Merge-When:
//   - Another test owns this exact typed-IR-to-ternary evidence.
// - Summary:
//   - Proves exact `i32` constant-return ternary lowering.
// - Description:
//   - Checks projection, bit preservation, provenance, and unsupported
//     rejection.
// - Usage:
//   - Run through Cargo or repository Jig validation.
// - Defaults:
//   - Only the tracked first lowering golden is accepted by this slice.
//

//! Integration tests for the first pre-layout ternary lowering slice.

#[path = "../src/compiler/ternary-lowering/composition/lib.rs"]
pub mod ternary_lowering;
#[path = "../src/compiler/typed-ir/composition/lib.rs"]
pub mod typed_ir;

use std::fs::read_to_string;
use std::str::from_utf8;

use malbolge::{current_profile, decode_profile_instruction};
use ternary_lowering::{
    I32_TERNARY_TRITS, InputBlock, InputFunction, InputInstruction,
    InputScalarType, InputSourcePosition, InputSourceSpan, InputTerminator,
    MachineIoEncodingError, MachineIoKind, MachineIoOperation,
    ProfileInstructionDecoder, RuntimeIntrinsicLoweringError,
    RuntimeIntrinsicOperation, RuntimeIntrinsicRequest,
    RuntimeIoRealizationError, StartupAction, StartupPlanningError,
    StartupRequest, TargetProfileIo, TernaryLoweringError, TernaryOperation,
    TypedIrInput, encode_machine_io, lower_runtime_intrinsic, lower_typed_ir,
    plan_startup, realize_runtime_io,
};
use typed_ir::{
    BasicBlock, BasicBlockSpec, BinaryOp, BlockId, CastOp, Function,
    FunctionId, FunctionSpec, Instruction, IntegerConstant, LocatedInstruction,
    Module, ModuleSpec, SourcePosition, SourceSpan, TYPED_IR_CODEC_ID,
    Terminator, TypeDef, TypeEntry, TypeId, ValueId, canonical_bytes,
    canonical_module, validate_module,
};

const RETURN_GOLDEN: &str =
    "tests/compiler/typed-ir/golden/ir-return-constant.hex";
const SELECT_GOLDEN: &str = "tests/compiler/typed-ir/golden/select.hex";
const BYTE_IO_SOURCE_HASH: [u8; 32] = [0x6b; 32];
const LOW_BYTE_SOURCE_HASH: [u8; 32] = [0x7c; 32];
const GUEST_INTRINSICS_HEADER: &str =
    "src/runtime/guest-runtime/contract/guest_intrinsics.h";
const GUEST_RUNTIME_CONTRACT: &str =
    "src/runtime/guest-runtime/contract/guest-runtime-v1.json";
const GUEST_RUNTIME_HEADER: &str =
    "src/runtime/guest-runtime/contract/guest_runtime.h";

struct VmProfileInstructionDecoder;

impl ProfileInstructionDecoder for VmProfileInstructionDecoder {
    fn decode(&self, cell: u32, code_pointer: u32) -> Option<u8> {
        decode_profile_instruction(cell, code_pointer)
    }
}

struct AmbiguousInstructionDecoder;

impl ProfileInstructionDecoder for AmbiguousInstructionDecoder {
    fn decode(&self, _cell: u32, _code_pointer: u32) -> Option<u8> {
        Some(current_profile().input_instruction())
    }
}

struct MissingInstructionDecoder;

impl ProfileInstructionDecoder for MissingInstructionDecoder {
    fn decode(&self, _cell: u32, _code_pointer: u32) -> Option<u8> {
        None
    }
}

fn valid_startup_request() -> StartupRequest {
    StartupRequest {
        abi_id: String::from("malbolge-c32-v1"),
        arena_pointer: 0x101,
        bind_identity: String::from("malbolge_guest_runtime_bind_heap"),
        capacity: 0x100,
        target_profile: String::from("malbolge-2026"),
        user_entry_function: 7,
    }
}

fn admitted_byte_io_fixture() -> Result<Module, String> {
    let module = byte_io_module();
    validate_module(&module)
        .map_err(|error| format!("validate byte-I/O fixture: {error:?}"))?;
    let bytes = canonical_bytes(&module)
        .map_err(|error| format!("canonicalize byte-I/O fixture: {error:?}"))?;
    let restored = canonical_module(&bytes)
        .map_err(|error| format!("restore byte-I/O fixture: {error:?}"))?;
    if restored != module {
        return Err(String::from("byte-I/O canonical round trip drifted"));
    }
    Ok(restored)
}

fn admitted_low_byte_fixture() -> Result<Module, String> {
    let module = low_byte_module();
    validate_module(&module)
        .map_err(|error| format!("validate low-byte fixture: {error:?}"))?;
    let bytes = canonical_bytes(&module)
        .map_err(|error| format!("canonicalize low-byte fixture: {error:?}"))?;
    let restored = canonical_module(&bytes)
        .map_err(|error| format!("restore low-byte fixture: {error:?}"))?;
    if restored != module {
        return Err(String::from("low-byte canonical round trip drifted"));
    }
    Ok(restored)
}

fn admitted_golden(path: &str) -> Result<Module, String> {
    let bytes = canonical_golden(path)?;
    canonical_module(&bytes)
        .map_err(|error| format!("admit typed IR: {error:?}"))
}

fn assert_byte_io_program(
    module: &Module,
    program: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    assert_program_provenance(module, program)?;
    let function = program
        .functions
        .first()
        .ok_or_else(|| String::from("byte-I/O lowering emitted no function"))?;
    if function.operations.len() != 4 {
        return Err(String::from("unexpected byte-I/O operation count"));
    }
    assert_byte_input(function)?;
    assert_byte_output(function)?;
    assert_byte_return_materialization(function)?;
    assert_byte_return(function)
}

fn assert_byte_input(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function
        .operations
        .first()
        .ok_or_else(|| String::from("missing byte input operation"))?;
    let TernaryOperation::ByteInput { result, span } = operation else {
        return Err(String::from("first byte-I/O operation is not input"));
    };
    if *result != 0 || *span != output_span(fixture_span(0, 1)) {
        return Err(String::from("byte input lowering drifted"));
    }
    Ok(())
}

fn assert_byte_output(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function
        .operations
        .get(1)
        .ok_or_else(|| String::from("missing byte output operation"))?;
    let TernaryOperation::ByteOutput { span, value } = operation else {
        return Err(String::from("second byte-I/O operation is not output"));
    };
    if *value != 0 || *span != output_span(fixture_span(1, 2)) {
        return Err(String::from("byte output lowering drifted"));
    }
    Ok(())
}

fn assert_byte_return(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function
        .operations
        .get(3)
        .ok_or_else(|| String::from("missing byte-I/O return"))?;
    let TernaryOperation::Return { span, value } = operation else {
        return Err(String::from("fourth byte-I/O operation is not return"));
    };
    if *value != 1 || *span != output_span(fixture_span(3, 4)) {
        return Err(String::from("byte-I/O return lowering drifted"));
    }
    Ok(())
}

fn assert_byte_return_materialization(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function.operations.get(2).ok_or_else(|| {
        String::from("missing byte-I/O return materialization")
    })?;
    let TernaryOperation::MaterializeI32 { result, scalar, span } = operation
    else {
        return Err(String::from(
            "third byte-I/O operation is not i32 materialization",
        ));
    };
    if *result != 1
        || scalar.bits() != 0
        || *span != output_span(fixture_span(2, 3))
    {
        return Err(String::from("byte-I/O return materialization drifted"));
    }
    Ok(())
}

fn assert_constant_return_program(
    module: &Module,
    program: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    assert_program_provenance(module, program)?;
    let function = program
        .functions
        .first()
        .ok_or_else(|| String::from("lowering emitted no function"))?;
    if function.operations.len() != 2 {
        return Err(String::from("unexpected ternary operation count"));
    }
    assert_materialize(module, function)?;
    assert_return(module, function)
}

fn assert_materialize(
    module: &Module,
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let materialize = function
        .operations
        .first()
        .ok_or_else(|| String::from("missing ternary materialization"))?;
    let TernaryOperation::MaterializeI32 { result, scalar, span } = materialize
    else {
        return Err(String::from("first operation is not i32 materialization"));
    };
    let input_function = module
        .functions()
        .first()
        .ok_or_else(|| String::from("typed IR has no function"))?;
    let input_instruction = input_function
        .blocks()
        .first()
        .and_then(|block| block.instructions().first())
        .ok_or_else(|| String::from("typed IR has no instruction"))?;
    if *result != 0
        || scalar.bits() != 7
        || scalar.trits().len() != I32_TERNARY_TRITS
        || scalar.trits().first() != Some(&1)
        || scalar.trits().get(1) != Some(&2)
        || scalar.trits().iter().any(|trit| *trit > 2)
        || *span != output_span(input_instruction.span())
    {
        return Err(String::from("i32 ternary materialization drifted"));
    }
    Ok(())
}

fn assert_program_provenance(
    module: &Module,
    program: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    let function = program.functions.first();
    let input_function = module.functions().first();
    if program.abi_id != module.abi_id()
        || program.input_format_version != module.format_version()
        || program.source_id != module.source_id()
        || program.source_sha256 != *module.source_sha256()
        || program.target_profile != module.target_profile()
        || program.functions.len() != 1
        || function.map(|value| value.span)
            != input_function.map(|value| output_span(value.span()))
    {
        return Err(String::from("ternary program provenance drifted"));
    }
    Ok(())
}

fn assert_return(
    module: &Module,
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let returned = function
        .operations
        .get(1)
        .ok_or_else(|| String::from("missing ternary return"))?;
    let TernaryOperation::Return { span, value } = returned else {
        return Err(String::from("second operation is not return"));
    };
    let input_span = module
        .functions()
        .first()
        .and_then(|input_function| input_function.blocks().first())
        .map(|block| output_span(block.terminator_span()))
        .ok_or_else(|| String::from("typed IR has no return block"))?;
    if *value != 0 || *span != input_span {
        return Err(String::from(
            "return operation did not use materialized value",
        ));
    }
    Ok(())
}

const fn output_span(span: SourceSpan) -> ternary_lowering::TernarySourceSpan {
    let begin = span.begin();
    let end = span.end();
    ternary_lowering::TernarySourceSpan {
        begin: ternary_lowering::TernarySourcePosition {
            byte: begin.byte(),
            column: begin.column(),
            line: begin.line(),
        },
        end: ternary_lowering::TernarySourcePosition {
            byte: end.byte(),
            column: end.column(),
            line: end.line(),
        },
    }
}

fn byte_io_module() -> Module {
    let u8_type = TypeId::new(0);
    let i32_type = TypeId::new(1);
    let function_type = TypeId::new(2);
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![
            LocatedInstruction::new(
                Instruction::ByteInput {
                    result: ValueId::new(0),
                    type_id: u8_type,
                },
                fixture_span(0, 1),
            ),
            LocatedInstruction::new(
                Instruction::ByteOutput { value: ValueId::new(0) },
                fixture_span(1, 2),
            ),
            LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(32, vec![0, 0, 0, 0]),
                    result: ValueId::new(1),
                    type_id: i32_type,
                },
                fixture_span(2, 3),
            ),
        ],
        phis: Vec::new(),
        span: fixture_span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(1)),
        },
        terminator_span: fixture_span(3, 4),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("byte_round_trip"),
        parameters: Vec::new(),
        signature: function_type,
        span: fixture_span(0, 4),
    });
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![function],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/byte-io.c"),
        source_sha256: BYTE_IO_SOURCE_HASH,
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(u8_type, TypeDef::U8),
            TypeEntry::new(i32_type, TypeDef::I32),
            TypeEntry::new(
                function_type,
                TypeDef::function(Vec::new(), Some(i32_type), false),
            ),
        ],
    })
}

fn low_byte_module() -> Module {
    let u8_type = TypeId::new(0);
    let i32_type = TypeId::new(1);
    let function_type = TypeId::new(2);
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: low_byte_instructions(u8_type, i32_type),
        phis: Vec::new(),
        span: fixture_span(0, 6),
        terminator: Terminator::Return {
            value: Some(ValueId::new(2)),
        },
        terminator_span: fixture_span(5, 6),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("low_byte"),
        parameters: Vec::new(),
        signature: function_type,
        span: fixture_span(0, 6),
    });
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![function],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/low-byte.c"),
        source_sha256: LOW_BYTE_SOURCE_HASH,
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(u8_type, TypeDef::U8),
            TypeEntry::new(i32_type, TypeDef::I32),
            TypeEntry::new(
                function_type,
                TypeDef::function(Vec::new(), Some(i32_type), false),
            ),
        ],
    })
}

fn low_byte_instructions(
    u8_type: TypeId,
    i32_type: TypeId,
) -> Vec<LocatedInstruction> {
    vec![
        low_byte_constant(0xffff_ffff, 0, 0, i32_type),
        low_byte_constant(0xff, 1, 1, i32_type),
        LocatedInstruction::new(
            Instruction::Binary {
                left: ValueId::new(0),
                operation: BinaryOp::And,
                result: ValueId::new(2),
                right: ValueId::new(1),
                type_id: i32_type,
            },
            fixture_span(2, 3),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::Truncate,
                result: ValueId::new(3),
                type_id: u8_type,
                value: ValueId::new(2),
            },
            fixture_span(3, 4),
        ),
        LocatedInstruction::new(
            Instruction::ByteOutput { value: ValueId::new(3) },
            fixture_span(4, 5),
        ),
    ]
}

fn low_byte_constant(
    bits: u32,
    result: u32,
    span_begin: u32,
    type_id: TypeId,
) -> LocatedInstruction {
    LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: IntegerConstant::new(32, Vec::from(bits.to_le_bytes())),
            result: ValueId::new(result),
            type_id,
        },
        fixture_span(span_begin, span_begin.saturating_add(1)),
    )
}

const fn fixture_position(byte: u32) -> SourcePosition {
    SourcePosition::new(byte, 1, byte.saturating_add(1))
}

const fn fixture_span(begin: u32, end: u32) -> SourceSpan {
    SourceSpan::new(fixture_position(begin), fixture_position(end))
}

fn canonical_golden(path: &str) -> Result<Vec<u8>, String> {
    let text = read_to_string(path)
        .map_err(|error| format!("read golden: {error}"))?;
    let compact = text.lines().collect::<String>();
    let payload = compact
        .strip_prefix(TYPED_IR_CODEC_ID)
        .and_then(|value| value.strip_prefix(':'))
        .ok_or_else(|| String::from("typed-IR golden prefix mismatch"))?;
    let (pairs, remainder) = payload.as_bytes().as_chunks::<2>();
    if !remainder.is_empty() {
        return Err(String::from("typed-IR golden has odd hex length"));
    }
    pairs
        .iter()
        .map(|pair| {
            from_utf8(pair)
                .map_err(|error| format!("golden UTF-8: {error}"))
                .and_then(|value| {
                    u8::from_str_radix(value, 16)
                        .map_err(|error| format!("golden hex: {error}"))
                })
        })
        .collect()
}

fn input_block(module: &Module, block: &BasicBlock) -> InputBlock {
    InputBlock {
        id: block.id().value(),
        instructions: block
            .instructions()
            .iter()
            .map(|instruction| input_instruction(module, instruction))
            .collect(),
        phi_count: block.phis().len(),
        terminator: input_terminator(block),
    }
}

fn input_function(module: &Module, function: &Function) -> InputFunction {
    InputFunction {
        blocks: function
            .blocks()
            .iter()
            .map(|block| input_block(module, block))
            .collect(),
        entry: function.entry().value(),
        id: function.id().value(),
        name: String::from(function.name()),
        parameter_count: function.parameters().len(),
        span: input_span(function.span()),
    }
}

fn input_instruction(
    module: &Module,
    instruction: &LocatedInstruction,
) -> InputInstruction {
    if let Instruction::Binary {
        left,
        operation: BinaryOp::And,
        result,
        right,
        type_id,
    } = instruction.instruction()
    {
        return InputInstruction::BinaryAnd {
            left: left.value(),
            result: result.value(),
            right: right.value(),
            span: input_span(instruction.span()),
            type_kind: input_scalar_type(module, *type_id),
        };
    }
    if let Instruction::ByteInput { result, type_id } =
        instruction.instruction()
    {
        return InputInstruction::ByteInput {
            result: result.value(),
            span: input_span(instruction.span()),
            type_kind: input_scalar_type(module, *type_id),
        };
    }
    if let Instruction::ByteOutput { value } = instruction.instruction() {
        return InputInstruction::ByteOutput {
            span: input_span(instruction.span()),
            value: value.value(),
        };
    }
    if let Instruction::ConstantInteger {
        constant,
        result,
        type_id,
    } = instruction.instruction()
    {
        return InputInstruction::ConstantInteger {
            bit_width: constant.bit_width(),
            little_endian: Vec::from(constant.little_endian()),
            result: result.value(),
            span: input_span(instruction.span()),
            type_kind: input_scalar_type(module, *type_id),
        };
    }
    if let Instruction::Cast {
        operation: CastOp::Truncate,
        result,
        type_id,
        value,
    } = instruction.instruction()
    {
        return InputInstruction::TruncateInteger {
            result: result.value(),
            span: input_span(instruction.span()),
            type_kind: input_scalar_type(module, *type_id),
            value: value.value(),
        };
    }
    InputInstruction::Unsupported
}

fn input_scalar_type(module: &Module, type_id: TypeId) -> InputScalarType {
    let Some(index) = usize::try_from(type_id.value()).ok() else {
        return InputScalarType::Other;
    };
    let Some(entry) = module.types().get(index) else {
        return InputScalarType::Other;
    };
    if entry.id() != type_id {
        return InputScalarType::Other;
    }
    match entry.definition() {
        TypeDef::I32 => InputScalarType::I32,
        TypeDef::U8 => InputScalarType::U8,
        TypeDef::Array { .. }
        | TypeDef::Bool
        | TypeDef::Char
        | TypeDef::F128
        | TypeDef::F32
        | TypeDef::F64
        | TypeDef::Function { .. }
        | TypeDef::I16
        | TypeDef::I64
        | TypeDef::I8
        | TypeDef::Pointer { .. }
        | TypeDef::Struct { .. }
        | TypeDef::U16
        | TypeDef::U32
        | TypeDef::U64
        | TypeDef::Union { .. }
        | TypeDef::Void => InputScalarType::Other,
    }
}

const fn input_span(span: SourceSpan) -> InputSourceSpan {
    let begin = span.begin();
    let end = span.end();
    InputSourceSpan {
        begin: InputSourcePosition {
            byte: begin.byte(),
            column: begin.column(),
            line: begin.line(),
        },
        end: InputSourcePosition {
            byte: end.byte(),
            column: end.column(),
            line: end.line(),
        },
    }
}

fn input_terminator(block: &BasicBlock) -> InputTerminator {
    if let Terminator::Return { value } = block.terminator() {
        return InputTerminator::Return {
            span: input_span(block.terminator_span()),
            value: (*value).map(ValueId::value),
        };
    }
    InputTerminator::Unsupported
}

fn project_typed_ir(module: &Module) -> Result<TypedIrInput, String> {
    validate_module(module).map_err(|error| {
        format!("validate typed IR before projection: {error:?}")
    })?;
    Ok(TypedIrInput {
        abi_id: String::from(module.abi_id()),
        functions: module
            .functions()
            .iter()
            .map(|function| input_function(module, function))
            .collect(),
        global_count: module.globals().len(),
        input_format_version: module.format_version(),
        proof_obligation_count: module.proof_obligations().len(),
        source_id: String::from(module.source_id()),
        source_sha256: *module.source_sha256(),
        target_profile: String::from(module.target_profile()),
    })
}

fn projected_byte_io_fixture() -> Result<TypedIrInput, String> {
    let module = admitted_byte_io_fixture()?;
    project_typed_ir(&module)
}

fn projected_low_byte_fixture() -> Result<TypedIrInput, String> {
    let module = admitted_low_byte_fixture()?;
    project_typed_ir(&module)
}

#[test]
fn byte_input_requires_u8_projection() -> Result<(), String> {
    let mut input = projected_byte_io_fixture()?;
    let instruction = input
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.first_mut())
        .ok_or_else(|| String::from("byte-I/O projection has no input"))?;
    let InputInstruction::ByteInput { type_kind, .. } = instruction else {
        return Err(String::from("first projection instruction is not input"));
    };
    *type_kind = InputScalarType::Other;
    if lower_typed_ir(&input)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("non-u8 byte input was not rejected"));
    }
    Ok(())
}

#[test]
fn byte_output_requires_prior_byte_definition() -> Result<(), String> {
    let mut input = projected_byte_io_fixture()?;
    let instruction = input
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(1))
        .ok_or_else(|| String::from("byte-I/O projection has no output"))?;
    let InputInstruction::ByteOutput { value, .. } = instruction else {
        return Err(String::from(
            "second projection instruction is not output",
        ));
    };
    *value = 99;
    if lower_typed_ir(&input)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("undefined byte output was not rejected"));
    }
    Ok(())
}

#[test]
fn duplicate_projection_value_ids_fail_closed() -> Result<(), String> {
    let mut input = projected_byte_io_fixture()?;
    let instruction = input
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(2))
        .ok_or_else(|| String::from("byte-I/O projection has no constant"))?;
    let InputInstruction::ConstantInteger { result, .. } = instruction else {
        return Err(String::from(
            "third projection instruction is not constant",
        ));
    };
    *result = 0;
    if lower_typed_ir(&input) != Err(TernaryLoweringError::InvalidProjection) {
        return Err(String::from(
            "duplicate projection SSA ID was not rejected",
        ));
    }
    Ok(())
}

#[test]
fn low_byte_and_rejects_projection_drift() -> Result<(), String> {
    let input = projected_low_byte_fixture()?;
    let mut wrong_type = input.clone();
    let instruction = wrong_type
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(2))
        .ok_or_else(|| String::from("low-byte projection has no AND"))?;
    let InputInstruction::BinaryAnd { type_kind, .. } = instruction else {
        return Err(String::from("low-byte projection AND is missing"));
    };
    *type_kind = InputScalarType::Other;
    if lower_typed_ir(&wrong_type)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("non-i32 AND projection was not rejected"));
    }
    let mut undefined = input;
    let undefined_instruction = undefined
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(2))
        .ok_or_else(|| String::from("low-byte projection has no AND"))?;
    let InputInstruction::BinaryAnd { right, .. } = undefined_instruction
    else {
        return Err(String::from("low-byte projection AND is missing"));
    };
    *right = 99;
    if lower_typed_ir(&undefined)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("undefined AND operand was not rejected"));
    }
    Ok(())
}

#[test]
fn low_byte_truncate_rejects_projection_drift() -> Result<(), String> {
    let input = projected_low_byte_fixture()?;
    let mut wrong_type = input.clone();
    let instruction = wrong_type
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(3))
        .ok_or_else(|| String::from("low-byte projection has no truncate"))?;
    let InputInstruction::TruncateInteger { type_kind, .. } = instruction
    else {
        return Err(String::from("low-byte projection truncate is missing"));
    };
    *type_kind = InputScalarType::I32;
    if lower_typed_ir(&wrong_type)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("non-u8 truncation result was not rejected"));
    }
    let mut undefined = input;
    let undefined_instruction = undefined
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(3))
        .ok_or_else(|| String::from("low-byte projection has no truncate"))?;
    let InputInstruction::TruncateInteger { value, .. } = undefined_instruction
    else {
        return Err(String::from("low-byte projection truncate is missing"));
    };
    *value = 99;
    if lower_typed_ir(&undefined)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from(
            "undefined truncation source was not rejected",
        ));
    }
    Ok(())
}

#[test]
fn i32_constant_return_lowers_to_exact_ternary_bits() -> Result<(), String> {
    let module = admitted_golden(RETURN_GOLDEN)?;
    let input = project_typed_ir(&module)?;
    let first = lower_typed_ir(&input)
        .map_err(|error| format!("lower typed IR projection: {error:?}"))?;
    let second = lower_typed_ir(&input)
        .map_err(|error| format!("repeat typed IR lowering: {error:?}"))?;
    if first != second {
        return Err(String::from("ternary lowering is not deterministic"));
    }
    assert_constant_return_program(&module, &first)
}

#[test]
fn byte_io_effects_lower_after_canonical_typed_ir_round_trip()
-> Result<(), String> {
    let module = admitted_byte_io_fixture()?;
    let input = project_typed_ir(&module)?;
    let first = lower_typed_ir(&input)
        .map_err(|error| format!("lower byte-I/O projection: {error:?}"))?;
    let second = lower_typed_ir(&input)
        .map_err(|error| format!("repeat byte-I/O lowering: {error:?}"))?;
    if first != second {
        return Err(String::from("byte-I/O lowering is not deterministic"));
    }
    assert_byte_io_program(&module, &first)
}

fn assert_low_byte_and(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function
        .operations
        .get(2)
        .ok_or_else(|| String::from("missing low-byte AND"))?;
    let TernaryOperation::AndI32 {
        left,
        result,
        right,
        span,
    } = operation
    else {
        return Err(String::from("low-byte path did not lower bitwise AND"));
    };
    if (*left, *result, *right) != (0, 2, 1)
        || *span != output_span(fixture_span(2, 3))
    {
        return Err(String::from("low-byte AND operands drifted"));
    }
    Ok(())
}

fn assert_low_byte_output(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function
        .operations
        .get(4)
        .ok_or_else(|| String::from("missing low-byte output"))?;
    if *operation
        != (TernaryOperation::ByteOutput {
            span: output_span(fixture_span(4, 5)),
            value: 3,
        })
    {
        return Err(String::from("low-byte output did not consume u8 result"));
    }
    Ok(())
}

fn assert_low_byte_truncate(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function
        .operations
        .get(3)
        .ok_or_else(|| String::from("missing low-byte truncation"))?;
    let TernaryOperation::TruncateI32ToU8 {
        result: truncate_result,
        span: truncate_span,
        value: truncate_value,
    } = operation
    else {
        return Err(String::from("low-byte path did not lower truncation"));
    };
    if (*truncate_result, *truncate_value) != (3, 2)
        || *truncate_span != output_span(fixture_span(3, 4))
    {
        return Err(String::from("low-byte truncation operands drifted"));
    }
    Ok(())
}

#[test]
fn low_byte_helper_path_round_trips_and_lowers() -> Result<(), String> {
    let module = admitted_low_byte_fixture()?;
    let input = project_typed_ir(&module)?;
    let program = lower_typed_ir(&input)
        .map_err(|error| format!("lower low-byte projection: {error:?}"))?;
    assert_program_provenance(&module, &program)?;
    let function = program
        .functions
        .first()
        .ok_or_else(|| String::from("low-byte lowering emitted no function"))?;
    if function.operations.len() != 6 {
        return Err(String::from("unexpected low-byte operation count"));
    }
    assert_low_byte_and(function)?;
    assert_low_byte_truncate(function)?;
    assert_low_byte_output(function)
}

#[test]
fn i32_ternary_scalar_width_is_minimal() -> Result<(), String> {
    let patterns = 1u64 << 32u32;
    if 3u64.pow(20) >= patterns || 3u64.pow(21) < patterns {
        return Err(String::from(
            "21 trits is not the minimal complete 32-bit scalar width",
        ));
    }
    Ok(())
}

#[test]
fn i32_ternary_scalars_preserve_extreme_bit_patterns() -> Result<(), String> {
    for bits in [0u32, 1, 0x7fff_ffff, 0x8000_0000, u32::MAX] {
        let scalar = ternary_lowering::TernaryI32Scalar::from_bits(bits);
        if scalar.bits() != bits || scalar.trits().iter().any(|trit| *trit > 2)
        {
            return Err(format!("ternary scalar round trip failed for {bits}"));
        }
    }
    Ok(())
}

#[test]
fn malformed_constant_projection_fails_closed() -> Result<(), String> {
    let module = admitted_golden(RETURN_GOLDEN)?;
    let mut input = project_typed_ir(&module)?;
    let Some(function) = input.functions.first_mut() else {
        return Err(String::from("projection has no function"));
    };
    let Some(block) = function.blocks.first_mut() else {
        return Err(String::from("projection has no block"));
    };
    let Some(instruction) = block.instructions.first_mut() else {
        return Err(String::from("projection has no instruction"));
    };
    let InputInstruction::ConstantInteger { little_endian, .. } = instruction
    else {
        return Err(String::from("projection constant is missing"));
    };
    let _: Option<u8> = little_endian.pop();
    if lower_typed_ir(&input)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("truncated constant was not rejected"));
    }
    Ok(())
}

#[test]
fn projection_identity_drift_fails_closed() -> Result<(), String> {
    let module = admitted_golden(RETURN_GOLDEN)?;
    let mut input = project_typed_ir(&module)?;
    input.target_profile = String::from("other-profile");
    if lower_typed_ir(&input) != Err(TernaryLoweringError::InvalidProjection) {
        return Err(String::from("target profile drift was not rejected"));
    }
    Ok(())
}

#[test]
fn startup_plan_binds_heap_before_user_entry() -> Result<(), String> {
    let request = valid_startup_request();
    let first = plan_startup(&request)
        .map_err(|error| format!("plan startup: {error:?}"))?;
    let second = plan_startup(&request)
        .map_err(|error| format!("repeat startup plan: {error:?}"))?;
    if first != second
        || first.bind_identity != "malbolge_guest_runtime_bind_heap"
        || first.actions
            != vec![
                StartupAction::BindHeap {
                    arena_pointer: 0x101,
                    capacity: 0x100,
                },
                StartupAction::EnterUserCode { function: 7 },
            ]
    {
        return Err(String::from("startup bind-before-entry plan drifted"));
    }
    Ok(())
}

#[test]
fn startup_plan_rejects_identity_drift() -> Result<(), String> {
    for mutate in 0u8..3u8 {
        let mut request = valid_startup_request();
        match mutate {
            0 => request.abi_id = String::from("host-abi"),
            1 => request.bind_identity = String::from("malloc"),
            _ => request.target_profile = String::from("malbolge-2026.3"),
        }
        if plan_startup(&request) != Err(StartupPlanningError::InvalidIdentity)
        {
            return Err(format!(
                "startup identity drift {mutate} was accepted"
            ));
        }
    }
    Ok(())
}

#[test]
fn startup_plan_rejects_invalid_heap_layout() -> Result<(), String> {
    for (arena_pointer, capacity) in [
        (0u32, 0x100u32),
        (0x102, 0x100),
        (0x101, 16),
        (0x101, 33),
        (0xffff_fff1, 32),
    ] {
        let mut request = valid_startup_request();
        request.arena_pointer = arena_pointer;
        request.capacity = capacity;
        if plan_startup(&request) != Err(StartupPlanningError::InvalidLayout) {
            return Err(format!(
                "invalid heap layout {arena_pointer:#x}/{capacity} accepted",
            ));
        }
    }
    Ok(())
}

#[test]
fn startup_authority_matches_guest_runtime_contract() -> Result<(), String> {
    let contract = read_to_string(GUEST_RUNTIME_CONTRACT)
        .map_err(|error| format!("read guest-runtime contract: {error}"))?;
    let header = read_to_string(GUEST_RUNTIME_HEADER)
        .map_err(|error| format!("read guest-runtime header: {error}"))?;
    for expected in [
        "\"heap_binding\": \"one-shot\"",
        "\"alignment\": 16",
        "\"header_bytes\": 16",
    ] {
        if !contract.contains(expected) {
            return Err(format!(
                "runtime startup authority missing {expected}"
            ));
        }
    }
    if !header.contains("malbolge_guest_runtime_bind_heap")
        || !header.contains("MALBOLGE_GUEST_HEAP_ALIGNMENT UINT32_C(16)")
        || !header.contains("MALBOLGE_GUEST_HEAP_HEADER_SIZE UINT32_C(16)")
    {
        return Err(String::from("guest-runtime startup header drifted"));
    }
    Ok(())
}

#[test]
fn runtime_intrinsic_identities_match_guest_runtime_authority()
-> Result<(), String> {
    let contract = read_to_string(GUEST_RUNTIME_CONTRACT)
        .map_err(|error| format!("read guest-runtime contract: {error}"))?;
    let header = read_to_string(GUEST_INTRINSICS_HEADER)
        .map_err(|error| format!("read guest intrinsic header: {error}"))?;
    for expected in [
        "malbolge_guest_intrinsic_input_word",
        "malbolge_guest_intrinsic_output_byte",
    ] {
        if !contract.contains(expected) || !header.contains(expected) {
            return Err(format!(
                "runtime intrinsic authority missing {expected}"
            ));
        }
    }
    if !contract.contains("\"target_profile\": \"malbolge-2026\"") {
        return Err(String::from("guest-runtime target profile drifted"));
    }
    Ok(())
}

fn current_profile_io() -> TargetProfileIo {
    let profile = current_profile();
    TargetProfileIo {
        eof_word: profile.eof_word(),
        input_instruction: profile.input_instruction(),
        output_instruction: profile.output_instruction(),
        profile_id: String::from(profile.id()),
    }
}

#[test]
fn machine_io_cells_round_trip_every_decode_phase() -> Result<(), String> {
    let projection = current_profile_io();
    let decoder = VmProfileInstructionDecoder;
    for code_pointer in 0u32..94u32 {
        for semantic in [
            RuntimeIntrinsicOperation::InputWord,
            RuntimeIntrinsicOperation::OutputByte,
        ] {
            let operation = realize_runtime_io(semantic, &projection)
                .map_err(|error| format!("realize machine I/O: {error:?}"))?;
            let encoded = encode_machine_io(operation, code_pointer, &decoder)
                .map_err(|error| format!("encode machine I/O: {error:?}"))?;
            if !(33..=126).contains(&encoded.source_cell)
                || encoded.code_pointer != code_pointer
                || encoded.operation != operation
                || decoder.decode(u32::from(encoded.source_cell), code_pointer)
                    != Some(operation.instruction)
            {
                return Err(format!(
                    "machine I/O round trip drifted at phase {code_pointer}",
                ));
            }
        }
    }
    Ok(())
}

#[test]
fn machine_io_encoder_rejects_broken_decoder_ports() -> Result<(), String> {
    let operation = realize_runtime_io(
        RuntimeIntrinsicOperation::InputWord,
        &current_profile_io(),
    )
    .map_err(|error| format!("realize machine I/O: {error:?}"))?;
    if encode_machine_io(operation, 0, &MissingInstructionDecoder)
        != Err(MachineIoEncodingError::MissingEncoding)
    {
        return Err(String::from("missing inverse encoding was not rejected"));
    }
    if encode_machine_io(operation, 0, &AmbiguousInstructionDecoder)
        != Err(MachineIoEncodingError::AmbiguousEncoding)
    {
        return Err(String::from(
            "ambiguous inverse encoding was not rejected",
        ));
    }
    Ok(())
}

#[test]
fn current_profile_realizes_runtime_io_from_authority() -> Result<(), String> {
    let profile = current_profile();
    let projection = current_profile_io();
    let input =
        realize_runtime_io(RuntimeIntrinsicOperation::InputWord, &projection)
            .map_err(|error| format!("realize input word: {error:?}"))?;
    let output =
        realize_runtime_io(RuntimeIntrinsicOperation::OutputByte, &projection)
            .map_err(|error| format!("realize output byte: {error:?}"))?;
    if input
        != (MachineIoOperation {
            eof_word: Some(profile.eof_word()),
            instruction: profile.input_instruction(),
            kind: MachineIoKind::InputWord,
        })
        || output
            != (MachineIoOperation {
                eof_word: None,
                instruction: profile.output_instruction(),
                kind: MachineIoKind::OutputByte,
            })
    {
        return Err(String::from(
            "profile-derived machine I/O realization drifted",
        ));
    }
    Ok(())
}

#[test]
fn malformed_profile_io_projection_fails_closed() -> Result<(), String> {
    let mut projection = current_profile_io();
    projection.output_instruction = projection.input_instruction;
    if realize_runtime_io(RuntimeIntrinsicOperation::InputWord, &projection)
        != Err(RuntimeIoRealizationError::InvalidProjection)
    {
        return Err(String::from(
            "colliding profile opcodes were not rejected",
        ));
    }
    projection = current_profile_io();
    projection.profile_id = String::from("malbolge-1998");
    if realize_runtime_io(RuntimeIntrinsicOperation::OutputByte, &projection)
        != Err(RuntimeIoRealizationError::UnsupportedProfile)
    {
        return Err(String::from("profile identity drift was not rejected"));
    }
    Ok(())
}

#[test]
fn raw_byte_io_intrinsic_identities_lower_exactly() -> Result<(), String> {
    let input = RuntimeIntrinsicRequest {
        identity: String::from("malbolge_guest_intrinsic_input_word"),
        target_profile: String::from("malbolge-2026"),
    };
    let output = RuntimeIntrinsicRequest {
        identity: String::from("malbolge_guest_intrinsic_output_byte"),
        target_profile: String::from("malbolge-2026"),
    };
    if lower_runtime_intrinsic(&input)
        != Ok(RuntimeIntrinsicOperation::InputWord)
        || lower_runtime_intrinsic(&output)
            != Ok(RuntimeIntrinsicOperation::OutputByte)
    {
        return Err(String::from(
            "runtime intrinsic identity lowering drifted",
        ));
    }
    Ok(())
}

#[test]
fn raw_intrinsic_identity_or_profile_drift_fails_closed() -> Result<(), String>
{
    let unknown = RuntimeIntrinsicRequest {
        identity: String::from("host_getchar"),
        target_profile: String::from("malbolge-2026"),
    };
    let wrong_profile = RuntimeIntrinsicRequest {
        identity: String::from("malbolge_guest_intrinsic_input_word"),
        target_profile: String::from("malbolge-1998"),
    };
    if lower_runtime_intrinsic(&unknown)
        != Err(RuntimeIntrinsicLoweringError::UnsupportedIdentity)
        || lower_runtime_intrinsic(&wrong_profile)
            != Err(RuntimeIntrinsicLoweringError::UnsupportedProfile)
    {
        return Err(String::from("runtime intrinsic drift was not rejected"));
    }
    Ok(())
}

#[test]
fn returning_byte_value_as_i32_fails_closed() -> Result<(), String> {
    let mut input = projected_byte_io_fixture()?;
    let block = input
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .ok_or_else(|| String::from("byte-I/O projection has no block"))?;
    let InputTerminator::Return { value, .. } = &mut block.terminator else {
        return Err(String::from("byte-I/O projection has no return"));
    };
    *value = Some(0);
    if lower_typed_ir(&input)
        != Err(TernaryLoweringError::UnsupportedTerminator)
    {
        return Err(String::from("byte value return was not rejected"));
    }
    Ok(())
}

#[test]
fn unsupported_typed_ir_shape_fails_closed() -> Result<(), String> {
    let module = admitted_golden(SELECT_GOLDEN)?;
    let input = project_typed_ir(&module)?;
    let observed = lower_typed_ir(&input);
    if !matches!(
        observed,
        Err(TernaryLoweringError::UnsupportedFunction
            | TernaryLoweringError::UnsupportedInstruction
            | TernaryLoweringError::UnsupportedModule)
    ) {
        return Err(format!(
            "unsupported typed IR was not rejected: {observed:?}"
        ));
    }
    Ok(())
}
