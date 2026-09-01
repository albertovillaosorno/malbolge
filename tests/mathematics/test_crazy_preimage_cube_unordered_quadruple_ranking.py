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
#   - Independent dense ranking evidence for endpoint-unordered S4 joint-count
#     classes.
# - Must-Not:
#   - Apply endpoint symmetry to direction-sensitive quadruple analyses or infer
#     a dense rank for larger endpoint groups.
# - Allows:
#   - Inputs: quadruple joint-count classes at ambiguity dimensions zero through
#     fourteen.
#   - Outputs: exact dense rank/unrank under the full S4 endpoint action.
#   - Side effects: none.
# - Split-When:
#   - A larger endpoint group needs a distinct orbit-ranking construction.
# - Merge-When:
#   - The unordered-quadruple theorem owns the same constructive quotient index.
# - Summary:
#   - Densely index S4 classes via vertex-pair and weighted-edge canonical data.
# - Description:
#   - Sorts four complementary vertex-count pairs, then quotients six edge
#     counts by the residual equal-vertex stabilizer.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Dense arithmetic reaches dimension fourteen; exhaustive states stop at 7.
#

"""Dense rank/unrank evidence for S4 endpoint-unordered quadruple classes."""

from __future__ import annotations

from functools import cache
from itertools import combinations
from itertools import permutations
from itertools import product
from math import comb

_EXHAUSTIVE_COUNT_DIMENSION = 4
_EXHAUSTIVE_RANK_DIMENSION = 6
_EXHAUSTIVE_RAW_DIMENSION = 3
_MAXIMUM_TRITS = 14
_PATTERN_COUNT = 16
_QUADRUPLE_ARITY = 4
_EDGE_COUNT = 6
_ENDPOINT_PERMUTATIONS = tuple(permutations(range(_QUADRUPLE_ARITY)))
_SINGLETON_LABELS = (8, 4, 2, 1)
_EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_WIDTH_FOURTEEN_CLASS_COUNT = 3_419_552

type _Pair = tuple[int, int]
type _VertexPairs = tuple[_Pair, _Pair, _Pair, _Pair]
type _Edges = tuple[int, int, int, int, int, int]
type _State = tuple[int, int, _VertexPairs, _Edges]


def _permuted_symbol(symbol: int, endpoint_order: tuple[int, ...]) -> int:
    result = 0
    for source in endpoint_order:
        result = (
            result << 1
        ) | ((symbol >> (_QUADRUPLE_ARITY - source - 1)) & 1)
    return result


def _permute_counts(
    counts: tuple[int, ...],
    endpoint_order: tuple[int, ...],
) -> tuple[int, ...]:
    result = [0] * _PATTERN_COUNT
    for symbol, count in enumerate(counts):
        result[_permuted_symbol(symbol, endpoint_order)] = count
    return tuple(result)


def _raw_state(counts: tuple[int, ...]) -> _State | None:
    if len(counts) != _PATTERN_COUNT or min(counts, default=-1) < 0:
        return None
    vertex_pairs = tuple(
        (counts[singleton], counts[(_PATTERN_COUNT - 1) ^ singleton])
        for singleton in _SINGLETON_LABELS
    )
    edge_counts = tuple(
        counts[(1 << (3 - left)) | (1 << (3 - right))]
        for left, right in _EDGES
    )
    assert len(vertex_pairs) == _QUADRUPLE_ARITY
    assert len(edge_counts) == _EDGE_COUNT
    return (
        counts[0],
        counts[_PATTERN_COUNT - 1],
        (vertex_pairs[0], vertex_pairs[1], vertex_pairs[2], vertex_pairs[3]),
        (
            edge_counts[0], edge_counts[1], edge_counts[2],
            edge_counts[3], edge_counts[4], edge_counts[5],
        ),
    )


def _canonical_state(counts: tuple[int, ...]) -> _State | None:
    if _raw_state(counts) is None:
        return None
    states = tuple(
        _raw_state(_permute_counts(counts, endpoint_order))
        for endpoint_order in _ENDPOINT_PERMUTATIONS
    )
    assert all(state is not None for state in states)
    return min(state for state in states if state is not None)


def _counts_from_state(state: _State) -> tuple[int, ...]:
    fixed_zero, fixed_one, vertex_pairs, edge_counts = state
    result = [0] * _PATTERN_COUNT
    result[0] = fixed_zero
    result[_PATTERN_COUNT - 1] = fixed_one
    for singleton, pair in zip(_SINGLETON_LABELS, vertex_pairs, strict=True):
        result[singleton] = pair[0]
        result[(_PATTERN_COUNT - 1) ^ singleton] = pair[1]
    for edge, count in zip(_EDGES, edge_counts, strict=True):
        left, right = edge
        result[(1 << (3 - left)) | (1 << (3 - right))] = count
    return tuple(result)


def _state_dimension(state: _State) -> int:
    return sum(_counts_from_state(state))


def _vertex_mass(vertex_pairs: _VertexPairs) -> int:
    return sum(left + right for left, right in vertex_pairs)


def _block_sizes(vertex_pairs: _VertexPairs) -> tuple[int, ...]:
    result: list[int] = []
    start = 0
    while start < _QUADRUPLE_ARITY:
        end = start + 1
        while (
            end < _QUADRUPLE_ARITY
            and vertex_pairs[end] == vertex_pairs[start]
        ):
            end += 1
        result.append(end - start)
        start = end
    return tuple(result)


@cache
def _stabilizer_orders(
    block_sizes: tuple[int, ...],
) -> tuple[tuple[int, ...], ...]:
    blocks: list[tuple[int, ...]] = []
    start = 0
    for size in block_sizes:
        blocks.append(tuple(range(start, start + size)))
        start += size
    assert start == _QUADRUPLE_ARITY
    result: list[tuple[int, ...]] = []
    for local_orders in product(*(permutations(block) for block in blocks)):
        order = list(range(_QUADRUPLE_ARITY))
        for block, image in zip(blocks, local_orders, strict=True):
            for destination, source in zip(block, image, strict=True):
                order[destination] = source
        result.append(tuple(order))
    return tuple(result)


def _permute_edges(
    edge_counts: _Edges,
    endpoint_order: tuple[int, ...],
) -> _Edges:
    result: list[int] = []
    for destination_left, destination_right in _EDGES:
        left = endpoint_order[destination_left]
        right = endpoint_order[destination_right]
        source = (left, right) if left < right else (right, left)
        result.append(edge_counts[_EDGE_INDEX[source]])
    assert len(result) == _EDGE_COUNT
    return (result[0], result[1], result[2], result[3], result[4], result[5])


def _canonical_edges(
    edge_counts: _Edges,
    block_sizes: tuple[int, ...],
) -> _Edges:
    return min(
        _permute_edges(edge_counts, endpoint_order)
        for endpoint_order in _stabilizer_orders(block_sizes)
    )


def _weak_compositions(total: int, parts: int) -> tuple[tuple[int, ...], ...]:
    if parts == 1:
        return ((total,),)
    result: list[tuple[int, ...]] = []
    for first in range(total + 1):
        result.extend(
            (first, *rest)
            for rest in _weak_compositions(total - first, parts - 1)
        )
    return tuple(result)


@cache
def _edge_representatives(
    block_sizes: tuple[int, ...],
    total: int,
) -> tuple[_Edges, ...]:
    representatives: set[_Edges] = set()
    for composition in _weak_compositions(total, _EDGE_COUNT):
        assert len(composition) == _EDGE_COUNT
        edge_counts = (
            composition[0], composition[1], composition[2],
            composition[3], composition[4], composition[5],
        )
        representatives.add(_canonical_edges(edge_counts, block_sizes))
    return tuple(sorted(representatives))


def _pair_values(maximum_mass: int) -> tuple[_Pair, ...]:
    return tuple(
        (left, right)
        for left in range(maximum_mass + 1)
        for right in range(maximum_mass - left + 1)
    )


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
        pair_mass = pair[0] + pair[1]
        result.extend(
            (pair, *rest)
            for rest in _vertex_sequences_from(
                maximum_mass - pair_mass,
                slots - 1,
                pair,
            )
        )
    return tuple(result)


@cache
def _vertex_sequences(maximum_mass: int) -> tuple[_VertexPairs, ...]:
    return tuple(
        sequence
        for sequence in _vertex_sequences_from(
            maximum_mass,
            _QUADRUPLE_ARITY,
            (0, 0),
        )
        if len(sequence) == _QUADRUPLE_ARITY
    )


def _vertex_edge_block_size(
    available_mass: int,
    vertex_pairs: _VertexPairs,
) -> int:
    edge_mass = available_mass - _vertex_mass(vertex_pairs)
    if edge_mass < 0:
        return 0
    return len(_edge_representatives(_block_sizes(vertex_pairs), edge_mass))


@cache
def _vertex_edge_count(available_mass: int) -> int:
    return sum(
        _vertex_edge_block_size(available_mass, vertex_pairs)
        for vertex_pairs in _vertex_sequences(available_mass)
    )


@cache
def _suffix_count(available_mass: int) -> int:
    return sum(
        _vertex_edge_count(available_mass - fixed_one)
        for fixed_one in range(available_mass + 1)
    )


@cache
def _class_count(dimension: int) -> int:
    return sum(
        _suffix_count(dimension - fixed_zero)
        for fixed_zero in range(dimension + 1)
    )


def _fixed_prefix(dimension: int, fixed_zero: int) -> int:
    return sum(
        _suffix_count(dimension - earlier)
        for earlier in range(fixed_zero)
    )


def _fixed_one_prefix(
    remaining_mass: int,
    fixed_one: int,
) -> int:
    return sum(
        _vertex_edge_count(remaining_mass - earlier)
        for earlier in range(fixed_one)
    )


def _vertex_prefix(
    available_mass: int,
    vertex_pairs: _VertexPairs,
) -> int | None:
    prefix = 0
    for candidate in _vertex_sequences(available_mass):
        if candidate == vertex_pairs:
            return prefix
        if candidate > vertex_pairs:
            return None
        prefix += _vertex_edge_block_size(available_mass, candidate)
    return None


def _edge_rank(
    vertex_pairs: _VertexPairs,
    available_mass: int,
    edge_counts: _Edges,
) -> int | None:
    edge_mass = available_mass - _vertex_mass(vertex_pairs)
    representatives = _edge_representatives(
        _block_sizes(vertex_pairs),
        edge_mass,
    )
    return (
        representatives.index(edge_counts)
        if edge_counts in representatives
        else None
    )


def _rank_canonical_state(state: _State) -> int | None:
    fixed_zero, fixed_one, vertex_pairs, edge_counts = state
    dimension = _state_dimension(state)
    remaining_mass = dimension - fixed_zero
    available_mass = remaining_mass - fixed_one
    vertex_prefix = _vertex_prefix(available_mass, vertex_pairs)
    edge_rank = _edge_rank(vertex_pairs, available_mass, edge_counts)
    if vertex_prefix is None or edge_rank is None:
        return None
    return (
        _fixed_prefix(dimension, fixed_zero)
        + _fixed_one_prefix(remaining_mass, fixed_one)
        + vertex_prefix
        + edge_rank
    )


def _dense_rank(counts: tuple[int, ...]) -> int | None:
    state = _canonical_state(counts)
    return None if state is None else _rank_canonical_state(state)


def _choose_fixed_zero(dimension: int, rank: int) -> tuple[int, int]:
    remaining = rank
    for fixed_zero in range(dimension + 1):
        block = _suffix_count(dimension - fixed_zero)
        if remaining >= block:
            remaining -= block
            continue
        return fixed_zero, remaining
    raise AssertionError


def _choose_fixed_one(available_mass: int, rank: int) -> tuple[int, int]:
    remaining = rank
    for fixed_one in range(available_mass + 1):
        block = _vertex_edge_count(available_mass - fixed_one)
        if remaining >= block:
            remaining -= block
            continue
        return fixed_one, remaining
    raise AssertionError


def _choose_vertex_pairs(
    available_mass: int,
    rank: int,
) -> tuple[_VertexPairs, int]:
    remaining = rank
    for vertex_pairs in _vertex_sequences(available_mass):
        block = _vertex_edge_block_size(available_mass, vertex_pairs)
        if remaining >= block:
            remaining -= block
            continue
        return vertex_pairs, remaining
    raise AssertionError


def _dense_unrank(dimension: int, rank: int) -> tuple[int, ...] | None:
    if rank < 0 or rank >= _class_count(dimension):
        return None
    fixed_zero, remaining = _choose_fixed_zero(dimension, rank)
    fixed_one, remaining = _choose_fixed_one(
        dimension - fixed_zero,
        remaining,
    )
    available_mass = dimension - fixed_zero - fixed_one
    vertex_pairs, edge_rank = _choose_vertex_pairs(available_mass, remaining)
    edge_mass = available_mass - _vertex_mass(vertex_pairs)
    edge_counts = _edge_representatives(
        _block_sizes(vertex_pairs),
        edge_mass,
    )[edge_rank]
    state = fixed_zero, fixed_one, vertex_pairs, edge_counts
    counts = _counts_from_state(state)
    assert _canonical_state(counts) == state
    return counts


def _fixed_count_from_cycles(cycles: tuple[int, ...], dimension: int) -> int:
    coefficients = [1] + [0] * dimension
    for cycle_length in cycles:
        next_coefficients = [0] * (dimension + 1)
        for total, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, dimension - total + 1, cycle_length):
                next_coefficients[total + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[dimension]


def _burnside_count(dimension: int) -> int:
    identity = comb(dimension + 15, 15)
    transposition = _fixed_count_from_cycles((1,) * 8 + (2,) * 4, dimension)
    double_transposition = _fixed_count_from_cycles(
        (1,) * 4 + (2,) * 6,
        dimension,
    )
    three_cycle = _fixed_count_from_cycles((1,) * 4 + (3,) * 4, dimension)
    four_cycle = _fixed_count_from_cycles(
        (1,) * 2 + (2,) + (4,) * 3,
        dimension,
    )
    return (
        identity
        + 6 * transposition
        + 3 * double_transposition
        + 8 * three_cycle
        + 6 * four_cycle
    ) // 24


def _count_vectors(dimension: int) -> tuple[tuple[int, ...], ...]:
    vectors: list[tuple[int, ...]] = []
    for bars in combinations(range(dimension + 15), 15):
        positions = (-1, *bars, dimension + 15)
        vectors.append(tuple(
            positions[index + 1] - positions[index] - 1
            for index in range(_PATTERN_COUNT)
        ))
    return tuple(vectors)


def _joint_counts(
    quadruple: tuple[int, int, int, int],
    dimension: int,
) -> tuple[int, ...]:
    counts = [0] * _PATTERN_COUNT
    for coordinate in range(dimension):
        symbol = 0
        for code in quadruple:
            symbol = (symbol << 1) | ((code >> coordinate) & 1)
        counts[symbol] += 1
    return tuple(counts)


def test_weighted_k4_state_is_complete_s4_orbit_invariant() -> None:
    """Small count vectors collide exactly on one weighted-K4 S4 orbit."""
    for dimension in range(_EXHAUSTIVE_COUNT_DIMENSION + 1):
        observed: dict[_State, set[tuple[int, ...]]] = {}
        for counts in _count_vectors(dimension):
            state = _canonical_state(counts)
            assert state is not None
            orbit = {
                _permute_counts(counts, endpoint_order)
                for endpoint_order in _ENDPOINT_PERMUTATIONS
            }
            if state not in observed:
                observed[state] = orbit
            assert observed[state] == orbit
        assert len(observed) == _burnside_count(dimension)


def test_dense_s4_class_count_matches_burnside_through_dimension_fourteen(
) -> None:
    """The constructive weighted-K4 blocks reproduce every checked S4 count."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        assert _class_count(dimension) == _burnside_count(dimension)
    assert _class_count(_MAXIMUM_TRITS) == _WIDTH_FOURTEEN_CLASS_COUNT


def test_dense_s4_rank_exhausts_small_checked_domains() -> None:
    """Every S4 class through dimension seven receives one contiguous rank."""
    for dimension in range(_EXHAUSTIVE_RANK_DIMENSION + 1):
        count = _class_count(dimension)
        for rank in range(count):
            counts = _dense_unrank(dimension, rank)
            assert counts is not None
            assert sum(counts) == dimension
            assert _dense_rank(counts) == rank


def test_dense_s4_rank_roundtrips_checked_boundaries() -> None:
    """Boundary and interior ranks roundtrip through every checked dimension."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        count = _class_count(dimension)
        assert _dense_unrank(dimension, -1) is None
        assert _dense_unrank(dimension, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            counts = _dense_unrank(dimension, rank)
            assert counts is not None
            assert _dense_rank(counts) == rank


def test_dense_s4_rank_is_endpoint_invariant_on_small_raw_quadruples() -> None:
    """Raw quadruples and endpoint permutations receive the same dense rank."""
    for dimension in range(_EXHAUSTIVE_RAW_DIMENSION + 1):
        size = 1 << dimension
        for raw in product(range(size), repeat=_QUADRUPLE_ARITY):
            quadruple = raw[0], raw[1], raw[2], raw[3]
            counts = _joint_counts(quadruple, dimension)
            rank = _dense_rank(counts)
            assert rank is not None
            for endpoint_order in _ENDPOINT_PERMUTATIONS:
                permuted = (
                    quadruple[endpoint_order[0]],
                    quadruple[endpoint_order[1]],
                    quadruple[endpoint_order[2]],
                    quadruple[endpoint_order[3]],
                )
                assert _dense_rank(_joint_counts(permuted, dimension)) == rank
