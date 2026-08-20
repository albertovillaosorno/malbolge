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
#   - Regression evidence for the first recorded classic superopt pilot.
# - Must-Not:
#   - Rerun timing, discard samples, or generalize beyond the recorded pilot.
# - Allows:
#   - Inputs: tracked manifest, benchmark metadata, raw CSV, and source pin.
#   - Outputs: shared-policy and exact observed-sample assertions.
#   - Side effects: repository-local evidence reads only.
# - Split-When:
#   - Another measured pilot gains independent retained evidence.
# - Merge-When:
#   - Shared benchmark evidence tests own this exact record shape.
# - Summary:
#   - Lock the first measured superoptimization pilot without rerunning it.
# - Description:
#   - Recomputes descriptive statistics only from the retained raw CSV.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Exact pilot observations are evidence, not a broad performance claim.
#

"""Regression tests for the first recorded classic superoptimization pilot."""

import csv
from pathlib import Path
from statistics import median
import tomllib
from typing import cast

from scripts.validate import benchmark_protocol
from scripts.validate import experiment_manifest

_ROOT = Path(__file__).resolve().parents[5]
_EVIDENCE = _ROOT / (
    "benchmarks/research/evidence/"
    "2026-08-11-classic-superopt-pilot-windows"
)
_BENCHMARK = _EVIDENCE / "benchmark.toml"
_EXPERIMENT = _EVIDENCE / "experiment.toml"
_RAW = _EVIDENCE / "raw.csv"
_SOURCE_COMMIT = _EVIDENCE / "source-commit.txt"
_COMMIT = "23dd86d656e6b7bdd0d1422a984e95a9feeebd0f"
_RAW_PATH = (
    "benchmarks/research/evidence/"
    "2026-08-11-classic-superopt-pilot-windows/raw.csv"
)
_ENUMERATION_ID = "deterministic-enumeration-v1"
_SEEDED_ID = "splitmix64-sparse-partial-fisher-yates-v1"
_REPETITIONS = 5
_STUDY_KIND = "deterministic"
_ROWS = 2 * _REPETITIONS
_CANDIDATES = 8_836
_VERIFIED = 10
_BEST_QUALITY = 1
_ENUM_FIRST_EVALUATION = 706
_SEEDED_FIRST_EVALUATION = 250
_ENUM_MEDIAN_ELAPSED = 227_928_500
_SEEDED_MEDIAN_ELAPSED = 227_433_600
_ENUM_MEDIAN_FIRST = 18_506_300
_SEEDED_MEDIAN_FIRST = 6_119_900
_STOP_REASON = "candidate-corpus-exhausted"
_OUTCOME = "verified-candidate-found"


def _rows() -> list[dict[str, str]]:
    with _RAW.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _schedule_rows(schedule_id: str) -> list[dict[str, str]]:
    return [row for row in _rows() if row["schedule_id"] == schedule_id]


def test_recorded_pilot_satisfies_shared_evidence_authorities() -> None:
    """Tracked manifest and benchmark metadata pass their shared validators."""
    benchmark = benchmark_protocol.validate_example(_BENCHMARK)
    manifest = experiment_manifest.parse_manifest(
        _EXPERIMENT.read_text(encoding="utf-8")
    )
    assert benchmark.kind == _STUDY_KIND
    assert benchmark.repetitions == _REPETITIONS
    assert benchmark.raw_path == _RAW_PATH
    assert manifest.record_kind == experiment_manifest.RUN_RECORD_KIND
    assert manifest.run is not None
    assert manifest.run.commit == _COMMIT
    assert manifest.run.raw_output == _RAW_PATH
    assert _SOURCE_COMMIT.read_text(encoding="utf-8").strip() == _COMMIT


def test_recorded_pilot_retains_exact_semantic_results() -> None:
    """Every retained schedule exhausts the corpus and agrees on quality."""
    rows = _rows()
    assert len(rows) == _ROWS
    for row in rows:
        assert int(row["evaluations"]) == _CANDIDATES
        assert int(row["verified_count"]) == _VERIFIED
        assert int(row["best_quality"]) == _BEST_QUALITY
        assert row["stop_reason"] == _STOP_REASON
        assert row["outcome"] == _OUTCOME


def test_recorded_pilot_locks_first_hit_and_elapsed_medians() -> None:
    """Recompute preregistered centers from retained raw samples."""
    expected = {
        _ENUMERATION_ID: (
            _ENUM_FIRST_EVALUATION,
            _ENUM_MEDIAN_ELAPSED,
            _ENUM_MEDIAN_FIRST,
        ),
        _SEEDED_ID: (
            _SEEDED_FIRST_EVALUATION,
            _SEEDED_MEDIAN_ELAPSED,
            _SEEDED_MEDIAN_FIRST,
        ),
    }
    for schedule_id, values in expected.items():
        rows = _schedule_rows(schedule_id)
        first_evaluation, elapsed_median, first_median = values
        assert len(rows) == _REPETITIONS
        assert {int(row["first_verified_evaluation"]) for row in rows} == {
            first_evaluation
        }
        elapsed = [int(row["elapsed_nanoseconds"]) for row in rows]
        first = [int(row["first_verified_elapsed_nanoseconds"]) for row in rows]
        assert median(elapsed) == elapsed_median
        assert median(first) == first_median


def test_recorded_manifest_retains_measurement_extension() -> None:
    """Generated run identity names the complete five-repetition series."""
    document = tomllib.loads(_EXPERIMENT.read_text(encoding="utf-8"))
    extension = cast(
        "dict[str, object]",
        document["superoptimization_measurement"],
    )
    assert extension["repetitions"] == _REPETITIONS
    assert extension["candidate_count"] == _CANDIDATES
    assert extension["seed"] == 0
