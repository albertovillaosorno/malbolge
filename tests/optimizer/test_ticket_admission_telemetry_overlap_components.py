# File:
#   - test_ticket_admission_telemetry_overlap_components.py
# Path:
#   - tests/optimizer/test_ticket_admission_telemetry_overlap_components.py
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
#   - Deterministic telemetry compatibility-component regressions.
# - Must-Not:
#   - Require CUDA, infer lineage, merge snapshots, or modify admission.
# - Allows:
#   - Inputs: synthetic telemetry documents and inherited index limits.
#   - Outputs: edge, component, clique, bridge, ordering, and failure
#     assertions.
#   - Side effects: temporary monkeypatching of the component digest
#     constructor.
# - Split-When:
#   - Split when asymmetric lineage or recommendation policy gains a
#     protocol.
# - Merge-When:
#   - Merge when another suite owns this exact compatibility-graph behavior.
# - Summary:
#   - Non-authoritative telemetry overlap component regressions.
# - Description:
#   - Proves transitive compatibility remains distinct from pairwise
#     equivalence.
# - Usage:
#   - Runs without accelerator hardware or filesystem access.
# - Defaults:
#   - Empty and duplicate-only inputs remain valid bounded graphs.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_overlap_components.py
# - accelerator/ticket_admission_telemetry_lineage.py
# - accelerator/ticket_admission_telemetry_lineage_trust.py
# - accelerator/ticket_admission_telemetry_lineage_trust_manifest.py
# - accelerator/ticket_admission_telemetry_lineage_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_secret_provider.py
# - accelerator/ticket_admission_memory_async_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage.py
#
# Large file:
#   - false
#

"""Deterministic non-authoritative telemetry overlap component tests."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from accelerator.ticket_admission import TicketAdmissionReport
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

from accelerator import (
    ticket_admission_telemetry_overlap_components as components_module,
)
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.ticket_admission import TicketAdmissionRequest
from accelerator.ticket_admission import TicketRouteCandidate
from accelerator.ticket_admission import TicketSubmissionMode
from accelerator.ticket_admission import plan_ticket_submissions_with_report
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionAttemptTelemetry,
)
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionFailureTelemetry,
)
from accelerator.ticket_admission_telemetry import TicketAdmissionTelemetry
from accelerator.ticket_admission_telemetry_overlap_components import (
    TicketAdmissionTelemetryOverlapComponentsError,
)
from accelerator.ticket_admission_telemetry_overlap_components import (
    build_ticket_admission_telemetry_overlap_components,
)
from accelerator.ticket_admission_telemetry_overlap_components import (
    ticket_admission_telemetry_overlap_components_id,
)
from accelerator.ticket_admission_telemetry_persistence import (
    capture_ticket_admission_telemetry_document,
)

COMPONENTS_ID = "offline-ticket-admission-telemetry-overlap-components-v1"
COMPONENT_PREFIX = "ticket-admission-telemetry-overlap-component-v1:sha256:"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "overlap-components-test-workload-v1"
BENCHMARK_ID = "overlap-components-test-route-v1"
TICKET_COUNT = 2
CANDIDATE_NS = 80
REFERENCE_NS = 180
PRIVATE_DETAIL = "private accelerator detail"
LOW_ELAPSED_NS = 70
MATCH_ELAPSED_NS = 80
HIGH_ELAPSED_NS = 90
FINAL_ELAPSED_NS = 100
TWO_DOCUMENT_COUNT = 2
THREE_DOCUMENT_COUNT = 3
CHAIN_EDGE_COUNT = 2
PAIR_COUNT = 3
DUPLICATE_INPUT_COUNT = 3
DUPLICATE_DOCUMENT_COUNT = 2


def _report() -> TicketAdmissionReport:
    request = TicketAdmissionRequest(
        backend_id=BACKEND_ID,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        ticket_count=TICKET_COUNT,
        workload_id=WORKLOAD_ID,
    )
    candidate = TicketRouteCandidate(
        backend_id=BACKEND_ID,
        benchmark_id=BENCHMARK_ID,
        candidate_median_ns=CANDIDATE_NS,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        exact_results=True,
        group_size=TICKET_COUNT,
        mode=TicketSubmissionMode.SYNCHRONOUS,
        paired_wins=15,
        reference_median_ns=REFERENCE_NS,
        sample_count=15,
        workload_id=WORKLOAD_ID,
    )
    return plan_ticket_submissions_with_report(
        request,
        candidates=(candidate,),
        fallback_ticket_ns=100,
    )


def _attempts(capacity: int = 2) -> TicketAdmissionAttemptTelemetry:
    return TicketAdmissionAttemptTelemetry(
        completed=TicketAdmissionTelemetry(capacity=capacity),
        failed=TicketAdmissionFailureTelemetry(capacity=capacity),
    )


def _capture(
    attempts: TicketAdmissionAttemptTelemetry,
) -> TicketAdmissionTelemetryDocument:
    return capture_ticket_admission_telemetry_document(attempts)


def _completed_document(elapsed_ns: int) -> TicketAdmissionTelemetryDocument:
    attempts = _attempts()
    _ = attempts.record_completed(_report(), elapsed_ns=elapsed_ns)
    return _capture(attempts)


def test_empty_graph_has_stable_identity_and_zero_counts() -> None:
    """An empty collection yields no vertices, edges, or components."""
    graph = build_ticket_admission_telemetry_overlap_components(())

    assert ticket_admission_telemetry_overlap_components_id() == COMPONENTS_ID
    assert graph.components_id == COMPONENTS_ID
    assert graph.component_count == 0
    assert graph.components == ()
    assert graph.connected_component_count == 0
    assert graph.connected_document_count == 0
    assert graph.isolated_document_count == 0
    assert graph.selected_edge_count == 0
    assert graph.ignored_pair_count == 0


def test_exact_duplicates_form_one_isolated_unique_component() -> None:
    """Duplicate occurrences never create vertices or compatibility edges."""
    document = _completed_document(LOW_ELAPSED_NS)

    graph = build_ticket_admission_telemetry_overlap_components(
        (document, document, document)
    )

    assert graph.index.collection.input_document_count == DUPLICATE_INPUT_COUNT
    assert graph.index.collection.duplicate_document_count == (
        DUPLICATE_DOCUMENT_COUNT
    )
    assert graph.component_count == 1
    assert graph.connected_component_count == 0
    assert graph.connected_document_count == 0
    assert graph.isolated_document_count == 1
    assert graph.selected_edge_count == 0
    component = graph.components[0]
    assert component.member_count == 1
    assert component.direct_edge_count == 0
    assert component.possible_edge_count == 0
    assert component.missing_direct_edge_count == 0
    assert component.is_clique
    assert component.edges == ()
    assert component.component_fingerprint.startswith(COMPONENT_PREFIX)


def test_matching_pair_forms_one_direct_clique() -> None:
    """One exact retained match creates one two-document clique."""
    report = _report()
    attempts = _attempts()
    _ = attempts.record_completed(report, elapsed_ns=LOW_ELAPSED_NS)
    first = _capture(attempts)
    _ = attempts.record_completed(report, elapsed_ns=MATCH_ELAPSED_NS)
    second = _capture(attempts)

    graph = build_ticket_admission_telemetry_overlap_components((first, second))

    assert graph.component_count == 1
    assert graph.connected_component_count == 1
    assert graph.connected_document_count == TWO_DOCUMENT_COUNT
    assert graph.isolated_document_count == 0
    assert graph.selected_edge_count == 1
    assert graph.ignored_pair_count == 0
    component = graph.components[0]
    assert component.member_count == TWO_DOCUMENT_COUNT
    assert component.direct_edge_count == 1
    assert component.possible_edge_count == 1
    assert component.missing_direct_edge_count == 0
    assert component.is_clique
    edge = component.edges[0]
    assert edge.completed_matching_observation_count == 1
    assert edge.failed_matching_observation_count == 0
    assert edge.matching_observation_count == 1


def test_conflicting_pair_remains_two_isolated_components() -> None:
    """A retained sequence conflict cannot become a compatibility edge."""
    first = _completed_document(LOW_ELAPSED_NS)
    second = _completed_document(HIGH_ELAPSED_NS)

    graph = build_ticket_admission_telemetry_overlap_components((first, second))

    assert graph.component_count == TWO_DOCUMENT_COUNT
    assert graph.connected_component_count == 0
    assert graph.connected_document_count == 0
    assert graph.isolated_document_count == TWO_DOCUMENT_COUNT
    assert graph.selected_edge_count == 0
    assert graph.ignored_pair_count == 1
    assert all(component.member_count == 1 for component in graph.components)


def test_three_successive_snapshots_form_one_direct_clique() -> None:
    """Three nested snapshots create all three direct compatibility edges."""
    report = _report()
    attempts = _attempts(capacity=3)
    documents: list[TicketAdmissionTelemetryDocument] = []
    for elapsed_ns in (LOW_ELAPSED_NS, MATCH_ELAPSED_NS, HIGH_ELAPSED_NS):
        _ = attempts.record_completed(report, elapsed_ns=elapsed_ns)
        documents.append(_capture(attempts))

    graph = build_ticket_admission_telemetry_overlap_components(
        tuple(documents)
    )

    assert graph.component_count == 1
    assert graph.selected_edge_count == PAIR_COUNT
    component = graph.components[0]
    assert component.member_count == THREE_DOCUMENT_COUNT
    assert component.direct_edge_count == PAIR_COUNT
    assert component.possible_edge_count == PAIR_COUNT
    assert component.missing_direct_edge_count == 0
    assert component.is_clique


def test_successive_chain_is_connected_but_not_pairwise_equivalent() -> None:
    """A transitive bridge remains visibly different from a clique."""
    report = _report()
    attempts = _attempts(capacity=2)
    _ = attempts.record_completed(report, elapsed_ns=LOW_ELAPSED_NS)
    _ = attempts.record_completed(report, elapsed_ns=MATCH_ELAPSED_NS)
    first = _capture(attempts)
    _ = attempts.record_completed(report, elapsed_ns=HIGH_ELAPSED_NS)
    second = _capture(attempts)
    _ = attempts.record_completed(report, elapsed_ns=FINAL_ELAPSED_NS)
    third = _capture(attempts)

    graph = build_ticket_admission_telemetry_overlap_components(
        (first, second, third)
    )

    assert graph.component_count == 1
    assert graph.connected_document_count == THREE_DOCUMENT_COUNT
    assert graph.selected_edge_count == CHAIN_EDGE_COUNT
    assert graph.ignored_pair_count == 1
    component = graph.components[0]
    assert component.member_count == THREE_DOCUMENT_COUNT
    assert component.direct_edge_count == CHAIN_EDGE_COUNT
    assert component.possible_edge_count == PAIR_COUNT
    assert component.missing_direct_edge_count == 1
    assert not component.is_clique


def test_failed_only_match_creates_compatibility_edge() -> None:
    """Exact failed telemetry can connect documents without completed data."""
    report = _report()
    attempts = _attempts()
    _ = attempts.record_failed(
        report,
        elapsed_ns=LOW_ELAPSED_NS,
        error=AcceleratorExecutionError(PRIVATE_DETAIL),
    )
    first = _capture(attempts)
    _ = attempts.record_failed(
        report,
        elapsed_ns=MATCH_ELAPSED_NS,
        error=AcceleratorUnavailableError(PRIVATE_DETAIL),
    )
    second = _capture(attempts)

    graph = build_ticket_admission_telemetry_overlap_components((first, second))

    edge = graph.components[0].edges[0]
    assert edge.completed_matching_observation_count == 0
    assert edge.failed_matching_observation_count == 1
    assert edge.matching_observation_count == 1
    assert PRIVATE_DETAIL not in repr(graph)


def test_conflict_in_either_fifo_blocks_an_edge() -> None:
    """A completed match cannot hide a failed-sequence conflict."""
    report = _report()
    first_attempts = _attempts()
    second_attempts = _attempts()
    for attempts in (first_attempts, second_attempts):
        _ = attempts.record_completed(report, elapsed_ns=LOW_ELAPSED_NS)
    _ = first_attempts.record_failed(
        report,
        elapsed_ns=LOW_ELAPSED_NS,
        error=AcceleratorExecutionError(PRIVATE_DETAIL),
    )
    _ = second_attempts.record_failed(
        report,
        elapsed_ns=HIGH_ELAPSED_NS,
        error=AcceleratorUnavailableError(PRIVATE_DETAIL),
    )

    graph = build_ticket_admission_telemetry_overlap_components(
        (_capture(first_attempts), _capture(second_attempts))
    )

    assert graph.selected_edge_count == 0
    assert graph.ignored_pair_count == 1
    assert graph.component_count == TWO_DOCUMENT_COUNT
    assert graph.isolated_document_count == TWO_DOCUMENT_COUNT


def test_component_output_is_input_order_independent() -> None:
    """Document permutation cannot change edge or component identities."""
    report = _report()
    attempts = _attempts(capacity=2)
    documents: list[TicketAdmissionTelemetryDocument] = []
    for elapsed_ns in (
        LOW_ELAPSED_NS,
        MATCH_ELAPSED_NS,
        HIGH_ELAPSED_NS,
        FINAL_ELAPSED_NS,
    ):
        _ = attempts.record_completed(report, elapsed_ns=elapsed_ns)
        if elapsed_ns != LOW_ELAPSED_NS:
            documents.append(_capture(attempts))

    forward = build_ticket_admission_telemetry_overlap_components(
        tuple(documents)
    )
    reverse = build_ticket_admission_telemetry_overlap_components(
        tuple(reversed(documents))
    )

    assert forward == reverse
    assert tuple(
        component.member_fingerprints for component in forward.components
    ) == tuple(
        sorted(
            component.member_fingerprints for component in forward.components
        )
    )
    assert all(
        component.edges
        == tuple(
            sorted(
                component.edges,
                key=lambda edge: (
                    edge.first_document_fingerprint,
                    edge.second_document_fingerprint,
                ),
            )
        )
        for component in forward.components
    )


def test_pair_limit_is_forwarded_before_component_work() -> None:
    """The compatibility graph preserves the bounded index pair budget."""
    documents = (
        _completed_document(LOW_ELAPSED_NS),
        _completed_document(MATCH_ELAPSED_NS),
        _completed_document(HIGH_ELAPSED_NS),
    )

    with pytest.raises(
        TicketAdmissionTelemetryOverlapComponentsError,
        match="unique document pairs exceed configured limit",
    ):
        _ = build_ticket_admission_telemetry_overlap_components(
            documents,
            max_pairs=2,
        )


def test_invalid_typed_document_fails_before_components() -> None:
    """A forged schema cannot become a compatibility-graph vertex."""
    document = _completed_document(LOW_ELAPSED_NS)
    malformed = replace(document, schema_version=True)

    with pytest.raises(
        TicketAdmissionTelemetryOverlapComponentsError,
        match="document schema is unsupported",
    ):
        _ = build_ticket_admission_telemetry_overlap_components(
            (malformed, document)
        )


class _ConstantDigest:
    @staticmethod
    def hexdigest() -> str:
        """Return one deterministic forged digest.

        Returns:
            A fixed 64-character hexadecimal string.

        """
        return "0" * 64


def _constant_sha256(payload: bytes) -> _ConstantDigest:
    _ = payload
    return _ConstantDigest()


def test_component_fingerprint_collision_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Distinct components may never share one component identity."""
    monkeypatch.setattr(components_module, "sha256", _constant_sha256)
    documents = (
        _completed_document(LOW_ELAPSED_NS),
        _completed_document(HIGH_ELAPSED_NS),
    )

    with pytest.raises(
        TicketAdmissionTelemetryOverlapComponentsError,
        match="component fingerprint collision detected",
    ):
        _ = build_ticket_admission_telemetry_overlap_components(documents)
