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
//   - Canonical malbolge-c32-v1 object size/alignment admission for typed IR.
// - Must-Not:
//   - Use host layout, native pointer size, or silently accept recursive
//     objects.
// - Allows:
//   - Inputs: closed typed-IR object definitions.
//   - Outputs: exact finite ABI size/alignment or stable type-table failure.
//   - Side effects: temporary dependency stack and layout-cache allocation.
// - Split-When:
//   - Another ABI version requires independently versioned layout policy.
// - Merge-When:
//   - Type-table admission directly owns all object-layout semantics.
// - Summary:
//   - Computes finite canonical object layout without host representation
//     leakage.
// - Description:
//   - Pointer layout terminates dependency traversal; by-value aggregate
//     cycles fail closed without host-stack recursion.
// - Usage:
//   - Used by type-table and initialized-global admission.
// - Defaults:
//   - Size overflow beyond the 32-bit logical address domain is rejected.
//

//! Canonical object layout for the deterministic guest C ABI.

use super::error::ValidationError;
use super::ids::TypeId;
use super::type_validation::{definition, is_object_type};
use super::types::{TypeDef, TypeEntry};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct ObjectLayout {
    pub(super) alignment: u8,
    pub(super) size: u32,
}

struct LayoutState<'types> {
    active: Vec<bool>,
    complete: Vec<Option<ObjectLayout>>,
    types: &'types [TypeEntry],
}

#[derive(Clone, Copy)]
struct PendingType {
    id: TypeId,
    next_child: usize,
}

impl<'types> LayoutState<'types> {
    fn new(types: &'types [TypeEntry]) -> Self {
        Self {
            active: vec![false; types.len()],
            complete: vec![None; types.len()],
            types,
        }
    }

    // An explicit DFS stack avoids relying on the host call stack for type
    // graphs carried by untrusted checkpoints. Successful subtrees are cached
    // across every root in the same type table.
    fn resolve(&mut self, root: TypeId) -> Result<ObjectLayout, ValidationError> {
        let root_index = layout_index(self.types, root)?;
        if let Some(known) = self.complete.get(root_index).copied().flatten() {
            return Ok(known);
        }
        let mut pending = vec![PendingType {
            id: root,
            next_child: 0,
        }];
        *self
            .active
            .get_mut(root_index)
            .ok_or(ValidationError::TypeTable)? = true;
        while let Some(frame) = pending.last_mut() {
            let index = layout_index(self.types, frame.id)?;
            let kind = definition(self.types, frame.id)?;
            if let Some(child) = layout_child(kind, frame.next_child) {
                frame.next_child = frame
                    .next_child
                    .checked_add(1)
                    .ok_or(ValidationError::TypeTable)?;
                self.schedule_child(&mut pending, child)?;
                continue;
            }
            let value = complete_layout(self.types, &self.complete, kind)?;
            *self
                .complete
                .get_mut(index)
                .ok_or(ValidationError::TypeTable)? = Some(value);
            *self
                .active
                .get_mut(index)
                .ok_or(ValidationError::TypeTable)? = false;
            _ = pending.pop();
        }
        self.complete
            .get(root_index)
            .copied()
            .flatten()
            .ok_or(ValidationError::TypeTable)
    }

    fn schedule_child(
        &mut self,
        pending: &mut Vec<PendingType>,
        child: TypeId,
    ) -> Result<(), ValidationError> {
        let child_index = layout_index(self.types, child)?;
        if self.complete.get(child_index).is_some_and(Option::is_some) {
            return Ok(());
        }
        if self
            .active
            .get(child_index)
            .copied()
            .ok_or(ValidationError::TypeTable)?
        {
            return Err(ValidationError::TypeTable);
        }
        *self
            .active
            .get_mut(child_index)
            .ok_or(ValidationError::TypeTable)? = true;
        pending.push(PendingType {
            id: child,
            next_child: 0,
        });
        Ok(())
    }
}

pub(super) fn object_layout(
    types: &[TypeEntry],
    type_id: TypeId,
) -> Result<ObjectLayout, ValidationError> {
    LayoutState::new(types).resolve(type_id)
}

pub(super) fn validate_object_layouts(types: &[TypeEntry]) -> Result<(), ValidationError> {
    let mut state = LayoutState::new(types);
    for entry in types {
        if is_object_type(types, entry.id()) {
            _ = state.resolve(entry.id())?;
        }
    }
    Ok(())
}

fn layout_index(types: &[TypeEntry], type_id: TypeId) -> Result<usize, ValidationError> {
    let index = usize::try_from(type_id.value()).map_err(|_error| ValidationError::TypeTable)?;
    _ = definition(types, type_id)?;
    Ok(index)
}

fn layout_child(kind: &TypeDef, index: usize) -> Option<TypeId> {
    match kind {
        TypeDef::Array { element, .. } if index == 0 => Some(*element),
        TypeDef::Struct { fields } => fields.get(index).copied(),
        TypeDef::Union { members } => members.get(index).copied(),
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
        | TypeDef::Pointer { .. }
        | TypeDef::U16
        | TypeDef::U32
        | TypeDef::U64
        | TypeDef::U8
        | TypeDef::Void => None,
    }
}

fn resolved_child(
    types: &[TypeEntry],
    complete: &[Option<ObjectLayout>],
    child: TypeId,
) -> Result<ObjectLayout, ValidationError> {
    let index = layout_index(types, child)?;
    complete
        .get(index)
        .copied()
        .flatten()
        .ok_or(ValidationError::TypeTable)
}

fn complete_layout(
    types: &[TypeEntry],
    complete: &[Option<ObjectLayout>],
    kind: &TypeDef,
) -> Result<ObjectLayout, ValidationError> {
    match kind {
        TypeDef::Array { count, element } => {
            let inner = resolved_child(types, complete, *element)?;
            let stride = align_up(inner.size, inner.alignment)?;
            let size = stride
                .checked_mul(*count)
                .ok_or(ValidationError::TypeTable)?;
            Ok(layout(size, inner.alignment))
        }
        TypeDef::Bool | TypeDef::Char | TypeDef::I8 | TypeDef::U8 => Ok(layout(1, 1)),
        TypeDef::F128 => Ok(layout(16, 16)),
        TypeDef::F32 | TypeDef::I32 | TypeDef::Pointer { .. } | TypeDef::U32 => Ok(layout(4, 4)),
        TypeDef::F64 | TypeDef::I64 | TypeDef::U64 => Ok(layout(8, 8)),
        TypeDef::I16 | TypeDef::U16 => Ok(layout(2, 2)),
        TypeDef::Struct { fields } => {
            let mut offset = 0u32;
            let mut alignment = 1u8;
            for field in fields {
                let inner = resolved_child(types, complete, *field)?;
                offset = align_up(offset, inner.alignment)?;
                offset = offset
                    .checked_add(inner.size)
                    .ok_or(ValidationError::TypeTable)?;
                alignment = alignment.max(inner.alignment);
            }
            Ok(layout(align_up(offset, alignment)?, alignment))
        }
        TypeDef::Union { members } => {
            let mut size = 0u32;
            let mut alignment = 1u8;
            for member in members {
                let inner = resolved_child(types, complete, *member)?;
                size = size.max(inner.size);
                alignment = alignment.max(inner.alignment);
            }
            Ok(layout(align_up(size, alignment)?, alignment))
        }
        TypeDef::Function { .. } | TypeDef::Void => Err(ValidationError::TypeTable),
    }
}

fn align_up(value: u32, alignment: u8) -> Result<u32, ValidationError> {
    let alignment_value = u32::from(alignment);
    let mask = alignment_value
        .checked_sub(1)
        .ok_or(ValidationError::TypeTable)?;
    let biased = value.checked_add(mask).ok_or(ValidationError::TypeTable)?;
    Ok(biased & !mask)
}

const fn layout(size: u32, alignment: u8) -> ObjectLayout {
    ObjectLayout { alignment, size }
}
