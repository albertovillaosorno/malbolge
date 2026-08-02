// File:
//   - profile_metadata.rs
// Path:
//   - execution/native/profile_metadata.rs
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
//   - Canonical native profile-metadata payload encoding.
// - Must-Not:
//   - Parse object containers, admit machine code, or define VM semantics.
// - Allows:
//   - Inputs: exact native artifact keys.
//   - Outputs: deterministic MBPF payload bytes and the section identity.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when multiple metadata schemas require independent version owners.
// - Merge-When:
//   - Merge when native metadata becomes part of one general artifact schema.
// - Summary:
//   - Encodes the profile envelope shared by direct and bootstrap objects.
// - Description:
//   - Produces MBPF v3 bytes from the exact profile and region footprint key.
// - Usage:
//   - Used by source/direct emitters and independent structural admission.
// - Defaults:
//   - Encoding failure is fail-closed and yields no payload.
//
// Related documents:
// - docs/technical/compatibility/custom-target-profile-identity.md
// - docs/technical/runtime/execution/tiered-native-execution-engine.md
//
// Large file:
//   - false
//

//! Canonical profile metadata shared across native artifact boundaries.

use crate::execution_cache::NativeArtifactKey;

const PROFILE_METADATA_MAGIC: &[u8; 4] = b"MBPF";
pub(super) const PROFILE_METADATA_SECTION: &str = ".mbprof";
const PROFILE_METADATA_VERSION: u16 = 3;

pub(super) fn canonical_profile_metadata(
    key: &NativeArtifactKey,
) -> Option<Vec<u8>> {
    let ir = key.ir();
    let requirement = ir.profile_requirement();
    let feature_count = u32::try_from(requirement.features.len()).ok()?;
    let mut bytes = Vec::new();
    bytes.extend_from_slice(PROFILE_METADATA_MAGIC);
    bytes.extend_from_slice(&PROFILE_METADATA_VERSION.to_le_bytes());
    bytes.extend_from_slice(&0u16.to_le_bytes());
    push_metadata_bytes(&mut bytes, ir.profile_id().as_bytes())?;
    push_metadata_bytes(&mut bytes, ir.profile_fingerprint().as_bytes())?;
    push_metadata_bytes(&mut bytes, requirement.version.as_bytes())?;
    bytes.extend_from_slice(&feature_count.to_le_bytes());
    for feature in &requirement.features {
        push_metadata_bytes(&mut bytes, feature.as_bytes())?;
    }
    bytes.push(requirement.word_trits);
    bytes.extend_from_slice(&requirement.memory_words.to_le_bytes());
    bytes.extend_from_slice(&ir.required_memory_words().to_le_bytes());
    Some(bytes)
}

fn push_metadata_bytes(output: &mut Vec<u8>, value: &[u8]) -> Option<()> {
    let length = u32::try_from(value.len()).ok()?;
    output.extend_from_slice(&length.to_le_bytes());
    output.extend_from_slice(value);
    Some(())
}
