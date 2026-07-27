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
//   - Canonical direct deopt/halt objects and byte-exact semantic admission.
// - Must-Not:
//   - Lower unsupported effects, bypass verifier guards, or trust compiler
//     output.
// - Allows:
//   - Inputs: portable region IR and exact Windows native target identity.
//   - Outputs: canonical COFF candidates and verified deopt-only artifacts.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when general region-effect instruction selection outgrows
//     templates.
// - Merge-When:
//   - Merge when all direct emitters share one reviewed instruction template.
// - Summary:
//   - Owns byte-canonical deopt and first state-applying native templates.
// - Description:
//   - Emits reviewed x86-64/AArch64 objects for exact verified IR subsets.
// - Usage:
//   - Provides a safe deopt floor plus exact reviewed one-step halt fast paths.
// - Defaults:
//   - Unsupported IR is rejected; no direct template is selected implicitly.
//
// Related documents:
// - docs/technical/adr/tiered-native-execution.md
// - docs/technical/adr/verification-trust-boundary.md
//
// Large file:
//   - true

//! Canonical direct native templates with byte-exact semantic verification.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    ProfileMachineObservation, ProfileMemoryDelta, ProfileRegisters,
    RunOutcome, Termination,
};

use super::{
    CoffAdmissionError, NATIVE_REGION_ABI_REVISION,
    StructurallyAdmittedNativeObjectArtifact, UntrustedNativeObjectArtifact,
    aarch64, structurally_admit_coff, x86_64,
};
use crate::execution_cache::{
    HostIsa, HostOperatingSystem, NativeArtifactKey, NativeTargetConfig,
    NativeTargetIdentity,
};
use crate::execution_ir::{
    EFFECT_IR_VERSION, IrEncodingError, RegionEffectProgram,
};

const COFF_HEADER_BYTES: usize = 20;
const COFF_SECTION_BYTES: usize = 40;
const COFF_SYMBOL_BYTES: usize = 18;
const IMAGE_FILE_MACHINE_AMD64: u16 = 0x8664;
const IMAGE_FILE_MACHINE_ARM64: u16 = 0xaa64;
const IMAGE_SCN_X86_TEXT: u32 = 0x6050_0020;
const IMAGE_SCN_ARM64_TEXT: u32 = 0x6030_0020;
const IMAGE_SYM_CLASS_EXTERNAL: u8 = 2;
const IMAGE_SYM_DTYPE_FUNCTION: u16 = 0x0020;
const REQUIRED_ENTRY: &str = "malbolge_native_region_apply";
/// Backend identity for the first direct, semantically admitted native tier.
pub const DIRECT_DEOPT_BACKEND_ID: &str = "direct-deopt-stub";
/// Direct deoptimization-stub code-generation revision.
pub const DIRECT_DEOPT_BACKEND_REVISION: u32 = 1;
/// Backend identity for the first state-applying direct native fast path.
pub const DIRECT_INITIAL_HALT_BACKEND_ID: &str = "direct-initial-halt";
/// Direct initial-halt code-generation revision.
pub const DIRECT_INITIAL_HALT_BACKEND_REVISION: u32 = 1;
/// Backend identity for arbitrary-register one-step direct halt.
pub const DIRECT_HALT_REGISTERS_BACKEND_ID: &str = "direct-halt-registers";
/// Direct arbitrary-register halt code-generation revision.
pub const DIRECT_HALT_REGISTERS_BACKEND_REVISION: u32 = 1;

/// Failure while emitting or verifying the direct deoptimization stub.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectDeoptError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity could not encode the portable program.
    Identity(IrEncodingError),
    /// Object bytes differ from the canonical direct deopt object.
    ObjectBytes,
    /// Target backend/revision/native ABI is not the direct deopt contract.
    TargetBackend,
    /// Direct deopt v1 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct deopt v1 emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectDeoptError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => "direct deopt COFF structure was rejected",
            Self::Identity(_error) => {
                "direct deopt native identity encoding failed"
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

impl From<IrEncodingError> for DirectDeoptError {
    fn from(error: IrEncodingError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying arbitrary-register direct halt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectHaltRegistersError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity could not encode the portable program.
    Identity(IrEncodingError),
    /// Object bytes differ from the canonical register-bound halt object.
    ObjectBytes,
    /// Portable IR is outside the exact register-bound halt subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not the register-halt contract.
    TargetBackend,
    /// Register-halt v1 has no target-specific feature specializations.
    TargetFeatures,
    /// Register-halt v1 emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectHaltRegistersError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct register-halt COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct register-halt identity encoding failed"
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

impl From<IrEncodingError> for DirectHaltRegistersError {
    fn from(error: IrEncodingError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying the direct initial-halt fast path.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectInitialHaltError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity could not encode the portable program.
    Identity(IrEncodingError),
    /// Object bytes differ from the canonical direct initial-halt object.
    ObjectBytes,
    /// Portable IR is outside the exact initial-halt subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not the initial-halt contract.
    TargetBackend,
    /// Direct initial-halt v1 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct initial-halt v1 emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectInitialHaltError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct initial-halt COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct initial-halt identity encoding failed"
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

impl From<IrEncodingError> for DirectInitialHaltError {
    fn from(error: IrEncodingError) -> Self {
        Self::Identity(error)
    }
}

/// Direct native template selected for one portable IR program.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectNativeKind {
    /// Safe fallback artifact that always requests interpreter deoptimization.
    Deopt,
    /// One-step halt bound to arbitrary 32-bit entry registers.
    HaltRegisters,
    /// Exact one-step zero-state halt fast path.
    InitialHalt,
}

/// Failure while selecting/emitting/verifying one direct native template.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectSelectionError {
    /// Deoptimization artifact emission or admission failed.
    Deopt(DirectDeoptError),
    /// Arbitrary-register halt artifact emission or admission failed.
    HaltRegisters(DirectHaltRegistersError),
    /// Initial-halt artifact emission or admission failed.
    InitialHalt(DirectInitialHaltError),
    /// Direct native templates currently emit Windows COFF only.
    TargetFormat,
}

impl Display for DirectSelectionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Deopt(error) => Display::fmt(error, f),
            Self::HaltRegisters(error) => Display::fmt(error, f),
            Self::InitialHalt(error) => Display::fmt(error, f),
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

/// Native object proven to implement exact-register one-step halt.
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
    /// One-step halt bound to arbitrary 32-bit entry registers.
    HaltRegisters(VerifiedHaltRegistersNativeObjectArtifact),
    /// Exact zero-state one-step halt fast path.
    InitialHalt(VerifiedInitialHaltNativeObjectArtifact),
}

impl VerifiedDirectNativeArtifact {
    /// Returns the exact selected native artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        match self {
            Self::Deopt(artifact) => artifact.key(),
            Self::HaltRegisters(artifact) => artifact.key(),
            Self::InitialHalt(artifact) => artifact.key(),
        }
    }

    /// Returns which reviewed direct template was selected.
    #[must_use]
    pub const fn kind(&self) -> DirectNativeKind {
        match self {
            Self::Deopt(_artifact) => DirectNativeKind::Deopt,
            Self::HaltRegisters(_artifact) => DirectNativeKind::HaltRegisters,
            Self::InitialHalt(_artifact) => DirectNativeKind::InitialHalt,
        }
    }

    /// Returns verified object bytes for the selected template.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        match self {
            Self::Deopt(artifact) => artifact.object(),
            Self::HaltRegisters(artifact) => artifact.object(),
            Self::InitialHalt(artifact) => artifact.object(),
        }
    }

    /// Returns the exact selected Windows target triple.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        match self {
            Self::Deopt(artifact) => artifact.target_triple(),
            Self::HaltRegisters(artifact) => artifact.target_triple(),
            Self::InitialHalt(artifact) => artifact.target_triple(),
        }
    }
}

/// Selects the narrowest semantically admitted direct native template.
///
/// Exact initial-halt IR selects the state-applying fast path. Every other
/// portable IR selects the byte-verified deoptimization stub. Selection never
/// converts an emitter/verifier error into fallback; only program shape
/// controls which backend identity is constructed.
///
/// # Errors
///
/// Returns [`DirectSelectionError`] for unsupported host format or any
/// emission/ verification failure after deterministic template selection.
pub fn select_verified_direct_native(
    program: &RegionEffectProgram,
    host_os: HostOperatingSystem,
    host_isa: HostIsa,
) -> Result<VerifiedDirectNativeArtifact, DirectSelectionError> {
    if host_os != HostOperatingSystem::Windows {
        return Err(DirectSelectionError::TargetFormat);
    }
    if validate_initial_halt_program(program).is_ok() {
        let target = direct_target(
            DIRECT_INITIAL_HALT_BACKEND_ID,
            DIRECT_INITIAL_HALT_BACKEND_REVISION,
            host_os,
            host_isa,
        );
        let artifact = emit_direct_initial_halt_coff(program, target)
            .map_err(DirectSelectionError::InitialHalt)?;
        let verified = verify_direct_initial_halt(&artifact, program)
            .map_err(DirectSelectionError::InitialHalt)?;
        return Ok(VerifiedDirectNativeArtifact::InitialHalt(verified));
    }
    if validate_halt_registers_program(program).is_ok() {
        let target = direct_target(
            DIRECT_HALT_REGISTERS_BACKEND_ID,
            DIRECT_HALT_REGISTERS_BACKEND_REVISION,
            host_os,
            host_isa,
        );
        let artifact = emit_direct_halt_registers_coff(program, target)
            .map_err(DirectSelectionError::HaltRegisters)?;
        let verified = verify_direct_halt_registers(&artifact, program)
            .map_err(DirectSelectionError::HaltRegisters)?;
        return Ok(VerifiedDirectNativeArtifact::HaltRegisters(verified));
    }
    let target = direct_target(
        DIRECT_DEOPT_BACKEND_ID,
        DIRECT_DEOPT_BACKEND_REVISION,
        host_os,
        host_isa,
    );
    let artifact = emit_direct_deopt_coff(program, target)
        .map_err(DirectSelectionError::Deopt)?;
    let verified = verify_direct_deopt_stub(&artifact)
        .map_err(DirectSelectionError::Deopt)?;
    Ok(VerifiedDirectNativeArtifact::Deopt(verified))
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
    let triple = target_triple(target.host_isa());
    let key = NativeArtifactKey::new(program, target)?;
    let object = canonical_coff(key.target().host_isa())?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
}

/// Emits a one-step halt fast path bound to exact entry registers.
///
/// # Errors
///
/// Returns [`DirectHaltRegistersError`] when IR/target is outside this subset.
pub fn emit_direct_halt_registers_coff(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, DirectHaltRegistersError> {
    let registers = validate_halt_registers_program(program)?;
    validate_halt_registers_target(&target)?;
    let triple = target_triple(target.host_isa());
    let key = NativeArtifactKey::new(program, target)?;
    let object = halt_registers_coff(key.target().host_isa(), registers)?;
    Ok(UntrustedNativeObjectArtifact::from_emitter_output(
        key, object, triple,
    ))
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
    let triple = target_triple(target.host_isa());
    let key = NativeArtifactKey::new(program, target)?;
    let object = initial_halt_coff(key.target().host_isa())?;
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
    let expected = canonical_coff(artifact.key().target().host_isa())?;
    if admitted.object() != expected {
        return Err(DirectDeoptError::ObjectBytes);
    }
    Ok(VerifiedDeoptNativeObjectArtifact { artifact: admitted })
}

/// Promotes only the canonical exact-register halt object for its IR.
///
/// # Errors
///
/// Returns [`DirectHaltRegistersError`] for IR/identity/COFF/byte mismatch.
pub fn verify_direct_halt_registers(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<VerifiedHaltRegistersNativeObjectArtifact, DirectHaltRegistersError>
{
    let registers = validate_halt_registers_program(program)?;
    validate_halt_registers_target(artifact.key().target())?;
    let expected_key =
        NativeArtifactKey::new(program, artifact.key().target().clone())?;
    if artifact.key() != &expected_key {
        return Err(DirectHaltRegistersError::ProgramShape);
    }
    let admitted = structurally_admit_coff(artifact)?;
    let expected =
        halt_registers_coff(artifact.key().target().host_isa(), registers)?;
    if admitted.object() != expected {
        return Err(DirectHaltRegistersError::ObjectBytes);
    }
    Ok(VerifiedHaltRegistersNativeObjectArtifact { artifact: admitted })
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
    let expected = initial_halt_coff(artifact.key().target().host_isa())?;
    if admitted.object() != expected {
        return Err(DirectInitialHaltError::ObjectBytes);
    }
    Ok(VerifiedInitialHaltNativeObjectArtifact { artifact: admitted })
}

fn canonical_coff(isa: HostIsa) -> Result<Vec<u8>, DirectDeoptError> {
    let text = match isa {
        HostIsa::AArch64 => aarch64::deopt_code(),
        HostIsa::X86_64 => x86_64::deopt_code(),
    };
    build_minimal_coff(isa, text).ok_or(DirectDeoptError::ObjectBytes)
}

fn build_minimal_coff(isa: HostIsa, text: &[u8]) -> Option<Vec<u8>> {
    let (machine, characteristics) = match isa {
        HostIsa::AArch64 => (IMAGE_FILE_MACHINE_ARM64, IMAGE_SCN_ARM64_TEXT),
        HostIsa::X86_64 => (IMAGE_FILE_MACHINE_AMD64, IMAGE_SCN_X86_TEXT),
    };
    let raw_start = COFF_HEADER_BYTES.checked_add(COFF_SECTION_BYTES)?;
    let symbol_start = raw_start.checked_add(text.len())?;
    let symbol_start_u32 = u32::try_from(symbol_start).ok()?;
    let raw_start_u32 = u32::try_from(raw_start).ok()?;
    let text_len = u32::try_from(text.len()).ok()?;
    let string_length =
        4usize.checked_add(REQUIRED_ENTRY.len())?.checked_add(1)?;
    let string_length_u32 = u32::try_from(string_length).ok()?;
    let capacity = symbol_start
        .checked_add(COFF_SYMBOL_BYTES)?
        .checked_add(string_length)?;

    let mut object = Vec::with_capacity(capacity);
    push_u16(&mut object, machine);
    push_u16(&mut object, 1);
    push_u32(&mut object, 0);
    push_u32(&mut object, symbol_start_u32);
    push_u32(&mut object, 1);
    push_u16(&mut object, 0);
    push_u16(&mut object, 0);

    object.extend_from_slice(b".text\0\0\0");
    push_u32(&mut object, 0);
    push_u32(&mut object, 0);
    push_u32(&mut object, text_len);
    push_u32(&mut object, raw_start_u32);
    push_u32(&mut object, 0);
    push_u32(&mut object, 0);
    push_u16(&mut object, 0);
    push_u16(&mut object, 0);
    push_u32(&mut object, characteristics);
    object.extend_from_slice(text);

    push_u32(&mut object, 0);
    push_u32(&mut object, 4);
    push_u32(&mut object, 0);
    push_u16(&mut object, 1);
    push_u16(&mut object, IMAGE_SYM_DTYPE_FUNCTION);
    object.push(IMAGE_SYM_CLASS_EXTERNAL);
    object.push(0);

    push_u32(&mut object, string_length_u32);
    object.extend_from_slice(REQUIRED_ENTRY.as_bytes());
    object.push(0);
    Some(object)
}

fn halt_registers_coff(
    isa: HostIsa,
    registers: ProfileRegisters,
) -> Result<Vec<u8>, DirectHaltRegistersError> {
    let text = match isa {
        HostIsa::AArch64 => aarch64::halt_registers_code(
            registers.accumulator,
            registers.code_pointer,
            registers.data_pointer,
        ),
        HostIsa::X86_64 => x86_64::halt_registers_code(
            registers.accumulator,
            registers.code_pointer,
            registers.data_pointer,
        ),
    };
    build_minimal_coff(isa, &text).ok_or(DirectHaltRegistersError::ObjectBytes)
}

fn initial_halt_coff(isa: HostIsa) -> Result<Vec<u8>, DirectInitialHaltError> {
    let text = match isa {
        HostIsa::AArch64 => aarch64::initial_halt_code(),
        HostIsa::X86_64 => x86_64::initial_halt_code(),
    };
    build_minimal_coff(isa, text).ok_or(DirectInitialHaltError::ObjectBytes)
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

fn validate_halt_registers_program(
    program: &RegionEffectProgram,
) -> Result<ProfileRegisters, DirectHaltRegistersError> {
    if program.format_version != EFFECT_IR_VERSION
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
    if effect.before.input_consumed != 0
        || effect.before.output_len != 0
        || effect.before.termination.is_some()
        || effect.after != expected_after
        || effect.input.is_some()
        || effect.output.is_some()
        || effect.memory_delta != ProfileMemoryDelta::default()
    {
        return Err(DirectHaltRegistersError::ProgramShape);
    }
    Ok(effect.before.registers)
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
