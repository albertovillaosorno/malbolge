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
#   - Exact executable evidence for the preregistered superoptimization pilot.
# - Must-Not:
#   - Claim a benchmark result, execute search, or replace manifest validation.
# - Allows:
#   - Inputs: the versioned experiment and lifecycle TOML records.
#   - Outputs: deterministic assertions over fixed pilot identity and bounds.
#   - Side effects: repository-local reads only.
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
_ORACLE = "classic-two-word-no-io-halt-v1"
_BASELINE = "deterministic-enumeration"
_LIFECYCLE_STATE = "experimental"
_CORPUS_CANDIDATES = 8_836
_CANDIDATE_ENCODING = "lexicographic-two-graphical-bytes-v1"
_OBJECTIVE = "halt-without-prior-input-or-output"
_QUALITY = "semantic-transitions-to-halt-v1"
_SOURCE_WORDS = 2
_MEASUREMENT_REPETITIONS = 5
_MEASUREMENT_WARMUPS = 0
_MEASUREMENT_ORDERING = "fixed-enumeration-then-seeded"
_MEASUREMENT_OUTLIER = "retain-all"
_MEASUREMENT_CENTER = "median"
_MEASUREMENT_DISPERSION = "observed-range"
_MEASUREMENT_UNCERTAINTY = "observed-range"
_WORKLOAD_SHA256 = (
    "eb739238b375fde435e3948896f385e6be9ab5002078b242c2826153ce1810fc"
)


def test_superoptimization_pilot_identity_is_preregistered() -> None:
    """Lock the first pilot identity and stopping bounds before any run."""
    plan = tomllib.loads(_PLAN.read_text(encoding="utf-8"))
    experiment = cast("dict[str, object]", plan["experiment"])
    challenge = cast("dict[str, object]", plan["challenge"])
    budget = cast("dict[str, object]", plan["budget"])
    verification = cast("dict[str, object]", plan["verification"])
    challenge_semantics = cast(
        "dict[str, object]", plan["classic_block_search"]
    )
    measurement = cast("dict[str, object]", plan["measurement"])

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
    assert challenge_semantics == {
        "candidate_count": _CORPUS_CANDIDATES,
        "candidate_encoding": _CANDIDATE_ENCODING,
        "objective": _OBJECTIVE,
        "quality": _QUALITY,
        "source_words": _SOURCE_WORDS,
        "verifier": _ORACLE,
        "workload_sha256": _WORKLOAD_SHA256,
    }
    assert measurement == {
        "repetitions": _MEASUREMENT_REPETITIONS,
        "warmup_iterations": _MEASUREMENT_WARMUPS,
        "ordering": _MEASUREMENT_ORDERING,
        "outlier_policy": _MEASUREMENT_OUTLIER,
        "center": _MEASUREMENT_CENTER,
        "dispersion": _MEASUREMENT_DISPERSION,
        "uncertainty": _MEASUREMENT_UNCERTAINTY,
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
