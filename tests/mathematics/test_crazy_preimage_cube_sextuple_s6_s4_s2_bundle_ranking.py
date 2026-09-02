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
#   - Dense rank/unrank for the second-layer S2 slice of the (4,1,1) S6 stratum.
# - Must-Not:
#   - Claim ranking for V4, S3, or S4 second-layer stabilizers.
# - Allows:
#   - Inputs: sextuple mass zero through fourteen with bundle partition (2,1,1).
#   - Outputs: dense ranks after one repeated bundle fixes an S2 stabilizer.
#   - Side effects: none.
# - Split-When:
#   - Another second-layer S4 stabilizer receives constructive rank/unrank.
# - Merge-When:
#   - Complete dense ranking owns the full (4,1,1) S6 stratum.
# - Summary:
#   - Rank repeated/singleton bundles and one shared K4-edge involution.
# - Description:
#   - Two fixed four-scalar edges plus two eight-scalar blocks share one swap.
# - Usage:
#   - Largest remaining constructive second-layer slice of the S4 S6 stratum.
# - Defaults:
#   - Direct abstract S4 orbits stop at mass two; full exhaustion stops at six.
#

"""Dense S2 second-layer ranking for the S6 (4,1,1) stratum."""

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

_ARITY = 6
_ACTIVE_COUNT = 4
_ACTIVE = tuple(range(_ACTIVE_COUNT))
_FIXED_COMPONENTS = 4
_VERTEX_COMPONENTS = 6
_EDGE_COMPONENTS = 4
_EDGE_COUNT = 6
_FIXED_EDGE_SCALARS = 2 * _EDGE_COMPONENTS
_MOVING_BLOCK_COMPONENTS = 2 * _EDGE_COMPONENTS
_MAXIMUM_MASS = 14
_EXHAUSTIVE_FULL_MASS = 6
_EXHAUSTIVE_ORBIT_MASS = 2
_TOP_PARTITION = (4, 1, 1)
_SECOND_PARTITION = (2, 1, 1)
_REPEAT_COUNT = 2
_SINGLE_COUNT = 1
_WIDTH_FOURTEEN_COUNT = 113_906_741_533
_EXPECTED_COUNTS = {
    4: 15,
    5: 546,
    6: 10_443,
    7: 140_568,
    8: 1_488_547,
    9: 13_128_302,
    10: 99_872_114,
    11: 671_354_392,
    12: 4_059_716_439,
    13: 22_392_012_768,
    14: 113_906_741_533,
}
_K4_EDGES = tuple(
    (left, right)
    for left in _ACTIVE
    for right in _ACTIVE
    if left < right
)
_K4_EDGE_INDEX = {edge: index for index, edge in enumerate(_K4_EDGES)}
_S4 = tuple(permutations(_ACTIVE))
_FIXED_EDGES = ((0, 1), (2, 3))
_LEFT_EDGES = ((0, 2), (1, 2))
_RIGHT_EDGES = ((0, 3), (1, 3))

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Vector = tuple[int, ...]
type _Bundle = tuple[int, int, int, int, int, int]
type _Bundles = tuple[_Bundle, _Bundle, _Bundle, _Bundle]
type _Edge = tuple[int, int, int, int]
type _Edges = tuple[_Edge, _Edge, _Edge, _Edge, _Edge, _Edge]
type _Block = tuple[int, int, int, int, int, int, int, int]
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


def _bundle_mass_triples(total: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (repeated, first, total - 2 * repeated - first)
        for repeated in range(total // 2 + 1)
        for first in range(total - 2 * repeated + 1)
        if first <= total - 2 * repeated - first
    )


def _bundle_block_count(masses: tuple[int, int, int]) -> int:
    repeated, first, second = masses
    repeated_count = _raw_bundle_count(repeated)
    first_count = _raw_bundle_count(first)
    second_count = _raw_bundle_count(second)
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
def _bundle_count(total: int) -> int:
    return sum(
        _bundle_block_count(masses) for masses in _bundle_mass_triples(total)
    )


def _rank_unequal_singletons(
    masses: tuple[int, int, int],
    ranks: tuple[int, int, int],
) -> int:
    repeated_mass, first_mass, second_mass = masses
    repeated_rank, first_rank, second_rank = ranks
    first_count = _raw_bundle_count(first_mass)
    second_count = _raw_bundle_count(second_mass)
    if repeated_mass == first_mass:
        first_rank = _filtered_rank(first_rank, repeated_rank)
        first_count -= 1
    if repeated_mass == second_mass:
        second_rank = _filtered_rank(second_rank, repeated_rank)
        second_count -= 1
    return (
        (repeated_rank * first_count + first_rank) * second_count
        + second_rank
    )


def _rank_equal_singletons(
    repeated_mass: int,
    singleton_mass: int,
    ranks: tuple[int, int, int],
) -> int:
    repeated_rank, first_rank, second_rank = ranks
    population = _raw_bundle_count(singleton_mass)
    if repeated_mass == singleton_mass:
        first_rank = _filtered_rank(first_rank, repeated_rank)
        second_rank = _filtered_rank(second_rank, repeated_rank)
        population -= 1
    pair_rank = _strict_pair_rank(first_rank, second_rank, population)
    return repeated_rank * comb(population, _REPEAT_COUNT) + pair_rank


def _bundle_local_rank(
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
    first_count = _raw_bundle_count(first_mass)
    second_count = _raw_bundle_count(second_mass)
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
    population = _raw_bundle_count(singleton_mass)
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


def _bundle_local_unrank(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    if masses[1] < masses[2]:
        return _unrank_unequal_singletons(masses, rank)
    return _unrank_equal_singletons(masses[0], masses[1], rank)


def _bundle_rank_data(
    bundles: _Bundles,
) -> tuple[tuple[int, int, int], tuple[int, int, int]] | None:
    keys = tuple(_bundle_key(bundle) for bundle in bundles)
    multiplicities = Counter(keys)
    partition = tuple(sorted(multiplicities.values(), reverse=True))
    if partition != _SECOND_PARTITION:
        return None
    repeated_key = next(
        key
        for key, count in multiplicities.items()
        if count == _REPEAT_COUNT
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


def _bundle_rank(bundles: _Bundles) -> int | None:
    data = _bundle_rank_data(bundles)
    if data is None:
        return None
    masses, ranks = data
    total = sum(sum(bundle) for bundle in bundles)
    prefix = sum(
        _bundle_block_count(candidate)
        for candidate in _bundle_mass_triples(total)
        if candidate < masses
    )
    return prefix + _bundle_local_rank(masses, ranks)


def _bundle_unrank(total: int, rank: int) -> _Bundles | None:
    if rank < 0 or rank >= _bundle_count(total):
        return None
    remaining = rank
    for masses in _bundle_mass_triples(total):
        block = _bundle_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        ranks = _bundle_local_unrank(masses, remaining)
        values: list[_Bundle] = []
        for mass, raw_rank in zip(masses, ranks, strict=True):
            vector = _composition_unrank(mass, _VERTEX_COMPONENTS, raw_rank)
            assert vector is not None
            values.append(_as_bundle(vector))
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
        sorted(
            {
                min(block, _swap_block(block))
                for block in _blocks(total)
                if _swap_block(block) != block
            }
        )
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
    return sum(
        _diagonal_count(left, total - left) for left in range(total + 1)
    )


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
        value
        for edge in selected
        for value in edges[_K4_EDGE_INDEX[edge]]
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
    first = bundles[order[2]]
    second = bundles[order[3]]
    canonical_bundles = repeated, repeated, first, second
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
    permuted_bundles = tuple(
        bundles[inverse[destination]] for destination in _ACTIVE
    )
    permuted_edges = tuple(
        edges[_K4_EDGE_INDEX[_ordered_edge(inverse[left], inverse[right])]]
        for left, right in _K4_EDGES
    )
    b0, b1, b2, b3 = permuted_bundles
    return fixed, (b0, b1, b2, b3), _as_edges(permuted_edges)


def test_s6_s4_s2_bundle_rank_matches_small_s4_orbits() -> None:
    """Repeated-bundle orientation agrees across raw S4 presentations."""
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


def test_s6_s4_s2_bundle_rank_exhausts_small_full_domains() -> None:
    """Every admitted class through mass six receives one contiguous rank."""
    for total in range(_EXHAUSTIVE_FULL_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s4_s2_bundle_rank_roundtrips_through_fourteen() -> None:
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


def test_s6_s4_s2_bundle_counts_match_reviewed_sequence() -> None:
    """Mass-four-through-fourteen counts match the nested factorization."""
    observed = {
        mass: _class_count(mass)
        for mass in range(_MAXIMUM_MASS + 1)
        if _class_count(mass) != 0
    }
    assert observed == _EXPECTED_COUNTS
