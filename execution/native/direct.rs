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
//   - Canonical direct native deoptimization stubs and byte-exact admission.
// - Must-Not:
//   - Apply region effects, bypass verifier guards, or trust compiler output.
// - Allows:
//   - Inputs: portable region IR and exact Windows native target identity.
//   - Outputs: canonical COFF candidates and verified deopt-only artifacts.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when direct fast-path instruction selection gains its own backend.
// - Merge-When:
//   - Merge when all direct emitters share one reviewed instruction template.
// - Summary:
//   - Establishes the first semantically admitted native artifact as
//     deopt-only.
// - Description:
//   - Emits tiny canonical x86-64/AArch64 stubs that return guard miss
//     unchanged.
// - Usage:
//   - Used as a safe native-tier floor before any accelerated direct fast path.
// - Defaults:
//   - Every invocation returns guard miss and commits no guest-visible state.
//
// Related documents:
// - docs/technical/adr/tiered-native-execution.md
// - docs/technical/adr/verification-trust-boundary.md
//
// Large file:
//   - false

//! Canonical direct native deoptimization stubs with byte-exact verification.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::{
    CoffAdmissionError, NATIVE_REGION_ABI_REVISION,
    StructurallyAdmittedNativeObjectArtifact, UntrustedNativeObjectArtifact,
    structurally_admit_coff,
};
use crate::execution_cache::{
    HostIsa, HostOperatingSystem, NativeArtifactKey, NativeTargetIdentity,
};
use crate::execution_ir::{IrEncodingError, RegionEffectProgram};

const AARCH64_DEOPT_CODE: &[u8] =
    &[0x20, 0x00, 0x80, 0x52, 0xc0, 0x03, 0x5f, 0xd6];
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
const X86_64_DEOPT_CODE: &[u8] = &[0xb8, 0x01, 0x00, 0x00, 0x00, 0xc3];

/// Backend identity for the first direct, semantically admitted native tier.
pub const DIRECT_DEOPT_BACKEND_ID: &str = "direct-deopt-stub";
/// Direct deoptimization-stub code-generation revision.
pub const DIRECT_DEOPT_BACKEND_REVISION: u32 = 1;

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

fn canonical_coff(isa: HostIsa) -> Result<Vec<u8>, DirectDeoptError> {
    let (machine, text, characteristics) = match isa {
        HostIsa::AArch64 => (
            IMAGE_FILE_MACHINE_ARM64,
            AARCH64_DEOPT_CODE,
            IMAGE_SCN_ARM64_TEXT,
        ),
        HostIsa::X86_64 => (
            IMAGE_FILE_MACHINE_AMD64,
            X86_64_DEOPT_CODE,
            IMAGE_SCN_X86_TEXT,
        ),
    };
    let raw_start = COFF_HEADER_BYTES.saturating_add(COFF_SECTION_BYTES);
    let symbol_start = raw_start.saturating_add(text.len());
    let symbol_start_u32 = u32::try_from(symbol_start)
        .map_err(|_error| DirectDeoptError::ObjectBytes)?;
    let raw_start_u32 = u32::try_from(raw_start)
        .map_err(|_error| DirectDeoptError::ObjectBytes)?;
    let text_len = u32::try_from(text.len())
        .map_err(|_error| DirectDeoptError::ObjectBytes)?;
    let string_length = 4usize
        .saturating_add(REQUIRED_ENTRY.len())
        .saturating_add(1);
    let string_length_u32 = u32::try_from(string_length)
        .map_err(|_error| DirectDeoptError::ObjectBytes)?;

    let mut object = Vec::with_capacity(
        symbol_start
            .saturating_add(COFF_SYMBOL_BYTES)
            .saturating_add(string_length),
    );
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
    Ok(object)
}

fn push_u16(output: &mut Vec<u8>, value: u16) {
    output.extend_from_slice(&value.to_le_bytes());
}

fn push_u32(output: &mut Vec<u8>, value: u32) {
    output.extend_from_slice(&value.to_le_bytes());
}

const fn target_triple(isa: HostIsa) -> &'static str {
    match isa {
        HostIsa::AArch64 => "aarch64-pc-windows-msvc",
        HostIsa::X86_64 => "x86_64-pc-windows-msvc",
    }
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
