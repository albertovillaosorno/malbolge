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
#   - Dense rank/unrank for the exact single-transposition S5 edge stratum.
# - Must-Not:
#   - Claim ranking for another exact stabilizer or the complete S5 quotient.
# - Allows:
#   - Inputs: pair-valued K5 edges fixed exactly by H=<01>, mass 0 through 14.
#   - Outputs: dense ranks modulo N(H)/H=S3.
#   - Side effects: none.
# - Split-When:
#   - Another exact stabilizer gets its own constructive rank.
# - Merge-When:
#   - Complete dense S5 ranking owns all exact-stabilizer strata.
# - Summary:
#   - Filter a weighted S3 bundle quotient to exact-transposition states.
# - Description:
#   - H-fixed edges are one fixed pair plus three weighted four-scalar bundles;
#     the normalizer quotient permutes the bundles as S3.
# - Usage:
#   - Dense rank for the largest symmetric mass-fourteen exception stratum.
# - Defaults:
#   - Direct S5 orbit exhaustion stops at mass three; arithmetic reaches 14.
#

"""Dense exact-transposition ranking in the full-S5 edge hard core."""

from __future__ import annotations

from bisect import bisect_left
from functools import cache
from itertools import combinations_with_replacement
from itertools import permutations
from itertools import product

_ARITY = 5
_EDGE_COUNT = 10
_EXHAUSTIVE_MASS = 3
_EXHAUSTIVE_RANK_MASS = 6
_MAXIMUM_MASS = 14
_PAIR_COMPONENTS = 2
_WIDTH_FOURTEEN_EXACT_COUNT = 239_656
_WIDTH_FOURTEEN_QUOTIENT_COUNT = 261_450
_H_ORDER = 2
_H_COSET_COUNT = 60
_EDGES = tuple(
    (left, right)
    for left in range(_ARITY)
    for right in range(left + 1, _ARITY)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_S5 = tuple(permutations(range(_ARITY)))
_H = (1, 0, 2, 3, 4)
_FIXED_EDGE = (0, 1)
_REMAINING = (2, 3, 4)

# H edge-orbit order: 01, {02,12}, {03,13}, {04,14}, 23, 24, 34.
_H_EDGE_ORBITS = (
    ((0, 1),),
    ((0, 2), (1, 2)),
    ((0, 3), (1, 3)),
    ((0, 4), (1, 4)),
    ((2, 3),),
    ((2, 4),),
    ((3, 4),),
)
_OPPOSITE_ORBIT = {2: 6, 3: 5, 4: 4}
_SPOKE_ORBIT = {2: 1, 3: 2, 4: 3}

type _Pair = tuple[int, int]
type _Bundle = tuple[int, int, int, int]
type _Bundles = tuple[_Bundle, _Bundle, _Bundle]
type _State = tuple[_Pair, _Bundles]
type _EdgePairs = tuple[_Pair, ...]


def _bundle_mass(bundle: _Bundle) -> int:
    return 2 * (bundle[0] + bundle[1]) + bundle[2] + bundle[3]


@cache
def _bundles(total: int) -> tuple[_Bundle, ...]:
    result: list[_Bundle] = []
    for first in range(total // 2 + 1):
        for second in range((total - 2 * first) // 2 + 1):
            remainder = total - 2 * first - 2 * second
            result.extend(
                (first, second, third, remainder - third)
                for third in range(remainder + 1)
            )
    return tuple(result)


def _bundle_key(bundle: _Bundle) -> tuple[int, _Bundle]:
    return _bundle_mass(bundle), bundle


def _bundle_multisets_for_masses(
    first_mass: int,
    second_mass: int,
    third_mass: int,
) -> tuple[_Bundles, ...]:
    first = _bundles(first_mass)
    second = _bundles(second_mass)
    third = _bundles(third_mass)
    if first_mass == third_mass:
        result = tuple(combinations_with_replacement(first, 3))
    elif first_mass == second_mass:
        result = tuple(
            (*pair, last)
            for pair in combinations_with_replacement(first, 2)
            for last in third
        )
    elif second_mass == third_mass:
        result = tuple(
            (head, *pair)
            for head in first
            for pair in combinations_with_replacement(second, 2)
        )
    else:
        result = tuple(product(first, second, third))
    return result


@cache
def _bundle_multisets(total: int) -> tuple[_Bundles, ...]:
    result: list[_Bundles] = []
    for first_mass in range(total + 1):
        for second_mass in range(first_mass, total + 1):
            third_mass = total - first_mass - second_mass
            if third_mass < second_mass:
                continue
            result.extend(
                _bundle_multisets_for_masses(
                    first_mass,
                    second_mass,
                    third_mass,
                )
            )
    return tuple(result)


@cache
def _quotient_count(total: int) -> int:
    return sum(
        (fixed_mass + 1) * len(_bundle_multisets(total - fixed_mass))
        for fixed_mass in range(total + 1)
    )


def _choose_fixed_mass(total: int, rank: int) -> tuple[int, int]:
    remaining = rank
    for fixed_mass in range(total + 1):
        block = (fixed_mass + 1) * len(
            _bundle_multisets(total - fixed_mass)
        )
        if remaining >= block:
            remaining -= block
            continue
        return fixed_mass, remaining
    raise AssertionError


def _quotient_unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _quotient_count(total):
        return None
    fixed_mass, remaining = _choose_fixed_mass(total, rank)
    bundles = _bundle_multisets(total - fixed_mass)
    fixed_rank, bundle_rank = divmod(remaining, len(bundles))
    return (fixed_rank, fixed_mass - fixed_rank), bundles[bundle_rank]


def _canonical_quotient_rank(fixed: _Pair, bundles: _Bundles) -> int:
    fixed_mass = sum(fixed)
    bundle_mass = sum(_bundle_mass(bundle) for bundle in bundles)
    total = fixed_mass + bundle_mass
    candidates = _bundle_multisets(bundle_mass)
    bundle_rank = candidates.index(bundles)
    prefix = sum(
        (mass + 1) * len(_bundle_multisets(total - mass))
        for mass in range(fixed_mass)
    )
    return prefix + fixed[0] * len(candidates) + bundle_rank


def _quotient_rank(state: _State) -> int | None:
    fixed, bundles = state
    valid = not any(value < 0 for value in fixed) and not any(
        value < 0 for bundle in bundles for value in bundle
    )
    canonical = tuple(sorted(bundles, key=_bundle_key))
    if not valid or canonical != bundles:
        return None
    if bundles not in _bundle_multisets(
        sum(_bundle_mass(bundle) for bundle in bundles)
    ):
        return None
    return _canonical_quotient_rank(fixed, bundles)


def _edge_orbit_index() -> tuple[int, ...]:
    result = [-1] * _EDGE_COUNT
    for orbit_index, orbit in enumerate(_H_EDGE_ORBITS):
        for edge in orbit:
            result[_EDGE_INDEX[edge]] = orbit_index
    assert all(index >= 0 for index in result)
    return tuple(result)


_EDGE_ORBIT_INDEX = _edge_orbit_index()
_BASE_SIGNATURE = _EDGE_ORBIT_INDEX


def _coset_signatures() -> tuple[tuple[int, ...], ...]:
    signatures: set[tuple[int, ...]] = set()
    for order in _S5:
        signature: list[int] = []
        for left, right in _EDGES:
            image = tuple(sorted((order[left], order[right])))
            source = _EDGE_INDEX[image[0], image[1]]
            signature.append(_EDGE_ORBIT_INDEX[source])
        signatures.add(tuple(signature))
    assert len(signatures) == _H_COSET_COUNT
    signatures.remove(_BASE_SIGNATURE)
    return tuple(sorted(signatures))


_COSET_SIGNATURES = _coset_signatures()


def _orbit_values(state: _State) -> tuple[_Pair, ...]:
    fixed, bundles = state
    result: list[_Pair | None] = [None] * len(_H_EDGE_ORBITS)
    result[0] = fixed
    for vertex, bundle in zip(_REMAINING, bundles, strict=True):
        result[_SPOKE_ORBIT[vertex]] = bundle[0], bundle[1]
        result[_OPPOSITE_ORBIT[vertex]] = bundle[2], bundle[3]
    assert all(value is not None for value in result)
    first, second, third, fourth, fifth, sixth, seventh = result
    assert first is not None
    assert second is not None
    assert third is not None
    assert fourth is not None
    assert fifth is not None
    assert sixth is not None
    assert seventh is not None
    return first, second, third, fourth, fifth, sixth, seventh


def _has_exact_h_stabilizer(state: _State) -> bool:
    values = _orbit_values(state)
    original = tuple(values[index] for index in _BASE_SIGNATURE)
    return not any(
        all(values[signature[index]] == original[index] for index in range(10))
        for signature in _COSET_SIGNATURES
    )


@cache
def _accepted_quotient_ranks(total: int) -> tuple[int, ...]:
    return tuple(
        rank
        for rank in range(_quotient_count(total))
        if (
            (state := _quotient_unrank(total, rank)) is not None
            and _has_exact_h_stabilizer(state)
        )
    )


def _dense_count(total: int) -> int:
    return len(_accepted_quotient_ranks(total))


def _dense_rank(state: _State) -> int | None:
    quotient_rank = _quotient_rank(state)
    if quotient_rank is None:
        return None
    accepted = _accepted_quotient_ranks(
        sum(state[0]) + sum(_bundle_mass(bundle) for bundle in state[1])
    )
    index = bisect_left(accepted, quotient_rank)
    if index == len(accepted) or accepted[index] != quotient_rank:
        return None
    return index


def _dense_unrank(total: int, rank: int) -> _State | None:
    accepted = _accepted_quotient_ranks(total)
    if rank < 0 or rank >= len(accepted):
        return None
    return _quotient_unrank(total, accepted[rank])


def _build_edge_pairs(state: _State) -> _EdgePairs:
    values = _orbit_values(state)
    return tuple(
        values[_EDGE_ORBIT_INDEX[index]] for index in range(_EDGE_COUNT)
    )


def _permute(edge_pairs: _EdgePairs, order: tuple[int, ...]) -> _EdgePairs:
    result: list[_Pair] = []
    for left, right in _EDGES:
        image = tuple(sorted((order[left], order[right])))
        result.append(edge_pairs[_EDGE_INDEX[image[0], image[1]]])
    return tuple(result)


def _stabilizer_order(edge_pairs: _EdgePairs) -> int:
    return sum(_permute(edge_pairs, order) == edge_pairs for order in _S5)


def test_transposition_quotient_has_exact_weighted_bundle_count() -> None:
    """H-fixed/N(H) states are one fixed pair plus a weighted S3 multiset."""
    assert _quotient_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_QUOTIENT_COUNT
    for total in range(_MAXIMUM_MASS + 1):
        for rank in {
            0,
            _quotient_count(total) // 2,
            _quotient_count(total) - 1,
        }:
            state = _quotient_unrank(total, rank)
            assert state is not None
            assert _quotient_rank(state) == rank


def test_transposition_dense_rank_matches_direct_small_s5_orbits() -> None:
    """Exact-H canonical states map one-to-one to direct S5 orbits."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        observed: set[_EdgePairs] = set()
        for rank in range(_dense_count(total)):
            state = _dense_unrank(total, rank)
            assert state is not None
            edge_pairs = _build_edge_pairs(state)
            assert _stabilizer_order(edge_pairs) == _H_ORDER
            representative = min(_permute(edge_pairs, order) for order in _S5)
            assert representative not in observed
            observed.add(representative)
            assert _dense_rank(state) == rank
        assert len(observed) == _dense_count(total)


def test_transposition_dense_rank_exhausts_small_domains() -> None:
    """Every exact-transposition class through mass six gets one dense rank."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        for rank in range(_dense_count(total)):
            state = _dense_unrank(total, rank)
            assert state is not None
            assert _dense_rank(state) == rank


def test_transposition_dense_rank_roundtrips_through_mass_fourteen() -> None:
    """Checked exact-H counts and representative ranks reach mass fourteen."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _dense_count(total)
        assert _dense_unrank(total, -1) is None
        assert _dense_unrank(total, count) is None
        if count == 0:
            continue
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _dense_unrank(total, rank)
            assert state is not None
            assert _dense_rank(state) == rank
            assert _has_exact_h_stabilizer(state)
    assert _dense_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_EXACT_COUNT
