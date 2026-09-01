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
#   - Dense S6 ranking for vertex multiplicity partition (3,1,1,1).
# - Must-Not:
#   - Claim ranking for larger Young stabilizers.
# - Allows:
#   - Inputs: sextuple joint-count mass 0 through 14 in the order-six stratum.
#   - Outputs: dense rank/unrank modulo the repeated-vertex S3 action.
#   - Side effects: none.
# - Split-When:
#   - Another Young stabilizer receives a constructive rank.
# - Merge-When:
#   - Complete dense S6 ranking owns every vertex multiplicity stratum.
# - Summary:
#   - Prefix repeated-vertex blocks around a three-bundle residual multiset.
# - Description:
#   - The residual action has 10 fixed scalars and 14 synchronized triplets.
# - Usage:
#   - Constructive S6 slice for the Young stabilizer S3.
# - Defaults:
#   - Direct residual orbits stop at mass two; full exhaustion stops at six.
#

"""Dense S6 ranking for the order-six Young-stabilizer vertex stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import permutations
from math import comb

_ARITY = 6
_FIXED_COMPONENTS = 10
_BUNDLE_COMPONENTS = 14
_RESIDUAL_COMPONENTS = _FIXED_COMPONENTS + 3 * _BUNDLE_COMPONENTS
_MAXIMUM_MASS = 14
_EXHAUSTIVE_RESIDUAL_MASS = 2
_EXHAUSTIVE_TOTAL_MASS = 6
_WIDTH_FOURTEEN_COUNT = 89_182_770_767
_VERTEX_PARTITION = (3, 1, 1, 1)
_EXPECTED_COUNTS = {
    4: 3,
    5: 82,
    6: 1_491,
    7: 22_028,
    8: 277_480,
    9: 3_037_588,
    10: 29_285_304,
    11: 251_670_820,
    12: 1_949_654_530,
    13: 13_754_973_430,
    14: 89_182_770_767,
}

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Vector = tuple[int, ...]
type _Bundles = tuple[_Vector, _Vector, _Vector]
type _ResidualState = tuple[_Vector, _Vector, _Vector, _Vector]
type _State = tuple[_Vertices, _Vector, _Vector, _Vector, _Vector]
type _Permutation = tuple[int, int, int, int, int, int]

_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)
_RESIDUAL_LABELS = tuple(
    symbol
    for symbol in range(1 << _ARITY)
    if symbol.bit_count() not in {1, _ARITY - 1}
)
_ACTIVE_ENDPOINTS = (0, 1, 2)
_S3 = tuple(
    (order[0], order[1], order[2], 3, 4, 5)
    for order in permutations(_ACTIVE_ENDPOINTS)
)


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
        rank += sum(
            _composition_count(remaining - earlier, tail_parts)
            for earlier in range(value)
        )
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
    if (
        any(value < 0 or value >= population for value in values)
        or tuple(sorted(values)) != values
    ):
        return None
    shifted = tuple(value + index for index, value in enumerate(values))
    universe = population + size - 1
    rank = 0
    previous = -1
    for index, value in enumerate(shifted):
        remaining = size - index - 1
        rank += sum(
            comb(universe - candidate - 1, remaining)
            for candidate in range(previous + 1, value)
        )
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
    first, second, third = masses
    return (
        _composition_count(first, _BUNDLE_COMPONENTS),
        _composition_count(second, _BUNDLE_COMPONENTS),
        _composition_count(third, _BUNDLE_COMPONENTS),
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


def _bundle_count(total: int) -> int:
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


def _bundle_rank(bundles: _Bundles) -> int | None:
    if any(len(bundle) != _BUNDLE_COMPONENTS for bundle in bundles):
        return None
    if any(value < 0 for bundle in bundles for value in bundle):
        return None
    keys = sorted(_bundle_key(bundle) for bundle in bundles)
    masses = keys[0][0], keys[1][0], keys[2][0]
    ranks = keys[0][1], keys[1][1], keys[2][1]
    prefix = sum(
        _mass_block_count(candidate)
        for candidate in _mass_triples(sum(masses))
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


def _bundle_unrank(total: int, rank: int) -> _Bundles | None:
    if rank < 0 or rank >= _bundle_count(total):
        return None
    remaining = rank
    for masses in _mass_triples(total):
        block = _mass_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        ranks = _mass_block_unrank(masses, remaining)
        bundles = tuple(
            _composition_unrank(mass, _BUNDLE_COMPONENTS, item_rank)
            for mass, item_rank in zip(masses, ranks, strict=True)
        )
        assert all(bundle is not None for bundle in bundles)
        first, second, third = bundles
        assert first is not None
        assert second is not None
        assert third is not None
        return first, second, third
    raise AssertionError


def _residual_count(total: int) -> int:
    return sum(
        _composition_count(fixed_mass, _FIXED_COMPONENTS)
        * _bundle_count(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def _residual_rank(state: _ResidualState) -> int | None:
    fixed, first, second, third = state
    if len(fixed) != _FIXED_COMPONENTS:
        return None
    fixed_mass = sum(fixed)
    fixed_rank = _composition_rank(fixed, fixed_mass)
    bundle_rank = _bundle_rank((first, second, third))
    if fixed_rank is None or bundle_rank is None:
        return None
    bundle_mass = sum((*first, *second, *third))
    total = fixed_mass + bundle_mass
    prefix = sum(
        _composition_count(mass, _FIXED_COMPONENTS)
        * _bundle_count(total - mass)
        for mass in range(fixed_mass)
    )
    return prefix + fixed_rank * _bundle_count(bundle_mass) + bundle_rank


def _residual_unrank(total: int, rank: int) -> _ResidualState | None:
    if rank < 0 or rank >= _residual_count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        bundle_mass = total - fixed_mass
        bundle_count = _bundle_count(bundle_mass)
        block = _composition_count(fixed_mass, _FIXED_COMPONENTS) * bundle_count
        if remaining >= block:
            remaining -= block
            continue
        fixed_rank, bundle_rank = divmod(remaining, bundle_count)
        fixed = _composition_unrank(fixed_mass, _FIXED_COMPONENTS, fixed_rank)
        bundles = _bundle_unrank(bundle_mass, bundle_rank)
        assert fixed is not None
        assert bundles is not None
        return fixed, bundles[0], bundles[1], bundles[2]
    raise AssertionError


def _fixed_count_from_cycles(total: int, lengths: tuple[int, ...]) -> int:
    coefficients = [1] + [0] * total
    for cycle_length in lengths:
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, total - degree + 1, cycle_length):
                next_coefficients[degree + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[total]


def _burnside_residual_count(total: int) -> int:
    identity = _composition_count(total, _RESIDUAL_COMPONENTS)
    transposition = _fixed_count_from_cycles(
        total,
        (1,) * 24 + (2,) * 14,
    )
    three_cycle = _fixed_count_from_cycles(total, (1,) * 10 + (3,) * 14)
    return (identity + 3 * transposition + 2 * three_cycle) // 6


@cache
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


def _vertex_partition(values: tuple[_Pair, ...]) -> tuple[int, ...]:
    return tuple(sorted(Counter(values).values(), reverse=True))


@cache
def _vertices_of_mass(mass: int) -> tuple[_Vertices, ...]:
    return tuple(
        _as_vertices(values)
        for values in _vertex_sequences_from(0, _ARITY, mass)
        if sum(sum(pair) for pair in values) == mass
        and _vertex_partition(values) == _VERTEX_PARTITION
    )


def _class_count(total: int) -> int:
    return sum(
        len(_vertices_of_mass(vertex_mass))
        * _residual_count(total - vertex_mass)
        for vertex_mass in range(total + 1)
    )


def _vertex_rank(vertices: _Vertices, mass: int) -> int | None:
    try:
        return _vertices_of_mass(mass).index(vertices)
    except ValueError:
        return None


def _state_data(total: int, state: _State) -> tuple[int, int, int, int] | None:
    vertices = state[0]
    residual: _ResidualState = state[1], state[2], state[3], state[4]
    vertex_mass = sum(sum(pair) for pair in vertices)
    residual_mass = total - vertex_mass
    vertex_rank = _vertex_rank(vertices, vertex_mass)
    residual_rank = _residual_rank(residual)
    residual_total = sum(value for vector in residual for value in vector)
    valid_mass = vertex_mass <= total and residual_total == residual_mass
    valid_ranks = vertex_rank is not None and residual_rank is not None
    if not valid_mass or not valid_ranks:
        return None
    assert vertex_rank is not None
    assert residual_rank is not None
    return vertex_mass, vertex_rank, residual_mass, residual_rank


def _rank(total: int, state: _State) -> int | None:
    data = _state_data(total, state)
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
        fixed, first, second, third = residual
        return (
            _vertices_of_mass(vertex_mass)[vertex_rank],
            fixed,
            first,
            second,
            third,
        )
    raise AssertionError


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _permuted_symbol(symbol: int, order: _Permutation) -> int:
    bits = tuple(
        (symbol >> (_ARITY - endpoint - 1)) & 1
        for endpoint in range(_ARITY)
    )
    result = 0
    for source in order:
        result = (result << 1) | bits[source]
    return result


def _cycle_histogram(order: _Permutation) -> Counter[int]:
    unseen = set(_RESIDUAL_LABELS)
    result: Counter[int] = Counter()
    while unseen:
        current = min(unseen)
        orbit: set[int] = set()
        while current not in orbit:
            orbit.add(current)
            current = _permuted_symbol(current, order)
        unseen -= orbit
        result[len(orbit)] += 1
    return result


def _endpoint_cycle_type(order: _Permutation) -> tuple[int, ...]:
    unseen = set(_ACTIVE_ENDPOINTS)
    lengths: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = order[current]
            length += 1
        lengths.append(length)
    return tuple(sorted(lengths))


def test_s6_order_six_residual_action_is_three_bundle_multiset() -> None:
    """S3 acts as 10 fixed scalars plus 14 synchronized triplets."""
    expected: dict[tuple[int, ...], Counter[int]] = {
        (1, 1, 1): Counter({1: _RESIDUAL_COMPONENTS}),
        (1, 2): Counter({1: 24, 2: 14}),
        (3,): Counter({1: _FIXED_COMPONENTS, 3: _BUNDLE_COMPONENTS}),
    }
    for order in _S3:
        assert _cycle_histogram(order) == expected[_endpoint_cycle_type(order)]


def test_s6_order_six_residual_rank_matches_direct_small_orbits() -> None:
    """Small residual assignments collapse to one contiguous S3 rank."""
    for total in range(_EXHAUSTIVE_RESIDUAL_MASS + 1):
        representatives: dict[int, set[_Vector]] = {}
        for vector in _weak_compositions(total, _RESIDUAL_COMPONENTS):
            fixed = vector[:_FIXED_COMPONENTS]
            start = _FIXED_COMPONENTS
            bundles = tuple(
                vector[
                    start + index * _BUNDLE_COMPONENTS :
                    start + (index + 1) * _BUNDLE_COMPONENTS
                ]
                for index in range(3)
            )
            first, second, third = bundles
            rank = _residual_rank((fixed, first, second, third))
            assert rank is not None
            orbit = {
                (
                    *fixed,
                    *bundles[order[0]],
                    *bundles[order[1]],
                    *bundles[order[2]],
                )
                for order in permutations(range(3))
            }
            if rank not in representatives:
                representatives[rank] = orbit
            assert representatives[rank] == orbit
        count = _residual_count(total)
        assert set(representatives) == set(range(count))
        assert count == _burnside_residual_count(total)


def test_s6_order_six_rank_exhausts_small_full_strata() -> None:
    """The complete S3 stratum is dense through mass six."""
    for total in range(_EXHAUSTIVE_TOTAL_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_order_six_rank_roundtrips_through_mass_fourteen() -> None:
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


def test_s6_order_six_counts_match_reviewed_sequence() -> None:
    """The mass-four-through-fourteen counts match the decomposition."""
    observed = {
        mass: _class_count(mass)
        for mass in range(_MAXIMUM_MASS + 1)
        if _class_count(mass) != 0
    }
    assert observed == _EXPECTED_COUNTS
