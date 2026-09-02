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
#   - Dense rank/unrank for the S6 top-level vertex partition (2,2,2).
# - Must-Not:
#   - Claim ranking for another S6 Young stabilizer.
# - Allows:
#   - Inputs: sorted (2,2,2) vertex pairs and 52 residual scalar counts.
#   - Outputs: dense full-stratum rank under the residual S2-cubed action.
#   - Side effects: none.
# - Split-When:
#   - The generic invariant-block stabilizer-chain rank is reused elsewhere.
# - Merge-When:
#   - Complete dense S6 ranking owns all top-level Young strata.
# - Summary:
#   - Rank fourteen invariant residual blocks through an eight-element chain.
# - Description:
#   - Canonical block orbits update the remaining subgroup and suffix counts.
# - Usage:
#   - Completes the 13,145,545,602-class mass-fourteen (2,2,2) stratum.
# - Defaults:
#   - Direct residual orbit exhaustion stops at mass two; ranks reach fourteen.
#

"""Dense stabilizer-chain rank for the S6 (2,2,2) Young stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from math import comb

_ARITY = 6
_MAXIMUM_MASS = 14
_EXHAUSTIVE_RESIDUAL_MASS = 2
_EXHAUSTIVE_TOTAL_MASS = 6
_VERTEX_PARTITION = (2, 2, 2)
_RESIDUAL_COMPONENTS = 52
_WIDTH_FOURTEEN_RESIDUAL = 7_636_686_343_840
_WIDTH_FOURTEEN_COUNT = 13_145_545_602
_EXPECTED_RESIDUAL_COUNTS = (
    1,
    21,
    334,
    4_465,
    52_175,
    534_922,
    4_842_436,
    39_059_786,
    283_694_647,
    1_874_510_905,
    11_373_892_862,
    63_900_207_037,
    334_802_577_049,
    1_646_166_960_848,
    7_636_686_343_840,
)
_EXPECTED_COUNTS = {
    4: 1,
    5: 21,
    6: 340,
    7: 4_591,
    8: 54_193,
    9: 562_006,
    10: 5_160_194,
    11: 42_332_500,
    12: 313_490_464,
    13: 2_116_502_732,
    14: 13_145_545_602,
}

_IDENTITY = (0, 1, 2, 3, 4, 5)
_A = (1, 0, 2, 3, 4, 5)
_B = (0, 1, 3, 2, 4, 5)
_C = (0, 1, 2, 3, 5, 4)

type _Pair = tuple[int, int]
type _Vertices = tuple[_Pair, _Pair, _Pair, _Pair, _Pair, _Pair]
type _Vector = tuple[int, ...]
type _Permutation = tuple[int, int, int, int, int, int]
type _Block = tuple[int, ...]
type _Blocks = tuple[_Block, ...]
type _LocalClass = tuple[_Block, int]
type _State = tuple[_Vertices, _Vector]
type _MassContext = tuple[int, int]
type _UnrankContext = tuple[int, int, int]


def _compose(left: _Permutation, right: _Permutation) -> _Permutation:
    values = tuple(left[right[index]] for index in range(_ARITY))
    first, second, third, fourth, fifth, sixth = values
    return first, second, third, fourth, fifth, sixth


_AB = _compose(_A, _B)
_AC = _compose(_A, _C)
_BC = _compose(_B, _C)
_ABC = _compose(_AB, _C)
_E8 = (_IDENTITY, _A, _B, _AB, _C, _AC, _BC, _ABC)
_IDENTITY_GROUP = 1
_ALL_GROUP = (1 << len(_E8)) - 1
_RESIDUAL_LABELS = tuple(
    symbol
    for symbol in range(1 << _ARITY)
    if symbol.bit_count() not in {1, _ARITY - 1}
)
_LABEL_INDEX = {label: index for index, label in enumerate(_RESIDUAL_LABELS)}
_PAIR_VALUES = tuple(
    (first, second)
    for first in range(_MAXIMUM_MASS + 1)
    for second in range(_MAXIMUM_MASS - first + 1)
)


def _permuted_symbol(symbol: int, order: _Permutation) -> int:
    bits = tuple(
        (symbol >> (_ARITY - endpoint - 1)) & 1 for endpoint in range(_ARITY)
    )
    result = 0
    for source in order:
        result = (result << 1) | bits[source]
    return result


def _label_orbits() -> tuple[tuple[int, ...], ...]:
    unseen = set(_RESIDUAL_LABELS)
    result: list[tuple[int, ...]] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(sorted({_permuted_symbol(seed, order) for order in _E8}))
        unseen -= set(orbit)
        result.append(orbit)
    return tuple(sorted(result, key=lambda orbit: (len(orbit), orbit)))


_LABEL_ORBITS = _label_orbits()
_FIXED_LABELS = tuple(orbit[0] for orbit in _LABEL_ORBITS if len(orbit) == 1)
_MOVING_LABELS = tuple(orbit for orbit in _LABEL_ORBITS if len(orbit) > 1)
_BLOCK_LABELS = (_FIXED_LABELS, *_MOVING_LABELS)
_BLOCK_SIZES = tuple(len(block) for block in _BLOCK_LABELS)
_BLOCK_COUNT = len(_BLOCK_LABELS)


def _group_elements(group: int) -> tuple[int, ...]:
    return tuple(index for index in range(len(_E8)) if group & (1 << index))


@cache
def _block_mapping(block: int, element: int) -> tuple[int, ...]:
    labels = _BLOCK_LABELS[block]
    if block == 0:
        return tuple(range(len(labels)))
    index = {label: position for position, label in enumerate(labels)}
    return tuple(
        index[_permuted_symbol(label, _E8[element])] for label in labels
    )


def _apply_block(vector: _Block, block: int, element: int) -> _Block:
    mapping = _block_mapping(block, element)
    result = [0] * len(vector)
    for source, destination in enumerate(mapping):
        result[destination] = vector[source]
    return tuple(result)


def _composition_count(total: int, parts: int) -> int:
    if total < 0 or parts <= 0:
        return 0
    return comb(total + parts - 1, parts - 1)


def _composition_rank(vector: _Block) -> int | None:
    if not vector or any(value < 0 for value in vector):
        return None
    remaining = sum(vector)
    rank = 0
    for index, value in enumerate(vector[:-1]):
        tail = len(vector) - index - 1
        rank += sum(
            _composition_count(remaining - earlier, tail)
            for earlier in range(value)
        )
        remaining -= value
    return rank


def _composition_unrank(total: int, parts: int, rank: int) -> _Block | None:
    if rank < 0 or rank >= _composition_count(total, parts):
        return None
    remaining_total = total
    remaining_rank = rank
    result: list[int] = []
    for index in range(parts - 1):
        tail = parts - index - 1
        for value in range(remaining_total + 1):
            block = _composition_count(remaining_total - value, tail)
            if remaining_rank >= block:
                remaining_rank -= block
                continue
            result.append(value)
            remaining_total -= value
            break
    result.append(remaining_total)
    return tuple(result)


def _compositions(total: int, parts: int) -> tuple[_Block, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *suffix)
        for first in range(total + 1)
        for suffix in _compositions(total - first, parts - 1)
    )


def _stabilizer(vector: _Block, block: int, group: int) -> int:
    result = 0
    for element in _group_elements(group):
        if _apply_block(vector, block, element) == vector:
            result |= 1 << element
    return result


@cache
def _local_classes(
    block: int, total: int, group: int
) -> tuple[_LocalClass, ...]:
    if group == _IDENTITY_GROUP:
        return tuple(
            (vector, _IDENTITY_GROUP)
            for vector in _compositions(total, _BLOCK_SIZES[block])
        )
    result: list[_LocalClass] = []
    elements = _group_elements(group)
    for vector in _compositions(total, _BLOCK_SIZES[block]):
        representative = min(
            _apply_block(vector, block, item) for item in elements
        )
        if vector == representative:
            result.append((vector, _stabilizer(vector, block, group)))
    return tuple(result)


def _remaining_components(block: int) -> int:
    return sum(_BLOCK_SIZES[block:])


@cache
def _suffix_count(block: int, total: int, group: int) -> int:
    result: int
    if block == _BLOCK_COUNT:
        result = int(total == 0)
    elif group == _IDENTITY_GROUP:
        result = _composition_count(total, _remaining_components(block))
    elif block == _BLOCK_COUNT - 1:
        result = len(_local_classes(block, total, group))
    else:
        result = sum(
            _block_mass_count(block, mass, (total - mass, group))
            for mass in range(total + 1)
        )
    return result


def _block_mass_count(
    block: int,
    mass: int,
    context: _MassContext,
) -> int:
    suffix_mass, group = context
    if block == 0 or group == _IDENTITY_GROUP:
        local = _composition_count(mass, _BLOCK_SIZES[block])
        return local * _suffix_count(block + 1, suffix_mass, group)
    return sum(
        _suffix_count(block + 1, suffix_mass, stabilizer)
        for _, stabilizer in _local_classes(block, mass, group)
    )


def _canonicalize_block(
    blocks: list[_Block],
    block: int,
    group: int,
) -> tuple[_Block, int]:
    candidates = tuple(
        (_apply_block(blocks[block], block, element), element)
        for element in _group_elements(group)
    )
    representative, chosen = min(candidates)
    for index in range(block, _BLOCK_COUNT):
        blocks[index] = _apply_block(blocks[index], index, chosen)
    return representative, _stabilizer(representative, block, group)


def _extract_blocks(vector: _Vector) -> _Blocks | None:
    if len(vector) != _RESIDUAL_COMPONENTS or any(
        value < 0 for value in vector
    ):
        return None
    values = {label: vector[_LABEL_INDEX[label]] for label in _RESIDUAL_LABELS}
    return tuple(
        tuple(values[label] for label in labels) for labels in _BLOCK_LABELS
    )


def _build_vector(blocks: _Blocks) -> _Vector:
    values: dict[int, int] = {}
    for labels, block in zip(_BLOCK_LABELS, blocks, strict=True):
        values.update(zip(labels, block, strict=True))
    assert set(values) == set(_RESIDUAL_LABELS)
    return tuple(values[label] for label in _RESIDUAL_LABELS)


def _rank_local_block(
    blocks: list[_Block],
    block: int,
    context: _MassContext,
) -> tuple[int, int]:
    suffix_mass, group = context
    vector = blocks[block]
    if block == 0 or group == _IDENTITY_GROUP:
        local_rank = _composition_rank(vector)
        assert local_rank is not None
        suffix = _suffix_count(block + 1, suffix_mass, group)
        return local_rank * suffix, group
    representative, stabilizer = _canonicalize_block(blocks, block, group)
    result = 0
    for candidate, candidate_stabilizer in _local_classes(
        block,
        sum(representative),
        group,
    ):
        if candidate == representative:
            return result, stabilizer
        result += _suffix_count(block + 1, suffix_mass, candidate_stabilizer)
    raise AssertionError


def _residual_count(total: int) -> int:
    return _suffix_count(0, total, _ALL_GROUP)


def _residual_rank(vector: _Vector) -> int | None:
    extracted = _extract_blocks(vector)
    if extracted is None:
        return None
    blocks = list(extracted)
    remaining_mass = sum(vector)
    group = _ALL_GROUP
    rank = 0
    for block in range(_BLOCK_COUNT):
        mass = sum(blocks[block])
        rank += sum(
            _block_mass_count(
                block, candidate, (remaining_mass - candidate, group)
            )
            for candidate in range(mass)
        )
        local, group = _rank_local_block(
            blocks,
            block,
            (remaining_mass - mass, group),
        )
        rank += local
        remaining_mass -= mass
    return rank


def _unrank_local_block(
    block: int,
    mass: int,
    context: _UnrankContext,
) -> tuple[_Block, int, int]:
    suffix_mass, group, rank = context
    if block == 0 or group == _IDENTITY_GROUP:
        suffix = _suffix_count(block + 1, suffix_mass, group)
        local_rank, residual = divmod(rank, suffix)
        vector = _composition_unrank(mass, _BLOCK_SIZES[block], local_rank)
        assert vector is not None
        return vector, group, residual
    for vector, stabilizer in _local_classes(block, mass, group):
        count = _suffix_count(block + 1, suffix_mass, stabilizer)
        if rank >= count:
            rank -= count
            continue
        return vector, stabilizer, rank
    raise AssertionError


def _residual_unrank(total: int, rank: int) -> _Vector | None:
    if rank < 0 or rank >= _residual_count(total):
        return None
    blocks: list[_Block] = []
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


def _permute_vector(vector: _Vector, order: _Permutation) -> _Vector:
    result = [0] * _RESIDUAL_COMPONENTS
    for source, label in enumerate(_RESIDUAL_LABELS):
        destination = _permuted_symbol(label, order)
        result[_LABEL_INDEX[destination]] = vector[source]
    return tuple(result)


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    return _compositions(total, parts)


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
        residual_rank = _residual_rank(residual)
        residual_mass = total - vertex_mass
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


def test_s6_s2_cubed_label_blocks_have_exact_orbit_geometry() -> None:
    """Residual labels have the reviewed fixed/pair/quad/octet geometry."""
    assert (8, *(2,) * 6, *(4,) * 6, 8) == _BLOCK_SIZES
    assert sum(_BLOCK_SIZES) == _RESIDUAL_COMPONENTS


def test_s6_s2_cubed_residual_rank_matches_direct_small_orbits() -> None:
    """Dense residual ranks agree with direct E8 orbits through mass two."""
    for total in range(_EXHAUSTIVE_RESIDUAL_MASS + 1):
        observed: set[int] = set()
        for vector in _weak_compositions(total, _RESIDUAL_COMPONENTS):
            rank = _residual_rank(vector)
            assert rank is not None
            observed.add(rank)
            for order in _E8:
                assert _residual_rank(_permute_vector(vector, order)) == rank
        assert observed == set(range(_residual_count(total)))


def test_s6_s2_cubed_residual_counts_match_burnside_sequence() -> None:
    """Stabilizer-chain suffix counts reproduce the exact E8 sequence."""
    observed = tuple(
        _residual_count(total) for total in range(_MAXIMUM_MASS + 1)
    )
    assert observed == _EXPECTED_RESIDUAL_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_RESIDUAL


def test_s6_s2_cubed_rank_exhausts_small_full_strata() -> None:
    """Complete (2,2,2) ranks form one interval through total mass six."""
    for total in range(_EXHAUSTIVE_TOTAL_MASS + 1):
        for rank in range(_class_count(total)):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank


def test_s6_s2_cubed_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior (2,2,2) ranks roundtrip through mass fourteen."""
    observed = {
        total: _class_count(total)
        for total in range(_MAXIMUM_MASS + 1)
        if _class_count(total) != 0
    }
    assert observed == _EXPECTED_COUNTS
    for total, count in observed.items():
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in {0, count // 4, count // 2, (3 * count) // 4, count - 1}:
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
    assert observed[_MAXIMUM_MASS] == _WIDTH_FOURTEEN_COUNT
