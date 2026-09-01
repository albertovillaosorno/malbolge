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
#   - Independent dense ranking evidence for endpoint-unordered S3 joint-count
#     classes.
# - Must-Not:
#   - Apply endpoint symmetry to direction-sensitive triple analyses or infer a
#     dense rank for larger endpoint groups.
# - Allows:
#   - Inputs: triple joint-count classes at ambiguity dimensions zero through
#     fourteen.
#   - Outputs: exact dense rank/unrank under the full S3 endpoint action.
#   - Side effects: none.
# - Split-When:
#   - A larger endpoint group needs a distinct orbit-ranking construction.
# - Merge-When:
#   - The unordered-triple theorem owns the same constructive quotient index.
# - Summary:
#   - Densely index unordered triple classes via three paired count slots.
# - Description:
#   - Sorts complement-paired label counts and ranks their finite multisets.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Dense arithmetic reaches dimension fourteen; raw orbits stop at four.
#

"""Dense rank/unrank evidence for S3 endpoint-unordered triple classes."""

from __future__ import annotations

from functools import cache
from itertools import combinations
from itertools import permutations
from itertools import product
from math import comb

_EXHAUSTIVE_RAW_DIMENSION = 4
_MAXIMUM_TRITS = 14
_PATTERN_COUNT = 8
_SLOT_COUNT = 3
_TRIPLE_ARITY = 3
_WIDTH_FOURTEEN_COUNT = 21_323
_ENDPOINT_PERMUTATIONS = tuple(permutations(range(_TRIPLE_ARITY)))
_SINGLETON_LABELS = (4, 2, 1)


def _permuted_symbol(symbol: int, endpoint_order: tuple[int, ...]) -> int:
    result = 0
    for source in endpoint_order:
        result = (result << 1) | ((symbol >> (_TRIPLE_ARITY - source - 1)) & 1)
    return result


def _permute_counts(
    counts: tuple[int, ...],
    endpoint_order: tuple[int, ...],
) -> tuple[int, ...]:
    result = [0] * _PATTERN_COUNT
    for symbol, count in enumerate(counts):
        result[_permuted_symbol(symbol, endpoint_order)] = count
    return tuple(result)


def _joint_counts(
    triple: tuple[int, int, int],
    dimension: int,
) -> tuple[int, ...]:
    counts = [0] * _PATTERN_COUNT
    for coordinate in range(dimension):
        symbol = 0
        for code in triple:
            symbol = (symbol << 1) | ((code >> coordinate) & 1)
        counts[symbol] += 1
    return tuple(counts)


def _paired_state(
    counts: tuple[int, ...],
) -> tuple[int, int, tuple[tuple[int, int], ...]] | None:
    if len(counts) != _PATTERN_COUNT or min(counts, default=-1) < 0:
        return None
    pairs = tuple(sorted(
        (counts[singleton], counts[(_PATTERN_COUNT - 1) ^ singleton])
        for singleton in _SINGLETON_LABELS
    ))
    return counts[0], counts[_PATTERN_COUNT - 1], pairs


def _state_dimension(
    state: tuple[int, int, tuple[tuple[int, int], ...]],
) -> int:
    fixed_zero, fixed_one, pairs = state
    return fixed_zero + fixed_one + sum(left + right for left, right in pairs)


def _counts_from_state(
    state: tuple[int, int, tuple[tuple[int, int], ...]],
) -> tuple[int, ...]:
    fixed_zero, fixed_one, pairs = state
    result = [0] * _PATTERN_COUNT
    result[0] = fixed_zero
    result[_PATTERN_COUNT - 1] = fixed_one
    for singleton, pair in zip(_SINGLETON_LABELS, pairs, strict=True):
        result[singleton] = pair[0]
        result[(_PATTERN_COUNT - 1) ^ singleton] = pair[1]
    return tuple(result)


def _pair_values(
    total: int,
    minimum: tuple[int, int],
) -> tuple[tuple[int, int], ...]:
    return tuple(
        (left, right)
        for left in range(total + 1)
        for right in range(total - left + 1)
        if (left, right) >= minimum
    )


@cache
def _pair_multiset_count(
    slots: int,
    total: int,
    minimum: tuple[int, int] = (0, 0),
) -> int:
    if slots == 0:
        return int(total == 0)
    return sum(
        _pair_multiset_count(
            slots - 1,
            total - left - right,
            (left, right),
        )
        for left, right in _pair_values(total, minimum)
    )


def _fixed_prefix(dimension: int, fixed_zero: int) -> int:
    return sum(
        _pair_multiset_count(_SLOT_COUNT, dimension - zero - one)
        for zero in range(fixed_zero)
        for one in range(dimension - zero + 1)
    )


def _fixed_one_prefix(
    dimension: int,
    fixed_zero: int,
    fixed_one: int,
) -> int:
    return sum(
        _pair_multiset_count(_SLOT_COUNT, dimension - fixed_zero - one)
        for one in range(fixed_one)
    )


def _earlier_pair_block_count(
    slots_after: int,
    remaining: int,
    *,
    minimum: tuple[int, int],
    current: tuple[int, int],
) -> int:
    return sum(
        _pair_multiset_count(
            slots_after,
            remaining - candidate[0] - candidate[1],
            candidate,
        )
        for candidate in _pair_values(remaining, minimum)
        if candidate < current
    )


def _pair_sequence_rank(
    pairs: tuple[tuple[int, int], ...],
    total: int,
) -> int | None:
    if len(pairs) != _SLOT_COUNT or tuple(sorted(pairs)) != pairs:
        return None
    rank = 0
    remaining = total
    minimum = (0, 0)
    for index, current in enumerate(pairs):
        if current not in _pair_values(remaining, minimum):
            return None
        slots_after = _SLOT_COUNT - index - 1
        rank += _earlier_pair_block_count(
            slots_after,
            remaining,
            minimum=minimum,
            current=current,
        )
        remaining -= current[0] + current[1]
        minimum = current
    return rank if remaining == 0 else None


def _pair_sequence_unrank(
    total: int,
    rank: int,
) -> tuple[tuple[int, int], ...] | None:
    count = _pair_multiset_count(_SLOT_COUNT, total)
    if rank < 0 or rank >= count:
        return None
    pairs: list[tuple[int, int]] = []
    remaining_rank = rank
    remaining = total
    minimum = (0, 0)
    for index in range(_SLOT_COUNT):
        slots_after = _SLOT_COUNT - index - 1
        for candidate in _pair_values(remaining, minimum):
            mass = candidate[0] + candidate[1]
            block = _pair_multiset_count(
                slots_after,
                remaining - mass,
                candidate,
            )
            if remaining_rank >= block:
                remaining_rank -= block
                continue
            pairs.append(candidate)
            remaining -= mass
            minimum = candidate
            break
        else:
            raise AssertionError
    assert remaining == 0
    assert remaining_rank == 0
    return tuple(pairs)


def _class_count(dimension: int) -> int:
    return sum(
        _pair_multiset_count(_SLOT_COUNT, dimension - fixed_zero - fixed_one)
        for fixed_zero in range(dimension + 1)
        for fixed_one in range(dimension - fixed_zero + 1)
    )


def _dense_rank(counts: tuple[int, ...]) -> int | None:
    state = _paired_state(counts)
    if state is None:
        return None
    fixed_zero, fixed_one, pairs = state
    dimension = _state_dimension(state)
    pair_total = dimension - fixed_zero - fixed_one
    pair_rank = _pair_sequence_rank(pairs, pair_total)
    if pair_rank is None:
        return None
    return (
        _fixed_prefix(dimension, fixed_zero)
        + _fixed_one_prefix(dimension, fixed_zero, fixed_one)
        + pair_rank
    )


def _fixed_zero_block(dimension: int, fixed_zero: int) -> int:
    return sum(
        _pair_multiset_count(
            _SLOT_COUNT,
            dimension - fixed_zero - fixed_one,
        )
        for fixed_one in range(dimension - fixed_zero + 1)
    )


def _select_fixed_zero(dimension: int, rank: int) -> tuple[int, int]:
    remaining = rank
    for fixed_zero in range(dimension + 1):
        block = _fixed_zero_block(dimension, fixed_zero)
        if remaining < block:
            return fixed_zero, remaining
        remaining -= block
    raise AssertionError


def _select_fixed_one(
    dimension: int,
    fixed_zero: int,
    rank: int,
) -> tuple[int, int]:
    remaining = rank
    for fixed_one in range(dimension - fixed_zero + 1):
        pair_total = dimension - fixed_zero - fixed_one
        row = _pair_multiset_count(_SLOT_COUNT, pair_total)
        if remaining < row:
            return fixed_one, remaining
        remaining -= row
    raise AssertionError


def _dense_unrank(dimension: int, rank: int) -> tuple[int, ...] | None:
    if rank < 0 or rank >= _class_count(dimension):
        return None
    fixed_zero, residual = _select_fixed_zero(dimension, rank)
    fixed_one, pair_rank = _select_fixed_one(dimension, fixed_zero, residual)
    pair_total = dimension - fixed_zero - fixed_one
    pairs = _pair_sequence_unrank(pair_total, pair_rank)
    assert pairs is not None
    return _counts_from_state((fixed_zero, fixed_one, pairs))


def _transposition_fixed_count(dimension: int) -> int:
    return sum(
        comb(dimension - 2 * paired_total + 3, 3) * (paired_total + 1)
        for paired_total in range(dimension // 2 + 1)
    )


def _three_cycle_fixed_count(dimension: int) -> int:
    return sum(
        (dimension - 3 * cycled_total + 1) * (cycled_total + 1)
        for cycled_total in range(dimension // 3 + 1)
    )


def _burnside_count(dimension: int) -> int:
    identity = comb(dimension + 7, 7)
    return (
        identity
        + 3 * _transposition_fixed_count(dimension)
        + 2 * _three_cycle_fixed_count(dimension)
    ) // 6


def _count_vectors(dimension: int) -> tuple[tuple[int, ...], ...]:
    vectors: list[tuple[int, ...]] = []
    for bars in combinations(range(dimension + 7), 7):
        positions = (-1, *bars, dimension + 7)
        vectors.append(tuple(
            positions[index + 1] - positions[index] - 1
            for index in range(_PATTERN_COUNT)
        ))
    return tuple(vectors)


def test_paired_state_is_complete_endpoint_orbit_invariant() -> None:
    """Small count vectors collide exactly under the full S3 endpoint action."""
    for dimension in range(_EXHAUSTIVE_RAW_DIMENSION + 1):
        observed: dict[
            tuple[int, int, tuple[tuple[int, int], ...]],
            set[tuple[int, ...]],
        ] = {}
        for counts in _count_vectors(dimension):
            state = _paired_state(counts)
            assert state is not None
            orbit = {
                _permute_counts(counts, order)
                for order in _ENDPOINT_PERMUTATIONS
            }
            if state not in observed:
                observed[state] = orbit
            assert observed[state] == orbit
        assert len(observed) == _burnside_count(dimension)


def test_dense_rank_exhausts_every_class_through_dimension_fourteen() -> None:
    """Every checked S3 quotient class receives one contiguous integer rank."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        count = _class_count(dimension)
        assert count == _burnside_count(dimension)
        observed: set[int] = set()
        for rank in range(count):
            counts = _dense_unrank(dimension, rank)
            assert counts is not None
            assert sum(counts) == dimension
            assert _dense_rank(counts) == rank
            observed.add(rank)
        assert observed == set(range(count))
    assert _class_count(_MAXIMUM_TRITS) == _WIDTH_FOURTEEN_COUNT


def test_dense_rank_is_endpoint_invariant_on_small_raw_triples() -> None:
    """Endpoint permutations of raw triples receive the same dense rank."""
    for dimension in range(_EXHAUSTIVE_RAW_DIMENSION + 1):
        size = 1 << dimension
        for triple in product(range(size), repeat=_TRIPLE_ARITY):
            counts = _joint_counts(
                (triple[0], triple[1], triple[2]),
                dimension,
            )
            rank = _dense_rank(counts)
            assert rank is not None
            for order in _ENDPOINT_PERMUTATIONS:
                permuted = (
                    triple[order[0]],
                    triple[order[1]],
                    triple[order[2]],
                )
                assert _dense_rank(_joint_counts(permuted, dimension)) == rank


def test_dense_rank_rejects_out_of_range_unrank_requests() -> None:
    """Unranking fails closed outside each exact S3 quotient range."""
    for dimension in range(_MAXIMUM_TRITS + 1):
        count = _class_count(dimension)
        assert _dense_unrank(dimension, -1) is None
        assert _dense_unrank(dimension, count) is None
