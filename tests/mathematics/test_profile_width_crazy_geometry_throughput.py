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
#   - Deterministic protocol checks for CUDA crazy-geometry throughput.
# - Must-Not:
#   - Require CUDA hardware or treat benchmark timing as semantic evidence.
# - Allows:
#   - Inputs: benchmark identities, route order, and inherited v1 workload.
#   - Outputs: deterministic comparison-protocol assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when another geometry benchmark gains a distinct protocol.
# - Merge-When:
#   - Merge when another test owns this exact three-route measurement identity.
# - Summary:
#   - Protocol tests for the N10-N14 CUDA crazy-geometry benchmark.
# - Description:
#   - Locks route identity/order and reuse of the reviewed v1 workload.
# - Usage:
#   - Run before collecting any retained geometry throughput evidence.
# - Defaults:
#   - Resource assertions cover declared constant bytes, not occupancy or
#     registers.
#

"""Protocol tests for the N10-N14 CUDA crazy-geometry throughput benchmark."""

from __future__ import annotations

from accelerator.cuda.resident_kernel import ResidentCrazyGeometry

from benchmarks.accelerator import (
    profile_width_crazy_geometry_throughput as geom,
)
from benchmarks.accelerator import profile_width_crazy_throughput as baseline

EXPECTED_BENCHMARK_ID = "cuda-profile-width-crazy-geometry-throughput-v1"
EXPECTED_GEOMETRIES = (
    ResidentCrazyGeometry.TRITWISE,
    ResidentCrazyGeometry.NATIVE,
    ResidentCrazyGeometry.PADDED,
)
EXPECTED_TRITWISE_CONSTANT_BYTES = 188
EXPECTED_LOOKUP_CONSTANT_BYTES = 59_237


def test_geometry_benchmark_reuses_exact_v1_workload_authority() -> None:
    """Geometry comparison cannot fork the reviewed workload or oracle."""
    assert geom.BENCHMARK_ID == EXPECTED_BENCHMARK_ID
    assert geom.BASELINE_BENCHMARK_ID == baseline.BENCHMARK_ID
    assert geom.WORKLOAD_ID == baseline.WORKLOAD_ID
    assert geom.WIDTHS == baseline.WIDTHS
    assert geom.STEP_BUDGET == baseline.STEP_BUDGET
    assert geom.SAMPLE_COUNT == baseline.SAMPLE_COUNT


def test_geometry_route_order_rotates_first_block_without_omissions() -> None:
    """Consecutive widths rotate the first route while retaining all routes."""
    assert geom.CRAZY_GEOMETRIES == EXPECTED_GEOMETRIES
    assert geom.rotated_crazy_geometry_order(0) == EXPECTED_GEOMETRIES
    assert geom.rotated_crazy_geometry_order(1) == (
        EXPECTED_GEOMETRIES[1:] + EXPECTED_GEOMETRIES[:1]
    )
    assert geom.rotated_crazy_geometry_order(2) == (
        EXPECTED_GEOMETRIES[2:] + EXPECTED_GEOMETRIES[:2]
    )
    assert geom.rotated_crazy_geometry_order(3) == EXPECTED_GEOMETRIES


def test_geometry_declared_constant_bytes_separate_lookup_pressure() -> None:
    """Lookup routes report their extra source-declared constant footprint."""
    assert (
        geom.declared_constant_bytes(ResidentCrazyGeometry.TRITWISE)
        == EXPECTED_TRITWISE_CONSTANT_BYTES
    )
    for route in (
        ResidentCrazyGeometry.NATIVE,
        ResidentCrazyGeometry.PADDED,
    ):
        assert (
            geom.declared_constant_bytes(route)
            == EXPECTED_LOOKUP_CONSTANT_BYTES
        )
