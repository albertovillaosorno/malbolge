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
#   - Dense rank/unrank for the S6 top-level vertex partition (4,2).
# - Must-Not:
#   - Claim dense ranking for the all-equal top-level S6 partition (6).
# - Allows:
#   - Inputs: sorted (4,2) vertex pairs and 52 residual scalar counts.
#   - Outputs: dense full-stratum rank under residual S4-times-S2.
#   - Side effects: none.
# - Split-When:
#   - The hard pair-valued K4 block rank is reused by another proof.
# - Merge-When:
#   - Complete dense S6 ranking owns all eleven top-level Young strata.
# - Summary:
#   - Rank the hard twelve-coordinate block first, then a stabilizer chain.
# - Description:
#   - Uses the proved pair-valued S4 K4 rank before the singleton swap.
# - Usage:
#   - Completes the 122,060,462,590-class mass-fourteen (4,2) stratum.
# - Defaults:
#   - Direct residual orbit exhaustion stops at mass two; full ranks reach 14.
#

"""Dense hard-block-first rank for the S6 (4,2) Young stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import permutations
from math import comb
from operator import itemgetter
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Callable

_ACTIVE = (0, 1, 2, 3)
_BLOCK_COMPONENTS = 4
_EDGE_BLOCK_COUNT = 3
_EDGE_COUNT = 6
_EXHAUSTIVE_MASS = 3
_EXHAUSTIVE_RANK_MASS = 6
_MAXIMUM_MASS = 14
_PAIR_COMPONENTS = 2
_WIDTH_FOURTEEN_COUNT = 191_180
_EDGES = tuple(
    (left, right) for left in _ACTIVE for right in _ACTIVE if left < right
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}
_OPPOSITE = (
    ((0, 1), (2, 3)),
    ((0, 2), (1, 3)),
    ((0, 3), (1, 2)),
)
_S4 = tuple(permutations(_ACTIVE))

type _Block = tuple[int, int, int, int]
type _Blocks = tuple[_Block, _Block, _Block]
type _EdgePairs = tuple[
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
    tuple[int, int],
]
type _Vector = tuple[int, ...]


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _rep_combination_rank(values: tuple[int, ...], population: int) -> int:
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


def _rep_combination_unrank(
    population: int,
    size: int,
    rank: int,
) -> tuple[int, ...]:
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


_t = cast("Callable[[_Block], _Block]", itemgetter(2, 3, 0, 1))


@cache
def _fixed_representatives(total: int) -> tuple[_Block, ...]:
    if total % 2 != 0:
        return ()
    half = total // 2
    return tuple(
        (pair[0], pair[1], pair[0], pair[1])
        for pair in _weak_compositions(half, _PAIR_COMPONENTS)
    )


@cache
def _moving_representatives(total: int) -> tuple[_Block, ...]:
    representatives: set[_Block] = set()
    for vector in _weak_compositions(total, _BLOCK_COMPONENTS):
        block = vector[0], vector[1], vector[2], vector[3]
        if _t(block) != block:
            representatives.add(min(block, _t(block)))
    return tuple(sorted(representatives))


def _fixed_count(total: int) -> int:
    return len(_fixed_representatives(total))


def _moving_count(total: int) -> int:
    return len(_moving_representatives(total))


def _orbit_count(total: int) -> int:
    return _fixed_count(total) + _moving_count(total)


def _block_orbit_rank(block: _Block) -> tuple[int, bool, bool]:
    total = sum(block)
    fixed = _fixed_representatives(total)
    if block in fixed:
        return fixed.index(block), False, False
    canonical = min(block, _t(block))
    moving = _moving_representatives(total)
    return (
        _fixed_count(total) + moving.index(canonical),
        True,
        block != canonical,
    )


def _block_orbit_unrank(total: int, rank: int, *, flipped: bool) -> _Block:
    fixed = _fixed_count(total)
    if rank < fixed:
        return _fixed_representatives(total)[rank]
    block = _moving_representatives(total)[rank - fixed]
    return _t(block) if flipped else block


def _moving_orbit_unrank(total: int, rank: int, *, flipped: bool) -> _Block:
    block = _moving_representatives(total)[rank]
    return _t(block) if flipped else block


def _mass_triples(total: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (first, second, total - first - second)
        for first in range(total + 1)
        for second in range(first, total + 1)
        if second <= total - first - second
    )


def _multiset_count(populations: tuple[int, int, int]) -> int:
    first, second, third = populations
    if first == second == third:
        result = comb(first + 2, 3)
    elif first == second:
        result = comb(first + 1, 2) * third
    elif second == third:
        result = first * comb(second + 1, 2)
    else:
        result = first * second * third
    return result


def _block_counts(masses: tuple[int, int, int]) -> tuple[int, int]:
    first, second, third = masses
    base = _multiset_count((
        _orbit_count(first),
        _orbit_count(second),
        _orbit_count(third),
    ))
    moving = _multiset_count((
        _moving_count(first),
        _moving_count(second),
        _moving_count(third),
    ))
    return base, moving


def _mass_block_count(masses: tuple[int, int, int]) -> int:
    base, moving = _block_counts(masses)
    return base + moving


@cache
def _edge_class_count(total: int) -> int:
    return sum(_mass_block_count(masses) for masses in _mass_triples(total))


def _multiset_rank(
    values: tuple[int, int, int],
    populations: tuple[int, int, int],
) -> int:
    first, second, third = populations
    if first == second == third:
        result = _rep_combination_rank(values, first)
    elif first == second:
        result = _rep_combination_rank(values[:2], first) * third + values[2]
    elif second == third:
        result = values[0] * comb(second + 1, 2) + _rep_combination_rank(
            values[1:], second
        )
    else:
        result = (values[0] * second + values[1]) * third + values[2]
    return result


def _unrank_all_equal(population: int, rank: int) -> tuple[int, int, int]:
    values = _rep_combination_unrank(population, _EDGE_BLOCK_COUNT, rank)
    return values[0], values[1], values[2]


def _unrank_first_equal(
    population: int,
    third: int,
    rank: int,
) -> tuple[int, int, int]:
    pair_rank, last = divmod(rank, third)
    pair = _rep_combination_unrank(population, _PAIR_COMPONENTS, pair_rank)
    return pair[0], pair[1], last


def _unrank_last_equal(
    first: int,
    population: int,
    rank: int,
) -> tuple[int, int, int]:
    pair_count = comb(population + 1, 2)
    first_rank, pair_rank = divmod(rank, pair_count)
    pair = _rep_combination_unrank(population, _PAIR_COMPONENTS, pair_rank)
    assert first_rank < first
    return first_rank, pair[0], pair[1]


def _multiset_unrank(
    populations: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    first, second, third = populations
    if first == second == third:
        result = _unrank_all_equal(first, rank)
    elif first == second:
        result = _unrank_first_equal(first, third, rank)
    elif second == third:
        result = _unrank_last_equal(first, second, rank)
    else:
        first_rank, tail = divmod(rank, second * third)
        second_rank, third_rank = divmod(tail, third)
        result = first_rank, second_rank, third_rank
    return result


def _blocks_from_edges(edge_pairs: _EdgePairs) -> _Blocks:
    blocks: list[_Block] = []
    for left_edge, right_edge in _OPPOSITE:
        left = edge_pairs[_EDGE_INDEX[left_edge]]
        right = edge_pairs[_EDGE_INDEX[right_edge]]
        blocks.append((left[0], left[1], right[0], right[1]))
    return blocks[0], blocks[1], blocks[2]


def _edges_from_blocks(blocks: _Blocks) -> _EdgePairs:
    result: list[tuple[int, int] | None] = [None] * _EDGE_COUNT
    for block, (left_edge, right_edge) in zip(blocks, _OPPOSITE, strict=True):
        result[_EDGE_INDEX[left_edge]] = block[0], block[1]
        result[_EDGE_INDEX[right_edge]] = block[2], block[3]
    first, second, third, fourth, fifth, sixth = result
    assert first is not None
    assert second is not None
    assert third is not None
    assert fourth is not None
    assert fifth is not None
    assert sixth is not None
    return first, second, third, fourth, fifth, sixth


def _canonical_block_data(
    edge_pairs: _EdgePairs,
) -> tuple[tuple[int, int, int], tuple[int, int, int], bool, bool]:
    rows: list[tuple[int, int, bool, bool]] = []
    for block in _blocks_from_edges(edge_pairs):
        orbit, moving, flipped = _block_orbit_rank(block)
        rows.append((sum(block), orbit, moving, flipped))
    rows.sort()
    masses = rows[0][0], rows[1][0], rows[2][0]
    orbits = rows[0][1], rows[1][1], rows[2][1]
    all_moving = all(row[2] for row in rows)
    parity = bool(sum(int(row[3]) for row in rows) % 2)
    return masses, orbits, all_moving, parity


def _extra_rank(
    masses: tuple[int, int, int],
    orbits: tuple[int, int, int],
) -> int:
    moving_values = (
        orbits[0] - _fixed_count(masses[0]),
        orbits[1] - _fixed_count(masses[1]),
        orbits[2] - _fixed_count(masses[2]),
    )
    moving_populations = (
        _moving_count(masses[0]),
        _moving_count(masses[1]),
        _moving_count(masses[2]),
    )
    return _multiset_rank(moving_values, moving_populations)


def _local_rank(
    masses: tuple[int, int, int],
    orbits: tuple[int, int, int],
    *,
    all_moving: bool,
    parity: bool,
) -> int:
    populations = (
        _orbit_count(masses[0]),
        _orbit_count(masses[1]),
        _orbit_count(masses[2]),
    )
    base_rank = _multiset_rank(orbits, populations)
    if not all_moving or not parity:
        return base_rank
    base_count, _ = _block_counts(masses)
    return base_count + _extra_rank(masses, orbits)


def _edge_rank(edge_pairs: _EdgePairs) -> int | None:
    if len(edge_pairs) != _EDGE_COUNT or any(
        value < 0 for pair in edge_pairs for value in pair
    ):
        return None
    total = sum(value for pair in edge_pairs for value in pair)
    masses, orbits, all_moving, parity = _canonical_block_data(edge_pairs)
    prefix = sum(
        _mass_block_count(candidate)
        for candidate in _mass_triples(total)
        if candidate < masses
    )
    return prefix + _local_rank(
        masses,
        orbits,
        all_moving=all_moving,
        parity=parity,
    )


def _choose_mass_block(
    total: int,
    rank: int,
) -> tuple[tuple[int, int, int], int]:
    remaining = rank
    for masses in _mass_triples(total):
        block = _mass_block_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        return masses, remaining
    raise AssertionError


def _unrank_base(
    masses: tuple[int, int, int],
    rank: int,
) -> _Blocks:
    populations = (
        _orbit_count(masses[0]),
        _orbit_count(masses[1]),
        _orbit_count(masses[2]),
    )
    values = _multiset_unrank(populations, rank)
    return (
        _block_orbit_unrank(masses[0], values[0], flipped=False),
        _block_orbit_unrank(masses[1], values[1], flipped=False),
        _block_orbit_unrank(masses[2], values[2], flipped=False),
    )


def _unrank_extra(
    masses: tuple[int, int, int],
    rank: int,
) -> _Blocks:
    populations = (
        _moving_count(masses[0]),
        _moving_count(masses[1]),
        _moving_count(masses[2]),
    )
    values = _multiset_unrank(populations, rank)
    blocks = [
        _moving_orbit_unrank(mass, value, flipped=False)
        for mass, value in zip(masses, values, strict=True)
    ]
    blocks[-1] = _t(blocks[-1])
    return blocks[0], blocks[1], blocks[2]


def _edge_unrank(total: int, rank: int) -> _EdgePairs | None:
    if rank < 0 or rank >= _edge_class_count(total):
        return None
    masses, local = _choose_mass_block(total, rank)
    base_count, _ = _block_counts(masses)
    blocks = (
        _unrank_base(masses, local)
        if local < base_count
        else _unrank_extra(masses, local - base_count)
    )
    return _edges_from_blocks(blocks)


def _fixed_count_from_cycles(cycles: tuple[int, ...], total: int) -> int:
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


# Full S4-times-S2 residual action.
_ARITY = 6
_RESIDUAL_COMPONENTS = 52
_RESIDUAL_RANK_MAXIMUM_MASS = 12
_FULL_MAXIMUM_MASS = 14
_FULL_EXHAUSTIVE_MASS = 6
_VERTEX_PARTITION = (4, 2)
_FULL_GROUP_ORDER = 48
_HARD_BLOCK_COMPONENTS = _EDGE_COUNT * _PAIR_COMPONENTS
_EXPECTED_BLOCK_SIZES = (12, 8, 8, 6, 6, 4, 4, 4)
_SINGLETON_SWAP = (0, 1, 2, 3, 5, 4)
_IDENTITY_SIX = (0, 1, 2, 3, 4, 5)
_WIDTH_TWELVE_RESIDUAL = 56_081_016_751
_WIDTH_FOURTEEN_FULL = 122_060_462_590
_EXPECTED_RESIDUAL_COUNTS = (
    1,
    11,
    113,
    1_137,
    11_167,
    103_188,
    879_530,
    6_852_156,
    48_774_117,
    318_468_417,
    1_918_648_907,
    10_732_517_607,
    56_081_016_751,
)
_EXPECTED_FULL_COUNTS = {
    2: 2,
    3: 22,
    4: 231,
    5: 2_329,
    6: 22_905,
    7: 212_127,
    8: 1_815_587,
    9: 14_227_228,
    10: 102_014_488,
    11: 671_832_880,
    12: 4_086_604_204,
    13: 23_099_957_904,
    14: 122_060_462_590,
}

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _PermutationSix = tuple[int, int, int, int, int, int]
type _ResidualVector = tuple[int, ...]
type _LocalClass = tuple[_Vector, int]
type _State = tuple[_Vertices, _ResidualVector]
type _MassContext = tuple[int, int]
type _UnrankContext = tuple[int, int, int]

_RESIDUAL_LABELS = tuple(
    symbol
    for symbol in range(1 << _ARITY)
    if symbol.bit_count() not in {1, _ARITY - 1}
)
_RESIDUAL_INDEX = {label: index for index, label in enumerate(_RESIDUAL_LABELS)}
_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_FULL_MAXIMUM_MASS + 1)
    for second in range(_FULL_MAXIMUM_MASS - first + 1)
)


def _as_six(order: tuple[int, ...]) -> _PermutationSix:
    assert len(order) == _ARITY
    first, second, third, fourth, fifth, sixth = order
    return first, second, third, fourth, fifth, sixth


def _compose_six(
    left: _PermutationSix,
    right: _PermutationSix,
) -> _PermutationSix:
    return _as_six(tuple(left[right[index]] for index in range(_ARITY)))


_S4_SIX = tuple(_as_six((*order, 4, 5)) for order in permutations(_ACTIVE))
_FULL_GROUP = (
    *_S4_SIX,
    *(_compose_six(_SINGLETON_SWAP, order) for order in _S4_SIX),
)
_GROUP_INDEX = {order: index for index, order in enumerate(_FULL_GROUP)}
_ALL_GROUP = (1 << len(_FULL_GROUP)) - 1
_IDENTITY_GROUP = 1 << _GROUP_INDEX[_IDENTITY_SIX]


def _permuted_symbol_six(symbol: int, order: _PermutationSix) -> int:
    bits = tuple(
        (symbol >> (_ARITY - endpoint - 1)) & 1 for endpoint in range(_ARITY)
    )
    result = 0
    for source in order:
        result = (result << 1) | bits[source]
    return result


def _active_bits(label: int) -> tuple[int, int, int, int]:
    values = tuple(
        (label >> (_ARITY - endpoint - 1)) & 1 for endpoint in _ACTIVE
    )
    first, second, third, fourth = values
    return first, second, third, fourth


def _active_edge(label: int) -> tuple[int, int]:
    values = tuple(
        index for index, value in enumerate(_active_bits(label)) if value
    )
    assert len(values) == _PAIR_COMPONENTS
    return values[0], values[1]


def _s4_label_orbits() -> tuple[tuple[int, ...], ...]:
    unseen = set(_RESIDUAL_LABELS)
    result: list[tuple[int, ...]] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(
            sorted({_permuted_symbol_six(seed, order) for order in _S4_SIX})
        )
        unseen -= set(orbit)
        result.append(orbit)
    return tuple(result)


def _full_label_orbits() -> tuple[tuple[int, ...], ...]:
    unseen = set(_RESIDUAL_LABELS)
    result: list[tuple[int, ...]] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(
            sorted({_permuted_symbol_six(seed, order) for order in _FULL_GROUP})
        )
        unseen -= set(orbit)
        result.append(orbit)
    return tuple(result)


def _hard_block_labels() -> tuple[int, ...]:
    edge_orbits: list[tuple[int, ...]] = []
    for orbit in _s4_label_orbits():
        if len(orbit) != len(_EDGES):
            continue
        by_edge = {_active_edge(label): label for label in orbit}
        edge_orbits.append(tuple(by_edge[edge] for edge in _EDGES))
    full_orbits = _full_label_orbits()
    hard = next(
        orbit for orbit in full_orbits if len(orbit) == _HARD_BLOCK_COMPONENTS
    )
    candidates = [orbit for orbit in edge_orbits if set(orbit) <= set(hard)]
    assert len(candidates) == _PAIR_COMPONENTS
    first, second = candidates
    if _permuted_symbol_six(first[0], _SINGLETON_SWAP) != second[0]:
        first, second = second, first
    return tuple(
        label
        for edge in range(len(_EDGES))
        for label in (first[edge], second[edge])
    )


def _block_labels() -> tuple[tuple[int, ...], ...]:
    full_orbits = _full_label_orbits()
    hard = _hard_block_labels()
    hard_set = set(hard)
    fixed = tuple(sorted(orbit[0] for orbit in full_orbits if len(orbit) == 1))
    moving = tuple(
        sorted(
            (
                orbit
                for orbit in full_orbits
                if len(orbit) > 1 and set(orbit) != hard_set
            ),
            key=lambda orbit: (-len(orbit), orbit),
        )
    )
    return hard, *moving, fixed


_BLOCK_LABELS = _block_labels()
_BLOCK_SIZES = tuple(len(block) for block in _BLOCK_LABELS)
_BLOCK_COUNT = len(_BLOCK_LABELS)


def _group_elements(group: int) -> tuple[int, ...]:
    return tuple(
        index for index in range(len(_FULL_GROUP)) if group & (1 << index)
    )


@cache
def _block_mapping(block: int, element: int) -> tuple[int, ...]:
    labels = _BLOCK_LABELS[block]
    index = {label: position for position, label in enumerate(labels)}
    return tuple(
        index[_permuted_symbol_six(label, _FULL_GROUP[element])]
        for label in labels
    )


def _apply_block(vector: _Vector, block: int, element: int) -> _Vector:
    mapping = _block_mapping(block, element)
    result = [0] * len(vector)
    for source, destination in enumerate(mapping):
        result[destination] = vector[source]
    return tuple(result)


def _stabilizer(vector: _Vector, block: int, group: int) -> int:
    result = 0
    for element in _group_elements(group):
        if _apply_block(vector, block, element) == vector:
            result |= 1 << element
    return result


def _swap_pair_components(edge_pairs: _EdgePairs) -> _EdgePairs:
    values = tuple((second, first) for first, second in edge_pairs)
    first, second, third, fourth, fifth, sixth = values
    return first, second, third, fourth, fifth, sixth


def _hard_vector(edge_pairs: _EdgePairs) -> _Vector:
    return tuple(value for pair in edge_pairs for value in pair)


@cache
def _hard_classes(total: int) -> tuple[_LocalClass, ...]:
    seen: set[int] = set()
    rows: list[tuple[int, _Vector, int]] = []
    for rank in range(_edge_class_count(total)):
        edge_pairs = _edge_unrank(total, rank)
        assert edge_pairs is not None
        swapped = _edge_rank(_swap_pair_components(edge_pairs))
        assert swapped is not None
        orbit_rank = min(rank, swapped)
        if orbit_rank in seen:
            continue
        seen.add(orbit_rank)
        representative_pairs = _edge_unrank(total, orbit_rank)
        assert representative_pairs is not None
        raw = _hard_vector(representative_pairs)
        representative = min(
            _apply_block(raw, 0, element) for element in range(len(_FULL_GROUP))
        )
        rows.append((
            orbit_rank,
            representative,
            _stabilizer(representative, 0, _ALL_GROUP),
        ))
    rows.sort(key=itemgetter(0))
    return tuple(
        (representative, stabilizer) for _, representative, stabilizer in rows
    )


@cache
def _local_classes(
    block: int, total: int, group: int
) -> tuple[_LocalClass, ...]:
    if block == 0 and group == _ALL_GROUP:
        return _hard_classes(total)
    if group == _IDENTITY_GROUP:
        return tuple(
            (vector, _IDENTITY_GROUP)
            for vector in _weak_compositions(total, _BLOCK_SIZES[block])
        )
    elements = _group_elements(group)
    result: list[_LocalClass] = []
    for vector in _weak_compositions(total, _BLOCK_SIZES[block]):
        representative = min(
            _apply_block(vector, block, element) for element in elements
        )
        if vector == representative:
            result.append((vector, _stabilizer(vector, block, group)))
    return tuple(result)


@cache
def _remaining_cycles(block: int, element: int) -> tuple[int, ...]:
    lengths: list[int] = []
    for candidate in range(block, _BLOCK_COUNT):
        mapping = _block_mapping(candidate, element)
        unseen = set(range(len(mapping)))
        while unseen:
            current = min(unseen)
            length = 0
            while current in unseen:
                unseen.remove(current)
                current = mapping[current]
                length += 1
            lengths.append(length)
    return tuple(sorted(lengths))


@cache
def _suffix_count(block: int, total: int, group: int) -> int:
    if block == _BLOCK_COUNT:
        return int(total == 0)
    elements = _group_elements(group)
    fixed = sum(
        _fixed_count_from_cycles(_remaining_cycles(block, element), total)
        for element in elements
    )
    assert fixed % len(elements) == 0
    return fixed // len(elements)


def _block_mass_count(
    block: int,
    mass: int,
    context: _MassContext,
) -> int:
    suffix_mass, group = context
    return sum(
        _suffix_count(block + 1, suffix_mass, stabilizer)
        for _, stabilizer in _local_classes(block, mass, group)
    )


def _canonicalize_block(
    blocks: list[_Vector],
    block: int,
    group: int,
) -> tuple[_Vector, int]:
    candidates = tuple(
        (_apply_block(blocks[block], block, element), element)
        for element in _group_elements(group)
    )
    representative, chosen = min(candidates)
    for index in range(block, _BLOCK_COUNT):
        blocks[index] = _apply_block(blocks[index], index, chosen)
    return representative, _stabilizer(representative, block, group)


def _rank_local_block(
    blocks: list[_Vector],
    block: int,
    context: _MassContext,
) -> tuple[int, int]:
    suffix_mass, group = context
    representative, stabilizer = _canonicalize_block(blocks, block, group)
    rank = 0
    for candidate, candidate_stabilizer in _local_classes(
        block, sum(representative), group
    ):
        if candidate == representative:
            return rank, stabilizer
        rank += _suffix_count(block + 1, suffix_mass, candidate_stabilizer)
    raise AssertionError


def _extract_blocks(vector: _ResidualVector) -> list[_Vector] | None:
    if len(vector) != _RESIDUAL_COMPONENTS or any(
        value < 0 for value in vector
    ):
        return None
    values = {
        label: vector[_RESIDUAL_INDEX[label]] for label in _RESIDUAL_LABELS
    }
    return [
        tuple(values[label] for label in labels) for labels in _BLOCK_LABELS
    ]


def _build_vector(blocks: tuple[_Vector, ...]) -> _ResidualVector:
    values: dict[int, int] = {}
    for labels, block in zip(_BLOCK_LABELS, blocks, strict=True):
        values.update(zip(labels, block, strict=True))
    assert set(values) == set(_RESIDUAL_LABELS)
    return tuple(values[label] for label in _RESIDUAL_LABELS)


def _residual_count(total: int) -> int:
    return _suffix_count(0, total, _ALL_GROUP)


def _residual_rank(vector: _ResidualVector) -> int | None:
    extracted = _extract_blocks(vector)
    if extracted is None:
        return None
    blocks = extracted
    remaining_mass = sum(vector)
    group = _ALL_GROUP
    rank = 0
    for block in range(_BLOCK_COUNT):
        mass = sum(blocks[block])
        rank += sum(
            _block_mass_count(
                block,
                candidate,
                (remaining_mass - candidate, group),
            )
            for candidate in range(mass)
        )
        local_rank, group = _rank_local_block(
            blocks,
            block,
            (remaining_mass - mass, group),
        )
        rank += local_rank
        remaining_mass -= mass
    return rank


def _unrank_local_block(
    block: int,
    mass: int,
    context: _UnrankContext,
) -> tuple[_Vector, int, int]:
    suffix_mass, group, rank = context
    for vector, stabilizer in _local_classes(block, mass, group):
        count = _suffix_count(block + 1, suffix_mass, stabilizer)
        if rank >= count:
            rank -= count
            continue
        return vector, stabilizer, rank
    raise AssertionError


def _residual_unrank(total: int, rank: int) -> _ResidualVector | None:
    if rank < 0 or rank >= _residual_count(total):
        return None
    blocks: list[_Vector] = []
    remaining_mass = total
    group = _ALL_GROUP
    for block in range(_BLOCK_COUNT):
        for mass in range(remaining_mass + 1):
            count = _block_mass_count(
                block,
                mass,
                (remaining_mass - mass, group),
            )
            if rank >= count:
                rank -= count
                continue
            vector, group, rank = _unrank_local_block(
                block,
                mass,
                (remaining_mass - mass, group, rank),
            )
            blocks.append(vector)
            remaining_mass -= mass
            break
    assert remaining_mass == 0
    assert rank == 0
    return _build_vector(tuple(blocks))


def _permute_residual(
    vector: _ResidualVector,
    order: _PermutationSix,
) -> _ResidualVector:
    result = [0] * _RESIDUAL_COMPONENTS
    for source, label in enumerate(_RESIDUAL_LABELS):
        destination = _permuted_symbol_six(label, order)
        result[_RESIDUAL_INDEX[destination]] = vector[source]
    return tuple(result)


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


def _rank(total: int, state: _State) -> int | None:
    vertices, residual = state
    vertex_mass = sum(sum(pair) for pair in vertices)
    result: int | None = None
    if vertex_mass <= total:
        try:
            vertex_rank = _vertices_of_mass(vertex_mass).index(vertices)
        except ValueError:
            vertex_rank = -1
        residual_mass = total - vertex_mass
        residual_rank = _residual_rank(residual)
        valid = (
            vertex_rank >= 0
            and residual_rank is not None
            and sum(residual) == residual_mass
        )
        if valid:
            residual_count = _residual_count(residual_mass)
            prefix = sum(
                len(_vertices_of_mass(mass)) * _residual_count(total - mass)
                for mass in range(vertex_mass)
            )
            assert residual_rank is not None
            result = prefix + vertex_rank * residual_count + residual_rank
    return result


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    for vertex_mass in range(total + 1):
        residual_mass = total - vertex_mass
        residual_count = _residual_count(residual_mass)
        block = len(_vertices_of_mass(vertex_mass)) * residual_count
        if rank >= block:
            rank -= block
            continue
        vertex_rank, residual_rank = divmod(rank, residual_count)
        residual = _residual_unrank(residual_mass, residual_rank)
        assert residual is not None
        return _vertices_of_mass(vertex_mass)[vertex_rank], residual
    raise AssertionError


def test_s6_s4s2_rank_has_exact_hard_block_geometry() -> None:
    """The labels split into one hard pair-edge block and seven easy blocks."""
    assert _BLOCK_SIZES == _EXPECTED_BLOCK_SIZES
    assert sum(_BLOCK_SIZES) == _RESIDUAL_COMPONENTS
    assert len(_FULL_GROUP) == _FULL_GROUP_ORDER


def test_s6_s4s2_rank_matches_direct_small_residual_orbits() -> None:
    """Dense ranks agree with direct 48-element orbits through mass two."""
    for total in range(3):
        observed: dict[int, set[_ResidualVector]] = {}
        for vector in _weak_compositions(total, _RESIDUAL_COMPONENTS):
            rank = _residual_rank(vector)
            assert rank is not None
            orbit = {_permute_residual(vector, order) for order in _FULL_GROUP}
            _ = observed.setdefault(rank, orbit)
            assert observed[rank] == orbit
        assert set(observed) == set(range(_residual_count(total)))


def test_s6_s4s2_rank_counts_match_reviewed_residual_sequence() -> None:
    """Burnside suffix counts reproduce all required residual counts."""
    observed = tuple(
        _residual_count(total)
        for total in range(_RESIDUAL_RANK_MAXIMUM_MASS + 1)
    )
    assert observed == _EXPECTED_RESIDUAL_COUNTS
    assert observed[-1] == _WIDTH_TWELVE_RESIDUAL


def test_s6_s4s2_residual_rank_roundtrips_through_mass_twelve() -> None:
    """Residual boundary and interior ranks roundtrip through mass 12."""
    for total in range(_RESIDUAL_RANK_MAXIMUM_MASS + 1):
        count = _residual_count(total)
        assert _residual_unrank(total, -1) is None
        assert _residual_unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            vector = _residual_unrank(total, rank)
            assert vector is not None
            assert _residual_rank(vector) == rank


def test_s6_s4s2_full_rank_exhausts_small_strata() -> None:
    """Complete (4,2) ranks form one interval through total mass six."""
    for total in range(_FULL_EXHAUSTIVE_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s4s2_full_rank_roundtrips_through_fourteen() -> None:
    """Reviewed complete counts and sampled ranks agree through mass 14."""
    observed = {
        total: _class_count(total)
        for total in range(_FULL_MAXIMUM_MASS + 1)
        if _class_count(total) != 0
    }
    assert observed == _EXPECTED_FULL_COUNTS
    for total, count in observed.items():
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
    assert observed[_FULL_MAXIMUM_MASS] == _WIDTH_FOURTEEN_FULL
