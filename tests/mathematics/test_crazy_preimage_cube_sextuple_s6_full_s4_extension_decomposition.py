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
#   - Exact count decomposition of the S4 extensions obstructing exact S3 in
#     the top-level all-equal S6 stratum.
# - Must-Not:
#   - Claim dense exact-S4, exact-S3, or exact-transposition rank/unrank.
# - Allows:
#   - Inputs: assignments fixed by S4 on vertices 0,1,2,3 through mass 14.
#   - Outputs: free external-S2 counts and exact point-S5 exception counts.
#   - Side effects: none.
# - Split-When:
#   - Dense exact-S4 rank/unrank is implemented.
# - Merge-When:
#   - Exact S3 ranking owns the same exception decomposition.
# - Summary:
#   - Quotient S4-fixed assignments by the external swap and isolate S5.
# - Description:
#   - The free external-S2 quotient differs from exact S4 only by point S5.
# - Usage:
#   - Final count prerequisite in the transposition exception chain.
# - Defaults:
#   - Count identities are checked at every residual mass through fourteen.
#

"""Count S4 extensions inside the exact-S3 exception hierarchy."""

from __future__ import annotations

from itertools import permutations
from typing import cast

_ARITY = 6
_MAXIMUM_MASS = 14
_EXPECTED_K_ORBIT_SIZES = {1: 4, 4: 6, 6: 4}
_EXPECTED_BLOCK_PROFILE = (
    (1, 1, 4),
    (1, 4, 2),
    (1, 6, 2),
    (2, 4, 2),
    (2, 6, 1),
)
_EXPECTED_FREE_COUNTS = (
    0,
    0,
    0,
    0,
    2,
    8,
    21,
    44,
    88,
    164,
    293,
    496,
    821,
    1_316,
    2_066,
)
_EXPECTED_EXACT_S4_COUNTS = (
    0,
    0,
    0,
    0,
    2,
    6,
    17,
    38,
    80,
    154,
    274,
    468,
    784,
    1_270,
    2_011,
)
_EXPECTED_POINT_S5_EXCEPTIONS = (
    0,
    0,
    0,
    0,
    0,
    2,
    4,
    6,
    8,
    10,
    19,
    28,
    37,
    46,
    55,
)

type _PermutationSix = tuple[int, int, int, int, int, int]
type _Orbit = tuple[int, ...]

_K = cast(
    "tuple[_PermutationSix, ...]",
    tuple((*order, 4, 5) for order in permutations(range(4))),
)
_EXTERNAL_SWAP: _PermutationSix = (0, 1, 2, 3, 5, 4)
_IDENTITY: _PermutationSix = (0, 1, 2, 3, 4, 5)
_RESIDUAL_LABELS = tuple(
    symbol
    for symbol in range(1 << _ARITY)
    if symbol.bit_count() not in {1, _ARITY - 1}
)


def _permuted_symbol(symbol: int, order: _PermutationSix) -> int:
    bits = tuple(
        (symbol >> (_ARITY - endpoint - 1)) & 1 for endpoint in range(_ARITY)
    )
    result = 0
    for source in order:
        result = (result << 1) | bits[source]
    return result


def _k_orbits() -> tuple[_Orbit, ...]:
    unseen = set(_RESIDUAL_LABELS)
    result: list[_Orbit] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(sorted({_permuted_symbol(seed, order) for order in _K}))
        unseen -= set(orbit)
        result.append(orbit)
    return tuple(sorted(result, key=lambda orbit: (len(orbit), orbit)))


_K_ORBITS = _k_orbits()
_K_INDEX = {orbit: index for index, orbit in enumerate(_K_ORBITS)}
_SWAP_MAP = tuple(
    _K_INDEX[
        tuple(
            sorted(_permuted_symbol(symbol, _EXTERNAL_SWAP) for symbol in orbit)
        )
    ]
    for orbit in _K_ORBITS
)


def _blocks() -> tuple[tuple[int, ...], ...]:
    unseen = set(range(len(_K_ORBITS)))
    result: list[tuple[int, ...]] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(sorted({seed, _SWAP_MAP[seed]}))
        unseen -= set(orbit)
        result.append(orbit)
    return tuple(result)


def _weights(*, swapped: bool) -> tuple[int, ...]:
    if not swapped:
        return tuple(sorted(len(orbit) for orbit in _K_ORBITS))
    return tuple(
        sorted(len(block) * len(_K_ORBITS[block[0]]) for block in _blocks())
    )


def _fixed_count(total: int, weights: tuple[int, ...]) -> int:
    coefficients = [1] + [0] * total
    for weight in weights:
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, total - degree + 1, weight):
                next_coefficients[degree + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[total]


def _free_count(total: int) -> int:
    identity_fixed = _fixed_count(total, _weights(swapped=False))
    swap_fixed = _fixed_count(total, _weights(swapped=True))
    assert (identity_fixed - swap_fixed) % 2 == 0
    return (identity_fixed - swap_fixed) // 2


def test_s4_extension_geometry_is_exact() -> None:
    """S4-fixed labels have the reviewed external-swap block shape."""
    spectrum = {
        size: sum(len(orbit) == size for orbit in _K_ORBITS)
        for size in (1, 4, 6)
    }
    assert spectrum == _EXPECTED_K_ORBIT_SIZES
    profile: dict[tuple[int, int], int] = {}
    for block in _blocks():
        key = len(block), len(_K_ORBITS[block[0]])
        profile[key] = profile.get(key, 0) + 1
    observed = tuple(
        sorted(
            (size, weight, count) for (size, weight), count in profile.items()
        )
    )
    assert observed == _EXPECTED_BLOCK_PROFILE
    assert _permuted_symbol(0, _IDENTITY) == 0


def test_s4_extension_free_counts_match_reviewed_sequence() -> None:
    """Free external-S2 counts reach 2,066 classes at residual mass 14."""
    observed = tuple(_free_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_FREE_COUNTS


def test_s4_extension_free_minus_exact_is_point_s5_sequence() -> None:
    """The free S4 quotient differs from exact S4 only by point S5."""
    difference = tuple(
        free - exact
        for free, exact in zip(
            _EXPECTED_FREE_COUNTS, _EXPECTED_EXACT_S4_COUNTS, strict=True
        )
    )
    assert difference == _EXPECTED_POINT_S5_EXCEPTIONS
