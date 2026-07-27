# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Phase-separated diagnostics for resident current-profile CUDA execution."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import json
from statistics import median
import sys
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
    from accelerator.cuda.profile_run import ProfileRunPhaseProfile
    from accelerator.profile_run import ProfileRunRequest

BATCH_SIZES: Final = (1, 8, 32)
SAMPLE_COUNT: Final = 15


@dataclass(frozen=True, slots=True)
class PhaseSummary:
    """Median current-profile phase costs for one batch size."""

    allocate_ns: int
    batch_size: int
    decode_ns: int
    download_ns: int
    host_build_ns: int
    kernel_ns: int
    release_ns: int
    total_ns: int
    upload_ns: int
    validation_plan_ns: int


def main() -> int:
    """Measure current-profile CUDA phases using adapter diagnostics.

    Returns:
        Zero after emitting raw and median phase evidence as JSON.

    """
    request = profile_noop_request()
    with CudaProfileRunAdapter(GEOMETRY) as adapter:
        rows = tuple(_measure(adapter, request, size) for size in BATCH_SIZES)
        capability = adapter.capability()
        plan = adapter.plan((request,) * max(BATCH_SIZES))
    payload = {
        "backend": capability.backend_id,
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
        "rows": [
            {
                "batch_size": summary.batch_size,
                "median": asdict(summary),
                "samples": [asdict(sample) for sample in samples],
            }
            for summary, samples in rows
        ],
        "sample_count": SAMPLE_COUNT,
        "step_budget": STEP_BUDGET,
        "workload": WORKLOAD_DESCRIPTION,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure(
    adapter: CudaProfileRunAdapter,
    request: ProfileRunRequest,
    batch_size: int,
) -> tuple[PhaseSummary, tuple[ProfileRunPhaseProfile, ...]]:
    requests = (request,) * batch_size
    validate_profile_noop_results(adapter.evaluate(requests), batch_size)
    samples: list[ProfileRunPhaseProfile] = []
    for _ in range(SAMPLE_COUNT):
        results, profile = adapter.profile_evaluate(requests)
        validate_profile_noop_results(results, batch_size)
        samples.append(profile)
    frozen = tuple(samples)
    return _summarize(batch_size, frozen), frozen


def _summarize(
    batch_size: int,
    samples: tuple[ProfileRunPhaseProfile, ...],
) -> PhaseSummary:
    return PhaseSummary(
        allocate_ns=_median_values(tuple(item.allocate_ns for item in samples)),
        batch_size=batch_size,
        decode_ns=_median_values(tuple(item.decode_ns for item in samples)),
        download_ns=_median_values(tuple(item.download_ns for item in samples)),
        host_build_ns=_median_values(
            tuple(item.host_build_ns for item in samples)
        ),
        kernel_ns=_median_values(tuple(item.kernel_ns for item in samples)),
        release_ns=_median_values(tuple(item.release_ns for item in samples)),
        total_ns=_median_values(tuple(item.total_ns for item in samples)),
        upload_ns=_median_values(tuple(item.upload_ns for item in samples)),
        validation_plan_ns=_median_values(
            tuple(item.validation_plan_ns for item in samples)
        ),
    )


def _median_values(values: tuple[int, ...]) -> int:
    return int(median(values))


if __name__ == "__main__":
    raise SystemExit(main())
