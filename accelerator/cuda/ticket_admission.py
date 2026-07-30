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
#   - Retained CUDA profile resolution, reporting, and opt-in execution.
# - Must-Not:
#   - Read benchmark evidence at runtime or generalize profile identities.
# - Allows:
#   - Inputs: exact CUDA capability, prepared workload, and ticket count.
#   - Outputs: optional plans, reports, and input-order exact results.
#   - Side effects: scoped CUDA ticket submission, wait, and cleanup only.
# - Split-When:
#   - Split when automatic dispatch gains an independent policy lifecycle.
# - Merge-When:
#   - Merge when another module owns this exact resolution/execution contract.
# - Summary:
#   - Resolve, explain, and execute retained CUDA ticket profiles.
# - Description:
#   - Uses a product manifest without embedding retained measurements in code.
# - Usage:
#   - Opt-in planning for exact profiles; ordinary defaults remain unchanged.
# - Defaults:
#   - Missing capability/profile identity returns no automatic plan.
#
# Related documents:
# - accelerator/cuda/ticket_admission_profiles.json
# - benchmarks/accelerator/ticket_admission_profile_manifest.py
#
# Large file:
#   - false
#

"""Resolve and execute exact product-owned CUDA ticket-admission profiles."""

from __future__ import annotations

from hashlib import sha256
from typing import Final
from typing import TYPE_CHECKING

from accelerator.cuda.ticket_admission_profile import (
    load_cuda_ticket_admission_profiles,
)
from accelerator.cuda.ticket_admission_profile import (
    resolve_cuda_ticket_admission_profile,
)
from accelerator.ticket_admission import TicketAdmissionError
from accelerator.ticket_admission import TicketSubmissionMode

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.cuda.exact_primitives import CudaExactPrimitiveAdapter
    from accelerator.cuda.exact_primitives import CudaPrimitiveEvaluationTicket
    from accelerator.cuda.runtime import CudaRuntimeIdentity
    from accelerator.cuda.ticket_admission_profile import (
        CudaTicketAdmissionProfile,
    )
    from accelerator.exact_primitives import AcceleratorCapability
    from accelerator.exact_primitives import PackedPrimitiveResult
    from accelerator.exact_primitives import PreparedPrimitiveBatch
    from accelerator.ticket_admission import TicketAdmissionPlan
    from accelerator.ticket_admission import TicketAdmissionReport

CUDA_TICKET_ADMISSION_PROFILE_ID: Final = (
    "rtx4060-full-domain-crazy-ticket-admission-2026-07-29-v1"
)
CUDA_TICKET_ADMISSION_WORKLOAD_ID: Final = (
    "classic-crazy-full-domain-ticket-transfer-v1"
)


def cuda_ticket_admission_profile_id() -> str:
    """Return the retained CUDA ticket admission profile identity.

    Returns:
        Versioned exact-device/workload profile identity.

    """
    return CUDA_TICKET_ADMISSION_PROFILE_ID


def cuda_ticket_admission_workload_id() -> str:
    """Return the retained workload identity used by compatibility wrappers.

    Returns:
        Versioned exact workload identity.

    """
    return CUDA_TICKET_ADMISSION_WORKLOAD_ID


def cuda_ticket_admission_profile(
    capability: AcceleratorCapability,
    runtime_identity: CudaRuntimeIdentity,
) -> CudaTicketAdmissionProfile | None:
    """Resolve retained evidence only for exact capability/runtime identity.

    Returns:
        Exact retained profile or ``None`` for any identity mismatch.

    """
    return resolve_cuda_ticket_admission_profile(
        load_cuda_ticket_admission_profiles(),
        capability=capability,
        runtime_identity=runtime_identity,
        workload_id=CUDA_TICKET_ADMISSION_WORKLOAD_ID,
    )


def plan_retained_cuda_tickets(
    capability: AcceleratorCapability,
    runtime_identity: CudaRuntimeIdentity,
    ticket_count: int,
) -> TicketAdmissionPlan | None:
    """Plan retained CUDA tickets without device/toolchain extrapolation.

    Returns:
        Retained admission plan, or ``None`` when no exact profile exists.

    """
    profile = cuda_ticket_admission_profile(capability, runtime_identity)
    return (
        None
        if profile is None
        else profile.plan(capability, runtime_identity, ticket_count)
    )


def plan_retained_cuda_tickets_with_report(
    capability: AcceleratorCapability,
    runtime_identity: CudaRuntimeIdentity,
    ticket_count: int,
) -> TicketAdmissionReport | None:
    """Plan retained CUDA tickets with opt-in route instrumentation.

    Returns:
        Exact immutable report, or ``None`` when no exact profile exists.

    """
    profile = cuda_ticket_admission_profile(capability, runtime_identity)
    return (
        None
        if profile is None
        else profile.plan_with_report(
            capability,
            runtime_identity,
            ticket_count,
        )
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
    capability = adapter.capability()
    runtime_identity = adapter.runtime_identity
    profile = cuda_ticket_admission_profile(capability, runtime_identity)
    if profile is None:
        return None
    _validate_prepared_workload(prepared, profile)
    plan = profile.plan(capability, runtime_identity, ticket_count)
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


def _validate_prepared_workload(
    prepared: PreparedPrimitiveBatch,
    profile: CudaTicketAdmissionProfile,
) -> None:
    storage = prepared.validated_storage()
    if (
        storage.count() != profile.workload_count
        or storage.kind.value != profile.workload_kind
    ):
        message = "CUDA ticket admission prepared workload identity mismatched"
        raise TicketAdmissionError(message)
    digest = sha256()
    digest.update(storage.kind.value.encode("ascii"))
    digest.update(b"\0")
    digest.update(storage.accumulators_u32le)
    digest.update(storage.data_u32le)
    if digest.hexdigest() != profile.workload_sha256:
        message = "CUDA ticket admission prepared workload SHA-256 mismatched"
        raise TicketAdmissionError(message)
