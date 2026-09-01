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
#   - Independent composition evidence for dense global S3 quotient ranking.
# - Must-Not:
#   - Re-prove local S3 rank semantics or apply endpoint symmetry to
#     direction-sensitive analyses.
# - Allows:
#   - Inputs: checked reachable-pair base-seven digits and local S3 quotient
#     ranks.
#   - Outputs: exact dense global rank/unrank through width fourteen.
#   - Side effects: none.
# - Split-When:
#   - A larger endpoint group needs a distinct global composition.
# - Merge-When:
#   - Global S3 accounting owns the same ragged-domain rank composition.
# - Summary:
#   - Compose reachable-pair order with local dense unordered-triple ranks.
# - Description:
#   - Uses ambiguity-weighted suffix sums of exact local S3 class counts.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Exhaustive global enumeration stops at width four; arithmetic reaches 14.
#

"""Dense global ranking for endpoint-unordered S3 preimage triple classes."""

from __future__ import annotations

from math import comb

_AMBIGUOUS_DIGITS = frozenset({0, 2})
_EXHAUSTIVE_TRITS = 4
_MAXIMUM_TRITS = 14
_PAIR_RADIX = 7
_WIDTH_FOURTEEN_COUNT = 124_279_218_052_677


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _transposition_fixed_count(dimension: int) -> int:
    return sum(
        comb(dimension - 2 * paired_total + 3, 3) * (paired_total + 1)
        for paired_total in range(dimension // 2 + 1)
    )


def _three_cycle_fixed_count(dimension: int) -> int:
    return sum(
        (dimension - 3 * cycled_total + 1) * (cycled_total + 1)
        for cycled_total in range(dimension // 3 + 1)
    )


def _local_class_count(dimension: int) -> int:
    identity = comb(dimension + 7, 7)
    return (
        identity
        + 3 * _transposition_fixed_count(dimension)
        + 2 * _three_cycle_fixed_count(dimension)
    ) // 6


def _digit_ambiguity(digit: int) -> int:
    return int(digit in _AMBIGUOUS_DIGITS)


def _pair_digits(rank: int, trit_count: int) -> tuple[int, ...] | None:
    pair_count = _integer_power(_PAIR_RADIX, trit_count)
    if rank < 0 or rank >= pair_count:
        return None
    digits: list[int] = []
    remaining = rank
    for _ in range(trit_count):
        digits.append(remaining % _PAIR_RADIX)
        remaining //= _PAIR_RADIX
    return tuple(digits)


def _pair_rank(digits: tuple[int, ...]) -> int | None:
    if any(digit < 0 or digit >= _PAIR_RADIX for digit in digits):
        return None
    return sum(
        digit * _integer_power(_PAIR_RADIX, position)
        for position, digit in enumerate(digits)
    )


def _suffix_weight(remaining: int, ambiguity: int) -> int:
    return sum(
        comb(remaining, added)
        * _integer_power(2, added)
        * _integer_power(5, remaining - added)
        * _local_class_count(ambiguity + added)
        for added in range(remaining + 1)
    )


def _global_count(trit_count: int) -> int:
    return _suffix_weight(trit_count, 0)


def _global_prefix(digits: tuple[int, ...]) -> int | None:
    if _pair_rank(digits) is None:
        return None
    prefix = 0
    ambiguity = 0
    for position in reversed(range(len(digits))):
        digit = digits[position]
        for earlier_digit in range(digit):
            prefix += _suffix_weight(
                position,
                ambiguity + _digit_ambiguity(earlier_digit),
            )
        ambiguity += _digit_ambiguity(digit)
    return prefix


def _global_rank(digits: tuple[int, ...], local_rank: int) -> int | None:
    prefix = _global_prefix(digits)
    if prefix is None:
        return None
    ambiguity = sum(_digit_ambiguity(digit) for digit in digits)
    if local_rank < 0 or local_rank >= _local_class_count(ambiguity):
        return None
    return prefix + local_rank


def _choose_digit(
    position: int,
    ambiguity: int,
    rank: int,
) -> tuple[int, int]:
    remaining = rank
    for digit in range(_PAIR_RADIX):
        block = _suffix_weight(
            position,
            ambiguity + _digit_ambiguity(digit),
        )
        if remaining >= block:
            remaining -= block
            continue
        return digit, remaining
    raise AssertionError


def _global_unrank(
    trit_count: int,
    rank: int,
) -> tuple[tuple[int, ...], int] | None:
    if rank < 0 or rank >= _global_count(trit_count):
        return None
    digits = [0] * trit_count
    remaining = rank
    ambiguity = 0
    for position in reversed(range(trit_count)):
        digit, remaining = _choose_digit(position, ambiguity, remaining)
        digits[position] = digit
        ambiguity += _digit_ambiguity(digit)
    assert remaining < _local_class_count(ambiguity)
    return tuple(digits), remaining


def test_global_s3_rank_exhausts_small_ragged_domains() -> None:
    """Widths one through four receive every global S3 rank exactly once."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        next_rank = 0
        for pair_rank in range(_integer_power(_PAIR_RADIX, trit_count)):
            digits = _pair_digits(pair_rank, trit_count)
            assert digits is not None
            ambiguity = sum(_digit_ambiguity(digit) for digit in digits)
            for local_rank in range(_local_class_count(ambiguity)):
                assert _global_rank(digits, local_rank) == next_rank
                assert _global_unrank(trit_count, next_rank) == (
                    digits,
                    local_rank,
                )
                next_rank += 1
        assert next_rank == _global_count(trit_count)


def test_global_s3_rank_roundtrips_checked_boundaries() -> None:
    """Boundary and midpoint S3 ranks roundtrip through every checked width."""
    for trit_count in range(1, _MAXIMUM_TRITS + 1):
        count = _global_count(trit_count)
        assert _global_unrank(trit_count, -1) is None
        assert _global_unrank(trit_count, count) is None
        for rank in {0, count // 2, count - 1}:
            value = _global_unrank(trit_count, rank)
            assert value is not None
            digits, local_rank = value
            assert _global_rank(digits, local_rank) == rank
    assert _global_count(_MAXIMUM_TRITS) == _WIDTH_FOURTEEN_COUNT


def test_global_s3_prefix_matches_direct_small_pair_sums() -> None:
    """Digit-DP prefixes equal direct earlier fixed-pair class sums."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        running = 0
        for pair_rank in range(_integer_power(_PAIR_RADIX, trit_count)):
            digits = _pair_digits(pair_rank, trit_count)
            assert digits is not None
            assert _global_prefix(digits) == running
            ambiguity = sum(_digit_ambiguity(digit) for digit in digits)
            running += _local_class_count(ambiguity)
        assert running == _global_count(trit_count)
