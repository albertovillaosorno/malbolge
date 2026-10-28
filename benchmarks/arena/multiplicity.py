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
#   - Exact Holm multiplicity adjustment over one declared test family.
# - Must-Not:
#   - Change null hypotheses, certify samples, or select the Pareto frontier.
# - Allows:
#   - Inputs: exact rational conditional-binomial p-values in one study.
#   - Outputs: exact rational monotone adjusted p-values in input order.
#   - Side effects: none.
# - Split-When:
#   - Additional correction procedures require separately identified policy.
# - Merge-When:
#   - A trusted statistical evidence port owns the same correction.
# - Summary:
#   - Controls family-wise error under arbitrarily dependent valid p-values.
# - Description:
#   - Applies step-down Holm-Bonferroni in exact rational arithmetic.
# - Usage:
#   - Called only by the explicit --adjust-paired-tests arena option.
# - Defaults:
#   - Empty families yield an empty list; no significance decision is made.
#

"""Exact Holm-Bonferroni correction for a predeclared family of p-values."""

from __future__ import annotations

from fractions import Fraction
from operator import itemgetter


def holm_adjusted(p_values: list[Fraction]) -> list[Fraction]:
    """Return step-down Holm-adjusted p-values in original input order.

    The input must consist of valid unadjusted p-values for the same
    predeclared family. This operation does not assert whether individual
    test null assumptions hold. Holm controls family-wise error under
    arbitrary dependence between valid marginal p-values.

    Returns:
        Exact adjusted probabilities between each raw p-value and one.

    Raises:
        ValueError: A caller supplied a probability outside [0, 1].

    """
    if any(value < 0 or value > 1 for value in p_values):
        message = "Holm adjustment requires probabilities in [0, 1]"
        raise ValueError(message)
    count = len(p_values)
    adjusted = [Fraction(1)] * count
    current = Fraction(0)
    for rank, (index, raw) in enumerate(
        sorted(enumerate(p_values), key=itemgetter(1, 0))
    ):
        current = max(current, min(Fraction(1), (count - rank) * raw))
        adjusted[index] = current
    return adjusted
