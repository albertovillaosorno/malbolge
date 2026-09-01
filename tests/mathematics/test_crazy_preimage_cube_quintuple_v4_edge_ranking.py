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
#   - Dense rank/unrank evidence for pair-valued K5 edges under the residual
#     V4=S2xS2 stabilizer of two disjoint equal vertex-pair blocks.
# - Must-Not:
#   - Claim ranking for larger residual stabilizers or complete S5 classes.
# - Allows:
#   - Inputs: residual edge-pair mass zero through fourteen.
#   - Outputs: exact dense V4 rank/unrank.
#   - Side effects: none.
# - Split-When:
#   - A residual stabilizer is not conjugate to V4.
# - Merge-When:
#   - Dense S5 ranking owns the same nested diagonal-involution construction.
# - Summary:
#   - Densely rank residual V4 pair-valued K5 edge orbits.
# - Description:
#   - Quotients the first row swap, then ranks the descended column swap by a
#     fixed/nonfixed diagonal-orbit decomposition.
# - Usage:
#   - Constructive prerequisite for S5 strata with stabilizer order four.
# - Defaults:
#   - Direct V4 orbit exhaustion stops at mass three; arithmetic reaches 14.
#

"""Dense residual V4 ranking for pair-valued K5 edge assignments."""

from __future__ import annotations

from functools import cache
from math import comb

_COMPONENTS_PER_PAIR = 2
_EDGE_COUNT = 10
_EXHAUSTIVE_MASS = 3
_MAXIMUM_MASS = 14
_WIDTH_FOURTEEN_COUNT = 205_482_000
_EDGES = tuple(
    (left, right)
    for left in range(5)
    for right in range(left + 1, 5)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_A = (1, 0, 2, 3, 4)
_B = (0, 1, 3, 2, 4)
_CORE_EDGES = ((0, 1), (2, 3))
_COLUMN_EDGES = ((2, 4), (3, 4))
_ROW_ZERO_EDGES = ((0, 4), (0, 2), (0, 3))
_ROW_ONE_EDGES = ((1, 4), (1, 2), (1, 3))
_CORE_COMPONENTS = 4
_SIDE_COMPONENTS = 2
_ROW_COMPONENTS = 6
_X_COMPONENTS = 8

# X is core[4] plus two column-margin pairs[2+2].
# Y is an unordered pair of row bundles[6+6] after the first S2 quotient.
type _Pair = tuple[int, int]
type _EdgePairs = tuple[_Pair, ...]
type _Vector = tuple[int, ...]
type _StateParts = tuple[_Vector, _Vector, _Vector, _Vector, _Vector]


def _composition_count(total: int, parts: int) -> int:
    if total < 0 or parts <= 0:
        return 0
    return comb(total + parts - 1, parts - 1)


def _composition_rank(vector: _Vector, total: int) -> int | None:
    if not vector or any(value < 0 for value in vector) or sum(vector) != total:
        return None
    rank = 0
    remaining = total
    for index, value in enumerate(vector[:-1]):
        tail_parts = len(vector) - index - 1
        for earlier in range(value):
            rank += _composition_count(remaining - earlier, tail_parts)
        remaining -= value
    return rank


def _composition_unrank(total: int, parts: int, rank: int) -> _Vector | None:
    if rank < 0 or rank >= _composition_count(total, parts):
        return None
    remaining_rank = rank
    remaining_total = total
    values: list[int] = []
    for index in range(parts - 1):
        tail_parts = parts - index - 1
        for value in range(remaining_total + 1):
            block = _composition_count(remaining_total - value, tail_parts)
            if remaining_rank >= block:
                remaining_rank -= block
                continue
            values.append(value)
            remaining_total -= value
            break
    values.append(remaining_total)
    return tuple(values)


def _vector_key(vector: _Vector) -> tuple[int, int]:
    total = sum(vector)
    rank = _composition_rank(vector, total)
    assert rank is not None
    return total, rank


def _multiset_pair_count(total: int, parts: int) -> int:
    count = 0
    for left_mass in range((total + 1) // 2):
        right_mass = total - left_mass
        count += _composition_count(left_mass, parts) * _composition_count(
            right_mass,
            parts,
        )
    if total % 2 == 0:
        half = total // 2
        population = _composition_count(half, parts)
        count += population * (population + 1) // 2
    return count


def _equal_pair_rank(left: int, right: int, population: int) -> int:
    assert 0 <= left <= right < population
    return left * population - left * (left - 1) // 2 + right - left


def _equal_pair_unrank(rank: int, population: int) -> tuple[int, int]:
    remaining = rank
    for left in range(population):
        block = population - left
        if remaining >= block:
            remaining -= block
            continue
        return left, left + remaining
    raise AssertionError


def _multiset_pair_rank(
    left: _Vector,
    right: _Vector,
    parts: int,
) -> int | None:
    result: int | None = None
    valid = (
        len(left) == parts
        and len(right) == parts
        and not any(value < 0 for value in (*left, *right))
    )
    if valid:
        if _vector_key(right) < _vector_key(left):
            left, right = right, left
        keys = _vector_key(left), _vector_key(right)
        total = keys[0][0] + keys[1][0]
        prefix = sum(
            _composition_count(mass, parts)
            * _composition_count(total - mass, parts)
            for mass in range(keys[0][0])
            if mass < total - mass
        )
        if keys[0][0] < keys[1][0]:
            result = (
                prefix
                + keys[0][1] * _composition_count(keys[1][0], parts)
                + keys[1][1]
            )
        else:
            population = _composition_count(keys[0][0], parts)
            result = prefix + _equal_pair_rank(
                keys[0][1], keys[1][1], population
            )
    return result


def _unrank_unequal_multiset_pair(
    total: int,
    parts: int,
    rank: int,
) -> tuple[_Vector, _Vector, int] | None:
    remaining = rank
    for left_mass in range((total + 1) // 2):
        right_mass = total - left_mass
        left_count = _composition_count(left_mass, parts)
        right_count = _composition_count(right_mass, parts)
        block = left_count * right_count
        if remaining >= block:
            remaining -= block
            continue
        left_rank, right_rank = divmod(remaining, right_count)
        left = _composition_unrank(left_mass, parts, left_rank)
        right = _composition_unrank(right_mass, parts, right_rank)
        assert left is not None
        assert right is not None
        return left, right, -1
    return None


def _multiset_pair_unrank(
    total: int,
    parts: int,
    rank: int,
) -> tuple[_Vector, _Vector] | None:
    if rank < 0 or rank >= _multiset_pair_count(total, parts):
        return None
    unequal = _unrank_unequal_multiset_pair(total, parts, rank)
    if unequal is not None:
        return unequal[0], unequal[1]
    unequal_count = sum(
        _composition_count(mass, parts)
        * _composition_count(total - mass, parts)
        for mass in range((total + 1) // 2)
        if mass < total - mass
    )
    half = total // 2
    population = _composition_count(half, parts)
    pair = _equal_pair_unrank(rank - unequal_count, population)
    left = _composition_unrank(half, parts, pair[0])
    right = _composition_unrank(half, parts, pair[1])
    assert left is not None
    assert right is not None
    return left, right


# ---- X: 8 scalar components, with b swapping two 2-component margins. ----


def _x_count(total: int) -> int:
    return _composition_count(total, _X_COMPONENTS)


@cache
def _x_fixed_count(total: int) -> int:
    return sum(
        _composition_count(core_mass, _CORE_COMPONENTS)
        * _composition_count((total - core_mass) // 2, _SIDE_COMPONENTS)
        for core_mass in range(total + 1)
        if (total - core_mass) % 2 == 0
    )


def _x_nonfixed_orbit_count(total: int) -> int:
    return (_x_count(total) - _x_fixed_count(total)) // 2


def _side_nonfixed_count(total: int) -> int:
    count = 0
    for left_mass in range((total + 1) // 2):
        right_mass = total - left_mass
        count += _composition_count(left_mass, _SIDE_COMPONENTS) * (
            _composition_count(right_mass, _SIDE_COMPONENTS)
        )
    if total % 2 == 0:
        half = total // 2
        population = _composition_count(half, _SIDE_COMPONENTS)
        count += population * (population - 1) // 2
    return count


def _side_nonfixed_rank(left: _Vector, right: _Vector) -> int | None:
    result: int | None = None
    if len(left) == _SIDE_COMPONENTS and len(right) == _SIDE_COMPONENTS:
        if _vector_key(right) < _vector_key(left):
            left, right = right, left
        if left != right:
            left_mass, left_rank = _vector_key(left)
            right_mass, right_rank = _vector_key(right)
            total = left_mass + right_mass
            prefix = sum(
                _composition_count(mass, _SIDE_COMPONENTS)
                * _composition_count(total - mass, _SIDE_COMPONENTS)
                for mass in range(left_mass)
                if mass < total - mass
            )
            if left_mass < right_mass:
                result = (
                    prefix
                    + left_rank
                    * _composition_count(right_mass, _SIDE_COMPONENTS)
                    + right_rank
                )
            else:
                population = _composition_count(
                    left_mass, _SIDE_COMPONENTS
                )
                result = (
                    prefix
                    + left_rank * (2 * population - left_rank - 1) // 2
                    + right_rank
                    - left_rank
                    - 1
                )
    return result


def _unrank_unequal_sides(
    total: int,
    rank: int,
) -> tuple[_Vector, _Vector] | None:
    remaining = rank
    for left_mass in range((total + 1) // 2):
        right_mass = total - left_mass
        left_count = _composition_count(left_mass, _SIDE_COMPONENTS)
        right_count = _composition_count(right_mass, _SIDE_COMPONENTS)
        block = left_count * right_count
        if remaining >= block:
            remaining -= block
            continue
        left_rank, right_rank = divmod(remaining, right_count)
        left = _composition_unrank(left_mass, _SIDE_COMPONENTS, left_rank)
        right = _composition_unrank(right_mass, _SIDE_COMPONENTS, right_rank)
        assert left is not None
        assert right is not None
        return left, right
    return None


def _side_nonfixed_unrank(
    total: int,
    rank: int,
) -> tuple[_Vector, _Vector] | None:
    if rank < 0 or rank >= _side_nonfixed_count(total):
        return None
    unequal = _unrank_unequal_sides(total, rank)
    if unequal is not None:
        return unequal
    unequal_count = sum(
        _composition_count(mass, _SIDE_COMPONENTS)
        * _composition_count(total - mass, _SIDE_COMPONENTS)
        for mass in range((total + 1) // 2)
        if mass < total - mass
    )
    half = total // 2
    population = _composition_count(half, _SIDE_COMPONENTS)
    remaining = rank - unequal_count
    for left_rank in range(population):
        block = population - left_rank - 1
        if remaining >= block:
            remaining -= block
            continue
        right_rank = left_rank + 1 + remaining
        left = _composition_unrank(half, _SIDE_COMPONENTS, left_rank)
        right = _composition_unrank(half, _SIDE_COMPONENTS, right_rank)
        assert left is not None
        assert right is not None
        return left, right
    raise AssertionError


def _x_fixed_rank(core: _Vector, side: _Vector) -> int | None:
    if len(core) != _CORE_COMPONENTS or len(side) != _SIDE_COMPONENTS:
        return None
    core_mass = sum(core)
    side_mass = sum(side)
    total = core_mass + 2 * side_mass
    core_rank = _composition_rank(core, core_mass)
    side_rank = _composition_rank(side, side_mass)
    if core_rank is None or side_rank is None:
        return None
    prefix = sum(
        _composition_count(total - 2 * mass, _CORE_COMPONENTS)
        * _composition_count(mass, _SIDE_COMPONENTS)
        for mass in range(side_mass)
        if 2 * mass <= total
    )
    return (
        prefix
        + core_rank * _composition_count(side_mass, _SIDE_COMPONENTS)
        + side_rank
    )


def _x_fixed_unrank(total: int, rank: int) -> tuple[_Vector, _Vector] | None:
    if rank < 0 or rank >= _x_fixed_count(total):
        return None
    remaining = rank
    for side_mass in range(total // 2 + 1):
        core_mass = total - 2 * side_mass
        side_count = _composition_count(side_mass, _SIDE_COMPONENTS)
        core_count = _composition_count(core_mass, _CORE_COMPONENTS)
        block = core_count * side_count
        if remaining >= block:
            remaining -= block
            continue
        core_rank, side_rank = divmod(remaining, side_count)
        core = _composition_unrank(core_mass, _CORE_COMPONENTS, core_rank)
        side = _composition_unrank(side_mass, _SIDE_COMPONENTS, side_rank)
        assert core is not None
        assert side is not None
        return core, side
    raise AssertionError


def _x_nonfixed_rank(
    core: _Vector,
    left: _Vector,
    right: _Vector,
) -> tuple[int, bool] | None:
    if len(core) != _CORE_COMPONENTS:
        return None
    flipped = _vector_key(right) < _vector_key(left)
    if flipped:
        left, right = right, left
    side_rank = _side_nonfixed_rank(left, right)
    core_mass = sum(core)
    core_rank = _composition_rank(core, core_mass)
    if side_rank is None or core_rank is None:
        return None
    side_mass = sum(left) + sum(right)
    total = core_mass + side_mass
    prefix = sum(
        _composition_count(mass, _CORE_COMPONENTS)
        * _side_nonfixed_count(total - mass)
        for mass in range(core_mass)
    )
    rank = (
        prefix
        + core_rank * _side_nonfixed_count(side_mass)
        + side_rank
    )
    return rank, flipped


def _x_nonfixed_unrank(
    total: int,
    rank: int,
) -> tuple[_Vector, _Vector, _Vector] | None:
    if rank < 0 or rank >= _x_nonfixed_orbit_count(total):
        return None
    remaining = rank
    for core_mass in range(total + 1):
        side_mass = total - core_mass
        side_count = _side_nonfixed_count(side_mass)
        core_count = _composition_count(core_mass, _CORE_COMPONENTS)
        block = core_count * side_count
        if remaining >= block:
            remaining -= block
            continue
        core_rank, side_rank = divmod(remaining, side_count)
        core = _composition_unrank(core_mass, _CORE_COMPONENTS, core_rank)
        sides = _side_nonfixed_unrank(side_mass, side_rank)
        assert core is not None
        assert sides is not None
        return core, sides[0], sides[1]
    raise AssertionError


# ---- Z row bundle and b's internal involution t. ----


def _t(vector: _Vector) -> _Vector:
    assert len(vector) == _ROW_COMPONENTS
    return vector[0:2] + vector[4:6] + vector[2:4]


def _z_count(total: int) -> int:
    return _composition_count(total, _ROW_COMPONENTS)


@cache
def _z_fixed_count(total: int) -> int:
    return sum(
        _composition_count(margin_mass, 2)
        * _composition_count((total - margin_mass) // 2, 2)
        for margin_mass in range(total + 1)
        if (total - margin_mass) % 2 == 0
    )


def _z_nonfixed_orbit_count(total: int) -> int:
    return (_z_count(total) - _z_fixed_count(total)) // 2


def _z_fixed_rank(vector: _Vector) -> int | None:
    if len(vector) != _ROW_COMPONENTS or _t(vector) != vector:
        return None
    margin = vector[0:2]
    cell = vector[2:4]
    margin_mass = sum(margin)
    cell_mass = sum(cell)
    total = margin_mass + 2 * cell_mass
    margin_rank = _composition_rank(margin, margin_mass)
    cell_rank = _composition_rank(cell, cell_mass)
    assert margin_rank is not None
    assert cell_rank is not None
    prefix = sum(
        _composition_count(mass, 2)
        * _composition_count((total - mass) // 2, 2)
        for mass in range(margin_mass)
        if (total - mass) % 2 == 0
    )
    return prefix + margin_rank * _composition_count(cell_mass, 2) + cell_rank


def _z_fixed_unrank(total: int, rank: int) -> _Vector | None:
    if rank < 0 or rank >= _z_fixed_count(total):
        return None
    remaining = rank
    for margin_mass in range(total + 1):
        if (total - margin_mass) % 2 != 0:
            continue
        cell_mass = (total - margin_mass) // 2
        margin_count = _composition_count(margin_mass, 2)
        cell_count = _composition_count(cell_mass, 2)
        block = margin_count * cell_count
        if remaining >= block:
            remaining -= block
            continue
        margin_rank, cell_rank = divmod(remaining, cell_count)
        margin = _composition_unrank(margin_mass, 2, margin_rank)
        cell = _composition_unrank(cell_mass, 2, cell_rank)
        assert margin is not None
        assert cell is not None
        return margin + cell + cell
    raise AssertionError


def _canonical_nonfixed_sides(
    left: _Vector,
    right: _Vector,
) -> tuple[_Vector, _Vector, int, bool] | None:
    flipped = _vector_key(right) < _vector_key(left)
    if flipped:
        left, right = right, left
    side_rank = _side_nonfixed_rank(left, right)
    if side_rank is None:
        return None
    return left, right, side_rank, flipped


def _z_nonfixed_rank(vector: _Vector) -> tuple[int, bool] | None:
    if len(vector) != _ROW_COMPONENTS or any(value < 0 for value in vector):
        return None
    margin = vector[0:2]
    sides = _canonical_nonfixed_sides(vector[2:4], vector[4:6])
    if sides is None:
        return None
    margin_key = _vector_key(margin)
    side_mass = sum(sides[0]) + sum(sides[1])
    total = margin_key[0] + side_mass
    prefix = sum(
        _composition_count(mass, 2) * _side_nonfixed_count(total - mass)
        for mass in range(margin_key[0])
    )
    rank = (
        prefix
        + margin_key[1] * _side_nonfixed_count(side_mass)
        + sides[2]
    )
    return rank, sides[3]


def _z_nonfixed_unrank(total: int, rank: int) -> _Vector | None:
    if rank < 0 or rank >= _z_nonfixed_orbit_count(total):
        return None
    remaining = rank
    for margin_mass in range(total + 1):
        side_mass = total - margin_mass
        side_count = _side_nonfixed_count(side_mass)
        margin_count = _composition_count(margin_mass, 2)
        block = margin_count * side_count
        if remaining >= block:
            remaining -= block
            continue
        margin_rank, side_rank = divmod(remaining, side_count)
        margin = _composition_unrank(margin_mass, 2, margin_rank)
        sides = _side_nonfixed_unrank(side_mass, side_rank)
        assert margin is not None
        assert sides is not None
        return margin + sides[0] + sides[1]
    raise AssertionError


def _z_orbit_count(total: int) -> int:
    return _z_fixed_count(total) + _z_nonfixed_orbit_count(total)


def _z_orbit_rank(vector: _Vector) -> tuple[int, bool]:
    fixed_rank = _z_fixed_rank(vector)
    if fixed_rank is not None:
        return fixed_rank, False
    result = _z_nonfixed_rank(vector)
    assert result is not None
    return _z_fixed_count(sum(vector)) + result[0], result[1]


def _z_orbit_unrank(total: int, rank: int) -> _Vector | None:
    fixed_count = _z_fixed_count(total)
    if rank < fixed_count:
        return _z_fixed_unrank(total, rank)
    return _z_nonfixed_unrank(total, rank - fixed_count)


# ---- Y = unordered row-bundle pair, with descended b acting by t on both. ----


def _y_count(total: int) -> int:
    return _multiset_pair_count(total, _ROW_COMPONENTS)


def _y_rank(left: _Vector, right: _Vector) -> int | None:
    return _multiset_pair_rank(left, right, _ROW_COMPONENTS)


def _y_unrank(total: int, rank: int) -> tuple[_Vector, _Vector] | None:
    return _multiset_pair_unrank(total, _ROW_COMPONENTS, rank)


def _y_mass_pair_block_count(left_mass: int, right_mass: int) -> int:
    if left_mass < right_mass:
        fixed_left = _z_fixed_count(left_mass)
        orbit_right = _z_orbit_count(right_mass)
        nonfixed_left = _z_nonfixed_orbit_count(left_mass)
        return fixed_left * orbit_right + nonfixed_left * _z_count(right_mass)
    fixed = _z_fixed_count(left_mass)
    paired = _z_nonfixed_orbit_count(left_mass)
    return fixed * (fixed + 1) // 2 + fixed * paired + paired * (paired + 1)


@cache
def _y_orbit_count(total: int) -> int:
    return sum(
        _y_mass_pair_block_count(left_mass, total - left_mass)
        for left_mass in range(total // 2 + 1)
        if left_mass <= total - left_mass
    )


def _rank_fixed_left_pair_orbit(
    left: _Vector,
    right: _Vector,
    fixed_left: int,
    *,
    right_mass: int,
) -> tuple[int, tuple[_Vector, _Vector]]:
    right_orbit, right_flipped = _z_orbit_rank(right)
    if right_flipped:
        right = _t(right)
    rank = fixed_left * _z_orbit_count(right_mass) + right_orbit
    return rank, (left, right)


def _rank_moving_left_pair_orbit(
    left: _Vector,
    right: _Vector,
    left_mass: int,
    *,
    right_mass: int,
) -> tuple[int, tuple[_Vector, _Vector]]:
    left_result = _z_nonfixed_rank(left)
    assert left_result is not None
    left_rank, flipped = left_result
    if flipped:
        left = _t(left)
        right = _t(right)
    prefix = _z_fixed_count(left_mass) * _z_orbit_count(right_mass)
    right_rank = _composition_rank(right, right_mass)
    assert right_rank is not None
    rank = prefix + left_rank * _z_count(right_mass) + right_rank
    return rank, (left, right)


def _pair_orbit_rank(
    left: _Vector,
    right: _Vector,
) -> tuple[int, tuple[_Vector, _Vector]]:
    left_mass = sum(left)
    right_mass = sum(right)
    if left_mass > right_mass:
        left, right = right, left
        left_mass, right_mass = right_mass, left_mass
    assert left_mass < right_mass
    fixed_left = _z_fixed_rank(left)
    if fixed_left is not None:
        return _rank_fixed_left_pair_orbit(
            left,
            right,
            fixed_left,
            right_mass=right_mass,
        )
    return _rank_moving_left_pair_orbit(
        left,
        right,
        left_mass,
        right_mass=right_mass,
    )


def _pair_orbit_unrank(
    left_mass: int,
    right_mass: int,
    rank: int,
) -> tuple[_Vector, _Vector]:
    fixed_block = _z_fixed_count(left_mass) * _z_orbit_count(right_mass)
    if rank < fixed_block:
        left_rank, right_orbit = divmod(rank, _z_orbit_count(right_mass))
        left = _z_fixed_unrank(left_mass, left_rank)
        right = _z_orbit_unrank(right_mass, right_orbit)
        assert left is not None
        assert right is not None
        return left, right
    residual = rank - fixed_block
    left_rank, right_raw_rank = divmod(residual, _z_count(right_mass))
    left = _z_nonfixed_unrank(left_mass, left_rank)
    right = _composition_unrank(right_mass, _ROW_COMPONENTS, right_raw_rank)
    assert left is not None
    assert right is not None
    return left, right


def _rank_equal_fixed_y(
    total: int,
    fixed_ranks: tuple[int, int],
) -> int:
    fixed = _z_fixed_count(total)
    left, right = sorted(fixed_ranks)
    return _equal_pair_rank(left, right, fixed)


def _rank_equal_mixed_y(
    total: int,
    left: _Vector,
    right: _Vector,
    *,
    fixed_ranks: tuple[int | None, int | None],
) -> int:
    fixed = _z_fixed_count(total)
    paired = _z_nonfixed_orbit_count(total)
    fixed_block = fixed * (fixed + 1) // 2
    fixed_rank = fixed_ranks[1] if fixed_ranks[0] is None else fixed_ranks[0]
    moving = left if fixed_ranks[0] is None else right
    assert fixed_rank is not None
    moving_rank = _z_nonfixed_rank(moving)
    assert moving_rank is not None
    return fixed_block + fixed_rank * paired + moving_rank[0]


def _rank_equal_moving_y(
    total: int,
    left: _Vector,
    right: _Vector,
) -> int:
    fixed = _z_fixed_count(total)
    paired = _z_nonfixed_orbit_count(total)
    moving = _z_nonfixed_rank(left), _z_nonfixed_rank(right)
    assert moving[0] is not None
    assert moving[1] is not None
    orbits = moving[0][0], moving[1][0]
    parity = int(moving[0][1] != moving[1][1])
    prefix = fixed * (fixed + 1) // 2 + fixed * paired
    if orbits[0] == orbits[1]:
        return prefix + 2 * orbits[0] + parity
    first, second = sorted(orbits)
    distinct_rank = _equal_pair_rank(first, second - 1, paired - 1)
    return prefix + 2 * paired + 2 * distinct_rank + parity


def _equal_y_orbit_rank(left: _Vector, right: _Vector) -> int:
    total = sum(left)
    assert total == sum(right)
    fixed_ranks = _z_fixed_rank(left), _z_fixed_rank(right)
    if fixed_ranks[0] is not None and fixed_ranks[1] is not None:
        return _rank_equal_fixed_y(
            total,
            (fixed_ranks[0], fixed_ranks[1]),
        )
    if (fixed_ranks[0] is None) != (fixed_ranks[1] is None):
        return _rank_equal_mixed_y(
            total,
            left,
            right,
            fixed_ranks=fixed_ranks,
        )
    return _rank_equal_moving_y(total, left, right)


def _unrank_equal_fixed_y(
    total: int,
    rank: int,
) -> tuple[_Vector, _Vector]:
    fixed = _z_fixed_count(total)
    pair = _equal_pair_unrank(rank, fixed)
    left = _z_fixed_unrank(total, pair[0])
    right = _z_fixed_unrank(total, pair[1])
    assert left is not None
    assert right is not None
    return left, right


def _unrank_equal_mixed_y(
    total: int,
    rank: int,
) -> tuple[_Vector, _Vector]:
    paired = _z_nonfixed_orbit_count(total)
    fixed_rank, moving_rank = divmod(rank, paired)
    left = _z_fixed_unrank(total, fixed_rank)
    right = _z_nonfixed_unrank(total, moving_rank)
    assert left is not None
    assert right is not None
    return left, right


def _unrank_equal_moving_y(
    total: int,
    rank: int,
) -> tuple[_Vector, _Vector]:
    paired = _z_nonfixed_orbit_count(total)
    same_block = 2 * paired
    if rank < same_block:
        moving_rank, parity = divmod(rank, 2)
        left = _z_nonfixed_unrank(total, moving_rank)
        assert left is not None
        right = _t(left) if parity else left
        return left, right
    pair_rank, parity = divmod(rank - same_block, 2)
    first, shifted_second = _equal_pair_unrank(pair_rank, paired - 1)
    second = shifted_second + 1
    left = _z_nonfixed_unrank(total, first)
    right = _z_nonfixed_unrank(total, second)
    assert left is not None
    assert right is not None
    if parity:
        right = _t(right)
    return left, right


def _equal_y_orbit_unrank(total: int, rank: int) -> tuple[_Vector, _Vector]:
    fixed = _z_fixed_count(total)
    paired = _z_nonfixed_orbit_count(total)
    fixed_block = fixed * (fixed + 1) // 2
    mixed_block = fixed * paired
    if rank < fixed_block:
        return _unrank_equal_fixed_y(total, rank)
    if rank < fixed_block + mixed_block:
        return _unrank_equal_mixed_y(total, rank - fixed_block)
    return _unrank_equal_moving_y(
        total,
        rank - fixed_block - mixed_block,
    )


def _y_orbit_rank(left: _Vector, right: _Vector) -> int | None:
    if len(left) != _ROW_COMPONENTS or len(right) != _ROW_COMPONENTS:
        return None
    left_mass = sum(left)
    right_mass = sum(right)
    if left_mass > right_mass:
        left, right = right, left
        left_mass, right_mass = right_mass, left_mass
    total = left_mass + right_mass
    prefix = sum(
        _y_mass_pair_block_count(mass, total - mass)
        for mass in range(left_mass)
        if mass <= total - mass
    )
    if left_mass < right_mass:
        block_rank, _ = _pair_orbit_rank(left, right)
    else:
        block_rank = _equal_y_orbit_rank(left, right)
    return prefix + block_rank


def _y_orbit_unrank(total: int, rank: int) -> tuple[_Vector, _Vector] | None:
    if rank < 0 or rank >= _y_orbit_count(total):
        return None
    remaining = rank
    for left_mass in range(total // 2 + 1):
        right_mass = total - left_mass
        block = _y_mass_pair_block_count(left_mass, right_mass)
        if remaining >= block:
            remaining -= block
            continue
        if left_mass < right_mass:
            return _pair_orbit_unrank(left_mass, right_mass, remaining)
        return _equal_y_orbit_unrank(left_mass, remaining)
    raise AssertionError


def _y_apply_t(left: _Vector, right: _Vector) -> tuple[_Vector, _Vector]:
    transformed = _t(left), _t(right)
    if _vector_key(transformed[1]) < _vector_key(transformed[0]):
        return transformed[1], transformed[0]
    return transformed


# ---- Full V4 quotient: diagonal b on X x Y after quotienting a. ----


def _v4_block_count(total: int, x_mass: int) -> int:
    y_mass = total - x_mass
    fixed_x = _x_fixed_count(x_mass)
    moving_x = _x_nonfixed_orbit_count(x_mass)
    return fixed_x * _y_orbit_count(y_mass) + moving_x * _y_count(y_mass)


@cache
def _v4_count(total: int) -> int:
    return sum(_v4_block_count(total, x_mass) for x_mass in range(total + 1))


def _flatten(
    edge_pairs: _EdgePairs,
    edges: tuple[tuple[int, int], ...],
) -> _Vector:
    values: list[int] = []
    for edge in edges:
        values.extend(edge_pairs[_EDGE_INDEX[edge]])
    return tuple(values)


def _extract(edge_pairs: _EdgePairs) -> _StateParts:
    return (
        _flatten(edge_pairs, _CORE_EDGES),
        _flatten(edge_pairs, (_COLUMN_EDGES[0],)),
        _flatten(edge_pairs, (_COLUMN_EDGES[1],)),
        _flatten(edge_pairs, _ROW_ZERO_EDGES),
        _flatten(edge_pairs, _ROW_ONE_EDGES),
    )


def _rank_fixed_x_state(
    parts: _StateParts,
    y_mass: int,
    *,
    prefix: int,
) -> int:
    x_rank = _x_fixed_rank(parts[0], parts[1])
    y_rank = _y_orbit_rank(parts[3], parts[4])
    assert x_rank is not None
    assert y_rank is not None
    return prefix + x_rank * _y_orbit_count(y_mass) + y_rank


def _rank_moving_x_state(
    parts: _StateParts,
    x_mass: int,
    y_mass: int,
    *,
    prefix: int,
) -> int:
    x_result = _x_nonfixed_rank(parts[0], parts[1], parts[2])
    assert x_result is not None
    x_rank, flipped = x_result
    rows = (parts[3], parts[4])
    if flipped:
        rows = _y_apply_t(*rows)
    y_rank = _y_rank(*rows)
    assert y_rank is not None
    fixed_block = _x_fixed_count(x_mass) * _y_orbit_count(y_mass)
    return prefix + fixed_block + x_rank * _y_count(y_mass) + y_rank


def _rank(edge_pairs: _EdgePairs) -> int | None:
    if len(edge_pairs) != _EDGE_COUNT or any(
        value < 0 for pair in edge_pairs for value in pair
    ):
        return None
    parts = _extract(edge_pairs)
    x_mass = sum(parts[0]) + sum(parts[1]) + sum(parts[2])
    y_mass = sum(parts[3]) + sum(parts[4])
    total = x_mass + y_mass
    prefix = sum(_v4_block_count(total, mass) for mass in range(x_mass))
    if parts[1] == parts[2]:
        return _rank_fixed_x_state(parts, y_mass, prefix=prefix)
    return _rank_moving_x_state(
        parts, x_mass, y_mass, prefix=prefix
    )


def _assign_pairs(
    result: list[_Pair | None],
    edges: tuple[tuple[int, int], ...],
    vector: _Vector,
) -> None:
    pairs = tuple(
        (vector[index], vector[index + 1])
        for index in range(0, len(vector), _COMPONENTS_PER_PAIR)
    )
    for edge, pair in zip(edges, pairs, strict=True):
        result[_EDGE_INDEX[edge]] = pair


def _build(parts: _StateParts) -> _EdgePairs:
    result: list[_Pair | None] = [None] * _EDGE_COUNT
    _assign_pairs(result, _CORE_EDGES, parts[0])
    _assign_pairs(result, (_COLUMN_EDGES[0],), parts[1])
    _assign_pairs(result, (_COLUMN_EDGES[1],), parts[2])
    _assign_pairs(result, _ROW_ZERO_EDGES, parts[3])
    _assign_pairs(result, _ROW_ONE_EDGES, parts[4])
    assert all(pair is not None for pair in result)
    return tuple(pair for pair in result if pair is not None)


def _unrank(total: int, rank: int) -> _EdgePairs | None:
    if rank < 0 or rank >= _v4_count(total):
        return None
    remaining = rank
    for x_mass in range(total + 1):
        y_mass = total - x_mass
        block = _v4_block_count(total, x_mass)
        if remaining >= block:
            remaining -= block
            continue
        fixed_block = _x_fixed_count(x_mass) * _y_orbit_count(y_mass)
        if remaining < fixed_block:
            x_rank, y_rank = divmod(remaining, _y_orbit_count(y_mass))
            x = _x_fixed_unrank(x_mass, x_rank)
            y = _y_orbit_unrank(y_mass, y_rank)
            assert x is not None
            assert y is not None
            return _build((x[0], x[1], x[1], y[0], y[1]))
        residual = remaining - fixed_block
        x_rank, y_rank = divmod(residual, _y_count(y_mass))
        x = _x_nonfixed_unrank(x_mass, x_rank)
        y = _y_unrank(y_mass, y_rank)
        assert x is not None
        assert y is not None
        return _build((x[0], x[1], x[2], y[0], y[1]))
    raise AssertionError


def _edge_permutation(order: tuple[int, ...]) -> tuple[int, ...]:
    result: list[int] = []
    for left, right in _EDGES:
        source = tuple(sorted((order[left], order[right])))
        result.append(_EDGE_INDEX[source[0], source[1]])
    return tuple(result)


def _permute_edges(
    edge_pairs: _EdgePairs,
    order: tuple[int, ...],
) -> _EdgePairs:
    permutation = _edge_permutation(order)
    result: list[_Pair | None] = [None] * _EDGE_COUNT
    for source, destination in enumerate(permutation):
        result[destination] = edge_pairs[source]
    assert all(pair is not None for pair in result)
    return tuple(pair for pair in result if pair is not None)


def _compose(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(left[right[index]] for index in range(len(left)))


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _edge_pairs_from_vector(vector: _Vector) -> _EdgePairs:
    return tuple(
        (vector[index], vector[index + 1])
        for index in range(0, 20, 2)
    )


def _fixed_scalar_count(cycles: tuple[int, ...], total: int) -> int:
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


def _burnside_count(total: int) -> int:
    identity = _composition_count(total, 20)
    single = _fixed_scalar_count((1,) * 8 + (2,) * 6, total)
    double = _fixed_scalar_count((1,) * 4 + (2,) * 8, total)
    return (identity + 2 * single + double) // 4


def test_v4_dense_rank_matches_direct_small_orbits() -> None:
    """Small edge assignments collapse to one contiguous V4 rank."""
    ab = _compose(_A, _B)
    orders = ((0, 1, 2, 3, 4), _A, _B, ab)
    for total in range(_EXHAUSTIVE_MASS + 1):
        representatives: dict[int, set[_EdgePairs]] = {}
        for vector in _weak_compositions(total, 20):
            edge_pairs = _edge_pairs_from_vector(vector)
            rank = _rank(edge_pairs)
            assert rank is not None
            orbit = {_permute_edges(edge_pairs, order) for order in orders}
            if rank not in representatives:
                representatives[rank] = orbit
            assert representatives[rank] == orbit
        count = _v4_count(total)
        assert set(representatives) == set(range(count))
        assert count == _burnside_count(total)


def test_v4_dense_rank_roundtrips_through_mass_fourteen() -> None:
    """Boundary and interior V4 ranks roundtrip through mass fourteen."""
    ab = _compose(_A, _B)
    orders = ((0, 1, 2, 3, 4), _A, _B, ab)
    for total in range(_MAXIMUM_MASS + 1):
        count = _v4_count(total)
        assert count == _burnside_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            edge_pairs = _unrank(total, rank)
            assert edge_pairs is not None
            assert _rank(edge_pairs) == rank
            for order in orders:
                assert _rank(_permute_edges(edge_pairs, order)) == rank
    assert _v4_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT


def test_v4_block_factorization_matches_nested_fixed_count() -> None:
    """Diagonal X/Y blocks reproduce the independently proved V4 total."""
    for total in range(_MAXIMUM_MASS + 1):
        assert _v4_count(total) == _burnside_count(total)
