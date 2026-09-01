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
#   - Dense rank/unrank for pair-valued K4 edges under the 3+1 spoke S3.
# - Must-Not:
#   - Claim rank for the 2+2 V4 spoke stratum or complete order-24 ranking.
# - Allows:
#   - Inputs: pair-valued K4 edge assignments of mass zero through fourteen.
#   - Outputs: exact dense S3 edge-orbit rank/unrank.
#   - Side effects: none.
# - Split-When:
#   - The spoke stabilizer is not conjugate to the 3+1 Young subgroup.
# - Merge-When:
#   - Dense order-twenty-four residual ranking owns this S3 edge quotient.
# - Summary:
#   - Rank three four-scalar edge bundles as one weighted S3 multiset.
# - Description:
#   - Pairs each equal vertex's singleton spoke with its opposite triangle edge
#     and ranks the resulting three bundles as one S3 multiset.
# - Usage:
#   - Constructive edge rank for the order-six order-24 spoke stratum.
# - Defaults:
#   - Direct orbit exhaustion stops at mass three.
#

"""Dense S3 ranking for the 3+1 pair-valued K4 edge stratum."""

from __future__ import annotations

from functools import cache
from itertools import permutations
from math import comb

_ACTIVE = (0, 1, 2)
_BLOCK_COMPONENTS = 4
_BLOCK_COUNT = 3
_EDGE_COUNT = 6
_EXHAUSTIVE_MASS = 3
_EXHAUSTIVE_RANK_MASS = 6
_MAXIMUM_MASS = 14
_PAIR_COMPONENTS = 2
_WIDTH_FOURTEEN_COUNT = 750_160
_EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_BUNDLE_EDGES = (
    ((1, 2), (0, 3)),
    ((0, 2), (1, 3)),
    ((0, 1), (2, 3)),
)
_S3 = tuple((*order, 3) for order in permutations(_ACTIVE))

type _Block = tuple[int, int, int, int]
type _Blocks = tuple[_Block, _Block, _Block]
type _EdgePairs = tuple[
    tuple[int, int], tuple[int, int], tuple[int, int],
    tuple[int, int], tuple[int, int], tuple[int, int],
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


@cache
def _blocks(total: int) -> tuple[_Block, ...]:
    return tuple(
        (v[0], v[1], v[2], v[3])
        for v in _weak_compositions(total, _BLOCK_COMPONENTS)
    )


def _block_rank(block: _Block) -> int:
    return _blocks(sum(block)).index(block)


def _block_unrank(total: int, rank: int) -> _Block:
    return _blocks(total)[rank]


def _mass_triples(total: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (a, b, total - a - b)
        for a in range(total + 1)
        for b in range(a, total + 1)
        if b <= total - a - b
    )


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


def _mass_block_count(masses: tuple[int, int, int]) -> int:
    first = len(_blocks(masses[0]))
    second = len(_blocks(masses[1]))
    third = len(_blocks(masses[2]))
    if masses[0] == masses[2]:
        result = comb(first + 2, 3)
    elif masses[0] == masses[1]:
        result = comb(first + 1, 2) * third
    elif masses[1] == masses[2]:
        result = first * comb(second + 1, 2)
    else:
        result = first * second * third
    return result


@cache
def _class_count(total: int) -> int:
    return sum(_mass_block_count(masses) for masses in _mass_triples(total))


def _local_rank(
    masses: tuple[int, int, int],
    values: tuple[int, int, int],
) -> int:
    first = len(_blocks(masses[0]))
    second = len(_blocks(masses[1]))
    third = len(_blocks(masses[2]))
    if masses[0] == masses[2]:
        result = _rep_rank(values, first)
    elif masses[0] == masses[1]:
        result = _rep_rank(values[:2], first) * third + values[2]
    elif masses[1] == masses[2]:
        result = values[0] * comb(second + 1, 2) + _rep_rank(
            values[1:], second
        )
    else:
        result = (values[0] * second + values[1]) * third + values[2]
    return result


def _unrank_equal_first(
    first: int,
    third: int,
    rank: int,
) -> tuple[int, int, int]:
    pair_rank, last = divmod(rank, third)
    pair = _rep_unrank(first, _PAIR_COMPONENTS, pair_rank)
    return pair[0], pair[1], last


def _unrank_equal_last(
    second: int,
    rank: int,
) -> tuple[int, int, int]:
    pair_count = comb(second + 1, 2)
    head, pair_rank = divmod(rank, pair_count)
    pair = _rep_unrank(second, _PAIR_COMPONENTS, pair_rank)
    return head, pair[0], pair[1]


def _local_unrank(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    first = len(_blocks(masses[0]))
    second = len(_blocks(masses[1]))
    third = len(_blocks(masses[2]))
    if masses[0] == masses[2]:
        values = _rep_unrank(first, _BLOCK_COUNT, rank)
        result = values[0], values[1], values[2]
    elif masses[0] == masses[1]:
        result = _unrank_equal_first(first, third, rank)
    elif masses[1] == masses[2]:
        result = _unrank_equal_last(second, rank)
    else:
        head, tail = divmod(rank, second * third)
        middle, last = divmod(tail, third)
        result = head, middle, last
    return result


def _blocks_from_edges(edge_pairs: _EdgePairs) -> _Blocks:
    result: list[_Block] = []
    for left_edge, right_edge in _BUNDLE_EDGES:
        left = edge_pairs[_EDGE_INDEX[left_edge]]
        right = edge_pairs[_EDGE_INDEX[right_edge]]
        result.append((left[0], left[1], right[0], right[1]))
    return result[0], result[1], result[2]


def _edges_from_blocks(blocks: _Blocks) -> _EdgePairs:
    result: list[tuple[int, int] | None] = [None] * _EDGE_COUNT
    for block, edges in zip(blocks, _BUNDLE_EDGES, strict=True):
        result[_EDGE_INDEX[edges[0]]] = block[0], block[1]
        result[_EDGE_INDEX[edges[1]]] = block[2], block[3]
    first, second, third, fourth, fifth, sixth = result
    assert first is not None
    assert second is not None
    assert third is not None
    assert fourth is not None
    assert fifth is not None
    assert sixth is not None
    return first, second, third, fourth, fifth, sixth


def _block_key(block: _Block) -> tuple[int, int]:
    return sum(block), _block_rank(block)


def _rank(edge_pairs: _EdgePairs) -> int | None:
    if any(value < 0 for pair in edge_pairs for value in pair):
        return None
    blocks = sorted(_blocks_from_edges(edge_pairs), key=_block_key)
    masses = sum(blocks[0]), sum(blocks[1]), sum(blocks[2])
    values = (
        _block_rank(blocks[0]),
        _block_rank(blocks[1]),
        _block_rank(blocks[2]),
    )
    total = sum(masses)
    prefix = sum(
        _mass_block_count(candidate)
        for candidate in _mass_triples(total)
        if candidate < masses
    )
    return prefix + _local_rank(masses, values)


def _choose_mass(total: int, rank: int) -> tuple[tuple[int, int, int], int]:
    remaining = rank
    for masses in _mass_triples(total):
        block = _mass_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        return masses, remaining
    raise AssertionError


def _unrank(total: int, rank: int) -> _EdgePairs | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    masses, local = _choose_mass(total, rank)
    values = _local_unrank(masses, local)
    blocks = (
        _block_unrank(masses[0], values[0]),
        _block_unrank(masses[1], values[1]),
        _block_unrank(masses[2], values[2]),
    )
    return _edges_from_blocks(blocks)


def _permute(edge_pairs: _EdgePairs, order: tuple[int, ...]) -> _EdgePairs:
    result: list[tuple[int, int] | None] = [None] * _EDGE_COUNT
    for source, edge in enumerate(_EDGES):
        a, b = order[edge[0]], order[edge[1]]
        image = (a, b) if a < b else (b, a)
        result[_EDGE_INDEX[image]] = edge_pairs[source]
    first, second, third, fourth, fifth, sixth = result
    assert first is not None
    assert second is not None
    assert third is not None
    assert fourth is not None
    assert fifth is not None
    assert sixth is not None
    return first, second, third, fourth, fifth, sixth


def _edge_pairs(vector: _Vector) -> _EdgePairs:
    pairs = tuple((vector[i], vector[i + 1]) for i in range(0, 12, 2))
    return pairs[0], pairs[1], pairs[2], pairs[3], pairs[4], pairs[5]


def _fixed(cycles: tuple[int, ...], total: int) -> int:
    coefficients = [1] + [0] * total
    for length in cycles:
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, total - degree + 1, length):
                next_coefficients[degree + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[total]


def _burnside(total: int) -> int:
    identity = comb(total + 11, 11)
    transposition = _fixed((1,) * 4 + (2,) * 4, total)
    three_cycle = _fixed((3,) * 4, total)
    return (identity + 3 * transposition + 2 * three_cycle) // 6


def test_s4_s3_edge_rank_matches_direct_small_orbits() -> None:
    """Small assignments collapse to one S3 bundle-multiset rank."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        observed: dict[int, set[_EdgePairs]] = {}
        for vector in _weak_compositions(total, 2 * _EDGE_COUNT):
            edge_pairs = _edge_pairs(vector)
            rank = _rank(edge_pairs)
            assert rank is not None
            orbit = {_permute(edge_pairs, order) for order in _S3}
            if rank not in observed:
                observed[rank] = orbit
            assert observed[rank] == orbit
        assert set(observed) == set(range(_class_count(total)))
        assert _class_count(total) == _burnside(total)


def test_s4_s3_edge_rank_exhausts_small_domains() -> None:
    """Every S3 edge class through mass six receives one contiguous rank."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        for rank in range(_class_count(total)):
            edge_pairs = _unrank(total, rank)
            assert edge_pairs is not None
            assert _rank(edge_pairs) == rank


def test_s4_s3_edge_rank_roundtrips_through_mass_fourteen() -> None:
    """Counts and representative ranks match S3 Burnside through mass 14."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert count == _burnside(total)
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            edge_pairs = _unrank(total, rank)
            assert edge_pairs is not None
            assert _rank(edge_pairs) == rank
            assert all(
                _rank(_permute(edge_pairs, order)) == rank for order in _S3
            )
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
