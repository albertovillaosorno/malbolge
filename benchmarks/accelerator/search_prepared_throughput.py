# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Ordinary-versus-prepared CPU/CUDA bounded-search throughput samples."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from hashlib import sha256
import json
from statistics import median
from statistics import pstdev
import sys
from time import perf_counter_ns
from typing import Final
from typing import TYPE_CHECKING

from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.exact_primitives import PrimitiveKind
from benchmarks.accelerator.search_workload import CORPUS_SIZE
from benchmarks.accelerator.search_workload import CPU_BACKEND
from benchmarks.accelerator.search_workload import CUDA_BACKEND
from benchmarks.accelerator.search_workload import SEED
from benchmarks.accelerator.search_workload import TARGET
from benchmarks.accelerator.search_workload import WORKLOAD_ID
from benchmarks.accelerator.search_workload import (
    full_domain_rotate_target_workload,
)
from benchmarks.accelerator.search_workload import (
    validate_search_benchmark_result,
)
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import cpu_rotate_target_search_adapter
from optimizer.rotate_target import rotate_target_search_adapter

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.cuda import CudaPreparedPrimitiveStats
    from accelerator.evaluated_search import EvaluatedSearchExecutionAdapter
    from accelerator.evaluated_search import PreparedEvaluatedSearch
    from accelerator.work_ports import SearchResult
    from benchmarks.accelerator.search_workload import SearchBenchmarkWorkload

SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1
CPU_ORDINARY: Final = "cpu-ordinary"
CPU_PREPARED: Final = "cpu-prepared"
CUDA_ORDINARY: Final = "cuda-ordinary"
CUDA_PREPARED: Final = "cuda-prepared"


@dataclass(frozen=True, slots=True)
class SearchTiming:
    """Raw and summary timing for one repeated-search execution route."""

    max_ns: int
    median_ns: int
    min_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]
    route_id: str


def main() -> int:
    """Measure ordinary and prepared full-domain search on CPU and CUDA.

    Returns:
        Zero after emitting retained-sample-ready JSON to stdout.

    """
    workload = full_domain_rotate_target_workload()
    cpu = cpu_rotate_target_search_adapter()
    prepared = cpu.prepare(workload.request)
    with CudaExactPrimitiveAdapter() as primitive:
        cuda = rotate_target_search_adapter(primitive)
        rows = _measure_routes(
            cpu,
            cuda,
            prepared=prepared,
            workload=workload,
        )
        capability = primitive.capability()
        prepared_stats = primitive.prepared_stats()
        _validate_prepared_stats(prepared_stats)
    by_route = {row.route_id: row for row in rows}
    payload = {
        "benchmark_id": "rotate-target-prepared-search-throughput-v1",
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
            "ordering": (
                "fixed interleaved CPU ordinary, CPU prepared, "
                "CUDA ordinary, CUDA prepared"
            ),
            "preparation_timed": False,
            "sample_count": SAMPLE_COUNT,
            "warmup_count": WARMUP_COUNT,
        },
        "device": {
            "arch": capability.device_arch,
            "backend": capability.backend_id,
            "name": capability.device_name,
        },
        "routes": {row.route_id: asdict(row) for row in rows},
        "cuda_prepared_session": asdict(prepared_stats),
        "prepared_membership_count": _validated_membership_count(
            cpu.prepared_membership_count(prepared)
        ),
        "speedups_at_median": {
            "cpu_prepared_over_ordinary": (
                by_route[CPU_ORDINARY].median_ns
                / by_route[CPU_PREPARED].median_ns
            ),
            "cuda_prepared_over_ordinary": (
                by_route[CUDA_ORDINARY].median_ns
                / by_route[CUDA_PREPARED].median_ns
            ),
            "cuda_prepared_over_cpu_prepared": (
                by_route[CPU_PREPARED].median_ns
                / by_route[CUDA_PREPARED].median_ns
            ),
        },
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure_routes(
    cpu: EvaluatedSearchExecutionAdapter,
    cuda: EvaluatedSearchExecutionAdapter,
    *,
    prepared: PreparedEvaluatedSearch,
    workload: SearchBenchmarkWorkload,
) -> tuple[SearchTiming, ...]:
    routes = (
        (
            CPU_ORDINARY,
            CPU_BACKEND,
            lambda: cpu.search(workload.request),
        ),
        (
            CPU_PREPARED,
            CPU_BACKEND,
            lambda: cpu.search_prepared(prepared),
        ),
        (
            CUDA_ORDINARY,
            CUDA_BACKEND,
            lambda: cuda.search(workload.request),
        ),
        (
            CUDA_PREPARED,
            CUDA_BACKEND,
            lambda: cuda.search_prepared(prepared),
        ),
    )
    for _ in range(WARMUP_COUNT):
        for _, backend_id, action in routes:
            validate_search_benchmark_result(
                action(),
                backend_id,
                workload.verifier,
            )
    raw: dict[str, list[int]] = {route_id: [] for route_id, _, _ in routes}
    for _ in range(SAMPLE_COUNT):
        for route_id, backend_id, action in routes:
            raw[route_id].append(
                _timed_search(
                    action,
                    backend_id,
                    workload,
                )
            )
    return tuple(_timing(route_id, raw[route_id]) for route_id in raw)


def _validated_membership_count(count: int) -> int:
    if count != CORPUS_SIZE:
        message = "prepared membership index does not cover full corpus"
        raise RuntimeError(message)
    return count


def _validate_prepared_stats(stats: CudaPreparedPrimitiveStats) -> None:
    expected_evaluations = WARMUP_COUNT + SAMPLE_COUNT
    observed = (
        stats.builds,
        stats.evaluations,
        stats.resident_count,
        stats.resident_kind,
        stats.reuses,
    )
    expected = (
        1,
        expected_evaluations,
        CORPUS_SIZE,
        PrimitiveKind.ROTATE,
        expected_evaluations - 1,
    )
    if observed != expected:
        message = "prepared throughput did not use one resident CUDA session"
        raise RuntimeError(message)


def _timed_search(
    action: Callable[[], SearchResult],
    backend_id: str,
    workload: SearchBenchmarkWorkload,
) -> int:
    start = perf_counter_ns()
    result = action()
    elapsed = perf_counter_ns() - start
    validate_search_benchmark_result(
        result,
        backend_id,
        workload.verifier,
    )
    return elapsed


def _timing(route_id: str, samples: list[int]) -> SearchTiming:
    if len(samples) != SAMPLE_COUNT:
        message = "prepared search benchmark retained the wrong sample count"
        raise RuntimeError(message)
    return SearchTiming(
        max_ns=max(samples),
        median_ns=int(median(samples)),
        min_ns=min(samples),
        pstdev_ns=pstdev(samples),
        raw_ns=tuple(samples),
        route_id=route_id,
    )


if __name__ == "__main__":
    raise SystemExit(main())
