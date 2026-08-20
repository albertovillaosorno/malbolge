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
//   - Canonical malbolge-c32-v1 object size/alignment admission for typed IR.
// - Must-Not:
//   - Use host layout, native pointer size, or silently accept recursive
//     objects.
// - Allows:
//   - Inputs: closed typed-IR object definitions.
//   - Outputs: exact finite ABI size/alignment or stable type-table failure.
//   - Side effects: temporary cycle-detection set allocation only.
// - Split-When:
//   - Another ABI version requires independently versioned layout policy.
// - Merge-When:
//   - Type-table admission directly owns all object-layout semantics.
// - Summary:
//   - Computes finite canonical object layout without host representation
//     leakage.
// - Description:
//   - Pointer layout terminates recursion; by-value aggregate cycles fail
//     closed.
// - Usage:
//   - Used by type-table and initialized-global admission.
// - Defaults:
//   - Size overflow beyond the 32-bit logical address domain is rejected.
//

//! Canonical object layout for the deterministic guest C ABI.

use std::collections::BTreeSet;

use super::error::ValidationError;
use super::ids::TypeId;
use super::type_validation::{definition, is_object_type};
use super::types::{TypeDef, TypeEntry};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct ObjectLayout {
    pub(super) alignment: u8,
    pub(super) size: u32,
}

pub(super) fn object_layout(
    types: &[TypeEntry],
    type_id: TypeId,
) -> Result<ObjectLayout, ValidationError> {
    let mut visiting = BTreeSet::new();
    layout_type(types, type_id, &mut visiting)
}

pub(super) fn validate_object_layouts(
    types: &[TypeEntry],
) -> Result<(), ValidationError> {
    for entry in types {
        if is_object_type(types, entry.id()) {
            _ = object_layout(types, entry.id())?;
        }
    }
    Ok(())
}

fn align_up(value: u32, alignment: u8) -> Result<u32, ValidationError> {
    let alignment_value = u32::from(alignment);
    let mask = alignment_value
        .checked_sub(1)
        .ok_or(ValidationError::TypeTable)?;
    let biased = value.checked_add(mask).ok_or(ValidationError::TypeTable)?;
    Ok(biased & !mask)
}

fn layout_type(
    types: &[TypeEntry],
    type_id: TypeId,
    visiting: &mut BTreeSet<TypeId>,
) -> Result<ObjectLayout, ValidationError> {
    if !visiting.insert(type_id) {
        return Err(ValidationError::TypeTable);
    }
    let result = match definition(types, type_id)? {
        TypeDef::Array { count, element } => {
            layout_array(types, *element, *count, visiting)
        },
        TypeDef::Bool | TypeDef::Char | TypeDef::I8 | TypeDef::U8 => {
            Ok(layout(1, 1))
        },
        TypeDef::F128 => Ok(layout(16, 16)),
        TypeDef::F32
        | TypeDef::I32
        | TypeDef::Pointer { .. }
        | TypeDef::U32 => Ok(layout(4, 4)),
        TypeDef::F64 | TypeDef::I64 | TypeDef::U64 => Ok(layout(8, 8)),
        TypeDef::I16 | TypeDef::U16 => Ok(layout(2, 2)),
        TypeDef::Struct { fields } => layout_struct(types, fields, visiting),
        TypeDef::Union { members } => layout_union(types, members, visiting),
        TypeDef::Function { .. } | TypeDef::Void => {
            Err(ValidationError::TypeTable)
        },
    };
    _ = visiting.remove(&type_id);
    result
}

const fn layout(size: u32, alignment: u8) -> ObjectLayout {
    ObjectLayout { alignment, size }
}

fn layout_array(
    types: &[TypeEntry],
    element: TypeId,
    count: u32,
    visiting: &mut BTreeSet<TypeId>,
) -> Result<ObjectLayout, ValidationError> {
    let element_layout = layout_type(types, element, visiting)?;
    let stride = align_up(element_layout.size, element_layout.alignment)?;
    let size = stride
        .checked_mul(count)
        .ok_or(ValidationError::TypeTable)?;
    Ok(layout(size, element_layout.alignment))
}

fn layout_struct(
    types: &[TypeEntry],
    fields: &[TypeId],
    visiting: &mut BTreeSet<TypeId>,
) -> Result<ObjectLayout, ValidationError> {
    let mut offset = 0u32;
    let mut alignment = 1u8;
    for field in fields {
        let field_layout = layout_type(types, *field, visiting)?;
        offset = align_up(offset, field_layout.alignment)?;
        offset = offset
            .checked_add(field_layout.size)
            .ok_or(ValidationError::TypeTable)?;
        alignment = alignment.max(field_layout.alignment);
    }
    Ok(layout(align_up(offset, alignment)?, alignment))
}

fn layout_union(
    types: &[TypeEntry],
    members: &[TypeId],
    visiting: &mut BTreeSet<TypeId>,
) -> Result<ObjectLayout, ValidationError> {
    let mut size = 0u32;
    let mut alignment = 1u8;
    for member in members {
        let member_layout = layout_type(types, *member, visiting)?;
        size = size.max(member_layout.size);
        alignment = alignment.max(member_layout.alignment);
    }
    Ok(layout(align_up(size, alignment)?, alignment))
}
