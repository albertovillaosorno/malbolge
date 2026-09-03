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
#   - Exact count decomposition of the S3 extensions obstructing the free
#     single-transposition quotient in the top-level all-equal S6 stratum.
# - Must-Not:
#   - Claim dense exact-S3 or exact-transposition rank/unrank.
# - Allows:
#   - Inputs: assignments fixed by S3 on vertices 0,1,2 through residual mass
#     14.
#   - Outputs: free external-S3 counts and exact-S4 exception counts.
#   - Side effects: none.
# - Split-When:
#   - Dense exact-S3 rank/unrank is implemented.
# - Merge-When:
#   - Exact transposition ranking owns the same exception decomposition.
# - Summary:
#   - Quotient S3-fixed assignments by external S3 and isolate S4 extensions.
# - Description:
#   - The free external-S3 quotient differs from exact S3 only by exact S4.
# - Usage:
#   - Second-level exception prerequisite for exact transposition ranking.
# - Defaults:
#   - Count identities are checked at every residual mass through fourteen.
#

"""Count S3 extensions inside the transposition free quotient."""

from __future__ import annotations

from collections import deque
from itertools import permutations
from typing import cast

_ARITY = 6
_MAXIMUM_MASS = 14
_EXPECTED_K_ORBIT_SIZES = {1: 10, 3: 14}
_EXPECTED_BLOCK_PROFILE = ((1, 1, 4), (1, 3, 2), (3, 1, 2), (3, 3, 4))
_EXPECTED_S3_SUBGROUPS = 6
_EXPECTED_FREE_COUNTS = (
    0,
    0,
    1,
    10,
    56,
    234,
    816,
    2_518,
    7_076,
    18_454,
    45_309,
    105_728,
    236_141,
    507_776,
    1_055_888,
)
_EXPECTED_EXACT_S3_COUNTS = (
    0,
    0,
    1,
    10,
    54,
    228,
    799,
    2_480,
    6_996,
    18_300,
    45_035,
    105_260,
    235_357,
    506_506,
    1_053_877,
)
_EXPECTED_EXACT_S4_EXCEPTIONS = (
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

type _PermutationSix = tuple[int, int, int, int, int, int]
type _PermutationThree = tuple[int, int, int]
type _Orbit = tuple[int, ...]

_K = cast(
    "tuple[_PermutationSix, ...]",
    tuple((*order, 3, 4, 5) for order in permutations(range(3))),
)
_Q3 = cast("tuple[_PermutationThree, ...]", tuple(permutations(range(3))))
_Q3_INDEX = {order: index for index, order in enumerate(_Q3)}
_IDENTITY = _Q3_INDEX[0, 1, 2]
_Q6 = cast(
    "tuple[_PermutationSix, ...]",
    tuple((0, 1, 2, *(value + 3 for value in order)) for order in _Q3),
)
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
_Q_MAPS = tuple(
    tuple(
        _K_INDEX[
            tuple(sorted(_permuted_symbol(symbol, order) for symbol in orbit))
        ]
        for orbit in _K_ORBITS
    )
    for order in _Q6
)


def _q_blocks() -> tuple[tuple[int, ...], ...]:
    unseen = set(range(len(_K_ORBITS)))
    result: list[tuple[int, ...]] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(sorted({mapping[seed] for mapping in _Q_MAPS}))
        unseen -= set(orbit)
        result.append(orbit)
    return tuple(result)


def _compose(left: int, right: int) -> int:
    return _Q3_INDEX[
        cast(
            "_PermutationThree",
            tuple(_Q3[left][_Q3[right][index]] for index in range(3)),
        )
    ]


_MULTIPLICATION = tuple(
    tuple(_compose(left, right) for right in range(6)) for left in range(6)
)


def _generated(generators: tuple[int, ...]) -> frozenset[int]:
    subgroup = {_IDENTITY}
    frontier = deque([_IDENTITY])
    generators = tuple(sorted(set(generators)))
    while frontier:
        left = frontier.popleft()
        products = tuple(
            product
            for right in generators
            for product in (
                _MULTIPLICATION[left][right],
                _MULTIPLICATION[right][left],
            )
        )
        for product in products:
            if product not in subgroup:
                subgroup.add(product)
                frontier.append(product)
    return frozenset(subgroup)


def _subgroups() -> tuple[frozenset[int], ...]:
    known = {frozenset({_IDENTITY})}
    frontier = list(known)
    while frontier:
        subgroup = frontier.pop()
        for element in range(6):
            if element in subgroup:
                continue
            candidate = _generated((*subgroup, element))
            if candidate not in known:
                known.add(candidate)
                frontier.append(candidate)
    return tuple(sorted(known, key=lambda group: (-len(group), tuple(group))))


def _subgroup_weights(subgroup: frozenset[int]) -> tuple[int, ...]:
    unseen = set(range(len(_K_ORBITS)))
    result: list[int] = []
    while unseen:
        seed = min(unseen)
        orbit = {_Q_MAPS[element][seed] for element in subgroup}
        unseen -= orbit
        result.append(len(orbit) * len(_K_ORBITS[seed]))
    return tuple(sorted(result))


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
    exact: dict[frozenset[int], int] = {}
    for subgroup in _subgroups():
        value = _fixed_count(total, _subgroup_weights(subgroup))
        for larger, exact_value in exact.items():
            if len(larger) > len(subgroup) and subgroup < larger:
                value -= exact_value
        exact[subgroup] = value
    trivial = exact[frozenset({_IDENTITY})]
    assert trivial % len(_Q3) == 0
    return trivial // len(_Q3)


def test_s3_extension_geometry_is_exact() -> None:
    """S3-fixed labels have the reviewed external-S3 block shape."""
    spectrum = {
        size: sum(len(orbit) == size for orbit in _K_ORBITS) for size in (1, 3)
    }
    assert spectrum == _EXPECTED_K_ORBIT_SIZES
    profile: dict[tuple[int, int], int] = {}
    for block in _q_blocks():
        key = len(block), len(_K_ORBITS[block[0]])
        profile[key] = profile.get(key, 0) + 1
    observed = tuple(
        sorted(
            (size, weight, count) for (size, weight), count in profile.items()
        )
    )
    assert observed == _EXPECTED_BLOCK_PROFILE
    assert len(_subgroups()) == _EXPECTED_S3_SUBGROUPS


def test_s3_extension_free_counts_match_reviewed_sequence() -> None:
    """Free external-S3 quotient counts reach 1,055,888 classes at mass 14."""
    observed = tuple(_free_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_FREE_COUNTS


def test_s3_extension_free_minus_exact_is_s4_sequence() -> None:
    """The free S3 quotient differs from exact S3 only by exact S4."""
    difference = tuple(
        free - exact
        for free, exact in zip(
            _EXPECTED_FREE_COUNTS, _EXPECTED_EXACT_S3_COUNTS, strict=True
        )
    )
    assert difference == _EXPECTED_EXACT_S4_EXCEPTIONS
