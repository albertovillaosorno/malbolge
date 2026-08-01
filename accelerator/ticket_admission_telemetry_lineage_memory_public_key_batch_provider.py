# File:
#   - ticket_admission_telemetry_lineage_memory_public_key_batch_provider.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_memory_public_key_batch_provider.py
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
#   - Explicit inline async batch adapter for one bounded memory key provider.
# - Must-Not:
#   - Create event loops, tasks, concurrency, scheduling points, discover,
#     retry, fetch, mutate, persist, validate certificates, or change policy.
# - Allows:
#   - Inputs: one exact bounded memory provider and one exact batch request.
#   - Outputs: one positional batch result from synchronous memory lookups.
#   - Side effects: none; awaiting completes inline without internal suspension.
# - Split-When:
#   - Split when concrete network transports, certificates, or
#     PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact memory-to-batch adaptation.
# - Summary:
#   - Inline async batch adapter for caller-owned detached-lineage public keys.
# - Description:
#   - Preserves exact memory validation and positional batch result semantics.
# - Usage:
#   - Build explicitly and pass to the caller-controlled async batch boundary.
# - Defaults:
#   - At most 256 requests and the wrapped service's bounded key count.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_session.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider_session.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Inline async batch adapter for the bounded memory key provider."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Final
from typing import Never

from accelerator import (
    ticket_admission_telemetry_lineage_memory_public_key_provider as memory,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_batch_provider as batch,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_provider as provider,
)
from accelerator.ticket_admission_telemetry_lineage_memory_public_key_provider import (
    validate_ticket_admission_telemetry_lineage_memory_public_key_provider,
)

TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_BATCH_PROVIDER_ID: Final = (
    "bounded-memory-async-batch-ticket-admission-"
    "telemetry-lineage-public-key-provider-v1"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_BATCH_REQUESTS: Final = (
    batch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BATCH_PROVIDER_REQUESTS
)
_validate_memory_provider: Final = (
    validate_ticket_admission_telemetry_lineage_memory_public_key_provider
)


class TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProviderError(
    ValueError
):
    """An in-memory batch adapter or request is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProvider:
    """Immutable inline batch adapter with hidden caller-owned key service."""

    adapter_id: str
    key_count: int
    max_requests: int
    provider: memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider = (
        field(repr=False)
    )
    provider_id: str

    async def __call__(
        self,
        request: batch.TicketAdmissionTelemetryLineagePublicKeyBatchRequest,
    ) -> batch.TicketAdmissionTelemetryLineagePublicKeyBatchResult:
        """Resolve one exact batch inline without creating a scheduling point.

        Returns:
            Exact positional result tuple with hidden public-key bytes.

        """
        adapter = _validated_adapter(self)
        validated_request = _validated_batch_request(
            request,
            provider_id=adapter.provider_id,
            max_requests=adapter.max_requests,
        )
        results = tuple(
            adapter.provider(item) for item in validated_request.requests
        )
        return batch.TicketAdmissionTelemetryLineagePublicKeyBatchResult(
            results=results
        )


def ticket_admission_memory_public_key_batch_provider_id() -> str:
    """Return the stable in-memory async batch-adapter identity.

    Returns:
        Versioned adapter implementation identity.

    """
    return (
        TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_BATCH_PROVIDER_ID
    )


def build_ticket_admission_memory_public_key_batch_provider(
    value: memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider,
    *,
    max_requests: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_BATCH_REQUESTS
    ),
) -> TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProvider:
    """Build one explicit inline batch adapter over exact memory state.

    Returns:
        Validated immutable batch adapter with hidden key material.

    """
    validated = _validated_memory_provider(value)
    request_limit = _validated_positive_limit(max_requests, "request limit")
    return TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProvider(
        adapter_id=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_BATCH_PROVIDER_ID
        ),
        key_count=validated.key_count,
        max_requests=request_limit,
        provider=validated,
        provider_id=validated.provider_id,
    )


def validate_ticket_admission_memory_public_key_batch_provider(
    adapter: TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProvider,
) -> TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProvider:
    """Validate one exact immutable memory-to-batch adapter.

    Returns:
        The exact validated adapter.

    """
    return _validated_adapter(adapter)


def _validated_adapter(
    adapter: TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProvider,
) -> TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProvider:
    _validate_adapter_shape(adapter)
    validated = _validated_memory_provider(adapter.provider)
    _validate_adapter_binding(adapter, validated)
    return adapter


def _validate_adapter_shape(
    adapter: TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProvider,
) -> None:
    if (
        type(adapter)
        is not TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProvider
    ):
        _raise_adapter("adapter must use the exact memory-batch type")
    if (
        adapter.adapter_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_BATCH_PROVIDER_ID
    ):
        _raise_adapter("adapter identity is unsupported")
    if type(adapter.key_count) is not int or adapter.key_count < 0:
        _raise_adapter("adapter key count must be a nonnegative integer")
    _ = _validated_positive_limit(adapter.max_requests, "adapter request limit")


def _validate_adapter_binding(
    adapter: TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProvider,
    validated: memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider,
) -> None:
    if adapter.key_count != validated.key_count:
        _raise_adapter("adapter key count does not match provider")
    if adapter.provider_id != validated.provider_id:
        _raise_adapter("adapter provider identity does not match provider")


def _validated_batch_request(
    request: batch.TicketAdmissionTelemetryLineagePublicKeyBatchRequest,
    *,
    provider_id: str,
    max_requests: int,
) -> batch.TicketAdmissionTelemetryLineagePublicKeyBatchRequest:
    _validate_batch_request_shape(request)
    if request.provider_id != provider_id:
        _raise_adapter("batch provider identity does not match adapter")
    if len(request.requests) > max_requests:
        _raise_adapter("batch request count exceeds configured limit")
    _validate_request_bindings(request)
    return request


def _validate_batch_request_shape(
    request: batch.TicketAdmissionTelemetryLineagePublicKeyBatchRequest,
) -> None:
    if (
        type(request)
        is not batch.TicketAdmissionTelemetryLineagePublicKeyBatchRequest
    ):
        _raise_adapter("request must use the exact batch request type")
    if (
        type(request.manifest_fingerprint) is not str
        or not request.manifest_fingerprint
    ):
        _raise_adapter("batch manifest fingerprint must be a nonempty string")
    if type(request.provider_id) is not str or not request.provider_id:
        _raise_adapter("batch provider identity must be a nonempty string")
    if type(request.requests) is not tuple:
        _raise_adapter("batch requests must use the exact immutable tuple type")


def _validate_request_bindings(
    request: batch.TicketAdmissionTelemetryLineagePublicKeyBatchRequest,
) -> None:
    for index, item in enumerate(request.requests):
        _validate_request_binding(request, item, index=index)


def _validate_request_binding(
    request: batch.TicketAdmissionTelemetryLineagePublicKeyBatchRequest,
    item: provider.TicketAdmissionTelemetryLineagePublicKeyRequest,
    *,
    index: int,
) -> None:
    if (
        type(item)
        is not provider.TicketAdmissionTelemetryLineagePublicKeyRequest
    ):
        _raise_adapter(
            f"batch item at index {index} must use exact request type"
        )
    if item.request_index != index:
        _raise_adapter(f"batch item index does not match position {index}")
    if item.provider_id != request.provider_id:
        _raise_adapter(f"batch item provider does not match at index {index}")
    if item.manifest_fingerprint != request.manifest_fingerprint:
        _raise_adapter(f"batch item manifest does not match at index {index}")


def _validated_memory_provider(
    value: memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider,
) -> memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider:
    try:
        return _validate_memory_provider(value)
    except (
        memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProviderError
    ) as error:
        message = f"invalid memory provider: {error}"
        raise TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProviderError(
            message
        ) from error


def _validated_positive_limit(value: int, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        _raise_adapter(f"{field_name} must be a positive integer")
    return value


def _raise_adapter(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage memory public-key batch provider "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageMemoryPublicKeyBatchProviderError(
        message
    )
