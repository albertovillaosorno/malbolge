# File:
#   - ticket_admission_telemetry_lineage_public_key_bundle.py
# Path:
#   - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
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
#   - Canonical explicit file bundles for bounded detached public keys.
# - Must-Not:
#   - Discover paths, load automatically, retry, watch, cache, fetch network
#     data, validate certificates, select algorithms, or change policy.
# - Allows:
#   - Inputs: explicit entries, provider identities, bytes, and file paths.
#   - Outputs: canonical bundles and caller-owned in-memory key providers.
#   - Side effects: explicit bounded reads and atomic replacement only.
# - Split-When:
#   - Split when native async HTTPS, concrete Authorization providers,
#     async Authorization injection, hosted APIs, certificates, or PKI gain
#     contracts.
# - Merge-When:
#   - Merge when another module owns this exact canonical key-bundle boundary.
# - Summary:
#   - Explicit canonical external bundles for detached public keys.
# - Description:
#   - Reuses the bounded memory provider for key validation and lookup.
# - Usage:
#   - Read one caller-selected path, then pass the loaded provider explicitly.
# - Defaults:
#   - At most 256 keys and 1 MiB of canonical compact UTF-8 JSON.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
# - docs/research/algorithms/adaptive-accelerator-resource-budgeting/research.md
#
# Large file:
#   - false
#

"""Canonical explicit bundles for detached public-key provider state."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from hashlib import sha256
import json
from pathlib import Path
from secrets import token_hex
from typing import Final
from typing import Never
from typing import cast

from accelerator import (
    ticket_admission_telemetry_lineage_memory_public_key_provider as memory,
)

_BUNDLE_ID: Final = "ticket-admission-telemetry-lineage-public-key-bundle-v1"
TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_ID: Final = _BUNDLE_ID
TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_SCHEMA_VERSION: Final = 1
_BUNDLE_FINGERPRINT_PREFIX: Final = f"{_BUNDLE_ID}:sha256:"
DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_BYTES: Final = 1024 * 1024
DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_ENTRIES: Final = (
    memory.DEFAULT_MAX_TELEMETRY_LINEAGE_MEMORY_PUBLIC_KEYS
)
_build_memory: Final = (
    memory.build_ticket_admission_telemetry_lineage_memory_public_key_provider
)
_ROOT_KEYS: Final = frozenset((
    "bundle_id",
    "entries",
    "provider_id",
    "schema_version",
))
_ENTRY_KEYS: Final = frozenset((
    "algorithm_id",
    "first_capture_sequence_id",
    "last_capture_sequence_id",
    "public_key_fingerprint",
    "public_key_hex",
    "public_key_id",
    "public_key_reference_id",
))


class TicketAdmissionTelemetryLineagePublicKeyBundleError(ValueError):
    """An explicit detached public-key bundle is invalid."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePublicKeyBundleEntry:
    """One exact persisted public key and its detached trust metadata."""

    algorithm_id: str
    first_capture_sequence_id: int
    last_capture_sequence_id: int | None
    public_key: bytes = field(repr=False)
    public_key_fingerprint: str
    public_key_id: str
    public_key_reference_id: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineagePublicKeyBundle:
    """Canonical bounded provider state with hidden public-key bytes."""

    bundle_id: str
    entries: tuple[TicketAdmissionTelemetryLineagePublicKeyBundleEntry, ...]
    provider_id: str
    schema_version: int


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryLineageLoadedPublicKeyBundle:
    """Explicit load metadata with a hidden caller-owned memory provider."""

    bundle_fingerprint: str
    byte_count: int
    key_count: int
    provider: memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider = (
        field(repr=False)
    )
    provider_id: str


def ticket_admission_telemetry_lineage_public_key_bundle_id() -> str:
    """Return the stable public-key bundle identity.

    Returns:
        Versioned canonical bundle identity.

    """
    return TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_ID


def build_ticket_admission_telemetry_lineage_public_key_bundle(
    entries: tuple[TicketAdmissionTelemetryLineagePublicKeyBundleEntry, ...],
    *,
    provider_id: str,
    max_entries: int = DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_ENTRIES,
) -> TicketAdmissionTelemetryLineagePublicKeyBundle:
    """Build one canonical bundle from exact caller-owned public keys.

    Returns:
        Provider-reference-ordered canonical bundle.

    """
    provider = _build_memory_provider(
        entries,
        provider_id=provider_id,
        max_entries=max_entries,
    )
    return TicketAdmissionTelemetryLineagePublicKeyBundle(
        bundle_id=TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_ID,
        entries=tuple(_bundle_entry(entry) for entry in provider.entries),
        provider_id=provider.provider_id,
        schema_version=(
            TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_SCHEMA_VERSION
        ),
    )


def encode_ticket_admission_telemetry_lineage_public_key_bundle(
    bundle: TicketAdmissionTelemetryLineagePublicKeyBundle,
) -> bytes:
    """Encode one validated bundle as canonical compact UTF-8 JSON.

    Returns:
        Sorted-key JSON bytes with one trailing newline.

    """
    validated = _validated_bundle(bundle)
    mapping: dict[str, object] = {
        "bundle_id": validated.bundle_id,
        "entries": [_entry_mapping(entry) for entry in validated.entries],
        "provider_id": validated.provider_id,
        "schema_version": validated.schema_version,
    }
    text = json.dumps(
        mapping,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{text}\n".encode()


def decode_ticket_admission_telemetry_lineage_public_key_bundle(
    data: bytes,
    *,
    max_bytes: int = DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_BYTES,
    max_entries: int = DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_ENTRIES,
) -> TicketAdmissionTelemetryLineagePublicKeyBundle:
    """Decode one canonical bounded public-key bundle.

    Returns:
        Exact validated canonical bundle.

    """
    byte_limit = _validated_positive_limit(max_bytes, "byte limit")
    entry_limit = _validated_positive_limit(max_entries, "entry limit")
    payload = _validated_payload(data, max_bytes=byte_limit)
    bundle = _bundle_from_mapping(
        _json_mapping(payload),
        max_entries=entry_limit,
    )
    if (
        encode_ticket_admission_telemetry_lineage_public_key_bundle(bundle)
        != data
    ):
        _raise_bundle("bundle bytes are not canonical")
    return bundle


def ticket_admission_telemetry_lineage_public_key_bundle_fingerprint(
    bundle: TicketAdmissionTelemetryLineagePublicKeyBundle,
) -> str:
    """Return the SHA-256 identity of canonical bundle bytes.

    Returns:
        Versioned bundle fingerprint.

    """
    digest = sha256(
        encode_ticket_admission_telemetry_lineage_public_key_bundle(bundle)
    ).hexdigest()
    prefix = _BUNDLE_FINGERPRINT_PREFIX
    return f"{prefix}{digest}"


def write_ticket_admission_telemetry_lineage_public_key_bundle(
    path: Path,
    bundle: TicketAdmissionTelemetryLineagePublicKeyBundle,
) -> None:
    """Atomically replace one explicit path with canonical bundle bytes."""
    destination = _validated_path(path)
    payload = encode_ticket_admission_telemetry_lineage_public_key_bundle(
        bundle
    )
    if len(payload) > DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_BYTES:
        _raise_bundle("bundle exceeds default byte limit")
    temporary = destination.with_name(f".{destination.name}.{token_hex(8)}.tmp")
    try:
        with temporary.open("xb") as output_file:
            _ = output_file.write(payload)
            output_file.flush()
        _ = temporary.replace(destination)
    except OSError as error:
        _remove_temporary(temporary)
        _raise_bundle_from("cannot atomically write public-key bundle", error)


def read_ticket_admission_telemetry_lineage_public_key_bundle(
    path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_BYTES,
    max_entries: int = DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_ENTRIES,
) -> TicketAdmissionTelemetryLineagePublicKeyBundle:
    """Read one caller-selected path under explicit bounded limits.

    Returns:
        Validated canonical public-key bundle.

    """
    source = _validated_path(path)
    byte_limit = _validated_positive_limit(max_bytes, "byte limit")
    try:
        with source.open("rb") as input_file:
            payload = input_file.read(byte_limit + 1)
    except OSError as error:
        _raise_bundle_from("cannot read public-key bundle", error)
    return decode_ticket_admission_telemetry_lineage_public_key_bundle(
        payload,
        max_bytes=byte_limit,
        max_entries=max_entries,
    )


def materialize_ticket_admission_public_key_bundle_provider(
    bundle: TicketAdmissionTelemetryLineagePublicKeyBundle,
    *,
    max_entries: int = DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_ENTRIES,
) -> TicketAdmissionTelemetryLineageLoadedPublicKeyBundle:
    """Build one caller-owned memory provider from an explicit decoded bundle.

    Returns:
        Stable bundle metadata and hidden bounded memory provider.

    """
    payload = encode_ticket_admission_telemetry_lineage_public_key_bundle(
        bundle
    )
    provider = _memory_provider_for_bundle(bundle, max_entries=max_entries)
    return TicketAdmissionTelemetryLineageLoadedPublicKeyBundle(
        bundle_fingerprint=(
            ticket_admission_telemetry_lineage_public_key_bundle_fingerprint(
                bundle
            )
        ),
        byte_count=len(payload),
        key_count=provider.key_count,
        provider=provider,
        provider_id=provider.provider_id,
    )


_materialize_provider: Final = (
    materialize_ticket_admission_public_key_bundle_provider
)


def load_ticket_admission_telemetry_lineage_public_key_bundle_provider(
    path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_BYTES,
    max_entries: int = DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_ENTRIES,
) -> TicketAdmissionTelemetryLineageLoadedPublicKeyBundle:
    """Read one explicit bundle and build one caller-owned memory provider.

    Returns:
        Stable load metadata and hidden bounded memory provider.

    """
    bundle = read_ticket_admission_telemetry_lineage_public_key_bundle(
        path,
        max_bytes=max_bytes,
        max_entries=max_entries,
    )
    return _materialize_provider(
        bundle,
        max_entries=max_entries,
    )


def _validated_bundle(
    bundle: TicketAdmissionTelemetryLineagePublicKeyBundle,
) -> TicketAdmissionTelemetryLineagePublicKeyBundle:
    if type(bundle) is not TicketAdmissionTelemetryLineagePublicKeyBundle:
        _raise_bundle("bundle must use the exact bundle type")
    if (
        bundle.bundle_id
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_ID
    ):
        _raise_bundle("bundle identity is unsupported")
    if (
        type(bundle.schema_version) is not int
        or bundle.schema_version
        != TICKET_ADMISSION_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_SCHEMA_VERSION
    ):
        _raise_bundle("bundle schema is unsupported")
    rebuilt = build_ticket_admission_telemetry_lineage_public_key_bundle(
        bundle.entries,
        provider_id=bundle.provider_id,
    )
    if rebuilt != bundle:
        _raise_bundle("bundle entries are not canonical")
    return bundle


def _build_memory_provider(
    entries: tuple[TicketAdmissionTelemetryLineagePublicKeyBundleEntry, ...],
    *,
    provider_id: str,
    max_entries: int,
) -> memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider:
    if type(entries) is not tuple:
        _raise_bundle("entries must use the exact immutable tuple type")
    entry_limit = _validated_positive_limit(max_entries, "entry limit")
    memory_entries = tuple(_memory_entry(entry) for entry in entries)
    try:
        return _build_memory(
            memory_entries,
            provider_id=provider_id,
            max_keys=entry_limit,
        )
    except (
        memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProviderError
    ) as error:
        _raise_bundle_from("cannot build bundle memory provider", error)


def _memory_provider_for_bundle(
    bundle: TicketAdmissionTelemetryLineagePublicKeyBundle,
    *,
    max_entries: int,
) -> memory.TicketAdmissionTelemetryLineageMemoryPublicKeyProvider:
    validated = _validated_bundle(bundle)
    return _build_memory_provider(
        validated.entries,
        provider_id=validated.provider_id,
        max_entries=max_entries,
    )


def _memory_entry(
    entry: TicketAdmissionTelemetryLineagePublicKeyBundleEntry,
) -> memory.TicketAdmissionTelemetryLineageMemoryPublicKeyEntry:
    if type(entry) is not TicketAdmissionTelemetryLineagePublicKeyBundleEntry:
        _raise_bundle("entry must use the exact bundle entry type")
    return memory.TicketAdmissionTelemetryLineageMemoryPublicKeyEntry(
        algorithm_id=entry.algorithm_id,
        first_capture_sequence_id=entry.first_capture_sequence_id,
        last_capture_sequence_id=entry.last_capture_sequence_id,
        public_key=entry.public_key,
        public_key_fingerprint=entry.public_key_fingerprint,
        public_key_id=entry.public_key_id,
        public_key_reference_id=entry.public_key_reference_id,
    )


def _bundle_entry(
    entry: memory.TicketAdmissionTelemetryLineageMemoryPublicKeyEntry,
) -> TicketAdmissionTelemetryLineagePublicKeyBundleEntry:
    return TicketAdmissionTelemetryLineagePublicKeyBundleEntry(
        algorithm_id=entry.algorithm_id,
        first_capture_sequence_id=entry.first_capture_sequence_id,
        last_capture_sequence_id=entry.last_capture_sequence_id,
        public_key=entry.public_key,
        public_key_fingerprint=entry.public_key_fingerprint,
        public_key_id=entry.public_key_id,
        public_key_reference_id=entry.public_key_reference_id,
    )


def _entry_mapping(
    entry: TicketAdmissionTelemetryLineagePublicKeyBundleEntry,
) -> dict[str, object]:
    return {
        "algorithm_id": entry.algorithm_id,
        "first_capture_sequence_id": entry.first_capture_sequence_id,
        "last_capture_sequence_id": entry.last_capture_sequence_id,
        "public_key_fingerprint": entry.public_key_fingerprint,
        "public_key_hex": entry.public_key.hex(),
        "public_key_id": entry.public_key_id,
        "public_key_reference_id": entry.public_key_reference_id,
    }


def _bundle_from_mapping(
    mapping: dict[str, object],
    *,
    max_entries: int,
) -> TicketAdmissionTelemetryLineagePublicKeyBundle:
    _expect_exact_keys(mapping, _ROOT_KEYS, "public-key bundle")
    raw_entries = _expect_list(mapping["entries"], "public-key bundle.entries")
    if len(raw_entries) > max_entries:
        _raise_bundle("entry count exceeds configured limit")
    entries = tuple(
        _entry_from_mapping(value, index)
        for index, value in enumerate(raw_entries)
    )
    built = build_ticket_admission_telemetry_lineage_public_key_bundle(
        entries,
        provider_id=_expect_string(
            mapping["provider_id"],
            "public-key bundle.provider_id",
        ),
        max_entries=max_entries,
    )
    candidate = TicketAdmissionTelemetryLineagePublicKeyBundle(
        bundle_id=_expect_string(
            mapping["bundle_id"],
            "public-key bundle.bundle_id",
        ),
        entries=built.entries,
        provider_id=built.provider_id,
        schema_version=_expect_int(
            mapping["schema_version"],
            "public-key bundle.schema_version",
        ),
    )
    return _validated_bundle(candidate)


def _entry_from_mapping(
    value: object,
    index: int,
) -> TicketAdmissionTelemetryLineagePublicKeyBundleEntry:
    context = f"public-key bundle.entries[{index}]"
    mapping = _expect_mapping(value, context)
    _expect_exact_keys(mapping, _ENTRY_KEYS, context)
    return TicketAdmissionTelemetryLineagePublicKeyBundleEntry(
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
        public_key=_decoded_public_key_hex(
            mapping["public_key_hex"],
            context=f"{context}.public_key_hex",
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


def _decoded_public_key_hex(value: object, *, context: str) -> bytes:
    encoded = _expect_string(value, context)
    if not encoded:
        _raise_bundle(f"{context} cannot be empty")
    try:
        decoded = bytes.fromhex(encoded)
    except ValueError as error:
        _raise_bundle_from(f"{context} must use hexadecimal bytes", error)
    if decoded.hex() != encoded:
        _raise_bundle(f"{context} must use canonical lowercase hexadecimal")
    return decoded


def _validated_payload(data: bytes, *, max_bytes: int) -> bytes:
    if type(data) is not bytes:
        _raise_bundle("bundle payload must use the exact bytes type")
    if not data:
        _raise_bundle("bundle payload cannot be empty")
    if len(data) > max_bytes:
        _raise_bundle("bundle exceeds configured byte limit")
    return data


def _json_mapping(data: bytes) -> dict[str, object]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        _raise_bundle_from("public-key bundle is not UTF-8", error)
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
        _raise_bundle_from("public-key bundle is not valid JSON", error)
    return _expect_mapping(parsed, "public-key bundle")


def _reject_duplicate_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    mapping: dict[str, object] = {}
    for key, value in pairs:
        if key in mapping:
            _raise_bundle(f"duplicate JSON key: {key}")
        mapping[key] = value
    return mapping


def _reject_json_constant(value: str) -> Never:
    _raise_bundle(f"invalid JSON constant: {value}")


def _expect_mapping(value: object, context: str) -> dict[str, object]:
    if type(value) is not dict:
        _raise_bundle(f"{context} must be an object")
    return cast("dict[str, object]", value)


def _expect_list(value: object, context: str) -> list[object]:
    if type(value) is not list:
        _raise_bundle(f"{context} must be an array")
    return cast("list[object]", value)


def _expect_string(value: object, context: str) -> str:
    if type(value) is not str:
        _raise_bundle(f"{context} must be a string")
    return value


def _expect_int(value: object, context: str) -> int:
    if type(value) is not int:
        _raise_bundle(f"{context} must be an integer")
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
    if frozenset(mapping) != expected:
        _raise_bundle(f"{context} keys are unsupported")


def _validated_path(path: object) -> Path:
    if not isinstance(path, Path):
        _raise_bundle("path must use pathlib.Path")
    return path


def _remove_temporary(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def _validated_positive_limit(value: int, field_name: str) -> int:
    if type(value) is not int or value <= 0:
        _raise_bundle(f"{field_name} must be a positive integer")
    return value


def _raise_bundle_from(detail: str, error: Exception) -> Never:
    message = f"ticket admission telemetry lineage public-key bundle {detail}"
    raise TicketAdmissionTelemetryLineagePublicKeyBundleError(
        message
    ) from error


def _raise_bundle(detail: str) -> Never:
    message = f"ticket admission telemetry lineage public-key bundle {detail}"
    raise TicketAdmissionTelemetryLineagePublicKeyBundleError(message)
