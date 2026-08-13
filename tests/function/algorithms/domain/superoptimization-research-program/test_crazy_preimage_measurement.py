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
#   - Synthetic-clock evidence for the preregistered crazy-preimage timing.
# - Must-Not:
#   - Observe real timing, write evidence, filter samples, or infer speedup.
# - Allows:
#   - Inputs: checked-in plan plus deterministic clocks and strategy stubs.
#   - Outputs: retention, CSV, semantic, and fail-closed protocol assertions.
#   - Side effects: monkeypatching registered strategy calls in process only.
# - Split-When:
#   - Retained crazy-preimage evidence gains an independent regression surface.
# - Merge-When:
#   - Shared measurement tests own this exact paired protocol.
# - Summary:
#   - Lock crazy-preimage measurement mechanics before any real clock run.
# - Description:
#   - Exercises all five pairs with synthetic nanosecond observations only.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - No host timing is admitted by this test module.
#

"""Synthetic-clock evidence for exact crazy-preimage pruning measurement."""

from operator import add
from pathlib import Path

from algorithms.superoptimization import (
    crazy_preimage_measurement as measurement,
)
from algorithms.superoptimization import crazy_preimage_runner as runner
import pytest

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/crazy-preimage-pruning-plan.toml"
)
_REPETITIONS = 5
_FORMAT_ID = "crazy-preimage-five-paired-measurement-v1"
_BASELINE_ID = "classic-crazy-full-domain-data-enumeration-v1"
_EXACT_ID = "classic-crazy-digitwise-exact-preimage-v1"
_BASELINE_EVALUATIONS = 708_588
_EXACT_EVALUATIONS = 2_047
_PREIMAGE_COUNT = 2_047
_ELAPSED = 100
_CSV_LINES = 1 + (2 * _REPETITIONS)
_SEMANTIC_SHA256 = "a" * 64
_BAD_SEMANTIC_SHA256 = "b" * 64


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


def _baseline_stub(
    oracle: runner.CrazySemanticOracle,
) -> runner.CrazyPreimageStrategyRun:
    _ = oracle
    return runner.CrazyPreimageStrategyRun(
        _BASELINE_ID,
        _BASELINE_EVALUATIONS,
        _PREIMAGE_COUNT,
        _SEMANTIC_SHA256,
    )


def _exact_stub(
    oracle: runner.CrazySemanticOracle,
) -> runner.CrazyPreimageStrategyRun:
    _ = oracle
    return runner.CrazyPreimageStrategyRun(
        _EXACT_ID,
        _EXACT_EVALUATIONS,
        _PREIMAGE_COUNT,
        _SEMANTIC_SHA256,
    )


def _bad_exact_stub(
    oracle: runner.CrazySemanticOracle,
) -> runner.CrazyPreimageStrategyRun:
    _ = oracle
    return runner.CrazyPreimageStrategyRun(
        _EXACT_ID,
        _EXACT_EVALUATIONS,
        _PREIMAGE_COUNT,
        _BAD_SEMANTIC_SHA256,
    )


def _patch_strategies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "run_baseline_strategy", _baseline_stub)
    monkeypatch.setattr(runner, "run_exact_strategy", _exact_stub)


def test_crazy_measurement_retains_all_five_fixed_order_pairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Synthetic timing preserves both registered strategies in every pair."""
    _patch_strategies(monkeypatch)
    series = measurement.run_preregistered_measurement(
        _plan_text(), oracle=add, clock_ns=_IncrementingClock()
    )
    assert series.format_id == _FORMAT_ID
    assert len(series.repetitions) == _REPETITIONS
    for pair in series.repetitions:
        assert pair.baseline.summary.strategy_id == _BASELINE_ID
        assert pair.exact.summary.strategy_id == _EXACT_ID
        assert pair.baseline.elapsed_nanoseconds == _ELAPSED
        assert pair.exact.elapsed_nanoseconds == _ELAPSED
        assert pair.baseline.summary.semantic_sha256 == _SEMANTIC_SHA256
        assert pair.exact.summary.semantic_sha256 == _SEMANTIC_SHA256


def test_crazy_measurement_raw_csv_keeps_every_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical raw output keeps two rows per paired repetition."""
    _patch_strategies(monkeypatch)
    series = measurement.run_preregistered_measurement(
        _plan_text(), oracle=add, clock_ns=_IncrementingClock()
    )
    lines = measurement.render_raw_csv(series).splitlines()
    assert len(lines) == _CSV_LINES
    assert lines[0].startswith("repetition,strategy_id,evaluations,")
    assert sum(_BASELINE_ID in line for line in lines) == _REPETITIONS
    assert sum(_EXACT_ID in line for line in lines) == _REPETITIONS


def test_crazy_measurement_rejects_protocol_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-registration repetition edits cannot silently change a run."""
    _patch_strategies(monkeypatch)
    drifted = _plan_text().replace("repetitions = 5", "repetitions = 3")
    with pytest.raises(
        measurement.InvalidCrazyPreimageMeasurementPlanError,
        match="repetitions differs from protocol",
    ):
        _ = measurement.run_preregistered_measurement(
            drifted, oracle=add, clock_ns=_IncrementingClock()
        )


def test_crazy_measurement_rejects_backward_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-monotonic clock cannot produce retained timing evidence."""
    _patch_strategies(monkeypatch)
    with pytest.raises(
        measurement.InvalidCrazyPreimageMeasurementError,
        match="clock must be monotonic exact integers",
    ):
        _ = measurement.run_preregistered_measurement(
            _plan_text(), oracle=add, clock_ns=_BackwardClock()
        )


def test_crazy_measurement_rejects_semantic_digest_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pair retention fails closed when strategy semantics diverge."""
    monkeypatch.setattr(runner, "run_baseline_strategy", _baseline_stub)
    monkeypatch.setattr(runner, "run_exact_strategy", _bad_exact_stub)
    with pytest.raises(
        measurement.InvalidCrazyPreimageMeasurementError,
        match="strategies disagree on semantics",
    ):
        _ = measurement.run_preregistered_measurement(
            _plan_text(), oracle=add, clock_ns=_IncrementingClock()
        )
