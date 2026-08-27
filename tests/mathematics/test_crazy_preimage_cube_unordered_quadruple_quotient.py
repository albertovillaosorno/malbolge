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
#   - Independent evidence for crazy preimage-cube quadruple orbits under
#     shared coordinate permutation and quadruple-endpoint permutation.
# - Must-Not:
#   - Apply endpoint-permutation equivalence to direction-sensitive analyses.
# - Allows:
#   - Inputs: reachable fixed accumulator/target pairs through width fourteen.
#   - Outputs: exact endpoint-unordered quadruple classes and representatives.
#   - Side effects: none.
# - Split-When:
#   - A larger tuple arity or a different endpoint symmetry group is required.
# - Merge-When:
#   - Another proof owns the same simultaneous S_k coordinate and S_4 endpoint
#     action on cube-word quadruples.
# - Summary:
#   - Quotient coordinate-symmetric quadruples further by endpoint permutation.
# - Description:
#   - Exhausts small quadruples and checks the bounded Burnside count exactly.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Raw quadruple enumeration stops at dimension three; Burnside arithmetic
#     reaches 14; fixed-pair lifting stops at width three.
#

"""Evidence for endpoint-unordered crazy preimage-cube quadruple quotients."""

from __future__ import annotations

from collections import Counter
from itertools import permutations
from itertools import product
from math import comb
from typing import cast

_BINARY_RADIX = 2
_EXHAUSTIVE_DIMENSION = 3
_EXHAUSTIVE_TRITS = 3
_MAXIMUM_TRITS = 14
_RADIX = 3
_QUADRUPLE_ARITY = 4
_PATTERN_COUNT = 1 << _QUADRUPLE_ARITY
_ENDPOINT_PERMUTATIONS = tuple(permutations(range(_QUADRUPLE_ARITY)))
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


def _integer_factorial(value: int) -> int:
    result = 1
    for factor in range(2, value + 1):
        result *= factor
    return result


def _tuple_symbol(
    codes: tuple[int, int, int, int],
    coordinate: int,
) -> int:
    result = 0
    for code in codes:
        result = (result << 1) | ((code >> coordinate) & 1)
    return result


def _tuple_counts(
    codes: tuple[int, int, int, int],
    dimension: int,
) -> tuple[int, ...]:
    counts = [0] * _PATTERN_COUNT
    for coordinate in range(dimension):
        counts[_tuple_symbol(codes, coordinate)] += 1
    return tuple(counts)


def _permuted_symbol(symbol: int, endpoint_order: tuple[int, ...]) -> int:
    bits = tuple(
        (symbol >> (_QUADRUPLE_ARITY - index - 1)) & 1
        for index in range(_QUADRUPLE_ARITY)
    )
    result = 0
    for source in endpoint_order:
        result = (result << 1) | bits[source]
    return result


def _permute_endpoint_counts(
    counts: tuple[int, ...],
    endpoint_order: tuple[int, ...],
) -> tuple[int, ...]:
    result = [0] * _PATTERN_COUNT
    for symbol, count in enumerate(counts):
        result[_permuted_symbol(symbol, endpoint_order)] = count
    return tuple(result)


def _canonical_counts(counts: tuple[int, ...]) -> tuple[int, ...]:
    return min(
        _permute_endpoint_counts(counts, endpoint_order)
        for endpoint_order in _ENDPOINT_PERMUTATIONS
    )


def _canonical_tuple(counts: tuple[int, ...]) -> tuple[int, int, int, int]:
    result = [0] * _QUADRUPLE_ARITY
    destination = 0
    for symbol in reversed(range(_PATTERN_COUNT)):
        for _ in range(counts[symbol]):
            for index in range(_QUADRUPLE_ARITY):
                shift = _QUADRUPLE_ARITY - index - 1
                result[index] |= ((symbol >> shift) & 1) << destination
            destination += 1
    return result[0], result[1], result[2], result[3]


def _canonicalize_quadruple(
    codes: tuple[int, int, int, int],
    dimension: int,
) -> tuple[tuple[int, int, int, int], tuple[int, ...]]:
    counts = _canonical_counts(_tuple_counts(codes, dimension))
    return _canonical_tuple(counts), counts


def _coordinate_orbit_size(counts: tuple[int, ...]) -> int:
    result = _integer_factorial(sum(counts))
    for count in counts:
        result //= _integer_factorial(count)
    return result


def _endpoint_orbit_size(counts: tuple[int, ...]) -> int:
    return len({
        _permute_endpoint_counts(counts, endpoint_order)
        for endpoint_order in _ENDPOINT_PERMUTATIONS
    })


def _combined_orbit_size(counts: tuple[int, ...]) -> int:
    return _coordinate_orbit_size(counts) * _endpoint_orbit_size(counts)


def _label_cycle_lengths(endpoint_order: tuple[int, ...]) -> tuple[int, ...]:
    unseen = set(range(_PATTERN_COUNT))
    lengths: list[int] = []
    while unseen:
        start = min(unseen)
        current = start
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


type _EndpointCycleType = (
    tuple[int]
    | tuple[int, int]
    | tuple[int, int, int]
    | tuple[int, int, int, int]
)


def _endpoint_cycle_type(
    endpoint_order: tuple[int, ...],
) -> _EndpointCycleType:
    unseen = set(range(_QUADRUPLE_ARITY))
    lengths: list[int] = []
    while unseen:
        start = min(unseen)
        current = start
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = endpoint_order[current]
            length += 1
        lengths.append(length)
    ordered = tuple(sorted(lengths))
    assert sum(ordered) == _QUADRUPLE_ARITY
    return cast("_EndpointCycleType", ordered)


def _fixed_counts_by_endpoint_type(
    dimension: int,
) -> dict[tuple[int, ...], int]:
    result: dict[tuple[int, ...], int] = {}
    for endpoint_order in _ENDPOINT_PERMUTATIONS:
        endpoint_type = _endpoint_cycle_type(endpoint_order)
        fixed_count = _fixed_count_from_cycles(
            _label_cycle_lengths(endpoint_order),
            dimension,
        )
        previous = result.setdefault(endpoint_type, fixed_count)
        assert previous == fixed_count
    return result


def _unordered_quadruple_class_count(dimension: int) -> int:
    fixed = _fixed_counts_by_endpoint_type(dimension)
    numerator = (
        fixed[1, 1, 1, 1]
        + 6 * fixed[1, 1, 2]
        + 3 * fixed[2, 2]
        + 8 * fixed[1, 3]
        + 6 * fixed[4,]
    )
    return numerator // 24


def _local_preimages(accumulator: int, target: int) -> tuple[int, ...]:
    return tuple(
        data
        for data in range(_RADIX)
        if _INDEPENDENT_CRAZY_TRIT[data][accumulator] == target
    )


def _choice_sets(
    target: int,
    accumulator: int,
    trit_count: int,
) -> tuple[tuple[int, ...], ...]:
    choices: list[tuple[int, ...]] = []
    for _ in range(trit_count):
        choices.append(_local_preimages(accumulator % _RADIX, target % _RADIX))
        target //= _RADIX
        accumulator //= _RADIX
    return tuple(choices)


def _cube_data(
    choices: tuple[tuple[int, ...], ...],
    cube_code: int,
) -> int:
    data = 0
    place = 1
    bit_position = 0
    for local in choices:
        if not local:
            raise ValueError
        if len(local) == 1:
            data_trit = local[0]
        else:
            data_trit = local[(cube_code >> bit_position) & 1]
            bit_position += 1
        data += data_trit * place
        place *= _RADIX
    return data


def _crazy(data: int, accumulator: int, trit_count: int) -> int:
    target = 0
    place = 1
    for _ in range(trit_count):
        target += (
            _INDEPENDENT_CRAZY_TRIT[data % _RADIX][accumulator % _RADIX] * place
        )
        data //= _RADIX
        accumulator //= _RADIX
        place *= _RADIX
    return target


def test_s4_endpoint_cycle_types_induce_exact_label_cycles() -> None:
    """All five endpoint conjugacy classes have the expected label cycles."""
    expected = {
        (1, 1, 1, 1): (1,) * 16,
        (1, 1, 2): (1,) * 8 + (2,) * 4,
        (2, 2): (1,) * 4 + (2,) * 6,
        (1, 3): (1,) * 4 + (3,) * 4,
        (4,): (1,) * 2 + (2,) + (4,) * 3,
    }
    observed = Counter(
        _endpoint_cycle_type(endpoint_order)
        for endpoint_order in _ENDPOINT_PERMUTATIONS
    )
    assert observed == Counter({
        (1, 1, 1, 1): 1,
        (1, 1, 2): 6,
        (2, 2): 3,
        (1, 3): 8,
        (4,): 6,
    })
    for endpoint_order in _ENDPOINT_PERMUTATIONS:
        assert _label_cycle_lengths(endpoint_order) == expected[
            _endpoint_cycle_type(endpoint_order)
        ]


def test_unordered_quadruple_orbits_are_exact_through_dimension_three() -> None:
    """Small quadruples collapse exactly under both permutation actions."""
    for dimension in range(_EXHAUSTIVE_DIMENSION + 1):
        size = _integer_power(_BINARY_RADIX, dimension)
        observed: Counter[tuple[int, ...]] = Counter()
        representatives: set[tuple[int, int, int, int]] = set()
        for codes in product(range(size), repeat=_QUADRUPLE_ARITY):
            quadruple = codes[0], codes[1], codes[2], codes[3]
            canonical, counts = _canonicalize_quadruple(quadruple, dimension)
            observed[counts] += 1
            representatives.add(canonical)
        assert all(
            mass == _combined_orbit_size(counts)
            for counts, mass in observed.items()
        )
        assert len(representatives) == _unordered_quadruple_class_count(
            dimension
        )
        assert sum(observed.values()) == _integer_power(
            _PATTERN_COUNT,
            dimension,
        )


def test_unordered_quadruple_burnside_counts_through_dimension_fourteen(
) -> None:
    """S4 Burnside arithmetic gives integral exact class counts through Q14."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        fixed = _fixed_counts_by_endpoint_type(dimension)
        assert fixed[1, 1, 1, 1] == comb(dimension + 15, 15)
        numerator = (
            fixed[1, 1, 1, 1]
            + 6 * fixed[1, 1, 2]
            + 3 * fixed[2, 2]
            + 8 * fixed[1, 3]
            + 6 * fixed[4,]
        )
        assert numerator % 24 == 0
        assert numerator // 24 == _unordered_quadruple_class_count(dimension)


def _check_fixed_pair_lifting(
    target: int,
    accumulator: int,
    trit_count: int,
) -> None:
    choices = _choice_sets(target, accumulator, trit_count)
    if any(not local for local in choices):
        return
    dimension = sum(len(local) == _BINARY_RADIX for local in choices)
    words = tuple(_cube_data(choices, code) for code in range(1 << dimension))
    assert all(
        _crazy(word, accumulator, trit_count) == target for word in words
    )
    representatives: set[tuple[int, int, int, int]] = set()
    for codes in product(range(1 << dimension), repeat=_QUADRUPLE_ARITY):
        quadruple = codes[0], codes[1], codes[2], codes[3]
        canonical, _ = _canonicalize_quadruple(quadruple, dimension)
        representatives.add(canonical)
        assert all(
            _crazy(words[code], accumulator, trit_count) == target
            for code in canonical
        )
    assert len(representatives) == _unordered_quadruple_class_count(dimension)


def test_unordered_quadruple_quotient_lifts_to_small_reachable_pairs() -> None:
    """Canonical unordered quadruples remain valid fixed-pair preimages."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        domain = _integer_power(_RADIX, trit_count)
        for accumulator in range(domain):
            for target in range(domain):
                _check_fixed_pair_lifting(target, accumulator, trit_count)
