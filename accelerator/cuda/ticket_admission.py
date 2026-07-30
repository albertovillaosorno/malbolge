# File:
#   - ticket_admission.py
# Path:
#   - accelerator/cuda/ticket_admission.py
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
#   - The retained RTX 4060 full-domain CRAZY ticket admission profile.
# - Must-Not:
#   - Generalize one-device evidence to other devices or enable streaming.
# - Allows:
#   - Inputs: exact CUDA capability and pending ticket count.
# - Outputs: an optional evidence profile and deterministic admission plan.
# - Side effects: none.
# - Split-When:
#   - Split when another workload/device obtains independent retained evidence.
# - Merge-When:
#   - Merge when a generated profile registry owns this exact evidence mapping.
# - Summary:
#   - Retained CUDA ticket route admission profile.
# - Description:
#   - Binds positive sync grouping and negative streamed comparisons.
# - Usage:
#   - Opt-in planning for the retained workload; ordinary defaults are
#     unchanged.
# - Defaults:
#   - Capability mismatch returns no profile and therefore no automatic plan.
#
# Related documents:
# - benchmarks/accelerator/evidence/
#   2026-07-29-independent-ticket-transfer-throughput-rtx4060/README.md
#
# Large file:
#   - false
#

"""Retained CUDA ticket route admission for one exact evidence context."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Final
from typing import TYPE_CHECKING

from accelerator.ticket_admission import TicketAdmissionError
from accelerator.ticket_admission import TicketAdmissionRequest
from accelerator.ticket_admission import TicketRouteCandidate
from accelerator.ticket_admission import TicketSubmissionMode
from accelerator.ticket_admission import plan_ticket_submissions

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.cuda.exact_primitives import CudaExactPrimitiveAdapter
    from accelerator.cuda.exact_primitives import CudaPrimitiveEvaluationTicket
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.exact_primitives import PackedPrimitiveResult
    from accelerator.exact_primitives import PreparedPrimitiveBatch
    from accelerator.ticket_admission import TicketAdmissionPlan

CUDA_TICKET_ADMISSION_PROFILE_ID: Final = (
    "rtx4060-full-domain-crazy-ticket-admission-2026-07-29-v1"
)
EVIDENCE_BENCHMARK_ID: Final = "cuda-independent-ticket-transfer-throughput-v1"
EVIDENCE_SOURCE_COMMIT: Final = "431f542ab6321eeb12b7bcb9195318f25cf376a5"
EVIDENCE_PATH: Final = (
    "benchmarks/accelerator/evidence/"
    "2026-07-29-independent-ticket-transfer-throughput-rtx4060/"
)
WORKLOAD_ID: Final = "classic-crazy-full-domain-ticket-transfer-v1"
BACKEND_ID: Final = "cuda"
DEVICE_ARCH: Final = "sm_89"
DEVICE_NAME: Final = "NVIDIA GeForce RTX 4060"
FALLBACK_TICKET_NS: Final = 1_471_000
SAMPLE_COUNT: Final = 15
WORKLOAD_SHA256: Final = (
    "a523502c24560424c7139b527019e3f26ded512db205dec12a073e4801d7f7dc"
)
WORKLOAD_COUNT: Final = 59_049
WORKLOAD_KIND: Final = "crazy"


@dataclass(frozen=True, slots=True)
class _MeasuredRoute:
    candidate_ns: int
    group_size: int
    mode: TicketSubmissionMode
    paired_wins: int
    reference_ns: int


@dataclass(frozen=True, slots=True)
class CudaTicketAdmissionProfile:
    """One exact retained CUDA route-admission evidence context."""

    candidates: tuple[TicketRouteCandidate, ...]
    evidence_path: str
    fallback_ticket_ns: int
    profile_id: str
    source_commit: str
    workload_id: str

    def plan(
        self,
        capability: AcceleratorCapability,
        ticket_count: int,
    ) -> TicketAdmissionPlan:
        """Plan pending tickets for this exact retained capability.

        Returns:
            Conservative fewest-chunk plan with measured-cost tie breaking.

        """
        return plan_ticket_submissions(
            TicketAdmissionRequest(
                backend_id=capability.backend_id,
                device_arch=capability.device_arch,
                device_name=capability.device_name,
                ticket_count=ticket_count,
                workload_id=self.workload_id,
            ),
            candidates=self.candidates,
            fallback_ticket_ns=self.fallback_ticket_ns,
        )


def cuda_ticket_admission_profile_id() -> str:
    """Return the retained CUDA ticket admission profile identity.

    Returns:
        Versioned exact-device/workload profile identity.

    """
    return CUDA_TICKET_ADMISSION_PROFILE_ID


def cuda_ticket_admission_profile(
    capability: AcceleratorCapability,
) -> CudaTicketAdmissionProfile | None:
    """Resolve retained evidence only for its exact measured capability.

    Returns:
        Exact retained profile or ``None`` for any identity mismatch.

    """
    if not _matches_capability(capability):
        return None
    return CudaTicketAdmissionProfile(
        candidates=_retained_candidates(),
        evidence_path=EVIDENCE_PATH,
        fallback_ticket_ns=FALLBACK_TICKET_NS,
        profile_id=CUDA_TICKET_ADMISSION_PROFILE_ID,
        source_commit=EVIDENCE_SOURCE_COMMIT,
        workload_id=WORKLOAD_ID,
    )


def plan_retained_cuda_tickets(
    capability: AcceleratorCapability,
    ticket_count: int,
) -> TicketAdmissionPlan | None:
    """Plan exact retained CUDA tickets without cross-device extrapolation.

    Returns:
        Retained admission plan, or ``None`` when no exact profile exists.

    """
    profile = cuda_ticket_admission_profile(capability)
    return None if profile is None else profile.plan(capability, ticket_count)


def _matches_capability(capability: AcceleratorCapability) -> bool:
    return (
        capability.backend_id == BACKEND_ID
        and capability.device_arch == DEVICE_ARCH
        and capability.device_name == DEVICE_NAME
    )


def _retained_candidates() -> tuple[TicketRouteCandidate, ...]:
    return (
        _candidate(
            _MeasuredRoute(
                candidate_ns=1_879_400,
                group_size=1,
                mode=TicketSubmissionMode.STREAMED,
                paired_wins=0,
                reference_ns=FALLBACK_TICKET_NS,
            )
        ),
        _candidate(
            _MeasuredRoute(
                candidate_ns=1_386_300,
                group_size=2,
                mode=TicketSubmissionMode.SYNCHRONOUS,
                paired_wins=15,
                reference_ns=1_788_500,
            )
        ),
        _candidate(
            _MeasuredRoute(
                candidate_ns=3_179_100,
                group_size=2,
                mode=TicketSubmissionMode.STREAMED,
                paired_wins=0,
                reference_ns=1_386_300,
            )
        ),
        _candidate(
            _MeasuredRoute(
                candidate_ns=3_061_100,
                group_size=4,
                mode=TicketSubmissionMode.SYNCHRONOUS,
                paired_wins=15,
                reference_ns=3_824_300,
            )
        ),
        _candidate(
            _MeasuredRoute(
                candidate_ns=6_403_800,
                group_size=4,
                mode=TicketSubmissionMode.STREAMED,
                paired_wins=0,
                reference_ns=3_061_100,
            )
        ),
        _candidate(
            _MeasuredRoute(
                candidate_ns=5_940_800,
                group_size=8,
                mode=TicketSubmissionMode.SYNCHRONOUS,
                paired_wins=15,
                reference_ns=7_456_400,
            )
        ),
        _candidate(
            _MeasuredRoute(
                candidate_ns=12_013_800,
                group_size=8,
                mode=TicketSubmissionMode.STREAMED,
                paired_wins=0,
                reference_ns=5_940_800,
            )
        ),
    )


def _candidate(measurement: _MeasuredRoute) -> TicketRouteCandidate:
    return TicketRouteCandidate(
        backend_id=BACKEND_ID,
        benchmark_id=EVIDENCE_BENCHMARK_ID,
        candidate_median_ns=measurement.candidate_ns,
        device_arch=DEVICE_ARCH,
        device_name=DEVICE_NAME,
        exact_results=True,
        group_size=measurement.group_size,
        mode=measurement.mode,
        paired_wins=measurement.paired_wins,
        reference_median_ns=measurement.reference_ns,
        sample_count=SAMPLE_COUNT,
        workload_id=WORKLOAD_ID,
    )


def execute_retained_cuda_tickets(
    adapter: CudaExactPrimitiveAdapter,
    prepared: PreparedPrimitiveBatch,
    ticket_count: int,
) -> tuple[TicketAdmissionPlan, tuple[PackedPrimitiveResult, ...]] | None:
    """Execute one exact retained ticket plan through admitted lifetimes.

    Returns:
        Plan and input-order results, or ``None`` without an exact profile.

    """
    profile = cuda_ticket_admission_profile(adapter.capability())
    if profile is None:
        return None
    _validate_prepared_workload(prepared)
    plan = profile.plan(adapter.capability(), ticket_count)
    results: list[PackedPrimitiveResult] = []
    for chunk in plan.chunks:
        submit = (
            adapter.submit_prepared
            if chunk.mode is TicketSubmissionMode.SYNCHRONOUS
            else adapter.ticket_transfers.submit
        )
        results.extend(_execute_chunk(submit, prepared, chunk.ticket_count))
    return plan, tuple(results)


def _execute_chunk(
    submit: Callable[[PreparedPrimitiveBatch], CudaPrimitiveEvaluationTicket],
    prepared: PreparedPrimitiveBatch,
    ticket_count: int,
) -> tuple[PackedPrimitiveResult, ...]:
    tickets: list[CudaPrimitiveEvaluationTicket] = []
    try:
        tickets.extend(submit(prepared) for _ in range(ticket_count))
        reversed_results = tuple(ticket.wait() for ticket in reversed(tickets))
        return tuple(reversed(reversed_results))
    finally:
        for ticket in reversed(tickets):
            ticket.close()


def _validate_prepared_workload(prepared: PreparedPrimitiveBatch) -> None:
    storage = prepared.validated_storage()
    if storage.count() != WORKLOAD_COUNT or storage.kind.value != WORKLOAD_KIND:
        message = "CUDA ticket admission prepared workload identity mismatched"
        raise TicketAdmissionError(message)
    digest = sha256()
    digest.update(storage.kind.value.encode("ascii"))
    digest.update(b"\0")
    digest.update(storage.accumulators_u32le)
    digest.update(storage.data_u32le)
    if digest.hexdigest() != WORKLOAD_SHA256:
        message = "CUDA ticket admission prepared workload SHA-256 mismatched"
        raise TicketAdmissionError(message)
