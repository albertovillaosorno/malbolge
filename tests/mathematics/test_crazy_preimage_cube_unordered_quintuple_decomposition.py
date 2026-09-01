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
#   - Independent structural evidence for decomposing endpoint-unordered S5
#     joint-count classes into fixed, vertex-pair, and edge-pair data.
# - Must-Not:
#   - Claim a dense S5 rank or apply endpoint symmetry to direction-sensitive
#     quintuple analyses.
# - Allows:
#   - Inputs: ambiguity dimensions zero through fourteen.
#   - Outputs: exact S5 class counts via vertex stabilizers and K5 edge orbits.
#   - Side effects: none.
# - Split-When:
#   - Dense S5 orbit ranking requires its own prefix-count construction.
# - Merge-When:
#   - The unordered-quintuple theorem owns the same structural factorization.
# - Summary:
#   - Factor S5 classes through sorted vertex pairs and residual K5 edge pairs.
# - Description:
#   - Burnside-counts edge-pair assignments under equal-vertex stabilizers.
# - Usage:
#   - Prerequisite evidence for a future constructive dense S5 index.
# - Defaults:
#   - Exact arithmetic reaches dimension fourteen; small edge states are direct.
#

"""Structural S5 quotient decomposition into complementary count pairs."""

from __future__ import annotations

from functools import cache
from itertools import permutations
from itertools import product
from math import factorial

_ARITY = 5
_EDGE_COUNT = 10
_PAIR_ARITY = 2
_EXHAUSTIVE_EDGE_MASS = 3
_MAXIMUM_TRITS = 14
_PATTERN_COUNT = 1 << _ARITY
_S5_ORDER = factorial(_ARITY)
_WIDTH_FOURTEEN_CLASS_COUNT = 1_426_354_541
_EDGES = tuple(
    (left, right)
    for left in range(_ARITY)
    for right in range(left + 1, _ARITY)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_ENDPOINT_PERMUTATIONS = tuple(permutations(range(_ARITY)))

type _Pair = tuple[int, int]
type _EdgePairs = tuple[_Pair, ...]


def _permuted_symbol(symbol: int, endpoint_order: tuple[int, ...]) -> int:
    result = 0
    for source in endpoint_order:
        result = (result << 1) | ((symbol >> (_ARITY - source - 1)) & 1)
    return result


def _label_cycles(endpoint_order: tuple[int, ...]) -> tuple[int, ...]:
    unseen = set(range(_PATTERN_COUNT))
    lengths: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = _permuted_symbol(current, endpoint_order)
            length += 1
        lengths.append(length)
    return tuple(sorted(lengths))


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
def _full_s5_burnside_count(total: int) -> int:
    numerator = sum(
        _fixed_count(_label_cycles(endpoint_order), total)
        for endpoint_order in _ENDPOINT_PERMUTATIONS
    )
    assert numerator % _S5_ORDER == 0
    return numerator // _S5_ORDER


def _block_sizes(vertex_pairs: tuple[_Pair, ...]) -> tuple[int, ...]:
    sizes: list[int] = []
    start = 0
    while start < len(vertex_pairs):
        end = start + 1
        while (
            end < len(vertex_pairs)
            and vertex_pairs[end] == vertex_pairs[start]
        ):
            end += 1
        sizes.append(end - start)
        start = end
    return tuple(sizes)


@cache
def _stabilizer_orders(
    block_sizes: tuple[int, ...],
) -> tuple[tuple[int, ...], ...]:
    blocks: list[tuple[int, ...]] = []
    start = 0
    for size in block_sizes:
        blocks.append(tuple(range(start, start + size)))
        start += size
    assert start == _ARITY
    orders: list[tuple[int, ...]] = []
    for local_orders in product(*(permutations(block) for block in blocks)):
        order = list(range(_ARITY))
        for block, image in zip(blocks, local_orders, strict=True):
            for destination, source in zip(block, image, strict=True):
                order[destination] = source
        orders.append(tuple(order))
    return tuple(orders)


def _edge_cycles(endpoint_order: tuple[int, ...]) -> tuple[int, ...]:
    edge_permutation: list[int] = []
    for left, right in _EDGES:
        source_left = endpoint_order[left]
        source_right = endpoint_order[right]
        source = (
            (source_left, source_right)
            if source_left < source_right
            else (source_right, source_left)
        )
        assert len(source) == _PAIR_ARITY
        edge_permutation.append(_EDGE_INDEX[source])
    unseen = set(range(_EDGE_COUNT))
    lengths: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = edge_permutation[current]
            length += 1
        lengths.append(length)
    return tuple(sorted(lengths))


def _fixed_edge_pair_count(cycles: tuple[int, ...], total: int) -> int:
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


@cache
def _edge_pair_orbit_count(block_sizes: tuple[int, ...], total: int) -> int:
    stabilizer = _stabilizer_orders(block_sizes)
    numerator = sum(
        _fixed_edge_pair_count(_edge_cycles(endpoint_order), total)
        for endpoint_order in stabilizer
    )
    assert numerator % len(stabilizer) == 0
    return numerator // len(stabilizer)


def _pair_values(maximum_mass: int) -> tuple[_Pair, ...]:
    return tuple(
        (left, right)
        for left in range(maximum_mass + 1)
        for right in range(maximum_mass - left + 1)
    )


@cache
def _vertex_sequences_from(
    maximum_mass: int,
    slots: int,
    minimum: _Pair,
) -> tuple[tuple[_Pair, ...], ...]:
    if slots == 0:
        return ((),)
    result: list[tuple[_Pair, ...]] = []
    for pair in _pair_values(maximum_mass):
        if pair < minimum:
            continue
        mass = pair[0] + pair[1]
        result.extend(
            (pair, *rest)
            for rest in _vertex_sequences_from(
                maximum_mass - mass,
                slots - 1,
                pair,
            )
        )
    return tuple(result)


@cache
def _vertex_sequences(maximum_mass: int) -> tuple[tuple[_Pair, ...], ...]:
    return _vertex_sequences_from(maximum_mass, _ARITY, (0, 0))


@cache
def _middle_layer_count(total: int) -> int:
    return sum(
        _edge_pair_orbit_count(
            _block_sizes(vertex_pairs),
            total - sum(left + right for left, right in vertex_pairs),
        )
        for vertex_pairs in _vertex_sequences(total)
    )


@cache
def _decomposed_class_count(total: int) -> int:
    return sum(
        _middle_layer_count(total - fixed_zero - fixed_one)
        for fixed_zero in range(total + 1)
        for fixed_one in range(total - fixed_zero + 1)
    )


def _visit_edge_pair_assignments(
    index: int,
    remaining: int,
    prefix: list[_Pair],
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
            _visit_edge_pair_assignments(
                index + 1,
                remaining - left - right,
                prefix,
                result=result,
            )
            _ = prefix.pop()


def _edge_pair_assignments(total: int) -> tuple[_EdgePairs, ...]:
    result: list[_EdgePairs] = []
    _visit_edge_pair_assignments(0, total, [], result=result)
    return tuple(result)


def _permute_edge_pairs(
    edge_pairs: _EdgePairs,
    endpoint_order: tuple[int, ...],
) -> _EdgePairs:
    result: list[_Pair] = []
    for left, right in _EDGES:
        source_left = endpoint_order[left]
        source_right = endpoint_order[right]
        source = (
            (source_left, source_right)
            if source_left < source_right
            else (source_right, source_left)
        )
        result.append(edge_pairs[_EDGE_INDEX[source]])
    return tuple(result)


def test_s5_hamming_layers_map_as_vertex_and_edge_complement_pairs() -> None:
    """All endpoint permutations preserve the fixed, vertex, and edge layers."""
    singleton_symbols = tuple(
        1 << (_ARITY - vertex - 1)
        for vertex in range(_ARITY)
    )
    edge_symbols = tuple(
        (1 << (_ARITY - left - 1)) | (1 << (_ARITY - right - 1))
        for left, right in _EDGES
    )
    for endpoint_order in _ENDPOINT_PERMUTATIONS:
        assert _permuted_symbol(0, endpoint_order) == 0
        assert (
            _permuted_symbol(_PATTERN_COUNT - 1, endpoint_order)
            == _PATTERN_COUNT - 1
        )
        assert {
            _permuted_symbol(symbol, endpoint_order)
            for symbol in singleton_symbols
        } == set(singleton_symbols)
        assert {
            _permuted_symbol(symbol, endpoint_order) for symbol in edge_symbols
        } == set(edge_symbols)


def test_s5_edge_pair_burnside_matches_small_direct_orbits() -> None:
    """Residual Burnside counts match direct small edge-pair orbits."""
    block_shapes = (
        (1, 1, 1, 1, 1),
        (1, 1, 1, 2),
        (1, 2, 2),
        (1, 1, 3),
        (2, 3),
        (1, 4),
        (5,),
    )
    for block_sizes in block_shapes:
        stabilizer = _stabilizer_orders(block_sizes)
        for total in range(_EXHAUSTIVE_EDGE_MASS + 1):
            representatives = {
                min(
                    _permute_edge_pairs(edge_pairs, endpoint_order)
                    for endpoint_order in stabilizer
                )
                for edge_pairs in _edge_pair_assignments(total)
            }
            assert len(representatives) == _edge_pair_orbit_count(
                block_sizes,
                total,
            )


def test_s5_vertex_edge_decomposition_matches_burnside() -> None:
    """The decomposition reproduces every checked S5 quotient count."""
    for total in range(_MAXIMUM_TRITS + 1):
        assert _decomposed_class_count(total) == _full_s5_burnside_count(total)
    assert (
        _decomposed_class_count(_MAXIMUM_TRITS)
        == _WIDTH_FOURTEEN_CLASS_COUNT
    )
