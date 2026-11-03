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
#   - Generic canonical units mapped back to raw source byte spans.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Generic canonical units mapped back to raw source byte spans."""

from __future__ import annotations

import builtins
from collections.abc import Callable
from dataclasses import dataclass
from types import MemberDescriptorType
from typing import cast

_ZERO = 0
# Preserve exact-record admission after untrusted domain callback execution.
_NATIVE_ANY = builtins.any
_NATIVE_TYPE = builtins.type
_NATIVE_BYTES = builtins.bytes
_NATIVE_INT = builtins.int
_NATIVE_LEN = builtins.len
_NATIVE_TUPLE = builtins.tuple
_NATIVE_OBJECT_SETATTR = object.__setattr__


class MappedViewError(ValueError):
    """Raised when canonical-to-raw mapping metadata is malformed."""


@dataclass(frozen=True, slots=True, init=False)
class MappedUnit:
    """One canonical identity unit and its half-open raw byte span."""

    canonical: bytes
    raw_start: int
    raw_end: int

    def __init__(self, canonical: bytes, raw_start: int, raw_end: int) -> None:
        """Construct and validate through the original stored-field checker."""
        _NATIVE_OBJECT_SETATTR(self, "canonical", canonical)
        _NATIVE_OBJECT_SETATTR(self, "raw_start", raw_start)
        _NATIVE_OBJECT_SETATTR(self, "raw_end", raw_end)
        _MAPPED_UNIT_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject empty canonical units or invalid raw ranges.

        Raises:
            MappedViewError: Canonical bytes or raw coordinates are invalid.

        """
        canonical, start, end = read_mapped_unit(self)
        if _NATIVE_TYPE(canonical) is not _NATIVE_BYTES or not canonical:
            message = "mapped canonical unit must be non-empty exact bytes"
            raise MappedViewError(message)
        if (
            _NATIVE_TYPE(start) is not _NATIVE_INT
            or _NATIVE_TYPE(end) is not _NATIVE_INT
        ):
            message = "mapped raw coordinates must use exact integers"
            raise MappedViewError(message)
        if start < _ZERO or end < start:
            message = "mapped raw span is invalid"
            raise MappedViewError(message)


# Dataclass-generated initializers look up ``__post_init__`` on the class.
# Pin the original validation method so later class hooks cannot skip it.
_MAPPED_UNIT_VALIDATOR = cast(
    "Callable[[MappedUnit], None]", MappedUnit.__dict__["__post_init__"]
)

# Slotted frozen records still expose mutable class descriptors to callbacks.
# Preserve the initial storage readers before domain code can replace them.
_UNIT_CANONICAL_SLOT = cast(
    "MemberDescriptorType", MappedUnit.__dict__["canonical"]
)
_UNIT_START_SLOT = cast(
    "MemberDescriptorType", MappedUnit.__dict__["raw_start"]
)
_UNIT_END_SLOT = cast("MemberDescriptorType", MappedUnit.__dict__["raw_end"])


def read_mapped_unit(unit: MappedUnit) -> tuple[bytes, int, int]:
    """Read canonical bytes and coordinates from original unit storage."""
    return (
        cast("bytes", _UNIT_CANONICAL_SLOT.__get__(unit, MappedUnit)),
        cast("int", _UNIT_START_SLOT.__get__(unit, MappedUnit)),
        cast("int", _UNIT_END_SLOT.__get__(unit, MappedUnit)),
    )


def _validate_view_units(raw: bytes, units: tuple[MappedUnit, ...]) -> None:
    previous_end = _ZERO
    for unit in units:
        _, start, end = read_mapped_unit(unit)
        if end > _NATIVE_LEN(raw):
            message = "mapped unit escapes raw source bytes"
            raise MappedViewError(message)
        if start < previous_end:
            message = "mapped units overlap or reorder raw source spans"
            raise MappedViewError(message)
        previous_end = end


@dataclass(frozen=True, slots=True, init=False)
class MappedView:
    """Raw source bytes plus sorted non-overlapping canonical units."""

    raw: bytes
    units: tuple[MappedUnit, ...]

    def __init__(self, raw: bytes, units: tuple[MappedUnit, ...]) -> None:
        """Construct and validate through the original stored-field checker."""
        _NATIVE_OBJECT_SETATTR(self, "raw", raw)
        _NATIVE_OBJECT_SETATTR(self, "units", units)
        _MAPPED_VIEW_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require spans to stay inside raw bytes and remain ordered.

        Raises:
            MappedViewError: A unit escapes raw bytes or overlaps a prior unit.

        """
        raw, units = read_mapped_view(self)
        if _NATIVE_TYPE(raw) is not _NATIVE_BYTES:
            message = "mapped raw source must use exact bytes"
            raise MappedViewError(message)
        if _NATIVE_TYPE(units) is not _NATIVE_TUPLE:
            message = "mapped units must use the exact immutable tuple type"
            raise MappedViewError(message)
        if _NATIVE_ANY(
            _NATIVE_TYPE(unit) is not MappedUnit for unit in units
        ):
            message = "mapped view contains a foreign unit record"
            raise MappedViewError(message)
        _validate_view_units(raw, units)

    @property
    def canonical(self) -> bytes:
        """Concatenated canonical identity stream."""
        return b"".join(
            read_mapped_unit(unit)[0] for unit in read_mapped_view(self)[1]
        )

    @property
    def keys(self) -> tuple[bytes, ...]:
        """Canonical unit sequence for placement matching."""
        return _NATIVE_TUPLE(
            read_mapped_unit(unit)[0] for unit in read_mapped_view(self)[1]
        )


_MAPPED_VIEW_VALIDATOR = cast(
    "Callable[[MappedView], None]", MappedView.__dict__["__post_init__"]
)
_VIEW_RAW_SLOT = cast("MemberDescriptorType", MappedView.__dict__["raw"])
_VIEW_UNITS_SLOT = cast("MemberDescriptorType", MappedView.__dict__["units"])


def read_mapped_view(view: MappedView) -> tuple[bytes, tuple[MappedUnit, ...]]:
    """Read raw bytes and units without invoking mutable class getters."""
    return (
        cast("bytes", _VIEW_RAW_SLOT.__get__(view, MappedView)),
        cast(
            "tuple[MappedUnit, ...]",
            _VIEW_UNITS_SLOT.__get__(view, MappedView),
        ),
    )
