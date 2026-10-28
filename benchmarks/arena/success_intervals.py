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
#   - Exact binomial-tail inversion for conservative success-probability bounds.
# - Must-Not:
#   - Authenticate outcomes, assert independence, or rank algorithms.
# - Allows:
#   - Inputs: bounded nonnegative successes and total Bernoulli trial counts.
#   - Outputs: outward rational-grid 95% Clopper-Pearson interval bounds.
#   - Side effects: none.
# - Split-When:
#   - Additional confidence policies require separately reviewed methods.
# - Merge-When:
#   - A research statistics port owns exact binomial inversion.
# - Summary:
#   - Describes reported reliability without normal approximations.
# - Description:
#   - Inverts two-sided 1/40 binomial tails with exact integer arithmetic.
# - Usage:
#   - Arena --success-intervals-95, not a guest execution verifier.
# - Defaults:
#   - No observations or >512 attempts yield no inferential interval.
#

"""Outward exact-grid 95% Clopper-Pearson confidence bounds for successes."""

from __future__ import annotations

from fractions import Fraction
from math import comb
from typing import TypedDict

MAX_ATTEMPTS = 512
GRID_DENOMINATOR = 4096
TWO_SIDED_TAIL_DENOMINATOR = 40


class SuccessInterval(TypedDict):
    """Conservatively rounded exact binomial success probability interval."""

    lower: list[int]
    upper: list[int]
    sample_count: int
    verified: int


def _binomial_lower_tail_numerator(n: int, k: int, p: int) -> int:
    total = GRID_DENOMINATOR**n
    q = GRID_DENOMINATOR - p
    if k < n // 2:
        return sum(comb(n, i) * p**i * q ** (n - i) for i in range(k + 1))
    return total - sum(
        comb(n, i) * p**i * q ** (n - i) for i in range(k + 1, n + 1)
    )


def _inverted_lower(n: int, k: int) -> int:
    if k == 0:
        return 0
    low, high = 0, GRID_DENOMINATOR
    threshold = GRID_DENOMINATOR**n
    while high - low > 1:
        midpoint = (low + high) // 2
        upper_tail = threshold - _binomial_lower_tail_numerator(
            n, k - 1, midpoint
        )
        if TWO_SIDED_TAIL_DENOMINATOR * upper_tail <= threshold:
            low = midpoint
        else:
            high = midpoint
    return low


def _inverted_upper(n: int, k: int) -> int:
    if k == n:
        return GRID_DENOMINATOR
    low, high = 0, GRID_DENOMINATOR
    threshold = GRID_DENOMINATOR**n
    while high - low > 1:
        midpoint = (low + high) // 2
        lower_tail = _binomial_lower_tail_numerator(n, k, midpoint)
        if TWO_SIDED_TAIL_DENOMINATOR * lower_tail <= threshold:
            high = midpoint
        else:
            low = midpoint
    return high


def success_interval_95(verified: int, attempts: int) -> SuccessInterval | None:
    """Conservatively enclose the two-sided 95% binomial confidence interval.

    Every tail comparison is exact integer arithmetic on a 1/4096 grid.
    Outward-rounded endpoints preserve at least the nominal Clopper-Pearson
    coverage assuming independent identically distributed Bernoulli attempts.
    The grid endpoints are exact rationals; the underlying root generally is
    irrational and is *not* claimed to be represented exactly.

    Returns:
        Exact rational outward bounds or no result for unsupported counts.

    """
    if type(verified) is not int or type(attempts) is not int:
        return None
    if attempts < 1 or attempts > MAX_ATTEMPTS or not 0 <= verified <= attempts:
        return None
    lower = Fraction(_inverted_lower(attempts, verified), GRID_DENOMINATOR)
    upper = Fraction(_inverted_upper(attempts, verified), GRID_DENOMINATOR)
    return SuccessInterval(
        lower=[lower.numerator, lower.denominator],
        upper=[upper.numerator, upper.denominator],
        sample_count=attempts,
        verified=verified,
    )
