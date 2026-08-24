# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Independent exhaustive evidence for classic rotate minimal periods.
# - Must-Not:
#   - Import production rotate helpers or claim unchanged state across writes.
# - Allows:
#   - Inputs: every classic ten-trit word and finite rotate visit counts.
#   - Outputs: exact period-class and canonical-residue assertions.
#   - Side effects: none.
# - Split-When:
#   - Another state canonicalization needs independent executable state.
# - Merge-When:
#   - A shared rotation proof owns the same exhaustive period classification.
# - Summary:
#   - Prove exact minimal rotate periods for every classic word.
# - Description:
#   - Classifies all classic words and checks residue canonicalization exactly.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Applies only to repeated rotate visits with no intervening cell writes.
#

"""Independent evidence for exact classic rotate minimal periods."""

from __future__ import annotations

from collections import Counter

_RADIX = 3
_TRITS = 10
_DOMAIN = 59_049
_HIGH_PLACE = 19_683
_PERIODS = (1, 2, 5, 10)
_EXPECTED_PERIOD_COUNTS = {1: 3, 2: 6, 5: 240, 10: 58_800}


def _rotate(word: int) -> int:
    return (word // _RADIX) + ((word % _RADIX) * _HIGH_PLACE)


def _rotate_n(word: int, visits: int) -> int:
    result = word
    for _ in range(visits):
        result = _rotate(result)
    return result


def _minimal_period(word: int) -> int:
    for period in _PERIODS:
        if _rotate_n(word, period) == word:
            return period
    raise AssertionError


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def test_classic_rotate_minimal_period_partition_is_exact() -> None:
    """Every classic word belongs to one exact divisor-of-ten period class."""
    counts = Counter(_minimal_period(word) for word in range(_DOMAIN))
    assert dict(sorted(counts.items())) == _EXPECTED_PERIOD_COUNTS
    assert counts[1] == _integer_power(_RADIX, 1)
    assert counts[2] == _integer_power(_RADIX, 2) - counts[1]
    assert counts[5] == _integer_power(_RADIX, 5) - counts[1]
    assert counts[10] == _DOMAIN - counts[1] - counts[2] - counts[5]
    assert sum(counts.values()) == _DOMAIN


def test_classic_rotate_uses_each_words_minimal_period_residue() -> None:
    """Two full ten-visit cycles reduce exactly modulo each word's period."""
    for word in range(_DOMAIN):
        period = _minimal_period(word)
        for visits in range((2 * _TRITS) + 1):
            assert _rotate_n(word, visits) == _rotate_n(word, visits % period)
