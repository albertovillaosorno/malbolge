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
    encrypt_profile_cell, profile_rotate,
};
use crate::word::profile_crazy;

const MINIMUM_ADAPTIVE_WORD_TRITS: u8 = 10;
const TERNARY_RADIX: u32 = 3;

type GuardedCrazyProjectionState = (u32, u32, u32);

type InstructionDiagnostic = (&'static str, u8, u32);

type ProfileWidthVerifier = fn(
    &'static ProfileDescriptor,
    &[u8],
    u8,
) -> Result<
    VerifiedProfileExecutionGeometry,
    ProfileWidthVerificationError,
>;

type SourceBackedCodeJumpState = (u32, u32);

struct SourceBackedCodeJumpPrefix {
    code_pointer: u32,
    data_pointer: u32,
    decoded: u8,
    jumps: usize,
    shadow: Vec<u32>,
}

struct DecodedSourceInstruction {
    decoded: u8,
    pointer: u32,
}

type MinimumProfileWidthVerifier = fn(
    &'static ProfileDescriptor,
    &[u8],
) -> Result<
    VerifiedProfileExecutionGeometry,
    ProfileWidthVerificationError,
>;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ProfileExecutionInputPolicy {
    Any,
    MinimumLength(usize),
}

struct RepeatedJumpContext<'memory> {
    canonical_word_trits: u8,
    memory_words: u32,
    narrow: &'memory [u32],
    wide: &'memory [u32],
    word_trits: u8,
}

/// Stable proof family that independently admitted one derived geometry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileWidthProofKind {
    /// Source loading succeeds and the first decoded instruction halts.
    InitialHalt,
    /// Input, output, then halt is safe only for nonempty input.
    InputOutputHaltProjection,
    /// One input transition is followed immediately by halt.
    InputThenHaltProjection,
    /// One or more exact code jumps encrypt source targets before halt.
    JumpCodeHaltProjection,
    /// Source-backed code jumps reach byte input/output before halt.
    JumpCodeIoHaltProjection,
    /// Source-backed code jumps reach one projection-compatible rotate.
    JumpCodeRotateHaltProjection,
    /// One exact jump enables one guarded crazy transition before halt.
    JumpCrazyHaltProjection,
    /// Guarded crazy projection is reset by exact byte input before output.
    JumpCrazyIoHaltProjection,
    /// One exact-address data jump is followed immediately by halt.
    JumpDataHaltProjection,
    /// Exact jump/no-ops reach one projection-compatible rotate before halt.
    JumpRotateHaltProjection,
    /// Projected rotate is recovered by exact byte input before output.
    JumpRotateIoHaltProjection,
    /// One or more decoded no-ops precede the first reached halt.
    NoopPrefixHalt,
    /// Repeated exact-address data jumps reach halt safely.
    RepeatedJumpDataProjection,
    /// Straight-line no-op/input/output composition reaches halt safely.
    StraightLineIoProjection,
}

/// Opaque execution-geometry authority emitted only by trusted verification.
///
/// Public accessors expose geometry only. Hidden admission constraints remain
/// inseparable from the copyable token and are rechecked by runtime state APIs.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProfileExecutionGeometry {
    input_policy: ProfileExecutionInputPolicy,
    memory_words: u32,
    profile: &'static ProfileDescriptor,
    word_trits: u8,
}

impl ProfileExecutionGeometry {
    pub(crate) const fn admits_input(self, input: &[u8]) -> bool {
        match self.input_policy {
            ProfileExecutionInputPolicy::Any => true,
            ProfileExecutionInputPolicy::MinimumLength(required) => {
                input.len() >= required
            },
        }
    }

    pub(crate) const fn canonical(profile: &'static ProfileDescriptor) -> Self {
        Self {
            input_policy: ProfileExecutionInputPolicy::Any,
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
    /// A reached input-output-halt position decoded to another instruction.
    InputOutputHaltInstruction {
        /// Exact loaded source position of the rejected instruction.
        position: u32,
        /// Exact decoded instruction byte.
        decoded: u8,
    },
    /// A reached input-then-halt position decoded to another instruction.
    InputThenHaltInstruction {
        /// Exact loaded source position of the rejected instruction.
        position: u32,
        /// Exact decoded instruction byte.
        decoded: u8,
    },
    /// A reached jump-code-halt position decoded to another instruction.
    JumpCodeHaltInstruction {
        /// Exact loaded source position of the rejected instruction.
        position: u32,
        /// Exact decoded instruction byte.
        decoded: u8,
    },
    /// A reached jump-code/input/output/halt position decoded differently.
    JumpCodeIoHaltInstruction {
        /// Exact loaded source position of the rejected instruction.
        position: u32,
        /// Exact decoded instruction byte.
        decoded: u8,
    },
    /// Exact source-backed code-jump premises did not hold.
    JumpCodeProjection,
    /// A reached jump-code/rotate/halt position decoded differently.
    JumpCodeRotateHaltInstruction {
        /// Exact loaded source position of the rejected instruction.
        position: u32,
        /// Exact decoded instruction byte.
        decoded: u8,
    },
    /// Source-backed rotate projection or write placement did not hold.
    JumpCodeRotateProjection,
    /// A reached jump-crazy-halt position decoded to another instruction.
    JumpCrazyHaltInstruction {
        /// Exact loaded source position of the rejected instruction.
        position: u32,
        /// Exact decoded instruction byte.
        decoded: u8,
    },
    /// Guarded crazy projection or exact-address premises did not hold.
    JumpCrazyProjection,
    /// A reached jump-data-halt position decoded to another instruction.
    JumpDataHaltInstruction {
        /// Exact loaded source position of the rejected instruction.
        position: u32,
        /// Exact decoded instruction byte.
        decoded: u8,
    },
    /// A reached jump/rotate/halt position decoded to another instruction.
    JumpRotateHaltInstruction {
        /// Exact loaded source position of the rejected instruction.
        position: u32,
        /// Exact decoded instruction byte.
        decoded: u8,
    },
    /// The exact-address rotate did not preserve candidate projection.
    JumpRotateProjection,
    /// A reached prefix instruction is neither an admitted no-op nor halt.
    NoopPrefixInstruction {
        /// Exact loaded source position of the rejected instruction.
        position: u32,
        /// Exact decoded instruction byte.
        decoded: u8,
    },
    /// The admitted source ended before a no-op prefix reached halt.
    NoopPrefixMissingHalt,
    /// A repeated-jump position decoded to another instruction.
    RepeatedJumpInstruction {
        /// Exact loaded source position of the rejected instruction.
        position: u32,
        /// Exact decoded instruction byte.
        decoded: u8,
    },
    /// A repeated jump read does not name the same exact initial word.
    RepeatedJumpMemoryMismatch {
        /// Exact data address whose initial words differed or were already
        /// code.
        address: u32,
    },
    /// The source did not provide at least two jumps followed by halt.
    RepeatedJumpMissingHalt,
    /// The exact source fails ordinary profile-loader admission.
    Source(ProfileLoadError),
    /// A reached straight-line position decoded to an unsupported instruction.
    StraightLineInstruction {
        /// Exact loaded source position of the rejected instruction.
        position: u32,
        /// Exact decoded instruction byte.
        decoded: u8,
    },
    /// The admitted straight-line prefix ended before reaching halt.
    StraightLineMissingHalt,
    /// Candidate width is outside the reviewed adaptive interval.
    WidthOutOfRange {
        /// Maximum width owned by the canonical profile.
        profile_word_trits: u8,
        /// Rejected requested width.
        requested: u8,
    },
}

impl ProfileWidthVerificationError {
    fn fmt_instruction(
        formatter: &mut Formatter<'_>,
        family: &str,
        decoded: u8,
        position: u32,
    ) -> FormatResult {
        write!(
            formatter,
            "derived {family} instruction {decoded} at {position} is invalid"
        )
    }

    const fn instruction_parts(self) -> Option<InstructionDiagnostic> {
        match self {
            Self::InputOutputHaltInstruction { position, decoded } => {
                Some(("input-output-halt", decoded, position))
            },
            Self::InputThenHaltInstruction { position, decoded } => {
                Some(("input-halt", decoded, position))
            },
            Self::JumpCodeHaltInstruction { position, decoded } => {
                Some(("jump-code-halt", decoded, position))
            },
            Self::JumpCodeIoHaltInstruction { position, decoded } => {
                Some(("jump-code-I/O-halt", decoded, position))
            },
            Self::JumpCodeRotateHaltInstruction { position, decoded } => {
                Some(("jump-code-rotate-halt", decoded, position))
            },
            Self::JumpCrazyHaltInstruction { position, decoded } => {
                Some(("jump-crazy", decoded, position))
            },
            Self::JumpDataHaltInstruction { position, decoded } => {
                Some(("jump-data-halt", decoded, position))
            },
            Self::JumpRotateHaltInstruction { position, decoded } => {
                Some(("jump-rotate-halt", decoded, position))
            },
            Self::NoopPrefixInstruction { position, decoded } => {
                Some(("no-op prefix", decoded, position))
            },
            Self::RepeatedJumpInstruction { position, decoded } => {
                Some(("repeated-jump", decoded, position))
            },
            Self::StraightLineInstruction { position, decoded } => {
                Some(("straight-line", decoded, position))
            },
            Self::GeometryInvariant
            | Self::InitialInstructionNotHalt { .. }
            | Self::JumpCodeProjection
            | Self::JumpCodeRotateProjection
            | Self::JumpCrazyProjection
            | Self::JumpRotateProjection
            | Self::NoopPrefixMissingHalt
            | Self::RepeatedJumpMemoryMismatch { .. }
            | Self::RepeatedJumpMissingHalt
            | Self::Source(_)
            | Self::StraightLineMissingHalt
            | Self::WidthOutOfRange { .. } => None,
        }
    }
}

impl Display for ProfileWidthVerificationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        if let Some((family, decoded, position)) = self.instruction_parts() {
            return Self::fmt_instruction(f, family, decoded, position);
        }
        match self {
            Self::GeometryInvariant => {
                f.write_str("derived profile geometry invariant failed")
            },
            Self::InitialInstructionNotHalt { decoded } => write!(
                f,
                "derived profile initial instruction {decoded} is not halt"
            ),
            Self::JumpCodeProjection => {
                f.write_str("derived jump-code projection premise failed")
            },
            Self::JumpCodeRotateProjection => f.write_str(
                "derived jump-code rotate projection premise failed",
            ),
            Self::JumpCrazyProjection => {
                f.write_str("derived jump-crazy projection premise failed")
            },
            Self::JumpRotateProjection => {
                f.write_str("derived jump-rotate projection premise failed")
            },
            Self::NoopPrefixMissingHalt => {
                f.write_str("derived no-op prefix does not reach halt")
            },
            Self::RepeatedJumpMemoryMismatch { address } => {
                write!(f, "derived repeated-jump memory differs at {address}")
            },
            Self::RepeatedJumpMissingHalt => {
                f.write_str("derived repeated jumps do not reach halt")
            },
            Self::Source(error) => Display::fmt(error, f),
            Self::StraightLineMissingHalt => {
                f.write_str("derived straight-line prefix does not reach halt")
            },
            Self::WidthOutOfRange {
                profile_word_trits,
                requested,
            } => {
                write!(f, "derived profile width {requested} outside ")?;
                write!(f, "10..={profile_word_trits}")
            },
            Self::InputOutputHaltInstruction { .. }
            | Self::InputThenHaltInstruction { .. }
            | Self::JumpCodeHaltInstruction { .. }
            | Self::JumpCodeIoHaltInstruction { .. }
            | Self::JumpCodeRotateHaltInstruction { .. }
            | Self::JumpCrazyHaltInstruction { .. }
            | Self::JumpDataHaltInstruction { .. }
            | Self::JumpRotateHaltInstruction { .. }
            | Self::NoopPrefixInstruction { .. }
            | Self::RepeatedJumpInstruction { .. }
            | Self::StraightLineInstruction { .. } => {
                f.write_str("unreachable profile-width instruction diagnostic")
            },
        }
    }
}

impl From<ProfileLoadError> for ProfileWidthVerificationError {
    fn from(error: ProfileLoadError) -> Self {
        Self::Source(error)
    }
}

fn verify_minimum_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    candidate_verifier: ProfileWidthVerifier,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let mut capacity_error = None;
    for word_trits in MINIMUM_ADAPTIVE_WORD_TRITS..=profile.word_trits() {
        match candidate_verifier(profile, source, word_trits) {
            Ok(admission) => return Ok(admission),
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

/// Selects the narrowest supported proof that admits this exact input domain.
///
/// Every candidate is produced by an independent trusted theorem verifier.
/// Failed theorem families are ignored as non-evidence; a successful candidate
/// is returned only when it is strictly narrower than the canonical profile and
/// its hidden input policy admits `input`. Equal-width proof tokens therefore
/// do not replace canonical execution.
#[must_use]
pub fn select_minimum_verified_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    input: &[u8],
) -> Option<VerifiedProfileExecutionGeometry> {
    let verifiers: [MinimumProfileWidthVerifier; 14] = [
        verify_minimum_initial_halt_profile_width,
        verify_minimum_input_output_halt_profile_width,
        verify_minimum_input_then_halt_profile_width,
        verify_minimum_jump_code_halt_profile_width,
        verify_minimum_jump_code_io_halt_profile_width,
        verify_minimum_jump_code_rotate_halt_profile_width,
        verify_minimum_jump_crazy_halt_profile_width,
        verify_minimum_jump_crazy_io_halt_profile_width,
        verify_minimum_jump_data_halt_profile_width,
        verify_minimum_jump_rotate_halt_profile_width,
        verify_minimum_jump_rotate_io_halt_profile_width,
        verify_minimum_noop_prefix_halt_profile_width,
        verify_minimum_repeated_jump_data_profile_width,
        verify_minimum_straight_line_io_profile_width,
    ];
    let mut selected: Option<VerifiedProfileExecutionGeometry> = None;
    for verifier in verifiers {
        let Ok(candidate) = verifier(profile, source) else {
            continue;
        };
        if candidate.word_trits() >= profile.word_trits()
            || !candidate.geometry().admits_input(input)
        {
            continue;
        }
        if selected
            .as_ref()
            .is_none_or(|current| candidate.word_trits() < current.word_trits())
        {
            selected = Some(candidate);
        }
    }
    selected
}

/// Selects the minimum independently verified input-output-halt width.
///
/// The returned proof token admits only nonempty runtime input. Capacity is the
/// only reason a candidate may widen.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed candidate admits
/// the exact source under the input-output-halt theorem.
pub fn verify_minimum_input_output_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    verify_minimum_width(
        profile,
        source,
        verify_input_output_halt_profile_width,
    )
}

/// Selects the minimum independently verified input-then-halt width.
///
/// Only derived-capacity rejection advances to a wider candidate. Any theorem
/// or source-admission failure rejects without widening around the evidence.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed candidate admits
/// the exact source under the input-then-halt theorem.
pub fn verify_minimum_input_then_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    verify_minimum_width(profile, source, verify_input_then_halt_profile_width)
}

/// Selects the minimum independently verified repeated-jump width.
///
/// Each jump retains exact D only after candidate/canonical initial-memory
/// equality is independently recomputed. Capacity is the only widening reason.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed candidate admits
/// the exact source under the repeated-jump theorem.
pub fn verify_minimum_repeated_jump_data_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    verify_minimum_width(
        profile,
        source,
        verify_repeated_jump_data_profile_width,
    )
}

/// Selects the minimum independently verified straight-line I/O width.
///
/// The returned token carries the minimum input length proved sufficient by the
/// reached no-op/input/output prefix. Capacity is the only widening reason.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed candidate admits
/// the source under the straight-line I/O theorem.
pub fn verify_minimum_straight_line_io_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    verify_minimum_width(profile, source, verify_straight_line_io_profile_width)
}

/// Selects the minimum independently verified source-backed jump-code width.
///
/// The theorem requires every reached jump data read, encryption target, and
/// successor to remain exact loaded-source cells, so only capacity may widen.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed candidate admits
/// the source under the exact source-backed jump-code theorem.
pub fn verify_minimum_jump_code_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    verify_minimum_width(profile, source, verify_jump_code_halt_profile_width)
}

/// Selects the minimum source-backed jump-code/input/output/halt width.
///
/// The returned token requires one runtime input byte. Capacity is the only
/// reason a candidate may widen; theorem failures remain fail-closed.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed candidate proves
/// the exact code-jump prefix and byte-visible I/O suffix.
pub fn verify_minimum_jump_code_io_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    verify_minimum_width(
        profile,
        source,
        verify_jump_code_io_halt_profile_width,
    )
}

/// Selects the narrowest source-backed jump-code/rotate/halt width.
///
/// Rotate projection is non-monotone across ternary widths. Explicit projection
/// misses and source capacity may continue to a wider reviewed candidate; all
/// other theorem failures remain fail-closed.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed width proves the
/// exact source-backed jump prefix and rotate projection before halt.
pub fn verify_minimum_jump_code_rotate_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let mut last_width_miss = None;
    for word_trits in MINIMUM_ADAPTIVE_WORD_TRITS..=profile.word_trits() {
        match verify_jump_code_rotate_halt_profile_width(
            profile,
            source,
            word_trits,
        ) {
            Ok(admission) => return Ok(admission),
            Err(
                error @ (ProfileWidthVerificationError::Source(
                    ProfileLoadError::SourceTooLong,
                )
                | ProfileWidthVerificationError::JumpCodeRotateProjection),
            ) => {
                last_width_miss = Some(error);
            },
            Err(error) => return Err(error),
        }
    }
    Err(last_width_miss.unwrap_or_else(|| {
        ProfileWidthVerificationError::WidthOutOfRange {
            profile_word_trits: profile.word_trits(),
            requested: MINIMUM_ADAPTIVE_WORD_TRITS,
        }
    }))
}

/// Selects the minimum independently verified jump-crazy-halt width.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed candidate proves
/// the exact-address crazy projection before halt.
pub fn verify_minimum_jump_crazy_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    verify_minimum_width(profile, source, verify_jump_crazy_halt_profile_width)
}

/// Selects the minimum guarded-crazy/input/output/halt width.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed candidate proves
/// the exact-address crazy prefix and byte-exact input recovery before output.
pub fn verify_minimum_jump_crazy_io_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    verify_minimum_width(
        profile,
        source,
        verify_jump_crazy_io_halt_profile_width,
    )
}

/// Selects the minimum independently verified jump-data-halt width.
///
/// The first data read remains an exact low source address/value at every
/// reviewed width. Capacity remains the only widening reason.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed candidate admits
/// the exact source under the jump-data-halt theorem.
pub fn verify_minimum_jump_data_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    verify_minimum_width(profile, source, verify_jump_data_halt_profile_width)
}

/// Selects the narrowest projection-compatible jump/rotate/halt width.
///
/// Rotate compatibility is intentionally non-monotone across ternary widths.
/// This selector may therefore continue after an explicit rotate-projection
/// miss, while lexical/decode/geometry failures still fail closed immediately.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed width admits the
/// exact source under the jump/rotate/halt theorem.
pub fn verify_minimum_jump_rotate_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let mut last_width_miss = None;
    for word_trits in MINIMUM_ADAPTIVE_WORD_TRITS..=profile.word_trits() {
        match verify_jump_rotate_halt_profile_width(profile, source, word_trits)
        {
            Ok(admission) => return Ok(admission),
            Err(
                error @ (ProfileWidthVerificationError::Source(
                    ProfileLoadError::SourceTooLong,
                )
                | ProfileWidthVerificationError::JumpRotateProjection),
            ) => {
                last_width_miss = Some(error);
            },
            Err(error) => return Err(error),
        }
    }
    Err(last_width_miss.unwrap_or_else(|| {
        ProfileWidthVerificationError::WidthOutOfRange {
            profile_word_trits: profile.word_trits(),
            requested: MINIMUM_ADAPTIVE_WORD_TRITS,
        }
    }))
}

/// Selects the narrowest jump/rotate/input/output/halt width.
///
/// Rotate compatibility is non-monotone, so an explicit projection miss may
/// continue to a wider reviewed candidate. All other theorem failures remain
/// fail-closed. The returned token requires the exact reached input count.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when no reviewed width proves the
/// projected rotate followed by exact byte recovery and output.
pub fn verify_minimum_jump_rotate_io_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let mut last_width_miss = None;
    for word_trits in MINIMUM_ADAPTIVE_WORD_TRITS..=profile.word_trits() {
        match verify_jump_rotate_io_halt_profile_width(
            profile, source, word_trits,
        ) {
            Ok(admission) => return Ok(admission),
            Err(
                error @ (ProfileWidthVerificationError::Source(
                    ProfileLoadError::SourceTooLong,
                )
                | ProfileWidthVerificationError::JumpRotateProjection),
            ) => {
                last_width_miss = Some(error);
            },
            Err(error) => return Err(error),
        }
    }
    Err(last_width_miss.unwrap_or_else(|| {
        ProfileWidthVerificationError::WidthOutOfRange {
            profile_word_trits: profile.word_trits(),
            requested: MINIMUM_ADAPTIVE_WORD_TRITS,
        }
    }))
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
    verify_minimum_width(profile, source, verify_noop_prefix_halt_profile_width)
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
    verify_minimum_width(profile, source, verify_initial_halt_profile_width)
}

/// Independently verifies input, output, then halt for nonempty input.
///
/// The first input byte becomes an exact accumulator value at every reviewed
/// width, so the following output is byte-identical. EOF is deliberately
/// outside this proof token because its low byte depends on the selected width.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when geometry, source admission,
/// or the required input/output/halt sequence does not hold.
pub fn verify_input_output_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let admitted = admit_profile_source(source, memory_words)?;
    let expected = [
        profile.input_instruction(),
        profile.output_instruction(),
        b'v',
    ];
    for (position, expected_instruction) in expected.into_iter().enumerate() {
        let pointer = u32::try_from(position).map_err(|_error| {
            ProfileWidthVerificationError::GeometryInvariant
        })?;
        let cell = admitted
            .get(position)
            .copied()
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        let decoded = decode_profile_instruction(cell, pointer)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        if decoded != expected_instruction {
            return Err(
                ProfileWidthVerificationError::InputOutputHaltInstruction {
                    position: pointer,
                    decoded,
                },
            );
        }
    }
    Ok(VerifiedProfileExecutionGeometry {
        geometry: ProfileExecutionGeometry {
            input_policy: ProfileExecutionInputPolicy::MinimumLength(1),
            memory_words,
            profile,
            word_trits,
        },
        proof_kind: ProfileWidthProofKind::InputOutputHaltProjection,
        source: Box::from(source),
    })
}

/// Independently verifies one input transition followed directly by halt.
///
/// The theorem is input-domain independent: a consumed byte is identical at all
/// reviewed widths, while EOF is each geometry's exact all-two-trit word. The
/// following halt occurs before either value can become width-sensitive output.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when geometry, source admission,
/// input decode, or the immediately following halt does not hold.
pub fn verify_input_then_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let admitted = admit_profile_source(source, memory_words)?;
    let expected = [profile.input_instruction(), b'v'];
    for (position, expected_instruction) in expected.into_iter().enumerate() {
        let pointer = u32::try_from(position).map_err(|_error| {
            ProfileWidthVerificationError::GeometryInvariant
        })?;
        let cell = admitted
            .get(position)
            .copied()
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        let decoded = decode_profile_instruction(cell, pointer)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        if decoded != expected_instruction {
            return Err(
                ProfileWidthVerificationError::InputThenHaltInstruction {
                    position: pointer,
                    decoded,
                },
            );
        }
    }
    Ok(VerifiedProfileExecutionGeometry {
        geometry: ProfileExecutionGeometry {
            input_policy: ProfileExecutionInputPolicy::Any,
            memory_words,
            profile,
            word_trits,
        },
        proof_kind: ProfileWidthProofKind::InputThenHaltProjection,
        source: Box::from(source),
    })
}

fn verified_initial_memory_word(
    source_words: &[u32],
    word_trits: u8,
    address: u32,
) -> Result<u32, ProfileWidthVerificationError> {
    let index = usize::try_from(address)
        .map_err(|_error| ProfileWidthVerificationError::GeometryInvariant)?;
    if let Some(value) = source_words.get(index).copied() {
        return Ok(value);
    }
    let mut previous = source_words
        .last()
        .copied()
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    let older_index = source_words.len().saturating_sub(2);
    let mut older = source_words
        .get(older_index)
        .copied()
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    for _position in source_words.len()..=index {
        let next = profile_crazy(older, previous, word_trits);
        older = previous;
        previous = next;
    }
    Ok(previous)
}

fn advance_verified_jump_address(
    context: &RepeatedJumpContext<'_>,
    data_address: u32,
    code_pointer: u32,
) -> Result<u32, ProfileWidthVerificationError> {
    if data_address < code_pointer
        && usize::try_from(data_address)
            .is_ok_and(|address| address < context.narrow.len())
    {
        return Err(
            ProfileWidthVerificationError::RepeatedJumpMemoryMismatch {
                address: data_address,
            },
        );
    }
    let narrow_word = verified_initial_memory_word(
        context.narrow,
        context.word_trits,
        data_address,
    )?;
    let wide_word = verified_initial_memory_word(
        context.wide,
        context.canonical_word_trits,
        data_address,
    )?;
    if narrow_word != wide_word {
        return Err(
            ProfileWidthVerificationError::RepeatedJumpMemoryMismatch {
                address: data_address,
            },
        );
    }
    narrow_word
        .checked_add(1)
        .filter(|next| *next < context.memory_words)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)
}

/// Independently verifies repeated exact data jumps followed by halt.
///
/// Every jump must read an unmodified exact initial word whose candidate and
/// canonical values are numerically identical. This preserves physical D rather
/// than relying on ternary projection alone.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when source admission, jump shape,
/// memory equality, successor domain, or the following halt does not hold.
pub fn verify_repeated_jump_data_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let narrow = admit_profile_source(source, memory_words)?;
    let wide = admit_profile_source(source, profile.memory_words())?;
    let context = RepeatedJumpContext {
        canonical_word_trits: profile.word_trits(),
        memory_words,
        narrow: &narrow,
        wide: &wide,
        word_trits,
    };
    let mut data_address = 0u32;
    let mut jumps = 0usize;
    for (position, cell) in narrow.iter().copied().enumerate() {
        let pointer = u32::try_from(position).map_err(|_error| {
            ProfileWidthVerificationError::GeometryInvariant
        })?;
        let decoded = decode_profile_instruction(cell, pointer)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        if decoded == b'v' {
            if jumps < 2 {
                return Err(
                    ProfileWidthVerificationError::RepeatedJumpMissingHalt,
                );
            }
            return Ok(VerifiedProfileExecutionGeometry {
                geometry: ProfileExecutionGeometry {
                    input_policy: ProfileExecutionInputPolicy::Any,
                    memory_words,
                    profile,
                    word_trits,
                },
                proof_kind: ProfileWidthProofKind::RepeatedJumpDataProjection,
                source: Box::from(source),
            });
        }
        if decoded != b'j' {
            return Err(
                ProfileWidthVerificationError::RepeatedJumpInstruction {
                    position: pointer,
                    decoded,
                },
            );
        }
        data_address =
            advance_verified_jump_address(&context, data_address, pointer)?;
        jumps = jumps.saturating_add(1);
    }
    Err(ProfileWidthVerificationError::RepeatedJumpMissingHalt)
}

/// Independently verifies straight-line no-op/input/output execution to halt.
///
/// The abstract accumulator starts byte-exact. Input increments the encountered
/// input ordinal, and each later output raises the required immutable input
/// length to that ordinal. No-op preserves exactness. Other opcodes fail
/// closed.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when geometry, source admission, a
/// reached opcode, or the required following halt violates this theorem.
pub fn verify_straight_line_io_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let admitted = admit_profile_source(source, memory_words)?;
    let mut input_ordinal = 0usize;
    let mut required_input_len = 0usize;
    for (position, cell) in admitted.iter().copied().enumerate() {
        let pointer = u32::try_from(position).map_err(|_error| {
            ProfileWidthVerificationError::GeometryInvariant
        })?;
        let decoded = decode_profile_instruction(cell, pointer)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        if decoded == b'v' {
            return Ok(VerifiedProfileExecutionGeometry {
                geometry: ProfileExecutionGeometry {
                    input_policy: ProfileExecutionInputPolicy::MinimumLength(
                        required_input_len,
                    ),
                    memory_words,
                    profile,
                    word_trits,
                },
                proof_kind: ProfileWidthProofKind::StraightLineIoProjection,
                source: Box::from(source),
            });
        }
        if decoded == profile.input_instruction() {
            input_ordinal = input_ordinal.saturating_add(1);
            continue;
        }
        if decoded == profile.output_instruction() {
            required_input_len = required_input_len.max(input_ordinal);
            continue;
        }
        if decoded != b'o' {
            return Err(
                ProfileWidthVerificationError::StraightLineInstruction {
                    position: pointer,
                    decoded,
                },
            );
        }
    }
    Err(ProfileWidthVerificationError::StraightLineMissingHalt)
}

fn advance_guarded_crazy_projection(
    source_words: &[u32],
    geometry: ProfileExecutionGeometry,
    state: GuardedCrazyProjectionState,
    code_pointer: u32,
) -> Result<GuardedCrazyProjectionState, ProfileWidthVerificationError> {
    let (data_address, narrow_accumulator, wide_accumulator) = state;
    if data_address == code_pointer
        || usize::try_from(data_address).is_ok_and(|address| {
            address > usize::try_from(code_pointer).unwrap_or(usize::MAX)
                && address < source_words.len()
        })
    {
        return Err(ProfileWidthVerificationError::JumpCrazyProjection);
    }
    let narrow_data = verified_initial_memory_word(
        source_words,
        geometry.word_trits(),
        data_address,
    )?;
    let wide_data = verified_initial_memory_word(
        source_words,
        geometry.profile().word_trits(),
        data_address,
    )?;
    if wide_data.rem_euclid(geometry.memory_words()) != narrow_data {
        return Err(ProfileWidthVerificationError::JumpCrazyProjection);
    }
    let narrow_crazy =
        profile_crazy(narrow_data, narrow_accumulator, geometry.word_trits());
    let wide_crazy = profile_crazy(
        wide_data,
        wide_accumulator,
        geometry.profile().word_trits(),
    );
    if wide_crazy.rem_euclid(geometry.memory_words()) != narrow_crazy {
        return Err(ProfileWidthVerificationError::JumpCrazyProjection);
    }
    let next_address = data_address
        .checked_add(1)
        .filter(|address| *address < geometry.memory_words())
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    Ok((next_address, narrow_crazy, wide_crazy))
}

fn advance_source_backed_code_jump(
    shadow: &mut [u32],
    data_pointer: u32,
    memory_words: u32,
) -> Result<SourceBackedCodeJumpState, ProfileWidthVerificationError> {
    let data_index = usize::try_from(data_pointer)
        .map_err(|_error| ProfileWidthVerificationError::GeometryInvariant)?;
    let target_word = shadow
        .get(data_index)
        .copied()
        .ok_or(ProfileWidthVerificationError::JumpCodeProjection)?;
    let target_index = usize::try_from(target_word)
        .map_err(|_error| ProfileWidthVerificationError::GeometryInvariant)?;
    let target_cell = shadow
        .get(target_index)
        .copied()
        .ok_or(ProfileWidthVerificationError::JumpCodeProjection)?;
    let encrypted = encrypt_profile_cell(target_cell)
        .ok_or(ProfileWidthVerificationError::JumpCodeProjection)?;
    let next_code = target_word
        .checked_add(1)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    let next_code_index = usize::try_from(next_code)
        .map_err(|_error| ProfileWidthVerificationError::GeometryInvariant)?;
    if shadow.get(next_code_index).is_none() {
        return Err(ProfileWidthVerificationError::JumpCodeProjection);
    }
    let next_data = data_pointer
        .checked_add(1)
        .filter(|address| *address < memory_words)
        .ok_or(ProfileWidthVerificationError::JumpCodeProjection)?;
    let target = shadow
        .get_mut(target_index)
        .ok_or(ProfileWidthVerificationError::JumpCodeProjection)?;
    *target = encrypted;
    Ok((next_code, next_data))
}

fn verify_source_backed_code_jump_prefix(
    source: &[u8],
    memory_words: u32,
) -> Result<SourceBackedCodeJumpPrefix, ProfileWidthVerificationError> {
    let mut shadow = admit_profile_source(source, memory_words)?;
    let mut code_pointer = 0u32;
    let mut data_pointer = 0u32;
    let mut jumps = 0usize;
    for _step in 0..=shadow.len() {
        let code_index = usize::try_from(code_pointer).map_err(|_error| {
            ProfileWidthVerificationError::GeometryInvariant
        })?;
        let cell = shadow
            .get(code_index)
            .copied()
            .ok_or(ProfileWidthVerificationError::JumpCodeProjection)?;
        let decoded = decode_profile_instruction(cell, code_pointer)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        if decoded != b'i' {
            return Ok(SourceBackedCodeJumpPrefix {
                code_pointer,
                data_pointer,
                decoded,
                jumps,
                shadow,
            });
        }
        (code_pointer, data_pointer) = advance_source_backed_code_jump(
            &mut shadow,
            data_pointer,
            memory_words,
        )?;
        jumps = jumps.saturating_add(1);
    }
    Err(ProfileWidthVerificationError::JumpCodeProjection)
}

fn advance_source_backed_expected_instruction(
    prefix: &mut SourceBackedCodeJumpPrefix,
    expected: u8,
    memory_words: u32,
) -> Result<(), ProfileWidthVerificationError> {
    if prefix.decoded != expected {
        return Err(ProfileWidthVerificationError::JumpCodeIoHaltInstruction {
            position: prefix.code_pointer,
            decoded: prefix.decoded,
        });
    }
    (prefix.code_pointer, prefix.data_pointer) =
        advance_source_backed_ordinary_instruction(
            &mut prefix.shadow,
            prefix.code_pointer,
            prefix.data_pointer,
            memory_words,
        )?;
    let code_index = usize::try_from(prefix.code_pointer)
        .map_err(|_error| ProfileWidthVerificationError::GeometryInvariant)?;
    let cell = prefix
        .shadow
        .get(code_index)
        .copied()
        .ok_or(ProfileWidthVerificationError::JumpCodeProjection)?;
    prefix.decoded = decode_profile_instruction(cell, prefix.code_pointer)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    Ok(())
}

fn advance_source_backed_ordinary_instruction(
    shadow: &mut [u32],
    code_pointer: u32,
    data_pointer: u32,
    memory_words: u32,
) -> Result<SourceBackedCodeJumpState, ProfileWidthVerificationError> {
    let code_index = usize::try_from(code_pointer)
        .map_err(|_error| ProfileWidthVerificationError::GeometryInvariant)?;
    let cell = shadow
        .get(code_index)
        .copied()
        .ok_or(ProfileWidthVerificationError::JumpCodeProjection)?;
    let encrypted = encrypt_profile_cell(cell)
        .ok_or(ProfileWidthVerificationError::JumpCodeProjection)?;
    let next_code = code_pointer
        .checked_add(1)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    let next_code_index = usize::try_from(next_code)
        .map_err(|_error| ProfileWidthVerificationError::GeometryInvariant)?;
    if shadow.get(next_code_index).is_none() {
        return Err(ProfileWidthVerificationError::JumpCodeProjection);
    }
    let next_data = data_pointer
        .checked_add(1)
        .filter(|address| *address < memory_words)
        .ok_or(ProfileWidthVerificationError::JumpCodeProjection)?;
    let target = shadow
        .get_mut(code_index)
        .ok_or(ProfileWidthVerificationError::JumpCodeProjection)?;
    *target = encrypted;
    Ok((next_code, next_data))
}

/// Verifies one or more exact source-backed code jumps followed by halt.
///
/// Initial D=0 and every committed jump keep D exact without wrap. Each reached
/// `i` reads its data word from the exact loaded-source shadow, so the
/// resulting code pointer is numerically identical at candidate and canonical
/// widths. The self-encryption target and successor must also remain inside
/// that source shadow. Width-independent XLAT2 is applied to the shadow after
/// each jump, allowing later exact reads to observe prior self-encryption
/// without importing recurrence memory into the proof.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when source shape, exact target
/// placement, nonwrapping D, or the reached jump/halt sequence does not hold.
pub fn verify_jump_code_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let prefix = verify_source_backed_code_jump_prefix(source, memory_words)?;
    if prefix.jumps == 0 || prefix.decoded != b'v' {
        return Err(ProfileWidthVerificationError::JumpCodeHaltInstruction {
            position: prefix.code_pointer,
            decoded: prefix.decoded,
        });
    }
    Ok(VerifiedProfileExecutionGeometry {
        geometry: ProfileExecutionGeometry {
            input_policy: ProfileExecutionInputPolicy::Any,
            memory_words,
            profile,
            word_trits,
        },
        proof_kind: ProfileWidthProofKind::JumpCodeHaltProjection,
        source: Box::from(source),
    })
}

/// Verifies source-backed code jumps followed by byte I/O pairs, then halt.
///
/// The exact jump prefix preserves physical C/D and source self-modification.
/// Each required non-EOF input overwrites A with the same byte at candidate and
/// canonical widths; its following output emits that byte exactly. The reached
/// input/output code cells are source-backed and encrypted identically before
/// the exact halt. The hidden policy requires exactly the number of input bytes
/// needed by the reached I/O pairs.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when the source-backed jump
/// prefix, exact I/O suffix, or nonwrapping C/D premises do not hold.
pub fn verify_jump_code_io_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let mut prefix =
        verify_source_backed_code_jump_prefix(source, memory_words)?;
    if prefix.jumps == 0 {
        return Err(ProfileWidthVerificationError::JumpCodeIoHaltInstruction {
            position: prefix.code_pointer,
            decoded: prefix.decoded,
        });
    }
    let mut required_input = 0usize;
    while prefix.decoded != b'v' {
        required_input = required_input
            .checked_add(1)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        advance_source_backed_expected_instruction(
            &mut prefix,
            profile.input_instruction(),
            memory_words,
        )?;
        advance_source_backed_expected_instruction(
            &mut prefix,
            profile.output_instruction(),
            memory_words,
        )?;
    }
    if required_input == 0 {
        return Err(ProfileWidthVerificationError::JumpCodeIoHaltInstruction {
            position: prefix.code_pointer,
            decoded: prefix.decoded,
        });
    }
    Ok(VerifiedProfileExecutionGeometry {
        geometry: ProfileExecutionGeometry {
            input_policy: ProfileExecutionInputPolicy::MinimumLength(
                required_input,
            ),
            memory_words,
            profile,
            word_trits,
        },
        proof_kind: ProfileWidthProofKind::JumpCodeIoHaltProjection,
        source: Box::from(source),
    })
}

fn verify_source_backed_jump_rotate_projection(
    prefix: &SourceBackedCodeJumpPrefix,
    geometry: ProfileExecutionGeometry,
) -> Result<(), ProfileWidthVerificationError> {
    let data_index = usize::try_from(prefix.data_pointer)
        .map_err(|_error| ProfileWidthVerificationError::GeometryInvariant)?;
    let data = prefix
        .shadow
        .get(data_index)
        .copied()
        .ok_or(ProfileWidthVerificationError::JumpCodeRotateProjection)?;
    let next_code = prefix
        .code_pointer
        .checked_add(1)
        .filter(|address| *address < geometry.memory_words())
        .ok_or(ProfileWidthVerificationError::JumpCodeRotateProjection)?;
    let next_code_index = usize::try_from(next_code)
        .map_err(|_error| ProfileWidthVerificationError::GeometryInvariant)?;
    if prefix.data_pointer == prefix.code_pointer
        || prefix.data_pointer == next_code
        || prefix.shadow.get(next_code_index).is_none()
    {
        return Err(ProfileWidthVerificationError::JumpCodeRotateProjection);
    }
    let narrow_rotate = profile_rotate(data, geometry.word_modulus());
    let wide_rotate = profile_rotate(data, geometry.profile().memory_words());
    if wide_rotate.rem_euclid(geometry.memory_words()) != narrow_rotate {
        return Err(ProfileWidthVerificationError::JumpCodeRotateProjection);
    }
    let _next_data = prefix
        .data_pointer
        .checked_add(1)
        .filter(|address| *address < geometry.memory_words())
        .ok_or(ProfileWidthVerificationError::JumpCodeRotateProjection)?;
    let halt_cell = prefix
        .shadow
        .get(next_code_index)
        .copied()
        .ok_or(ProfileWidthVerificationError::JumpCodeRotateProjection)?;
    let halt_decoded = decode_profile_instruction(halt_cell, next_code)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    if halt_decoded != b'v' {
        return Err(
            ProfileWidthVerificationError::JumpCodeRotateHaltInstruction {
                position: next_code,
                decoded: halt_decoded,
            },
        );
    }
    Ok(())
}

/// Verifies source-backed code jumps followed by one rotate and halt.
///
/// The jump prefix preserves exact physical C/D and a mutable source shadow.
/// The reached rotate must read the same source-backed D word at candidate and
/// canonical widths, write neither the current code cell nor the following
/// halt, and produce a candidate value equal to canonical rotation modulo the
/// derived word domain. The following halt remains an exact untouched source
/// cell.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when the source-backed jump
/// prefix, reached rotate/halt shape, physical write placement, or rotate
/// projection does not hold.
pub fn verify_jump_code_rotate_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let geometry = ProfileExecutionGeometry {
        input_policy: ProfileExecutionInputPolicy::Any,
        memory_words,
        profile,
        word_trits,
    };
    let prefix = verify_source_backed_code_jump_prefix(source, memory_words)?;
    if prefix.jumps == 0 || prefix.decoded != b'*' {
        return Err(
            ProfileWidthVerificationError::JumpCodeRotateHaltInstruction {
                position: prefix.code_pointer,
                decoded: prefix.decoded,
            },
        );
    }
    verify_source_backed_jump_rotate_projection(&prefix, geometry)?;
    Ok(VerifiedProfileExecutionGeometry {
        geometry,
        proof_kind: ProfileWidthProofKind::JumpCodeRotateHaltProjection,
        source: Box::from(source),
    })
}

/// Independently verifies exact jump, guarded crazy prefix, then halt.
///
/// The jump establishes exact D. Every reached crazy must target a distinct
/// exact data address outside current/future source code; candidate/canonical
/// data and accumulator values are checked by projection at each transition.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when shape, exact address, guarded
/// write placement, or any crazy projection does not hold.
pub fn verify_jump_crazy_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let geometry = ProfileExecutionGeometry {
        input_policy: ProfileExecutionInputPolicy::Any,
        memory_words,
        profile,
        word_trits,
    };
    let admitted = admit_profile_source(source, memory_words)?;
    let first = admitted
        .first()
        .copied()
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    let first_decoded = decode_profile_instruction(first, 0)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    if first_decoded != b'j' {
        return Err(ProfileWidthVerificationError::JumpCrazyHaltInstruction {
            position: 0,
            decoded: first_decoded,
        });
    }
    let first_data_address = first
        .checked_add(1)
        .filter(|address| *address < memory_words)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    let mut state = (first_data_address, 0u32, 0u32);
    let mut crazies = 0usize;
    for (position, cell) in admitted.iter().copied().enumerate().skip(1) {
        let pointer = u32::try_from(position).map_err(|_error| {
            ProfileWidthVerificationError::GeometryInvariant
        })?;
        let decoded = decode_profile_instruction(cell, pointer)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        if decoded == b'v' {
            if crazies == 0 {
                return Err(ProfileWidthVerificationError::JumpCrazyProjection);
            }
            return Ok(VerifiedProfileExecutionGeometry {
                geometry,
                proof_kind: ProfileWidthProofKind::JumpCrazyHaltProjection,
                source: Box::from(source),
            });
        }
        if decoded != b'p' {
            return Err(
                ProfileWidthVerificationError::JumpCrazyHaltInstruction {
                    position: pointer,
                    decoded,
                },
            );
        }
        state = advance_guarded_crazy_projection(
            &admitted, geometry, state, pointer,
        )?;
        crazies = crazies.saturating_add(1);
    }
    Err(ProfileWidthVerificationError::JumpCrazyProjection)
}

fn verify_jump_crazy_io_suffix(
    admitted: &[u32],
    geometry: ProfileExecutionGeometry,
    mut data_address: u32,
    mut position: usize,
) -> Result<(), ProfileWidthVerificationError> {
    let profile = geometry.profile();
    let expected = [
        profile.input_instruction(),
        profile.output_instruction(),
        b'v',
    ];
    for expected_instruction in expected {
        let pointer = u32::try_from(position).map_err(|_error| {
            ProfileWidthVerificationError::GeometryInvariant
        })?;
        let cell = admitted
            .get(position)
            .copied()
            .ok_or(ProfileWidthVerificationError::JumpCrazyProjection)?;
        let suffix_decoded = decode_profile_instruction(cell, pointer)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        if suffix_decoded != expected_instruction {
            return Err(
                ProfileWidthVerificationError::JumpCrazyHaltInstruction {
                    position: pointer,
                    decoded: suffix_decoded,
                },
            );
        }
        if expected_instruction != b'v' {
            data_address = data_address
                .checked_add(1)
                .filter(|address| *address < geometry.memory_words())
                .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        }
        position = position.saturating_add(1);
    }
    Ok(())
}

/// Verifies guarded crazy projection recovered by byte input before output.
///
/// The prefix is exactly `j p+ / < v`. Guarded crazy transitions preserve the
/// width projection at exact D; one non-EOF input then restores an identical
/// byte accumulator before output, so no projected crazy value is observed.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when shape, guarded crazy
/// projection, nonwrapping ordinary D advancement, or the recovery suffix
/// fails.
pub fn verify_jump_crazy_io_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let geometry = ProfileExecutionGeometry {
        input_policy: ProfileExecutionInputPolicy::Any,
        memory_words,
        profile,
        word_trits,
    };
    let admitted = admit_profile_source(source, memory_words)?;
    let first = admitted
        .first()
        .copied()
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    let first_decoded = decode_profile_instruction(first, 0)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    if first_decoded != b'j' {
        return Err(ProfileWidthVerificationError::JumpCrazyHaltInstruction {
            position: 0,
            decoded: first_decoded,
        });
    }
    let data_address = first
        .checked_add(1)
        .filter(|address| *address < memory_words)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    let mut state = (data_address, 0u32, 0u32);
    let mut position = 1usize;
    let mut crazies = 0usize;
    while let Some(cell) = admitted.get(position).copied() {
        let pointer = u32::try_from(position).map_err(|_error| {
            ProfileWidthVerificationError::GeometryInvariant
        })?;
        let prefix_decoded = decode_profile_instruction(cell, pointer)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        if prefix_decoded != b'p' {
            break;
        }
        state = advance_guarded_crazy_projection(
            &admitted, geometry, state, pointer,
        )?;
        crazies = crazies.saturating_add(1);
        position = position.saturating_add(1);
    }
    if crazies == 0 {
        return Err(ProfileWidthVerificationError::JumpCrazyProjection);
    }
    verify_jump_crazy_io_suffix(&admitted, geometry, state.0, position)?;
    Ok(VerifiedProfileExecutionGeometry {
        geometry,
        proof_kind: ProfileWidthProofKind::JumpCrazyIoHaltProjection,
        source: Box::from(source),
    })
}

/// Independently verifies one exact initial data jump followed by halt.
///
/// D starts at zero, so the jump reads the first admitted source cell itself.
/// That graphical byte and its nonwrapping successor are identical at every
/// reviewed geometry; the following halt occurs before D is used again.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when geometry, source admission,
/// exact jump premises, or the immediately following halt does not hold.
pub fn verify_jump_data_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let admitted = admit_profile_source(source, memory_words)?;
    let expected = *b"jv";
    for (position, expected_instruction) in expected.into_iter().enumerate() {
        let pointer = u32::try_from(position).map_err(|_error| {
            ProfileWidthVerificationError::GeometryInvariant
        })?;
        let cell = admitted
            .get(position)
            .copied()
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        let decoded = decode_profile_instruction(cell, pointer)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        if decoded != expected_instruction {
            return Err(
                ProfileWidthVerificationError::JumpDataHaltInstruction {
                    position: pointer,
                    decoded,
                },
            );
        }
    }
    let first = admitted
        .first()
        .copied()
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    let successor = first
        .checked_add(1)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    if successor >= memory_words {
        return Err(ProfileWidthVerificationError::GeometryInvariant);
    }
    Ok(VerifiedProfileExecutionGeometry {
        geometry: ProfileExecutionGeometry {
            input_policy: ProfileExecutionInputPolicy::Any,
            memory_words,
            profile,
            word_trits,
        },
        proof_kind: ProfileWidthProofKind::JumpDataHaltProjection,
        source: Box::from(source),
    })
}

fn jump_rotate_initial_address(
    admitted: &[u32],
    memory_words: u32,
) -> Result<u32, ProfileWidthVerificationError> {
    let first = admitted
        .first()
        .copied()
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    let decoded = decode_profile_instruction(first, 0)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    if decoded != b'j' {
        return Err(ProfileWidthVerificationError::JumpRotateHaltInstruction {
            position: 0,
            decoded,
        });
    }
    first
        .checked_add(1)
        .filter(|address| *address < memory_words)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)
}

fn advance_jump_rotate_address(
    data_address: u32,
    memory_words: u32,
) -> Result<u32, ProfileWidthVerificationError> {
    data_address
        .checked_add(1)
        .filter(|address| *address < memory_words)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)
}

fn verify_jump_rotate_projection(
    admitted: &[u32],
    geometry: ProfileExecutionGeometry,
    data_address: u32,
) -> Result<(), ProfileWidthVerificationError> {
    if usize::try_from(data_address)
        .is_ok_and(|address| address < admitted.len())
    {
        return Err(ProfileWidthVerificationError::JumpRotateProjection);
    }
    let narrow_data = verified_initial_memory_word(
        admitted,
        geometry.word_trits(),
        data_address,
    )?;
    let profile = geometry.profile();
    let wide_data = verified_initial_memory_word(
        admitted,
        profile.word_trits(),
        data_address,
    )?;
    if wide_data.rem_euclid(geometry.memory_words()) != narrow_data {
        return Err(ProfileWidthVerificationError::JumpRotateProjection);
    }
    let narrow_rotate = profile_rotate(narrow_data, geometry.word_modulus());
    let wide_rotate = profile_rotate(wide_data, profile.memory_words());
    if wide_rotate.rem_euclid(geometry.memory_words()) != narrow_rotate {
        return Err(ProfileWidthVerificationError::JumpRotateProjection);
    }
    Ok(())
}

/// Verifies exact jump, zero or more no-ops, one rotate, then halt.
///
/// The initial jump establishes exact D from the first raw source cell. Each
/// reached no-op advances D without reading or writing data memory. The rotate
/// target must remain outside the loaded source, so its candidate/canonical
/// initial words are independently reconstructed. The verifier then requires
/// both the initial-word projection and the width-specific rotate projection
/// before authorizing the data write.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when source shape, exact address,
/// initial-memory projection, or rotate projection does not hold.
pub fn verify_jump_rotate_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let geometry = ProfileExecutionGeometry {
        input_policy: ProfileExecutionInputPolicy::Any,
        memory_words,
        profile,
        word_trits,
    };
    let admitted = admit_profile_source(source, memory_words)?;
    let mut data_address =
        jump_rotate_initial_address(&admitted, memory_words)?;
    let mut rotated = false;
    for (position, cell) in admitted.iter().copied().enumerate().skip(1) {
        let pointer = u32::try_from(position).map_err(|_error| {
            ProfileWidthVerificationError::GeometryInvariant
        })?;
        let decoded = decode_profile_instruction(cell, pointer)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        if !rotated && decoded == b'o' {
            data_address =
                advance_jump_rotate_address(data_address, memory_words)?;
            continue;
        }
        if !rotated && decoded == b'*' {
            verify_jump_rotate_projection(&admitted, geometry, data_address)?;
            data_address =
                advance_jump_rotate_address(data_address, memory_words)?;
            rotated = true;
            continue;
        }
        if rotated && decoded == b'v' {
            return Ok(VerifiedProfileExecutionGeometry {
                geometry,
                proof_kind: ProfileWidthProofKind::JumpRotateHaltProjection,
                source: Box::from(source),
            });
        }
        return Err(ProfileWidthVerificationError::JumpRotateHaltInstruction {
            position: pointer,
            decoded,
        });
    }
    Err(ProfileWidthVerificationError::JumpRotateProjection)
}

fn jump_rotate_io_decoded_at(
    admitted: &[u32],
    position: usize,
) -> Result<DecodedSourceInstruction, ProfileWidthVerificationError> {
    let pointer = u32::try_from(position)
        .map_err(|_error| ProfileWidthVerificationError::GeometryInvariant)?;
    let cell = admitted
        .get(position)
        .copied()
        .ok_or(ProfileWidthVerificationError::JumpRotateProjection)?;
    let decoded = decode_profile_instruction(cell, pointer)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    Ok(DecodedSourceInstruction { decoded, pointer })
}

fn verify_jump_rotate_io_suffix(
    admitted: &[u32],
    geometry: ProfileExecutionGeometry,
    mut data_address: u32,
    mut position: usize,
) -> Result<usize, ProfileWidthVerificationError> {
    let profile = geometry.profile();
    let mut required_input = 0usize;
    loop {
        let input_instruction = jump_rotate_io_decoded_at(admitted, position)?;
        if input_instruction.decoded == b'v' {
            if required_input == 0 {
                return Err(
                    ProfileWidthVerificationError::JumpRotateHaltInstruction {
                        position: input_instruction.pointer,
                        decoded: input_instruction.decoded,
                    },
                );
            }
            return Ok(required_input);
        }
        if input_instruction.decoded != profile.input_instruction() {
            return Err(
                ProfileWidthVerificationError::JumpRotateHaltInstruction {
                    position: input_instruction.pointer,
                    decoded: input_instruction.decoded,
                },
            );
        }
        required_input = required_input
            .checked_add(1)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        data_address =
            advance_jump_rotate_address(data_address, geometry.memory_words())?;
        position = position
            .checked_add(1)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        let output_instruction = jump_rotate_io_decoded_at(admitted, position)?;
        if output_instruction.decoded != profile.output_instruction() {
            return Err(
                ProfileWidthVerificationError::JumpRotateHaltInstruction {
                    position: output_instruction.pointer,
                    decoded: output_instruction.decoded,
                },
            );
        }
        data_address =
            advance_jump_rotate_address(data_address, geometry.memory_words())?;
        position = position
            .checked_add(1)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    }
}

/// Verifies exact jump/no-ops, projected rotate, byte I/O pairs, and halt.
///
/// The prefix uses the same exact-D and independent candidate/canonical rotate
/// projection proof as [`verify_jump_rotate_halt_profile_width`]. The rotated
/// accumulator may differ numerically across widths. Each required non-EOF
/// input overwrites A with the same byte before its output, while sequential
/// source encryption and nonwrapping D advancement remain width-independent.
/// The hidden policy records the exact number of reached input instructions.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when source shape, rotate
/// projection, recovery suffix, or nonwrapping D advancement does not hold.
pub fn verify_jump_rotate_io_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let geometry = ProfileExecutionGeometry {
        input_policy: ProfileExecutionInputPolicy::MinimumLength(1),
        memory_words,
        profile,
        word_trits,
    };
    let admitted = admit_profile_source(source, memory_words)?;
    let mut data_address =
        jump_rotate_initial_address(&admitted, memory_words)?;
    let mut position = 1usize;
    while let Some(cell) = admitted.get(position).copied() {
        let pointer = u32::try_from(position).map_err(|_error| {
            ProfileWidthVerificationError::GeometryInvariant
        })?;
        let decoded = decode_profile_instruction(cell, pointer)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        if decoded == b'o' {
            data_address =
                advance_jump_rotate_address(data_address, memory_words)?;
            position = position.saturating_add(1);
            continue;
        }
        if decoded != b'*' {
            return Err(
                ProfileWidthVerificationError::JumpRotateHaltInstruction {
                    position: pointer,
                    decoded,
                },
            );
        }
        verify_jump_rotate_projection(&admitted, geometry, data_address)?;
        data_address = advance_jump_rotate_address(data_address, memory_words)?;
        position = position.saturating_add(1);
        let required_input = verify_jump_rotate_io_suffix(
            &admitted,
            geometry,
            data_address,
            position,
        )?;
        return Ok(VerifiedProfileExecutionGeometry {
            geometry: ProfileExecutionGeometry {
                input_policy: ProfileExecutionInputPolicy::MinimumLength(
                    required_input,
                ),
                ..geometry
            },
            proof_kind: ProfileWidthProofKind::JumpRotateIoHaltProjection,
            source: Box::from(source),
        });
    }
    Err(ProfileWidthVerificationError::JumpRotateProjection)
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
                    input_policy: ProfileExecutionInputPolicy::Any,
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
            input_policy: ProfileExecutionInputPolicy::Any,
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
