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
#   - Independent aggregate accounting for ordered quintuple cube quotients.
# - Must-Not:
#   - Convert representative-count reductions into wall-clock speedup claims.
# - Allows:
#   - Inputs: reachable fixed-pair ambiguity classes through width fourteen.
#   - Outputs: exact raw and canonical ordered-quintuple case counts.
#   - Side effects: none.
# - Split-When:
#   - Tuple arity or the quotient symmetry group changes.
# - Merge-When:
#   - Global search-space accounting owns the same fixed-pair quotient sum.
# - Summary:
#   - Sum ordered cube-quintuple quotient classes over reachable fixed pairs.
# - Description:
#   - Brute-forces small pair classes and checks a weighted-binomial identity.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Independent fixed-pair enumeration stops at width four; arithmetic at 14.
#

"""Prospective evidence for global ordered cube-quintuple quotient counts."""

from __future__ import annotations

from math import comb

_AMBIGUOUS_MULTIPLICITY = 2
_EXHAUSTIVE_TRITS = 4
_MAXIMUM_TRITS = 14
_QUINTUPLE_PATTERN_COUNT = 32
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


def _ordered_quintuple_classes(dimension: int) -> int:
    return comb(
        dimension + _QUINTUPLE_PATTERN_COUNT - 1,
        _QUINTUPLE_PATTERN_COUNT - 1,
    )


def _direct_canonical_count(trit_count: int) -> int:
    return sum(
        _fixed_pair_class_count(trit_count, dimension)
        * _ordered_quintuple_classes(dimension)
        for dimension in range(trit_count + 1)
    )


def _closed_canonical_count(trit_count: int) -> int:
    separators = _QUINTUPLE_PATTERN_COUNT - 1
    return sum(
        comb(separators, degree)
        * comb(trit_count, degree)
        * _integer_power(2, degree)
        * _integer_power(7, trit_count - degree)
        for degree in range(min(separators, trit_count) + 1)
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
            raw += _integer_power(_QUINTUPLE_PATTERN_COUNT, dimension)
            canonical += _ordered_quintuple_classes(dimension)
    return raw, canonical


def test_small_widths_match_independent_fixed_pair_enumeration() -> None:
    """Small fixed pairs sum to exact raw and quotient quintuple counts."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        raw, canonical = _independent_width_counts(trit_count)
        assert raw == _integer_power(69, trit_count)
        assert canonical == _closed_canonical_count(trit_count)


def test_global_ordered_quintuple_quotient_has_exact_closed_count() -> None:
    """Ambiguity-class summation equals the closed quintuple quotient count."""
    for trit_count in range(1, _MAXIMUM_TRITS + 1):
        assert _direct_canonical_count(trit_count) == _closed_canonical_count(
            trit_count
        )
        raw = sum(
            _fixed_pair_class_count(trit_count, dimension)
            * _integer_power(_QUINTUPLE_PATTERN_COUNT, dimension)
            for dimension in range(trit_count + 1)
        )
        assert raw == _integer_power(69, trit_count)
        assert _closed_canonical_count(trit_count) <= raw
