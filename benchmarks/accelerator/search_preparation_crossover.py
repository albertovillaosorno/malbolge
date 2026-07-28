# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Prepared-search setup, memory, and reuse-crossover benchmark."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import gc
from hashlib import sha256
import json
import os
from pathlib import Path
from statistics import median
from statistics import pstdev
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
from time import perf_counter_ns
import tracemalloc
from typing import Final
from typing import TYPE_CHECKING

from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.evaluated_search import prepared_membership_index_id
from accelerator.exact_primitives import PrimitiveKind
from accelerator.primitive_candidates import encode_rotate_candidate
from accelerator.primitive_candidates import packed_primitive_validation_id
from accelerator.primitive_candidates import prepared_primitive_validation_id
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import admit_search_result
from benchmarks.accelerator.search_workload import CORPUS_SIZE
from benchmarks.accelerator.search_workload import CUDA_BACKEND
from benchmarks.accelerator.search_workload import SEED
from benchmarks.accelerator.search_workload import TARGET
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import RotateTargetProblem
from optimizer.rotate_target import RotateTargetVerifier
from optimizer.rotate_target import cpu_rotate_target_search_adapter
from optimizer.rotate_target import rotate_target_search_adapter

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.cuda import CudaPreparedPrimitiveStats
    from accelerator.evaluated_search import EvaluatedSearchExecutionAdapter
    from accelerator.evaluated_search import PreparedEvaluatedSearch
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.work_ports import SearchResult

SAMPLE_COUNT: Final = 15
MEMORY_SAMPLE_COUNT: Final = 5
WARMUP_COUNT: Final = 1
CORPUS_SIZES: Final = (1, 64, 1_024, CORPUS_SIZE)
WORD_BYTES: Final = 4
COLD_CHILD_ARGUMENT_COUNT: Final = 2
ORDINARY_VALIDATION_ID: Final = "u32le-broadword-domain-v1"
PREPARED_VALIDATION_ID: Final = "cpu-reference-packed-equality-v1"
MEMBERSHIP_INDEX_ID: Final = (
    "identity-sorted-candidate-reference-binary-search-v1"
)
COLD_CHILD_FLAG: Final = "--cold-child"
MODULE_NAME: Final = "benchmarks.accelerator.search_preparation_crossover"
REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class Timing:
    """Raw and summary nanosecond observations."""

    max_ns: int
    median_ns: int
    min_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ByteTiming:
    """Raw and summary byte-count observations."""

    max_bytes: int
    median_bytes: int
    min_bytes: int
    pstdev_bytes: float
    raw_bytes: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MemoryMeasurement:
    """Incremental traced-memory observations for one prepared request."""

    peak: ByteTiming
    retained: ByteTiming


@dataclass(frozen=True, slots=True)
class Crossover:
    """Strict ordinary-versus-prepared amortization result."""

    cold_runs: int | None
    warm_runs: int | None


@dataclass(frozen=True, slots=True)
class ScaleWorkload:
    """Canonical scale workload with exact expected proposal identity."""

    expected: tuple[CandidateProposal, ...]
    problem: bytes
    request: SearchRequest
    verifier: RotateTargetVerifier


@dataclass(frozen=True, slots=True)
class _CudaTimings:
    capability: AcceleratorCapability
    first_build: Timing
    ordinary: Timing
    reuse: Timing
    reuse_stats: CudaPreparedPrimitiveStats


@dataclass(frozen=True, slots=True)
class ScaleMeasurement:
    """Complete preparation and execution economics for one corpus size."""

    cold_prepare: Timing
    corpus_size: int
    crossover: Crossover
    cuda: _CudaTimings
    cuda_device_bytes: int
    cuda_host_output_bytes: int
    memory: MemoryMeasurement
    membership_count: int
    problem_sha256: str
    reference_bytes: int
    reference_word_count: int
    selection_count: int
    warm_prepare: Timing


def main(argv: list[str] | None = None) -> int:
    """Measure preparation economics or execute one cold child sample.

    Returns:
        Zero after writing deterministic JSON or one child duration.

    Raises:
        ValueError: If command-line arguments are malformed.

    """
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == COLD_CHILD_FLAG:
        return _cold_child(arguments)
    if arguments:
        message = "unexpected search preparation crossover arguments"
        raise ValueError(message)
    measurements = tuple(_measure_size(size) for size in CORPUS_SIZES)
    capability = measurements[-1].cuda.capability
    payload = {
        "benchmark_id": "rotate-target-preparation-crossover-v1",
        "measurement": {
            "adapter_setup_timed": False,
            "cold_process_per_sample": True,
            "crossover_formula": (
                "prepare + first_build + (runs - 1) * reuse < runs * ordinary"
            ),
            "fresh_build_scope": (
                "resident allocate/upload plus one exact search; "
                "adapter and NVRTC setup excluded"
            ),
            "memory_sample_count": MEMORY_SAMPLE_COUNT,
            "memory_scope": (
                "incremental tracemalloc allocations with workload and "
                "global rotate table outside tracing; CUDA/native excluded"
            ),
            "ordering": (
                "ascending corpus size; cold, warm, memory, ordinary/reuse, "
                "fresh build"
            ),
            "result_validation_timed": False,
            "sample_count": SAMPLE_COUNT,
            "warmup_count": WARMUP_COUNT,
            "warm_prepare_scope": "global rotate table prewarmed",
            "workload_build_timed": False,
        },
        "device": {
            "arch": capability.device_arch,
            "backend": capability.backend_id,
            "name": capability.device_name,
        },
        "proof": {
            "membership_index_id": _membership_index_id(),
            "ordinary_validation_id": _ordinary_validation_id(),
            "prepared_validation_id": _prepared_validation_id(),
            "strict_crossover": True,
        },
        "scales": [asdict(item) for item in measurements],
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure_size(size: int) -> ScaleMeasurement:
    workload = build_scale_workload(size)
    cold_prepare = _cold_prepare_timing(size)
    cpu = cpu_rotate_target_search_adapter()
    warm_prepare = _warm_prepare_timing(cpu, workload, size)
    memory = _memory_measurement(cpu, workload)
    prepared = cpu.prepare(workload.request)
    proofs = validate_prepared_scale(cpu, prepared, size)
    cuda = _cuda_timings(workload, prepared, size)
    crossover = Crossover(
        cold_runs=preparation_crossover_runs(
            preparation_ns=cold_prepare.median_ns,
            first_build_ns=cuda.first_build.median_ns,
            reuse_ns=cuda.reuse.median_ns,
            ordinary_ns=cuda.ordinary.median_ns,
        ),
        warm_runs=preparation_crossover_runs(
            preparation_ns=warm_prepare.median_ns,
            first_build_ns=cuda.first_build.median_ns,
            reuse_ns=cuda.reuse.median_ns,
            ordinary_ns=cuda.ordinary.median_ns,
        ),
    )
    return ScaleMeasurement(
        cold_prepare=cold_prepare,
        corpus_size=size,
        crossover=crossover,
        cuda=cuda,
        cuda_device_bytes=size * WORD_BYTES * 2,
        cuda_host_output_bytes=size * WORD_BYTES,
        memory=memory,
        membership_count=proofs[1],
        problem_sha256=sha256(workload.problem).hexdigest(),
        reference_bytes=size * WORD_BYTES,
        reference_word_count=proofs[0],
        selection_count=proofs[2],
        warm_prepare=warm_prepare,
    )


def build_scale_workload(size: int) -> ScaleWorkload:
    """Build one canonical preparation-crossover workload.

    Returns:
        Problem, request, verifier, and expected exact proposal.

    Raises:
        ValueError: If ``size`` is outside the preregistered scale set.

    """
    if size not in CORPUS_SIZES:
        message = "unsupported preparation-crossover corpus size"
        raise ValueError(message)
    candidates = (1,) if size == 1 else tuple(range(size))
    problem = RotateTargetProblem(
        target=TARGET,
        candidates=candidates,
    ).encode()
    request = SearchRequest(
        algorithm_id=ROTATE_TARGET_ALGORITHM_ID,
        evaluation_budget=size,
        problem=problem,
        seed=SEED,
    ).validated()
    logical_id = "corpus-0" if size == 1 else "corpus-1"
    expected = (
        CandidateProposal(
            logical_id=logical_id,
            payload=encode_rotate_candidate(1),
        ),
    )
    return ScaleWorkload(
        expected=expected,
        problem=problem,
        request=request,
        verifier=RotateTargetVerifier(TARGET),
    )


def _cold_child(arguments: list[str]) -> int:
    if len(arguments) != COLD_CHILD_ARGUMENT_COUNT:
        message = "cold child requires exactly one corpus size"
        raise ValueError(message)
    size = int(arguments[1])
    workload = build_scale_workload(size)
    adapter = cpu_rotate_target_search_adapter()
    start = perf_counter_ns()
    prepared = adapter.prepare(workload.request)
    elapsed = perf_counter_ns() - start
    _ = validate_prepared_scale(adapter, prepared, size)
    _ = sys.stdout.write(f"{elapsed}\n")
    return 0


def _cold_prepare_timing(size: int) -> Timing:
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = "0"
    samples: list[int] = []
    for _ in range(SAMPLE_COUNT):
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [sys.executable, "-m", MODULE_NAME, COLD_CHILD_FLAG, str(size)],
            cwd=REPOSITORY_ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        samples.append(int(completed.stdout.strip()))
    return _timing(samples, SAMPLE_COUNT)


def _warm_prepare_timing(
    adapter: EvaluatedSearchExecutionAdapter,
    workload: ScaleWorkload,
    size: int,
) -> Timing:
    warm = adapter.prepare(workload.request)
    _ = validate_prepared_scale(adapter, warm, size)
    del warm
    samples: list[int] = []
    for _ in range(SAMPLE_COUNT):
        _ = gc.collect()
        start = perf_counter_ns()
        prepared = adapter.prepare(workload.request)
        samples.append(perf_counter_ns() - start)
        _ = validate_prepared_scale(
            adapter,
            prepared,
            len(prepared.batch.items),
        )
        del prepared
    return _timing(samples, SAMPLE_COUNT)


def _memory_measurement(
    adapter: EvaluatedSearchExecutionAdapter,
    workload: ScaleWorkload,
) -> MemoryMeasurement:
    retained_samples: list[int] = []
    peak_samples: list[int] = []
    for _ in range(MEMORY_SAMPLE_COUNT):
        _ = gc.collect()
        tracemalloc.start()
        before, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        prepared = adapter.prepare(workload.request)
        current, peak = tracemalloc.get_traced_memory()
        _ = validate_prepared_scale(
            adapter,
            prepared,
            len(prepared.batch.items),
        )
        retained_samples.append(max(0, current - before))
        peak_samples.append(max(0, peak - before))
        tracemalloc.stop()
        del prepared
    return MemoryMeasurement(
        peak=_byte_timing(peak_samples, MEMORY_SAMPLE_COUNT),
        retained=_byte_timing(retained_samples, MEMORY_SAMPLE_COUNT),
    )


def _cuda_timings(
    workload: ScaleWorkload,
    prepared: PreparedEvaluatedSearch,
    size: int,
) -> _CudaTimings:
    with CudaExactPrimitiveAdapter() as primitive:
        ordinary = rotate_target_search_adapter(primitive)
        reuse = rotate_target_search_adapter(primitive)
        _validate_result(ordinary.search(workload.request), workload)
        _validate_result(reuse.search_prepared(prepared), workload)
        _validate_result(reuse.search_prepared(prepared), workload)
        ordinary_samples: list[int] = []
        reuse_samples: list[int] = []
        for _ in range(SAMPLE_COUNT):
            ordinary_samples.append(
                _timed_result(
                    lambda: ordinary.search(workload.request),
                    workload,
                )
            )
            reuse_samples.append(
                _timed_result(lambda: reuse.search_prepared(prepared), workload)
            )
        reuse_stats = primitive.prepared_stats()
        capability = primitive.capability()
        _validate_reuse_stats(reuse_stats, size)
    first_samples = [
        _fresh_build_sample(workload, prepared, size)
        for _ in range(SAMPLE_COUNT)
    ]
    return _CudaTimings(
        capability=capability,
        first_build=_timing(first_samples, SAMPLE_COUNT),
        ordinary=_timing(ordinary_samples, SAMPLE_COUNT),
        reuse=_timing(reuse_samples, SAMPLE_COUNT),
        reuse_stats=reuse_stats,
    )


def _fresh_build_sample(
    workload: ScaleWorkload,
    prepared: PreparedEvaluatedSearch,
    size: int,
) -> int:
    with CudaExactPrimitiveAdapter() as primitive:
        adapter = rotate_target_search_adapter(primitive)
        elapsed = _timed_result(
            lambda: adapter.search_prepared(prepared),
            workload,
        )
        _validate_fresh_stats(primitive.prepared_stats(), size)
        return elapsed


def _timed_result(
    action: Callable[[], SearchResult],
    workload: ScaleWorkload,
) -> int:
    start = perf_counter_ns()
    result = action()
    elapsed = perf_counter_ns() - start
    _validate_result(result, workload)
    return elapsed


def _validate_result(result: SearchResult, workload: ScaleWorkload) -> None:
    if result.capability.backend_id != CUDA_BACKEND:
        message = "preparation crossover executed an unexpected backend"
        raise RuntimeError(message)
    if result.proposals != workload.expected:
        message = "preparation crossover changed exact proposal identity"
        raise RuntimeError(message)
    if admit_search_result(result, workload.verifier) != workload.expected:
        message = "preparation crossover proposal failed trusted admission"
        raise RuntimeError(message)


def validate_prepared_scale(
    adapter: EvaluatedSearchExecutionAdapter,
    prepared: PreparedEvaluatedSearch,
    size: int,
) -> tuple[int, int, int]:
    """Validate reference, membership, and selector cardinality.

    Returns:
        Exact proof counts in reference, membership, selector order.

    Raises:
        RuntimeError: If any prepared proof count differs from ``size``.

    """
    observed = (
        adapter.prepared_candidate_state_count(prepared),
        adapter.prepared_membership_count(prepared),
        adapter.prepared_selection_count(prepared),
    )
    expected = (size, size, 1)
    if observed != expected:
        message = "prepared crossover state proof counts drifted"
        raise RuntimeError(message)
    return observed


def _validate_reuse_stats(
    stats: CudaPreparedPrimitiveStats,
    size: int,
) -> None:
    expected_evaluations = 2 + SAMPLE_COUNT
    observed = (
        stats.builds,
        stats.evaluations,
        stats.packed_evaluations,
        stats.resident_count,
        stats.resident_kind,
        stats.reuses,
    )
    expected = (
        1,
        expected_evaluations,
        expected_evaluations,
        size,
        PrimitiveKind.ROTATE,
        expected_evaluations - 1,
    )
    if observed != expected:
        message = "prepared crossover reuse-session proof drifted"
        raise RuntimeError(message)


def _validate_fresh_stats(
    stats: CudaPreparedPrimitiveStats,
    size: int,
) -> None:
    observed = (
        stats.builds,
        stats.evaluations,
        stats.packed_evaluations,
        stats.resident_count,
        stats.resident_kind,
        stats.reuses,
    )
    expected = (1, 1, 1, size, PrimitiveKind.ROTATE, 0)
    if observed != expected:
        message = "prepared crossover fresh-session proof drifted"
        raise RuntimeError(message)


def preparation_crossover_runs(
    *,
    preparation_ns: int,
    first_build_ns: int,
    reuse_ns: int,
    ordinary_ns: int,
) -> int | None:
    """Return first run count where prepared total is strictly lower.

    Returns:
        Positive crossover run count, or ``None`` without per-run savings.

    """
    savings_per_reuse = ordinary_ns - reuse_ns
    if savings_per_reuse <= 0:
        return None
    fixed_cost = preparation_ns + first_build_ns - reuse_ns
    if fixed_cost < 0:
        return 1
    return (fixed_cost // savings_per_reuse) + 1


def _byte_timing(samples: list[int], expected_count: int) -> ByteTiming:
    if len(samples) != expected_count:
        message = "preparation crossover retained the wrong memory sample count"
        raise RuntimeError(message)
    return ByteTiming(
        max_bytes=max(samples),
        median_bytes=int(median(samples)),
        min_bytes=min(samples),
        pstdev_bytes=pstdev(samples),
        raw_bytes=tuple(samples),
    )


def _timing(samples: list[int], expected_count: int) -> Timing:
    if len(samples) != expected_count:
        message = "preparation crossover retained the wrong sample count"
        raise RuntimeError(message)
    return Timing(
        max_ns=max(samples),
        median_ns=int(median(samples)),
        min_ns=min(samples),
        pstdev_ns=pstdev(samples),
        raw_ns=tuple(samples),
    )


def _membership_index_id() -> str:
    identifier = prepared_membership_index_id()
    if identifier != MEMBERSHIP_INDEX_ID:
        message = "prepared membership index identity drifted"
        raise RuntimeError(message)
    return identifier


def _ordinary_validation_id() -> str:
    identifier = packed_primitive_validation_id()
    if identifier != ORDINARY_VALIDATION_ID:
        message = "ordinary prepared-crossover validator identity drifted"
        raise RuntimeError(message)
    return identifier


def _prepared_validation_id() -> str:
    identifier = prepared_primitive_validation_id()
    if identifier != PREPARED_VALIDATION_ID:
        message = "prepared crossover validator identity drifted"
        raise RuntimeError(message)
    return identifier


if __name__ == "__main__":
    raise SystemExit(main())
