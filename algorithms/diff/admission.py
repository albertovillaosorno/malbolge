# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Tree-level structural and stable-anchor source admission."""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.fingerprints import anchor_coverage
from algorithms.diff.fingerprints import stable_anchors

if TYPE_CHECKING:
    from algorithms.diff.fingerprints import StableAnchor

_BACKSLASH = "\\"
_DOT = "."
_PARENT = ".."
_ZERO = 0
_ONE = 1
_STRUCTURAL_POLICY = AnchorPolicy(window_bytes=16, selection_modulus=8)
_ANCHOR_POLICY = AnchorPolicy(window_bytes=32, selection_modulus=64)


class AdmissionPolicyError(ValueError):
    """Raised when tree admission policy is internally invalid."""


class AdmissionError(RuntimeError):
    """Raised when candidate source evidence does not satisfy admission."""


@dataclass(frozen=True, slots=True, order=True)
class IdentityFile:
    """One consumer-canonicalized file admitted to source identity."""

    path: str
    canonical: bytes

    def __post_init__(self) -> None:
        """Require one normalized portable relative file path.

        Raises:
            AdmissionPolicyError: The identity path is unsafe or non-canonical.

        """
        candidate = PurePosixPath(self.path)
        unsafe = (
            not self.path
            or _BACKSLASH in self.path
            or self.path == _DOT
            or candidate.is_absolute()
            or _PARENT in candidate.parts
        )
        if unsafe or candidate.as_posix() != self.path:
            message = f"invalid identity path: {self.path!r}"
            raise AdmissionPolicyError(message)


@dataclass(frozen=True, slots=True)
class IdentityTree:
    """Explicit set of consumer-selected files participating in identity."""

    files: tuple[IdentityFile, ...]

    def __post_init__(self) -> None:
        """Require sorted unique paths for deterministic evidence.

        Raises:
            AdmissionPolicyError: Files are duplicated or out of order.

        """
        paths = tuple(item.path for item in self.files)
        if paths != tuple(sorted(set(paths))):
            message = "identity tree paths must be unique and sorted"
            raise AdmissionPolicyError(message)


@dataclass(frozen=True, slots=True)
class AdmissionPolicy:
    """Thresholds and distribution requirements for source admission."""

    minimum_source_similarity: float
    minimum_anchor_coverage: float
    minimum_anchor_files: int
    minimum_anchors_per_file: int
    structural_policy: AnchorPolicy = _STRUCTURAL_POLICY
    anchor_policy: AnchorPolicy = _ANCHOR_POLICY

    def __post_init__(self) -> None:
        """Validate threshold and positive-count requirements.

        Raises:
            AdmissionPolicyError: A threshold or evidence count is invalid.

        """
        _validate_fraction(
            "minimum_source_similarity", self.minimum_source_similarity
        )
        _validate_fraction(
            "minimum_anchor_coverage", self.minimum_anchor_coverage
        )
        if self.minimum_anchor_files < _ONE:
            message = "minimum_anchor_files must be positive"
            raise AdmissionPolicyError(message)
        if self.minimum_anchors_per_file < _ONE:
            message = "minimum_anchors_per_file must be positive"
            raise AdmissionPolicyError(message)


@dataclass(frozen=True, slots=True)
class FileAdmissionEvidence:
    """Structural and anchor evidence for one reference identity file."""

    path: str
    structural_similarity: float
    anchor_coverage: float | None
    reference_anchor_count: int
    matched_anchor_count: int


@dataclass(frozen=True, slots=True)
class TreeAdmissionEvidence:
    """Aggregated source-lineage evidence with deterministic failure reasons."""

    source_similarity: float
    anchor_coverage: float
    eligible_anchor_files: int
    satisfied_anchor_files: int
    files: tuple[FileAdmissionEvidence, ...]
    reasons: tuple[str, ...]

    @property
    def admitted(self) -> bool:
        """Whether every source-lineage requirement passed.

        Returns:
            True exactly when no deterministic rejection reason exists.

        """
        return not self.reasons


def identity_tree(files: dict[str, bytes]) -> IdentityTree:
    """Build a sorted explicit identity tree from consumer-canonicalized bytes.

    Returns:
        A deterministic identity tree.

    """
    records = tuple(
        IdentityFile(path=path, canonical=canonical)
        for path, canonical in sorted(files.items())
    )
    return IdentityTree(files=records)


def _validate_fraction(name: str, value: float) -> None:
    if not math.isfinite(value) or value < _ZERO or value > _ONE:
        message = f"{name} must be a finite fraction in [0, 1], got {value}"
        raise AdmissionPolicyError(message)


def _digest_set(anchors: tuple[StableAnchor, ...]) -> frozenset[bytes]:
    return frozenset(anchor.digest for anchor in anchors)


def _structural_similarity(
    reference: bytes,
    candidate: bytes,
    policy: AnchorPolicy,
) -> float:
    if reference == candidate:
        return 1.0
    reference_digests = _digest_set(stable_anchors(reference, policy))
    candidate_digests = _digest_set(stable_anchors(candidate, policy))
    if not reference_digests or not candidate_digests:
        return 0.0
    intersection = len(reference_digests & candidate_digests)
    return (
        2.0 * intersection / (len(reference_digests) + len(candidate_digests))
    )


def _file_evidence(
    reference: IdentityFile,
    candidate: IdentityFile | None,
    policy: AdmissionPolicy,
) -> FileAdmissionEvidence:
    candidate_bytes = b"" if candidate is None else candidate.canonical
    structural = _structural_similarity(
        reference.canonical,
        candidate_bytes,
        policy.structural_policy,
    )
    reference_anchors = stable_anchors(
        reference.canonical, policy.anchor_policy
    )
    candidate_anchors = stable_anchors(candidate_bytes, policy.anchor_policy)
    coverage = anchor_coverage(reference_anchors, candidate_anchors)
    eligible = coverage.total >= policy.minimum_anchors_per_file
    return FileAdmissionEvidence(
        path=reference.path,
        structural_similarity=structural,
        anchor_coverage=coverage.ratio if eligible else None,
        reference_anchor_count=coverage.total,
        matched_anchor_count=coverage.matched,
    )


def _mean(values: tuple[float, ...]) -> float:
    if not values:
        return 0.0
    return math.fsum(values) / len(values)


@dataclass(frozen=True, slots=True)
class _AggregateEvidence:
    source_similarity: float
    anchor_average: float
    eligible_files: int
    satisfied_files: int


def _reason_tuple(
    aggregate: _AggregateEvidence,
    policy: AdmissionPolicy,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if aggregate.source_similarity < policy.minimum_source_similarity:
        reasons.append("insufficient structural source similarity")
    if aggregate.anchor_average < policy.minimum_anchor_coverage:
        reasons.append("insufficient stable-anchor coverage")
    if aggregate.eligible_files < policy.minimum_anchor_files:
        reasons.append("insufficient files with anchor evidence")
    if aggregate.satisfied_files < policy.minimum_anchor_files:
        reasons.append("stable-anchor evidence is not sufficiently distributed")
    return tuple(reasons)


def evaluate_admission(
    reference: IdentityTree,
    candidate: IdentityTree,
    policy: AdmissionPolicy,
) -> TreeAdmissionEvidence:
    """Evaluate structural and distributed-anchor source lineage.

    Every reference file receives equal weight. Consumers choose which files
    belong to identity before calling this function, so opaque assets cannot
    gain influence merely by being large.

    Returns:
        Deterministic per-file and aggregate admission evidence.

    Raises:
        AdmissionError: The reference identity tree is empty.

    """
    if not reference.files:
        message = "reference identity tree contains no source evidence"
        raise AdmissionError(message)
    candidate_by_path = {item.path: item for item in candidate.files}
    files = tuple(
        _file_evidence(item, candidate_by_path.get(item.path), policy)
        for item in reference.files
    )
    source_similarity = _mean(
        tuple(item.structural_similarity for item in files)
    )
    eligible = tuple(item for item in files if item.anchor_coverage is not None)
    anchor_average = _mean(
        tuple(item.anchor_coverage or 0.0 for item in eligible)
    )
    satisfied = sum(
        item.matched_anchor_count > _ZERO
        and (item.anchor_coverage or 0.0) >= policy.minimum_anchor_coverage
        for item in eligible
    )
    aggregate = _AggregateEvidence(
        source_similarity=source_similarity,
        anchor_average=anchor_average,
        eligible_files=len(eligible),
        satisfied_files=satisfied,
    )
    reasons = _reason_tuple(aggregate, policy)
    return TreeAdmissionEvidence(
        source_similarity=source_similarity,
        anchor_coverage=anchor_average,
        eligible_anchor_files=len(eligible),
        satisfied_anchor_files=satisfied,
        files=files,
        reasons=reasons,
    )


def require_admission(
    reference: IdentityTree,
    candidate: IdentityTree,
    policy: AdmissionPolicy,
) -> TreeAdmissionEvidence:
    """Require tree admission and return its evidence.

    Returns:
        Passing deterministic source-lineage evidence.

    Raises:
        AdmissionError: Candidate source lineage is insufficient.

    """
    evidence = evaluate_admission(reference, candidate, policy)
    if not evidence.admitted:
        message = "; ".join(evidence.reasons)
        raise AdmissionError(message)
    return evidence
