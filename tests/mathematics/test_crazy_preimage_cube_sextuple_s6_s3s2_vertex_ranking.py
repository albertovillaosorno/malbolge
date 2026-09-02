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
#   - Dense S6 ranking for vertex multiplicity partition (3,2,1).
# - Must-Not:
#   - Claim ranking for larger Young stabilizers or complete S6 ranking.
# - Allows:
#   - Inputs: sextuple joint-count mass 0 through 14 in the S3xS2 stratum.
#   - Outputs: dense rank/unrank modulo the repeated-vertex product group.
#   - Side effects: none.
# - Split-When:
#   - Another Young stabilizer receives a constructive rank.
# - Merge-When:
#   - Complete dense S6 ranking owns every vertex multiplicity stratum.
# - Summary:
#   - Quotient S3 bundles, then rank the descended commuting involution.
# - Description:
#   - Uses a (6;2,2) fixed vector and three (6;4,4) bundle involutions.
# - Usage:
#   - Constructive S6 slice for the Young stabilizer S3xS2.
# - Defaults:
#   - Direct residual orbits stop at mass two; full exhaustion stops at five.
#

"""Dense S6 ranking for the S3xS2 Young-stabilizer vertex stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import permutations
from math import comb

_ARITY = 6
_BUNDLE_COMPONENTS = 14
_BUNDLE_COUNT = 3
_Z_FIXED_COMPONENTS = 6
_Z_SIDE_COMPONENTS = 4
_SIDE_COMPONENTS = 4
_PAIR_COMPONENTS = 2
_X_COMPONENTS = 10
_X_FIXED_COMPONENTS = 6
_X_SIDE_COMPONENTS = 2
_RESIDUAL_COMPONENTS = 52
_EXHAUSTIVE_RESIDUAL_MASS = 2
_EXHAUSTIVE_TOTAL_MASS = 5
_MAXIMUM_MASS = 14
_WIDTH_FOURTEEN_COUNT = 180_275_648_841
_VERTEX_PARTITION = (3, 2, 1)
_FIXED_TAG = "f"
_MOVING_TAG = "m"
_EXPECTED_COUNTS = {
    3: 2,
    4: 44,
    5: 680,
    6: 8_972,
    7: 105_464,
    8: 1_108_403,
    9: 10_428_550,
    10: 88_217_154,
    11: 675_502_692,
    12: 4_718_732_554,
    13: 30_306_550_190,
    14: 180_275_648_841,
}
_ACTIVE_ENDPOINTS = (0, 1, 2)
_C = (0, 1, 2, 4, 3, 5)
_S3 = tuple(
    (order[0], order[1], order[2], 3, 4, 5)
    for order in permutations(_ACTIVE_ENDPOINTS)
)
_IDENTITY = (0, 1, 2, 3, 4, 5)

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Vector = tuple[int, ...]
type _Bundles = tuple[_Vector, _Vector, _Vector]
type _Sym2 = tuple[_Vector, _Vector]
type _ResidualState = tuple[_Vector, _Vector, _Vector, _Vector]
type _State = tuple[_Vertices, _Vector]
type _Permutation = tuple[int, int, int, int, int, int]

_RESIDUAL_LABELS = tuple(
    symbol
    for symbol in range(1 << _ARITY)
    if symbol.bit_count() not in {1, _ARITY - 1}
)
_LABEL_INDEX = {label: index for index, label in enumerate(_RESIDUAL_LABELS)}
_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)


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


def _rep_combination_rank(values: tuple[int, ...], population: int) -> int:
    assert tuple(sorted(values)) == values
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
    assert 0 <= rank < comb(universe, size)
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


def _strict_pair_rank(left: int, right: int, population: int) -> int:
    assert 0 <= left < right < population
    return left * (2 * population - left - 1) // 2 + right - left - 1


def _strict_pair_unrank(rank: int, population: int) -> tuple[int, int]:
    remaining = rank
    for left in range(population):
        block = population - left - 1
        if remaining >= block:
            remaining -= block
            continue
        return left, left + 1 + remaining
    raise AssertionError


def _strict_triple_rank(values: tuple[int, int, int], population: int) -> int:
    first, second, third = values
    assert 0 <= first < second < third < population
    rank = 0
    for left in range(first):
        rank += comb(population - left - 1, 2)
    for middle in range(first + 1, second):
        rank += population - middle - 1
    return rank + third - second - 1


def _strict_triple_unrank(rank: int, population: int) -> tuple[int, int, int]:
    remaining = rank
    for first in range(population - 2):
        block = comb(population - first - 1, 2)
        if remaining >= block:
            remaining -= block
            continue
        for second in range(first + 1, population - 1):
            middle_block = population - second - 1
            if remaining >= middle_block:
                remaining -= middle_block
                continue
            return first, second, second + 1 + remaining
    raise AssertionError


def _t(vector: _Vector) -> _Vector:
    assert len(vector) == _BUNDLE_COMPONENTS
    middle = _Z_FIXED_COMPONENTS + _Z_SIDE_COMPONENTS
    return (
        vector[:_Z_FIXED_COMPONENTS]
        + vector[middle:]
        + vector[_Z_FIXED_COMPONENTS:middle]
    )


def _raw_count(total: int) -> int:
    return _composition_count(total, _BUNDLE_COMPONENTS)


@cache
@cache
def _fixed_count(total: int) -> int:
    return sum(
        _composition_count(core_mass, _Z_FIXED_COMPONENTS)
        * _composition_count(
            (total - core_mass) // 2,
            _Z_SIDE_COMPONENTS,
        )
        for core_mass in range(total + 1)
        if (total - core_mass) % 2 == 0
    )


def _moving_count(total: int) -> int:
    return (_raw_count(total) - _fixed_count(total)) // 2


def _orbit_count(total: int) -> int:
    return _fixed_count(total) + _moving_count(total)


def _fixed_rank(vector: _Vector) -> int | None:
    if len(vector) != _BUNDLE_COMPONENTS or _t(vector) != vector:
        return None
    core = vector[:_Z_FIXED_COMPONENTS]
    side = vector[
        _Z_FIXED_COMPONENTS : _Z_FIXED_COMPONENTS + _Z_SIDE_COMPONENTS
    ]
    core_mass = sum(core)
    side_mass = sum(side)
    total = core_mass + 2 * side_mass
    core_rank = _composition_rank(core, core_mass)
    side_rank = _composition_rank(side, side_mass)
    assert core_rank is not None
    assert side_rank is not None
    prefix = sum(
        _composition_count(total - 2 * mass, _Z_FIXED_COMPONENTS)
        * _composition_count(mass, _Z_SIDE_COMPONENTS)
        for mass in range(side_mass)
    )
    side_count = _composition_count(side_mass, _Z_SIDE_COMPONENTS)
    return prefix + core_rank * side_count + side_rank


def _fixed_unrank(total: int, rank: int) -> _Vector:
    assert 0 <= rank < _fixed_count(total)
    remaining = rank
    for side_mass in range(total // 2 + 1):
        core_mass = total - 2 * side_mass
        side_count = _composition_count(side_mass, _Z_SIDE_COMPONENTS)
        block = _composition_count(core_mass, _Z_FIXED_COMPONENTS) * side_count
        if remaining >= block:
            remaining -= block
            continue
        core_rank, side_rank = divmod(remaining, side_count)
        core = _composition_unrank(
            core_mass,
            _Z_FIXED_COMPONENTS,
            core_rank,
        )
        side = _composition_unrank(
            side_mass,
            _Z_SIDE_COMPONENTS,
            side_rank,
        )
        assert core is not None
        assert side is not None
        return core + side + side
    raise AssertionError


def _side_moving_count(total: int) -> int:
    count = 0
    for left_mass in range((total + 1) // 2):
        right_mass = total - left_mass
        count += _composition_count(
            left_mass,
            _SIDE_COMPONENTS,
        ) * _composition_count(right_mass, _SIDE_COMPONENTS)
    if total % 2 == 0:
        half = total // 2
        population = _composition_count(half, _SIDE_COMPONENTS)
        count += comb(population, 2)
    return count


def _pair_key(vector: _Vector) -> tuple[int, int]:
    total = sum(vector)
    rank = _composition_rank(vector, total)
    assert rank is not None
    return total, rank


def _side_moving_rank(
    left: _Vector,
    right: _Vector,
) -> tuple[int, bool] | None:
    result: tuple[int, bool] | None = None
    if len(left) == _SIDE_COMPONENTS and len(right) == _SIDE_COMPONENTS:
        left_key = _pair_key(left)
        right_key = _pair_key(right)
        flipped = right_key < left_key
        if flipped:
            left, right = right, left
            left_key, right_key = right_key, left_key
        if left != right:
            total = left_key[0] + right_key[0]
            prefix = sum(
                _composition_count(mass, _SIDE_COMPONENTS)
                * _composition_count(total - mass, _SIDE_COMPONENTS)
                for mass in range(left_key[0])
                if mass < total - mass
            )
            if left_key[0] < right_key[0]:
                rank = prefix + left_key[1] * _composition_count(
                    right_key[0], _SIDE_COMPONENTS
                )
                result = rank + right_key[1], flipped
            else:
                population = _composition_count(
                    left_key[0], _SIDE_COMPONENTS
                )
                rank = prefix + _strict_pair_rank(
                    left_key[1], right_key[1], population
                )
                result = rank, flipped
    return result


def _side_unequal_unrank(
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


def _side_moving_unrank(total: int, rank: int) -> tuple[_Vector, _Vector]:
    assert 0 <= rank < _side_moving_count(total)
    unequal = _side_unequal_unrank(total, rank)
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
    left_rank, right_rank = _strict_pair_unrank(
        rank - unequal_count, population
    )
    left = _composition_unrank(half, _SIDE_COMPONENTS, left_rank)
    right = _composition_unrank(half, _SIDE_COMPONENTS, right_rank)
    assert left is not None
    assert right is not None
    return left, right


def _moving_rank(vector: _Vector) -> tuple[int, bool] | None:
    if len(vector) != _BUNDLE_COMPONENTS or any(value < 0 for value in vector):
        return None
    core = vector[:_Z_FIXED_COMPONENTS]
    middle = _Z_FIXED_COMPONENTS + _Z_SIDE_COMPONENTS
    sides = _side_moving_rank(
        vector[_Z_FIXED_COMPONENTS:middle],
        vector[middle:],
    )
    if sides is None:
        return None
    core_mass = sum(core)
    core_rank = _composition_rank(core, core_mass)
    assert core_rank is not None
    side_mass = sum(vector[_Z_FIXED_COMPONENTS:])
    total = core_mass + side_mass
    prefix = sum(
        _composition_count(mass, _Z_FIXED_COMPONENTS)
        * _side_moving_count(total - mass)
        for mass in range(core_mass)
    )
    rank = prefix + core_rank * _side_moving_count(side_mass) + sides[0]
    return rank, sides[1]


def _moving_unrank(total: int, rank: int) -> _Vector:
    assert 0 <= rank < _moving_count(total)
    remaining = rank
    for core_mass in range(total + 1):
        side_mass = total - core_mass
        side_count = _side_moving_count(side_mass)
        block = _composition_count(core_mass, _Z_FIXED_COMPONENTS) * side_count
        if remaining >= block:
            remaining -= block
            continue
        core_rank, side_rank = divmod(remaining, side_count)
        core = _composition_unrank(
            core_mass,
            _Z_FIXED_COMPONENTS,
            core_rank,
        )
        sides = _side_moving_unrank(side_mass, side_rank)
        assert core is not None
        return core + sides[0] + sides[1]
    raise AssertionError


def _orbit_rank(vector: _Vector) -> tuple[int, bool]:
    fixed = _fixed_rank(vector)
    if fixed is not None:
        return fixed, False
    moving = _moving_rank(vector)
    assert moving is not None
    return _fixed_count(sum(vector)) + moving[0], moving[1]


def _orbit_unrank(total: int, rank: int) -> _Vector:
    fixed = _fixed_count(total)
    if rank < fixed:
        return _fixed_unrank(total, rank)
    return _moving_unrank(total, rank - fixed)


# ---- Symmetric square of one bundle mass under the internal involution. ----


def _sym2_raw_count(total: int) -> int:
    return comb(_raw_count(total) + 1, 2)


def _sym2_fixed_count(total: int) -> int:
    fixed = _fixed_count(total)
    return comb(fixed + 1, 2) + _moving_count(total)


def _sym2_moving_count(total: int) -> int:
    raw = _sym2_raw_count(total)
    return (raw - _sym2_fixed_count(total)) // 2


def _sym2_orbit_count(total: int) -> int:
    return _sym2_fixed_count(total) + _sym2_moving_count(total)


def _raw_rank(vector: _Vector) -> int:
    rank = _composition_rank(vector, sum(vector))
    assert rank is not None
    return rank


def _raw_unrank(total: int, rank: int) -> _Vector:
    vector = _composition_unrank(total, _BUNDLE_COMPONENTS, rank)
    assert vector is not None
    return vector


def _sym2_raw_rank(state: _Sym2, total: int) -> int:
    ranks = sorted((_raw_rank(state[0]), _raw_rank(state[1])))
    return _rep_combination_rank((ranks[0], ranks[1]), _raw_count(total))


def _sym2_raw_unrank(total: int, rank: int) -> _Sym2:
    pair = _rep_combination_unrank(_raw_count(total), 2, rank)
    return _raw_unrank(total, pair[0]), _raw_unrank(total, pair[1])


def _sym2_fixed_rank(state: _Sym2, total: int) -> int | None:
    result: int | None = None
    fixed_ranks = (_fixed_rank(state[0]), _fixed_rank(state[1]))
    fixed = _fixed_count(total)
    if fixed_ranks[0] is not None and fixed_ranks[1] is not None:
        ranks = sorted((fixed_ranks[0], fixed_ranks[1]))
        result = _rep_combination_rank((ranks[0], ranks[1]), fixed)
    else:
        moving = (_moving_rank(state[0]), _moving_rank(state[1]))
        complete_pair = (
            moving[0] is not None
            and moving[1] is not None
            and moving[0][0] == moving[1][0]
            and moving[0][1] != moving[1][1]
        )
        if complete_pair:
            assert moving[0] is not None
            result = comb(fixed + 1, 2) + moving[0][0]
    return result


def _sym2_fixed_unrank(total: int, rank: int) -> _Sym2:
    fixed = _fixed_count(total)
    fixed_block = comb(fixed + 1, 2)
    if rank < fixed_block:
        pair = _rep_combination_unrank(fixed, 2, rank)
        return _fixed_unrank(total, pair[0]), _fixed_unrank(total, pair[1])
    moving = _moving_unrank(total, rank - fixed_block)
    return moving, _t(moving)


def _sym2_mixed_rank(
    fixed_ranks: tuple[int | None, int | None],
    moving: tuple[tuple[int, bool] | None, tuple[int, bool] | None],
    moving_count: int,
) -> tuple[int, bool]:
    first_is_moving = fixed_ranks[0] is None
    fixed_rank = fixed_ranks[1] if first_is_moving else fixed_ranks[0]
    moving_item = moving[0] if first_is_moving else moving[1]
    assert fixed_rank is not None
    assert moving_item is not None
    return fixed_rank * moving_count + moving_item[0], moving_item[1]


def _sym2_all_moving_rank(
    moving: tuple[tuple[int, bool], tuple[int, bool]],
    fixed: int,
    moving_count: int,
) -> tuple[int, bool] | None:
    left, right = moving
    prefix = fixed * moving_count
    result: tuple[int, bool] | None
    if left[0] == right[0]:
        result = None if left[1] != right[1] else (prefix + left[0], left[1])
    else:
        first, second = sorted((left[0], right[0]))
        parity = int(left[1] != right[1])
        flip = left[1] if left[0] == first else right[1]
        pair_rank = _strict_pair_rank(first, second, moving_count)
        result = prefix + moving_count + 2 * pair_rank + parity, flip
    return result


def _sym2_moving_rank(state: _Sym2, total: int) -> tuple[int, bool] | None:
    fixed = _fixed_count(total)
    moving_count = _moving_count(total)
    fixed_ranks = (_fixed_rank(state[0]), _fixed_rank(state[1]))
    moving = (_moving_rank(state[0]), _moving_rank(state[1]))
    if (fixed_ranks[0] is None) != (fixed_ranks[1] is None):
        return _sym2_mixed_rank(fixed_ranks, moving, moving_count)
    if moving[0] is None or moving[1] is None:
        return None
    return _sym2_all_moving_rank(
        (moving[0], moving[1]), fixed, moving_count
    )


def _sym2_unrank_mixed(total: int, rank: int, moving: int) -> _Sym2:
    fixed_rank, moving_rank = divmod(rank, moving)
    return (
        _fixed_unrank(total, fixed_rank),
        _moving_unrank(total, moving_rank),
    )


def _sym2_unrank_all_moving(total: int, rank: int, moving: int) -> _Sym2:
    if rank < moving:
        item = _moving_unrank(total, rank)
        return item, item
    pair_rank, parity = divmod(rank - moving, 2)
    first, second = _strict_pair_unrank(pair_rank, moving)
    return (
        _moving_unrank(total, first),
        _moving_vector(total, second, parity),
    )


def _sym2_moving_unrank(total: int, rank: int) -> _Sym2:
    fixed = _fixed_count(total)
    moving = _moving_count(total)
    mixed_block = fixed * moving
    if rank < mixed_block:
        return _sym2_unrank_mixed(total, rank, moving)
    return _sym2_unrank_all_moving(total, rank - mixed_block, moving)


def _sym2_orbit_rank(state: _Sym2, total: int) -> tuple[int, bool]:
    fixed = _sym2_fixed_rank(state, total)
    if fixed is not None:
        return fixed, False
    moving = _sym2_moving_rank(state, total)
    assert moving is not None
    return _sym2_fixed_count(total) + moving[0], moving[1]


def _sym2_orbit_unrank(total: int, rank: int) -> _Sym2:
    fixed = _sym2_fixed_count(total)
    if rank < fixed:
        return _sym2_fixed_unrank(total, rank)
    return _sym2_moving_unrank(total, rank - fixed)


def _apply_t_sym2(state: _Sym2) -> _Sym2:
    transformed = _t(state[0]), _t(state[1])
    if _raw_rank(transformed[1]) < _raw_rank(transformed[0]):
        return transformed[1], transformed[0]
    return transformed


# ---- Diagonal involution quotients for unequal bundle masses. ----


def _pair_quotient_count(left_mass: int, right_mass: int) -> int:
    raw = _raw_count(left_mass) * _raw_count(right_mass)
    fixed = _fixed_count(left_mass) * _fixed_count(right_mass)
    return (raw + fixed) // 2


def _pair_quotient_rank(left: _Vector, right: _Vector) -> int:
    left_mass = sum(left)
    right_mass = sum(right)
    left_fixed = _fixed_rank(left)
    if left_fixed is not None:
        right_orbit, _ = _orbit_rank(right)
        return left_fixed * _orbit_count(right_mass) + right_orbit
    left_moving = _moving_rank(left)
    assert left_moving is not None
    if left_moving[1]:
        right = _t(right)
    prefix = _fixed_count(left_mass) * _orbit_count(right_mass)
    return prefix + left_moving[0] * _raw_count(right_mass) + _raw_rank(right)


def _pair_quotient_unrank(
    left_mass: int,
    right_mass: int,
    rank: int,
) -> tuple[_Vector, _Vector]:
    fixed_block = _fixed_count(left_mass) * _orbit_count(right_mass)
    if rank < fixed_block:
        left_rank, right_rank = divmod(rank, _orbit_count(right_mass))
        return _fixed_unrank(left_mass, left_rank), _orbit_unrank(
            right_mass, right_rank
        )
    remaining = rank - fixed_block
    left_rank, right_rank = divmod(remaining, _raw_count(right_mass))
    return _moving_unrank(left_mass, left_rank), _raw_unrank(
        right_mass, right_rank
    )


def _distinct_block_count(masses: tuple[int, int, int]) -> int:
    first, second, third = masses
    raw_tail = _raw_count(second) * _raw_count(third)
    quotient_tail = _pair_quotient_count(second, third)
    return (
        _fixed_count(first) * quotient_tail
        + _moving_count(first) * raw_tail
    )


def _distinct_block_rank(bundles: _Bundles) -> int:
    masses = tuple(sum(bundle) for bundle in bundles)
    first, second, third = bundles
    first_fixed = _fixed_rank(first)
    if first_fixed is not None:
        tail_rank = _pair_quotient_rank(second, third)
        tail_count = _pair_quotient_count(masses[1], masses[2])
        return first_fixed * tail_count + tail_rank
    first_moving = _moving_rank(first)
    assert first_moving is not None
    if first_moving[1]:
        second, third = _t(second), _t(third)
    prefix = _fixed_count(masses[0]) * _pair_quotient_count(
        masses[1], masses[2]
    )
    raw_tail = _raw_count(masses[1]) * _raw_count(masses[2])
    tail_rank = _raw_rank(second) * _raw_count(masses[2]) + _raw_rank(third)
    return prefix + first_moving[0] * raw_tail + tail_rank


def _distinct_block_unrank(
    masses: tuple[int, int, int],
    rank: int,
) -> _Bundles:
    tail_count = _pair_quotient_count(masses[1], masses[2])
    fixed_block = _fixed_count(masses[0]) * tail_count
    if rank < fixed_block:
        first_rank, tail_rank = divmod(rank, tail_count)
        second, third = _pair_quotient_unrank(
            masses[1], masses[2], tail_rank
        )
        return _fixed_unrank(masses[0], first_rank), second, third
    remaining = rank - fixed_block
    raw_tail = _raw_count(masses[1]) * _raw_count(masses[2])
    first_rank, tail_rank = divmod(remaining, raw_tail)
    second_rank, third_rank = divmod(tail_rank, _raw_count(masses[2]))
    return (
        _moving_unrank(masses[0], first_rank),
        _raw_unrank(masses[1], second_rank),
        _raw_unrank(masses[2], third_rank),
    )


def _sym2_left_block_count(left_mass: int, right_mass: int) -> int:
    return (
        _sym2_fixed_count(left_mass) * _orbit_count(right_mass)
        + _sym2_moving_count(left_mass) * _raw_count(right_mass)
    )


def _sym2_left_block_rank(state: _Sym2, right: _Vector, total: int) -> int:
    fixed = _sym2_fixed_rank(state, total)
    if fixed is not None:
        right_orbit, _ = _orbit_rank(right)
        return fixed * _orbit_count(sum(right)) + right_orbit
    moving = _sym2_moving_rank(state, total)
    assert moving is not None
    if moving[1]:
        right = _t(right)
    prefix = _sym2_fixed_count(total) * _orbit_count(sum(right))
    return prefix + moving[0] * _raw_count(sum(right)) + _raw_rank(right)


def _sym2_left_block_unrank(
    left_mass: int,
    right_mass: int,
    rank: int,
) -> _Bundles:
    fixed_block = _sym2_fixed_count(left_mass) * _orbit_count(right_mass)
    if rank < fixed_block:
        left_rank, right_rank = divmod(rank, _orbit_count(right_mass))
        pair = _sym2_fixed_unrank(left_mass, left_rank)
        return pair[0], pair[1], _orbit_unrank(right_mass, right_rank)
    remaining = rank - fixed_block
    left_rank, right_rank = divmod(remaining, _raw_count(right_mass))
    pair = _sym2_moving_unrank(left_mass, left_rank)
    return pair[0], pair[1], _raw_unrank(right_mass, right_rank)


def _sym2_right_block_count(left_mass: int, right_mass: int) -> int:
    return (
        _fixed_count(left_mass) * _sym2_orbit_count(right_mass)
        + _moving_count(left_mass) * _sym2_raw_count(right_mass)
    )


def _sym2_right_block_rank(left: _Vector, state: _Sym2, total: int) -> int:
    fixed = _fixed_rank(left)
    if fixed is not None:
        state_orbit, _ = _sym2_orbit_rank(state, total)
        return fixed * _sym2_orbit_count(total) + state_orbit
    moving = _moving_rank(left)
    assert moving is not None
    if moving[1]:
        state = _apply_t_sym2(state)
    prefix = _fixed_count(sum(left)) * _sym2_orbit_count(total)
    return prefix + moving[0] * _sym2_raw_count(total) + _sym2_raw_rank(
        state, total
    )


def _sym2_right_block_unrank(
    left_mass: int,
    right_mass: int,
    rank: int,
) -> _Bundles:
    fixed_block = _fixed_count(left_mass) * _sym2_orbit_count(right_mass)
    if rank < fixed_block:
        left_rank, right_rank = divmod(rank, _sym2_orbit_count(right_mass))
        pair = _sym2_orbit_unrank(right_mass, right_rank)
        return _fixed_unrank(left_mass, left_rank), pair[0], pair[1]
    remaining = rank - fixed_block
    left_rank, right_rank = divmod(remaining, _sym2_raw_count(right_mass))
    pair = _sym2_raw_unrank(right_mass, right_rank)
    return _moving_unrank(left_mass, left_rank), pair[0], pair[1]


# ---- All-equal Sym^3 bundle block. ----


def _sym3_fixed_count(total: int) -> int:
    fixed = _fixed_count(total)
    moving = _moving_count(total)
    return comb(fixed + 2, 3) + fixed * moving


def _sym3_quotient_count(total: int) -> int:
    raw = comb(_raw_count(total) + 2, 3)
    return (raw + _sym3_fixed_count(total)) // 2


def _classify_bundle(vector: _Vector) -> tuple[str, int, int]:
    fixed = _fixed_rank(vector)
    if fixed is not None:
        return _FIXED_TAG, fixed, 0
    moving = _moving_rank(vector)
    assert moving is not None
    return _MOVING_TAG, moving[0], int(moving[1])


def _moving_vector(total: int, orbit: int, bit: int) -> _Vector:
    vector = _moving_unrank(total, orbit)
    return _t(vector) if bit else vector


def _sym3_rank_all_fixed(
    classes: list[tuple[str, int, int]],
    total: int,
) -> int:
    ranks = tuple(sorted(item[1] for item in classes))
    return _rep_combination_rank(ranks, _fixed_count(total))


def _sym3_rank_one_fixed(
    classes: list[tuple[str, int, int]],
    total: int,
) -> int:
    fixed_item = next(item for item in classes if item[0] == _FIXED_TAG)
    moving = sorted(item for item in classes if item[0] == _MOVING_TAG)
    fixed = _fixed_count(total)
    moving_count = _moving_count(total)
    prefix = _sym3_fixed_count(total) + comb(fixed + 1, 2) * moving_count
    left, right = moving
    if left[1] == right[1]:
        if left[2] != right[2]:
            return comb(fixed + 2, 3) + fixed_item[1] * moving_count + left[1]
        return prefix + fixed_item[1] * moving_count * moving_count + left[1]
    pair_rank = _strict_pair_rank(left[1], right[1], moving_count)
    parity = left[2] ^ right[2]
    local = moving_count + 2 * pair_rank + parity
    return prefix + fixed_item[1] * moving_count * moving_count + local


def _sym3_rank_two_fixed(
    classes: list[tuple[str, int, int]],
    total: int,
) -> int:
    fixed_ranks = tuple(
        sorted(item[1] for item in classes if item[0] == _FIXED_TAG)
    )
    moving = next(item for item in classes if item[0] == _MOVING_TAG)
    fixed = _fixed_count(total)
    moving_count = _moving_count(total)
    prefix = _sym3_fixed_count(total)
    pair_rank = _rep_combination_rank(fixed_ranks, fixed)
    return prefix + pair_rank * moving_count + moving[1]


def _ordered_distinct_pair_rank(left: int, right: int, population: int) -> int:
    assert left != right
    return left * (population - 1) + (right if right < left else right - 1)


def _ordered_distinct_pair_unrank(
    rank: int,
    population: int,
) -> tuple[int, int]:
    left, residual = divmod(rank, population - 1)
    right = residual if residual < left else residual + 1
    return left, right


def _sym3_moving_prefix(total: int) -> int:
    fixed = _fixed_count(total)
    moving = _moving_count(total)
    return (
        _sym3_fixed_count(total)
        + comb(fixed + 1, 2) * moving
        + fixed * moving * moving
    )


def _sym3_rank_same_moving(
    orbits: list[int],
    bits: list[int],
    prefix: int,
) -> int:
    minor = min(sum(bits), _BUNDLE_COUNT - sum(bits))
    return prefix + 2 * orbits[0] + minor


def _sym3_rank_doubled_moving(
    orbits: list[int],
    bits: list[int],
    moving_count: int,
    *,
    prefix: int,
) -> int:
    doubled = orbits[1]
    single = orbits[2] if orbits[0] == orbits[1] else orbits[0]
    doubled_bits = [
        bits[index]
        for index, orbit in enumerate(orbits)
        if orbit == doubled
    ]
    single_index = next(
        index for index, orbit in enumerate(orbits) if orbit == single
    )
    if doubled_bits[0] != doubled_bits[1]:
        kind = 0
    else:
        kind = 1 + (doubled_bits[0] ^ bits[single_index])
    pair_rank = _ordered_distinct_pair_rank(doubled, single, moving_count)
    return prefix + 3 * pair_rank + kind


def _sym3_rank_distinct_moving(
    orbits: list[int],
    bits: list[int],
    moving_count: int,
    *,
    prefix: int,
) -> int:
    triple_rank = _strict_triple_rank(
        (orbits[0], orbits[1], orbits[2]), moving_count
    )
    parity = 2 * (bits[0] ^ bits[1]) + (bits[0] ^ bits[2])
    return prefix + 4 * triple_rank + parity


def _sym3_rank_all_moving(
    classes: list[tuple[str, int, int]],
    total: int,
) -> int:
    moving_count = _moving_count(total)
    prefix = _sym3_moving_prefix(total)
    items = sorted((item[1], item[2]) for item in classes)
    orbits = [item[0] for item in items]
    bits = [item[1] for item in items]
    if orbits[0] == orbits[2]:
        return _sym3_rank_same_moving(orbits, bits, prefix)
    prefix += 2 * moving_count
    doubled = orbits[0] == orbits[1] or orbits[1] == orbits[2]
    if doubled:
        return _sym3_rank_doubled_moving(
            orbits, bits, moving_count, prefix=prefix
        )
    prefix += 3 * moving_count * (moving_count - 1)
    return _sym3_rank_distinct_moving(
        orbits, bits, moving_count, prefix=prefix
    )


def _sym3_quotient_rank(bundles: _Bundles, total: int) -> int:
    classes = [_classify_bundle(bundle) for bundle in bundles]
    fixed_items = sum(item[0] == _FIXED_TAG for item in classes)
    if fixed_items == _BUNDLE_COUNT:
        result = _sym3_rank_all_fixed(classes, total)
    elif fixed_items == _PAIR_COMPONENTS:
        result = _sym3_rank_two_fixed(classes, total)
    elif fixed_items == 1:
        result = _sym3_rank_one_fixed(classes, total)
    else:
        result = _sym3_rank_all_moving(classes, total)
    return result


def _sym3_unrank_all_fixed(total: int, rank: int) -> _Bundles:
    ranks = _rep_combination_unrank(_fixed_count(total), 3, rank)
    return (
        _fixed_unrank(total, ranks[0]),
        _fixed_unrank(total, ranks[1]),
        _fixed_unrank(total, ranks[2]),
    )


def _sym3_unrank_two_fixed(total: int, rank: int) -> _Bundles:
    moving = _moving_count(total)
    pair_rank, moving_rank = divmod(rank, moving)
    pair = _rep_combination_unrank(_fixed_count(total), 2, pair_rank)
    return (
        _fixed_unrank(total, pair[0]),
        _fixed_unrank(total, pair[1]),
        _moving_unrank(total, moving_rank),
    )


def _sym3_unrank_one_fixed(total: int, rank: int) -> _Bundles:
    moving = _moving_count(total)
    fixed_rank, local = divmod(rank, moving * moving)
    fixed_vector = _fixed_unrank(total, fixed_rank)
    if local < moving:
        item = _moving_unrank(total, local)
        return fixed_vector, item, item
    pair_rank, parity = divmod(local - moving, 2)
    pair = _strict_pair_unrank(pair_rank, moving)
    return (
        fixed_vector,
        _moving_unrank(total, pair[0]),
        _moving_vector(total, pair[1], parity),
    )


def _sym3_unrank_same_moving(total: int, rank: int) -> _Bundles:
    orbit, minor = divmod(rank, 2)
    base = _moving_unrank(total, orbit)
    if minor == 0:
        return base, base, base
    return base, base, _t(base)


def _sym3_unrank_doubled_moving(
    total: int,
    rank: int,
    moving: int,
) -> _Bundles:
    pair_rank, kind = divmod(rank, 3)
    doubled, single = _ordered_distinct_pair_unrank(pair_rank, moving)
    doubled_vector = _moving_unrank(total, doubled)
    single_vector = _moving_unrank(total, single)
    if kind == 0:
        return doubled_vector, _t(doubled_vector), single_vector
    if kind == 1:
        return doubled_vector, doubled_vector, single_vector
    return doubled_vector, doubled_vector, _t(single_vector)


def _sym3_unrank_distinct_moving(
    total: int,
    rank: int,
    moving: int,
) -> _Bundles:
    triple_rank, parity = divmod(rank, 4)
    orbits = _strict_triple_unrank(triple_rank, moving)
    return (
        _moving_unrank(total, orbits[0]),
        _moving_vector(total, orbits[1], (parity >> 1) & 1),
        _moving_vector(total, orbits[2], parity & 1),
    )


def _sym3_unrank_all_moving(total: int, rank: int) -> _Bundles:
    moving = _moving_count(total)
    same_block = 2 * moving
    doubled_block = 3 * moving * (moving - 1)
    if rank < same_block:
        result = _sym3_unrank_same_moving(total, rank)
    elif rank < same_block + doubled_block:
        result = _sym3_unrank_doubled_moving(
            total, rank - same_block, moving
        )
    else:
        result = _sym3_unrank_distinct_moving(
            total, rank - same_block - doubled_block, moving
        )
    return result


def _sym3_unrank_fixed_pair(total: int, rank: int) -> _Bundles:
    moving = _moving_count(total)
    fixed_rank, moving_rank = divmod(rank, moving)
    item = _moving_unrank(total, moving_rank)
    return _fixed_unrank(total, fixed_rank), item, _t(item)


def _sym3_quotient_unrank(total: int, rank: int) -> _Bundles:
    fixed = _fixed_count(total)
    moving = _moving_count(total)
    fixed3 = comb(fixed + 2, 3)
    fixed_pair = fixed * moving
    ffm = comb(fixed + 1, 2) * moving
    fmm = fixed * moving * moving
    if rank < fixed3:
        result = _sym3_unrank_all_fixed(total, rank)
    elif rank < fixed3 + fixed_pair:
        result = _sym3_unrank_fixed_pair(total, rank - fixed3)
    elif rank < fixed3 + fixed_pair + ffm:
        result = _sym3_unrank_two_fixed(
            total, rank - fixed3 - fixed_pair
        )
    elif rank < fixed3 + fixed_pair + ffm + fmm:
        result = _sym3_unrank_one_fixed(
            total, rank - fixed3 - fixed_pair - ffm
        )
    else:
        result = _sym3_unrank_all_moving(
            total, rank - fixed3 - fixed_pair - ffm - fmm
        )
    return result


# ---- Bundle mass blocks under the descended involution. ----

def _mass_triples(total: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (first, second, total - first - second)
        for first in range(total + 1)
        for second in range(first, total + 1)
        if second <= total - first - second
    )


def _bundle_block_count(masses: tuple[int, int, int]) -> int:
    first, second, third = masses
    if first == third:
        result = _sym3_quotient_count(first)
    elif first == second:
        result = _sym2_left_block_count(first, third)
    elif second == third:
        result = _sym2_right_block_count(first, second)
    else:
        result = _distinct_block_count(masses)
    return result


@cache
def _bundle_quotient_count(total: int) -> int:
    return sum(_bundle_block_count(masses) for masses in _mass_triples(total))


def _bundle_quotient_rank(bundles: _Bundles) -> int:
    ordered_items = sorted(
        bundles, key=lambda item: (sum(item), _raw_rank(item))
    )
    ordered: _Bundles = (
        ordered_items[0],
        ordered_items[1],
        ordered_items[2],
    )
    masses = (sum(ordered[0]), sum(ordered[1]), sum(ordered[2]))
    prefix = sum(
        _bundle_block_count(candidate)
        for candidate in _mass_triples(sum(masses))
        if candidate < masses
    )
    first, second, third = masses
    if first == third:
        local = _sym3_quotient_rank(ordered, first)
    elif first == second:
        local = _sym2_left_block_rank(
            (ordered[0], ordered[1]), ordered[2], first
        )
    elif second == third:
        local = _sym2_right_block_rank(
            ordered[0], (ordered[1], ordered[2]), second
        )
    else:
        local = _distinct_block_rank(ordered)
    return prefix + local


def _unrank_bundle_block(
    masses: tuple[int, int, int],
    rank: int,
) -> _Bundles:
    first, second, third = masses
    if first == third:
        result = _sym3_quotient_unrank(first, rank)
    elif first == second:
        result = _sym2_left_block_unrank(first, third, rank)
    elif second == third:
        result = _sym2_right_block_unrank(first, second, rank)
    else:
        result = _distinct_block_unrank(masses, rank)
    return result


def _bundle_quotient_unrank(total: int, rank: int) -> _Bundles:
    assert 0 <= rank < _bundle_quotient_count(total)
    remaining = rank
    for masses in _mass_triples(total):
        block = _bundle_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        return _unrank_bundle_block(masses, remaining)
    raise AssertionError


def _s3_block_count(masses: tuple[int, int, int]) -> int:
    first, second, third = masses
    counts = tuple(_raw_count(mass) for mass in masses)
    if first == third:
        result = comb(counts[0] + 2, 3)
    elif first == second:
        result = comb(counts[0] + 1, 2) * counts[2]
    elif second == third:
        result = counts[0] * comb(counts[1] + 1, 2)
    else:
        result = counts[0] * counts[1] * counts[2]
    return result


def _s3_bundle_count(total: int) -> int:
    return sum(_s3_block_count(masses) for masses in _mass_triples(total))


def _s3_block_rank(
    bundles: _Bundles,
    masses: tuple[int, int, int],
) -> int:
    ranks = tuple(_raw_rank(bundle) for bundle in bundles)
    first, second, third = masses
    counts = tuple(_raw_count(mass) for mass in masses)
    if first == third:
        result = _rep_combination_rank(tuple(sorted(ranks)), counts[0])
    elif first == second:
        pair = _rep_combination_rank(tuple(sorted(ranks[:2])), counts[0])
        result = pair * counts[2] + ranks[2]
    elif second == third:
        pair = _rep_combination_rank(tuple(sorted(ranks[1:])), counts[1])
        result = ranks[0] * comb(counts[1] + 1, 2) + pair
    else:
        result = (ranks[0] * counts[1] + ranks[1]) * counts[2] + ranks[2]
    return result


def _s3_bundle_rank(bundles: _Bundles) -> int:
    ordered_items = sorted(
        bundles,
        key=lambda item: (sum(item), _raw_rank(item)),
    )
    ordered: _Bundles = ordered_items[0], ordered_items[1], ordered_items[2]
    masses = sum(ordered[0]), sum(ordered[1]), sum(ordered[2])
    prefix = sum(
        _s3_block_count(candidate)
        for candidate in _mass_triples(sum(masses))
        if candidate < masses
    )
    return prefix + _s3_block_rank(ordered, masses)


def _s3_equal_rank_tuple(count: int, rank: int) -> tuple[int, int, int]:
    values = _rep_combination_unrank(count, 3, rank)
    first, second, third = values
    return first, second, third


def _s3_first_equal_rank_tuple(
    counts: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    pair_rank, third_rank = divmod(rank, counts[2])
    pair = _rep_combination_unrank(counts[0], 2, pair_rank)
    first, second = pair
    return first, second, third_rank


def _s3_last_equal_rank_tuple(
    counts: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    first_rank, pair_rank = divmod(rank, comb(counts[1] + 1, 2))
    pair = _rep_combination_unrank(counts[1], 2, pair_rank)
    second, third = pair
    return first_rank, second, third


def _s3_distinct_rank_tuple(
    counts: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    first_rank, residual = divmod(rank, counts[1] * counts[2])
    second_rank, third_rank = divmod(residual, counts[2])
    return first_rank, second_rank, third_rank


def _s3_block_rank_tuple(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    counts = (
        _raw_count(masses[0]),
        _raw_count(masses[1]),
        _raw_count(masses[2]),
    )
    if masses[0] == masses[2]:
        result = _s3_equal_rank_tuple(counts[0], rank)
    elif masses[0] == masses[1]:
        result = _s3_first_equal_rank_tuple(counts, rank)
    elif masses[1] == masses[2]:
        result = _s3_last_equal_rank_tuple(counts, rank)
    else:
        result = _s3_distinct_rank_tuple(counts, rank)
    return result


def _s3_block_unrank(masses: tuple[int, int, int], rank: int) -> _Bundles:
    ranks = _s3_block_rank_tuple(masses, rank)
    first = _raw_unrank(masses[0], ranks[0])
    second = _raw_unrank(masses[1], ranks[1])
    third = _raw_unrank(masses[2], ranks[2])
    return first, second, third


def _s3_bundle_unrank(total: int, rank: int) -> _Bundles:
    assert 0 <= rank < _s3_bundle_count(total)
    remaining = rank
    for masses in _mass_triples(total):
        block = _s3_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        return _s3_block_unrank(masses, remaining)
    raise AssertionError


def _x_t(vector: _Vector) -> _Vector:
    assert len(vector) == _X_COMPONENTS
    middle = _X_FIXED_COMPONENTS + _X_SIDE_COMPONENTS
    return (
        vector[:_X_FIXED_COMPONENTS]
        + vector[middle:]
        + vector[_X_FIXED_COMPONENTS:middle]
    )


def _x_raw_count(total: int) -> int:
    return _composition_count(total, _X_COMPONENTS)


@cache
def _x_fixed_count(total: int) -> int:
    return sum(
        _composition_count(core_mass, _X_FIXED_COMPONENTS)
        * _composition_count((total - core_mass) // 2, _X_SIDE_COMPONENTS)
        for core_mass in range(total + 1)
        if (total - core_mass) % 2 == 0
    )


def _x_moving_count(total: int) -> int:
    return (_x_raw_count(total) - _x_fixed_count(total)) // 2


def _x_side_count(total: int) -> int:
    result = sum(
        _composition_count(left, _X_SIDE_COMPONENTS)
        * _composition_count(total - left, _X_SIDE_COMPONENTS)
        for left in range((total + 1) // 2)
    )
    if total % 2 == 0:
        population = _composition_count(total // 2, _X_SIDE_COMPONENTS)
        result += comb(population, 2)
    return result


def _x_side_rank(left: _Vector, right: _Vector) -> tuple[int, bool] | None:
    left_key = _pair_key(left)
    right_key = _pair_key(right)
    flipped = right_key < left_key
    if flipped:
        left, right = right, left
        left_key, right_key = right_key, left_key
    if left == right:
        return None
    total = left_key[0] + right_key[0]
    prefix = sum(
        _composition_count(mass, _X_SIDE_COMPONENTS)
        * _composition_count(total - mass, _X_SIDE_COMPONENTS)
        for mass in range(left_key[0])
        if mass < total - mass
    )
    if left_key[0] < right_key[0]:
        offset = left_key[1] * _composition_count(
            right_key[0], _X_SIDE_COMPONENTS
        ) + right_key[1]
    else:
        population = _composition_count(left_key[0], _X_SIDE_COMPONENTS)
        offset = _strict_pair_rank(left_key[1], right_key[1], population)
    return prefix + offset, flipped


def _x_side_unrank(total: int, rank: int) -> tuple[_Vector, _Vector]:
    assert 0 <= rank < _x_side_count(total)
    remaining = rank
    for left_mass in range((total + 1) // 2):
        right_mass = total - left_mass
        right_count = _composition_count(right_mass, _X_SIDE_COMPONENTS)
        block = _composition_count(left_mass, _X_SIDE_COMPONENTS) * right_count
        if remaining >= block:
            remaining -= block
            continue
        left_rank, right_rank = divmod(remaining, right_count)
        left = _composition_unrank(left_mass, _X_SIDE_COMPONENTS, left_rank)
        right = _composition_unrank(right_mass, _X_SIDE_COMPONENTS, right_rank)
        assert left is not None
        assert right is not None
        return left, right
    half = total // 2
    population = _composition_count(half, _X_SIDE_COMPONENTS)
    left_rank, right_rank = _strict_pair_unrank(remaining, population)
    left = _composition_unrank(half, _X_SIDE_COMPONENTS, left_rank)
    right = _composition_unrank(half, _X_SIDE_COMPONENTS, right_rank)
    assert left is not None
    assert right is not None
    return left, right


def _x_fixed_rank(vector: _Vector) -> int | None:
    if len(vector) != _X_COMPONENTS or _x_t(vector) != vector:
        return None
    core = vector[:_X_FIXED_COMPONENTS]
    middle = _X_FIXED_COMPONENTS + _X_SIDE_COMPONENTS
    side = vector[_X_FIXED_COMPONENTS:middle]
    core_mass = sum(core)
    side_mass = sum(side)
    total = core_mass + 2 * side_mass
    core_rank = _composition_rank(core, core_mass)
    side_rank = _composition_rank(side, side_mass)
    assert core_rank is not None
    assert side_rank is not None
    prefix = sum(
        _composition_count(total - 2 * mass, _X_FIXED_COMPONENTS)
        * _composition_count(mass, _X_SIDE_COMPONENTS)
        for mass in range(side_mass)
    )
    side_count = _composition_count(side_mass, _X_SIDE_COMPONENTS)
    return prefix + core_rank * side_count + side_rank


def _x_fixed_unrank(total: int, rank: int) -> _Vector:
    assert 0 <= rank < _x_fixed_count(total)
    remaining = rank
    for side_mass in range(total // 2 + 1):
        core_mass = total - 2 * side_mass
        side_count = _composition_count(side_mass, _X_SIDE_COMPONENTS)
        block = _composition_count(core_mass, _X_FIXED_COMPONENTS) * side_count
        if remaining >= block:
            remaining -= block
            continue
        core_rank, side_rank = divmod(remaining, side_count)
        core = _composition_unrank(core_mass, _X_FIXED_COMPONENTS, core_rank)
        side = _composition_unrank(side_mass, _X_SIDE_COMPONENTS, side_rank)
        assert core is not None
        assert side is not None
        return core + side + side
    raise AssertionError


def _x_moving_rank(vector: _Vector) -> tuple[int, bool] | None:
    if len(vector) != _X_COMPONENTS or any(value < 0 for value in vector):
        return None
    core = vector[:_X_FIXED_COMPONENTS]
    middle = _X_FIXED_COMPONENTS + _X_SIDE_COMPONENTS
    sides = _x_side_rank(vector[_X_FIXED_COMPONENTS:middle], vector[middle:])
    if sides is None:
        return None
    core_mass = sum(core)
    core_rank = _composition_rank(core, core_mass)
    assert core_rank is not None
    side_mass = sum(vector[_X_FIXED_COMPONENTS:])
    total = core_mass + side_mass
    prefix = sum(
        _composition_count(mass, _X_FIXED_COMPONENTS)
        * _x_side_count(total - mass)
        for mass in range(core_mass)
    )
    return prefix + core_rank * _x_side_count(side_mass) + sides[0], sides[1]


def _x_moving_unrank(total: int, rank: int) -> _Vector:
    assert 0 <= rank < _x_moving_count(total)
    remaining = rank
    for core_mass in range(total + 1):
        side_mass = total - core_mass
        side_count = _x_side_count(side_mass)
        block = _composition_count(core_mass, _X_FIXED_COMPONENTS) * side_count
        if remaining >= block:
            remaining -= block
            continue
        core_rank, side_rank = divmod(remaining, side_count)
        core = _composition_unrank(core_mass, _X_FIXED_COMPONENTS, core_rank)
        sides = _x_side_unrank(side_mass, side_rank)
        assert core is not None
        return core + sides[0] + sides[1]
    raise AssertionError


def _apply_t_bundles(bundles: _Bundles) -> _Bundles:
    transformed = tuple(_t(bundle) for bundle in bundles)
    ordered = sorted(transformed, key=lambda item: (sum(item), _raw_rank(item)))
    return ordered[0], ordered[1], ordered[2]


def _residual_block_count(total: int, x_mass: int) -> int:
    bundle_mass = total - x_mass
    fixed = _x_fixed_count(x_mass)
    moving = _x_moving_count(x_mass)
    return (
        fixed * _bundle_quotient_count(bundle_mass)
        + moving * _s3_bundle_count(bundle_mass)
    )


@cache
def _residual_count(total: int) -> int:
    return sum(
        _residual_block_count(total, x_mass)
        for x_mass in range(total + 1)
    )


def _rank_fixed_x_residual(
    x: _Vector,
    bundles: _Bundles,
    *,
    bundle_mass: int,
    prefix: int,
) -> int | None:
    fixed_rank = _x_fixed_rank(x)
    if fixed_rank is None:
        return None
    return (
        prefix
        + fixed_rank * _bundle_quotient_count(bundle_mass)
        + _bundle_quotient_rank(bundles)
    )


def _rank_moving_x_residual(
    x: _Vector,
    bundles: _Bundles,
    masses: tuple[int, int],
    *,
    prefix: int,
) -> int:
    x_mass, bundle_mass = masses
    moving = _x_moving_rank(x)
    assert moving is not None
    x_rank, flipped = moving
    if flipped:
        bundles = _apply_t_bundles(bundles)
    fixed_block = _x_fixed_count(x_mass) * _bundle_quotient_count(bundle_mass)
    return (
        prefix
        + fixed_block
        + x_rank * _s3_bundle_count(bundle_mass)
        + _s3_bundle_rank(bundles)
    )


def _residual_rank(state: _ResidualState) -> int | None:
    x, first, second, third = state
    if len(x) != _X_COMPONENTS:
        return None
    bundles: _Bundles = first, second, third
    x_mass = sum(x)
    bundle_mass = sum(sum(bundle) for bundle in bundles)
    total = x_mass + bundle_mass
    prefix = sum(
        _residual_block_count(total, mass) for mass in range(x_mass)
    )
    fixed = _rank_fixed_x_residual(
        x,
        bundles,
        bundle_mass=bundle_mass,
        prefix=prefix,
    )
    if fixed is not None:
        return fixed
    return _rank_moving_x_residual(
        x,
        bundles,
        (x_mass, bundle_mass),
        prefix=prefix,
    )


def _unrank_residual_block(
    x_mass: int,
    bundle_mass: int,
    rank: int,
) -> _ResidualState:
    quotient_count = _bundle_quotient_count(bundle_mass)
    fixed_block = _x_fixed_count(x_mass) * quotient_count
    if rank < fixed_block:
        x_rank, bundle_rank = divmod(rank, quotient_count)
        x = _x_fixed_unrank(x_mass, x_rank)
        bundles = _bundle_quotient_unrank(bundle_mass, bundle_rank)
    else:
        residual = rank - fixed_block
        raw_count = _s3_bundle_count(bundle_mass)
        x_rank, bundle_rank = divmod(residual, raw_count)
        x = _x_moving_unrank(x_mass, x_rank)
        bundles = _s3_bundle_unrank(bundle_mass, bundle_rank)
    return x, bundles[0], bundles[1], bundles[2]


def _residual_unrank(total: int, rank: int) -> _ResidualState | None:
    if rank < 0 or rank >= _residual_count(total):
        return None
    remaining = rank
    for x_mass in range(total + 1):
        bundle_mass = total - x_mass
        block = _residual_block_count(total, x_mass)
        if remaining >= block:
            remaining -= block
            continue
        return _unrank_residual_block(x_mass, bundle_mass, remaining)
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


def _active_endpoint(label: int) -> int:
    bits = tuple(
        (label >> (_ARITY - endpoint - 1)) & 1
        for endpoint in range(_BUNDLE_COUNT)
    )
    weight = sum(bits)
    assert weight in {1, 2}
    return bits.index(1) if weight == 1 else bits.index(0)


def _s3_label_orbits(
) -> tuple[tuple[int, ...], tuple[tuple[int, int, int], ...]]:
    unseen = set(_RESIDUAL_LABELS)
    fixed: list[int] = []
    triples: list[tuple[int, int, int]] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(sorted({_permuted_symbol(seed, order) for order in _S3}))
        unseen -= set(orbit)
        if len(orbit) == 1:
            fixed.append(orbit[0])
            continue
        assert len(orbit) == _BUNDLE_COUNT
        by_endpoint = {_active_endpoint(label): label for label in orbit}
        triples.append((by_endpoint[0], by_endpoint[1], by_endpoint[2]))
    return tuple(fixed), tuple(triples)


def _involution_order(
    items: tuple[object, ...],
    image_of: dict[int, int],
) -> tuple[int, ...]:
    seen: set[int] = set()
    fixed: list[int] = []
    left: list[int] = []
    right: list[int] = []
    for index in range(len(items)):
        if index in seen:
            continue
        other = image_of[index]
        if other == index:
            fixed.append(index)
            seen.add(index)
        else:
            first, second = sorted((index, other))
            left.append(first)
            right.append(second)
            seen.update((first, second))
    return *fixed, *left, *right


def _label_layout() -> tuple[tuple[int, ...], tuple[tuple[int, int, int], ...]]:
    fixed, triples = _s3_label_orbits()
    fixed_index = {label: index for index, label in enumerate(fixed)}
    fixed_image = {
        index: fixed_index[_permuted_symbol(label, _C)]
        for index, label in enumerate(fixed)
    }
    fixed_order = _involution_order(fixed, fixed_image)
    triple_index = {
        frozenset(item): index for index, item in enumerate(triples)
    }
    triple_image = {
        index: triple_index[
            frozenset(_permuted_symbol(label, _C) for label in item)
        ]
        for index, item in enumerate(triples)
    }
    triple_order = _involution_order(triples, triple_image)
    ordered_fixed = tuple(fixed[index] for index in fixed_order)
    ordered_triples = tuple(triples[index] for index in triple_order)
    return ordered_fixed, ordered_triples


_X_LABELS, _BUNDLE_LABELS = _label_layout()


def _extract_residual(vector: _Vector) -> _ResidualState | None:
    valid_length = len(vector) == _RESIDUAL_COMPONENTS
    if not valid_length or any(value < 0 for value in vector):
        return None
    values = {label: vector[_LABEL_INDEX[label]] for label in _RESIDUAL_LABELS}
    x = tuple(values[label] for label in _X_LABELS)
    bundles = tuple(
        tuple(values[item[endpoint]] for item in _BUNDLE_LABELS)
        for endpoint in _ACTIVE_ENDPOINTS
    )
    first, second, third = bundles
    return x, first, second, third


def _build_residual(state: _ResidualState) -> _Vector:
    x, first, second, third = state
    values: dict[int, int] = {}
    values.update(zip(_X_LABELS, x, strict=True))
    bundles: _Bundles = first, second, third
    for endpoint, bundle in enumerate(bundles):
        for labels, value in zip(_BUNDLE_LABELS, bundle, strict=True):
            values[labels[endpoint]] = value
    assert set(values) == set(_RESIDUAL_LABELS)
    return tuple(values[label] for label in _RESIDUAL_LABELS)


def _compose(left: _Permutation, right: _Permutation) -> _Permutation:
    values = tuple(left[right[index]] for index in range(_ARITY))
    first, second, third, fourth, fifth, sixth = values
    return first, second, third, fourth, fifth, sixth


_PRODUCT_GROUP = tuple(
    _compose(order, suffix)
    for order in _S3
    for suffix in (_IDENTITY, _C)
)


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
    transposition = _fixed_count_from_cycles(total, (1,) * 24 + (2,) * 14)
    double_swap = _fixed_count_from_cycles(total, (1,) * 12 + (2,) * 20)
    three_cycle = _fixed_count_from_cycles(total, (1,) * 10 + (3,) * 14)
    mixed = _fixed_count_from_cycles(
        total,
        (1,) * 6 + (2,) * 2 + (3,) * 6 + (6,) * 4,
    )
    return (
        identity
        + 4 * transposition
        + 3 * double_swap
        + 2 * three_cycle
        + 2 * mixed
    ) // 12


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


def _state_rank_data(
    total: int,
    state: _State,
) -> tuple[int, int, int, int] | None:
    vertices, vector = state
    vertex_mass = sum(sum(pair) for pair in vertices)
    residual_mass = total - vertex_mass
    vertex_rank = _vertex_rank(vertices, vertex_mass)
    residual = _extract_residual(vector)
    residual_rank = None if residual is None else _residual_rank(residual)
    valid_mass = vertex_mass <= total and sum(vector) == residual_mass
    valid_ranks = vertex_rank is not None and residual_rank is not None
    result: tuple[int, int, int, int] | None = None
    if valid_mass and valid_ranks:
        assert vertex_rank is not None
        assert residual_rank is not None
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
        vertices = _vertices_of_mass(vertex_mass)[vertex_rank]
        return vertices, _build_residual(residual)
    raise AssertionError


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def test_s6_s3s2_label_layout_has_exact_product_geometry() -> None:
    """The 52 labels realize X=(6;2,2) and three Z=(6;4,4) bundles."""
    assert len(_X_LABELS) == _X_COMPONENTS
    assert len(_BUNDLE_LABELS) == _BUNDLE_COMPONENTS
    for total in range(_EXHAUSTIVE_RESIDUAL_MASS + 1):
        for vector in _weak_compositions(total, _RESIDUAL_COMPONENTS):
            state = _extract_residual(vector)
            assert state is not None
            assert _build_residual(state) == vector


def test_s6_s3s2_residual_rank_matches_direct_small_orbits() -> None:
    """Small residual assignments collapse to one contiguous product rank."""
    for total in range(_EXHAUSTIVE_RESIDUAL_MASS + 1):
        representatives: dict[int, set[_Vector]] = {}
        for vector in _weak_compositions(total, _RESIDUAL_COMPONENTS):
            state = _extract_residual(vector)
            assert state is not None
            rank = _residual_rank(state)
            assert rank is not None
            orbit = {
                _permute_residual(vector, order) for order in _PRODUCT_GROUP
            }
            if rank not in representatives:
                representatives[rank] = orbit
            assert representatives[rank] == orbit
        count = _residual_count(total)
        assert set(representatives) == set(range(count))
        assert count == _burnside_residual_count(total)


def test_s6_s3s2_rank_exhausts_small_full_strata() -> None:
    """The complete product-group stratum is dense through mass five."""
    for total in range(_EXHAUSTIVE_TOTAL_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s3s2_rank_roundtrips_through_mass_fourteen() -> None:
    """Boundary and interior ranks roundtrip throughout the admitted range."""
    for total in range(_MAXIMUM_MASS + 1):
        assert _residual_count(total) == _burnside_residual_count(total)
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


def test_s6_s3s2_counts_match_reviewed_sequence() -> None:
    """The mass-three-through-fourteen counts match the decomposition."""
    observed = {
        mass: _class_count(mass)
        for mass in range(_MAXIMUM_MASS + 1)
        if _class_count(mass) != 0
    }
    assert observed == _EXPECTED_COUNTS
