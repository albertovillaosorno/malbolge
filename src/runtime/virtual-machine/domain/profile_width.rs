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
//   - Trusted admission of derived profile execution geometry for proved
//   - width-safe source families.
// - Must-Not:
//   - Create canonical profile identities, trust optimizer certificates, or
//   - execute guest code.
// - Allows:
//   - Inputs: one canonical profile, exact source bytes, and a candidate width.
//   - Outputs: an unforgeable source/profile-bound verified geometry or a typed
//   - rejection.
//   - Side effects: owned source-byte allocation only after verification.
// - Split-When:
//   - Split when another proof family needs an independent verifier lifecycle.
// - Merge-When:
//   - Merge when canonical profile verification owns derived geometry directly.
// - Summary:
//   - Independently verifies narrow initial-halt execution geometry.
// - Description:
//   - Reuses VM source admission and decode authority rather than research
//   - certificate implementations.
// - Usage:
//   - Verify first, then pass only the resulting opaque geometry to future
//   - execution adapters.
// - Defaults:
//   - Widths outside 10 through the canonical profile width fail closed.
//

//! Trusted admission for source-bound derived profile execution geometry.

use std::fmt::{Display, Formatter, Result as FormatResult};

use crate::profile::ProfileDescriptor;
use crate::profile_machine::{
    ProfileLoadError, admit_profile_source, decode_profile_instruction,
};

const MINIMUM_ADAPTIVE_WORD_TRITS: u8 = 10;
const TERNARY_RADIX: u32 = 3;

/// Stable proof family that independently admitted one derived geometry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileWidthProofKind {
    /// Source loading succeeds and the first decoded instruction halts.
    InitialHalt,
    /// One or more decoded no-ops precede the first reached halt.
    NoopPrefixHalt,
}

/// Opaque execution geometry emitted only through trusted width verification.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProfileExecutionGeometry {
    memory_words: u32,
    profile: &'static ProfileDescriptor,
    word_trits: u8,
}

impl ProfileExecutionGeometry {
    pub(crate) const fn canonical(profile: &'static ProfileDescriptor) -> Self {
        Self {
            memory_words: profile.memory_words(),
            profile,
            word_trits: profile.word_trits(),
        }
    }

    /// Returns the derived all-two-trit EOF value.
    #[must_use]
    pub const fn eof_word(self) -> u32 {
        self.memory_words.saturating_sub(1)
    }

    /// Returns the exact derived resident memory length.
    #[must_use]
    pub const fn memory_words(self) -> u32 {
        self.memory_words
    }

    /// Returns the unchanged canonical profile bound to this geometry.
    #[must_use]
    pub const fn profile(self) -> &'static ProfileDescriptor {
        self.profile
    }

    /// Returns the exact derived ternary word modulus.
    #[must_use]
    pub const fn word_modulus(self) -> u32 {
        self.memory_words
    }

    /// Returns the independently admitted ternary word width.
    #[must_use]
    pub const fn word_trits(self) -> u8 {
        self.word_trits
    }
}

/// Source/profile-bound proof envelope emitted only by trusted verification.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct VerifiedProfileExecutionGeometry {
    geometry: ProfileExecutionGeometry,
    proof_kind: ProfileWidthProofKind,
    source: Box<[u8]>,
}

impl VerifiedProfileExecutionGeometry {
    /// Returns the derived all-two-trit EOF value.
    #[must_use]
    pub const fn eof_word(&self) -> u32 {
        self.geometry.eof_word()
    }

    /// Returns the copyable opaque execution token admitted by this proof.
    #[must_use]
    pub const fn geometry(&self) -> ProfileExecutionGeometry {
        self.geometry
    }

    /// Returns the exact derived resident memory length.
    #[must_use]
    pub const fn memory_words(&self) -> u32 {
        self.geometry.memory_words()
    }

    /// Returns the unchanged canonical profile identity and semantics.
    #[must_use]
    pub const fn profile(&self) -> &'static ProfileDescriptor {
        self.geometry.profile()
    }

    /// Returns the trusted proof family that admitted this geometry.
    #[must_use]
    pub const fn proof_kind(&self) -> ProfileWidthProofKind {
        self.proof_kind
    }

    /// Returns the exact raw source bytes bound by this verification.
    #[must_use]
    pub fn source(&self) -> &[u8] {
        &self.source
    }

    /// Returns the exact derived ternary word modulus.
    #[must_use]
    pub const fn word_modulus(&self) -> u32 {
        self.geometry.word_modulus()
    }

    /// Returns the independently admitted ternary word width.
    #[must_use]
    pub const fn word_trits(&self) -> u8 {
        self.geometry.word_trits()
    }
}

/// Deterministic rejection from trusted adaptive-width verification.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileWidthVerificationError {
    /// Derived `3^N` arithmetic unexpectedly exceeded the u32 profile domain.
    GeometryInvariant,
    /// The admitted source does not halt at its first decoded instruction.
    InitialInstructionNotHalt {
        /// Exact decoded first instruction.
        decoded: u8,
    },
    /// A reached prefix instruction is neither an admitted no-op nor halt.
    NoopPrefixInstruction {
        /// Exact loaded source position of the rejected instruction.
        position: u32,
        /// Exact decoded instruction byte.
        decoded: u8,
    },
    /// The admitted source ended before a no-op prefix reached halt.
    NoopPrefixMissingHalt,
    /// The exact source fails ordinary profile-loader admission.
    Source(ProfileLoadError),
    /// Candidate width is outside the reviewed adaptive interval.
    WidthOutOfRange {
        /// Maximum width owned by the canonical profile.
        profile_word_trits: u8,
        /// Rejected requested width.
        requested: u8,
    },
}

impl Display for ProfileWidthVerificationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::GeometryInvariant => {
                f.write_str("derived profile geometry invariant failed")
            },
            Self::InitialInstructionNotHalt { decoded } => write!(
                f,
                "derived profile initial instruction {decoded} is not halt"
            ),
            Self::NoopPrefixInstruction { position, decoded } => {
                write!(f, "derived no-op prefix instruction {decoded} at ")?;
                write!(f, "{position} is invalid")
            },
            Self::NoopPrefixMissingHalt => {
                f.write_str("derived no-op prefix does not reach halt")
            },
            Self::Source(error) => Display::fmt(error, f),
            Self::WidthOutOfRange {
                profile_word_trits,
                requested,
            } => {
                write!(f, "derived profile width {requested} outside ")?;
                write!(f, "10..={profile_word_trits}")
            },
        }
    }
}

impl From<ProfileLoadError> for ProfileWidthVerificationError {
    fn from(error: ProfileLoadError) -> Self {
        Self::Source(error)
    }
}

/// Selects the minimum independently verified no-op-prefix-halt width.
///
/// Only derived-capacity rejection advances to a wider candidate. Any theorem
/// or source-admission failure rejects without widening around the evidence.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed candidate admits
/// the exact source under the no-op-prefix-halt theorem.
pub fn verify_minimum_noop_prefix_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let mut capacity_error = None;
    for word_trits in MINIMUM_ADAPTIVE_WORD_TRITS..=profile.word_trits() {
        match verify_noop_prefix_halt_profile_width(profile, source, word_trits)
        {
            Ok(verified) => return Ok(verified),
            Err(
                error @ ProfileWidthVerificationError::Source(
                    ProfileLoadError::SourceTooLong,
                ),
            ) => {
                capacity_error = Some(error);
            },
            Err(error) => return Err(error),
        }
    }
    Err(capacity_error.unwrap_or_else(|| {
        ProfileWidthVerificationError::WidthOutOfRange {
            profile_word_trits: profile.word_trits(),
            requested: MINIMUM_ADAPTIVE_WORD_TRITS,
        }
    }))
}

/// Selects the minimum independently verified initial-halt width.
///
/// Only a derived-capacity rejection advances to the next width. Any lexical,
/// decode, theorem, or geometry failure rejects immediately rather than being
/// reinterpreted as evidence for a wider candidate.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed candidate admits
/// the exact source under the initial-halt theorem.
pub fn verify_minimum_initial_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let mut capacity_error = None;
    for word_trits in MINIMUM_ADAPTIVE_WORD_TRITS..=profile.word_trits() {
        match verify_initial_halt_profile_width(profile, source, word_trits) {
            Ok(verified) => return Ok(verified),
            Err(
                error @ ProfileWidthVerificationError::Source(
                    ProfileLoadError::SourceTooLong,
                ),
            ) => {
                capacity_error = Some(error);
            },
            Err(error) => return Err(error),
        }
    }
    Err(capacity_error.unwrap_or_else(|| {
        ProfileWidthVerificationError::WidthOutOfRange {
            profile_word_trits: profile.word_trits(),
            requested: MINIMUM_ADAPTIVE_WORD_TRITS,
        }
    }))
}

/// Independently verifies a nonempty no-op prefix followed by halt.
///
/// Ordinary profile source admission validates the complete raw source. This
/// theorem then follows only the reached decoded prefix until its first halt.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when geometry, source admission,
/// the required nonempty no-op prefix, or its reached halt does not hold.
pub fn verify_noop_prefix_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let admitted = admit_profile_source(source, memory_words)?;
    let mut noops = 0usize;
    for (position, cell) in admitted.iter().copied().enumerate() {
        let pointer = u32::try_from(position).map_err(|_error| {
            ProfileWidthVerificationError::GeometryInvariant
        })?;
        let decoded = decode_profile_instruction(cell, pointer)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        if decoded == b'o' {
            noops = noops.saturating_add(1);
            continue;
        }
        if decoded == b'v' && noops > 0 {
            return Ok(VerifiedProfileExecutionGeometry {
                geometry: ProfileExecutionGeometry {
                    memory_words,
                    profile,
                    word_trits,
                },
                proof_kind: ProfileWidthProofKind::NoopPrefixHalt,
                source: Box::from(source),
            });
        }
        return Err(ProfileWidthVerificationError::NoopPrefixInstruction {
            position: pointer,
            decoded,
        });
    }
    Err(ProfileWidthVerificationError::NoopPrefixMissingHalt)
}

/// Independently verifies the initial-halt proof family for one derived width.
///
/// This verifier consumes canonical VM source-admission and decode rules. It
/// does not parse or trust research certificates, and the returned geometry
/// retains the exact canonical profile plus raw source bytes.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when width geometry, ordinary
/// profile-source admission, or the required initial halt does not hold.
pub fn verify_initial_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let admitted = admit_profile_source(source, memory_words)?;
    let first = admitted
        .first()
        .copied()
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    let decoded = decode_profile_instruction(first, 0)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    if decoded != b'v' {
        return Err(ProfileWidthVerificationError::InitialInstructionNotHalt {
            decoded,
        });
    }
    Ok(VerifiedProfileExecutionGeometry {
        geometry: ProfileExecutionGeometry {
            memory_words,
            profile,
            word_trits,
        },
        proof_kind: ProfileWidthProofKind::InitialHalt,
        source: Box::from(source),
    })
}

fn derived_memory_words(
    profile: &ProfileDescriptor,
    word_trits: u8,
) -> Result<u32, ProfileWidthVerificationError> {
    if word_trits < MINIMUM_ADAPTIVE_WORD_TRITS
        || word_trits > profile.word_trits()
    {
        return Err(ProfileWidthVerificationError::WidthOutOfRange {
            profile_word_trits: profile.word_trits(),
            requested: word_trits,
        });
    }
    let mut memory_words = 1u32;
    for _trit in 0..word_trits {
        memory_words = memory_words
            .checked_mul(TERNARY_RADIX)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    }
    if memory_words > profile.memory_words() {
        return Err(ProfileWidthVerificationError::GeometryInvariant);
    }
    Ok(memory_words)
}
