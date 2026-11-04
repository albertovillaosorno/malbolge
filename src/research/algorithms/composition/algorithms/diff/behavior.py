# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Generic behavior-probe semantics for source-bound admission.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Generic behavior-probe semantics for source-bound admission."""

from __future__ import annotations

import builtins
import math
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal as _native_decimal
from enum import StrEnum
from types import MemberDescriptorType
from typing import cast

_ZERO = 0
_ONE = 1
_NUL = "\x00"
# Do not allow domain-loaded code to redefine finite score admission.
_NATIVE_ISFINITE = math.isfinite
_NATIVE_SORTED = builtins.sorted
_NATIVE_SET = builtins.set
_NATIVE_TYPE = builtins.type
_NATIVE_ANY = builtins.any
_NATIVE_LEN = builtins.len
_NATIVE_TUPLE = builtins.tuple
_NATIVE_LIST = builtins.list
_NATIVE_STR = builtins.str
_NATIVE_BYTES = builtins.bytes
_NATIVE_BOOL = builtins.bool
_NATIVE_INT = builtins.int
_NATIVE_FLOAT = builtins.float
_NATIVE_ATTRIBUTE_ERROR = builtins.AttributeError
_NATIVE_TYPE_ERROR = builtins.TypeError
_NATIVE_UNICODE_ENCODE_ERROR = builtins.UnicodeEncodeError
_NATIVE_OBJECT_NEW = object.__new__


class BehaviorPolicyError(ValueError):
    """Raised when behavior profile or observation shape is invalid."""


class BehaviorAdmissionError(RuntimeError):
    """Raised when mandatory behavior evidence does not admit a candidate."""


# Consumer-loaded modules may replace public exception names after import.
# Rejection authority keeps the original native classes.
_NATIVE_BEHAVIOR_POLICY_ERROR = BehaviorPolicyError
_NATIVE_BEHAVIOR_ADMISSION_ERROR = BehaviorAdmissionError


class BugState(StrEnum):
    """Observed candidate state for one known historical defect."""

    PRESENT = "present"
    FIXED = "fixed"
    UNKNOWN = "unknown"


def _require_identifier(value: object, context: str) -> str:
    if _NATIVE_TYPE(value) is not _NATIVE_STR or not value:
        message = f"{context} must be a non-empty string"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    if _NUL in value:
        message = f"{context} must be portable UTF-8 text without NUL"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    try:
        _ = value.encode("utf-8")
    except _NATIVE_UNICODE_ENCODE_ERROR as error:
        message = f"{context} must be portable UTF-8 text"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message) from error
    return value


def _require_digest(value: object, context: str) -> bytes:
    if _NATIVE_TYPE(value) is not _NATIVE_BYTES or not value:
        message = f"{context} must be non-empty exact bytes"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    return value


@dataclass(frozen=True, slots=True, order=True, init=False)
class IdentityProbe:
    """Stable historical behavior fingerprint expected from source lineage."""

    probe_id: str
    expected_digest: bytes

    def __init__(
        self,
        probe_id: str,
        expected_digest: bytes,
    ) -> None:
        """Validate IdentityProbe via its original constructor guard."""
        _IDENTITY_PROBE_ID_SLOT.__set__(self, probe_id)
        _IDENTITY_PROBE_DIGEST_SLOT.__set__(self, expected_digest)
        _IDENTITY_PROBE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require canonical probe identity and exact fingerprint bytes."""
        _ = _require_identifier(_probe_identifier(self), "identity probe ID")
        _ = _require_digest(
            cast(
                "bytes",
                _IDENTITY_PROBE_DIGEST_SLOT.__get__(self, IdentityProbe),
            ),
            "identity probe digest",
        )


# Pin the original validator before consumers can replace class hooks.
_IDENTITY_PROBE_ID_SLOT = cast(
    "MemberDescriptorType", IdentityProbe.__dict__["probe_id"]
)
_IDENTITY_PROBE_DIGEST_SLOT = cast(
    "MemberDescriptorType", IdentityProbe.__dict__["expected_digest"]
)


_IDENTITY_PROBE_VALIDATOR = cast(
    "Callable[[IdentityProbe], None]",
    IdentityProbe.__dict__["__post_init__"],
)


@dataclass(frozen=True, slots=True, order=True, init=False)
class CompatibilityProbe:
    """Named runtime/build precondition required before transformation."""

    probe_id: str

    def __init__(
        self,
        probe_id: str,
    ) -> None:
        """Validate CompatibilityProbe via its original constructor guard."""
        _COMPATIBILITY_PROBE_ID_SLOT.__set__(self, probe_id)
        _COMPATIBILITY_PROBE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require one canonical compatibility probe identity."""
        _ = _require_identifier(
            _probe_identifier(self), "compatibility probe ID"
        )


# Pin the original validator before consumers can replace class hooks.
_COMPATIBILITY_PROBE_ID_SLOT = cast(
    "MemberDescriptorType", CompatibilityProbe.__dict__["probe_id"]
)


_COMPATIBILITY_PROBE_VALIDATOR = cast(
    "Callable[[CompatibilityProbe], None]",
    CompatibilityProbe.__dict__["__post_init__"],
)


@dataclass(frozen=True, slots=True, order=True, init=False)
class BugProbe:
    """Known defect whose correction can be skipped when already fixed."""

    probe_id: str
    correction_id: str

    def __init__(
        self,
        probe_id: str,
        correction_id: str,
    ) -> None:
        """Validate BugProbe via its original constructor guard."""
        _BUG_PROBE_ID_SLOT.__set__(self, probe_id)
        _BUG_PROBE_CORRECTION_SLOT.__set__(self, correction_id)
        _BUG_PROBE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require canonical bug and correction identities."""
        _ = _require_identifier(_probe_identifier(self), "bug probe ID")
        _ = _require_identifier(
            cast("str", _BUG_PROBE_CORRECTION_SLOT.__get__(self, BugProbe)),
            "bug correction ID",
        )


# Pin the original validator before consumers can replace class hooks.
_BUG_PROBE_ID_SLOT = cast("MemberDescriptorType", BugProbe.__dict__["probe_id"])
_BUG_PROBE_CORRECTION_SLOT = cast(
    "MemberDescriptorType", BugProbe.__dict__["correction_id"]
)


_BUG_PROBE_VALIDATOR = cast(
    "Callable[[BugProbe], None]",
    BugProbe.__dict__["__post_init__"],
)


def _probe_ids(
    probes: tuple[IdentityProbe, ...]
    | tuple[CompatibilityProbe, ...]
    | tuple[BugProbe, ...],
) -> tuple[str, ...]:
    identifiers = _NATIVE_TUPLE(_probe_identifier(item) for item in probes)
    if _NATIVE_ANY(not identifier for identifier in identifiers):
        message = "behavior probe identifiers must be non-empty"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    if identifiers != _NATIVE_TUPLE(_NATIVE_SORTED(identifiers)):
        message = "behavior probes must be sorted by probe_id"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    return identifiers


def _validate_unique(values: tuple[str, ...], message: str) -> None:
    if _NATIVE_LEN(values) != _NATIVE_LEN(_NATIVE_SET(values)):
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)


def _validate_correction_ids(bugs: tuple[BugProbe, ...]) -> None:
    correction_ids = _NATIVE_TUPLE(
        cast("str", _BUG_PROBE_CORRECTION_SLOT.__get__(item, BugProbe))
        for item in bugs
    )
    if _NATIVE_ANY(not correction_id for correction_id in correction_ids):
        message = "bug probes require non-empty correction identifiers"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    _validate_unique(
        correction_ids, "bug correction identifiers must be unique"
    )


def _require_probe_tuple(
    value: object,
    item_type: type[IdentityProbe | CompatibilityProbe | BugProbe],
    context: str,
) -> None:
    if _NATIVE_TYPE(value) is not _NATIVE_TUPLE:
        message = f"{context} must use the exact immutable tuple type"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    items = cast("tuple[object, ...]", value)
    if _NATIVE_ANY(_NATIVE_TYPE(item) is not item_type for item in items):
        message = f"{context} contains a foreign probe record"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    # Exact native type does not imply the child constructor ran. Nested
    # records control the source-bound behavior decision, so validate their
    # stored fields using their original, captured constructors' guards.
    validator = cast(
        "Callable[[object], None]",
        _IDENTITY_PROBE_VALIDATOR
        if item_type is IdentityProbe
        else (
            _COMPATIBILITY_PROBE_VALIDATOR
            if item_type is CompatibilityProbe
            else _BUG_PROBE_VALIDATOR
        ),
    )
    try:
        for item in items:
            validator(item)
    except (_NATIVE_ATTRIBUTE_ERROR, _NATIVE_TYPE_ERROR) as error:
        message = f"{context} contains incomplete native probe metadata"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message) from error


@dataclass(frozen=True, slots=True, init=False)
class BehaviorProfile:
    """Behavior expectations generated from the authoring source."""

    identity: tuple[IdentityProbe, ...]
    compatibility: tuple[CompatibilityProbe, ...]
    bugs: tuple[BugProbe, ...]

    def __init__(
        self,
        identity: tuple[IdentityProbe, ...],
        compatibility: tuple[CompatibilityProbe, ...],
        bugs: tuple[BugProbe, ...],
    ) -> None:
        """Validate BehaviorProfile via its original constructor guard."""
        _PROFILE_IDENTITY_SLOT.__set__(self, identity)
        _PROFILE_COMPATIBILITY_SLOT.__set__(self, compatibility)
        _PROFILE_BUGS_SLOT.__set__(self, bugs)
        _BEHAVIOR_PROFILE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require deterministic unique probe identifiers.

        Raises:
            BehaviorPolicyError: Probe identifiers violate profile policy.

        """
        identity, compatibility, bugs = _profile_fields(self)
        _require_probe_tuple(identity, IdentityProbe, "identity probes")
        _require_probe_tuple(
            compatibility, CompatibilityProbe, "compatibility probes"
        )
        _require_probe_tuple(bugs, BugProbe, "bug probes")
        if not identity:
            message = "behavior profile requires at least one identity probe"
            raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
        groups = (
            _probe_ids(identity),
            _probe_ids(compatibility),
            _probe_ids(bugs),
        )
        all_ids = _NATIVE_TUPLE(
            identifier for group in groups for identifier in group
        )
        _validate_unique(
            all_ids, "behavior probe identifiers must be globally unique"
        )
        _validate_correction_ids(bugs)


# Pin the original validator before consumers can replace class hooks.
_BEHAVIOR_PROFILE_VALIDATOR = cast(
    "Callable[[BehaviorProfile], None]",
    BehaviorProfile.__dict__["__post_init__"],
)


_PROFILE_IDENTITY_SLOT = cast(
    "MemberDescriptorType", BehaviorProfile.__dict__["identity"]
)
_PROFILE_COMPATIBILITY_SLOT = cast(
    "MemberDescriptorType", BehaviorProfile.__dict__["compatibility"]
)
_PROFILE_BUGS_SLOT = cast(
    "MemberDescriptorType", BehaviorProfile.__dict__["bugs"]
)


def _profile_fields(
    profile: BehaviorProfile,
) -> tuple[
    tuple[IdentityProbe, ...],
    tuple[CompatibilityProbe, ...],
    tuple[BugProbe, ...],
]:
    owner = BehaviorProfile
    return (
        cast(
            "tuple[IdentityProbe, ...]",
            _PROFILE_IDENTITY_SLOT.__get__(profile, owner),
        ),
        cast(
            "tuple[CompatibilityProbe, ...]",
            _PROFILE_COMPATIBILITY_SLOT.__get__(profile, owner),
        ),
        cast(
            "tuple[BugProbe, ...]", _PROFILE_BUGS_SLOT.__get__(profile, owner)
        ),
    )


@dataclass(frozen=True, slots=True, order=True, init=False)
class IdentityObservation:
    """Candidate identity-probe result; ``None`` means execution unavailable."""

    probe_id: str
    digest: bytes | None

    def __init__(
        self,
        probe_id: str,
        digest: bytes | None,
    ) -> None:
        """Validate IdentityObservation via its original constructor guard."""
        _IDENTITY_OBSERVATION_ID_SLOT.__set__(self, probe_id)
        _IDENTITY_OBSERVATION_DIGEST_SLOT.__set__(self, digest)
        _IDENTITY_OBSERVATION_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require canonical identity evidence or explicit unavailability."""
        _ = _require_identifier(
            _observation_identifier(self), "identity observation ID"
        )
        digest = cast(
            "bytes | None",
            _IDENTITY_OBSERVATION_DIGEST_SLOT.__get__(
                self, IdentityObservation
            ),
        )
        if digest is not None:
            _ = _require_digest(digest, "identity observation digest")


# Pin the original validator before consumers can replace class hooks.
_IDENTITY_OBSERVATION_VALIDATOR = cast(
    "Callable[[IdentityObservation], None]",
    IdentityObservation.__dict__["__post_init__"],
)


_IDENTITY_OBSERVATION_ID_SLOT = cast(
    "MemberDescriptorType", IdentityObservation.__dict__["probe_id"]
)


_IDENTITY_OBSERVATION_DIGEST_SLOT = cast(
    "MemberDescriptorType", IdentityObservation.__dict__["digest"]
)


@dataclass(frozen=True, slots=True, order=True, init=False)
class CompatibilityObservation:
    """Candidate precondition result; ``None`` means execution unavailable."""

    probe_id: str
    compatible: bool | None

    def __init__(
        self,
        probe_id: str,
        compatible: bool | None,
    ) -> None:
        """Seal compatibility observation through original validation."""
        _COMPATIBILITY_OBSERVATION_ID_SLOT.__set__(self, probe_id)
        _COMPATIBILITY_OBSERVATION_VALUE_SLOT.__set__(self, compatible)
        _COMPATIBILITY_OBSERVATION_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require canonical identity and exact tri-state compatibility.

        Raises:
            BehaviorPolicyError: Identity or compatibility metadata is invalid.

        """
        _ = _require_identifier(
            _observation_identifier(self), "compatibility observation ID"
        )
        compatible = cast(
            "bool | None",
            _COMPATIBILITY_OBSERVATION_VALUE_SLOT.__get__(
                self, CompatibilityObservation
            ),
        )
        if (
            compatible is not None
            and _NATIVE_TYPE(compatible) is not _NATIVE_BOOL
        ):
            message = "compatibility observation must be bool or None"
            raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)


# Pin the original validator before consumers can replace class hooks.
_COMPATIBILITY_OBSERVATION_VALIDATOR = cast(
    "Callable[[CompatibilityObservation], None]",
    CompatibilityObservation.__dict__["__post_init__"],
)


_COMPATIBILITY_OBSERVATION_ID_SLOT = cast(
    "MemberDescriptorType", CompatibilityObservation.__dict__["probe_id"]
)


_COMPATIBILITY_OBSERVATION_VALUE_SLOT = cast(
    "MemberDescriptorType", CompatibilityObservation.__dict__["compatible"]
)


@dataclass(frozen=True, slots=True, order=True, init=False)
class BugObservation:
    """Candidate classification for one known historical defect."""

    probe_id: str
    state: BugState

    def __init__(
        self,
        probe_id: str,
        state: BugState,
    ) -> None:
        """Validate BugObservation via its original constructor guard."""
        _BUG_OBSERVATION_ID_SLOT.__set__(self, probe_id)
        _BUG_OBSERVATION_STATE_SLOT.__set__(self, state)
        _BUG_OBSERVATION_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require canonical identity and exact bug-state enum metadata.

        Raises:
            BehaviorPolicyError: Identity or bug-state metadata is invalid.

        """
        _ = _require_identifier(
            _observation_identifier(self), "bug observation ID"
        )
        state = cast(
            "BugState",
            _BUG_OBSERVATION_STATE_SLOT.__get__(self, BugObservation),
        )
        if _NATIVE_TYPE(state) is not BugState:
            message = "bug observation state must use the exact BugState type"
            raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)


# Pin the original validator before consumers can replace class hooks.
_BUG_OBSERVATION_VALIDATOR = cast(
    "Callable[[BugObservation], None]",
    BugObservation.__dict__["__post_init__"],
)


_BUG_OBSERVATION_ID_SLOT = cast(
    "MemberDescriptorType", BugObservation.__dict__["probe_id"]
)


_BUG_OBSERVATION_STATE_SLOT = cast(
    "MemberDescriptorType", BugObservation.__dict__["state"]
)


def _probe_identifier(
    probe: IdentityProbe | CompatibilityProbe | BugProbe,
) -> str:
    """Read a validated probe ID without mutable class field dispatch."""
    kind = _NATIVE_TYPE(probe)
    if kind is IdentityProbe:
        return cast(
            "str", _IDENTITY_PROBE_ID_SLOT.__get__(probe, IdentityProbe)
        )
    if kind is CompatibilityProbe:
        return cast(
            "str",
            _COMPATIBILITY_PROBE_ID_SLOT.__get__(probe, CompatibilityProbe),
        )
    if kind is BugProbe:
        return cast("str", _BUG_PROBE_ID_SLOT.__get__(probe, BugProbe))
    message = "behavior probe identifier requires exact probe record"
    raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)


def _observation_identifier(
    observation: (
        IdentityObservation | CompatibilityObservation | BugObservation
    ),
) -> str:
    """Read a validated observation ID from its original immutable slot."""
    kind = _NATIVE_TYPE(observation)
    if kind is IdentityObservation:
        return cast(
            "str", _IDENTITY_OBSERVATION_ID_SLOT.__get__(
                observation, IdentityObservation
            )
        )
    if kind is CompatibilityObservation:
        return cast(
            "str", _COMPATIBILITY_OBSERVATION_ID_SLOT.__get__(
                observation, CompatibilityObservation
            )
        )
    if kind is BugObservation:
        return cast(
            "str", _BUG_OBSERVATION_ID_SLOT.__get__(observation, BugObservation)
        )
    message = (
        "behavior observation identifier requires exact observation record"
    )
    raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)


def _require_observation_tuple(
    value: object,
    item_type: (
        type[IdentityObservation | CompatibilityObservation | BugObservation]
    ),
    context: str,
) -> None:
    if _NATIVE_TYPE(value) is not _NATIVE_TUPLE:
        message = f"{context} must use the exact immutable tuple type"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    items = cast("tuple[object, ...]", value)
    if _NATIVE_ANY(_NATIVE_TYPE(item) is not item_type for item in items):
        message = f"{context} contains a foreign observation record"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    validator = cast(
        "Callable[[object], None]",
        _IDENTITY_OBSERVATION_VALIDATOR
        if item_type is IdentityObservation
        else (
            _COMPATIBILITY_OBSERVATION_VALIDATOR
            if item_type is CompatibilityObservation
            else _BUG_OBSERVATION_VALIDATOR
        ),
    )
    try:
        for item in items:
            validator(item)
    except (_NATIVE_ATTRIBUTE_ERROR, _NATIVE_TYPE_ERROR) as error:
        message = f"{context} contains incomplete native observation metadata"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message) from error


@dataclass(frozen=True, slots=True, init=False)
class BehaviorObservations:
    """All candidate probe results for one deterministic evaluation."""

    identity: tuple[IdentityObservation, ...]
    compatibility: tuple[CompatibilityObservation, ...]
    bugs: tuple[BugObservation, ...]

    def __init__(
        self,
        identity: tuple[IdentityObservation, ...],
        compatibility: tuple[CompatibilityObservation, ...],
        bugs: tuple[BugObservation, ...],
    ) -> None:
        """Validate BehaviorObservations via its original constructor guard."""
        _OBSERVATIONS_IDENTITY_SLOT.__set__(self, identity)
        _OBSERVATIONS_COMPATIBILITY_SLOT.__set__(self, compatibility)
        _OBSERVATIONS_BUGS_SLOT.__set__(self, bugs)
        _BEHAVIOR_OBSERVATIONS_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require immutable exact observation records for every category."""
        identity, compatibility, bugs = _observations_fields(self)
        _require_observation_tuple(
            identity, IdentityObservation, "identity observations"
        )
        _require_observation_tuple(
            compatibility,
            CompatibilityObservation,
            "compatibility observations",
        )
        _require_observation_tuple(bugs, BugObservation, "bug observations")


# Pin the original validator before consumers can replace class hooks.
_BEHAVIOR_OBSERVATIONS_VALIDATOR = cast(
    "Callable[[BehaviorObservations], None]",
    BehaviorObservations.__dict__["__post_init__"],
)


_OBSERVATIONS_IDENTITY_SLOT = cast(
    "MemberDescriptorType", BehaviorObservations.__dict__["identity"]
)
_OBSERVATIONS_COMPATIBILITY_SLOT = cast(
    "MemberDescriptorType", BehaviorObservations.__dict__["compatibility"]
)
_OBSERVATIONS_BUGS_SLOT = cast(
    "MemberDescriptorType", BehaviorObservations.__dict__["bugs"]
)


def _observations_fields(
    observations: BehaviorObservations,
) -> tuple[
    tuple[IdentityObservation, ...],
    tuple[CompatibilityObservation, ...],
    tuple[BugObservation, ...],
]:
    owner = BehaviorObservations
    return (
        cast(
            "tuple[IdentityObservation, ...]",
            _OBSERVATIONS_IDENTITY_SLOT.__get__(observations, owner),
        ),
        cast(
            "tuple[CompatibilityObservation, ...]",
            _OBSERVATIONS_COMPATIBILITY_SLOT.__get__(observations, owner),
        ),
        cast(
            "tuple[BugObservation, ...]",
            _OBSERVATIONS_BUGS_SLOT.__get__(observations, owner),
        ),
    )


def _require_evidence_similarity(value: object) -> float:
    if _NATIVE_TYPE(value) is not _NATIVE_FLOAT or not _NATIVE_ISFINITE(value):
        message = "behavior evidence similarity must use a finite exact float"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    if value < _ZERO or value > _ONE:
        message = "behavior evidence similarity must be in [0, 1]"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    return value


def _require_evidence_count(value: object, context: str, minimum: int) -> int:
    if _NATIVE_TYPE(value) is not _NATIVE_INT or value < minimum:
        message = f"{context} must use an exact integer >= {minimum}"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    return value


def _require_string_tuple(value: object, context: str) -> tuple[str, ...]:
    if _NATIVE_TYPE(value) is not _NATIVE_TUPLE:
        message = f"{context} must use the exact immutable tuple type"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    items = cast("tuple[object, ...]", value)
    if _NATIVE_ANY(
        _NATIVE_TYPE(item) is not _NATIVE_STR or not item for item in items
    ):
        message = f"{context} must contain non-empty exact strings"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    return cast("tuple[str, ...]", value)


def _validate_behavior_evidence(evidence: BehaviorEvidence) -> None:
    (
        similarity_value,
        matched_count,
        total_count,
        apply_values,
        skip_values,
        _,
        _,
        _,
    ) = _behavior_evidence_fields(evidence)
    similarity = _require_evidence_similarity(similarity_value)
    matched = _require_evidence_count(
        matched_count, "matched identity probe count", _ZERO
    )
    total = _require_evidence_count(
        total_count, "total identity probe count", _ONE
    )
    if matched > total:
        message = "matched identity probe count cannot exceed total"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    if similarity != matched / total:
        message = "behavior evidence similarity does not match probe counts"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    apply = _require_string_tuple(apply_values, "corrections to apply")
    skip = _require_string_tuple(skip_values, "corrections to skip")
    if _NATIVE_LEN(apply) != _NATIVE_LEN(_NATIVE_SET(apply)) or _NATIVE_LEN(
        skip
    ) != _NATIVE_LEN(_NATIVE_SET(skip)):
        message = "behavior correction routes must not contain duplicates"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    if _NATIVE_SET(apply) & _NATIVE_SET(skip):
        message = "behavior correction routes must be disjoint"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    _ = _require_string_tuple(
        cast(
            "object", _BEHAVIOR_REASONS_SLOT.__get__(evidence, BehaviorEvidence)
        ),
        "behavior evidence reasons",
    )
    _validate_behavior_evidence_binding(evidence)


@dataclass(frozen=True, slots=True, init=False)
class BehaviorEvidence:
    """Aggregated behavior admission plus bug-correction routing."""

    similarity: float
    matched_identity_probes: int
    total_identity_probes: int
    corrections_to_apply: tuple[str, ...]
    corrections_to_skip: tuple[str, ...]
    reasons: tuple[str, ...]
    profile: BehaviorProfile
    observations: BehaviorObservations
    minimum_similarity: float

    def __init__(
        self,
        similarity: float,
        matched_identity_probes: int,
        total_identity_probes: int,
        corrections_to_apply: tuple[str, ...],
        corrections_to_skip: tuple[str, ...],
        reasons: tuple[str, ...],
        profile: BehaviorProfile,
        observations: BehaviorObservations,
        minimum_similarity: float,
    ) -> None:
        """Validate BehaviorEvidence via its original constructor guard."""
        _BEHAVIOR_SIMILARITY_SLOT.__set__(self, similarity)
        _BEHAVIOR_MATCHED_SLOT.__set__(self, matched_identity_probes)
        _BEHAVIOR_TOTAL_SLOT.__set__(self, total_identity_probes)
        _BEHAVIOR_APPLY_SLOT.__set__(self, corrections_to_apply)
        _BEHAVIOR_SKIP_SLOT.__set__(self, corrections_to_skip)
        _BEHAVIOR_REASONS_SLOT.__set__(self, reasons)
        _BEHAVIOR_PROFILE_SLOT.__set__(self, profile)
        _BEHAVIOR_OBSERVATIONS_SLOT.__set__(self, observations)
        _BEHAVIOR_MINIMUM_SLOT.__set__(self, minimum_similarity)
        _BEHAVIOR_EVIDENCE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require internally coherent aggregated behavior evidence."""
        _validate_behavior_evidence(self)

    @property
    def admitted(self) -> bool:
        """Whether all mandatory behavior requirements passed.

        Returns:
            True exactly when no deterministic rejection reason exists.

        """
        if _NATIVE_TYPE(self) is not BehaviorEvidence:
            message = "behavior evidence requires exact BehaviorEvidence"
            raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
        # Exact native receipts can be allocated without this constructor.
        # Re-check the original binding before exposing a public verdict.
        try:
            _BEHAVIOR_EVIDENCE_VALIDATOR(self)
        except (_NATIVE_ATTRIBUTE_ERROR, _NATIVE_TYPE_ERROR) as error:
            message = "behavior evidence has incomplete native metadata"
            raise _NATIVE_BEHAVIOR_POLICY_ERROR(message) from error
        return not _BEHAVIOR_REASONS_SLOT.__get__(self, BehaviorEvidence)


# Pin the original validator before consumers can replace class hooks.
_BEHAVIOR_EVIDENCE_VALIDATOR = cast(
    "Callable[[BehaviorEvidence], None]",
    BehaviorEvidence.__dict__["__post_init__"],
)


# The class descriptor can change after domain callbacks; trust the saved
# original frozen slot reader for evidence binding and admission decisions.
_BEHAVIOR_REASONS_SLOT = cast(
    "MemberDescriptorType", BehaviorEvidence.__dict__["reasons"]
)
_BEHAVIOR_SIMILARITY_SLOT = cast(
    "MemberDescriptorType", BehaviorEvidence.__dict__["similarity"]
)
_BEHAVIOR_MATCHED_SLOT = cast(
    "MemberDescriptorType", BehaviorEvidence.__dict__["matched_identity_probes"]
)
_BEHAVIOR_TOTAL_SLOT = cast(
    "MemberDescriptorType", BehaviorEvidence.__dict__["total_identity_probes"]
)
_BEHAVIOR_APPLY_SLOT = cast(
    "MemberDescriptorType", BehaviorEvidence.__dict__["corrections_to_apply"]
)
_BEHAVIOR_SKIP_SLOT = cast(
    "MemberDescriptorType", BehaviorEvidence.__dict__["corrections_to_skip"]
)
_BEHAVIOR_PROFILE_SLOT = cast(
    "MemberDescriptorType", BehaviorEvidence.__dict__["profile"]
)
_BEHAVIOR_OBSERVATIONS_SLOT = cast(
    "MemberDescriptorType", BehaviorEvidence.__dict__["observations"]
)
_BEHAVIOR_MINIMUM_SLOT = cast(
    "MemberDescriptorType", BehaviorEvidence.__dict__["minimum_similarity"]
)

_BEHAVIOR_EVIDENCE_INIT = cast(
    Callable[
        [
            BehaviorEvidence,
            float,
            int,
            int,
            tuple[str, ...],
            tuple[str, ...],
            tuple[str, ...],
            BehaviorProfile,
            BehaviorObservations,
            float,
        ],
        None,
    ],
    BehaviorEvidence.__dict__["__init__"],
)


def _new_behavior_evidence(
    similarity: float,
    matched_identity_probes: int,
    total_identity_probes: int,
    corrections_to_apply: tuple[str, ...],
    corrections_to_skip: tuple[str, ...],
    reasons: tuple[str, ...],
    profile: BehaviorProfile,
    observations: BehaviorObservations,
    minimum_similarity: float,
) -> BehaviorEvidence:
    """Validate internal decisions without late evidence class constructors."""
    evidence = _NATIVE_OBJECT_NEW(BehaviorEvidence)
    _BEHAVIOR_EVIDENCE_INIT(
        evidence,
        similarity,
        matched_identity_probes,
        total_identity_probes,
        corrections_to_apply,
        corrections_to_skip,
        reasons,
        profile,
        observations,
        minimum_similarity,
    )
    return evidence


def _behavior_evidence_fields(
    evidence: BehaviorEvidence,
) -> tuple[
    float,
    int,
    int,
    tuple[str, ...],
    tuple[str, ...],
    BehaviorProfile,
    BehaviorObservations,
    float,
]:
    owner = BehaviorEvidence
    return (
        cast("float", _BEHAVIOR_SIMILARITY_SLOT.__get__(evidence, owner)),
        cast("int", _BEHAVIOR_MATCHED_SLOT.__get__(evidence, owner)),
        cast("int", _BEHAVIOR_TOTAL_SLOT.__get__(evidence, owner)),
        cast("tuple[str, ...]", _BEHAVIOR_APPLY_SLOT.__get__(evidence, owner)),
        cast("tuple[str, ...]", _BEHAVIOR_SKIP_SLOT.__get__(evidence, owner)),
        cast(
            "BehaviorProfile", _BEHAVIOR_PROFILE_SLOT.__get__(evidence, owner)
        ),
        cast(
            "BehaviorObservations",
            _BEHAVIOR_OBSERVATIONS_SLOT.__get__(evidence, owner),
        ),
        cast("float", _BEHAVIOR_MINIMUM_SLOT.__get__(evidence, owner)),
    )


def _validate_fraction(name: str, value: object) -> float:
    if _NATIVE_TYPE(value) is _NATIVE_INT:
        # Reject out-of-range integers before float conversion; arbitrary-sized
        # values can otherwise overflow or fail decimal diagnostic formatting.
        if _ZERO <= value <= _ONE:
            return _NATIVE_FLOAT(value)
    elif _NATIVE_TYPE(value) is _NATIVE_FLOAT:
        if _NATIVE_ISFINITE(value) and _ZERO <= value <= _ONE:
            return value
    else:
        message = f"{name} must be a finite numeric fraction in [0, 1]"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    message = f"{name} must be a finite fraction in [0, 1]"
    raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)


def _observation_map(
    observations: tuple[IdentityObservation, ...]
    | tuple[CompatibilityObservation, ...]
    | tuple[BugObservation, ...],
) -> dict[str, IdentityObservation | CompatibilityObservation | BugObservation]:
    identifiers = _NATIVE_TUPLE(
        _observation_identifier(item) for item in observations
    )
    if identifiers != _NATIVE_TUPLE(_NATIVE_SORTED(identifiers)) or _NATIVE_LEN(
        identifiers
    ) != _NATIVE_LEN(_NATIVE_SET(identifiers)):
        message = (
            "behavior observations must have unique sorted probe identifiers"
        )
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    return {_observation_identifier(item): item for item in observations}


def _require_observation_shape(
    expected_ids: tuple[str, ...],
    observed_ids: tuple[str, ...],
    kind: str,
) -> None:
    if expected_ids != observed_ids:
        message = (
            f"{kind} observation identifiers do not match behavior profile"
        )
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)


def _identity_evidence(
    profile: BehaviorProfile,
    observations: BehaviorObservations,
) -> tuple[int, tuple[str, ...]]:
    observed = _observation_map(_observations_fields(observations)[0])
    expected = _profile_fields(profile)[0]
    expected_ids = _NATIVE_TUPLE(_probe_identifier(item) for item in expected)
    _require_observation_shape(
        expected_ids, _NATIVE_TUPLE(observed), "identity"
    )
    matched = 0
    reasons: list[str] = []
    for probe in expected:
        observation = observed[_probe_identifier(probe)]
        if _NATIVE_TYPE(observation) is not IdentityObservation:
            message = "internal identity observation type mismatch"
            raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
        digest = cast(
            "bytes | None",
            _IDENTITY_OBSERVATION_DIGEST_SLOT.__get__(
                observation, IdentityObservation
            ),
        )
        if digest is None:
            reasons.append(
                f"identity probe unavailable: {_probe_identifier(probe)}"
            )
            continue
        matched += digest == cast(
            "bytes", _IDENTITY_PROBE_DIGEST_SLOT.__get__(probe, IdentityProbe)
        )
    return matched, _NATIVE_TUPLE(reasons)


def _compatibility_reasons(
    profile: BehaviorProfile,
    observations: BehaviorObservations,
) -> tuple[str, ...]:
    observed = _observation_map(_observations_fields(observations)[1])
    expected = _profile_fields(profile)[1]
    expected_ids = _NATIVE_TUPLE(_probe_identifier(item) for item in expected)
    _require_observation_shape(
        expected_ids, _NATIVE_TUPLE(observed), "compatibility"
    )
    reasons: list[str] = []
    for probe in expected:
        observation = observed[_probe_identifier(probe)]
        if _NATIVE_TYPE(observation) is not CompatibilityObservation:
            message = "internal compatibility observation type mismatch"
            raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
        if _COMPATIBILITY_OBSERVATION_VALUE_SLOT.__get__(
            observation, CompatibilityObservation
        ) is not True:
            reasons.append(
                f"compatibility probe failed: {_probe_identifier(probe)}"
            )
    return _NATIVE_TUPLE(reasons)


def _bug_routing(
    profile: BehaviorProfile,
    observations: BehaviorObservations,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    observed = _observation_map(_observations_fields(observations)[2])
    expected = _profile_fields(profile)[2]
    expected_ids = _NATIVE_TUPLE(_probe_identifier(item) for item in expected)
    _require_observation_shape(expected_ids, _NATIVE_TUPLE(observed), "bug")
    apply: list[str] = []
    skip: list[str] = []
    reasons: list[str] = []
    for probe in expected:
        observation = observed[_probe_identifier(probe)]
        if _NATIVE_TYPE(observation) is not BugObservation:
            message = "internal bug observation type mismatch"
            raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
        state = cast(
            "BugState",
            _BUG_OBSERVATION_STATE_SLOT.__get__(observation, BugObservation),
        )
        if state is BugState.PRESENT:
            apply.append(
                cast("str", _BUG_PROBE_CORRECTION_SLOT.__get__(probe, BugProbe))
            )
        elif state is BugState.FIXED:
            skip.append(
                cast("str", _BUG_PROBE_CORRECTION_SLOT.__get__(probe, BugProbe))
            )
        else:
            reasons.append(f"bug probe unresolved: {_probe_identifier(probe)}")
    return _NATIVE_TUPLE(apply), _NATIVE_TUPLE(skip), _NATIVE_TUPLE(reasons)


def _below_similarity_threshold(
    matched: int, total: int, minimum: float
) -> bool:
    """Compare exact probe counts to the configured decimal policy fraction."""
    # Rounded division may equal a threshold that is slightly above the true
    # ratio (for example 1/11). Interpret the input float's canonical decimal,
    # consistently with source-binding thresholds, without losing precision.
    numerator, denominator = _native_decimal(
        _NATIVE_STR(minimum)
    ).as_integer_ratio()
    return matched * denominator < total * numerator


def _behavior_decision(
    profile: BehaviorProfile,
    observations: BehaviorObservations,
    minimum_similarity: float,
) -> tuple[int, tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    matched, identity_reasons = _identity_evidence(profile, observations)
    reasons = _NATIVE_LIST(identity_reasons)
    if _below_similarity_threshold(
        matched, _NATIVE_LEN(_profile_fields(profile)[0]), minimum_similarity
    ):
        reasons.append("insufficient behavior identity similarity")
    reasons.extend(_compatibility_reasons(profile, observations))
    apply, skip, bug_reasons = _bug_routing(profile, observations)
    reasons.extend(bug_reasons)
    return matched, apply, skip, _NATIVE_TUPLE(reasons)


def _require_behavior_evidence_sources(
    profile: BehaviorProfile, observations: BehaviorObservations
) -> None:
    if _NATIVE_TYPE(profile) is not BehaviorProfile:
        message = "behavior evidence requires exact BehaviorProfile"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    if _NATIVE_TYPE(observations) is not BehaviorObservations:
        message = "behavior evidence requires exact BehaviorObservations"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    # Revalidate original, nested records even when a caller supplied a raw
    # exact outer profile/observation object that skipped its initializer.
    try:
        _BEHAVIOR_PROFILE_VALIDATOR(profile)
        _BEHAVIOR_OBSERVATIONS_VALIDATOR(observations)
    except (_NATIVE_ATTRIBUTE_ERROR, _NATIVE_TYPE_ERROR) as error:
        message = "behavior evidence has incomplete native source metadata"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message) from error


def _validate_behavior_evidence_binding(evidence: BehaviorEvidence) -> None:
    (
        _,
        matched_count,
        total_count,
        apply_values,
        skip_values,
        profile,
        observations,
        minimum_value,
    ) = _behavior_evidence_fields(evidence)
    _require_behavior_evidence_sources(profile, observations)
    minimum = _validate_fraction(
        "behavior evidence minimum_similarity", minimum_value
    )
    matched, apply, skip, reasons = _behavior_decision(
        profile, observations, minimum
    )
    if (
        matched != matched_count
        or _NATIVE_LEN(_profile_fields(profile)[0]) != total_count
    ):
        message = "behavior evidence probe counts do not match observations"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    if (apply, skip) != (apply_values, skip_values):
        message = (
            "behavior evidence correction routes do not match observations"
        )
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    if reasons != _BEHAVIOR_REASONS_SLOT.__get__(evidence, BehaviorEvidence):
        message = "behavior evidence reasons do not match observations"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)


def evaluate_behavior(
    profile: BehaviorProfile,
    observations: BehaviorObservations,
    minimum_similarity: float,
) -> BehaviorEvidence:
    """Evaluate mandatory identity, compatibility, and bug-probe semantics.

    Identity probes must all execute. Their matching results are aggregated
    against the configured similarity threshold. Compatibility probes must pass.
    Bug probes must classify a defect as present or already fixed; already-fixed
    bugs route their correction to ``skip`` rather than rejecting the source.

    Returns:
        Behavior evidence and deterministic correction-routing decisions.

    Raises:
        BehaviorPolicyError: Profile, observations, or threshold is invalid.

    """
    if _NATIVE_TYPE(profile) is not BehaviorProfile:
        message = "behavior profile must use the exact BehaviorProfile type"
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    if _NATIVE_TYPE(observations) is not BehaviorObservations:
        message = (
            "behavior observations must use the exact BehaviorObservations type"
        )
        raise _NATIVE_BEHAVIOR_POLICY_ERROR(message)
    _require_behavior_evidence_sources(profile, observations)
    validated_minimum = _validate_fraction(
        "minimum_similarity", minimum_similarity
    )
    matched, apply, skip, reasons = _behavior_decision(
        profile, observations, validated_minimum
    )
    total = _NATIVE_LEN(_profile_fields(profile)[0])
    return _new_behavior_evidence(
        similarity=matched / total,
        matched_identity_probes=matched,
        total_identity_probes=total,
        corrections_to_apply=apply,
        corrections_to_skip=skip,
        reasons=reasons,
        profile=profile,
        observations=observations,
        minimum_similarity=validated_minimum,
    )


def require_behavior(
    profile: BehaviorProfile,
    observations: BehaviorObservations,
    minimum_similarity: float,
) -> BehaviorEvidence:
    """Require behavior admission and return passing evidence.

    Returns:
        Passing behavior evidence with bug-correction routing.

    Raises:
        BehaviorAdmissionError: Mandatory behavior evidence rejects the
        candidate.

    """
    evidence = evaluate_behavior(profile, observations, minimum_similarity)
    reasons = cast(
        "tuple[str, ...]",
        _BEHAVIOR_REASONS_SLOT.__get__(evidence, BehaviorEvidence),
    )
    if reasons:
        message = "; ".join(reasons)
        raise _NATIVE_BEHAVIOR_ADMISSION_ERROR(message)
    return evidence
