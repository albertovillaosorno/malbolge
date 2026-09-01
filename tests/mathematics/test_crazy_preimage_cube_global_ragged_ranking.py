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
#   - Generic dense-rank composition evidence for reachable fixed pairs and any
#     ambiguity-indexed local quotient family.
# - Must-Not:
#   - Claim that a local quotient has a dense rank unless separately proved.
# - Allows:
#   - Inputs: widths one through fourteen, base-seven reachable-pair digits,
#     exact local class counts, and already-dense local ranks.
#   - Outputs: exact dense global rank/unrank over the resulting ragged union.
#   - Side effects: none.
# - Split-When:
#   - Fixed-pair multiplicities stop depending only on ambiguity dimension.
# - Merge-When:
#   - Generic global quotient accounting owns the same constructive lift.
# - Summary:
#   - Lift any ambiguity-indexed dense local rank through reachable-pair order.
# - Description:
#   - Uses binomial suffix weights and high-digit base-seven block subtraction.
# - Usage:
#   - Specialized by the S2, S3, and S4 global dense quotient ranks.
# - Defaults:
#   - Exhaustive synthetic enumeration stops at width four; checks reach 14.
#

"""Generic dense ragged-domain ranking over reachable crazy fixed pairs."""

from __future__ import annotations

from collections.abc import Callable
from functools import cache
from math import comb

_AMBIGUOUS_DIGITS = frozenset({0, 2})
_EXHAUSTIVE_TRITS = 4
_MAXIMUM_TRITS = 14
_PAIR_RADIX = 7
_S2_GLOBAL_N14 = 18_096_618_233_793
_S3_GLOBAL_N14 = 124_279_218_052_677
_S4_GLOBAL_N14 = 1_409_733_897_288_413

LocalCount = Callable[[int], int]


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _digit_ambiguity(digit: int) -> int:
    return int(digit in _AMBIGUOUS_DIGITS)


def _pair_digits(rank: int, trit_count: int) -> tuple[int, ...] | None:
    if rank < 0 or rank >= _integer_power(_PAIR_RADIX, trit_count):
        return None
    digits: list[int] = []
    remaining = rank
    for _ in range(trit_count):
        digits.append(remaining % _PAIR_RADIX)
        remaining //= _PAIR_RADIX
    return tuple(digits)


def _suffix_weight(
    remaining: int,
    ambiguity: int,
    local_count: LocalCount,
) -> int:
    return sum(
        comb(remaining, added)
        * _integer_power(2, added)
        * _integer_power(5, remaining - added)
        * local_count(ambiguity + added)
        for added in range(remaining + 1)
    )


def _global_count(trit_count: int, local_count: LocalCount) -> int:
    return _suffix_weight(trit_count, 0, local_count)


def _global_prefix(
    digits: tuple[int, ...],
    local_count: LocalCount,
) -> int | None:
    if any(digit < 0 or digit >= _PAIR_RADIX for digit in digits):
        return None
    prefix = 0
    ambiguity = 0
    for position in reversed(range(len(digits))):
        digit = digits[position]
        for earlier_digit in range(digit):
            prefix += _suffix_weight(
                position,
                ambiguity + _digit_ambiguity(earlier_digit),
                local_count,
            )
        ambiguity += _digit_ambiguity(digit)
    return prefix


def _global_rank(
    digits: tuple[int, ...],
    local_rank: int,
    local_count: LocalCount,
) -> int | None:
    prefix = _global_prefix(digits, local_count)
    if prefix is None:
        return None
    ambiguity = sum(_digit_ambiguity(digit) for digit in digits)
    if local_rank < 0 or local_rank >= local_count(ambiguity):
        return None
    return prefix + local_rank


def _choose_digit(
    position: int,
    ambiguity: int,
    rank: int,
    *,
    local_count: LocalCount,
) -> tuple[int, int]:
    remaining = rank
    for digit in range(_PAIR_RADIX):
        block = _suffix_weight(
            position,
            ambiguity + _digit_ambiguity(digit),
            local_count,
        )
        if remaining >= block:
            remaining -= block
            continue
        return digit, remaining
    raise AssertionError


def _global_unrank(
    trit_count: int,
    rank: int,
    local_count: LocalCount,
) -> tuple[tuple[int, ...], int] | None:
    if rank < 0 or rank >= _global_count(trit_count, local_count):
        return None
    digits = [0] * trit_count
    remaining = rank
    ambiguity = 0
    for position in reversed(range(trit_count)):
        digit, remaining = _choose_digit(
            position,
            ambiguity,
            remaining,
            local_count=local_count,
        )
        digits[position] = digit
        ambiguity += _digit_ambiguity(digit)
    assert remaining < local_count(ambiguity)
    return tuple(digits), remaining


def _synthetic_count(ambiguity: int) -> int:
    return ambiguity * ambiguity + ambiguity + 1


def _s2_count(ambiguity: int) -> int:
    ordered = comb(ambiguity + 3, 3)
    swap_fixed = ((ambiguity + 2) * (ambiguity + 2)) // 4
    return (ordered + swap_fixed) // 2


def _fixed_count(cycles: tuple[int, ...], ambiguity: int) -> int:
    coefficients = [1] + [0] * ambiguity
    for cycle_length in cycles:
        next_coefficients = [0] * (ambiguity + 1)
        for total, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, ambiguity - total + 1, cycle_length):
                next_coefficients[total + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[ambiguity]


@cache
def _s3_count(ambiguity: int) -> int:
    identity = comb(ambiguity + 7, 7)
    transposition = _fixed_count((1,) * 4 + (2,) * 2, ambiguity)
    three_cycle = _fixed_count((1,) * 2 + (3,) * 2, ambiguity)
    return (identity + 3 * transposition + 2 * three_cycle) // 6


@cache
def _s4_count(ambiguity: int) -> int:
    fixed = (
        _fixed_count((1,) * 16, ambiguity),
        _fixed_count((1,) * 8 + (2,) * 4, ambiguity),
        _fixed_count((1,) * 4 + (2,) * 6, ambiguity),
        _fixed_count((1,) * 4 + (3,) * 4, ambiguity),
        _fixed_count((1,) * 2 + (2,) + (4,) * 3, ambiguity),
    )
    weights = (1, 6, 3, 8, 6)
    return sum(
        weight * value
        for weight, value in zip(weights, fixed, strict=True)
    ) // 24


def test_generic_ragged_rank_exhausts_synthetic_small_domains() -> None:
    """An arbitrary positive local count law lifts to one contiguous domain."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        next_rank = 0
        for pair_rank in range(_integer_power(_PAIR_RADIX, trit_count)):
            digits = _pair_digits(pair_rank, trit_count)
            assert digits is not None
            ambiguity = sum(_digit_ambiguity(digit) for digit in digits)
            for local_rank in range(_synthetic_count(ambiguity)):
                assert (
                    _global_rank(digits, local_rank, _synthetic_count)
                    == next_rank
                )
                assert _global_unrank(
                    trit_count,
                    next_rank,
                    _synthetic_count,
                ) == (digits, local_rank)
                next_rank += 1
        assert next_rank == _global_count(trit_count, _synthetic_count)


def test_generic_ragged_rank_rejects_invalid_local_or_pair_ranks() -> None:
    """The lift fails closed on invalid digits and local quotient ranks."""
    assert _global_rank((7,), 0, _synthetic_count) is None
    assert _global_rank((0,), -1, _synthetic_count) is None
    ambiguity = _digit_ambiguity(0)
    assert (
        _global_rank((0,), _synthetic_count(ambiguity), _synthetic_count)
        is None
    )


def test_s2_s3_s4_specializations_match_exact_global_counts() -> None:
    """The generic lift reproduces every currently dense endpoint quotient."""
    expected = (
        (_s2_count, _S2_GLOBAL_N14),
        (_s3_count, _S3_GLOBAL_N14),
        (_s4_count, _S4_GLOBAL_N14),
    )
    for local_count, global_count in expected:
        assert _global_count(_MAXIMUM_TRITS, local_count) == global_count
        for trit_count in range(1, _MAXIMUM_TRITS + 1):
            count = _global_count(trit_count, local_count)
            for rank in {0, count // 2, count - 1}:
                value = _global_unrank(trit_count, rank, local_count)
                assert value is not None
                digits, local_rank = value
                assert _global_rank(digits, local_rank, local_count) == rank
