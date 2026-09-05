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
#   - Integrity checks for retained candidate CRAZY CUDA-event evidence.
# - Must-Not:
#   - Execute CUDA or treat event duration as semantic authority.
# - Allows:
#   - Inputs: tracked event samples and clean source-commit identity.
#   - Outputs: exact shape and non-promotion assertions.
#   - Side effects: tracked-file reads only.
# - Split-When:
#   - Split when another retained event protocol gains independent identity.
# - Merge-When:
#   - Merge when another test owns this exact retained event record.
# - Summary:
#   - Integrity evidence for candidate CRAZY CUDA-event timing.
# - Description:
#   - Locks raw samples, event identities, and rejection of lookup promotion.
# - Usage:
#   - Run under mathematics validation without CUDA hardware.
# - Defaults:
#   - Event timing remains research evidence, never verification authority.
#

"""Integrity checks for retained candidate CRAZY CUDA-event evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from benchmarks.accelerator.crazy_lookup_address_fanout import ORDINARY_ROUTE
from benchmarks.accelerator.crazy_lookup_address_fanout import PREPARED_ROUTE

from benchmarks.accelerator import (
    crazy_lookup_candidate_event_timeline as event,
)

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    ROOT
    / "benchmarks/accelerator/evidence"
    / "2026-09-04-crazy-lookup-candidate-event-timeline-rtx4060"
)
EXPECTED_SOURCE_COMMIT = "7d1ac9414317ede5e6a944a0bc97562fff2331f0"
EXPECTED_DEVICE = {"arch": "sm_89", "name": "NVIDIA GeForce RTX 4060"}
EXPECTED_ROW_COUNT = 4
EXPECTED_ORDINARY_COUNT = 59_049
EXPECTED_PROJECTED_COUNT = 1_024
EXPECTED_ORDINARY_LOOKUP_WINS = 0
EXPECTED_PROJECTED_LOOKUP_WINS = 2


def _payload() -> dict[str, object]:
    return cast(
        "dict[str, object]",
        json.loads((EVIDENCE / "timeline.json").read_text()),
    )


def _rows() -> tuple[dict[str, object], ...]:
    value = _payload()["rows"]
    if not isinstance(value, list):
        message = "retained candidate event rows must be a JSON array"
        raise TypeError(message)
    converted: list[dict[str, object]] = []
    for row in cast("list[object]", value):
        if not isinstance(row, dict):
            message = "retained candidate event row must be a JSON object"
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
        message = "retained candidate event route/geometry identity drifted"
        raise AssertionError(message)
    return matches[0]


def _samples(row: dict[str, object]) -> tuple[float, ...]:
    value = row["raw_duration_ms"]
    if not isinstance(value, list):
        message = "retained candidate event samples must be a JSON array"
        raise TypeError(message)
    samples = cast("list[object]", value)
    if any(type(sample) is not float for sample in samples):
        message = "retained candidate event sample must be an exact JSON float"
        raise TypeError(message)
    return tuple(cast("list[float]", samples))


def _lookup_wins(route_id: str) -> int:
    tritwise = _samples(_row(route_id, event.TRITWISE))
    lookup = _samples(_row(route_id, event.LOOKUP))
    return sum(
        lookup_ms < tritwise_ms
        for tritwise_ms, lookup_ms in zip(tritwise, lookup, strict=True)
    )


def test_retained_candidate_event_evidence_has_exact_identity() -> None:
    """Bind event evidence to its clean harness, identities, and GPU."""
    payload = _payload()
    assert payload["benchmark_id"] == event.BENCHMARK_ID
    assert payload["device"] == EXPECTED_DEVICE
    assert payload["interpretation_limit"] == event.INTERPRETATION_LIMIT
    identities = cast("dict[str, object]", payload["identities"])
    assert identities == {
        "kernel_launch": event.EXPECTED_LAUNCH_ID,
        "kernel_timeline": event.EXPECTED_TIMELINE_ID,
    }
    assert (EVIDENCE / "source-commit.txt").read_text().strip() == (
        EXPECTED_SOURCE_COMMIT
    )
    assert len(_rows()) == EXPECTED_ROW_COUNT


def test_retained_candidate_event_evidence_preserves_all_samples() -> None:
    """Every route and geometry retains exactly fifteen event durations."""
    expected_counts = {
        ORDINARY_ROUTE: EXPECTED_ORDINARY_COUNT,
        PREPARED_ROUTE: EXPECTED_PROJECTED_COUNT,
    }
    for route_id, count in expected_counts.items():
        for geometry in event.GEOMETRIES:
            row = _row(route_id, geometry)
            assert row["candidate_count"] == count
            assert len(_samples(row)) == event.SAMPLE_COUNT


def test_retained_candidate_event_evidence_rejects_lookup_promotion() -> None:
    """Both event medians and paired counts favor retained tritwise behavior."""
    ordinary_tritwise = _row(ORDINARY_ROUTE, event.TRITWISE)
    ordinary_lookup = _row(ORDINARY_ROUTE, event.LOOKUP)
    projected_tritwise = _row(PREPARED_ROUTE, event.TRITWISE)
    projected_lookup = _row(PREPARED_ROUTE, event.LOOKUP)
    assert cast("float", ordinary_tritwise["median_duration_ms"]) < cast(
        "float", ordinary_lookup["median_duration_ms"]
    )
    assert cast("float", projected_tritwise["median_duration_ms"]) < cast(
        "float", projected_lookup["median_duration_ms"]
    )
    assert _lookup_wins(ORDINARY_ROUTE) == EXPECTED_ORDINARY_LOOKUP_WINS
    assert _lookup_wins(PREPARED_ROUTE) == EXPECTED_PROJECTED_LOOKUP_WINS
