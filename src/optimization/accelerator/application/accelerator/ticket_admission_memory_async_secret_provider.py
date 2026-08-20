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
#   - Explicit inline async adapter for one bounded memory secret provider.
# - Must-Not:
#   - Create event loops, tasks, scheduling points, read environment, files,
#     network, external secret stores, discover, refresh, retry, persist, or
#     change policy.
# - Allows:
#   - Inputs: one exact bounded memory provider and exact async-port requests.
#   - Outputs: the same stable typed result as the synchronous memory service.
#   - Side effects: none; awaiting completes inline without internal suspension.
# - Split-When:
#   - Split when external credential providers, hosted APIs, certificates, or
#     PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact memory-secret async adaptation.
# - Summary:
#   - Inline async adapter for caller-owned HMAC lineage secrets.
# - Description:
#   - Preserves memory-provider validation without hidden async scheduling.
# - Usage:
#   - Build explicitly and pass to the sequential async secret-provider port.
# - Defaults:
#   - Retains the wrapped service's entry limit and provider identity.
#

"""Inline async adapter for bounded in-memory lineage secret values."""

# ruff: file-ignore[hardcoded-password-string]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Final
from typing import Never
from typing import TYPE_CHECKING

from accelerator import (
    ticket_admission_telemetry_lineage_memory_secret_provider as memory,
)

if TYPE_CHECKING:
    from accelerator import (
        ticket_admission_telemetry_lineage_secret_provider as port,
    )

_MEMORY_ASYNC_SECRET_PROVIDER_ID_PREFIX: Final = (
    "bounded-in-memory-async-ticket-admission-telemetry-lineage-"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_ASYNC_SECRET_PROVIDER_ID: Final = (
    f"{_MEMORY_ASYNC_SECRET_PROVIDER_ID_PREFIX}secret-provider-v1"
)
_validate_memory_provider: Final = (
    memory.validate_ticket_admission_telemetry_lineage_memory_secret_provider
)


class TicketAdmissionTelemetryLineageMemoryAsyncSecretProviderError(ValueError):
    """An inline memory lineage secret adapter is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageMemoryAsyncSecretProvider:
    """Immutable inline adapter with hidden caller-owned secret service."""

    adapter_id: str
    max_entries: int
    provider: memory.TicketAdmissionTelemetryLineageMemorySecretProvider = (
        field(repr=False)
    )
    provider_id: str
    secret_count: int

    async def __call__(
        self,
        request: port.TicketAdmissionTelemetryLineageSecretRequest,
    ) -> port.TicketAdmissionTelemetryLineageSecretResult:
        """Resolve one request inline without creating a scheduling point.

        Returns:
            Stable resolved, unavailable, or failed provider result.

        """
        adapter = _validated_adapter(self)
        return adapter.provider(request)


def ticket_admission_memory_async_secret_provider_id() -> str:
    """Return the stable memory async secret-provider identity.

    Returns:
        Versioned adapter implementation identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_ASYNC_SECRET_PROVIDER_ID


def build_ticket_admission_memory_async_secret_provider(
    value: memory.TicketAdmissionTelemetryLineageMemorySecretProvider,
) -> TicketAdmissionTelemetryLineageMemoryAsyncSecretProvider:
    """Build one explicit inline async adapter over exact memory state.

    Returns:
        Validated immutable adapter with hidden secret values.

    """
    validated = _validated_memory_provider(value)
    return TicketAdmissionTelemetryLineageMemoryAsyncSecretProvider(
        adapter_id=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_ASYNC_SECRET_PROVIDER_ID
        ),
        max_entries=validated.max_entries,
        provider=validated,
        provider_id=validated.provider_id,
        secret_count=validated.secret_count,
    )


def validate_ticket_admission_memory_async_secret_provider(
    adapter: TicketAdmissionTelemetryLineageMemoryAsyncSecretProvider,
) -> TicketAdmissionTelemetryLineageMemoryAsyncSecretProvider:
    """Validate one exact immutable memory-to-async secret adapter.

    Returns:
        The exact validated adapter.

    """
    return _validated_adapter(adapter)


def _validated_adapter(
    adapter: TicketAdmissionTelemetryLineageMemoryAsyncSecretProvider,
) -> TicketAdmissionTelemetryLineageMemoryAsyncSecretProvider:
    _validate_adapter_shape(adapter)
    validated = _validated_memory_provider(adapter.provider)
    _validate_adapter_binding(adapter, validated)
    return adapter


def _validate_adapter_shape(
    adapter: TicketAdmissionTelemetryLineageMemoryAsyncSecretProvider,
) -> None:
    if (
        type(adapter)
        is not TicketAdmissionTelemetryLineageMemoryAsyncSecretProvider
    ):
        _raise_adapter("adapter must use the exact memory-async secret type")
    if (
        adapter.adapter_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_ASYNC_SECRET_PROVIDER_ID
    ):
        _raise_adapter("adapter identity is unsupported")
    if type(adapter.max_entries) is not int or adapter.max_entries <= 0:
        _raise_adapter("adapter entry limit must be a positive integer")
    if type(adapter.secret_count) is not int or adapter.secret_count < 0:
        _raise_adapter("adapter secret count must be a nonnegative integer")


def _validate_adapter_binding(
    adapter: TicketAdmissionTelemetryLineageMemoryAsyncSecretProvider,
    validated: memory.TicketAdmissionTelemetryLineageMemorySecretProvider,
) -> None:
    if adapter.max_entries != validated.max_entries:
        _raise_adapter("adapter entry limit does not match provider")
    if adapter.provider_id != validated.provider_id:
        _raise_adapter("adapter provider identity does not match provider")
    if adapter.secret_count != validated.secret_count:
        _raise_adapter("adapter secret count does not match provider")


def _validated_memory_provider(
    value: memory.TicketAdmissionTelemetryLineageMemorySecretProvider,
) -> memory.TicketAdmissionTelemetryLineageMemorySecretProvider:
    try:
        return _validate_memory_provider(value)
    except (
        memory.TicketAdmissionTelemetryLineageMemorySecretProviderError
    ) as error:
        message = "invalid memory lineage secret provider"
        raise TicketAdmissionTelemetryLineageMemoryAsyncSecretProviderError(
            message
        ) from error


def _raise_adapter(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage memory async secret provider "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageMemoryAsyncSecretProviderError(message)
