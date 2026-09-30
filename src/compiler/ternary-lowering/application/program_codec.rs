// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE-APACHE-2.0
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
    TernaryProgram, TernarySourcePosition, TernarySourceSpan,
};

const ABI_ID: &str = "malbolge-c32-v1";
const MAGIC: &[u8; 4] = b"MCTR";
const TARGET_PROFILE: &str = "malbolge-2026";
const TERNARY_WIRE_VERSION: u16 = 1;
const TYPED_IR_VERSION: u16 = 1;

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
    Byte,
    I32,
}

struct Decoder<'bytes> {
    bytes: &'bytes [u8],
    offset: usize,
}

impl<'bytes> Decoder<'bytes> {
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
    let count = decoder.count(1)?;
    let mut operations = Vec::with_capacity(count);
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
    let count = decoder.count(1)?;
    let mut functions = Vec::with_capacity(count);
    for _ in 0..count {
        functions.push(decode_function(decoder)?);
    }
    Ok(functions)
}

fn decode_operation(
    decoder: &mut Decoder<'_>,
) -> Result<TernaryOperation, TernaryProgramCodecError> {
    let operation = match decoder.u8()? {
        0 => TernaryOperation::AndI32 {
            left: decoder.u32()?,
            result: decoder.u32()?,
            right: decoder.u32()?,
            span: decode_span(decoder)?,
        },
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
        5 => TernaryOperation::TruncateI32ToU8 {
            result: decoder.u32()?,
            span: decode_span(decoder)?,
            value: decoder.u32()?,
        },
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

fn encode_operation(encoder: &mut Encoder, operation: TernaryOperation) {
    match operation {
        TernaryOperation::AndI32 {
            left,
            result,
            right,
            span,
        } => {
            encoder.u8(0);
            encoder.u32(left);
            encoder.u32(result);
            encoder.u32(right);
            encode_span(encoder, span);
        },
        TernaryOperation::ByteInput { result, span } => {
            encoder.u8(1);
            encoder.u32(result);
            encode_span(encoder, span);
        },
        TernaryOperation::ByteOutput { span, value } => {
            encoder.u8(2);
            encode_span(encoder, span);
            encoder.u32(value);
        },
        TernaryOperation::MaterializeI32 { result, scalar, span } => {
            encoder.u8(3);
            encoder.u32(result);
            encoder.scalar(&scalar);
            encode_span(encoder, span);
        },
        TernaryOperation::Return { span, value } => {
            encoder.u8(4);
            encode_span(encoder, span);
            encoder.u32(value);
        },
        TernaryOperation::TruncateI32ToU8 { result, span, value } => {
            encoder.u8(5);
            encoder.u32(result);
            encode_span(encoder, span);
            encoder.u32(value);
        },
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
        TernaryOperation::AndI32 { span, .. }
        | TernaryOperation::ByteInput { span, .. }
        | TernaryOperation::ByteOutput { span, .. }
        | TernaryOperation::MaterializeI32 { span, .. }
        | TernaryOperation::Return { span, .. }
        | TernaryOperation::TruncateI32ToU8 { span, .. } => span,
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

fn validate_operation(
    operation: TernaryOperation,
    values: &mut BTreeMap<u32, ValueKind>,
) -> Result<bool, TernaryProgramValidationError> {
    match operation {
        TernaryOperation::AndI32 { left, result, right, .. } => {
            require_value(values, left, ValueKind::I32)?;
            require_value(values, right, ValueKind::I32)?;
            insert_value(values, result, ValueKind::I32)?;
            Ok(false)
        },
        TernaryOperation::ByteInput { result, .. } => {
            insert_value(values, result, ValueKind::Byte)?;
            Ok(false)
        },
        TernaryOperation::ByteOutput { value, .. } => {
            require_value(values, value, ValueKind::Byte)?;
            Ok(false)
        },
        TernaryOperation::MaterializeI32 { result, scalar, .. } => {
            if scalar.trits().iter().any(|trit| *trit > 2) {
                return Err(TernaryProgramValidationError::SsaValue);
            }
            insert_value(values, result, ValueKind::I32)?;
            Ok(false)
        },
        TernaryOperation::Return { value, .. } => {
            require_value(values, value, ValueKind::I32)?;
            Ok(true)
        },
        TernaryOperation::TruncateI32ToU8 { result, value, .. } => {
            require_value(values, value, ValueKind::I32)?;
            insert_value(values, result, ValueKind::Byte)?;
            Ok(false)
        },
    }
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
    if !matches!(last, TernaryOperation::Return { .. })
        || !validate_operation(*last, &mut values)?
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
