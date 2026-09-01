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
#   - Dense rank/unrank evidence for pair-valued K4 edges under full S4.
# - Must-Not:
#   - Claim dense order-twenty-four K5 residual ranking or complete S5 ranking.
# - Allows:
#   - Inputs: pair-valued K4 edge assignments of mass zero through fourteen.
#   - Outputs: exact dense full-S4 edge-orbit rank/unrank.
#   - Side effects: none.
# - Split-When:
#   - Sorted spoke data is added around this all-equal-spoke core.
# - Merge-When:
#   - Dense order-twenty-four residual ranking owns the same full-S4 edge core.
# - Summary:
#   - Rank full-S4 pair-valued K4 edge orbits by opposite-edge blocks.
# - Description:
#   - Quotients three opposite-edge blocks by even internal flips and S3 block
#     permutations, retaining one parity bit only when all blocks move.
# - Usage:
#   - Hard-core prerequisite for dense order-twenty-four S5 residual ranking.
# - Defaults:
#   - Direct full-S4 orbit exhaustion stops at mass three.
#

"""Dense full-S4 ranking for pair-valued K4 edge assignments."""

from __future__ import annotations

from functools import cache
from itertools import permutations
from math import comb
from operator import itemgetter
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Callable

_ACTIVE = (0, 1, 2, 3)
_BLOCK_COMPONENTS = 4
_BLOCK_COUNT = 3
_EDGE_COUNT = 6
_EXHAUSTIVE_MASS = 3
_EXHAUSTIVE_RANK_MASS = 6
_MAXIMUM_MASS = 14
_PAIR_COMPONENTS = 2
_WIDTH_FOURTEEN_COUNT = 191_180
_EDGES = tuple(
    (left, right)
    for left in _ACTIVE
    for right in _ACTIVE
    if left < right
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_OPPOSITE = (
    ((0, 1), (2, 3)),
    ((0, 2), (1, 3)),
    ((0, 3), (1, 2)),
)
_S4 = tuple(permutations(_ACTIVE))

type _Block = tuple[int, int, int, int]
type _Blocks = tuple[_Block, _Block, _Block]
type _EdgePairs = tuple[
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
]
type _Vector = tuple[int, ...]


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _rep_combination_rank(values: tuple[int, ...], population: int) -> int:
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


def _rep_combination_unrank(
    population: int,
    size: int,
    rank: int,
) -> tuple[int, ...]:
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


_t = cast("Callable[[_Block], _Block]", itemgetter(2, 3, 0, 1))


@cache
def _fixed_representatives(total: int) -> tuple[_Block, ...]:
    if total % 2 != 0:
        return ()
    half = total // 2
    return tuple(
        (pair[0], pair[1], pair[0], pair[1])
        for pair in _weak_compositions(half, _PAIR_COMPONENTS)
    )


@cache
def _moving_representatives(total: int) -> tuple[_Block, ...]:
    representatives: set[_Block] = set()
    for vector in _weak_compositions(total, _BLOCK_COMPONENTS):
        block = vector[0], vector[1], vector[2], vector[3]
        if _t(block) != block:
            representatives.add(min(block, _t(block)))
    return tuple(sorted(representatives))


def _fixed_count(total: int) -> int:
    return len(_fixed_representatives(total))


def _moving_count(total: int) -> int:
    return len(_moving_representatives(total))


def _orbit_count(total: int) -> int:
    return _fixed_count(total) + _moving_count(total)


def _block_orbit_rank(block: _Block) -> tuple[int, bool, bool]:
    total = sum(block)
    fixed = _fixed_representatives(total)
    if block in fixed:
        return fixed.index(block), False, False
    canonical = min(block, _t(block))
    moving = _moving_representatives(total)
    return (
        _fixed_count(total) + moving.index(canonical),
        True,
        block != canonical,
    )


def _block_orbit_unrank(total: int, rank: int, *, flipped: bool) -> _Block:
    fixed = _fixed_count(total)
    if rank < fixed:
        return _fixed_representatives(total)[rank]
    block = _moving_representatives(total)[rank - fixed]
    return _t(block) if flipped else block


def _moving_orbit_unrank(total: int, rank: int, *, flipped: bool) -> _Block:
    block = _moving_representatives(total)[rank]
    return _t(block) if flipped else block


def _mass_triples(total: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (first, second, total - first - second)
        for first in range(total + 1)
        for second in range(first, total + 1)
        if second <= total - first - second
    )


def _multiset_count(populations: tuple[int, int, int]) -> int:
    first, second, third = populations
    if first == second == third:
        result = comb(first + 2, 3)
    elif first == second:
        result = comb(first + 1, 2) * third
    elif second == third:
        result = first * comb(second + 1, 2)
    else:
        result = first * second * third
    return result


def _block_counts(masses: tuple[int, int, int]) -> tuple[int, int]:
    first, second, third = masses
    base = _multiset_count(
        (_orbit_count(first), _orbit_count(second), _orbit_count(third))
    )
    moving = _multiset_count(
        (_moving_count(first), _moving_count(second), _moving_count(third))
    )
    return base, moving


def _mass_block_count(masses: tuple[int, int, int]) -> int:
    base, moving = _block_counts(masses)
    return base + moving


@cache
def _class_count(total: int) -> int:
    return sum(_mass_block_count(masses) for masses in _mass_triples(total))


def _multiset_rank(
    values: tuple[int, int, int],
    populations: tuple[int, int, int],
) -> int:
    first, second, third = populations
    if first == second == third:
        result = _rep_combination_rank(values, first)
    elif first == second:
        result = _rep_combination_rank(values[:2], first) * third + values[2]
    elif second == third:
        result = values[0] * comb(second + 1, 2) + _rep_combination_rank(
            values[1:], second
        )
    else:
        result = (values[0] * second + values[1]) * third + values[2]
    return result


def _unrank_all_equal(population: int, rank: int) -> tuple[int, int, int]:
    values = _rep_combination_unrank(population, _BLOCK_COUNT, rank)
    return values[0], values[1], values[2]


def _unrank_first_equal(
    population: int,
    third: int,
    rank: int,
) -> tuple[int, int, int]:
    pair_rank, last = divmod(rank, third)
    pair = _rep_combination_unrank(population, _PAIR_COMPONENTS, pair_rank)
    return pair[0], pair[1], last


def _unrank_last_equal(
    first: int,
    population: int,
    rank: int,
) -> tuple[int, int, int]:
    pair_count = comb(population + 1, 2)
    first_rank, pair_rank = divmod(rank, pair_count)
    pair = _rep_combination_unrank(population, _PAIR_COMPONENTS, pair_rank)
    assert first_rank < first
    return first_rank, pair[0], pair[1]


def _multiset_unrank(
    populations: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    first, second, third = populations
    if first == second == third:
        result = _unrank_all_equal(first, rank)
    elif first == second:
        result = _unrank_first_equal(first, third, rank)
    elif second == third:
        result = _unrank_last_equal(first, second, rank)
    else:
        first_rank, tail = divmod(rank, second * third)
        second_rank, third_rank = divmod(tail, third)
        result = first_rank, second_rank, third_rank
    return result


def _blocks_from_edges(edge_pairs: _EdgePairs) -> _Blocks:
    blocks: list[_Block] = []
    for left_edge, right_edge in _OPPOSITE:
        left = edge_pairs[_EDGE_INDEX[left_edge]]
        right = edge_pairs[_EDGE_INDEX[right_edge]]
        blocks.append((left[0], left[1], right[0], right[1]))
    return blocks[0], blocks[1], blocks[2]


def _edges_from_blocks(blocks: _Blocks) -> _EdgePairs:
    result: list[tuple[int, int] | None] = [None] * _EDGE_COUNT
    for block, (left_edge, right_edge) in zip(blocks, _OPPOSITE, strict=True):
        result[_EDGE_INDEX[left_edge]] = block[0], block[1]
        result[_EDGE_INDEX[right_edge]] = block[2], block[3]
    first, second, third, fourth, fifth, sixth = result
    assert first is not None
    assert second is not None
    assert third is not None
    assert fourth is not None
    assert fifth is not None
    assert sixth is not None
    return first, second, third, fourth, fifth, sixth


def _canonical_block_data(
    edge_pairs: _EdgePairs,
) -> tuple[tuple[int, int, int], tuple[int, int, int], bool, bool]:
    rows: list[tuple[int, int, bool, bool]] = []
    for block in _blocks_from_edges(edge_pairs):
        orbit, moving, flipped = _block_orbit_rank(block)
        rows.append((sum(block), orbit, moving, flipped))
    rows.sort()
    masses = rows[0][0], rows[1][0], rows[2][0]
    orbits = rows[0][1], rows[1][1], rows[2][1]
    all_moving = all(row[2] for row in rows)
    parity = bool(sum(int(row[3]) for row in rows) % 2)
    return masses, orbits, all_moving, parity


def _extra_rank(
    masses: tuple[int, int, int],
    orbits: tuple[int, int, int],
) -> int:
    moving_values = (
        orbits[0] - _fixed_count(masses[0]),
        orbits[1] - _fixed_count(masses[1]),
        orbits[2] - _fixed_count(masses[2]),
    )
    moving_populations = (
        _moving_count(masses[0]),
        _moving_count(masses[1]),
        _moving_count(masses[2]),
    )
    return _multiset_rank(moving_values, moving_populations)


def _local_rank(
    masses: tuple[int, int, int],
    orbits: tuple[int, int, int],
    *,
    all_moving: bool,
    parity: bool,
) -> int:
    populations = (
        _orbit_count(masses[0]),
        _orbit_count(masses[1]),
        _orbit_count(masses[2]),
    )
    base_rank = _multiset_rank(orbits, populations)
    if not all_moving or not parity:
        return base_rank
    base_count, _ = _block_counts(masses)
    return base_count + _extra_rank(masses, orbits)


def _rank(edge_pairs: _EdgePairs) -> int | None:
    if len(edge_pairs) != _EDGE_COUNT or any(
        value < 0 for pair in edge_pairs for value in pair
    ):
        return None
    total = sum(value for pair in edge_pairs for value in pair)
    masses, orbits, all_moving, parity = _canonical_block_data(edge_pairs)
    prefix = sum(
        _mass_block_count(candidate)
        for candidate in _mass_triples(total)
        if candidate < masses
    )
    return prefix + _local_rank(
        masses,
        orbits,
        all_moving=all_moving,
        parity=parity,
    )


def _choose_mass_block(
    total: int,
    rank: int,
) -> tuple[tuple[int, int, int], int]:
    remaining = rank
    for masses in _mass_triples(total):
        block = _mass_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        return masses, remaining
    raise AssertionError


def _unrank_base(
    masses: tuple[int, int, int],
    rank: int,
) -> _Blocks:
    populations = (
        _orbit_count(masses[0]),
        _orbit_count(masses[1]),
        _orbit_count(masses[2]),
    )
    values = _multiset_unrank(populations, rank)
    return (
        _block_orbit_unrank(masses[0], values[0], flipped=False),
        _block_orbit_unrank(masses[1], values[1], flipped=False),
        _block_orbit_unrank(masses[2], values[2], flipped=False),
    )


def _unrank_extra(
    masses: tuple[int, int, int],
    rank: int,
) -> _Blocks:
    populations = (
        _moving_count(masses[0]),
        _moving_count(masses[1]),
        _moving_count(masses[2]),
    )
    values = _multiset_unrank(populations, rank)
    blocks = [
        _moving_orbit_unrank(mass, value, flipped=False)
        for mass, value in zip(masses, values, strict=True)
    ]
    blocks[-1] = _t(blocks[-1])
    return blocks[0], blocks[1], blocks[2]


def _unrank(total: int, rank: int) -> _EdgePairs | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    masses, local = _choose_mass_block(total, rank)
    base_count, _ = _block_counts(masses)
    blocks = (
        _unrank_base(masses, local)
        if local < base_count
        else _unrank_extra(masses, local - base_count)
    )
    return _edges_from_blocks(blocks)


def _permute_edges(
    edge_pairs: _EdgePairs,
    order: tuple[int, ...],
) -> _EdgePairs:
    result: list[tuple[int, int] | None] = [None] * _EDGE_COUNT
    for source, edge in enumerate(_EDGES):
        left, right = order[edge[0]], order[edge[1]]
        image = (left, right) if left < right else (right, left)
        result[_EDGE_INDEX[image]] = edge_pairs[source]
    first, second, third, fourth, fifth, sixth = result
    assert first is not None
    assert second is not None
    assert third is not None
    assert fourth is not None
    assert fifth is not None
    assert sixth is not None
    return first, second, third, fourth, fifth, sixth


def _edge_pairs_from_vector(vector: _Vector) -> _EdgePairs:
    pairs = tuple(
        (vector[index], vector[index + 1])
        for index in range(0, 2 * _EDGE_COUNT, _PAIR_COMPONENTS)
    )
    return pairs[0], pairs[1], pairs[2], pairs[3], pairs[4], pairs[5]


def _fixed_count_from_cycles(cycles: tuple[int, ...], total: int) -> int:
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


def _edge_cycles(order: tuple[int, ...]) -> tuple[int, ...]:
    permutation: list[int] = []
    for left, right in _EDGES:
        image_left, image_right = order[left], order[right]
        image = (
            (image_left, image_right)
            if image_left < image_right
            else (image_right, image_left)
        )
        permutation.append(_EDGE_INDEX[image])
    unseen = set(range(_EDGE_COUNT))
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


def _burnside_count(total: int) -> int:
    fixed_sum = sum(
        _fixed_count_from_cycles(tuple(sorted(_edge_cycles(order) * 2)), total)
        for order in _S4
    )
    return fixed_sum // len(_S4)


def test_s4_edge_core_rank_matches_direct_small_orbits() -> None:
    """Small pair-valued K4 assignments collapse to one contiguous S4 rank."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        observed: dict[int, set[_EdgePairs]] = {}
        for vector in _weak_compositions(total, 2 * _EDGE_COUNT):
            edge_pairs = _edge_pairs_from_vector(vector)
            rank = _rank(edge_pairs)
            assert rank is not None
            orbit = {_permute_edges(edge_pairs, order) for order in _S4}
            if rank not in observed:
                observed[rank] = orbit
            assert observed[rank] == orbit
        assert set(observed) == set(range(_class_count(total)))
        assert _class_count(total) == _burnside_count(total)


def test_s4_edge_core_rank_exhausts_small_domains() -> None:
    """Every class through mass six receives exactly one roundtripping rank."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        count = _class_count(total)
        for rank in range(count):
            edge_pairs = _unrank(total, rank)
            assert edge_pairs is not None
            assert _rank(edge_pairs) == rank


def test_s4_edge_core_rank_roundtrips_through_mass_fourteen() -> None:
    """Counts and boundary/interior ranks agree with S4 Burnside through 14."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert count == _burnside_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            edge_pairs = _unrank(total, rank)
            assert edge_pairs is not None
            assert _rank(edge_pairs) == rank
            for order in _S4:
                assert _rank(_permute_edges(edge_pairs, order)) == rank
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
