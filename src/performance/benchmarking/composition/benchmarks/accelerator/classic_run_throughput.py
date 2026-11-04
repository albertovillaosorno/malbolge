# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
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
#   - Raw resident classic CUDA throughput samples across batch sizes.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Raw resident classic CUDA throughput samples across batch sizes."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from statistics import median, pstdev
from time import perf_counter_ns
from typing import TYPE_CHECKING, Final

from accelerator.cuda.classic_run import CudaClassicRunAdapter

from benchmarks.accelerator.classic_workload import (
    STEP_BUDGET,
    WORKLOAD_DESCRIPTION,
    classic_noop_request,
    validate_classic_noop_results,
)

if TYPE_CHECKING:
    from accelerator.classic_run import ClassicRunRequest

BATCH_SIZES: Final = (1, 8, 32, 128)
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


class ClassicThroughputReportError(ValueError):
    """Retained classic CUDA evidence could not be published."""


def _render_report(payload: object) -> str:
    """Corroborate public JSON against source-bound native encoding."""
    try:
        source = _SOURCE_JSON_ENCODER(indent=2, sort_keys=True).encode(payload)
        observed = json.dumps(payload, indent=2, sort_keys=True)
    except Exception as error:
        message = f"classic throughput JSON writer failed: {type(error).__name__}"
        raise ClassicThroughputReportError(message) from error
    if type(source) is not str or type(observed) is not str or observed != source:
        message = "classic throughput JSON writer differs from source"
        raise ClassicThroughputReportError(message)
    return source + "\n"


def _publish_report(record: str) -> None:
    """Reject incomplete native write acknowledgements and failed flushes."""
    try:
        written = sys.stdout.write(record)
    except Exception as error:
        message = f"classic throughput stdout write failed: {type(error).__name__}"
        raise ClassicThroughputReportError(message) from error
    if type(written) is not int or written != len(record):
        message = "classic throughput stdout write incomplete"
        raise ClassicThroughputReportError(message)
    try:
        flushed = sys.stdout.flush()
    except Exception as error:
        message = f"classic throughput stdout flush failed: {type(error).__name__}"
        raise ClassicThroughputReportError(message) from error
    if flushed is not None:
        message = "classic throughput stdout flush incomplete"
        raise ClassicThroughputReportError(message)


def main() -> int:
    """Measure resident CUDA batch throughput for an exact 64-step workload.

    Returns:
        Zero after emitting JSON to stdout.

    """
    request = classic_noop_request()
    with CudaClassicRunAdapter() as adapter:
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
        "rows": [asdict(row) for row in rows],
        "sample_count": SAMPLE_COUNT,
        "step_budget": STEP_BUDGET,
        "workload": WORKLOAD_DESCRIPTION,
    }
    _publish_report(_render_report(payload))
    return 0


def _measure(
    adapter: CudaClassicRunAdapter,
    request: ClassicRunRequest,
    batch_size: int,
) -> ThroughputRow:
    requests = (request,) * batch_size
    validate_classic_noop_results(adapter.evaluate(requests), batch_size)
    raw: list[int] = []
    for _ in range(SAMPLE_COUNT):
        start = perf_counter_ns()
        results = adapter.evaluate(requests)
        elapsed = perf_counter_ns() - start
        validate_classic_noop_results(results, batch_size)
        raw.append(elapsed)
    median_ns = int(median(raw))
    return ThroughputRow(
        batch_size=batch_size,
        items_per_second_at_median=(batch_size * 1_000_000_000) / median_ns,
        median_ns=median_ns,
        ns_per_item_at_median=median_ns / batch_size,
        pstdev_ns=pstdev(raw),
        raw_ns=tuple(raw),
        step_budget=STEP_BUDGET,
    )


if __name__ == "__main__":
    raise SystemExit(main())
