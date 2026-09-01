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
#   - Exact vertex-spoke/K4-edge stabilizer decomposition for pair-valued K5
#     edges under a residual S4 vertex stabilizer.
# - Must-Not:
#   - Claim dense S4 residual rank/unrank or complete dense S5 ranking.
# - Allows:
#   - Inputs: residual edge-pair mass zero through fourteen.
#   - Outputs: exact stabilizer-shape and total orbit counts.
#   - Side effects: none.
# - Split-When:
#   - Constructive dense S4 residual ranking is introduced.
# - Merge-When:
#   - Dense S5 ranking owns this four-spoke/K4-edge decomposition.
# - Summary:
#   - Decompose residual S4 pair-valued K5 edge orbits by spoke multiplicity.
# - Description:
#   - Sorts four spoke pairs, then Burnside-counts pair-valued K4 edges under
#     the equal-spoke stabilizer.
# - Usage:
#   - Prerequisite for dense residual order-twenty-four ranking.
# - Defaults:
#   - Direct full-group orbit enumeration stops at mass three.
#

"""Residual S4 spoke/K4-edge decomposition for pair-valued K5 edges."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import permutations
from math import factorial

_ACTIVE = (0, 1, 2, 3)
_EDGE_COMPONENTS = 12
_EXHAUSTIVE_MASS = 3
_MAXIMUM_MASS = 14
_SPOKE_COMPONENTS = 8
_WIDTH_FOURTEEN_COUNT = 34_507_258
_K4_EDGES = tuple(
    (left, right)
    for left in _ACTIVE
    for right in _ACTIVE
    if left < right
)
_K4_EDGE_INDEX = {edge: index for index, edge in enumerate(_K4_EDGES)}
_S4 = tuple(permutations(_ACTIVE))
_PARTITIONS = (
    (1, 1, 1, 1),
    (2, 1, 1),
    (2, 2),
    (3, 1),
    (4,),
)

type _Pair = tuple[int, int]
type _Spokes = tuple[_Pair, _Pair, _Pair, _Pair]
type _Vector = tuple[int, ...]


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _spokes_from_vector(vector: _Vector) -> _Spokes:
    pairs = tuple(
        (vector[index], vector[index + 1]) for index in range(0, 8, 2)
    )
    return pairs[0], pairs[1], pairs[2], pairs[3]


def _canonical_spokes(vector: _Vector) -> _Spokes:
    spokes = sorted(_spokes_from_vector(vector))
    return spokes[0], spokes[1], spokes[2], spokes[3]


def _multiplicity_partition(spokes: _Spokes) -> tuple[int, ...]:
    multiplicities = Counter(spokes).values()
    return tuple(sorted(multiplicities, reverse=True))


@cache
def _spoke_shape_counts(total: int) -> dict[tuple[int, ...], int]:
    canonical = {
        _canonical_spokes(vector)
        for vector in _weak_compositions(total, _SPOKE_COMPONENTS)
    }
    counts = Counter(_multiplicity_partition(spokes) for spokes in canonical)
    return {partition: counts[partition] for partition in _PARTITIONS}


def _representative_labels(
    partition: tuple[int, ...],
) -> tuple[int, int, int, int]:
    labels: list[int] = []
    for label, size in enumerate(partition):
        labels.extend([label] * size)
    return labels[0], labels[1], labels[2], labels[3]


@cache
def _stabilizer(partition: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    labels = _representative_labels(partition)
    return tuple(
        order
        for order in _S4
        if all(labels[order[index]] == labels[index] for index in _ACTIVE)
    )


def _edge_cycles(order: tuple[int, ...]) -> tuple[int, ...]:
    permutation: list[int] = []
    for left, right in _K4_EDGES:
        source = tuple(sorted((order[left], order[right])))
        permutation.append(_K4_EDGE_INDEX[source[0], source[1]])
    unseen = set(range(len(_K4_EDGES)))
    cycles: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = permutation[current]
            length += 1
        cycles.append(length)
    return tuple(sorted(cycles))


def _fixed_count(cycles: tuple[int, ...], total: int) -> int:
    coefficients = [1] + [0] * total
    for cycle_length in cycles:
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, total - degree + 1, cycle_length):
                next_coefficients[degree + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[total]


@cache
def _edge_quotient_count(partition: tuple[int, ...], total: int) -> int:
    group = _stabilizer(partition)
    fixed_sum = sum(
        _fixed_count(tuple(sorted(_edge_cycles(order) * 2)), total)
        for order in group
    )
    return fixed_sum // len(group)


def _decomposed_count(total: int) -> int:
    return sum(
        shape_count * _edge_quotient_count(partition, total - spoke_mass)
        for spoke_mass in range(total + 1)
        for partition, shape_count in _spoke_shape_counts(spoke_mass).items()
    )


def _full_edge_cycles(order: tuple[int, ...]) -> tuple[int, ...]:
    full_edges = tuple(
        (left, right) for left in range(5) for right in range(left + 1, 5)
    )
    index = {edge: position for position, edge in enumerate(full_edges)}
    full_order = (*order, 4)
    permutation: list[int] = []
    for left, right in full_edges:
        source = tuple(sorted((full_order[left], full_order[right])))
        permutation.append(index[source[0], source[1]])
    unseen = set(range(len(full_edges)))
    cycles: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = permutation[current]
            length += 1
        cycles.append(length)
    return tuple(sorted(cycles))


def _full_burnside_count(total: int) -> int:
    fixed_sum = sum(
        _fixed_count(tuple(sorted(_full_edge_cycles(order) * 2)), total)
        for order in _S4
    )
    return fixed_sum // factorial(len(_ACTIVE))


def test_s4_spoke_shapes_have_exact_stabilizer_orders() -> None:
    """Each spoke multiplicity partition has the expected Young stabilizer."""
    expected = {
        (1, 1, 1, 1): 1,
        (2, 1, 1): 2,
        (2, 2): 4,
        (3, 1): 6,
        (4,): 24,
    }
    for partition, order in expected.items():
        assert len(_stabilizer(partition)) == order


def _full_scalar_permutation(order: tuple[int, ...]) -> tuple[int, ...]:
    full_edges = tuple(
        (left, right) for left in range(5) for right in range(left + 1, 5)
    )
    edge_index = {edge: position for position, edge in enumerate(full_edges)}
    full_order = (*order, 4)
    edge_permutation: list[int] = []
    for left, right in full_edges:
        source = tuple(sorted((full_order[left], full_order[right])))
        edge_permutation.append(edge_index[source[0], source[1]])
    return tuple(
        2 * edge_permutation[edge] + component
        for edge in range(len(full_edges))
        for component in range(2)
    )


def _permute_vector(vector: _Vector, permutation: tuple[int, ...]) -> _Vector:
    result = [0] * len(vector)
    for source, destination in enumerate(permutation):
        result[destination] = vector[source]
    return tuple(result)


def _direct_orbit_count(total: int) -> int:
    permutations = tuple(_full_scalar_permutation(order) for order in _S4)
    representatives = {
        min(_permute_vector(vector, order) for order in permutations)
        for vector in _weak_compositions(total, 20)
    }
    return len(representatives)


def test_s4_decomposition_matches_direct_small_orbit_counts() -> None:
    """Small residual domains agree with direct full-S4 Burnside counts."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        assert _decomposed_count(total) == _direct_orbit_count(total)
        assert _decomposed_count(total) == _full_burnside_count(total)


def test_s4_decomposition_is_exact_through_mass_fourteen() -> None:
    """Spoke/K4-edge factorization reproduces S4 Burnside through mass 14."""
    for total in range(_MAXIMUM_MASS + 1):
        assert _decomposed_count(total) == _full_burnside_count(total)
    assert _decomposed_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
