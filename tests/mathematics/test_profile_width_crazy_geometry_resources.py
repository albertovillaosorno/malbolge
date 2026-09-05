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
#   - Protocol checks for CRAZY geometry resident-resource diagnostics.
# - Must-Not:
#   - Require CUDA hardware or infer performance from resource accounting.
# - Allows:
#   - Inputs: diagnostic constants and frozen crazy-width workload authority.
#   - Outputs: stable identity and exact footprint-formula assertions.
#   - Side effects: none.
# - Split-When:
#   - Split when another resource protocol gains independent identity.
# - Merge-When:
#   - Merge when another test owns this exact resource diagnostic protocol.
# - Summary:
#   - Protocol regression for CRAZY geometry VRAM and transfer accounting.
# - Description:
#   - Locks workload reuse and the 100,000-request planning horizon.
# - Usage:
#   - Run under mathematics validation without CUDA hardware.
# - Defaults:
#   - Geometry arithmetic must not change per-VM state shape.
#

"""Protocol checks for CRAZY geometry resident-resource diagnostics."""

from __future__ import annotations

from accelerator.classic_run import STATE_WORDS
from accelerator.cuda.profile_run import cuda_profile_resident_footprint

from benchmarks.accelerator import profile_width_crazy_geometry_resources as res
from benchmarks.accelerator import (
    profile_width_crazy_geometry_throughput as geom,
)
from benchmarks.accelerator import profile_width_crazy_throughput as baseline

EXPECTED_BENCHMARK_ID = "cuda-profile-width-crazy-geometry-resources-v1"
EXPECTED_PLANNING_REQUESTS = 100_000


def test_geometry_resource_diagnostic_reuses_frozen_workload() -> None:
    """Resource evidence cannot silently fork widths, routes, or workload."""
    assert res.BENCHMARK_ID == EXPECTED_BENCHMARK_ID
    assert res.PLANNING_REQUESTS == EXPECTED_PLANNING_REQUESTS
    assert res.WIDTHS == geom.WIDTHS == baseline.WIDTHS
    assert res.CRAZY_GEOMETRIES == geom.CRAZY_GEOMETRIES
    assert res.WORKLOAD_ID == geom.WORKLOAD_ID == baseline.WORKLOAD_ID


def test_geometry_resource_expected_one_vm_bytes_are_route_independent(
) -> None:
    """Arithmetic route cannot alter one request's semantic resident shape."""
    for word_trits in res.WIDTHS:
        geometry = baseline.profile_width_crazy_geometry(word_trits)
        state_bytes = STATE_WORDS * baseline.WORD_BYTES
        memory_bytes = geometry.memory_words * baseline.WORD_BYTES
        input_buffer_bytes = baseline.WORD_BYTES
        output_buffer_bytes = baseline.STEP_BUDGET * baseline.WORD_BYTES
        allocated = (
            state_bytes
            + memory_bytes
            + input_buffer_bytes
            + output_buffer_bytes
        )
        planner_item = allocated - input_buffer_bytes
        assert planner_item > memory_bytes
        assert allocated == planner_item + baseline.WORD_BYTES


def test_cuda_profile_resident_footprint_matches_exact_buffer_layout() -> None:
    """Public accounting matches the four one-request CUDA allocations."""
    for word_trits in res.WIDTHS:
        geometry = baseline.profile_width_crazy_geometry(word_trits)
        request = baseline.profile_width_crazy_request(word_trits)
        footprint = cuda_profile_resident_footprint(geometry, request)
        assert footprint.state_bytes == STATE_WORDS * baseline.WORD_BYTES
        assert footprint.memory_bytes == (
            geometry.memory_words * baseline.WORD_BYTES
        )
        assert footprint.input_buffer_bytes == baseline.WORD_BYTES
        assert footprint.output_buffer_bytes == (
            baseline.STEP_BUDGET * baseline.WORD_BYTES
        )
        assert footprint.device_allocated_bytes == (
            footprint.state_bytes
            + footprint.memory_bytes
            + footprint.input_buffer_bytes
            + footprint.output_buffer_bytes
        )
        assert footprint.initial_host_to_device_bytes == (
            footprint.device_allocated_bytes
        )
        assert footprint.planner_item_bytes == (
            footprint.device_allocated_bytes - footprint.input_buffer_bytes
        )
        assert footprint.planner_fixed_chunk_bytes == 2 * baseline.WORD_BYTES
