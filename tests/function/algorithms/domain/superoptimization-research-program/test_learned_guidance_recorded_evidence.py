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
#   - Regression evidence for the retained learned-guidance no-solution run.
# - Must-Not:
#   - Rerun timing or reinterpret the null holdout as a ranking win/loss.
# - Allows:
#   - Inputs: retained CSV, manifests, and source pin.
#   - Outputs: exact no-solution and timing-summary assertions.
#   - Side effects: repository-local evidence reads only.
# - Split-When:
#   - Another learned-guidance run gains independent provenance.
# - Merge-When:
#   - Shared tests own this exact retained comparison identity.
# - Summary:
#   - Lock the learned-guidance null result and visible overhead.
# - Description:
#   - Recomputes outcome, medians, ranges, and paired wins from raw rows.
# - Usage:
#   - Collected by the superoptimization research test surface.
# - Defaults:
#   - No first-hit ranking claim is made when the holdout has no solution.
#

"""Regression checks for retained training-only learned-guidance evidence."""

import csv
from pathlib import Path
from statistics import median

from scripts.validate import benchmark_protocol
from scripts.validate import experiment_manifest

_ROOT = Path(__file__).resolve().parents[5]
_E = _ROOT / (
    "benchmarks/research/evidence/"
    "2026-09-04-classic-four-word-training-only-guidance-linux"
)
_STATIC = "four-word-static-initial-decode-order-v1"
_LEARNED = "laplace-pooled-initial-decode-guidance-order-v1"
_REPETITIONS = 5
_BUDGET = 50_000
_NO_SOLUTION = "no-solution"
_STATIC_MEDIAN = 407_894_273
_STATIC_RANGE = (400_226_527, 461_588_241)
_TRAINING_MEDIAN = 6_259_721_192
_TRAINING_RANGE = (6_045_943_284, 7_483_139_893)
_LEARNED_PHASE_MEDIAN = 2_092_124_024
_LEARNED_PHASE_RANGE = (2_044_123_502, 2_240_697_649)
_LEARNED_END_MEDIAN = 8_303_844_694
_LEARNED_END_RANGE = (8_138_067_308, 9_723_837_542)


def _rows() -> list[dict[str, str]]:
    with (_E / "raw.csv").open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_learned_guidance_manifests_and_null_outcomes() -> None:
    """Shared authorities accept the retained no-solution comparison."""
    _ = benchmark_protocol.validate_example(_E / "benchmark.toml")
    manifest = experiment_manifest.parse_manifest(
        (_E / "experiment.toml").read_text(encoding="utf-8")
    )
    assert manifest.run is not None
    assert manifest.run.outcome == _NO_SOLUTION
    rows = _rows()
    assert len(rows) == _REPETITIONS * 2
    assert all(row["outcome"] == _NO_SOLUTION for row in rows)
    assert all(int(row["evaluations"]) == _BUDGET for row in rows)
    assert all(not row["candidate"] and not row["quality"] for row in rows)


def test_learned_guidance_recomputes_retained_timing() -> None:
    """Raw rows preserve the secondary timing cost of the null comparison."""
    rows = _rows()
    static = [row for row in rows if row["strategy_id"] == _STATIC]
    learned = [row for row in rows if row["strategy_id"] == _LEARNED]
    static_end = [int(row["end_to_end_nanoseconds"]) for row in static]
    training = [int(row["training_nanoseconds"]) for row in learned]
    learned_phase = [
        int(row["schedule_and_search_nanoseconds"]) for row in learned
    ]
    learned_end = [int(row["end_to_end_nanoseconds"]) for row in learned]
    assert median(static_end) == _STATIC_MEDIAN
    assert (min(static_end), max(static_end)) == _STATIC_RANGE
    assert median(training) == _TRAINING_MEDIAN
    assert (min(training), max(training)) == _TRAINING_RANGE
    assert median(learned_phase) == _LEARNED_PHASE_MEDIAN
    assert (min(learned_phase), max(learned_phase)) == _LEARNED_PHASE_RANGE
    assert median(learned_end) == _LEARNED_END_MEDIAN
    assert (min(learned_end), max(learned_end)) == _LEARNED_END_RANGE
    paired_wins = sum(
        learned_ns < static_ns
        for learned_ns, static_ns in zip(learned_end, static_end, strict=True)
    )
    assert paired_wins == 0
