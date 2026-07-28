# File:
#   - profile_run_throughput.py
# Path:
#   - benchmarks/accelerator/profile_run_throughput.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - End-to-end resident current-profile CUDA throughput samples.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""End-to-end resident current-profile CUDA throughput samples."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import json
from statistics import median
from statistics import pstdev
import sys
from time import perf_counter_ns
from typing import Final
from typing import TYPE_CHECKING

from accelerator.cuda.profile_run import CudaProfileRunAdapter
from benchmarks.accelerator.profile_workload import GEOMETRY
from benchmarks.accelerator.profile_workload import PROFILE_TRITS
from benchmarks.accelerator.profile_workload import PROFILE_WORDS
from benchmarks.accelerator.profile_workload import STEP_BUDGET
from benchmarks.accelerator.profile_workload import WORD_BYTES
from benchmarks.accelerator.profile_workload import WORKLOAD_DESCRIPTION
from benchmarks.accelerator.profile_workload import profile_noop_request
from benchmarks.accelerator.profile_workload import (
    validate_profile_noop_results,
)

if TYPE_CHECKING:
    from accelerator.profile_run import ProfileRunRequest

BATCH_SIZES: Final = (1, 2, 4, 8, 16, 32)
SAMPLE_COUNT: Final = 15


@dataclass(frozen=True, slots=True)
class ThroughputRow:
    """Serializable raw and summary measurements for one batch size."""

    batch_size: int
    items_per_second_at_median: float
    median_ns: int
    ns_per_item_at_median: float
    pstdev_ns: float
    raw_ns: tuple[int, ...]
    step_budget: int
    vm_steps_per_second_at_median: float


def main() -> int:
    """Measure current-profile CUDA end-to-end resident throughput.

    Returns:
        Zero after emitting raw timing evidence as JSON.

    """
    request = profile_noop_request()
    with CudaProfileRunAdapter(GEOMETRY) as adapter:
        rows = tuple(_measure(adapter, request, size) for size in BATCH_SIZES)
        capability = adapter.capability()
        plan = adapter.plan((request,) * max(BATCH_SIZES))
    payload = {
        "backend": capability.backend_id,
        "batch_sizes": BATCH_SIZES,
        "device": {
            "arch": capability.device_arch,
            "free_memory_bytes": plan.resources.free_memory_bytes,
            "max_threads_per_block": plan.resources.max_threads_per_block,
            "multiprocessor_count": plan.resources.multiprocessor_count,
            "name": capability.device_name,
            "total_memory_bytes": plan.resources.total_memory_bytes,
        },
        "geometry": {
            "memory_bytes_per_vm": PROFILE_WORDS * WORD_BYTES,
            "memory_words": PROFILE_WORDS,
            "word_trits": PROFILE_TRITS,
        },
        "rows": [asdict(row) for row in rows],
        "sample_count": SAMPLE_COUNT,
        "step_budget": STEP_BUDGET,
        "timed_region": "CudaProfileRunAdapter.evaluate",
        "workload": WORKLOAD_DESCRIPTION,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure(
    adapter: CudaProfileRunAdapter,
    request: ProfileRunRequest,
    batch_size: int,
) -> ThroughputRow:
    requests = (request,) * batch_size
    validate_profile_noop_results(adapter.evaluate(requests), batch_size)
    raw: list[int] = []
    for _ in range(SAMPLE_COUNT):
        start = perf_counter_ns()
        results = adapter.evaluate(requests)
        elapsed = perf_counter_ns() - start
        validate_profile_noop_results(results, batch_size)
        raw.append(elapsed)
    median_ns = int(median(raw))
    items_per_second = (batch_size * 1_000_000_000) / median_ns
    return ThroughputRow(
        batch_size=batch_size,
        items_per_second_at_median=items_per_second,
        median_ns=median_ns,
        ns_per_item_at_median=median_ns / batch_size,
        pstdev_ns=pstdev(raw),
        raw_ns=tuple(raw),
        step_budget=STEP_BUDGET,
        vm_steps_per_second_at_median=items_per_second * STEP_BUDGET,
    )


if __name__ == "__main__":
    raise SystemExit(main())
