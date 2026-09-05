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
#   - Preregistration invariants for training-only learned guidance.
# - Must-Not:
#   - Execute or characterize the four-word holdout verifier.
# - Allows:
#   - Inputs: the checked-in learned-guidance plan only.
#   - Outputs: frozen train/holdout/model/budget/gate assertions.
#   - Side effects: none.
# - Split-When:
#   - Another learned model or holdout gains independent preregistration.
# - Merge-When:
#   - One plan test owns this exact experiment identity.
# - Summary:
#   - Freeze learned guidance before any four-word holdout outcome exists.
# - Description:
#   - Locks training identity, deterministic holdout, model, and equal budget.
# - Usage:
#   - Run before implementing or executing the holdout verifier.
# - Defaults:
#   - Results remain forbidden until every execution component is registered.
#

"""Preregistration checks for training-only learned guidance."""

from pathlib import Path
import tomllib
from typing import cast

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/learned-guidance-plan.toml"
)
_PLAN_ID = "classic-four-word-training-only-guidance-v1"
_TRAINING_ID = "classic-three-word-verified-block-search-v1"
_HOLDOUT_ID = "classic-four-word-learned-guidance-holdout-v1"
_MODEL_ID = "laplace-pooled-initial-decode-guidance-v1"
_TRAINING_COUNT = 830_584
_HOLDOUT_COUNT = 100_000
_FULL_COUNT = 78_074_896
_BUDGET = 50_000
_STRIDE = 104_729
_SCALE = 1_000_000
_REGISTERED = "registered"
_MEASURED = "measured"
_UNREGISTERED = "unregistered"
_UNCHARACTERIZED = "uncharacterized"
_PRIMARY = "first-verified-evaluation"
_REPETITIONS = 5
_TRAINING_POLICY = "fit-from-scratch-inside-each-learned-repetition"
_HOLDOUT_SHA = (
    "54edc48898f06d1652150e5defb80ffce9e98a386cf5d07615c8182cdde33fcc"
)
_SELECTED_SHA = (
    "28f8e60161e71c364702a2fd3618c333e82aff17df737a9c8709ea97080a99d4"
)


def _doc() -> dict[str, object]:
    return cast("dict[str, object]", tomllib.loads(_PLAN.read_text()))


def _table(name: str) -> dict[str, object]:
    return cast("dict[str, object]", _doc()[name])


def test_learned_plan_freezes_training_without_holdout_labels() -> None:
    """Training is old evidence; four-word holdout remains uncharacterized."""
    assert _table("plan")["id"] == _PLAN_ID
    assert _table("plan")["status"] == _MEASURED
    training = _table("training")
    holdout = _table("holdout")
    assert training["challenge_id"] == _TRAINING_ID
    assert training["candidate_count"] == _TRAINING_COUNT
    assert training["status"] == _REGISTERED
    assert holdout["challenge_id"] == _HOLDOUT_ID
    assert holdout["full_candidate_count"] == _FULL_COUNT
    assert holdout["candidate_count"] == _HOLDOUT_COUNT
    assert holdout["selection_stride"] == _STRIDE
    assert holdout["selected_index_sha256"] == _SELECTED_SHA
    assert holdout["workload_sha256"] == _HOLDOUT_SHA
    assert holdout["status"] == _REGISTERED


def test_model_is_training_only_and_integer_deterministic() -> None:
    """The preregistered learner cannot consume holdout outcomes or dynamics."""
    model = _table("model")
    assert model["id"] == _MODEL_ID
    assert model["integer_scale"] == _SCALE
    assert model["uses_holdout_outcome"] is False
    assert model["uses_dynamic_transition"] is False
    assert model["uses_candidate_quality_as_feature"] is False


def test_comparison_uses_equal_first_hit_budget_and_training_cost(
) -> None:
    """Learned guidance keeps equal work bounds and visible fit cost."""
    comparison = _table("comparison")
    measurement = _table("measurement")
    assert comparison["evaluation_budget"] == _BUDGET
    assert comparison["primary_metric"] == _PRIMARY
    assert measurement["repetitions"] == _REPETITIONS
    assert measurement["training_policy"] == _TRAINING_POLICY


def test_results_gate_is_closed_before_holdout_execution() -> None:
    """Preregistration cannot become learned-guidance holdout evidence."""
    gate = _table("measurement_gate")
    assert gate["plan_status"] == _REGISTERED
    assert gate["training_status"] == _REGISTERED
    assert gate["holdout_status"] == _REGISTERED
    assert gate["model_status"] == _REGISTERED
    assert gate["runner_status"] == _REGISTERED
    assert gate["retained_provenance_status"] == _REGISTERED
    assert gate["results_allowed"] is True
