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
#   - Dense composition for the full-S4 spoke stratum of S6 (5,1)/(4,1).
# - Must-Not:
#   - Re-prove the widened full-S4 edge-core rank.
# - Allows:
#   - Inputs: one repeated four-component spoke and a proved full-S4 edge rank.
#   - Outputs: dense local rank/unrank at residual mass zero through fourteen.
#   - Side effects: none.
# - Split-When:
#   - The widened full-S4 edge-rank contract changes.
# - Merge-When:
#   - Complete dense ranking owns the full S6 (5,1)/(4,1) edge slice.
# - Summary:
#   - Prefix one quadruple-repeated spoke before the widened full-S4 edge rank.
# - Description:
#   - All four spokes are equal, leaving the complete residual S4 action.
# - Usage:
#   - Final local spoke stabilizer beneath the S4 factorization.
# - Defaults:
#   - Exhaustive abstract ranks stop at residual mass eight.
#

"""Dense full-S4 spoke composition inside the S6 (5,1)/(4,1) stratum."""

from __future__ import annotations

from functools import cache
from itertools import permutations
from math import comb

_ACTIVE = (0, 1, 2, 3)
_SPOKE_COMPONENTS = 4
_EDGE_COMPONENTS = 4
_MAXIMUM_MASS = 14
_EXHAUSTIVE_RANK_MASS = 8
_SAMPLE_DIVISOR = 4
_WIDTH_FOURTEEN_COUNT = 271_468_676
_WIDTH_FOURTEEN_EDGE_COUNT = 255_543_816
_EXPECTED_COUNTS = (
    1,
    4,
    30,
    180,
    984,
    4_876,
    22_098,
    91_188,
    346_408,
    1_219_888,
    4_014_332,
    12_429_864,
    36_442_258,
    101_705_432,
    271_468_676,
)
_EXPECTED_SPOKE_COUNTS = (
    1,
    0,
    0,
    0,
    4,
    0,
    0,
    0,
    10,
    0,
    0,
    0,
    20,
    0,
    0,
)
_K4_EDGES = tuple(
    (left, right) for left in _ACTIVE for right in _ACTIVE if left < right
)
_K4_EDGE_INDEX = {edge: index for index, edge in enumerate(_K4_EDGES)}
_S4 = tuple(permutations(_ACTIVE))

type _Vector = tuple[int, ...]
type _Spoke = tuple[int, int, int, int]
type _State = tuple[_Spoke, int]


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


def _as_spoke(vector: _Vector) -> _Spoke:
    assert len(vector) == _SPOKE_COMPONENTS
    first, second, third, fourth = vector
    return first, second, third, fourth


def _spoke_count(total: int) -> int:
    if total % 4 != 0:
        return 0
    return _composition_count(total // 4, _SPOKE_COMPONENTS)


def _spoke_rank(spoke: _Spoke) -> int:
    rank = _composition_rank(spoke, _SPOKE_COMPONENTS)
    assert rank is not None
    return rank


def _spoke_unrank(total: int, rank: int) -> _Spoke | None:
    if total % 4 != 0:
        return None
    vector = _composition_unrank(total // 4, _SPOKE_COMPONENTS, rank)
    return None if vector is None else _as_spoke(vector)


def _edge_cycles(order: tuple[int, ...]) -> tuple[int, ...]:
    permutation: list[int] = []
    for left, right in _K4_EDGES:
        image = tuple(sorted((order[left], order[right])))
        permutation.append(_K4_EDGE_INDEX[image[0], image[1]])
    unseen = set(range(len(_K4_EDGES)))
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


def _fixed_count(cycles: tuple[int, ...], total: int) -> int:
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


@cache
def _edge_count(total: int) -> int:
    fixed_sum = sum(
        _fixed_count(
            tuple(sorted(_edge_cycles(order) * _EDGE_COMPONENTS)),
            total,
        )
        for order in _S4
    )
    return fixed_sum // len(_S4)


@cache
def _class_count(total: int) -> int:
    return sum(
        _spoke_count(spoke_mass) * _edge_count(total - spoke_mass)
        for spoke_mass in range(total + 1)
    )


def _rank(total: int, state: _State) -> int | None:
    spoke, edge_rank = state
    spoke_mass = 4 * sum(spoke)
    edge_mass = total - spoke_mass
    if edge_mass < 0:
        return None
    edge_count = _edge_count(edge_mass)
    if not 0 <= edge_rank < edge_count:
        return None
    prefix = sum(
        _spoke_count(mass) * _edge_count(total - mass)
        for mass in range(spoke_mass)
    )
    return prefix + _spoke_rank(spoke) * edge_count + edge_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for spoke_mass in range(total + 1):
        edge_mass = total - spoke_mass
        edge_count = _edge_count(edge_mass)
        block = _spoke_count(spoke_mass) * edge_count
        if remaining >= block:
            remaining -= block
            continue
        spoke_rank, edge_rank = divmod(remaining, edge_count)
        spoke = _spoke_unrank(spoke_mass, spoke_rank)
        assert spoke is not None
        return spoke, edge_rank
    raise AssertionError


def _sample_ranks(count: int) -> tuple[int, ...]:
    return tuple(
        sorted({
            0,
            count // _SAMPLE_DIVISOR,
            count // 2,
            (3 * count) // _SAMPLE_DIVISOR,
            count - 1,
        })
    )


def test_s6_s5_s4_full_spoke_counts_match_nested_factorization() -> None:
    """Quadruple-spoke counts and full-S4 edge totals match prerequisites."""
    observed = tuple(_spoke_count(mass) for mass in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_SPOKE_COUNTS
    assert _edge_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_EDGE_COUNT


def test_s6_s5_s4_full_spoke_rank_exhausts_small_abstract_domains() -> None:
    """One repeated spoke plus local full-S4 ranks form one dense index."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        count = _class_count(total)
        for rank in range(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s5_s4_full_spoke_rank_roundtrips_through_fourteen() -> None:
    """Counts and representative abstract ranks reach residual mass fourteen."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    for total, count in enumerate(observed):
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in _sample_ranks(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
