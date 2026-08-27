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
#   - Independent evidence for ordered and endpoint-unordered sextuple orbits
#     under shared ambiguity-coordinate permutation.
# - Must-Not:
#   - Apply endpoint-permutation equivalence to direction-sensitive analyses.
# - Allows:
#   - Inputs: reachable fixed accumulator/target pairs through width fourteen.
#   - Outputs: exact ordered and endpoint-unordered sextuple class counts.
#   - Side effects: none.
# - Split-When:
#   - A larger tuple arity or a different endpoint symmetry group is required.
# - Merge-When:
#   - Another proof owns the same S_k coordinate and S_6 endpoint actions.
# - Summary:
#   - Classify sextuples by joint counts and then quotient endpoint order.
# - Description:
#   - Exhausts the coordinate quotient through Q2 and checks Burnside to Q14.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Coordinate-quotient orbit enumeration stops at dimension two; Burnside
#     arithmetic reaches 14; fixed-pair lifting stops at width two.
#

"""Evidence for ordered and endpoint-unordered cube-sextuple quotients."""

from __future__ import annotations

from collections import Counter
from itertools import combinations_with_replacement
from itertools import permutations
from math import comb
from math import factorial

_AMBIGUOUS_MULTIPLICITY = 2
_ARITY = 6
_EXHAUSTIVE_DIMENSION = 2
_EXHAUSTIVE_TRITS = 2
_MAXIMUM_TRITS = 14
_PATTERN_COUNT = 1 << _ARITY
_RADIX = 3
_S6_ORDER = factorial(_ARITY)
_WIDTH_FOURTEEN_COUNT = 1_179_940_653_635
_WIDTH_FOURTEEN_FIXED_COUNTS = (
    839_983_521_106_400,
    624_814_559_200,
    281_038_424,
    4_150_120_800,
    1_846_872,
    2_700_856,
    6_050,
    201_249_216,
    171_120,
    217_400,
    1_020,
)
_ENDPOINT_PERMUTATIONS = tuple(permutations(range(_ARITY)))
_INDEPENDENT_CRAZY_TRIT = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _permuted_symbol(symbol: int, endpoint_order: tuple[int, ...]) -> int:
    bits = tuple(
        (symbol >> (_ARITY - index - 1)) & 1 for index in range(_ARITY)
    )
    result = 0
    for source in endpoint_order:
        result = (result << 1) | bits[source]
    return result


def _endpoint_cycle_type(endpoint_order: tuple[int, ...]) -> tuple[int, ...]:
    unseen = set(range(_ARITY))
    lengths: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = endpoint_order[current]
            length += 1
        lengths.append(length)
    return tuple(sorted(lengths))


def _label_cycle_lengths(endpoint_order: tuple[int, ...]) -> tuple[int, ...]:
    unseen = set(range(_PATTERN_COUNT))
    lengths: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = _permuted_symbol(current, endpoint_order)
            length += 1
        lengths.append(length)
    return tuple(sorted(lengths))


def _endpoint_type_data() -> dict[tuple[int, ...], tuple[int, tuple[int, ...]]]:
    result: dict[tuple[int, ...], tuple[int, tuple[int, ...]]] = {}
    for endpoint_order in _ENDPOINT_PERMUTATIONS:
        endpoint_type = _endpoint_cycle_type(endpoint_order)
        cycles = _label_cycle_lengths(endpoint_order)
        if endpoint_type in result:
            weight, previous = result[endpoint_type]
            assert previous == cycles
            result[endpoint_type] = weight + 1, cycles
        else:
            result[endpoint_type] = 1, cycles
    return result


def _fixed_count_from_cycles(cycles: tuple[int, ...], dimension: int) -> int:
    coefficients = [1] + [0] * dimension
    for cycle_length in cycles:
        next_coefficients = [0] * (dimension + 1)
        for total, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, dimension - total + 1, cycle_length):
                next_coefficients[total + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[dimension]


def _ordered_sextuple_class_count(dimension: int) -> int:
    return comb(dimension + _PATTERN_COUNT - 1, _PATTERN_COUNT - 1)


def _unordered_sextuple_class_count(dimension: int) -> int:
    numerator = sum(
        weight * _fixed_count_from_cycles(cycles, dimension)
        for weight, cycles in _endpoint_type_data().values()
    )
    assert numerator % _S6_ORDER == 0
    return numerator // _S6_ORDER


def _endpoint_symbol_maps() -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(
            _permuted_symbol(symbol, order)
            for symbol in range(_PATTERN_COUNT)
        )
        for order in _ENDPOINT_PERMUTATIONS
    )


def _canonical_label_multiset(
    labels: tuple[int, ...],
    symbol_maps: tuple[tuple[int, ...], ...],
) -> tuple[int, ...]:
    return min(
        tuple(sorted(symbol_map[label] for label in labels))
        for symbol_map in symbol_maps
    )


def _endpoint_orbit_size(
    labels: tuple[int, ...],
    symbol_maps: tuple[tuple[int, ...], ...],
) -> int:
    return len({
        tuple(sorted(symbol_map[label] for label in labels))
        for symbol_map in symbol_maps
    })


def _coordinate_orbit_size(labels: tuple[int, ...]) -> int:
    multiplicities = Counter(labels)
    result = factorial(len(labels))
    for count in multiplicities.values():
        result //= factorial(count)
    return result


def _local_multiplicity(accumulator: int, target: int) -> int:
    return sum(
        _INDEPENDENT_CRAZY_TRIT[data][accumulator] == target
        for data in range(_RADIX)
    )


def _ambiguity_dimension(
    accumulator: int,
    target: int,
    trit_count: int,
) -> int | None:
    dimension = 0
    for _ in range(trit_count):
        multiplicity = _local_multiplicity(
            accumulator % _RADIX,
            target % _RADIX,
        )
        if multiplicity == 0:
            return None
        dimension += multiplicity == _AMBIGUOUS_MULTIPLICITY
        accumulator //= _RADIX
        target //= _RADIX
    return dimension


def _independent_width_histogram(trit_count: int) -> Counter[int]:
    domain = _integer_power(_RADIX, trit_count)
    observed: Counter[int] = Counter()
    for accumulator in range(domain):
        for target in range(domain):
            dimension = _ambiguity_dimension(accumulator, target, trit_count)
            if dimension is not None:
                observed[dimension] += 1
    return observed


def test_s6_endpoint_cycle_types_induce_exact_label_cycles() -> None:
    """All eleven S6 conjugacy classes induce one exact label-cycle type."""
    data = _endpoint_type_data()
    expected: dict[tuple[int, ...], tuple[int, Counter[int]]] = {
        (1, 1, 1, 1, 1, 1): (1, Counter({1: 64})),
        (1, 1, 1, 1, 2): (15, Counter({1: 32, 2: 16})),
        (1, 1, 1, 3): (40, Counter({1: 16, 3: 16})),
        (1, 1, 2, 2): (45, Counter({1: 16, 2: 24})),
        (1, 1, 4): (90, Counter({1: 8, 2: 4, 4: 12})),
        (1, 2, 3): (120, Counter({1: 8, 2: 4, 3: 8, 6: 4})),
        (1, 5): (144, Counter({1: 4, 5: 12})),
        (2, 2, 2): (15, Counter({1: 8, 2: 28})),
        (2, 4): (90, Counter({1: 4, 2: 6, 4: 12})),
        (3, 3): (40, Counter({1: 4, 3: 20})),
        (6,): (120, Counter({1: 2, 2: 1, 3: 2, 6: 9})),
    }
    assert len(data) == len(expected)
    for endpoint_type, (weight, cycles) in data.items():
        expected_weight, expected_cycles = expected[endpoint_type]
        assert weight == expected_weight
        assert Counter(cycles) == expected_cycles
    assert sum(weight for weight, _ in data.values()) == _S6_ORDER


def test_ordered_sextuple_joint_counts_cover_through_dimension_fourteen(
) -> None:
    """The identity fixed count equals the ordered joint-count quotient."""
    identity_cycles = _endpoint_type_data()[1, 1, 1, 1, 1, 1][1]
    for dimension in range(_MAXIMUM_TRITS + 1):
        assert _fixed_count_from_cycles(
            identity_cycles, dimension
        ) == _ordered_sextuple_class_count(dimension)


def test_unordered_sextuple_orbits_are_exact_through_dimension_two() -> None:
    """Coordinate multisets collapse exactly under endpoint permutation."""
    symbol_maps = _endpoint_symbol_maps()
    for dimension in range(_EXHAUSTIVE_DIMENSION + 1):
        observed: set[tuple[int, ...]] = set()
        raw_mass = 0
        for labels in combinations_with_replacement(
            range(_PATTERN_COUNT),
            dimension,
        ):
            canonical = _canonical_label_multiset(labels, symbol_maps)
            if canonical in observed:
                continue
            observed.add(canonical)
            raw_mass += _coordinate_orbit_size(labels) * _endpoint_orbit_size(
                labels, symbol_maps
            )
        assert len(observed) == _unordered_sextuple_class_count(dimension)
        assert raw_mass == _integer_power(_PATTERN_COUNT, dimension)


def test_unordered_sextuple_burnside_counts_through_dimension_fourteen(
) -> None:
    """S6 Burnside arithmetic remains integral through the admitted bound."""
    data = _endpoint_type_data()
    for dimension in range(_MAXIMUM_TRITS + 1):
        assert 1 <= _unordered_sextuple_class_count(
            dimension
        ) <= _ordered_sextuple_class_count(dimension)
    fixed = tuple(
        _fixed_count_from_cycles(cycles, _MAXIMUM_TRITS)
        for _, cycles in data.values()
    )
    assert sorted(fixed) == sorted(_WIDTH_FOURTEEN_FIXED_COUNTS)
    assert _unordered_sextuple_class_count(
        _MAXIMUM_TRITS
    ) == _WIDTH_FOURTEEN_COUNT


def test_sextuple_quotients_lift_to_small_reachable_pairs() -> None:
    """Small reachable pairs inherit both sextuple quotient class counts."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        observed = _independent_width_histogram(trit_count)
        expected = Counter({
            dimension: comb(trit_count, dimension)
            * _integer_power(2, dimension)
            * _integer_power(5, trit_count - dimension)
            for dimension in range(trit_count + 1)
        })
        assert observed == expected
        assert all(
            _unordered_sextuple_class_count(dimension)
            <= _ordered_sextuple_class_count(dimension)
            for dimension in observed
        )
