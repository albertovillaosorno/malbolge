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
#   - S4-first quotient and descended-swap counts for S6 partition (4,2).
# - Must-Not:
#   - Claim dense rank/unrank for the residual S4-times-S2 quotient.
# - Allows:
#   - Inputs: residual and complete (4,2) masses zero through fourteen.
#   - Outputs: exact S4 quotient, descended fixed-set, and S4xS2 counts.
#   - Side effects: none.
# - Split-When:
#   - The descended singleton swap receives constructive dense rank/unrank.
# - Merge-When:
#   - Complete dense S6 ranking owns the same (4,2) quotient.
# - Summary:
#   - Quotient S4 first, then count S4 classes fixed by the singleton swap.
# - Description:
#   - Uses the commuting S2 coset average before the final two-way quotient.
# - Usage:
#   - Exact prerequisite for dense ranking of the S6 (4,2) Young stratum.
# - Defaults:
#   - Direct residual orbit/fixed-set enumeration stops at mass two.
#

"""S4-first count decomposition for the S6 (4,2) Young stratum."""

from __future__ import annotations

from collections import Counter
from functools import cache
from itertools import permutations

_ARITY = 6
_MAXIMUM_MASS = 14
_S4_ORDER = 24
_S4_S2_ORDER = 48
_EXHAUSTIVE_MASS = 2
_VERTEX_PARTITION = (4, 2)
_WIDTH_FOURTEEN_RESIDUAL = 1_275_603_806_904
_WIDTH_FOURTEEN_S4 = 2_549_713_246_880
_WIDTH_FOURTEEN_FIXED = 1_494_366_928
_WIDTH_FOURTEEN_STRATUM = 122_060_462_590
_EXPECTED_STRATUM_COUNTS = {
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

_IDENTITY = (0, 1, 2, 3, 4, 5)
_SINGLETON_SWAP = (0, 1, 2, 3, 5, 4)

type _Pair = tuple[int, int]
type _Vector = tuple[int, ...]
type _Permutation = tuple[int, int, int, int, int, int]

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


def _as_permutation(order: tuple[int, ...]) -> _Permutation:
    assert len(order) == _ARITY
    first, second, third, fourth, fifth, sixth = order
    return first, second, third, fourth, fifth, sixth


def _s4_group() -> tuple[_Permutation, ...]:
    return tuple(
        _as_permutation((*active, 4, 5)) for active in permutations(range(4))
    )


_S4 = _s4_group()


def _compose(left: _Permutation, right: _Permutation) -> _Permutation:
    return _as_permutation(tuple(left[right[index]] for index in range(_ARITY)))


_COSET = tuple(_compose(_SINGLETON_SWAP, order) for order in _S4)
_S4_S2 = (*_S4, *_COSET)


def _permuted_symbol(symbol: int, order: _Permutation) -> int:
    bits = tuple(
        (symbol >> (_ARITY - endpoint - 1)) & 1 for endpoint in range(_ARITY)
    )
    result = 0
    for source in order:
        result = (result << 1) | bits[source]
    return result


def _cycle_lengths(order: _Permutation) -> tuple[int, ...]:
    unseen = set(_RESIDUAL_LABELS)
    result: list[int] = []
    while unseen:
        current = min(unseen)
        length = 0
        while current in unseen:
            unseen.remove(current)
            current = _permuted_symbol(current, order)
            length += 1
        result.append(length)
    return tuple(sorted(result))


def _fixed_count(total: int, cycles: tuple[int, ...]) -> int:
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


def _average_fixed(total: int, group: tuple[_Permutation, ...]) -> int:
    fixed = sum(_fixed_count(total, _cycle_lengths(order)) for order in group)
    assert fixed % len(group) == 0
    return fixed // len(group)


def _s4_count(total: int) -> int:
    return _average_fixed(total, _S4)


def _descended_fixed_count(total: int) -> int:
    fixed = sum(_fixed_count(total, _cycle_lengths(order)) for order in _COSET)
    assert fixed % len(_S4) == 0
    return fixed // len(_S4)


def _s4s2_count(total: int) -> int:
    return (_s4_count(total) + _descended_fixed_count(total)) // 2


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _permute_vector(vector: _Vector, order: _Permutation) -> _Vector:
    result = [0] * len(_RESIDUAL_LABELS)
    for source, label in enumerate(_RESIDUAL_LABELS):
        destination = _permuted_symbol(label, order)
        result[_LABEL_INDEX[destination]] = vector[source]
    return tuple(result)


def _canonical(vector: _Vector, group: tuple[_Permutation, ...]) -> _Vector:
    return min(_permute_vector(vector, order) for order in group)


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


def _vertex_partition(values: tuple[_Pair, ...]) -> tuple[int, ...]:
    return tuple(sorted(Counter(values).values(), reverse=True))


@cache
def _vertex_count(mass: int) -> int:
    return sum(
        1
        for values in _vertex_sequences_from(0, _ARITY, mass)
        if sum(sum(pair) for pair in values) == mass
        and _vertex_partition(values) == _VERTEX_PARTITION
    )


def _stratum_count(total: int) -> int:
    return sum(
        _vertex_count(vertex_mass) * _s4s2_count(total - vertex_mass)
        for vertex_mass in range(total + 1)
    )


def test_s6_s4s2_groups_are_exact_commuting_extension() -> None:
    """The full Young group is S4 times the singleton-exchange S2."""
    assert len(_S4) == _S4_ORDER
    assert len(_COSET) == _S4_ORDER
    assert len(set(_S4_S2)) == _S4_S2_ORDER
    assert _IDENTITY in _S4
    assert _SINGLETON_SWAP in _COSET


def test_s6_s4s2_descended_fixed_set_matches_direct_small_orbits() -> None:
    """The commuting coset counts S4 classes fixed by the singleton swap."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        s4_representatives: set[_Vector] = set()
        fixed_representatives: set[_Vector] = set()
        full_representatives: set[_Vector] = set()
        for vector in _weak_compositions(total, len(_RESIDUAL_LABELS)):
            s4 = _canonical(vector, _S4)
            s4_representatives.add(s4)
            swapped = _permute_vector(s4, _SINGLETON_SWAP)
            if _canonical(swapped, _S4) == s4:
                fixed_representatives.add(s4)
            full_representatives.add(_canonical(vector, _S4_S2))
        assert len(s4_representatives) == _s4_count(total)
        assert len(fixed_representatives) == _descended_fixed_count(total)
        assert len(full_representatives) == _s4s2_count(total)


def test_s6_s4s2_nested_count_matches_full_product_burnside() -> None:
    """The descended involution reconstructs the exact 48-element quotient."""
    for total in range(_MAXIMUM_MASS + 1):
        assert _s4s2_count(total) == _average_fixed(total, _S4_S2)
    assert _s4_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_S4
    assert _descended_fixed_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_FIXED
    assert _s4s2_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_RESIDUAL


def test_s6_s4s2_stratum_counts_match_reviewed_sequence() -> None:
    """Vertex prefixes lift the product quotient to the exact stratum."""
    observed = {
        mass: _stratum_count(mass)
        for mass in range(_MAXIMUM_MASS + 1)
        if _stratum_count(mass) != 0
    }
    assert observed == _EXPECTED_STRATUM_COUNTS
    assert observed[_MAXIMUM_MASS] == _WIDTH_FOURTEEN_STRATUM
