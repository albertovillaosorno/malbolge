// File:
//   - direct.rs
// Path:
//   - execution/native/direct.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Canonical reviewed direct objects and byte-exact semantic admission.
// - Must-Not:
//   - Lower unsupported effects, bypass verifier guards, or trust compiler
//   - output.
// - Allows:
//   - Inputs: portable region IR, explicit runtime capability, and exact
//   - Windows native target identity.
//   - Outputs: profile-bound COFF candidates and verified direct artifacts.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when general region-effect instruction selection outgrows
//   - templates.
// - Merge-When:
//   - Merge when all direct emitters share one reviewed instruction template.
// - Summary:
//   - Owns byte-canonical deopt and reviewed direct native templates.
// - Description:
//   - Emits reviewed x86-64/AArch64 objects for exact verified IR subsets.
// - Usage:
//   - Provides a safe deopt floor plus reviewed terminal/no-op fast paths.
// - Defaults:
//   - Unsupported IR is rejected; no direct template is selected implicitly.
//
// Related documents:
// - docs/technical/adr/tiered-native-execution.md
// - docs/technical/adr/verification-trust-boundary.md
//
// Large file:
//   - true
//

//! Canonical direct native templates with byte-exact semantic verification.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::sync::Arc;

use malbolge::{
    PortableProfileRequirementError, ProfileMachineObservation,
    ProfileMemoryDelta, ProfileMemoryWrite, ProfileRegisters, RunOutcome,
    RuntimeCapability, Termination, decode_profile_instruction,
    encrypt_profile_cell, preflight_portable_profile_requirement,
    profile_cell_decodes_to_no_operation, profile_cell_is_graphical,
    profile_pointer_successor,
};

use super::profile_metadata::canonical_profile_metadata;
use super::{
    CoffAdmissionError, NATIVE_REGION_ABI_REVISION,
    StructurallyAdmittedNativeObjectArtifact, UntrustedNativeObjectArtifact,
    aarch64, structurally_admit_coff, x86_64,
};
use crate::execution_cache::{
    HostIsa, HostOperatingSystem, NativeArtifactCache, NativeArtifactKey,
    NativeIdentityError, NativeTargetConfig, NativeTargetIdentity,
    RegionEffectIdentity,
};
use crate::execution_ir::{
    EFFECT_IR_VERSION, EffectOp, MemoryLiveIn, RegionEffectProgram,
};

const COFF_HEADER_BYTES: usize = 20;
const COFF_SECTION_BYTES: usize = 40;
const COFF_SYMBOL_BYTES: usize = 18;
const IMAGE_FILE_MACHINE_AMD64: u16 = 0x8664;
const IMAGE_FILE_MACHINE_ARM64: u16 = 0xaa64;
const IMAGE_SCN_X86_TEXT: u32 = 0x6050_0020;
const IMAGE_SCN_ARM64_TEXT: u32 = 0x6030_0020;
const IMAGE_SCN_PROFILE_METADATA: u32 = 0x4030_0040;
const IMAGE_SYM_CLASS_EXTERNAL: u8 = 2;
const IMAGE_SYM_DTYPE_FUNCTION: u16 = 0x0020;
const REQUIRED_ENTRY: &str = "malbolge_native_region_apply";

/// Backend identity for the first direct, semantically admitted native tier.
pub const DIRECT_DEOPT_BACKEND_ID: &str = "direct-deopt-stub";
/// Direct deoptimization-stub code-generation revision.
pub const DIRECT_DEOPT_BACKEND_REVISION: u32 = 4;
/// Backend identity for the first state-applying direct native fast path.
pub const DIRECT_INITIAL_HALT_BACKEND_ID: &str = "direct-initial-halt";
/// Direct initial-halt code-generation revision.
pub const DIRECT_INITIAL_HALT_BACKEND_REVISION: u32 = 4;
/// Backend identity for exact-observation one-step direct halt.
pub const DIRECT_HALT_REGISTERS_BACKEND_ID: &str = "direct-halt-registers";
/// Direct exact-observation halt code-generation revision.
pub const DIRECT_HALT_REGISTERS_BACKEND_REVISION: u32 = 5;

/// Backend identity for exact graphical halt fetch termination.
pub const DIRECT_HALT_FETCH_BACKEND_ID: &str = "direct-halt-fetch";
/// Direct graphical halt-fetch code-generation revision.
pub const DIRECT_HALT_FETCH_BACKEND_REVISION: u32 = 1;

/// Backend identity for exact non-graphical fetch termination.
pub const DIRECT_NON_GRAPHICAL_BACKEND_ID: &str = "direct-non-graphical";
/// Direct non-graphical termination code-generation revision.
pub const DIRECT_NON_GRAPHICAL_BACKEND_REVISION: u32 = 1;

/// Backend identity for exact one-step no-operation execution.
pub const DIRECT_NO_OPERATION_BACKEND_ID: &str = "direct-no-operation";
/// Direct no-operation code-generation revision.
pub const DIRECT_NO_OPERATION_BACKEND_REVISION: u32 = 1;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct DirectEntryObservation {
    pub(super) accumulator: u32,
    pub(super) code_pointer: u32,
    pub(super) data_pointer: u32,
    pub(super) input_consumed: u64,
    pub(super) output_len: u64,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct DirectNoOperationCommit {
    pub(super) encrypted_value: u32,
    pub(super) next_code_pointer: u32,
    pub(super) next_data_pointer: u32,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DirectFetchedTerminalProgram {
    live_in: MemoryLiveIn,
    observation: ProfileMachineObservation,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct DirectNoOperationProgram {
    encrypted_value: u32,
    live_in: MemoryLiveIn,
    next_code_pointer: u32,
    next_data_pointer: u32,
    observation: ProfileMachineObservation,
}

/// Failure while emitting or verifying the direct deoptimization stub.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectDeoptError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical direct deopt object.
    ObjectBytes,
    /// Target backend/revision/native ABI is not the direct deopt contract.
    TargetBackend,
    /// Direct deopt v4 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct deopt v3 emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectDeoptError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => "direct deopt COFF structure was rejected",
            Self::Identity(_error) => {
                "direct deopt native identity construction failed"
            },
            Self::ObjectBytes => {
                "direct deopt object differs from canonical bytes"
            },
            Self::TargetBackend => {
                "target does not select direct deopt backend"
            },
            Self::TargetFeatures => {
                "direct deopt backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct deopt backend currently requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectDeoptError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectDeoptError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying exact-observation direct halt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectHaltRegistersError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical observation-bound halt object.
    ObjectBytes,
    /// Portable IR is outside the exact observation-bound halt subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not the register-halt contract.
    TargetBackend,
    /// Register-halt v5 has no target-specific feature specializations.
    TargetFeatures,
    /// Register-halt v3 emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectHaltRegistersError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct register-halt COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct register-halt identity construction failed"
            },
            Self::ObjectBytes => {
                "direct register-halt object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "portable IR is outside direct register-halt subset"
            },
            Self::TargetBackend => {
                "target does not select direct register-halt backend"
            },
            Self::TargetFeatures => {
                "direct register-halt backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct register-halt backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectHaltRegistersError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectHaltRegistersError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying exact graphical halt fetch.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectHaltFetchError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical halt-fetch object.
    ObjectBytes,
    /// Portable IR is outside the exact halt-fetch subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this contract.
    TargetBackend,
    /// Halt-fetch v1 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct halt-fetch currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectHaltFetchError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct halt-fetch COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct halt-fetch identity construction failed"
            },
            Self::ObjectBytes => {
                "direct halt-fetch object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "portable IR is outside direct halt-fetch subset"
            },
            Self::TargetBackend => {
                "target does not select direct halt-fetch backend"
            },
            Self::TargetFeatures => {
                "direct halt-fetch backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct halt-fetch backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectHaltFetchError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectHaltFetchError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying direct non-graphical termination.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectNonGraphicalError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical non-graphical object.
    ObjectBytes,
    /// Portable IR is outside the exact non-graphical subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this contract.
    TargetBackend,
    /// Non-graphical v1 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct non-graphical currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectNonGraphicalError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct non-graphical COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct non-graphical identity construction failed"
            },
            Self::ObjectBytes => {
                "direct non-graphical object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "portable IR is outside direct non-graphical subset"
            },
            Self::TargetBackend => {
                "target does not select direct non-graphical backend"
            },
            Self::TargetFeatures => {
                "direct non-graphical backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct non-graphical backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectNonGraphicalError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectNonGraphicalError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying exact one-step no-operation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectNoOperationError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical no-operation object.
    ObjectBytes,
    /// Portable IR is outside the exact no-operation subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this contract.
    TargetBackend,
    /// No-operation v1 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct no-operation currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectNoOperationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct no-operation COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct no-operation identity construction failed"
            },
            Self::ObjectBytes => {
                "direct no-operation object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "portable IR is outside direct no-operation subset"
            },
            Self::TargetBackend => {
                "target does not select direct no-operation backend"
            },
            Self::TargetFeatures => {
                "direct no-operation backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct no-operation backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectNoOperationError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectNoOperationError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying the direct initial-halt fast path.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectInitialHaltError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical direct initial-halt object.
    ObjectBytes,
    /// Portable IR is outside the exact initial-halt subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not the initial-halt contract.
    TargetBackend,
    /// Direct initial-halt v4 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct initial-halt v3 emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectInitialHaltError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct initial-halt COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct initial-halt identity construction failed"
            },
            Self::ObjectBytes => {
                "direct initial-halt object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "portable IR is outside direct initial-halt subset"
            },
            Self::TargetBackend => {
                "target does not select direct initial-halt backend"
            },
            Self::TargetFeatures => {
                "direct initial-halt backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct initial-halt backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectInitialHaltError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectInitialHaltError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Direct native template selected for one portable IR program.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectNativeKind {
    /// Safe fallback artifact that always requests interpreter deoptimization.
    Deopt,
    /// Exact graphical halt fetch with one code-cell live-in.
    HaltFetch,
    /// One-step halt bound to one exact register/counter observation.
    HaltRegisters,
    /// Exact one-step zero-state halt fast path.
    InitialHalt,
    /// Exact one-step no-operation with one code-cell write.
    NoOperation,
    /// Exact non-graphical code-cell termination fast path.
    NonGraphical,
}

/// Exact host surface considered by direct native planning.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DirectHost {
    isa: HostIsa,
    operating_system: HostOperatingSystem,
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

/// Failure while selecting/emitting/verifying one direct native template.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DirectSelectionError<'requirement> {
    /// Deoptimization artifact emission or admission failed.
    Deopt(Box<DirectDeoptError>),
    /// Graphical halt-fetch artifact emission or admission failed.
    HaltFetch(Box<DirectHaltFetchError>),
    /// Arbitrary-register halt artifact emission or admission failed.
    HaltRegisters(Box<DirectHaltRegistersError>),
    /// Initial-halt artifact emission or admission failed.
    InitialHalt(Box<DirectInitialHaltError>),
    /// No-operation artifact emission or admission failed.
    NoOperation(Box<DirectNoOperationError>),
    /// Non-graphical artifact emission or admission failed.
    NonGraphical(Box<DirectNonGraphicalError>),
    /// Selected runtime cannot implement the admitted profile requirement.
    Profile(Box<PortableProfileRequirementError<'requirement>>),
    /// Direct native templates currently emit Windows COFF only.
    TargetFormat,
}

impl Display for DirectSelectionError<'_> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Deopt(error) => Display::fmt(error, f),
            Self::HaltRegisters(error) => Display::fmt(error, f),
            Self::HaltFetch(error) => Display::fmt(error, f),
            Self::InitialHalt(error) => Display::fmt(error, f),
            Self::NonGraphical(error) => Display::fmt(error, f),
            Self::NoOperation(error) => Display::fmt(error, f),
            Self::Profile(error) => Display::fmt(error, f),
            Self::TargetFormat => f.write_str(
                "direct native selection currently requires Windows",
            ),
        }
    }
}

/// Native object proven to be the canonical no-write guard-miss stub.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedDeoptNativeObjectArtifact {
    artifact: StructurallyAdmittedNativeObjectArtifact,
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

/// Native object proven to implement exact graphical halt fetch.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedHaltFetchNativeObjectArtifact {
    artifact: StructurallyAdmittedNativeObjectArtifact,
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
    artifact: StructurallyAdmittedNativeObjectArtifact,
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
    artifact: StructurallyAdmittedNativeObjectArtifact,
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

/// Native object proven to implement one exact no-operation transition.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedNoOperationNativeObjectArtifact {
    artifact: StructurallyAdmittedNativeObjectArtifact,
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
    artifact: StructurallyAdmittedNativeObjectArtifact,
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
    /// Safe no-state-change guard-miss fallback.
    Deopt(VerifiedDeoptNativeObjectArtifact),
    /// Exact graphical halt fetch with one code-cell live-in.
    HaltFetch(VerifiedHaltFetchNativeObjectArtifact),
    /// One-step halt bound to one exact register/counter observation.
    HaltRegisters(VerifiedHaltRegistersNativeObjectArtifact),
    /// Exact zero-state one-step halt fast path.
    InitialHalt(VerifiedInitialHaltNativeObjectArtifact),
    /// Exact one-step no-operation with one code-cell write.
    NoOperation(VerifiedNoOperationNativeObjectArtifact),
    /// Exact non-graphical code-cell termination fast path.
    NonGraphical(VerifiedNonGraphicalNativeObjectArtifact),
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
    entries: NativeArtifactCache<Arc<VerifiedDirectNativeArtifact>>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum SelectedDirectTarget {
    Deopt(NativeTargetIdentity),
    HaltFetch(NativeTargetIdentity),
    HaltRegisters(NativeTargetIdentity),
    InitialHalt(NativeTargetIdentity),
    NoOperation(NativeTargetIdentity),
    NonGraphical(NativeTargetIdentity),
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum PreparedDirectTarget {
    Deopt(NativeArtifactKey),
    HaltFetch(NativeArtifactKey),
    HaltRegisters(NativeArtifactKey),
    InitialHalt(NativeArtifactKey),
    NoOperation(NativeArtifactKey),
    NonGraphical(NativeArtifactKey),
}

type VerifiedDirectSelectionResult<'requirement> =
    Result<VerifiedDirectNativeArtifact, DirectSelectionError<'requirement>>;

impl VerifiedDirectNativeCache {
    /// Removes every retained verified artifact.
    pub fn clear(&mut self) {
        self.entries.clear();
    }

    /// Invalidates future reuse of one exact verified artifact key.
    ///
    /// Outstanding [`Arc`] owners remain valid; invalidation only removes the
    /// cache entry used by later planning.
    pub fn invalidate(
        &mut self,
        artifact: &VerifiedDirectNativeArtifact,
    ) -> bool {
        self.entries.remove(artifact.key()).is_some()
    }

    /// Invalidates future reuse of every direct variant for one exact program.
    ///
    /// Outstanding [`Arc`] owners remain valid. Program identity construction
    /// fails before mutation when the IR exceeds its declared profile capacity.
    ///
    /// # Errors
    ///
    /// Returns [`NativeIdentityError`] when exact region identity cannot be
    /// constructed.
    pub fn invalidate_program(
        &mut self,
        program: &RegionEffectProgram,
    ) -> Result<usize, NativeIdentityError> {
        let identity = RegionEffectIdentity::new(program)?;
        Ok(self.entries.remove_region(&identity))
    }

    /// Invalidates every cached region for one artifact's exact direct target.
    ///
    /// The target includes host ISA, backend/revision, native ABI revision, and
    /// required features. Outstanding [`Arc`] owners remain valid.
    pub fn invalidate_target(
        &mut self,
        artifact: &VerifiedDirectNativeArtifact,
    ) -> usize {
        self.entries.remove_target(artifact.key().target())
    }

    /// Reports whether no verified direct artifacts are retained.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Returns the number of exact-key verified direct artifacts.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.entries.len()
    }
}

impl PreparedDirectTarget {
    fn emit_verified(
        self,
        program: &RegionEffectProgram,
    ) -> VerifiedDirectSelectionResult<'_> {
        match self {
            Self::Deopt(key) => {
                validate_target(key.target()).map_err(|error| {
                    DirectSelectionError::Deopt(Box::new(error))
                })?;
                let artifact =
                    emit_direct_deopt_with_key(key).map_err(|error| {
                        DirectSelectionError::Deopt(Box::new(error))
                    })?;
                let verified =
                    verify_direct_deopt_stub(&artifact).map_err(|error| {
                        DirectSelectionError::Deopt(Box::new(error))
                    })?;
                Ok(VerifiedDirectNativeArtifact::Deopt(verified))
            },
            Self::HaltFetch(key) => emit_verified_halt_fetch(key, program),
            Self::HaltRegisters(key) => {
                let registers = validate_halt_registers_program(program)
                    .map_err(|error| {
                        DirectSelectionError::HaltRegisters(Box::new(error))
                    })?;
                validate_halt_registers_target(key.target()).map_err(
                    |error| {
                        DirectSelectionError::HaltRegisters(Box::new(error))
                    },
                )?;
                let artifact =
                    emit_direct_halt_registers_with_key(key, registers)
                        .map_err(|error| {
                            DirectSelectionError::HaltRegisters(Box::new(error))
                        })?;
                let verified = verify_direct_halt_registers(&artifact, program)
                    .map_err(|error| {
                        DirectSelectionError::HaltRegisters(Box::new(error))
                    })?;
                Ok(VerifiedDirectNativeArtifact::HaltRegisters(verified))
            },
            Self::InitialHalt(key) => {
                validate_initial_halt_program(program).map_err(|error| {
                    DirectSelectionError::InitialHalt(Box::new(error))
                })?;
                validate_initial_halt_target(key.target()).map_err(
                    |error| DirectSelectionError::InitialHalt(Box::new(error)),
                )?;
                let artifact = emit_direct_initial_halt_with_key(key).map_err(
                    |error| DirectSelectionError::InitialHalt(Box::new(error)),
                )?;
                let verified = verify_direct_initial_halt(&artifact, program)
                    .map_err(|error| {
                    DirectSelectionError::InitialHalt(Box::new(error))
                })?;
                Ok(VerifiedDirectNativeArtifact::InitialHalt(verified))
            },
            Self::NonGraphical(key) => {
                emit_verified_non_graphical(key, program)
            },
            Self::NoOperation(key) => emit_verified_no_operation(key, program),
        }
    }

    const fn key(&self) -> &NativeArtifactKey {
        match self {
            Self::Deopt(key)
            | Self::HaltFetch(key)
            | Self::HaltRegisters(key)
            | Self::InitialHalt(key)
            | Self::NonGraphical(key)
            | Self::NoOperation(key) => key,
        }
    }
}

impl SelectedDirectTarget {
    fn prepare(
        self,
        program: &RegionEffectProgram,
    ) -> Result<PreparedDirectTarget, DirectSelectionError<'_>> {
        match self {
            Self::Deopt(target) => NativeArtifactKey::new(program, target)
                .map(PreparedDirectTarget::Deopt)
                .map_err(|error| {
                    DirectSelectionError::Deopt(Box::new(
                        DirectDeoptError::Identity(error),
                    ))
                }),
            Self::HaltFetch(target) => NativeArtifactKey::new(program, target)
                .map(PreparedDirectTarget::HaltFetch)
                .map_err(|error| {
                    DirectSelectionError::HaltFetch(Box::new(
                        DirectHaltFetchError::Identity(error),
                    ))
                }),
            Self::HaltRegisters(target) => {
                NativeArtifactKey::new(program, target)
                    .map(PreparedDirectTarget::HaltRegisters)
                    .map_err(|error| {
                        DirectSelectionError::HaltRegisters(Box::new(
                            DirectHaltRegistersError::Identity(error),
                        ))
                    })
            },
            Self::InitialHalt(target) => {
                NativeArtifactKey::new(program, target)
                    .map(PreparedDirectTarget::InitialHalt)
                    .map_err(|error| {
                        DirectSelectionError::InitialHalt(Box::new(
                            DirectInitialHaltError::Identity(error),
                        ))
                    })
            },
            Self::NonGraphical(target) => {
                NativeArtifactKey::new(program, target)
                    .map(PreparedDirectTarget::NonGraphical)
                    .map_err(|error| {
                        DirectSelectionError::NonGraphical(Box::new(
                            DirectNonGraphicalError::Identity(error),
                        ))
                    })
            },
            Self::NoOperation(target) => {
                NativeArtifactKey::new(program, target)
                    .map(PreparedDirectTarget::NoOperation)
                    .map_err(|error| {
                        DirectSelectionError::NoOperation(Box::new(
                            DirectNoOperationError::Identity(error),
                        ))
                    })
            },
        }
    }
}

impl VerifiedDirectNativeArtifact {
    /// Returns the exact selected native artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        match self {
            Self::Deopt(artifact) => artifact.key(),
            Self::HaltFetch(artifact) => artifact.key(),
            Self::HaltRegisters(artifact) => artifact.key(),
            Self::InitialHalt(artifact) => artifact.key(),
            Self::NonGraphical(artifact) => artifact.key(),
            Self::NoOperation(artifact) => artifact.key(),
        }
    }

    /// Returns which reviewed direct template was selected.
    #[must_use]
    pub const fn kind(&self) -> DirectNativeKind {
        match self {
            Self::Deopt(_artifact) => DirectNativeKind::Deopt,
            Self::HaltFetch(_artifact) => DirectNativeKind::HaltFetch,
            Self::HaltRegisters(_artifact) => DirectNativeKind::HaltRegisters,
            Self::InitialHalt(_artifact) => DirectNativeKind::InitialHalt,
            Self::NonGraphical(_artifact) => DirectNativeKind::NonGraphical,
            Self::NoOperation(_artifact) => DirectNativeKind::NoOperation,
        }
    }

    /// Returns verified object bytes for the selected template.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        match self {
            Self::Deopt(artifact) => artifact.object(),
            Self::HaltFetch(artifact) => artifact.object(),
            Self::HaltRegisters(artifact) => artifact.object(),
            Self::InitialHalt(artifact) => artifact.object(),
            Self::NonGraphical(artifact) => artifact.object(),
            Self::NoOperation(artifact) => artifact.object(),
        }
    }

    /// Returns the exact selected Windows target triple.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        match self {
            Self::Deopt(artifact) => artifact.target_triple(),
            Self::HaltFetch(artifact) => artifact.target_triple(),
            Self::HaltRegisters(artifact) => artifact.target_triple(),
            Self::InitialHalt(artifact) => artifact.target_triple(),
            Self::NonGraphical(artifact) => artifact.target_triple(),
            Self::NoOperation(artifact) => artifact.target_triple(),
        }
    }
}

fn emit_verified_halt_fetch(
    key: NativeArtifactKey,
    program: &RegionEffectProgram,
) -> VerifiedDirectSelectionResult<'_> {
    let selected = validate_halt_fetch_program(program)
        .map_err(|error| DirectSelectionError::HaltFetch(Box::new(error)))?;
    validate_halt_fetch_target(key.target())
        .map_err(|error| DirectSelectionError::HaltFetch(Box::new(error)))?;
    let artifact = emit_direct_halt_fetch_with_key(key, selected)
        .map_err(|error| DirectSelectionError::HaltFetch(Box::new(error)))?;
    let verified = verify_direct_halt_fetch(&artifact, program)
        .map_err(|error| DirectSelectionError::HaltFetch(Box::new(error)))?;
    Ok(VerifiedDirectNativeArtifact::HaltFetch(verified))
}

fn emit_verified_non_graphical(
    key: NativeArtifactKey,
    program: &RegionEffectProgram,
) -> VerifiedDirectSelectionResult<'_> {
    let selected = validate_non_graphical_program(program)
        .map_err(|error| DirectSelectionError::NonGraphical(Box::new(error)))?;
    validate_non_graphical_target(key.target())
        .map_err(|error| DirectSelectionError::NonGraphical(Box::new(error)))?;
    let artifact = emit_direct_non_graphical_with_key(key, selected)
        .map_err(|error| DirectSelectionError::NonGraphical(Box::new(error)))?;
    let verified = verify_direct_non_graphical(&artifact, program)
        .map_err(|error| DirectSelectionError::NonGraphical(Box::new(error)))?;
    Ok(VerifiedDirectNativeArtifact::NonGraphical(verified))
}

fn emit_verified_no_operation(
    key: NativeArtifactKey,
    program: &RegionEffectProgram,
) -> VerifiedDirectSelectionResult<'_> {
    let selected = validate_no_operation_program(program)
        .map_err(|error| DirectSelectionError::NoOperation(Box::new(error)))?;
    validate_no_operation_target(key.target())
        .map_err(|error| DirectSelectionError::NoOperation(Box::new(error)))?;
    let artifact = emit_direct_no_operation_with_key(key, selected)
        .map_err(|error| DirectSelectionError::NoOperation(Box::new(error)))?;
    let verified = verify_direct_no_operation(&artifact, program)
        .map_err(|error| DirectSelectionError::NoOperation(Box::new(error)))?;
    Ok(VerifiedDirectNativeArtifact::NoOperation(verified))
}

/// Selects the narrowest semantically admitted direct native template.
///
/// Program/profile capacity and runtime preflight occur before host/backend
/// selection. Exact halt, fetched-terminal, and no-op subsets select reviewed
/// state-applying fast paths; every remaining IR selects verified
/// deoptimization. Selection never converts profile, emitter, or verifier
/// errors into fallback; only admitted program shape controls which backend
/// identity is constructed.
///
/// # Errors
///
/// Returns [`DirectSelectionError`] for unsupported program/profile/runtime,
/// host format, or any emission/verification failure after deterministic
/// template selection.
pub fn select_verified_direct_native<'requirement>(
    program: &'requirement RegionEffectProgram,
    runtime: &'static RuntimeCapability,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> VerifiedDirectSelectionResult<'requirement> {
    preflight_direct_selection(program, runtime)?;
    if host_os != HostOperatingSystem::Windows {
        return Err(DirectSelectionError::TargetFormat);
    }
    select_direct_target(program, host_os, host_isa)
        .prepare(program)?
        .emit_verified(program)
}

/// Selects a profile-preflighted direct or interpreter execution plan.
///
/// Unsupported direct host formats are an expected capability absence and map
/// to the interpreter. Profile errors and any failure after backend selection
/// remain errors; they are never converted to interpreter fallback.
///
/// # Errors
///
/// Returns [`DirectSelectionError`] for unsupported program/profile/runtime or
/// any direct emission/admission failure other than host-format absence.
pub fn select_preflighted_execution_tier<'requirement>(
    program: &'requirement RegionEffectProgram,
    runtime: &'static RuntimeCapability,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<PreflightedExecutionTier, DirectSelectionError<'requirement>> {
    match select_verified_direct_native(program, runtime, host_os, host_isa) {
        Ok(artifact) => {
            Ok(PreflightedExecutionTier::Direct(Box::new(artifact)))
        },
        Err(DirectSelectionError::TargetFormat) => {
            Ok(PreflightedExecutionTier::Interpreter)
        },
        Err(error) => Err(error),
    }
}

/// Selects a cache-aware profile-preflighted direct or interpreter plan.
///
/// Profile preflight and host-format selection happen before cache lookup. Only
/// semantically admitted direct artifacts can enter the caller-owned cache.
///
/// # Errors
///
/// Returns [`DirectSelectionError`] for unsupported program/profile/runtime or
/// any direct emission/admission failure other than host-format absence.
pub fn select_cached_preflighted_execution_tier<'requirement>(
    program: &'requirement RegionEffectProgram,
    runtime: &'static RuntimeCapability,
    host: DirectHost,
    cache: &mut VerifiedDirectNativeCache,
) -> Result<CachedPreflightedExecutionTier, DirectSelectionError<'requirement>>
{
    preflight_direct_selection(program, runtime)?;
    if host.operating_system != HostOperatingSystem::Windows {
        return Ok(CachedPreflightedExecutionTier::Interpreter);
    }
    let prepared =
        select_direct_target(program, host.operating_system, host.isa)
            .prepare(program)?;
    if let Some(artifact) = cache.entries.get(prepared.key()) {
        return Ok(CachedPreflightedExecutionTier::Direct {
            artifact: Arc::clone(artifact),
            cache: DirectCacheDisposition::Hit,
        });
    }
    let artifact = Arc::new(prepared.emit_verified(program)?);
    let inserted_key = artifact.key().clone();
    let _replaced = cache.entries.insert(inserted_key, Arc::clone(&artifact));
    Ok(CachedPreflightedExecutionTier::Direct {
        artifact,
        cache: DirectCacheDisposition::Inserted,
    })
}

/// Emits a deterministic direct native object that always requests deopt.
///
/// The resulting object is still untrusted until [`verify_direct_deopt_stub`]
/// performs structural admission and exact canonical-byte verification.
///
/// # Errors
///
/// Returns [`DirectDeoptError`] for unsupported target assumptions or an
/// unrepresentable native identity.
pub fn emit_direct_deopt_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectDeoptError> {
    validate_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_deopt_with_key(key)
}

/// Emits a one-step halt fast path bound to one exact entry observation.
///
/// # Errors
///
/// Returns [`DirectHaltRegistersError`] when IR/target is outside this subset.
pub fn emit_direct_halt_registers_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectHaltRegistersError> {
    let observation = validate_halt_registers_program(program)?;
    validate_halt_registers_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_halt_registers_with_key(key, observation)
}

/// Emits the exact graphical halt-fetch termination fast path.
///
/// # Errors
///
/// Returns [`DirectHaltFetchError`] when IR/target is outside this subset.
pub fn emit_direct_halt_fetch_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectHaltFetchError> {
    let selected = validate_halt_fetch_program(program)?;
    validate_halt_fetch_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_halt_fetch_with_key(key, selected)
}

/// Emits a direct native fast path for the exact initial-halt IR subset.
///
/// # Errors
///
/// Returns [`DirectInitialHaltError`] when the program/target is outside the
/// reviewed subset or native identity cannot be represented.
pub fn emit_direct_initial_halt_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectInitialHaltError> {
    validate_initial_halt_program(program)?;
    validate_initial_halt_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_initial_halt_with_key(key)
}

/// Emits the exact non-graphical fetch termination fast path.
///
/// # Errors
///
/// Returns [`DirectNonGraphicalError`] when IR/target is outside this subset.
pub fn emit_direct_non_graphical_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectNonGraphicalError> {
    let selected = validate_non_graphical_program(program)?;
    validate_non_graphical_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_non_graphical_with_key(key, selected)
}

/// Emits one exact no-operation fetch/encryption/advance fast path.
///
/// # Errors
///
/// Returns [`DirectNoOperationError`] when IR/target is outside this subset.
pub fn emit_direct_no_operation_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectNoOperationError> {
    let selected = validate_no_operation_program(program)?;
    validate_no_operation_target(&target)?;
    let key = NativeArtifactKey::new(program, target)?;
    emit_direct_no_operation_with_key(key, selected)
}

fn emit_direct_deopt_with_key(
    key: NativeArtifactKey,
) -> Result<UntrustedNativeObjectArtifact, DirectDeoptError> {
    let triple = target_triple(key.target().host_isa());
    let object = canonical_coff(&key)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

fn emit_direct_halt_registers_with_key(
    key: NativeArtifactKey,
    observation: ProfileMachineObservation,
) -> Result<UntrustedNativeObjectArtifact, DirectHaltRegistersError> {
    let triple = target_triple(key.target().host_isa());
    let object = halt_registers_coff(&key, observation)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

fn emit_direct_halt_fetch_with_key(
    key: NativeArtifactKey,
    selected: DirectFetchedTerminalProgram,
) -> Result<UntrustedNativeObjectArtifact, DirectHaltFetchError> {
    let triple = target_triple(key.target().host_isa());
    let object = halt_fetch_coff(&key, selected)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

fn emit_direct_initial_halt_with_key(
    key: NativeArtifactKey,
) -> Result<UntrustedNativeObjectArtifact, DirectInitialHaltError> {
    let triple = target_triple(key.target().host_isa());
    let object = initial_halt_coff(&key)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

fn emit_direct_non_graphical_with_key(
    key: NativeArtifactKey,
    selected: DirectFetchedTerminalProgram,
) -> Result<UntrustedNativeObjectArtifact, DirectNonGraphicalError> {
    let triple = target_triple(key.target().host_isa());
    let object = non_graphical_coff(&key, selected)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

fn emit_direct_no_operation_with_key(
    key: NativeArtifactKey,
    selected: DirectNoOperationProgram,
) -> Result<UntrustedNativeObjectArtifact, DirectNoOperationError> {
    let triple = target_triple(key.target().host_isa());
    let object = no_operation_coff(&key, selected)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

/// Promotes only the exact canonical deopt-only object to semantic authority.
///
/// Byte equality here is semantic validation because v1 admits exactly two
/// reviewed instruction sequences: each sets the integer return register to the
/// guard-miss status `1` and returns without reading or writing guest state.
///
/// # Errors
///
/// Returns [`DirectDeoptError`] when target assumptions, COFF structure, or any
/// object byte differs from the canonical deoptimization stub.
pub fn verify_direct_deopt_stub(
    artifact: &UntrustedNativeObjectArtifact,
) -> Result<VerifiedDeoptNativeObjectArtifact, DirectDeoptError> {
    validate_target(artifact.key().target())?;
    let admitted = structurally_admit_coff(artifact)?;
    let expected = canonical_coff(artifact.key())?;
    if admitted.object() != expected {
        return Err(DirectDeoptError::ObjectBytes);
    }
    Ok(VerifiedDeoptNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical exact-observation halt object for its IR.
///
/// # Errors
///
/// Returns [`DirectHaltRegistersError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_halt_registers(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedHaltRegistersNativeObjectArtifact, DirectHaltRegistersError>
{
    let observation = validate_halt_registers_program(program)?;
    validate_halt_registers_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectHaltRegistersError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = halt_registers_coff(artifact.key(), observation)?;
    if admitted.object() != expected {
        return Err(DirectHaltRegistersError::ObjectBytes);
    }
    Ok(VerifiedHaltRegistersNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical graphical halt-fetch object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectHaltFetchError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_halt_fetch(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedHaltFetchNativeObjectArtifact, DirectHaltFetchError> {
    let selected = validate_halt_fetch_program(program)?;
    validate_halt_fetch_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectHaltFetchError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = halt_fetch_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectHaltFetchError::ObjectBytes);
    }
    Ok(VerifiedHaltFetchNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the exact canonical initial-halt object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectInitialHaltError`] when IR shape, identity, COFF structure,
/// or any object byte differs from the reviewed initial-halt contract.
pub fn verify_direct_initial_halt(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedInitialHaltNativeObjectArtifact, DirectInitialHaltError> {
    validate_initial_halt_program(program)?;
    validate_initial_halt_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectInitialHaltError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = initial_halt_coff(artifact.key())?;
    if admitted.object() != expected {
        return Err(DirectInitialHaltError::ObjectBytes);
    }
    Ok(VerifiedInitialHaltNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical non-graphical object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectNonGraphicalError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_non_graphical(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedNonGraphicalNativeObjectArtifact, DirectNonGraphicalError> {
    let selected = validate_non_graphical_program(program)?;
    validate_non_graphical_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectNonGraphicalError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = non_graphical_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectNonGraphicalError::ObjectBytes);
    }
    Ok(VerifiedNonGraphicalNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical no-operation object for its exact IR.
///
/// # Errors
///
/// Returns [`DirectNoOperationError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_no_operation(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedNoOperationNativeObjectArtifact, DirectNoOperationError> {
    let selected = validate_no_operation_program(program)?;
    validate_no_operation_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectNoOperationError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected = no_operation_coff(artifact.key(), selected)?;
    if admitted.object() != expected {
        return Err(DirectNoOperationError::ObjectBytes);
    }
    Ok(VerifiedNoOperationNativeObjectArtifact { artifact: admitted })
}

fn canonical_coff(
    key: &NativeArtifactKey,
) -> Result<Vec<u8>, DirectDeoptError> {
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => aarch64::deopt_code(),
        HostIsa::X86_64 => x86_64::deopt_code(),
    };
    build_minimal_coff(key, text).ok_or(DirectDeoptError::ObjectBytes)
}

fn build_minimal_coff(key: &NativeArtifactKey, text: &[u8]) -> Option<Vec<u8>> {
    let (machine, text_characteristics) = match key.target().host_isa() {
        HostIsa::AArch64 => (IMAGE_FILE_MACHINE_ARM64, IMAGE_SCN_ARM64_TEXT),
        HostIsa::X86_64 => (IMAGE_FILE_MACHINE_AMD64, IMAGE_SCN_X86_TEXT),
    };
    let metadata = canonical_profile_metadata(key)?;
    let section_headers = COFF_SECTION_BYTES.checked_mul(2)?;
    let text_start = COFF_HEADER_BYTES.checked_add(section_headers)?;
    let metadata_start = text_start.checked_add(text.len())?;
    let symbol_start = metadata_start.checked_add(metadata.len())?;
    let symbol_start_u32 = u32::try_from(symbol_start).ok()?;
    let text_start_u32 = u32::try_from(text_start).ok()?;
    let metadata_start_u32 = u32::try_from(metadata_start).ok()?;
    let text_len = u32::try_from(text.len()).ok()?;
    let metadata_len = u32::try_from(metadata.len()).ok()?;
    let string_length =
        4usize.checked_add(REQUIRED_ENTRY.len())?.checked_add(1)?;
    let string_length_u32 = u32::try_from(string_length).ok()?;
    let capacity = symbol_start
        .checked_add(COFF_SYMBOL_BYTES)?
        .checked_add(string_length)?;

    let mut object = Vec::with_capacity(capacity);
    push_coff_header(&mut object, machine, symbol_start_u32);
    push_text_section(
        &mut object,
        text_len,
        text_start_u32,
        text_characteristics,
    );
    push_profile_section(&mut object, metadata_len, metadata_start_u32);
    object.extend_from_slice(text);
    object.extend_from_slice(&metadata);
    push_entry_symbol(&mut object, string_length_u32);
    Some(object)
}

fn push_coff_header(output: &mut Vec<u8>, machine: u16, symbol_start: u32) {
    push_u16(output, machine);
    push_u16(output, 2);
    push_u32(output, 0);
    push_u32(output, symbol_start);
    push_u32(output, 1);
    push_u16(output, 0);
    push_u16(output, 0);
}

fn push_profile_section(output: &mut Vec<u8>, raw_len: u32, raw_start: u32) {
    output.extend_from_slice(b".mbprof\0");
    push_u32(output, 0);
    push_u32(output, 0);
    push_u32(output, raw_len);
    push_u32(output, raw_start);
    push_u32(output, 0);
    push_u32(output, 0);
    push_u16(output, 0);
    push_u16(output, 0);
    push_u32(output, IMAGE_SCN_PROFILE_METADATA);
}

fn push_text_section(
    output: &mut Vec<u8>,
    raw_len: u32,
    raw_start: u32,
    characteristics: u32,
) {
    output.extend_from_slice(b".text\0\0\0");
    push_u32(output, 0);
    push_u32(output, 0);
    push_u32(output, raw_len);
    push_u32(output, raw_start);
    push_u32(output, 0);
    push_u32(output, 0);
    push_u16(output, 0);
    push_u16(output, 0);
    push_u32(output, characteristics);
}

fn push_entry_symbol(output: &mut Vec<u8>, string_length: u32) {
    push_u32(output, 0);
    push_u32(output, 4);
    push_u32(output, 0);
    push_u16(output, 1);
    push_u16(output, IMAGE_SYM_DTYPE_FUNCTION);
    output.push(IMAGE_SYM_CLASS_EXTERNAL);
    output.push(0);
    push_u32(output, string_length);
    output.extend_from_slice(REQUIRED_ENTRY.as_bytes());
    output.push(0);
}

fn halt_registers_coff(
    key: &NativeArtifactKey,
    observation: ProfileMachineObservation,
) -> Result<Vec<u8>, DirectHaltRegistersError> {
    let direct = direct_entry_observation(observation)
        .ok_or(DirectHaltRegistersError::ObjectBytes)?;
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => aarch64::halt_observation_code(direct),
        HostIsa::X86_64 => x86_64::halt_observation_code(direct),
    }
    .ok_or(DirectHaltRegistersError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectHaltRegistersError::ObjectBytes)
}

fn halt_fetch_coff(
    key: &NativeArtifactKey,
    selected: DirectFetchedTerminalProgram,
) -> Result<Vec<u8>, DirectHaltFetchError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectHaltFetchError::ObjectBytes)?;
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::halt_fetch_code(observation, selected.live_in.value)
        },
        HostIsa::X86_64 => {
            x86_64::halt_fetch_code(observation, selected.live_in.value)
        },
    }
    .ok_or(DirectHaltFetchError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectHaltFetchError::ObjectBytes)
}

fn non_graphical_coff(
    key: &NativeArtifactKey,
    selected: DirectFetchedTerminalProgram,
) -> Result<Vec<u8>, DirectNonGraphicalError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectNonGraphicalError::ObjectBytes)?;
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => {
            aarch64::non_graphical_code(observation, selected.live_in.value)
        },
        HostIsa::X86_64 => {
            x86_64::non_graphical_code(observation, selected.live_in.value)
        },
    }
    .ok_or(DirectNonGraphicalError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectNonGraphicalError::ObjectBytes)
}

fn no_operation_coff(
    key: &NativeArtifactKey,
    selected: DirectNoOperationProgram,
) -> Result<Vec<u8>, DirectNoOperationError> {
    let observation = direct_entry_observation(selected.observation)
        .ok_or(DirectNoOperationError::ObjectBytes)?;
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => aarch64::no_operation_code(
            observation,
            selected.live_in.value,
            DirectNoOperationCommit {
                encrypted_value: selected.encrypted_value,
                next_code_pointer: selected.next_code_pointer,
                next_data_pointer: selected.next_data_pointer,
            },
        ),
        HostIsa::X86_64 => x86_64::no_operation_code(
            observation,
            selected.live_in.value,
            DirectNoOperationCommit {
                encrypted_value: selected.encrypted_value,
                next_code_pointer: selected.next_code_pointer,
                next_data_pointer: selected.next_data_pointer,
            },
        ),
    }
    .ok_or(DirectNoOperationError::ObjectBytes)?;
    build_minimal_coff(key, &text).ok_or(DirectNoOperationError::ObjectBytes)
}

fn initial_halt_coff(
    key: &NativeArtifactKey,
) -> Result<Vec<u8>, DirectInitialHaltError> {
    let text = match key.target().host_isa() {
        HostIsa::AArch64 => aarch64::initial_halt_code(),
        HostIsa::X86_64 => x86_64::initial_halt_code(),
    };
    build_minimal_coff(key, text).ok_or(DirectInitialHaltError::ObjectBytes)
}

fn direct_entry_observation(
    observation: ProfileMachineObservation,
) -> Option<DirectEntryObservation> {
    let registers = observation.registers;
    Some(DirectEntryObservation {
        accumulator: registers.accumulator,
        code_pointer: registers.code_pointer,
        data_pointer: registers.data_pointer,
        input_consumed: u64::try_from(observation.input_consumed).ok()?,
        output_len: u64::try_from(observation.output_len).ok()?,
    })
}

fn is_zero_observation(observation: ProfileMachineObservation) -> bool {
    observation.input_consumed == 0
        && observation.output_len == 0
        && observation.registers == ProfileRegisters::default()
        && observation.termination.is_none()
}

fn push_u16(output: &mut Vec<u8>, value: u16) {
    output.extend_from_slice(&value.to_le_bytes());
}

fn push_u32(output: &mut Vec<u8>, value: u32) {
    output.extend_from_slice(&value.to_le_bytes());
}

fn preflight_direct_selection<'requirement>(
    program: &'requirement RegionEffectProgram,
    runtime: &'static RuntimeCapability,
) -> Result<(), DirectSelectionError<'requirement>> {
    preflight_portable_profile_requirement(
        &program.profile_id,
        &program.profile_requirement,
        program.required_memory_words(),
        runtime,
    )
    .map_err(|error| DirectSelectionError::Profile(Box::new(error)))
}

fn select_direct_target(
    program: &RegionEffectProgram,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> SelectedDirectTarget {
    if validate_initial_halt_program(program).is_ok() {
        return SelectedDirectTarget::InitialHalt(direct_target(
            DIRECT_INITIAL_HALT_BACKEND_ID,
            DIRECT_INITIAL_HALT_BACKEND_REVISION,
            host_os,
            host_isa,
        ));
    }
    if validate_halt_registers_program(program).is_ok() {
        return SelectedDirectTarget::HaltRegisters(direct_target(
            DIRECT_HALT_REGISTERS_BACKEND_ID,
            DIRECT_HALT_REGISTERS_BACKEND_REVISION,
            host_os,
            host_isa,
        ));
    }
    if validate_halt_fetch_program(program).is_ok() {
        return SelectedDirectTarget::HaltFetch(direct_target(
            DIRECT_HALT_FETCH_BACKEND_ID,
            DIRECT_HALT_FETCH_BACKEND_REVISION,
            host_os,
            host_isa,
        ));
    }
    if validate_non_graphical_program(program).is_ok() {
        return SelectedDirectTarget::NonGraphical(direct_target(
            DIRECT_NON_GRAPHICAL_BACKEND_ID,
            DIRECT_NON_GRAPHICAL_BACKEND_REVISION,
            host_os,
            host_isa,
        ));
    }
    if validate_no_operation_program(program).is_ok() {
        return SelectedDirectTarget::NoOperation(direct_target(
            DIRECT_NO_OPERATION_BACKEND_ID,
            DIRECT_NO_OPERATION_BACKEND_REVISION,
            host_os,
            host_isa,
        ));
    }
    SelectedDirectTarget::Deopt(direct_target(
        DIRECT_DEOPT_BACKEND_ID,
        DIRECT_DEOPT_BACKEND_REVISION,
        host_os,
        host_isa,
    ))
}

fn direct_target(
    backend_id: &str,
    backend_revision: u32,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(backend_id),
        backend_revision,
        host_isa,
        host_os,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

const fn target_triple(isa: HostIsa) -> &'static str {
    match isa {
        HostIsa::AArch64 => "aarch64-pc-windows-msvc",
        HostIsa::X86_64 => "x86_64-pc-windows-msvc",
    }
}

fn fetched_terminal_program(
    program: &RegionEffectProgram,
    reason: Termination,
) -> Option<DirectFetchedTerminalProgram> {
    if program.format_version != EFFECT_IR_VERSION
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || program.memory_live_ins.len() != 1
        || program.effects.len() != 1
        || program.outcome != (RunOutcome::Terminated { reason, steps: 1 })
    {
        return None;
    }
    let effect = program.effects.first()?;
    let live_in = program.memory_live_ins.first().copied()?;
    let expected_after = ProfileMachineObservation {
        termination: Some(reason),
        ..effect.before
    };
    if effect.before.termination.is_some()
        || effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta != ProfileMemoryDelta::default()
        || live_in.address != effect.before.registers.code_pointer
    {
        return None;
    }
    Some(DirectFetchedTerminalProgram {
        live_in,
        observation: effect.before,
    })
}

fn validate_halt_fetch_program(
    program: &RegionEffectProgram,
) -> Result<DirectFetchedTerminalProgram, DirectHaltFetchError> {
    let selected =
        fetched_terminal_program(program, Termination::HaltInstruction)
            .ok_or(DirectHaltFetchError::ProgramShape)?;
    if decode_profile_instruction(
        selected.live_in.value,
        selected.observation.registers.code_pointer,
    ) == Some(b'v')
    {
        Ok(selected)
    } else {
        Err(DirectHaltFetchError::ProgramShape)
    }
}

fn validate_halt_fetch_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectHaltFetchError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectHaltFetchError::TargetFormat);
    }
    if target.backend_id() != DIRECT_HALT_FETCH_BACKEND_ID
        || target.backend_revision() != DIRECT_HALT_FETCH_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectHaltFetchError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectHaltFetchError::TargetFeatures);
    }
    Ok(())
}

fn validate_non_graphical_program(
    program: &RegionEffectProgram,
) -> Result<DirectFetchedTerminalProgram, DirectNonGraphicalError> {
    let selected =
        fetched_terminal_program(program, Termination::NonGraphicalCell)
            .ok_or(DirectNonGraphicalError::ProgramShape)?;
    if profile_cell_is_graphical(selected.live_in.value) {
        Err(DirectNonGraphicalError::ProgramShape)
    } else {
        Ok(selected)
    }
}

fn validate_non_graphical_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectNonGraphicalError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectNonGraphicalError::TargetFormat);
    }
    if target.backend_id() != DIRECT_NON_GRAPHICAL_BACKEND_ID
        || target.backend_revision() != DIRECT_NON_GRAPHICAL_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectNonGraphicalError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectNonGraphicalError::TargetFeatures);
    }
    Ok(())
}

fn validate_no_operation_program(
    program: &RegionEffectProgram,
) -> Result<DirectNoOperationProgram, DirectNoOperationError> {
    if program.format_version != EFFECT_IR_VERSION
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || program.memory_live_ins.len() != 1
        || program.effects.len() != 1
        || program.outcome != (RunOutcome::BudgetExhausted { steps: 1 })
    {
        return Err(DirectNoOperationError::ProgramShape);
    }
    let effect = program
        .effects
        .first()
        .ok_or(DirectNoOperationError::ProgramShape)?;
    let live_in = program
        .memory_live_ins
        .first()
        .copied()
        .ok_or(DirectNoOperationError::ProgramShape)?;
    derive_no_operation_program(program, *effect, live_in)
        .ok_or(DirectNoOperationError::ProgramShape)
}

fn derive_no_operation_program(
    program: &RegionEffectProgram,
    effect: EffectOp,
    live_in: MemoryLiveIn,
) -> Option<DirectNoOperationProgram> {
    let before = effect.before;
    let memory_words = program.profile_requirement.memory_words;
    let next_code_pointer =
        profile_pointer_successor(before.registers.code_pointer, memory_words)?;
    let next_data_pointer =
        profile_pointer_successor(before.registers.data_pointer, memory_words)?;
    let encrypted_value = encrypt_profile_cell(live_in.value)?;
    let expected_after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: before.registers.accumulator,
            code_pointer: next_code_pointer,
            data_pointer: next_data_pointer,
        },
        ..before
    };
    let expected_encryption =
        (live_in.value != encrypted_value).then_some(ProfileMemoryWrite {
            address: before.registers.code_pointer,
            after: encrypted_value,
            before: live_in.value,
        });
    let expected_delta = ProfileMemoryDelta {
        data: None,
        encryption: expected_encryption,
    };
    if before.termination.is_some()
        || effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta != expected_delta
        || live_in.address != before.registers.code_pointer
        || !profile_cell_decodes_to_no_operation(
            live_in.value,
            before.registers.code_pointer,
        )
    {
        return None;
    }
    Some(DirectNoOperationProgram {
        encrypted_value,
        live_in,
        next_code_pointer,
        next_data_pointer,
        observation: before,
    })
}

fn validate_no_operation_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectNoOperationError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectNoOperationError::TargetFormat);
    }
    if target.backend_id() != DIRECT_NO_OPERATION_BACKEND_ID
        || target.backend_revision() != DIRECT_NO_OPERATION_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectNoOperationError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectNoOperationError::TargetFeatures);
    }
    Ok(())
}

fn validate_halt_registers_program(
    program: &RegionEffectProgram,
) -> Result<ProfileMachineObservation, DirectHaltRegistersError> {
    if program.format_version != EFFECT_IR_VERSION
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || !program.memory_live_ins.is_empty()
        || program.effects.len() != 1
        || program.outcome
            != (RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 1,
            })
    {
        return Err(DirectHaltRegistersError::ProgramShape);
    }
    let effect = program
        .effects
        .first()
        .ok_or(DirectHaltRegistersError::ProgramShape)?;
    let expected_after = ProfileMachineObservation {
        termination: Some(Termination::HaltInstruction),
        ..effect.before
    };
    if effect.before.termination.is_some()
        || effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta != ProfileMemoryDelta::default()
    {
        return Err(DirectHaltRegistersError::ProgramShape);
    }
    Ok(effect.before)
}

fn validate_halt_registers_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectHaltRegistersError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectHaltRegistersError::TargetFormat);
    }
    if target.backend_id() != DIRECT_HALT_REGISTERS_BACKEND_ID
        || target.backend_revision() != DIRECT_HALT_REGISTERS_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectHaltRegistersError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectHaltRegistersError::TargetFeatures);
    }
    Ok(())
}

fn validate_initial_halt_program(
    program: &RegionEffectProgram,
) -> Result<(), DirectInitialHaltError> {
    if program.format_version != EFFECT_IR_VERSION
        || !program.fits_declared_profile_capacity()
        || program.step_budget != 1
        || !program.memory_live_ins.is_empty()
        || program.effects.len() != 1
        || program.outcome
            != (RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 1,
            })
    {
        return Err(DirectInitialHaltError::ProgramShape);
    }
    let effect = program
        .effects
        .first()
        .ok_or(DirectInitialHaltError::ProgramShape)?;
    let expected_after = ProfileMachineObservation {
        termination: Some(Termination::HaltInstruction),
        ..effect.before
    };
    if !is_zero_observation(effect.before)
        || effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta != ProfileMemoryDelta::default()
    {
        return Err(DirectInitialHaltError::ProgramShape);
    }
    Ok(())
}

fn validate_initial_halt_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectInitialHaltError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectInitialHaltError::TargetFormat);
    }
    if target.backend_id() != DIRECT_INITIAL_HALT_BACKEND_ID
        || target.backend_revision() != DIRECT_INITIAL_HALT_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectInitialHaltError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectInitialHaltError::TargetFeatures);
    }
    Ok(())
}

fn validate_target(
    target: &NativeTargetIdentity,
) -> Result<(), DirectDeoptError> {
    if target.host_os() != HostOperatingSystem::Windows {
        return Err(DirectDeoptError::TargetFormat);
    }
    if target.backend_id() != DIRECT_DEOPT_BACKEND_ID
        || target.backend_revision() != DIRECT_DEOPT_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(DirectDeoptError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(DirectDeoptError::TargetFeatures);
    }
    Ok(())
}
