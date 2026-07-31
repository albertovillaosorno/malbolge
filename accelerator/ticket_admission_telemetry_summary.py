# File:
#   - ticket_admission_telemetry_summary.py
# Path:
#   - accelerator/ticket_admission_telemetry_summary.py
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
#   - Deterministic offline summaries of one validated telemetry document.
# - Must-Not:
#   - Recommend, promote, persist, load, or change ticket admission policy.
# - Allows:
#   - Inputs: one explicit schema-v1 ticket telemetry document.
#   - Outputs: immutable exact-count summaries grouped by execution context.
#   - Side effects: none.
# - Split-When:
#   - Split when recommendations gain an independent lifecycle.
# - Merge-When:
#   - Merge when another module owns this exact offline summary contract.
# - Summary:
#   - Non-authoritative ticket telemetry summaries.
# - Description:
#   - Aggregates retained outcomes without inventing evidence or policy.
# - Usage:
#   - Decode explicitly, summarize explicitly, and review counts offline.
# - Defaults:
#   - Invalid documents fail closed; empty documents produce an empty summary.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_persistence.py
# - accelerator/ticket_admission_telemetry_store.py
# - accelerator/ticket_admission_telemetry_collection.py
# - accelerator/ticket_admission_telemetry_overlap.py
# - accelerator/ticket_admission_telemetry_overlap_index.py
# - accelerator/ticket_admission_telemetry_overlap_components.py
# - accelerator/ticket_admission_telemetry_lineage.py
# - accelerator/ticket_admission_telemetry_lineage_trust.py
# - accelerator/ticket_admission_telemetry_lineage_trust_manifest.py
# - accelerator/ticket_admission_telemetry_lineage_secret_provider.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Deterministic non-authoritative ticket telemetry summaries."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Final
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry import (
        TicketAdmissionFailureKind,
    )
    from accelerator.ticket_admission_telemetry import (
        TicketAdmissionFailureObservation,
    )
    from accelerator.ticket_admission_telemetry import (
        TicketAdmissionFailureTelemetrySnapshot,
    )
    from accelerator.ticket_admission_telemetry import (
        TicketAdmissionObservation,
    )
    from accelerator.ticket_admission_telemetry import (
        TicketAdmissionTelemetrySnapshot,
    )
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

from accelerator.ticket_admission_telemetry_persistence import (
    TicketAdmissionTelemetryPersistenceError,
)
from accelerator.ticket_admission_telemetry_persistence import (
    encode_ticket_admission_telemetry_document,
)

TICKET_ADMISSION_TELEMETRY_SUMMARY_ID: Final = (
    "offline-ticket-admission-telemetry-summary-v1"
)

type _Observation = (
    TicketAdmissionObservation | TicketAdmissionFailureObservation
)
type _Snapshot = (
    TicketAdmissionTelemetrySnapshot | TicketAdmissionFailureTelemetrySnapshot
)
type _ContextKey = tuple[str, str, str, str, int]


class TicketAdmissionTelemetrySummaryError(ValueError):
    """A telemetry document cannot produce a trusted offline summary."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionRetentionSummary:
    """Exact retained and evicted range state for one bounded FIFO."""

    capacity: int
    dropped_observation_count: int
    first_sequence_id: int | None
    next_sequence_id: int
    retained_observation_count: int


@dataclass(frozen=True, slots=True)
class TicketAdmissionOutcomeSummary:
    """Exact integer aggregates for one completed or failed outcome class."""

    chunk_count: int
    elapsed_ns: int
    estimate_delta_ns: int
    estimated_ns: int
    fallback_ticket_count: int
    faster_than_estimate_count: int
    matched_estimate_count: int
    observation_count: int
    selected_streamed_ticket_count: int
    selected_synchronous_ticket_count: int
    slower_than_estimate_count: int
    ticket_count: int


@dataclass(frozen=True, slots=True)
class TicketAdmissionFailureCount:
    """Number of retained failures in one stable non-message category."""

    count: int
    failure_kind: TicketAdmissionFailureKind


@dataclass(frozen=True, slots=True)
class TicketAdmissionEvidenceAppearance:
    """Observation counts in which one selected evidence identity appeared."""

    completed_observation_count: int
    evidence_id: str
    failed_observation_count: int


@dataclass(frozen=True, slots=True)
class TicketAdmissionContextSummary:
    """Offline aggregates for one exact device, workload, and queue context."""

    backend_id: str
    completed: TicketAdmissionOutcomeSummary
    device_arch: str
    device_name: str
    evidence_appearances: tuple[TicketAdmissionEvidenceAppearance, ...]
    failed: TicketAdmissionOutcomeSummary
    failure_counts: tuple[TicketAdmissionFailureCount, ...]
    ticket_count: int
    workload_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetrySummary:
    """Deterministic review surface for one validated telemetry document."""

    completed_retention: TicketAdmissionRetentionSummary
    contexts: tuple[TicketAdmissionContextSummary, ...]
    document_id: str
    failed_retention: TicketAdmissionRetentionSummary
    schema_version: int
    summary_id: str


@dataclass(slots=True)
class _OutcomeAccumulator:
    chunk_count: int = 0
    elapsed_ns: int = 0
    estimate_delta_ns: int = 0
    estimated_ns: int = 0
    fallback_ticket_count: int = 0
    faster_than_estimate_count: int = 0
    matched_estimate_count: int = 0
    observation_count: int = 0
    selected_streamed_ticket_count: int = 0
    selected_synchronous_ticket_count: int = 0
    slower_than_estimate_count: int = 0
    ticket_count: int = 0

    def add(self, observation: _Observation) -> None:
        """Add one already validated observation to exact integer totals."""
        self.chunk_count += observation.chunk_count
        self.elapsed_ns += observation.elapsed_ns
        self.estimate_delta_ns += observation.estimate_delta_ns
        self.estimated_ns += observation.estimated_ns
        self.fallback_ticket_count += observation.fallback_ticket_count
        self.observation_count += 1
        self.selected_streamed_ticket_count += (
            observation.selected_streamed_ticket_count
        )
        self.selected_synchronous_ticket_count += (
            observation.selected_synchronous_ticket_count
        )
        self.ticket_count += observation.ticket_count
        self._record_estimate_comparison(observation.estimate_delta_ns)

    def _record_estimate_comparison(self, delta_ns: int) -> None:
        if delta_ns < 0:
            self.faster_than_estimate_count += 1
        elif delta_ns > 0:
            self.slower_than_estimate_count += 1
        else:
            self.matched_estimate_count += 1


@dataclass(slots=True)
class _EvidenceAccumulator:
    completed_observation_count: int = 0
    failed_observation_count: int = 0


@dataclass(slots=True)
class _ContextAccumulator:
    completed: _OutcomeAccumulator = field(default_factory=_OutcomeAccumulator)
    evidence: dict[str, _EvidenceAccumulator] = field(default_factory=dict)
    failed: _OutcomeAccumulator = field(default_factory=_OutcomeAccumulator)
    failures: dict[TicketAdmissionFailureKind, int] = field(
        default_factory=dict
    )


def ticket_admission_telemetry_summary_id() -> str:
    """Return the stable offline telemetry summary identity.

    Returns:
        Versioned non-authoritative summary identity.

    """
    return TICKET_ADMISSION_TELEMETRY_SUMMARY_ID


def summarize_ticket_admission_telemetry(
    document: TicketAdmissionTelemetryDocument,
) -> TicketAdmissionTelemetrySummary:
    """Summarize one explicit validated document without policy authority.

    Returns:
        Deterministically ordered exact-count review summary.

    """
    state = _validated_document(document)
    contexts: dict[_ContextKey, _ContextAccumulator] = {}
    for observation in state.completed.observations:
        _record_completed(contexts, observation)
    for observation in state.failed.observations:
        _record_failed(contexts, observation)
    return TicketAdmissionTelemetrySummary(
        completed_retention=_retention_summary(state.completed),
        contexts=tuple(
            _context_summary(key, contexts[key]) for key in sorted(contexts)
        ),
        document_id=state.document_id,
        failed_retention=_retention_summary(state.failed),
        schema_version=state.schema_version,
        summary_id=TICKET_ADMISSION_TELEMETRY_SUMMARY_ID,
    )


def _validated_document(
    document: TicketAdmissionTelemetryDocument,
) -> TicketAdmissionTelemetryDocument:
    try:
        _ = encode_ticket_admission_telemetry_document(document)
    except TicketAdmissionTelemetryPersistenceError as error:
        message = f"invalid ticket telemetry document: {error}"
        raise TicketAdmissionTelemetrySummaryError(message) from error
    return document


def _retention_summary(snapshot: _Snapshot) -> TicketAdmissionRetentionSummary:
    first_sequence_id = None
    if snapshot.observations:
        first_sequence_id = snapshot.observations[0].sequence_id
    return TicketAdmissionRetentionSummary(
        capacity=snapshot.capacity,
        dropped_observation_count=snapshot.dropped_observation_count,
        first_sequence_id=first_sequence_id,
        next_sequence_id=snapshot.next_sequence_id,
        retained_observation_count=len(snapshot.observations),
    )


def _record_completed(
    contexts: dict[_ContextKey, _ContextAccumulator],
    observation: TicketAdmissionObservation,
) -> None:
    context = _context(contexts, observation)
    context.completed.add(observation)
    _record_evidence(context, observation, completed=True)


def _record_failed(
    contexts: dict[_ContextKey, _ContextAccumulator],
    observation: TicketAdmissionFailureObservation,
) -> None:
    context = _context(contexts, observation)
    context.failed.add(observation)
    context.failures[observation.failure_kind] = (
        context.failures.get(observation.failure_kind, 0) + 1
    )
    _record_evidence(context, observation, completed=False)


def _context(
    contexts: dict[_ContextKey, _ContextAccumulator],
    observation: _Observation,
) -> _ContextAccumulator:
    key = _context_key(observation)
    if key not in contexts:
        contexts[key] = _ContextAccumulator()
    return contexts[key]


def _context_key(observation: _Observation) -> _ContextKey:
    return (
        observation.backend_id,
        observation.device_arch,
        observation.device_name,
        observation.workload_id,
        observation.ticket_count,
    )


def _record_evidence(
    context: _ContextAccumulator,
    observation: _Observation,
    *,
    completed: bool,
) -> None:
    for evidence_id in observation.selected_evidence_ids:
        appearance = context.evidence.setdefault(
            evidence_id,
            _EvidenceAccumulator(),
        )
        if completed:
            appearance.completed_observation_count += 1
        else:
            appearance.failed_observation_count += 1


def _context_summary(
    key: _ContextKey,
    context: _ContextAccumulator,
) -> TicketAdmissionContextSummary:
    backend_id, device_arch, device_name, workload_id, ticket_count = key
    return TicketAdmissionContextSummary(
        backend_id=backend_id,
        completed=_outcome_summary(context.completed),
        device_arch=device_arch,
        device_name=device_name,
        evidence_appearances=_evidence_appearances(context.evidence),
        failed=_outcome_summary(context.failed),
        failure_counts=_failure_counts(context.failures),
        ticket_count=ticket_count,
        workload_id=workload_id,
    )


def _outcome_summary(
    outcome: _OutcomeAccumulator,
) -> TicketAdmissionOutcomeSummary:
    return TicketAdmissionOutcomeSummary(
        chunk_count=outcome.chunk_count,
        elapsed_ns=outcome.elapsed_ns,
        estimate_delta_ns=outcome.estimate_delta_ns,
        estimated_ns=outcome.estimated_ns,
        fallback_ticket_count=outcome.fallback_ticket_count,
        faster_than_estimate_count=outcome.faster_than_estimate_count,
        matched_estimate_count=outcome.matched_estimate_count,
        observation_count=outcome.observation_count,
        selected_streamed_ticket_count=(
            outcome.selected_streamed_ticket_count
        ),
        selected_synchronous_ticket_count=(
            outcome.selected_synchronous_ticket_count
        ),
        slower_than_estimate_count=outcome.slower_than_estimate_count,
        ticket_count=outcome.ticket_count,
    )


def _failure_counts(
    counts: dict[TicketAdmissionFailureKind, int],
) -> tuple[TicketAdmissionFailureCount, ...]:
    return tuple(
        TicketAdmissionFailureCount(count=counts[kind], failure_kind=kind)
        for kind in sorted(counts, key=lambda value: value.value)
    )


def _evidence_appearances(
    appearances: dict[str, _EvidenceAccumulator],
) -> tuple[TicketAdmissionEvidenceAppearance, ...]:
    return tuple(
        TicketAdmissionEvidenceAppearance(
            completed_observation_count=(
                appearances[evidence_id].completed_observation_count
            ),
            evidence_id=evidence_id,
            failed_observation_count=(
                appearances[evidence_id].failed_observation_count
            ),
        )
        for evidence_id in sorted(appearances)
    )
