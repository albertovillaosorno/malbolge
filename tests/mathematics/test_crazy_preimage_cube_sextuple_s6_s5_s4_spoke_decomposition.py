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
#   - Nested S4 spoke factorization of the S6 (5,1)/(4,1) stratum.
# - Must-Not:
#   - Claim dense ranking for any second-layer spoke stabilizer.
# - Allows:
#   - Inputs: ambiguity mass zero through fourteen.
#   - Outputs: exact spoke/K4-edge quotient and complete-stratum counts.
#   - Side effects: none.
# - Split-When:
#   - A spoke stabilizer receives constructive rank/unrank.
# - Merge-When:
#   - Complete dense ranking owns the full (5,1)/(4,1) slice.
# - Summary:
#   - Sort four four-scalar spokes, then quotient six widened K4 edges.
# - Description:
#   - Leaves identity, S2, V4, S3, and S4 spoke stabilizers.
# - Usage:
#   - Canonical prerequisite for dense ranking of the order-24 S5 slice.
# - Defaults:
#   - Direct edge orbits stop at mass two; arithmetic reaches mass fourteen.
#

"""Nested S4 spoke factorization inside the S6 (5,1) stratum."""

from __future__ import annotations

from collections import Counter
from collections import defaultdict
from functools import cache
from itertools import combinations_with_replacement
from itertools import permutations
from itertools import product
from math import comb
from math import factorial

_ACTIVE = tuple(range(4))
_FIXED_VERTEX = 4
_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 2
_COMPONENTS = 4
_SPOKE_COUNT = 4
_EDGE_COUNT = 6
_K5_EDGES = tuple(
    (left, right) for left in range(5) for right in range(left + 1, 5)
)
_K4_EDGES = tuple(edge for edge in _K5_EDGES if _FIXED_VERTEX not in edge)
_SPOKES = tuple((vertex, _FIXED_VERTEX) for vertex in _ACTIVE)
_SECOND_PARTITIONS = {
    (1, 1, 1, 1),
    (2, 1, 1),
    (2, 2),
    (3, 1),
    (4,),
}
_WIDTH_FOURTEEN_EDGE_QUOTIENT = 100_371_765_432
_WIDTH_FOURTEEN_FULL_SLICE = 96_141_721_711
_EXPECTED_FULL_CONTRIBUTIONS = {
    (1, 1, 1, 1): 35_347_204_706,
    (2, 1, 1): 45_289_854_118,
    (2, 2): 2_603_914_760,
    (3, 1): 11_867_845_606,
    (4,): 1_032_902_521,
}

type _Partition = tuple[int, ...]
type _Permutation = tuple[int, int, int, int]


def _as_permutation(values: tuple[int, ...]) -> _Permutation:
    assert len(values) == len(_ACTIVE)
    first, second, third, fourth = values
    return first, second, third, fourth


_S4: tuple[_Permutation, ...] = tuple(
    _as_permutation(values) for values in permutations(_ACTIVE)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_K4_EDGES)}


def _composition_count(total: int, parts: int) -> int:
    return comb(total + parts - 1, parts - 1) if total >= 0 and parts > 0 else 0


def _fixed_count(cycles: tuple[int, ...], mass: int) -> int:
    coefficients = [1] + [0] * mass
    for cycle_length in cycles:
        next_coefficients = [0] * (mass + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, mass - degree + 1, cycle_length):
                next_coefficients[degree + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[mass]


def _ordered_edge(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def _k4_edge_cycles(order: _Permutation) -> tuple[int, ...]:
    permutation = tuple(
        _EDGE_INDEX[_ordered_edge(order[left], order[right])]
        for left, right in _K4_EDGES
    )
    unseen = set(range(_EDGE_COUNT))
    result: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = permutation[current]
            length += 1
        result.append(length)
    return tuple(sorted(result))


def _partition_blocks(partition: _Partition) -> tuple[tuple[int, ...], ...]:
    result: list[tuple[int, ...]] = []
    start = 0
    for size in partition:
        result.append(tuple(range(start, start + size)))
        start += size
    assert start == _SPOKE_COUNT
    return tuple(result)


@cache
def _young_group(partition: _Partition) -> tuple[_Permutation, ...]:
    choices = tuple(
        tuple(permutations(block)) for block in _partition_blocks(partition)
    )
    result: list[_Permutation] = []
    for block_orders in product(*choices):
        order = list(_ACTIVE)
        for block, block_order in zip(
            _partition_blocks(partition), block_orders, strict=True
        ):
            for source, destination in zip(block, block_order, strict=True):
                order[source] = destination
        first, second, third, fourth = order
        result.append((first, second, third, fourth))
    return tuple(result)


@cache
def _k4_edge_quotient(partition: _Partition, mass: int) -> int:
    group = _young_group(partition)
    fixed = sum(
        _fixed_count(
            tuple(sorted(_k4_edge_cycles(order) * _COMPONENTS)),
            mass,
        )
        for order in group
    )
    assert fixed % len(group) == 0
    return fixed // len(group)


def _spoke_population(mass: int) -> int:
    return _composition_count(mass, _COMPONENTS)


def _choice_partition(counts: tuple[int, int, int, int]) -> _Partition:
    return tuple(
        sorted(
            (
                index + 1
                for index, count in enumerate(counts)
                for _ in range(count)
            ),
            reverse=True,
        )
    )


def _choice_ways(population: int, counts: tuple[int, int, int, int]) -> int:
    objects = sum(counts)
    result = 1
    for index in range(objects):
        result *= population - index
    for count in counts:
        result //= factorial(count)
    return result


def _mass_choices(mass: int) -> tuple[tuple[int, int, _Partition, int], ...]:
    population = _spoke_population(mass)
    ranges = (range(5), range(3), range(2), range(2))
    result: list[tuple[int, int, _Partition, int]] = []
    for counts in product(*ranges):
        singles, doubles, triples, quads = counts
        slots = singles + 2 * doubles + 3 * triples + 4 * quads
        objects = sum(counts)
        if slots > _SPOKE_COUNT or objects > population:
            continue
        result.append((
            slots,
            mass * slots,
            _choice_partition(counts),
            _choice_ways(population, counts),
        ))
    return tuple(result)


def _advance_states(
    states: dict[tuple[int, int, _Partition], int],
    mass: int,
) -> dict[tuple[int, int, _Partition], int]:
    result: defaultdict[tuple[int, int, _Partition], int] = defaultdict(int)
    for (slots, total, partition), base in states.items():
        for added_slots, added_mass, added_partition, ways in _mass_choices(
            mass
        ):
            new_slots = slots + added_slots
            new_total = total + added_mass
            if new_slots > _SPOKE_COUNT or new_total > _MAXIMUM_MASS:
                continue
            merged = tuple(sorted(partition + added_partition, reverse=True))
            result[new_slots, new_total, merged] += base * ways
    return dict(result)


@cache
def _spoke_histogram() -> Counter[tuple[int, _Partition]]:
    states: dict[tuple[int, int, _Partition], int] = {(0, 0, ()): 1}
    for mass in range(_MAXIMUM_MASS + 1):
        states = _advance_states(states, mass)
    result: Counter[tuple[int, _Partition]] = Counter()
    for (slots, mass, partition), count in states.items():
        if slots == _SPOKE_COUNT:
            result[mass, partition] += count
    return result


@cache
def _factored_edge_count(total: int) -> int:
    histogram = _spoke_histogram()
    return sum(
        histogram[spoke_mass, partition]
        * _k4_edge_quotient(partition, total - spoke_mass)
        for spoke_mass in range(total + 1)
        for partition in _SECOND_PARTITIONS
    )


def _full_s4_edge_count(total: int) -> int:
    fixed = 0
    for order in _S4:
        # Spokes transform as vertices; K4 edges use induced edge action.
        spoke_cycles = _permutation_cycles(order)
        edge_cycles = _k4_edge_cycles(order)
        scalar_cycles = tuple(
            sorted((spoke_cycles + edge_cycles) * _COMPONENTS)
        )
        fixed += _fixed_count(scalar_cycles, total)
    assert fixed % len(_S4) == 0
    return fixed // len(_S4)


def _permutation_cycles(order: _Permutation) -> tuple[int, ...]:
    unseen = set(_ACTIVE)
    result: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = order[current]
            length += 1
        result.append(length)
    return tuple(sorted(result))


def _raw_edge_orbit_count(mass: int) -> int:
    # Forty scalar positions: four spoke bundles plus six edge bundles.
    positions = tuple(range((_SPOKE_COUNT + _EDGE_COUNT) * _COMPONENTS))
    maps: list[tuple[int, ...]] = []
    for order in _S4:
        mapped: list[int] = []
        for position in positions:
            bundle, component = divmod(position, _COMPONENTS)
            if bundle < _SPOKE_COUNT:
                image_bundle = order[bundle]
            else:
                left, right = _K4_EDGES[bundle - _SPOKE_COUNT]
                image_edge = _ordered_edge(order[left], order[right])
                image_bundle = _SPOKE_COUNT + _EDGE_INDEX[image_edge]
            mapped.append(image_bundle * _COMPONENTS + component)
        maps.append(tuple(mapped))
    representatives = {
        min(
            tuple(sorted(mapping[index] for index in labels))
            for mapping in maps
        )
        for labels in combinations_with_replacement(positions, mass)
    }
    return len(representatives)


def _pair_sequences_from(
    start: int,
    slots: int,
    remaining: int,
) -> tuple[tuple[tuple[int, int], ...], ...]:
    if slots == 0:
        return ((),)
    values = tuple(
        (first, second)
        for first in range(_MAXIMUM_MASS + 1)
        for second in range(_MAXIMUM_MASS - first + 1)
    )
    result: list[tuple[tuple[int, int], ...]] = []
    for index in range(start, len(values)):
        pair = values[index]
        pair_mass = sum(pair)
        if pair_mass > remaining:
            continue
        result.extend(
            (pair, *suffix)
            for suffix in _pair_sequences_from(
                index,
                slots - 1,
                remaining - pair_mass,
            )
        )
    return tuple(result)


@cache
def _top_histogram() -> Counter[int]:
    result: Counter[int] = Counter()
    for values in _pair_sequences_from(0, 6, _MAXIMUM_MASS):
        if tuple(sorted(Counter(values).values(), reverse=True)) == (5, 1):
            result[sum(sum(pair) for pair in values)] += 1
    return result


@cache
def _second_bundle_histogram() -> Counter[int]:
    # Five two-component bundles with partition (4,1).
    result: Counter[int] = Counter()
    for values in _pair_sequences_from(0, 5, _MAXIMUM_MASS):
        if tuple(sorted(Counter(values).values(), reverse=True)) == (4, 1):
            result[sum(sum(pair) for pair in values)] += 1
    return result


def _partition_edge_count(partition: _Partition, total: int) -> int:
    histogram = _spoke_histogram()
    return sum(
        histogram[spoke_mass, partition]
        * _k4_edge_quotient(partition, total - spoke_mass)
        for spoke_mass in range(total + 1)
    )


def _residual_contribution(partition: _Partition, total: int) -> int:
    second = _second_bundle_histogram()
    return sum(
        (fixed_mass + 1)
        * second[bundle_mass]
        * _partition_edge_count(
            partition,
            total - fixed_mass - bundle_mass,
        )
        for fixed_mass in range(total + 1)
        for bundle_mass in range(total - fixed_mass + 1)
    )


def _full_slice_contribution(partition: _Partition, total: int) -> int:
    top = _top_histogram()
    residual = tuple(
        _residual_contribution(partition, mass) for mass in range(total + 1)
    )
    return sum(
        top[vertex_mass] * residual[total - vertex_mass]
        for vertex_mass in range(total + 1)
    )


def test_s6_s5_s4_edges_split_into_spokes_and_k4_edges() -> None:
    """S4 sees four spokes to the singleton and six internal K4 edges."""
    assert len(_SPOKES) == _SPOKE_COUNT
    assert len(_K4_EDGES) == _EDGE_COUNT
    assert set(_SPOKES) | set(_K4_EDGES) == set(_K5_EDGES)


def test_s6_s5_s4_spokes_leave_exact_five_stabilizers() -> None:
    """Four sorted four-component spokes induce the five Young groups."""
    observed = {partition for _, partition in _spoke_histogram()}
    assert observed == _SECOND_PARTITIONS
    for partition in observed:
        expected = 1
        for size in partition:
            expected *= factorial(size)
        assert len(_young_group(partition)) == expected


def test_s6_s5_s4_factorization_matches_direct_small_orbits() -> None:
    """The spoke/K4 factorization agrees with direct S4 scalar orbits."""
    for mass in range(_EXHAUSTIVE_MASS + 1):
        assert _factored_edge_count(mass) == _raw_edge_orbit_count(mass)


def test_s6_s5_s4_factorization_matches_burnside_through_fourteen() -> None:
    """Five spoke stabilizers reconstruct the residual S4 edge quotient."""
    for mass in range(_MAXIMUM_MASS + 1):
        assert _factored_edge_count(mass) == _full_s4_edge_count(mass)
    assert _factored_edge_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_EDGE_QUOTIENT
    contributions = {
        partition: _full_slice_contribution(partition, _MAXIMUM_MASS)
        for partition in _SECOND_PARTITIONS
    }
    assert contributions == _EXPECTED_FULL_CONTRIBUTIONS
    assert sum(contributions.values()) == _WIDTH_FOURTEEN_FULL_SLICE
