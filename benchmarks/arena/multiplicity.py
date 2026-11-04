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

# Preserve the exact rational domain and rank order if public aliases change.
_CANONICAL_FRACTION = Fraction
_CANONICAL_ITEMGETTER = itemgetter
# A shared mutable ranking/arithmetic alias cannot define accepted p-values.
_SOURCE_SORTED = sorted
_SOURCE_ENUMERATE = enumerate
_SOURCE_MIN = min
_SOURCE_MAX = max
_SOURCE_ANY = any
_SOURCE_LEN = len
# Preserve the native family and per-value shapes under module substitutions.
_SOURCE_TYPE = type
_SOURCE_LIST = list
_SOURCE_VALUE_ERROR = ValueError


def holm_adjusted(p_values: list[Fraction]) -> list[Fraction]:
    """Return step-down Holm-adjusted p-values in original input order.

    The input must consist of valid unadjusted p-values for the same
    predeclared family. This operation does not assert whether individual
    test null assumptions hold. Holm controls family-wise error under
    arbitrary dependence between valid marginal p-values.

    Returns:
        Exact adjusted probabilities between each raw p-value and one.

    Raises:
        ValueError: A caller supplied a non-Fraction or out-of-range value.

    """
    if _SOURCE_TYPE(p_values) is not _SOURCE_LIST or _SOURCE_ANY(
        _SOURCE_TYPE(value) is not _CANONICAL_FRACTION or not 0 <= value <= 1
        for value in p_values
    ):
        message = "Holm adjustment requires exact rational probabilities in [0, 1]"
        raise _SOURCE_VALUE_ERROR(message)
    count = _SOURCE_LEN(p_values)
    adjusted = [_CANONICAL_FRACTION(1)] * count
    current = _CANONICAL_FRACTION(0)
    for rank, (index, raw) in _SOURCE_ENUMERATE(
        _SOURCE_SORTED(_SOURCE_ENUMERATE(p_values), key=_CANONICAL_ITEMGETTER(1, 0))
    ):
        current = _SOURCE_MAX(
            current, _SOURCE_MIN(_CANONICAL_FRACTION(1), (count - rank) * raw)
        )
        adjusted[index] = current
    return adjusted
