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
#   - Preregistration evidence for exact repeated-batch verified-result reuse.
# - Must-Not:
#   - Implement reuse, claim timing, or permit non-exact cache identity.
# - Allows:
#   - Inputs: tracked reuse plan and frozen classic challenge identity.
#   - Outputs: workload, bounds, reuse key, rejection, and gate assertions.
#   - Side effects: repository-local reads only.
# - Split-When:
#   - Runner or retained measurement evidence gains an independent lifecycle.
# - Merge-When:
#   - Shared preregistration tests own this exact record shape.
# - Summary:
#   - Freeze two-pass exact verified-result reuse before implementation.
# - Description:
#   - The second pass may reuse only the identical frozen candidate index.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Results remain forbidden until runner, protocol, and provenance register.
#

"""Preregistration checks for exact two-pass verified-result reuse."""

from hashlib import sha256
import json
from pathlib import Path
import tomllib
from typing import cast

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/verified-block-reuse-plan.toml"
)
_PLAN_ID = "classic-two-pass-verified-block-reuse-v1"
_BASE_CHALLENGE = "classic-verified-block-search-v1"
_BASE_CANDIDATES = 8_836
_PASSES = 2
_REQUESTS = _BASE_CANDIDATES * _PASSES
_ENCODING = "two-complete-lexicographic-passes-v1"
_BASE_SHA256 = (
    "eb739238b375fde435e3948896f385e6be9ab5002078b242c2826153ce1810fc"
)
_WORKLOAD_SHA256 = (
    "d86f190a512b64724b9546c72f2ee56973292e6ef5707378f8c9a9ba2050bbc7"
)
_RUNNER_ID = "classic-two-pass-verified-block-reuse-comparison-v1"
_TECHNIQUE = "exact-candidate-verified-result-reuse-v1"
_BASELINE = "per-request-independent-verification-v1"
_EQUIVALENCE = "exact-request-index-quality-map-v1"
_REUSE_KEY = "exact-frozen-candidate-index-v1"
_REGISTERED = "registered"
_UNREGISTERED = "unregistered"
_PREREGISTERED = "preregistered"


def _document() -> dict[str, object]:
    return cast(
        "dict[str, object]",
        tomllib.loads(_PLAN.read_text(encoding="utf-8")),
    )


def test_reuse_plan_locks_two_complete_frozen_corpus_passes() -> None:
    """Repeated workload identity is exact and independently reproducible."""
    document = _document()
    challenge = cast("dict[str, object]", document["challenge"])
    comparison = cast("dict[str, object]", document["comparison"])
    assert challenge["id"] == _PLAN_ID
    assert challenge["base_challenge"] == _BASE_CHALLENGE
    assert challenge["base_candidate_count"] == _BASE_CANDIDATES
    assert challenge["passes"] == _PASSES
    assert challenge["request_encoding"] == _ENCODING
    assert challenge["base_workload_sha256"] == _BASE_SHA256
    assert comparison["request_count"] == _REQUESTS
    assert comparison["unique_candidate_count"] == _BASE_CANDIDATES

    payload = json.dumps(
        {
            "base_candidate_count": _BASE_CANDIDATES,
            "base_workload_sha256": _BASE_SHA256,
            "passes": _PASSES,
            "request_encoding": _ENCODING,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    assert sha256(payload).hexdigest() == _WORKLOAD_SHA256
    assert challenge["workload_sha256"] == _WORKLOAD_SHA256


def test_reuse_plan_requires_exact_identity_and_complete_final_map() -> None:
    """Cache reuse cannot cross candidate identity or hide request coverage."""
    reuse = cast("dict[str, object]", _document()["reuse"])
    assert reuse["key"] == _REUSE_KEY
    assert reuse["requires_exact_candidate_identity"] is True
    assert reuse["requires_complete_request_coverage"] is True
    assert reuse["requires_independent_final_map_equality"] is True


def test_reuse_plan_registers_only_the_comparison_identity() -> None:
    """Plan identity is fixed while its runner remains unimplemented."""
    document = _document()
    plan = cast("dict[str, object]", document["plan"])
    runner = cast("dict[str, object]", document["runner"])
    assert plan["id"] == _PLAN_ID
    assert plan["status"] == _PREREGISTERED
    assert plan["technique"] == _TECHNIQUE
    assert plan["baseline"] == _BASELINE
    assert runner["id"] == _RUNNER_ID
    assert runner["semantic_equivalence"] == _EQUIVALENCE
    assert runner["status"] == _REGISTERED


def test_reuse_plan_measurement_gate_opens_after_retained_provenance() -> None:
    """Source-pinned retained provenance opens comparative interpretation."""
    gate = cast("dict[str, object]", _document()["measurement_gate"])
    assert gate["challenge_status"] == _REGISTERED
    assert gate["runner_status"] == _REGISTERED
    assert gate["protocol_status"] == _REGISTERED
    assert gate["retained_provenance_status"] == _REGISTERED
    assert gate["results_allowed"] is True
