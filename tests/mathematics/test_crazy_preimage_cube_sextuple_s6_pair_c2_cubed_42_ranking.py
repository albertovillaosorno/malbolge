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
#   - Dense rank/unrank for pair-valued K6 edge classes whose exact S6
#     stabilizer is C2-cubed-42 on three paired endpoint orbits.
# - Must-Not:
#   - Claim coverage for pair-graph stabilizers outside this V4 type.
# - Allows:
#   - Inputs: fifteen two-component K6 edge values through mass fourteen.
#   - Outputs: dense exact-C2-cubed-42 pair-graph ranks.
#   - Side effects: none.
# - Split-When:
#   - Another pair-graph stabilizer type needs its own target coefficients.
# - Merge-When:
#   - A generic exact-stabilizer pair-graph rank owns this specialization.
# - Summary:
#   - Canonical blocks target the C2-cubed-42 conjugacy class.
# - Description:
#   - Interval Mobius coefficients isolate exact C2-cubed-42 stabilizers.
# - Usage:
#   - Supplies the next pair-symmetric branch with constructive triple breaking.
# - Defaults:
#   - Exhaustive ranks reach pair mass six; sampled ranks reach fourteen.
#

"""Dense exact-C2-cubed-42 rank for pair-valued K6 edge graphs."""

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
    1,
    2,
    9,
    16,
    37,
    58,
    111,
    164,
    282,
    400,
    642,
)
_WIDTH_FOURTEEN_COUNT = _EXPECTED_COUNTS[-1]
_EXPECTED_TRIPLE_FREE_COUNTS = (
    0,
    0,
    18,
    152,
    982,
    4_968,
    21_252,
    80_168,
    272_832,
    853_720,
    2_483_898,
    6_790_560,
    17_567_834,
    43_292_256,
    102_118_992,
)
_EXPECTED_RESIDUAL_BRANCH_COUNTS = (
    0,
    0,
    0,
    0,
    0,
    0,
    18,
    224,
    1_878,
    12_120,
    65_486,
    308_616,
    1_302_818,
    5_018_544,
    17_877_258,
)
_EXPECTED_COMPLETE_BRANCH_COUNTS = (
    0,
    0,
    0,
    0,
    0,
    0,
    18,
    224,
    1_878,
    12_120,
    65_486,
    308_616,
    1_302_854,
    5_018_992,
    17_881_014,
)
_TRIPLE_COORDINATES = 20
_FIXED_COMPONENTS = 2
_EXPECTED_TRIPLE_BLOCK_SIZES = (4, 4, 4, 4, 4)
_EXPECTED_TARGET_CONJUGATES = 15
_EXPECTED_TARGET_INVOLUTIONS = 7


type _EdgeValue = tuple[int, int]
type _EdgeValues = tuple[_EdgeValue, ...]
type _Weights = tuple[int, ...]
type _Pattern = tuple[int, ...]
type _Masses = tuple[int, ...]
type _PatternContext = tuple[int, Subgroup]
type _PatternChoice = tuple[int, Subgroup, int]
type _OrbitSizes = tuple[int, ...]
type _Vector = tuple[int, ...]
type _FixedPair = tuple[int, int]
type _BranchMasses = tuple[int, int, int]
type _BranchRanks = tuple[int, int, int]
type _BranchRankData = tuple[_BranchMasses, _BranchRanks]
type _TripleBlock = tuple[int, ...]
type _TripleContext = tuple[Subgroup, int, Subgroup]
type _TripleLocalClass = tuple[_Vector, Subgroup]
type _ResidualBranchState = tuple[_FixedPair, _EdgeValues, _Vector]
type _CompleteBranchState = tuple[_EdgeValue, _FixedPair, _EdgeValues, _Vector]

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


def _vertex_orbit_sizes(group: Subgroup) -> tuple[int, ...]:
    unseen = set(range(_ARITY))
    result: list[int] = []
    while unseen:
        seed = min(unseen)
        orbit = {PERMUTATIONS[element][seed] for element in group}
        unseen -= orbit
        result.append(len(orbit))
    return tuple(sorted(result, reverse=True))


_TARGET_VERTEX_ORBITS = (4, 2)
_TARGET_ORDER = 8


def _is_nontrivial_involution(element: int) -> bool:
    if element == 0:
        return False
    order = PERMUTATIONS[element]
    return all(order[order[index]] == index for index in range(_ARITY))


def _involution_count(group: Subgroup) -> int:
    return sum(_is_nontrivial_involution(element) for element in group)


_TARGET_SUBGROUPS = tuple(
    group
    for group in _SUBGROUPS
    if len(group) == _TARGET_ORDER
    and _vertex_orbit_sizes(group) == _TARGET_VERTEX_ORBITS
    and _involution_count(group) == _EXPECTED_TARGET_INVOLUTIONS
)
_S6 = next(group for group in _SUBGROUPS if len(group) == _GROUP_ORDER)


def _target_coefficients() -> tuple[tuple[Subgroup, int], ...]:
    coefficients = dict.fromkeys(_SUBGROUPS, 0)
    for target in _TARGET_SUBGROUPS:
        supers = tuple(group for group in _SUBGROUPS if target <= group)
        interval = {target: 1}
        for group in supers:
            if group == target:
                continue
            interval[group] = -sum(
                value for smaller, value in interval.items() if smaller < group
            )
        for group, value in interval.items():
            coefficients[group] += value
    return tuple(
        (group, value) for group, value in coefficients.items() if value != 0
    )


_TARGET_COEFFICIENTS = _target_coefficients()
_IDENTITY_GROUP = next(group for group in _SUBGROUPS if len(group) == 1)
_REFERENCE_TARGET = _TARGET_SUBGROUPS[0]


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
    raw = sum(
        coefficient
        * _fixed_pattern_count(_orbit_sizes(subgroup, remaining), weights)
        for subgroup, coefficient in _TARGET_COEFFICIENTS
        if subgroup <= group
    )
    numerator = _TARGET_ORDER * raw
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
            0
            if not pattern and remaining == 0 and group in _TARGET_SUBGROUPS
            else None
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
        return (
            ()
            if rank == 0 and remaining == 0 and group in _TARGET_SUBGROUPS
            else None
        )
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


def _stabilizer_group(edge_values: _EdgeValues) -> Subgroup:
    return frozenset(
        element
        for element in range(_GROUP_ORDER)
        if _permute(edge_values, element) == edge_values
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


@cache
def _weak_vectors(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *suffix)
        for first in range(total + 1)
        for suffix in _weak_vectors(total - first, parts - 1)
    )


@cache
def _subgroup_mobius(group: Subgroup) -> int:
    if group == _IDENTITY_GROUP:
        return 1
    return -sum(
        _subgroup_mobius(smaller)
        for smaller in _SUBGROUPS
        if len(smaller) < len(group) and smaller < group
    )


@cache
def _triple_blocks(target: Subgroup) -> tuple[_TripleBlock, ...]:
    unseen = set(range(_TRIPLE_COORDINATES))
    result: list[_TripleBlock] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(
            sorted({_TRIPLE_PERMUTATIONS[element][seed] for element in target})
        )
        unseen -= set(orbit)
        result.append(orbit)
    return tuple(sorted(result, key=lambda block: (len(block), block)))


def _triple_transform(
    vector: _Vector,
    block: _TripleBlock,
    element: int,
) -> _Vector:
    positions = {coordinate: index for index, coordinate in enumerate(block)}
    result = [0] * len(block)
    for index, coordinate in enumerate(block):
        image = _TRIPLE_PERMUTATIONS[element][coordinate]
        result[positions[image]] = vector[index]
    return tuple(result)


def _triple_stabilizer(
    vector: _Vector,
    block: _TripleBlock,
    group: Subgroup,
) -> Subgroup:
    return frozenset(
        element
        for element in group
        if _triple_transform(vector, block, element) == vector
    )


@cache
def _triple_local_classes(
    context: _TripleContext,
    mass: int,
) -> tuple[_TripleLocalClass, ...]:
    target, step, group = context
    block = _triple_blocks(target)[step]
    unseen = set(_weak_vectors(mass, len(block)))
    result: list[_TripleLocalClass] = []
    while unseen:
        seed = min(unseen)
        orbit = {_triple_transform(seed, block, element) for element in group}
        representative = min(orbit)
        assert seed == representative
        unseen -= orbit
        result.append((
            representative,
            _triple_stabilizer(representative, block, group),
        ))
    return tuple(result)


@cache
def _triple_remaining_orbit_sizes(
    context: _TripleContext,
    subgroup: Subgroup,
) -> _OrbitSizes:
    target, step, _ = context
    blocks = _triple_blocks(target)
    unseen = {coordinate for block in blocks[step:] for coordinate in block}
    result: list[int] = []
    while unseen:
        seed = min(unseen)
        orbit = {_TRIPLE_PERMUTATIONS[element][seed] for element in subgroup}
        unseen -= orbit
        result.append(len(orbit))
    return tuple(sorted(result))


@cache
def _scalar_fixed_count(orbit_sizes: _OrbitSizes, total: int) -> int:
    coefficients = [1] + [0] * total
    for orbit_size in orbit_sizes:
        following = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for value in range((total - degree) // orbit_size + 1):
                following[degree + value * orbit_size] += coefficient
        coefficients = following
    return coefficients[total]


@cache
def _triple_suffix_count(context: _TripleContext, total: int) -> int:
    target, step, group = context
    if step == len(_triple_blocks(target)):
        return int(total == 0 and group == _IDENTITY_GROUP)
    numerator = sum(
        _subgroup_mobius(subgroup)
        * _scalar_fixed_count(
            _triple_remaining_orbit_sizes(context, subgroup), total
        )
        for subgroup in _SUBGROUPS
        if subgroup <= group
    )
    assert numerator % len(group) == 0
    return numerator // len(group)


def _triple_free_count(total: int, group: Subgroup = _REFERENCE_TARGET) -> int:
    return _triple_suffix_count((group, 0, group), total)


@cache
def _residual_branch_count(total: int) -> int:
    return sum(
        (fixed_mass + 1)
        * _class_count(pair_mass)
        * _triple_free_count(total - fixed_mass - pair_mass)
        for fixed_mass in range(total + 1)
        for pair_mass in range(total - fixed_mass + 1)
    )


def _triple_mass_prefix(
    context: _TripleContext,
    remaining: int,
    mass: int,
) -> int:
    target, step, _ = context
    return sum(
        _triple_suffix_count(
            (target, step + 1, stabilizer), remaining - earlier
        )
        for earlier in range(mass)
        for _, stabilizer in _triple_local_classes(context, earlier)
    )


def _triple_same_mass_rank(
    context: _TripleContext,
    remaining: int,
    local: _Vector,
) -> tuple[int, Subgroup] | None:
    target, step, _ = context
    mass = sum(local)
    prefix = 0
    selected: Subgroup | None = None
    for candidate, stabilizer in _triple_local_classes(context, mass):
        count = _triple_suffix_count(
            (target, step + 1, stabilizer), remaining - mass
        )
        if candidate < local:
            prefix += count
        elif candidate == local:
            selected = stabilizer
            break
    return None if selected is None else (prefix, selected)


def _triple_rank(total: int, vector: _Vector, target: Subgroup) -> int | None:
    valid = len(vector) == _TRIPLE_COORDINATES and not any(
        value < 0 for value in vector
    )
    if not valid or sum(vector) != total:
        return None
    remaining = total
    group = target
    result = 0
    for step, block in enumerate(_triple_blocks(target)):
        local = tuple(vector[coordinate] for coordinate in block)
        mass = sum(local)
        context = target, step, group
        result += _triple_mass_prefix(context, remaining, mass)
        selected = _triple_same_mass_rank(context, remaining, local)
        if selected is None:
            return None
        prefix, group = selected
        result += prefix
        remaining -= mass
    return result if remaining == 0 and group == _IDENTITY_GROUP else None


def _triple_unrank_choice(
    context: _TripleContext,
    remaining: int,
    rank: int,
) -> tuple[_Vector, Subgroup, int, int]:
    target, step, _ = context
    for mass in range(remaining + 1):
        for candidate, stabilizer in _triple_local_classes(context, mass):
            count = _triple_suffix_count(
                (target, step + 1, stabilizer), remaining - mass
            )
            if rank >= count:
                rank -= count
                continue
            return candidate, stabilizer, mass, rank
    raise AssertionError


def _triple_unrank(total: int, rank: int, target: Subgroup) -> _Vector | None:
    if rank < 0 or rank >= _triple_free_count(total, target):
        return None
    result = [0] * _TRIPLE_COORDINATES
    remaining = total
    group = target
    for step, block in enumerate(_triple_blocks(target)):
        candidate, group, mass, rank = _triple_unrank_choice(
            (target, step, group), remaining, rank
        )
        for coordinate, value in zip(block, candidate, strict=True):
            result[coordinate] = value
        remaining -= mass
    assert rank == 0
    assert remaining == 0
    assert group == _IDENTITY_GROUP
    return tuple(result)


def _triple_stabilizer_order(vector: _Vector, group: Subgroup) -> int:
    return sum(
        tuple(
            vector[_TRIPLE_PERMUTATIONS[element][index]] for index in range(20)
        )
        == vector
        for element in group
    )


def _fixed_pair(vector: _Vector) -> _FixedPair:
    assert len(vector) == _FIXED_COMPONENTS
    return vector[0], vector[1]


def _branch_masses(
    total: int, fixed: _FixedPair, pairs: _EdgeValues
) -> _BranchMasses:
    fixed_mass = sum(fixed)
    pair_mass = sum(sum(value) for value in pairs)
    return fixed_mass, pair_mass, total - fixed_mass - pair_mass


def _residual_branch_rank_data(
    total: int,
    state: _ResidualBranchState,
) -> _BranchRankData | None:
    fixed, pairs, triples = state
    pair_rank = _rank(pairs)
    group = _stabilizer_group(pairs)
    masses = _branch_masses(total, fixed, pairs)
    result: _BranchRankData | None = None
    valid = (
        not any(value < 0 for value in fixed)
        and pair_rank is not None
        and len(group) == _TARGET_ORDER
        and masses[2] >= 0
    )
    if valid and pair_rank is not None:
        triple_rank = _triple_rank(masses[2], triples, group)
        if triple_rank is not None:
            result = (masses, (_weak_rank(fixed), pair_rank, triple_rank))
    return result


def _residual_branch_prefix(total: int, masses: _BranchMasses) -> int:
    fixed_mass, pair_mass, _ = masses
    return sum(
        (earlier_fixed + 1)
        * _class_count(earlier_pair)
        * _triple_free_count(total - earlier_fixed - earlier_pair)
        for earlier_fixed in range(total + 1)
        for earlier_pair in range(total - earlier_fixed + 1)
        if (earlier_fixed, earlier_pair) < (fixed_mass, pair_mass)
    )


def _residual_branch_local(masses: _BranchMasses, ranks: _BranchRanks) -> int:
    _, pair_mass, triple_mass = masses
    fixed_rank, pair_rank, triple_rank = ranks
    return (
        fixed_rank * _class_count(pair_mass) + pair_rank
    ) * _triple_free_count(triple_mass) + triple_rank


def _residual_branch_rank(
    total: int,
    state: _ResidualBranchState,
) -> int | None:
    data = _residual_branch_rank_data(total, state)
    if data is None:
        return None
    masses, ranks = data
    return _residual_branch_prefix(total, masses) + _residual_branch_local(
        masses, ranks
    )


def _branch_component_ranks(
    pair_count: int, triple_count: int, rank: int
) -> _BranchRanks:
    head, triple_rank = divmod(rank, triple_count)
    fixed_rank, pair_rank = divmod(head, pair_count)
    return fixed_rank, pair_rank, triple_rank


def _residual_branch_unrank_block(
    masses: _BranchMasses,
    rank: int,
) -> _ResidualBranchState:
    fixed_mass, pair_mass, triple_mass = masses
    ranks = _branch_component_ranks(
        _class_count(pair_mass), _triple_free_count(triple_mass), rank
    )
    fixed_rank, pair_rank, triple_rank = ranks
    fixed = _weak_unrank(fixed_mass, _FIXED_COMPONENTS, fixed_rank)
    pairs = _unrank(pair_mass, pair_rank)
    assert fixed is not None
    assert pairs is not None
    triples = _triple_unrank(triple_mass, triple_rank, _stabilizer_group(pairs))
    assert triples is not None
    return _fixed_pair(fixed), pairs, triples


def _residual_branch_unrank(
    total: int, rank: int
) -> _ResidualBranchState | None:
    if rank < 0 or rank >= _residual_branch_count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        for pair_mass in range(total - fixed_mass + 1):
            triple_mass = total - fixed_mass - pair_mass
            block = (
                (fixed_mass + 1)
                * _class_count(pair_mass)
                * _triple_free_count(triple_mass)
            )
            if remaining >= block:
                remaining -= block
                continue
            return _residual_branch_unrank_block(
                (fixed_mass, pair_mass, triple_mass), remaining
            )
    raise AssertionError


@cache
def _complete_branch_count(total: int) -> int:
    return sum(
        (vertex_mass + 1) * _residual_branch_count(total - 6 * vertex_mass)
        for vertex_mass in range(total // 6 + 1)
    )


def _complete_branch_rank(
    total: int,
    state: _CompleteBranchState,
) -> int | None:
    vertex, fixed, pairs, triples = state
    vertex_mass = sum(vertex)
    residual_mass = total - 6 * vertex_mass
    result: int | None = None
    if not any(value < 0 for value in vertex) and residual_mass >= 0:
        residual_rank = _residual_branch_rank(
            residual_mass, (fixed, pairs, triples)
        )
        if residual_rank is not None:
            prefix = sum(
                (earlier + 1) * _residual_branch_count(total - 6 * earlier)
                for earlier in range(vertex_mass)
            )
            result = (
                prefix
                + _weak_rank(vertex) * _residual_branch_count(residual_mass)
                + residual_rank
            )
    return result


def _complete_branch_unrank_block(
    total: int, vertex_mass: int, rank: int
) -> _CompleteBranchState:
    residual_mass = total - 6 * vertex_mass
    residual_count = _residual_branch_count(residual_mass)
    vertex_rank, residual_rank = divmod(rank, residual_count)
    vertex = _weak_unrank(vertex_mass, _FIXED_COMPONENTS, vertex_rank)
    residual = _residual_branch_unrank(residual_mass, residual_rank)
    assert vertex is not None
    assert residual is not None
    fixed, pairs, triples = residual
    return _fixed_pair(vertex), fixed, pairs, triples


def _complete_branch_unrank(
    total: int, rank: int
) -> _CompleteBranchState | None:
    if rank < 0 or rank >= _complete_branch_count(total):
        return None
    remaining = rank
    for vertex_mass in range(total // 6 + 1):
        block = (vertex_mass + 1) * _residual_branch_count(
            total - 6 * vertex_mass
        )
        if remaining >= block:
            remaining -= block
            continue
        return _complete_branch_unrank_block(total, vertex_mass, remaining)
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


def test_pair_c2_cubed_42_counts_match_independent_sequence() -> None:
    """Target-Mobius blocks reproduce exact C2-cubed-42 pair counts."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT
    assert len(_TARGET_SUBGROUPS) == _EXPECTED_TARGET_CONJUGATES
    assert all(
        _involution_count(group) == _EXPECTED_TARGET_INVOLUTIONS
        for group in _TARGET_SUBGROUPS
    )


def test_pair_c2_cubed_42_rank_exhausts_masses_three_through_five() -> None:
    """Every exact C2-cubed-42 pair rank through mass five roundtrips."""
    for total in range(3, _EXHAUSTIVE_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(state) == rank
            assert _stabilizer_order(state) == _TARGET_ORDER


def test_pair_c2_cubed_42_rank_roundtrips_through_fourteen() -> None:
    """Exact C2-cubed-42 pair ranks invert through mass fourteen."""
    for total, count in enumerate(_EXPECTED_COUNTS):
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in _sample_ranks(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(state) == rank
            assert _stabilizer_order(state) == _TARGET_ORDER


def test_pair_c2_cubed_42_triple_geometry_and_counts() -> None:
    """Ten H-invariant triple blocks give the reviewed free V4 quotient."""
    assert tuple(map(len, _triple_blocks(_REFERENCE_TARGET))) == (
        _EXPECTED_TRIPLE_BLOCK_SIZES
    )
    observed = tuple(_triple_free_count(total) for total in range(15))
    assert observed == _EXPECTED_TRIPLE_FREE_COUNTS
    for total in range(1, 5):
        for rank in range(observed[total]):
            vector = _triple_unrank(total, rank, _REFERENCE_TARGET)
            assert vector is not None
            assert _triple_rank(total, vector, _REFERENCE_TARGET) == rank
            assert _triple_stabilizer_order(vector, _REFERENCE_TARGET) == 1


def test_pair_c2_cubed_42_branch_rank_roundtrips_through_fourteen() -> None:
    """Pair, free-V4 triple, fixed, and vertex ranks compose densely."""
    residual = tuple(_residual_branch_count(total) for total in range(15))
    complete = tuple(_complete_branch_count(total) for total in range(15))
    assert residual == _EXPECTED_RESIDUAL_BRANCH_COUNTS
    assert complete == _EXPECTED_COMPLETE_BRANCH_COUNTS
    for total in range(15):
        for rank in _sample_ranks(residual[total]):
            state = _residual_branch_unrank(total, rank)
            assert state is not None
            assert _residual_branch_rank(total, state) == rank
        for rank in _sample_ranks(complete[total]):
            state = _complete_branch_unrank(total, rank)
            assert state is not None
            assert _complete_branch_rank(total, state) == rank
