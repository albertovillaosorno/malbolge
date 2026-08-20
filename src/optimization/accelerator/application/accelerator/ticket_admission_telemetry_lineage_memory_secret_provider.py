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
#   - Reusable bounded caller-owned in-memory lineage secret provider.
# - Must-Not:
#   - Read environment, files, network, secret stores, discover, refresh, retry,
#     cache externally, persist, log secrets, create workers, or change policy.
# - Allows:
#   - Inputs: one provider identity and explicit immutable secret entries.
#   - Outputs: stable typed results for exact manifest-bound requests.
#   - Side effects: none; retained secret bytes remain caller-owned.
# - Split-When:
#   - Split when external credentials, hosted APIs, certificates, or PKI
#     gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact bounded memory-secret boundary.
# - Summary:
#   - Exact reusable in-memory telemetry lineage secret provider.
# - Description:
#   - Revalidates hidden keys and exact manifest bindings before every lookup.
# - Usage:
#   - Build explicitly, then pass the service to the synchronous provider port.
# - Defaults:
#   - At most 256 entries; empty services return unavailable for every request.
#

"""Reusable bounded caller-owned in-memory lineage secret provider."""

# ruff: file-ignore[hardcoded-password-string]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from re import compile as compile_pattern
from typing import Final
from typing import Never

from accelerator import (
    ticket_admission_telemetry_lineage_secret_provider as port,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    TicketAdmissionTelemetryLineageTrustError,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    TicketAdmissionTelemetryLineageTrustKey,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    build_ticket_admission_telemetry_lineage_trust,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_MANIFEST_FINGERPRINT_PREFIX,
)

_MEMORY_SECRET_PROVIDER_ID_PREFIX: Final = (
    "bounded-in-memory-ticket-admission-telemetry-lineage-"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_SECRET_PROVIDER_ID: Final = (
    f"{_MEMORY_SECRET_PROVIDER_ID_PREFIX}secret-provider-v1"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_SECRETS: Final = (
    port.DEFAULT_MAX_TELEMETRY_LINEAGE_SECRET_PROVIDER_REQUESTS
)
MAX_TELEMETRY_LINEAGE_MEMORY_SECRETS: Final = 4096
_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_MANIFEST_FINGERPRINT_PATTERN: Final = compile_pattern(
    TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_MANIFEST_FINGERPRINT_PREFIX
    + r"[0-9a-f]{64}"
)
_RESOLVED: Final = port.TicketAdmissionTelemetryLineageSecretResultKind.RESOLVED
_UNAVAILABLE: Final = (
    port.TicketAdmissionTelemetryLineageSecretResultKind.UNAVAILABLE
)
_FAILED: Final = port.TicketAdmissionTelemetryLineageSecretResultKind.FAILED


class TicketAdmissionTelemetryLineageMemorySecretProviderError(ValueError):
    """A bounded in-memory lineage secret provider is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageMemorySecretEntry:
    """One hidden secret and its exact nonsecret manifest request binding."""

    first_capture_sequence_id: int
    key_id: str
    key_reference_id: str
    last_capture_sequence_id: int | None
    manifest_fingerprint: str
    secret_key: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageMemorySecretProvider:
    """Immutable bounded memory service for the secret-provider port."""

    entries: tuple[TicketAdmissionTelemetryLineageMemorySecretEntry, ...] = (
        field(repr=False)
    )
    max_entries: int
    provider_id: str
    secret_count: int
    service_id: str

    def __call__(
        self,
        request: port.TicketAdmissionTelemetryLineageSecretRequest,
    ) -> port.TicketAdmissionTelemetryLineageSecretResult:
        """Resolve one exact manifest-bound request without I/O or mutation.

        Returns:
            Stable resolved, unavailable, or failed provider result.

        """
        service = _validated_service(self)
        validated_request = _validated_request(request)
        return _lookup_result(service, validated_request)


def ticket_admission_telemetry_lineage_memory_secret_provider_id() -> str:
    """Return the stable bounded memory-secret service identity.

    Returns:
        Versioned caller-owned memory-service identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_SECRET_PROVIDER_ID


def build_ticket_admission_telemetry_lineage_memory_secret_provider(
    entries: tuple[TicketAdmissionTelemetryLineageMemorySecretEntry, ...],
    *,
    provider_id: str,
    max_entries: int = DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_SECRETS,
) -> TicketAdmissionTelemetryLineageMemorySecretProvider:
    """Build one bounded immutable provider from explicit caller-owned keys.

    Returns:
        Canonically ordered service with hidden secret bytes.

    """
    validated_provider_id = _validated_identifier(
        provider_id,
        "provider identity",
    )
    entry_limit = _validated_max_entries(max_entries)
    if type(entries) is not tuple:
        _raise_provider("entries must use the exact immutable tuple type")
    if len(entries) > entry_limit:
        _raise_provider("secret count exceeds configured entry limit")
    ordered = _ordered_entries(entries)
    return TicketAdmissionTelemetryLineageMemorySecretProvider(
        entries=ordered,
        max_entries=entry_limit,
        provider_id=validated_provider_id,
        secret_count=len(ordered),
        service_id=TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_SECRET_PROVIDER_ID,
    )


def validate_ticket_admission_telemetry_lineage_memory_secret_provider(
    service: TicketAdmissionTelemetryLineageMemorySecretProvider,
) -> TicketAdmissionTelemetryLineageMemorySecretProvider:
    """Validate one exact bounded memory-secret provider.

    Returns:
        The same exact service after complete revalidation.

    """
    return _validated_service(service)


def _ordered_entries(
    entries: tuple[TicketAdmissionTelemetryLineageMemorySecretEntry, ...],
) -> tuple[TicketAdmissionTelemetryLineageMemorySecretEntry, ...]:
    validated = tuple(_validated_entry(entry) for entry in entries)
    identities = [_entry_identity(entry) for entry in validated]
    if len(identities) != len(set(identities)):
        _raise_provider("entries contain duplicate manifest request binding")
    return tuple(sorted(validated, key=_entry_identity))


def _validated_service(
    service: TicketAdmissionTelemetryLineageMemorySecretProvider,
) -> TicketAdmissionTelemetryLineageMemorySecretProvider:
    _validate_service_shape(service)
    entry_limit = _validated_max_entries(service.max_entries)
    _validate_service_count(service, entry_limit=entry_limit)
    _validate_service_entries(service.entries)
    return service


def _validate_service_shape(
    service: TicketAdmissionTelemetryLineageMemorySecretProvider,
) -> None:
    if type(service) is not TicketAdmissionTelemetryLineageMemorySecretProvider:
        _raise_provider(
            "service must use the exact memory-secret provider type"
        )
    if (
        service.service_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_SECRET_PROVIDER_ID
    ):
        _raise_provider("service identity is unsupported")
    _ = _validated_identifier(service.provider_id, "provider identity")
    if type(service.entries) is not tuple:
        _raise_provider(
            "service entries must use the exact immutable tuple type"
        )


def _validate_service_count(
    service: TicketAdmissionTelemetryLineageMemorySecretProvider,
    *,
    entry_limit: int,
) -> None:
    if type(service.secret_count) is not int or service.secret_count < 0:
        _raise_provider("service secret count must be a nonnegative integer")
    if service.secret_count != len(service.entries):
        _raise_provider("service secret count does not match entries")
    if service.secret_count > entry_limit:
        _raise_provider("service secret count exceeds configured entry limit")


def _validate_service_entries(
    entries: tuple[TicketAdmissionTelemetryLineageMemorySecretEntry, ...],
) -> None:
    validated = tuple(_validated_entry(entry) for entry in entries)
    if validated != tuple(sorted(validated, key=_entry_identity)):
        _raise_provider("service entries are not canonically ordered")
    identities = [_entry_identity(entry) for entry in validated]
    if len(identities) != len(set(identities)):
        _raise_provider("service entries repeat a manifest request binding")


def _validated_entry(
    entry: TicketAdmissionTelemetryLineageMemorySecretEntry,
) -> TicketAdmissionTelemetryLineageMemorySecretEntry:
    if type(entry) is not TicketAdmissionTelemetryLineageMemorySecretEntry:
        _raise_provider("entry must use the exact memory-secret entry type")
    _ = _validated_manifest_fingerprint(entry.manifest_fingerprint)
    _ = _validated_identifier(entry.key_reference_id, "key reference identity")
    try:
        _ = build_ticket_admission_telemetry_lineage_trust(
            (
                TicketAdmissionTelemetryLineageTrustKey(
                    first_capture_sequence_id=entry.first_capture_sequence_id,
                    key_id=entry.key_id,
                    last_capture_sequence_id=entry.last_capture_sequence_id,
                    secret_key=entry.secret_key,
                ),
            ),
            max_keys=1,
        )
    except TicketAdmissionTelemetryLineageTrustError as error:
        message = "entry contains invalid key metadata or secret bytes"
        raise TicketAdmissionTelemetryLineageMemorySecretProviderError(
            message
        ) from error
    return entry


def _validated_request(
    request: port.TicketAdmissionTelemetryLineageSecretRequest,
) -> port.TicketAdmissionTelemetryLineageSecretRequest:
    if type(request) is not port.TicketAdmissionTelemetryLineageSecretRequest:
        _raise_provider(
            "request must use the exact secret-provider request type"
        )
    _ = _validated_identifier(request.key_id, "request key identity")
    _ = _validated_identifier(
        request.key_reference_id,
        "request key reference identity",
    )
    _ = _validated_identifier(request.provider_id, "request provider identity")
    _ = _validated_manifest_fingerprint(request.manifest_fingerprint)
    _validate_window(
        request.first_capture_sequence_id,
        request.last_capture_sequence_id,
    )
    if type(request.request_index) is not int or request.request_index < 0:
        _raise_provider("request index must be a nonnegative integer")
    return request


def _lookup_result(
    service: TicketAdmissionTelemetryLineageMemorySecretProvider,
    request: port.TicketAdmissionTelemetryLineageSecretRequest,
) -> port.TicketAdmissionTelemetryLineageSecretResult:
    kind = _FAILED
    secret_key: bytes | None = None
    if request.provider_id == service.provider_id:
        entry = _entry_for_reference(
            service.entries,
            manifest_fingerprint=request.manifest_fingerprint,
            key_reference_id=request.key_reference_id,
        )
        if entry is None:
            kind = _UNAVAILABLE
        elif _request_matches_entry(request, entry):
            kind = _RESOLVED
            secret_key = entry.secret_key
    return _result(kind, secret_key=secret_key)


def _entry_for_reference(
    entries: tuple[TicketAdmissionTelemetryLineageMemorySecretEntry, ...],
    *,
    manifest_fingerprint: str,
    key_reference_id: str,
) -> TicketAdmissionTelemetryLineageMemorySecretEntry | None:
    for entry in entries:
        if (
            entry.manifest_fingerprint == manifest_fingerprint
            and entry.key_reference_id == key_reference_id
        ):
            return entry
    return None


def _request_matches_entry(
    request: port.TicketAdmissionTelemetryLineageSecretRequest,
    entry: TicketAdmissionTelemetryLineageMemorySecretEntry,
) -> bool:
    return (
        request.first_capture_sequence_id == entry.first_capture_sequence_id
        and request.key_id == entry.key_id
        and request.last_capture_sequence_id == entry.last_capture_sequence_id
    )


def _entry_identity(
    entry: TicketAdmissionTelemetryLineageMemorySecretEntry,
) -> tuple[str, str]:
    return (entry.manifest_fingerprint, entry.key_reference_id)


def _result(
    kind: port.TicketAdmissionTelemetryLineageSecretResultKind,
    *,
    secret_key: bytes | None = None,
) -> port.TicketAdmissionTelemetryLineageSecretResult:
    return port.TicketAdmissionTelemetryLineageSecretResult(
        kind=kind,
        secret_key=secret_key,
    )


def _validated_manifest_fingerprint(value: str) -> str:
    if (
        type(value) is not str
        or _MANIFEST_FINGERPRINT_PATTERN.fullmatch(value) is None
    ):
        _raise_provider("manifest fingerprint must use canonical SHA-256 form")
    return value


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_provider(f"{field_name} must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_provider(f"{field_name} exceeds configured length")
    return value


def _validate_window(first: int, last: int | None) -> None:
    if type(first) is not int or first < 0:
        _raise_provider("first capture sequence identity must be nonnegative")
    if last is None:
        return
    if type(last) is not int or last < 0:
        _raise_provider("last capture sequence identity must be nonnegative")
    if last < first:
        _raise_provider("last capture sequence precedes first capture sequence")


def _validated_max_entries(value: int) -> int:
    if type(value) is not int or value <= 0:
        _raise_provider("maximum secret count must be a positive integer")
    if value > MAX_TELEMETRY_LINEAGE_MEMORY_SECRETS:
        _raise_provider("maximum secret count exceeds supported limit")
    return value


def _raise_provider(detail: str) -> Never:
    message = (
        f"ticket admission telemetry lineage memory secret provider {detail}"
    )
    raise TicketAdmissionTelemetryLineageMemorySecretProviderError(message)
