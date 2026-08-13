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
#   - Preregistration evidence for exact history-residue canonicalization.
# - Must-Not:
#   - Claim measurements, widen applicability, or replace independent
#     verification.
# - Allows:
#   - Inputs: tracked plan and formal optimization specification.
#   - Outputs: exact identity, budget, equation, and measurement-gate
#     assertions.
#   - Side effects: repository-local reads only.
# - Split-When:
#   - Measured evidence gains an independent protocol or retained lifecycle.
# - Merge-When:
#   - Shared preregistration tests own this exact record shape.
# - Summary:
#   - Lock the history canonicalization comparison before implementation or
#     runs.
# - Description:
#   - Binds exact algebraic applicability to a future equal-budget comparison.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Measured interpretation requires the frozen protocol and retained pin.
#

"""Preregistration checks for exact history-residue canonicalization."""

from pathlib import Path
import tomllib
from typing import cast

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/history-canonicalization-plan.toml"
)
_TEX = _ROOT / (
    "src/specification/formal-model/math/algorithms/"
    "malbolge-specific-optimization-mathematics.tex"
)
_PLAN_ID = "classic-history-residue-canonicalization-v1"
_TECHNIQUE = "exact-history-residue-state-v1"
_BASELINE = "raw-visit-count-state-v1"
_SELF_ENCRYPTION = "eq:optimization-encryption-orbit"
_ROTATE_HISTORY = "eq:optimization-rotate-history"
_PRIMARY_METRIC = "unique-search-states"
_EVALUATION_BUDGET = 10_000
_WALL_CLOCK_SECONDS = 60
_MEMORY_MIB = 512
_REGISTERED = "registered"
_ACCEPTED_SET_REJECTION = "verified accepted-set differs from baseline"
_APPLICABILITY_REJECTION = (
    "applicability cannot be checked before canonicalization"
)
_CHALLENGE_ID = "classic-history-residue-search-v1"
_RUNNER_ID = "classic-history-residue-comparison-v1"
_CANDIDATE_COUNT = 10_000
_WORKLOAD_SHA256 = (
    "f300a5adf717027eb11c850b4a8b292bf0bac7fe0cde6bdb9be9d2f7f504d103"
)
_MEASUREMENT_ID = "history-residue-five-paired-protocol-v1"
_REPETITIONS = 5
_ORDERING = "fixed-raw-then-canonicalized"
_RETAIN_ALL = "retain-all"


def test_history_canonicalization_plan_retains_measured_identity() -> None:
    """Lock the measured plan identity and original comparison bounds."""
    document = tomllib.loads(_PLAN.read_text(encoding="utf-8"))
    plan = cast("dict[str, object]", document["plan"])
    comparison = cast("dict[str, object]", document["comparison"])
    challenge = cast("dict[str, object]", document["challenge"])
    runner = cast("dict[str, object]", document["runner"])

    assert plan == {
        "id": _PLAN_ID,
        "record_kind": "plan",
        "status": "measured",
        "method_class": "optimization",
        "technique": _TECHNIQUE,
        "baseline": _BASELINE,
    }
    assert comparison["primary_metric"] == _PRIMARY_METRIC
    assert comparison["evaluation_budget"] == _EVALUATION_BUDGET
    assert comparison["wall_clock_seconds"] == _WALL_CLOCK_SECONDS
    assert comparison["memory_mib"] == _MEMORY_MIB
    assert challenge["id"] == _CHALLENGE_ID
    assert challenge["candidate_count"] == _CANDIDATE_COUNT
    assert challenge["workload_sha256"] == _WORKLOAD_SHA256
    assert runner["id"] == _RUNNER_ID
    assert runner["baseline"] == _BASELINE
    assert runner["canonicalized"] == _TECHNIQUE


def test_history_measurement_protocol_has_retained_provenance() -> None:
    """Keep the frozen protocol and its retained source-pinned run."""
    document = tomllib.loads(_PLAN.read_text(encoding="utf-8"))
    measurement = cast("dict[str, object]", document["measurement"])
    gate = cast("dict[str, object]", document["measurement_gate"])

    assert measurement["id"] == _MEASUREMENT_ID
    assert measurement["repetitions"] == _REPETITIONS
    assert measurement["warmup_iterations"] == 0
    assert measurement["ordering"] == _ORDERING
    assert measurement["outlier_policy"] == _RETAIN_ALL
    assert measurement["per_strategy_wall_clock_seconds"] == _WALL_CLOCK_SECONDS
    assert gate["challenge_status"] == _REGISTERED
    assert gate["runner_status"] == _REGISTERED
    assert gate["protocol_status"] == _REGISTERED
    assert gate["retained_provenance_status"] == _REGISTERED
    assert gate["results_allowed"] is True


def test_history_canonicalization_plan_binds_existing_formal_equations(
) -> None:
    """Keep the plan bound to its proved formal equations."""
    document = tomllib.loads(_PLAN.read_text(encoding="utf-8"))
    formal = cast("dict[str, object]", document["formal_basis"])
    source = _TEX.read_text(encoding="utf-8")

    assert formal["self_encryption_equation"] == _SELF_ENCRYPTION
    assert formal["rotate_history_equation"] == _ROTATE_HISTORY
    assert rf"\label{{{_SELF_ENCRYPTION}}}" in source
    assert rf"\label{{{_ROTATE_HISTORY}}}" in source


def test_history_canonicalization_plan_keeps_applicability_fail_closed(
) -> None:
    """Require stable address identity and no intervening write."""
    document = tomllib.loads(_PLAN.read_text(encoding="utf-8"))
    applicability = cast("dict[str, object]", document["applicability"])
    rejection = cast("dict[str, object]", document["rejection"])

    assert applicability["requires_same_address_identity"] is True
    assert applicability["requires_no_intervening_write"] is True
    conditions = cast("list[str]", rejection["conditions"])
    assert _ACCEPTED_SET_REJECTION in conditions
    assert _APPLICABILITY_REJECTION in conditions
