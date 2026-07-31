# File:
#   - ticket_admission_telemetry_lineage_memory_async_public_key_provider.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_memory_async_public_key_provider.py
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
#   - Explicit sequential async adapter for one bounded memory key provider.
# - Must-Not:
#   - Create event loops, tasks, scheduling points, discover, retry, fetch,
#     mutate, persist, validate certificates, select algorithms, or change policy.
# - Allows:
#   - Inputs: one exact bounded memory provider and exact async-port requests.
#   - Outputs: the same stable typed result as the synchronous memory service.
#   - Side effects: none; awaiting completes inline without internal suspension.
# - Split-When:
#   - Split when batch/session memory adapters, external services, certificates,
#     or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact memory-to-async adaptation.
# - Summary:
#   - Inline async adapter for caller-owned detached-lineage public keys.
# - Description:
#   - Preserves memory-provider validation without hidden async scheduling.
# - Usage:
#   - Build explicitly and pass to the sequential async provider boundary.
# - Defaults:
#   - Retains the wrapped service's bounded key count and provider identity.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Inline async adapter for the bounded in-memory public-key provider."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Final
from typing import Never
from typing import TYPE_CHECKING

from accelerator import (
    ticket_admission_telemetry_lineage_memory_public_key_provider as memory,
)
from accelerator.ticket_admission_telemetry_lineage_memory_public_key_provider import (
    validate_ticket_admission_telemetry_lineage_memory_public_key_provider,
)

if TYPE_CHECKING:
    from accelerator import (
        ticket_admission_telemetry_lineage_public_key_provider as provider,
    )

_ADAPTER_ID_PREFIX: Final = "bounded-in-memory-async-ticket-admission-"
_ADAPTER_ID_SUFFIX: Final = "telemetry-lineage-public-key-provider-v1"
_validate_memory_provider: Final = (
    validate_ticket_admission_telemetry_lineage_memory_public_key_provider
)

TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_ASYNC_PUBLIC_KEY_PROVIDER_ID: Final = (
    "bounded-in-memory-async-ticket-admission-"
    "telemetry-lineage-public-key-provider-v1"
)


class TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProviderError(
    ValueError
):
    """An in-memory async adapter is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProvider:
    """Immutable inline adapter with hidden caller-owned key service."""

    adapter_id: str
    key_count: int
    provider: memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider = (
        field(repr=False)
    )
    provider_id: str

    async def __call__(
        self,
        request: provider.TicketAdmissionTelemetryLineagePublicKeyRequest,
    ) -> provider.TicketAdmissionTelemetryLineagePublicKeyResult:
        """Resolve one request inline without creating a scheduling point.

        Returns:
            Stable resolved, unavailable, or failed provider result.

        """
        adapter = _validated_adapter(self)
        return adapter.provider(request)


def ticket_admission_telemetry_lineage_memory_async_public_key_provider_id() -> (
    str
):
    """Return the stable in-memory async adapter identity.

    Returns:
        Versioned adapter implementation identity.

    """
    return (
        TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_ASYNC_PUBLIC_KEY_PROVIDER_ID
    )


def build_ticket_admission_memory_async_public_key_provider(
    value: memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider,
) -> TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProvider:
    """Build one explicit inline async adapter over exact memory state.

    Returns:
        Validated immutable adapter with hidden key material.

    """
    validated = _validated_memory_provider(value)
    return TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProvider(
        adapter_id=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_ASYNC_PUBLIC_KEY_PROVIDER_ID
        ),
        key_count=validated.key_count,
        provider=validated,
        provider_id=validated.provider_id,
    )


def validate_ticket_admission_memory_async_public_key_provider(
    adapter: TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProvider,
) -> TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProvider:
    """Validate one exact immutable memory-to-async adapter.

    Returns:
        The exact validated adapter.

    """
    return _validated_adapter(adapter)


def _validated_adapter(
    adapter: TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProvider,
) -> TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProvider:
    _validate_adapter_shape(adapter)
    validated = _validated_memory_provider(adapter.provider)
    _validate_adapter_binding(adapter, validated)
    return adapter


def _validate_adapter_shape(
    adapter: TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProvider,
) -> None:
    if (
        type(adapter)
        is not TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProvider
    ):
        _raise_adapter("adapter must use the exact memory-async type")
    if (
        adapter.adapter_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_ASYNC_PUBLIC_KEY_PROVIDER_ID
    ):
        _raise_adapter("adapter identity is unsupported")
    if type(adapter.key_count) is not int or adapter.key_count < 0:
        _raise_adapter("adapter key count must be a nonnegative integer")


def _validate_adapter_binding(
    adapter: TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProvider,
    validated: memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider,
) -> None:
    if adapter.key_count != validated.key_count:
        _raise_adapter("adapter key count does not match provider")
    if adapter.provider_id != validated.provider_id:
        _raise_adapter("adapter provider identity does not match provider")


def _validated_memory_provider(
    value: memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider,
) -> memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider:
    try:
        return _validate_memory_provider(value)
    except (
        memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProviderError
    ) as error:
        message = f"invalid memory provider: {error}"
        raise TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProviderError(
            message
        ) from error


def _raise_adapter(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage memory async public-key provider "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageMemoryAsyncPublicKeyProviderError(
        message
    )
