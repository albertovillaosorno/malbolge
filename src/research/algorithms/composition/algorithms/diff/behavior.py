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


@dataclass(frozen=True, slots=True, order=True)
class IdentityProbe:
    """Stable historical behavior fingerprint expected from source lineage."""

    probe_id: str
    expected_digest: bytes


@dataclass(frozen=True, slots=True, order=True)
class CompatibilityProbe:
    """Named runtime/build precondition required before transformation."""

    probe_id: str


@dataclass(frozen=True, slots=True, order=True)
class BugProbe:
    """Known defect whose correction can be skipped when already fixed."""

    probe_id: str
    correction_id: str


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


@dataclass(frozen=True, slots=True, order=True)
class CompatibilityObservation:
    """Candidate precondition result; ``None`` means execution unavailable."""

    probe_id: str
    compatible: bool | None


@dataclass(frozen=True, slots=True, order=True)
class BugObservation:
    """Candidate classification for one known historical defect."""

    probe_id: str
    state: BugState


@dataclass(frozen=True, slots=True)
class BehaviorObservations:
    """All candidate probe results for one deterministic evaluation."""

    identity: tuple[IdentityObservation, ...]
    compatibility: tuple[CompatibilityObservation, ...]
    bugs: tuple[BugObservation, ...]


@dataclass(frozen=True, slots=True)
class BehaviorEvidence:
    """Aggregated behavior admission plus bug-correction routing."""

    similarity: float
    matched_identity_probes: int
    total_identity_probes: int
    corrections_to_apply: tuple[str, ...]
    corrections_to_skip: tuple[str, ...]
    reasons: tuple[str, ...]

    @property
    def admitted(self) -> bool:
        """Whether all mandatory behavior requirements passed.

        Returns:
            True exactly when no deterministic rejection reason exists.

        """
        return not self.reasons


def _validate_fraction(name: str, value: float) -> None:
    if not math.isfinite(value) or value < _ZERO or value > _ONE:
        message = f"{name} must be a finite fraction in [0, 1], got {value}"
        raise BehaviorPolicyError(message)


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

    """
    _validate_fraction("minimum_similarity", minimum_similarity)
    matched, identity_reasons = _identity_evidence(profile, observations)
    total = len(profile.identity)
    similarity = matched / total
    reasons = list(identity_reasons)
    if similarity < minimum_similarity:
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
