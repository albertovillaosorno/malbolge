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
#   - Dense rank/unrank for pair-valued K4 edges under one residual vertex
#     transposition.
# - Must-Not:
#   - Treat the two swapped edge blocks as independent involutions.
# - Allows:
#   - Inputs: pair-valued K4 edge assignments of mass zero through fourteen.
#   - Outputs: exact dense S2 edge-orbit rank/unrank.
#   - Side effects: none.
# - Split-When:
#   - The spoke stabilizer is not conjugate to the 2+1+1 Young subgroup.
# - Merge-When:
#   - Dense order-twenty-four residual ranking owns this S2 edge quotient.
# - Summary:
#   - Rank the order-two K4 edge quotient by one shared diagonal involution.
# - Description:
#   - Keeps two fixed edge pairs and quotients two four-scalar moving blocks by
#     the same involution orientation.
# - Usage:
#   - Constructive edge rank for the largest nontrivial order-24 spoke stratum.
# - Defaults:
#   - Direct orbit exhaustion stops at mass three.
#

"""Dense S2 ranking for pair-valued K4 edge assignments."""

from __future__ import annotations

from functools import cache
from math import comb
from operator import itemgetter
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Callable

_BLOCK_COMPONENTS = 4
_EDGE_COUNT = 6
_EXHAUSTIVE_MASS = 3
_EXHAUSTIVE_RANK_MASS = 6
_MAXIMUM_MASS = 14
_PAIR_COMPONENTS = 2
_WIDTH_FOURTEEN_COUNT = 2_235_960
_EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_FIXED_EDGES = ((0, 1), (2, 3))
_LEFT_EDGES = ((0, 2), (1, 2))
_RIGHT_EDGES = ((0, 3), (1, 3))
_SWAP = (1, 0, 2, 3)

type _Block = tuple[int, int, int, int]
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


@cache
def _blocks(total: int) -> tuple[_Block, ...]:
    return tuple(
        (vector[0], vector[1], vector[2], vector[3])
        for vector in _weak_compositions(total, _BLOCK_COMPONENTS)
    )


_t = cast("Callable[[_Block], _Block]", itemgetter(2, 3, 0, 1))


@cache
def _fixed_blocks(total: int) -> tuple[_Block, ...]:
    return tuple(block for block in _blocks(total) if _t(block) == block)


@cache
def _moving_blocks(total: int) -> tuple[_Block, ...]:
    return tuple(
        sorted(
            {
                min(block, _t(block))
                for block in _blocks(total)
                if _t(block) != block
            }
        )
    )


def _raw_count(total: int) -> int:
    return len(_blocks(total))


def _fixed_count(total: int) -> int:
    return len(_fixed_blocks(total))


def _moving_count(total: int) -> int:
    return len(_moving_blocks(total))


def _orbit_count(total: int) -> int:
    return _fixed_count(total) + _moving_count(total)


def _raw_rank(block: _Block) -> int:
    return _blocks(sum(block)).index(block)


def _raw_unrank(total: int, rank: int) -> _Block:
    return _blocks(total)[rank]


def _orbit_rank(block: _Block) -> tuple[int, bool, bool]:
    total = sum(block)
    fixed = _fixed_blocks(total)
    if block in fixed:
        return fixed.index(block), False, False
    canonical = min(block, _t(block))
    return (
        _fixed_count(total) + _moving_blocks(total).index(canonical),
        True,
        block != canonical,
    )


def _orbit_unrank(total: int, rank: int) -> _Block:
    fixed = _fixed_count(total)
    if rank < fixed:
        return _fixed_blocks(total)[rank]
    return _moving_blocks(total)[rank - fixed]


def _diagonal_count(left_mass: int, right_mass: int) -> int:
    raw = _raw_count(left_mass) * _raw_count(right_mass)
    fixed = _fixed_count(left_mass) * _fixed_count(right_mass)
    return (raw + fixed) // 2


def _diagonal_rank(left: _Block, right: _Block) -> int:
    left_mass = sum(left)
    right_mass = sum(right)
    left_orbit, moving, flipped = _orbit_rank(left)
    if not moving:
        return left_orbit * _orbit_count(right_mass) + _orbit_rank(right)[0]
    if flipped:
        right = _t(right)
    prefix = _fixed_count(left_mass) * _orbit_count(right_mass)
    moving_rank = left_orbit - _fixed_count(left_mass)
    return prefix + moving_rank * _raw_count(right_mass) + _raw_rank(right)


def _diagonal_unrank(
    left_mass: int,
    right_mass: int,
    rank: int,
) -> tuple[_Block, _Block]:
    fixed_block = _fixed_count(left_mass) * _orbit_count(right_mass)
    if rank < fixed_block:
        left_rank, right_rank = divmod(rank, _orbit_count(right_mass))
        return _fixed_blocks(left_mass)[left_rank], _orbit_unrank(
            right_mass, right_rank
        )
    remaining = rank - fixed_block
    left_rank, right_rank = divmod(remaining, _raw_count(right_mass))
    return _moving_blocks(left_mass)[left_rank], _raw_unrank(
        right_mass, right_rank
    )


def _pair_total(total: int) -> int:
    return sum(_diagonal_count(left, total - left) for left in range(total + 1))


@cache
def _class_count(total: int) -> int:
    return sum(
        _raw_count(fixed_mass) * _pair_total(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def _flatten(
    edge_pairs: _EdgePairs,
    edges: tuple[tuple[int, int], ...],
) -> _Block:
    values: list[int] = []
    for edge in edges:
        values.extend(edge_pairs[_EDGE_INDEX[edge]])
    assert len(values) == _BLOCK_COMPONENTS
    return values[0], values[1], values[2], values[3]


def _rank(edge_pairs: _EdgePairs) -> int | None:
    if len(edge_pairs) != _EDGE_COUNT or any(
        value < 0 for pair in edge_pairs for value in pair
    ):
        return None
    fixed = _flatten(edge_pairs, _FIXED_EDGES)
    left = _flatten(edge_pairs, _LEFT_EDGES)
    right = _flatten(edge_pairs, _RIGHT_EDGES)
    fixed_mass = sum(fixed)
    pair_mass = sum(left) + sum(right)
    total = fixed_mass + pair_mass
    prefix = sum(
        _raw_count(mass) * _pair_total(total - mass)
        for mass in range(fixed_mass)
    )
    local = _raw_rank(fixed) * _pair_total(pair_mass)
    left_mass = sum(left)
    local += sum(
        _diagonal_count(mass, pair_mass - mass) for mass in range(left_mass)
    )
    return prefix + local + _diagonal_rank(left, right)


def _choose_fixed_mass(total: int, rank: int) -> tuple[int, int]:
    remaining = rank
    for fixed_mass in range(total + 1):
        block = _raw_count(fixed_mass) * _pair_total(total - fixed_mass)
        if remaining >= block:
            remaining -= block
            continue
        return fixed_mass, remaining
    raise AssertionError


def _choose_left_mass(total: int, rank: int) -> tuple[int, int]:
    remaining = rank
    for left_mass in range(total + 1):
        block = _diagonal_count(left_mass, total - left_mass)
        if remaining >= block:
            remaining -= block
            continue
        return left_mass, remaining
    raise AssertionError


def _assign_block(
    result: list[tuple[int, int] | None],
    edges: tuple[tuple[int, int], ...],
    block: _Block,
) -> None:
    pairs = ((block[0], block[1]), (block[2], block[3]))
    for edge, pair in zip(edges, pairs, strict=True):
        result[_EDGE_INDEX[edge]] = pair


def _assemble_edges(
    fixed: _Block,
    left: _Block,
    right: _Block,
) -> _EdgePairs:
    result: list[tuple[int, int] | None] = [None] * _EDGE_COUNT
    _assign_block(result, _FIXED_EDGES, fixed)
    _assign_block(result, _LEFT_EDGES, left)
    _assign_block(result, _RIGHT_EDGES, right)
    first, second, third, fourth, fifth, sixth = result
    assert first is not None
    assert second is not None
    assert third is not None
    assert fourth is not None
    assert fifth is not None
    assert sixth is not None
    return first, second, third, fourth, fifth, sixth


def _unrank(total: int, rank: int) -> _EdgePairs | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    fixed_mass, remaining = _choose_fixed_mass(total, rank)
    pair_mass = total - fixed_mass
    fixed_rank, remaining = divmod(remaining, _pair_total(pair_mass))
    left_mass, diagonal_rank = _choose_left_mass(pair_mass, remaining)
    left, right = _diagonal_unrank(
        left_mass, pair_mass - left_mass, diagonal_rank
    )
    return _assemble_edges(
        _raw_unrank(fixed_mass, fixed_rank),
        left,
        right,
    )


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


def _fixed_scalar_count(total: int) -> int:
    coefficients = [1] + [0] * total
    for cycle_length in (1, 1, 1, 1, 2, 2, 2, 2):
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, total - degree + 1, cycle_length):
                next_coefficients[degree + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[total]


def _burnside_count(total: int) -> int:
    raw = comb(total + 11, 11)
    return (raw + _fixed_scalar_count(total)) // 2


def test_s4_s2_edge_rank_matches_direct_small_orbits() -> None:
    """Small edge assignments collapse under the shared transposition."""
    identity = (0, 1, 2, 3)
    for total in range(_EXHAUSTIVE_MASS + 1):
        observed: dict[int, set[_EdgePairs]] = {}
        for vector in _weak_compositions(total, 2 * _EDGE_COUNT):
            edge_pairs = _edge_pairs_from_vector(vector)
            rank = _rank(edge_pairs)
            assert rank is not None
            orbit = {
                _permute_edges(edge_pairs, order) for order in (identity, _SWAP)
            }
            if rank not in observed:
                observed[rank] = orbit
            assert observed[rank] == orbit
        assert set(observed) == set(range(_class_count(total)))
        assert _class_count(total) == _burnside_count(total)


def test_s4_s2_edge_rank_exhausts_small_domains() -> None:
    """Every order-two class through mass six receives one dense rank."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        for rank in range(_class_count(total)):
            edge_pairs = _unrank(total, rank)
            assert edge_pairs is not None
            assert _rank(edge_pairs) == rank


def test_s4_s2_edge_rank_roundtrips_through_mass_fourteen() -> None:
    """Boundary and interior ranks agree with Burnside through mass 14."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert count == _burnside_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            edge_pairs = _unrank(total, rank)
            assert edge_pairs is not None
            assert _rank(edge_pairs) == rank
            assert _rank(_permute_edges(edge_pairs, _SWAP)) == rank
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
