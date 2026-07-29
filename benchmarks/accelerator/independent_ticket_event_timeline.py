# File:
#   - independent_ticket_event_timeline.py
# Path:
#   - benchmarks/accelerator/independent_ticket_event_timeline.py
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
#   - CUDA-event interval attribution for grouped independent primitive tickets.
# - Must-Not:
#   - Treat event intervals as pure kernel duration or change exact semantics.
# - Allows:
#   - Inputs: the retained full-domain crazy workload and groups 2/4/8.
#   - Outputs: raw event intervals, overlap metrics, wall time, and identities.
#   - Side effects: scoped CUDA execution and JSON output only.
# - Split-When:
#   - Split when asynchronous transfers or another workload needs a separate
#     protocol.
# - Merge-When:
#   - Merge when another benchmark owns this timeline-attribution question.
# - Summary:
#   - Independent CUDA ticket event-timeline benchmark.
# - Description:
#   - Tests whether grouped one-shot ticket kernels overlap on the live device.
# - Usage:
#   - Run from a clean commit and retain output under accelerator evidence.
# - Defaults:
#   - One warmup and fifteen retained cyclic-order samples per group.
#
# Related documents:
# - docs/research/methodology/benchmark-protocol.md
#
# Large file:
#   - false
#

"""CUDA-event attribution for grouped independent primitive tickets."""

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from hashlib import sha256
import json
from operator import itemgetter
from statistics import median
from statistics import pstdev
import sys
from time import perf_counter_ns
from typing import Final
from typing import TYPE_CHECKING

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.cuda import cuda_independent_kernel_launch_id
from accelerator.cuda import cuda_independent_kernel_timeline_id
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PackedPrimitiveResult
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import prepare_packed_primitive_batch
from accelerator.exact_primitives import prepared_primitive_storage_id

if TYPE_CHECKING:
    from accelerator.cuda import CudaIndependentKernelTimelineSample
    from accelerator.exact_primitives import PreparedPrimitiveBatch
    from accelerator.exact_primitives import PrimitiveExecutionResult

WORD_BYTES: Final = 4
CORPUS_SIZE: Final = MAX_WORD + 1
GROUP_SIZES: Final = (2, 4, 8)
HYPOTHESIS_GROUP_SIZE: Final = 8
CUDA_BACKEND_ID: Final = "cuda"
SAMPLE_COUNT: Final = 15
WARMUP_COUNT: Final = 1
OVERLAP_EPSILON_MS: Final = 0.001
WORKLOAD_ID: Final = "classic-crazy-full-domain-independent-ticket-group-v1"
BENCHMARK_ID: Final = "cuda-independent-ticket-event-timeline-v1"
EXPECTED_LAUNCH_ID: Final = "cuda-independent-stream-kernel-launch-v1"
EXPECTED_TIMELINE_ID: Final = "cuda-independent-stream-kernel-timeline-v1"
EXPECTED_STORAGE_ID: Final = "proof-bound-u32le-primitive-input-v1"
ROUTE_ORDER: Final = "cyclic first-group rotation across groups 2, 4, and 8"
HYPOTHESIS: Final = (
    "group-eight submit-all/reverse-wait produces significant CUDA-event "
    "interval overlap in more than seven of fifteen samples"
)
REJECTION_RULE: Final = (
    "reject physical-overlap attribution when group eight has at most seven "
    "samples with overlap above one microsecond, when median overlap is not "
    "positive, when peak concurrency never exceeds one, or when an exact "
    "identity/output check fails"
)
INTERPRETATION_LIMIT: Final = (
    "CUDA event elapsed intervals can include interleaved work; endpoints "
    "describe an observed execution timeline rather than pure kernel duration"
)


@dataclass(frozen=True, slots=True)
class TicketInterval:
    """One retained CUDA-event interval for one submitted ticket."""

    duration_ms: float
    end_ms: float
    start_ms: float
    submission_index: int


@dataclass(frozen=True, slots=True)
class TimelineObservation:
    """One grouped route wall time plus derived event-timeline metrics."""

    concurrency_ratio: float
    event_span_ms: float
    event_sum_ms: float
    event_union_ms: float
    group_size: int
    intervals: tuple[TicketInterval, ...]
    overlap_ms: float
    overlapping_pairs: int
    peak_concurrency: int
    wall_ns: int


@dataclass(frozen=True, slots=True)
class GroupSummary:
    """Retained raw observations and median attribution for one group."""

    group_size: int
    max_peak_concurrency: int
    median_concurrency_ratio: float
    median_event_span_ms: float
    median_event_sum_ms: float
    median_event_union_ms: float
    median_overlap_ms: float
    median_wall_ns: int
    overlap_samples: int
    pstdev_wall_ns: float
    raw: tuple[TimelineObservation, ...]


@dataclass(frozen=True, slots=True)
class _Measured:
    arch: str
    device_name: str
    groups: tuple[GroupSummary, ...]


def main() -> int:
    """Run grouped CUDA-event attribution and emit JSON evidence.

    Returns:
        Zero after every exact output and identity check passes.

    """
    prepared = _prepared_workload()
    expected = _reference_words(prepared)
    measured = _measure(prepared, expected)
    groups = {str(group.group_size): group for group in measured.groups}
    payload = {
        "benchmark_id": BENCHMARK_ID,
        "hypothesis": HYPOTHESIS,
        "rejection_rule": REJECTION_RULE,
        "interpretation_limit": INTERPRETATION_LIMIT,
        "workload": {
            "count_per_ticket": CORPUS_SIZE,
            "group_sizes": GROUP_SIZES,
            "identity": WORKLOAD_ID,
            "kind": PrimitiveKind.CRAZY.value,
            "sha256": _workload_sha256(prepared),
            "total_words_by_group": {
                str(size): size * CORPUS_SIZE for size in GROUP_SIZES
            },
        },
        "measurement": {
            "adapter_setup_timed": False,
            "event_origin_setup_timed": False,
            "ordering": ROUTE_ORDER,
            "overlap_epsilon_ms": OVERLAP_EPSILON_MS,
            "preparation_timed": False,
            "sample_count": SAMPLE_COUNT,
            "timeline_close_timed": False,
            "validation_timed": False,
            "warmup_count": WARMUP_COUNT,
        },
        "device": {
            "arch": measured.arch,
            "backend": CUDA_BACKEND_ID,
            "name": measured.device_name,
        },
        "identities": {
            "kernel_launch": _validated_identity(
                cuda_independent_kernel_launch_id(),
                EXPECTED_LAUNCH_ID,
                "kernel-launch",
            ),
            "kernel_timeline": _validated_identity(
                cuda_independent_kernel_timeline_id(),
                EXPECTED_TIMELINE_ID,
                "kernel-timeline",
            ),
            "prepared_storage": _validated_identity(
                prepared_primitive_storage_id(),
                EXPECTED_STORAGE_ID,
                "prepared-storage",
            ),
        },
        "groups": {key: asdict(value) for key, value in groups.items()},
        "hypothesis_outcome": _hypothesis_outcome(
            groups[str(HYPOTHESIS_GROUP_SIZE)]
        ),
    }
    _ = sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _prepared_workload() -> PreparedPrimitiveBatch:
    data = b"".join(
        value.to_bytes(WORD_BYTES, "little") for value in range(CORPUS_SIZE)
    )
    prepared = prepare_packed_primitive_batch(
        accumulators_u32le=b"\0" * len(data),
        data_u32le=data,
        kind=PrimitiveKind.CRAZY,
    )
    if prepared.count() != CORPUS_SIZE:
        message = "independent ticket timeline workload cardinality drifted"
        raise RuntimeError(message)
    return prepared


def _workload_sha256(prepared: PreparedPrimitiveBatch) -> str:
    validated = prepared.validated_storage()
    digest = sha256()
    digest.update(validated.kind.value.encode("ascii"))
    digest.update(b"\0")
    digest.update(validated.accumulators_u32le)
    digest.update(validated.data_u32le)
    return digest.hexdigest()


def _reference_words(prepared: PreparedPrimitiveBatch) -> bytes:
    result = CpuExactPrimitiveAdapter().evaluate_prepared(prepared)
    words = _packed_words(result)
    expected_bytes = CORPUS_SIZE * WORD_BYTES
    if len(words) != expected_bytes:
        message = "independent ticket timeline CPU reference size drifted"
        raise RuntimeError(message)
    return words


def _measure(prepared: PreparedPrimitiveBatch, expected: bytes) -> _Measured:
    with CudaExactPrimitiveAdapter() as adapter:
        for group_size in GROUP_SIZES:
            _warmup(
                adapter,
                prepared,
                expected=expected,
                group_size=group_size,
            )
        raw: dict[int, list[TimelineObservation]] = {
            size: [] for size in GROUP_SIZES
        }
        for sample_index in range(SAMPLE_COUNT):
            first = sample_index % len(GROUP_SIZES)
            ordered = GROUP_SIZES[first:] + GROUP_SIZES[:first]
            for group_size in ordered:
                raw[group_size].append(
                    _observe_group(
                        adapter,
                        prepared,
                        expected=expected,
                        group_size=group_size,
                    )
                )
        capability = adapter.capability()
    return _Measured(
        arch=capability.device_arch,
        device_name=capability.device_name,
        groups=tuple(_summary(size, raw[size]) for size in GROUP_SIZES),
    )


def _warmup(
    adapter: CudaExactPrimitiveAdapter,
    prepared: PreparedPrimitiveBatch,
    *,
    expected: bytes,
    group_size: int,
) -> None:
    for _ in range(WARMUP_COUNT):
        _ = _observe_group(
            adapter,
            prepared,
            expected=expected,
            group_size=group_size,
        )


def _observe_group(
    adapter: CudaExactPrimitiveAdapter,
    prepared: PreparedPrimitiveBatch,
    *,
    expected: bytes,
    group_size: int,
) -> TimelineObservation:
    timeline = adapter.ticket_timelines.create()
    try:
        start = perf_counter_ns()
        tickets = [timeline.submit(prepared) for _ in range(group_size)]
        results = tuple(ticket.wait() for ticket in reversed(tickets))
        wall_ns = perf_counter_ns() - start
        samples = timeline.samples()
        _validate_results(results, group_size, expected)
        return _observation(samples, group_size, wall_ns)
    finally:
        timeline.close()


def _observation(
    samples: tuple[CudaIndependentKernelTimelineSample, ...],
    group_size: int,
    wall_ns: int,
) -> TimelineObservation:
    intervals = tuple(
        TicketInterval(
            duration_ms=sample.duration_ms,
            end_ms=sample.end_ms,
            start_ms=sample.start_ms,
            submission_index=sample.submission_index,
        )
        for sample in samples
    )
    _validate_intervals(intervals, group_size)
    widths = tuple(
        interval.end_ms - interval.start_ms for interval in intervals
    )
    event_sum_ms = sum(widths)
    event_union_ms = _interval_union_ms(intervals)
    overlap_ms = max(0.0, event_sum_ms - event_union_ms)
    return TimelineObservation(
        concurrency_ratio=(
            event_sum_ms / event_union_ms if event_union_ms > 0.0 else 0.0
        ),
        event_span_ms=(
            max(interval.end_ms for interval in intervals)
            - min(interval.start_ms for interval in intervals)
        ),
        event_sum_ms=event_sum_ms,
        event_union_ms=event_union_ms,
        group_size=group_size,
        intervals=intervals,
        overlap_ms=overlap_ms,
        overlapping_pairs=_overlapping_pairs(intervals),
        peak_concurrency=_peak_concurrency(intervals),
        wall_ns=wall_ns,
    )


def _interval_union_ms(intervals: tuple[TicketInterval, ...]) -> float:
    ordered = sorted(
        (interval.start_ms, interval.end_ms) for interval in intervals
    )
    start, end = ordered[0]
    union_ms = 0.0
    for next_start, next_end in ordered[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            union_ms += end - start
            start, end = next_start, next_end
    return union_ms + end - start


def _overlapping_pairs(intervals: tuple[TicketInterval, ...]) -> int:
    return sum(
        min(first.end_ms, second.end_ms) - max(first.start_ms, second.start_ms)
        > OVERLAP_EPSILON_MS
        for index, first in enumerate(intervals)
        for second in intervals[index + 1 :]
    )


def _peak_concurrency(intervals: tuple[TicketInterval, ...]) -> int:
    points = sorted(
        (
            *((interval.start_ms, 1) for interval in intervals),
            *((interval.end_ms, -1) for interval in intervals),
        ),
        key=itemgetter(0, 1),
    )
    active = 0
    peak = 0
    for _, delta in points:
        active += delta
        peak = max(peak, active)
    return peak


def _validate_intervals(
    intervals: tuple[TicketInterval, ...],
    group_size: int,
) -> None:
    if len(intervals) != group_size:
        message = "independent ticket timeline interval count drifted"
        raise RuntimeError(message)
    for index, interval in enumerate(intervals):
        _validate_interval(index, interval)


def _validate_interval(index: int, interval: TicketInterval) -> None:
    if interval.submission_index != index:
        message = "independent ticket timeline changed submission order"
        raise RuntimeError(message)
    if interval.start_ms < 0.0 or interval.end_ms < interval.start_ms:
        message = "independent ticket timeline returned an invalid endpoint"
        raise RuntimeError(message)
    if interval.duration_ms < 0.0:
        message = "independent ticket timeline returned a negative duration"
        raise RuntimeError(message)


def _validate_results(
    results: tuple[PackedPrimitiveResult, ...],
    group_size: int,
    expected: bytes,
) -> None:
    if len(results) != group_size:
        message = "independent ticket timeline returned the wrong result count"
        raise RuntimeError(message)
    for result in results:
        if result.capability.backend_id != CUDA_BACKEND_ID:
            message = "independent ticket timeline changed backend identity"
            raise RuntimeError(message)
        if result.words_u32le != expected:
            message = (
                "independent ticket timeline changed exact primitive output"
            )
            raise RuntimeError(message)


def _packed_words(result: PrimitiveExecutionResult) -> bytes:
    if isinstance(result, PackedPrimitiveResult):
        return result.words_u32le
    return b"".join(
        value.to_bytes(WORD_BYTES, "little") for value in result.values
    )


def _summary(
    group_size: int,
    observations: list[TimelineObservation],
) -> GroupSummary:
    if len(observations) != SAMPLE_COUNT:
        message = "independent ticket timeline retained the wrong sample count"
        raise RuntimeError(message)
    wall = tuple(observation.wall_ns for observation in observations)
    return GroupSummary(
        group_size=group_size,
        max_peak_concurrency=max(
            observation.peak_concurrency for observation in observations
        ),
        median_concurrency_ratio=median(
            observation.concurrency_ratio for observation in observations
        ),
        median_event_span_ms=median(
            observation.event_span_ms for observation in observations
        ),
        median_event_sum_ms=median(
            observation.event_sum_ms for observation in observations
        ),
        median_event_union_ms=median(
            observation.event_union_ms for observation in observations
        ),
        median_overlap_ms=median(
            observation.overlap_ms for observation in observations
        ),
        median_wall_ns=int(median(wall)),
        overlap_samples=sum(
            observation.overlap_ms > OVERLAP_EPSILON_MS
            and observation.overlapping_pairs > 0
            for observation in observations
        ),
        pstdev_wall_ns=pstdev(wall),
        raw=tuple(observations),
    )


def _hypothesis_outcome(group: GroupSummary) -> dict[str, object]:
    if group.group_size != HYPOTHESIS_GROUP_SIZE:
        message = (
            "independent ticket timeline selected the wrong hypothesis group"
        )
        raise RuntimeError(message)
    passed = (
        group.overlap_samples > SAMPLE_COUNT // 2
        and group.median_overlap_ms > OVERLAP_EPSILON_MS
        and group.max_peak_concurrency > 1
    )
    return {
        "group_size": group.group_size,
        "passed": passed,
        "reason": (
            "significant event-interval overlap observed"
            if passed
            else "significant event-interval overlap not observed"
        ),
    }


def _validated_identity(
    identifier: str,
    expected: str,
    label: str,
) -> str:
    if identifier != expected:
        message = f"independent ticket {label} identity drifted"
        raise RuntimeError(message)
    return identifier


if __name__ == "__main__":
    raise SystemExit(main())
