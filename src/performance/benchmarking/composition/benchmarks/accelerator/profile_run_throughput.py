# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
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

"""End-to-end resident current-profile CUDA throughput samples."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from statistics import median, pstdev
from time import perf_counter_ns
from typing import TYPE_CHECKING, Final

from accelerator.cuda.profile_run import CudaProfileRunAdapter

from benchmarks.accelerator.profile_workload import (
    GEOMETRY,
    PROFILE_TRITS,
    PROFILE_WORDS,
    STEP_BUDGET,
    WORD_BYTES,
    WORKLOAD_DESCRIPTION,
    profile_noop_request,
    validate_profile_noop_results,
)

if TYPE_CHECKING:
    from accelerator.profile_run import ProfileRunRequest

BATCH_SIZES: Final = (1, 2, 4, 8, 16, 32)
SAMPLE_COUNT: Final = 15
_SOURCE_JSON_ENCODER: Final = json.JSONEncoder


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


class ProfileRunReportError(ValueError):
    """Retained CUDA throughput evidence could not be published."""


def _render_report(payload: object) -> str:
    """Compare public JSON to source-bound native evidence serialization."""
    try:
        source = _SOURCE_JSON_ENCODER(indent=2, sort_keys=True).encode(payload)
        observed = json.dumps(payload, indent=2, sort_keys=True)
    except Exception as error:
        message = f"profile run JSON writer failed: {type(error).__name__}"
        raise ProfileRunReportError(message) from error
    if type(source) is not str or type(observed) is not str or observed != source:
        message = "profile run JSON writer differs from source"
        raise ProfileRunReportError(message)
    return source + "\n"


def _publish_report(record: str) -> None:
    """Require the native exact stdout write receipt and successful flush."""
    try:
        written = sys.stdout.write(record)
    except Exception as error:
        message = f"profile run stdout write failed: {type(error).__name__}"
        raise ProfileRunReportError(message) from error
    if type(written) is not int or written != len(record):
        message = "profile run stdout write incomplete"
        raise ProfileRunReportError(message)
    try:
        flushed = sys.stdout.flush()
    except Exception as error:
        message = f"profile run stdout flush failed: {type(error).__name__}"
        raise ProfileRunReportError(message) from error
    if flushed is not None:
        message = "profile run stdout flush incomplete"
        raise ProfileRunReportError(message)


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
    _publish_report(_render_report(payload))
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
