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
#   - Dense ranking evidence for pair-valued K5 edge assignments under one
#     residual S3 vertex stabilizer.
# - Must-Not:
#   - Claim dense ranking for other residual stabilizers or complete S5 classes.
# - Allows:
#   - Inputs: residual edge-pair mass zero through fourteen.
#   - Outputs: exact dense rank/unrank modulo the residual S3 action.
#   - Side effects: none.
# - Split-When:
#   - The residual vertex stabilizer is not conjugate to S3.
# - Merge-When:
#   - Dense S5 ranking owns the same three-bundle multiset construction.
# - Summary:
#   - Densely rank the residual S3 K5 edge-pair quotient.
# - Description:
#   - Uses one fixed edge and a multiset of three six-component vertex bundles.
# - Usage:
#   - Constructive prerequisite for S5 strata with stabilizer order six.
# - Defaults:
#   - Direct orbit enumeration stops at mass three; arithmetic reaches 14.
#

"""Dense residual S3 ranking for pair-valued K5 edge assignments."""

from __future__ import annotations

from itertools import permutations
from math import comb

_ACTIVE_VERTICES = (0, 1, 2)
_COMPONENTS_PER_BUNDLE = 6
_EDGE_COUNT = 10
_EXHAUSTIVE_MASS = 3
_FIXED_COMPONENTS = 2
_MAXIMUM_MASS = 14
_ENDPOINT_ORDERS = tuple(
    (*order, 3, 4) for order in permutations(_ACTIVE_VERTICES)
)
_EDGES = tuple(
    (left, right)
    for left in range(5)
    for right in range(left + 1, 5)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_FIXED_EDGE = (3, 4)

type _Pair = tuple[int, int]
type _EdgePairs = tuple[_Pair, ...]
type _Vector = tuple[int, ...]


def _composition_count(total: int, parts: int) -> int:
    if total < 0 or parts <= 0:
        return 0
    return comb(total + parts - 1, parts - 1)


def _composition_rank(vector: _Vector, total: int) -> int | None:
    if not vector or any(value < 0 for value in vector) or sum(vector) != total:
        return None
    rank = 0
    remaining = total
    for index, value in enumerate(vector[:-1]):
        tail_parts = len(vector) - index - 1
        for earlier in range(value):
            rank += _composition_count(remaining - earlier, tail_parts)
        remaining -= value
    return rank


def _composition_unrank(total: int, parts: int, rank: int) -> _Vector | None:
    if rank < 0 or rank >= _composition_count(total, parts):
        return None
    remaining_rank = rank
    remaining_total = total
    values: list[int] = []
    for index in range(parts - 1):
        tail_parts = parts - index - 1
        for value in range(remaining_total + 1):
            block = _composition_count(remaining_total - value, tail_parts)
            if remaining_rank >= block:
                remaining_rank -= block
                continue
            values.append(value)
            remaining_total -= value
            break
    values.append(remaining_total)
    return tuple(values)


def _combination_rank(values: tuple[int, ...], population: int) -> int | None:
    size = len(values)
    shifted = tuple(value + index for index, value in enumerate(values))
    universe = population + size - 1
    if (
        any(value < 0 or value >= population for value in values)
        or tuple(sorted(values)) != values
    ):
        return None
    rank = 0
    previous = -1
    for index, value in enumerate(shifted):
        remaining = size - index - 1
        for candidate in range(previous + 1, value):
            rank += comb(universe - candidate - 1, remaining)
        previous = value
    return rank


def _combination_unrank(
    population: int,
    size: int,
    rank: int,
) -> tuple[int, ...] | None:
    count = comb(population + size - 1, size)
    if rank < 0 or rank >= count:
        return None
    universe = population + size - 1
    remaining_rank = rank
    previous = -1
    shifted: list[int] = []
    for index in range(size):
        remaining = size - index - 1
        for candidate in range(previous + 1, universe):
            block = comb(universe - candidate - 1, remaining)
            if remaining_rank >= block:
                remaining_rank -= block
                continue
            shifted.append(candidate)
            previous = candidate
            break
    return tuple(value - index for index, value in enumerate(shifted))


def _mass_triples(total: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (first, second, total - first - second)
        for first in range(total + 1)
        for second in range(first, total + 1)
        if second <= total - first - second
    )


def _mass_counts(masses: tuple[int, int, int]) -> tuple[int, int, int]:
    return (
        _composition_count(masses[0], _COMPONENTS_PER_BUNDLE),
        _composition_count(masses[1], _COMPONENTS_PER_BUNDLE),
        _composition_count(masses[2], _COMPONENTS_PER_BUNDLE),
    )


def _mass_block_count(masses: tuple[int, int, int]) -> int:
    first, second, third = masses
    first_count, second_count, third_count = _mass_counts(masses)
    if first == third:
        result = comb(first_count + 2, 3)
    elif first == second:
        result = comb(first_count + 1, 2) * third_count
    elif second == third:
        result = first_count * comb(second_count + 1, 2)
    else:
        result = first_count * second_count * third_count
    return result


def _active_count(total: int) -> int:
    return sum(_mass_block_count(masses) for masses in _mass_triples(total))


def _bundle_key(bundle: _Vector) -> tuple[int, int]:
    mass = sum(bundle)
    rank = _composition_rank(bundle, mass)
    assert rank is not None
    return mass, rank


def _rank_equal_mass_block(
    masses: tuple[int, int, int],
    ranks: tuple[int, int, int],
) -> int:
    population = _mass_counts(masses)[0]
    result = _combination_rank(ranks, population)
    assert result is not None
    return result


def _rank_first_equal_block(
    masses: tuple[int, int, int],
    ranks: tuple[int, int, int],
) -> int:
    first_count, _, third_count = _mass_counts(masses)
    pair_rank = _combination_rank((ranks[0], ranks[1]), first_count)
    assert pair_rank is not None
    return pair_rank * third_count + ranks[2]


def _rank_last_equal_block(
    masses: tuple[int, int, int],
    ranks: tuple[int, int, int],
) -> int:
    _, second_count, _ = _mass_counts(masses)
    pair_rank = _combination_rank((ranks[1], ranks[2]), second_count)
    assert pair_rank is not None
    return ranks[0] * comb(second_count + 1, 2) + pair_rank


def _rank_distinct_mass_block(
    masses: tuple[int, int, int],
    ranks: tuple[int, int, int],
) -> int:
    _, second_count, third_count = _mass_counts(masses)
    return (ranks[0] * second_count + ranks[1]) * third_count + ranks[2]


def _mass_block_rank(
    masses: tuple[int, int, int],
    ranks: tuple[int, int, int],
) -> int:
    first, second, third = masses
    if first == third:
        result = _rank_equal_mass_block(masses, ranks)
    elif first == second:
        result = _rank_first_equal_block(masses, ranks)
    elif second == third:
        result = _rank_last_equal_block(masses, ranks)
    else:
        result = _rank_distinct_mass_block(masses, ranks)
    return result


def _active_rank(bundles: tuple[_Vector, _Vector, _Vector]) -> int | None:
    if any(len(bundle) != _COMPONENTS_PER_BUNDLE for bundle in bundles):
        return None
    if any(value < 0 for bundle in bundles for value in bundle):
        return None
    keys = sorted(_bundle_key(bundle) for bundle in bundles)
    masses = keys[0][0], keys[1][0], keys[2][0]
    ranks = keys[0][1], keys[1][1], keys[2][1]
    total = sum(masses)
    prefix = sum(
        _mass_block_count(candidate)
        for candidate in _mass_triples(total)
        if candidate < masses
    )
    return prefix + _mass_block_rank(masses, ranks)


def _unrank_equal_mass_block(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    population = _mass_counts(masses)[0]
    values = _combination_unrank(population, 3, rank)
    assert values is not None
    return values[0], values[1], values[2]


def _unrank_first_equal_block(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    first_count, _, third_count = _mass_counts(masses)
    pair_rank, third_rank = divmod(rank, third_count)
    values = _combination_unrank(first_count, 2, pair_rank)
    assert values is not None
    return values[0], values[1], third_rank


def _unrank_last_equal_block(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    _, second_count, _ = _mass_counts(masses)
    first_rank, pair_rank = divmod(rank, comb(second_count + 1, 2))
    values = _combination_unrank(second_count, 2, pair_rank)
    assert values is not None
    return first_rank, values[0], values[1]


def _unrank_distinct_mass_block(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    _, second_count, third_count = _mass_counts(masses)
    first_rank, residual = divmod(rank, second_count * third_count)
    second_rank, third_rank = divmod(residual, third_count)
    return first_rank, second_rank, third_rank


def _mass_block_unrank(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    first, second, third = masses
    if first == third:
        result = _unrank_equal_mass_block(masses, rank)
    elif first == second:
        result = _unrank_first_equal_block(masses, rank)
    elif second == third:
        result = _unrank_last_equal_block(masses, rank)
    else:
        result = _unrank_distinct_mass_block(masses, rank)
    return result


def _active_unrank(
    total: int,
    rank: int,
) -> tuple[_Vector, _Vector, _Vector] | None:
    if rank < 0 or rank >= _active_count(total):
        return None
    remaining = rank
    for masses in _mass_triples(total):
        block = _mass_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        ranks = _mass_block_unrank(masses, remaining)
        first = _composition_unrank(
            masses[0], _COMPONENTS_PER_BUNDLE, ranks[0]
        )
        second = _composition_unrank(
            masses[1], _COMPONENTS_PER_BUNDLE, ranks[1]
        )
        third = _composition_unrank(
            masses[2], _COMPONENTS_PER_BUNDLE, ranks[2]
        )
        assert first is not None
        assert second is not None
        assert third is not None
        return first, second, third
    raise AssertionError


def _edge_orbit_count(total: int) -> int:
    return sum(
        _composition_count(fixed_mass, _FIXED_COMPONENTS)
        * _active_count(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def _bundle_edges(vertex: int) -> tuple[tuple[int, int], ...]:
    others = tuple(value for value in _ACTIVE_VERTICES if value != vertex)
    left, right = others[0], others[1]
    opposite = (left, right) if left < right else (right, left)
    return opposite, (vertex, 3), (vertex, 4)


def _flatten(
    edge_pairs: _EdgePairs,
    edges: tuple[tuple[int, int], ...],
) -> _Vector:
    values: list[int] = []
    for edge in edges:
        values.extend(edge_pairs[_EDGE_INDEX[edge]])
    return tuple(values)


def _rank(edge_pairs: _EdgePairs) -> int | None:
    if len(edge_pairs) != _EDGE_COUNT or any(
        value < 0 for pair in edge_pairs for value in pair
    ):
        return None
    fixed = _flatten(edge_pairs, (_FIXED_EDGE,))
    bundles = tuple(
        _flatten(edge_pairs, _bundle_edges(vertex))
        for vertex in _ACTIVE_VERTICES
    )
    fixed_mass = sum(fixed)
    fixed_rank = _composition_rank(fixed, fixed_mass)
    active_rank = _active_rank((bundles[0], bundles[1], bundles[2]))
    if fixed_rank is None or active_rank is None:
        return None
    active_mass = sum(sum(bundle) for bundle in bundles)
    total = fixed_mass + active_mass
    prefix = sum(
        _composition_count(mass, _FIXED_COMPONENTS)
        * _active_count(total - mass)
        for mass in range(fixed_mass)
    )
    return prefix + fixed_rank * _active_count(active_mass) + active_rank


def _assemble_edges(
    fixed: _Vector,
    bundles: tuple[_Vector, _Vector, _Vector],
) -> _EdgePairs:
    result: list[_Pair | None] = [None] * _EDGE_COUNT
    result[_EDGE_INDEX[_FIXED_EDGE]] = (fixed[0], fixed[1])
    for vertex, bundle in zip(_ACTIVE_VERTICES, bundles, strict=True):
        pairs = tuple(
            (bundle[index], bundle[index + 1])
            for index in range(0, _COMPONENTS_PER_BUNDLE, 2)
        )
        for edge, pair in zip(_bundle_edges(vertex), pairs, strict=True):
            result[_EDGE_INDEX[edge]] = pair
    assert all(pair is not None for pair in result)
    return tuple(pair for pair in result if pair is not None)


def _unrank(total: int, rank: int) -> _EdgePairs | None:
    if rank < 0 or rank >= _edge_orbit_count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        active_mass = total - fixed_mass
        active_count = _active_count(active_mass)
        block = _composition_count(fixed_mass, _FIXED_COMPONENTS) * active_count
        if remaining >= block:
            remaining -= block
            continue
        fixed_rank, active_rank = divmod(remaining, active_count)
        fixed = _composition_unrank(fixed_mass, _FIXED_COMPONENTS, fixed_rank)
        bundles = _active_unrank(active_mass, active_rank)
        assert fixed is not None
        assert bundles is not None
        return _assemble_edges(fixed, bundles)
    raise AssertionError


def _permute_edges(
    edge_pairs: _EdgePairs,
    order: tuple[int, ...],
) -> _EdgePairs:
    result: list[_Pair] = []
    for left, right in _EDGES:
        source = tuple(sorted((order[left], order[right])))
        result.append(edge_pairs[_EDGE_INDEX[source[0], source[1]]])
    return tuple(result)


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _edge_pairs_from_vector(vector: _Vector) -> _EdgePairs:
    return tuple(
        (vector[index], vector[index + 1])
        for index in range(0, 20, 2)
    )


def _fixed_scalar_count(cycles: tuple[int, ...], total: int) -> int:
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


def _burnside_count(total: int) -> int:
    identity = _composition_count(total, 20)
    transposition = _fixed_scalar_count((1,) * 8 + (2,) * 6, total)
    three_cycle = _fixed_scalar_count((1,) * 2 + (3,) * 6, total)
    return (identity + 3 * transposition + 2 * three_cycle) // 6


def test_s3_edge_bundles_transform_by_one_common_permutation() -> None:
    """The fixed edge stays fixed and the three six-count bundles permute."""
    sample = tuple((index, index + 1) for index in range(_EDGE_COUNT))
    fixed = _flatten(sample, (_FIXED_EDGE,))
    original = tuple(
        _flatten(sample, _bundle_edges(vertex))
        for vertex in _ACTIVE_VERTICES
    )
    for order in _ENDPOINT_ORDERS:
        permuted = _permute_edges(sample, order)
        assert _flatten(permuted, (_FIXED_EDGE,)) == fixed
        observed = tuple(
            _flatten(permuted, _bundle_edges(v)) for v in _ACTIVE_VERTICES
        )
        assert sorted(observed) == sorted(original)


def test_dense_s3_edge_rank_matches_direct_small_orbits() -> None:
    """Small edge assignments collapse to one contiguous residual S3 rank."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        representatives: dict[int, set[_EdgePairs]] = {}
        for vector in _weak_compositions(total, 20):
            edge_pairs = _edge_pairs_from_vector(vector)
            rank = _rank(edge_pairs)
            assert rank is not None
            orbit = {
                _permute_edges(edge_pairs, order) for order in _ENDPOINT_ORDERS
            }
            if rank not in representatives:
                representatives[rank] = orbit
            assert representatives[rank] == orbit
        count = _edge_orbit_count(total)
        assert set(representatives) == set(range(count))
        assert count == _burnside_count(total)


def test_dense_s3_edge_rank_roundtrips_through_mass_fourteen() -> None:
    """Boundary and interior S3 edge ranks roundtrip through mass fourteen."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _edge_orbit_count(total)
        assert count == _burnside_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            edge_pairs = _unrank(total, rank)
            assert edge_pairs is not None
            assert _rank(edge_pairs) == rank
            for order in _ENDPOINT_ORDERS:
                assert _rank(_permute_edges(edge_pairs, order)) == rank
