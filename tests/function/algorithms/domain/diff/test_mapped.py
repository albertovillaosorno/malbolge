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
from dataclasses import fields, replace
from types import MemberDescriptorType, SimpleNamespace
from typing import cast

import pytest
from algorithms.diff.mapped import (
    MappedUnit,
    MappedView,
    MappedViewError,
    read_mapped_unit,
    read_mapped_view,
)

_CANONICAL_PAIR = b"AB"
_CANONICAL_WITH_MARKER = b"AE"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("canonical", b""),
        ("canonical", bytearray(b"A")),
        ("raw_start", -1),
        ("raw_start", True),
        ("raw_end", -1),
        ("raw_end", True),
    ],
)
def test_mapped_view_revalidates_fabricated_native_unit(
    field: str, invalid: object
) -> None:
    """Exact native units must retain their own coordinate/content contract."""
    unit = object.__new__(MappedUnit)
    values: dict[str, object] = {
        "canonical": b"A", "raw_start": 0, "raw_end": 1
    }
    values[field] = invalid
    for name, value in values.items():
        slot = cast("MemberDescriptorType", MappedUnit.__dict__[name])
        slot.__set__(unit, value)
    with pytest.raises(MappedViewError):
        _ = MappedView(b"raw", (unit,))


@pytest.mark.parametrize("missing", ["canonical", "raw_start", "raw_end"])
def test_mapped_view_rejects_incomplete_native_unit(missing: str) -> None:
    """Uninitialized native unit slots must fail with typed errors."""
    unit = object.__new__(MappedUnit)
    values: dict[str, object] = {
        "canonical": b"A", "raw_start": 0, "raw_end": 1
    }
    for name, value in values.items():
        if name == missing:
            continue
        slot = cast("MemberDescriptorType", MappedUnit.__dict__[name])
        slot.__set__(unit, value)
    with pytest.raises(MappedViewError, match="incomplete native unit"):
        _ = MappedView(b"raw", (unit,))


@pytest.mark.parametrize("property_name", ["canonical", "keys"])
@pytest.mark.parametrize("invalid", ["empty-unit", "mutable-raw", "missing-units"])
def test_mapped_properties_revalidate_fabricated_view(
    property_name: str, invalid: str
) -> None:
    """Direct native allocation cannot promote malformed canonical identity."""
    view = object.__new__(MappedView)
    values: dict[str, object] = {
        "raw": b"raw", "units": (MappedUnit(b"A", 0, 1),)
    }
    if invalid == "empty-unit":
        unit = object.__new__(MappedUnit)
        for name, value in {"canonical": b"", "raw_start": 0, "raw_end": 0}.items():
            slot = cast("MemberDescriptorType", MappedUnit.__dict__[name])
            slot.__set__(unit, value)
        values["units"] = (unit,)
    elif invalid == "mutable-raw":
        values["raw"] = bytearray(b"raw")
    else:
        del values["units"]
    for name, value in values.items():
        slot = cast("MemberDescriptorType", MappedView.__dict__[name])
        slot.__set__(view, value)
    with pytest.raises(MappedViewError):
        _ = view.canonical if property_name == "canonical" else view.keys


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

    def forged_max(*_values: object) -> int:
        return 0

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "max", forged_max)
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

    def forged_any(_values: object) -> bool:
        return False

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", forged_any)
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


@pytest.mark.parametrize("field", ["canonical", "raw_start", "raw_end"])
def test_mapped_unit_constructor_ignores_late_validator_override(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Replacing the class post-init method cannot admit malformed storage."""
    values: dict[str, object] = {
        "canonical": b"A", "raw_start": 0, "raw_end": 1
    }
    values[field] = bytearray(b"A") if field == "canonical" else True
    calls = 0

    def skip_validation(_value: MappedUnit) -> None:
        nonlocal calls
        calls += 1

    with monkeypatch.context() as patched:
        patched.setattr(MappedUnit, "__post_init__", skip_validation)
        constructor = cast("Callable[..., MappedUnit]", MappedUnit)
        with pytest.raises(MappedViewError):
            _ = constructor(**values)
    assert calls == 0, "late unit validator override gained authoring authority"


@pytest.mark.parametrize("field", ["raw", "units", "span"])
def test_mapped_view_constructor_ignores_late_validator_override(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """A late class validation hook cannot admit mutable or escaping views."""
    values: dict[str, object] = {
        "raw": b"a", "units": (MappedUnit(b"A", 0, 1),)
    }
    if field == "raw":
        values["raw"] = bytearray(b"a")
    elif field == "units":
        values["units"] = [MappedUnit(b"A", 0, 1)]
    else:
        values["units"] = (MappedUnit(b"A", 0, 2),)
    calls = 0

    def skip_validation(_value: MappedView) -> None:
        nonlocal calls
        calls += 1

    with monkeypatch.context() as patched:
        patched.setattr(MappedView, "__post_init__", skip_validation)
        constructor = cast("Callable[..., MappedView]", MappedView)
        with pytest.raises(MappedViewError):
            _ = constructor(**values)
    assert calls == 0, "late view validator override gained authoring authority"



def test_mapped_explicit_initializers_preserve_dataclass_replacement() -> None:
    """Pinned validation still preserves normal frozen-dataclass replacement."""
    unit = MappedUnit(b"A", 0, 1)
    moved = replace(unit, raw_start=1, raw_end=2)
    assert moved.raw_start == 1 and moved.raw_end == 2
    with pytest.raises(MappedViewError, match="invalid"):
        _ = replace(unit, raw_end=-1)

    view = MappedView(b"a", (unit,))
    expanded = replace(view, raw=b"aa")
    assert expanded.units == (unit,)
    with pytest.raises(MappedViewError, match="escapes"):
        _ = replace(expanded, units=(MappedUnit(b"B", 0, 3),))


@pytest.mark.parametrize(
    ("valid", "field", "invalid"),
    [
        (MappedUnit(b"A", 0, 1), "canonical", b""),
        (MappedUnit(b"A", 0, 1), "raw_start", -1),
        (MappedUnit(b"A", 0, 1), "raw_end", -1),
        (MappedView(b"a", (MappedUnit(b"A", 0, 1),)), "raw", bytearray(b"a")),
        (MappedView(b"a", (MappedUnit(b"A", 0, 1),)), "units", []),
    ],
)
def test_mapped_constructors_ignore_late_class_field_setters(
    monkeypatch: pytest.MonkeyPatch,
    valid: MappedUnit | MappedView,
    field: str,
    invalid: object,
) -> None:
    """Late class setters must not launder invalid canonical/raw metadata."""
    owner = type(valid)
    factory = cast("Callable[..., object]", owner)
    values = {datum.name: getattr(valid, datum.name) for datum in fields(valid)}
    original = cast("object", values[field])
    values[field] = invalid
    slot = cast("MemberDescriptorType", owner.__dict__[field])
    calls = 0

    def forged_getter(_record: object) -> object:
        return original

    def forged_setter(record: object, _value: object) -> None:
        nonlocal calls
        calls += 1
        slot.__set__(record, original)

    with monkeypatch.context() as patch:
        patch.setattr(owner, field, property(forged_getter, forged_setter))
        with pytest.raises(MappedViewError):
            _ = factory(**values)
    assert calls == 0, "mutable setter rewrote the original mapped storage"


@pytest.mark.parametrize("field,invalid", [
    ("canonical", b""),
    ("canonical", bytearray(b"A")),
    ("raw_start", True),
    ("raw_end", -1),
])
def test_public_mapped_unit_reader_revalidates_native_storage(
    field: str, invalid: object
) -> None:
    """Public mapped reads cannot admit a fabricated same-type unit."""
    unit = object.__new__(MappedUnit)
    values: dict[str, object] = {"canonical": b"A", "raw_start": 0, "raw_end": 1}
    values[field] = invalid
    for name, value in values.items():
        slot = cast("MemberDescriptorType", MappedUnit.__dict__[name])
        slot.__set__(unit, value)
    with pytest.raises(MappedViewError):
        _ = read_mapped_unit(unit)


@pytest.mark.parametrize("corruption", [
    "mutable-raw", "mutable-units", "escaping-unit", "missing-units",
])
def test_public_mapped_view_reader_revalidates_native_storage(
    corruption: str,
) -> None:
    """Semantic consumers must not read constructor-bypassed canonical views."""
    view = object.__new__(MappedView)
    raw: object = b"abc"
    units: object = (MappedUnit(b"A", 0, 1),)
    if corruption == "mutable-raw":
        raw = bytearray(b"abc")
    elif corruption == "mutable-units":
        units = list(cast("tuple[MappedUnit, ...]", units))
    elif corruption == "escaping-unit":
        units = (MappedUnit(b"A", 0, 4),)
    raw_slot = cast("MemberDescriptorType", MappedView.__dict__["raw"])
    raw_slot.__set__(view, raw)
    if corruption != "missing-units":
        unit_slot = cast("MemberDescriptorType", MappedView.__dict__["units"])
        unit_slot.__set__(view, units)
    with pytest.raises(MappedViewError):
        _ = read_mapped_view(view)


@pytest.mark.parametrize("record", ["unit", "view"])
def test_public_mapped_readers_reject_uninitialized_native_records(
    record: str,
) -> None:
    """Uninitialized native mapped records produce typed boundary errors."""
    with pytest.raises(MappedViewError, match="incomplete"):
        if record == "unit":
            _ = read_mapped_unit(object.__new__(MappedUnit))
        else:
            _ = read_mapped_view(object.__new__(MappedView))


@pytest.mark.parametrize("record", ["unit", "view"])
def test_public_mapped_readers_ignore_late_validator_override(
    monkeypatch: pytest.MonkeyPatch, record: str
) -> None:
    """Late class validation hooks cannot admit invalid original storage."""
    calls = 0

    def replaced_validator(_value: object) -> None:
        nonlocal calls
        calls += 1

    if record == "unit":
        forged = object.__new__(MappedUnit)
        for name, value in {
            "canonical": bytearray(b"A"), "raw_start": 0, "raw_end": 1,
        }.items():
            slot = cast("MemberDescriptorType", MappedUnit.__dict__[name])
            slot.__set__(forged, value)
        owner = MappedUnit
        action = lambda: read_mapped_unit(forged)
    else:
        forged_view = object.__new__(MappedView)
        for name, value in {"raw": bytearray(b"A"), "units": ()}.items():
            slot = cast("MemberDescriptorType", MappedView.__dict__[name])
            slot.__set__(forged_view, value)
        owner = MappedView
        action = lambda: read_mapped_view(forged_view)
    with monkeypatch.context() as patched:
        patched.setattr(owner, "__post_init__", replaced_validator)
        with pytest.raises(MappedViewError):
            _ = action()
    assert calls == 0


@pytest.mark.parametrize("record", ["unit", "view"])
def test_public_mapped_readers_require_exact_record_types(record: str) -> None:
    """Foreign subclasses or records do not enter native slot readers."""
    if record == "unit":
        with pytest.raises(MappedViewError, match="exact MappedUnit"):
            _ = read_mapped_unit(cast("MappedUnit", object()))
    else:
        with pytest.raises(MappedViewError, match="exact MappedView"):
            _ = read_mapped_view(cast("MappedView", object()))


@pytest.mark.parametrize("property_name", ["canonical", "keys"])
def test_mapped_identity_properties_reject_foreign_native_view_subclass(
    property_name: str,
) -> None:
    """Inherited identity getters must not admit foreign mapped-view types."""

    class ForeignMappedView(MappedView):
        pass

    foreign = ForeignMappedView(b"a", (MappedUnit(b"A", 0, 1),))
    with pytest.raises(MappedViewError, match="exact MappedView"):
        _ = foreign.canonical if property_name == "canonical" else foreign.keys


@pytest.mark.parametrize("property_name", ["canonical", "keys"])
def test_mapped_identity_properties_reject_foreign_unbound_receiver(
    property_name: str,
) -> None:
    """Unbound native getters reject unrelated receivers with owned errors."""
    getter = cast("property", MappedView.__dict__[property_name]).fget
    assert getter is not None
    with pytest.raises(MappedViewError, match="exact MappedView"):
        _ = getter(object())
