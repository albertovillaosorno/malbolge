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
#   - Dense rank/unrank for the second-layer S3 slice of the (4,1,1) S6 stratum.
# - Must-Not:
#   - Claim ranking for V4 or full-S4 second-layer stabilizers.
# - Allows:
#   - Inputs: sextuple mass zero through fourteen with bundle partition (3,1).
#   - Outputs: dense ranks over one repeated bundle and an S3 edge multiset.
#   - Side effects: none.
# - Split-When:
#   - Another second-layer S4 stabilizer receives constructive rank/unrank.
# - Merge-When:
#   - Complete dense ranking owns the full (4,1,1) S6 stratum.
# - Summary:
#   - Rank triple/singleton bundles and three eight-scalar K4-edge bundles.
# - Description:
#   - The three repeated endpoints permute one weighted multiset of edge blocks.
# - Usage:
#   - Constructive order-six second-layer slice of the nested S4 S6 stratum.
# - Defaults:
#   - Direct abstract S4 orbits stop at mass two; full exhaustion stops at six.
#

"""Dense S3 second-layer ranking for the S6 (4,1,1) stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import permutations
from math import comb

_ARITY = 6
_ACTIVE_COUNT = 4
_ACTIVE = tuple(range(_ACTIVE_COUNT))
_REPEAT_COUNT = 3
_SINGLE_COUNT = 1
_FIXED_COMPONENTS = 4
_VERTEX_COMPONENTS = 6
_EDGE_COMPONENTS = 4
_EDGE_COUNT = 6
_BLOCK_COMPONENTS = 2 * _EDGE_COMPONENTS
_BLOCK_COUNT = 3
_MAXIMUM_MASS = 14
_EXHAUSTIVE_FULL_MASS = 6
_EXHAUSTIVE_ORBIT_MASS = 2
_TOP_PARTITION = (4, 1, 1)
_SECOND_PARTITION = (3, 1)
_WIDTH_FOURTEEN_COUNT = 17_436_163_856
_EXPECTED_COUNTS = {
    3: 6,
    4: 129,
    5: 1_622,
    6: 15_945,
    7: 132_412,
    8: 958_607,
    9: 6_164_874,
    10: 35_715_856,
    11: 188_567_946,
    12: 916_308_892,
    13: 4_133_308_028,
    14: 17_436_163_856,
}
_K4_EDGES = tuple(
    (left, right)
    for left in _ACTIVE
    for right in _ACTIVE
    if left < right
)
_K4_EDGE_INDEX = {edge: index for index, edge in enumerate(_K4_EDGES)}
_S4 = tuple(permutations(_ACTIVE))
_BUNDLE_EDGES = (
    ((1, 2), (0, 3)),
    ((0, 2), (1, 3)),
    ((0, 1), (2, 3)),
)

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Vector = tuple[int, ...]
type _Bundle = tuple[int, int, int, int, int, int]
type _Bundles = tuple[_Bundle, _Bundle, _Bundle, _Bundle]
type _Edge = tuple[int, int, int, int]
type _Edges = tuple[_Edge, _Edge, _Edge, _Edge, _Edge, _Edge]
type _Block = tuple[int, int, int, int, int, int, int, int]
type _Blocks = tuple[_Block, _Block, _Block]
type _Residual = tuple[_Vector, _Bundles, _Edges]
type _State = tuple[_Vertices, _Residual]

_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)


def _composition_count(total: int, parts: int) -> int:
    if total < 0 or parts <= 0:
        return 0
    return comb(total + parts - 1, parts - 1)


def _composition_rank(vector: _Vector, parts: int) -> int | None:
    if len(vector) != parts or any(value < 0 for value in vector):
        return None
    remaining = sum(vector)
    rank = 0
    for index, value in enumerate(vector[:-1]):
        tail = parts - index - 1
        rank += sum(
            _composition_count(remaining - earlier, tail)
            for earlier in range(value)
        )
        remaining -= value
    return rank


def _composition_unrank(total: int, parts: int, rank: int) -> _Vector | None:
    if rank < 0 or rank >= _composition_count(total, parts):
        return None
    remaining = total
    residual_rank = rank
    result: list[int] = []
    for index in range(parts - 1):
        tail = parts - index - 1
        for value in range(remaining + 1):
            block = _composition_count(remaining - value, tail)
            if residual_rank >= block:
                residual_rank -= block
                continue
            result.append(value)
            remaining -= value
            break
    result.append(remaining)
    return tuple(result)


def _rep_rank(values: tuple[int, ...], population: int) -> int:
    shifted = tuple(value + index for index, value in enumerate(values))
    universe = population + len(values) - 1
    rank = 0
    previous = -1
    for index, value in enumerate(shifted):
        remaining = len(values) - index - 1
        for candidate in range(previous + 1, value):
            rank += comb(universe - candidate - 1, remaining)
        previous = value
    return rank


def _rep_unrank(population: int, size: int, rank: int) -> tuple[int, ...]:
    universe = population + size - 1
    remaining_rank = rank
    previous = -1
    shifted: list[int] = []
    for index in range(size):
        remaining = size - index - 1
        for candidate in range(previous + 1, universe):
            block = comb(universe - candidate - 1, remaining)
            if remaining_rank >= block:
                remaining_rank -= block
                continue
            shifted.append(candidate)
            previous = candidate
            break
    return tuple(value - index for index, value in enumerate(shifted))


def _filtered_rank(value: int, excluded: int) -> int:
    assert value != excluded
    return value if value < excluded else value - 1


def _filtered_unrank(rank: int, excluded: int) -> int:
    return rank if rank < excluded else rank + 1


def _as_bundle(vector: _Vector) -> _Bundle:
    assert len(vector) == _VERTEX_COMPONENTS
    first, second, third, fourth, fifth, sixth = vector
    return first, second, third, fourth, fifth, sixth


def _raw_bundle_count(total: int) -> int:
    return _composition_count(total, _VERTEX_COMPONENTS)


def _bundle_key(bundle: _Bundle) -> tuple[int, int]:
    rank = _composition_rank(bundle, _VERTEX_COMPONENTS)
    assert rank is not None
    return sum(bundle), rank


def _bundle_mass_pairs(total: int) -> tuple[tuple[int, int], ...]:
    return tuple(
        (repeated, total - _REPEAT_COUNT * repeated)
        for repeated in range(total // _REPEAT_COUNT + 1)
    )


def _bundle_block_count(masses: tuple[int, int]) -> int:
    repeated_mass, single_mass = masses
    repeated = _raw_bundle_count(repeated_mass)
    single = _raw_bundle_count(single_mass)
    if repeated_mass == single_mass:
        single -= 1
    return repeated * single


@cache
def _bundle_count(total: int) -> int:
    return sum(
        _bundle_block_count(masses) for masses in _bundle_mass_pairs(total)
    )


def _bundle_rank_data(
    bundles: _Bundles,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    keys = tuple(_bundle_key(bundle) for bundle in bundles)
    multiplicities = Counter(keys)
    partition = tuple(sorted(multiplicities.values(), reverse=True))
    if partition != _SECOND_PARTITION:
        return None
    repeated = next(
        key
        for key, count in multiplicities.items()
        if count == _REPEAT_COUNT
    )
    single = next(
        key
        for key, count in multiplicities.items()
        if count == _SINGLE_COUNT
    )
    return (repeated[0], single[0]), (repeated[1], single[1])


def _bundle_local_rank(
    masses: tuple[int, int],
    ranks: tuple[int, int],
) -> int:
    repeated_rank, single_rank = ranks
    single_count = _raw_bundle_count(masses[1])
    if masses[0] == masses[1]:
        single_rank = _filtered_rank(single_rank, repeated_rank)
        single_count -= 1
    return repeated_rank * single_count + single_rank


def _bundle_local_unrank(
    masses: tuple[int, int],
    rank: int,
) -> tuple[int, int]:
    single_count = _raw_bundle_count(masses[1])
    same_mass = masses[0] == masses[1]
    if same_mass:
        single_count -= 1
    repeated_rank, single_rank = divmod(rank, single_count)
    if same_mass:
        single_rank = _filtered_unrank(single_rank, repeated_rank)
    return repeated_rank, single_rank


def _bundle_rank(bundles: _Bundles) -> int | None:
    data = _bundle_rank_data(bundles)
    if data is None:
        return None
    masses, ranks = data
    total = sum(sum(bundle) for bundle in bundles)
    prefix = sum(
        _bundle_block_count(candidate)
        for candidate in _bundle_mass_pairs(total)
        if candidate < masses
    )
    return prefix + _bundle_local_rank(masses, ranks)


def _bundle_unrank(total: int, rank: int) -> _Bundles | None:
    if rank < 0 or rank >= _bundle_count(total):
        return None
    remaining = rank
    for masses in _bundle_mass_pairs(total):
        block = _bundle_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        repeated_rank, single_rank = _bundle_local_unrank(masses, remaining)
        repeated = _composition_unrank(
            masses[0],
            _VERTEX_COMPONENTS,
            repeated_rank,
        )
        single = _composition_unrank(masses[1], _VERTEX_COMPONENTS, single_rank)
        assert repeated is not None
        assert single is not None
        repeated_bundle = _as_bundle(repeated)
        single_bundle = _as_bundle(single)
        return (
            repeated_bundle,
            repeated_bundle,
            repeated_bundle,
            single_bundle,
        )
    raise AssertionError


def _as_block(vector: _Vector) -> _Block:
    assert len(vector) == _BLOCK_COMPONENTS
    first, second, third, fourth, fifth, sixth, seventh, eighth = vector
    return first, second, third, fourth, fifth, sixth, seventh, eighth


def _block_count(total: int) -> int:
    return _composition_count(total, _BLOCK_COMPONENTS)


def _block_rank(block: _Block) -> int:
    rank = _composition_rank(block, _BLOCK_COMPONENTS)
    assert rank is not None
    return rank


def _block_unrank(total: int, rank: int) -> _Block:
    vector = _composition_unrank(total, _BLOCK_COMPONENTS, rank)
    assert vector is not None
    return _as_block(vector)


def _mass_triples(total: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (first, second, total - first - second)
        for first in range(total + 1)
        for second in range(first, total + 1)
        if second <= total - first - second
    )


def _edge_block_count(masses: tuple[int, int, int]) -> int:
    first = _block_count(masses[0])
    second = _block_count(masses[1])
    third = _block_count(masses[2])
    result = first * second * third
    if masses[0] == masses[2]:
        result = comb(first + 2, _BLOCK_COUNT)
    elif masses[0] == masses[1]:
        result = comb(first + 1, 2) * third
    elif masses[1] == masses[2]:
        result = first * comb(second + 1, 2)
    return result


@cache
def _edge_count(total: int) -> int:
    return sum(_edge_block_count(masses) for masses in _mass_triples(total))


def _edge_local_rank(
    masses: tuple[int, int, int],
    values: tuple[int, int, int],
) -> int:
    first = _block_count(masses[0])
    second = _block_count(masses[1])
    third = _block_count(masses[2])
    result = (values[0] * second + values[1]) * third + values[2]
    if masses[0] == masses[2]:
        result = _rep_rank(values, first)
    elif masses[0] == masses[1]:
        result = _rep_rank(values[:2], first) * third + values[2]
    elif masses[1] == masses[2]:
        result = values[0] * comb(second + 1, 2) + _rep_rank(
            values[1:],
            second,
        )
    return result


def _unrank_equal_first(
    first: int,
    third: int,
    rank: int,
) -> tuple[int, int, int]:
    pair_rank, last = divmod(rank, third)
    pair = _rep_unrank(first, 2, pair_rank)
    return pair[0], pair[1], last


def _unrank_equal_last(
    second: int,
    rank: int,
) -> tuple[int, int, int]:
    pair_count = comb(second + 1, 2)
    head, pair_rank = divmod(rank, pair_count)
    pair = _rep_unrank(second, 2, pair_rank)
    return head, pair[0], pair[1]


def _unrank_distinct(
    second: int,
    third: int,
    rank: int,
) -> tuple[int, int, int]:
    head, tail = divmod(rank, second * third)
    middle, last = divmod(tail, third)
    return head, middle, last


def _edge_local_unrank(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    first = _block_count(masses[0])
    second = _block_count(masses[1])
    third = _block_count(masses[2])
    result = _unrank_distinct(second, third, rank)
    if masses[0] == masses[2]:
        values = _rep_unrank(first, _BLOCK_COUNT, rank)
        result = values[0], values[1], values[2]
    elif masses[0] == masses[1]:
        result = _unrank_equal_first(first, third, rank)
    elif masses[1] == masses[2]:
        result = _unrank_equal_last(second, rank)
    return result


def _as_edge(vector: _Vector) -> _Edge:
    assert len(vector) == _EDGE_COMPONENTS
    first, second, third, fourth = vector
    return first, second, third, fourth


def _as_edges(values: tuple[_Edge, ...]) -> _Edges:
    assert len(values) == _EDGE_COUNT
    first, second, third, fourth, fifth, sixth = values
    return first, second, third, fourth, fifth, sixth


def _blocks_from_edges(edges: _Edges) -> _Blocks:
    result: list[_Block] = []
    for left_edge, right_edge in _BUNDLE_EDGES:
        left = edges[_K4_EDGE_INDEX[left_edge]]
        right = edges[_K4_EDGE_INDEX[right_edge]]
        result.append(_as_block((*left, *right)))
    first, second, third = result
    return first, second, third


def _edges_from_blocks(blocks: _Blocks) -> _Edges:
    result: list[_Edge | None] = [None] * _EDGE_COUNT
    for block, edge_pair in zip(blocks, _BUNDLE_EDGES, strict=True):
        result[_K4_EDGE_INDEX[edge_pair[0]]] = _as_edge(
            block[:_EDGE_COMPONENTS]
        )
        result[_K4_EDGE_INDEX[edge_pair[1]]] = _as_edge(
            block[_EDGE_COMPONENTS:]
        )
    assert all(edge is not None for edge in result)
    first, second, third, fourth, fifth, sixth = result
    assert first is not None
    assert second is not None
    assert third is not None
    assert fourth is not None
    assert fifth is not None
    assert sixth is not None
    return first, second, third, fourth, fifth, sixth


def _edge_rank(edges: _Edges) -> int | None:
    if any(value < 0 for edge in edges for value in edge):
        return None
    blocks = sorted(
        _blocks_from_edges(edges),
        key=lambda block: (sum(block), _block_rank(block)),
    )
    masses = sum(blocks[0]), sum(blocks[1]), sum(blocks[2])
    values = (
        _block_rank(blocks[0]),
        _block_rank(blocks[1]),
        _block_rank(blocks[2]),
    )
    total = sum(masses)
    prefix = sum(
        _edge_block_count(candidate)
        for candidate in _mass_triples(total)
        if candidate < masses
    )
    return prefix + _edge_local_rank(masses, values)


def _edge_unrank(total: int, rank: int) -> _Edges | None:
    if rank < 0 or rank >= _edge_count(total):
        return None
    remaining = rank
    for masses in _mass_triples(total):
        block = _edge_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        values = _edge_local_unrank(masses, remaining)
        blocks = (
            _block_unrank(masses[0], values[0]),
            _block_unrank(masses[1], values[1]),
            _block_unrank(masses[2], values[2]),
        )
        return _edges_from_blocks(blocks)
    raise AssertionError


def _ordered_edge(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def _bundle_order(bundles: _Bundles) -> tuple[int, int, int, int] | None:
    keyed = tuple(
        (_bundle_key(bundle), index)
        for index, bundle in enumerate(bundles)
    )
    multiplicities = Counter(key for key, _ in keyed)
    partition = tuple(sorted(multiplicities.values(), reverse=True))
    if partition != _SECOND_PARTITION:
        return None
    repeated = next(
        key
        for key, count in multiplicities.items()
        if count == _REPEAT_COUNT
    )
    repeated_indices = tuple(
        sorted(index for key, index in keyed if key == repeated)
    )
    singleton = next(index for key, index in keyed if key != repeated)
    return (
        repeated_indices[0],
        repeated_indices[1],
        repeated_indices[2],
        singleton,
    )


def _reorder_edges(edges: _Edges, order: tuple[int, int, int, int]) -> _Edges:
    values = tuple(
        edges[_K4_EDGE_INDEX[_ordered_edge(order[left], order[right])]]
        for left, right in _K4_EDGES
    )
    return _as_edges(values)


def _canonicalize_residual(state: _Residual) -> _Residual | None:
    fixed, bundles, edges = state
    valid = (
        len(fixed) == _FIXED_COMPONENTS
        and all(len(bundle) == _VERTEX_COMPONENTS for bundle in bundles)
        and all(len(edge) == _EDGE_COMPONENTS for edge in edges)
        and all(
            value >= 0
            for vector in (fixed, *bundles, *edges)
            for value in vector
        )
    )
    if not valid:
        return None
    order = _bundle_order(bundles)
    if order is None:
        return None
    repeated = bundles[order[0]]
    canonical_bundles = repeated, repeated, repeated, bundles[order[3]]
    return fixed, canonical_bundles, _reorder_edges(edges, order)


@cache
def _residual_count(total: int) -> int:
    return sum(
        _composition_count(fixed_mass, _FIXED_COMPONENTS)
        * _bundle_count(bundle_mass)
        * _edge_count(total - fixed_mass - bundle_mass)
        for fixed_mass in range(total + 1)
        for bundle_mass in range(total - fixed_mass + 1)
    )


def _residual_rank_data(
    state: _Residual,
) -> tuple[_Vector, _Bundles, _Edges, tuple[int, int, int]] | None:
    canonical = _canonicalize_residual(state)
    if canonical is None:
        return None
    fixed, bundles, edges = canonical
    masses = (
        sum(fixed),
        sum(sum(bundle) for bundle in bundles),
        sum(sum(edge) for edge in edges),
    )
    return fixed, bundles, edges, masses


def _residual_prefix(total: int, fixed_mass: int, bundle_mass: int) -> int:
    return sum(
        _composition_count(fmass, _FIXED_COMPONENTS)
        * _bundle_count(bmass)
        * _edge_count(total - fmass - bmass)
        for fmass in range(total + 1)
        for bmass in range(total - fmass + 1)
        if (fmass, bmass) < (fixed_mass, bundle_mass)
    )


def _residual_local_rank(
    state: _Residual,
    masses: tuple[int, int, int],
) -> int:
    fixed, bundles, edges = state
    fixed_rank = _composition_rank(fixed, _FIXED_COMPONENTS)
    bundle_rank = _bundle_rank(bundles)
    edge_rank = _edge_rank(edges)
    assert fixed_rank is not None
    assert bundle_rank is not None
    assert edge_rank is not None
    bundle_count = _bundle_count(masses[1])
    edge_count = _edge_count(masses[2])
    return (fixed_rank * bundle_count + bundle_rank) * edge_count + edge_rank


def _residual_rank(state: _Residual) -> int | None:
    data = _residual_rank_data(state)
    if data is None:
        return None
    fixed, bundles, edges, masses = data
    total = sum(masses)
    prefix = _residual_prefix(total, masses[0], masses[1])
    return prefix + _residual_local_rank((fixed, bundles, edges), masses)


def _residual_component_ranks(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    bundle_count = _bundle_count(masses[1])
    edge_count = _edge_count(masses[2])
    fixed_and_bundle, edge_rank = divmod(rank, edge_count)
    fixed_rank, bundle_rank = divmod(fixed_and_bundle, bundle_count)
    return fixed_rank, bundle_rank, edge_rank


def _unrank_residual_block(
    masses: tuple[int, int, int],
    rank: int,
) -> _Residual:
    fixed_rank, bundle_rank, edge_rank = _residual_component_ranks(masses, rank)
    fixed = _composition_unrank(masses[0], _FIXED_COMPONENTS, fixed_rank)
    bundles = _bundle_unrank(masses[1], bundle_rank)
    edges = _edge_unrank(masses[2], edge_rank)
    assert fixed is not None
    assert bundles is not None
    assert edges is not None
    return fixed, bundles, edges


def _residual_unrank(total: int, rank: int) -> _Residual | None:
    if rank < 0 or rank >= _residual_count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        for bundle_mass in range(total - fixed_mass + 1):
            edge_mass = total - fixed_mass - bundle_mass
            block = (
                _composition_count(fixed_mass, _FIXED_COMPONENTS)
                * _bundle_count(bundle_mass)
                * _edge_count(edge_mass)
            )
            if remaining >= block:
                remaining -= block
                continue
            return _unrank_residual_block(
                (fixed_mass, bundle_mass, edge_mass),
                remaining,
            )
    raise AssertionError


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


def _as_vertices(values: tuple[_Pair, ...]) -> _Vertices:
    assert len(values) == _ARITY
    first, second, third, fourth, fifth, sixth = values
    return first, second, third, fourth, fifth, sixth


def _partition(values: tuple[_Pair, ...]) -> tuple[int, ...]:
    return tuple(sorted(Counter(values).values(), reverse=True))


@cache
def _vertices_of_mass(mass: int) -> tuple[_Vertices, ...]:
    return tuple(
        _as_vertices(values)
        for values in _vertex_sequences_from(0, _ARITY, mass)
        if sum(sum(pair) for pair in values) == mass
        and _partition(values) == _TOP_PARTITION
    )


@cache
def _class_count(total: int) -> int:
    return sum(
        len(_vertices_of_mass(vertex_mass))
        * _residual_count(total - vertex_mass)
        for vertex_mass in range(total + 1)
    )


def _residual_mass(residual: _Residual) -> int:
    return sum(
        value
        for vector in (residual[0], *residual[1], *residual[2])
        for value in vector
    )


def _state_rank_data(
    total: int,
    state: _State,
) -> tuple[int, int, int, int] | None:
    vertices, residual = state
    vertex_mass = sum(sum(pair) for pair in vertices)
    residual_mass = total - vertex_mass
    valid_mass = (
        vertex_mass <= total
        and _residual_mass(residual) == residual_mass
    )
    result: tuple[int, int, int, int] | None = None
    if valid_mass:
        try:
            vertex_rank = _vertices_of_mass(vertex_mass).index(vertices)
        except ValueError:
            vertex_rank = -1
        residual_rank = _residual_rank(residual)
        if vertex_rank >= 0 and residual_rank is not None:
            result = vertex_mass, vertex_rank, residual_mass, residual_rank
    return result


def _rank(total: int, state: _State) -> int | None:
    data = _state_rank_data(total, state)
    if data is None:
        return None
    vertex_mass, vertex_rank, residual_mass, residual_rank = data
    prefix = sum(
        len(_vertices_of_mass(mass)) * _residual_count(total - mass)
        for mass in range(vertex_mass)
    )
    return prefix + vertex_rank * _residual_count(residual_mass) + residual_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for vertex_mass in range(total + 1):
        residual_count = _residual_count(total - vertex_mass)
        block = len(_vertices_of_mass(vertex_mass)) * residual_count
        if remaining >= block:
            remaining -= block
            continue
        vertex_rank, residual_rank = divmod(remaining, residual_count)
        residual = _residual_unrank(total - vertex_mass, residual_rank)
        assert residual is not None
        return _vertices_of_mass(vertex_mass)[vertex_rank], residual
    raise AssertionError


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _slice_vectors(
    vector: _Vector,
    *,
    start: int,
    count: int,
    width: int,
) -> tuple[_Vector, ...]:
    return tuple(
        vector[start + index * width : start + (index + 1) * width]
        for index in range(count)
    )


def _as_bundles(values: tuple[_Bundle, ...]) -> _Bundles:
    assert len(values) == _ACTIVE_COUNT
    first, second, third, fourth = values
    return first, second, third, fourth


def _vector_to_residual(vector: _Vector) -> _Residual:
    expected = (
        _FIXED_COMPONENTS
        + _ACTIVE_COUNT * _VERTEX_COMPONENTS
        + _EDGE_COUNT * _EDGE_COMPONENTS
    )
    assert len(vector) == expected
    bundle_start = _FIXED_COMPONENTS
    edge_start = bundle_start + _ACTIVE_COUNT * _VERTEX_COMPONENTS
    bundle_values = _slice_vectors(
        vector,
        start=bundle_start,
        count=_ACTIVE_COUNT,
        width=_VERTEX_COMPONENTS,
    )
    edge_values = _slice_vectors(
        vector,
        start=edge_start,
        count=_EDGE_COUNT,
        width=_EDGE_COMPONENTS,
    )
    bundles = _as_bundles(tuple(_as_bundle(item) for item in bundle_values))
    edges = _as_edges(tuple(_as_edge(item) for item in edge_values))
    return vector[:_FIXED_COMPONENTS], bundles, edges


def _inverse_order(order: tuple[int, ...]) -> tuple[int, int, int, int]:
    inverse = tuple(order.index(destination) for destination in _ACTIVE)
    first, second, third, fourth = inverse
    return first, second, third, fourth


def _permute_residual(state: _Residual, order: tuple[int, ...]) -> _Residual:
    fixed, bundles, edges = state
    inverse = _inverse_order(order)
    permuted_bundles = _as_bundles(
        tuple(bundles[inverse[destination]] for destination in _ACTIVE)
    )
    permuted_edges = _as_edges(
        tuple(
            edges[_K4_EDGE_INDEX[_ordered_edge(inverse[left], inverse[right])]]
            for left, right in _K4_EDGES
        )
    )
    return fixed, permuted_bundles, permuted_edges


def test_s6_s4_s3_bundle_rank_matches_small_s4_orbits() -> None:
    """Triple-bundle orientation agrees across raw S4 presentations."""
    ranks: set[int] = set()
    for vector in _weak_compositions(_EXHAUSTIVE_ORBIT_MASS, 52):
        state = _vector_to_residual(vector)
        rank = _residual_rank(state)
        if rank is None:
            continue
        ranks.add(rank)
        for order in _S4:
            assert _residual_rank(_permute_residual(state, order)) == rank
    assert ranks == set(range(_residual_count(_EXHAUSTIVE_ORBIT_MASS)))


def test_s6_s4_s3_bundle_rank_exhausts_small_full_domains() -> None:
    """Every admitted class through mass six receives one contiguous rank."""
    for total in range(_EXHAUSTIVE_FULL_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s4_s3_bundle_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior ranks roundtrip through checked masses."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        if count == 0:
            continue
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT


def test_s6_s4_s3_bundle_counts_match_reviewed_sequence() -> None:
    """Mass-three-through-fourteen counts match the nested factorization."""
    observed = {
        mass: _class_count(mass)
        for mass in range(_MAXIMUM_MASS + 1)
        if _class_count(mass) != 0
    }
    assert observed == _EXPECTED_COUNTS
