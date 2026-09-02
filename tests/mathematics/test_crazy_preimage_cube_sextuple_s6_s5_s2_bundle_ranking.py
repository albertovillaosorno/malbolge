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
#   - Dense rank/unrank for the (5,1)/(2,1,1,1) S2 second-layer S6 stratum.
# - Must-Not:
#   - Claim ranking for the other five open second-layer S5 stabilizers.
# - Allows:
#   - Inputs: canonical top vertices, two fixed scalars, one repeated bundle,
#     three singleton bundles, and one fixed-plus-side-pair edge quotient.
#   - Outputs: exact dense full-S6 rank/unrank for this second-layer stratum.
#   - Side effects: none.
# - Split-When:
#   - Another second-layer S5 stabilizer receives constructive rank/unrank.
# - Merge-When:
#   - Complete dense ranking owns the full (5,1) S6 stratum.
# - Summary:
#   - Rank pair/singleton bundles and one shared edge-side involution.
# - Description:
#   - S2 swaps two twelve-scalar edge sides; sixteen edge scalars stay fixed.
# - Usage:
#   - Constructive order-two second-layer slice of the nested S5 S6 stratum.
# - Defaults:
#   - Exhaustive abstract ranks stop at mass five; arithmetic reaches fourteen.
#

"""Dense S2 second-layer ranking for the S6 (5,1) stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import combinations
from itertools import product
from math import comb

_ARITY = 6
_FIXED_COMPONENTS = 2
_EDGE_FIXED_COMPONENTS = 16
_SIDE_COMPONENTS = 12
_REPEAT_COUNT = 2
_MAXIMUM_MASS = 14
_EXHAUSTIVE_RANK_MASS = 5
_TOP_PARTITION = (5, 1)
_WIDTH_FOURTEEN_COUNT = 26_007_971_192
_WIDTH_FOURTEEN_EDGE_COUNT = 1_202_396_111_272
_EXPECTED_COUNTS = (
    0,
    0,
    0,
    0,
    0,
    6,
    221,
    4_642,
    71_127,
    868_666,
    8_857_824,
    77_732_592,
    600_189_773,
    4_147_764_698,
    26_007_971_192,
)
_EXPECTED_BUNDLE_COUNTS = (
    0,
    0,
    0,
    0,
    3,
    16,
    47,
    112,
    233,
    452,
    794,
    1_364,
    2_208,
    3_478,
    5_279,
)
_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Bundle = tuple[int, int]
type _BundleState = tuple[_Bundle, _Bundle, _Bundle, _Bundle]
type _Vector = tuple[int, ...]
type _EdgeState = tuple[_Vector, _Vector, _Vector]
type _State = tuple[_Vertices, _Vector, _BundleState, _EdgeState]


def _composition_count(total: int, parts: int) -> int:
    return comb(total + parts - 1, parts - 1) if total >= 0 and parts > 0 else 0


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


def _rep_rank(values: tuple[int, ...], population: int) -> int:
    shifted = tuple(value + index for index, value in enumerate(values))
    universe = population + len(values) - 1
    rank = 0
    previous = -1
    for index, value in enumerate(shifted):
        remaining = len(values) - index - 1
        for candidate in range(previous + 1, value):
            rank += comb(universe - candidate - 1, remaining)
        previous = value
    return rank


def _rep_unrank(population: int, size: int, rank: int) -> tuple[int, ...]:
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


def _bundle_key(bundle: _Bundle) -> tuple[int, int]:
    return sum(bundle), bundle[0]


def _bundles_of_mass(mass: int) -> tuple[_Bundle, ...]:
    return tuple((first, mass - first) for first in range(mass + 1))


def _mass_triples(total: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (first, second, total - first - second)
        for first in range(total + 1)
        for second in range(first, total + 1)
        if second <= total - first - second
    )


def _singleton_triples(
    masses: tuple[int, int, int],
    excluded: _Bundle,
) -> tuple[tuple[_Bundle, _Bundle, _Bundle], ...]:
    pools = tuple(
        tuple(bundle for bundle in _bundles_of_mass(mass) if bundle != excluded)
        for mass in masses
    )
    result = tuple(product(pools[0], pools[1], pools[2]))
    if masses[0] == masses[2]:
        result = tuple(combinations(pools[0], 3))
    elif masses[0] == masses[1]:
        result = tuple(
            (*pair, last)
            for pair in combinations(pools[0], 2)
            for last in pools[2]
        )
    elif masses[1] == masses[2]:
        result = tuple(
            (first, *pair)
            for first in pools[0]
            for pair in combinations(pools[1], 2)
        )
    return result


def _states_for_repeated(
    total: int,
    repeated: _Bundle,
) -> tuple[_BundleState, ...]:
    singleton_total = total - _REPEAT_COUNT * sum(repeated)
    return tuple(
        (repeated, *singles)
        for masses in _mass_triples(singleton_total)
        for singles in _singleton_triples(masses, repeated)
    )


@cache
def _bundle_states(total: int) -> tuple[_BundleState, ...]:
    states: list[_BundleState] = []
    for repeated_mass in range(total // _REPEAT_COUNT + 1):
        for repeated in _bundles_of_mass(repeated_mass):
            states.extend(_states_for_repeated(total, repeated))
    return tuple(sorted(set(states)))


@cache
def _bundle_rank_map(total: int) -> dict[_BundleState, int]:
    return {state: rank for rank, state in enumerate(_bundle_states(total))}


def _bundle_count(total: int) -> int:
    return len(_bundle_states(total))


def _bundle_rank(state: _BundleState) -> int | None:
    repeated, *single_values = state
    singles = tuple(sorted(single_values, key=_bundle_key))
    canonical = repeated, singles[0], singles[1], singles[2]
    total = _REPEAT_COUNT * sum(repeated) + sum(
        sum(bundle) for bundle in singles
    )
    return _bundle_rank_map(total).get(canonical)


def _bundle_unrank(total: int, rank: int) -> _BundleState | None:
    states = _bundle_states(total)
    return states[rank] if 0 <= rank < len(states) else None


def _side_count(total: int) -> int:
    return _composition_count(total, _SIDE_COMPONENTS)


def _side_mass_pairs(total: int) -> tuple[tuple[int, int], ...]:
    return tuple((left, total - left) for left in range(total // 2 + 1))


def _side_pair_block_count(masses: tuple[int, int]) -> int:
    left = _side_count(masses[0])
    right = _side_count(masses[1])
    return comb(left + 1, 2) if masses[0] == masses[1] else left * right


@cache
def _side_pair_count(total: int) -> int:
    return sum(
        _side_pair_block_count(masses) for masses in _side_mass_pairs(total)
    )


def _side_pair_rank(left: _Vector, right: _Vector) -> int | None:
    if len(left) != _SIDE_COMPONENTS or len(right) != _SIDE_COMPONENTS:
        return None
    if any(value < 0 for value in (*left, *right)):
        return None
    items = sorted(
        (left, right),
        key=lambda vector: (
            sum(vector),
            _composition_rank(vector, _SIDE_COMPONENTS),
        ),
    )
    masses = sum(items[0]), sum(items[1])
    left_rank = _composition_rank(items[0], _SIDE_COMPONENTS)
    right_rank = _composition_rank(items[1], _SIDE_COMPONENTS)
    assert left_rank is not None
    assert right_rank is not None
    prefix = sum(
        _side_pair_block_count(candidate)
        for candidate in _side_mass_pairs(sum(masses))
        if candidate < masses
    )
    local = left_rank * _side_count(masses[1]) + right_rank
    if masses[0] == masses[1]:
        local = _rep_rank((left_rank, right_rank), _side_count(masses[0]))
    return prefix + local


def _side_pair_unrank(total: int, rank: int) -> tuple[_Vector, _Vector] | None:
    if rank < 0 or rank >= _side_pair_count(total):
        return None
    remaining = rank
    for masses in _side_mass_pairs(total):
        block = _side_pair_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        if masses[0] == masses[1]:
            ranks = _rep_unrank(_side_count(masses[0]), 2, remaining)
        else:
            ranks = divmod(remaining, _side_count(masses[1]))
        left = _composition_unrank(masses[0], _SIDE_COMPONENTS, ranks[0])
        right = _composition_unrank(masses[1], _SIDE_COMPONENTS, ranks[1])
        assert left is not None
        assert right is not None
        return left, right
    raise AssertionError


def _edge_count(total: int) -> int:
    return sum(
        _composition_count(fixed_mass, _EDGE_FIXED_COMPONENTS)
        * _side_pair_count(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def _edge_rank(state: _EdgeState) -> int | None:
    fixed, left, right = state
    fixed_rank = _composition_rank(fixed, _EDGE_FIXED_COMPONENTS)
    pair_rank = _side_pair_rank(left, right)
    if fixed_rank is None or pair_rank is None:
        return None
    fixed_mass = sum(fixed)
    pair_mass = sum(left) + sum(right)
    prefix = sum(
        _composition_count(candidate, _EDGE_FIXED_COMPONENTS)
        * _side_pair_count(fixed_mass + pair_mass - candidate)
        for candidate in range(fixed_mass)
    )
    return prefix + fixed_rank * _side_pair_count(pair_mass) + pair_rank


def _edge_unrank(total: int, rank: int) -> _EdgeState | None:
    if rank < 0 or rank >= _edge_count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        pair_mass = total - fixed_mass
        pair_count = _side_pair_count(pair_mass)
        block = (
            _composition_count(fixed_mass, _EDGE_FIXED_COMPONENTS) * pair_count
        )
        if remaining >= block:
            remaining -= block
            continue
        fixed_rank, pair_rank = divmod(remaining, pair_count)
        fixed = _composition_unrank(
            fixed_mass, _EDGE_FIXED_COMPONENTS, fixed_rank
        )
        pair = _side_pair_unrank(pair_mass, pair_rank)
        assert fixed is not None
        assert pair is not None
        return fixed, pair[0], pair[1]
    raise AssertionError


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


def _burnside_edge_count(total: int) -> int:
    identity = _composition_count(total, 40)
    involution = _fixed_count((1,) * 16 + (2,) * 12, total)
    return (identity + involution) // 2


def _vertex_sequences_from(
    start: int, slots: int, remaining: int
) -> tuple[tuple[_Pair, ...], ...]:
    if slots == 0:
        return ((),)
    result: list[tuple[_Pair, ...]] = []
    for index in range(start, len(_PAIR_VALUES)):
        pair = _PAIR_VALUES[index]
        if sum(pair) > remaining:
            continue
        result.extend(
            (pair, *suffix)
            for suffix in _vertex_sequences_from(
                index, slots - 1, remaining - sum(pair)
            )
        )
    return tuple(result)


def _as_vertices(values: tuple[_Pair, ...]) -> _Vertices:
    first, second, third, fourth, fifth, sixth = values
    return first, second, third, fourth, fifth, sixth


@cache
def _vertices_of_mass(mass: int) -> tuple[_Vertices, ...]:
    return tuple(
        _as_vertices(values)
        for values in _vertex_sequences_from(0, _ARITY, mass)
        if sum(sum(pair) for pair in values) == mass
        and tuple(sorted(Counter(values).values(), reverse=True))
        == _TOP_PARTITION
    )


@cache
def _residual_blocks(total: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (fixed_mass, bundle_mass, total - fixed_mass - bundle_mass)
        for fixed_mass in range(total + 1)
        for bundle_mass in range(total - fixed_mass + 1)
    )


def _residual_block_count(masses: tuple[int, int, int]) -> int:
    return (
        _composition_count(masses[0], _FIXED_COMPONENTS)
        * _bundle_count(masses[1])
        * _edge_count(masses[2])
    )


@cache
def _residual_count(total: int) -> int:
    return sum(
        _residual_block_count(masses) for masses in _residual_blocks(total)
    )


def _residual_rank(
    fixed: _Vector, bundles: _BundleState, edges: _EdgeState
) -> int | None:
    fixed_rank = _composition_rank(fixed, _FIXED_COMPONENTS)
    bundle_rank = _bundle_rank(bundles)
    edge_rank = _edge_rank(edges)
    if fixed_rank is None or bundle_rank is None or edge_rank is None:
        return None
    bundle_mass = _REPEAT_COUNT * sum(bundles[0]) + sum(
        sum(bundle) for bundle in bundles[1:]
    )
    edge_mass = sum(edges[0]) + sum(edges[1]) + sum(edges[2])
    masses = sum(fixed), bundle_mass, edge_mass
    prefix = sum(
        _residual_block_count(candidate)
        for candidate in _residual_blocks(sum(masses))
        if candidate < masses
    )
    local = fixed_rank * _bundle_count(bundle_mass) + bundle_rank
    return prefix + local * _edge_count(edge_mass) + edge_rank


def _residual_unrank_block(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[_Vector, _BundleState, _EdgeState]:
    edge_count = _edge_count(masses[2])
    bundle_count = _bundle_count(masses[1])
    head, edge_rank = divmod(rank, edge_count)
    fixed_rank, bundle_rank = divmod(head, bundle_count)
    fixed = _composition_unrank(masses[0], _FIXED_COMPONENTS, fixed_rank)
    bundles = _bundle_unrank(masses[1], bundle_rank)
    edges = _edge_unrank(masses[2], edge_rank)
    assert fixed is not None
    assert bundles is not None
    assert edges is not None
    return fixed, bundles, edges


def _residual_unrank(
    total: int, rank: int
) -> tuple[_Vector, _BundleState, _EdgeState] | None:
    if rank < 0 or rank >= _residual_count(total):
        return None
    remaining = rank
    for masses in _residual_blocks(total):
        block = _residual_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        return _residual_unrank_block(masses, remaining)
    raise AssertionError


@cache
def _class_count(total: int) -> int:
    return sum(
        len(_vertices_of_mass(vertex_mass))
        * _residual_count(total - vertex_mass)
        for vertex_mass in range(total + 1)
    )


def _rank(total: int, state: _State) -> int | None:
    vertices, fixed, bundles, edges = state
    vertex_mass = sum(sum(pair) for pair in vertices)
    try:
        vertex_rank = _vertices_of_mass(vertex_mass).index(vertices)
    except ValueError:
        return None
    residual_rank = _residual_rank(fixed, bundles, edges)
    residual_mass = total - vertex_mass
    if (
        residual_rank is None
        or residual_mass < 0
        or residual_rank >= _residual_count(residual_mass)
    ):
        return None
    prefix = sum(
        len(_vertices_of_mass(candidate)) * _residual_count(total - candidate)
        for candidate in range(vertex_mass)
    )
    return prefix + vertex_rank * _residual_count(residual_mass) + residual_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for vertex_mass in range(total + 1):
        vertices = _vertices_of_mass(vertex_mass)
        residual_count = _residual_count(total - vertex_mass)
        block = len(vertices) * residual_count
        if remaining >= block:
            remaining -= block
            continue
        vertex_rank, residual_rank = divmod(remaining, residual_count)
        residual = _residual_unrank(total - vertex_mass, residual_rank)
        assert residual is not None
        return vertices[vertex_rank], residual[0], residual[1], residual[2]
    raise AssertionError


def test_s6_s5_s2_bundle_and_edge_counts_match_factorization() -> None:
    """Bundle and shared-involution edge counts match the factorization."""
    assert (
        tuple(_bundle_count(mass) for mass in range(15))
        == _EXPECTED_BUNDLE_COUNTS
    )
    for mass in range(_MAXIMUM_MASS + 1):
        assert _edge_count(mass) == _burnside_edge_count(mass)
    assert _edge_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_EDGE_COUNT


def test_s6_s5_s2_rank_exhausts_small_abstract_domains() -> None:
    """The nested S2 rank is contiguous through mass five."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s5_s2_rank_roundtrips_through_fourteen() -> None:
    """Counts and representative ranks reach the reviewed mass-14 boundary."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    for total, count in enumerate(observed):
        if count == 0:
            continue
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
