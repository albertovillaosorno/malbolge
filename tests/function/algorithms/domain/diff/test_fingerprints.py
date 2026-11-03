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
#   - Tests for deterministic content-defined stable anchors.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Tests for deterministic content-defined stable anchors."""

import builtins
from collections.abc import Iterable, Sized
import hashlib
from typing import cast

from algorithms.diff.fingerprints import AnchorCoverage
from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.fingerprints import FingerprintPolicyError
from algorithms.diff.fingerprints import StableAnchor
from algorithms.diff.fingerprints import anchor_coverage
from algorithms.diff.fingerprints import stable_anchors
import pytest

_BLOCK_COUNT = 256
_INSERTION = b"target-only insertion that shifts all later offsets"
_MINIMUM_EXPECTED_COVERAGE = 0.90
_MAXIMUM_UNRELATED_COVERAGE = 0.10


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _synthetic_bytes(label: str) -> bytes:
    blocks = (
        hashlib.sha256(f"{label}:{index}".encode()).digest()
        for index in range(_BLOCK_COUNT)
    )
    return b"".join(blocks)


def test_stable_anchors_are_deterministic() -> None:
    """Repeated anchor extraction must produce byte-identical evidence."""
    source = _synthetic_bytes("source")
    first = stable_anchors(source)
    second = stable_anchors(source)
    _expect(first == second, "repeated anchor extraction differs")
    _expect(bool(first), "synthetic source produced no anchors")


def test_anchor_selection_resists_post_import_power_hook_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutable process-global power must not redefine lineage windows."""
    source = _synthetic_bytes("pow-lineage")
    expected = stable_anchors(source)
    original_pow = builtins.pow
    calls = 0

    def forged_pow(base: int, exponent: int, modulus: int | None = None) -> int:
        nonlocal calls
        if (base, exponent, modulus) == (257, 31, 1 << 64):
            calls += 1
            return 0
        if modulus is None:
            return cast("int", original_pow(base, exponent))
        return original_pow(base, exponent, modulus)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "pow", forged_pow)
        observed = stable_anchors(source)
    assert observed == expected
    assert calls == 0


def test_anchor_offsets_resist_post_import_sorted_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late source hooks cannot reorder deterministic lineage evidence."""
    source = _synthetic_bytes("sorted-lineage")
    expected = stable_anchors(source)
    assert len(expected) > 1, "fixture needs multiple stable anchors"
    calls = 0

    def forged_sorted(
        values: Iterable[StableAnchor], *, key: object = None
    ) -> list[StableAnchor]:
        """Reverse selected anchors instead of sorting them.

        Returns:
            Illegitimately reordered source lineage anchors.

        """
        nonlocal calls
        del key
        calls += 1
        return list(reversed(tuple(values)))

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "sorted", forged_sorted)
        observed = stable_anchors(source)

    assert observed == expected, "mutable sorted hook reordered source evidence"
    assert calls == 0, "mutable global sorting hook was consulted"


def test_anchor_selection_ignores_late_range_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A domain hook cannot remove rolling-hash windows from evidence."""
    source = _synthetic_bytes("range-lineage")
    expected = stable_anchors(source)
    native_range = range
    calls = 0

    def erase_window_scan(*args: int) -> range:
        nonlocal calls
        if len(args) == 1:
            calls += 1
            return native_range(0)
        return native_range(*args)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "range", erase_window_scan)
        observed = stable_anchors(source)

    _expect(observed == expected, "range override changed source anchors")
    _expect(calls == 0, "mutable range was consulted")


def test_anchor_coverage_rejects_foreign_record_after_any_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged any() cannot admit a foreign immutable anchor record."""
    foreign = cast("StableAnchor", object())
    calls = 0

    def suppress_foreign_record(_items: object) -> bool:
        nonlocal calls
        calls += 1
        return False

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "any", suppress_foreign_record)
        try:
            _ = anchor_coverage((foreign,), ())
        except FingerprintPolicyError:
            rejected = True

    _expect(rejected, "foreign anchor was accepted after any override")
    _expect(calls == 0, "mutable any was consulted")


def test_anchor_policy_rejects_bool_after_type_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late type() spoofing cannot admit Boolean anchor dimensions."""
    native_type = type
    calls = 0

    def disguise_boolean(value: object) -> type[object]:
        nonlocal calls
        if value is True:
            calls += 1
            return int
        return native_type(value)

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "type", disguise_boolean)
        try:
            _ = AnchorPolicy(window_bytes=True)
        except FingerprintPolicyError:
            rejected = True

    _expect(rejected, "Boolean anchor width was admitted")
    _expect(calls == 0, "mutable type was consulted")


def test_stable_anchor_rejects_short_digest_after_len_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late len() spoofing cannot admit undersized digest evidence."""
    short_digest = b"short"
    native_len = len
    calls = 0

    def disguise_length(value: Sized) -> int:
        nonlocal calls
        if value is short_digest:
            calls += 1
            return 32
        return native_len(value)

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "len", disguise_length)
        try:
            _ = StableAnchor(digest=short_digest, offset=0)
        except FingerprintPolicyError:
            rejected = True

    _expect(rejected, "short digest was accepted after len override")
    _expect(calls == 0, "mutable len was consulted")


def test_anchor_selection_rejects_mutable_data_after_type_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Foreign mutable source cannot masquerade as immutable SHA input."""
    foreign = bytearray(b"source")
    native_type = type
    calls = 0

    def disguise_bytes(value: object) -> type[object]:
        nonlocal calls
        if value is foreign:
            calls += 1
            return bytes
        return native_type(value)

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "type", disguise_bytes)
        try:
            _ = stable_anchors(cast("bytes", cast("object", foreign)))
        except FingerprintPolicyError:
            rejected = True

    _expect(rejected, "mutable input was admitted as source bytes")
    _expect(calls == 0, "mutable type was consulted")


def test_anchor_policy_rejects_late_int_alias_for_bool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late integer aliases cannot admit Boolean anchor dimensions."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        try:
            _ = AnchorPolicy(window_bytes=True, selection_modulus=True)
        except FingerprintPolicyError:
            rejected = True
    assert rejected, "late int alias admitted Boolean dimensions"


def test_stable_anchor_rejects_late_int_alias_for_bool_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late integer aliases cannot certify Boolean source offsets."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        try:
            _ = StableAnchor(digest=b"x" * 32, offset=True)
        except FingerprintPolicyError:
            rejected = True
    assert rejected, "late int alias admitted a Boolean offset"


def test_anchor_coverage_rejects_late_int_alias_for_bool_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late integer aliases cannot certify Boolean coverage counts."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        try:
            _ = AnchorCoverage(matched=True, total=True, ratio=1.0)
        except FingerprintPolicyError:
            rejected = True
    assert rejected, "late int alias admitted Boolean coverage counts"


@pytest.mark.parametrize("entry", ["digest", "input"])
def test_stable_anchors_reject_late_bytes_alias_for_mutable_evidence(
    monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    """Late bytes aliases cannot certify mutable source or digest evidence."""
    foreign = bytearray(b"x" * 32) if entry == "digest" else bytearray()
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bytes", bytearray)
        try:
            if entry == "digest":
                _ = StableAnchor(
                    digest=cast("bytes", cast("object", foreign)), offset=0
                )
            else:
                _ = stable_anchors(cast("bytes", cast("object", foreign)))
        except FingerprintPolicyError:
            rejected = True
    assert rejected, f"late bytes alias admitted mutable {entry}"


def test_anchor_coverage_rejects_late_tuple_alias_for_list_records(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late tuple aliases cannot certify mutable anchor collections."""
    anchors = [StableAnchor(digest=b"x" * 32, offset=0)]
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "tuple", list)
        try:
            _ = anchor_coverage(
                cast("tuple[StableAnchor, ...]", cast("object", anchors)),
                cast("tuple[StableAnchor, ...]", cast("object", anchors)),
            )
        except FingerprintPolicyError:
            rejected = True
    assert rejected, "late tuple alias admitted mutable anchor collections"


def test_anchor_coverage_rejects_late_float_alias_for_boolean_ratio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late float aliases cannot certify a Boolean coverage ratio."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "float", bool)
        try:
            _ = AnchorCoverage(matched=1, total=1, ratio=True)
        except FingerprintPolicyError:
            rejected = True
    assert rejected, "late float alias admitted a Boolean coverage ratio"


def test_valid_fingerprint_metadata_resists_late_type_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native records remain admissible after foreign builtin names change."""
    original = stable_anchors(b"lineage bytes")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        policy = AnchorPolicy(window_bytes=32, selection_modulus=64)
        anchor = StableAnchor(digest=b"x" * 32, offset=0)
        coverage = AnchorCoverage(matched=1, total=1, ratio=1.0)
    assert policy == AnchorPolicy()
    assert anchor.offset == 0
    assert coverage.ratio == 1.0

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "float", bool)
        assert AnchorCoverage(matched=1, total=1, ratio=1.0) == coverage
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bytes", bytearray)
        assert stable_anchors(b"lineage bytes") == original
        assert StableAnchor(digest=b"x" * 32, offset=0) == anchor
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "tuple", list)
        assert anchor_coverage((anchor,), (anchor,)).ratio == 1.0


def test_content_defined_anchors_survive_insertion_shift() -> None:
    """Insertion offsets may move while unchanged content digests survive."""
    source = _synthetic_bytes("source")
    midpoint = len(source) // 2
    candidate = source[:midpoint] + _INSERTION + source[midpoint:]
    reference_anchors = stable_anchors(source)
    candidate_anchors = stable_anchors(candidate)
    coverage = anchor_coverage(reference_anchors, candidate_anchors)
    _expect(
        coverage.ratio >= _MINIMUM_EXPECTED_COVERAGE,
        "insertion destroyed too many content-defined anchors",
    )


def test_unrelated_content_has_low_anchor_coverage() -> None:
    """Aggregate size alone must not create convincing source lineage."""
    source = _synthetic_bytes("source")
    unrelated = _synthetic_bytes("unrelated")
    coverage = anchor_coverage(
        stable_anchors(source),
        stable_anchors(unrelated),
    )
    _expect(
        coverage.ratio <= _MAXIMUM_UNRELATED_COVERAGE,
        "unrelated content retained too many source anchors",
    )


class _ForgedStableDigest:
    """Hostile hash callback always returns one identical fingerprint."""

    @staticmethod
    def digest() -> bytes:
        """Return one false SHA-256 digest.

        Returns:
            A constant value of the expected digest length.

        """
        return b"z" * 32


def _forged_sha256(data: bytes = b"") -> _ForgedStableDigest:
    del data
    return _ForgedStableDigest()


def test_anchor_coverage_resists_post_import_hash_constructor_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A host callback must not make unrelated sources appear lineal."""
    source = _synthetic_bytes("reference")
    unrelated = _synthetic_bytes("independent")
    genuine = anchor_coverage(stable_anchors(source), stable_anchors(unrelated))
    _expect(
        genuine.ratio <= _MAXIMUM_UNRELATED_COVERAGE,
        "unrelated fixture was not sufficiently independent",
    )

    with monkeypatch.context() as patch:
        patch.setattr(hashlib, "sha256", _forged_sha256)
        observed = anchor_coverage(
            stable_anchors(source), stable_anchors(unrelated)
        )
    _expect(
        observed.ratio <= _MAXIMUM_UNRELATED_COVERAGE,
        "hostile SHA-256 constructor forged full source lineage",
    )


def test_anchor_policy_controls_sampling_density() -> None:
    """A deterministic denser policy should not yield fewer sampled anchors."""
    source = _synthetic_bytes("source")
    dense = stable_anchors(source, AnchorPolicy(selection_modulus=16))
    sparse = stable_anchors(source, AnchorPolicy(selection_modulus=128))
    _expect(len(dense) >= len(sparse), "denser policy yielded fewer anchors")


def test_anchor_policy_rejects_boolean_dimensions() -> None:
    """Boolean values cannot alias one-byte anchor policy dimensions."""
    with pytest.raises(FingerprintPolicyError, match="must be integers"):
        _ = AnchorPolicy(window_bytes=True)
    with pytest.raises(FingerprintPolicyError, match="must be integers"):
        _ = AnchorPolicy(selection_modulus=True)


def test_anchor_functions_reject_foreign_runtime_types() -> None:
    """Anchor extraction and coverage never accept foreign evidence records."""
    with pytest.raises(FingerprintPolicyError, match="exact bytes"):
        _ = stable_anchors(cast("bytes", cast("object", bytearray(b"source"))))
    with pytest.raises(FingerprintPolicyError, match="exact AnchorPolicy"):
        _ = stable_anchors(
            b"source",
            cast("AnchorPolicy", object()),
        )
    with pytest.raises(FingerprintPolicyError, match="immutable tuples"):
        _ = anchor_coverage(
            cast("tuple[StableAnchor, ...]", cast("object", [])),
            (),
        )
    with pytest.raises(FingerprintPolicyError, match="foreign anchor"):
        _ = anchor_coverage((cast("StableAnchor", object()),), ())


def test_anchor_coverage_rejects_incoherent_direct_construction() -> None:
    """Coverage records cannot contradict their own matched/total counts."""
    with pytest.raises(FingerprintPolicyError, match="cannot exceed total"):
        _ = AnchorCoverage(matched=2, total=1, ratio=1.0)
    with pytest.raises(FingerprintPolicyError, match="does not match"):
        _ = AnchorCoverage(matched=1, total=2, ratio=1.0)
    with pytest.raises(FingerprintPolicyError, match="non-negative integer"):
        _ = AnchorCoverage(matched=True, total=1, ratio=1.0)


def test_stable_anchor_rejects_malformed_digest_and_offset() -> None:
    """Direct anchor records require exact SHA-256 bytes and integer offsets."""
    with pytest.raises(FingerprintPolicyError, match="exactly 32 bytes"):
        _ = StableAnchor(digest=b"short", offset=0)
    with pytest.raises(FingerprintPolicyError, match="non-negative integer"):
        _ = StableAnchor(digest=b"x" * 32, offset=True)
    with pytest.raises(FingerprintPolicyError, match="non-negative integer"):
        _ = StableAnchor(digest=b"x" * 32, offset=-1)


@pytest.mark.parametrize("hook", ["slot", "getattribute"])
@pytest.mark.parametrize(
    ("field", "forged"),
    [("window_bytes", 4), ("selection_modulus", 1)],
)
def test_anchor_selection_ignores_late_policy_field_forgery(
    monkeypatch: pytest.MonkeyPatch, hook: str, field: str, forged: int
) -> None:
    """Mutable policy class accessors cannot redefine source anchor windows."""
    data = _synthetic_bytes("policy-slot")
    policy = AnchorPolicy(window_bytes=16, selection_modulus=17)
    expected = stable_anchors(data, policy)
    calls = 0
    original = AnchorPolicy.__getattribute__

    def forged_attribute(value: AnchorPolicy, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return forged
        return cast("object", original(value, name))

    def forged_property(_value: AnchorPolicy) -> object:
        nonlocal calls
        calls += 1
        return forged

    with monkeypatch.context() as patch:
        if hook == "slot":
            patch.setattr(AnchorPolicy, field, property(forged_property))
        else:
            patch.setattr(AnchorPolicy, "__getattribute__", forged_attribute)
        observed = stable_anchors(data, policy)
    assert observed == expected
    assert calls == 0, "mutable policy getter was used for source evidence"


@pytest.mark.parametrize("field", ["window_bytes", "selection_modulus"])
def test_anchor_policy_constructor_ignores_late_getattribute_forgery(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """A class hook cannot disguise an invalid stored policy dimension."""
    original = AnchorPolicy.__getattribute__

    def forged_attribute(value: AnchorPolicy, name: str) -> object:
        if name == field:
            return 16
        return cast("object", original(value, name))

    with monkeypatch.context() as patch:
        patch.setattr(AnchorPolicy, "__getattribute__", forged_attribute)
        with pytest.raises(FingerprintPolicyError, match="must be integers"):
            _ = AnchorPolicy(**{field: True})


@pytest.mark.parametrize("hook", ["slot", "getattribute"])
def test_anchor_coverage_ignores_late_digest_forgery(
    monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """A mutable digest reader cannot promote unrelated source evidence."""
    reference = StableAnchor(digest=b"r" * 32, offset=0)
    unrelated = StableAnchor(digest=b"c" * 32, offset=0)
    original = StableAnchor.__getattribute__
    calls = 0

    def forged_attribute(value: StableAnchor, name: str) -> object:
        nonlocal calls
        if name == "digest":
            calls += 1
            return reference.digest if value is unrelated else b"r" * 32
        return cast("object", original(value, name))

    def forged_property(_value: StableAnchor) -> object:
        nonlocal calls
        calls += 1
        return b"r" * 32

    with monkeypatch.context() as patch:
        if hook == "slot":
            patch.setattr(StableAnchor, "digest", property(forged_property))
        else:
            patch.setattr(StableAnchor, "__getattribute__", forged_attribute)
        observed = anchor_coverage((reference,), (unrelated,))
    assert observed == AnchorCoverage(matched=0, total=1, ratio=0.0)
    assert calls == 0, "mutable digest getter affected lineage coverage"


def test_stable_anchor_constructor_ignores_late_getattribute_forgery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct anchor construction validates the stored digest, not a hook."""
    original = StableAnchor.__getattribute__

    def forged_attribute(value: StableAnchor, name: str) -> object:
        if name == "digest":
            return b"r" * 32
        return cast("object", original(value, name))

    with monkeypatch.context() as patch:
        patch.setattr(StableAnchor, "__getattribute__", forged_attribute)
        with pytest.raises(FingerprintPolicyError, match="exactly 32 bytes"):
            _ = StableAnchor(digest=b"short", offset=0)


def test_anchor_coverage_constructor_ignores_late_getattribute_forgery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late accessor cannot disguise inconsistent matched and total slots."""
    original = AnchorCoverage.__getattribute__

    def forged_attribute(value: AnchorCoverage, name: str) -> object:
        if name == "matched":
            return 1
        return cast("object", original(value, name))

    with monkeypatch.context() as patch:
        patch.setattr(AnchorCoverage, "__getattribute__", forged_attribute)
        with pytest.raises(FingerprintPolicyError, match="cannot exceed total"):
            _ = AnchorCoverage(matched=2, total=1, ratio=1.0)


def test_anchor_selection_ignores_late_digest_getattribute_forgery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Selected anchors are deduplicated by their stored SHA digests."""
    data = _synthetic_bytes("digest-deduplication")
    expected = stable_anchors(data)
    assert len(expected) > 1
    original = StableAnchor.__getattribute__
    calls = 0

    def forged_attribute(value: StableAnchor, name: str) -> object:
        nonlocal calls
        if name == "digest":
            calls += 1
            return b"x" * 32
        return cast("object", original(value, name))

    with monkeypatch.context() as patch:
        patch.setattr(StableAnchor, "__getattribute__", forged_attribute)
        observed = stable_anchors(data)
    assert observed == expected
    assert calls == 0, "mutable digest getter changed anchor deduplication"


@pytest.mark.parametrize("field", ["digest", "offset"])
def test_stable_anchor_constructor_rejects_forged_invalid_fields(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """A late getter cannot hide invalid raw anchor metadata."""
    original = StableAnchor.__getattribute__

    def forged_attribute(value: StableAnchor, name: str) -> object:
        if name == field:
            return 0 if field == "offset" else b"x" * 32
        return cast("object", original(value, name))

    with monkeypatch.context() as patch:
        patch.setattr(StableAnchor, "__getattribute__", forged_attribute)
        with pytest.raises(FingerprintPolicyError):
            _ = StableAnchor(
                digest=b"short" if field == "digest" else b"x" * 32,
                offset=-1 if field == "offset" else 0,
            )
