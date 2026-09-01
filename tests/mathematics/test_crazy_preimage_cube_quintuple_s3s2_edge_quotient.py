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
#   - Exact nested quotient counts for pair-valued K5 edges under a residual
#     S3xS2 vertex stabilizer.
# - Must-Not:
#   - Claim dense order-twelve rank/unrank.
# - Allows:
#   - Inputs: residual edge-pair mass zero through fourteen.
#   - Outputs: exact S3-first, descended-S2-fixed, and final orbit counts.
#   - Side effects: none.
# - Split-When:
#   - Constructive dense S3xS2 ranking is introduced.
# - Merge-When:
#   - Dense S5 ranking owns the same nested product-group quotient.
# - Summary:
#   - Factor residual S3xS2 edge orbits through a first S3 quotient.
# - Description:
#   - Counts the descended S2-fixed first-quotient classes by a commuting coset.
# - Usage:
#   - Prerequisite for dense residual order-twelve edge ranking.
# - Defaults:
#   - Direct orbit enumeration stops at mass three; arithmetic reaches 14.
#

"""Nested residual S3xS2 quotient evidence for pair-valued K5 edges."""

from __future__ import annotations

from itertools import permutations
from math import comb

_ACTIVE = (0, 1, 2)
_EDGE_COUNT = 10
_EXHAUSTIVE_MASS = 3
_MAXIMUM_MASS = 14
_SCALAR_COMPONENTS = 20
_WIDTH_FOURTEEN_COUNT = 68_763_298
_EDGES = tuple(
    (left, right)
    for left in range(5)
    for right in range(left + 1, 5)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_S3_ORDERS = tuple((*order, 3, 4) for order in permutations(_ACTIVE))
_B = (0, 1, 2, 4, 3)

type _Vector = tuple[int, ...]


def _composition_count(total: int, parts: int) -> int:
    return comb(total + parts - 1, parts - 1)


def _compose(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(left[right[index]] for index in range(len(left)))


def _edge_permutation(order: tuple[int, ...]) -> tuple[int, ...]:
    result: list[int] = []
    for left, right in _EDGES:
        source = tuple(sorted((order[left], order[right])))
        result.append(_EDGE_INDEX[source[0], source[1]])
    return tuple(result)


def _scalar_permutation(order: tuple[int, ...]) -> tuple[int, ...]:
    edge_permutation = _edge_permutation(order)
    return tuple(
        2 * edge_permutation[edge] + component
        for edge in range(_EDGE_COUNT)
        for component in range(2)
    )


def _cycle_lengths(permutation: tuple[int, ...]) -> tuple[int, ...]:
    unseen = set(range(len(permutation)))
    lengths: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = permutation[current]
            length += 1
        lengths.append(length)
    return tuple(sorted(lengths))


def _fixed_count(cycles: tuple[int, ...], total: int) -> int:
    coefficients = [1] + [0] * total
    for cycle_length in cycles:
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, total - degree + 1, cycle_length):
                next_coefficients[degree + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[total]


def _a(total: int) -> int:
    return _composition_count(total, _SCALAR_COMPONENTS)


def _b(total: int) -> int:
    return _fixed_count((1,) * 8 + (2,) * 6, total)


def _c(total: int) -> int:
    return _fixed_count((1,) * 2 + (3,) * 6, total)


def _d(total: int) -> int:
    return _fixed_count((1,) * 4 + (2,) * 8, total)


def _e(total: int) -> int:
    return _fixed_count((1,) * 2 + (3,) * 2 + (6,) * 2, total)


def _s3_quotient_count(total: int) -> int:
    return (_a(total) + 3 * _b(total) + 2 * _c(total)) // 6


def _descended_s2_fixed_count(total: int) -> int:
    return (_b(total) + 3 * _d(total) + 2 * _e(total)) // 6


def _s3s2_count(total: int) -> int:
    return (
        _s3_quotient_count(total) + _descended_s2_fixed_count(total)
    ) // 2


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _permute(vector: _Vector, permutation: tuple[int, ...]) -> _Vector:
    result = [0] * len(vector)
    for source, destination in enumerate(permutation):
        result[destination] = vector[source]
    return tuple(result)


def test_s3s2_generators_induce_exact_scalar_cycle_types() -> None:
    """S3 classes and the commuting S2 coset have the stated scalar cycles."""
    identity = _scalar_permutation((0, 1, 2, 3, 4))
    transposition = _scalar_permutation((1, 0, 2, 3, 4))
    three_cycle = _scalar_permutation((1, 2, 0, 3, 4))
    b = _scalar_permutation(_B)
    tb = _scalar_permutation((1, 0, 2, 4, 3))
    cb = _scalar_permutation((1, 2, 0, 4, 3))
    assert _cycle_lengths(identity) == (1,) * 20
    assert _cycle_lengths(transposition) == (1,) * 8 + (2,) * 6
    assert _cycle_lengths(three_cycle) == (1,) * 2 + (3,) * 6
    assert _cycle_lengths(b) == (1,) * 8 + (2,) * 6
    assert _cycle_lengths(tb) == (1,) * 4 + (2,) * 8
    assert _cycle_lengths(cb) == (1,) * 2 + (3,) * 2 + (6,) * 2


def test_nested_s3s2_counts_match_direct_small_orbits() -> None:
    """Direct small domains reproduce first, fixed-second, and final counts."""
    s3 = tuple(_scalar_permutation(order) for order in _S3_ORDERS)
    b = _scalar_permutation(_B)
    full = tuple(
        _scalar_permutation(_compose(order, suffix))
        for order in _S3_ORDERS
        for suffix in ((0, 1, 2, 3, 4), _B)
    )
    for total in range(_EXHAUSTIVE_MASS + 1):
        first_orbits: dict[_Vector, set[_Vector]] = {}
        final_representatives: set[_Vector] = set()
        for vector in _weak_compositions(total, _SCALAR_COMPONENTS):
            first_orbit = {_permute(vector, order) for order in s3}
            first_orbits[min(first_orbit)] = first_orbit
            final_representatives.add(
                min(_permute(vector, order) for order in full)
            )
        fixed_first = sum(
            {_permute(value, b) for value in orbit} == orbit
            for orbit in first_orbits.values()
        )
        assert len(first_orbits) == _s3_quotient_count(total)
        assert fixed_first == _descended_s2_fixed_count(total)
        assert len(final_representatives) == _s3s2_count(total)


def test_nested_s3s2_formula_is_exact_through_mass_fourteen() -> None:
    """Nested S3 then S2 counts equal direct product-group Burnside counts."""
    for total in range(_MAXIMUM_MASS + 1):
        direct = (
            _a(total)
            + 4 * _b(total)
            + 2 * _c(total)
            + 3 * _d(total)
            + 2 * _e(total)
        ) // 12
        assert _s3s2_count(total) == direct
    assert _s3s2_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
