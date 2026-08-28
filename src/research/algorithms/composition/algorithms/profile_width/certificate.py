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
#   - Research-only finite width-relation checking and width selection.
# - Must-Not:
#   - Change runtime profiles or claim trusted-verifier authority.
# - Allows:
#   - Inputs: explicit finite systems, relations, and width certificate results.
#   - Outputs: deterministic certificate validity and fail-closed width choice.
#   - Side effects: none.
# - Split-When:
#   - A trusted product verifier or serialized certificate format is promoted.
# - Merge-When:
#   - Another research module owns the same finite lockstep certificate logic.
# - Summary:
#   - Experimental finite profile-width certificate checker and selector.
# - Description:
#   - Checks initial coverage, observations, lockstep edges, and width results.
# - Usage:
#   - Mathematical evidence exercises this module before any product promotion.
# - Defaults:
#   - Missing surfaces or width results fail closed to the canonical width.
#

"""Research-only finite profile-width certificate checking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

MINIMUM_WIDTH: Final = 10
CANONICAL_WIDTH: Final = 14


type WidthRelation = frozenset[tuple[str, str]]


@dataclass(frozen=True, slots=True)
class FiniteSystem:
    """One explicit deterministic finite system used by a width certificate."""

    initial: Mapping[str, str]
    observation: Mapping[str, tuple[int, ...]]
    successor: Mapping[str, str | None]


def _initial_coverage(
    wide: FiniteSystem,
    narrow: FiniteSystem,
    relation: WidthRelation,
) -> bool:
    if set(wide.initial) != set(narrow.initial):
        return False
    return all(
        (wide_state, narrow.initial[input_id]) in relation
        for input_id, wide_state in wide.initial.items()
    )


def _state_present(system: FiniteSystem, state: str) -> bool:
    return state in system.observation and state in system.successor


def _successors_match(
    successors: tuple[str | None, str | None],
    relation: WidthRelation,
) -> bool:
    wide_next, narrow_next = successors
    if wide_next is None or narrow_next is None:
        return wide_next is None and narrow_next is None
    return (wide_next, narrow_next) in relation


def _pair_obligation(
    systems: tuple[FiniteSystem, FiniteSystem],
    relation: WidthRelation,
    pair: tuple[str, str],
) -> bool:
    wide, narrow = systems
    wide_state, narrow_state = pair
    if not (
        _state_present(wide, wide_state)
        and _state_present(narrow, narrow_state)
    ):
        return False
    observations_equal = (
        wide.observation[wide_state] == narrow.observation[narrow_state]
    )
    successors = (
        wide.successor[wide_state],
        narrow.successor[narrow_state],
    )
    return observations_equal and _successors_match(successors, relation)


def certificate_valid(
    wide: FiniteSystem,
    narrow: FiniteSystem,
    relation: WidthRelation,
) -> bool:
    """Return whether one finite lockstep width certificate is complete.

    Returns:
        True only when every declared finite obligation is satisfied.

    """
    return _initial_coverage(wide, narrow, relation) and all(
        _pair_obligation((wide, narrow), relation, pair) for pair in relation
    )


def minimum_certified_width(results: Mapping[int, bool]) -> int:
    """Return the minimum independently certified profile width.

    Returns:
        The smallest accepted width, or canonical width on missing/invalid data.

    """
    candidates = set(range(MINIMUM_WIDTH, CANONICAL_WIDTH))
    if set(results) != candidates:
        return CANONICAL_WIDTH
    if not all(type(results[width]) is bool for width in candidates):
        return CANONICAL_WIDTH
    certified = {width for width in candidates if results[width]}
    return min(certified, default=CANONICAL_WIDTH)
