# File:
#   - search_prepared_phase_profile.py
# Path:
#   - benchmarks/accelerator/search_prepared_phase_profile.py
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
#   - Raw post-preparation phase samples for identical CPU/CUDA search.
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

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.exact_primitives import PrimitiveKind
from accelerator.primitive_candidates import packed_primitive_validation_id
from accelerator.primitive_candidates import prepared_primitive_validation_id
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
from optimizer.rotate_target import rotate_target_search_adapter

if TYPE_CHECKING:
    from accelerator.cpu import CpuPreparedPrimitiveStats
    from accelerator.cuda import CudaPreparedPrimitiveStats
    from accelerator.evaluated_search import EvaluatedSearchExecutionAdapter
    from accelerator.evaluated_search import PreparedEvaluatedSearch
    from accelerator.evaluated_search import PreparedSearchPhaseProfile
    from accelerator.exact_primitives import AcceleratorCapability
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


@dataclass(frozen=True, slots=True)
class _MeasuredPhases:
    capability: AcceleratorCapability
    cpu: dict[str, PhaseTiming]
    cpu_stats: CpuPreparedPrimitiveStats
    cuda: dict[str, PhaseTiming]
    cuda_stats: CudaPreparedPrimitiveStats
    membership_count: int
    reference_word_count: int
    selection_count: int


def main() -> int:
    """Measure post-preparation full-domain phases on CPU and CUDA.

    Returns:
        Zero after emitting retained-sample-ready JSON to stdout.

    """
    workload = full_domain_rotate_target_workload()
    measured = _measure_phases(workload)
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
            "arch": measured.capability.device_arch,
            "backend": measured.capability.backend_id,
            "name": measured.capability.device_name,
        },
        "cpu": {name: asdict(value) for name, value in measured.cpu.items()},
        "cuda": {name: asdict(value) for name, value in measured.cuda.items()},
        "cpu_prepared_rotate": asdict(measured.cpu_stats),
        "cuda_prepared_session": asdict(measured.cuda_stats),
        "prepared_membership_count": measured.membership_count,
        "prepared_selection_count": measured.selection_count,
        "ordinary_packed_validation": _validated_packed_validation_id(
            packed_primitive_validation_id()
        ),
        "prepared_primitive_validation": _validated_prepared_validation_id(
            prepared_primitive_validation_id()
        ),
        "prepared_reference_word_count": measured.reference_word_count,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure_phases(workload: SearchBenchmarkWorkload) -> _MeasuredPhases:
    cpu_primitive = CpuExactPrimitiveAdapter()
    cpu = rotate_target_search_adapter(cpu_primitive)
    prepared = cpu.prepare(workload.request)
    with CudaExactPrimitiveAdapter() as primitive:
        cuda = rotate_target_search_adapter(primitive)
        cpu_phases, cuda_phases = _measure_pair(
            cpu,
            cuda,
            prepared=prepared,
            workload=workload,
        )
        cpu_stats = cpu_primitive.prepared_stats()
        _validate_cpu_prepared_stats(cpu_stats)
        cuda_stats = primitive.prepared_stats()
        _validate_prepared_stats(cuda_stats)
        return _MeasuredPhases(
            capability=primitive.capability(),
            cpu=cpu_phases,
            cpu_stats=cpu_stats,
            cuda=cuda_phases,
            cuda_stats=cuda_stats,
            membership_count=_validated_membership_count(
                cpu.prepared_membership_count(prepared)
            ),
            reference_word_count=_validated_reference_count(
                cpu.prepared_candidate_state_count(prepared)
            ),
            selection_count=_validated_selection_count(
                cpu.prepared_selection_count(prepared)
            ),
        )


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


def _validate_cpu_prepared_stats(stats: CpuPreparedPrimitiveStats) -> None:
    evaluations = WARMUP_COUNT + SAMPLE_COUNT
    expected = (
        1,
        evaluations,
        CORPUS_SIZE,
        PrimitiveKind.ROTATE,
        evaluations - 1,
        CORPUS_SIZE,
    )
    observed = (
        stats.builds,
        stats.evaluations,
        stats.resident_count,
        stats.resident_kind,
        stats.reuses,
        stats.rotate_table_entries,
    )
    if observed != expected:
        message = (
            "prepared CPU rotate did not build and reuse one decode session"
        )
        raise RuntimeError(message)


def _validated_packed_validation_id(identifier: str) -> str:
    expected = "u32le-broadword-domain-v1"
    if identifier != expected:
        message = "packed primitive validation identity drifted"
        raise RuntimeError(message)
    return identifier


def _validated_prepared_validation_id(identifier: str) -> str:
    expected = "cpu-scalar-packed-equality-v2"
    if identifier != expected:
        message = "prepared primitive validation identity drifted"
        raise RuntimeError(message)
    return identifier


def _validated_reference_count(count: int) -> int:
    if count != CORPUS_SIZE:
        message = "prepared CPU reference does not cover full candidate corpus"
        raise RuntimeError(message)
    return count


def _validated_membership_count(count: int) -> int:
    if count != CORPUS_SIZE:
        message = "prepared membership index does not cover full corpus"
        raise RuntimeError(message)
    return count


def _validated_selection_count(count: int) -> int:
    if count != 1:
        message = "prepared rotate selector must retain one exact position"
        raise RuntimeError(message)
    return count


def _validate_prepared_stats(stats: CudaPreparedPrimitiveStats) -> None:
    expected_evaluations = WARMUP_COUNT + SAMPLE_COUNT
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
