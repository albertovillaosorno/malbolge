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
#   - Integrity checks for retained CRAZY geometry failure-policy evidence.
# - Must-Not:
#   - Require CUDA hardware or reinterpret fallback as accelerator execution.
# - Allows:
#   - Inputs: tracked failure-policy JSON and source-commit provenance.
#   - Outputs: deterministic retained-evidence assertions.
#   - Side effects: tracked evidence reads only.
# - Split-When:
#   - Split when another failure-policy evidence identity is retained.
# - Merge-When:
#   - Merge when another test owns this exact retained evidence directory.
# - Summary:
#   - Locks N10-N14 one-byte resource failure boundaries and provenance.
# - Description:
#   - Recomputes retained boundary relationships from the JSON rows.
# - Usage:
#   - Run without accelerator hardware on every validation host.
# - Defaults:
#   - Evidence source commit is the clean harness commit, not this test commit.
#

"""Integrity checks for retained CRAZY geometry failure-policy evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final
from typing import cast

EVIDENCE_ROOT: Final = (
    Path("benchmarks/accelerator/evidence")
    / "2026-09-04-profile-width-crazy-geometry-failure-policy"
)
EXPECTED_BENCHMARK_ID: Final = (
    "cuda-profile-width-crazy-geometry-failure-policy-v1"
)
EXPECTED_FAILURE_POLICY: Final = "planner-fail-closed-before-allocation"
EXPECTED_FALLBACK_POLICY: Final = "optional-backend-unavailable-safe-rust"
EXPECTED_SOURCE_COMMIT: Final = "fc9638565984ff5ff0e97274a783aabf88df31fc"
EXPECTED_WIDTHS: Final = (10, 11, 12, 13, 14)
EXPECTED_REQUIRED_BYTES: Final = (
    301_804,
    774_196,
    2_191_372,
    6_442_900,
    19_197_484,
)


def _payload() -> dict[str, object]:
    return cast(
        "dict[str, object]",
        json.loads((EVIDENCE_ROOT / "failure-policy.json").read_text()),
    )


def _rows() -> tuple[dict[str, object], ...]:
    value = _payload()["rows"]
    if not isinstance(value, list):
        message = "retained CRAZY failure-policy rows must be a JSON array"
        raise TypeError(message)
    converted: list[dict[str, object]] = []
    for row in cast("list[object]", value):
        if not isinstance(row, dict):
            message = "retained CRAZY failure-policy row must be a JSON object"
            raise TypeError(message)
        converted.append(cast("dict[str, object]", row))
    return tuple(converted)


def test_failure_policy_evidence_has_clean_source_identity() -> None:
    """Retained JSON remains bound to the clean harness source commit."""
    source = (EVIDENCE_ROOT / "source-commit.txt").read_text().strip()
    payload = _payload()
    assert source == EXPECTED_SOURCE_COMMIT
    assert payload["benchmark_id"] == EXPECTED_BENCHMARK_ID
    assert payload["failure_policy"] == EXPECTED_FAILURE_POLICY
    assert payload["product_fallback_policy"] == EXPECTED_FALLBACK_POLICY
    assert tuple(cast("list[int]", payload["widths"])) == EXPECTED_WIDTHS


def test_failure_policy_evidence_keeps_exact_one_byte_boundaries() -> None:
    """Every retained width rejects one byte below exact one-VM admission."""
    rows = _rows()
    assert len(rows) == len(EXPECTED_WIDTHS)
    observed_required: list[int] = []
    for row in rows:
        required = cast("int", row["required_chunk_bytes"])
        failing = cast("int", row["failing_usable_memory_bytes"])
        admitted = cast("int", row["admitted_usable_memory_bytes"])
        fixed = cast("int", row["planner_fixed_chunk_bytes"])
        item = cast("int", row["planner_item_bytes_per_vm"])
        observed_required.append(required)
        assert failing + 1 == required
        assert admitted == required
        assert fixed + item == required
        assert cast("int", row["admitted_free_memory_bytes"]) == (
            cast("int", row["failing_free_memory_bytes"]) + 1
        )
        failure_message = cast("str", row["failure_message"])
        assert f"requires {required} bytes" in failure_message
        assert f"only {failing} bytes are budgeted" in failure_message
    assert tuple(observed_required) == EXPECTED_REQUIRED_BYTES
