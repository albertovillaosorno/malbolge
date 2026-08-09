// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Closed version-one portable type vocabulary for typed compiler IR.
// - Must-Not:
//   - Inherit LLVM type identity, native layout strings, or host pointer width.
// - Allows:
//   - Inputs: ABI-normalized scalar and aggregate/function type relationships.
//   - Outputs: explicit version-one type definitions and dense table entries.
//   - Side effects: none.
// - Split-When:
//   - A new type family requires independent versioning or proof semantics.
// - Merge-When:
//   - Type identity and other IR values no longer have separate policy.
// - Summary:
//   - Defines portable type-table entries bound to malbolge-c32-v1 semantics.
// - Description:
//   - Type IDs are explicit; referenced IDs are admitted by application policy.
// - Usage:
//   - Consumed by instructions, functions, globals, validation, and encoding.
// - Defaults:
//   - No opaque/native/vector type exists in version one.
//

//! Closed portable type vocabulary for typed compiler IR version one.

use super::ids::TypeId;

/// One explicit type-table entry.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TypeEntry {
    definition: TypeDef,
    id: TypeId,
}

impl TypeEntry {
    /// Returns the portable type definition.
    #[must_use]
    pub const fn definition(&self) -> &TypeDef {
        &self.definition
    }

    /// Returns the explicit type-table ID.
    #[must_use]
    pub const fn id(&self) -> TypeId {
        self.id
    }

    /// Creates one explicit type-table entry.
    #[must_use]
    pub const fn new(id: TypeId, definition: TypeDef) -> Self {
        Self { definition, id }
    }
}

/// Closed version-one portable type grammar.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum TypeDef {
    /// Fixed-size array of one element type.
    Array {
        /// Number of elements.
        count: u32,
        /// Element type.
        element: TypeId,
    },
    /// C boolean representation.
    Bool,
    /// C plain `char` representation.
    Char,
    /// IEEE-style binary128 representation.
    F128,
    /// IEEE-style binary32 representation.
    F32,
    /// IEEE-style binary64 representation.
    F64,
    /// Portable function signature.
    Function {
        /// Ordered parameter types.
        parameters: Vec<TypeId>,
        /// Optional result type; `None` means `void`.
        result: Option<TypeId>,
        /// Whether trailing default-promoted arguments are admitted.
        variadic: bool,
    },
    /// Signed 16-bit integer.
    I16,
    /// Signed 32-bit integer.
    I32,
    /// Signed 64-bit integer.
    I64,
    /// Signed 8-bit integer.
    I8,
    /// Guest pointer in the object/void or function namespace.
    Pointer {
        /// Pointee type.
        pointee: TypeId,
    },
    /// Ordered structure fields.
    Struct {
        /// Field types in source order.
        fields: Vec<TypeId>,
    },
    /// Unsigned 16-bit integer.
    U16,
    /// Unsigned 32-bit integer.
    U32,
    /// Unsigned 64-bit integer.
    U64,
    /// Unsigned 8-bit integer.
    U8,
    /// Union member alternatives.
    Union {
        /// Member types in source order.
        members: Vec<TypeId>,
    },
    /// No value.
    Void,
}

impl TypeDef {
    /// Creates a fixed-size array definition.
    #[must_use]
    pub const fn array(element: TypeId, count: u32) -> Self {
        Self::Array { count, element }
    }

    /// Creates a portable function-signature definition.
    #[must_use]
    pub const fn function(
        parameters: Vec<TypeId>,
        result: Option<TypeId>,
        variadic: bool,
    ) -> Self {
        Self::Function {
            parameters,
            result,
            variadic,
        }
    }

    /// Creates a guest object-pointer definition.
    #[must_use]
    pub const fn pointer(pointee: TypeId) -> Self {
        Self::Pointer { pointee }
    }

    /// Creates an ordered structure definition.
    #[must_use]
    pub const fn structure(fields: Vec<TypeId>) -> Self {
        Self::Struct { fields }
    }

    /// Creates an ordered union definition.
    #[must_use]
    pub const fn union(members: Vec<TypeId>) -> Self {
        Self::Union { members }
    }
}
