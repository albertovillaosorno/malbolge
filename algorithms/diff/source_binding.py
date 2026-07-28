# File:
#   - source_binding.py
# Path:
#   - algorithms/diff/source_binding.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
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
#   - Deterministic threshold source binding for high-entropy key material.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""
Deterministic threshold source binding for high-entropy key material.

This module implements only the source-bound *key unlock* layer. It does not
serialize or encrypt target payload bytes. A future payload cipher must remain
blocked until an independently reviewed AEAD construction is selected.

Share masks use HKDF-SHA-256 as specified by RFC 5869. Polynomial coefficients
are deterministically derived from the secret to preserve repository generation
determinism; consequently this implementation makes a computational source-
binding claim, not a claim of information-theoretic perfect secret sharing.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import math
from typing import TYPE_CHECKING

from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.fingerprints import stable_anchors

if TYPE_CHECKING:
    from algorithms.diff.admission import IdentityFile
    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.fingerprints import StableAnchor

_SHA256_BYTES = 32
_HKDF_MAX_BLOCKS = 255
_GF_SIZE = 256
_GF_REDUCTION = 0x1B
_GF_HIGH_BIT = 0x80
_MAX_SHARES = 255
_ONE = 1
_ZERO = 0
_DEFAULT_BINDING_ANCHOR_POLICY = AnchorPolicy(
    window_bytes=32,
    selection_modulus=64,
)


class SourceBindingPolicyError(ValueError):
    """Raised when threshold source-binding policy is internally invalid."""


class SourceBindingError(RuntimeError):
    """Raised when candidate source cannot recover bound key material."""


@dataclass(frozen=True, slots=True)
class SourceBindingPolicy:
    """Deterministic threshold and anchor-selection policy."""

    threshold_fraction: float
    maximum_anchors: int = 127
    minimum_anchor_files: int = 3
    anchor_policy: AnchorPolicy = _DEFAULT_BINDING_ANCHOR_POLICY

    def __post_init__(self) -> None:
        """Reject invalid threshold or anchor-distribution policy.

        Raises:
            SourceBindingPolicyError: One policy value is outside its domain.

        """
        if (
            not math.isfinite(self.threshold_fraction)
            or self.threshold_fraction <= _ZERO
            or self.threshold_fraction > _ONE
        ):
            message = "threshold_fraction must be a finite value in (0, 1]"
            raise SourceBindingPolicyError(message)
        if self.maximum_anchors < _ONE or self.maximum_anchors > _MAX_SHARES:
            message = "maximum_anchors must be in [1, 255]"
            raise SourceBindingPolicyError(message)
        if self.minimum_anchor_files < _ONE:
            message = "minimum_anchor_files must be positive"
            raise SourceBindingPolicyError(message)
        if self.minimum_anchor_files > self.maximum_anchors:
            message = "minimum_anchor_files cannot exceed maximum_anchors"
            raise SourceBindingPolicyError(message)


@dataclass(frozen=True, slots=True, order=True)
class BoundShare:
    """One masked threshold share bound to one canonical source anchor."""

    source_path: str
    anchor_digest: bytes
    x: int
    masked_share: bytes


@dataclass(frozen=True, slots=True)
class ThresholdBinding:
    """Distributable source-bound secret metadata without plaintext secret."""

    context: bytes
    threshold: int
    minimum_anchor_files: int
    secret_length: int
    secret_commitment: bytes
    anchor_policy: AnchorPolicy
    shares: tuple[BoundShare, ...]


@dataclass(frozen=True, slots=True)
class _AnchorMaterial:
    source_path: str
    digest: bytes
    window: bytes


@dataclass(frozen=True, slots=True)
class _RecoveredShare:
    source_path: str
    x: int
    value: bytes


def hkdf_extract_sha256(salt: bytes, input_key_material: bytes) -> bytes:
    """Apply RFC 5869 HKDF-Extract with SHA-256.

    Returns:
        A 32-byte pseudorandom key.

    """
    effective_salt = salt or bytes(_SHA256_BYTES)
    return hmac.new(effective_salt, input_key_material, hashlib.sha256).digest()


def hkdf_expand_sha256(
    pseudorandom_key: bytes,
    info: bytes,
    length: int,
) -> bytes:
    """Apply RFC 5869 HKDF-Expand with SHA-256.

    Returns:
        Exactly ``length`` bytes of output keying material.

    Raises:
        SourceBindingPolicyError: The output length exceeds RFC 5869 limits.

    """
    if length < _ZERO or length > _HKDF_MAX_BLOCKS * _SHA256_BYTES:
        message = "HKDF-SHA-256 output length exceeds RFC 5869 limits"
        raise SourceBindingPolicyError(message)
    output = bytearray()
    previous = b""
    block_count = math.ceil(length / _SHA256_BYTES)
    for block_index in range(_ONE, block_count + _ONE):
        previous = hmac.new(
            pseudorandom_key,
            previous + info + bytes([block_index]),
            hashlib.sha256,
        ).digest()
        output.extend(previous)
    return bytes(output[:length])


def _frame(value: bytes) -> bytes:
    return len(value).to_bytes(8, byteorder="big") + value


def _context_digest(context: bytes) -> bytes:
    return hashlib.sha256(
        b"source-binding-context-v1\0" + _frame(context)
    ).digest()


def _secret_commitment(context: bytes, secret: bytes) -> bytes:
    return hashlib.sha256(
        b"source-binding-secret-commitment-v1\0"
        + _frame(context)
        + _frame(secret)
    ).digest()


def _gf_multiply(left: int, right: int) -> int:
    result = _ZERO
    multiplicand = left
    multiplier = right
    for _ in range(8):
        if multiplier & _ONE:
            result ^= multiplicand
        high_bit = multiplicand & _GF_HIGH_BIT
        multiplicand = (multiplicand << _ONE) & 0xFF
        if high_bit:
            multiplicand ^= _GF_REDUCTION
        multiplier >>= _ONE
    return result


def _gf_power(value: int, exponent: int) -> int:
    result = _ONE
    base = value
    remaining = exponent
    while remaining:
        if remaining & _ONE:
            result = _gf_multiply(result, base)
        base = _gf_multiply(base, base)
        remaining >>= _ONE
    return result


def _gf_inverse(value: int) -> int:
    if value == _ZERO:
        message = "cannot invert zero in GF(256)"
        raise SourceBindingError(message)
    return _gf_power(value, 254)


def _gf_divide(numerator: int, denominator: int) -> int:
    return _gf_multiply(numerator, _gf_inverse(denominator))


def _coefficient_bytes(
    secret: bytes,
    context: bytes,
    *,
    byte_index: int,
    degree: int,
) -> bytes:
    if degree == _ZERO:
        return b""
    salt = _context_digest(context)
    pseudorandom_key = hkdf_extract_sha256(salt, secret)
    info = b"source-binding-shamir-coefficients-v1\0" + byte_index.to_bytes(
        8, byteorder="big"
    )
    return hkdf_expand_sha256(pseudorandom_key, info, degree)


def _evaluate_polynomial(secret_byte: int, coefficients: bytes, x: int) -> int:
    result = secret_byte
    power = _ONE
    for coefficient in coefficients:
        power = _gf_multiply(power, x)
        result ^= _gf_multiply(coefficient, power)
    return result


def _split_secret(
    secret: bytes,
    context: bytes,
    *,
    threshold: int,
    share_count: int,
) -> tuple[tuple[int, bytes], ...]:
    shares = [bytearray(len(secret)) for _ in range(share_count)]
    degree = threshold - _ONE
    for byte_index, secret_byte in enumerate(secret):
        coefficients = _coefficient_bytes(
            secret,
            context,
            byte_index=byte_index,
            degree=degree,
        )
        for share_index in range(share_count):
            x = share_index + _ONE
            shares[share_index][byte_index] = _evaluate_polynomial(
                secret_byte,
                coefficients,
                x,
            )
    return tuple(
        (share_index + _ONE, bytes(share))
        for share_index, share in enumerate(shares)
    )


def _lagrange_weight_at_zero(x: int, x_values: tuple[int, ...]) -> int:
    numerator = _ONE
    denominator = _ONE
    for other in x_values:
        if other == x:
            continue
        numerator = _gf_multiply(numerator, other)
        denominator = _gf_multiply(denominator, x ^ other)
    return _gf_divide(numerator, denominator)


def _validate_recovery_shares(
    shares: tuple[tuple[int, bytes], ...],
) -> tuple[tuple[int, ...], int]:
    if not shares:
        message = "cannot recover a secret from zero shares"
        raise SourceBindingError(message)
    x_values = tuple(x for x, _ in shares)
    if any(x <= _ZERO or x >= _GF_SIZE for x in x_values):
        message = "share coordinate is outside GF(256)"
        raise SourceBindingError(message)
    if len(x_values) != len(set(x_values)):
        message = "share coordinates must be unique"
        raise SourceBindingError(message)
    lengths = {len(share) for _, share in shares}
    if len(lengths) != _ONE:
        message = "threshold shares have inconsistent lengths"
        raise SourceBindingError(message)
    return x_values, lengths.pop()


def _interpolate_secret_byte(
    shares: tuple[tuple[int, bytes], ...],
    weights: dict[int, int],
    byte_index: int,
) -> int:
    value = _ZERO
    for x, share in shares:
        value ^= _gf_multiply(share[byte_index], weights[x])
    return value


def _recover_shares(shares: tuple[tuple[int, bytes], ...]) -> bytes:
    x_values, secret_length = _validate_recovery_shares(shares)
    weights = {x: _lagrange_weight_at_zero(x, x_values) for x in x_values}
    return bytes(
        _interpolate_secret_byte(shares, weights, byte_index)
        for byte_index in range(secret_length)
    )


def _anchor_window(
    identity_file: IdentityFile,
    anchor: StableAnchor,
    policy: AnchorPolicy,
) -> bytes:
    if len(identity_file.canonical) < policy.window_bytes:
        return identity_file.canonical
    end = anchor.offset + policy.window_bytes
    return identity_file.canonical[anchor.offset : end]


def _file_anchor_materials(
    identity_file: IdentityFile,
    policy: AnchorPolicy,
) -> tuple[_AnchorMaterial, ...]:
    anchors = sorted(
        stable_anchors(identity_file.canonical, policy),
        key=lambda anchor: anchor.digest,
    )
    return tuple(
        _AnchorMaterial(
            source_path=identity_file.path,
            digest=anchor.digest,
            window=_anchor_window(identity_file, anchor, policy),
        )
        for anchor in anchors
    )


def _per_file_anchor_materials(
    reference: IdentityTree,
    policy: AnchorPolicy,
) -> tuple[tuple[_AnchorMaterial, ...], ...]:
    return tuple(
        materials
        for identity_file in reference.files
        if (materials := _file_anchor_materials(identity_file, policy))
    )


def _round_robin_materials(
    per_file: tuple[tuple[_AnchorMaterial, ...], ...],
    maximum_anchors: int,
) -> tuple[_AnchorMaterial, ...]:
    selected: list[_AnchorMaterial] = []
    maximum_depth = max(
        (len(materials) for materials in per_file), default=_ZERO
    )
    for depth in range(maximum_depth):
        for materials in per_file:
            if depth < len(materials):
                selected.append(materials[depth])
            if len(selected) == maximum_anchors:
                return tuple(selected)
    return tuple(selected)


def _require_distributed_materials(
    selected: tuple[_AnchorMaterial, ...],
    minimum_anchor_files: int,
) -> None:
    selected_files = {item.source_path for item in selected}
    if len(selected_files) < minimum_anchor_files:
        message = "reference identity lacks distributed source-binding anchors"
        raise SourceBindingPolicyError(message)


def _select_anchor_materials(
    reference: IdentityTree,
    policy: SourceBindingPolicy,
) -> tuple[_AnchorMaterial, ...]:
    per_file = _per_file_anchor_materials(reference, policy.anchor_policy)
    if not per_file:
        message = "reference identity tree contains no bindable anchor material"
        raise SourceBindingPolicyError(message)
    selected = _round_robin_materials(per_file, policy.maximum_anchors)
    _require_distributed_materials(selected, policy.minimum_anchor_files)
    return selected


def _share_mask(
    material: _AnchorMaterial,
    context: bytes,
    *,
    x: int,
    length: int,
) -> bytes:
    salt = _context_digest(context)
    pseudorandom_key = hkdf_extract_sha256(salt, material.window)
    info = (
        b"source-binding-anchor-share-mask-v1\0"
        + _frame(material.source_path.encode("utf-8"))
        + _frame(material.digest)
        + x.to_bytes(2, byteorder="big")
    )
    return hkdf_expand_sha256(pseudorandom_key, info, length)


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    if len(left) != len(right):
        message = "source-binding byte strings have inconsistent lengths"
        raise SourceBindingError(message)
    return bytes(a ^ b for a, b in zip(left, right, strict=True))


def bind_secret(
    reference: IdentityTree,
    secret: bytes,
    *,
    policy: SourceBindingPolicy,
    context: bytes,
) -> ThresholdBinding:
    """Bind high-entropy secret bytes to a threshold of reference anchors.

    The returned object contains only masked shares and a commitment. It does
    not contain the plaintext secret or target payload bytes.

    Returns:
        Deterministic threshold source-binding metadata.

    Raises:
        SourceBindingPolicyError: Input or reference evidence is unsuitable.

    """
    if not secret:
        message = "source-bound secret must be non-empty"
        raise SourceBindingPolicyError(message)
    if len(secret) > _HKDF_MAX_BLOCKS * _SHA256_BYTES:
        message = "source-bound secret exceeds HKDF-SHA-256 output limits"
        raise SourceBindingPolicyError(message)
    if not context:
        message = "source-binding context must be non-empty"
        raise SourceBindingPolicyError(message)
    materials = _select_anchor_materials(reference, policy)
    threshold = max(
        _ONE,
        math.ceil(len(materials) * policy.threshold_fraction),
    )
    raw_shares = _split_secret(
        secret,
        context,
        threshold=threshold,
        share_count=len(materials),
    )
    bound_shares = tuple(
        BoundShare(
            source_path=material.source_path,
            anchor_digest=material.digest,
            x=x,
            masked_share=_xor_bytes(
                share,
                _share_mask(
                    material,
                    context,
                    x=x,
                    length=len(secret),
                ),
            ),
        )
        for material, (x, share) in zip(materials, raw_shares, strict=True)
    )
    return ThresholdBinding(
        context=context,
        threshold=threshold,
        minimum_anchor_files=policy.minimum_anchor_files,
        secret_length=len(secret),
        secret_commitment=_secret_commitment(context, secret),
        anchor_policy=policy.anchor_policy,
        shares=bound_shares,
    )


def _candidate_materials(
    candidate: IdentityTree,
    policy: AnchorPolicy,
) -> dict[tuple[str, bytes], _AnchorMaterial]:
    materials: dict[tuple[str, bytes], _AnchorMaterial] = {}
    for identity_file in candidate.files:
        for material in _file_anchor_materials(identity_file, policy):
            materials[material.source_path, material.digest] = material
    return materials


def _recover_available_shares(
    binding: ThresholdBinding,
    candidate: IdentityTree,
) -> tuple[_RecoveredShare, ...]:
    candidate_materials = _candidate_materials(candidate, binding.anchor_policy)
    available: list[_RecoveredShare] = []
    for bound in binding.shares:
        material = candidate_materials.get((
            bound.source_path,
            bound.anchor_digest,
        ))
        if material is None:
            continue
        mask = _share_mask(
            material,
            binding.context,
            x=bound.x,
            length=binding.secret_length,
        )
        available.append(
            _RecoveredShare(
                source_path=bound.source_path,
                x=bound.x,
                value=_xor_bytes(bound.masked_share, mask),
            )
        )
    return tuple(available)


def _require_recovery_distribution(
    binding: ThresholdBinding,
    available: tuple[_RecoveredShare, ...],
) -> None:
    available_files = {share.source_path for share in available}
    if len(available_files) < binding.minimum_anchor_files:
        message = (
            "insufficient distributed source-bound files: "
            f"need {binding.minimum_anchor_files}, found {len(available_files)}"
        )
        raise SourceBindingError(message)


def recover_secret(
    binding: ThresholdBinding,
    candidate: IdentityTree,
) -> bytes:
    """Recover source-bound key material after the configured threshold exists.

    Returns:
        The committed secret bytes.

    Raises:
        SourceBindingError: Too few anchors exist or recovered material fails
        its commitment.

    """
    available = _recover_available_shares(binding, candidate)
    if len(available) < binding.threshold:
        message = (
            "insufficient source-bound anchors: "
            f"need {binding.threshold}, found {len(available)}"
        )
        raise SourceBindingError(message)
    _require_recovery_distribution(binding, available)
    raw_shares = tuple(
        (share.x, share.value) for share in available[: binding.threshold]
    )
    secret = _recover_shares(raw_shares)
    if _secret_commitment(binding.context, secret) != binding.secret_commitment:
        message = "recovered source-bound secret failed commitment"
        raise SourceBindingError(message)
    return secret
