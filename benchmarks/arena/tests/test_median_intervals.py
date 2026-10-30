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
#   - Independent finite-sample order-statistic interval regressions.
# - Must-Not:
#   - Treat synthetic, dependent, or unverified trials as real evidence.
# - Allows:
#   - Inputs: deterministic adversarial integers and binomial reference cases.
#   - Outputs: exact endpoint and rational coverage assertions.
#   - Side effects: none.
# - Split-When:
#   - Another interval family gains its own statistical validity contract.
# - Merge-When:
#   - The governing arena test suite owns the same reference checks.
# - Summary:
#   - Verifies exact median intervals independently of the recurrence.
# - Description:
#   - Covers insufficient data, ties, boundaries, huge costs and rank choices.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_median_intervals.py`.
# - Defaults:
#   - No interval implies no inferential claim.
#

"""Independent combinatorial checks of opt-in median uncertainty bounds."""

# ruff: file-ignore[assert]

from __future__ import annotations

from fractions import Fraction
from math import comb
from typing import cast

import pytest

from benchmarks.arena import median_intervals

TARGET = Fraction(19, 20)
TIED_SAMPLE = 7


def _reference(values: list[int]) -> tuple[int, int, Fraction] | None:
    """Compute all candidate tail probabilities independently via comb().

    Returns:
        Tightest symmetric observed ranks meeting the requested coverage.

    """
    size = len(values)
    if size < median_intervals.MIN_SAMPLES:
        return None
    for rank in range(size // 2, 0, -1):
        tail = sum(comb(size, k) for k in range(rank))
        confidence = Fraction((1 << size) - 2 * tail, 1 << size)
        if confidence >= TARGET:
            sorted_values = sorted(values)
            return sorted_values[rank - 1], sorted_values[-rank], confidence
    return None


@pytest.mark.parametrize("sample_count", [0, 1, 2, 3, 4, 5])
def test_fewer_than_six_observations_cannot_prove_95_percent(
    sample_count: int,
) -> None:
    """Even the full observed min-max interval undercovers at n <= 5."""
    assert median_intervals.median_interval_95(list(range(sample_count))) is None


@pytest.mark.parametrize("sample_count", [6, 7, 8, 9, 10, 11, 20, 99, 100])
def test_rank_interval_agrees_with_independent_binomial_reference(
    sample_count: int,
) -> None:
    """Exact binomial coverage and rank choice agree without floats."""
    values = list(range(sample_count))
    expected = _reference(values)
    assert expected is not None
    observed = median_intervals.median_interval_95(values)
    assert observed is not None
    assert (observed["lower"], observed["upper"]) == expected[:2]
    assert Fraction(*observed["coverage"]) == expected[2]
    assert observed["sample_count"] == sample_count
    assert Fraction(*observed["coverage"]) >= TARGET


def test_95_percent_interval_is_not_achievable_for_five_samples() -> None:
    """Reference probability confirms why n=5 cannot publish an interval."""
    size = 5
    assert Fraction((1 << size) - 2, 1 << size) < TARGET
    assert _reference(list(range(size))) is None


def test_six_sample_interval_is_min_max_with_exact_31_over_32() -> None:
    """Prevent one-tail rather than two-tail confidence miscalculation."""
    observed = median_intervals.median_interval_95([1, 2, 3, 4, 5, 6])
    assert observed == {
        "lower": 1,
        "upper": 6,
        "coverage": [31, 32],
        "sample_count": 6,
    }


def test_ten_sample_interval_moves_inside_observed_extremes() -> None:
    """Reject arbitrarily wide intervals once narrower ranks are available."""
    observed = median_intervals.median_interval_95(list(range(10)))
    assert observed == {
        "lower": 1,
        "upper": 8,
        "coverage": [501, 512],
        "sample_count": 10,
    }


def test_tied_measurements_do_not_invent_uncertainty() -> None:
    """An atomic observed distribution can have identical endpoints."""
    observed = median_intervals.median_interval_95([TIED_SAMPLE] * 10)
    assert observed is not None
    assert observed["lower"] == observed["upper"] == TIED_SAMPLE
    assert Fraction(*observed["coverage"]) >= TARGET


def test_signed_large_sample_costs_remain_exact_and_order_invariant() -> None:
    """Paired differences can be negative and arbitrarily wider than f64."""
    huge = 2**90
    values = [huge + k for k in range(10)]
    values[0] = -huge
    expected = median_intervals.median_interval_95(values)
    assert expected is not None
    assert expected["lower"] == huge + 1
    assert expected["upper"] == huge + 8
    values.reverse()
    assert median_intervals.median_interval_95(values) == expected


def test_bounded_maximum_and_one_above_limit() -> None:
    """Huge repetitions do not force unbounded binomial arithmetic."""
    within = list(range(median_intervals.MAX_SAMPLES))
    observed = median_intervals.median_interval_95(within)
    assert observed is not None
    assert Fraction(*observed["coverage"]) >= TARGET
    within.append(median_intervals.MAX_SAMPLES)
    assert median_intervals.median_interval_95(within) is None


@pytest.mark.parametrize(
    "invalid",
    [True, 6.0, float("nan"), float("inf"), "6", None, Fraction(6)],
)
def test_noninteger_costs_never_produce_inferential_interval(
    invalid: object,
) -> None:
    """Malformed reported costs cannot become numeric median evidence."""
    values = cast("list[int]", [1, 2, 3, 4, 5, invalid])
    assert median_intervals.median_interval_95(values) is None


def test_median_interval_rejects_non_list_collection() -> None:
    """A malformed direct call cannot leak untyped collection errors."""
    values = cast("list[int]", (1, 2, 3, 4, 5, 6))
    assert median_intervals.median_interval_95(values) is None
