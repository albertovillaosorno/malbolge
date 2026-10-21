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
//   - Validation-gated canonical bytes for pre-layout ternary programs.
// - Must-Not:
//   - Serialize invalid programs, Rust discriminants, host widths, or layout
//     addresses.
// - Allows:
//   - Inputs: one complete pre-layout ternary program.
//   - Outputs: stable little-endian bytes or a fully validated restored
//     program.
//   - Side effects: owned allocation only.
// - Split-When:
//   - A new ternary wire version needs independently reviewed encoding rules.
// - Merge-When:
//   - Program validation and canonical serialization become inseparable.
// - Summary:
//   - Gives the pre-layout ternary stage one concrete portable wire identity.
// - Description:
//   - Explicit tags and fixed-width ternary scalars avoid Rust-layout
//     authority.
// - Usage:
//   - Used by compiler replay, cache, checkpoint, and round-trip evidence.
// - Defaults:
//   - Malformed, noncanonical, unsupported-version, or invalid state fails
//     closed.
//

//! Canonical validation-gated codec for pre-layout ternary programs.

use std::collections::{BTreeMap, BTreeSet};
use std::str;

use super::model::{
    I32_TERNARY_TRITS, TernaryFunction, TernaryI32Scalar, TernaryOperation,
    TernaryProgram, TernarySourcePosition, TernarySourceSpan, TernaryU8Scalar,
    U8_TERNARY_TRITS,
};

const ABI_ID: &str = "malbolge-c32-v1";
const MAGIC: &[u8; 4] = b"MCTR";
const TARGET_PROFILE: &str = "malbolge-2026";
const TERNARY_WIRE_VERSION: u16 = 1;
const TYPED_IR_VERSION: u16 = 1;
// Conservative wire minima: id + empty name + span + operation count;
// operation tag + one `u32` value + the required 24-byte source span.
const FUNCTION_MIN_BYTES: usize = 36;
const OPERATION_MIN_BYTES: usize = 29;

/// Stable codec identity for canonical pre-layout ternary programs.
pub const TERNARY_PROGRAM_CODEC_ID: &str = "malbolge-ternary-ir-v1";

/// Stable failures for canonical pre-layout ternary encoding/restoration.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TernaryProgramCodecError {
    /// Wire magic does not identify a canonical ternary program.
    InvalidMagic,
    /// Fixed-width ternary scalar contains an invalid or out-of-range value.
    InvalidScalar,
    /// One encoded string is not valid UTF-8.
    InvalidUtf8,
    /// A variable-length field cannot fit the canonical unsigned 32-bit length.
    LengthOverflow,
    /// Decoded state does not reproduce the exact canonical input bytes.
    NonCanonical,
    /// Bytes remain after one complete program.
    TrailingBytes,
    /// Input ends before a declared field is complete.
    Truncated,
    /// A closed operation tag is unknown for this wire version.
    UnknownTag,
    /// Wire version is not supported by this codec.
    UnsupportedVersion,
    /// Program semantics or provenance violate stage invariants.
    Validation(TernaryProgramValidationError),
}

/// Stable semantic validation failures for pre-layout ternary programs.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TernaryProgramValidationError {
    /// Function identity/name ordering is not canonical.
    FunctionIdentity,
    /// Program ABI/profile/input identity is outside this codec contract.
    ProgramIdentity,
    /// Function or operation source provenance is malformed.
    SourceProvenance,
    /// Operation result/use identities violate the lowered SSA type/order
    /// model.
    SsaValue,
    /// Function does not end in exactly one valid `i32` return.
    Terminator,
}

#[derive(Clone, Copy, Eq, PartialEq)]
enum ValueKind {
    Bool,
    Byte,
    I32,
    U32,
}

struct Decoder<'bytes> {
    bytes: &'bytes [u8],
    offset: usize,
}

impl<'bytes> Decoder<'bytes> {
    fn byte_scalar(
        &mut self,
    ) -> Result<TernaryU8Scalar, TernaryProgramCodecError> {
        let encoded = self.raw(U8_TERNARY_TRITS)?;
        if encoded.iter().any(|trit| *trit > 2) {
            return Err(TernaryProgramCodecError::InvalidScalar);
        }
        let value = encoded.iter().rev().try_fold(0u16, |value, trit| {
            value
                .checked_mul(3)
                .and_then(|next| next.checked_add(u16::from(*trit)))
                .ok_or(TernaryProgramCodecError::InvalidScalar)
        })?;
        let bits = u8::try_from(value)
            .map_err(|_error| TernaryProgramCodecError::InvalidScalar)?;
        let scalar = TernaryU8Scalar::from_bits(bits);
        if scalar.trits().as_slice() != encoded {
            return Err(TernaryProgramCodecError::InvalidScalar);
        }
        Ok(scalar)
    }

    fn count(
        &mut self,
        minimum_item_bytes: usize,
    ) -> Result<usize, TernaryProgramCodecError> {
        let count = usize::try_from(self.u32()?)
            .map_err(|_error| TernaryProgramCodecError::Truncated)?;
        let minimum = count
            .checked_mul(minimum_item_bytes)
            .ok_or(TernaryProgramCodecError::Truncated)?;
        if minimum > self.remaining() {
            return Err(TernaryProgramCodecError::Truncated);
        }
        Ok(count)
    }

    const fn new(bytes: &'bytes [u8]) -> Self {
        Self { bytes, offset: 0 }
    }

    fn raw(
        &mut self,
        count: usize,
    ) -> Result<&'bytes [u8], TernaryProgramCodecError> {
        let end = self
            .offset
            .checked_add(count)
            .ok_or(TernaryProgramCodecError::Truncated)?;
        let value = self
            .bytes
            .get(self.offset..end)
            .ok_or(TernaryProgramCodecError::Truncated)?;
        self.offset = end;
        Ok(value)
    }

    const fn remaining(&self) -> usize {
        self.bytes.len().saturating_sub(self.offset)
    }

    fn scalar(&mut self) -> Result<TernaryI32Scalar, TernaryProgramCodecError> {
        let encoded = self.raw(I32_TERNARY_TRITS)?;
        if encoded.iter().any(|trit| *trit > 2) {
            return Err(TernaryProgramCodecError::InvalidScalar);
        }
        let value = encoded.iter().rev().try_fold(0u64, |value, trit| {
            value
                .checked_mul(3)
                .and_then(|next| next.checked_add(u64::from(*trit)))
                .ok_or(TernaryProgramCodecError::InvalidScalar)
        })?;
        let bits = u32::try_from(value)
            .map_err(|_error| TernaryProgramCodecError::InvalidScalar)?;
        let scalar = TernaryI32Scalar::from_bits(bits);
        if scalar.trits().as_slice() != encoded {
            return Err(TernaryProgramCodecError::InvalidScalar);
        }
        Ok(scalar)
    }

    fn string(&mut self) -> Result<String, TernaryProgramCodecError> {
        let count = self.count(1)?;
        let bytes = self.raw(count)?;
        str::from_utf8(bytes)
            .map(str::to_owned)
            .map_err(|_error| TernaryProgramCodecError::InvalidUtf8)
    }

    fn u16(&mut self) -> Result<u16, TernaryProgramCodecError> {
        let raw: [u8; 2] = self
            .raw(2)?
            .try_into()
            .map_err(|_error| TernaryProgramCodecError::Truncated)?;
        Ok(u16::from_le_bytes(raw))
    }

    fn u32(&mut self) -> Result<u32, TernaryProgramCodecError> {
        let raw: [u8; 4] = self
            .raw(4)?
            .try_into()
            .map_err(|_error| TernaryProgramCodecError::Truncated)?;
        Ok(u32::from_le_bytes(raw))
    }

    fn u8(&mut self) -> Result<u8, TernaryProgramCodecError> {
        self.raw(1)?
            .first()
            .copied()
            .ok_or(TernaryProgramCodecError::Truncated)
    }
}

struct Encoder {
    bytes: Vec<u8>,
}

impl Encoder {
    fn byte_scalar(&mut self, value: TernaryU8Scalar) {
        self.raw(value.trits());
    }

    fn finish(self) -> Vec<u8> {
        self.bytes
    }

    fn length(&mut self, value: usize) -> Result<(), TernaryProgramCodecError> {
        let encoded = u32::try_from(value)
            .map_err(|_error| TernaryProgramCodecError::LengthOverflow)?;
        self.u32(encoded);
        Ok(())
    }

    const fn new() -> Self {
        Self { bytes: Vec::new() }
    }

    fn raw(&mut self, value: &[u8]) {
        self.bytes.extend_from_slice(value);
    }

    fn scalar(&mut self, value: &TernaryI32Scalar) {
        self.raw(value.trits());
    }

    fn string(&mut self, value: &str) -> Result<(), TernaryProgramCodecError> {
        self.length(value.len())?;
        self.raw(value.as_bytes());
        Ok(())
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

/// Returns canonical version-one bytes for one validated ternary program.
///
/// # Errors
///
/// Returns validation or length failures before publishing bytes.
pub fn canonical_ternary_bytes(
    program: &TernaryProgram,
) -> Result<Vec<u8>, TernaryProgramCodecError> {
    validate_ternary_program(program)
        .map_err(TernaryProgramCodecError::Validation)?;
    let mut encoder = Encoder::new();
    encoder.raw(MAGIC);
    encoder.u16(TERNARY_WIRE_VERSION);
    encoder.u16(program.input_format_version);
    encoder.string(&program.abi_id)?;
    encoder.string(&program.target_profile)?;
    encoder.string(&program.source_id)?;
    encoder.raw(&program.source_sha256);
    encode_functions(&mut encoder, &program.functions)?;
    Ok(encoder.finish())
}

/// Restores one exact canonical pre-layout ternary program.
///
/// # Errors
///
/// Rejects malformed, truncated, noncanonical, unsupported-version, or
/// semantic-invalid input.
pub fn canonical_ternary_program(
    bytes: &[u8],
) -> Result<TernaryProgram, TernaryProgramCodecError> {
    let mut decoder = Decoder::new(bytes);
    if decoder.raw(MAGIC.len())? != MAGIC {
        return Err(TernaryProgramCodecError::InvalidMagic);
    }
    if decoder.u16()? != TERNARY_WIRE_VERSION {
        return Err(TernaryProgramCodecError::UnsupportedVersion);
    }
    let input_format_version = decoder.u16()?;
    let abi_id = decoder.string()?;
    let target_profile = decoder.string()?;
    let source_id = decoder.string()?;
    let source_sha256: [u8; 32] = decoder
        .raw(32)?
        .try_into()
        .map_err(|_error| TernaryProgramCodecError::Truncated)?;
    let functions = decode_functions(&mut decoder)?;
    if decoder.remaining() != 0 {
        return Err(TernaryProgramCodecError::TrailingBytes);
    }
    let program = TernaryProgram {
        abi_id,
        functions,
        input_format_version,
        source_id,
        source_sha256,
        target_profile,
    };
    validate_ternary_program(&program)
        .map_err(TernaryProgramCodecError::Validation)?;
    let restored = canonical_ternary_bytes(&program)?;
    if restored != bytes {
        return Err(TernaryProgramCodecError::NonCanonical);
    }
    Ok(program)
}

fn decode_function(
    decoder: &mut Decoder<'_>,
) -> Result<TernaryFunction, TernaryProgramCodecError> {
    let id = decoder.u32()?;
    let name = decoder.string()?;
    let span = decode_span(decoder)?;
    let count = decoder.count(OPERATION_MIN_BYTES)?;
    let mut operations = Vec::new();
    for _ in 0..count {
        operations.push(decode_operation(decoder)?);
    }
    Ok(TernaryFunction {
        id,
        name,
        operations,
        span,
    })
}

fn decode_functions(
    decoder: &mut Decoder<'_>,
) -> Result<Vec<TernaryFunction>, TernaryProgramCodecError> {
    let count = decoder.count(FUNCTION_MIN_BYTES)?;
    let mut functions = Vec::new();
    for _ in 0..count {
        functions.push(decode_function(decoder)?);
    }
    Ok(functions)
}

fn decode_bitwise_operation(
    decoder: &mut Decoder<'_>,
    tag: u8,
) -> Result<TernaryOperation, TernaryProgramCodecError> {
    let left = decoder.u32()?;
    let result = decoder.u32()?;
    let right = decoder.u32()?;
    let span = decode_span(decoder)?;
    Ok(match tag {
        0 => TernaryOperation::AndI32 {
            left,
            result,
            right,
            span,
        },
        6 => TernaryOperation::OrI32 {
            left,
            result,
            right,
            span,
        },
        7 => TernaryOperation::XorI32 {
            left,
            result,
            right,
            span,
        },
        12 => TernaryOperation::AndU32 {
            left,
            result,
            right,
            span,
        },
        13 => TernaryOperation::OrU32 {
            left,
            result,
            right,
            span,
        },
        14 => TernaryOperation::XorU32 {
            left,
            result,
            right,
            span,
        },
        _ => return Err(TernaryProgramCodecError::UnknownTag),
    })
}

fn decode_comparison_operation(
    decoder: &mut Decoder<'_>,
    tag: u8,
) -> Result<TernaryOperation, TernaryProgramCodecError> {
    let left = decoder.u32()?;
    let result = decoder.u32()?;
    let right = decoder.u32()?;
    let span = decode_span(decoder)?;
    Ok(match tag {
        35 => TernaryOperation::EqualI32 {
            left,
            result,
            right,
            span,
        },
        36 => TernaryOperation::EqualU32 {
            left,
            result,
            right,
            span,
        },
        37 => TernaryOperation::NotEqualI32 {
            left,
            result,
            right,
            span,
        },
        38 => TernaryOperation::NotEqualU32 {
            left,
            result,
            right,
            span,
        },
        _ => return Err(TernaryProgramCodecError::UnknownTag),
    })
}

fn decode_ordered_comparison_operation(
    decoder: &mut Decoder<'_>,
    tag: u8,
) -> Result<TernaryOperation, TernaryProgramCodecError> {
    let left = decoder.u32()?;
    let result = decoder.u32()?;
    let right = decoder.u32()?;
    let span = decode_span(decoder)?;
    Ok(match tag {
        40 => TernaryOperation::LessSignedI32 {
            left,
            result,
            right,
            span,
        },
        41 => TernaryOperation::LessSignedEqualI32 {
            left,
            result,
            right,
            span,
        },
        42 => TernaryOperation::LessUnsignedU32 {
            left,
            result,
            right,
            span,
        },
        43 => TernaryOperation::LessUnsignedEqualU32 {
            left,
            result,
            right,
            span,
        },
        _ => return Err(TernaryProgramCodecError::UnknownTag),
    })
}

fn decode_arithmetic_operation(
    decoder: &mut Decoder<'_>,
    tag: u8,
) -> Result<TernaryOperation, TernaryProgramCodecError> {
    let left = decoder.u32()?;
    let result = decoder.u32()?;
    let right = decoder.u32()?;
    let span = decode_span(decoder)?;
    Ok(match tag {
        19 => TernaryOperation::AddI32 {
            left,
            result,
            right,
            span,
        },
        20 => TernaryOperation::AddU32 {
            left,
            result,
            right,
            span,
        },
        21 => TernaryOperation::SubtractI32 {
            left,
            result,
            right,
            span,
        },
        22 => TernaryOperation::SubtractU32 {
            left,
            result,
            right,
            span,
        },
        23 => TernaryOperation::MultiplyI32 {
            left,
            result,
            right,
            span,
        },
        24 => TernaryOperation::MultiplyU32 {
            left,
            result,
            right,
            span,
        },
        _ => return Err(TernaryProgramCodecError::UnknownTag),
    })
}

fn decode_divrem_operation(
    decoder: &mut Decoder<'_>,
    tag: u8,
) -> Result<TernaryOperation, TernaryProgramCodecError> {
    let left = decoder.u32()?;
    let result = decoder.u32()?;
    let right = decoder.u32()?;
    let span = decode_span(decoder)?;
    Ok(match tag {
        29 => TernaryOperation::DivideI32 {
            left,
            result,
            right,
            span,
        },
        30 => TernaryOperation::DivideU32 {
            left,
            result,
            right,
            span,
        },
        31 => TernaryOperation::RemainderI32 {
            left,
            result,
            right,
            span,
        },
        32 => TernaryOperation::RemainderU32 {
            left,
            result,
            right,
            span,
        },
        _ => return Err(TernaryProgramCodecError::UnknownTag),
    })
}

fn decode_shift_operation(
    decoder: &mut Decoder<'_>,
    tag: u8,
) -> Result<TernaryOperation, TernaryProgramCodecError> {
    let left = decoder.u32()?;
    let result = decoder.u32()?;
    let right = decoder.u32()?;
    let span = decode_span(decoder)?;
    Ok(match tag {
        25 => TernaryOperation::ShiftLeftI32 {
            left,
            result,
            right,
            span,
        },
        26 => TernaryOperation::ShiftLeftU32 {
            left,
            result,
            right,
            span,
        },
        27 => TernaryOperation::ShiftRightArithmeticI32 {
            left,
            result,
            right,
            span,
        },
        28 => TernaryOperation::ShiftRightLogicalU32 {
            left,
            result,
            right,
            span,
        },
        _ => return Err(TernaryProgramCodecError::UnknownTag),
    })
}

fn decode_cast_operation(
    decoder: &mut Decoder<'_>,
    tag: u8,
) -> Result<TernaryOperation, TernaryProgramCodecError> {
    let result = decoder.u32()?;
    let span = decode_span(decoder)?;
    let value = decoder.u32()?;
    Ok(match tag {
        5 => TernaryOperation::TruncateI32ToU8 { result, span, value },
        15 => TernaryOperation::TruncateU32ToU8 { result, span, value },
        16 => TernaryOperation::ZeroExtendU8ToU32 { result, span, value },
        17 => TernaryOperation::BitcastI32ToU32 { result, span, value },
        18 => TernaryOperation::BitcastU32ToI32 { result, span, value },
        33 => TernaryOperation::BitcastI32ToI32 { result, span, value },
        34 => TernaryOperation::BitcastU32ToU32 { result, span, value },
        44 => TernaryOperation::BoolToI32 { result, span, value },
        45 => TernaryOperation::I32ToBool { result, span, value },
        46 => TernaryOperation::U32ToBool { result, span, value },
        47 => TernaryOperation::U8ToBool { result, span, value },
        _ => return Err(TernaryProgramCodecError::UnknownTag),
    })
}

fn decode_boolean_constant(
    decoder: &mut Decoder<'_>,
) -> Result<TernaryOperation, TernaryProgramCodecError> {
    let result = decoder.u32()?;
    let value = match decoder.u8()? {
        0 => false,
        1 => true,
        _ => return Err(TernaryProgramCodecError::InvalidScalar),
    };
    let span = decode_span(decoder)?;
    Ok(TernaryOperation::MaterializeBool { result, value, span })
}

fn decode_operation(
    decoder: &mut Decoder<'_>,
) -> Result<TernaryOperation, TernaryProgramCodecError> {
    let tag = decoder.u8()?;
    let operation = match tag {
        0 => decode_bitwise_operation(decoder, 0)?,
        1 => TernaryOperation::ByteInput {
            result: decoder.u32()?,
            span: decode_span(decoder)?,
        },
        2 => TernaryOperation::ByteOutput {
            span: decode_span(decoder)?,
            value: decoder.u32()?,
        },
        3 => TernaryOperation::MaterializeI32 {
            result: decoder.u32()?,
            scalar: decoder.scalar()?,
            span: decode_span(decoder)?,
        },
        4 => TernaryOperation::Return {
            span: decode_span(decoder)?,
            value: decoder.u32()?,
        },
        6 => decode_bitwise_operation(decoder, 6)?,
        7 => decode_bitwise_operation(decoder, 7)?,
        48 => decode_boolean_constant(decoder)?,
        8 => TernaryOperation::MaterializeU8 {
            result: decoder.u32()?,
            scalar: decoder.byte_scalar()?,
            span: decode_span(decoder)?,
        },
        9 => TernaryOperation::ReturnU8 {
            span: decode_span(decoder)?,
            value: decoder.u32()?,
        },
        10 => TernaryOperation::MaterializeU32 {
            result: decoder.u32()?,
            scalar: decoder.scalar()?,
            span: decode_span(decoder)?,
        },
        39 => TernaryOperation::ReturnBool {
            span: decode_span(decoder)?,
            value: decoder.u32()?,
        },
        11 => TernaryOperation::ReturnU32 {
            span: decode_span(decoder)?,
            value: decoder.u32()?,
        },
        12 => decode_bitwise_operation(decoder, 12)?,
        13 => decode_bitwise_operation(decoder, 13)?,
        14 => decode_bitwise_operation(decoder, 14)?,
        5 | 15 | 16 | 17 | 18 | 33..=34 | 44..=47 => {
            decode_cast_operation(decoder, tag)?
        },
        19..=24 => decode_arithmetic_operation(decoder, tag)?,
        25..=28 => decode_shift_operation(decoder, tag)?,
        29..=32 => decode_divrem_operation(decoder, tag)?,
        35..=38 => decode_comparison_operation(decoder, tag)?,
        40..=43 => decode_ordered_comparison_operation(decoder, tag)?,
        _ => return Err(TernaryProgramCodecError::UnknownTag),
    };
    Ok(operation)
}

fn decode_position(
    decoder: &mut Decoder<'_>,
) -> Result<TernarySourcePosition, TernaryProgramCodecError> {
    Ok(TernarySourcePosition {
        byte: decoder.u32()?,
        column: decoder.u32()?,
        line: decoder.u32()?,
    })
}

fn decode_span(
    decoder: &mut Decoder<'_>,
) -> Result<TernarySourceSpan, TernaryProgramCodecError> {
    Ok(TernarySourceSpan {
        begin: decode_position(decoder)?,
        end: decode_position(decoder)?,
    })
}

fn encode_function(
    encoder: &mut Encoder,
    function: &TernaryFunction,
) -> Result<(), TernaryProgramCodecError> {
    encoder.u32(function.id);
    encoder.string(&function.name)?;
    encode_span(encoder, function.span);
    encoder.length(function.operations.len())?;
    for operation in &function.operations {
        encode_operation(encoder, *operation);
    }
    Ok(())
}

fn encode_functions(
    encoder: &mut Encoder,
    functions: &[TernaryFunction],
) -> Result<(), TernaryProgramCodecError> {
    encoder.length(functions.len())?;
    for function in functions {
        encode_function(encoder, function)?;
    }
    Ok(())
}

fn encode_byte_output(
    encoder: &mut Encoder,
    span: TernarySourceSpan,
    value: u32,
) {
    encoder.u8(2);
    encode_span(encoder, span);
    encoder.u32(value);
}

fn encode_byte_scalar(
    encoder: &mut Encoder,
    result: u32,
    scalar: TernaryU8Scalar,
    span: TernarySourceSpan,
) {
    encoder.u8(8);
    encoder.u32(result);
    encoder.byte_scalar(scalar);
    encode_span(encoder, span);
}

fn encode_bitwise_operation(
    encoder: &mut Encoder,
    tag: u8,
    operands: (u32, u32, u32, TernarySourceSpan),
) {
    let (left, result, right, span) = operands;
    encoder.u8(tag);
    encoder.u32(left);
    encoder.u32(result);
    encoder.u32(right);
    encode_span(encoder, span);
}

fn encode_comparison_model(encoder: &mut Encoder, operation: TernaryOperation) {
    if let TernaryOperation::EqualI32 {
        left,
        result,
        right,
        span,
    }
    | TernaryOperation::EqualU32 {
        left,
        result,
        right,
        span,
    }
    | TernaryOperation::NotEqualI32 {
        left,
        result,
        right,
        span,
    }
    | TernaryOperation::NotEqualU32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        let tag = if matches!(operation, TernaryOperation::EqualI32 { .. }) {
            35
        } else if matches!(operation, TernaryOperation::EqualU32 { .. }) {
            36
        } else if matches!(operation, TernaryOperation::NotEqualI32 { .. }) {
            37
        } else {
            38
        };
        encode_bitwise_operation(encoder, tag, (left, result, right, span));
        return;
    }
    debug_assert!(false, "non-comparison reached comparison encoder");
}

fn encode_ordered_comparison_model(
    encoder: &mut Encoder,
    operation: TernaryOperation,
) {
    if let TernaryOperation::LessSignedI32 {
        left,
        result,
        right,
        span,
    }
    | TernaryOperation::LessSignedEqualI32 {
        left,
        result,
        right,
        span,
    }
    | TernaryOperation::LessUnsignedU32 {
        left,
        result,
        right,
        span,
    }
    | TernaryOperation::LessUnsignedEqualU32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        let tag = if matches!(operation, TernaryOperation::LessSignedI32 { .. })
        {
            40
        } else if matches!(
            operation,
            TernaryOperation::LessSignedEqualI32 { .. }
        ) {
            41
        } else if matches!(operation, TernaryOperation::LessUnsignedU32 { .. })
        {
            42
        } else {
            43
        };
        encode_bitwise_operation(encoder, tag, (left, result, right, span));
        return;
    }
    debug_assert!(false, "non-ordered comparison reached ordered encoder");
}

fn encode_byte_input(
    encoder: &mut Encoder,
    result: u32,
    span: TernarySourceSpan,
) {
    encoder.u8(1);
    encoder.u32(result);
    encode_span(encoder, span);
}

fn encode_return_operation(
    encoder: &mut Encoder,
    tag: u8,
    span: TernarySourceSpan,
    value: u32,
) {
    encoder.u8(tag);
    encode_span(encoder, span);
    encoder.u32(value);
}

fn encode_ternary_scalar(
    encoder: &mut Encoder,
    tag: u8,
    payload: (u32, TernaryI32Scalar, TernarySourceSpan),
) {
    let (result, scalar, span) = payload;
    encoder.u8(tag);
    encoder.u32(result);
    encoder.scalar(&scalar);
    encode_span(encoder, span);
}

fn encode_arithmetic_model(encoder: &mut Encoder, operation: TernaryOperation) {
    if let TernaryOperation::AddI32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 19, (left, result, right, span));
        return;
    }
    if let TernaryOperation::AddU32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 20, (left, result, right, span));
        return;
    }
    encode_arithmetic_model_tail(encoder, operation);
}

fn encode_arithmetic_model_tail(
    encoder: &mut Encoder,
    operation: TernaryOperation,
) {
    if let TernaryOperation::SubtractI32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 21, (left, result, right, span));
        return;
    }
    if let TernaryOperation::SubtractU32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 22, (left, result, right, span));
        return;
    }
    if let TernaryOperation::MultiplyI32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 23, (left, result, right, span));
        return;
    }
    if let TernaryOperation::MultiplyU32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 24, (left, result, right, span));
        return;
    }
    debug_assert!(false, "wrong binary operation family reached encoder");
}

fn encode_divrem_model(encoder: &mut Encoder, operation: TernaryOperation) {
    if let TernaryOperation::DivideI32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 29, (left, result, right, span));
        return;
    }
    if let TernaryOperation::DivideU32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 30, (left, result, right, span));
        return;
    }
    if let TernaryOperation::RemainderI32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 31, (left, result, right, span));
        return;
    }
    if let TernaryOperation::RemainderU32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 32, (left, result, right, span));
        return;
    }
    debug_assert!(false, "non-divrem instruction reached divrem encoder");
}

fn encode_shift_model(encoder: &mut Encoder, operation: TernaryOperation) {
    if let TernaryOperation::ShiftLeftI32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 25, (left, result, right, span));
        return;
    }
    if let TernaryOperation::ShiftLeftU32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 26, (left, result, right, span));
        return;
    }
    if let TernaryOperation::ShiftRightArithmeticI32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 27, (left, result, right, span));
        return;
    }
    if let TernaryOperation::ShiftRightLogicalU32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 28, (left, result, right, span));
        return;
    }
    debug_assert!(false, "non-shift instruction reached shift encoder");
}

fn encode_bitwise_model(encoder: &mut Encoder, operation: TernaryOperation) {
    if let TernaryOperation::AndI32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 0, (left, result, right, span));
        return;
    }
    if let TernaryOperation::AndU32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 12, (left, result, right, span));
        return;
    }
    encode_bitwise_model_tail(encoder, operation);
}

fn encode_bitwise_model_tail(
    encoder: &mut Encoder,
    operation: TernaryOperation,
) {
    if let TernaryOperation::OrI32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 6, (left, result, right, span));
        return;
    }
    if let TernaryOperation::OrU32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 13, (left, result, right, span));
        return;
    }
    if let TernaryOperation::XorI32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 7, (left, result, right, span));
        return;
    }
    if let TernaryOperation::XorU32 {
        left,
        result,
        right,
        span,
    } = operation
    {
        encode_bitwise_operation(encoder, 14, (left, result, right, span));
        return;
    }
    debug_assert!(false, "wrong binary operation family reached encoder");
}

const fn cast_tag(operation: TernaryOperation) -> u8 {
    if matches!(operation, TernaryOperation::TruncateI32ToU8 { .. }) {
        5
    } else if matches!(operation, TernaryOperation::TruncateU32ToU8 { .. }) {
        15
    } else if matches!(operation, TernaryOperation::ZeroExtendU8ToU32 { .. }) {
        16
    } else {
        bool_and_bitcast_tag(operation)
    }
}

const fn bool_and_bitcast_tag(operation: TernaryOperation) -> u8 {
    if matches!(operation, TernaryOperation::BoolToI32 { .. }) {
        44
    } else if matches!(operation, TernaryOperation::I32ToBool { .. }) {
        45
    } else if matches!(operation, TernaryOperation::U32ToBool { .. }) {
        46
    } else if matches!(operation, TernaryOperation::U8ToBool { .. }) {
        47
    } else {
        bitcast_tag(operation)
    }
}

const fn bitcast_tag(operation: TernaryOperation) -> u8 {
    if matches!(operation, TernaryOperation::BitcastI32ToU32 { .. }) {
        17
    } else if matches!(operation, TernaryOperation::BitcastU32ToI32 { .. }) {
        18
    } else if matches!(operation, TernaryOperation::BitcastI32ToI32 { .. }) {
        33
    } else {
        34
    }
}

fn encode_cast_model(encoder: &mut Encoder, operation: TernaryOperation) {
    let (TernaryOperation::I32ToBool { result, span, value }
    | TernaryOperation::U32ToBool { result, span, value }
    | TernaryOperation::U8ToBool { result, span, value }
    | TernaryOperation::BoolToI32 { result, span, value }
    | TernaryOperation::TruncateI32ToU8 { result, span, value }
    | TernaryOperation::TruncateU32ToU8 { result, span, value }
    | TernaryOperation::ZeroExtendU8ToU32 { result, span, value }
    | TernaryOperation::BitcastI32ToU32 { result, span, value }
    | TernaryOperation::BitcastU32ToI32 { result, span, value }
    | TernaryOperation::BitcastI32ToI32 { result, span, value }
    | TernaryOperation::BitcastU32ToU32 { result, span, value }) = operation
    else {
        debug_assert!(false, "non-cast instruction reached cast encoder");
        return;
    };
    let tag = cast_tag(operation);
    encoder.u8(tag);
    encoder.u32(result);
    encode_span(encoder, span);
    encoder.u32(value);
}

fn encode_return_model(
    encoder: &mut Encoder,
    operation: TernaryOperation,
    span: TernarySourceSpan,
    value: u32,
) {
    let tag = if matches!(operation, TernaryOperation::Return { .. }) {
        4
    } else if matches!(operation, TernaryOperation::ReturnU32 { .. }) {
        11
    } else if matches!(operation, TernaryOperation::ReturnBool { .. }) {
        39
    } else {
        9
    };
    encode_return_operation(encoder, tag, span, value);
}

fn encode_large_scalar_model(
    encoder: &mut Encoder,
    operation: TernaryOperation,
    payload: (u32, TernaryI32Scalar, TernarySourceSpan),
) {
    let (result, scalar, span) = payload;
    let tag = if matches!(operation, TernaryOperation::MaterializeI32 { .. }) {
        3
    } else {
        10
    };
    encode_ternary_scalar(encoder, tag, (result, scalar, span));
}

fn encode_byte_effect(encoder: &mut Encoder, operation: TernaryOperation) {
    if let TernaryOperation::ByteInput { result, span } = operation {
        encode_byte_input(encoder, result, span);
        return;
    }
    if let TernaryOperation::ByteOutput { span, value } = operation {
        encode_byte_output(encoder, span, value);
        return;
    }
    debug_assert!(false, "non-byte effect reached byte encoder");
}

fn try_encode_word_operation(
    encoder: &mut Encoder,
    operation: TernaryOperation,
) -> bool {
    if matches!(
        operation,
        TernaryOperation::AddI32 { .. }
            | TernaryOperation::AddU32 { .. }
            | TernaryOperation::SubtractI32 { .. }
            | TernaryOperation::SubtractU32 { .. }
            | TernaryOperation::MultiplyI32 { .. }
            | TernaryOperation::MultiplyU32 { .. }
    ) {
        encode_arithmetic_model(encoder, operation);
        return true;
    }
    if matches!(
        operation,
        TernaryOperation::DivideI32 { .. }
            | TernaryOperation::DivideU32 { .. }
            | TernaryOperation::RemainderI32 { .. }
            | TernaryOperation::RemainderU32 { .. }
    ) {
        encode_divrem_model(encoder, operation);
        return true;
    }
    if matches!(
        operation,
        TernaryOperation::ShiftLeftI32 { .. }
            | TernaryOperation::ShiftLeftU32 { .. }
            | TernaryOperation::ShiftRightArithmeticI32 { .. }
            | TernaryOperation::ShiftRightLogicalU32 { .. }
    ) {
        encode_shift_model(encoder, operation);
        return true;
    }
    if matches!(
        operation,
        TernaryOperation::AndI32 { .. }
            | TernaryOperation::AndU32 { .. }
            | TernaryOperation::OrI32 { .. }
            | TernaryOperation::OrU32 { .. }
            | TernaryOperation::XorI32 { .. }
            | TernaryOperation::XorU32 { .. }
    ) {
        encode_bitwise_model(encoder, operation);
        return true;
    }
    try_encode_comparison_operation(encoder, operation)
}

fn try_encode_comparison_operation(
    encoder: &mut Encoder,
    operation: TernaryOperation,
) -> bool {
    if matches!(
        operation,
        TernaryOperation::EqualI32 { .. }
            | TernaryOperation::EqualU32 { .. }
            | TernaryOperation::NotEqualI32 { .. }
            | TernaryOperation::NotEqualU32 { .. }
    ) {
        encode_comparison_model(encoder, operation);
        return true;
    }
    if matches!(
        operation,
        TernaryOperation::LessSignedI32 { .. }
            | TernaryOperation::LessSignedEqualI32 { .. }
            | TernaryOperation::LessUnsignedU32 { .. }
            | TernaryOperation::LessUnsignedEqualU32 { .. }
    ) {
        encode_ordered_comparison_model(encoder, operation);
        return true;
    }
    false
}

fn encode_non_word_operation(
    encoder: &mut Encoder,
    operation: TernaryOperation,
) {
    if matches!(
        operation,
        TernaryOperation::ByteInput { .. }
            | TernaryOperation::ByteOutput { .. }
    ) {
        encode_byte_effect(encoder, operation);
        return;
    }
    if let TernaryOperation::MaterializeI32 { result, scalar, span }
    | TernaryOperation::MaterializeU32 { result, scalar, span } = operation
    {
        encode_large_scalar_model(encoder, operation, (result, scalar, span));
        return;
    }
    if let TernaryOperation::MaterializeBool { result, value, span } = operation
    {
        encoder.u8(48);
        encoder.u32(result);
        encoder.u8(u8::from(value));
        encode_span(encoder, span);
        return;
    }
    if let TernaryOperation::MaterializeU8 { result, scalar, span } = operation
    {
        encode_byte_scalar(encoder, result, scalar, span);
        return;
    }
    if let TernaryOperation::Return { span, value }
    | TernaryOperation::ReturnBool { span, value }
    | TernaryOperation::ReturnU32 { span, value }
    | TernaryOperation::ReturnU8 { span, value } = operation
    {
        encode_return_model(encoder, operation, span, value);
        return;
    }
    if matches!(
        operation,
        TernaryOperation::I32ToBool { .. }
            | TernaryOperation::U32ToBool { .. }
            | TernaryOperation::U8ToBool { .. }
            | TernaryOperation::BoolToI32 { .. }
            | TernaryOperation::TruncateI32ToU8 { .. }
            | TernaryOperation::TruncateU32ToU8 { .. }
            | TernaryOperation::ZeroExtendU8ToU32 { .. }
            | TernaryOperation::BitcastI32ToU32 { .. }
            | TernaryOperation::BitcastU32ToI32 { .. }
            | TernaryOperation::BitcastI32ToI32 { .. }
            | TernaryOperation::BitcastU32ToU32 { .. }
    ) {
        encode_cast_model(encoder, operation);
        return;
    }
    debug_assert!(false, "word operation reached scalar encoder");
}

fn encode_operation(encoder: &mut Encoder, operation: TernaryOperation) {
    if !try_encode_word_operation(encoder, operation) {
        encode_non_word_operation(encoder, operation);
    }
}

fn encode_position(encoder: &mut Encoder, position: TernarySourcePosition) {
    encoder.u32(position.byte);
    encoder.u32(position.column);
    encoder.u32(position.line);
}

fn encode_span(encoder: &mut Encoder, span: TernarySourceSpan) {
    encode_position(encoder, span.begin);
    encode_position(encoder, span.end);
}

fn insert_value(
    values: &mut BTreeMap<u32, ValueKind>,
    result: u32,
    kind: ValueKind,
) -> Result<(), TernaryProgramValidationError> {
    let expected = u32::try_from(values.len())
        .map_err(|_error| TernaryProgramValidationError::SsaValue)?;
    if result != expected || values.insert(result, kind).is_some() {
        return Err(TernaryProgramValidationError::SsaValue);
    }
    Ok(())
}

const fn operation_span(operation: TernaryOperation) -> TernarySourceSpan {
    match operation {
        TernaryOperation::AddI32 { span, .. }
        | TernaryOperation::AddU32 { span, .. }
        | TernaryOperation::SubtractI32 { span, .. }
        | TernaryOperation::SubtractU32 { span, .. }
        | TernaryOperation::DivideI32 { span, .. }
        | TernaryOperation::DivideU32 { span, .. }
        | TernaryOperation::RemainderI32 { span, .. }
        | TernaryOperation::RemainderU32 { span, .. }
        | TernaryOperation::MultiplyI32 { span, .. }
        | TernaryOperation::MultiplyU32 { span, .. }
        | TernaryOperation::ShiftLeftI32 { span, .. }
        | TernaryOperation::ShiftLeftU32 { span, .. }
        | TernaryOperation::ShiftRightArithmeticI32 { span, .. }
        | TernaryOperation::ShiftRightLogicalU32 { span, .. }
        | TernaryOperation::AndI32 { span, .. }
        | TernaryOperation::AndU32 { span, .. }
        | TernaryOperation::OrU32 { span, .. }
        | TernaryOperation::XorU32 { span, .. }
        | TernaryOperation::OrI32 { span, .. }
        | TernaryOperation::XorI32 { span, .. }
        | TernaryOperation::EqualI32 { span, .. }
        | TernaryOperation::EqualU32 { span, .. }
        | TernaryOperation::NotEqualI32 { span, .. }
        | TernaryOperation::LessSignedEqualI32 { span, .. }
        | TernaryOperation::LessSignedI32 { span, .. }
        | TernaryOperation::LessUnsignedEqualU32 { span, .. }
        | TernaryOperation::LessUnsignedU32 { span, .. }
        | TernaryOperation::NotEqualU32 { span, .. }
        | TernaryOperation::ReturnBool { span, .. }
        | TernaryOperation::BoolToI32 { span, .. }
        | TernaryOperation::I32ToBool { span, .. }
        | TernaryOperation::U32ToBool { span, .. }
        | TernaryOperation::U8ToBool { span, .. }
        | TernaryOperation::ByteInput { span, .. }
        | TernaryOperation::ByteOutput { span, .. }
        | TernaryOperation::MaterializeBool { span, .. }
        | TernaryOperation::MaterializeI32 { span, .. }
        | TernaryOperation::MaterializeU32 { span, .. }
        | TernaryOperation::MaterializeU8 { span, .. }
        | TernaryOperation::Return { span, .. }
        | TernaryOperation::ReturnU32 { span, .. }
        | TernaryOperation::ReturnU8 { span, .. }
        | TernaryOperation::TruncateI32ToU8 { span, .. }
        | TernaryOperation::TruncateU32ToU8 { span, .. }
        | TernaryOperation::ZeroExtendU8ToU32 { span, .. }
        | TernaryOperation::BitcastI32ToU32 { span, .. }
        | TernaryOperation::BitcastU32ToI32 { span, .. }
        | TernaryOperation::BitcastI32ToI32 { span, .. }
        | TernaryOperation::BitcastU32ToU32 { span, .. } => span,
    }
}

fn require_value(
    values: &BTreeMap<u32, ValueKind>,
    value: u32,
    kind: ValueKind,
) -> Result<(), TernaryProgramValidationError> {
    if values.get(&value) != Some(&kind) {
        return Err(TernaryProgramValidationError::SsaValue);
    }
    Ok(())
}

const fn span_contains(
    parent: TernarySourceSpan,
    child: TernarySourceSpan,
) -> bool {
    parent.begin.byte <= child.begin.byte && child.end.byte <= parent.end.byte
}

fn valid_name(name: &str) -> bool {
    !name.is_empty() && !name.contains('\0')
}

const fn valid_position(position: TernarySourcePosition) -> bool {
    position.line != 0 && position.column != 0
}

fn valid_source_id(source_id: &str) -> bool {
    !source_id.is_empty()
        && !source_id.starts_with('/')
        && !source_id.contains('\\')
        && !source_id.contains(':')
        && !source_id.contains('\0')
        && !source_id
            .split('/')
            .any(|part| part.is_empty() || part == "." || part == "..")
}

const fn valid_span(span: TernarySourceSpan) -> bool {
    let begin = span.begin;
    let end = span.end;
    if !valid_position(begin) || !valid_position(end) || begin.byte > end.byte {
        return false;
    }
    if begin.byte == end.byte {
        return begin.line == end.line && begin.column == end.column;
    }
    begin.line < end.line
        || (begin.line == end.line && begin.column <= end.column)
}

fn validate_function(
    function: &TernaryFunction,
    index: usize,
    names: &mut BTreeSet<String>,
) -> Result<(), TernaryProgramValidationError> {
    let expected = u32::try_from(index)
        .map_err(|_error| TernaryProgramValidationError::FunctionIdentity)?;
    if function.id != expected
        || !valid_name(&function.name)
        || !names.insert(function.name.clone())
        || !valid_span(function.span)
    {
        return Err(TernaryProgramValidationError::FunctionIdentity);
    }
    validate_operations(function)
}

fn validate_bitwise_values(
    values: &mut BTreeMap<u32, ValueKind>,
    operands: (u32, u32, u32),
    kind: ValueKind,
) -> Result<bool, TernaryProgramValidationError> {
    let (left, result, right) = operands;
    require_value(values, left, kind)?;
    require_value(values, right, kind)?;
    insert_value(values, result, kind)?;
    Ok(false)
}

fn validate_large_scalar(
    values: &mut BTreeMap<u32, ValueKind>,
    result: u32,
    scalar: TernaryI32Scalar,
    kind: ValueKind,
) -> Result<bool, TernaryProgramValidationError> {
    if scalar.trits().iter().any(|trit| *trit > 2)
        || TernaryI32Scalar::from_bits(scalar.bits()) != scalar
    {
        return Err(TernaryProgramValidationError::SsaValue);
    }
    insert_value(values, result, kind)?;
    Ok(false)
}

fn validate_truncated_value(
    values: &mut BTreeMap<u32, ValueKind>,
    result: u32,
    value: u32,
    source_kind: ValueKind,
) -> Result<bool, TernaryProgramValidationError> {
    require_value(values, value, source_kind)?;
    insert_value(values, result, ValueKind::Byte)?;
    Ok(false)
}

fn validate_byte_scalar(
    values: &mut BTreeMap<u32, ValueKind>,
    result: u32,
    scalar: TernaryU8Scalar,
) -> Result<bool, TernaryProgramValidationError> {
    if scalar.trits().iter().any(|trit| *trit > 2)
        || TernaryU8Scalar::from_bits(scalar.bits()) != scalar
    {
        return Err(TernaryProgramValidationError::SsaValue);
    }
    insert_value(values, result, ValueKind::Byte)?;
    Ok(false)
}

fn validate_reinterpret_value(
    values: &mut BTreeMap<u32, ValueKind>,
    result: u32,
    value: u32,
    types: (ValueKind, ValueKind),
) -> Result<bool, TernaryProgramValidationError> {
    let (source_kind, destination_kind) = types;
    require_value(values, value, source_kind)?;
    insert_value(values, result, destination_kind)?;
    Ok(false)
}

fn validate_widen_or_bitcast(
    values: &mut BTreeMap<u32, ValueKind>,
    operation: TernaryOperation,
) -> Result<bool, TernaryProgramValidationError> {
    let (result, value, types) = if let TernaryOperation::I32ToBool {
        result,
        value,
        ..
    } = operation
    {
        (result, value, (ValueKind::I32, ValueKind::Bool))
    } else if let TernaryOperation::U32ToBool { result, value, .. } = operation
    {
        (result, value, (ValueKind::U32, ValueKind::Bool))
    } else if let TernaryOperation::U8ToBool { result, value, .. } = operation {
        (result, value, (ValueKind::Byte, ValueKind::Bool))
    } else if let TernaryOperation::BoolToI32 { result, value, .. } = operation
    {
        (result, value, (ValueKind::Bool, ValueKind::I32))
    } else if let TernaryOperation::ZeroExtendU8ToU32 {
        result, value, ..
    } = operation
    {
        (result, value, (ValueKind::Byte, ValueKind::U32))
    } else if let TernaryOperation::BitcastI32ToU32 { result, value, .. } =
        operation
    {
        (result, value, (ValueKind::I32, ValueKind::U32))
    } else if let TernaryOperation::BitcastU32ToI32 { result, value, .. } =
        operation
    {
        (result, value, (ValueKind::U32, ValueKind::I32))
    } else if let TernaryOperation::BitcastI32ToI32 { result, value, .. } =
        operation
    {
        (result, value, (ValueKind::I32, ValueKind::I32))
    } else if let TernaryOperation::BitcastU32ToU32 { result, value, .. } =
        operation
    {
        (result, value, (ValueKind::U32, ValueKind::U32))
    } else {
        return Err(TernaryProgramValidationError::SsaValue);
    };
    validate_reinterpret_value(values, result, value, types)
}

fn validate_return_value(
    values: &BTreeMap<u32, ValueKind>,
    value: u32,
    operation: TernaryOperation,
) -> Result<bool, TernaryProgramValidationError> {
    let kind = if matches!(operation, TernaryOperation::Return { .. }) {
        ValueKind::I32
    } else if matches!(operation, TernaryOperation::ReturnU32 { .. }) {
        ValueKind::U32
    } else if matches!(operation, TernaryOperation::ReturnBool { .. }) {
        ValueKind::Bool
    } else {
        ValueKind::Byte
    };
    require_value(values, value, kind)?;
    Ok(true)
}

fn validate_comparison_values(
    values: &mut BTreeMap<u32, ValueKind>,
    operands: (u32, u32, u32),
    kind: ValueKind,
) -> Result<bool, TernaryProgramValidationError> {
    let (left, result, right) = operands;
    require_value(values, left, kind)?;
    require_value(values, right, kind)?;
    insert_value(values, result, ValueKind::Bool)?;
    Ok(false)
}

fn validate_comparison_operation(
    operation: TernaryOperation,
    values: &mut BTreeMap<u32, ValueKind>,
) -> Option<Result<bool, TernaryProgramValidationError>> {
    if let TernaryOperation::EqualI32 { left, result, right, .. }
    | TernaryOperation::LessSignedI32 { left, result, right, .. }
    | TernaryOperation::LessSignedEqualI32 {
        left, result, right, ..
    }
    | TernaryOperation::NotEqualI32 { left, result, right, .. } = operation
    {
        return Some(validate_comparison_values(
            values,
            (left, result, right),
            ValueKind::I32,
        ));
    }
    if let TernaryOperation::EqualU32 { left, result, right, .. }
    | TernaryOperation::LessUnsignedU32 { left, result, right, .. }
    | TernaryOperation::LessUnsignedEqualU32 {
        left, result, right, ..
    }
    | TernaryOperation::NotEqualU32 { left, result, right, .. } = operation
    {
        return Some(validate_comparison_values(
            values,
            (left, result, right),
            ValueKind::U32,
        ));
    }
    None
}

fn validate_binary_operation(
    operation: TernaryOperation,
    values: &mut BTreeMap<u32, ValueKind>,
) -> Option<Result<bool, TernaryProgramValidationError>> {
    if let Some(outcome) = validate_comparison_operation(operation, values) {
        return Some(outcome);
    }
    if let TernaryOperation::AddI32 { left, result, right, .. }
    | TernaryOperation::SubtractI32 { left, result, right, .. }
    | TernaryOperation::DivideI32 { left, result, right, .. }
    | TernaryOperation::RemainderI32 { left, result, right, .. }
    | TernaryOperation::MultiplyI32 { left, result, right, .. }
    | TernaryOperation::ShiftLeftI32 { left, result, right, .. }
    | TernaryOperation::ShiftRightArithmeticI32 {
        left,
        result,
        right,
        ..
    }
    | TernaryOperation::AndI32 { left, result, right, .. }
    | TernaryOperation::OrI32 { left, result, right, .. }
    | TernaryOperation::XorI32 { left, result, right, .. } = operation
    {
        return Some(validate_bitwise_values(
            values,
            (left, result, right),
            ValueKind::I32,
        ));
    }
    if let TernaryOperation::AddU32 { left, result, right, .. }
    | TernaryOperation::SubtractU32 { left, result, right, .. }
    | TernaryOperation::DivideU32 { left, result, right, .. }
    | TernaryOperation::RemainderU32 { left, result, right, .. }
    | TernaryOperation::MultiplyU32 { left, result, right, .. }
    | TernaryOperation::ShiftLeftU32 { left, result, right, .. }
    | TernaryOperation::ShiftRightLogicalU32 {
        left, result, right, ..
    }
    | TernaryOperation::AndU32 { left, result, right, .. }
    | TernaryOperation::OrU32 { left, result, right, .. }
    | TernaryOperation::XorU32 { left, result, right, .. } = operation
    {
        return Some(validate_bitwise_values(
            values,
            (left, result, right),
            ValueKind::U32,
        ));
    }
    None
}

fn validate_byte_effect_operation(
    operation: TernaryOperation,
    values: &mut BTreeMap<u32, ValueKind>,
) -> Result<bool, TernaryProgramValidationError> {
    if let TernaryOperation::ByteInput { result, .. } = operation {
        return insert_value(values, result, ValueKind::Byte).map(|()| false);
    }
    if let TernaryOperation::ByteOutput { value, .. } = operation {
        return require_value(values, value, ValueKind::Byte).map(|()| false);
    }
    Err(TernaryProgramValidationError::SsaValue)
}

fn validate_materialize_operation(
    operation: TernaryOperation,
    values: &mut BTreeMap<u32, ValueKind>,
) -> Result<bool, TernaryProgramValidationError> {
    if let TernaryOperation::MaterializeBool { result, .. } = operation {
        return insert_value(values, result, ValueKind::Bool).map(|()| false);
    }
    if let TernaryOperation::MaterializeI32 { result, scalar, .. } = operation {
        return validate_large_scalar(values, result, scalar, ValueKind::I32);
    }
    if let TernaryOperation::MaterializeU32 { result, scalar, .. } = operation {
        return validate_large_scalar(values, result, scalar, ValueKind::U32);
    }
    if let TernaryOperation::MaterializeU8 { result, scalar, .. } = operation {
        return validate_byte_scalar(values, result, scalar);
    }
    Err(TernaryProgramValidationError::SsaValue)
}

fn validate_operation(
    operation: TernaryOperation,
    values: &mut BTreeMap<u32, ValueKind>,
) -> Result<bool, TernaryProgramValidationError> {
    if let Some(outcome) = validate_binary_operation(operation, values) {
        return outcome;
    }
    if matches!(
        operation,
        TernaryOperation::ByteInput { .. }
            | TernaryOperation::ByteOutput { .. }
    ) {
        return validate_byte_effect_operation(operation, values);
    }
    if matches!(
        operation,
        TernaryOperation::MaterializeBool { .. }
            | TernaryOperation::MaterializeI32 { .. }
            | TernaryOperation::MaterializeU32 { .. }
            | TernaryOperation::MaterializeU8 { .. }
    ) {
        return validate_materialize_operation(operation, values);
    }
    if let TernaryOperation::Return { value, .. }
    | TernaryOperation::ReturnU32 { value, .. }
    | TernaryOperation::ReturnU8 { value, .. }
    | TernaryOperation::ReturnBool { value, .. } = operation
    {
        return validate_return_value(values, value, operation);
    }
    if let TernaryOperation::TruncateI32ToU8 { result, value, .. } = operation {
        return validate_truncated_value(values, result, value, ValueKind::I32);
    }
    if let TernaryOperation::TruncateU32ToU8 { result, value, .. } = operation {
        return validate_truncated_value(values, result, value, ValueKind::U32);
    }
    if matches!(
        operation,
        TernaryOperation::I32ToBool { .. }
            | TernaryOperation::U32ToBool { .. }
            | TernaryOperation::U8ToBool { .. }
            | TernaryOperation::BoolToI32 { .. }
            | TernaryOperation::ZeroExtendU8ToU32 { .. }
            | TernaryOperation::BitcastI32ToU32 { .. }
            | TernaryOperation::BitcastU32ToI32 { .. }
            | TernaryOperation::BitcastI32ToI32 { .. }
            | TernaryOperation::BitcastU32ToU32 { .. }
    ) {
        return validate_widen_or_bitcast(values, operation);
    }
    Err(TernaryProgramValidationError::SsaValue)
}

fn validate_operations(
    function: &TernaryFunction,
) -> Result<(), TernaryProgramValidationError> {
    let mut values = BTreeMap::new();
    let Some((last, prefix)) = function.operations.split_last() else {
        return Err(TernaryProgramValidationError::Terminator);
    };
    for operation in prefix {
        if !valid_span(operation_span(*operation))
            || !span_contains(function.span, operation_span(*operation))
        {
            return Err(TernaryProgramValidationError::SourceProvenance);
        }
        if validate_operation(*operation, &mut values)? {
            return Err(TernaryProgramValidationError::Terminator);
        }
    }
    if !valid_span(operation_span(*last))
        || !span_contains(function.span, operation_span(*last))
    {
        return Err(TernaryProgramValidationError::SourceProvenance);
    }
    if !matches!(
        last,
        TernaryOperation::Return { .. }
            | TernaryOperation::ReturnU32 { .. }
            | TernaryOperation::ReturnU8 { .. }
            | TernaryOperation::ReturnBool { .. }
    ) || !validate_operation(*last, &mut values)?
    {
        return Err(TernaryProgramValidationError::Terminator);
    }
    Ok(())
}

/// Validates one pre-layout ternary program independently of its producer.
///
/// # Errors
///
/// Returns a stable invariant failure for malformed identity, provenance,
/// function ordering, SSA type/order, or terminator semantics.
pub fn validate_ternary_program(
    program: &TernaryProgram,
) -> Result<(), TernaryProgramValidationError> {
    if program.abi_id != ABI_ID
        || program.input_format_version != TYPED_IR_VERSION
        || program.target_profile != TARGET_PROFILE
        || !valid_source_id(&program.source_id)
    {
        return Err(TernaryProgramValidationError::ProgramIdentity);
    }
    let mut names = BTreeSet::new();
    for (index, function) in program.functions.iter().enumerate() {
        validate_function(function, index, &mut names)?;
    }
    Ok(())
}
