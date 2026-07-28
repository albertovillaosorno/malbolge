# File:
#   - test_semantic.py
# Path:
#   - algorithms/diff/tests/test_semantic.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
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
#   - Synthetic tests for mapped semantic compatible placement.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Synthetic tests for mapped semantic compatible placement."""

from __future__ import annotations

import re

import pytest

from algorithms.diff.mapped import MappedUnit
from algorithms.diff.mapped import MappedView
from algorithms.diff.semantic import SemanticPlacementError
from algorithms.diff.semantic import apply_semantic_plan
from algorithms.diff.semantic import build_semantic_plan

_TOKEN = re.compile(rb"[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[^\s]")
_REPLACED = b"extra ; alpha   = new ; omega tail"
_INSERTED = b"alpha   added; omega"
_DELETED = b"alpha      ; omega"
_LARGE_REPLACEMENT = b"new"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _map(raw: bytes) -> MappedView:
    units = tuple(
        MappedUnit(
            canonical=match.group(0),
            raw_start=match.start(),
            raw_end=match.end(),
        )
        for match in _TOKEN.finditer(raw)
    )
    return MappedView(raw=raw, units=units)


def test_replacement_preserves_candidate_formatting() -> None:
    """Patch one semantic unit without normalizing unrelated candidate bytes."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    candidate_raw = b"extra ; alpha   = old ; omega tail"
    candidate = _map(candidate_raw)
    plan = build_semantic_plan(source, target, context_units=2)

    output = apply_semantic_plan(candidate, plan, _map)

    _expect(
        output == _REPLACED,
        "semantic replacement discarded candidate presentation or additions",
    )


def test_format_only_target_change_authors_no_semantic_edits() -> None:
    """Preserve candidate bytes when source and target units agree."""
    source = _map(b"alpha=old;")
    target = _map(b"alpha = old ;")
    candidate = _map(b"alpha\t=\told ;  ")
    plan = build_semantic_plan(source, target)

    output = apply_semantic_plan(candidate, plan, _map)

    _expect(not plan.edits, "format-only target authored a semantic edit")
    _expect(output == candidate.raw, "format-only plan rewrote candidate bytes")


def test_semantic_insertion_uses_candidate_boundary_and_preserves_trivia() -> (
    None
):
    """Insert target units at a uniquely located canonical boundary."""
    source = _map(b"alpha ; omega")
    target = _map(b"alpha added ; omega")
    candidate = _map(b"alpha   ; omega")
    plan = build_semantic_plan(source, target, context_units=2)

    output = apply_semantic_plan(candidate, plan, _map)

    _expect(output == _INSERTED, "semantic insertion moved trivia")


def test_semantic_deletion_keeps_surrounding_candidate_whitespace() -> None:
    """Delete only mapped source units and leave presentation gaps untouched."""
    source = _map(b"alpha obsolete ; omega")
    target = _map(b"alpha ; omega")
    candidate = _map(b"alpha   obsolete   ; omega")
    plan = build_semantic_plan(source, target, context_units=2)

    output = apply_semantic_plan(candidate, plan, _map)

    _expect(output == _DELETED, "semantic deletion removed trivia")


def test_changed_or_ambiguous_source_region_fails_closed() -> None:
    """Reject unavailable or ambiguous semantic source evidence."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")
    plan = build_semantic_plan(source, target, context_units=1)

    with pytest.raises(SemanticPlacementError, match="missing or ambiguous"):
        _ = apply_semantic_plan(_map(b"alpha = upstream ; omega"), plan, _map)
    with pytest.raises(SemanticPlacementError, match="missing or ambiguous"):
        _ = apply_semantic_plan(
            _map(b"alpha = old ; omega alpha = old ; omega"),
            plan,
            _map,
        )


def test_retokenization_rejects_unsafe_insertion_seam() -> None:
    """Fail when raw insertion would merge semantic tokens."""
    source = _map(b"a;")
    target = _map(b"a b;")
    candidate = _map(b"a;")
    plan = build_semantic_plan(source, target, context_units=1)

    with pytest.raises(SemanticPlacementError, match="replacement seam"):
        _ = apply_semantic_plan(candidate, plan, _map)


def test_semantic_authoring_is_deterministic() -> None:
    """Produce stable hashed locators and target replacements across runs."""
    source = _map(b"alpha = old ; omega")
    target = _map(b"alpha = new ; omega")

    first = build_semantic_plan(source, target)
    second = build_semantic_plan(source, target)

    _expect(first == second, "semantic authoring changed across runs")


def test_large_repetitive_sequence_authors_local_edit() -> None:
    """Keep a large repetitive fixture local instead of quadratic matching."""
    repeated = b"a " * 5_000
    source = _map(repeated + b"old " + repeated)
    target = _map(repeated + b"new " + repeated)

    plan = build_semantic_plan(source, target)

    _expect(len(plan.edits) == 1, "large local change fragmented unexpectedly")
    _expect(
        plan.edits[0].replacement == _LARGE_REPLACEMENT,
        "large local replacement changed",
    )
