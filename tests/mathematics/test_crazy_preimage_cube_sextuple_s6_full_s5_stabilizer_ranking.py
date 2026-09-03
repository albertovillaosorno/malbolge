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
#   - Dense rank/unrank for the exact point-stabilizer S5 automorphism stratum
#     inside the top-level all-equal `(6)` vertex partition through mass 14.
# - Must-Not:
#   - Claim rank/unrank for another proper S6 residual stabilizer.
# - Allows:
#   - Inputs: one repeated-six vertex pair and exact S5-fixed residual orbit
#     data.
#   - Outputs: exact dense point-stabilizer S5 rank/unrank.
#   - Side effects: none.
# - Split-When:
#   - Another exact stabilizer shares this weighted-orbit filter.
# - Merge-When:
#   - Complete dense full-S6 residual ranking owns every stabilizer stratum.
# - Summary:
#   - Filter the self-normalizing point-stabilizer S5 fixed states exactly.
# - Description:
#   - S5 is maximal in S6, so excluding full-S6-fixed states leaves exact S5.
# - Usage:
#   - Second constructive symmetric stratum for the final top-level `(6)`
#     branch.
# - Defaults:
#   - Exhaustive rank/unrank reaches every total mass zero through fourteen.
#

"""Dense exact point-stabilizer S5 rank for the top-level `(6)` stratum."""

from __future__ import annotations

from functools import cache
from itertools import permutations
from typing import cast

_ARITY = 6
_ACTIVE = tuple(range(5))
_REPEAT_COUNT = 6
_MAXIMUM_MASS = 14
_S5_ORDER = 120
_EXPECTED_ORBIT_SIZES = (1, 1, 5, 5, 10, 10, 10, 10)
_EXPECTED_RESIDUAL_COUNTS = (0, 0, 0, 0, 0, 2, 4, 6, 8, 10, 19, 28, 37, 46, 55)
_EXPECTED_COUNTS = (0, 0, 0, 0, 0, 2, 4, 6, 8, 10, 19, 32, 45, 58, 71)
_WIDTH_FOURTEEN_COUNT = _EXPECTED_COUNTS[-1]


type _Pair = tuple[int, int]
type _Permutation = tuple[int, int, int, int, int, int]
type _OrbitValues = tuple[int, ...]
type _State = tuple[_Pair, _OrbitValues]

_S6 = cast(
    "tuple[_Permutation, ...]",
    tuple(permutations(range(_ARITY))),
)
_S5 = cast(
    "tuple[_Permutation, ...]",
    tuple((*order, 5) for order in permutations(_ACTIVE)),
)
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


def _s5_orbits() -> tuple[tuple[int, ...], ...]:
    unseen = set(_RESIDUAL_LABELS)
    result: list[tuple[int, ...]] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(sorted({_permuted_symbol(seed, order) for order in _S5}))
        unseen -= set(orbit)
        result.append(orbit)
    return tuple(sorted(result, key=lambda orbit: (len(orbit), orbit)))


_ORBITS = _s5_orbits()
_ORBIT_SIZES = tuple(len(orbit) for orbit in _ORBITS)


@cache
def _weighted_vectors_from(index: int, total: int) -> tuple[_OrbitValues, ...]:
    if index == len(_ORBIT_SIZES):
        return ((),) if total == 0 else ()
    weight = _ORBIT_SIZES[index]
    return tuple(
        (value, *suffix)
        for value in range(total // weight + 1)
        for suffix in _weighted_vectors_from(index + 1, total - value * weight)
    )


def _residual_vector(values: _OrbitValues) -> tuple[int, ...]:
    assert len(values) == len(_ORBITS)
    result = [0] * len(_RESIDUAL_LABELS)
    for orbit, value in zip(_ORBITS, values, strict=True):
        for label in orbit:
            result[_RESIDUAL_INDEX[label]] = value
    return tuple(result)


_S6_LABEL_MAPS = tuple(
    tuple(
        _RESIDUAL_INDEX[_permuted_symbol(label, order)]
        for label in _RESIDUAL_LABELS
    )
    for order in _S6
)


def _stabilizer_order(values: _OrbitValues) -> int:
    vector = _residual_vector(values)
    return sum(
        all(
            vector[source] == vector[destination]
            for source, destination in enumerate(mapping)
        )
        for mapping in _S6_LABEL_MAPS
    )


@cache
def _exact_values(total: int) -> tuple[_OrbitValues, ...]:
    return tuple(
        values
        for values in _weighted_vectors_from(0, total)
        if _stabilizer_order(values) == _S5_ORDER
    )


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
        (vertex_mass + 1)
        * len(_exact_values(total - _REPEAT_COUNT * vertex_mass))
        for vertex_mass in range(total // _REPEAT_COUNT + 1)
    )


def _rank(total: int, state: _State) -> int | None:
    vertex_pair, residual = state
    vertex_rank = _pair_rank(vertex_pair)
    result: int | None = None
    if vertex_rank is not None:
        vertex_mass = sum(vertex_pair)
        residual_mass = sum(
            value * weight
            for value, weight in zip(residual, _ORBIT_SIZES, strict=True)
        )
        valid_mass = _REPEAT_COUNT * vertex_mass + residual_mass == total
        if valid_mass:
            try:
                residual_rank = _exact_values(residual_mass).index(residual)
            except ValueError:
                residual_rank = -1
            if residual_rank >= 0:
                prefix = sum(
                    (mass + 1)
                    * len(_exact_values(total - _REPEAT_COUNT * mass))
                    for mass in range(vertex_mass)
                )
                result = (
                    prefix
                    + vertex_rank * len(_exact_values(residual_mass))
                    + residual_rank
                )
    return result


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for vertex_mass in range(total // _REPEAT_COUNT + 1):
        residual_mass = total - _REPEAT_COUNT * vertex_mass
        residual_count = len(_exact_values(residual_mass))
        block = (vertex_mass + 1) * residual_count
        if remaining >= block:
            remaining -= block
            continue
        vertex_rank, residual_rank = divmod(remaining, residual_count)
        vertex_pair = _pair_unrank(vertex_mass, vertex_rank)
        assert vertex_pair is not None
        return vertex_pair, _exact_values(residual_mass)[residual_rank]
    raise AssertionError


def test_point_s5_has_exact_residual_orbit_geometry() -> None:
    """The point stabilizer has residual orbit sizes 1,1,5,5,10,10,10,10."""
    assert len(_S5) == _S5_ORDER
    assert _ORBIT_SIZES == _EXPECTED_ORBIT_SIZES


def test_point_s5_exact_residual_counts_match_spectrum() -> None:
    """Exact point-S5 states match the reviewed spectrum through mass 14."""
    observed = tuple(
        len(_exact_values(total)) for total in range(_MAXIMUM_MASS + 1)
    )
    assert observed == _EXPECTED_RESIDUAL_COUNTS
    assert all(
        _stabilizer_order(values) == _S5_ORDER
        for total in range(_MAXIMUM_MASS + 1)
        for values in _exact_values(total)
    )


def test_point_s5_complete_counts_match_outer_prefix() -> None:
    """Repeated-six vertex pairs lift the exact residual sequence densely."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT


def test_point_s5_rank_exhausts_through_fourteen() -> None:
    """Every exact point-S5 class receives one contiguous roundtripping rank."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in range(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
