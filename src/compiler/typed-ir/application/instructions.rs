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
//   - Typed operand/result, call, terminator, constant, and use-dominance
//     admission.
// - Must-Not:
//   - Rewrite IR, infer missing casts, or discharge proof obligations.
// - Allows:
//   - Inputs: one function, module type/callee tables, SSA values, and CFG
//     analysis.
//   - Outputs: deterministic success or one stable admission failure.
//   - Side effects: temporary ordered switch-case sets only.
// - Split-When:
//   - Floating-point or aggregate instruction semantics gain separate
//     versioning.
// - Merge-When:
//   - One application validator remains clearer than semantic family
//     separation.
// - Summary:
//   - Proves typed instruction and control-flow uses before canonical encoding.
// - Description:
//   - Operand existence and SSA dominance are checked as distinct obligations.
// - Usage:
//   - Called for every admitted typed-IR function after CFG construction.
// - Defaults:
//   - Alignment is a positive power of two no larger than ABI maximum 16.
//

//! Instruction, call, terminator, and SSA-use admission for typed compiler IR.

use std::collections::BTreeSet;

use super::cfg::{
    ControlFlow, InstructionPoint, available_at_instruction,
    available_at_terminator, value_type,
};
use super::control::{BasicBlock, SwitchCase, Terminator};
use super::error::ValidationError;
use super::ids::{BlockId, FunctionId, TypeId, ValueId};
use super::instruction::{
    BinaryOp, CallTarget, CastOp, CompareOp, Instruction, IntegerConstant,
};
use super::module::{Function, Module};
use super::type_validation::{
    definition, float_width, function_signature, integer_width, is_bool,
    is_float, is_function_pointer, is_function_value_type, is_integer,
    is_non_bool_integer, is_object_pointer, is_signed_integer,
    is_unsigned_integer, pointee, requires_integer_promotion,
};
use super::types::{TypeDef, TypeEntry};
use super::values::ValueTable;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct BinaryShape {
    left: ValueId,
    right: ValueId,
    type_id: TypeId,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct CompareShape {
    left: ValueId,
    result_type: TypeId,
    right: ValueId,
}

struct FunctionContext<'context> {
    flow: &'context ControlFlow,
    function: &'context Function,
    module: &'context Module,
    values: &'context ValueTable,
}

struct InstructionContext<'context> {
    block: &'context BasicBlock,
    flow: &'context ControlFlow,
    module: &'context Module,
    order: u32,
    values: &'context ValueTable,
}

impl InstructionContext<'_> {
    fn type_of_use(&self, value: ValueId) -> Result<TypeId, ValidationError> {
        let type_id = value_type(self.values, value)?;
        let point = InstructionPoint {
            block: self.block.id(),
            order: self.order,
        };
        if !available_at_instruction(self.flow, self.values, value, point) {
            return Err(ValidationError::SsaDominance);
        }
        Ok(type_id)
    }

    fn types(&self) -> &[TypeEntry] {
        self.module.types()
    }
}

pub(super) fn validate_function_semantics(
    module: &Module,
    function: &Function,
    values: &ValueTable,
    flow: &ControlFlow,
) -> Result<(), ValidationError> {
    validate_signature(module.types(), function)?;
    let context = FunctionContext {
        flow,
        function,
        module,
        values,
    };
    for block in function.blocks() {
        validate_block_instructions(module, block, values, flow)?;
        validate_terminator(&context, block)?;
    }
    Ok(())
}

fn function_by_id(
    module: &Module,
    function_id: FunctionId,
) -> Option<&Function> {
    let index = usize::try_from(function_id.value()).ok()?;
    module
        .functions()
        .get(index)
        .filter(|function| function.id() == function_id)
}

fn require_terminator_use(
    flow: &ControlFlow,
    values: &ValueTable,
    value: ValueId,
    block: BlockId,
) -> Result<TypeId, ValidationError> {
    let type_id = value_type(values, value)?;
    if !available_at_terminator(flow, values, value, block) {
        return Err(ValidationError::SsaDominance);
    }
    Ok(type_id)
}

const fn valid_alignment(alignment: u8) -> bool {
    alignment.is_power_of_two() && alignment <= 16
}

fn validate_block_instructions(
    module: &Module,
    block: &BasicBlock,
    values: &ValueTable,
    flow: &ControlFlow,
) -> Result<(), ValidationError> {
    for (index, instruction) in block.instructions().iter().enumerate() {
        let order = u32::try_from(index)
            .map_err(|_error| ValidationError::ValueIdentity)?;
        let context = InstructionContext {
            block,
            flow,
            module,
            order,
            values,
        };
        validate_instruction(&context, instruction.instruction())?;
    }
    Ok(())
}

const fn instruction_is_high(instruction: &Instruction) -> bool {
    match instruction {
        Instruction::AddressOffset { .. }
        | Instruction::Binary { .. }
        | Instruction::ByteInput { .. }
        | Instruction::ByteOutput { .. }
        | Instruction::Call { .. } => false,
        Instruction::AutomaticAllocate { .. }
        | Instruction::Cast { .. }
        | Instruction::Compare { .. }
        | Instruction::ConstantInteger { .. }
        | Instruction::FunctionAddress { .. }
        | Instruction::Load { .. }
        | Instruction::Store { .. } => true,
    }
}

fn validate_instruction(
    context: &InstructionContext<'_>,
    instruction: &Instruction,
) -> Result<(), ValidationError> {
    if instruction_is_high(instruction) {
        validate_instruction_high(context, instruction)
    } else {
        validate_instruction_low(context, instruction)
    }
}

fn validate_instruction_low(
    context: &InstructionContext<'_>,
    instruction: &Instruction,
) -> Result<(), ValidationError> {
    match instruction {
        Instruction::AddressOffset {
            byte_offset,
            pointer,
            type_id,
            ..
        } => validate_address_offset(context, *pointer, *byte_offset, *type_id),
        Instruction::Binary {
            left,
            operation,
            right,
            type_id,
            ..
        } => validate_binary(
            context,
            BinaryShape {
                left: *left,
                right: *right,
                type_id: *type_id,
            },
            *operation,
        ),
        Instruction::ByteInput { type_id, .. } => {
            validate_byte_type(context.types(), *type_id)
        },
        Instruction::ByteOutput { value } => {
            validate_byte_type(context.types(), context.type_of_use(*value)?)
        },
        Instruction::Call {
            arguments,
            callee,
            result,
        } => validate_call(context, arguments, *callee, *result),
        Instruction::AutomaticAllocate { .. }
        | Instruction::Cast { .. }
        | Instruction::Compare { .. }
        | Instruction::ConstantInteger { .. }
        | Instruction::FunctionAddress { .. }
        | Instruction::Load { .. }
        | Instruction::Store { .. } => Ok(()),
    }
}

fn validate_instruction_high(
    context: &InstructionContext<'_>,
    instruction: &Instruction,
) -> Result<(), ValidationError> {
    match instruction {
        Instruction::AutomaticAllocate {
            alignment,
            byte_count,
            type_id,
            ..
        } => validate_automatic_allocate(
            context,
            *byte_count,
            *type_id,
            *alignment,
        ),
        Instruction::Cast {
            operation,
            type_id,
            value,
            ..
        } => validate_cast(context, *value, *type_id, *operation),
        Instruction::Compare {
            left,
            operation,
            right,
            type_id,
            ..
        } => validate_compare(
            context,
            CompareShape {
                left: *left,
                result_type: *type_id,
                right: *right,
            },
            *operation,
        ),
        Instruction::ConstantInteger { constant, type_id, .. } => {
            validate_integer_constant(context.types(), *type_id, constant)
        },
        Instruction::FunctionAddress { function, type_id, .. } => {
            validate_function_address(context, *function, *type_id)
        },
        Instruction::Load {
            alignment,
            pointer,
            type_id,
            ..
        } => validate_load(context, *pointer, *type_id, *alignment),
        Instruction::Store {
            alignment,
            pointer,
            value,
        } => validate_store(context, *pointer, *value, *alignment),
        Instruction::AddressOffset { .. }
        | Instruction::Binary { .. }
        | Instruction::ByteInput { .. }
        | Instruction::ByteOutput { .. }
        | Instruction::Call { .. } => Ok(()),
    }
}

fn validate_signature(
    types: &[TypeEntry],
    function: &Function,
) -> Result<(), ValidationError> {
    let signature = function_signature(types, function.signature())?;
    if signature.parameters.len() != function.parameters().len() {
        return Err(ValidationError::FunctionIdentity);
    }
    for (parameter, expected) in
        function.parameters().iter().zip(signature.parameters)
    {
        if parameter.type_id() != *expected {
            return Err(ValidationError::FunctionIdentity);
        }
    }
    Ok(())
}

fn validate_address_offset(
    context: &InstructionContext<'_>,
    pointer: ValueId,
    byte_offset: ValueId,
    type_id: TypeId,
) -> Result<(), ValidationError> {
    let pointer_type = context.type_of_use(pointer)?;
    let offset_type = context.type_of_use(byte_offset)?;
    if pointer_type != type_id
        || !is_object_pointer(context.types(), type_id)
        || !is_integer(context.types(), offset_type)
    {
        return Err(ValidationError::OperandType);
    }
    Ok(())
}

fn validate_automatic_allocate(
    context: &InstructionContext<'_>,
    byte_count: ValueId,
    pointer_type: TypeId,
    alignment: u8,
) -> Result<(), ValidationError> {
    let count_type = context.type_of_use(byte_count)?;
    if !valid_alignment(alignment)
        || !matches!(definition(context.types(), count_type), Ok(TypeDef::U32))
        || !is_object_pointer(context.types(), pointer_type)
    {
        return Err(ValidationError::OperandType);
    }
    Ok(())
}

fn validate_function_address(
    context: &InstructionContext<'_>,
    function_id: FunctionId,
    pointer_type: TypeId,
) -> Result<(), ValidationError> {
    let function = function_by_id(context.module, function_id)
        .ok_or(ValidationError::CallSignature)?;
    if pointee(context.types(), pointer_type) != Some(function.signature()) {
        return Err(ValidationError::CallSignature);
    }
    Ok(())
}

fn validate_binary(
    context: &InstructionContext<'_>,
    shape: BinaryShape,
    operation: BinaryOp,
) -> Result<(), ValidationError> {
    if context.type_of_use(shape.left)? != shape.type_id
        || context.type_of_use(shape.right)? != shape.type_id
    {
        return Err(ValidationError::OperandType);
    }
    let promoted_integer = is_non_bool_integer(context.types(), shape.type_id)
        && !requires_integer_promotion(context.types(), shape.type_id);
    let valid = match operation {
        BinaryOp::Add | BinaryOp::Multiply | BinaryOp::Subtract => {
            promoted_integer || is_float(context.types(), shape.type_id)
        },
        BinaryOp::And | BinaryOp::Or | BinaryOp::ShiftLeft | BinaryOp::Xor => {
            promoted_integer
        },
        BinaryOp::DivideFloat => is_float(context.types(), shape.type_id),
        BinaryOp::DivideSigned
        | BinaryOp::RemainderSigned
        | BinaryOp::ShiftRightArithmetic => {
            promoted_integer
                && is_signed_integer(context.types(), shape.type_id)
        },
        BinaryOp::DivideUnsigned
        | BinaryOp::RemainderUnsigned
        | BinaryOp::ShiftRightLogical => {
            promoted_integer
                && is_unsigned_integer(context.types(), shape.type_id)
        },
    };
    if !valid {
        return Err(ValidationError::OperandType);
    }
    Ok(())
}

fn validate_byte_type(
    types: &[TypeEntry],
    type_id: TypeId,
) -> Result<(), ValidationError> {
    if !matches!(definition(types, type_id), Ok(TypeDef::U8)) {
        return Err(ValidationError::OperandType);
    }
    Ok(())
}

fn validate_compare(
    context: &InstructionContext<'_>,
    shape: CompareShape,
    operation: CompareOp,
) -> Result<(), ValidationError> {
    let operand_type = context.type_of_use(shape.left)?;
    if context.type_of_use(shape.right)? != operand_type
        || !is_bool(context.types(), shape.result_type)
    {
        return Err(ValidationError::OperandType);
    }
    let promoted_integer = is_non_bool_integer(context.types(), operand_type)
        && !requires_integer_promotion(context.types(), operand_type);
    let valid = match operation {
        CompareOp::Equal | CompareOp::NotEqual => {
            promoted_integer
                || is_float(context.types(), operand_type)
                || pointee(context.types(), operand_type).is_some()
        },
        CompareOp::FloatLess | CompareOp::FloatLessEqual => {
            is_float(context.types(), operand_type)
        },
        CompareOp::LessSigned | CompareOp::LessSignedEqual => {
            promoted_integer && is_signed_integer(context.types(), operand_type)
        },
        CompareOp::LessUnsigned | CompareOp::LessUnsignedEqual => {
            promoted_integer
                && is_unsigned_integer(context.types(), operand_type)
        },
    };
    if !valid {
        return Err(ValidationError::OperandType);
    }
    Ok(())
}

fn validate_integer_constant(
    types: &[TypeEntry],
    type_id: TypeId,
    constant: &IntegerConstant,
) -> Result<(), ValidationError> {
    let width = integer_width(types, type_id)
        .ok_or(ValidationError::IntegerConstant)?;
    let expected_bytes = usize::from(width.div_ceil(8));
    if constant.bit_width() != width
        || constant.little_endian().len() != expected_bytes
    {
        return Err(ValidationError::IntegerConstant);
    }
    if width == 1
        && constant
            .little_endian()
            .first()
            .is_none_or(|value| *value > 1)
    {
        return Err(ValidationError::IntegerConstant);
    }
    Ok(())
}

fn validate_call(
    context: &InstructionContext<'_>,
    arguments: &[ValueId],
    callee: CallTarget,
    result: Option<(ValueId, TypeId)>,
) -> Result<(), ValidationError> {
    let signature_type = resolve_call_signature_type(context, callee)?;
    let signature = function_signature(context.types(), signature_type)?;
    if arguments.len() < signature.parameters.len()
        || (!signature.variadic
            && arguments.len() != signature.parameters.len())
    {
        return Err(ValidationError::CallSignature);
    }
    for (argument, expected) in arguments.iter().zip(signature.parameters) {
        if context.type_of_use(*argument)? != *expected {
            return Err(ValidationError::CallSignature);
        }
    }
    for argument in arguments.iter().skip(signature.parameters.len()) {
        let argument_type = context.type_of_use(*argument)?;
        if !is_function_value_type(context.types(), argument_type)
            || requires_default_argument_promotion(
                context.types(),
                argument_type,
            )
        {
            return Err(ValidationError::CallSignature);
        }
    }
    match (result, signature.result) {
        (None, None) => Ok(()),
        (Some((_value, observed)), Some(expected)) if observed == expected => {
            Ok(())
        },
        _ => Err(ValidationError::CallSignature),
    }
}

fn requires_default_argument_promotion(
    types: &[TypeEntry],
    type_id: TypeId,
) -> bool {
    requires_integer_promotion(types, type_id)
        || matches!(definition(types, type_id), Ok(TypeDef::F32))
}

fn resolve_call_signature_type(
    context: &InstructionContext<'_>,
    callee: CallTarget,
) -> Result<TypeId, ValidationError> {
    match callee {
        CallTarget::Direct(function_id) => {
            function_by_id(context.module, function_id)
                .map(Function::signature)
                .ok_or(ValidationError::CallSignature)
        },
        CallTarget::Indirect(value) => {
            let pointer_type = context.type_of_use(value)?;
            let signature_type = pointee(context.types(), pointer_type)
                .ok_or(ValidationError::CallSignature)?;
            if !matches!(
                definition(context.types(), signature_type),
                Ok(TypeDef::Function { .. })
            ) {
                return Err(ValidationError::CallSignature);
            }
            Ok(signature_type)
        },
    }
}

fn validate_cast(
    context: &InstructionContext<'_>,
    value: ValueId,
    destination: TypeId,
    operation: CastOp,
) -> Result<(), ValidationError> {
    let source = context.type_of_use(value)?;
    _ = definition(context.types(), destination)?;
    let valid = if matches!(
        operation,
        CastOp::Bitcast
            | CastOp::BoolToSigned
            | CastOp::FloatToBool
            | CastOp::FloatToFloat
            | CastOp::FloatToSigned
            | CastOp::FloatToUnsigned
            | CastOp::IntegerBitcast
            | CastOp::IntegerToBool
    ) {
        validate_cast_low(context.types(), source, destination, operation)
    } else {
        validate_cast_high(context.types(), source, destination, operation)
    };
    if !valid {
        return Err(ValidationError::OperandType);
    }
    Ok(())
}

fn validate_cast_low(
    types: &[TypeEntry],
    source: TypeId,
    destination: TypeId,
    operation: CastOp,
) -> bool {
    match operation {
        CastOp::Bitcast => {
            (is_object_pointer(types, source)
                && is_object_pointer(types, destination))
                || (is_function_pointer(types, source)
                    && is_function_pointer(types, destination))
        },
        CastOp::BoolToSigned => {
            is_bool(types, source) && is_signed_integer(types, destination)
        },
        CastOp::FloatToBool => {
            is_float(types, source) && is_bool(types, destination)
        },
        CastOp::FloatToFloat => {
            float_width(types, source).is_some()
                && float_width(types, destination).is_some()
        },
        CastOp::FloatToSigned => {
            is_float(types, source) && is_signed_integer(types, destination)
        },
        CastOp::FloatToUnsigned => {
            is_float(types, source)
                && is_unsigned_integer(types, destination)
                && !is_bool(types, destination)
        },
        CastOp::IntegerBitcast => {
            is_non_bool_integer(types, source)
                && is_non_bool_integer(types, destination)
                && integer_width(types, source)
                    == integer_width(types, destination)
        },
        CastOp::IntegerToBool => {
            is_non_bool_integer(types, source) && is_bool(types, destination)
        },
        CastOp::IntegerToPointer
        | CastOp::PointerToBool
        | CastOp::PointerToInteger
        | CastOp::SignExtend
        | CastOp::SignedToFloat
        | CastOp::Truncate
        | CastOp::UnsignedToFloat
        | CastOp::ZeroExtend => false,
    }
}

fn validate_cast_high(
    types: &[TypeEntry],
    source: TypeId,
    destination: TypeId,
    operation: CastOp,
) -> bool {
    match operation {
        CastOp::IntegerToPointer => {
            integer_width(types, source) == Some(32)
                && !is_bool(types, source)
                && is_object_pointer(types, destination)
        },
        CastOp::PointerToBool => {
            pointee(types, source).is_some() && is_bool(types, destination)
        },
        CastOp::PointerToInteger => {
            is_object_pointer(types, source)
                && integer_width(types, destination) == Some(32)
                && !is_bool(types, destination)
        },
        CastOp::SignExtend => {
            validate_integer_extension(types, source, destination, true)
        },
        CastOp::SignedToFloat => {
            is_signed_integer(types, source) && is_float(types, destination)
        },
        CastOp::Truncate => {
            validate_integer_truncation(types, source, destination)
        },
        CastOp::UnsignedToFloat => {
            is_unsigned_integer(types, source)
                && !is_bool(types, source)
                && is_float(types, destination)
        },
        CastOp::ZeroExtend => {
            validate_integer_extension(types, source, destination, false)
        },
        CastOp::Bitcast
        | CastOp::BoolToSigned
        | CastOp::FloatToBool
        | CastOp::FloatToFloat
        | CastOp::FloatToSigned
        | CastOp::FloatToUnsigned
        | CastOp::IntegerBitcast
        | CastOp::IntegerToBool => false,
    }
}

fn validate_integer_extension(
    types: &[TypeEntry],
    source: TypeId,
    destination: TypeId,
    signed: bool,
) -> bool {
    let category = if signed {
        is_signed_integer(types, source)
            && is_signed_integer(types, destination)
    } else {
        is_unsigned_integer(types, source)
            && !is_bool(types, source)
            && is_unsigned_integer(types, destination)
            && !is_bool(types, destination)
    };
    category
        && integer_width(types, source)
            .zip(integer_width(types, destination))
            .is_some_and(|(source_width, destination_width)| {
                source_width < destination_width
            })
}

fn validate_integer_truncation(
    types: &[TypeEntry],
    source: TypeId,
    destination: TypeId,
) -> bool {
    is_non_bool_integer(types, source)
        && is_non_bool_integer(types, destination)
        && integer_width(types, source)
            .zip(integer_width(types, destination))
            .is_some_and(|(source_width, destination_width)| {
                source_width > destination_width
            })
}

fn validate_load(
    context: &InstructionContext<'_>,
    pointer: ValueId,
    result_type: TypeId,
    alignment: u8,
) -> Result<(), ValidationError> {
    let pointer_type = context.type_of_use(pointer)?;
    if !valid_alignment(alignment)
        || !is_object_pointer(context.types(), pointer_type)
        || pointee(context.types(), pointer_type) != Some(result_type)
    {
        return Err(ValidationError::OperandType);
    }
    Ok(())
}

fn validate_store(
    context: &InstructionContext<'_>,
    pointer: ValueId,
    value: ValueId,
    alignment: u8,
) -> Result<(), ValidationError> {
    let pointer_type = context.type_of_use(pointer)?;
    let stored_type = context.type_of_use(value)?;
    if !valid_alignment(alignment)
        || !is_object_pointer(context.types(), pointer_type)
        || pointee(context.types(), pointer_type) != Some(stored_type)
    {
        return Err(ValidationError::OperandType);
    }
    Ok(())
}

fn validate_terminator(
    context: &FunctionContext<'_>,
    block: &BasicBlock,
) -> Result<(), ValidationError> {
    let signature = function_signature(
        context.module.types(),
        context.function.signature(),
    )?;
    match block.terminator() {
        Terminator::Branch { condition, .. } => {
            let type_id = require_terminator_use(
                context.flow,
                context.values,
                *condition,
                block.id(),
            )?;
            if !is_bool(context.module.types(), type_id) {
                return Err(ValidationError::ControlType);
            }
        },
        Terminator::Jump { .. } => {},
        Terminator::Return { value } => {
            validate_return(context, block.id(), *value, signature.result)?;
        },
        Terminator::Switch { cases, selector, .. } => {
            validate_switch(context, block.id(), *selector, cases)?;
        },
    }
    Ok(())
}

fn validate_return(
    context: &FunctionContext<'_>,
    block: BlockId,
    value: Option<ValueId>,
    expected: Option<TypeId>,
) -> Result<(), ValidationError> {
    match (value, expected) {
        (None, None) => Ok(()),
        (Some(value_id), Some(expected_type)) => {
            let observed = require_terminator_use(
                context.flow,
                context.values,
                value_id,
                block,
            )?;
            if observed != expected_type {
                return Err(ValidationError::ReturnType);
            }
            Ok(())
        },
        _ => Err(ValidationError::ReturnType),
    }
}

fn validate_switch(
    context: &FunctionContext<'_>,
    block: BlockId,
    selector: ValueId,
    cases: &[SwitchCase],
) -> Result<(), ValidationError> {
    let selector_type =
        require_terminator_use(context.flow, context.values, selector, block)?;
    if !is_integer(context.module.types(), selector_type)
        || requires_integer_promotion(context.module.types(), selector_type)
    {
        return Err(ValidationError::ControlType);
    }
    let mut identities = BTreeSet::new();
    for case in cases {
        validate_integer_constant(
            context.module.types(),
            selector_type,
            case.constant(),
        )?;
        let identity = (
            case.constant().bit_width(),
            case.constant().little_endian().to_vec(),
        );
        if !identities.insert(identity) {
            return Err(ValidationError::ControlType);
        }
    }
    Ok(())
}
