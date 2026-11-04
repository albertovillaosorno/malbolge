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
#   - CPU-versus-CUDA throughput samples for one identical bounded search.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""CPU-versus-CUDA throughput samples for one identical bounded search."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from hashlib import sha256
from statistics import median, pstdev
from time import perf_counter_ns
from typing import TYPE_CHECKING, Final

from accelerator.cuda import CudaExactPrimitiveAdapter
from optimizer.rotate_target import (
    ROTATE_TARGET_ALGORITHM_ID,
    cpu_rotate_target_search_adapter,
    rotate_target_search_adapter,
)

from benchmarks.accelerator.search_workload import (
    CORPUS_SIZE,
    CPU_BACKEND,
    CUDA_BACKEND,
    SEED,
    TARGET,
    WORKLOAD_ID,
    full_domain_rotate_target_workload,
    validate_search_benchmark_result,
)

if TYPE_CHECKING:
    from accelerator.work_ports import SearchExecutionAdapter, SearchRequest
    from optimizer.rotate_target import RotateTargetVerifier

SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1
_SOURCE_JSON_ENCODER: Final = json.JSONEncoder


@dataclass(frozen=True, slots=True)
class SearchTiming:
    """Raw and summary timing for one search execution backend."""

    backend_id: str
    max_ns: int
    median_ns: int
    min_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]


class SearchThroughputReportError(ValueError):
    """Retained CPU/CUDA search evidence could not be published."""


def _render_report(payload: object) -> str:
    """Compare public search JSON to source-bound native encoding."""
    try:
        source = _SOURCE_JSON_ENCODER(indent=2, sort_keys=True).encode(payload)
        observed = json.dumps(payload, indent=2, sort_keys=True)
    except Exception as error:
        message = f"search throughput JSON writer failed: {type(error).__name__}"
        raise SearchThroughputReportError(message) from error
    if type(source) is not str or type(observed) is not str or observed != source:
        message = "search throughput JSON writer differs from source"
        raise SearchThroughputReportError(message)
    return source + "\n"


def _publish_report(record: str) -> None:
    """Reject incomplete native write and nonvoid flush acknowledgements."""
    try:
        written = sys.stdout.write(record)
    except Exception as error:
        message = f"search throughput stdout write failed: {type(error).__name__}"
        raise SearchThroughputReportError(message) from error
    if type(written) is not int or written != len(record):
        message = "search throughput stdout write incomplete"
        raise SearchThroughputReportError(message)
    try:
        flushed = sys.stdout.flush()
    except Exception as error:
        message = f"search throughput stdout flush failed: {type(error).__name__}"
        raise SearchThroughputReportError(message) from error
    if flushed is not None:
        message = "search throughput stdout flush incomplete"
        raise SearchThroughputReportError(message)


def main() -> int:
    """Measure identical full-domain rotate-target search on CPU and CUDA.

    Returns:
        Zero after emitting retained-sample-ready JSON to stdout.

    """
    workload = full_domain_rotate_target_workload()
    cpu = cpu_rotate_target_search_adapter()
    with CudaExactPrimitiveAdapter() as primitive:
        cuda = rotate_target_search_adapter(primitive)
        cpu_timing, cuda_timing = _measure_pair(
            cpu,
            cuda,
            workload.request,
            verifier=workload.verifier,
        )
        capability = primitive.capability()
    payload = {
        "benchmark_id": "rotate-target-search-cpu-vs-cuda-v1",
        "workload": {
            "algorithm_id": ROTATE_TARGET_ALGORITHM_ID,
            "corpus_size": CORPUS_SIZE,
            "evaluation_budget": CORPUS_SIZE,
            "identity": WORKLOAD_ID,
            "problem_sha256": sha256(workload.problem).hexdigest(),
            "seed": SEED,
            "target": TARGET,
        },
        "measurement": {
            "adapter_setup_timed": False,
            "ordering": "fixed interleaved CPU then CUDA",
            "sample_count": SAMPLE_COUNT,
            "warmup_count": WARMUP_COUNT,
        },
        "device": {
            "arch": capability.device_arch,
            "backend": capability.backend_id,
            "name": capability.device_name,
        },
        "cpu": asdict(cpu_timing),
        "cuda": asdict(cuda_timing),
        "cuda_speedup_at_median": (cpu_timing.median_ns / cuda_timing.median_ns),
    }
    _publish_report(_render_report(payload))
    return 0


def _measure_pair(
    cpu: SearchExecutionAdapter,
    cuda: SearchExecutionAdapter,
    request: SearchRequest,
    *,
    verifier: RotateTargetVerifier,
) -> tuple[SearchTiming, SearchTiming]:
    for _ in range(WARMUP_COUNT):
        validate_search_benchmark_result(
            cpu.search(request),
            CPU_BACKEND,
            verifier,
        )
        validate_search_benchmark_result(
            cuda.search(request),
            CUDA_BACKEND,
            verifier,
        )
    cpu_raw: list[int] = []
    cuda_raw: list[int] = []
    for _ in range(SAMPLE_COUNT):
        cpu_raw.append(_timed_search(cpu, request, CPU_BACKEND, verifier=verifier))
        cuda_raw.append(_timed_search(cuda, request, CUDA_BACKEND, verifier=verifier))
    return (
        _timing(CPU_BACKEND, cpu_raw),
        _timing(CUDA_BACKEND, cuda_raw),
    )


def _timed_search(
    adapter: SearchExecutionAdapter,
    request: SearchRequest,
    backend_id: str,
    *,
    verifier: RotateTargetVerifier,
) -> int:
    start = perf_counter_ns()
    result = adapter.search(request)
    elapsed = perf_counter_ns() - start
    validate_search_benchmark_result(result, backend_id, verifier)
    return elapsed


def _timing(backend_id: str, samples: list[int]) -> SearchTiming:
    if len(samples) != SAMPLE_COUNT:
        message = "search benchmark retained the wrong sample count"
        raise RuntimeError(message)
    return SearchTiming(
        backend_id=backend_id,
        max_ns=max(samples),
        median_ns=int(median(samples)),
        min_ns=min(samples),
        pstdev_ns=pstdev(samples),
        raw_ns=tuple(samples),
    )


if __name__ == "__main__":
    raise SystemExit(main())
