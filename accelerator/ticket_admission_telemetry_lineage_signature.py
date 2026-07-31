# File:
#   - ticket_admission_telemetry_lineage_signature.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_signature.py
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
#   - Detached public-key lineage signature and verification ports.
# - Must-Not:
#   - Implement algorithms, store private keys, discover trust, retry, cache,
#     spawn workers, merge snapshots, or change policy.
# - Allows:
#   - Inputs: exact schema-v1 documents, claims, public keys, and caller ports.
#   - Outputs: canonical detached attestations and verified lineage material.
#   - Side effects: exactly one signer or verifier call per explicit operation.
# - Split-When:
#   - Split when external trust manifests, concrete algorithms, or PKI gain
#     contracts.
# - Merge-When:
#   - Merge when another module owns this exact detached-signature boundary.
# - Summary:
#   - Caller-supplied public-key telemetry lineage signatures.
# - Description:
#   - Binds exact public-key bytes and signatures without choosing cryptography.
# - Usage:
#   - Sign through one explicit port, persist canonically, then verify
#     explicitly.
# - Defaults:
#   - 64 KiB attestations/public keys and 16 KiB detached signatures.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust.py
# - accelerator/ticket_admission_telemetry_persistence.py
# - accelerator/ticket_admission_telemetry_migration.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Detached caller-supplied public-key signatures for telemetry lineage."""

from __future__ import annotations

from base64 import b64decode
from base64 import b64encode
from binascii import Error as Base64Error
from dataclasses import dataclass
from dataclasses import field
from dataclasses import replace
from enum import StrEnum
from hashlib import sha256
from json import JSONDecodeError
from json import dumps
from json import loads
from re import compile as compile_pattern
from typing import Final
from typing import Never
from typing import Protocol
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry_lineage import (
        TicketAdmissionTelemetryLineageComparison,
    )
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

from accelerator.ticket_admission_telemetry_collection import (
    TicketAdmissionTelemetryCollectionError,
)
from accelerator.ticket_admission_telemetry_collection import (
    ticket_admission_telemetry_document_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)
from accelerator.ticket_admission_telemetry_lineage import (
    TICKET_ADMISSION_TELEMETRY_LINEAGE_FINGERPRINT_PREFIX,
)
from accelerator.ticket_admission_telemetry_lineage import (
    TicketAdmissionTelemetryLineageError,
)
from accelerator.ticket_admission_telemetry_lineage import (
    TicketAdmissionTelemetryVerifiedLineage,
)
from accelerator.ticket_admission_telemetry_lineage import (
    TicketAdmissionTelemetryVerifiedLineageItem,
)
from accelerator.ticket_admission_telemetry_lineage import (
    compare_verified_ticket_admission_telemetry_lineage,
)
from accelerator.ticket_admission_telemetry_persistence import (
    TicketAdmissionTelemetryPersistenceError,
)
from accelerator.ticket_admission_telemetry_persistence import (
    encode_ticket_admission_telemetry_document,
)

TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_SCHEMA_VERSION: Final = 1
TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_ID: Final = (
    "caller-owned-ticket-admission-telemetry-lineage-signature-v1"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_ENCODING_ID: Final = (
    "base64-standard-canonical-v1"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_FINGERPRINT_PREFIX: Final = (
    "ticket-admission-telemetry-lineage-signature-v1:sha256:"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_FINGERPRINT_PREFIX: Final = (
    "ticket-admission-telemetry-lineage-public-key-v1:sha256:"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_BYTES: Final = 16 * 1024
DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_ATTESTATION_BYTES: Final = 64 * 1024
DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BYTES: Final = 64 * 1024

_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_DOCUMENT_FINGERPRINT_PATTERN: Final = compile_pattern(
    r"ticket-admission-telemetry-document-v1:sha256:[0-9a-f]{64}"
)
_PUBLIC_KEY_FINGERPRINT_PATTERN: Final = compile_pattern(
    r"ticket-admission-telemetry-lineage-public-key-v1:sha256:[0-9a-f]{64}"
)
_HMAC_ATTESTATION_FINGERPRINT_PATTERN: Final = compile_pattern(
    rf"{TICKET_ADMISSION_TELEMETRY_LINEAGE_FINGERPRINT_PREFIX}[0-9a-f]{{64}}"
)
_SIGNATURE_ATTESTATION_FINGERPRINT_PATTERN: Final = compile_pattern(
    TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_FINGERPRINT_PREFIX
    + r"[0-9a-f]{64}"
)
_ATTESTATION_KEYS: Final = (
    "algorithm_id",
    "attestation_id",
    "capture_sequence_id",
    "completed_stream_id",
    "document_fingerprint",
    "failed_stream_id",
    "previous_attestation_fingerprint",
    "public_key_fingerprint",
    "public_key_id",
    "recorder_id",
    "schema_version",
    "signature_base64",
    "signature_encoding_id",
)


class TicketAdmissionTelemetryLineageSignatureError(ValueError):
    """A detached lineage signature request or attestation is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageSignatureClaim:
    """Caller-supplied recorder, public-key, and capture signature claims."""

    algorithm_id: str
    capture_sequence_id: int
    completed_stream_id: str
    failed_stream_id: str
    previous_attestation_fingerprint: str | None
    public_key_fingerprint: str
    public_key_id: str
    recorder_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageSignatureAttestation:
    """Canonical detached signature binding one exact telemetry document."""

    algorithm_id: str
    attestation_id: str
    capture_sequence_id: int
    completed_stream_id: str
    document_fingerprint: str
    failed_stream_id: str
    previous_attestation_fingerprint: str | None
    public_key_fingerprint: str
    public_key_id: str
    recorder_id: str
    schema_version: int
    signature_base64: str
    signature_encoding_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageSignatureItem:
    """One exact document paired with its detached signature attestation."""

    attestation: TicketAdmissionTelemetryLineageSignatureAttestation
    document: TicketAdmissionTelemetryDocument


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageSignatureRequest:
    """One immutable caller-supplied signer request."""

    algorithm_id: str
    payload: bytes = field(repr=False)
    public_key_fingerprint: str
    public_key_id: str


class TicketAdmissionTelemetryLineageSignerResultKind(StrEnum):
    """Stable signer outcome without private-key or vendor text."""

    SIGNED = "signed"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageSignerResult:
    """Typed signer outcome with hidden optional detached signature bytes."""

    kind: TicketAdmissionTelemetryLineageSignerResultKind
    signature: bytes | None = field(default=None, repr=False)


class TicketAdmissionTelemetryLineageSigner(Protocol):
    """Synchronous caller-supplied signer without a lifecycle contract."""

    def __call__(
        self,
        request: TicketAdmissionTelemetryLineageSignatureRequest,
    ) -> TicketAdmissionTelemetryLineageSignerResult:
        """Return one typed result for exact canonical signing bytes."""
        ...


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageVerificationRequest:
    """One immutable caller-supplied public-key verification request."""

    algorithm_id: str
    payload: bytes = field(repr=False)
    public_key: bytes = field(repr=False)
    public_key_fingerprint: str
    public_key_id: str
    signature: bytes = field(repr=False)


class TicketAdmissionTelemetryLineageVerifierResultKind(StrEnum):
    """Stable verifier outcome without algorithm or vendor text."""

    VERIFIED = "verified"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageVerifierResult:
    """Typed public-key verification outcome."""

    kind: TicketAdmissionTelemetryLineageVerifierResultKind


class TicketAdmissionTelemetryLineageVerifier(Protocol):
    """Synchronous caller-supplied verifier without trust discovery."""

    def __call__(
        self,
        request: TicketAdmissionTelemetryLineageVerificationRequest,
    ) -> TicketAdmissionTelemetryLineageVerifierResult:
        """Return one typed result for exact signature and public-key bytes."""
        ...


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageSignatureVerificationItem:
    """One signature item paired with exact caller-supplied public-key bytes."""

    item: TicketAdmissionTelemetryLineageSignatureItem
    public_key: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryVerifiedSignatureLineage:
    """Verified lineage material plus exact public-key signature metadata."""

    algorithm_id: str
    public_key_fingerprint: str
    public_key_id: str
    signature_byte_count: int
    verified_item: TicketAdmissionTelemetryVerifiedLineageItem


class _DuplicateKeyError(ValueError):
    """A decoded signature attestation contains a duplicate JSON key."""


def ticket_admission_telemetry_lineage_signature_id() -> str:
    """Return the stable detached public-key signature identity.

    Returns:
        Versioned signature-port identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_ID


def ticket_admission_telemetry_lineage_public_key_fingerprint(
    public_key: bytes,
) -> str:
    """Return SHA-256 identity over exact caller-owned public-key bytes.

    Returns:
        Versioned exact public-key fingerprint.

    """
    validated = _validated_public_key(public_key)
    digest = sha256(validated).hexdigest()
    return (
        f"{TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_FINGERPRINT_PREFIX}"
        f"{digest}"
    )


def create_ticket_admission_telemetry_lineage_signature_attestation(
    document: TicketAdmissionTelemetryDocument,
    claim: TicketAdmissionTelemetryLineageSignatureClaim,
    signer: TicketAdmissionTelemetryLineageSigner,
) -> TicketAdmissionTelemetryLineageSignatureAttestation:
    """Create one detached signature through an explicit caller-supplied port.

    Returns:
        Canonical immutable attestation containing no private-key material.

    """
    validated_claim = _validated_claim(claim)
    attestation = TicketAdmissionTelemetryLineageSignatureAttestation(
        algorithm_id=validated_claim.algorithm_id,
        attestation_id=TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_ID,
        capture_sequence_id=validated_claim.capture_sequence_id,
        completed_stream_id=validated_claim.completed_stream_id,
        document_fingerprint=_document_fingerprint(document),
        failed_stream_id=validated_claim.failed_stream_id,
        previous_attestation_fingerprint=(
            validated_claim.previous_attestation_fingerprint
        ),
        public_key_fingerprint=validated_claim.public_key_fingerprint,
        public_key_id=validated_claim.public_key_id,
        recorder_id=validated_claim.recorder_id,
        schema_version=TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_SCHEMA_VERSION,
        signature_base64="AA==",
        signature_encoding_id=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_ENCODING_ID
        ),
    )
    request = TicketAdmissionTelemetryLineageSignatureRequest(
        algorithm_id=attestation.algorithm_id,
        payload=_unsigned_payload_bytes(attestation),
        public_key_fingerprint=attestation.public_key_fingerprint,
        public_key_id=attestation.public_key_id,
    )
    signature = _signed_bytes(signer(request))
    return _validated_attestation(
        replace(
            attestation,
            signature_base64=b64encode(signature).decode("ascii"),
        )
    )


def encode_ticket_admission_telemetry_lineage_signature_attestation(
    attestation: TicketAdmissionTelemetryLineageSignatureAttestation,
) -> bytes:
    """Encode one structurally valid signature attestation as canonical JSON.

    Returns:
        Compact sorted-key UTF-8 JSON bytes.

    """
    validated = _validated_attestation(attestation)
    return _canonical_json_bytes(_attestation_mapping(validated))


def decode_ticket_admission_telemetry_lineage_signature_attestation(
    data: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_ATTESTATION_BYTES,
) -> TicketAdmissionTelemetryLineageSignatureAttestation:
    """Decode one canonical bounded detached signature attestation.

    Returns:
        Structurally validated attestation; verification remains explicit.

    """
    canonical_input = _validated_encoded_input(data, max_bytes=max_bytes)
    mapping = _decoded_mapping(canonical_input)
    attestation = TicketAdmissionTelemetryLineageSignatureAttestation(
        algorithm_id=_required_str(mapping, "algorithm_id"),
        attestation_id=_required_str(mapping, "attestation_id"),
        capture_sequence_id=_required_int(mapping, "capture_sequence_id"),
        completed_stream_id=_required_str(mapping, "completed_stream_id"),
        document_fingerprint=_required_str(mapping, "document_fingerprint"),
        failed_stream_id=_required_str(mapping, "failed_stream_id"),
        previous_attestation_fingerprint=_optional_str(
            mapping,
            "previous_attestation_fingerprint",
        ),
        public_key_fingerprint=_required_str(
            mapping,
            "public_key_fingerprint",
        ),
        public_key_id=_required_str(mapping, "public_key_id"),
        recorder_id=_required_str(mapping, "recorder_id"),
        schema_version=_required_int(mapping, "schema_version"),
        signature_base64=_required_str(mapping, "signature_base64"),
        signature_encoding_id=_required_str(
            mapping,
            "signature_encoding_id",
        ),
    )
    validated = _validated_attestation(attestation)
    encoded = encode_ticket_admission_telemetry_lineage_signature_attestation(
        validated
    )
    if encoded != data:
        _raise_signature("encoded attestation must use canonical JSON")
    return validated


def ticket_admission_telemetry_lineage_signature_attestation_fingerprint(
    attestation: TicketAdmissionTelemetryLineageSignatureAttestation,
) -> str:
    """Return the SHA-256 identity of canonical detached attestation bytes.

    Returns:
        Versioned detached signature attestation fingerprint.

    """
    canonical_bytes = (
        encode_ticket_admission_telemetry_lineage_signature_attestation(
            attestation
        )
    )
    return _attestation_fingerprint(canonical_bytes)


def verify_ticket_admission_telemetry_lineage_signature_item(
    item: TicketAdmissionTelemetryLineageSignatureItem,
    verifier: TicketAdmissionTelemetryLineageVerifier,
    *,
    public_key: bytes,
) -> TicketAdmissionTelemetryVerifiedSignatureLineage:
    """Verify one signature under exact caller-supplied public-key bytes.

    Returns:
        Public-key metadata and canonical independently comparable lineage.

    """
    validated_item = _validated_item(item)
    key = _validated_public_key(public_key)
    attestation = _validated_attestation(validated_item.attestation)
    key_fingerprint = (
        ticket_admission_telemetry_lineage_public_key_fingerprint(key)
    )
    if attestation.public_key_fingerprint != key_fingerprint:
        _raise_signature("attestation public-key fingerprint does not match")
    document_fingerprint = _document_fingerprint(validated_item.document)
    if attestation.document_fingerprint != document_fingerprint:
        _raise_signature("attestation document fingerprint does not match")
    signature = _signature_bytes(attestation.signature_base64)
    request = TicketAdmissionTelemetryLineageVerificationRequest(
        algorithm_id=attestation.algorithm_id,
        payload=_unsigned_payload_bytes(attestation),
        public_key=key,
        public_key_fingerprint=attestation.public_key_fingerprint,
        public_key_id=attestation.public_key_id,
        signature=signature,
    )
    _require_verified(verifier(request))
    attestation_bytes = (
        encode_ticket_admission_telemetry_lineage_signature_attestation(
            attestation
        )
    )
    verified_item = TicketAdmissionTelemetryVerifiedLineageItem(
        attestation_bytes=attestation_bytes,
        document_bytes=_document_bytes(validated_item.document),
        verified=TicketAdmissionTelemetryVerifiedLineage(
            attestation_fingerprint=_attestation_fingerprint(
                attestation_bytes
            ),
            canonical_byte_count=len(attestation_bytes),
            capture_sequence_id=attestation.capture_sequence_id,
            completed_stream_id=attestation.completed_stream_id,
            document_fingerprint=attestation.document_fingerprint,
            failed_stream_id=attestation.failed_stream_id,
            key_id=attestation.public_key_id,
            previous_attestation_fingerprint=(
                attestation.previous_attestation_fingerprint
            ),
            recorder_id=attestation.recorder_id,
        ),
    )
    return TicketAdmissionTelemetryVerifiedSignatureLineage(
        algorithm_id=attestation.algorithm_id,
        public_key_fingerprint=attestation.public_key_fingerprint,
        public_key_id=attestation.public_key_id,
        signature_byte_count=len(signature),
        verified_item=verified_item,
    )


def compare_ticket_admission_telemetry_lineage_signatures(
    first: TicketAdmissionTelemetryLineageSignatureVerificationItem,
    second: TicketAdmissionTelemetryLineageSignatureVerificationItem,
    verifier: TicketAdmissionTelemetryLineageVerifier,
) -> TicketAdmissionTelemetryLineageComparison:
    """Compare two items after independent exact public-key verification.

    Returns:
        Canonically ordered recorder, stream, capture, and chain relation.

    Raises:
        TicketAdmissionTelemetryLineageSignatureError: Verification or
            comparison fails.

    """
    first_input = _validated_verification_item(first)
    second_input = _validated_verification_item(second)
    first_verified = verify_ticket_admission_telemetry_lineage_signature_item(
        first_input.item,
        verifier,
        public_key=first_input.public_key,
    )
    second_verified = verify_ticket_admission_telemetry_lineage_signature_item(
        second_input.item,
        verifier,
        public_key=second_input.public_key,
    )
    try:
        return compare_verified_ticket_admission_telemetry_lineage(
            first_verified.verified_item,
            second_verified.verified_item,
        )
    except TicketAdmissionTelemetryLineageError as error:
        message = f"invalid verified signature comparison: {error}"
        raise TicketAdmissionTelemetryLineageSignatureError(message) from error


def _validated_claim(
    claim: TicketAdmissionTelemetryLineageSignatureClaim,
) -> TicketAdmissionTelemetryLineageSignatureClaim:
    if type(claim) is not TicketAdmissionTelemetryLineageSignatureClaim:
        _raise_signature("claim must use the exact signature claim type")
    _ = _validated_identifier(claim.algorithm_id, "algorithm identity")
    sequence_id = _validated_capture_sequence_id(claim.capture_sequence_id)
    _ = _validated_identifier(
        claim.completed_stream_id,
        "completed stream identity",
    )
    _ = _validated_identifier(claim.failed_stream_id, "failed stream identity")
    _ = _validated_identifier(claim.public_key_id, "public-key identity")
    _ = _validated_identifier(claim.recorder_id, "recorder identity")
    _ = _validated_public_key_fingerprint(claim.public_key_fingerprint)
    _ = _validated_previous_fingerprint(
        claim.previous_attestation_fingerprint,
        capture_sequence_id=sequence_id,
    )
    return claim


def _validated_attestation(
    attestation: TicketAdmissionTelemetryLineageSignatureAttestation,
) -> TicketAdmissionTelemetryLineageSignatureAttestation:
    if (
        type(attestation)
        is not TicketAdmissionTelemetryLineageSignatureAttestation
    ):
        _raise_signature("attestation must use the exact signature type")
    _validate_attestation_header(attestation)
    _ = _validated_claim(_claim_from_attestation(attestation))
    _validate_document_fingerprint(attestation.document_fingerprint)
    _ = _signature_bytes(attestation.signature_base64)
    return attestation


def _validate_attestation_header(
    attestation: TicketAdmissionTelemetryLineageSignatureAttestation,
) -> None:
    if (
        type(attestation.schema_version) is not int
        or attestation.schema_version
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_SCHEMA_VERSION
    ):
        _raise_signature("attestation schema is unsupported")
    if (
        attestation.attestation_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_ID
    ):
        _raise_signature("attestation identity is unsupported")
    if (
        attestation.signature_encoding_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_ENCODING_ID
    ):
        _raise_signature("attestation signature encoding is unsupported")


def _claim_from_attestation(
    attestation: TicketAdmissionTelemetryLineageSignatureAttestation,
) -> TicketAdmissionTelemetryLineageSignatureClaim:
    return TicketAdmissionTelemetryLineageSignatureClaim(
        algorithm_id=attestation.algorithm_id,
        capture_sequence_id=attestation.capture_sequence_id,
        completed_stream_id=attestation.completed_stream_id,
        failed_stream_id=attestation.failed_stream_id,
        previous_attestation_fingerprint=(
            attestation.previous_attestation_fingerprint
        ),
        public_key_fingerprint=attestation.public_key_fingerprint,
        public_key_id=attestation.public_key_id,
        recorder_id=attestation.recorder_id,
    )


def _signed_bytes(
    result: TicketAdmissionTelemetryLineageSignerResult,
) -> bytes:
    validated = _validated_signer_result(result)
    if (
        validated.kind
        is not TicketAdmissionTelemetryLineageSignerResultKind.SIGNED
    ):
        _raise_signature(f"signer returned {validated.kind.value}")
    if type(validated.signature) is not bytes:
        _raise_signature("signed result must contain exact signature bytes")
    return _validated_signature_bytes(validated.signature)


def _validated_signer_result(
    result: TicketAdmissionTelemetryLineageSignerResult,
) -> TicketAdmissionTelemetryLineageSignerResult:
    if type(result) is not TicketAdmissionTelemetryLineageSignerResult:
        _raise_signature("signer result must use the exact result type")
    if type(result.kind) is not TicketAdmissionTelemetryLineageSignerResultKind:
        _raise_signature("signer result kind must use the exact enum")
    if (
        result.kind
        is not TicketAdmissionTelemetryLineageSignerResultKind.SIGNED
        and result.signature is not None
    ):
        _raise_signature("nonsigned result cannot contain signature bytes")
    return result


def _require_verified(
    result: TicketAdmissionTelemetryLineageVerifierResult,
) -> None:
    validated = _validated_verifier_result(result)
    if (
        validated.kind
        is not TicketAdmissionTelemetryLineageVerifierResultKind.VERIFIED
    ):
        _raise_signature(f"verifier returned {validated.kind.value}")


def _validated_verifier_result(
    result: TicketAdmissionTelemetryLineageVerifierResult,
) -> TicketAdmissionTelemetryLineageVerifierResult:
    if type(result) is not TicketAdmissionTelemetryLineageVerifierResult:
        _raise_signature("verifier result must use the exact result type")
    if (
        type(result.kind)
        is not TicketAdmissionTelemetryLineageVerifierResultKind
    ):
        _raise_signature("verifier result kind must use the exact enum")
    return result


def _validated_capture_sequence_id(value: int) -> int:
    if type(value) is not int or value < 0:
        _raise_signature(
            "capture sequence identity must be a nonnegative integer"
        )
    return value


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_signature(
            f"{field_name} must use canonical ASCII identity form"
        )
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_signature(f"{field_name} exceeds configured length")
    return value


def _validated_public_key(public_key: bytes) -> bytes:
    if type(public_key) is not bytes:
        _raise_signature("public key must use the exact bytes type")
    if not public_key:
        _raise_signature("public key cannot be empty")
    if len(public_key) > DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BYTES:
        _raise_signature("public key exceeds configured byte limit")
    return public_key


def _validated_public_key_fingerprint(value: str) -> str:
    if (
        type(value) is not str
        or _PUBLIC_KEY_FINGERPRINT_PATTERN.fullmatch(value) is None
    ):
        _raise_signature("public-key fingerprint is malformed")
    return value


def _validated_previous_fingerprint(
    value: str | None,
    *,
    capture_sequence_id: int,
) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        _raise_signature("previous attestation fingerprint is malformed")
    if (
        _HMAC_ATTESTATION_FINGERPRINT_PATTERN.fullmatch(value) is None
        and _SIGNATURE_ATTESTATION_FINGERPRINT_PATTERN.fullmatch(value) is None
    ):
        _raise_signature("previous attestation fingerprint is malformed")
    if capture_sequence_id == 0:
        _raise_signature("genesis capture cannot name a predecessor")
    return value


def _validate_document_fingerprint(value: str) -> None:
    if (
        type(value) is not str
        or _DOCUMENT_FINGERPRINT_PATTERN.fullmatch(value) is None
    ):
        _raise_signature("document fingerprint must use canonical SHA-256 form")


def _validated_signature_bytes(signature: bytes) -> bytes:
    if type(signature) is not bytes:
        _raise_signature("signature must use the exact bytes type")
    if not signature:
        _raise_signature("signature cannot be empty")
    if len(signature) > DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_BYTES:
        _raise_signature("signature exceeds configured byte limit")
    return signature


def _signature_bytes(signature_base64: str) -> bytes:
    if type(signature_base64) is not str or not signature_base64:
        _raise_signature("signature payload must be a non-empty string")
    try:
        signature = b64decode(signature_base64, validate=True)
    except (Base64Error, ValueError) as error:
        message = "ticket admission telemetry lineage signature is not Base64"
        raise TicketAdmissionTelemetryLineageSignatureError(message) from error
    validated = _validated_signature_bytes(signature)
    canonical = b64encode(validated).decode("ascii")
    if canonical != signature_base64:
        _raise_signature("signature payload must use canonical Base64")
    return validated


def _validated_encoded_input(data: bytes, *, max_bytes: int) -> bytes:
    if type(data) is not bytes:
        _raise_signature("encoded attestation must use the exact bytes type")
    if type(max_bytes) is not int or max_bytes <= 0:
        _raise_signature("decode byte limit must be a positive integer")
    if not data:
        _raise_signature("encoded attestation cannot be empty")
    if len(data) > max_bytes:
        _raise_signature("encoded attestation exceeds configured byte limit")
    return data


def _decoded_mapping(data: bytes) -> dict[str, object]:
    parsed = _parsed_json(_decoded_text(data))
    if type(parsed) is not dict:
        _raise_signature("encoded attestation root must be an object")
    mapping = cast("dict[str, object]", parsed)
    if tuple(sorted(mapping)) != _ATTESTATION_KEYS:
        _raise_signature("encoded attestation keys are unsupported")
    return mapping


def _decoded_text(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        message = "ticket admission telemetry lineage signature must use UTF-8"
        raise TicketAdmissionTelemetryLineageSignatureError(message) from error


def _parsed_json(text: str) -> object:
    try:
        return cast(
            "object",
            loads(text, object_pairs_hook=_object_without_duplicates),
        )
    except _DuplicateKeyError as error:
        message = (
            "ticket admission telemetry lineage signature contains duplicate "
            "keys"
        )
        raise TicketAdmissionTelemetryLineageSignatureError(message) from error
    except JSONDecodeError as error:
        message = (
            "ticket admission telemetry lineage signature is not valid JSON"
        )
        raise TicketAdmissionTelemetryLineageSignatureError(message) from error


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
        _raise_signature(f"encoded {key} must be a string")
    return value


def _optional_str(mapping: dict[str, object], key: str) -> str | None:
    value = mapping[key]
    if value is None:
        return None
    if type(value) is not str:
        _raise_signature(f"encoded {key} must be a string or null")
    return value


def _required_int(mapping: dict[str, object], key: str) -> int:
    value = mapping[key]
    if type(value) is not int:
        _raise_signature(f"encoded {key} must be an integer")
    return value


def _unsigned_payload_bytes(
    attestation: TicketAdmissionTelemetryLineageSignatureAttestation,
) -> bytes:
    mapping = _attestation_mapping(attestation)
    del mapping["signature_base64"]
    return _canonical_json_bytes(mapping)


def _attestation_mapping(
    attestation: TicketAdmissionTelemetryLineageSignatureAttestation,
) -> dict[str, object]:
    return {
        "algorithm_id": attestation.algorithm_id,
        "attestation_id": attestation.attestation_id,
        "capture_sequence_id": attestation.capture_sequence_id,
        "completed_stream_id": attestation.completed_stream_id,
        "document_fingerprint": attestation.document_fingerprint,
        "failed_stream_id": attestation.failed_stream_id,
        "previous_attestation_fingerprint": (
            attestation.previous_attestation_fingerprint
        ),
        "public_key_fingerprint": attestation.public_key_fingerprint,
        "public_key_id": attestation.public_key_id,
        "recorder_id": attestation.recorder_id,
        "schema_version": attestation.schema_version,
        "signature_base64": attestation.signature_base64,
        "signature_encoding_id": attestation.signature_encoding_id,
    }


def _canonical_json_bytes(mapping: dict[str, object]) -> bytes:
    return dumps(
        mapping,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _attestation_fingerprint(canonical_bytes: bytes) -> str:
    digest = sha256(canonical_bytes).hexdigest()
    return (
        f"{TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_FINGERPRINT_PREFIX}"
        f"{digest}"
    )


def _document_fingerprint(
    document: TicketAdmissionTelemetryDocument,
) -> str:
    try:
        return ticket_admission_telemetry_document_fingerprint(document)
    except TicketAdmissionTelemetryCollectionError as error:
        message = f"invalid telemetry document identity: {error}"
        raise TicketAdmissionTelemetryLineageSignatureError(message) from error


def _document_bytes(document: TicketAdmissionTelemetryDocument) -> bytes:
    try:
        return encode_ticket_admission_telemetry_document(document)
    except TicketAdmissionTelemetryPersistenceError as error:
        message = f"invalid telemetry document: {error}"
        raise TicketAdmissionTelemetryLineageSignatureError(message) from error


def _validated_item(
    item: TicketAdmissionTelemetryLineageSignatureItem,
) -> TicketAdmissionTelemetryLineageSignatureItem:
    if type(item) is not TicketAdmissionTelemetryLineageSignatureItem:
        _raise_signature("item must use the exact signature item type")
    return item


def _validated_verification_item(
    item: TicketAdmissionTelemetryLineageSignatureVerificationItem,
) -> TicketAdmissionTelemetryLineageSignatureVerificationItem:
    if (
        type(item)
        is not TicketAdmissionTelemetryLineageSignatureVerificationItem
    ):
        _raise_signature("verification item must use the exact input type")
    _ = _validated_item(item.item)
    _ = _validated_public_key(item.public_key)
    return item


def _raise_signature(detail: str) -> Never:
    message = f"ticket admission telemetry lineage signature {detail}"
    raise TicketAdmissionTelemetryLineageSignatureError(message)
