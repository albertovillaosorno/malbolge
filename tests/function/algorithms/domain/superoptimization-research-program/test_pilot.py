# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Plan-to-runner binding evidence for the concrete classic pilot.
# - Must-Not:
#   - Persist a run, use real timing, or infer comparative performance.
# - Allows:
#   - Inputs: checked-in plan text plus synthetic plan mutations/clocks.
#   - Outputs: exact request identity and fail-closed drift assertions.
#   - Side effects: repository-local plan read only.
# - Split-When:
#   - Retained measured-run execution gains an evidence contract.
# - Merge-When:
#   - Shared experiment harness tests own this exact plan binding.
# - Summary:
#   - Lock concrete challenge identity into executable pilot orchestration.
# - Description:
#   - Stops synthetic execution before any candidate verifier call.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Tests contain no wall-clock benchmark measurement.
#

"""Plan-bound orchestration tests for the concrete classic superopt pilot."""

from pathlib import Path

import pytest

from src.research.algorithms.composition.algorithms.superoptimization import (
    challenge,
)
from src.research.algorithms.composition.algorithms.superoptimization import (
    pilot,
)

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/experiment.toml"
)
_EVALUATIONS = 10_000
_WALL_NANOSECONDS = 60_000_000_000
_SEED = 0
_WALL_STOP = "wall-clock-budget"
_WORKLOAD_HASH = (
    "eb739238b375fde435e3948896f385e6be9ab5002078b242c2826153ce1810fc"
)


class _ImmediateBudgetClock:
    def __init__(self) -> None:
        self._values: tuple[int, ...] = (
            0,
            _WALL_NANOSECONDS,
            0,
            _WALL_NANOSECONDS,
        )
        self._index: int = 0

    def __call__(self) -> int:
        value = self._values[self._index]
        self._index += 1
        return value


def _plan_text() -> str:
    return _PLAN.read_text(encoding="utf-8")


def test_preregistered_request_matches_concrete_challenge() -> None:
    """Checked-in plan projects to one exact finite dual-bound request."""
    request = pilot.preregistered_request(_plan_text())
    assert (
        request.candidate_count
        == challenge.CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT
    )
    assert request.evaluation_budget == _EVALUATIONS
    assert request.wall_clock_budget_nanoseconds == _WALL_NANOSECONDS
    assert request.seed == _SEED


def test_pilot_rejects_workload_identity_drift() -> None:
    """Plan mutation cannot silently substitute another workload."""
    drifted = _plan_text().replace(_WORKLOAD_HASH, "0" * 64)
    with pytest.raises(
        pilot.InvalidPilotPlanError,
        match="workload hash differs from concrete challenge",
    ):
        _ = pilot.preregistered_request(drifted)


def test_pilot_rejects_verifier_identity_drift() -> None:
    """Plan mutation cannot replace the independent semantic verifier."""
    drifted = _plan_text().replace(
        challenge.CLASSIC_BLOCK_SEARCH_VERIFIER_ID,
        "different-verifier-v1",
    )
    with pytest.raises(
        pilot.InvalidPilotPlanError,
        match="verifier identity differs from concrete challenge",
    ):
        _ = pilot.preregistered_request(drifted)


def test_synthetic_wall_stop_writes_no_measurement() -> None:
    """Harness wiring can be tested without evaluating a candidate."""
    result = pilot.run_preregistered_pilot(
        _plan_text(),
        clock_ns=_ImmediateBudgetClock(),
    )
    for schedule in (result.enumeration, result.seeded):
        assert schedule.result.evaluations == 0
        assert schedule.result.verified_count == 0
        assert schedule.stop_reason == _WALL_STOP
