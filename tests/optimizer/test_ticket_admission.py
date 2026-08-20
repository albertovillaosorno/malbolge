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
#   - Ticket admission, reporting, and exact CUDA profile regressions.
# - Must-Not:
#   - Generalize retained RTX 4060 evidence or weaken synchronous fallback.
# - Allows:
#   - Inputs: synthetic comparison records and scoped live CUDA tickets.
#   - Outputs: deterministic chunk, rejection, exactness, and cleanup
#     assertions.
#   - Side effects: scoped optional CUDA execution only.
# - Split-When:
#   - Split when another device profile gains independent retained evidence.
# - Merge-When:
#   - Merge when another suite owns this exact admission contract.
# - Summary:
#   - Conservative ticket admission regressions.
# - Description:
#   - Proves grouping, rejection reporting, and exact profile binding.
# - Usage:
#   - Runs with optimizer tests; live routes skip without CUDA.
# - Defaults:
#   - Missing or negative evidence leaves singleton synchronous execution.
#

"""Conservative evidence-bound ticket route and group admission tests."""

from __future__ import annotations

from dataclasses import replace
import platform
from typing import TYPE_CHECKING
from typing import cast
from typing import final

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.cuda import CudaHostRuntimeIdentity
from accelerator.cuda import CudaRuntimeIdentity
from accelerator.cuda import cuda_ticket_admission_profile
from accelerator.cuda import cuda_ticket_admission_profile_id
from accelerator.cuda import cuda_ticket_admission_workload_id
from accelerator.cuda import execute_retained_cuda_tickets
from accelerator.cuda import (
    execute_retained_cuda_tickets_with_attempt_telemetry,
)
from accelerator.cuda import execute_retained_cuda_tickets_with_telemetry
from accelerator.cuda import load_cuda_ticket_admission_profiles
from accelerator.cuda import plan_retained_cuda_tickets
from accelerator.cuda import plan_retained_cuda_tickets_with_report
from accelerator.cuda import resolve_cuda_ticket_admission_profile
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorExecutionError
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PackedPrimitiveResult
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import prepare_packed_primitive_batch
from accelerator.ticket_admission import TicketAdmissionError
from accelerator.ticket_admission import TicketAdmissionRequest
from accelerator.ticket_admission import TicketRouteCandidate
from accelerator.ticket_admission import TicketRouteRejection
from accelerator.ticket_admission import TicketSubmissionMode
from accelerator.ticket_admission import plan_ticket_submissions
from accelerator.ticket_admission import plan_ticket_submissions_with_report
from accelerator.ticket_admission import ticket_route_admission_id
from accelerator.ticket_admission import ticket_route_admission_report_id
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionAttemptTelemetry,
)
from accelerator.ticket_admission_telemetry import TicketAdmissionFailureKind
from accelerator.ticket_admission_telemetry import (
    TicketAdmissionFailureTelemetry,
)
from accelerator.ticket_admission_telemetry import TicketAdmissionTelemetry
import pytest

if TYPE_CHECKING:
    from accelerator.exact_primitives import PreparedPrimitiveBatch

GENERIC_ADMISSION_ID = "evidence-bound-ticket-route-admission-v1"
GENERIC_REPORT_ID = "evidence-bound-ticket-route-admission-report-v1"
CUDA_PROFILE_ID = "rtx4060-full-domain-crazy-ticket-admission-2026-07-29-v1"
CUDA_WORKLOAD_ID = "classic-crazy-full-domain-ticket-transfer-v1"
BENCHMARK_ID = "test-ticket-route-v1"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "exact-test-workload-v1"
WORD_BYTES = 4
FALLBACK_NS = 100
THREE_FALLBACK_NS = 3 * FALLBACK_NS
TRIPLE_TICKET_COUNT = 3
TEN_TICKET_COUNT = 10
COMPOSED_NS = 680
PAIR_GROUP_SIZE = 2
RETAINED_TEN_NS = 7_327_100
DISPLAY_DRIVER_VERSION = "610.88"
HOST_RUNTIME_IDENTITY = CudaHostRuntimeIdentity(
    host_edition="Professional",
    host_machine="x86_64",
    host_release="11",
    host_system="Windows",
    host_version="10.0.26200",
    identity_id="cuda-host-runtime-identity-v1",
    python_implementation="CPython",
    python_version="3.14.6",
)
MATCHING_RUNTIME = CudaRuntimeIdentity(
    display_driver_version=DISPLAY_DRIVER_VERSION,
    driver_api_version=13_030,
    host_runtime_identity=HOST_RUNTIME_IDENTITY,
    identity_id="cuda-runtime-toolchain-identity-v1",
    nvrtc_major=13,
    nvrtc_minor=3,
    toolchain_manifest_sha256=(
        "b8249cc1accf4b0532779c7c42e6505c9840d7208b4ab945e54daa456206b95e"
    ),
)


@final
class _RetainedAdapterStub:
    runtime_identity: CudaRuntimeIdentity = MATCHING_RUNTIME

    @staticmethod
    def capability() -> AcceleratorCapability:
        return AcceleratorCapability(
            backend_id="cuda",
            device_arch="sm_89",
            device_name="NVIDIA GeForce RTX 4060",
        )


def _retained_adapter_stub() -> CudaExactPrimitiveAdapter:
    return cast(
        "CudaExactPrimitiveAdapter",
        cast("object", _RetainedAdapterStub()),
    )


def _request(ticket_count: int) -> TicketAdmissionRequest:
    return TicketAdmissionRequest(
        backend_id=BACKEND_ID,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        ticket_count=ticket_count,
        workload_id=WORKLOAD_ID,
    )


def _candidate(  # ruff: ignore[too-many-arguments]
    mode: TicketSubmissionMode,
    group_size: int,
    *,
    candidate_ns: int,
    paired_wins: int,
    reference_ns: int,
    **overrides: object,
) -> TicketRouteCandidate:
    values: dict[str, object] = {
        "backend_id": BACKEND_ID,
        "benchmark_id": BENCHMARK_ID,
        "candidate_median_ns": candidate_ns,
        "device_arch": DEVICE_ARCH,
        "device_name": DEVICE_NAME,
        "exact_results": True,
        "group_size": group_size,
        "mode": mode,
        "paired_wins": paired_wins,
        "reference_median_ns": reference_ns,
        "sample_count": 15,
        "workload_id": WORKLOAD_ID,
    }
    values.update(overrides)
    return TicketRouteCandidate(**values)  # pyright: ignore[reportArgumentType]


def _cuda() -> CudaExactPrimitiveAdapter:
    try:
        return CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        pytest.skip(f"CUDA unavailable: {error}")


def _prepared_full_domain() -> PreparedPrimitiveBatch:
    data = b"".join(
        value.to_bytes(WORD_BYTES, "little") for value in range(MAX_WORD + 1)
    )
    return prepare_packed_primitive_batch(
        accumulators_u32le=b"\0" * len(data),
        data_u32le=data,
        kind=PrimitiveKind.CRAZY,
    )


def _packed_cpu_result(
    adapter: CudaExactPrimitiveAdapter,
    prepared: PreparedPrimitiveBatch,
) -> PackedPrimitiveResult:
    cpu_result = CpuExactPrimitiveAdapter().evaluate_prepared(prepared)
    return PackedPrimitiveResult(
        capability=adapter.capability(),
        words_u32le=b"".join(
            value.to_bytes(WORD_BYTES, "little") for value in cpu_result.values
        ),
    )


def test_ticket_route_admission_identity_is_stable() -> None:
    """Planning and retained CUDA profile identities remain versioned."""
    assert ticket_route_admission_id() == GENERIC_ADMISSION_ID
    assert ticket_route_admission_report_id() == GENERIC_REPORT_ID
    assert cuda_ticket_admission_profile_id() == CUDA_PROFILE_ID
    assert cuda_ticket_admission_workload_id() == CUDA_WORKLOAD_ID


def test_missing_evidence_keeps_singleton_synchronous_fallback() -> None:
    """No comparison evidence never invents grouping or streaming."""
    plan = plan_ticket_submissions(
        _request(3),
        candidates=(),
        fallback_ticket_ns=FALLBACK_NS,
    )
    assert plan.estimated_ns == THREE_FALLBACK_NS
    assert [(chunk.start, chunk.stop) for chunk in plan.chunks] == [
        (0, 1),
        (1, 2),
        (2, 3),
    ]
    assert all(chunk.evidence_id is None for chunk in plan.chunks)
    assert all(
        chunk.mode is TicketSubmissionMode.SYNCHRONOUS for chunk in plan.chunks
    )


def test_opt_in_report_preserves_empty_evidence_fallback_plan() -> None:
    """Reporting an empty evidence set does not coalesce safe fallbacks."""
    report = plan_ticket_submissions_with_report(
        _request(3),
        candidates=(),
        fallback_ticket_ns=FALLBACK_NS,
    )
    ordinary = plan_ticket_submissions(
        _request(3),
        candidates=(),
        fallback_ticket_ns=FALLBACK_NS,
    )

    assert report.report_id == GENERIC_REPORT_ID
    assert report.plan == ordinary
    assert report.assessments == ()
    assert report.fallback_ticket_count == TRIPLE_TICKET_COUNT
    assert report.selected_synchronous_ticket_count == 0
    assert report.selected_streamed_ticket_count == 0


def test_opt_in_report_classifies_route_rejections_in_input_order() -> None:
    """Context, exactness, median, majority, and size failures stay explicit."""
    candidates = (
        _candidate(
            TicketSubmissionMode.SYNCHRONOUS,
            2,
            candidate_ns=80,
            reference_ns=180,
            paired_wins=15,
            device_name="another device",
        ),
        _candidate(
            TicketSubmissionMode.SYNCHRONOUS,
            2,
            candidate_ns=80,
            reference_ns=180,
            paired_wins=15,
            exact_results=False,
        ),
        _candidate(
            TicketSubmissionMode.SYNCHRONOUS,
            4,
            candidate_ns=180,
            reference_ns=180,
            paired_wins=15,
        ),
        _candidate(
            TicketSubmissionMode.SYNCHRONOUS,
            8,
            candidate_ns=80,
            reference_ns=180,
            paired_wins=7,
        ),
        _candidate(
            TicketSubmissionMode.SYNCHRONOUS,
            16,
            candidate_ns=80,
            reference_ns=180,
            paired_wins=15,
        ),
    )
    report = plan_ticket_submissions_with_report(
        _request(10),
        candidates=candidates,
        fallback_ticket_ns=FALLBACK_NS,
    )

    assert tuple(
        assessment.rejection_reasons for assessment in report.assessments
    ) == (
        (TicketRouteRejection.CONTEXT_MISMATCH,),
        (TicketRouteRejection.INEXACT_RESULTS,),
        (TicketRouteRejection.NO_MEDIAN_IMPROVEMENT,),
        (TicketRouteRejection.NO_PAIRED_MAJORITY,),
        (TicketRouteRejection.GROUP_EXCEEDS_QUEUE,),
    )
    assert all(not assessment.eligible for assessment in report.assessments)
    assert report.fallback_ticket_count == TEN_TICKET_COUNT


def test_report_never_attributes_use_to_mismatched_route() -> None:
    """A rejected same-ID route cannot inherit another context's usage."""
    mismatched = _candidate(
        TicketSubmissionMode.SYNCHRONOUS,
        2,
        candidate_ns=80,
        reference_ns=180,
        paired_wins=15,
        device_name="another device",
    )
    matching = _candidate(
        TicketSubmissionMode.SYNCHRONOUS,
        2,
        candidate_ns=80,
        reference_ns=180,
        paired_wins=15,
    )
    report = plan_ticket_submissions_with_report(
        _request(2),
        candidates=(mismatched, matching),
        fallback_ticket_ns=FALLBACK_NS,
    )

    rejected, selected = report.assessments
    assert rejected.evidence_id == selected.evidence_id
    assert rejected.rejection_reasons == (
        TicketRouteRejection.CONTEXT_MISMATCH,
    )
    assert rejected.selected_chunk_count == 0
    assert rejected.selected_ticket_count == 0
    assert selected.selected_chunk_count == 1
    assert selected.selected_ticket_count == PAIR_GROUP_SIZE


def test_opt_in_report_records_selected_and_unused_eligible_routes() -> None:
    """Eligibility and final-plan selection remain distinct observations."""
    candidates = tuple(
        _candidate(
            mode,
            2,
            candidate_ns=80,
            reference_ns=180,
            paired_wins=15,
        )
        for mode in (
            TicketSubmissionMode.SYNCHRONOUS,
            TicketSubmissionMode.STREAMED,
        )
    )
    report = plan_ticket_submissions_with_report(
        _request(2),
        candidates=candidates,
        fallback_ticket_ns=FALLBACK_NS,
    )

    synchronous, streamed = report.assessments
    assert synchronous.eligible
    assert synchronous.selected_chunk_count == 1
    assert synchronous.selected_ticket_count == PAIR_GROUP_SIZE
    assert streamed.eligible
    assert streamed.selected_chunk_count == 0
    assert streamed.selected_ticket_count == 0
    assert report.selected_synchronous_ticket_count == PAIR_GROUP_SIZE
    assert report.selected_streamed_ticket_count == 0
    assert report.fallback_ticket_count == 0


def test_positive_groups_compose_while_streaming_evidence_is_rejected() -> None:
    """Fewest exact groups win; negative streamed comparisons stay unused."""
    candidates = (
        _candidate(
            TicketSubmissionMode.SYNCHRONOUS,
            2,
            candidate_ns=80,
            reference_ns=180,
            paired_wins=15,
        ),
        _candidate(
            TicketSubmissionMode.SYNCHRONOUS,
            8,
            candidate_ns=600,
            reference_ns=760,
            paired_wins=15,
        ),
        _candidate(
            TicketSubmissionMode.STREAMED,
            8,
            candidate_ns=1_200,
            reference_ns=600,
            paired_wins=0,
        ),
    )
    plan = plan_ticket_submissions(
        _request(10),
        candidates=candidates,
        fallback_ticket_ns=FALLBACK_NS,
    )
    assert [(chunk.start, chunk.stop) for chunk in plan.chunks] == [
        (0, 2),
        (2, 10),
    ]
    assert plan.estimated_ns == COMPOSED_NS
    assert all(
        chunk.mode is TicketSubmissionMode.SYNCHRONOUS for chunk in plan.chunks
    )


def test_equal_cost_prefers_synchronous_over_streamed() -> None:
    """A route tie stays on the simpler synchronous lifetime."""
    candidates = tuple(
        _candidate(
            mode,
            2,
            candidate_ns=80,
            reference_ns=180,
            paired_wins=15,
        )
        for mode in (
            TicketSubmissionMode.SYNCHRONOUS,
            TicketSubmissionMode.STREAMED,
        )
    )
    plan = plan_ticket_submissions(
        _request(2),
        candidates=candidates,
        fallback_ticket_ns=FALLBACK_NS,
    )
    assert len(plan.chunks) == 1
    assert plan.chunks[0].mode is TicketSubmissionMode.SYNCHRONOUS


def test_mismatched_evidence_is_ignored_without_extrapolation() -> None:
    """Another device's positive result cannot alter this request."""
    mismatched = _candidate(
        TicketSubmissionMode.STREAMED,
        2,
        candidate_ns=1,
        reference_ns=200,
        paired_wins=15,
        device_name="another device",
    )
    plan = plan_ticket_submissions(
        _request(2),
        candidates=(mismatched,),
        fallback_ticket_ns=FALLBACK_NS,
    )
    assert len(plan.chunks) == PAIR_GROUP_SIZE
    assert all(chunk.evidence_id is None for chunk in plan.chunks)


def test_duplicate_matching_route_evidence_fails_closed() -> None:
    """Conflicting same-route evidence cannot be cherry-picked."""
    candidate = _candidate(
        TicketSubmissionMode.SYNCHRONOUS,
        2,
        candidate_ns=80,
        reference_ns=180,
        paired_wins=15,
    )
    with pytest.raises(TicketAdmissionError, match="duplicate route evidence"):
        _ = plan_ticket_submissions(
            _request(2),
            candidates=(candidate, candidate),
            fallback_ticket_ns=FALLBACK_NS,
        )


def test_opt_in_report_rejects_duplicate_matching_evidence() -> None:
    """Instrumentation cannot bypass the ordinary duplicate-evidence gate."""
    candidate = _candidate(
        TicketSubmissionMode.SYNCHRONOUS,
        2,
        candidate_ns=80,
        reference_ns=180,
        paired_wins=15,
    )
    with pytest.raises(TicketAdmissionError, match="duplicate route evidence"):
        _ = plan_ticket_submissions_with_report(
            _request(2),
            candidates=(candidate, candidate),
            fallback_ticket_ns=FALLBACK_NS,
        )


def test_ticket_identity_and_mode_types_fail_closed() -> None:
    """Foreign identity and mode values never escape as downstream errors."""
    malformed_request = replace(
        _request(1),
        backend_id=cast("str", cast("object", 1)),
    )
    with pytest.raises(TicketAdmissionError, match="non-empty string"):
        _ = malformed_request.validated()

    malformed_candidate = _candidate(
        cast(
            "TicketSubmissionMode",
            cast("object", TicketSubmissionMode.SYNCHRONOUS.value),
        ),
        1,
        candidate_ns=80,
        reference_ns=180,
        paired_wins=15,
    )
    with pytest.raises(TicketAdmissionError, match="exact enum"):
        _ = malformed_candidate.validated()


def test_malformed_ticket_medians_fail_closed() -> None:
    """Boolean or floating evidence cannot become retained nanoseconds."""
    cases = (
        _candidate(
            TicketSubmissionMode.SYNCHRONOUS,
            2,
            candidate_ns=True,
            reference_ns=180,
            paired_wins=15,
        ),
        _candidate(
            TicketSubmissionMode.SYNCHRONOUS,
            2,
            candidate_ns=80,
            reference_ns=cast("int", 180.5),
            paired_wins=15,
        ),
    )
    for candidate in cases:
        with pytest.raises(TicketAdmissionError, match="positive integers"):
            _ = candidate.validated()


def test_malformed_paired_counts_fail_closed() -> None:
    """Impossible paired-win evidence is rejected before planning."""
    malformed = _candidate(
        TicketSubmissionMode.SYNCHRONOUS,
        2,
        candidate_ns=80,
        reference_ns=180,
        paired_wins=16,
    )
    with pytest.raises(TicketAdmissionError, match="paired wins"):
        _ = plan_ticket_submissions(
            _request(2),
            candidates=(malformed,),
            fallback_ticket_ns=FALLBACK_NS,
        )


def test_cuda_profile_requires_exact_measured_capability() -> None:
    """The retained profile never generalizes to another device name."""
    exact = AcceleratorCapability(
        backend_id="cuda",
        device_arch="sm_89",
        device_name="NVIDIA GeForce RTX 4060",
    )
    mismatch = AcceleratorCapability(
        backend_id="cuda",
        device_arch="sm_89",
        device_name="another sm_89 device",
    )
    profile = cuda_ticket_admission_profile(exact, MATCHING_RUNTIME)
    assert profile is not None
    assert profile.profile_id == CUDA_PROFILE_ID
    assert cuda_ticket_admission_profile(mismatch, MATCHING_RUNTIME) is None
    assert plan_retained_cuda_tickets(mismatch, MATCHING_RUNTIME, 8) is None


def test_registry_resolver_selects_exact_runtime_variant() -> None:
    """Two runtime variants resolve independently for one workload/device."""
    current = load_cuda_ticket_admission_profiles()[0]
    alternate = replace(
        current,
        profile_id="rtx4060-alternate-driver-v1",
        runtime=replace(current.runtime, display_driver_version="611.00"),
    )
    capability = AcceleratorCapability(
        backend_id="cuda",
        device_arch="sm_89",
        device_name="NVIDIA GeForce RTX 4060",
    )
    profiles = (current, alternate)
    assert (
        resolve_cuda_ticket_admission_profile(
            profiles,
            capability=capability,
            runtime_identity=MATCHING_RUNTIME,
            workload_id=current.workload_id,
        )
        is current
    )
    assert (
        resolve_cuda_ticket_admission_profile(
            profiles,
            capability=capability,
            runtime_identity=replace(
                MATCHING_RUNTIME,
                display_driver_version="611.00",
            ),
            workload_id=current.workload_id,
        )
        is alternate
    )


def test_registry_resolver_returns_none_for_unknown_workload() -> None:
    """A registry never extrapolates one profile to another workload."""
    current = load_cuda_ticket_admission_profiles()[0]
    capability = AcceleratorCapability(
        backend_id="cuda",
        device_arch="sm_89",
        device_name="NVIDIA GeForce RTX 4060",
    )
    assert (
        resolve_cuda_ticket_admission_profile(
            (current,),
            capability=capability,
            runtime_identity=MATCHING_RUNTIME,
            workload_id="unknown-exact-workload-v1",
        )
        is None
    )


def test_registry_resolver_rejects_invalid_workload_identity() -> None:
    """Empty workload identity fails before registry selection."""
    current = load_cuda_ticket_admission_profiles()[0]
    capability = AcceleratorCapability(
        backend_id="cuda",
        device_arch="sm_89",
        device_name="NVIDIA GeForce RTX 4060",
    )
    with pytest.raises(
        TicketAdmissionError, match="workload identity is invalid"
    ):
        _ = resolve_cuda_ticket_admission_profile(
            (current,),
            capability=capability,
            runtime_identity=MATCHING_RUNTIME,
            workload_id="",
        )


def test_registry_resolver_rejects_ambiguous_exact_profiles() -> None:
    """An unvalidated duplicate tuple still fails closed at resolution."""
    current = load_cuda_ticket_admission_profiles()[0]
    duplicate = replace(current, profile_id="duplicate-profile-v1")
    capability = AcceleratorCapability(
        backend_id="cuda",
        device_arch="sm_89",
        device_name="NVIDIA GeForce RTX 4060",
    )
    with pytest.raises(TicketAdmissionError, match="multiple exact profiles"):
        _ = resolve_cuda_ticket_admission_profile(
            (current, duplicate),
            capability=capability,
            runtime_identity=MATCHING_RUNTIME,
            workload_id=current.workload_id,
        )


@pytest.mark.parametrize(
    "runtime_identity",
    [
        replace(MATCHING_RUNTIME, driver_api_version=13_029),
        replace(MATCHING_RUNTIME, nvrtc_minor=2),
        replace(MATCHING_RUNTIME, toolchain_manifest_sha256="0" * 64),
        replace(MATCHING_RUNTIME, display_driver_version=None),
        replace(MATCHING_RUNTIME, display_driver_version="611.00"),
        replace(MATCHING_RUNTIME, host_runtime_identity=None),
        replace(
            MATCHING_RUNTIME,
            host_runtime_identity=replace(
                HOST_RUNTIME_IDENTITY,
                host_version="10.0.99999",
            ),
        ),
    ],
)
def test_cuda_profile_rejects_runtime_identity_drift(
    runtime_identity: CudaRuntimeIdentity,
) -> None:
    """Host, display, Driver API, NVRTC, and manifest drift are rejected."""
    capability = AcceleratorCapability(
        backend_id="cuda",
        device_arch="sm_89",
        device_name="NVIDIA GeForce RTX 4060",
    )
    assert cuda_ticket_admission_profile(capability, runtime_identity) is None
    assert plan_retained_cuda_tickets(capability, runtime_identity, 8) is None


def test_retained_cuda_profile_selects_sync_group_two_plus_eight() -> None:
    """Ten retained tickets use two positive synchronous comparisons."""
    capability = AcceleratorCapability(
        backend_id="cuda",
        device_arch="sm_89",
        device_name="NVIDIA GeForce RTX 4060",
    )
    plan = plan_retained_cuda_tickets(capability, MATCHING_RUNTIME, 10)
    assert plan is not None
    assert [(chunk.start, chunk.stop) for chunk in plan.chunks] == [
        (0, 2),
        (2, 10),
    ]
    assert plan.estimated_ns == RETAINED_TEN_NS
    assert all(
        chunk.mode is TicketSubmissionMode.SYNCHRONOUS for chunk in plan.chunks
    )
    assert all(chunk.evidence_id is not None for chunk in plan.chunks)


def test_retained_cuda_report_matches_ordinary_plan() -> None:
    """Exact retained instrumentation explains but never changes selection."""
    capability = AcceleratorCapability(
        backend_id="cuda",
        device_arch="sm_89",
        device_name="NVIDIA GeForce RTX 4060",
    )
    ordinary = plan_retained_cuda_tickets(capability, MATCHING_RUNTIME, 10)
    report = plan_retained_cuda_tickets_with_report(
        capability,
        MATCHING_RUNTIME,
        10,
    )
    mismatch = replace(capability, device_name="another sm_89 device")

    assert ordinary is not None
    assert report is not None
    assert report.plan == ordinary
    assert report.report_id == GENERIC_REPORT_ID
    assert report.fallback_ticket_count == 0
    assert report.selected_synchronous_ticket_count == TEN_TICKET_COUNT
    assert report.selected_streamed_ticket_count == 0
    selected = tuple(
        assessment.selected_ticket_count
        for assessment in report.assessments
        if assessment.selected_ticket_count
    )
    assert selected == (2, 8)
    assert (
        plan_retained_cuda_tickets_with_report(
            mismatch,
            MATCHING_RUNTIME,
            10,
        )
        is None
    )


@pytest.mark.skipif(
    platform.system() != HOST_RUNTIME_IDENTITY.host_system,
    reason="retained CUDA ticket-admission evidence is Windows-specific",
)
def test_live_retained_executor_uses_only_synchronous_exact_tickets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The group-two plan publishes CPU-equal bytes without streaming."""
    prepared = _prepared_full_domain()
    expected = CpuExactPrimitiveAdapter().evaluate_prepared(prepared)
    expected_words = b"".join(
        value.to_bytes(WORD_BYTES, "little") for value in expected.values
    )

    def reject_streaming(*arguments: object, **keywords: object) -> object:
        del arguments, keywords
        message = "negative streamed evidence was incorrectly admitted"
        raise AssertionError(message)

    with _cuda() as cuda:
        monkeypatch.setattr(cuda.ticket_transfers, "submit", reject_streaming)
        executed = execute_retained_cuda_tickets(cuda, prepared, 2)

    assert executed is not None
    plan, results = executed
    assert len(plan.chunks) == 1
    assert plan.chunks[0].ticket_count == PAIR_GROUP_SIZE
    assert plan.chunks[0].mode is TicketSubmissionMode.SYNCHRONOUS
    assert len(results) == PAIR_GROUP_SIZE
    assert all(result.words_u32le == expected_words for result in results)


@pytest.mark.skipif(
    platform.system() != HOST_RUNTIME_IDENTITY.host_system,
    reason="retained CUDA ticket-admission evidence is Windows-specific",
)
def test_live_retained_telemetry_records_completed_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The explicit telemetry path records only a completed exact plan."""
    prepared = _prepared_full_domain()
    telemetry = TicketAdmissionTelemetry(capacity=1)

    def reject_streaming(*arguments: object, **keywords: object) -> object:
        del arguments, keywords
        message = "negative streamed evidence was incorrectly admitted"
        raise AssertionError(message)

    with _cuda() as cuda:
        monkeypatch.setattr(cuda.ticket_transfers, "submit", reject_streaming)
        executed = execute_retained_cuda_tickets_with_telemetry(
            cuda,
            prepared,
            PAIR_GROUP_SIZE,
            telemetry=telemetry,
        )

    assert executed is not None
    report, results = executed
    snapshot = telemetry.snapshot()
    assert report.plan.request.ticket_count == PAIR_GROUP_SIZE
    assert len(results) == PAIR_GROUP_SIZE
    assert len(snapshot.observations) == 1
    observation = snapshot.observations[0]
    assert observation.ticket_count == PAIR_GROUP_SIZE
    assert observation.selected_synchronous_ticket_count == PAIR_GROUP_SIZE
    assert observation.selected_streamed_ticket_count == 0
    assert observation.elapsed_ns >= 0


@pytest.mark.skipif(
    platform.system() != HOST_RUNTIME_IDENTITY.host_system,
    reason="retained CUDA ticket-admission evidence is Windows-specific",
)
def test_live_retained_executor_rejects_wrong_prepared_workload() -> None:
    """An exact capability cannot authorize another prepared payload."""
    prepared = prepare_packed_primitive_batch(
        accumulators_u32le=(0).to_bytes(WORD_BYTES, "little"),
        data_u32le=(0).to_bytes(WORD_BYTES, "little"),
        kind=PrimitiveKind.CRAZY,
    )
    with (
        _cuda() as cuda,
        pytest.raises(TicketAdmissionError, match="identity mismatched"),
    ):
        _ = execute_retained_cuda_tickets(cuda, prepared, 1)


def test_retained_attempt_telemetry_records_failure_and_reraises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An admitted accelerator failure is recorded and re-raised unchanged."""
    prepared = _prepared_full_domain()
    completed = TicketAdmissionTelemetry(capacity=1)
    failed = TicketAdmissionFailureTelemetry(capacity=1)
    telemetry = TicketAdmissionAttemptTelemetry(
        completed=completed,
        failed=failed,
    )
    failure = AcceleratorExecutionError("sensitive synthetic CUDA detail")

    def reject_execution(*arguments: object, **keywords: object) -> object:
        del arguments, keywords
        raise failure

    monkeypatch.setattr(
        "accelerator.cuda.ticket_admission._execute_plan",
        reject_execution,
    )
    adapter = _retained_adapter_stub()

    with pytest.raises(
        AcceleratorExecutionError,
        match="sensitive synthetic CUDA detail",
    ) as caught:
        _ = execute_retained_cuda_tickets_with_attempt_telemetry(
            adapter,
            prepared,
            PAIR_GROUP_SIZE,
            telemetry=telemetry,
        )

    assert caught.value is failure
    assert completed.snapshot().observations == ()
    snapshot = failed.snapshot()
    assert len(snapshot.observations) == 1
    observation = snapshot.observations[0]
    assert observation.failure_kind is TicketAdmissionFailureKind.EXECUTION
    assert observation.ticket_count == PAIR_GROUP_SIZE
    assert observation.elapsed_ns >= 0
    assert not hasattr(observation, "message")


def test_retained_attempt_telemetry_records_completed_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful admitted attempt mutates only the completed FIFO."""
    prepared = _prepared_full_domain()
    telemetry = TicketAdmissionAttemptTelemetry(
        completed=TicketAdmissionTelemetry(capacity=1),
        failed=TicketAdmissionFailureTelemetry(capacity=1),
    )
    adapter = _retained_adapter_stub()
    expected = (_packed_cpu_result(adapter, prepared),) * PAIR_GROUP_SIZE

    def complete_execution(
        *arguments: object,
        **keywords: object,
    ) -> tuple[PackedPrimitiveResult, ...]:
        del arguments, keywords
        return expected

    monkeypatch.setattr(
        "accelerator.cuda.ticket_admission._execute_plan",
        complete_execution,
    )

    executed = execute_retained_cuda_tickets_with_attempt_telemetry(
        adapter,
        prepared,
        PAIR_GROUP_SIZE,
        telemetry=telemetry,
    )

    assert executed is not None
    assert executed[1] == expected
    assert telemetry.failed.snapshot().observations == ()
    observations = telemetry.completed.snapshot().observations
    assert len(observations) == 1
    assert observations[0].ticket_count == PAIR_GROUP_SIZE
    assert observations[0].report_id == executed[0].report_id
    assert observations[0].elapsed_ns >= 0
