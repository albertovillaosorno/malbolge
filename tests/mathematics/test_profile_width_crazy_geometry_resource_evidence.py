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
#   - Integrity checks for retained N10-N14 CRAZY resource evidence.
# - Must-Not:
#   - Execute CUDA or turn resource capacity into semantic authority.
# - Allows:
#   - Inputs: tracked resource JSON and clean source-commit identity.
#   - Outputs: exact footprint, chunk, and provenance assertions.
#   - Side effects: tracked-file reads only.
# - Split-When:
#   - Split when another retained resource matrix gains independent identity.
# - Merge-When:
#   - Merge when another test owns this exact resource evidence record.
# - Summary:
#   - Integrity evidence for N10-N14 CRAZY resident resource accounting.
# - Description:
#   - Locks route-independent per-VM bytes and retained live planner snapshots.
# - Usage:
#   - Run under mathematics validation without CUDA hardware.
# - Defaults:
#   - Capacity differences remain tied to their measured free-memory snapshots.
#

"""Integrity checks for retained CRAZY geometry resident resource evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from benchmarks.accelerator import profile_width_crazy_geometry_resources as res

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    ROOT
    / "benchmarks/accelerator/evidence"
    / "2026-09-04-profile-width-crazy-geometry-resources-rtx4060"
)
EXPECTED_SOURCE_COMMIT = "f325d3ee0c7b00c996093842c8c31c1433b85247"
EXPECTED_DEVICE = {"arch": "sm_89", "name": "NVIDIA GeForce RTX 4060"}
EXPECTED_ROW_COUNT = 15
EXPECTED_FIXED_CHUNK_BYTES = 8
EXPECTED_FOOTPRINTS = {
    10: (301_800, 301_796),
    11: (774_192, 774_188),
    12: (2_191_368, 2_191_364),
    13: (6_442_896, 6_442_892),
    14: (19_197_480, 19_197_476),
}
EXPECTED_FIRST_CHUNKS = {
    10: (16_360, 16_360, 16_360),
    11: (6_396, 6_400, 6_406),
    12: (2_263, 2_257, 2_265),
    13: (769, 769, 769),
    14: (258, 257, 257),
}


def _payload() -> dict[str, object]:
    return cast(
        "dict[str, object]",
        json.loads((EVIDENCE / "resources.json").read_text()),
    )


def _rows() -> tuple[dict[str, object], ...]:
    value = _payload()["rows"]
    if not isinstance(value, list):
        message = "retained CRAZY resource rows must be a JSON array"
        raise TypeError(message)
    converted: list[dict[str, object]] = []
    for row in cast("list[object]", value):
        if not isinstance(row, dict):
            message = "retained CRAZY resource row must be a JSON object"
            raise TypeError(message)
        converted.append(cast("dict[str, object]", row))
    return tuple(converted)


def test_retained_geometry_resources_have_exact_identity() -> None:
    """Bind the retained matrix to its clean diagnostic, device, and horizon."""
    payload = _payload()
    assert payload["benchmark_id"] == res.BENCHMARK_ID
    assert payload["device"] == EXPECTED_DEVICE
    assert payload["planning_requested_items"] == res.PLANNING_REQUESTS
    assert tuple(cast("list[int]", payload["widths"])) == res.WIDTHS
    assert len(_rows()) == EXPECTED_ROW_COUNT
    assert (EVIDENCE / "source-commit.txt").read_text().strip() == (
        EXPECTED_SOURCE_COMMIT
    )


def test_retained_geometry_resources_preserve_exact_per_vm_footprints() -> None:
    """Arithmetic route never changes one VM's allocation or initial upload."""
    for width, (allocated, planner_item) in EXPECTED_FOOTPRINTS.items():
        rows = tuple(row for row in _rows() if row["word_trits"] == width)
        assert len(rows) == len(res.CRAZY_GEOMETRIES)
        for row in rows:
            assert row["device_allocated_bytes_per_vm"] == allocated
            assert row["initial_host_to_device_bytes_per_vm"] == allocated
            assert row["planner_item_bytes_per_vm"] == planner_item
            assert row["planner_fixed_chunk_bytes"] == (
                EXPECTED_FIXED_CHUNK_BYTES
            )


def test_retained_geometry_resources_preserve_live_chunk_plans() -> None:
    """First chunks remain bound to retained free-memory snapshots."""
    geometries = tuple(item.value for item in res.CRAZY_GEOMETRIES)
    for width, expected_items in EXPECTED_FIRST_CHUNKS.items():
        rows = tuple(row for row in _rows() if row["word_trits"] == width)
        ordered = tuple(
            next(row for row in rows if row["crazy_geometry"] == geometry)
            for geometry in geometries
        )
        assert tuple(row["first_chunk_items"] for row in ordered) == (
            expected_items
        )
        for row in ordered:
            expected_bytes = cast("int", row["planner_fixed_chunk_bytes"]) + (
                cast("int", row["first_chunk_items"])
                * cast("int", row["planner_item_bytes_per_vm"])
            )
            assert row["first_chunk_bytes"] == expected_bytes
            assert cast("int", row["first_chunk_bytes"]) <= cast(
                "int", row["usable_memory_bytes"]
            )
            assert cast("int", row["total_chunks"]) > 0
