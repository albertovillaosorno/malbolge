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
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256 as _native_sha256
from typing import TYPE_CHECKING

from algorithms.diff.admission import IdentityTree
from algorithms.diff.fingerprints import AnchorPolicy, stable_anchors

if TYPE_CHECKING:
    from algorithms.diff.admission import IdentityFile
    from algorithms.diff.fingerprints import StableAnchor

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
        _ = _binding_fraction(self.threshold_fraction)
        maximum = _binding_positive_int(
            self.maximum_anchors, "maximum_anchors", _MAX_SHARES
        )
        minimum = _binding_positive_int(
            self.minimum_anchor_files, "minimum_anchor_files", None
        )
        if minimum > maximum:
            message = "minimum_anchor_files cannot exceed maximum_anchors"
            raise SourceBindingPolicyError(message)
        if _NATIVE_TYPE(self.anchor_policy) is not AnchorPolicy:
            message = "anchor_policy must use the exact AnchorPolicy type"
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
    if _NATIVE_LEN(identity_file.canonical) < policy.window_bytes:
        return identity_file.canonical
    end = anchor.offset + policy.window_bytes
    return identity_file.canonical[anchor.offset : end]


def _file_anchor_materials(
    identity_file: IdentityFile,
    policy: AnchorPolicy,
) -> tuple[_AnchorMaterial, ...]:
    anchors = _NATIVE_SORTED(
        stable_anchors(identity_file.canonical, policy),
        key=lambda anchor: anchor.digest,
    )
    return _NATIVE_TUPLE(
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
    return _NATIVE_TUPLE(
        materials
        for identity_file in reference.files
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
    selected_files = {item.source_path for item in selected}
    if _NATIVE_LEN(selected_files) < minimum_anchor_files:
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
    drives = (_has_windows_drive(item.path) for item in reference.files)
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
    # Interpret the configured float's canonical decimal as the policy value.
    # A float product can round a fraction just above k/N back to k and admit
    # fewer shares than required. Integer arithmetic keeps the ceiling exact.
    fraction_value = _binding_fraction(policy.threshold_fraction)
    fraction = Decimal(_NATIVE_STR(fraction_value))
    fraction_numerator, fraction_denominator = fraction.as_integer_ratio()
    numerator = _NATIVE_LEN(materials) * fraction_numerator
    threshold = _NATIVE_MAX(
        _ONE,
        (numerator + fraction_denominator - _ONE) // fraction_denominator,
    )
    if threshold < policy.minimum_anchor_files:
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
                    length=_NATIVE_LEN(secret),
                ),
            ),
        )
        for material, (x, share) in paired
    )
    return ThresholdBinding(
        context=context,
        threshold=threshold,
        minimum_anchor_files=policy.minimum_anchor_files,
        secret_length=_NATIVE_LEN(secret),
        secret_commitment=_secret_commitment(context, secret),
        anchor_policy=policy.anchor_policy,
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
        _NATIVE_TYPE(share.anchor_digest) is not _NATIVE_BYTES
        or _NATIVE_LEN(share.anchor_digest) != _SHA256_BYTES
    ):
        message = "source-binding anchor digest must be 32 bytes"
        raise SourceBindingError(message)
    coordinate = share.x
    if (
        _NATIVE_TYPE(coordinate) is not _NATIVE_INT
        or coordinate <= _ZERO
        or coordinate >= _GF_SIZE
    ):
        message = "source-binding share coordinate is outside GF(256)"
        raise SourceBindingError(message)
    if (
        _NATIVE_TYPE(share.masked_share) is not _NATIVE_BYTES
        or _NATIVE_LEN(share.masked_share) != secret_length
    ):
        message = "source-binding masked share length is invalid"
        raise SourceBindingError(message)


def _validate_bound_share(share: BoundShare, *, secret_length: int) -> None:
    if _NATIVE_TYPE(share) is not BoundShare:
        message = "source-binding share must use the exact BoundShare type"
        raise SourceBindingError(message)
    _validate_share_path(share.source_path)
    _validate_share_payload(share, secret_length)


def _validate_binding_counts(binding: ThresholdBinding) -> None:
    threshold = binding.threshold
    if _NATIVE_TYPE(threshold) is not _NATIVE_INT or threshold <= _ZERO:
        message = "source-binding threshold must be a positive integer"
        raise SourceBindingError(message)
    if (
        _NATIVE_TYPE(binding.minimum_anchor_files) is not _NATIVE_INT
        or binding.minimum_anchor_files <= _ZERO
    ):
        message = "source-binding minimum anchor files must be a positive integer"
        raise SourceBindingError(message)
    if binding.threshold < binding.minimum_anchor_files:
        message = "source-binding threshold must reach minimum anchor files"
        raise SourceBindingError(message)


def _validate_binding_secret(binding: ThresholdBinding) -> None:
    context = binding.context
    if _NATIVE_TYPE(context) is not _NATIVE_BYTES or not context:
        message = "source-binding context must be non-empty bytes"
        raise SourceBindingError(message)
    if (
        _NATIVE_TYPE(binding.secret_length) is not _NATIVE_INT
        or binding.secret_length <= _ZERO
        or binding.secret_length > _HKDF_MAX_BLOCKS * _SHA256_BYTES
    ):
        message = "source-binding secret length is invalid"
        raise SourceBindingError(message)
    if (
        _NATIVE_TYPE(binding.secret_commitment) is not _NATIVE_BYTES
        or _NATIVE_LEN(binding.secret_commitment) != _SHA256_BYTES
    ):
        message = "source-binding secret commitment must be 32 bytes"
        raise SourceBindingError(message)


def _validate_binding_header(binding: ThresholdBinding) -> None:
    _validate_binding_counts(binding)
    _validate_binding_secret(binding)
    if _NATIVE_TYPE(binding.anchor_policy) is not AnchorPolicy:
        message = "source-binding anchor policy must use the exact AnchorPolicy type"
        raise SourceBindingError(message)


def _validate_binding_extent(binding: ThresholdBinding) -> None:
    if _NATIVE_TYPE(binding.shares) is not _NATIVE_TUPLE or not binding.shares:
        message = "source binding must contain an immutable non-empty share set"
        raise SourceBindingError(message)
    if _NATIVE_LEN(binding.shares) > _MAX_SHARES:
        message = "source-binding share set exceeds the supported maximum"
        raise SourceBindingError(message)
    if binding.threshold > _NATIVE_LEN(binding.shares):
        message = "source-binding threshold exceeds the available share set"
        raise SourceBindingError(message)
    if binding.minimum_anchor_files > _NATIVE_LEN(binding.shares):
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
    for share in binding.shares:
        _validate_bound_share(share, secret_length=binding.secret_length)
        if share.x in x_values:
            message = "source-binding share coordinates must be unique"
            raise SourceBindingError(message)
        anchor_key = (share.source_path, share.anchor_digest)
        if anchor_key in anchor_keys:
            message = "source-binding share anchors must be unique"
            raise SourceBindingError(message)
        x_values.add(share.x)
        anchor_keys.add(anchor_key)
        source_paths.add(share.source_path)
    _require_possible_share_paths(source_paths)
    if binding.minimum_anchor_files > _NATIVE_LEN(source_paths):
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
        material = candidate_materials.get(
            (
                bound.source_path,
                bound.anchor_digest,
            )
        )
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
    return _NATIVE_TUPLE(available)


def _require_recovery_distribution(
    binding: ThresholdBinding,
    available: tuple[_RecoveredShare, ...],
) -> None:
    available_files = {share.source_path for share in available}
    if _NATIVE_LEN(available_files) < binding.minimum_anchor_files:
        message = (
            "insufficient distributed source-bound files: "
            f"need {binding.minimum_anchor_files}, "
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
        if share.source_path not in first_by_file:
            first_by_file[share.source_path] = share
    required_files = binding.minimum_anchor_files
    distributed = _NATIVE_TUPLE(first_by_file.values())[:required_files]
    chosen_x = {share.x for share in distributed}
    remaining = _NATIVE_TUPLE(s for s in available if s.x not in chosen_x)
    remaining_count = binding.threshold - _NATIVE_LEN(distributed)
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
    if _NATIVE_LEN(available) < admitted.threshold:
        message = (
            "insufficient source-bound anchors: "
            f"need {admitted.threshold}, found {_NATIVE_LEN(available)}"
        )
        raise SourceBindingError(message)
    _require_recovery_distribution(admitted, available)
    raw_shares = _NATIVE_TUPLE(
        (share.x, share.value)
        for share in _select_distributed_quorum(admitted, available)
    )
    secret = _recover_shares(raw_shares)
    if _secret_commitment(admitted.context, secret) != admitted.secret_commitment:
        message = "recovered source-bound secret failed commitment"
        raise SourceBindingError(message)
    return secret
