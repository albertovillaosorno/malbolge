# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Semantic compatible placement over canonical units mapped to raw bytes."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from algorithms.diff.mapped import MappedView

_ZERO = 0
_ONE = 1
_DEFAULT_CONTEXT_UNITS = 4
_UNIT_DOMAIN = b"semantic-placement-unit-v1\0"
_EQUAL_OPCODE = "equal"


class SemanticPlacementError(RuntimeError):
    """Raised when semantic edit placement is missing, ambiguous, or unsafe."""


@dataclass(frozen=True, slots=True)
class SemanticLocator:
    """Hashed source-unit range plus immediate canonical context."""

    source_digests: tuple[bytes, ...]
    before_digests: tuple[bytes, ...]
    after_digests: tuple[bytes, ...]

    def __post_init__(self) -> None:
        """Require at least one source or context digest.

        Raises:
            SemanticPlacementError: Locator has no semantic evidence.

        """
        if not (
            self.source_digests or self.before_digests or self.after_digests
        ):
            message = "semantic locator requires source or context evidence"
            raise SemanticPlacementError(message)


@dataclass(frozen=True, slots=True)
class SemanticEdit:
    """Target replacement relative to hashed canonical source units."""

    locator: SemanticLocator
    replacement: bytes
    replacement_digests: tuple[bytes, ...]


@dataclass(frozen=True, slots=True)
class SemanticAuthoringPlan:
    """Non-distributable semantic edit plan for one mapped source file."""

    edits: tuple[SemanticEdit, ...]


@dataclass(frozen=True, slots=True)
class _LocatedEdit:
    edit: SemanticEdit
    unit_start: int
    unit_end: int
    raw_start: int
    raw_end: int


def _frame(value: bytes) -> bytes:
    return len(value).to_bytes(8, byteorder="big") + value


def _unit_digest(canonical: bytes) -> bytes:
    return hashlib.sha256(_UNIT_DOMAIN + _frame(canonical)).digest()


def _view_digests(view: MappedView) -> tuple[bytes, ...]:
    return tuple(_unit_digest(unit.canonical) for unit in view.units)


def _replacement_bytes(view: MappedView, start: int, end: int) -> bytes:
    if start == end:
        return b""
    raw_start = view.units[start].raw_start
    raw_end = view.units[end - _ONE].raw_end
    return view.raw[raw_start:raw_end]


def _locator(
    source_digests: tuple[bytes, ...],
    start: int,
    end: int,
    *,
    context_units: int,
) -> SemanticLocator:
    before_start = max(_ZERO, start - context_units)
    after_end = min(len(source_digests), end + context_units)
    return SemanticLocator(
        source_digests=source_digests[start:end],
        before_digests=source_digests[before_start:start],
        after_digests=source_digests[end:after_end],
    )


def build_semantic_plan(
    source: MappedView,
    target: MappedView,
    *,
    context_units: int = _DEFAULT_CONTEXT_UNITS,
) -> SemanticAuthoringPlan:
    """Build semantic edits without plaintext source canonical units.

    Returns:
        Deterministic non-distributable edit plan containing only hashed source
        locators and target replacement bytes.

    Raises:
        SemanticPlacementError: Context width is invalid or an edit is
        unlocatable by construction.

    """
    if context_units < _ONE:
        message = "semantic placement context_units must be positive"
        raise SemanticPlacementError(message)
    source_digests = _view_digests(source)
    target_digests = _view_digests(target)
    matcher = SequenceMatcher(
        None,
        source_digests,
        target_digests,
        autojunk=False,
    )
    edits: list[SemanticEdit] = []
    for (
        tag,
        source_start,
        source_end,
        target_start,
        target_end,
    ) in matcher.get_opcodes():
        if tag == _EQUAL_OPCODE:
            continue
        edits.append(
            SemanticEdit(
                locator=_locator(
                    source_digests,
                    source_start,
                    source_end,
                    context_units=context_units,
                ),
                replacement=_replacement_bytes(
                    target, target_start, target_end
                ),
                replacement_digests=target_digests[target_start:target_end],
            )
        )
    return SemanticAuthoringPlan(edits=tuple(edits))


def _context_matches(
    candidate: tuple[bytes, ...],
    locator: SemanticLocator,
    start: int,
) -> bool:
    source_end = start + len(locator.source_digests)
    before_count = len(locator.before_digests)
    after_count = len(locator.after_digests)
    fits = start >= before_count and source_end + after_count <= len(candidate)
    source_matches = (
        fits and candidate[start:source_end] == locator.source_digests
    )
    before_matches = (
        source_matches
        and candidate[start - before_count : start] == locator.before_digests
    )
    return bool(
        before_matches
        and candidate[source_end : source_end + after_count]
        == locator.after_digests
    )


def _candidate_positions(
    candidate: tuple[bytes, ...],
    locator: SemanticLocator,
) -> tuple[int, ...]:
    source_count = len(locator.source_digests)
    final_start = len(candidate) - source_count
    return tuple(
        start
        for start in range(final_start + _ONE)
        if _context_matches(candidate, locator, start)
    )


def _unique_position(
    candidate: tuple[bytes, ...],
    locator: SemanticLocator,
) -> int:
    positions = _candidate_positions(candidate, locator)
    if len(positions) != _ONE:
        message = (
            "semantic source locator is missing or ambiguous: "
            f"found {len(positions)} placements"
        )
        raise SemanticPlacementError(message)
    return positions[0]


def _raw_span(view: MappedView, start: int, end: int) -> tuple[int, int]:
    if start == end:
        offset = (
            view.units[start].raw_start
            if start < len(view.units)
            else len(view.raw)
        )
        return offset, offset
    return view.units[start].raw_start, view.units[end - _ONE].raw_end


def _locate_edits(
    candidate: MappedView,
    plan: SemanticAuthoringPlan,
) -> tuple[_LocatedEdit, ...]:
    digests = _view_digests(candidate)
    located: list[_LocatedEdit] = []
    for edit in plan.edits:
        unit_start = _unique_position(digests, edit.locator)
        unit_end = unit_start + len(edit.locator.source_digests)
        raw_start, raw_end = _raw_span(candidate, unit_start, unit_end)
        located.append(
            _LocatedEdit(
                edit=edit,
                unit_start=unit_start,
                unit_end=unit_end,
                raw_start=raw_start,
                raw_end=raw_end,
            )
        )
    ordered = tuple(
        sorted(located, key=lambda item: (item.raw_start, item.raw_end))
    )
    previous_raw_end = _ZERO
    previous_unit_end = _ZERO
    for item in ordered:
        if (
            item.raw_start < previous_raw_end
            or item.unit_start < previous_unit_end
        ):
            message = "semantic edits overlap or reorder in candidate source"
            raise SemanticPlacementError(message)
        previous_raw_end = item.raw_end
        previous_unit_end = item.unit_end
    return ordered


def _apply_raw_edits(raw: bytes, edits: tuple[_LocatedEdit, ...]) -> bytes:
    output = raw
    for item in reversed(edits):
        output = (
            output[: item.raw_start]
            + item.edit.replacement
            + output[item.raw_end :]
        )
    return output


def _expected_digests(
    candidate: MappedView,
    edits: tuple[_LocatedEdit, ...],
) -> tuple[bytes, ...]:
    expected = list(_view_digests(candidate))
    for item in reversed(edits):
        expected[item.unit_start : item.unit_end] = (
            item.edit.replacement_digests
        )
    return tuple(expected)


def apply_semantic_plan(
    candidate: MappedView,
    plan: SemanticAuthoringPlan,
    mapper: Callable[[bytes], MappedView],
) -> bytes:
    """Apply mapped semantic edits while preserving unaffected candidate bytes.

    Returns:
        Candidate raw bytes with uniquely located semantic changes applied.

    Raises:
        SemanticPlacementError: Placement is missing/ambiguous, edits overlap,
        or re-tokenization does not match the intended canonical unit sequence.

    """
    if not plan.edits:
        return candidate.raw
    located = _locate_edits(candidate, plan)
    expected = _expected_digests(candidate, located)
    output = _apply_raw_edits(candidate.raw, located)
    observed = _view_digests(mapper(output))
    if observed != expected:
        message = "semantic edit changed canonical units at a replacement seam"
        raise SemanticPlacementError(message)
    return output
