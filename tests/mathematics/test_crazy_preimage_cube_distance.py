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
#   - Independent evidence for exact crazy preimage cube distance classes.
# - Must-Not:
#   - Import production crazy helpers or infer external-corpus membership.
# - Allows:
#   - Inputs: reachable fixed accumulator/target pairs through width fourteen.
#   - Outputs: exact distance-class, radius-ball, and diameter assertions.
#   - Side effects: none.
# - Split-When:
#   - Another preimage distance metric needs independent executable state.
# - Merge-When:
#   - The cube-graph proof owns the same exact Hamming-distance classes.
# - Summary:
#   - Count exact distance shells and balls in crazy preimage cubes.
# - Description:
#   - Matches trit distance to bit distance and closed binomial shell counts.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - All-pair brute force stops at width four; cube dimensions reach fourteen.
#

"""Independent evidence for exact crazy preimage cube distance classes."""

from __future__ import annotations

from collections import Counter

_BINARY_RADIX = 2
_EXHAUSTIVE_TRITS = 4
_MAXIMUM_TRITS = 14
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


def _integer_binomial(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    result = 1
    for index in range(1, k + 1):
        result = result * (n - k + index) // index
    return result


def _local_preimages(accumulator: int, target: int) -> tuple[int, ...]:
    return tuple(
        data
        for data in range(_RADIX)
        if _INDEPENDENT_CRAZY_TRIT[data][accumulator] == target
    )


def _choice_sets(
    target: int,
    accumulator: int,
    trit_count: int,
) -> tuple[tuple[int, ...], ...]:
    choices: list[tuple[int, ...]] = []
    for _ in range(trit_count):
        choices.append(
            _local_preimages(accumulator % _RADIX, target % _RADIX)
        )
        target //= _RADIX
        accumulator //= _RADIX
    return tuple(choices)


def _cube_dimension(choices: tuple[tuple[int, ...], ...]) -> int:
    return sum(len(local) == _BINARY_RADIX for local in choices)


def _cube_data(
    choices: tuple[tuple[int, ...], ...],
    cube_code: int,
) -> int:
    data = 0
    place = 1
    bit_position = 0
    for local in choices:
        if not local:
            raise ValueError
        if len(local) == 1:
            data_trit = local[0]
        else:
            data_trit = local[(cube_code >> bit_position) & 1]
            bit_position += 1
        data += data_trit * place
        place *= _RADIX
    return data


def _trit_distance(left: int, right: int, trit_count: int) -> int:
    distance = 0
    for _ in range(trit_count):
        distance += left % _RADIX != right % _RADIX
        left //= _RADIX
        right //= _RADIX
    return distance


def _check_pair(target: int, accumulator: int, trit_count: int) -> None:
    choices = _choice_sets(target, accumulator, trit_count)
    if any(not local for local in choices):
        return
    dimension = _cube_dimension(choices)
    size = _integer_power(_BINARY_RADIX, dimension)
    words = tuple(_cube_data(choices, code) for code in range(size))
    for origin_code, origin in enumerate(words):
        observed = Counter(
            _trit_distance(origin, other, trit_count)
            for other in words
        )
        expected = {
            distance: _integer_binomial(dimension, distance)
            for distance in range(dimension + 1)
        }
        assert observed == expected
        for other_code, other in enumerate(words):
            assert _trit_distance(origin, other, trit_count) == (
                origin_code ^ other_code
            ).bit_count()


def test_small_pairs_have_exact_binomial_distance_shells() -> None:
    """Every reachable pair through width four has binomial distance shells."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        domain = _integer_power(_RADIX, trit_count)
        for accumulator in range(domain):
            for target in range(domain):
                _check_pair(target, accumulator, trit_count)


def test_checked_cube_dimensions_have_exact_radius_balls_and_diameter() -> None:
    """Dimensions zero through fourteen have exact balls and diameter k."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        size = _integer_power(_BINARY_RADIX, dimension)
        origin = 0
        distances = tuple((origin ^ code).bit_count() for code in range(size))
        assert max(distances, default=0) == dimension
        for radius in range(dimension + 1):
            observed = sum(distance <= radius for distance in distances)
            expected = sum(
                _integer_binomial(dimension, distance)
                for distance in range(radius + 1)
            )
            assert observed == expected
