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
//   - Fail-closed restoration of canonical version-one typed-IR bytes.
// - Must-Not:
//   - Accept unknown tags, alternate encodings, trailing bytes, or invalid IR.
// - Allows:
//   - Inputs: exact canonical typed-IR byte strings.
//   - Outputs: fully validated portable typed-IR modules.
//   - Side effects: owned allocation only.
// - Split-When:
//   - A new wire version needs independently reviewed decode semantics.
// - Merge-When:
//   - Canonical encoding and decoding become one inseparable lifecycle.
// - Summary:
//   - Restores canonical typed compiler IR with exact wire validation.
// - Description:
//   - Every explicit encoder tag has one exact inverse and bounded length read.
// - Usage:
//   - Used by durable compiler checkpoints, caches, and replay tests.
// - Defaults:
//   - Truncation, unknown tags, invalid UTF-8, or noncanonical bytes fail
//     closed.
//

//! Fail-closed restoration of canonical portable typed compiler IR.

use std::str;

use super::control::{
    BasicBlock, BasicBlockSpec, Phi, PhiIncoming, SwitchCase, Terminator,
};
use super::encode::{CanonicalError, canonical_bytes};
use super::error::ValidationError;
use super::ids::{BlockId, FunctionId, GlobalId, TypeId, ValueId};
use super::instruction::{
    BinaryOp, CallTarget, CastOp, CompareOp, Instruction, IntegerConstant,
    LocatedInstruction,
};
use super::module::{
    Function, FunctionSpec, Global, GlobalSpec, Module, ModuleSpec, Parameter,
    ProofObligation, TYPED_IR_VERSION,
};
use super::source::{SourcePosition, SourceSpan};
use super::types::{TypeDef, TypeEntry};
use super::validate::validate_module;

const MAGIC: &[u8; 4] = b"MCTI";
type OptionalTypedValue = Option<(ValueId, TypeId)>;

/// Canonical typed-IR restoration failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CanonicalDecodeError {
    /// A boolean/optional discriminator was not exactly zero or one.
    InvalidBoolean,
    /// The byte stream does not start with the typed-IR wire magic.
    InvalidMagic,
    /// A UTF-8 text field is malformed.
    InvalidUtf8,
    /// Decoded bytes do not reproduce the exact canonical input.
    NonCanonical,
    /// Bytes remain after one complete module.
    TrailingBytes,
    /// The byte stream ends before a declared field is complete.
    Truncated,
    /// A closed wire tag is unknown for version one.
    UnknownTag,
    /// The encoded typed-IR version is not supported by this decoder.
    UnsupportedVersion,
    /// Complete typed-IR admission rejected the restored module.
    Validation(ValidationError),
}

impl From<ValidationError> for CanonicalDecodeError {
    fn from(error: ValidationError) -> Self {
        Self::Validation(error)
    }
}

struct Decoder<'bytes> {
    bytes: &'bytes [u8],
    offset: usize,
}

impl<'bytes> Decoder<'bytes> {
    fn boolean(&mut self) -> Result<bool, CanonicalDecodeError> {
        match self.u8()? {
            0 => Ok(false),
            1 => Ok(true),
            _ => Err(CanonicalDecodeError::InvalidBoolean),
        }
    }

    fn bytes(&mut self) -> Result<Vec<u8>, CanonicalDecodeError> {
        let count = self.count(1)?;
        Ok(self.raw(count)?.to_vec())
    }

    fn count(
        &mut self,
        minimum_item_bytes: usize,
    ) -> Result<usize, CanonicalDecodeError> {
        let count = usize::try_from(self.u32()?)
            .map_err(|_error| CanonicalDecodeError::Truncated)?;
        let minimum = count
            .checked_mul(minimum_item_bytes)
            .ok_or(CanonicalDecodeError::Truncated)?;
        if minimum > self.remaining() {
            return Err(CanonicalDecodeError::Truncated);
        }
        Ok(count)
    }

    const fn new(bytes: &'bytes [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn raw(
        &mut self,
        count: usize,
    ) -> Result<&'bytes [u8], CanonicalDecodeError> {
        let end = self
            .offset
            .checked_add(count)
            .ok_or(CanonicalDecodeError::Truncated)?;
        let value = self
            .bytes
            .get(self.offset..end)
            .ok_or(CanonicalDecodeError::Truncated)?;
        self.offset = end;
        Ok(value)
    }

    const fn remaining(&self) -> usize {
        self.bytes.len().saturating_sub(self.offset)
    }

    fn string(&mut self) -> Result<String, CanonicalDecodeError> {
        let bytes = self.bytes()?;
        let text = str::from_utf8(&bytes)
            .map_err(|_error| CanonicalDecodeError::InvalidUtf8)?;
        Ok(text.to_owned())
    }

    fn u16(&mut self) -> Result<u16, CanonicalDecodeError> {
        let raw: [u8; 2] = self
            .raw(2)?
            .try_into()
            .map_err(|_error| CanonicalDecodeError::Truncated)?;
        Ok(u16::from_le_bytes(raw))
    }

    fn u32(&mut self) -> Result<u32, CanonicalDecodeError> {
        let raw: [u8; 4] = self
            .raw(4)?
            .try_into()
            .map_err(|_error| CanonicalDecodeError::Truncated)?;
        Ok(u32::from_le_bytes(raw))
    }

    fn u8(&mut self) -> Result<u8, CanonicalDecodeError> {
        self.raw(1)?
            .first()
            .copied()
            .ok_or(CanonicalDecodeError::Truncated)
    }
}

/// Restores one exact version-one typed-IR module from canonical bytes.
///
/// # Errors
///
/// Rejects malformed, truncated, noncanonical, unsupported-version, or
/// validation-invalid input.
pub fn canonical_module(bytes: &[u8]) -> Result<Module, CanonicalDecodeError> {
    let mut decoder = Decoder::new(bytes);
    if decoder.raw(MAGIC.len())? != MAGIC {
        return Err(CanonicalDecodeError::InvalidMagic);
    }
    let format_version = decoder.u16()?;
    if format_version != TYPED_IR_VERSION {
        return Err(CanonicalDecodeError::UnsupportedVersion);
    }
    let abi_id = decoder.string()?;
    let target_profile = decoder.string()?;
    let source_id = decoder.string()?;
    let source_sha256: [u8; 32] = decoder
        .raw(32)?
        .try_into()
        .map_err(|_error| CanonicalDecodeError::Truncated)?;
    let types = decode_types(&mut decoder)?;
    let globals = decode_globals(&mut decoder)?;
    let functions = decode_functions(&mut decoder)?;
    let proof_obligations = decode_proofs(&mut decoder)?;
    if decoder.remaining() != 0 {
        return Err(CanonicalDecodeError::TrailingBytes);
    }
    let module = Module::new(ModuleSpec {
        abi_id,
        format_version,
        functions,
        globals,
        proof_obligations,
        source_id,
        source_sha256,
        target_profile,
        types,
    });
    validate_module(&module)?;
    let restored = canonical_bytes(&module).map_err(decode_canonical_error)?;
    if restored != bytes {
        return Err(CanonicalDecodeError::NonCanonical);
    }
    Ok(module)
}

const fn decode_canonical_error(error: CanonicalError) -> CanonicalDecodeError {
    match error {
        CanonicalError::Validation(validation) => {
            CanonicalDecodeError::Validation(validation)
        },
        CanonicalError::LengthOverflow | CanonicalError::TextFormatting => {
            CanonicalDecodeError::NonCanonical
        },
    }
}

fn decode_type_ids(
    decoder: &mut Decoder<'_>,
) -> Result<Vec<TypeId>, CanonicalDecodeError> {
    let count = decoder.count(4)?;
    let mut values = Vec::with_capacity(count);
    for _ in 0..count {
        values.push(TypeId::new(decoder.u32()?));
    }
    Ok(values)
}

fn decode_optional_type(
    decoder: &mut Decoder<'_>,
) -> Result<Option<TypeId>, CanonicalDecodeError> {
    match decoder.u8()? {
        0 => Ok(None),
        1 => Ok(Some(TypeId::new(decoder.u32()?))),
        _ => Err(CanonicalDecodeError::InvalidBoolean),
    }
}

fn decode_type(
    decoder: &mut Decoder<'_>,
) -> Result<TypeDef, CanonicalDecodeError> {
    let definition = match decoder.u8()? {
        0 => TypeDef::Array {
            element: TypeId::new(decoder.u32()?),
            count: decoder.u32()?,
        },
        1 => TypeDef::Bool,
        2 => TypeDef::Char,
        3 => TypeDef::F128,
        4 => TypeDef::F32,
        5 => TypeDef::F64,
        6 => TypeDef::Function {
            parameters: decode_type_ids(decoder)?,
            result: decode_optional_type(decoder)?,
            variadic: decoder.boolean()?,
        },
        7 => TypeDef::I16,
        8 => TypeDef::I32,
        9 => TypeDef::I64,
        10 => TypeDef::I8,
        11 => TypeDef::Pointer {
            pointee: TypeId::new(decoder.u32()?),
        },
        12 => TypeDef::Struct {
            fields: decode_type_ids(decoder)?,
        },
        13 => TypeDef::U16,
        14 => TypeDef::U32,
        15 => TypeDef::U64,
        16 => TypeDef::U8,
        17 => TypeDef::Union {
            members: decode_type_ids(decoder)?,
        },
        18 => TypeDef::Void,
        _ => return Err(CanonicalDecodeError::UnknownTag),
    };
    Ok(definition)
}

fn decode_types(
    decoder: &mut Decoder<'_>,
) -> Result<Vec<TypeEntry>, CanonicalDecodeError> {
    let count = decoder.count(5)?;
    let mut entries = Vec::with_capacity(count);
    for _ in 0..count {
        let id = TypeId::new(decoder.u32()?);
        entries.push(TypeEntry::new(id, decode_type(decoder)?));
    }
    Ok(entries)
}

fn decode_position(
    decoder: &mut Decoder<'_>,
) -> Result<SourcePosition, CanonicalDecodeError> {
    Ok(SourcePosition::new(
        decoder.u32()?,
        decoder.u32()?,
        decoder.u32()?,
    ))
}

fn decode_span(
    decoder: &mut Decoder<'_>,
) -> Result<SourceSpan, CanonicalDecodeError> {
    Ok(SourceSpan::new(
        decode_position(decoder)?,
        decode_position(decoder)?,
    ))
}

fn decode_global(
    decoder: &mut Decoder<'_>,
) -> Result<Global, CanonicalDecodeError> {
    let id = GlobalId::new(decoder.u32()?);
    let name = decoder.string()?;
    let type_id = TypeId::new(decoder.u32()?);
    let span = decode_span(decoder)?;
    let initializer = match decoder.u8()? {
        0 => None,
        1 => Some(decoder.bytes()?),
        _ => return Err(CanonicalDecodeError::InvalidBoolean),
    };
    Ok(Global::new(GlobalSpec {
        id,
        initializer,
        name,
        span,
        type_id,
    }))
}

fn decode_globals(
    decoder: &mut Decoder<'_>,
) -> Result<Vec<Global>, CanonicalDecodeError> {
    let count = decoder.count(1)?;
    let mut globals = Vec::with_capacity(count);
    for _ in 0..count {
        globals.push(decode_global(decoder)?);
    }
    Ok(globals)
}

fn decode_phi(decoder: &mut Decoder<'_>) -> Result<Phi, CanonicalDecodeError> {
    let result = ValueId::new(decoder.u32()?);
    let type_id = TypeId::new(decoder.u32()?);
    let span = decode_span(decoder)?;
    let count = decoder.count(8)?;
    let mut incoming = Vec::with_capacity(count);
    for _ in 0..count {
        incoming.push(PhiIncoming::new(
            BlockId::new(decoder.u32()?),
            ValueId::new(decoder.u32()?),
        ));
    }
    Ok(Phi::new(result, type_id, incoming, span))
}

fn decode_integer_constant(
    decoder: &mut Decoder<'_>,
) -> Result<IntegerConstant, CanonicalDecodeError> {
    Ok(IntegerConstant::new(decoder.u16()?, decoder.bytes()?))
}

const fn decode_binary_tag(tag: u8) -> Result<BinaryOp, CanonicalDecodeError> {
    let operation = match tag {
        0 => BinaryOp::Add,
        1 => BinaryOp::And,
        2 => BinaryOp::DivideFloat,
        3 => BinaryOp::DivideSigned,
        4 => BinaryOp::DivideUnsigned,
        5 => BinaryOp::Multiply,
        6 => BinaryOp::Or,
        7 => BinaryOp::RemainderSigned,
        8 => BinaryOp::RemainderUnsigned,
        9 => BinaryOp::ShiftLeft,
        10 => BinaryOp::ShiftRightArithmetic,
        11 => BinaryOp::ShiftRightLogical,
        12 => BinaryOp::Subtract,
        13 => BinaryOp::Xor,
        _ => return Err(CanonicalDecodeError::UnknownTag),
    };
    Ok(operation)
}

const fn decode_cast_tag(tag: u8) -> Result<CastOp, CanonicalDecodeError> {
    let operation = match tag {
        0 => CastOp::Bitcast,
        1 => CastOp::FloatToFloat,
        2 => CastOp::FloatToSigned,
        3 => CastOp::FloatToUnsigned,
        4 => CastOp::IntegerToPointer,
        5 => CastOp::PointerToInteger,
        6 => CastOp::SignExtend,
        7 => CastOp::SignedToFloat,
        8 => CastOp::Truncate,
        9 => CastOp::UnsignedToFloat,
        10 => CastOp::ZeroExtend,
        11 => CastOp::BoolToSigned,
        12 => CastOp::FloatToBool,
        13 => CastOp::IntegerToBool,
        14 => CastOp::PointerToBool,
        15 => CastOp::IntegerBitcast,
        _ => return Err(CanonicalDecodeError::UnknownTag),
    };
    Ok(operation)
}

const fn decode_compare_tag(
    tag: u8,
) -> Result<CompareOp, CanonicalDecodeError> {
    let operation = match tag {
        0 => CompareOp::Equal,
        1 => CompareOp::FloatLess,
        2 => CompareOp::FloatLessEqual,
        3 => CompareOp::LessSigned,
        4 => CompareOp::LessSignedEqual,
        5 => CompareOp::LessUnsigned,
        6 => CompareOp::LessUnsignedEqual,
        7 => CompareOp::NotEqual,
        _ => return Err(CanonicalDecodeError::UnknownTag),
    };
    Ok(operation)
}

fn decode_optional_result(
    decoder: &mut Decoder<'_>,
) -> Result<OptionalTypedValue, CanonicalDecodeError> {
    match decoder.u8()? {
        0 => Ok(None),
        1 => Ok(Some((
            ValueId::new(decoder.u32()?),
            TypeId::new(decoder.u32()?),
        ))),
        _ => Err(CanonicalDecodeError::InvalidBoolean),
    }
}

fn decode_call_target(
    decoder: &mut Decoder<'_>,
) -> Result<CallTarget, CanonicalDecodeError> {
    match decoder.u8()? {
        0 => Ok(CallTarget::Direct(FunctionId::new(decoder.u32()?))),
        1 => Ok(CallTarget::Indirect(ValueId::new(decoder.u32()?))),
        _ => Err(CanonicalDecodeError::UnknownTag),
    }
}

fn decode_value_ids(
    decoder: &mut Decoder<'_>,
) -> Result<Vec<ValueId>, CanonicalDecodeError> {
    let count = decoder.count(4)?;
    let mut values = Vec::with_capacity(count);
    for _ in 0..count {
        values.push(ValueId::new(decoder.u32()?));
    }
    Ok(values)
}

fn decode_instruction(
    decoder: &mut Decoder<'_>,
) -> Result<Instruction, CanonicalDecodeError> {
    let tag = decoder.u8()?;
    if tag < 5 {
        return decode_instruction_low(tag, decoder);
    }
    if tag < 8 {
        return decode_instruction_mid(tag, decoder);
    }
    decode_instruction_high(tag, decoder)
}

fn decode_instruction_high(
    tag: u8,
    decoder: &mut Decoder<'_>,
) -> Result<Instruction, CanonicalDecodeError> {
    let instruction = match tag {
        8 => Instruction::Load {
            result: ValueId::new(decoder.u32()?),
            type_id: TypeId::new(decoder.u32()?),
            pointer: ValueId::new(decoder.u32()?),
            alignment: decoder.u8()?,
        },
        9 => Instruction::Store {
            pointer: ValueId::new(decoder.u32()?),
            value: ValueId::new(decoder.u32()?),
            alignment: decoder.u8()?,
        },
        10 => Instruction::AutomaticAllocate {
            result: ValueId::new(decoder.u32()?),
            type_id: TypeId::new(decoder.u32()?),
            byte_count: ValueId::new(decoder.u32()?),
            alignment: decoder.u8()?,
        },
        11 => Instruction::FunctionAddress {
            result: ValueId::new(decoder.u32()?),
            type_id: TypeId::new(decoder.u32()?),
            function: FunctionId::new(decoder.u32()?),
        },
        _ => return Err(CanonicalDecodeError::UnknownTag),
    };
    Ok(instruction)
}

fn decode_instruction_low(
    tag: u8,
    decoder: &mut Decoder<'_>,
) -> Result<Instruction, CanonicalDecodeError> {
    let instruction = match tag {
        0 => Instruction::AddressOffset {
            result: ValueId::new(decoder.u32()?),
            type_id: TypeId::new(decoder.u32()?),
            pointer: ValueId::new(decoder.u32()?),
            byte_offset: ValueId::new(decoder.u32()?),
        },
        1 => Instruction::Binary {
            result: ValueId::new(decoder.u32()?),
            type_id: TypeId::new(decoder.u32()?),
            operation: decode_binary_tag(decoder.u8()?)?,
            left: ValueId::new(decoder.u32()?),
            right: ValueId::new(decoder.u32()?),
        },
        2 => Instruction::ByteInput {
            result: ValueId::new(decoder.u32()?),
            type_id: TypeId::new(decoder.u32()?),
        },
        3 => Instruction::ByteOutput {
            value: ValueId::new(decoder.u32()?),
        },
        4 => Instruction::Call {
            result: decode_optional_result(decoder)?,
            callee: decode_call_target(decoder)?,
            arguments: decode_value_ids(decoder)?,
        },
        _ => return Err(CanonicalDecodeError::UnknownTag),
    };
    Ok(instruction)
}

fn decode_instruction_mid(
    tag: u8,
    decoder: &mut Decoder<'_>,
) -> Result<Instruction, CanonicalDecodeError> {
    let instruction = match tag {
        5 => Instruction::Cast {
            result: ValueId::new(decoder.u32()?),
            type_id: TypeId::new(decoder.u32()?),
            operation: decode_cast_tag(decoder.u8()?)?,
            value: ValueId::new(decoder.u32()?),
        },
        6 => Instruction::Compare {
            result: ValueId::new(decoder.u32()?),
            type_id: TypeId::new(decoder.u32()?),
            operation: decode_compare_tag(decoder.u8()?)?,
            left: ValueId::new(decoder.u32()?),
            right: ValueId::new(decoder.u32()?),
        },
        7 => Instruction::ConstantInteger {
            result: ValueId::new(decoder.u32()?),
            type_id: TypeId::new(decoder.u32()?),
            constant: decode_integer_constant(decoder)?,
        },
        _ => return Err(CanonicalDecodeError::UnknownTag),
    };
    Ok(instruction)
}

fn decode_located_instruction(
    decoder: &mut Decoder<'_>,
) -> Result<LocatedInstruction, CanonicalDecodeError> {
    let span = decode_span(decoder)?;
    Ok(LocatedInstruction::new(decode_instruction(decoder)?, span))
}

fn decode_switch_case(
    decoder: &mut Decoder<'_>,
) -> Result<SwitchCase, CanonicalDecodeError> {
    Ok(SwitchCase::new(
        decode_integer_constant(decoder)?,
        BlockId::new(decoder.u32()?),
    ))
}

fn decode_terminator(
    decoder: &mut Decoder<'_>,
) -> Result<Terminator, CanonicalDecodeError> {
    let terminator = match decoder.u8()? {
        0 => Terminator::Branch {
            condition: ValueId::new(decoder.u32()?),
            true_target: BlockId::new(decoder.u32()?),
            false_target: BlockId::new(decoder.u32()?),
        },
        1 => Terminator::Jump {
            target: BlockId::new(decoder.u32()?),
        },
        2 => Terminator::Return {
            value: match decoder.u8()? {
                0 => None,
                1 => Some(ValueId::new(decoder.u32()?)),
                _ => return Err(CanonicalDecodeError::InvalidBoolean),
            },
        },
        3 => {
            let selector = ValueId::new(decoder.u32()?);
            let default_target = BlockId::new(decoder.u32()?);
            let count = decoder.count(1)?;
            let mut cases = Vec::with_capacity(count);
            for _ in 0..count {
                cases.push(decode_switch_case(decoder)?);
            }
            Terminator::Switch {
                cases,
                default_target,
                selector,
            }
        },
        _ => return Err(CanonicalDecodeError::UnknownTag),
    };
    Ok(terminator)
}

fn decode_block(
    decoder: &mut Decoder<'_>,
) -> Result<BasicBlock, CanonicalDecodeError> {
    let id = BlockId::new(decoder.u32()?);
    let span = decode_span(decoder)?;
    let phi_count = decoder.count(1)?;
    let mut phis = Vec::with_capacity(phi_count);
    for _ in 0..phi_count {
        phis.push(decode_phi(decoder)?);
    }
    let instruction_count = decoder.count(1)?;
    let mut instructions = Vec::with_capacity(instruction_count);
    for _ in 0..instruction_count {
        instructions.push(decode_located_instruction(decoder)?);
    }
    let terminator_span = decode_span(decoder)?;
    let terminator = decode_terminator(decoder)?;
    Ok(BasicBlock::new(BasicBlockSpec {
        id,
        instructions,
        phis,
        span,
        terminator,
        terminator_span,
    }))
}

fn decode_function(
    decoder: &mut Decoder<'_>,
) -> Result<Function, CanonicalDecodeError> {
    let id = FunctionId::new(decoder.u32()?);
    let name = decoder.string()?;
    let signature = TypeId::new(decoder.u32()?);
    let span = decode_span(decoder)?;
    let parameter_count = decoder.count(8)?;
    let mut parameters = Vec::with_capacity(parameter_count);
    for _ in 0..parameter_count {
        parameters.push(Parameter::new(
            ValueId::new(decoder.u32()?),
            TypeId::new(decoder.u32()?),
        ));
    }
    let entry = BlockId::new(decoder.u32()?);
    let block_count = decoder.count(1)?;
    let mut blocks = Vec::with_capacity(block_count);
    for _ in 0..block_count {
        blocks.push(decode_block(decoder)?);
    }
    Ok(Function::new(FunctionSpec {
        blocks,
        entry,
        id,
        name,
        parameters,
        signature,
        span,
    }))
}

fn decode_functions(
    decoder: &mut Decoder<'_>,
) -> Result<Vec<Function>, CanonicalDecodeError> {
    let count = decoder.count(1)?;
    let mut functions = Vec::with_capacity(count);
    for _ in 0..count {
        functions.push(decode_function(decoder)?);
    }
    Ok(functions)
}

fn decode_proof(
    decoder: &mut Decoder<'_>,
) -> Result<ProofObligation, CanonicalDecodeError> {
    let proof = match decoder.u8()? {
        0 => ProofObligation::Aligned {
            function: FunctionId::new(decoder.u32()?),
            pointer: ValueId::new(decoder.u32()?),
            alignment: decoder.u8()?,
        },
        1 => ProofObligation::InBounds {
            function: FunctionId::new(decoder.u32()?),
            pointer: ValueId::new(decoder.u32()?),
            bytes: decoder.u32()?,
        },
        2 => ProofObligation::Nonzero {
            function: FunctionId::new(decoder.u32()?),
            value: ValueId::new(decoder.u32()?),
        },
        3 => ProofObligation::NoSignedOverflow {
            function: FunctionId::new(decoder.u32()?),
            result: ValueId::new(decoder.u32()?),
        },
        4 => ProofObligation::ProfileCapability {
            capability: decoder.string()?,
        },
        _ => return Err(CanonicalDecodeError::UnknownTag),
    };
    Ok(proof)
}

fn decode_proofs(
    decoder: &mut Decoder<'_>,
) -> Result<Vec<ProofObligation>, CanonicalDecodeError> {
    let count = decoder.count(1)?;
    let mut proofs = Vec::with_capacity(count);
    for _ in 0..count {
        proofs.push(decode_proof(decoder)?);
    }
    Ok(proofs)
}
