# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Subphase diagnostics for prepared CUDA primitive candidate evidence."""

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

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import prepare_primitive_batch
from accelerator.primitive_candidates import PrimitiveCandidateEvaluationAdapter
from accelerator.primitive_candidates import packed_primitive_validation_id
from accelerator.primitive_candidates import profile_packed_primitive_result
from benchmarks.accelerator.search_workload import CORPUS_SIZE
from benchmarks.accelerator.search_workload import SEED
from benchmarks.accelerator.search_workload import TARGET
from benchmarks.accelerator.search_workload import WORKLOAD_ID
from benchmarks.accelerator.search_workload import (
    full_domain_rotate_target_workload,
)
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import build_rotate_target_batch

if TYPE_CHECKING:
    from accelerator.cuda import CudaPreparedPrimitivePhaseProfile
    from accelerator.cuda import CudaPreparedPrimitiveStats
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.exact_primitives import PreparedPrimitiveBatch
    from accelerator.primitive_candidates import (
        PackedPrimitiveEncodingPhaseProfile,
    )
    from accelerator.work_ports import CandidateEvaluationBatch
    from accelerator.work_ports import CandidateEvaluationResult
    from benchmarks.accelerator.search_workload import SearchBenchmarkWorkload

SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1
MINIMUM_COVERAGE_PERCENT: Final = 95.0
VALIDATION_ID: Final = "u32le-broadword-domain-v1"
PHASE_NAMES: Final = (
    "launch_sync_ns",
    "download_ns",
    "immutable_bytes_ns",
    "cuda_total_ns",
    "contract_ns",
    "mask_lookup_ns",
    "int_decode_ns",
    "high_mask_ns",
    "threshold_ns",
    "diagnostic_ns",
    "result_build_ns",
    "encoding_total_ns",
    "end_to_end_total_ns",
)
COMPONENT_NAMES: Final = (
    "launch_sync_ns",
    "download_ns",
    "immutable_bytes_ns",
    "contract_ns",
    "mask_lookup_ns",
    "int_decode_ns",
    "high_mask_ns",
    "threshold_ns",
    "diagnostic_ns",
    "result_build_ns",
)


@dataclass(frozen=True, slots=True)
class PrimitivePhaseSample:
    """One exact prepared CUDA primitive phase observation."""

    contract_ns: int
    cuda_total_ns: int
    diagnostic_ns: int
    download_ns: int
    encoding_total_ns: int
    end_to_end_total_ns: int
    high_mask_ns: int
    immutable_bytes_ns: int
    int_decode_ns: int
    launch_sync_ns: int
    mask_lookup_ns: int
    result_build_ns: int
    threshold_ns: int


@dataclass(frozen=True, slots=True)
class PhaseTiming:
    """Raw and summary timing for one primitive subphase."""

    max_ns: int
    median_ns: int
    min_ns: int
    pstdev_ns: float
    raw_ns: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _MeasuredPrimitiveProfile:
    capability: AcceleratorCapability
    samples: tuple[PrimitivePhaseSample, ...]
    stats: CudaPreparedPrimitiveStats


def main() -> int:
    """Measure exact prepared CUDA primitive and packed-validation subphases.

    Returns:
        Zero after emitting retained-sample-ready JSON to stdout.

    """
    workload = full_domain_rotate_target_workload()
    measured = _measure_workload(workload)
    phases = {
        name: _timing(
            tuple(getattr(sample, name) for sample in measured.samples)
        )
        for name in PHASE_NAMES
    }
    coverage = _coverage(measured.samples)
    _validate_coverage(coverage)
    payload = {
        "benchmark_id": "prepared-cuda-primitive-phase-profile-v1",
        "workload": {
            "algorithm_id": ROTATE_TARGET_ALGORITHM_ID,
            "candidate_count": CORPUS_SIZE,
            "identity": WORKLOAD_ID,
            "problem_sha256": sha256(workload.problem).hexdigest(),
            "seed": SEED,
            "target": TARGET,
        },
        "measurement": {
            "adapter_setup_timed": False,
            "ordering": "fixed prepared CUDA then neutral packed encoding",
            "preparation_timed": False,
            "sample_count": SAMPLE_COUNT,
            "warmup_count": WARMUP_COUNT,
        },
        "device": _device_payload(measured.capability),
        "proof": {
            "exact_cpu_result_equality": True,
            "minimum_coverage_percent": MINIMUM_COVERAGE_PERCENT,
            "packed_validation_id": _validated_validation_id(),
            "prepared_session": asdict(measured.stats),
        },
        "coverage_percent": {
            "median": median(coverage),
            "minimum": min(coverage),
            "maximum": max(coverage),
            "raw": coverage,
        },
        "phases": {name: asdict(value) for name, value in phases.items()},
        "samples": [asdict(sample) for sample in measured.samples],
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _measure_workload(
    workload: SearchBenchmarkWorkload,
) -> _MeasuredPrimitiveProfile:
    batch = build_rotate_target_batch(workload.request).validated()
    prepared = _prepare_primitive(batch)
    expected = PrimitiveCandidateEvaluationAdapter(
        CpuExactPrimitiveAdapter(),
        PrimitiveKind.ROTATE,
    ).evaluate(batch)
    with CudaExactPrimitiveAdapter() as adapter:
        samples = _measure(
            adapter,
            batch=batch,
            prepared=prepared,
            expected=expected,
        )
        stats = adapter.prepared_stats()
        _validate_stats(stats)
        return _MeasuredPrimitiveProfile(
            capability=adapter.capability(),
            samples=samples,
            stats=stats,
        )


def _prepare_primitive(
    batch: CandidateEvaluationBatch,
) -> PreparedPrimitiveBatch:
    data = tuple(int.from_bytes(item.payload, "little") for item in batch.items)
    return prepare_primitive_batch(
        PrimitiveBatch(
            accumulators=(),
            data=data,
            kind=PrimitiveKind.ROTATE,
        )
    )


def _measure(
    adapter: CudaExactPrimitiveAdapter,
    *,
    batch: CandidateEvaluationBatch,
    prepared: PreparedPrimitiveBatch,
    expected: CandidateEvaluationResult,
) -> tuple[PrimitivePhaseSample, ...]:
    for _ in range(WARMUP_COUNT):
        primitive, _ = adapter.profile_prepared(prepared)
        result, _ = profile_packed_primitive_result(
            batch,
            primitive,
            adapter.capability(),
        )
        _validate_result(result, expected)
    return tuple(
        _measure_one(
            adapter,
            batch=batch,
            prepared=prepared,
            expected=expected,
        )
        for _ in range(SAMPLE_COUNT)
    )


def _measure_one(
    adapter: CudaExactPrimitiveAdapter,
    *,
    batch: CandidateEvaluationBatch,
    prepared: PreparedPrimitiveBatch,
    expected: CandidateEvaluationResult,
) -> PrimitivePhaseSample:
    total_start = perf_counter_ns()
    primitive, cuda = adapter.profile_prepared(prepared)
    result, encoding = profile_packed_primitive_result(
        batch,
        primitive,
        adapter.capability(),
    )
    end_to_end_total_ns = perf_counter_ns() - total_start
    _validate_result(result, expected)
    sample = _sample(cuda, encoding, end_to_end_total_ns=end_to_end_total_ns)
    _validate_sample(sample)
    return sample


def _sample(
    cuda: CudaPreparedPrimitivePhaseProfile,
    encoding: PackedPrimitiveEncodingPhaseProfile,
    *,
    end_to_end_total_ns: int,
) -> PrimitivePhaseSample:
    return PrimitivePhaseSample(
        contract_ns=encoding.contract_ns,
        cuda_total_ns=cuda.total_ns,
        diagnostic_ns=encoding.diagnostic_ns,
        download_ns=cuda.download_ns,
        encoding_total_ns=encoding.total_ns,
        end_to_end_total_ns=end_to_end_total_ns,
        high_mask_ns=encoding.high_mask_ns,
        immutable_bytes_ns=cuda.immutable_bytes_ns,
        int_decode_ns=encoding.int_decode_ns,
        launch_sync_ns=cuda.launch_sync_ns,
        mask_lookup_ns=encoding.mask_lookup_ns,
        result_build_ns=encoding.result_build_ns,
        threshold_ns=encoding.threshold_ns,
    )


def _validate_result(
    observed: CandidateEvaluationResult,
    expected: CandidateEvaluationResult,
) -> None:
    if observed.packed != expected.packed:
        message = "profiled CUDA primitive result differs from CPU reference"
        raise RuntimeError(message)


def _validate_sample(sample: PrimitivePhaseSample) -> None:
    cuda_components = (
        sample.launch_sync_ns,
        sample.download_ns,
        sample.immutable_bytes_ns,
    )
    encoding_components = tuple(
        getattr(sample, name)
        for name in COMPONENT_NAMES
        if name
        not in {
            "launch_sync_ns",
            "download_ns",
            "immutable_bytes_ns",
        }
    )
    if sample.cuda_total_ns < sum(cuda_components):
        message = "CUDA primitive phase profile has incomplete total"
        raise RuntimeError(message)
    if sample.encoding_total_ns < sum(encoding_components):
        message = "packed encoding phase profile has incomplete total"
        raise RuntimeError(message)


def _coverage(samples: tuple[PrimitivePhaseSample, ...]) -> tuple[float, ...]:
    return tuple(
        sum(getattr(sample, name) for name in COMPONENT_NAMES)
        / sample.end_to_end_total_ns
        * 100
        for sample in samples
    )


def _validate_coverage(coverage: tuple[float, ...]) -> None:
    if min(coverage) < MINIMUM_COVERAGE_PERCENT:
        message = (
            "prepared CUDA primitive named phase coverage is below 95 percent"
        )
        raise RuntimeError(message)


def _validated_validation_id() -> str:
    identifier = packed_primitive_validation_id()
    if identifier != VALIDATION_ID:
        message = "packed primitive validation identity drifted"
        raise RuntimeError(message)
    return identifier


def _validate_stats(stats: CudaPreparedPrimitiveStats) -> None:
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
        WARMUP_COUNT + SAMPLE_COUNT,
        WARMUP_COUNT + SAMPLE_COUNT,
        CORPUS_SIZE,
        PrimitiveKind.ROTATE,
        WARMUP_COUNT + SAMPLE_COUNT - 1,
    )
    if observed != expected:
        message = "prepared CUDA primitive profile proof counters drifted"
        raise RuntimeError(message)


def _device_payload(capability: AcceleratorCapability) -> dict[str, str]:
    return {
        "arch": capability.device_arch,
        "backend": capability.backend_id,
        "name": capability.device_name,
    }


def _timing(values: tuple[int, ...]) -> PhaseTiming:
    return PhaseTiming(
        max_ns=max(values),
        median_ns=int(median(values)),
        min_ns=min(values),
        pstdev_ns=pstdev(values),
        raw_ns=values,
    )


if __name__ == "__main__":
    raise SystemExit(main())
