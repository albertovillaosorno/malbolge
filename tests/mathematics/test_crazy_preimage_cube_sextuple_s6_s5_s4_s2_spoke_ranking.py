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
#   - Dense rank/unrank for the S2 spoke stratum of S6 (5,1)/(4,1).
# - Must-Not:
#   - Claim ranking for V4, S3, or S4 spoke stabilizers.
# - Allows:
#   - Inputs: widened S4 spoke/K4-edge mass zero through fourteen.
#   - Outputs: dense ranks when four spokes have partition (2,1,1).
#   - Side effects: none.
# - Split-When:
#   - Another nontrivial spoke stabilizer receives constructive rank/unrank.
# - Merge-When:
#   - Complete dense ranking owns the full S6 (5,1)/(4,1) edge slice.
# - Summary:
#   - Rank one repeated spoke and one shared K4-edge transposition.
# - Description:
#   - Two fixed widened edges plus two eight-scalar blocks share one swap.
# - Usage:
#   - Largest nontrivial spoke stratum beneath the S6 (5,1)/(4,1) factorization.
# - Defaults:
#   - Direct S4 orbit checks stop at mass two; dense exhaustion stops at five.
#

"""Dense S2 spoke ranking inside the S6 (5,1)/(4,1) stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import permutations
from math import comb
from operator import itemgetter
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Callable

_ACTIVE_COUNT = 4
_ACTIVE = tuple(range(_ACTIVE_COUNT))
_SPOKE_COMPONENTS = 4
_EDGE_COMPONENTS = 4
_EDGE_COUNT = 6
_FIXED_EDGE_SCALARS = 2 * _EDGE_COMPONENTS
_MOVING_BLOCK_COMPONENTS = 2 * _EDGE_COMPONENTS
_MAXIMUM_MASS = 14
_EXHAUSTIVE_FULL_MASS = 5
_EXHAUSTIVE_ORBIT_MASS = 2
_SECOND_PARTITION = (2, 1, 1)
_REPEAT_COUNT = 2
_SINGLE_COUNT = 1
_SAMPLE_LIMIT = 5
_WIDTH_FOURTEEN_COUNT = 39_143_536_686
_EXPECTED_COUNTS = {
    2: 6,
    3: 148,
    4: 2_041,
    5: 20_708,
    6: 168_194,
    7: 1_147_672,
    8: 6_789_551,
    9: 35_641_020,
    10: 168_969_046,
    11: 733_547_104,
    12: 2_948_627_389,
    13: 11_073_644_648,
    14: 39_143_536_686,
}
_EXPECTED_EDGE_COUNTS = {
    0: 1,
    1: 16,
    2: 172,
    3: 1_392,
    4: 9_102,
    5: 50_160,
    6: 240_396,
    7: 1_025_424,
    8: 3_962_709,
    9: 14_066_624,
    10: 46_373_008,
    11: 143_242_816,
    12: 417_617_240,
    13: 1_156_157_760,
    14: 3_054_985_680,
}
_K4_EDGES = tuple(
    (left, right) for left in _ACTIVE for right in _ACTIVE if left < right
)
_K4_EDGE_INDEX = {edge: index for index, edge in enumerate(_K4_EDGES)}
_S4 = tuple(permutations(_ACTIVE))
_FIXED_EDGES = ((0, 1), (2, 3))
_LEFT_EDGES = ((0, 2), (1, 2))
_RIGHT_EDGES = ((0, 3), (1, 3))

type _Vector = tuple[int, ...]
type _Spoke = tuple[int, int, int, int]
type _Spokes = tuple[_Spoke, _Spoke, _Spoke, _Spoke]
type _Edge = tuple[int, int, int, int]
type _Edges = tuple[_Edge, _Edge, _Edge, _Edge, _Edge, _Edge]
type _Block = tuple[int, int, int, int, int, int, int, int]
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


def _strict_pair_rank(left: int, right: int, population: int) -> int:
    assert 0 <= left < right < population
    return left * (2 * population - left - 1) // 2 + right - left - 1


def _strict_pair_unrank(rank: int, population: int) -> tuple[int, int]:
    remaining = rank
    for left in range(population - 1):
        block = population - left - 1
        if remaining >= block:
            remaining -= block
            continue
        return left, left + remaining + 1
    raise AssertionError


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


def _spoke_mass_triples(total: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (repeated, first, total - 2 * repeated - first)
        for repeated in range(total // 2 + 1)
        for first in range(total - 2 * repeated + 1)
        if first <= total - 2 * repeated - first
    )


def _spoke_block_count(masses: tuple[int, int, int]) -> int:
    repeated, first, second = masses
    repeated_count = _raw_spoke_count(repeated)
    first_count = _raw_spoke_count(first)
    second_count = _raw_spoke_count(second)
    if first < second:
        if repeated == first:
            first_count -= 1
        if repeated == second:
            second_count -= 1
        return repeated_count * first_count * second_count
    assert first == second
    pair_count = comb(first_count, 2)
    if repeated == first:
        pair_count = comb(first_count - 1, 2)
    return repeated_count * pair_count


@cache
def _spoke_count(total: int) -> int:
    return sum(
        _spoke_block_count(masses) for masses in _spoke_mass_triples(total)
    )


def _rank_unequal_singletons(
    masses: tuple[int, int, int],
    ranks: tuple[int, int, int],
) -> int:
    repeated_mass, first_mass, second_mass = masses
    repeated_rank, first_rank, second_rank = ranks
    first_count = _raw_spoke_count(first_mass)
    second_count = _raw_spoke_count(second_mass)
    if repeated_mass == first_mass:
        first_rank = _filtered_rank(first_rank, repeated_rank)
        first_count -= 1
    if repeated_mass == second_mass:
        second_rank = _filtered_rank(second_rank, repeated_rank)
        second_count -= 1
    return (
        repeated_rank * first_count + first_rank
    ) * second_count + second_rank


def _rank_equal_singletons(
    repeated_mass: int,
    singleton_mass: int,
    ranks: tuple[int, int, int],
) -> int:
    repeated_rank, first_rank, second_rank = ranks
    population = _raw_spoke_count(singleton_mass)
    if repeated_mass == singleton_mass:
        first_rank = _filtered_rank(first_rank, repeated_rank)
        second_rank = _filtered_rank(second_rank, repeated_rank)
        population -= 1
    pair_rank = _strict_pair_rank(first_rank, second_rank, population)
    return repeated_rank * comb(population, _REPEAT_COUNT) + pair_rank


def _spoke_local_rank(
    masses: tuple[int, int, int],
    ranks: tuple[int, int, int],
) -> int:
    if masses[1] < masses[2]:
        return _rank_unequal_singletons(masses, ranks)
    return _rank_equal_singletons(masses[0], masses[1], ranks)


def _unrank_unequal_singletons(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    repeated_mass, first_mass, second_mass = masses
    first_count = _raw_spoke_count(first_mass)
    second_count = _raw_spoke_count(second_mass)
    if repeated_mass == first_mass:
        first_count -= 1
    if repeated_mass == second_mass:
        second_count -= 1
    repeated_rank, pair_rank = divmod(rank, first_count * second_count)
    first_rank, second_rank = divmod(pair_rank, second_count)
    if repeated_mass == first_mass:
        first_rank = _filtered_unrank(first_rank, repeated_rank)
    if repeated_mass == second_mass:
        second_rank = _filtered_unrank(second_rank, repeated_rank)
    return repeated_rank, first_rank, second_rank


def _unrank_equal_singletons(
    repeated_mass: int,
    singleton_mass: int,
    rank: int,
) -> tuple[int, int, int]:
    population = _raw_spoke_count(singleton_mass)
    excludes_repeated = repeated_mass == singleton_mass
    if excludes_repeated:
        population -= 1
    pair_count = comb(population, _REPEAT_COUNT)
    repeated_rank, pair_rank = divmod(rank, pair_count)
    first_rank, second_rank = _strict_pair_unrank(pair_rank, population)
    if excludes_repeated:
        first_rank = _filtered_unrank(first_rank, repeated_rank)
        second_rank = _filtered_unrank(second_rank, repeated_rank)
    return repeated_rank, first_rank, second_rank


def _spoke_local_unrank(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    if masses[1] < masses[2]:
        return _unrank_unequal_singletons(masses, rank)
    return _unrank_equal_singletons(masses[0], masses[1], rank)


def _spoke_rank_data(
    spokes: _Spokes,
) -> tuple[tuple[int, int, int], tuple[int, int, int]] | None:
    keys = tuple(_spoke_key(spoke) for spoke in spokes)
    multiplicities = Counter(keys)
    partition = tuple(sorted(multiplicities.values(), reverse=True))
    if partition != _SECOND_PARTITION:
        return None
    repeated_key = next(
        key for key, count in multiplicities.items() if count == _REPEAT_COUNT
    )
    singleton_keys = tuple(
        sorted(
            key
            for key, count in multiplicities.items()
            if count == _SINGLE_COUNT
        )
    )
    first_key, second_key = singleton_keys
    masses = repeated_key[0], first_key[0], second_key[0]
    ranks = repeated_key[1], first_key[1], second_key[1]
    return masses, ranks


def _spoke_rank(spokes: _Spokes) -> int | None:
    data = _spoke_rank_data(spokes)
    if data is None:
        return None
    masses, ranks = data
    total = sum(sum(spoke) for spoke in spokes)
    prefix = sum(
        _spoke_block_count(candidate)
        for candidate in _spoke_mass_triples(total)
        if candidate < masses
    )
    return prefix + _spoke_local_rank(masses, ranks)


def _spoke_unrank(total: int, rank: int) -> _Spokes | None:
    if rank < 0 or rank >= _spoke_count(total):
        return None
    remaining = rank
    for masses in _spoke_mass_triples(total):
        block = _spoke_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        ranks = _spoke_local_unrank(masses, remaining)
        values: list[_Spoke] = []
        for mass, raw_rank in zip(masses, ranks, strict=True):
            vector = _composition_unrank(mass, _SPOKE_COMPONENTS, raw_rank)
            assert vector is not None
            values.append(_as_spoke(vector))
        repeated, first, second = values
        return repeated, repeated, first, second
    raise AssertionError


def _as_block(vector: _Vector) -> _Block:
    assert len(vector) == _MOVING_BLOCK_COMPONENTS
    a, b, c, d, e, f, g, h = vector
    return a, b, c, d, e, f, g, h


_swap_block = cast(
    "Callable[[_Block], _Block]",
    itemgetter(4, 5, 6, 7, 0, 1, 2, 3),
)


@cache
def _blocks(total: int) -> tuple[_Block, ...]:
    return tuple(
        _as_block(vector)
        for vector in _weak_compositions(total, _MOVING_BLOCK_COMPONENTS)
    )


@cache
def _fixed_blocks(total: int) -> tuple[_Block, ...]:
    return tuple(
        block for block in _blocks(total) if _swap_block(block) == block
    )


@cache
def _moving_blocks(total: int) -> tuple[_Block, ...]:
    return tuple(
        sorted({
            min(block, _swap_block(block))
            for block in _blocks(total)
            if _swap_block(block) != block
        })
    )


def _raw_block_count(total: int) -> int:
    return _composition_count(total, _MOVING_BLOCK_COMPONENTS)


def _fixed_block_count(total: int) -> int:
    return len(_fixed_blocks(total))


def _orbit_block_count(total: int) -> int:
    return _fixed_block_count(total) + len(_moving_blocks(total))


def _block_raw_rank(block: _Block) -> int:
    rank = _composition_rank(block, _MOVING_BLOCK_COMPONENTS)
    assert rank is not None
    return rank


def _block_orbit_rank(block: _Block) -> tuple[int, bool, bool]:
    total = sum(block)
    fixed = _fixed_blocks(total)
    if block in fixed:
        return fixed.index(block), False, False
    canonical = min(block, _swap_block(block))
    return (
        len(fixed) + _moving_blocks(total).index(canonical),
        True,
        block != canonical,
    )


def _block_orbit_unrank(total: int, rank: int) -> _Block:
    fixed = _fixed_block_count(total)
    if rank < fixed:
        return _fixed_blocks(total)[rank]
    return _moving_blocks(total)[rank - fixed]


def _diagonal_count(left_mass: int, right_mass: int) -> int:
    raw = _raw_block_count(left_mass) * _raw_block_count(right_mass)
    fixed = _fixed_block_count(left_mass) * _fixed_block_count(right_mass)
    return (raw + fixed) // 2


def _diagonal_rank(left: _Block, right: _Block) -> int:
    right_mass = sum(right)
    left_orbit, moving, flipped = _block_orbit_rank(left)
    if not moving:
        return (
            left_orbit * _orbit_block_count(right_mass)
            + _block_orbit_rank(right)[0]
        )
    if flipped:
        right = _swap_block(right)
    prefix = _fixed_block_count(sum(left)) * _orbit_block_count(right_mass)
    moving_rank = left_orbit - _fixed_block_count(sum(left))
    return (
        prefix
        + moving_rank * _raw_block_count(right_mass)
        + _block_raw_rank(right)
    )


def _diagonal_unrank(
    left_mass: int,
    right_mass: int,
    rank: int,
) -> tuple[_Block, _Block]:
    fixed_block = _fixed_block_count(left_mass) * _orbit_block_count(right_mass)
    if rank < fixed_block:
        left_rank, right_rank = divmod(rank, _orbit_block_count(right_mass))
        return _fixed_blocks(left_mass)[left_rank], _block_orbit_unrank(
            right_mass,
            right_rank,
        )
    remaining = rank - fixed_block
    left_rank, right_rank = divmod(remaining, _raw_block_count(right_mass))
    return _moving_blocks(left_mass)[left_rank], _blocks(right_mass)[right_rank]


def _moving_pair_count(total: int) -> int:
    return sum(_diagonal_count(left, total - left) for left in range(total + 1))


def _moving_pair_rank(left: _Block, right: _Block) -> int:
    left_mass = sum(left)
    total = left_mass + sum(right)
    prefix = sum(
        _diagonal_count(mass, total - mass) for mass in range(left_mass)
    )
    return prefix + _diagonal_rank(left, right)


def _moving_pair_unrank(total: int, rank: int) -> tuple[_Block, _Block]:
    remaining = rank
    for left_mass in range(total + 1):
        block = _diagonal_count(left_mass, total - left_mass)
        if remaining >= block:
            remaining -= block
            continue
        return _diagonal_unrank(left_mass, total - left_mass, remaining)
    raise AssertionError


def _flatten_edges(
    edges: _Edges,
    selected: tuple[tuple[int, int], ...],
) -> _Vector:
    return tuple(
        value for edge in selected for value in edges[_K4_EDGE_INDEX[edge]]
    )


def _edge_blocks(edges: _Edges) -> tuple[_Vector, _Block, _Block]:
    fixed = _flatten_edges(edges, _FIXED_EDGES)
    left = _as_block(_flatten_edges(edges, _LEFT_EDGES))
    right = _as_block(_flatten_edges(edges, _RIGHT_EDGES))
    return fixed, left, right


@cache
def _edge_count(total: int) -> int:
    return sum(
        _composition_count(fixed_mass, _FIXED_EDGE_SCALARS)
        * _moving_pair_count(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def _edge_rank(edges: _Edges) -> int | None:
    if any(value < 0 for edge in edges for value in edge):
        return None
    fixed, left, right = _edge_blocks(edges)
    fixed_mass = sum(fixed)
    pair_mass = sum(left) + sum(right)
    total = fixed_mass + pair_mass
    fixed_rank = _composition_rank(fixed, _FIXED_EDGE_SCALARS)
    assert fixed_rank is not None
    pair_count = _moving_pair_count(pair_mass)
    prefix = sum(
        _composition_count(mass, _FIXED_EDGE_SCALARS)
        * _moving_pair_count(total - mass)
        for mass in range(fixed_mass)
    )
    return prefix + fixed_rank * pair_count + _moving_pair_rank(left, right)


def _as_edge(vector: _Vector) -> _Edge:
    assert len(vector) == _EDGE_COMPONENTS
    first, second, third, fourth = vector
    return first, second, third, fourth


def _assign_edge_vectors(
    fixed: _Vector,
    left: _Block,
    right: _Block,
) -> _Edges:
    fixed_first = _as_edge(fixed[:_EDGE_COMPONENTS])
    fixed_second = _as_edge(fixed[_EDGE_COMPONENTS:])
    left_first = _as_edge(left[:_EDGE_COMPONENTS])
    left_second = _as_edge(left[_EDGE_COMPONENTS:])
    right_first = _as_edge(right[:_EDGE_COMPONENTS])
    right_second = _as_edge(right[_EDGE_COMPONENTS:])
    return (
        fixed_first,
        left_first,
        right_first,
        left_second,
        right_second,
        fixed_second,
    )


def _edge_unrank(total: int, rank: int) -> _Edges | None:
    if rank < 0 or rank >= _edge_count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        pair_mass = total - fixed_mass
        pair_count = _moving_pair_count(pair_mass)
        block = _composition_count(fixed_mass, _FIXED_EDGE_SCALARS) * pair_count
        if remaining >= block:
            remaining -= block
            continue
        fixed_rank, pair_rank = divmod(remaining, pair_count)
        fixed = _composition_unrank(fixed_mass, _FIXED_EDGE_SCALARS, fixed_rank)
        assert fixed is not None
        left, right = _moving_pair_unrank(pair_mass, pair_rank)
        return _assign_edge_vectors(fixed, left, right)
    raise AssertionError


def _ordered_edge(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def _as_edges(values: tuple[_Edge, ...]) -> _Edges:
    assert len(values) == _EDGE_COUNT
    first, second, third, fourth, fifth, sixth = values
    return first, second, third, fourth, fifth, sixth


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
    singletons = tuple(
        sorted((key, index) for key, index in keyed if key != repeated)
    )
    return (
        repeated_indices[0],
        repeated_indices[1],
        singletons[0][1],
        singletons[1][1],
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
    first = spokes[order[2]]
    second = spokes[order[3]]
    canonical_spokes = repeated, repeated, first, second
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
        vector,
        start=0,
        count=_ACTIVE_COUNT,
        width=_SPOKE_COMPONENTS,
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


def test_s6_s5_s4_s2_spoke_rank_matches_small_s4_orbits() -> None:
    """Full S4 relabeling preserves the dense S2 spoke-stratum rank."""
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
            orbit_ranks = {
                _rank(total, _permute_state(state, order)) for order in _S4
            }
            assert orbit_ranks == {rank}
        assert observed == set(range(_class_count(total)))


def test_s6_s5_s4_s2_spoke_rank_exhausts_small_domains() -> None:
    """Every small S2 spoke class receives exactly one dense rank."""
    for total in range(_EXHAUSTIVE_FULL_MASS + 1):
        count = _class_count(total)
        for rank in range(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s5_s4_s2_spoke_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior S2 spoke ranks invert through mass fourteen."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in _sample_ranks(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT


def test_s6_s5_s4_s2_spoke_counts_match_reviewed_sequences() -> None:
    """S2 edge and composed spoke counts match independent decomposition."""
    observed = {
        total: _class_count(total)
        for total in range(_MAXIMUM_MASS + 1)
        if _class_count(total)
    }
    assert observed == _EXPECTED_COUNTS
    assert {
        total: _edge_count(total) for total in range(_MAXIMUM_MASS + 1)
    } == _EXPECTED_EDGE_COUNTS
