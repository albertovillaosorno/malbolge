# File:
#   - test_ticket_admission_memory_secret_provider.py
# Path:
#   - tests/optimizer/test_ticket_admission_memory_secret_provider.py
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
#   - Bounded caller-owned in-memory lineage secret-provider regressions.
# - Must-Not:
#   - Read environment, files, network, secret stores, create hidden workers,
#     refresh, retry, persist, log secrets, require hardware, or change policy.
# - Allows:
#   - Inputs: synthetic manifests, secrets, requests, integration, and tampering.
#   - Outputs: exact lookup, binding, limits, secrecy, and failure assertions.
#   - Side effects: none beyond explicit in-process calls.
# - Split-When:
#   - Split when external credentials, hosted APIs, certificates, or PKI
#     gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact memory-secret behavior.
# - Summary:
#   - Exact bounded memory lineage secret-provider regressions.
# - Description:
#   - Proves hidden keys are revalidated against exact manifest-bound requests.
# - Usage:
#   - Runs without sockets, files, environment access, or accelerator hardware.
# - Defaults:
#   - Uses two synthetic 32-byte secrets and the 256-entry default.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_memory_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_secret_provider.py
# - accelerator/ticket_admission_memory_async_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_file_secret_provider.py
# - accelerator/ticket_admission_file_async_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_secret_provider.py
# - accelerator/ticket_admission_telemetry_lineage_trust_manifest.py
# - accelerator/ticket_admission_telemetry_lineage_trust.py
# - accelerator/ticket_admission_telemetry_lineage.py
# - accelerator/ticket_admission_telemetry_lineage_memory_https_auth_provider.py
# - accelerator/ticket_admission_memory_async_https_auth_provider.py
#
# Large file:
#   - false
#

"""Bounded caller-owned memory lineage secret-provider tests."""

# ruff: file-ignore[line-too-long,doc-line-too-long,undocumented-public-function]

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from typing import cast

import pytest

from accelerator import (
    ticket_admission_telemetry_lineage_memory_secret_provider as memory,
)
from accelerator import (
    ticket_admission_telemetry_lineage_secret_provider as port,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_KEY_BYTES,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MIN_TELEMETRY_LINEAGE_KEY_BYTES,
)

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
        TicketAdmissionTelemetryLineageTrustManifest,
    )
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    TicketAdmissionTelemetryLineageTrustManifestEntry,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    build_ticket_admission_telemetry_lineage_trust_manifest,
)
from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
    ticket_admission_telemetry_lineage_trust_manifest_fingerprint,
)

MemoryProviderError = (
    memory.TicketAdmissionTelemetryLineageMemorySecretProviderError
)
MemoryEntry = memory.TicketAdmissionTelemetryLineageMemorySecretEntry
MemoryProvider = memory.TicketAdmissionTelemetryLineageMemorySecretProvider
SecretRequest = port.TicketAdmissionTelemetryLineageSecretRequest
SecretResult = port.TicketAdmissionTelemetryLineageSecretResult
SecretKind = port.TicketAdmissionTelemetryLineageSecretResultKind
_build = memory.build_ticket_admission_telemetry_lineage_memory_secret_provider
_validate = (
    memory.validate_ticket_admission_telemetry_lineage_memory_secret_provider
)
_resolve = port.resolve_ticket_admission_telemetry_lineage_trust_with_provider

SERVICE_ID = (
    "bounded-in-memory-ticket-admission-telemetry-lineage-secret-provider-v1"
)
PROVIDER_ID = "provider.test.memory-lineage-secrets"
OTHER_PROVIDER_ID = "provider.test.other-lineage-secrets"
OLD_KEY_ID = "local.lineage-key.2026-07"
NEW_KEY_ID = "local.lineage-key.2026-08"
OLD_REFERENCE_ID = "vault.lineage-key.2026-07"
NEW_REFERENCE_ID = "vault.lineage-key.2026-08"
UNKNOWN_REFERENCE_ID = "vault.lineage-key.unknown"
OLD_SECRET = b"o" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
NEW_SECRET = b"n" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
OTHER_SECRET = b"z" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
SECRET_FIELD = b"secret_key"
ENTRIES_FIELD = b"entries=("
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_ENTRIES = 2
ONE_ENTRY = 1
DEFAULT_MAX_ENTRIES = 256
MAX_ENTRIES = 4096


def _entry(  # ruff: ignore[too-many-arguments]
    *,
    first_capture_sequence_id: int = GENESIS_SEQUENCE_ID,
    key_id: str = OLD_KEY_ID,
    key_reference_id: str = OLD_REFERENCE_ID,
    last_capture_sequence_id: int | None = GENESIS_SEQUENCE_ID,
    manifest_fingerprint: str,
    secret_key: bytes = OLD_SECRET,
) -> MemoryEntry:
    return MemoryEntry(
        first_capture_sequence_id=first_capture_sequence_id,
        key_id=key_id,
        key_reference_id=key_reference_id,
        last_capture_sequence_id=last_capture_sequence_id,
        manifest_fingerprint=manifest_fingerprint,
        secret_key=secret_key,
    )


def _manifest() -> TicketAdmissionTelemetryLineageTrustManifest:
    return build_ticket_admission_telemetry_lineage_trust_manifest((
        TicketAdmissionTelemetryLineageTrustManifestEntry(
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            key_id=NEW_KEY_ID,
            key_reference_id=NEW_REFERENCE_ID,
            last_capture_sequence_id=None,
        ),
        TicketAdmissionTelemetryLineageTrustManifestEntry(
            first_capture_sequence_id=GENESIS_SEQUENCE_ID,
            key_id=OLD_KEY_ID,
            key_reference_id=OLD_REFERENCE_ID,
            last_capture_sequence_id=GENESIS_SEQUENCE_ID,
        ),
    ))


def _manifest_fingerprint() -> str:
    return ticket_admission_telemetry_lineage_trust_manifest_fingerprint(
        _manifest()
    )


def _entries() -> tuple[MemoryEntry, ...]:
    fingerprint = _manifest_fingerprint()
    return (
        _entry(
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            key_id=NEW_KEY_ID,
            key_reference_id=NEW_REFERENCE_ID,
            last_capture_sequence_id=None,
            manifest_fingerprint=fingerprint,
            secret_key=NEW_SECRET,
        ),
        _entry(manifest_fingerprint=fingerprint),
    )


def _service(
    entries: tuple[MemoryEntry, ...] | None = None,
    *,
    provider_id: str = PROVIDER_ID,
    max_entries: int = DEFAULT_MAX_ENTRIES,
) -> MemoryProvider:
    return _build(
        _entries() if entries is None else entries,
        provider_id=provider_id,
        max_entries=max_entries,
    )


def _request(  # ruff: ignore[too-many-arguments]
    *,
    first_capture_sequence_id: int = GENESIS_SEQUENCE_ID,
    key_id: str = OLD_KEY_ID,
    key_reference_id: str = OLD_REFERENCE_ID,
    last_capture_sequence_id: int | None = GENESIS_SEQUENCE_ID,
    manifest_fingerprint: str | None = None,
    provider_id: str = PROVIDER_ID,
    request_index: int = 0,
) -> SecretRequest:
    return SecretRequest(
        first_capture_sequence_id=first_capture_sequence_id,
        key_id=key_id,
        key_reference_id=key_reference_id,
        last_capture_sequence_id=last_capture_sequence_id,
        manifest_fingerprint=(
            _manifest_fingerprint()
            if manifest_fingerprint is None
            else manifest_fingerprint
        ),
        provider_id=provider_id,
        request_index=request_index,
    )


def test_identity_limits_metadata_and_repr_are_stable() -> None:
    service = _service()
    representation = repr(service).encode("utf-8")
    entry_representation = repr(service.entries[0]).encode("utf-8")

    assert (
        memory.ticket_admission_telemetry_lineage_memory_secret_provider_id()
        == SERVICE_ID
    )
    assert (
        memory.DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_SECRETS
        == DEFAULT_MAX_ENTRIES
    )
    assert memory.MAX_TELEMETRY_LINEAGE_MEMORY_SECRETS == MAX_ENTRIES
    assert service.service_id == SERVICE_ID
    assert service.provider_id == PROVIDER_ID
    assert service.secret_count == TWO_ENTRIES
    assert service.max_entries == DEFAULT_MAX_ENTRIES
    assert _validate(service) is service
    assert OLD_SECRET not in representation
    assert NEW_SECRET not in representation
    assert SECRET_FIELD not in entry_representation
    assert ENTRIES_FIELD not in representation


def test_builder_canonically_orders_entries() -> None:
    service = _service()

    assert tuple(entry.key_reference_id for entry in service.entries) == (
        OLD_REFERENCE_ID,
        NEW_REFERENCE_ID,
    )


def test_exact_request_resolves_exact_caller_owned_secret() -> None:
    result = _service()(_request())

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key is OLD_SECRET
    assert OLD_SECRET not in repr(result).encode("utf-8")


def test_request_index_is_context_not_secret_binding() -> None:
    result = _service()(_request(request_index=19))

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key is OLD_SECRET


def test_repeated_calls_are_stable_and_cache_free() -> None:
    service = _service()

    first = service(_request())
    second = service(_request())

    assert first == second
    assert first.secret_key is OLD_SECRET
    assert second.secret_key is OLD_SECRET


def test_provider_identity_mismatch_returns_failed() -> None:
    result = _service()(_request(provider_id=OTHER_PROVIDER_ID))

    assert result == SecretResult(kind=SecretKind.FAILED)


@pytest.mark.parametrize(
    "changed_request",
    [
        _request(key_id=NEW_KEY_ID),
        _request(
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            last_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
        ),
        _request(last_capture_sequence_id=None),
    ],
)
def test_matching_reference_with_metadata_mismatch_returns_failed(
    changed_request: SecretRequest,
) -> None:
    result = _service()(changed_request)

    assert result == SecretResult(kind=SecretKind.FAILED)


def test_unknown_reference_returns_unavailable() -> None:
    result = _service()(_request(key_reference_id=UNKNOWN_REFERENCE_ID))

    assert result == SecretResult(kind=SecretKind.UNAVAILABLE)


def test_unknown_manifest_returns_unavailable() -> None:
    other_fingerprint = (
        "ticket-admission-telemetry-lineage-trust-manifest-v1:sha256:"
        + ("f" * 64)
    )
    result = _service()(_request(manifest_fingerprint=other_fingerprint))

    assert result == SecretResult(kind=SecretKind.UNAVAILABLE)


def test_empty_service_returns_unavailable() -> None:
    result = _service(())(_request())

    assert result == SecretResult(kind=SecretKind.UNAVAILABLE)


def test_second_exact_entry_resolves_second_secret() -> None:
    result = _service()(
        _request(
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            key_id=NEW_KEY_ID,
            key_reference_id=NEW_REFERENCE_ID,
            last_capture_sequence_id=None,
            request_index=1,
        )
    )

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key is NEW_SECRET


def test_provider_port_builds_manifest_bound_trust() -> None:
    resolved = _resolve(
        _manifest(),
        _service(),
        provider_id=PROVIDER_ID,
    )

    assert resolved.provider_id == PROVIDER_ID
    assert resolved.request_count == TWO_ENTRIES
    assert resolved.key_ids == (OLD_KEY_ID, NEW_KEY_ID)
    assert resolved.key_reference_ids == (
        OLD_REFERENCE_ID,
        NEW_REFERENCE_ID,
    )
    assert resolved.trust.key_count == TWO_ENTRIES
    assert tuple(key.secret_key for key in resolved.trust.keys) == (
        OLD_SECRET,
        NEW_SECRET,
    )
    representation = repr(resolved).encode("utf-8")
    assert OLD_SECRET not in representation
    assert NEW_SECRET not in representation


def test_repeated_port_resolution_reuses_only_explicit_memory_state() -> None:
    service = _service()

    first = _resolve(_manifest(), service, provider_id=PROVIDER_ID)
    second = _resolve(_manifest(), service, provider_id=PROVIDER_ID)

    assert first == second
    assert _validate(service) is service


def test_empty_manifest_and_empty_service_resolve_without_lookup() -> None:
    empty_manifest = build_ticket_admission_telemetry_lineage_trust_manifest(())
    resolved = _resolve(
        empty_manifest,
        _service(()),
        provider_id=PROVIDER_ID,
    )

    assert resolved.request_count == 0
    assert resolved.trust.key_count == 0


def test_service_revalidates_secret_bytes_on_every_call() -> None:
    service = _service()
    changed = replace(service.entries[0], secret_key=b"short")
    tampered = replace(service, entries=(changed, service.entries[1]))

    with pytest.raises(
        MemoryProviderError, match="invalid key metadata or secret"
    ):
        _ = tampered(_request())


def test_service_revalidates_entry_binding_on_every_call() -> None:
    service = _service()
    changed = replace(service.entries[0], key_id="bad key")
    tampered = replace(service, entries=(changed, service.entries[1]))

    with pytest.raises(
        MemoryProviderError, match="invalid key metadata or secret"
    ):
        _ = tampered(_request())


def test_foreign_request_type_fails_closed() -> None:
    with pytest.raises(
        MemoryProviderError, match="exact secret-provider request type"
    ):
        _ = _service()(cast("SecretRequest", object()))


def test_validator_rejects_foreign_service_type() -> None:
    with pytest.raises(
        MemoryProviderError, match="exact memory-secret provider type"
    ):
        _ = _validate(cast("MemoryProvider", object()))


def test_tampered_service_identity_fails_closed() -> None:
    tampered = replace(_service(), service_id="unsupported")

    with pytest.raises(
        MemoryProviderError, match="service identity is unsupported"
    ):
        _ = tampered(_request())


def test_tampered_provider_identity_fails_closed() -> None:
    tampered = replace(_service(), provider_id="bad provider")

    with pytest.raises(MemoryProviderError, match="provider identity"):
        _ = tampered(_request())


@pytest.mark.parametrize("secret_count", [-1, True])
def test_tampered_secret_count_type_fails_closed(secret_count: int) -> None:
    tampered = replace(_service(), secret_count=secret_count)

    with pytest.raises(MemoryProviderError, match="nonnegative integer"):
        _ = tampered(_request())


def test_tampered_secret_count_binding_fails_closed() -> None:
    tampered = replace(_service(), secret_count=ONE_ENTRY)

    with pytest.raises(MemoryProviderError, match="does not match entries"):
        _ = tampered(_request())


@pytest.mark.parametrize("max_entries", [0, -1, True])
def test_invalid_max_entry_limit_fails_closed(max_entries: int) -> None:
    with pytest.raises(MemoryProviderError, match="positive integer"):
        _ = _service((), max_entries=max_entries)


def test_max_entry_limit_above_supported_limit_fails_closed() -> None:
    with pytest.raises(MemoryProviderError, match="exceeds supported limit"):
        _ = _service((), max_entries=MAX_ENTRIES + 1)


def test_entry_count_above_configured_limit_fails_closed() -> None:
    with pytest.raises(MemoryProviderError, match="secret count exceeds"):
        _ = _service(_entries(), max_entries=ONE_ENTRY)


def test_entries_require_exact_tuple() -> None:
    with pytest.raises(MemoryProviderError, match="exact immutable tuple"):
        _ = _build(
            cast("tuple[MemoryEntry, ...]", object()),
            provider_id=PROVIDER_ID,
        )


def test_entry_requires_exact_type() -> None:
    with pytest.raises(
        MemoryProviderError, match="exact memory-secret entry type"
    ):
        _ = _service((cast("MemoryEntry", object()),))


@pytest.mark.parametrize(
    "provider_id",
    ["", "bad provider", cast("str", object())],
)
def test_provider_identity_requires_canonical_form(provider_id: str) -> None:
    with pytest.raises(
        MemoryProviderError, match="canonical ASCII identity form"
    ):
        _ = _service((), provider_id=provider_id)


@pytest.mark.parametrize(
    "entry",
    [
        _entry(
            manifest_fingerprint=(
                "ticket-admission-telemetry-lineage-trust-manifest-v1:sha256:"
                + ("0" * 63)
            )
        ),
        _entry(manifest_fingerprint="malformed"),
        _entry(manifest_fingerprint=_manifest_fingerprint(), key_id="bad key"),
        _entry(
            manifest_fingerprint=_manifest_fingerprint(),
            key_reference_id="bad reference",
        ),
        _entry(
            first_capture_sequence_id=-1,
            manifest_fingerprint=_manifest_fingerprint(),
        ),
        _entry(
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            last_capture_sequence_id=GENESIS_SEQUENCE_ID,
            manifest_fingerprint=_manifest_fingerprint(),
        ),
    ],
)
def test_entry_metadata_requires_canonical_shared_form(
    entry: MemoryEntry,
) -> None:
    with pytest.raises(MemoryProviderError):
        _ = _service((entry,))


@pytest.mark.parametrize(
    "secret_key",
    [
        b"",
        b"x" * (MIN_TELEMETRY_LINEAGE_KEY_BYTES - 1),
        b"x" * (MAX_TELEMETRY_LINEAGE_KEY_BYTES + 1),
        cast("bytes", cast("object", bytearray(OLD_SECRET))),
    ],
)
def test_entry_secret_uses_shared_trust_validation(secret_key: bytes) -> None:
    with pytest.raises(
        MemoryProviderError, match="invalid key metadata or secret"
    ):
        _ = _service((
            _entry(
                manifest_fingerprint=_manifest_fingerprint(),
                secret_key=secret_key,
            ),
        ))


@pytest.mark.parametrize(
    "secret_key",
    [
        b"x" * MIN_TELEMETRY_LINEAGE_KEY_BYTES,
        b"x" * MAX_TELEMETRY_LINEAGE_KEY_BYTES,
    ],
)
def test_exact_shared_secret_limits_are_accepted(secret_key: bytes) -> None:
    entry = _entry(
        manifest_fingerprint=_manifest_fingerprint(),
        secret_key=secret_key,
    )

    service = _service((entry,))
    result = service(_request())

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key is secret_key


def test_duplicate_manifest_request_binding_fails_closed() -> None:
    duplicate = replace(_entries()[1], secret_key=OTHER_SECRET)

    with pytest.raises(
        MemoryProviderError, match="duplicate manifest request binding"
    ):
        _ = _service((_entries()[1], duplicate))


def test_same_reference_under_distinct_manifests_is_explicitly_supported() -> (
    None
):
    first = _entries()[1]
    second_fingerprint = (
        "ticket-admission-telemetry-lineage-trust-manifest-v1:sha256:"
        + ("e" * 64)
    )
    second = replace(
        first,
        manifest_fingerprint=second_fingerprint,
        secret_key=OTHER_SECRET,
    )
    service = _service((second, first))

    first_result = service(_request())
    second_result = service(_request(manifest_fingerprint=second_fingerprint))

    assert first_result.secret_key is OLD_SECRET
    assert second_result.secret_key is OTHER_SECRET


def test_tampered_service_entry_order_fails_closed() -> None:
    service = _service()
    tampered = replace(service, entries=tuple(reversed(service.entries)))

    with pytest.raises(MemoryProviderError, match="not canonically ordered"):
        _ = tampered(_request())


def test_tampered_service_duplicate_binding_fails_closed() -> None:
    service = _service()
    duplicate = replace(service.entries[0], secret_key=OTHER_SECRET)
    tampered = replace(
        service,
        entries=(service.entries[0], duplicate),
        secret_count=TWO_ENTRIES,
    )

    with pytest.raises(
        MemoryProviderError, match="repeat a manifest request binding"
    ):
        _ = tampered(_request())


def test_tampered_service_entries_type_fails_closed() -> None:
    tampered = replace(
        _service(),
        entries=cast("tuple[MemoryEntry, ...]", object()),
    )

    with pytest.raises(MemoryProviderError, match="exact immutable tuple"):
        _ = tampered(_request())


@pytest.mark.parametrize(
    "changed_request",
    [
        replace(_request(), manifest_fingerprint="malformed"),
        replace(_request(), key_id="bad key"),
        replace(_request(), key_reference_id="bad reference"),
        replace(_request(), provider_id="bad provider"),
        replace(_request(), first_capture_sequence_id=-1),
        replace(_request(), request_index=-1),
        replace(_request(), request_index=True),
    ],
)
def test_malformed_requests_fail_closed(changed_request: SecretRequest) -> None:
    with pytest.raises(MemoryProviderError):
        _ = _service()(changed_request)


def test_tampered_service_max_entries_binding_fails_closed() -> None:
    tampered = replace(_service(), max_entries=ONE_ENTRY)

    with pytest.raises(
        MemoryProviderError, match="exceeds configured entry limit"
    ):
        _ = tampered(_request())
