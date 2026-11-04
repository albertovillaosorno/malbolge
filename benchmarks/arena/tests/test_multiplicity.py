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
#   - Independent exact Holm correction and regression checks.
# - Must-Not:
#   - Infer significance or authenticate the input p-values.
# - Allows:
#   - Inputs: synthetic test probabilities, ties, and bounded exact fractions.
#   - Outputs: assertions on monotone adjusted values in original order.
#   - Side effects: none.
# - Split-When:
#   - A different family-wise or false-discovery method needs separate tests.
# - Merge-When:
#   - A single statistics test boundary includes these Holm references.
# - Summary:
#   - Guards against rank-order, tie, and floating adjustment defects.
# - Description:
#   - Exercises independent manual examples and invariant enumerations.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_multiplicity.py`.
# - Defaults:
#   - Empty test families produce empty results.
#

"""Synthetic regression checks for exact Holm family-wise adjustment."""

# ruff: file-ignore[assert]

from __future__ import annotations

from fractions import Fraction
from itertools import product
from operator import itemgetter
from typing import Never, cast

import pytest

from benchmarks.arena import multiplicity


@pytest.mark.parametrize(
    ("raw", "adjusted"),
    [
        ([], []),
        ([Fraction(1, 100)], [Fraction(1, 100)]),
        (
            [
                Fraction(1, 2),
                Fraction(1, 100),
                Fraction(1, 20),
                Fraction(1, 25),
            ],
            [Fraction(1, 2), Fraction(1, 25), Fraction(3, 25), Fraction(3, 25)],
        ),
        (
            [Fraction(1, 20), Fraction(1, 20), Fraction(1, 2)],
            [Fraction(3, 20), Fraction(3, 20), Fraction(1, 2)],
        ),
        ([Fraction(0), Fraction(1)], [Fraction(0), Fraction(1)]),
        ([Fraction(1, 2)] * 3, [Fraction(1)] * 3),
    ],
)
def test_known_holm_examples_preserve_input_order_and_exact_fractions(
    raw: list[Fraction],
    adjusted: list[Fraction],
) -> None:
    """Compare with manually computed two-sided multiple-test examples."""
    assert multiplicity.holm_adjusted(raw) == adjusted


def test_holm_monotonicity_and_uncorrected_lower_bound_for_small_families() -> None:
    """Small exact fractions never become smaller after correction."""
    candidates = [Fraction(0), Fraction(1, 10), Fraction(1, 2), Fraction(1)]
    for sample in product(candidates, repeat=4):
        adjusted = multiplicity.holm_adjusted(list(sample))
        assert all(
            left <= right <= 1 for left, right in zip(sample, adjusted, strict=True)
        )
        ordered = sorted(zip(sample, adjusted, strict=True), key=itemgetter(0))
        assert all(
            ordered[index][1] <= ordered[index + 1][1]
            for index in range(len(ordered) - 1)
        )


def test_equal_raw_p_values_get_equal_adjustment() -> None:
    """Tie-breaking is deterministic but never changes tied conclusions."""
    raw = [Fraction(1, 40), Fraction(1, 40), Fraction(1, 40), Fraction(1)]
    result = multiplicity.holm_adjusted(raw)
    assert result[:3] == [Fraction(1, 10)] * 3
    assert result[3] == 1


def test_large_integer_fractions_do_not_round_to_equal_floats() -> None:
    """Exact high-precision probabilities retain strict ordering when needed."""
    large = 2**100
    raw = [Fraction(large + 1, 2 * large), Fraction(1, large)]
    assert multiplicity.holm_adjusted(raw) == [raw[0], Fraction(2, large)]


@pytest.mark.parametrize("bad", [Fraction(-1, 10), Fraction(11, 10)])
def test_invalid_probability_fails_closed(bad: Fraction) -> None:
    """Caller bugs must not produce a purported correction from invalid p."""
    with pytest.raises(ValueError, match="Holm adjustment requires"):
        multiplicity.holm_adjusted([Fraction(1, 5), bad])


@pytest.mark.parametrize(
    "invalid",
    [0, True, 0.05, float("nan"), float("inf"), "0.05", None],
)
def test_non_rational_probability_rejects_without_adjustment(
    invalid: object,
) -> None:
    """Do not convert untrusted or nonfinite values into exact p-values."""
    probabilities = cast("list[Fraction]", [Fraction(1, 20), invalid])
    with pytest.raises(ValueError, match="exact rational probabilities"):
        multiplicity.holm_adjusted(probabilities)


def test_holm_rejects_integer_probabilities_after_fraction_alias_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rebinding the module's Fraction alias cannot admit integer p-values."""
    monkeypatch.setattr(multiplicity, "Fraction", int)
    with pytest.raises(ValueError, match="exact rational probabilities"):
        multiplicity.holm_adjusted(cast("list[Fraction]", [0, 1]))


def test_holm_preserves_exact_ranking_after_sort_key_provider_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced sort-key helper cannot reorder the Holm test family."""
    probabilities = [
        Fraction(1, 2),
        Fraction(1, 100),
        Fraction(1, 20),
        Fraction(1, 25),
    ]
    monkeypatch.setattr(multiplicity, "itemgetter", lambda *_: lambda _item: 0)
    assert multiplicity.holm_adjusted(probabilities) == [
        Fraction(1, 2),
        Fraction(1, 25),
        Fraction(3, 25),
        Fraction(3, 25),
    ]


def test_holm_rejects_non_list_collection() -> None:
    """A malformed direct call must raise a typed admission failure."""
    probabilities = cast("list[Fraction]", (Fraction(1, 20),))
    with pytest.raises(ValueError, match="exact rational probabilities"):
        multiplicity.holm_adjusted(probabilities)


@pytest.mark.parametrize("provider", ["sorted", "enumerate", "min", "max"])
def test_holm_native_math_cannot_be_rebound_to_forge_adjustment(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    """Shared mutable arithmetic aliases must not alter exact Holm ranks."""
    raw = [Fraction(1, 2), Fraction(1, 100), Fraction(1, 20), Fraction(1, 25)]
    expected = multiplicity.holm_adjusted(raw)

    def leave_unsorted(values: object, *, key: object) -> list[object]:
        del key
        return list(cast("list[object]", values))

    def forge_zero(*_values: object) -> Fraction:
        return Fraction(0)

    def forge_enumeration(values: object) -> object:
        members = list(cast("list[object]", values))
        if members and type(members[0]) is Fraction:
            members = [Fraction(0)] * len(members)
        return enumerate(members)

    if provider == "sorted":
        replacement = leave_unsorted
    elif provider == "enumerate":
        replacement = forge_enumeration
    else:
        replacement = forge_zero
    monkeypatch.setattr(multiplicity, provider, replacement, raising=False)
    assert multiplicity.holm_adjusted(raw) == expected


@pytest.mark.parametrize(
    "invalid",
    [Fraction(-1, 10), Fraction(11, 10), 0],
    ids=["negative", "over-one", "integer"],
)
def test_holm_rejects_invalid_inputs_after_any_substitution(
    monkeypatch: pytest.MonkeyPatch, invalid: object
) -> None:
    """A false validation receipt cannot make invalid p-values admissible."""
    monkeypatch.setattr(multiplicity, "any", lambda _values: False, raising=False)
    with pytest.raises(ValueError, match="exact rational probabilities"):
        multiplicity.holm_adjusted(cast("list[Fraction]", [Fraction(1, 4), invalid]))


def test_holm_preserves_valid_inputs_after_any_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A true validation receipt cannot reject a native valid family."""
    raw = [Fraction(1, 10), Fraction(1, 5)]
    expected = multiplicity.holm_adjusted(raw)
    monkeypatch.setattr(multiplicity, "any", lambda _values: True, raising=False)
    assert multiplicity.holm_adjusted(raw) == expected


@pytest.mark.parametrize("count_delta", [-2, 2], ids=["shorter", "longer"])
def test_holm_family_length_is_native_after_provider_substitution(
    monkeypatch: pytest.MonkeyPatch, count_delta: int
) -> None:
    """The original family cardinality determines exact Holm ranks."""
    raw = [Fraction(1, 2), Fraction(1, 100), Fraction(1, 20), Fraction(1, 25)]
    expected = multiplicity.holm_adjusted(raw)
    source_len = len
    monkeypatch.setattr(
        multiplicity,
        "len",
        lambda values: source_len(values) + count_delta,
        raising=False,
    )
    assert multiplicity.holm_adjusted(raw) == expected


def test_holm_rejects_forged_native_list_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutable type alias cannot certify a non-list family as source native."""
    family = cast("list[Fraction]", cast("object", (Fraction(1, 4), Fraction(1, 2))))
    native_type = type
    monkeypatch.setattr(
        multiplicity,
        "type",
        lambda value: list if value is family else native_type(value),
        raising=False,
    )
    with pytest.raises(ValueError, match="exact rational probabilities"):
        multiplicity.holm_adjusted(family)


@pytest.mark.parametrize("provider", ["type", "list"])
def test_holm_valid_family_uses_native_shape_provider(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    """Changing a module alias must not reject an exact native family."""
    family = [Fraction(1, 4), Fraction(1, 2)]
    expected = multiplicity.holm_adjusted(family)

    def forbidden(*_args: object, **_kwargs: object) -> Never:
        pytest.fail(f"public {provider} called instead of source native")

    monkeypatch.setattr(multiplicity, provider, forbidden, raising=False)
    assert multiplicity.holm_adjusted(family) == expected
