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
#   - Dense rank/unrank for the S6 stratum with six distinct vertex pair-values.
# - Must-Not:
#   - Claim ranking for any nontrivial Young stabilizer stratum.
# - Allows:
#   - Inputs: sextuple mass 0 through 14 in the distinct-vertex stratum.
#   - Outputs: dense ranks over sorted vertices and 52 labeled residual scalars.
#   - Side effects: none.
# - Split-When:
#   - Another Young stabilizer receives a constructive rank.
# - Merge-When:
#   - Complete dense S6 ranking owns every vertex multiplicity stratum.
# - Summary:
#   - Distinct vertex pairs kill symmetry; rank the residual composition.
# - Description:
#   - Prefix vertex mass/sequence blocks and lex-rank 52-part compositions.
# - Usage:
#   - First constructive S6 slice after the eleven-stabilizer decomposition.
# - Defaults:
#   - Exhaustive dense rank checking stops at mass ten; roundtrips reach 14.
#

"""Dense S6 ranking for the trivial Young-stabilizer vertex stratum."""

from __future__ import annotations

from functools import cache
from math import comb

_ARITY = 6
_RESIDUAL_PARTS = 52
_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 10
_WIDTH_FOURTEEN_COUNT = 99_892_279
_EXPECTED_COUNTS = {
    8: 1,
    9: 64,
    10: 2_043,
    11: 43_604,
    12: 702_403,
    13: 9_129_708,
    14: 99_892_279,
}

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Residual = tuple[int, ...]
type _State = tuple[_Vertices, _Residual]

_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)


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
        mass = sum(pair)
        if mass > remaining:
            continue
        result.extend(
            (pair, *suffix)
            for suffix in _vertex_sequences_from(
                index + 1,
                slots - 1,
                remaining - mass,
            )
        )
    return tuple(result)


def _as_vertices(values: tuple[_Pair, ...]) -> _Vertices:
    assert len(values) == _ARITY
    first, second, third, fourth, fifth, sixth = values
    return first, second, third, fourth, fifth, sixth


@cache
def _vertices_of_mass(mass: int) -> tuple[_Vertices, ...]:
    return tuple(
        _as_vertices(values)
        for values in _vertex_sequences_from(0, _ARITY, mass)
        if sum(sum(pair) for pair in values) == mass
    )


def _composition_count(total: int, parts: int = _RESIDUAL_PARTS) -> int:
    return comb(total + parts - 1, parts - 1)


def _composition_rank(values: _Residual) -> int | None:
    if len(values) != _RESIDUAL_PARTS or any(value < 0 for value in values):
        return None
    remaining = sum(values)
    rank = 0
    for index, value in enumerate(values[:-1]):
        tail_parts = len(values) - index - 1
        rank += sum(
            _composition_count(remaining - earlier, tail_parts)
            for earlier in range(value)
        )
        remaining -= value
    return rank


def _composition_unrank(total: int, rank: int) -> _Residual | None:
    count = _composition_count(total)
    if rank < 0 or rank >= count:
        return None
    remaining = total
    residual_rank = rank
    result: list[int] = []
    for index in range(_RESIDUAL_PARTS - 1):
        tail_parts = _RESIDUAL_PARTS - index - 1
        for value in range(remaining + 1):
            block = _composition_count(remaining - value, tail_parts)
            if residual_rank >= block:
                residual_rank -= block
                continue
            result.append(value)
            remaining -= value
            break
    result.append(remaining)
    return tuple(result)


def _class_count(total: int) -> int:
    return sum(
        len(_vertices_of_mass(vertex_mass))
        * _composition_count(total - vertex_mass)
        for vertex_mass in range(total + 1)
    )


def _canonical_state_data(
    total: int,
    state: _State,
) -> tuple[int, int, int, int] | None:
    vertices, residual = state
    vertex_mass = sum(sum(pair) for pair in vertices)
    residual_mass = total - vertex_mass
    if vertex_mass > total or sum(residual) != residual_mass:
        return None
    candidates = _vertices_of_mass(vertex_mass)
    try:
        vertex_rank = candidates.index(vertices)
    except ValueError:
        vertex_rank = -1
    residual_rank = _composition_rank(residual)
    if vertex_rank < 0 or residual_rank is None:
        return None
    return vertex_mass, vertex_rank, residual_mass, residual_rank


def _rank(total: int, state: _State) -> int | None:
    data = _canonical_state_data(total, state)
    if data is None:
        return None
    vertex_mass, vertex_rank, residual_mass, residual_rank = data
    prefix = sum(
        len(_vertices_of_mass(mass)) * _composition_count(total - mass)
        for mass in range(vertex_mass)
    )
    return (
        prefix
        + vertex_rank * _composition_count(residual_mass)
        + residual_rank
    )


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for vertex_mass in range(total + 1):
        residual_count = _composition_count(total - vertex_mass)
        block = len(_vertices_of_mass(vertex_mass)) * residual_count
        if remaining >= block:
            remaining -= block
            continue
        vertex_rank, residual_rank = divmod(remaining, residual_count)
        residual = _composition_unrank(total - vertex_mass, residual_rank)
        assert residual is not None
        return _vertices_of_mass(vertex_mass)[vertex_rank], residual
    raise AssertionError


def test_distinct_vertex_s6_rank_exhausts_small_domains() -> None:
    """Every class through mass ten receives one contiguous rank."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_distinct_vertex_s6_rank_roundtrips_through_mass_fourteen() -> None:
    """Boundary and interior ranks roundtrip through the admitted mass bound."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        if count == 0:
            continue
        for rank in {0, count // 2, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT


def test_distinct_vertex_s6_counts_match_reviewed_sequence() -> None:
    """Mass-eight-through-fourteen counts match exactly."""
    observed = {
        mass: _class_count(mass)
        for mass in range(_MAXIMUM_MASS + 1)
        if _class_count(mass) != 0
    }
    assert observed == _EXPECTED_COUNTS
