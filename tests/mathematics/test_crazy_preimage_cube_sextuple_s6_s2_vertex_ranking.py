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
#   - Dense S6 ranking for vertex multiplicity partition (2,1,1,1,1).
# - Must-Not:
#   - Claim ranking for larger Young stabilizers.
# - Allows:
#   - Inputs: sextuple joint-count mass 0 through 14 in the order-two stratum.
#   - Outputs: dense rank/unrank modulo the one repeated-vertex transposition.
#   - Side effects: none.
# - Split-When:
#   - Another Young stabilizer receives a constructive rank.
# - Merge-When:
#   - Complete dense S6 ranking owns every vertex multiplicity stratum.
# - Summary:
#   - Prefix repeated-vertex blocks around one coupled residual involution.
# - Description:
#   - The residual action has 24 fixed scalars and 14 simultaneous swaps.
# - Usage:
#   - Constructive S6 slice for the Young stabilizer S2.
# - Defaults:
#   - Direct residual orbits stop at mass three; full exhaustion stops at eight.
#

"""Dense S6 ranking for the order-two Young-stabilizer vertex stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from math import comb

_ARITY = 6
_FIXED_COMPONENTS = 24
_SIDE_COMPONENTS = 14
_RESIDUAL_COMPONENTS = _FIXED_COMPONENTS + 2 * _SIDE_COMPONENTS
_MAXIMUM_MASS = 14
_EXHAUSTIVE_RESIDUAL_MASS = 3
_EXHAUSTIVE_TOTAL_MASS = 8
_WIDTH_FOURTEEN_COUNT = 8_308_559_181
_VERTEX_PARTITION = (2, 1, 1, 1, 1)
_EXPECTED_COUNTS = {
    6: 3,
    7: 134,
    8: 3_375,
    9: 61_650,
    10: 894_765,
    11: 10_816_206,
    12: 112_245_675,
    13: 1_022_182_400,
    14: 8_308_559_181,
}

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Vector = tuple[int, ...]
type _ResidualState = tuple[_Vector, _Vector, _Vector]
type _State = tuple[_Vertices, _Vector, _Vector, _Vector]
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
    count = sum(
        _composition_count(left_mass, _SIDE_COMPONENTS)
        * _composition_count(total - left_mass, _SIDE_COMPONENTS)
        for left_mass in range((total + 1) // 2)
    )
    if total % 2 == 0:
        side_count = _composition_count(total // 2, _SIDE_COMPONENTS)
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


def _movable_rank(left: _Vector, right: _Vector) -> int | None:
    if (
        len(left) != _SIDE_COMPONENTS
        or len(right) != _SIDE_COMPONENTS
        or any(value < 0 for value in (*left, *right))
    ):
        return None
    if _side_key(right) < _side_key(left):
        left, right = right, left
    left_mass, left_rank = _side_key(left)
    right_mass, right_rank = _side_key(right)
    total = left_mass + right_mass
    prefix = sum(
        _composition_count(mass, _SIDE_COMPONENTS)
        * _composition_count(total - mass, _SIDE_COMPONENTS)
        for mass in range(left_mass)
        if mass < total - mass
    )
    if left_mass < right_mass:
        offset = (
            left_rank * _composition_count(right_mass, _SIDE_COMPONENTS)
            + right_rank
        )
    else:
        side_count = _composition_count(left_mass, _SIDE_COMPONENTS)
        offset = _equal_mass_pair_rank(left_rank, right_rank, side_count)
    return prefix + offset


def _side_pair(
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
        return _side_pair(
            left_mass,
            right_mass,
            left_rank=left_rank,
            right_rank=right_rank,
        )
    half = total // 2
    side_count = _composition_count(half, _SIDE_COMPONENTS)
    left_rank, right_rank = _equal_mass_pair_unrank(remaining, side_count)
    return _side_pair(
        half,
        half,
        left_rank=left_rank,
        right_rank=right_rank,
    )


def _residual_count(total: int) -> int:
    return sum(
        _composition_count(fixed_mass, _FIXED_COMPONENTS)
        * _unordered_pair_count(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def _residual_rank(state: _ResidualState) -> int | None:
    fixed, left, right = state
    if len(fixed) != _FIXED_COMPONENTS:
        return None
    fixed_mass = sum(fixed)
    fixed_rank = _composition_rank(fixed, fixed_mass)
    movable_rank = _movable_rank(left, right)
    if fixed_rank is None or movable_rank is None:
        return None
    movable_mass = sum(left) + sum(right)
    total = fixed_mass + movable_mass
    prefix = sum(
        _composition_count(mass, _FIXED_COMPONENTS)
        * _unordered_pair_count(total - mass)
        for mass in range(fixed_mass)
    )
    return (
        prefix
        + fixed_rank * _unordered_pair_count(movable_mass)
        + movable_rank
    )


def _residual_unrank(total: int, rank: int) -> _ResidualState | None:
    if rank < 0 or rank >= _residual_count(total):
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


def _burnside_residual_count(total: int) -> int:
    identity = _composition_count(total, _RESIDUAL_COMPONENTS)
    fixed = sum(
        _composition_count(fixed_mass, _FIXED_COMPONENTS)
        * _composition_count((total - fixed_mass) // 2, _SIDE_COMPONENTS)
        for fixed_mass in range(total + 1)
        if (total - fixed_mass) % 2 == 0
    )
    return (identity + fixed) // 2


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
    residual: _ResidualState = state[1], state[2], state[3]
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
        fixed, left, right = residual
        return _vertices_of_mass(vertex_mass)[vertex_rank], fixed, left, right
    raise AssertionError


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _as_permutation(order: tuple[int, ...]) -> _Permutation:
    assert len(order) == _ARITY
    first, second, third, fourth, fifth, sixth = order
    return first, second, third, fourth, fifth, sixth


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


def test_s6_order_two_residual_action_is_one_coupled_involution() -> None:
    """Every endpoint transposition induces 24 fixed and 14 swapped pairs."""
    identity = tuple(range(_ARITY))
    for left in range(_ARITY):
        for right in range(left + 1, _ARITY):
            order = list(identity)
            order[left], order[right] = order[right], order[left]
            assert _cycle_histogram(_as_permutation(tuple(order))) == Counter({
                1: _FIXED_COMPONENTS,
                2: _SIDE_COMPONENTS,
            })


def test_s6_order_two_residual_rank_matches_direct_small_orbits() -> None:
    """Small residual assignments collapse to one contiguous involution rank."""
    for total in range(_EXHAUSTIVE_RESIDUAL_MASS + 1):
        representatives: dict[int, set[_Vector]] = {}
        for vector in _weak_compositions(total, _RESIDUAL_COMPONENTS):
            fixed = vector[:_FIXED_COMPONENTS]
            left_end = _FIXED_COMPONENTS + _SIDE_COMPONENTS
            left = vector[_FIXED_COMPONENTS:left_end]
            right = vector[-_SIDE_COMPONENTS:]
            rank = _residual_rank((fixed, left, right))
            assert rank is not None
            swapped = (*fixed, *right, *left)
            orbit = {vector, swapped}
            if rank not in representatives:
                representatives[rank] = orbit
            assert representatives[rank] == orbit
        count = _residual_count(total)
        assert set(representatives) == set(range(count))
        assert count == _burnside_residual_count(total)


def test_s6_order_two_rank_exhausts_small_full_strata() -> None:
    """The complete order-two stratum is dense through mass eight."""
    for total in range(_EXHAUSTIVE_TOTAL_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_order_two_rank_roundtrips_through_mass_fourteen() -> None:
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


def test_s6_order_two_counts_match_reviewed_sequence() -> None:
    """The mass-six-through-fourteen counts match the decomposition."""
    observed = {
        mass: _class_count(mass)
        for mass in range(_MAXIMUM_MASS + 1)
        if _class_count(mass) != 0
    }
    assert observed == _EXPECTED_COUNTS
