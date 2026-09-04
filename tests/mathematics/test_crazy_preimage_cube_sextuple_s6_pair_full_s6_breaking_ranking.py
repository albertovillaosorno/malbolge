# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
# RESEARCH-ONLY PROOF BOUNDARY
# Scope:
#   - Pair graph fixed by the full S6 action in the all-equal vertex stratum.
#   - Twenty weight-three triples whose exact final S6 stabilizer is trivial.
# Non-goals:
#   - Rank other pair-graph stabilizer branches here.
# Method:
#   - Rank equality patterns of the twenty triples by an S6 stabilizer chain.
#   - Mobius-invert subgroup-fixed pattern suffixes to require final identity.
#   - Rank strictly increasing scalar colors for each equality multiplicity.
#   - Compose with two fixed residual scalars and the repeated-six vertex pair.
"""Dense rank for the full-S6 pair branch broken by triple values."""

from __future__ import annotations

from functools import cache
from itertools import combinations

from tests.mathematics.s6_subgroup_lattice import PERMUTATIONS
from tests.mathematics.s6_subgroup_lattice import Subgroup
from tests.mathematics.s6_subgroup_lattice import all_subgroups

_ARITY = 6
_GROUP_ORDER = 720
_COORDINATE_COUNT = 20
_MAXIMUM_MASS = 14
_MAXIMUM_COLORS = 5
_SAMPLE_DIVISOR = 4
_FULL_MASK = (1 << _COORDINATE_COUNT) - 1
_FIXED_COMPONENTS = 2
_EXPECTED_TRIPLE_FREE_COUNTS = (
    0,
    0,
    0,
    0,
    2,
    26,
    149,
    661,
    2_481,
    8_264,
    25_031,
    70_307,
    185_297,
    462_691,
    1_101_650,
)
_EXPECTED_RESIDUAL_COUNTS = (
    0,
    0,
    0,
    0,
    2,
    30,
    207,
    1_045,
    4_364,
    15_947,
    52_561,
    159_482,
    451_700,
    1_206_609,
    3_063_168,
)
_EXPECTED_COMPLETE_COUNTS = (
    0,
    0,
    0,
    0,
    2,
    30,
    207,
    1_045,
    4_364,
    15_947,
    52_565,
    159_542,
    452_114,
    1_208_699,
    3_071_896,
)

type _Weights = tuple[int, ...]
type _Pattern = tuple[int, ...]
type _PatternContext = tuple[int, Subgroup]
type _PatternChoice = tuple[int, Subgroup, int]
type _OrbitSizes = tuple[int, ...]
type _Vector = tuple[int, ...]
type _Pair = tuple[int, int]
type _ResidualState = tuple[_Pair, _Vector]
type _CompleteState = tuple[_Pair, _Pair, _Vector]

_TRIPLES = tuple(combinations(range(_ARITY), 3))
_TRIPLE_INDEX = {triple: index for index, triple in enumerate(_TRIPLES)}


def _ordered_triple(
    first: int, second: int, third: int
) -> tuple[int, int, int]:
    ordered = sorted((first, second, third))
    return ordered[0], ordered[1], ordered[2]


_TRIPLE_PERMUTATIONS = tuple(
    tuple(
        _TRIPLE_INDEX[_ordered_triple(*(order[vertex] for vertex in triple))]
        for triple in _TRIPLES
    )
    for order in PERMUTATIONS
)
_SUBGROUPS = all_subgroups()
_S6 = next(group for group in _SUBGROUPS if len(group) == _GROUP_ORDER)
_IDENTITY_GROUP = next(group for group in _SUBGROUPS if len(group) == 1)


@cache
def _subgroup_mobius(group: Subgroup) -> int:
    if group == _IDENTITY_GROUP:
        return 1
    return -sum(
        _subgroup_mobius(smaller)
        for smaller in _SUBGROUPS
        if len(smaller) < len(group) and smaller < group
    )


_MOBIUS_COEFFICIENTS = tuple(
    (group, coefficient)
    for group in _SUBGROUPS
    if (coefficient := _subgroup_mobius(group)) != 0
)


def _map_mask(element: int, mask: int) -> int:
    result = 0
    mapping = _TRIPLE_PERMUTATIONS[element]
    remaining = mask
    while remaining:
        bit = remaining & -remaining
        coordinate = bit.bit_length() - 1
        result |= 1 << mapping[coordinate]
        remaining -= bit
    return result


@cache
def _orbit_sizes(subgroup: Subgroup, mask: int) -> _OrbitSizes:
    domain = {
        coordinate
        for coordinate in range(_COORDINATE_COUNT)
        if mask & (1 << coordinate)
    }
    unseen = set(domain)
    result: list[int] = []
    while unseen:
        seed = min(unseen)
        orbit = {_TRIPLE_PERMUTATIONS[element][seed] for element in subgroup}
        assert orbit <= domain
        unseen -= orbit
        result.append(len(orbit))
    return tuple(sorted(result))


def _fixed_step(
    states: dict[_Weights, int], orbit_size: int, weights: _Weights
) -> dict[_Weights, int]:
    result: dict[_Weights, int] = {}
    for state, count in states.items():
        for index, target in enumerate(weights):
            if state[index] + orbit_size > target:
                continue
            updated = (
                *state[:index],
                state[index] + orbit_size,
                *state[index + 1 :],
            )
            result[updated] = result.get(updated, 0) + count
    return result


@cache
def _fixed_pattern_count(orbit_sizes: _OrbitSizes, weights: _Weights) -> int:
    if sum(orbit_sizes) != sum(weights):
        return 0
    states = {(0,) * len(weights): 1}
    for orbit_size in orbit_sizes:
        states = _fixed_step(states, orbit_size, weights)
    return states.get(weights, 0)


@cache
def _pattern_suffix_count(
    weights: _Weights, remaining: int, group: Subgroup
) -> int:
    if sum(weights) != remaining.bit_count():
        return 0
    numerator = sum(
        coefficient
        * _fixed_pattern_count(_orbit_sizes(subgroup, remaining), weights)
        for subgroup, coefficient in _MOBIUS_COEFFICIENTS
        if subgroup <= group
    )
    assert numerator % len(group) == 0
    return numerator // len(group)


@cache
def _subset_masks(mask: int, size: int) -> tuple[int, ...]:
    positions = tuple(
        coordinate
        for coordinate in range(_COORDINATE_COUNT)
        if mask & (1 << coordinate)
    )
    return tuple(
        sum(1 << coordinate for coordinate in choice)
        for choice in combinations(positions, size)
    )


@cache
def _canonical_blocks(
    remaining: int, size: int, group: Subgroup
) -> tuple[int, ...]:
    unseen = set(_subset_masks(remaining, size))
    result: list[int] = []
    while unseen:
        seed = min(unseen)
        orbit = {_map_mask(element, seed) for element in group}
        assert seed == min(orbit)
        result.append(seed)
        unseen -= orbit
    return tuple(result)


def _block_stabilizer(block: int, group: Subgroup) -> Subgroup:
    return frozenset(
        element for element in group if _map_mask(element, block) == block
    )


@cache
def _pattern_choices(
    weights: _Weights, context: _PatternContext
) -> tuple[_PatternChoice, ...]:
    remaining, group = context
    if not weights:
        return ()
    return tuple(
        (
            block,
            stabilizer,
            _pattern_suffix_count(weights[1:], remaining ^ block, stabilizer),
        )
        for block in _canonical_blocks(remaining, weights[0], group)
        for stabilizer in (_block_stabilizer(block, group),)
    )


def _pattern_rank_from(
    weights: _Weights, pattern: _Pattern, context: _PatternContext
) -> int | None:
    remaining, group = context
    result: int | None = None
    if not weights:
        result = (
            0
            if not pattern and remaining == 0 and group == _IDENTITY_GROUP
            else None
        )
    elif pattern and pattern[0].bit_count() == weights[0]:
        target = pattern[0]
        choices = _pattern_choices(weights, context)
        prefix = sum(count for block, _, count in choices if block < target)
        selected = next(
            (
                (block, stabilizer)
                for block, stabilizer, _ in choices
                if block == target
            ),
            None,
        )
        if selected is not None:
            block, stabilizer = selected
            suffix = _pattern_rank_from(
                weights[1:], pattern[1:], (remaining ^ block, stabilizer)
            )
            result = None if suffix is None else prefix + suffix
    return result


def _pattern_rank(weights: _Weights, pattern: _Pattern) -> int | None:
    return _pattern_rank_from(weights, pattern, (_FULL_MASK, _S6))


def _pattern_unrank_from(
    weights: _Weights, rank: int, context: _PatternContext
) -> _Pattern | None:
    remaining, group = context
    if not weights:
        return (
            ()
            if rank == 0 and remaining == 0 and group == _IDENTITY_GROUP
            else None
        )
    for block, stabilizer, count in _pattern_choices(weights, context):
        if rank >= count:
            rank -= count
            continue
        suffix = _pattern_unrank_from(
            weights[1:], rank, (remaining ^ block, stabilizer)
        )
        return None if suffix is None else (block, *suffix)
    return None


def _pattern_unrank(weights: _Weights, rank: int) -> _Pattern | None:
    count = _pattern_suffix_count(weights, _FULL_MASK, _S6)
    if rank < 0 or rank >= count:
        return None
    return _pattern_unrank_from(weights, rank, (_FULL_MASK, _S6))


@cache
def _positive_compositions(
    total: int, maximum_parts: int
) -> tuple[_Weights, ...]:
    if total == 0:
        return ((),)
    if maximum_parts == 0:
        return ()
    return tuple(
        (first, *suffix)
        for first in range(1, total + 1)
        for suffix in _positive_compositions(total - first, maximum_parts - 1)
    )


_WEIGHT_COMPOSITIONS = _positive_compositions(
    _COORDINATE_COUNT, _MAXIMUM_COLORS
)


@cache
def _scalar_colors(weights: _Weights, total: int) -> tuple[_Vector, ...]:
    result: list[_Vector] = []

    def visit(
        index: int, previous: int, *, remaining: int, values: _Vector
    ) -> None:
        if index == len(weights):
            if remaining == 0:
                result.append(values)
            return
        weight = weights[index]
        for value in range(previous + 1, remaining // weight + 1):
            visit(
                index + 1,
                value,
                remaining=remaining - weight * value,
                values=(*values, value),
            )

    visit(0, -1, remaining=total, values=())
    return tuple(result)


@cache
def _feasible_weights(total: int) -> tuple[_Weights, ...]:
    return tuple(
        weights
        for weights in _WEIGHT_COMPOSITIONS
        if _scalar_colors(weights, total)
    )


def _canonical_pattern(pattern: _Pattern) -> _Pattern:
    return min(
        tuple(_map_mask(element, block) for block in pattern) for element in _S6
    )


def _state_pattern(
    vector: _Vector,
) -> tuple[_Weights, _Pattern, _Vector] | None:
    if len(vector) != _COORDINATE_COUNT or any(value < 0 for value in vector):
        return None
    colors = tuple(sorted(set(vector)))
    blocks = tuple(
        sum(
            1 << coordinate
            for coordinate, value in enumerate(vector)
            if value == color
        )
        for color in colors
    )
    return (
        tuple(block.bit_count() for block in blocks),
        _canonical_pattern(blocks),
        colors,
    )


@cache
def _triple_free_count(total: int) -> int:
    return sum(
        _pattern_suffix_count(weights, _FULL_MASK, _S6)
        * len(_scalar_colors(weights, total))
        for weights in _feasible_weights(total)
    )


def _weight_prefix(weights: _Weights, total: int) -> int:
    result = 0
    for candidate in _feasible_weights(total):
        if candidate == weights:
            return result
        result += _pattern_suffix_count(candidate, _FULL_MASK, _S6) * len(
            _scalar_colors(candidate, total)
        )
    raise AssertionError


def _triple_rank(vector: _Vector) -> int | None:
    data = _state_pattern(vector)
    if data is None:
        return None
    weights, pattern, colors = data
    pattern_rank = _pattern_rank(weights, pattern)
    scalar_colors = _scalar_colors(weights, sum(vector))
    if pattern_rank is None or colors not in scalar_colors:
        return None
    color_count = len(scalar_colors)
    return (
        _weight_prefix(weights, sum(vector))
        + pattern_rank * color_count
        + scalar_colors.index(colors)
    )


def _vector_from_pattern(pattern: _Pattern, colors: _Vector) -> _Vector:
    result = [0] * _COORDINATE_COUNT
    for block, color in zip(pattern, colors, strict=True):
        for coordinate in range(_COORDINATE_COUNT):
            if block & (1 << coordinate):
                result[coordinate] = color
    return tuple(result)


def _triple_unrank(total: int, rank: int) -> _Vector | None:
    if rank < 0 or rank >= _triple_free_count(total):
        return None
    remaining = rank
    for weights in _feasible_weights(total):
        colors = _scalar_colors(weights, total)
        block = _pattern_suffix_count(weights, _FULL_MASK, _S6) * len(colors)
        if remaining >= block:
            remaining -= block
            continue
        pattern_rank, color_rank = divmod(remaining, len(colors))
        pattern = _pattern_unrank(weights, pattern_rank)
        assert pattern is not None
        return _vector_from_pattern(pattern, colors[color_rank])
    raise AssertionError


def _stabilizer_order(vector: _Vector) -> int:
    return sum(
        tuple(
            vector[_TRIPLE_PERMUTATIONS[element][coordinate]]
            for coordinate in range(_COORDINATE_COUNT)
        )
        == vector
        for element in range(_GROUP_ORDER)
    )


def _weak_pair_unrank(total: int, rank: int) -> _Pair | None:
    if rank < 0 or rank > total:
        return None
    return rank, total - rank


@cache
def _residual_count(total: int) -> int:
    return sum(
        (fixed_mass + 1) * _triple_free_count(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def _residual_rank(total: int, state: _ResidualState) -> int | None:
    fixed, triples = state
    fixed_mass = sum(fixed)
    triple_mass = total - fixed_mass
    result: int | None = None
    valid = (
        not any(value < 0 for value in fixed)
        and triple_mass >= 0
        and sum(triples) == triple_mass
    )
    if valid:
        triple_rank = _triple_rank(triples)
        if triple_rank is not None:
            prefix = sum(
                (mass + 1) * _triple_free_count(total - mass)
                for mass in range(fixed_mass)
            )
            result = (
                prefix
                + fixed[0] * _triple_free_count(triple_mass)
                + triple_rank
            )
    return result


def _residual_unrank(total: int, rank: int) -> _ResidualState | None:
    if rank < 0 or rank >= _residual_count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        triple_mass = total - fixed_mass
        block = (fixed_mass + 1) * _triple_free_count(triple_mass)
        if remaining >= block:
            remaining -= block
            continue
        fixed_rank, triple_rank = divmod(
            remaining, _triple_free_count(triple_mass)
        )
        fixed = _weak_pair_unrank(fixed_mass, fixed_rank)
        triples = _triple_unrank(triple_mass, triple_rank)
        assert fixed is not None
        assert triples is not None
        return fixed, triples
    raise AssertionError


@cache
def _complete_count(total: int) -> int:
    return sum(
        (vertex_mass + 1) * _residual_count(total - 6 * vertex_mass)
        for vertex_mass in range(total // 6 + 1)
    )


def _complete_rank(total: int, state: _CompleteState) -> int | None:
    vertex, fixed, triples = state
    vertex_mass = sum(vertex)
    residual_mass = total - 6 * vertex_mass
    result: int | None = None
    if not any(value < 0 for value in vertex) and residual_mass >= 0:
        residual_rank = _residual_rank(residual_mass, (fixed, triples))
        if residual_rank is not None:
            prefix = sum(
                (mass + 1) * _residual_count(total - 6 * mass)
                for mass in range(vertex_mass)
            )
            result = (
                prefix
                + vertex[0] * _residual_count(residual_mass)
                + residual_rank
            )
    return result


def _complete_unrank(total: int, rank: int) -> _CompleteState | None:
    if rank < 0 or rank >= _complete_count(total):
        return None
    remaining = rank
    for vertex_mass in range(total // 6 + 1):
        residual_mass = total - 6 * vertex_mass
        block = (vertex_mass + 1) * _residual_count(residual_mass)
        if remaining >= block:
            remaining -= block
            continue
        vertex_rank, residual_rank = divmod(
            remaining, _residual_count(residual_mass)
        )
        vertex = _weak_pair_unrank(vertex_mass, vertex_rank)
        residual = _residual_unrank(residual_mass, residual_rank)
        assert vertex is not None
        assert residual is not None
        fixed, triples = residual
        return vertex, fixed, triples
    raise AssertionError


def _sample_ranks(count: int) -> tuple[int, ...]:
    if count == 0:
        return ()
    return tuple(
        sorted({
            0,
            count // _SAMPLE_DIVISOR,
            count // 2,
            3 * count // _SAMPLE_DIVISOR,
            count - 1,
        })
    )


def test_full_s6_pair_triple_counts_match_independent_sequence() -> None:
    """Pattern Mobius counts reproduce the reviewed free-triple sequence."""
    observed = tuple(
        _triple_free_count(total) for total in range(_MAXIMUM_MASS + 1)
    )
    assert observed == _EXPECTED_TRIPLE_FREE_COUNTS
    assert len(_S6) == _GROUP_ORDER
    assert _orbit_sizes(_S6, _FULL_MASK) == (_COORDINATE_COUNT,)


def test_full_s6_pair_triple_rank_exhausts_small_masses() -> None:
    """Free triple ranks through mass six have trivial S6 stabilizer."""
    for total in range(4, 7):
        for rank in range(_triple_free_count(total)):
            vector = _triple_unrank(total, rank)
            assert vector is not None
            assert _triple_rank(vector) == rank
            assert _stabilizer_order(vector) == 1


def test_full_s6_pair_triple_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior free-triple ranks invert at mass fourteen."""
    total = _MAXIMUM_MASS
    for rank in _sample_ranks(_triple_free_count(total)):
        vector = _triple_unrank(total, rank)
        assert vector is not None
        assert _triple_rank(vector) == rank
        assert _stabilizer_order(vector) == 1


def test_full_s6_pair_branch_composes_densely() -> None:
    """Fixed scalars and the vertex prefix preserve dense intervals."""
    residual = tuple(
        _residual_count(total) for total in range(_MAXIMUM_MASS + 1)
    )
    complete = tuple(
        _complete_count(total) for total in range(_MAXIMUM_MASS + 1)
    )
    assert residual == _EXPECTED_RESIDUAL_COUNTS
    assert complete == _EXPECTED_COMPLETE_COUNTS
    total = _MAXIMUM_MASS
    for rank in _sample_ranks(residual[total]):
        state = _residual_unrank(total, rank)
        assert state is not None
        assert _residual_rank(total, state) == rank
    for rank in _sample_ranks(complete[total]):
        state = _complete_unrank(total, rank)
        assert state is not None
        assert _complete_rank(total, state) == rank
