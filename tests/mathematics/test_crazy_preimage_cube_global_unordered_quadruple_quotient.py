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
#   - Independent aggregate accounting for endpoint-unordered quadruple
#     quotients.
# - Must-Not:
#   - Convert representative-count reductions into wall-clock speedup claims.
# - Allows:
#   - Inputs: reachable fixed-pair ambiguity classes through width fourteen.
#   - Outputs: exact raw and endpoint-unordered quadruple case counts.
#   - Side effects: none.
# - Split-When:
#   - Tuple arity or the endpoint symmetry group changes.
# - Merge-When:
#   - Global accounting owns the same fixed-pair unordered-quadruple quotient
#     sum.
# - Summary:
#   - Sum endpoint-unordered quadruple classes over reachable fixed pairs.
# - Description:
#   - Enumerates small pair classes and checks transformed Burnside series.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Independent fixed-pair enumeration stops at width three; arithmetic at 14.
#

"""Evidence for global endpoint-unordered cube-quadruple quotient counts."""

from __future__ import annotations

from math import comb

_AMBIGUOUS_MULTIPLICITY = 2
_EXHAUSTIVE_TRITS = 3
_MAXIMUM_TRITS = 14
_QUADRATIC_DEGREE = 2
_RADIX = 3
_RAW_GLOBAL_LOCAL_MASS = 37
_S4_ORDER = 24
_WIDTH_FOURTEEN_COUNT = 1_409_733_897_288_413
_WIDTH_FOURTEEN_FIXED_COUNTS = (
    25_678_405_217_633_865,
    1_182_834_266_824_809,
    180_742_210_147_993,
    57_110_313_884_289,
    9_848_929_136_817,
)
_INDEPENDENT_CRAZY_TRIT = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)
_ENDPOINT_CLASS_WEIGHTS = (1, 6, 3, 8, 6)
_LOCAL_LABEL_CYCLES = (
    (1,) * 16,
    (1,) * 8 + (2,) * 4,
    (1,) * 4 + (2,) * 6,
    (1,) * 4 + (3,) * 4,
    (1,) * 2 + (2,) + (4,) * 3,
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


def _local_fixed_counts(dimension: int) -> tuple[int, int, int, int, int]:
    values = tuple(
        _fixed_count_from_cycles(cycles, dimension)
        for cycles in _LOCAL_LABEL_CYCLES
    )
    return values[0], values[1], values[2], values[3], values[4]


def _unordered_quadruple_classes(dimension: int) -> int:
    numerator = sum(
        weight * fixed
        for weight, fixed in zip(
            _ENDPOINT_CLASS_WEIGHTS,
            _local_fixed_counts(dimension),
            strict=True,
        )
    )
    assert numerator % _S4_ORDER == 0
    return numerator // _S4_ORDER


def _direct_global_fixed_counts(
    trit_count: int,
) -> tuple[int, int, int, int, int]:
    totals = [0] * len(_ENDPOINT_CLASS_WEIGHTS)
    for dimension in range(trit_count + 1):
        pair_count = _fixed_pair_class_count(trit_count, dimension)
        for index, fixed in enumerate(_local_fixed_counts(dimension)):
            totals[index] += pair_count * fixed
    return totals[0], totals[1], totals[2], totals[3], totals[4]


def _direct_global_count(trit_count: int) -> int:
    fixed = _direct_global_fixed_counts(trit_count)
    numerator = sum(
        weight * count
        for weight, count in zip(_ENDPOINT_CLASS_WEIGHTS, fixed, strict=True)
    )
    assert numerator % _S4_ORDER == 0
    return numerator // _S4_ORDER


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
    padded = base + [0] * (degree + 1 - len(base))
    for _ in range(exponent):
        result = _series_product(result, padded, degree)
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


def _inverse_quadratic_power(
    linear: int,
    quadratic: int,
    *,
    exponent: int,
    degree: int,
) -> list[int]:
    inverse = [0] * (degree + 1)
    inverse[0] = 1
    for index in range(1, degree + 1):
        inverse[index] = linear * inverse[index - 1]
        if index >= _QUADRATIC_DEGREE:
            inverse[index] -= quadratic * inverse[index - _QUADRATIC_DEGREE]
    result = [1] + [0] * degree
    for _ in range(exponent):
        result = _series_product(result, inverse, degree)
    return result


def _coefficient_with_numerator(
    denominator_series: list[int],
    degree: int,
) -> int:
    numerator = _polynomial_power([1, -5], 15, degree)
    return _series_product(numerator, denominator_series, degree)[degree]


def _identity_global_fixed_count(trit_count: int) -> int:
    series = _inverse_linear_power(7, 16, trit_count)
    return _coefficient_with_numerator(series, trit_count)


def _transposition_global_fixed_count(trit_count: int) -> int:
    series = _series_product(
        _inverse_linear_power(7, 12, trit_count),
        _inverse_linear_power(3, 4, trit_count),
        trit_count,
    )
    return _coefficient_with_numerator(series, trit_count)


def _double_transposition_global_fixed_count(trit_count: int) -> int:
    series = _series_product(
        _inverse_linear_power(7, 10, trit_count),
        _inverse_linear_power(3, 6, trit_count),
        trit_count,
    )
    return _coefficient_with_numerator(series, trit_count)


def _three_cycle_global_fixed_count(trit_count: int) -> int:
    series = _series_product(
        _inverse_linear_power(7, 8, trit_count),
        _inverse_quadratic_power(8, 19, exponent=4, degree=trit_count),
        trit_count,
    )
    return _coefficient_with_numerator(series, trit_count)


def _four_cycle_global_fixed_count(trit_count: int) -> int:
    linear = _series_product(
        _inverse_linear_power(7, 6, trit_count),
        _inverse_linear_power(3, 4, trit_count),
        trit_count,
    )
    series = _series_product(
        linear,
        _inverse_quadratic_power(10, 29, exponent=3, degree=trit_count),
        trit_count,
    )
    return _coefficient_with_numerator(series, trit_count)


def _closed_global_fixed_counts(
    trit_count: int,
) -> tuple[int, int, int, int, int]:
    return (
        _identity_global_fixed_count(trit_count),
        _transposition_global_fixed_count(trit_count),
        _double_transposition_global_fixed_count(trit_count),
        _three_cycle_global_fixed_count(trit_count),
        _four_cycle_global_fixed_count(trit_count),
    )


def _closed_global_count(trit_count: int) -> int:
    fixed = _closed_global_fixed_counts(trit_count)
    numerator = sum(
        weight * count
        for weight, count in zip(_ENDPOINT_CLASS_WEIGHTS, fixed, strict=True)
    )
    assert numerator % _S4_ORDER == 0
    return numerator // _S4_ORDER


def _independent_width_count(trit_count: int) -> int:
    domain = _integer_power(_RADIX, trit_count)
    canonical = 0
    for accumulator in range(domain):
        for target in range(domain):
            dimension = _ambiguity_dimension(accumulator, target, trit_count)
            if dimension is not None:
                canonical += _unordered_quadruple_classes(dimension)
    return canonical


def test_small_widths_match_independent_fixed_pair_enumeration() -> None:
    """Small reachable pairs sum to exact unordered-quadruple counts."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        assert _independent_width_count(trit_count) == _direct_global_count(
            trit_count
        )


def test_global_unordered_quadruple_quotient_has_exact_closed_count() -> None:
    """Burnside sums equal independent transformed generating functions."""
    for trit_count in range(1, _MAXIMUM_TRITS + 1):
        assert _direct_global_fixed_counts(
            trit_count
        ) == _closed_global_fixed_counts(trit_count)
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
