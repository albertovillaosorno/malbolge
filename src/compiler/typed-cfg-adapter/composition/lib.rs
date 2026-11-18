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
//   - Canonical typed-IR to validated symbolic ternary CFG composition.
// - Must-Not:
//   - Invent phi edges, replay input on the host, serialize MCTR-v1, or publish
//     unlinked CFG as executable Malbolge.
// - Allows:
//   - Inputs: independently decoded canonical typed-IR bytes.
//   - Outputs: a provenance-preserving, pre-layout TernaryCfgPlan.
//   - Side effects: none.
// - Split-When:
//   - Physical guest value storage and control relocation require a linker.
// - Merge-When:
//   - The general compiler composition subsumes this exact typed boundary.
// - Summary:
//   - Preserves real typed SSA, block edges and input effects without a
//     caller-authored projection or executable guest claim.
// - Description:
//   - Copies only validated typed values and delegates CFG/SSA admission to the
//     independently checked ternary lowerer.
// - Usage:
//   - Call `lower_canonical_dynamic_cfg` with canonical MCTI bytes.
// - Defaults:
//   - Unsupported source effects fail closed before target layout.
//

//! Validated typed compiler IR to unlinked ternary CFG composition.

#[path = "phi_edge_transfers.rs"]
mod phi_edge_transfers;
#[path = "state_operations.rs"]
pub mod state_operations;
#[path = "state_storage.rs"]
pub mod state_storage;

#[path = "../../ternary-lowering/composition/lib.rs"]
pub mod ternary;
#[path = "../../typed-ir/composition/lib.rs"]
pub mod typed;

pub use phi_edge_transfers::{PhiEdgeMove, PhiEdgeTransfers, PrelinkCfgPlan};
use ternary::{
    InputBlock, InputDynamicBlockPhis, InputDynamicPhi, InputFunction,
    InputInstruction, InputOrderedComparison, InputPhiIncoming,
    InputScalarType, InputSourcePosition, InputSourceSpan, InputTerminator,
    TernaryCfgPlan, TernaryLoweringError, TypedIrInput,
    lower_dynamic_typed_cfg,
};
use typed::{
    BinaryOp, CanonicalDecodeError, CastOp, CompareOp, Function, Instruction,
    LocatedInstruction, Module, SourcePosition, SourceSpan, Terminator,
    TypeDef, TypeId, canonical_module,
};

/// An exact failure before or during canonical dynamic-CFG lowering.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TypedCfgAdapterError {
    /// Relocatable guest frame allocation or parallel-copy proof failed.
    GuestStateAllocation,
    /// The canonical MCTI decoder rejected invalid or noncanonical bytes.
    InvalidTypedIr(CanonicalDecodeError),
    /// The symbolic ternary CFG rejected an invalid or unsupported projection.
    Lowering(TernaryLoweringError),
    /// An independently validated typed operation lacks target semantics.
    UnsupportedTypedIr,
}

const fn position(value: SourcePosition) -> InputSourcePosition {
    InputSourcePosition {
        byte: value.byte(),
        column: value.column(),
        line: value.line(),
    }
}

const fn span(value: SourceSpan) -> InputSourceSpan {
    InputSourceSpan {
        begin: position(value.begin()),
        end: position(value.end()),
    }
}

fn scalar_kind(module: &Module, id: TypeId) -> InputScalarType {
    let definition = usize::try_from(id.value())
        .ok()
        .and_then(|index| module.types().get(index))
        .filter(|entry| entry.id() == id)
        .map(typed::TypeEntry::definition);
    match definition {
        Some(TypeDef::Bool) => InputScalarType::Bool,
        Some(TypeDef::I8) => InputScalarType::I8,
        Some(TypeDef::I16) => InputScalarType::I16,
        Some(TypeDef::I32) => InputScalarType::I32,
        Some(TypeDef::U8) => InputScalarType::U8,
        Some(TypeDef::U16) => InputScalarType::U16,
        Some(TypeDef::U32) => InputScalarType::U32,
        _ => InputScalarType::Other,
    }
}

fn instruction(
    module: &Module,
    located: &LocatedInstruction,
) -> Result<InputInstruction, TypedCfgAdapterError> {
    let location = span(located.span());
    let converted = match located.instruction() {
        Instruction::Binary {
            left,
            operation,
            result,
            right,
            type_id,
        } => {
            let left = left.value();
            let result = result.value();
            let right = right.value();
            let span = location;
            let type_kind = scalar_kind(module, *type_id);
            match operation {
                BinaryOp::Add => InputInstruction::BinaryAdd {
                    left,
                    result,
                    right,
                    span,
                    type_kind,
                },
                BinaryOp::And => InputInstruction::BinaryAnd {
                    left,
                    result,
                    right,
                    span,
                    type_kind,
                },
                BinaryOp::DivideSigned => {
                    InputInstruction::BinaryDivideSigned {
                        left,
                        result,
                        right,
                        span,
                        type_kind,
                    }
                },
                BinaryOp::DivideUnsigned => {
                    InputInstruction::BinaryDivideUnsigned {
                        left,
                        result,
                        right,
                        span,
                        type_kind,
                    }
                },
                BinaryOp::Multiply => InputInstruction::BinaryMultiply {
                    left,
                    result,
                    right,
                    span,
                    type_kind,
                },
                BinaryOp::Or => InputInstruction::BinaryOr {
                    left,
                    result,
                    right,
                    span,
                    type_kind,
                },
                BinaryOp::RemainderSigned => {
                    InputInstruction::BinaryRemainderSigned {
                        left,
                        result,
                        right,
                        span,
                        type_kind,
                    }
                },
                BinaryOp::RemainderUnsigned => {
                    InputInstruction::BinaryRemainderUnsigned {
                        left,
                        result,
                        right,
                        span,
                        type_kind,
                    }
                },
                BinaryOp::ShiftLeft => InputInstruction::BinaryShiftLeft {
                    left,
                    result,
                    right,
                    span,
                    type_kind,
                },
                BinaryOp::ShiftRightArithmetic => {
                    InputInstruction::BinaryShiftRightArithmetic {
                        left,
                        result,
                        right,
                        span,
                        type_kind,
                    }
                },
                BinaryOp::ShiftRightLogical => {
                    InputInstruction::BinaryShiftRightLogical {
                        left,
                        result,
                        right,
                        span,
                        type_kind,
                    }
                },
                BinaryOp::Subtract => InputInstruction::BinarySubtract {
                    left,
                    result,
                    right,
                    span,
                    type_kind,
                },
                BinaryOp::Xor => InputInstruction::BinaryXor {
                    left,
                    result,
                    right,
                    span,
                    type_kind,
                },
                BinaryOp::DivideFloat => {
                    return Err(TypedCfgAdapterError::UnsupportedTypedIr);
                },
            }
        },
        Instruction::ByteInput { result, type_id } => {
            InputInstruction::ByteInput {
                result: result.value(),
                span: location,
                type_kind: scalar_kind(module, *type_id),
            }
        },
        Instruction::Getchar { result, type_id } => InputInstruction::Getchar {
            result: result.value(),
            span: location,
            type_kind: scalar_kind(module, *type_id),
        },
        Instruction::ByteOutput { value } => InputInstruction::ByteOutput {
            span: location,
            value: value.value(),
        },
        Instruction::Cast {
            operation,
            result,
            type_id,
            value,
        } => {
            let result = result.value();
            let span = location;
            let type_kind = scalar_kind(module, *type_id);
            let value = value.value();
            match operation {
                CastOp::BoolToSigned => InputInstruction::BoolToSigned {
                    result,
                    span,
                    type_kind,
                    value,
                },
                CastOp::IntegerBitcast => InputInstruction::IntegerBitcast {
                    result,
                    span,
                    type_kind,
                    value,
                },
                CastOp::IntegerToBool => InputInstruction::IntegerToBool {
                    result,
                    span,
                    type_kind,
                    value,
                },
                CastOp::SignExtend => InputInstruction::SignExtendI8ToI32 {
                    result,
                    span,
                    type_kind,
                    value,
                },
                CastOp::Truncate => InputInstruction::TruncateInteger {
                    result,
                    span,
                    type_kind,
                    value,
                },
                CastOp::ZeroExtend => InputInstruction::ZeroExtendInteger {
                    result,
                    span,
                    type_kind,
                    value,
                },
                CastOp::Bitcast
                | CastOp::FloatToBool
                | CastOp::FloatToFloat
                | CastOp::FloatToSigned
                | CastOp::FloatToUnsigned
                | CastOp::IntegerToPointer
                | CastOp::PointerToBool
                | CastOp::PointerToInteger
                | CastOp::SignedToFloat
                | CastOp::UnsignedToFloat => {
                    return Err(TypedCfgAdapterError::UnsupportedTypedIr);
                },
            }
        },
        Instruction::Compare {
            left,
            operation,
            result,
            right,
            type_id,
        } => {
            let left = left.value();
            let result = result.value();
            let right = right.value();
            let span = location;
            let type_kind = scalar_kind(module, *type_id);
            match operation {
                CompareOp::Equal => InputInstruction::CompareEqual {
                    left,
                    result,
                    right,
                    span,
                    type_kind,
                },
                CompareOp::NotEqual => InputInstruction::CompareNotEqual {
                    left,
                    result,
                    right,
                    span,
                    type_kind,
                },
                CompareOp::LessSigned
                | CompareOp::LessSignedEqual
                | CompareOp::LessUnsigned
                | CompareOp::LessUnsignedEqual => {
                    let operation = match operation {
                        CompareOp::LessSigned => InputOrderedComparison::Signed,
                        CompareOp::LessSignedEqual => {
                            InputOrderedComparison::SignedEqual
                        },
                        CompareOp::LessUnsigned => {
                            InputOrderedComparison::Unsigned
                        },
                        CompareOp::LessUnsignedEqual => {
                            InputOrderedComparison::UnsignedEqual
                        },
                        CompareOp::Equal
                        | CompareOp::NotEqual
                        | CompareOp::FloatLess
                        | CompareOp::FloatLessEqual => {
                            return Err(
                                TypedCfgAdapterError::UnsupportedTypedIr,
                            );
                        },
                    };
                    InputInstruction::CompareOrdered {
                        left,
                        operation,
                        result,
                        right,
                        span,
                        type_kind,
                    }
                },
                CompareOp::FloatLess | CompareOp::FloatLessEqual => {
                    return Err(TypedCfgAdapterError::UnsupportedTypedIr);
                },
            }
        },
        Instruction::ConstantInteger {
            constant,
            result,
            type_id,
        } => InputInstruction::ConstantInteger {
            bit_width: constant.bit_width(),
            little_endian: constant.little_endian().to_vec(),
            result: result.value(),
            span: location,
            type_kind: scalar_kind(module, *type_id),
        },
        Instruction::AddressOffset { .. }
        | Instruction::AutomaticAllocate { .. }
        | Instruction::Call { .. }
        | Instruction::FunctionAddress { .. }
        | Instruction::Load { .. }
        | Instruction::Store { .. } => {
            return Err(TypedCfgAdapterError::UnsupportedTypedIr);
        },
    };
    Ok(converted)
}

fn function_projection(
    module: &Module,
    function: &Function,
) -> Result<(InputFunction, Vec<InputDynamicBlockPhis>), TypedCfgAdapterError> {
    let return_kind = module
        .types()
        .iter()
        .find(|entry| entry.id() == function.signature())
        .and_then(|entry| match entry.definition() {
            TypeDef::Function { result: None, .. } => {
                Some(InputScalarType::Void)
            },
            TypeDef::Function { result: Some(result), .. } => {
                Some(scalar_kind(module, *result))
            },
            _ => None,
        })
        .ok_or(TypedCfgAdapterError::UnsupportedTypedIr)?;
    let mut blocks = Vec::with_capacity(function.blocks().len());
    let mut bindings = Vec::new();
    for block in function.blocks() {
        let terminator = match block.terminator() {
            Terminator::Branch {
                condition,
                false_target,
                true_target,
            } => InputTerminator::Branch {
                condition: condition.value(),
                false_target: false_target.value(),
                span: span(block.terminator_span()),
                true_target: true_target.value(),
            },
            Terminator::Jump { target } => InputTerminator::Jump {
                span: span(block.terminator_span()),
                target: target.value(),
            },
            Terminator::Return { value } => InputTerminator::Return {
                span: span(block.terminator_span()),
                value: value.map(typed::ValueId::value),
            },
            Terminator::Switch { .. } => {
                return Err(TypedCfgAdapterError::UnsupportedTypedIr);
            },
        };
        let operations = block
            .instructions()
            .iter()
            .map(|item| instruction(module, item))
            .collect::<Result<Vec<_>, _>>()?;
        blocks.push(InputBlock {
            id: block.id().value(),
            instructions: operations,
            phi_count: block.phis().len(),
            terminator,
        });
        if !block.phis().is_empty() {
            bindings.push(InputDynamicBlockPhis {
                block: block.id().value(),
                function: function.id().value(),
                phis: block
                    .phis()
                    .iter()
                    .map(|phi| InputDynamicPhi {
                        incoming: phi
                            .incoming()
                            .iter()
                            .map(|edge| InputPhiIncoming {
                                block: edge.block().value(),
                                value: edge.value().value(),
                            })
                            .collect(),
                        result: phi.result().value(),
                        span: span(phi.span()),
                        type_kind: scalar_kind(module, phi.type_id()),
                    })
                    .collect(),
            });
        }
    }
    Ok((
        InputFunction {
            blocks,
            entry: function.entry().value(),
            id: function.id().value(),
            name: function.name().to_owned(),
            parameter_count: function.parameters().len(),
            return_kind,
            span: span(function.span()),
        },
        bindings,
    ))
}

/// Decodes the canonical typed wire and lowers its complete admitted CFG.
/// No caller may supply phi edges or substitute source/SSA identities.
///
/// # Errors
///
/// Returns an explicit error for noncanonical typed bytes, unsupported
/// instructions or CFG shapes, and symbolic ternary lowering failures.
/// This stage cannot publish Malbolge or serialize MCTR-v1.
pub fn lower_canonical_dynamic_cfg(
    canonical: &[u8],
) -> Result<TernaryCfgPlan, TypedCfgAdapterError> {
    let module = canonical_module(canonical)
        .map_err(TypedCfgAdapterError::InvalidTypedIr)?;
    let mut functions = Vec::with_capacity(module.functions().len());
    let mut bindings = Vec::new();
    for function in module.functions() {
        let (projected, mut phis) = function_projection(&module, function)?;
        functions.push(projected);
        bindings.append(&mut phis);
    }
    let input = TypedIrInput {
        abi_id: module.abi_id().to_owned(),
        functions,
        global_count: module.globals().len(),
        input_format_version: module.format_version(),
        proof_obligation_count: module.proof_obligations().len(),
        source_id: module.source_id().to_owned(),
        source_sha256: *module.source_sha256(),
        target_profile: module.target_profile().to_owned(),
    };
    lower_dynamic_typed_cfg(&input, &bindings)
        .map_err(TypedCfgAdapterError::Lowering)
}

/// Also reserves disjoint frame-relative state cells and stages parallel phi
/// assignments for future physical guest state and control linkage.
///
/// # Errors
///
/// Propagates canonical typed decoding, symbolic CFG lowering and phi-edge
/// consistency errors, without creating guest source or a physical layout.
pub fn prepare_canonical_dynamic_cfg(
    canonical: &[u8],
) -> Result<PrelinkCfgPlan, TypedCfgAdapterError> {
    let cfg = lower_canonical_dynamic_cfg(canonical)?;
    if cfg.target_profile != "malbolge-2026" {
        return Err(TypedCfgAdapterError::UnsupportedTypedIr);
    }
    let phi_edges = phi_edge_transfers::plan_phi_edges(&cfg)?;
    let module = canonical_module(canonical)
        .map_err(TypedCfgAdapterError::InvalidTypedIr)?;
    let state_frames = module
        .functions()
        .iter()
        .map(|function| {
            state_storage::plan_frame(&module, function, &phi_edges)
        })
        .collect::<Result<Vec<_>, _>>()?;
    let mut operation_blocks = Vec::new();
    for (function, frame) in module.functions().iter().zip(&state_frames) {
        operation_blocks.extend(state_operations::bind_function_operations(
            &module, function, frame,
        )?);
    }
    let mut cell_edges = Vec::new();
    for edge in &phi_edges {
        let frame = state_frames
            .iter()
            .find(|frame| frame.function == edge.function)
            .ok_or(TypedCfgAdapterError::GuestStateAllocation)?;
        cell_edges.push(state_storage::plan_cell_edge(frame, edge)?);
    }
    Ok(PrelinkCfgPlan {
        cell_edges,
        cfg,
        operation_blocks,
        phi_edges,
        state_frames,
    })
}
