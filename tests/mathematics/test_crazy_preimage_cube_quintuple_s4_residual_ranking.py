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
#   - Dense composition of all five order-twenty-four S4 spoke strata.
# - Must-Not:
#   - Re-prove local stabilizer ranks or claim order-120/full-S5 ranking.
# - Allows:
#   - Inputs: sorted spoke multisets and their proved local edge-orbit ranks.
#   - Outputs: exact dense order-twenty-four residual rank/unrank.
#   - Side effects: none.
# - Split-When:
#   - A local spoke-stabilizer rank changes its domain contract.
# - Merge-When:
#   - Complete dense S5 ranking owns the same residual-prefix composition.
# - Summary:
#   - Prefix all sorted spoke multisets and dispatch their local dense ranks.
# - Description:
#   - Uses the identity/S2/V4/S3/S4 local quotient size for each spoke shape.
# - Usage:
#   - Completes dense order-twenty-four residual indexing through mass fourteen.
# - Defaults:
#   - Exhaustive abstract ranks stop at mass six; arithmetic reaches 14.
#

"""Dense composition of all order-twenty-four S4 residual spoke strata."""

from __future__ import annotations

from functools import cache
from itertools import permutations
from math import comb

_ACTIVE = (0, 1, 2, 3)
_EDGE_SCALARS = 12
_EXHAUSTIVE_RANK_MASS = 6
_MAXIMUM_MASS = 14
_PAIR_COMPONENTS = 2
_WIDTH_FOURTEEN_COUNT = 34_507_258
_K4_EDGES = tuple(
    (left, right)
    for left in _ACTIVE
    for right in _ACTIVE
    if left < right
)
_K4_EDGE_INDEX = {edge: index for index, edge in enumerate(_K4_EDGES)}
_S4 = tuple(permutations(_ACTIVE))

type _Pair = tuple[int, int]
type _Spokes = tuple[_Pair, _Pair, _Pair, _Pair]
type _State = tuple[_Spokes, int]


def _pair_values(maximum_mass: int) -> tuple[_Pair, ...]:
    return tuple(
        (left, right)
        for left in range(maximum_mass + 1)
        for right in range(maximum_mass - left + 1)
    )


def _spokes_from(
    maximum_mass: int,
    slots: int,
    minimum: _Pair,
) -> tuple[tuple[_Pair, ...], ...]:
    if slots == 0:
        return ((),)
    result: list[tuple[_Pair, ...]] = []
    for pair in _pair_values(maximum_mass):
        if pair < minimum:
            continue
        mass = sum(pair)
        result.extend(
            (pair, *rest)
            for rest in _spokes_from(maximum_mass - mass, slots - 1, pair)
        )
    return tuple(result)


@cache
def _spoke_sequences(maximum_mass: int) -> tuple[_Spokes, ...]:
    return tuple(
        (row[0], row[1], row[2], row[3])
        for row in _spokes_from(maximum_mass, len(_ACTIVE), (0, 0))
    )


def _spoke_mass(spokes: _Spokes) -> int:
    return sum(left + right for left, right in spokes)


def _partition(spokes: _Spokes) -> tuple[int, ...]:
    sizes: list[int] = []
    start = 0
    while start < len(_ACTIVE):
        end = start + 1
        while end < len(_ACTIVE) and spokes[end] == spokes[start]:
            end += 1
        sizes.append(end - start)
        start = end
    return tuple(sorted(sizes, reverse=True))


def _representative_labels(partition: tuple[int, ...]) -> tuple[int, ...]:
    labels: list[int] = []
    for label, size in enumerate(partition):
        labels.extend([label] * size)
    return tuple(labels)


@cache
def _stabilizer(partition: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    labels = _representative_labels(partition)
    return tuple(
        order
        for order in _S4
        if all(labels[order[index]] == labels[index] for index in _ACTIVE)
    )


def _edge_cycles(order: tuple[int, ...]) -> tuple[int, ...]:
    permutation: list[int] = []
    for left, right in _K4_EDGES:
        source = tuple(sorted((order[left], order[right])))
        permutation.append(_K4_EDGE_INDEX[source[0], source[1]])
    unseen = set(range(len(_K4_EDGES)))
    cycles: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = permutation[current]
            length += 1
        cycles.append(length)
    return tuple(sorted(cycles))


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


@cache
def _local_count(partition: tuple[int, ...], edge_mass: int) -> int:
    group = _stabilizer(partition)
    fixed_sum = sum(
        _fixed_count(tuple(sorted(_edge_cycles(order) * 2)), edge_mass)
        for order in group
    )
    return fixed_sum // len(group)


def _local_kind(partition: tuple[int, ...]) -> str:
    kinds: dict[tuple[int, ...], str] = {
        (1, 1, 1, 1): "identity",
        (2, 1, 1): "S2",
        (2, 2): "V4",
        (3, 1): "S3",
        (4,): "S4",
    }
    return kinds[partition]


def _block_size(total: int, spokes: _Spokes) -> int:
    edge_mass = total - _spoke_mass(spokes)
    return _local_count(_partition(spokes), edge_mass)


@cache
def _class_count(total: int) -> int:
    return sum(_block_size(total, spokes) for spokes in _spoke_sequences(total))


def _rank(total: int, state: _State) -> int | None:
    spokes, local_rank = state
    if spokes not in _spoke_sequences(total):
        return None
    block = _block_size(total, spokes)
    if local_rank < 0 or local_rank >= block:
        return None
    prefix = sum(
        _block_size(total, candidate)
        for candidate in _spoke_sequences(total)
        if candidate < spokes
    )
    return prefix + local_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for spokes in _spoke_sequences(total):
        block = _block_size(total, spokes)
        if remaining >= block:
            remaining -= block
            continue
        return spokes, remaining
    raise AssertionError


def _full_edge_cycles(order: tuple[int, ...]) -> tuple[int, ...]:
    full_edges = tuple(
        (left, right) for left in range(5) for right in range(left + 1, 5)
    )
    index = {edge: position for position, edge in enumerate(full_edges)}
    full_order = (*order, 4)
    permutation: list[int] = []
    for left, right in full_edges:
        source = tuple(sorted((full_order[left], full_order[right])))
        permutation.append(index[source[0], source[1]])
    unseen = set(range(len(full_edges)))
    cycles: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = permutation[current]
            length += 1
        cycles.append(length)
    return tuple(sorted(cycles))


def _burnside_count(total: int) -> int:
    fixed_sum = sum(
        _fixed_count(tuple(sorted(_full_edge_cycles(order) * 2)), total)
        for order in _S4
    )
    return fixed_sum // len(_S4)


def test_s4_residual_dispatch_covers_all_five_spoke_shapes() -> None:
    """Every Young stabilizer shape dispatches to its proved local rank kind."""
    observed = {
        _partition(spokes)
        for spokes in _spoke_sequences(_MAXIMUM_MASS)
    }
    assert observed == {
        (1, 1, 1, 1),
        (2, 1, 1),
        (2, 2),
        (3, 1),
        (4,),
    }
    assert {_local_kind(partition) for partition in observed} == {
        "identity", "S2", "V4", "S3", "S4"
    }


def test_s4_residual_rank_exhausts_small_abstract_domains() -> None:
    """Spoke prefixes plus local ranks form one contiguous residual index."""
    for total in range(_EXHAUSTIVE_RANK_MASS + 1):
        count = _class_count(total)
        for rank in range(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s4_residual_rank_matches_full_burnside_through_mass_fourteen() -> None:
    """Composed local blocks reproduce full residual S4 counts through 14."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert count == _burnside_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
    assert _class_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_COUNT


def test_distinct_spoke_local_block_is_plain_composition_domain() -> None:
    """The trivial stabilizer uses ordinary twelve-scalar edge compositions."""
    partition = (1, 1, 1, 1)
    for edge_mass in range(_MAXIMUM_MASS + 1):
        assert _local_count(partition, edge_mass) == comb(
            edge_mass + _EDGE_SCALARS - 1,
            _EDGE_SCALARS - 1,
        )
