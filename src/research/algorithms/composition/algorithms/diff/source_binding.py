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
#   - Deterministic threshold source binding for high-entropy key material.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
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

import builtins
import math
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256 as _native_sha256
from types import MemberDescriptorType
from typing import cast

from algorithms.diff.admission import IdentityFile, IdentityTree
from algorithms.diff.fingerprints import (
    AnchorPolicy,
    StableAnchor,
    stable_anchors,
)

_SHA256_BYTES = 32
_SHA256_BLOCK_BYTES = 64
_HMAC_INNER_PAD = 0x36
_HMAC_OUTER_PAD = 0x5C
_HKDF_MAX_BLOCKS = 255
_GF_SIZE = 256
_GF_REDUCTION = 0x1B
_GF_HIGH_BIT = 0x80
_MAX_SHARES = 255
_ONE = 1
_ZERO = 0
_BACKSLASH = "\\"
_UNSAFE_PATH_COMPONENTS = frozenset(("", ".", ".."))
_NUL = "\x00"
# Portable Windows name checks must not call ntpath.isreserved/splitdrive:
# those helpers reconsult mutable os.fspath, splitroot, and builtins.
_WINDOWS_DRIVE_SEPARATOR = ":"
_WINDOWS_RESERVED_CHARACTERS = frozenset(
    chr(value) for value in range(32)
) | frozenset("*?<>/\\:|") | frozenset((chr(34),))
_WINDOWS_RESERVED_DEVICES = frozenset(
    ("CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$")
) | frozenset(
    f"{prefix}{digit}" for prefix in ("COM", "LPT")
    for digit in "123456789¹²³"
)
# Preserve threshold and selection semantics across domain callback hooks.
_NATIVE_MAX = builtins.max
_NATIVE_SORTED = builtins.sorted
# Keep share admission and key derivation independent of late host hooks.
_NATIVE_ANY = builtins.any
_NATIVE_BYTEARRAY = builtins.bytearray
_NATIVE_BYTES = builtins.bytes
_NATIVE_SET = builtins.set
_NATIVE_TYPE = builtins.type
_NATIVE_INT = builtins.int
_NATIVE_FLOAT = builtins.float
_NATIVE_STR = builtins.str
_NATIVE_LEN = builtins.len
_NATIVE_TUPLE = builtins.tuple
_NATIVE_RANGE = builtins.range
_NATIVE_ENUMERATE = builtins.enumerate
_NATIVE_ISFINITE = math.isfinite
_NATIVE_CEIL = math.ceil
_NATIVE_ZIP = builtins.zip
_NATIVE_OBJECT_NEW = object.__new__
_DEFAULT_BINDING_ANCHOR_POLICY = AnchorPolicy(
    window_bytes=32,
    selection_modulus=64,
)


class SourceBindingPolicyError(ValueError):
    """Raised when threshold source-binding policy is internally invalid."""


class SourceBindingError(RuntimeError):
    """Raised when candidate source cannot recover bound key material."""


def _binding_fraction(value: object) -> float:
    message = "threshold_fraction must be a finite value in (0, 1]"
    if _NATIVE_TYPE(value) is _NATIVE_INT:
        # The only integral fraction in (0, 1] is one. Reject large integers
        # before float conversion, which can otherwise raise OverflowError.
        if value != _ONE:
            raise SourceBindingPolicyError(message)
        return 1.0
    if _NATIVE_TYPE(value) is not _NATIVE_FLOAT:
        raise SourceBindingPolicyError(message)
    if not _NATIVE_ISFINITE(value) or value <= _ZERO or value > _ONE:
        raise SourceBindingPolicyError(message)
    return value


def _binding_positive_int(value: object, context: str, maximum: int | None) -> int:
    if _NATIVE_TYPE(value) is not _NATIVE_INT or value < _ONE:
        message = f"{context} must be a positive integer"
        raise SourceBindingPolicyError(message)
    if maximum is not None and value > maximum:
        message = f"{context} must not exceed {maximum}"
        raise SourceBindingPolicyError(message)
    return value


@dataclass(frozen=True, slots=True, init=False)
class SourceBindingPolicy:
    """Deterministic threshold and anchor-selection policy."""

    threshold_fraction: float
    maximum_anchors: int = 127
    minimum_anchor_files: int = 3
    anchor_policy: AnchorPolicy = _DEFAULT_BINDING_ANCHOR_POLICY

    def __init__(
        self,
        threshold_fraction: float,
        maximum_anchors: int = 127,
        minimum_anchor_files: int = 3,
        anchor_policy: AnchorPolicy = _DEFAULT_BINDING_ANCHOR_POLICY,
    ) -> None:
        """Validate source quorum policy through the captured native guard."""
        _POLICY_FRACTION_SLOT.__set__(self, threshold_fraction)
        _POLICY_MAXIMUM_SLOT.__set__(self, maximum_anchors)
        _POLICY_MINIMUM_SLOT.__set__(self, minimum_anchor_files)
        _POLICY_ANCHORS_SLOT.__set__(self, anchor_policy)
        _SOURCE_BINDING_POLICY_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject invalid threshold or anchor-distribution policy.

        Raises:
            SourceBindingPolicyError: One policy value is outside its domain.

        """
        fraction, maximum_anchors, minimum_files, anchor_policy = (
            _policy_fields(self)
        )
        _ = _binding_fraction(fraction)
        maximum = _binding_positive_int(
            maximum_anchors, "maximum_anchors", _MAX_SHARES
        )
        minimum = _binding_positive_int(
            minimum_files, "minimum_anchor_files", None
        )
        if minimum > maximum:
            message = "minimum_anchor_files cannot exceed maximum_anchors"
            raise SourceBindingPolicyError(message)
        if _NATIVE_TYPE(anchor_policy) is not AnchorPolicy:
            message = "anchor_policy must use the exact AnchorPolicy type"
            raise SourceBindingPolicyError(message)
        if not _valid_anchor_policy_fields(anchor_policy):
            message = "anchor_policy requires positive exact integer anchor dimensions"
            raise SourceBindingPolicyError(message)


# Generated dataclass constructors resolve post-init through mutable class
# attributes. Preserve its original guard against later consumer overrides.
_SOURCE_BINDING_POLICY_VALIDATOR = cast(
    "Callable[[SourceBindingPolicy], None]",
    SourceBindingPolicy.__dict__["__post_init__"],
)

# A consumer may replace dataclass class descriptors after this module loads.
# Read the original stored policy slots for both validation and key binding.
_POLICY_FRACTION_SLOT = cast(
    "MemberDescriptorType", SourceBindingPolicy.__dict__["threshold_fraction"]
)
_POLICY_MAXIMUM_SLOT = cast(
    "MemberDescriptorType", SourceBindingPolicy.__dict__["maximum_anchors"]
)
_POLICY_MINIMUM_SLOT = cast(
    "MemberDescriptorType", SourceBindingPolicy.__dict__["minimum_anchor_files"]
)
_POLICY_ANCHORS_SLOT = cast(
    "MemberDescriptorType", SourceBindingPolicy.__dict__["anchor_policy"]
)


def _policy_fields(
    policy: SourceBindingPolicy,
) -> tuple[float, int, int, AnchorPolicy]:
    return (
        _POLICY_FRACTION_SLOT.__get__(policy, SourceBindingPolicy),
        _POLICY_MAXIMUM_SLOT.__get__(policy, SourceBindingPolicy),
        _POLICY_MINIMUM_SLOT.__get__(policy, SourceBindingPolicy),
        _POLICY_ANCHORS_SLOT.__get__(policy, SourceBindingPolicy),
    )


@dataclass(frozen=True, slots=True, order=True, init=False)
class BoundShare:
    """One masked threshold share bound to one canonical source anchor."""

    source_path: str
    anchor_digest: bytes
    x: int
    masked_share: bytes

    def __init__(
        self,
        source_path: str,
        anchor_digest: bytes,
        x: int,
        masked_share: bytes,
    ) -> None:
        """Store the supplied share through original class slots."""
        _SHARE_PATH_SLOT.__set__(self, source_path)
        _SHARE_DIGEST_SLOT.__set__(self, anchor_digest)
        _SHARE_X_SLOT.__set__(self, x)
        _SHARE_MASKED_SLOT.__set__(self, masked_share)


@dataclass(frozen=True, slots=True, init=False)
class ThresholdBinding:
    """Distributable source-bound secret metadata without plaintext secret."""

    context: bytes
    threshold: int
    minimum_anchor_files: int
    secret_length: int
    secret_commitment: bytes
    anchor_policy: AnchorPolicy
    shares: tuple[BoundShare, ...]

    def __init__(
        self,
        context: bytes,
        threshold: int,
        minimum_anchor_files: int,
        secret_length: int,
        secret_commitment: bytes,
        anchor_policy: AnchorPolicy,
        shares: tuple[BoundShare, ...],
    ) -> None:
        """Store the exact envelope fields without invoking class setters."""
        _BINDING_CONTEXT_SLOT.__set__(self, context)
        _BINDING_THRESHOLD_SLOT.__set__(self, threshold)
        _BINDING_MINIMUM_FILES_SLOT.__set__(self, minimum_anchor_files)
        _BINDING_SECRET_LENGTH_SLOT.__set__(self, secret_length)
        _BINDING_COMMITMENT_SLOT.__set__(self, secret_commitment)
        _BINDING_ANCHOR_POLICY_SLOT.__set__(self, anchor_policy)
        _BINDING_SHARES_SLOT.__set__(self, shares)


@dataclass(frozen=True, slots=True, init=False)
class _AnchorMaterial:
    source_path: str
    digest: bytes
    window: bytes

    def __init__(self, source_path: str, digest: bytes, window: bytes) -> None:
        """Pin internal anchor material to its supplied bytes."""
        _ANCHOR_PATH_SLOT.__set__(self, source_path)
        _ANCHOR_DIGEST_SLOT.__set__(self, digest)
        _ANCHOR_WINDOW_SLOT.__set__(self, window)


@dataclass(frozen=True, slots=True, init=False)
class _RecoveredShare:
    source_path: str
    x: int
    value: bytes

    def __init__(self, source_path: str, x: int, value: bytes) -> None:
        """Pin internal recovered evidence to its supplied fields."""
        _RECOVERED_PATH_SLOT.__set__(self, source_path)
        _RECOVERED_X_SLOT.__set__(self, x)
        _RECOVERED_VALUE_SLOT.__set__(self, value)


# Imported fingerprint records and the window policy are also evidence.
_STABLE_ANCHOR_DIGEST_SLOT = cast(
    "MemberDescriptorType", StableAnchor.__dict__["digest"]
)
_STABLE_ANCHOR_OFFSET_SLOT = cast(
    "MemberDescriptorType", StableAnchor.__dict__["offset"]
)
_ANCHOR_POLICY_WINDOW_SLOT = cast(
    "MemberDescriptorType", AnchorPolicy.__dict__["window_bytes"]
)
_ANCHOR_POLICY_MODULUS_SLOT = cast(
    "MemberDescriptorType", AnchorPolicy.__dict__["selection_modulus"]
)


def _valid_anchor_policy_fields(value: AnchorPolicy) -> bool:
    if _NATIVE_TYPE(value) is not AnchorPolicy:
        return False
    # The envelope can originate outside the constructor. Check native slots
    # before candidate inspection instead of trusting a nested record's type.
    try:
        window = _ANCHOR_POLICY_WINDOW_SLOT.__get__(value, AnchorPolicy)
        modulus = _ANCHOR_POLICY_MODULUS_SLOT.__get__(value, AnchorPolicy)
    except AttributeError:
        return False
    return (
        _NATIVE_TYPE(window) is _NATIVE_INT
        and window > _ZERO
        and _NATIVE_TYPE(modulus) is _NATIVE_INT
        and modulus > _ZERO
    )


def _stable_anchor_digest(value: StableAnchor) -> bytes:
    return _STABLE_ANCHOR_DIGEST_SLOT.__get__(value, StableAnchor)


def _stable_anchor_offset(value: StableAnchor) -> int:
    return _STABLE_ANCHOR_OFFSET_SLOT.__get__(value, StableAnchor)


def _anchor_policy_window(value: AnchorPolicy) -> int:
    return _ANCHOR_POLICY_WINDOW_SLOT.__get__(value, AnchorPolicy)


# Private intermediate evidence cannot be reinterpreted by consumer hooks.
_ANCHOR_PATH_SLOT = cast(
    "MemberDescriptorType", _AnchorMaterial.__dict__["source_path"]
)
_ANCHOR_DIGEST_SLOT = cast(
    "MemberDescriptorType", _AnchorMaterial.__dict__["digest"]
)
_ANCHOR_WINDOW_SLOT = cast(
    "MemberDescriptorType", _AnchorMaterial.__dict__["window"]
)
_RECOVERED_PATH_SLOT = cast(
    "MemberDescriptorType", _RecoveredShare.__dict__["source_path"]
)
_RECOVERED_X_SLOT = cast(
    "MemberDescriptorType", _RecoveredShare.__dict__["x"]
)
_RECOVERED_VALUE_SLOT = cast(
    "MemberDescriptorType", _RecoveredShare.__dict__["value"]
)


def _anchor_path(value: _AnchorMaterial) -> str:
    return _ANCHOR_PATH_SLOT.__get__(value, _AnchorMaterial)


def _anchor_digest(value: _AnchorMaterial) -> bytes:
    return _ANCHOR_DIGEST_SLOT.__get__(value, _AnchorMaterial)


def _anchor_window_bytes(value: _AnchorMaterial) -> bytes:
    return _ANCHOR_WINDOW_SLOT.__get__(value, _AnchorMaterial)


def _recovered_path(value: _RecoveredShare) -> str:
    return _RECOVERED_PATH_SLOT.__get__(value, _RecoveredShare)


def _recovered_x(value: _RecoveredShare) -> int:
    return _RECOVERED_X_SLOT.__get__(value, _RecoveredShare)


def _recovered_value(value: _RecoveredShare) -> bytes:
    return _RECOVERED_VALUE_SLOT.__get__(value, _RecoveredShare)


# Bound key material must not reenter mutable class allocation/initializer
# hooks after consumer callbacks. Public constructors retain normal behavior.
_ANCHOR_MATERIAL_INIT = cast(
    "Callable[[_AnchorMaterial, str, bytes, bytes], None]",
    _AnchorMaterial.__dict__["__init__"],
)
_BOUND_SHARE_INIT = cast(
    "Callable[[BoundShare, str, bytes, int, bytes], None]",
    BoundShare.__dict__["__init__"],
)
_THRESHOLD_BINDING_INIT = cast(
    Callable[
        [
            ThresholdBinding,
            bytes,
            int,
            int,
            int,
            bytes,
            AnchorPolicy,
            tuple[BoundShare, ...],
        ],
        None,
    ],
    ThresholdBinding.__dict__["__init__"],
)
_RECOVERED_SHARE_INIT = cast(
    "Callable[[_RecoveredShare, str, int, bytes], None]",
    _RecoveredShare.__dict__["__init__"],
)


def _new_anchor_material(
    source_path: str, digest: bytes, window: bytes
) -> _AnchorMaterial:
    material = _NATIVE_OBJECT_NEW(_AnchorMaterial)
    _ANCHOR_MATERIAL_INIT(material, source_path, digest, window)
    return material


def _new_bound_share(
    source_path: str, anchor_digest: bytes, x: int, masked_share: bytes
) -> BoundShare:
    share = _NATIVE_OBJECT_NEW(BoundShare)
    _BOUND_SHARE_INIT(share, source_path, anchor_digest, x, masked_share)
    return share


def _new_threshold_binding(
    context: bytes,
    threshold: int,
    minimum_anchor_files: int,
    secret_length: int,
    secret_commitment: bytes,
    anchor_policy: AnchorPolicy,
    shares: tuple[BoundShare, ...],
) -> ThresholdBinding:
    binding = _NATIVE_OBJECT_NEW(ThresholdBinding)
    _THRESHOLD_BINDING_INIT(
        binding,
        context,
        threshold,
        minimum_anchor_files,
        secret_length,
        secret_commitment,
        anchor_policy,
        shares,
    )
    return binding


def _new_recovered_share(source_path: str, x: int, value: bytes) -> _RecoveredShare:
    share = _NATIVE_OBJECT_NEW(_RecoveredShare)
    _RECOVERED_SHARE_INIT(share, source_path, x, value)
    return share


# Source identities are admitted at construction; mutable class getters must
# not change the actual bytes or path labels used to bind or recover secrets.
_IDENTITY_FILES_SLOT = cast(
    "MemberDescriptorType", IdentityTree.__dict__["files"]
)
_IDENTITY_PATH_SLOT = cast(
    "MemberDescriptorType", IdentityFile.__dict__["path"]
)
_IDENTITY_CANONICAL_SLOT = cast(
    "MemberDescriptorType", IdentityFile.__dict__["canonical"]
)


def _identity_files(value: IdentityTree) -> tuple[IdentityFile, ...]:
    return _IDENTITY_FILES_SLOT.__get__(value, IdentityTree)


def _identity_path(value: IdentityFile) -> str:
    return _IDENTITY_PATH_SLOT.__get__(value, IdentityFile)


def _identity_canonical(value: IdentityFile) -> bytes:
    return _IDENTITY_CANONICAL_SLOT.__get__(value, IdentityFile)


# Validate and recover from stored metadata, not late class attribute hooks.
_BINDING_CONTEXT_SLOT = cast(
    "MemberDescriptorType", ThresholdBinding.__dict__["context"]
)
_BINDING_THRESHOLD_SLOT = cast(
    "MemberDescriptorType", ThresholdBinding.__dict__["threshold"]
)
_BINDING_MINIMUM_FILES_SLOT = cast(
    "MemberDescriptorType", ThresholdBinding.__dict__["minimum_anchor_files"]
)
_BINDING_SECRET_LENGTH_SLOT = cast(
    "MemberDescriptorType", ThresholdBinding.__dict__["secret_length"]
)
_BINDING_COMMITMENT_SLOT = cast(
    "MemberDescriptorType", ThresholdBinding.__dict__["secret_commitment"]
)
_BINDING_ANCHOR_POLICY_SLOT = cast(
    "MemberDescriptorType", ThresholdBinding.__dict__["anchor_policy"]
)
_BINDING_SHARES_SLOT = cast(
    "MemberDescriptorType", ThresholdBinding.__dict__["shares"]
)

_SHARE_PATH_SLOT = cast(
    "MemberDescriptorType", BoundShare.__dict__["source_path"]
)
_SHARE_DIGEST_SLOT = cast(
    "MemberDescriptorType", BoundShare.__dict__["anchor_digest"]
)
_SHARE_X_SLOT = cast(
    "MemberDescriptorType", BoundShare.__dict__["x"]
)
_SHARE_MASKED_SLOT = cast(
    "MemberDescriptorType", BoundShare.__dict__["masked_share"]
)


def _binding_context(value: ThresholdBinding) -> bytes:
    return _BINDING_CONTEXT_SLOT.__get__(value, ThresholdBinding)


def _binding_threshold(value: ThresholdBinding) -> int:
    return _BINDING_THRESHOLD_SLOT.__get__(value, ThresholdBinding)


def _binding_minimum_files(value: ThresholdBinding) -> int:
    return _BINDING_MINIMUM_FILES_SLOT.__get__(value, ThresholdBinding)


def _binding_secret_length(value: ThresholdBinding) -> int:
    return _BINDING_SECRET_LENGTH_SLOT.__get__(value, ThresholdBinding)


def _binding_commitment(value: ThresholdBinding) -> bytes:
    return _BINDING_COMMITMENT_SLOT.__get__(value, ThresholdBinding)


def _binding_anchor_policy(value: ThresholdBinding) -> AnchorPolicy:
    return _BINDING_ANCHOR_POLICY_SLOT.__get__(value, ThresholdBinding)


def _binding_shares(value: ThresholdBinding) -> tuple[BoundShare, ...]:
    return _BINDING_SHARES_SLOT.__get__(value, ThresholdBinding)


def _share_path(value: BoundShare) -> str:
    return _SHARE_PATH_SLOT.__get__(value, BoundShare)


def _share_digest(value: BoundShare) -> bytes:
    return _SHARE_DIGEST_SLOT.__get__(value, BoundShare)


def _share_x(value: BoundShare) -> int:
    return _SHARE_X_SLOT.__get__(value, BoundShare)


def _share_masked(value: BoundShare) -> bytes:
    return _SHARE_MASKED_SLOT.__get__(value, BoundShare)


def _hmac_sha256(key: bytes, message: bytes) -> bytes:
    # Use the import-pinned SHA-256 factory rather than mutable HMAC class
    # methods, which callbacks could replace after this module is imported.
    if _NATIVE_LEN(key) > _SHA256_BLOCK_BYTES:
        key = _native_sha256(key).digest()
    padded_key = key.ljust(_SHA256_BLOCK_BYTES, b"\0")
    inner = _NATIVE_BYTES(byte ^ _HMAC_INNER_PAD for byte in padded_key)
    outer = _NATIVE_BYTES(byte ^ _HMAC_OUTER_PAD for byte in padded_key)
    inner_digest = _native_sha256(inner + message).digest()
    return _native_sha256(outer + inner_digest).digest()


def hkdf_extract_sha256(salt: bytes, input_key_material: bytes) -> bytes:
    """Apply RFC 5869 HKDF-Extract with SHA-256.

    Returns:
        A 32-byte pseudorandom key.

    Raises:
        SourceBindingPolicyError: Salt or key material is not exact bytes.

    """
    if (
        _NATIVE_TYPE(salt) is not _NATIVE_BYTES
        or _NATIVE_TYPE(input_key_material) is not _NATIVE_BYTES
    ):
        message = "HKDF-SHA-256 extract inputs must use exact bytes"
        raise SourceBindingPolicyError(message)
    effective_salt = salt or _NATIVE_BYTES(_SHA256_BYTES)
    return _hmac_sha256(effective_salt, input_key_material)


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
    if (
        _NATIVE_TYPE(pseudorandom_key) is not _NATIVE_BYTES
        or _NATIVE_TYPE(info) is not _NATIVE_BYTES
    ):
        message = "HKDF-SHA-256 expand inputs must use exact bytes"
        raise SourceBindingPolicyError(message)
    if (
        _NATIVE_TYPE(length) is not _NATIVE_INT
        or length < _ZERO
        or length > _HKDF_MAX_BLOCKS * _SHA256_BYTES
    ):
        message = "HKDF-SHA-256 output length must be an integer within RFC 5869 limits"
        raise SourceBindingPolicyError(message)
    output = _NATIVE_BYTEARRAY()
    previous = b""
    block_count = _NATIVE_CEIL(length / _SHA256_BYTES)
    for block_index in _NATIVE_RANGE(_ONE, block_count + _ONE):
        previous = _hmac_sha256(
            pseudorandom_key, previous + info + _NATIVE_BYTES([block_index])
        )
        output.extend(previous)
    return _NATIVE_BYTES(output[:length])


def _frame(value: bytes) -> bytes:
    return _NATIVE_LEN(value).to_bytes(8, byteorder="big") + value


def _context_digest(context: bytes) -> bytes:
    return _native_sha256(b"source-binding-context-v1\0" + _frame(context)).digest()


def _secret_commitment(context: bytes, secret: bytes) -> bytes:
    return _native_sha256(
        b"source-binding-secret-commitment-v1\0" + _frame(context) + _frame(secret)
    ).digest()


def _gf_multiply(left: int, right: int) -> int:
    result = _ZERO
    multiplicand = left
    multiplier = right
    for _ in _NATIVE_RANGE(8):
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
    secret_size = _NATIVE_LEN(secret)
    shares = [_NATIVE_BYTEARRAY(secret_size) for _ in _NATIVE_RANGE(share_count)]
    degree = threshold - _ONE
    for byte_index, secret_byte in _NATIVE_ENUMERATE(secret):
        coefficients = _coefficient_bytes(
            secret,
            context,
            byte_index=byte_index,
            degree=degree,
        )
        for share_index in _NATIVE_RANGE(share_count):
            x = share_index + _ONE
            shares[share_index][byte_index] = _evaluate_polynomial(
                secret_byte,
                coefficients,
                x,
            )
    return _NATIVE_TUPLE(
        (share_index + _ONE, _NATIVE_BYTES(share))
        for share_index, share in _NATIVE_ENUMERATE(shares)
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
    x_values = _NATIVE_TUPLE(x for x, _ in shares)
    if _NATIVE_ANY(x <= _ZERO or x >= _GF_SIZE for x in x_values):
        message = "share coordinate is outside GF(256)"
        raise SourceBindingError(message)
    if _NATIVE_LEN(x_values) != _NATIVE_LEN(_NATIVE_SET(x_values)):
        message = "share coordinates must be unique"
        raise SourceBindingError(message)
    lengths = {_NATIVE_LEN(share) for _, share in shares}
    if _NATIVE_LEN(lengths) != _ONE:
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
    return _NATIVE_BYTES(
        _interpolate_secret_byte(shares, weights, byte_index)
        for byte_index in _NATIVE_RANGE(secret_length)
    )


def _anchor_window(
    identity_file: IdentityFile,
    anchor: StableAnchor,
    policy: AnchorPolicy,
) -> bytes:
    window_bytes = _anchor_policy_window(policy)
    if _NATIVE_LEN(_identity_canonical(identity_file)) < window_bytes:
        return _identity_canonical(identity_file)
    offset = _stable_anchor_offset(anchor)
    end = offset + window_bytes
    return _identity_canonical(identity_file)[offset:end]


def _file_anchor_materials(
    identity_file: IdentityFile,
    policy: AnchorPolicy,
) -> tuple[_AnchorMaterial, ...]:
    anchors = _NATIVE_SORTED(
        stable_anchors(_identity_canonical(identity_file), policy),
        key=lambda anchor: _stable_anchor_digest(anchor),
    )
    return _NATIVE_TUPLE(
        _new_anchor_material(
            source_path=_identity_path(identity_file),
            digest=_stable_anchor_digest(anchor),
            window=_anchor_window(identity_file, anchor, policy),
        )
        for anchor in anchors
    )


def _per_file_anchor_materials(
    reference: IdentityTree,
    policy: AnchorPolicy,
) -> tuple[tuple[_AnchorMaterial, ...], ...]:
    return _NATIVE_TUPLE(
        materials
        for identity_file in _identity_files(reference)
        if (materials := _file_anchor_materials(identity_file, policy))
    )


def _round_robin_materials(
    per_file: tuple[tuple[_AnchorMaterial, ...], ...],
    maximum_anchors: int,
) -> tuple[_AnchorMaterial, ...]:
    selected: list[_AnchorMaterial] = []
    maximum_depth = _NATIVE_MAX(
        (_NATIVE_LEN(materials) for materials in per_file), default=_ZERO
    )
    for depth in _NATIVE_RANGE(maximum_depth):
        for materials in per_file:
            if depth < _NATIVE_LEN(materials):
                selected.append(materials[depth])
            if _NATIVE_LEN(selected) == maximum_anchors:
                return _NATIVE_TUPLE(selected)
    return _NATIVE_TUPLE(selected)


def _require_distributed_materials(
    selected: tuple[_AnchorMaterial, ...],
    minimum_anchor_files: int,
) -> None:
    selected_files = {_anchor_path(item) for item in selected}
    if _NATIVE_LEN(selected_files) < minimum_anchor_files:
        message = "reference identity lacks distributed source-binding anchors"
        raise SourceBindingPolicyError(message)


def _select_anchor_materials(
    reference: IdentityTree,
    policy: SourceBindingPolicy,
) -> tuple[_AnchorMaterial, ...]:
    _, maximum, minimum, anchors = _policy_fields(policy)
    per_file = _per_file_anchor_materials(reference, anchors)
    if not per_file:
        message = "reference identity tree contains no bindable anchor material"
        raise SourceBindingPolicyError(message)
    selected = _round_robin_materials(per_file, maximum)
    _require_distributed_materials(selected, minimum)
    return selected


def _share_mask(
    material: _AnchorMaterial,
    context: bytes,
    *,
    x: int,
    length: int,
) -> bytes:
    salt = _context_digest(context)
    pseudorandom_key = hkdf_extract_sha256(salt, _anchor_window_bytes(material))
    info = (
        b"source-binding-anchor-share-mask-v1\0"
        + _frame(_anchor_path(material).encode("utf-8"))
        + _frame(_anchor_digest(material))
        + x.to_bytes(2, byteorder="big")
    )
    return hkdf_expand_sha256(pseudorandom_key, info, length)


def _xor_bytes(left: bytes, right: bytes) -> bytes:
    if _NATIVE_LEN(left) != _NATIVE_LEN(right):
        message = "source-binding byte strings have inconsistent lengths"
        raise SourceBindingError(message)
    pairs = _NATIVE_ZIP(left, right, strict=True)
    return _NATIVE_BYTES(a ^ b for a, b in pairs)


def _has_windows_drive(value: str) -> bool:
    # Backslash/UNC forms also fail canonical relative-path checks.
    return (
        value[1:2] == _WINDOWS_DRIVE_SEPARATOR
        or value.startswith(("//", "\\\\"))
    )


def _is_windows_reserved_component(component: str) -> bool:
    device = component.partition(".")[0].rstrip(" ").upper()
    return (
        (component[-1:] in {".", " "} and component not in {".", ".."})
        or bool(_WINDOWS_RESERVED_CHARACTERS.intersection(component))
        or device in _WINDOWS_RESERVED_DEVICES
    )


def _is_windows_reserved(value: str) -> bool:
    return _NATIVE_ANY(
        _is_windows_reserved_component(component)
        for component in value.split("/")
    )


def _validate_bind_identity(reference: object, policy: object) -> None:
    if _NATIVE_TYPE(reference) is not IdentityTree:
        message = "source-binding reference must use the exact IdentityTree type"
        raise SourceBindingPolicyError(message)
    if _NATIVE_TYPE(policy) is not SourceBindingPolicy:
        message = "source-binding policy must use the exact SourceBindingPolicy type"
        raise SourceBindingPolicyError(message)
    # Raw exact records can enter this boundary without running __init__.
    # Revalidate all native policy slots before interpreting source material.
    try:
        _SOURCE_BINDING_POLICY_VALIDATOR(policy)
    except AttributeError as error:
        message = "source-binding policy requires all stored fields"
        raise SourceBindingPolicyError(message) from error
    drives = (
        _has_windows_drive(_identity_path(item))
        for item in _identity_files(reference)
    )
    if _NATIVE_ANY(drives):
        message = "source-binding reference path cannot have a Windows drive"
        raise SourceBindingPolicyError(message)


def _validate_bind_secret(secret: object, context: object) -> None:
    if _NATIVE_TYPE(secret) is not _NATIVE_BYTES or not secret:
        message = "source-bound secret must be non-empty exact bytes"
        raise SourceBindingPolicyError(message)
    if _NATIVE_LEN(secret) > _HKDF_MAX_BLOCKS * _SHA256_BYTES:
        message = "source-bound secret exceeds HKDF-SHA-256 output limits"
        raise SourceBindingPolicyError(message)
    if _NATIVE_TYPE(context) is not _NATIVE_BYTES or not context:
        message = "source-binding context must be non-empty exact bytes"
        raise SourceBindingPolicyError(message)


def _validate_bind_inputs(
    reference: object, secret: object, *, policy: object, context: object
) -> None:
    _validate_bind_identity(reference, policy)
    _validate_bind_secret(secret, context)


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
        SourceBindingPolicyError: The selected Shamir threshold cannot satisfy
            the required minimum number of source files.

    """
    _validate_bind_inputs(reference, secret, policy=policy, context=context)
    materials = _select_anchor_materials(reference, policy)
    fraction, _, minimum_files, anchor_policy = _policy_fields(policy)
    # Interpret the configured float's canonical decimal as the policy value.
    # A float product can round a fraction just above k/N back to k and admit
    # fewer shares than required. Integer arithmetic keeps the ceiling exact.
    fraction_value = _binding_fraction(fraction)
    fraction = Decimal(_NATIVE_STR(fraction_value))
    fraction_numerator, fraction_denominator = fraction.as_integer_ratio()
    numerator = _NATIVE_LEN(materials) * fraction_numerator
    threshold = _NATIVE_MAX(
        _ONE,
        (numerator + fraction_denominator - _ONE) // fraction_denominator,
    )
    if threshold < minimum_files:
        message = "source-binding threshold must reach minimum anchor files"
        raise SourceBindingPolicyError(message)
    raw_shares = _split_secret(
        secret,
        context,
        threshold=threshold,
        share_count=_NATIVE_LEN(materials),
    )
    paired = _NATIVE_ZIP(materials, raw_shares, strict=True)
    bound_shares = _NATIVE_TUPLE(
        _new_bound_share(
            source_path=_anchor_path(material),
            anchor_digest=_anchor_digest(material),
            x=x,
            masked_share=_xor_bytes(
                share,
                _share_mask(
                    material,
                    context,
                    x=x,
                    length=_NATIVE_LEN(secret),
                ),
            ),
        )
        for material, (x, share) in paired
    )
    return _new_threshold_binding(
        context=context,
        threshold=threshold,
        minimum_anchor_files=minimum_files,
        secret_length=_NATIVE_LEN(secret),
        secret_commitment=_secret_commitment(context, secret),
        anchor_policy=anchor_policy,
        shares=bound_shares,
    )


def _require_no_windows_drive(value: str) -> None:
    if _has_windows_drive(value):
        message = "source-binding share path cannot have a Windows drive"
        raise SourceBindingError(message)


def _validate_share_path(value: object) -> None:
    if _NATIVE_TYPE(value) is not _NATIVE_STR or not value:
        message = "source-binding share path must be a non-empty string"
        raise SourceBindingError(message)
    if _NUL in value:
        message = "source-binding share path cannot contain NUL"
        raise SourceBindingError(message)
    try:
        _ = value.encode("utf-8")
    except UnicodeEncodeError as error:
        message = "source-binding share path must be UTF-8 encodable"
        raise SourceBindingError(message) from error
    _require_no_windows_drive(value)
    if _is_windows_reserved(value):
        message = "source-binding share path uses a Windows reserved name"
        raise SourceBindingError(message)
    # Lexical admission cannot trust late mutations of pathlib class methods.
    unsafe = _BACKSLASH in value or _NATIVE_ANY(
        part in _UNSAFE_PATH_COMPONENTS for part in value.split("/")
    )
    if unsafe:
        message = "source-binding share path must be canonical and relative"
        raise SourceBindingError(message)


def _validate_share_payload(share: BoundShare, secret_length: int) -> None:
    if (
        _NATIVE_TYPE(_share_digest(share)) is not _NATIVE_BYTES
        or _NATIVE_LEN(_share_digest(share)) != _SHA256_BYTES
    ):
        message = "source-binding anchor digest must be 32 bytes"
        raise SourceBindingError(message)
    coordinate = _share_x(share)
    if (
        _NATIVE_TYPE(coordinate) is not _NATIVE_INT
        or coordinate <= _ZERO
        or coordinate >= _GF_SIZE
    ):
        message = "source-binding share coordinate is outside GF(256)"
        raise SourceBindingError(message)
    if (
        _NATIVE_TYPE(_share_masked(share)) is not _NATIVE_BYTES
        or _NATIVE_LEN(_share_masked(share)) != secret_length
    ):
        message = "source-binding masked share length is invalid"
        raise SourceBindingError(message)


def _validate_bound_share(share: BoundShare, *, secret_length: int) -> None:
    if _NATIVE_TYPE(share) is not BoundShare:
        message = "source-binding share must use the exact BoundShare type"
        raise SourceBindingError(message)
    _validate_share_path(_share_path(share))
    _validate_share_payload(share, secret_length)


def _validate_binding_counts(binding: ThresholdBinding) -> None:
    threshold = _binding_threshold(binding)
    if _NATIVE_TYPE(threshold) is not _NATIVE_INT or threshold <= _ZERO:
        message = "source-binding threshold must be a positive integer"
        raise SourceBindingError(message)
    if (
        _NATIVE_TYPE(_binding_minimum_files(binding)) is not _NATIVE_INT
        or _binding_minimum_files(binding) <= _ZERO
    ):
        message = "source-binding minimum anchor files must be a positive integer"
        raise SourceBindingError(message)
    if _binding_threshold(binding) < _binding_minimum_files(binding):
        message = "source-binding threshold must reach minimum anchor files"
        raise SourceBindingError(message)


def _validate_binding_secret(binding: ThresholdBinding) -> None:
    context = _binding_context(binding)
    if _NATIVE_TYPE(context) is not _NATIVE_BYTES or not context:
        message = "source-binding context must be non-empty bytes"
        raise SourceBindingError(message)
    if (
        _NATIVE_TYPE(_binding_secret_length(binding)) is not _NATIVE_INT
        or _binding_secret_length(binding) <= _ZERO
        or _binding_secret_length(binding) > _HKDF_MAX_BLOCKS * _SHA256_BYTES
    ):
        message = "source-binding secret length is invalid"
        raise SourceBindingError(message)
    if (
        _NATIVE_TYPE(_binding_commitment(binding)) is not _NATIVE_BYTES
        or _NATIVE_LEN(_binding_commitment(binding)) != _SHA256_BYTES
    ):
        message = "source-binding secret commitment must be 32 bytes"
        raise SourceBindingError(message)


def _validate_binding_header(binding: ThresholdBinding) -> None:
    _validate_binding_counts(binding)
    _validate_binding_secret(binding)
    if _NATIVE_TYPE(_binding_anchor_policy(binding)) is not AnchorPolicy:
        message = "source-binding anchor policy must use the exact AnchorPolicy type"
        raise SourceBindingError(message)
    if not _valid_anchor_policy_fields(_binding_anchor_policy(binding)):
        message = "source-binding anchor policy requires positive exact integers"
        raise SourceBindingError(message)


def _validate_binding_extent(binding: ThresholdBinding) -> None:
    shares = _binding_shares(binding)
    if _NATIVE_TYPE(shares) is not _NATIVE_TUPLE or not shares:
        message = "source binding must contain an immutable non-empty share set"
        raise SourceBindingError(message)
    if _NATIVE_LEN(_binding_shares(binding)) > _MAX_SHARES:
        message = "source-binding share set exceeds the supported maximum"
        raise SourceBindingError(message)
    if _binding_threshold(binding) > _NATIVE_LEN(_binding_shares(binding)):
        message = "source-binding threshold exceeds the available share set"
        raise SourceBindingError(message)
    if _binding_minimum_files(binding) > _NATIVE_LEN(_binding_shares(binding)):
        message = "source-binding minimum anchor files exceeds the share set"
        raise SourceBindingError(message)


def _require_possible_share_paths(source_paths: set[str]) -> None:
    if _NATIVE_ANY(
        "/".join(parts[:index]) in source_paths
        for path in source_paths
        for parts in (path.split("/"),)
        for index in _NATIVE_RANGE(1, _NATIVE_LEN(parts))
    ):
        message = "source-binding share paths contain an ancestor/descendant overlap"
        raise SourceBindingError(message)


def _validate_binding_shares(binding: ThresholdBinding) -> None:
    x_values: set[int] = _NATIVE_SET()
    anchor_keys: set[tuple[str, bytes]] = _NATIVE_SET()
    source_paths: set[str] = _NATIVE_SET()
    for share in _binding_shares(binding):
        _validate_bound_share(
            share, secret_length=_binding_secret_length(binding)
        )
        if _share_x(share) in x_values:
            message = "source-binding share coordinates must be unique"
            raise SourceBindingError(message)
        anchor_key = (_share_path(share), _share_digest(share))
        if anchor_key in anchor_keys:
            message = "source-binding share anchors must be unique"
            raise SourceBindingError(message)
        x_values.add(_share_x(share))
        anchor_keys.add(anchor_key)
        source_paths.add(_share_path(share))
    _require_possible_share_paths(source_paths)
    if _binding_minimum_files(binding) > _NATIVE_LEN(source_paths):
        message = "source-binding minimum anchor files exceeds represented files"
        raise SourceBindingError(message)


def _validate_binding(binding: ThresholdBinding) -> ThresholdBinding:
    if _NATIVE_TYPE(binding) is not ThresholdBinding:
        message = "source binding must use the exact ThresholdBinding type"
        raise SourceBindingError(message)
    _validate_binding_header(binding)
    _validate_binding_extent(binding)
    _validate_binding_shares(binding)
    return binding


def validate_threshold_binding(
    binding: ThresholdBinding,
) -> ThresholdBinding:
    """Validate one distributable threshold-binding envelope.

    Returns:
        The admitted binding unchanged.

    """
    return _validate_binding(binding)


def _candidate_materials(
    candidate: IdentityTree,
    policy: AnchorPolicy,
) -> dict[tuple[str, bytes], _AnchorMaterial]:
    materials: dict[tuple[str, bytes], _AnchorMaterial] = {}
    for identity_file in _identity_files(candidate):
        for material in _file_anchor_materials(identity_file, policy):
            materials[
                _anchor_path(material), _anchor_digest(material)
            ] = material
    return materials


def _recover_available_shares(
    binding: ThresholdBinding,
    candidate: IdentityTree,
) -> tuple[_RecoveredShare, ...]:
    candidate_materials = _candidate_materials(
        candidate, _binding_anchor_policy(binding)
    )
    available: list[_RecoveredShare] = []
    for bound in _binding_shares(binding):
        material = candidate_materials.get(
            (
                _share_path(bound),
                _share_digest(bound),
            )
        )
        if material is None:
            continue
        mask = _share_mask(
            material,
            _binding_context(binding),
            x=_share_x(bound),
            length=_binding_secret_length(binding),
        )
        available.append(
            _new_recovered_share(
                source_path=_share_path(bound),
                x=_share_x(bound),
                value=_xor_bytes(_share_masked(bound), mask),
            )
        )
    return _NATIVE_TUPLE(available)


def _require_recovery_distribution(
    binding: ThresholdBinding,
    available: tuple[_RecoveredShare, ...],
) -> None:
    available_files = {_recovered_path(share) for share in available}
    if _NATIVE_LEN(available_files) < _binding_minimum_files(binding):
        message = (
            "insufficient distributed source-bound files: "
            f"need {_binding_minimum_files(binding)}, "
            f"found {_NATIVE_LEN(available_files)}"
        )
        raise SourceBindingError(message)


def _select_distributed_quorum(
    binding: ThresholdBinding,
    available: tuple[_RecoveredShare, ...],
) -> tuple[_RecoveredShare, ...]:
    """Select a threshold including material from required distinct files.

    Returns:
        Deterministic quorum with the minimum file diversity represented.

    """
    first_by_file: dict[str, _RecoveredShare] = {}
    for share in available:
        if _recovered_path(share) not in first_by_file:
            first_by_file[_recovered_path(share)] = share
    required_files = _binding_minimum_files(binding)
    distributed = _NATIVE_TUPLE(first_by_file.values())[:required_files]
    chosen_x = {_recovered_x(share) for share in distributed}
    remaining = _NATIVE_TUPLE(
        share for share in available if _recovered_x(share) not in chosen_x
    )
    remaining_count = _binding_threshold(binding) - _NATIVE_LEN(distributed)
    return (*distributed, *remaining[:remaining_count])


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
    admitted = validate_threshold_binding(binding)
    if _NATIVE_TYPE(candidate) is not IdentityTree:
        message = "source-binding candidate must use the exact IdentityTree type"
        raise SourceBindingError(message)
    available = _recover_available_shares(admitted, candidate)
    if _NATIVE_LEN(available) < _binding_threshold(admitted):
        message = (
            "insufficient source-bound anchors: "
            f"need {_binding_threshold(admitted)}, "
            f"found {_NATIVE_LEN(available)}"
        )
        raise SourceBindingError(message)
    _require_recovery_distribution(admitted, available)
    raw_shares = _NATIVE_TUPLE(
        (_recovered_x(share), _recovered_value(share))
        for share in _select_distributed_quorum(admitted, available)
    )
    secret = _recover_shares(raw_shares)
    if _secret_commitment(
        _binding_context(admitted), secret
    ) != _binding_commitment(admitted):
        message = "recovered source-bound secret failed commitment"
        raise SourceBindingError(message)
    return secret
