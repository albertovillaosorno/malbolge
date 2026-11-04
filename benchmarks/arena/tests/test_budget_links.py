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
