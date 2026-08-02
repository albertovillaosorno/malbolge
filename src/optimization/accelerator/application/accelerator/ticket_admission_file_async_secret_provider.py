# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Caller-offloaded async adaptation of one exact file secret provider.
# - Must-Not:
#   - Create event loops, tasks, threads, executors, discover paths, read files
#     directly, retry, cache, persist, log paths or secrets, or change policy.
# - Allows:
#   - Inputs: one exact file provider, one caller offloader, and exact requests.
#   - Outputs: the shared typed resolved, unavailable, or failed result.
#   - Side effects: exactly one caller-supplied offloader await per matched
#     call.
# - Split-When:
#   - Split when native async file I/O, external stores, hosted APIs,
#     certificates, or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact caller-offloaded file boundary.
# - Summary:
#   - Caller-offloaded async adapter for explicit raw-secret files.
# - Description:
#   - Reuses exact file-provider validation without owning scheduling.
# - Usage:
#   - Build with one file provider and a caller-selected async offloader.
# - Defaults:
#   - No default offloader; caller owns all blocking-file-work placement.
#

"""Caller-offloaded async adapter for explicit lineage secret files."""

from __future__ import annotations

from asyncio import CancelledError
from dataclasses import dataclass
from dataclasses import field
from typing import Final
from typing import Never
from typing import Protocol
from typing import TYPE_CHECKING

from accelerator import (
    ticket_admission_telemetry_lineage_file_secret_provider as file_provider,
)
from accelerator import (
    ticket_admission_telemetry_lineage_secret_provider as port,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MIN_TELEMETRY_LINEAGE_KEY_BYTES,
)

if TYPE_CHECKING:
    from accelerator import (
        ticket_admission_telemetry_lineage_file_secret_provider as file_types,
    )

    type FileSecretProvider = (
        file_types.TicketAdmissionTelemetryLineageFileSecretProvider
    )


_ADAPTER_ID_PREFIX: Final = (
    "offloaded-async-file-ticket-admission-telemetry-lineage-"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_FILE_ASYNC_SECRET_PROVIDER_ID: Final = (
    f"{_ADAPTER_ID_PREFIX}secret-provider-v1"
)
_validate_file_provider: Final = (  # fmt: skip
    # jig-ignore-next-line: indivisible reviewed identifier
    file_provider.validate_ticket_admission_telemetry_lineage_file_secret_provider
)
_validate_request: Final = (
    port.validate_ticket_admission_telemetry_lineage_secret_request
)
_validate_result: Final = (
    port.validate_ticket_admission_telemetry_lineage_secret_result
)
_FAILED: Final = port.TicketAdmissionTelemetryLineageSecretResultKind.FAILED
_RESOLVED: Final = port.TicketAdmissionTelemetryLineageSecretResultKind.RESOLVED


class TicketAdmissionTelemetryLineageFileAsyncSecretProviderError(ValueError):
    """A caller-offloaded async file-secret adapter is invalid."""


class TicketAdmissionTelemetryLineageFileSecretOffloader(Protocol):
    """Caller-owned placement of one synchronous file-provider invocation."""

    async def __call__(
        self,
        provider: FileSecretProvider,
        request: port.TicketAdmissionTelemetryLineageSecretRequest,
    ) -> port.TicketAdmissionTelemetryLineageSecretResult:
        """Run one exact synchronous provider call under caller scheduling."""
        ...


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageFileAsyncSecretProvider:
    """Immutable async adapter with hidden file provider and offloader."""

    adapter_id: str
    max_entries: int
    max_secret_bytes: int
    offloader: TicketAdmissionTelemetryLineageFileSecretOffloader = field(
        repr=False
    )
    provider: FileSecretProvider = field(repr=False)
    provider_id: str
    secret_count: int

    async def __call__(
        self,
        request: port.TicketAdmissionTelemetryLineageSecretRequest,
    ) -> port.TicketAdmissionTelemetryLineageSecretResult:
        """Await one caller-owned offload without hidden scheduling resources.

        Returns:
            Shared typed resolved, unavailable, or failed result.

        Cancellation propagates directly to the caller.

        """
        adapter = _validated_adapter(self)
        validated_request = _validated_shared_request(request)
        if validated_request.provider_id != adapter.provider_id:
            return _failed_result()
        result = await _await_offloader(adapter, validated_request)
        return _validated_shared_result(
            result,
            max_secret_bytes=adapter.max_secret_bytes,
        )


def ticket_admission_file_async_secret_provider_id() -> str:
    """Return the stable caller-offloaded file adapter identity.

    Returns:
        Versioned async file-secret adapter identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_FILE_ASYNC_SECRET_PROVIDER_ID


def build_ticket_admission_file_async_secret_provider(
    provider: FileSecretProvider,
    offloader: TicketAdmissionTelemetryLineageFileSecretOffloader,
) -> TicketAdmissionTelemetryLineageFileAsyncSecretProvider:
    """Build one explicit caller-offloaded adapter over exact file state.

    Returns:
        Validated immutable async adapter with hidden provider and offloader.

    """
    validated = _validated_file_provider(provider)
    _validate_offloader(offloader)
    return TicketAdmissionTelemetryLineageFileAsyncSecretProvider(
        adapter_id=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_FILE_ASYNC_SECRET_PROVIDER_ID
        ),
        max_entries=validated.max_entries,
        max_secret_bytes=validated.max_secret_bytes,
        offloader=offloader,
        provider=validated,
        provider_id=validated.provider_id,
        secret_count=validated.secret_count,
    )


def validate_ticket_admission_file_async_secret_provider(
    adapter: TicketAdmissionTelemetryLineageFileAsyncSecretProvider,
) -> TicketAdmissionTelemetryLineageFileAsyncSecretProvider:
    """Validate one exact immutable caller-offloaded file adapter.

    Returns:
        The same exact adapter after complete binding validation.

    """
    return _validated_adapter(adapter)


def _validated_adapter(
    adapter: TicketAdmissionTelemetryLineageFileAsyncSecretProvider,
) -> TicketAdmissionTelemetryLineageFileAsyncSecretProvider:
    _validate_adapter_shape(adapter)
    validated = _validated_file_provider(adapter.provider)
    _validate_adapter_binding(adapter, validated)
    _validate_offloader(adapter.offloader)
    return adapter


def _validate_adapter_shape(
    adapter: TicketAdmissionTelemetryLineageFileAsyncSecretProvider,
) -> None:
    _validate_adapter_identity(adapter)
    _validate_adapter_limits(adapter)
    _validate_adapter_metadata(adapter)


def _validate_adapter_identity(
    adapter: TicketAdmissionTelemetryLineageFileAsyncSecretProvider,
) -> None:
    if (
        type(adapter)
        is not TicketAdmissionTelemetryLineageFileAsyncSecretProvider
    ):
        _raise_adapter("adapter must use the exact file-async secret type")
    if (
        adapter.adapter_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_FILE_ASYNC_SECRET_PROVIDER_ID
    ):
        _raise_adapter("adapter identity is unsupported")


def _validate_adapter_limits(
    adapter: TicketAdmissionTelemetryLineageFileAsyncSecretProvider,
) -> None:
    if type(adapter.max_entries) is not int or adapter.max_entries <= 0:
        _raise_adapter("adapter entry limit must be a positive integer")
    if type(adapter.max_secret_bytes) is not int:
        _raise_adapter("adapter secret byte limit must be an integer")
    if adapter.max_secret_bytes < MIN_TELEMETRY_LINEAGE_KEY_BYTES:
        _raise_adapter("adapter secret byte limit is below supported minimum")


def _validate_adapter_metadata(
    adapter: TicketAdmissionTelemetryLineageFileAsyncSecretProvider,
) -> None:
    if type(adapter.secret_count) is not int or adapter.secret_count < 0:
        _raise_adapter("adapter secret count must be a nonnegative integer")
    if type(adapter.provider_id) is not str or not adapter.provider_id:
        _raise_adapter("adapter provider identity must be a nonempty string")


def _validate_adapter_binding(
    adapter: TicketAdmissionTelemetryLineageFileAsyncSecretProvider,
    validated: FileSecretProvider,
) -> None:
    if adapter.max_entries != validated.max_entries:
        _raise_adapter("adapter entry limit does not match provider")
    if adapter.max_secret_bytes != validated.max_secret_bytes:
        _raise_adapter("adapter secret byte limit does not match provider")
    if adapter.provider_id != validated.provider_id:
        _raise_adapter("adapter provider identity does not match provider")
    if adapter.secret_count != validated.secret_count:
        _raise_adapter("adapter secret count does not match provider")


def _validated_file_provider(
    value: FileSecretProvider,
) -> FileSecretProvider:
    try:
        return _validate_file_provider(value)
    except (
        file_provider.TicketAdmissionTelemetryLineageFileSecretProviderError
    ) as error:
        message = "invalid synchronous file lineage secret provider"
        raise TicketAdmissionTelemetryLineageFileAsyncSecretProviderError(
            message
        ) from error


def _validate_offloader(value: object) -> None:
    if not callable(value):
        _raise_adapter("offloader must be callable")


def _validated_shared_request(
    request: port.TicketAdmissionTelemetryLineageSecretRequest,
) -> port.TicketAdmissionTelemetryLineageSecretRequest:
    try:
        return _validate_request(request)
    except port.TicketAdmissionTelemetryLineageSecretProviderError as error:
        message = "invalid caller-offloaded file secret request"
        raise TicketAdmissionTelemetryLineageFileAsyncSecretProviderError(
            message
        ) from error


async def _await_offloader(
    adapter: TicketAdmissionTelemetryLineageFileAsyncSecretProvider,
    request: port.TicketAdmissionTelemetryLineageSecretRequest,
) -> port.TicketAdmissionTelemetryLineageSecretResult:
    try:
        return await adapter.offloader(adapter.provider, request)
    except CancelledError:
        raise
    except Exception as error:
        message = "caller file-secret offloader raised during explicit read"
        raise TicketAdmissionTelemetryLineageFileAsyncSecretProviderError(
            message
        ) from error


def _validated_shared_result(
    result: port.TicketAdmissionTelemetryLineageSecretResult,
    *,
    max_secret_bytes: int,
) -> port.TicketAdmissionTelemetryLineageSecretResult:
    try:
        validated = _validate_result(result)
    except port.TicketAdmissionTelemetryLineageSecretProviderError as error:
        message = "caller file-secret offloader returned an invalid result"
        raise TicketAdmissionTelemetryLineageFileAsyncSecretProviderError(
            message
        ) from error
    if validated.kind is _RESOLVED:
        _validate_resolved_secret(
            validated.secret_key,
            max_secret_bytes=max_secret_bytes,
        )
    return validated


def _validate_resolved_secret(
    secret_key: bytes | None,
    *,
    max_secret_bytes: int,
) -> None:
    if type(secret_key) is not bytes:
        _raise_adapter("resolved result must use exact secret bytes")
    if len(secret_key) < MIN_TELEMETRY_LINEAGE_KEY_BYTES:
        _raise_adapter("resolved secret is shorter than supported minimum")
    if len(secret_key) > max_secret_bytes:
        _raise_adapter("resolved secret exceeds adapter byte limit")


def _failed_result() -> port.TicketAdmissionTelemetryLineageSecretResult:
    return port.TicketAdmissionTelemetryLineageSecretResult(kind=_FAILED)


def _raise_adapter(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage file async secret provider "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageFileAsyncSecretProviderError(message)
