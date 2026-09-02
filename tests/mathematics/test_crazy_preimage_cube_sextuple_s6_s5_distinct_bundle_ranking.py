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
#   - Dense rank/unrank for the all-distinct second-layer (5,1) S6 slice.
# - Must-Not:
#   - Claim ranking for nontrivial second-layer S5 stabilizers.
# - Allows:
#   - Inputs: sextuple mass zero through fourteen in this nested trivial
#     stratum.
#   - Outputs: dense ranks after unique ordering of five two-component bundles.
#   - Side effects: none.
# - Split-When:
#   - Another second-layer stabilizer receives constructive rank/unrank.
# - Merge-When:
#   - Complete dense ranking owns the full (5,1) S6 stratum.
# - Summary:
#   - Distinct vertex bundles orient S5, leaving 40 labeled edge scalars.
# - Description:
#   - Prefix bundle masses and strict combinadics, then rank edge compositions.
# - Usage:
#   - Largest constructive second-layer slice of the (5,1) S6 stratum.
# - Defaults:
#   - Full rank exhaustion stops at mass seven; boundary checks reach mass 14.
#

"""Dense all-distinct second-layer ranking for the S6 (5,1) stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import permutations
from math import comb

_ARITY = 6
_ACTIVE_COUNT = 5
_ACTIVE = tuple(range(_ACTIVE_COUNT))
_FIXED_COMPONENTS = 2
_VERTEX_COMPONENTS = 2
_EDGE_COMPONENTS = 4
_EDGE_COUNT = 10
_EDGE_SCALARS = _EDGE_COMPONENTS * _EDGE_COUNT
_MAXIMUM_MASS = 14
_EXHAUSTIVE_FULL_MASS = 7
_EXHAUSTIVE_ORBIT_MASS = 3
_TOP_PARTITION = (5, 1)
_WIDTH_FOURTEEN_COUNT = 1_124_927_130
_EXPECTED_COUNTS = {
    7: 6,
    8: 289,
    9: 7_118,
    10: 119_456,
    11: 1_535_898,
    12: 16_129_864,
    13: 144_057_980,
    14: 1_124_927_130,
}
_K5_EDGES = tuple(
    (left, right) for left in _ACTIVE for right in _ACTIVE if left < right
)
_K5_EDGE_INDEX = {edge: index for index, edge in enumerate(_K5_EDGES)}
_S5 = tuple(permutations(_ACTIVE))

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Vector = tuple[int, ...]
type _Bundles = tuple[_Vector, _Vector, _Vector, _Vector, _Vector]
type _Edges = tuple[
    _Vector,
    _Vector,
    _Vector,
    _Vector,
    _Vector,
    _Vector,
    _Vector,
    _Vector,
    _Vector,
    _Vector,
]
type _Residual = tuple[_Vector, _Bundles, _Edges]
type _State = tuple[_Vertices, _Residual]

_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)


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
            _composition_count(remaining - earlier, tail) for earlier in range(value)
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


def _strict_combination_rank(values: tuple[int, ...], population: int) -> int:
    assert tuple(sorted(values)) == values
    assert len(set(values)) == len(values)
    rank = 0
    previous = -1
    for index, value in enumerate(values):
        remaining = len(values) - index - 1
        for candidate in range(previous + 1, value):
            rank += comb(population - candidate - 1, remaining)
        previous = value
    return rank


def _strict_combination_unrank(
    population: int,
    size: int,
    rank: int,
) -> tuple[int, ...]:
    assert 0 <= rank < comb(population, size)
    remaining_rank = rank
    previous = -1
    result: list[int] = []
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


def _raw_bundle_count(total: int) -> int:
    return _composition_count(total, _VERTEX_COMPONENTS)


def _bundle_key(bundle: _Vector) -> tuple[int, int]:
    mass = sum(bundle)
    rank = _composition_rank(bundle, _VERTEX_COMPONENTS)
    assert rank is not None
    return mass, rank


def _mass_quintuples(
    total: int,
) -> tuple[tuple[int, int, int, int, int], ...]:
    return tuple(
        (first, second, third, fourth, total - first - second - third - fourth)
        for first in range(total + 1)
        for second in range(first, total + 1)
        for third in range(second, total + 1)
        for fourth in range(third, total + 1)
        if fourth <= total - first - second - third - fourth
    )


def _mass_groups(
    masses: tuple[int, int, int, int, int],
) -> tuple[tuple[int, int], ...]:
    result: list[tuple[int, int]] = []
    start = 0
    while start < _ACTIVE_COUNT:
        end = start + 1
        while end < _ACTIVE_COUNT and masses[end] == masses[start]:
            end += 1
        result.append((start, end))
        start = end
    return tuple(result)


def _bundle_block_count(
    masses: tuple[int, int, int, int, int],
) -> int:
    result = 1
    for start, end in _mass_groups(masses):
        population = _raw_bundle_count(masses[start])
        result *= comb(population, end - start)
    return result


@cache
def _bundle_count(total: int) -> int:
    return sum(_bundle_block_count(masses) for masses in _mass_quintuples(total))


def _bundle_local_rank(
    masses: tuple[int, int, int, int, int],
    ranks: tuple[int, int, int, int, int],
) -> int:
    result = 0
    for start, end in _mass_groups(masses):
        population = _raw_bundle_count(masses[start])
        group_count = comb(population, end - start)
        group_rank = _strict_combination_rank(ranks[start:end], population)
        result = result * group_count + group_rank
    return result


def _ordered_bundle_data(
    bundles: _Bundles,
) -> (
    tuple[
        tuple[int, int, int, int, int],
        tuple[int, int, int, int, int],
    ]
    | None
):
    valid_lengths = all(len(bundle) == _VERTEX_COMPONENTS for bundle in bundles)
    valid_values = all(value >= 0 for bundle in bundles for value in bundle)
    if not valid_lengths or not valid_values:
        return None
    ordered = sorted(_bundle_key(bundle) for bundle in bundles)
    if len(set(ordered)) != _ACTIVE_COUNT:
        return None
    masses = tuple(item[0] for item in ordered)
    ranks = tuple(item[1] for item in ordered)
    assert len(masses) == _ACTIVE_COUNT
    assert len(ranks) == _ACTIVE_COUNT
    return masses, ranks


def _bundle_rank(bundles: _Bundles) -> int | None:
    data = _ordered_bundle_data(bundles)
    if data is None:
        return None
    masses, ranks = data
    prefix = sum(
        _bundle_block_count(candidate)
        for candidate in _mass_quintuples(sum(masses))
        if candidate < masses
    )
    return prefix + _bundle_local_rank(masses, ranks)


def _bundle_group_ranks(
    masses: tuple[int, int, int, int, int],
    rank: int,
) -> tuple[int, ...]:
    groups = _mass_groups(masses)
    counts = tuple(
        comb(_raw_bundle_count(masses[start]), end - start) for start, end in groups
    )
    remaining = rank
    reversed_ranks: list[int] = []
    for count in reversed(counts):
        remaining, local = divmod(remaining, count)
        reversed_ranks.append(local)
    assert remaining == 0
    return tuple(reversed(reversed_ranks))


def _bundle_block_unrank(
    masses: tuple[int, int, int, int, int],
    rank: int,
) -> _Bundles:
    group_ranks = _bundle_group_ranks(masses, rank)
    result: list[_Vector] = []
    for (start, end), group_rank in zip(_mass_groups(masses), group_ranks, strict=True):
        mass = masses[start]
        population = _raw_bundle_count(mass)
        raw_ranks = _strict_combination_unrank(
            population,
            end - start,
            group_rank,
        )
        for raw_rank in raw_ranks:
            bundle = _composition_unrank(mass, _VERTEX_COMPONENTS, raw_rank)
            assert bundle is not None
            result.append(bundle)
    first, second, third, fourth, fifth = result
    return first, second, third, fourth, fifth


def _bundle_unrank(total: int, rank: int) -> _Bundles | None:
    if rank < 0 or rank >= _bundle_count(total):
        return None
    remaining = rank
    for masses in _mass_quintuples(total):
        block = _bundle_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        return _bundle_block_unrank(masses, remaining)
    raise AssertionError


def _ordered_edge(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


def _as_bundles(values: tuple[_Vector, ...]) -> _Bundles:
    assert len(values) == _ACTIVE_COUNT
    first, second, third, fourth, fifth = values
    return first, second, third, fourth, fifth


def _as_edges(values: tuple[_Vector, ...]) -> _Edges:
    assert len(values) == _EDGE_COUNT
    first, second, third, fourth, fifth, sixth, seventh, eighth, ninth, tenth = values
    return first, second, third, fourth, fifth, sixth, seventh, eighth, ninth, tenth


def _valid_residual_shapes(state: _Residual) -> bool:
    fixed, bundles, edges = state
    return (
        len(fixed) == _FIXED_COMPONENTS
        and all(len(bundle) == _VERTEX_COMPONENTS for bundle in bundles)
        and all(len(edge) == _EDGE_COMPONENTS for edge in edges)
        and all(value >= 0 for vector in (fixed, *bundles, *edges) for value in vector)
    )


def _bundle_order(
    bundles: _Bundles,
) -> tuple[int, int, int, int, int] | None:
    keyed = sorted((_bundle_key(bundle), index) for index, bundle in enumerate(bundles))
    if len({key for key, _ in keyed}) != _ACTIVE_COUNT:
        return None
    indices = tuple(index for _, index in keyed)
    first, second, third, fourth, fifth = indices
    return first, second, third, fourth, fifth


def _reorder_edges(
    edges: _Edges,
    order: tuple[int, int, int, int, int],
) -> _Edges:
    values = tuple(
        edges[_K5_EDGE_INDEX[_ordered_edge(order[left], order[right])]]
        for left, right in _K5_EDGES
    )
    return _as_edges(values)


def _canonicalize_residual(state: _Residual) -> _Residual | None:
    if not _valid_residual_shapes(state):
        return None
    fixed, bundles, edges = state
    order = _bundle_order(bundles)
    if order is None:
        return None
    canonical_bundles = _as_bundles(tuple(bundles[index] for index in order))
    return fixed, canonical_bundles, _reorder_edges(edges, order)


def _flatten_edges(edges: _Edges) -> _Vector:
    return tuple(value for edge in edges for value in edge)


def _edges_from_vector(vector: _Vector) -> _Edges:
    assert len(vector) == _EDGE_SCALARS
    values = tuple(
        vector[index : index + _EDGE_COMPONENTS]
        for index in range(0, _EDGE_SCALARS, _EDGE_COMPONENTS)
    )
    return _as_edges(values)


@cache
def _residual_count(total: int) -> int:
    return sum(
        _composition_count(fixed_mass, _FIXED_COMPONENTS)
        * _bundle_count(bundle_mass)
        * _composition_count(total - fixed_mass - bundle_mass, _EDGE_SCALARS)
        for fixed_mass in range(total + 1)
        for bundle_mass in range(total - fixed_mass + 1)
    )


def _residual_rank_data(
    state: _Residual,
) -> tuple[_Vector, _Bundles, _Vector, int, int, int] | None:
    canonical = _canonicalize_residual(state)
    if canonical is None:
        return None
    fixed, bundles, edges = canonical
    edge_vector = _flatten_edges(edges)
    return (
        fixed,
        bundles,
        edge_vector,
        sum(fixed),
        sum(sum(bundle) for bundle in bundles),
        sum(edge_vector),
    )


def _residual_prefix(total: int, fixed_mass: int, bundle_mass: int) -> int:
    before_fixed = sum(
        _composition_count(mass, _FIXED_COMPONENTS)
        * sum(
            _bundle_count(bmass)
            * _composition_count(total - mass - bmass, _EDGE_SCALARS)
            for bmass in range(total - mass + 1)
        )
        for mass in range(fixed_mass)
    )
    before_bundle = _composition_count(fixed_mass, _FIXED_COMPONENTS) * sum(
        _bundle_count(mass)
        * _composition_count(total - fixed_mass - mass, _EDGE_SCALARS)
        for mass in range(bundle_mass)
    )
    return before_fixed + before_bundle


def _residual_local_rank(
    fixed: _Vector,
    bundles: _Bundles,
    edge_vector: _Vector,
    *,
    masses: tuple[int, int, int],
) -> int:
    _, bundle_mass, edge_mass = masses
    fixed_rank = _composition_rank(fixed, _FIXED_COMPONENTS)
    bundle_rank = _bundle_rank(bundles)
    edge_rank = _composition_rank(edge_vector, _EDGE_SCALARS)
    assert fixed_rank is not None
    assert bundle_rank is not None
    assert edge_rank is not None
    bundle_count = _bundle_count(bundle_mass)
    edge_count = _composition_count(edge_mass, _EDGE_SCALARS)
    return (fixed_rank * bundle_count + bundle_rank) * edge_count + edge_rank


def _residual_rank(state: _Residual) -> int | None:
    data = _residual_rank_data(state)
    if data is None:
        return None
    fixed = data[0]
    bundles = data[1]
    edge_vector = data[2]
    masses = data[3], data[4], data[5]
    total = sum(masses)
    prefix = _residual_prefix(total, masses[0], masses[1])
    return prefix + _residual_local_rank(
        fixed,
        bundles,
        edge_vector,
        masses=masses,
    )


def _residual_component_ranks(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    _, bundle_mass, edge_mass = masses
    edge_count = _composition_count(edge_mass, _EDGE_SCALARS)
    fixed_and_bundle, edge_rank = divmod(rank, edge_count)
    fixed_rank, bundle_rank = divmod(
        fixed_and_bundle,
        _bundle_count(bundle_mass),
    )
    return fixed_rank, bundle_rank, edge_rank


def _unrank_residual_block(
    masses: tuple[int, int, int],
    rank: int,
) -> _Residual:
    fixed_rank, bundle_rank, edge_rank = _residual_component_ranks(masses, rank)
    fixed = _composition_unrank(masses[0], _FIXED_COMPONENTS, fixed_rank)
    bundles = _bundle_unrank(masses[1], bundle_rank)
    edge_vector = _composition_unrank(masses[2], _EDGE_SCALARS, edge_rank)
    assert fixed is not None
    assert bundles is not None
    assert edge_vector is not None
    return fixed, bundles, _edges_from_vector(edge_vector)


def _residual_unrank(total: int, rank: int) -> _Residual | None:
    if rank < 0 or rank >= _residual_count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        for bundle_mass in range(total - fixed_mass + 1):
            edge_mass = total - fixed_mass - bundle_mass
            block = (
                _composition_count(fixed_mass, _FIXED_COMPONENTS)
                * _bundle_count(bundle_mass)
                * _composition_count(edge_mass, _EDGE_SCALARS)
            )
            if remaining >= block:
                remaining -= block
                continue
            return _unrank_residual_block(
                (fixed_mass, bundle_mass, edge_mass),
                remaining,
            )
    raise AssertionError


def _vertex_sequences_from(
    start: int,
    slots: int,
    remaining: int,
) -> tuple[tuple[_Pair, ...], ...]:
    if slots == 0:
        return ((),)
    result: list[tuple[_Pair, ...]] = []
    for index in range(start, len(_PAIR_VALUES)):
        pair = _PAIR_VALUES[index]
        pair_mass = sum(pair)
        if pair_mass > remaining:
            continue
        result.extend(
            (pair, *suffix)
            for suffix in _vertex_sequences_from(
                index,
                slots - 1,
                remaining - pair_mass,
            )
        )
    return tuple(result)


def _as_vertices(values: tuple[_Pair, ...]) -> _Vertices:
    assert len(values) == _ARITY
    first, second, third, fourth, fifth, sixth = values
    return first, second, third, fourth, fifth, sixth


def _partition(values: tuple[_Pair, ...]) -> tuple[int, ...]:
    return tuple(sorted(Counter(values).values(), reverse=True))


@cache
def _vertices_of_mass(mass: int) -> tuple[_Vertices, ...]:
    return tuple(
        _as_vertices(values)
        for values in _vertex_sequences_from(0, _ARITY, mass)
        if sum(sum(pair) for pair in values) == mass
        and _partition(values) == _TOP_PARTITION
    )


@cache
def _class_count(total: int) -> int:
    return sum(
        len(_vertices_of_mass(vertex_mass)) * _residual_count(total - vertex_mass)
        for vertex_mass in range(total + 1)
    )


def _residual_mass(residual: _Residual) -> int:
    return sum(
        value
        for vector in (residual[0], *residual[1], *residual[2])
        for value in vector
    )


def _vertex_rank(vertices: _Vertices, mass: int) -> int | None:
    try:
        return _vertices_of_mass(mass).index(vertices)
    except ValueError:
        return None


def _state_rank_data(
    total: int,
    state: _State,
) -> tuple[int, int, int, int] | None:
    vertices, residual = state
    vertex_mass = sum(sum(pair) for pair in vertices)
    residual_mass = total - vertex_mass
    vertex_rank = _vertex_rank(vertices, vertex_mass)
    residual_rank = _residual_rank(residual)
    valid_mass = vertex_mass <= total and _residual_mass(residual) == residual_mass
    if not valid_mass or vertex_rank is None or residual_rank is None:
        return None
    return vertex_mass, vertex_rank, residual_mass, residual_rank


def _rank(total: int, state: _State) -> int | None:
    data = _state_rank_data(total, state)
    if data is None:
        return None
    vertex_mass, vertex_rank, residual_mass, residual_rank = data
    prefix = sum(
        len(_vertices_of_mass(mass)) * _residual_count(total - mass)
        for mass in range(vertex_mass)
    )
    return prefix + vertex_rank * _residual_count(residual_mass) + residual_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for vertex_mass in range(total + 1):
        residual_count = _residual_count(total - vertex_mass)
        block = len(_vertices_of_mass(vertex_mass)) * residual_count
        if remaining >= block:
            remaining -= block
            continue
        vertex_rank, residual_rank = divmod(remaining, residual_count)
        residual = _residual_unrank(total - vertex_mass, residual_rank)
        assert residual is not None
        return _vertices_of_mass(vertex_mass)[vertex_rank], residual
    raise AssertionError


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _vector_to_residual(vector: _Vector) -> _Residual:
    expected = _FIXED_COMPONENTS + _ACTIVE_COUNT * _VERTEX_COMPONENTS + _EDGE_SCALARS
    assert len(vector) == expected
    cursor = _FIXED_COMPONENTS
    fixed = vector[:cursor]
    bundles = tuple(
        vector[
            cursor + index * _VERTEX_COMPONENTS : cursor
            + (index + 1) * _VERTEX_COMPONENTS
        ]
        for index in range(_ACTIVE_COUNT)
    )
    cursor += _ACTIVE_COUNT * _VERTEX_COMPONENTS
    edges = _edges_from_vector(vector[cursor:])
    b0, b1, b2, b3, b4 = bundles
    return fixed, (b0, b1, b2, b3, b4), edges


def _inverse_order(
    order: tuple[int, ...],
) -> tuple[int, int, int, int, int]:
    inverse = tuple(order.index(destination) for destination in _ACTIVE)
    first, second, third, fourth, fifth = inverse
    return first, second, third, fourth, fifth


def _permute_residual(state: _Residual, order: tuple[int, ...]) -> _Residual:
    fixed, bundles, edges = state
    inverse = _inverse_order(order)
    permuted_bundles = _as_bundles(
        tuple(bundles[inverse[destination]] for destination in _ACTIVE)
    )
    permuted_edges = _as_edges(
        tuple(
            edges[_K5_EDGE_INDEX[_ordered_edge(inverse[left], inverse[right])]]
            for left, right in _K5_EDGES
        )
    )
    return fixed, permuted_bundles, permuted_edges


def test_s6_s5_distinct_bundle_rank_matches_small_s5_orbits() -> None:
    """The unique bundle order makes the abstract S5 residual rank invariant."""
    total = _EXHAUSTIVE_ORBIT_MASS
    ranks: set[int] = set()
    for vector in _weak_compositions(total, 52):
        state = _vector_to_residual(vector)
        rank = _residual_rank(state)
        if rank is None:
            continue
        ranks.add(rank)
        for order in _S5:
            assert _residual_rank(_permute_residual(state, order)) == rank
    assert ranks == set(range(_residual_count(total)))


def test_s6_s5_distinct_bundle_rank_exhausts_small_full_domains() -> None:
    """Every complete class through mass seven receives one contiguous rank."""
    for total in range(_EXHAUSTIVE_FULL_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s5_distinct_bundle_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior ranks roundtrip throughout the admitted range."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        if count == 0:
            continue
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT


def test_s6_s5_distinct_bundle_counts_match_reviewed_sequence() -> None:
    """Mass-seven-through-fourteen counts match the nested factorization."""
    observed = {
        mass: _class_count(mass)
        for mass in range(_MAXIMUM_MASS + 1)
        if _class_count(mass) != 0
    }
    assert observed == _EXPECTED_COUNTS
