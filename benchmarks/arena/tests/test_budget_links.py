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
#   - Native unit conversion semantics for experiment-run resource budgets.
# - Must-Not:
#   - Claim enforcement of memory or time limits by the operating system.
# - Allows:
#   - Inputs: native bounded TOML budget tables and injected unit drift.
#   - Outputs: canonical nanoseconds/MiB byte budgets or typed failure.
#   - Side effects: isolated monkeypatches of conversion constants.
# - Split-When:
#   - Additional budget units require a separate protocol.
# - Merge-When:
#   - The arena budget-link parser owns this conversion policy.
# - Summary:
#   - Publicly replaceable unit constants cannot reinterpret source budgets.
# - Description:
#   - Red-first time and memory conversion substitutions with a valid source.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_budget_links.py`.
# - Defaults:
#   - Whole seconds and MiB convert to exact base units.
#

"""Independent source-stable arena budget-unit semantics."""

# ruff: file-ignore[assert]

from __future__ import annotations

import pytest

from benchmarks.arena import budget_links

MANIFEST = "[budget]\nseconds = 3\nmemory_mib = 5\n"
EXPECTED = budget_links.RunBudgets(time_ns=3_000_000_000, memory_bytes=5_242_880)


def test_declared_seconds_and_mib_convert_without_drift() -> None:
    """A valid source budget has the exact governed physical units."""
    assert budget_links.parse_run_budgets(MANIFEST) == EXPECTED


@pytest.mark.parametrize(
    ("conversion", "forged_factor"),
    [("NANOSECONDS_PER_SECOND", 1000), ("BYTES_PER_MIB", 1000)],
)
def test_source_budget_unit_conversion_ignores_mutable_policy_drift(
    monkeypatch: pytest.MonkeyPatch, conversion: str, forged_factor: int
) -> None:
    """Changed runtime constants cannot relabel native source limits."""
    with monkeypatch.context() as patched:
        patched.setattr(budget_links, conversion, forged_factor)
        assert budget_links.parse_run_budgets(MANIFEST) == EXPECTED


def test_public_budget_size_limit_cannot_admit_oversized_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A changed runtime limit cannot authorize oversized source TOML."""
    oversized = MANIFEST + "#" + "x" * budget_links.MAX_RUN_MANIFEST_BYTES
    monkeypatch.setattr(budget_links, "MAX_RUN_MANIFEST_BYTES", len(oversized) + 1)
    with pytest.raises(budget_links.BudgetLinkError, match="byte limit"):
        budget_links.parse_run_budgets(oversized)


@pytest.mark.parametrize("forged_field", ["time_ns", "memory_bytes"])
def test_source_budgets_ignore_substituted_result_constructor(
    monkeypatch: pytest.MonkeyPatch, forged_field: str
) -> None:
    """A replacement result factory cannot alter checked source budgets."""
    original = budget_links.RunBudgets

    def forged_constructor(
        *, time_ns: int, memory_bytes: int
    ) -> budget_links.RunBudgets:
        result = {"time_ns": time_ns, "memory_bytes": memory_bytes}
        result[forged_field] += 1
        return original(**result)

    with monkeypatch.context() as patched:
        patched.setattr(budget_links, "RunBudgets", forged_constructor)
        assert budget_links.parse_run_budgets(MANIFEST) == EXPECTED


def test_budget_source_limit_rejects_substituted_text_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced local size preflight cannot admit oversized source TOML."""
    oversized = MANIFEST + "#" + "x" * budget_links.MAX_RUN_MANIFEST_BYTES
    monkeypatch.setattr(budget_links, "_admit_text", lambda _text: None)
    with pytest.raises(budget_links.BudgetLinkError, match="byte limit"):
        budget_links.parse_run_budgets(oversized)


def test_budget_source_limit_rejects_suppressed_error_hook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An overridden error hook cannot silently ignore an oversized manifest."""
    oversized = MANIFEST + "#" + "x" * budget_links.MAX_RUN_MANIFEST_BYTES
    monkeypatch.setattr(budget_links, "_fail", lambda _message: None)
    with pytest.raises(budget_links.BudgetLinkError, match="byte limit"):
        budget_links.parse_run_budgets(oversized)
