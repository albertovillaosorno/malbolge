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
#   - Synthetic invariants for canonical units mapped to raw source spans.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic invariants for canonical units mapped to raw source spans."""

import builtins
from collections.abc import Callable
from types import SimpleNamespace
from typing import cast

import pytest
from algorithms.diff.mapped import MappedUnit, MappedView, MappedViewError

_CANONICAL_PAIR = b"AB"
_CANONICAL_WITH_MARKER = b"AE"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_mapped_view_concatenates_canonical_units() -> None:
    """Keep canonical identity independent from raw presentation gaps."""
    view = MappedView(
        raw=b"a  b",
        units=(
            MappedUnit(canonical=b"A", raw_start=0, raw_end=1),
            MappedUnit(canonical=b"B", raw_start=3, raw_end=4),
        ),
    )

    _expect(view.canonical == _CANONICAL_PAIR, "mapped canonical stream changed")
    _expect(view.keys == (b"A", b"B"), "mapped unit sequence changed")


def test_zero_width_marker_is_allowed_between_units() -> None:
    """Permit zero-width semantic markers such as directive ends."""
    view = MappedView(
        raw=b"a\n",
        units=(
            MappedUnit(canonical=b"A", raw_start=0, raw_end=1),
            MappedUnit(canonical=b"E", raw_start=1, raw_end=1),
        ),
    )

    _expect(
        view.canonical == _CANONICAL_WITH_MARKER,
        "zero-width marker changed identity",
    )


def test_overlapping_or_escaping_units_fail_closed() -> None:
    """Reject ambiguous raw mappings before compatible placement uses them."""
    with pytest.raises(MappedViewError, match="overlap"):
        _ = MappedView(
            raw=b"abc",
            units=(
                MappedUnit(canonical=b"A", raw_start=0, raw_end=2),
                MappedUnit(canonical=b"B", raw_start=1, raw_end=3),
            ),
        )
    with pytest.raises(MappedViewError, match="escapes"):
        _ = MappedView(
            raw=b"abc",
            units=(MappedUnit(canonical=b"A", raw_start=0, raw_end=4),),
        )


def test_mapped_view_rejects_overlap_after_late_builtin_max_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consumer hooks cannot rewrite the raw span ordering check."""
    first = MappedUnit(canonical=b"A", raw_start=0, raw_end=2)
    overlapping = MappedUnit(canonical=b"B", raw_start=1, raw_end=3)
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "max", lambda *_values: 0)
        with pytest.raises(MappedViewError, match="overlap"):
            _ = MappedView(raw=b"abc", units=(first, overlapping))


def test_mapped_view_rejects_foreign_unit_after_late_any_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A shape-compatible object must never cross canonical mapping trust."""
    foreign = cast(
        "MappedUnit",
        cast("object", SimpleNamespace(canonical=b"A", raw_start=0, raw_end=1)),
    )
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda values: False)
        try:
            _ = MappedView(raw=b"a", units=(foreign,))
        except MappedViewError:
            rejected = True
    assert rejected, "late any hook admitted a foreign canonical unit"


def test_mapped_bytes_reject_late_type_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutable bytes cannot masquerade as immutable canonical or raw data."""
    foreign = bytearray(b"a")
    native_type = type
    unit_rejected = False
    view_rejected = False

    def forged_type(value: object) -> type:
        return bytes if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = MappedUnit(cast("bytes", cast("object", foreign)), 0, 1)
        except MappedViewError:
            unit_rejected = True
        try:
            _ = MappedView(
                cast("bytes", cast("object", foreign)),
                (MappedUnit(b"A", 0, 1),),
            )
        except MappedViewError:
            view_rejected = True
    assert unit_rejected, "late type admitted mutable canonical bytes"
    assert view_rejected, "late type admitted mutable raw bytes"


def test_mapped_coordinates_reject_late_type_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boolean offsets must not be admitted as exact raw coordinates."""
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return int if value is True else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = MappedUnit(b"A", True, 1)
        except MappedViewError:
            rejected = True
    assert rejected, "late type admitted a boolean source offset"


def test_mapped_view_rejects_foreign_unit_after_late_type_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged type verdict cannot admit a fake canonical unit record."""
    foreign = SimpleNamespace(canonical=b"A", raw_start=0, raw_end=1)
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return MappedUnit if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = MappedView(
                b"a", (cast("MappedUnit", cast("object", foreign)),)
            )
        except MappedViewError:
            rejected = True
    assert rejected, "late type admitted a foreign canonical unit"


def test_mapped_view_rejects_late_len_escape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing len cannot move a mapped span past true source length."""
    source = b"a"
    unit = MappedUnit(b"A", 0, 2)
    native_len = len
    rejected = False

    def forged_len(value: object) -> int:
        if value is source:
            return 2
        return native_len(cast("bytes", value))

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "len", forged_len)
        try:
            _ = MappedView(source, (unit,))
        except MappedViewError:
            rejected = True
    assert rejected, "late len admitted an escaping source span"


def test_mapped_keys_ignore_late_tuple_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical placement keys cannot be erased by a consumer hook."""
    view = MappedView(b"a", (MappedUnit(b"A", 0, 1),))

    def forged_tuple(values: object) -> tuple[bytes, ...]:
        del values
        return ()

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "tuple", forged_tuple)
        keys = view.keys
    assert keys == (b"A",)


def test_mapped_records_reject_foreign_runtime_metadata() -> None:
    """Mapped bytes, coordinates, and unit collections require exact types."""
    with pytest.raises(MappedViewError, match="exact bytes"):
        _ = MappedUnit(cast("bytes", cast("object", bytearray(b"A"))), 0, 1)
    with pytest.raises(MappedViewError, match="exact integers"):
        _ = MappedUnit(canonical=b"A", raw_start=True, raw_end=1)
    with pytest.raises(MappedViewError, match="exact bytes"):
        _ = MappedView(
            cast("bytes", cast("object", bytearray(b"a"))),
            (MappedUnit(b"A", 0, 1),),
        )
    with pytest.raises(MappedViewError, match="immutable tuple"):
        _ = MappedView(
            b"a",
            cast(
                "tuple[MappedUnit, ...]",
                cast("object", [MappedUnit(b"A", 0, 1)]),
            ),
        )
    with pytest.raises(MappedViewError, match="foreign unit"):
        _ = MappedView(b"a", (cast("MappedUnit", object()),))


def test_mapped_unit_rejects_late_bytes_alias_for_mutable_canonical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late bytes aliases cannot admit mutable canonical unit metadata."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bytes", bytearray)
        try:
            _ = MappedUnit(
                cast("bytes", cast("object", bytearray(b"A"))), 0, 1
            )
        except MappedViewError:
            rejected = True
    assert rejected, "mutable canonical unit passed a late bytes alias"


def test_mapped_view_rejects_late_bytes_alias_for_mutable_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late bytes aliases cannot admit mutable raw source evidence."""
    unit = MappedUnit(b"A", 0, 1)
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bytes", bytearray)
        try:
            _ = MappedView(
                cast("bytes", cast("object", bytearray(b"a"))),
                (unit,),
            )
        except MappedViewError:
            rejected = True
    assert rejected, "mutable mapped source passed a late bytes alias"


def test_mapped_unit_rejects_late_integer_alias_for_boolean_span(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late int aliases cannot certify Boolean source offsets."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "int", bool)
        try:
            _ = MappedUnit(canonical=b"A", raw_start=True, raw_end=True)
        except MappedViewError:
            rejected = True
    assert rejected, "Boolean raw offsets passed a late integer alias"


def test_mapped_native_metadata_survives_late_builtin_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late bytes/int aliases do not reject valid native mapping records."""
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "int", bool)
        unit = MappedUnit(b"A", 0, 1)
    assert unit.raw_start == 0

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bytes", bytearray)
        view = MappedView(b"a", (MappedUnit(b"A", 0, 1),))
    assert view.canonical == _CANONICAL_PAIR[:1]


@pytest.mark.parametrize(
    ("field", "invalid", "forged"),
    [
        ("canonical", bytearray(b"A"), b"A"),
        ("raw_start", True, 0),
        ("raw_end", True, 1),
    ],
)
def test_mapped_unit_constructor_ignores_late_class_getter(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid: object,
    forged: object,
) -> None:
    """Malformed stored unit evidence cannot be laundered by class hooks."""
    values: dict[str, object] = {
        "canonical": b"A", "raw_start": 0, "raw_end": 1
    }
    values[field] = invalid
    original = MappedUnit.__getattribute__
    calls = 0

    def getter(value: MappedUnit, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return forged
        return cast("object", original(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(MappedUnit, "__getattribute__", getter)
        with pytest.raises(MappedViewError):
            constructor = cast("Callable[..., MappedUnit]", MappedUnit)
            _ = constructor(**values)
    assert calls == 0, "late class getter hid malformed unit storage"


@pytest.mark.parametrize(
    ("field", "invalid", "forged"),
    [
        ("raw", bytearray(b"a"), b"a"),
        ("units", [MappedUnit(b"A", 0, 1)], (MappedUnit(b"A", 0, 1),)),
    ],
)
def test_mapped_view_constructor_ignores_late_class_getter(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid: object,
    forged: object,
) -> None:
    """A late mapped-view hook must not conceal a mutable input container."""
    values: dict[str, object] = {
        "raw": b"a", "units": (MappedUnit(b"A", 0, 1),)
    }
    values[field] = invalid
    original = MappedView.__getattribute__
    calls = 0

    def getter(value: MappedView, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return forged
        return cast("object", original(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(MappedView, "__getattribute__", getter)
        with pytest.raises(MappedViewError):
            constructor = cast("Callable[..., MappedView]", MappedView)
            _ = constructor(**values)
    assert calls == 0, "late class getter hid malformed mapped-view storage"


@pytest.mark.parametrize("hook", ["getattribute", "slot"])
def test_mapped_keys_ignore_late_unit_canonical_hook(
    monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """Placement identity reads the original unit's immutable bytes."""
    view = MappedView(b"a", (MappedUnit(b"A", 0, 1),))
    original = MappedUnit.__getattribute__
    calls = 0

    def getter(value: MappedUnit, name: str) -> object:
        nonlocal calls
        if name == "canonical":
            calls += 1
            return b"FORGED"
        return cast("object", original(value, name))

    def forged_property(_value: MappedUnit) -> bytes:
        return b"FORGED"

    with monkeypatch.context() as patched:
        if hook == "slot":
            patched.setattr(MappedUnit, "canonical", property(forged_property))
        else:
            patched.setattr(MappedUnit, "__getattribute__", getter)
        assert view.canonical == b"A"
        assert view.keys == (b"A",)
    assert calls == 0, "late canonical getter forged placement evidence"


@pytest.mark.parametrize("field", ["raw", "units"])
def test_mapped_keys_ignore_late_view_field_getter(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """The original mapped-unit tuple remains the only identity evidence."""
    view = MappedView(b"a", (MappedUnit(b"A", 0, 1),))
    original = MappedView.__getattribute__
    calls = 0

    def getter(value: MappedView, name: str) -> object:
        nonlocal calls
        if name == field:
            calls += 1
            return () if field == "units" else b"z"
        return cast("object", original(value, name))

    with monkeypatch.context() as patched:
        patched.setattr(MappedView, "__getattribute__", getter)
        assert view.canonical == b"A"
        assert view.keys == (b"A",)
    assert calls == 0, "late mapped view getter changed placement identity"
