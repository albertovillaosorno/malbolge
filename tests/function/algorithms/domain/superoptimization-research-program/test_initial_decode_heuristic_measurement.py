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
#   - Synthetic-clock evidence for the initial-decode heuristic timing protocol.
# - Must-Not:
#   - Execute holdout verification, observe real timing, or write evidence.
# - Allows:
#   - Inputs: checked-in plan plus synthetic strategy summaries and clocks.
#   - Outputs: retention, CSV, budget, identity, and failure assertions.
#   - Side effects: process-local monkeypatching only.
# - Split-When:
#   - Retained heuristic evidence gains its own regression test.
# - Merge-When:
#   - Shared timing tests own this exact protocol.
# - Summary:
#   - Lock heuristic timing mechanics before any real-clock holdout run.
# - Description:
#   - Verifies schedule construction belongs inside each timed strategy call.
# - Usage:
#   - Collected before source-pinned real measurement is allowed.
# - Defaults:
#   - No holdout candidate outcome appears in this synthetic test.
#

"""Synthetic-clock evidence for the initial-decode heuristic protocol."""

from pathlib import Path

from algorithms.superoptimization import (
    initial_decode_heuristic_measurement as measurement,
)
from algorithms.superoptimization import (
    initial_decode_heuristic_runner as runner,
)
import pytest

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/initial-decode-heuristic-plan.toml"
)
_REPETITIONS = 5
_ELAPSED = 100
_CSV_LINES = 1 + (2 * _REPETITIONS)
_VERIFIED = 3
_FIRST_EVALUATION = 7
_FIRST_CANDIDATE = 11
_BEST_CANDIDATE = 13
_BEST_QUALITY = 1
_FORMAT_ID = "initial-decode-heuristic-five-paired-measurement-v1"


class _IncrementingClock:
    def __init__(self) -> None:
        self._value: int = 0

    def __call__(self) -> int:
        value = self._value
        self._value += _ELAPSED
        return value


class _BackwardClock:
    def __init__(self) -> None:
        self._values: tuple[int, int] = (100, 99)
        self._index: int = 0

    def __call__(self) -> int:
        value = self._values[self._index]
        self._index += 1
        return value


def _plan_text() -> str:
    return _PLAN.read_text(encoding="utf-8")


def _summary(schedule_id: str) -> runner.HeuristicStrategyRun:
    return runner.HeuristicStrategyRun(
        schedule_id=schedule_id,
        evaluations=runner.EVALUATION_BUDGET,
        verified_candidate_count=_VERIFIED,
        first_verified_evaluation=_FIRST_EVALUATION,
        first_verified_candidate=_FIRST_CANDIDATE,
        best_verified_candidate=_BEST_CANDIDATE,
        best_verified_quality=_BEST_QUALITY,
    )


def _baseline(_: runner.CandidateVerifier) -> runner.HeuristicStrategyRun:
    return _summary(runner.BASELINE_ID)


def _heuristic(_: runner.CandidateVerifier) -> runner.HeuristicStrategyRun:
    return _summary(runner.HEURISTIC_ID)


def _patch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "run_baseline_strategy", _baseline)
    monkeypatch.setattr(runner, "run_heuristic_strategy", _heuristic)


def test_heuristic_measurement_retains_all_five_pairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Synthetic timing keeps both registered full-budget strategy calls."""
    _patch(monkeypatch)
    series = measurement.run_preregistered_measurement(
        _plan_text(),
        verifier=lambda _: None,
        clock_ns=_IncrementingClock(),
    )
    assert series.format_id == _FORMAT_ID
    assert len(series.repetitions) == _REPETITIONS
    for pair in series.repetitions:
        assert pair.baseline.summary.schedule_id == runner.BASELINE_ID
        assert pair.heuristic.summary.schedule_id == runner.HEURISTIC_ID
        assert pair.baseline.summary.evaluations == runner.EVALUATION_BUDGET
        assert pair.heuristic.summary.evaluations == runner.EVALUATION_BUDGET
        assert pair.baseline.elapsed_nanoseconds == _ELAPSED
        assert pair.heuristic.elapsed_nanoseconds == _ELAPSED


def test_heuristic_measurement_csv_keeps_every_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical raw output keeps two strategy rows per repetition."""
    _patch(monkeypatch)
    series = measurement.run_preregistered_measurement(
        _plan_text(),
        verifier=lambda _: None,
        clock_ns=_IncrementingClock(),
    )
    lines = measurement.render_raw_csv(series).splitlines()
    assert len(lines) == _CSV_LINES
    assert sum(runner.BASELINE_ID in line for line in lines) == _REPETITIONS
    assert sum(runner.HEURISTIC_ID in line for line in lines) == _REPETITIONS


def test_heuristic_measurement_rejects_protocol_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-registration timing-scope edits fail closed."""
    _patch(monkeypatch)
    drifted = _plan_text().replace(
        "schedule-construction-plus-full-budget-verification",
        "verification-only",
    )
    with pytest.raises(
        measurement.InvalidInitialDecodeHeuristicMeasurementPlanError,
        match="timing scope differs from protocol",
    ):
        _ = measurement.run_preregistered_measurement(
            drifted,
            verifier=lambda _: None,
            clock_ns=_IncrementingClock(),
        )


def test_heuristic_measurement_rejects_backward_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-monotonic clock cannot create retained timing evidence."""
    _patch(monkeypatch)
    with pytest.raises(
        measurement.InvalidInitialDecodeHeuristicMeasurementError,
        match="clock must be monotonic exact integers",
    ):
        _ = measurement.run_preregistered_measurement(
            _plan_text(),
            verifier=lambda _: None,
            clock_ns=_BackwardClock(),
        )
