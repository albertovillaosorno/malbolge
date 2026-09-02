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
#   - Nested S4 factorization of the S6 vertex partition (4,1,1).
# - Must-Not:
#   - Claim dense ranking for any second-layer S4 stabilizer.
# - Allows:
#   - Inputs: residual and complete sextuple mass zero through fourteen.
#   - Outputs: exact fixed/vertex-bundle/K4-edge residual quotient counts.
#   - Side effects: none.
# - Split-When:
#   - A second-layer S4 stabilizer receives constructive rank/unrank.
# - Merge-When:
#   - Complete dense S6 ranking owns the same nested S4 factorization.
# - Summary:
#   - Sort four six-component vertex bundles, then quotient K4 edge bundles.
# - Description:
#   - Leaves five second-layer stabilizers: identity, S2, V4, S3, and S4.
# - Usage:
#   - Canonical prerequisite for dense ranking of the (4,1,1) S6 stratum.
# - Defaults:
#   - Direct residual orbits stop at mass two; arithmetic reaches mass 14.
#

"""Nested S4 factorization of the S6 (4,1,1) Young stratum."""

from __future__ import annotations

from collections import Counter
from collections import defaultdict
from functools import cache
from itertools import combinations_with_replacement
from itertools import permutations
from itertools import product
from math import comb
from math import factorial

_ARITY = 6
_ACTIVE_COUNT = 4
_ACTIVE = tuple(range(_ACTIVE_COUNT))
_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 2
_RESIDUAL_COMPONENTS = 52
_FIXED_COMPONENTS = 4
_VERTEX_COMPONENTS = 6
_EDGE_COMPONENTS = 4
_EDGE_WEIGHT = 2
_VERTEX_BUNDLE_COUNT = 4
_EDGE_BUNDLE_COUNT = 6
_WIDTH_FOURTEEN_RESIDUAL_COUNT = 2_549_713_246_880
_WIDTH_FOURTEEN_STRATUM_COUNT = 302_650_855_156
_TOP_PARTITION = (4, 1, 1)
_SECOND_PARTITIONS = {
    (1, 1, 1, 1),
    (2, 1, 1),
    (2, 2),
    (3, 1),
    (4,),
}
_K4_EDGES = tuple(
    (left, right)
    for left in _ACTIVE
    for right in _ACTIVE
    if left < right
)
_K4_EDGE_INDEX = {edge: index for index, edge in enumerate(_K4_EDGES)}

type _Pair = tuple[int, int]
type _Partition = tuple[int, ...]
type _Permutation = tuple[int, int, int, int, int, int]


def _as_permutation(order: tuple[int, ...]) -> _Permutation:
    assert len(order) == _ARITY
    first, second, third, fourth, fifth, sixth = order
    return first, second, third, fourth, fifth, sixth


_S4: tuple[_Permutation, ...] = tuple(
    _as_permutation((*order, 4, 5)) for order in permutations(_ACTIVE)
)
_RESIDUAL_LABELS = tuple(
    symbol
    for symbol in range(1 << _ARITY)
    if symbol.bit_count() not in {1, _ARITY - 1}
)
_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)


def _permuted_symbol(symbol: int, order: _Permutation) -> int:
    bits = tuple(
        (symbol >> (_ARITY - endpoint - 1)) & 1
        for endpoint in range(_ARITY)
    )
    result = 0
    for source in order:
        result = (result << 1) | bits[source]
    return result


def _s4_orbits() -> tuple[tuple[int, ...], ...]:
    unseen = set(_RESIDUAL_LABELS)
    result: list[tuple[int, ...]] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(sorted({_permuted_symbol(seed, order) for order in _S4}))
        unseen -= set(orbit)
        result.append(orbit)
    return tuple(result)


def _active_bits(label: int) -> tuple[int, int, int, int]:
    values = tuple(
        (label >> (_ARITY - endpoint - 1)) & 1
        for endpoint in _ACTIVE
    )
    first, second, third, fourth = values
    return first, second, third, fourth


def _active_vertex(label: int) -> int:
    bits = _active_bits(label)
    weight = sum(bits)
    assert weight in {1, _ACTIVE_COUNT - 1}
    return bits.index(1) if weight == 1 else bits.index(0)


def _active_edge(label: int) -> tuple[int, int]:
    bits = _active_bits(label)
    assert sum(bits) == _EDGE_WEIGHT
    values = tuple(index for index, value in enumerate(bits) if value == 1)
    left, right = values
    return left, right


def _label_geometry(
) -> tuple[
    tuple[int, ...],
    tuple[tuple[int, int, int, int], ...],
    tuple[tuple[int, ...], ...],
]:
    fixed: list[int] = []
    vertices: list[tuple[int, int, int, int]] = []
    edges: list[tuple[int, ...]] = []
    for orbit in _s4_orbits():
        if len(orbit) == 1:
            fixed.append(orbit[0])
        elif len(orbit) == _ACTIVE_COUNT:
            by_vertex = {_active_vertex(label): label for label in orbit}
            item = tuple(by_vertex[index] for index in _ACTIVE)
            first, second, third, fourth = item
            vertices.append((first, second, third, fourth))
        else:
            assert len(orbit) == len(_K4_EDGES)
            by_edge = {_active_edge(label): label for label in orbit}
            edges.append(tuple(by_edge[edge] for edge in _K4_EDGES))
    return tuple(fixed), tuple(vertices), tuple(edges)


def _fixed_count_from_cycles(cycles: tuple[int, ...], mass: int) -> int:
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


def _label_cycles(order: _Permutation) -> tuple[int, ...]:
    unseen = set(_RESIDUAL_LABELS)
    result: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = _permuted_symbol(current, order)
            length += 1
        result.append(length)
    return tuple(sorted(result))


@cache
def _full_residual_count(mass: int) -> int:
    fixed = sum(
        _fixed_count_from_cycles(_label_cycles(order), mass) for order in _S4
    )
    assert fixed % len(_S4) == 0
    return fixed // len(_S4)


def _partition_blocks(partition: _Partition) -> tuple[tuple[int, ...], ...]:
    result: list[tuple[int, ...]] = []
    start = 0
    for size in partition:
        result.append(tuple(range(start, start + size)))
        start += size
    assert start == _ACTIVE_COUNT
    return tuple(result)


@cache
def _young_group(partition: _Partition) -> tuple[tuple[int, ...], ...]:
    blocks = _partition_blocks(partition)
    choices = tuple(tuple(permutations(block)) for block in blocks)
    result: list[tuple[int, ...]] = []
    for block_orders in product(*choices):
        order = list(_ACTIVE)
        for block, block_order in zip(blocks, block_orders, strict=True):
            for source, destination in zip(block, block_order, strict=True):
                order[source] = destination
        result.append(tuple(order))
    return tuple(result)


def _ordered_edge(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def _edge_cycles(order: tuple[int, ...]) -> tuple[int, ...]:
    permutation = tuple(
        _K4_EDGE_INDEX[_ordered_edge(order[left], order[right])]
        for left, right in _K4_EDGES
    )
    unseen = set(range(len(_K4_EDGES)))
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


@cache
def _edge_quotient_count(partition: _Partition, mass: int) -> int:
    group = _young_group(partition)
    fixed = sum(
        _fixed_count_from_cycles(
            tuple(sorted(_edge_cycles(order) * _EDGE_COMPONENTS)),
            mass,
        )
        for order in group
    )
    assert fixed % len(group) == 0
    return fixed // len(group)


def _bundle_population(mass: int) -> int:
    return comb(mass + _VERTEX_COMPONENTS - 1, _VERTEX_COMPONENTS - 1)


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


def _choice_data(
    mass: int,
    population: int,
    counts: tuple[int, int, int, int],
) -> tuple[int, int, _Partition, int] | None:
    slots = sum((index + 1) * count for index, count in enumerate(counts))
    objects = sum(counts)
    result: tuple[int, int, _Partition, int] | None = None
    if slots <= _VERTEX_BUNDLE_COUNT and objects <= population:
        result = (
            slots,
            mass * slots,
            _choice_partition(counts),
            _choice_ways(population, counts),
        )
    return result


def _mass_choices(mass: int) -> tuple[tuple[int, int, _Partition, int], ...]:
    population = _bundle_population(mass)
    ranges = (
        range(_VERTEX_BUNDLE_COUNT + 1),
        range(_VERTEX_BUNDLE_COUNT // 2 + 1),
        range(2),
        range(2),
    )
    result: list[tuple[int, int, _Partition, int]] = []
    for values in product(*ranges):
        singles, doubles, triples, quads = values
        item = _choice_data(
            mass,
            population,
            (singles, doubles, triples, quads),
        )
        if item is not None:
            result.append(item)
    return tuple(result)


def _advance_states(
    states: dict[tuple[int, int, _Partition], int],
    mass: int,
) -> dict[tuple[int, int, _Partition], int]:
    result: defaultdict[tuple[int, int, _Partition], int] = defaultdict(int)
    for (slots, total, partition), base in states.items():
        choices = _mass_choices(mass)
        for added_slots, added_mass, added_partition, ways in choices:
            new_slots = slots + added_slots
            new_total = total + added_mass
            valid_slots = new_slots <= _VERTEX_BUNDLE_COUNT
            if not valid_slots or new_total > _MAXIMUM_MASS:
                continue
            merged = tuple(
                sorted(partition + added_partition, reverse=True)
            )
            result[new_slots, new_total, merged] += base * ways
    return dict(result)


@cache
def _vertex_bundle_histogram() -> Counter[tuple[int, _Partition]]:
    states: dict[tuple[int, int, _Partition], int] = {(0, 0, ()): 1}
    for mass in range(_MAXIMUM_MASS + 1):
        states = _advance_states(states, mass)
    result: Counter[tuple[int, _Partition]] = Counter()
    for (slots, mass, partition), count in states.items():
        if slots == _VERTEX_BUNDLE_COUNT:
            result[mass, partition] += count
    return result


@cache
def _factored_residual_count(total: int) -> int:
    histogram = _vertex_bundle_histogram()
    return sum(
        comb(fixed_mass + _FIXED_COMPONENTS - 1, _FIXED_COMPONENTS - 1)
        * histogram[vertex_mass, partition]
        * _edge_quotient_count(partition, total - fixed_mass - vertex_mass)
        for fixed_mass in range(total + 1)
        for vertex_mass in range(total - fixed_mass + 1)
        for partition in _SECOND_PARTITIONS
    )


def _pair_sequences_from(
    start: int,
    slots: int,
    remaining: int,
) -> tuple[tuple[_Pair, ...], ...]:
    if slots == 0:
        return ((),)
    result: list[tuple[_Pair, ...]] = []
    for index in range(start, len(_PAIR_VALUES)):
        pair = _PAIR_VALUES[index]
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
def _top_vertex_histogram() -> Counter[int]:
    result: Counter[int] = Counter()
    for values in _pair_sequences_from(0, _ARITY, _MAXIMUM_MASS):
        multiplicities = Counter(values)
        partition = tuple(sorted(multiplicities.values(), reverse=True))
        if partition == _TOP_PARTITION:
            result[sum(sum(pair) for pair in values)] += 1
    return result


@cache
def _stratum_count(total: int) -> int:
    histogram = _top_vertex_histogram()
    return sum(
        histogram[vertex_mass] * _factored_residual_count(total - vertex_mass)
        for vertex_mass in range(total + 1)
    )


def _direct_residual_orbit_count(mass: int) -> int:
    maps = tuple(
        tuple(_permuted_symbol(label, order) for label in _RESIDUAL_LABELS)
        for order in _S4
    )
    index = {label: position for position, label in enumerate(_RESIDUAL_LABELS)}
    representatives = {
        min(
            tuple(sorted(index[symbol_map[index[label]]] for label in labels))
            for symbol_map in maps
        )
        for labels in combinations_with_replacement(_RESIDUAL_LABELS, mass)
    }
    return len(representatives)


def test_s6_s4_residual_labels_have_exact_nested_geometry() -> None:
    """The 52 labels are four fixed scalars plus vertex and K4-edge bundles."""
    fixed, vertices, edges = _label_geometry()
    assert len(fixed) == _FIXED_COMPONENTS
    assert len(vertices) == _VERTEX_COMPONENTS
    assert len(edges) == _EDGE_COMPONENTS
    assert all(len(item) == _VERTEX_BUNDLE_COUNT for item in vertices)
    assert all(len(item) == _EDGE_BUNDLE_COUNT for item in edges)
    labels = set(fixed)
    labels.update(label for item in vertices for label in item)
    labels.update(label for item in edges for label in item)
    assert labels == set(_RESIDUAL_LABELS)


def test_s6_s4_vertex_bundles_leave_exact_five_stabilizers() -> None:
    """Four sorted six-component bundles induce precisely five Young groups."""
    histogram = _vertex_bundle_histogram()
    observed = {partition for _, partition in histogram}
    assert observed == _SECOND_PARTITIONS
    for partition in observed:
        expected_order = 1
        for size in partition:
            expected_order *= factorial(size)
        assert len(_young_group(partition)) == expected_order


def test_s6_s4_nested_factorization_matches_direct_small_orbits() -> None:
    """The nested factorization agrees with raw S4 residual orbits."""
    for mass in range(_EXHAUSTIVE_MASS + 1):
        observed = _factored_residual_count(mass)
        assert observed == _direct_residual_orbit_count(mass)


def test_s6_s4_nested_factorization_matches_burnside_through_fourteen() -> None:
    """Five second-layer stabilizers reconstruct the residual S4 quotient."""
    for mass in range(_MAXIMUM_MASS + 1):
        assert _factored_residual_count(mass) == _full_residual_count(mass)
    observed = _factored_residual_count(_MAXIMUM_MASS)
    assert observed == _WIDTH_FOURTEEN_RESIDUAL_COUNT
    assert _stratum_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_STRATUM_COUNT
