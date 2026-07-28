# File:
#   - prepared_cuda_primitive_phase_profile.py
# Path:
#   - benchmarks/accelerator/prepared_cuda_primitive_phase_profile.py
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
#   - Subphase diagnostics for prepared CUDA primitive candidate evidence.
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

from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.exact_primitives import PrimitiveBatch
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import prepare_primitive_batch
from accelerator.primitive_candidates import prepare_rotate_candidate_batch
from accelerator.primitive_candidates import (
    prepared_primitive_reference_word_count,
)
from accelerator.primitive_candidates import prepared_primitive_validation_id
from accelerator.primitive_candidates import profile_prepared_primitive_result
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
        PreparedPrimitiveEncodingPhaseProfile,
    )
    from accelerator.work_ports import CandidateEvaluationBatch
    from benchmarks.accelerator.search_workload import SearchBenchmarkWorkload

SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1
MINIMUM_COVERAGE_PERCENT: Final = 95.0
VALIDATION_ID: Final = "cpu-reference-packed-equality-v1"
PHASE_NAMES: Final = (
    "launch_sync_ns",
    "download_ns",
    "immutable_bytes_ns",
    "cuda_total_ns",
    "cuda_unattributed_ns",
    "contract_ns",
    "exact_compare_ns",
    "diagnostic_ns",
    "result_build_ns",
    "encoding_total_ns",
    "encoding_unattributed_ns",
    "end_to_end_total_ns",
)
COMPONENT_NAMES: Final = (
    "launch_sync_ns",
    "download_ns",
    "immutable_bytes_ns",
    "cuda_unattributed_ns",
    "contract_ns",
    "exact_compare_ns",
    "diagnostic_ns",
    "result_build_ns",
    "encoding_unattributed_ns",
)


@dataclass(frozen=True, slots=True)
class PrimitivePhaseSample:
    """One exact prepared CUDA primitive phase observation."""

    contract_ns: int
    cuda_total_ns: int
    cuda_unattributed_ns: int
    diagnostic_ns: int
    download_ns: int
    encoding_total_ns: int
    encoding_unattributed_ns: int
    end_to_end_total_ns: int
    exact_compare_ns: int
    immutable_bytes_ns: int
    launch_sync_ns: int
    result_build_ns: int


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
    reference_word_count: int
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
        "benchmark_id": "prepared-cuda-primitive-reference-phase-profile-v1",
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
            "ordering": "fixed prepared CUDA then exact CPU-reference check",
            "preparation_timed": False,
            "sample_count": SAMPLE_COUNT,
            "warmup_count": WARMUP_COUNT,
        },
        "device": _device_payload(measured.capability),
        "proof": {
            "exact_cpu_result_equality": True,
            "coverage_scope": (
                "named components plus visible residuals over public "
                "layer totals"
            ),
            "minimum_coverage_percent": MINIMUM_COVERAGE_PERCENT,
            "prepared_reference_word_count": measured.reference_word_count,
            "prepared_validation_id": _validated_validation_id(),
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
    candidate_state = prepare_rotate_candidate_batch(batch)
    prepared = _prepare_primitive(batch)
    reference_word_count = _validated_reference_count(
        prepared_primitive_reference_word_count(candidate_state)
    )
    with CudaExactPrimitiveAdapter() as adapter:
        samples = _measure(
            adapter,
            candidate_state=candidate_state,
            prepared=prepared,
        )
        stats = adapter.prepared_stats()
        _validate_stats(stats)
        return _MeasuredPrimitiveProfile(
            capability=adapter.capability(),
            reference_word_count=reference_word_count,
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
    candidate_state: object,
    prepared: PreparedPrimitiveBatch,
) -> tuple[PrimitivePhaseSample, ...]:
    for _ in range(WARMUP_COUNT):
        primitive, _ = adapter.profile_prepared(prepared)
        _, _ = profile_prepared_primitive_result(
            candidate_state,
            primitive,
            adapter.capability(),
        )
    return tuple(
        _measure_one(
            adapter,
            candidate_state=candidate_state,
            prepared=prepared,
        )
        for _ in range(SAMPLE_COUNT)
    )


def _measure_one(
    adapter: CudaExactPrimitiveAdapter,
    *,
    candidate_state: object,
    prepared: PreparedPrimitiveBatch,
) -> PrimitivePhaseSample:
    total_start = perf_counter_ns()
    primitive, cuda = adapter.profile_prepared(prepared)
    _, encoding = profile_prepared_primitive_result(
        candidate_state,
        primitive,
        adapter.capability(),
    )
    end_to_end_total_ns = perf_counter_ns() - total_start
    sample = _sample(cuda, encoding, end_to_end_total_ns=end_to_end_total_ns)
    _validate_sample(sample)
    return sample


def _sample(
    cuda: CudaPreparedPrimitivePhaseProfile,
    encoding: PreparedPrimitiveEncodingPhaseProfile,
    *,
    end_to_end_total_ns: int,
) -> PrimitivePhaseSample:
    cuda_components = (
        cuda.launch_sync_ns + cuda.download_ns + cuda.immutable_bytes_ns
    )
    encoding_components = (
        encoding.contract_ns
        + encoding.exact_compare_ns
        + encoding.diagnostic_ns
        + encoding.result_build_ns
    )
    return PrimitivePhaseSample(
        contract_ns=encoding.contract_ns,
        cuda_total_ns=cuda.total_ns,
        cuda_unattributed_ns=cuda.total_ns - cuda_components,
        diagnostic_ns=encoding.diagnostic_ns,
        download_ns=cuda.download_ns,
        encoding_total_ns=encoding.total_ns,
        encoding_unattributed_ns=encoding.total_ns - encoding_components,
        end_to_end_total_ns=end_to_end_total_ns,
        exact_compare_ns=encoding.exact_compare_ns,
        immutable_bytes_ns=cuda.immutable_bytes_ns,
        launch_sync_ns=cuda.launch_sync_ns,
        result_build_ns=encoding.result_build_ns,
    )


def _validate_sample(sample: PrimitivePhaseSample) -> None:
    cuda_components = (
        sample.launch_sync_ns,
        sample.download_ns,
        sample.immutable_bytes_ns,
        sample.cuda_unattributed_ns,
    )
    encoding_components = (
        sample.contract_ns,
        sample.exact_compare_ns,
        sample.diagnostic_ns,
        sample.result_build_ns,
        sample.encoding_unattributed_ns,
    )
    if sample.cuda_total_ns != sum(cuda_components):
        message = "CUDA primitive phase profile has incomplete total"
        raise RuntimeError(message)
    if sample.encoding_total_ns != sum(encoding_components):
        message = "prepared exact-validation profile has incomplete total"
        raise RuntimeError(message)


def _coverage(samples: tuple[PrimitivePhaseSample, ...]) -> tuple[float, ...]:
    return tuple(
        sum(getattr(sample, name) for name in COMPONENT_NAMES)
        / (sample.cuda_total_ns + sample.encoding_total_ns)
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
    identifier = prepared_primitive_validation_id()
    if identifier != VALIDATION_ID:
        message = "prepared primitive validation identity drifted"
        raise RuntimeError(message)
    return identifier


def _validated_reference_count(count: int) -> int:
    if count != CORPUS_SIZE:
        message = "prepared CPU reference does not cover full candidate corpus"
        raise RuntimeError(message)
    return count


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
