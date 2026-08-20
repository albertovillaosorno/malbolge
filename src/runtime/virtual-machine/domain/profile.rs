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
//   - Runtime target-profile descriptors and fail-closed capability preflight.
// - Must-Not:
//   - Reinterpret profile JSON, guess missing capabilities, or execute
//   - fallback.
// - Allows:
//   - Inputs: generated canonical profile descriptors and runtime capacities.
//   - Outputs: exact profile identity and deterministic requirement
//   - diagnostics.
//   - Side effects: none.
// - Split-When:
//   - Split when another runtime family needs an independent capability model.
// - Merge-When:
//   - Merge when target identity and runtime capability become one authority.
// - Summary:
//   - Canonical profile projection and deterministic execution preflight.
// - Description:
//   - Compares immutable target requirements with explicit runtime capacity.
// - Usage:
//   - Call before constructing a machine for an explicitly selected profile.
// - Defaults:
//   - The safe Rust VM capability remains the classic ten-trit implementation.
//

//! Target-profile identity and deterministic runtime-capability preflight.

#[path = "profile_generated.rs"]
mod generated;

use std::fmt::{Display, Formatter, Result as FormatResult};

const BYTE_INPUT: ProfileFeature = ProfileFeature::ByteInput;
const BYTE_OUTPUT: ProfileFeature = ProfileFeature::ByteOutput;
const CRAZY_OPERATION: ProfileFeature = ProfileFeature::CrazyOperation;
const DETERMINISTIC: ProfileFeature = ProfileFeature::Deterministic;
const POST_INSTRUCTION_ENCRYPTION: ProfileFeature =
    ProfileFeature::PostInstructionEncryption;
const ROTATE: ProfileFeature = ProfileFeature::Rotate;
const SELF_MODIFICATION: ProfileFeature = ProfileFeature::SelfModification;
const SEQUENTIAL_GUEST: ProfileFeature = ProfileFeature::SequentialGuest;
const REQUIRED_FEATURES: [ProfileFeature; 8] = [
    BYTE_INPUT,
    BYTE_OUTPUT,
    CRAZY_OPERATION,
    DETERMINISTIC,
    POST_INSTRUCTION_ENCRYPTION,
    ROTATE,
    SELF_MODIFICATION,
    SEQUENTIAL_GUEST,
];

const SAFE_RUST_CLASSIC: RuntimeCapability = RuntimeCapability {
    features: ProfileFeatureSet::NORMATIVE,
    id: "safe-rust-classic",
    max_memory_words: 59_049,
    max_word_trits: 10,
};
const SAFE_RUST_PROFILED: RuntimeCapability = RuntimeCapability {
    features: ProfileFeatureSet::NORMATIVE,
    id: "safe-rust-profiled",
    max_memory_words: 4_782_969,
    max_word_trits: 14,
};

/// One immutable target-profile classification from `malbolge.json`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileKind {
    /// The profile selected as the repository's current language identity.
    Current,
    /// Frozen original-interpreter conformance with host UB excluded.
    HistoricalConformance,
    /// Published immutable language identity that is no longer current.
    Versioned,
}

impl ProfileKind {
    /// Returns the stable profile-kind spelling used by the canonical JSON.
    #[must_use]
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::Current => "current",
            Self::HistoricalConformance => "historical-conformance",
            Self::Versioned => "versioned",
        }
    }
}

/// One defining semantic capability required by schema-v2 target profiles.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileFeature {
    /// Input reads one byte, with profile maximum as EOF.
    ByteInput,
    /// Output emits the accumulator modulo 256.
    ByteOutput,
    /// Digitwise normative Malbolge crazy operation.
    CrazyOperation,
    /// Repeated execution of one state/input pair is deterministic.
    Deterministic,
    /// The executed instruction cell is encrypted after committed execution.
    PostInstructionEncryption,
    /// One-trit circular right rotation over the profile word width.
    Rotate,
    /// Guest code remains writable and self-modifying.
    SelfModification,
    /// Guest instruction order is sequential.
    SequentialGuest,
}

impl ProfileFeature {
    const fn bit(self) -> u16 {
        match self {
            Self::ByteInput => 1 << 0,
            Self::ByteOutput => 1 << 1,
            Self::CrazyOperation => 1 << 2,
            Self::Deterministic => 1 << 3,
            Self::PostInstructionEncryption => 1 << 4,
            Self::Rotate => 1 << 5,
            Self::SelfModification => 1 << 6,
            Self::SequentialGuest => 1 << 7,
        }
    }

    /// Parses one exact stable capability spelling.
    #[must_use]
    pub fn from_stable_id(value: &str) -> Option<Self> {
        match value {
            "byte-input" => Some(Self::ByteInput),
            "byte-output" => Some(Self::ByteOutput),
            "crazy-operation" => Some(Self::CrazyOperation),
            "deterministic" => Some(Self::Deterministic),
            "post-instruction-encryption" => {
                Some(Self::PostInstructionEncryption)
            },
            "rotate" => Some(Self::Rotate),
            "self-modification" => Some(Self::SelfModification),
            "sequential-guest" => Some(Self::SequentialGuest),
            _ => None,
        }
    }

    /// Returns the stable diagnostic spelling for this capability.
    #[must_use]
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::ByteInput => "byte-input",
            Self::ByteOutput => "byte-output",
            Self::CrazyOperation => "crazy-operation",
            Self::Deterministic => "deterministic",
            Self::PostInstructionEncryption => "post-instruction-encryption",
            Self::Rotate => "rotate",
            Self::SelfModification => "self-modification",
            Self::SequentialGuest => "sequential-guest",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ProfileFeatureSet(u16);

impl ProfileFeatureSet {
    const NORMATIVE: Self = Self(
        BYTE_INPUT.bit()
            | BYTE_OUTPUT.bit()
            | CRAZY_OPERATION.bit()
            | DETERMINISTIC.bit()
            | POST_INSTRUCTION_ENCRYPTION.bit()
            | ROTATE.bit()
            | SELF_MODIFICATION.bit()
            | SEQUENTIAL_GUEST.bit(),
    );

    const fn contains(self, feature: ProfileFeature) -> bool {
        self.0 & feature.bit() != 0
    }

    const fn is_empty(self) -> bool {
        self.0 == 0
    }

    const fn missing_from(self, available: Self) -> Self {
        Self(self.0 & !available.0)
    }
}

/// One immutable canonical target-profile descriptor.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProfileDescriptor {
    eof_word: u32,
    fingerprint: &'static str,
    id: &'static str,
    input_instruction: u8,
    kind: ProfileKind,
    memory_words: u32,
    output_instruction: u8,
    version: &'static str,
    word_modulus: u32,
    word_trits: u8,
}

impl ProfileDescriptor {
    /// Returns the all-two-trit EOF sentinel for this profile.
    #[must_use]
    pub const fn eof_word(self) -> u32 {
        self.eof_word
    }

    /// Returns the canonical immutable profile fingerprint.
    #[must_use]
    pub const fn fingerprint(self) -> &'static str {
        self.fingerprint
    }

    /// Returns the stable canonical profile identity.
    #[must_use]
    pub const fn id(self) -> &'static str {
        self.id
    }

    /// Returns the decoded instruction byte assigned to byte input.
    #[must_use]
    pub const fn input_instruction(self) -> u8 {
        self.input_instruction
    }

    /// Returns the immutable profile classification.
    #[must_use]
    pub const fn kind(self) -> ProfileKind {
        self.kind
    }

    /// Returns the exact directly addressed word capacity.
    #[must_use]
    pub const fn memory_words(self) -> u32 {
        self.memory_words
    }

    /// Returns the decoded instruction byte assigned to byte output.
    #[must_use]
    pub const fn output_instruction(self) -> u8 {
        self.output_instruction
    }

    /// Returns all defining schema-v2 semantic capabilities in stable order.
    #[must_use]
    pub const fn required_features() -> &'static [ProfileFeature; 8] {
        &REQUIRED_FEATURES
    }

    /// Returns the profile's published language version.
    #[must_use]
    pub const fn version(self) -> &'static str {
        self.version
    }

    /// Returns `3^N`, the exact profile word modulus.
    #[must_use]
    pub const fn word_modulus(self) -> u32 {
        self.word_modulus
    }

    /// Returns the number of ternary digits in one profile word.
    #[must_use]
    pub const fn word_trits(self) -> u8 {
        self.word_trits
    }
}

/// Portable immutable target-profile requirement envelope.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TargetProfileRequirement {
    /// Defining semantic capabilities in stable diagnostic order.
    pub features: Vec<String>,
    /// Exact directly addressed profile capacity.
    pub memory_words: u32,
    /// Published immutable language version.
    pub version: String,
    /// Number of ternary digits in one profile word.
    pub word_trits: u8,
}

impl TargetProfileRequirement {
    /// Projects one validated canonical profile descriptor into owned data.
    #[must_use]
    pub fn from_descriptor(profile: &ProfileDescriptor) -> Self {
        Self {
            features: ProfileDescriptor::required_features()
                .iter()
                .map(|feature| String::from(feature.stable_id()))
                .collect(),
            memory_words: profile.memory_words(),
            version: String::from(profile.version()),
            word_trits: profile.word_trits(),
        }
    }

    /// Reports whether this envelope exactly matches one canonical profile.
    #[must_use]
    pub fn is_canonical_for(&self, profile_id: &str) -> bool {
        let Some(profile) = target_profile(profile_id) else {
            return false;
        };
        self.memory_words == profile.memory_words()
            && self.version == profile.version()
            && self.word_trits == profile.word_trits()
            && self.features.len() == REQUIRED_FEATURES.len()
            && self
                .features
                .iter()
                .zip(REQUIRED_FEATURES)
                .all(|(observed, required)| observed == required.stable_id())
    }
}

/// One explicit execution-runtime capability envelope.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RuntimeCapability {
    features: ProfileFeatureSet,
    id: &'static str,
    max_memory_words: u32,
    max_word_trits: u8,
}

impl RuntimeCapability {
    /// Returns the stable runtime capability identity.
    #[must_use]
    pub const fn id(self) -> &'static str {
        self.id
    }

    /// Returns the largest directly addressed memory this runtime implements.
    #[must_use]
    pub const fn max_memory_words(self) -> u32 {
        self.max_memory_words
    }

    /// Returns the largest word width this runtime implements.
    #[must_use]
    pub const fn max_word_trits(self) -> u8 {
        self.max_word_trits
    }
}

/// Stable category for target-profile preflight rejection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileRequirementErrorKind {
    /// Program requirements exceed the explicitly selected profile itself.
    ProfileCapacityExceeded,
    /// The selected runtime cannot implement the selected profile.
    RuntimeCapabilityMissing,
}

/// Deterministic target-profile or runtime-capability rejection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProfileRequirementError {
    kind: ProfileRequirementErrorKind,
    profile: &'static ProfileDescriptor,
    required_memory_words: u64,
    runtime: &'static RuntimeCapability,
}

/// Portable program/profile or runtime-capability preflight rejection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PortableProfileRequirementError<'requirement> {
    kind: ProfileRequirementErrorKind,
    profile_id: &'requirement str,
    required_memory_words: u64,
    requirement: &'requirement TargetProfileRequirement,
    runtime: &'static RuntimeCapability,
}

impl<'requirement> PortableProfileRequirementError<'requirement> {
    /// Returns the stable machine-readable diagnostic code.
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self.kind {
            ProfileRequirementErrorKind::ProfileCapacityExceeded => {
                "MALBOLGE-PROFILE-002"
            },
            ProfileRequirementErrorKind::RuntimeCapabilityMissing => {
                "MALBOLGE-PROFILE-001"
            },
        }
    }

    /// Returns the stable rejection category.
    #[must_use]
    pub const fn kind(self) -> ProfileRequirementErrorKind {
        self.kind
    }

    /// Returns the declared profile identity checked by this preflight.
    #[must_use]
    pub const fn profile_id(self) -> &'requirement str {
        self.profile_id
    }

    /// Returns the exact minimum directly addressed words requested.
    #[must_use]
    pub const fn required_memory_words(self) -> u64 {
        self.required_memory_words
    }

    /// Returns the admitted portable target-profile requirement envelope.
    #[must_use]
    pub const fn requirement(self) -> &'requirement TargetProfileRequirement {
        self.requirement
    }

    /// Returns the runtime capability checked after profile capacity.
    #[must_use]
    pub const fn runtime(self) -> &'static RuntimeCapability {
        self.runtime
    }
}

/// Runtime-capability rejection for an admitted portable requirement envelope.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct RuntimeProfileRequirementError<'requirement> {
    profile_id: &'requirement str,
    requirement: &'requirement TargetProfileRequirement,
    runtime: &'static RuntimeCapability,
}

impl<'requirement> RuntimeProfileRequirementError<'requirement> {
    /// Stable machine-readable diagnostic code.
    pub const CODE: &'static str = "MALBOLGE-PROFILE-001";

    /// Returns the declared profile identity that failed preflight.
    #[must_use]
    pub const fn profile_id(self) -> &'requirement str {
        self.profile_id
    }

    /// Returns the portable requirement envelope checked by this preflight.
    #[must_use]
    pub const fn requirement(self) -> &'requirement TargetProfileRequirement {
        self.requirement
    }

    /// Returns the runtime capability checked by this preflight.
    #[must_use]
    pub const fn runtime(self) -> &'static RuntimeCapability {
        self.runtime
    }
}

impl ProfileRequirementError {
    /// Returns the stable machine-readable diagnostic code.
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self.kind {
            ProfileRequirementErrorKind::ProfileCapacityExceeded => {
                "MALBOLGE-PROFILE-002"
            },
            ProfileRequirementErrorKind::RuntimeCapabilityMissing => {
                "MALBOLGE-PROFILE-001"
            },
        }
    }

    /// Returns the stable failure category.
    #[must_use]
    pub const fn kind(self) -> ProfileRequirementErrorKind {
        self.kind
    }

    /// Returns the profile whose requirements could not be satisfied.
    #[must_use]
    pub const fn profile(self) -> &'static ProfileDescriptor {
        self.profile
    }

    /// Returns the minimum guest memory requested by the program/profile.
    #[must_use]
    pub const fn required_memory_words(self) -> u64 {
        self.required_memory_words
    }

    /// Returns the runtime capability checked by this preflight.
    #[must_use]
    pub const fn runtime(self) -> &'static RuntimeCapability {
        self.runtime
    }
}

impl Display for PortableProfileRequirementError<'_> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self.kind {
            ProfileRequirementErrorKind::ProfileCapacityExceeded => {
                write_portable_capacity_error(f, *self)
            },
            ProfileRequirementErrorKind::RuntimeCapabilityMissing => {
                write_runtime_requirement(f, RuntimeRequirementView {
                    features: RequirementFeatures::Portable(
                        &self.requirement.features,
                    ),
                    memory_words: self.requirement.memory_words,
                    profile_id: self.profile_id,
                    runtime: *self.runtime,
                    version: &self.requirement.version,
                    word_trits: self.requirement.word_trits,
                })
            },
        }
    }
}

impl Display for RuntimeProfileRequirementError<'_> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write_runtime_requirement(f, RuntimeRequirementView {
            features: RequirementFeatures::Portable(&self.requirement.features),
            memory_words: self.requirement.memory_words,
            profile_id: self.profile_id,
            runtime: *self.runtime,
            version: &self.requirement.version,
            word_trits: self.requirement.word_trits,
        })
    }
}

impl Display for ProfileRequirementError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self.kind {
            ProfileRequirementErrorKind::ProfileCapacityExceeded => {
                write_capacity_error(f, *self)
            },
            ProfileRequirementErrorKind::RuntimeCapabilityMissing => {
                write_runtime_error(f, *self)
            },
        }
    }
}

#[derive(Clone, Copy)]
struct CapacityRequirementView<'requirement> {
    constraint: &'static str,
    profile_id: &'requirement str,
    profile_memory_words: u32,
    required_memory_words: u64,
    version: &'requirement str,
}

#[derive(Clone, Copy)]
enum RequirementFeatures<'requirement> {
    Canonical,
    Portable(&'requirement [String]),
}

#[derive(Clone, Copy)]
struct RuntimeRequirementView<'requirement> {
    features: RequirementFeatures<'requirement>,
    memory_words: u32,
    profile_id: &'requirement str,
    runtime: RuntimeCapability,
    version: &'requirement str,
    word_trits: u8,
}

/// Returns the canonical current target profile.
#[must_use]
pub const fn current_profile() -> &'static ProfileDescriptor {
    generated::CURRENT_PROFILE
}

/// Returns the frozen historical-conformance target profile.
#[must_use]
pub const fn historical_profile() -> &'static ProfileDescriptor {
    generated::HISTORICAL_PROFILE
}

/// Checks one portable program/profile requirement against a runtime.
///
/// Profile capacity is checked before runtime capability. This accepts a `u64`
/// memory requirement so the full `u32` address domain remains exact.
///
/// # Errors
///
/// Returns `MALBOLGE-PROFILE-002` when the program addresses beyond the
/// selected profile, otherwise returns the shared `MALBOLGE-PROFILE-001`
/// runtime error.
pub fn preflight_portable_profile_requirement<'requirement>(
    profile_id: &'requirement str,
    requirement: &'requirement TargetProfileRequirement,
    required_memory_words: u64,
    runtime: &'static RuntimeCapability,
) -> Result<(), PortableProfileRequirementError<'requirement>> {
    if required_memory_words > u64::from(requirement.memory_words) {
        return Err(PortableProfileRequirementError {
            kind: ProfileRequirementErrorKind::ProfileCapacityExceeded,
            profile_id,
            required_memory_words,
            requirement,
            runtime,
        });
    }
    let view = RuntimeRequirementView {
        features: RequirementFeatures::Portable(&requirement.features),
        memory_words: requirement.memory_words,
        profile_id,
        runtime: *runtime,
        version: &requirement.version,
        word_trits: requirement.word_trits,
    };
    if runtime_requirement_missing(view) {
        return Err(PortableProfileRequirementError {
            kind: ProfileRequirementErrorKind::RuntimeCapabilityMissing,
            profile_id,
            required_memory_words,
            requirement,
            runtime,
        });
    }
    Ok(())
}

/// Checks one admitted portable profile envelope against a runtime capability.
///
/// # Errors
///
/// Returns the shared `MALBOLGE-PROFILE-001` diagnostic when the runtime cannot
/// implement the declared word width, memory capacity, or semantic features.
pub fn preflight_runtime_requirement<'requirement>(
    profile_id: &'requirement str,
    requirement: &'requirement TargetProfileRequirement,
    runtime: &'static RuntimeCapability,
) -> Result<(), RuntimeProfileRequirementError<'requirement>> {
    let view = RuntimeRequirementView {
        features: RequirementFeatures::Portable(&requirement.features),
        memory_words: requirement.memory_words,
        profile_id,
        runtime: *runtime,
        version: &requirement.version,
        word_trits: requirement.word_trits,
    };
    if runtime_requirement_missing(view) {
        return Err(RuntimeProfileRequirementError {
            profile_id,
            requirement,
            runtime,
        });
    }
    Ok(())
}

/// Checks one program/profile requirement against one runtime capability.
///
/// # Errors
///
/// Returns a deterministic profile-capacity diagnostic when the program asks
/// for more memory than the selected profile defines, or a runtime-capability
/// diagnostic when the runtime cannot implement the profile exactly.
pub fn preflight_profile(
    profile: &'static ProfileDescriptor,
    required_memory_words: u64,
    runtime: &'static RuntimeCapability,
) -> Result<(), ProfileRequirementError> {
    if required_memory_words > u64::from(profile.memory_words) {
        return Err(ProfileRequirementError {
            kind: ProfileRequirementErrorKind::ProfileCapacityExceeded,
            profile,
            required_memory_words,
            runtime,
        });
    }
    let missing_features =
        ProfileFeatureSet::NORMATIVE.missing_from(runtime.features);
    if runtime_geometry_missing(
        profile.word_trits,
        profile.memory_words,
        *runtime,
    ) || !missing_features.is_empty()
    {
        return Err(ProfileRequirementError {
            kind: ProfileRequirementErrorKind::RuntimeCapabilityMissing,
            profile,
            required_memory_words: u64::from(profile.memory_words),
            runtime,
        });
    }
    Ok(())
}

/// Returns the safe Rust VM's current explicit capability envelope.
#[must_use]
pub const fn safe_rust_classic_capability() -> &'static RuntimeCapability {
    &SAFE_RUST_CLASSIC
}

/// Returns the safe Rust profile-driven VM capability envelope.
#[must_use]
pub const fn safe_rust_profiled_capability() -> &'static RuntimeCapability {
    &SAFE_RUST_PROFILED
}

/// Looks up one exact canonical profile identity without fallback.
#[must_use]
pub fn target_profile(id: &str) -> Option<&'static ProfileDescriptor> {
    generated::PROFILE_DESCRIPTORS
        .iter()
        .copied()
        .find(|profile| profile.id == id)
}

const fn runtime_geometry_missing(
    word_trits: u8,
    memory_words: u32,
    runtime: RuntimeCapability,
) -> bool {
    word_trits > runtime.max_word_trits
        || memory_words > runtime.max_memory_words
}

fn runtime_requirement_missing(view: RuntimeRequirementView<'_>) -> bool {
    if runtime_geometry_missing(
        view.word_trits,
        view.memory_words,
        view.runtime,
    ) {
        return true;
    }
    match view.features {
        RequirementFeatures::Canonical => !ProfileFeatureSet::NORMATIVE
            .missing_from(view.runtime.features)
            .is_empty(),
        RequirementFeatures::Portable(features) => {
            features.iter().any(|feature| {
                ProfileFeature::from_stable_id(feature)
                    .is_none_or(|known| !view.runtime.features.contains(known))
            })
        },
    }
}

fn write_capacity_error(
    formatter: &mut Formatter<'_>,
    error: ProfileRequirementError,
) -> FormatResult {
    let profile = error.profile;
    let constraint = if profile.kind == ProfileKind::HistoricalConformance {
        "historical-profile-ceiling"
    } else {
        "profile-capacity-ceiling"
    };
    write_capacity_requirement(formatter, CapacityRequirementView {
        constraint,
        profile_id: profile.id,
        profile_memory_words: profile.memory_words,
        required_memory_words: error.required_memory_words,
        version: profile.version,
    })
}

fn write_capacity_requirement(
    formatter: &mut Formatter<'_>,
    view: CapacityRequirementView<'_>,
) -> FormatResult {
    formatter.write_str("MALBOLGE-PROFILE-002 profile=")?;
    formatter.write_str(view.profile_id)?;
    formatter.write_str(" version=")?;
    formatter.write_str(view.version)?;
    formatter.write_str(" constraint=")?;
    formatter.write_str(view.constraint)?;
    let required_memory_words = view.required_memory_words;
    let profile_memory_words = view.profile_memory_words;
    write!(formatter, " required_memory_words={required_memory_words} ")?;
    write!(formatter, "profile_memory_words={profile_memory_words}")
}

fn write_portable_capacity_error(
    formatter: &mut Formatter<'_>,
    error: PortableProfileRequirementError<'_>,
) -> FormatResult {
    let constraint = if error.profile_id == generated::HISTORICAL_PROFILE.id {
        "historical-profile-ceiling"
    } else {
        "profile-capacity-ceiling"
    };
    write_capacity_requirement(formatter, CapacityRequirementView {
        constraint,
        profile_id: error.profile_id,
        profile_memory_words: error.requirement.memory_words,
        required_memory_words: error.required_memory_words,
        version: &error.requirement.version,
    })
}

fn write_feature_list(
    formatter: &mut Formatter<'_>,
    features: RequirementFeatures<'_>,
) -> FormatResult {
    match features {
        RequirementFeatures::Canonical => {
            for (index, feature) in
                REQUIRED_FEATURES.iter().copied().enumerate()
            {
                if index != 0 {
                    formatter.write_str(",")?;
                }
                formatter.write_str(feature.stable_id())?;
            }
        },
        RequirementFeatures::Portable(values) => {
            for (index, feature) in values.iter().enumerate() {
                if index != 0 {
                    formatter.write_str(",")?;
                }
                formatter.write_str(feature)?;
            }
        },
    }
    Ok(())
}

fn write_list_item(
    formatter: &mut Formatter<'_>,
    value: &str,
    needs_separator: &mut bool,
) -> FormatResult {
    if *needs_separator {
        formatter.write_str(",")?;
    }
    formatter.write_str(value)?;
    *needs_separator = true;
    Ok(())
}

fn write_missing_feature_ids(
    formatter: &mut Formatter<'_>,
    view: RuntimeRequirementView<'_>,
    prefix_present: bool,
) -> FormatResult {
    let mut needs_separator = prefix_present;
    match view.features {
        RequirementFeatures::Canonical => {
            for feature in REQUIRED_FEATURES {
                if !view.runtime.features.contains(feature) {
                    write_list_item(
                        formatter,
                        feature.stable_id(),
                        &mut needs_separator,
                    )?;
                }
            }
        },
        RequirementFeatures::Portable(values) => {
            for feature in values {
                let supported = ProfileFeature::from_stable_id(feature)
                    .is_some_and(|known| view.runtime.features.contains(known));
                if !supported {
                    write_list_item(formatter, feature, &mut needs_separator)?;
                }
            }
        },
    }
    Ok(())
}

fn write_missing_runtime_dimensions(
    formatter: &mut Formatter<'_>,
    view: RuntimeRequirementView<'_>,
) -> FormatResult {
    let word_missing = view.word_trits > view.runtime.max_word_trits;
    let memory_missing = view.memory_words > view.runtime.max_memory_words;
    let prefix_present = match (word_missing, memory_missing) {
        (false, false) => false,
        (false, true) => {
            formatter.write_str("memory-words")?;
            true
        },
        (true, false) => {
            formatter.write_str("word-trits")?;
            true
        },
        (true, true) => {
            formatter.write_str("word-trits,memory-words")?;
            true
        },
    };
    write_missing_feature_ids(formatter, view, prefix_present)
}

fn write_runtime_requirement(
    formatter: &mut Formatter<'_>,
    view: RuntimeRequirementView<'_>,
) -> FormatResult {
    formatter.write_str("MALBOLGE-PROFILE-001 profile=")?;
    formatter.write_str(view.profile_id)?;
    formatter.write_str(" version=")?;
    formatter.write_str(view.version)?;
    formatter.write_str(" required_features=")?;
    write_feature_list(formatter, view.features)?;
    let runtime_id = view.runtime.id;
    let max_word_trits = view.runtime.max_word_trits;
    let max_memory_words = view.runtime.max_memory_words;
    let required_word_trits = view.word_trits;
    let required_memory_words = view.memory_words;
    write!(formatter, " required_word_trits={required_word_trits} ")?;
    write!(formatter, "required_memory_words={required_memory_words} ")?;
    write!(
        formatter,
        "runtime={runtime_id} max_word_trits={max_word_trits} "
    )?;
    write!(formatter, "max_memory_words={max_memory_words} missing=")?;
    write_missing_runtime_dimensions(formatter, view)
}

fn write_runtime_error(
    formatter: &mut Formatter<'_>,
    error: ProfileRequirementError,
) -> FormatResult {
    let profile = error.profile;
    write_runtime_requirement(formatter, RuntimeRequirementView {
        features: RequirementFeatures::Canonical,
        memory_words: profile.memory_words,
        profile_id: profile.id,
        runtime: *error.runtime,
        version: profile.version,
        word_trits: profile.word_trits,
    })
}
