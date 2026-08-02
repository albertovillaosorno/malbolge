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

from dataclasses import dataclass

_ZERO = 0


class MappedViewError(ValueError):
    """Raised when canonical-to-raw mapping metadata is malformed."""


@dataclass(frozen=True, slots=True)
class MappedUnit:
    """One canonical identity unit and its half-open raw byte span."""

    canonical: bytes
    raw_start: int
    raw_end: int

    def __post_init__(self) -> None:
        """Reject empty canonical units or invalid raw ranges.

        Raises:
            MappedViewError: Canonical bytes or raw coordinates are invalid.

        """
        if not self.canonical:
            message = "mapped canonical unit must be non-empty"
            raise MappedViewError(message)
        if self.raw_start < _ZERO or self.raw_end < self.raw_start:
            message = "mapped raw span is invalid"
            raise MappedViewError(message)


@dataclass(frozen=True, slots=True)
class MappedView:
    """Raw source bytes plus sorted non-overlapping canonical units."""

    raw: bytes
    units: tuple[MappedUnit, ...]

    def __post_init__(self) -> None:
        """Require spans to stay inside raw bytes and remain ordered.

        Raises:
            MappedViewError: A unit escapes raw bytes or overlaps a prior unit.

        """
        previous_end = _ZERO
        for unit in self.units:
            if unit.raw_end > len(self.raw):
                message = "mapped unit escapes raw source bytes"
                raise MappedViewError(message)
            if unit.raw_start < previous_end:
                message = "mapped units overlap or reorder raw source spans"
                raise MappedViewError(message)
            previous_end = max(previous_end, unit.raw_end)

    @property
    def canonical(self) -> bytes:
        """Concatenated canonical identity stream."""
        return b"".join(unit.canonical for unit in self.units)

    @property
    def keys(self) -> tuple[bytes, ...]:
        """Canonical unit sequence for placement matching."""
        return tuple(unit.canonical for unit in self.units)
