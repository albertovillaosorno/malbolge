# File:
#   - ticket_admission_telemetry_lineage_file_secret_provider.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_file_secret_provider.py
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
#   - Explicit bounded read-only files for lineage secret-provider requests.
# - Must-Not:
#   - Discover paths, write files, retry, cache secret bytes, inspect
#     permissions, follow provider lifecycles, log secrets or paths, create
#     workers, choose algorithms, or change policy.
# - Allows:
#   - Inputs: one provider identity and explicit manifest-bound absolute paths.
#   - Outputs: stable typed results containing exact caller-file bytes.
#   - Side effects: one bounded explicit file read for one exact matched
#     request.
# - Split-When:
#   - Split when native async file I/O, external stores, hosted APIs,
#     certificates, or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact explicit file-secret boundary.
# - Summary:
#   - Exact read-only file-backed telemetry lineage secret provider.
# - Description:
#   - Reads one caller-selected raw-byte file only after exact request binding.
# - Usage:
#   - Build explicitly from absolute paths, then pass to the synchronous port.
# - Defaults:
#   - At most 256 bindings and 4096 secret bytes per matched file.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_secret_provider.py
# - accelerator/ticket_admission_file_async_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_file_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_secret_provider.py
# - accelerator/ticket_admission_memory_async_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_trust_manifest.py
# - accelerator/ticket_admission_telemetry_lineage_trust.py
# - accelerator/ticket_admission_telemetry_lineage.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Explicit bounded read-only files for lineage secret-provider requests."""

# ruff: file-ignore[hardcoded-password-string]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from re import compile as compile_pattern
from typing import Final
from typing import Never

from accelerator import (
    ticket_admission_telemetry_lineage_memory_secret_provider as memory,
)
from accelerator import (
    ticket_admission_telemetry_lineage_secret_provider as port,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_KEY_BYTES,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MIN_TELEMETRY_LINEAGE_KEY_BYTES,
)

_build_memory_provider: Final = (
    memory.build_ticket_admission_telemetry_lineage_memory_secret_provider
)

_FILE_SECRET_PROVIDER_ID_PREFIX: Final = (
    "explicit-file-ticket-admission-telemetry-lineage-"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_FILE_SECRET_PROVIDER_ID: Final = (
    f"{_FILE_SECRET_PROVIDER_ID_PREFIX}secret-provider-v1"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_FILE_SECRETS: Final = (
    memory.DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_SECRETS
)
MAX_TELEMETRY_LINEAGE_FILE_SECRETS: Final = (
    memory.MAX_TELEMETRY_LINEAGE_MEMORY_SECRETS
)
DEFAULT_MAX_TELEMETRY_LINEAGE_FILE_SECRET_BYTES: Final = (
    MAX_TELEMETRY_LINEAGE_KEY_BYTES
)
MAX_TELEMETRY_LINEAGE_FILE_SECRET_BYTES: Final = MAX_TELEMETRY_LINEAGE_KEY_BYTES

_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_RESOLVED: Final = port.TicketAdmissionTelemetryLineageSecretResultKind.RESOLVED
_UNAVAILABLE: Final = (
    port.TicketAdmissionTelemetryLineageSecretResultKind.UNAVAILABLE
)
_FAILED: Final = port.TicketAdmissionTelemetryLineageSecretResultKind.FAILED
_NUL: Final = chr(0)


class TicketAdmissionTelemetryLineageFileSecretProviderError(ValueError):
    """An explicit bounded file-secret provider is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageFileSecretEntry:
    """One exact request binding and hidden absolute raw-secret path."""

    first_capture_sequence_id: int
    key_id: str
    key_reference_id: str
    last_capture_sequence_id: int | None
    manifest_fingerprint: str
    secret_path: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageFileSecretProvider:
    """Immutable explicit read-only file service for the provider port."""

    entries: tuple[TicketAdmissionTelemetryLineageFileSecretEntry, ...] = field(
        repr=False
    )
    max_entries: int
    max_secret_bytes: int
    provider_id: str
    secret_count: int
    service_id: str

    def __call__(
        self,
        request: port.TicketAdmissionTelemetryLineageSecretRequest,
    ) -> port.TicketAdmissionTelemetryLineageSecretResult:
        """Read one exact matched raw-secret file after full revalidation.

        Returns:
            Stable resolved, unavailable, or failed provider result.

        """
        service = _validated_service(self)
        validated_request = _validated_request(request)
        return _lookup_result(service, validated_request)


def ticket_admission_telemetry_lineage_file_secret_provider_id() -> str:
    """Return the stable explicit file-secret service identity.

    Returns:
        Versioned explicit file-service identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_FILE_SECRET_PROVIDER_ID


def build_ticket_admission_telemetry_lineage_file_secret_provider(
    entries: tuple[TicketAdmissionTelemetryLineageFileSecretEntry, ...],
    *,
    provider_id: str,
    max_entries: int = DEFAULT_MAX_TELEMETRY_LINEAGE_FILE_SECRETS,
    max_secret_bytes: int = DEFAULT_MAX_TELEMETRY_LINEAGE_FILE_SECRET_BYTES,
) -> TicketAdmissionTelemetryLineageFileSecretProvider:
    """Build one bounded immutable provider from explicit absolute paths.

    Returns:
        Canonically ordered service with hidden caller-selected paths.

    """
    validated_provider_id = _validated_identifier(
        provider_id,
        "provider identity",
    )
    entry_limit = _validated_max_entries(max_entries)
    secret_byte_limit = _validated_max_secret_bytes(max_secret_bytes)
    if type(entries) is not tuple:
        _raise_provider("entries must use the exact immutable tuple type")
    if len(entries) > entry_limit:
        _raise_provider("secret count exceeds configured entry limit")
    ordered = _ordered_entries(entries, provider_id=validated_provider_id)
    return TicketAdmissionTelemetryLineageFileSecretProvider(
        entries=ordered,
        max_entries=entry_limit,
        max_secret_bytes=secret_byte_limit,
        provider_id=validated_provider_id,
        secret_count=len(ordered),
        service_id=TICKET_ADMISSION_TELEMETRY_LINEAGE_FILE_SECRET_PROVIDER_ID,
    )


def validate_ticket_admission_telemetry_lineage_file_secret_provider(
    service: TicketAdmissionTelemetryLineageFileSecretProvider,
) -> TicketAdmissionTelemetryLineageFileSecretProvider:
    """Validate one exact bounded file-secret provider.

    Returns:
        The same exact service after complete non-I/O revalidation.

    """
    return _validated_service(service)


def _ordered_entries(
    entries: tuple[TicketAdmissionTelemetryLineageFileSecretEntry, ...],
    *,
    provider_id: str,
) -> tuple[TicketAdmissionTelemetryLineageFileSecretEntry, ...]:
    validated = tuple(
        _validated_entry(entry, provider_id=provider_id) for entry in entries
    )
    identities = [_entry_identity(entry) for entry in validated]
    if len(identities) != len(set(identities)):
        _raise_provider("entries contain duplicate manifest request binding")
    return tuple(sorted(validated, key=_entry_identity))


def _validated_service(
    service: TicketAdmissionTelemetryLineageFileSecretProvider,
) -> TicketAdmissionTelemetryLineageFileSecretProvider:
    _validate_service_shape(service)
    entry_limit = _validated_max_entries(service.max_entries)
    _ = _validated_max_secret_bytes(service.max_secret_bytes)
    _validate_service_count(service, entry_limit=entry_limit)
    validated = _ordered_entries(
        service.entries,
        provider_id=service.provider_id,
    )
    if service.entries != validated:
        _raise_provider("service entries are not canonically ordered")
    return service


def _validate_service_shape(
    service: TicketAdmissionTelemetryLineageFileSecretProvider,
) -> None:
    if type(service) is not TicketAdmissionTelemetryLineageFileSecretProvider:
        _raise_provider("service must use the exact file-secret provider type")
    if (
        service.service_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_FILE_SECRET_PROVIDER_ID
    ):
        _raise_provider("service identity is unsupported")
    _ = _validated_identifier(service.provider_id, "provider identity")
    if type(service.entries) is not tuple:
        _raise_provider(
            "service entries must use the exact immutable tuple type"
        )


def _validate_service_count(
    service: TicketAdmissionTelemetryLineageFileSecretProvider,
    *,
    entry_limit: int,
) -> None:
    if type(service.secret_count) is not int or service.secret_count < 0:
        _raise_provider("service secret count must be a nonnegative integer")
    if service.secret_count != len(service.entries):
        _raise_provider("service secret count does not match entries")
    if service.secret_count > entry_limit:
        _raise_provider("service secret count exceeds configured entry limit")


def _validated_entry(
    entry: TicketAdmissionTelemetryLineageFileSecretEntry,
    *,
    provider_id: str,
) -> TicketAdmissionTelemetryLineageFileSecretEntry:
    if type(entry) is not TicketAdmissionTelemetryLineageFileSecretEntry:
        _raise_provider("entry must use the exact file-secret entry type")
    request = port.TicketAdmissionTelemetryLineageSecretRequest(
        first_capture_sequence_id=entry.first_capture_sequence_id,
        key_id=entry.key_id,
        key_reference_id=entry.key_reference_id,
        last_capture_sequence_id=entry.last_capture_sequence_id,
        manifest_fingerprint=entry.manifest_fingerprint,
        provider_id=provider_id,
        request_index=0,
    )
    try:
        _ = port.validate_ticket_admission_telemetry_lineage_secret_request(
            request
        )
    except port.TicketAdmissionTelemetryLineageSecretProviderError as error:
        message = "entry contains invalid manifest request metadata"
        raise TicketAdmissionTelemetryLineageFileSecretProviderError(
            message
        ) from error
    _ = _validated_absolute_path(entry.secret_path)
    return entry


def _validated_request(
    request: port.TicketAdmissionTelemetryLineageSecretRequest,
) -> port.TicketAdmissionTelemetryLineageSecretRequest:
    try:
        return port.validate_ticket_admission_telemetry_lineage_secret_request(
            request
        )
    except port.TicketAdmissionTelemetryLineageSecretProviderError as error:
        message = "invalid file-provider secret request"
        raise TicketAdmissionTelemetryLineageFileSecretProviderError(
            message
        ) from error


def _lookup_result(
    service: TicketAdmissionTelemetryLineageFileSecretProvider,
    request: port.TicketAdmissionTelemetryLineageSecretRequest,
) -> port.TicketAdmissionTelemetryLineageSecretResult:
    result = _result(_FAILED)
    if request.provider_id == service.provider_id:
        entry = _entry_for_reference(
            service.entries,
            manifest_fingerprint=request.manifest_fingerprint,
            key_reference_id=request.key_reference_id,
        )
        if entry is None:
            result = _result(_UNAVAILABLE)
        elif _request_matches_entry(request, entry):
            result = _read_result(
                entry,
                request,
                provider_id=service.provider_id,
                max_secret_bytes=service.max_secret_bytes,
            )
    return result


def _read_result(
    entry: TicketAdmissionTelemetryLineageFileSecretEntry,
    request: port.TicketAdmissionTelemetryLineageSecretRequest,
    *,
    provider_id: str,
    max_secret_bytes: int,
) -> port.TicketAdmissionTelemetryLineageSecretResult:
    kind, secret_key = _read_secret_bytes(
        entry.secret_path,
        max_secret_bytes=max_secret_bytes,
    )
    result = _result(kind)
    if kind is _RESOLVED and secret_key is not None:
        result = _memory_result(
            entry,
            request,
            secret_key=secret_key,
            provider_id=provider_id,
        )
    return result


def _read_secret_bytes(
    secret_path: str,
    *,
    max_secret_bytes: int,
) -> tuple[port.TicketAdmissionTelemetryLineageSecretResultKind, bytes | None]:
    kind = _FAILED
    secret_key: bytes | None = None
    try:
        with Path(secret_path).open("rb") as stream:
            candidate = stream.read(max_secret_bytes + 1)
    except FileNotFoundError:
        kind = _UNAVAILABLE
    except OSError:
        kind = _FAILED
    else:
        if len(candidate) <= max_secret_bytes:
            kind = _RESOLVED
            secret_key = candidate
    return kind, secret_key


def _memory_result(
    entry: TicketAdmissionTelemetryLineageFileSecretEntry,
    request: port.TicketAdmissionTelemetryLineageSecretRequest,
    *,
    secret_key: bytes,
    provider_id: str,
) -> port.TicketAdmissionTelemetryLineageSecretResult:
    result = _result(_FAILED)
    try:
        memory_entry = memory.TicketAdmissionTelemetryLineageMemorySecretEntry(
            first_capture_sequence_id=entry.first_capture_sequence_id,
            key_id=entry.key_id,
            key_reference_id=entry.key_reference_id,
            last_capture_sequence_id=entry.last_capture_sequence_id,
            manifest_fingerprint=entry.manifest_fingerprint,
            secret_key=secret_key,
        )
        memory_service = _build_memory_provider(
            (memory_entry,),
            provider_id=provider_id,
            max_entries=1,
        )
        candidate = memory_service(request)
    except memory.TicketAdmissionTelemetryLineageMemorySecretProviderError:
        result = _result(_FAILED)
    else:
        if candidate.kind is _RESOLVED:
            result = candidate
    return result


def _entry_for_reference(
    entries: tuple[TicketAdmissionTelemetryLineageFileSecretEntry, ...],
    *,
    manifest_fingerprint: str,
    key_reference_id: str,
) -> TicketAdmissionTelemetryLineageFileSecretEntry | None:
    for entry in entries:
        if (
            entry.manifest_fingerprint == manifest_fingerprint
            and entry.key_reference_id == key_reference_id
        ):
            return entry
    return None


def _request_matches_entry(
    request: port.TicketAdmissionTelemetryLineageSecretRequest,
    entry: TicketAdmissionTelemetryLineageFileSecretEntry,
) -> bool:
    return (
        request.first_capture_sequence_id == entry.first_capture_sequence_id
        and request.key_id == entry.key_id
        and request.last_capture_sequence_id == entry.last_capture_sequence_id
    )


def _entry_identity(
    entry: TicketAdmissionTelemetryLineageFileSecretEntry,
) -> tuple[str, str]:
    return (entry.manifest_fingerprint, entry.key_reference_id)


def _result(
    kind: port.TicketAdmissionTelemetryLineageSecretResultKind,
) -> port.TicketAdmissionTelemetryLineageSecretResult:
    return port.TicketAdmissionTelemetryLineageSecretResult(kind=kind)


def _validated_absolute_path(value: str) -> str:
    if type(value) is not str or not value or _NUL in value:
        _raise_provider("secret path must be a nonempty path string")
    if not Path(value).is_absolute():
        _raise_provider("secret path must be absolute")
    return value


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_provider(f"{field_name} must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_provider(f"{field_name} exceeds configured length")
    return value


def _validated_max_entries(value: int) -> int:
    if type(value) is not int or value <= 0:
        _raise_provider("maximum secret count must be a positive integer")
    if value > MAX_TELEMETRY_LINEAGE_FILE_SECRETS:
        _raise_provider("maximum secret count exceeds supported limit")
    return value


def _validated_max_secret_bytes(value: int) -> int:
    if type(value) is not int:
        _raise_provider("maximum secret bytes must be an integer")
    if value < MIN_TELEMETRY_LINEAGE_KEY_BYTES:
        _raise_provider("maximum secret bytes is below the supported minimum")
    if value > MAX_TELEMETRY_LINEAGE_FILE_SECRET_BYTES:
        _raise_provider("maximum secret bytes exceeds supported limit")
    return value


def _raise_provider(detail: str) -> Never:
    message = (
        f"ticket admission telemetry lineage file secret provider {detail}"
    )
    raise TicketAdmissionTelemetryLineageFileSecretProviderError(message)
