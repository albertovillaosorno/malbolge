# File:
#   - ticket_admission_telemetry_lineage.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage.py
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
#   - Canonical HMAC-authenticated recorder and capture lineage attestations.
# - Must-Not:
#   - Store keys, infer identity from observations, merge snapshots, or
#     change policy.
# - Allows:
#   - Inputs: one document, explicit lineage claims, and caller-supplied
#     trust keys.
#   - Outputs: canonical attestations, verified claims, and pairwise
#     lineage reports.
#   - Side effects: none.
# - Split-When:
#   - Split when asymmetric signatures or asynchronous provider
#     lifecycles gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact authenticated-lineage boundary.
# - Summary:
#   - Caller-trusted authenticated telemetry recorder lineage.
# - Description:
#   - Authenticates explicit recorder claims without deriving them from
#     telemetry.
# - Usage:
#   - Create with a secret, persist the attestation, then verify explicitly.
# - Defaults:
#   - HMAC-SHA-256, canonical JSON, 16 KiB decode bound, and 32-byte
#     minimum keys.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_collection.py
# - accelerator/ticket_admission_telemetry_overlap_components.py
# - accelerator/ticket_admission_telemetry_persistence.py
# - accelerator/ticket_admission_telemetry_store.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Caller-trusted authentication for telemetry recorder lineage."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from enum import StrEnum
from hashlib import sha256
from hmac import compare_digest
from hmac import digest as hmac_digest
from json import JSONDecodeError
from json import dumps
from json import loads
from re import compile as compile_pattern
from typing import Final
from typing import Never
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

from accelerator.ticket_admission_telemetry_collection import (
    TicketAdmissionTelemetryCollectionError,
)
from accelerator.ticket_admission_telemetry_collection import (
    ticket_admission_telemetry_document_fingerprint,
)
from accelerator.ticket_admission_telemetry_persistence import (
    TicketAdmissionTelemetryPersistenceError,
)
from accelerator.ticket_admission_telemetry_persistence import (
    encode_ticket_admission_telemetry_document,
)

TICKET_ADMISSION_TELEMETRY_LINEAGE_SCHEMA_VERSION: Final = 1
TICKET_ADMISSION_TELEMETRY_LINEAGE_ID: Final = (
    "authenticated-ticket-admission-telemetry-lineage-v1"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_ALGORITHM_ID: Final = "hmac-sha256"
TICKET_ADMISSION_TELEMETRY_LINEAGE_FINGERPRINT_PREFIX: Final = (
    "ticket-admission-telemetry-lineage-v1:sha256:"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_BYTES: Final = 16 * 1024
MIN_TELEMETRY_LINEAGE_KEY_BYTES: Final = 32
MAX_TELEMETRY_LINEAGE_KEY_BYTES: Final = 4_096
MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH: Final = 128

_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_MAC_PATTERN: Final = compile_pattern(r"[0-9a-f]{64}")
_DOCUMENT_FINGERPRINT_PATTERN: Final = compile_pattern(
    r"ticket-admission-telemetry-document-v1:sha256:[0-9a-f]{64}"
)
_FINGERPRINT_PATTERN: Final = compile_pattern(
    r"ticket-admission-telemetry-lineage-v1:sha256:[0-9a-f]{64}"
)
_ATTESTATION_KEYS: Final = (
    "algorithm_id",
    "attestation_id",
    "capture_sequence_id",
    "completed_stream_id",
    "document_fingerprint",
    "failed_stream_id",
    "key_id",
    "mac_hex",
    "previous_attestation_fingerprint",
    "recorder_id",
    "schema_version",
)


class TicketAdmissionTelemetryLineageError(ValueError):
    """A telemetry lineage attestation cannot be created or verified."""


class TicketAdmissionTelemetryLineageRelation(StrEnum):
    """Stable relation between two independently verified attestations."""

    DIFFERENT_RECORDER = "different-recorder"
    DIFFERENT_STREAMS = "different-streams"
    DIRECT_SUCCESSOR = "direct-successor"
    ORDERED_GAP = "ordered-gap"
    SAME_CAPTURE = "same-capture"


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageClaim:
    """Caller-supplied recorder, stream, capture, and trust-key claims."""

    capture_sequence_id: int
    completed_stream_id: str
    failed_stream_id: str
    key_id: str
    previous_attestation_fingerprint: str | None
    recorder_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageAttestation:
    """Canonical authenticated claim binding one document to one capture."""

    algorithm_id: str
    attestation_id: str
    capture_sequence_id: int
    completed_stream_id: str
    document_fingerprint: str
    failed_stream_id: str
    key_id: str
    mac_hex: str
    previous_attestation_fingerprint: str | None
    recorder_id: str
    schema_version: int


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageItem:
    """One document paired with its claimed lineage attestation."""

    attestation: TicketAdmissionTelemetryLineageAttestation
    document: TicketAdmissionTelemetryDocument


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryVerifiedLineage:
    """One claim verified against a caller-selected symmetric trust key."""

    attestation_fingerprint: str
    canonical_byte_count: int
    capture_sequence_id: int
    completed_stream_id: str
    document_fingerprint: str
    failed_stream_id: str
    key_id: str
    previous_attestation_fingerprint: str | None
    recorder_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryVerifiedLineageItem:
    """Canonical bytes and verified claim for one lineage item."""

    attestation_bytes: bytes
    document_bytes: bytes
    verified: TicketAdmissionTelemetryVerifiedLineage


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageComparison:
    """Deterministic relation between two authenticated recorder claims."""

    common_recorder_lineage: bool
    direct_chain_link: bool
    exact_attestation_match: bool
    exact_document_match: bool
    first: TicketAdmissionTelemetryVerifiedLineage
    relation: TicketAdmissionTelemetryLineageRelation
    second: TicketAdmissionTelemetryVerifiedLineage
    sequence_gap: int | None


class _DuplicateKeyError(ValueError):
    """A decoded lineage JSON object contains a duplicate key."""


@dataclass(frozen=True, slots=True)
class _RelationDecision:
    common_lineage: bool
    direct_link: bool
    relation: TicketAdmissionTelemetryLineageRelation
    sequence_gap: int | None


def ticket_admission_telemetry_lineage_id() -> str:
    """Return the stable authenticated lineage identity.

    Returns:
        Versioned authenticated-lineage identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_ID


def create_ticket_admission_telemetry_lineage_attestation(
    document: TicketAdmissionTelemetryDocument,
    claim: TicketAdmissionTelemetryLineageClaim,
    *,
    secret_key: bytes,
) -> TicketAdmissionTelemetryLineageAttestation:
    """Create one canonical HMAC-authenticated document lineage claim.

    Returns:
        Immutable attestation that stores no secret key material.

    """
    key = _validated_secret_key(secret_key)
    validated_claim = _validated_claim(claim)
    attestation = TicketAdmissionTelemetryLineageAttestation(
        algorithm_id=TICKET_ADMISSION_TELEMETRY_LINEAGE_ALGORITHM_ID,
        attestation_id=TICKET_ADMISSION_TELEMETRY_LINEAGE_ID,
        capture_sequence_id=validated_claim.capture_sequence_id,
        completed_stream_id=validated_claim.completed_stream_id,
        document_fingerprint=_document_fingerprint(document),
        failed_stream_id=validated_claim.failed_stream_id,
        key_id=validated_claim.key_id,
        mac_hex="0" * 64,
        previous_attestation_fingerprint=(
            validated_claim.previous_attestation_fingerprint
        ),
        recorder_id=validated_claim.recorder_id,
        schema_version=TICKET_ADMISSION_TELEMETRY_LINEAGE_SCHEMA_VERSION,
    )
    return replace(
        attestation,
        mac_hex=_mac_hex(key, _unsigned_payload_bytes(attestation)),
    )


def encode_ticket_admission_telemetry_lineage_attestation(
    attestation: TicketAdmissionTelemetryLineageAttestation,
) -> bytes:
    """Encode one structurally valid attestation as canonical JSON bytes.

    Returns:
        Compact sorted-key UTF-8 JSON bytes.

    """
    validated = _validated_attestation(attestation)
    return _canonical_json_bytes(_attestation_mapping(validated))


def decode_ticket_admission_telemetry_lineage_attestation(
    data: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_TELEMETRY_LINEAGE_BYTES,
) -> TicketAdmissionTelemetryLineageAttestation:
    """Decode one canonical bounded lineage attestation.

    Returns:
        Structurally validated attestation; MAC verification remains explicit.

    """
    canonical_input = _validated_encoded_input(data, max_bytes=max_bytes)
    mapping = _decoded_mapping(canonical_input)
    attestation = TicketAdmissionTelemetryLineageAttestation(
        algorithm_id=_required_str(mapping, "algorithm_id"),
        attestation_id=_required_str(mapping, "attestation_id"),
        capture_sequence_id=_required_int(mapping, "capture_sequence_id"),
        completed_stream_id=_required_str(mapping, "completed_stream_id"),
        document_fingerprint=_required_str(mapping, "document_fingerprint"),
        failed_stream_id=_required_str(mapping, "failed_stream_id"),
        key_id=_required_str(mapping, "key_id"),
        mac_hex=_required_str(mapping, "mac_hex"),
        previous_attestation_fingerprint=_optional_str(
            mapping,
            "previous_attestation_fingerprint",
        ),
        recorder_id=_required_str(mapping, "recorder_id"),
        schema_version=_required_int(mapping, "schema_version"),
    )
    validated = _validated_attestation(attestation)
    if encode_ticket_admission_telemetry_lineage_attestation(validated) != data:
        _raise_lineage("encoded attestation must use canonical JSON")
    return validated


def ticket_admission_telemetry_lineage_attestation_fingerprint(
    attestation: TicketAdmissionTelemetryLineageAttestation,
) -> str:
    """Return the SHA-256 identity of canonical attestation bytes.

    Returns:
        Versioned attestation fingerprint.

    """
    canonical_bytes = encode_ticket_admission_telemetry_lineage_attestation(
        attestation
    )
    return _attestation_fingerprint(canonical_bytes)


def verify_ticket_admission_telemetry_lineage_attestation(
    item: TicketAdmissionTelemetryLineageItem,
    *,
    secret_key: bytes,
    trusted_key_id: str,
) -> TicketAdmissionTelemetryVerifiedLineage:
    """Verify one document-bound attestation under a caller-selected key.

    Returns:
        Authenticated lineage fields and canonical attestation identity.

    """
    return verify_ticket_admission_telemetry_lineage_item(
        item,
        secret_key=secret_key,
        trusted_key_id=trusted_key_id,
    ).verified


def verify_ticket_admission_telemetry_lineage_item(
    item: TicketAdmissionTelemetryLineageItem,
    *,
    secret_key: bytes,
    trusted_key_id: str,
) -> TicketAdmissionTelemetryVerifiedLineageItem:
    """Verify one item and retain its exact canonical comparison material.

    Returns:
        Canonical document and attestation bytes with the verified claim.

    """
    validated_item = _validated_item(item)
    key = _validated_secret_key(secret_key)
    trusted_id = _validated_identifier(trusted_key_id, "trusted key identity")
    validated = _validated_attestation(validated_item.attestation)
    if validated.key_id != trusted_id:
        _raise_lineage("attestation key identity is not trusted")
    document_fingerprint = _document_fingerprint(validated_item.document)
    if validated.document_fingerprint != document_fingerprint:
        _raise_lineage("attestation document fingerprint does not match")
    expected_mac = _mac_hex(key, _unsigned_payload_bytes(validated))
    if not compare_digest(validated.mac_hex, expected_mac):
        _raise_lineage("attestation authentication failed")
    attestation_bytes = encode_ticket_admission_telemetry_lineage_attestation(
        validated
    )
    return TicketAdmissionTelemetryVerifiedLineageItem(
        attestation_bytes=attestation_bytes,
        document_bytes=_document_bytes(validated_item.document),
        verified=TicketAdmissionTelemetryVerifiedLineage(
            attestation_fingerprint=_attestation_fingerprint(attestation_bytes),
            canonical_byte_count=len(attestation_bytes),
            capture_sequence_id=validated.capture_sequence_id,
            completed_stream_id=validated.completed_stream_id,
            document_fingerprint=validated.document_fingerprint,
            failed_stream_id=validated.failed_stream_id,
            key_id=validated.key_id,
            previous_attestation_fingerprint=(
                validated.previous_attestation_fingerprint
            ),
            recorder_id=validated.recorder_id,
        ),
    )


def compare_ticket_admission_telemetry_lineage(
    first: TicketAdmissionTelemetryLineageItem,
    second: TicketAdmissionTelemetryLineageItem,
    *,
    secret_key: bytes,
    trusted_key_id: str,
) -> TicketAdmissionTelemetryLineageComparison:
    """Compare two authenticated claims under one explicit trust key.

    Returns:
        Canonically ordered recorder, stream, capture, and chain relation.

    """
    return compare_verified_ticket_admission_telemetry_lineage(
        verify_ticket_admission_telemetry_lineage_item(
            first,
            secret_key=secret_key,
            trusted_key_id=trusted_key_id,
        ),
        verify_ticket_admission_telemetry_lineage_item(
            second,
            secret_key=secret_key,
            trusted_key_id=trusted_key_id,
        ),
    )


def compare_verified_ticket_admission_telemetry_lineage(
    first: TicketAdmissionTelemetryVerifiedLineageItem,
    second: TicketAdmissionTelemetryVerifiedLineageItem,
) -> TicketAdmissionTelemetryLineageComparison:
    """Compare two independently verified canonical lineage materials.

    Returns:
        Canonically ordered recorder, stream, capture, and chain relation.

    """
    first_material = _validated_verified_item(first)
    second_material = _validated_verified_item(second)
    _reject_fingerprint_collisions(first_material, second_material)
    earlier, later = tuple(
        sorted((first_material, second_material), key=_material_identity)
    )
    decision = _lineage_relation(earlier.verified, later.verified)
    return TicketAdmissionTelemetryLineageComparison(
        common_recorder_lineage=decision.common_lineage,
        direct_chain_link=decision.direct_link,
        exact_attestation_match=(
            earlier.attestation_bytes == later.attestation_bytes
        ),
        exact_document_match=earlier.document_bytes == later.document_bytes,
        first=earlier.verified,
        relation=decision.relation,
        second=later.verified,
        sequence_gap=decision.sequence_gap,
    )


def _lineage_relation(
    first: TicketAdmissionTelemetryVerifiedLineage,
    second: TicketAdmissionTelemetryVerifiedLineage,
) -> _RelationDecision:
    identity_decision = _different_identity_relation(first, second)
    if identity_decision is not None:
        return identity_decision
    return _same_lineage_relation(first, second)


def _different_identity_relation(
    first: TicketAdmissionTelemetryVerifiedLineage,
    second: TicketAdmissionTelemetryVerifiedLineage,
) -> _RelationDecision | None:
    if first.recorder_id != second.recorder_id:
        return _RelationDecision(
            common_lineage=False,
            direct_link=False,
            relation=TicketAdmissionTelemetryLineageRelation.DIFFERENT_RECORDER,
            sequence_gap=None,
        )
    if (
        first.completed_stream_id != second.completed_stream_id
        or first.failed_stream_id != second.failed_stream_id
    ):
        return _RelationDecision(
            common_lineage=False,
            direct_link=False,
            relation=TicketAdmissionTelemetryLineageRelation.DIFFERENT_STREAMS,
            sequence_gap=None,
        )
    return None


def _same_lineage_relation(
    first: TicketAdmissionTelemetryVerifiedLineage,
    second: TicketAdmissionTelemetryVerifiedLineage,
) -> _RelationDecision:
    sequence_gap = second.capture_sequence_id - first.capture_sequence_id
    if sequence_gap == 0:
        return _same_capture_relation(first, second)
    if sequence_gap == 1:
        return _direct_successor_relation(first, second)
    return _ordered_gap_relation(first, second, sequence_gap=sequence_gap)


def _same_capture_relation(
    first: TicketAdmissionTelemetryVerifiedLineage,
    second: TicketAdmissionTelemetryVerifiedLineage,
) -> _RelationDecision:
    if first.attestation_fingerprint != second.attestation_fingerprint:
        _raise_lineage("authenticated capture sequence fork detected")
    return _RelationDecision(
        common_lineage=True,
        direct_link=False,
        relation=TicketAdmissionTelemetryLineageRelation.SAME_CAPTURE,
        sequence_gap=0,
    )


def _direct_successor_relation(
    first: TicketAdmissionTelemetryVerifiedLineage,
    second: TicketAdmissionTelemetryVerifiedLineage,
) -> _RelationDecision:
    _validate_direct_predecessor(first, second)
    return _RelationDecision(
        common_lineage=True,
        direct_link=True,
        relation=TicketAdmissionTelemetryLineageRelation.DIRECT_SUCCESSOR,
        sequence_gap=1,
    )


def _ordered_gap_relation(
    first: TicketAdmissionTelemetryVerifiedLineage,
    second: TicketAdmissionTelemetryVerifiedLineage,
    *,
    sequence_gap: int,
) -> _RelationDecision:
    if second.previous_attestation_fingerprint == first.attestation_fingerprint:
        _raise_lineage("predecessor link requires adjacent capture sequence")
    return _RelationDecision(
        common_lineage=True,
        direct_link=False,
        relation=TicketAdmissionTelemetryLineageRelation.ORDERED_GAP,
        sequence_gap=sequence_gap,
    )


def _validate_direct_predecessor(
    first: TicketAdmissionTelemetryVerifiedLineage,
    second: TicketAdmissionTelemetryVerifiedLineage,
) -> None:
    if second.previous_attestation_fingerprint != first.attestation_fingerprint:
        _raise_lineage("adjacent capture predecessor does not match")


def _validated_claim(
    claim: TicketAdmissionTelemetryLineageClaim,
) -> TicketAdmissionTelemetryLineageClaim:
    if type(claim) is not TicketAdmissionTelemetryLineageClaim:
        _raise_lineage("claim must use the exact lineage claim type")
    sequence_id = _validated_capture_sequence_id(claim.capture_sequence_id)
    _ = _validated_identifier(
        claim.completed_stream_id,
        "completed stream identity",
    )
    _ = _validated_identifier(claim.failed_stream_id, "failed stream identity")
    _ = _validated_identifier(claim.key_id, "key identity")
    _ = _validated_identifier(claim.recorder_id, "recorder identity")
    _ = _validated_previous_fingerprint(
        claim.previous_attestation_fingerprint,
        capture_sequence_id=sequence_id,
    )
    return claim


def _validated_attestation(
    attestation: TicketAdmissionTelemetryLineageAttestation,
) -> TicketAdmissionTelemetryLineageAttestation:
    if type(attestation) is not TicketAdmissionTelemetryLineageAttestation:
        _raise_lineage("attestation must use the exact lineage type")
    _validate_attestation_header(attestation)
    _ = _validated_claim(_claim_from_attestation(attestation))
    _validate_attestation_hashes(attestation)
    return attestation


def _validate_attestation_header(
    attestation: TicketAdmissionTelemetryLineageAttestation,
) -> None:
    if (
        type(attestation.schema_version) is not int
        or attestation.schema_version
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_SCHEMA_VERSION
    ):
        _raise_lineage("attestation schema is unsupported")
    if attestation.attestation_id != TICKET_ADMISSION_TELEMETRY_LINEAGE_ID:
        _raise_lineage("attestation identity is unsupported")
    if (
        attestation.algorithm_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_ALGORITHM_ID
    ):
        _raise_lineage("attestation algorithm is unsupported")


def _claim_from_attestation(
    attestation: TicketAdmissionTelemetryLineageAttestation,
) -> TicketAdmissionTelemetryLineageClaim:
    return TicketAdmissionTelemetryLineageClaim(
        capture_sequence_id=attestation.capture_sequence_id,
        completed_stream_id=attestation.completed_stream_id,
        failed_stream_id=attestation.failed_stream_id,
        key_id=attestation.key_id,
        previous_attestation_fingerprint=(
            attestation.previous_attestation_fingerprint
        ),
        recorder_id=attestation.recorder_id,
    )


def _validate_attestation_hashes(
    attestation: TicketAdmissionTelemetryLineageAttestation,
) -> None:
    if (
        type(attestation.document_fingerprint) is not str
        or _DOCUMENT_FINGERPRINT_PATTERN.fullmatch(
            attestation.document_fingerprint
        )
        is None
    ):
        _raise_lineage("document fingerprint must use canonical SHA-256 form")
    if (
        type(attestation.mac_hex) is not str
        or _MAC_PATTERN.fullmatch(attestation.mac_hex) is None
    ):
        _raise_lineage("attestation MAC must use lowercase SHA-256 hexadecimal")


def _validated_capture_sequence_id(value: int) -> int:
    if type(value) is not int or value < 0:
        _raise_lineage(
            "capture sequence identity must be a nonnegative integer"
        )
    return value


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_lineage(f"{field_name} must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_lineage(f"{field_name} exceeds configured length")
    return value


def _validated_previous_fingerprint(
    value: str | None,
    *,
    capture_sequence_id: int,
) -> str | None:
    if value is None:
        return None
    if type(value) is not str or _FINGERPRINT_PATTERN.fullmatch(value) is None:
        _raise_lineage("previous attestation fingerprint is malformed")
    if capture_sequence_id == 0:
        _raise_lineage("genesis capture cannot name a predecessor")
    return value


def _validated_secret_key(secret_key: bytes) -> bytes:
    if type(secret_key) is not bytes:
        _raise_lineage("secret key must use the exact bytes type")
    if len(secret_key) < MIN_TELEMETRY_LINEAGE_KEY_BYTES:
        _raise_lineage("secret key is shorter than the configured minimum")
    if len(secret_key) > MAX_TELEMETRY_LINEAGE_KEY_BYTES:
        _raise_lineage("secret key exceeds the configured maximum")
    return secret_key


def _validated_encoded_input(data: bytes, *, max_bytes: int) -> bytes:
    if type(data) is not bytes:
        _raise_lineage("encoded attestation must use the exact bytes type")
    if type(max_bytes) is not int or max_bytes <= 0:
        _raise_lineage("decode byte limit must be a positive integer")
    if not data:
        _raise_lineage("encoded attestation cannot be empty")
    if len(data) > max_bytes:
        _raise_lineage("encoded attestation exceeds configured byte limit")
    return data


def _decoded_mapping(data: bytes) -> dict[str, object]:
    parsed = _parsed_json(_decoded_text(data))
    if type(parsed) is not dict:
        _raise_lineage("encoded attestation root must be an object")
    mapping = cast("dict[str, object]", parsed)
    if tuple(sorted(mapping)) != _ATTESTATION_KEYS:
        _raise_lineage("encoded attestation keys are unsupported")
    return mapping


def _decoded_text(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        message = "ticket admission telemetry lineage must use UTF-8"
        raise TicketAdmissionTelemetryLineageError(message) from error


def _parsed_json(text: str) -> object:
    try:
        return cast(
            "object",
            loads(text, object_pairs_hook=_object_without_duplicates),
        )
    except _DuplicateKeyError as error:
        message = "ticket admission telemetry lineage contains duplicate keys"
        raise TicketAdmissionTelemetryLineageError(message) from error
    except JSONDecodeError as error:
        message = "ticket admission telemetry lineage is not valid JSON"
        raise TicketAdmissionTelemetryLineageError(message) from error


def _object_without_duplicates(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    mapping: dict[str, object] = {}
    for key, value in pairs:
        if key in mapping:
            raise _DuplicateKeyError(key)
        mapping[key] = value
    return mapping


def _required_str(mapping: dict[str, object], key: str) -> str:
    value = mapping[key]
    if type(value) is not str:
        _raise_lineage(f"encoded {key} must be a string")
    return value


def _optional_str(mapping: dict[str, object], key: str) -> str | None:
    value = mapping[key]
    if value is None:
        return None
    if type(value) is not str:
        _raise_lineage(f"encoded {key} must be a string or null")
    return value


def _required_int(mapping: dict[str, object], key: str) -> int:
    value = mapping[key]
    if type(value) is not int:
        _raise_lineage(f"encoded {key} must be an integer")
    return value


def _unsigned_payload_bytes(
    attestation: TicketAdmissionTelemetryLineageAttestation,
) -> bytes:
    mapping = _attestation_mapping(attestation)
    del mapping["mac_hex"]
    return _canonical_json_bytes(mapping)


def _attestation_mapping(
    attestation: TicketAdmissionTelemetryLineageAttestation,
) -> dict[str, object]:
    return {
        "algorithm_id": attestation.algorithm_id,
        "attestation_id": attestation.attestation_id,
        "capture_sequence_id": attestation.capture_sequence_id,
        "completed_stream_id": attestation.completed_stream_id,
        "document_fingerprint": attestation.document_fingerprint,
        "failed_stream_id": attestation.failed_stream_id,
        "key_id": attestation.key_id,
        "mac_hex": attestation.mac_hex,
        "previous_attestation_fingerprint": (
            attestation.previous_attestation_fingerprint
        ),
        "recorder_id": attestation.recorder_id,
        "schema_version": attestation.schema_version,
    }


def _canonical_json_bytes(mapping: dict[str, object]) -> bytes:
    return dumps(
        mapping,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _mac_hex(secret_key: bytes, payload: bytes) -> str:
    return hmac_digest(secret_key, payload, "sha256").hex()


def _attestation_fingerprint(canonical_bytes: bytes) -> str:
    digest = sha256(canonical_bytes).hexdigest()
    return (
        f"{TICKET_ADMISSION_TELEMETRY_LINEAGE_FINGERPRINT_PREFIX}{digest}"
    )


def _document_fingerprint(
    document: TicketAdmissionTelemetryDocument,
) -> str:
    try:
        return ticket_admission_telemetry_document_fingerprint(document)
    except TicketAdmissionTelemetryCollectionError as error:
        message = f"invalid telemetry document identity: {error}"
        raise TicketAdmissionTelemetryLineageError(message) from error


def _document_bytes(document: TicketAdmissionTelemetryDocument) -> bytes:
    try:
        return encode_ticket_admission_telemetry_document(document)
    except TicketAdmissionTelemetryPersistenceError as error:
        message = f"invalid telemetry document: {error}"
        raise TicketAdmissionTelemetryLineageError(message) from error


def _validated_item(
    item: TicketAdmissionTelemetryLineageItem,
) -> TicketAdmissionTelemetryLineageItem:
    if type(item) is not TicketAdmissionTelemetryLineageItem:
        _raise_lineage("comparison item must use the exact lineage item type")
    return item


def _validated_verified_item(
    item: TicketAdmissionTelemetryVerifiedLineageItem,
) -> TicketAdmissionTelemetryVerifiedLineageItem:
    if type(item) is not TicketAdmissionTelemetryVerifiedLineageItem:
        _raise_lineage("verified item must use the exact lineage material type")
    if type(item.attestation_bytes) is not bytes:
        _raise_lineage("verified attestation material must use exact bytes")
    if type(item.document_bytes) is not bytes:
        _raise_lineage("verified document material must use exact bytes")
    if type(item.verified) is not TicketAdmissionTelemetryVerifiedLineage:
        _raise_lineage("verified claim must use the exact lineage type")
    return item


def _material_identity(
    material: TicketAdmissionTelemetryVerifiedLineageItem,
) -> tuple[str, str, str, int, str]:
    verified = material.verified
    return (
        verified.recorder_id,
        verified.completed_stream_id,
        verified.failed_stream_id,
        verified.capture_sequence_id,
        verified.attestation_fingerprint,
    )


def _reject_fingerprint_collisions(
    first: TicketAdmissionTelemetryVerifiedLineageItem,
    second: TicketAdmissionTelemetryVerifiedLineageItem,
) -> None:
    if (
        first.verified.attestation_fingerprint
        == second.verified.attestation_fingerprint
        and first.attestation_bytes != second.attestation_bytes
    ):
        _raise_lineage("attestation fingerprint collision detected")
    if (
        first.verified.document_fingerprint
        == second.verified.document_fingerprint
        and first.document_bytes != second.document_bytes
    ):
        _raise_lineage("document fingerprint collision detected")


def _raise_lineage(detail: str) -> Never:
    message = f"ticket admission telemetry lineage {detail}"
    raise TicketAdmissionTelemetryLineageError(message)
