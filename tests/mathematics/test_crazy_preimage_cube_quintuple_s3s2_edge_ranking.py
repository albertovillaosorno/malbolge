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
#   - Dense rank/unrank evidence for pair-valued K5 edges under a residual
#     S3xS2 stabilizer on disjoint equal vertex blocks of sizes three and two.
# - Must-Not:
#   - Claim ranking for S4/S5 residual stabilizers or complete dense S5 ranking.
# - Allows:
#   - Inputs: residual edge-pair mass zero through fourteen.
#   - Outputs: exact dense S3xS2 rank/unrank.
#   - Side effects: none.
# - Split-When:
#   - The residual stabilizer is not conjugate to S3xS2.
# - Merge-When:
#   - Complete dense S5 ranking owns this three-bundle involution quotient.
# - Summary:
#   - Densely rank residual S3xS2 pair-valued K5 edge orbits.
# - Description:
#   - Quotients three six-count bundles by S3, then by their common internal
#     involution using fixed/nonfixed multiset blocks.
# - Usage:
#   - Constructive coverage for the order-twelve S5 residual strata.
# - Defaults:
#   - Direct product-group orbit exhaustion stops at mass three.
#

"""Dense residual S3xS2 ranking for pair-valued K5 edge assignments."""

from __future__ import annotations

from functools import cache
from itertools import permutations
from math import comb

_ACTIVE_VERTICES = (0, 1, 2)
_BUNDLE_COMPONENTS = 6
_EDGE_COUNT = 10
_EXHAUSTIVE_MASS = 3
_FIXED_COMPONENTS = 2
_PAIR_COMPONENTS = 2
_BUNDLE_COUNT = 3
_FIXED_TAG = "f"
_MOVING_TAG = "m"
_MAXIMUM_MASS = 14
_WIDTH_FOURTEEN_COUNT = 68_763_298
_EDGES = tuple(
    (left, right)
    for left in range(5)
    for right in range(left + 1, 5)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_FIXED_EDGE = (3, 4)
_S3_ORDERS = tuple((*order, 3, 4) for order in permutations(_ACTIVE_VERTICES))
_SWAP = (0, 1, 2, 4, 3)
_IDENTITY = (0, 1, 2, 3, 4)

type _Pair = tuple[int, int]
type _EdgePairs = tuple[_Pair, ...]
type _Vector = tuple[int, ...]
type _Bundles = tuple[_Vector, _Vector, _Vector]
type _Sym2 = tuple[_Vector, _Vector]


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
    return vector[0:2] + vector[4:6] + vector[2:4]


def _raw_count(total: int) -> int:
    return _composition_count(total, _BUNDLE_COMPONENTS)


@cache
def _fixed_count(total: int) -> int:
    return sum(
        _composition_count(margin_mass, 2)
        * _composition_count((total - margin_mass) // 2, 2)
        for margin_mass in range(total + 1)
        if (total - margin_mass) % 2 == 0
    )


def _moving_count(total: int) -> int:
    return (_raw_count(total) - _fixed_count(total)) // 2


def _orbit_count(total: int) -> int:
    return _fixed_count(total) + _moving_count(total)


def _fixed_rank(vector: _Vector) -> int | None:
    if len(vector) != _BUNDLE_COMPONENTS or _t(vector) != vector:
        return None
    margin = vector[0:2]
    side = vector[2:4]
    margin_mass = sum(margin)
    side_mass = sum(side)
    total = margin_mass + 2 * side_mass
    margin_rank = _composition_rank(margin, margin_mass)
    side_rank = _composition_rank(side, side_mass)
    assert margin_rank is not None
    assert side_rank is not None
    prefix = sum(
        _composition_count(mass, 2)
        * _composition_count((total - mass) // 2, 2)
        for mass in range(margin_mass)
        if (total - mass) % 2 == 0
    )
    return prefix + margin_rank * _composition_count(side_mass, 2) + side_rank


def _fixed_unrank(total: int, rank: int) -> _Vector:
    assert 0 <= rank < _fixed_count(total)
    remaining = rank
    for margin_mass in range(total + 1):
        if (total - margin_mass) % 2 != 0:
            continue
        side_mass = (total - margin_mass) // 2
        side_count = _composition_count(side_mass, 2)
        block = _composition_count(margin_mass, 2) * side_count
        if remaining >= block:
            remaining -= block
            continue
        margin_rank, side_rank = divmod(remaining, side_count)
        margin = _composition_unrank(margin_mass, 2, margin_rank)
        side = _composition_unrank(side_mass, 2, side_rank)
        assert margin is not None
        assert side is not None
        return margin + side + side
    raise AssertionError


def _side_moving_count(total: int) -> int:
    count = 0
    for left_mass in range((total + 1) // 2):
        right_mass = total - left_mass
        count += _composition_count(left_mass, 2) * _composition_count(
            right_mass, 2
        )
    if total % 2 == 0:
        half = total // 2
        population = _composition_count(half, 2)
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
    if len(left) == _PAIR_COMPONENTS and len(right) == _PAIR_COMPONENTS:
        left_key = _pair_key(left)
        right_key = _pair_key(right)
        flipped = right_key < left_key
        if flipped:
            left, right = right, left
            left_key, right_key = right_key, left_key
        if left != right:
            total = left_key[0] + right_key[0]
            prefix = sum(
                _composition_count(mass, _PAIR_COMPONENTS)
                * _composition_count(total - mass, _PAIR_COMPONENTS)
                for mass in range(left_key[0])
                if mass < total - mass
            )
            if left_key[0] < right_key[0]:
                rank = prefix + left_key[1] * _composition_count(
                    right_key[0], _PAIR_COMPONENTS
                )
                result = rank + right_key[1], flipped
            else:
                population = _composition_count(
                    left_key[0], _PAIR_COMPONENTS
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
        left_count = _composition_count(left_mass, _PAIR_COMPONENTS)
        right_count = _composition_count(right_mass, _PAIR_COMPONENTS)
        block = left_count * right_count
        if remaining >= block:
            remaining -= block
            continue
        left_rank, right_rank = divmod(remaining, right_count)
        left = _composition_unrank(left_mass, _PAIR_COMPONENTS, left_rank)
        right = _composition_unrank(right_mass, _PAIR_COMPONENTS, right_rank)
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
        _composition_count(mass, _PAIR_COMPONENTS)
        * _composition_count(total - mass, _PAIR_COMPONENTS)
        for mass in range((total + 1) // 2)
        if mass < total - mass
    )
    half = total // 2
    population = _composition_count(half, _PAIR_COMPONENTS)
    left_rank, right_rank = _strict_pair_unrank(
        rank - unequal_count, population
    )
    left = _composition_unrank(half, _PAIR_COMPONENTS, left_rank)
    right = _composition_unrank(half, _PAIR_COMPONENTS, right_rank)
    assert left is not None
    assert right is not None
    return left, right


def _moving_rank(vector: _Vector) -> tuple[int, bool] | None:
    if len(vector) != _BUNDLE_COMPONENTS or any(value < 0 for value in vector):
        return None
    margin = vector[0:2]
    sides = _side_moving_rank(vector[2:4], vector[4:6])
    if sides is None:
        return None
    margin_mass = sum(margin)
    margin_rank = _composition_rank(margin, margin_mass)
    assert margin_rank is not None
    side_mass = sum(vector[2:6])
    total = margin_mass + side_mass
    prefix = sum(
        _composition_count(mass, 2) * _side_moving_count(total - mass)
        for mass in range(margin_mass)
    )
    rank = prefix + margin_rank * _side_moving_count(side_mass) + sides[0]
    return rank, sides[1]


def _moving_unrank(total: int, rank: int) -> _Vector:
    assert 0 <= rank < _moving_count(total)
    remaining = rank
    for margin_mass in range(total + 1):
        side_mass = total - margin_mass
        side_count = _side_moving_count(side_mass)
        block = _composition_count(margin_mass, 2) * side_count
        if remaining >= block:
            remaining -= block
            continue
        margin_rank, side_rank = divmod(remaining, side_count)
        margin = _composition_unrank(margin_mass, 2, margin_rank)
        sides = _side_moving_unrank(side_mass, side_rank)
        assert margin is not None
        return margin + sides[0] + sides[1]
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


# ---- Bundle mass blocks and full K5 edge rank. ----


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


def _edge_orbit_count(total: int) -> int:
    return sum(
        _composition_count(fixed_mass, _FIXED_COMPONENTS)
        * _bundle_quotient_count(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def _bundle_edges(vertex: int) -> tuple[tuple[int, int], ...]:
    others = tuple(value for value in _ACTIVE_VERTICES if value != vertex)
    left, right = others[0], others[1]
    opposite = (left, right) if left < right else (right, left)
    return opposite, (vertex, 3), (vertex, 4)


def _flatten(
    edge_pairs: _EdgePairs,
    edges: tuple[tuple[int, int], ...],
) -> _Vector:
    values: list[int] = []
    for edge in edges:
        values.extend(edge_pairs[_EDGE_INDEX[edge]])
    return tuple(values)


def _rank(edge_pairs: _EdgePairs) -> int | None:
    if len(edge_pairs) != _EDGE_COUNT or any(
        value < 0 for pair in edge_pairs for value in pair
    ):
        return None
    fixed = _flatten(edge_pairs, (_FIXED_EDGE,))
    bundles = tuple(
        _flatten(edge_pairs, _bundle_edges(vertex))
        for vertex in _ACTIVE_VERTICES
    )
    fixed_mass = sum(fixed)
    fixed_rank = _composition_rank(fixed, fixed_mass)
    assert fixed_rank is not None
    bundle_mass = sum(sum(bundle) for bundle in bundles)
    total = fixed_mass + bundle_mass
    prefix = sum(
        _composition_count(mass, _FIXED_COMPONENTS)
        * _bundle_quotient_count(total - mass)
        for mass in range(fixed_mass)
    )
    return (
        prefix
        + fixed_rank * _bundle_quotient_count(bundle_mass)
        + _bundle_quotient_rank((bundles[0], bundles[1], bundles[2]))
    )


def _assign_bundle(
    result: list[_Pair | None],
    vertex: int,
    bundle: _Vector,
) -> None:
    pairs = tuple(
        (bundle[index], bundle[index + 1])
        for index in range(0, _BUNDLE_COMPONENTS, _PAIR_COMPONENTS)
    )
    for edge, pair in zip(_bundle_edges(vertex), pairs, strict=True):
        result[_EDGE_INDEX[edge]] = pair


def _unrank(total: int, rank: int) -> _EdgePairs | None:
    if rank < 0 or rank >= _edge_orbit_count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        bundle_mass = total - fixed_mass
        bundle_count = _bundle_quotient_count(bundle_mass)
        fixed_count = _composition_count(fixed_mass, _FIXED_COMPONENTS)
        block = fixed_count * bundle_count
        if remaining >= block:
            remaining -= block
            continue
        fixed_rank, bundle_rank = divmod(remaining, bundle_count)
        fixed = _composition_unrank(fixed_mass, _FIXED_COMPONENTS, fixed_rank)
        bundles = _bundle_quotient_unrank(bundle_mass, bundle_rank)
        assert fixed is not None
        result: list[_Pair | None] = [None] * _EDGE_COUNT
        result[_EDGE_INDEX[_FIXED_EDGE]] = (fixed[0], fixed[1])
        for vertex, bundle in zip(_ACTIVE_VERTICES, bundles, strict=True):
            _assign_bundle(result, vertex, bundle)
        assert all(pair is not None for pair in result)
        return tuple(pair for pair in result if pair is not None)
    raise AssertionError


def _compose(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(left[right[index]] for index in range(len(left)))


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
        for index in range(0, 20, _PAIR_COMPONENTS)
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
    transposition = _fixed_scalar_count((1,) * 8 + (2,) * 6, total)
    three_cycle = _fixed_scalar_count((1,) * 2 + (3,) * 6, total)
    double_swap = _fixed_scalar_count((1,) * 4 + (2,) * 8, total)
    mixed = _fixed_scalar_count((1,) * 2 + (3,) * 2 + (6,) * 2, total)
    return (
        identity
        + 4 * transposition
        + 2 * three_cycle
        + 3 * double_swap
        + 2 * mixed
    ) // 12


def test_s3s2_dense_rank_matches_direct_small_orbits() -> None:
    """Small edge assignments collapse to one contiguous product-group rank."""
    orders = tuple(
        _compose(order, suffix)
        for order in _S3_ORDERS
        for suffix in (_IDENTITY, _SWAP)
    )
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
        count = _edge_orbit_count(total)
        assert set(representatives) == set(range(count))
        assert count == _burnside_count(total)


def test_s3s2_dense_rank_roundtrips_through_mass_fourteen() -> None:
    """Boundary and interior product-group ranks roundtrip through mass 14."""
    orders = tuple(
        _compose(order, suffix)
        for order in _S3_ORDERS
        for suffix in (_IDENTITY, _SWAP)
    )
    for total in range(_MAXIMUM_MASS + 1):
        count = _edge_orbit_count(total)
        assert count == _burnside_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            edge_pairs = _unrank(total, rank)
            assert edge_pairs is not None
            assert _rank(edge_pairs) == rank
            for order in orders:
                assert _rank(_permute_edges(edge_pairs, order)) == rank
    assert _edge_orbit_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT


def test_s3s2_bundle_blocks_match_descended_fixed_count() -> None:
    """Constructive bundle blocks reproduce the independent product total."""
    for total in range(_MAXIMUM_MASS + 1):
        assert _edge_orbit_count(total) == _burnside_count(total)
