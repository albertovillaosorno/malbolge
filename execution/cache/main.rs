// File:
//   - main.rs
// Path:
//   - execution/cache/main.rs
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
//   - Collision-safe native artifact identity and cache-key assumptions.
// - Must-Not:
//   - Treat bucket hashes as identity, emit machine code, or trust unverified
//   - IR.
// - Allows:
//   - Inputs: portable effect programs and explicit host/backend assumptions.
//   - Outputs: full-equality native artifact keys and non-authoritative
//   - buckets.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when durable serialized cache storage needs independent ownership.
// - Merge-When:
//   - Merge when native artifact ownership subsumes cache-key construction.
// - Summary:
//   - Keys native reuse by canonical IR plus every declared host assumption.
// - Description:
//   - Full canonical equality remains authoritative after any bucket collision.
// - Usage:
//   - Included by tiered execution composition roots through explicit paths.
// - Defaults:
//   - No cache key is architecture- or operating-system-neutral.
//
// Related documents:
// - docs/technical/adr/host-cpu-and-accelerator-runtime-baseline.md
// - docs/technical/adr/tiered-native-execution.md
//
// Large file:
//   - false
//

//! Collision-safe native artifact identity over canonical execution IR.

use std::sync::Arc;

use crate::execution_ir::{IrEncodingError, RegionEffectProgram};

const FNV_OFFSET: u64 = 14_695_981_039_346_656_037;
const FNV_PRIME: u64 = 1_099_511_628_211;
const NATIVE_KEY_MAGIC: &[u8; 4] = b"MBNK";

/// Supported 64-bit native code-generation host ISA.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum HostIsa {
    /// 64-bit Arm architecture.
    AArch64,
    /// 64-bit x86 architecture.
    X86_64,
}

/// Supported native artifact host operating-system family.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum HostOperatingSystem {
    /// Linux host runtime.
    Linux,
    /// macOS host runtime.
    MacOs,
    /// Windows host runtime.
    Windows,
}

/// Caller-supplied target assumptions normalized into cache identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeTargetConfig {
    /// Stable backend implementation identity.
    pub backend_id: String,
    /// Backend code-generation revision.
    pub backend_revision: u32,
    /// Selected host ISA.
    pub host_isa: HostIsa,
    /// Selected host operating-system family.
    pub host_os: HostOperatingSystem,
    /// Native runner ABI revision assumed by generated code.
    pub native_abi_revision: u16,
    /// Required host-code features; order and duplicates are canonicalized.
    pub required_features: Vec<String>,
}

/// Exact backend/runtime assumptions that participate in native artifact reuse.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeTargetIdentity {
    backend_id: String,
    backend_revision: u32,
    host_isa: HostIsa,
    host_os: HostOperatingSystem,
    native_abi_revision: u16,
    required_features: Vec<String>,
}

/// Canonical portable-IR identity with a non-authoritative lookup digest.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegionEffectIdentity {
    bucket_digest: u64,
    canonical_bytes: Arc<[u8]>,
}

/// Full native artifact reuse key.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeArtifactKey {
    bucket_digest: u64,
    ir: RegionEffectIdentity,
    target: NativeTargetIdentity,
}

type BucketDigestFunction = fn(&[u8]) -> u64;

impl NativeArtifactKey {
    /// Returns the non-authoritative bucket digest used only for lookup.
    #[must_use]
    pub const fn bucket_digest(&self) -> u64 {
        self.bucket_digest
    }

    /// Returns the canonical portable IR identity inside this key.
    #[must_use]
    pub const fn ir(&self) -> &RegionEffectIdentity {
        &self.ir
    }

    /// Constructs one native reuse key from canonical IR and target
    /// assumptions.
    ///
    /// # Errors
    ///
    /// Returns [`IrEncodingError`] when portable IR or target lengths cannot be
    /// represented by the architecture-neutral encoding.
    pub fn new(
        program: &RegionEffectProgram,
        target: NativeTargetIdentity,
    ) -> Result<Self, IrEncodingError> {
        Self::with_digest(program, target, fnv_bytes)
    }

    /// Returns the exact host/backend assumptions inside this key.
    #[must_use]
    pub const fn target(&self) -> &NativeTargetIdentity {
        &self.target
    }

    pub(crate) fn with_digest(
        program: &RegionEffectProgram,
        target: NativeTargetIdentity,
        digest: BucketDigestFunction,
    ) -> Result<Self, IrEncodingError> {
        let ir = RegionEffectIdentity::with_digest(program, digest)?;
        let mut key_bytes = target.canonical_bytes()?;
        key_bytes.extend_from_slice(ir.canonical_bytes());
        Ok(Self {
            bucket_digest: digest(&key_bytes),
            ir,
            target,
        })
    }
}

impl NativeTargetIdentity {
    /// Returns the stable backend implementation identity.
    #[must_use]
    pub fn backend_id(&self) -> &str {
        &self.backend_id
    }

    /// Returns the backend code-generation revision.
    #[must_use]
    pub const fn backend_revision(&self) -> u32 {
        self.backend_revision
    }

    fn canonical_bytes(&self) -> Result<Vec<u8>, IrEncodingError> {
        let mut bytes = Vec::new();
        bytes.extend_from_slice(NATIVE_KEY_MAGIC);
        bytes.push(host_os_tag(self.host_os));
        bytes.push(host_isa_tag(self.host_isa));
        push_string(&mut bytes, &self.backend_id)?;
        bytes.extend_from_slice(&self.backend_revision.to_le_bytes());
        bytes.extend_from_slice(&self.native_abi_revision.to_le_bytes());
        push_usize(&mut bytes, self.required_features.len())?;
        for feature in &self.required_features {
            push_string(&mut bytes, feature)?;
        }
        Ok(bytes)
    }

    /// Returns the selected host ISA.
    #[must_use]
    pub const fn host_isa(&self) -> HostIsa {
        self.host_isa
    }

    /// Returns the selected host operating-system family.
    #[must_use]
    pub const fn host_os(&self) -> HostOperatingSystem {
        self.host_os
    }

    /// Returns the native runner ABI revision assumed by generated code.
    #[must_use]
    pub const fn native_abi_revision(&self) -> u16 {
        self.native_abi_revision
    }

    /// Constructs canonical host/backend assumptions for native reuse.
    #[must_use]
    pub fn new(mut config: NativeTargetConfig) -> Self {
        config.required_features.sort_unstable();
        config.required_features.dedup();
        Self {
            backend_id: config.backend_id,
            backend_revision: config.backend_revision,
            host_isa: config.host_isa,
            host_os: config.host_os,
            native_abi_revision: config.native_abi_revision,
            required_features: config.required_features,
        }
    }

    /// Returns sorted/deduplicated required host-code features.
    #[must_use]
    pub fn required_features(&self) -> &[String] {
        &self.required_features
    }
}

impl RegionEffectIdentity {
    /// Returns the bucket-only digest. Full canonical bytes remain authority.
    #[must_use]
    pub const fn bucket_digest(&self) -> u64 {
        self.bucket_digest
    }

    /// Returns the exact canonical portable-IR bytes.
    #[must_use]
    pub fn canonical_bytes(&self) -> &[u8] {
        &self.canonical_bytes
    }

    /// Constructs canonical IR identity and its non-authoritative lookup
    /// digest.
    ///
    /// # Errors
    ///
    /// Returns [`IrEncodingError`] from portable IR canonicalization.
    pub fn new(program: &RegionEffectProgram) -> Result<Self, IrEncodingError> {
        Self::with_digest(program, fnv_bytes)
    }

    fn with_digest(
        program: &RegionEffectProgram,
        digest: BucketDigestFunction,
    ) -> Result<Self, IrEncodingError> {
        let canonical = program.canonical_bytes()?;
        Ok(Self {
            bucket_digest: digest(&canonical),
            canonical_bytes: Arc::from(canonical),
        })
    }
}

fn fnv_bytes(bytes: &[u8]) -> u64 {
    let mut hash = FNV_OFFSET;
    for byte in bytes {
        hash = (hash ^ u64::from(*byte)).wrapping_mul(FNV_PRIME);
    }
    hash
}

const fn host_isa_tag(isa: HostIsa) -> u8 {
    match isa {
        HostIsa::AArch64 => 1,
        HostIsa::X86_64 => 2,
    }
}

const fn host_os_tag(os: HostOperatingSystem) -> u8 {
    match os {
        HostOperatingSystem::Linux => 1,
        HostOperatingSystem::MacOs => 2,
        HostOperatingSystem::Windows => 3,
    }
}

fn push_string(
    output: &mut Vec<u8>,
    value: &str,
) -> Result<(), IrEncodingError> {
    push_usize(output, value.len())?;
    output.extend_from_slice(value.as_bytes());
    Ok(())
}

fn push_usize(
    output: &mut Vec<u8>,
    value: usize,
) -> Result<(), IrEncodingError> {
    let canonical = u64::try_from(value)
        .map_err(|_error| IrEncodingError::LengthOverflow)?;
    output.extend_from_slice(&canonical.to_le_bytes());
    Ok(())
}
