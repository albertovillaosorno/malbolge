# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
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
#   - Content-defined stable fingerprints for source-lineage evidence.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Content-defined stable fingerprints for source-lineage evidence."""

from __future__ import annotations

import builtins
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from types import MemberDescriptorType
from typing import cast

_DEFAULT_WINDOW_BYTES = 32
_DEFAULT_SELECTION_MODULUS = 64
_ROLLING_BASE = 257
_ROLLING_BITS = 64
_ROLLING_MODULUS = 1 << _ROLLING_BITS
_ROLLING_MASK = _ROLLING_MODULUS - 1
_ZERO = 0
_ONE = 1
# A mutable module-level hashlib symbol must not redefine lineage evidence.
_SHA256_FACTORY = hashlib.sha256
_SHA256_BYTES = _SHA256_FACTORY().digest_size
_NATIVE_POW = builtins.pow
_NATIVE_ATTRIBUTE_ERROR = builtins.AttributeError
_NATIVE_SORTED = builtins.sorted
_NATIVE_TYPE = builtins.type
_NATIVE_INT = builtins.int
_NATIVE_FLOAT = builtins.float
_NATIVE_BYTES = builtins.bytes
_NATIVE_LEN = len
_NATIVE_RANGE = range
_NATIVE_TUPLE = tuple
_NATIVE_OBJECT_NEW = object.__new__


class FingerprintPolicyError(ValueError):
    """Raised when stable-anchor policy is internally invalid."""


# Consumer imports may rebind the exported name after native policy creation.
_NATIVE_FINGERPRINT_POLICY_ERROR = FingerprintPolicyError


@dataclass(frozen=True, slots=True, init=False)
class AnchorPolicy:
    """Deterministic content-defined anchor selection policy."""

    window_bytes: int = _DEFAULT_WINDOW_BYTES
    selection_modulus: int = _DEFAULT_SELECTION_MODULUS

    def __init__(
        self,
        window_bytes: int = _DEFAULT_WINDOW_BYTES,
        selection_modulus: int = _DEFAULT_SELECTION_MODULUS,
    ) -> None:
        """Validate anchor parameters with the captured original guard."""
        _POLICY_WINDOW_SLOT.__set__(self, window_bytes)
        _POLICY_MODULUS_SLOT.__set__(self, selection_modulus)
        _ANCHOR_POLICY_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject unusable anchor parameters.

        Raises:
            FingerprintPolicyError: A configured integer is not positive.

        """
        window_bytes, selection_modulus = _policy_fields(self)
        if (
            _NATIVE_TYPE(window_bytes) is not _NATIVE_INT
            or _NATIVE_TYPE(selection_modulus) is not _NATIVE_INT
        ):
            message = "anchor window and selection modulus must be integers"
            raise _NATIVE_FINGERPRINT_POLICY_ERROR(message)
        if window_bytes < _ONE or selection_modulus < _ONE:
            message = (
                "anchor window and selection modulus must be positive integers"
            )
            raise _NATIVE_FINGERPRINT_POLICY_ERROR(message)


# Generated dataclass constructors resolve class validators late. Pin the
# originals so consumer hooks cannot suppress or forge evidence admission.
_ANCHOR_POLICY_VALIDATOR = cast(
    "Callable[[AnchorPolicy], None]", AnchorPolicy.__dict__["__post_init__"]
)

# Preserve original slotted storage access across consumer-controlled hooks.
_POLICY_WINDOW_SLOT = cast(
    "MemberDescriptorType", AnchorPolicy.__dict__["window_bytes"]
)
_POLICY_MODULUS_SLOT = cast(
    "MemberDescriptorType", AnchorPolicy.__dict__["selection_modulus"]
)


def _policy_fields(policy: AnchorPolicy) -> tuple[int, int]:
    return (
        _POLICY_WINDOW_SLOT.__get__(policy, AnchorPolicy),
        _POLICY_MODULUS_SLOT.__get__(policy, AnchorPolicy),
    )


_DEFAULT_POLICY = AnchorPolicy()


@dataclass(frozen=True, slots=True, order=True, init=False)
class StableAnchor:
    """One selected source-content fingerprint and its authoring offset."""

    digest: bytes
    offset: int

    def __init__(self, digest: bytes, offset: int) -> None:
        """Validate source digest and offset with the original guard."""
        _ANCHOR_DIGEST_SLOT.__set__(self, digest)
        _ANCHOR_OFFSET_SLOT.__set__(self, offset)
        _STABLE_ANCHOR_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require one exact SHA-256 digest and non-negative byte offset.

        Raises:
            FingerprintPolicyError: Digest or offset metadata is invalid.

        """
        digest, offset = _anchor_fields(self)
        native_bytes = _NATIVE_TYPE(digest) is _NATIVE_BYTES
        if not native_bytes or _NATIVE_LEN(digest) != _SHA256_BYTES:
            message = "stable anchor digest must be exactly 32 bytes"
            raise _NATIVE_FINGERPRINT_POLICY_ERROR(message)
        if _NATIVE_TYPE(offset) is not _NATIVE_INT or offset < _ZERO:
            message = "stable anchor offset must be a non-negative integer"
            raise _NATIVE_FINGERPRINT_POLICY_ERROR(message)


_STABLE_ANCHOR_VALIDATOR = cast(
    "Callable[[StableAnchor], None]", StableAnchor.__dict__["__post_init__"]
)

_ANCHOR_DIGEST_SLOT = cast(
    "MemberDescriptorType", StableAnchor.__dict__["digest"]
)
_ANCHOR_OFFSET_SLOT = cast(
    "MemberDescriptorType", StableAnchor.__dict__["offset"]
)
_ANCHOR_INIT = cast(
    "Callable[[StableAnchor, bytes, int], None]", StableAnchor.__dict__["__init__"]
)


def _anchor_fields(anchor: StableAnchor) -> tuple[bytes, int]:
    return (
        _ANCHOR_DIGEST_SLOT.__get__(anchor, StableAnchor),
        _ANCHOR_OFFSET_SLOT.__get__(anchor, StableAnchor),
    )


def _require_coverage_count(value: object, context: str) -> int:
    if _NATIVE_TYPE(value) is not _NATIVE_INT or value < _ZERO:
        message = f"{context} must be a non-negative integer"
        raise _NATIVE_FINGERPRINT_POLICY_ERROR(message)
    return value


def _require_coverage_ratio(value: object) -> float:
    if _NATIVE_TYPE(value) is not _NATIVE_FLOAT or not 0.0 <= value <= 1.0:
        message = "anchor coverage ratio must be an exact float in [0, 1]"
        raise _NATIVE_FINGERPRINT_POLICY_ERROR(message)
    return value


def _validate_anchor_coverage(coverage: AnchorCoverage) -> None:
    matched_value, total_value, ratio_value = _coverage_fields(coverage)
    matched = _require_coverage_count(
        matched_value,
        "matched anchor coverage",
    )
    total = _require_coverage_count(
        total_value,
        "total anchor coverage",
    )
    if matched > total:
        message = "matched anchor coverage cannot exceed total anchors"
        raise _NATIVE_FINGERPRINT_POLICY_ERROR(message)
    ratio = _require_coverage_ratio(ratio_value)
    expected = 1.0 if total == _ZERO else matched / total
    # Float rounding can conceal a nonempty difference at the endpoints:
    # 2**54 / (2**54 + 1) rounds to 1.0, and tiny positive ratios to 0.0.
    # Do not let those rounded values masquerade as complete/zero coverage.
    if (
        ratio != expected
        or (ratio == 1.0 and matched != total)
        or (ratio == 0.0 and matched != _ZERO)
    ):
        message = "anchor coverage ratio does not match anchor counts"
        raise _NATIVE_FINGERPRINT_POLICY_ERROR(message)


@dataclass(frozen=True, slots=True, init=False)
class AnchorCoverage:
    """Measured overlap between reference and candidate stable anchors."""

    matched: int
    total: int
    ratio: float

    def __init__(self, matched: int, total: int, ratio: float) -> None:
        """Validate coverage counts and ratio using the original guard."""
        _COVERAGE_MATCHED_SLOT.__set__(self, matched)
        _COVERAGE_TOTAL_SLOT.__set__(self, total)
        _COVERAGE_RATIO_SLOT.__set__(self, ratio)
        _ANCHOR_COVERAGE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require coverage counts and ratio to describe the same overlap."""
        _validate_anchor_coverage(self)


_ANCHOR_COVERAGE_VALIDATOR = cast(
    "Callable[[AnchorCoverage], None]", AnchorCoverage.__dict__["__post_init__"]
)

_COVERAGE_MATCHED_SLOT = cast(
    "MemberDescriptorType", AnchorCoverage.__dict__["matched"]
)
_COVERAGE_TOTAL_SLOT = cast(
    "MemberDescriptorType", AnchorCoverage.__dict__["total"]
)
_COVERAGE_RATIO_SLOT = cast(
    "MemberDescriptorType", AnchorCoverage.__dict__["ratio"]
)
_COVERAGE_INIT = cast(
    "Callable[[AnchorCoverage, int, int, float], None]",
    AnchorCoverage.__dict__["__init__"],
)
# Native class identities remain authoritative after consumer module alias edits.
_NATIVE_ANCHOR_POLICY = AnchorPolicy
_NATIVE_STABLE_ANCHOR = StableAnchor
_NATIVE_ANCHOR_COVERAGE = AnchorCoverage


def _coverage_fields(coverage: AnchorCoverage) -> tuple[int, int, float]:
    return (
        _COVERAGE_MATCHED_SLOT.__get__(coverage, AnchorCoverage),
        _COVERAGE_TOTAL_SLOT.__get__(coverage, AnchorCoverage),
        _COVERAGE_RATIO_SLOT.__get__(coverage, AnchorCoverage),
    )


def _new_anchor(digest: bytes, offset: int) -> StableAnchor:
    """Construct internal evidence without late class allocation/init hooks."""
    anchor = _NATIVE_OBJECT_NEW(_NATIVE_STABLE_ANCHOR)
    _ANCHOR_INIT(anchor, digest, offset)
    return anchor


def _new_coverage(matched: int, total: int, ratio: float) -> AnchorCoverage:
    """Keep computed lineage coverage independent of late class constructors."""
    coverage = _NATIVE_OBJECT_NEW(_NATIVE_ANCHOR_COVERAGE)
    _COVERAGE_INIT(coverage, matched, total, ratio)
    return coverage


def _digest_window(window: bytes) -> bytes:
    return _SHA256_FACTORY(window).digest()


def _small_input_anchor(data: bytes) -> tuple[StableAnchor, ...]:
    if not data:
        return ()
    return (_new_anchor(digest=_digest_window(data), offset=_ZERO),)


def _initial_rolling_hash(data: bytes, window_bytes: int) -> int:
    value = _ZERO
    for byte in data[:window_bytes]:
        value = ((value * _ROLLING_BASE) + byte) & _ROLLING_MASK
    return value


def _rolling_power(window_bytes: int) -> int:
    return _NATIVE_POW(_ROLLING_BASE, window_bytes - _ONE, _ROLLING_MODULUS)


def _roll_hash(
    value: int,
    outgoing: int,
    incoming: int,
    *,
    leading_power: int,
) -> int:
    without_leading = (value - (outgoing * leading_power)) & _ROLLING_MASK
    return ((without_leading * _ROLLING_BASE) + incoming) & _ROLLING_MASK


def _selected_anchor(
    data: bytes, offset: int, window_bytes: int
) -> StableAnchor:
    window = data[offset : offset + window_bytes]
    return _new_anchor(digest=_digest_window(window), offset=offset)


def _scan_anchor_windows(
    data: bytes,
    window_bytes: int,
    selection_modulus: int,
) -> tuple[dict[bytes, StableAnchor], int]:
    last_offset = _NATIVE_LEN(data) - window_bytes
    selected: dict[bytes, StableAnchor] = {}
    rolling = _initial_rolling_hash(data, window_bytes)
    leading_power = _rolling_power(window_bytes)
    fallback_value = rolling
    fallback_offset = _ZERO
    for offset in _NATIVE_RANGE(last_offset + _ONE):
        if rolling < fallback_value:
            fallback_value = rolling
            fallback_offset = offset
        if rolling % selection_modulus == _ZERO:
            anchor = _selected_anchor(data, offset, window_bytes)
            _ = selected.setdefault(_anchor_fields(anchor)[0], anchor)
        if offset < last_offset:
            rolling = _roll_hash(
                rolling,
                data[offset],
                data[offset + window_bytes],
                leading_power=leading_power,
            )
    return selected, fallback_offset


def stable_anchors(
    data: bytes,
    policy: AnchorPolicy = _DEFAULT_POLICY,
) -> tuple[StableAnchor, ...]:
    """Select deterministic anchors from sliding content windows.

    A 64-bit polynomial rolling hash evaluates every fixed-size content window.
    The rolling value selects sparse windows without a cryptographic hash call
    at every byte offset; selected windows are then fingerprinted with SHA-256.
    Insertions shift offsets but unchanged windows retain the same selector
    value
    and final digest. If no window is selected, the minimum rolling-hash window
    becomes a deterministic fallback.

    Returns:
        Unique selected SHA-256 digests ordered by authoring offset.

    Raises:
        FingerprintPolicyError: Input bytes or policy metadata is invalid.

    """
    if _NATIVE_TYPE(data) is not _NATIVE_BYTES:
        message = "stable anchor input must use exact bytes"
        raise _NATIVE_FINGERPRINT_POLICY_ERROR(message)
    if _NATIVE_TYPE(policy) is not _NATIVE_ANCHOR_POLICY:
        message = "stable anchor policy must use the exact AnchorPolicy type"
        raise _NATIVE_FINGERPRINT_POLICY_ERROR(message)
    # Exact native type alone does not prove that callers ran __init__.
    # Revalidate original slotted metadata before it controls hash windows.
    try:
        _ANCHOR_POLICY_VALIDATOR(policy)
        window_bytes, selection_modulus = _policy_fields(policy)
    except _NATIVE_ATTRIBUTE_ERROR as error:
        message = "stable anchor policy has incomplete native metadata"
        raise _NATIVE_FINGERPRINT_POLICY_ERROR(message) from error
    if _NATIVE_LEN(data) < window_bytes:
        return _small_input_anchor(data)
    selected, fallback_offset = _scan_anchor_windows(
        data, window_bytes, selection_modulus
    )
    if not selected:
        fallback = _selected_anchor(data, fallback_offset, window_bytes)
        selected[_anchor_fields(fallback)[0]] = fallback
    ordered = _NATIVE_SORTED(
        selected.values(), key=lambda anchor: _anchor_fields(anchor)[1]
    )
    return _NATIVE_TUPLE(ordered)


def anchor_coverage(
    reference: tuple[StableAnchor, ...],
    candidate: tuple[StableAnchor, ...],
) -> AnchorCoverage:
    """Measure how many unique reference anchor digests survive in a candidate.

    Returns:
        Matched count, reference count, and matched/reference ratio.

    Raises:
        FingerprintPolicyError: Anchor collections contain foreign records.

    """
    reference_type = _NATIVE_TYPE(reference)
    candidate_type = _NATIVE_TYPE(candidate)
    native_reference = reference_type is _NATIVE_TUPLE
    native_candidate = candidate_type is _NATIVE_TUPLE
    if not native_reference or not native_candidate:
        message = "anchor coverage inputs must use exact immutable tuples"
        raise _NATIVE_FINGERPRINT_POLICY_ERROR(message)
    for anchor in (*reference, *candidate):
        if _NATIVE_TYPE(anchor) is not _NATIVE_STABLE_ANCHOR:
            message = "anchor coverage inputs contain a foreign anchor record"
            raise _NATIVE_FINGERPRINT_POLICY_ERROR(message)
        # A fabricated exact StableAnchor can carry invalid native slots even
        # though its class identity passes the public admission gate.
        try:
            _STABLE_ANCHOR_VALIDATOR(anchor)
        except _NATIVE_ATTRIBUTE_ERROR as error:
            message = "anchor coverage input has incomplete native anchor metadata"
            raise _NATIVE_FINGERPRINT_POLICY_ERROR(message) from error
    reference_digests = {_anchor_fields(anchor)[0] for anchor in reference}
    candidate_digests = {_anchor_fields(anchor)[0] for anchor in candidate}
    total = _NATIVE_LEN(reference_digests)
    if total == _ZERO:
        return _new_coverage(matched=_ZERO, total=_ZERO, ratio=1.0)
    matched = _NATIVE_LEN(reference_digests & candidate_digests)
    return _new_coverage(
        matched=matched,
        total=total,
        ratio=matched / total,
    )
