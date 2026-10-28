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
#   - Exact binomial-tail reference regressions for reported success intervals.
# - Must-Not:
#   - Infer actual sampling independence or externally verified outcomes.
# - Allows:
#   - Inputs: synthetic Bernoulli counts and independent exact binomial sums.
#   - Outputs: assertions on conservative rational grid endpoints.
#   - Side effects: none.
# - Split-When:
#   - Other success-rate estimands require independent verification tests.
# - Merge-When:
#   - One research statistics fixture owns exact coverage inversion.
# - Summary:
#   - Guards Clopper-Pearson tail direction and outward grid rounding.
# - Description:
#   - Checks extreme, balanced, invalid, large and symmetry boundaries.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_success_intervals.py`.
# - Defaults:
#   - Unmeasured sample populations yield no confidence claim.
#

"""Exact independent binomial checks for optional success uncertainty."""

# ruff: file-ignore[assert]

from __future__ import annotations

from fractions import Fraction
from itertools import pairwise
from math import comb

import pytest

from benchmarks.arena import success_intervals

TAIL = Fraction(1, 40)
GRID = success_intervals.GRID_DENOMINATOR


def _reference_lower_tail(n: int, k: int, p: Fraction) -> Fraction:
    """Evaluate a binomial CDF by an independent rational polynomial.

    Returns:
        The exact probability of at most k successes.

    """
    return sum(
        (
            Fraction(comb(n, index)) * p**index * (1 - p) ** (n - index)
            for index in range(k + 1)
        ),
        Fraction(0),
    )


def _reference_grid_bound(n: int, k: int, *, lower: bool) -> int:
    """Scan all 4097 grid points without using the production binary search.

    Returns:
        A conservatively rounded endpoint index.

    """
    if lower:
        return (
            max(
                index
                for index in range(GRID + 1)
                if 1 - _reference_lower_tail(n, k - 1, Fraction(index, GRID))
                <= TAIL
            )
            if k != 0
            else 0
        )
    return (
        min(
            index
            for index in range(GRID + 1)
            if _reference_lower_tail(n, k, Fraction(index, GRID)) <= TAIL
        )
        if k != n
        else GRID
    )


@pytest.mark.parametrize(
    ("verified", "attempts", "expected"),
    [
        (0, 1, (Fraction(0), Fraction(1997, 2048))),
        (1, 1, (Fraction(51, 2048), Fraction(1))),
        (0, 10, (Fraction(0), Fraction(79, 256))),
        (5, 10, (Fraction(383, 2048), Fraction(1665, 2048))),
        (10, 10, (Fraction(177, 256), Fraction(1))),
    ],
)
def test_known_clopper_pearson_rational_outer_bounds(
    verified: int,
    attempts: int,
    expected: tuple[Fraction, Fraction],
) -> None:
    """Published endpoints bound exact binomial-tail inversions outward."""
    observed = success_intervals.success_interval_95(verified, attempts)
    assert observed is not None
    assert Fraction(*observed["lower"]) == expected[0]
    assert Fraction(*observed["upper"]) == expected[1]
    assert observed["sample_count"] == attempts
    assert observed["verified"] == verified


@pytest.mark.parametrize(("n", "k"), [(1, 0), (1, 1), (3, 1), (6, 3)])
def test_grid_endpoints_match_exhaustive_independent_fraction_reference(
    n: int,
    k: int,
) -> None:
    """Full-grid oracle verifies both one-sided tail directions."""
    observed = success_intervals.success_interval_95(k, n)
    assert observed is not None
    assert Fraction(*observed["lower"]) == Fraction(
        _reference_grid_bound(n, k, lower=True),
        GRID,
    )
    assert Fraction(*observed["upper"]) == Fraction(
        _reference_grid_bound(n, k, lower=False),
        GRID,
    )


def test_binomial_bounds_are_symmetric_in_success_failure_exchange() -> None:
    """Reversing the Bernoulli event complements both endpoints exactly."""
    for attempts in (1, 2, 7, 10, 21):
        for verified in range(attempts + 1):
            left = success_intervals.success_interval_95(verified, attempts)
            right = success_intervals.success_interval_95(
                attempts - verified, attempts
            )
            assert left is not None
            assert right is not None
            assert Fraction(*left["lower"]) == 1 - Fraction(*right["upper"])
            assert Fraction(*left["upper"]) == 1 - Fraction(*right["lower"])


def test_lower_upper_bounds_monotone_in_success_count() -> None:
    """More reported successes cannot lower both confidence endpoints."""
    intervals = [
        success_intervals.success_interval_95(k, 15) for k in range(16)
    ]
    assert all(interval is not None for interval in intervals)
    for left, right in pairwise(intervals):
        assert left is not None
        assert right is not None
        assert Fraction(*left["lower"]) <= Fraction(*right["lower"])
        assert Fraction(*left["upper"]) <= Fraction(*right["upper"])


def test_maximum_sample_bound_and_above_limit() -> None:
    """Bounded exact large-n results avoid silent overflow or extrapolation."""
    limit = success_intervals.MAX_ATTEMPTS
    observed = success_intervals.success_interval_95(limit // 2, limit)
    assert observed is not None
    assert Fraction(*observed["lower"]) < Fraction(1, 2)
    assert Fraction(*observed["upper"]) > Fraction(1, 2)
    assert success_intervals.success_interval_95(0, limit + 1) is None


@pytest.mark.parametrize(
    ("verified", "attempts"),
    [(0, 0), (1, 0), (-1, 2), (3, 2), (True, 2), (1, False), (1.5, 2)],
)
def test_invalid_or_empty_bernoulli_population_produces_no_interval(
    verified: int,
    attempts: int,
) -> None:
    """Unsupported raw values cannot masquerade as a success-rate bound."""
    assert success_intervals.success_interval_95(verified, attempts) is None
