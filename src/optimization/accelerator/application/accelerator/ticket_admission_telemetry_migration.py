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
#   - Explicit lossless schema-v1/schema-v2 telemetry migration and dispatch.
# - Must-Not:
#   - Auto-upgrade, load files, reinterpret snapshots, merge, or change policy.
# - Allows:
#   - Inputs: canonical schema-v1 or schema-v2 telemetry document bytes.
#   - Outputs: canonical versioned documents and a fixed compatibility matrix.
#   - Side effects: none.
# - Split-When:
#   - Split when schema-v3 or a lossy migration requires a separate contract.
# - Merge-When:
#   - Merge when persistence owns this exact multi-schema compatibility
#     boundary.
# - Summary:
#   - Lossless canonical ticket telemetry schema migration.
# - Description:
#   - Wraps exact schema-v1 bytes in schema-v2 without changing telemetry
#     meaning.
# - Usage:
#   - Decode explicitly, migrate explicitly, and encode the selected schema.
# - Defaults:
#   - 2 MiB versioned bytes, 1 MiB embedded v1 bytes, and 4,096 observations.
#

"""Lossless explicit migration for canonical ticket telemetry documents."""

from __future__ import annotations

from base64 import b64decode
from base64 import b64encode
from binascii import Error as Base64Error
from dataclasses import asdict
from dataclasses import dataclass
from hashlib import sha256
import json
from re import compile as compile_pattern
from typing import Final
from typing import Never
from typing import cast

from accelerator.ticket_admission_telemetry_collection import (
    TICKET_ADMISSION_TELEMETRY_DOCUMENT_FINGERPRINT_PREFIX,
)
from accelerator.ticket_admission_telemetry_persistence import (
    DEFAULT_MAX_TELEMETRY_DOCUMENT_BYTES,
)
from accelerator.ticket_admission_telemetry_persistence import (
    DEFAULT_MAX_TELEMETRY_OBSERVATIONS,
)
from accelerator.ticket_admission_telemetry_persistence import (
    TICKET_ADMISSION_TELEMETRY_DOCUMENT_ID,
)
from accelerator.ticket_admission_telemetry_persistence import (
    TICKET_ADMISSION_TELEMETRY_SCHEMA_VERSION,
)
from accelerator.ticket_admission_telemetry_persistence import (
    TicketAdmissionTelemetryDocument,
)
from accelerator.ticket_admission_telemetry_persistence import (
    TicketAdmissionTelemetryPersistenceError,
)
from accelerator.ticket_admission_telemetry_persistence import (
    decode_ticket_admission_telemetry_document,
)
from accelerator.ticket_admission_telemetry_persistence import (
    encode_ticket_admission_telemetry_document,
)

TICKET_ADMISSION_TELEMETRY_SCHEMA_MIGRATION_ID: Final = (
    "ticket-admission-telemetry-schema-migration-v1"
)
TICKET_ADMISSION_TELEMETRY_DOCUMENT_V2_ID: Final = (
    "ticket-admission-telemetry-document-v2"
)
TICKET_ADMISSION_TELEMETRY_SCHEMA_V2: Final = 2
TICKET_ADMISSION_TELEMETRY_SOURCE_ENCODING: Final = (
    "base64-standard-canonical-v1"
)
TICKET_ADMISSION_TELEMETRY_DOCUMENT_V2_FINGERPRINT_PREFIX: Final = (
    "ticket-admission-telemetry-document-v2:sha256:"
)
DEFAULT_MAX_TELEMETRY_VERSIONED_DOCUMENT_BYTES: Final = 2 * 1024 * 1024

_V2_ROOT_KEYS: Final = frozenset((
    "document_id",
    "schema_version",
    "source_document_encoding",
    "source_document_fingerprint",
    "source_document_id",
    "source_document_payload",
    "source_schema_version",
))
_SCHEMA_VERSION_KEY: Final = "schema_version"
_FINGERPRINT_PATTERN: Final = compile_pattern(
    rf"{TICKET_ADMISSION_TELEMETRY_DOCUMENT_FINGERPRINT_PREFIX}[0-9a-f]{{64}}"
)


class TicketAdmissionTelemetryMigrationError(ValueError):
    """A versioned telemetry document or migration request is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryDocumentV2:
    """Canonical schema-v2 wrapper preserving exact schema-v1 source bytes."""

    document_id: str
    schema_version: int
    source_document_encoding: str
    source_document_fingerprint: str
    source_document_id: str
    source_document_payload: str
    source_schema_version: int


type TicketAdmissionTelemetryVersionedDocument = (
    TicketAdmissionTelemetryDocument | TicketAdmissionTelemetryDocumentV2
)


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetrySchemaCompatibility:
    """One explicit lossless route in the fixed schema compatibility matrix."""

    lossless: bool
    preserves_schema_v1_canonical_bytes: bool
    source_schema_version: int
    target_schema_version: int


def ticket_admission_telemetry_schema_migration_id() -> str:
    """Return the stable explicit migration identity.

    Returns:
        Versioned migration identity.

    """
    return TICKET_ADMISSION_TELEMETRY_SCHEMA_MIGRATION_ID


def ticket_admission_telemetry_schema_compatibility() -> tuple[
    TicketAdmissionTelemetrySchemaCompatibility,
    ...,
]:
    """Return the fixed explicit lossless compatibility matrix.

    Returns:
        Four deterministic identity/upgrade/downgrade routes.

    """
    return tuple(
        TicketAdmissionTelemetrySchemaCompatibility(
            lossless=True,
            preserves_schema_v1_canonical_bytes=True,
            source_schema_version=source,
            target_schema_version=target,
        )
        for source, target in ((1, 1), (1, 2), (2, 1), (2, 2))
    )


def migrate_ticket_admission_telemetry_document(
    document: TicketAdmissionTelemetryVersionedDocument,
    *,
    target_schema_version: int,
) -> TicketAdmissionTelemetryVersionedDocument:
    """Migrate one document through the explicit lossless compatibility matrix.

    Returns:
        Validated document in the requested supported schema.

    """
    target = _validated_target_schema(target_schema_version)
    if type(document) is TicketAdmissionTelemetryDocument:
        return _migrate_from_v1(document, target)
    if type(document) is TicketAdmissionTelemetryDocumentV2:
        return _migrate_from_v2(document, target)
    return _raise_migration("document type is unsupported")


def encode_ticket_admission_telemetry_document_versioned(
    document: TicketAdmissionTelemetryVersionedDocument,
) -> bytes:
    """Encode one validated supported schema as canonical compact JSON.

    Returns:
        Exact canonical schema-v1 or schema-v2 bytes.

    Raises:
        TicketAdmissionTelemetryMigrationError: If the document is invalid.

    """
    if type(document) is TicketAdmissionTelemetryDocument:
        try:
            return encode_ticket_admission_telemetry_document(document)
        except TicketAdmissionTelemetryPersistenceError as error:
            message = f"invalid schema-v1 document: {error}"
            raise TicketAdmissionTelemetryMigrationError(message) from error
    if type(document) is TicketAdmissionTelemetryDocumentV2:
        state = _validated_v2(
            document,
            max_source_bytes=DEFAULT_MAX_TELEMETRY_DOCUMENT_BYTES,
            max_observations=DEFAULT_MAX_TELEMETRY_OBSERVATIONS,
        )
        return _canonical_json(asdict(state))
    return _raise_migration("document type is unsupported")


def decode_ticket_admission_telemetry_document_versioned(
    data: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_TELEMETRY_VERSIONED_DOCUMENT_BYTES,
    max_source_bytes: int = DEFAULT_MAX_TELEMETRY_DOCUMENT_BYTES,
    max_observations: int = DEFAULT_MAX_TELEMETRY_OBSERVATIONS,
) -> TicketAdmissionTelemetryVersionedDocument:
    """Decode canonical schema-v1 or schema-v2 bytes under explicit limits.

    Returns:
        Exact validated versioned telemetry document.

    """
    byte_limit = _validated_positive_limit(max_bytes, "byte limit")
    source_limit = _validated_positive_limit(
        max_source_bytes,
        "source byte limit",
    )
    observation_limit = _validated_positive_limit(
        max_observations,
        "observation limit",
    )
    payload = _validated_payload(data, byte_limit)
    schema_version = _schema_version(payload)
    if schema_version == TICKET_ADMISSION_TELEMETRY_SCHEMA_VERSION:
        return _decode_v1_payload(
            payload,
            max_source_bytes=source_limit,
            max_observations=observation_limit,
        )
    if schema_version == TICKET_ADMISSION_TELEMETRY_SCHEMA_V2:
        return _decode_v2_payload(
            payload,
            max_source_bytes=source_limit,
            max_observations=observation_limit,
        )
    return _raise_migration("document schema is unsupported")


def ticket_admission_telemetry_versioned_document_fingerprint(
    document: TicketAdmissionTelemetryVersionedDocument,
) -> str:
    """Return a schema-specific SHA-256 identity over canonical document bytes.

    Returns:
        Self-describing schema-v1 or schema-v2 document fingerprint.

    """
    canonical_bytes = encode_ticket_admission_telemetry_document_versioned(
        document
    )
    if type(document) is TicketAdmissionTelemetryDocument:
        prefix = TICKET_ADMISSION_TELEMETRY_DOCUMENT_FINGERPRINT_PREFIX
    elif type(document) is TicketAdmissionTelemetryDocumentV2:
        prefix = TICKET_ADMISSION_TELEMETRY_DOCUMENT_V2_FINGERPRINT_PREFIX
    else:
        _raise_migration("document type is unsupported")
    return f"{prefix}{sha256(canonical_bytes).hexdigest()}"


def _migrate_from_v1(
    document: TicketAdmissionTelemetryDocument,
    target_schema_version: int,
) -> TicketAdmissionTelemetryVersionedDocument:
    source = _validated_v1(document)
    if target_schema_version == TICKET_ADMISSION_TELEMETRY_SCHEMA_VERSION:
        return source
    return _migrate_v1_to_v2(source)


def _migrate_from_v2(
    document: TicketAdmissionTelemetryDocumentV2,
    target_schema_version: int,
) -> TicketAdmissionTelemetryVersionedDocument:
    source = _validated_v2(
        document,
        max_source_bytes=DEFAULT_MAX_TELEMETRY_DOCUMENT_BYTES,
        max_observations=DEFAULT_MAX_TELEMETRY_OBSERVATIONS,
    )
    if target_schema_version == TICKET_ADMISSION_TELEMETRY_SCHEMA_V2:
        return source
    return _source_v1_document(
        source,
        max_source_bytes=DEFAULT_MAX_TELEMETRY_DOCUMENT_BYTES,
        max_observations=DEFAULT_MAX_TELEMETRY_OBSERVATIONS,
    )


def _decode_v1_payload(
    payload: bytes,
    *,
    max_source_bytes: int,
    max_observations: int,
) -> TicketAdmissionTelemetryDocument:
    if len(payload) > max_source_bytes:
        _raise_migration("schema-v1 document exceeds source byte limit")
    try:
        return decode_ticket_admission_telemetry_document(
            payload,
            max_bytes=max_source_bytes,
            max_observations=max_observations,
        )
    except TicketAdmissionTelemetryPersistenceError as error:
        message = f"invalid schema-v1 document: {error}"
        raise TicketAdmissionTelemetryMigrationError(message) from error


def _decode_v2_payload(
    payload: bytes,
    *,
    max_source_bytes: int,
    max_observations: int,
) -> TicketAdmissionTelemetryDocumentV2:
    document = _v2_document(_json_mapping(payload))
    validated = _validated_v2(
        document,
        max_source_bytes=max_source_bytes,
        max_observations=max_observations,
    )
    if _canonical_json(asdict(validated)) != payload:
        _raise_migration("schema-v2 document bytes are not canonical")
    return validated


def _migrate_v1_to_v2(
    document: TicketAdmissionTelemetryDocument,
) -> TicketAdmissionTelemetryDocumentV2:
    canonical_bytes = encode_ticket_admission_telemetry_document(document)
    return TicketAdmissionTelemetryDocumentV2(
        document_id=TICKET_ADMISSION_TELEMETRY_DOCUMENT_V2_ID,
        schema_version=TICKET_ADMISSION_TELEMETRY_SCHEMA_V2,
        source_document_encoding=TICKET_ADMISSION_TELEMETRY_SOURCE_ENCODING,
        source_document_fingerprint=_v1_fingerprint(canonical_bytes),
        source_document_id=TICKET_ADMISSION_TELEMETRY_DOCUMENT_ID,
        source_document_payload=b64encode(canonical_bytes).decode("ascii"),
        source_schema_version=TICKET_ADMISSION_TELEMETRY_SCHEMA_VERSION,
    )


def _validated_v1(
    document: TicketAdmissionTelemetryDocument,
) -> TicketAdmissionTelemetryDocument:
    try:
        canonical_bytes = encode_ticket_admission_telemetry_document(document)
        return decode_ticket_admission_telemetry_document(
            canonical_bytes,
            max_bytes=len(canonical_bytes),
        )
    except TicketAdmissionTelemetryPersistenceError as error:
        message = f"invalid schema-v1 document: {error}"
        raise TicketAdmissionTelemetryMigrationError(message) from error


def _validated_v2(
    document: TicketAdmissionTelemetryDocumentV2,
    *,
    max_source_bytes: int,
    max_observations: int,
) -> TicketAdmissionTelemetryDocumentV2:
    _validate_v2_document_header(document)
    fingerprint = _validated_v2_source_header(document)
    source_bytes = _source_v1_bytes(
        document.source_document_payload,
        max_source_bytes=max_source_bytes,
    )
    source_document = _decode_source_v1(
        source_bytes,
        max_source_bytes=max_source_bytes,
        max_observations=max_observations,
    )
    canonical_source = encode_ticket_admission_telemetry_document(
        source_document
    )
    _validate_v2_source_binding(
        document,
        fingerprint=fingerprint,
        canonical_source=canonical_source,
        source_bytes=source_bytes,
    )
    return document


def _validate_v2_document_header(
    document: TicketAdmissionTelemetryDocumentV2,
) -> None:
    if type(document) is not TicketAdmissionTelemetryDocumentV2:
        _raise_migration("schema-v2 document type is invalid")
    if document.document_id != TICKET_ADMISSION_TELEMETRY_DOCUMENT_V2_ID:
        _raise_migration("schema-v2 document identity is unsupported")
    if (
        type(document.schema_version) is not int
        or document.schema_version != TICKET_ADMISSION_TELEMETRY_SCHEMA_V2
    ):
        _raise_migration("schema-v2 document schema is unsupported")


def _validated_v2_source_header(
    document: TicketAdmissionTelemetryDocumentV2,
) -> str:
    if (
        document.source_document_encoding
        != TICKET_ADMISSION_TELEMETRY_SOURCE_ENCODING
    ):
        _raise_migration("schema-v2 source encoding is unsupported")
    if document.source_document_id != TICKET_ADMISSION_TELEMETRY_DOCUMENT_ID:
        _raise_migration("schema-v2 source document identity is unsupported")
    if (
        type(document.source_schema_version) is not int
        or document.source_schema_version
        != TICKET_ADMISSION_TELEMETRY_SCHEMA_VERSION
    ):
        _raise_migration("schema-v2 source schema is unsupported")
    return _validated_v1_fingerprint(document.source_document_fingerprint)


def _validate_v2_source_binding(
    document: TicketAdmissionTelemetryDocumentV2,
    *,
    fingerprint: str,
    canonical_source: bytes,
    source_bytes: bytes,
) -> None:
    if canonical_source != source_bytes:
        _raise_migration("schema-v2 source bytes are not canonical schema-v1")
    if _v1_fingerprint(canonical_source) != fingerprint:
        _raise_migration("schema-v2 source document fingerprint mismatched")
    canonical_payload = b64encode(canonical_source).decode("ascii")
    if canonical_payload != document.source_document_payload:
        _raise_migration("schema-v2 source payload is not canonical Base64")


def _source_v1_document(
    document: TicketAdmissionTelemetryDocumentV2,
    *,
    max_source_bytes: int,
    max_observations: int,
) -> TicketAdmissionTelemetryDocument:
    state = _validated_v2(
        document,
        max_source_bytes=max_source_bytes,
        max_observations=max_observations,
    )
    source_bytes = _source_v1_bytes(
        state.source_document_payload,
        max_source_bytes=max_source_bytes,
    )
    return _decode_source_v1(
        source_bytes,
        max_source_bytes=max_source_bytes,
        max_observations=max_observations,
    )


def _source_v1_bytes(
    payload: str,
    *,
    max_source_bytes: int,
) -> bytes:
    if type(payload) is not str or not payload:
        _raise_migration("schema-v2 source payload must be a non-empty string")
    try:
        source_bytes = b64decode(payload, validate=True)
    except (Base64Error, ValueError) as error:
        message = "schema-v2 source payload is not valid Base64"
        raise TicketAdmissionTelemetryMigrationError(message) from error
    if not source_bytes:
        _raise_migration("schema-v2 source payload decoded to empty bytes")
    if len(source_bytes) > max_source_bytes:
        _raise_migration("schema-v2 source document exceeds source byte limit")
    return source_bytes


def _decode_source_v1(
    source_bytes: bytes,
    *,
    max_source_bytes: int,
    max_observations: int,
) -> TicketAdmissionTelemetryDocument:
    try:
        return decode_ticket_admission_telemetry_document(
            source_bytes,
            max_bytes=max_source_bytes,
            max_observations=max_observations,
        )
    except TicketAdmissionTelemetryPersistenceError as error:
        message = f"invalid schema-v2 source document: {error}"
        raise TicketAdmissionTelemetryMigrationError(message) from error


def _v2_document(
    mapping: dict[str, object],
) -> TicketAdmissionTelemetryDocumentV2:
    _expect_exact_keys(mapping, _V2_ROOT_KEYS, "schema-v2 document")
    return TicketAdmissionTelemetryDocumentV2(
        document_id=_expect_string(
            mapping["document_id"],
            "schema-v2 document.document_id",
        ),
        schema_version=_expect_int(
            mapping["schema_version"],
            "schema-v2 document.schema_version",
        ),
        source_document_encoding=_expect_string(
            mapping["source_document_encoding"],
            "schema-v2 document.source_document_encoding",
        ),
        source_document_fingerprint=_expect_string(
            mapping["source_document_fingerprint"],
            "schema-v2 document.source_document_fingerprint",
        ),
        source_document_id=_expect_string(
            mapping["source_document_id"],
            "schema-v2 document.source_document_id",
        ),
        source_document_payload=_expect_string(
            mapping["source_document_payload"],
            "schema-v2 document.source_document_payload",
        ),
        source_schema_version=_expect_int(
            mapping["source_schema_version"],
            "schema-v2 document.source_schema_version",
        ),
    )


def _schema_version(payload: bytes) -> int:
    mapping = _json_mapping(payload)
    if _SCHEMA_VERSION_KEY not in mapping:
        _raise_migration("document is missing key: schema_version")
    return _expect_int(
        mapping[_SCHEMA_VERSION_KEY],
        "document.schema_version",
    )


def _json_mapping(payload: bytes) -> dict[str, object]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        message = f"versioned document is not UTF-8: {error}"
        raise TicketAdmissionTelemetryMigrationError(message) from error
    try:
        parsed = cast(
            "object",
            json.loads(
                text,
                object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=_reject_json_constant,
            ),
        )
    except json.JSONDecodeError as error:
        message = f"invalid versioned document JSON: {error}"
        raise TicketAdmissionTelemetryMigrationError(message) from error
    if not isinstance(parsed, dict):
        _raise_migration("versioned document must be a JSON object")
    mapping = cast("dict[object, object]", parsed)
    if any(type(key) is not str for key in mapping):
        _raise_migration("versioned document contains a non-string key")
    return cast("dict[str, object]", mapping)


def _reject_duplicate_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            _raise_migration(f"duplicate versioned JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Never:
    _raise_migration(f"invalid versioned JSON constant: {value}")


def _canonical_json(value: object) -> bytes:
    text = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{text}\n".encode()


def _validated_payload(data: bytes, max_bytes: int) -> bytes:
    if type(data) is not bytes:
        _raise_migration("document payload must be bytes")
    if not data:
        _raise_migration("document payload must not be empty")
    if len(data) > max_bytes:
        _raise_migration("versioned document exceeds configured byte limit")
    return data


def _validated_target_schema(target_schema_version: int) -> int:
    if type(target_schema_version) is not int:
        _raise_migration("target schema must be an integer")
    if target_schema_version not in {
        TICKET_ADMISSION_TELEMETRY_SCHEMA_VERSION,
        TICKET_ADMISSION_TELEMETRY_SCHEMA_V2,
    }:
        _raise_migration("target schema is unsupported")
    return target_schema_version


def _validated_v1_fingerprint(fingerprint: str) -> str:
    if (
        type(fingerprint) is not str
        or _FINGERPRINT_PATTERN.fullmatch(fingerprint) is None
    ):
        _raise_migration("schema-v2 source document fingerprint is invalid")
    return fingerprint


def _v1_fingerprint(canonical_bytes: bytes) -> str:
    digest = sha256(canonical_bytes).hexdigest()
    return f"{TICKET_ADMISSION_TELEMETRY_DOCUMENT_FINGERPRINT_PREFIX}{digest}"


def _expect_exact_keys(
    mapping: dict[str, object],
    expected: frozenset[str],
    context: str,
) -> None:
    observed = frozenset(mapping)
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    if missing:
        _raise_migration(f"{context} is missing key: {missing[0]}")
    if unknown:
        _raise_migration(f"{context} contains unknown key: {unknown[0]}")


def _expect_string(value: object, context: str) -> str:
    if type(value) is not str or not value:
        _raise_migration(f"{context} must be a non-empty string")
    return value


def _expect_int(value: object, context: str) -> int:
    if type(value) is not int or value < 0:
        _raise_migration(f"{context} must be a non-negative integer")
    return value


def _validated_positive_limit(value: int, label: str) -> int:
    if type(value) is not int or value <= 0:
        _raise_migration(f"{label} must be a positive integer")
    return value


def _raise_migration(detail: str) -> Never:
    message = f"ticket admission telemetry migration {detail}"
    raise TicketAdmissionTelemetryMigrationError(message)
