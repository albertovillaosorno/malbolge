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
#   - Independent evidence for exact crazy preimage cube geodesics.
# - Must-Not:
#   - Import production crazy helpers or infer external-corpus membership.
# - Allows:
#   - Inputs: reachable fixed accumulator/target pairs through width fourteen.
#   - Outputs: exact mutation-step lower bounds and shortest-path counts.
#   - Side effects: none.
# - Split-When:
#   - Another mutation-path cost model needs independent executable state.
# - Merge-When:
#   - The cube-distance proof owns the same exact shortest-path structure.
# - Summary:
#   - Prove exact one-trit mutation distances and geodesic counts.
# - Description:
#   - Matches trit distance to cube distance and counts coordinate orders.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - All-pair brute force stops at width four; cube dimensions reach fourteen.
#

"""Independent evidence for exact crazy preimage cube geodesics."""

from __future__ import annotations

from itertools import pairwise
from itertools import permutations

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


def _integer_factorial(value: int) -> int:
    result = 1
    for factor in range(2, value + 1):
        result *= factor
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


def _shortest_cube_paths(left: int, right: int) -> tuple[tuple[int, ...], ...]:
    difference = left ^ right
    differing_bits = tuple(
        bit
        for bit in range(difference.bit_length())
        if difference & (1 << bit)
    )
    paths: list[tuple[int, ...]] = []
    for order in permutations(differing_bits):
        current = left
        path = [current]
        for bit in order:
            current ^= 1 << bit
            path.append(current)
        assert current == right
        paths.append(tuple(path))
    if not differing_bits:
        return ((left,),)
    return tuple(paths)


def _check_geodesics(
    words: tuple[int, ...],
    left_code: int,
    right_code: int,
    *,
    trit_count: int,
) -> None:
    left = words[left_code]
    right = words[right_code]
    distance = _trit_distance(left, right, trit_count)
    assert distance == (left_code ^ right_code).bit_count()
    paths = _shortest_cube_paths(left_code, right_code)
    assert len(paths) == _integer_factorial(distance)
    assert len(set(paths)) == len(paths)
    assert all(len(path) - 1 == distance for path in paths)
    assert all(
        path[0] == left_code and path[-1] == right_code
        for path in paths
    )
    for path in paths:
        encoded = tuple(words[code] for code in path)
        assert all(
            _trit_distance(before, after, trit_count) == 1
            for before, after in pairwise(encoded)
        )


def _check_pair(target: int, accumulator: int, trit_count: int) -> None:
    choices = _choice_sets(target, accumulator, trit_count)
    if any(not local for local in choices):
        return
    dimension = _cube_dimension(choices)
    size = _integer_power(_BINARY_RADIX, dimension)
    words = tuple(_cube_data(choices, code) for code in range(size))
    for left_code in range(size):
        for right_code in range(size):
            _check_geodesics(
                words,
                left_code,
                right_code,
                trit_count=trit_count,
            )


def test_small_pairs_have_exact_shortest_mutation_paths() -> None:
    """Every reachable pair through width four has exact cube geodesics."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        domain = _integer_power(_RADIX, trit_count)
        for accumulator in range(domain):
            for target in range(domain):
                _check_pair(target, accumulator, trit_count)


def _monotone_path_counts(dimension: int) -> tuple[int, ...]:
    size = _integer_power(_BINARY_RADIX, dimension)
    counts = [0] * size
    counts[0] = 1
    for code in range(1, size):
        counts[code] = sum(
            counts[code ^ (1 << bit)]
            for bit in range(dimension)
            if code & (1 << bit)
        )
    return tuple(counts)


def test_checked_cube_distances_have_factorial_geodesic_counts() -> None:
    """Checked cube geodesic counts independently equal distance factorials."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        counts = _monotone_path_counts(dimension)
        for code, count in enumerate(counts):
            distance = code.bit_count()
            assert count == _integer_factorial(distance)
            assert distance <= dimension
