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
#   - Independent evidence for exact crazy preimage cube neighborhoods.
# - Must-Not:
#   - Import production crazy helpers or infer external-corpus membership.
# - Allows:
#   - Inputs: reachable fixed accumulator/target pairs through width fourteen.
#   - Outputs: exact one-trit adjacency, degree, and edge-count assertions.
#   - Side effects: none.
# - Split-When:
#   - Another preimage graph metric needs independent executable state.
# - Merge-When:
#   - The Gray inverse proof owns the same exact neighborhood graph.
# - Summary:
#   - Prove each crazy preimage set has an exact binary-cube mutation graph.
# - Description:
#   - Matches trit adjacency to cube bits and counts every cube neighborhood.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - All-pair brute force stops at width four; cube dimensions reach fourteen.
#

"""Independent evidence for exact crazy preimage cube neighborhoods."""

from __future__ import annotations

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


def _expected_edge_count(dimension: int) -> int:
    if dimension == 0:
        return 0
    return dimension * _integer_power(_BINARY_RADIX, dimension - 1)


def _check_pair(target: int, accumulator: int, trit_count: int) -> None:
    choices = _choice_sets(target, accumulator, trit_count)
    if any(not local for local in choices):
        return
    dimension = _cube_dimension(choices)
    size = _integer_power(_BINARY_RADIX, dimension)
    words = tuple(_cube_data(choices, code) for code in range(size))
    degrees: list[int] = []
    for code, word in enumerate(words):
        degree = 0
        for other_code, other in enumerate(words):
            adjacent = _trit_distance(word, other, trit_count) == 1
            cube_adjacent = (code ^ other_code).bit_count() == 1
            assert adjacent == cube_adjacent
            degree += adjacent
        degrees.append(degree)
    assert set(degrees) == {dimension}
    assert sum(degrees) // _BINARY_RADIX == _expected_edge_count(dimension)


def test_small_pairs_match_cube_adjacency() -> None:
    """All reachable pairs through width four have exactly cube adjacency."""
    for trit_count in range(1, _EXHAUSTIVE_TRITS + 1):
        domain = _integer_power(_RADIX, trit_count)
        for accumulator in range(domain):
            for target in range(domain):
                _check_pair(target, accumulator, trit_count)


def test_checked_cube_dimensions_have_exact_degree_and_edges() -> None:
    """Dimensions zero through fourteen have degree k and k*2^(k-1) edges."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        size = _integer_power(_BINARY_RADIX, dimension)
        degree_sum = 0
        for code in range(size):
            neighbors = tuple(code ^ (1 << bit) for bit in range(dimension))
            assert len(set(neighbors)) == dimension
            assert all(0 <= neighbor < size for neighbor in neighbors)
            assert all(
                (code ^ neighbor).bit_count() == 1
                for neighbor in neighbors
            )
            degree_sum += len(neighbors)
        assert degree_sum // _BINARY_RADIX == _expected_edge_count(dimension)
