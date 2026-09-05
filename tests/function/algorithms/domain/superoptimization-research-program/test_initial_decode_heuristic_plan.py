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
#   - Preregistration invariants for the three-word initial-decode heuristic.
# - Must-Not:
#   - Execute or characterize the holdout verifier or observe search outcomes.
# - Allows:
#   - Inputs: the checked-in heuristic plan only.
#   - Outputs: frozen identity, budget, feature, and closed-gate assertions.
#   - Side effects: none.
# - Split-When:
#   - Another heuristic or holdout challenge gains independent preregistration.
# - Merge-When:
#   - One plan test owns this exact experiment identity.
# - Summary:
#   - Freeze heuristic search before any holdout candidate is verified.
# - Description:
#   - Locks a static initial-decode feature and equal 50,000-evaluation budget.
# - Usage:
#   - Run before challenge implementation and all real measurement.
# - Defaults:
#   - Results remain forbidden while any experiment component is unregistered.
#

"""Preregistration checks for the three-word initial-decode heuristic."""

from pathlib import Path
import tomllib
from typing import cast

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/initial-decode-heuristic-plan.toml"
)
_PLAN_ID = "classic-three-word-initial-halt-heuristic-v1"
_CHALLENGE_ID = "classic-three-word-verified-block-search-v1"
_CANDIDATES = 830_584
_BUDGET = 50_000
_WALL_SECONDS = 60
_WORKLOAD_SHA256 = (
    "03276bbed2b81d90553fa9ddca6046602108f992c48520554651638c626409d4"
)
_FEATURE = "initial-positional-decode-only-v1"
_SCORE = "earliest-position-decoding-to-halt-else-three-v1"
_BASELINE = "deterministic-enumeration-v1"
_HEURISTIC = "initial-decode-halt-proximity-order-v1"
_MEASURED = "measured"
_REGISTERED = "registered"


def _document() -> dict[str, object]:
    return cast("dict[str, object]", tomllib.loads(_PLAN.read_text()))


def _table(name: str) -> dict[str, object]:
    return cast("dict[str, object]", _document()[name])


def test_heuristic_plan_freezes_holdout_identity_before_execution() -> None:
    """The three-word corpus has stable identity without outcome evidence."""
    plan = _table("plan")
    challenge = _table("challenge")
    assert plan["id"] == _PLAN_ID
    assert plan["status"] == _MEASURED
    assert challenge["id"] == _CHALLENGE_ID
    assert challenge["candidate_count"] == _CANDIDATES
    assert challenge["status"] == _REGISTERED
    assert challenge["workload_sha256"] == _WORKLOAD_SHA256


def test_heuristic_plan_freezes_equal_search_budget() -> None:
    """Baseline and heuristic share one fixed evaluation and wall budget."""
    comparison = _table("comparison")
    assert comparison["evaluation_budget"] == _BUDGET
    assert comparison["wall_clock_seconds"] == _WALL_SECONDS
    assert comparison["baseline_order"] == _BASELINE
    assert comparison["heuristic_order"] == _HEURISTIC


def test_heuristic_feature_cannot_consume_verifier_or_dynamic_state() -> None:
    """The schedule sees only initial positional decode plus candidate index."""
    heuristic = _table("heuristic")
    assert heuristic["feature"] == _FEATURE
    assert heuristic["score"] == _SCORE
    assert heuristic["score_domain"] == [0, 1, 2, 3]
    assert heuristic["uses_dynamic_transition"] is False
    assert heuristic["uses_verifier_outcome"] is False
    assert heuristic["uses_accepted_set"] is False
    assert heuristic["uses_training_data"] is False


def test_heuristic_plan_results_gate_opens_only_after_retained_provenance(
) -> None:
    """Results become admissible only with registered retained provenance."""
    gate = _table("measurement_gate")
    assert gate["challenge_status"] == _REGISTERED
    assert gate["schedule_status"] == _REGISTERED
    assert gate["runner_status"] == _REGISTERED
    assert gate["protocol_status"] == _REGISTERED
    assert gate["retained_provenance_status"] == _REGISTERED
    assert gate["results_allowed"] is True
