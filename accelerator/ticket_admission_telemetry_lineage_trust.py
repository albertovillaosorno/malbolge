# File:
#   - ticket_admission_telemetry_lineage_trust.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_trust.py
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
#   - Bounded caller-owned HMAC lineage trust and capture-window rotation.
# - Must-Not:
#   - Load keys, persist secrets, infer trust, merge snapshots, or change
#     policy.
# - Allows:
#   - Inputs: explicit trust keys and authenticated lineage items.
#   - Outputs: immutable trust sets and independently verified comparisons.
#   - Side effects: none.
# - Split-When:
#   - Split when asymmetric signatures or external trust stores gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact caller-owned trust boundary.
# - Summary:
#   - Bounded in-memory telemetry lineage key rotation.
# - Description:
#   - Selects exact HMAC keys by identity and inclusive capture windows.
# - Usage:
#   - Build explicitly, verify each item, then compare verified lineage.
# - Defaults:
#   - At most 256 unique keys; empty trust sets are valid and trust nothing.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Bounded caller-owned trust and rotation for telemetry lineage keys."""

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
    from accelerator.ticket_admission_telemetry_lineage import (
        TicketAdmissionTelemetryVerifiedLineageItem,
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
from accelerator.ticket_admission_telemetry_lineage import (
    TicketAdmissionTelemetryLineageAttestation,
)
from accelerator.ticket_admission_telemetry_lineage import (
    TicketAdmissionTelemetryLineageError,
)
from accelerator.ticket_admission_telemetry_lineage import (
    TicketAdmissionTelemetryLineageItem,
)
from accelerator.ticket_admission_telemetry_lineage import (
    compare_verified_ticket_admission_telemetry_lineage,
)
from accelerator.ticket_admission_telemetry_lineage import (
    verify_ticket_admission_telemetry_lineage_item,
)

TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_ID: Final = (
    "caller-owned-ticket-admission-telemetry-lineage-trust-v1"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_KEYS: Final = 256

_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)


class TicketAdmissionTelemetryLineageTrustError(ValueError):
    """A caller-owned lineage trust set cannot be built or applied."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageTrustKey:
    """One caller-owned secret and its inclusive capture validity window."""

    first_capture_sequence_id: int
    key_id: str
    last_capture_sequence_id: int | None
    secret_key: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageTrust:
    """Bounded deterministic trust keys sorted by canonical identity."""

    key_count: int
    keys: tuple[TicketAdmissionTelemetryLineageTrustKey, ...]
    trust_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryTrustedLineageItem:
    """One verified item plus the exact selected trust-key window."""

    first_capture_sequence_id: int
    key_id: str
    last_capture_sequence_id: int | None
    trust_id: str
    verified_item: TicketAdmissionTelemetryVerifiedLineageItem


def ticket_admission_telemetry_lineage_trust_id() -> str:
    """Return the stable caller-owned trust identity.

    Returns:
        Versioned lineage trust identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_ID


def build_ticket_admission_telemetry_lineage_trust(
    keys: tuple[TicketAdmissionTelemetryLineageTrustKey, ...],
    *,
    max_keys: int = DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_KEYS,
) -> TicketAdmissionTelemetryLineageTrust:
    """Build one bounded deterministic in-memory lineage trust set.

    Returns:
        Canonical key-identity-ordered trust set.

    """
    _validate_build_inputs(keys, max_keys=max_keys)
    validated_by_id: dict[str, TicketAdmissionTelemetryLineageTrustKey] = {}
    for key in keys:
        validated = _validated_trust_key(key)
        if validated.key_id in validated_by_id:
            _raise_trust("duplicate key identity")
        validated_by_id[validated.key_id] = validated
    ordered = tuple(
        validated_by_id[key_id] for key_id in sorted(validated_by_id)
    )
    return TicketAdmissionTelemetryLineageTrust(
        key_count=len(ordered),
        keys=ordered,
        trust_id=TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_ID,
    )


def verify_ticket_admission_telemetry_lineage_with_trust(
    item: TicketAdmissionTelemetryLineageItem,
    trust: TicketAdmissionTelemetryLineageTrust,
) -> TicketAdmissionTelemetryTrustedLineageItem:
    """Verify one lineage item with its exact trusted rotation entry.

    Returns:
        Verified canonical item and selected inclusive key window.

    Raises:
        TicketAdmissionTelemetryLineageTrustError: Trust or verification fails.

    """
    validated_trust = _validated_trust(trust)
    key = _selected_key(item, validated_trust)
    _validate_capture_window(item.attestation.capture_sequence_id, key)
    try:
        verified_item = verify_ticket_admission_telemetry_lineage_item(
            item,
            secret_key=key.secret_key,
            trusted_key_id=key.key_id,
        )
    except TicketAdmissionTelemetryLineageError as error:
        message = f"invalid authenticated lineage item: {error}"
        raise TicketAdmissionTelemetryLineageTrustError(message) from error
    return TicketAdmissionTelemetryTrustedLineageItem(
        first_capture_sequence_id=key.first_capture_sequence_id,
        key_id=key.key_id,
        last_capture_sequence_id=key.last_capture_sequence_id,
        trust_id=validated_trust.trust_id,
        verified_item=verified_item,
    )


def compare_ticket_admission_telemetry_lineage_with_trust(
    first: TicketAdmissionTelemetryLineageItem,
    second: TicketAdmissionTelemetryLineageItem,
    trust: TicketAdmissionTelemetryLineageTrust,
) -> TicketAdmissionTelemetryLineageComparison:
    """Compare two items after independent rotation-aware verification.

    Returns:
        Authenticated lineage relation across same-key or rotated-key captures.

    Raises:
        TicketAdmissionTelemetryLineageTrustError: Trust or comparison fails.

    """
    first_trusted = verify_ticket_admission_telemetry_lineage_with_trust(
        first,
        trust,
    )
    second_trusted = verify_ticket_admission_telemetry_lineage_with_trust(
        second,
        trust,
    )
    try:
        return compare_verified_ticket_admission_telemetry_lineage(
            first_trusted.verified_item,
            second_trusted.verified_item,
        )
    except TicketAdmissionTelemetryLineageError as error:
        message = f"invalid authenticated lineage comparison: {error}"
        raise TicketAdmissionTelemetryLineageTrustError(message) from error


def _validate_build_inputs(
    keys: tuple[TicketAdmissionTelemetryLineageTrustKey, ...],
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
    key: TicketAdmissionTelemetryLineageTrustKey,
) -> TicketAdmissionTelemetryLineageTrustKey:
    if type(key) is not TicketAdmissionTelemetryLineageTrustKey:
        _raise_trust("key entry must use the exact trust-key type")
    _ = _validated_key_id(key.key_id)
    _ = _validated_secret_key(key.secret_key)
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
    trust: TicketAdmissionTelemetryLineageTrust,
) -> TicketAdmissionTelemetryLineageTrust:
    if type(trust) is not TicketAdmissionTelemetryLineageTrust:
        _raise_trust("trust must use the exact lineage trust type")
    _validate_trust_header(trust)
    _validate_trust_order(trust.keys)
    return trust


def _validate_trust_header(
    trust: TicketAdmissionTelemetryLineageTrust,
) -> None:
    if trust.trust_id != TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_ID:
        _raise_trust("trust identity is unsupported")
    if type(trust.key_count) is not int or trust.key_count != len(trust.keys):
        _raise_trust("trust key count is inconsistent")
    _validate_build_inputs(
        trust.keys,
        max_keys=DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_KEYS,
    )


def _validate_trust_order(
    keys: tuple[TicketAdmissionTelemetryLineageTrustKey, ...],
) -> None:
    previous_key_id: str | None = None
    for key in keys:
        validated = _validated_trust_key(key)
        if previous_key_id is not None and validated.key_id <= previous_key_id:
            _raise_trust("trust keys must be uniquely ordered by identity")
        previous_key_id = validated.key_id


def _selected_key(
    item: TicketAdmissionTelemetryLineageItem,
    trust: TicketAdmissionTelemetryLineageTrust,
) -> TicketAdmissionTelemetryLineageTrustKey:
    if type(item) is not TicketAdmissionTelemetryLineageItem:
        _raise_trust("item must use the exact lineage item type")
    if type(item.attestation) is not TicketAdmissionTelemetryLineageAttestation:
        _raise_trust("attestation must use the exact lineage type")
    key_id = item.attestation.key_id
    for key in trust.keys:
        if key.key_id == key_id:
            return key
    message = (
        "ticket admission telemetry lineage trust attestation key identity "
        "is not present in trust set"
    )
    raise TicketAdmissionTelemetryLineageTrustError(message)


def _validate_capture_window(
    capture_sequence_id: int,
    key: TicketAdmissionTelemetryLineageTrustKey,
) -> None:
    sequence_id = _validated_sequence_id(
        capture_sequence_id,
        "capture sequence identity",
    )
    if sequence_id < key.first_capture_sequence_id:
        _raise_trust("capture sequence precedes trusted key window")
    if (
        key.last_capture_sequence_id is not None
        and sequence_id > key.last_capture_sequence_id
    ):
        _raise_trust("capture sequence exceeds trusted key window")


def _validated_key_id(value: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_trust("key identity must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_trust("key identity exceeds configured length")
    return value


def _validated_secret_key(value: bytes) -> bytes:
    if type(value) is not bytes:
        _raise_trust("secret key must use the exact bytes type")
    if len(value) < MIN_TELEMETRY_LINEAGE_KEY_BYTES:
        _raise_trust("secret key is shorter than the configured minimum")
    if len(value) > MAX_TELEMETRY_LINEAGE_KEY_BYTES:
        _raise_trust("secret key exceeds the configured maximum")
    return value


def _validated_sequence_id(value: int, field_name: str) -> int:
    if type(value) is not int or value < 0:
        _raise_trust(f"{field_name} must be a nonnegative integer")
    return value


def _raise_trust(detail: str) -> Never:
    message = f"ticket admission telemetry lineage trust {detail}"
    raise TicketAdmissionTelemetryLineageTrustError(message)
