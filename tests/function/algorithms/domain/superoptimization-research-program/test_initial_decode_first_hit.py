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
#   - Synthetic evidence for the stop-on-first follow-up runner and plan.
# - Must-Not:
#   - Execute the real holdout or observe real timing.
# - Allows:
#   - Inputs: checked-in plan, synthetic verifier, and deterministic clocks.
#   - Outputs: stopping, quality, protocol, and fail-closed assertions.
#   - Side effects: repository-local plan reads only.
# - Split-When:
#   - Another first-hit follow-up gains independent protocol evidence.
# - Merge-When:
#   - Shared tests own this exact first-hit runner and plan identity.
# - Summary:
#   - Freeze first-hit execution mechanics before real follow-up timing.
# - Description:
#   - Locks five fixed-order retain-all pairs without a real clock run.
# - Usage:
#   - Run before source-pinned first-hit timing is collected.
# - Defaults:
#   - Real holdout outcomes remain absent from this synthetic test module.
#

"""Synthetic tests for the bucketed initial-decode first-hit follow-up."""

from pathlib import Path
import tomllib
from typing import cast

from algorithms.superoptimization import initial_decode_first_hit as runner
import pytest

_HIT = 7
_QUALITY = 2
_ELAPSED = 10
_REPETITIONS = 5
_ORDERING = "fixed-enumeration-then-heuristic"
_OUTLIERS = "retain-all"
_REGISTERED = "registered"
_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/initial-decode-first-hit-plan.toml"
)


class _Clock:
    def __init__(self) -> None:
        self.value: int = 0

    def __call__(self) -> int:
        current = self.value
        self.value += _ELAPSED
        return current


def _verifier(candidate: int) -> int | None:
    return _QUALITY if candidate == _HIT else None


def test_first_hit_baseline_stops_on_verified_candidate() -> None:
    """Natural order stops immediately after the first trusted verifier hit."""
    run = runner.run_baseline(_verifier, _Clock())
    assert run.evaluations == _HIT + 1
    assert run.candidate == _HIT
    assert run.quality == _QUALITY
    assert run.elapsed_nanoseconds == _ELAPSED


def test_first_hit_rejects_malformed_quality() -> None:
    """Malformed verifier output never becomes search success."""
    with pytest.raises(runner.InitialDecodeFirstHitError, match="malformed"):
        _ = runner.run_baseline(lambda _: -1, _Clock())


def test_first_hit_plan_freezes_real_measurement_gate() -> None:
    """Five fixed-order pairs remain gated on retained provenance."""
    document = cast("dict[str, object]", tomllib.loads(_PLAN.read_text()))
    measurement = cast("dict[str, object]", document["measurement"])
    gate = cast("dict[str, object]", document["measurement_gate"])
    assert measurement["repetitions"] == _REPETITIONS
    assert measurement["warmup_iterations"] == 0
    assert measurement["ordering"] == _ORDERING
    assert measurement["outlier_policy"] == _OUTLIERS
    assert gate["retained_provenance_status"] == _REGISTERED
    assert gate["results_allowed"] is True
