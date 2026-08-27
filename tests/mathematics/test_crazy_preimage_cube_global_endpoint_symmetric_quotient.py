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
#   - Independent aggregate accounting for endpoint-symmetric pair quotients.
# - Must-Not:
#   - Apply endpoint-swap equivalence to direction-sensitive analyses.
# - Allows:
#   - Inputs: reachable fixed-pair ambiguity classes through width fourteen.
#   - Outputs: exact raw and canonical endpoint-symmetric ordered-pair counts.
#   - Side effects: none.
# - Split-When:
#   - A larger pair-symmetry group needs a distinct aggregate classification.
# - Merge-When:
#   - Global accounting owns the same coordinate-permutation-plus-swap quotient.
# - Summary:
#   - Sum endpoint-symmetric cube-pair classes over reachable fixed pairs.
# - Description:
#   - Enumerates small fixed pairs and checks parity-corrected closed
#     arithmetic.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Independent fixed-pair enumeration stops at width four; arithmetic at 14.
#

"""Prospective evidence for global endpoint-symmetric cube-pair quotients."""

from __future__ import annotations

from math import comb

_AMBIGUOUS_MULTIPLICITY = 2
_EXHAUSTIVE_TRITS = 4
_MAXIMUM_TRITS = 14
_PAIR_PATTERN_COUNT = 4
_RADIX = 3
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


def _swap_fixed_classes(dimension: int) -> int:
    return ((dimension + 2) * (dimension + 2)) // 4


def _ordered_pair_classes(dimension: int) -> int:
    return comb(dimension + 3, 3)


def _endpoint_symmetric_classes(dimension: int) -> int:
    total = _ordered_pair_classes(dimension) + _swap_fixed_classes(dimension)
    return total // 2


def _closed_ordered_count(trit_count: int) -> int:
    return sum(
        comb(3, degree)
        * comb(trit_count, degree)
        * _integer_power(2, degree)
        * _integer_power(7, trit_count - degree)
        for degree in range(min(3, trit_count) + 1)
    )


def _direct_swap_fixed_count(trit_count: int) -> int:
    return sum(
        _fixed_pair_class_count(trit_count, dimension)
        * _swap_fixed_classes(dimension)
        for dimension in range(trit_count + 1)
    )


def _closed_swap_fixed_count(trit_count: int) -> int:
    if trit_count == 1:
        return 9
    numerator = (
        _integer_power(7, trit_count + 1)
        + _integer_power(3, trit_count)
        + 20 * trit_count * _integer_power(7, trit_count - 1)
        + 8
        * trit_count
        * (trit_count - 1)
        * _integer_power(7, trit_count - 2)
    )
    assert numerator % 8 == 0
    return numerator // 8


def _closed_endpoint_count(trit_count: int) -> int:
    total = (
        _closed_ordered_count(trit_count)
        + _closed_swap_fixed_count(trit_count)
    )
    assert total % 2 == 0
    return total // 2


def _direct_endpoint_count(trit_count: int) -> int:
    return sum(
        _fixed_pair_class_count(trit_count, dimension)
        * _endpoint_symmetric_classes(dimension)
        for dimension in range(trit_count + 1)
    )


def _independent_width_counts(trit_count: int) -> tuple[int, int]:
    domain = _integer_power(_RADIX, trit_count)
    raw = 0
    canonical = 0
    for accumulator in range(domain):
        for target in range(domain):
            dimension = _ambiguity_dimension(accumulator, target, trit_count)
            if dimension is None:
                continue
            raw += _integer_power(_PAIR_PATTERN_COUNT, dimension)
            canonical += _endpoint_symmetric_classes(dimension)
    return raw, canonical


def test_small_widths_match_independent_fixed_pair_enumeration() -> None:
    """Small fixed pairs sum to exact raw and endpoint-symmetric pair counts."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        raw, canonical = _independent_width_counts(trit_count)
        assert raw == _integer_power(13, trit_count)
        assert canonical == _closed_endpoint_count(trit_count)


def test_global_endpoint_symmetric_quotient_has_exact_closed_count() -> None:
    """Ambiguity sums equal the parity-corrected endpoint quotient count."""
    for trit_count in range(1, _MAXIMUM_TRITS + 1):
        assert _direct_swap_fixed_count(trit_count) == _closed_swap_fixed_count(
            trit_count
        )
        assert _direct_endpoint_count(trit_count) == _closed_endpoint_count(
            trit_count
        )
        raw = sum(
            _fixed_pair_class_count(trit_count, dimension)
            * _integer_power(_PAIR_PATTERN_COUNT, dimension)
            for dimension in range(trit_count + 1)
        )
        assert raw == _integer_power(13, trit_count)
        assert _closed_endpoint_count(trit_count) <= raw
