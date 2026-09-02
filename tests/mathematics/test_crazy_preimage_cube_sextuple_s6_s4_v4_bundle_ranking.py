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
#   - Dense composition of the nested S6 (4,1,1)/(2,2) V4 bundle stratum.
# - Must-Not:
#   - Re-prove the widened V4 edge rank or claim the full-S4 bundle stratum.
# - Allows:
#   - Inputs: canonical top vertices, fixed scalars, repeated bundle pairs,
#     and a proved local V4 edge rank.
#   - Outputs: exact dense full-S6 rank/unrank for this second-layer stratum.
#   - Side effects: none.
# - Split-When:
#   - The widened V4 edge-rank contract changes.
# - Merge-When:
#   - Complete dense ranking owns the full (4,1,1) S6 stratum.
# - Summary:
#   - Prefix strict repeated-bundle pairs and the proved widened V4 edge rank.
# - Description:
#   - Two distinct six-component bundle keys each occur twice; the remaining
#     edge coordinate is the independently proved dense V4 local rank.
# - Usage:
#   - Completes the second-layer (2,2) slice through total mass fourteen.
# - Defaults:
#   - Exhaustive abstract ranks stop at total mass eight; arithmetic reaches 14.
#

"""Dense V4 bundle composition for the nested S6 (4,1,1) stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from math import comb

_ARITY = 6
_FIXED_COMPONENTS = 4
_VERTEX_COMPONENTS = 6
_MAXIMUM_MASS = 14
_EXHAUSTIVE_RANK_MASS = 8
_TOP_PARTITION = (4, 1, 1)
_WIDTH_FOURTEEN_COUNT = 2_954_772_356
_WIDTH_FOURTEEN_EDGE_COUNT = 1_528_935_120
_EXPECTED_COUNTS = (
    0,
    0,
    0,
    0,
    6,
    132,
    1_674,
    16_128,
    128_774,
    888_452,
    5_423_910,
    29_795_952,
    149_220_534,
    688_626_036,
    2_954_772_356,
)
_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Vector = tuple[int, ...]
type _Bundle = tuple[int, int, int, int, int, int]
type _BundlePair = tuple[_Bundle, _Bundle]
type _State = tuple[_Vertices, _Vector, _BundlePair, int]
type _Masses = tuple[int, int, int]
type _Ranks = tuple[int, int, int]


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


def _as_bundle(vector: _Vector) -> _Bundle:
    assert len(vector) == _VERTEX_COMPONENTS
    first, second, third, fourth, fifth, sixth = vector
    return first, second, third, fourth, fifth, sixth


def _bundle_population(mass: int) -> int:
    return _composition_count(mass, _VERTEX_COMPONENTS)


def _bundle_key(bundle: _Bundle) -> tuple[int, int]:
    rank = _composition_rank(bundle, _VERTEX_COMPONENTS)
    assert rank is not None
    return sum(bundle), rank


def _bundle_mass_pairs(total: int) -> tuple[tuple[int, int], ...]:
    if total % 2 != 0:
        return ()
    half = total // 2
    return tuple((left, half - left) for left in range(half // 2 + 1))


def _bundle_block_count(masses: tuple[int, int]) -> int:
    left = _bundle_population(masses[0])
    right = _bundle_population(masses[1])
    if masses[0] == masses[1]:
        return comb(left, 2)
    return left * right


@cache
def _bundle_count(total: int) -> int:
    return sum(
        _bundle_block_count(masses) for masses in _bundle_mass_pairs(total)
    )


def _bundle_rank(state: _BundlePair) -> int | None:
    left, right = sorted(state, key=_bundle_key)
    left_key = _bundle_key(left)
    right_key = _bundle_key(right)
    if left_key == right_key:
        return None
    masses = left_key[0], right_key[0]
    total = 2 * sum(masses)
    prefix = sum(
        _bundle_block_count(candidate)
        for candidate in _bundle_mass_pairs(total)
        if candidate < masses
    )
    if masses[0] < masses[1]:
        local = left_key[1] * _bundle_population(masses[1]) + right_key[1]
    else:
        local = _strict_pair_rank(
            left_key[1],
            right_key[1],
            _bundle_population(masses[0]),
        )
    return prefix + local


def _bundle_unrank(total: int, rank: int) -> _BundlePair | None:
    if rank < 0 or rank >= _bundle_count(total):
        return None
    remaining = rank
    for masses in _bundle_mass_pairs(total):
        block = _bundle_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        if masses[0] < masses[1]:
            left_rank, right_rank = divmod(
                remaining,
                _bundle_population(masses[1]),
            )
        else:
            left_rank, right_rank = _strict_pair_unrank(
                remaining,
                _bundle_population(masses[0]),
            )
        left = _composition_unrank(masses[0], _VERTEX_COMPONENTS, left_rank)
        right = _composition_unrank(masses[1], _VERTEX_COMPONENTS, right_rank)
        assert left is not None
        assert right is not None
        return _as_bundle(left), _as_bundle(right)
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


def _partition(values: tuple[_Pair, ...]) -> tuple[int, ...]:
    return tuple(sorted(Counter(values).values(), reverse=True))


@cache
def _vertices_of_mass(mass: int) -> tuple[_Vertices, ...]:
    return tuple(
        _as_vertices(values)
        for values in _vertex_sequences_from(0, _ARITY, mass)
        if sum(sum(pair) for pair in values) == mass
        and _partition(values) == _TOP_PARTITION
    )


def _state_masses(state: _State) -> _Masses:
    vertices, fixed, bundles, _ = state
    return (
        sum(sum(pair) for pair in vertices),
        sum(fixed),
        2 * sum(sum(bundle) for bundle in bundles),
    )


@cache
def _mass_blocks(total: int) -> tuple[_Masses, ...]:
    return tuple(
        (vertex_mass, fixed_mass, bundle_mass)
        for vertex_mass in range(total + 1)
        for fixed_mass in range(total - vertex_mass + 1)
        for bundle_mass in range(total - vertex_mass - fixed_mass + 1)
    )


def _block_count(total: int, masses: _Masses) -> int:
    vertex_mass, fixed_mass, bundle_mass = masses
    edge_mass = total - sum(masses)
    if edge_mass < 0:
        return 0
    return (
        len(_vertices_of_mass(vertex_mass))
        * _composition_count(fixed_mass, _FIXED_COMPONENTS)
        * _bundle_count(bundle_mass)
        * _edge_count(edge_mass)
    )


@cache
def _class_count(total: int) -> int:
    return sum(_block_count(total, masses) for masses in _mass_blocks(total))


def _state_ranks(state: _State, masses: _Masses) -> _Ranks | None:
    vertices, fixed, bundles, _ = state
    try:
        vertex_rank = _vertices_of_mass(masses[0]).index(vertices)
    except ValueError:
        vertex_rank = -1
    fixed_rank = _composition_rank(fixed, _FIXED_COMPONENTS)
    bundle_rank = _bundle_rank(bundles)
    result: _Ranks | None = None
    if vertex_rank >= 0 and fixed_rank is not None and bundle_rank is not None:
        result = vertex_rank, fixed_rank, bundle_rank
    return result


def _state_data(
    total: int,
    state: _State,
) -> tuple[_Masses, _Ranks] | None:
    masses = _state_masses(state)
    edge_mass = total - sum(masses)
    ranks = _state_ranks(state, masses)
    result: tuple[_Masses, _Ranks] | None = None
    valid_edge = edge_mass >= 0 and 0 <= state[3] < _edge_count(edge_mass)
    if ranks is not None and valid_edge:
        result = masses, ranks
    return result


def _prefix(total: int, masses: _Masses) -> int:
    return sum(
        _block_count(total, candidate)
        for candidate in _mass_blocks(total)
        if candidate < masses
    )


def _local_rank(
    total: int,
    masses: _Masses,
    ranks: _Ranks,
    *,
    edge_rank: int,
) -> int:
    vertex_rank, fixed_rank, bundle_rank = ranks
    fixed_count = _composition_count(masses[1], _FIXED_COMPONENTS)
    bundle_count = _bundle_count(masses[2])
    edge_count = _edge_count(total - sum(masses))
    head = vertex_rank * fixed_count + fixed_rank
    head = head * bundle_count + bundle_rank
    return head * edge_count + edge_rank


def _rank(total: int, state: _State) -> int | None:
    data = _state_data(total, state)
    if data is None:
        return None
    masses, ranks = data
    return _prefix(total, masses) + _local_rank(
        total,
        masses,
        ranks,
        edge_rank=state[3],
    )


def _component_ranks(
    total: int,
    masses: _Masses,
    rank: int,
) -> tuple[_Ranks, int]:
    fixed_count = _composition_count(masses[1], _FIXED_COMPONENTS)
    bundle_count = _bundle_count(masses[2])
    edge_count = _edge_count(total - sum(masses))
    head, edge_rank = divmod(rank, edge_count)
    head, bundle_rank = divmod(head, bundle_count)
    vertex_rank, fixed_rank = divmod(head, fixed_count)
    return (vertex_rank, fixed_rank, bundle_rank), edge_rank


def _unrank_block(total: int, masses: _Masses, rank: int) -> _State:
    ranks, edge_rank = _component_ranks(total, masses, rank)
    fixed = _composition_unrank(masses[1], _FIXED_COMPONENTS, ranks[1])
    bundles = _bundle_unrank(masses[2], ranks[2])
    assert fixed is not None
    assert bundles is not None
    vertices = _vertices_of_mass(masses[0])[ranks[0]]
    return vertices, fixed, bundles, edge_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for masses in _mass_blocks(total):
        block = _block_count(total, masses)
        if remaining >= block:
            remaining -= block
            continue
        return _unrank_block(total, masses, remaining)
    raise AssertionError


def test_s6_s4_v4_bundle_pair_counts_match_nested_factorization() -> None:
    """Strict bundle-pair counts reproduce the reviewed histogram."""
    expected = (
        0, 0, 6, 0, 36, 0, 182, 0,
        672, 0, 2_184, 0, 6_160, 0, 15_912,
    )
    observed = tuple(
        _bundle_count(mass) for mass in range(_MAXIMUM_MASS + 1)
    )
    assert observed == expected
    assert _edge_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_EDGE_COUNT


def test_s6_s4_v4_bundle_rank_exhausts_small_abstract_domains() -> None:
    """Canonical bundle pairs plus local V4 ranks form one dense full index."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        count = _class_count(total)
        for rank in range(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s4_v4_bundle_rank_roundtrips_through_fourteen() -> None:
    """Counts and representative abstract ranks reach the mass-14 boundary."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    for total, count in enumerate(observed):
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        if count == 0:
            continue
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
