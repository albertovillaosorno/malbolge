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
#   - Dense rank/unrank for the S3 spoke stratum of S6 (5,1)/(4,1).
# - Must-Not:
#   - Claim ranking for the full-S4 spoke stabilizer.
# - Allows:
#   - Inputs: widened S4 spoke/K4-edge mass zero through fourteen.
#   - Outputs: dense ranks when four spokes have partition (3,1).
#   - Side effects: none.
# - Split-When:
#   - The full-S4 spoke stratum receives constructive rank/unrank.
# - Merge-When:
#   - Complete dense ranking owns the full S6 (5,1)/(4,1) edge slice.
# - Summary:
#   - Rank one triple spoke plus singleton and a weighted three-block edge
#     multiset.
# - Description:
#   - Three widened opposite-edge blocks share the residual S3 permutation.
# - Usage:
#   - Constructive order-six spoke stratum beneath the S4 factorization.
# - Defaults:
#   - Direct S4 orbit checks stop at mass two; dense exhaustion stops at five.
#

"""Dense S3 spoke ranking inside the S6 (5,1)/(4,1) stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import permutations
from math import comb

_ACTIVE_COUNT = 4
_ACTIVE = tuple(range(_ACTIVE_COUNT))
_REPEAT_COUNT = 3
_SINGLE_COUNT = 1
_SPOKE_COMPONENTS = 4
_EDGE_COMPONENTS = 4
_EDGE_COUNT = 6
_BLOCK_COMPONENTS = 2 * _EDGE_COMPONENTS
_BLOCK_COUNT = 3
_MAXIMUM_MASS = 14
_EXHAUSTIVE_FULL_MASS = 5
_EXHAUSTIVE_ORBIT_MASS = 2
_SECOND_PARTITION = (3, 1)
_SAMPLE_LIMIT = 5
_WIDTH_FOURTEEN_COUNT = 5_663_416_324
_EXPECTED_COUNTS = {
    1: 4,
    2: 42,
    3: 392,
    4: 3_071,
    5: 20_488,
    6: 119_118,
    7: 613_740,
    8: 2_844_515,
    9: 12_018_480,
    10: 46_817_108,
    11: 169_745_760,
    12: 577_433_044,
    13: 1_855_393_032,
    14: 5_663_416_324,
}
_K4_EDGES = tuple(
    (left, right) for left in _ACTIVE for right in _ACTIVE if left < right
)
_K4_EDGE_INDEX = {edge: index for index, edge in enumerate(_K4_EDGES)}
_S4 = tuple(permutations(_ACTIVE))
_BUNDLE_EDGES = (
    ((1, 2), (0, 3)),
    ((0, 2), (1, 3)),
    ((0, 1), (2, 3)),
)

type _Vector = tuple[int, ...]
type _Spoke = tuple[int, int, int, int]
type _Spokes = tuple[_Spoke, _Spoke, _Spoke, _Spoke]
type _Edge = tuple[int, int, int, int]
type _Edges = tuple[_Edge, _Edge, _Edge, _Edge, _Edge, _Edge]
type _Block = tuple[int, int, int, int, int, int, int, int]
type _Blocks = tuple[_Block, _Block, _Block]
type _State = tuple[_Spokes, _Edges]


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


def _as_spoke(vector: _Vector) -> _Spoke:
    assert len(vector) == _SPOKE_COMPONENTS
    first, second, third, fourth = vector
    return first, second, third, fourth


def _raw_spoke_count(total: int) -> int:
    return _composition_count(total, _SPOKE_COMPONENTS)


def _spoke_key(spoke: _Spoke) -> tuple[int, int]:
    rank = _composition_rank(spoke, _SPOKE_COMPONENTS)
    assert rank is not None
    return sum(spoke), rank


def _spoke_mass_pairs(total: int) -> tuple[tuple[int, int], ...]:
    return tuple(
        (repeated, total - _REPEAT_COUNT * repeated)
        for repeated in range(total // _REPEAT_COUNT + 1)
    )


def _spoke_block_count(masses: tuple[int, int]) -> int:
    repeated_mass, single_mass = masses
    repeated = _raw_spoke_count(repeated_mass)
    single = _raw_spoke_count(single_mass)
    if repeated_mass == single_mass:
        single -= 1
    return repeated * single


@cache
def _spoke_count(total: int) -> int:
    return sum(
        _spoke_block_count(masses) for masses in _spoke_mass_pairs(total)
    )


def _spoke_rank_data(
    spokes: _Spokes,
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    keys = tuple(_spoke_key(spoke) for spoke in spokes)
    multiplicities = Counter(keys)
    partition = tuple(sorted(multiplicities.values(), reverse=True))
    if partition != _SECOND_PARTITION:
        return None
    repeated = next(
        key for key, count in multiplicities.items() if count == _REPEAT_COUNT
    )
    single = next(
        key for key, count in multiplicities.items() if count == _SINGLE_COUNT
    )
    return (repeated[0], single[0]), (repeated[1], single[1])


def _spoke_local_rank(
    masses: tuple[int, int],
    ranks: tuple[int, int],
) -> int:
    repeated_rank, single_rank = ranks
    single_count = _raw_spoke_count(masses[1])
    if masses[0] == masses[1]:
        single_rank = _filtered_rank(single_rank, repeated_rank)
        single_count -= 1
    return repeated_rank * single_count + single_rank


def _spoke_local_unrank(
    masses: tuple[int, int],
    rank: int,
) -> tuple[int, int]:
    single_count = _raw_spoke_count(masses[1])
    same_mass = masses[0] == masses[1]
    if same_mass:
        single_count -= 1
    repeated_rank, single_rank = divmod(rank, single_count)
    if same_mass:
        single_rank = _filtered_unrank(single_rank, repeated_rank)
    return repeated_rank, single_rank


def _spoke_rank(spokes: _Spokes) -> int | None:
    data = _spoke_rank_data(spokes)
    if data is None:
        return None
    masses, ranks = data
    total = sum(sum(spoke) for spoke in spokes)
    prefix = sum(
        _spoke_block_count(candidate)
        for candidate in _spoke_mass_pairs(total)
        if candidate < masses
    )
    return prefix + _spoke_local_rank(masses, ranks)


def _spoke_unrank(total: int, rank: int) -> _Spokes | None:
    if rank < 0 or rank >= _spoke_count(total):
        return None
    remaining = rank
    for masses in _spoke_mass_pairs(total):
        block = _spoke_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        repeated_rank, single_rank = _spoke_local_unrank(masses, remaining)
        repeated = _composition_unrank(
            masses[0],
            _SPOKE_COMPONENTS,
            repeated_rank,
        )
        single = _composition_unrank(masses[1], _SPOKE_COMPONENTS, single_rank)
        assert repeated is not None
        assert single is not None
        repeated_spoke = _as_spoke(repeated)
        single_spoke = _as_spoke(single)
        return (
            repeated_spoke,
            repeated_spoke,
            repeated_spoke,
            single_spoke,
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


def _spoke_order(spokes: _Spokes) -> tuple[int, int, int, int] | None:
    keyed = tuple(
        (_spoke_key(spoke), index) for index, spoke in enumerate(spokes)
    )
    multiplicities = Counter(key for key, _ in keyed)
    partition = tuple(sorted(multiplicities.values(), reverse=True))
    if partition != _SECOND_PARTITION:
        return None
    repeated = next(
        key for key, count in multiplicities.items() if count == _REPEAT_COUNT
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


def _canonicalize_state(state: _State) -> _State | None:
    spokes, edges = state
    valid = (
        all(len(spoke) == _SPOKE_COMPONENTS for spoke in spokes)
        and all(len(edge) == _EDGE_COMPONENTS for edge in edges)
        and all(value >= 0 for vector in (*spokes, *edges) for value in vector)
    )
    if not valid:
        return None
    order = _spoke_order(spokes)
    if order is None:
        return None
    repeated = spokes[order[0]]
    single = spokes[order[3]]
    canonical_spokes = repeated, repeated, repeated, single
    return canonical_spokes, _reorder_edges(edges, order)


@cache
def _class_count(total: int) -> int:
    return sum(
        _spoke_count(spoke_mass) * _edge_count(total - spoke_mass)
        for spoke_mass in range(total + 1)
    )


def _rank(total: int, state: _State) -> int | None:
    canonical = _canonicalize_state(state)
    if canonical is None:
        return None
    spokes, edges = canonical
    spoke_mass = sum(sum(spoke) for spoke in spokes)
    edge_mass = sum(sum(edge) for edge in edges)
    if spoke_mass + edge_mass != total:
        return None
    spoke_rank = _spoke_rank(spokes)
    edge_rank = _edge_rank(edges)
    assert spoke_rank is not None
    assert edge_rank is not None
    prefix = sum(
        _spoke_count(mass) * _edge_count(total - mass)
        for mass in range(spoke_mass)
    )
    return prefix + spoke_rank * _edge_count(edge_mass) + edge_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for spoke_mass in range(total + 1):
        edge_mass = total - spoke_mass
        edge_count = _edge_count(edge_mass)
        block = _spoke_count(spoke_mass) * edge_count
        if remaining >= block:
            remaining -= block
            continue
        spoke_rank, edge_rank = divmod(remaining, edge_count)
        spokes = _spoke_unrank(spoke_mass, spoke_rank)
        edges = _edge_unrank(edge_mass, edge_rank)
        assert spokes is not None
        assert edges is not None
        return spokes, edges
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


def _as_spokes(values: tuple[_Spoke, ...]) -> _Spokes:
    assert len(values) == _ACTIVE_COUNT
    first, second, third, fourth = values
    return first, second, third, fourth


def _vector_to_state(vector: _Vector) -> _State:
    spoke_scalars = _ACTIVE_COUNT * _SPOKE_COMPONENTS
    edge_scalars = _EDGE_COUNT * _EDGE_COMPONENTS
    assert len(vector) == spoke_scalars + edge_scalars
    spoke_values = _slice_vectors(
        vector, start=0, count=_ACTIVE_COUNT, width=_SPOKE_COMPONENTS
    )
    edge_values = _slice_vectors(
        vector,
        start=spoke_scalars,
        count=_EDGE_COUNT,
        width=_EDGE_COMPONENTS,
    )
    spokes = _as_spokes(tuple(_as_spoke(item) for item in spoke_values))
    edges = _as_edges(tuple(_as_edge(item) for item in edge_values))
    return spokes, edges


def _inverse_order(order: tuple[int, ...]) -> tuple[int, int, int, int]:
    inverse = tuple(order.index(destination) for destination in _ACTIVE)
    first, second, third, fourth = inverse
    return first, second, third, fourth


def _permute_state(state: _State, order: tuple[int, ...]) -> _State:
    spokes, edges = state
    inverse = _inverse_order(order)
    permuted_spokes = _as_spokes(
        tuple(spokes[inverse[destination]] for destination in _ACTIVE)
    )
    permuted_edges = _as_edges(
        tuple(
            edges[_K4_EDGE_INDEX[_ordered_edge(inverse[left], inverse[right])]]
            for left, right in _K4_EDGES
        )
    )
    return permuted_spokes, permuted_edges


def _sample_ranks(count: int) -> tuple[int, ...]:
    if count <= _SAMPLE_LIMIT:
        return tuple(range(count))
    return 0, 1, count // 2, count - 2, count - 1


def test_s6_s5_s4_s3_spoke_rank_matches_small_s4_orbits() -> None:
    """Full S4 relabeling preserves the dense S3 spoke-stratum rank."""
    scalar_count = (
        _ACTIVE_COUNT * _SPOKE_COMPONENTS + _EDGE_COUNT * _EDGE_COMPONENTS
    )
    for total in range(_EXHAUSTIVE_ORBIT_MASS + 1):
        observed: set[int] = set()
        for vector in _weak_compositions(total, scalar_count):
            state = _vector_to_state(vector)
            rank = _rank(total, state)
            if rank is None:
                continue
            observed.add(rank)
            assert {
                _rank(total, _permute_state(state, order)) for order in _S4
            } == {rank}
        assert observed == set(range(_class_count(total)))


def test_s6_s5_s4_s3_spoke_rank_exhausts_small_domains() -> None:
    """Every small S3 spoke class receives exactly one dense rank."""
    for total in range(_EXHAUSTIVE_FULL_MASS + 1):
        count = _class_count(total)
        for rank in range(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s5_s4_s3_spoke_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior S3 spoke ranks invert through mass fourteen."""
    observed = {
        total: _class_count(total)
        for total in range(_MAXIMUM_MASS + 1)
        if _class_count(total)
    }
    assert observed == _EXPECTED_COUNTS
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in _sample_ranks(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
