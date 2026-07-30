# File:
#   - test_ticket_admission_telemetry.py
# Path:
#   - tests/optimizer/test_ticket_admission_telemetry.py
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
#   - Bounded completed-plan telemetry regressions.
# - Must-Not:
#   - Require CUDA, alter admission, or treat observations as policy evidence.
# - Allows:
#   - Inputs: synthetic immutable admission reports and elapsed durations.
#   - Outputs: recorder identity, ordering, eviction, and validation assertions.
#   - Side effects: bounded in-memory recorder mutation only.
# - Split-When:
#   - Split when persisted telemetry gains an independent contract.
# - Merge-When:
#   - Merge when another suite owns this exact bounded recorder behavior.
# - Summary:
#   - Ticket admission telemetry regressions.
# - Description:
#   - Proves opt-in recording stays bounded and fails closed before mutation.
# - Usage:
#   - Runs with optimizer tests without accelerator hardware.
# - Defaults:
#   - No online learning or automatic recorder exists.
#
# Related documents:
# - accelerator/ticket_admission_telemetry.py
#
# Large file:
#   - false
#

"""Bounded opt-in ticket admission telemetry tests."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from accelerator.ticket_admission import TicketAdmissionRequest
from accelerator.ticket_admission import TicketRouteCandidate
from accelerator.ticket_admission import TicketSubmissionMode
from accelerator.ticket_admission import plan_ticket_submissions_with_report
from accelerator.ticket_admission_telemetry import TicketAdmissionTelemetry
from accelerator.ticket_admission_telemetry import TicketAdmissionTelemetryError
from accelerator.ticket_admission_telemetry import ticket_admission_telemetry_id

if TYPE_CHECKING:
    from accelerator.ticket_admission import TicketAdmissionReport

TELEMETRY_ID = "bounded-ticket-admission-telemetry-v1"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "exact-test-workload-v1"
BENCHMARK_ID = "test-ticket-route-v1"
FALLBACK_NS = 100
CANDIDATE_NS = 80
ELAPSED_NS = 125
SECOND_ELAPSED_NS = 145
PAIR_GROUP_SIZE = 2


def _report(
    ticket_count: int = PAIR_GROUP_SIZE,
) -> TicketAdmissionReport:
    request = TicketAdmissionRequest(
        backend_id=BACKEND_ID,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        ticket_count=ticket_count,
        workload_id=WORKLOAD_ID,
    )
    candidate = TicketRouteCandidate(
        backend_id=BACKEND_ID,
        benchmark_id=BENCHMARK_ID,
        candidate_median_ns=CANDIDATE_NS,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        exact_results=True,
        group_size=PAIR_GROUP_SIZE,
        mode=TicketSubmissionMode.SYNCHRONOUS,
        paired_wins=15,
        reference_median_ns=180,
        sample_count=15,
        workload_id=WORKLOAD_ID,
    )
    return plan_ticket_submissions_with_report(
        request,
        candidates=(candidate,),
        fallback_ticket_ns=FALLBACK_NS,
    )


def test_ticket_admission_telemetry_identity_and_empty_snapshot() -> None:
    """A caller-created recorder starts empty with one stable identity."""
    telemetry = TicketAdmissionTelemetry(capacity=2)

    snapshot = telemetry.snapshot()

    assert ticket_admission_telemetry_id() == TELEMETRY_ID
    assert snapshot.telemetry_id == TELEMETRY_ID
    assert snapshot.capacity == PAIR_GROUP_SIZE
    assert snapshot.dropped_observation_count == 0
    assert snapshot.next_sequence_id == 0
    assert snapshot.observations == ()


@pytest.mark.parametrize("capacity", [0, -1, True])
def test_ticket_admission_telemetry_rejects_invalid_capacity(
    capacity: int,
) -> None:
    """Zero, negative, and boolean capacities fail before allocation."""
    with pytest.raises(
        TicketAdmissionTelemetryError,
        match="capacity must be a positive integer",
    ):
        _ = TicketAdmissionTelemetry(capacity=capacity)


def test_ticket_admission_telemetry_records_completed_report() -> None:
    """One observation preserves exact plan identity, usage, and timing."""
    report = _report()
    telemetry = TicketAdmissionTelemetry(capacity=2)

    observation = telemetry.record_completed(report, elapsed_ns=ELAPSED_NS)

    assert observation.sequence_id == 0
    assert observation.backend_id == BACKEND_ID
    assert observation.device_arch == DEVICE_ARCH
    assert observation.device_name == DEVICE_NAME
    assert observation.workload_id == WORKLOAD_ID
    assert observation.ticket_count == PAIR_GROUP_SIZE
    assert observation.chunk_count == 1
    assert observation.estimated_ns == CANDIDATE_NS
    assert observation.elapsed_ns == ELAPSED_NS
    assert observation.estimate_delta_ns == ELAPSED_NS - CANDIDATE_NS
    assert observation.fallback_ticket_count == 0
    assert observation.selected_streamed_ticket_count == 0
    assert observation.selected_synchronous_ticket_count == PAIR_GROUP_SIZE
    assert observation.selected_evidence_ids == (
        f"{BENCHMARK_ID}:synchronous:{PAIR_GROUP_SIZE}",
    )
    assert telemetry.snapshot().observations == (observation,)


def test_ticket_admission_telemetry_evicts_oldest_observation() -> None:
    """Capacity eviction is FIFO while sequence IDs remain monotonic."""
    telemetry = TicketAdmissionTelemetry(capacity=1)
    first = telemetry.record_completed(_report(), elapsed_ns=ELAPSED_NS)
    second = telemetry.record_completed(
        _report(),
        elapsed_ns=SECOND_ELAPSED_NS,
    )

    snapshot = telemetry.snapshot()

    assert first.sequence_id == 0
    assert second.sequence_id == 1
    assert snapshot.observations == (second,)
    assert snapshot.dropped_observation_count == 1
    assert snapshot.next_sequence_id == PAIR_GROUP_SIZE


def test_ticket_admission_telemetry_rejects_before_mutation() -> None:
    """Malformed reports and durations leave recorder state unchanged."""
    telemetry = TicketAdmissionTelemetry(capacity=2)
    report = _report()
    malformed = replace(report, fallback_ticket_count=1)

    with pytest.raises(
        TicketAdmissionTelemetryError,
        match="aggregate counts mismatched",
    ):
        _ = telemetry.record_completed(malformed, elapsed_ns=ELAPSED_NS)
    with pytest.raises(
        TicketAdmissionTelemetryError,
        match="elapsed time must be a non-negative integer",
    ):
        _ = telemetry.record_completed(report, elapsed_ns=-1)

    snapshot = telemetry.snapshot()
    assert snapshot.observations == ()
    assert snapshot.dropped_observation_count == 0
    assert snapshot.next_sequence_id == 0
