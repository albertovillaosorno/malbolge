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
#   - Independent exact-binomial reference checks for paired comparisons.
# - Must-Not:
#   - Treat synthetic outcome labels as actual stochastic trial evidence.
# - Allows:
#   - Inputs: bounded integer discordant counts and independent comb() sums.
#   - Outputs: assertions about exact two-sided probabilities and no-data cases.
#   - Side effects: none.
# - Split-When:
#   - An independent statistical null needs a different reference oracle.
# - Merge-When:
#   - One research statistics test boundary owns these exact sign tests.
# - Summary:
#   - Guards two-sided p-values from one-tail errors and tie miscounting.
# - Description:
#   - Checks balanced, unbalanced, huge, invalid and empty comparisons.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_paired_exact_tests.py`.
# - Defaults:
#   - Missing discordant evidence yields null, not p=1.
#

"""Exact combinatorial reference tests for paired binomial sign tests."""

# ruff: file-ignore[assert]

from __future__ import annotations

from fractions import Fraction
from math import comb

import pytest

from benchmarks.arena import paired_exact_tests


def _reference(left: int, right: int) -> Fraction:
    """Compute the full exact binomial tail using math.comb().

    Returns:
        Independent two-sided conditional probability.

    """
    count = left + right
    tail = sum(comb(count, index) for index in range(min(left, right) + 1))
    return min(Fraction(1), Fraction(2 * tail, 1 << count))


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (1, 0),
        (0, 1),
        (1, 1),
        (0, 6),
        (6, 0),
        (1, 11),
        (11, 1),
        (3, 7),
        (7, 3),
        (5, 5),
        (15, 5),
        (5, 15),
        (0, 100),
        (50, 50),
    ],
)
def test_exact_paired_p_value_matches_independent_binomial_reference(
    left: int,
    right: int,
) -> None:
    """Two-sided conditional symmetry retains exact rational probability."""
    observed = paired_exact_tests.two_sided_sign_test(left, right)
    assert observed is not None
    assert observed["discordant_pairs"] == left + right
    assert Fraction(*observed["p_two_sided"]) == _reference(left, right)
    assert Fraction(*observed["p_two_sided"]) <= 1
    assert paired_exact_tests.two_sided_sign_test(right, left) == observed


def test_zero_discordance_is_uninformative_not_evidence_for_null() -> None:
    """No discordant pairs means no exact conditional test is possible."""
    assert paired_exact_tests.two_sided_sign_test(0, 0) is None


def test_all_six_discordant_in_one_direction_have_one_over_32() -> None:
    """Detect one-tail versus two-tail errors at the p=0.05 boundary."""
    assert paired_exact_tests.two_sided_sign_test(6, 0) == {
        "discordant_pairs": 6,
        "p_two_sided": [1, 32],
    }


def test_one_against_eleven_has_exact_thirteen_over_2048() -> None:
    """Check nontrivial combinatorial tail and reduced rational output."""
    assert paired_exact_tests.two_sided_sign_test(11, 1) == {
        "discordant_pairs": 12,
        "p_two_sided": [13, 2048],
    }


def test_perfect_balance_caps_two_sided_probability_at_one() -> None:
    """Avoid returning an uncapped two-sided mass above one."""
    assert paired_exact_tests.two_sided_sign_test(5, 5) == {
        "discordant_pairs": 10,
        "p_two_sided": [1, 1],
    }


@pytest.mark.parametrize(
    ("left", "right"),
    [(True, 0), (False, 1), (-1, 2), (2, -1), (1, 2.0)],
)
def test_bad_caller_counts_produce_no_inferential_result(
    left: int,
    right: int,
) -> None:
    """Booleans and invalid counts never impersonate valid evidence."""
    assert paired_exact_tests.two_sided_sign_test(left, right) is None


def test_bounded_discordant_pairs_keep_large_exact_probabilities() -> None:
    """No overflowing floating-point probability or unbounded big integers."""
    count = paired_exact_tests.MAX_DISCORDANT_PAIRS
    all_left = paired_exact_tests.two_sided_sign_test(count, 0)
    assert all_left is not None
    assert Fraction(*all_left["p_two_sided"]) == Fraction(1, 1 << (count - 1))
    balanced = paired_exact_tests.two_sided_sign_test(count // 2, count // 2)
    assert balanced is not None
    assert balanced["p_two_sided"] == [1, 1]
    assert paired_exact_tests.two_sided_sign_test(count + 1, 0) is None
