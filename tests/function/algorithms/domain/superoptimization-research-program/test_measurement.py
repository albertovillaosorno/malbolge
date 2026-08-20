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
#   - Retained-measurement contract tests for the concrete classic pilot.
# - Must-Not:
#   - Use real timing, write evidence, or infer comparative performance.
# - Allows:
#   - Inputs: checked-in plan plus synthetic clocks and plan mutations.
#   - Outputs: repetition, fail-closed protocol, and raw-CSV assertions.
#   - Side effects: repository-local plan read only.
# - Split-When:
#   - Persistent measured evidence gains an independent test surface.
# - Merge-When:
#   - Shared benchmark harness tests own this exact retained-sample policy.
# - Summary:
#   - Prove all preregistered superoptimization samples are retained.
# - Description:
#   - Synthetic clocks stop before candidate evaluation and create no benchmark.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - No warmup, sample filtering, or host timing occurs in these tests.
#

"""Retained-measurement tests for the concrete classic superopt pilot."""

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
_MEASUREMENT = _ROOT / (
    "src/research/algorithms/composition/algorithms/"
    "superoptimization/measurement.py"
)
_REPETITIONS = 5
_WALL_NANOSECONDS = 60_000_000_000
_FORMAT_ID = "superoptimization-five-repetition-measurement-v1"
_CSV_LINES = 1 + 2 * _REPETITIONS
_WALL_STOP = "wall-clock-budget"
_ENUMERATION_ID = "deterministic-enumeration-v1"
_SEEDED_ID = "splitmix64-sparse-partial-fisher-yates-v1"


class _ScheduleResult(Protocol):
    evaluations: int
    verified_count: int


class _Schedule(Protocol):
    result: _ScheduleResult
    stop_reason: str


class _Comparison(Protocol):
    enumeration: _Schedule
    seeded: _Schedule


class _Series(Protocol):
    format_id: str
    repetitions: tuple[_Comparison, ...]


class _MeasurementModule(Protocol):
    InvalidMeasurementPlanError: type[ValueError]

    def run_preregistered_measurement(
        self,
        plan_text: str,
        *,
        clock_ns: object,
    ) -> _Series: ...

    def render_raw_csv(self, series: _Series) -> str: ...


def _load_measurement() -> _MeasurementModule:
    spec = importlib.util.spec_from_file_location(
        "superoptimization_measurement_test",
        _MEASUREMENT,
    )
    if spec is None or spec.loader is None:
        message = "superoptimization measurement module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(_ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        _ = sys.path.pop(0)
    return cast("_MeasurementModule", cast("object", module))


_MEASUREMENT_MODULE = _load_measurement()


class _ImmediateBudgetClock:
    def __init__(self) -> None:
        pair = (0, _WALL_NANOSECONDS, 0, _WALL_NANOSECONDS)
        self._values: tuple[int, ...] = pair * _REPETITIONS
        self._index: int = 0

    def __call__(self) -> int:
        value = self._values[self._index]
        self._index += 1
        return value


def _plan_text() -> str:
    return _PLAN.read_text(encoding="utf-8")


def test_measurement_retains_all_preregistered_repetitions() -> None:
    """Synthetic execution retains every repetition without evaluation."""
    series = _MEASUREMENT_MODULE.run_preregistered_measurement(
        _plan_text(),
        clock_ns=_ImmediateBudgetClock(),
    )
    assert series.format_id == _FORMAT_ID
    assert len(series.repetitions) == _REPETITIONS
    for comparison in series.repetitions:
        for schedule in (comparison.enumeration, comparison.seeded):
            assert schedule.result.evaluations == 0
            assert schedule.result.verified_count == 0
            assert schedule.stop_reason == _WALL_STOP


def test_measurement_rejects_post_preregistration_repetition_drift() -> None:
    """Repetition count cannot change after the timing protocol is frozen."""
    drifted = _plan_text().replace("repetitions = 5", "repetitions = 3")
    with pytest.raises(
        _MEASUREMENT_MODULE.InvalidMeasurementPlanError,
        match="repetitions differs from preregistration",
    ):
        _ = _MEASUREMENT_MODULE.run_preregistered_measurement(
            drifted,
            clock_ns=_ImmediateBudgetClock(),
        )


def test_raw_csv_retains_both_schedules_for_every_repetition() -> None:
    """Canonical raw output has one row per retained schedule execution."""
    series = _MEASUREMENT_MODULE.run_preregistered_measurement(
        _plan_text(),
        clock_ns=_ImmediateBudgetClock(),
    )
    lines = _MEASUREMENT_MODULE.render_raw_csv(series).splitlines()
    assert len(lines) == _CSV_LINES
    assert lines[0].startswith("repetition,schedule_id,evaluations,")
    assert sum(_ENUMERATION_ID in line for line in lines) == _REPETITIONS
    assert sum(_SEEDED_ID in line for line in lines) == _REPETITIONS
