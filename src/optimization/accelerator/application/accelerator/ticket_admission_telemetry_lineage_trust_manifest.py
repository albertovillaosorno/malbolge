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
#   - Canonical secret-free persistence for lineage trust metadata.
# - Must-Not:
#   - Persist secrets, load keys automatically, infer trust, or change policy.
# - Allows:
#   - Inputs: explicit metadata entries, paths, and caller-resolved secrets.
#   - Outputs: canonical manifests, identities, and caller-owned trust sets.
#   - Side effects: explicit bounded file reads and atomic replacement only.
# - Split-When:
#   - Split when concrete signature algorithms, external credential stores,
#     provider lifecycles, or PKI gain contracts.
# - Merge-When:
#   - Merge when another module owns this exact secret-free manifest boundary.
# - Summary:
#   - Canonical external metadata for telemetry lineage trust.
# - Description:
#   - Persists key references and capture windows without secret material.
# - Usage:
#   - Build or read explicitly, resolve secrets explicitly, then verify lineage.
# - Defaults:
#   - At most 256 entries and 64 KiB of canonical UTF-8 JSON.
#

"""Canonical secret-free manifests for telemetry lineage trust metadata."""

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
    from accelerator.ticket_admission_telemetry_lineage_trust import (
        TicketAdmissionTelemetryLineageTrust,
    )

from accelerator.ticket_admission_telemetry_lineage import (
    MAX_TELEMETRY_LINEAGE_IDENTIFIER_LENGTH,
)
from accelerator.ticket_admission_telemetry_lineage_trust import (
    DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_KEYS,
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

TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_MANIFEST_ID: Final = (
    "ticket-admission-telemetry-lineage-trust-manifest-v1"
)
TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_MANIFEST_SCHEMA_VERSION: Final = 1
TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_MANIFEST_FINGERPRINT_PREFIX: Final = (
    "ticket-admission-telemetry-lineage-trust-manifest-v1:sha256:"
)
DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_MANIFEST_BYTES: Final = 64 * 1024
DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_MANIFEST_ENTRIES: Final = (
    DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_KEYS
)

_IDENTIFIER_PATTERN: Final = compile_pattern(
    r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
)
_ROOT_KEYS: Final = frozenset(("entries", "manifest_id", "schema_version"))
_ENTRY_KEYS: Final = frozenset((
    "first_capture_sequence_id",
    "key_id",
    "key_reference_id",
    "last_capture_sequence_id",
))


class TicketAdmissionTelemetryLineageTrustManifestError(ValueError):
    """A secret-free lineage trust manifest is invalid or inaccessible."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageTrustManifestEntry:
    """One persisted key identity, reference, and inclusive capture window."""

    first_capture_sequence_id: int
    key_id: str
    key_reference_id: str
    last_capture_sequence_id: int | None


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageTrustManifest:
    """Canonical secret-free lineage trust metadata."""

    entries: tuple[TicketAdmissionTelemetryLineageTrustManifestEntry, ...]
    manifest_id: str
    schema_version: int


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageResolvedSecret:
    """One explicit caller resolution for a manifest key reference."""

    key_id: str
    key_reference_id: str
    secret_key: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageResolvedTrust:
    """Caller-owned trust plus the exact manifest identity that described it."""

    manifest_fingerprint: str
    trust: TicketAdmissionTelemetryLineageTrust


def ticket_admission_telemetry_lineage_trust_manifest_id() -> str:
    """Return the stable secret-free trust manifest identity.

    Returns:
        Versioned manifest identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_MANIFEST_ID


def build_ticket_admission_telemetry_lineage_trust_manifest(
    entries: tuple[TicketAdmissionTelemetryLineageTrustManifestEntry, ...],
    *,
    max_entries: int = DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_MANIFEST_ENTRIES,
) -> TicketAdmissionTelemetryLineageTrustManifest:
    """Build one bounded canonical manifest from explicit metadata entries.

    Returns:
        Key-identity-ordered secret-free manifest.

    """
    _validate_entry_inputs(entries, max_entries=max_entries)
    entries_by_key: dict[
        str,
        TicketAdmissionTelemetryLineageTrustManifestEntry,
    ] = {}
    reference_ids: set[str] = set()
    for entry in entries:
        validated = _validated_entry(entry)
        if validated.key_id in entries_by_key:
            _raise_manifest("duplicate key identity")
        if validated.key_reference_id in reference_ids:
            _raise_manifest("duplicate key reference identity")
        entries_by_key[validated.key_id] = validated
        reference_ids.add(validated.key_reference_id)
    ordered = tuple(entries_by_key[key_id] for key_id in sorted(entries_by_key))
    return TicketAdmissionTelemetryLineageTrustManifest(
        entries=ordered,
        manifest_id=TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_MANIFEST_ID,
        schema_version=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_MANIFEST_SCHEMA_VERSION
        ),
    )


def encode_ticket_admission_telemetry_lineage_trust_manifest(
    manifest: TicketAdmissionTelemetryLineageTrustManifest,
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


def decode_ticket_admission_telemetry_lineage_trust_manifest(
    data: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_MANIFEST_BYTES,
    max_entries: int = DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_MANIFEST_ENTRIES,
) -> TicketAdmissionTelemetryLineageTrustManifest:
    """Decode canonical bounded secret-free trust metadata.

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
    encoded = encode_ticket_admission_telemetry_lineage_trust_manifest(manifest)
    if encoded != data:
        _raise_manifest("manifest bytes are not canonical")
    return manifest


def ticket_admission_telemetry_lineage_trust_manifest_fingerprint(
    manifest: TicketAdmissionTelemetryLineageTrustManifest,
) -> str:
    """Return the SHA-256 identity of canonical manifest bytes.

    Returns:
        Versioned manifest fingerprint.

    """
    payload = encode_ticket_admission_telemetry_lineage_trust_manifest(manifest)
    digest = sha256(payload).hexdigest()
    return (
        # jig-ignore-next-line: indivisible reviewed identifier
        f"{TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_MANIFEST_FINGERPRINT_PREFIX}"
        f"{digest}"
    )


def write_ticket_admission_telemetry_lineage_trust_manifest(
    path: Path,
    manifest: TicketAdmissionTelemetryLineageTrustManifest,
) -> None:
    """Atomically replace one explicit path with canonical manifest bytes.

    Raises:
        TicketAdmissionTelemetryLineageTrustManifestError: Encoding or writing
            fails.

    """
    destination = _validated_path(path)
    payload = encode_ticket_admission_telemetry_lineage_trust_manifest(manifest)
    temporary = _write_temporary(destination, payload)
    try:
        _ = temporary.replace(destination)
    except OSError as error:
        _remove_temporary(temporary)
        message = f"cannot replace trust manifest: {error}"
        raise TicketAdmissionTelemetryLineageTrustManifestError(
            message
        ) from error


def read_ticket_admission_telemetry_lineage_trust_manifest(
    path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_MANIFEST_BYTES,
    max_entries: int = DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_MANIFEST_ENTRIES,
) -> TicketAdmissionTelemetryLineageTrustManifest:
    """Read one explicit secret-free manifest under bounded limits.

    Returns:
        Validated canonical manifest.

    Raises:
        TicketAdmissionTelemetryLineageTrustManifestError: Reading or decoding
            fails.

    """
    source = _validated_path(path)
    byte_limit = _validated_positive_limit(max_bytes, "byte limit")
    try:
        with source.open("rb") as input_file:
            payload = input_file.read(byte_limit + 1)
    except OSError as error:
        message = f"cannot read trust manifest: {error}"
        raise TicketAdmissionTelemetryLineageTrustManifestError(
            message
        ) from error
    return decode_ticket_admission_telemetry_lineage_trust_manifest(
        payload,
        max_bytes=byte_limit,
        max_entries=max_entries,
    )


def resolve_ticket_admission_telemetry_lineage_trust_manifest(
    manifest: TicketAdmissionTelemetryLineageTrustManifest,
    secrets: tuple[TicketAdmissionTelemetryLineageResolvedSecret, ...],
) -> TicketAdmissionTelemetryLineageResolvedTrust:
    """Resolve every persisted key reference from explicit caller secrets.

    Returns:
        Caller-owned in-memory trust bound to the canonical manifest identity.

    Raises:
        TicketAdmissionTelemetryLineageTrustManifestError: Metadata or
            resolution coverage is invalid.

    """
    validated_manifest = _validated_manifest(manifest)
    resolved_by_key = _validated_resolutions(secrets)
    if len(resolved_by_key) != len(validated_manifest.entries):
        _raise_manifest("resolved secret coverage is incomplete or excessive")
    trust_keys = tuple(
        _resolved_trust_key(entry, resolved_by_key)
        for entry in validated_manifest.entries
    )
    try:
        trust = build_ticket_admission_telemetry_lineage_trust(trust_keys)
    except TicketAdmissionTelemetryLineageTrustError as error:
        message = f"cannot build resolved lineage trust: {error}"
        raise TicketAdmissionTelemetryLineageTrustManifestError(
            message
        ) from error
    return TicketAdmissionTelemetryLineageResolvedTrust(
        manifest_fingerprint=(
            ticket_admission_telemetry_lineage_trust_manifest_fingerprint(
                validated_manifest
            )
        ),
        trust=trust,
    )


def _validated_manifest(
    manifest: TicketAdmissionTelemetryLineageTrustManifest,
) -> TicketAdmissionTelemetryLineageTrustManifest:
    if type(manifest) is not TicketAdmissionTelemetryLineageTrustManifest:
        _raise_manifest("manifest must use the exact trust manifest type")
    _validate_manifest_header(manifest)
    _validate_manifest_entries(manifest.entries)
    return manifest


def _validate_manifest_header(
    manifest: TicketAdmissionTelemetryLineageTrustManifest,
) -> None:
    if (
        manifest.manifest_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_MANIFEST_ID
    ):
        _raise_manifest("manifest identity is unsupported")
    if (
        type(manifest.schema_version) is not int
        or manifest.schema_version
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_TRUST_MANIFEST_SCHEMA_VERSION
    ):
        _raise_manifest("manifest schema is unsupported")


def _validate_manifest_entries(
    entries: tuple[TicketAdmissionTelemetryLineageTrustManifestEntry, ...],
) -> None:
    _validate_entry_inputs(
        entries,
        max_entries=DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_MANIFEST_ENTRIES,
    )
    previous_key_id: str | None = None
    reference_ids: set[str] = set()
    for entry in entries:
        validated = _validated_entry(entry)
        if previous_key_id is not None and validated.key_id <= previous_key_id:
            _raise_manifest("manifest entries must be uniquely ordered by key")
        if validated.key_reference_id in reference_ids:
            _raise_manifest("duplicate key reference identity")
        previous_key_id = validated.key_id
        reference_ids.add(validated.key_reference_id)


def _validate_entry_inputs(
    entries: tuple[TicketAdmissionTelemetryLineageTrustManifestEntry, ...],
    *,
    max_entries: int,
) -> None:
    if type(entries) is not tuple:
        _raise_manifest("entries must use the exact immutable tuple type")
    limit = _validated_positive_limit(max_entries, "entry limit")
    if len(entries) > limit:
        _raise_manifest("entry count exceeds configured limit")


def _validated_entry(
    entry: TicketAdmissionTelemetryLineageTrustManifestEntry,
) -> TicketAdmissionTelemetryLineageTrustManifestEntry:
    if type(entry) is not TicketAdmissionTelemetryLineageTrustManifestEntry:
        _raise_manifest("entry must use the exact manifest entry type")
    _ = _validated_identifier(entry.key_id, "key identity")
    _ = _validated_identifier(entry.key_reference_id, "key reference identity")
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
    secrets: tuple[TicketAdmissionTelemetryLineageResolvedSecret, ...],
) -> dict[str, TicketAdmissionTelemetryLineageResolvedSecret]:
    _validate_resolution_inputs(secrets)
    resolved_by_key: dict[
        str,
        TicketAdmissionTelemetryLineageResolvedSecret,
    ] = {}
    reference_ids: set[str] = set()
    for secret in secrets:
        validated = _validated_resolution(secret)
        _insert_resolution(validated, resolved_by_key, reference_ids)
    return resolved_by_key


def _validate_resolution_inputs(
    secrets: tuple[TicketAdmissionTelemetryLineageResolvedSecret, ...],
) -> None:
    if type(secrets) is not tuple:
        _raise_manifest(
            "resolved secrets must use the exact immutable tuple type"
        )
    if len(secrets) > DEFAULT_MAX_TELEMETRY_LINEAGE_TRUST_MANIFEST_ENTRIES:
        _raise_manifest("resolved secret count exceeds configured limit")


def _insert_resolution(
    secret: TicketAdmissionTelemetryLineageResolvedSecret,
    resolved_by_key: dict[str, TicketAdmissionTelemetryLineageResolvedSecret],
    reference_ids: set[str],
) -> None:
    if secret.key_id in resolved_by_key:
        _raise_manifest("duplicate resolved key identity")
    if secret.key_reference_id in reference_ids:
        _raise_manifest("duplicate resolved key reference identity")
    resolved_by_key[secret.key_id] = secret
    reference_ids.add(secret.key_reference_id)


def _validated_resolution(
    secret: TicketAdmissionTelemetryLineageResolvedSecret,
) -> TicketAdmissionTelemetryLineageResolvedSecret:
    if type(secret) is not TicketAdmissionTelemetryLineageResolvedSecret:
        _raise_manifest("resolved secret must use the exact resolution type")
    _ = _validated_identifier(secret.key_id, "resolved key identity")
    _ = _validated_identifier(
        secret.key_reference_id,
        "resolved key reference identity",
    )
    if type(secret.secret_key) is not bytes:
        _raise_manifest("resolved secret key must use the exact bytes type")
    return secret


def _resolved_trust_key(
    entry: TicketAdmissionTelemetryLineageTrustManifestEntry,
    resolved_by_key: dict[str, TicketAdmissionTelemetryLineageResolvedSecret],
) -> TicketAdmissionTelemetryLineageTrustKey:
    secret = resolved_by_key.get(entry.key_id)
    if secret is None:
        _raise_manifest("manifest key identity has no resolved secret")
    if secret.key_reference_id != entry.key_reference_id:
        _raise_manifest("resolved key reference does not match manifest")
    return TicketAdmissionTelemetryLineageTrustKey(
        first_capture_sequence_id=entry.first_capture_sequence_id,
        key_id=entry.key_id,
        last_capture_sequence_id=entry.last_capture_sequence_id,
        secret_key=secret.secret_key,
    )


def _manifest_from_mapping(
    mapping: dict[str, object],
    *,
    max_entries: int,
) -> TicketAdmissionTelemetryLineageTrustManifest:
    _expect_exact_keys(mapping, _ROOT_KEYS, "trust manifest")
    raw_entries = _expect_list(mapping["entries"], "trust manifest.entries")
    if len(raw_entries) > max_entries:
        _raise_manifest("entry count exceeds configured limit")
    entries = tuple(
        _entry_from_mapping(value, index)
        for index, value in enumerate(raw_entries)
    )
    built = build_ticket_admission_telemetry_lineage_trust_manifest(
        entries,
        max_entries=max_entries,
    )
    manifest_id = _expect_string(
        mapping["manifest_id"],
        "trust manifest.manifest_id",
    )
    schema_version = _expect_int(
        mapping["schema_version"],
        "trust manifest.schema_version",
    )
    return _validated_manifest(
        TicketAdmissionTelemetryLineageTrustManifest(
            entries=built.entries,
            manifest_id=manifest_id,
            schema_version=schema_version,
        )
    )


def _entry_from_mapping(
    value: object,
    index: int,
) -> TicketAdmissionTelemetryLineageTrustManifestEntry:
    context = f"trust manifest.entries[{index}]"
    mapping = _expect_mapping(value, context)
    _expect_exact_keys(mapping, _ENTRY_KEYS, context)
    return TicketAdmissionTelemetryLineageTrustManifestEntry(
        first_capture_sequence_id=_expect_int(
            mapping["first_capture_sequence_id"],
            f"{context}.first_capture_sequence_id",
        ),
        key_id=_expect_string(mapping["key_id"], f"{context}.key_id"),
        key_reference_id=_expect_string(
            mapping["key_reference_id"],
            f"{context}.key_reference_id",
        ),
        last_capture_sequence_id=_expect_optional_int(
            mapping["last_capture_sequence_id"],
            f"{context}.last_capture_sequence_id",
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
        message = "ticket admission telemetry trust manifest is not UTF-8"
        raise TicketAdmissionTelemetryLineageTrustManifestError(
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
        message = "ticket admission telemetry trust manifest is not valid JSON"
        raise TicketAdmissionTelemetryLineageTrustManifestError(
            message
        ) from error
    return _expect_mapping(parsed, "trust manifest")


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
        message = f"cannot write trust manifest: {error}"
        raise TicketAdmissionTelemetryLineageTrustManifestError(
            message
        ) from error
    return temporary


def _remove_temporary(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def _raise_manifest(detail: str) -> Never:
    message = f"ticket admission telemetry lineage trust manifest {detail}"
    raise TicketAdmissionTelemetryLineageTrustManifestError(message)
