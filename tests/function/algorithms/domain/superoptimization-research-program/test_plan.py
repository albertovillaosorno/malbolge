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
#   - Exact executable evidence for the preregistered superoptimization pilot.
# - Must-Not:
#   - Claim a benchmark result, execute search, or replace manifest validation.
# - Allows:
#   - Inputs: the versioned experiment and lifecycle TOML records.
# - Outputs:
#   - Deterministic assertions over the fixed pilot identity and stopping
#     bounds.
# - Side effects:
#   - Repository-local reads only.
# - Split-When:
#   - Recorded runs gain an independently governed evidence contract.
# - Merge-When:
#   - A shared experiment-plan test owns these exact preregistration invariants.
# - Summary:
#   - Lock the first superoptimization comparison before measurements exist.
# - Description:
#   - Keeps seed, profile, budget, baseline, verifier, and lifecycle explicit.
# - Usage:
#   - Run through the repository Python validation suite.
# - Defaults:
#   - Any drift in the preregistered pilot identity fails closed.
#

"""Executable identity checks for the first superoptimization pilot plan."""

from pathlib import Path
import tomllib
from typing import cast

_ROOT = Path(__file__).resolve().parents[5]
_PLAN = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/experiment.toml"
)
_LIFECYCLE = _PLAN.with_name("lifecycle.toml")
_EXPERIMENT_ID = "superoptimization-research-program"
_RECORD_KIND = "plan"
_METHOD_CLASS = "optimization"
_CHALLENGE_FAMILY = "classic-verified-block-search-v1"
_TARGET_PROFILE = "malbolge-1998"
_TARGET_FINGERPRINT = (
    "malbolge-profile-v1:sha256:"
    "8b8689e5e3daef745d58681efe78106070736abb2ffa0895511fac5150b5b73e"
)
_SEED = 0
_DIFFICULTY = 1
_SECONDS = 60
_CANDIDATES = 10_000
_MEMORY_MIB = 512
_ORACLE = "trusted-semantic-verifier"
_BASELINE = "deterministic-enumeration"
_LIFECYCLE_STATE = "experimental"


def test_superoptimization_pilot_identity_is_preregistered() -> None:
    """Lock the first pilot identity and stopping bounds before any run."""
    plan = tomllib.loads(_PLAN.read_text(encoding="utf-8"))
    experiment = cast("dict[str, object]", plan["experiment"])
    challenge = cast("dict[str, object]", plan["challenge"])
    budget = cast("dict[str, object]", plan["budget"])
    verification = cast("dict[str, object]", plan["verification"])

    assert experiment == {
        "id": _EXPERIMENT_ID,
        "record_kind": _RECORD_KIND,
        "seed": _SEED,
        "method_class": _METHOD_CLASS,
    }
    assert challenge == {
        "family": _CHALLENGE_FAMILY,
        "difficulty": _DIFFICULTY,
        "target_profile": _TARGET_PROFILE,
        "target_profile_fingerprint": _TARGET_FINGERPRINT,
    }
    assert budget == {
        "seconds": _SECONDS,
        "candidate_evaluations": _CANDIDATES,
        "memory_mib": _MEMORY_MIB,
    }
    assert verification == {
        "required": True,
        "oracle": _ORACLE,
        "baseline": _BASELINE,
    }


def test_superoptimization_plan_remains_experimental_without_results() -> None:
    """Keep planning state distinct from measured or promoted evidence."""
    lifecycle_document = tomllib.loads(_LIFECYCLE.read_text(encoding="utf-8"))
    lifecycle = cast("dict[str, object]", lifecycle_document["algorithm"])
    plan = tomllib.loads(_PLAN.read_text(encoding="utf-8"))
    experiment = cast("dict[str, object]", plan["experiment"])
    assert lifecycle["id"] == _EXPERIMENT_ID
    assert lifecycle["state"] == _LIFECYCLE_STATE
    assert experiment["record_kind"] == _RECORD_KIND
