# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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

from dataclasses import dataclass
from enum import StrEnum
import math
from typing import cast

_ZERO = 0
_ONE = 1


class BehaviorPolicyError(ValueError):
    """Raised when behavior profile or observation shape is invalid."""


class BehaviorAdmissionError(RuntimeError):
    """Raised when mandatory behavior evidence does not admit a candidate."""


class BugState(StrEnum):
    """Observed candidate state for one known historical defect."""

    PRESENT = "present"
    FIXED = "fixed"
    UNKNOWN = "unknown"


def _require_identifier(value: object, context: str) -> str:
    if type(value) is not str or not value:
        message = f"{context} must be a non-empty string"
        raise BehaviorPolicyError(message)
    return value


def _require_digest(value: object, context: str) -> bytes:
    if type(value) is not bytes or not value:
        message = f"{context} must be non-empty exact bytes"
        raise BehaviorPolicyError(message)
    return value


@dataclass(frozen=True, slots=True, order=True)
class IdentityProbe:
    """Stable historical behavior fingerprint expected from source lineage."""

    probe_id: str
    expected_digest: bytes

    def __post_init__(self) -> None:
        """Require canonical probe identity and exact fingerprint bytes."""
        _ = _require_identifier(self.probe_id, "identity probe ID")
        _ = _require_digest(self.expected_digest, "identity probe digest")


@dataclass(frozen=True, slots=True, order=True)
class CompatibilityProbe:
    """Named runtime/build precondition required before transformation."""

    probe_id: str

    def __post_init__(self) -> None:
        """Require one canonical compatibility probe identity."""
        _ = _require_identifier(self.probe_id, "compatibility probe ID")


@dataclass(frozen=True, slots=True, order=True)
class BugProbe:
    """Known defect whose correction can be skipped when already fixed."""

    probe_id: str
    correction_id: str

    def __post_init__(self) -> None:
        """Require canonical bug and correction identities."""
        _ = _require_identifier(self.probe_id, "bug probe ID")
        _ = _require_identifier(self.correction_id, "bug correction ID")


def _probe_ids(
    probes: tuple[IdentityProbe, ...]
    | tuple[CompatibilityProbe, ...]
    | tuple[BugProbe, ...],
) -> tuple[str, ...]:
    identifiers = tuple(item.probe_id for item in probes)
    if any(not identifier for identifier in identifiers):
        message = "behavior probe identifiers must be non-empty"
        raise BehaviorPolicyError(message)
    if identifiers != tuple(sorted(identifiers)):
        message = "behavior probes must be sorted by probe_id"
        raise BehaviorPolicyError(message)
    return identifiers


def _validate_unique(values: tuple[str, ...], message: str) -> None:
    if len(values) != len(set(values)):
        raise BehaviorPolicyError(message)


def _validate_correction_ids(bugs: tuple[BugProbe, ...]) -> None:
    correction_ids = tuple(item.correction_id for item in bugs)
    if any(not correction_id for correction_id in correction_ids):
        message = "bug probes require non-empty correction identifiers"
        raise BehaviorPolicyError(message)
    _validate_unique(
        correction_ids, "bug correction identifiers must be unique"
    )


def _require_probe_tuple(
    value: object,
    item_type: type[IdentityProbe | CompatibilityProbe | BugProbe],
    context: str,
) -> None:
    if type(value) is not tuple:
        message = f"{context} must use the exact immutable tuple type"
        raise BehaviorPolicyError(message)
    items = cast("tuple[object, ...]", value)
    if any(type(item) is not item_type for item in items):
        message = f"{context} contains a foreign probe record"
        raise BehaviorPolicyError(message)


@dataclass(frozen=True, slots=True)
class BehaviorProfile:
    """Behavior expectations generated from the authoring source."""

    identity: tuple[IdentityProbe, ...]
    compatibility: tuple[CompatibilityProbe, ...]
    bugs: tuple[BugProbe, ...]

    def __post_init__(self) -> None:
        """Require deterministic unique probe identifiers.

        Raises:
            BehaviorPolicyError: Probe identifiers violate profile policy.

        """
        _require_probe_tuple(self.identity, IdentityProbe, "identity probes")
        _require_probe_tuple(
            self.compatibility,
            CompatibilityProbe,
            "compatibility probes",
        )
        _require_probe_tuple(self.bugs, BugProbe, "bug probes")
        if not self.identity:
            message = "behavior profile requires at least one identity probe"
            raise BehaviorPolicyError(message)
        groups = (
            _probe_ids(self.identity),
            _probe_ids(self.compatibility),
            _probe_ids(self.bugs),
        )
        all_ids = tuple(identifier for group in groups for identifier in group)
        _validate_unique(
            all_ids, "behavior probe identifiers must be globally unique"
        )
        _validate_correction_ids(self.bugs)


@dataclass(frozen=True, slots=True, order=True)
class IdentityObservation:
    """Candidate identity-probe result; ``None`` means execution unavailable."""

    probe_id: str
    digest: bytes | None

    def __post_init__(self) -> None:
        """Require canonical identity evidence or explicit unavailability."""
        _ = _require_identifier(self.probe_id, "identity observation ID")
        if self.digest is not None:
            _ = _require_digest(self.digest, "identity observation digest")


@dataclass(frozen=True, slots=True, order=True)
class CompatibilityObservation:
    """Candidate precondition result; ``None`` means execution unavailable."""

    probe_id: str
    compatible: bool | None

    def __post_init__(self) -> None:
        """Require canonical identity and exact tri-state compatibility.

        Raises:
            BehaviorPolicyError: Identity or compatibility metadata is invalid.

        """
        _ = _require_identifier(self.probe_id, "compatibility observation ID")
        if self.compatible is not None and type(self.compatible) is not bool:
            message = "compatibility observation must be bool or None"
            raise BehaviorPolicyError(message)


@dataclass(frozen=True, slots=True, order=True)
class BugObservation:
    """Candidate classification for one known historical defect."""

    probe_id: str
    state: BugState

    def __post_init__(self) -> None:
        """Require canonical identity and exact bug-state enum metadata.

        Raises:
            BehaviorPolicyError: Identity or bug-state metadata is invalid.

        """
        _ = _require_identifier(self.probe_id, "bug observation ID")
        if type(self.state) is not BugState:
            message = "bug observation state must use the exact BugState type"
            raise BehaviorPolicyError(message)


def _require_observation_tuple(
    value: object,
    item_type: (
        type[IdentityObservation | CompatibilityObservation | BugObservation]
    ),
    context: str,
) -> None:
    if type(value) is not tuple:
        message = f"{context} must use the exact immutable tuple type"
        raise BehaviorPolicyError(message)
    items = cast("tuple[object, ...]", value)
    if any(type(item) is not item_type for item in items):
        message = f"{context} contains a foreign observation record"
        raise BehaviorPolicyError(message)


@dataclass(frozen=True, slots=True)
class BehaviorObservations:
    """All candidate probe results for one deterministic evaluation."""

    identity: tuple[IdentityObservation, ...]
    compatibility: tuple[CompatibilityObservation, ...]
    bugs: tuple[BugObservation, ...]

    def __post_init__(self) -> None:
        """Require immutable exact observation records for every category."""
        _require_observation_tuple(
            self.identity, IdentityObservation, "identity observations"
        )
        _require_observation_tuple(
            self.compatibility,
            CompatibilityObservation,
            "compatibility observations",
        )
        _require_observation_tuple(
            self.bugs, BugObservation, "bug observations"
        )


def _require_evidence_similarity(value: object) -> float:
    if type(value) is not float or not math.isfinite(value):
        message = "behavior evidence similarity must use a finite exact float"
        raise BehaviorPolicyError(message)
    if value < _ZERO or value > _ONE:
        message = "behavior evidence similarity must be in [0, 1]"
        raise BehaviorPolicyError(message)
    return value


def _require_evidence_count(value: object, context: str, minimum: int) -> int:
    if type(value) is not int or value < minimum:
        message = f"{context} must use an exact integer >= {minimum}"
        raise BehaviorPolicyError(message)
    return value


def _require_string_tuple(value: object, context: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        message = f"{context} must use the exact immutable tuple type"
        raise BehaviorPolicyError(message)
    items = cast("tuple[object, ...]", value)
    if any(type(item) is not str or not item for item in items):
        message = f"{context} must contain non-empty exact strings"
        raise BehaviorPolicyError(message)
    return cast("tuple[str, ...]", value)


def _validate_behavior_evidence(evidence: BehaviorEvidence) -> None:
    similarity = _require_evidence_similarity(evidence.similarity)
    matched = _require_evidence_count(
        evidence.matched_identity_probes,
        "matched identity probe count",
        _ZERO,
    )
    total = _require_evidence_count(
        evidence.total_identity_probes,
        "total identity probe count",
        _ONE,
    )
    if matched > total:
        message = "matched identity probe count cannot exceed total"
        raise BehaviorPolicyError(message)
    if similarity != matched / total:
        message = "behavior evidence similarity does not match probe counts"
        raise BehaviorPolicyError(message)
    apply = _require_string_tuple(
        evidence.corrections_to_apply,
        "corrections to apply",
    )
    skip = _require_string_tuple(
        evidence.corrections_to_skip,
        "corrections to skip",
    )
    if len(apply) != len(set(apply)) or len(skip) != len(set(skip)):
        message = "behavior correction routes must not contain duplicates"
        raise BehaviorPolicyError(message)
    if set(apply) & set(skip):
        message = "behavior correction routes must be disjoint"
        raise BehaviorPolicyError(message)
    _ = _require_string_tuple(evidence.reasons, "behavior evidence reasons")


@dataclass(frozen=True, slots=True)
class BehaviorEvidence:
    """Aggregated behavior admission plus bug-correction routing."""

    similarity: float
    matched_identity_probes: int
    total_identity_probes: int
    corrections_to_apply: tuple[str, ...]
    corrections_to_skip: tuple[str, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        """Require internally coherent aggregated behavior evidence."""
        _validate_behavior_evidence(self)

    @property
    def admitted(self) -> bool:
        """Whether all mandatory behavior requirements passed.

        Returns:
            True exactly when no deterministic rejection reason exists.

        """
        return not self.reasons


def _validate_fraction(name: str, value: object) -> float:
    if type(value) is int:
        number = float(value)
    elif type(value) is float:
        number = value
    else:
        message = f"{name} must be a finite numeric fraction in [0, 1]"
        raise BehaviorPolicyError(message)
    if not math.isfinite(number) or number < _ZERO or number > _ONE:
        message = f"{name} must be a finite fraction in [0, 1], got {value}"
        raise BehaviorPolicyError(message)
    return number


def _observation_map(
    observations: tuple[IdentityObservation, ...]
    | tuple[CompatibilityObservation, ...]
    | tuple[BugObservation, ...],
) -> dict[str, IdentityObservation | CompatibilityObservation | BugObservation]:
    identifiers = tuple(item.probe_id for item in observations)
    if identifiers != tuple(sorted(identifiers)) or len(identifiers) != len(
        set(identifiers)
    ):
        message = (
            "behavior observations must have unique sorted probe identifiers"
        )
        raise BehaviorPolicyError(message)
    return {item.probe_id: item for item in observations}


def _require_observation_shape(
    expected_ids: tuple[str, ...],
    observed_ids: tuple[str, ...],
    kind: str,
) -> None:
    if expected_ids != observed_ids:
        message = (
            f"{kind} observation identifiers do not match behavior profile"
        )
        raise BehaviorPolicyError(message)


def _identity_evidence(
    profile: BehaviorProfile,
    observations: BehaviorObservations,
) -> tuple[int, tuple[str, ...]]:
    observed = _observation_map(observations.identity)
    expected_ids = tuple(item.probe_id for item in profile.identity)
    _require_observation_shape(expected_ids, tuple(observed), "identity")
    matched = 0
    reasons: list[str] = []
    for probe in profile.identity:
        observation = observed[probe.probe_id]
        if not isinstance(observation, IdentityObservation):
            message = "internal identity observation type mismatch"
            raise BehaviorPolicyError(message)
        if observation.digest is None:
            reasons.append(f"identity probe unavailable: {probe.probe_id}")
            continue
        matched += observation.digest == probe.expected_digest
    return matched, tuple(reasons)


def _compatibility_reasons(
    profile: BehaviorProfile,
    observations: BehaviorObservations,
) -> tuple[str, ...]:
    observed = _observation_map(observations.compatibility)
    expected_ids = tuple(item.probe_id for item in profile.compatibility)
    _require_observation_shape(expected_ids, tuple(observed), "compatibility")
    reasons: list[str] = []
    for probe in profile.compatibility:
        observation = observed[probe.probe_id]
        if not isinstance(observation, CompatibilityObservation):
            message = "internal compatibility observation type mismatch"
            raise BehaviorPolicyError(message)
        if observation.compatible is not True:
            reasons.append(f"compatibility probe failed: {probe.probe_id}")
    return tuple(reasons)


def _bug_routing(
    profile: BehaviorProfile,
    observations: BehaviorObservations,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    observed = _observation_map(observations.bugs)
    expected_ids = tuple(item.probe_id for item in profile.bugs)
    _require_observation_shape(expected_ids, tuple(observed), "bug")
    apply: list[str] = []
    skip: list[str] = []
    reasons: list[str] = []
    for probe in profile.bugs:
        observation = observed[probe.probe_id]
        if not isinstance(observation, BugObservation):
            message = "internal bug observation type mismatch"
            raise BehaviorPolicyError(message)
        if observation.state is BugState.PRESENT:
            apply.append(probe.correction_id)
        elif observation.state is BugState.FIXED:
            skip.append(probe.correction_id)
        else:
            reasons.append(f"bug probe unresolved: {probe.probe_id}")
    return tuple(apply), tuple(skip), tuple(reasons)


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
    if type(profile) is not BehaviorProfile:
        message = "behavior profile must use the exact BehaviorProfile type"
        raise BehaviorPolicyError(message)
    if type(observations) is not BehaviorObservations:
        message = (
            "behavior observations must use the exact BehaviorObservations type"
        )
        raise BehaviorPolicyError(message)
    validated_minimum = _validate_fraction(
        "minimum_similarity", minimum_similarity
    )
    matched, identity_reasons = _identity_evidence(profile, observations)
    total = len(profile.identity)
    similarity = matched / total
    reasons = list(identity_reasons)
    if similarity < validated_minimum:
        reasons.append("insufficient behavior identity similarity")
    reasons.extend(_compatibility_reasons(profile, observations))
    apply, skip, bug_reasons = _bug_routing(profile, observations)
    reasons.extend(bug_reasons)
    return BehaviorEvidence(
        similarity=similarity,
        matched_identity_probes=matched,
        total_identity_probes=total,
        corrections_to_apply=apply,
        corrections_to_skip=skip,
        reasons=tuple(reasons),
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
    if not evidence.admitted:
        message = "; ".join(evidence.reasons)
        raise BehaviorAdmissionError(message)
    return evidence
