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
#   - Exact widened double-transposition H-fixed quotient counts under N(H)/H.
# - Must-Not:
#   - Claim dense rank/unrank or exact-H filtering for this S5 stratum.
# - Allows:
#   - Inputs: six four-component H-edge-orbit values through mass fourteen.
#   - Outputs: quotient cardinalities under the residual Klein-four action.
#   - Side effects: none.
# - Split-When:
#   - A scalable dense quotient rank replaces count-only evidence.
# - Merge-When:
#   - Complete widened full-S5 ranking owns the same quotient cycle index.
# - Summary:
#   - Burnside-count the residual V4 action on widened H-edge-orbit values.
# - Description:
#   - Two weight-one and four weight-two values transform by four reviewed maps.
# - Usage:
#   - Fixes the 6,611,992-class mass-fourteen quotient target.
# - Defaults:
#   - Direct quotient orbits stop at mass two; Burnside arithmetic reaches 14.
#

"""Exact widened double-transposition normalizer-quotient counts."""

from __future__ import annotations

from functools import cache
from math import comb

_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 2
_WIDTH_FOURTEEN_COUNT = 6_611_992
_WEIGHTS = (1, 1, 2, 2, 2, 2)
_MAPS = (
    (0, 1, 2, 3, 4, 5),
    (0, 1, 3, 2, 4, 5),
    (1, 0, 2, 3, 5, 4),
    (1, 0, 3, 2, 5, 4),
)
_EXPECTED_EFFECTIVE_WEIGHTS = (
    (1, 1, 2, 2, 2, 2),
    (1, 1, 2, 2, 4),
    (2, 2, 2, 4),
    (2, 4, 4),
)
_EXPECTED_COUNTS = (
    1,
    4,
    28,
    108,
    450,
    1_468,
    4_780,
    13_684,
    38_295,
    98_920,
    248_728,
    591_736,
    1_370_988,
    3_047_928,
    6_611_992,
)

type _Vector = tuple[int, int, int, int]
type _OrbitState = tuple[_Vector, ...]


def _cycles(mapping: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    unseen = set(range(len(mapping)))
    result: list[tuple[int, ...]] = []
    while unseen:
        seed = min(unseen)
        cycle: list[int] = []
        current = seed
        while current not in cycle:
            cycle.append(current)
            unseen.discard(current)
            current = mapping[current]
        result.append(tuple(cycle))
    return tuple(result)


def _effective_weights(mapping: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(
        sorted(_WEIGHTS[cycle[0]] * len(cycle) for cycle in _cycles(mapping))
    )


def _fixed_count(effective_weights: tuple[int, ...], total: int) -> int:
    coefficients = [1] + [0] * total
    for weight in effective_weights:
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for mass in range((total - degree) // weight + 1):
                multiplicity = comb(mass + 3, 3)
                next_coefficients[degree + weight * mass] += (
                    coefficient * multiplicity
                )
        coefficients = next_coefficients
    return coefficients[total]


def _burnside_count(total: int) -> int:
    fixed = tuple(
        _fixed_count(_effective_weights(mapping), total) for mapping in _MAPS
    )
    assert sum(fixed) % len(_MAPS) == 0
    return sum(fixed) // len(_MAPS)


@cache
def _values_of_mass(total: int) -> tuple[_Vector, ...]:
    return tuple(
        (first, second, third, total - first - second - third)
        for first in range(total + 1)
        for second in range(total - first + 1)
        for third in range(total - first - second + 1)
    )


@cache
def _states_from(
    index: int,
    remaining: int,
) -> tuple[_OrbitState, ...]:
    if index == len(_WEIGHTS):
        return ((),) if remaining == 0 else ()
    weight = _WEIGHTS[index]
    result: list[tuple[_Vector, ...]] = []
    for value_mass in range(remaining // weight + 1):
        residual = remaining - weight * value_mass
        for value in _values_of_mass(value_mass):
            result.extend(
                (value, *suffix) for suffix in _states_from(index + 1, residual)
            )
    return tuple(result)


def _transform(state: _OrbitState, mapping: tuple[int, ...]) -> _OrbitState:
    return tuple(state[mapping[index]] for index in range(len(mapping)))


def _direct_count(total: int) -> int:
    representatives = {
        min(_transform(state, mapping) for mapping in _MAPS)
        for state in _states_from(0, total)
    }
    return len(representatives)


def test_double_transposition_quotient_has_reviewed_v4_cycle_weights() -> None:
    """Residual maps induce the reviewed effective weight signatures."""
    observed = tuple(_effective_weights(mapping) for mapping in _MAPS)
    assert observed == _EXPECTED_EFFECTIVE_WEIGHTS


def test_double_transposition_quotient_burnside_sequence_through_fourteen() -> (
    None
):
    """Residual V4 Burnside arithmetic reaches the mass-fourteen target."""
    observed = tuple(
        _burnside_count(total) for total in range(_MAXIMUM_MASS + 1)
    )
    assert observed == _EXPECTED_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT


def test_double_transposition_quotient_matches_direct_small_orbits() -> None:
    """Direct widened quotient orbits agree with Burnside through mass two."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        assert _direct_count(total) == _burnside_count(total)
