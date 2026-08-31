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
#   - Independent generic ordered-tuple quotient evidence for crazy preimage
#     cubes under simultaneous ambiguity-coordinate permutation.
# - Must-Not:
#   - Treat coordinate orbits as position-sensitive semantic equivalence or
#     silently add endpoint-permutation symmetry.
# - Allows:
#   - Inputs: ordered endpoint arities one through eight and cube dimensions
#     zero through fourteen.
#   - Outputs: exact joint-count canonical forms, orbit masses, and global
#     reachable-pair representative counts.
#   - Side effects: none.
# - Split-When:
#   - Endpoint-order symmetry or another coordinate action needs a new group.
# - Merge-When:
#   - A generic cube quotient correspondence owns this exact bounded theorem.
# - Summary:
#   - Generalize ordered cube tuple quotients through eight endpoints.
# - Description:
#   - Exhausts bounded raw tuples and checks exact composition/global formulas.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Exact formulas reach width fourteen; raw exhaustion is capped by an
#     sixteen-bit tuple-space budget.
#

"""Independent evidence for generic ordered crazy preimage-cube quotients."""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from itertools import product
from math import comb
from math import factorial

_MAXIMUM_ARITY = 8
_MAXIMUM_TRITS = 14
_RAW_EXHAUSTION_BITS = 16
_REACHABLE_SINGLETON_LOCAL_COUNT = 5
_REACHABLE_AMBIGUOUS_LOCAL_COUNT = 2
_WIDTH_FOURTEEN_LOCAL_COUNTS = {
    7: 7_227_209_188_850_973_120,
    8: 84_466_573_066_471_253_216_128,
}
_WIDTH_FOURTEEN_GLOBAL_COUNTS = {
    3: 547_751_638_341_145,
    4: 25_678_405_217_633_865,
    5: 3_571_359_808_057_227_945,
    6: 1_584_315_319_509_725_541_225,
    7: 2_119_509_834_155_204_235_011_305,
    8: 7_093_373_076_831_030_274_633_041_897,
}


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _tuple_symbol(codes: tuple[int, ...], coordinate: int) -> int:
    result = 0
    for code in codes:
        result = (result << 1) | ((code >> coordinate) & 1)
    return result


def _tuple_counts(codes: tuple[int, ...], dimension: int) -> tuple[int, ...]:
    counts = [0] * (1 << len(codes))
    for coordinate in range(dimension):
        counts[_tuple_symbol(codes, coordinate)] += 1
    return tuple(counts)


def _tuple_order(codes: tuple[int, ...], dimension: int) -> tuple[int, ...]:
    buckets: list[list[int]] = [[] for _ in range(1 << len(codes))]
    for coordinate in range(dimension):
        buckets[_tuple_symbol(codes, coordinate)].append(coordinate)
    return tuple(
        coordinate
        for symbol in reversed(range(len(buckets)))
        for coordinate in buckets[symbol]
    )


def _permute_code(code: int, order: tuple[int, ...]) -> int:
    result = 0
    for destination, source in enumerate(order):
        result |= ((code >> source) & 1) << destination
    return result


def _canonical_tuple(counts: tuple[int, ...], arity: int) -> tuple[int, ...]:
    result = [0] * arity
    destination = 0
    for symbol in reversed(range(1 << arity)):
        for _ in range(counts[symbol]):
            for endpoint in range(arity):
                shift = arity - endpoint - 1
                result[endpoint] |= ((symbol >> shift) & 1) << destination
            destination += 1
    return tuple(result)


def _canonicalize_tuple(
    codes: tuple[int, ...],
    dimension: int,
) -> tuple[int, ...]:
    order = _tuple_order(codes, dimension)
    return tuple(_permute_code(code, order) for code in codes)


def _orbit_mass(counts: tuple[int, ...]) -> int:
    result = factorial(sum(counts))
    for count in counts:
        result //= factorial(count)
    return result


def _composition_count(symbol_count: int, dimension: int) -> int:
    counts = [1] + [0] * dimension
    for _ in range(symbol_count):
        next_counts = [0] * (dimension + 1)
        running = 0
        for total in range(dimension + 1):
            running += counts[total]
            next_counts[total] = running
        counts = next_counts
    return counts[dimension]


def _multinomial_mass_sum(symbol_count: int, dimension: int) -> int:
    masses = [1] + [0] * dimension
    for _ in range(symbol_count):
        next_masses = [0] * (dimension + 1)
        for total in range(dimension + 1):
            next_masses[total] = sum(
                comb(total, chosen) * masses[total - chosen]
                for chosen in range(total + 1)
            )
        masses = next_masses
    return masses[dimension]


def _fixed_pair_class_count(trit_count: int, dimension: int) -> int:
    return (
        comb(trit_count, dimension)
        * _integer_power(_REACHABLE_AMBIGUOUS_LOCAL_COUNT, dimension)
        * _integer_power(
            _REACHABLE_SINGLETON_LOCAL_COUNT,
            trit_count - dimension,
        )
    )


def _ordered_tuple_classes(arity: int, dimension: int) -> int:
    symbol_count = 1 << arity
    return comb(dimension + symbol_count - 1, symbol_count - 1)


def _direct_global_count(arity: int, trit_count: int) -> int:
    return sum(
        _fixed_pair_class_count(trit_count, dimension)
        * _ordered_tuple_classes(arity, dimension)
        for dimension in range(trit_count + 1)
    )


def _closed_global_count(arity: int, trit_count: int) -> int:
    separators = (1 << arity) - 1
    return sum(
        comb(separators, degree)
        * comb(trit_count, degree)
        * _integer_power(_REACHABLE_AMBIGUOUS_LOCAL_COUNT, degree)
        * _integer_power(7, trit_count - degree)
        for degree in range(min(separators, trit_count) + 1)
    )


def test_generic_ordered_tuple_orbits_are_exact_under_bounded_exhaustion() -> (
    None
):
    """Classify every raw tuple exactly inside the exhaustion cap."""
    for arity in range(1, _MAXIMUM_ARITY + 1):
        maximum_dimension = min(
            _MAXIMUM_TRITS,
            _RAW_EXHAUSTION_BITS // arity,
        )
        for dimension in range(maximum_dimension + 1):
            cube_size = 1 << dimension
            observed: Counter[tuple[int, ...]] = Counter()
            representatives: set[tuple[int, ...]] = set()
            for codes in product(range(cube_size), repeat=arity):
                counts = _tuple_counts(codes, dimension)
                canonical = _canonicalize_tuple(codes, dimension)
                assert canonical == _canonical_tuple(counts, arity)
                assert _tuple_counts(canonical, dimension) == counts
                observed[counts] += 1
                representatives.add(canonical)
            expected = _ordered_tuple_classes(arity, dimension)
            assert len(observed) == expected
            assert len(representatives) == expected
            assert observed == Counter({
                counts: _orbit_mass(counts) for counts in observed
            })


def test_generic_ordered_tuple_counts_cover_checked_arities_and_dimensions(
) -> None:
    """Cover every checked cube by composition classes and orbit masses."""
    for arity in range(1, _MAXIMUM_ARITY + 1):
        symbol_count = 1 << arity
        for dimension in range(_MAXIMUM_TRITS + 1):
            expected_classes = _ordered_tuple_classes(arity, dimension)
            assert (
                _composition_count(symbol_count, dimension)
                == expected_classes
            )
            assert _multinomial_mass_sum(symbol_count, dimension) == (
                _integer_power(symbol_count, dimension)
            )
    for arity, expected in _WIDTH_FOURTEEN_LOCAL_COUNTS.items():
        assert _ordered_tuple_classes(arity, _MAXIMUM_TRITS) == expected


def test_generic_global_ordered_tuple_count_matches_independent_transform() -> (
    None
):
    """Reachable-pair sums equal the closed checked-arity quotient transform."""
    for arity in range(1, _MAXIMUM_ARITY + 1):
        raw_local_mass = _REACHABLE_SINGLETON_LOCAL_COUNT + (
            _REACHABLE_AMBIGUOUS_LOCAL_COUNT * (1 << arity)
        )
        for trit_count in range(1, _MAXIMUM_TRITS + 1):
            direct = _direct_global_count(arity, trit_count)
            closed = _closed_global_count(arity, trit_count)
            raw = _integer_power(raw_local_mass, trit_count)
            assert direct == closed
            assert direct <= raw
    for arity, expected in _WIDTH_FOURTEEN_GLOBAL_COUNTS.items():
        assert _closed_global_count(arity, _MAXIMUM_TRITS) == expected


def _composition_rank(counts: tuple[int, ...]) -> int:
    separator_count = len(counts) - 1
    prefix = 0
    rank = 0
    for index in range(separator_count):
        prefix += counts[index]
        separator = prefix + index
        rank += comb(separator, index + 1)
    return rank


def _composition_unrank(
    rank: int,
    *,
    symbol_count: int,
    dimension: int,
) -> tuple[int, ...] | None:
    separator_count = symbol_count - 1
    size = comb(dimension + separator_count, separator_count)
    if rank < 0 or rank >= size:
        return None
    remaining = rank
    separators = [0] * separator_count
    upper = dimension + separator_count - 1
    for order in range(separator_count, 0, -1):
        separator = upper
        while comb(separator, order) > remaining:
            separator -= 1
        separators[order - 1] = separator
        remaining -= comb(separator, order)
        upper = separator - 1
    assert remaining == 0
    counts = [0] * symbol_count
    counts[0] = separators[0]
    for index in range(1, separator_count):
        counts[index] = separators[index] - separators[index - 1] - 1
    counts[-1] = dimension + separator_count - 1 - separators[-1]
    return tuple(counts)


def _counts_from_separators(
    separators: tuple[int, ...],
    *,
    symbol_count: int,
    dimension: int,
) -> tuple[int, ...]:
    counts = [0] * symbol_count
    counts[0] = separators[0]
    for index in range(1, len(separators)):
        counts[index] = separators[index] - separators[index - 1] - 1
    counts[-1] = dimension + len(separators) - 1 - separators[-1]
    return tuple(counts)


def test_ordered_tuple_class_rank_exhausts_small_composition_domains() -> None:
    """Colexicographic combinadics densely index every small quotient class."""
    for arity in range(1, 4):
        symbol_count = 1 << arity
        separator_count = symbol_count - 1
        for dimension in range(7):
            size = _ordered_tuple_classes(arity, dimension)
            observed: set[int] = set()
            for separators in combinations(
                range(dimension + separator_count),
                separator_count,
            ):
                counts = _counts_from_separators(
                    separators,
                    symbol_count=symbol_count,
                    dimension=dimension,
                )
                rank = _composition_rank(counts)
                decoded = _composition_unrank(
                    rank,
                    symbol_count=symbol_count,
                    dimension=dimension,
                )
                assert decoded == counts
                observed.add(rank)
            assert observed == set(range(size))


def test_ordered_tuple_class_rank_roundtrips_checked_domain_edges() -> None:
    """Rank and unrank stay exact through arity eight and dimension fourteen."""
    for arity in range(1, _MAXIMUM_ARITY + 1):
        symbol_count = 1 << arity
        for dimension in range(_MAXIMUM_TRITS + 1):
            size = _ordered_tuple_classes(arity, dimension)
            ranks = {0, size - 1, size // 2}
            for rank in ranks:
                counts = _composition_unrank(
                    rank,
                    symbol_count=symbol_count,
                    dimension=dimension,
                )
                assert counts is not None
                assert len(counts) == symbol_count
                assert sum(counts) == dimension
                assert all(count >= 0 for count in counts)
                assert _composition_rank(counts) == rank
            first = (0,) * (symbol_count - 1) + (dimension,)
            last = (dimension,) + (0,) * (symbol_count - 1)
            assert _composition_rank(first) == 0
            assert _composition_rank(last) == size - 1


def test_ordered_tuple_class_unrank_rejects_outside_dense_domain() -> None:
    """Dense quotient indexing rejects ranks outside its exact class count."""
    symbol_count = 1 << _MAXIMUM_ARITY
    dimension = _MAXIMUM_TRITS
    size = comb(dimension + symbol_count - 1, symbol_count - 1)
    for rank in (-1, size):
        assert _composition_unrank(
            rank,
            symbol_count=symbol_count,
            dimension=dimension,
        ) is None


def _ordered_budget_exceedance(
    arity: int,
    trit_count: int,
    budget: int,
) -> int:
    return sum(
        _fixed_pair_class_count(trit_count, dimension)
        for dimension in range(trit_count + 1)
        if _ordered_tuple_classes(arity, dimension) > budget
    )


def _ordered_budget_coverage(
    arity: int,
    trit_count: int,
    budget: int,
) -> int:
    return _integer_power(7, trit_count) - _ordered_budget_exceedance(
        arity,
        trit_count,
        budget,
    )


def _minimum_ordered_budget(
    arity: int,
    trit_count: int,
    target_pairs: int,
) -> int | None:
    reachable = _integer_power(7, trit_count)
    if target_pairs < 0 or target_pairs > reachable:
        return None
    if target_pairs == 0:
        return 0
    cumulative = 0
    for dimension in range(trit_count + 1):
        cumulative += _fixed_pair_class_count(trit_count, dimension)
        if cumulative >= target_pairs:
            return _ordered_tuple_classes(arity, dimension)
    raise AssertionError


def test_ordered_tuple_class_thresholds_are_strictly_increasing() -> None:
    """Checked ordered quotient budgets grow strictly with cube dimension."""
    for arity in range(1, _MAXIMUM_ARITY + 1):
        counts = tuple(
            _ordered_tuple_classes(arity, dimension)
            for dimension in range(_MAXIMUM_TRITS + 1)
        )
        assert counts[0] == 1
        assert all(
            counts[index] < counts[index + 1]
            for index in range(len(counts) - 1)
        )


def test_ordered_budget_exceedance_has_exact_checked_thresholds() -> None:
    """Every ordered budget threshold removes exactly one ambiguity class."""
    for arity in range(1, _MAXIMUM_ARITY + 1):
        for trit_count in range(1, _MAXIMUM_TRITS + 1):
            thresholds = tuple(
                _ordered_tuple_classes(arity, dimension)
                for dimension in range(trit_count + 1)
            )
            assert _ordered_budget_exceedance(arity, trit_count, 0) == (
                _integer_power(7, trit_count)
            )
            assert _ordered_budget_exceedance(
                arity,
                trit_count,
                thresholds[-1],
            ) == 0
            cumulative = 0
            for dimension, threshold in enumerate(thresholds):
                cumulative += _fixed_pair_class_count(trit_count, dimension)
                assert _ordered_budget_coverage(
                    arity,
                    trit_count,
                    threshold,
                ) == cumulative


def test_minimum_ordered_budget_inverts_exact_pair_coverage() -> None:
    """Minimum ordered-search budgets invert each checked ambiguity boundary."""
    for arity in range(1, _MAXIMUM_ARITY + 1):
        for trit_count in range(1, _MAXIMUM_TRITS + 1):
            cumulative = 0
            assert _minimum_ordered_budget(arity, trit_count, 0) == 0
            for dimension in range(trit_count + 1):
                threshold = _ordered_tuple_classes(arity, dimension)
                previous = cumulative
                cumulative += _fixed_pair_class_count(trit_count, dimension)
                assert _minimum_ordered_budget(
                    arity,
                    trit_count,
                    previous + 1,
                ) == threshold
                assert _minimum_ordered_budget(
                    arity,
                    trit_count,
                    cumulative,
                ) == threshold
            assert cumulative == _integer_power(7, trit_count)
            assert _minimum_ordered_budget(
                arity,
                trit_count,
                cumulative + 1,
            ) is None
