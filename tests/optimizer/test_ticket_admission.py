# File:
#   - test_ticket_admission.py
# Path:
#   - tests/optimizer/test_ticket_admission.py
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
#   - Evidence-bound ticket route/group admission and exact CUDA profile tests.
# - Must-Not:
#   - Generalize retained RTX 4060 evidence or weaken synchronous fallback.
# - Allows:
#   - Inputs: synthetic comparison records and scoped live CUDA tickets.
# - Outputs: deterministic chunk, rejection, exactness, and cleanup assertions.
# - Side effects: scoped optional CUDA execution only.
# - Split-When:
#   - Split when online telemetry or another device profile is implemented.
# - Merge-When:
#   - Merge when another suite owns this exact admission contract.
# - Summary:
#   - Conservative ticket admission regressions.
# - Description:
#   - Proves positive grouping, negative streaming, and exact profile binding.
# - Usage:
#   - Runs with optimizer tests; live routes skip without CUDA.
# - Defaults:
#   - Missing or negative evidence leaves singleton synchronous execution.
#
# Related documents:
# - accelerator/ticket_admission.py
# - accelerator/cuda/ticket_admission.py
#
# Large file:
#   - false
#

"""Conservative evidence-bound ticket route and group admission tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from accelerator.cpu import CpuExactPrimitiveAdapter
from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.cuda import CudaRuntimeIdentity
from accelerator.cuda import cuda_ticket_admission_profile
from accelerator.cuda import cuda_ticket_admission_profile_id
from accelerator.cuda import execute_retained_cuda_tickets
from accelerator.cuda import plan_retained_cuda_tickets
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PrimitiveKind
from accelerator.exact_primitives import prepare_packed_primitive_batch
from accelerator.ticket_admission import TicketAdmissionError
from accelerator.ticket_admission import TicketAdmissionRequest
from accelerator.ticket_admission import TicketRouteCandidate
from accelerator.ticket_admission import TicketSubmissionMode
from accelerator.ticket_admission import plan_ticket_submissions
from accelerator.ticket_admission import ticket_route_admission_id

if TYPE_CHECKING:
    from accelerator.exact_primitives import PreparedPrimitiveBatch

GENERIC_ADMISSION_ID = "evidence-bound-ticket-route-admission-v1"
CUDA_PROFILE_ID = "rtx4060-full-domain-crazy-ticket-admission-2026-07-29-v1"
BENCHMARK_ID = "test-ticket-route-v1"
BACKEND_ID = "cuda"
DEVICE_ARCH = "sm_test"
DEVICE_NAME = "test device"
WORKLOAD_ID = "exact-test-workload-v1"
WORD_BYTES = 4
FALLBACK_NS = 100
THREE_FALLBACK_NS = 3 * FALLBACK_NS
COMPOSED_NS = 680
PAIR_GROUP_SIZE = 2
RETAINED_TEN_NS = 7_327_100
MATCHING_RUNTIME = CudaRuntimeIdentity(
    driver_api_version=13_030,
    identity_id="cuda-runtime-toolchain-identity-v1",
    nvrtc_major=13,
    nvrtc_minor=3,
    toolchain_manifest_sha256=(
        "b8249cc1accf4b0532779c7c42e6505c9840d7208b4ab945e54daa456206b95e"
    ),
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


def test_ticket_route_admission_identity_is_stable() -> None:
    """Planning and retained CUDA profile identities remain versioned."""
    assert ticket_route_admission_id() == GENERIC_ADMISSION_ID
    assert cuda_ticket_admission_profile_id() == CUDA_PROFILE_ID


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


@pytest.mark.parametrize(
    "runtime_identity",
    [
        CudaRuntimeIdentity(
            driver_api_version=13_029,
            identity_id=MATCHING_RUNTIME.identity_id,
            nvrtc_major=13,
            nvrtc_minor=3,
            toolchain_manifest_sha256=(
                MATCHING_RUNTIME.toolchain_manifest_sha256
            ),
        ),
        CudaRuntimeIdentity(
            driver_api_version=13_030,
            identity_id=MATCHING_RUNTIME.identity_id,
            nvrtc_major=13,
            nvrtc_minor=2,
            toolchain_manifest_sha256=(
                MATCHING_RUNTIME.toolchain_manifest_sha256
            ),
        ),
        CudaRuntimeIdentity(
            driver_api_version=13_030,
            identity_id=MATCHING_RUNTIME.identity_id,
            nvrtc_major=13,
            nvrtc_minor=3,
            toolchain_manifest_sha256="0" * 64,
        ),
    ],
)
def test_cuda_profile_rejects_runtime_identity_drift(
    runtime_identity: CudaRuntimeIdentity,
) -> None:
    """Driver API, NVRTC, and manifest mismatch prevent profile resolution."""
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
