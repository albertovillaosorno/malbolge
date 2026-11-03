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

import builtins
import hashlib
from bisect import bisect_left
from collections.abc import Callable
from dataclasses import dataclass
from types import MemberDescriptorType
from typing import cast

from algorithms.diff.mapped import (
    MappedView,
    read_mapped_unit,
    read_mapped_view,
)

_ZERO = 0
_ONE = 1
# Preserve exact metadata and edit ordering after domain callbacks run.
_NATIVE_ANY = builtins.any
_NATIVE_CALLABLE = builtins.callable
_NATIVE_LEN = builtins.len
_NATIVE_MAX = builtins.max
_NATIVE_MIN = builtins.min
_NATIVE_SORTED = builtins.sorted
_NATIVE_TUPLE = builtins.tuple
_NATIVE_TYPE = builtins.type
_NATIVE_BYTES = builtins.bytes
_NATIVE_INT = builtins.int
_NATIVE_ENUMERATE = builtins.enumerate
_NATIVE_RANGE = builtins.range
_NATIVE_BOOL = builtins.bool
_NATIVE_SET = builtins.set
_NATIVE_REVERSED = builtins.reversed
_NATIVE_LIST = builtins.list
_NATIVE_OBJECT_NEW = object.__new__
# Verify placement using a constructor pinned before host hooks can replace it.
_SHA256_FACTORY = hashlib.sha256
_SHA256_BYTES = _SHA256_FACTORY().digest_size
_DEFAULT_CONTEXT_UNITS = 4
_UNIT_DOMAIN = b"semantic-placement-unit-v1\0"
_ANCHOR_WIDTHS = (8, 4, 2, 1)


class SemanticPlacementError(RuntimeError):
    """Raised when semantic edit placement is missing, ambiguous, or unsafe."""


@dataclass(frozen=True, slots=True, init=False)
class SemanticLocator:
    """Hashed source-unit range plus immediate canonical context."""

    source_digests: tuple[bytes, ...]
    before_digests: tuple[bytes, ...]
    after_digests: tuple[bytes, ...]

    def __init__(
        self,
        source_digests: tuple[bytes, ...],
        before_digests: tuple[bytes, ...],
        after_digests: tuple[bytes, ...],
    ) -> None:
        """Seal source/context metadata with the original validator."""
        _LOCATOR_SOURCE_SLOT.__set__(self, source_digests)
        _LOCATOR_BEFORE_SLOT.__set__(self, before_digests)
        _LOCATOR_AFTER_SLOT.__set__(self, after_digests)
        _LOCATOR_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require at least one source or context digest.

        Raises:
            SemanticPlacementError: Locator has no semantic evidence.

        """
        groups = read_semantic_locator(self)
        for group in groups:
            if _NATIVE_TYPE(group) is not _NATIVE_TUPLE:
                message = "semantic locator digests must use immutable tuples"
                raise SemanticPlacementError(message)
            items = cast("tuple[object, ...]", group)
            if _NATIVE_ANY(
                _NATIVE_TYPE(digest) is not _NATIVE_BYTES
                or _NATIVE_LEN(digest) != _SHA256_BYTES
                for digest in items
            ):
                message = "semantic locator digests must be exact SHA-256 bytes"
                raise SemanticPlacementError(message)
        if not _NATIVE_ANY(groups):
            message = "semantic locator requires source or context evidence"
            raise SemanticPlacementError(message)


_LOCATOR_VALIDATOR = cast(
    "Callable[[SemanticLocator], None]",
    SemanticLocator.__dict__["__post_init__"],
)
_LOCATOR_SOURCE_SLOT = cast(
    "MemberDescriptorType", SemanticLocator.__dict__["source_digests"]
)
_LOCATOR_BEFORE_SLOT = cast(
    "MemberDescriptorType", SemanticLocator.__dict__["before_digests"]
)
_LOCATOR_AFTER_SLOT = cast(
    "MemberDescriptorType", SemanticLocator.__dict__["after_digests"]
)


def read_semantic_locator(
    locator: SemanticLocator,
) -> tuple[tuple[bytes, ...], tuple[bytes, ...], tuple[bytes, ...]]:
    """Read immutable source/context hashes through original slot storage."""
    return (
        cast(
            "tuple[bytes, ...]",
            _LOCATOR_SOURCE_SLOT.__get__(locator, SemanticLocator),
        ),
        cast(
            "tuple[bytes, ...]",
            _LOCATOR_BEFORE_SLOT.__get__(locator, SemanticLocator),
        ),
        cast(
            "tuple[bytes, ...]",
            _LOCATOR_AFTER_SLOT.__get__(locator, SemanticLocator),
        ),
    )


@dataclass(frozen=True, slots=True, init=False)
class SemanticEdit:
    """Target replacement relative to hashed canonical source units."""

    locator: SemanticLocator
    replacement: bytes
    replacement_digests: tuple[bytes, ...]

    def __init__(
        self,
        locator: SemanticLocator,
        replacement: bytes,
        replacement_digests: tuple[bytes, ...],
    ) -> None:
        """Seal edit metadata with the original validator."""
        _EDIT_LOCATOR_SLOT.__set__(self, locator)
        _EDIT_REPLACEMENT_SLOT.__set__(self, replacement)
        _EDIT_DIGESTS_SLOT.__set__(self, replacement_digests)
        _EDIT_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require exact locator, replacement, and target digest metadata.

        Raises:
            SemanticPlacementError: Edit metadata is malformed.

        """
        locator, replacement, replacement_digests = read_semantic_edit(self)
        if _NATIVE_TYPE(locator) is not SemanticLocator:
            message = "semantic edit locator must use the exact locator type"
            raise SemanticPlacementError(message)
        if _NATIVE_TYPE(replacement) is not _NATIVE_BYTES:
            message = "semantic replacement must use exact bytes"
            raise SemanticPlacementError(message)
        if _NATIVE_TYPE(replacement_digests) is not _NATIVE_TUPLE:
            message = "semantic replacement digests must use an immutable tuple"
            raise SemanticPlacementError(message)
        items = cast("tuple[object, ...]", replacement_digests)
        if _NATIVE_ANY(
            _NATIVE_TYPE(digest) is not _NATIVE_BYTES
            or _NATIVE_LEN(digest) != _SHA256_BYTES
            for digest in items
        ):
            message = "semantic replacement digests must be exact SHA-256 bytes"
            raise SemanticPlacementError(message)


_EDIT_VALIDATOR = cast(
    "Callable[[SemanticEdit], None]", SemanticEdit.__dict__["__post_init__"]
)
_EDIT_LOCATOR_SLOT = cast(
    "MemberDescriptorType", SemanticEdit.__dict__["locator"]
)
_EDIT_REPLACEMENT_SLOT = cast(
    "MemberDescriptorType", SemanticEdit.__dict__["replacement"]
)
_EDIT_DIGESTS_SLOT = cast(
    "MemberDescriptorType", SemanticEdit.__dict__["replacement_digests"]
)


def read_semantic_edit(
    edit: SemanticEdit,
) -> tuple[SemanticLocator, bytes, tuple[bytes, ...]]:
    """Read the stored source locator and replacement evidence directly."""
    return (
        cast("SemanticLocator", _EDIT_LOCATOR_SLOT.__get__(edit, SemanticEdit)),
        cast("bytes", _EDIT_REPLACEMENT_SLOT.__get__(edit, SemanticEdit)),
        cast(
            "tuple[bytes, ...]", _EDIT_DIGESTS_SLOT.__get__(edit, SemanticEdit)
        ),
    )


@dataclass(frozen=True, slots=True, init=False)
class SemanticAuthoringPlan:
    """Non-distributable semantic edit plan for one mapped source file."""

    edits: tuple[SemanticEdit, ...]

    def __init__(self, edits: tuple[SemanticEdit, ...]) -> None:
        """Seal the edit sequence with the original validator."""
        _PLAN_EDITS_SLOT.__set__(self, edits)
        _PLAN_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require one immutable sequence of exact semantic edits.

        Raises:
            SemanticPlacementError: Plan records are mutable or foreign.

        """
        edits = read_semantic_plan(self)
        if _NATIVE_TYPE(edits) is not _NATIVE_TUPLE:
            message = "semantic edits must use the exact immutable tuple type"
            raise SemanticPlacementError(message)
        if _NATIVE_ANY(
            _NATIVE_TYPE(edit) is not SemanticEdit for edit in edits
        ):
            message = "semantic plan contains a foreign edit record"
            raise SemanticPlacementError(message)


_PLAN_VALIDATOR = cast(
    "Callable[[SemanticAuthoringPlan], None]",
    SemanticAuthoringPlan.__dict__["__post_init__"],
)
_PLAN_EDITS_SLOT = cast(
    "MemberDescriptorType", SemanticAuthoringPlan.__dict__["edits"]
)


def read_semantic_plan(plan: SemanticAuthoringPlan) -> tuple[SemanticEdit, ...]:
    """Read the original immutable edit sequence, not late class getters."""
    return cast(
        "tuple[SemanticEdit, ...]",
        _PLAN_EDITS_SLOT.__get__(plan, SemanticAuthoringPlan),
    )


@dataclass(frozen=True, slots=True, init=False)
class _LocatedEdit:
    edit: SemanticEdit
    unit_start: int
    unit_end: int
    raw_start: int
    raw_end: int

    def __init__(
        self,
        edit: SemanticEdit,
        unit_start: int,
        unit_end: int,
        raw_start: int,
        raw_end: int,
    ) -> None:
        """Preserve computed evidence against late class setters."""
        _LOCATED_EDIT_SLOT.__set__(self, edit)
        _LOCATED_UNIT_START_SLOT.__set__(self, unit_start)
        _LOCATED_UNIT_END_SLOT.__set__(self, unit_end)
        _LOCATED_RAW_START_SLOT.__set__(self, raw_start)
        _LOCATED_RAW_END_SLOT.__set__(self, raw_end)


# Placement must keep its computed bounds after host callbacks replace class
# accessors. These slots are private to semantic replay, not public metadata.
_LOCATED_EDIT_SLOT = cast(
    "MemberDescriptorType", _LocatedEdit.__dict__["edit"]
)
_LOCATED_UNIT_START_SLOT = cast(
    "MemberDescriptorType", _LocatedEdit.__dict__["unit_start"]
)
_LOCATED_UNIT_END_SLOT = cast(
    "MemberDescriptorType", _LocatedEdit.__dict__["unit_end"]
)
_LOCATED_RAW_START_SLOT = cast(
    "MemberDescriptorType", _LocatedEdit.__dict__["raw_start"]
)
_LOCATED_RAW_END_SLOT = cast(
    "MemberDescriptorType", _LocatedEdit.__dict__["raw_end"]
)


def _located_edit_fields(
    located: _LocatedEdit,
) -> tuple[SemanticEdit, int, int, int, int]:
    """Read computed edit coordinates without replaceable class getters."""
    return (
        cast("SemanticEdit", _LOCATED_EDIT_SLOT.__get__(located, _LocatedEdit)),
        cast("int", _LOCATED_UNIT_START_SLOT.__get__(located, _LocatedEdit)),
        cast("int", _LOCATED_UNIT_END_SLOT.__get__(located, _LocatedEdit)),
        cast("int", _LOCATED_RAW_START_SLOT.__get__(located, _LocatedEdit)),
        cast("int", _LOCATED_RAW_END_SLOT.__get__(located, _LocatedEdit)),
    )


@dataclass(frozen=True, slots=True, init=False)
class _AnchorPair:
    source_start: int
    target_start: int

    def __init__(
        self,
        source_start: int,
        target_start: int,
    ) -> None:
        """Preserve computed evidence against late class setters."""
        _ANCHOR_SLOTS[0].__set__(self, source_start)
        _ANCHOR_SLOTS[1].__set__(self, target_start)


@dataclass(frozen=True, slots=True, init=False)
class _MatchBlock:
    source_start: int
    target_start: int
    length: int

    def __init__(
        self,
        source_start: int,
        target_start: int,
        length: int,
    ) -> None:
        """Preserve computed evidence against late class setters."""
        _MATCH_BLOCK_SLOTS[0].__set__(self, source_start)
        _MATCH_BLOCK_SLOTS[1].__set__(self, target_start)
        _MATCH_BLOCK_SLOTS[2].__set__(self, length)


_MATCH_BLOCK_SLOTS = (
    cast("MemberDescriptorType", _MatchBlock.__dict__["source_start"]),
    cast("MemberDescriptorType", _MatchBlock.__dict__["target_start"]),
    cast("MemberDescriptorType", _MatchBlock.__dict__["length"]),
)


def _match_block_fields(block: _MatchBlock) -> tuple[int, int, int]:
    """Keep matched source/target ranges independent of late class hooks."""
    return (
        cast("int", _MATCH_BLOCK_SLOTS[0].__get__(block, _MatchBlock)),
        cast("int", _MATCH_BLOCK_SLOTS[1].__get__(block, _MatchBlock)),
        cast("int", _MATCH_BLOCK_SLOTS[2].__get__(block, _MatchBlock)),
    )


@dataclass(frozen=True, slots=True, init=False)
class _EditRange:
    source_start: int
    source_end: int
    target_start: int
    target_end: int

    def __init__(
        self,
        source_start: int,
        source_end: int,
        target_start: int,
        target_end: int,
    ) -> None:
        """Preserve computed evidence against late class setters."""
        _EDIT_RANGE_SLOTS[0].__set__(self, source_start)
        _EDIT_RANGE_SLOTS[1].__set__(self, source_end)
        _EDIT_RANGE_SLOTS[2].__set__(self, target_start)
        _EDIT_RANGE_SLOTS[3].__set__(self, target_end)


@dataclass(frozen=True, slots=True, init=False)
class _MatchContext:
    source: tuple[bytes, ...]
    target: tuple[bytes, ...]

    def __init__(
        self,
        source: tuple[bytes, ...],
        target: tuple[bytes, ...],
    ) -> None:
        """Preserve computed evidence against late class setters."""
        _MATCH_CONTEXT_SLOTS[0].__set__(self, source)
        _MATCH_CONTEXT_SLOTS[1].__set__(self, target)


@dataclass(frozen=True, slots=True, init=False)
class _Region:
    source_start: int
    source_end: int
    target_start: int
    target_end: int

    def __init__(
        self,
        source_start: int,
        source_end: int,
        target_start: int,
        target_end: int,
    ) -> None:
        """Preserve computed evidence against late class setters."""
        _REGION_SLOTS[0].__set__(self, source_start)
        _REGION_SLOTS[1].__set__(self, source_end)
        _REGION_SLOTS[2].__set__(self, target_start)
        _REGION_SLOTS[3].__set__(self, target_end)


@dataclass(frozen=True, slots=True, init=False)
class _SemanticBuildContext:
    source_digests: tuple[bytes, ...]
    target_digests: tuple[bytes, ...]
    target: MappedView
    context_units: int

    def __init__(
        self,
        source_digests: tuple[bytes, ...],
        target_digests: tuple[bytes, ...],
        target: MappedView,
        context_units: int,
    ) -> None:
        """Preserve computed evidence against late class setters."""
        _BUILD_CONTEXT_SLOTS[0].__set__(self, source_digests)
        _BUILD_CONTEXT_SLOTS[1].__set__(self, target_digests)
        _BUILD_CONTEXT_SLOTS[2].__set__(self, target)
        _BUILD_CONTEXT_SLOTS[3].__set__(self, context_units)


# All transient matching roles bind original slots, not later class hooks.
_ANCHOR_SLOTS = (
    cast("MemberDescriptorType", _AnchorPair.__dict__["source_start"]),
    cast("MemberDescriptorType", _AnchorPair.__dict__["target_start"]),
)
_MATCH_CONTEXT_SLOTS = (
    cast("MemberDescriptorType", _MatchContext.__dict__["source"]),
    cast("MemberDescriptorType", _MatchContext.__dict__["target"]),
)
_REGION_SLOTS = (
    cast("MemberDescriptorType", _Region.__dict__["source_start"]),
    cast("MemberDescriptorType", _Region.__dict__["source_end"]),
    cast("MemberDescriptorType", _Region.__dict__["target_start"]),
    cast("MemberDescriptorType", _Region.__dict__["target_end"]),
)


def _anchor_fields(pair: _AnchorPair) -> tuple[int, int]:
    """Read anchored source and target offsets from initial slot storage."""
    return (
        cast("int", _ANCHOR_SLOTS[0].__get__(pair, _AnchorPair)),
        cast("int", _ANCHOR_SLOTS[1].__get__(pair, _AnchorPair)),
    )


def _match_context_fields(
    context: _MatchContext,
) -> tuple[tuple[bytes, ...], tuple[bytes, ...]]:
    """Preserve the source and target hash streams during matching."""
    source_slot, target_slot = _MATCH_CONTEXT_SLOTS
    return (
        cast("tuple[bytes, ...]", source_slot.__get__(context, _MatchContext)),
        cast("tuple[bytes, ...]", target_slot.__get__(context, _MatchContext)),
    )


def _region_fields(region: _Region) -> tuple[int, int, int, int]:
    """Preserve the region bounds used to authorize matching and edits."""
    return (
        cast("int", _REGION_SLOTS[0].__get__(region, _Region)),
        cast("int", _REGION_SLOTS[1].__get__(region, _Region)),
        cast("int", _REGION_SLOTS[2].__get__(region, _Region)),
        cast("int", _REGION_SLOTS[3].__get__(region, _Region)),
    )


# Context and range records are internal, but later class getter changes must
# not redirect source binding or replacement authoring at this boundary.
_EDIT_RANGE_SLOTS = (
    cast("MemberDescriptorType", _EditRange.__dict__["source_start"]),
    cast("MemberDescriptorType", _EditRange.__dict__["source_end"]),
    cast("MemberDescriptorType", _EditRange.__dict__["target_start"]),
    cast("MemberDescriptorType", _EditRange.__dict__["target_end"]),
)
_BUILD_CONTEXT_SLOTS = (
    cast("MemberDescriptorType", _SemanticBuildContext.__dict__["source_digests"]),
    cast("MemberDescriptorType", _SemanticBuildContext.__dict__["target_digests"]),
    cast("MemberDescriptorType", _SemanticBuildContext.__dict__["target"]),
    cast("MemberDescriptorType", _SemanticBuildContext.__dict__["context_units"]),
)


# Semantic authoring consults mapper and matching callbacks before emitting
# evidence. Keep class allocation and initializers bound to their original
# validated slot-writers rather than mutable post-import class attributes.
_SEMANTIC_LOCATOR_INIT = cast(
    Callable[
        [SemanticLocator, tuple[bytes, ...], tuple[bytes, ...], tuple[bytes, ...]],
        None,
    ],
    SemanticLocator.__dict__["__init__"],
)
_SEMANTIC_EDIT_INIT = cast(
    "Callable[[SemanticEdit, SemanticLocator, bytes, tuple[bytes, ...]], None]",
    SemanticEdit.__dict__["__init__"],
)
_SEMANTIC_PLAN_INIT = cast(
    "Callable[[SemanticAuthoringPlan, tuple[SemanticEdit, ...]], None]",
    SemanticAuthoringPlan.__dict__["__init__"],
)
_SEMANTIC_BUILD_CONTEXT_INIT = cast(
    Callable[
        [
            _SemanticBuildContext,
            tuple[bytes, ...],
            tuple[bytes, ...],
            MappedView,
            int,
        ],
        None,
    ],
    _SemanticBuildContext.__dict__["__init__"],
)


def _new_semantic_locator(
    source_digests: tuple[bytes, ...],
    before_digests: tuple[bytes, ...],
    after_digests: tuple[bytes, ...],
) -> SemanticLocator:
    locator = _NATIVE_OBJECT_NEW(SemanticLocator)
    _SEMANTIC_LOCATOR_INIT(locator, source_digests, before_digests, after_digests)
    return locator


def _new_semantic_edit(
    locator: SemanticLocator,
    replacement: bytes,
    replacement_digests: tuple[bytes, ...],
) -> SemanticEdit:
    edit = _NATIVE_OBJECT_NEW(SemanticEdit)
    _SEMANTIC_EDIT_INIT(edit, locator, replacement, replacement_digests)
    return edit


def _new_semantic_plan(edits: tuple[SemanticEdit, ...]) -> SemanticAuthoringPlan:
    plan = _NATIVE_OBJECT_NEW(SemanticAuthoringPlan)
    _SEMANTIC_PLAN_INIT(plan, edits)
    return plan


def _new_build_context(
    source_digests: tuple[bytes, ...],
    target_digests: tuple[bytes, ...],
    target: MappedView,
    context_units: int,
) -> _SemanticBuildContext:
    context = _NATIVE_OBJECT_NEW(_SemanticBuildContext)
    _SEMANTIC_BUILD_CONTEXT_INIT(
        context, source_digests, target_digests, target, context_units
    )
    return context


def _edit_range_fields(edit: _EditRange) -> tuple[int, int, int, int]:
    """Read admitted source/target edit offsets from their initial slots."""
    return (
        cast("int", _EDIT_RANGE_SLOTS[0].__get__(edit, _EditRange)),
        cast("int", _EDIT_RANGE_SLOTS[1].__get__(edit, _EditRange)),
        cast("int", _EDIT_RANGE_SLOTS[2].__get__(edit, _EditRange)),
        cast("int", _EDIT_RANGE_SLOTS[3].__get__(edit, _EditRange)),
    )


def _build_context_fields(
    context: _SemanticBuildContext,
) -> tuple[tuple[bytes, ...], tuple[bytes, ...], MappedView, int]:
    """Read the original semantic authoring context, not replaced getters."""
    source_slot, digests_slot, target_slot, width_slot = _BUILD_CONTEXT_SLOTS
    return (
        cast("tuple[bytes, ...]", source_slot.__get__(context, _SemanticBuildContext)),
        cast("tuple[bytes, ...]", digests_slot.__get__(context, _SemanticBuildContext)),
        cast("MappedView", target_slot.__get__(context, _SemanticBuildContext)),
        cast("int", width_slot.__get__(context, _SemanticBuildContext)),
    )


def _frame(value: bytes) -> bytes:
    return _NATIVE_LEN(value).to_bytes(8, byteorder="big") + value


def _unit_digest(canonical: bytes) -> bytes:
    return _SHA256_FACTORY(_UNIT_DOMAIN + _frame(canonical)).digest()


def _view_digests(view: MappedView) -> tuple[bytes, ...]:
    return _NATIVE_TUPLE(
        _unit_digest(read_mapped_unit(unit)[0])
        for unit in read_mapped_view(view)[1]
    )


def _replacement_bytes(view: MappedView, start: int, end: int) -> bytes:
    if start == end:
        return b""
    raw, units = read_mapped_view(view)
    raw_start = read_mapped_unit(units[start])[1]
    raw_end = read_mapped_unit(units[end - _ONE])[2]
    return raw[raw_start:raw_end]


def _locator(
    source_digests: tuple[bytes, ...],
    start: int,
    end: int,
    *,
    context_units: int,
) -> SemanticLocator:
    before_start = _NATIVE_MAX(_ZERO, start - context_units)
    after_end = _NATIVE_MIN(_NATIVE_LEN(source_digests), end + context_units)
    return _new_semantic_locator(
        source_digests=source_digests[start:end],
        before_digests=source_digests[before_start:start],
        after_digests=source_digests[end:after_end],
    )


def _common_prefix_length(context: _MatchContext, region: _Region) -> int:
    source, target = _match_context_fields(context)
    source_start, source_end, target_start, target_end = _region_fields(region)
    limit = _NATIVE_MIN(
        source_end - source_start,
        target_end - target_start,
    )
    length = _ZERO
    while (
        length < limit
        and source[source_start + length]
        == target[target_start + length]
    ):
        length += _ONE
    return length


def _common_suffix_length(context: _MatchContext, region: _Region) -> int:
    source, target = _match_context_fields(context)
    source_start, source_end, target_start, target_end = _region_fields(region)
    limit = _NATIVE_MIN(
        source_end - source_start,
        target_end - target_start,
    )
    length = _ZERO
    while (
        length < limit
        and source[source_end - length - _ONE]
        == target[target_end - length - _ONE]
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
    for offset in _NATIVE_RANGE(start, final_start + _ONE):
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
    return _NATIVE_TUPLE(selected)


def _lis_pairs(pairs: tuple[_AnchorPair, ...]) -> tuple[_AnchorPair, ...]:
    if not pairs:
        return ()
    tail_targets: list[int] = []
    tail_indices: list[int] = []
    predecessors = [-_ONE] * _NATIVE_LEN(pairs)
    for index, pair in _NATIVE_ENUMERATE(pairs):
        target_start = _anchor_fields(pair)[1]
        position = bisect_left(tail_targets, target_start)
        if position == _NATIVE_LEN(tail_targets):
            tail_targets.append(target_start)
            tail_indices.append(index)
        else:
            tail_targets[position] = target_start
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
        source_start, target_start = _anchor_fields(pair)
        if source_start < source_end or target_start < target_end:
            continue
        selected.append(pair)
        source_end = source_start + width
        target_end = target_start + width
    return _NATIVE_TUPLE(selected)


def _window_pairs(
    context: _MatchContext,
    region: _Region,
    width: int,
) -> tuple[_AnchorPair, ...]:
    source, target = _match_context_fields(context)
    source_start, source_end, target_start, target_end = _region_fields(region)
    source_windows = _unique_windows(
        source,
        source_start,
        source_end,
        width=width,
    )
    target_windows = _unique_windows(
        target,
        target_start,
        target_end,
        width=width,
    )
    return _NATIVE_TUPLE(
        _NATIVE_SORTED(
            (
                _AnchorPair(source_offset, target_windows[window])
                for window, source_offset in source_windows.items()
                if window in target_windows
            ),
            key=_anchor_fields,
        )
    )


def _anchor_pairs(
    context: _MatchContext,
    region: _Region,
) -> tuple[int, tuple[_AnchorPair, ...]]:
    source_start, source_end, target_start, target_end = _region_fields(region)
    source_length = source_end - source_start
    target_length = target_end - target_start
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
        previous_source, previous_target, previous_length = _match_block_fields(
            previous
        )
        source_start, target_start, length = _match_block_fields(block)
        contiguous = (
            previous_source + previous_length == source_start
            and previous_target + previous_length == target_start
        )
        if contiguous:
            merged[-_ONE] = _MatchBlock(
                source_start=previous_source,
                target_start=previous_target,
                length=previous_length + length,
            )
        else:
            merged.append(block)
    return merged


def _prefix_block(region: _Region, length: int) -> _MatchBlock | None:
    source_start, _, target_start, _ = _region_fields(region)
    if not length:
        return None
    return _MatchBlock(source_start, target_start, length)


def _suffix_block(region: _Region, length: int) -> _MatchBlock | None:
    _, source_end, _, target_end = _region_fields(region)
    if not length:
        return None
    return _MatchBlock(
        source_end - length,
        target_end - length,
        length,
    )


def _core_region(region: _Region, prefix: int, suffix: int) -> _Region:
    source_start, source_end, target_start, target_end = _region_fields(region)
    return _Region(
        source_start=source_start + prefix,
        source_end=source_end - suffix,
        target_start=target_start + prefix,
        target_end=target_end - suffix,
    )


def _anchored_core_blocks(
    context: _MatchContext,
    region: _Region,
) -> list[_MatchBlock]:
    source_start, source_end, target_start, target_end = _region_fields(region)
    width, anchors = _anchor_pairs(context, region)
    if not anchors:
        return []
    blocks: list[_MatchBlock] = []
    previous_source = source_start
    previous_target = target_start
    for anchor in anchors:
        anchor_source, anchor_target = _anchor_fields(anchor)
        gap = _Region(
            previous_source,
            anchor_source,
            previous_target,
            anchor_target,
        )
        blocks.extend(_region_blocks(context, gap))
        blocks.append(
            _MatchBlock(anchor_source, anchor_target, width)
        )
        previous_source = anchor_source + width
        previous_target = anchor_target + width
    trailing = _Region(
        previous_source,
        source_end,
        previous_target,
        target_end,
    )
    blocks.extend(_region_blocks(context, trailing))
    return blocks


def _region_blocks(
    context: _MatchContext,
    region: _Region,
) -> list[_MatchBlock]:
    source_start, source_end, target_start, target_end = _region_fields(region)
    prefix = _common_prefix_length(context, region)
    after_prefix = _Region(
        source_start + prefix,
        source_end,
        target_start + prefix,
        target_end,
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
    region = _Region(_ZERO, _NATIVE_LEN(source), _ZERO, _NATIVE_LEN(target))
    return _NATIVE_TUPLE(_region_blocks(context, region))


def _edit_ranges(
    source: tuple[bytes, ...],
    target: tuple[bytes, ...],
) -> tuple[_EditRange, ...]:
    edits: list[_EditRange] = []
    source_cursor = _ZERO
    target_cursor = _ZERO
    for block in _matching_blocks(source, target):
        source_start, target_start, length = _match_block_fields(block)
        has_gap = source_cursor != source_start or target_cursor != target_start
        if has_gap:
            edits.append(
                _EditRange(
                    source_cursor, source_start, target_cursor, target_start
                )
            )
        source_cursor = source_start + length
        target_cursor = target_start + length
    if (
        source_cursor != _NATIVE_LEN(source)
        or target_cursor != _NATIVE_LEN(target)
    ):
        edits.append(
            _EditRange(
                source_cursor,
                _NATIVE_LEN(source),
                target_cursor,
                _NATIVE_LEN(target),
            )
        )
    return _NATIVE_TUPLE(edits)


def _semantic_edit(
    context: _SemanticBuildContext,
    edit: _EditRange,
) -> SemanticEdit:
    source_digests, target_digests, target, context_units = _build_context_fields(
        context
    )
    source_start, source_end, target_start, target_end = _edit_range_fields(edit)
    return _new_semantic_edit(
        locator=_locator(
            source_digests, source_start, source_end,
            context_units=context_units,
        ),
        replacement=_replacement_bytes(target, target_start, target_end),
        replacement_digests=target_digests[target_start:target_end],
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
    if (
        _NATIVE_TYPE(source) is not MappedView
        or _NATIVE_TYPE(target) is not MappedView
    ):
        message = "semantic build inputs must use exact MappedView records"
        raise SemanticPlacementError(message)
    if _NATIVE_TYPE(context_units) is not _NATIVE_INT or context_units < _ONE:
        message = "semantic placement context_units must be a positive integer"
        raise SemanticPlacementError(message)
    source_digests = _view_digests(source)
    target_digests = _view_digests(target)
    context = _new_build_context(
        source_digests=source_digests,
        target_digests=target_digests,
        target=target,
        context_units=context_units,
    )
    edits = _NATIVE_TUPLE(
        _semantic_edit(context, edit)
        for edit in _edit_ranges(source_digests, target_digests)
    )
    return _new_semantic_plan(edits=edits)


def _context_matches(
    candidate: tuple[bytes, ...],
    locator: SemanticLocator,
    start: int,
) -> bool:
    source, before, after = read_semantic_locator(locator)
    source_end = start + _NATIVE_LEN(source)
    before_count = _NATIVE_LEN(before)
    after_count = _NATIVE_LEN(after)
    fits = (
        start >= before_count
        and source_end + after_count <= _NATIVE_LEN(candidate)
    )
    source_matches = (
        fits and candidate[start:source_end] == source
    )
    before_matches = (
        source_matches
        and candidate[start - before_count : start] == before
    )
    return _NATIVE_BOOL(
        before_matches
        and candidate[source_end : source_end + after_count]
        == after
    )


def _position_seeds(
    candidate: tuple[bytes, ...],
    locator: SemanticLocator,
) -> tuple[int, ...]:
    source, before, after = read_semantic_locator(locator)
    if source:
        first = source[0]
        return _NATIVE_TUPLE(
            index
            for index, digest in _NATIVE_ENUMERATE(candidate)
            if digest == first
        )
    if before:
        final_before = before[-_ONE]
        return _NATIVE_TUPLE(
            index + _ONE
            for index, digest in _NATIVE_ENUMERATE(candidate)
            if digest == final_before
        )
    first_after = after[0]
    return _NATIVE_TUPLE(
        index
        for index, digest in _NATIVE_ENUMERATE(candidate)
        if digest == first_after
    )


def _candidate_positions(
    candidate: tuple[bytes, ...],
    locator: SemanticLocator,
) -> tuple[int, ...]:
    return _NATIVE_TUPLE(
        start
        for start in _position_seeds(candidate, locator)
        if _context_matches(candidate, locator, start)
    )


def _unique_position(
    candidate: tuple[bytes, ...],
    locator: SemanticLocator,
) -> int:
    positions = _candidate_positions(candidate, locator)
    if _NATIVE_LEN(positions) != _ONE:
        message = (
            "semantic source locator is missing or ambiguous: "
            f"found {_NATIVE_LEN(positions)} placements"
        )
        raise SemanticPlacementError(message)
    return positions[0]


def _raw_span(view: MappedView, start: int, end: int) -> tuple[int, int]:
    raw, units = read_mapped_view(view)
    if start == end:
        offset = (
            read_mapped_unit(units[start])[1]
            if start < _NATIVE_LEN(units)
            else _NATIVE_LEN(raw)
        )
        return offset, offset
    return (
        read_mapped_unit(units[start])[1],
        read_mapped_unit(units[end - _ONE])[2],
    )


def _locate_edits(
    candidate: MappedView,
    plan: SemanticAuthoringPlan,
) -> tuple[_LocatedEdit, ...]:
    digests = _view_digests(candidate)
    located: list[_LocatedEdit] = []
    for edit in read_semantic_plan(plan):
        locator = read_semantic_edit(edit)[0]
        unit_start = _unique_position(digests, locator)
        unit_end = unit_start + _NATIVE_LEN(read_semantic_locator(locator)[0])
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
    ordered = _NATIVE_TUPLE(
        _NATIVE_SORTED(
            located, key=lambda item: _located_edit_fields(item)[3:]
        )
    )
    _require_nonoverlapping_edits(ordered)
    return ordered


def _require_nonoverlapping_edits(ordered: tuple[_LocatedEdit, ...]) -> None:
    previous: tuple[SemanticEdit, int, int, int, int] | None = None
    insertion_boundaries: set[int] = _NATIVE_SET()
    for item in ordered:
        fields = _located_edit_fields(item)
        _, unit_start, unit_end, raw_start, _ = fields
        if unit_start == unit_end:
            if unit_start in insertion_boundaries:
                message = (
                    "semantic edits overlap or reorder in candidate source"
                )
                raise SemanticPlacementError(message)
            insertion_boundaries.add(unit_start)
        if previous is not None and (
            raw_start < previous[4] or unit_start < previous[2]
        ):
            message = "semantic edits overlap or reorder in candidate source"
            raise SemanticPlacementError(message)
        previous = fields


def _apply_raw_edits(raw: bytes, edits: tuple[_LocatedEdit, ...]) -> bytes:
    output = raw
    for item in _NATIVE_REVERSED(edits):
        edit, _, _, raw_start, raw_end = _located_edit_fields(item)
        output = (
            output[:raw_start]
            + read_semantic_edit(edit)[1]
            + output[raw_end:]
        )
    return output


def _expected_digests(
    candidate: MappedView,
    edits: tuple[_LocatedEdit, ...],
) -> tuple[bytes, ...]:
    expected = _NATIVE_LIST(_view_digests(candidate))
    for item in _NATIVE_REVERSED(edits):
        edit, unit_start, unit_end, _, _ = _located_edit_fields(item)
        expected[unit_start:unit_end] = read_semantic_edit(edit)[2]
    return _NATIVE_TUPLE(expected)


def _validate_mapper(value: object) -> None:
    if not _NATIVE_CALLABLE(value):
        message = "semantic mapper must be callable"
        raise SemanticPlacementError(message)


def _map_semantic_output(
    mapper: Callable[[bytes], MappedView], output: bytes
) -> MappedView:
    try:
        mapped = mapper(output)
    except Exception as error:
        # Callback exceptions may define executable or failing __str__ hooks.
        # Preserve the original error as the cause without formatting it.
        message = "semantic mapper failed after edit application"
        raise SemanticPlacementError(message) from error
    if _NATIVE_TYPE(mapped) is not MappedView:
        message = "semantic mapper must return the exact MappedView type"
        raise SemanticPlacementError(message)
    if read_mapped_view(mapped)[0] != output:
        message = "semantic mapper must describe the actual output bytes"
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
    if _NATIVE_TYPE(candidate) is not MappedView:
        message = "semantic candidate must use the exact MappedView type"
        raise SemanticPlacementError(message)
    if _NATIVE_TYPE(plan) is not SemanticAuthoringPlan:
        message = "semantic plan must use the exact authoring-plan type"
        raise SemanticPlacementError(message)
    _validate_mapper(mapper)
    if not read_semantic_plan(plan):
        return read_mapped_view(candidate)[0]
    located = _locate_edits(candidate, plan)
    expected = _expected_digests(candidate, located)
    output = _apply_raw_edits(read_mapped_view(candidate)[0], located)
    observed = _view_digests(_map_semantic_output(mapper, output))
    if observed != expected:
        message = "semantic edit changed canonical units at a replacement seam"
        raise SemanticPlacementError(message)
    return output
