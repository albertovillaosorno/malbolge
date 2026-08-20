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
#   - Crossover tests for bounded snapshot host registration.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Pure crossover tests for bounded snapshot host registration."""

from __future__ import annotations

from benchmarks.accelerator.profile_snapshot_host_registration_tradeoff import (
    strict_host_registration_crossover,
)

EXPECTED_CROSSOVER = 3


def test_host_registration_crossover_is_incremental_and_strict() -> None:
    """Only incremental setup cost is amortized by a faster hot path."""
    assert (
        strict_host_registration_crossover(
            100,
            80,
            30,
            registration_active=True,
        )
        == EXPECTED_CROSSOVER
    )
    assert (200 - 100) + (2 * 30) >= 2 * 80
    assert (200 - 100) + (3 * 30) < 3 * 80


def test_host_registration_crossover_rejects_fallback_or_slow_routes() -> None:
    """Fallback and non-improving registered routes cannot amortize."""
    assert (
        strict_host_registration_crossover(
            100,
            80,
            30,
            registration_active=False,
        )
        is None
    )
    assert (
        strict_host_registration_crossover(
            100,
            80,
            80,
            registration_active=True,
        )
        is None
    )


def test_host_registration_crossover_clamps_noisy_setup_advantage() -> None:
    """A lower observed registered setup cost yields one-snapshot crossover."""
    assert (
        strict_host_registration_crossover(
            -100,
            80,
            30,
            registration_active=True,
        )
        == 1
    )
