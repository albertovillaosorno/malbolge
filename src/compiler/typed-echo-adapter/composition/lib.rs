// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Exact admitted typed-IR-to-ternary byte-I/O projections for one void
//     function, with canonical wire and verified graphical output.
// - Must-Not:
//   - Impersonate a C compiler, EOF/error semantics, or a full guest ABI.
// - Allows:
//   - Inputs: canonical typed-IR bytes and explicit target-profile descriptor.
//   - Outputs: canonical ternary bytes and independently admitted Malbolge code.
//   - Side effects: none.
// - Split-When:
//   - General typed-IR conversion needs a wider typed-IR semantics adapter.
// - Merge-When:
//   - A complete typed-IR-to-ternary compiler owns this exact admitted slice.
// - Summary:
//   - Closes the real typed-IR byte-I/O gap without caller-fabricated projection.
// - Description:
//   - Revalidates canonical typed IR and retains function/SSA/source provenance.
// - Usage:
//   - Call the strict echo or opt-in latest-read trace compiler with MCTI bytes.
// - Defaults:
//   - Unsupported typed operations and profiles reject before emission.
//
//! Narrow typed-IR-to-Malbolge bridge for successful-byte I/O traces.
//!
//! Unlike an external caller-provided projection, every effect originates from
//! the independently validated canonical typed-IR module. The result is only
//! equivalent when all guest reads and writes succeed, with void ABI ignored.

#[path = "../../byte-echo-bridge/composition/lib.rs"]
pub mod bridge;
#[path = "../../typed-ir/composition/lib.rs"]
pub mod typed;

use malbolge::ProfileDescriptor;
use std::collections::BTreeSet;

use bridge::layout::LinearLayout;
use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryLoweringError, TernaryProgramCodecError, TypedIrInput,
    canonical_ternary_bytes, canonical_ternary_program, lower_typed_ir,
};
use typed::{
    CanonicalDecodeError, CastOp, Instruction, Module, SourcePosition, SourceSpan, Terminator,
    TypeDef, TypeId, canonical_module,
};

/// A refused canonical typed-IR read, typed subset, ternary state or layout.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TypedEchoAdapterError {
    /// The produced canonical ternary bytes failed admission.
    InvalidTernary(TernaryProgramCodecError),
    /// The canonical typed-IR decoder independently rejected the input.
    InvalidTypedIr(CanonicalDecodeError),
    /// The verified ternary trace cannot be emitted to executable source.
    Layout(bridge::ByteEchoBridgeError),
    /// Fresh projection was rejected by the canonical ternary lowerer.
    Lowering(TernaryLoweringError),
    /// The complete typed module is outside the supported successful-byte trace.
    UnsupportedTypedIr,
}

/// Both stage identities produced by the accepted typed byte-I/O trace.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompiledTypedEcho {
    layout: LinearLayout,
    ternary_bytes: Vec<u8>,
}

impl CompiledTypedEcho {
    /// Returns the independently admitted position-sensitive source.
    #[must_use]
    pub const fn layout(&self) -> &LinearLayout {
        &self.layout
    }

    /// Returns canonical, independently decodable `MCTR` version-one bytes.
    #[must_use]
    pub fn ternary_bytes(&self) -> &[u8] {
        &self.ternary_bytes
    }
}

#[derive(Clone, Copy)]
enum ByteTraceMode {
    AdjacentEcho,
    DistinctLiteralPair,
    DistinctLiteralTriple,
    DistinctLiteralQuad,
    DistinctLiteralQuint,
    DistinctLiteralSix,
    DistinctLiteralSeven,
    DistinctLiteralEight,
    DistinctLiteralNine,
    DistinctLiteralTen,
    DistinctLiteralEleven,
    DistinctLiteralTwelve,
    DistinctLiteralThirteen,
    DistinctLiteralFourteen,
    DistinctLiteralFifteen,
    DistinctLiteralSixteen,
    DistinctLiteralSeventeen,
    DistinctLiteralEighteen,
    DistinctLiteralNineteen,
    DistinctLiteralTwenty,
    DistinctLiteralTwentyOne,
    DistinctLiteralTwentyTwo,
    DistinctLiteralTwentyThree,
    DistinctLiteralTwentyFour,
    DistinctLiteralTwentyFive,
    DistinctLiteralTwentySix,
    DistinctLiteralTwentySeven,
    DistinctLiteralTwentyEight,
    DistinctLiteralTwentyNine,
    DistinctLiteralThirty,
    DistinctLiteralThirtyOne,
    DistinctLiteralThirtyTwo,
    DistinctLiteralThirtyThree,
    DistinctLiteralThirtyFour,
    DistinctLiteralThirtyFive,
    DistinctLiteralThirtySix,
    DistinctLiteralThirtySeven,
    DistinctLiteralThirtyEight,
    DistinctLiteralThirtyNine,
    DistinctLiteralForty,
    EmptyVoid,
    IdentityByteBitcast,
    InitialZero,
    LatestRead,
    RotatedLiteral,
    ZeroPrefixedLatest,
    ZeroThenLiteral,
}

const fn project_position(position: SourcePosition) -> InputSourcePosition {
    InputSourcePosition {
        byte: position.byte(),
        column: position.column(),
        line: position.line(),
    }
}

const fn project_span(span: SourceSpan) -> InputSourceSpan {
    InputSourceSpan {
        begin: project_position(span.begin()),
        end: project_position(span.end()),
    }
}

fn is_byte_type(module: &Module, id: TypeId) -> bool {
    module
        .types()
        .iter()
        .any(|entry| entry.id() == id && *entry.definition() == TypeDef::U8)
}

fn project_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.is_empty() || pairs.len() > 2047 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(original.len());
    for [read, write] in pairs {
        let (Instruction::ByteInput { result, type_id }, Instruction::ByteOutput { value }) =
            (read.instruction(), write.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id) || result != value {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ByteInput {
            result: result.value(),
            span: project_span(read.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(write.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_latest_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    if original.is_empty() || original.len() >= 4096 {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut last_input = None;
    let mut instructions = Vec::with_capacity(original.len());
    for located in original {
        if let Instruction::ByteInput { result, type_id } = located.instruction() {
            if !is_byte_type(module, *type_id) {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            last_input = Some(*result);
            instructions.push(InputInstruction::ByteInput {
                result: result.value(),
                span: project_span(located.span()),
                type_kind: InputScalarType::U8,
            });
        } else if let Instruction::ByteOutput { value } = located.instruction() {
            if last_input != Some(*value) {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            instructions.push(InputInstruction::ByteOutput {
                span: project_span(located.span()),
                value: value.value(),
            });
        } else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
    }
    if last_input.is_none() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    Ok(instructions)
}

// An exact source u8 zero needs no materialization instruction: the normative
// guest VM starts with accumulator A=0. This shape never consumes guest input.
fn project_initial_zero_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let Some((first, outputs)) = original.split_first() else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    let Instruction::ConstantInteger {
        constant,
        result,
        type_id,
    } = first.instruction()
    else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    if !is_byte_type(module, *type_id)
        || constant.bit_width() != 8
        || constant.little_endian() != [0]
        || outputs.is_empty()
        || outputs.len() > 4095
    {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(original.len());
    instructions.push(InputInstruction::ConstantInteger {
        bit_width: constant.bit_width(),
        little_endian: constant.little_endian().to_vec(),
        result: result.value(),
        span: project_span(first.span()),
        type_kind: InputScalarType::U8,
    });
    for output in outputs {
        let Instruction::ByteOutput { value } = output.instruction() else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if value != result {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

// The guest computes one exact nonzero u8 with j then *, and can repeatedly
// emit the unchanged accumulator while the proven code/data layout is safe.
fn project_rotated_literal_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let Some((source, outputs)) = original.split_first() else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    let Instruction::ConstantInteger {
        constant,
        result,
        type_id,
    } = source.instruction()
    else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    if outputs.is_empty()
        || outputs.len() > 33
        || !is_byte_type(module, *type_id)
        || constant.bit_width() != 8
        || constant.little_endian().len() != 1
    {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(original.len());
    instructions.push(InputInstruction::ConstantInteger {
        bit_width: constant.bit_width(),
        little_endian: constant.little_endian().to_vec(),
        result: result.value(),
        span: project_span(source.span()),
        type_kind: InputScalarType::U8,
    });
    for output in outputs {
        let Instruction::ByteOutput { value } = output.instruction() else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if value != result {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

// Source-proven two distinct constants: zero then one of four witnessed
// printable bytes, or one of three independently witnessed nonzero pairs.
// Both modes retain exact source spans and separate SSA definitions.
fn project_literal_pair_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
    mode: ByteTraceMode,
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let [first, zero_output, second, second_output] = original else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    let (
        Instruction::ConstantInteger {
            constant: zero,
            result: zero_id,
            type_id: zero_type,
        },
        Instruction::ByteOutput { value: first_id },
        Instruction::ConstantInteger {
            constant: literal,
            result: literal_id,
            type_id: literal_type,
        },
        Instruction::ByteOutput { value: last_id },
    ) = (
        first.instruction(),
        zero_output.instruction(),
        second.instruction(),
        second_output.instruction(),
    )
    else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    if !is_byte_type(module, *zero_type)
        || !is_byte_type(module, *literal_type)
        || zero.bit_width() != 8
        || literal.bit_width() != 8
        || !match mode {
            ByteTraceMode::ZeroThenLiteral => {
                zero.little_endian() == [0]
                    && matches!(literal.little_endian(), [b'Z' | b'P' | b'T' | b'S'])
            }
            ByteTraceMode::DistinctLiteralTriple
            | ByteTraceMode::DistinctLiteralQuad
            | ByteTraceMode::DistinctLiteralQuint
            | ByteTraceMode::DistinctLiteralSix
            | ByteTraceMode::DistinctLiteralSeven
            | ByteTraceMode::DistinctLiteralEight
            | ByteTraceMode::DistinctLiteralNine
            | ByteTraceMode::DistinctLiteralTen
            | ByteTraceMode::DistinctLiteralEleven
            | ByteTraceMode::DistinctLiteralTwelve
            | ByteTraceMode::DistinctLiteralThirteen
            | ByteTraceMode::DistinctLiteralFourteen
            | ByteTraceMode::DistinctLiteralFifteen
            | ByteTraceMode::DistinctLiteralSixteen
            | ByteTraceMode::DistinctLiteralSeventeen
            | ByteTraceMode::DistinctLiteralEighteen
            | ByteTraceMode::DistinctLiteralNineteen
            | ByteTraceMode::DistinctLiteralTwenty
            | ByteTraceMode::DistinctLiteralTwentyOne
            | ByteTraceMode::DistinctLiteralTwentyTwo
            | ByteTraceMode::DistinctLiteralTwentyThree
            | ByteTraceMode::DistinctLiteralTwentyFour
            | ByteTraceMode::DistinctLiteralTwentyFive
            | ByteTraceMode::DistinctLiteralTwentySix
            | ByteTraceMode::DistinctLiteralTwentySeven
            | ByteTraceMode::DistinctLiteralTwentyEight
            | ByteTraceMode::DistinctLiteralTwentyNine
            | ByteTraceMode::DistinctLiteralThirty
            | ByteTraceMode::DistinctLiteralThirtyOne => false,
            | ByteTraceMode::DistinctLiteralThirtyTwo => false,
            | ByteTraceMode::DistinctLiteralThirtyThree
            | ByteTraceMode::DistinctLiteralThirtyFour
            | ByteTraceMode::DistinctLiteralThirtyFive
            | ByteTraceMode::DistinctLiteralThirtySix
            | ByteTraceMode::DistinctLiteralThirtySeven
            | ByteTraceMode::DistinctLiteralThirtyEight
            | ByteTraceMode::DistinctLiteralThirtyNine
            | ByteTraceMode::DistinctLiteralForty => false,
            ByteTraceMode::DistinctLiteralPair => matches!(
                (zero.little_endian(), literal.little_endian()),
                ([b'Y'], [b'/' | b'$']) | ([b'Q'], [b'.'])
            ),
            ByteTraceMode::AdjacentEcho
            | ByteTraceMode::EmptyVoid
            | ByteTraceMode::IdentityByteBitcast
            | ByteTraceMode::InitialZero
            | ByteTraceMode::LatestRead
            | ByteTraceMode::RotatedLiteral
            | ByteTraceMode::ZeroPrefixedLatest => false,
        }
        || zero_id != first_id
        || literal_id != last_id
        || zero_id == literal_id
    {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    Ok(vec![
        InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: zero.little_endian().to_vec(),
            result: zero_id.value(),
            span: project_span(first.span()),
            type_kind: InputScalarType::U8,
        },
        InputInstruction::ByteOutput {
            span: project_span(zero_output.span()),
            value: zero_id.value(),
        },
        InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: literal_id.value(),
            span: project_span(second.span()),
            type_kind: InputScalarType::U8,
        },
        InputInstruction::ByteOutput {
            span: project_span(second_output.span()),
            value: literal_id.value(),
        },
    ])
}

// Three independently witnessed guest arithmetic outputs preserve three
// different source-bound constant definitions and their exact SSA uses.
fn project_literal_triple_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let [
        first,
        first_output,
        second,
        second_output,
        third,
        third_output,
    ] = original
    else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    let triples = [
        (first, first_output),
        (second, second_output),
        (third, third_output),
    ];
    let mut values = Vec::with_capacity(3);
    let mut result = Vec::with_capacity(6);
    let mut ids = BTreeSet::new();
    for (constant, output) in triples {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        let [byte] = literal.little_endian() else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        values.push(*byte);
        result.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        result.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: id.value(),
        });
    }
    if !matches!(
        values.as_slice(),
        [b'Z', b'%', b'H'] | [b'Q', b'.', b'O'] | [b'Y', b'-', b'P'] | [b'T', b'"', b'O' | b'Q']
    ) {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    Ok(result)
}

// Four exact source constants must preserve distinct output SSA identities.
fn project_literal_quad_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let [
        first,
        first_out,
        second,
        second_out,
        third,
        third_out,
        fourth,
        fourth_out,
    ] = original
    else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    let pairs = [
        (first, first_out),
        (second, second_out),
        (third, third_out),
        (fourth, fourth_out),
    ];
    let mut result = Vec::with_capacity(8);
    let mut ids = BTreeSet::new();
    for (index, (constant, output)) in pairs.into_iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != [b'T', b'=', b'4', b'>']
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        result.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        result.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: id.value(),
        });
    }
    Ok(result)
}

// Five exact byte constants, each with its own source-derived SSA value.
fn project_literal_quint_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 5 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(10);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"Q\"\x1b79"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

// Six exact byte constants, each with its own source-derived SSA value.
fn project_literal_six_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 6 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(12);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"Q\x1cO\x1dP\x1b"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

// Seven exact byte constants, each with its own source-derived SSA value.
fn project_literal_seven_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 7 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(14);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"6>5\x02T\x1f\x18"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

// Eight exact byte constants, each with its own source-derived SSA value.
fn project_literal_eight_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 8 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(16);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"S \x17<6\x01R\x06"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

// Nine exact byte constants, each with its own source-derived SSA value.
fn project_literal_nine_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 9 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(18);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"T=\x8d\xd1\xc0\xb4\xbf\xd2\xa2"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

// Ten exact byte constants, each with its own source-derived SSA value.
fn project_literal_ten_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 10 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(20);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"Q\"\xfd\xce\xa5\x98\xba\xb6\x87\xcb"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

// Eleven exact byte constants, each with its own source-derived SSA value.
fn project_literal_eleven_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 11 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(22);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"P\x1d\x1a6\x05\xb4\xba\xb3\x84\xcf\x9e"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

// Twelve exact byte constants, each with its own source-derived SSA value.
fn project_literal_twelve_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 12 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(24);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"Q748\xfb\xce\x9f\x98\xb8\xb4\x83\xcd"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_thirteen_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 13 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(26);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"BC0\x16T\x09\xbf\xc6\xc8\x87\xe3\xab\xa4"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_fourteen_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 14 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(28);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"YE,HS\x17LO=@[1\x194"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_fifteen_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 15 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(30);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"Q.\x198>\x89\xd2\xad\xa3\xb7\xc8\x88\x08\xd5\xc6"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_sixteen_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 16 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(32);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"?I6\x13Z\x0a\xba\xb3\xc3\x86\xcc\xaa\x01\x07\xd5\xc5"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_seventeen_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 17 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(34);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"Y?,HP\x1b\x182\x15MK;B\x0fD0\x17"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_eighteen_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 18 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(36);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x54\x22\x19\x3e\x38\x03\x09\xdd\x87\xd1\xa5\x99\xbf\x08\xc7\xc6\xc2\x91"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_nineteen_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 19 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(38);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"S!\x1a<8\x03\x17U\x0eI+\x10F\x16@L:\x19X"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_twenty_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 20 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(40);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x3e\x14\x35\x12\x3f\x0a\xa4\x9c\xad\xa3\x1a\xa8\xa2\x95\xab\x9f\x98\x1d\xac\xae"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_twenty_one_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 21 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(42);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x41\x0e\x3b\x0f\x3f\x0a\x40\x8e\x26\x92\x27\x96\x22\x97\x8d\x15\x31\x18\x35\x1a\x2f"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_twenty_two_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 22 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(44);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x39\x16\x37\x05\x41\x0c\x30\x8e\x24\x9f\x1b\xa0\x23\x97\x15\x28\x27\x29\x14\x32\x1e\x1f"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_twenty_three_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 23 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(46);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x42\x0e\x2f\x17\x39\x04\x8e\x24\x9f\x1b\xa0\x23\x97\x15\x28\x27\x29\x14\x32\x1e\x8b\x26\x92"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_twenty_four_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 24 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(48);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x3e\x0b\x2c\x12\x36\x01\x3d\x95\x0f\x9d\x17\x8b\x21\x93\x92\x20\x94\x0e\x9b\x18\x8a\x1c\x2f\x23"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_twenty_five_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 25 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(50);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_twenty_six_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 26 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(52);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_twenty_seven_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 27 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(54);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95\x2d"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_twenty_eight_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 28 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(56);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95\x2d\xab"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_twenty_nine_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 29 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(58);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x87\xb7\xbc\xb1\x8a\xce\x9f\x9c\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95\x2d\xab\x33\x3d\x39\x05\x53\x23\x1b"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_thirty_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 30 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(60);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x39\xa8\x07\xda\x99\xdd\xa3\xcf\xa7\xd9\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_thirty_one_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 31 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(62);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x3f\x0b\x92\x21\x94\x0e\x9d\x1c\x34\x27\x2b\x25\x35\x1d\x33\x11\xa8\xa2\x95\xab\x9f\x98\x14\xac\xae\xa4\x9b\xa5\xad\xa3\x9c"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_thirty_two_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 32 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(64);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x41\x17\x32\x18\x50\x23\x5c\x27\x4b\x34\x4f\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_thirty_three_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 33 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(66);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x39\x19\x34\x08\x41\x0c\x5c\x32\x4d\x33\x5a\x25\x5b\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_thirty_four_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 34 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(68);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x3f\x11\x2c\x14\x39\x04\xa8\x50\x36\x3d\x42\x44\x2f\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae\x09\xd4\xac\xe1\x9e\xe2\xab"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_thirty_five_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 35 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(70);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_thirty_six_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 36 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(72);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x39\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x4b\x34\x4f\x23\x5c\x93\xe0\x9f\xe4\xaa\xd5\xae\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_thirty_seven_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 37 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(74);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x3f\x11\x2c\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x4b\x34\x4f\x23\x5c\x93\xe0\x9f\xe4\xaa\xd5\xae\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_thirty_eight_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 38 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(76);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x41\x17\x32\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_thirty_nine_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 39 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(78);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\x5c\x32\x26\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_literal_forty_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.len() != 40 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(80);
    let mut ids = BTreeSet::new();
    for (index, [constant, output]) in pairs.iter().enumerate() {
        let (
            Instruction::ConstantInteger {
                constant: literal,
                result: id,
                type_id,
            },
            Instruction::ByteOutput { value },
        ) = (constant.instruction(), output.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id)
            || literal.bit_width() != 8
            || id != value
            || !ids.insert(*id)
            || literal.little_endian()
                != b"\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa"
                    .get(index)
                    .map(std::slice::from_ref)
                    .unwrap_or(&[])
        {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: literal.little_endian().to_vec(),
            result: id.value(),
            span: project_span(constant.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

// A source zero SSA can be emitted until the first input overwrites VM A.
// Thereafter only outputs naming the latest successful input are executable.
#[expect(
    clippy::too_many_lines,
    reason = "complete source-bound mixed constant and byte-input SSA admission"
)]
fn project_zero_prefixed_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let Some((first, effects)) = original.split_first() else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    let Instruction::ConstantInteger {
        constant,
        result: zero,
        type_id,
    } = first.instruction()
    else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    if !is_byte_type(module, *type_id)
        || constant.bit_width() != 8
        || constant.little_endian() != [0]
        || effects.len() >= 4096
    {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(original.len());
    instructions.push(InputInstruction::ConstantInteger {
        bit_width: constant.bit_width(),
        little_endian: constant.little_endian().to_vec(),
        result: zero.value(),
        span: project_span(first.span()),
        type_kind: InputScalarType::U8,
    });
    let mut latest = None;
    let mut initial_outputs = false;
    let mut subsequent_outputs = false;
    for located in effects {
        if let Instruction::ByteInput {
            result,
            type_id: input_type,
        } = located.instruction()
        {
            if !is_byte_type(module, *input_type) {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            latest = Some(*result);
            instructions.push(InputInstruction::ByteInput {
                result: result.value(),
                span: project_span(located.span()),
                type_kind: InputScalarType::U8,
            });
        } else if let Instruction::ByteOutput { value } = located.instruction() {
            let valid = latest.map_or(value == zero, |last| *value == last);
            if !valid {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            if latest.is_some() {
                subsequent_outputs = true;
            } else {
                initial_outputs = true;
            }
            instructions.push(InputInstruction::ByteOutput {
                span: project_span(located.span()),
                value: value.value(),
            });
        } else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
    }
    if !initial_outputs || latest.is_none() || !subsequent_outputs {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    Ok(instructions)
}

// A u8/i8 representation bitcast is a new SSA name for the same eight bits.
// Once another input overwrites A, no old alias is realizable without memory.
fn project_identity_bitcast_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    if original.is_empty() || original.len() > 4096 {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut aliases = BTreeSet::new();
    let mut seen_cast = false;
    let mut seen_output = false;
    let mut instructions = Vec::with_capacity(original.len());
    for located in original {
        if let Instruction::ByteInput { result, type_id } = located.instruction() {
            if !is_byte_type(module, *type_id) {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            aliases.clear();
            _ = aliases.insert(*result);
            instructions.push(InputInstruction::ByteInput {
                result: result.value(),
                span: project_span(located.span()),
                type_kind: InputScalarType::U8,
            });
        } else if let Instruction::ByteOutput { value } = located.instruction() {
            if !aliases.contains(value) {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            seen_output = true;
            instructions.push(InputInstruction::ByteOutput {
                span: project_span(located.span()),
                value: value.value(),
            });
        } else if let Instruction::Cast {
            operation: CastOp::IntegerBitcast,
            result,
            type_id,
            value,
        } = located.instruction()
        {
            if !aliases.contains(value) {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            let kind = byte_bitcast_kind(module, *type_id)?;
            _ = aliases.insert(*result);
            seen_cast = true;
            instructions.push(InputInstruction::IntegerBitcast {
                result: result.value(),
                span: project_span(located.span()),
                type_kind: kind,
                value: value.value(),
            });
        } else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
    }
    if aliases.is_empty() || !seen_cast || !seen_output {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    Ok(instructions)
}

fn byte_bitcast_kind(
    module: &Module,
    id: TypeId,
) -> Result<InputScalarType, TypedEchoAdapterError> {
    for entry in module.types() {
        if entry.id() == id {
            return if entry.definition() == &TypeDef::I8 {
                Ok(InputScalarType::I8)
            } else if entry.definition() == &TypeDef::U8 {
                Ok(InputScalarType::U8)
            } else {
                Err(TypedEchoAdapterError::UnsupportedTypedIr)
            };
        }
    }
    Err(TypedEchoAdapterError::UnsupportedTypedIr)
}

#[expect(
    clippy::too_many_lines,
    reason = "complete canonical typed bridge admission"
)]
fn project_byte_trace(
    module: &Module,
    mode: ByteTraceMode,
) -> Result<TypedIrInput, TypedEchoAdapterError> {
    let [function] = module.functions() else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    let [block] = function.blocks() else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    let has_void_signature = module.types().iter().any(|entry| {
        entry.id() == function.signature()
            && matches!(entry.definition(), TypeDef::Function {
                parameters, result: None, variadic: false
            } if parameters.is_empty())
    });
    if !module.globals().is_empty()
        || !module.proof_obligations().is_empty()
        || !has_void_signature
        || !function.parameters().is_empty()
        || function.entry() != block.id()
        || !block.phis().is_empty()
        || !matches!(block.terminator(), Terminator::Return { value: None })
    {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let instructions = match mode {
        ByteTraceMode::AdjacentEcho => project_effects(module, block.instructions())?,
        ByteTraceMode::EmptyVoid if block.instructions().is_empty() => Vec::new(),
        ByteTraceMode::EmptyVoid => return Err(TypedEchoAdapterError::UnsupportedTypedIr),
        ByteTraceMode::InitialZero => project_initial_zero_effects(module, block.instructions())?,
        ByteTraceMode::LatestRead => project_latest_effects(module, block.instructions())?,
        ByteTraceMode::ZeroPrefixedLatest => {
            project_zero_prefixed_effects(module, block.instructions())?
        }
        ByteTraceMode::IdentityByteBitcast => {
            project_identity_bitcast_effects(module, block.instructions())?
        }
        ByteTraceMode::RotatedLiteral => {
            project_rotated_literal_effects(module, block.instructions())?
        }
        ByteTraceMode::ZeroThenLiteral | ByteTraceMode::DistinctLiteralPair => {
            project_literal_pair_effects(module, block.instructions(), mode)?
        }
        ByteTraceMode::DistinctLiteralTriple => {
            project_literal_triple_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralQuad => {
            project_literal_quad_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralQuint => {
            project_literal_quint_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralSix => {
            project_literal_six_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralSeven => {
            project_literal_seven_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralEight => {
            project_literal_eight_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralNine => {
            project_literal_nine_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralTen => {
            project_literal_ten_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralEleven => {
            project_literal_eleven_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralTwelve => {
            project_literal_twelve_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralThirteen => {
            project_literal_thirteen_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralFourteen => {
            project_literal_fourteen_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralFifteen => {
            project_literal_fifteen_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralSixteen => {
            project_literal_sixteen_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralSeventeen => {
            project_literal_seventeen_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralEighteen => {
            project_literal_eighteen_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralNineteen => {
            project_literal_nineteen_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralTwenty => {
            project_literal_twenty_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralTwentyOne => {
            project_literal_twenty_one_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralTwentyTwo => {
            project_literal_twenty_two_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralTwentyThree => {
            project_literal_twenty_three_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralTwentyFour => {
            project_literal_twenty_four_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralTwentyFive => {
            project_literal_twenty_five_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralTwentySix => {
            project_literal_twenty_six_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralTwentySeven => {
            project_literal_twenty_seven_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralTwentyEight => {
            project_literal_twenty_eight_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralTwentyNine => {
            project_literal_twenty_nine_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralThirty => {
            project_literal_thirty_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralThirtyOne => {
            project_literal_thirty_one_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralThirtyTwo => {
            project_literal_thirty_two_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralThirtyThree => {
            project_literal_thirty_three_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralThirtyFour => {
            project_literal_thirty_four_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralThirtyFive => {
            project_literal_thirty_five_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralThirtySix => {
            project_literal_thirty_six_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralThirtySeven => {
            project_literal_thirty_seven_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralThirtyEight => {
            project_literal_thirty_eight_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralThirtyNine => {
            project_literal_thirty_nine_effects(module, block.instructions())?
        }
        ByteTraceMode::DistinctLiteralForty => {
            project_literal_forty_effects(module, block.instructions())?
        }
    };
    Ok(TypedIrInput {
        abi_id: module.abi_id().to_owned(),
        functions: vec![InputFunction {
            blocks: vec![InputBlock {
                id: block.id().value(),
                instructions,
                phi_count: 0,
                terminator: InputTerminator::Return {
                    span: project_span(block.terminator_span()),
                    value: None,
                },
            }],
            entry: function.entry().value(),
            id: function.id().value(),
            name: function.name().to_owned(),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: project_span(function.span()),
        }],
        global_count: 0,
        input_format_version: module.format_version(),
        proof_obligation_count: 0,
        source_id: module.source_id().to_owned(),
        source_sha256: *module.source_sha256(),
        target_profile: module.target_profile().to_owned(),
    })
}

// Both opt-in modes consume the exact canonical typed module, preserve every
// admitted source/SSA identity, and independently re-admit MCTR and layout.
// The private composition never falls back to host I/O execution.
fn compile_byte_trace(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
    mode: ByteTraceMode,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    let module = canonical_module(canonical).map_err(TypedEchoAdapterError::InvalidTypedIr)?;
    // A canonical source-target identity is admission evidence, not a hint.
    // Refuse profile drift before allocating/lowering an entire effect trace.
    if module.target_profile() != profile.id() {
        return Err(TypedEchoAdapterError::Layout(
            bridge::ByteEchoBridgeError::ProfileMismatch,
        ));
    }
    let projection = project_byte_trace(&module, mode)?;
    let lowered = lower_typed_ir(&projection).map_err(TypedEchoAdapterError::Lowering)?;
    let ternary_bytes =
        canonical_ternary_bytes(&lowered).map_err(TypedEchoAdapterError::InvalidTernary)?;
    let independently_admitted =
        canonical_ternary_program(&ternary_bytes).map_err(TypedEchoAdapterError::InvalidTernary)?;
    if independently_admitted != lowered {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let layout = match mode {
        ByteTraceMode::AdjacentEcho => {
            bridge::encode_successful_byte_echo(&independently_admitted, profile)
        }
        ByteTraceMode::EmptyVoid => {
            bridge::encode_empty_void_function(&independently_admitted, profile)
        }
        ByteTraceMode::InitialZero => {
            bridge::encode_initial_zero_outputs(&independently_admitted, profile)
        }
        ByteTraceMode::LatestRead => {
            bridge::encode_successful_latest_byte_trace(&independently_admitted, profile)
        }
        ByteTraceMode::ZeroPrefixedLatest => {
            bridge::encode_zero_prefixed_latest_byte_trace(&independently_admitted, profile)
        }
        ByteTraceMode::IdentityByteBitcast => {
            bridge::encode_latest_byte_identity_trace(&independently_admitted, profile)
        }
        ByteTraceMode::RotatedLiteral => {
            bridge::encode_rotated_byte_literal(&independently_admitted, profile)
        }
        ByteTraceMode::ZeroThenLiteral => {
            bridge::encode_zero_then_literal(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralPair => {
            bridge::encode_distinct_literal_pair(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralTriple => {
            bridge::encode_distinct_literal_triple(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralQuad => {
            bridge::encode_distinct_literal_quad(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralQuint => {
            bridge::encode_distinct_literal_quint(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralSix => {
            bridge::encode_distinct_literal_six(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralSeven => {
            bridge::encode_distinct_literal_seven(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralEight => {
            bridge::encode_distinct_literal_eight(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralNine => {
            bridge::encode_distinct_literal_nine(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralTen => {
            bridge::encode_distinct_literal_ten(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralEleven => {
            bridge::encode_distinct_literal_eleven(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralTwelve => {
            bridge::encode_distinct_literal_twelve(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralThirteen => {
            bridge::encode_distinct_literal_thirteen(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralFourteen => {
            bridge::encode_distinct_literal_fourteen(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralFifteen => {
            bridge::encode_distinct_literal_fifteen(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralSixteen => {
            bridge::encode_distinct_literal_sixteen(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralSeventeen => {
            bridge::encode_distinct_literal_seventeen(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralEighteen => {
            bridge::encode_distinct_literal_eighteen(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralNineteen => {
            bridge::encode_distinct_literal_nineteen(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralTwenty => {
            bridge::encode_distinct_literal_twenty(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralTwentyOne => {
            bridge::encode_distinct_literal_twenty_one(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralTwentyTwo => {
            bridge::encode_distinct_literal_twenty_two(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralTwentyThree => {
            bridge::encode_distinct_literal_twenty_three(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralTwentyFour => {
            bridge::encode_distinct_literal_twenty_four(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralTwentyFive => {
            bridge::encode_distinct_literal_twenty_five(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralTwentySix => {
            bridge::encode_distinct_literal_twenty_six(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralTwentySeven => {
            bridge::encode_distinct_literal_twenty_seven(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralTwentyEight => {
            bridge::encode_distinct_literal_twenty_eight(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralTwentyNine => {
            bridge::encode_distinct_literal_twenty_nine(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralThirty => {
            bridge::encode_distinct_literal_thirty(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralThirtyOne => {
            bridge::encode_distinct_literal_thirty_one(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralThirtyTwo => {
            bridge::encode_distinct_literal_thirty_two(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralThirtyThree => {
            bridge::encode_distinct_literal_thirty_three(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralThirtyFour => {
            bridge::encode_distinct_literal_thirty_four(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralThirtyFive => {
            bridge::encode_distinct_literal_thirty_five(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralThirtySix => {
            bridge::encode_distinct_literal_thirty_six(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralThirtySeven => {
            bridge::encode_distinct_literal_thirty_seven(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralThirtyEight => {
            bridge::encode_distinct_literal_thirty_eight(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralThirtyNine => {
            bridge::encode_distinct_literal_thirty_nine(&independently_admitted, profile)
        }
        ByteTraceMode::DistinctLiteralForty => {
            bridge::encode_distinct_literal_forty(&independently_admitted, profile)
        }
    }
    .map_err(TypedEchoAdapterError::Layout)?;
    Ok(CompiledTypedEcho {
        layout,
        ternary_bytes,
    })
}

/// Lowers one canonical side-effect-free void-return typed function.
///
/// The admitted function has no parameters, instructions, globals, or proof
/// obligations, and one void return block. Canonical MCTR is independently
/// decoded before the generated two-cell no-op/halt Malbolge layout is accepted.
/// This does not claim to compile arbitrary C returns or a process exit ABI.
///
/// # Errors
///
/// Refuses nonempty effects, invalid typed/wire state, foreign profiles and
/// unadmitted positional source.
pub fn compile_canonical_typed_empty_void(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::EmptyVoid)
}

/// Lowers the **original** strict canonical typed-IR echo sublanguage.
///
/// Every input must be immediately followed by one output of that exact
/// result. This entrypoint is intentionally unaffected by the broader
/// latest-read byte-I/O trace mode.
///
/// # Errors
///
/// Rejects unsupported typed source, profile drift, malformed canonical IR
/// and independently unadmitted Malbolge layout.
pub fn compile_canonical_typed_echo(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::AdjacentEcho)
}

/// Lowers an admitted canonical typed-IR **latest successful byte** trace.
///
/// Each output must refer to the most recent successful input's SSA byte.
/// Multiple outputs of that value and unused intervening input values are
/// supported, but outputting an older result after another input is forbidden
/// without guest memory. The caller must guarantee all reads/writes succeed;
/// EOF, ABI returns, heap storage and arbitrary typed computations are absent.
///
/// # Errors
///
/// Rejects unsupported module, function, instruction, or SSA flow; invalid
/// canonical source, profile drift or address-sensitive target-layout failure.
pub fn compile_canonical_typed_latest_byte_trace(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::LatestRead)
}

/// Compiles canonical typed-IR initial-zero outputs to real guest instructions.
///
/// The complete canonical module must contain exactly one zero-argument void
/// function with one phi-free block and no global state/proof obligations. Its
/// instructions are exactly one `u8` constant of value zero, then one or more
/// `ByteOutput`s using that precise SSA value. The canonical MCTR is independently
/// decoded and the actual Malbolge code is independently admitted by layout.
/// No host byte emulation, arbitrary constants, EOF or guest ABI is implemented.
///
/// # Errors
///
/// Rejects invalid typed/MCTR data, profile mismatch, unsupported SSA flow
/// or target source beyond the 4096-cell positional layout bound.
pub fn compile_canonical_typed_initial_zero_outputs(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::InitialZero)
}

/// Lowers canonical typed zero-output prefix followed by successful-byte I/O.
///
/// One `u8 ConstantInteger(0)` SSA definition must be followed by at least
/// one output of that SSA byte, then at least one successful input and one
/// output of the latest input. Reads overwrite the VM accumulator, so any
/// later zero-SSA replay and stale input SSA replay fail closed. Actual
/// guest instructions perform every I/O effect; return/ABI and EOF are absent.
///
/// # Errors
///
/// Rejects malformed or unsupported typed semantics, mismatched profile,
/// canonical MCTR drift or unadmitted/oversized address-sensitive layout.
pub fn compile_canonical_typed_zero_prefixed_latest_byte_trace(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::ZeroPrefixedLatest)
}

/// Lowers an admitted canonical byte I/O trace with exact eight-bit SSA casts.
///
/// `IntegerBitcast` operations between `u8` and `i8` are representation-only
/// and create new aliases of A, without emitting guest instructions. Every
/// output must reference a still-live unsigned-byte alias of the most recent
/// successful input; later input invalidates all earlier aliases. No EOF,
/// general computation, byte storage, or guest return/ABI claim is made.
///
/// # Errors
///
/// Rejects unsupported effects/casts/SSA, invalid canonical MCTI/MCTR,
/// profile drift, and unadmitted address-sensitive target source.
pub fn compile_canonical_typed_identity_byte_trace(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::IdentityByteBitcast)
}

/// Compile one current-profile `u8` constant and one to twenty-three outputs via rotation.
///
/// Unlike initial-zero, only a finite verified set of nonzero values has
/// safe `j`, `*`, `<`, `v` source layouts. The independent bridge executes
/// the produced source in the normative VM and checks exact output bits.
/// No EOF, guest arithmetic, additional source effects or ABI is claimed.
///
/// # Errors
///
/// Rejects malformed MCTI/MCTR, unsupported literal values, forged source
/// semantics, wrong profiles, or unadmitted guest output.
pub fn compile_canonical_typed_rotated_byte_literal(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::RotatedLiteral)
}

/// Compile one proven initial-zero byte followed by one nonzero printable byte.
///
/// # Errors
///
/// Refuses other typed effects, unproved constant values, foreign profiles,
/// or any mismatch under independent MCTR and normative guest verification.
pub fn compile_canonical_typed_zero_then_literal(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::ZeroThenLiteral)
}

/// Compile exactly two different source-proven nonzero printable bytes.
///
/// # Errors
///
/// Refuses unproved pairs, stale SSA, extra effects, profile drift and
/// guest results that cannot be independently reproduced.
pub fn compile_canonical_typed_distinct_literal_pair(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralPair)
}

/// Compile one of three independently verified distinct three-byte C traces.
///
/// # Errors
///
/// Refuses unproved triples, stale SSA, malformed input, profile drift or a
/// mismatch under independent guest execution.
pub fn compile_canonical_typed_distinct_literal_triple(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralTriple)
}

/// Compile five distinct guest bytes `Q`, `"`, ESC, `7`, `9`.
///
/// # Errors
///
/// Rejects stale SSA, foreign profiles, unwitnessed values or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_quint(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralQuint)
}

/// Compile six distinct guest bytes `Q`, FS, `O`, GS, `P`, ESC.
///
/// # Errors
///
/// Rejects stale SSA, foreign profiles, unwitnessed values or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_six(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralSix)
}

/// Compile seven independently produced guest bytes `6>5`, STX, `T`, US, CAN.
///
/// # Errors
///
/// Rejects stale SSA, foreign profiles, unwitnessed values or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_seven(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralSeven)
}

/// Compile eight independent mixed-arithmetic guest bytes including ETB and ACK.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, wrong profiles and VM disagreement.
pub fn compile_canonical_typed_distinct_literal_eight(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralEight)
}

/// Compile nine independent binary bytes from eight guest crazy writes and one rotate.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, wrong profiles and VM disagreement.
pub fn compile_canonical_typed_distinct_literal_nine(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralNine)
}

/// Compile ten independent binary bytes from nine guest crazy writes and one rotate.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, wrong profiles and VM disagreement.
pub fn compile_canonical_typed_distinct_literal_ten(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralTen)
}

/// Compile eleven independent binary bytes from ten guest crazy writes and one rotate.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, wrong profiles and VM disagreement.
pub fn compile_canonical_typed_distinct_literal_eleven(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralEleven)
}

/// Compile twelve independent binary bytes from eleven guest crazy writes and one rotate.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, wrong profiles and VM disagreement.
pub fn compile_canonical_typed_distinct_literal_twelve(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralTwelve)
}

/// Compile thirteen independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_thirteen(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralThirteen)
}

/// Compile fourteen independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_fourteen(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralFourteen)
}

/// Compile fifteen independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_fifteen(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralFifteen)
}

/// Compile sixteen independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_sixteen(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralSixteen)
}

/// Compile seventeen independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_seventeen(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralSeventeen)
}

/// Compile eighteen independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_eighteen(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralEighteen)
}

/// Compile nineteen independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_nineteen(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralNineteen)
}

/// Compile twenty independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_twenty(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralTwenty)
}

/// Compile twenty-one independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_twenty_one(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralTwentyOne)
}

/// Compile twenty-two independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_twenty_two(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralTwentyTwo)
}

/// Compile twenty-three independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_twenty_three(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralTwentyThree,
    )
}

/// Compile twenty-four independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_twenty_four(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralTwentyFour)
}

/// Compile twenty-five independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_twenty_five(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralTwentyFive)
}

/// Compile twenty-six independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_twenty_six(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralTwentySix)
}

/// Compile twenty-seven independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_twenty_seven(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralTwentySeven,
    )
}

/// Compile twenty-eight independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_twenty_eight(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralTwentyEight,
    )
}

/// Compile twenty-nine independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_twenty_nine(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralTwentyNine,
    )
}

/// Compile thirty independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_thirty(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralThirty,
    )
}

/// Compile thirty-one independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_thirty_one(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralThirtyOne,
    )
}
/// Compile thirty-two independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_thirty_two(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralThirtyTwo,
    )
}
/// Compile thirty-three independently source-proven binary bytes in the real VM.
///
/// # Errors
///
/// Rejects unsupported constants, stale SSA, profiles or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_thirty_three(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralThirtyThree,
    )
}

/// Compile the independently verified thirty-four-byte typed trace.
///
/// # Errors
///
/// Rejects wrong bytes, invalid SSA, foreign profiles or guest divergence.
pub fn compile_canonical_typed_distinct_literal_thirty_four(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralThirtyFour,
    )
}

/// Compile the independently verified thirty-five-byte typed trace.
///
/// # Errors
///
/// Rejects unrelated effects, profiles, and unauthenticated output.
pub fn compile_canonical_typed_distinct_literal_thirty_five(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralThirtyFive,
    )
}

/// Compile the independently verified thirty-six-byte typed trace.
///
/// # Errors
///
/// Rejects unrelated effects, profiles, and unauthenticated output.
pub fn compile_canonical_typed_distinct_literal_thirty_six(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralThirtySix,
    )
}

/// Compile the independently verified thirty-seven-byte typed trace.
///
/// # Errors
///
/// Rejects unrelated effects, profiles, and unauthenticated output.
pub fn compile_canonical_typed_distinct_literal_thirty_seven(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralThirtySeven,
    )
}

/// Compile the independently verified thirty-eight-byte typed trace.
///
/// # Errors
///
/// Rejects unrelated effects, profiles, and unauthenticated output.
pub fn compile_canonical_typed_distinct_literal_thirty_eight(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralThirtyEight,
    )
}

/// Compile the independently verified thirty-nine-byte typed trace.
///
/// # Errors
///
/// Rejects unrelated effects, profiles, and unauthenticated output.
pub fn compile_canonical_typed_distinct_literal_thirty_nine(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralThirtyNine,
    )
}

/// Compile the independently verified forty-byte typed trace.
///
/// # Errors
///
/// Rejects unrelated effects, profiles, and unauthenticated output.
pub fn compile_canonical_typed_distinct_literal_forty(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(
        canonical,
        profile,
        ByteTraceMode::DistinctLiteralForty,
    )
}

/// Compile exactly four distinct source-proven guest bytes `T=4>`.
///
/// # Errors
///
/// Rejects any other effects, stale SSA, profile drift or VM disagreement.
pub fn compile_canonical_typed_distinct_literal_quad(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::DistinctLiteralQuad)
}
