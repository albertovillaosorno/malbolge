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
#   - Regression evidence for the retained first-hit follow-up run.
# - Must-Not:
#   - Rerun timing or present this known-holdout follow-up as independent.
# - Allows:
#   - Inputs: retained CSV, manifests, and source pin.
#   - Outputs: exact stopping and timing-summary assertions.
#   - Side effects: repository-local evidence reads only.
# - Split-When:
#   - Another first-hit run gains independent provenance.
# - Merge-When:
#   - Shared tests own this exact retained follow-up identity.
# - Summary:
#   - Lock the 475-evaluation and 16.183x follow-up result.
# - Description:
#   - Recomputes all search and timing summaries from ten raw rows.
# - Usage:
#   - Collected by the superoptimization research test surface.
# - Defaults:
#   - The earlier full-budget negative result remains separate evidence.
#

"""Regression checks for retained first-hit follow-up evidence."""

import csv
from pathlib import Path
from statistics import median

from scripts.validate import benchmark_protocol
from scripts.validate import experiment_manifest

_ROOT = Path(__file__).resolve().parents[5]
_E = _ROOT / (
    "benchmarks/research/evidence/"
    "2026-09-04-classic-three-word-first-hit-follow-up-linux"
)
_BASE = "deterministic-enumeration-first-hit-v1"
_HEUR = "bucketed-initial-decode-first-hit-v1"
_BASE_MEDIAN = 212_739_774
_HEUR_MEDIAN = 13_146_086
_BASE_RANGE = (206_582_814, 253_086_582)
_HEUR_RANGE = (12_635_046, 14_932_775)
_BUDGET = 50_000
_HEUR_EVALUATIONS = 475
_HEUR_CANDIDATE = 424_602
_REPETITIONS = 5


def _rows() -> list[dict[str, str]]:
    with (_E / "raw.csv").open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_first_hit_follow_up_authorities_and_outcome() -> None:
    """Shared manifests validate and every row preserves exact stopping."""
    _ = benchmark_protocol.validate_example(_E / "benchmark.toml")
    manifest = experiment_manifest.parse_manifest(
        (_E / "experiment.toml").read_text(encoding="utf-8")
    )
    assert manifest.run is not None
    rows = _rows()
    baseline = [row for row in rows if row["strategy_id"] == _BASE]
    heuristic = [row for row in rows if row["strategy_id"] == _HEUR]
    assert all(not row["candidate"] for row in baseline)
    assert all(int(row["evaluations"]) == _BUDGET for row in baseline)
    assert all(
        int(row["evaluations"]) == _HEUR_EVALUATIONS
        for row in heuristic
    )
    assert all(int(row["candidate"]) == _HEUR_CANDIDATE for row in heuristic)
    assert all(int(row["quality"]) == 1 for row in heuristic)


def test_first_hit_follow_up_locks_medians_ranges_and_wins() -> None:
    """Recompute the positive stop-on-first timing result from raw rows."""
    rows = _rows()
    by = {
        strategy: [
            int(row["elapsed_nanoseconds"])
            for row in rows
            if row["strategy_id"] == strategy
        ]
        for strategy in (_BASE, _HEUR)
    }
    assert median(by[_BASE]) == _BASE_MEDIAN
    assert (min(by[_BASE]), max(by[_BASE])) == _BASE_RANGE
    assert median(by[_HEUR]) == _HEUR_MEDIAN
    assert (min(by[_HEUR]), max(by[_HEUR])) == _HEUR_RANGE
    paired_wins = sum(
        h < b for h, b in zip(by[_HEUR], by[_BASE], strict=True)
    )
    assert paired_wins == _REPETITIONS
