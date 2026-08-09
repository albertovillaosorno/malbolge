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
//   - Typed inbound semantic projection of normalized C frontend version one.
// - Must-Not:
//   - Parse JSON, expose Clang objects, or contain downstream IR decisions.
// - Allows:
//   - Inputs: portable frontend identity, source provenance, and supported
//     normalized function semantics.
//   - Outputs: immutable values consumed by typed-IR application lowering.
//   - Side effects: none.
// - Split-When:
//   - Serialized frontend adaptation or another frontend version needs policy.
// - Merge-When:
//   - The normalized frontend and typed IR share one implementation boundary.
// - Summary:
//   - Defines the semantic handoff from normalized C into portable typed IR.
// - Description:
//   - Version one begins with exact integer-return functions and grows by
//     explicit reviewed semantic variants.
// - Usage:
//   - Constructed by a frontend artifact adapter and consumed by lowering.
// - Defaults:
//   - Unsupported frontend semantics are not silently approximated.
//

//! Inbound normalized-C semantic projection for typed compiler IR lowering.

/// One normalized source position from the frontend artifact.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct FrontendPosition {
    byte: u32,
    column: u32,
    line: u32,
}

impl FrontendPosition {
    /// Returns the zero-based source byte offset.
    #[must_use]
    pub const fn byte(self) -> u32 {
        self.byte
    }

    /// Returns the one-based source column.
    #[must_use]
    pub const fn column(self) -> u32 {
        self.column
    }

    /// Returns the one-based source line.
    #[must_use]
    pub const fn line(self) -> u32 {
        self.line
    }

    /// Creates one normalized frontend source position.
    #[must_use]
    pub const fn new(byte: u32, line: u32, column: u32) -> Self {
        Self { byte, column, line }
    }
}

/// One half-open normalized source span from the frontend artifact.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct FrontendSpan {
    begin: FrontendPosition,
    end: FrontendPosition,
}

impl FrontendSpan {
    /// Returns the inclusive begin position.
    #[must_use]
    pub const fn begin(self) -> FrontendPosition {
        self.begin
    }

    /// Returns the exclusive end position.
    #[must_use]
    pub const fn end(self) -> FrontendPosition {
        self.end
    }

    /// Creates one normalized frontend source span.
    #[must_use]
    pub const fn new(begin: FrontendPosition, end: FrontendPosition) -> Self {
        Self { begin, end }
    }
}

/// Construction payload for one supported normalized integer-return function.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FrontendReturnIntegerFunctionSpec {
    /// Normalized compound-statement span.
    pub body_span: FrontendSpan,
    /// Semantic decimal integer value from the frontend.
    pub constant_decimal: String,
    /// Normalized declaration definition classification.
    pub definition: String,
    /// Complete function-declaration span.
    pub function_span: FrontendSpan,
    /// Whether the source declaration explicitly specified `inline`.
    pub inline_specified: bool,
    /// Normalized declaration linkage classification.
    pub linkage: String,
    /// Portable source-level function name.
    pub name: String,
    /// Normalized return-statement span.
    pub return_span: FrontendSpan,
    /// Canonical normalized function type spelling.
    pub signature: String,
    /// Normalized declaration storage-class classification.
    pub storage_class: String,
    /// Integer-literal span.
    pub value_span: FrontendSpan,
    /// Canonical normalized integer type spelling.
    pub value_type: String,
}

/// One supported normalized function whose body returns one integer constant.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FrontendReturnIntegerFunction {
    body_span: FrontendSpan,
    constant_decimal: String,
    definition: String,
    function_span: FrontendSpan,
    inline_specified: bool,
    linkage: String,
    name: String,
    return_span: FrontendSpan,
    signature: String,
    storage_class: String,
    value_span: FrontendSpan,
    value_type: String,
}

impl FrontendReturnIntegerFunction {
    /// Returns the normalized body span.
    #[must_use]
    pub const fn body_span(&self) -> FrontendSpan {
        self.body_span
    }

    /// Returns the semantic decimal integer value.
    #[must_use]
    pub fn constant_decimal(&self) -> &str {
        &self.constant_decimal
    }

    /// Returns normalized declaration definition classification.
    #[must_use]
    pub fn definition(&self) -> &str {
        &self.definition
    }

    /// Returns the complete function span.
    #[must_use]
    pub const fn function_span(&self) -> FrontendSpan {
        self.function_span
    }

    /// Returns whether `inline` was explicitly specified.
    #[must_use]
    pub const fn inline_specified(&self) -> bool {
        self.inline_specified
    }

    /// Returns normalized declaration linkage classification.
    #[must_use]
    pub fn linkage(&self) -> &str {
        &self.linkage
    }

    /// Returns the portable function name.
    #[must_use]
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Creates one supported normalized function projection.
    #[must_use]
    pub fn new(spec: FrontendReturnIntegerFunctionSpec) -> Self {
        Self {
            body_span: spec.body_span,
            constant_decimal: spec.constant_decimal,
            definition: spec.definition,
            function_span: spec.function_span,
            inline_specified: spec.inline_specified,
            linkage: spec.linkage,
            name: spec.name,
            return_span: spec.return_span,
            signature: spec.signature,
            storage_class: spec.storage_class,
            value_span: spec.value_span,
            value_type: spec.value_type,
        }
    }

    /// Returns the normalized return-statement span.
    #[must_use]
    pub const fn return_span(&self) -> FrontendSpan {
        self.return_span
    }

    /// Returns the normalized function type spelling.
    #[must_use]
    pub fn signature(&self) -> &str {
        &self.signature
    }

    /// Returns normalized declaration storage-class classification.
    #[must_use]
    pub fn storage_class(&self) -> &str {
        &self.storage_class
    }

    /// Returns the integer-literal span.
    #[must_use]
    pub const fn value_span(&self) -> FrontendSpan {
        self.value_span
    }

    /// Returns the normalized integer type spelling.
    #[must_use]
    pub fn value_type(&self) -> &str {
        &self.value_type
    }
}

/// Construction payload for one normalized frontend semantic projection.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FrontendArtifactSpec {
    /// Deterministic guest ABI identity.
    pub abi_id: String,
    /// Normalized frontend artifact identity.
    pub artifact_id: String,
    /// Exact reviewed Clang target triple.
    pub clang_target: String,
    /// Exact reviewed Clang/LLVM version.
    pub clang_version: String,
    /// Ordered supported normalized functions.
    pub functions: Vec<FrontendReturnIntegerFunction>,
    /// Exact reviewed source-language mode.
    pub language: String,
    /// Frontend artifact schema version.
    pub schema_version: u16,
    /// Portable source identity.
    pub source_id: String,
    /// Exact normalized source SHA-256 bytes.
    pub source_sha256: [u8; 32],
    /// Canonical target-profile identity.
    pub target_profile: String,
}

/// One typed semantic projection of a normalized C frontend artifact.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FrontendArtifact {
    abi_id: String,
    artifact_id: String,
    clang_target: String,
    clang_version: String,
    functions: Vec<FrontendReturnIntegerFunction>,
    language: String,
    schema_version: u16,
    source_id: String,
    source_sha256: [u8; 32],
    target_profile: String,
}

impl FrontendArtifact {
    /// Returns the deterministic guest ABI identity.
    #[must_use]
    pub fn abi_id(&self) -> &str {
        &self.abi_id
    }

    /// Returns the normalized frontend artifact identity.
    #[must_use]
    pub fn artifact_id(&self) -> &str {
        &self.artifact_id
    }

    /// Returns the exact reviewed Clang target triple.
    #[must_use]
    pub fn clang_target(&self) -> &str {
        &self.clang_target
    }

    /// Returns the exact reviewed Clang/LLVM version.
    #[must_use]
    pub fn clang_version(&self) -> &str {
        &self.clang_version
    }

    /// Returns ordered supported normalized functions.
    #[must_use]
    pub fn functions(&self) -> &[FrontendReturnIntegerFunction] {
        &self.functions
    }

    /// Returns the exact reviewed source-language mode.
    #[must_use]
    pub fn language(&self) -> &str {
        &self.language
    }

    /// Creates one normalized frontend semantic projection.
    #[must_use]
    pub fn new(spec: FrontendArtifactSpec) -> Self {
        Self {
            abi_id: spec.abi_id,
            artifact_id: spec.artifact_id,
            clang_target: spec.clang_target,
            clang_version: spec.clang_version,
            functions: spec.functions,
            language: spec.language,
            schema_version: spec.schema_version,
            source_id: spec.source_id,
            source_sha256: spec.source_sha256,
            target_profile: spec.target_profile,
        }
    }

    /// Returns the frontend artifact schema version.
    #[must_use]
    pub const fn schema_version(&self) -> u16 {
        self.schema_version
    }

    /// Returns the portable source identity.
    #[must_use]
    pub fn source_id(&self) -> &str {
        &self.source_id
    }

    /// Returns exact normalized source SHA-256 bytes.
    #[must_use]
    pub const fn source_sha256(&self) -> &[u8; 32] {
        &self.source_sha256
    }

    /// Returns the canonical target-profile identity.
    #[must_use]
    pub fn target_profile(&self) -> &str {
        &self.target_profile
    }
}
