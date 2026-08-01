# File:
#   - ticket_admission_telemetry_lineage_signature_trust_manifest.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
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
#   - Canonical key-free persistence for detached signature trust metadata.
# - Must-Not:
#   - Persist public keys, load keys automatically, select algorithms, infer
#     trust, retry, cache, merge snapshots, or change policy.
# - Allows:
#   - Inputs: explicit metadata entries, paths, and caller-resolved public keys.
#   - Outputs: canonical manifests and caller-owned signature trust sets.
#   - Side effects: explicit bounded file reads and atomic replacement only.
# - Split-When:
#   - Split when native async HTTPS, concrete credential providers,
#     hosted APIs, certificates, or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact public-key manifest boundary.
# - Summary:
#   - Canonical external metadata for detached lineage signature trust.
# - Description:
#   - Persists algorithm/key references and windows without public-key bytes.
# - Usage:
#   - Build or read explicitly, resolve public keys, then verify signatures.
# - Defaults:
#   - At most 256 entries and 64 KiB of canonical UTF-8 JSON.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_signature.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust.py
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
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_persistence.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Canonical key-free manifests for detached telemetry signature trust."""

# ruff: file-ignore[line-too-long,doc-line-too-long]

from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from hashlib import sha256
import json
import os
from pathlib import Path
from re import compile as compile_pattern
from tempfile import NamedTemporaryFile
from typing import Final
from typing import Never
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry_lineage_signature_trust import (
        TicketAdmissionTelemetryLineageSignatureTrust,
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
from accelerator.ticket_admission_telemetry_lineage_signature_trust import (
    DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_KEYS,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust import (
    TicketAdmissionTelemetryLineageSignatureTrustError,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust import (
    TicketAdmissionTelemetryLineageSignatureTrustKey,
)
from accelerator.ticket_admission_telemetry_lineage_signature_trust import (
    build_ticket_admission_telemetry_lineage_signature_trust,
)

TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_ID: Final = (
    "ticket-admission-telemetry-lineage-signature-trust-manifest-v1"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_SCHEMA_VERSION = 1
(
    TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_FINGERPRINT_PREFIX
) = "ticket-admission-telemetry-lineage-signature-trust-manifest-v1:sha256:"
_MANIFEST_FINGERPRINT_PREFIX: Final = (
    "ticket-admission-telemetry-lineage-signature-trust-manifest-v1:sha256:"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_BYTES: Final = 64 * 1024
DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_ENTRIES: Final = (
    DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_KEYS
)

_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_PUBLIC_KEY_FINGERPRINT_PATTERN: Final = compile_pattern(
    r"ticket-admission-telemetry-lineage-public-key-v1:sha256:[0-9a-f]{64}"
)
_ROOT_KEYS: Final = frozenset(("entries", "manifest_id", "schema_version"))
_ENTRY_KEYS: Final = frozenset((
    "algorithm_id",
    "first_capture_sequence_id",
    "last_capture_sequence_id",
    "public_key_fingerprint",
    "public_key_id",
    "public_key_reference_id",
))


class TicketAdmissionTelemetryLineageSignatureTrustManifestError(ValueError):
    """A key-free detached signature trust manifest is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageSignatureTrustManifestEntry:
    """One persisted algorithm/key identity, reference, and capture window."""

    algorithm_id: str
    first_capture_sequence_id: int
    last_capture_sequence_id: int | None
    public_key_fingerprint: str
    public_key_id: str
    public_key_reference_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageSignatureTrustManifest:
    """Canonical key-free detached signature trust metadata."""

    entries: tuple[
        TicketAdmissionTelemetryLineageSignatureTrustManifestEntry, ...
    ]
    manifest_id: str
    schema_version: int


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageResolvedPublicKey:
    """One explicit caller resolution for a public-key reference."""

    algorithm_id: str
    public_key: bytes = field(repr=False)
    public_key_id: str
    public_key_reference_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageResolvedSignatureTrust:
    """Resolved signature trust bound to its canonical manifest identity."""

    manifest_fingerprint: str
    trust: TicketAdmissionTelemetryLineageSignatureTrust


def ticket_admission_telemetry_lineage_signature_trust_manifest_id() -> str:
    """Return the stable key-free signature trust manifest identity.

    Returns:
        Versioned manifest identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_ID


def build_ticket_admission_telemetry_lineage_signature_trust_manifest(
    entries: tuple[
        TicketAdmissionTelemetryLineageSignatureTrustManifestEntry, ...
    ],
    *,
    max_entries: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_ENTRIES
    ),
) -> TicketAdmissionTelemetryLineageSignatureTrustManifest:
    """Build one bounded canonical manifest from explicit metadata entries.

    Returns:
        Composite-identity-ordered key-free manifest.

    """
    _validate_entry_inputs(entries, max_entries=max_entries)
    entries_by_identity: dict[
        tuple[str, str],
        TicketAdmissionTelemetryLineageSignatureTrustManifestEntry,
    ] = {}
    reference_ids: set[str] = set()
    for entry in entries:
        validated = _validated_entry(entry)
        identity = _entry_identity(validated)
        if identity in entries_by_identity:
            _raise_manifest("duplicate algorithm and public-key identity")
        if validated.public_key_reference_id in reference_ids:
            _raise_manifest("duplicate public-key reference identity")
        entries_by_identity[identity] = validated
        reference_ids.add(validated.public_key_reference_id)
    ordered = tuple(
        entries_by_identity[identity]
        for identity in sorted(entries_by_identity)
    )
    return TicketAdmissionTelemetryLineageSignatureTrustManifest(
        entries=ordered,
        manifest_id=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_ID
        ),
        schema_version=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_SCHEMA_VERSION
        ),
    )


def encode_ticket_admission_telemetry_lineage_signature_trust_manifest(
    manifest: TicketAdmissionTelemetryLineageSignatureTrustManifest,
) -> bytes:
    """Encode one validated manifest as canonical compact UTF-8 JSON.

    Returns:
        Sorted-key JSON bytes with one trailing newline.

    """
    validated = _validated_manifest(manifest)
    text = json.dumps(
        asdict(validated),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{text}\n".encode()


def decode_ticket_admission_telemetry_lineage_signature_trust_manifest(
    data: bytes,
    *,
    max_bytes: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_BYTES
    ),
    max_entries: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_ENTRIES
    ),
) -> TicketAdmissionTelemetryLineageSignatureTrustManifest:
    """Decode canonical bounded key-free trust metadata.

    Returns:
        Validated canonical manifest.

    """
    byte_limit = _validated_positive_limit(max_bytes, "byte limit")
    entry_limit = _validated_positive_limit(max_entries, "entry limit")
    payload = _validated_payload(data, max_bytes=byte_limit)
    manifest = _manifest_from_mapping(
        _json_mapping(payload),
        max_entries=entry_limit,
    )
    encoded = (
        encode_ticket_admission_telemetry_lineage_signature_trust_manifest(
            manifest
        )
    )
    if encoded != data:
        _raise_manifest("manifest bytes are not canonical")
    return manifest


def ticket_admission_telemetry_lineage_signature_trust_manifest_fingerprint(
    manifest: TicketAdmissionTelemetryLineageSignatureTrustManifest,
) -> str:
    """Return the SHA-256 identity of canonical manifest bytes.

    Returns:
        Versioned manifest fingerprint.

    """
    payload = (
        encode_ticket_admission_telemetry_lineage_signature_trust_manifest(
            manifest
        )
    )
    digest = sha256(payload).hexdigest()
    return f"{_MANIFEST_FINGERPRINT_PREFIX}{digest}"


def write_ticket_admission_telemetry_lineage_signature_trust_manifest(
    path: Path,
    manifest: TicketAdmissionTelemetryLineageSignatureTrustManifest,
) -> None:
    """Atomically replace one explicit path with canonical manifest bytes.

    Raises:
        TicketAdmissionTelemetryLineageSignatureTrustManifestError: Encoding
            or writing fails.

    """
    destination = _validated_path(path)
    payload = (
        encode_ticket_admission_telemetry_lineage_signature_trust_manifest(
            manifest
        )
    )
    temporary = _write_temporary(destination, payload)
    try:
        _ = temporary.replace(destination)
    except OSError as error:
        _remove_temporary(temporary)
        message = f"cannot replace signature trust manifest: {error}"
        raise TicketAdmissionTelemetryLineageSignatureTrustManifestError(
            message
        ) from error


def read_ticket_admission_telemetry_lineage_signature_trust_manifest(
    path: Path,
    *,
    max_bytes: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_BYTES
    ),
    max_entries: int = (
        DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_ENTRIES
    ),
) -> TicketAdmissionTelemetryLineageSignatureTrustManifest:
    """Read one explicit key-free manifest under bounded limits.

    Returns:
        Validated canonical manifest.

    Raises:
        TicketAdmissionTelemetryLineageSignatureTrustManifestError: Reading
            or decoding fails.

    """
    source = _validated_path(path)
    byte_limit = _validated_positive_limit(max_bytes, "byte limit")
    try:
        with source.open("rb") as input_file:
            payload = input_file.read(byte_limit + 1)
    except OSError as error:
        message = f"cannot read signature trust manifest: {error}"
        raise TicketAdmissionTelemetryLineageSignatureTrustManifestError(
            message
        ) from error
    return decode_ticket_admission_telemetry_lineage_signature_trust_manifest(
        payload,
        max_bytes=byte_limit,
        max_entries=max_entries,
    )


def resolve_ticket_admission_telemetry_lineage_signature_trust_manifest(
    manifest: TicketAdmissionTelemetryLineageSignatureTrustManifest,
    public_keys: tuple[TicketAdmissionTelemetryLineageResolvedPublicKey, ...],
) -> TicketAdmissionTelemetryLineageResolvedSignatureTrust:
    """Resolve every persisted reference from explicit caller public keys.

    Returns:
        Caller-owned in-memory trust bound to the canonical manifest identity.

    Raises:
        TicketAdmissionTelemetryLineageSignatureTrustManifestError: Metadata or
            resolution coverage is invalid.

    """
    validated_manifest = _validated_manifest(manifest)
    resolved_by_identity = _validated_resolutions(public_keys)
    if len(resolved_by_identity) != len(validated_manifest.entries):
        _raise_manifest(
            "resolved public-key coverage is incomplete or excessive"
        )
    trust_keys = tuple(
        _resolved_trust_key(entry, resolved_by_identity)
        for entry in validated_manifest.entries
    )
    try:
        trust = build_ticket_admission_telemetry_lineage_signature_trust(
            trust_keys
        )
    except TicketAdmissionTelemetryLineageSignatureTrustError as error:
        message = f"cannot build resolved signature trust: {error}"
        raise TicketAdmissionTelemetryLineageSignatureTrustManifestError(
            message
        ) from error
    return TicketAdmissionTelemetryLineageResolvedSignatureTrust(
        manifest_fingerprint=(
            ticket_admission_telemetry_lineage_signature_trust_manifest_fingerprint(
                validated_manifest
            )
        ),
        trust=trust,
    )


def _validated_manifest(
    manifest: TicketAdmissionTelemetryLineageSignatureTrustManifest,
) -> TicketAdmissionTelemetryLineageSignatureTrustManifest:
    if (
        type(manifest)
        is not TicketAdmissionTelemetryLineageSignatureTrustManifest
    ):
        _raise_manifest(
            "manifest must use the exact signature trust manifest type"
        )
    _validate_manifest_header(manifest)
    _validate_manifest_entries(manifest.entries)
    return manifest


def _validate_manifest_header(
    manifest: TicketAdmissionTelemetryLineageSignatureTrustManifest,
) -> None:
    if (
        manifest.manifest_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_ID
    ):
        _raise_manifest("manifest identity is unsupported")
    if type(manifest.schema_version) is not int or manifest.schema_version != (
        TICKET_ADMISSION_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_SCHEMA_VERSION
    ):
        _raise_manifest("manifest schema is unsupported")


def _validate_manifest_entries(
    entries: tuple[
        TicketAdmissionTelemetryLineageSignatureTrustManifestEntry, ...
    ],
) -> None:
    _validate_entry_inputs(
        entries,
        max_entries=DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_ENTRIES,
    )
    previous_identity: tuple[str, str] | None = None
    reference_ids: set[str] = set()
    for entry in entries:
        validated = _validated_entry(entry)
        identity = _entry_identity(validated)
        if previous_identity is not None and identity <= previous_identity:
            _raise_manifest(
                "manifest entries must be uniquely ordered by algorithm and key"
            )
        if validated.public_key_reference_id in reference_ids:
            _raise_manifest("duplicate public-key reference identity")
        previous_identity = identity
        reference_ids.add(validated.public_key_reference_id)


def _validate_entry_inputs(
    entries: tuple[
        TicketAdmissionTelemetryLineageSignatureTrustManifestEntry, ...
    ],
    *,
    max_entries: int,
) -> None:
    if type(entries) is not tuple:
        _raise_manifest("entries must use the exact immutable tuple type")
    limit = _validated_positive_limit(max_entries, "entry limit")
    if len(entries) > limit:
        _raise_manifest("entry count exceeds configured limit")


def _validated_entry(
    entry: TicketAdmissionTelemetryLineageSignatureTrustManifestEntry,
) -> TicketAdmissionTelemetryLineageSignatureTrustManifestEntry:
    if (
        type(entry)
        is not TicketAdmissionTelemetryLineageSignatureTrustManifestEntry
    ):
        _raise_manifest("entry must use the exact manifest entry type")
    _ = _validated_identifier(entry.algorithm_id, "algorithm identity")
    _ = _validated_identifier(entry.public_key_id, "public-key identity")
    _ = _validated_identifier(
        entry.public_key_reference_id,
        "public-key reference identity",
    )
    _ = _validated_public_key_fingerprint(entry.public_key_fingerprint)
    first = _validated_sequence_id(
        entry.first_capture_sequence_id,
        "first capture sequence identity",
    )
    last = entry.last_capture_sequence_id
    if last is not None:
        validated_last = _validated_sequence_id(
            last,
            "last capture sequence identity",
        )
        if validated_last < first:
            _raise_manifest(
                "last capture sequence precedes first capture sequence"
            )
    return entry


def _validated_resolutions(
    public_keys: tuple[TicketAdmissionTelemetryLineageResolvedPublicKey, ...],
) -> dict[tuple[str, str], TicketAdmissionTelemetryLineageResolvedPublicKey]:
    _validate_resolution_inputs(public_keys)
    resolved_by_identity: dict[
        tuple[str, str],
        TicketAdmissionTelemetryLineageResolvedPublicKey,
    ] = {}
    reference_ids: set[str] = set()
    for public_key in public_keys:
        validated = _validated_resolution(public_key)
        identity = _resolution_identity(validated)
        if identity in resolved_by_identity:
            _raise_manifest(
                "duplicate resolved algorithm and public-key identity"
            )
        if validated.public_key_reference_id in reference_ids:
            _raise_manifest("duplicate resolved public-key reference identity")
        resolved_by_identity[identity] = validated
        reference_ids.add(validated.public_key_reference_id)
    return resolved_by_identity


def _validate_resolution_inputs(
    public_keys: tuple[TicketAdmissionTelemetryLineageResolvedPublicKey, ...],
) -> None:
    if type(public_keys) is not tuple:
        _raise_manifest(
            "resolved public keys must use the exact immutable tuple type"
        )
    if (
        len(public_keys)
        > DEFAULT_MAX_TELEMETRY_LINEAGE_SIGNATURE_TRUST_MANIFEST_ENTRIES
    ):
        _raise_manifest("resolved public-key count exceeds configured limit")


def _validated_resolution(
    public_key: TicketAdmissionTelemetryLineageResolvedPublicKey,
) -> TicketAdmissionTelemetryLineageResolvedPublicKey:
    if type(public_key) is not TicketAdmissionTelemetryLineageResolvedPublicKey:
        _raise_manifest(
            "resolved public key must use the exact resolution type"
        )
    _ = _validated_identifier(
        public_key.algorithm_id,
        "resolved algorithm identity",
    )
    _ = _validated_identifier(
        public_key.public_key_id,
        "resolved public-key identity",
    )
    _ = _validated_identifier(
        public_key.public_key_reference_id,
        "resolved public-key reference identity",
    )
    _ = _public_key_fingerprint(public_key.public_key)
    return public_key


def _resolved_trust_key(
    entry: TicketAdmissionTelemetryLineageSignatureTrustManifestEntry,
    resolved_by_identity: dict[
        tuple[str, str],
        TicketAdmissionTelemetryLineageResolvedPublicKey,
    ],
) -> TicketAdmissionTelemetryLineageSignatureTrustKey:
    public_key = resolved_by_identity.get(_entry_identity(entry))
    if public_key is None:
        _raise_manifest("manifest identity has no resolved public key")
    if public_key.public_key_reference_id != entry.public_key_reference_id:
        _raise_manifest("resolved public-key reference does not match manifest")
    fingerprint = _public_key_fingerprint(public_key.public_key)
    if fingerprint != entry.public_key_fingerprint:
        _raise_manifest(
            "resolved public-key fingerprint does not match manifest"
        )
    return TicketAdmissionTelemetryLineageSignatureTrustKey(
        algorithm_id=entry.algorithm_id,
        first_capture_sequence_id=entry.first_capture_sequence_id,
        last_capture_sequence_id=entry.last_capture_sequence_id,
        public_key=public_key.public_key,
        public_key_fingerprint=entry.public_key_fingerprint,
        public_key_id=entry.public_key_id,
    )


def _entry_identity(
    entry: TicketAdmissionTelemetryLineageSignatureTrustManifestEntry,
) -> tuple[str, str]:
    return (entry.algorithm_id, entry.public_key_id)


def _resolution_identity(
    public_key: TicketAdmissionTelemetryLineageResolvedPublicKey,
) -> tuple[str, str]:
    return (public_key.algorithm_id, public_key.public_key_id)


def _public_key_fingerprint(public_key: bytes) -> str:
    try:
        return ticket_admission_telemetry_lineage_public_key_fingerprint(
            public_key
        )
    except TicketAdmissionTelemetryLineageSignatureError as error:
        message = f"invalid resolved public key: {error}"
        raise TicketAdmissionTelemetryLineageSignatureTrustManifestError(
            message
        ) from error


def _validated_public_key_fingerprint(value: str) -> str:
    if (
        type(value) is not str
        or _PUBLIC_KEY_FINGERPRINT_PATTERN.fullmatch(value) is None
    ):
        _raise_manifest("public-key fingerprint is malformed")
    return value


def _manifest_from_mapping(
    mapping: dict[str, object],
    *,
    max_entries: int,
) -> TicketAdmissionTelemetryLineageSignatureTrustManifest:
    _expect_exact_keys(mapping, _ROOT_KEYS, "signature trust manifest")
    raw_entries = _expect_list(
        mapping["entries"],
        "signature trust manifest.entries",
    )
    if len(raw_entries) > max_entries:
        _raise_manifest("entry count exceeds configured limit")
    entries = tuple(
        _entry_from_mapping(value, index)
        for index, value in enumerate(raw_entries)
    )
    built = build_ticket_admission_telemetry_lineage_signature_trust_manifest(
        entries,
        max_entries=max_entries,
    )
    manifest_id = _expect_string(
        mapping["manifest_id"],
        "signature trust manifest.manifest_id",
    )
    schema_version = _expect_int(
        mapping["schema_version"],
        "signature trust manifest.schema_version",
    )
    return _validated_manifest(
        TicketAdmissionTelemetryLineageSignatureTrustManifest(
            entries=built.entries,
            manifest_id=manifest_id,
            schema_version=schema_version,
        )
    )


def _entry_from_mapping(
    value: object,
    index: int,
) -> TicketAdmissionTelemetryLineageSignatureTrustManifestEntry:
    context = f"signature trust manifest.entries[{index}]"
    mapping = _expect_mapping(value, context)
    _expect_exact_keys(mapping, _ENTRY_KEYS, context)
    return TicketAdmissionTelemetryLineageSignatureTrustManifestEntry(
        algorithm_id=_expect_string(
            mapping["algorithm_id"],
            f"{context}.algorithm_id",
        ),
        first_capture_sequence_id=_expect_int(
            mapping["first_capture_sequence_id"],
            f"{context}.first_capture_sequence_id",
        ),
        last_capture_sequence_id=_expect_optional_int(
            mapping["last_capture_sequence_id"],
            f"{context}.last_capture_sequence_id",
        ),
        public_key_fingerprint=_expect_string(
            mapping["public_key_fingerprint"],
            f"{context}.public_key_fingerprint",
        ),
        public_key_id=_expect_string(
            mapping["public_key_id"],
            f"{context}.public_key_id",
        ),
        public_key_reference_id=_expect_string(
            mapping["public_key_reference_id"],
            f"{context}.public_key_reference_id",
        ),
    )


def _validated_payload(data: bytes, *, max_bytes: int) -> bytes:
    if type(data) is not bytes:
        _raise_manifest("manifest payload must use the exact bytes type")
    if not data:
        _raise_manifest("manifest payload cannot be empty")
    if len(data) > max_bytes:
        _raise_manifest("manifest exceeds configured byte limit")
    return data


def _json_mapping(data: bytes) -> dict[str, object]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        message = (
            "ticket admission telemetry lineage signature trust manifest "
            "is not UTF-8"
        )
        raise TicketAdmissionTelemetryLineageSignatureTrustManifestError(
            message
        ) from error
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
        message = (
            "ticket admission telemetry lineage signature trust manifest "
            "is not valid JSON"
        )
        raise TicketAdmissionTelemetryLineageSignatureTrustManifestError(
            message
        ) from error
    return _expect_mapping(parsed, "signature trust manifest")


def _reject_duplicate_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    mapping: dict[str, object] = {}
    for key, value in pairs:
        if key in mapping:
            _raise_manifest(f"duplicate JSON key: {key}")
        mapping[key] = value
    return mapping


def _reject_json_constant(value: str) -> Never:
    _raise_manifest(f"invalid JSON constant: {value}")


def _expect_mapping(value: object, context: str) -> dict[str, object]:
    if type(value) is not dict:
        _raise_manifest(f"{context} must be an object")
    return cast("dict[str, object]", value)


def _expect_list(value: object, context: str) -> list[object]:
    if type(value) is not list:
        _raise_manifest(f"{context} must be an array")
    return cast("list[object]", value)


def _expect_string(value: object, context: str) -> str:
    if type(value) is not str:
        _raise_manifest(f"{context} must be a string")
    return value


def _expect_int(value: object, context: str) -> int:
    if type(value) is not int:
        _raise_manifest(f"{context} must be an integer")
    return value


def _expect_optional_int(value: object, context: str) -> int | None:
    if value is None:
        return None
    return _expect_int(value, context)


def _expect_exact_keys(
    mapping: dict[str, object],
    expected: frozenset[str],
    context: str,
) -> None:
    keys = frozenset(mapping)
    if keys != expected:
        _raise_manifest(f"{context} keys are unsupported")


def _validated_identifier(value: str, field_name: str) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        _raise_manifest(f"{field_name} must use canonical ASCII identity form")
    if len(value) > MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH:
        _raise_manifest(f"{field_name} exceeds configured length")
    return value


def _validated_sequence_id(value: int, field_name: str) -> int:
    if type(value) is not int or value < 0:
        _raise_manifest(f"{field_name} must be a nonnegative integer")
    return value


def _validated_positive_limit(value: int, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        _raise_manifest(f"{field_name} must be a positive integer")
    return value


def _validated_path(path: object) -> Path:
    if not isinstance(path, Path):
        _raise_manifest("path must be a pathlib Path")
    if not path.name:
        _raise_manifest("path must name a file")
    return path


def _write_temporary(destination: Path, payload: bytes) -> Path:
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as output:
            temporary = Path(output.name)
            _ = output.write(payload)
            output.flush()
            os.fsync(output.fileno())
    except OSError as error:
        if temporary is not None:
            _remove_temporary(temporary)
        message = f"cannot write signature trust manifest: {error}"
        raise TicketAdmissionTelemetryLineageSignatureTrustManifestError(
            message
        ) from error
    return temporary


def _remove_temporary(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def _raise_manifest(detail: str) -> Never:
    message = (
        f"ticket admission telemetry lineage signature trust manifest {detail}"
    )
    raise TicketAdmissionTelemetryLineageSignatureTrustManifestError(message)
