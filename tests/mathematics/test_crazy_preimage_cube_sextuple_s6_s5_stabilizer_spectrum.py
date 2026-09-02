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
#   - Exact stabilizer-order spectrum for widened full-S5 K5 edge orbits.
# - Must-Not:
#   - Claim a dense local rank for any exact-stabilizer stratum.
# - Allows:
#   - Inputs: four-component K5 edge assignments through mass fourteen.
#   - Outputs: exact class counts grouped by full-S5 stabilizer order.
#   - Side effects: none.
# - Split-When:
#   - Constructive local ranks replace count-only exact-stabilizer strata.
# - Merge-When:
#   - A widened complete full-S5 dense rank owns the same subgroup inversion.
# - Summary:
#   - Invert the complete S5 subgroup lattice for widened K5 edge values.
# - Description:
#   - Möbius-style supergroup subtraction isolates exact stabilizers.
# - Usage:
#   - Fixes the stratum targets for the remaining order-120 dense rank.
# - Defaults:
#   - Direct orbit spectra stop at mass two; lattice arithmetic reaches 14.
#

"""Exact widened full-S5 stabilizer-order spectrum for the S6 (5,1;5) core."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import permutations
from math import comb
from math import factorial

_ARITY = 5
_EDGE_COUNT = 10
_EDGE_COMPONENTS = 4
_SCALAR_COMPONENTS = _EDGE_COUNT * _EDGE_COMPONENTS
_EXHAUSTIVE_MASS = 2
_MAXIMUM_MASS = 14
_S5_ORDER = factorial(_ARITY)
_SUBGROUP_COUNT = 156
_WIDTH_FOURTEEN_CLASSES = 20_103_708_128
_WIDTH_FOURTEEN_TRIVIAL_CLASSES = 19_963_566_552
_EXPECTED_ORDER_SPECTRUM = {
    1: 19_963_566_552,
    2: 138_268_888,
    4: 1_841_328,
    6: 22_280,
    8: 1_728,
    12: 7_312,
    24: 40,
}
_EXPECTED_COUNTS = (
    1,
    4,
    30,
    220,
    1_651,
    11_784,
    78_886,
    486_608,
    2_759_434,
    14_421_284,
    69_829_516,
    315_151_692,
    1_333_556_680,
    5_319_669_572,
    20_103_708_128,
)
_EDGES = tuple(
    (left, right) for left in range(_ARITY) for right in range(left + 1, _ARITY)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_PERMUTATIONS = tuple(permutations(range(_ARITY)))
_PERMUTATION_INDEX = {order: index for index, order in enumerate(_PERMUTATIONS)}
_IDENTITY = _PERMUTATION_INDEX[tuple(range(_ARITY))]

type _EdgeValue = tuple[int, int, int, int]
type _EdgeValues = tuple[_EdgeValue, ...]
type _Subgroup = frozenset[int]
type _Vector = tuple[int, ...]


def _compose(left: int, right: int) -> int:
    left_order = _PERMUTATIONS[left]
    right_order = _PERMUTATIONS[right]
    composed = tuple(left_order[right_order[index]] for index in range(_ARITY))
    return _PERMUTATION_INDEX[composed]


_MULTIPLICATION = tuple(
    tuple(_compose(left, right) for right in range(_S5_ORDER))
    for left in range(_S5_ORDER)
)


def _closure_step(subgroup: set[int], generators: tuple[int, ...]) -> set[int]:
    additions: set[int] = set()
    for left in subgroup:
        for right in generators:
            additions.update((
                _MULTIPLICATION[left][right],
                _MULTIPLICATION[right][left],
            ))
    return additions - subgroup


@cache
def _generated(generators: tuple[int, ...]) -> _Subgroup:
    subgroup = {_IDENTITY}
    additions = _closure_step(subgroup, generators)
    while additions:
        subgroup.update(additions)
        additions = _closure_step(subgroup, generators)
    return frozenset(subgroup)


@cache
def _subgroups() -> tuple[_Subgroup, ...]:
    known = {frozenset({_IDENTITY})}
    frontier = [frozenset({_IDENTITY})]
    while frontier:
        subgroup = frontier.pop()
        for element in range(_S5_ORDER):
            if element in subgroup:
                continue
            generated = _generated((*sorted(subgroup), element))
            if generated in known:
                continue
            known.add(generated)
            frontier.append(generated)
    return tuple(sorted(known, key=lambda group: (-len(group), tuple(group))))


def _edge_permutation(element: int) -> tuple[int, ...]:
    order = _PERMUTATIONS[element]
    result: list[int] = []
    for left, right in _EDGES:
        image = tuple(sorted((order[left], order[right])))
        result.append(_EDGE_INDEX[image[0], image[1]])
    return tuple(result)


_EDGE_PERMUTATIONS = tuple(
    _edge_permutation(element) for element in range(_S5_ORDER)
)


def _edge_orbit_sizes(subgroup: _Subgroup) -> tuple[int, ...]:
    unseen = set(range(_EDGE_COUNT))
    sizes: list[int] = []
    while unseen:
        seed = min(unseen)
        orbit = {_EDGE_PERMUTATIONS[element][seed] for element in subgroup}
        unseen -= orbit
        sizes.append(len(orbit))
    return tuple(sorted(sizes))


def _fixed_count(subgroup: _Subgroup, total: int) -> int:
    coefficients = [1] + [0] * total
    for orbit_size in _edge_orbit_sizes(subgroup):
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            value_mass = 0
            while degree + value_mass * orbit_size <= total:
                multiplicity = comb(
                    value_mass + _EDGE_COMPONENTS - 1,
                    _EDGE_COMPONENTS - 1,
                )
                next_coefficients[degree + value_mass * orbit_size] += (
                    coefficient * multiplicity
                )
                value_mass += 1
        coefficients = next_coefficients
    return coefficients[total]


def _exact_stabilizer_assignments(total: int) -> dict[_Subgroup, int]:
    exact: dict[_Subgroup, int] = {}
    for subgroup in _subgroups():
        strict_supergroups = (
            count
            for supergroup, count in exact.items()
            if subgroup < supergroup
        )
        exact[subgroup] = _fixed_count(subgroup, total) - sum(
            strict_supergroups
        )
    assert all(count >= 0 for count in exact.values())
    return exact


def _orbit_count_by_order(total: int) -> dict[int, int]:
    assignments = _exact_stabilizer_assignments(total)
    by_order: Counter[int] = Counter()
    for subgroup, count in assignments.items():
        by_order[len(subgroup)] += count
    return {
        order: count * order // _S5_ORDER
        for order, count in by_order.items()
        if count != 0
    }


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _edge_values_from_vector(vector: _Vector) -> _EdgeValues:
    values = tuple(
        tuple(vector[index : index + _EDGE_COMPONENTS])
        for index in range(0, _SCALAR_COMPONENTS, _EDGE_COMPONENTS)
    )
    assert all(len(value) == _EDGE_COMPONENTS for value in values)
    return tuple((value[0], value[1], value[2], value[3]) for value in values)


def _permute(edge_values: _EdgeValues, element: int) -> _EdgeValues:
    permutation = _EDGE_PERMUTATIONS[element]
    return tuple(edge_values[index] for index in permutation)


def _direct_order_spectrum(total: int) -> dict[int, int]:
    representatives: dict[_EdgeValues, int] = {}
    for vector in _weak_compositions(total, _SCALAR_COMPONENTS):
        edge_values = _edge_values_from_vector(vector)
        orbit = {_permute(edge_values, element) for element in range(_S5_ORDER)}
        representative = min(orbit)
        if representative in representatives:
            continue
        stabilizer_order = sum(
            _permute(representative, element) == representative
            for element in range(_S5_ORDER)
        )
        representatives[representative] = stabilizer_order
    return dict(Counter(representatives.values()))


def test_s6_s5_widened_stabilizer_lattice_has_156_subgroups() -> None:
    """The same complete S5 subgroup lattice governs widened edge values."""
    assert len(_subgroups()) == _SUBGROUP_COUNT


def test_s6_s5_widened_mass_fourteen_exact_stabilizer_spectrum() -> None:
    """Mass fourteen has the exact widened full-S5 stabilizer-order spectrum."""
    spectrum = _orbit_count_by_order(_MAXIMUM_MASS)
    assert spectrum == _EXPECTED_ORDER_SPECTRUM
    assert sum(spectrum.values()) == _WIDTH_FOURTEEN_CLASSES
    assert spectrum[1] == _WIDTH_FOURTEEN_TRIVIAL_CLASSES


def test_s6_s5_widened_stabilizer_inversion_reconstructs_edge_core() -> None:
    """Exact-stabilizer strata reconstruct every checked full-S5 edge count."""
    observed = tuple(
        sum(_orbit_count_by_order(total).values())
        for total in range(_MAXIMUM_MASS + 1)
    )
    assert observed == _EXPECTED_COUNTS


def test_s6_s5_widened_stabilizers_match_direct_small_orbits() -> None:
    """Direct S5 edge orbits agree with lattice inversion through mass two."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        assert _orbit_count_by_order(total) == _direct_order_spectrum(total)
