# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
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
#   - Rotate-target selector preparation allocation comparison.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Rotate-target selector preparation allocation comparison."""

from __future__ import annotations

from array import array
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

from accelerator.exact_primitives import ROTATE_HIGH_TRIT_WEIGHT
from accelerator.primitive_candidates import ROTATE_EVALUATOR_ID
from accelerator.primitive_candidates import encode_rotate_candidate
from accelerator.work_ports import IndexedCandidateWorkItems
from accelerator.work_ports import InvalidAcceleratorWorkError
from optimizer.rotate_target import PreparedRotateTargetSelection
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import RotateTargetProblem
from optimizer.rotate_target import build_rotate_target_batch
from optimizer.rotate_target import prepare_rotate_target_selection
from optimizer.rotate_target import rotate_target_selection_preparer_id

from benchmarks.accelerator.search_preparation_crossover import CORPUS_SIZES
from benchmarks.accelerator.search_preparation_crossover import (
    build_scale_workload,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.work_ports import CandidateEvaluationBatch
    from accelerator.work_ports import SearchRequest

SAMPLE_COUNT: Final = 15
MEMORY_SAMPLE_COUNT: Final = 5
WARMUP_COUNT: Final = 1
WORD_BYTES: Final = 4
LITTLE_ENDIAN: Final = "little"
NATIVE_WORD_FORMAT: Final = "I"
LEGACY_SELECTION_PREPARER_ID: Final = "classic-u32le-array-copy-preimage-v1"
NATIVE_SELECTION_PREPARER_ID: Final = "classic-u32le-native-view-preimage-v2"
_LEGACY_SELECTION_PROOF = object()


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
    """Incremental allocation observations for one selector preparation."""

    peak: ByteTiming
    retained: ByteTiming


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectionMeasurementPlan:
    """Fixed sample counts for one selector comparison."""

    memory_sample_count: int
    sample_count: int


DEFAULT_PLAN: Final = SelectionMeasurementPlan(
    memory_sample_count=MEMORY_SAMPLE_COUNT,
    sample_count=SAMPLE_COUNT,
)


@dataclass(frozen=True, slots=True)
class SelectionPreparerComparison:
    """Same-run economics for copied-array and native-view selectors."""

    legacy_memory: MemoryMeasurement
    legacy_prepare: Timing
    native_memory: MemoryMeasurement
    native_prepare: Timing
    position_count: int


@dataclass(frozen=True, slots=True)
class ScaleMeasurement:
    """One preregistered candidate scale and exact selector comparison."""

    comparison: SelectionPreparerComparison
    corpus_size: int


def main() -> int:
    """Measure selector preparation at every preregistered corpus size.

    Returns:
        Zero after writing deterministic JSON to stdout.

    """
    scales = tuple(_measure_size(size) for size in CORPUS_SIZES)
    payload = {
        "benchmark_id": "rotate-target-selection-preparer-comparison-v1",
        "measurement": {
            "memory_sample_count": MEMORY_SAMPLE_COUNT,
            "memory_scope": (
                "incremental tracemalloc allocation with request and validated "
                "candidate batch outside tracing"
            ),
            "ordering": "ascending corpus size; legacy then native",
            "sample_count": SAMPLE_COUNT,
            "timed_scope": (
                "request/batch validation, target decode, inverse encoding, "
                "indexed preimage scan, and immutable selector-state "
                "construction"
            ),
            "warmup_count": WARMUP_COUNT,
        },
        "proof": {
            "legacy_selection_preparer_id": LEGACY_SELECTION_PREPARER_ID,
            "native_selection_preparer_id": _native_selection_preparer_id(),
            "positions_equal": True,
        },
        "scales": [asdict(item) for item in scales],
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def measure_selection_preparer_comparison(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    plan: SelectionMeasurementPlan = DEFAULT_PLAN,
) -> SelectionPreparerComparison:
    """Compare exact historical and active selector preparation.

    Returns:
        Timing, memory, and exact-position observations for both algorithms.

    Raises:
        ValueError: If sample counts are not positive.
        RuntimeError: If either implementation changes exact positions.

    """
    if plan.sample_count <= 0 or plan.memory_sample_count <= 0:
        message = "selection comparison sample counts must be positive"
        raise ValueError(message)
    expected = _native_positions(request, batch)
    if _legacy_positions(request, batch) != expected:
        message = "selection comparison changed exact preimage positions"
        raise RuntimeError(message)
    legacy_prepare, native_prepare = _preparation_timings(
        request,
        batch,
        expected,
        sample_count=plan.sample_count,
    )
    legacy_memory, native_memory = _memory_measurements(
        request,
        batch,
        expected,
        sample_count=plan.memory_sample_count,
    )
    return SelectionPreparerComparison(
        legacy_memory=legacy_memory,
        legacy_prepare=legacy_prepare,
        native_memory=native_memory,
        native_prepare=native_prepare,
        position_count=len(expected),
    )


def _measure_size(size: int) -> ScaleMeasurement:
    workload = build_scale_workload(size)
    batch = build_rotate_target_batch(workload.request).validated()
    _ = _legacy_positions(workload.request, batch)
    _ = _native_positions(workload.request, batch)
    return ScaleMeasurement(
        comparison=measure_selection_preparer_comparison(
            workload.request,
            batch,
        ),
        corpus_size=size,
    )


def _preparation_timings(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    expected: tuple[int, ...],
    *,
    sample_count: int,
) -> tuple[Timing, Timing]:
    legacy_samples: list[int] = []
    native_samples: list[int] = []
    for _ in range(sample_count):
        _ = gc.collect()
        legacy_samples.append(
            _timed_positions(
                lambda: _legacy_positions(request, batch), expected
            )
        )
        native_samples.append(
            _timed_positions(
                lambda: _native_positions(request, batch), expected
            )
        )
    return (
        _timing(legacy_samples, sample_count),
        _timing(native_samples, sample_count),
    )


def _timed_positions(
    action: Callable[[], tuple[int, ...]],
    expected: tuple[int, ...],
) -> int:
    start = perf_counter_ns()
    observed = action()
    elapsed = perf_counter_ns() - start
    if observed != expected:
        message = "selector timing changed exact preimage positions"
        raise RuntimeError(message)
    return elapsed


def _memory_measurements(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
    expected: tuple[int, ...],
    *,
    sample_count: int,
) -> tuple[MemoryMeasurement, MemoryMeasurement]:
    legacy_retained: list[int] = []
    legacy_peak: list[int] = []
    native_retained: list[int] = []
    native_peak: list[int] = []
    for _ in range(sample_count):
        retained, peak = _memory_sample(
            lambda: _legacy_positions(request, batch),
            expected,
        )
        legacy_retained.append(retained)
        legacy_peak.append(peak)
        retained, peak = _memory_sample(
            lambda: _native_positions(request, batch),
            expected,
        )
        native_retained.append(retained)
        native_peak.append(peak)
    return (
        _memory(legacy_retained, legacy_peak, sample_count),
        _memory(native_retained, native_peak, sample_count),
    )


def _memory_sample(
    action: Callable[[], tuple[int, ...]],
    expected: tuple[int, ...],
) -> tuple[int, int]:
    _ = gc.collect()
    tracemalloc.start()
    try:
        before, _ = tracemalloc.get_traced_memory()
        tracemalloc.reset_peak()
        observed = action()
        current, peak = tracemalloc.get_traced_memory()
        if observed != expected:
            message = "selector memory sample changed exact preimage positions"
            raise RuntimeError(message)
    finally:
        tracemalloc.stop()
    return max(0, current - before), max(0, peak - before)


def _legacy_positions(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
) -> tuple[int, ...]:
    state = _legacy_prepare_rotate_target_selection(request, batch)
    return state.positions


def _native_positions(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
) -> tuple[int, ...]:
    state = prepare_rotate_target_selection(request, batch)
    if not isinstance(state, PreparedRotateTargetSelection):
        message = "native selector preparer returned an unexpected state"
        raise TypeError(message)
    _, positions = state.for_selection(request, batch)
    return positions


def _legacy_prepare_rotate_target_selection(
    request: SearchRequest,
    batch: CandidateEvaluationBatch,
) -> PreparedRotateTargetSelection:
    validated_request = request.validated()
    if validated_request.algorithm_id != ROTATE_TARGET_ALGORITHM_ID:
        message = "rotate target selection selects a different algorithm"
        raise InvalidAcceleratorWorkError(message)
    validated_batch = batch.validated()
    if validated_batch.evaluator_id != ROTATE_EVALUATOR_ID:
        message = "rotate target selection uses a different evaluator"
        raise InvalidAcceleratorWorkError(message)
    target = RotateTargetProblem.decode_target(validated_request.problem)
    payload = encode_rotate_candidate(_inverse_rotate(target))
    items = validated_batch.items
    if isinstance(items, IndexedCandidateWorkItems):
        positions = _legacy_indexed_rotate_positions(items, payload)
    else:
        positions = tuple(
            index for index, item in enumerate(items) if item.payload == payload
        )
    return PreparedRotateTargetSelection(
        request=validated_request,
        batch=validated_batch,
        target=target,
        positions=positions,
        _proof=_LEGACY_SELECTION_PROOF,
    )


def _legacy_indexed_rotate_positions(
    items: IndexedCandidateWorkItems,
    payload: bytes,
) -> tuple[int, ...]:
    if items.payload_width != WORD_BYTES or len(payload) != WORD_BYTES:
        message = "indexed rotate payload width changed"
        raise InvalidAcceleratorWorkError(message)
    target = int.from_bytes(payload, LITTLE_ENDIAN)
    values = array(NATIVE_WORD_FORMAT)
    if values.itemsize == WORD_BYTES:
        values.frombytes(items.payloads)
        if sys.byteorder != LITTLE_ENDIAN:
            values.byteswap()
        positions = tuple(
            index for index, value in enumerate(values) if value == target
        )
    else:
        positions = tuple(
            index
            for index in range(len(items))
            if int.from_bytes(items.payload_at(index), LITTLE_ENDIAN) == target
        )
    if len(positions) > 1:
        message = "rotate candidate batch retained duplicate payload"
        raise InvalidAcceleratorWorkError(message)
    return positions


def _inverse_rotate(target: int) -> int:
    low_trit = target // ROTATE_HIGH_TRIT_WEIGHT
    quotient = target % ROTATE_HIGH_TRIT_WEIGHT
    return (quotient * 3) + low_trit


def _native_selection_preparer_id() -> str:
    observed = rotate_target_selection_preparer_id()
    if observed != NATIVE_SELECTION_PREPARER_ID:
        message = "native selector preparer identity drifted"
        raise RuntimeError(message)
    return observed


def _memory(
    retained: list[int],
    peak: list[int],
    sample_count: int,
) -> MemoryMeasurement:
    return MemoryMeasurement(
        peak=_byte_timing(peak, sample_count),
        retained=_byte_timing(retained, sample_count),
    )


def _byte_timing(samples: list[int], expected_count: int) -> ByteTiming:
    if len(samples) != expected_count:
        message = "selector comparison retained the wrong memory sample count"
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
        message = "selector comparison retained the wrong timing sample count"
        raise RuntimeError(message)
    return Timing(
        max_ns=max(samples),
        median_ns=int(median(samples)),
        min_ns=min(samples),
        pstdev_ns=pstdev(samples),
        raw_ns=tuple(samples),
    )


if __name__ == "__main__":
    raise SystemExit(main())
