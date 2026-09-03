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
#   - Reusable exact subgroup enumeration for the natural S6 action.
# - Must-Not:
#   - Define optimization semantics or replace owning mathematical proofs.
# - Allows:
#   - Inputs: subgroup generators and the natural six-point permutation action.
#   - Outputs: 56 conjugacy representatives and 1,455 concrete subgroups.
#   - Side effects: none.
# - Split-When:
#   - Another group action needs an independent reusable lattice.
# - Merge-When:
#   - A repository-owned general finite-group lattice utility owns this role.
# - Summary:
#   - Share the reviewed S6 subgroup lattice across bounded mathematics proofs.
# - Description:
#   - Enumerates generated subgroups and their conjugates deterministically.
# - Usage:
#   - Imported by S6 mathematics evidence that needs concrete subgroup incidence.
# - Defaults:
#   - The action is fixed to S6 on six endpoints.
#

"""Reusable exact subgroup lattice for the natural six-point S6 action."""

from __future__ import annotations

from collections import deque
from functools import cache
from itertools import permutations
from typing import cast

_ARITY = 6
_GROUP_ORDER = 720

type Permutation = tuple[int, int, int, int, int, int]
type Subgroup = frozenset[int]

PERMUTATIONS = cast(
    "tuple[Permutation, ...]",
    tuple(permutations(range(_ARITY))),
)
_PERMUTATION_INDEX = {
    permutation: index for index, permutation in enumerate(PERMUTATIONS)
}
_IDENTITY = _PERMUTATION_INDEX[0, 1, 2, 3, 4, 5]
_MULTIPLICATION = tuple(
    tuple(
        _PERMUTATION_INDEX[
            cast(
                "Permutation",
                tuple(
                    PERMUTATIONS[left][PERMUTATIONS[right][index]]
                    for index in range(_ARITY)
                ),
            )
        ]
        for right in range(_GROUP_ORDER)
    )
    for left in range(_GROUP_ORDER)
)


def _inverse(element: int) -> int:
    permutation = PERMUTATIONS[element]
    result = [0] * _ARITY
    for source, destination in enumerate(permutation):
        result[destination] = source
    return _PERMUTATION_INDEX[cast("Permutation", tuple(result))]


_INVERSES = tuple(_inverse(element) for element in range(_GROUP_ORDER))


def _products(left: int, generators: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(
        product
        for right in generators
        for product in (
            _MULTIPLICATION[left][right],
            _MULTIPLICATION[right][left],
        )
    )


@cache
def _generated(generators: tuple[int, ...]) -> Subgroup:
    generators = tuple(sorted(set(generators)))
    subgroup = {_IDENTITY}
    frontier = deque([_IDENTITY])
    while frontier:
        left = frontier.popleft()
        for product in _products(left, generators):
            if product not in subgroup:
                subgroup.add(product)
                frontier.append(product)
    return frozenset(subgroup)


def _conjugate(subgroup: Subgroup, element: int) -> Subgroup:
    inverse = _INVERSES[element]
    return frozenset(
        _MULTIPLICATION[_MULTIPLICATION[element][item]][inverse]
        for item in subgroup
    )


@cache
def _canonical_subgroup(subgroup: Subgroup) -> Subgroup:
    canonical = min(
        tuple(sorted(_conjugate(subgroup, element)))
        for element in range(_GROUP_ORDER)
    )
    return frozenset(canonical)


@cache
def _subgroup_generators(subgroup: Subgroup) -> tuple[int, ...]:
    generators: list[int] = []
    generated = frozenset({_IDENTITY})
    for element in sorted(subgroup):
        if element in generated:
            continue
        generators.append(element)
        generated = _generated(tuple(generators))
        if generated == subgroup:
            break
    return tuple(generators)


@cache
def subgroup_conjugacy_classes() -> tuple[Subgroup, ...]:
    """Return the 56 conjugacy-class representatives of S6 subgroups.

    Returns:
        The canonical representative of each subgroup conjugacy class.

    """
    identity = _canonical_subgroup(frozenset({_IDENTITY}))
    known = {identity}
    frontier = [identity]
    while frontier:
        subgroup = frontier.pop()
        generators = _subgroup_generators(subgroup)
        for element in range(_GROUP_ORDER):
            if element in subgroup:
                continue
            candidate = _canonical_subgroup(_generated((*generators, element)))
            if candidate in known:
                continue
            known.add(candidate)
            frontier.append(candidate)
    return tuple(sorted(known, key=lambda group: (-len(group), tuple(group))))


@cache
def conjugates(subgroup: Subgroup) -> tuple[Subgroup, ...]:
    """Return every distinct S6 conjugate of one subgroup.

    Returns:
        Every subgroup obtained by conjugating with an S6 element.

    """
    return tuple({
        _conjugate(subgroup, element) for element in range(_GROUP_ORDER)
    })


@cache
def all_subgroups() -> tuple[Subgroup, ...]:
    """Return all 1,455 actual subgroups of S6 in ascending order.

    Returns:
        All concrete subgroups ordered first by group order.

    """
    return tuple(
        sorted(
            {
                subgroup
                for representative in subgroup_conjugacy_classes()
                for subgroup in conjugates(representative)
            },
            key=lambda subgroup: (len(subgroup), tuple(subgroup)),
        )
    )
