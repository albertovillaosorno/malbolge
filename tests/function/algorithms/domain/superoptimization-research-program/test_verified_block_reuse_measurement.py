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
#   - Synthetic-clock evidence for the verified-block-reuse timing protocol.
# - Must-Not:
#   - Observe real timing, write evidence, filter samples, or infer speedup.
# - Allows:
#   - Inputs: checked-in plan plus deterministic clocks and strategy stubs.
#   - Outputs: paired retention, CSV, map-equality, and failure assertions.
#   - Side effects: monkeypatching registered strategy calls in process only.
# - Split-When:
#   - Retained verified-block-reuse evidence gains its own regression surface.
# - Merge-When:
#   - Shared measurement tests own this exact paired protocol.
# - Summary:
#   - Lock reuse measurement mechanics before any real clock run.
# - Description:
#   - Exercises all five pairs with synthetic nanosecond observations only.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - No host timing is admitted by this test module.
#

"""Synthetic-clock evidence for exact verified-block-reuse measurement."""

from dataclasses import replace
from pathlib import Path

from algorithms.superoptimization import (
    verified_block_reuse_measurement as measurement,
)
from algorithms.superoptimization import verified_block_reuse_runner as runner
import pytest

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/verified-block-reuse-plan.toml"
)
_REPETITIONS = 5
_FORMAT_ID = "verified-block-reuse-five-paired-measurement-v1"
_BASELINE_ID = "per-request-independent-verification-v1"
_REUSE_ID = "exact-candidate-verified-result-reuse-v1"
_REQUEST_COUNT = 17_672
_UNIQUE = 8_836
_REUSE_CALLS = 8_836
_REUSED_REQUESTS = 8_836
_ACCEPTED = 20
_BEST_QUALITY = 1
_ELAPSED = 100
_CSV_LINES = 1 + (2 * _REPETITIONS)
_MAP = (None, 1, None, 1)
_MAP_SHA256 = "a" * 64
_BAD_MAP_SHA256 = "b" * 64


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


def _verifier(candidate_index: int) -> int | None:
    _ = candidate_index
    return None


def _summary(
    strategy_id: str,
    *,
    verifier_calls: int,
    reused_requests: int,
) -> runner.VerifiedBlockReuseStrategyRun:
    return runner.VerifiedBlockReuseStrategyRun(
        strategy_id=strategy_id,
        request_count=_REQUEST_COUNT,
        unique_candidate_count=_UNIQUE,
        independent_verifier_calls=verifier_calls,
        reused_request_count=reused_requests,
        accepted_request_count=_ACCEPTED,
        best_verified_quality=_BEST_QUALITY,
        quality_map_sha256=_MAP_SHA256,
        quality_map=_MAP,
    )


def _baseline_stub(
    verifier: runner.CandidateVerifier,
) -> runner.VerifiedBlockReuseStrategyRun:
    _ = verifier
    return _summary(
        _BASELINE_ID,
        verifier_calls=_REQUEST_COUNT,
        reused_requests=0,
    )


def _reuse_stub(
    verifier: runner.CandidateVerifier,
) -> runner.VerifiedBlockReuseStrategyRun:
    _ = verifier
    return _summary(
        _REUSE_ID,
        verifier_calls=_REUSE_CALLS,
        reused_requests=_REUSED_REQUESTS,
    )


def _bad_reuse_stub(
    verifier: runner.CandidateVerifier,
) -> runner.VerifiedBlockReuseStrategyRun:
    _ = verifier
    return replace(
        _reuse_stub(verifier),
        quality_map=(1, None, 1, None),
        quality_map_sha256=_BAD_MAP_SHA256,
    )


def _patch_strategies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "run_baseline_strategy", _baseline_stub)
    monkeypatch.setattr(runner, "run_reuse_strategy", _reuse_stub)


def test_reuse_measurement_retains_all_five_fixed_order_pairs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Synthetic timing keeps both registered strategies in every pair."""
    _patch_strategies(monkeypatch)
    series = measurement.run_preregistered_measurement(
        _plan_text(),
        verifier=_verifier,
        clock_ns=_IncrementingClock(),
    )
    assert series.format_id == _FORMAT_ID
    assert len(series.repetitions) == _REPETITIONS
    for pair in series.repetitions:
        assert pair.baseline.summary.strategy_id == _BASELINE_ID
        assert pair.reused.summary.strategy_id == _REUSE_ID
        assert (
            pair.baseline.summary.independent_verifier_calls == _REQUEST_COUNT
        )
        assert pair.reused.summary.independent_verifier_calls == _REUSE_CALLS
        assert pair.reused.summary.reused_request_count == _REUSED_REQUESTS
        assert (
            pair.baseline.summary.quality_map
            == pair.reused.summary.quality_map
        )
        assert pair.baseline.elapsed_nanoseconds == _ELAPSED
        assert pair.reused.elapsed_nanoseconds == _ELAPSED


def test_reuse_measurement_raw_csv_keeps_every_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical raw output keeps two rows per paired repetition."""
    _patch_strategies(monkeypatch)
    series = measurement.run_preregistered_measurement(
        _plan_text(),
        verifier=_verifier,
        clock_ns=_IncrementingClock(),
    )
    lines = measurement.render_raw_csv(series).splitlines()
    assert len(lines) == _CSV_LINES
    assert lines[0].startswith("repetition,strategy_id,request_count,")
    assert sum(_BASELINE_ID in line for line in lines) == _REPETITIONS
    assert sum(_REUSE_ID in line for line in lines) == _REPETITIONS


def test_reuse_measurement_rejects_protocol_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-registration repetition edits cannot silently change a run."""
    _patch_strategies(monkeypatch)
    drifted = _plan_text().replace("repetitions = 5", "repetitions = 3")
    with pytest.raises(
        measurement.InvalidVerifiedBlockReuseMeasurementPlanError,
        match="repetitions differs from protocol",
    ):
        _ = measurement.run_preregistered_measurement(
            drifted,
            verifier=_verifier,
            clock_ns=_IncrementingClock(),
        )


def test_reuse_measurement_rejects_backward_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-monotonic clock cannot produce retained timing evidence."""
    _patch_strategies(monkeypatch)
    with pytest.raises(
        measurement.InvalidVerifiedBlockReuseMeasurementError,
        match="clock must be monotonic exact integers",
    ):
        _ = measurement.run_preregistered_measurement(
            _plan_text(),
            verifier=_verifier,
            clock_ns=_BackwardClock(),
        )


def test_reuse_measurement_rejects_quality_map_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a retained pair when reuse changes any request result."""
    monkeypatch.setattr(runner, "run_baseline_strategy", _baseline_stub)
    monkeypatch.setattr(runner, "run_reuse_strategy", _bad_reuse_stub)
    with pytest.raises(
        measurement.InvalidVerifiedBlockReuseMeasurementError,
        match="strategies disagree on map",
    ):
        _ = measurement.run_preregistered_measurement(
            _plan_text(),
            verifier=_verifier,
            clock_ns=_IncrementingClock(),
        )
