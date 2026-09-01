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
#   - Exact full-S5 pair-valued K5 edge-orbit counts through residual mass 14.
# - Must-Not:
#   - Claim dense order-120 rank/unrank or complete dense S5 ranking.
# - Allows:
#   - Inputs: pair-valued K5 edge assignments of mass zero through fourteen.
#   - Outputs: exact S5 conjugacy-cycle data and orbit counts.
#   - Side effects: none.
# - Split-When:
#   - Constructive dense order-120 edge ranking is introduced.
# - Merge-When:
#   - Complete dense S5 ranking owns this all-equal-vertex edge hard core.
# - Summary:
#   - Isolate the order-120 all-equal-vertex edge hard core.
# - Description:
#   - Burnside-counts pair-valued K5 edges over the seven S5 vertex types.
# - Usage:
#   - Exact target and cycle-index prerequisite for dense order-120 ranking.
# - Defaults:
#   - Direct raw orbit exhaustion stops at mass three.
#

"""Exact full-S5 pair-valued K5 edge-orbit evidence."""

from __future__ import annotations

from collections import defaultdict
from itertools import permutations
from math import factorial

_ARITY = 5
_EDGE_COUNT = 10
_EXHAUSTIVE_MASS = 3
_MAXIMUM_MASS = 14
_S5 = tuple(permutations(range(_ARITY)))
_S5_ORDER = factorial(_ARITY)
_WIDTH_FOURTEEN_COUNT = 6_962_786
_EDGES = tuple(
    (left, right)
    for left in range(_ARITY)
    for right in range(left + 1, _ARITY)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_EXPECTED_TYPES = {
    (1, 1, 1, 1, 1): (1, (1,) * 10, 818_809_200),
    (2, 1, 1, 1): (10, (1, 1, 1, 1, 2, 2, 2), 1_504_176),
    (2, 2, 1): (15, (1, 1, 2, 2, 2, 2), 110_448),
    (3, 1, 1): (20, (1, 3, 3, 3), 990),
    (3, 2): (20, (1, 3, 6), 174),
    (4, 1): (30, (2, 4, 4), 112),
    (5,): (24, (5, 5), 0),
}
_EXPECTED_COUNTS = (
    1,
    2,
    9,
    36,
    146,
    546,
    1_972,
    6_650,
    21_135,
    63_162,
    178_382,
    477_670,
    1_218_583,
    2_972_858,
    6_962_786,
)

type _EdgePairs = tuple[tuple[int, int], ...]


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


def _fixed_pair_count(cycles: tuple[int, ...], total: int) -> int:
    coefficients = [1] + [0] * total
    for cycle_length in cycles:
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            multiplier = 0
            while degree + multiplier * cycle_length <= total:
                next_coefficients[degree + multiplier * cycle_length] += (
                    coefficient * (multiplier + 1)
                )
                multiplier += 1
        coefficients = next_coefficients
    return coefficients[total]


def _classes() -> dict[tuple[int, ...], tuple[tuple[int, ...], ...]]:
    grouped: dict[tuple[int, ...], list[tuple[int, ...]]] = defaultdict(list)
    for order in _S5:
        grouped[_partition(order)].append(order)
    return {partition: tuple(orders) for partition, orders in grouped.items()}


def _burnside_count(total: int) -> int:
    numerator = sum(
        _fixed_pair_count(_edge_cycles(order), total) for order in _S5
    )
    assert numerator % _S5_ORDER == 0
    return numerator // _S5_ORDER


def _visit_assignments(
    index: int,
    remaining: int,
    prefix: list[tuple[int, int]],
    *,
    result: list[_EdgePairs],
) -> None:
    if index == _EDGE_COUNT:
        if remaining == 0:
            result.append(tuple(prefix))
        return
    for left in range(remaining + 1):
        for right in range(remaining - left + 1):
            prefix.append((left, right))
            _visit_assignments(
                index + 1,
                remaining - left - right,
                prefix,
                result=result,
            )
            _ = prefix.pop()


def _assignments(total: int) -> tuple[_EdgePairs, ...]:
    result: list[_EdgePairs] = []
    _visit_assignments(0, total, [], result=result)
    return tuple(result)


def _permute(edge_pairs: _EdgePairs, order: tuple[int, ...]) -> _EdgePairs:
    result: list[tuple[int, int]] = []
    for left, right in _EDGES:
        source = tuple(sorted((order[left], order[right])))
        result.append(edge_pairs[_EDGE_INDEX[source[0], source[1]]])
    return tuple(result)


def _direct_orbit_count(total: int) -> int:
    representatives = {
        min(_permute(edge_pairs, order) for order in _S5)
        for edge_pairs in _assignments(total)
    }
    return len(representatives)


def test_s5_edge_conjugacy_types_have_exact_cycles_and_mass_fourteen_fixes(
) -> None:
    """Seven S5 vertex types induce the exact reviewed K5 edge cycles."""
    classes = _classes()
    assert set(classes) == set(_EXPECTED_TYPES)
    for partition, (weight, cycles, fixed) in _EXPECTED_TYPES.items():
        orders = classes[partition]
        assert len(orders) == weight
        assert {_edge_cycles(order) for order in orders} == {cycles}
        assert _fixed_pair_count(cycles, _MAXIMUM_MASS) == fixed


def test_s5_edge_burnside_sequence_is_exact_through_mass_fourteen() -> None:
    """Full-S5 pair-valued edge counts match the exact retained sequence."""
    observed = tuple(
        _burnside_count(total) for total in range(_MAXIMUM_MASS + 1)
    )
    assert observed == _EXPECTED_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT


def test_s5_edge_burnside_matches_direct_small_orbits() -> None:
    """Direct edge assignments reproduce Burnside through mass three."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        assert _burnside_count(total) == _direct_orbit_count(total)
