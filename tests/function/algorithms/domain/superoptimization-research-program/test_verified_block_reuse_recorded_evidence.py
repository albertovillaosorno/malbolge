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
#   - Regression evidence for the retained verified-block-reuse run.
# - Must-Not:
#   - Rerun timing, filter rows, infer production hit rate, or widen cache keys.
# - Allows:
#   - Inputs: tracked benchmark/run manifests, source pin, and raw CSV.
#   - Outputs: provenance, map, work-count, and timing-summary assertions.
#   - Side effects: repository-local evidence reads only.
# - Split-When:
#   - Another retained verified-block-reuse run needs independent provenance.
# - Merge-When:
#   - Shared evidence tests own this exact retained run identity.
# - Summary:
#   - Lock the repeated-corpus reuse result without remeasurement.
# - Description:
#   - Recomputes exact work and timing summaries from all ten raw rows.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Timing is host-specific and the workload has deliberate 100% repetition.
#

"""Regression checks for retained classic verified-block-reuse evidence."""

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
    "2026-09-04-classic-verified-block-reuse-linux"
)
_BENCHMARK = _EVIDENCE / "benchmark.toml"
_EXPERIMENT = _EVIDENCE / "experiment.toml"
_RAW = _EVIDENCE / "raw.csv"
_SOURCE_COMMIT = _EVIDENCE / "source-commit.txt"
_COMMIT = "f42579b927b79d62d3763d4ee714ed22961d80b2"
_BASELINE_ID = "per-request-independent-verification-v1"
_REUSE_ID = "exact-candidate-verified-result-reuse-v1"
_REPETITIONS = 5
_ROWS = 2 * _REPETITIONS
_REQUESTS = 17_672
_UNIQUE = 8_836
_BASELINE_CALLS = 17_672
_REUSE_CALLS = 8_836
_REUSED_REQUESTS = 8_836
_ACCEPTED = 20
_BEST_QUALITY = 1
_BASELINE_MEDIAN = 1_617_672_749
_REUSE_MEDIAN = 851_323_429
_BASELINE_RANGE = (1_611_357_982, 1_733_219_224)
_REUSE_RANGE = (824_892_050, 866_041_992)
_REUSE_PAIRED_WINS = 5
_MINIMUM_MEDIAN_SPEEDUP = 1.9
_MAP_SHA256 = (
    "9dfe349bf961baf7c0f507fcff549198a3dffe687b1ea23714769e9105f36fdd"
)
_WORKLOAD_SHA256 = (
    "d86f190a512b64724b9546c72f2ee56973292e6ef5707378f8c9a9ba2050bbc7"
)
_RAW_PATH = (
    "benchmarks/research/evidence/"
    "2026-09-04-classic-verified-block-reuse-linux/raw.csv"
)


def _rows() -> list[dict[str, str]]:
    with _RAW.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _strategy_rows(strategy_id: str) -> list[dict[str, str]]:
    return [row for row in _rows() if row["strategy_id"] == strategy_id]


def test_reuse_evidence_satisfies_shared_authorities_and_source_pin() -> None:
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
    assert manifest.run.workload_sha256 == _WORKLOAD_SHA256
    assert manifest.run.raw_output == _RAW_PATH
    assert _SOURCE_COMMIT.read_text(encoding="utf-8").strip() == _COMMIT


def test_reuse_evidence_retains_exact_map_and_work_counts() -> None:
    """Every row preserves request-map identity and registered work counts."""
    rows = _rows()
    assert len(rows) == _ROWS
    expected = {
        _BASELINE_ID: (_BASELINE_CALLS, 0),
        _REUSE_ID: (_REUSE_CALLS, _REUSED_REQUESTS),
    }
    for row in rows:
        calls, reused = expected[row["strategy_id"]]
        assert int(row["request_count"]) == _REQUESTS
        assert int(row["unique_candidate_count"]) == _UNIQUE
        assert int(row["independent_verifier_calls"]) == calls
        assert int(row["reused_request_count"]) == reused
        assert int(row["accepted_request_count"]) == _ACCEPTED
        assert int(row["best_verified_quality"]) == _BEST_QUALITY
        assert row["quality_map_sha256"] == _MAP_SHA256
    assert _BASELINE_CALLS - _REUSE_CALLS == _REUSED_REQUESTS
    assert _REUSE_CALLS * 2 == _BASELINE_CALLS


def test_reuse_evidence_locks_timing_medians_ranges_and_paired_wins() -> None:
    """Recompute the host timing result from every retained pair."""
    expected = {
        _BASELINE_ID: (_BASELINE_MEDIAN, _BASELINE_RANGE),
        _REUSE_ID: (_REUSE_MEDIAN, _REUSE_RANGE),
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
    reused = _strategy_rows(_REUSE_ID)
    paired_wins = sum(
        int(reused[index]["elapsed_nanoseconds"])
        < int(baseline[index]["elapsed_nanoseconds"])
        for index in range(_REPETITIONS)
    )
    assert paired_wins == _REUSE_PAIRED_WINS
    assert _BASELINE_MEDIAN / _REUSE_MEDIAN > _MINIMUM_MEDIAN_SPEEDUP


def test_reuse_run_manifest_locks_measurement_extension() -> None:
    """Run metadata binds exact workload, map, counts, and strategies."""
    document = tomllib.loads(_EXPERIMENT.read_text(encoding="utf-8"))
    extension = cast(
        "dict[str, object]",
        document["verified_block_reuse_measurement"],
    )
    assert extension["request_count"] == _REQUESTS
    assert extension["unique_candidate_count"] == _UNIQUE
    assert extension["baseline_verifier_calls"] == _BASELINE_CALLS
    assert extension["reuse_verifier_calls"] == _REUSE_CALLS
    assert extension["reused_request_count"] == _REUSED_REQUESTS
    assert extension["baseline_strategy"] == _BASELINE_ID
    assert extension["reuse_strategy"] == _REUSE_ID
    assert extension["workload_sha256"] == _WORKLOAD_SHA256
    assert extension["quality_map_sha256"] == _MAP_SHA256
