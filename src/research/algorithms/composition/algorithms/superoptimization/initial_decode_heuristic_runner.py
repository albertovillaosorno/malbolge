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
#   - Equal-budget enumeration-versus-initial-decode heuristic comparison.
# - Must-Not:
#   - Define challenge semantics, accept candidates without the caller verifier,
#     alter schedules from outcomes, or write measurement evidence.
# - Allows:
#   - Inputs: one deterministic trusted verifier callback.
#   - Outputs: full-budget first-hit/count/best-quality strategy summaries.
#   - Side effects: invokes only the supplied verifier callback.
# - Split-When:
#   - Timing/provenance or another heuristic gains independent policy.
# - Merge-When:
#   - A shared heuristic runner owns this exact fixed holdout comparison.
# - Summary:
#   - Compare natural enumeration with the preregistered static decode order.
# - Description:
#   - Runs all 50,000 scheduled candidates so first-hit cannot hide later data.
# - Usage:
#   - Register before any real-clock holdout comparison is interpreted.
# - Defaults:
#   - Malformed verifier quality and schedule cardinality fail closed.
#

"""Verifier-gated runner for the three-word initial-decode heuristic."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from algorithms.superoptimization import initial_decode_heuristic as heuristic
from algorithms.superoptimization import schedule

COMPARISON_ID: Final = "classic-three-word-initial-halt-heuristic-comparison-v1"
BASELINE_ID: Final = schedule.ENUMERATION_SCHEDULE_ID
HEURISTIC_ID: Final = heuristic.HEURISTIC_SCHEDULE_ID
CANDIDATE_COUNT: Final = heuristic.THREE_WORD_CANDIDATE_COUNT
EVALUATION_BUDGET: Final = 50_000
_MAX_U64: Final = (1 << 64) - 1

type CandidateVerifier = Callable[[int], int | None]


class InitialDecodeHeuristicComparisonError(ValueError):
    """The heuristic comparison violated its frozen verifier-gated contract."""


@dataclass(frozen=True, slots=True)
class HeuristicStrategyRun:
    """Complete fixed-budget result for one candidate ordering."""

    schedule_id: str
    evaluations: int
    verified_candidate_count: int
    first_verified_evaluation: int | None
    first_verified_candidate: int | None
    best_verified_candidate: int | None
    best_verified_quality: int | None


@dataclass(frozen=True, slots=True)
class InitialDecodeHeuristicComparison:
    """Equal-budget baseline and static-heuristic strategy summaries."""

    comparison_id: str
    candidate_count: int
    evaluation_budget: int
    baseline: HeuristicStrategyRun
    heuristic: HeuristicStrategyRun


@dataclass(slots=True)
class _RunState:
    verified_count: int = 0
    first_evaluation: int | None = None
    first_candidate: int | None = None
    best_candidate: int | None = None
    best_quality: int | None = None

    def record(
        self,
        candidate: int,
        evaluation: int,
        quality: int | None,
    ) -> None:
        """Record one already-validated verifier result."""
        if quality is None:
            return
        self.verified_count += 1
        if self.first_evaluation is None:
            self.first_evaluation = evaluation
            self.first_candidate = candidate
        if self.best_quality is None or quality < self.best_quality:
            self.best_candidate = candidate
            self.best_quality = quality


def _quality(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= _MAX_U64:
        message = "trusted heuristic-search verifier quality is malformed"
        raise InitialDecodeHeuristicComparisonError(message)
    return value


def _strategy_run(
    order: tuple[int, ...],
    schedule_id: str,
    verifier: CandidateVerifier,
) -> HeuristicStrategyRun:
    if len(order) != EVALUATION_BUDGET or len(set(order)) != len(order):
        message = "heuristic-search schedule lost fixed-budget uniqueness"
        raise InitialDecodeHeuristicComparisonError(message)
    state = _RunState()
    for evaluation, candidate in enumerate(order, start=1):
        state.record(candidate, evaluation, _quality(verifier(candidate)))
    return HeuristicStrategyRun(
        schedule_id=schedule_id,
        evaluations=len(order),
        verified_candidate_count=state.verified_count,
        first_verified_evaluation=state.first_evaluation,
        first_verified_candidate=state.first_candidate,
        best_verified_candidate=state.best_candidate,
        best_verified_quality=state.best_quality,
    )


def run_baseline_strategy(verifier: CandidateVerifier) -> HeuristicStrategyRun:
    """Run natural enumeration for the complete preregistered budget.

    Returns:
        Verifier-gated natural-order search summary.

    """
    order = schedule.enumeration_order(CANDIDATE_COUNT, EVALUATION_BUDGET)
    return _strategy_run(order, BASELINE_ID, verifier)


def run_heuristic_strategy(verifier: CandidateVerifier) -> HeuristicStrategyRun:
    """Run the static initial-decode order for the same evaluation budget.

    Returns:
        Verifier-gated static-heuristic search summary.

    """
    order = heuristic.heuristic_order(CANDIDATE_COUNT, EVALUATION_BUDGET)
    return _strategy_run(order, HEURISTIC_ID, verifier)


def run_comparison(
    verifier: CandidateVerifier,
) -> InitialDecodeHeuristicComparison:
    """Run both registered schedules through one caller-supplied verifier.

    Returns:
        Fixed-budget baseline and heuristic evidence with verifier-only
        acceptance.

    Raises:
        InitialDecodeHeuristicComparisonError: If schedule budgets differ.

    """
    baseline = run_baseline_strategy(verifier)
    heuristic_run = run_heuristic_strategy(verifier)
    if baseline.evaluations != heuristic_run.evaluations:
        message = "heuristic-search strategies used unequal evaluation budgets"
        raise InitialDecodeHeuristicComparisonError(message)
    return InitialDecodeHeuristicComparison(
        comparison_id=COMPARISON_ID,
        candidate_count=CANDIDATE_COUNT,
        evaluation_budget=EVALUATION_BUDGET,
        baseline=baseline,
        heuristic=heuristic_run,
    )
