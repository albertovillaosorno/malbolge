# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""CPU-versus-CUDA throughput samples for one identical bounded search."""

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
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import ROTATE_HIGH_TRIT_WEIGHT
from accelerator.primitive_candidates import encode_rotate_candidate
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import admit_search_result
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import RotateTargetProblem
from optimizer.rotate_target import RotateTargetVerifier
from optimizer.rotate_target import cpu_rotate_target_search_adapter
from optimizer.rotate_target import rotate_target_search_adapter

if TYPE_CHECKING:
    from accelerator.work_ports import SearchExecutionAdapter
    from accelerator.work_ports import SearchResult

SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1
SEED: Final = 17
CORPUS_SIZE: Final = MAX_WORD + 1
TARGET: Final = ROTATE_HIGH_TRIT_WEIGHT
WORKLOAD_ID: Final = "classic-rotate-target-full-domain-v1"
CPU_BACKEND: Final = "cpu-reference"
CUDA_BACKEND: Final = "cuda"
EXPECTED_PROPOSALS: Final = (
    CandidateProposal(
        logical_id="corpus-1", payload=encode_rotate_candidate(1)
    ),
)


@dataclass(frozen=True, slots=True)
class SearchTiming:
    """Raw and summary timing for one search execution backend."""

    backend_id: str
    max_ns: int
    median_ns: int
    min_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]


def main() -> int:
    """Measure identical full-domain rotate-target search on CPU and CUDA.

    Returns:
        Zero after emitting retained-sample-ready JSON to stdout.

    """
    problem = RotateTargetProblem(
        target=TARGET,
        candidates=tuple(range(CORPUS_SIZE)),
    ).encode()
    request = SearchRequest(
        algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
        evaluation_budget=CORPUS_SIZE,
        problem=problem,
        seed=SEED,
    ).validated()
    verifier = RotateTargetVerifier(TARGET)
    cpu = cpu_rotate_target_search_adapter()
    with CudaExactPrimitiveAdapter() as primitive:
        cuda = rotate_target_search_adapter(primitive)
        cpu_timing, cuda_timing = _measure_pair(
            cpu,
            cuda,
            request,
            verifier=verifier,
        )
        capability = primitive.capability()
    payload = {
        "benchmark_id": "rotate-target-search-cpu-vs-cuda-v1",
        "workload": {
            "algorithm_id": ROTATE_TARGET_ALGORITHM_ID,
            "corpus_size": CORPUS_SIZE,
            "evaluation_budget": CORPUS_SIZE,
            "identity": WORKLOAD_ID,
            "problem_sha256": sha256(problem).hexdigest(),
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
        "cuda_speedup_at_median": (
            cpu_timing.median_ns / cuda_timing.median_ns
        ),
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure_pair(
    cpu: SearchExecutionAdapter,
    cuda: SearchExecutionAdapter,
    request: SearchRequest,
    *,
    verifier: RotateTargetVerifier,
) -> tuple[SearchTiming, SearchTiming]:
    for _ in range(WARMUP_COUNT):
        _validate_result(cpu.search(request), CPU_BACKEND, verifier)
        _validate_result(cuda.search(request), CUDA_BACKEND, verifier)
    cpu_raw: list[int] = []
    cuda_raw: list[int] = []
    for _ in range(SAMPLE_COUNT):
        cpu_raw.append(
            _timed_search(cpu, request, CPU_BACKEND, verifier=verifier)
        )
        cuda_raw.append(
            _timed_search(cuda, request, CUDA_BACKEND, verifier=verifier)
        )
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
    _validate_result(result, backend_id, verifier)
    return elapsed


def _validate_result(
    result: SearchResult,
    backend_id: str,
    verifier: RotateTargetVerifier,
) -> None:
    if result.capability.backend_id != backend_id:
        message = "search benchmark executed an unexpected backend"
        raise RuntimeError(message)
    if result.proposals != EXPECTED_PROPOSALS:
        message = "search benchmark changed exact proposal identity"
        raise RuntimeError(message)
    if admit_search_result(result, verifier) != EXPECTED_PROPOSALS:
        message = "search benchmark proposal failed independent CPU admission"
        raise RuntimeError(message)


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
