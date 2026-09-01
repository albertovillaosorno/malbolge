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
#   - Independent dense ranking evidence for endpoint-symmetric pair classes
#     across all reachable fixed accumulator/target pairs.
# - Must-Not:
#   - Apply endpoint swap to direction-sensitive analyses or import production
#     crazy-search helpers.
# - Allows:
#   - Inputs: checked widths one through fourteen and canonical local pair
#     joint-count classes.
#   - Outputs: exact global dense rank/unrank across the ragged fixed-pair
#     domain.
#   - Side effects: none.
# - Split-When:
#   - A larger endpoint group needs a distinct global orbit-ranking scheme.
# - Merge-When:
#   - Global endpoint-symmetric accounting owns the same constructive index.
# - Summary:
#   - Densely index every reachable fixed pair plus endpoint-symmetric class.
# - Description:
#   - Uses base-seven pair order and ambiguity-weighted suffix block sums.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Exhaustive global enumeration stops at width four; arithmetic reaches 14.
#

"""Dense global ranking for endpoint-symmetric crazy preimage pair classes."""

from __future__ import annotations

from math import comb

_AMBIGUOUS_DIGITS = frozenset({0, 2})
_EXHAUSTIVE_TRITS = 4
_MAXIMUM_TRITS = 14
_PAIR_RADIX = 7
_WIDTH_FOURTEEN_COUNT = 18_096_618_233_793


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _endpoint_classes(dimension: int) -> int:
    ordered = comb(dimension + 3, 3)
    swap_fixed = ((dimension + 2) * (dimension + 2)) // 4
    return (ordered + swap_fixed) // 2


def _local_block_size(residual: int) -> int:
    return ((residual + 2) * (residual + 2)) // 4


def _local_prefix(dimension: int, n00: int) -> int:
    return sum(
        _local_block_size(dimension - earlier_n00)
        for earlier_n00 in range(n00)
    )


def _local_rank(counts: tuple[int, int, int, int]) -> int | None:
    n00, n01, n10, _ = counts
    if min(counts) < 0 or n01 > n10:
        return None
    dimension = sum(counts)
    residual = dimension - n00
    return (
        _local_prefix(dimension, n00)
        + n01 * (residual - n01 + 2)
        + n10
        - n01
    )


def _local_unrank_row(residual: int, rank: int) -> tuple[int, int, int]:
    remaining = rank
    for n01 in range((residual // 2) + 1):
        row_size = residual - 2 * n01 + 1
        if remaining >= row_size:
            remaining -= row_size
            continue
        n10 = n01 + remaining
        return n01, n10, residual - n01 - n10
    raise AssertionError


def _local_unrank(
    dimension: int,
    rank: int,
) -> tuple[int, int, int, int] | None:
    if rank < 0 or rank >= _endpoint_classes(dimension):
        return None
    remaining = rank
    for n00 in range(dimension + 1):
        residual = dimension - n00
        block_size = _local_block_size(residual)
        if remaining >= block_size:
            remaining -= block_size
            continue
        n01, n10, n11 = _local_unrank_row(residual, remaining)
        return n00, n01, n10, n11
    raise AssertionError


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
        * _endpoint_classes(ambiguity + added)
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


def _global_rank(
    digits: tuple[int, ...],
    counts: tuple[int, int, int, int],
) -> int | None:
    prefix = _global_prefix(digits)
    local_rank = _local_rank(counts)
    if prefix is None or local_rank is None:
        return None
    dimension = sum(_digit_ambiguity(digit) for digit in digits)
    if sum(counts) != dimension:
        return None
    return prefix + local_rank


def _choose_global_digit(
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
) -> tuple[tuple[int, ...], tuple[int, int, int, int]] | None:
    if rank < 0 or rank >= _global_count(trit_count):
        return None
    digits = [0] * trit_count
    remaining = rank
    ambiguity = 0
    for position in reversed(range(trit_count)):
        digit, remaining = _choose_global_digit(
            position,
            ambiguity,
            remaining,
        )
        digits[position] = digit
        ambiguity += _digit_ambiguity(digit)
    counts = _local_unrank(ambiguity, remaining)
    assert counts is not None
    return tuple(digits), counts


def test_global_rank_exhausts_small_ragged_domains() -> None:
    """Widths one through four receive every global rank exactly once."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        next_rank = 0
        pair_count = _integer_power(_PAIR_RADIX, trit_count)
        for pair_rank in range(pair_count):
            digits = _pair_digits(pair_rank, trit_count)
            assert digits is not None
            ambiguity = sum(_digit_ambiguity(digit) for digit in digits)
            for local_rank in range(_endpoint_classes(ambiguity)):
                counts = _local_unrank(ambiguity, local_rank)
                assert counts is not None
                assert _global_rank(digits, counts) == next_rank
                assert _global_unrank(trit_count, next_rank) == (digits, counts)
                next_rank += 1
        assert next_rank == _global_count(trit_count)


def test_global_rank_roundtrips_checked_width_boundaries() -> None:
    """Boundary and midpoint ranks roundtrip through every checked width."""
    for trit_count in range(1, _MAXIMUM_TRITS + 1):
        count = _global_count(trit_count)
        assert _global_unrank(trit_count, -1) is None
        assert _global_unrank(trit_count, count) is None
        for rank in {0, count // 2, count - 1}:
            value = _global_unrank(trit_count, rank)
            assert value is not None
            digits, counts = value
            assert _pair_rank(digits) is not None
            assert _global_rank(digits, counts) == rank
    assert _global_count(_MAXIMUM_TRITS) == _WIDTH_FOURTEEN_COUNT


def test_global_prefix_matches_direct_small_pair_weight_sums() -> None:
    """Digit-DP prefixes equal direct earlier-pair sums at small widths."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        pair_count = _integer_power(_PAIR_RADIX, trit_count)
        running = 0
        for pair_rank in range(pair_count):
            digits = _pair_digits(pair_rank, trit_count)
            assert digits is not None
            assert _global_prefix(digits) == running
            ambiguity = sum(_digit_ambiguity(digit) for digit in digits)
            running += _endpoint_classes(ambiguity)
        assert running == _global_count(trit_count)
