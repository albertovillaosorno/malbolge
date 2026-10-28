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
#   - Exact conditional two-sided sign tests for matched discordant trials.
# - Must-Not:
#   - Infer replicate independence, attest correctness, or rank algorithms.
# - Allows:
#   - Inputs: integer counts of paired outcomes on either side of a null tie.
#   - Outputs: exact rational uncorrected two-sided conditional p-values.
#   - Side effects: none.
# - Split-When:
#   - An independent statistical test needs a separately named contract.
# - Merge-When:
#   - One guarded research-statistics port owns these binomial calculations.
# - Summary:
#   - Tests asymmetry without rounding or treating ties as wins.
# - Description:
#   - Uses the complete exact binomial tail conditioned on discordance.
# - Usage:
#   - Called by the optional arena --paired-exact-tests report view.
# - Defaults:
#   - No discordance or more than 4096 discordant pairs gives no p-value.
#

"""Exact two-sided conditional-binomial comparisons of paired outcomes."""

from __future__ import annotations

from fractions import Fraction
from typing import TypedDict

MAX_DISCORDANT_PAIRS = 4096


class PairedExactTest(TypedDict):
    """Unadjusted exact paired sign asymmetry with ties excluded."""

    discordant_pairs: int
    p_two_sided: list[int]


def _valid_count(value: int) -> bool:
    return type(value) is int and value >= 0


def two_sided_sign_test(left: int, right: int) -> PairedExactTest | None:
    """Compare matched discordant outcomes against symmetric signs.

    Condition on the number of discordant pairs and use the exact two-sided
    binomial tail under a conditional null probability of one half per side.
    For a McNemar-type paired verification test, left/right count baseline-only
    and candidate-only successes. For cost comparisons, they count candidate
    lower/higher among pairs in which both verified. Ties are excluded.

    Results require independent paired trials for inferential interpretation.
    This function only computes the exact null probability and cannot verify
    that assumption, establish a verifier verdict, or correct multiple tests.

    Returns:
        Exact reduced probability fraction or None for unavailable comparisons.

    """
    if not _valid_count(left) or not _valid_count(right):
        return None
    size = left + right
    if size == 0 or size > MAX_DISCORDANT_PAIRS:
        return None
    smaller = min(left, right)
    denominator = 1 << size
    tail = 0
    binomial = 1
    for index in range(smaller + 1):
        tail += binomial
        binomial = binomial * (size - index) // (index + 1)
    probability = min(Fraction(1), Fraction(2 * tail, denominator))
    return PairedExactTest(
        discordant_pairs=size,
        p_two_sided=[probability.numerator, probability.denominator],
    )
