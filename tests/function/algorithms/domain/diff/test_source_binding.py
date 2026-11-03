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
from dataclasses import replace
from pathlib import PurePosixPath, PureWindowsPath
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

import pytest
from algorithms.diff import source_binding as binding_module
from algorithms.diff.admission import AdmissionPolicyError, IdentityTree, identity_tree
from algorithms.diff.fingerprints import AnchorPolicy
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
    from collections.abc import Callable, Iterable, Sized

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
