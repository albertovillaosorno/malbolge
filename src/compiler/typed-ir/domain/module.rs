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
//   - Versioned typed-IR module, function, global, parameter, and proof values.
// - Must-Not:
//   - Parse C, infer missing CFG/type facts, or encode target Malbolge layout.
// - Allows:
//   - Inputs: explicit normalized provenance and closed typed-IR domain values.
//   - Outputs: immutable portable compiler-stage modules.
//   - Side effects: owned allocation only.
// - Split-When:
//   - Global linking or proof discharge gains independent artifact lifecycle.
// - Merge-When:
//   - Module-level identity and lower-level IR values share one policy owner.
// - Summary:
//   - Aggregates the closed version-one typed IR into one portable module.
// - Description:
//   - Construction permits values before application admission.
// - Usage:
//   - Produced by future frontend lowering and consumed by later compiler
//     stages.
// - Defaults:
//   - Exact ABI/profile/source identity is carried in every module.
//

//! Versioned portable typed compiler IR module values.

use super::control::BasicBlock;
use super::ids::{BlockId, FunctionId, GlobalId, TypeId, ValueId};
use super::source::SourceSpan;
use super::types::TypeEntry;

/// Current portable typed compiler IR schema version.
pub const TYPED_IR_VERSION: u16 = 1;

/// One function parameter and its entry SSA value.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Parameter {
    type_id: TypeId,
    value: ValueId,
}

impl Parameter {
    /// Creates one typed function parameter.
    #[must_use]
    pub const fn new(value: ValueId, type_id: TypeId) -> Self {
        Self { type_id, value }
    }

    /// Returns the parameter type.
    #[must_use]
    pub const fn type_id(self) -> TypeId {
        self.type_id
    }

    /// Returns the entry SSA value identity.
    #[must_use]
    pub const fn value(self) -> ValueId {
        self.value
    }
}

/// Construction payload for one untrusted typed function.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FunctionSpec {
    /// Ordered basic blocks.
    pub blocks: Vec<BasicBlock>,
    /// Entry block identity.
    pub entry: BlockId,
    /// Module-local function identity.
    pub id: FunctionId,
    /// Portable semantic function name.
    pub name: String,
    /// Ordered entry SSA parameters.
    pub parameters: Vec<Parameter>,
    /// Function-signature type ID.
    pub signature: TypeId,
    /// Complete normalized source provenance.
    pub span: SourceSpan,
}

/// One module-local typed function.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Function {
    blocks: Vec<BasicBlock>,
    entry: BlockId,
    id: FunctionId,
    name: String,
    parameters: Vec<Parameter>,
    signature: TypeId,
    span: SourceSpan,
}

impl Function {
    /// Returns ordered basic blocks.
    #[must_use]
    pub fn blocks(&self) -> &[BasicBlock] {
        &self.blocks
    }

    /// Returns the entry block identity.
    #[must_use]
    pub const fn entry(&self) -> BlockId {
        self.entry
    }

    /// Returns the module-local function identity.
    #[must_use]
    pub const fn id(&self) -> FunctionId {
        self.id
    }

    /// Returns the portable semantic function name.
    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Creates one typed function from an untrusted construction payload.
    #[must_use]
    pub fn new(spec: FunctionSpec) -> Self {
        Self {
            blocks: spec.blocks,
            entry: spec.entry,
            id: spec.id,
            name: spec.name,
            parameters: spec.parameters,
            signature: spec.signature,
            span: spec.span,
        }
    }

    /// Returns ordered parameter values.
    #[must_use]
    pub fn parameters(&self) -> &[Parameter] {
        &self.parameters
    }

    /// Returns the function-signature type ID.
    #[must_use]
    pub const fn signature(&self) -> TypeId {
        self.signature
    }

    /// Returns normalized source provenance.
    #[must_use]
    pub const fn span(&self) -> SourceSpan {
        self.span
    }
}

/// Construction payload for one untrusted global object.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GlobalSpec {
    /// Module-local global identity.
    pub id: GlobalId,
    /// Exact initialized object bytes when present.
    pub initializer: Option<Vec<u8>>,
    /// Portable semantic global name.
    pub name: String,
    /// Complete normalized source provenance.
    pub span: SourceSpan,
    /// Global object type.
    pub type_id: TypeId,
}

/// One module-local static global object.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Global {
    id: GlobalId,
    initializer: Option<Vec<u8>>,
    name: String,
    span: SourceSpan,
    type_id: TypeId,
}

impl Global {
    /// Returns the global identity.
    #[must_use]
    pub const fn id(&self) -> GlobalId {
        self.id
    }

    /// Returns exact initialized object bytes when present.
    #[must_use]
    pub fn initializer(&self) -> Option<&[u8]> {
        self.initializer.as_deref()
    }

    /// Returns the portable semantic global name.
    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Creates one global object from an untrusted construction payload.
    #[must_use]
    pub fn new(spec: GlobalSpec) -> Self {
        Self {
            id: spec.id,
            initializer: spec.initializer,
            name: spec.name,
            span: spec.span,
            type_id: spec.type_id,
        }
    }

    /// Returns normalized source provenance.
    #[must_use]
    pub const fn span(&self) -> SourceSpan {
        self.span
    }

    /// Returns the global object type.
    #[must_use]
    pub const fn type_id(&self) -> TypeId {
        self.type_id
    }
}

/// One verifier-visible obligation retained by typed compiler IR.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ProofObligation {
    /// Pointer must satisfy a power-of-two alignment.
    Aligned {
        /// Required alignment in bytes.
        alignment: u8,
        /// Owning function identity.
        function: FunctionId,
        /// Pointer SSA value.
        pointer: ValueId,
    },
    /// Pointer range must remain inside one live guest object.
    InBounds {
        /// Required byte extent.
        bytes: u32,
        /// Owning function identity.
        function: FunctionId,
        /// Pointer SSA value.
        pointer: ValueId,
    },
    /// Signed arithmetic result must not overflow its type.
    NoSignedOverflow {
        /// Owning function identity.
        function: FunctionId,
        /// SSA result carrying the obligation.
        result: ValueId,
    },
    /// Scalar must be nonzero at its semantic use.
    Nonzero {
        /// Owning function identity.
        function: FunctionId,
        /// Required nonzero SSA value.
        value: ValueId,
    },
    /// Module requires one target-profile semantic capability.
    ProfileCapability {
        /// Stable capability identity.
        capability: String,
    },
}

/// Construction payload for one untrusted typed compiler IR module.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ModuleSpec {
    /// Deterministic guest ABI identity.
    pub abi_id: String,
    /// Portable typed-IR schema version.
    pub format_version: u16,
    /// Ordered module-local functions.
    pub functions: Vec<Function>,
    /// Ordered static global objects.
    pub globals: Vec<Global>,
    /// Ordered verifier-visible proof obligations.
    pub proof_obligations: Vec<ProofObligation>,
    /// Portable logical source identity.
    pub source_id: String,
    /// Exact normalized-source SHA-256 bytes.
    pub source_sha256: [u8; 32],
    /// Canonical target-profile identity.
    pub target_profile: String,
    /// Ordered explicit type-table entries.
    pub types: Vec<TypeEntry>,
}

/// One complete versioned typed compiler IR module.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Module {
    abi_id: String,
    format_version: u16,
    functions: Vec<Function>,
    globals: Vec<Global>,
    proof_obligations: Vec<ProofObligation>,
    source_id: String,
    source_sha256: [u8; 32],
    target_profile: String,
    types: Vec<TypeEntry>,
}

impl Module {
    /// Returns the deterministic guest ABI identity.
    #[must_use]
    pub fn abi_id(&self) -> &str {
        &self.abi_id
    }

    /// Returns the typed-IR schema version.
    #[must_use]
    pub const fn format_version(&self) -> u16 {
        self.format_version
    }

    /// Returns ordered module-local functions.
    #[must_use]
    pub fn functions(&self) -> &[Function] {
        &self.functions
    }

    /// Returns ordered static global objects.
    #[must_use]
    pub fn globals(&self) -> &[Global] {
        &self.globals
    }

    /// Creates one typed module from an untrusted construction payload.
    #[must_use]
    pub fn new(spec: ModuleSpec) -> Self {
        Self {
            abi_id: spec.abi_id,
            format_version: spec.format_version,
            functions: spec.functions,
            globals: spec.globals,
            proof_obligations: spec.proof_obligations,
            source_id: spec.source_id,
            source_sha256: spec.source_sha256,
            target_profile: spec.target_profile,
            types: spec.types,
        }
    }

    /// Returns ordered verifier-visible proof obligations.
    #[must_use]
    pub fn proof_obligations(&self) -> &[ProofObligation] {
        &self.proof_obligations
    }

    /// Returns the portable logical source identity.
    #[must_use]
    pub fn source_id(&self) -> &str {
        &self.source_id
    }

    /// Returns exact normalized-source SHA-256 bytes.
    #[must_use]
    pub const fn source_sha256(&self) -> &[u8; 32] {
        &self.source_sha256
    }

    /// Returns the canonical target-profile identity.
    #[must_use]
    pub fn target_profile(&self) -> &str {
        &self.target_profile
    }

    /// Returns ordered explicit type-table entries.
    #[must_use]
    pub fn types(&self) -> &[TypeEntry] {
        &self.types
    }
}
