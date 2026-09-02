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
#   - Dense rank/unrank for trivial-stabilizer four-component K5 edge orbits.
# - Must-Not:
#   - Claim a local rank for any nontrivial exact S5 stabilizer stratum.
# - Allows:
#   - Inputs: ten four-component K5 edge values through mass fourteen.
#   - Outputs: dense ranks from ordered equality patterns and strict colors.
#   - Side effects: none.
# - Split-When:
#   - Ordered edge-pattern ranking becomes a separately consumed primitive.
# - Merge-When:
#   - Complete widened full-S5 ranking owns every exact stabilizer stratum.
# - Summary:
#   - Separate ordered edge-equality patterns from increasing edge values.
# - Description:
#   - Stabilizer-chain subset orbits rank patterns; combinadics rank colors.
# - Usage:
#   - Completes the 19,963,566,552-class mass-fourteen generic S5 stratum.
# - Defaults:
#   - Direct raw S5 orbit comparison stops at mass three; ranks reach fourteen.
#

"""Dense ordered-pattern ranking for trivial-stabilizer widened K5 edges."""

from __future__ import annotations

from functools import cache
from itertools import combinations
from itertools import permutations
from math import comb

_ARITY = 5
_EDGE_COUNT = 10
_EDGE_COMPONENTS = 4
_SCALAR_COMPONENTS = _EDGE_COUNT * _EDGE_COMPONENTS
_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 3
_SAMPLE_DIVISOR = 4
_FULL_EDGE_MASK = (1 << _EDGE_COUNT) - 1
_EXPECTED_COUNTS = (
    0,
    0,
    0,
    28,
    608,
    6_896,
    58_532,
    409_700,
    2_492_068,
    13_554_716,
    67_188_884,
    307_526_548,
    1_312_575_006,
    5_264_371_340,
    19_963_566_552,
)
_WIDTH_FOURTEEN_COUNT = _EXPECTED_COUNTS[-1]

type _Vector = tuple[int, ...]
type _EdgeValue = tuple[int, int, int, int]
type _EdgeValues = tuple[_EdgeValue, ...]
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


def _pattern_count(weights: _Weights) -> int:
    return _pattern_suffix_count(weights, _FULL_EDGE_MASK, _ALL_GROUP)


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


def _pattern_rank(weights: _Weights, pattern: _Pattern) -> int | None:
    return _pattern_rank_from(weights, pattern, (_FULL_EDGE_MASK, _ALL_GROUP))


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
    if rank < 0 or rank >= _pattern_count(weights):
        return None
    return _pattern_unrank_from(weights, rank, (_FULL_EDGE_MASK, _ALL_GROUP))


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


def _canonical_pattern(pattern: _Pattern) -> _Pattern:
    return min(
        tuple(_MASK_IMAGES[element][block] for block in pattern)
        for element in _ALL_GROUP
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


def _class_count(total: int) -> int:
    return sum(
        _pattern_count(weights) * _color_count(weights, total)
        for weights in _WEIGHT_COMPOSITIONS
    )


def _weight_prefix(weights: _Weights, total: int) -> int:
    result = 0
    for candidate in _WEIGHT_COMPOSITIONS:
        if candidate == weights:
            return result
        result += _pattern_count(candidate) * _color_count(candidate, total)
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
    for weights in _WEIGHT_COMPOSITIONS:
        color_count = _color_count(weights, total)
        block = _pattern_count(weights) * color_count
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


def _permute(edge_values: _EdgeValues, order: _Permutation) -> _EdgeValues:
    mapping = _edge_permutation(order)
    return tuple(edge_values[mapping[edge]] for edge in range(_EDGE_COUNT))


def _stabilizer_order(edge_values: _EdgeValues) -> int:
    return sum(_permute(edge_values, order) == edge_values for order in _S5)


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *suffix)
        for first in range(total + 1)
        for suffix in _weak_compositions(total - first, parts - 1)
    )


def _edge_values_from_vector(vector: _Vector) -> _EdgeValues:
    assert len(vector) == _SCALAR_COMPONENTS
    values = tuple(
        vector[index : index + _EDGE_COMPONENTS]
        for index in range(0, _SCALAR_COMPONENTS, _EDGE_COMPONENTS)
    )
    return tuple((value[0], value[1], value[2], value[3]) for value in values)


def _direct_trivial_representatives(total: int) -> tuple[_EdgeValues, ...]:
    representatives: set[_EdgeValues] = set()
    for vector in _weak_compositions(total, _SCALAR_COMPONENTS):
        edge_values = _edge_values_from_vector(vector)
        representative = min(_permute(edge_values, order) for order in _S5)
        if _stabilizer_order(representative) == 1:
            representatives.add(representative)
    return tuple(sorted(representatives))


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


def test_trivial_pattern_color_factorization_matches_lattice_counts() -> None:
    """Pattern and color factors reproduce the exact free sequence."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT


def test_trivial_pattern_rank_exhausts_small_feasible_patterns() -> None:
    """Every pattern used through mass four has one dense rank."""
    for weights in _WEIGHT_COMPOSITIONS:
        if _color_count(weights, 4) == 0:
            continue
        count = _pattern_count(weights)
        for rank in range(count):
            pattern = _pattern_unrank(weights, rank)
            assert pattern is not None
            assert _pattern_rank(weights, pattern) == rank
        assert _pattern_unrank(weights, -1) is None
        assert _pattern_unrank(weights, count) is None


def test_trivial_rank_matches_direct_small_s5_orbits() -> None:
    """Dense ranks agree with direct free S5 orbits through mass three."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        direct = _direct_trivial_representatives(total)
        observed = {_rank(edge_values) for edge_values in direct}
        assert observed == set(range(_class_count(total)))
        for edge_values in direct:
            rank = _rank(edge_values)
            assert rank is not None
            decoded = _unrank(total, rank)
            assert decoded is not None
            assert _rank(decoded) == rank
            assert _stabilizer_order(decoded) == 1
            for order in _S5:
                assert _rank(_permute(edge_values, order)) == rank


def test_trivial_rank_roundtrips_through_mass_fourteen() -> None:
    """Generic S5 rank samples roundtrip through mass fourteen."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in _sample_ranks(count):
            edge_values = _unrank(total, rank)
            assert edge_values is not None
            assert _rank(edge_values) == rank
            assert _stabilizer_order(edge_values) == 1
