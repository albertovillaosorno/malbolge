# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
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

# Fixed inference geometry must not follow mutable public aliases.
_SOURCE_MAX_ATTEMPTS = MAX_ATTEMPTS
_SOURCE_GRID_DENOMINATOR = GRID_DENOMINATOR
_SOURCE_TWO_SIDED_TAIL_DENOMINATOR = TWO_SIDED_TAIL_DENOMINATOR
_SOURCE_FRACTION = Fraction
_SOURCE_COMB = comb
_SOURCE_TYPE = type
_SOURCE_INT = int
_SOURCE_RANGE = range
_SOURCE_SUM = sum


class SuccessInterval(TypedDict):
    """Conservatively rounded exact binomial success probability interval."""

    lower: list[int]
    upper: list[int]
    sample_count: int
    verified: int


_SOURCE_SUCCESS_INTERVAL = SuccessInterval


def _binomial_lower_tail_numerator(n: int, k: int, p: int) -> int:
    total = _SOURCE_GRID_DENOMINATOR**n
    q = _SOURCE_GRID_DENOMINATOR - p
    if k < n // 2:
        return _SOURCE_SUM(
            _SOURCE_COMB(n, i) * p**i * q ** (n - i) for i in _SOURCE_RANGE(k + 1)
        )
    return total - _SOURCE_SUM(
        _SOURCE_COMB(n, i) * p**i * q ** (n - i) for i in _SOURCE_RANGE(k + 1, n + 1)
    )


_SOURCE_BINOMIAL_LOWER_TAIL_NUMERATOR = _binomial_lower_tail_numerator


def _inverted_lower(n: int, k: int) -> int:
    if k == 0:
        return 0
    low, high = 0, _SOURCE_GRID_DENOMINATOR
    threshold = _SOURCE_GRID_DENOMINATOR**n
    while high - low > 1:
        midpoint = (low + high) // 2
        upper_tail = threshold - _SOURCE_BINOMIAL_LOWER_TAIL_NUMERATOR(
            n, k - 1, midpoint
        )
        if _SOURCE_TWO_SIDED_TAIL_DENOMINATOR * upper_tail <= threshold:
            low = midpoint
        else:
            high = midpoint
    return low


def _inverted_upper(n: int, k: int) -> int:
    if k == n:
        return _SOURCE_GRID_DENOMINATOR
    low, high = 0, _SOURCE_GRID_DENOMINATOR
    threshold = _SOURCE_GRID_DENOMINATOR**n
    while high - low > 1:
        midpoint = (low + high) // 2
        lower_tail = _SOURCE_BINOMIAL_LOWER_TAIL_NUMERATOR(n, k, midpoint)
        if _SOURCE_TWO_SIDED_TAIL_DENOMINATOR * lower_tail <= threshold:
            high = midpoint
        else:
            low = midpoint
    return high


_SOURCE_INVERTED_LOWER = _inverted_lower
_SOURCE_INVERTED_UPPER = _inverted_upper


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
    if (
        _SOURCE_TYPE(verified) is not _SOURCE_INT
        or _SOURCE_TYPE(attempts) is not _SOURCE_INT
    ):
        return None
    if attempts < 1 or attempts > _SOURCE_MAX_ATTEMPTS or not 0 <= verified <= attempts:
        return None
    lower = _SOURCE_FRACTION(
        _SOURCE_INVERTED_LOWER(attempts, verified), _SOURCE_GRID_DENOMINATOR
    )
    upper = _SOURCE_FRACTION(
        _SOURCE_INVERTED_UPPER(attempts, verified), _SOURCE_GRID_DENOMINATOR
    )
    return _SOURCE_SUCCESS_INTERVAL(
        lower=[lower.numerator, lower.denominator],
        upper=[upper.numerator, upper.denominator],
        sample_count=attempts,
        verified=verified,
    )
