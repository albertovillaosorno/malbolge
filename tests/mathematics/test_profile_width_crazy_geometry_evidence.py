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
#   - Integrity checks for retained CUDA crazy-geometry evidence.
# - Must-Not:
#   - Execute CUDA or turn benchmark timing into semantic authority.
# - Allows:
#   - Inputs: tracked RTX 4060 raw evidence and source-commit identity.
#   - Outputs: deterministic evidence-shape and documented-winner assertions.
#   - Side effects: tracked-file reads only.
# - Split-When:
#   - Split when another retained geometry run gains an independent identity.
# - Merge-When:
#   - Merge when another test owns this exact retained evidence record.
# - Summary:
#   - Integrity evidence for the N10-N14 CUDA crazy-geometry comparison.
# - Description:
#   - Locks raw cardinality, resources, occupancy, and documented median
#     winners.
# - Usage:
#   - Run with mathematics validation; CUDA hardware is not required.
# - Defaults:
#   - Retained timings remain evidence only and never verification authority.
#

"""Integrity checks for retained CUDA crazy-geometry evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    ROOT
    / "benchmarks/accelerator/evidence"
    / "2026-09-04-profile-width-crazy-geometry-throughput-rtx4060"
)
EXPECTED_BENCHMARK_ID = "cuda-profile-width-crazy-geometry-throughput-v1"
EXPECTED_SOURCE_COMMIT = "ac62c4becb9b7e5606026bbb668e810a67a24ca4"
EXPECTED_WIDTHS = (10, 11, 12, 13, 14)
EXPECTED_MODES = frozenset(("tritwise", "native-5+5+r", "padded-5+5+5"))
EXPECTED_SAMPLE_COUNT = 15
EXPECTED_ROW_COUNT = len(EXPECTED_WIDTHS) * len(EXPECTED_MODES)
EXPECTED_ACTIVE_BLOCKS = 6
EXPECTED_THREADS_PER_BLOCK = 256
EXPECTED_THREADS_PER_MULTIPROCESSOR = 1536


def _payload() -> dict[str, object]:
    return cast(
        "dict[str, object]",
        json.loads((EVIDENCE / "throughput.json").read_text()),
    )


def _rows() -> tuple[dict[str, object], ...]:
    rows_value = _payload()["rows"]
    if not isinstance(rows_value, list):
        message = "retained crazy-geometry rows must be a JSON array"
        raise TypeError(message)
    rows = cast("list[object]", rows_value)
    converted: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            message = "retained crazy-geometry row must be a JSON object"
            raise TypeError(message)
        converted.append(cast("dict[str, object]", row))
    return tuple(converted)


def test_retained_crazy_geometry_evidence_has_exact_identity_and_samples(
) -> None:
    """The retained run preserves its clean harness and complete raw matrix."""
    payload = _payload()
    assert payload["benchmark_id"] == EXPECTED_BENCHMARK_ID
    assert tuple(cast("list[int]", payload["widths"])) == EXPECTED_WIDTHS
    assert (EVIDENCE / "source-commit.txt").read_text().strip() == (
        EXPECTED_SOURCE_COMMIT
    )
    rows = _rows()
    assert len(rows) == EXPECTED_ROW_COUNT
    for row in rows:
        assert len(cast("list[int]", row["resident_raw_ns"])) == (
            EXPECTED_SAMPLE_COUNT
        )
        assert len(cast("list[int]", row["end_to_end_raw_ns"])) == (
            EXPECTED_SAMPLE_COUNT
        )


def test_retained_resources_and_documented_median_winners_match_raw() -> None:
    """Resource invariants and the documented route winners derive from raw."""
    rows = _rows()
    by_width: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        width = cast("int", row["word_trits"])
        by_width.setdefault(width, []).append(row)
        assert row["driver_constant_memory_bytes"] == (
            row["declared_constant_bytes"]
        )
        assert row["driver_active_blocks_per_multiprocessor_at_launch"] == (
            EXPECTED_ACTIVE_BLOCKS
        )
        assert row["driver_launch_threads_per_block"] == (
            EXPECTED_THREADS_PER_BLOCK
        )
        assert row["driver_max_threads_per_multiprocessor"] == (
            EXPECTED_THREADS_PER_MULTIPROCESSOR
        )
    for width, width_rows in by_width.items():
        assert {cast("str", row["crazy_geometry"]) for row in width_rows} == (
            EXPECTED_MODES
        )
        resident_winner = min(
            width_rows,
            key=lambda row: cast("int", row["resident_median_ns"]),
        )["crazy_geometry"]
        end_to_end_winner = min(
            width_rows,
            key=lambda row: cast("int", row["end_to_end_median_ns"]),
        )["crazy_geometry"]
        expected = (
            "native-5+5+r"
            if width == EXPECTED_WIDTHS[0]
            else "padded-5+5+5"
        )
        assert resident_winner == expected
        assert end_to_end_winner == expected
