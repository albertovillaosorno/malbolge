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
#   - Synthetic tests for deterministic threshold source binding.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for deterministic threshold source binding."""

import builtins
import hashlib
import hmac
import itertools
import math
import ntpath
import os
import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import replace
from pathlib import PurePosixPath, PureWindowsPath
from types import MemberDescriptorType, SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from algorithms.diff import source_binding as binding_module
from algorithms.diff.admission import AdmissionPolicyError, IdentityTree, identity_tree
from algorithms.diff.fingerprints import AnchorPolicy, StableAnchor
from algorithms.diff.source_binding import (
    SourceBindingError,
    SourceBindingPolicy,
    SourceBindingPolicyError,
    bind_secret,
    hkdf_expand_sha256,
    hkdf_extract_sha256,
    recover_secret,
    validate_threshold_binding,
)

if TYPE_CHECKING:
    from collections.abc import Sized

    from algorithms.diff.source_binding import BoundShare, ThresholdBinding

_SECRET = hashlib.sha256(b"synthetic high-entropy payload key").digest()
_CONTEXT = b"synthetic-source-binding-v1"
_FILE_COUNT = 5
_BLOCKS_PER_FILE = 64
_DEFAULT_THRESHOLD = 3
_STRICT_THRESHOLD = 5
_HMAC_DIGEST_METHOD = "digest"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _files(label: str) -> dict[str, bytes]:
    return {
        f"src/file-{file_index}.c": b"".join(
            hashlib.sha256(f"{label}:{file_index}:{block_index}".encode()).digest()
            for block_index in range(_BLOCKS_PER_FILE)
        )
        for file_index in range(_FILE_COUNT)
    }


def _policy(*, threshold_fraction: float = 0.60) -> SourceBindingPolicy:
    return SourceBindingPolicy(
        threshold_fraction=threshold_fraction,
        maximum_anchors=_FILE_COUNT,
        minimum_anchor_files=3,
        anchor_policy=AnchorPolicy(window_bytes=16, selection_modulus=1),
    )


def _reference() -> IdentityTree:
    return identity_tree(_files("reference"))


def _candidate_paths(reference: IdentityTree, paths: tuple[str, ...]) -> IdentityTree:
    by_path = {item.path: item.canonical for item in reference.files}
    return identity_tree({path: by_path[path] for path in paths})


@pytest.mark.parametrize("foreign_role", ["envelope", "share"])
def test_binding_rejects_late_type_foreign_records(
    monkeypatch: pytest.MonkeyPatch, foreign_role: str
) -> None:
    """Late type replacement cannot admit structural imitations of records."""
    valid = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    native_type = builtins.type
    first = valid.shares[0]
    shape = SimpleNamespace(
        source_path=first.source_path,
        anchor_digest=first.anchor_digest,
        x=first.x,
        masked_share=first.masked_share,
    )
    if foreign_role == "share":
        foreign_share = cast("BoundShare", cast("object", shape))
        foreign = replace(
            valid, shares=(foreign_share, *valid.shares[1:])
        )
    else:
        foreign = cast(
            "ThresholdBinding",
            cast(
                "object",
                SimpleNamespace(
                    context=valid.context,
                    threshold=valid.threshold,
                    minimum_anchor_files=valid.minimum_anchor_files,
                    secret_length=valid.secret_length,
                    secret_commitment=valid.secret_commitment,
                    anchor_policy=valid.anchor_policy,
                    shares=valid.shares,
                ),
            ),
        )

    def forged_type(value: object) -> type[object]:
        if native_type(value) is SimpleNamespace:
            if foreign_role == "envelope":
                return native_type(valid)
            return native_type(first)
        return native_type(value)

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = validate_threshold_binding(foreign)
        except SourceBindingError:
            rejected = True
    assert rejected, f"late type hook admitted a foreign {foreign_role} record"


@pytest.mark.parametrize("field", ["anchor_digest", "masked_share"])
def test_binding_rejects_late_len_spoof_of_share_bytes(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """A late length hook cannot certify undersized source-binding shares."""
    valid = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    first = valid.shares[0]
    malformed = cast("bytes", getattr(first, field))[:-1]
    forged = replace(
        valid,
        shares=(replace(first, **{field: malformed}), *valid.shares[1:]),
    )
    native_len = builtins.len

    def spoof_len(value: object) -> int:
        if value is malformed:
            return native_len(malformed) + 1
        return native_len(cast("Sized", value))

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "len", spoof_len)
        try:
            _ = validate_threshold_binding(forged)
        except SourceBindingError:
            rejected = True
    assert rejected, f"late len hook admitted undersized {field}"


def test_binding_policy_rejects_late_int_spoof_of_boolean_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boolean source-binding limits must not masquerade as native integers."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "int", bool)
        try:
            _ = SourceBindingPolicy(
                threshold_fraction=0.6,
                maximum_anchors=True,
                minimum_anchor_files=True,
            )
        except SourceBindingPolicyError:
            rejected = True
    assert rejected, "late int hook admitted boolean anchor limits"


def test_binding_threshold_ignores_late_str_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late numeric string hook cannot lower the source quorum."""
    reference = _reference()
    policy = _policy(threshold_fraction=0.8)
    expected = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    def forged_str(_value: object) -> str:
        return "0.2"

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "str", forged_str)
        observed = bind_secret(
            reference, _SECRET, policy=policy, context=_CONTEXT
        )
    assert observed.threshold == expected.threshold


@pytest.mark.parametrize("hook", ["slot", "getattribute"])
@pytest.mark.parametrize(
    ("field", "forged"),
    [
        ("threshold_fraction", 0.6),
        ("maximum_anchors", 4),
        ("minimum_anchor_files", 1),
        ("anchor_policy", AnchorPolicy(window_bytes=32, selection_modulus=8)),
    ],
)
def test_binding_policy_ignores_late_field_forgery(
    monkeypatch: pytest.MonkeyPatch, hook: str, field: str, forged: object
) -> None:
    """A consumer cannot relax the binding policy via a mutable class hook."""
    reference = _reference()
    policy = _policy(threshold_fraction=0.8)
    expected = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    original_getattribute = SourceBindingPolicy.__getattribute__
    calls = 0

    def forged_attribute(value: SourceBindingPolicy, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return forged
        return original_getattribute(value, name)

    def forged_slot(_value: SourceBindingPolicy) -> object:
        nonlocal calls
        calls += 1
        return forged

    with monkeypatch.context() as patched:
        if hook == "slot":
            patched.setattr(SourceBindingPolicy, field, property(forged_slot))
        else:
            patched.setattr(
                SourceBindingPolicy, "__getattribute__", forged_attribute
            )
        observed = bind_secret(
            reference, _SECRET, policy=policy, context=_CONTEXT
        )
    assert observed == expected
    assert calls == 0, "late policy hook participated in source binding"


@pytest.mark.parametrize("field", ["files", "path", "canonical"])
@pytest.mark.parametrize("hook", ["slot", "getattribute"])
def test_binding_uses_stored_source_identity_after_late_hooks(
    monkeypatch: pytest.MonkeyPatch, field: str, hook: str
) -> None:
    """Late identity getters cannot redirect key binding to foreign bytes."""
    reference = _reference()
    policy = _policy()
    expected = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    first = reference.files[0]
    if field == "files":
        owner = type(reference)
        target = reference
        forged: object = identity_tree(_files("foreign")).files
    else:
        owner = type(first)
        target = first
        forged = "src/forged.c" if field == "path" else b"forged" * 512
    original_slot = owner.__dict__[field]

    def forged_getattr(value: object, name: str) -> object:
        if name == field and value is target:
            return forged
        return object.__getattribute__(value, name)

    def forged_slot(value: object) -> object:
        if value is target:
            return forged
        return original_slot.__get__(value, owner)

    with monkeypatch.context() as patched:
        if hook == "slot":
            patched.setattr(owner, field, property(forged_slot))
        else:
            patched.setattr(owner, "__getattribute__", forged_getattr)
        observed = bind_secret(
            reference, _SECRET, policy=policy, context=_CONTEXT
        )
    assert observed == expected


@pytest.mark.parametrize("field", ["files", "path", "canonical"])
def test_recovery_uses_stored_candidate_source_identity(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """A valid candidate cannot be hidden by late source-record hooks."""
    reference = _reference()
    binding = bind_secret(
        reference, _SECRET, policy=_policy(), context=_CONTEXT
    )
    if field == "files":
        owner = type(reference)
        forged: object = identity_tree(_files("foreign")).files
    else:
        owner = type(reference.files[0])
        forged = "src/forged.c" if field == "path" else b"forged" * 512
    original_slot = owner.__dict__[field]

    def forged_slot(value: object) -> object:
        if field == "files" and value is not reference:
            return original_slot.__get__(value, owner)
        return forged

    with monkeypatch.context() as patched:
        patched.setattr(owner, field, property(forged_slot))
        assert recover_secret(binding, reference) == _SECRET


@pytest.mark.parametrize(
    ("field", "forged"),
    [
        ("source_path", "src/forged.c"),
        ("digest", b"forged"),
        ("window", b"forged source bytes"),
    ],
)
def test_anchor_material_ignores_late_getter_forgery(
    monkeypatch: pytest.MonkeyPatch, field: str, forged: object
) -> None:
    """An internal anchor getter must not redefine masked secret shares."""
    reference = _reference()
    policy = _policy()
    expected = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    anchor_type = vars(binding_module)["_AnchorMaterial"]

    def forged_getattr(value: object, name: str) -> object:
        if name == field:
            return forged
        return object.__getattribute__(value, name)

    with monkeypatch.context() as patched:
        patched.setattr(anchor_type, "__getattribute__", forged_getattr)
        observed = bind_secret(
            reference, _SECRET, policy=policy, context=_CONTEXT
        )
    assert observed == expected


@pytest.mark.parametrize(
    ("field", "forged"),
    [
        ("source_path", "src/forged.c"),
        ("x", 17),
        ("value", b"forged recovered share"),
    ],
)
def test_recovered_share_ignores_late_getter_forgery(
    monkeypatch: pytest.MonkeyPatch, field: str, forged: object
) -> None:
    """A late in-memory receipt getter cannot change a verified quorum."""
    reference = _reference()
    binding = bind_secret(
        reference, _SECRET, policy=_policy(), context=_CONTEXT
    )
    recovered_type = vars(binding_module)["_RecoveredShare"]

    def forged_getattr(value: object, name: str) -> object:
        if name == field:
            return forged
        return object.__getattribute__(value, name)

    with monkeypatch.context() as patched:
        patched.setattr(recovered_type, "__getattribute__", forged_getattr)
        assert recover_secret(binding, reference) == _SECRET


@pytest.mark.parametrize(
    ("role", "field", "forged"),
    [
        ("anchor", "digest", b"forged"),
        ("anchor", "offset", 0),
        ("policy", "window_bytes", 1),
    ],
)
def test_anchor_windows_ignore_late_class_getters(
    monkeypatch: pytest.MonkeyPatch, role: str, field: str, forged: object
) -> None:
    """Imported anchor records cannot redirect authenticated source windows."""
    reference = _reference()
    policy = _policy()
    expected = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    if role == "anchor":
        owner = StableAnchor
    else:
        owner = AnchorPolicy

    def forged_getattr(value: object, name: str) -> object:
        if name == field:
            return forged
        return object.__getattribute__(value, name)

    with monkeypatch.context() as patched:
        patched.setattr(owner, "__getattribute__", forged_getattr)
        observed = bind_secret(
            reference, _SECRET, policy=policy, context=_CONTEXT
        )
    assert observed == expected


def test_binding_policy_validation_rejects_late_getattribute_forgery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Constructor validation must inspect raw numeric policy slots."""
    original_getattribute = SourceBindingPolicy.__getattribute__

    def forged_attribute(value: SourceBindingPolicy, name: str) -> object:
        if name == "maximum_anchors":
            return 5
        return original_getattribute(value, name)

    with monkeypatch.context() as patched:
        patched.setattr(
            SourceBindingPolicy, "__getattribute__", forged_attribute
        )
        with pytest.raises(SourceBindingPolicyError, match="positive integer"):
            _ = SourceBindingPolicy(threshold_fraction=0.6, maximum_anchors=True)


def test_hkdf_expand_ignores_late_range_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late loop hook cannot suppress output key-schedule blocks."""
    expected = hkdf_expand_sha256(b"k" * 32, b"source", 64)
    def forged_range(*_args: object) -> tuple[()]:
        return ()

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "range", forged_range)
        observed = hkdf_expand_sha256(b"k" * 32, b"source", 64)
    assert observed == expected


def test_hkdf_expand_ignores_late_ceil_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An overridden math helper cannot erase HKDF output blocks."""
    expected = hkdf_expand_sha256(b"k" * 32, b"source", 64)
    def forged_ceil(_value: object) -> int:
        return 0

    with monkeypatch.context() as patched:
        patched.setattr(math, "ceil", forged_ceil)
        observed = hkdf_expand_sha256(b"k" * 32, b"source", 64)
    assert observed == expected


def test_binding_policy_rejects_late_isfinite_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nonfinite threshold policies cannot be admitted by a late math hook."""
    rejected = False
    def forged_isfinite(_value: object) -> bool:
        return True

    with monkeypatch.context() as patched:
        patched.setattr(math, "isfinite", forged_isfinite)
        try:
            _ = SourceBindingPolicy(threshold_fraction=float("nan"))
        except SourceBindingPolicyError:
            rejected = True
    assert rejected, "late finite predicate admitted an invalid threshold"


def test_binding_shares_ignore_late_enumerate_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late iterator hook cannot erase generated Shamir coefficients."""
    reference = _reference()
    policy = _policy()
    expected = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)

    def forged_enumerate(_value: object) -> tuple[()]:
        return ()

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "enumerate", forged_enumerate)
        observed = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    assert observed == expected


def test_binding_rejects_late_tuple_spoof_of_mutable_shares(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutable share list cannot become an authenticated share tuple."""
    valid = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    forged = replace(
        valid,
        shares=cast("tuple[BoundShare, ...]", cast("object", list(valid.shares))),
    )
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "tuple", list)
        try:
            _ = validate_threshold_binding(forged)
        except SourceBindingError:
            rejected = True
    assert rejected, "late tuple hook admitted mutable share metadata"


def test_binding_share_path_rejects_late_any_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late any hook cannot admit a source share path with traversal."""
    binding = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    forged = replace(
        binding,
        shares=(
            replace(binding.shares[0], source_path="src/../escape.c"),
            *binding.shares[1:],
        ),
    )
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda values: False)
        try:
            _ = validate_threshold_binding(forged)
        except SourceBindingError:
            rejected = True
    assert rejected, "late any hook admitted a traversing share path"


def test_recovery_coordinates_reject_late_set_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged set cannot certify duplicate Shamir share coordinates."""
    validate = cast(
        "Callable[[tuple[tuple[int, bytes], ...]], object]",
        vars(binding_module)["_validate_recovery_shares"],
    )
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "set", lambda values: list(values))
        try:
            _ = validate(((1, b"a"), (1, b"b")))
        except SourceBindingError:
            rejected = True
    assert rejected, "late set hook admitted duplicate share coordinates"


def test_binding_mask_xor_resists_late_zip_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged zipper cannot erase bytes from a source-bound key mask."""
    xor_bytes = cast(
        "Callable[[bytes, bytes], bytes]", vars(binding_module)["_xor_bytes"]
    )
    expected = xor_bytes(b"alpha", b"omega")
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "zip", lambda *args, **kwargs: ())
        observed = xor_bytes(b"alpha", b"omega")
    assert observed == expected, "late zip hook truncated key-mask output"


def test_hkdf_resists_late_bytearray_collector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign collector cannot replace key-schedule bytes."""
    native_buffer = builtins.bytearray

    class _ZeroCollector:
        def __init__(self) -> None:
            self.data = native_buffer()

        def extend(self, data: bytes) -> None:
            self.data.extend(b"\0" * len(data))

        def __getitem__(self, index: slice) -> bytearray:
            return self.data[index]

    expected = hkdf_expand_sha256(b"k" * 32, b"source mask", 32)
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bytearray", _ZeroCollector)
        observed = hkdf_expand_sha256(b"k" * 32, b"source mask", 32)
    assert observed == expected, "late collector changed HKDF key schedule"


def test_hkdf_ignores_late_bytes_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late bytes binding cannot override an imported KDF constructor."""
    expected = hkdf_expand_sha256(b"k" * 32, b"source mask", 32)
    observed: bytes | None = None
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bytes", lambda value: b"x" * 32)
        try:
            observed = hkdf_expand_sha256(b"k" * 32, b"source mask", 32)
        except SourceBindingPolicyError:
            pass
    assert observed == expected, "late bytes hook changed HKDF admission"


def test_hkdf_sha256_matches_rfc5869_test_case_1() -> None:
    """Lock HKDF implementation to the RFC 5869 SHA-256 test vector."""
    input_key_material = bytes.fromhex("0b" * 22)
    salt = bytes.fromhex("000102030405060708090a0b0c")
    info = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9")
    expected_prk = bytes.fromhex(
        "077709362c2e32df0ddc3f0dc47bba6390b6c73bb50f9c3122ec844ad7c2b3e5"
    )
    expected_okm_parts = (
        "3cb25f25faacd57a90434f64d0362f2a",
        "2d2d0a90cf1a5a4c5db02d56ecc4c5bf",
        "34007208d5b887185865",
    )
    expected_okm = bytes.fromhex("".join(expected_okm_parts))

    pseudorandom_key = hkdf_extract_sha256(salt, input_key_material)
    output = hkdf_expand_sha256(pseudorandom_key, info, 42)

    _expect(pseudorandom_key == expected_prk, "HKDF extract vector changed")
    _expect(output == expected_okm, "HKDF expand vector changed")


@pytest.mark.parametrize("salt_length", [0, 1, 63, 64, 65, 256])
def test_hkdf_extract_matches_independent_hmac_across_key_lengths(
    salt_length: int,
) -> None:
    """The SHA-256 implementation preserves RFC 2104 HMAC key normalization."""
    salt = bytes(index % 256 for index in range(salt_length))
    input_key_material = b"independent HMAC-SHA-256 cross-check"
    expected = hmac.digest(
        salt or bytes(32), input_key_material, hashlib.sha256
    )
    _expect(
        hkdf_extract_sha256(salt, input_key_material) == expected,
        "HKDF extract differs from standard-library HMAC",
    )


def test_hkdf_ignores_replaced_global_sha256_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign digest constructor cannot rewrite the RFC 5869 key schedule."""
    ikm = bytes.fromhex("0b" * 22)
    salt = bytes.fromhex("000102030405060708090a0b0c")
    info = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9")
    reference_prk = hkdf_extract_sha256(salt, ikm)
    reference_okm = hkdf_expand_sha256(reference_prk, info, 42)
    calls = 0

    def forged_hash(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        message = "mutable SHA-256 constructor evaluated"
        raise AssertionError(message)

    monkeypatch.setattr(hashlib, "sha256", forged_hash)
    _expect(hkdf_extract_sha256(salt, ikm) == reference_prk, "HKDF extract changed")
    _expect(
        hkdf_expand_sha256(reference_prk, info, 42) == reference_okm,
        "HKDF expand changed",
    )
    _expect(calls == 0, "mutable digest constructor was consulted")


def test_bound_shares_ignore_replaced_global_hmac_constructor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Untrusted domain hooks cannot expose the plaintext secret as masked shares."""
    reference = _reference()
    calls = 0

    class _ZeroDigest:
        def digest(self) -> bytes:
            return bytes(32)

    def forge_hmac(
        _key: bytes,
        _message: bytes,
        _digestmod: object,
    ) -> _ZeroDigest:
        nonlocal calls
        calls += 1
        return _ZeroDigest()

    monkeypatch.setattr(hmac, "new", forge_hmac)
    monkeypatch.setattr(hmac, "HMAC", forge_hmac)
    binding = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)
    _expect(
        all(share.masked_share != _SECRET for share in binding.shares),
        "replaced HMAC made distributable masked shares expose the secret",
    )
    _expect(calls == 0, "mutable global HMAC constructor was consulted")
    _expect(recover_secret(binding, reference) == _SECRET, "valid binding changed")


@pytest.mark.parametrize("method", ["digest", "_current"])
def test_bound_shares_ignore_replaced_hmac_class_methods(
    monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    """A late HMAC method swap must not expose plaintext threshold shares."""
    reference = _reference()
    policy = _policy()
    expected = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    calls = 0

    class _ZeroDigest:
        @staticmethod
        def digest() -> bytes:
            return bytes(32)

    def forged_method(_hmac: hmac.HMAC) -> bytes | _ZeroDigest:
        nonlocal calls
        del _hmac
        calls += 1
        if method == _HMAC_DIGEST_METHOD:
            return bytes(32)
        return _ZeroDigest()

    with monkeypatch.context() as patched:
        patched.setattr(hmac.HMAC, method, forged_method)
        actual = bind_secret(
            reference, _SECRET, policy=policy, context=_CONTEXT
        )
        _expect(actual == expected, "mutable HMAC changed bound shares")
        _expect(
            all(share.masked_share != _SECRET for share in actual.shares),
            "forged HMAC exposed the plaintext secret",
        )
        _expect(
            recover_secret(actual, reference) == _SECRET, "recovery changed"
        )
    _expect(calls == 0, "mutable HMAC method was evaluated")


def test_full_reference_recovers_bound_secret() -> None:
    """Recover key material from the exact canonical reference source."""
    reference = _reference()
    binding = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)

    recovered = recover_secret(binding, reference)

    _expect(recovered == _SECRET, "exact reference did not recover secret")
    _expect(binding.threshold == _DEFAULT_THRESHOLD, "synthetic threshold changed")
    _expect(len(binding.shares) == _FILE_COUNT, "binding share count changed")


def test_every_exact_threshold_file_combination_recovers() -> None:
    """Recover from every exact-threshold combination of source files."""
    reference = _reference()
    binding = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)
    paths = tuple(share.source_path for share in binding.shares)

    for selected in itertools.combinations(paths, binding.threshold):
        candidate = _candidate_paths(reference, selected)
        _expect(
            recover_secret(binding, candidate) == _SECRET,
            f"threshold combination failed: {selected!r}",
        )


def test_below_threshold_fails_before_secret_recovery() -> None:
    """Reject a candidate with one fewer bound source file than required."""
    reference = _reference()
    binding = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)
    selected = tuple(
        share.source_path for share in binding.shares[: binding.threshold - 1]
    )
    candidate = _candidate_paths(reference, selected)

    with pytest.raises(SourceBindingError, match="insufficient source-bound anchors"):
        _ = recover_secret(binding, candidate)


def test_empty_source_cannot_materialize_bound_secret() -> None:
    """Prove the distributable binding metadata is insufficient by itself."""
    binding = bind_secret(_reference(), _SECRET, policy=_policy(), context=_CONTEXT)

    with pytest.raises(SourceBindingError, match="insufficient source-bound anchors"):
        _ = recover_secret(binding, identity_tree({}))


def test_enough_shares_from_too_few_files_still_fails_closed() -> None:
    """Reject numerically sufficient shares concentrated in one source file."""
    reference = _reference()
    policy = SourceBindingPolicy(
        threshold_fraction=0.20,
        maximum_anchors=15,
        minimum_anchor_files=3,
        anchor_policy=AnchorPolicy(window_bytes=16, selection_modulus=1),
    )
    binding = bind_secret(
        reference,
        _SECRET,
        policy=policy,
        context=_CONTEXT,
    )
    concentrated_path = binding.shares[0].source_path
    candidate = _candidate_paths(reference, (concentrated_path,))

    with pytest.raises(
        SourceBindingError,
        match="insufficient distributed source-bound files",
    ):
        _ = recover_secret(binding, candidate)


def test_insertions_shift_offsets_without_breaking_bound_anchors() -> None:
    """Recover when unchanged source windows move to different byte offsets."""
    reference_files = _files("reference")
    reference = identity_tree(reference_files)
    binding = bind_secret(
        reference,
        _SECRET,
        policy=_policy(),
        context=_CONTEXT,
    )
    candidate = identity_tree(
        {path: b"inserted-prefix:" + data for path, data in reference_files.items()}
    )

    _expect(
        recover_secret(binding, candidate) == _SECRET,
        "offset-shifted stable anchors did not recover the secret",
    )


def test_unrelated_same_shape_source_cannot_recover_secret() -> None:
    """Reject unrelated canonical bytes with similar paths and sizes."""
    binding = bind_secret(_reference(), _SECRET, policy=_policy(), context=_CONTEXT)
    unrelated = identity_tree(_files("unrelated"))

    with pytest.raises(SourceBindingError, match="insufficient source-bound anchors"):
        _ = recover_secret(binding, unrelated)


def test_binding_is_deterministic_and_distributed() -> None:
    """Generate deterministic masked shares distributed across source files."""
    reference = _reference()
    first = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)
    second = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)

    _expect(first == second, "repeated source binding changed")
    selected_files = {share.source_path for share in first.shares}
    _expect(
        len(selected_files) == _FILE_COUNT,
        "binding concentrated in fewer files",
    )
    _expect(
        all(share.masked_share != _SECRET for share in first.shares),
        "binding stored plaintext secret as a share",
    )


def test_recovery_reconstructs_from_distributed_threshold_shares() -> None:
    """Do not count a distinct source file without using its share."""
    reference = _reference()
    policy = SourceBindingPolicy(
        threshold_fraction=0.20,
        maximum_anchors=15,
        minimum_anchor_files=2,
        anchor_policy=AnchorPolicy(window_bytes=16, selection_modulus=1),
    )
    binding = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    dominant_path = binding.shares[0].source_path
    dominant = tuple(
        share for share in binding.shares if share.source_path == dominant_path
    )
    minority = next(
        share for share in binding.shares if share.source_path != dominant_path
    )
    other = tuple(
        share
        for share in binding.shares
        if share.source_path != dominant_path and share != minority
    )
    _expect(
        len(dominant) >= binding.threshold,
        "synthetic test does not concentrate the threshold",
    )
    _expect(
        recover_secret(
            replace(binding, shares=(*dominant, minority, *other)),
            reference,
        )
        == _SECRET,
        "reordered genuine distributed binding did not recover",
    )

    malformed_share = replace(
        minority,
        masked_share=bytes([minority.masked_share[0] ^ 1]) + minority.masked_share[1:],
    )
    forged = replace(
        binding,
        shares=(*dominant, malformed_share, *other),
    )
    with pytest.raises(SourceBindingError, match="failed commitment"):
        _ = recover_secret(forged, reference)


def test_tampered_masked_share_fails_secret_commitment() -> None:
    """Reject malformed transform metadata rather than returning a wrong key."""
    reference = _reference()
    binding = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)
    first = binding.shares[0]
    tampered_bytes = bytes([first.masked_share[0] ^ 1]) + first.masked_share[1:]
    tampered_share = replace(first, masked_share=tampered_bytes)
    tampered = replace(binding, shares=(tampered_share, *binding.shares[1:]))

    with pytest.raises(SourceBindingError, match="failed commitment"):
        _ = recover_secret(tampered, reference)


def test_recovery_uses_constant_time_commitment_comparison(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Genuine and forged commitments use one pinned comparison primitive."""
    reference = _reference()
    binding = bind_secret(
        reference, _SECRET, policy=_policy(), context=_CONTEXT
    )
    forged = replace(
        binding,
        secret_commitment=bytes([binding.secret_commitment[0] ^ 1])
        + binding.secret_commitment[1:],
    )
    native_compare = hmac.compare_digest
    compared: list[tuple[bytes, bytes]] = []

    def record_compare(expected: bytes, received: bytes) -> bool:
        compared.append((expected, received))
        return native_compare(expected, received)

    with monkeypatch.context() as patched:
        patched.setattr(
            binding_module, "_native_compare_digest", record_compare
        )
        assert recover_secret(binding, reference) == _SECRET
        with pytest.raises(SourceBindingError, match="failed commitment"):
            _ = recover_secret(forged, reference)
    assert compared == [
        (binding.secret_commitment, binding.secret_commitment),
        (binding.secret_commitment, forged.secret_commitment),
    ]


@pytest.mark.parametrize("approve", [True, False])
def test_recovery_ignores_late_host_commitment_comparison(
    monkeypatch: pytest.MonkeyPatch, *, approve: bool
) -> None:
    """A late host comparison cannot permit or deny recovered keys."""
    reference = _reference()
    binding = bind_secret(
        reference, _SECRET, policy=_policy(), context=_CONTEXT
    )
    forged = replace(
        binding,
        secret_commitment=bytes([binding.secret_commitment[0] ^ 1])
        + binding.secret_commitment[1:],
    )
    calls = 0

    def swapped_compare(_expected: bytes, _received: bytes) -> bool:
        nonlocal calls
        del _expected, _received
        calls += 1
        return approve

    with monkeypatch.context() as patched:
        patched.setattr(hmac, "compare_digest", swapped_compare)
        if approve:
            with pytest.raises(SourceBindingError, match="failed commitment"):
                _ = recover_secret(forged, reference)
        else:
            assert recover_secret(binding, reference) == _SECRET
    assert calls == 0, "late host comparison was consulted during recovery"


def test_binding_rejects_threshold_below_required_file_count() -> None:
    """A source-distribution gate cannot exceed cryptographic quorum size."""
    policy = SourceBindingPolicy(
        threshold_fraction=0.20,
        maximum_anchors=_FILE_COUNT,
        minimum_anchor_files=3,
        anchor_policy=AnchorPolicy(window_bytes=16, selection_modulus=1),
    )
    with pytest.raises(SourceBindingPolicyError, match=r"threshold.*minimum"):
        _ = bind_secret(_reference(), _SECRET, policy=policy, context=_CONTEXT)


def test_recovery_rejects_file_requirement_above_share_threshold() -> None:
    """A forged envelope cannot declare more required files than shares."""
    valid = bind_secret(_reference(), _SECRET, policy=_policy(), context=_CONTEXT)
    malformed = replace(valid, threshold=valid.minimum_anchor_files - 1)
    with pytest.raises(SourceBindingError, match=r"threshold.*minimum"):
        _ = validate_threshold_binding(malformed)
    with pytest.raises(SourceBindingError, match=r"threshold.*minimum"):
        _ = recover_secret(malformed, cast("IdentityTree", object()))


def test_stricter_fraction_changes_threshold_fail_closed() -> None:
    """Round the configured threshold fraction up deterministically."""
    reference = _reference()
    binding = bind_secret(
        reference,
        _SECRET,
        policy=_policy(threshold_fraction=0.81),
        context=_CONTEXT,
    )

    _expect(
        binding.threshold == _STRICT_THRESHOLD,
        "threshold fraction did not round up",
    )


@pytest.mark.parametrize(
    ("maximum_anchors", "boundary"),
    [(3, 1), (20, 17), (50, 35)],
)
def test_threshold_ceil_respects_fraction_just_above_share_boundary(
    maximum_anchors: int, boundary: int
) -> None:
    """Floating-point multiplication must not round away a required share."""
    fraction = math.nextafter(boundary / maximum_anchors, math.inf)
    numerator, denominator = fraction.as_integer_ratio()
    assert maximum_anchors * numerator > boundary * denominator
    policy = SourceBindingPolicy(
        threshold_fraction=fraction,
        maximum_anchors=maximum_anchors,
        minimum_anchor_files=1,
        anchor_policy=AnchorPolicy(window_bytes=16, selection_modulus=1),
    )
    reference = _reference()
    binding = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    assert len(binding.shares) == maximum_anchors
    assert binding.threshold == boundary + 1
    assert recover_secret(binding, reference) == _SECRET

    if boundary == 1:
        single_share_source = _candidate_paths(
            reference, (binding.shares[0].source_path,)
        )
        with pytest.raises(SourceBindingError, match="insufficient"):
            _ = recover_secret(binding, single_share_source)


@pytest.mark.parametrize(
    ("fraction", "expected_threshold"),
    [(0.20, 1), (0.60, 3), (0.80, 4)],
)
def test_decimal_share_boundaries_keep_expected_quorum(
    fraction: float, expected_threshold: int
) -> None:
    """Decimal fractions at exact k/N boundaries must not tighten spuriously."""
    policy = SourceBindingPolicy(
        threshold_fraction=fraction,
        maximum_anchors=_FILE_COUNT,
        minimum_anchor_files=1,
        anchor_policy=AnchorPolicy(window_bytes=16, selection_modulus=1),
    )
    binding = bind_secret(_reference(), _SECRET, policy=policy, context=_CONTEXT)
    assert binding.threshold == expected_threshold


def test_bound_threshold_ignores_late_max_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late max override must not weaken T-of-N source dependence."""
    reference = _reference()
    policy = SourceBindingPolicy(
        threshold_fraction=0.80,
        maximum_anchors=_FILE_COUNT,
        minimum_anchor_files=1,
        anchor_policy=AnchorPolicy(window_bytes=16, selection_modulus=1),
    )
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "max", lambda *args, **kwargs: 1)
        binding = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)

    single_source = _candidate_paths(reference, (binding.shares[0].source_path,))
    with pytest.raises(SourceBindingError, match="insufficient"):
        _ = recover_secret(binding, single_source)
    assert binding.threshold == 4


def test_bound_anchors_ignore_late_sorted_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Domain sort hooks cannot change the authored source-binding shares."""
    reference = _reference()
    policy = _policy()
    baseline = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    native_sorted = builtins.sorted

    with monkeypatch.context() as patch:
        patch.setattr(
            builtins,
            "sorted",
            lambda values, *, key: list(reversed(native_sorted(values, key=key))),
        )
        after_hook = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)

    assert after_hook == baseline


def test_source_binding_policy_rejects_boolean_numeric_fields() -> None:
    """Boolean aliases cannot become thresholds, counts, or HKDF lengths."""
    with pytest.raises(SourceBindingPolicyError, match="finite value"):
        _ = SourceBindingPolicy(threshold_fraction=True)
    with pytest.raises(SourceBindingPolicyError, match="positive integer"):
        _ = SourceBindingPolicy(threshold_fraction=0.66, maximum_anchors=True)
    with pytest.raises(SourceBindingPolicyError, match="positive integer"):
        _ = SourceBindingPolicy(
            threshold_fraction=0.66,
            minimum_anchor_files=True,
        )
    with pytest.raises(SourceBindingPolicyError, match="integer within"):
        _ = hkdf_expand_sha256(b"key", b"info", length=True)


def test_source_binding_policy_rejects_huge_integer_fraction() -> None:
    """An out-of-range integer must not overflow during policy admission."""
    huge = 10**400
    for invalid in (huge, -huge):
        with pytest.raises(SourceBindingPolicyError, match="finite value"):
            _ = SourceBindingPolicy(threshold_fraction=invalid)


def test_public_source_binding_inputs_fail_closed() -> None:
    """Public binding and HKDF APIs reject foreign runtime input types."""
    reference = _reference()
    policy = _policy()
    with pytest.raises(SourceBindingPolicyError, match="exact IdentityTree"):
        _ = bind_secret(
            cast("IdentityTree", object()),
            _SECRET,
            policy=policy,
            context=_CONTEXT,
        )
    with pytest.raises(SourceBindingPolicyError, match="non-empty exact bytes"):
        _ = bind_secret(
            reference,
            cast("bytes", cast("object", bytearray(_SECRET))),
            policy=policy,
            context=_CONTEXT,
        )
    with pytest.raises(SourceBindingPolicyError, match="exact SourceBindingPolicy"):
        _ = bind_secret(
            reference,
            _SECRET,
            policy=cast("SourceBindingPolicy", object()),
            context=_CONTEXT,
        )
    with pytest.raises(SourceBindingPolicyError, match="non-empty exact bytes"):
        _ = bind_secret(
            reference,
            _SECRET,
            policy=policy,
            context=cast("bytes", cast("object", bytearray(_CONTEXT))),
        )
    with pytest.raises(SourceBindingPolicyError, match="extract inputs"):
        _ = hkdf_extract_sha256(cast("bytes", cast("object", bytearray())), _SECRET)
    with pytest.raises(SourceBindingPolicyError, match="expand inputs"):
        _ = hkdf_expand_sha256(
            _SECRET, cast("bytes", cast("object", bytearray(b"info"))), 1
        )


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("maximum_anchors", 0),
        ("maximum_anchors", 256),
        ("minimum_anchor_files", 0),
        ("minimum_anchor_files", True),
    ],
)
def test_binding_rechecks_unvalidated_native_policy_fields(
    field: str, invalid: object
) -> None:
    """A raw exact policy object must not bypass constructor bounds at bind."""
    raw = object.__new__(SourceBindingPolicy)
    object.__setattr__(raw, "threshold_fraction", 0.6)
    object.__setattr__(raw, "maximum_anchors", 5)
    object.__setattr__(raw, "minimum_anchor_files", 3)
    object.__setattr__(raw, "anchor_policy", AnchorPolicy(16, 1))
    object.__setattr__(raw, field, invalid)
    reference = identity_tree({f"src/{i}.bin": bytes((i,)) for i in range(5)})
    with pytest.raises(SourceBindingPolicyError):
        _ = bind_secret(reference, _SECRET, policy=raw, context=_CONTEXT)


def test_binding_rejects_incomplete_native_policy_before_source_use() -> None:
    """A raw policy with an unset slot fails with a typed policy error."""
    raw = object.__new__(SourceBindingPolicy)
    object.__setattr__(raw, "threshold_fraction", 0.6)
    with pytest.raises(SourceBindingPolicyError):
        _ = bind_secret(
            _reference(), _SECRET,
            policy=raw, context=_CONTEXT,
        )


@pytest.mark.parametrize("field", ["window_bytes", "selection_modulus"])
@pytest.mark.parametrize("invalid", [0, True, "1"])
def test_binding_policy_rejects_unvalidated_nested_anchor_fields(
    field: str, invalid: object
) -> None:
    """A forged exact policy record must not bypass nested anchor admission."""
    raw = object.__new__(AnchorPolicy)
    object.__setattr__(raw, "window_bytes", invalid if field == "window_bytes" else 16)
    object.__setattr__(
        raw, "selection_modulus", invalid if field == "selection_modulus" else 1
    )
    with pytest.raises(SourceBindingPolicyError, match="anchor_policy"):
        _ = SourceBindingPolicy(
            0.6, maximum_anchors=5, minimum_anchor_files=3,
            anchor_policy=raw,
        )


@pytest.mark.parametrize("field", ["window_bytes", "selection_modulus"])
@pytest.mark.parametrize("invalid", [0, True, "1"])
def test_binding_validation_rejects_unvalidated_nested_anchor_fields(
    field: str, invalid: object
) -> None:
    """A distributable envelope cannot admit malformed nested policy slots."""
    valid = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    raw = object.__new__(AnchorPolicy)
    object.__setattr__(raw, "window_bytes", invalid if field == "window_bytes" else 16)
    object.__setattr__(
        raw, "selection_modulus", invalid if field == "selection_modulus" else 1
    )
    malformed = replace(valid, anchor_policy=raw)
    with pytest.raises(SourceBindingError, match="anchor policy"):
        _ = validate_threshold_binding(malformed)
    with pytest.raises(SourceBindingError, match="anchor policy"):
        _ = recover_secret(malformed, cast("IdentityTree", object()))


@pytest.mark.parametrize("field", ["window_bytes", "selection_modulus"])
def test_binding_rejects_nested_anchor_record_changed_after_policy_creation(
    field: str,
) -> None:
    """An invalid nested anchor policy cannot be admitted by a later bind."""
    policy = _policy()
    unvalidated = object.__new__(AnchorPolicy)
    object.__setattr__(unvalidated, "window_bytes", 0 if field == "window_bytes" else 16)
    object.__setattr__(
        unvalidated, "selection_modulus", 0 if field == "selection_modulus" else 1
    )
    object.__setattr__(policy, "anchor_policy", unvalidated)
    with pytest.raises(SourceBindingPolicyError, match="anchor_policy"):
        _ = bind_secret(
            _reference(), _SECRET, policy=policy, context=_CONTEXT
        )


@pytest.mark.parametrize("role", ["policy", "envelope"])
@pytest.mark.parametrize("missing", ["window_bytes", "selection_modulus"])
def test_source_binding_rejects_incomplete_nested_anchor_policy(
    role: str, missing: str
) -> None:
    """An incomplete native anchor record must fail closed with a typed error."""
    unvalidated = object.__new__(AnchorPolicy)
    if missing != "window_bytes":
        object.__setattr__(unvalidated, "window_bytes", 16)
    if missing != "selection_modulus":
        object.__setattr__(unvalidated, "selection_modulus", 1)
    if role == "policy":
        with pytest.raises(SourceBindingPolicyError, match="anchor_policy"):
            _ = SourceBindingPolicy(0.6, anchor_policy=unvalidated)
    else:
        binding = bind_secret(
            _reference(), _SECRET, policy=_policy(), context=_CONTEXT
        )
        with pytest.raises(SourceBindingError, match="anchor policy"):
            _ = validate_threshold_binding(
                replace(binding, anchor_policy=unvalidated)
            )


@pytest.mark.parametrize("field", ["window_bytes", "selection_modulus"])
@pytest.mark.parametrize("hook", ["slot", "getattribute"])
def test_binding_nested_anchor_validation_ignores_late_getters(
    monkeypatch: pytest.MonkeyPatch, field: str, hook: str
) -> None:
    """Stored valid dimensions survive late anchor-policy class hook changes."""
    reference = _reference()
    policy = _policy()
    baseline = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    calls = 0

    def forbidden_getter(_anchor: AnchorPolicy) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("late anchor-policy getter consulted")

    native_getattribute = AnchorPolicy.__getattribute__

    def forbidden_getattribute(anchor: AnchorPolicy, name: str) -> object:
        if name == field:
            return forbidden_getter(anchor)
        return native_getattribute(anchor, name)

    with monkeypatch.context() as patched:
        if hook == "slot":
            patched.setattr(AnchorPolicy, field, property(forbidden_getter))
        else:
            patched.setattr(
                AnchorPolicy, "__getattribute__", forbidden_getattribute
            )
        _ = SourceBindingPolicy(
            0.6, maximum_anchors=5, minimum_anchor_files=3,
            anchor_policy=policy.anchor_policy,
        )
        assert validate_threshold_binding(baseline) is baseline
        observed = bind_secret(
            reference, _SECRET, policy=policy, context=_CONTEXT
        )
    assert calls == 0
    assert observed == baseline


@pytest.mark.parametrize(
    ("record", "missing"),
    [("binding", "context"), ("binding", "shares"),
     ("share", "source_path"), ("share", "masked_share")],
)
def test_incomplete_source_binding_records_fail_with_typed_error(
    record: str, missing: str
) -> None:
    """Uninitialized envelope/share slots must not expose AttributeError."""
    valid = bind_secret(_reference(), _SECRET, policy=_policy(), context=_CONTEXT)
    if record == "binding":
        raw = object.__new__(type(valid))
        for field in (
            "context", "threshold", "minimum_anchor_files", "secret_length",
            "secret_commitment", "anchor_policy", "shares",
        ):
            if field != missing:
                object.__setattr__(raw, field, getattr(valid, field))
        malformed = raw
    else:
        first = valid.shares[0]
        raw_share = object.__new__(type(first))
        for field in ("source_path", "anchor_digest", "x", "masked_share"):
            if field != missing:
                object.__setattr__(raw_share, field, getattr(first, field))
        malformed = replace(valid, shares=(raw_share, *valid.shares[1:]))
    with pytest.raises(SourceBindingError, match="source binding"):
        _ = validate_threshold_binding(malformed)
    with pytest.raises(SourceBindingError, match="source binding"):
        _ = recover_secret(malformed, cast("IdentityTree", object()))


@pytest.mark.parametrize("role", ["reference", "candidate"])
def test_incomplete_source_identity_fails_with_typed_binding_error(
    role: str
) -> None:
    """Uninitialized identity-tree slots cannot escape public error classes."""
    raw_identity = object.__new__(IdentityTree)
    if role == "reference":
        with pytest.raises(SourceBindingPolicyError):
            _ = bind_secret(
                raw_identity, _SECRET, policy=_policy(), context=_CONTEXT
            )
    else:
        valid = bind_secret(
            _reference(), _SECRET, policy=_policy(), context=_CONTEXT
        )
        with pytest.raises(SourceBindingError):
            _ = recover_secret(valid, raw_identity)


@pytest.mark.parametrize("role", ["reference", "candidate"])
@pytest.mark.parametrize("mutation", ["noncanonical_file", "unsorted_tree"])
def test_binding_rejects_unvalidated_native_source_identity(
    role: str, mutation: str
) -> None:
    """Raw identity slots cannot bypass portable path and tree admission."""
    reference = _reference()
    binding = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)
    files = reference.files
    if mutation == "noncanonical_file":
        first = files[0]
        raw_file = object.__new__(type(first))
        object.__setattr__(raw_file, "path", "src/../escape.c")
        object.__setattr__(raw_file, "canonical", first.canonical)
        unsafe_files = (raw_file, *files[1:])
    else:
        unsafe_files = tuple(reversed(files))
    raw_tree = object.__new__(IdentityTree)
    object.__setattr__(raw_tree, "files", unsafe_files)
    if role == "reference":
        with pytest.raises(SourceBindingPolicyError):
            _ = bind_secret(raw_tree, _SECRET, policy=_policy(), context=_CONTEXT)
    else:
        with pytest.raises(SourceBindingError):
            _ = recover_secret(binding, raw_tree)


@pytest.mark.parametrize("role", ["reference", "candidate"])
@pytest.mark.parametrize("mutation", ["foreign_file", "mutable_canonical", "mutable_files"])
def test_binding_rejects_unvalidated_identity_record_shapes(
    role: str, mutation: str
) -> None:
    """Raw source identity cannot certify foreign or mutable nested evidence."""
    reference = _reference()
    binding = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)
    first = reference.files[0]
    if mutation == "foreign_file":
        files = (cast("object", SimpleNamespace(path=first.path, canonical=first.canonical)),
                 *reference.files[1:])
    elif mutation == "mutable_canonical":
        raw_file = object.__new__(type(first))
        object.__setattr__(raw_file, "path", first.path)
        object.__setattr__(raw_file, "canonical", bytearray(first.canonical))
        files = (raw_file, *reference.files[1:])
    else:
        files = list(reference.files)
    raw_tree = object.__new__(IdentityTree)
    object.__setattr__(raw_tree, "files", files)
    if role == "reference":
        with pytest.raises(SourceBindingPolicyError):
            _ = bind_secret(raw_tree, _SECRET, policy=_policy(), context=_CONTEXT)
    else:
        with pytest.raises(SourceBindingError):
            _ = recover_secret(binding, raw_tree)


@pytest.mark.parametrize("role", ["reference", "candidate"])
@pytest.mark.parametrize("record", ["tree", "file"])
def test_source_binding_validation_uses_original_identity_validators(
    monkeypatch: pytest.MonkeyPatch, role: str, record: str
) -> None:
    """Late class validators cannot override stored source admission."""
    reference = _reference()
    binding = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)
    owner = IdentityTree if record == "tree" else type(reference.files[0])
    calls = 0

    def forbidden_validator(_value: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("late identity validator consulted")

    with monkeypatch.context() as patched:
        patched.setattr(owner, "__post_init__", forbidden_validator)
        if role == "reference":
            observed = bind_secret(
                reference, _SECRET, policy=_policy(), context=_CONTEXT
            )
            assert observed == binding
        else:
            assert recover_secret(binding, reference) == _SECRET
    assert calls == 0


def test_recovery_rejects_malformed_binding_before_candidate_use() -> None:
    """Distributable binding metadata is admitted before source inspection."""
    reference = _reference()
    binding = bind_secret(
        reference,
        _SECRET,
        policy=_policy(),
        context=_CONTEXT,
    )
    malformed = (
        replace(
            binding,
            context=cast("bytes", cast("object", bytearray(binding.context))),
        ),
        replace(binding, threshold=True),
        replace(binding, threshold=-1),
        replace(binding, minimum_anchor_files=True),
        replace(binding, minimum_anchor_files=-1),
        replace(binding, secret_length=True),
        replace(binding, secret_length=0),
        replace(binding, secret_commitment=b"short"),
        replace(binding, anchor_policy=cast("AnchorPolicy", object())),
        replace(
            binding,
            shares=cast("tuple[BoundShare, ...]", cast("object", list(binding.shares))),
        ),
        replace(binding, threshold=len(binding.shares) + 1),
        replace(binding, minimum_anchor_files=len(binding.shares) + 1),
    )
    for candidate in malformed:
        with pytest.raises(SourceBindingError, match="source"):
            _ = recover_secret(candidate, cast("IdentityTree", object()))


@pytest.mark.parametrize("record", ["binding", "share"])
@pytest.mark.parametrize("hook", ["slot", "getattribute"])
def test_binding_validation_ignores_late_metadata_forgery(
    monkeypatch: pytest.MonkeyPatch, record: str, hook: str
) -> None:
    """Stored invalid binding metadata cannot be validated by class hooks."""
    valid = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    first = valid.shares[0]
    if record == "binding":
        malformed = replace(valid, threshold=len(valid.shares) + 1)
        owner = type(valid)
        field = "threshold"
        forged: object = valid.threshold
        target = malformed
    else:
        malformed_share = replace(first, source_path="src/../escape.c")
        malformed = replace(
            valid, shares=(malformed_share, *valid.shares[1:])
        )
        owner = type(first)
        field = "source_path"
        forged = first.source_path
        target = malformed_share

    original_slot = owner.__dict__[field]

    def forged_getattr(value: object, name: str) -> object:
        if name == field and value is target:
            return forged
        return object.__getattribute__(value, name)

    def forged_slot(value: object) -> object:
        if value is target:
            return forged
        return original_slot.__get__(value, owner)

    with monkeypatch.context() as patched:
        if hook == "slot":
            patched.setattr(owner, field, property(forged_slot))
        else:
            patched.setattr(owner, "__getattribute__", forged_getattr)
        with pytest.raises(SourceBindingError):
            _ = validate_threshold_binding(malformed)


@pytest.mark.parametrize(
    ("record", "field", "forged"),
    [
        ("binding", "threshold", 99),
        ("binding", "minimum_anchor_files", 99),
        ("binding", "context", b"wrong-context"),
        ("binding", "shares", ()),
        ("share", "source_path", "src/missing.c"),
        ("share", "masked_share", b"short"),
    ],
)
def test_binding_recovery_ignores_late_metadata_hooks(
    monkeypatch: pytest.MonkeyPatch, record: str, field: str, forged: object
) -> None:
    """A valid binding recovers from stored metadata, not class getters."""
    reference = _reference()
    binding = bind_secret(
        reference, _SECRET, policy=_policy(), context=_CONTEXT
    )
    owner = type(binding) if record == "binding" else type(binding.shares[0])
    calls = 0

    def forged_getattr(value: object, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return forged
        return object.__getattribute__(value, name)

    with monkeypatch.context() as patched:
        patched.setattr(owner, "__getattribute__", forged_getattr)
        assert recover_secret(binding, reference) == _SECRET
    assert calls == 0, "late metadata getter participated in key recovery"


def test_recovery_rejects_impossible_share_file_topology() -> None:
    """A file cannot also be the ancestor directory of another bound file."""
    binding = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    first, second = binding.shares[:2]
    for first_path, second_path in (
        (first.source_path, f"{first.source_path}/child.c"),
        (f"{second.source_path}/parent.c", second.source_path),
    ):
        malformed = replace(
            binding,
            shares=(
                replace(first, source_path=first_path),
                replace(second, source_path=second_path),
                *binding.shares[2:],
            ),
        )
        with pytest.raises(SourceBindingError, match="ancestor/descendant"):
            _ = validate_threshold_binding(malformed)
        with pytest.raises(SourceBindingError, match="ancestor/descendant"):
            _ = recover_secret(malformed, cast("IdentityTree", object()))


def test_binding_inputs_reject_windows_drive_prefixed_paths() -> None:
    """Source identity admission rejects drive paths before key binding."""
    for drive_path in ("C:/unsafe.c", "C:unsafe.c"):
        files = _files("reference")
        files[drive_path] = files.pop("src/file-0.c")
        with pytest.raises(AdmissionPolicyError, match="invalid identity path"):
            _ = identity_tree(files)


def test_recovery_rejects_windows_drive_prefixed_share_paths() -> None:
    """Portable bindings reject Windows drive paths before candidate use."""
    binding = bind_secret(_reference(), _SECRET, policy=_policy(), context=_CONTEXT)
    for drive_path in ("C:/unsafe.c", "C:unsafe.c"):
        malformed = replace(
            binding,
            shares=(
                replace(binding.shares[0], source_path=drive_path),
                *binding.shares[1:],
            ),
        )
        with pytest.raises(SourceBindingError, match="drive"):
            _ = validate_threshold_binding(malformed)
        with pytest.raises(SourceBindingError, match="drive"):
            _ = recover_secret(malformed, cast("IdentityTree", object()))


@pytest.mark.parametrize(
    "reserved_path",
    [
        "NUL", "src/CON.txt", "src/COM1", "src/name:stream",
        "src/end.", "src/end ", "src/LPT².txt", "src/CONOUT$",
    ],
)
def test_recovery_rejects_windows_reserved_share_paths(
    reserved_path: str,
) -> None:
    """Distributable shares must use file names portable to Windows hosts."""
    binding = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    malformed = replace(
        binding,
        shares=(
            replace(binding.shares[0], source_path=reserved_path),
            *binding.shares[1:],
        ),
    )
    with pytest.raises(SourceBindingError, match="reserved"):
        _ = validate_threshold_binding(malformed)
    with pytest.raises(SourceBindingError, match="reserved"):
        _ = recover_secret(malformed, cast("IdentityTree", object()))


@pytest.mark.parametrize(
    "reserved_path", ["NUL", "src/CON.txt", "src/COM1/child.txt"]
)
def test_recovery_reserved_share_paths_resist_host_hook_swap(
    monkeypatch: pytest.MonkeyPatch,
    reserved_path: str,
) -> None:
    """Post-load host hooks cannot permit invalid distributable paths."""
    binding = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    malformed = replace(
        binding,
        shares=(
            replace(binding.shares[0], source_path=reserved_path),
            *binding.shares[1:],
        ),
    )

    def forged_isreserved(path: str) -> bool:
        del path
        return False

    monkeypatch.setattr(ntpath, "isreserved", forged_isreserved)
    with pytest.raises(SourceBindingError, match="reserved"):
        _ = validate_threshold_binding(malformed)
    with pytest.raises(SourceBindingError, match="reserved"):
        _ = recover_secret(malformed, cast("IdentityTree", object()))


@pytest.mark.parametrize(
    ("replacement", "forged_result", "expected_admitted"),
    [
        ("src/unsafe?.c", False, False),
        ("src/valid.c", True, True),
    ],
)
def test_binding_share_path_ignores_late_bool_predicate(
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
    forged_result: bool,
    expected_admitted: bool,
) -> None:
    """A mutable bool hook cannot alter Windows share-path admission."""
    original = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    forged = replace(
        original,
        shares=(
            replace(original.shares[0], source_path=replacement),
            *original.shares[1:],
        ),
    )
    calls = 0

    def forged_bool(value: object) -> bool:
        nonlocal calls
        del value
        calls += 1
        return forged_result

    admitted = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bool", forged_bool)
        try:
            _ = validate_threshold_binding(forged)
        except SourceBindingError:
            pass
        else:
            admitted = True
    assert admitted is expected_admitted
    assert calls == 0, "late bool hook participated in share-path admission"


def _forge_ntpath_any(patched: pytest.MonkeyPatch, invalid: str) -> None:
    del invalid
    native_any = builtins.any

    def forged_any(values: Iterable[object]) -> bool:
        frame = getattr(values, "gi_frame", None)
        globals_map = getattr(frame, "f_globals", {})
        if globals_map.get("__name__") == "ntpath":
            return False
        return native_any(values)

    patched.setattr(builtins, "any", forged_any)


def _forge_ntpath_reversed(patched: pytest.MonkeyPatch, invalid: str) -> None:
    native_reversed = builtins.reversed

    def forged_reversed(values: list[str]) -> object:
        if values == [invalid]:
            return ()
        return native_reversed(values)

    patched.setattr(builtins, "reversed", forged_reversed)


def _forge_ntpath_splitroot(patched: pytest.MonkeyPatch, invalid: str) -> None:
    native_splitroot = ntpath.splitroot

    def forged_splitroot(path: str) -> tuple[str, str, str]:
        if path == invalid:
            return "", "", "safe.c"
        return native_splitroot(path)

    patched.setattr(ntpath, "splitroot", forged_splitroot)


def _forge_ntpath_fspath(patched: pytest.MonkeyPatch, invalid: str) -> None:
    native_fspath = os.fspath

    def forged_fspath(path: os.PathLike[str] | str) -> str:
        if path == invalid:
            return "safe.c"
        return native_fspath(path)

    patched.setattr(os, "fspath", forged_fspath)


@pytest.mark.parametrize(
    ("forge", "invalid"),
    [
        (_forge_ntpath_any, "NUL"),
        (_forge_ntpath_reversed, "NUL"),
        (_forge_ntpath_splitroot, "src/COM1/child.txt"),
        (_forge_ntpath_fspath, "C:/escape.c"),
    ],
)
def test_binding_share_path_rejects_late_ntpath_dependency_hooks(
    monkeypatch: pytest.MonkeyPatch,
    forge: Callable[[pytest.MonkeyPatch, str], None],
    invalid: str,
) -> None:
    """An imported ntpath function cannot trust its mutable dependencies."""
    binding = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    malformed = replace(
        binding,
        shares=(
            replace(binding.shares[0], source_path=invalid),
            *binding.shares[1:],
        ),
    )
    rejected = False
    with monkeypatch.context() as patched:
        forge(patched, invalid)
        try:
            _ = validate_threshold_binding(malformed)
        except SourceBindingError:
            rejected = True
    assert rejected, f"late host hook admitted unsafe share path {invalid!r}"


def _forge_binding_path_method(
    patched: pytest.MonkeyPatch, method: str, invalid: str
) -> None:
    def forged_parts(_path: PurePosixPath) -> tuple[str, ...]:
        del _path
        return ()

    def forged_as_posix(_path: PurePosixPath) -> str:
        del _path
        return invalid

    def forged_absolute(_path: PurePosixPath) -> bool:
        del _path
        return False

    hooks = {
        "parts": property(forged_parts),
        "as_posix": forged_as_posix,
        "is_absolute": forged_absolute,
    }
    patched.setattr(PurePosixPath, method, hooks[method])


@pytest.mark.parametrize(
    ("method", "invalid"),
    [
        ("is_absolute", "/outside.c"),
        ("parts", "nested/../outside.c"),
        ("as_posix", "nested//outside.c"),
    ],
)
def test_binding_share_paths_resist_late_pathlib_method_spoof(
    monkeypatch: pytest.MonkeyPatch, method: str, invalid: str
) -> None:
    """Mutable native path methods must not admit noncanonical share labels."""
    binding = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    malformed = replace(
        binding,
        shares=(
            replace(binding.shares[0], source_path=invalid),
            *binding.shares[1:],
        ),
    )
    with monkeypatch.context() as patched:
        _forge_binding_path_method(patched, method, invalid)
        with pytest.raises(SourceBindingError, match="canonical and relative"):
            _ = validate_threshold_binding(malformed)


def test_binding_share_drive_resists_late_pathlib_drive_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutable Windows property cannot authorize drive-prefixed metadata."""
    binding = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    malformed = replace(
        binding,
        shares=(
            replace(binding.shares[0], source_path="C:/escape.c"),
            *binding.shares[1:],
        ),
    )

    def forged_drive(_path: PureWindowsPath) -> str:
        del _path
        return ""

    with monkeypatch.context() as patched:
        patched.setattr(PureWindowsPath, "drive", property(forged_drive))
        with pytest.raises(SourceBindingError, match="drive"):
            _ = validate_threshold_binding(malformed)


def test_binding_share_ancestry_resists_late_pathlib_parent_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutable parent hook cannot hide impossible share-file topology."""
    binding = bind_secret(
        _reference(), _SECRET, policy=_policy(), context=_CONTEXT
    )
    first, second = binding.shares[:2]
    malformed = replace(
        binding,
        shares=(
            first,
            replace(second, source_path=first.source_path + "/child.c"),
            *binding.shares[2:],
        ),
    )

    def forged_parents(_path: PurePosixPath) -> tuple[()]:
        del _path
        return ()

    with monkeypatch.context() as patched:
        patched.setattr(PurePosixPath, "parents", property(forged_parents))
        with pytest.raises(SourceBindingError, match="ancestor/descendant"):
            _ = validate_threshold_binding(malformed)


def test_recovery_rejects_malformed_share_metadata() -> None:
    """Every serialized share is canonical even when enough peers remain."""
    reference = _reference()
    binding = bind_secret(
        reference,
        _SECRET,
        policy=_policy(),
        context=_CONTEXT,
    )
    first = binding.shares[0]
    second = binding.shares[1]
    malformed_shares = (
        replace(first, source_path="../escape.c"),
        replace(first, source_path="src/bad\x00name.c"),
        replace(first, source_path="src/bad\ud800name.c"),
        replace(first, anchor_digest=b"short"),
        replace(first, x=True),
        replace(first, x=0),
        replace(first, x=256),
        replace(first, masked_share=b"short"),
    )
    for share in malformed_shares:
        malformed = replace(binding, shares=(share, *binding.shares[1:]))
        with pytest.raises(SourceBindingError, match="source"):
            _ = validate_threshold_binding(malformed)
        with pytest.raises(SourceBindingError, match="source"):
            _ = recover_secret(malformed, reference)

    duplicate_x = replace(second, x=first.x)
    with pytest.raises(SourceBindingError, match="coordinates must be unique"):
        _ = recover_secret(
            replace(binding, shares=(first, duplicate_x, *binding.shares[2:])),
            reference,
        )
    duplicate_anchor = replace(
        second,
        source_path=first.source_path,
        anchor_digest=first.anchor_digest,
    )
    with pytest.raises(SourceBindingError, match="anchors must be unique"):
        _ = recover_secret(
            replace(binding, shares=(first, duplicate_anchor, *binding.shares[2:])),
            reference,
        )


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("threshold_fraction", 0.0),
        ("maximum_anchors", 0),
        ("minimum_anchor_files", 256),
        ("anchor_policy", object()),
    ],
)
def test_binding_policy_rejects_invalid_after_validator_override(
    monkeypatch: pytest.MonkeyPatch, field: str, invalid: object
) -> None:
    """Policy construction cannot bypass the original quorum checker."""
    policy = _policy()
    calls = 0

    def allow_any(_value: SourceBindingPolicy) -> None:
        nonlocal calls
        calls += 1

    with monkeypatch.context() as patch:
        patch.setattr(SourceBindingPolicy, "__post_init__", allow_any)
        with pytest.raises(SourceBindingPolicyError):
            _ = replace(policy, **{field: invalid})
    assert calls == 0, "late validator hook admitted unsafe quorum metadata"


def test_binding_policy_keeps_valid_data_after_validator_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late class checker cannot reject valid binding policy dimensions."""
    calls = 0

    def reject_any(_value: SourceBindingPolicy) -> None:
        nonlocal calls
        calls += 1
        raise SourceBindingPolicyError("forged rejection")

    with monkeypatch.context() as patch:
        patch.setattr(SourceBindingPolicy, "__post_init__", reject_any)
        policy = SourceBindingPolicy(0.6, maximum_anchors=5, minimum_anchor_files=3)
    assert policy.threshold_fraction == 0.6
    assert policy.maximum_anchors == 5
    assert calls == 0, "late class checker rejected a valid binding policy"


@pytest.mark.parametrize(
    ("field", "invalid", "replacement"),
    [
        ("threshold_fraction", 0.0, 0.6),
        ("maximum_anchors", 0, 5),
        ("minimum_anchor_files", 0, 3),
        ("anchor_policy", object(), _policy().anchor_policy),
    ],
)
def test_binding_policy_constructor_rejects_property_setter_substitution(
    monkeypatch: pytest.MonkeyPatch, field: str, invalid: object,
    replacement: object,
) -> None:
    """A class property setter cannot replace invalid quorum policy inputs."""
    valid_policy = _policy()
    original_slot = cast(
        "MemberDescriptorType", SourceBindingPolicy.__dict__[field]
    )
    calls = 0

    def forged_setter(value: SourceBindingPolicy, _supplied: object) -> None:
        nonlocal calls
        calls += 1
        original_slot.__set__(value, replacement)

    def stored_field(value: object) -> object:
        return cast("object", original_slot.__get__(value, SourceBindingPolicy))

    with monkeypatch.context() as patched:
        patched.setattr(
            SourceBindingPolicy,
            field,
            property(stored_field, forged_setter),
        )
        with pytest.raises(SourceBindingPolicyError):
            _ = replace(
                valid_policy, **{field: invalid}
            )
    assert calls == 0, "late policy property setter intercepted construction"


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("source_path", "../unsafe.c"),
        ("anchor_digest", b"short"),
        ("x", 0),
        ("masked_share", b"short"),
    ],
)
def test_bound_share_constructor_rejects_property_setter_substitution(
    monkeypatch: pytest.MonkeyPatch, field: str, invalid: object
) -> None:
    """A share setter cannot launder malformed distributable evidence."""
    reference = _reference()
    binding = bind_secret(
        reference, _SECRET, policy=_policy(), context=_CONTEXT
    )
    original = binding.shares[0]
    owner = type(original)
    slot = cast("MemberDescriptorType", owner.__dict__[field])
    valid = cast("object", slot.__get__(original, owner))
    calls = 0

    def forged_setter(value: object, _supplied: object) -> None:
        nonlocal calls
        calls += 1
        slot.__set__(value, valid)

    def stored_field(value: object) -> object:
        return cast("object", slot.__get__(value, owner))

    with monkeypatch.context() as patched:
        patched.setattr(
            owner, field,
            property(stored_field, forged_setter),
        )
        changed = replace(original, **{field: invalid})
        malformed = replace(
            binding, shares=(changed, *binding.shares[1:])
        )
        with pytest.raises(SourceBindingError):
            _ = validate_threshold_binding(malformed)
    assert calls == 0, "late share property setter intercepted construction"


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("context", b""),
        ("threshold", 0),
        ("minimum_anchor_files", 0),
        ("secret_length", 0),
        ("secret_commitment", b"short"),
        ("anchor_policy", object()),
        ("shares", ()),
    ],
)
def test_threshold_binding_constructor_rejects_property_setter_substitution(
    monkeypatch: pytest.MonkeyPatch, field: str, invalid: object
) -> None:
    """An envelope setter cannot replace evidence before admission."""
    reference = _reference()
    binding = bind_secret(
        reference, _SECRET, policy=_policy(), context=_CONTEXT
    )
    owner = type(binding)
    slot = cast("MemberDescriptorType", owner.__dict__[field])
    valid = cast("object", slot.__get__(binding, owner))
    calls = 0

    def forged_setter(value: object, _supplied: object) -> None:
        nonlocal calls
        calls += 1
        slot.__set__(value, valid)

    def stored_field(value: object) -> object:
        return cast("object", slot.__get__(value, owner))

    with monkeypatch.context() as patched:
        patched.setattr(
            owner, field,
            property(stored_field, forged_setter),
        )
        malformed = replace(binding, **{field: invalid})
        with pytest.raises(SourceBindingError):
            _ = validate_threshold_binding(malformed)
    assert calls == 0, "late binding property setter intercepted construction"


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("source_path", "src/foreign.c"),
        ("digest", b"forged"),
        ("window", b"forged anchor bytes"),
    ],
)
def test_anchor_material_constructor_ignores_property_setters(
    monkeypatch: pytest.MonkeyPatch, field: str, replacement: object
) -> None:
    """Internal material creation must store real path, digest, and window."""
    reference = _reference()
    policy = _policy()
    expected = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    owner = cast("type[object]", vars(binding_module)["_AnchorMaterial"])
    slot = cast("MemberDescriptorType", owner.__dict__[field])
    calls = 0

    def forged_setter(value: object, _supplied: object) -> None:
        nonlocal calls
        calls += 1
        slot.__set__(value, replacement)

    def stored_field(value: object) -> object:
        return cast("object", slot.__get__(value, owner))

    with monkeypatch.context() as patched:
        patched.setattr(
            owner, field,
            property(stored_field, forged_setter),
        )
        observed = bind_secret(
            reference, _SECRET, policy=policy, context=_CONTEXT
        )
    assert observed == expected
    assert calls == 0, "late material property setter intercepted construction"


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("source_path", "src/foreign.c"),
        ("x", 254),
        ("value", b"forged recovered key bytes"),
    ],
)
def test_recovered_share_constructor_ignores_property_setters(
    monkeypatch: pytest.MonkeyPatch, field: str, replacement: object
) -> None:
    """Recovered shares must not be rewritten by class field properties."""
    reference = _reference()
    binding = bind_secret(
        reference, _SECRET, policy=_policy(), context=_CONTEXT
    )
    owner = cast("type[object]", vars(binding_module)["_RecoveredShare"])
    slot = cast("MemberDescriptorType", owner.__dict__[field])
    calls = 0

    def forged_setter(value: object, _supplied: object) -> None:
        nonlocal calls
        calls += 1
        slot.__set__(value, replacement)

    def stored_field(value: object) -> object:
        return cast("object", slot.__get__(value, owner))

    with monkeypatch.context() as patched:
        patched.setattr(
            owner, field,
            property(stored_field, forged_setter),
        )
        assert recover_secret(binding, reference) == _SECRET
    assert calls == 0, "late recovered share setter intercepted construction"


@pytest.mark.parametrize("record", ["material", "share", "binding", "recovered"])
def test_binding_internal_creation_ignores_late_class_initializers(
    monkeypatch: pytest.MonkeyPatch, record: str
) -> None:
    """Consumer class hooks cannot rewrite internal key-binding evidence."""
    reference = _reference()
    policy = _policy()
    baseline = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    owners: dict[str, type[object]] = {
        "material": cast("type[object]", vars(binding_module)["_AnchorMaterial"]),
        "share": type(baseline.shares[0]),
        "binding": type(baseline),
        "recovered": cast("type[object]", vars(binding_module)["_RecoveredShare"]),
    }
    calls = 0

    def forbidden_constructor(*args: object, **kwargs: object) -> None:
        nonlocal calls
        del args, kwargs
        calls += 1
        raise AssertionError("late record constructor replaced source evidence")

    with monkeypatch.context() as patched:
        patched.setattr(owners[record], "__init__", forbidden_constructor)
        if record == "recovered":
            assert recover_secret(baseline, reference) == _SECRET
        else:
            observed = bind_secret(
                reference, _SECRET, policy=policy, context=_CONTEXT
            )
            assert observed == baseline
    assert calls == 0, f"late {record} initializer was consulted"


@pytest.mark.parametrize("record", ["material", "share", "binding", "recovered"])
def test_binding_internal_allocation_ignores_late_class_new(record: str) -> None:
    """Check unsafe class allocation changes in an isolated interpreter."""
    script = """
from algorithms.diff import source_binding as module
from algorithms.diff.admission import identity_tree
from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.source_binding import (
    SourceBindingPolicy, bind_secret, recover_secret,
)
reference = identity_tree({
    "src/a.c": b"alpha-alpha",
    "src/b.c": b"bravo-bravo",
    "src/c.c": b"charlie-charlie",
})
policy = SourceBindingPolicy(
    1.0, maximum_anchors=3, minimum_anchor_files=3,
    anchor_policy=AnchorPolicy(window_bytes=4, selection_modulus=1),
)
secret = b"synthetic 32-byte protected key!"
context = b"isolated-constructor-test"
baseline = bind_secret(reference, secret, policy=policy, context=context)
owners = {
    "material": module._AnchorMaterial,
    "share": type(baseline.shares[0]),
    "binding": type(baseline),
    "recovered": module._RecoveredShare,
}
def forbidden_new(*args, **kwargs):
    raise AssertionError("late __new__ hook rewrote source evidence")
owners[RECORD].__new__ = staticmethod(forbidden_new)
if RECORD == "recovered":
    assert recover_secret(baseline, reference) == secret
else:
    assert bind_secret(reference, secret, policy=policy, context=context) == baseline
""".replace("RECORD", repr(record))
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("route", "detail"),
    [
        ("anchor-policy", "invalid nested anchor"),
        ("policy", "stored fields"),
        ("reference", "invalid identity fields"),
        ("envelope", "incomplete envelope"),
        ("candidate", "invalid identity metadata"),
    ],
)
def test_source_binding_native_guards_reject_late_attribute_error_alias(
    monkeypatch: pytest.MonkeyPatch, route: str, detail: str
) -> None:
    """Incomplete exact records must fail closed after builtin alias swaps."""
    reference = _reference()
    policy = _policy()
    valid = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    native_attribute_error = builtins.AttributeError
    rejected: SourceBindingPolicyError | SourceBindingError | None = None
    anchor_result: bool | None = None
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "AttributeError", RuntimeError)
        try:
            if route == "anchor-policy":
                anchor_result = binding_module._valid_anchor_policy_fields(
                    object.__new__(AnchorPolicy)
                )
            elif route == "policy":
                _ = bind_secret(
                    reference, _SECRET,
                    policy=object.__new__(SourceBindingPolicy),
                    context=_CONTEXT,
                )
            elif route == "reference":
                _ = bind_secret(
                    object.__new__(IdentityTree), _SECRET,
                    policy=policy, context=_CONTEXT,
                )
            elif route == "envelope":
                _ = validate_threshold_binding(object.__new__(type(valid)))
            else:
                _ = recover_secret(valid, object.__new__(IdentityTree))
        except (SourceBindingPolicyError, SourceBindingError) as error:
            rejected = error
        finally:
            builtins.__dict__["AttributeError"] = native_attribute_error
    if route == "anchor-policy":
        assert anchor_result is False
    else:
        assert rejected is not None, route
        assert detail in str(rejected)


@pytest.mark.parametrize("route", ["validate", "recover"])
def test_source_binding_share_path_unicode_error_alias_fails_closed(
    monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    """A late exception alias cannot leak an unencodable share path error."""
    reference = _reference()
    valid = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)
    first = valid.shares[0]
    malformed = replace(
        valid,
        shares=(
            replace(first, source_path="src/bad\ud800name.c"),
            *valid.shares[1:],
        ),
    )
    native_unicode_encode_error = builtins.UnicodeEncodeError
    rejected: SourceBindingError | None = None
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "UnicodeEncodeError", LookupError)
        try:
            if route == "validate":
                _ = validate_threshold_binding(malformed)
            else:
                _ = recover_secret(malformed, reference)
        except SourceBindingError as error:
            rejected = error
        finally:
            builtins.__dict__["UnicodeEncodeError"] = native_unicode_encode_error
    assert rejected is not None, route
    assert "UTF-8 encodable" in str(rejected)
    assert type(rejected.__cause__) is native_unicode_encode_error


@pytest.mark.parametrize("route", ["reference", "candidate"])
def test_source_binding_identity_validator_ignores_late_error_alias(
    monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    """Mutable imported policy error alias must not leak native admission errors."""
    reference = _reference()
    invalid = object.__new__(IdentityTree)
    object.__setattr__(invalid, "files", tuple(reversed(reference.files)))
    valid_binding = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)
    rejected: SourceBindingPolicyError | SourceBindingError | None = None
    with monkeypatch.context() as patched:
        patched.setattr(binding_module, "AdmissionPolicyError", LookupError)
        try:
            if route == "reference":
                _ = bind_secret(invalid, _SECRET, policy=_policy(), context=_CONTEXT)
            else:
                _ = recover_secret(valid_binding, invalid)
        except (SourceBindingPolicyError, SourceBindingError) as error:
            rejected = error
    assert rejected is not None, route
    assert type(rejected) is (
        SourceBindingPolicyError if route == "reference" else SourceBindingError
    )
    assert type(rejected.__cause__) is AdmissionPolicyError
    assert "invalid identity metadata" in str(rejected)


@pytest.mark.parametrize(
    "route", ["constructor", "bind", "hkdf"]
)
def test_source_binding_policy_error_preserves_native_class_after_alias(
    monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    """Late public error aliases cannot replace a native policy rejection."""
    with monkeypatch.context() as patched:
        patched.setattr(binding_module, "SourceBindingPolicyError", object)
        with pytest.raises(SourceBindingPolicyError):
            if route == "constructor":
                _ = SourceBindingPolicy(threshold_fraction=0.0)
            elif route == "bind":
                _ = bind_secret(
                    cast("IdentityTree", object()), _SECRET,
                    policy=_policy(), context=_CONTEXT,
                )
            else:
                _ = hkdf_extract_sha256(
                    cast("bytes", cast("object", "bad")), _SECRET
                )


@pytest.mark.parametrize(
    "route", ["header", "share", "recovery"]
)
def test_source_binding_recovery_error_preserves_native_class_after_alias(
    monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    """Late public error aliases cannot leak raw TypeError in admission."""
    reference = _reference()
    valid = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)
    invalid = replace(
        valid,
        shares=(
            replace(valid.shares[0], source_path="../escape"),
            *valid.shares[1:],
        ),
    )
    with monkeypatch.context() as patched:
        patched.setattr(binding_module, "SourceBindingError", object)
        with pytest.raises(SourceBindingError):
            if route == "header":
                _ = validate_threshold_binding(
                    cast("ThresholdBinding", object())
                )
            elif route == "share":
                _ = validate_threshold_binding(invalid)
            else:
                _ = recover_secret(
                    valid, cast("IdentityTree", object())
                )


@pytest.mark.parametrize(
    "alias",
    [
        "AnchorPolicy",
        "StableAnchor",
        "IdentityTree",
        "IdentityFile",
        "SourceBindingPolicy",
        "BoundShare",
        "ThresholdBinding",
    ],
)
def test_source_binding_native_records_survive_late_class_aliases(
    monkeypatch: pytest.MonkeyPatch, alias: str
) -> None:
    """Public class names must not replace original evidence identities."""
    reference = _reference()
    policy = _policy()
    expected = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    with monkeypatch.context() as patched:
        patched.setattr(binding_module, alias, object)
        observed = bind_secret(
            reference, _SECRET, policy=policy, context=_CONTEXT
        )
        assert observed == expected
        assert validate_threshold_binding(expected) is expected
        assert recover_secret(expected, reference) == _SECRET


@pytest.mark.parametrize("alias", ["BoundShare", "ThresholdBinding"])
def test_source_binding_foreign_receipts_remain_rejected_after_class_alias(
    monkeypatch: pytest.MonkeyPatch, alias: str
) -> None:
    """A class alias cannot turn foreign receipts into native metadata."""
    reference = _reference()
    valid = bind_secret(reference, _SECRET, policy=_policy(), context=_CONTEXT)
    if alias == "BoundShare":
        foreign = replace(
            valid,
            shares=(
                cast("BoundShare", cast("object", SimpleNamespace())),
                *valid.shares[1:],
            ),
        )
    else:
        foreign = cast("ThresholdBinding", cast("object", SimpleNamespace()))
    with monkeypatch.context() as patched:
        patched.setattr(binding_module, alias, SimpleNamespace)
        with pytest.raises(SourceBindingError):
            _ = validate_threshold_binding(foreign)


@pytest.mark.parametrize("route", ["bind", "recover"])
def test_source_binding_anchor_selection_ignores_late_function_alias(
    monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    """A late selection helper must not discard valid source evidence."""
    reference = _reference()
    policy = _policy()
    binding = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    calls = 0

    def no_anchors(
        _data: bytes, _policy: AnchorPolicy
    ) -> tuple[StableAnchor, ...]:
        nonlocal calls
        calls += 1
        return ()

    with monkeypatch.context() as patched:
        patched.setattr(binding_module, "stable_anchors", no_anchors)
        if route == "bind":
            observed = bind_secret(
                reference, _SECRET, policy=policy, context=_CONTEXT
            )
            assert observed == binding
        else:
            assert recover_secret(binding, reference) == _SECRET
    assert calls == 0, "late anchor selector intercepted source identity"


def test_source_binding_fraction_decimal_alias_cannot_lower_quorum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late decimal factory cannot reduce the threshold at key binding."""
    reference = _reference()
    policy = _policy(threshold_fraction=1.0)
    expected = bind_secret(reference, _SECRET, policy=policy, context=_CONTEXT)
    calls = 0

    class ReducedFraction:
        def __init__(self, _fraction: str) -> None:
            nonlocal calls
            calls += 1

        def as_integer_ratio(self) -> tuple[int, int]:
            return 3, 5

    with monkeypatch.context() as patched:
        patched.setattr(binding_module, "Decimal", ReducedFraction)
        observed = bind_secret(
            reference, _SECRET, policy=policy, context=_CONTEXT
        )
    assert expected.threshold == len(expected.shares)
    assert observed == expected
    assert calls == 0, "late Decimal alias changed the threshold"
