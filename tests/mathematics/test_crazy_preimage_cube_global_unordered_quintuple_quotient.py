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
#   - Independent aggregate accounting for endpoint-unordered quintuple
#     quotients.
# - Must-Not:
#   - Convert representative-count reductions into wall-clock speedup claims.
# - Allows:
#   - Inputs: reachable fixed-pair ambiguity classes through width fourteen.
#   - Outputs: exact raw and endpoint-unordered quintuple case counts.
#   - Side effects: none.
# - Split-When:
#   - Tuple arity or the endpoint symmetry group changes.
# - Merge-When:
#   - Global accounting owns the same fixed-pair unordered-quintuple sum.
# - Summary:
#   - Sum endpoint-unordered quintuple classes over reachable fixed pairs.
# - Description:
#   - Enumerates small pair classes and checks transformed generating series.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Independent fixed-pair enumeration stops at width two; arithmetic at 14.
#

"""Evidence for global endpoint-unordered cube-quintuple quotient counts."""

from __future__ import annotations

from math import comb

_AMBIGUOUS_MULTIPLICITY = 2
_ENDPOINT_CLASS_WEIGHTS = (1, 10, 20, 15, 30, 20, 24)
_EXHAUSTIVE_TRITS = 2
_MAXIMUM_TRITS = 14
_PATTERN_COUNT = 32
_RADIX = 3
_RAW_GLOBAL_LOCAL_MASS = 69
_S5_ORDER = 120
_WIDTH_FOURTEEN_COUNT = 34_995_940_605_821_849
_WIDTH_FOURTEEN_FIXED_COUNTS = (
    3_571_359_808_057_227_945,
    54_779_621_914_531_305,
    955_501_620_651_033,
    3_768_908_530_569_225,
    84_481_568_466_345,
    101_628_460_149_705,
    6_090_369_480_725,
)
_LABEL_CYCLE_TYPES = (
    (1,) * 32,
    (1,) * 16 + (2,) * 8,
    (1,) * 8 + (3,) * 8,
    (1,) * 8 + (2,) * 12,
    (1,) * 4 + (2,) * 2 + (4,) * 6,
    (1,) * 4 + (2,) * 2 + (3,) * 4 + (6,) * 2,
    (1,) * 2 + (5,) * 6,
)
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


def _fixed_pair_class_count(trit_count: int, dimension: int) -> int:
    return (
        comb(trit_count, dimension)
        * _integer_power(2, dimension)
        * _integer_power(5, trit_count - dimension)
    )


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


def _unordered_quintuple_classes(dimension: int) -> int:
    numerator = sum(
        weight * _fixed_count_from_cycles(cycles, dimension)
        for weight, cycles in zip(
            _ENDPOINT_CLASS_WEIGHTS,
            _LABEL_CYCLE_TYPES,
            strict=True,
        )
    )
    assert numerator % _S5_ORDER == 0
    return numerator // _S5_ORDER


def _direct_global_count(trit_count: int) -> int:
    return sum(
        _fixed_pair_class_count(trit_count, dimension)
        * _unordered_quintuple_classes(dimension)
        for dimension in range(trit_count + 1)
    )


def _polynomial_product(left: list[int], right: list[int]) -> list[int]:
    result = [0] * (len(left) + len(right) - 1)
    for left_degree, left_value in enumerate(left):
        for right_degree, right_value in enumerate(right):
            result[left_degree + right_degree] += left_value * right_value
    return result


def _inverse_polynomial(polynomial: list[int], degree: int) -> list[int]:
    assert polynomial[0] == 1
    result = [0] * (degree + 1)
    result[0] = 1
    for index in range(1, degree + 1):
        result[index] = -sum(
            polynomial[offset] * result[index - offset]
            for offset in range(1, min(index, len(polynomial) - 1) + 1)
        )
    return result


def _cycle_transform_factor(cycle_length: int) -> list[int]:
    factor = [
        comb(cycle_length, degree) * _integer_power(-5, degree)
        for degree in range(cycle_length + 1)
    ]
    factor[cycle_length] -= _integer_power(2, cycle_length)
    return factor


def _global_fixed_count_from_transform(
    cycles: tuple[int, ...],
    trit_count: int,
) -> int:
    denominator = [1]
    for cycle_length in cycles:
        denominator = _polynomial_product(
            denominator,
            _cycle_transform_factor(cycle_length),
        )
    inverse = _inverse_polynomial(denominator, trit_count)
    numerator = [
        comb(_PATTERN_COUNT - 1, degree) * _integer_power(-5, degree)
        for degree in range(min(_PATTERN_COUNT - 1, trit_count) + 1)
    ]
    coefficient = 0
    for degree, value in enumerate(numerator):
        coefficient += value * inverse[trit_count - degree]
    return coefficient


def _closed_global_fixed_counts(trit_count: int) -> tuple[int, ...]:
    return tuple(
        _global_fixed_count_from_transform(cycles, trit_count)
        for cycles in _LABEL_CYCLE_TYPES
    )


def _closed_global_count(trit_count: int) -> int:
    fixed = _closed_global_fixed_counts(trit_count)
    numerator = sum(
        weight * count
        for weight, count in zip(_ENDPOINT_CLASS_WEIGHTS, fixed, strict=True)
    )
    assert numerator % _S5_ORDER == 0
    return numerator // _S5_ORDER


def _independent_width_count(trit_count: int) -> int:
    domain = _integer_power(_RADIX, trit_count)
    canonical = 0
    for accumulator in range(domain):
        for target in range(domain):
            dimension = _ambiguity_dimension(accumulator, target, trit_count)
            if dimension is not None:
                canonical += _unordered_quintuple_classes(dimension)
    return canonical


def test_small_widths_match_independent_fixed_pair_enumeration() -> None:
    """Small reachable pairs sum to the exact unordered-quintuple counts."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        assert _independent_width_count(trit_count) == _direct_global_count(
            trit_count
        )


def test_global_unordered_quintuple_quotient_has_exact_closed_count() -> None:
    """Burnside sums equal independent transformed generating functions."""
    for trit_count in range(1, _MAXIMUM_TRITS + 1):
        assert _direct_global_count(trit_count) == _closed_global_count(
            trit_count
        )
        assert _closed_global_count(trit_count) <= _integer_power(
            _RAW_GLOBAL_LOCAL_MASS,
            trit_count,
        )
    assert _closed_global_fixed_counts(
        _MAXIMUM_TRITS
    ) == _WIDTH_FOURTEEN_FIXED_COUNTS
    assert _closed_global_count(_MAXIMUM_TRITS) == _WIDTH_FOURTEEN_COUNT
