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
#   - Independent evidence for preimage-cube radius-covering lower bounds.
# - Must-Not:
#   - Import production crazy helpers or claim lower-bound attainability.
# - Allows:
#   - Inputs: cube dimensions through fourteen and complete radius balls.
#   - Outputs: exact volume arithmetic and necessary center-count bounds.
#   - Also checks one strict lower-bound example at dimension five.
#   - Side effects: none.
# - Split-When:
#   - Another covering metric needs independent executable state.
# - Merge-When:
#   - The cube-distance proof owns the same radius-volume lower bound.
# - Summary:
#   - Lower-bound the centers needed for complete fixed-radius coverage.
# - Description:
#   - Uses exact ball volumes plus exhaustive small-cube noncoverage.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - General exhaustive center sets stop at dimension four; arithmetic reaches
#     fourteen, plus Q5 radius-one strictness is checked separately.
#

"""Independent evidence for preimage-cube radius-covering lower bounds."""

from __future__ import annotations

from itertools import combinations

_BINARY_RADIX = 2
_EXHAUSTIVE_DIMENSION = 4
_MAXIMUM_TRITS = 14


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _integer_binomial(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    result = 1
    for index in range(1, k + 1):
        result = result * (n - k + index) // index
    return result


def _ball_volume(dimension: int, radius: int) -> int:
    return sum(
        _integer_binomial(dimension, distance)
        for distance in range(radius + 1)
    )


def _ceil_div(numerator: int, denominator: int) -> int:
    return (numerator + denominator - 1) // denominator


def _ball_mask(dimension: int, center: int, radius: int) -> int:
    size = _integer_power(_BINARY_RADIX, dimension)
    mask = 0
    for code in range(size):
        if (center ^ code).bit_count() <= radius:
            mask |= 1 << code
    return mask


def test_volume_bound_is_exact_arithmetic_through_dimension_fourteen() -> None:
    """Every checked radius yields the exact volume lower-bound arithmetic."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        size = _integer_power(_BINARY_RADIX, dimension)
        for radius in range(dimension + 1):
            volume = _ball_volume(dimension, radius)
            lower_bound = _ceil_div(size, volume)
            assert 1 <= lower_bound <= size
            assert (lower_bound - 1) * volume < size
            assert lower_bound * volume >= size


def _covered_mask(masks: tuple[int, ...], centers: tuple[int, ...]) -> int:
    covered = 0
    for center in centers:
        covered |= masks[center]
    return covered


def _check_small_radius(dimension: int, radius: int) -> None:
    size = _integer_power(_BINARY_RADIX, dimension)
    full_mask = (1 << size) - 1
    volume = _ball_volume(dimension, radius)
    lower_bound = _ceil_div(size, volume)
    masks = tuple(
        _ball_mask(dimension, center, radius)
        for center in range(size)
    )
    assert all(mask.bit_count() == volume for mask in masks)
    for center_count in range(lower_bound):
        assert all(
            _covered_mask(masks, centers) != full_mask
            for centers in combinations(range(size), center_count)
        )


def test_small_cubes_cannot_cover_below_volume_lower_bound() -> None:
    """No small-cube center set below the volume bound covers every vertex."""
    for dimension in range(_EXHAUSTIVE_DIMENSION + 1):
        for radius in range(dimension + 1):
            _check_small_radius(dimension, radius)


def _masks_for_radius(dimension: int, radius: int) -> tuple[int, ...]:
    size = _integer_power(_BINARY_RADIX, dimension)
    return tuple(
        _ball_mask(dimension, center, radius)
        for center in range(size)
    )


def _has_cover(masks: tuple[int, ...], center_count: int) -> bool:
    size = len(masks)
    full_mask = (1 << size) - 1
    return any(
        _covered_mask(masks, centers) == full_mask
        for centers in combinations(range(size), center_count)
    )


def test_q5_radius_one_volume_bound_is_strict() -> None:
    """Q5 radius one needs seven centers although volume gives only six."""
    dimension = 5
    radius = 1
    masks = _masks_for_radius(dimension, radius)
    size = len(masks)
    volume = _ball_volume(dimension, radius)
    lower_bound = _ceil_div(size, volume)
    assert (size, volume, lower_bound) == (32, 6, 6)
    assert not _has_cover(masks, lower_bound)
    witness = (0, 1, 2, 15, 23, 27, 28)
    assert len(witness) == lower_bound + 1
    assert _covered_mask(masks, witness) == (1 << size) - 1
