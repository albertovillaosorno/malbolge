# File:
#   - ticket_admission_telemetry_lineage_memory_public_key_provider.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
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
#   - Bounded caller-owned in-memory public-key provider implementation.
# - Must-Not:
#   - Read files, discover, retry, fetch, mutate, persist, spawn workers,
#     validate certificates, select algorithms, or change policy.
# - Allows:
#   - Inputs: exact provider identity and explicit immutable public-key entries.
#   - Outputs: stable typed provider results for exact manifest requests.
#   - Side effects: none; retained key bytes remain caller-owned in memory.
# - Split-When:
#   - Split when external services, certificates, or PKI gain
#     contracts.
# - Merge-When:
#   - Merge when another module owns this exact bounded memory-provider boundary.
# - Summary:
#   - Exact reusable in-memory detached-lineage public-key provider.
# - Description:
#   - Revalidates bounded key metadata and bytes before each explicit lookup.
# - Usage:
#   - Build explicitly, then pass the service to the synchronous provider port.
# - Defaults:
#   - At most 256 keys; empty services return unavailable for every request.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_session.py
# - accelerator/ticket_admission_telemetry_lineage_signature.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Bounded caller-owned in-memory public-key provider implementation."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from re import compile as compile_pattern
from typing import Final
from typing import Never

from accelerator import (
    ticket_admission_telemetry_lineage_public_key_provider as p,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignatureError,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)

_MEMORY_PROVIDER_ID_PREFIX: Final = "bounded-in-memory-ticket-admission-"
_MEMORY_PROVIDER_ID_SUFFIX: Final = "telemetry-lineage-public-key-provider-v1"
TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_PROVIDER_ID: Final = (
    f"{_MEMORY_PROVIDER_ID_PREFIX}{_MEMORY_PROVIDER_ID_SUFFIX}"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEYS: Final = (
    p.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_PROVIDER_REQUESTS
)

_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)


class TicketAdmissionTelemetryLineageMemoryPublicKeyProviderError(ValueError):
    """A bounded in-memory public-key service or request is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageMemoryPublicKeyEntry:
    """One exact key identity, reference, fingerprint, and capture window."""

    algorithm_id: str
    first_capture_sequence_id: int
    last_capture_sequence_id: int | None
    public_key: bytes = field(repr=False)
    public_key_fingerprint: str
    public_key_id: str
    public_key_reference_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageMemoryPublicKeyProvider:
    """Bounded immutable service sorted by external public-key reference."""

    entries: tuple[TicketAdmissionTelemetryLineageMemoryPublicKeyEntry, ...]
    key_count: int
    provider_id: str
    service_id: str

    def __call__(
        self,
        request: p.TicketAdmissionTelemetryLineagePublicKeyRequest,
    ) -> p.TicketAdmissionTelemetryLineagePublicKeyResult:
        """Resolve one exact request without I/O or hidden state.

        Returns:
            Stable resolved, unavailable, or failed provider result.

        """
        service = _validated_service(self)
        validated_request = _validated_request(request)
        if validated_request.provider_id != service.provider_id:
            _raise_provider("request provider identity does not match service")
        entry = _entry_for_reference(
            service.entries,
            validated_request.public_key_reference_id,
        )
        if entry is None:
            return _result(
                p.TicketAdmissionTelemetryLineagePublicKeyResultKind.UNAVAILABLE
            )
        if not _request_matches_entry(validated_request, entry):
            return _result(
                p.TicketAdmissionTelemetryLineagePublicKeyResultKind.FAILED
            )
        return _result(
            p.TicketAdmissionTelemetryLineagePublicKeyResultKind.RESOLVED,
            public_key=entry.public_key,
        )


def ticket_admission_telemetry_lineage_memory_public_key_provider_id() -> str:
    """Return the stable bounded in-memory service identity.

    Returns:
        Versioned memory-provider implementation identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_PROVIDER_ID


def build_ticket_admission_telemetry_lineage_memory_public_key_provider(
    entries: tuple[TicketAdmissionTelemetryLineageMemoryPublicKeyEntry, ...],
    *,
    provider_id: str,
    max_keys: int = DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEYS,
) -> TicketAdmissionTelemetryLineageMemoryPublicKeyProvider:
    """Build one bounded immutable provider from exact caller-owned key bytes.

    Returns:
        Reference-ordered service with hidden key material.

    """
    validated_provider_id = _validated_build_inputs(
        entries,
        provider_id=provider_id,
        max_keys=max_keys,
    )
    ordered = _ordered_entries(entries)
    return TicketAdmissionTelemetryLineageMemoryPublicKeyProvider(
        entries=ordered,
        key_count=len(ordered),
        provider_id=validated_provider_id,
        service_id=TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_PROVIDER_ID,
    )


def validate_ticket_admission_telemetry_lineage_memory_public_key_provider(
    provider: TicketAdmissionTelemetryLineageMemoryPublicKeyProvider,
) -> TicketAdmissionTelemetryLineageMemoryPublicKeyProvider:
    """Validate one exact bounded memory-provider object.

    Returns:
        The exact validated caller-owned provider.

    """
    return _validated_service(provider)


def _validated_build_inputs(
    entries: tuple[TicketAdmissionTelemetryLineageMemoryPublicKeyEntry, ...],
    *,
    provider_id: str,
    max_keys: int,
) -> str:
    if type(entries) is not tuple:
        _raise_provider("entries must use the exact immutable tuple type")
    key_limit = _validated_positive_limit(max_keys, "key limit")
    if len(entries) > key_limit:
        _raise_provider("key count exceeds configured limit")
    return _validated_identifier(provider_id, "provider identity")


def _ordered_entries(
    entries: tuple[TicketAdmissionTelemetryLineageMemoryPublicKeyEntry, ...],
) -> tuple[TicketAdmissionTelemetryLineageMemoryPublicKeyEntry, ...]:
    by_reference: dict[
        str, TicketAdmissionTelemetryLineageMemoryPublicKeyEntry
    ] = {}
    identities: set[tuple[str, str]] = set()
    for entry in entries:
        validated = _validated_entry(entry)
        identity = (validated.algorithm_id, validated.public_key_id)
        _validate_unique_entry(
            validated,
            identity=identity,
            identities=identities,
            by_reference=by_reference,
        )
        identities.add(identity)
        by_reference[validated.public_key_reference_id] = validated
    return tuple(by_reference[reference] for reference in sorted(by_reference))


def _validate_unique_entry(
    entry: TicketAdmissionTelemetryLineageMemoryPublicKeyEntry,
    *,
    identity: tuple[str, str],
    identities: set[tuple[str, str]],
    by_reference: dict[
        str, TicketAdmissionTelemetryLineageMemoryPublicKeyEntry
    ],
) -> None:
    if identity in identities:
        _raise_provider("duplicate algorithm and public-key identity")
    if entry.public_key_reference_id in by_reference:
        _raise_provider("duplicate public-key reference identity")


def _validated_service(
    service: TicketAdmissionTelemetryLineageMemoryPublicKeyProvider,
) -> TicketAdmissionTelemetryLineageMemoryPublicKeyProvider:
    _validate_service_shape(service)
    references = _validated_service_entries(service.entries)
    if references != sorted(references) or len(references) != len(
        set(references)
    ):
        _raise_provider("service entries are not uniquely reference ordered")
    return service


def _validate_service_shape(
    service: TicketAdmissionTelemetryLineageMemoryPublicKeyProvider,
) -> None:
    if (
        type(service)
        is not TicketAdmissionTelemetryLineageMemoryPublicKeyProvider
    ):
        _raise_provider("service must use the exact memory-provider type")
    if (
        service.service_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEY_PROVIDER_ID
    ):
        _raise_provider("service identity is unsupported")
    _ = _validated_identifier(service.provider_id, "provider identity")
    if type(service.entries) is not tuple:
        _raise_provider(
            "service entries must use the exact immutable tuple type"
        )
    _validate_service_count(service)


def _validate_service_count(
    service: TicketAdmissionTelemetryLineageMemoryPublicKeyProvider,
) -> None:
    if type(service.key_count) is not int or service.key_count < 0:
        _raise_provider("service key count must be a nonnegative integer")
    if service.key_count != len(service.entries):
        _raise_provider("service key count does not match entries")
    if service.key_count > DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEYS:
        _raise_provider("service key count exceeds default limit")


def _validated_service_entries(
    entries: tuple[TicketAdmissionTelemetryLineageMemoryPublicKeyEntry, ...],
) -> list[str]:
    references: list[str] = []
    identities: set[tuple[str, str]] = set()
    for entry in entries:
        validated = _validated_entry(entry)
        identity = (validated.algorithm_id, validated.public_key_id)
        if identity in identities:
            _raise_provider("service repeats algorithm and public-key identity")
        identities.add(identity)
        references.append(validated.public_key_reference_id)
    return references


def _validated_entry(
    entry: TicketAdmissionTelemetryLineageMemoryPublicKeyEntry,
) -> TicketAdmissionTelemetryLineageMemoryPublicKeyEntry:
    if type(entry) is not TicketAdmissionTelemetryLineageMemoryPublicKeyEntry:
        _raise_provider("entry must use the exact memory-provider entry type")
    _ = _validated_identifier(entry.algorithm_id, "algorithm identity")
    _ = _validated_identifier(entry.public_key_id, "public-key identity")
    _ = _validated_identifier(
        entry.public_key_reference_id,
        "public-key reference identity",
    )
    _validate_window(
        entry.first_capture_sequence_id,
        entry.last_capture_sequence_id,
    )
    if type(entry.public_key_fingerprint) is not str:
        _raise_provider("public-key fingerprint must use the exact string type")
    try:
        fingerprint = ticket_admission_telemetry_lineage_public_key_fingerprint(
            entry.public_key
        )
    except TicketAdmissionTelemetryLineageSignatureError as error:
        message = f"invalid public key: {error}"
        raise TicketAdmissionTelemetryLineageMemoryPublicKeyProviderError(
            message
        ) from error
    if entry.public_key_fingerprint != fingerprint:
        _raise_provider("public-key fingerprint does not match exact key bytes")
    return entry


def _validated_request(
    request: p.TicketAdmissionTelemetryLineagePublicKeyRequest,
) -> p.TicketAdmissionTelemetryLineagePublicKeyRequest:
    if type(request) is not p.TicketAdmissionTelemetryLineagePublicKeyRequest:
        _raise_provider("request must use the exact public-key request type")
    _ = _validated_identifier(
        request.algorithm_id, "request algorithm identity"
    )
    _ = _validated_identifier(request.provider_id, "request provider identity")
    _ = _validated_identifier(
        request.public_key_id, "request public-key identity"
    )
    _ = _validated_identifier(
        request.public_key_reference_id,
        "request public-key reference identity",
    )
    _validate_window(
        request.first_capture_sequence_id,
        request.last_capture_sequence_id,
    )
    if (
        type(request.manifest_fingerprint) is not str
        or not request.manifest_fingerprint
    ):
        _raise_provider(
            "request manifest fingerprint must be a nonempty string"
        )
    if (
        type(request.public_key_fingerprint) is not str
        or not request.public_key_fingerprint
    ):
        _raise_provider(
            "request public-key fingerprint must be a nonempty string"
        )
    if type(request.request_index) is not int or request.request_index < 0:
        _raise_provider("request index must be a nonnegative integer")
    return request


def _entry_for_reference(
    entries: tuple[TicketAdmissionTelemetryLineageMemoryPublicKeyEntry, ...],
    reference_id: str,
) -> TicketAdmissionTelemetryLineageMemoryPublicKeyEntry | None:
    return next(
        (
            entry
            for entry in entries
            if entry.public_key_reference_id == reference_id
        ),
        None,
    )


def _request_matches_entry(
    request: p.TicketAdmissionTelemetryLineagePublicKeyRequest,
    entry: TicketAdmissionTelemetryLineageMemoryPublicKeyEntry,
) -> bool:
    return (
        request.algorithm_id == entry.algorithm_id
        and request.first_capture_sequence_id == entry.first_capture_sequence_id
        and request.last_capture_sequence_id == entry.last_capture_sequence_id
        and request.public_key_fingerprint == entry.public_key_fingerprint
        and request.public_key_id == entry.public_key_id
    )


def _result(
    kind: p.TicketAdmissionTelemetryLineagePublicKeyResultKind,
    *,
    public_key: bytes | None = None,
) -> p.TicketAdmissionTelemetryLineagePublicKeyResult:
    return p.TicketAdmissionTelemetryLineagePublicKeyResult(
        kind=kind,
        public_key=public_key,
    )


def _validate_window(first: int, last: int | None) -> None:
    if type(first) is not int or first < 0:
        _raise_provider("first capture sequence identity must be nonnegative")
    if last is not None and (type(last) is not int or last < first):
        _raise_provider(
            "last capture sequence identity must be absent or ordered"
        )


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_provider(f"{field_name} must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_provider(f"{field_name} exceeds configured length")
    return value


def _validated_positive_limit(value: int, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        _raise_provider(f"{field_name} must be a positive integer")
    return value


def _raise_provider(detail: str) -> Never:
    message = (
        "ticket admission telemetry lineage memory public-key provider "
        f"{detail}"
    )
    raise TicketAdmissionTelemetryLineageMemoryPublicKeyProviderError(message)
