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
//   - Validation-gated canonical bytes and deterministic typed-IR debug text.
// - Must-Not:
//   - Serialize invalid IR, Rust enum discriminants, host widths, or debug
//     layout.
// - Allows:
//   - Inputs: one complete typed-IR module accepted by version-one validation.
//   - Outputs: stable little-endian bytes and lowercase-hex debug identity
//     text.
//   - Side effects: returned byte/string allocation only.
// - Split-When:
//   - A new IR wire version requires independently reviewed encoding semantics.
// - Merge-When:
//   - Validation and serialization become one inseparable application
//     lifecycle.
// - Summary:
//   - Emits canonical typed-IR identity only after complete fail-closed
//     admission.
// - Description:
//   - Every enum uses explicit versioned tags rather than Rust representation.
// - Usage:
//   - Used by compiler tests, caches, manifests, and downstream compiler
//     stages.
// - Defaults:
//   - Variable lengths are canonical u32 and overflow rejects serialization.
//

//! Validation-gated canonical encoding and debug identity for typed compiler
//! IR.

use std::fmt::Write as _;

use super::control::{BasicBlock, Phi, SwitchCase, Terminator};
use super::error::ValidationError;
use super::ids::{TypeId, ValueId};
use super::instruction::{
    BinaryOp, CallTarget, CastOp, CompareOp, Instruction, IntegerConstant,
    LocatedInstruction,
};
use super::module::{Function, Global, Module, ProofObligation};
use super::source::{SourcePosition, SourceSpan};
use super::types::{TypeDef, TypeEntry};
use super::validate::validate_module;

const MAGIC: &[u8; 4] = b"MCTI";
const DEBUG_PREFIX: &str = "malbolge-typed-ir-v1:";

/// Canonical typed-IR serialization failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CanonicalError {
    /// A variable-length field cannot fit the canonical unsigned 32-bit length.
    LengthOverflow,
    /// Deterministic debug-text formatting failed.
    TextFormatting,
    /// Complete typed-IR admission rejected the module before serialization.
    Validation(ValidationError),
}

impl From<ValidationError> for CanonicalError {
    fn from(error: ValidationError) -> Self {
        Self::Validation(error)
    }
}
struct Encoder {
    bytes: Vec<u8>,
}

impl Encoder {
    fn bytes(&mut self, value: &[u8]) -> Result<(), CanonicalError> {
        self.length(value.len())?;
        self.raw(value);
        Ok(())
    }

    fn finish(self) -> Vec<u8> {
        self.bytes
    }

    fn length(&mut self, value: usize) -> Result<(), CanonicalError> {
        let encoded = u32::try_from(value)
            .map_err(|_error| CanonicalError::LengthOverflow)?;
        self.u32(encoded);
        Ok(())
    }

    const fn new() -> Self {
        Self { bytes: Vec::new() }
    }

    fn raw(&mut self, value: &[u8]) {
        self.bytes.extend_from_slice(value);
    }

    fn string(&mut self, value: &str) -> Result<(), CanonicalError> {
        self.bytes(value.as_bytes())
    }

    fn u16(&mut self, value: u16) {
        self.raw(&value.to_le_bytes());
    }

    fn u32(&mut self, value: u32) {
        self.raw(&value.to_le_bytes());
    }

    fn u8(&mut self, value: u8) {
        self.bytes.push(value);
    }
}

/// Returns canonical version-one typed-IR identity bytes.
///
/// # Errors
///
/// Returns [`CanonicalError::Validation`] for malformed IR or
/// [`CanonicalError::LengthOverflow`] when a variable-length field exceeds u32.
pub fn canonical_bytes(module: &Module) -> Result<Vec<u8>, CanonicalError> {
    validate_module(module)?;
    let mut encoder = Encoder::new();
    encoder.raw(MAGIC);
    encoder.u16(module.format_version());
    encoder.string(module.abi_id())?;
    encoder.string(module.target_profile())?;
    encoder.string(module.source_id())?;
    encoder.raw(module.source_sha256());
    encode_types(&mut encoder, module.types())?;
    encode_globals(&mut encoder, module.globals())?;
    encode_functions(&mut encoder, module.functions())?;
    encode_proofs(&mut encoder, module.proof_obligations())?;
    Ok(encoder.finish())
}

/// Returns deterministic lowercase-hex debug identity for canonical bytes.
///
/// # Errors
///
/// Returns the same validation/length failures as [`canonical_bytes`] plus
/// [`CanonicalError::TextFormatting`] if writing to the debug string fails.
pub fn canonical_debug_text(module: &Module) -> Result<String, CanonicalError> {
    let bytes = canonical_bytes(module)?;
    let mut output = String::from(DEBUG_PREFIX);
    for byte in bytes {
        write!(&mut output, "{byte:02x}")
            .map_err(|_error| CanonicalError::TextFormatting)?;
    }
    Ok(output)
}

fn encode_type(
    encoder: &mut Encoder,
    definition: &TypeDef,
) -> Result<(), CanonicalError> {
    match definition {
        TypeDef::Array { count, element } => {
            encoder.u8(0);
            encoder.u32(element.value());
            encoder.u32(*count);
        },
        TypeDef::Bool => encoder.u8(1),
        TypeDef::Char => encoder.u8(2),
        TypeDef::F128 => encoder.u8(3),
        TypeDef::F32 => encoder.u8(4),
        TypeDef::F64 => encoder.u8(5),
        TypeDef::Function {
            parameters,
            result,
            variadic,
        } => {
            encoder.u8(6);
            encode_type_ids(encoder, parameters)?;
            encode_optional_type(encoder, *result);
            encoder.u8(u8::from(*variadic));
        },
        TypeDef::I16 => encoder.u8(7),
        TypeDef::I32 => encoder.u8(8),
        TypeDef::I64 => encoder.u8(9),
        TypeDef::I8 => encoder.u8(10),
        TypeDef::Pointer { pointee } => {
            encoder.u8(11);
            encoder.u32(pointee.value());
        },
        TypeDef::Struct { fields } => {
            encoder.u8(12);
            encode_type_ids(encoder, fields)?;
        },
        TypeDef::U16 => encoder.u8(13),
        TypeDef::U32 => encoder.u8(14),
        TypeDef::U64 => encoder.u8(15),
        TypeDef::U8 => encoder.u8(16),
        TypeDef::Union { members } => {
            encoder.u8(17);
            encode_type_ids(encoder, members)?;
        },
        TypeDef::Void => encoder.u8(18),
    }
    Ok(())
}

fn encode_type_ids(
    encoder: &mut Encoder,
    type_ids: &[TypeId],
) -> Result<(), CanonicalError> {
    encoder.length(type_ids.len())?;
    for type_id in type_ids {
        encoder.u32(type_id.value());
    }
    Ok(())
}

fn encode_optional_type(encoder: &mut Encoder, type_id: Option<TypeId>) {
    match type_id {
        None => encoder.u8(0),
        Some(value) => {
            encoder.u8(1);
            encoder.u32(value.value());
        },
    }
}

fn encode_types(
    encoder: &mut Encoder,
    types: &[TypeEntry],
) -> Result<(), CanonicalError> {
    encoder.length(types.len())?;
    for entry in types {
        encoder.u32(entry.id().value());
        encode_type(encoder, entry.definition())?;
    }
    Ok(())
}

fn encode_global(
    encoder: &mut Encoder,
    global: &Global,
) -> Result<(), CanonicalError> {
    encoder.u32(global.id().value());
    encoder.string(global.name())?;
    encoder.u32(global.type_id().value());
    encode_span(encoder, global.span());
    match global.initializer() {
        None => encoder.u8(0),
        Some(initializer) => {
            encoder.u8(1);
            encoder.bytes(initializer)?;
        },
    }
    Ok(())
}

fn encode_globals(
    encoder: &mut Encoder,
    globals: &[Global],
) -> Result<(), CanonicalError> {
    encoder.length(globals.len())?;
    for global in globals {
        encode_global(encoder, global)?;
    }
    Ok(())
}

fn encode_position(encoder: &mut Encoder, position: SourcePosition) {
    encoder.u32(position.byte());
    encoder.u32(position.line());
    encoder.u32(position.column());
}

fn encode_span(encoder: &mut Encoder, span: SourceSpan) {
    encode_position(encoder, span.begin());
    encode_position(encoder, span.end());
}

fn encode_phi(encoder: &mut Encoder, phi: &Phi) -> Result<(), CanonicalError> {
    encoder.u32(phi.result().value());
    encoder.u32(phi.type_id().value());
    encode_span(encoder, phi.span());
    encoder.length(phi.incoming().len())?;
    for incoming in phi.incoming() {
        encoder.u32(incoming.block().value());
        encoder.u32(incoming.value().value());
    }
    Ok(())
}

fn encode_located_instruction(
    encoder: &mut Encoder,
    located: &LocatedInstruction,
) -> Result<(), CanonicalError> {
    encode_span(encoder, located.span());
    encode_instruction(encoder, located.instruction())
}

fn encode_block(
    encoder: &mut Encoder,
    block: &BasicBlock,
) -> Result<(), CanonicalError> {
    encoder.u32(block.id().value());
    encode_span(encoder, block.span());
    encoder.length(block.phis().len())?;
    for phi in block.phis() {
        encode_phi(encoder, phi)?;
    }
    encoder.length(block.instructions().len())?;
    for instruction in block.instructions() {
        encode_located_instruction(encoder, instruction)?;
    }
    encode_span(encoder, block.terminator_span());
    encode_terminator(encoder, block.terminator())
}

fn encode_function(
    encoder: &mut Encoder,
    function: &Function,
) -> Result<(), CanonicalError> {
    encoder.u32(function.id().value());
    encoder.string(function.name())?;
    encoder.u32(function.signature().value());
    encode_span(encoder, function.span());
    encoder.length(function.parameters().len())?;
    for parameter in function.parameters() {
        encoder.u32(parameter.value().value());
        encoder.u32(parameter.type_id().value());
    }
    encoder.u32(function.entry().value());
    encoder.length(function.blocks().len())?;
    for block in function.blocks() {
        encode_block(encoder, block)?;
    }
    Ok(())
}

fn encode_functions(
    encoder: &mut Encoder,
    functions: &[Function],
) -> Result<(), CanonicalError> {
    encoder.length(functions.len())?;
    for function in functions {
        encode_function(encoder, function)?;
    }
    Ok(())
}

const fn binary_tag(operation: BinaryOp) -> u8 {
    match operation {
        BinaryOp::Add => 0,
        BinaryOp::And => 1,
        BinaryOp::DivideFloat => 2,
        BinaryOp::DivideSigned => 3,
        BinaryOp::DivideUnsigned => 4,
        BinaryOp::Multiply => 5,
        BinaryOp::Or => 6,
        BinaryOp::RemainderSigned => 7,
        BinaryOp::RemainderUnsigned => 8,
        BinaryOp::ShiftLeft => 9,
        BinaryOp::ShiftRightArithmetic => 10,
        BinaryOp::ShiftRightLogical => 11,
        BinaryOp::Subtract => 12,
        BinaryOp::Xor => 13,
    }
}

const fn cast_tag(operation: CastOp) -> u8 {
    match operation {
        CastOp::Bitcast => 0,
        CastOp::BoolToSigned => 11,
        CastOp::FloatToBool => 12,
        CastOp::FloatToFloat => 1,
        CastOp::FloatToSigned => 2,
        CastOp::FloatToUnsigned => 3,
        CastOp::IntegerBitcast => 15,
        CastOp::IntegerToBool => 13,
        CastOp::IntegerToPointer => 4,
        CastOp::PointerToBool => 14,
        CastOp::PointerToInteger => 5,
        CastOp::SignExtend => 6,
        CastOp::SignedToFloat => 7,
        CastOp::Truncate => 8,
        CastOp::UnsignedToFloat => 9,
        CastOp::ZeroExtend => 10,
    }
}

const fn compare_tag(operation: CompareOp) -> u8 {
    match operation {
        CompareOp::Equal => 0,
        CompareOp::FloatLess => 1,
        CompareOp::FloatLessEqual => 2,
        CompareOp::LessSigned => 3,
        CompareOp::LessSignedEqual => 4,
        CompareOp::LessUnsigned => 5,
        CompareOp::LessUnsignedEqual => 6,
        CompareOp::NotEqual => 7,
    }
}

fn encode_integer_constant(
    encoder: &mut Encoder,
    constant: &IntegerConstant,
) -> Result<(), CanonicalError> {
    encoder.u16(constant.bit_width());
    encoder.bytes(constant.little_endian())
}

fn encode_optional_result(
    encoder: &mut Encoder,
    result: Option<(ValueId, TypeId)>,
) {
    match result {
        None => encoder.u8(0),
        Some((value, type_id)) => {
            encoder.u8(1);
            encoder.u32(value.value());
            encoder.u32(type_id.value());
        },
    }
}

const fn instruction_tag(instruction: &Instruction) -> u8 {
    match instruction {
        Instruction::AddressOffset { .. } => 0,
        Instruction::Binary { .. } => 1,
        Instruction::ByteInput { .. } => 2,
        Instruction::ByteOutput { .. } => 3,
        Instruction::Call { .. } => 4,
        Instruction::Cast { .. } => 5,
        Instruction::Compare { .. } => 6,
        Instruction::ConstantInteger { .. } => 7,
        Instruction::Load { .. } => 8,
        Instruction::Store { .. } => 9,
        Instruction::AutomaticAllocate { .. } => 10,
        Instruction::FunctionAddress { .. } => 11,
    }
}

fn encode_call_target(encoder: &mut Encoder, target: CallTarget) {
    match target {
        CallTarget::Direct(function) => {
            encoder.u8(0);
            encoder.u32(function.value());
        },
        CallTarget::Indirect(value) => {
            encoder.u8(1);
            encoder.u32(value.value());
        },
    }
}

fn encode_function_address_payload(
    encoder: &mut Encoder,
    result: ValueId,
    type_id: TypeId,
    function: super::ids::FunctionId,
) {
    encoder.u32(result.value());
    encoder.u32(type_id.value());
    encoder.u32(function.value());
}

fn encode_instruction(
    encoder: &mut Encoder,
    instruction: &Instruction,
) -> Result<(), CanonicalError> {
    let tag = instruction_tag(instruction);
    encoder.u8(tag);
    if tag < 5 {
        return encode_instruction_low(encoder, instruction);
    }
    if tag < 8 {
        return encode_instruction_mid(encoder, instruction);
    }
    encode_instruction_high(encoder, instruction);
    Ok(())
}

fn encode_instruction_low(
    encoder: &mut Encoder,
    instruction: &Instruction,
) -> Result<(), CanonicalError> {
    match instruction {
        Instruction::AddressOffset {
            byte_offset,
            pointer,
            result,
            type_id,
        } => {
            encoder.u32(result.value());
            encoder.u32(type_id.value());
            encoder.u32(pointer.value());
            encoder.u32(byte_offset.value());
        },
        Instruction::Binary {
            left,
            operation,
            result,
            right,
            type_id,
        } => {
            encoder.u32(result.value());
            encoder.u32(type_id.value());
            encoder.u8(binary_tag(*operation));
            encoder.u32(left.value());
            encoder.u32(right.value());
        },
        Instruction::ByteInput { result, type_id } => {
            encoder.u32(result.value());
            encoder.u32(type_id.value());
        },
        Instruction::ByteOutput { value } => encoder.u32(value.value()),
        Instruction::Call {
            arguments,
            callee,
            result,
        } => {
            encode_optional_result(encoder, *result);
            encode_call_target(encoder, *callee);
            encoder.length(arguments.len())?;
            for argument in arguments {
                encoder.u32(argument.value());
            }
        },
        Instruction::AutomaticAllocate { .. }
        | Instruction::Cast { .. }
        | Instruction::Compare { .. }
        | Instruction::ConstantInteger { .. }
        | Instruction::FunctionAddress { .. }
        | Instruction::Load { .. }
        | Instruction::Store { .. } => {},
    }
    Ok(())
}

fn encode_instruction_mid(
    encoder: &mut Encoder,
    instruction: &Instruction,
) -> Result<(), CanonicalError> {
    match instruction {
        Instruction::Cast {
            operation,
            result,
            type_id,
            value,
        } => {
            encoder.u32(result.value());
            encoder.u32(type_id.value());
            encoder.u8(cast_tag(*operation));
            encoder.u32(value.value());
        },
        Instruction::Compare {
            left,
            operation,
            result,
            right,
            type_id,
        } => {
            encoder.u32(result.value());
            encoder.u32(type_id.value());
            encoder.u8(compare_tag(*operation));
            encoder.u32(left.value());
            encoder.u32(right.value());
        },
        Instruction::ConstantInteger {
            constant,
            result,
            type_id,
        } => {
            encoder.u32(result.value());
            encoder.u32(type_id.value());
            encode_integer_constant(encoder, constant)?;
        },
        Instruction::AddressOffset { .. }
        | Instruction::AutomaticAllocate { .. }
        | Instruction::Binary { .. }
        | Instruction::ByteInput { .. }
        | Instruction::ByteOutput { .. }
        | Instruction::Call { .. }
        | Instruction::FunctionAddress { .. }
        | Instruction::Load { .. }
        | Instruction::Store { .. } => {},
    }
    Ok(())
}

fn encode_instruction_high(encoder: &mut Encoder, instruction: &Instruction) {
    match instruction {
        Instruction::AutomaticAllocate {
            alignment,
            byte_count,
            result,
            type_id,
        } => {
            encoder.u32(result.value());
            encoder.u32(type_id.value());
            encoder.u32(byte_count.value());
            encoder.u8(*alignment);
        },
        Instruction::FunctionAddress {
            function,
            result,
            type_id,
        } => encode_function_address_payload(
            encoder, *result, *type_id, *function,
        ),
        Instruction::Load {
            alignment,
            pointer,
            result,
            type_id,
        } => {
            encoder.u32(result.value());
            encoder.u32(type_id.value());
            encoder.u32(pointer.value());
            encoder.u8(*alignment);
        },
        Instruction::Store {
            alignment,
            pointer,
            value,
        } => encode_store_payload(encoder, *pointer, *value, *alignment),
        Instruction::AddressOffset { .. }
        | Instruction::Binary { .. }
        | Instruction::ByteInput { .. }
        | Instruction::ByteOutput { .. }
        | Instruction::Call { .. }
        | Instruction::Cast { .. }
        | Instruction::Compare { .. }
        | Instruction::ConstantInteger { .. } => {},
    }
}

fn encode_store_payload(
    encoder: &mut Encoder,
    pointer: ValueId,
    value: ValueId,
    alignment: u8,
) {
    encoder.u32(pointer.value());
    encoder.u32(value.value());
    encoder.u8(alignment);
}

fn encode_switch_case(
    encoder: &mut Encoder,
    case: &SwitchCase,
) -> Result<(), CanonicalError> {
    encode_integer_constant(encoder, case.constant())?;
    encoder.u32(case.target().value());
    Ok(())
}

fn encode_terminator(
    encoder: &mut Encoder,
    terminator: &Terminator,
) -> Result<(), CanonicalError> {
    match terminator {
        Terminator::Branch {
            condition,
            false_target,
            true_target,
        } => {
            encoder.u8(0);
            encoder.u32(condition.value());
            encoder.u32(true_target.value());
            encoder.u32(false_target.value());
        },
        Terminator::Jump { target } => {
            encoder.u8(1);
            encoder.u32(target.value());
        },
        Terminator::Return { value } => {
            encoder.u8(2);
            match value {
                None => encoder.u8(0),
                Some(result) => {
                    encoder.u8(1);
                    encoder.u32(result.value());
                },
            }
        },
        Terminator::Switch {
            cases,
            default_target,
            selector,
        } => {
            encoder.u8(3);
            encoder.u32(selector.value());
            encoder.u32(default_target.value());
            encoder.length(cases.len())?;
            for case in cases {
                encode_switch_case(encoder, case)?;
            }
        },
    }
    Ok(())
}

fn encode_proof(
    encoder: &mut Encoder,
    proof: &ProofObligation,
) -> Result<(), CanonicalError> {
    match proof {
        ProofObligation::Aligned {
            alignment,
            function,
            pointer,
        } => {
            encoder.u8(0);
            encoder.u32(function.value());
            encoder.u32(pointer.value());
            encoder.u8(*alignment);
        },
        ProofObligation::InBounds { bytes, function, pointer } => {
            encoder.u8(1);
            encoder.u32(function.value());
            encoder.u32(pointer.value());
            encoder.u32(*bytes);
        },
        ProofObligation::Nonzero { function, value } => {
            encoder.u8(2);
            encoder.u32(function.value());
            encoder.u32(value.value());
        },
        ProofObligation::NoSignedOverflow { function, result } => {
            encoder.u8(3);
            encoder.u32(function.value());
            encoder.u32(result.value());
        },
        ProofObligation::ProfileCapability { capability } => {
            encoder.u8(4);
            encoder.string(capability)?;
        },
    }
    Ok(())
}

fn encode_proofs(
    encoder: &mut Encoder,
    proofs: &[ProofObligation],
) -> Result<(), CanonicalError> {
    encoder.length(proofs.len())?;
    for proof in proofs {
        encode_proof(encoder, proof)?;
    }
    Ok(())
}
