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
#   - Regression evidence for the retained prefix-decomposition run.
# - Must-Not:
#   - Rerun timing, filter rows, broaden proof classes, or generalize host
#     timing.
# - Allows:
#   - Inputs: tracked benchmark/run manifests, source pin, and raw CSV.
#   - Outputs: provenance, map, work-count, and timing-summary assertions.
#   - Side effects: repository-local evidence reads only.
# - Split-When:
#   - Another retained prefix-decomposition run needs independent provenance.
# - Merge-When:
#   - Shared evidence tests own this exact retained run identity.
# - Summary:
#   - Lock the first measured prefix-decomposition result without remeasurement.
# - Description:
#   - Recomputes exact work and timing summaries from all ten raw rows.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Host timing is narrow; quality-map and verifier counts are
#     corpus-specific.
#

"""Regression checks for retained classic prefix-decomposition evidence."""

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
    "2026-09-04-classic-prefix-decomposition-linux"
)
_BENCHMARK = _EVIDENCE / "benchmark.toml"
_EXPERIMENT = _EVIDENCE / "experiment.toml"
_RAW = _EVIDENCE / "raw.csv"
_SOURCE_COMMIT = _EVIDENCE / "source-commit.txt"
_COMMIT = "ed6825af65aa0fb43ffc3c6dac913fda00b07a52"
_BASELINE_ID = "full-candidate-independent-verification-v1"
_DECOMPOSED_ID = "exact-first-step-prefix-decomposition-v1"
_REPETITIONS = 5
_ROWS = 2 * _REPETITIONS
_CANDIDATES = 8_836
_BASELINE_CALLS = 8_836
_DECOMPOSED_CALLS = 8_742
_DISCHARGED = 94
_ACCEPTED = 10
_BEST_QUALITY = 1
_BASELINE_MEDIAN = 831_921_051
_DECOMPOSED_MEDIAN = 835_180_632
_BASELINE_RANGE = (809_975_223, 850_855_502)
_DECOMPOSED_RANGE = (818_562_725, 970_178_389)
_DECOMPOSED_PAIRED_WINS = 2
_MAP_SHA256 = (
    "33d23f934b0541140e51716f6f814d42697773f64788c9f778238c8dc7b64335"
)
_RAW_PATH = (
    "benchmarks/research/evidence/"
    "2026-09-04-classic-prefix-decomposition-linux/raw.csv"
)


def _rows() -> list[dict[str, str]]:
    with _RAW.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _strategy_rows(strategy_id: str) -> list[dict[str, str]]:
    return [row for row in _rows() if row["strategy_id"] == strategy_id]


def test_prefix_evidence_satisfies_shared_authorities_and_source_pin() -> None:
    """Protocol, run manifest, raw path, and pre-run commit remain exact."""
    benchmark = benchmark_protocol.validate_example(_BENCHMARK)
    manifest = experiment_manifest.parse_manifest(
        _EXPERIMENT.read_text(encoding="utf-8")
    )
    assert benchmark.kind == benchmark_protocol.DETERMINISTIC_KIND
    assert benchmark.repetitions == _REPETITIONS
    assert benchmark.raw_path == _RAW_PATH
    assert manifest.record_kind == experiment_manifest.RUN_RECORD_KIND
    assert manifest.run is not None
    assert manifest.run.commit == _COMMIT
    assert manifest.run.raw_output == _RAW_PATH
    assert _SOURCE_COMMIT.read_text(encoding="utf-8").strip() == _COMMIT


def test_prefix_evidence_retains_exact_map_and_verifier_work() -> None:
    """Every row preserves complete quality-map identity and exact work."""
    rows = _rows()
    assert len(rows) == _ROWS
    expected = {
        _BASELINE_ID: (_BASELINE_CALLS, 0),
        _DECOMPOSED_ID: (_DECOMPOSED_CALLS, _DISCHARGED),
    }
    for row in rows:
        calls, discharged = expected[row["strategy_id"]]
        assert int(row["candidate_count"]) == _CANDIDATES
        assert int(row["independent_verifier_calls"]) == calls
        assert int(row["full_candidate_verifications"]) == calls
        assert int(row["structurally_discharged_candidates"]) == discharged
        assert int(row["accepted_candidate_count"]) == _ACCEPTED
        assert int(row["best_verified_quality"]) == _BEST_QUALITY
        assert row["quality_map_sha256"] == _MAP_SHA256


def test_prefix_evidence_locks_timing_medians_ranges_and_paired_wins() -> None:
    """Recompute the narrow timing result from all retained samples."""
    expected = {
        _BASELINE_ID: (_BASELINE_MEDIAN, _BASELINE_RANGE),
        _DECOMPOSED_ID: (_DECOMPOSED_MEDIAN, _DECOMPOSED_RANGE),
    }
    for strategy_id, (expected_median, expected_range) in expected.items():
        elapsed = [
            int(row["elapsed_nanoseconds"])
            for row in _strategy_rows(strategy_id)
        ]
        assert len(elapsed) == _REPETITIONS
        assert median(elapsed) == expected_median
        assert (min(elapsed), max(elapsed)) == expected_range
    baseline = _strategy_rows(_BASELINE_ID)
    decomposed = _strategy_rows(_DECOMPOSED_ID)
    paired_wins = sum(
        int(decomposed[index]["elapsed_nanoseconds"])
        < int(baseline[index]["elapsed_nanoseconds"])
        for index in range(_REPETITIONS)
    )
    assert paired_wins == _DECOMPOSED_PAIRED_WINS


def test_prefix_run_manifest_locks_measurement_extension() -> None:
    """Run metadata binds the exact map, counts, and registered strategies."""
    document = tomllib.loads(_EXPERIMENT.read_text(encoding="utf-8"))
    extension = cast(
        "dict[str, object]",
        document["prefix_decomposition_measurement"],
    )
    assert extension["candidate_count"] == _CANDIDATES
    assert extension["baseline_verifier_calls"] == _BASELINE_CALLS
    assert extension["decomposed_verifier_calls"] == _DECOMPOSED_CALLS
    assert extension["structurally_discharged_candidates"] == _DISCHARGED
    assert extension["baseline_strategy"] == _BASELINE_ID
    assert extension["decomposed_strategy"] == _DECOMPOSED_ID
    assert extension["quality_map_sha256"] == _MAP_SHA256
