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
#   - Dense rank/unrank for rooted-S5 residual classes with trivial rooted
#     stabilizer in the top-level all-equal S6 residual domain.
# - Must-Not:
#   - Claim that rooted-S5 trivial implies full-S6 trivial.
#   - Claim dense rank for the final unrooted trivial-S6 interval.
# - Allows:
#   - Inputs: two fixed scalars, five canonical two-component rooted bundles,
#     and ten four-component K5 edge values through mass fourteen.
#   - Outputs: one dense rooted-S5 trivial rank and inverse.
#   - Side effects: none.
# - Split-When:
#   - Full-S6 root selection needs its own constrained-prefix state.
# - Merge-When:
#   - Complete dense full-S6 ranking owns canonical rooted dispatch directly.
# - Summary:
#   - Let bundle equalities choose a Young group, then free-rank its K5 edges.
# - Description:
#   - Pattern/color stabilizer chains are parameterized by sixteen Young groups.
# - Usage:
#   - Constructive prerequisite for the dominant trivial-S6 stabilizer stratum.
# - Defaults:
#   - Exhaustive ranks reach mass three; boundary samples reach mass fourteen.
#

"""Dense rooted-S5 trivial-stabilizer rank for the full S6 residual domain."""

from __future__ import annotations

from functools import cache
from itertools import combinations
from itertools import permutations
from math import comb

_ARITY = 5
_FIXED_COMPONENTS = 2
_BUNDLE_COMPONENTS = 2
_BUNDLE_COUNT = 5
_EDGE_COUNT = 10
_EDGE_COMPONENTS = 4
_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 3
_SAMPLE_DIVISOR = 4
_FULL_EDGE_MASK = (1 << _EDGE_COUNT) - 1
_EXPECTED_COUNTS = (
    0,
    0,
    0,
    40,
    1_340,
    21_462,
    242_629,
    2_204_012,
    17_109_191,
    117_488_832,
    729_410_921,
    4_155_525_962,
    21_962_281_262,
    108_578_479_120,
    505_481_889_514,
)
_WIDTH_FOURTEEN_COUNT = _EXPECTED_COUNTS[-1]
_EXPECTED_BRANCH_COUNTS = {
    (5,): 36_138_820_806,
    (4, 1): 139_829_538_243,
    (3, 2): 58_148_591_048,
    (3, 1, 1): 148_170_968_754,
    (2, 2, 1): 64_809_370_672,
    (2, 1, 1, 1): 55_291_253_944,
    (1, 1, 1, 1, 1): 3_093_346_047,
}

type _Pair = tuple[int, int]
type _Bundles = tuple[_Pair, _Pair, _Pair, _Pair, _Pair]
type _EdgeValue = tuple[int, int, int, int]
type _EdgeValues = tuple[_EdgeValue, ...]
type _State = tuple[_Pair, _Bundles, _EdgeValues]
type _Partition = tuple[int, ...]
type _MassBlock = tuple[int, int]
type _Permutation = tuple[int, int, int, int, int]
type _EdgePermutation = tuple[int, ...]
type _Group = tuple[int, ...]
type _Weights = tuple[int, ...]
type _Pattern = tuple[int, ...]
type _Masses = tuple[int, ...]
type _PatternContext = tuple[int, _Group]
type _PatternChoice = tuple[int, _Group, int]

_EDGES = tuple(
    (left, right) for left in range(_ARITY) for right in range(left + 1, _ARITY)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}


def _as_permutation(order: tuple[int, ...]) -> _Permutation:
    assert len(order) == _ARITY
    first, second, third, fourth, fifth = order
    return first, second, third, fourth, fifth


_S5: tuple[_Permutation, ...] = tuple(
    _as_permutation(order) for order in permutations(range(_ARITY))
)


def _edge_permutation(order: _Permutation) -> _EdgePermutation:
    result: list[int] = []
    for left, right in _EDGES:
        image = tuple(sorted((order[left], order[right])))
        result.append(_EDGE_INDEX[image[0], image[1]])
    return tuple(result)


_EDGE_PERMUTATIONS = tuple(_edge_permutation(order) for order in _S5)
_ALL_GROUP: _Group = tuple(range(len(_EDGE_PERMUTATIONS)))


def _map_mask(mask: int, mapping: _EdgePermutation) -> int:
    result = 0
    for edge in range(_EDGE_COUNT):
        if mask & (1 << edge):
            result |= 1 << mapping[edge]
    return result


_MASK_IMAGES = tuple(
    tuple(_map_mask(mask, mapping) for mask in range(1 << _EDGE_COUNT))
    for mapping in _EDGE_PERMUTATIONS
)


def _positive_compositions(total: int) -> tuple[_Weights, ...]:
    if total == 0:
        return ((),)
    return tuple(
        (first, *suffix)
        for first in range(1, total + 1)
        for suffix in _positive_compositions(total - first)
    )


_WEIGHT_COMPOSITIONS = _positive_compositions(_EDGE_COUNT)


def _subset_masks(mask: int, size: int) -> tuple[int, ...]:
    bits = tuple(edge for edge in range(_EDGE_COUNT) if mask & (1 << edge))
    return tuple(
        sorted(
            sum(1 << edge for edge in choice)
            for choice in combinations(bits, size)
        )
    )


def _is_canonical_block(block: int, group: _Group) -> bool:
    return block == min(_MASK_IMAGES[element][block] for element in group)


def _block_stabilizer(block: int, group: _Group) -> _Group:
    return tuple(
        element for element in group if _MASK_IMAGES[element][block] == block
    )


@cache
def _pattern_suffix_count(
    weights: _Weights,
    remaining: int,
    group: _Group,
) -> int:
    if not weights:
        return int(remaining == 0 and len(group) == 1)
    size = weights[0]
    result = 0
    for block in _subset_masks(remaining, size):
        if not _is_canonical_block(block, group):
            continue
        stabilizer = _block_stabilizer(block, group)
        result += _pattern_suffix_count(
            weights[1:],
            remaining ^ block,
            stabilizer,
        )
    return result


@cache
def _pattern_count(weights: _Weights, group: _Group) -> int:
    return _pattern_suffix_count(weights, _FULL_EDGE_MASK, group)


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
        for block in _subset_masks(remaining, weights[0])
        if _is_canonical_block(block, group)
        for stabilizer in (_block_stabilizer(block, group),)
    )


def _pattern_rank_choice(
    weights: _Weights,
    target: int,
    context: _PatternContext,
) -> tuple[int, int, _Group] | None:
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


def _pattern_rank(
    weights: _Weights,
    pattern: _Pattern,
    group: _Group,
) -> int | None:
    return _pattern_rank_from(weights, pattern, (_FULL_EDGE_MASK, group))


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


def _pattern_unrank(
    weights: _Weights,
    rank: int,
    group: _Group,
) -> _Pattern | None:
    if rank < 0 or rank >= _pattern_count(weights, group):
        return None
    return _pattern_unrank_from(weights, rank, (_FULL_EDGE_MASK, group))


def _composition_count(total: int) -> int:
    return comb(total + _EDGE_COMPONENTS - 1, _EDGE_COMPONENTS - 1)


def _composition_rank(value: _EdgeValue) -> int:
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


def _composition_unrank(total: int, rank: int) -> _EdgeValue | None:
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


def _value_key(value: _EdgeValue) -> tuple[int, int]:
    return sum(value), _composition_rank(value)


@cache
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


def _canonical_pattern(pattern: _Pattern, group: _Group) -> _Pattern:
    return min(
        tuple(_MASK_IMAGES[element][block] for block in pattern)
        for element in group
    )


def _state_pattern(
    edge_values: _EdgeValues,
    group: _Group,
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
    return weights, _canonical_pattern(blocks, group), colors


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


_PAIR_VALUES = tuple(
    sorted(
        (
            (first, second)
            for first in range(_MAXIMUM_MASS + 1)
            for second in range(_MAXIMUM_MASS - first + 1)
        ),
        key=lambda pair: (sum(pair), pair[0]),
    )
)


def _bundle_key(bundle: _Pair) -> tuple[int, int]:
    return sum(bundle), bundle[0]


@cache
def _bundle_sequences_from(
    start: int,
    slots: int,
    total: int,
) -> tuple[tuple[_Pair, ...], ...]:
    if slots == 0:
        return ((),) if total == 0 else ()
    result: list[tuple[_Pair, ...]] = []
    for index in range(start, len(_PAIR_VALUES)):
        pair = _PAIR_VALUES[index]
        mass = sum(pair)
        if mass > total:
            break
        result.extend(
            (pair, *suffix)
            for suffix in _bundle_sequences_from(
                index,
                slots - 1,
                total - mass,
            )
        )
    return tuple(result)


@cache
def _bundle_sequences(total: int) -> tuple[_Bundles, ...]:
    return tuple(
        (values[0], values[1], values[2], values[3], values[4])
        for values in _bundle_sequences_from(0, _BUNDLE_COUNT, total)
    )


def _run_sizes(bundles: _Bundles) -> tuple[int, ...]:
    result: list[int] = []
    start = 0
    while start < _BUNDLE_COUNT:
        end = start + 1
        while end < _BUNDLE_COUNT and bundles[end] == bundles[start]:
            end += 1
        result.append(end - start)
        start = end
    return tuple(result)


def _partition(bundles: _Bundles) -> tuple[int, ...]:
    return tuple(sorted(_run_sizes(bundles), reverse=True))


@cache
def _group_for_runs(run_sizes: tuple[int, ...]) -> _Group:
    blocks: list[frozenset[int]] = []
    start = 0
    for size in run_sizes:
        blocks.append(frozenset(range(start, start + size)))
        start += size
    assert start == _BUNDLE_COUNT
    return tuple(
        index
        for index, order in enumerate(_S5)
        if all(
            frozenset(order[item] for item in block) == block
            for block in blocks
        )
    )


@cache
def _edge_count(run_sizes: tuple[int, ...], total: int) -> int:
    group = _group_for_runs(run_sizes)
    return sum(
        _pattern_count(weights, group) * _color_count(weights, total)
        for weights in _WEIGHT_COMPOSITIONS
    )


def _edge_weight_prefix(
    run_sizes: tuple[int, ...],
    weights: _Weights,
    total: int,
) -> int:
    group = _group_for_runs(run_sizes)
    result = 0
    for candidate in _WEIGHT_COMPOSITIONS:
        if candidate == weights:
            return result
        result += _pattern_count(candidate, group) * _color_count(
            candidate, total
        )
    raise AssertionError


def _edge_rank_data(
    run_sizes: tuple[int, ...],
    total: int,
    data: tuple[_Weights, _Pattern, tuple[_EdgeValue, ...]],
) -> int | None:
    weights, pattern, colors = data
    group = _group_for_runs(run_sizes)
    pattern_rank = _pattern_rank(weights, pattern, group)
    color_rank = _color_rank(weights, colors)
    if pattern_rank is None or color_rank is None:
        return None
    color_count = _color_count(weights, total)
    return (
        _edge_weight_prefix(run_sizes, weights, total)
        + pattern_rank * color_count
        + color_rank
    )


def _edge_rank(bundles: _Bundles, edge_values: _EdgeValues) -> int | None:
    result: int | None = None
    if len(edge_values) == _EDGE_COUNT:
        run_sizes = _run_sizes(bundles)
        group = _group_for_runs(run_sizes)
        data = _state_pattern(edge_values, group)
        if data is not None:
            total = sum(sum(value) for value in edge_values)
            result = _edge_rank_data(run_sizes, total, data)
    return result


def _edge_unrank(
    bundles: _Bundles,
    total: int,
    rank: int,
) -> _EdgeValues | None:
    run_sizes = _run_sizes(bundles)
    group = _group_for_runs(run_sizes)
    if rank < 0 or rank >= _edge_count(run_sizes, total):
        return None
    remaining = rank
    for weights in _WEIGHT_COMPOSITIONS:
        color_count = _color_count(weights, total)
        block = _pattern_count(weights, group) * color_count
        if remaining >= block:
            remaining -= block
            continue
        pattern_rank, color_rank = divmod(remaining, color_count)
        pattern = _pattern_unrank(weights, pattern_rank, group)
        colors = _color_unrank(weights, total, color_rank)
        assert pattern is not None
        assert colors is not None
        return _state_from_pattern(pattern, colors)
    raise AssertionError


@cache
def _bundle_edge_count(bundle_mass: int, edge_mass: int) -> int:
    return sum(
        _edge_count(_run_sizes(bundles), edge_mass)
        for bundles in _bundle_sequences(bundle_mass)
    )


@cache
def _class_count(total: int) -> int:
    return sum(
        (fixed_mass + 1)
        * _bundle_edge_count(bundle_mass, total - fixed_mass - bundle_mass)
        for fixed_mass in range(total + 1)
        for bundle_mass in range(total - fixed_mass + 1)
    )


def _mass_prefix(total: int, fixed_mass: int, bundle_mass: int) -> int:
    return sum(
        (candidate_fixed + 1)
        * _bundle_edge_count(
            candidate_bundle,
            total - candidate_fixed - candidate_bundle,
        )
        for candidate_fixed in range(total + 1)
        for candidate_bundle in range(total - candidate_fixed + 1)
        if (candidate_fixed, candidate_bundle) < (fixed_mass, bundle_mass)
    )


def _bundle_prefix(
    bundles: _Bundles,
    bundle_mass: int,
    edge_mass: int,
) -> int:
    result = 0
    for candidate in _bundle_sequences(bundle_mass):
        if candidate == bundles:
            return result
        result += _edge_count(_run_sizes(candidate), edge_mass)
    raise AssertionError


def _rank(total: int, state: _State) -> int | None:
    fixed, bundles, edges = state
    fixed_mass = sum(fixed)
    bundle_mass = sum(sum(bundle) for bundle in bundles)
    edge_mass = total - fixed_mass - bundle_mass
    valid = (
        len(fixed) == _FIXED_COMPONENTS
        and all(value >= 0 for value in fixed)
        and tuple(sorted(bundles, key=_bundle_key)) == bundles
        and edge_mass >= 0
        and sum(sum(value) for value in edges) == edge_mass
    )
    result: int | None = None
    if valid:
        edge_rank = _edge_rank(bundles, edges)
        if edge_rank is not None:
            bundle_edge_count = _bundle_edge_count(bundle_mass, edge_mass)
            result = (
                _mass_prefix(total, fixed_mass, bundle_mass)
                + fixed[0] * bundle_edge_count
                + _bundle_prefix(bundles, bundle_mass, edge_mass)
                + edge_rank
            )
    return result


@cache
def _mass_blocks(total: int) -> tuple[_MassBlock, ...]:
    return tuple(
        (fixed_mass, bundle_mass)
        for fixed_mass in range(total + 1)
        for bundle_mass in range(total - fixed_mass + 1)
    )


def _unrank_mass_block(
    total: int,
    block: _MassBlock,
    rank: int,
) -> tuple[_State | None, int]:
    fixed_mass, bundle_mass = block
    edge_mass = total - fixed_mass - bundle_mass
    bundle_edge_count = _bundle_edge_count(bundle_mass, edge_mass)
    block_count = (fixed_mass + 1) * bundle_edge_count
    if rank >= block_count:
        return None, rank - block_count
    fixed_rank, local_rank = divmod(rank, bundle_edge_count)
    fixed = fixed_rank, fixed_mass - fixed_rank
    for bundles in _bundle_sequences(bundle_mass):
        edge_count = _edge_count(_run_sizes(bundles), edge_mass)
        if local_rank >= edge_count:
            local_rank -= edge_count
            continue
        edges = _edge_unrank(bundles, edge_mass, local_rank)
        assert edges is not None
        return (fixed, bundles, edges), 0
    raise AssertionError


def _unrank(total: int, rank: int) -> _State | None:
    result: _State | None = None
    if 0 <= rank < _class_count(total):
        remaining = rank
        for block in _mass_blocks(total):
            result, remaining = _unrank_mass_block(total, block, remaining)
            if result is not None:
                break
        else:
            raise AssertionError
    return result


def _permute_bundles(bundles: _Bundles, order: _Permutation) -> _Bundles:
    values = tuple(bundles[order[index]] for index in range(_BUNDLE_COUNT))
    return values[0], values[1], values[2], values[3], values[4]


def _permute_edges(
    edge_values: _EdgeValues, order: _Permutation
) -> _EdgeValues:
    mapping = _edge_permutation(order)
    return tuple(edge_values[mapping[edge]] for edge in range(_EDGE_COUNT))


def _stabilizer_order(state: _State) -> int:
    _, bundles, edges = state
    return sum(
        _permute_bundles(bundles, order) == bundles
        and _permute_edges(edges, order) == edges
        for order in _S5
    )


def _branch_counts(total: int) -> dict[_Partition, int]:
    result: dict[_Partition, int] = dict.fromkeys(_EXPECTED_BRANCH_COUNTS, 0)
    for fixed_mass in range(total + 1):
        for bundle_mass in range(total - fixed_mass + 1):
            edge_mass = total - fixed_mass - bundle_mass
            for bundles in _bundle_sequences(bundle_mass):
                result[_partition(bundles)] += (fixed_mass + 1) * _edge_count(
                    _run_sizes(bundles), edge_mass
                )
    return result


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


def test_rooted_s5_trivial_counts_match_independent_lattice_sequence() -> None:
    """Young-free edge branches reconstruct the rooted-S5 trivial sequence."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT
    assert _branch_counts(_MAXIMUM_MASS) == _EXPECTED_BRANCH_COUNTS


def test_rooted_s5_trivial_rank_exhausts_small_domains() -> None:
    """Every rooted-trivial rank is dense through mass three."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_rooted_s5_trivial_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior ranks invert through the mass-fourteen interval."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in _sample_ranks(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_rooted_s5_trivial_samples_have_trivial_root_stabilizer() -> None:
    """Sampled rooted representatives have no nonidentity S5 stabilizer."""
    for total in (3, 5, 8, _MAXIMUM_MASS):
        for rank in _sample_ranks(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _stabilizer_order(state) == 1
