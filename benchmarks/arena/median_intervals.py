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
#   - Exact finite-sample nonparametric median interval calculations.
# - Must-Not:
#   - Authenticate measurements, assume independence, or rank algorithms.
# - Allows:
#   - Inputs: bounded collections of exact integer trial costs.
#   - Outputs: coverage-exact order-statistic median intervals or no interval.
#   - Side effects: none.
# - Split-When:
#   - Other statistical estimands require separate inference contracts.
# - Merge-When:
#   - A governed statistics boundary subsumes exact median intervals.
# - Summary:
#   - Exposes conservative 95% median uncertainty without float rounding.
# - Description:
#   - Binomial order statistics give guaranteed iid-continuous-median coverage.
# - Usage:
#   - Opt-in through the arena analyzer's --median-intervals-95 flag.
# - Defaults:
#   - Fewer than six or more than 4096 samples yield no interval.
#

"""Bounded exact 95% order-statistic intervals for an iid sample median."""

from __future__ import annotations

from fractions import Fraction
from typing import TypedDict

MIN_SAMPLES = 6
MAX_SAMPLES = 4096
REQUESTED_CONFIDENCE = Fraction(19, 20)


class MedianInterval(TypedDict):
    """Exact attainable sample-median confidence interval."""

    lower: int
    upper: int
    coverage: list[int]
    sample_count: int


def median_interval_95(values: list[int]) -> MedianInterval | None:
    """Find the shortest rank-symmetric interval with coverage >= 95%.

    This calculation assumes independent, identically distributed draws and
    makes no claim about whether the caller's trials satisfy that assumption.
    For distributions with atoms at the median, binomial symmetry gives a
    conservative lower bound on coverage. For too few samples there is no
    finite interval with the requested worst-case coverage from observed
    order statistics alone.

    Returns:
        Exact integer order-statistic endpoints and rational lower coverage,
        or None for invalid integer samples or sizes outside the bounded domain.

    """
    if type(values) is not list:
        return None
    size = len(values)
    if size < MIN_SAMPLES or size > MAX_SAMPLES:
        return None
    if any(type(value) is not int for value in values):
        return None
    denominator = 1 << size
    tail = 0
    binomial = 1
    rank = 0
    # Coverage [X_(k), X_(n-k+1)] = 1 - 2 * P(Bin(n, 1/2) < k).
    # Recurrence uses exact integer arithmetic without enormous factorials.
    for j in range(size // 2):
        proposed_tail = tail + binomial
        if proposed_tail * 2 * REQUESTED_CONFIDENCE.denominator > (
            denominator
            * (REQUESTED_CONFIDENCE.denominator - REQUESTED_CONFIDENCE.numerator)
        ):
            break
        rank = j + 1
        tail = proposed_tail
        binomial = binomial * (size - j) // (j + 1)
    if rank == 0:
        return None
    exact_coverage = Fraction(denominator - 2 * tail, denominator)
    ordered = sorted(values)
    return MedianInterval(
        lower=ordered[rank - 1],
        upper=ordered[-rank],
        coverage=[exact_coverage.numerator, exact_coverage.denominator],
        sample_count=size,
    )
