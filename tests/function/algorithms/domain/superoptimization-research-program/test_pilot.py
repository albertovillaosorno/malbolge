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

import importlib.util
from pathlib import Path
import sys
from typing import Protocol
from typing import cast

import pytest

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/experiment.toml"
)
_PILOT = _ROOT / (
    "src/research/algorithms/composition/algorithms/superoptimization/pilot.py"
)
_EVALUATIONS = 10_000
_WALL_NANOSECONDS = 60_000_000_000
_SEED = 0
_WALL_STOP = "wall-clock-budget"
_CANDIDATE_COUNT = 8_836
_VERIFIER_ID = "classic-two-word-no-io-halt-v1"
_WORKLOAD_HASH = (
    "eb739238b375fde435e3948896f385e6be9ab5002078b242c2826153ce1810fc"
)


class _Request(Protocol):
    candidate_count: int
    evaluation_budget: int
    wall_clock_budget_nanoseconds: int
    seed: int


class _ScheduleResult(Protocol):
    evaluations: int
    verified_count: int


class _BoundedSchedule(Protocol):
    result: _ScheduleResult
    stop_reason: str


class _Comparison(Protocol):
    enumeration: _BoundedSchedule
    seeded: _BoundedSchedule


class _PilotModule(Protocol):
    InvalidPilotPlanError: type[ValueError]

    def preregistered_request(self, plan_text: str) -> _Request: ...

    def run_preregistered_pilot(
        self,
        plan_text: str,
        *,
        clock_ns: object,
    ) -> _Comparison: ...


def _load_pilot() -> _PilotModule:
    spec = importlib.util.spec_from_file_location(
        "superoptimization_pilot_test",
        _PILOT,
    )
    if spec is None or spec.loader is None:
        message = "superoptimization pilot module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(_ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        _ = sys.path.pop(0)
    return cast("_PilotModule", cast("object", module))


_PILOT_MODULE = _load_pilot()


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
    request = _PILOT_MODULE.preregistered_request(_plan_text())
    assert (
        request.candidate_count
        == _CANDIDATE_COUNT
    )
    assert request.evaluation_budget == _EVALUATIONS
    assert request.wall_clock_budget_nanoseconds == _WALL_NANOSECONDS
    assert request.seed == _SEED


def test_pilot_rejects_workload_identity_drift() -> None:
    """Plan mutation cannot silently substitute another workload."""
    drifted = _plan_text().replace(_WORKLOAD_HASH, "0" * 64)
    with pytest.raises(
        _PILOT_MODULE.InvalidPilotPlanError,
        match="workload hash differs from concrete challenge",
    ):
        _ = _PILOT_MODULE.preregistered_request(drifted)


def test_pilot_rejects_verifier_identity_drift() -> None:
    """Plan mutation cannot replace the independent semantic verifier."""
    drifted = _plan_text().replace(
        _VERIFIER_ID,
        "different-verifier-v1",
    )
    with pytest.raises(
        _PILOT_MODULE.InvalidPilotPlanError,
        match="verifier identity differs from concrete challenge",
    ):
        _ = _PILOT_MODULE.preregistered_request(drifted)


def test_synthetic_wall_stop_writes_no_measurement() -> None:
    """Harness wiring can be tested without evaluating a candidate."""
    result = _PILOT_MODULE.run_preregistered_pilot(
        _plan_text(),
        clock_ns=_ImmediateBudgetClock(),
    )
    for schedule in (result.enumeration, result.seeded):
        assert schedule.result.evaluations == 0
        assert schedule.result.verified_count == 0
        assert schedule.stop_reason == _WALL_STOP
