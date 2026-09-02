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
#   - Dense ranks for two widened full-S5 stabilizers absent at mass fourteen.
# - Must-Not:
#   - Re-rank any stabilizer type populated at mass fourteen.
# - Allows:
#   - Inputs: D10 and full-S5 fixed K5 edge values through mass fourteen.
#   - Outputs: dense exact D10 and full-S5 local ranks.
#   - Side effects: none.
# - Split-When:
#   - Another low-mass-only exact stabilizer appears in the checked domain.
# - Merge-When:
#   - Complete widened full-S5 ranking owns all residual masses directly.
# - Summary:
#   - Rank distinct D10 orbit values and one full-S5 repeated edge value.
# - Description:
#   - D10 has two five-edge orbits; full S5 has one ten-edge orbit.
# - Usage:
#   - Supplies the only two extra stabilizer strata needed below mass fourteen.
# - Defaults:
#   - Exact ranks are empty outside their reviewed divisible-mass supports.
#

"""Dense low-mass-only exact-stabilizer ranks for widened full-S5 edges."""

from __future__ import annotations

from itertools import permutations
from math import comb

_ARITY = 5
_EDGE_COMPONENTS = 4
_MAXIMUM_MASS = 14
_D10_ORDER = 10
_S5_ORDER = 120
_EXPECTED_D10 = (0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 16, 0, 0, 0, 0)
_EXPECTED_S5 = (1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0)

type _Vector = tuple[int, int, int, int]
type _D10State = tuple[_Vector, _Vector]

_EDGES = tuple(
    (left, right) for left in range(_ARITY) for right in range(left + 1, _ARITY)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_S5 = tuple(permutations(range(_ARITY)))


def _ordered_edge(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


_CYCLE_EDGES = frozenset(
    _EDGE_INDEX[_ordered_edge(vertex, (vertex + 1) % _ARITY)]
    for vertex in range(_ARITY)
)
_DIAGONAL_EDGES = frozenset(range(len(_EDGES))) - _CYCLE_EDGES


def _composition_count(total: int) -> int:
    return comb(total + _EDGE_COMPONENTS - 1, _EDGE_COMPONENTS - 1)


def _composition_rank(value: _Vector) -> int:
    remaining = sum(value)
    rank = 0
    for index, component in enumerate(value[:-1]):
        tail = _EDGE_COMPONENTS - index - 1
        rank += sum(
            comb(remaining - earlier + tail - 1, tail - 1)
            for earlier in range(component)
        )
        remaining -= component
    return rank


def _composition_unrank(total: int, rank: int) -> _Vector | None:
    if rank < 0 or rank >= _composition_count(total):
        return None
    remaining_total = total
    remaining_rank = rank
    values: list[int] = []
    for index in range(_EDGE_COMPONENTS - 1):
        tail = _EDGE_COMPONENTS - index - 1
        for component in range(remaining_total + 1):
            block = comb(remaining_total - component + tail - 1, tail - 1)
            if remaining_rank >= block:
                remaining_rank -= block
                continue
            values.append(component)
            remaining_total -= component
            break
    values.append(remaining_total)
    first, second, third, fourth = values
    return first, second, third, fourth


def _key(value: _Vector) -> tuple[int, int]:
    return sum(value), _composition_rank(value)


def _strict_pair_count(population: int) -> int:
    return comb(population, 2)


def _strict_pair_rank(left: int, right: int, population: int) -> int:
    assert 0 <= left < right < population
    return left * (2 * population - left - 1) // 2 + right - left - 1


def _strict_pair_unrank(rank: int, population: int) -> tuple[int, int]:
    remaining = rank
    for left in range(population):
        block = population - left - 1
        if remaining >= block:
            remaining -= block
            continue
        return left, left + remaining + 1
    raise AssertionError


def _d10_mass_pairs(total: int) -> tuple[tuple[int, int], ...]:
    if total % 5 != 0:
        return ()
    quotient = total // 5
    return tuple((left, quotient - left) for left in range(quotient // 2 + 1))


def _d10_block_count(masses: tuple[int, int]) -> int:
    left, right = masses
    left_count = _composition_count(left)
    right_count = _composition_count(right)
    if left < right:
        return left_count * right_count
    return _strict_pair_count(left_count)


def _d10_count(total: int) -> int:
    return sum(_d10_block_count(masses) for masses in _d10_mass_pairs(total))


def _d10_rank(state: _D10State) -> int | None:
    left, right = sorted(state, key=_key)
    if left == right:
        return None
    left_key, right_key = _key(left), _key(right)
    masses = left_key[0], right_key[0]
    total = 5 * sum(masses)
    prefix = sum(
        _d10_block_count(candidate)
        for candidate in _d10_mass_pairs(total)
        if candidate < masses
    )
    if masses[0] < masses[1]:
        local = left_key[1] * _composition_count(masses[1]) + right_key[1]
    else:
        local = _strict_pair_rank(
            left_key[1],
            right_key[1],
            _composition_count(masses[0]),
        )
    return prefix + local


def _d10_unrank(total: int, rank: int) -> _D10State | None:
    if rank < 0 or rank >= _d10_count(total):
        return None
    remaining = rank
    for masses in _d10_mass_pairs(total):
        count = _d10_block_count(masses)
        if remaining >= count:
            remaining -= count
            continue
        if masses[0] < masses[1]:
            left_rank, right_rank = divmod(
                remaining,
                _composition_count(masses[1]),
            )
        else:
            left_rank, right_rank = _strict_pair_unrank(
                remaining,
                _composition_count(masses[0]),
            )
        left = _composition_unrank(masses[0], left_rank)
        right = _composition_unrank(masses[1], right_rank)
        assert left is not None
        assert right is not None
        return left, right
    raise AssertionError


def _s5_count(total: int) -> int:
    return _composition_count(total // 10) if total % 10 == 0 else 0


def _s5_rank(total: int, value: _Vector) -> int | None:
    if 10 * sum(value) != total:
        return None
    return _composition_rank(value)


def _s5_unrank(total: int, rank: int) -> _Vector | None:
    if total % 10 != 0:
        return None
    return _composition_unrank(total // 10, rank)


def _edge_values(state: _D10State) -> tuple[_Vector, ...]:
    cycle, diagonal = state
    return tuple(
        cycle if edge in _CYCLE_EDGES else diagonal
        for edge in range(len(_EDGES))
    )


def _permute(
    edge_values: tuple[_Vector, ...],
    order: tuple[int, ...],
) -> tuple[_Vector, ...]:
    result: list[_Vector] = []
    for left, right in _EDGES:
        source = _ordered_edge(order[left], order[right])
        result.append(edge_values[_EDGE_INDEX[source]])
    return tuple(result)


def _stabilizer_order(edge_values: tuple[_Vector, ...]) -> int:
    return sum(_permute(edge_values, order) == edge_values for order in _S5)


def test_low_mass_exception_counts_match_lattice_spectrum() -> None:
    """D10 and full-S5 ranks match their complete reviewed support."""
    assert tuple(_d10_count(total) for total in range(_MAXIMUM_MASS + 1)) == (
        _EXPECTED_D10
    )
    assert tuple(_s5_count(total) for total in range(_MAXIMUM_MASS + 1)) == (
        _EXPECTED_S5
    )


def test_d10_rank_roundtrips_and_has_exact_stabilizer() -> None:
    """Every D10 local rank is dense and has exact stabilizer order ten."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _d10_count(total)
        assert _d10_unrank(total, -1) is None
        assert _d10_unrank(total, count) is None
        for rank in range(count):
            state = _d10_unrank(total, rank)
            assert state is not None
            assert _d10_rank(state) == rank
            assert _d10_rank((state[1], state[0])) == rank
            assert _stabilizer_order(_edge_values(state)) == _D10_ORDER


def test_full_s5_rank_roundtrips_and_has_exact_stabilizer() -> None:
    """Every full-S5 local rank is one repeated four-component edge value."""
    zero = (0, 0, 0, 0)
    for total in range(_MAXIMUM_MASS + 1):
        count = _s5_count(total)
        assert _s5_unrank(total, -1) is None
        assert _s5_unrank(total, count) is None
        for rank in range(count):
            value = _s5_unrank(total, rank)
            assert value is not None
            assert _s5_rank(total, value) == rank
            assert _stabilizer_order((value,) * len(_EDGES)) == _S5_ORDER
        if count == 0:
            assert _s5_rank(total, zero) is None
