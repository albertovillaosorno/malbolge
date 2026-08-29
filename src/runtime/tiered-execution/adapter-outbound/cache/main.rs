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
//   - Collision-safe native artifact identity, cache-key assumptions, and
//   - process-local full-equality reuse storage.
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

//! Collision-safe native artifact identity and process-local reuse storage.

use std::collections::BTreeMap;
use std::mem::replace;
use std::sync::Arc;

use malbolge::{
    IrEncodingError, RegionEffectProgram, TargetProfileRequirement,
};

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

/// Failure while constructing canonical native artifact identity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeIdentityError {
    /// Portable IR or target identity bytes cannot be represented canonically.
    Encoding(IrEncodingError),
    /// Region addressing exceeds the capacity declared by its profile envelope.
    ProfileCapacity,
}

impl From<IrEncodingError> for NativeIdentityError {
    fn from(error: IrEncodingError) -> Self {
        Self::Encoding(error)
    }
}

/// Canonical portable-IR identity with a non-authoritative lookup digest.
#[derive(Clone, Debug)]
pub struct RegionEffectIdentity {
    bucket_digest: u64,
    canonical_bytes: Arc<[u8]>,
    profile_fingerprint: Arc<str>,
    profile_id: Arc<str>,
    profile_requirement: TargetProfileRequirement,
    required_memory_words: u64,
}

/// Full native artifact reuse key.
#[derive(Clone, Debug)]
pub struct NativeArtifactKey {
    bucket_digest: u64,
    ir: RegionEffectIdentity,
    target: NativeTargetIdentity,
}

/// One caller-owned process-local cache entry.
#[derive(Clone, Debug, Eq, PartialEq)]
struct NativeArtifactCacheEntry<Value> {
    key: NativeArtifactKey,
    value: Value,
}

type NativeArtifactCacheBucket<Value> = Vec<NativeArtifactCacheEntry<Value>>;
type NativeArtifactCacheBuckets<Value> =
    BTreeMap<u64, NativeArtifactCacheBucket<Value>>;

/// Collision-safe process-local native artifact reuse storage.
///
/// The bucket digest narrows lookup only. Every read, replacement, and removal
/// confirms complete [`NativeArtifactKey`] equality before exposing a value.
#[derive(Clone, Debug)]
pub struct NativeArtifactCache<Value> {
    buckets: NativeArtifactCacheBuckets<Value>,
    entries: usize,
}

type BucketDigestFunction = fn(&[u8]) -> u64;

#[expect(
    clippy::missing_trait_methods,
    reason = "default trait methods preserve standard equality semantics"
)]
impl PartialEq for RegionEffectIdentity {
    fn eq(&self, other: &Self) -> bool {
        self.canonical_bytes == other.canonical_bytes
            && self.profile_fingerprint == other.profile_fingerprint
            && self.profile_id == other.profile_id
            && self.profile_requirement == other.profile_requirement
            && self.required_memory_words == other.required_memory_words
    }
}

#[expect(
    clippy::missing_trait_methods,
    reason = "default trait methods preserve standard equality semantics"
)]
impl Eq for RegionEffectIdentity {}

#[expect(
    clippy::missing_trait_methods,
    reason = "default trait methods preserve standard equality semantics"
)]
impl PartialEq for NativeArtifactKey {
    fn eq(&self, other: &Self) -> bool {
        self.ir == other.ir && self.target == other.target
    }
}

#[expect(
    clippy::missing_trait_methods,
    reason = "default trait methods preserve standard equality semantics"
)]
impl Eq for NativeArtifactKey {}

#[expect(
    clippy::missing_trait_methods,
    reason = "default trait methods preserve standard equality semantics"
)]
impl<Value: PartialEq> PartialEq for NativeArtifactCache<Value> {
    fn eq(&self, other: &Self) -> bool {
        self.entries == other.entries
            && self
                .buckets
                .values()
                .flatten()
                .all(|entry| other.get(&entry.key) == Some(&entry.value))
    }
}

#[expect(
    clippy::missing_trait_methods,
    reason = "default trait methods preserve standard equality semantics"
)]
impl<Value: Eq> Eq for NativeArtifactCache<Value> {}

impl<Value> Default for NativeArtifactCache<Value> {
    fn default() -> Self {
        Self {
            buckets: BTreeMap::new(),
            entries: 0,
        }
    }
}

impl<Value> NativeArtifactCache<Value> {
    /// Removes every cached value while retaining no reuse authority.
    pub fn clear(&mut self) {
        self.buckets.clear();
        self.entries = 0;
    }

    fn exact_location(&self, key: &NativeArtifactKey) -> Option<(u64, usize)> {
        let preferred = key.bucket_digest();
        if let Some(index) = self.buckets.get(&preferred).and_then(|bucket| {
            bucket.iter().position(|entry| entry.key == *key)
        }) {
            return Some((preferred, index));
        }
        self.buckets.iter().find_map(|(digest, bucket)| {
            if *digest == preferred {
                None
            } else {
                bucket
                    .iter()
                    .position(|entry| entry.key == *key)
                    .map(|index| (*digest, index))
            }
        })
    }

    /// Returns a cached value only after complete key equality.
    #[must_use]
    pub fn get(&self, key: &NativeArtifactKey) -> Option<&Value> {
        let (digest, index) = self.exact_location(key)?;
        self.buckets
            .get(&digest)?
            .get(index)
            .map(|entry| &entry.value)
    }

    /// Inserts one value, replacing only an existing full-equality key.
    ///
    /// Returns the replaced value when this exact key already existed. A bucket
    /// collision with a different key creates a distinct entry. Equal keys
    /// remain one entry even if their non-authoritative digests differ.
    pub fn insert(
        &mut self,
        key: NativeArtifactKey,
        value: Value,
    ) -> Option<Value> {
        if let Some((digest, index)) = self.exact_location(&key) {
            let entry = self.buckets.get_mut(&digest)?.get_mut(index)?;
            return Some(replace(&mut entry.value, value));
        }
        let bucket = self.buckets.entry(key.bucket_digest()).or_default();
        bucket.push(NativeArtifactCacheEntry { key, value });
        self.entries = self.entries.saturating_add(1);
        None
    }

    /// Reports whether no exact-key values are retained.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.entries == 0
    }

    /// Returns the number of exact-key entries across every digest bucket.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.entries
    }

    /// Removes and returns one value only after complete key equality.
    pub fn remove(&mut self, key: &NativeArtifactKey) -> Option<Value> {
        let (digest, index) = self.exact_location(key)?;
        let (value, empty) = {
            let bucket = self.buckets.get_mut(&digest)?;
            let entry = bucket.remove(index);
            (entry.value, bucket.is_empty())
        };
        self.entries = self.entries.saturating_sub(1);
        if empty {
            let _removed = self.buckets.remove(&digest);
        }
        Some(value)
    }

    /// Removes every target/backend variant for one exact region identity.
    ///
    /// Returns the number of removed entries. Region equality excludes the
    /// non-authoritative bucket digest and confirms complete retained identity.
    pub fn remove_region(&mut self, identity: &RegionEffectIdentity) -> usize {
        let mut removed = 0usize;
        self.buckets.retain(|_digest, bucket| {
            let before = bucket.len();
            bucket.retain(|entry| entry.key.ir() != identity);
            removed =
                removed.saturating_add(before.saturating_sub(bucket.len()));
            !bucket.is_empty()
        });
        self.entries = self.entries.saturating_sub(removed);
        removed
    }

    /// Removes every region compiled for one exact target/backend identity.
    ///
    /// Returns the number of removed entries. Target equality includes host OS,
    /// ISA, backend/revision, native ABI revision, and required features.
    pub fn remove_target(&mut self, target: &NativeTargetIdentity) -> usize {
        let mut removed = 0usize;
        self.buckets.retain(|_digest, bucket| {
            let before = bucket.len();
            bucket.retain(|entry| entry.key.target() != target);
            removed =
                removed.saturating_add(before.saturating_sub(bucket.len()));
            !bucket.is_empty()
        });
        self.entries = self.entries.saturating_sub(removed);
        removed
    }
}

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
    /// Returns [`NativeIdentityError`] when region addressing exceeds its
    /// declared profile capacity or identity lengths cannot be represented.
    pub fn new(
        program: &RegionEffectProgram,
        target: NativeTargetIdentity,
    ) -> Result<Self, NativeIdentityError> {
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
    ) -> Result<Self, NativeIdentityError> {
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
    /// Returns [`NativeIdentityError`] when profile capacity is inconsistent or
    /// portable IR canonicalization fails.
    pub fn new(
        program: &RegionEffectProgram,
    ) -> Result<Self, NativeIdentityError> {
        Self::with_digest(program, fnv_bytes)
    }

    /// Returns the canonical profile fingerprint bound into this IR.
    #[must_use]
    pub fn profile_fingerprint(&self) -> &str {
        &self.profile_fingerprint
    }

    /// Returns the exact declared profile identity bound into this IR.
    #[must_use]
    pub fn profile_id(&self) -> &str {
        &self.profile_id
    }

    /// Returns canonical profile geometry and semantic capabilities.
    #[must_use]
    pub const fn profile_requirement(&self) -> &TargetProfileRequirement {
        &self.profile_requirement
    }

    /// Returns the exact derived region memory footprint in words.
    #[must_use]
    pub const fn required_memory_words(&self) -> u64 {
        self.required_memory_words
    }

    fn with_digest(
        program: &RegionEffectProgram,
        digest: BucketDigestFunction,
    ) -> Result<Self, NativeIdentityError> {
        let required_memory_words = program.required_memory_words();
        if required_memory_words > program.profile_requirement.memory_words {
            return Err(NativeIdentityError::ProfileCapacity);
        }
        let canonical = program.canonical_bytes()?;
        Ok(Self {
            bucket_digest: digest(&canonical),
            canonical_bytes: Arc::from(canonical),
            profile_fingerprint: Arc::from(
                program.profile_fingerprint.as_str(),
            ),
            profile_id: Arc::from(program.profile_id.as_str()),
            profile_requirement: program.profile_requirement.clone(),
            required_memory_words,
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
