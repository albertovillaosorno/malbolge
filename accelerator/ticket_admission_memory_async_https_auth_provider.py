# File:
#   - ticket_admission_memory_async_https_auth_provider.py
# Path:
#   - accelerator/ticket_admission_memory_async_https_auth_provider.py
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
#   - Explicit inline async adapter for one bounded memory Authorization provider.
# - Must-Not:
#   - Create event loops, tasks, scheduling points, read environment, files,
#     network, secret stores, discover, refresh, retry, persist, or change policy.
# - Allows:
#   - Inputs: one exact bounded memory provider and exact async-port requests.
#   - Outputs: the same stable typed result as the synchronous memory service.
#   - Side effects: none; awaiting completes inline without internal suspension.
# - Split-When:
#   - Split when external credential providers, hosted APIs, certificates, or PKI
#     gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact memory-auth async adaptation.
# - Summary:
#   - Inline async adapter for caller-owned HTTPS Authorization values.
# - Description:
#   - Preserves memory-provider validation without hidden async scheduling.
# - Usage:
#   - Build explicitly and pass to the one-await async Authorization port.
# - Defaults:
#   - Retains the wrapped service's entry limit and provider identity.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_environment_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Inline async adapter for bounded in-memory HTTPS Authorization values."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Final
from typing import Never
from typing import TYPE_CHECKING

from accelerator import (
    ticket_admission_telemetry_lineage_memory_https_auth_provider as memory,
)

if TYPE_CHECKING:
    from accelerator import (
        ticket_admission_telemetry_lineage_https_auth_provider as auth,
    )

TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_ASYNC_HTTPS_AUTH_PROVIDER_ID: Final = (
    "memory-async-ticket-admission-lineage-"
    "https-authorization-provider-v1"
)
_validate_memory_provider: Final = (
    memory.validate_ticket_admission_memory_https_authorization_provider
)


class TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProviderError(
    ValueError
):
    """An inline memory HTTPS Authorization adapter is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProvider:
    """Immutable inline adapter with hidden caller-owned auth service."""

    adapter_id: str
    entry_count: int
    max_entries: int
    provider: memory.TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider = (
        field(repr=False)
    )
    provider_id: str

    async def __call__(
        self,
        request: auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest,
    ) -> auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult:
        """Resolve one request inline without creating a scheduling point.

        Returns:
            Stable resolved, unavailable, or failed provider result.

        """
        adapter = _validated_adapter(self)
        return adapter.provider(request)


def ticket_admission_memory_async_https_authorization_provider_id() -> str:
    """Return the stable memory async Authorization adapter identity.

    Returns:
        Versioned adapter implementation identity.

    """
    return (
        TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_ASYNC_HTTPS_AUTH_PROVIDER_ID
    )


def build_ticket_admission_memory_async_https_authorization_provider(
    value: memory.TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider,
) -> TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProvider:
    """Build one explicit inline async adapter over exact memory state.

    Returns:
        Validated immutable adapter with hidden Authorization values.

    """
    validated = _validated_memory_provider(value)
    return TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProvider(
        adapter_id=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_ASYNC_HTTPS_AUTH_PROVIDER_ID
        ),
        entry_count=len(validated.entries),
        max_entries=validated.max_entries,
        provider=validated,
        provider_id=validated.provider_id,
    )


def validate_ticket_admission_memory_async_https_authorization_provider(
    adapter: TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProvider,
) -> TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProvider:
    """Validate one exact immutable memory-to-async auth adapter.

    Returns:
        The exact validated adapter.

    """
    return _validated_adapter(adapter)


def _validated_adapter(
    adapter: TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProvider,
) -> TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProvider:
    _validate_adapter_shape(adapter)
    validated = _validated_memory_provider(adapter.provider)
    _validate_adapter_binding(adapter, validated)
    return adapter


def _validate_adapter_shape(
    adapter: TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProvider,
) -> None:
    if (
        type(adapter)
        is not TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProvider
    ):
        _raise_adapter("adapter must use the exact memory-async auth type")
    if (
        adapter.adapter_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_ASYNC_HTTPS_AUTH_PROVIDER_ID
    ):
        _raise_adapter("adapter identity is unsupported")
    if type(adapter.entry_count) is not int or adapter.entry_count < 0:
        _raise_adapter("adapter entry count must be a nonnegative integer")
    if type(adapter.max_entries) is not int or adapter.max_entries <= 0:
        _raise_adapter("adapter entry limit must be a positive integer")


def _validate_adapter_binding(
    adapter: TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProvider,
    validated: memory.TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider,
) -> None:
    if adapter.entry_count != len(validated.entries):
        _raise_adapter("adapter entry count does not match provider")
    if adapter.max_entries != validated.max_entries:
        _raise_adapter("adapter entry limit does not match provider")
    if adapter.provider_id != validated.provider_id:
        _raise_adapter("adapter provider identity does not match provider")


def _validated_memory_provider(
    value: memory.TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider,
) -> memory.TicketAdmissionTelemetryLineageMemoryHttpsAuthProvider:
    try:
        return _validate_memory_provider(value)
    except (
        memory.TicketAdmissionTelemetryLineageMemoryHttpsAuthProviderError
    ) as error:
        message = "invalid memory Authorization provider"
        raise TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProviderError(
            message
        ) from error


def _raise_adapter(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage memory async HTTPS Authorization "
        f"provider {detail}"
    )
    raise TicketAdmissionTelemetryLineageMemoryAsyncHttpsAuthProviderError(
        message
    )
