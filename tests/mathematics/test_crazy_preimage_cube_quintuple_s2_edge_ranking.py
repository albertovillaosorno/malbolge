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
#     transposition stabilizer arising from an equal S5 vertex-pair block.
# - Must-Not:
#   - Claim dense ranking for larger residual stabilizers or for the complete S5
#     quotient.
# - Allows:
#   - Inputs: residual edge-pair mass zero through fourteen.
#   - Outputs: exact dense rank/unrank modulo one coupled vertex transposition.
#   - Side effects: none.
# - Split-When:
#   - Residual stabilizer order exceeds two.
# - Merge-When:
#   - Dense S5 ranking owns the same transposition edge-orbit construction.
# - Summary:
#   - Densely rank the S2 residual K5 edge-pair quotient.
# - Description:
#   - Splits four fixed edges from three coupled swapped-edge pairs. The latter
#     become one unordered pair of six-component compositions.
# - Usage:
#   - Constructive prerequisite for S5 strata with stabilizer order two.
# - Defaults:
#   - Direct orbit enumeration stops at mass four; arithmetic reaches 14.
#

"""Dense residual S2 ranking for pair-valued K5 edge assignments."""

from __future__ import annotations

from math import comb

_COMPONENTS_PER_EDGE_PAIR = 2
_EDGE_COUNT = 10
_EXHAUSTIVE_MASS = 4
_FIXED_COMPONENTS = 8
_MAXIMUM_MASS = 14
_SIDE_COMPONENTS = 6

_FIXED_EDGES = ((0, 1), (2, 3), (2, 4), (3, 4))
_LEFT_EDGES = ((0, 2), (0, 3), (0, 4))
_RIGHT_EDGES = ((1, 2), (1, 3), (1, 4))
_EDGES = tuple(
    (left, right)
    for left in range(5)
    for right in range(left + 1, 5)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_TRANSPOSE = (1, 0, 2, 3, 4)

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
    count = _composition_count(total, parts)
    if rank < 0 or rank >= count:
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


def _unordered_pair_count(total: int) -> int:
    count = 0
    for left_mass in range((total + 1) // 2):
        right_mass = total - left_mass
        count += _composition_count(left_mass, _SIDE_COMPONENTS) * (
            _composition_count(right_mass, _SIDE_COMPONENTS)
        )
    if total % 2 == 0:
        half = total // 2
        side_count = _composition_count(half, _SIDE_COMPONENTS)
        count += side_count * (side_count + 1) // 2
    return count


def _equal_mass_pair_rank(left_rank: int, right_rank: int, count: int) -> int:
    assert 0 <= left_rank <= right_rank < count
    return (
        left_rank * count
        - left_rank * (left_rank - 1) // 2
        + right_rank
        - left_rank
    )


def _equal_mass_pair_unrank(rank: int, count: int) -> tuple[int, int]:
    remaining = rank
    for left_rank in range(count):
        block = count - left_rank
        if remaining >= block:
            remaining -= block
            continue
        return left_rank, left_rank + remaining
    raise AssertionError


def _side_key(vector: _Vector) -> tuple[int, int]:
    total = sum(vector)
    rank = _composition_rank(vector, total)
    assert rank is not None
    return total, rank


def _valid_side_pair(left: _Vector, right: _Vector) -> bool:
    return (
        len(left) == _SIDE_COMPONENTS
        and len(right) == _SIDE_COMPONENTS
        and all(value >= 0 for value in (*left, *right))
    )


def _movable_rank(left: _Vector, right: _Vector) -> int | None:
    if not _valid_side_pair(left, right):
        return None
    if _side_key(right) < _side_key(left):
        left, right = right, left
    left_mass, left_rank = _side_key(left)
    right_mass, right_rank = _side_key(right)
    total = left_mass + right_mass
    rank = sum(
        _composition_count(mass, _SIDE_COMPONENTS)
        * _composition_count(total - mass, _SIDE_COMPONENTS)
        for mass in range(left_mass)
        if mass < total - mass
    )
    if left_mass < right_mass:
        offset = left_rank * _composition_count(
            right_mass,
            _SIDE_COMPONENTS,
        ) + right_rank
    else:
        side_count = _composition_count(left_mass, _SIDE_COMPONENTS)
        offset = _equal_mass_pair_rank(left_rank, right_rank, side_count)
    return rank + offset


def _unrank_side_pair(
    left_mass: int,
    right_mass: int,
    *,
    left_rank: int,
    right_rank: int,
) -> tuple[_Vector, _Vector]:
    left = _composition_unrank(left_mass, _SIDE_COMPONENTS, left_rank)
    right = _composition_unrank(right_mass, _SIDE_COMPONENTS, right_rank)
    assert left is not None
    assert right is not None
    return left, right


def _movable_unrank(total: int, rank: int) -> tuple[_Vector, _Vector] | None:
    if rank < 0 or rank >= _unordered_pair_count(total):
        return None
    remaining = rank
    for left_mass in range((total + 1) // 2):
        right_mass = total - left_mass
        right_count = _composition_count(right_mass, _SIDE_COMPONENTS)
        block = _composition_count(left_mass, _SIDE_COMPONENTS) * right_count
        if remaining >= block:
            remaining -= block
            continue
        left_rank, right_rank = divmod(remaining, right_count)
        return _unrank_side_pair(
            left_mass,
            right_mass,
            left_rank=left_rank,
            right_rank=right_rank,
        )
    half = total // 2
    side_count = _composition_count(half, _SIDE_COMPONENTS)
    left_rank, right_rank = _equal_mass_pair_unrank(remaining, side_count)
    return _unrank_side_pair(
        half,
        half,
        left_rank=left_rank,
        right_rank=right_rank,
    )


def _edge_orbit_count(total: int) -> int:
    return sum(
        _composition_count(fixed_mass, _FIXED_COMPONENTS)
        * _unordered_pair_count(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def _rank_components(
    fixed: _Vector,
    left: _Vector,
    right: _Vector,
) -> int | None:
    if len(fixed) != _FIXED_COMPONENTS:
        return None
    fixed_mass = sum(fixed)
    fixed_rank = _composition_rank(fixed, fixed_mass)
    movable_rank = _movable_rank(left, right)
    if fixed_rank is None or movable_rank is None:
        return None
    movable_mass = sum(left) + sum(right)
    total = fixed_mass + movable_mass
    return (
        sum(
            _composition_count(mass, _FIXED_COMPONENTS)
            * _unordered_pair_count(total - mass)
            for mass in range(fixed_mass)
        )
        + fixed_rank * _unordered_pair_count(movable_mass)
        + movable_rank
    )


def _unrank_components(
    total: int,
    rank: int,
) -> tuple[_Vector, _Vector, _Vector] | None:
    if rank < 0 or rank >= _edge_orbit_count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        movable_mass = total - fixed_mass
        movable_count = _unordered_pair_count(movable_mass)
        fixed_count = _composition_count(fixed_mass, _FIXED_COMPONENTS)
        block = fixed_count * movable_count
        if remaining >= block:
            remaining -= block
            continue
        fixed_rank, movable_rank = divmod(remaining, movable_count)
        fixed = _composition_unrank(fixed_mass, _FIXED_COMPONENTS, fixed_rank)
        movable = _movable_unrank(movable_mass, movable_rank)
        assert fixed is not None
        assert movable is not None
        return fixed, movable[0], movable[1]
    raise AssertionError


def _flatten(
    edge_pairs: _EdgePairs,
    edges: tuple[tuple[int, int], ...],
) -> _Vector:
    values: list[int] = []
    for edge in edges:
        values.extend(edge_pairs[_EDGE_INDEX[edge]])
    return tuple(values)


def _components(
    edge_pairs: _EdgePairs,
) -> tuple[_Vector, _Vector, _Vector] | None:
    if len(edge_pairs) != _EDGE_COUNT or any(
        value < 0 for pair in edge_pairs for value in pair
    ):
        return None
    return (
        _flatten(edge_pairs, _FIXED_EDGES),
        _flatten(edge_pairs, _LEFT_EDGES),
        _flatten(edge_pairs, _RIGHT_EDGES),
    )


def _rank(edge_pairs: _EdgePairs) -> int | None:
    components = _components(edge_pairs)
    if components is None:
        return None
    return _rank_components(*components)


def _unflatten(vector: _Vector) -> tuple[_Pair, ...]:
    assert len(vector) % _COMPONENTS_PER_EDGE_PAIR == 0
    return tuple(
        (vector[index], vector[index + 1])
        for index in range(0, len(vector), _COMPONENTS_PER_EDGE_PAIR)
    )


def _unrank(total: int, rank: int) -> _EdgePairs | None:
    components = _unrank_components(total, rank)
    if components is None:
        return None
    fixed, left, right = components
    result: list[_Pair | None] = [None] * _EDGE_COUNT
    for edges, vector in (
        (_FIXED_EDGES, fixed),
        (_LEFT_EDGES, left),
        (_RIGHT_EDGES, right),
    ):
        for edge, pair in zip(edges, _unflatten(vector), strict=True):
            result[_EDGE_INDEX[edge]] = pair
    assert all(pair is not None for pair in result)
    return tuple(pair for pair in result if pair is not None)


def _permute_edges(edge_pairs: _EdgePairs) -> _EdgePairs:
    result: list[_Pair] = []
    for left, right in _EDGES:
        source = tuple(sorted((_TRANSPOSE[left], _TRANSPOSE[right])))
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
    assert len(vector) == _EDGE_COUNT * _COMPONENTS_PER_EDGE_PAIR
    return tuple(
        (vector[index], vector[index + 1])
        for index in range(0, len(vector), _COMPONENTS_PER_EDGE_PAIR)
    )


def _burnside_count(total: int) -> int:
    identity = _composition_count(total, 20)
    fixed = sum(
        _composition_count(fixed_mass, _FIXED_COMPONENTS)
        * _composition_count((total - fixed_mass) // 2, _SIDE_COMPONENTS)
        for fixed_mass in range(total + 1)
        if (total - fixed_mass) % 2 == 0
    )
    return (identity + fixed) // 2


def test_s2_edge_action_has_four_fixed_and_three_swapped_edges() -> None:
    """The residual transposition has the exact K5 edge action."""
    assert {_TRANSPOSE[index] for index in range(5)} == set(range(5))
    assert all(_permute_edges(_permute_edges(value)) == value for value in (
        tuple((index, index + 1) for index in range(_EDGE_COUNT)),
    ))
    observed_edges = set(_FIXED_EDGES) | set(_LEFT_EDGES) | set(_RIGHT_EDGES)
    assert observed_edges == set(_EDGES)


def test_dense_s2_edge_rank_matches_direct_small_orbits() -> None:
    """Small pair-valued edge assignments collapse to one contiguous S2 rank."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        representatives: dict[int, set[_EdgePairs]] = {}
        for vector in _weak_compositions(total, 20):
            edge_pairs = _edge_pairs_from_vector(vector)
            rank = _rank(edge_pairs)
            assert rank is not None
            orbit = {edge_pairs, _permute_edges(edge_pairs)}
            if rank not in representatives:
                representatives[rank] = orbit
            assert representatives[rank] == orbit
        count = _edge_orbit_count(total)
        assert set(representatives) == set(range(count))
        assert count == _burnside_count(total)


def test_dense_s2_edge_rank_roundtrips_through_mass_fourteen() -> None:
    """Boundary and interior ranks roundtrip through the checked mass range."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _edge_orbit_count(total)
        assert count == _burnside_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            edge_pairs = _unrank(total, rank)
            assert edge_pairs is not None
            assert _rank(edge_pairs) == rank
            assert _rank(_permute_edges(edge_pairs)) == rank
