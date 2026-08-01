# File:
#   - test_ticket_admission_public_key_bundle.py
# Path:
#   - tests/optimizer/test_ticket_admission_public_key_bundle.py
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
#   - Canonical explicit public-key bundle regressions.
# - Must-Not:
#   - Require CUDA, network, discovery, retry, secure cryptography,
#     certificates, PKI, or admission-policy changes.
# - Allows:
#   - Inputs: synthetic entries, JSON bytes, paths, keys, and tampering.
#   - Outputs: canonical, bounded, load, integration, and failure assertions.
#   - Side effects: temporary-directory file creation only.
# - Split-When:
#   - Split when native async HTTPS, concrete credential providers,
#     hosted APIs, certificates, or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact canonical bundle boundary.
# - Summary:
#   - Explicit file-backed detached public-key bundle regressions.
# - Description:
#   - Proves each explicit load rebuilds exact caller-owned memory state.
# - Usage:
#   - Runs without accelerator hardware or external network services.
# - Defaults:
#   - Uses two synthetic public-key byte strings and bounded temporary files.
#
# Related documents:
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_provider.py
# - accelerator/ticket_admission_telemetry_lineage_https_authorized_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_auth_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_https_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_async_bundle_fetcher.py
# - accelerator/ticket_admission_telemetry_lineage_memory_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_public_key_provider.py
# - accelerator/ticket_admission_telemetry_lineage_signature_trust_manifest.py
#
# Large file:
#   - false
#

"""Canonical explicit detached public-key bundle tests."""

# ruff: file-ignore[line-too-long,undocumented-public-function]

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from json import dumps
from json import loads
from typing import TYPE_CHECKING
from typing import cast

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle as bundle,
)
from accelerator import (
    ticket_admission_telemetry_lineage_signature_trust_manifest as manifest,
)
from accelerator.ticket_admission_telemetry_lineage_public_key_provider import (
    resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider,
)
from accelerator.ticket_admission_telemetry_lineage_signature import (
    ticket_admission_telemetry_lineage_public_key_fingerprint,
)

BundleError = bundle.TicketAdmissionTelemetryLineagePublicKeyBundleError
BundleEntry = bundle.TicketAdmissionTelemetryLineagePublicKeyBundleEntry
PublicKeyBundle = bundle.TicketAdmissionTelemetryLineagePublicKeyBundle
LoadedBundle = bundle.TicketAdmissionTelemetryLineageLoadedPublicKeyBundle
ManifestEntry = (
    manifest.TicketAdmissionTelemetryLineageSignatureTrustManifestEntry
)
_build_bundle = (
    bundle.build_ticket_admission_telemetry_lineage_public_key_bundle
)
_decode_bundle = (
    bundle.decode_ticket_admission_telemetry_lineage_public_key_bundle
)
_encode_bundle = (
    bundle.encode_ticket_admission_telemetry_lineage_public_key_bundle
)
_bundle_fingerprint = (
    bundle.ticket_admission_telemetry_lineage_public_key_bundle_fingerprint
)
_load_provider = (
    bundle.load_ticket_admission_telemetry_lineage_public_key_bundle_provider
)
_materialize_provider = (
    bundle.materialize_ticket_admission_public_key_bundle_provider
)
_read_bundle = bundle.read_ticket_admission_telemetry_lineage_public_key_bundle
_write_bundle = (
    bundle.write_ticket_admission_telemetry_lineage_public_key_bundle
)
_resolve_provider = (
    resolve_ticket_admission_telemetry_lineage_signature_trust_with_provider
)

BUNDLE_ID = "ticket-admission-telemetry-lineage-public-key-bundle-v1"
BUNDLE_PREFIX = f"{BUNDLE_ID}:sha256:"
PROVIDER_ID = "provider.test.file-public-keys"
OTHER_PROVIDER_ID = "provider.test.other-public-keys"
OLD_ALGORITHM_ID = "test-only-public-digest-v1"
NEW_ALGORITHM_ID = "test-only-public-digest-v2"
OLD_KEY_ID = "public.test-key.2026-07"
NEW_KEY_ID = "public.test-key.2026-08"
OLD_REFERENCE_ID = "vault.public-key.2026-07"
NEW_REFERENCE_ID = "vault.public-key.2026-08"
UNKNOWN_REFERENCE_ID = "vault.public-key.unknown"
OLD_PUBLIC_KEY = b"caller-owned-old-test-public-key"
NEW_PUBLIC_KEY = b"caller-owned-new-test-public-key"
REPLACEMENT_PUBLIC_KEY = b"caller-owned-replacement-public-key"
WRONG_PUBLIC_KEY = b"caller-owned-wrong-test-public-key"
PUBLIC_KEY_FIELD = b"public_key=b"
PROVIDER_FIELD = b"provider="
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
TWO_KEYS = 2
SCHEMA_VERSION = 1
EXPECTED_EMPTY_BUNDLE = (
    b'{"bundle_id":"ticket-admission-telemetry-lineage-public-key-bundle-v1",'
    b'"entries":[],"provider_id":"provider.test.file-public-keys",'
    b'"schema_version":1}\n'
)
PUBLIC_KEY_HEX_FIELD = b'"public_key_hex":"'
MISSING_MUTATION = "missing"
UNKNOWN_MUTATION = "unknown"
SPACES_MUTATION = "spaces"
ORDER_MUTATION = "order"
NEWLINE_MUTATION = "newline"


def _fingerprint(public_key: bytes) -> str:
    return ticket_admission_telemetry_lineage_public_key_fingerprint(public_key)


def _entry(  # ruff: ignore[too-many-arguments]
    *,
    algorithm_id: str = OLD_ALGORITHM_ID,
    public_key: bytes = OLD_PUBLIC_KEY,
    public_key_fingerprint: str | None = None,
    public_key_id: str = OLD_KEY_ID,
    public_key_reference_id: str = OLD_REFERENCE_ID,
    window: tuple[int, int | None] = (GENESIS_SEQUENCE_ID, GENESIS_SEQUENCE_ID),
) -> BundleEntry:
    first_capture_sequence_id, last_capture_sequence_id = window
    return BundleEntry(
        algorithm_id=algorithm_id,
        first_capture_sequence_id=first_capture_sequence_id,
        last_capture_sequence_id=last_capture_sequence_id,
        public_key=public_key,
        public_key_fingerprint=(
            _fingerprint(public_key)
            if public_key_fingerprint is None
            else public_key_fingerprint
        ),
        public_key_id=public_key_id,
        public_key_reference_id=public_key_reference_id,
    )


def _entries(*, same_key_id: bool = False) -> tuple[BundleEntry, ...]:
    return (
        _entry(
            algorithm_id=NEW_ALGORITHM_ID,
            public_key=NEW_PUBLIC_KEY,
            public_key_id=(OLD_KEY_ID if same_key_id else NEW_KEY_ID),
            public_key_reference_id=NEW_REFERENCE_ID,
            window=(SUCCESSOR_SEQUENCE_ID, None),
        ),
        _entry(),
    )


def _bundle(
    *,
    entries: tuple[BundleEntry, ...] | None = None,
    provider_id: str = PROVIDER_ID,
) -> PublicKeyBundle:
    return _build_bundle(
        _entries() if entries is None else entries,
        provider_id=provider_id,
    )


def _manifest(
    *,
    same_key_id: bool = False,
    replacement_key: bool = False,
) -> manifest.TicketAdmissionTelemetryLineageSignatureTrustManifest:
    old_key = REPLACEMENT_PUBLIC_KEY if replacement_key else OLD_PUBLIC_KEY
    return manifest.build_ticket_admission_telemetry_lineage_signature_trust_manifest((
        ManifestEntry(
            algorithm_id=NEW_ALGORITHM_ID,
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            last_capture_sequence_id=None,
            public_key_fingerprint=_fingerprint(NEW_PUBLIC_KEY),
            public_key_id=(OLD_KEY_ID if same_key_id else NEW_KEY_ID),
            public_key_reference_id=NEW_REFERENCE_ID,
        ),
        ManifestEntry(
            algorithm_id=OLD_ALGORITHM_ID,
            first_capture_sequence_id=GENESIS_SEQUENCE_ID,
            last_capture_sequence_id=GENESIS_SEQUENCE_ID,
            public_key_fingerprint=_fingerprint(old_key),
            public_key_id=OLD_KEY_ID,
            public_key_reference_id=OLD_REFERENCE_ID,
        ),
    ))


def _mapping(encoded: bytes) -> dict[str, object]:
    return cast("dict[str, object]", loads(encoded.decode("utf-8")))


def _encoded_mapping(mapping: dict[str, object]) -> bytes:
    text = dumps(
        mapping,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{text}\n".encode()


def _write(path: Path, value: PublicKeyBundle | None = None) -> bytes:
    built = _bundle() if value is None else value
    encoded = _encode_bundle(built)
    _write_bundle(path, built)
    return encoded


def _load(path: Path) -> LoadedBundle:
    return _load_provider(path)


def test_bundle_identity_defaults_and_empty_canonical_bytes_are_stable() -> (
    None
):
    built = _bundle(entries=())
    encoded = _encode_bundle(built)

    assert (
        bundle.ticket_admission_telemetry_lineage_public_key_bundle_id()
        == BUNDLE_ID
    )
    assert built.bundle_id == BUNDLE_ID
    assert built.provider_id == PROVIDER_ID
    assert built.schema_version == SCHEMA_VERSION
    assert built.entries == ()
    assert encoded == EXPECTED_EMPTY_BUNDLE


def test_entries_are_reference_ordered_and_hide_public_key_bytes() -> None:
    built = _bundle()

    representation = repr(built).encode("utf-8")
    entry_representation = repr(built.entries[0]).encode("utf-8")
    assert tuple(entry.public_key_reference_id for entry in built.entries) == (
        OLD_REFERENCE_ID,
        NEW_REFERENCE_ID,
    )
    assert OLD_PUBLIC_KEY not in representation
    assert NEW_PUBLIC_KEY not in representation
    assert OLD_PUBLIC_KEY not in entry_representation
    assert PUBLIC_KEY_FIELD not in representation
    assert PUBLIC_KEY_FIELD not in entry_representation


def test_encode_decode_round_trip_and_fingerprint_are_exact() -> None:
    built = _bundle()
    encoded = _encode_bundle(built)

    decoded = _decode_bundle(encoded)
    fingerprint = _bundle_fingerprint(decoded)

    assert decoded == built
    assert fingerprint == f"{BUNDLE_PREFIX}{sha256(encoded).hexdigest()}"
    assert encoded.endswith(b"\n")
    assert PUBLIC_KEY_HEX_FIELD in encoded
    assert OLD_PUBLIC_KEY.hex().encode() in encoded


def test_same_key_id_under_distinct_algorithms_is_allowed() -> None:
    built = _bundle(entries=_entries(same_key_id=True))

    assert tuple(entry.public_key_id for entry in built.entries) == (
        OLD_KEY_ID,
        OLD_KEY_ID,
    )
    assert tuple(entry.algorithm_id for entry in built.entries) == (
        OLD_ALGORITHM_ID,
        NEW_ALGORITHM_ID,
    )


def test_materialize_bundle_builds_provider_without_path() -> None:
    built = _bundle()

    loaded = _materialize_provider(built)

    assert loaded.bundle_fingerprint == _bundle_fingerprint(built)
    assert loaded.byte_count == len(_encode_bundle(built))
    assert loaded.key_count == TWO_KEYS
    assert loaded.provider_id == PROVIDER_ID
    assert loaded.provider.key_count == TWO_KEYS


def test_explicit_write_read_and_load_are_exact(tmp_path: Path) -> None:
    path = tmp_path / "keys.json"
    encoded = _write(path)

    read_back = _read_bundle(path)
    loaded = _load(path)

    assert path.read_bytes() == encoded
    assert read_back == _bundle()
    assert loaded.bundle_fingerprint == _bundle_fingerprint(read_back)
    assert loaded.byte_count == len(encoded)
    assert loaded.key_count == TWO_KEYS
    assert loaded.provider_id == PROVIDER_ID
    assert loaded.provider.key_count == TWO_KEYS


def test_loaded_bundle_repr_hides_provider_and_key_bytes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "keys.json"
    _ = _write(path)

    loaded = _load(path)
    representation = repr(loaded).encode("utf-8")

    assert OLD_PUBLIC_KEY not in representation
    assert NEW_PUBLIC_KEY not in representation
    assert PUBLIC_KEY_FIELD not in representation
    assert PROVIDER_FIELD not in representation


def test_loaded_provider_builds_manifest_bound_trust(tmp_path: Path) -> None:
    path = tmp_path / "keys.json"
    _ = _write(path)
    loaded = _load(path)

    resolved = _resolve_provider(
        _manifest(),
        loaded.provider,
        provider_id=PROVIDER_ID,
    )

    assert resolved.provider_id == PROVIDER_ID
    assert resolved.request_count == TWO_KEYS
    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)
    assert resolved.public_key_ids == (OLD_KEY_ID, NEW_KEY_ID)
    assert resolved.trust.key_count == TWO_KEYS


def test_empty_bundle_loads_empty_memory_provider(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    _ = _write(path, _bundle(entries=()))

    loaded = _load(path)

    assert loaded.key_count == 0
    assert loaded.provider.entries == ()
    assert loaded.provider.key_count == 0


def test_each_explicit_load_rereads_path_without_cache(tmp_path: Path) -> None:
    path = tmp_path / "keys.json"
    first_bundle = _bundle()
    _ = _write(path, first_bundle)
    first = _load(path)
    replacement_entries = (
        _entry(public_key=REPLACEMENT_PUBLIC_KEY),
        _entries()[0],
    )
    second_bundle = _bundle(entries=replacement_entries)
    _ = _write(path, second_bundle)

    second = _load(path)

    assert first.bundle_fingerprint != second.bundle_fingerprint
    assert first.provider.entries[0].public_key == OLD_PUBLIC_KEY
    assert second.provider.entries[0].public_key == REPLACEMENT_PUBLIC_KEY


def test_atomic_write_replaces_existing_bundle(tmp_path: Path) -> None:
    path = tmp_path / "keys.json"
    _ = _write(path, _bundle(entries=()))
    expected = _write(path, _bundle())

    assert path.read_bytes() == expected
    assert list(tmp_path.glob(".*.tmp")) == []


def test_same_key_id_bundle_loads_and_resolves(tmp_path: Path) -> None:
    path = tmp_path / "keys.json"
    _ = _write(path, _bundle(entries=_entries(same_key_id=True)))
    loaded = _load(path)

    resolved = _resolve_provider(
        _manifest(same_key_id=True),
        loaded.provider,
        provider_id=PROVIDER_ID,
    )

    assert resolved.public_key_ids == (OLD_KEY_ID, OLD_KEY_ID)
    assert resolved.algorithm_ids == (OLD_ALGORITHM_ID, NEW_ALGORITHM_ID)


def test_missing_read_path_has_stable_error_without_path_text(
    tmp_path: Path,
) -> None:
    path = tmp_path / "private-path-name.json"

    with pytest.raises(
        BundleError, match="cannot read public-key bundle"
    ) as caught:
        _ = _read_bundle(path)

    assert path.name not in str(caught.value)


def test_missing_write_parent_has_stable_error_without_path_text(
    tmp_path: Path,
) -> None:
    path = tmp_path / "missing" / "private-path-name.json"

    with pytest.raises(
        BundleError,
        match="cannot atomically write public-key bundle",
    ) as caught:
        _write_bundle(path, _bundle())

    assert path.name not in str(caught.value)


def test_paths_require_pathlib_path() -> None:
    foreign = cast("Path", cast("object", "keys.json"))

    with pytest.raises(BundleError, match=r"path must use pathlib\.Path"):
        _ = _read_bundle(foreign)
    with pytest.raises(BundleError, match=r"path must use pathlib\.Path"):
        _write_bundle(foreign, _bundle())


@pytest.mark.parametrize("limit", [0, True])
def test_byte_limit_requires_positive_exact_integer(limit: int) -> None:
    encoded = _encode_bundle(_bundle())

    with pytest.raises(
        BundleError, match="byte limit must be a positive integer"
    ):
        _ = _decode_bundle(encoded, max_bytes=limit)


@pytest.mark.parametrize("limit", [0, True])
def test_entry_limit_requires_positive_exact_integer(limit: int) -> None:
    encoded = _encode_bundle(_bundle())

    with pytest.raises(
        BundleError, match="entry limit must be a positive integer"
    ):
        _ = _decode_bundle(encoded, max_entries=limit)


def test_payload_requires_exact_nonempty_bytes() -> None:
    with pytest.raises(BundleError, match="exact bytes type"):
        _ = _decode_bundle(cast("bytes", cast("object", bytearray(b"{}\n"))))
    with pytest.raises(BundleError, match="cannot be empty"):
        _ = _decode_bundle(b"")


def test_payload_byte_limit_is_enforced() -> None:
    encoded = _encode_bundle(_bundle())

    assert _decode_bundle(encoded, max_bytes=len(encoded)) == _bundle()
    with pytest.raises(BundleError, match="exceeds configured byte limit"):
        _ = _decode_bundle(encoded, max_bytes=len(encoded) - 1)


def test_entry_limit_is_enforced_before_entry_build() -> None:
    encoded = _encode_bundle(_bundle())

    with pytest.raises(BundleError, match="entry count exceeds"):
        _ = _decode_bundle(encoded, max_entries=1)


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        (b"\xff\n", "not UTF-8"),
        (b"{\n", "not valid JSON"),
        (b"NaN\n", "invalid JSON constant"),
        (b'[["not","object"]]\n', "must be an object"),
    ],
)
def test_invalid_json_payloads_fail_closed(payload: bytes, match: str) -> None:
    with pytest.raises(BundleError, match=match):
        _ = _decode_bundle(payload)


def test_duplicate_json_key_fails_closed() -> None:
    payload = (
        b'{"bundle_id":"a","bundle_id":"b","entries":[],'
        b'"provider_id":"provider.test","schema_version":1}\n'
    )

    with pytest.raises(BundleError, match="duplicate JSON key: bundle_id"):
        _ = _decode_bundle(payload)


@pytest.mark.parametrize("mutation", [MISSING_MUTATION, UNKNOWN_MUTATION])
def test_root_keys_must_be_exact(mutation: str) -> None:
    mapping = _mapping(_encode_bundle(_bundle()))
    if mutation == MISSING_MUTATION:
        del mapping["provider_id"]
    else:
        mapping["unknown"] = True

    with pytest.raises(BundleError, match="bundle keys are unsupported"):
        _ = _decode_bundle(_encoded_mapping(mapping))


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("bundle_id", "unsupported", "bundle identity is unsupported"),
        ("bundle_id", 1, "bundle_id must be a string"),
        ("schema_version", 2, "bundle schema is unsupported"),
        ("schema_version", True, "schema_version must be an integer"),
        ("provider_id", "bad provider", "cannot build bundle memory provider"),
        ("entries", {}, "entries must be an array"),
    ],
)
def test_root_metadata_is_exact(
    field: str,
    value: object,
    match: str,
) -> None:
    mapping = _mapping(_encode_bundle(_bundle()))
    mapping[field] = value

    with pytest.raises(BundleError, match=match):
        _ = _decode_bundle(_encoded_mapping(mapping))


def _first_entry_mapping() -> tuple[dict[str, object], dict[str, object]]:
    mapping = _mapping(_encode_bundle(_bundle()))
    entries = cast("list[object]", mapping["entries"])
    entry = cast("dict[str, object]", entries[0])
    return mapping, entry


def test_entry_must_be_an_object() -> None:
    mapping = _mapping(_encode_bundle(_bundle()))
    entries = cast("list[object]", mapping["entries"])
    entries[0] = "not-an-object"

    with pytest.raises(BundleError, match=r"entries\[0\] must be an object"):
        _ = _decode_bundle(_encoded_mapping(mapping))


@pytest.mark.parametrize("mutation", [MISSING_MUTATION, UNKNOWN_MUTATION])
def test_entry_keys_must_be_exact(mutation: str) -> None:
    mapping, entry = _first_entry_mapping()
    if mutation == MISSING_MUTATION:
        del entry["public_key_id"]
    else:
        entry["unknown"] = True

    with pytest.raises(BundleError, match=r"entries\[0\] keys are unsupported"):
        _ = _decode_bundle(_encoded_mapping(mapping))


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("algorithm_id", 1, "algorithm_id must be a string"),
        (
            "first_capture_sequence_id",
            True,
            "first_capture_sequence_id must be an integer",
        ),
        (
            "last_capture_sequence_id",
            "none",
            "last_capture_sequence_id must be an integer",
        ),
        (
            "public_key_fingerprint",
            1,
            "public_key_fingerprint must be a string",
        ),
        ("public_key_id", 1, "public_key_id must be a string"),
        (
            "public_key_reference_id",
            1,
            "public_key_reference_id must be a string",
        ),
    ],
)
def test_entry_json_field_types_are_exact(
    field: str,
    value: object,
    match: str,
) -> None:
    mapping, entry = _first_entry_mapping()
    entry[field] = value

    with pytest.raises(BundleError, match=match):
        _ = _decode_bundle(_encoded_mapping(mapping))


@pytest.mark.parametrize(
    ("public_key_hex", "match"),
    [
        ("", "public_key_hex cannot be empty"),
        ("zz", "must use hexadecimal bytes"),
        ("0", "must use hexadecimal bytes"),
        (OLD_PUBLIC_KEY.hex().upper(), "canonical lowercase hexadecimal"),
        (f"{OLD_PUBLIC_KEY.hex()} ", "canonical lowercase hexadecimal"),
    ],
)
def test_public_key_hex_must_be_canonical(
    public_key_hex: str,
    match: str,
) -> None:
    mapping, entry = _first_entry_mapping()
    entry["public_key_hex"] = public_key_hex

    with pytest.raises(BundleError, match=match):
        _ = _decode_bundle(_encoded_mapping(mapping))


def test_public_key_hex_requires_string() -> None:
    mapping, entry = _first_entry_mapping()
    entry["public_key_hex"] = 1

    with pytest.raises(BundleError, match="public_key_hex must be a string"):
        _ = _decode_bundle(_encoded_mapping(mapping))


@pytest.mark.parametrize(
    "mutation",
    [SPACES_MUTATION, ORDER_MUTATION, NEWLINE_MUTATION],
)
def test_noncanonical_json_bytes_fail_closed(mutation: str) -> None:
    encoded = _encode_bundle(_bundle())
    mapping = _mapping(encoded)
    if mutation == SPACES_MUTATION:
        payload = dumps(mapping, sort_keys=True).encode() + b"\n"
    elif mutation == ORDER_MUTATION:
        prefix = (
            b'{"schema_version":1,"provider_id":'
            b'"provider.test.file-public-keys",'
        )
        entries = (
            b'"entries":'
            + dumps(
                mapping["entries"],
                separators=(",", ":"),
            ).encode()
        )
        suffix = (
            b',"bundle_id":'
            b'"ticket-admission-telemetry-lineage-public-key-bundle-v1"}\n'
        )
        payload = b"".join((prefix, entries, suffix))
    else:
        payload = encoded.rstrip(b"\n")

    with pytest.raises(BundleError, match="bundle bytes are not canonical"):
        _ = _decode_bundle(payload)


def test_build_entries_require_exact_tuple() -> None:
    entries = cast(
        "tuple[BundleEntry, ...]",
        cast("object", list(_entries())),
    )

    with pytest.raises(BundleError, match="exact immutable tuple"):
        _ = _build_bundle(entries, provider_id=PROVIDER_ID)


@pytest.mark.parametrize("limit", [0, True])
def test_build_entry_limit_requires_positive_exact_integer(limit: int) -> None:
    with pytest.raises(
        BundleError, match="entry limit must be a positive integer"
    ):
        _ = _build_bundle((), provider_id=PROVIDER_ID, max_entries=limit)


def test_build_entry_count_is_bounded() -> None:
    with pytest.raises(
        BundleError, match="cannot build bundle memory provider"
    ):
        _ = _build_bundle(_entries(), provider_id=PROVIDER_ID, max_entries=1)


def test_build_rejects_foreign_entry_type() -> None:
    entries = cast(
        "tuple[BundleEntry, ...]",
        cast("object", (object(),)),
    )

    with pytest.raises(BundleError, match="exact bundle entry type"):
        _ = _build_bundle(entries, provider_id=PROVIDER_ID)


def test_build_rejects_duplicate_composite_identity() -> None:
    duplicate = replace(_entry(), public_key_reference_id=NEW_REFERENCE_ID)

    with pytest.raises(
        BundleError, match="cannot build bundle memory provider"
    ):
        _ = _build_bundle(
            (_entry(), duplicate),
            provider_id=PROVIDER_ID,
        )


def test_build_rejects_duplicate_reference_identity() -> None:
    duplicate = _entry(
        algorithm_id=NEW_ALGORITHM_ID,
        public_key=NEW_PUBLIC_KEY,
        public_key_id=NEW_KEY_ID,
    )

    with pytest.raises(
        BundleError, match="cannot build bundle memory provider"
    ):
        _ = _build_bundle(
            (_entry(), duplicate),
            provider_id=PROVIDER_ID,
        )


def test_build_rejects_wrong_public_key_fingerprint() -> None:
    entry = _entry(public_key_fingerprint=_fingerprint(WRONG_PUBLIC_KEY))

    with pytest.raises(
        BundleError, match="cannot build bundle memory provider"
    ):
        _ = _build_bundle((entry,), provider_id=PROVIDER_ID)


@pytest.mark.parametrize(
    "public_key", [b"", cast("bytes", cast("object", "key"))]
)
def test_build_rejects_invalid_public_key_bytes(public_key: bytes) -> None:
    entry = _entry(
        public_key=public_key,
        public_key_fingerprint=_fingerprint(OLD_PUBLIC_KEY),
    )

    with pytest.raises(
        BundleError, match="cannot build bundle memory provider"
    ):
        _ = _build_bundle((entry,), provider_id=PROVIDER_ID)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("algorithm_id", "bad algorithm"),
        ("public_key_id", ""),
        ("public_key_reference_id", "bad reference"),
        ("first_capture_sequence_id", -1),
        ("last_capture_sequence_id", -1),
    ],
)
def test_build_rejects_invalid_entry_metadata(
    field: str,
    value: object,
) -> None:
    entry = replace(_entry(), **{field: value})

    with pytest.raises(
        BundleError, match="cannot build bundle memory provider"
    ):
        _ = _build_bundle((entry,), provider_id=PROVIDER_ID)


def test_encode_rejects_foreign_bundle_type() -> None:
    with pytest.raises(BundleError, match="exact bundle type"):
        _ = _encode_bundle(cast("PublicKeyBundle", object()))


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("bundle_id", "unsupported", "bundle identity is unsupported"),
        ("schema_version", 2, "bundle schema is unsupported"),
        ("schema_version", True, "bundle schema is unsupported"),
    ],
)
def test_encode_rejects_tampered_bundle_header(
    field: str,
    value: object,
    match: str,
) -> None:
    built = replace(_bundle(), **{field: value})

    with pytest.raises(BundleError, match=match):
        _ = _encode_bundle(built)


def test_encode_rejects_noncanonical_entry_order() -> None:
    built = _bundle()
    tampered = replace(built, entries=tuple(reversed(built.entries)))

    with pytest.raises(BundleError, match="entries are not canonical"):
        _ = _encode_bundle(tampered)


def test_encode_rejects_foreign_entries_tuple() -> None:
    built = replace(
        _bundle(),
        entries=cast(
            "tuple[BundleEntry, ...]",
            cast("object", list(_entries())),
        ),
    )

    with pytest.raises(BundleError, match="exact immutable tuple"):
        _ = _encode_bundle(built)
