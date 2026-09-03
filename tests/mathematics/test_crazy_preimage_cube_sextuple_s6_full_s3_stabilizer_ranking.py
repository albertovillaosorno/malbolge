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
#   - Dense exact-S3 automorphism rank/unrank for the three-vertex extension
#     inside the top-level all-equal `(6)` S6 stratum through total mass 14.
# - Must-Not:
#   - Claim dense exact-transposition rank/unrank.
# - Allows:
#   - Inputs: one repeated-six vertex pair and S3-fixed residual orbit values.
#   - Outputs: dense exact-S3 residual and complete-stratum rank/unrank.
#   - Side effects: none.
# - Split-When:
#   - The exact-S4 exclusion mapping becomes independently reusable.
# - Merge-When:
#   - Exact transposition ranking directly owns this exception rank.
# - Summary:
#   - Rank the free external-S3 quotient and delete mapped exact-S4 ranks.
# - Description:
#   - Only 2,011 of 1,055,888 free mass-14 ranks are S4 extensions.
# - Usage:
#   - Constructive exception primitive for exact transposition ranking.
# - Defaults:
#   - Exhaustive small ranks and sampled ranks reach residual mass fourteen.
#

"""Dense exact-S3 rank inside the full-S6 transposition exception hierarchy."""

from __future__ import annotations

from bisect import bisect_left
from bisect import bisect_right
from collections import defaultdict
from collections import deque
from functools import cache
from itertools import permutations
from math import comb
from typing import cast

_ARITY = 6
_REPEAT_COUNT = 6
_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 7
_SAMPLE_DIVISOR = 4
_S3_ORDER = 6
_S4_ORDER = 24
_EXPECTED_BLOCK_SIZES = (4, 2, 3, 3, 3, 3, 3, 3)
_EXPECTED_BLOCK_WEIGHTS = (1, 3, 1, 1, 3, 3, 3, 3)
_EXPECTED_Q3_SUBGROUPS = 6
_EXPECTED_FREE_COUNTS = (
    0,
    0,
    1,
    10,
    56,
    234,
    816,
    2_518,
    7_076,
    18_454,
    45_309,
    105_728,
    236_141,
    507_776,
    1_055_888,
)
_EXPECTED_RESIDUAL_COUNTS = (
    0,
    0,
    1,
    10,
    54,
    228,
    799,
    2_480,
    6_996,
    18_300,
    45_035,
    105_260,
    235_357,
    506_506,
    1_053_877,
)
_EXPECTED_S4_EXCLUSIONS = (
    0,
    0,
    0,
    0,
    2,
    6,
    17,
    38,
    80,
    154,
    274,
    468,
    784,
    1_270,
    2_011,
)
_EXPECTED_COUNTS = (
    0,
    0,
    1,
    10,
    54,
    228,
    799,
    2_480,
    6_998,
    18_320,
    45_143,
    105_716,
    236_955,
    511_466,
    1_067_872,
)
_WIDTH_FOURTEEN_COUNT = _EXPECTED_COUNTS[-1]

type _Pair = tuple[int, int]
type _PermutationSix = tuple[int, int, int, int, int, int]
type _PermutationThree = tuple[int, int, int]
type _Orbit = tuple[int, ...]
type _Block = tuple[int, ...]
type _Blocks = tuple[_Block, ...]
type _OrbitValues = tuple[int, ...]
type _LocalClass = tuple[_Block, int]
type _State = tuple[_Pair, _OrbitValues]
type _MassContext = tuple[int, int]
type _UnrankContext = tuple[int, int, int]

_K3 = cast(
    "tuple[_PermutationSix, ...]",
    tuple((*order, 3, 4, 5) for order in permutations(range(3))),
)
_K4 = cast(
    "tuple[_PermutationSix, ...]",
    tuple((*order, 4, 5) for order in permutations(range(4))),
)
_S6 = cast(
    "tuple[_PermutationSix, ...]",
    tuple(permutations(range(_ARITY))),
)
_Q3 = cast("tuple[_PermutationThree, ...]", tuple(permutations(range(3))))
_Q3_INDEX = {order: index for index, order in enumerate(_Q3)}
_IDENTITY_ELEMENT = _Q3_INDEX[0, 1, 2]
_IDENTITY_GROUP = 1 << _IDENTITY_ELEMENT
_ALL_GROUP = (1 << len(_Q3)) - 1
_Q6 = cast(
    "tuple[_PermutationSix, ...]",
    tuple((0, 1, 2, *(value + 3 for value in order)) for order in _Q3),
)
_RESIDUAL_LABELS = tuple(
    symbol
    for symbol in range(1 << _ARITY)
    if symbol.bit_count() not in {1, _ARITY - 1}
)
_RESIDUAL_INDEX = {label: index for index, label in enumerate(_RESIDUAL_LABELS)}


def _permuted_symbol(symbol: int, order: _PermutationSix) -> int:
    bits = tuple(
        (symbol >> (_ARITY - endpoint - 1)) & 1 for endpoint in range(_ARITY)
    )
    result = 0
    for source in order:
        result = (result << 1) | bits[source]
    return result


def _orbits(group: tuple[_PermutationSix, ...]) -> tuple[_Orbit, ...]:
    unseen = set(_RESIDUAL_LABELS)
    result: list[_Orbit] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(
            sorted({_permuted_symbol(seed, order) for order in group})
        )
        unseen -= set(orbit)
        result.append(orbit)
    return tuple(sorted(result, key=lambda orbit: (len(orbit), orbit)))


_K3_ORBITS = _orbits(_K3)
_K3_WEIGHTS = tuple(len(orbit) for orbit in _K3_ORBITS)
_K3_INDEX = {orbit: index for index, orbit in enumerate(_K3_ORBITS)}
_K4_ORBITS = _orbits(_K4)
_K4_WEIGHTS = tuple(len(orbit) for orbit in _K4_ORBITS)
_Q_MAPS = tuple(
    tuple(
        _K3_INDEX[
            tuple(sorted(_permuted_symbol(symbol, order) for symbol in orbit))
        ]
        for orbit in _K3_ORBITS
    )
    for order in _Q6
)
_S6_LABEL_MAPS = tuple(
    tuple(
        _RESIDUAL_INDEX[_permuted_symbol(label, order)]
        for label in _RESIDUAL_LABELS
    )
    for order in _S6
)


def _q_blocks() -> tuple[tuple[int, ...], ...]:
    unseen = set(range(len(_K3_ORBITS)))
    fixed: defaultdict[int, list[int]] = defaultdict(list)
    moving: list[tuple[int, ...]] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(sorted({mapping[seed] for mapping in _Q_MAPS}))
        unseen -= set(orbit)
        if len(orbit) == 1:
            fixed[len(_K3_ORBITS[seed])].append(seed)
        else:
            moving.append(orbit)
    fixed_blocks = tuple(tuple(fixed[weight]) for weight in sorted(fixed))
    moving.sort(key=lambda block: (len(_K3_ORBITS[block[0]]), block))
    return (*fixed_blocks, *moving)


_BLOCK_LABELS = _q_blocks()
_BLOCK_SIZES = tuple(len(block) for block in _BLOCK_LABELS)
_BLOCK_WEIGHTS = tuple(len(_K3_ORBITS[block[0]]) for block in _BLOCK_LABELS)
_BLOCK_COUNT = len(_BLOCK_LABELS)


def _compose(left: int, right: int) -> int:
    return _Q3_INDEX[
        cast(
            "_PermutationThree",
            tuple(_Q3[left][_Q3[right][index]] for index in range(3)),
        )
    ]


_MULTIPLICATION = tuple(
    tuple(_compose(left, right) for right in range(len(_Q3)))
    for left in range(len(_Q3))
)


def _group_elements(group: int) -> tuple[int, ...]:
    return tuple(
        element for element in range(len(_Q3)) if group & (1 << element)
    )


@cache
def _generated(generators: tuple[int, ...]) -> int:
    subgroup = {_IDENTITY_ELEMENT}
    frontier = deque([_IDENTITY_ELEMENT])
    generators = tuple(sorted(set(generators)))
    while frontier:
        left = frontier.popleft()
        products = tuple(
            product
            for right in generators
            for product in (
                _MULTIPLICATION[left][right],
                _MULTIPLICATION[right][left],
            )
        )
        for product in products:
            if product not in subgroup:
                subgroup.add(product)
                frontier.append(product)
    return sum(1 << element for element in subgroup)


@cache
def _all_subgroups() -> tuple[int, ...]:
    known = {_IDENTITY_GROUP}
    frontier = [_IDENTITY_GROUP]
    while frontier:
        group = frontier.pop()
        for element in range(len(_Q3)):
            if group & (1 << element):
                continue
            candidate = _generated((*_group_elements(group), element))
            if candidate not in known:
                known.add(candidate)
                frontier.append(candidate)
    return tuple(sorted(known, key=lambda group: (-group.bit_count(), group)))


def _subgroups_of(group: int) -> tuple[int, ...]:
    return tuple(
        candidate for candidate in _all_subgroups() if candidate & ~group == 0
    )


@cache
def _block_mapping(block: int, element: int) -> tuple[int, ...]:
    labels = _BLOCK_LABELS[block]
    index = {label: position for position, label in enumerate(labels)}
    return tuple(index[_Q_MAPS[element][label]] for label in labels)


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


@cache
def _compositions(total: int, parts: int) -> tuple[_Block, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *suffix)
        for first in range(total + 1)
        for suffix in _compositions(total - first, parts - 1)
    )


def _stabilizer(vector: _Block, block: int, group: int) -> int:
    return sum(
        1 << element
        for element in _group_elements(group)
        if _apply_block(vector, block, element) == vector
    )


@cache
def _local_classes(
    block: int, mass: int, group: int
) -> tuple[_LocalClass, ...]:
    weight = _BLOCK_WEIGHTS[block]
    if mass % weight != 0:
        return ()
    scalar_mass = mass // weight
    if group == _IDENTITY_GROUP:
        return tuple(
            (vector, _IDENTITY_GROUP)
            for vector in _compositions(scalar_mass, _BLOCK_SIZES[block])
        )
    elements = _group_elements(group)
    result: list[_LocalClass] = []
    for vector in _compositions(scalar_mass, _BLOCK_SIZES[block]):
        representative = min(
            _apply_block(vector, block, element) for element in elements
        )
        if vector == representative:
            result.append((vector, _stabilizer(vector, block, group)))
    return tuple(result)


@cache
def _remaining_group_weights(block: int, group: int) -> tuple[int, ...]:
    elements = _group_elements(group)
    result: list[int] = []
    for candidate in range(block, _BLOCK_COUNT):
        unseen = set(range(_BLOCK_SIZES[candidate]))
        while unseen:
            seed = min(unseen)
            orbit = {
                _block_mapping(candidate, element)[seed] for element in elements
            }
            unseen -= orbit
            result.append(len(orbit) * _BLOCK_WEIGHTS[candidate])
    return tuple(sorted(result))


def _fixed_count(total: int, weights: tuple[int, ...]) -> int:
    coefficients = [1] + [0] * total
    for weight in weights:
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(0, total - degree + 1, weight):
                next_coefficients[degree + addition] += coefficient
        coefficients = next_coefficients
    return coefficients[total]


@cache
def _free_suffix_count(block: int, total: int, group: int) -> int:
    if block == _BLOCK_COUNT:
        return int(total == 0 and group == _IDENTITY_GROUP)
    exact: dict[int, int] = {}
    for subgroup in _subgroups_of(group):
        fixed = _fixed_count(total, _remaining_group_weights(block, subgroup))
        for larger, value in exact.items():
            is_larger = larger.bit_count() > subgroup.bit_count()
            is_container = subgroup & ~larger == 0
            if is_larger and is_container:
                fixed -= value
        assert fixed >= 0
        exact[subgroup] = fixed
    trivial = exact[_IDENTITY_GROUP]
    assert trivial % group.bit_count() == 0
    return trivial // group.bit_count()


def _block_mass_count(block: int, mass: int, context: _MassContext) -> int:
    suffix_mass, group = context
    if group == _IDENTITY_GROUP:
        weight = _BLOCK_WEIGHTS[block]
        if mass % weight != 0:
            return 0
        local = _composition_count(mass // weight, _BLOCK_SIZES[block])
        return local * _free_suffix_count(block + 1, suffix_mass, group)
    return sum(
        _free_suffix_count(block + 1, suffix_mass, stabilizer)
        for _, stabilizer in _local_classes(block, mass, group)
    )


def _canonicalize_block(
    blocks: list[_Block], block: int, group: int
) -> tuple[_Block, int]:
    candidates = tuple(
        (_apply_block(blocks[block], block, element), element)
        for element in _group_elements(group)
    )
    representative, chosen = min(candidates)
    for index in range(block, _BLOCK_COUNT):
        blocks[index] = _apply_block(blocks[index], index, chosen)
    return representative, _stabilizer(representative, block, group)


def _block_mass(vector: _Block, block: int) -> int:
    return sum(vector) * _BLOCK_WEIGHTS[block]


def _rank_local_block(
    blocks: list[_Block], block: int, context: _MassContext
) -> tuple[int, int] | None:
    suffix_mass, group = context
    representative, stabilizer = _canonicalize_block(blocks, block, group)
    result = 0
    for candidate, candidate_stabilizer in _local_classes(
        block, _block_mass(representative, block), group
    ):
        count = _free_suffix_count(block + 1, suffix_mass, candidate_stabilizer)
        if candidate == representative:
            return None if count == 0 else (result, stabilizer)
        result += count
    raise AssertionError


def _extract_blocks(values: _OrbitValues) -> _Blocks | None:
    if len(values) != len(_K3_ORBITS) or any(value < 0 for value in values):
        return None
    return tuple(
        tuple(values[index] for index in labels) for labels in _BLOCK_LABELS
    )


def _build_values(blocks: _Blocks) -> _OrbitValues:
    result = [0] * len(_K3_ORBITS)
    for labels, block in zip(_BLOCK_LABELS, blocks, strict=True):
        for label, value in zip(labels, block, strict=True):
            result[label] = value
    return tuple(result)


def _values_mass(values: _OrbitValues) -> int:
    return sum(
        value * weight
        for value, weight in zip(values, _K3_WEIGHTS, strict=True)
    )


def _free_count(total: int) -> int:
    if total < 0 or total > _MAXIMUM_MASS:
        return 0
    return _free_suffix_count(0, total, _ALL_GROUP)


def _free_rank_blocks(blocks: list[_Block], remaining_mass: int) -> int | None:
    group = _ALL_GROUP
    rank = 0
    for block in range(_BLOCK_COUNT):
        mass = _block_mass(blocks[block], block)
        rank += sum(
            _block_mass_count(
                block, candidate, (remaining_mass - candidate, group)
            )
            for candidate in range(mass)
        )
        local = _rank_local_block(blocks, block, (remaining_mass - mass, group))
        if local is None:
            return None
        local_rank, group = local
        rank += local_rank
        remaining_mass -= mass
    return rank if group == _IDENTITY_GROUP else None


def _free_rank(values: _OrbitValues) -> int | None:
    extracted = _extract_blocks(values)
    if extracted is None:
        return None
    remaining_mass = _values_mass(values)
    if remaining_mass > _MAXIMUM_MASS:
        return None
    return _free_rank_blocks(list(extracted), remaining_mass)


def _unrank_local_block(
    block: int, mass: int, context: _UnrankContext
) -> tuple[_Block, int, int]:
    suffix_mass, group, rank = context
    for vector, stabilizer in _local_classes(block, mass, group):
        count = _free_suffix_count(block + 1, suffix_mass, stabilizer)
        if rank >= count:
            rank -= count
            continue
        return vector, stabilizer, rank
    raise AssertionError


def _free_unrank(total: int, rank: int) -> _OrbitValues | None:
    if rank < 0 or rank >= _free_count(total):
        return None
    blocks: list[_Block] = []
    remaining_mass = total
    group = _ALL_GROUP
    for block in range(_BLOCK_COUNT):
        for mass in range(remaining_mass + 1):
            count = _block_mass_count(
                block, mass, (remaining_mass - mass, group)
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
    assert group == _IDENTITY_GROUP
    return _build_values(tuple(blocks))


@cache
def _weighted_values_from(
    weights: tuple[int, ...], index: int, total: int
) -> tuple[_OrbitValues, ...]:
    if index == len(weights):
        return ((),) if total == 0 else ()
    weight = weights[index]
    return tuple(
        (value, *suffix)
        for value in range(total // weight + 1)
        for suffix in _weighted_values_from(
            weights, index + 1, total - value * weight
        )
    )


def _residual_vector(
    values: _OrbitValues, orbits: tuple[_Orbit, ...]
) -> tuple[int, ...]:
    result = [0] * len(_RESIDUAL_LABELS)
    for orbit, value in zip(orbits, values, strict=True):
        for label in orbit:
            result[_RESIDUAL_INDEX[label]] = value
    return tuple(result)


def _stabilizer_order(values: _OrbitValues, orbits: tuple[_Orbit, ...]) -> int:
    vector = _residual_vector(values, orbits)
    return sum(
        all(
            vector[source] == vector[destination]
            for source, destination in enumerate(mapping)
        )
        for mapping in _S6_LABEL_MAPS
    )


@cache
def _exact_s4_values(total: int) -> tuple[_OrbitValues, ...]:
    return tuple(
        values
        for values in _weighted_values_from(_K4_WEIGHTS, 0, total)
        if _stabilizer_order(values, _K4_ORBITS) == _S4_ORDER
    )


def _s4_to_s3(values: _OrbitValues) -> _OrbitValues:
    by_label = {
        label: value
        for orbit, value in zip(_K4_ORBITS, values, strict=True)
        for label in orbit
    }
    return tuple(by_label[orbit[0]] for orbit in _K3_ORBITS)


@cache
def _excluded_free_ranks(total: int) -> tuple[int, ...]:
    ranks: set[int] = set()
    for values in _exact_s4_values(total):
        free_rank = _free_rank(_s4_to_s3(values))
        assert free_rank is not None
        ranks.add(free_rank)
    return tuple(sorted(ranks))


def _residual_count(total: int) -> int:
    if total < 0 or total > _MAXIMUM_MASS:
        return 0
    return _free_count(total) - len(_excluded_free_ranks(total))


def _residual_rank(values: _OrbitValues) -> int | None:
    free_rank = _free_rank(values)
    if free_rank is None:
        return None
    excluded = _excluded_free_ranks(_values_mass(values))
    if free_rank in excluded:
        return None
    return free_rank - bisect_left(excluded, free_rank)


def _free_rank_from_exact(total: int, rank: int) -> int:
    excluded = _excluded_free_ranks(total)
    free_rank = rank
    while True:
        candidate = rank + bisect_right(excluded, free_rank)
        if candidate == free_rank:
            return free_rank
        free_rank = candidate


def _residual_unrank(total: int, rank: int) -> _OrbitValues | None:
    if rank < 0 or rank >= _residual_count(total):
        return None
    free_rank = _free_rank_from_exact(total, rank)
    return _free_unrank(total, free_rank)


def _pair_rank(pair: _Pair) -> int | None:
    first, second = pair
    return None if first < 0 or second < 0 else first


def _pair_unrank(total: int, rank: int) -> _Pair | None:
    if total < 0 or rank < 0 or rank > total:
        return None
    return rank, total - rank


def _class_count(total: int) -> int:
    if total < 0 or total > _MAXIMUM_MASS:
        return 0
    return sum(
        (vertex_mass + 1) * _residual_count(total - _REPEAT_COUNT * vertex_mass)
        for vertex_mass in range(total // _REPEAT_COUNT + 1)
    )


def _rank(total: int, state: _State) -> int | None:
    vertex_pair, residual = state
    vertex_rank = _pair_rank(vertex_pair)
    residual_rank = _residual_rank(residual)
    if vertex_rank is None or residual_rank is None:
        return None
    vertex_mass = sum(vertex_pair)
    residual_mass = _values_mass(residual)
    if _REPEAT_COUNT * vertex_mass + residual_mass != total:
        return None
    prefix = sum(
        (mass + 1) * _residual_count(total - _REPEAT_COUNT * mass)
        for mass in range(vertex_mass)
    )
    return prefix + vertex_rank * _residual_count(residual_mass) + residual_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    remaining = rank
    for vertex_mass in range(total // _REPEAT_COUNT + 1):
        residual_mass = total - _REPEAT_COUNT * vertex_mass
        residual_count = _residual_count(residual_mass)
        block = (vertex_mass + 1) * residual_count
        if remaining >= block:
            remaining -= block
            continue
        vertex_rank, residual_rank = divmod(remaining, residual_count)
        vertex_pair = _pair_unrank(vertex_mass, vertex_rank)
        residual = _residual_unrank(residual_mass, residual_rank)
        assert vertex_pair is not None
        assert residual is not None
        return vertex_pair, residual
    raise AssertionError


def _sample_ranks(count: int) -> tuple[int, ...]:
    if count == 0:
        return ()
    return tuple(
        sorted({
            0,
            count // _SAMPLE_DIVISOR,
            count // 2,
            3 * count // 4,
            count - 1,
        })
    )


def test_exact_s3_free_geometry_and_counts_match_reviewed_data() -> None:
    """Weighted external-S3 free quotient matches the reviewed sequence."""
    assert _BLOCK_SIZES == _EXPECTED_BLOCK_SIZES
    assert _BLOCK_WEIGHTS == _EXPECTED_BLOCK_WEIGHTS
    assert len(_all_subgroups()) == _EXPECTED_Q3_SUBGROUPS
    observed = tuple(_free_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_FREE_COUNTS


def test_exact_s3_exclusion_map_matches_exact_s4_counts() -> None:
    """Mapped exact-S4 states occupy distinct free-S3 ranks through mass 14."""
    excluded = tuple(
        len(_excluded_free_ranks(total)) for total in range(_MAXIMUM_MASS + 1)
    )
    assert excluded == _EXPECTED_S4_EXCLUSIONS
    observed = tuple(
        _residual_count(total) for total in range(_MAXIMUM_MASS + 1)
    )
    assert observed == _EXPECTED_RESIDUAL_COUNTS


def test_exact_s3_residual_rank_exhausts_small_domains() -> None:
    """Every exact-S3 residual rank roundtrips through mass seven."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        for rank in range(_residual_count(total)):
            values = _residual_unrank(total, rank)
            assert values is not None
            assert _residual_rank(values) == rank
            assert _stabilizer_order(values, _K3_ORBITS) == _S3_ORDER


def test_exact_s3_residual_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior exact-S3 residual ranks reach mass fourteen."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _residual_count(total)
        assert _residual_unrank(total, -1) is None
        assert _residual_unrank(total, count) is None
        for rank in _sample_ranks(count):
            values = _residual_unrank(total, rank)
            assert values is not None
            assert _residual_rank(values) == rank
            assert _stabilizer_order(values, _K3_ORBITS) == _S3_ORDER


def test_exact_s3_complete_counts_match_outer_prefix() -> None:
    """Repeated-six vertex pairs lift exact S3 to 1,067,872 mass-14 classes."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COUNTS
    assert observed[-1] == _WIDTH_FOURTEEN_COUNT


def test_exact_s3_complete_rank_roundtrips_through_fourteen() -> None:
    """Boundary and interior complete exact-S3 ranks reach mass fourteen."""
    for total in range(_MAXIMUM_MASS + 1):
        count = _class_count(total)
        assert _unrank(total, -1) is None
        assert _unrank(total, count) is None
        for rank in _sample_ranks(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
