# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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

from typing import cast

from algorithms.diff.mapped import MappedUnit
from algorithms.diff.mapped import MappedView
from algorithms.diff.mapped import MappedViewError
import pytest

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

    _expect(
        view.canonical == _CANONICAL_PAIR, "mapped canonical stream changed"
    )
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
