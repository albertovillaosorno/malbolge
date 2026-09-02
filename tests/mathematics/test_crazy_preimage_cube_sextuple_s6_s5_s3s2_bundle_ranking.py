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
#   - Dense composition of the S6 (5,1)/(3,2) S3xS2 bundle stratum.
# - Must-Not:
#   - Re-prove the widened V4 edge rank or claim another S5 stratum.
# - Allows:
#   - Inputs: canonical top vertices, two fixed scalars, canonical (3,2)
#     bundle states, and a proved residual S3xS2 edge rank.
#   - Outputs: exact dense full-S6 rank/unrank for this second-layer stratum.
#   - Side effects: none.
# - Split-When:
#   - The residual V4 edge-rank contract changes.
# - Merge-When:
#   - Complete dense ranking owns the full S6 (5,1) stratum.
# - Summary:
#   - Prefix the (3,2) bundle state before the widened V4 edge rank.
# - Description:
#   - One bundle key repeats three times and a distinct key repeats twice.
# - Usage:
#   - Completes the S3xS2 second-layer slice through total mass fourteen.
# - Defaults:
#   - Exhaustive abstract ranks stop at total mass six; arithmetic reaches 14.
#

"""Dense S3xS2 bundle composition for the nested S6 (5,1) stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from math import comb

_ARITY = 6
_FIXED_COMPONENTS = 2
_MAXIMUM_MASS = 14
_EXHAUSTIVE_RANK_MASS = 6
_SAMPLE_DIVISOR = 4
_TOP_PARTITION = (5, 1)
_WIDTH_FOURTEEN_COUNT = 36_950_581_606
_WIDTH_FOURTEEN_EDGE_COUNT = 200_608_118_832
_EXPECTED_COUNTS = (
    0,
    0,
    0,
    4,
    66,
    804,
    8_609,
    82_880,
    715_037,
    5_527_610,
    38_467_687,
    242_819_402,
    1_402_054_650,
    7_466_507_322,
    36_950_581_606,
)
_EXPECTED_BUNDLE_COUNTS = (
    0,
    0,
    2,
    2,
    3,
    2,
    7,
    6,
    11,
    12,
    12,
    18,
    24,
    24,
    33,
)
_EDGE_COUNTS = (
    1,
    12,
    134,
    1_364,
    12_429,
    100_344,
    719_278,
    4_612_344,
    26_731_381,
    141_462_708,
    690_010_120,
    3_127_808_188,
    13_270_752_452,
    53_026_761_140,
    200_608_118_832,
)
_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Vector = tuple[int, ...]
type _Bundle = tuple[int, int]
type _BundleState = tuple[_Bundle, _Bundle]
type _State = tuple[_Vertices, _Vector, _BundleState, int]
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


def _bundle_key(bundle: _Bundle) -> tuple[int, int]:
    return sum(bundle), bundle[0]


def _bundles_of_mass(mass: int) -> tuple[_Bundle, ...]:
    return tuple((first, mass - first) for first in range(mass + 1))


@cache
def _bundle_states(total: int) -> tuple[_BundleState, ...]:
    states = tuple(
        (triple, double)
        for triple_mass in range(total // 3 + 1)
        for double_mass in range(total // 2 + 1)
        if 3 * triple_mass + 2 * double_mass == total
        for triple in _bundles_of_mass(triple_mass)
        for double in _bundles_of_mass(double_mass)
        if triple != double
    )
    return tuple(
        sorted(states, key=lambda state: tuple(map(_bundle_key, state)))
    )


@cache
def _bundle_rank_map(total: int) -> dict[_BundleState, int]:
    return {state: rank for rank, state in enumerate(_bundle_states(total))}


def _bundle_count(total: int) -> int:
    return len(_bundle_states(total))


def _bundle_rank(state: _BundleState) -> int | None:
    triple, double = state
    if triple == double:
        return None
    total = 3 * sum(triple) + 2 * sum(double)
    return _bundle_rank_map(total).get(state)


def _bundle_unrank(total: int, rank: int) -> _BundleState | None:
    states = _bundle_states(total)
    return states[rank] if 0 <= rank < len(states) else None


def _edge_count(total: int) -> int:
    if total < 0 or total > _MAXIMUM_MASS:
        return 0
    return _EDGE_COUNTS[total]


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


@cache
def _mass_blocks(total: int) -> tuple[_Masses, ...]:
    return tuple(
        (vertex_mass, fixed_mass, bundle_mass)
        for vertex_mass in range(total + 1)
        for fixed_mass in range(total - vertex_mass + 1)
        for bundle_mass in range(total - vertex_mass - fixed_mass + 1)
    )


def _block_count(total: int, masses: _Masses) -> int:
    edge_mass = total - sum(masses)
    return (
        len(_vertices_of_mass(masses[0]))
        * _composition_count(masses[1], _FIXED_COMPONENTS)
        * _bundle_count(masses[2])
        * _edge_count(edge_mass)
    )


@cache
def _class_count(total: int) -> int:
    return sum(_block_count(total, masses) for masses in _mass_blocks(total))


def _state_masses(state: _State) -> _Masses:
    vertices, fixed, bundles, _ = state
    return (
        sum(sum(pair) for pair in vertices),
        sum(fixed),
        3 * sum(bundles[0]) + 2 * sum(bundles[1]),
    )


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
    valid_edge = edge_mass >= 0 and 0 <= state[3] < _edge_count(edge_mass)
    return (masses, ranks) if ranks is not None and valid_edge else None


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


def test_s6_s5_s3s2_bundle_counts_match_nested_factorization() -> None:
    """Bundle histogram and residual S3xS2 edge counts match reviewed proofs."""
    observed_bundles = tuple(
        _bundle_count(mass) for mass in range(_MAXIMUM_MASS + 1)
    )
    assert observed_bundles == _EXPECTED_BUNDLE_COUNTS
    assert _edge_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_EDGE_COUNT


def test_s6_s5_s3s2_bundle_rank_exhausts_small_abstract_domains() -> None:
    """The nested S3xS2 rank is contiguous through total mass six."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        count = _class_count(total)
        for rank in range(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s5_s3s2_bundle_rank_roundtrips_through_fourteen() -> None:
    """Counts and representative ranks reach the reviewed mass-14 boundary."""
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
