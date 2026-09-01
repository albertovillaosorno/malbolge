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
#   - Exact automorphism-stabilizer spectrum for the full-S5 edge hard core.
# - Must-Not:
#   - Claim dense order-120 rank/unrank from stabilizer counts alone.
# - Allows:
#   - Inputs: pair-valued K5 edge assignments of residual mass 0 through 14.
#   - Outputs: exact subgroup fixed/stabilizer counts and orbit counts.
#   - Side effects: none.
# - Split-When:
#   - A constructive dense rank consumes individual stabilizer strata.
# - Merge-When:
#   - Complete dense S5 ranking owns the same subgroup-lattice decomposition.
# - Summary:
#   - Mobius-invert all 156 S5 subgroups to isolate exact automorphisms.
# - Description:
#   - Counts subgroup-fixed edge assignments from edge orbits, then subtracts
#     all strict supergroup-fixed strata in descending subgroup order.
# - Usage:
#   - Quantifies the generic rooted-rank path and every symmetric exception.
# - Defaults:
#   - Full subgroup arithmetic is checked at mass 14; direct orbits stop at 3.
#

"""Exact full-S5 edge automorphism stabilizer spectrum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import permutations
from math import factorial

_ARITY = 5
_EDGE_COUNT = 10
_EXHAUSTIVE_MASS = 3
_MAXIMUM_MASS = 14
_S5_ORDER = factorial(_ARITY)
_SUBGROUP_COUNT = 156
_SUBGROUP_CONJUGACY_CLASS_COUNT = 19
_WIDTH_FOURTEEN_CLASSES = 6_962_786
_WIDTH_FOURTEEN_ROOTED_CLASSES = 34_507_258
_WIDTH_FOURTEEN_TRIVIAL_CLASSES = 6_689_862
_EDGES = tuple(
    (left, right)
    for left in range(_ARITY)
    for right in range(left + 1, _ARITY)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_PERMUTATIONS = tuple(permutations(range(_ARITY)))
_PERMUTATION_INDEX = {
    order: index for index, order in enumerate(_PERMUTATIONS)
}
_IDENTITY = _PERMUTATION_INDEX[tuple(range(_ARITY))]
_EXPECTED_ORDER_SPECTRUM = {
    1: 6_689_862,
    2: 261_576,
    4: 10_660,
    6: 402,
    8: 106,
    12: 174,
    24: 6,
}
_EXPECTED_CONJUGACY_SPECTRUM = {
    (1, (1, 1, 1, 1, 1), (1,) * 10): 6_689_862,
    (2, (2, 1, 1, 1), (1, 1, 1, 1, 2, 2, 2)): 239_656,
    (2, (2, 2, 1), (1, 1, 2, 2, 2, 2)): 21_920,
    (4, (4, 1), (2, 2, 2, 4)): 194,
    (4, (2, 2, 1), (1, 1, 2, 2, 4)): 10_466,
    (6, (3, 1, 1), (1, 3, 3, 3)): 402,
    (8, (4, 1), (2, 4, 4)): 106,
    (12, (3, 2), (1, 3, 6)): 174,
    (24, (4, 1), (4, 6)): 6,
}

type _EdgePairs = tuple[tuple[int, int], ...]
type _Subgroup = frozenset[int]


def _compose(left: int, right: int) -> int:
    first = _PERMUTATIONS[left]
    second = _PERMUTATIONS[right]
    result = tuple(first[second[index]] for index in range(_ARITY))
    return _PERMUTATION_INDEX[result]


_MULTIPLICATION = tuple(
    tuple(_compose(left, right) for right in range(_S5_ORDER))
    for left in range(_S5_ORDER)
)


def _inverse(element: int) -> int:
    order = _PERMUTATIONS[element]
    result = [0] * _ARITY
    for source, destination in enumerate(order):
        result[destination] = source
    return _PERMUTATION_INDEX[tuple(result)]


def _closure_step(
    subgroup: set[int],
    generators: tuple[int, ...],
) -> set[int]:
    additions: set[int] = set()
    for left in subgroup:
        for right in generators:
            additions.update(
                (
                    _MULTIPLICATION[left][right],
                    _MULTIPLICATION[right][left],
                )
            )
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


def _vertex_orbit_sizes(subgroup: _Subgroup) -> tuple[int, ...]:
    unseen = set(range(_ARITY))
    sizes: list[int] = []
    while unseen:
        seed = min(unseen)
        orbit = {_PERMUTATIONS[element][seed] for element in subgroup}
        unseen -= orbit
        sizes.append(len(orbit))
    return tuple(sorted(sizes, reverse=True))


def _fixed_count(subgroup: _Subgroup, total: int) -> int:
    coefficients = [1] + [0] * total
    for orbit_size in _edge_orbit_sizes(subgroup):
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            multiplier = 0
            while degree + multiplier * orbit_size <= total:
                next_coefficients[degree + multiplier * orbit_size] += (
                    coefficient * (multiplier + 1)
                )
                multiplier += 1
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


def _conjugate(subgroup: _Subgroup, element: int) -> _Subgroup:
    inverse = _inverse(element)
    return frozenset(
        _MULTIPLICATION[_MULTIPLICATION[element][member]][inverse]
        for member in subgroup
    )


def _subgroup_conjugacy_classes() -> tuple[tuple[_Subgroup, ...], ...]:
    unseen = set(_subgroups())
    result: list[tuple[_Subgroup, ...]] = []
    while unseen:
        subgroup = next(iter(unseen))
        conjugates = {_conjugate(subgroup, element) for element in range(120)}
        result.append(tuple(conjugates))
        unseen -= conjugates
    return tuple(result)


def _conjugacy_spectrum(total: int) -> dict[tuple[object, ...], int]:
    exact = _exact_stabilizer_assignments(total)
    result: dict[tuple[object, ...], int] = {}
    for conjugacy_class in _subgroup_conjugacy_classes():
        subgroup = conjugacy_class[0]
        assignments = sum(exact[member] for member in conjugacy_class)
        if assignments == 0:
            continue
        key = (
            len(subgroup),
            _vertex_orbit_sizes(subgroup),
            _edge_orbit_sizes(subgroup),
        )
        result[key] = assignments * len(subgroup) // _S5_ORDER
    return result


def _rooted_class_count(total: int) -> int:
    exact = _exact_stabilizer_assignments(total)
    numerator = sum(
        count * len(subgroup) * len(_vertex_orbit_sizes(subgroup))
        for subgroup, count in exact.items()
    )
    assert numerator % _S5_ORDER == 0
    return numerator // _S5_ORDER


def _visit_assignments(
    index: int,
    remaining: int,
    prefix: list[tuple[int, int]],
    *,
    result: list[_EdgePairs],
) -> None:
    if index == _EDGE_COUNT:
        if remaining == 0:
            result.append(tuple(prefix))
        return
    for left in range(remaining + 1):
        for right in range(remaining - left + 1):
            prefix.append((left, right))
            _visit_assignments(
                index + 1,
                remaining - left - right,
                prefix,
                result=result,
            )
            _ = prefix.pop()


def _assignments(total: int) -> tuple[_EdgePairs, ...]:
    result: list[_EdgePairs] = []
    _visit_assignments(0, total, [], result=result)
    return tuple(result)


def _permute(edge_pairs: _EdgePairs, element: int) -> _EdgePairs:
    permutation = _EDGE_PERMUTATIONS[element]
    return tuple(edge_pairs[index] for index in permutation)


def _direct_order_spectrum(total: int) -> dict[int, int]:
    representatives: dict[_EdgePairs, int] = {}
    for edge_pairs in _assignments(total):
        orbit = {_permute(edge_pairs, element) for element in range(_S5_ORDER)}
        representative = min(orbit)
        if representative in representatives:
            continue
        stabilizer_order = sum(
            _permute(representative, element) == representative
            for element in range(_S5_ORDER)
        )
        representatives[representative] = stabilizer_order
    return dict(Counter(representatives.values()))


def test_s5_has_exactly_156_subgroups_in_19_conjugacy_classes() -> None:
    """The finite subgroup lattice used by inversion is complete."""
    assert len(_subgroups()) == _SUBGROUP_COUNT
    assert len(_subgroup_conjugacy_classes()) == _SUBGROUP_CONJUGACY_CLASS_COUNT


def test_s5_mass_fourteen_exact_stabilizer_spectrum() -> None:
    """Mass 14 has the exact reviewed generic and symmetric orbit strata."""
    spectrum = _orbit_count_by_order(_MAXIMUM_MASS)
    assert spectrum == _EXPECTED_ORDER_SPECTRUM
    assert sum(spectrum.values()) == _WIDTH_FOURTEEN_CLASSES
    assert spectrum[1] == _WIDTH_FOURTEEN_TRIVIAL_CLASSES
    assert _conjugacy_spectrum(_MAXIMUM_MASS) == _EXPECTED_CONJUGACY_SPECTRUM


def test_s5_stabilizer_inversion_reconstructs_rooted_s4_count() -> None:
    """Vertex-orbit weighting recovers the independently proved rooted count."""
    assert _rooted_class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_ROOTED_CLASSES


def test_s5_exact_stabilizers_match_direct_small_orbits() -> None:
    """Direct S5 edge orbits agree with lattice inversion through mass three."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        assert _orbit_count_by_order(total) == _direct_order_spectrum(total)


_EXPECTED_ROOTED_VIEW_SPECTRUM = {
    2: 480,
    3: 32_788,
    4: 239_656,
    5: 6_689_862,
}


def _rooted_representative(edge_pairs: _EdgePairs, root: int) -> _EdgePairs:
    return min(
        _permute(edge_pairs, element)
        for element, order in enumerate(_PERMUTATIONS)
        if order[_ARITY - 1] == root
    )


def _stabilizer(edge_pairs: _EdgePairs) -> _Subgroup:
    return frozenset(
        element
        for element in range(_S5_ORDER)
        if _permute(edge_pairs, element) == edge_pairs
    )


def _rooted_view_spectrum(total: int) -> dict[int, int]:
    exact = _exact_stabilizer_assignments(total)
    numerators: Counter[int] = Counter()
    for subgroup, count in exact.items():
        if count == 0:
            continue
        vertex_orbits = len(_vertex_orbit_sizes(subgroup))
        numerators[vertex_orbits] += count * len(subgroup)
    assert all(value % _S5_ORDER == 0 for value in numerators.values())
    return {
        vertex_orbits: value // _S5_ORDER
        for vertex_orbits, value in numerators.items()
    }


def test_s5_rooted_views_equal_automorphism_vertex_orbits() -> None:
    """Rooted-view collisions occur exactly between automorphic vertices."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        seen: set[_EdgePairs] = set()
        for edge_pairs in _assignments(total):
            representative = min(
                _permute(edge_pairs, element)
                for element in range(_S5_ORDER)
            )
            if representative in seen:
                continue
            seen.add(representative)
            rooted_views = {
                _rooted_representative(representative, root)
                for root in range(_ARITY)
            }
            assert len(rooted_views) == len(
                _vertex_orbit_sizes(_stabilizer(representative))
            )


def test_s5_mass_fourteen_rooted_view_multiplicity_spectrum() -> None:
    """Mass 14 rooted-view multiplicities reconstruct the rooted quotient."""
    spectrum = _rooted_view_spectrum(_MAXIMUM_MASS)
    assert spectrum == _EXPECTED_ROOTED_VIEW_SPECTRUM
    assert sum(spectrum.values()) == _WIDTH_FOURTEEN_CLASSES
    assert sum(
        views * count for views, count in spectrum.items()
    ) == _WIDTH_FOURTEEN_ROOTED_CLASSES
    assert spectrum[_ARITY] == _WIDTH_FOURTEEN_TRIVIAL_CLASSES
