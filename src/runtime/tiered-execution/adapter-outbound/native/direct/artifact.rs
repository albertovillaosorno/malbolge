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
//   - Verified artifact wrappers and public direct-plan value types.
// - Must-Not:
//   - Bypass canonical object identity or semantic admission.
// - Allows:
//   - Inputs: reviewed direct-native planning and artifact values.
//   - Outputs: deterministic values owned by this direct-native slice.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - The slice exceeds one independently reviewable responsibility.
// - Merge-When:
//   - Another module owns the exact same direct-native authority.
// - Summary:
//   - Verified direct-native value types.
// - Description:
//   - Isolates one direct-native responsibility from the facade.
// - Usage:
//   - Used only through the parent direct-native module.
// - Defaults:
//   - Unsupported values fail closed.
//

//! Verified artifact and plan value types.

use super::*;

/// Direct native template selected for one portable IR program.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectNativeKind {
    /// Exact non-aliasing one-step crazy transition.
    Crazy,
    /// Safe fallback artifact that always requests interpreter deoptimization.
    Deopt,
    /// Exact graphical halt fetch with one code-cell live-in.
    HaltFetch,
    /// One-step halt bound to one exact register/counter observation.
    HaltRegisters,
    /// Exact one-step zero-state halt fast path.
    InitialHalt,
    /// Exact one-step input transition for byte or EOF.
    Input,
    /// Exact non-aliasing one-step jump-code transition.
    JumpCode,
    /// Exact non-aliasing one-step jump-data transition.
    JumpData,
    /// Exact one-step no-operation with one code-cell write.
    NoOperation,
    /// Exact non-graphical code-cell termination fast path.
    NonGraphical,
    /// Exact one-step output transition with one byte append.
    Output,
    /// Exact non-aliasing one-step rotate transition.
    Rotate,
}

/// Exact host surface considered by direct native planning.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DirectHost {
    pub(super) isa: HostIsa,
    pub(super) operating_system: HostOperatingSystem,
}

impl DirectHost {
    /// Constructs one explicit direct native host identity.
    #[must_use]
    pub const fn new(
        operating_system: HostOperatingSystem,
        isa: HostIsa,
    ) -> Self {
        Self { isa, operating_system }
    }
}
/// Native object proven to be the canonical no-write guard-miss stub.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedDeoptNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedDeoptNativeObjectArtifact {
    /// Returns the exact native artifact identity associated with the stub.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement guarded explicit-geometry initial halt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedExecutionGeometryInitialHaltNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedExecutionGeometryInitialHaltNativeObjectArtifact {
    /// Returns the exact v5 native artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement guarded explicit-geometry initial
/// jump-data.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedExecutionGeometryInitialJumpDataNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedExecutionGeometryInitialJumpDataNativeObjectArtifact {
    /// Returns the exact v5 native artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement guarded explicit-geometry input.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedExecutionGeometryInputNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedExecutionGeometryInputNativeObjectArtifact {
    /// Returns the exact v5 native artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement guarded explicit-geometry no-operation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedExecutionGeometryNoOperationNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedExecutionGeometryNoOperationNativeObjectArtifact {
    /// Returns the exact v5 native artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement guarded explicit-geometry output.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedExecutionGeometryOutputNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedExecutionGeometryOutputNativeObjectArtifact {
    /// Returns the exact v5 native artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement guarded explicit-geometry rotate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedExecutionGeometryRotateNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedExecutionGeometryRotateNativeObjectArtifact {
    /// Returns the exact v5 native artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement exact graphical halt fetch.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedHaltFetchNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedHaltFetchNativeObjectArtifact {
    /// Returns the exact native artifact identity associated with the fast
    /// path.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement exact-observation one-step halt.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedHaltRegistersNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedHaltRegistersNativeObjectArtifact {
    /// Returns the exact native artifact identity associated with the fast
    /// path.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement exact non-graphical termination.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedNonGraphicalNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedNonGraphicalNativeObjectArtifact {
    /// Returns the exact native artifact identity associated with the fast
    /// path.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement exact one-step input.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedInputNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedInputNativeObjectArtifact {
    /// Returns the exact native artifact identity associated with the fast
    /// path.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement exact non-aliasing jump-code.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedJumpCodeNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedJumpCodeNativeObjectArtifact {
    /// Returns the exact native artifact identity associated with the fast
    /// path.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement exact non-aliasing jump-data.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedJumpDataNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedJumpDataNativeObjectArtifact {
    /// Returns the exact native artifact identity associated with the fast
    /// path.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement exact non-aliasing crazy.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedCrazyNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedCrazyNativeObjectArtifact {
    /// Returns the exact native artifact identity associated with the fast
    /// path.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement exact one-step output.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedOutputNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedOutputNativeObjectArtifact {
    /// Returns the exact native artifact identity associated with the fast
    /// path.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement exact non-aliasing rotate.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedRotateNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedRotateNativeObjectArtifact {
    /// Returns the exact native artifact identity associated with the fast
    /// path.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement one exact no-operation transition.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedNoOperationNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedNoOperationNativeObjectArtifact {
    /// Returns the exact native artifact identity associated with the fast
    /// path.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Native object proven to implement the exact initial-halt fast path.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedInitialHaltNativeObjectArtifact {
    pub(super) artifact: StructurallyAdmittedNativeObjectArtifact,
}

impl VerifiedInitialHaltNativeObjectArtifact {
    /// Returns the exact native artifact identity associated with the fast
    /// path.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        self.artifact.key()
    }

    /// Returns the exact verified canonical COFF bytes.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        self.artifact.object()
    }

    /// Returns the exact Windows target triple selected for linking.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.artifact.target_triple()
    }
}

/// Semantically admitted direct native artifact selected for one exact IR.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum VerifiedDirectNativeArtifact {
    /// Exact non-aliasing one-step crazy transition.
    Crazy(VerifiedCrazyNativeObjectArtifact),
    /// Safe no-state-change guard-miss fallback.
    Deopt(VerifiedDeoptNativeObjectArtifact),
    /// Exact graphical halt fetch with one code-cell live-in.
    HaltFetch(VerifiedHaltFetchNativeObjectArtifact),
    /// One-step halt bound to one exact register/counter observation.
    HaltRegisters(VerifiedHaltRegistersNativeObjectArtifact),
    /// Exact zero-state one-step halt fast path.
    InitialHalt(VerifiedInitialHaltNativeObjectArtifact),
    /// Exact one-step input transition for byte or EOF.
    Input(VerifiedInputNativeObjectArtifact),
    /// Exact non-aliasing one-step jump-code transition.
    JumpCode(VerifiedJumpCodeNativeObjectArtifact),
    /// Exact non-aliasing one-step jump-data transition.
    JumpData(VerifiedJumpDataNativeObjectArtifact),
    /// Exact one-step no-operation with one code-cell write.
    NoOperation(VerifiedNoOperationNativeObjectArtifact),
    /// Exact non-graphical code-cell termination fast path.
    NonGraphical(VerifiedNonGraphicalNativeObjectArtifact),
    /// Exact one-step output transition with one byte append.
    Output(VerifiedOutputNativeObjectArtifact),
    /// Exact non-aliasing one-step rotate transition.
    Rotate(VerifiedRotateNativeObjectArtifact),
}

/// Profile-preflighted execution-tier plan for one portable IR program.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum PreflightedExecutionTier {
    /// One semantically admitted direct object is available for this host.
    Direct(Box<VerifiedDirectNativeArtifact>),
    /// No direct object format exists; use the normative interpreter.
    Interpreter,
}

/// Whether a cache-aware direct plan reused or inserted an artifact.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectCacheDisposition {
    /// The exact verified artifact already existed under the complete key.
    Hit,
    /// The planner emitted, verified, and inserted a new exact-key artifact.
    Inserted,
}

/// Cache-aware profile-preflighted execution-tier plan.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum CachedPreflightedExecutionTier {
    /// One verified direct artifact plus its cache disposition.
    Direct {
        /// Exact semantically admitted direct artifact.
        artifact: Arc<VerifiedDirectNativeArtifact>,
        /// Whether this exact artifact was reused or newly inserted.
        cache: DirectCacheDisposition,
    },
    /// No direct object format exists; use the normative interpreter.
    Interpreter,
}

/// Caller-owned cache containing only semantically admitted direct artifacts.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct VerifiedDirectNativeCache {
    pub(super) entries: NativeArtifactCache<Arc<VerifiedDirectNativeArtifact>>,
}
impl VerifiedDirectNativeArtifact {
    /// Returns the exact selected native artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        match self {
            Self::Crazy(artifact) => artifact.key(),
            Self::Deopt(artifact) => artifact.key(),
            Self::HaltFetch(artifact) => artifact.key(),
            Self::HaltRegisters(artifact) => artifact.key(),
            Self::InitialHalt(artifact) => artifact.key(),
            Self::Input(artifact) => artifact.key(),
            Self::JumpCode(artifact) => artifact.key(),
            Self::JumpData(artifact) => artifact.key(),
            Self::NonGraphical(artifact) => artifact.key(),
            Self::NoOperation(artifact) => artifact.key(),
            Self::Output(artifact) => artifact.key(),
            Self::Rotate(artifact) => artifact.key(),
        }
    }

    /// Returns which reviewed direct template was selected.
    #[must_use]
    pub const fn kind(&self) -> DirectNativeKind {
        match self {
            Self::Crazy(_artifact) => DirectNativeKind::Crazy,
            Self::Deopt(_artifact) => DirectNativeKind::Deopt,
            Self::HaltFetch(_artifact) => DirectNativeKind::HaltFetch,
            Self::HaltRegisters(_artifact) => DirectNativeKind::HaltRegisters,
            Self::InitialHalt(_artifact) => DirectNativeKind::InitialHalt,
            Self::Input(_artifact) => DirectNativeKind::Input,
            Self::JumpCode(_artifact) => DirectNativeKind::JumpCode,
            Self::JumpData(_artifact) => DirectNativeKind::JumpData,
            Self::NonGraphical(_artifact) => DirectNativeKind::NonGraphical,
            Self::NoOperation(_artifact) => DirectNativeKind::NoOperation,
            Self::Output(_artifact) => DirectNativeKind::Output,
            Self::Rotate(_artifact) => DirectNativeKind::Rotate,
        }
    }

    /// Returns verified object bytes for the selected template.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        match self {
            Self::Crazy(artifact) => artifact.object(),
            Self::Deopt(artifact) => artifact.object(),
            Self::HaltFetch(artifact) => artifact.object(),
            Self::HaltRegisters(artifact) => artifact.object(),
            Self::InitialHalt(artifact) => artifact.object(),
            Self::Input(artifact) => artifact.object(),
            Self::JumpCode(artifact) => artifact.object(),
            Self::JumpData(artifact) => artifact.object(),
            Self::NonGraphical(artifact) => artifact.object(),
            Self::NoOperation(artifact) => artifact.object(),
            Self::Output(artifact) => artifact.object(),
            Self::Rotate(artifact) => artifact.object(),
        }
    }

    /// Returns the exact selected Windows target triple.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        match self {
            Self::Crazy(artifact) => artifact.target_triple(),
            Self::Deopt(artifact) => artifact.target_triple(),
            Self::HaltFetch(artifact) => artifact.target_triple(),
            Self::HaltRegisters(artifact) => artifact.target_triple(),
            Self::InitialHalt(artifact) => artifact.target_triple(),
            Self::Input(artifact) => artifact.target_triple(),
            Self::JumpCode(artifact) => artifact.target_triple(),
            Self::JumpData(artifact) => artifact.target_triple(),
            Self::NonGraphical(artifact) => artifact.target_triple(),
            Self::NoOperation(artifact) => artifact.target_triple(),
            Self::Output(artifact) => artifact.target_triple(),
            Self::Rotate(artifact) => artifact.target_triple(),
        }
    }
}
