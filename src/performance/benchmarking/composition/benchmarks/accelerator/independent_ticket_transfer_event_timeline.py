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
#   - CUDA-event upload/kernel/download attribution for streamed tickets.
# - Must-Not:
#   - Treat event overlap as engine occupancy or change exact semantics.
# - Allows:
#   - Inputs: the full-domain CRAZY workload and groups 2/4/8.
#   - Outputs: raw phase intervals, cross-phase overlap, wall time, identities.
#   - Side effects: scoped CUDA execution and JSON output only.
# - Split-When:
#   - Split when admission policy or another workload needs a new protocol.
# - Merge-When:
#   - Merge when another benchmark owns this exact phase-overlap question.
# - Summary:
#   - Independent CUDA ticket transfer-event timeline benchmark.
# - Description:
#   - Tests whether transfer and kernel phase intervals overlap across tickets.
# - Usage:
#   - Run from a clean commit and retain output under accelerator evidence.
# - Defaults:
#   - One warmup and fifteen retained cyclic-order samples per group.
#

"""CUDA-event transfer/kernel phase attribution for streamed tickets."""

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
from accelerator.cuda import cuda_independent_kernel_launch_id
from accelerator.cuda import cuda_independent_ticket_transfer_id
from accelerator.cuda import cuda_independent_ticket_transfer_timeline_id
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PackedPrimitiveResult
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import prepare_packed_primitive_batch
from accelerator.exact_primitives import prepared_primitive_storage_id

if TYPE_CHECKING:
    from accelerator.cuda import CudaIndependentTicketTransferTimelineSample
    from accelerator.cuda import CudaPrimitiveEvaluationTicket
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
WORKLOAD_ID: Final = "classic-crazy-full-domain-ticket-transfer-v1"
BENCHMARK_ID: Final = "cuda-independent-ticket-transfer-event-timeline-v1"
EXPECTED_LAUNCH_ID: Final = "cuda-independent-stream-kernel-launch-v1"
EXPECTED_TRANSFER_ID: Final = "cuda-independent-stream-ticket-transfer-v1"
EXPECTED_TIMELINE_ID: Final = (
    "cuda-independent-stream-ticket-transfer-timeline-v1"
)
EXPECTED_STORAGE_ID: Final = "proof-bound-u32le-primitive-input-v1"
ROUTE_ORDER: Final = "cyclic first-group rotation across groups 2, 4, and 8"
HYPOTHESIS: Final = (
    "group-eight streamed tickets produce more than one microsecond of "
    "CUDA-event transfer/kernel phase overlap in more than seven samples"
)
REJECTION_RULE: Final = (
    "reject transfer/kernel overlap attribution when group eight has at most "
    "seven significant samples, median overlap is not above one microsecond, "
    "or any exact identity/output/phase-order check fails"
)
INTERPRETATION_LIMIT: Final = (
    "origin-relative CUDA-event phases describe observed stream intervals; "
    "they do not prove copy-engine occupancy or uninstrumented performance"
)


@dataclass(frozen=True, slots=True)
class TicketPhases:
    """One retained streamed ticket's origin-relative event phases."""

    download_duration_ms: float
    end_ms: float
    kernel_duration_ms: float
    kernel_end_ms: float
    start_ms: float
    submission_index: int
    total_duration_ms: float
    upload_duration_ms: float
    upload_end_ms: float


@dataclass(frozen=True, slots=True)
class PhaseObservation:
    """One grouped streamed route with cross-ticket phase attribution."""

    download_sum_ms: float
    group_size: int
    kernel_download_overlap_ms: float
    kernel_sum_ms: float
    tickets: tuple[TicketPhases, ...]
    transfer_kernel_overlap_ms: float
    upload_download_overlap_ms: float
    upload_kernel_overlap_ms: float
    upload_sum_ms: float
    wall_ns: int


@dataclass(frozen=True, slots=True)
class GroupSummary:
    """Retained raw observations and medians for one ticket group."""

    group_size: int
    median_download_sum_ms: float
    median_kernel_download_overlap_ms: float
    median_kernel_sum_ms: float
    median_transfer_kernel_overlap_ms: float
    median_upload_download_overlap_ms: float
    median_upload_kernel_overlap_ms: float
    median_upload_sum_ms: float
    median_wall_ns: int
    pstdev_wall_ns: float
    raw: tuple[PhaseObservation, ...]
    transfer_kernel_overlap_samples: int


@dataclass(frozen=True, slots=True)
class _Measured:
    arch: str
    device_name: str
    groups: tuple[GroupSummary, ...]


def main() -> int:
    """Run transfer/kernel CUDA-event attribution and emit JSON evidence.

    Returns:
        Zero after every exact output, identity, and phase check passes.

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
                "kernel launch",
            ),
            "prepared_storage": _validated_identity(
                prepared_primitive_storage_id(),
                EXPECTED_STORAGE_ID,
                "prepared storage",
            ),
            "streamed_transfer": _validated_identity(
                cuda_independent_ticket_transfer_id(),
                EXPECTED_TRANSFER_ID,
                "streamed transfer",
            ),
            "transfer_timeline": _validated_identity(
                cuda_independent_ticket_transfer_timeline_id(),
                EXPECTED_TIMELINE_ID,
                "transfer timeline",
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
        message = "ticket transfer timeline workload cardinality drifted"
        raise RuntimeError(message)
    return prepared


def _workload_sha256(prepared: PreparedPrimitiveBatch) -> str:
    storage = prepared.validated_storage()
    digest = sha256()
    digest.update(storage.kind.value.encode("ascii"))
    digest.update(b"\0")
    digest.update(storage.accumulators_u32le)
    digest.update(storage.data_u32le)
    return digest.hexdigest()


def _reference_words(prepared: PreparedPrimitiveBatch) -> bytes:
    result = CpuExactPrimitiveAdapter().evaluate_prepared(prepared)
    words = _packed_words(result)
    expected_bytes = CORPUS_SIZE * WORD_BYTES
    if len(words) != expected_bytes:
        message = "ticket transfer timeline CPU reference size drifted"
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
        raw: dict[int, list[PhaseObservation]] = {
            size: [] for size in GROUP_SIZES
        }
        for sample_index in range(SAMPLE_COUNT):
            first = sample_index % len(GROUP_SIZES)
            for group_size in GROUP_SIZES[first:] + GROUP_SIZES[:first]:
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
) -> PhaseObservation:
    timeline = adapter.ticket_transfer_timelines.create()
    tickets: list[CudaPrimitiveEvaluationTicket] = []
    try:
        start = perf_counter_ns()
        tickets.extend(timeline.submit(prepared) for _ in range(group_size))
        results = tuple(ticket.wait() for ticket in reversed(tickets))
        wall_ns = perf_counter_ns() - start
        samples = timeline.samples()
        _validate_results(results, group_size, expected)
        return _observation(samples, group_size, wall_ns)
    finally:
        for ticket in reversed(tickets):
            ticket.close()
        timeline.close()


def _observation(
    samples: tuple[CudaIndependentTicketTransferTimelineSample, ...],
    group_size: int,
    wall_ns: int,
) -> PhaseObservation:
    tickets = tuple(_ticket_phases(sample) for sample in samples)
    _validate_tickets(tickets, group_size)
    uploads = tuple(
        (ticket.start_ms, ticket.upload_end_ms) for ticket in tickets
    )
    kernels = tuple(
        (ticket.upload_end_ms, ticket.kernel_end_ms) for ticket in tickets
    )
    downloads = tuple(
        (ticket.kernel_end_ms, ticket.end_ms) for ticket in tickets
    )
    transfers = uploads + downloads
    return PhaseObservation(
        download_sum_ms=sum(ticket.download_duration_ms for ticket in tickets),
        group_size=group_size,
        kernel_download_overlap_ms=_union_intersection_ms(kernels, downloads),
        kernel_sum_ms=sum(ticket.kernel_duration_ms for ticket in tickets),
        tickets=tickets,
        transfer_kernel_overlap_ms=_union_intersection_ms(transfers, kernels),
        upload_download_overlap_ms=_union_intersection_ms(uploads, downloads),
        upload_kernel_overlap_ms=_union_intersection_ms(uploads, kernels),
        upload_sum_ms=sum(ticket.upload_duration_ms for ticket in tickets),
        wall_ns=wall_ns,
    )


def _ticket_phases(
    sample: CudaIndependentTicketTransferTimelineSample,
) -> TicketPhases:
    return TicketPhases(
        download_duration_ms=sample.download_duration_ms,
        end_ms=sample.end_ms,
        kernel_duration_ms=sample.kernel_duration_ms,
        kernel_end_ms=sample.kernel_end_ms,
        start_ms=sample.start_ms,
        submission_index=sample.submission_index,
        total_duration_ms=sample.total_duration_ms,
        upload_duration_ms=sample.upload_duration_ms,
        upload_end_ms=sample.upload_end_ms,
    )


def _union_intersection_ms(
    first: tuple[tuple[float, float], ...],
    second: tuple[tuple[float, float], ...],
) -> float:
    left = _merge_intervals(first)
    right = _merge_intervals(second)
    total = 0.0
    left_index = 0
    right_index = 0
    while left_index < len(left) and right_index < len(right):
        left_start, left_end = left[left_index]
        right_start, right_end = right[right_index]
        total += max(
            0.0,
            min(left_end, right_end) - max(left_start, right_start),
        )
        if left_end <= right_end:
            left_index += 1
        else:
            right_index += 1
    return total


def _merge_intervals(
    intervals: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...]:
    ordered = sorted(intervals)
    if not ordered:
        return ()
    merged: list[tuple[float, float]] = []
    start, end = ordered[0]
    for next_start, next_end in ordered[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            merged.append((start, end))
            start, end = next_start, next_end
    merged.append((start, end))
    return tuple(merged)


def _validate_tickets(
    tickets: tuple[TicketPhases, ...],
    group_size: int,
) -> None:
    if len(tickets) != group_size:
        message = "ticket transfer timeline phase count drifted"
        raise RuntimeError(message)
    for index, ticket in enumerate(tickets):
        _validate_ticket(index, ticket)


def _validate_ticket(index: int, ticket: TicketPhases) -> None:
    if ticket.submission_index != index:
        message = "ticket transfer timeline changed submission order"
        raise RuntimeError(message)
    if not (
        0.0
        <= ticket.start_ms
        <= ticket.upload_end_ms
        <= ticket.kernel_end_ms
        <= ticket.end_ms
    ):
        message = "ticket transfer timeline returned unordered phases"
        raise RuntimeError(message)
    durations = (
        ticket.upload_duration_ms,
        ticket.kernel_duration_ms,
        ticket.download_duration_ms,
        ticket.total_duration_ms,
    )
    if any(duration < 0.0 for duration in durations):
        message = "ticket transfer timeline returned negative duration"
        raise RuntimeError(message)


def _validate_results(
    results: tuple[PackedPrimitiveResult, ...],
    group_size: int,
    expected: bytes,
) -> None:
    if len(results) != group_size:
        message = "ticket transfer timeline returned the wrong result count"
        raise RuntimeError(message)
    for result in results:
        if result.capability.backend_id != CUDA_BACKEND_ID:
            message = "ticket transfer timeline changed backend identity"
            raise RuntimeError(message)
        if result.words_u32le != expected:
            message = "ticket transfer timeline changed exact primitive output"
            raise RuntimeError(message)


def _packed_words(result: PrimitiveExecutionResult) -> bytes:
    if isinstance(result, PackedPrimitiveResult):
        return result.words_u32le
    return b"".join(
        value.to_bytes(WORD_BYTES, "little") for value in result.values
    )


def _summary(
    group_size: int,
    observations: list[PhaseObservation],
) -> GroupSummary:
    if len(observations) != SAMPLE_COUNT:
        message = "ticket transfer timeline retained the wrong sample count"
        raise RuntimeError(message)
    wall = tuple(observation.wall_ns for observation in observations)
    return GroupSummary(
        group_size=group_size,
        median_download_sum_ms=median(
            observation.download_sum_ms for observation in observations
        ),
        median_kernel_download_overlap_ms=median(
            observation.kernel_download_overlap_ms
            for observation in observations
        ),
        median_kernel_sum_ms=median(
            observation.kernel_sum_ms for observation in observations
        ),
        median_transfer_kernel_overlap_ms=median(
            observation.transfer_kernel_overlap_ms
            for observation in observations
        ),
        median_upload_download_overlap_ms=median(
            observation.upload_download_overlap_ms
            for observation in observations
        ),
        median_upload_kernel_overlap_ms=median(
            observation.upload_kernel_overlap_ms for observation in observations
        ),
        median_upload_sum_ms=median(
            observation.upload_sum_ms for observation in observations
        ),
        median_wall_ns=int(median(wall)),
        pstdev_wall_ns=pstdev(wall),
        raw=tuple(observations),
        transfer_kernel_overlap_samples=sum(
            observation.transfer_kernel_overlap_ms > OVERLAP_EPSILON_MS
            for observation in observations
        ),
    )


def _hypothesis_outcome(group: GroupSummary) -> dict[str, object]:
    if group.group_size != HYPOTHESIS_GROUP_SIZE:
        message = "ticket transfer timeline selected the wrong hypothesis group"
        raise RuntimeError(message)
    passed = (
        group.transfer_kernel_overlap_samples > SAMPLE_COUNT // 2
        and group.median_transfer_kernel_overlap_ms > OVERLAP_EPSILON_MS
    )
    return {
        "group_size": group.group_size,
        "passed": passed,
        "reason": (
            "significant transfer/kernel event overlap observed"
            if passed
            else "significant transfer/kernel event overlap not observed"
        ),
    }


def _validated_identity(identifier: str, expected: str, label: str) -> str:
    if identifier != expected:
        message = f"ticket transfer {label} identity drifted"
        raise RuntimeError(message)
    return identifier


if __name__ == "__main__":
    raise SystemExit(main())
