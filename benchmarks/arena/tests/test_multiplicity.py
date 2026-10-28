# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Independent exact Holm correction and regression checks.
# - Must-Not:
#   - Infer significance or authenticate the input p-values.
# - Allows:
#   - Inputs: synthetic test probabilities, ties, and bounded exact fractions.
#   - Outputs: assertions on monotone adjusted values in original order.
#   - Side effects: none.
# - Split-When:
#   - A different family-wise or false-discovery method needs separate tests.
# - Merge-When:
#   - A single statistics test boundary includes these Holm references.
# - Summary:
#   - Guards against rank-order, tie, and floating adjustment defects.
# - Description:
#   - Exercises independent manual examples and invariant enumerations.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_multiplicity.py`.
# - Defaults:
#   - Empty test families produce empty results.
#

"""Synthetic regression checks for exact Holm family-wise adjustment."""

# ruff: file-ignore[assert]

from __future__ import annotations

from fractions import Fraction
from itertools import product
from operator import itemgetter

import pytest

from benchmarks.arena import multiplicity


@pytest.mark.parametrize(
    ("raw", "adjusted"),
    [
        ([], []),
        ([Fraction(1, 100)], [Fraction(1, 100)]),
        (
            [
                Fraction(1, 2),
                Fraction(1, 100),
                Fraction(1, 20),
                Fraction(1, 25),
            ],
            [Fraction(1, 2), Fraction(1, 25), Fraction(3, 25), Fraction(3, 25)],
        ),
        (
            [Fraction(1, 20), Fraction(1, 20), Fraction(1, 2)],
            [Fraction(3, 20), Fraction(3, 20), Fraction(1, 2)],
        ),
        ([Fraction(0), Fraction(1)], [Fraction(0), Fraction(1)]),
        ([Fraction(1, 2)] * 3, [Fraction(1)] * 3),
    ],
)
def test_known_holm_examples_preserve_input_order_and_exact_fractions(
    raw: list[Fraction],
    adjusted: list[Fraction],
) -> None:
    """Compare with manually computed two-sided multiple-test examples."""
    assert multiplicity.holm_adjusted(raw) == adjusted


def test_holm_monotonicity_and_uncorrected_lower_bound_for_small_families() -> (
    None
):
    """Small exact fractions never become smaller after correction."""
    candidates = [Fraction(0), Fraction(1, 10), Fraction(1, 2), Fraction(1)]
    for sample in product(candidates, repeat=4):
        adjusted = multiplicity.holm_adjusted(list(sample))
        assert all(
            left <= right <= 1
            for left, right in zip(sample, adjusted, strict=True)
        )
        ordered = sorted(zip(sample, adjusted, strict=True), key=itemgetter(0))
        assert all(
            ordered[index][1] <= ordered[index + 1][1]
            for index in range(len(ordered) - 1)
        )


def test_equal_raw_p_values_get_equal_adjustment() -> None:
    """Tie-breaking is deterministic but never changes tied conclusions."""
    raw = [Fraction(1, 40), Fraction(1, 40), Fraction(1, 40), Fraction(1)]
    result = multiplicity.holm_adjusted(raw)
    assert result[:3] == [Fraction(1, 10)] * 3
    assert result[3] == 1


def test_large_integer_fractions_do_not_round_to_equal_floats() -> None:
    """Exact high-precision probabilities retain strict ordering when needed."""
    large = 2**100
    raw = [Fraction(large + 1, 2 * large), Fraction(1, large)]
    assert multiplicity.holm_adjusted(raw) == [raw[0], Fraction(2, large)]


@pytest.mark.parametrize("bad", [Fraction(-1, 10), Fraction(11, 10)])
def test_invalid_probability_fails_closed(bad: Fraction) -> None:
    """Caller bugs must not produce a purported correction from invalid p."""
    with pytest.raises(ValueError, match="Holm adjustment requires"):
        multiplicity.holm_adjusted([Fraction(1, 5), bad])
