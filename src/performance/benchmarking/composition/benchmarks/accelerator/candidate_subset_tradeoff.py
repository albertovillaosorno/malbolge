# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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
#   - Exact candidate-subset proof construction tradeoff benchmark.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Exact candidate-subset proof versus repeated membership validation."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
import gc
import json
from statistics import median
from statistics import pstdev
import sys
from time import perf_counter_ns
import tracemalloc
from typing import Final
from typing import TYPE_CHECKING

from accelerator.evaluated_search import PreparedCandidateMembershipIndex
from accelerator.work_ports import CandidateEvaluationBatch
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import prepare_candidate_subset
from accelerator.work_ports import prepared_candidate_subset_id
from optimizer.rotate_target import build_rotate_target_batch

from benchmarks.accelerator.search_preparation_crossover import (
    build_scale_workload,
)
from benchmarks.accelerator.search_workload import CORPUS_SIZE

if TYPE_CHECKING:
    from collections.abc import Callable

BENCHMARK_ID: Final = "candidate-subset-proof-tradeoff-v1"
LEGACY_VALIDATION_ID: Final = "materialized-membership-revalidation-v1"
CANDIDATE_SUBSET_ID: Final = "request-order-position-subset-v1"
SUBSET_SIZES: Final = (0, 1, 64, 1_024)
SAMPLE_COUNT: Final = 15
MEMORY_SAMPLE_COUNT: Final = 5
WARMUP_COUNT: Final = 1


@dataclass(frozen=True, slots=True, kw_only=True)
class MeasurementPlan:
    """Fixed sample counts for one subset comparison."""

    memory_sample_count: int
    sample_count: int


DEFAULT_PLAN: Final = MeasurementPlan(
    memory_sample_count=MEMORY_SAMPLE_COUNT,
    sample_count=SAMPLE_COUNT,
)


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
    """Retained and peak traced allocation for one action."""

    peak: ByteTiming
    retained: ByteTiming


@dataclass(frozen=True, slots=True)
class RouteMeasurement:
    """Timing and memory for one exact subset-construction route."""

    memory: MemoryMeasurement
    timing: Timing


@dataclass(frozen=True, slots=True)
class SubsetMeasurement:
    """One exact subset size compared through both validation routes."""

    legacy: RouteMeasurement
    proof: RouteMeasurement
    subset_size: int


@dataclass(frozen=True, slots=True)
class _SubsetActions:
    full_batch: CandidateEvaluationBatch
    membership: PreparedCandidateMembershipIndex
    positions: tuple[int, ...]

    def legacy(self) -> CandidateEvaluationBatch:
        projected = CandidateEvaluationBatch(
            evaluator_id=self.full_batch.evaluator_id,
            items=tuple(
                self.full_batch.items[position] for position in self.positions
            ),
        ).validated()
        for item in projected.items:
            proposal = CandidateProposal(
                logical_id=item.logical_id,
                payload=item.payload,
            )
            if not self.membership.contains(self.full_batch, proposal):
                message = "legacy subset validation lost exact membership"
                raise RuntimeError(message)
        return projected

    def proof(self) -> CandidateEvaluationBatch:
        subset = prepare_candidate_subset(self.full_batch, self.positions)
        projected, observed = subset.for_batch(self.full_batch)
        if observed != self.positions:
            message = "candidate subset proof changed request-order positions"
            raise RuntimeError(message)
        return projected


def measure_candidate_subset_tradeoff(
    full_batch: CandidateEvaluationBatch,
    positions: tuple[int, ...],
    *,
    plan: MeasurementPlan = DEFAULT_PLAN,
) -> SubsetMeasurement:
    """Measure exact proof construction against repeated membership checks.

    Returns:
        Both routes with raw timing and traced-memory samples.

    Raises:
        RuntimeError: If exact route results or position identity diverge.

    """
    validated = full_batch.validated()
    actions = _SubsetActions(
        full_batch=validated,
        membership=PreparedCandidateMembershipIndex.prepare(validated),
        positions=positions,
    )
    expected = actions.legacy()
    if actions.proof() != expected:
        message = "candidate subset routes produced different projected batches"
        raise RuntimeError(message)
    return SubsetMeasurement(
        legacy=_measure_route(actions.legacy, len(positions), plan),
        proof=_measure_route(actions.proof, len(positions), plan),
        subset_size=len(positions),
    )


def _measure_route(
    action: Callable[[], CandidateEvaluationBatch],
    expected_count: int,
    plan: MeasurementPlan,
) -> RouteMeasurement:
    for _ in range(WARMUP_COUNT):
        _validate_count(action(), expected_count)
    timing_samples: list[int] = []
    for _ in range(plan.sample_count):
        start = perf_counter_ns()
        result = action()
        timing_samples.append(perf_counter_ns() - start)
        _validate_count(result, expected_count)
    retained: list[int] = []
    peaks: list[int] = []
    for _ in range(plan.memory_sample_count):
        _ = gc.collect()
        tracemalloc.start()
        before = tracemalloc.get_traced_memory()[0]
        result = action()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        _validate_count(result, expected_count)
        retained.append(current - before)
        peaks.append(peak - before)
    return RouteMeasurement(
        memory=MemoryMeasurement(
            peak=_byte_timing(peaks, plan.memory_sample_count),
            retained=_byte_timing(retained, plan.memory_sample_count),
        ),
        timing=_timing(timing_samples, plan.sample_count),
    )


def _validate_count(batch: CandidateEvaluationBatch, expected: int) -> None:
    if len(batch.items) != expected:
        message = "candidate subset benchmark count drifted"
        raise RuntimeError(message)


def _timing(samples: list[int], expected: int) -> Timing:
    if len(samples) != expected:
        message = "candidate subset benchmark timing sample count drifted"
        raise RuntimeError(message)
    return Timing(
        max_ns=max(samples),
        median_ns=int(median(samples)),
        min_ns=min(samples),
        pstdev_ns=pstdev(samples),
        raw_ns=tuple(samples),
    )


def _byte_timing(samples: list[int], expected: int) -> ByteTiming:
    if len(samples) != expected:
        message = "candidate subset benchmark memory sample count drifted"
        raise RuntimeError(message)
    return ByteTiming(
        max_bytes=max(samples),
        median_bytes=int(median(samples)),
        min_bytes=min(samples),
        pstdev_bytes=pstdev(samples),
        raw_bytes=tuple(samples),
    )


def main() -> int:
    """Run the full-domain exact subset comparison and emit JSON.

    Returns:
        Process status zero after the complete record is emitted.

    Raises:
        RuntimeError: If active subset identity drifts.

    """
    workload = build_scale_workload(CORPUS_SIZE)
    full_batch = build_rotate_target_batch(workload.request).validated()
    measurements = tuple(
        measure_candidate_subset_tradeoff(
            full_batch,
            tuple(range(subset_size)),
        )
        for subset_size in SUBSET_SIZES
    )
    identifier = prepared_candidate_subset_id()
    if identifier != CANDIDATE_SUBSET_ID:
        message = "candidate subset benchmark identity drifted"
        raise RuntimeError(message)
    payload = {
        "benchmark_id": BENCHMARK_ID,
        "candidate_subset_id": identifier,
        "corpus_size": len(full_batch.items),
        "legacy_validation_id": LEGACY_VALIDATION_ID,
        "memory_sample_count": MEMORY_SAMPLE_COUNT,
        "sample_count": SAMPLE_COUNT,
        "scales": [asdict(item) for item in measurements],
        "warmup_count": WARMUP_COUNT,
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
