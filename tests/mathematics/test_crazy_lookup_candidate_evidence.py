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
#   - Integrity checks for retained CUDA CRAZY candidate lookup evidence.
# - Must-Not:
#   - Execute CUDA or turn benchmark timing into semantic authority.
# - Allows:
#   - Inputs: tracked RTX 4060 raw timing and clean source-commit identity.
#   - Outputs: deterministic evidence-shape and mixed-result assertions.
#   - Side effects: tracked-file reads only.
# - Split-When:
#   - Split when another retained candidate-arithmetic run gains its own ID.
# - Merge-When:
#   - Merge when another test owns this exact retained evidence record.
# - Summary:
#   - Integrity evidence for classic candidate CRAZY lookup throughput.
# - Description:
#   - Locks raw cardinality, source identity, and non-promotional conclusion.
# - Usage:
#   - Run with mathematics validation; CUDA hardware is not required.
# - Defaults:
#   - Timing remains research evidence and never verification authority.
#

"""Integrity checks for retained CUDA CRAZY candidate lookup evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from benchmarks.accelerator.crazy_lookup_address_fanout import ORDINARY_ROUTE
from benchmarks.accelerator.crazy_lookup_address_fanout import PREPARED_ROUTE
from benchmarks.accelerator.crazy_lookup_address_fanout import WORKLOAD_ID

from benchmarks.accelerator import crazy_lookup_candidate_throughput as bench

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    ROOT
    / "benchmarks/accelerator/evidence"
    / "2026-09-04-crazy-lookup-candidate-throughput-rtx4060"
)
EXPECTED_SOURCE_COMMIT = "6852089254d13bd1544d69c94b552254e566561c"
EXPECTED_DEVICE_NAME = "NVIDIA GeForce RTX 4060"
EXPECTED_DEVICE_ARCH = "sm_89"
EXPECTED_ORDINARY_COUNT = 59_049
EXPECTED_PROJECTED_COUNT = 1_024
EXPECTED_ROW_COUNT = 4
EXPECTED_ORDINARY_LOOKUP_WINS = 7
EXPECTED_PROJECTED_LOOKUP_WINS = 5


def _payload() -> dict[str, object]:
    return cast(
        "dict[str, object]",
        json.loads((EVIDENCE / "throughput.json").read_text()),
    )


def _rows() -> tuple[dict[str, object], ...]:
    value = _payload()["rows"]
    if not isinstance(value, list):
        message = "retained candidate lookup rows must be a JSON array"
        raise TypeError(message)
    rows = cast("list[object]", value)
    converted: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            message = "retained candidate lookup row must be a JSON object"
            raise TypeError(message)
        converted.append(cast("dict[str, object]", row))
    return tuple(converted)


def _row(route_id: str, geometry: str) -> dict[str, object]:
    matches = tuple(
        row
        for row in _rows()
        if row["route_id"] == route_id and row["geometry"] == geometry
    )
    if len(matches) != 1:
        message = "retained candidate lookup route/geometry identity drifted"
        raise AssertionError(message)
    return matches[0]


def _samples(row: dict[str, object]) -> tuple[int, ...]:
    value = row["raw_ns"]
    if not isinstance(value, list):
        message = "retained candidate lookup raw samples must be a JSON array"
        raise TypeError(message)
    samples = cast("list[object]", value)
    if any(type(sample) is not int for sample in samples):
        message = "retained candidate lookup sample must be an exact integer"
        raise TypeError(message)
    return tuple(cast("list[int]", samples))


def test_retained_candidate_lookup_evidence_has_exact_identity() -> None:
    """Bind the retained run to its clean harness, workload, and GPU."""
    payload = _payload()
    assert payload["benchmark_id"] == bench.BENCHMARK_ID
    assert payload["workload_id"] == WORKLOAD_ID
    assert tuple(cast("list[str]", payload["geometries"])) == bench.GEOMETRIES
    assert payload["sample_count"] == bench.SAMPLE_COUNT
    assert payload["warmup_count"] == bench.WARMUP_COUNT
    device = cast("dict[str, object]", payload["device"])
    assert device == {
        "arch": EXPECTED_DEVICE_ARCH,
        "name": EXPECTED_DEVICE_NAME,
    }
    assert (EVIDENCE / "source-commit.txt").read_text().strip() == (
        EXPECTED_SOURCE_COMMIT
    )
    assert len(_rows()) == EXPECTED_ROW_COUNT


def test_retained_candidate_lookup_evidence_preserves_all_samples() -> None:
    """Every route/geometry retains exactly fifteen validated timings."""
    expected_counts = {
        ORDINARY_ROUTE: EXPECTED_ORDINARY_COUNT,
        PREPARED_ROUTE: EXPECTED_PROJECTED_COUNT,
    }
    for route_id, count in expected_counts.items():
        for geometry in bench.GEOMETRIES:
            row = _row(route_id, geometry)
            assert row["candidate_count"] == count
            assert len(_samples(row)) == bench.SAMPLE_COUNT


def test_retained_candidate_lookup_result_does_not_support_promotion() -> None:
    """Median and paired evidence remain mixed across the two search orders."""
    ordinary_tritwise = _row(ORDINARY_ROUTE, bench.TRITWISE)
    ordinary_lookup = _row(ORDINARY_ROUTE, bench.LOOKUP)
    projected_tritwise = _row(PREPARED_ROUTE, bench.TRITWISE)
    projected_lookup = _row(PREPARED_ROUTE, bench.LOOKUP)

    assert cast("int", ordinary_tritwise["median_ns"]) < cast(
        "int", ordinary_lookup["median_ns"]
    )
    assert cast("int", projected_lookup["median_ns"]) < cast(
        "int", projected_tritwise["median_ns"]
    )

    ordinary_wins = sum(
        lookup < tritwise
        for tritwise, lookup in zip(
            _samples(ordinary_tritwise),
            _samples(ordinary_lookup),
            strict=True,
        )
    )
    projected_wins = sum(
        lookup < tritwise
        for tritwise, lookup in zip(
            _samples(projected_tritwise),
            _samples(projected_lookup),
            strict=True,
        )
    )
    assert ordinary_wins == EXPECTED_ORDINARY_LOOKUP_WINS
    assert projected_wins == EXPECTED_PROJECTED_LOOKUP_WINS
    assert ordinary_wins <= bench.SAMPLE_COUNT // 2
    assert projected_wins <= bench.SAMPLE_COUNT // 2
