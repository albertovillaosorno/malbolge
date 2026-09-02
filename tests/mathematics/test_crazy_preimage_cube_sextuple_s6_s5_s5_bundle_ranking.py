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
#   - Dense composition of the S6 (5,1)/(5) second-layer full-S5 bundle stratum.
# - Must-Not:
#   - Re-prove the complete widened S5 edge rank or claim another S5 stratum.
# - Allows:
#   - Inputs: canonical top vertices, two fixed scalars, one repeated-five
#     bundle value, and a proved complete residual full-S5 edge rank.
#   - Outputs: exact dense full-S6 rank/unrank for this second-layer stratum.
#   - Side effects: none.
# - Split-When:
#   - The complete residual full-S5 edge-rank contract changes.
# - Merge-When:
#   - Complete dense ranking owns the full S6 (5,1) stratum.
# - Summary:
#   - Prefix the five-equal bundle value before the complete full-S5 edge rank.
# - Description:
#   - One two-component bundle key repeats five times, leaving full S5.
# - Usage:
#   - Completes the final second-layer (5) slice through total mass fourteen.
# - Defaults:
#   - Exhaustive abstract ranks stop at total mass six; arithmetic reaches 14.
#

"""Dense full-S5 bundle composition for the nested S6 (5,1) stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from math import comb

_ARITY = 6
_FIXED_COMPONENTS = 2
_VERTEX_COMPONENTS = 2
_REPEAT_COUNT = 5
_MAXIMUM_MASS = 14
_EXHAUSTIVE_RANK_MASS = 6
_SAMPLE_DIVISOR = 4
_TOP_PARTITION = (5, 1)
_WIDTH_FOURTEEN_COUNT = 28_193_036_967
_WIDTH_FOURTEEN_EDGE_COUNT = 20_103_708_128
_EXPECTED_COUNTS = (
    0,
    2,
    15,
    104,
    744,
    5_494,
    39_840,
    275_326,
    1_778_332,
    10_651_292,
    59_107_031,
    304_780_354,
    1_466_931_408,
    6_623_409_906,
    28_193_036_967,
)
_EXPECTED_BUNDLE_COUNTS = (
    1,
    0,
    0,
    0,
    0,
    2,
    0,
    0,
    0,
    0,
    3,
    0,
    0,
    0,
    0,
)
_EDGE_COUNTS = (
    1,
    4,
    30,
    220,
    1_651,
    11_784,
    78_886,
    486_608,
    2_759_434,
    14_421_284,
    69_829_516,
    315_151_692,
    1_333_556_680,
    5_319_669_572,
    20_103_708_128,
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
type _State = tuple[_Vertices, _Vector, _Bundle, int]
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


def _as_bundle(vector: _Vector) -> _Bundle:
    assert len(vector) == _VERTEX_COMPONENTS
    first, second = vector
    return first, second


def _bundle_count(total: int) -> int:
    if total < 0 or total % _REPEAT_COUNT != 0:
        return 0
    return _composition_count(total // _REPEAT_COUNT, _VERTEX_COMPONENTS)


def _bundle_rank(bundle: _Bundle) -> int:
    rank = _composition_rank(bundle, _VERTEX_COMPONENTS)
    assert rank is not None
    return rank


def _bundle_unrank(total: int, rank: int) -> _Bundle | None:
    if total % _REPEAT_COUNT != 0:
        return None
    vector = _composition_unrank(
        total // _REPEAT_COUNT,
        _VERTEX_COMPONENTS,
        rank,
    )
    return None if vector is None else _as_bundle(vector)


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
    vertices, fixed, bundle, _ = state
    return (
        sum(sum(pair) for pair in vertices),
        sum(fixed),
        _REPEAT_COUNT * sum(bundle),
    )


def _state_ranks(state: _State, masses: _Masses) -> _Ranks | None:
    vertices, fixed, bundle, _ = state
    try:
        vertex_rank = _vertices_of_mass(masses[0]).index(vertices)
    except ValueError:
        vertex_rank = -1
    fixed_rank = _composition_rank(fixed, _FIXED_COMPONENTS)
    bundle_rank = _bundle_rank(bundle)
    result: _Ranks | None = None
    if vertex_rank >= 0 and fixed_rank is not None:
        result = vertex_rank, fixed_rank, bundle_rank
    return result


def _state_data(
    total: int,
    state: _State,
) -> tuple[_Masses, _Ranks] | None:
    masses = _state_masses(state)
    edge_mass = total - sum(masses)
    ranks = _state_ranks(state, masses)
    valid_bundle = 0 <= ranks[2] < _bundle_count(masses[2]) if ranks else False
    valid_edge = edge_mass >= 0 and 0 <= state[3] < _edge_count(edge_mass)
    return (
        (masses, ranks)
        if ranks is not None and valid_bundle and valid_edge
        else None
    )


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


def _unrank_block(
    total: int,
    masses: _Masses,
    rank: int,
) -> _State:
    ranks, edge_rank = _component_ranks(total, masses, rank)
    vertex_rank, fixed_rank, bundle_rank = ranks
    vertices = _vertices_of_mass(masses[0])[vertex_rank]
    fixed = _composition_unrank(masses[1], _FIXED_COMPONENTS, fixed_rank)
    bundle = _bundle_unrank(masses[2], bundle_rank)
    assert fixed is not None
    assert bundle is not None
    return vertices, fixed, bundle, edge_rank


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


def test_s6_s5_s5_bundle_counts_match_nested_factorization() -> None:
    """Repeated-five bundles and full-S5 edges match the missing branch."""
    observed_bundles = tuple(
        _bundle_count(mass) for mass in range(_MAXIMUM_MASS + 1)
    )
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed_bundles == _EXPECTED_BUNDLE_COUNTS
    assert observed == _EXPECTED_COUNTS
    assert _edge_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_EDGE_COUNT
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT


def test_s6_s5_s5_bundle_rank_exhausts_small_abstract_domains() -> None:
    """All-equal bundle composition is one dense interval through mass six."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s5_s5_bundle_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior all-equal bundle ranks reach mass fourteen."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in _sample_ranks(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
