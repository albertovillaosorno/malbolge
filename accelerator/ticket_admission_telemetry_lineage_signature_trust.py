# File:
#   - ticket_admission_telemetry_lineage_signature_trust.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_signature_trust.py
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
#   - Bounded caller-owned public-key lineage trust and capture windows.
# - Must-Not:
#   - Load keys, select algorithms, discover trust, persist material, retry,
#     cache, merge snapshots, or change policy.
# - Allows:
#   - Inputs: explicit public keys, detached signature items, and one verifier.
#   - Outputs: immutable trust sets and independently verified comparisons.
#   - Side effects: verifier calls only after exact trust selection succeeds.
# - Split-When:
#   - Split when concrete network transports, certificates, or PKI
#     gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact public-key trust boundary.
# - Summary:
#   - Bounded in-memory detached lineage signature trust.
# - Description:
#   - Selects exact algorithms and public keys by inclusive capture windows.
# - Usage:
#   - Build explicitly, verify each item, then compare verified lineage.
# - Defaults:
#   - At most 256 unique algorithm/key pairs; empty trust trusts nothing.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage.py
# - accelerator/ticket_admission_telemetry_lineage_signature.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider_session.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_async_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_batch_provider.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_session.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_trust.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Bounded caller-owned trust for detached telemetry lineage signatures."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from re import compile as compile_pattern
from typing import Final
from typing import Never
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry_lineage import (
        TicketAdmissionTelemetryLineageComparison,
    )
    from accelerator.ticket_admission_telemetry_lineage_signature import (
        TicketAdmissionTelemetryLineageVerifier,
    )
    from accelerator.ticket_admission_telemetry_lineage_signature import (
        TicketAdmissionTelemetryVerifiedSignatureLineage,
    )

from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)
from accelerator.ticket_admission_telemetry_lineage import (
    TicketAdmissionTelemetryLineageError,
)
from accelerator.ticket_admission_telemetry_lineage import (
    compare_verified_ticket_admission_telemetry_lineage,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignatureAttestation,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignatureError,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    TicketAdmissionTelemetryLineageSignatureItem,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    verify_ticket_admission_telemetry_lineage_signature_item,
)

TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_TRUST_ID: Final = (
    "caller-owned-ticket-admission-telemetry-lineage-signature-trust-v1"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_KEYS: Final = 256

_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)


class TicketAdmissionTelemetryLineageSignatureTrustError(ValueError):
    """A public-key lineage signature trust set cannot be built or applied."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageSignatureTrustKey:
    """One exact public key and its inclusive capture validity window."""

    algorithm_id: str
    first_capture_sequence_id: int
    last_capture_sequence_id: int | None
    public_key: bytes = field(repr=False)
    public_key_fingerprint: str
    public_key_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageSignatureTrust:
    """Bounded deterministic public keys sorted by algorithm and identity."""

    key_count: int
    keys: tuple[TicketAdmissionTelemetryLineageSignatureTrustKey, ...]
    trust_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryTrustedSignatureLineage:
    """One verified signature plus its exact trusted public-key window."""

    algorithm_id: str
    first_capture_sequence_id: int
    last_capture_sequence_id: int | None
    public_key_fingerprint: str
    public_key_id: str
    trust_id: str
    verified_signature: TicketAdmissionTelemetryVerifiedSignatureLineage


def ticket_admission_telemetry_lineage_signature_trust_id() -> str:
    """Return the stable caller-owned public-key trust identity.

    Returns:
        Versioned detached signature trust identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_TRUST_ID


def build_ticket_admission_telemetry_lineage_signature_trust(
    keys: tuple[TicketAdmissionTelemetryLineageSignatureTrustKey, ...],
    *,
    max_keys: int = DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_KEYS,
) -> TicketAdmissionTelemetryLineageSignatureTrust:
    """Build one bounded deterministic in-memory public-key trust set.

    Returns:
        Canonical algorithm/key-identity-ordered trust set.

    """
    _validate_build_inputs(keys, max_keys=max_keys)
    validated_by_identity: dict[
        tuple[str, str],
        TicketAdmissionTelemetryLineageSignatureTrustKey,
    ] = {}
    for key in keys:
        validated = _validated_trust_key(key)
        identity = _key_identity(validated)
        if identity in validated_by_identity:
            _raise_trust("duplicate algorithm and public-key identity")
        validated_by_identity[identity] = validated
    ordered = tuple(
        validated_by_identity[identity]
        for identity in sorted(validated_by_identity)
    )
    return TicketAdmissionTelemetryLineageSignatureTrust(
        key_count=len(ordered),
        keys=ordered,
        trust_id=TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_TRUST_ID,
    )


def verify_ticket_admission_telemetry_lineage_signature_with_trust(
    item: TicketAdmissionTelemetryLineageSignatureItem,
    verifier: TicketAdmissionTelemetryLineageVerifier,
    trust: TicketAdmissionTelemetryLineageSignatureTrust,
) -> TicketAdmissionTelemetryTrustedSignatureLineage:
    """Verify one signature with its exact trusted algorithm/key window.

    Returns:
        Verified canonical signature and selected inclusive key window.

    Raises:
        TicketAdmissionTelemetryLineageSignatureTrustError: Trust selection or
            signature verification fails.

    """
    validated_trust = _validated_trust(trust)
    key = _selected_key(item, validated_trust)
    _validate_capture_window(item.attestation.capture_sequence_id, key)
    if item.attestation.public_key_fingerprint != key.public_key_fingerprint:
        _raise_trust("attestation public-key fingerprint is not trusted")
    try:
        verified = verify_ticket_admission_telemetry_lineage_signature_item(
            item,
            verifier,
            public_key=key.public_key,
        )
    except TicketAdmissionTelemetryLineageSignatureError as error:
        message = f"invalid trusted signature item: {error}"
        raise TicketAdmissionTelemetryLineageSignatureTrustError(
            message
        ) from error
    return TicketAdmissionTelemetryTrustedSignatureLineage(
        algorithm_id=key.algorithm_id,
        first_capture_sequence_id=key.first_capture_sequence_id,
        last_capture_sequence_id=key.last_capture_sequence_id,
        public_key_fingerprint=key.public_key_fingerprint,
        public_key_id=key.public_key_id,
        trust_id=validated_trust.trust_id,
        verified_signature=verified,
    )


def compare_ticket_admission_telemetry_lineage_signatures_with_trust(
    first: TicketAdmissionTelemetryLineageSignatureItem,
    second: TicketAdmissionTelemetryLineageSignatureItem,
    verifier: TicketAdmissionTelemetryLineageVerifier,
    *,
    trust: TicketAdmissionTelemetryLineageSignatureTrust,
) -> TicketAdmissionTelemetryLineageComparison:
    """Compare two signatures after independent trust-aware verification.

    Returns:
        Authenticated relation across same or rotated public keys/algorithms.

    Raises:
        TicketAdmissionTelemetryLineageSignatureTrustError: Trust,
            verification, or comparison fails.

    """
    first_trusted = (
        verify_ticket_admission_telemetry_lineage_signature_with_trust(
            first,
            verifier,
            trust,
        )
    )
    second_trusted = (
        verify_ticket_admission_telemetry_lineage_signature_with_trust(
            second,
            verifier,
            trust,
        )
    )
    try:
        return compare_verified_ticket_admission_telemetry_lineage(
            first_trusted.verified_signature.verified_item,
            second_trusted.verified_signature.verified_item,
        )
    except TicketAdmissionTelemetryLineageError as error:
        message = f"invalid trusted signature comparison: {error}"
        raise TicketAdmissionTelemetryLineageSignatureTrustError(
            message
        ) from error


def _validate_build_inputs(
    keys: tuple[TicketAdmissionTelemetryLineageSignatureTrustKey, ...],
    *,
    max_keys: int,
) -> None:
    if type(keys) is not tuple:
        _raise_trust("keys must use the exact immutable tuple type")
    if type(max_keys) is not int or max_keys <= 0:
        _raise_trust("key limit must be a positive integer")
    if len(keys) > max_keys:
        _raise_trust("key count exceeds configured limit")


def _validated_trust_key(
    key: TicketAdmissionTelemetryLineageSignatureTrustKey,
) -> TicketAdmissionTelemetryLineageSignatureTrustKey:
    if type(key) is not TicketAdmissionTelemetryLineageSignatureTrustKey:
        _raise_trust("key entry must use the exact signature trust-key type")
    _ = _validated_identifier(key.algorithm_id, "algorithm identity")
    _ = _validated_identifier(key.public_key_id, "public-key identity")
    fingerprint = _public_key_fingerprint(key.public_key)
    if key.public_key_fingerprint != fingerprint:
        _raise_trust("public-key fingerprint does not match exact key bytes")
    first = _validated_sequence_id(
        key.first_capture_sequence_id,
        "first capture sequence identity",
    )
    last = key.last_capture_sequence_id
    if last is not None:
        validated_last = _validated_sequence_id(
            last,
            "last capture sequence identity",
        )
        if validated_last < first:
            _raise_trust(
                "last capture sequence precedes first capture sequence"
            )
    return key


def _validated_trust(
    trust: TicketAdmissionTelemetryLineageSignatureTrust,
) -> TicketAdmissionTelemetryLineageSignatureTrust:
    if type(trust) is not TicketAdmissionTelemetryLineageSignatureTrust:
        _raise_trust("trust must use the exact signature trust type")
    if trust.trust_id != TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_TRUST_ID:
        _raise_trust("trust identity is unsupported")
    if type(trust.key_count) is not int or trust.key_count != len(trust.keys):
        _raise_trust("trust key count is inconsistent")
    _validate_build_inputs(
        trust.keys,
        max_keys=DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_KEYS,
    )
    _validate_trust_order(trust.keys)
    return trust


def _validate_trust_order(
    keys: tuple[TicketAdmissionTelemetryLineageSignatureTrustKey, ...],
) -> None:
    previous_identity: tuple[str, str] | None = None
    for key in keys:
        validated = _validated_trust_key(key)
        identity = _key_identity(validated)
        if previous_identity is not None and identity <= previous_identity:
            _raise_trust(
                "trust keys must be uniquely ordered by algorithm and identity"
            )
        previous_identity = identity


def _selected_key(
    item: TicketAdmissionTelemetryLineageSignatureItem,
    trust: TicketAdmissionTelemetryLineageSignatureTrust,
) -> TicketAdmissionTelemetryLineageSignatureTrustKey:
    if type(item) is not TicketAdmissionTelemetryLineageSignatureItem:
        _raise_trust("item must use the exact signature item type")
    if (
        type(item.attestation)
        is not TicketAdmissionTelemetryLineageSignatureAttestation
    ):
        _raise_trust("attestation must use the exact signature type")
    identity = (
        item.attestation.algorithm_id,
        item.attestation.public_key_id,
    )
    for key in trust.keys:
        if _key_identity(key) == identity:
            return key
    return _raise_trust(
        "attestation algorithm and public-key identity are not in trust set"
    )


def _validate_capture_window(
    capture_sequence_id: int,
    key: TicketAdmissionTelemetryLineageSignatureTrustKey,
) -> None:
    sequence_id = _validated_sequence_id(
        capture_sequence_id,
        "capture sequence identity",
    )
    if sequence_id < key.first_capture_sequence_id:
        _raise_trust("capture sequence precedes trusted public-key window")
    if (
        key.last_capture_sequence_id is not None
        and sequence_id > key.last_capture_sequence_id
    ):
        _raise_trust("capture sequence exceeds trusted public-key window")


def _key_identity(
    key: TicketAdmissionTelemetryLineageSignatureTrustKey,
) -> tuple[str, str]:
    return (key.algorithm_id, key.public_key_id)


def _public_key_fingerprint(public_key: bytes) -> str:
    try:
        return ticket_admission_telemetry_lineage_public_key_fingerprint(
            public_key
        )
    except TicketAdmissionTelemetryLineageSignatureError as error:
        message = f"invalid public key: {error}"
        raise TicketAdmissionTelemetryLineageSignatureTrustError(
            message
        ) from error


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_trust(f"{field_name} must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_trust(f"{field_name} exceeds configured length")
    return value


def _validated_sequence_id(value: int, field_name: str) -> int:
    if type(value) is not int or value < 0:
        _raise_trust(f"{field_name} must be a nonnegative integer")
    return value


def _raise_trust(detail: str) -> Never:
    message = f"ticket admission telemetry lineage signature trust {detail}"
    raise TicketAdmissionTelemetryLineageSignatureTrustError(message)
