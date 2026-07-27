# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Content-defined stable fingerprints for source-lineage evidence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

_DEFAULT_WINDOW_BYTES = 32
_DEFAULT_SELECTION_MODULUS = 64
_SELECTION_PREFIX_BYTES = 8
_ZERO = 0
_ONE = 1


class FingerprintPolicyError(ValueError):
    """Raised when stable-anchor policy is internally invalid."""


@dataclass(frozen=True, slots=True)
class AnchorPolicy:
    """Deterministic content-defined anchor selection policy."""

    window_bytes: int = _DEFAULT_WINDOW_BYTES
    selection_modulus: int = _DEFAULT_SELECTION_MODULUS

    def __post_init__(self) -> None:
        """Reject unusable anchor parameters.

        Raises:
            FingerprintPolicyError: A configured integer is not positive.

        """
        if self.window_bytes < _ONE or self.selection_modulus < _ONE:
            message = "anchor window and selection modulus must be positive"
            raise FingerprintPolicyError(message)


_DEFAULT_POLICY = AnchorPolicy()


@dataclass(frozen=True, slots=True, order=True)
class StableAnchor:
    """One selected source-content fingerprint and its authoring offset."""

    digest: bytes
    offset: int


@dataclass(frozen=True, slots=True)
class AnchorCoverage:
    """Measured overlap between reference and candidate stable anchors."""

    matched: int
    total: int
    ratio: float


def _digest_window(window: bytes) -> bytes:
    return hashlib.sha256(window).digest()


def _is_selected(digest: bytes, policy: AnchorPolicy) -> bool:
    prefix = digest[:_SELECTION_PREFIX_BYTES]
    value = int.from_bytes(prefix, byteorder="big", signed=False)
    return value % policy.selection_modulus == _ZERO


def _small_input_anchor(data: bytes) -> tuple[StableAnchor, ...]:
    if not data:
        return ()
    return (StableAnchor(digest=_digest_window(data), offset=_ZERO),)


def _scan_anchor_windows(
    data: bytes,
    policy: AnchorPolicy,
) -> tuple[dict[bytes, StableAnchor], StableAnchor]:
    last_offset = len(data) - policy.window_bytes
    selected: dict[bytes, StableAnchor] = {}
    first_digest = _digest_window(data[: policy.window_bytes])
    fallback = StableAnchor(digest=first_digest, offset=_ZERO)
    for offset in range(last_offset + _ONE):
        digest = _digest_window(data[offset : offset + policy.window_bytes])
        anchor = StableAnchor(digest=digest, offset=offset)
        if digest < fallback.digest:
            fallback = anchor
        if _is_selected(digest, policy):
            selected.setdefault(digest, anchor)
    return selected, fallback


def stable_anchors(
    data: bytes,
    policy: AnchorPolicy = _DEFAULT_POLICY,
) -> tuple[StableAnchor, ...]:
    """Select deterministic anchors from sliding content windows.

    Every byte offset is considered, so an insertion changes offsets but leaves
    unchanged content windows eligible for the same anchor digest. Selection is
    based only on the digest value. If no window passes the sampling predicate,
    the lexicographically smallest digest is retained as a deterministic
    fallback.

    Returns:
        Unique selected digests ordered by authoring offset.

    """
    if len(data) < policy.window_bytes:
        return _small_input_anchor(data)
    selected, fallback = _scan_anchor_windows(data, policy)
    if not selected:
        selected[fallback.digest] = fallback
    return tuple(sorted(selected.values(), key=lambda anchor: anchor.offset))


def anchor_coverage(
    reference: tuple[StableAnchor, ...],
    candidate: tuple[StableAnchor, ...],
) -> AnchorCoverage:
    """Measure how many unique reference anchor digests survive in a candidate.

    Returns:
        Matched count, reference count, and matched/reference ratio.

    """
    reference_digests = {anchor.digest for anchor in reference}
    candidate_digests = {anchor.digest for anchor in candidate}
    total = len(reference_digests)
    if total == _ZERO:
        return AnchorCoverage(matched=_ZERO, total=_ZERO, ratio=1.0)
    matched = len(reference_digests & candidate_digests)
    return AnchorCoverage(
        matched=matched,
        total=total,
        ratio=matched / total,
    )
