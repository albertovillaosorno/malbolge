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
#   - Independent evidence for perfect radius-one covers of selected cubes.
# - Must-Not:
#   - Import production crazy helpers or claim wall-clock performance.
# - Allows:
#   - Inputs: cube dimensions 1 through 14 plus Hamming constructions 1,3,7.
#   - Outputs: exact perfect-cover dimensions, unique coverage, and centers.
#   - Side effects: none.
# - Split-When:
#   - A different covering radius needs separate coding-theoretic evidence.
# - Merge-When:
#   - General covering-code machinery owns the same finite construction.
# - Summary:
#   - Characterize and construct perfect radius-one covers through Q14.
# - Description:
#   - Uses nonzero binary syndrome columns and exhaustive cube verification.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Only Hamming dimensions whose cube dimension is at most fourteen.
#

"""Independent evidence for perfect radius-one covers of preimage cubes."""

from __future__ import annotations

from collections import Counter
from itertools import combinations

_MAXIMUM_TRITS = 14
_MINIMUM_CENTER_DISTANCE = 3
_RADIX = 3
_TESTED_HAMMING_DIMENSIONS = (1, 2, 3)
_INDEPENDENT_CRAZY_TRIT = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)


def _cube_dimension(parity_bits: int) -> int:
    return (1 << parity_bits) - 1


def _syndrome(word: int, dimension: int) -> int:
    result = 0
    for coordinate in range(dimension):
        if word & (1 << coordinate):
            result ^= coordinate + 1
    return result


def _codewords(parity_bits: int) -> tuple[int, ...]:
    dimension = _cube_dimension(parity_bits)
    return tuple(
        word
        for word in range(1 << dimension)
        if _syndrome(word, dimension) == 0
    )


def _decode_to_center(word: int, dimension: int) -> int:
    syndrome = _syndrome(word, dimension)
    if syndrome == 0:
        return word
    return word ^ (1 << (syndrome - 1))


def _radius_one_ball(center: int, dimension: int) -> tuple[int, ...]:
    neighbors = tuple(
        center ^ (1 << coordinate)
        for coordinate in range(dimension)
    )
    return (center, *neighbors)


def test_only_hamming_dimensions_can_partition_radius_one_balls() -> None:
    """Divisibility permits perfect radius-one partitions only in Q1, Q3, Q7."""
    admissible: list[int] = []
    for dimension in range(1, _MAXIMUM_TRITS + 1):
        ball_size = dimension + 1
        cube_size = 1 << dimension
        divides_cube = cube_size % ball_size == 0
        is_power_of_two = ball_size & (ball_size - 1) == 0
        assert divides_cube == is_power_of_two
        if divides_cube:
            admissible.append(dimension)
    expected = tuple(
        _cube_dimension(parity_bits) for parity_bits in _TESTED_HAMMING_DIMENSIONS
    )
    assert tuple(admissible) == expected


def test_hamming_centers_match_volume_lower_bound() -> None:
    """Perfect-code center counts attain the radius-one volume lower bound."""
    for parity_bits in _TESTED_HAMMING_DIMENSIONS:
        dimension = _cube_dimension(parity_bits)
        assert dimension <= _MAXIMUM_TRITS
        centers = _codewords(parity_bits)
        volume = dimension + 1
        lower_bound = (1 << dimension) // volume
        syndrome_counts = Counter(
            _syndrome(word, dimension)
            for word in range(1 << dimension)
        )
        expected_class_size = 1 << (dimension - parity_bits)
        assert syndrome_counts == Counter(
            dict.fromkeys(range(1 << parity_bits), expected_class_size)
        )
        assert len(centers) == expected_class_size
        assert len(centers) == lower_bound
        assert len(centers) * volume == 1 << dimension


def test_hamming_radius_one_balls_partition_each_checked_cube() -> None:
    """Every checked cube word lies in exactly one codeword radius-one ball."""
    for parity_bits in _TESTED_HAMMING_DIMENSIONS:
        dimension = _cube_dimension(parity_bits)
        centers = _codewords(parity_bits)
        assert all(
            (left ^ right).bit_count() >= _MINIMUM_CENTER_DISTANCE
            for left, right in combinations(centers, 2)
        )
        covered = Counter(
            word
            for center in centers
            for word in _radius_one_ball(center, dimension)
        )
        assert covered == Counter(dict.fromkeys(range(1 << dimension), 1))
        for word in range(1 << dimension):
            center = _decode_to_center(word, dimension)
            assert center in centers
            assert (word ^ center).bit_count() <= 1


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _embedded_preimage(cube_code: int, dimension: int, trit_count: int) -> int:
    word = 0
    place = 1
    for coordinate in range(trit_count):
        data_trit = (
            cube_code >> coordinate & 1
            if coordinate < dimension
            else 2
        )
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


def test_hamming_decoder_lifts_to_checked_preimage_cubes() -> None:
    """Syndrome centers stay canonical after ternary preimage embedding."""
    for parity_bits in _TESTED_HAMMING_DIMENSIONS:
        dimension = _cube_dimension(parity_bits)
        for trit_count in range(dimension, _MAXIMUM_TRITS + 1):
            target = _target_for_dimension(dimension, trit_count)
            centers = _codewords(parity_bits)
            center_words = {
                center: _embedded_preimage(center, dimension, trit_count)
                for center in centers
            }
            for code in range(1 << dimension):
                word = _embedded_preimage(code, dimension, trit_count)
                assert 0 <= word < _integer_power(_RADIX, trit_count)
                assert _crazy_with_zero_accumulator(word, trit_count) == target
                center = _decode_to_center(code, dimension)
                center_word = center_words[center]
                assert (
                    _crazy_with_zero_accumulator(center_word, trit_count)
                    == target
                )
                assert _trit_distance(word, center_word, trit_count) <= 1
