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
#   - Equal-budget verifier-gated comparison over opaque finite candidates.
# - Must-Not:
#   - Define candidate semantics, trust schedules as acceptance, or claim
#     timing.
# - Allows:
#   - Inputs: finite dimensions, seed, and one deterministic trusted verifier.
#   - Outputs: evaluation-count, first-hit, best-quality, and null outcomes.
#   - Side effects: invokes only the caller-supplied verifier callback.
# - Split-When:
#   - Candidate-language semantics or measured-run evidence gains ownership.
# - Merge-When:
#   - A shared research execution harness owns this exact comparison contract.
# - Summary:
#   - Deterministic equal-budget superoptimization comparison substrate.
# - Description:
#   - Applies one trusted verifier to enumeration and seeded candidate orders.
# - Usage:
#   - Research pilots may bind concrete candidate semantics above this module.
# - Defaults:
#   - Invalid verifier quality results fail closed and no timing is inferred.
#

"""Verifier-gated equal-budget substrate for superoptimization research."""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from typing import Protocol
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Callable


class _ScheduleModule(Protocol):
    ENUMERATION_SCHEDULE_ID: str
    SEEDED_PROPOSAL_SCHEDULE_ID: str

    def enumeration_order(
        self,
        candidate_count: int,
        evaluation_budget: int,
    ) -> tuple[int, ...]: ...

    def seeded_proposal_order(
        self,
        candidate_count: int,
        evaluation_budget: int,
        seed: int,
    ) -> tuple[int, ...]: ...


def _load_schedule() -> _ScheduleModule:
    path = Path(__file__).with_name("schedule.py")
    spec = importlib.util.spec_from_file_location(
        "superoptimization_runner_schedule",
        path,
    )
    if spec is None or spec.loader is None:
        message = "superoptimization schedule module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast("_ScheduleModule", cast("object", module))


_SCHEDULE = _load_schedule()

_MAX_U64 = (1 << 64) - 1
_OUTCOME_FOUND = "verified-candidate-found"
_OUTCOME_NONE = "no-verified-candidate"
VERIFIER_GATED_COMPARISON_ID = "finite-verifier-gated-comparison-v1"

type CandidateVerifier = Callable[[int], int | None]


class InvalidVerifierResultError(ValueError):
    """One trusted verifier callback returned a malformed quality result."""


@dataclass(frozen=True, slots=True)
class ScheduleRun:
    """Deterministic result of one complete budget-bounded schedule run."""

    schedule_id: str
    evaluations: int
    verified_count: int
    first_verified_evaluation: int | None
    first_verified_candidate: int | None
    best_candidate: int | None
    best_quality: int | None
    outcome: str


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    """Equal-input enumeration and seeded proposal results."""

    comparison_id: str
    candidate_count: int
    evaluation_budget: int
    seed: int
    enumeration: ScheduleRun
    seeded: ScheduleRun


def _verified_quality(value: object) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= _MAX_U64:
        message = "trusted verifier quality must be an unsigned 64-bit integer"
        raise InvalidVerifierResultError(message)
    return value


def _run_schedule(
    order: tuple[int, ...],
    schedule_id: str,
    verifier: CandidateVerifier,
) -> ScheduleRun:
    verified_count = 0
    first_evaluation: int | None = None
    first_candidate: int | None = None
    best_candidate: int | None = None
    best_quality: int | None = None
    for evaluation, candidate in enumerate(order, start=1):
        quality = _verified_quality(verifier(candidate))
        if quality is None:
            continue
        verified_count += 1
        if first_evaluation is None:
            first_evaluation = evaluation
            first_candidate = candidate
        if best_quality is None or quality < best_quality:
            best_candidate = candidate
            best_quality = quality
    return ScheduleRun(
        schedule_id=schedule_id,
        evaluations=len(order),
        verified_count=verified_count,
        first_verified_evaluation=first_evaluation,
        first_verified_candidate=first_candidate,
        best_candidate=best_candidate,
        best_quality=best_quality,
        outcome=_OUTCOME_FOUND if verified_count else _OUTCOME_NONE,
    )


def compare_schedules(
    candidate_count: int,
    evaluation_budget: int,
    seed: int,
    *,
    verifier: CandidateVerifier,
) -> ComparisonResult:
    """Run both preregistered candidate orders through one trusted verifier.

    Returns:
        Equal-input evaluation-count and verified-quality results for both
        schedules. Every scheduled candidate is evaluated so best-quality and
        null outcomes are retained independently from time-to-first evidence.

    """
    enumeration = _SCHEDULE.enumeration_order(
        candidate_count,
        evaluation_budget,
    )
    seeded = _SCHEDULE.seeded_proposal_order(
        candidate_count,
        evaluation_budget,
        seed,
    )
    return ComparisonResult(
        comparison_id=VERIFIER_GATED_COMPARISON_ID,
        candidate_count=candidate_count,
        evaluation_budget=evaluation_budget,
        seed=seed,
        enumeration=_run_schedule(
            enumeration,
            _SCHEDULE.ENUMERATION_SCHEDULE_ID,
            verifier,
        ),
        seeded=_run_schedule(
            seeded,
            _SCHEDULE.SEEDED_PROPOSAL_SCHEDULE_ID,
            verifier,
        ),
    )
