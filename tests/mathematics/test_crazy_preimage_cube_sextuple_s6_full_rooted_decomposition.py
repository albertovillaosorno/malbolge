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
#   - Rooted-S5 versus unrooted-S6 counts for the top-level (6) residual domain.
# - Must-Not:
#   - Interpret root-view deficits as symmetric-class counts or claim dense
#     rank.
# - Allows:
#   - Inputs: residual ambiguity mass zero through fourteen.
#   - Outputs: exact full/layer Burnside counts and six-root deficits.
#   - Side effects: none.
# - Split-When:
#   - Exact S6 stabilizer classes or canonical-root rank/unrank are added.
# - Merge-When:
#   - Complete dense S6 ranking owns the all-equal top-level stratum.
# - Summary:
#   - Compare full-S6 residual classes with one-endpoint-rooted S5 classes.
# - Description:
#   - The difference from six rooted views is a weighted automorphism deficit.
# - Usage:
#   - Exact prerequisite for canonical-root ranking of the final (6) stratum.
# - Defaults:
#   - Burnside arithmetic reaches mass fourteen; no orbit materialization is
#     used.
#

"""Rooted-S5 count decomposition for the final S6 (6) Young stratum."""

from __future__ import annotations

from functools import cache
from itertools import permutations
from typing import cast

_ARITY = 6
_MAXIMUM_MASS = 14
_ROOT = 5
_S6_ORDER = 720
_S5_ORDER = 120
_FULL_LABEL_COUNT = 52
_EDGE_LABEL_COUNT = 30
_MIDDLE_LABEL_COUNT = 20
_MIDDLE_WEIGHT = 3
_EXPECTED_FULL_UNROOTED = (
    1,
    5,
    28,
    178,
    1_268,
    9_476,
    70_922,
    511_459,
    3_480_079,
    22_130_232,
    131_252_006,
    727_284_758,
    3_778_300_228,
    18_478_372_801,
    85_431_118_919,
)
_EXPECTED_FULL_ROOTED = (
    1,
    8,
    67,
    588,
    5_257,
    45_642,
    374_027,
    2_845_008,
    19_961_731,
    129_216_492,
    774_402_196,
    4_317_877_538,
    22_516_940_260,
    110_382_248_928,
    511_090_971_734,
)
_EXPECTED_EDGE_DEFICIT = 6_635_545
_EXPECTED_MIDDLE_DEFICIT = 92_506
_EXPECTED_FULL_DEFICIT = 1_495_741_780

type _Permutation = tuple[int, int, int, int, int, int]

_S6 = cast("tuple[_Permutation, ...]", tuple(permutations(range(_ARITY))))
_S5 = tuple(order for order in _S6 if order[_ROOT] == _ROOT)
_FULL_LABELS = tuple(
    symbol
    for symbol in range(1 << _ARITY)
    if symbol.bit_count() not in {1, _ARITY - 1}
)
_EDGE_LABELS = tuple(
    symbol for symbol in _FULL_LABELS if symbol.bit_count() in {2, 4}
)
_MIDDLE_LABELS = tuple(
    symbol for symbol in _FULL_LABELS if symbol.bit_count() == _MIDDLE_WEIGHT
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
def _cycle_lengths(
    order: _Permutation,
    labels: tuple[int, ...],
) -> tuple[int, ...]:
    unseen = set(labels)
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


def _fixed_sequence(cycles: tuple[int, ...]) -> tuple[int, ...]:
    coefficients = [1] + [0] * _MAXIMUM_MASS
    for cycle_length in cycles:
        next_coefficients = [0] * (_MAXIMUM_MASS + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for addition in range(
                0,
                _MAXIMUM_MASS - degree + 1,
                cycle_length,
            ):
                next_coefficients[degree + addition] += coefficient
        coefficients = next_coefficients
    return tuple(coefficients)


def _burnside_sequence(
    group: tuple[_Permutation, ...],
    labels: tuple[int, ...],
) -> tuple[int, ...]:
    totals = [0] * (_MAXIMUM_MASS + 1)
    for order in group:
        fixed = _fixed_sequence(_cycle_lengths(order, labels))
        for mass, count in enumerate(fixed):
            totals[mass] += count
    assert all(total % len(group) == 0 for total in totals)
    return tuple(total // len(group) for total in totals)


def _root_deficit(
    unrooted: tuple[int, ...],
    rooted: tuple[int, ...],
) -> tuple[int, ...]:
    return tuple(
        _ARITY * unrooted_count - rooted_count
        for unrooted_count, rooted_count in zip(unrooted, rooted, strict=True)
    )


def test_s6_full_rooted_groups_and_layers_have_exact_sizes() -> None:
    """Rooting one endpoint leaves S5 and the residual 30+20+2 layer split."""
    assert len(_S6) == _S6_ORDER
    assert len(_S5) == _S5_ORDER
    assert len(_FULL_LABELS) == _FULL_LABEL_COUNT
    assert len(_EDGE_LABELS) == _EDGE_LABEL_COUNT
    assert len(_MIDDLE_LABELS) == _MIDDLE_LABEL_COUNT


def test_s6_full_rooted_counts_match_reviewed_full_sequences() -> None:
    """Full residual S6 and rooted-S5 Burnside sequences agree through 14."""
    unrooted = _burnside_sequence(_S6, _FULL_LABELS)
    rooted = _burnside_sequence(_S5, _FULL_LABELS)
    assert unrooted == _EXPECTED_FULL_UNROOTED
    assert rooted == _EXPECTED_FULL_ROOTED
    assert (
        _root_deficit(unrooted, rooted)[_MAXIMUM_MASS] == _EXPECTED_FULL_DEFICIT
    )


def test_s6_full_rooted_layer_deficits_match_reviewed_values() -> None:
    """The edge-pair and middle layers have exact bounded root deficits."""
    edge_unrooted = _burnside_sequence(_S6, _EDGE_LABELS)
    edge_rooted = _burnside_sequence(_S5, _EDGE_LABELS)
    middle_unrooted = _burnside_sequence(_S6, _MIDDLE_LABELS)
    middle_rooted = _burnside_sequence(_S5, _MIDDLE_LABELS)
    assert (
        _root_deficit(edge_unrooted, edge_rooted)[-1] == _EXPECTED_EDGE_DEFICIT
    )
    assert (
        _root_deficit(middle_unrooted, middle_rooted)[-1]
        == _EXPECTED_MIDDLE_DEFICIT
    )


def test_s6_full_root_deficit_is_not_a_class_count_identity() -> None:
    """The deficit is missing rooted-view multiplicity, not an orbit count."""
    unrooted = _burnside_sequence(_S6, _FULL_LABELS)
    rooted = _burnside_sequence(_S5, _FULL_LABELS)
    deficit = _root_deficit(unrooted, rooted)
    assert all(value >= 0 for value in deficit)
    assert rooted[-1] + deficit[-1] == _ARITY * unrooted[-1]
