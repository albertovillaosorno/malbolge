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
_EXPECTED_ENUMERATION_ID = "deterministic-enumeration-v1"
_EXPECTED_SEEDED_ID = "splitmix64-sparse-partial-fisher-yates-v1"
_EXPECTED_EVALUATIONS = 6
_EXPECTED_SEEDED_FIRST = 1
_EXPECTED_ENUMERATION_FIRST = 2
_BEST_CANDIDATE = 1
_BEST_QUALITY = 3
_NULL_OUTCOME = "no-verified-candidate"


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


class _RunnerModule(Protocol):
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
