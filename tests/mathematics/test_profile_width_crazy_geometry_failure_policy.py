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
#   - Hardware-free CRAZY geometry resource failure-policy regressions.
# - Must-Not:
#   - Require CUDA, allocate device memory, or infer product route selection.
# - Allows:
#   - Inputs: deterministic failure-policy benchmark rows.
#   - Outputs: exact one-byte rejection/admission boundary assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when operational backend fallback gains independent Python evidence.
# - Merge-When:
#   - Merge when another test owns this exact N10-N14 boundary matrix.
# - Summary:
#   - Locks fail-closed resident resource boundaries for CRAZY widths.
# - Description:
#   - Verifies one-byte-below rejection and exact-byte admission for N10-N14.
# - Usage:
#   - Run with mathematics/resource tests on every host.
# - Defaults:
#   - Product fallback semantics remain owned and tested by the Rust VM layer.
#

"""Hardware-free CRAZY geometry resource failure-policy regressions."""

from __future__ import annotations

from benchmarks.accelerator import (
    profile_width_crazy_geometry_failure_policy as failure,
)
from benchmarks.accelerator import profile_width_crazy_throughput as baseline

EXPECTED_BENCHMARK_ID = "cuda-profile-width-crazy-geometry-failure-policy-v1"
EXPECTED_FIXED_CHUNK_BYTES = 8
EXPECTED_POLICY = "planner-fail-closed-before-allocation"
EXPECTED_PRODUCT_FALLBACK = "optional-backend-unavailable-safe-rust"


def test_failure_policy_reuses_frozen_crazy_width_workload() -> None:
    """Failure evidence cannot fork the reviewed N10-N14 workload identity."""
    assert failure.BENCHMARK_ID == EXPECTED_BENCHMARK_ID
    assert failure.WIDTHS == baseline.WIDTHS
    assert failure.WORKLOAD_ID == baseline.WORKLOAD_ID
    assert failure.FAILURE_POLICY == EXPECTED_POLICY
    assert failure.PRODUCT_FALLBACK_POLICY == EXPECTED_PRODUCT_FALLBACK


def test_each_width_rejects_one_byte_below_exact_required_chunk() -> None:
    """Every N10-N14 state crosses from rejection to admission at one byte."""
    rows = failure.failure_boundaries()
    assert tuple(row.word_trits for row in rows) == baseline.WIDTHS
    for row in rows:
        assert row.planner_fixed_chunk_bytes == EXPECTED_FIXED_CHUNK_BYTES
        assert row.required_chunk_bytes == (
            row.planner_fixed_chunk_bytes + row.planner_item_bytes_per_vm
        )
        assert row.failing_usable_memory_bytes + 1 == row.required_chunk_bytes
        assert row.admitted_usable_memory_bytes == row.required_chunk_bytes
        assert row.admitted_free_memory_bytes == (
            row.failing_free_memory_bytes + 1
        )
        assert row.reserve_bytes == failure.RESERVE_BYTES
        assert (
            f"requires {row.required_chunk_bytes} bytes"
            in row.failure_message
        )
        assert (
            f"only {row.failing_usable_memory_bytes} bytes are budgeted"
            in row.failure_message
        )
