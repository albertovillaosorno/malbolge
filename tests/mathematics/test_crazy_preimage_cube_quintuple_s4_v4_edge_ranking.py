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
#   - Dense rank/unrank for pair-valued K4 edges under the 2+2 spoke V4.
# - Must-Not:
#   - Claim complete order-twenty-four or complete S5 ranking.
# - Allows:
#   - Inputs: pair-valued K4 edge assignments of mass zero through fourteen.
#   - Outputs: exact dense V4 edge-orbit rank/unrank.
#   - Side effects: none.
# - Split-When:
#   - The spoke stabilizer is not conjugate to the 2+2 Young subgroup.
# - Merge-When:
#   - Dense order-twenty-four residual ranking owns this V4 edge quotient.
# - Summary:
#   - Rank the 2+2 K4 edge quotient as a row/column-swap matrix.
# - Description:
#   - Quotients row swap first, then ranks the descended column involution on
#     an unordered pair of four-scalar rows.
# - Usage:
#   - Final nontrivial spoke-stratum edge rank for order-twenty-four S4.
# - Defaults:
#   - Direct orbit exhaustion stops at mass three; arithmetic reaches 14.
#

"""Dense V4 ranking for the 2+2 pair-valued K4 edge stratum."""

from __future__ import annotations

from functools import cache
from math import comb
from operator import itemgetter
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Callable

_COMPONENTS = 4
_EDGE_COUNT = 6
_EXHAUSTIVE_MASS = 3
_EXHAUSTIVE_RANK_MASS = 6
_MAXIMUM_MASS = 14
_PAIR_COMPONENTS = 2
_WIDTH_FOURTEEN_COUNT = 1_125_240
_EDGES = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_FIXED_EDGES = ((0, 1), (2, 3))
_ROW_ZERO = ((0, 2), (0, 3))
_ROW_ONE = ((1, 2), (1, 3))
_A = (1, 0, 2, 3)
_B = (0, 1, 3, 2)
_AB = (1, 0, 3, 2)
_t = cast("Callable[[_Row], _Row]", itemgetter(2, 3, 0, 1))

type _EdgePairs = tuple[
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
]
type _Row = tuple[int, int, int, int]
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
def _rows(total: int) -> tuple[_Row, ...]:
    return tuple(
        (value[0], value[1], value[2], value[3])
        for value in _weak_compositions(total, _COMPONENTS)
    )


def _raw_count(total: int) -> int:
    return len(_rows(total))


def _raw_rank(row: _Row) -> int:
    return _rows(sum(row)).index(row)


def _raw_unrank(total: int, rank: int) -> _Row:
    return _rows(total)[rank]


@cache
def _fixed_rows(total: int) -> tuple[_Row, ...]:
    return tuple(row for row in _rows(total) if _t(row) == row)


@cache
def _moving_rows(total: int) -> tuple[_Row, ...]:
    return tuple(
        sorted(
            {
                min(row, _t(row))
                for row in _rows(total)
                if _t(row) != row
            }
        )
    )


def _fixed_count(total: int) -> int:
    return len(_fixed_rows(total))


def _moving_count(total: int) -> int:
    return len(_moving_rows(total))


def _orbit_count(total: int) -> int:
    return _fixed_count(total) + _moving_count(total)


def _orbit_rank(row: _Row) -> tuple[int, bool, bool]:
    total = sum(row)
    fixed = _fixed_rows(total)
    if row in fixed:
        result = fixed.index(row), False, False
    else:
        canonical = min(row, _t(row))
        result = (
            _fixed_count(total) + _moving_rows(total).index(canonical),
            True,
            row != canonical,
        )
    return result


def _orbit_unrank(total: int, rank: int) -> _Row:
    fixed = _fixed_count(total)
    if rank < fixed:
        result = _fixed_rows(total)[rank]
    else:
        result = _moving_rows(total)[rank - fixed]
    return result


def _pair_rank(left: int, right: int, population: int) -> int:
    assert 0 <= left <= right < population
    return left * population - left * (left - 1) // 2 + right - left


def _pair_unrank(rank: int, population: int) -> tuple[int, int]:
    remaining = rank
    for left in range(population):
        block = population - left
        if remaining >= block:
            remaining -= block
            continue
        return left, left + remaining
    raise AssertionError


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


def _diagonal_count(left_mass: int, right_mass: int) -> int:
    raw = _raw_count(left_mass) * _raw_count(right_mass)
    fixed = _fixed_count(left_mass) * _fixed_count(right_mass)
    return (raw + fixed) // 2


def _diagonal_rank(left: _Row, right: _Row) -> int:
    right_mass = sum(right)
    left_orbit, moving, flipped = _orbit_rank(left)
    if not moving:
        result = left_orbit * _orbit_count(right_mass) + _orbit_rank(right)[0]
    else:
        if flipped:
            right = _t(right)
        prefix = _fixed_count(sum(left)) * _orbit_count(right_mass)
        moving_rank = left_orbit - _fixed_count(sum(left))
        result = (
            prefix + moving_rank * _raw_count(right_mass) + _raw_rank(right)
        )
    return result


def _diagonal_unrank(
    left_mass: int,
    right_mass: int,
    rank: int,
) -> tuple[_Row, _Row]:
    fixed_block = _fixed_count(left_mass) * _orbit_count(right_mass)
    if rank < fixed_block:
        left_rank, right_rank = divmod(rank, _orbit_count(right_mass))
        result = _fixed_rows(left_mass)[left_rank], _orbit_unrank(
            right_mass, right_rank
        )
    else:
        remaining = rank - fixed_block
        left_rank, right_rank = divmod(remaining, _raw_count(right_mass))
        result = _moving_rows(left_mass)[left_rank], _raw_unrank(
            right_mass, right_rank
        )
    return result


def _equal_count(total: int) -> int:
    fixed = _fixed_count(total)
    moving = _moving_count(total)
    return comb(fixed + 1, 2) + fixed * moving + moving * (moving + 1)


def _equal_rank_fixed(left: _Row, right: _Row, total: int) -> int:
    fixed = _fixed_rows(total)
    return _pair_rank(fixed.index(left), fixed.index(right), len(fixed))


def _equal_rank_mixed(fixed_row: _Row, moving_row: _Row, total: int) -> int:
    fixed_rank = _fixed_rows(total).index(fixed_row)
    moving_rank = _moving_rows(total).index(min(moving_row, _t(moving_row)))
    return fixed_rank * _moving_count(total) + moving_rank


def _equal_rank_moving(left: _Row, right: _Row, total: int) -> int:
    moving = _moving_rows(total)
    left_canonical = min(left, _t(left))
    right_canonical = min(right, _t(right))
    left_orbit = moving.index(left_canonical)
    right_orbit = moving.index(right_canonical)
    if left_orbit == right_orbit:
        result = 2 * left_orbit + int(left != right)
    else:
        if left_orbit > right_orbit:
            left, right = right, left
            left_orbit, right_orbit = right_orbit, left_orbit
            left_canonical, right_canonical = right_canonical, left_canonical
        parity = int((left != left_canonical) ^ (right != right_canonical))
        prefix = 2 * len(moving)
        result = prefix + 2 * _strict_pair_rank(
            left_orbit, right_orbit, len(moving)
        ) + parity
    return result


def _equal_rank(left: _Row, right: _Row) -> int:
    total = sum(left)
    if _raw_rank(right) < _raw_rank(left):
        left, right = right, left
    left_fixed = _t(left) == left
    right_fixed = _t(right) == right
    fixed_block = comb(_fixed_count(total) + 1, 2)
    mixed_block = _fixed_count(total) * _moving_count(total)
    if left_fixed and right_fixed:
        result = _equal_rank_fixed(left, right, total)
    elif left_fixed or right_fixed:
        fixed_row = left if left_fixed else right
        moving_row = right if left_fixed else left
        result = fixed_block + _equal_rank_mixed(
            fixed_row, moving_row, total
        )
    else:
        result = fixed_block + mixed_block + _equal_rank_moving(
            left, right, total
        )
    return result


def _unrank_distinct_moving(
    total: int,
    rank: int,
) -> tuple[_Row, _Row]:
    moving = _moving_rows(total)
    pair_rank, parity = divmod(rank, 2)
    left_rank, right_rank = _strict_pair_unrank(pair_rank, len(moving))
    left = moving[left_rank]
    right = moving[right_rank]
    return left, _t(right) if parity else right


def _equal_unrank_moving(total: int, rank: int) -> tuple[_Row, _Row]:
    moving = _moving_rows(total)
    same_block = 2 * len(moving)
    if rank < same_block:
        orbit, kind = divmod(rank, 2)
        left = moving[orbit]
        result = (left, left) if kind == 0 else (left, _t(left))
    else:
        result = _unrank_distinct_moving(total, rank - same_block)
    return result


def _equal_unrank(total: int, rank: int) -> tuple[_Row, _Row]:
    fixed = _fixed_rows(total)
    moving = _moving_rows(total)
    fixed_block = comb(len(fixed) + 1, 2)
    mixed_block = len(fixed) * len(moving)
    if rank < fixed_block:
        left, right = _pair_unrank(rank, len(fixed))
        result = fixed[left], fixed[right]
    elif rank < fixed_block + mixed_block:
        fixed_rank, moving_rank = divmod(rank - fixed_block, len(moving))
        result = fixed[fixed_rank], moving[moving_rank]
    else:
        result = _equal_unrank_moving(
            total, rank - fixed_block - mixed_block
        )
    return result


def _row_quotient_count(total: int) -> int:
    result = 0
    for left_mass in range((total + 1) // 2):
        result += _diagonal_count(left_mass, total - left_mass)
    if total % 2 == 0:
        result += _equal_count(total // 2)
    return result


def _row_quotient_rank(left: _Row, right: _Row) -> int:
    if (sum(right), _raw_rank(right)) < (sum(left), _raw_rank(left)):
        left, right = right, left
    left_mass = sum(left)
    right_mass = sum(right)
    total = left_mass + right_mass
    prefix = sum(
        _diagonal_count(mass, total - mass)
        for mass in range(left_mass)
        if mass < total - mass
    )
    if left_mass < right_mass:
        result = prefix + _diagonal_rank(left, right)
    else:
        result = prefix + _equal_rank(left, right)
    return result


def _row_quotient_unrank(total: int, rank: int) -> tuple[_Row, _Row]:
    remaining = rank
    for left_mass in range((total + 1) // 2):
        right_mass = total - left_mass
        block = _diagonal_count(left_mass, right_mass)
        if remaining >= block:
            remaining -= block
            continue
        return _diagonal_unrank(left_mass, right_mass, remaining)
    assert total % 2 == 0
    return _equal_unrank(total // 2, remaining)


@cache
def _class_count(total: int) -> int:
    return sum(
        _raw_count(fixed_mass) * _row_quotient_count(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def _flatten(
    edge_pairs: _EdgePairs,
    edges: tuple[tuple[int, int], ...],
) -> _Row:
    values: list[int] = []
    for edge in edges:
        values.extend(edge_pairs[_EDGE_INDEX[edge]])
    return values[0], values[1], values[2], values[3]


def _rank(edge_pairs: _EdgePairs) -> int | None:
    if any(value < 0 for pair in edge_pairs for value in pair):
        return None
    fixed = _flatten(edge_pairs, _FIXED_EDGES)
    left = _flatten(edge_pairs, _ROW_ZERO)
    right = _flatten(edge_pairs, _ROW_ONE)
    fixed_mass = sum(fixed)
    row_mass = sum(left) + sum(right)
    total = fixed_mass + row_mass
    prefix = sum(
        _raw_count(mass) * _row_quotient_count(total - mass)
        for mass in range(fixed_mass)
    )
    return (
        prefix
        + _raw_rank(fixed) * _row_quotient_count(row_mass)
        + _row_quotient_rank(left, right)
    )


def _choose_fixed_mass(total: int, rank: int) -> tuple[int, int]:
    remaining = rank
    for fixed_mass in range(total + 1):
        block = _raw_count(fixed_mass) * _row_quotient_count(total - fixed_mass)
        if remaining >= block:
            remaining -= block
            continue
        return fixed_mass, remaining
    raise AssertionError


def _assign(
    result: list[tuple[int, int] | None],
    edges: tuple[tuple[int, int], ...],
    row: _Row,
) -> None:
    pairs = ((row[0], row[1]), (row[2], row[3]))
    for edge, pair in zip(edges, pairs, strict=True):
        result[_EDGE_INDEX[edge]] = pair


def _assemble(fixed: _Row, left: _Row, right: _Row) -> _EdgePairs:
    result: list[tuple[int, int] | None] = [None] * _EDGE_COUNT
    _assign(result, _FIXED_EDGES, fixed)
    _assign(result, _ROW_ZERO, left)
    _assign(result, _ROW_ONE, right)
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
    row_mass = total - fixed_mass
    fixed_rank, row_rank = divmod(remaining, _row_quotient_count(row_mass))
    left, right = _row_quotient_unrank(row_mass, row_rank)
    return _assemble(_raw_unrank(fixed_mass, fixed_rank), left, right)


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


def _fixed_scalar_count(total: int) -> int:
    coefficients = [1] + [0] * total
    for length in (1, 1, 1, 1, 2, 2, 2, 2):
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, total - degree + 1, length):
                next_coefficients[degree + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[total]


def _burnside(total: int) -> int:
    raw = comb(total + 11, 11)
    return (raw + 3 * _fixed_scalar_count(total)) // 4


def test_s4_v4_edge_rank_matches_direct_small_orbits() -> None:
    """Small edge assignments collapse exactly to one dense V4 rank."""
    group = ((0, 1, 2, 3), _A, _B, _AB)
    for total in range(_EXHAUSTIVE_MASS + 1):
        observed: dict[int, set[_EdgePairs]] = {}
        for vector in _weak_compositions(total, 2 * _EDGE_COUNT):
            edge_pairs = _edge_pairs(vector)
            rank = _rank(edge_pairs)
            assert rank is not None
            orbit = {_permute(edge_pairs, order) for order in group}
            if rank not in observed:
                observed[rank] = orbit
            assert observed[rank] == orbit
        assert set(observed) == set(range(_class_count(total)))
        assert _class_count(total) == _burnside(total)


def test_s4_v4_edge_rank_exhausts_small_domains() -> None:
    """Every V4 edge class through mass six receives one contiguous rank."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        for rank in range(_class_count(total)):
            edge_pairs = _unrank(total, rank)
            assert edge_pairs is not None
            assert _rank(edge_pairs) == rank


def test_s4_v4_edge_rank_roundtrips_through_mass_fourteen() -> None:
    """Counts and representative ranks match V4 Burnside through mass 14."""
    group = ((0, 1, 2, 3), _A, _B, _AB)
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert count == _burnside(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            edge_pairs = _unrank(total, rank)
            assert edge_pairs is not None
            assert _rank(edge_pairs) == rank
            assert all(
                _rank(_permute(edge_pairs, order)) == rank for order in group
            )
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
