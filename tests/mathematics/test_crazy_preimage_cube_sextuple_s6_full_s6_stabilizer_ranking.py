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
#   - Dense rank/unrank for the exact full-S6 automorphism stratum inside the
#     top-level all-equal `(6)` vertex partition through total mass fourteen.
# - Must-Not:
#   - Claim rank/unrank for any proper residual stabilizer or all `(6)` classes.
# - Allows:
#   - Inputs: one repeated-six vertex pair and the two S6-fixed residual counts.
#   - Outputs: exact dense full-S6-stabilizer rank/unrank.
#   - Side effects: none.
# - Split-When:
#   - Another exact full-S6 stabilizer mass range includes nontrivial label
#     orbits of size fifteen or twenty.
# - Merge-When:
#   - Complete dense full-S6 residual ranking owns every stabilizer stratum.
# - Summary:
#   - Rank the repeated vertex pair and the two fixed residual scalars.
# - Description:
#   - Nontrivial full-S6 residual label orbits have size at least fifteen, so
#     they cannot carry positive mass inside the admitted total-mass range.
# - Usage:
#   - First constructive symmetric stratum for the final top-level `(6)` branch.
# - Defaults:
#   - Exhaustive rank/unrank reaches every total mass from zero through
#     fourteen.
#

"""Dense exact full-S6 stabilizer rank for the top-level `(6)` stratum."""

from __future__ import annotations

from itertools import permutations
from typing import cast

_ARITY = 6
_REPEAT_COUNT = 6
_MAXIMUM_MASS = 14
_EXPECTED_ORBIT_SIZES = (1, 1, 15, 15, 20)
_EXPECTED_COUNTS = (1, 2, 3, 4, 5, 6, 9, 12, 15, 18, 21, 24, 30, 36, 42)
_WIDTH_FOURTEEN_COUNT = _EXPECTED_COUNTS[-1]


type _Pair = tuple[int, int]
type _Permutation = tuple[int, int, int, int, int, int]
type _ResidualVector = tuple[int, ...]
type _State = tuple[_Pair, _Pair]

_S6 = cast(
    "tuple[_Permutation, ...]",
    tuple(permutations(range(_ARITY))),
)
_RESIDUAL_LABELS = tuple(
    symbol
    for symbol in range(1 << _ARITY)
    if symbol.bit_count() not in {1, _ARITY - 1}
)
_RESIDUAL_INDEX = {label: index for index, label in enumerate(_RESIDUAL_LABELS)}
_FIXED_LABELS = (0, (1 << _ARITY) - 1)


def _permuted_symbol(symbol: int, order: _Permutation) -> int:
    bits = tuple(
        (symbol >> (_ARITY - endpoint - 1)) & 1 for endpoint in range(_ARITY)
    )
    result = 0
    for source in order:
        result = (result << 1) | bits[source]
    return result


def _full_s6_orbits() -> tuple[tuple[int, ...], ...]:
    unseen = set(_RESIDUAL_LABELS)
    result: list[tuple[int, ...]] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(sorted({_permuted_symbol(seed, order) for order in _S6}))
        unseen -= set(orbit)
        result.append(orbit)
    return tuple(sorted(result, key=lambda orbit: (len(orbit), orbit)))


def _pair_rank(pair: _Pair) -> int | None:
    first, second = pair
    if first < 0 or second < 0:
        return None
    return first


def _pair_unrank(total: int, rank: int) -> _Pair | None:
    if total < 0 or rank < 0 or rank > total:
        return None
    return rank, total - rank


def _block_count(total: int, vertex_pair_mass: int) -> int:
    residual_mass = total - _REPEAT_COUNT * vertex_pair_mass
    if residual_mass < 0:
        return 0
    return (vertex_pair_mass + 1) * (residual_mass + 1)


def _class_count(total: int) -> int:
    if total < 0 or total > _MAXIMUM_MASS:
        return 0
    return sum(
        _block_count(total, vertex_pair_mass)
        for vertex_pair_mass in range(total // _REPEAT_COUNT + 1)
    )


def _rank(total: int, state: _State) -> int | None:
    vertex_pair, residual_pair = state
    vertex_rank = _pair_rank(vertex_pair)
    residual_rank = _pair_rank(residual_pair)
    if vertex_rank is None or residual_rank is None:
        return None
    vertex_pair_mass = sum(vertex_pair)
    residual_mass = sum(residual_pair)
    if _REPEAT_COUNT * vertex_pair_mass + residual_mass != total:
        return None
    prefix = sum(_block_count(total, mass) for mass in range(vertex_pair_mass))
    return prefix + vertex_rank * (residual_mass + 1) + residual_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for vertex_pair_mass in range(total // _REPEAT_COUNT + 1):
        block = _block_count(total, vertex_pair_mass)
        if remaining >= block:
            remaining -= block
            continue
        residual_mass = total - _REPEAT_COUNT * vertex_pair_mass
        vertex_rank, residual_rank = divmod(remaining, residual_mass + 1)
        vertex_pair = _pair_unrank(vertex_pair_mass, vertex_rank)
        residual_pair = _pair_unrank(residual_mass, residual_rank)
        assert vertex_pair is not None
        assert residual_pair is not None
        return vertex_pair, residual_pair
    raise AssertionError


def _residual_vector(pair: _Pair) -> _ResidualVector:
    result = [0] * len(_RESIDUAL_LABELS)
    for label, value in zip(_FIXED_LABELS, pair, strict=True):
        result[_RESIDUAL_INDEX[label]] = value
    return tuple(result)


def _permute_residual(
    vector: _ResidualVector,
    order: _Permutation,
) -> _ResidualVector:
    result = [0] * len(_RESIDUAL_LABELS)
    for source, label in enumerate(_RESIDUAL_LABELS):
        image = _permuted_symbol(label, order)
        result[_RESIDUAL_INDEX[image]] = vector[source]
    return tuple(result)


def test_full_s6_stabilizer_has_exact_residual_orbit_geometry() -> None:
    """Full S6 has two singleton residual orbits before sizes 15, 15, and 20."""
    orbits = _full_s6_orbits()
    assert tuple(len(orbit) for orbit in orbits) == _EXPECTED_ORBIT_SIZES
    assert tuple(orbit[0] for orbit in orbits[:2]) == _FIXED_LABELS


def test_full_s6_stabilizer_counts_match_reviewed_sequence() -> None:
    """Only the repeated vertex pair and two fixed scalars contribute by 14."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT


def test_full_s6_stabilizer_rank_exhausts_through_fourteen() -> None:
    """Every admitted full-S6 state receives one contiguous dense rank."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in range(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_full_s6_stabilizer_unranked_states_are_fully_invariant() -> None:
    """Every produced residual state is fixed by all 720 endpoints."""
    for total in range(_MAXIMUM_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            vector = _residual_vector(state[1])
            assert all(
                _permute_residual(vector, order) == vector for order in _S6
            )
