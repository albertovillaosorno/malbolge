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
#   - Dense quotient and normalizer-free rank/unrank for widened
#     single-transposition H-fixed K5 edges modulo N(H)/H=S3.
# - Must-Not:
#   - Claim exact-H filtering or the complete single-transposition S5 stratum.
# - Allows:
#   - Inputs: one fixed four-vector and three weighted eight-scalar bundles.
#   - Outputs: dense quotient ranks and pairwise-distinct free-S3 ranks.
#   - Side effects: none.
# - Split-When:
#   - Exact-H exclusion maps the remaining S3-stabilizer classes.
# - Merge-When:
#   - Complete widened full-S5 dense ranking owns the same S3 quotient.
# - Summary:
#   - Rank one fixed edge with multiset and pairwise-distinct bundle triples.
# - Description:
#   - Each bundle has four weight-two spoke scalars and four weight-one
#     opposite scalars.
# - Usage:
#   - Free-S3 prerequisite with 133,547,296 mass-fourteen candidates.
# - Defaults:
#   - Exhaustive dense domains stop at mass six; arithmetic reaches fourteen.
#

"""Dense widened single-transposition quotient in the full-S5 edge core."""

from __future__ import annotations

from itertools import permutations
from math import comb
from operator import itemgetter

_COMPONENTS = 4
_BUNDLE_PARTS = 2
_EXHAUSTIVE_MASS = 6
_MAXIMUM_MASS = 14
_WIDTH_FOURTEEN_COUNT = 137_230_360
_WIDTH_FOURTEEN_FREE_COUNT = 133_547_296
_EXPECTED_FREE_COUNTS = (
    0,
    0,
    6,
    84,
    619,
    3_420,
    15_710,
    63_224,
    229_630,
    767_648,
    2_393_880,
    7_033_408,
    19_616_888,
    52_250_304,
    133_547_296,
)
_EXPECTED_COUNTS = (
    1,
    8,
    50,
    268,
    1_277,
    5_492,
    21_658,
    79_008,
    268_949,
    860_336,
    2_602_384,
    7_483_312,
    20_552_900,
    54_134_576,
    137_230_360,
)

type _Vector = tuple[int, ...]
type _Bundle = tuple[_Vector, _Vector]
type _Bundles = tuple[_Bundle, _Bundle, _Bundle]
type _State = tuple[_Vector, _Bundles]


def _composition_count(total: int) -> int:
    if total < 0:
        return 0
    return comb(total + _COMPONENTS - 1, _COMPONENTS - 1)


def _composition_rank(vector: _Vector, total: int) -> int | None:
    if len(vector) != _COMPONENTS or any(value < 0 for value in vector):
        return None
    if sum(vector) != total:
        return None
    rank = 0
    remaining = total
    for index, value in enumerate(vector[:-1]):
        tail = _COMPONENTS - index - 1
        rank += sum(
            comb(remaining - earlier + tail - 1, tail - 1)
            for earlier in range(value)
        )
        remaining -= value
    return rank


def _composition_unrank(total: int, rank: int) -> _Vector | None:
    if rank < 0 or rank >= _composition_count(total):
        return None
    remaining_rank = rank
    remaining_total = total
    values: list[int] = []
    for index in range(_COMPONENTS - 1):
        tail = _COMPONENTS - index - 1
        for value in range(remaining_total + 1):
            block = comb(remaining_total - value + tail - 1, tail - 1)
            if remaining_rank >= block:
                remaining_rank -= block
                continue
            values.append(value)
            remaining_total -= value
            break
    values.append(remaining_total)
    return tuple(values)


def _bundle_mass(bundle: _Bundle) -> int:
    spoke, opposite = bundle
    return 2 * sum(spoke) + sum(opposite)


def _bundle_count(total: int) -> int:
    return sum(
        _composition_count(spoke_mass)
        * _composition_count(total - 2 * spoke_mass)
        for spoke_mass in range(total // 2 + 1)
    )


def _bundle_rank(bundle: _Bundle) -> int | None:
    spoke, opposite = bundle
    if len(spoke) != _COMPONENTS or len(opposite) != _COMPONENTS:
        return None
    spoke_mass = sum(spoke)
    opposite_mass = sum(opposite)
    total = 2 * spoke_mass + opposite_mass
    spoke_rank = _composition_rank(spoke, spoke_mass)
    opposite_rank = _composition_rank(opposite, opposite_mass)
    if spoke_rank is None or opposite_rank is None:
        return None
    prefix = sum(
        _composition_count(mass) * _composition_count(total - 2 * mass)
        for mass in range(spoke_mass)
    )
    return (
        prefix + spoke_rank * _composition_count(opposite_mass) + opposite_rank
    )


def _bundle_unrank(total: int, rank: int) -> _Bundle | None:
    if rank < 0 or rank >= _bundle_count(total):
        return None
    remaining = rank
    for spoke_mass in range(total // 2 + 1):
        opposite_mass = total - 2 * spoke_mass
        opposite_count = _composition_count(opposite_mass)
        block = _composition_count(spoke_mass) * opposite_count
        if remaining >= block:
            remaining -= block
            continue
        spoke_rank, opposite_rank = divmod(remaining, opposite_count)
        spoke = _composition_unrank(spoke_mass, spoke_rank)
        opposite = _composition_unrank(opposite_mass, opposite_rank)
        assert spoke is not None
        assert opposite is not None
        return spoke, opposite
    raise AssertionError


def _bundle_key(bundle: _Bundle) -> tuple[int, int]:
    rank = _bundle_rank(bundle)
    assert rank is not None
    return _bundle_mass(bundle), rank


def _pair_count(population: int) -> int:
    return population * (population + 1) // 2


def _pair_rank(left: int, right: int, population: int) -> int:
    assert 0 <= left <= right < population
    return left * population - left * (left - 1) // 2 + right - left


def _pair_unrank(rank: int, population: int) -> tuple[int, int]:
    remaining = rank
    for left in range(population):
        block = population - left
        if remaining >= block:
            remaining -= block
            continue
        return left, left + remaining
    raise AssertionError


def _triple_repetition_count(population: int) -> int:
    return comb(population + 2, 3)


def _triple_repetition_rank(
    ranks: tuple[int, int, int],
    population: int,
) -> int:
    first, second, third = ranks
    assert 0 <= first <= second <= third < population
    prefix_first = _triple_repetition_count(population) - comb(
        population - first + 2,
        3,
    )
    prefix_second = sum(population - value for value in range(first, second))
    return prefix_first + prefix_second + third - second


def _triple_repetition_unrank(
    rank: int, population: int
) -> tuple[int, int, int]:
    remaining = rank
    for first in range(population):
        block = comb(population - first + 1, 2)
        if remaining >= block:
            remaining -= block
            continue
        for second in range(first, population):
            second_block = population - second
            if remaining >= second_block:
                remaining -= second_block
                continue
            return first, second, second + remaining
    raise AssertionError


def _mass_triples(total: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (first, second, third)
        for first in range(total + 1)
        for second in range(first, total + 1)
        for third in (total - first - second,)
        if third >= second
    )


def _triple_counts(masses: tuple[int, int, int]) -> tuple[int, int, int]:
    return (
        _bundle_count(masses[0]),
        _bundle_count(masses[1]),
        _bundle_count(masses[2]),
    )


def _triple_block_count(masses: tuple[int, int, int]) -> int:
    first, second, third = masses
    first_count, second_count, third_count = _triple_counts(masses)
    if first == third:
        result = _triple_repetition_count(first_count)
    elif first == second:
        result = _pair_count(first_count) * third_count
    elif second == third:
        result = first_count * _pair_count(second_count)
    else:
        result = first_count * second_count * third_count
    return result


def _triple_count(total: int) -> int:
    return sum(_triple_block_count(masses) for masses in _mass_triples(total))


def _triple_local_rank(
    masses: tuple[int, int, int],
    ranks: tuple[int, int, int],
) -> int:
    first, second, third = masses
    first_rank, second_rank, third_rank = ranks
    first_count, second_count, third_count = _triple_counts(masses)
    if first == third:
        result = _triple_repetition_rank(ranks, first_count)
    elif first == second:
        result = (
            _pair_rank(first_rank, second_rank, first_count) * third_count
            + third_rank
        )
    elif second == third:
        result = first_rank * _pair_count(second_count) + _pair_rank(
            second_rank, third_rank, second_count
        )
    else:
        result = (
            first_rank * second_count + second_rank
        ) * third_count + third_rank
    return result


def _triple_rank(bundles: _Bundles) -> int | None:
    ranked = tuple((_bundle_key(bundle), bundle) for bundle in bundles)
    first, second, third = sorted(ranked, key=itemgetter(0))
    masses = first[0][0], second[0][0], third[0][0]
    ranks = first[0][1], second[0][1], third[0][1]
    total = sum(masses)
    prefix = sum(
        _triple_block_count(candidate)
        for candidate in _mass_triples(total)
        if candidate < masses
    )
    return prefix + _triple_local_rank(masses, ranks)


def _unrank_first_pair(
    rank: int, first_count: int, third_count: int
) -> tuple[int, int, int]:
    pair_rank, third_rank = divmod(rank, third_count)
    pair = _pair_unrank(pair_rank, first_count)
    return pair[0], pair[1], third_rank


def _unrank_second_pair(rank: int, second_count: int) -> tuple[int, int, int]:
    first_rank, pair_rank = divmod(rank, _pair_count(second_count))
    pair = _pair_unrank(pair_rank, second_count)
    return first_rank, pair[0], pair[1]


def _unrank_distinct(
    rank: int, second_count: int, third_count: int
) -> tuple[int, int, int]:
    first_rank, residual = divmod(rank, second_count * third_count)
    second_rank, third_rank = divmod(residual, third_count)
    return first_rank, second_rank, third_rank


def _triple_local_unrank(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    first, second, third = masses
    first_count, second_count, third_count = _triple_counts(masses)
    if first == third:
        result = _triple_repetition_unrank(rank, first_count)
    elif first == second:
        result = _unrank_first_pair(rank, first_count, third_count)
    elif second == third:
        result = _unrank_second_pair(rank, second_count)
    else:
        result = _unrank_distinct(rank, second_count, third_count)
    return result


def _triple_unrank(total: int, rank: int) -> _Bundles | None:
    if rank < 0 or rank >= _triple_count(total):
        return None
    remaining = rank
    for masses in _mass_triples(total):
        block = _triple_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        ranks = _triple_local_unrank(masses, remaining)
        first = _bundle_unrank(masses[0], ranks[0])
        second = _bundle_unrank(masses[1], ranks[1])
        third = _bundle_unrank(masses[2], ranks[2])
        assert first is not None
        assert second is not None
        assert third is not None
        return first, second, third
    raise AssertionError


def _count(total: int) -> int:
    return sum(
        _composition_count(fixed_mass) * _triple_count(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def _rank(state: _State) -> int | None:
    fixed, bundles = state
    fixed_mass = sum(fixed)
    fixed_rank = _composition_rank(fixed, fixed_mass)
    bundle_total = sum(_bundle_mass(bundle) for bundle in bundles)
    triple_rank = _triple_rank(bundles)
    if fixed_rank is None or triple_rank is None:
        return None
    total = fixed_mass + bundle_total
    prefix = sum(
        _composition_count(mass) * _triple_count(total - mass)
        for mass in range(fixed_mass)
    )
    return prefix + fixed_rank * _triple_count(bundle_total) + triple_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        bundle_total = total - fixed_mass
        triple_count = _triple_count(bundle_total)
        block = _composition_count(fixed_mass) * triple_count
        if remaining >= block:
            remaining -= block
            continue
        fixed_rank, triple_rank = divmod(remaining, triple_count)
        fixed = _composition_unrank(fixed_mass, fixed_rank)
        bundles = _triple_unrank(bundle_total, triple_rank)
        assert fixed is not None
        assert bundles is not None
        return fixed, bundles
    raise AssertionError


def _strict_pair_count(population: int) -> int:
    return comb(population, 2)


def _strict_pair_rank(left: int, right: int, population: int) -> int:
    assert 0 <= left < right < population
    return left * (2 * population - left - 1) // 2 + right - left - 1


def _strict_pair_unrank(rank: int, population: int) -> tuple[int, int]:
    remaining = rank
    for left in range(population):
        block = population - left - 1
        if remaining >= block:
            remaining -= block
            continue
        return left, left + 1 + remaining
    raise AssertionError


def _strict_triple_count(population: int) -> int:
    return comb(population, 3)


def _strict_triple_rank(
    ranks: tuple[int, int, int],
    population: int,
) -> int:
    first, second, third = ranks
    assert 0 <= first < second < third < population
    prefix_first = sum(
        comb(population - value - 1, 2) for value in range(first)
    )
    prefix_second = sum(
        population - value - 1 for value in range(first + 1, second)
    )
    return prefix_first + prefix_second + third - second - 1


def _strict_triple_unrank(
    rank: int,
    population: int,
) -> tuple[int, int, int]:
    remaining = rank
    for first in range(population):
        block = comb(population - first - 1, 2)
        if remaining >= block:
            remaining -= block
            continue
        for second in range(first + 1, population):
            second_block = population - second - 1
            if remaining >= second_block:
                remaining -= second_block
                continue
            return first, second, second + 1 + remaining
    raise AssertionError


def _free_triple_block_count(masses: tuple[int, int, int]) -> int:
    first, second, third = masses
    first_count, second_count, third_count = _triple_counts(masses)
    if first == third:
        result = _strict_triple_count(first_count)
    elif first == second:
        result = _strict_pair_count(first_count) * third_count
    elif second == third:
        result = first_count * _strict_pair_count(second_count)
    else:
        result = first_count * second_count * third_count
    return result


def _free_triple_count(total: int) -> int:
    return sum(
        _free_triple_block_count(masses) for masses in _mass_triples(total)
    )


def _free_triple_local_rank(
    masses: tuple[int, int, int],
    ranks: tuple[int, int, int],
) -> int:
    first, second, third = masses
    first_rank, second_rank, third_rank = ranks
    first_count, second_count, third_count = _triple_counts(masses)
    if first == third:
        result = _strict_triple_rank(ranks, first_count)
    elif first == second:
        result = (
            _strict_pair_rank(first_rank, second_rank, first_count)
            * third_count
            + third_rank
        )
    elif second == third:
        result = first_rank * _strict_pair_count(
            second_count
        ) + _strict_pair_rank(
            second_rank,
            third_rank,
            second_count,
        )
    else:
        result = (
            first_rank * second_count + second_rank
        ) * third_count + third_rank
    return result


def _free_triple_rank(bundles: _Bundles) -> int | None:
    keys = tuple(sorted(_bundle_key(bundle) for bundle in bundles))
    first, second, third = keys
    if second in {first, third}:
        return None
    masses = first[0], second[0], third[0]
    ranks = first[1], second[1], third[1]
    total = sum(masses)
    prefix = sum(
        _free_triple_block_count(candidate)
        for candidate in _mass_triples(total)
        if candidate < masses
    )
    return prefix + _free_triple_local_rank(masses, ranks)


def _free_unrank_first_pair(
    rank: int,
    first_count: int,
    third_count: int,
) -> tuple[int, int, int]:
    pair_rank, third_rank = divmod(rank, third_count)
    pair = _strict_pair_unrank(pair_rank, first_count)
    return pair[0], pair[1], third_rank


def _free_unrank_second_pair(
    rank: int,
    second_count: int,
) -> tuple[int, int, int]:
    first_rank, pair_rank = divmod(rank, _strict_pair_count(second_count))
    pair = _strict_pair_unrank(pair_rank, second_count)
    return first_rank, pair[0], pair[1]


def _free_triple_local_unrank(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    first, second, third = masses
    first_count, second_count, third_count = _triple_counts(masses)
    if first == third:
        result = _strict_triple_unrank(rank, first_count)
    elif first == second:
        result = _free_unrank_first_pair(rank, first_count, third_count)
    elif second == third:
        result = _free_unrank_second_pair(rank, second_count)
    else:
        result = _unrank_distinct(rank, second_count, third_count)
    return result


def _free_triple_unrank(total: int, rank: int) -> _Bundles | None:
    if rank < 0 or rank >= _free_triple_count(total):
        return None
    remaining = rank
    for masses in _mass_triples(total):
        block = _free_triple_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        ranks = _free_triple_local_unrank(masses, remaining)
        first = _bundle_unrank(masses[0], ranks[0])
        second = _bundle_unrank(masses[1], ranks[1])
        third = _bundle_unrank(masses[2], ranks[2])
        assert first is not None
        assert second is not None
        assert third is not None
        return first, second, third
    raise AssertionError


def _free_count(total: int) -> int:
    return sum(
        _composition_count(fixed_mass) * _free_triple_count(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def _free_rank(state: _State) -> int | None:
    fixed, bundles = state
    fixed_mass = sum(fixed)
    fixed_rank = _composition_rank(fixed, fixed_mass)
    bundle_total = sum(_bundle_mass(bundle) for bundle in bundles)
    triple_rank = _free_triple_rank(bundles)
    if fixed_rank is None or triple_rank is None:
        return None
    total = fixed_mass + bundle_total
    prefix = sum(
        _composition_count(mass) * _free_triple_count(total - mass)
        for mass in range(fixed_mass)
    )
    return prefix + fixed_rank * _free_triple_count(bundle_total) + triple_rank


def _free_unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _free_count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        bundle_total = total - fixed_mass
        triple_count = _free_triple_count(bundle_total)
        block = _composition_count(fixed_mass) * triple_count
        if remaining >= block:
            remaining -= block
            continue
        fixed_rank, triple_rank = divmod(remaining, triple_count)
        fixed = _composition_unrank(fixed_mass, fixed_rank)
        bundles = _free_triple_unrank(bundle_total, triple_rank)
        assert fixed is not None
        assert bundles is not None
        return fixed, bundles
    raise AssertionError


def _ordered_triple_count(total: int) -> int:
    return sum(
        _bundle_count(first)
        * _bundle_count(second)
        * _bundle_count(total - first - second)
        for first in range(total + 1)
        for second in range(total - first + 1)
    )


def _transposition_fixed_count(total: int) -> int:
    return sum(
        _bundle_count(single_mass) * _bundle_count(pair_mass)
        for pair_mass in range(total // 2 + 1)
        for single_mass in (total - 2 * pair_mass,)
    )


def _three_cycle_fixed_count(total: int) -> int:
    return _bundle_count(total // 3) if total % 3 == 0 else 0


def _burnside_triple_count(total: int) -> int:
    numerator = (
        _ordered_triple_count(total)
        + 3 * _transposition_fixed_count(total)
        + 2 * _three_cycle_fixed_count(total)
    )
    assert numerator % 6 == 0
    return numerator // 6


def _burnside_count(total: int) -> int:
    return sum(
        _composition_count(fixed_mass)
        * _burnside_triple_count(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def test_transposition_free_rank_has_reviewed_distinct_bundle_counts() -> None:
    """Pairwise-distinct bundle counts match the reviewed free-S3 sequence."""
    observed = tuple(_free_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_FREE_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_FREE_COUNT


def test_transposition_free_rank_exhausts_small_domains() -> None:
    """Every free normalizer class through mass six has one dense rank."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        for rank in range(_free_count(total)):
            state = _free_unrank(total, rank)
            assert state is not None
            assert _free_rank(state) == rank
            fixed, bundles = state
            for order in permutations(range(3)):
                permuted = (
                    bundles[order[0]],
                    bundles[order[1]],
                    bundles[order[2]],
                )
                assert _free_rank((fixed, permuted)) == rank


def test_transposition_free_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior free-S3 ranks roundtrip through mass fourteen."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _free_count(total)
        assert _free_unrank(total, -1) is None
        assert _free_unrank(total, count) is None
        if count == 0:
            continue
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _free_unrank(total, rank)
            assert state is not None
            assert _free_rank(state) == rank


def test_transposition_quotient_count_matches_s3_burnside() -> None:
    """The graded multiset count matches the independent S3 Burnside average."""
    observed = tuple(_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed == tuple(
        _burnside_count(total) for total in range(_MAXIMUM_MASS + 1)
    )
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT


def test_transposition_quotient_rank_exhausts_small_domains() -> None:
    """Every quotient class through mass six receives one contiguous rank."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        for rank in range(_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(state) == rank
            fixed, bundles = state
            for order in permutations(range(3)):
                permuted = (
                    bundles[order[0]],
                    bundles[order[1]],
                    bundles[order[2]],
                )
                assert _rank((fixed, permuted)) == rank


def test_transposition_quotient_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior quotient ranks roundtrip through mass fourteen."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(state) == rank
