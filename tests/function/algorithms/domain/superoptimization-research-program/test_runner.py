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
#   - Equal-budget verifier-gated superoptimization runner evidence.
# - Must-Not:
#   - Define the pilot candidate language or claim measured search performance.
# - Allows:
#   - Inputs: finite synthetic candidate indices and deterministic verifiers.
#   - Outputs: first-hit, best-quality, null-outcome, and fail-closed
#     assertions.
#   - Side effects: dynamic import of repository-owned pure research modules.
# - Split-When:
#   - Concrete challenge semantics or recorded-run evidence gains ownership.
# - Merge-When:
#   - Another test owns this exact verifier-gated runner contract.
# - Summary:
#   - Correctness evidence for equal-budget candidate-order comparison.
# - Description:
#   - Proves schedules never bypass the caller-supplied trusted verifier.
# - Usage:
#   - Collected by the research algorithm Python test surface.
# - Defaults:
#   - Evaluation counts are evidence; elapsed-time speedups are not inferred.
#

"""Correctness evidence for the superoptimization comparison substrate."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Protocol
from typing import TYPE_CHECKING
from typing import cast

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

_ROOT = Path(__file__).resolve().parents[5]
_RUNNER = _ROOT / (
    "src/research/algorithms/composition/algorithms/"
    "superoptimization/runner.py"
)
_EXPECTED_COMPARISON_ID = "finite-verifier-gated-comparison-v1"
_EXPECTED_BOUNDED_ID = "finite-verifier-gated-dual-bound-comparison-v1"
_EXPECTED_ENUMERATION_ID = "deterministic-enumeration-v1"
_EXPECTED_SEEDED_ID = "splitmix64-sparse-partial-fisher-yates-v1"
_EXPECTED_EVALUATIONS = 6
_EXPECTED_SEEDED_FIRST = 1
_EXPECTED_ENUMERATION_FIRST = 2
_BEST_CANDIDATE = 1
_BEST_QUALITY = 3
_NULL_OUTCOME = "no-verified-candidate"
_STOP_WALL_CLOCK = "wall-clock-budget"
_STOP_EVALUATION = "evaluation-budget"
_STOP_CORPUS = "candidate-corpus-exhausted"
_WALL_BUDGET = 5
_LARGE_WALL_BUDGET = 100
_TWO_EVALUATIONS = 2
_ENUMERATION_FIRST_ELAPSED = 4
_SEEDED_FIRST_ELAPSED = 2


class _ScheduleRun(Protocol):
    schedule_id: str
    evaluations: int
    verified_count: int
    first_verified_evaluation: int | None
    first_verified_candidate: int | None
    best_candidate: int | None
    best_quality: int | None
    outcome: str


class _ComparisonResult(Protocol):
    comparison_id: str
    enumeration: _ScheduleRun
    seeded: _ScheduleRun


class _BoundedRequest(Protocol):
    candidate_count: int
    evaluation_budget: int
    wall_clock_budget_nanoseconds: int
    seed: int


class _BoundedRequestFactory(Protocol):
    def __call__(
        self,
        candidate_count: int,
        *,
        evaluation_budget: int,
        wall_clock_budget_nanoseconds: int,
        seed: int,
    ) -> _BoundedRequest: ...


class _BoundedScheduleRun(Protocol):
    result: _ScheduleRun
    elapsed_nanoseconds: int
    first_verified_elapsed_nanoseconds: int | None
    stop_reason: str


class _BoundedComparisonResult(Protocol):
    comparison_id: str
    candidate_count: int
    evaluation_budget: int
    wall_clock_budget_nanoseconds: int
    seed: int
    enumeration: _BoundedScheduleRun
    seeded: _BoundedScheduleRun


class _RunnerModule(Protocol):
    BoundedComparisonRequest: _BoundedRequestFactory
    InvalidComparisonClockError: type[ValueError]
    InvalidVerifierResultError: type[ValueError]

    def compare_schedules(
        self,
        candidate_count: int,
        evaluation_budget: int,
        seed: int,
        *,
        verifier: object,
    ) -> _ComparisonResult:
        """Run the two candidate orders through one trusted verifier."""
        ...

    def compare_schedules_bounded(
        self,
        request: _BoundedRequest,
        *,
        verifier: object,
        clock_ns: object,
    ) -> _BoundedComparisonResult:
        """Run both candidate orders through dual stopping bounds."""
        ...


def _load_runner() -> _RunnerModule:
    spec = importlib.util.spec_from_file_location(
        "superoptimization_pilot_runner",
        _RUNNER,
    )
    if spec is None or spec.loader is None:
        message = "superoptimization runner module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(_RUNNER.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        _ = sys.path.pop(0)
    return cast("_RunnerModule", cast("object", module))


_RUNNER_MODULE = _load_runner()


def _fixture_verifier(candidate: int) -> int | None:
    qualities = {1: _BEST_QUALITY, 5: 9}
    return qualities.get(candidate)


def _assert_common_result(result: _ComparisonResult) -> None:
    assert result.comparison_id == _EXPECTED_COMPARISON_ID
    assert result.enumeration.schedule_id == _EXPECTED_ENUMERATION_ID
    assert result.seeded.schedule_id == _EXPECTED_SEEDED_ID
    assert result.enumeration.evaluations == _EXPECTED_EVALUATIONS
    assert result.seeded.evaluations == _EXPECTED_EVALUATIONS


def _assert_best_is_shared(result: _ComparisonResult) -> None:
    assert result.enumeration.best_candidate == _BEST_CANDIDATE
    assert result.seeded.best_candidate == _BEST_CANDIDATE
    assert result.enumeration.best_quality == _BEST_QUALITY
    assert result.seeded.best_quality == _BEST_QUALITY


class _CountingClock:
    def __init__(self) -> None:
        self._value: int = 0

    def __call__(self) -> int:
        value = self._value
        self._value += 1
        return value


class _ScriptedClock:
    def __init__(self, values: tuple[int, ...]) -> None:
        self._values: tuple[int, ...] = values
        self._index: int = 0

    def __call__(self) -> int:
        value = self._values[self._index]
        self._index += 1
        return value


def _bounded_request(
    candidate_count: int,
    evaluation_budget: int,
    wall_clock_budget_nanoseconds: int,
) -> _BoundedRequest:
    return _RUNNER_MODULE.BoundedComparisonRequest(
        candidate_count,
        evaluation_budget=evaluation_budget,
        wall_clock_budget_nanoseconds=wall_clock_budget_nanoseconds,
        seed=0,
    )


def test_runner_records_first_and_best_verified_candidate() -> None:
    """Order changes first hit while verifier quality remains authoritative."""
    result = _RUNNER_MODULE.compare_schedules(
        10,
        _EXPECTED_EVALUATIONS,
        0,
        verifier=_fixture_verifier,
    )
    _assert_common_result(result)
    assert (
        result.enumeration.first_verified_evaluation
        == _EXPECTED_ENUMERATION_FIRST
    )
    assert result.seeded.first_verified_evaluation == _EXPECTED_SEEDED_FIRST
    _assert_best_is_shared(result)


def _reject_all(candidate: int) -> None:
    _ = candidate


def _constant_verifier(
    quality: object,
) -> Callable[[int], object]:
    def verify(candidate: int) -> object:
        _ = candidate
        return quality

    return verify


def test_runner_retains_null_outcome_after_full_budget() -> None:
    """No accepted candidate remains explicit rather than becoming success."""
    result = _RUNNER_MODULE.compare_schedules(
        10,
        _EXPECTED_EVALUATIONS,
        0,
        verifier=_reject_all,
    )
    for run in (result.enumeration, result.seeded):
        assert run.evaluations == _EXPECTED_EVALUATIONS
        assert run.verified_count == 0
        assert run.first_verified_evaluation is None
        assert run.first_verified_candidate is None
        assert run.best_candidate is None
        assert run.best_quality is None
        assert run.outcome == _NULL_OUTCOME


@pytest.mark.parametrize("quality", [-1, True, 1 << 64])
def test_runner_rejects_malformed_trusted_quality(quality: object) -> None:
    """Even the trusted-verifier port fails closed on malformed quality data."""
    with pytest.raises(_RUNNER_MODULE.InvalidVerifierResultError):
        _ = _RUNNER_MODULE.compare_schedules(
            1,
            1,
            0,
            verifier=_constant_verifier(quality),
        )


def test_bounded_runner_stops_both_schedules_on_wall_clock() -> None:
    """Equal wall-clock bounds stop both schedules after two evaluations."""
    result = _RUNNER_MODULE.compare_schedules_bounded(
        _bounded_request(10, _EXPECTED_EVALUATIONS, _WALL_BUDGET),
        verifier=_fixture_verifier,
        clock_ns=_CountingClock(),
    )
    assert result.comparison_id == _EXPECTED_BOUNDED_ID
    for run in (result.enumeration, result.seeded):
        assert run.result.evaluations == _TWO_EVALUATIONS
        assert run.elapsed_nanoseconds == _WALL_BUDGET
        assert run.stop_reason == _STOP_WALL_CLOCK
    assert (
        result.enumeration.first_verified_elapsed_nanoseconds
        == _ENUMERATION_FIRST_ELAPSED
    )
    assert (
        result.seeded.first_verified_elapsed_nanoseconds
        == _SEEDED_FIRST_ELAPSED
    )


def test_bounded_runner_records_evaluation_budget_stop() -> None:
    """Evaluation budget remains the stop reason when time is ample."""
    result = _RUNNER_MODULE.compare_schedules_bounded(
        _bounded_request(10, 2, _LARGE_WALL_BUDGET),
        verifier=_fixture_verifier,
        clock_ns=_CountingClock(),
    )
    for run in (result.enumeration, result.seeded):
        assert run.result.evaluations == _TWO_EVALUATIONS
        assert run.stop_reason == _STOP_EVALUATION


def test_bounded_runner_records_candidate_corpus_exhaustion() -> None:
    """A short finite corpus is distinct from budget exhaustion."""
    result = _RUNNER_MODULE.compare_schedules_bounded(
        _bounded_request(2, _EXPECTED_EVALUATIONS, _LARGE_WALL_BUDGET),
        verifier=_fixture_verifier,
        clock_ns=_CountingClock(),
    )
    for run in (result.enumeration, result.seeded):
        assert run.result.evaluations == _TWO_EVALUATIONS
        assert run.stop_reason == _STOP_CORPUS


@pytest.mark.parametrize("wall_budget", [0, -1, True, 1 << 64])
def test_bounded_runner_rejects_invalid_wall_clock_budget(
    wall_budget: int,
) -> None:
    """Wall-clock bound requires one exact positive unsigned integer."""
    request = _RUNNER_MODULE.BoundedComparisonRequest(
        10,
        evaluation_budget=_TWO_EVALUATIONS,
        wall_clock_budget_nanoseconds=wall_budget,
        seed=0,
    )
    with pytest.raises(_RUNNER_MODULE.InvalidComparisonClockError):
        _ = _RUNNER_MODULE.compare_schedules_bounded(
            request,
            verifier=_fixture_verifier,
            clock_ns=_CountingClock(),
        )


def test_bounded_runner_rejects_backward_clock() -> None:
    """Elapsed-time evidence fails closed if the injected clock regresses."""
    with pytest.raises(
        _RUNNER_MODULE.InvalidComparisonClockError,
        match="comparison clock moved backwards",
    ):
        _ = _RUNNER_MODULE.compare_schedules_bounded(
            _bounded_request(10, 2, _LARGE_WALL_BUDGET),
            verifier=_fixture_verifier,
            clock_ns=_ScriptedClock((5, 4)),
        )
