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
#   - Preregistration evidence for exact classic crazy preimage pruning.
# - Must-Not:
#   - Claim measurements, widen beyond classic words, or replace verification.
# - Allows:
#   - Inputs: tracked plan, formal equations, and production preparer identity.
#   - Outputs: exact identity, bound, applicability, and gate assertions.
#   - Side effects: repository-local reads only.
# - Split-When:
#   - A registered challenge/runner or retained measurement needs new evidence.
# - Merge-When:
#   - Shared preregistration tests own this exact record shape.
# - Summary:
#   - Lock exact crazy preimage pruning before comparative measurement.
# - Description:
#   - Binds the production digitwise preparer to proved complete-domain bounds.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Results remain forbidden until every measurement gate is registered.
#

"""Preregistration checks for exact classic crazy preimage pruning."""

from pathlib import Path
import tomllib
from typing import cast

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/crazy-preimage-pruning-plan.toml"
)
_TEX = _ROOT / (
    "src/specification/formal-model/math/algorithms/"
    "malbolge-specific-optimization-mathematics.tex"
)
_IMPLEMENTATION = _ROOT / (
    "src/optimization/optimizer/application/optimizer/crazy_target.py"
)
_PLAN_ID = "classic-crazy-exact-preimage-pruning-v1"
_TECHNIQUE = "classic-crazy-digitwise-exact-preimage-v1"
_BASELINE = "classic-crazy-full-domain-data-enumeration-v1"
_PREIMAGE_CARDINALITY = "eq:optimization-crazy-preimage-cardinality"
_PREIMAGE_BOUND = "eq:optimization-crazy-preimage-bound"
_FULL_DOMAIN_WORDS = 59_049
_MAXIMUM_PREIMAGES = 1_024
_PRIMARY_METRIC = "evaluated-data-candidates"
_PREIMAGE_SET_REJECTION = "exact preimage set differs from full-domain baseline"
_UNREACHABLE_REJECTION = "unreachable targets are treated as having a candidate"
_UNREGISTERED = "unregistered"
_REGISTERED = "registered"
_CHALLENGE_ID = "classic-crazy-preimage-cardinality-span-v1"
_RUNNER_ID = "classic-crazy-preimage-structural-comparison-v1"
_SEMANTIC_EQUIVALENCE = "exact-sorted-preimage-set-v1"
_MEASUREMENT_ID = "crazy-preimage-five-paired-protocol-v1"
_REPETITIONS = 5
_ORDERING = "fixed-full-domain-then-exact"
_RETAIN_ALL = "retain-all"
_CLOCK = "time-perf-counter-ns"
_TIMING_SCOPE = "strategy-run-including-independent-semantic-check"
_WALL_SECONDS = 60
_PROBLEM_COUNT = 12
_WORKLOAD_SHA256 = (
    "2b0c969c46511a67fae4b977fdfa6cb0b6019740ed81c018d6150b03d8387d15"
)


def _document() -> dict[str, object]:
    return cast(
        "dict[str, object]",
        tomllib.loads(_PLAN.read_text(encoding="utf-8")),
    )


def test_crazy_preimage_plan_locks_identity_and_exact_bounds() -> None:
    """Keep the baseline, production technique, and classic bounds fixed."""
    document = _document()
    plan = cast("dict[str, object]", document["plan"])
    comparison = cast("dict[str, object]", document["comparison"])

    assert plan == {
        "id": _PLAN_ID,
        "record_kind": "plan",
        "status": "measured",
        "method_class": "optimization",
        "technique": _TECHNIQUE,
        "baseline": _BASELINE,
    }
    assert comparison["primary_metric"] == _PRIMARY_METRIC
    assert comparison["full_domain_data_words"] == _FULL_DOMAIN_WORDS
    assert comparison["maximum_exact_preimages"] == _MAXIMUM_PREIMAGES


def test_crazy_preimage_plan_binds_formal_and_product_identity() -> None:
    """The plan names proved equations and the existing exact preparer."""
    document = _document()
    formal = cast("dict[str, object]", document["formal_basis"])
    tex = _TEX.read_text(encoding="utf-8")
    implementation = _IMPLEMENTATION.read_text(encoding="utf-8")

    assert formal["preimage_cardinality_equation"] == _PREIMAGE_CARDINALITY
    assert formal["preimage_bound_equation"] == _PREIMAGE_BOUND
    assert rf"\label{{{_PREIMAGE_CARDINALITY}}}" in tex
    assert rf"\label{{{_PREIMAGE_BOUND}}}" in tex
    preparer_identity = f'CRAZY_TARGET_SELECTION_PREPARER_ID = "{_TECHNIQUE}"'
    assert preparer_identity in implementation


def test_crazy_preimage_plan_registers_frozen_challenge_and_runner() -> None:
    """Lock the finite challenge/runner without opening measurement results."""
    document = _document()
    challenge = cast("dict[str, object]", document["challenge"])
    runner = cast("dict[str, object]", document["runner"])

    assert challenge["id"] == _CHALLENGE_ID
    assert challenge["problem_count"] == _PROBLEM_COUNT
    assert challenge["workload_sha256"] == _WORKLOAD_SHA256
    assert runner["id"] == _RUNNER_ID
    assert runner["baseline"] == _BASELINE
    assert runner["technique"] == _TECHNIQUE
    assert runner["semantic_equivalence"] == _SEMANTIC_EQUIVALENCE


def test_crazy_preimage_plan_registers_measurement_protocol() -> None:
    """Freeze paired timing mechanics while retained provenance stays absent."""
    document = _document()
    measurement = cast("dict[str, object]", document["measurement"])

    assert measurement["id"] == _MEASUREMENT_ID
    assert measurement["repetitions"] == _REPETITIONS
    assert measurement["warmup_iterations"] == 0
    assert measurement["ordering"] == _ORDERING
    assert measurement["outlier_policy"] == _RETAIN_ALL
    assert measurement["clock"] == _CLOCK
    assert measurement["timing_scope"] == _TIMING_SCOPE
    assert measurement["per_strategy_wall_clock_seconds"] == _WALL_SECONDS


def test_crazy_preimage_plan_keeps_classic_applicability_fail_closed() -> None:
    """Exact pruning stays bound to one complete classic fixed-input problem."""
    document = _document()
    applicability = cast("dict[str, object]", document["applicability"])
    rejection = cast("dict[str, object]", document["rejection"])

    assert applicability == {
        "word_trits": 10,
        "word_modulus": _FULL_DOMAIN_WORDS,
        "requires_fixed_accumulator": True,
        "requires_fixed_target": True,
        "requires_complete_classic_data_domain": True,
    }
    conditions = cast("list[str]", rejection["conditions"])
    assert _PREIMAGE_SET_REJECTION in conditions
    assert _UNREACHABLE_REJECTION in conditions


def test_crazy_preimage_plan_has_retained_measurement_provenance() -> None:
    """All lifecycle gates open only after source-pinned evidence exists."""
    gate = cast("dict[str, object]", _document()["measurement_gate"])

    assert gate["challenge_status"] == _REGISTERED
    assert gate["runner_status"] == _REGISTERED
    assert gate["protocol_status"] == _REGISTERED
    assert gate["retained_provenance_status"] == _REGISTERED
    assert gate["results_allowed"] is True
