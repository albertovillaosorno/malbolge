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
#   - Static initial-positional-decode ordering for the three-word holdout.
# - Must-Not:
#   - Import the holdout challenge, call a verifier, inspect dynamic state, or
#     consume accepted-set/training evidence.
# - Allows:
#   - Inputs: exact holdout dimensions and an evaluation budget.
#   - Outputs: deterministic candidate-index order by frozen static score.
#   - Side effects: none.
# - Split-When:
#   - Another heuristic feature or candidate language gains independent policy.
# - Merge-When:
#   - A shared static scheduler owns this exact score and holdout identity.
# - Summary:
#   - Rank by earliest initial source position that decodes to halt.
# - Description:
#   - Uses classic positional decode only; candidate index breaks score ties.
# - Usage:
#   - Feed the registered heuristic runner under the plan's equal budget.
# - Defaults:
#   - Foreign dimensions and malformed integer inputs fail closed.
#

"""Verifier-independent initial-decode heuristic for the three-word holdout."""

from __future__ import annotations

from itertools import chain
from itertools import islice
from typing import Final
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

from verifier import emitted_malbolge_classic as classic

HEURISTIC_SCHEDULE_ID: Final = "initial-decode-halt-proximity-order-v1"
HEURISTIC_SCORE_ID: Final = "earliest-position-decoding-to-halt-else-three-v1"
THREE_WORD_CANDIDATE_COUNT: Final = 830_584

_GRAPHICAL_START: Final = 33
_GRAPHICAL_VALUES: Final = 94
_SOURCE_WORDS: Final = 3
_HALT: Final = ord("v")
_SCORE_NONE: Final = _SOURCE_WORDS
_MAX_U64: Final = (1 << 64) - 1


class InvalidInitialDecodeHeuristicRequestError(ValueError):
    """The static heuristic request is outside its preregistered holdout."""


def _u64(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value <= _MAX_U64:
        message = f"{label} must be an unsigned 64-bit integer"
        raise InvalidInitialDecodeHeuristicRequestError(message)
    return value


def _halt_source_byte(position: int) -> int:
    matches = tuple(
        value
        for value in range(
            _GRAPHICAL_START,
            _GRAPHICAL_START + _GRAPHICAL_VALUES,
        )
        if classic.decode(value, position) == _HALT
    )
    if len(matches) != 1:
        message = "classic positional decode lost unique halt source byte"
        raise InvalidInitialDecodeHeuristicRequestError(message)
    return matches[0]


_HALT_SOURCE_BYTES: Final = tuple(
    _halt_source_byte(position) for position in range(_SOURCE_WORDS)
)


def _source_digits(candidate_index: int) -> tuple[int, int, int]:
    prefix, third = divmod(candidate_index, _GRAPHICAL_VALUES)
    first, second = divmod(prefix, _GRAPHICAL_VALUES)
    return (
        _GRAPHICAL_START + first,
        _GRAPHICAL_START + second,
        _GRAPHICAL_START + third,
    )


def initial_decode_score(candidate_index: int) -> int:
    """Return earliest initial source position that positionally decodes halt.

    Returns:
        Zero, one, or two for the earliest halt decode, otherwise three.

    Raises:
        InvalidInitialDecodeHeuristicRequestError: If the index is outside
            holdout.

    """
    index = _u64(candidate_index, "candidate index")
    if index >= THREE_WORD_CANDIDATE_COUNT:
        message = "candidate index is outside the three-word holdout"
        raise InvalidInitialDecodeHeuristicRequestError(message)
    source = _source_digits(index)
    score = _SCORE_NONE
    for position, (value, halt_value) in enumerate(
        zip(source, _HALT_SOURCE_BYTES, strict=True)
    ):
        if value == halt_value:
            score = position
            break
    return score


def _score_zero_indices(halt_first: int) -> range:
    width = _GRAPHICAL_VALUES
    first_base = halt_first * width * width
    return range(first_base, first_base + (width * width))


def _score_one_indices(halt_first: int, halt_second: int) -> Iterator[int]:
    width = _GRAPHICAL_VALUES
    return (
        ((first * width) + halt_second) * width + third
        for first in range(width)
        if first != halt_first
        for third in range(width)
    )


def _score_two_indices(
    halt_first: int,
    halt_second: int,
    halt_third: int,
) -> Iterator[int]:
    width = _GRAPHICAL_VALUES
    return (
        ((first * width) + second) * width + halt_third
        for first in range(width)
        if first != halt_first
        for second in range(width)
        if second != halt_second
    )


def _score_three_indices(
    halt_first: int,
    halt_second: int,
    halt_third: int,
) -> Iterator[int]:
    width = _GRAPHICAL_VALUES
    return (
        ((first * width) + second) * width + third
        for first in range(width)
        if first != halt_first
        for second in range(width)
        if second != halt_second
        for third in range(width)
        if third != halt_third
    )


def _bucketed_indices() -> Iterator[int]:
    halt_first, halt_second, halt_third = (
        value - _GRAPHICAL_START for value in _HALT_SOURCE_BYTES
    )
    return chain(
        _score_zero_indices(halt_first),
        _score_one_indices(halt_first, halt_second),
        _score_two_indices(halt_first, halt_second, halt_third),
        _score_three_indices(halt_first, halt_second, halt_third),
    )


def heuristic_order(
    candidate_count: int,
    evaluation_budget: int,
) -> tuple[int, ...]:
    """Return the frozen score-then-index heuristic prefix.

    Returns:
        Up to the requested budget of unique holdout candidate indices.

    Raises:
        InvalidInitialDecodeHeuristicRequestError: If dimensions differ from
            the preregistered plan.

    """
    count = _u64(candidate_count, "candidate count")
    budget = _u64(evaluation_budget, "evaluation budget")
    if count != THREE_WORD_CANDIDATE_COUNT:
        message = "candidate count differs from the preregistered holdout"
        raise InvalidInitialDecodeHeuristicRequestError(message)
    selected_count = min(count, budget)
    return tuple(islice(_bucketed_indices(), selected_count))
