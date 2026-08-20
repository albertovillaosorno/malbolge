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
#   - Regression evidence for the retained crazy-preimage pruning run.
# - Must-Not:
#   - Rerun measurement, filter raw rows, or generalize host timing.
# - Allows:
#   - Inputs: tracked benchmark/run manifests, source pin, and raw CSV.
#   - Outputs: authority, structural, semantic, and retained timing assertions.
#   - Side effects: repository-local reads only.
# - Split-When:
#   - Another retained run needs independent provenance.
# - Merge-When:
#   - Shared evidence tests own this exact retained run identity.
# - Summary:
#   - Lock retained exact-preimage pruning evidence without remeasurement.
# - Description:
#   - Recomputes exact counts and timing summaries from all ten raw rows.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Host timing remains narrow evidence; exact structural counts are frozen.
#

"""Regression checks for retained crazy-preimage pruning evidence."""

import csv
from pathlib import Path
from statistics import median

from scripts.validate import benchmark_protocol
from scripts.validate import experiment_manifest

_ROOT = Path(__file__).resolve().parents[5]
_EVIDENCE = _ROOT / (
    "benchmarks/research/evidence/2026-08-12-crazy-preimage-pruning-windows"
)
_BENCHMARK = _EVIDENCE / "benchmark.toml"
_EXPERIMENT = _EVIDENCE / "experiment.toml"
_RAW = _EVIDENCE / "raw.csv"
_SOURCE_COMMIT = _EVIDENCE / "source-commit.txt"
_COMMIT = "5fbea3461d5fbb035611b1ce6cce43b3d4cad44c"
_BASELINE_ID = "classic-crazy-full-domain-data-enumeration-v1"
_EXACT_ID = "classic-crazy-digitwise-exact-preimage-v1"
_REPETITIONS = 5
_ROWS = 2 * _REPETITIONS
_BASELINE_EVALUATIONS = 708_588
_EXACT_EVALUATIONS = 2_047
_PREIMAGE_COUNT = 2_047
_BASELINE_MEDIAN = 2_298_684_800
_EXACT_MEDIAN = 2_931_140_300
_BASELINE_RANGE = (2_122_264_300, 2_474_458_100)
_EXACT_RANGE = (2_234_618_200, 3_064_837_900)
_SEMANTIC_SHA256 = (
    "86cbd11391b4db60a8665cb2f1d698140206f388400bd072116d72a32cbf2f62"
)
_RAW_PATH = (
    "benchmarks/research/evidence/"
    "2026-08-12-crazy-preimage-pruning-windows/raw.csv"
)


def _rows() -> list[dict[str, str]]:
    with _RAW.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _strategy_rows(strategy_id: str) -> list[dict[str, str]]:
    return [row for row in _rows() if row["strategy_id"] == strategy_id]


def test_crazy_evidence_satisfies_shared_authorities_and_source_pin() -> None:
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


def test_crazy_evidence_retains_exact_structural_and_semantic_result() -> None:
    """Every row preserves exact work counts and semantic identity."""
    rows = _rows()
    assert len(rows) == _ROWS
    expected_evaluations = {
        _BASELINE_ID: _BASELINE_EVALUATIONS,
        _EXACT_ID: _EXACT_EVALUATIONS,
    }
    for row in rows:
        expected = expected_evaluations[row["strategy_id"]]
        assert int(row["evaluations"]) == expected
        assert int(row["preimage_count"]) == _PREIMAGE_COUNT
        assert row["semantic_sha256"] == _SEMANTIC_SHA256


def test_crazy_evidence_locks_retained_timing_medians_and_ranges() -> None:
    """Recompute host-specific timing summaries from all retained samples."""
    expected = {
        _BASELINE_ID: (_BASELINE_MEDIAN, _BASELINE_RANGE),
        _EXACT_ID: (_EXACT_MEDIAN, _EXACT_RANGE),
    }
    for strategy_id, (expected_median, expected_range) in expected.items():
        rows = _strategy_rows(strategy_id)
        elapsed = [int(row["elapsed_nanoseconds"]) for row in rows]
        assert len(elapsed) == _REPETITIONS
        assert median(elapsed) == expected_median
        assert (min(elapsed), max(elapsed)) == expected_range
