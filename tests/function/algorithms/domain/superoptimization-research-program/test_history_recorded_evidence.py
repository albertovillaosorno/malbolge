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
#   - Regression evidence for the retained history canonicalization run.
# - Must-Not:
#   - Rerun timing, discard samples, or generalize beyond the recorded host.
# - Allows:
#   - Inputs: tracked protocol, manifest, raw CSV, README, and source pin.
#   - Outputs: exact structural and descriptive-statistic assertions.
#   - Side effects: repository-local evidence reads only.
# - Split-When:
#   - Another history measurement gains independent retained evidence.
# - Merge-When:
#   - Shared benchmark evidence tests own this exact record shape.
# - Summary:
#   - Lock the first measured history-residue comparison without rerunning it.
# - Description:
#   - Recomputes medians and ranges only from every retained paired sample.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Host timing is narrow evidence; structural counts remain corpus-specific.
#

"""Regression tests for retained history-residue measurement evidence."""

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
    "2026-08-12-history-residue-canonicalization-windows"
)
_BENCHMARK = _EVIDENCE / "benchmark.toml"
_EXPERIMENT = _EVIDENCE / "experiment.toml"
_RAW = _EVIDENCE / "raw.csv"
_SOURCE_COMMIT = _EVIDENCE / "source-commit.txt"
_COMMIT = "9ff4834614b35900cbc51f85a4edd3b5e24fe38b"
_BASELINE_ID = "raw-visit-count-state-v1"
_CANONICAL_ID = "exact-history-residue-state-v1"
_REPETITIONS = 5
_ROWS = 2 * _REPETITIONS
_CANDIDATES = 10_000
_BASELINE_STATES = 10_000
_CANONICAL_STATES = 6_496
_BASELINE_MEDIAN = 96_384_900
_CANONICAL_MEDIAN = 244_447_500
_BASELINE_RANGE = (84_090_300, 106_369_300)
_CANONICAL_RANGE = (202_653_700, 268_365_700)
_SEMANTIC_SHA256 = (
    "fd3644058b415d3acc091d0b837111948ff640132f7c8093fca562d553bdb527"
)
_RAW_PATH = (
    "benchmarks/research/evidence/"
    "2026-08-12-history-residue-canonicalization-windows/raw.csv"
)


def _rows() -> list[dict[str, str]]:
    with _RAW.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _strategy_rows(strategy_id: str) -> list[dict[str, str]]:
    return [row for row in _rows() if row["strategy_id"] == strategy_id]


def test_history_evidence_satisfies_shared_authorities_and_source_pin() -> None:
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


def test_history_evidence_retains_exact_structural_and_semantic_result(
) -> None:
    """Every row preserves corpus work counts and one exact semantic digest."""
    rows = _rows()
    assert len(rows) == _ROWS
    expected_states = {
        _BASELINE_ID: _BASELINE_STATES,
        _CANONICAL_ID: _CANONICAL_STATES,
    }
    for row in rows:
        states = expected_states[row["strategy_id"]]
        assert int(row["unique_search_states"]) == states
        assert int(row["independent_verifier_calls"]) == states
        assert int(row["peak_frontier_states"]) == states
        assert int(row["generated_successors"]) == _CANDIDATES
        assert row["semantic_sha256"] == _SEMANTIC_SHA256


def test_history_evidence_locks_retained_timing_medians_and_ranges() -> None:
    """Recompute declared host-specific timing summaries from raw samples."""
    expected = {
        _BASELINE_ID: (_BASELINE_MEDIAN, _BASELINE_RANGE),
        _CANONICAL_ID: (_CANONICAL_MEDIAN, _CANONICAL_RANGE),
    }
    for strategy_id, (expected_median, expected_range) in expected.items():
        rows = _strategy_rows(strategy_id)
        elapsed = [int(row["elapsed_nanoseconds"]) for row in rows]
        assert len(elapsed) == _REPETITIONS
        assert median(elapsed) == expected_median
        assert (min(elapsed), max(elapsed)) == expected_range


def test_history_run_manifest_locks_measurement_extension() -> None:
    """Run metadata binds the frozen comparison and exact semantic digest."""
    document = tomllib.loads(_EXPERIMENT.read_text(encoding="utf-8"))
    extension = cast("dict[str, object]", document["history_measurement"])
    assert extension["repetitions"] == _REPETITIONS
    assert extension["candidate_count"] == _CANDIDATES
    assert extension["baseline_strategy"] == _BASELINE_ID
    assert extension["canonicalized_strategy"] == _CANONICAL_ID
    assert extension["semantic_sha256"] == _SEMANTIC_SHA256
