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
#   - Dense composition for the V4 spoke stratum of S6 (5,1)/(4,1).
# - Must-Not:
#   - Re-prove the widened V4 edge rank or claim the full S4 spoke slice.
# - Allows:
#   - Inputs: two distinct repeated four-component spokes plus a proved V4 edge
#     rank at residual mass zero through fourteen.
#   - Outputs: dense local rank/unrank for spoke multiplicity partition (2,2).
#   - Side effects: none.
# - Split-When:
#   - The widened V4 edge-rank contract changes.
# - Merge-When:
#   - Complete dense ranking owns the full S6 (5,1)/(4,1) edge slice.
# - Summary:
#   - Prefix strict repeated-spoke pairs before the proved widened V4 edge rank.
# - Description:
#   - Two distinct four-component spoke keys each occur twice.
# - Usage:
#   - Constructive order-four spoke stratum beneath the S4 factorization.
# - Defaults:
#   - Exhaustive abstract ranks stop at residual mass eight.
#

"""Dense V4 spoke composition inside the S6 (5,1)/(4,1) stratum."""

from __future__ import annotations

from functools import cache
from math import comb

_SPOKE_COMPONENTS = 4
_MAXIMUM_MASS = 14
_EXHAUSTIVE_RANK_MASS = 8
_SAMPLE_DIVISOR = 4
_WIDTH_FOURTEEN_COUNT = 1_350_964_200
_WIDTH_FOURTEEN_EDGE_COUNT = 1_528_935_120
_EXPECTED_COUNTS = (
    0,
    0,
    4,
    48,
    448,
    3_344,
    21_300,
    117_728,
    577_024,
    2_547_744,
    10_278_504,
    38_322_752,
    133_320_320,
    436_182_336,
    1_350_964_200,
)
_EXPECTED_SPOKE_COUNTS = (
    0,
    0,
    4,
    0,
    16,
    0,
    60,
    0,
    160,
    0,
    396,
    0,
    848,
    0,
    1_716,
)

type _Vector = tuple[int, ...]
type _Spoke = tuple[int, int, int, int]
type _SpokePair = tuple[_Spoke, _Spoke]
type _State = tuple[_SpokePair, int]


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


def _as_spoke(vector: _Vector) -> _Spoke:
    assert len(vector) == _SPOKE_COMPONENTS
    first, second, third, fourth = vector
    return first, second, third, fourth


def _spoke_population(mass: int) -> int:
    return _composition_count(mass, _SPOKE_COMPONENTS)


def _spoke_key(spoke: _Spoke) -> tuple[int, int]:
    rank = _composition_rank(spoke, _SPOKE_COMPONENTS)
    assert rank is not None
    return sum(spoke), rank


def _spoke_mass_pairs(total: int) -> tuple[tuple[int, int], ...]:
    if total % 2 != 0:
        return ()
    half = total // 2
    return tuple((left, half - left) for left in range(half // 2 + 1))


def _spoke_block_count(masses: tuple[int, int]) -> int:
    left = _spoke_population(masses[0])
    right = _spoke_population(masses[1])
    if masses[0] == masses[1]:
        return comb(left, 2)
    return left * right


@cache
def _spoke_count(total: int) -> int:
    return sum(
        _spoke_block_count(masses) for masses in _spoke_mass_pairs(total)
    )


def _spoke_rank(state: _SpokePair) -> int | None:
    left, right = sorted(state, key=_spoke_key)
    left_key = _spoke_key(left)
    right_key = _spoke_key(right)
    if left_key == right_key:
        return None
    masses = left_key[0], right_key[0]
    total = 2 * sum(masses)
    prefix = sum(
        _spoke_block_count(candidate)
        for candidate in _spoke_mass_pairs(total)
        if candidate < masses
    )
    if masses[0] < masses[1]:
        local = left_key[1] * _spoke_population(masses[1]) + right_key[1]
    else:
        local = _strict_pair_rank(
            left_key[1],
            right_key[1],
            _spoke_population(masses[0]),
        )
    return prefix + local


def _spoke_unrank(total: int, rank: int) -> _SpokePair | None:
    if rank < 0 or rank >= _spoke_count(total):
        return None
    remaining = rank
    for masses in _spoke_mass_pairs(total):
        block = _spoke_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        if masses[0] < masses[1]:
            left_rank, right_rank = divmod(
                remaining,
                _spoke_population(masses[1]),
            )
        else:
            left_rank, right_rank = _strict_pair_unrank(
                remaining,
                _spoke_population(masses[0]),
            )
        left = _composition_unrank(masses[0], _SPOKE_COMPONENTS, left_rank)
        right = _composition_unrank(masses[1], _SPOKE_COMPONENTS, right_rank)
        assert left is not None
        assert right is not None
        return _as_spoke(left), _as_spoke(right)
    raise AssertionError


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
    identity = _composition_count(total, 24)
    involution = _fixed_count((1,) * 8 + (2,) * 8, total)
    return (identity + 3 * involution) // 4


@cache
def _class_count(total: int) -> int:
    return sum(
        _spoke_count(spoke_mass) * _edge_count(total - spoke_mass)
        for spoke_mass in range(total + 1)
    )


def _rank(total: int, state: _State) -> int | None:
    spokes, edge_rank = state
    spoke_mass = 2 * sum(sum(spoke) for spoke in spokes)
    edge_mass = total - spoke_mass
    spoke_rank = _spoke_rank(spokes)
    if spoke_rank is None or edge_mass < 0:
        return None
    edge_count = _edge_count(edge_mass)
    if not 0 <= edge_rank < edge_count:
        return None
    prefix = sum(
        _spoke_count(mass) * _edge_count(total - mass)
        for mass in range(spoke_mass)
    )
    return prefix + spoke_rank * edge_count + edge_rank


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
        spokes = _spoke_unrank(spoke_mass, spoke_rank)
        assert spokes is not None
        return spokes, edge_rank
    raise AssertionError


def _sample_ranks(count: int) -> tuple[int, ...]:
    if count == 0:
        return ()
    return tuple(
        sorted({
            0,
            count // _SAMPLE_DIVISOR,
            count // 2,
            (3 * count) // _SAMPLE_DIVISOR,
            count - 1,
        })
    )


def test_s6_s5_s4_v4_spoke_pair_counts_match_nested_factorization() -> None:
    """Strict repeated-spoke pairs reproduce the independent histogram."""
    observed = tuple(_spoke_count(mass) for mass in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_SPOKE_COUNTS
    assert _edge_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_EDGE_COUNT


def test_s6_s5_s4_v4_spoke_rank_exhausts_small_abstract_domains() -> None:
    """Canonical spoke pairs plus local V4 ranks form one dense index."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        count = _class_count(total)
        for rank in range(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s5_s4_v4_spoke_rank_roundtrips_through_fourteen() -> None:
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
