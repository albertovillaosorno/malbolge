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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Crossover tests for caller-owned snapshot workspaces.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Pure crossover tests for caller-owned snapshot workspaces."""

from __future__ import annotations

from benchmarks.accelerator.profile_snapshot_workspace_tradeoff import (
    strict_workspace_crossover,
)

EXPECTED_CROSSOVER = 3


def test_workspace_crossover_is_strict_and_ceiling_bounded() -> None:
    """One-time allocation is recovered only after total cost is lower."""
    assert strict_workspace_crossover(100, 80, 30) == EXPECTED_CROSSOVER
    assert 100 + (2 * 30) >= 2 * 80
    assert 100 + (3 * 30) < 3 * 80


def test_workspace_crossover_rejects_non_improving_hot_path() -> None:
    """A workspace cannot amortize when one snapshot is not faster."""
    assert strict_workspace_crossover(100, 80, 80) is None
    assert strict_workspace_crossover(100, 80, 90) is None
