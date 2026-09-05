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
#   - Synthetic verifier evidence for the initial-decode heuristic runner.
# - Must-Not:
#   - Execute the real three-word holdout or observe its accepted candidates.
# - Allows:
#   - Inputs: monkeypatched finite schedules and synthetic verifier callbacks.
#   - Outputs: equal-budget, first-hit, best-quality, and failure assertions.
#   - Side effects: process-local monkeypatching only.
# - Split-When:
#   - Real timing/provenance gains a separate retained-evidence surface.
# - Merge-When:
#   - One runner test owns this exact comparison contract.
# - Summary:
#   - Prove schedules propose while only the injected verifier accepts.
# - Description:
#   - Uses synthetic candidates so holdout outcomes remain unobserved here.
# - Usage:
#   - Run before registering any real measurement protocol.
# - Defaults:
#   - Every synthetic schedule has exactly the frozen evaluation cardinality.
#

"""Synthetic tests for the three-word initial-decode heuristic runner."""

from algorithms.superoptimization import initial_decode_heuristic as heuristic
from algorithms.superoptimization import (
    initial_decode_heuristic_runner as runner,
)
from algorithms.superoptimization import schedule
import pytest

_BUDGET = runner.EVALUATION_BUDGET
_HIT_CANDIDATE = 7
_BEST_CANDIDATE = 11
_BEST_QUALITY = 1
_FIRST_QUALITY = 3
_VERIFIED_COUNT = 2
_MALFORMED = "trusted heuristic-search verifier quality is malformed"


def _baseline_order(candidate_count: int, budget: int) -> tuple[int, ...]:
    assert candidate_count == runner.CANDIDATE_COUNT
    assert budget == _BUDGET
    return tuple(range(_BUDGET))


def _heuristic_order(candidate_count: int, budget: int) -> tuple[int, ...]:
    assert candidate_count == runner.CANDIDATE_COUNT
    assert budget == _BUDGET
    prefix = (_HIT_CANDIDATE, _BEST_CANDIDATE)
    rest = tuple(
        candidate
        for candidate in range(_BUDGET)
        if candidate not in prefix
    )
    return (*prefix, *rest)


def _verifier(candidate: int) -> int | None:
    if candidate == _HIT_CANDIDATE:
        return _FIRST_QUALITY
    if candidate == _BEST_CANDIDATE:
        return _BEST_QUALITY
    return None


def _patch_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(schedule, "enumeration_order", _baseline_order)
    monkeypatch.setattr(heuristic, "heuristic_order", _heuristic_order)


def test_heuristic_runner_uses_equal_complete_budgets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both synthetic schedules retain every evaluation in the fixed budget."""
    _patch_orders(monkeypatch)
    result = runner.run_comparison(_verifier)
    assert result.candidate_count == runner.CANDIDATE_COUNT
    assert result.evaluation_budget == _BUDGET
    assert result.baseline.evaluations == _BUDGET
    assert result.heuristic.evaluations == _BUDGET
    assert result.baseline.schedule_id == runner.BASELINE_ID
    assert result.heuristic.schedule_id == runner.HEURISTIC_ID


def test_heuristic_runner_records_first_hit_and_best_quality_independently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A first hit cannot prevent a later better candidate from counting."""
    _patch_orders(monkeypatch)
    result = runner.run_comparison(_verifier)
    assert result.baseline.first_verified_evaluation == _HIT_CANDIDATE + 1
    assert result.heuristic.first_verified_evaluation == 1
    assert result.baseline.best_verified_candidate == _BEST_CANDIDATE
    assert result.heuristic.best_verified_candidate == _BEST_CANDIDATE
    assert result.baseline.best_verified_quality == _BEST_QUALITY
    assert result.heuristic.best_verified_quality == _BEST_QUALITY
    assert result.baseline.verified_candidate_count == _VERIFIED_COUNT
    assert result.heuristic.verified_candidate_count == _VERIFIED_COUNT


def test_heuristic_runner_accepts_only_through_supplied_verifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Schedule rank alone cannot manufacture a verified result."""
    _patch_orders(monkeypatch)
    result = runner.run_comparison(lambda _: None)
    assert result.baseline.verified_candidate_count == 0
    assert result.heuristic.verified_candidate_count == 0
    assert result.baseline.first_verified_candidate is None
    assert result.heuristic.first_verified_candidate is None
    assert result.baseline.best_verified_quality is None
    assert result.heuristic.best_verified_quality is None


def test_heuristic_runner_rejects_malformed_verifier_quality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Untrusted malformed quality cannot enter a strategy summary."""
    _patch_orders(monkeypatch)
    with pytest.raises(
        runner.InitialDecodeHeuristicComparisonError,
        match=_MALFORMED,
    ):
        _ = runner.run_comparison(lambda _: -1)
