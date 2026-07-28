# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Raw post-preparation phase samples for identical CPU/CUDA search."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from hashlib import sha256
import json
from statistics import median
from statistics import pstdev
import sys
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
    from accelerator.cuda import CudaPreparedPrimitiveStats
    from accelerator.evaluated_search import EvaluatedSearchExecutionAdapter
    from accelerator.evaluated_search import PreparedEvaluatedSearch
    from accelerator.evaluated_search import PreparedSearchPhaseProfile
    from benchmarks.accelerator.search_workload import SearchBenchmarkWorkload

SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1
PHASE_NAMES: Final = (
    "prepared_validation_ns",
    "backend_evaluation_ns",
    "proposal_selection_ns",
    "result_validation_ns",
    "total_ns",
)


@dataclass(frozen=True, slots=True)
class PhaseTiming:
    """Raw and summary timing for one prepared-search phase."""

    max_ns: int
    median_ns: int
    min_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]


def main() -> int:
    """Measure post-preparation full-domain phases on CPU and CUDA.

    Returns:
        Zero after emitting retained-sample-ready JSON to stdout.

    """
    workload = full_domain_rotate_target_workload()
    cpu = cpu_rotate_target_search_adapter()
    prepared = cpu.prepare(workload.request)
    with CudaExactPrimitiveAdapter() as primitive:
        cuda = rotate_target_search_adapter(primitive)
        cpu_phases, cuda_phases = _measure_pair(
            cpu,
            cuda,
            prepared=prepared,
            workload=workload,
        )
        capability = primitive.capability()
        prepared_stats = primitive.prepared_stats()
        _validate_prepared_stats(prepared_stats)
    payload = {
        "benchmark_id": "rotate-target-prepared-search-phase-profile-v1",
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
            "preparation_timed": False,
            "sample_count": SAMPLE_COUNT,
            "warmup_count": WARMUP_COUNT,
        },
        "device": {
            "arch": capability.device_arch,
            "backend": capability.backend_id,
            "name": capability.device_name,
        },
        "cpu": {name: asdict(value) for name, value in cpu_phases.items()},
        "cuda": {name: asdict(value) for name, value in cuda_phases.items()},
        "cuda_prepared_session": asdict(prepared_stats),
        "prepared_membership_count": _validated_membership_count(
            cpu.prepared_membership_count(prepared)
        ),
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure_pair(
    cpu: EvaluatedSearchExecutionAdapter,
    cuda: EvaluatedSearchExecutionAdapter,
    *,
    prepared: PreparedEvaluatedSearch,
    workload: SearchBenchmarkWorkload,
) -> tuple[dict[str, PhaseTiming], dict[str, PhaseTiming]]:
    for _ in range(WARMUP_COUNT):
        _ = _profile(
            cpu,
            prepared=prepared,
            workload=workload,
            backend_id=CPU_BACKEND,
        )
        _ = _profile(
            cuda,
            prepared=prepared,
            workload=workload,
            backend_id=CUDA_BACKEND,
        )
    cpu_raw: dict[str, list[int]] = {name: [] for name in PHASE_NAMES}
    cuda_raw: dict[str, list[int]] = {name: [] for name in PHASE_NAMES}
    for _ in range(SAMPLE_COUNT):
        _append_profile(
            cpu_raw,
            _profile(
                cpu,
                prepared=prepared,
                workload=workload,
                backend_id=CPU_BACKEND,
            ),
        )
        _append_profile(
            cuda_raw,
            _profile(
                cuda,
                prepared=prepared,
                workload=workload,
                backend_id=CUDA_BACKEND,
            ),
        )
    return (
        {name: _timing(samples) for name, samples in cpu_raw.items()},
        {name: _timing(samples) for name, samples in cuda_raw.items()},
    )


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
        message = "prepared phase profile did not use one resident CUDA session"
        raise RuntimeError(message)


def _profile(
    adapter: EvaluatedSearchExecutionAdapter,
    *,
    prepared: PreparedEvaluatedSearch,
    workload: SearchBenchmarkWorkload,
    backend_id: str,
) -> PreparedSearchPhaseProfile:
    profiled = adapter.profile_prepared_search(prepared)
    _validate_profile(profiled.phases)
    validate_search_benchmark_result(
        profiled.result,
        backend_id,
        workload.verifier,
    )
    return profiled.phases


def _append_profile(
    raw: dict[str, list[int]],
    phases: PreparedSearchPhaseProfile,
) -> None:
    values = _phase_values(phases)
    for name in PHASE_NAMES:
        raw[name].append(values[name])


def _phase_values(
    phases: PreparedSearchPhaseProfile,
) -> dict[str, int]:
    return {
        "prepared_validation_ns": phases.prepared_validation_ns,
        "backend_evaluation_ns": phases.backend_evaluation_ns,
        "proposal_selection_ns": phases.proposal_selection_ns,
        "result_validation_ns": phases.result_validation_ns,
        "total_ns": phases.total_ns,
    }


def _validate_profile(phases: PreparedSearchPhaseProfile) -> None:
    measured = (
        phases.prepared_validation_ns,
        phases.backend_evaluation_ns,
        phases.proposal_selection_ns,
        phases.result_validation_ns,
    )
    if any(value < 0 for value in measured):
        message = "prepared search phase benchmark returned a negative duration"
        raise RuntimeError(message)
    if phases.total_ns < sum(measured):
        message = "prepared search phase total is smaller than named phases"
        raise RuntimeError(message)


def _timing(samples: list[int]) -> PhaseTiming:
    if len(samples) != SAMPLE_COUNT:
        message = "prepared search phase benchmark retained wrong sample count"
        raise RuntimeError(message)
    return PhaseTiming(
        max_ns=max(samples),
        median_ns=int(median(samples)),
        min_ns=min(samples),
        pstdev_ns=pstdev(samples),
        raw_ns=tuple(samples),
    )


if __name__ == "__main__":
    raise SystemExit(main())
