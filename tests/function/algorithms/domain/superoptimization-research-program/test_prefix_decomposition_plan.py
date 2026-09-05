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
#   - Preregistration evidence for exact classic prefix decomposition.
# - Must-Not:
#   - Claim measurements, reopen the results gate, or weaken final verification.
# - Allows:
#   - Inputs: tracked plan and the frozen classic superoptimization challenge.
#   - Outputs: exact identity, bounds, applicability, and closed-gate
#     assertions.
#   - Side effects: repository-local reads only.
# - Split-When:
#   - Retained measurement evidence gains an independent lifecycle.
# - Merge-When:
#   - Shared preregistration tests own this exact record shape.
# - Summary:
#   - Lock prefix decomposition and registered runner before measurement.
# - Description:
#   - Requires exact suffix-independence proof before any prefix result reuse.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Results stay forbidden until protocol and provenance register.
#

"""Preregistration checks for exact classic prefix decomposition."""

from pathlib import Path
import tomllib
from typing import cast

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/prefix-decomposition-plan.toml"
)
_EXPERIMENT = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/experiment.toml"
)
_PLAN_ID = "classic-two-word-prefix-decomposition-v1"
_TECHNIQUE = "exact-first-step-prefix-decomposition-v1"
_BASELINE = "full-candidate-independent-verification-v1"
_CHALLENGE_ID = "classic-verified-block-search-v1"
_VERIFIER_ID = "classic-two-word-no-io-halt-v1"
_RUNNER_ID = "classic-two-word-prefix-decomposition-comparison-v1"
_EQUIVALENCE_ID = "exact-candidate-index-quality-map-v1"
_CANDIDATE_COUNT = 8_836
_PRIMARY_METRIC = "independent-verifier-calls"
_WALL_CLOCK_SECONDS = 60
_MEMORY_MIB = 512
_WORKLOAD_SHA256 = (
    "eb739238b375fde435e3948896f385e6be9ab5002078b242c2826153ce1810fc"
)
_MAP_REJECTION = (
    "candidate-index quality map differs from full-verification baseline"
)
_PROOF_REJECTION = (
    "a reused prefix lacks exact proof that suffix cannot change its result"
)
_REGISTERED = "registered"
_UNREGISTERED = "unregistered"


def _document() -> dict[str, object]:
    return cast(
        "dict[str, object]",
        tomllib.loads(_PLAN.read_text(encoding="utf-8")),
    )


def test_prefix_decomposition_plan_locks_frozen_challenge_identity() -> None:
    """Reuse the existing corpus and verifier rather than inventing evidence."""
    document = _document()
    plan = cast("dict[str, object]", document["plan"])
    challenge = cast("dict[str, object]", document["challenge"])
    experiment = cast(
        "dict[str, object]",
        tomllib.loads(_EXPERIMENT.read_text(encoding="utf-8")),
    )
    frozen = cast("dict[str, object]", experiment["classic_block_search"])

    assert plan == {
        "id": _PLAN_ID,
        "record_kind": "plan",
        "status": "preregistered",
        "method_class": "optimization",
        "technique": _TECHNIQUE,
        "baseline": _BASELINE,
    }
    assert challenge["id"] == _CHALLENGE_ID
    assert challenge["candidate_count"] == _CANDIDATE_COUNT
    assert challenge["verifier"] == _VERIFIER_ID
    assert challenge["workload_sha256"] == _WORKLOAD_SHA256
    assert challenge["candidate_count"] == frozen["candidate_count"]
    assert challenge["workload_sha256"] == frozen["workload_sha256"]


def test_prefix_decomposition_plan_fixes_equal_bounds_and_equivalence() -> None:
    """Keep work comparison and exact semantic equality explicit."""
    document = _document()
    comparison = cast("dict[str, object]", document["comparison"])
    runner = cast("dict[str, object]", document["runner"])

    assert comparison["primary_metric"] == _PRIMARY_METRIC
    assert comparison["candidate_evaluation_budget"] == _CANDIDATE_COUNT
    assert comparison["wall_clock_seconds"] == _WALL_CLOCK_SECONDS
    assert comparison["memory_mib"] == _MEMORY_MIB
    assert runner["id"] == _RUNNER_ID
    assert runner["baseline"] == _BASELINE
    assert runner["technique"] == _TECHNIQUE
    assert runner["semantic_equivalence"] == _EQUIVALENCE_ID
    assert runner["status"] == _REGISTERED


def test_prefix_decomposition_requires_proof_before_reuse() -> None:
    """No suffix may be skipped merely because one representative matched."""
    document = _document()
    decomposition = cast("dict[str, object]", document["decomposition"])
    rejection = cast("dict[str, object]", document["rejection"])

    assert decomposition == {
        "prefix_words": 1,
        "suffix_words": 1,
        "graphical_values_per_word": 94,
        "requires_suffix_independence_proof_before_reuse": True,
        "requires_complete_candidate_coverage": True,
        "requires_independent_final_map_equality": True,
    }
    conditions = cast("list[str]", rejection["conditions"])
    assert _MAP_REJECTION in conditions
    assert _PROOF_REJECTION in conditions


def test_prefix_decomposition_measurement_gate_stays_closed() -> None:
    """Preregistration alone cannot become comparative result evidence."""
    gate = cast("dict[str, object]", _document()["measurement_gate"])

    assert gate["challenge_status"] == _REGISTERED
    assert gate["runner_status"] == _REGISTERED
    assert gate["protocol_status"] == _UNREGISTERED
    assert gate["retained_provenance_status"] == _UNREGISTERED
    assert gate["results_allowed"] is False
