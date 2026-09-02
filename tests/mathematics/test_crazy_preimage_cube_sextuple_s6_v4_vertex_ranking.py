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
#   - Dense S6 ranking for vertex multiplicity partition (2,2,1,1).
# - Must-Not:
#   - Claim ranking for larger Young stabilizers.
# - Allows:
#   - Inputs: sextuple joint-count mass 0 through 14 in the V4 stratum.
#   - Outputs: dense rank/unrank modulo two commuting repeated-vertex swaps.
#   - Side effects: none.
# - Split-When:
#   - Another Young stabilizer receives a constructive rank.
# - Merge-When:
#   - Complete dense S6 ranking owns every vertex multiplicity stratum.
# - Summary:
#   - Quotient one swap, then rank the descended diagonal involution.
# - Description:
#   - Uses generic fixed-plus-swapped-side ranks at both nested levels.
# - Usage:
#   - Constructive S6 slice for the Young stabilizer V4=S2xS2.
# - Defaults:
#   - Direct residual orbits stop at mass two; full exhaustion stops at six.
#

"""Dense S6 ranking for the V4 Young-stabilizer vertex stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from math import comb

_ARITY = 6
_MAXIMUM_MASS = 14
_EXHAUSTIVE_RESIDUAL_MASS = 2
_EXHAUSTIVE_TOTAL_MASS = 6
_WIDTH_FOURTEEN_COUNT = 39_233_740_619
_VERTEX_PARTITION = (2, 2, 1, 1)
_X_SHAPE = (12, 6)
_Z_SHAPE = (6, 4)
_X_COMPONENTS = _X_SHAPE[0] + 2 * _X_SHAPE[1]
_Z_COMPONENTS = _Z_SHAPE[0] + 2 * _Z_SHAPE[1]
_RESIDUAL_COMPONENTS = _X_COMPONENTS + 2 * _Z_COMPONENTS
_EXPECTED_COUNTS = {
    5: 6,
    6: 188,
    7: 3_772,
    8: 59_113,
    9: 770_882,
    10: 8_602_203,
    11: 83_705_886,
    12: 721_443_423,
    13: 5_582_322_358,
    14: 39_233_740_619,
}
_A = (1, 0, 2, 3, 4, 5)
_B = (0, 1, 3, 2, 4, 5)
_IDENTITY = (0, 1, 2, 3, 4, 5)
_V4 = (_IDENTITY, _A, _B, (1, 0, 3, 2, 4, 5))

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Vector = tuple[int, ...]
type _Shape = tuple[int, int]
type _ResidualParts = tuple[_Vector, _Vector, _Vector]
type _State = tuple[_Vertices, _Vector]
type _Permutation = tuple[int, int, int, int, int, int]

_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)
_RESIDUAL_LABELS = tuple(
    symbol
    for symbol in range(1 << _ARITY)
    if symbol.bit_count() not in {1, _ARITY - 1}
)
_LABEL_INDEX = {label: index for index, label in enumerate(_RESIDUAL_LABELS)}


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
        rank += sum(
            _composition_count(remaining - earlier, tail_parts)
            for earlier in range(value)
        )
        remaining -= value
    return rank


def _composition_unrank(total: int, parts: int, rank: int) -> _Vector | None:
    count = _composition_count(total, parts)
    if rank < 0 or rank >= count:
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
        return left, left + 1 + remaining
    raise AssertionError


def _multiset_pair_count(total: int, parts: int) -> int:
    result = sum(
        _composition_count(left_mass, parts)
        * _composition_count(total - left_mass, parts)
        for left_mass in range((total + 1) // 2)
    )
    if total % 2 == 0:
        population = _composition_count(total // 2, parts)
        result += population * (population + 1) // 2
    return result


def _multiset_pair_rank(
    left: _Vector,
    right: _Vector,
    parts: int,
) -> int | None:
    if (
        len(left) != parts
        or len(right) != parts
        or any(value < 0 for value in (*left, *right))
    ):
        return None
    if _vector_key(right) < _vector_key(left):
        left, right = right, left
    left_mass, left_rank = _vector_key(left)
    right_mass, right_rank = _vector_key(right)
    total = left_mass + right_mass
    prefix = sum(
        _composition_count(mass, parts)
        * _composition_count(total - mass, parts)
        for mass in range(left_mass)
        if mass < total - mass
    )
    if left_mass < right_mass:
        offset = left_rank * _composition_count(right_mass, parts) + right_rank
    else:
        population = _composition_count(left_mass, parts)
        offset = _pair_rank(left_rank, right_rank, population)
    return prefix + offset


def _multiset_pair_unrank(
    total: int,
    parts: int,
    rank: int,
) -> tuple[_Vector, _Vector] | None:
    if rank < 0 or rank >= _multiset_pair_count(total, parts):
        return None
    remaining = rank
    for left_mass in range((total + 1) // 2):
        right_mass = total - left_mass
        right_count = _composition_count(right_mass, parts)
        block = _composition_count(left_mass, parts) * right_count
        if remaining >= block:
            remaining -= block
            continue
        left_rank, right_rank = divmod(remaining, right_count)
        left = _composition_unrank(left_mass, parts, left_rank)
        right = _composition_unrank(right_mass, parts, right_rank)
        assert left is not None
        assert right is not None
        return left, right
    half = total // 2
    population = _composition_count(half, parts)
    left_rank, right_rank = _pair_unrank(remaining, population)
    left = _composition_unrank(half, parts, left_rank)
    right = _composition_unrank(half, parts, right_rank)
    assert left is not None
    assert right is not None
    return left, right


def _strict_multiset_pair_count(total: int, parts: int) -> int:
    result = sum(
        _composition_count(left_mass, parts)
        * _composition_count(total - left_mass, parts)
        for left_mass in range((total + 1) // 2)
    )
    if total % 2 == 0:
        population = _composition_count(total // 2, parts)
        result += population * (population - 1) // 2
    return result


def _strict_multiset_pair_rank(
    left: _Vector,
    right: _Vector,
    parts: int,
) -> int | None:
    if len(left) != parts or len(right) != parts:
        return None
    if _vector_key(right) < _vector_key(left):
        left, right = right, left
    if left == right:
        return None
    left_mass, left_rank = _vector_key(left)
    right_mass, right_rank = _vector_key(right)
    total = left_mass + right_mass
    prefix = sum(
        _composition_count(mass, parts)
        * _composition_count(total - mass, parts)
        for mass in range(left_mass)
        if mass < total - mass
    )
    if left_mass < right_mass:
        offset = left_rank * _composition_count(right_mass, parts) + right_rank
    else:
        population = _composition_count(left_mass, parts)
        offset = _strict_pair_rank(left_rank, right_rank, population)
    return prefix + offset


def _strict_multiset_pair_unrank(
    total: int,
    parts: int,
    rank: int,
) -> tuple[_Vector, _Vector] | None:
    if rank < 0 or rank >= _strict_multiset_pair_count(total, parts):
        return None
    remaining = rank
    for left_mass in range((total + 1) // 2):
        right_mass = total - left_mass
        right_count = _composition_count(right_mass, parts)
        block = _composition_count(left_mass, parts) * right_count
        if remaining >= block:
            remaining -= block
            continue
        left_rank, right_rank = divmod(remaining, right_count)
        left = _composition_unrank(left_mass, parts, left_rank)
        right = _composition_unrank(right_mass, parts, right_rank)
        assert left is not None
        assert right is not None
        return left, right
    half = total // 2
    population = _composition_count(half, parts)
    left_rank, right_rank = _strict_pair_unrank(remaining, population)
    left = _composition_unrank(half, parts, left_rank)
    right = _composition_unrank(half, parts, right_rank)
    assert left is not None
    assert right is not None
    return left, right


def _shape_parts(shape: _Shape) -> int:
    fixed, side = shape
    return fixed + 2 * side


def _apply_involution(vector: _Vector, shape: _Shape) -> _Vector:
    fixed, side = shape
    assert len(vector) == _shape_parts(shape)
    middle = fixed + side
    return vector[:fixed] + vector[middle:] + vector[fixed:middle]


def _involution_raw_count(total: int, shape: _Shape) -> int:
    return _composition_count(total, _shape_parts(shape))


@cache
def _involution_fixed_count(total: int, shape: _Shape) -> int:
    fixed, side = shape
    return sum(
        _composition_count(core_mass, fixed)
        * _composition_count((total - core_mass) // 2, side)
        for core_mass in range(total + 1)
        if (total - core_mass) % 2 == 0
    )


def _involution_moving_count(total: int, shape: _Shape) -> int:
    raw = _involution_raw_count(total, shape)
    fixed = _involution_fixed_count(total, shape)
    return (raw - fixed) // 2


def _fixed_rank_value(
    core: _Vector,
    side_vector: _Vector,
    shape: _Shape,
) -> int:
    fixed, side = shape
    core_mass = sum(core)
    side_mass = sum(side_vector)
    total = core_mass + 2 * side_mass
    core_rank = _composition_rank(core, core_mass)
    side_rank = _composition_rank(side_vector, side_mass)
    assert core_rank is not None
    assert side_rank is not None
    prefix = sum(
        _composition_count(total - 2 * mass, fixed)
        * _composition_count(mass, side)
        for mass in range(side_mass)
    )
    return prefix + core_rank * _composition_count(side_mass, side) + side_rank


def _involution_fixed_rank(vector: _Vector, shape: _Shape) -> int | None:
    fixed, side = shape
    valid_shape = len(vector) == _shape_parts(shape)
    if not valid_shape or _apply_involution(vector, shape) != vector:
        return None
    core = vector[:fixed]
    side_vector = vector[fixed : fixed + side]
    return _fixed_rank_value(core, side_vector, shape)


def _involution_fixed_unrank(
    total: int,
    shape: _Shape,
    rank: int,
) -> _Vector | None:
    if rank < 0 or rank >= _involution_fixed_count(total, shape):
        return None
    fixed, side = shape
    remaining = rank
    for side_mass in range(total // 2 + 1):
        core_mass = total - 2 * side_mass
        side_count = _composition_count(side_mass, side)
        block = _composition_count(core_mass, fixed) * side_count
        if remaining >= block:
            remaining -= block
            continue
        core_rank, side_rank = divmod(remaining, side_count)
        core = _composition_unrank(core_mass, fixed, core_rank)
        side_vector = _composition_unrank(side_mass, side, side_rank)
        assert core is not None
        assert side_vector is not None
        return core + side_vector + side_vector
    raise AssertionError


def _canonical_moving_parts(
    vector: _Vector,
    shape: _Shape,
) -> tuple[_Vector, _Vector, _Vector, bool] | None:
    fixed, side = shape
    if len(vector) != _shape_parts(shape) or any(value < 0 for value in vector):
        return None
    core = vector[:fixed]
    left = vector[fixed : fixed + side]
    right = vector[fixed + side :]
    flipped = _vector_key(right) < _vector_key(left)
    if flipped:
        left, right = right, left
    if left == right:
        return None
    return core, left, right, flipped


def _moving_rank_value(
    core: _Vector,
    left: _Vector,
    right: _Vector,
    *,
    shape: _Shape,
) -> int | None:
    fixed, side = shape
    side_rank = _strict_multiset_pair_rank(left, right, side)
    core_mass = sum(core)
    core_rank = _composition_rank(core, core_mass)
    if side_rank is None or core_rank is None:
        return None
    side_mass = sum(left) + sum(right)
    total = core_mass + side_mass
    side_count = _strict_multiset_pair_count(side_mass, side)
    prefix = sum(
        _composition_count(mass, fixed)
        * _strict_multiset_pair_count(total - mass, side)
        for mass in range(core_mass)
    )
    return prefix + core_rank * side_count + side_rank


def _involution_moving_rank(
    vector: _Vector,
    shape: _Shape,
) -> tuple[int, bool] | None:
    parts = _canonical_moving_parts(vector, shape)
    if parts is None:
        return None
    core, left, right, flipped = parts
    rank = _moving_rank_value(core, left, right, shape=shape)
    if rank is None:
        return None
    return rank, flipped


def _involution_moving_unrank(
    total: int,
    shape: _Shape,
    rank: int,
) -> _Vector | None:
    if rank < 0 or rank >= _involution_moving_count(total, shape):
        return None
    fixed, side = shape
    remaining = rank
    for core_mass in range(total + 1):
        side_mass = total - core_mass
        side_count = _strict_multiset_pair_count(side_mass, side)
        block = _composition_count(core_mass, fixed) * side_count
        if remaining >= block:
            remaining -= block
            continue
        core_rank, side_rank = divmod(remaining, side_count)
        core = _composition_unrank(core_mass, fixed, core_rank)
        sides = _strict_multiset_pair_unrank(side_mass, side, side_rank)
        assert core is not None
        assert sides is not None
        return core + sides[0] + sides[1]
    raise AssertionError


def _involution_orbit_count(total: int, shape: _Shape) -> int:
    fixed = _involution_fixed_count(total, shape)
    moving = _involution_moving_count(total, shape)
    return fixed + moving


def _involution_orbit_rank(vector: _Vector, shape: _Shape) -> tuple[int, bool]:
    fixed_rank = _involution_fixed_rank(vector, shape)
    if fixed_rank is not None:
        return fixed_rank, False
    moving = _involution_moving_rank(vector, shape)
    assert moving is not None
    return _involution_fixed_count(sum(vector), shape) + moving[0], moving[1]


def _involution_orbit_unrank(
    total: int,
    shape: _Shape,
    rank: int,
) -> _Vector | None:
    fixed_count = _involution_fixed_count(total, shape)
    if rank < fixed_count:
        return _involution_fixed_unrank(total, shape, rank)
    return _involution_moving_unrank(total, shape, rank - fixed_count)


def _y_count(total: int) -> int:
    return _multiset_pair_count(total, _Z_COMPONENTS)


def _y_rank(left: _Vector, right: _Vector) -> int | None:
    return _multiset_pair_rank(left, right, _Z_COMPONENTS)


def _y_unrank(total: int, rank: int) -> tuple[_Vector, _Vector] | None:
    return _multiset_pair_unrank(total, _Z_COMPONENTS, rank)


def _y_mass_block_count(left_mass: int, right_mass: int) -> int:
    fixed = _involution_fixed_count(left_mass, _Z_SHAPE)
    moving = _involution_moving_count(left_mass, _Z_SHAPE)
    if left_mass < right_mass:
        right_orbits = _involution_orbit_count(right_mass, _Z_SHAPE)
        right_raw = _involution_raw_count(right_mass, _Z_SHAPE)
        result = fixed * right_orbits + moving * right_raw
    else:
        result = fixed * (fixed + 1) // 2 + fixed * moving
        result += moving * (moving + 1)
    return result


@cache
def _y_orbit_count(total: int) -> int:
    return sum(
        _y_mass_block_count(left_mass, total - left_mass)
        for left_mass in range(total // 2 + 1)
    )


def _rank_y_fixed_left(
    fixed_rank: int,
    right: _Vector,
    right_mass: int,
) -> int:
    right_orbit, _ = _involution_orbit_rank(right, _Z_SHAPE)
    right_count = _involution_orbit_count(right_mass, _Z_SHAPE)
    return fixed_rank * right_count + right_orbit


def _rank_y_moving_left(
    left: _Vector,
    right: _Vector,
    *,
    left_mass: int,
    right_mass: int,
) -> int:
    moving = _involution_moving_rank(left, _Z_SHAPE)
    assert moving is not None
    left_rank, flipped = moving
    if flipped:
        right = _apply_involution(right, _Z_SHAPE)
    fixed = _involution_fixed_count(left_mass, _Z_SHAPE)
    right_orbits = _involution_orbit_count(right_mass, _Z_SHAPE)
    right_raw = _involution_raw_count(right_mass, _Z_SHAPE)
    right_rank = _composition_rank(right, right_mass)
    assert right_rank is not None
    return fixed * right_orbits + left_rank * right_raw + right_rank


def _y_distinct_mass_rank(left: _Vector, right: _Vector) -> int:
    left_mass = sum(left)
    right_mass = sum(right)
    assert left_mass < right_mass
    fixed_rank = _involution_fixed_rank(left, _Z_SHAPE)
    if fixed_rank is not None:
        return _rank_y_fixed_left(fixed_rank, right, right_mass)
    return _rank_y_moving_left(
        left,
        right,
        left_mass=left_mass,
        right_mass=right_mass,
    )


def _y_distinct_mass_unrank(
    left_mass: int,
    right_mass: int,
    rank: int,
) -> tuple[_Vector, _Vector]:
    right_orbits = _involution_orbit_count(right_mass, _Z_SHAPE)
    fixed_count = _involution_fixed_count(left_mass, _Z_SHAPE)
    fixed_block = fixed_count * right_orbits
    if rank < fixed_block:
        left_rank, right_rank = divmod(rank, right_orbits)
        left = _involution_fixed_unrank(left_mass, _Z_SHAPE, left_rank)
        right = _involution_orbit_unrank(right_mass, _Z_SHAPE, right_rank)
    else:
        remaining = rank - fixed_block
        right_raw = _involution_raw_count(right_mass, _Z_SHAPE)
        left_rank, right_rank = divmod(remaining, right_raw)
        left = _involution_moving_unrank(left_mass, _Z_SHAPE, left_rank)
        right = _composition_unrank(right_mass, _Z_COMPONENTS, right_rank)
    assert left is not None
    assert right is not None
    return left, right


def _y_equal_fixed_rank(left_rank: int, right_rank: int, fixed: int) -> int:
    first, second = sorted((left_rank, right_rank))
    return _pair_rank(first, second, fixed)


def _y_equal_mixed_rank(
    left: _Vector,
    right: _Vector,
    *,
    fixed_ranks: tuple[int | None, int | None],
    counts: tuple[int, int],
) -> int:
    left_fixed, right_fixed = fixed_ranks
    fixed, moving = counts
    fixed_rank = right_fixed if left_fixed is None else left_fixed
    moving_vector = left if left_fixed is None else right
    moving_rank = _involution_moving_rank(moving_vector, _Z_SHAPE)
    assert fixed_rank is not None
    assert moving_rank is not None
    fixed_block = fixed * (fixed + 1) // 2
    return fixed_block + fixed_rank * moving + moving_rank[0]


def _y_equal_moving_rank(
    left: _Vector,
    right: _Vector,
    *,
    counts: tuple[int, int],
) -> int:
    fixed, moving = counts
    left_result = _involution_moving_rank(left, _Z_SHAPE)
    right_result = _involution_moving_rank(right, _Z_SHAPE)
    assert left_result is not None
    assert right_result is not None
    first_orbit, second_orbit = left_result[0], right_result[0]
    parity = int(left_result[1] != right_result[1])
    prefix = fixed * (fixed + 1) // 2 + fixed * moving
    if first_orbit == second_orbit:
        return prefix + 2 * first_orbit + parity
    if second_orbit < first_orbit:
        first_orbit, second_orbit = second_orbit, first_orbit
    pair_rank = _strict_pair_rank(first_orbit, second_orbit, moving)
    return prefix + 2 * moving + 2 * pair_rank + parity


def _y_equal_rank(left: _Vector, right: _Vector) -> int:
    total = sum(left)
    assert total == sum(right)
    fixed = _involution_fixed_count(total, _Z_SHAPE)
    moving = _involution_moving_count(total, _Z_SHAPE)
    left_fixed = _involution_fixed_rank(left, _Z_SHAPE)
    right_fixed = _involution_fixed_rank(right, _Z_SHAPE)
    if left_fixed is not None and right_fixed is not None:
        result = _y_equal_fixed_rank(left_fixed, right_fixed, fixed)
    elif (left_fixed is None) != (right_fixed is None):
        result = _y_equal_mixed_rank(
            left,
            right,
            fixed_ranks=(left_fixed, right_fixed),
            counts=(fixed, moving),
        )
    else:
        result = _y_equal_moving_rank(left, right, counts=(fixed, moving))
    return result


def _unrank_y_equal_fixed(
    total: int,
    rank: int,
    fixed: int,
) -> tuple[_Vector, _Vector]:
    left_rank, right_rank = _pair_unrank(rank, fixed)
    left = _involution_fixed_unrank(total, _Z_SHAPE, left_rank)
    right = _involution_fixed_unrank(total, _Z_SHAPE, right_rank)
    assert left is not None
    assert right is not None
    return left, right


def _unrank_y_equal_mixed(
    total: int,
    rank: int,
    moving: int,
) -> tuple[_Vector, _Vector]:
    fixed_rank, moving_rank = divmod(rank, moving)
    left = _involution_fixed_unrank(total, _Z_SHAPE, fixed_rank)
    right = _involution_moving_unrank(total, _Z_SHAPE, moving_rank)
    assert left is not None
    assert right is not None
    return left, right


def _unrank_y_equal_moving(
    total: int,
    rank: int,
    moving: int,
) -> tuple[_Vector, _Vector]:
    same_block = 2 * moving
    if rank < same_block:
        orbit, parity = divmod(rank, 2)
        left = _involution_moving_unrank(total, _Z_SHAPE, orbit)
        assert left is not None
        right = _apply_involution(left, _Z_SHAPE) if parity else left
        return left, right
    pair_rank, parity = divmod(rank - same_block, 2)
    left_rank, right_rank = _strict_pair_unrank(pair_rank, moving)
    left = _involution_moving_unrank(total, _Z_SHAPE, left_rank)
    right = _involution_moving_unrank(total, _Z_SHAPE, right_rank)
    assert left is not None
    assert right is not None
    if parity:
        right = _apply_involution(right, _Z_SHAPE)
    return left, right


def _y_equal_unrank(total: int, rank: int) -> tuple[_Vector, _Vector]:
    fixed = _involution_fixed_count(total, _Z_SHAPE)
    moving = _involution_moving_count(total, _Z_SHAPE)
    fixed_block = fixed * (fixed + 1) // 2
    mixed_block = fixed * moving
    if rank < fixed_block:
        result = _unrank_y_equal_fixed(total, rank, fixed)
    elif rank < fixed_block + mixed_block:
        result = _unrank_y_equal_mixed(
            total, rank - fixed_block, moving
        )
    else:
        result = _unrank_y_equal_moving(
            total, rank - fixed_block - mixed_block, moving
        )
    return result


def _y_orbit_rank(left: _Vector, right: _Vector) -> int | None:
    if len(left) != _Z_COMPONENTS or len(right) != _Z_COMPONENTS:
        return None
    if _vector_key(right) < _vector_key(left):
        left, right = right, left
    left_mass = sum(left)
    right_mass = sum(right)
    total = left_mass + right_mass
    prefix = sum(
        _y_mass_block_count(mass, total - mass)
        for mass in range(left_mass)
        if mass <= total - mass
    )
    if left_mass < right_mass:
        block = _y_distinct_mass_rank(left, right)
    else:
        block = _y_equal_rank(left, right)
    return prefix + block


def _y_orbit_unrank(total: int, rank: int) -> tuple[_Vector, _Vector] | None:
    if rank < 0 or rank >= _y_orbit_count(total):
        return None
    remaining = rank
    for left_mass in range(total // 2 + 1):
        right_mass = total - left_mass
        block = _y_mass_block_count(left_mass, right_mass)
        if remaining >= block:
            remaining -= block
            continue
        if left_mass < right_mass:
            return _y_distinct_mass_unrank(left_mass, right_mass, remaining)
        return _y_equal_unrank(left_mass, remaining)
    raise AssertionError


def _y_apply_involution(
    left: _Vector,
    right: _Vector,
) -> tuple[_Vector, _Vector]:
    first = _apply_involution(left, _Z_SHAPE)
    second = _apply_involution(right, _Z_SHAPE)
    if _vector_key(second) < _vector_key(first):
        return second, first
    return first, second


def _v4_block_count(total: int, x_mass: int) -> int:
    y_mass = total - x_mass
    fixed = _involution_fixed_count(x_mass, _X_SHAPE)
    moving = _involution_moving_count(x_mass, _X_SHAPE)
    return fixed * _y_orbit_count(y_mass) + moving * _y_count(y_mass)


@cache
def _residual_count(total: int) -> int:
    return sum(_v4_block_count(total, x_mass) for x_mass in range(total + 1))


def _rank_fixed_x(
    parts: _ResidualParts,
    *,
    y_mass: int,
    prefix: int,
) -> int | None:
    x, left, right = parts
    fixed_rank = _involution_fixed_rank(x, _X_SHAPE)
    if fixed_rank is None:
        return None
    y_rank = _y_orbit_rank(left, right)
    assert y_rank is not None
    return prefix + fixed_rank * _y_orbit_count(y_mass) + y_rank


def _rank_moving_x(
    parts: _ResidualParts,
    *,
    x_mass: int,
    y_mass: int,
    prefix: int,
) -> int:
    x, left, right = parts
    moving = _involution_moving_rank(x, _X_SHAPE)
    assert moving is not None
    x_rank, flipped = moving
    if flipped:
        left, right = _y_apply_involution(left, right)
    y_rank = _y_rank(left, right)
    assert y_rank is not None
    fixed = _involution_fixed_count(x_mass, _X_SHAPE)
    fixed_block = fixed * _y_orbit_count(y_mass)
    return prefix + fixed_block + x_rank * _y_count(y_mass) + y_rank


def _residual_rank(parts: _ResidualParts) -> int | None:
    x, left, right = parts
    if len(x) != _X_COMPONENTS:
        return None
    if _vector_key(right) < _vector_key(left):
        left, right = right, left
    x_mass = sum(x)
    y_mass = sum(left) + sum(right)
    total = x_mass + y_mass
    prefix = sum(_v4_block_count(total, mass) for mass in range(x_mass))
    canonical = (x, left, right)
    fixed = _rank_fixed_x(canonical, y_mass=y_mass, prefix=prefix)
    if fixed is not None:
        return fixed
    return _rank_moving_x(
        canonical,
        x_mass=x_mass,
        y_mass=y_mass,
        prefix=prefix,
    )


def _residual_unrank(total: int, rank: int) -> _ResidualParts | None:
    if rank < 0 or rank >= _residual_count(total):
        return None
    remaining = rank
    for x_mass in range(total + 1):
        y_mass = total - x_mass
        block = _v4_block_count(total, x_mass)
        if remaining >= block:
            remaining -= block
            continue
        fixed = _involution_fixed_count(x_mass, _X_SHAPE)
        fixed_block = fixed * _y_orbit_count(y_mass)
        if remaining < fixed_block:
            x_rank, y_rank = divmod(remaining, _y_orbit_count(y_mass))
            x = _involution_fixed_unrank(x_mass, _X_SHAPE, x_rank)
            y = _y_orbit_unrank(y_mass, y_rank)
        else:
            residual = remaining - fixed_block
            x_rank, y_rank = divmod(residual, _y_count(y_mass))
            x = _involution_moving_unrank(x_mass, _X_SHAPE, x_rank)
            y = _y_unrank(y_mass, y_rank)
        assert x is not None
        assert y is not None
        return x, y[0], y[1]
    raise AssertionError


def _permuted_symbol(symbol: int, order: _Permutation) -> int:
    bits = tuple(
        (symbol >> (_ARITY - endpoint - 1)) & 1
        for endpoint in range(_ARITY)
    )
    result = 0
    for source in order:
        result = (result << 1) | bits[source]
    return result


def _a_fixed_layout(
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    a_fixed = tuple(
        label
        for label in _RESIDUAL_LABELS
        if _permuted_symbol(label, _A) == label
    )
    core = tuple(
        label for label in a_fixed if _permuted_symbol(label, _B) == label
    )
    seen = set(core)
    left: list[int] = []
    right: list[int] = []
    for label in a_fixed:
        if label in seen:
            continue
        other = _permuted_symbol(label, _B)
        first, second = sorted((label, other))
        left.append(first)
        right.append(second)
        seen.update((first, second))
    return core, tuple(left), tuple(right)


def _a_pair_sets(a_fixed: tuple[int, ...]) -> tuple[frozenset[int], ...]:
    seen = set(a_fixed)
    result: list[frozenset[int]] = []
    for label in _RESIDUAL_LABELS:
        if label in seen:
            continue
        pair = frozenset((label, _permuted_symbol(label, _A)))
        result.append(pair)
        seen.update(pair)
    return tuple(result)


def _z_pair_layout(
    pair_sets: tuple[frozenset[int], ...],
) -> tuple[tuple[tuple[int, int], ...], ...]:
    pair_index = {pair: index for index, pair in enumerate(pair_sets)}
    seen: set[int] = set()
    fixed: list[tuple[int, int]] = []
    left: list[tuple[int, int]] = []
    right: list[tuple[int, int]] = []
    for index, pair in enumerate(pair_sets):
        if index in seen:
            continue
        image = frozenset(_permuted_symbol(label, _B) for label in pair)
        other_index = pair_index[image]
        first = min(pair)
        second = _permuted_symbol(first, _A)
        if other_index == index:
            fixed.append((first, second))
            seen.add(index)
        else:
            left.append((first, second))
            right.append(
                (_permuted_symbol(first, _B), _permuted_symbol(second, _B))
            )
            seen.update((index, other_index))
    return tuple(fixed), tuple(left), tuple(right)


def _label_layout() -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    x_parts = _a_fixed_layout()
    a_fixed = (*x_parts[0], *x_parts[1], *x_parts[2])
    z_parts = _z_pair_layout(_a_pair_sets(a_fixed))
    z_pairs = (*z_parts[0], *z_parts[1], *z_parts[2])
    x_labels = (*x_parts[0], *x_parts[1], *x_parts[2])
    z0 = tuple(first for first, _ in z_pairs)
    z1 = tuple(second for _, second in z_pairs)
    assert len(x_labels) == _X_COMPONENTS
    assert len(z0) == _Z_COMPONENTS
    assert len(z1) == _Z_COMPONENTS
    return tuple(x_labels), z0, z1


_X_LABELS, _Z0_LABELS, _Z1_LABELS = _label_layout()


def _extract_residual(vector: _Vector) -> _ResidualParts | None:
    valid_length = len(vector) == _RESIDUAL_COMPONENTS
    if not valid_length or any(value < 0 for value in vector):
        return None
    values = {
        label: vector[_LABEL_INDEX[label]] for label in _RESIDUAL_LABELS
    }
    return (
        tuple(values[label] for label in _X_LABELS),
        tuple(values[label] for label in _Z0_LABELS),
        tuple(values[label] for label in _Z1_LABELS),
    )


def _build_residual(parts: _ResidualParts) -> _Vector:
    x, z0, z1 = parts
    values: dict[int, int] = {}
    values.update(zip(_X_LABELS, x, strict=True))
    values.update(zip(_Z0_LABELS, z0, strict=True))
    values.update(zip(_Z1_LABELS, z1, strict=True))
    assert set(values) == set(_RESIDUAL_LABELS)
    return tuple(values[label] for label in _RESIDUAL_LABELS)


def _permute_residual(vector: _Vector, order: _Permutation) -> _Vector:
    result = [0] * _RESIDUAL_COMPONENTS
    for source, label in enumerate(_RESIDUAL_LABELS):
        destination = _permuted_symbol(label, order)
        result[_LABEL_INDEX[destination]] = vector[source]
    return tuple(result)


def _fixed_count_from_cycles(total: int, lengths: tuple[int, ...]) -> int:
    coefficients = [1] + [0] * total
    for cycle_length in lengths:
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, total - degree + 1, cycle_length):
                next_coefficients[degree + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[total]


def _burnside_residual_count(total: int) -> int:
    identity = _composition_count(total, _RESIDUAL_COMPONENTS)
    single = _fixed_count_from_cycles(total, (1,) * 24 + (2,) * 14)
    double = _fixed_count_from_cycles(total, (1,) * 12 + (2,) * 20)
    return (identity + 2 * single + double) // 4


@cache
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


def _vertex_partition(values: tuple[_Pair, ...]) -> tuple[int, ...]:
    return tuple(sorted(Counter(values).values(), reverse=True))


@cache
def _vertices_of_mass(mass: int) -> tuple[_Vertices, ...]:
    return tuple(
        _as_vertices(values)
        for values in _vertex_sequences_from(0, _ARITY, mass)
        if sum(sum(pair) for pair in values) == mass
        and _vertex_partition(values) == _VERTEX_PARTITION
    )


def _class_count(total: int) -> int:
    return sum(
        len(_vertices_of_mass(vertex_mass))
        * _residual_count(total - vertex_mass)
        for vertex_mass in range(total + 1)
    )


def _vertex_rank(vertices: _Vertices, mass: int) -> int | None:
    try:
        return _vertices_of_mass(mass).index(vertices)
    except ValueError:
        return None


def _residual_vector_rank(vector: _Vector) -> int | None:
    parts = _extract_residual(vector)
    if parts is None:
        return None
    return _residual_rank(parts)


def _state_rank_data(
    total: int,
    state: _State,
) -> tuple[int, int, int, int] | None:
    vertices, vector = state
    vertex_mass = sum(sum(pair) for pair in vertices)
    residual_mass = total - vertex_mass
    vertex_rank = _vertex_rank(vertices, vertex_mass)
    residual_rank = _residual_vector_rank(vector)
    valid_mass = vertex_mass <= total and sum(vector) == residual_mass
    valid_ranks = vertex_rank is not None and residual_rank is not None
    if not valid_mass or not valid_ranks:
        return None
    assert vertex_rank is not None
    assert residual_rank is not None
    return vertex_mass, vertex_rank, residual_mass, residual_rank


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
        parts = _residual_unrank(total - vertex_mass, residual_rank)
        assert parts is not None
        vertices = _vertices_of_mass(vertex_mass)[vertex_rank]
        return vertices, _build_residual(parts)
    raise AssertionError


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def test_s6_v4_label_layout_has_exact_nested_involution_geometry() -> None:
    """The actual 52 labels realize the abstract X/Sym2(Z) V4 action."""
    assert _X_COMPONENTS + 2 * _Z_COMPONENTS == _RESIDUAL_COMPONENTS
    observed = {*_X_LABELS, *_Z0_LABELS, *_Z1_LABELS}
    assert observed == set(_RESIDUAL_LABELS)
    for total in range(_EXHAUSTIVE_RESIDUAL_MASS + 1):
        for vector in _weak_compositions(total, _RESIDUAL_COMPONENTS):
            parts = _extract_residual(vector)
            assert parts is not None
            assert _build_residual(parts) == vector


def test_s6_v4_residual_rank_matches_direct_small_orbits() -> None:
    """Small residual assignments collapse to one contiguous V4 rank."""
    for total in range(_EXHAUSTIVE_RESIDUAL_MASS + 1):
        representatives: dict[int, set[_Vector]] = {}
        for vector in _weak_compositions(total, _RESIDUAL_COMPONENTS):
            parts = _extract_residual(vector)
            assert parts is not None
            rank = _residual_rank(parts)
            assert rank is not None
            orbit = {_permute_residual(vector, order) for order in _V4}
            if rank not in representatives:
                representatives[rank] = orbit
            assert representatives[rank] == orbit
        count = _residual_count(total)
        assert set(representatives) == set(range(count))
        assert count == _burnside_residual_count(total)


def test_s6_v4_rank_exhausts_small_full_strata() -> None:
    """The complete V4 stratum is dense through mass six."""
    for total in range(_EXHAUSTIVE_TOTAL_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_v4_rank_roundtrips_through_mass_fourteen() -> None:
    """Boundary and interior ranks roundtrip throughout the admitted range."""
    for total in range(_MAXIMUM_MASS + 1):
        residual_count = _residual_count(total)
        assert residual_count == _burnside_residual_count(total)
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


def test_s6_v4_counts_match_reviewed_sequence() -> None:
    """The mass-five-through-fourteen counts match the decomposition."""
    observed = {
        mass: _class_count(mass)
        for mass in range(_MAXIMUM_MASS + 1)
        if _class_count(mass) != 0
    }
    assert observed == _EXPECTED_COUNTS
