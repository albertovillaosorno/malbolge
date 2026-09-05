# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Deterministic evidence for the preregistered static heuristic order.
# - Must-Not:
#   - Invoke holdout verification or inspect accepted candidates.
# - Allows:
#   - Inputs: static scheduler and classic positional decode only.
#   - Outputs: score, ordering, uniqueness, and fail-closed assertions.
#   - Side effects: source-text reads for forbidden dependency checks only.
# - Split-When:
#   - Another heuristic schedule gains independent identity.
# - Merge-When:
#   - A shared test owns this exact static ordering contract.
# - Summary:
#   - Prove the schedule depends only on initial decode and candidate index.
# - Description:
#   - Locks the 50,000-candidate prefix without running the holdout verifier.
# - Usage:
#   - Run before registering the heuristic comparison runner.
# - Defaults:
#   - No search outcome may appear in this test module.
#

"""Deterministic tests for the three-word initial-decode heuristic."""

from pathlib import Path
from typing import cast

from algorithms.superoptimization import initial_decode_heuristic as heuristic
import pytest

from verifier import emitted_malbolge_classic as classic

_ROOT = Path(__file__).resolve().parents[5]
_SOURCE = _ROOT / (
    "src/research/algorithms/composition/algorithms/"
    "superoptimization/initial_decode_heuristic.py"
)
_CANDIDATES = 830_584
_BUDGET = 50_000
_GRAPHICAL_START = 33
_GRAPHICAL_VALUES = 94
_HALT = ord("v")
_SOURCE_WORDS = 3
_FOREIGN_COUNT = _CANDIDATES - 1
_SCORE_NONE = 3
_REQUEST_ERROR = (
    "must be an unsigned 64-bit integer|differs from the preregistered holdout"
)
_FORBIDDEN_SOURCE_MARKERS = (
    "three_word_challenge",
    "verified_quality",
    "accepted_set",
    "accepted_candidate",
)


def _halt_source_bytes() -> tuple[int, ...]:
    result: list[int] = []
    for position in range(_SOURCE_WORDS):
        matches = tuple(
            value
            for value in range(
                _GRAPHICAL_START,
                _GRAPHICAL_START + _GRAPHICAL_VALUES,
            )
            if classic.decode(value, position) == _HALT
        )
        assert len(matches) == 1
        result.append(matches[0])
    return tuple(result)


def _index(source: tuple[int, int, int]) -> int:
    first, second, third = (
        value - _GRAPHICAL_START for value in source
    )
    return (
        (first * _GRAPHICAL_VALUES * _GRAPHICAL_VALUES)
        + (second * _GRAPHICAL_VALUES)
        + third
    )


def test_initial_decode_score_matches_independent_positional_decode() -> None:
    """Each score is exactly the earliest initial positional halt decode."""
    halt = _halt_source_bytes()
    nonhalt = _GRAPHICAL_START
    while classic.decode(nonhalt, 0) == _HALT:
        nonhalt += 1
    cases = (
        ((halt[0], nonhalt, nonhalt), 0),
        ((nonhalt, halt[1], nonhalt), 1),
        ((nonhalt, nonhalt, halt[2]), 2),
        ((nonhalt, nonhalt, nonhalt), _SCORE_NONE),
    )
    for source, expected in cases:
        assert heuristic.initial_decode_score(_index(source)) == expected


def test_heuristic_order_is_exact_score_then_index_prefix() -> None:
    """The frozen 50k schedule is unique and lexicographic within score."""
    order = heuristic.heuristic_order(_CANDIDATES, _BUDGET)
    assert len(order) == _BUDGET
    assert len(set(order)) == _BUDGET
    keys = tuple(
        (heuristic.initial_decode_score(index), index) for index in order
    )
    assert keys == tuple(sorted(keys))
    assert {score for score, _ in keys}.issubset({0, 1, 2, 3})


def test_heuristic_module_has_no_holdout_verifier_or_outcome_dependency(
) -> None:
    """Static schedule source cannot import challenge or outcome knowledge."""
    source = _SOURCE.read_text(encoding="utf-8")
    assert all(marker not in source for marker in _FORBIDDEN_SOURCE_MARKERS)


@pytest.mark.parametrize(
    ("candidate_count", "budget"),
    [(_FOREIGN_COUNT, _BUDGET), (_CANDIDATES, -1), (True, _BUDGET)],
)
def test_heuristic_order_rejects_foreign_dimensions(
    candidate_count: object,
    budget: object,
) -> None:
    """Foreign holdout dimensions or malformed budgets fail closed."""
    with pytest.raises(
        heuristic.InvalidInitialDecodeHeuristicRequestError,
        match=_REQUEST_ERROR,
    ):
        _ = heuristic.heuristic_order(
            cast("int", candidate_count),
            cast("int", budget),
        )
