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
#   - CUDA resident footprint and live batch-plan evidence by CRAZY geometry.
# - Must-Not:
#   - Allocate the planned batch, time kernels, or change product selection.
# - Allows:
#   - Inputs: frozen N10-N14 crazy workload and explicit research geometries.
#   - Outputs: exact per-VM bytes and live resource-plan summaries.
#   - Side effects: CUDA context/module setup and stdout JSON only.
# - Split-When:
#   - Split when another workload or resource-planning question is admitted.
# - Merge-When:
#   - Merge when another diagnostic owns this exact geometry/resource matrix.
# - Summary:
#   - N10-N14 CRAZY geometry VRAM, transfer, and admitted batch evidence.
# - Description:
#   - Separates one-VM buffer accounting from live planner capacity.
# - Usage:
#   - Run from a clean commit and retain with exact device provenance.
# - Defaults:
#   - Plans 100,000 repeated requests without allocating the planned batch.
#

"""CUDA resident resource accounting across CRAZY arithmetic geometries."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import json
import sys
from typing import Final
from typing import TYPE_CHECKING

from accelerator.cuda.profile_run import CudaProfileRunAdapter
from accelerator.cuda.profile_run import cuda_profile_resident_footprint

from benchmarks.accelerator import (
    profile_width_crazy_geometry_throughput as geom,
)
from benchmarks.accelerator import profile_width_crazy_throughput as baseline

if TYPE_CHECKING:
    from accelerator.cuda.resident_kernel import ResidentCrazyGeometry
    from accelerator.profile_run import ProfileRunRequest

BENCHMARK_ID: Final = "cuda-profile-width-crazy-geometry-resources-v1"
PLANNING_REQUESTS: Final = 100_000
WIDTHS: Final = geom.WIDTHS
CRAZY_GEOMETRIES: Final = geom.CRAZY_GEOMETRIES
WORKLOAD_ID: Final = geom.WORKLOAD_ID


@dataclass(frozen=True, slots=True)
class CrazyGeometryResourceRow:
    """One width/geometry footprint plus live resource-plan observation."""

    crazy_geometry: str
    device_allocated_bytes_per_vm: int
    first_chunk_bytes: int
    first_chunk_items: int
    free_memory_bytes: int
    initial_host_to_device_bytes_per_vm: int
    input_buffer_bytes_per_vm: int
    memory_bytes_per_vm: int
    output_buffer_bytes_per_vm: int
    planner_fixed_chunk_bytes: int
    planner_item_bytes_per_vm: int
    planning_requested_items: int
    reserve_bytes: int
    state_bytes_per_vm: int
    total_chunks: int
    total_memory_bytes: int
    usable_memory_bytes: int
    word_trits: int


def main() -> int:
    """Emit per-VM CUDA footprint and live planner capacity by geometry.

    Returns:
        Zero after every configured width and geometry is observed.

    """
    rows: list[CrazyGeometryResourceRow] = []
    device: dict[str, str] | None = None
    for word_trits in WIDTHS:
        measured, width_device = _measure_width(word_trits)
        rows.extend(measured)
        if device is None:
            device = width_device
    payload = {
        "benchmark_id": BENCHMARK_ID,
        "crazy_geometries": tuple(item.value for item in CRAZY_GEOMETRIES),
        "device": device,
        "planning_requested_items": PLANNING_REQUESTS,
        "rows": [asdict(row) for row in rows],
        "widths": WIDTHS,
        "workload_id": WORKLOAD_ID,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure_width(
    word_trits: int,
) -> tuple[tuple[CrazyGeometryResourceRow, ...], dict[str, str]]:
    request = baseline.profile_width_crazy_request(word_trits)
    geometry = baseline.profile_width_crazy_geometry(word_trits)
    rows: list[CrazyGeometryResourceRow] = []
    device: dict[str, str] | None = None
    for crazy_geometry in CRAZY_GEOMETRIES:
        with CudaProfileRunAdapter(
            geometry,
            crazy_geometry=crazy_geometry,
        ) as adapter:
            if device is None:
                capability = adapter.capability()
                device = {
                    "arch": capability.device_arch,
                    "name": capability.device_name,
                }
            rows.append(
                _row(
                    adapter,
                    request,
                    word_trits=word_trits,
                    crazy_geometry=crazy_geometry,
                )
            )
    if device is None:
        message = "CRAZY geometry resource diagnostic has no routes"
        raise RuntimeError(message)
    return tuple(rows), device


def _row(
    adapter: CudaProfileRunAdapter,
    request: ProfileRunRequest,
    *,
    word_trits: int,
    crazy_geometry: ResidentCrazyGeometry,
) -> CrazyGeometryResourceRow:
    footprint = cuda_profile_resident_footprint(
        baseline.profile_width_crazy_geometry(word_trits),
        request,
    )
    plan = adapter.plan((request,) * PLANNING_REQUESTS)
    if not plan.chunks:
        message = "CRAZY geometry resource plan unexpectedly has no chunks"
        raise RuntimeError(message)
    first = plan.chunks[0]
    return CrazyGeometryResourceRow(
        crazy_geometry=crazy_geometry.value,
        device_allocated_bytes_per_vm=footprint.device_allocated_bytes,
        first_chunk_bytes=first.bytes_required,
        first_chunk_items=first.item_count,
        free_memory_bytes=plan.resources.free_memory_bytes,
        initial_host_to_device_bytes_per_vm=(
            footprint.initial_host_to_device_bytes
        ),
        input_buffer_bytes_per_vm=footprint.input_buffer_bytes,
        memory_bytes_per_vm=footprint.memory_bytes,
        output_buffer_bytes_per_vm=footprint.output_buffer_bytes,
        planner_fixed_chunk_bytes=footprint.planner_fixed_chunk_bytes,
        planner_item_bytes_per_vm=footprint.planner_item_bytes,
        planning_requested_items=PLANNING_REQUESTS,
        reserve_bytes=plan.reserve_bytes,
        state_bytes_per_vm=footprint.state_bytes,
        total_chunks=len(plan.chunks),
        total_memory_bytes=plan.resources.total_memory_bytes,
        usable_memory_bytes=plan.usable_memory_bytes,
        word_trits=word_trits,
    )


if __name__ == "__main__":
    raise SystemExit(main())
