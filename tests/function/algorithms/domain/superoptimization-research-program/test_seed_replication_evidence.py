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
#   - Retained evidence for the classic superopt seed replication.
# - Must-Not:
#   - Rerun timing, discard trials, or generalize beyond the recorded seeds.
# - Allows:
#   - Inputs: tracked manifest, benchmark metadata, raw CSV, and source pin.
#   - Outputs: shared-policy and exact observed-trial assertions.
#   - Side effects: repository-local evidence reads only.
# - Split-When:
#   - Another seed replication gains independent retained evidence.
# - Merge-When:
#   - Shared benchmark evidence tests own this exact record shape.
# - Summary:
#   - Lock the preregistered eight-seed mixed replication result.
# - Description:
#   - Recomputes first-hit work conclusions from every retained seed trial.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Exact observations are evidence, not a broad performance claim.
#

"""Retained evidence for the preregistered classic superopt seed replication."""

import csv
from pathlib import Path
from statistics import median

from scripts.validate import benchmark_protocol
from scripts.validate import experiment_manifest

_ROOT = Path(__file__).resolve().parents[5]
_EVIDENCE = _ROOT / (
    "benchmarks/research/evidence/"
    "2026-08-11-classic-superopt-seed-replication-windows"
)
_BENCHMARK = _EVIDENCE / "benchmark.toml"
_EXPERIMENT = _EVIDENCE / "experiment.toml"
_RAW = _EVIDENCE / "raw.csv"
_SOURCE_COMMIT = _EVIDENCE / "source-commit.txt"
_COMMIT = "f2dcc67aa313a7d0279ba081479bf4f9b46ebd0d"
_SEEDED_FIRST = (250, 1709, 642, 1142, 189, 1861, 506, 804)
_ENUM_FIRST = 706
_CANDIDATES = 8_836
_VERIFIED = 10
_BEST_QUALITY = 1
_TRIALS = 8
_ROWS = 2 * _TRIALS
_SEEDED_LABEL = "seeded"
_ENUMERATION_LABEL = "enumeration"
_SEEDED_MEDIAN = 723
_BETTER_TRIALS = 4
_WORSE_TRIALS = 4


def _rows() -> list[dict[str, str]]:
    with _RAW.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_seed_replication_satisfies_shared_evidence_authorities() -> None:
    """Protocol and run manifest retain the preregistered stochastic trials."""
    benchmark = benchmark_protocol.validate_example(_BENCHMARK)
    manifest = experiment_manifest.parse_manifest(
        _EXPERIMENT.read_text(encoding="utf-8")
    )
    assert benchmark.kind == benchmark_protocol.STOCHASTIC_KIND
    assert benchmark.trial_count == _TRIALS
    assert benchmark.failed_trials == 0
    assert benchmark.seeds == tuple(range(_TRIALS))
    assert manifest.run is not None
    assert manifest.run.commit == _COMMIT
    assert _SOURCE_COMMIT.read_text(encoding="utf-8").strip() == _COMMIT


def test_seed_replication_retains_complete_semantic_results() -> None:
    """Every trial exhausts the corpus with the same accepted semantics."""
    rows = _rows()
    assert len(rows) == _ROWS
    assert all(int(row["evaluations"]) == _CANDIDATES for row in rows)
    assert all(int(row["verified_count"]) == _VERIFIED for row in rows)
    assert all(int(row["best_quality"]) == _BEST_QUALITY for row in rows)


def test_seed_replication_is_mixed_on_first_hit_work() -> None:
    """Four preregistered seeds improve and four worsen first-hit work."""
    rows = _rows()
    seeded = tuple(
        int(row["first_verified_evaluation"])
        for row in rows
        if row["schedule"] == _SEEDED_LABEL
    )
    enumeration = tuple(
        int(row["first_verified_evaluation"])
        for row in rows
        if row["schedule"] == _ENUMERATION_LABEL
    )
    assert seeded == _SEEDED_FIRST
    assert enumeration == (_ENUM_FIRST,) * _TRIALS
    assert median(seeded) == _SEEDED_MEDIAN
    assert sum(value < _ENUM_FIRST for value in seeded) == _BETTER_TRIALS
    assert sum(value > _ENUM_FIRST for value in seeded) == _WORSE_TRIALS
