# File:
#   - ticket_admission_telemetry.py
# Path:
#   - accelerator/ticket_admission_telemetry.py
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
#   - Bounded caller-owned observations of completed and failed ticket plans.
# - Must-Not:
#   - Change admission, read benchmarks, learn routes, or create hidden threads.
# - Allows:
#   - Inputs: validated reports, durations, and accelerator failures.
#   - Outputs: immutable ordered telemetry snapshots with explicit eviction.
#   - Side effects: bounded in-memory recorder mutation only.
# - Split-When:
#   - Split when persistence or adaptive policy gains its own lifecycle.
# - Merge-When:
#   - Merge when another module owns these exact bounded observations.
# - Summary:
#   - Bounded opt-in ticket admission telemetry.
# - Description:
#   - Records completion and stable failure categories without policy authority.
# - Usage:
#   - Construct explicitly, pass to an instrumented executor, then snapshot.
# - Defaults:
#   - No recorder exists unless a caller opts in; malformed input fails closed.
#
# Related documents:
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Bounded opt-in telemetry for completed and failed ticket plans."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final
from typing import NoReturn
from typing import TYPE_CHECKING
from typing import final

from accelerator.exact_primitives import AcceleratorError
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import InvalidPrimitiveBatchError
from accelerator.ticket_admission import TicketSubmissionMode
from accelerator.ticket_admission import ticket_route_admission_id
from accelerator.ticket_admission import ticket_route_admission_report_id

if TYPE_CHECKING:
    from accelerator.ticket_admission import TicketAdmissionReport
    from accelerator.ticket_admission import TicketRouteAssessment
    from accelerator.ticket_admission import TicketSubmissionChunk

TICKET_ADMISSION_TELEMETRY_ID: Final = "bounded-ticket-admission-telemetry-v1"
TICKET_ADMISSION_FAILURE_TELEMETRY_ID: Final = (
    "bounded-ticket-admission-failure-telemetry-v1"
)


class TicketAdmissionTelemetryError(ValueError):
    """Ticket admission telemetry input or retained state is invalid."""


class TicketAdmissionFailureKind(StrEnum):
    """Stable accelerator failure category retained without error text."""

    EXECUTION = "accelerator-execution"
    INVALID_INPUT = "invalid-input"
    OTHER = "accelerator-error"
    UNAVAILABLE = "accelerator-unavailable"


@dataclass(frozen=True, slots=True)
class TicketAdmissionObservation:
    """One completed admission plan observed by a caller-owned clock."""

    admission_id: str
    backend_id: str
    chunk_count: int
    device_arch: str
    device_name: str
    elapsed_ns: int
    estimate_delta_ns: int
    estimated_ns: int
    fallback_ticket_count: int
    report_id: str
    selected_evidence_ids: tuple[str, ...]
    selected_streamed_ticket_count: int
    selected_synchronous_ticket_count: int
    sequence_id: int
    ticket_count: int
    workload_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetrySnapshot:
    """Immutable bounded recorder state at one caller-selected instant."""

    capacity: int
    dropped_observation_count: int
    next_sequence_id: int
    observations: tuple[TicketAdmissionObservation, ...]
    telemetry_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionFailureObservation:
    """One failed execution attempt with a stable non-message category."""

    admission_id: str
    backend_id: str
    chunk_count: int
    device_arch: str
    device_name: str
    elapsed_ns: int
    estimate_delta_ns: int
    estimated_ns: int
    failure_kind: TicketAdmissionFailureKind
    fallback_ticket_count: int
    report_id: str
    selected_evidence_ids: tuple[str, ...]
    selected_streamed_ticket_count: int
    selected_synchronous_ticket_count: int
    sequence_id: int
    ticket_count: int
    workload_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionFailureTelemetrySnapshot:
    """Immutable bounded failed-attempt recorder state."""

    capacity: int
    dropped_observation_count: int
    next_sequence_id: int
    observations: tuple[TicketAdmissionFailureObservation, ...]
    telemetry_id: str


@final
class TicketAdmissionTelemetry:
    """Caller-owned bounded FIFO recorder with no adaptive authority."""

    __slots__ = (
        "_capacity",
        "_dropped_observation_count",
        "_next_sequence_id",
        "_observations",
    )

    def __init__(self, capacity: int) -> None:
        """Create one bounded recorder."""
        self._capacity = _validated_capacity(capacity)
        self._dropped_observation_count = 0
        self._next_sequence_id = 0
        self._observations: list[TicketAdmissionObservation] = []

    def record_completed(
        self,
        report: TicketAdmissionReport,
        *,
        elapsed_ns: int,
    ) -> TicketAdmissionObservation:
        """Record one fully completed plan without changing its policy.

        Returns:
            Immutable appended observation.

        """
        observation = _completed_observation(
            report,
            elapsed_ns=elapsed_ns,
            sequence_id=self._next_sequence_id,
        )
        if len(self._observations) == self._capacity:
            del self._observations[0]
            self._dropped_observation_count += 1
        self._observations.append(observation)
        self._next_sequence_id += 1
        return observation

    def snapshot(self) -> TicketAdmissionTelemetrySnapshot:
        """Return an immutable copy of current bounded telemetry state.

        Returns:
            Stable bounded snapshot.

        """
        return TicketAdmissionTelemetrySnapshot(
            capacity=self._capacity,
            dropped_observation_count=self._dropped_observation_count,
            next_sequence_id=self._next_sequence_id,
            observations=tuple(self._observations),
            telemetry_id=TICKET_ADMISSION_TELEMETRY_ID,
        )


@final
class TicketAdmissionFailureTelemetry:
    """Caller-owned bounded FIFO of failed execution attempts."""

    __slots__ = (
        "_capacity",
        "_dropped_observation_count",
        "_next_sequence_id",
        "_observations",
    )

    def __init__(self, capacity: int) -> None:
        """Create one bounded failed-attempt recorder."""
        self._capacity = _validated_capacity(capacity)
        self._dropped_observation_count = 0
        self._next_sequence_id = 0
        self._observations: list[TicketAdmissionFailureObservation] = []

    def record_failed(
        self,
        report: TicketAdmissionReport,
        *,
        elapsed_ns: int,
        error: object,
    ) -> TicketAdmissionFailureObservation:
        """Record one failed accelerator execution without error text.

        Returns:
            Immutable appended failed-attempt observation.

        """
        observation = _failed_observation(
            report,
            elapsed_ns=elapsed_ns,
            error=error,
            sequence_id=self._next_sequence_id,
        )
        if len(self._observations) == self._capacity:
            del self._observations[0]
            self._dropped_observation_count += 1
        self._observations.append(observation)
        self._next_sequence_id += 1
        return observation

    def snapshot(self) -> TicketAdmissionFailureTelemetrySnapshot:
        """Return an immutable copy of failed-attempt telemetry state.

        Returns:
            Stable bounded failed-attempt snapshot.

        """
        return TicketAdmissionFailureTelemetrySnapshot(
            capacity=self._capacity,
            dropped_observation_count=self._dropped_observation_count,
            next_sequence_id=self._next_sequence_id,
            observations=tuple(self._observations),
            telemetry_id=TICKET_ADMISSION_FAILURE_TELEMETRY_ID,
        )


@dataclass(frozen=True, slots=True)
class TicketAdmissionAttemptTelemetry:
    """Explicit completed/failed recorder pair for one executor boundary."""

    completed: TicketAdmissionTelemetry
    failed: TicketAdmissionFailureTelemetry

    def record_completed(
        self,
        report: TicketAdmissionReport,
        *,
        elapsed_ns: int,
    ) -> TicketAdmissionObservation:
        """Delegate one completed report to the completed FIFO.

        Returns:
            Immutable appended completion observation.

        """
        return self.completed.record_completed(report, elapsed_ns=elapsed_ns)

    def record_failed(
        self,
        report: TicketAdmissionReport,
        *,
        elapsed_ns: int,
        error: object,
    ) -> TicketAdmissionFailureObservation:
        """Delegate one accelerator failure to the failed FIFO.

        Returns:
            Immutable appended failed-attempt observation.

        """
        return self.failed.record_failed(
            report,
            elapsed_ns=elapsed_ns,
            error=error,
        )


def ticket_admission_telemetry_id() -> str:
    """Return the stable bounded ticket telemetry identity.

    Returns:
        Versioned completed-plan telemetry identity.

    """
    return TICKET_ADMISSION_TELEMETRY_ID


def ticket_admission_failure_telemetry_id() -> str:
    """Return the stable bounded failed-attempt telemetry identity.

    Returns:
        Versioned accelerator-failure telemetry identity.

    """
    return TICKET_ADMISSION_FAILURE_TELEMETRY_ID


def _validated_capacity(capacity: int) -> int:
    if type(capacity) is not int or capacity <= 0:
        _raise_telemetry("capacity must be a positive integer")
    return capacity


def _completed_observation(
    report: TicketAdmissionReport,
    *,
    elapsed_ns: int,
    sequence_id: int,
) -> TicketAdmissionObservation:
    if type(elapsed_ns) is not int or elapsed_ns < 0:
        message = "ticket admission elapsed time must be a non-negative integer"
        raise TicketAdmissionTelemetryError(message)
    _validate_report(report)
    plan = report.plan
    request = plan.request
    return TicketAdmissionObservation(
        admission_id=plan.admission_id,
        backend_id=request.backend_id,
        chunk_count=len(plan.chunks),
        device_arch=request.device_arch,
        device_name=request.device_name,
        elapsed_ns=elapsed_ns,
        estimate_delta_ns=elapsed_ns - plan.estimated_ns,
        estimated_ns=plan.estimated_ns,
        fallback_ticket_count=report.fallback_ticket_count,
        report_id=report.report_id,
        selected_evidence_ids=_selected_evidence_ids(report),
        selected_streamed_ticket_count=(
            report.selected_streamed_ticket_count
        ),
        selected_synchronous_ticket_count=(
            report.selected_synchronous_ticket_count
        ),
        sequence_id=sequence_id,
        ticket_count=request.ticket_count,
        workload_id=request.workload_id,
    )


def _failed_observation(
    report: TicketAdmissionReport,
    *,
    elapsed_ns: int,
    error: object,
    sequence_id: int,
) -> TicketAdmissionFailureObservation:
    if type(elapsed_ns) is not int or elapsed_ns < 0:
        message = "ticket admission elapsed time must be a non-negative integer"
        raise TicketAdmissionTelemetryError(message)
    if not isinstance(error, AcceleratorError):
        _raise_telemetry("failure must be an accelerator error")
    _validate_report(report)
    plan = report.plan
    request = plan.request
    return TicketAdmissionFailureObservation(
        admission_id=plan.admission_id,
        backend_id=request.backend_id,
        chunk_count=len(plan.chunks),
        device_arch=request.device_arch,
        device_name=request.device_name,
        elapsed_ns=elapsed_ns,
        estimate_delta_ns=elapsed_ns - plan.estimated_ns,
        estimated_ns=plan.estimated_ns,
        failure_kind=_failure_kind(error),
        fallback_ticket_count=report.fallback_ticket_count,
        report_id=report.report_id,
        selected_evidence_ids=_selected_evidence_ids(report),
        selected_streamed_ticket_count=(
            report.selected_streamed_ticket_count
        ),
        selected_synchronous_ticket_count=(
            report.selected_synchronous_ticket_count
        ),
        sequence_id=sequence_id,
        ticket_count=request.ticket_count,
        workload_id=request.workload_id,
    )


def _failure_kind(error: AcceleratorError) -> TicketAdmissionFailureKind:
    kind = TicketAdmissionFailureKind.OTHER
    if isinstance(error, AcceleratorUnavailableError):
        kind = TicketAdmissionFailureKind.UNAVAILABLE
    elif isinstance(error, InvalidPrimitiveBatchError):
        kind = TicketAdmissionFailureKind.INVALID_INPUT
    elif isinstance(error, AcceleratorExecutionError):
        kind = TicketAdmissionFailureKind.EXECUTION
    return kind


def _selected_evidence_ids(
    report: TicketAdmissionReport,
) -> tuple[str, ...]:
    return tuple(
        chunk.evidence_id
        for chunk in report.plan.chunks
        if chunk.evidence_id is not None
    )


def _validate_report(report: TicketAdmissionReport) -> None:
    if report.report_id != ticket_route_admission_report_id():
        _raise_telemetry("report identity mismatched")
    plan = report.plan
    if plan.admission_id != ticket_route_admission_id():
        _raise_telemetry("plan identity mismatched")
    _ = plan.request.validated()
    selected, aggregate = _validate_chunks(report)
    _validate_assessments(report.assessments, selected)
    observed = (
        report.fallback_ticket_count,
        report.selected_streamed_ticket_count,
        report.selected_synchronous_ticket_count,
    )
    if aggregate != observed:
        _raise_telemetry("aggregate counts mismatched")


def _validate_chunks(
    report: TicketAdmissionReport,
) -> tuple[dict[str, tuple[int, int]], tuple[int, int, int]]:
    cursor = 0
    estimated_ns = 0
    fallback = 0
    streamed = 0
    synchronous = 0
    selected: dict[str, tuple[int, int]] = {}
    for chunk in report.plan.chunks:
        cursor, estimate, contribution = _validated_chunk(chunk, cursor)
        estimated_ns += estimate
        fallback += contribution[0]
        streamed += contribution[1]
        synchronous += contribution[2]
        _record_selected_chunk(selected, chunk)
    request_count = report.plan.request.ticket_count
    if cursor != request_count:
        _raise_telemetry("plan does not cover its request")
    if estimated_ns != report.plan.estimated_ns:
        _raise_telemetry("plan estimate mismatched")
    aggregate = (fallback, streamed, synchronous)
    if sum(aggregate) != request_count:
        _raise_telemetry("ticket counts mismatched")
    return selected, aggregate


def _validated_chunk(
    chunk: TicketSubmissionChunk,
    cursor: int,
) -> tuple[int, int, tuple[int, int, int]]:
    _validate_chunk_shape(chunk, cursor)
    return chunk.stop, chunk.estimated_ns, _chunk_contribution(chunk)


def _validate_chunk_shape(
    chunk: TicketSubmissionChunk,
    cursor: int,
) -> None:
    if chunk.start != cursor or chunk.stop <= chunk.start:
        _raise_telemetry("plan chunks are not contiguous")
    if type(chunk.estimated_ns) is not int or chunk.estimated_ns <= 0:
        _raise_telemetry("chunk estimate must be positive")


def _chunk_contribution(
    chunk: TicketSubmissionChunk,
) -> tuple[int, int, int]:
    ticket_count = chunk.ticket_count
    if chunk.evidence_id is None:
        if chunk.mode is not TicketSubmissionMode.SYNCHRONOUS:
            _raise_telemetry("fallback mode is invalid")
        return ticket_count, 0, 0
    if chunk.mode is TicketSubmissionMode.STREAMED:
        return 0, ticket_count, 0
    return 0, 0, ticket_count


def _record_selected_chunk(
    selected: dict[str, tuple[int, int]],
    chunk: TicketSubmissionChunk,
) -> None:
    evidence_id = chunk.evidence_id
    if evidence_id is None:
        return
    chunk_count, ticket_count = selected.get(evidence_id, (0, 0))
    selected[evidence_id] = (
        chunk_count + 1,
        ticket_count + chunk.ticket_count,
    )


def _validate_assessments(
    assessments: tuple[TicketRouteAssessment, ...],
    selected: dict[str, tuple[int, int]],
) -> None:
    eligible_ids: set[str] = set()
    for assessment in assessments:
        _validate_assessment_shape(assessment)
        if not assessment.eligible:
            _validate_rejected_assessment(assessment)
            continue
        evidence_id = assessment.evidence_id
        if evidence_id in eligible_ids:
            _raise_telemetry("duplicate eligible route")
        eligible_ids.add(evidence_id)
        _validate_selected_usage(assessment, selected)
    if not set(selected).issubset(eligible_ids):
        _raise_telemetry("selected route is unexplained")


def _validate_rejected_assessment(
    assessment: TicketRouteAssessment,
) -> None:
    if assessment.selected_chunk_count or assessment.selected_ticket_count:
        _raise_telemetry("rejected route has selected counts")


def _validate_selected_usage(
    assessment: TicketRouteAssessment,
    selected: dict[str, tuple[int, int]],
) -> None:
    expected = selected.get(assessment.evidence_id, (0, 0))
    observed = (
        assessment.selected_chunk_count,
        assessment.selected_ticket_count,
    )
    if expected != observed:
        _raise_telemetry("route usage mismatched")


def _validate_assessment_shape(assessment: TicketRouteAssessment) -> None:
    if not assessment.evidence_id:
        _raise_telemetry("evidence identity must not be empty")
    _validate_positive_assessment_counts(assessment)
    _validate_nonnegative_assessment_counts(assessment)
    if assessment.paired_wins > assessment.sample_count:
        _raise_telemetry("paired wins are inconsistent")
    if type(assessment.exact_results) is not bool:
        _raise_telemetry("exact-result flag is invalid")


def _validate_positive_assessment_counts(
    assessment: TicketRouteAssessment,
) -> None:
    values = (
        assessment.candidate_median_ns,
        assessment.group_size,
        assessment.reference_median_ns,
        assessment.sample_count,
    )
    if any(type(value) is not int or value <= 0 for value in values):
        _raise_telemetry("assessment evidence is invalid")


def _validate_nonnegative_assessment_counts(
    assessment: TicketRouteAssessment,
) -> None:
    values = (
        assessment.paired_wins,
        assessment.selected_chunk_count,
        assessment.selected_ticket_count,
    )
    if any(type(value) is not int or value < 0 for value in values):
        _raise_telemetry("assessment counts are invalid")


def _raise_telemetry(detail: str) -> NoReturn:
    message = f"ticket admission telemetry {detail}"
    raise TicketAdmissionTelemetryError(message)
