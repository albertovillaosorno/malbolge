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
#   - Independent aggregate accounting for endpoint-unordered triple quotients.
# - Must-Not:
#   - Convert representative-count reductions into wall-clock speedup claims.
# - Allows:
#   - Inputs: reachable fixed-pair ambiguity classes through width fourteen.
#   - Outputs: exact raw and endpoint-unordered triple case counts.
#   - Side effects: none.
# - Split-When:
#   - Tuple arity or the endpoint symmetry group changes.
# - Merge-When:
#   - Global accounting owns the same fixed-pair unordered-triple quotient sum.
# - Summary:
#   - Sum endpoint-unordered triple classes over reachable fixed pairs.
# - Description:
#   - Brute-forces small pair classes and checks Burnside generating functions.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Independent fixed-pair enumeration stops at width four; arithmetic at 14.
#

"""Evidence for global endpoint-unordered cube-triple quotient counts."""

from __future__ import annotations

from math import comb

_AMBIGUOUS_MULTIPLICITY = 2
_EXHAUSTIVE_TRITS = 4
_MAXIMUM_TRITS = 14
_RADIX = 3
_QUADRATIC_DEGREE = 2
_RAW_GLOBAL_LOCAL_MASS = 21
_WIDTH_FOURTEEN_COUNT = 124_279_218_052_677
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


def _transposition_fixed_classes(dimension: int) -> int:
    return sum(
        comb(dimension - 2 * pair_count + 3, 3) * (pair_count + 1)
        for pair_count in range(dimension // 2 + 1)
    )


def _three_cycle_fixed_classes(dimension: int) -> int:
    return sum(
        (dimension - 3 * cycle_count + 1) * (cycle_count + 1)
        for cycle_count in range(dimension // 3 + 1)
    )


def _unordered_triple_classes(dimension: int) -> int:
    numerator = (
        comb(dimension + 7, 7)
        + 3 * _transposition_fixed_classes(dimension)
        + 2 * _three_cycle_fixed_classes(dimension)
    )
    assert numerator % 6 == 0
    return numerator // 6


def _direct_global_count(trit_count: int) -> int:
    return sum(
        _fixed_pair_class_count(trit_count, dimension)
        * _unordered_triple_classes(dimension)
        for dimension in range(trit_count + 1)
    )


def _series_product(
    left: list[int],
    right: list[int],
    degree: int,
) -> list[int]:
    result = [0] * (degree + 1)
    for left_degree, left_value in enumerate(left):
        for right_degree, right_value in enumerate(right):
            total_degree = left_degree + right_degree
            if total_degree > degree:
                break
            result[total_degree] += left_value * right_value
    return result


def _polynomial_power(base: list[int], exponent: int, degree: int) -> list[int]:
    result = [1] + [0] * degree
    for _ in range(exponent):
        result = _series_product(result, base, degree)
    return result


def _inverse_linear_power(
    scale: int,
    exponent: int,
    degree: int,
) -> list[int]:
    return [
        comb(index + exponent - 1, exponent - 1)
        * _integer_power(scale, index)
        for index in range(degree + 1)
    ]


def _inverse_quadratic_squared(degree: int) -> list[int]:
    # Coefficients of (1 - 8x + 19x^2)^-2, built independently by recurrence.
    base = [0] * (degree + 1)
    base[0] = 1
    for index in range(1, degree + 1):
        base[index] = 8 * base[index - 1]
        if index >= _QUADRATIC_DEGREE:
            base[index] -= 19 * base[index - _QUADRATIC_DEGREE]
    return _series_product(base, base, degree)


def _coefficient_with_numerator(
    denominator_series: list[int],
    degree: int,
) -> int:
    numerator = _polynomial_power([1, -5], 7, degree)
    return _series_product(numerator, denominator_series, degree)[degree]


def _identity_global_fixed_count(trit_count: int) -> int:
    denominator = _inverse_linear_power(7, 8, trit_count)
    return _coefficient_with_numerator(denominator, trit_count)


def _transposition_global_fixed_count(trit_count: int) -> int:
    left = _inverse_linear_power(7, 6, trit_count)
    right = _inverse_linear_power(3, 2, trit_count)
    return _coefficient_with_numerator(
        _series_product(left, right, trit_count),
        trit_count,
    )


def _three_cycle_global_fixed_count(trit_count: int) -> int:
    left = _inverse_linear_power(7, 4, trit_count)
    right = _inverse_quadratic_squared(trit_count)
    return _coefficient_with_numerator(
        _series_product(left, right, trit_count),
        trit_count,
    )


def _closed_global_count(trit_count: int) -> int:
    numerator = (
        _identity_global_fixed_count(trit_count)
        + 3 * _transposition_global_fixed_count(trit_count)
        + 2 * _three_cycle_global_fixed_count(trit_count)
    )
    assert numerator % 6 == 0
    return numerator // 6


def _independent_width_count(trit_count: int) -> int:
    domain = _integer_power(_RADIX, trit_count)
    canonical = 0
    for accumulator in range(domain):
        for target in range(domain):
            dimension = _ambiguity_dimension(accumulator, target, trit_count)
            if dimension is None:
                continue
            canonical += _unordered_triple_classes(dimension)
    return canonical


def test_small_widths_match_independent_fixed_pair_enumeration() -> None:
    """Small reachable pairs sum to the exact unordered-triple counts."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        assert _independent_width_count(trit_count) == _direct_global_count(
            trit_count
        )


def test_global_unordered_triple_quotient_has_exact_closed_count() -> None:
    """Burnside sums equal independent transformed generating functions."""
    for trit_count in range(1, _MAXIMUM_TRITS + 1):
        assert _direct_global_count(
            trit_count
        ) == _closed_global_count(trit_count)
        assert _closed_global_count(trit_count) <= _integer_power(
            _RAW_GLOBAL_LOCAL_MASS,
            trit_count,
        )
    assert _closed_global_count(_MAXIMUM_TRITS) == _WIDTH_FOURTEEN_COUNT
