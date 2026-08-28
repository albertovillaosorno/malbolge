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
use crate::word::profile_crazy;

const MINIMUM_ADAPTIVE_WORD_TRITS: u8 = 10;
const TERNARY_RADIX: u32 = 3;

type ProfileWidthVerifier = fn(
    &'static ProfileDescriptor,
    &[u8],
    u8,
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
    /// One exact jump enables one guarded crazy transition before halt.
    JumpCrazyHaltProjection,
    /// One exact-address data jump is followed immediately by halt.
    JumpDataHaltProjection,
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
            Self::InputOutputHaltInstruction { position, decoded } => {
                Self::fmt_instruction(
                    f,
                    "input-output-halt",
                    *decoded,
                    *position,
                )
            },
            Self::InputThenHaltInstruction { position, decoded } => {
                Self::fmt_instruction(f, "input-halt", *decoded, *position)
            },
            Self::JumpCrazyHaltInstruction { position, decoded } => {
                Self::fmt_instruction(f, "jump-crazy", *decoded, *position)
            },
            Self::JumpCrazyProjection => {
                f.write_str("derived jump-crazy projection premise failed")
            },
            Self::JumpDataHaltInstruction { position, decoded } => {
                Self::fmt_instruction(f, "jump-data-halt", *decoded, *position)
            },
            Self::NoopPrefixInstruction { position, decoded } => {
                Self::fmt_instruction(f, "no-op prefix", *decoded, *position)
            },
            Self::NoopPrefixMissingHalt => {
                f.write_str("derived no-op prefix does not reach halt")
            },
            Self::RepeatedJumpInstruction { position, decoded } => {
                Self::fmt_instruction(f, "repeated-jump", *decoded, *position)
            },
            Self::RepeatedJumpMemoryMismatch { address } => {
                write!(f, "derived repeated-jump memory differs at {address}")
            },
            Self::RepeatedJumpMissingHalt => {
                f.write_str("derived repeated jumps do not reach halt")
            },
            Self::Source(error) => Display::fmt(error, f),
            Self::StraightLineInstruction { position, decoded } => {
                Self::fmt_instruction(f, "straight-line", *decoded, *position)
            },
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

/// Independently verifies exact jump, guarded crazy, then halt.
///
/// The jump establishes exact D. Crazy must target data outside current/future
/// source code, and candidate/canonical crazy results are checked by
/// projection.
///
/// # Errors
///
/// Returns [`ProfileWidthVerificationError`] when shape, exact memory, guarded
/// write placement, or crazy projection does not hold.
pub fn verify_jump_crazy_halt_profile_width(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    word_trits: u8,
) -> Result<VerifiedProfileExecutionGeometry, ProfileWidthVerificationError> {
    let memory_words = derived_memory_words(profile, word_trits)?;
    let narrow = admit_profile_source(source, memory_words)?;
    for (position, expected) in b"jpv".iter().copied().enumerate() {
        let pointer = u32::try_from(position).map_err(|_error| {
            ProfileWidthVerificationError::GeometryInvariant
        })?;
        let cell = narrow
            .get(position)
            .copied()
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        let decoded = decode_profile_instruction(cell, pointer)
            .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
        if decoded != expected {
            return Err(
                ProfileWidthVerificationError::JumpCrazyHaltInstruction {
                    position: pointer,
                    decoded,
                },
            );
        }
    }
    let first = narrow
        .first()
        .copied()
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    let data_address = first
        .checked_add(1)
        .filter(|address| *address < memory_words)
        .ok_or(ProfileWidthVerificationError::GeometryInvariant)?;
    if data_address == 1
        || usize::try_from(data_address)
            .is_ok_and(|address| address > 1 && address < narrow.len())
    {
        return Err(ProfileWidthVerificationError::JumpCrazyProjection);
    }
    let narrow_data =
        verified_initial_memory_word(&narrow, word_trits, data_address)?;
    let wide_data = verified_initial_memory_word(
        &narrow,
        profile.word_trits(),
        data_address,
    )?;
    if wide_data.rem_euclid(memory_words) != narrow_data {
        return Err(ProfileWidthVerificationError::JumpCrazyProjection);
    }
    let narrow_crazy = profile_crazy(narrow_data, 0, word_trits);
    let wide_crazy = profile_crazy(wide_data, 0, profile.word_trits());
    if wide_crazy.rem_euclid(memory_words) != narrow_crazy {
        return Err(ProfileWidthVerificationError::JumpCrazyProjection);
    }
    Ok(VerifiedProfileExecutionGeometry {
        geometry: ProfileExecutionGeometry {
            input_policy: ProfileExecutionInputPolicy::Any,
            memory_words,
            profile,
            word_trits,
        },
        proof_kind: ProfileWidthProofKind::JumpCrazyHaltProjection,
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
