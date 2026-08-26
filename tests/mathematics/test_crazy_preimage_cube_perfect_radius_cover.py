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
#   - Independent evidence for nontrivial perfect-radius preimage-cube covers.
# - Must-Not:
#   - Promote divisibility alone to construction or claim wall-clock speedup.
# - Allows:
#   - Inputs: cube dimensions one through fourteen and radii below dimension.
#   - Outputs: exact checked perfect-partition parameter pairs and
#     constructions.
#   - Side effects: none.
# - Split-When:
#   - Covering machinery beyond the checked perfect partitions is required.
# - Merge-When:
#   - General perfect-cover evidence owns the same radius domain.
# - Summary:
#   - Classify nontrivial perfect Hamming-ball partitions through Q14.
# - Description:
#   - Screens exact ball-volume divisibility and constructs antipodal survivors.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Arithmetic reaches Q14; antipodal partitions lift through width fourteen.
#

"""Evidence for nontrivial perfect-radius preimage-cube partitions."""

from __future__ import annotations

from math import comb

_MAXIMUM_TRITS = 14
_RADIX = 3
_Q7_DIMENSION = 7
_Q7_RADIUS_ONE_CENTERS = 16
_ANTIPODAL_CENTER_COUNT = 2
_INDEPENDENT_CRAZY_TRIT = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)


def _ball_volume(dimension: int, radius: int) -> int:
    return sum(comb(dimension, distance) for distance in range(radius + 1))


def _divisibility_survivors() -> tuple[tuple[int, int], ...]:
    return tuple(
        (dimension, radius)
        for dimension in range(1, _MAXIMUM_TRITS + 1)
        for radius in range(1, dimension)
        if (1 << dimension) % _ball_volume(dimension, radius) == 0
    )


def _antipodal_radius(dimension: int) -> int:
    return (dimension - 1) // 2


def _antipodal_center(word: int, dimension: int) -> int:
    radius = _antipodal_radius(dimension)
    return 0 if word.bit_count() <= radius else (1 << dimension) - 1


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _embedded_preimage(cube_code: int, dimension: int, trit_count: int) -> int:
    word = 0
    place = 1
    for coordinate in range(trit_count):
        data_trit = cube_code >> coordinate & 1 if coordinate < dimension else 2
        word += data_trit * place
        place *= _RADIX
    return word


def _target_for_dimension(dimension: int, trit_count: int) -> int:
    target = 0
    place = 1
    for coordinate in range(trit_count):
        target_trit = 1 if coordinate < dimension else 2
        target += target_trit * place
        place *= _RADIX
    return target


def _crazy_with_zero_accumulator(data: int, trit_count: int) -> int:
    target = 0
    place = 1
    for _ in range(trit_count):
        target += _INDEPENDENT_CRAZY_TRIT[data % _RADIX][0] * place
        data //= _RADIX
        place *= _RADIX
    return target


def _trit_distance(left: int, right: int, trit_count: int) -> int:
    distance = 0
    for _ in range(trit_count):
        distance += left % _RADIX != right % _RADIX
        left //= _RADIX
        right //= _RADIX
    return distance


def test_divisibility_survivors_are_exactly_constructed() -> None:
    """Only the checked antipodal family plus Q7 radius one can be perfect."""
    expected = (
        (3, 1),
        (5, 2),
        (_Q7_DIMENSION, 1),
        (_Q7_DIMENSION, 3),
        (9, 4),
        (11, 5),
        (13, 6),
    )
    assert _divisibility_survivors() == expected
    for dimension, radius in expected:
        center_count = (1 << dimension) // _ball_volume(dimension, radius)
        if (dimension, radius) == (_Q7_DIMENSION, 1):
            assert center_count == _Q7_RADIUS_ONE_CENTERS
        else:
            assert radius == _antipodal_radius(dimension)
            assert center_count == _ANTIPODAL_CENTER_COUNT


def test_odd_antipodal_balls_partition_every_checked_cube() -> None:
    """Two opposite centers partition every checked odd cube at half radius."""
    for dimension in range(3, _MAXIMUM_TRITS, 2):
        radius = _antipodal_radius(dimension)
        all_ones = (1 << dimension) - 1
        for word in range(1 << dimension):
            center = _antipodal_center(word, dimension)
            assert center in {0, all_ones}
            assert (word ^ center).bit_count() <= radius
            other = all_ones ^ center
            assert (word ^ other).bit_count() > radius


def test_antipodal_partitions_lift_to_checked_preimage_cubes() -> None:
    """Every checked antipodal partition transports to a fixed crazy cube."""
    for dimension in range(3, _MAXIMUM_TRITS, 2):
        radius = _antipodal_radius(dimension)
        for trit_count in range(dimension, _MAXIMUM_TRITS + 1):
            target = _target_for_dimension(dimension, trit_count)
            for code in range(1 << dimension):
                center = _antipodal_center(code, dimension)
                word = _embedded_preimage(code, dimension, trit_count)
                center_word = _embedded_preimage(center, dimension, trit_count)
                assert 0 <= word < _integer_power(_RADIX, trit_count)
                assert _crazy_with_zero_accumulator(word, trit_count) == target
                assert (
                    _crazy_with_zero_accumulator(center_word, trit_count)
                    == target
                )
                assert _trit_distance(word, center_word, trit_count) <= radius
