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
#   - Independent evidence for crazy preimage-cube quintuple orbits under
#     shared coordinate permutation and quintuple-endpoint permutation.
# - Must-Not:
#   - Apply endpoint-permutation equivalence to direction-sensitive analyses.
# - Allows:
#   - Inputs: reachable fixed accumulator/target pairs through width fourteen.
#   - Outputs: exact endpoint-unordered quintuple classes and representatives.
#   - Side effects: none.
# - Split-When:
#   - A larger tuple arity or a different endpoint symmetry group is required.
# - Merge-When:
#   - Another proof owns the same simultaneous S_k coordinate and S_5 endpoint
#     action on cube-word quintuples.
# - Summary:
#   - Quotient coordinate-symmetric quintuples further by endpoint permutation.
# - Description:
#   - Exhausts small quintuples and checks the bounded Burnside count exactly.
# - Usage:
#   - Prospective mathematical correspondence evidence.
# - Defaults:
#   - Raw quintuple enumeration stops at dimension two; Burnside arithmetic
#     reaches 14; fixed-pair lifting stops at width two.
#

"""Prospective evidence for endpoint-unordered cube-quintuple quotients."""

from __future__ import annotations

from collections import Counter
from itertools import permutations
from itertools import product
from math import comb
from math import factorial
from typing import cast

_AMBIGUOUS_MULTIPLICITY = 2
_ARITY = 5
_PATTERN_COUNT = 1 << _ARITY
_ENDPOINT_PERMUTATIONS = tuple(permutations(range(_ARITY)))
_EXHAUSTIVE_DIMENSION = 2
_EXHAUSTIVE_TRITS = 2
_MAXIMUM_TRITS = 14
_WIDTH_FOURTEEN_COUNT = 1_426_354_541
_RADIX = 3
_INDEPENDENT_CRAZY_TRIT = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)

type _EndpointCycleType = (
    tuple[int]
    | tuple[int, int]
    | tuple[int, int, int]
    | tuple[int, int, int, int]
    | tuple[int, int, int, int, int]
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


def _endpoint_cycle_type(endpoint_order: tuple[int, ...]) -> _EndpointCycleType:
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
    ordered = tuple(sorted(lengths))
    assert sum(ordered) == _ARITY
    return cast("_EndpointCycleType", ordered)


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


def _endpoint_type_data(
) -> dict[_EndpointCycleType, tuple[int, tuple[int, ...]]]:
    result: dict[_EndpointCycleType, tuple[int, tuple[int, ...]]] = {}
    for endpoint_order in _ENDPOINT_PERMUTATIONS:
        endpoint_type = _endpoint_cycle_type(endpoint_order)
        cycles = _label_cycle_lengths(endpoint_order)
        if endpoint_type in result:
            count, previous = result[endpoint_type]
            assert previous == cycles
            result[endpoint_type] = count + 1, cycles
        else:
            result[endpoint_type] = 1, cycles
    return result


def _unordered_quintuple_class_count(dimension: int) -> int:
    numerator = sum(
        weight * _fixed_count_from_cycles(cycles, dimension)
        for weight, cycles in _endpoint_type_data().values()
    )
    assert numerator % factorial(_ARITY) == 0
    return numerator // factorial(_ARITY)


def _tuple_counts(
    codes: tuple[int, int, int, int, int],
    dimension: int,
) -> tuple[int, ...]:
    counts = [0] * _PATTERN_COUNT
    for coordinate in range(dimension):
        symbol = 0
        for code in codes:
            symbol = (symbol << 1) | ((code >> coordinate) & 1)
        counts[symbol] += 1
    return tuple(counts)


def _permute_counts(
    counts: tuple[int, ...], endpoint_order: tuple[int, ...]
) -> tuple[int, ...]:
    result = [0] * _PATTERN_COUNT
    for symbol, count in enumerate(counts):
        result[_permuted_symbol(symbol, endpoint_order)] = count
    return tuple(result)


def _canonical_counts(counts: tuple[int, ...]) -> tuple[int, ...]:
    return min(
        _permute_counts(counts, endpoint_order)
        for endpoint_order in _ENDPOINT_PERMUTATIONS
    )


def _coordinate_orbit_size(counts: tuple[int, ...]) -> int:
    result = factorial(sum(counts))
    for count in counts:
        result //= factorial(count)
    return result


def _endpoint_orbit_size(counts: tuple[int, ...]) -> int:
    return len({
        _permute_counts(counts, endpoint_order)
        for endpoint_order in _ENDPOINT_PERMUTATIONS
    })


def _local_preimages(accumulator: int, target: int) -> tuple[int, ...]:
    return tuple(
        data
        for data in range(_RADIX)
        if _INDEPENDENT_CRAZY_TRIT[data][accumulator] == target
    )


def _ambiguity_dimension(
    accumulator: int,
    target: int,
    trit_count: int,
) -> int | None:
    dimension = 0
    for _ in range(trit_count):
        multiplicity = len(
            _local_preimages(accumulator % _RADIX, target % _RADIX)
        )
        if multiplicity == 0:
            return None
        dimension += multiplicity == _AMBIGUOUS_MULTIPLICITY
        accumulator //= _RADIX
        target //= _RADIX
    return dimension


def test_s5_endpoint_cycle_types_induce_exact_label_cycles() -> None:
    """Each S5 conjugacy class has one induced label cycle type."""
    data = _endpoint_type_data()
    assert sum(weight for weight, _ in data.values()) == factorial(_ARITY)
    observed = Counter({kind: weight for kind, (weight, _) in data.items()})
    assert observed == Counter({
        (1, 1, 1, 1, 1): 1,
        (1, 1, 1, 2): 10,
        (1, 1, 3): 20,
        (1, 2, 2): 15,
        (1, 4): 30,
        (2, 3): 20,
        (5,): 24,
    })
    expected = {
        (1, 1, 1, 1, 1): Counter({1: 32}),
        (1, 1, 1, 2): Counter({1: 16, 2: 8}),
        (1, 1, 3): Counter({1: 8, 3: 8}),
        (1, 2, 2): Counter({1: 8, 2: 12}),
        (1, 4): Counter({1: 4, 2: 2, 4: 6}),
        (2, 3): Counter({1: 4, 2: 2, 3: 4, 6: 2}),
        (5,): Counter({1: 2, 5: 6}),
    }
    for kind, (_, cycles) in data.items():
        assert Counter(cycles) == expected[kind]


def test_unordered_quintuple_orbits_are_exact_through_dimension_two() -> None:
    """Small quintuples collapse exactly under both permutation actions."""
    for dimension in range(_EXHAUSTIVE_DIMENSION + 1):
        size = _integer_power(2, dimension)
        observed: Counter[tuple[int, ...]] = Counter()
        for codes in product(range(size), repeat=_ARITY):
            quintuple = codes[0], codes[1], codes[2], codes[3], codes[4]
            counts = _canonical_counts(_tuple_counts(quintuple, dimension))
            observed[counts] += 1
        assert len(observed) == _unordered_quintuple_class_count(dimension)
        assert sum(observed.values()) == _integer_power(
            _PATTERN_COUNT, dimension
        )
        assert all(
            mass
            == _coordinate_orbit_size(counts) * _endpoint_orbit_size(counts)
            for counts, mass in observed.items()
        )


def test_unordered_quintuple_burnside_counts_through_dimension_fourteen(
) -> None:
    """S5 Burnside arithmetic remains integral through the admitted bound."""
    data = _endpoint_type_data()
    for dimension in range(_MAXIMUM_TRITS + 1):
        identity_cycles = data[1, 1, 1, 1, 1][1]
        assert _fixed_count_from_cycles(identity_cycles, dimension) == comb(
            dimension + 31, 31
        )
        assert 1 <= _unordered_quintuple_class_count(dimension) <= comb(
            dimension + 31, 31
        )
    assert (
        _unordered_quintuple_class_count(_MAXIMUM_TRITS)
        == _WIDTH_FOURTEEN_COUNT
    )


def _independent_width_histogram(trit_count: int) -> Counter[int]:
    domain = _integer_power(_RADIX, trit_count)
    observed: Counter[int] = Counter()
    for accumulator in range(domain):
        for target in range(domain):
            dimension = _ambiguity_dimension(accumulator, target, trit_count)
            if dimension is not None:
                observed[dimension] += 1
    return observed


def test_unordered_quintuple_quotient_lifts_to_small_reachable_pairs() -> None:
    """Small reachable pairs inherit their cube-dimension class count."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        observed = _independent_width_histogram(trit_count)
        expected = Counter({
            dimension: comb(trit_count, dimension)
            * _integer_power(2, dimension)
            * _integer_power(5, trit_count - dimension)
            for dimension in range(trit_count + 1)
        })
        assert observed == expected
        assert sum(
            multiplicity * _unordered_quintuple_class_count(dimension)
            for dimension, multiplicity in observed.items()
        ) > 0
