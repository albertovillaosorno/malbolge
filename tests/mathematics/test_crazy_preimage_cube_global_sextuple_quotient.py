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
#   - Independent aggregate accounting for ordered and endpoint-unordered
#     sextuple quotients over reachable fixed pairs.
# - Must-Not:
#   - Convert representative-count reductions into wall-clock speedup claims.
# - Allows:
#   - Inputs: reachable fixed-pair ambiguity classes through width fourteen.
#   - Outputs: exact raw, ordered, and endpoint-unordered sextuple case counts.
#   - Side effects: none.
# - Split-When:
#   - Tuple arity or the endpoint symmetry group changes.
# - Merge-When:
#   - Global accounting owns the same sextuple quotient sums.
# - Summary:
#   - Sum ordered and endpoint-unordered sextuple classes over reachable pairs.
# - Description:
#   - Enumerates small pair classes and checks two independent closed forms.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Independent fixed-pair enumeration stops at width two; arithmetic at 14.
#

"""Evidence for global ordered and endpoint-unordered sextuple quotients."""

from __future__ import annotations

from math import comb

_AMBIGUOUS_MULTIPLICITY = 2
_ENDPOINT_CLASS_WEIGHTS = (1, 15, 40, 45, 90, 120, 144, 15, 90, 40, 120)
_EXHAUSTIVE_TRITS = 2
_MAXIMUM_TRITS = 14
_PATTERN_COUNT = 64
_RADIX = 3
_RAW_GLOBAL_LOCAL_MASS = 133
_S6_ORDER = 720
_WIDTH_FOURTEEN_ORDERED_COUNT = 1_584_315_319_509_725_541_225
_WIDTH_FOURTEEN_UNORDERED_COUNT = 2_361_488_883_978_006_005
_WIDTH_FOURTEEN_FIXED_COUNTS = (
    1_584_315_319_509_725_541_225,
    7_054_158_423_775_528_425,
    38_878_022_703_262_281,
    175_942_582_684_950_825,
    1_460_917_013_254_953,
    1_806_087_636_205_929,
    43_767_572_733_825,
    18_851_333_161_147_209,
    256_827_625_272_665,
    244_844_111_940_225,
    13_080_355_599_105,
)
_LABEL_CYCLE_TYPES = (
    (1,) * 64,
    (1,) * 32 + (2,) * 16,
    (1,) * 16 + (3,) * 16,
    (1,) * 16 + (2,) * 24,
    (1,) * 8 + (2,) * 4 + (4,) * 12,
    (1,) * 8 + (2,) * 4 + (3,) * 8 + (6,) * 4,
    (1,) * 4 + (5,) * 12,
    (1,) * 8 + (2,) * 28,
    (1,) * 4 + (2,) * 6 + (4,) * 12,
    (1,) * 4 + (3,) * 20,
    (1,) * 2 + (2,) + (3,) * 2 + (6,) * 9,
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


def _ordered_sextuple_classes(dimension: int) -> int:
    return comb(dimension + _PATTERN_COUNT - 1, _PATTERN_COUNT - 1)


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


def _unordered_sextuple_classes(dimension: int) -> int:
    numerator = sum(
        weight * _fixed_count_from_cycles(cycles, dimension)
        for weight, cycles in zip(
            _ENDPOINT_CLASS_WEIGHTS,
            _LABEL_CYCLE_TYPES,
            strict=True,
        )
    )
    assert numerator % _S6_ORDER == 0
    return numerator // _S6_ORDER


def _direct_global_counts(trit_count: int) -> tuple[int, int, int]:
    raw = 0
    ordered = 0
    unordered = 0
    for dimension in range(trit_count + 1):
        pair_count = _fixed_pair_class_count(trit_count, dimension)
        raw += pair_count * _integer_power(_PATTERN_COUNT, dimension)
        ordered += pair_count * _ordered_sextuple_classes(dimension)
        unordered += pair_count * _unordered_sextuple_classes(dimension)
    return raw, ordered, unordered


def _closed_ordered_count(trit_count: int) -> int:
    separators = _PATTERN_COUNT - 1
    return sum(
        comb(separators, degree)
        * comb(trit_count, degree)
        * _integer_power(2, degree)
        * _integer_power(7, trit_count - degree)
        for degree in range(min(separators, trit_count) + 1)
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
    return sum(
        value * inverse[trit_count - degree]
        for degree, value in enumerate(numerator)
    )


def _closed_global_fixed_counts(trit_count: int) -> tuple[int, ...]:
    return tuple(
        _global_fixed_count_from_transform(cycles, trit_count)
        for cycles in _LABEL_CYCLE_TYPES
    )


def _closed_unordered_count(trit_count: int) -> int:
    fixed = _closed_global_fixed_counts(trit_count)
    numerator = sum(
        weight * count
        for weight, count in zip(_ENDPOINT_CLASS_WEIGHTS, fixed, strict=True)
    )
    assert numerator % _S6_ORDER == 0
    return numerator // _S6_ORDER


def _independent_width_counts(trit_count: int) -> tuple[int, int, int]:
    domain = _integer_power(_RADIX, trit_count)
    raw = 0
    ordered = 0
    unordered = 0
    for accumulator in range(domain):
        for target in range(domain):
            dimension = _ambiguity_dimension(accumulator, target, trit_count)
            if dimension is None:
                continue
            raw += _integer_power(_PATTERN_COUNT, dimension)
            ordered += _ordered_sextuple_classes(dimension)
            unordered += _unordered_sextuple_classes(dimension)
    return raw, ordered, unordered


def test_small_widths_match_independent_fixed_pair_enumeration() -> None:
    """Small reachable pairs reproduce all three global sextuple counts."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        independent = _independent_width_counts(trit_count)
        direct = _direct_global_counts(trit_count)
        assert independent == direct
        assert direct[0] == _integer_power(_RAW_GLOBAL_LOCAL_MASS, trit_count)


def test_global_sextuple_quotients_have_exact_closed_counts() -> None:
    """Ordered and unordered direct sums match independent closed forms."""
    for trit_count in range(1, _MAXIMUM_TRITS + 1):
        raw, ordered, unordered = _direct_global_counts(trit_count)
        assert raw == _integer_power(_RAW_GLOBAL_LOCAL_MASS, trit_count)
        assert ordered == _closed_ordered_count(trit_count)
        assert unordered == _closed_unordered_count(trit_count)
        assert unordered <= ordered <= raw
    assert _closed_ordered_count(
        _MAXIMUM_TRITS
    ) == _WIDTH_FOURTEEN_ORDERED_COUNT
    assert _closed_unordered_count(
        _MAXIMUM_TRITS
    ) == _WIDTH_FOURTEEN_UNORDERED_COUNT
    assert _closed_global_fixed_counts(
        _MAXIMUM_TRITS
    ) == _WIDTH_FOURTEEN_FIXED_COUNTS
