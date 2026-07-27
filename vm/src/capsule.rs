// File:
//   - capsule.rs
// Path:
//   - vm/src/capsule.rs
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
//   - Version-one historical-fallback capsule framing and parsing.
// - Must-Not:
//   - Execute payloads, reinterpret profile identity, or emulate Ben defects.
// - Allows:
//   - Inputs: canonical profile descriptors and arbitrary payload bytes.
//   - Outputs: `QP` fallback capsules and validated extracted payloads.
//   - Side effects: caller-owned allocation only.
// - Split-When:
//   - Split when another capsule version needs an incompatible framing model.
// - Merge-When:
//   - Merge when execution loading owns the same framing boundary directly.
// - Summary:
//   - Encodes modern payloads behind a classic-safe space/tab sideband.
// - Description:
//   - Keeps the historical loader surface exactly `QP` while modern runtimes
//     validate profile identity, framing, lengths, and transport checksum.
// - Usage:
//   - Parse before classic source loading when capsule support is requested.
// - Defaults:
//   - Ordinary classic source remains ordinary source unless the exact magic
//     sideband follows `QP`.
//
// Related documents:
// - docs/technical/compatibility/historical-interpreter-fallback-capsule.md
// - docs/technical/compatibility/custom-target-profile-identity.md
//
// Large file:
//   - false

//! Historical-safe fallback capsule framing for modern Malbolge payloads.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::str;

use crate::{ProfileDescriptor, target_profile};

const BITS_PER_BYTE: usize = 8;
const BIT_MASKS: [u8; BITS_PER_BYTE] =
    [0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01];
const CAPSULE_FLAGS: u8 = 0;
const CAPSULE_MAGIC: &[u8; 8] = b"MALBCAP1";
const CAPSULE_VERSION: u8 = 1;
const CHECKSUM_BYTES: usize = 8;
const FALLBACK_SOURCE: &[u8; 7] = b"(C<;_\"K";
const FNV1A64_OFFSET: u64 = 0xcbf2_9ce4_8422_2325;
const FNV1A64_PRIME: u64 = 0x0000_0100_0000_01b3;
const MAGIC_SYMBOLS: usize = 64;
const SPACE: u8 = b' ';
const TAB: u8 = b'\t';

/// One validated modern capsule extracted from a historical-safe source file.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Capsule {
    payload: Vec<u8>,
    profile: &'static ProfileDescriptor,
}

/// Deterministic failure while building one version-one capsule.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CapsuleBuildError {
    /// One framed length cannot be represented by the version-one format.
    LengthOverflow,
}

/// Deterministic failure after the exact capsule marker has been recognized.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum CapsuleError {
    /// The decoded frame checksum differs from the stored checksum.
    ChecksumMismatch {
        /// Checksum stored in the capsule frame.
        expected: u64,
        /// Checksum recomputed from decoded frame bytes.
        observed: u64,
    },
    /// The recognized sideband cannot be decoded under version-one framing.
    Malformed,
    /// The sideband profile fingerprint does not match canonical identity.
    ProfileFingerprintMismatch {
        /// Canonical profile whose sideband fingerprint did not match.
        profile_id: &'static str,
    },
    /// The sideband selected a profile absent from the canonical registry.
    UnknownProfile {
        /// Unknown profile identity encoded by the sideband.
        profile_id: Box<str>,
    },
    /// Reserved version-one flag bits were nonzero.
    UnsupportedFlags {
        /// Exact unsupported flag byte.
        flags: u8,
    },
    /// The sideband version is not implemented by this parser.
    UnsupportedVersion {
        /// Exact unsupported version byte.
        version: u8,
    },
}

struct FrameCursor<'frame> {
    bytes: &'frame [u8],
    position: usize,
}

impl Capsule {
    /// Returns the decoded modern payload bytes.
    #[must_use]
    pub fn payload(&self) -> &[u8] {
        &self.payload
    }

    /// Returns the canonical profile selected and fingerprint-verified by
    /// frame.
    #[must_use]
    pub const fn profile(&self) -> &'static ProfileDescriptor {
        self.profile
    }
}

impl Display for CapsuleBuildError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::LengthOverflow => f.write_str(
                "MALBOLGE-CAPSULE-BUILD-001 capsule field length overflow",
            ),
        }
    }
}

impl Display for CapsuleError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ChecksumMismatch { expected, observed } => {
                f.write_str("MALBOLGE-CAPSULE-003 checksum mismatch ")?;
                write!(f, "expected={expected:016x} observed={observed:016x}")
            },
            Self::Malformed => {
                f.write_str("MALBOLGE-CAPSULE-001 malformed capsule sideband")
            },
            Self::ProfileFingerprintMismatch { profile_id } => write!(
                f,
                "MALBOLGE-CAPSULE-005 profile={profile_id} fingerprint mismatch"
            ),
            Self::UnknownProfile { profile_id } => {
                write!(f, "MALBOLGE-CAPSULE-004 unknown profile={profile_id}")
            },
            Self::UnsupportedFlags { flags } => {
                write!(f, "MALBOLGE-CAPSULE-006 unsupported flags={flags}")
            },
            Self::UnsupportedVersion { version } => {
                write!(f, "MALBOLGE-CAPSULE-002 unsupported version={version}")
            },
        }
    }
}

impl<'frame> FrameCursor<'frame> {
    const fn new(bytes: &'frame [u8]) -> Self {
        Self { bytes, position: 0 }
    }

    const fn remaining(&self) -> usize {
        self.bytes.len().saturating_sub(self.position)
    }

    fn take(&mut self, count: usize) -> Result<&'frame [u8], CapsuleError> {
        let end = self
            .position
            .checked_add(count)
            .ok_or(CapsuleError::Malformed)?;
        let value = self
            .bytes
            .get(self.position..end)
            .ok_or(CapsuleError::Malformed)?;
        self.position = end;
        Ok(value)
    }

    fn u16(&mut self) -> Result<u16, CapsuleError> {
        let bytes: [u8; 2] = self
            .take(2)?
            .try_into()
            .ok()
            .ok_or(CapsuleError::Malformed)?;
        Ok(u16::from_be_bytes(bytes))
    }

    fn u32(&mut self) -> Result<u32, CapsuleError> {
        let bytes: [u8; 4] = self
            .take(4)?
            .try_into()
            .ok()
            .ok_or(CapsuleError::Malformed)?;
        Ok(u32::from_be_bytes(bytes))
    }

    fn u64(&mut self) -> Result<u64, CapsuleError> {
        let bytes: [u8; 8] = self
            .take(8)?
            .try_into()
            .ok()
            .ok_or(CapsuleError::Malformed)?;
        Ok(u64::from_be_bytes(bytes))
    }

    fn u8(&mut self) -> Result<u8, CapsuleError> {
        self.take(1)?
            .first()
            .copied()
            .ok_or(CapsuleError::Malformed)
    }
}

/// Builds one version-one capsule with the fixed historical `!` sentinel
/// fallback.
///
/// # Errors
///
/// Returns [`CapsuleBuildError`] when a length cannot fit version-one fields.
pub fn build_capsule(
    profile: &'static ProfileDescriptor,
    payload: &[u8],
) -> Result<Vec<u8>, CapsuleBuildError> {
    let profile_id = profile.id().as_bytes();
    let fingerprint = profile.fingerprint().as_bytes();
    let profile_id_len = u16::try_from(profile_id.len())
        .ok()
        .ok_or(CapsuleBuildError::LengthOverflow)?;
    let fingerprint_len = u16::try_from(fingerprint.len())
        .ok()
        .ok_or(CapsuleBuildError::LengthOverflow)?;
    let payload_len = u32::try_from(payload.len())
        .ok()
        .ok_or(CapsuleBuildError::LengthOverflow)?;

    let mut frame = Vec::new();
    frame.extend_from_slice(CAPSULE_MAGIC);
    frame.push(CAPSULE_VERSION);
    frame.push(CAPSULE_FLAGS);
    frame.extend_from_slice(&profile_id_len.to_be_bytes());
    frame.extend_from_slice(&fingerprint_len.to_be_bytes());
    frame.extend_from_slice(&payload_len.to_be_bytes());
    frame.extend_from_slice(profile_id);
    frame.extend_from_slice(fingerprint);
    frame.extend_from_slice(payload);
    let checksum = fnv1a64(&frame);
    frame.extend_from_slice(&checksum.to_be_bytes());

    let mut source = Vec::new();
    source.extend_from_slice(FALLBACK_SOURCE);
    encode_sideband(&frame, &mut source);
    Ok(source)
}

/// Recognizes and validates one version-one historical-fallback capsule.
///
/// Ordinary source, including the fallback with ordinary trailing whitespace,
/// returns `Ok(None)` unless the exact version-one magic is present in a pure
/// space/tab suffix. Once that marker is recognized, all malformed data fails
/// closed.
///
/// # Errors
///
/// Returns [`CapsuleError`] after exact capsule recognition when framing,
/// checksum, profile identity, fingerprint, version, or flags are invalid.
pub fn parse_capsule(source: &[u8]) -> Result<Option<Capsule>, CapsuleError> {
    let Some(sideband) = capsule_sideband(source) else {
        return Ok(None);
    };
    let frame = decode_sideband(sideband)?;
    parse_frame(&frame).map(Some)
}

fn capsule_sideband(source: &[u8]) -> Option<&[u8]> {
    if !source.starts_with(FALLBACK_SOURCE) {
        return None;
    }
    let sideband = source.get(FALLBACK_SOURCE.len()..)?;
    if sideband.len() < MAGIC_SYMBOLS
        || sideband
            .iter()
            .any(|symbol| !matches!(*symbol, SPACE | TAB))
    {
        return None;
    }
    let magic_symbols = sideband.get(..MAGIC_SYMBOLS)?;
    let decoded_magic = decode_sideband(magic_symbols).ok()?;
    if decoded_magic.as_slice() != CAPSULE_MAGIC {
        return None;
    }
    Some(sideband)
}

fn decode_sideband(sideband: &[u8]) -> Result<Vec<u8>, CapsuleError> {
    let (chunks, remainder) = sideband.as_chunks::<BITS_PER_BYTE>();
    if !remainder.is_empty() {
        return Err(CapsuleError::Malformed);
    }
    let mut decoded = Vec::new();
    for chunk in chunks {
        let mut value = 0u8;
        for symbol in chunk.iter().copied() {
            value = value.checked_mul(2).ok_or(CapsuleError::Malformed)?;
            match symbol {
                SPACE => {},
                TAB => {
                    value =
                        value.checked_add(1).ok_or(CapsuleError::Malformed)?;
                },
                _ => return Err(CapsuleError::Malformed),
            }
        }
        decoded.push(value);
    }
    Ok(decoded)
}

fn encode_sideband(frame: &[u8], source: &mut Vec<u8>) {
    for byte in frame.iter().copied() {
        for mask in BIT_MASKS {
            let symbol = if byte & mask == 0 {
                SPACE
            } else {
                TAB
            };
            source.push(symbol);
        }
    }
}

fn fnv1a64(bytes: &[u8]) -> u64 {
    let mut hash = FNV1A64_OFFSET;
    for byte in bytes.iter().copied() {
        hash ^= u64::from(byte);
        hash = hash.wrapping_mul(FNV1A64_PRIME);
    }
    hash
}

fn parse_frame(frame: &[u8]) -> Result<Capsule, CapsuleError> {
    let checksum_input_len = frame
        .len()
        .checked_sub(CHECKSUM_BYTES)
        .ok_or(CapsuleError::Malformed)?;
    let checksum_input = frame
        .get(..checksum_input_len)
        .ok_or(CapsuleError::Malformed)?;
    let mut cursor = FrameCursor::new(frame);
    if cursor.take(CAPSULE_MAGIC.len())? != CAPSULE_MAGIC {
        return Err(CapsuleError::Malformed);
    }
    let version = cursor.u8()?;
    if version != CAPSULE_VERSION {
        return Err(CapsuleError::UnsupportedVersion { version });
    }
    let flags = cursor.u8()?;
    if flags != CAPSULE_FLAGS {
        return Err(CapsuleError::UnsupportedFlags { flags });
    }
    let profile_id_len = usize::from(cursor.u16()?);
    let fingerprint_len = usize::from(cursor.u16()?);
    let payload_len = usize::try_from(cursor.u32()?)
        .ok()
        .ok_or(CapsuleError::Malformed)?;
    let profile_id_bytes = cursor.take(profile_id_len)?;
    let fingerprint_bytes = cursor.take(fingerprint_len)?;
    let payload = cursor.take(payload_len)?.to_vec();
    let expected_checksum = cursor.u64()?;
    if cursor.remaining() != 0 {
        return Err(CapsuleError::Malformed);
    }
    let observed_checksum = fnv1a64(checksum_input);
    if expected_checksum != observed_checksum {
        return Err(CapsuleError::ChecksumMismatch {
            expected: expected_checksum,
            observed: observed_checksum,
        });
    }
    let profile_id = str::from_utf8(profile_id_bytes)
        .ok()
        .ok_or(CapsuleError::Malformed)?;
    let fingerprint = str::from_utf8(fingerprint_bytes)
        .ok()
        .ok_or(CapsuleError::Malformed)?;
    let Some(profile) = target_profile(profile_id) else {
        return Err(CapsuleError::UnknownProfile {
            profile_id: profile_id.into(),
        });
    };
    if fingerprint != profile.fingerprint() {
        return Err(CapsuleError::ProfileFingerprintMismatch {
            profile_id: profile.id(),
        });
    }
    Ok(Capsule { payload, profile })
}
