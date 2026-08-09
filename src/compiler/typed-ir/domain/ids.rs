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
//   - Explicit numeric identities used by the portable typed compiler IR.
// - Must-Not:
//   - Derive identity from addresses, hashes, container iteration, or Rust
//     layout.
// - Allows:
//   - Inputs: canonical unsigned 32-bit IDs assigned by compiler traversal.
//   - Outputs: strongly separated type, function, block, global, and value IDs.
//   - Side effects: none.
// - Split-When:
//   - An identity namespace gains independent allocation/versioning rules.
// - Merge-When:
//   - The IR no longer benefits from type-safe namespace separation.
// - Summary:
//   - Defines dense explicit numeric identity namespaces for typed IR.
// - Description:
//   - All IDs are portable u32 values; density is checked by admission.
// - Usage:
//   - Shared by typed-IR domain, validation, encoding, and tests.
// - Defaults:
//   - Zero is an ordinary first ID, never an implicit null sentinel.
//

//! Portable numeric identity namespaces for typed compiler IR.

/// Stable basic-block identity local to one function.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct BlockId(u32);

impl BlockId {
    /// Creates an explicit portable block identity.
    #[must_use]
    pub const fn new(value: u32) -> Self {
        Self(value)
    }

    /// Returns the canonical unsigned numeric identity.
    #[must_use]
    pub const fn value(self) -> u32 {
        self.0
    }
}

/// Stable function identity local to one module.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct FunctionId(u32);

impl FunctionId {
    /// Creates an explicit portable function identity.
    #[must_use]
    pub const fn new(value: u32) -> Self {
        Self(value)
    }

    /// Returns the canonical unsigned numeric identity.
    #[must_use]
    pub const fn value(self) -> u32 {
        self.0
    }
}

/// Stable global-object identity local to one module.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct GlobalId(u32);

impl GlobalId {
    /// Creates an explicit portable global identity.
    #[must_use]
    pub const fn new(value: u32) -> Self {
        Self(value)
    }

    /// Returns the canonical unsigned numeric identity.
    #[must_use]
    pub const fn value(self) -> u32 {
        self.0
    }
}

/// Stable canonical type-table identity local to one module.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct TypeId(u32);

impl TypeId {
    /// Creates an explicit portable type identity.
    #[must_use]
    pub const fn new(value: u32) -> Self {
        Self(value)
    }

    /// Returns the canonical unsigned numeric identity.
    #[must_use]
    pub const fn value(self) -> u32 {
        self.0
    }
}

/// Stable SSA value identity local to one function.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct ValueId(u32);

impl ValueId {
    /// Creates an explicit portable SSA value identity.
    #[must_use]
    pub const fn new(value: u32) -> Self {
        Self(value)
    }

    /// Returns the canonical unsigned numeric identity.
    #[must_use]
    pub const fn value(self) -> u32 {
        self.0
    }
}
