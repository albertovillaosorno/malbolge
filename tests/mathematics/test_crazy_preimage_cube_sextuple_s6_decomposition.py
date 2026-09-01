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
#   - Structural factorization of endpoint-unordered S6 sextuple joint counts.
# - Must-Not:
#   - Claim dense S6 rank/unrank or a wall-clock search improvement.
# - Allows:
#   - Inputs: joint-count mass 0 through 14 under full S6 endpoint permutation.
#   - Outputs: exact vertex-pair/Young-stabilizer residual quotient counts.
#   - Side effects: none.
# - Split-When:
#   - A residual Young-stabilizer quotient receives a constructive rank.
# - Merge-When:
#   - Complete dense S6 ranking owns the same structural decomposition.
# - Summary:
#   - Sort six weight-1/5 pairs, then quotient 52 labels by their stabilizer.
# - Description:
#   - Eleven vertex multiplicity partitions reproduce full S6 Burnside counts.
# - Usage:
#   - Canonical-form prerequisite for future dense endpoint-unordered sextuples.
# - Defaults:
#   - Direct orbit exhaustion stops at mass two; arithmetic reaches mass 14.
#

"""Vertex-pair/Young-stabilizer decomposition of the S6 sextuple quotient."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import combinations_with_replacement
from itertools import permutations
from itertools import product
from math import factorial

_ARITY = 6
_PATTERN_COUNT = 1 << _ARITY
_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 2
_S6_ORDER = factorial(_ARITY)
_WIDTH_FOURTEEN_COUNT = 1_179_940_653_635
_FIXED_LABEL_COUNT = 2
_VERTEX_LABEL_COUNT = 12
_EDGE_LABEL_COUNT = 30
_MIDDLE_LABEL_COUNT = 20
_RESIDUAL_LABEL_COUNT = 52
_VERTEX_PAIR_COUNT = 6
_EDGE_PAIR_COUNT = 15
_MIDDLE_PAIR_COUNT = 10
_VERTEX_SEQUENCE_COUNT = 37_600
_EDGE_WEIGHT = 2
_MIDDLE_WEIGHT = _ARITY // 2
_EXPECTED_PARTITIONS = {
    (6,),
    (5, 1),
    (4, 2),
    (4, 1, 1),
    (3, 3),
    (3, 2, 1),
    (3, 1, 1, 1),
    (2, 2, 2),
    (2, 2, 1, 1),
    (2, 1, 1, 1, 1),
    (1, 1, 1, 1, 1, 1),
}

type _Pair = tuple[int, int]
type _Partition = tuple[int, ...]
type _Permutation = tuple[int, int, int, int, int, int]


def _as_permutation(order: tuple[int, ...]) -> _Permutation:
    assert len(order) == _ARITY
    first, second, third, fourth, fifth, sixth = order
    return first, second, third, fourth, fifth, sixth


_S6: tuple[_Permutation, ...] = tuple(
    _as_permutation(order) for order in permutations(range(_ARITY))
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


def _label_cycles(
    order: _Permutation,
    labels: tuple[int, ...],
) -> tuple[int, ...]:
    allowed = set(labels)
    unseen = set(labels)
    lengths: list[int] = []
    while unseen:
        current = min(unseen)
        orbit: set[int] = set()
        while current not in orbit:
            orbit.add(current)
            current = _permuted_symbol(current, order)
            assert current in allowed
        unseen -= orbit
        lengths.append(len(orbit))
    return tuple(sorted(lengths))


_ALL_LABELS = tuple(range(_PATTERN_COUNT))
_VERTEX_LABELS = tuple(
    symbol for symbol in _ALL_LABELS if symbol.bit_count() in {1, 5}
)
_RESIDUAL_LABELS = tuple(
    symbol for symbol in _ALL_LABELS if symbol.bit_count() not in {1, 5}
)
_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)


@cache
def _full_class_count(mass: int) -> int:
    fixed = sum(
        _fixed_count_from_cycles(_label_cycles(order, _ALL_LABELS), mass)
        for order in _S6
    )
    assert fixed % _S6_ORDER == 0
    return fixed // _S6_ORDER


def _partition_blocks(partition: _Partition) -> tuple[tuple[int, ...], ...]:
    result: list[tuple[int, ...]] = []
    start = 0
    for size in partition:
        result.append(tuple(range(start, start + size)))
        start += size
    assert start == _ARITY
    return tuple(result)


@cache
def _young_group(partition: _Partition) -> tuple[_Permutation, ...]:
    blocks = _partition_blocks(partition)
    choices = tuple(tuple(permutations(block)) for block in blocks)
    result: list[_Permutation] = []
    for block_orders in product(*choices):
        order = list(range(_ARITY))
        for block, block_order in zip(blocks, block_orders, strict=True):
            for source, destination in zip(block, block_order, strict=True):
                order[source] = destination
        result.append(_as_permutation(tuple(order)))
    return tuple(result)


@cache
def _residual_class_count(partition: _Partition, mass: int) -> int:
    group = _young_group(partition)
    fixed = sum(
        _fixed_count_from_cycles(_label_cycles(order, _RESIDUAL_LABELS), mass)
        for order in group
    )
    assert fixed % len(group) == 0
    return fixed // len(group)


@cache
def _vertex_sequences_from(
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
            for suffix in _vertex_sequences_from(
                index,
                slots - 1,
                remaining - pair_mass,
            )
        )
    return tuple(result)


@cache
def _vertex_histogram() -> Counter[tuple[int, _Partition]]:
    result: Counter[tuple[int, _Partition]] = Counter()
    for values in _vertex_sequences_from(0, _ARITY, _MAXIMUM_MASS):
        mass = sum(first + second for first, second in values)
        multiplicities = Counter(values)
        partition = tuple(sorted(multiplicities.values(), reverse=True))
        result[mass, partition] += 1
    return result


def _decomposed_count(mass: int) -> int:
    histogram = _vertex_histogram()
    return sum(
        histogram[vertex_mass, partition]
        * _residual_class_count(partition, mass - vertex_mass)
        for vertex_mass in range(mass + 1)
        for partition in _EXPECTED_PARTITIONS
    )


def _symbol_maps() -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(_permuted_symbol(symbol, order) for symbol in _ALL_LABELS)
        for order in _S6
    )


def _direct_orbit_count(mass: int) -> int:
    maps = _symbol_maps()
    representatives = {
        min(
            tuple(sorted(symbol_map[label] for label in labels))
            for symbol_map in maps
        )
        for labels in combinations_with_replacement(_ALL_LABELS, mass)
    }
    return len(representatives)


def test_s6_layers_have_exact_complement_pair_geometry() -> None:
    """The 64 labels split into four exact Hamming-weight layers."""
    fixed = tuple(
        symbol for symbol in _ALL_LABELS if symbol.bit_count() in {0, _ARITY}
    )
    edges = tuple(
        symbol
        for symbol in _ALL_LABELS
        if symbol.bit_count() in {_EDGE_WEIGHT, _ARITY - _EDGE_WEIGHT}
    )
    middle = tuple(
        symbol for symbol in _ALL_LABELS if symbol.bit_count() == _MIDDLE_WEIGHT
    )
    assert len(fixed) == _FIXED_LABEL_COUNT
    assert len(_VERTEX_LABELS) == _VERTEX_LABEL_COUNT
    assert len(edges) == _EDGE_LABEL_COUNT
    assert len(middle) == _MIDDLE_LABEL_COUNT
    assert len(_RESIDUAL_LABELS) == _RESIDUAL_LABEL_COUNT
    assert _VERTEX_LABEL_COUNT // _FIXED_LABEL_COUNT == _VERTEX_PAIR_COUNT
    assert _EDGE_LABEL_COUNT // _FIXED_LABEL_COUNT == _EDGE_PAIR_COUNT
    assert _MIDDLE_LABEL_COUNT // _FIXED_LABEL_COUNT == _MIDDLE_PAIR_COUNT


def test_s6_vertex_sequences_induce_all_eleven_young_stabilizers() -> None:
    """Sorted vertex pair-values produce exactly the partitions of six."""
    histogram = _vertex_histogram()
    observed = {partition for _, partition in histogram}
    assert observed == _EXPECTED_PARTITIONS
    assert sum(histogram.values()) == _VERTEX_SEQUENCE_COUNT
    for partition in observed:
        expected_order = 1
        for size in partition:
            expected_order *= factorial(size)
        assert len(_young_group(partition)) == expected_order


def test_s6_decomposition_matches_direct_small_orbits() -> None:
    """The factorization agrees with direct S6 orbits through mass two."""
    for mass in range(_EXHAUSTIVE_MASS + 1):
        assert _decomposed_count(mass) == _direct_orbit_count(mass)


def test_s6_decomposition_matches_full_burnside_through_mass_fourteen() -> None:
    """Eleven residual Young quotients reconstruct full S6 exactly."""
    for mass in range(_MAXIMUM_MASS + 1):
        assert _decomposed_count(mass) == _full_class_count(mass)
    assert _decomposed_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
