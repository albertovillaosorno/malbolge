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
#   - Dense rank/unrank for widened transitive-V4-fixed K5 edges modulo N(H)/H.
# - Must-Not:
#   - Claim exact-H filtering or the complete transitive-V4 S5 stratum.
# - Allows:
#   - Inputs: five four-component H-edge-orbit values through mass fourteen.
#   - Outputs: dense ranks modulo the residual normalizer involution.
#   - Side effects: none.
# - Split-When:
#   - Exact-H exclusion is composed into the quotient rank.
# - Merge-When:
#   - Complete widened full-S5 dense ranking owns this quotient prerequisite.
# - Summary:
#   - Rank a diagonal involution on two weighted pairs and one fixed value.
# - Description:
#   - N(H)/H swaps both equal-weight orbit pairs simultaneously.
# - Usage:
#   - Scalable prerequisite for the 1,833,336 exact transitive-V4 classes.
# - Defaults:
#   - Exhaustive quotient domains stop at mass six; arithmetic reaches fourteen.
#

"""Dense widened transitive-V4 normalizer quotient for the full-S5 edge core."""

from __future__ import annotations

from math import comb
from operator import itemgetter
from typing import cast

_COMPONENTS = 4
_EXHAUSTIVE_MASS = 6
_MAXIMUM_MASS = 14
_WIDTH_FOURTEEN_COUNT = 1_842_416
_EXPECTED_COUNTS = (
    1,
    4,
    24,
    92,
    338,
    1_036,
    3_000,
    7_892,
    19_735,
    46_344,
    104_432,
    224_952,
    468_428,
    942_136,
    1_842_416,
)

type _Vector = tuple[int, ...]
type _State = tuple[_Vector, _Vector, _Vector, _Vector, _Vector]


def _composition_count(total: int, parts: int = _COMPONENTS) -> int:
    if total < 0 or parts <= 0:
        return 0
    return comb(total + parts - 1, parts - 1)


def _composition_rank(vector: _Vector, total: int) -> int | None:
    if len(vector) != _COMPONENTS or any(value < 0 for value in vector):
        return None
    if sum(vector) != total:
        return None
    rank = 0
    remaining = total
    for index, value in enumerate(vector[:-1]):
        tail = _COMPONENTS - index - 1
        rank += sum(
            _composition_count(remaining - earlier, tail)
            for earlier in range(value)
        )
        remaining -= value
    return rank


def _composition_unrank(total: int, rank: int) -> _Vector | None:
    if rank < 0 or rank >= _composition_count(total):
        return None
    remaining_rank = rank
    remaining_total = total
    values: list[int] = []
    for index in range(_COMPONENTS - 1):
        tail = _COMPONENTS - index - 1
        for value in range(remaining_total + 1):
            block = _composition_count(remaining_total - value, tail)
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


def _fixed_pair_count(total: int) -> int:
    return _composition_count(total // 2) if total % 2 == 0 else 0


def _fixed_pair_rank(left: _Vector, right: _Vector) -> int | None:
    if left != right:
        return None
    return _composition_rank(left, sum(left))


def _fixed_pair_unrank(total: int, rank: int) -> tuple[_Vector, _Vector] | None:
    if total % 2 != 0:
        return None
    value = _composition_unrank(total // 2, rank)
    return (value, value) if value is not None else None


def _moving_pair_count(total: int) -> int:
    raw = _composition_count(total, 2 * _COMPONENTS)
    return (raw - _fixed_pair_count(total)) // 2


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


def _moving_pair_rank_canonical(left: _Vector, right: _Vector) -> int:
    left_key = _vector_key(left)
    right_key = _vector_key(right)
    total = left_key[0] + right_key[0]
    prefix = sum(
        _composition_count(mass) * _composition_count(total - mass)
        for mass in range(left_key[0])
        if mass < total - mass
    )
    if left_key[0] < right_key[0]:
        return (
            prefix
            + left_key[1] * _composition_count(right_key[0])
            + right_key[1]
        )
    population = _composition_count(left_key[0])
    return prefix + _strict_pair_rank(left_key[1], right_key[1], population)


def _moving_pair_rank(
    left: _Vector,
    right: _Vector,
) -> tuple[int, bool] | None:
    if len(left) != _COMPONENTS or len(right) != _COMPONENTS:
        return None
    if any(value < 0 for value in (*left, *right)) or left == right:
        return None
    flipped = _vector_key(right) < _vector_key(left)
    if flipped:
        left, right = right, left
    return _moving_pair_rank_canonical(left, right), flipped


def _moving_pair_unrank(
    total: int, rank: int
) -> tuple[_Vector, _Vector] | None:
    if rank < 0 or rank >= _moving_pair_count(total):
        return None
    remaining = rank
    for left_mass in range((total + 1) // 2):
        right_mass = total - left_mass
        block = _composition_count(left_mass) * _composition_count(right_mass)
        if remaining >= block:
            remaining -= block
            continue
        left_rank, right_rank = divmod(
            remaining, _composition_count(right_mass)
        )
        left = _composition_unrank(left_mass, left_rank)
        right = _composition_unrank(right_mass, right_rank)
        assert left is not None
        assert right is not None
        return left, right
    half = total // 2
    population = _composition_count(half)
    left_rank, right_rank = _strict_pair_unrank(remaining, population)
    left = _composition_unrank(half, left_rank)
    right = _composition_unrank(half, right_rank)
    assert left is not None
    assert right is not None
    return left, right


def _pair_counts(
    left_total: int, right_total: int
) -> tuple[int, int, int, int]:
    return (
        _fixed_pair_count(left_total),
        _fixed_pair_count(right_total),
        _moving_pair_count(left_total),
        _moving_pair_count(right_total),
    )


def _pair_prefixes(counts: tuple[int, int, int, int]) -> tuple[int, int, int]:
    left_fixed, right_fixed, left_moving, right_moving = counts
    fixed_fixed = left_fixed * right_fixed
    fixed_moving = left_fixed * right_moving
    moving_fixed = left_moving * right_fixed
    return (
        fixed_fixed,
        fixed_fixed + fixed_moving,
        fixed_fixed + fixed_moving + moving_fixed,
    )


def _pair_product_count(left_total: int, right_total: int) -> int:
    counts = _pair_counts(left_total, right_total)
    prefixes = _pair_prefixes(counts)
    return prefixes[2] + 2 * counts[2] * counts[3]


def _pair_product_rank(
    left_pair: tuple[_Vector, _Vector],
    right_pair: tuple[_Vector, _Vector],
) -> int | None:
    left_fixed = _fixed_pair_rank(*left_pair)
    right_fixed = _fixed_pair_rank(*right_pair)
    counts = _pair_counts(
        sum(left_pair[0]) + sum(left_pair[1]),
        sum(right_pair[0]) + sum(right_pair[1]),
    )
    prefixes = _pair_prefixes(counts)
    left_moving = _moving_pair_rank(*left_pair)
    right_moving = _moving_pair_rank(*right_pair)
    result: int | None = None
    if left_fixed is not None and right_fixed is not None:
        result = left_fixed * counts[1] + right_fixed
    elif left_fixed is not None and right_moving is not None:
        result = prefixes[0] + left_fixed * counts[3] + right_moving[0]
    elif left_moving is not None and right_fixed is not None:
        result = prefixes[1] + left_moving[0] * counts[1] + right_fixed
    elif left_moving is not None and right_moving is not None:
        relative = int(left_moving[1] != right_moving[1])
        local = (left_moving[0] * counts[3] + right_moving[0]) * 2
        result = prefixes[2] + local + relative
    return result


def _unrank_fixed_fixed(
    totals: tuple[int, int],
    rank: int,
    counts: tuple[int, int, int, int],
) -> tuple[tuple[_Vector, _Vector], tuple[_Vector, _Vector]]:
    left_rank, right_rank = divmod(rank, counts[1])
    left = _fixed_pair_unrank(totals[0], left_rank)
    right = _fixed_pair_unrank(totals[1], right_rank)
    assert left is not None
    assert right is not None
    return left, right


def _unrank_fixed_moving(
    totals: tuple[int, int],
    rank: int,
    counts: tuple[int, int, int, int],
) -> tuple[tuple[_Vector, _Vector], tuple[_Vector, _Vector]]:
    left_rank, right_rank = divmod(rank, counts[3])
    left = _fixed_pair_unrank(totals[0], left_rank)
    right = _moving_pair_unrank(totals[1], right_rank)
    assert left is not None
    assert right is not None
    return left, right


def _unrank_moving_fixed(
    totals: tuple[int, int],
    rank: int,
    counts: tuple[int, int, int, int],
) -> tuple[tuple[_Vector, _Vector], tuple[_Vector, _Vector]]:
    left_rank, right_rank = divmod(rank, counts[1])
    left = _moving_pair_unrank(totals[0], left_rank)
    right = _fixed_pair_unrank(totals[1], right_rank)
    assert left is not None
    assert right is not None
    return left, right


def _unrank_moving_moving(
    totals: tuple[int, int],
    rank: int,
    counts: tuple[int, int, int, int],
) -> tuple[tuple[_Vector, _Vector], tuple[_Vector, _Vector]]:
    local, relative = divmod(rank, 2)
    left_rank, right_rank = divmod(local, counts[3])
    left = _moving_pair_unrank(totals[0], left_rank)
    right = _moving_pair_unrank(totals[1], right_rank)
    assert left is not None
    assert right is not None
    if relative:
        right = right[1], right[0]
    return left, right


def _pair_product_unrank(
    left_total: int,
    right_total: int,
    rank: int,
) -> tuple[tuple[_Vector, _Vector], tuple[_Vector, _Vector]] | None:
    if rank < 0 or rank >= _pair_product_count(left_total, right_total):
        return None
    counts = _pair_counts(left_total, right_total)
    prefixes = _pair_prefixes(counts)
    result: tuple[tuple[_Vector, _Vector], tuple[_Vector, _Vector]]
    if rank < prefixes[0]:
        result = _unrank_fixed_fixed((left_total, right_total), rank, counts)
    elif rank < prefixes[1]:
        result = _unrank_fixed_moving(
            (left_total, right_total), rank - prefixes[0], counts
        )
    elif rank < prefixes[2]:
        result = _unrank_moving_fixed(
            (left_total, right_total), rank - prefixes[1], counts
        )
    else:
        result = _unrank_moving_moving(
            (left_total, right_total), rank - prefixes[2], counts
        )
    return result


def _mass_blocks(total: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (left_total, right_total, fixed_mass)
        for left_total in range(total + 1)
        for right_total in range((total - left_total) // 2 + 1)
        for fixed_mass in range((total - left_total - 2 * right_total) // 4 + 1)
        if left_total + 2 * right_total + 4 * fixed_mass == total
    )


def _block_count(block: tuple[int, int, int]) -> int:
    left_total, right_total, fixed_mass = block
    return _pair_product_count(left_total, right_total) * _composition_count(
        fixed_mass
    )


def _count(total: int) -> int:
    return sum(_block_count(block) for block in _mass_blocks(total))


def _state_block(state: _State) -> tuple[int, int, int]:
    first, second, third, fourth, fixed = state
    return (
        sum(first) + sum(second),
        sum(third) + sum(fourth),
        sum(fixed),
    )


def _rank(state: _State) -> int | None:
    block = _state_block(state)
    total = block[0] + 2 * block[1] + 4 * block[2]
    pair_rank = _pair_product_rank((state[0], state[1]), (state[2], state[3]))
    fixed_rank = _composition_rank(state[4], block[2])
    if pair_rank is None or fixed_rank is None:
        return None
    prefix = sum(
        _block_count(candidate)
        for candidate in _mass_blocks(total)
        if candidate < block
    )
    return prefix + pair_rank * _composition_count(block[2]) + fixed_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _count(total):
        return None
    remaining = rank
    for block in _mass_blocks(total):
        block_count = _block_count(block)
        if remaining >= block_count:
            remaining -= block_count
            continue
        fixed_count = _composition_count(block[2])
        pair_rank, fixed_rank = divmod(remaining, fixed_count)
        pairs = _pair_product_unrank(block[0], block[1], pair_rank)
        fixed = _composition_unrank(block[2], fixed_rank)
        assert pairs is not None
        assert fixed is not None
        return pairs[0][0], pairs[0][1], pairs[1][0], pairs[1][1], fixed
    raise AssertionError


_swap_items = itemgetter(1, 0, 3, 2, 4)


def _swap(state: _State) -> _State:
    return cast("_State", _swap_items(state))


def _burnside_count(total: int) -> int:
    raw = sum(
        _composition_count(left_total, 2 * _COMPONENTS)
        * _composition_count(right_total, 2 * _COMPONENTS)
        * _composition_count(fixed_mass)
        for left_total, right_total, fixed_mass in _mass_blocks(total)
    )
    fixed = sum(
        _fixed_pair_count(left_total)
        * _fixed_pair_count(right_total)
        * _composition_count(fixed_mass)
        for left_total, right_total, fixed_mass in _mass_blocks(total)
    )
    return (raw + fixed) // 2


def test_transitive_v4_quotient_count_matches_burnside_through_fourteen() -> (
    None
):
    """The diagonal involution count matches independent Burnside counts."""
    observed = tuple(_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed == tuple(
        _burnside_count(total) for total in range(_MAXIMUM_MASS + 1)
    )
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT


def test_transitive_v4_quotient_rank_exhausts_small_domains() -> None:
    """Every quotient class through mass six receives one contiguous rank."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        for rank in range(_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(state) == rank
            assert _rank(_swap(state)) == rank


def test_transitive_v4_quotient_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior quotient ranks roundtrip through mass fourteen."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(state) == rank
            assert _rank(_swap(state)) == rank
