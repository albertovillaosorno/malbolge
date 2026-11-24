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
//   - Numerical result checks for source-authenticated guest computations.
// - Must-Not:
//   - Replace real guest execution, infer operand causal paths or emit code.
// - Allows:
//   - Inputs: checked typed placement and the normative VM's reached steps.
//   - Outputs: explicit missing/incorrect/unsupported computation refusal.
//   - Side effects: none.
// - Split-When:
//   - General strict source semantic replay subsumes this result check.
// - Merge-When:
//   - The physical CFG linker checks all typed operations independently.
// - Summary:
//   - Compare actual frame stores to source-typed arithmetic expectations.

//! Optional exact typed-result check on an independently verified VM trace.
//!
//! Source operands are read only from earlier source-authorized physical
//! stores or completed two-phase phi copies, never from loader-seeded memory.
//! The guest must actually write each result at its source-anchored site.
//! Numeric equality is necessary, not proof that guest arithmetic consumed
//! the inputs: causal source dependencies still require separate evidence.

use std::collections::BTreeMap;

use malbolge::ProfileStepTrace;

use super::source_phi_copy_trace::SourcePhiCopyTraceError;
use super::typed_cfg_adapter::state_relocation::{
    GuestCodeComputation, GuestCodeControlEdge, GuestCodeOperationEffect,
    GuestCodeOperationEffectSite, GuestCodeOperationSite, GuestPlacedOperand,
};
use super::typed_cfg_adapter::state_storage::{
    GuestFramePlacement, decode_i32_cells, encode_i32_cells,
};
use super::typed_cfg_adapter::ternary::TernaryCfgScalarKind;
use super::typed_cfg_adapter::typed::{BinaryOp, CastOp, CompareOp};

type OperationId = (u32, u32, u32);

const fn scalar_bits(kind: TernaryCfgScalarKind) -> u32 {
    match kind {
        TernaryCfgScalarKind::Bool => 1,
        TernaryCfgScalarKind::I8 | TernaryCfgScalarKind::U8 => 8,
        TernaryCfgScalarKind::I16 | TernaryCfgScalarKind::U16 => 16,
        TernaryCfgScalarKind::I32 | TernaryCfgScalarKind::U32 => 32,
    }
}

const fn bit_mask(bits: u32) -> u32 {
    u32::MAX.wrapping_shr(32u32.saturating_sub(bits))
}

fn read_scalar(
    operand: GuestPlacedOperand,
    written: &BTreeMap<u32, u32>,
) -> Result<u32, SourcePhiCopyTraceError> {
    let low = *written
        .get(&operand.address)
        .ok_or(SourcePhiCopyTraceError::MissingComputationOperand)?;
    let bits = if operand.words == 1 {
        low
    } else if operand.words == 2 {
        let high_address = operand
            .address
            .checked_add(1)
            .ok_or(SourcePhiCopyTraceError::InvalidSourcePlacement)?;
        let high = *written
            .get(&high_address)
            .ok_or(SourcePhiCopyTraceError::MissingComputationOperand)?;
        decode_i32_cells([low, high])
            .ok_or(SourcePhiCopyTraceError::InvalidComputationValue)?
    } else {
        return Err(SourcePhiCopyTraceError::UnsupportedComputation);
    };
    let width = scalar_bits(operand.type_kind);
    if bits & !bit_mask(width) != 0
        || (operand.words == 2) != (width == 32)
        || (operand.type_kind == TernaryCfgScalarKind::Bool && bits > 1)
    {
        return Err(SourcePhiCopyTraceError::InvalidComputationValue);
    }
    Ok(bits)
}

const fn signed(bits: u32, width: u32) -> i32 {
    let shift = 32u32.saturating_sub(width);
    bits.wrapping_shl(shift).cast_signed().wrapping_shr(shift)
}

// Signed values are accepted only if the exact mathematical value fits the
// source scalar. A matched low-width guest word cannot authorize C23 UB.
fn signed_result_bits(
    result: i64,
    width: u32,
) -> Result<u32, SourcePhiCopyTraceError> {
    use SourcePhiCopyTraceError::InvalidComputationValue;
    let bound = 1i64
        .checked_shl(width.saturating_sub(1))
        .ok_or(InvalidComputationValue)?;
    let minimum = bound.checked_neg().ok_or(InvalidComputationValue)?;
    if !(minimum..bound).contains(&result) {
        return Err(InvalidComputationValue);
    }
    u32::try_from(result & i64::from(bit_mask(width)))
        .map_err(|_error| InvalidComputationValue)
}

// C23 signed overflow is undefined, not a two's-complement wrapped result.
// Use i64 so multiplication of any two i32 operands is representable before
// checking the exact signed source-type range.
fn checked_signed_arithmetic(
    operation: BinaryOp,
    lhs: u32,
    rhs: u32,
    width: u32,
) -> Result<u32, SourcePhiCopyTraceError> {
    use SourcePhiCopyTraceError::{
        InvalidComputationValue, UnsupportedComputation,
    };
    let left = i64::from(signed(lhs, width));
    let right = i64::from(signed(rhs, width));
    let result = match operation {
        BinaryOp::Add => left.checked_add(right),
        BinaryOp::Multiply => left.checked_mul(right),
        BinaryOp::Subtract => left.checked_sub(right),
        BinaryOp::And
        | BinaryOp::DivideFloat
        | BinaryOp::DivideSigned
        | BinaryOp::DivideUnsigned
        | BinaryOp::Or
        | BinaryOp::RemainderSigned
        | BinaryOp::RemainderUnsigned
        | BinaryOp::ShiftLeft
        | BinaryOp::ShiftRightArithmetic
        | BinaryOp::ShiftRightLogical
        | BinaryOp::Xor => return Err(UnsupportedComputation),
    }
    .ok_or(InvalidComputationValue)?;
    signed_result_bits(result, width)
}

// Division by zero and the signed minimum/-1 overflow are undefined source
// behavior. Even for small signed types the checked quotient must fit the
// original width before accepting a physical guest result.
fn checked_integer_division(
    operation: BinaryOp,
    lhs: u32,
    rhs: u32,
    kind: TernaryCfgScalarKind,
) -> Result<u32, SourcePhiCopyTraceError> {
    use SourcePhiCopyTraceError::{
        InvalidComputationValue, UnsupportedComputation,
    };
    let width = scalar_bits(kind);
    let signed_kind = matches!(
        kind,
        TernaryCfgScalarKind::I8
            | TernaryCfgScalarKind::I16
            | TernaryCfgScalarKind::I32
    );
    match operation {
        BinaryOp::DivideSigned | BinaryOp::RemainderSigned if signed_kind => {
            let left = signed(lhs, width);
            let right = signed(rhs, width);
            let result = if operation == BinaryOp::DivideSigned {
                left.checked_div(right)
            } else {
                left.checked_rem(right)
            }
            .ok_or(InvalidComputationValue)?;
            signed_result_bits(i64::from(result), width)
        },
        BinaryOp::DivideUnsigned | BinaryOp::RemainderUnsigned
            if !signed_kind && kind != TernaryCfgScalarKind::Bool =>
        {
            if operation == BinaryOp::DivideUnsigned {
                lhs.checked_div(rhs)
            } else {
                lhs.checked_rem(rhs)
            }
            .ok_or(InvalidComputationValue)
        },
        BinaryOp::Add
        | BinaryOp::And
        | BinaryOp::DivideSigned
        | BinaryOp::DivideUnsigned
        | BinaryOp::RemainderSigned
        | BinaryOp::RemainderUnsigned
        | BinaryOp::DivideFloat
        | BinaryOp::Multiply
        | BinaryOp::Or
        | BinaryOp::ShiftLeft
        | BinaryOp::ShiftRightArithmetic
        | BinaryOp::ShiftRightLogical
        | BinaryOp::Subtract
        | BinaryOp::Xor => Err(UnsupportedComputation),
    }
}

// A typed shift has its original scalar width, not the VM word width.
// Signed left shift of a negative operand or out-of-range result is refused;
// unsigned left shift wraps. The distinct signed/arithmetic and unsigned/
// logical right-shift operators retain the IR's explicit bit semantics.
fn checked_integer_shift(
    operation: BinaryOp,
    lhs: u32,
    rhs: u32,
    kind: TernaryCfgScalarKind,
) -> Result<u32, SourcePhiCopyTraceError> {
    use SourcePhiCopyTraceError::{
        InvalidComputationValue, UnsupportedComputation,
    };
    let width = scalar_bits(kind);
    if kind == TernaryCfgScalarKind::Bool {
        return Err(UnsupportedComputation);
    }
    if rhs >= width {
        return Err(InvalidComputationValue);
    }
    let signed_kind = matches!(
        kind,
        TernaryCfgScalarKind::I8
            | TernaryCfgScalarKind::I16
            | TernaryCfgScalarKind::I32
    );
    match operation {
        BinaryOp::ShiftLeft if signed_kind => {
            let value = i64::from(signed(lhs, width));
            if value < 0 {
                return Err(InvalidComputationValue);
            }
            signed_result_bits(
                value.checked_shl(rhs).ok_or(InvalidComputationValue)?,
                width,
            )
        },
        BinaryOp::ShiftLeft => Ok(lhs.wrapping_shl(rhs) & bit_mask(width)),
        BinaryOp::ShiftRightArithmetic if signed_kind => {
            Ok(signed(lhs, width).wrapping_shr(rhs).cast_unsigned()
                & bit_mask(width))
        },
        BinaryOp::ShiftRightLogical if !signed_kind => Ok(lhs >> rhs),
        BinaryOp::Add
        | BinaryOp::And
        | BinaryOp::DivideFloat
        | BinaryOp::DivideSigned
        | BinaryOp::DivideUnsigned
        | BinaryOp::Multiply
        | BinaryOp::Or
        | BinaryOp::RemainderSigned
        | BinaryOp::RemainderUnsigned
        | BinaryOp::ShiftRightArithmetic
        | BinaryOp::ShiftRightLogical
        | BinaryOp::Subtract
        | BinaryOp::Xor => Err(UnsupportedComputation),
    }
}

#[expect(
    clippy::too_many_lines,
    reason = "exhaustive typed operations share one closed result interpreter"
)]
fn evaluate(
    computation: GuestCodeComputation,
    written: &BTreeMap<u32, u32>,
) -> Result<u32, SourcePhiCopyTraceError> {
    use SourcePhiCopyTraceError::UnsupportedComputation;
    match computation {
        GuestCodeComputation::Binary {
            operation,
            left,
            right,
            result,
        } => {
            if left.type_kind != right.type_kind
                || left.type_kind != result.type_kind
            {
                return Err(UnsupportedComputation);
            }
            let lhs = read_scalar(left, written)?;
            let rhs = read_scalar(right, written)?;
            let width = scalar_bits(result.type_kind);
            let computed = match operation {
                BinaryOp::Add | BinaryOp::Multiply | BinaryOp::Subtract
                    if matches!(
                        result.type_kind,
                        TernaryCfgScalarKind::I8
                            | TernaryCfgScalarKind::I16
                            | TernaryCfgScalarKind::I32
                    ) =>
                {
                    checked_signed_arithmetic(operation, lhs, rhs, width)?
                },
                BinaryOp::Add => lhs.wrapping_add(rhs),
                BinaryOp::And => lhs & rhs,
                BinaryOp::Multiply => lhs.wrapping_mul(rhs),
                BinaryOp::Or => lhs | rhs,
                BinaryOp::Subtract => lhs.wrapping_sub(rhs),
                BinaryOp::Xor => lhs ^ rhs,
                BinaryOp::DivideSigned
                | BinaryOp::DivideUnsigned
                | BinaryOp::RemainderSigned
                | BinaryOp::RemainderUnsigned => checked_integer_division(
                    operation,
                    lhs,
                    rhs,
                    result.type_kind,
                )?,
                BinaryOp::ShiftLeft
                | BinaryOp::ShiftRightArithmetic
                | BinaryOp::ShiftRightLogical => checked_integer_shift(
                    operation,
                    lhs,
                    rhs,
                    result.type_kind,
                )?,
                BinaryOp::DivideFloat => {
                    return Err(UnsupportedComputation);
                },
            };
            Ok(computed & bit_mask(scalar_bits(result.type_kind)))
        },
        GuestCodeComputation::Compare {
            operation,
            left,
            right,
            result,
        } => {
            if result.type_kind != TernaryCfgScalarKind::Bool
                || left.type_kind != right.type_kind
            {
                return Err(UnsupportedComputation);
            }
            let lhs = read_scalar(left, written)?;
            let rhs = read_scalar(right, written)?;
            let width = scalar_bits(left.type_kind);
            // C23 comparisons must use their source-typed signedness.
            // Reinterpreting U8 0xff as signed -1, for example, could
            // numerically certify the wrong physical branch predicate.
            let signed_kind = matches!(
                left.type_kind,
                TernaryCfgScalarKind::I8
                    | TernaryCfgScalarKind::I16
                    | TernaryCfgScalarKind::I32
            );
            if (matches!(
                operation,
                CompareOp::LessSigned | CompareOp::LessSignedEqual
            ) && !signed_kind)
                || (matches!(
                    operation,
                    CompareOp::LessUnsigned | CompareOp::LessUnsignedEqual
                ) && signed_kind)
            {
                return Err(UnsupportedComputation);
            }
            let comparison = match operation {
                CompareOp::Equal => lhs == rhs,
                CompareOp::NotEqual => lhs != rhs,
                CompareOp::LessUnsigned => lhs < rhs,
                CompareOp::LessUnsignedEqual => lhs <= rhs,
                CompareOp::LessSigned => {
                    signed(lhs, width) < signed(rhs, width)
                },
                CompareOp::LessSignedEqual => {
                    signed(lhs, width) <= signed(rhs, width)
                },
                CompareOp::FloatLess | CompareOp::FloatLessEqual => {
                    return Err(UnsupportedComputation);
                },
            };
            Ok(u32::from(comparison))
        },
        GuestCodeComputation::Cast {
            operation,
            source,
            result,
        } => {
            let bits = read_scalar(source, written)?;
            let width = scalar_bits(result.type_kind);
            let source_width = scalar_bits(source.type_kind);
            let source_is_signed = matches!(
                source.type_kind,
                TernaryCfgScalarKind::I8
                    | TernaryCfgScalarKind::I16
                    | TernaryCfgScalarKind::I32
            );
            let result_is_signed = matches!(
                result.type_kind,
                TernaryCfgScalarKind::I8
                    | TernaryCfgScalarKind::I16
                    | TernaryCfgScalarKind::I32
            );
            let value = match operation {
                CastOp::IntegerBitcast
                    if source.type_kind != TernaryCfgScalarKind::Bool
                        && result.type_kind != TernaryCfgScalarKind::Bool
                        && source_width == width =>
                {
                    bits
                },
                CastOp::Truncate
                    if source.type_kind != TernaryCfgScalarKind::Bool
                        && result.type_kind != TernaryCfgScalarKind::Bool
                        && source_width > width =>
                {
                    bits & bit_mask(width)
                },
                CastOp::ZeroExtend
                    if !source_is_signed
                        && result.type_kind != TernaryCfgScalarKind::Bool
                        && source_width < width =>
                {
                    bits
                },
                CastOp::SignExtend
                    if source_is_signed
                        && result.type_kind != TernaryCfgScalarKind::Bool
                        && source_width < width =>
                {
                    signed(bits, source_width).cast_unsigned() & bit_mask(width)
                },
                CastOp::IntegerToBool
                    if source.type_kind != TernaryCfgScalarKind::Bool
                        && result.type_kind == TernaryCfgScalarKind::Bool =>
                {
                    u32::from(bits != 0)
                },
                CastOp::BoolToSigned
                    if source.type_kind == TernaryCfgScalarKind::Bool
                        && result_is_signed =>
                {
                    bits
                },
                CastOp::Bitcast
                | CastOp::BoolToSigned
                | CastOp::FloatToBool
                | CastOp::FloatToFloat
                | CastOp::FloatToSigned
                | CastOp::FloatToUnsigned
                | CastOp::IntegerBitcast
                | CastOp::IntegerToBool
                | CastOp::IntegerToPointer
                | CastOp::PointerToBool
                | CastOp::PointerToInteger
                | CastOp::SignExtend
                | CastOp::SignedToFloat
                | CastOp::Truncate
                | CastOp::UnsignedToFloat
                | CastOp::ZeroExtend => return Err(UnsupportedComputation),
            };
            Ok(value)
        },
    }
}

fn expected_word(
    value: u32,
    result: GuestPlacedOperand,
    destination: u32,
) -> Result<u32, SourcePhiCopyTraceError> {
    let index = destination
        .checked_sub(result.address)
        .ok_or(SourcePhiCopyTraceError::InvalidSourcePlacement)?;
    if index >= result.words {
        return Err(SourcePhiCopyTraceError::InvalidSourcePlacement);
    }
    let cells = encode_i32_cells(value);
    if result.words == 1 {
        Ok(value)
    } else {
        cells
            .get(usize::try_from(index).unwrap_or(usize::MAX))
            .copied()
            .ok_or(SourcePhiCopyTraceError::InvalidSourcePlacement)
    }
}

const fn result_operand(
    computation: GuestCodeComputation,
) -> GuestPlacedOperand {
    match computation {
        GuestCodeComputation::Binary { result, .. }
        | GuestCodeComputation::Cast { result, .. }
        | GuestCodeComputation::Compare { result, .. } => result,
    }
}

/// Independently compare reached source-computation stores with typed results.
///
/// The caller must first validate the same normative VM trace against the
/// source-locked code, effect order, phi copies and source frame write sites.
/// This check does not choose a CFG edge, emulate a guest computation or
/// establish causal use of operands by the Malbolge opcodes.
///
/// # Errors
///
/// Refuses missing source operand cells, unsupported computation kinds,
/// noncanonical scalar representations or numerically incorrect guest stores.
#[expect(
    clippy::too_many_arguments,
    clippy::too_many_lines,
    reason = "one guest frame write journal with ordered source result checks"
)]
pub(super) fn verify_source_computation_values(
    operations: &[GuestCodeOperationSite],
    effects: &[GuestCodeOperationEffectSite],
    edges: &[GuestCodeControlEdge],
    frames: &[GuestFramePlacement],
    steps: &[ProfileStepTrace],
) -> Result<(), SourcePhiCopyTraceError> {
    let computations: BTreeMap<OperationId, GuestCodeComputation> = operations
        .iter()
        .filter_map(|site| {
            site.computation.map(|computation| {
                ((site.function, site.block, site.ordinal), computation)
            })
        })
        .collect();
    let by_address: BTreeMap<u32, &GuestCodeOperationEffectSite> = effects
        .iter()
        .map(|effect| (effect.code_address, effect))
        .collect();
    let copy_destinations: BTreeMap<u32, u32> = edges
        .iter()
        .flat_map(|edge| edge.snapshot_sites.iter().chain(&edge.commit_sites))
        .map(|site| (site.code_address, site.copy.destination))
        .collect();
    let mut written = BTreeMap::new();
    let mut pending: BTreeMap<OperationId, u32> = BTreeMap::new();
    for step in steps {
        if !matches!(step.decoded, Some(b'p' | b'*')) {
            continue;
        }
        let code = step.before.registers.code_pointer;
        let destination = step.before.registers.data_pointer;
        if !frames.iter().any(|frame| {
            (frame.base..frame.end_exclusive).contains(&destination)
        }) {
            continue;
        }
        if copy_destinations.get(&code) == Some(&destination) {
            let _previous =
                written.insert(destination, step.after.registers.accumulator);
            continue;
        }
        let effect = by_address
            .get(&code)
            .ok_or(SourcePhiCopyTraceError::UnexpectedFrameEffect)?;
        let GuestCodeOperationEffect::Store {
            destination: expected, ..
        } = effect.effect
        else {
            return Err(SourcePhiCopyTraceError::InvalidBlockEffect);
        };
        if expected != destination {
            return Err(SourcePhiCopyTraceError::UnexpectedFrameEffect);
        }
        let key = (effect.function, effect.block, effect.ordinal);
        if let Some(&computation) = computations.get(&key) {
            let computed = if let Some(&value) = pending.get(&key) {
                value
            } else {
                let value = evaluate(computation, &written)?;
                let _previous = pending.insert(key, value);
                value
            };
            if step.after.registers.accumulator
                != expected_word(
                    computed,
                    result_operand(computation),
                    destination,
                )?
            {
                return Err(SourcePhiCopyTraceError::InvalidComputationValue);
            }
            let last_effect = effects
                .iter()
                .filter(|site| (site.function, site.block, site.ordinal) == key)
                .map(|site| site.code_address)
                .max();
            if last_effect == Some(code) {
                let _done = pending.remove(&key);
            }
        }
        let _previous =
            written.insert(destination, step.after.registers.accumulator);
    }
    if !pending.is_empty() {
        return Err(SourcePhiCopyTraceError::MissingBlockEffect);
    }
    Ok(())
}

#[cfg(test)]
#[path = "../../../../tests/compiler/source_computation_trace.rs"]
mod tests;
