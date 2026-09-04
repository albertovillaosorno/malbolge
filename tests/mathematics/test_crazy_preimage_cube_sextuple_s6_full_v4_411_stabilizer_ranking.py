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
#   - Dense normalizer-free and exact rank/unrank for the V4-(4,1,1)
#     stabilizer in the top-level all-equal S6 residual stratum.
# - Must-Not:
#   - Claim dense rank for another exact full-S6 stabilizer type.
# - Allows:
#   - Inputs: H-fixed residual assignments for the V4-(4,1,1) subgroup.
#   - Outputs: free N(H)/H ranks, exact-H ranks, and complete outer ranks.
#   - Side effects: none.
# - Split-When:
#   - Another exact V4 action needs the same quotient primitive.
# - Merge-When:
#   - Complete dense full-S6 ranking owns every exact stabilizer stratum.
# - Summary:
#   - Rank the order-twelve normalizer quotient with no external exceptions.
# - Description:
#   - Normalizer-free already means exact-H for this subgroup.
# - Usage:
#   - Constructive rank for the exact V4 endpoint-orbit-(4,1,1) type.
# - Defaults:
#   - Exact residual and complete rank/unrank reach total mass fourteen.
#

"""Dense exact rank for the full-S6 V4-(4,1,1) stabilizer."""

from __future__ import annotations

from collections import deque
from functools import cache
from itertools import permutations
from typing import cast

_ARITY = 6
_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 5
_H_ORDER = 4
_NORMALIZER_ORDER = 48
_QUOTIENT_ORDER = 12
_EXPECTED_QUOTIENT_SUBGROUPS = 16
_EXPECTED_H_GENERATORS = 2
_EXPECTED_VERTEX_ORBITS = (4, 1, 1)
_EXPECTED_H_ORBIT_SIZES = {1: 4, 2: 12, 4: 6}
_EXPECTED_BLOCK_SIZES = (4, 2, 6, 3, 3, 2, 2)
_EXPECTED_BLOCK_WEIGHTS = (1, 4, 2, 2, 2, 4, 4)
_EXPECTED_FREE_COUNTS = (
    0,
    0,
    0,
    0,
    2,
    8,
    37,
    108,
    334,
    828,
    2_109,
    4_696,
    10_557,
    21_660,
    44_590,
)
_EXPECTED_EXACT_COUNTS = _EXPECTED_FREE_COUNTS
_EXPECTED_COMPLETE_COUNTS = (
    0,
    0,
    0,
    0,
    2,
    8,
    37,
    108,
    334,
    828,
    2_113,
    4_712,
    10_631,
    21_876,
    45_258,
)


type _Permutation = tuple[int, int, int, int, int, int]
type _Group = frozenset[_Permutation]
type _Orbit = tuple[int, ...]
type _Block = tuple[int, ...]
type _Vector = tuple[int, ...]
type _LocalClass = tuple[_Block, int]
type _Pair = tuple[int, int]
type _State = tuple[_Pair, _Vector]
type _MassContext = tuple[int, int]
type _RankContext = tuple[int, int, int]
type _UnrankContext = tuple[int, int, int]

_IDENTITY: _Permutation = (0, 1, 2, 3, 4, 5)
_FIRST_GENERATOR: _Permutation = (0, 1, 3, 2, 5, 4)
_SECOND_GENERATOR: _Permutation = (0, 1, 4, 5, 2, 3)
_H_GENERATORS = (_FIRST_GENERATOR, _SECOND_GENERATOR)
_S6 = cast("tuple[_Permutation, ...]", tuple(permutations(range(_ARITY))))
_RESIDUAL_LABELS = tuple(
    symbol
    for symbol in range(1 << _ARITY)
    if symbol.bit_count() not in {1, _ARITY - 1}
)
_RESIDUAL_INDEX = {label: index for index, label in enumerate(_RESIDUAL_LABELS)}


def _compose(left: _Permutation, right: _Permutation) -> _Permutation:
    return cast(
        "_Permutation",
        tuple(left[right[index]] for index in range(_ARITY)),
    )


def _inverse(order: _Permutation) -> _Permutation:
    result = [0] * _ARITY
    for source, target in enumerate(order):
        result[target] = source
    return cast("_Permutation", tuple(result))


def _products(
    left: _Permutation, generators: tuple[_Permutation, ...]
) -> tuple[_Permutation, ...]:
    return tuple(
        product
        for right in generators
        for product in (_compose(left, right), _compose(right, left))
    )


@cache
def _generated(generators: tuple[_Permutation, ...]) -> _Group:
    generators = tuple(sorted(set(generators)))
    subgroup = {_IDENTITY}
    frontier = deque([_IDENTITY])
    while frontier:
        left = frontier.popleft()
        for product in _products(left, generators):
            if product not in subgroup:
                subgroup.add(product)
                frontier.append(product)
    return frozenset(subgroup)


_H: _Group = _generated(_H_GENERATORS)


def _minimal_generators(group: _Group) -> tuple[_Permutation, ...]:
    generators: list[_Permutation] = []
    generated = frozenset({_IDENTITY})
    for element in sorted(group):
        if element in generated:
            continue
        generators.append(element)
        generated = _generated(tuple(generators))
        if generated == group:
            break
    return tuple(generators)


def _conjugate(element: _Permutation, by: _Permutation) -> _Permutation:
    return _compose(_compose(by, element), _inverse(by))


def _conjugate_group(group: _Group, by: _Permutation) -> _Group:
    return frozenset(_conjugate(element, by) for element in group)


_NORMALIZER = tuple(
    element for element in _S6 if _conjugate_group(_H, element) == _H
)


def _permuted_symbol(symbol: int, order: _Permutation) -> int:
    bits = tuple(
        (symbol >> (_ARITY - endpoint - 1)) & 1 for endpoint in range(_ARITY)
    )
    result = 0
    for source in order:
        result = (result << 1) | bits[source]
    return result


@cache
def _residual_orbits(group: _Group) -> tuple[_Orbit, ...]:
    unseen = set(_RESIDUAL_LABELS)
    result: list[_Orbit] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(sorted({_permuted_symbol(seed, item) for item in group}))
        unseen -= set(orbit)
        result.append(orbit)
    return tuple(sorted(result, key=lambda orbit: (len(orbit), orbit)))


def _vertex_orbit_sizes(group: _Group) -> tuple[int, ...]:
    unseen = set(range(_ARITY))
    sizes: list[int] = []
    while unseen:
        seed = min(unseen)
        orbit = {order[seed] for order in group}
        unseen -= orbit
        sizes.append(len(orbit))
    return tuple(sorted(sizes, reverse=True))


_H_ORBITS = _residual_orbits(_H)
_H_ORBIT_INDEX = {orbit: index for index, orbit in enumerate(_H_ORBITS)}


def _image_h_orbit(orbit: _Orbit, order: _Permutation) -> _Orbit:
    return tuple(sorted(_permuted_symbol(symbol, order) for symbol in orbit))


_ACTIONS = tuple(
    sorted({
        tuple(
            _H_ORBIT_INDEX[_image_h_orbit(orbit, order)] for orbit in _H_ORBITS
        )
        for order in _NORMALIZER
    })
)
_ACTION_INDEX = {action: index for index, action in enumerate(_ACTIONS)}
_IDENTITY_ACTION = _ACTION_INDEX[tuple(range(len(_H_ORBITS)))]
_IDENTITY_GROUP = 1 << _IDENTITY_ACTION
_ALL_GROUP = (1 << len(_ACTIONS)) - 1


def _compose_action(left: int, right: int) -> int:
    return _ACTION_INDEX[
        tuple(
            _ACTIONS[left][_ACTIONS[right][index]]
            for index in range(len(_H_ORBITS))
        )
    ]


_MULTIPLICATION = tuple(
    tuple(_compose_action(left, right) for right in range(len(_ACTIONS)))
    for left in range(len(_ACTIONS))
)


def _group_elements(group: int) -> tuple[int, ...]:
    return tuple(
        element for element in range(len(_ACTIONS)) if group & (1 << element)
    )


def _q_products(left: int, generators: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(
        product
        for right in generators
        for product in (
            _MULTIPLICATION[left][right],
            _MULTIPLICATION[right][left],
        )
    )


@cache
def _generated_q(generators: tuple[int, ...]) -> int:
    subgroup = {_IDENTITY_ACTION}
    frontier = deque([_IDENTITY_ACTION])
    generators = tuple(sorted(set(generators)))
    while frontier:
        left = frontier.popleft()
        for product in _q_products(left, generators):
            if product not in subgroup:
                subgroup.add(product)
                frontier.append(product)
    return sum(1 << element for element in subgroup)


def _minimal_q_generators(group: int) -> tuple[int, ...]:
    generators: list[int] = []
    generated = _IDENTITY_GROUP
    for element in _group_elements(group):
        if generated & (1 << element):
            continue
        generators.append(element)
        generated = _generated_q(tuple(generators))
    return tuple(generators)


@cache
def _all_q_subgroups() -> tuple[int, ...]:
    known = {_IDENTITY_GROUP}
    frontier = [_IDENTITY_GROUP]
    while frontier:
        group = frontier.pop()
        generators = _minimal_q_generators(group)
        for element in range(len(_ACTIONS)):
            if group & (1 << element):
                continue
            candidate = _generated_q((*generators, element))
            if candidate not in known:
                known.add(candidate)
                frontier.append(candidate)
    return tuple(sorted(known, key=lambda group: (-group.bit_count(), group)))


def _subgroups_of(group: int) -> tuple[int, ...]:
    return tuple(
        candidate for candidate in _all_q_subgroups() if candidate & ~group == 0
    )


def _q_blocks() -> tuple[tuple[int, ...], ...]:
    unseen = set(range(len(_H_ORBITS)))
    fixed: dict[int, list[int]] = {}
    moving: list[tuple[int, ...]] = []
    while unseen:
        seed = min(unseen)
        orbit = tuple(sorted({action[seed] for action in _ACTIONS}))
        unseen -= set(orbit)
        weight = len(_H_ORBITS[seed])
        if len(orbit) == 1:
            fixed.setdefault(weight, []).append(seed)
        else:
            moving.append(orbit)
    fixed_blocks = [tuple(values) for _, values in sorted(fixed.items())]
    moving.sort(
        key=lambda block: (-len(block), len(_H_ORBITS[block[0]]), block)
    )
    return (*fixed_blocks, *moving)


_BLOCK_LABELS = _q_blocks()
_BLOCK_SIZES = tuple(len(block) for block in _BLOCK_LABELS)
_BLOCK_WEIGHTS = tuple(len(_H_ORBITS[block[0]]) for block in _BLOCK_LABELS)
_BLOCK_COUNT = len(_BLOCK_LABELS)


@cache
def _block_mapping(block: int, element: int) -> tuple[int, ...]:
    labels = _BLOCK_LABELS[block]
    index = {label: position for position, label in enumerate(labels)}
    return tuple(index[_ACTIONS[element][label]] for label in labels)


def _apply_block(vector: _Block, block: int, element: int) -> _Block:
    mapping = _block_mapping(block, element)
    result = [0] * len(vector)
    for source, destination in enumerate(mapping):
        result[destination] = vector[source]
    return tuple(result)


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


@cache
def _free_suffix_count(block: int, total: int, group: int) -> int:
    if block == _BLOCK_COUNT:
        return int(total == 0 and group == _IDENTITY_GROUP)
    exact: dict[int, int] = {}
    for subgroup in _subgroups_of(group):
        fixed = _fixed_count(total, _remaining_group_weights(block, subgroup))
        for larger, value in exact.items():
            if (
                larger.bit_count() > subgroup.bit_count()
                and subgroup & ~larger == 0
            ):
                fixed -= value
        assert fixed >= 0
        exact[subgroup] = fixed
    trivial_assignments = exact[_IDENTITY_GROUP]
    assert trivial_assignments % group.bit_count() == 0
    return trivial_assignments // group.bit_count()


def _block_mass(vector: _Block, block: int) -> int:
    return sum(vector) * _BLOCK_WEIGHTS[block]


def _block_mass_count(block: int, mass: int, context: _MassContext) -> int:
    suffix_mass, group = context
    return sum(
        _free_suffix_count(block + 1, suffix_mass, stabilizer)
        for _, stabilizer in _local_classes(block, mass, group)
    )


def _canonicalize_block(
    blocks: list[_Block], block: int, group: int
) -> tuple[_Block, int]:
    representative, chosen = min(
        (_apply_block(blocks[block], block, element), element)
        for element in _group_elements(group)
    )
    for index in range(block, _BLOCK_COUNT):
        blocks[index] = _apply_block(blocks[index], index, chosen)
    return representative, _stabilizer(representative, block, group)


def _extract_blocks(vector: _Vector) -> list[_Block] | None:
    if len(vector) != len(_H_ORBITS) or any(value < 0 for value in vector):
        return None
    return [
        tuple(vector[index] for index in labels) for labels in _BLOCK_LABELS
    ]


def _build_vector(blocks: tuple[_Block, ...]) -> _Vector:
    result = [0] * len(_H_ORBITS)
    for labels, block in zip(_BLOCK_LABELS, blocks, strict=True):
        for label, value in zip(labels, block, strict=True):
            result[label] = value
    return tuple(result)


def _vector_mass(vector: _Vector) -> int:
    return sum(
        value * len(orbit)
        for value, orbit in zip(vector, _H_ORBITS, strict=True)
    )


def _free_count(total: int) -> int:
    return _free_suffix_count(0, total, _ALL_GROUP)


def _free_rank_step(
    blocks: list[_Block], block: int, context: _RankContext
) -> tuple[int, int, int] | None:
    remaining_mass, group, rank = context
    mass = _block_mass(blocks[block], block)
    rank += sum(
        _block_mass_count(block, candidate, (remaining_mass - candidate, group))
        for candidate in range(mass)
    )
    representative, stabilizer = _canonicalize_block(blocks, block, group)
    for candidate, candidate_stabilizer in _local_classes(block, mass, group):
        count = _free_suffix_count(
            block + 1, remaining_mass - mass, candidate_stabilizer
        )
        if candidate != representative:
            rank += count
            continue
        if count == 0:
            return None
        return remaining_mass - mass, stabilizer, rank
    raise AssertionError


def _free_rank(vector: _Vector) -> int | None:
    blocks = _extract_blocks(vector)
    if blocks is None:
        return None
    context = (_vector_mass(vector), _ALL_GROUP, 0)
    for block in range(_BLOCK_COUNT):
        next_context = _free_rank_step(blocks, block, context)
        if next_context is None:
            return None
        context = next_context
    _, group, rank = context
    return rank if group == _IDENTITY_GROUP else None


def _choose_local_class(
    block: int, mass: int, context: _UnrankContext
) -> tuple[_Block, int, int] | None:
    remaining_mass, group, rank = context
    for vector, stabilizer in _local_classes(block, mass, group):
        count = _free_suffix_count(block + 1, remaining_mass - mass, stabilizer)
        if rank >= count:
            rank -= count
            continue
        return vector, stabilizer, rank
    return None


def _free_unrank_step(
    block: int, blocks: list[_Block], context: _UnrankContext
) -> _UnrankContext:
    remaining_mass, group, rank = context
    for mass in range(remaining_mass + 1):
        count = _block_mass_count(block, mass, (remaining_mass - mass, group))
        if rank >= count:
            rank -= count
            continue
        chosen = _choose_local_class(block, mass, (remaining_mass, group, rank))
        assert chosen is not None
        vector, stabilizer, rank = chosen
        blocks.append(vector)
        return remaining_mass - mass, stabilizer, rank
    raise AssertionError


def _free_unrank(total: int, rank: int) -> _Vector | None:
    if rank < 0 or rank >= _free_count(total):
        return None
    blocks: list[_Block] = []
    context = (total, _ALL_GROUP, rank)
    for block in range(_BLOCK_COUNT):
        context = _free_unrank_step(block, blocks, context)
    remaining_mass, group, rank = context
    assert remaining_mass == 0
    assert rank == 0
    assert group == _IDENTITY_GROUP
    return _build_vector(tuple(blocks))


def _exact_count(total: int) -> int:
    return _free_count(total)


def _exact_rank(vector: _Vector) -> int | None:
    return _free_rank(vector)


def _exact_unrank(total: int, rank: int) -> _Vector | None:
    return _free_unrank(total, rank)


_S6_LABEL_MAPS = tuple(
    tuple(
        _RESIDUAL_INDEX[_permuted_symbol(label, order)]
        for label in _RESIDUAL_LABELS
    )
    for order in _S6
)


def _residual_values(vector: _Vector) -> _Vector:
    result = [0] * len(_RESIDUAL_LABELS)
    for value, orbit in zip(vector, _H_ORBITS, strict=True):
        for label in orbit:
            result[_RESIDUAL_INDEX[label]] = value
    return tuple(result)


def _stabilizer_order(vector: _Vector) -> int:
    values = _residual_values(vector)
    return sum(
        tuple(values[mapping[index]] for index in range(len(values))) == values
        for mapping in _S6_LABEL_MAPS
    )


def _pair_rank(pair: _Pair) -> int | None:
    first, second = pair
    if first < 0 or second < 0:
        return None
    return first


def _pair_unrank(total: int, rank: int) -> _Pair | None:
    if rank < 0 or rank > total:
        return None
    return rank, total - rank


def _class_count(total: int) -> int:
    return sum(
        (vertex_mass + 1) * _exact_count(total - _ARITY * vertex_mass)
        for vertex_mass in range(total // _ARITY + 1)
    )


def _rank(total: int, state: _State) -> int | None:
    vertex, residual = state
    vertex_rank = _pair_rank(vertex)
    vertex_mass = sum(vertex)
    residual_mass = total - _ARITY * vertex_mass
    if (
        vertex_rank is None
        or residual_mass < 0
        or _vector_mass(residual) != residual_mass
    ):
        return None
    residual_rank = _exact_rank(residual)
    if residual_rank is None:
        return None
    prefix = sum(
        (candidate_mass + 1) * _exact_count(total - _ARITY * candidate_mass)
        for candidate_mass in range(vertex_mass)
    )
    return prefix + vertex_rank * _exact_count(residual_mass) + residual_rank


def _unrank(total: int, rank: int) -> _State | None:
    if rank < 0 or rank >= _class_count(total):
        return None
    for vertex_mass in range(total // _ARITY + 1):
        residual_mass = total - _ARITY * vertex_mass
        residual_count = _exact_count(residual_mass)
        block_count = (vertex_mass + 1) * residual_count
        if rank >= block_count:
            rank -= block_count
            continue
        vertex_rank, residual_rank = divmod(rank, residual_count)
        vertex = _pair_unrank(vertex_mass, vertex_rank)
        residual = _exact_unrank(residual_mass, residual_rank)
        assert vertex is not None
        assert residual is not None
        return vertex, residual
    raise AssertionError


def _sample_ranks(count: int) -> tuple[int, ...]:
    return tuple(sorted({0, count // 4, count // 2, 3 * count // 4, count - 1}))


def test_v4_411_normalizer_geometry_is_exact() -> None:
    """H has order-twelve quotient, sixteen subgroups, and seven rank blocks."""
    orbit_sizes = {
        size: sum(len(orbit) == size for orbit in _H_ORBITS)
        for size in (1, 2, 4)
    }
    assert len(_minimal_generators(_H)) == _EXPECTED_H_GENERATORS
    assert _vertex_orbit_sizes(_H) == _EXPECTED_VERTEX_ORBITS
    assert len(_NORMALIZER) == _NORMALIZER_ORDER
    assert len(_ACTIONS) == _QUOTIENT_ORDER
    assert len(_all_q_subgroups()) == _EXPECTED_QUOTIENT_SUBGROUPS
    assert orbit_sizes == _EXPECTED_H_ORBIT_SIZES
    assert _BLOCK_SIZES == _EXPECTED_BLOCK_SIZES
    assert _BLOCK_WEIGHTS == _EXPECTED_BLOCK_WEIGHTS


def test_v4_411_free_rank_matches_exact_counts() -> None:
    """Normalizer-free and exact-H sequences coincide through mass fourteen."""
    observed = tuple(_free_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_FREE_COUNTS == _EXPECTED_EXACT_COUNTS
    for total in range(_EXHAUSTIVE_MASS + 1):
        for rank in range(_free_count(total)):
            vector = _free_unrank(total, rank)
            assert vector is not None
            assert _free_rank(vector) == rank


def test_v4_411_exact_rank_roundtrips_through_fourteen() -> None:
    """The free quotient itself is one dense exact-H residual interval."""
    for total in (*range(_EXHAUSTIVE_MASS + 1), _MAXIMUM_MASS):
        count = _exact_count(total)
        assert count == _EXPECTED_EXACT_COUNTS[total]
        if count == 0:
            continue
        ranks = (
            range(count) if total <= _EXHAUSTIVE_MASS else _sample_ranks(count)
        )
        for rank in ranks:
            vector = _exact_unrank(total, rank)
            assert vector is not None
            assert _exact_rank(vector) == rank


def test_v4_411_exact_samples_have_stabilizer_four() -> None:
    """Sampled retained representatives have exact S6 stabilizer H."""
    for total in (4, 5, 6, _MAXIMUM_MASS):
        count = _exact_count(total)
        for rank in _sample_ranks(count):
            vector = _exact_unrank(total, rank)
            assert vector is not None
            assert _stabilizer_order(vector) == _H_ORDER


def test_v4_411_complete_rank_roundtrips_through_fourteen() -> None:
    """Repeated-six vertex prefixes form one complete exact-H interval."""
    observed = tuple(_class_count(total) for total in range(_MAXIMUM_MASS + 1))
    assert observed == _EXPECTED_COMPLETE_COUNTS
    for total in (*range(_EXHAUSTIVE_MASS + 1), _MAXIMUM_MASS):
        count = _class_count(total)
        if count == 0:
            continue
        for rank in _sample_ranks(count):
            state = _unrank(total, rank)
            assert state is not None
            assert _rank(total, state) == rank
