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
#   - Integrity checks for retained CRAZY lookup address-fanout evidence.
# - Must-Not:
#   - Execute CUDA or reinterpret address fanout as physical cache counters.
# - Allows:
#   - Inputs: tracked structural JSON and clean source-commit identity.
#   - Outputs: exact metadata, row order, histogram, and raw-warp assertions.
#   - Side effects: tracked-file reads and deterministic model construction.
# - Split-When:
#   - Split when hardware cache-counter evidence gains another record.
# - Merge-When:
#   - Merge when another test owns this exact retained fanout record.
# - Summary:
#   - Integrity evidence for canonical CRAZY lookup address fanout.
# - Description:
#   - Locks retained per-warp counts to the deterministic current model.
# - Usage:
#   - Run with mathematics validation; CUDA hardware is not required.
# - Defaults:
#   - Structural fanout remains performance evidence, not semantic authority.
#

"""Integrity checks for retained CRAZY lookup address-fanout evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from benchmarks.accelerator import crazy_lookup_address_fanout as fanout

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = (
    ROOT
    / "benchmarks/accelerator/evidence"
    / "2026-09-04-crazy-lookup-address-fanout"
)
EXPECTED_SOURCE_COMMIT = "bf6cfbc37291f11ef5ea7633b14744d26a5c617f"
EXPECTED_ROW_COUNT = 4
EXPECTED_RAW_CARDINALITY = 3_756


def _payload() -> dict[str, object]:
    return cast(
        "dict[str, object]",
        json.loads((EVIDENCE / "fanout.json").read_text()),
    )


def _rows() -> tuple[dict[str, object], ...]:
    value = _payload()["rows"]
    if not isinstance(value, list):
        message = "retained lookup fanout rows must be a JSON array"
        raise TypeError(message)
    rows = cast("list[object]", value)
    converted: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            message = "retained lookup fanout row must be a JSON object"
            raise TypeError(message)
        converted.append(cast("dict[str, object]", row))
    return tuple(converted)


def _histogram(row: dict[str, object]) -> tuple[tuple[int, int], ...]:
    value = row["histogram"]
    if not isinstance(value, list):
        message = "retained lookup fanout histogram must be a JSON array"
        raise TypeError(message)
    bins = cast("list[object]", value)
    result: list[tuple[int, int]] = []
    for item in bins:
        if not isinstance(item, dict):
            message = "retained lookup fanout bin must be a JSON object"
            raise TypeError(message)
        entry = cast("dict[str, object]", item)
        result.append((
            cast("int", entry["unique_addresses"]),
            cast("int", entry["warp_count"]),
        ))
    return tuple(result)


def test_retained_fanout_identity_is_bound_to_clean_model_commit() -> None:
    """Bind the record to its model, workload, and clean commit."""
    payload = _payload()
    assert payload["benchmark_id"] == fanout.BENCHMARK_ID
    assert payload["workload_id"] == fanout.WORKLOAD_ID
    assert payload["warp_size"] == fanout.WARP_SIZE
    assert payload["crazy_chunk_values"] == fanout.CRAZY_CHUNK_VALUES
    assert payload["interpretation"] == fanout.INTERPRETATION
    assert (EVIDENCE / "source-commit.txt").read_text().strip() == (
        EXPECTED_SOURCE_COMMIT
    )


def test_retained_fanout_rows_equal_current_deterministic_model() -> None:
    """Retained per-warp counts match the current deterministic model."""
    retained = _rows()
    current = fanout.crazy_lookup_address_fanout()
    assert len(retained) == EXPECTED_ROW_COUNT == len(current)
    raw_cardinality = 0
    for saved, generated in zip(retained, current, strict=True):
        raw = tuple(cast("list[int]", saved["raw_unique_addresses_per_warp"]))
        raw_cardinality += len(raw)
        assert saved["route_id"] == generated.route_id
        assert saved["lookup_chunk"] == generated.lookup_chunk
        assert saved["candidate_count"] == generated.candidate_count
        assert saved["warp_count"] == generated.warp_count
        assert saved["total_unique_address_requests"] == (
            generated.total_unique_address_requests
        )
        assert raw == generated.raw_unique_addresses_per_warp
        assert _histogram(saved) == tuple(
            (item.unique_addresses, item.warp_count)
            for item in generated.histogram
        )
    assert raw_cardinality == EXPECTED_RAW_CARDINALITY
