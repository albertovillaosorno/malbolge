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
#   - Dense rank/unrank for the all-distinct spoke stratum of S6 (5,1)/(4,1).
# - Must-Not:
#   - Claim ranking for nontrivial S4 spoke stabilizers.
# - Allows:
#   - Inputs: widened S4 spoke/K4-edge mass zero through fourteen.
#   - Outputs: dense canonical ranks for distinct four-component spokes.
#   - Side effects: none.
# - Split-When:
#   - Another spoke stabilizer receives constructive rank/unrank.
# - Merge-When:
#   - Complete dense ranking owns the full S6 (5,1)/(4,1) edge slice.
# - Summary:
#   - Distinct spokes orient S4, leaving twenty-four labelled edge scalars.
# - Description:
#   - Strict combinadics rank spokes; weak compositions rank the K4 edges.
# - Usage:
#   - First constructive spoke stratum beneath the S6 (5,1)/(4,1) factorization.
# - Defaults:
#   - Dense exhaustion stops at mass five; checked roundtrips reach mass
#     fourteen.
#

"""Dense distinct-spoke ranking inside the S6 (5,1)/(4,1) stratum."""

from __future__ import annotations

from functools import cache
from itertools import permutations
from math import comb

_ACTIVE = tuple(range(4))
_SPOKE_COUNT = 4
_SPOKE_COMPONENTS = 4
_EDGE_COMPONENTS = 4
_EDGE_COUNT = 6
_EDGE_SCALARS = _EDGE_COMPONENTS * _EDGE_COUNT
_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 5
_SAMPLE_LIMIT = 5
_MINIMUM_MASS_COUNT = 4
_WIDTH_FOURTEEN_COUNT = 53_942_379_546
_EXPECTED_COUNTS = {
    3: 4,
    4: 157,
    5: 3_004,
    6: 38_340,
    7: 371_536,
    8: 2_933_147,
    9: 19_711_788,
    10: 116_176_354,
    11: 613_489_840,
    12: 2_949_599_617,
    13: 13_073_057_984,
    14: 53_942_379_546,
}
_K4_EDGES = tuple(
    (left, right) for left in _ACTIVE for right in _ACTIVE if left < right
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_K4_EDGES)}
_S4 = tuple(permutations(_ACTIVE))

type _Vector = tuple[int, ...]
type _Quadruple = tuple[int, int, int, int]
type _Spokes = tuple[_Vector, _Vector, _Vector, _Vector]
type _Edges = tuple[_Vector, _Vector, _Vector, _Vector, _Vector, _Vector]
type _State = tuple[_Spokes, _Edges]


def _composition_count(total: int, parts: int) -> int:
    if total < 0 or parts <= 0:
        return 0
    return comb(total + parts - 1, parts - 1)


def _composition_rank(vector: _Vector, parts: int) -> int | None:
    if len(vector) != parts or any(value < 0 for value in vector):
        return None
    remaining = sum(vector)
    rank = 0
    for index, value in enumerate(vector[:-1]):
        tail = parts - index - 1
        rank += sum(
            _composition_count(remaining - earlier, tail)
            for earlier in range(value)
        )
        remaining -= value
    return rank


def _composition_unrank(total: int, parts: int, rank: int) -> _Vector | None:
    if rank < 0 or rank >= _composition_count(total, parts):
        return None
    remaining = total
    residual_rank = rank
    result: list[int] = []
    for index in range(parts - 1):
        tail = parts - index - 1
        for value in range(remaining + 1):
            block = _composition_count(remaining - value, tail)
            if residual_rank >= block:
                residual_rank -= block
                continue
            result.append(value)
            remaining -= value
            break
    result.append(remaining)
    return tuple(result)


def _strict_rank(values: tuple[int, ...], population: int) -> int:
    rank = 0
    previous = -1
    for index, value in enumerate(values):
        remaining = len(values) - index - 1
        rank += sum(
            comb(population - candidate - 1, remaining)
            for candidate in range(previous + 1, value)
        )
        previous = value
    return rank


def _strict_unrank(population: int, size: int, rank: int) -> tuple[int, ...]:
    assert 0 <= rank < comb(population, size)
    result: list[int] = []
    previous = -1
    remaining_rank = rank
    for index in range(size):
        remaining = size - index - 1
        for candidate in range(previous + 1, population):
            block = comb(population - candidate - 1, remaining)
            if remaining_rank >= block:
                remaining_rank -= block
                continue
            result.append(candidate)
            previous = candidate
            break
    return tuple(result)


def _spoke_key(spoke: _Vector) -> tuple[int, int]:
    rank = _composition_rank(spoke, _SPOKE_COMPONENTS)
    assert rank is not None
    return sum(spoke), rank


def _as_quadruple(values: tuple[int, ...]) -> _Quadruple:
    assert len(values) == _SPOKE_COUNT
    first, second, third, fourth = values
    return first, second, third, fourth


def _mass_quadruples(total: int) -> tuple[tuple[int, int, int, int], ...]:
    return tuple(
        (first, second, third, total - first - second - third)
        for first in range(total + 1)
        for second in range(first, total + 1)
        for third in range(second, total + 1)
        if third <= total - first - second - third
    )


def _mass_groups(
    masses: tuple[int, int, int, int],
) -> tuple[tuple[int, int], ...]:
    result: list[tuple[int, int]] = []
    start = 0
    while start < _SPOKE_COUNT:
        end = start + 1
        while end < _SPOKE_COUNT and masses[end] == masses[start]:
            end += 1
        result.append((start, end))
        start = end
    return tuple(result)


def _spoke_block_count(masses: tuple[int, int, int, int]) -> int:
    result = 1
    for start, end in _mass_groups(masses):
        population = _composition_count(masses[start], _SPOKE_COMPONENTS)
        result *= comb(population, end - start)
    return result


@cache
def _spoke_count(total: int) -> int:
    return sum(_spoke_block_count(masses) for masses in _mass_quadruples(total))


def _ordered_spoke_data(
    spokes: _Spokes,
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]] | None:
    valid = all(len(spoke) == _SPOKE_COMPONENTS for spoke in spokes)
    valid = valid and all(value >= 0 for spoke in spokes for value in spoke)
    if not valid:
        return None
    ordered = sorted(_spoke_key(spoke) for spoke in spokes)
    if len(set(ordered)) != _SPOKE_COUNT:
        return None
    masses = _as_quadruple(tuple(item[0] for item in ordered))
    ranks = _as_quadruple(tuple(item[1] for item in ordered))
    return masses, ranks


def _spoke_local_rank(
    masses: tuple[int, int, int, int],
    ranks: tuple[int, int, int, int],
) -> int:
    result = 0
    for start, end in _mass_groups(masses):
        population = _composition_count(masses[start], _SPOKE_COMPONENTS)
        count = comb(population, end - start)
        result *= count
        result += _strict_rank(ranks[start:end], population)
    return result


def _spoke_rank(spokes: _Spokes) -> int | None:
    data = _ordered_spoke_data(spokes)
    if data is None:
        return None
    masses, ranks = data
    prefix = sum(
        _spoke_block_count(candidate)
        for candidate in _mass_quadruples(sum(masses))
        if candidate < masses
    )
    return prefix + _spoke_local_rank(masses, ranks)


def _group_ranks(
    masses: tuple[int, int, int, int],
    rank: int,
) -> tuple[int, ...]:
    groups = _mass_groups(masses)
    counts = tuple(
        comb(
            _composition_count(masses[start], _SPOKE_COMPONENTS),
            end - start,
        )
        for start, end in groups
    )
    remaining = rank
    result: list[int] = []
    for count in reversed(counts):
        remaining, local = divmod(remaining, count)
        result.append(local)
    assert remaining == 0
    return tuple(reversed(result))


def _as_spokes(values: tuple[_Vector, ...]) -> _Spokes:
    assert len(values) == _SPOKE_COUNT
    first, second, third, fourth = values
    return first, second, third, fourth


def _spoke_block_unrank(
    masses: tuple[int, int, int, int],
    rank: int,
) -> _Spokes:
    result: list[_Vector] = []
    group_ranks = _group_ranks(masses, rank)
    for (start, end), group_rank in zip(
        _mass_groups(masses), group_ranks, strict=True
    ):
        mass = masses[start]
        population = _composition_count(mass, _SPOKE_COMPONENTS)
        raw_ranks = _strict_unrank(population, end - start, group_rank)
        for raw_rank in raw_ranks:
            spoke = _composition_unrank(mass, _SPOKE_COMPONENTS, raw_rank)
            assert spoke is not None
            result.append(spoke)
    return _as_spokes(tuple(result))


def _spoke_unrank(total: int, rank: int) -> _Spokes | None:
    if rank < 0 or rank >= _spoke_count(total):
        return None
    remaining = rank
    for masses in _mass_quadruples(total):
        block = _spoke_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        return _spoke_block_unrank(masses, remaining)
    raise AssertionError


def _ordered_edge(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def _as_edges(values: tuple[_Vector, ...]) -> _Edges:
    assert len(values) == _EDGE_COUNT
    first, second, third, fourth, fifth, sixth = values
    return first, second, third, fourth, fifth, sixth


def _edge_vector(edges: _Edges) -> _Vector | None:
    if not all(len(edge) == _EDGE_COMPONENTS for edge in edges):
        return None
    vector = tuple(value for edge in edges for value in edge)
    return vector if all(value >= 0 for value in vector) else None


def _edges_from_vector(vector: _Vector) -> _Edges:
    assert len(vector) == _EDGE_SCALARS
    return _as_edges(
        tuple(
            vector[index : index + _EDGE_COMPONENTS]
            for index in range(0, _EDGE_SCALARS, _EDGE_COMPONENTS)
        )
    )


def _spoke_order(spokes: _Spokes) -> tuple[int, int, int, int] | None:
    keyed = sorted(
        (_spoke_key(spoke), index) for index, spoke in enumerate(spokes)
    )
    if len({key for key, _ in keyed}) != _SPOKE_COUNT:
        return None
    indices = tuple(index for _, index in keyed)
    first, second, third, fourth = indices
    return first, second, third, fourth


def _reorder_edges(
    edges: _Edges,
    order: tuple[int, int, int, int],
) -> _Edges:
    return _as_edges(
        tuple(
            edges[_EDGE_INDEX[_ordered_edge(order[left], order[right])]]
            for left, right in _K4_EDGES
        )
    )


def _canonical_state(state: _State) -> _State | None:
    spokes, edges = state
    order = _spoke_order(spokes)
    vector = _edge_vector(edges)
    if order is None or vector is None:
        return None
    canonical_spokes = _as_spokes(tuple(spokes[index] for index in order))
    return canonical_spokes, _reorder_edges(edges, order)


@cache
def _class_count(total: int) -> int:
    return sum(
        _spoke_count(spoke_mass)
        * _composition_count(total - spoke_mass, _EDGE_SCALARS)
        for spoke_mass in range(total + 1)
    )


def _class_rank(total: int, state: _State) -> int | None:
    canonical = _canonical_state(state)
    if canonical is None:
        return None
    spokes, edges = canonical
    spoke_mass = sum(sum(spoke) for spoke in spokes)
    edge_vector = _edge_vector(edges)
    assert edge_vector is not None
    edge_mass = sum(edge_vector)
    if spoke_mass + edge_mass != total:
        return None
    spoke_rank = _spoke_rank(spokes)
    edge_rank = _composition_rank(edge_vector, _EDGE_SCALARS)
    assert spoke_rank is not None
    assert edge_rank is not None
    prefix = sum(
        _spoke_count(mass) * _composition_count(total - mass, _EDGE_SCALARS)
        for mass in range(spoke_mass)
    )
    return (
        prefix
        + spoke_rank * _composition_count(edge_mass, _EDGE_SCALARS)
        + edge_rank
    )


def _class_unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for spoke_mass in range(total + 1):
        edge_mass = total - spoke_mass
        edge_count = _composition_count(edge_mass, _EDGE_SCALARS)
        block = _spoke_count(spoke_mass) * edge_count
        if remaining >= block:
            remaining -= block
            continue
        spoke_rank, edge_rank = divmod(remaining, edge_count)
        spokes = _spoke_unrank(spoke_mass, spoke_rank)
        edge_vector = _composition_unrank(
            edge_mass,
            _EDGE_SCALARS,
            edge_rank,
        )
        assert spokes is not None
        assert edge_vector is not None
        return spokes, _edges_from_vector(edge_vector)
    raise AssertionError


def _inverse_order(order: tuple[int, ...]) -> tuple[int, int, int, int]:
    inverse = tuple(order.index(destination) for destination in _ACTIVE)
    first, second, third, fourth = inverse
    return first, second, third, fourth


def _permute_state(state: _State, order: tuple[int, ...]) -> _State:
    spokes, edges = state
    inverse = _inverse_order(order)
    permuted_spokes = _as_spokes(
        tuple(spokes[inverse[destination]] for destination in _ACTIVE)
    )
    permuted_edges = _as_edges(
        tuple(
            edges[_EDGE_INDEX[_ordered_edge(inverse[left], inverse[right])]]
            for left, right in _K4_EDGES
        )
    )
    return permuted_spokes, permuted_edges


def _sample_ranks(count: int) -> tuple[int, ...]:
    if count <= _SAMPLE_LIMIT:
        return tuple(range(count))
    return 0, 1, count // 2, count - 2, count - 1


def test_s6_s5_s4_distinct_spoke_rank_is_s4_invariant() -> None:
    """Unique spoke ordering gives one rank to every residual S4 orbit."""
    total = 3
    assert _class_count(total) == _MINIMUM_MASS_COUNT
    for rank in range(_class_count(total)):
        state = _class_unrank(total, rank)
        assert state is not None
        assert {
            _class_rank(total, _permute_state(state, order)) for order in _S4
        } == {rank}


def test_s6_s5_s4_distinct_spoke_rank_exhausts_small_domains() -> None:
    """Every small distinct-spoke class has exactly one dense rank."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        count = _class_count(total)
        observed = {
            _class_rank(total, state)
            for rank in range(count)
            if (state := _class_unrank(total, rank)) is not None
        }
        assert observed == set(range(count))


def test_s6_s5_s4_distinct_spoke_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior ranks invert through the maximum checked mass."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        for rank in _sample_ranks(count):
            state = _class_unrank(total, rank)
            assert state is not None
            assert _class_rank(total, state) == rank
        assert _class_unrank(total, count) is None
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT


def test_s6_s5_s4_distinct_spoke_counts_match_reviewed_sequence() -> None:
    """Distinct-spoke counts agree with the independent S4 decomposition."""
    observed = {
        total: _class_count(total)
        for total in range(_MAXIMUM_MASS + 1)
        if _class_count(total)
    }
    assert observed == _EXPECTED_COUNTS
