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
#   - Exact full-S5 four-component K5 edge-orbit counts through mass fourteen.
# - Must-Not:
#   - Claim dense order-120 rank/unrank or complete dense S5 ranking.
# - Allows:
#   - Inputs: ten four-component K5 edge values of mass zero through fourteen.
#   - Outputs: exact S5 conjugacy-cycle data and residual orbit counts.
#   - Side effects: none.
# - Split-When:
#   - Constructive dense order-120 edge ranking is introduced.
# - Merge-When:
#   - Complete dense S5 ranking owns this widened all-equal-bundle hard core.
# - Summary:
#   - Isolate the widened order-120 all-equal-bundle edge hard core.
# - Description:
#   - Burnside-counts four-component K5 edges over the seven S5 vertex types.
# - Usage:
#   - Exact target prerequisite for the final (5,1;5) dense ranking slice.
# - Defaults:
#   - Direct raw orbit exhaustion stops at mass two; arithmetic reaches 14.
#

"""Exact full-S5 widened K5 edge-orbit evidence for the S6 (5,1;5) slice."""

from __future__ import annotations

from collections import defaultdict
from itertools import permutations
from math import comb
from math import factorial

_ARITY = 5
_EDGE_COUNT = 10
_EDGE_COMPONENTS = 4
_SCALAR_COMPONENTS = _EDGE_COUNT * _EDGE_COMPONENTS
_EXHAUSTIVE_MASS = 2
_MAXIMUM_MASS = 14
_S5 = tuple(permutations(range(_ARITY)))
_S5_ORDER = factorial(_ARITY)
_WIDTH_FOURTEEN_COUNT = 20_103_708_128
_EDGES = tuple(
    (left, right) for left in range(_ARITY) for right in range(left + 1, _ARITY)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_EXPECTED_TYPES = {
    (1, 1, 1, 1, 1): (1, (1,) * 10, 2_403_979_904_200),
    (2, 1, 1, 1): (10, (1, 1, 1, 1, 2, 2, 2), 812_318_344),
    (2, 2, 1): (15, (1, 1, 2, 2, 2, 2), 22_709_960),
    (3, 1, 1): (20, (1, 3, 3, 3), 51_952),
    (3, 2): (20, (1, 3, 6), 7_312),
    (4, 1): (30, (2, 4, 4), 1_768),
    (5,): (24, (5, 5), 0),
}
_EXPECTED_COUNTS = (
    1,
    4,
    30,
    220,
    1_651,
    11_784,
    78_886,
    486_608,
    2_759_434,
    14_421_284,
    69_829_516,
    315_151_692,
    1_333_556_680,
    5_319_669_572,
    20_103_708_128,
)

type _EdgeValue = tuple[int, int, int, int]
type _EdgeValues = tuple[_EdgeValue, ...]
type _Vector = tuple[int, ...]


def _partition(order: tuple[int, ...]) -> tuple[int, ...]:
    unseen = set(range(_ARITY))
    lengths: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = order[current]
            length += 1
        lengths.append(length)
    return tuple(sorted(lengths, reverse=True))


def _edge_cycles(order: tuple[int, ...]) -> tuple[int, ...]:
    permutation: list[int] = []
    for left, right in _EDGES:
        image = tuple(sorted((order[left], order[right])))
        permutation.append(_EDGE_INDEX[image[0], image[1]])
    unseen = set(range(_EDGE_COUNT))
    lengths: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = permutation[current]
            length += 1
        lengths.append(length)
    return tuple(sorted(lengths))


def _fixed_value_count(cycles: tuple[int, ...], total: int) -> int:
    coefficients = [1] + [0] * total
    for cycle_length in cycles:
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            value_mass = 0
            while degree + value_mass * cycle_length <= total:
                multiplicity = comb(
                    value_mass + _EDGE_COMPONENTS - 1,
                    _EDGE_COMPONENTS - 1,
                )
                next_coefficients[degree + value_mass * cycle_length] += (
                    coefficient * multiplicity
                )
                value_mass += 1
        coefficients = next_coefficients
    return coefficients[total]


def _classes() -> dict[tuple[int, ...], tuple[tuple[int, ...], ...]]:
    grouped: dict[tuple[int, ...], list[tuple[int, ...]]] = defaultdict(list)
    for order in _S5:
        grouped[_partition(order)].append(order)
    return {partition: tuple(orders) for partition, orders in grouped.items()}


def _burnside_count(total: int) -> int:
    numerator = sum(
        _fixed_value_count(_edge_cycles(order), total) for order in _S5
    )
    assert numerator % _S5_ORDER == 0
    return numerator // _S5_ORDER


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _edge_values_from_vector(vector: _Vector) -> _EdgeValues:
    assert len(vector) == _SCALAR_COMPONENTS
    values = tuple(
        tuple(vector[index : index + _EDGE_COMPONENTS])
        for index in range(0, _SCALAR_COMPONENTS, _EDGE_COMPONENTS)
    )
    return tuple((value[0], value[1], value[2], value[3]) for value in values)


def _permute(edge_values: _EdgeValues, order: tuple[int, ...]) -> _EdgeValues:
    result: list[_EdgeValue] = []
    for left, right in _EDGES:
        source = tuple(sorted((order[left], order[right])))
        result.append(edge_values[_EDGE_INDEX[source[0], source[1]]])
    return tuple(result)


def _direct_orbit_count(total: int) -> int:
    representatives = {
        min(_permute(_edge_values_from_vector(vector), order) for order in _S5)
        for vector in _weak_compositions(total, _SCALAR_COMPONENTS)
    }
    return len(representatives)


def test_s6_s5_edge_conjugacy_types_have_exact_widened_fixes() -> None:
    """Seven S5 vertex types induce the exact widened K5 fixed counts."""
    classes = _classes()
    assert set(classes) == set(_EXPECTED_TYPES)
    for partition, (weight, cycles, fixed) in _EXPECTED_TYPES.items():
        orders = classes[partition]
        assert len(orders) == weight
        assert {_edge_cycles(order) for order in orders} == {cycles}
        assert _fixed_value_count(cycles, _MAXIMUM_MASS) == fixed


def test_s6_s5_edge_burnside_sequence_is_exact_through_fourteen() -> None:
    """Full-S5 widened edge counts match the independently retained sequence."""
    observed = tuple(
        _burnside_count(total) for total in range(_MAXIMUM_MASS + 1)
    )
    assert observed == _EXPECTED_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT


def test_s6_s5_edge_burnside_matches_direct_small_orbits() -> None:
    """Direct widened edge assignments reproduce Burnside through mass two."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        assert _burnside_count(total) == _direct_orbit_count(total)
