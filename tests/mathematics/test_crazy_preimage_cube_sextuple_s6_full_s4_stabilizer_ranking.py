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
#   - Dense exact-S4 automorphism rank/unrank for the four-vertex extension
#     inside the top-level all-equal `(6)` S6 stratum through total mass 14.
# - Must-Not:
#   - Claim dense exact-S3 or exact-transposition rank/unrank.
# - Allows:
#   - Inputs: one repeated-six vertex pair and S4-fixed residual orbit values.
#   - Outputs: dense exact-S4 residual and complete-stratum rank/unrank.
#   - Side effects: none.
# - Split-When:
#   - The point-stabilizer S5 exclusion mapping becomes separately reusable.
# - Merge-When:
#   - Exact-S3 ranking directly owns this terminal exception rank.
# - Summary:
#   - Delete mapped point-S5 ranks from the free external-S2 S4 quotient.
# - Description:
#   - At mass 14 only 55 of 2,066 free ranks are point-S5 extensions.
# - Usage:
#   - Terminal constructive exception primitive for exact transposition ranking.
# - Defaults:
#   - Exhaustive residual and complete ranks reach every mass through fourteen.
#

"""Dense exact-S4 rank inside the full-S6 transposition exception hierarchy."""

from __future__ import annotations

from bisect import bisect_left
from functools import cache
from itertools import permutations
from typing import cast

_ARITY = 6
_REPEAT_COUNT = 6
_MAXIMUM_MASS = 14
_S4_ORDER = 24
_S5_ORDER = 120
_EXPECTED_FREE_COUNTS = (
    0,
    0,
    0,
    0,
    2,
    8,
    21,
    44,
    88,
    164,
    293,
    496,
    821,
    1_316,
    2_066,
)
_EXPECTED_RESIDUAL_COUNTS = (
    0,
    0,
    0,
    0,
    2,
    6,
    17,
    38,
    80,
    154,
    274,
    468,
    784,
    1_270,
    2_011,
)
_EXPECTED_S5_EXCLUSIONS = (
    0,
    0,
    0,
    0,
    0,
    2,
    4,
    6,
    8,
    10,
    19,
    28,
    37,
    46,
    55,
)
_EXPECTED_COUNTS = (
    0,
    0,
    0,
    0,
    2,
    6,
    17,
    38,
    80,
    154,
    278,
    480,
    818,
    1_346,
    2_171,
)
_WIDTH_FOURTEEN_COUNT = _EXPECTED_COUNTS[-1]

type _Pair = tuple[int, int]
type _Permutation = tuple[int, int, int, int, int, int]
type _Orbit = tuple[int, ...]
type _OrbitValues = tuple[int, ...]
type _State = tuple[_Pair, _OrbitValues]

_S4 = cast(
    "tuple[_Permutation, ...]",
    tuple((*order, 4, 5) for order in permutations(range(4))),
)
_S5 = cast(
    "tuple[_Permutation, ...]",
    tuple((*order, 5) for order in permutations(range(5))),
)
_S6 = cast(
    "tuple[_Permutation, ...]",
    tuple(permutations(range(_ARITY))),
)
_EXTERNAL_SWAP: _Permutation = (0, 1, 2, 3, 5, 4)
_RESIDUAL_LABELS = tuple(
    symbol
    for symbol in range(1 << _ARITY)
    if symbol.bit_count() not in {1, _ARITY - 1}
)
_RESIDUAL_INDEX = {label: index for index, label in enumerate(_RESIDUAL_LABELS)}


def _permuted_symbol(symbol: int, order: _Permutation) -> int:
    bits = tuple(
        (symbol >> (_ARITY - endpoint - 1)) & 1 for endpoint in range(_ARITY)
    )
    result = 0
    for source in order:
        result = (result << 1) | bits[source]
    return result


def _orbits(group: tuple[_Permutation, ...]) -> tuple[_Orbit, ...]:
    unseen = set(_RESIDUAL_LABELS)
    result: list[_Orbit] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(
            sorted({_permuted_symbol(seed, order) for order in group})
        )
        unseen -= set(orbit)
        result.append(orbit)
    return tuple(sorted(result, key=lambda orbit: (len(orbit), orbit)))


_S4_ORBITS = _orbits(_S4)
_S4_WEIGHTS = tuple(len(orbit) for orbit in _S4_ORBITS)
_S4_INDEX = {orbit: index for index, orbit in enumerate(_S4_ORBITS)}
_S5_ORBITS = _orbits(_S5)
_S5_WEIGHTS = tuple(len(orbit) for orbit in _S5_ORBITS)
_SWAP_MAP = tuple(
    _S4_INDEX[
        tuple(
            sorted(_permuted_symbol(symbol, _EXTERNAL_SWAP) for symbol in orbit)
        )
    ]
    for orbit in _S4_ORBITS
)
_S6_LABEL_MAPS = tuple(
    tuple(
        _RESIDUAL_INDEX[_permuted_symbol(label, order)]
        for label in _RESIDUAL_LABELS
    )
    for order in _S6
)


@cache
def _weighted_values_from(
    weights: tuple[int, ...], index: int, total: int
) -> tuple[_OrbitValues, ...]:
    if index == len(weights):
        return ((),) if total == 0 else ()
    weight = weights[index]
    return tuple(
        (value, *suffix)
        for value in range(total // weight + 1)
        for suffix in _weighted_values_from(
            weights, index + 1, total - value * weight
        )
    )


def _swap(values: _OrbitValues) -> _OrbitValues:
    result = [0] * len(values)
    for source, destination in enumerate(_SWAP_MAP):
        result[destination] = values[source]
    return tuple(result)


@cache
def _free_values(total: int) -> tuple[_OrbitValues, ...]:
    return tuple(
        values
        for values in _weighted_values_from(_S4_WEIGHTS, 0, total)
        if values < _swap(values)
    )


def _residual_vector(
    values: _OrbitValues, orbits: tuple[_Orbit, ...]
) -> tuple[int, ...]:
    assert len(values) == len(orbits)
    result = [0] * len(_RESIDUAL_LABELS)
    for orbit, value in zip(orbits, values, strict=True):
        for label in orbit:
            result[_RESIDUAL_INDEX[label]] = value
    return tuple(result)


def _stabilizer_order(values: _OrbitValues, orbits: tuple[_Orbit, ...]) -> int:
    vector = _residual_vector(values, orbits)
    return sum(
        all(
            vector[source] == vector[destination]
            for source, destination in enumerate(mapping)
        )
        for mapping in _S6_LABEL_MAPS
    )


@cache
def _exact_s5_values(total: int) -> tuple[_OrbitValues, ...]:
    return tuple(
        values
        for values in _weighted_values_from(_S5_WEIGHTS, 0, total)
        if _stabilizer_order(values, _S5_ORBITS) == _S5_ORDER
    )


def _s5_to_s4(values: _OrbitValues) -> _OrbitValues:
    by_label = {
        label: value
        for orbit, value in zip(_S5_ORBITS, values, strict=True)
        for label in orbit
    }
    return tuple(by_label[orbit[0]] for orbit in _S4_ORBITS)


@cache
def _excluded_free_ranks(total: int) -> tuple[int, ...]:
    free = _free_values(total)
    ranks: set[int] = set()
    for values in _exact_s5_values(total):
        mapped = _s5_to_s4(values)
        representative = min(mapped, _swap(mapped))
        assert representative != _swap(representative)
        ranks.add(free.index(representative))
    return tuple(sorted(ranks))


@cache
def _exact_free_ranks(total: int) -> tuple[int, ...]:
    excluded = set(_excluded_free_ranks(total))
    return tuple(
        rank for rank in range(len(_free_values(total))) if rank not in excluded
    )


def _residual_count(total: int) -> int:
    if total < 0 or total > _MAXIMUM_MASS:
        return 0
    return len(_exact_free_ranks(total))


def _residual_rank(values: _OrbitValues) -> int | None:
    total = sum(
        value * weight
        for value, weight in zip(values, _S4_WEIGHTS, strict=True)
    )
    result: int | None = None
    if total <= _MAXIMUM_MASS:
        try:
            free_rank = _free_values(total).index(values)
        except ValueError:
            free_rank = -1
        if free_rank >= 0:
            excluded = _excluded_free_ranks(total)
            if free_rank not in excluded:
                result = free_rank - bisect_left(excluded, free_rank)
    return result


def _residual_unrank(total: int, rank: int) -> _OrbitValues | None:
    if rank < 0 or rank >= _residual_count(total):
        return None
    free_rank = _exact_free_ranks(total)[rank]
    return _free_values(total)[free_rank]


def _pair_rank(pair: _Pair) -> int | None:
    first, second = pair
    return None if first < 0 or second < 0 else first


def _pair_unrank(total: int, rank: int) -> _Pair | None:
    if total < 0 or rank < 0 or rank > total:
        return None
    return rank, total - rank


def _class_count(total: int) -> int:
    if total < 0 or total > _MAXIMUM_MASS:
        return 0
    return sum(
        (vertex_mass + 1) * _residual_count(total - _REPEAT_COUNT * vertex_mass)
        for vertex_mass in range(total // _REPEAT_COUNT + 1)
    )


def _rank(total: int, state: _State) -> int | None:
    vertex_pair, residual = state
    vertex_rank = _pair_rank(vertex_pair)
    residual_rank = _residual_rank(residual)
    if vertex_rank is None or residual_rank is None:
        return None
    vertex_mass = sum(vertex_pair)
    residual_mass = sum(
        value * weight
        for value, weight in zip(residual, _S4_WEIGHTS, strict=True)
    )
    if _REPEAT_COUNT * vertex_mass + residual_mass != total:
        return None
    prefix = sum(
        (mass + 1) * _residual_count(total - _REPEAT_COUNT * mass)
        for mass in range(vertex_mass)
    )
    return prefix + vertex_rank * _residual_count(residual_mass) + residual_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for vertex_mass in range(total // _REPEAT_COUNT + 1):
        residual_mass = total - _REPEAT_COUNT * vertex_mass
        residual_count = _residual_count(residual_mass)
        block = (vertex_mass + 1) * residual_count
        if remaining >= block:
            remaining -= block
            continue
        vertex_rank, residual_rank = divmod(remaining, residual_count)
        vertex_pair = _pair_unrank(vertex_mass, vertex_rank)
        residual = _residual_unrank(residual_mass, residual_rank)
        assert vertex_pair is not None
        assert residual is not None
        return vertex_pair, residual
    raise AssertionError


def test_exact_s4_exclusion_map_matches_point_s5_counts() -> None:
    """Mapped point-S5 states occupy distinct free-S2 ranks through mass 14."""
    free = tuple(len(_free_values(total)) for total in range(_MAXIMUM_MASS + 1))
    excluded = tuple(
        len(_excluded_free_ranks(total)) for total in range(_MAXIMUM_MASS + 1)
    )
    assert free == _EXPECTED_FREE_COUNTS
    assert excluded == _EXPECTED_S5_EXCLUSIONS
    assert tuple(a - b for a, b in zip(free, excluded, strict=True)) == (
        _EXPECTED_RESIDUAL_COUNTS
    )


def test_exact_s4_residual_states_have_stabilizer_order_24() -> None:
    """Every retained residual representative has exact S4 stabilizer."""
    for total in range(_MAXIMUM_MASS + 1):
        for rank in range(_residual_count(total)):
            values = _residual_unrank(total, rank)
            assert values is not None
            assert _stabilizer_order(values, _S4_ORBITS) == _S4_ORDER


def test_exact_s4_residual_rank_exhausts_through_fourteen() -> None:
    """Every exact-S4 residual interval roundtrips densely through mass 14."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _residual_count(total)
        assert _residual_unrank(total, -1) is None
        assert _residual_unrank(total, count) is None
        for rank in range(count):
            values = _residual_unrank(total, rank)
            assert values is not None
            assert _residual_rank(values) == rank


def test_exact_s4_complete_counts_match_outer_prefix() -> None:
    """Repeated-six vertex pairs lift exact S4 to 2,171 mass-14 classes."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT


def test_exact_s4_complete_rank_exhausts_through_fourteen() -> None:
    """Complete exact-S4 rank is contiguous through total mass fourteen."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in range(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
