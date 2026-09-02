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
#   - Dense rank/unrank for the five bounded widened symmetric S5 strata.
# - Must-Not:
#   - Rank the large order-2, transitive-V4, or trivial-stabilizer strata.
# - Allows:
#   - Inputs: four-component K5 edges with five exact stabilizers through
#     mass fourteen.
#   - Outputs: dense ranks modulo the corresponding normalizer quotient.
#   - Side effects: none.
# - Split-When:
#   - A stabilizer stratum needs a specialized non-table rank construction.
# - Merge-When:
#   - Complete dense S5 ranking owns all exact-stabilizer strata.
# - Summary:
#   - Canonicalize H-edge-orbit values under N(H)/H, then filter exact H.
# - Description:
#   - Every remaining symmetric stratum is a finite weighted orbit-value domain.
# - Usage:
#   - Constructive coverage for five bounded widened S5 stabilizer exceptions.
# - Defaults:
#   - Direct S5 orbit exhaustion stops at mass two; arithmetic reaches 14.
#

"""Dense ranking for five bounded widened exact-S5 stabilizer strata."""

from __future__ import annotations

from bisect import bisect_left
from functools import cache
from itertools import permutations
from operator import itemgetter

_ARITY = 5
_EDGE_COUNT = 10
_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 2
_EXHAUSTIVE_RANK_MASS = 6

type _Value = tuple[int, int, int, int]
type _Permutation = tuple[int, int, int, int, int]
type _Group = frozenset[_Permutation]
type _OrbitState = tuple[_Value, ...]
type _EdgeValues = tuple[_Value, ...]
type _Key = tuple[int, tuple[int, ...], tuple[int, ...]]


def _as_permutation(order: tuple[int, ...]) -> _Permutation:
    assert len(order) == _ARITY
    first, second, third, fourth, fifth = order
    return first, second, third, fourth, fifth


_S5: tuple[_Permutation, ...] = tuple(
    _as_permutation(order) for order in permutations(range(_ARITY))
)
_EDGES = tuple(
    (left, right) for left in range(_ARITY) for right in range(left + 1, _ARITY)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_IDENTITY: _Permutation = (0, 1, 2, 3, 4)
_EXPECTED_MASS_FOURTEEN = {
    (4, (4, 1), (2, 2, 2, 4)): (9_760, 7_992),
    (6, (3, 1, 1), (1, 3, 3, 3)): (29_632, 22_280),
    (8, (4, 1), (2, 4, 4)): (1_768, 1_728),
    (12, (3, 2), (1, 3, 6)): (7_312, 7_312),
    (24, (4, 1), (4, 6)): (40, 40),
}


def _cycle(*vertices: int) -> _Permutation:
    result = list(range(_ARITY))
    for source, destination in zip(
        vertices,
        (*vertices[1:], vertices[0]),
        strict=True,
    ):
        result[source] = destination
    first, second, third, fourth, fifth = result
    return first, second, third, fourth, fifth


def _compose(left: _Permutation, right: _Permutation) -> _Permutation:
    result = tuple(left[right[index]] for index in range(_ARITY))
    first, second, third, fourth, fifth = result
    return first, second, third, fourth, fifth


def _inverse(order: _Permutation) -> _Permutation:
    result = [0] * _ARITY
    for source, destination in enumerate(order):
        result[destination] = source
    first, second, third, fourth, fifth = result
    return first, second, third, fourth, fifth


def _closure_step(
    group: set[_Permutation],
    generators: tuple[_Permutation, ...],
) -> set[_Permutation]:
    additions: set[_Permutation] = set()
    for left in group:
        for right in generators:
            additions.update((_compose(left, right), _compose(right, left)))
    return additions - group


def _generated(*generators: _Permutation) -> _Group:
    group: set[_Permutation] = {_IDENTITY}
    additions = _closure_step(group, generators)
    while additions:
        group.update(additions)
        additions = _closure_step(group, generators)
    return frozenset(group)


def _conjugate(group: _Group, order: _Permutation) -> _Group:
    inverse = _inverse(order)
    return frozenset(
        _compose(_compose(order, member), inverse) for member in group
    )


def _normalizer(group: _Group) -> _Group:
    return frozenset(
        order for order in _S5 if _conjugate(group, order) == group
    )


def _edge_permutation(order: _Permutation) -> tuple[int, ...]:
    result: list[int] = []
    for left, right in _EDGES:
        image = tuple(sorted((order[left], order[right])))
        result.append(_EDGE_INDEX[image[0], image[1]])
    return tuple(result)


_EDGE_PERMUTATIONS = {_order: _edge_permutation(_order) for _order in _S5}


def _orbits(
    group: _Group,
    domain_size: int,
    permutations_by_order: dict[_Permutation, tuple[int, ...]],
) -> tuple[tuple[int, ...], ...]:
    unseen = set(range(domain_size))
    result: list[tuple[int, ...]] = []
    while unseen:
        seed = min(unseen)
        orbit = {permutations_by_order[order][seed] for order in group}
        unseen -= orbit
        result.append(tuple(sorted(orbit)))
    return tuple(sorted(result, key=lambda orbit: (len(orbit), orbit)))


def _vertex_orbit_sizes(group: _Group) -> tuple[int, ...]:
    permutations_by_order = {order: order for order in group}
    return tuple(
        sorted(
            (
                len(orbit)
                for orbit in _orbits(group, _ARITY, permutations_by_order)
            ),
            reverse=True,
        )
    )


def _edge_orbits(group: _Group) -> tuple[tuple[int, ...], ...]:
    return _orbits(group, _EDGE_COUNT, _EDGE_PERMUTATIONS)


def _key(group: _Group) -> _Key:
    return (
        len(group),
        _vertex_orbit_sizes(group),
        tuple(sorted(len(orbit) for orbit in _edge_orbits(group))),
    )


_SWAP_01 = _cycle(0, 1)
_SWAP_23 = _cycle(2, 3)
_SWAP_34 = _cycle(3, 4)
_CYCLE_012 = _cycle(0, 1, 2)
_CYCLE_0123 = _cycle(0, 1, 2, 3)
_REFLECT_13 = _cycle(1, 3)
_DOUBLE_01_23: _Permutation = (1, 0, 3, 2, 4)
_DOUBLE_02_13: _Permutation = (2, 3, 0, 1, 4)

_GROUPS = (
    _generated(_DOUBLE_01_23, _DOUBLE_02_13),
    _generated(_SWAP_01, _CYCLE_012),
    _generated(_CYCLE_0123, _REFLECT_13),
    _generated(_SWAP_01, _CYCLE_012, _SWAP_34),
    _generated(_CYCLE_0123, _SWAP_01),
)


@cache
def _representatives() -> tuple[tuple[_Key, _Group], ...]:
    rows = ((_key(group), group) for group in _GROUPS)
    return tuple(sorted(rows, key=itemgetter(0)))


def _edge_orbit_index(orbits: tuple[tuple[int, ...], ...]) -> tuple[int, ...]:
    result = [-1] * _EDGE_COUNT
    for orbit_index, orbit in enumerate(orbits):
        for edge in orbit:
            result[edge] = orbit_index
    assert all(index >= 0 for index in result)
    return tuple(result)


def _normalizer_maps(
    group: _Group,
    orbits: tuple[tuple[int, ...], ...],
    orbit_index: tuple[int, ...],
) -> tuple[tuple[int, ...], ...]:
    maps: set[tuple[int, ...]] = set()
    representatives = tuple(orbit[0] for orbit in orbits)
    for order in _normalizer(group):
        edge_permutation = _EDGE_PERMUTATIONS[order]
        mapping = tuple(
            orbit_index[edge_permutation[edge]] for edge in representatives
        )
        assert all(
            all(
                orbit_index[edge_permutation[edge]] == mapping[index]
                for edge in orbit
            )
            for index, orbit in enumerate(orbits)
        )
        maps.add(mapping)
    return tuple(sorted(maps))


@cache
def _values_of_mass(total: int) -> tuple[_Value, ...]:
    return tuple(
        (first, second, third, total - first - second - third)
        for first in range(total + 1)
        for second in range(total - first + 1)
        for third in range(total - first - second + 1)
    )


@cache
def _states_from(
    weights: tuple[int, ...],
    index: int,
    remaining: int,
) -> tuple[_OrbitState, ...]:
    if index == len(weights):
        return ((),) if remaining == 0 else ()
    weight = weights[index]
    result: list[_OrbitState] = []
    for value_mass in range(remaining // weight + 1):
        residual = remaining - weight * value_mass
        result.extend(
            (value, *suffix)
            for value in _values_of_mass(value_mass)
            for suffix in _states_from(weights, index + 1, residual)
        )
    return tuple(result)


@cache
def _fixed_states(key: _Key, total: int) -> tuple[_OrbitState, ...]:
    group = dict(_representatives())[key]
    weights = tuple(len(orbit) for orbit in _edge_orbits(group))
    return _states_from(weights, 0, total)


def _transform(state: _OrbitState, mapping: tuple[int, ...]) -> _OrbitState:
    return tuple(state[mapping[index]] for index in range(len(mapping)))


@cache
def _quotient_states(key: _Key, total: int) -> tuple[_OrbitState, ...]:
    group = dict(_representatives())[key]
    orbits = _edge_orbits(group)
    orbit_index = _edge_orbit_index(orbits)
    maps = _normalizer_maps(group, orbits, orbit_index)
    canonical = {
        min(_transform(state, mapping) for mapping in maps)
        for state in _fixed_states(key, total)
    }
    return tuple(sorted(canonical))


def _edge_values(key: _Key, state: _OrbitState) -> _EdgeValues:
    group = dict(_representatives())[key]
    orbit_index = _edge_orbit_index(_edge_orbits(group))
    return tuple(state[orbit_index[edge]] for edge in range(_EDGE_COUNT))


def _permute(edge_values: _EdgeValues, order: _Permutation) -> _EdgeValues:
    permutation = _EDGE_PERMUTATIONS[order]
    return tuple(edge_values[permutation[edge]] for edge in range(_EDGE_COUNT))


def _stabilizer(edge_values: _EdgeValues) -> _Group:
    return frozenset(
        order for order in _S5 if _permute(edge_values, order) == edge_values
    )


@cache
def _accepted_states(key: _Key, total: int) -> tuple[_OrbitState, ...]:
    group = dict(_representatives())[key]
    return tuple(
        state
        for state in _quotient_states(key, total)
        if _stabilizer(_edge_values(key, state)) == group
    )


def _rank(key: _Key, total: int, state: _OrbitState) -> int | None:
    accepted = _accepted_states(key, total)
    index = bisect_left(accepted, state)
    if index == len(accepted) or accepted[index] != state:
        return None
    return index


def _unrank(key: _Key, total: int, rank: int) -> _OrbitState | None:
    accepted = _accepted_states(key, total)
    if rank < 0 or rank >= len(accepted):
        return None
    return accepted[rank]


def test_s6_s5_small_exception_keys_are_the_five_bounded_types() -> None:
    """The rank owns exactly the five bounded widened symmetric types."""
    observed = {key for key, _ in _representatives()}
    assert observed == set(_EXPECTED_MASS_FOURTEEN)


def test_s6_s5_small_exception_mass_fourteen_counts() -> None:
    """Every mass-14 normalizer quotient filters to its exact reviewed count."""
    for key, (quotient_count, exact_count) in _EXPECTED_MASS_FOURTEEN.items():
        assert len(_quotient_states(key, _MAXIMUM_MASS)) == quotient_count
        assert len(_accepted_states(key, _MAXIMUM_MASS)) == exact_count


def test_s6_s5_small_exception_rank_matches_direct_small_s5_orbits() -> None:
    """Each accepted state represents one direct S5 orbit through mass two."""
    for key, group in _representatives():
        for total in range(_EXHAUSTIVE_MASS + 1):
            seen: set[_EdgeValues] = set()
            for rank, state in enumerate(_accepted_states(key, total)):
                edge_values = _edge_values(key, state)
                assert _stabilizer(edge_values) == group
                representative = min(
                    _permute(edge_values, order) for order in _S5
                )
                assert representative not in seen
                seen.add(representative)
                assert _rank(key, total, state) == rank


def test_s6_s5_small_exception_rank_exhausts_small_domains() -> None:
    """Every accepted class through mass six receives one contiguous rank."""
    for key, _ in _representatives():
        for total in range(_EXHAUSTIVE_RANK_MASS + 1):
            for rank in range(len(_accepted_states(key, total))):
                state = _unrank(key, total, rank)
                assert state is not None
                assert _rank(key, total, state) == rank


def test_s6_s5_small_exception_rank_roundtrips_through_mass_fourteen() -> None:
    """Boundary and interior ranks roundtrip for all five types through 14."""
    for key, _ in _representatives():
        for total in range(_MAXIMUM_MASS + 1):
            count = len(_accepted_states(key, total))
            assert _unrank(key, total, -1) is None
            assert _unrank(key, total, count) is None
            if count == 0:
                continue
            for rank in {0, count // 2, count - 1}:
                state = _unrank(key, total, rank)
                assert state is not None
                assert _rank(key, total, state) == rank
