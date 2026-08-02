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
#   - Evidence-bound ticket route/group admission and explanations.
# - Must-Not:
#   - Infer support from a GPU name alone or bypass exact-result evidence.
# - Allows:
#   - Inputs: one exact request context and retained paired route candidates.
#   - Outputs: deterministic plans and opt-in immutable reports.
#   - Side effects: none.
# - Split-When:
#   - Split when online learning or queue telemetry gains its own lifecycle.
# - Merge-When:
#   - Merge when another module owns this exact evidence admission policy.
# - Summary:
#   - Conservative evidence-bound ticket route admission.
# - Description:
#   - Selects measured groups and explains eligibility without learning.
# - Usage:
#   - Called by backend-specific profiles; ordinary fallback remains
#     synchronous.
# - Defaults:
#   - Missing, mismatched, or negative evidence yields singleton sync chunks.
#

"""Conservative evidence-bound accelerator ticket route admission."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

TICKET_ROUTE_ADMISSION_ID: Final = "evidence-bound-ticket-route-admission-v1"
TICKET_ROUTE_ADMISSION_REPORT_ID: Final = (
    "evidence-bound-ticket-route-admission-report-v1"
)


class TicketAdmissionError(ValueError):
    """Ticket admission inputs or retained evidence are invalid."""


class TicketSubmissionMode(StrEnum):
    """Host-transfer lifetime selected for one admitted ticket chunk."""

    SYNCHRONOUS = "synchronous"
    STREAMED = "streamed"


class TicketRouteRejection(StrEnum):
    """Stable reason one validated route was not eligible for planning."""

    CONTEXT_MISMATCH = "context-mismatch"
    GROUP_EXCEEDS_QUEUE = "group-exceeds-queue"
    INEXACT_RESULTS = "inexact-results"
    NO_MEDIAN_IMPROVEMENT = "no-median-improvement"
    NO_PAIRED_MAJORITY = "no-paired-majority"


@dataclass(frozen=True, slots=True)
class TicketAdmissionRequest:
    """Exact workload and device context for one pending ticket queue."""

    backend_id: str
    device_arch: str
    device_name: str
    ticket_count: int
    workload_id: str

    def validated(self) -> TicketAdmissionRequest:
        """Validate one exact admission context.

        Returns:
            The unchanged request.

        Raises:
            TicketAdmissionError: If an identity or count is invalid.

        """
        for label, value in (
            ("backend", self.backend_id),
            ("device architecture", self.device_arch),
            ("device name", self.device_name),
            ("workload", self.workload_id),
        ):
            if not value:
                message = f"ticket admission {label} identity must not be empty"
                raise TicketAdmissionError(message)
        if type(self.ticket_count) is not int or self.ticket_count < 0:
            message = "ticket admission count must be a non-negative integer"
            raise TicketAdmissionError(message)
        return self


@dataclass(frozen=True, slots=True)
class TicketRouteCandidate:
    """One retained same-work route comparison offered for admission."""

    backend_id: str
    benchmark_id: str
    candidate_median_ns: int
    device_arch: str
    device_name: str
    exact_results: bool
    group_size: int
    mode: TicketSubmissionMode
    paired_wins: int
    reference_median_ns: int
    sample_count: int
    workload_id: str

    def validated(self) -> TicketRouteCandidate:
        """Validate retained comparison shape and identities.

        Returns:
            The unchanged candidate.

        """
        _validate_candidate_identities(self)
        _validate_candidate_counts(self)
        _validate_candidate_measurements(self)
        return self

    @property
    def admitted(self) -> bool:
        """Whether this comparison passes conservative promotion.

        Returns:
            True only for exact, median-improving, majority-win evidence.

        """
        return (
            self.exact_results
            and self.candidate_median_ns < self.reference_median_ns
            and self.paired_wins > self.sample_count // 2
        )


def _validate_candidate_identities(candidate: TicketRouteCandidate) -> None:
    for label, value in (
        ("backend", candidate.backend_id),
        ("benchmark", candidate.benchmark_id),
        ("device architecture", candidate.device_arch),
        ("device name", candidate.device_name),
        ("workload", candidate.workload_id),
    ):
        if not value:
            message = f"ticket candidate {label} identity must not be empty"
            raise TicketAdmissionError(message)


def _validate_candidate_counts(candidate: TicketRouteCandidate) -> None:
    if type(candidate.group_size) is not int or candidate.group_size <= 0:
        message = "ticket candidate group size must be a positive integer"
        raise TicketAdmissionError(message)
    if type(candidate.sample_count) is not int or candidate.sample_count <= 0:
        message = "ticket candidate sample count must be a positive integer"
        raise TicketAdmissionError(message)
    if (
        type(candidate.paired_wins) is not int
        or not 0 <= candidate.paired_wins <= candidate.sample_count
    ):
        message = "ticket candidate paired wins are inconsistent"
        raise TicketAdmissionError(message)


def _validate_candidate_measurements(candidate: TicketRouteCandidate) -> None:
    if candidate.candidate_median_ns <= 0 or candidate.reference_median_ns <= 0:
        message = "ticket candidate medians must be positive"
        raise TicketAdmissionError(message)
    if type(candidate.exact_results) is not bool:
        message = "ticket candidate exact-result flag must be boolean"
        raise TicketAdmissionError(message)


@dataclass(frozen=True, slots=True)
class TicketSubmissionChunk:
    """One input-order ticket range assigned to one measured route."""

    estimated_ns: int
    evidence_id: str | None
    mode: TicketSubmissionMode
    start: int
    stop: int

    @property
    def ticket_count(self) -> int:
        """Number of tickets in this half-open chunk."""
        return self.stop - self.start


@dataclass(frozen=True, slots=True)
class TicketAdmissionPlan:
    """Deterministic evidence-bound plan for one pending ticket queue."""

    admission_id: str
    chunks: tuple[TicketSubmissionChunk, ...]
    estimated_ns: int
    request: TicketAdmissionRequest


@dataclass(frozen=True, slots=True)
class TicketRouteAssessment:
    """One validated route's eligibility and final-plan usage."""

    benchmark_id: str
    candidate_median_ns: int
    evidence_id: str
    exact_results: bool
    group_size: int
    mode: TicketSubmissionMode
    paired_wins: int
    reference_median_ns: int
    rejection_reasons: tuple[TicketRouteRejection, ...]
    sample_count: int
    selected_chunk_count: int
    selected_ticket_count: int

    @property
    def eligible(self) -> bool:
        """Whether retained evidence may participate in planning."""
        return not self.rejection_reasons


@dataclass(frozen=True, slots=True)
class TicketAdmissionReport:
    """Opt-in immutable explanation of one ticket admission decision."""

    assessments: tuple[TicketRouteAssessment, ...]
    fallback_ticket_count: int
    plan: TicketAdmissionPlan
    report_id: str
    selected_streamed_ticket_count: int
    selected_synchronous_ticket_count: int


@dataclass(frozen=True, slots=True)
class _CandidateEvaluation:
    candidate: TicketRouteCandidate
    rejection_reasons: tuple[TicketRouteRejection, ...]


@dataclass(frozen=True, slots=True)
class _PlanState:
    chunks: tuple[TicketSubmissionChunk, ...]
    estimated_ns: int


def ticket_route_admission_id() -> str:
    """Return the stable conservative ticket admission identity.

    Returns:
        Versioned evidence-bound route admission identity.

    """
    return TICKET_ROUTE_ADMISSION_ID


def ticket_route_admission_report_id() -> str:
    """Return the stable opt-in admission-report identity.

    Returns:
        Versioned immutable ticket admission explanation identity.

    """
    return TICKET_ROUTE_ADMISSION_REPORT_ID


def plan_ticket_submissions(
    request: TicketAdmissionRequest,
    *,
    candidates: tuple[TicketRouteCandidate, ...],
    fallback_ticket_ns: int,
) -> TicketAdmissionPlan:
    """Plan exact ticket chunks from retained positive route evidence.

    Returns:
        Fewest-chunk partition, then minimum measured cost for the exact
        context.

    """
    context, evaluations = _validated_evaluations(
        request,
        candidates,
        fallback_ticket_ns=fallback_ticket_ns,
    )
    return _plan_from_evaluations(
        context,
        evaluations,
        fallback_ticket_ns=fallback_ticket_ns,
    )


def plan_ticket_submissions_with_report(
    request: TicketAdmissionRequest,
    *,
    candidates: tuple[TicketRouteCandidate, ...],
    fallback_ticket_ns: int,
) -> TicketAdmissionReport:
    """Plan exact tickets and publish an immutable route explanation.

    Returns:
        The unchanged conservative plan plus per-route eligibility and usage.

    """
    context, evaluations = _validated_evaluations(
        request,
        candidates,
        fallback_ticket_ns=fallback_ticket_ns,
    )
    plan = _plan_from_evaluations(
        context,
        evaluations,
        fallback_ticket_ns=fallback_ticket_ns,
    )
    return _admission_report(plan, evaluations)


def _validated_evaluations(
    request: TicketAdmissionRequest,
    candidates: tuple[TicketRouteCandidate, ...],
    *,
    fallback_ticket_ns: int,
) -> tuple[TicketAdmissionRequest, tuple[_CandidateEvaluation, ...]]:
    context = request.validated()
    if type(fallback_ticket_ns) is not int or fallback_ticket_ns <= 0:
        message = "ticket admission fallback median must be a positive integer"
        raise TicketAdmissionError(message)
    return context, _evaluate_candidates(context, candidates)


def _plan_from_evaluations(
    context: TicketAdmissionRequest,
    evaluations: tuple[_CandidateEvaluation, ...],
    *,
    fallback_ticket_ns: int,
) -> TicketAdmissionPlan:
    admitted = tuple(
        sorted(
            (
                evaluation.candidate
                for evaluation in evaluations
                if not evaluation.rejection_reasons
            ),
            key=lambda evidence: (
                evidence.group_size,
                evidence.mode.value,
                evidence.benchmark_id,
            ),
        )
    )
    state = _minimum_plan(context.ticket_count, fallback_ticket_ns, admitted)
    return TicketAdmissionPlan(
        admission_id=TICKET_ROUTE_ADMISSION_ID,
        chunks=state.chunks,
        estimated_ns=state.estimated_ns,
        request=context,
    )


def _evaluate_candidates(
    request: TicketAdmissionRequest,
    candidates: tuple[TicketRouteCandidate, ...],
) -> tuple[_CandidateEvaluation, ...]:
    matching: dict[tuple[TicketSubmissionMode, int], TicketRouteCandidate] = {}
    evaluations: list[_CandidateEvaluation] = []
    for candidate in candidates:
        evidence = candidate.validated()
        context_matches = _matches(request, evidence)
        if context_matches:
            key = (evidence.mode, evidence.group_size)
            if key in matching:
                message = (
                    "ticket admission contains duplicate route evidence: "
                    f"{evidence.mode.value}/{evidence.group_size}"
                )
                raise TicketAdmissionError(message)
            matching[key] = evidence
        evaluations.append(
            _CandidateEvaluation(
                candidate=evidence,
                rejection_reasons=_rejection_reasons(
                    request,
                    evidence,
                    context_matches=context_matches,
                ),
            )
        )
    return tuple(evaluations)


def _rejection_reasons(
    request: TicketAdmissionRequest,
    candidate: TicketRouteCandidate,
    *,
    context_matches: bool,
) -> tuple[TicketRouteRejection, ...]:
    if not context_matches:
        return (TicketRouteRejection.CONTEXT_MISMATCH,)
    checks = (
        (TicketRouteRejection.INEXACT_RESULTS, not candidate.exact_results),
        (
            TicketRouteRejection.NO_MEDIAN_IMPROVEMENT,
            candidate.candidate_median_ns >= candidate.reference_median_ns,
        ),
        (
            TicketRouteRejection.NO_PAIRED_MAJORITY,
            candidate.paired_wins <= candidate.sample_count // 2,
        ),
        (
            TicketRouteRejection.GROUP_EXCEEDS_QUEUE,
            candidate.group_size > request.ticket_count,
        ),
    )
    return tuple(reason for reason, rejected in checks if rejected)


def _admission_report(
    plan: TicketAdmissionPlan,
    evaluations: tuple[_CandidateEvaluation, ...],
) -> TicketAdmissionReport:
    selected: dict[str, tuple[int, int]] = {}
    fallback_ticket_count = 0
    selected_streamed_ticket_count = 0
    selected_synchronous_ticket_count = 0
    for chunk in plan.chunks:
        if chunk.evidence_id is None:
            fallback_ticket_count += chunk.ticket_count
            continue
        chunk_count, ticket_count = selected.get(chunk.evidence_id, (0, 0))
        selected[chunk.evidence_id] = (
            chunk_count + 1,
            ticket_count + chunk.ticket_count,
        )
        if chunk.mode is TicketSubmissionMode.STREAMED:
            selected_streamed_ticket_count += chunk.ticket_count
        else:
            selected_synchronous_ticket_count += chunk.ticket_count
    assessments = tuple(
        _route_assessment(evaluation, selected) for evaluation in evaluations
    )
    return TicketAdmissionReport(
        assessments=assessments,
        fallback_ticket_count=fallback_ticket_count,
        plan=plan,
        report_id=TICKET_ROUTE_ADMISSION_REPORT_ID,
        selected_streamed_ticket_count=selected_streamed_ticket_count,
        selected_synchronous_ticket_count=selected_synchronous_ticket_count,
    )


def _route_assessment(
    evaluation: _CandidateEvaluation,
    selected: dict[str, tuple[int, int]],
) -> TicketRouteAssessment:
    candidate = evaluation.candidate
    evidence_id = _candidate_evidence_id(candidate)
    selected_chunk_count, selected_ticket_count = (
        (0, 0)
        if evaluation.rejection_reasons
        else selected.get(evidence_id, (0, 0))
    )
    return TicketRouteAssessment(
        benchmark_id=candidate.benchmark_id,
        candidate_median_ns=candidate.candidate_median_ns,
        evidence_id=evidence_id,
        exact_results=candidate.exact_results,
        group_size=candidate.group_size,
        mode=candidate.mode,
        paired_wins=candidate.paired_wins,
        reference_median_ns=candidate.reference_median_ns,
        rejection_reasons=evaluation.rejection_reasons,
        sample_count=candidate.sample_count,
        selected_chunk_count=selected_chunk_count,
        selected_ticket_count=selected_ticket_count,
    )


def _candidate_evidence_id(candidate: TicketRouteCandidate) -> str:
    return (
        f"{candidate.benchmark_id}:{candidate.mode.value}:"
        f"{candidate.group_size}"
    )


def _matches(
    request: TicketAdmissionRequest,
    candidate: TicketRouteCandidate,
) -> bool:
    return (
        candidate.backend_id == request.backend_id
        and candidate.device_arch == request.device_arch
        and candidate.device_name == request.device_name
        and candidate.workload_id == request.workload_id
    )


def _minimum_plan(
    ticket_count: int,
    fallback_ticket_ns: int,
    candidates: tuple[TicketRouteCandidate, ...],
) -> _PlanState:
    states: list[_PlanState | None] = [None] * (ticket_count + 1)
    states[0] = _PlanState(chunks=(), estimated_ns=0)
    for stop in range(1, ticket_count + 1):
        states[stop] = _best_plan_for_stop(
            states,
            stop,
            fallback_ticket_ns=fallback_ticket_ns,
            candidates=candidates,
        )
    result = states[ticket_count]
    if result is None:
        message = "ticket admission failed to construct a complete plan"
        raise TicketAdmissionError(message)
    return result


def _best_plan_for_stop(
    states: list[_PlanState | None],
    stop: int,
    *,
    fallback_ticket_ns: int,
    candidates: tuple[TicketRouteCandidate, ...],
) -> _PlanState:
    previous = states[stop - 1]
    if previous is None:
        message = "ticket admission fallback state is missing"
        raise TicketAdmissionError(message)
    best = _append_fallback(previous, stop, fallback_ticket_ns)
    for candidate in candidates:
        source = _candidate_source(states, stop, candidate.group_size)
        if source is None:
            continue
        proposed = _append_candidate(source, stop, candidate)
        if _plan_key(proposed) < _plan_key(best):
            best = proposed
    return best


def _candidate_source(
    states: list[_PlanState | None], stop: int, group_size: int
) -> _PlanState | None:
    start = stop - group_size
    return None if start < 0 else states[start]


def _append_fallback(
    state: _PlanState,
    stop: int,
    fallback_ticket_ns: int,
) -> _PlanState:
    chunk = TicketSubmissionChunk(
        estimated_ns=fallback_ticket_ns,
        evidence_id=None,
        mode=TicketSubmissionMode.SYNCHRONOUS,
        start=stop - 1,
        stop=stop,
    )
    return _PlanState(
        chunks=(*state.chunks, chunk),
        estimated_ns=state.estimated_ns + fallback_ticket_ns,
    )


def _append_candidate(
    state: _PlanState,
    stop: int,
    candidate: TicketRouteCandidate,
) -> _PlanState:
    chunk = TicketSubmissionChunk(
        estimated_ns=candidate.candidate_median_ns,
        evidence_id=_candidate_evidence_id(candidate),
        mode=candidate.mode,
        start=stop - candidate.group_size,
        stop=stop,
    )
    return _PlanState(
        chunks=(*state.chunks, chunk),
        estimated_ns=state.estimated_ns + candidate.candidate_median_ns,
    )


def _plan_key(state: _PlanState) -> tuple[object, ...]:
    streamed = sum(
        chunk.mode is TicketSubmissionMode.STREAMED for chunk in state.chunks
    )
    signature = tuple(
        (
            chunk.start,
            chunk.stop,
            chunk.mode.value,
            chunk.evidence_id or "",
        )
        for chunk in state.chunks
    )
    return (len(state.chunks), state.estimated_ns, streamed, signature)
