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
#   - Dense rank/unrank for trivial-stabilizer pair-valued K5 edge orbits.
# - Must-Not:
#   - Claim a local rank for any nontrivial exact stabilizer stratum.
# - Allows:
#   - Inputs: full-S5 edge orbits with trivial stabilizer, mass 0 through 14.
#   - Outputs: dense prefix/select ranks of unique minimum rooted views.
#   - Side effects: none.
# - Split-When:
#   - The rooted canonical order becomes a separately consumed API.
# - Merge-When:
#   - Complete dense S5 ranking owns every stabilizer stratum.
# - Summary:
#   - Select the unique minimum rooted S4 canonical view of each free S5 orbit.
# - Description:
#   - Lexicographic rooted canonical order makes the free-orbit selector exact.
# - Usage:
#   - Dense rank for the 6,689,862-class mass-fourteen generic S5 stratum.
# - Defaults:
#   - Direct orbit/rank exhaustion stops at mass three; counts reach mass 14.
#

"""Dense unique-minimum-root ranking for trivial-stabilizer S5 edge orbits."""

from __future__ import annotations

from functools import cache
from itertools import permutations

_ARITY = 5
_EDGE_COUNT = 10
_SCALAR_COUNT = 2 * _EDGE_COUNT
_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 3
_WIDTH_FOURTEEN_ALL_CLASSES = 6_962_786
_WIDTH_FOURTEEN_SYMMETRIC_CLASSES = 272_924
_WIDTH_FOURTEEN_TRIVIAL_CLASSES = 6_689_862
_EXPECTED_EXCEPTION_COUNTS = (
    239_656,
    21_920,
    10_466,
    402,
    106,
    174,
    6,
    194,
)

type _Pair = tuple[int, int]
type _EdgePairs = tuple[_Pair, ...]
type _Permutation = tuple[int, int, int, int, int]

_EDGES = tuple(
    (left, right)
    for left in range(_ARITY)
    for right in range(left + 1, _ARITY)
)
_EDGE_INDEX = {edge: index for index, edge in enumerate(_EDGES)}


def _as_permutation(order: tuple[int, ...]) -> _Permutation:
    assert len(order) == _ARITY
    first, second, third, fourth, fifth = order
    return first, second, third, fourth, fifth


_S5: tuple[_Permutation, ...] = tuple(
    _as_permutation(order) for order in permutations(range(_ARITY))
)
_ROOT_ORDERS = tuple(
    tuple(order for order in _S5 if order[_ARITY - 1] == root)
    for root in range(_ARITY)
)


def _permute(edge_pairs: _EdgePairs, order: _Permutation) -> _EdgePairs:
    result: list[_Pair] = []
    for left, right in _EDGES:
        source = tuple(sorted((order[left], order[right])))
        result.append(edge_pairs[_EDGE_INDEX[source[0], source[1]]])
    return tuple(result)


def _rooted_representative(edge_pairs: _EdgePairs, root: int) -> _EdgePairs:
    return min(_permute(edge_pairs, order) for order in _ROOT_ORDERS[root])


def _full_representative(edge_pairs: _EdgePairs) -> _EdgePairs:
    return min(_permute(edge_pairs, order) for order in _S5)


def _stabilizer_order(edge_pairs: _EdgePairs) -> int:
    return sum(_permute(edge_pairs, order) == edge_pairs for order in _S5)


def _visit_scalars(
    remaining: int,
    index: int,
    prefix: list[int],
    *,
    result: list[tuple[int, ...]],
) -> None:
    if index == _SCALAR_COUNT - 1:
        result.append((*prefix, remaining))
        return
    for value in range(remaining + 1):
        prefix.append(value)
        _visit_scalars(
            remaining - value,
            index + 1,
            prefix,
            result=result,
        )
        _ = prefix.pop()


@cache
def _assignments(total: int) -> tuple[_EdgePairs, ...]:
    scalars: list[tuple[int, ...]] = []
    _visit_scalars(total, 0, [], result=scalars)
    return tuple(
        tuple(
            (vector[2 * edge], vector[2 * edge + 1])
            for edge in range(_EDGE_COUNT)
        )
        for vector in scalars
    )


@cache
def _rooted_classes(total: int) -> tuple[_EdgePairs, ...]:
    rooted = {
        _rooted_representative(edge_pairs, _ARITY - 1)
        for edge_pairs in _assignments(total)
    }
    return tuple(sorted(rooted))


def _is_selected_trivial_root(edge_pairs: _EdgePairs) -> bool:
    if _stabilizer_order(edge_pairs) != 1:
        return False
    rooted_views = tuple(
        _rooted_representative(edge_pairs, root) for root in range(_ARITY)
    )
    return edge_pairs == min(rooted_views)


@cache
def _accepted_rooted_classes(total: int) -> tuple[_EdgePairs, ...]:
    return tuple(
        edge_pairs
        for edge_pairs in _rooted_classes(total)
        if _is_selected_trivial_root(edge_pairs)
    )


def _rank(total: int, edge_pairs: _EdgePairs) -> int | None:
    accepted = _accepted_rooted_classes(total)
    try:
        return accepted.index(edge_pairs)
    except ValueError:
        return None


def _unrank(total: int, rank: int) -> _EdgePairs | None:
    accepted = _accepted_rooted_classes(total)
    if rank < 0 or rank >= len(accepted):
        return None
    return accepted[rank]


def _fixed_count(cycles: tuple[int, ...], total: int) -> int:
    coefficients = [1] + [0] * total
    for cycle in cycles:
        next_coefficients = [0] * (total + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            multiplicity = 0
            while degree + multiplicity * cycle <= total:
                next_coefficients[degree + multiplicity * cycle] += (
                    coefficient * (multiplicity + 1)
                )
                multiplicity += 1
        coefficients = next_coefficients
    return coefficients[total]


def _edge_cycles(order: _Permutation) -> tuple[int, ...]:
    edge_permutation: list[int] = []
    for left, right in _EDGES:
        image = tuple(sorted((order[left], order[right])))
        edge_permutation.append(_EDGE_INDEX[image[0], image[1]])
    unseen = set(range(_EDGE_COUNT))
    result: list[int] = []
    while unseen:
        seed = min(unseen)
        cycle: set[int] = set()
        current = seed
        while current not in cycle:
            cycle.add(current)
            current = edge_permutation[current]
        unseen -= cycle
        result.append(len(cycle))
    return tuple(sorted(result))


def _burnside_count(total: int) -> int:
    fixed = sum(_fixed_count(_edge_cycles(order), total) for order in _S5)
    return fixed // len(_S5)


def test_trivial_rank_selects_unique_minimum_root_per_free_orbit() -> None:
    """Each small free S5 orbit contributes one accepted rooted view."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        expected: set[_EdgePairs] = set()
        for edge_pairs in _assignments(total):
            representative = _full_representative(edge_pairs)
            if _stabilizer_order(representative) != 1:
                continue
            expected.add(representative)
        accepted = _accepted_rooted_classes(total)
        assert len(accepted) == len(expected)
        accepted_orbits = {_full_representative(item) for item in accepted}
        assert len(accepted_orbits) == len(expected)
        assert all(_is_selected_trivial_root(item) for item in accepted)


def test_trivial_rank_is_dense_on_small_free_orbits() -> None:
    """Selected rooted views have one contiguous rank per free orbit."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        accepted = _accepted_rooted_classes(total)
        for rank, edge_pairs in enumerate(accepted):
            assert _rank(total, edge_pairs) == rank
            assert _unrank(total, rank) == edge_pairs
            full_orbit = {
                _full_representative(_permute(edge_pairs, order))
                for order in _S5
            }
            assert full_orbit == {_full_representative(edge_pairs)}
        assert _unrank(total, -1) is None
        assert _unrank(total, len(accepted)) is None


def test_trivial_mass_fourteen_count_is_exact_from_proved_strata() -> None:
    """Burnside total minus all symmetric exact strata gives the free count."""
    assert _burnside_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_ALL_CLASSES
    assert sum(_EXPECTED_EXCEPTION_COUNTS) == _WIDTH_FOURTEEN_SYMMETRIC_CLASSES
    assert (
        _WIDTH_FOURTEEN_ALL_CLASSES - _WIDTH_FOURTEEN_SYMMETRIC_CLASSES
        == _WIDTH_FOURTEEN_TRIVIAL_CLASSES
    )
