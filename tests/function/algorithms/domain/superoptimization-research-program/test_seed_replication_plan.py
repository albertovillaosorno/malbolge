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
#   - Preregistration evidence for the classic superopt seed replication.
# - Must-Not:
#   - Observe replication outcomes or weaken the frozen base-plan identity.
# - Allows:
#   - Inputs: tracked replication plan and frozen base plan.
#   - Outputs: exact preregistered seed, metric, and identity assertions.
#   - Side effects: repository-local plan reads only.
# - Split-When:
#   - Another replication protocol gains independent lifecycle or policy.
# - Merge-When:
#   - Shared preregistration tests own this exact record shape.
# - Summary:
#   - Lock the multi-seed replication identity before measured runs.
# - Description:
#   - Binds declared seeds and metric to the immutable classic pilot plan.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Any plan or base-plan digest drift fails closed.
#

"""Preregistration evidence for the classic superopt multi-seed replication."""

from hashlib import sha256
from pathlib import Path
import tomllib
from typing import cast

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/seed-replication.toml"
)
_BASE = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/experiment.toml"
)
_EXPECTED_SEEDS = list(range(8))
_REPLICATION_ID = "classic-superopt-seed-replication-v1"
_ORDERING = "ascending-seed"
_PRIMARY_METRIC = "first_verified_evaluation"
_TIMING_INTERPRETATION = "retained-not-compared"
_CANDIDATE_COUNT = 8_836
_EVALUATION_BUDGET = 10_000
_BASE_SHA256 = (
    "0c5239e47d6ceaae0536d61fa1b8abb8c44461e5caaa04becd1a195b9a218b2c"
)


def test_seed_replication_is_preregistered_against_frozen_base_plan() -> None:
    """Lock seeds, metric, ordering, and base-plan identity before runs."""
    document = tomllib.loads(_PLAN.read_text(encoding="utf-8"))
    replication = cast("dict[str, object]", document["replication"])
    constraints = cast("dict[str, object]", document["constraints"])
    assert replication["id"] == _REPLICATION_ID
    assert replication["base_plan_sha256"] == _BASE_SHA256
    assert replication["seeds"] == _EXPECTED_SEEDS
    assert replication["repetitions_per_seed"] == 1
    assert replication["ordering"] == _ORDERING
    assert replication["primary_metric"] == _PRIMARY_METRIC
    assert replication["timing_interpretation"] == _TIMING_INTERPRETATION
    assert constraints["candidate_count"] == _CANDIDATE_COUNT
    assert constraints["evaluation_budget"] == _EVALUATION_BUDGET
    assert sha256(_BASE.read_bytes()).hexdigest() == _BASE_SHA256
