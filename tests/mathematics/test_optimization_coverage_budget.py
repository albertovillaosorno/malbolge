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
#   - Independent executable correspondence for exact crazy coverage budgets.
# - Must-Not:
#   - Import production crazy-target planning helpers or claim runtime speedup.
# - Allows:
#   - Inputs: checked trit widths one through fourteen and exact class bounds.
#   - Outputs: exact cumulative reachable-pair coverage threshold assertions.
#   - Side effects: none.
# - Split-When:
#   - Another optimization equation needs independent executable state.
# - Merge-When:
#   - A shared mathematical correspondence test owns the same threshold proof.
# - Summary:
#   - Verify exact minimum complete-preimage budgets by independent convolution.
# - Description:
#   - Inverts reachable-pair multiplicity classes at every discrete boundary.
# - Usage:
#   - Referenced by the mathematical correspondence manifest.
# - Defaults:
#   - Widths are checked only across the admitted one-through-fourteen family.
#

"""Independent evidence for exact crazy reachable-pair coverage budgets."""

from __future__ import annotations

_MAXIMUM_TRITS = 14
_RADIX = 3
_INDEPENDENT_CRAZY_TRIT = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)


def _independent_trit_classes() -> tuple[tuple[int, int], ...]:
    classes: dict[int, int] = {}
    for accumulator in range(_RADIX):
        for target in range(_RADIX):
            multiplicity = sum(
                row[accumulator] == target
                for row in _INDEPENDENT_CRAZY_TRIT
            )
            if multiplicity > 0:
                classes[multiplicity] = classes.get(multiplicity, 0) + 1
    return tuple(sorted(classes.items()))


def _independent_histogram(trit_count: int) -> dict[int, int]:
    counts = {1: 1}
    for _ in range(trit_count):
        expanded: dict[int, int] = {}
        for preimages, pairs in counts.items():
            for multiplicity, trit_pairs in _independent_trit_classes():
                combined = preimages * multiplicity
                expanded[combined] = (
                    expanded.get(combined, 0) + pairs * trit_pairs
                )
        counts = expanded
    return counts


def _integer_binomial(total: int, selected: int) -> int:
    if selected < 0 or selected > total:
        return 0
    selected = min(selected, total - selected)
    result = 1
    for index in range(1, selected + 1):
        result *= total - index + 1
        result //= index
    return result


def _integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def _closed_form_class_count(trit_count: int, exponent: int) -> int:
    return (
        _integer_binomial(trit_count, exponent)
        * _integer_power(2, exponent)
        * _integer_power(5, trit_count - exponent)
    )


def _minimum_budget_for_coverage(
    trit_count: int,
    requested_pairs: int,
) -> int:
    if requested_pairs == 0:
        return 0
    cumulative = 0
    for exponent in range(trit_count + 1):
        cumulative += _closed_form_class_count(trit_count, exponent)
        if cumulative >= requested_pairs:
            return 1 << exponent
    raise AssertionError


def test_profile_width_minimum_coverage_budget_matches_independent_classes(
) -> None:
    """Every class boundary has the exact least complete-preimage budget."""
    assert _independent_trit_classes() == ((1, 5), (2, 2))
    for trit_count in range(1, _MAXIMUM_TRITS + 1):
        histogram = _independent_histogram(trit_count)
        assert _minimum_budget_for_coverage(trit_count, 0) == 0
        cumulative = 0
        for exponent in range(trit_count + 1):
            budget = 1 << exponent
            independent_count = histogram[budget]
            assert independent_count == _closed_form_class_count(
                trit_count,
                exponent,
            )
            previous = cumulative
            cumulative += independent_count
            assert _minimum_budget_for_coverage(
                trit_count,
                previous + 1,
            ) == budget
            assert _minimum_budget_for_coverage(
                trit_count,
                cumulative,
            ) == budget
        assert cumulative == _integer_power(7, trit_count)


def _independent_coverage(histogram: dict[int, int], budget: int) -> int:
    return sum(
        pairs
        for preimages, pairs in histogram.items()
        if preimages <= budget
    )


def _closed_form_coverage(trit_count: int, budget: int) -> int:
    return sum(
        _closed_form_class_count(trit_count, exponent)
        for exponent in range(trit_count + 1)
        if (1 << exponent) <= budget
    )


def test_profile_width_coverage_changes_only_at_power_of_two_budgets() -> None:
    """Every integer budget matches the exact independent class coverage."""
    for trit_count in range(1, _MAXIMUM_TRITS + 1):
        histogram = _independent_histogram(trit_count)
        maximum_budget = 1 << trit_count
        for budget in range(maximum_budget + 1):
            assert _independent_coverage(histogram, budget) == (
                _closed_form_coverage(trit_count, budget)
            )
