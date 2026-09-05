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
#   - Deterministic N10-N14 resident resource rejection-boundary evidence.
# - Must-Not:
#   - Allocate CUDA memory, time execution, or select a product geometry.
# - Allows:
#   - Inputs: frozen crazy-width workload and hardware-neutral resource planner.
#   - Outputs: exact fail-closed/admitted byte boundaries serialized as JSON.
#   - Side effects: stdout JSON only.
# - Split-When:
#   - Split when operational backend fallback needs a different evidence source.
# - Merge-When:
#   - Merge when another diagnostic owns this exact rejection-boundary matrix.
# - Summary:
#   - CRAZY-width resident planner failure boundaries before CUDA allocation.
# - Description:
#   - Proves each N10-N14 VM is rejected one byte below its required chunk size.
# - Usage:
#   - Run without CUDA hardware; pair with product safe-Rust fallback tests.
# - Defaults:
#   - Uses a 128 MiB synthetic device so the minimum reserve is exactly 8 MiB.
#

"""Deterministic resource rejection boundaries for CRAZY-width CUDA states."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import json
import sys
from typing import Final

from accelerator.cuda.profile_run import cuda_profile_resident_footprint
from accelerator.resource_budget import AcceleratorResources
from accelerator.resource_budget import MINIMUM_RESERVE_BYTES
from accelerator.resource_budget import ResourceBudgetError
from accelerator.resource_budget import plan_resident_batches

from benchmarks.accelerator import profile_width_crazy_throughput as baseline

BENCHMARK_ID: Final = "cuda-profile-width-crazy-geometry-failure-policy-v1"
MIB: Final = 1024 * 1024
SYNTHETIC_TOTAL_MEMORY_BYTES: Final = 128 * MIB
SYNTHETIC_THREADS_PER_BLOCK: Final = 256
SYNTHETIC_MULTIPROCESSORS: Final = 1
RESERVE_BYTES: Final = MINIMUM_RESERVE_BYTES
WIDTHS: Final = baseline.WIDTHS
WORKLOAD_ID: Final = baseline.WORKLOAD_ID
FAILURE_POLICY: Final = "planner-fail-closed-before-allocation"
PRODUCT_FALLBACK_POLICY: Final = "optional-backend-unavailable-safe-rust"


@dataclass(frozen=True, slots=True)
class CrazyGeometryFailureBoundary:
    """Exact one-byte resource rejection/admission boundary for one width."""

    admitted_free_memory_bytes: int
    admitted_usable_memory_bytes: int
    failing_free_memory_bytes: int
    failing_usable_memory_bytes: int
    failure_message: str
    planner_fixed_chunk_bytes: int
    planner_item_bytes_per_vm: int
    required_chunk_bytes: int
    reserve_bytes: int
    word_trits: int


def failure_boundaries() -> tuple[CrazyGeometryFailureBoundary, ...]:
    """Return exact N10-N14 planner rejection/admission boundaries.

    Returns:
        One row per width using the same per-item accounting as CUDA profiles.

    """
    return tuple(_boundary(word_trits) for word_trits in WIDTHS)


def main() -> int:
    """Emit the deterministic failure-policy matrix as JSON.

    Returns:
        Zero after all width boundaries validate.

    """
    payload = {
        "benchmark_id": BENCHMARK_ID,
        "failure_policy": FAILURE_POLICY,
        "product_fallback_policy": PRODUCT_FALLBACK_POLICY,
        "rows": [asdict(row) for row in failure_boundaries()],
        "synthetic_total_memory_bytes": SYNTHETIC_TOTAL_MEMORY_BYTES,
        "widths": WIDTHS,
        "workload_id": WORKLOAD_ID,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _boundary(word_trits: int) -> CrazyGeometryFailureBoundary:
    footprint = cuda_profile_resident_footprint(
        baseline.profile_width_crazy_geometry(word_trits),
        baseline.profile_width_crazy_request(word_trits),
    )
    required = (
        footprint.planner_fixed_chunk_bytes + footprint.planner_item_bytes
    )
    failing_usable = required - 1
    failing_resources = _resources(RESERVE_BYTES + failing_usable)
    failure_message = _rejection_message(
        footprint.planner_item_bytes,
        footprint.planner_fixed_chunk_bytes,
        failing_resources,
    )
    admitted_resources = _resources(RESERVE_BYTES + required)
    admitted = plan_resident_batches(
        (footprint.planner_item_bytes,),
        admitted_resources,
        fixed_chunk_bytes=footprint.planner_fixed_chunk_bytes,
    )
    first = admitted.chunks[0]
    if first.item_count != 1 or first.bytes_required != required:
        message = "CRAZY geometry failure boundary admission drifted"
        raise RuntimeError(message)
    if admitted.reserve_bytes != RESERVE_BYTES:
        message = "CRAZY geometry failure boundary reserve drifted"
        raise RuntimeError(message)
    return CrazyGeometryFailureBoundary(
        admitted_free_memory_bytes=admitted_resources.free_memory_bytes,
        admitted_usable_memory_bytes=admitted.usable_memory_bytes,
        failing_free_memory_bytes=failing_resources.free_memory_bytes,
        failing_usable_memory_bytes=failing_usable,
        failure_message=failure_message,
        planner_fixed_chunk_bytes=footprint.planner_fixed_chunk_bytes,
        planner_item_bytes_per_vm=footprint.planner_item_bytes,
        required_chunk_bytes=required,
        reserve_bytes=admitted.reserve_bytes,
        word_trits=word_trits,
    )


def _resources(free_memory_bytes: int) -> AcceleratorResources:
    return AcceleratorResources(
        free_memory_bytes=free_memory_bytes,
        max_threads_per_block=SYNTHETIC_THREADS_PER_BLOCK,
        multiprocessor_count=SYNTHETIC_MULTIPROCESSORS,
        total_memory_bytes=SYNTHETIC_TOTAL_MEMORY_BYTES,
    )


def _rejection_message(
    item_bytes: int,
    fixed_chunk_bytes: int,
    resources: AcceleratorResources,
) -> str:
    try:
        _ = plan_resident_batches(
            (item_bytes,),
            resources,
            fixed_chunk_bytes=fixed_chunk_bytes,
        )
    except ResourceBudgetError as error:
        return str(error)
    message = "CRAZY geometry failure boundary unexpectedly admitted"
    raise RuntimeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
