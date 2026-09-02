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
#   - Dense rank/unrank for the (5,1)/(3,1,1) S3 second-layer S6 stratum.
# - Must-Not:
#   - Claim ranking for the other six second-layer S5 stabilizers.
# - Allows:
#   - Inputs: canonical top vertices, two fixed scalars, one repeated bundle,
#     two singleton bundles, and one fixed-edge plus three S3 edge blocks.
#   - Outputs: exact dense full-S6 rank/unrank for this second-layer stratum.
#   - Side effects: none.
# - Split-When:
#   - Another second-layer S5 stabilizer receives constructive rank/unrank.
# - Merge-When:
#   - Complete dense ranking owns the full (5,1) S6 stratum.
# - Summary:
#   - Rank triple/single/single bundles and three twelve-scalar edge blocks.
# - Description:
#   - S3 permutes repeated endpoints and their corresponding edge blocks.
# - Usage:
#   - Constructive order-six second-layer slice of the nested S5 S6 stratum.
# - Defaults:
#   - Exhaustive abstract ranks stop at mass five; arithmetic reaches fourteen.
#

"""Dense S3 second-layer ranking for the S6 (5,1) stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import combinations
from math import comb

_ARITY = 6
_FIXED_COMPONENTS = 2
_VERTEX_COMPONENTS = 2
_EDGE_FIXED_COMPONENTS = 4
_EDGE_BLOCK_COMPONENTS = 12
_BLOCK_COUNT = 3
_REPEAT_COUNT = 3
_MAXIMUM_MASS = 14
_EXHAUSTIVE_RANK_MASS = 5
_TOP_PARTITION = (5, 1)
_WIDTH_FOURTEEN_COUNT = 86_903_339_017
_WIDTH_FOURTEEN_EDGE_COUNT = 401_069_493_856
_EXPECTED_COUNTS = (
    0,
    0,
    0,
    2,
    51,
    816,
    10_539,
    115_984,
    1_108_835,
    9_334_420,
    70_042_924,
    473_845_602,
    2_920_184_587,
    16_546_299_256,
    86_903_339_017,
)
_EXPECTED_BUNDLE_COUNTS = (
    0,
    0,
    1,
    6,
    13,
    28,
    47,
    82,
    126,
    192,
    285,
    402,
    554,
    754,
    1_002,
)
_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Bundle = tuple[int, int]
type _BundleState = tuple[_Bundle, _Bundle, _Bundle]
type _Vector = tuple[int, ...]
type _Block = tuple[int, ...]
type _Blocks = tuple[_Block, _Block, _Block]
type _EdgeState = tuple[_Vector, _Blocks]
type _State = tuple[_Vertices, _Vector, _BundleState, _EdgeState]


def _composition_count(total: int, parts: int) -> int:
    if total < 0 or parts <= 0:
        return 0
    return comb(total + parts - 1, parts - 1)


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


def _bundle_candidates(total: int) -> tuple[_Bundle, ...]:
    return tuple(
        (first, mass - first)
        for mass in range(total + 1)
        for first in range(mass + 1)
    )


@cache
def _bundle_states(total: int) -> tuple[_BundleState, ...]:
    candidates = _bundle_candidates(total)
    states: list[_BundleState] = []
    for repeated in candidates:
        repeated_key = _bundle_key(repeated)
        singles = tuple(
            bundle
            for bundle in candidates
            if _bundle_key(bundle) != repeated_key
        )
        for left, right in combinations(singles, 2):
            contribution = (
                _REPEAT_COUNT * sum(repeated)
                + sum(left)
                + sum(right)
            )
            if contribution == total:
                ordered = tuple(sorted((left, right), key=_bundle_key))
                states.append((repeated, ordered[0], ordered[1]))
    return tuple(
        sorted(set(states), key=lambda state: tuple(map(_bundle_key, state)))
    )


@cache
def _bundle_rank_map(total: int) -> dict[_BundleState, int]:
    return {state: rank for rank, state in enumerate(_bundle_states(total))}


def _bundle_count(total: int) -> int:
    return len(_bundle_states(total))


def _bundle_rank(state: _BundleState) -> int | None:
    repeated, left, right = state
    ordered = tuple(sorted((left, right), key=_bundle_key))
    canonical = repeated, ordered[0], ordered[1]
    total = _REPEAT_COUNT * sum(repeated) + sum(left) + sum(right)
    return _bundle_rank_map(total).get(canonical)


def _bundle_unrank(total: int, rank: int) -> _BundleState | None:
    states = _bundle_states(total)
    return states[rank] if 0 <= rank < len(states) else None


def _block_count(total: int) -> int:
    return _composition_count(total, _EDGE_BLOCK_COMPONENTS)


def _mass_triples(total: int) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        (first, second, total - first - second)
        for first in range(total + 1)
        for second in range(first, total + 1)
        if second <= total - first - second
    )


def _multiset_count(masses: tuple[int, int, int]) -> int:
    first = _block_count(masses[0])
    second = _block_count(masses[1])
    third = _block_count(masses[2])
    result = first * second * third
    if masses[0] == masses[2]:
        result = comb(first + 2, _BLOCK_COUNT)
    elif masses[0] == masses[1]:
        result = comb(first + 1, 2) * third
    elif masses[1] == masses[2]:
        result = first * comb(second + 1, 2)
    return result


@cache
def _block_multiset_count(total: int) -> int:
    return sum(_multiset_count(masses) for masses in _mass_triples(total))


def _block_rank(block: _Block) -> int:
    rank = _composition_rank(block, _EDGE_BLOCK_COMPONENTS)
    assert rank is not None
    return rank


def _block_unrank(total: int, rank: int) -> _Block:
    block = _composition_unrank(total, _EDGE_BLOCK_COMPONENTS, rank)
    assert block is not None
    return block


def _multiset_local_rank(
    masses: tuple[int, int, int],
    ranks: tuple[int, int, int],
) -> int:
    first = _block_count(masses[0])
    second = _block_count(masses[1])
    third = _block_count(masses[2])
    result = (ranks[0] * second + ranks[1]) * third + ranks[2]
    if masses[0] == masses[2]:
        result = _rep_rank(ranks, first)
    elif masses[0] == masses[1]:
        result = _rep_rank(ranks[:2], first) * third + ranks[2]
    elif masses[1] == masses[2]:
        result = ranks[0] * comb(second + 1, 2) + _rep_rank(
            ranks[1:],
            second,
        )
    return result


def _unrank_equal_first(
    first: int,
    third: int,
    rank: int,
) -> tuple[int, int, int]:
    pair_rank, last = divmod(rank, third)
    pair = _rep_unrank(first, 2, pair_rank)
    return pair[0], pair[1], last


def _unrank_equal_last(second: int, rank: int) -> tuple[int, int, int]:
    pair_count = comb(second + 1, 2)
    head, pair_rank = divmod(rank, pair_count)
    pair = _rep_unrank(second, 2, pair_rank)
    return head, pair[0], pair[1]


def _unrank_distinct(
    second: int,
    third: int,
    rank: int,
) -> tuple[int, int, int]:
    head, tail = divmod(rank, second * third)
    middle, last = divmod(tail, third)
    return head, middle, last


def _multiset_local_unrank(
    masses: tuple[int, int, int],
    rank: int,
) -> tuple[int, int, int]:
    first = _block_count(masses[0])
    second = _block_count(masses[1])
    third = _block_count(masses[2])
    result = _unrank_distinct(second, third, rank)
    if masses[0] == masses[2]:
        values = _rep_unrank(first, _BLOCK_COUNT, rank)
        result = values[0], values[1], values[2]
    elif masses[0] == masses[1]:
        result = _unrank_equal_first(first, third, rank)
    elif masses[1] == masses[2]:
        result = _unrank_equal_last(second, rank)
    return result


def _blocks_rank(blocks: _Blocks) -> int | None:
    if any(len(block) != _EDGE_BLOCK_COMPONENTS for block in blocks):
        return None
    if any(value < 0 for block in blocks for value in block):
        return None
    ordered = sorted(blocks, key=lambda block: (sum(block), _block_rank(block)))
    masses = tuple(sum(block) for block in ordered)
    ranks = tuple(_block_rank(block) for block in ordered)
    assert len(masses) == _BLOCK_COUNT
    assert len(ranks) == _BLOCK_COUNT
    mass_key = masses[0], masses[1], masses[2]
    rank_key = ranks[0], ranks[1], ranks[2]
    total = sum(mass_key)
    prefix = sum(
        _multiset_count(candidate)
        for candidate in _mass_triples(total)
        if candidate < mass_key
    )
    return prefix + _multiset_local_rank(mass_key, rank_key)


def _blocks_unrank(total: int, rank: int) -> _Blocks | None:
    if rank < 0 or rank >= _block_multiset_count(total):
        return None
    remaining = rank
    for masses in _mass_triples(total):
        block = _multiset_count(masses)
        if remaining >= block:
            remaining -= block
            continue
        ranks = _multiset_local_unrank(masses, remaining)
        return (
            _block_unrank(masses[0], ranks[0]),
            _block_unrank(masses[1], ranks[1]),
            _block_unrank(masses[2], ranks[2]),
        )
    raise AssertionError


def _edge_count(total: int) -> int:
    return sum(
        _composition_count(fixed_mass, _EDGE_FIXED_COMPONENTS)
        * _block_multiset_count(total - fixed_mass)
        for fixed_mass in range(total + 1)
    )


def _edge_rank(state: _EdgeState) -> int | None:
    fixed, blocks = state
    fixed_rank = _composition_rank(fixed, _EDGE_FIXED_COMPONENTS)
    blocks_rank = _blocks_rank(blocks)
    if fixed_rank is None or blocks_rank is None:
        return None
    fixed_mass = sum(fixed)
    block_mass = sum(sum(block) for block in blocks)
    total = fixed_mass + block_mass
    prefix = sum(
        _composition_count(candidate, _EDGE_FIXED_COMPONENTS)
        * _block_multiset_count(total - candidate)
        for candidate in range(fixed_mass)
    )
    return prefix + fixed_rank * _block_multiset_count(block_mass) + blocks_rank


def _edge_unrank(total: int, rank: int) -> _EdgeState | None:
    if rank < 0 or rank >= _edge_count(total):
        return None
    remaining = rank
    for fixed_mass in range(total + 1):
        block_mass = total - fixed_mass
        block_count = _block_multiset_count(block_mass)
        fixed_count = _composition_count(fixed_mass, _EDGE_FIXED_COMPONENTS)
        size = fixed_count * block_count
        if remaining >= size:
            remaining -= size
            continue
        fixed_rank, blocks_rank = divmod(remaining, block_count)
        fixed = _composition_unrank(
            fixed_mass,
            _EDGE_FIXED_COMPONENTS,
            fixed_rank,
        )
        blocks = _blocks_unrank(block_mass, blocks_rank)
        assert fixed is not None
        assert blocks is not None
        return fixed, blocks
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
    transposition = _fixed_count((1,) * 16 + (2,) * 12, total)
    three_cycle = _fixed_count((1,) * 4 + (3,) * 12, total)
    return (identity + 3 * transposition + 2 * three_cycle) // 6


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


def _partition(values: tuple[_Pair, ...]) -> tuple[int, ...]:
    return tuple(sorted(Counter(values).values(), reverse=True))


@cache
def _vertices_of_mass(mass: int) -> tuple[_Vertices, ...]:
    return tuple(
        _as_vertices(values)
        for values in _vertex_sequences_from(0, _ARITY, mass)
        if sum(sum(pair) for pair in values) == mass
        and _partition(values) == _TOP_PARTITION
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
        _residual_block_count(masses)
        for masses in _residual_blocks(total)
    )


def _residual_rank(
    fixed: _Vector,
    bundles: _BundleState,
    edges: _EdgeState,
) -> int | None:
    fixed_rank = _composition_rank(fixed, _FIXED_COMPONENTS)
    bundle_rank = _bundle_rank(bundles)
    edge_rank = _edge_rank(edges)
    if fixed_rank is None or bundle_rank is None or edge_rank is None:
        return None
    bundle_mass = (
        _REPEAT_COUNT * sum(bundles[0])
        + sum(bundles[1])
        + sum(bundles[2])
    )
    edge_mass = sum(edges[0]) + sum(sum(block) for block in edges[1])
    masses = sum(fixed), bundle_mass, edge_mass
    total = sum(masses)
    prefix = sum(
        _residual_block_count(candidate)
        for candidate in _residual_blocks(total)
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
    total: int,
    rank: int,
) -> tuple[_Vector, _BundleState, _EdgeState] | None:
    if rank < 0 or rank >= _residual_count(total):
        return None
    remaining = rank
    for masses in _residual_blocks(total):
        size = _residual_block_count(masses)
        if remaining >= size:
            remaining -= size
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


def _rank_data(
    total: int,
    state: _State,
) -> tuple[int, int, int] | None:
    vertices, fixed, bundles, edges = state
    vertex_mass = sum(sum(pair) for pair in vertices)
    try:
        vertex_rank = _vertices_of_mass(vertex_mass).index(vertices)
    except ValueError:
        vertex_rank = -1
    residual_rank = _residual_rank(fixed, bundles, edges)
    residual_mass = total - vertex_mass
    valid = (
        vertex_rank >= 0
        and residual_rank is not None
        and residual_mass >= 0
        and residual_rank < _residual_count(residual_mass)
    )
    result: tuple[int, int, int] | None = None
    if valid:
        assert residual_rank is not None
        result = vertex_mass, vertex_rank, residual_rank
    return result


def _rank(total: int, state: _State) -> int | None:
    data = _rank_data(total, state)
    if data is None:
        return None
    vertex_mass, vertex_rank, residual_rank = data
    residual_mass = total - vertex_mass
    prefix = sum(
        len(_vertices_of_mass(candidate))
        * _residual_count(total - candidate)
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
        size = len(vertices) * residual_count
        if remaining >= size:
            remaining -= size
            continue
        vertex_rank, residual_rank = divmod(remaining, residual_count)
        residual = _residual_unrank(total - vertex_mass, residual_rank)
        assert residual is not None
        fixed, bundles, edges = residual
        return vertices[vertex_rank], fixed, bundles, edges
    raise AssertionError


def test_s6_s5_s3_bundle_and_edge_counts_match_factorization() -> None:
    """Bundle and S3 edge counts reproduce the independently reviewed counts."""
    observed_bundles = tuple(_bundle_count(mass) for mass in range(15))
    assert observed_bundles == _EXPECTED_BUNDLE_COUNTS
    for mass in range(_MAXIMUM_MASS + 1):
        assert _edge_count(mass) == _burnside_edge_count(mass)
    assert _edge_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_EDGE_COUNT


def test_s6_s5_s3_rank_exhausts_small_abstract_domains() -> None:
    """The nested S3 rank is contiguous through mass five."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s5_s3_rank_roundtrips_through_fourteen() -> None:
    """Counts and representative ranks reach the reviewed mass-14 boundary."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    for total, count in enumerate(observed):
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        if count == 0:
            continue
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT
