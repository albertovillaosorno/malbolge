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
#   - Dense rank/unrank for pair-valued K6 edge classes with trivial S6
#     stabilizer.
# - Must-Not:
#   - Claim coverage of trivial-S6 classes whose pair graph remains symmetric.
# - Allows:
#   - Inputs: fifteen two-component K6 edge values through mass fourteen.
#   - Outputs: dense free ranks using subgroup-Mobius suffix counts.
#   - Side effects: none.
# - Split-When:
#   - Symmetric pair-graph stabilizers need separate triple-breaking ranks.
# - Merge-When:
#   - Complete trivial-S6 ranking owns all pair-graph stabilizer branches.
# - Summary:
#   - Canonical edge-color blocks use Mobius-counted free suffixes.
# - Description:
#   - S6 subgroup Mobius inversion replaces memory-heavy mask-image recursion.
# - Usage:
#   - Constructively covers the pair-trivial majority of the free S6 stratum.
# - Defaults:
#   - Exhaustive ranks reach pair mass six; sampled ranks reach fourteen.
#

"""Dense trivial-S6 rank for pair-valued K6 edge graphs."""

from __future__ import annotations

from functools import cache
from itertools import combinations
from math import comb

from tests.mathematics.s6_subgroup_lattice import PERMUTATIONS
from tests.mathematics.s6_subgroup_lattice import Subgroup
from tests.mathematics.s6_subgroup_lattice import all_subgroups

_ARITY = 6
_GROUP_ORDER = 720
_EDGE_COUNT = 15
_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 5
_SAMPLE_DIVISOR = 4
_FULL_EDGE_MASK = (1 << _EDGE_COUNT) - 1
_EXPECTED_COUNTS = (
    0,
    0,
    0,
    0,
    10,
    156,
    1_315,
    8_260,
    42_975,
    195_100,
    796_976,
    2_987_812,
    10_420_165,
    34_143_362,
    105_908_244,
)
_WIDTH_FOURTEEN_COUNT = _EXPECTED_COUNTS[-1]
_EXPECTED_RESIDUAL_COUNTS = (
    0,
    0,
    0,
    0,
    10,
    376,
    7_277,
    96_898,
    999_634,
    8_523_090,
    62_536_621,
    405_870_644,
    2_376_530_747,
    12_741_994_672,
    63_276_927_716,
)
_EXPECTED_COMPLETE_COUNTS = (
    0,
    0,
    0,
    0,
    10,
    376,
    7_277,
    96_898,
    999_634,
    8_523_090,
    62_536_641,
    405_871_396,
    2_376_545_301,
    12_742_188_468,
    63_278_926_984,
)
_FIXED_COMPONENTS = 2
_TRIPLE_COMPONENTS = 20


type _EdgeValue = tuple[int, int]
type _EdgeValues = tuple[_EdgeValue, ...]
type _Weights = tuple[int, ...]
type _Pattern = tuple[int, ...]
type _Masses = tuple[int, ...]
type _PatternContext = tuple[int, Subgroup]
type _PatternChoice = tuple[int, Subgroup, int]
type _OrbitSizes = tuple[int, ...]
type _Vector = tuple[int, ...]
type _Fixed = tuple[int, int]
type _ResidualState = tuple[_Fixed, _EdgeValues, _Vector]
type _CompleteState = tuple[_EdgeValue, _Fixed, _EdgeValues, _Vector]
type _ResidualRankData = tuple[tuple[int, int, int], tuple[int, int, int]]

_EDGES = tuple(
    (left, right) for left in range(_ARITY) for right in range(left + 1, _ARITY)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}


def _ordered_edge(left: int, right: int) -> tuple[int, int]:
    return (left, right) if left < right else (right, left)


_EDGE_PERMUTATIONS = tuple(
    tuple(
        _EDGE_INDEX[_ordered_edge(order[left], order[right])]
        for left, right in _EDGES
    )
    for order in PERMUTATIONS
)
_SUBGROUPS = all_subgroups()
_IDENTITY_GROUP = next(group for group in _SUBGROUPS if len(group) == 1)
_S6 = next(group for group in _SUBGROUPS if len(group) == _GROUP_ORDER)


@cache
def _mobius(subgroup: Subgroup) -> int:
    if subgroup == _IDENTITY_GROUP:
        return 1
    return -sum(
        _mobius(smaller)
        for smaller in _SUBGROUPS
        if len(smaller) < len(subgroup) and smaller < subgroup
    )


_MOBIUS = {subgroup: _mobius(subgroup) for subgroup in _SUBGROUPS}
_MOBIUS_SUBGROUPS = tuple(
    subgroup for subgroup in _SUBGROUPS if _MOBIUS[subgroup] != 0
)


@cache
def _subgroups_under(group: Subgroup) -> tuple[Subgroup, ...]:
    return tuple(
        subgroup for subgroup in _MOBIUS_SUBGROUPS if subgroup <= group
    )


def _map_mask(element: int, mask: int) -> int:
    result = 0
    mapping = _EDGE_PERMUTATIONS[element]
    remaining = mask
    while remaining:
        bit = remaining & -remaining
        edge = bit.bit_length() - 1
        result |= 1 << mapping[edge]
        remaining -= bit
    return result


@cache
def _orbit_sizes(subgroup: Subgroup, mask: int) -> _OrbitSizes:
    domain = {edge for edge in range(_EDGE_COUNT) if mask & (1 << edge)}
    unseen = set(domain)
    result: list[int] = []
    while unseen:
        seed = min(unseen)
        orbit = {_EDGE_PERMUTATIONS[element][seed] for element in subgroup}
        assert orbit <= domain
        unseen -= orbit
        result.append(len(orbit))
    return tuple(sorted(result))


def _fixed_step(
    states: dict[_Weights, int],
    orbit_size: int,
    weights: _Weights,
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
def _fixed_pattern_count(
    orbit_sizes: _OrbitSizes,
    weights: _Weights,
) -> int:
    if sum(orbit_sizes) != sum(weights):
        return 0
    states = {(0,) * len(weights): 1}
    for orbit_size in orbit_sizes:
        states = _fixed_step(states, orbit_size, weights)
    return states.get(weights, 0)


@cache
def _pattern_suffix_count(
    weights: _Weights,
    remaining: int,
    group: Subgroup,
) -> int:
    if sum(weights) != remaining.bit_count():
        return 0
    numerator = sum(
        _MOBIUS[subgroup]
        * _fixed_pattern_count(_orbit_sizes(subgroup, remaining), weights)
        for subgroup in _subgroups_under(group)
    )
    assert numerator % len(group) == 0
    return numerator // len(group)


def _positive_compositions(total: int) -> tuple[_Weights, ...]:
    if total == 0:
        return ((),)
    return tuple(
        (first, *suffix)
        for first in range(1, total + 1)
        for suffix in _positive_compositions(total - first)
    )


_WEIGHT_COMPOSITIONS = _positive_compositions(_EDGE_COUNT)


@cache
def _subset_masks(mask: int, size: int) -> tuple[int, ...]:
    bits = tuple(edge for edge in range(_EDGE_COUNT) if mask & (1 << edge))
    return tuple(
        sum(1 << edge for edge in choice) for choice in combinations(bits, size)
    )


@cache
def _canonical_blocks(
    remaining: int,
    size: int,
    group: Subgroup,
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
    weights: _Weights,
    context: _PatternContext,
) -> tuple[_PatternChoice, ...]:
    remaining, group = context
    if not weights:
        return ()
    return tuple(
        (
            block,
            stabilizer,
            _pattern_suffix_count(
                weights[1:],
                remaining ^ block,
                stabilizer,
            ),
        )
        for block in _canonical_blocks(remaining, weights[0], group)
        for stabilizer in (_block_stabilizer(block, group),)
    )


def _pattern_rank_choice(
    weights: _Weights,
    target: int,
    context: _PatternContext,
) -> tuple[int, int, Subgroup] | None:
    choices = _pattern_choices(weights, context)
    prefix = sum(count for block, _, count in choices if block < target)
    selected = next(
        ((block, group) for block, group, _ in choices if block == target),
        None,
    )
    return None if selected is None else (prefix, selected[0], selected[1])


def _pattern_rank_from(
    weights: _Weights,
    pattern: _Pattern,
    context: _PatternContext,
) -> int | None:
    remaining, group = context
    result: int | None = None
    if not weights:
        result = (
            0 if not pattern and remaining == 0 and len(group) == 1 else None
        )
    elif pattern and pattern[0].bit_count() == weights[0]:
        selected = _pattern_rank_choice(weights, pattern[0], context)
        if selected is not None:
            prefix, block, stabilizer = selected
            suffix = _pattern_rank_from(
                weights[1:],
                pattern[1:],
                (remaining ^ block, stabilizer),
            )
            result = None if suffix is None else prefix + suffix
    return result


def _pattern_rank(weights: _Weights, pattern: _Pattern) -> int | None:
    return _pattern_rank_from(weights, pattern, (_FULL_EDGE_MASK, _S6))


def _pattern_unrank_from(
    weights: _Weights,
    rank: int,
    context: _PatternContext,
) -> _Pattern | None:
    remaining, group = context
    if not weights:
        return () if rank == 0 and remaining == 0 and len(group) == 1 else None
    for block, stabilizer, count in _pattern_choices(weights, context):
        if rank >= count:
            rank -= count
            continue
        suffix = _pattern_unrank_from(
            weights[1:],
            rank,
            (remaining ^ block, stabilizer),
        )
        return None if suffix is None else (block, *suffix)
    return None


def _pattern_unrank(weights: _Weights, rank: int) -> _Pattern | None:
    count = _pattern_suffix_count(weights, _FULL_EDGE_MASK, _S6)
    if rank < 0 or rank >= count:
        return None
    return _pattern_unrank_from(weights, rank, (_FULL_EDGE_MASK, _S6))


def _composition_count(total: int) -> int:
    return total + 1


def _composition_rank(value: _EdgeValue) -> int:
    first, _ = value
    return first


def _composition_unrank(total: int, rank: int) -> _EdgeValue | None:
    if rank < 0 or rank >= _composition_count(total):
        return None
    return rank, total - rank


def _value_key(value: _EdgeValue) -> tuple[int, int]:
    return sum(value), _composition_rank(value)


def _mass_sequences_from(
    weights: _Weights,
    total: int,
    minimum: int,
) -> tuple[_Masses, ...]:
    if not weights:
        return ((),) if total == 0 else ()
    weight = weights[0]
    return tuple(
        (mass, *suffix)
        for mass in range(minimum, total // weight + 1)
        for suffix in _mass_sequences_from(
            weights[1:],
            total - weight * mass,
            mass,
        )
    )


def _mass_sequences(weights: _Weights, total: int) -> tuple[_Masses, ...]:
    return _mass_sequences_from(weights, total, 0)


def _mass_runs(masses: _Masses) -> tuple[tuple[int, int], ...]:
    result: list[tuple[int, int]] = []
    start = 0
    while start < len(masses):
        end = start + 1
        while end < len(masses) and masses[end] == masses[start]:
            end += 1
        result.append((start, end))
        start = end
    return tuple(result)


def _color_block_count(masses: _Masses) -> int:
    result = 1
    for start, end in _mass_runs(masses):
        result *= comb(_composition_count(masses[start]), end - start)
    return result


@cache
def _color_count(weights: _Weights, total: int) -> int:
    return sum(
        _color_block_count(masses) for masses in _mass_sequences(weights, total)
    )


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


def _strict_unrank(
    population: int,
    size: int,
    rank: int,
) -> tuple[int, ...]:
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


def _color_local_rank(masses: _Masses, ranks: tuple[int, ...]) -> int:
    result = 0
    for start, end in _mass_runs(masses):
        population = _composition_count(masses[start])
        count = comb(population, end - start)
        result *= count
        result += _strict_rank(ranks[start:end], population)
    return result


def _color_rank(
    weights: _Weights,
    values: tuple[_EdgeValue, ...],
) -> int | None:
    if len(weights) != len(values):
        return None
    keys = tuple(_value_key(value) for value in values)
    if tuple(sorted(keys)) != keys or len(set(keys)) != len(keys):
        return None
    masses = tuple(key[0] for key in keys)
    total = sum(
        weight * mass for weight, mass in zip(weights, masses, strict=True)
    )
    prefix = sum(
        _color_block_count(candidate)
        for candidate in _mass_sequences(weights, total)
        if candidate < masses
    )
    ranks = tuple(key[1] for key in keys)
    return prefix + _color_local_rank(masses, ranks)


def _color_run_ranks(masses: _Masses, rank: int) -> tuple[int, ...]:
    runs = _mass_runs(masses)
    counts = tuple(
        comb(_composition_count(masses[start]), end - start)
        for start, end in runs
    )
    result: list[int] = []
    remaining = rank
    for count in reversed(counts):
        remaining, local = divmod(remaining, count)
        result.append(local)
    assert remaining == 0
    return tuple(reversed(result))


def _color_local_unrank(masses: _Masses, rank: int) -> tuple[_EdgeValue, ...]:
    values: list[_EdgeValue] = []
    for (start, end), local in zip(
        _mass_runs(masses),
        _color_run_ranks(masses, rank),
        strict=True,
    ):
        mass = masses[start]
        raw_ranks = _strict_unrank(
            _composition_count(mass),
            end - start,
            local,
        )
        for raw_rank in raw_ranks:
            value = _composition_unrank(mass, raw_rank)
            assert value is not None
            values.append(value)
    return tuple(values)


def _color_unrank(
    weights: _Weights,
    total: int,
    rank: int,
) -> tuple[_EdgeValue, ...] | None:
    if rank < 0 or rank >= _color_count(weights, total):
        return None
    remaining = rank
    for masses in _mass_sequences(weights, total):
        count = _color_block_count(masses)
        if remaining >= count:
            remaining -= count
            continue
        return _color_local_unrank(masses, remaining)
    raise AssertionError


def _canonical_pattern(pattern: _Pattern) -> _Pattern:
    return min(
        tuple(_map_mask(element, block) for block in pattern) for element in _S6
    )


def _state_pattern(
    edge_values: _EdgeValues,
) -> tuple[_Weights, _Pattern, tuple[_EdgeValue, ...]] | None:
    if any(value < 0 for edge in edge_values for value in edge):
        return None
    colors = tuple(sorted(set(edge_values), key=_value_key))
    color_index = {value: index for index, value in enumerate(colors)}
    blocks = tuple(
        sum(
            1 << edge
            for edge, value in enumerate(edge_values)
            if color_index[value] == index
        )
        for index in range(len(colors))
    )
    weights = tuple(block.bit_count() for block in blocks)
    return weights, _canonical_pattern(blocks), colors


@cache
def _feasible_weights(total: int) -> tuple[_Weights, ...]:
    return tuple(
        weights
        for weights in _WEIGHT_COMPOSITIONS
        if _color_count(weights, total) != 0
    )


@cache
def _class_count(total: int) -> int:
    return sum(
        _pattern_suffix_count(weights, _FULL_EDGE_MASK, _S6)
        * _color_count(weights, total)
        for weights in _feasible_weights(total)
    )


def _weight_prefix(weights: _Weights, total: int) -> int:
    result = 0
    for candidate in _feasible_weights(total):
        if candidate == weights:
            return result
        result += _pattern_suffix_count(
            candidate, _FULL_EDGE_MASK, _S6
        ) * _color_count(candidate, total)
    raise AssertionError


def _rank(edge_values: _EdgeValues) -> int | None:
    data = (
        _state_pattern(edge_values) if len(edge_values) == _EDGE_COUNT else None
    )
    if data is None:
        return None
    weights, pattern, colors = data
    pattern_rank = _pattern_rank(weights, pattern)
    color_rank = _color_rank(weights, colors)
    result: int | None = None
    if pattern_rank is not None and color_rank is not None:
        total = sum(sum(value) for value in edge_values)
        color_count = _color_count(weights, total)
        result = (
            _weight_prefix(weights, total)
            + pattern_rank * color_count
            + color_rank
        )
    return result


def _state_from_pattern(
    pattern: _Pattern,
    colors: tuple[_EdgeValue, ...],
) -> _EdgeValues:
    result: list[_EdgeValue | None] = [None] * _EDGE_COUNT
    for block, color in zip(pattern, colors, strict=True):
        for edge in range(_EDGE_COUNT):
            if block & (1 << edge):
                result[edge] = color
    assert all(value is not None for value in result)
    return tuple(value for value in result if value is not None)


def _unrank(total: int, rank: int) -> _EdgeValues | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for weights in _feasible_weights(total):
        color_count = _color_count(weights, total)
        block = (
            _pattern_suffix_count(weights, _FULL_EDGE_MASK, _S6) * color_count
        )
        if remaining >= block:
            remaining -= block
            continue
        pattern_rank, color_rank = divmod(remaining, color_count)
        pattern = _pattern_unrank(weights, pattern_rank)
        colors = _color_unrank(weights, total, color_rank)
        assert pattern is not None
        assert colors is not None
        return _state_from_pattern(pattern, colors)
    raise AssertionError


def _permute(edge_values: _EdgeValues, element: int) -> _EdgeValues:
    mapping = _EDGE_PERMUTATIONS[element]
    return tuple(edge_values[mapping[edge]] for edge in range(_EDGE_COUNT))


def _stabilizer_order(edge_values: _EdgeValues) -> int:
    return sum(
        _permute(edge_values, element) == edge_values
        for element in range(_GROUP_ORDER)
    )


def _weak_count(total: int, parts: int) -> int:
    if total < 0:
        return 0
    return comb(total + parts - 1, parts - 1)


def _weak_rank(vector: _Vector) -> int:
    remaining = sum(vector)
    result = 0
    for index, value in enumerate(vector[:-1]):
        tail = len(vector) - index - 1
        result += sum(
            _weak_count(remaining - earlier, tail) for earlier in range(value)
        )
        remaining -= value
    return result


def _weak_unrank(total: int, parts: int, rank: int) -> _Vector | None:
    if rank < 0 or rank >= _weak_count(total, parts):
        return None
    remaining_total = total
    remaining_rank = rank
    result: list[int] = []
    for index in range(parts - 1):
        tail = parts - index - 1
        for value in range(remaining_total + 1):
            block = _weak_count(remaining_total - value, tail)
            if remaining_rank >= block:
                remaining_rank -= block
                continue
            result.append(value)
            remaining_total -= value
            break
    result.append(remaining_total)
    return tuple(result)


def _as_fixed(vector: _Vector) -> _Fixed:
    assert len(vector) == _FIXED_COMPONENTS
    return vector[0], vector[1]


def _residual_block_count(total: int, fixed_mass: int, pair_mass: int) -> int:
    triple_mass = total - fixed_mass - pair_mass
    return (
        _weak_count(fixed_mass, _FIXED_COMPONENTS)
        * _class_count(pair_mass)
        * _weak_count(triple_mass, _TRIPLE_COMPONENTS)
    )


@cache
def _residual_count(total: int) -> int:
    return sum(
        _residual_block_count(total, fixed_mass, pair_mass)
        for fixed_mass in range(total + 1)
        for pair_mass in range(total - fixed_mass + 1)
    )


def _residual_rank_data(
    total: int,
    state: _ResidualState,
) -> _ResidualRankData | None:
    fixed, pairs, triples = state
    if len(triples) != _TRIPLE_COMPONENTS or any(
        value < 0 for value in triples
    ):
        return None
    pair_rank = _rank(pairs)
    masses = (
        sum(fixed),
        sum(sum(value) for value in pairs),
        sum(triples),
    )
    if pair_rank is None or sum(masses) != total:
        return None
    ranks = _weak_rank(fixed), pair_rank, _weak_rank(triples)
    return masses, ranks


def _residual_prefix(total: int, masses: tuple[int, int, int]) -> int:
    fixed_mass, pair_mass, _ = masses
    return sum(
        _residual_block_count(total, earlier_fixed, earlier_pair)
        for earlier_fixed in range(total + 1)
        for earlier_pair in range(total - earlier_fixed + 1)
        if (earlier_fixed, earlier_pair) < (fixed_mass, pair_mass)
    )


def _residual_local_rank(
    masses: tuple[int, int, int],
    ranks: tuple[int, int, int],
) -> int:
    _, pair_mass, triple_mass = masses
    fixed_rank, pair_rank, triple_rank = ranks
    pair_count = _class_count(pair_mass)
    triple_count = _weak_count(triple_mass, _TRIPLE_COMPONENTS)
    return (fixed_rank * pair_count + pair_rank) * triple_count + triple_rank


def _residual_rank(total: int, state: _ResidualState) -> int | None:
    data = _residual_rank_data(total, state)
    if data is None:
        return None
    masses, ranks = data
    return _residual_prefix(total, masses) + _residual_local_rank(masses, ranks)


def _residual_component_ranks(
    pair_count: int,
    triple_count: int,
    rank: int,
) -> tuple[int, int, int]:
    head, triple_rank = divmod(rank, triple_count)
    fixed_rank, pair_rank = divmod(head, pair_count)
    return fixed_rank, pair_rank, triple_rank


def _residual_unrank_block(
    total: int,
    masses: tuple[int, int],
    rank: int,
) -> _ResidualState:
    fixed_mass, pair_mass = masses
    triple_mass = total - fixed_mass - pair_mass
    fixed_rank, pair_rank, triple_rank = _residual_component_ranks(
        _class_count(pair_mass),
        _weak_count(triple_mass, _TRIPLE_COMPONENTS),
        rank,
    )
    fixed = _weak_unrank(fixed_mass, _FIXED_COMPONENTS, fixed_rank)
    pairs = _unrank(pair_mass, pair_rank)
    triples = _weak_unrank(triple_mass, _TRIPLE_COMPONENTS, triple_rank)
    assert fixed is not None
    assert pairs is not None
    assert triples is not None
    return _as_fixed(fixed), pairs, triples


def _residual_unrank(total: int, rank: int) -> _ResidualState | None:
    if rank < 0 or rank >= _residual_count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        for pair_mass in range(total - fixed_mass + 1):
            block = _residual_block_count(total, fixed_mass, pair_mass)
            if remaining >= block:
                remaining -= block
                continue
            return _residual_unrank_block(
                total,
                (fixed_mass, pair_mass),
                remaining,
            )
    raise AssertionError


@cache
def _complete_count(total: int) -> int:
    return sum(
        _weak_count(vertex_mass, 2) * _residual_count(total - 6 * vertex_mass)
        for vertex_mass in range(total // 6 + 1)
    )


def _complete_rank(total: int, state: _CompleteState) -> int | None:
    vertex, fixed, pairs, triples = state
    result: int | None = None
    if all(value >= 0 for value in vertex):
        vertex_mass = sum(vertex)
        residual_mass = total - 6 * vertex_mass
        if residual_mass >= 0:
            residual_rank = _residual_rank(
                residual_mass,
                (fixed, pairs, triples),
            )
            if residual_rank is not None:
                prefix = sum(
                    _weak_count(earlier, 2)
                    * _residual_count(total - 6 * earlier)
                    for earlier in range(vertex_mass)
                )
                result = (
                    prefix
                    + _weak_rank(vertex) * _residual_count(residual_mass)
                    + residual_rank
                )
    return result


def _complete_unrank_block(
    total: int,
    vertex_mass: int,
    rank: int,
) -> _CompleteState:
    residual_mass = total - 6 * vertex_mass
    residual_count = _residual_count(residual_mass)
    vertex_rank, residual_rank = divmod(rank, residual_count)
    vertex = _weak_unrank(vertex_mass, 2, vertex_rank)
    residual = _residual_unrank(residual_mass, residual_rank)
    assert vertex is not None
    assert residual is not None
    fixed, pairs, triples = residual
    return (vertex[0], vertex[1]), fixed, pairs, triples


def _complete_unrank(total: int, rank: int) -> _CompleteState | None:
    if rank < 0 or rank >= _complete_count(total):
        return None
    remaining = rank
    for vertex_mass in range(total // 6 + 1):
        residual_mass = total - 6 * vertex_mass
        block = _weak_count(vertex_mass, 2) * _residual_count(residual_mass)
        if remaining >= block:
            remaining -= block
            continue
        return _complete_unrank_block(total, vertex_mass, remaining)
    raise AssertionError


def _sample_ranks(count: int) -> tuple[int, ...]:
    if count == 0:
        return ()
    return tuple(
        sorted({
            0,
            count // _SAMPLE_DIVISOR,
            count // 2,
            (3 * count) // _SAMPLE_DIVISOR,
            count - 1,
        })
    )


def test_k6_pair_trivial_counts_match_independent_lattice_sequence() -> None:
    """Pattern/color ranks reproduce the independent pair-lattice counts."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT


def test_k6_pair_trivial_rank_exhausts_masses_four_through_six() -> None:
    """Every free K6 pair rank through mass six roundtrips densely."""
    for total in range(4, _EXHAUSTIVE_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(state) == rank
            assert _stabilizer_order(state) == 1


def test_k6_pair_trivial_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior K6 pair ranks invert through mass fourteen."""
    for total, count in enumerate(_EXPECTED_COUNTS):
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in _sample_ranks(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(state) == rank
            assert _stabilizer_order(state) == 1


def test_pair_trivial_residual_and_complete_counts_match_factorization() -> (
    None
):
    """Pair-free ranks compose with fixed, triple, and vertex values."""
    residual = tuple(_residual_count(total) for total in range(15))
    complete = tuple(_complete_count(total) for total in range(15))
    assert residual == _EXPECTED_RESIDUAL_COUNTS
    assert complete == _EXPECTED_COMPLETE_COUNTS


def test_pair_trivial_composed_ranks_roundtrip_through_fourteen() -> None:
    """Composed pair-free intervals invert through mass fourteen."""
    for total in range(15):
        for target in _sample_ranks(_residual_count(total)):
            state = _residual_unrank(total, target)
            assert state is not None
            assert _residual_rank(total, state) == target
        for target in _sample_ranks(_complete_count(total)):
            state = _complete_unrank(total, target)
            assert state is not None
            assert _complete_rank(total, state) == target
