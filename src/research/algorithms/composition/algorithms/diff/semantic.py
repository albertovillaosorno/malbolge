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
#   - Semantic compatible placement over canonical units mapped to raw bytes.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Semantic compatible placement over canonical units mapped to raw bytes."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
import hashlib
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff.mapped import MappedView

if TYPE_CHECKING:
    from collections.abc import Callable

_ZERO = 0
_ONE = 1
_SHA256_BYTES = hashlib.sha256().digest_size
_DEFAULT_CONTEXT_UNITS = 4
_UNIT_DOMAIN = b"semantic-placement-unit-v1\0"
_ANCHOR_WIDTHS = (8, 4, 2, 1)


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
        groups = (
            self.source_digests,
            self.before_digests,
            self.after_digests,
        )
        for group in groups:
            if type(group) is not tuple:
                message = "semantic locator digests must use immutable tuples"
                raise SemanticPlacementError(message)
            items = cast("tuple[object, ...]", group)
            if any(
                type(digest) is not bytes or len(digest) != _SHA256_BYTES
                for digest in items
            ):
                message = "semantic locator digests must be exact SHA-256 bytes"
                raise SemanticPlacementError(message)
        if not any(groups):
            message = "semantic locator requires source or context evidence"
            raise SemanticPlacementError(message)


@dataclass(frozen=True, slots=True)
class SemanticEdit:
    """Target replacement relative to hashed canonical source units."""

    locator: SemanticLocator
    replacement: bytes
    replacement_digests: tuple[bytes, ...]

    def __post_init__(self) -> None:
        """Require exact locator, replacement, and target digest metadata.

        Raises:
            SemanticPlacementError: Edit metadata is malformed.

        """
        if type(self.locator) is not SemanticLocator:
            message = "semantic edit locator must use the exact locator type"
            raise SemanticPlacementError(message)
        if type(self.replacement) is not bytes:
            message = "semantic replacement must use exact bytes"
            raise SemanticPlacementError(message)
        if type(self.replacement_digests) is not tuple:
            message = "semantic replacement digests must use an immutable tuple"
            raise SemanticPlacementError(message)
        items = cast("tuple[object, ...]", self.replacement_digests)
        if any(
            type(digest) is not bytes or len(digest) != _SHA256_BYTES
            for digest in items
        ):
            message = "semantic replacement digests must be exact SHA-256 bytes"
            raise SemanticPlacementError(message)


@dataclass(frozen=True, slots=True)
class SemanticAuthoringPlan:
    """Non-distributable semantic edit plan for one mapped source file."""

    edits: tuple[SemanticEdit, ...]

    def __post_init__(self) -> None:
        """Require one immutable sequence of exact semantic edits.

        Raises:
            SemanticPlacementError: Plan records are mutable or foreign.

        """
        if type(self.edits) is not tuple:
            message = "semantic edits must use the exact immutable tuple type"
            raise SemanticPlacementError(message)
        if any(type(edit) is not SemanticEdit for edit in self.edits):
            message = "semantic plan contains a foreign edit record"
            raise SemanticPlacementError(message)


@dataclass(frozen=True, slots=True)
class _LocatedEdit:
    edit: SemanticEdit
    unit_start: int
    unit_end: int
    raw_start: int
    raw_end: int


@dataclass(frozen=True, slots=True)
class _AnchorPair:
    source_start: int
    target_start: int


@dataclass(frozen=True, slots=True)
class _MatchBlock:
    source_start: int
    target_start: int
    length: int


@dataclass(frozen=True, slots=True)
class _EditRange:
    source_start: int
    source_end: int
    target_start: int
    target_end: int


@dataclass(frozen=True, slots=True)
class _MatchContext:
    source: tuple[bytes, ...]
    target: tuple[bytes, ...]


@dataclass(frozen=True, slots=True)
class _Region:
    source_start: int
    source_end: int
    target_start: int
    target_end: int


@dataclass(frozen=True, slots=True)
class _SemanticBuildContext:
    source_digests: tuple[bytes, ...]
    target_digests: tuple[bytes, ...]
    target: MappedView
    context_units: int


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


def _common_prefix_length(context: _MatchContext, region: _Region) -> int:
    limit = min(
        region.source_end - region.source_start,
        region.target_end - region.target_start,
    )
    length = _ZERO
    while (
        length < limit
        and context.source[region.source_start + length]
        == context.target[region.target_start + length]
    ):
        length += _ONE
    return length


def _common_suffix_length(context: _MatchContext, region: _Region) -> int:
    limit = min(
        region.source_end - region.source_start,
        region.target_end - region.target_start,
    )
    length = _ZERO
    while (
        length < limit
        and context.source[region.source_end - length - _ONE]
        == context.target[region.target_end - length - _ONE]
    ):
        length += _ONE
    return length


def _unique_windows(
    values: tuple[bytes, ...],
    start: int,
    end: int,
    *,
    width: int,
) -> dict[tuple[bytes, ...], int]:
    positions: dict[tuple[bytes, ...], int | None] = {}
    final_start = end - width
    for offset in range(start, final_start + _ONE):
        window = values[offset : offset + width]
        if window in positions:
            positions[window] = None
        else:
            positions[window] = offset
    return {
        window: offset
        for window, offset in positions.items()
        if offset is not None
    }


def _reconstruct_lis(
    pairs: tuple[_AnchorPair, ...],
    tail_indices: list[int],
    predecessors: list[int],
) -> tuple[_AnchorPair, ...]:
    cursor = tail_indices[-_ONE]
    selected: list[_AnchorPair] = []
    while cursor >= _ZERO:
        selected.append(pairs[cursor])
        cursor = predecessors[cursor]
    selected.reverse()
    return tuple(selected)


def _lis_pairs(pairs: tuple[_AnchorPair, ...]) -> tuple[_AnchorPair, ...]:
    if not pairs:
        return ()
    tail_targets: list[int] = []
    tail_indices: list[int] = []
    predecessors = [-_ONE] * len(pairs)
    for index, pair in enumerate(pairs):
        position = bisect_left(tail_targets, pair.target_start)
        if position == len(tail_targets):
            tail_targets.append(pair.target_start)
            tail_indices.append(index)
        else:
            tail_targets[position] = pair.target_start
            tail_indices[position] = index
        if position > _ZERO:
            predecessors[index] = tail_indices[position - _ONE]
    return _reconstruct_lis(pairs, tail_indices, predecessors)


def _non_overlapping_pairs(
    pairs: tuple[_AnchorPair, ...],
    width: int,
) -> tuple[_AnchorPair, ...]:
    selected: list[_AnchorPair] = []
    source_end = -_ONE
    target_end = -_ONE
    for pair in pairs:
        if pair.source_start < source_end or pair.target_start < target_end:
            continue
        selected.append(pair)
        source_end = pair.source_start + width
        target_end = pair.target_start + width
    return tuple(selected)


def _window_pairs(
    context: _MatchContext,
    region: _Region,
    width: int,
) -> tuple[_AnchorPair, ...]:
    source_windows = _unique_windows(
        context.source,
        region.source_start,
        region.source_end,
        width=width,
    )
    target_windows = _unique_windows(
        context.target,
        region.target_start,
        region.target_end,
        width=width,
    )
    return tuple(
        sorted(
            (
                _AnchorPair(source_offset, target_windows[window])
                for window, source_offset in source_windows.items()
                if window in target_windows
            ),
            key=lambda pair: (pair.source_start, pair.target_start),
        )
    )


def _anchor_pairs(
    context: _MatchContext,
    region: _Region,
) -> tuple[int, tuple[_AnchorPair, ...]]:
    source_length = region.source_end - region.source_start
    target_length = region.target_end - region.target_start
    for width in _ANCHOR_WIDTHS:
        if width > source_length or width > target_length:
            continue
        pairs = _window_pairs(context, region, width)
        ordered = _non_overlapping_pairs(_lis_pairs(pairs), width)
        if ordered:
            return width, ordered
    return _ZERO, ()


def _merge_blocks(blocks: list[_MatchBlock]) -> list[_MatchBlock]:
    if not blocks:
        return []
    merged = [blocks[0]]
    for block in blocks[1:]:
        previous = merged[-_ONE]
        contiguous = (
            previous.source_start + previous.length == block.source_start
            and previous.target_start + previous.length == block.target_start
        )
        if contiguous:
            merged[-_ONE] = _MatchBlock(
                source_start=previous.source_start,
                target_start=previous.target_start,
                length=previous.length + block.length,
            )
        else:
            merged.append(block)
    return merged


def _prefix_block(region: _Region, length: int) -> _MatchBlock | None:
    if not length:
        return None
    return _MatchBlock(region.source_start, region.target_start, length)


def _suffix_block(region: _Region, length: int) -> _MatchBlock | None:
    if not length:
        return None
    return _MatchBlock(
        region.source_end - length,
        region.target_end - length,
        length,
    )


def _core_region(region: _Region, prefix: int, suffix: int) -> _Region:
    return _Region(
        source_start=region.source_start + prefix,
        source_end=region.source_end - suffix,
        target_start=region.target_start + prefix,
        target_end=region.target_end - suffix,
    )


def _anchored_core_blocks(
    context: _MatchContext,
    region: _Region,
) -> list[_MatchBlock]:
    width, anchors = _anchor_pairs(context, region)
    if not anchors:
        return []
    blocks: list[_MatchBlock] = []
    previous_source = region.source_start
    previous_target = region.target_start
    for anchor in anchors:
        gap = _Region(
            previous_source,
            anchor.source_start,
            previous_target,
            anchor.target_start,
        )
        blocks.extend(_region_blocks(context, gap))
        blocks.append(
            _MatchBlock(anchor.source_start, anchor.target_start, width)
        )
        previous_source = anchor.source_start + width
        previous_target = anchor.target_start + width
    trailing = _Region(
        previous_source,
        region.source_end,
        previous_target,
        region.target_end,
    )
    blocks.extend(_region_blocks(context, trailing))
    return blocks


def _region_blocks(
    context: _MatchContext,
    region: _Region,
) -> list[_MatchBlock]:
    prefix = _common_prefix_length(context, region)
    after_prefix = _Region(
        region.source_start + prefix,
        region.source_end,
        region.target_start + prefix,
        region.target_end,
    )
    suffix = _common_suffix_length(context, after_prefix)
    core = _core_region(region, prefix, suffix)
    blocks: list[_MatchBlock] = []
    prefix_match = _prefix_block(region, prefix)
    if prefix_match is not None:
        blocks.append(prefix_match)
    blocks.extend(_anchored_core_blocks(context, core))
    suffix_match = _suffix_block(region, suffix)
    if suffix_match is not None:
        blocks.append(suffix_match)
    return _merge_blocks(blocks)


def _matching_blocks(
    source: tuple[bytes, ...],
    target: tuple[bytes, ...],
) -> tuple[_MatchBlock, ...]:
    context = _MatchContext(source=source, target=target)
    region = _Region(_ZERO, len(source), _ZERO, len(target))
    return tuple(_region_blocks(context, region))


def _edit_ranges(
    source: tuple[bytes, ...],
    target: tuple[bytes, ...],
) -> tuple[_EditRange, ...]:
    edits: list[_EditRange] = []
    source_cursor = _ZERO
    target_cursor = _ZERO
    for block in _matching_blocks(source, target):
        has_gap = (
            source_cursor != block.source_start
            or target_cursor != block.target_start
        )
        if has_gap:
            edits.append(
                _EditRange(
                    source_cursor,
                    block.source_start,
                    target_cursor,
                    block.target_start,
                )
            )
        source_cursor = block.source_start + block.length
        target_cursor = block.target_start + block.length
    if source_cursor != len(source) or target_cursor != len(target):
        edits.append(
            _EditRange(
                source_cursor,
                len(source),
                target_cursor,
                len(target),
            )
        )
    return tuple(edits)


def _semantic_edit(
    context: _SemanticBuildContext,
    edit: _EditRange,
) -> SemanticEdit:
    return SemanticEdit(
        locator=_locator(
            context.source_digests,
            edit.source_start,
            edit.source_end,
            context_units=context.context_units,
        ),
        replacement=_replacement_bytes(
            context.target,
            edit.target_start,
            edit.target_end,
        ),
        replacement_digests=context.target_digests[
            edit.target_start : edit.target_end
        ],
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
    if type(source) is not MappedView or type(target) is not MappedView:
        message = "semantic build inputs must use exact MappedView records"
        raise SemanticPlacementError(message)
    if type(context_units) is not int or context_units < _ONE:
        message = "semantic placement context_units must be a positive integer"
        raise SemanticPlacementError(message)
    source_digests = _view_digests(source)
    target_digests = _view_digests(target)
    context = _SemanticBuildContext(
        source_digests=source_digests,
        target_digests=target_digests,
        target=target,
        context_units=context_units,
    )
    edits = tuple(
        _semantic_edit(context, edit)
        for edit in _edit_ranges(source_digests, target_digests)
    )
    return SemanticAuthoringPlan(edits=edits)


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


def _position_seeds(
    candidate: tuple[bytes, ...],
    locator: SemanticLocator,
) -> tuple[int, ...]:
    if locator.source_digests:
        first = locator.source_digests[0]
        return tuple(
            index for index, digest in enumerate(candidate) if digest == first
        )
    if locator.before_digests:
        final_before = locator.before_digests[-_ONE]
        return tuple(
            index + _ONE
            for index, digest in enumerate(candidate)
            if digest == final_before
        )
    first_after = locator.after_digests[0]
    return tuple(
        index for index, digest in enumerate(candidate) if digest == first_after
    )


def _candidate_positions(
    candidate: tuple[bytes, ...],
    locator: SemanticLocator,
) -> tuple[int, ...]:
    return tuple(
        start
        for start in _position_seeds(candidate, locator)
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


def _validate_mapper(value: object) -> None:
    if not callable(value):
        message = "semantic mapper must be callable"
        raise SemanticPlacementError(message)


def _map_semantic_output(
    mapper: Callable[[bytes], MappedView], output: bytes
) -> MappedView:
    try:
        mapped = mapper(output)
    except Exception as error:
        message = f"semantic mapper failed after edit application: {error}"
        raise SemanticPlacementError(message) from error
    if type(mapped) is not MappedView:
        message = "semantic mapper must return the exact MappedView type"
        raise SemanticPlacementError(message)
    return mapped


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
    if type(candidate) is not MappedView:
        message = "semantic candidate must use the exact MappedView type"
        raise SemanticPlacementError(message)
    if type(plan) is not SemanticAuthoringPlan:
        message = "semantic plan must use the exact authoring-plan type"
        raise SemanticPlacementError(message)
    _validate_mapper(mapper)
    if not plan.edits:
        return candidate.raw
    located = _locate_edits(candidate, plan)
    expected = _expected_digests(candidate, located)
    output = _apply_raw_edits(candidate.raw, located)
    observed = _view_digests(_map_semantic_output(mapper, output))
    if observed != expected:
        message = "semantic edit changed canonical units at a replacement seam"
        raise SemanticPlacementError(message)
    return output
