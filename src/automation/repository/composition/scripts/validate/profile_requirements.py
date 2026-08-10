# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Deterministic target-profile requirement preflight for Python consumers.
# - Must-Not:
#   - Define profile semantics, infer host capacity, select fallback profiles,
#     load artifacts, execute guest code, mutate canonical data, or change
#     policy.
# - Allows:
#   - Inputs: validated canonical profile data, exact program memory demand, and
#     one explicit runtime capability envelope.
#   - Outputs: immutable requirements or stable typed profile diagnostics.
#   - Side effects: none.
# - Split-When:
#   - Split when another runtime family needs independent capability discovery.
# - Merge-When:
#   - Merge when every Python consumer uses another exact requirement boundary.
# - Summary:
#   - Python target-profile requirement and runtime-capability preflight.
# - Description:
#   - Mirrors the Rust diagnostic contract while deriving semantics from JSON.
# - Usage:
#   - Build one requirement and one explicit capability, then preflight them.
# - Defaults:
#   - Safe Rust classic/profiled envelopes are explicit convenience constants.
#

"""Deterministic target-profile requirement preflight for Python consumers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from re import compile as compile_pattern
from typing import Final
from typing import Never
from typing import cast

from scripts.validate import target_profile

PROFILE_RUNTIME_DIAGNOSTIC_CODE: Final = "MALBOLGE-PROFILE-001"
PROFILE_CAPACITY_DIAGNOSTIC_CODE: Final = "MALBOLGE-PROFILE-002"
SAFE_RUST_CLASSIC_CAPABILITY_ID: Final = "safe-rust-classic"
SAFE_RUST_PROFILED_CAPABILITY_ID: Final = "safe-rust-profiled"
SAFE_RUST_CLASSIC_MAX_WORD_TRITS: Final = 10
SAFE_RUST_CLASSIC_MAX_MEMORY_WORDS: Final = 59_049
SAFE_RUST_PROFILED_MAX_WORD_TRITS: Final = 14
SAFE_RUST_PROFILED_MAX_MEMORY_WORDS: Final = 4_782_969
HISTORICAL_PROFILE_CEILING: Final = "historical-profile-ceiling"
PROFILE_CAPACITY_CEILING: Final = "profile-capacity-ceiling"
WORD_TRITS_DIMENSION: Final = "word-trits"
MEMORY_WORDS_DIMENSION: Final = "memory-words"
NORMATIVE_PROFILE_FEATURES: Final = (
    "byte-input",
    "byte-output",
    "crazy-operation",
    "deterministic",
    "post-instruction-encryption",
    "rotate",
    "self-modification",
    "sequential-guest",
)
_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_FEATURE_ORDER: Final = {
    feature: index for index, feature in enumerate(NORMATIVE_PROFILE_FEATURES)
}


class ProfileRequirementValidationError(ValueError):
    """Profile requirement or runtime capability input is invalid."""


class ProfileRequirementErrorKind(Enum):
    """Stable category for one target-profile preflight rejection."""

    PROFILE_CAPACITY_EXCEEDED = "profile-capacity-exceeded"
    RUNTIME_CAPABILITY_MISSING = "runtime-capability-missing"


@dataclass(frozen=True, slots=True)
class ProfileRequirement:
    """Immutable profile identity and one program's memory requirement."""

    kind: str
    memory_words: int
    profile_id: str
    required_features: tuple[str, ...]
    required_memory_words: int
    version: str
    word_trits: int


@dataclass(frozen=True, slots=True)
class RuntimeCapability:
    """Explicit immutable runtime implementation envelope."""

    capability_id: str
    features: tuple[str, ...]
    max_memory_words: int
    max_word_trits: int


class ProfileRequirementError(ValueError):
    """Deterministic typed profile-capacity or runtime-capability rejection."""

    def __init__(
        self,
        kind: ProfileRequirementErrorKind,
        requirement: ProfileRequirement,
        runtime: RuntimeCapability,
        *,
        missing_dimensions: tuple[str, ...],
    ) -> None:
        """Build one stable rejection without consulting host state."""
        validated = _validated_error_contract(
            kind,
            requirement,
            runtime,
            missing_dimensions=missing_dimensions,
        )
        self.kind: ProfileRequirementErrorKind = validated[0]
        self.requirement: ProfileRequirement = validated[1]
        self.runtime: RuntimeCapability = validated[2]
        self.missing_dimensions: tuple[str, ...] = validated[3]
        super().__init__(_diagnostic_text(self))

    @property
    def code(self) -> str:
        """Stable machine-readable diagnostic code."""
        if self.kind is ProfileRequirementErrorKind.PROFILE_CAPACITY_EXCEEDED:
            return PROFILE_CAPACITY_DIAGNOSTIC_CODE
        return PROFILE_RUNTIME_DIAGNOSTIC_CODE


def build_profile_requirement(
    document: target_profile.JsonObject,
    profile_id: str,
    *,
    required_memory_words: int,
) -> ProfileRequirement:
    """Build one requirement from canonical validated profile data.

    Returns:
        Immutable exact profile and program-memory requirements.

    """
    target_profile.validate_document(document)
    validated_profile_id = _validated_identifier(profile_id, "profile identity")
    profiles = _mapping(document["profiles"], "profiles")
    if validated_profile_id not in profiles:
        _raise_validation("unknown profile identity")
    profile = _mapping(
        profiles[validated_profile_id],
        f"profiles.{validated_profile_id}",
    )
    word = _mapping(profile["word"], f"profiles.{validated_profile_id}.word")
    memory = _mapping(
        profile["memory"],
        f"profiles.{validated_profile_id}.memory",
    )
    return ProfileRequirement(
        kind=_string(profile["kind"], "profile kind"),
        memory_words=_positive_int(memory["words"], "profile memory words"),
        profile_id=validated_profile_id,
        required_features=NORMATIVE_PROFILE_FEATURES,
        required_memory_words=_non_negative_int(
            required_memory_words,
            "required memory words",
        ),
        version=_string(profile["version"], "profile version"),
        word_trits=_positive_int(word["trits"], "profile word trits"),
    )


def build_runtime_capability(
    *,
    capability_id: str,
    features: tuple[str, ...],
    max_memory_words: int,
    max_word_trits: int,
) -> RuntimeCapability:
    """Build one explicit runtime capability with canonical feature ordering.

    Returns:
        Immutable validated runtime capability envelope.

    """
    validated_features = _validated_features(features)
    return RuntimeCapability(
        capability_id=_validated_identifier(
            capability_id,
            "runtime capability identity",
        ),
        features=validated_features,
        max_memory_words=_positive_int(
            max_memory_words,
            "runtime maximum memory words",
        ),
        max_word_trits=_positive_int(
            max_word_trits,
            "runtime maximum word trits",
        ),
    )


def safe_rust_classic_capability() -> RuntimeCapability:
    """Return the explicit classic safe-Rust runtime envelope.

    Returns:
        Ten-trit, 59,049-word normative runtime capability.

    """
    return build_runtime_capability(
        capability_id=SAFE_RUST_CLASSIC_CAPABILITY_ID,
        features=NORMATIVE_PROFILE_FEATURES,
        max_memory_words=SAFE_RUST_CLASSIC_MAX_MEMORY_WORDS,
        max_word_trits=SAFE_RUST_CLASSIC_MAX_WORD_TRITS,
    )


def safe_rust_profiled_capability() -> RuntimeCapability:
    """Return the explicit profile-driven safe-Rust runtime envelope.

    Returns:
        Fourteen-trit, 4,782,969-word normative runtime capability.

    """
    return build_runtime_capability(
        capability_id=SAFE_RUST_PROFILED_CAPABILITY_ID,
        features=NORMATIVE_PROFILE_FEATURES,
        max_memory_words=SAFE_RUST_PROFILED_MAX_MEMORY_WORDS,
        max_word_trits=SAFE_RUST_PROFILED_MAX_WORD_TRITS,
    )


def preflight_profile_requirement(
    requirement: ProfileRequirement,
    runtime: RuntimeCapability,
) -> None:
    """Validate one exact profile/program requirement against one runtime.

    Raises:
        ProfileRequirementError: For profile capacity or runtime mismatch.

    """
    validated_requirement = _validated_requirement(requirement)
    validated_runtime = _validated_runtime(runtime)
    if (
        validated_requirement.required_memory_words
        > validated_requirement.memory_words
    ):
        raise ProfileRequirementError(
            ProfileRequirementErrorKind.PROFILE_CAPACITY_EXCEEDED,
            validated_requirement,
            validated_runtime,
            missing_dimensions=(),
        )
    missing = _missing_dimensions(validated_requirement, validated_runtime)
    if missing:
        raise ProfileRequirementError(
            ProfileRequirementErrorKind.RUNTIME_CAPABILITY_MISSING,
            validated_requirement,
            validated_runtime,
            missing_dimensions=missing,
        )


def _validated_error_contract(
    kind: ProfileRequirementErrorKind,
    requirement: ProfileRequirement,
    runtime: RuntimeCapability,
    *,
    missing_dimensions: tuple[str, ...],
) -> tuple[
    ProfileRequirementErrorKind,
    ProfileRequirement,
    RuntimeCapability,
    tuple[str, ...],
]:
    validated_kind = _validated_error_kind(kind)
    validated_requirement = _validated_requirement(requirement)
    validated_runtime = _validated_runtime(runtime)
    validated_dimensions = _validated_error_dimensions(missing_dimensions)
    expected_kind, expected_dimensions = _expected_error_contract(
        validated_requirement,
        validated_runtime,
    )
    _validate_error_match(
        validated_kind,
        validated_dimensions,
        expected_kind=expected_kind,
        expected_dimensions=expected_dimensions,
    )
    return (
        validated_kind,
        validated_requirement,
        validated_runtime,
        validated_dimensions,
    )


def _validated_error_kind(
    value: ProfileRequirementErrorKind,
) -> ProfileRequirementErrorKind:
    if type(value) is not ProfileRequirementErrorKind:
        _raise_validation("diagnostic kind must use the exact enum type")
    return value


def _validated_error_dimensions(
    value: tuple[str, ...],
) -> tuple[str, ...]:
    if type(value) is not tuple:
        _raise_validation(
            "diagnostic missing dimensions must use the exact immutable tuple"
        )
    return value


def _validate_error_match(
    kind: ProfileRequirementErrorKind,
    dimensions: tuple[str, ...],
    *,
    expected_kind: ProfileRequirementErrorKind | None,
    expected_dimensions: tuple[str, ...],
) -> None:
    if expected_kind is None:
        _raise_validation("diagnostic requires a rejected profile preflight")
    if kind is not expected_kind:
        _raise_validation(
            "diagnostic kind does not match the preflight rejection"
        )
    if dimensions != expected_dimensions:
        _raise_validation(
            "diagnostic missing dimensions do not match the preflight rejection"
        )


def _expected_error_contract(
    requirement: ProfileRequirement,
    runtime: RuntimeCapability,
) -> tuple[ProfileRequirementErrorKind | None, tuple[str, ...]]:
    if requirement.required_memory_words > requirement.memory_words:
        return ProfileRequirementErrorKind.PROFILE_CAPACITY_EXCEEDED, ()
    missing = _missing_dimensions(requirement, runtime)
    if missing:
        return ProfileRequirementErrorKind.RUNTIME_CAPABILITY_MISSING, missing
    return None, ()


def _validated_requirement(value: ProfileRequirement) -> ProfileRequirement:
    if type(value) is not ProfileRequirement:
        _raise_validation("requirement must use the exact immutable type")
    _ = _validated_identifier(value.profile_id, "profile identity")
    _ = _string(value.version, "profile version")
    if value.kind not in {
        target_profile.CURRENT_KIND,
        target_profile.HISTORICAL_KIND,
        target_profile.VERSIONED_KIND,
    }:
        _raise_validation("profile kind is unsupported")
    _ = _positive_int(value.word_trits, "profile word trits")
    _ = _positive_int(value.memory_words, "profile memory words")
    _ = _non_negative_int(
        value.required_memory_words,
        "required memory words",
    )
    if value.required_features != NORMATIVE_PROFILE_FEATURES:
        _raise_validation(
            "profile features must equal the normative feature set"
        )
    canonical = build_profile_requirement(
        target_profile.load_document(target_profile.DEFAULT_PROFILE),
        value.profile_id,
        required_memory_words=value.required_memory_words,
    )
    if value != canonical:
        _raise_validation(
            "profile fields must match canonical profile authority"
        )
    return value


def _validated_runtime(value: RuntimeCapability) -> RuntimeCapability:
    if type(value) is not RuntimeCapability:
        _raise_validation("runtime must use the exact immutable type")
    _ = _validated_identifier(
        value.capability_id,
        "runtime capability identity",
    )
    _ = _validated_features(value.features)
    _ = _positive_int(value.max_memory_words, "runtime maximum memory words")
    _ = _positive_int(value.max_word_trits, "runtime maximum word trits")
    canonical = _canonical_runtime_capability(value.capability_id)
    if canonical is not None and value != canonical:
        _raise_validation(
            "reserved runtime fields must match canonical runtime authority"
        )
    return value


def _canonical_runtime_capability(
    capability_id: str,
) -> RuntimeCapability | None:
    if capability_id == SAFE_RUST_CLASSIC_CAPABILITY_ID:
        return safe_rust_classic_capability()
    if capability_id == SAFE_RUST_PROFILED_CAPABILITY_ID:
        return safe_rust_profiled_capability()
    return None


def _validated_features(value: tuple[str, ...]) -> tuple[str, ...]:
    if type(value) is not tuple:
        _raise_validation("runtime features must use the exact immutable tuple")
    _validate_feature_members(value)
    ordered = tuple(sorted(value, key=_FEATURE_ORDER.__getitem__))
    if value != ordered:
        _raise_validation("runtime features are not canonically ordered")
    return value


def _validate_feature_members(value: tuple[str, ...]) -> None:
    if len(value) != len(set(value)):
        _raise_validation("runtime features contain duplicates")
    for feature in value:
        if type(feature) is not str or feature not in _FEATURE_ORDER:
            _raise_validation("runtime features contain an unsupported feature")


def _missing_dimensions(
    requirement: ProfileRequirement,
    runtime: RuntimeCapability,
) -> tuple[str, ...]:
    missing: list[str] = []
    if requirement.word_trits > runtime.max_word_trits:
        missing.append(WORD_TRITS_DIMENSION)
    if requirement.memory_words > runtime.max_memory_words:
        missing.append(MEMORY_WORDS_DIMENSION)
    available = frozenset(runtime.features)
    missing.extend(
        feature
        for feature in requirement.required_features
        if feature not in available
    )
    return tuple(missing)


def _diagnostic_text(error: ProfileRequirementError) -> str:
    requirement = error.requirement
    if error.kind is ProfileRequirementErrorKind.PROFILE_CAPACITY_EXCEEDED:
        constraint = (
            HISTORICAL_PROFILE_CEILING
            if requirement.kind == target_profile.HISTORICAL_KIND
            else PROFILE_CAPACITY_CEILING
        )
        return " ".join((
            PROFILE_CAPACITY_DIAGNOSTIC_CODE,
            f"profile={requirement.profile_id}",
            f"version={requirement.version}",
            f"constraint={constraint}",
            f"required_memory_words={requirement.required_memory_words}",
            f"profile_memory_words={requirement.memory_words}",
        ))
    runtime = error.runtime
    return " ".join((
        PROFILE_RUNTIME_DIAGNOSTIC_CODE,
        f"profile={requirement.profile_id}",
        f"version={requirement.version}",
        f"required_features={",".join(requirement.required_features)}",
        f"required_word_trits={requirement.word_trits}",
        f"required_memory_words={requirement.memory_words}",
        f"runtime={runtime.capability_id}",
        f"max_word_trits={runtime.max_word_trits}",
        f"max_memory_words={runtime.max_memory_words}",
        f"missing={",".join(error.missing_dimensions)}",
    ))


def _mapping(value: object, context: str) -> target_profile.JsonObject:
    if not isinstance(value, dict):
        _raise_validation(f"{context} must be an object")
    return cast("target_profile.JsonObject", value)


def _string(value: object, context: str) -> str:
    if type(value) is not str or not value:
        _raise_validation(f"{context} must be a nonempty string")
    return value


def _non_negative_int(value: object, context: str) -> int:
    if type(value) is not int or value < 0:
        _raise_validation(f"{context} must be a non-negative integer")
    return value


def _positive_int(value: object, context: str) -> int:
    if type(value) is not int or value <= 0:
        _raise_validation(f"{context} must be a positive integer")
    return value


def _validated_identifier(value: str, context: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_validation(f"{context} must use canonical ASCII identity form")
    return value


def _raise_validation(detail: str) -> Never:
    message = f"target profile requirement {detail}"
    raise ProfileRequirementValidationError(message)
