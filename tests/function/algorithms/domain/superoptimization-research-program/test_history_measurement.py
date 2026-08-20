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
#   - Synthetic-clock evidence for the preregistered history measurement.
# - Must-Not:
#   - Observe real timing, write evidence, filter samples, or infer speedup.
# - Allows:
#   - Inputs: checked-in plan plus deterministic test clocks.
#   - Outputs: paired-retention, CSV, and fail-closed protocol assertions.
#   - Side effects: dynamic import and deterministic in-memory strategy runs.
# - Split-When:
#   - Retained history evidence gains its own regression surface.
# - Merge-When:
#   - Shared measurement tests own this exact paired protocol.
# - Summary:
#   - Lock history measurement mechanics before any real clock is observed.
# - Description:
#   - Exercises all five pairs with synthetic nanosecond observations only.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - No host timing is admitted by this test module.
#

"""Synthetic-clock evidence for history canonicalization measurement."""

import importlib.util
from pathlib import Path
import sys
from typing import Protocol
from typing import cast

import pytest

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/history-canonicalization-plan.toml"
)
_MODULE = _ROOT / (
    "src/research/algorithms/composition/algorithms/"
    "superoptimization/history_measurement.py"
)
_REPETITIONS = 5
_FORMAT_ID = "history-residue-five-paired-measurement-v1"
_BASELINE_ID = "raw-visit-count-state-v1"
_CANONICAL_ID = "exact-history-residue-state-v1"
_BASELINE_STATES = 10_000
_CANONICAL_STATES = 6_496
_ELAPSED = 100
_CSV_LINES = 1 + (2 * _REPETITIONS)
_SEMANTIC_SHA256 = (
    "fd3644058b415d3acc091d0b837111948ff640132f7c8093fca562d553bdb527"
)


class _Summary(Protocol):
    strategy_id: str
    unique_search_states: int
    semantic_sha256: str


class _Timed(Protocol):
    summary: _Summary
    elapsed_nanoseconds: int


class _Pair(Protocol):
    baseline: _Timed
    canonicalized: _Timed


class _Series(Protocol):
    format_id: str
    repetitions: tuple[_Pair, ...]


class _MeasurementModule(Protocol):
    InvalidHistoryMeasurementPlanError: type[ValueError]
    InvalidHistoryMeasurementError: type[RuntimeError]

    def run_preregistered_measurement(
        self,
        plan_text: str,
        *,
        clock_ns: object,
    ) -> _Series: ...

    def render_raw_csv(self, series: _Series) -> str: ...


def _load_measurement() -> _MeasurementModule:
    spec = importlib.util.spec_from_file_location(
        "superoptimization_history_measurement_test",
        _MODULE,
    )
    if spec is None or spec.loader is None:
        message = "history measurement module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(_ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        _ = sys.path.pop(0)
    return cast("_MeasurementModule", cast("object", module))


_MEASUREMENT = _load_measurement()


class _IncrementingClock:
    def __init__(self) -> None:
        self._value: int = 0

    def __call__(self) -> int:
        value = self._value
        self._value += _ELAPSED
        return value


class _BackwardClock:
    def __init__(self) -> None:
        self._values: tuple[int, ...] = (100, 99)
        self._index: int = 0

    def __call__(self) -> int:
        value = self._values[self._index]
        self._index += 1
        return value


def _plan_text() -> str:
    return _PLAN.read_text(encoding="utf-8")


def test_history_measurement_retains_all_five_fixed_order_pairs() -> None:
    """Synthetic timing preserves both exact strategies in every repetition."""
    series = _MEASUREMENT.run_preregistered_measurement(
        _plan_text(),
        clock_ns=_IncrementingClock(),
    )
    assert series.format_id == _FORMAT_ID
    assert len(series.repetitions) == _REPETITIONS
    for pair in series.repetitions:
        assert pair.baseline.summary.strategy_id == _BASELINE_ID
        assert pair.canonicalized.summary.strategy_id == _CANONICAL_ID
        assert pair.baseline.summary.unique_search_states == _BASELINE_STATES
        assert (
            pair.canonicalized.summary.unique_search_states
            == _CANONICAL_STATES
        )
        assert pair.baseline.summary.semantic_sha256 == _SEMANTIC_SHA256
        assert pair.canonicalized.summary.semantic_sha256 == _SEMANTIC_SHA256
        assert pair.baseline.elapsed_nanoseconds == _ELAPSED
        assert pair.canonicalized.elapsed_nanoseconds == _ELAPSED


def test_history_measurement_raw_csv_keeps_every_pair() -> None:
    """Canonical raw output has two rows per retained paired repetition."""
    series = _MEASUREMENT.run_preregistered_measurement(
        _plan_text(),
        clock_ns=_IncrementingClock(),
    )
    lines = _MEASUREMENT.render_raw_csv(series).splitlines()
    assert len(lines) == _CSV_LINES
    assert lines[0].startswith("repetition,strategy_id,unique_search_states,")
    assert sum(_BASELINE_ID in line for line in lines) == _REPETITIONS
    assert sum(_CANONICAL_ID in line for line in lines) == _REPETITIONS


def test_history_measurement_rejects_protocol_drift() -> None:
    """Post-registration repetition edits cannot silently change a run."""
    drifted = _plan_text().replace("repetitions = 5", "repetitions = 3")
    with pytest.raises(
        _MEASUREMENT.InvalidHistoryMeasurementPlanError,
        match="repetitions differs from protocol",
    ):
        _ = _MEASUREMENT.run_preregistered_measurement(
            drifted,
            clock_ns=_IncrementingClock(),
        )


def test_history_measurement_rejects_backward_clock() -> None:
    """A non-monotonic clock cannot produce retained timing evidence."""
    with pytest.raises(
        _MEASUREMENT.InvalidHistoryMeasurementError,
        match="clock must be monotonic exact integers",
    ):
        _ = _MEASUREMENT.run_preregistered_measurement(
            _plan_text(),
            clock_ns=_BackwardClock(),
        )
