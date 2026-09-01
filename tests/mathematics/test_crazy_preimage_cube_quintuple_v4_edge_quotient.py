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
#     S2-by-S2 vertex stabilizer.
# - Must-Not:
#   - Claim dense V4 rank/unrank or quotient by independent edge swaps.
# - Allows:
#   - Inputs: residual edge-pair mass zero through fourteen.
#   - Outputs: exact first-quotient, second-fixed, and V4 orbit counts.
#   - Side effects: none.
# - Split-When:
#   - Constructive dense V4 ranking is introduced.
# - Merge-When:
#   - Dense S5 ranking owns the same nested commuting-involution quotient.
# - Summary:
#   - Factor residual V4 edge orbits through two commuting transpositions.
# - Description:
#   - Counts the second involution's fixed first-S2 quotient classes exactly.
# - Usage:
#   - Prerequisite for dense residual order-four edge ranking.
# - Defaults:
#   - Direct orbit enumeration stops at mass three; arithmetic reaches 14.
#

"""Nested residual V4 quotient evidence for pair-valued K5 edge counts."""

from __future__ import annotations

from math import comb

_EDGE_COUNT = 10
_EXHAUSTIVE_MASS = 3
_MAXIMUM_MASS = 14
_SCALAR_COMPONENTS = 20
_WIDTH_FOURTEEN_COUNT = 205_482_000
_A = (1, 0, 2, 3, 4)
_B = (0, 1, 3, 2, 4)
_EDGES = tuple(
    (left, right)
    for left in range(5)
    for right in range(left + 1, 5)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}

type _Vector = tuple[int, ...]


def _composition_count(total: int, parts: int) -> int:
    return comb(total + parts - 1, parts - 1)


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


def _compose(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(left[right[index]] for index in range(len(left)))


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


def _identity_count(total: int) -> int:
    return _composition_count(total, _SCALAR_COMPONENTS)


def _single_fixed_count(total: int) -> int:
    return _fixed_count((1,) * 8 + (2,) * 6, total)


def _double_fixed_count(total: int) -> int:
    return _fixed_count((1,) * 4 + (2,) * 8, total)


def _first_quotient_count(total: int) -> int:
    return (_identity_count(total) + _single_fixed_count(total)) // 2


def _second_fixed_first_quotient_count(total: int) -> int:
    return (_single_fixed_count(total) + _double_fixed_count(total)) // 2


def _v4_count(total: int) -> int:
    return (
        _first_quotient_count(total)
        + _second_fixed_first_quotient_count(total)
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


def test_v4_generators_have_exact_commuting_scalar_cycle_types() -> None:
    """The two transpositions commute and induce the expected scalar cycles."""
    a = _scalar_permutation(_A)
    b = _scalar_permutation(_B)
    ab = _compose(a, b)
    assert _compose(a, b) == _compose(b, a)
    assert _cycle_lengths(a) == (1,) * 8 + (2,) * 6
    assert _cycle_lengths(b) == (1,) * 8 + (2,) * 6
    assert _cycle_lengths(ab) == (1,) * 4 + (2,) * 8


def test_nested_v4_counts_match_direct_small_orbits() -> None:
    """Direct small domains reproduce first, fixed-second, and final counts."""
    a = _scalar_permutation(_A)
    b = _scalar_permutation(_B)
    for total in range(_EXHAUSTIVE_MASS + 1):
        first_orbits: dict[_Vector, set[_Vector]] = {}
        final_representatives: set[_Vector] = set()
        for vector in _weak_compositions(total, _SCALAR_COMPONENTS):
            av = _permute(vector, a)
            bv = _permute(vector, b)
            first_orbits[min(vector, av)] = {vector, av}
            final_representatives.add(min(vector, av, bv, _permute(av, b)))
        fixed_first = sum(
            {
                _permute(value, b) for value in orbit
            } == orbit
            for orbit in first_orbits.values()
        )
        assert len(first_orbits) == _first_quotient_count(total)
        assert fixed_first == _second_fixed_first_quotient_count(total)
        assert len(final_representatives) == _v4_count(total)


def test_nested_v4_formula_is_exact_through_mass_fourteen() -> None:
    """Nested involution counts equal direct V4 Burnside arithmetic."""
    for total in range(_MAXIMUM_MASS + 1):
        direct = (
            _identity_count(total)
            + 2 * _single_fixed_count(total)
            + _double_fixed_count(total)
        ) // 4
        assert _v4_count(total) == direct
    assert _v4_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
