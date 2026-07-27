# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Raw resident classic CUDA throughput samples across batch sizes."""

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

from accelerator.classic_run import ClassicRunRequest
from accelerator.classic_run import MEMORY_WORDS
from accelerator.classic_run import RunStatus
from accelerator.classic_step import StepTermination
from accelerator.cuda.classic_run import CudaClassicRunAdapter
from accelerator.cuda.classic_step import XLAT1

if TYPE_CHECKING:
    from accelerator.classic_run import ClassicRunResult

BATCH_SIZES: Final = (1, 8, 32, 128)
NOOP_DECODED: Final = ord("+")
SAMPLE_COUNT: Final = 15
STEP_BUDGET: Final = 64


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


def main() -> int:
    """Measure resident CUDA batch throughput for an exact 64-step workload.

    Returns:
        Zero after emitting JSON to stdout.

    """
    request = _request()
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
        "workload": "64 committed no-op transitions per classic VM",
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure(
    adapter: CudaClassicRunAdapter,
    request: ClassicRunRequest,
    batch_size: int,
) -> ThroughputRow:
    requests = (request,) * batch_size
    _validate_results(adapter.evaluate(requests), batch_size)
    raw: list[int] = []
    for _ in range(SAMPLE_COUNT):
        start = perf_counter_ns()
        results = adapter.evaluate(requests)
        elapsed = perf_counter_ns() - start
        _validate_results(results, batch_size)
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


def _request() -> ClassicRunRequest:
    return ClassicRunRequest(
        accumulator=0,
        code_pointer=0,
        data_pointer=0,
        input_bytes=(),
        input_consumed=0,
        memory=_noop_memory(),
        output_bytes=(),
        step_budget=STEP_BUDGET,
        termination=StepTermination.NONE,
    ).validated()


def _noop_memory() -> tuple[int, ...]:
    try:
        target_index = XLAT1.index(NOOP_DECODED)
    except ValueError as error:
        message = "reviewed XLAT1 table has no benchmark no-op decode"
        raise RuntimeError(message) from error
    words = [0] * MEMORY_WORDS
    for code_pointer in range(STEP_BUDGET):
        encoded_index = (target_index - code_pointer) % len(XLAT1)
        words[code_pointer] = 33 + encoded_index
    return tuple(words)


def _validate_results(
    results: tuple[ClassicRunResult, ...],
    expected_count: int,
) -> None:
    if len(results) != expected_count:
        message = "CUDA throughput batch returned wrong result count"
        raise RuntimeError(message)
    for result in results:
        _validate_result(result)


def _validate_result(result: ClassicRunResult) -> None:
    if result.status != RunStatus.BUDGET_EXHAUSTED:
        message = "CUDA throughput workload terminated unexpectedly"
        raise RuntimeError(message)
    if result.steps != STEP_BUDGET:
        message = "CUDA throughput workload executed wrong step count"
        raise RuntimeError(message)
    if result.termination != StepTermination.NONE:
        message = "CUDA throughput workload gained unexpected termination"
        raise RuntimeError(message)


if __name__ == "__main__":
    raise SystemExit(main())
