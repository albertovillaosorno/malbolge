# File:
#   - search_preparation_crossover.py
# Path:
#   - benchmarks/accelerator/search_preparation_crossover.py
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
#   - Prepared-search setup, memory, and reuse-crossover benchmark.
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
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed interpreter and argv only.
import sys
from time import perf_counter_ns
import tracemalloc
from typing import Final
from typing import TYPE_CHECKING

from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.evaluated_search import PreparedCandidateMembershipIndex
from accelerator.evaluated_search import prepared_membership_index_id
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import prepared_primitive_storage_id
from accelerator.primitive_candidates import encode_rotate_candidate
from accelerator.primitive_candidates import packed_primitive_validation_id
from accelerator.primitive_candidates import prepared_primitive_validation_id
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import IndexedCandidateWorkItems
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import admit_search_result
from accelerator.work_ports import indexed_candidate_items_id
from benchmarks.accelerator.search_workload import CORPUS_SIZE
from benchmarks.accelerator.search_workload import CUDA_BACKEND
from benchmarks.accelerator.search_workload import SEED
from benchmarks.accelerator.search_workload import TARGET
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import RotateTargetProblem
from optimizer.rotate_target import RotateTargetVerifier
from optimizer.rotate_target import cpu_rotate_target_search_adapter
from optimizer.rotate_target import rotate_target_batch_builder_id
from optimizer.rotate_target import rotate_target_search_adapter

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.cuda import CudaPreparedPrimitiveStats
    from accelerator.evaluated_search import EvaluatedSearchExecutionAdapter
    from accelerator.evaluated_search import PreparedEvaluatedSearch
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.work_ports import CandidateEvaluationBatch
    from accelerator.work_ports import SearchResult

SAMPLE_COUNT: Final = 15
MEMORY_SAMPLE_COUNT: Final = 5
LOOKUP_ITERATIONS: Final = 4_096
WARMUP_COUNT: Final = 1
CORPUS_SIZES: Final = (1, 64, 1_024, CORPUS_SIZE)
WORD_BYTES: Final = 4
COLD_CHILD_ARGUMENT_COUNT: Final = 2
ORDINARY_VALIDATION_ID: Final = "u32le-broadword-domain-v1"
PREPARED_VALIDATION_ID: Final = "cpu-scalar-packed-equality-v2"
CANDIDATE_ITEMS_ID: Final = "u32-index-fixed-width-payloads-rotation-v1"
PREPARED_PRIMITIVE_STORAGE_ID: Final = "proof-bound-u32le-primitive-input-v1"
ROTATE_TARGET_BATCH_BUILDER_ID: Final = (
    "classic-u32le-bitset-inplace-first-representatives-v2"
)
MEMBERSHIP_INDEX_ID: Final = (
    "u32-rotation-or-pair-or-reference-binary-search-v1"
)
LEGACY_MEMBERSHIP_INDEX_ID: Final = "copied-identity-payload-frozenset-v1"
MISSING_LOGICAL_ID: Final = "membership-benchmark-missing-candidate"
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
class MembershipMeasurementPlan:
    """Fixed component sample counts for one membership comparison."""

    lookup_iterations: int
    memory_sample_count: int
    sample_count: int


DEFAULT_MEMBERSHIP_PLAN: Final = MembershipMeasurementPlan(
    lookup_iterations=LOOKUP_ITERATIONS,
    memory_sample_count=MEMORY_SAMPLE_COUNT,
    sample_count=SAMPLE_COUNT,
)


@dataclass(frozen=True, slots=True)
class MembershipLookupMeasurement:
    """Exact hit/miss lookup timings for compact and historical indexes."""

    compact_hit: Timing
    compact_miss: Timing
    iterations_per_sample: int
    legacy_hit: Timing
    legacy_miss: Timing


@dataclass(frozen=True, slots=True)
class MembershipIndexComparison:
    """Same-run component economics for the prepared membership index."""

    compact_memory: MemoryMeasurement
    compact_prepare: Timing
    legacy_memory: MemoryMeasurement
    legacy_prepare: Timing
    lookup: MembershipLookupMeasurement


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
    membership: MembershipIndexComparison
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
        "benchmark_id": "rotate-target-preparation-crossover-v6",
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
            "lookup_iterations_per_sample": LOOKUP_ITERATIONS,
            "lookup_scope": (
                "same proof-bound compact index and copied-tuple frozenset; "
                "exact hit/miss result checked after each timed loop"
            ),
            "membership_component_ordering": (
                "compact prepare, legacy prepare, compact memory, legacy "
                "memory, compact hit/miss, legacy hit/miss"
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
            "candidate_items_id": _candidate_items_id(),
            "legacy_membership_index_id": LEGACY_MEMBERSHIP_INDEX_ID,
            "membership_index_id": _membership_index_id(),
            "ordinary_validation_id": _ordinary_validation_id(),
            "prepared_primitive_storage_id": _prepared_primitive_storage_id(),
            "prepared_validation_id": _prepared_validation_id(),
            "rotate_target_batch_builder_id": _rotate_target_batch_builder_id(),
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
    _require_indexed_candidate_items(prepared)
    proofs = validate_prepared_scale(cpu, prepared, size)
    membership = measure_membership_index_comparison(
        prepared.batch,
        workload.expected[0],
    )
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
        membership=membership,
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
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed module argv, no shell.
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


def measure_membership_index_comparison(
    batch: CandidateEvaluationBatch,
    hit: CandidateProposal,
    plan: MembershipMeasurementPlan = DEFAULT_MEMBERSHIP_PLAN,
) -> MembershipIndexComparison:
    """Measure compact-index economics against the historical copied set.

    Returns:
        Same-run preparation, memory, and exact hit/miss observations.

    Raises:
        ValueError: A sample count is nonpositive or the miss identity exists.

    """
    if (
        plan.sample_count <= 0
        or plan.memory_sample_count <= 0
        or plan.lookup_iterations <= 0
    ):
        message = "membership comparison sample counts must be positive"
        raise ValueError(message)
    validated = batch.validated()
    miss = CandidateProposal(
        logical_id=MISSING_LOGICAL_ID,
        payload=hit.payload,
    )
    if any(item.logical_id == miss.logical_id for item in validated.items):
        message = "membership benchmark miss identity exists in candidate batch"
        raise ValueError(message)
    compact_prepare, legacy_prepare = _membership_preparation(
        validated,
        plan.sample_count,
    )
    compact_memory, legacy_memory = _membership_memory(
        validated,
        plan.memory_sample_count,
    )
    lookup = _membership_lookup(
        validated,
        hit,
        miss,
        plan=plan,
    )
    return MembershipIndexComparison(
        compact_memory=compact_memory,
        compact_prepare=compact_prepare,
        legacy_memory=legacy_memory,
        legacy_prepare=legacy_prepare,
        lookup=lookup,
    )


def _membership_preparation(
    batch: CandidateEvaluationBatch,
    sample_count: int,
) -> tuple[Timing, Timing]:
    compact_samples: list[int] = []
    legacy_samples: list[int] = []
    for _ in range(sample_count):
        _ = gc.collect()
        start = perf_counter_ns()
        compact = PreparedCandidateMembershipIndex.prepare(batch)
        compact_samples.append(perf_counter_ns() - start)
        if compact.count_for(batch) != len(batch.items):
            message = "compact membership preparation changed candidate count"
            raise RuntimeError(message)
        start = perf_counter_ns()
        legacy = _legacy_membership_index(batch)
        legacy_samples.append(perf_counter_ns() - start)
        if len(legacy) != len(batch.items):
            message = "legacy membership preparation changed candidate count"
            raise RuntimeError(message)
    return (
        _timing(compact_samples, sample_count),
        _timing(legacy_samples, sample_count),
    )


def _membership_memory(
    batch: CandidateEvaluationBatch,
    sample_count: int,
) -> tuple[MemoryMeasurement, MemoryMeasurement]:
    compact_retained: list[int] = []
    compact_peak: list[int] = []
    legacy_retained: list[int] = []
    legacy_peak: list[int] = []
    for _ in range(sample_count):
        compact_current, compact_max = _component_memory_sample(
            lambda: PreparedCandidateMembershipIndex.prepare(batch),
        )
        legacy_current, legacy_max = _component_memory_sample(
            lambda: _legacy_membership_index(batch),
        )
        compact_retained.append(compact_current)
        compact_peak.append(compact_max)
        legacy_retained.append(legacy_current)
        legacy_peak.append(legacy_max)
    return (
        _memory_measurement_from_samples(
            compact_retained,
            compact_peak,
            sample_count,
        ),
        _memory_measurement_from_samples(
            legacy_retained,
            legacy_peak,
            sample_count,
        ),
    )


def _component_memory_sample(factory: Callable[[], object]) -> tuple[int, int]:
    _ = gc.collect()
    tracemalloc.start()
    try:
        before, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        value = factory()
        current, peak = tracemalloc.get_traced_memory()
        del value
    finally:
        tracemalloc.stop()
    return max(0, current - before), max(0, peak - before)


def _memory_measurement_from_samples(
    retained: list[int],
    peak: list[int],
    sample_count: int,
) -> MemoryMeasurement:
    return MemoryMeasurement(
        peak=_byte_timing(peak, sample_count),
        retained=_byte_timing(retained, sample_count),
    )


def _membership_lookup(
    batch: CandidateEvaluationBatch,
    hit: CandidateProposal,
    miss: CandidateProposal,
    *,
    plan: MembershipMeasurementPlan,
) -> MembershipLookupMeasurement:
    compact = PreparedCandidateMembershipIndex.prepare(batch)
    legacy = _legacy_membership_index(batch)
    _validate_membership_models(
        compact,
        legacy,
        batch=batch,
        proposals=(hit, miss),
    )
    compact_hit: list[int] = []
    compact_miss: list[int] = []
    legacy_hit: list[int] = []
    legacy_miss: list[int] = []
    for _ in range(plan.sample_count):
        compact_hit.append(
            _timed_lookup(
                lambda: compact.contains(batch, hit),
                plan.lookup_iterations,
                plan.lookup_iterations,
            )
        )
        compact_miss.append(
            _timed_lookup(
                lambda: compact.contains(batch, miss),
                plan.lookup_iterations,
                0,
            )
        )
        legacy_hit.append(
            _timed_lookup(
                lambda: _legacy_contains(legacy, hit),
                plan.lookup_iterations,
                plan.lookup_iterations,
            )
        )
        legacy_miss.append(
            _timed_lookup(
                lambda: _legacy_contains(legacy, miss),
                plan.lookup_iterations,
                0,
            )
        )
    return MembershipLookupMeasurement(
        compact_hit=_timing(compact_hit, plan.sample_count),
        compact_miss=_timing(compact_miss, plan.sample_count),
        iterations_per_sample=plan.lookup_iterations,
        legacy_hit=_timing(legacy_hit, plan.sample_count),
        legacy_miss=_timing(legacy_miss, plan.sample_count),
    )


def _validate_membership_models(
    compact: PreparedCandidateMembershipIndex,
    legacy: frozenset[tuple[str, bytes]],
    *,
    batch: CandidateEvaluationBatch,
    proposals: tuple[CandidateProposal, CandidateProposal],
) -> None:
    hit, miss = proposals
    observed = (
        compact.contains(batch, hit),
        compact.contains(batch, miss),
        _legacy_contains(legacy, hit),
        _legacy_contains(legacy, miss),
    )
    if observed != (True, False, True, False):
        message = "membership comparison changed exact hit/miss semantics"
        raise RuntimeError(message)


def _timed_lookup(
    action: Callable[[], bool],
    iterations: int,
    expected_matches: int,
) -> int:
    matches = 0
    start = perf_counter_ns()
    for _ in range(iterations):
        matches += action()
    elapsed = perf_counter_ns() - start
    if matches != expected_matches:
        message = "membership lookup changed expected exact result"
        raise RuntimeError(message)
    return elapsed


def _legacy_membership_index(
    batch: CandidateEvaluationBatch,
) -> frozenset[tuple[str, bytes]]:
    return frozenset((item.logical_id, item.payload) for item in batch.items)


def _legacy_contains(
    index: frozenset[tuple[str, bytes]],
    proposal: CandidateProposal,
) -> bool:
    return (proposal.logical_id, proposal.payload) in index


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


def _require_indexed_candidate_items(
    prepared: PreparedEvaluatedSearch,
) -> None:
    if not isinstance(prepared.batch.items, IndexedCandidateWorkItems):
        message = "rotate preparation did not retain indexed candidate items"
        raise TypeError(message)


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


def _rotate_target_batch_builder_id() -> str:
    observed = rotate_target_batch_builder_id()
    if observed != ROTATE_TARGET_BATCH_BUILDER_ID:
        message = "rotate-target batch builder identity drifted"
        raise RuntimeError(message)
    return observed


def _prepared_primitive_storage_id() -> str:
    observed = prepared_primitive_storage_id()
    if observed != PREPARED_PRIMITIVE_STORAGE_ID:
        message = "prepared primitive storage identity drifted"
        raise RuntimeError(message)
    return observed


def _candidate_items_id() -> str:
    observed = indexed_candidate_items_id()
    if observed != CANDIDATE_ITEMS_ID:
        message = "indexed candidate item storage identity drifted"
        raise RuntimeError(message)
    return observed


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
