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
#   - Dense composition of the nested S6 (4,1,1)/(4) full-S4 bundle stratum.
# - Must-Not:
#   - Re-prove the widened full-S4 edge rank or rank another S6 stratum.
# - Allows:
#   - Inputs: canonical top vertices, fixed scalars, one quadruple-repeated
#     six-component bundle key, and a proved local full-S4 edge rank.
#   - Outputs: exact dense full-S6 rank/unrank for this second-layer stratum.
#   - Side effects: none.
# - Split-When:
#   - The widened full-S4 edge-rank contract changes.
# - Merge-When:
#   - Complete dense ranking owns the full (4,1,1) S6 stratum.
# - Summary:
#   - Prefix one quadruple-repeated bundle key and the proved full-S4 edge rank.
# - Description:
#   - All four second-layer bundles are equal, so their common six-vector rank
#     is the only bundle coordinate before the local full-S4 edge rank.
# - Usage:
#   - Completes the second-layer (4) slice through total mass fourteen.
# - Defaults:
#   - Exhaustive abstract ranks stop at total mass eight; arithmetic reaches 14.
#

"""Dense full-S4 bundle composition for the nested S6 (4,1,1) stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import permutations
from math import comb

_ARITY = 6
_FIXED_COMPONENTS = 4
_VERTEX_COMPONENTS = 6
_EDGE_COMPONENTS = 4
_MAXIMUM_MASS = 14
_EXHAUSTIVE_RANK_MASS = 8
_TOP_PARTITION = (4, 1, 1)
_WIDTH_FOURTEEN_COUNT = 829_746_428
_WIDTH_FOURTEEN_EDGE_COUNT = 255_543_816
_EXPECTED_COUNTS = (
    0,
    0,
    1,
    14,
    115,
    808,
    5_128,
    29_832,
    159_834,
    791_464,
    3_633_671,
    15_532_486,
    62_115_104,
    233_555_344,
    829_746_428,
)
_ACTIVE = (0, 1, 2, 3)
_K4_EDGES = tuple(
    (left, right)
    for left in _ACTIVE
    for right in _ACTIVE
    if left < right
)
_K4_EDGE_INDEX = {edge: index for index, edge in enumerate(_K4_EDGES)}
_S4 = tuple(permutations(_ACTIVE))
_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Vector = tuple[int, ...]
type _Bundle = tuple[int, int, int, int, int, int]
type _State = tuple[_Vertices, _Vector, _Bundle, int]
type _Masses = tuple[int, int, int]
type _Ranks = tuple[int, int, int]


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


def _as_bundle(vector: _Vector) -> _Bundle:
    assert len(vector) == _VERTEX_COMPONENTS
    first, second, third, fourth, fifth, sixth = vector
    return first, second, third, fourth, fifth, sixth


def _bundle_count(total: int) -> int:
    if total % 4 != 0:
        return 0
    return _composition_count(total // 4, _VERTEX_COMPONENTS)


def _bundle_rank(bundle: _Bundle) -> int:
    rank = _composition_rank(bundle, _VERTEX_COMPONENTS)
    assert rank is not None
    return rank


def _bundle_unrank(total: int, rank: int) -> _Bundle | None:
    if total % 4 != 0:
        return None
    vector = _composition_unrank(total // 4, _VERTEX_COMPONENTS, rank)
    return None if vector is None else _as_bundle(vector)


def _edge_cycles(order: tuple[int, ...]) -> tuple[int, ...]:
    permutation: list[int] = []
    for left, right in _K4_EDGES:
        image = tuple(sorted((order[left], order[right])))
        permutation.append(_K4_EDGE_INDEX[image[0], image[1]])
    unseen = set(range(len(_K4_EDGES)))
    cycles: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = permutation[current]
            length += 1
        cycles.append(length)
    return tuple(sorted(cycles))


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


@cache
def _edge_count(total: int) -> int:
    fixed_sum = sum(
        _fixed_count(
            tuple(sorted(_edge_cycles(order) * _EDGE_COMPONENTS)),
            total,
        )
        for order in _S4
    )
    return fixed_sum // len(_S4)


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


def _state_masses(state: _State) -> _Masses:
    vertices, fixed, bundle, _ = state
    return (
        sum(sum(pair) for pair in vertices),
        sum(fixed),
        4 * sum(bundle),
    )


@cache
def _mass_blocks(total: int) -> tuple[_Masses, ...]:
    return tuple(
        (vertex_mass, fixed_mass, bundle_mass)
        for vertex_mass in range(total + 1)
        for fixed_mass in range(total - vertex_mass + 1)
        for bundle_mass in range(total - vertex_mass - fixed_mass + 1)
        if bundle_mass % 4 == 0
    )


def _block_count(total: int, masses: _Masses) -> int:
    edge_mass = total - sum(masses)
    return (
        len(_vertices_of_mass(masses[0]))
        * _composition_count(masses[1], _FIXED_COMPONENTS)
        * _bundle_count(masses[2])
        * _edge_count(edge_mass)
    )


@cache
def _class_count(total: int) -> int:
    return sum(_block_count(total, masses) for masses in _mass_blocks(total))


def _state_ranks(state: _State, masses: _Masses) -> _Ranks | None:
    vertices, fixed, bundle, _ = state
    try:
        vertex_rank = _vertices_of_mass(masses[0]).index(vertices)
    except ValueError:
        vertex_rank = -1
    fixed_rank = _composition_rank(fixed, _FIXED_COMPONENTS)
    bundle_rank = _bundle_rank(bundle)
    valid_bundle = 4 * sum(bundle) == masses[2]
    result: _Ranks | None = None
    if vertex_rank >= 0 and fixed_rank is not None and valid_bundle:
        result = vertex_rank, fixed_rank, bundle_rank
    return result


def _state_data(
    total: int,
    state: _State,
) -> tuple[_Masses, _Ranks] | None:
    masses = _state_masses(state)
    edge_mass = total - sum(masses)
    ranks = _state_ranks(state, masses)
    valid_edge = edge_mass >= 0 and 0 <= state[3] < _edge_count(edge_mass)
    return (masses, ranks) if ranks is not None and valid_edge else None


def _prefix(total: int, masses: _Masses) -> int:
    return sum(
        _block_count(total, candidate)
        for candidate in _mass_blocks(total)
        if candidate < masses
    )


def _local_rank(
    total: int,
    masses: _Masses,
    ranks: _Ranks,
    *,
    edge_rank: int,
) -> int:
    vertex_rank, fixed_rank, bundle_rank = ranks
    fixed_count = _composition_count(masses[1], _FIXED_COMPONENTS)
    bundle_count = _bundle_count(masses[2])
    edge_count = _edge_count(total - sum(masses))
    head = vertex_rank * fixed_count + fixed_rank
    head = head * bundle_count + bundle_rank
    return head * edge_count + edge_rank


def _rank(total: int, state: _State) -> int | None:
    data = _state_data(total, state)
    if data is None:
        return None
    masses, ranks = data
    return _prefix(total, masses) + _local_rank(
        total,
        masses,
        ranks,
        edge_rank=state[3],
    )


def _component_ranks(
    total: int,
    masses: _Masses,
    rank: int,
) -> tuple[_Ranks, int]:
    fixed_count = _composition_count(masses[1], _FIXED_COMPONENTS)
    bundle_count = _bundle_count(masses[2])
    edge_count = _edge_count(total - sum(masses))
    head, edge_rank = divmod(rank, edge_count)
    head, bundle_rank = divmod(head, bundle_count)
    vertex_rank, fixed_rank = divmod(head, fixed_count)
    return (vertex_rank, fixed_rank, bundle_rank), edge_rank


def _unrank_block(total: int, masses: _Masses, rank: int) -> _State:
    ranks, edge_rank = _component_ranks(total, masses, rank)
    fixed = _composition_unrank(masses[1], _FIXED_COMPONENTS, ranks[1])
    bundle = _bundle_unrank(masses[2], ranks[2])
    assert fixed is not None
    assert bundle is not None
    vertices = _vertices_of_mass(masses[0])[ranks[0]]
    return vertices, fixed, bundle, edge_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for masses in _mass_blocks(total):
        block = _block_count(total, masses)
        if remaining >= block:
            remaining -= block
            continue
        return _unrank_block(total, masses, remaining)
    raise AssertionError


def test_s6_s4_full_bundle_counts_match_nested_factorization() -> None:
    """Quadruple bundle counts and edge totals match reviewed prerequisites."""
    expected_bundle = (1, 0, 0, 0, 6, 0, 0, 0, 21, 0, 0, 0, 56, 0, 0)
    observed_bundle = tuple(
        _bundle_count(mass) for mass in range(_MAXIMUM_MASS + 1)
    )
    assert observed_bundle == expected_bundle
    assert _edge_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_EDGE_COUNT


def test_s6_s4_full_bundle_rank_exhausts_small_abstract_domains() -> None:
    """One bundle key plus local S4 ranks form one dense full index."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        count = _class_count(total)
        for rank in range(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s4_full_bundle_rank_roundtrips_through_fourteen() -> None:
    """Counts and representative abstract ranks reach the mass-14 boundary."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    for total, count in enumerate(observed):
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        if count == 0:
            continue
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
