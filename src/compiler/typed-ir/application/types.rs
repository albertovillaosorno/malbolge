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
//   - Typed-IR type-table admission and scalar category queries.
// - Must-Not:
//   - Compute native layout, infer C typedef spelling, or lower aggregate
//     storage.
// - Allows:
//   - Inputs: explicit type entries and referenced type IDs.
//   - Outputs: validated references plus portable scalar/pointer
//     classifications.
//   - Side effects: none.
// - Split-When:
//   - Aggregate ABI layout becomes an independently owned compiler pass.
// - Merge-When:
//   - Instruction admission owns all type-table policy directly.
// - Summary:
//   - Validates dense type IDs and closed version-one type references.
// - Description:
//   - Forward/cyclic references through pointers are admitted
//     deterministically.
// - Usage:
//   - Shared by module, instruction, CFG, and proof validation.
// - Defaults:
//   - Missing IDs and zero-length fixed aggregates fail closed.
//

//! Type-table validation and portable type-category queries.

use super::error::ValidationError;
use super::ids::TypeId;
use super::types::{TypeDef, TypeEntry};

pub(super) struct FunctionSignature<'types> {
    pub(super) parameters: &'types [TypeId],
    pub(super) result: Option<TypeId>,
    pub(super) variadic: bool,
}

pub(super) fn definition(
    types: &[TypeEntry],
    type_id: TypeId,
) -> Result<&TypeDef, ValidationError> {
    let index = usize::try_from(type_id.value())
        .map_err(|_error| ValidationError::TypeTable)?;
    let entry = types.get(index).ok_or(ValidationError::TypeTable)?;
    if entry.id() != type_id {
        return Err(ValidationError::TypeTable);
    }
    Ok(entry.definition())
}

pub(super) fn float_width(types: &[TypeEntry], type_id: TypeId) -> Option<u16> {
    match definition(types, type_id).ok()? {
        TypeDef::F128 => Some(128),
        TypeDef::F32 => Some(32),
        TypeDef::F64 => Some(64),
        TypeDef::Array { .. }
        | TypeDef::Bool
        | TypeDef::Char
        | TypeDef::Function { .. }
        | TypeDef::I16
        | TypeDef::I32
        | TypeDef::I64
        | TypeDef::I8
        | TypeDef::Pointer { .. }
        | TypeDef::Struct { .. }
        | TypeDef::U16
        | TypeDef::U32
        | TypeDef::U64
        | TypeDef::U8
        | TypeDef::Union { .. }
        | TypeDef::Void => None,
    }
}

pub(super) fn function_signature(
    types: &[TypeEntry],
    type_id: TypeId,
) -> Result<FunctionSignature<'_>, ValidationError> {
    match definition(types, type_id)? {
        TypeDef::Function {
            parameters,
            result,
            variadic,
        } => Ok(FunctionSignature {
            parameters,
            result: *result,
            variadic: *variadic,
        }),
        TypeDef::Array { .. }
        | TypeDef::Bool
        | TypeDef::Char
        | TypeDef::F128
        | TypeDef::F32
        | TypeDef::F64
        | TypeDef::I16
        | TypeDef::I32
        | TypeDef::I64
        | TypeDef::I8
        | TypeDef::Pointer { .. }
        | TypeDef::Struct { .. }
        | TypeDef::U16
        | TypeDef::U32
        | TypeDef::U64
        | TypeDef::U8
        | TypeDef::Union { .. }
        | TypeDef::Void => Err(ValidationError::FunctionIdentity),
    }
}

pub(super) fn integer_width(
    types: &[TypeEntry],
    type_id: TypeId,
) -> Option<u16> {
    match definition(types, type_id).ok()? {
        TypeDef::Bool => Some(1),
        TypeDef::Char | TypeDef::I8 | TypeDef::U8 => Some(8),
        TypeDef::I16 | TypeDef::U16 => Some(16),
        TypeDef::I32 | TypeDef::U32 => Some(32),
        TypeDef::I64 | TypeDef::U64 => Some(64),
        TypeDef::Array { .. }
        | TypeDef::F128
        | TypeDef::F32
        | TypeDef::F64
        | TypeDef::Function { .. }
        | TypeDef::Pointer { .. }
        | TypeDef::Struct { .. }
        | TypeDef::Union { .. }
        | TypeDef::Void => None,
    }
}

pub(super) fn is_bool(types: &[TypeEntry], type_id: TypeId) -> bool {
    matches!(definition(types, type_id), Ok(TypeDef::Bool))
}

pub(super) fn is_float(types: &[TypeEntry], type_id: TypeId) -> bool {
    matches!(
        definition(types, type_id),
        Ok(TypeDef::F32 | TypeDef::F64 | TypeDef::F128)
    )
}

pub(super) fn is_integer(types: &[TypeEntry], type_id: TypeId) -> bool {
    integer_width(types, type_id).is_some()
}

pub(super) fn requires_integer_promotion(
    types: &[TypeEntry],
    type_id: TypeId,
) -> bool {
    matches!(
        definition(types, type_id),
        Ok(TypeDef::Bool
            | TypeDef::Char
            | TypeDef::I8
            | TypeDef::I16
            | TypeDef::U8
            | TypeDef::U16)
    )
}

pub(super) fn is_function_pointer(
    types: &[TypeEntry],
    type_id: TypeId,
) -> bool {
    pointee(types, type_id).is_some_and(|pointee_type| {
        matches!(
            definition(types, pointee_type),
            Ok(TypeDef::Function { .. })
        )
    })
}

pub(super) fn is_non_bool_integer(
    types: &[TypeEntry],
    type_id: TypeId,
) -> bool {
    is_integer(types, type_id) && !is_bool(types, type_id)
}

pub(super) fn is_object_pointer(types: &[TypeEntry], type_id: TypeId) -> bool {
    pointee(types, type_id).is_some_and(|pointee_type| {
        is_object_type(types, pointee_type)
            || matches!(definition(types, pointee_type), Ok(TypeDef::Void))
    })
}

pub(super) fn is_signed_integer(types: &[TypeEntry], type_id: TypeId) -> bool {
    matches!(
        definition(types, type_id),
        Ok(TypeDef::Char
            | TypeDef::I8
            | TypeDef::I16
            | TypeDef::I32
            | TypeDef::I64)
    )
}

pub(super) fn is_unsigned_integer(
    types: &[TypeEntry],
    type_id: TypeId,
) -> bool {
    matches!(
        definition(types, type_id),
        Ok(TypeDef::Bool
            | TypeDef::U8
            | TypeDef::U16
            | TypeDef::U32
            | TypeDef::U64)
    )
}

pub(super) fn pointee(types: &[TypeEntry], type_id: TypeId) -> Option<TypeId> {
    match definition(types, type_id).ok()? {
        TypeDef::Pointer { pointee } => Some(*pointee),
        TypeDef::Array { .. }
        | TypeDef::Bool
        | TypeDef::Char
        | TypeDef::F128
        | TypeDef::F32
        | TypeDef::F64
        | TypeDef::Function { .. }
        | TypeDef::I16
        | TypeDef::I32
        | TypeDef::I64
        | TypeDef::I8
        | TypeDef::Struct { .. }
        | TypeDef::U16
        | TypeDef::U32
        | TypeDef::U64
        | TypeDef::U8
        | TypeDef::Union { .. }
        | TypeDef::Void => None,
    }
}

pub(super) fn validate_type_table(
    types: &[TypeEntry],
) -> Result<(), ValidationError> {
    if types.is_empty() {
        return Err(ValidationError::TypeTable);
    }
    for (index, entry) in types.iter().enumerate() {
        let expected = u32::try_from(index)
            .map_err(|_error| ValidationError::TypeTable)?;
        if entry.id().value() != expected {
            return Err(ValidationError::TypeTable);
        }
        validate_definition(types, entry.definition())?;
    }
    Ok(())
}

pub(super) fn is_object_type(types: &[TypeEntry], type_id: TypeId) -> bool {
    matches!(
        definition(types, type_id),
        Ok(TypeDef::Array { .. }
            | TypeDef::Bool
            | TypeDef::Char
            | TypeDef::F32
            | TypeDef::F64
            | TypeDef::F128
            | TypeDef::I8
            | TypeDef::I16
            | TypeDef::I32
            | TypeDef::I64
            | TypeDef::Pointer { .. }
            | TypeDef::Struct { .. }
            | TypeDef::U8
            | TypeDef::U16
            | TypeDef::U32
            | TypeDef::U64
            | TypeDef::Union { .. })
    )
}

pub(super) fn is_function_value_type(
    types: &[TypeEntry],
    type_id: TypeId,
) -> bool {
    is_object_type(types, type_id)
        && !matches!(definition(types, type_id), Ok(TypeDef::Array { .. }))
}

fn validate_definition(
    types: &[TypeEntry],
    definition_value: &TypeDef,
) -> Result<(), ValidationError> {
    match definition_value {
        TypeDef::Array { count, element } => {
            if *count == 0 || !is_object_type(types, *element) {
                return Err(ValidationError::TypeTable);
            }
        },
        TypeDef::Function { parameters, result, .. } => {
            if parameters
                .iter()
                .any(|type_id| !is_function_value_type(types, *type_id))
            {
                return Err(ValidationError::TypeTable);
            }
            if result
                .is_some_and(|type_id| !is_function_value_type(types, type_id))
            {
                return Err(ValidationError::TypeTable);
            }
        },
        TypeDef::Pointer { pointee } => {
            _ = definition(types, *pointee)?;
        },
        TypeDef::Struct { fields } => validate_members(types, fields)?,
        TypeDef::Union { members } => validate_members(types, members)?,
        TypeDef::Bool
        | TypeDef::Char
        | TypeDef::F128
        | TypeDef::F32
        | TypeDef::F64
        | TypeDef::I16
        | TypeDef::I32
        | TypeDef::I64
        | TypeDef::I8
        | TypeDef::U16
        | TypeDef::U32
        | TypeDef::U64
        | TypeDef::U8
        | TypeDef::Void => {},
    }
    Ok(())
}

fn validate_members(
    types: &[TypeEntry],
    members: &[TypeId],
) -> Result<(), ValidationError> {
    if members.is_empty()
        || members
            .iter()
            .any(|type_id| !is_object_type(types, *type_id))
    {
        return Err(ValidationError::TypeTable);
    }
    Ok(())
}
