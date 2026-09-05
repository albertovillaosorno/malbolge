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
#   - Regression evidence for the retained three-word heuristic holdout run.
# - Must-Not:
#   - Rerun timing, filter rows, or generalize the host-specific result.
# - Allows:
#   - Inputs: tracked run/benchmark manifests, source pin, and retained CSV.
#   - Outputs: provenance, search-outcome, and timing-tradeoff assertions.
#   - Side effects: repository-local evidence reads only.
# - Split-When:
#   - Another retained heuristic run needs independent provenance.
# - Merge-When:
#   - Shared evidence tests own this exact retained holdout identity.
# - Summary:
#   - Lock search-order success and negative full-strategy timing together.
# - Description:
#   - Recomputes all result summaries from the ten retained raw rows.
# - Usage:
#   - Collected by the superoptimization research test surface.
# - Defaults:
#   - Search-order evidence is holdout-specific and timing is host-specific.
#

"""Regression checks for retained three-word heuristic evidence."""

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
    "2026-09-04-classic-three-word-initial-decode-heuristic-linux"
)
_BENCHMARK = _EVIDENCE / "benchmark.toml"
_EXPERIMENT = _EVIDENCE / "experiment.toml"
_RAW = _EVIDENCE / "raw.csv"
_SOURCE = _EVIDENCE / "source-commit.txt"
_COMMIT = "b399fff7bd1904d60dde274f940b5d2c68906824"
_BASELINE = "deterministic-enumeration-v1"
_HEURISTIC = "initial-decode-halt-proximity-order-v1"
_REPETITIONS = 5
_BUDGET = 50_000
_BASELINE_MEDIAN = 215_984_447
_HEURISTIC_MEDIAN = 2_948_297_136
_BASELINE_RANGE = (209_487_992, 233_148_571)
_HEURISTIC_RANGE = (2_763_390_294, 3_298_160_067)
_FIRST_EVALUATION = 475
_FIRST_CANDIDATE = 424_602
_ACCEPTED = 86
_BEST = 1
_MINIMUM_TIME_RATIO = 13.6
_RAW_PATH = (
    "benchmarks/research/evidence/"
    "2026-09-04-classic-three-word-initial-decode-heuristic-linux/raw.csv"
)


def _rows() -> list[dict[str, str]]:
    with _RAW.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _strategy_rows(strategy: str) -> list[dict[str, str]]:
    return [row for row in _rows() if row["schedule_id"] == strategy]


def test_heuristic_evidence_satisfies_authorities_and_source_pin() -> None:
    """Shared manifests and the pre-run source commit remain exact."""
    benchmark = benchmark_protocol.validate_example(_BENCHMARK)
    manifest = experiment_manifest.parse_manifest(
        _EXPERIMENT.read_text(encoding="utf-8")
    )
    assert benchmark.repetitions == _REPETITIONS
    assert benchmark.raw_path == _RAW_PATH
    assert manifest.run is not None
    assert manifest.run.commit == _COMMIT
    assert manifest.run.raw_output == _RAW_PATH
    assert _SOURCE.read_text(encoding="utf-8").strip() == _COMMIT


def test_heuristic_evidence_locks_search_outcome() -> None:
    """All retained rows preserve the preregistered search outcome."""
    baseline = _strategy_rows(_BASELINE)
    heuristic = _strategy_rows(_HEURISTIC)
    assert len(baseline) == _REPETITIONS
    assert len(heuristic) == _REPETITIONS
    all_rows = (*baseline, *heuristic)
    assert all(int(row["evaluations"]) == _BUDGET for row in all_rows)
    assert all(int(row["verified_candidate_count"]) == 0 for row in baseline)
    assert all(not row["first_verified_evaluation"] for row in baseline)
    assert all(
        int(row["verified_candidate_count"]) == _ACCEPTED
        for row in heuristic
    )
    assert all(
        int(row["first_verified_evaluation"]) == _FIRST_EVALUATION
        for row in heuristic
    )
    assert all(
        int(row["first_verified_candidate"]) == _FIRST_CANDIDATE
        for row in heuristic
    )
    assert all(int(row["best_verified_quality"]) == _BEST for row in heuristic)


def test_heuristic_evidence_locks_timing_tradeoff() -> None:
    """Raw samples retain the negative full-strategy timing tradeoff."""
    expected = {
        _BASELINE: (_BASELINE_MEDIAN, _BASELINE_RANGE),
        _HEURISTIC: (_HEURISTIC_MEDIAN, _HEURISTIC_RANGE),
    }
    for strategy, (expected_median, expected_range) in expected.items():
        elapsed = [
            int(row["elapsed_nanoseconds"])
            for row in _strategy_rows(strategy)
        ]
        assert median(elapsed) == expected_median
        assert (min(elapsed), max(elapsed)) == expected_range
    assert _HEURISTIC_MEDIAN / _BASELINE_MEDIAN > _MINIMUM_TIME_RATIO


def test_heuristic_manifest_locks_result_extension() -> None:
    """Run extension keeps budget, hits, and first verified candidate exact."""
    document = tomllib.loads(_EXPERIMENT.read_text(encoding="utf-8"))
    extension = cast(
        "dict[str, object]",
        document["initial_decode_heuristic_measurement"],
    )
    assert extension["evaluation_budget"] == _BUDGET
    assert extension["baseline_verified_candidate_count"] == 0
    assert extension["heuristic_verified_candidate_count"] == _ACCEPTED
    assert extension["heuristic_first_verified_evaluation"] == _FIRST_EVALUATION
    assert extension["heuristic_first_verified_candidate"] == _FIRST_CANDIDATE
