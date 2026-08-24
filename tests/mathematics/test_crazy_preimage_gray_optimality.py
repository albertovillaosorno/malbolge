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
#   - Independent evidence for the exact minimum Gray preimage edit cost.
# - Must-Not:
#   - Import production crazy helpers or claim runtime performance.
# - Allows:
#   - Inputs: binary cube dimensions induced by reachable crazy preimages.
#   - Outputs: exact Hamiltonian-path trit-edit lower-bound assertions.
#   - Side effects: none.
# - Split-When:
#   - Another traversal metric needs an independent proof surface.
# - Merge-When:
#   - The Gray preimage proof owns the same minimum-edit theorem.
# - Summary:
#   - Prove Gray preimage enumeration minimizes total trit edits.
# - Description:
#   - Uses distinct-vertex lower bounds and exhaustive small-cube paths.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Gray dimensions stop at fourteen; exhaustive permutations stop at three.
#

"""Independent evidence for exact minimum Gray preimage edit cost."""

from __future__ import annotations

from itertools import pairwise
from itertools import permutations

_BINARY_RADIX = 2
_EXHAUSTIVE_DIMENSION = 3
_MAXIMUM_TRITS = 14


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _gray_code(rank: int) -> int:
    return rank ^ (rank >> 1)


def _binary_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def _path_cost(path: tuple[int, ...]) -> int:
    cost = 0
    for left, right in pairwise(path):
        cost += _binary_distance(left, right)
    return cost


def _minimum_distinct_path_cost(vertex_count: int) -> int:
    return max(0, vertex_count - 1)


def test_gray_cube_attains_path_lower_bound() -> None:
    """Gray order spends exactly one bit edit on every required transition."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        size = _integer_power(_BINARY_RADIX, dimension)
        path = tuple(_gray_code(rank) for rank in range(size))
        assert len(set(path)) == size
        assert _path_cost(path) == _minimum_distinct_path_cost(size)


def test_small_cube_paths_cannot_beat_lower_bound() -> None:
    """Every small-cube Hamiltonian path obeys the same lower bound."""
    for dimension in range(_EXHAUSTIVE_DIMENSION + 1):
        size = _integer_power(_BINARY_RADIX, dimension)
        lower_bound = _minimum_distinct_path_cost(size)
        observed = min(
            _path_cost(path)
            for path in permutations(range(size))
        )
        assert observed == lower_bound


def test_gray_path_cost_is_two_to_k_minus_one() -> None:
    """The exact optimum for a k-dimensional preimage cube is 2^k minus one."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        size = _integer_power(_BINARY_RADIX, dimension)
        path = tuple(_gray_code(rank) for rank in range(size))
        assert _path_cost(path) == max(0, size - 1)
