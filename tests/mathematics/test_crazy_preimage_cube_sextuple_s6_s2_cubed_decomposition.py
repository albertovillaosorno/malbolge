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
#   - Nested quotient counts for S6 vertex multiplicity partition (2,2,2).
# - Must-Not:
#   - Claim dense rank/unrank for the S2-cubed Young stabilizer.
# - Allows:
#   - Inputs: sextuple residual mass 0 through 14 under three commuting swaps.
#   - Outputs: exact V4 quotient, descended fixed-set, and S2-cubed counts.
#   - Side effects: none.
# - Split-When:
#   - The descended third involution receives a constructive rank.
# - Merge-When:
#   - Complete dense S6 ranking owns the same nested quotient.
# - Summary:
#   - Quotient two swaps, then count fixed V4 classes under the third swap.
# - Description:
#   - Uses one V4 Burnside average and one commuting-coset fixed average.
# - Usage:
#   - Exact prerequisite for dense ranking of the (2,2,2) S6 stratum.
# - Defaults:
#   - Direct orbit/fixed-set enumeration stops at mass two.
#   - Exact arithmetic reaches mass 14.
#

"""Nested S2-cubed count decomposition for the S6 sextuple quotient."""

from __future__ import annotations

from collections import Counter
from functools import cache

_ARITY = 6
_MAXIMUM_MASS = 14
_EXHAUSTIVE_MASS = 2
_RESIDUAL_COMPONENTS = 52
_VERTEX_PARTITION = (2, 2, 2)
_WIDTH_FOURTEEN_RESIDUAL = 7_636_686_343_840
_WIDTH_FOURTEEN_STRATUM = 13_145_545_602
_EXPECTED_STRATUM_COUNTS = {
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

# Fixed-count cycle types by number of swapped vertex pairs.
_CYCLES = {
    0: (1,) * 52,
    1: (1,) * 24 + (2,) * 14,
    2: (1,) * 12 + (2,) * 20,
    3: (1,) * 8 + (2,) * 22,
}

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


def _compose(left: _Permutation, right: _Permutation) -> _Permutation:
    values = tuple(left[right[index]] for index in range(_ARITY))
    first, second, third, fourth, fifth, sixth = values
    return first, second, third, fourth, fifth, sixth


_AB = _compose(_A, _B)
_AC = _compose(_A, _C)
_BC = _compose(_B, _C)
_ABC = _compose(_AB, _C)
_V4 = (_IDENTITY, _A, _B, _AB)
_E8 = (_IDENTITY, _A, _B, _AB, _C, _AC, _BC, _ABC)


def _permuted_symbol(symbol: int, order: _Permutation) -> int:
    bits = tuple(
        (symbol >> (_ARITY - endpoint - 1)) & 1
        for endpoint in range(_ARITY)
    )
    result = 0
    for source in order:
        result = (result << 1) | bits[source]
    return result


def _cycle_histogram(order: _Permutation) -> Counter[int]:
    unseen = set(_RESIDUAL_LABELS)
    result: Counter[int] = Counter()
    while unseen:
        current = min(unseen)
        orbit: set[int] = set()
        while current not in orbit:
            orbit.add(current)
            current = _permuted_symbol(current, order)
        unseen -= orbit
        result[len(orbit)] += 1
    return result


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


def _v4_count(total: int) -> int:
    identity = _fixed_count(total, _CYCLES[0])
    single = _fixed_count(total, _CYCLES[1])
    double = _fixed_count(total, _CYCLES[2])
    return (identity + 2 * single + double) // 4


def _descended_fixed_count(total: int) -> int:
    single = _fixed_count(total, _CYCLES[1])
    double = _fixed_count(total, _CYCLES[2])
    triple = _fixed_count(total, _CYCLES[3])
    return (single + 2 * double + triple) // 4


def _e8_count(total: int) -> int:
    return (_v4_count(total) + _descended_fixed_count(total)) // 2


def _weak_compositions(total: int, parts: int) -> tuple[_Vector, ...]:
    if parts == 1:
        return ((total,),)
    return tuple(
        (first, *rest)
        for first in range(total + 1)
        for rest in _weak_compositions(total - first, parts - 1)
    )


def _permute_vector(vector: _Vector, order: _Permutation) -> _Vector:
    result = [0] * _RESIDUAL_COMPONENTS
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
        _vertex_count(vertex_mass) * _e8_count(total - vertex_mass)
        for vertex_mass in range(total + 1)
    )


def test_s6_s2_cubed_residual_cycle_types_are_exact() -> None:
    """The eight group elements realize the four reviewed cycle types."""
    expected = {
        _IDENTITY: Counter({1: 52}),
        _A: Counter({1: 24, 2: 14}),
        _B: Counter({1: 24, 2: 14}),
        _C: Counter({1: 24, 2: 14}),
        _AB: Counter({1: 12, 2: 20}),
        _AC: Counter({1: 12, 2: 20}),
        _BC: Counter({1: 12, 2: 20}),
        _ABC: Counter({1: 8, 2: 22}),
    }
    observed = Counter(
        tuple(sorted(_cycle_histogram(order).items())) for order in _E8
    )
    reviewed = Counter(
        tuple(sorted(value.items())) for value in expected.values()
    )
    assert observed == reviewed
    for order, histogram in expected.items():
        assert _cycle_histogram(order) == histogram


def test_s6_s2_cubed_nested_fixed_set_matches_direct_small_orbits() -> None:
    """The commuting coset average counts V4 classes fixed by the third swap."""
    for total in range(_EXHAUSTIVE_MASS + 1):
        v4_representatives: set[_Vector] = set()
        fixed_representatives: set[_Vector] = set()
        e8_representatives: set[_Vector] = set()
        for vector in _weak_compositions(total, _RESIDUAL_COMPONENTS):
            v4 = _canonical(vector, _V4)
            v4_representatives.add(v4)
            if _canonical(_permute_vector(v4, _C), _V4) == v4:
                fixed_representatives.add(v4)
            e8_representatives.add(_canonical(vector, _E8))
        assert len(v4_representatives) == _v4_count(total)
        assert len(fixed_representatives) == _descended_fixed_count(total)
        assert len(e8_representatives) == _e8_count(total)


def test_s6_s2_cubed_nested_count_matches_full_burnside() -> None:
    """The third involution reconstructs the exact eight-element quotient."""
    for total in range(_MAXIMUM_MASS + 1):
        identity = _fixed_count(total, _CYCLES[0])
        single = _fixed_count(total, _CYCLES[1])
        double = _fixed_count(total, _CYCLES[2])
        triple = _fixed_count(total, _CYCLES[3])
        full = (identity + 3 * single + 3 * double + triple) // 8
        assert _e8_count(total) == full
    assert _e8_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_RESIDUAL


def test_s6_s2_cubed_stratum_counts_match_reviewed_sequence() -> None:
    """Vertex prefixes lift the residual quotient to the exact local stratum."""
    observed = {
        mass: _stratum_count(mass)
        for mass in range(_MAXIMUM_MASS + 1)
        if _stratum_count(mass) != 0
    }
    assert observed == _EXPECTED_STRATUM_COUNTS
    assert _stratum_count(_MAXIMUM_MASS) == _WIDTH_FOURTEEN_STRATUM
