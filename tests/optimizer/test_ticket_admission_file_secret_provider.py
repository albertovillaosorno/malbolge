# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Explicit bounded read-only file-secret provider regressions.
# - Must-Not:
#   - Discover paths, write persistent files outside temporary tests, retry,
#     cache secrets, inspect permissions, create workers, or change policy.
# - Allows:
#   - Inputs: synthetic manifests, absolute temporary paths, bytes, and
#     tampering.
#   - Outputs: exact read, bounds, binding, secrecy, and failure assertions.
#   - Side effects: explicit bounded reads of pytest-managed temporary files.
# - Split-When:
#   - Split when native async file I/O, external stores, hosted APIs,
#     certificates, or PKI gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact explicit file-secret behavior.
# - Summary:
#   - Exact read-only file-backed lineage secret-provider regressions.
# - Description:
#   - Proves only exact matched requests perform one bounded raw-byte read.
# - Usage:
#   - Runs without network, external stores, async plugins, or accelerator
#     hardware.
# - Defaults:
#   - Uses two temporary raw-secret files and 256-entry/4096-byte limits.
#

"""Explicit bounded read-only file-secret provider tests."""

# ruff: file-ignore[line-too-long,undocumented-public-function]

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Self
from typing import TYPE_CHECKING
from typing import cast

from accelerator import (
    ticket_admission_telemetry_lineage_file_secret_provider as file_provider,
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

# jig-ignore-next-line: indivisible reviewed identifier
from accelerator.ticket_admission_telemetry_lineage_file_secret_provider import (
    # jig-ignore-next-line: indivisible reviewed identifier
    validate_ticket_admission_telemetry_lineage_file_secret_provider as _validate,
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
import pytest

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch
    from accelerator.ticket_admission_telemetry_lineage_secret_provider import (
        TicketAdmissionTelemetryLineageProviderTrust,
    )
    from accelerator.ticket_admission_telemetry_lineage_trust_manifest import (
        TicketAdmissionTelemetryLineageTrustManifest,
    )

FileProviderError = (
    file_provider.TicketAdmissionTelemetryLineageFileSecretProviderError
)
FileEntry = file_provider.TicketAdmissionTelemetryLineageFileSecretEntry
FileProvider = file_provider.TicketAdmissionTelemetryLineageFileSecretProvider
SecretRequest = port.TicketAdmissionTelemetryLineageSecretRequest
SecretResult = port.TicketAdmissionTelemetryLineageSecretResult
SecretKind = port.TicketAdmissionTelemetryLineageSecretResultKind
_build = (
    file_provider.build_ticket_admission_telemetry_lineage_file_secret_provider
)


_resolve = port.resolve_ticket_admission_telemetry_lineage_trust_with_provider

SERVICE_ID = (
    "explicit-file-ticket-admission-telemetry-lineage-secret-provider-v1"
)
PROVIDER_ID = "provider.test.file-lineage-secrets"
OTHER_PROVIDER_ID = "provider.test.other-lineage-secrets"
OLD_KEY_ID = "local.lineage-key.2026-07"
NEW_KEY_ID = "local.lineage-key.2026-08"
OLD_REFERENCE_ID = "file.lineage-key.2026-07"
NEW_REFERENCE_ID = "file.lineage-key.2026-08"
UNKNOWN_REFERENCE_ID = "file.lineage-key.unknown"
OLD_SECRET = b"o" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
NEW_SECRET = b"n" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
ROTATED_SECRET = b"r" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
VENDOR_DETAIL = "filesystem detail must not cross boundary"
PATH_FIELD = b"secret_path"
SECRET_FIELD = b"secret_key"
RELATIVE_PATH = "relative.secret"
ENTRIES_FIELD = b"entries=("
GENESIS_SEQUENCE_ID = 0
SUCCESSOR_SEQUENCE_ID = 1
ONE_ENTRY = 1
TWO_ENTRIES = 2
DEFAULT_MAX_ENTRIES = 256
MAX_ENTRIES = 4096
DEFAULT_MAX_SECRET_BYTES = MAX_TELEMETRY_LINEAGE_KEY_BYTES


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


def _entry(  # ruff: ignore[too-many-arguments]
    secret_path: Path,
    *,
    first_capture_sequence_id: int = GENESIS_SEQUENCE_ID,
    key_id: str = OLD_KEY_ID,
    key_reference_id: str = OLD_REFERENCE_ID,
    last_capture_sequence_id: int | None = GENESIS_SEQUENCE_ID,
    manifest_fingerprint: str | None = None,
) -> FileEntry:
    return FileEntry(
        first_capture_sequence_id=first_capture_sequence_id,
        key_id=key_id,
        key_reference_id=key_reference_id,
        last_capture_sequence_id=last_capture_sequence_id,
        manifest_fingerprint=(
            _manifest_fingerprint()
            if manifest_fingerprint is None
            else manifest_fingerprint
        ),
        secret_path=str(secret_path.absolute()),
    )


def _entries(tmp_path: Path) -> tuple[FileEntry, ...]:
    return (
        _entry(
            tmp_path / "new.secret",
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            key_id=NEW_KEY_ID,
            key_reference_id=NEW_REFERENCE_ID,
            last_capture_sequence_id=None,
        ),
        _entry(tmp_path / "old.secret"),
    )


def _write_secrets(tmp_path: Path) -> None:
    _ = (tmp_path / "old.secret").write_bytes(OLD_SECRET)
    _ = (tmp_path / "new.secret").write_bytes(NEW_SECRET)


def _service(  # ruff: ignore[too-many-arguments]
    tmp_path: Path,
    *,
    entries: tuple[FileEntry, ...] | None = None,
    provider_id: str = PROVIDER_ID,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    max_secret_bytes: int = DEFAULT_MAX_SECRET_BYTES,
    write_secrets: bool = True,
) -> FileProvider:
    if write_secrets:
        _write_secrets(tmp_path)
    return _build(
        _entries(tmp_path) if entries is None else entries,
        provider_id=provider_id,
        max_entries=max_entries,
        max_secret_bytes=max_secret_bytes,
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


def _resolve_service(
    service: FileProvider,
) -> TicketAdmissionTelemetryLineageProviderTrust:
    return _resolve(
        _manifest(),
        service,
        provider_id=PROVIDER_ID,
    )


def test_identity_limits_metadata_and_repr_are_stable(tmp_path: Path) -> None:
    service = _service(tmp_path)
    representation = repr(service).encode("utf-8")
    entry_representation = repr(service.entries[0]).encode("utf-8")

    assert (
        # jig-ignore-next-line: indivisible reviewed identifier
        file_provider.ticket_admission_telemetry_lineage_file_secret_provider_id()
        == SERVICE_ID
    )
    assert (
        file_provider.DEFAULT_MAX_TELEMETRY_LINEAGE_FILE_SECRETS
        == DEFAULT_MAX_ENTRIES
    )
    assert file_provider.MAX_TELEMETRY_LINEAGE_FILE_SECRETS == MAX_ENTRIES
    assert (
        file_provider.DEFAULT_MAX_TELEMETRY_LINEAGE_FILE_SECRET_BYTES
        == DEFAULT_MAX_SECRET_BYTES
    )
    assert service.service_id == SERVICE_ID
    assert service.provider_id == PROVIDER_ID
    assert service.secret_count == TWO_ENTRIES
    assert service.max_entries == DEFAULT_MAX_ENTRIES
    assert service.max_secret_bytes == DEFAULT_MAX_SECRET_BYTES
    assert _validate(service) is service
    assert str(tmp_path).encode() not in representation
    assert PATH_FIELD not in entry_representation
    assert ENTRIES_FIELD not in representation


def test_builder_canonically_orders_entries(tmp_path: Path) -> None:
    service = _service(tmp_path, write_secrets=False)

    assert tuple(entry.key_reference_id for entry in service.entries) == (
        OLD_REFERENCE_ID,
        NEW_REFERENCE_ID,
    )


def test_builder_does_not_read_files(tmp_path: Path) -> None:
    service = _service(tmp_path, write_secrets=False)

    assert service.secret_count == TWO_ENTRIES
    assert not (tmp_path / "old.secret").exists()
    assert not (tmp_path / "new.secret").exists()


def test_validator_does_not_read_files(tmp_path: Path) -> None:
    service = _service(tmp_path, write_secrets=False)

    assert _validate(service) is service
    assert not (tmp_path / "old.secret").exists()


def test_empty_service_is_valid_without_io(tmp_path: Path) -> None:
    service = _service(tmp_path, entries=(), write_secrets=False)

    assert service.secret_count == 0
    assert _validate(service) is service
    assert service(_request()) == SecretResult(kind=SecretKind.UNAVAILABLE)


def test_exact_request_reads_exact_secret_bytes(tmp_path: Path) -> None:
    result = _service(tmp_path)(_request())

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key == OLD_SECRET


def test_second_exact_request_reads_second_secret(tmp_path: Path) -> None:
    result = _service(tmp_path)(
        _request(
            first_capture_sequence_id=SUCCESSOR_SEQUENCE_ID,
            key_id=NEW_KEY_ID,
            key_reference_id=NEW_REFERENCE_ID,
            last_capture_sequence_id=None,
            request_index=1,
        )
    )

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key == NEW_SECRET


def test_request_index_is_ordering_context_only(tmp_path: Path) -> None:
    result = _service(tmp_path)(_request(request_index=999))

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key == OLD_SECRET


def test_sync_port_materializes_exact_file_trust(tmp_path: Path) -> None:
    resolved = _resolve_service(_service(tmp_path))

    assert resolved.provider_id == PROVIDER_ID
    assert resolved.request_count == TWO_ENTRIES
    assert resolved.key_ids == (OLD_KEY_ID, NEW_KEY_ID)
    assert tuple(key.secret_key for key in resolved.trust.keys) == (
        OLD_SECRET,
        NEW_SECRET,
    )


def test_repeated_calls_reread_rotated_file(tmp_path: Path) -> None:
    service = _service(tmp_path)

    first = service(_request())
    _ = (tmp_path / "old.secret").write_bytes(ROTATED_SECRET)
    second = service(_request())

    assert first.secret_key == OLD_SECRET
    assert second.secret_key == ROTATED_SECRET


def test_raw_file_bytes_are_preserved_exactly(tmp_path: Path) -> None:
    secret = b"x" * MIN_TELEMETRY_LINEAGE_KEY_BYTES + b"\n"
    service = _service(tmp_path)
    _ = (tmp_path / "old.secret").write_bytes(secret)

    result = service(_request())

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key == secret


def test_exact_configured_byte_limit_is_allowed(tmp_path: Path) -> None:
    secret = b"x" * MIN_TELEMETRY_LINEAGE_KEY_BYTES
    service = _service(
        tmp_path,
        max_secret_bytes=len(secret),
    )
    _ = (tmp_path / "old.secret").write_bytes(secret)

    result = service(_request())

    assert result.kind is SecretKind.RESOLVED
    assert result.secret_key == secret


def test_missing_matched_file_returns_unavailable(tmp_path: Path) -> None:
    service = _service(tmp_path, write_secrets=False)

    result = service(_request())

    assert result == SecretResult(kind=SecretKind.UNAVAILABLE)


class _UnexpectedReadError(AssertionError):
    """A test observed forbidden file I/O."""


def test_unknown_binding_returns_unavailable_before_io(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    service = _service(tmp_path)

    def forbidden_open(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise _UnexpectedReadError

    monkeypatch.setattr(Path, "open", forbidden_open)

    result = service(_request(key_reference_id=UNKNOWN_REFERENCE_ID))

    assert result == SecretResult(kind=SecretKind.UNAVAILABLE)


def test_provider_mismatch_returns_failed_before_io(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    service = _service(tmp_path)

    def forbidden_open(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise _UnexpectedReadError

    monkeypatch.setattr(Path, "open", forbidden_open)

    result = service(_request(provider_id=OTHER_PROVIDER_ID))

    assert result == SecretResult(kind=SecretKind.FAILED)


@pytest.mark.parametrize(
    "candidate",
    [
        _request(key_id="local.lineage-key.other"),
        _request(last_capture_sequence_id=None),
    ],
)
def test_metadata_mismatch_returns_failed_before_io(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    candidate: SecretRequest,
) -> None:
    service = _service(tmp_path)

    def forbidden_open(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise _UnexpectedReadError

    monkeypatch.setattr(Path, "open", forbidden_open)

    result = service(candidate)

    assert result == SecretResult(kind=SecretKind.FAILED)


def test_unknown_manifest_returns_unavailable_before_io(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    other_fingerprint = (
        "ticket-admission-telemetry-lineage-trust-manifest-v1:sha256:"
        + ("f" * 64)
    )

    def forbidden_open(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise _UnexpectedReadError

    monkeypatch.setattr(Path, "open", forbidden_open)

    result = service(_request(manifest_fingerprint=other_fingerprint))

    assert result == SecretResult(kind=SecretKind.UNAVAILABLE)


def test_file_above_byte_limit_returns_failed(tmp_path: Path) -> None:
    service = _service(
        tmp_path,
        max_secret_bytes=MIN_TELEMETRY_LINEAGE_KEY_BYTES,
    )
    _ = (tmp_path / "old.secret").write_bytes(
        b"x" * (MIN_TELEMETRY_LINEAGE_KEY_BYTES + 1)
    )

    result = service(_request())

    assert result == SecretResult(kind=SecretKind.FAILED)


@pytest.mark.parametrize("secret", [b"", b"short"])
def test_file_below_key_minimum_returns_failed(
    tmp_path: Path,
    secret: bytes,
) -> None:
    service = _service(tmp_path)
    _ = (tmp_path / "old.secret").write_bytes(secret)

    result = service(_request())

    assert result == SecretResult(kind=SecretKind.FAILED)


def test_directory_path_returns_failed(tmp_path: Path) -> None:
    directory = tmp_path / "directory.secret"
    directory.mkdir()
    entries = (_entry(directory),)
    service = _service(
        tmp_path,
        entries=entries,
        write_secrets=False,
    )

    result = service(_request())

    assert result == SecretResult(kind=SecretKind.FAILED)


def test_generic_os_error_returns_failed_without_vendor_text(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    service = _service(tmp_path)

    def raising_open(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise OSError(VENDOR_DETAIL)

    monkeypatch.setattr(Path, "open", raising_open)

    result = service(_request())

    assert result == SecretResult(kind=SecretKind.FAILED)
    assert VENDOR_DETAIL not in repr(result)


def test_file_not_found_error_returns_unavailable(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    service = _service(tmp_path)

    def missing_open(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise FileNotFoundError(VENDOR_DETAIL)

    monkeypatch.setattr(Path, "open", missing_open)

    result = service(_request())

    assert result == SecretResult(kind=SecretKind.UNAVAILABLE)


def test_exact_match_opens_and_reads_once(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    calls: list[Path] = []
    stream = _TrackedStream(OLD_SECRET)

    def tracked_open(
        self: Path,
        *args: object,
        **kwargs: object,
    ) -> _TrackedStream:
        del args, kwargs
        calls.append(self)
        return stream

    monkeypatch.setattr(Path, "open", tracked_open)

    result = service(_request())

    assert result.kind is SecretKind.RESOLVED
    assert calls == [tmp_path / "old.secret"]
    assert stream.read_sizes == [DEFAULT_MAX_SECRET_BYTES + 1]


class _TrackedStream:
    def __init__(self, value: bytes) -> None:
        self._value: bytes = value
        self.read_sizes: list[int] = []

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return self._value if size < 0 else self._value[:size]

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        del exc_type, exc_value, traceback


def test_read_uses_configured_limit_plus_one(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    limit = MIN_TELEMETRY_LINEAGE_KEY_BYTES
    service = _service(tmp_path, max_secret_bytes=limit)
    stream = _TrackedStream(OLD_SECRET)

    def tracked_open(*args: object, **kwargs: object) -> _TrackedStream:
        del args, kwargs
        return stream

    monkeypatch.setattr(Path, "open", tracked_open)

    result = service(_request())

    assert result.kind is SecretKind.RESOLVED
    assert stream.read_sizes == [limit + 1]


def test_result_repr_hides_secret_bytes(tmp_path: Path) -> None:
    result = _service(tmp_path)(_request())
    representation = repr(result).encode("utf-8")

    assert OLD_SECRET not in representation
    assert SECRET_FIELD not in representation


def test_builder_rejects_non_tuple_entries(tmp_path: Path) -> None:
    with pytest.raises(FileProviderError, match="exact immutable tuple"):
        _ = _build(
            cast(
                "tuple[FileEntry, ...]",
                cast("object", list(_entries(tmp_path))),
            ),
            provider_id=PROVIDER_ID,
        )


def test_exact_entry_limit_is_allowed(tmp_path: Path) -> None:
    service = _service(tmp_path, max_entries=TWO_ENTRIES)

    assert service.max_entries == TWO_ENTRIES
    assert service.secret_count == TWO_ENTRIES


def test_entry_limit_is_enforced(tmp_path: Path) -> None:
    with pytest.raises(FileProviderError, match="secret count exceeds"):
        _ = _service(tmp_path, max_entries=ONE_ENTRY)


@pytest.mark.parametrize("max_entries", [0, -1, True, MAX_ENTRIES + 1])
def test_invalid_entry_limit_fails(
    tmp_path: Path,
    max_entries: int,
) -> None:
    with pytest.raises(FileProviderError, match="maximum secret count"):
        _ = _service(
            tmp_path,
            max_entries=max_entries,
            write_secrets=False,
        )


@pytest.mark.parametrize(
    "max_secret_bytes",
    [
        MIN_TELEMETRY_LINEAGE_KEY_BYTES - 1,
        True,
        MAX_TELEMETRY_LINEAGE_KEY_BYTES + 1,
    ],
)
def test_invalid_secret_byte_limit_fails(
    tmp_path: Path,
    max_secret_bytes: int,
) -> None:
    with pytest.raises(FileProviderError, match="maximum secret bytes"):
        _ = _service(
            tmp_path,
            max_secret_bytes=max_secret_bytes,
            write_secrets=False,
        )


def test_custom_secret_byte_limit_is_copied(tmp_path: Path) -> None:
    service = _service(
        tmp_path,
        max_secret_bytes=MIN_TELEMETRY_LINEAGE_KEY_BYTES,
    )

    assert service.max_secret_bytes == MIN_TELEMETRY_LINEAGE_KEY_BYTES


def test_foreign_entry_type_fails() -> None:
    with pytest.raises(FileProviderError, match="exact file-secret entry"):
        _ = _build(
            (cast("FileEntry", object()),),
            provider_id=PROVIDER_ID,
        )


@pytest.mark.parametrize(
    "secret_path",
    ["relative.secret", "", "bad\0path"],
)
def test_invalid_secret_path_fails(
    tmp_path: Path,
    secret_path: str,
) -> None:
    entry = replace(_entry(tmp_path / "old.secret"), secret_path=secret_path)

    with pytest.raises(FileProviderError, match="secret path"):
        _ = _build((entry,), provider_id=PROVIDER_ID)


@pytest.mark.parametrize(
    "entry",
    [
        FileEntry(
            first_capture_sequence_id=0,
            key_id="bad key",
            key_reference_id=OLD_REFERENCE_ID,
            last_capture_sequence_id=0,
            manifest_fingerprint=(
                "ticket-admission-telemetry-lineage-trust-manifest-v1:sha256:"
                + ("0" * 64)
            ),
            secret_path=str(Path.cwd() / "old.secret"),
        ),
        FileEntry(
            first_capture_sequence_id=0,
            key_id=OLD_KEY_ID,
            key_reference_id=OLD_REFERENCE_ID,
            last_capture_sequence_id=0,
            manifest_fingerprint="malformed",
            secret_path=str(Path.cwd() / "old.secret"),
        ),
        FileEntry(
            first_capture_sequence_id=2,
            key_id=OLD_KEY_ID,
            key_reference_id=OLD_REFERENCE_ID,
            last_capture_sequence_id=1,
            manifest_fingerprint=(
                "ticket-admission-telemetry-lineage-trust-manifest-v1:sha256:"
                + ("0" * 64)
            ),
            secret_path=str(Path.cwd() / "old.secret"),
        ),
    ],
)
def test_invalid_entry_metadata_fails(entry: FileEntry) -> None:
    with pytest.raises(FileProviderError, match="invalid manifest request"):
        _ = _build((entry,), provider_id=PROVIDER_ID)


def test_duplicate_manifest_reference_binding_fails(tmp_path: Path) -> None:
    entry = _entry(tmp_path / "first.secret")
    duplicate = replace(
        entry, secret_path=str((tmp_path / "second.secret").absolute())
    )

    with pytest.raises(FileProviderError, match="duplicate manifest request"):
        _ = _build((entry, duplicate), provider_id=PROVIDER_ID)


def test_validator_rejects_foreign_service_type() -> None:
    with pytest.raises(FileProviderError, match="exact file-secret provider"):
        _ = _validate(cast("FileProvider", object()))


def test_tampered_service_identity_fails(tmp_path: Path) -> None:
    service = replace(_service(tmp_path), service_id="unsupported")

    with pytest.raises(FileProviderError, match="identity is unsupported"):
        _ = service(_request())


def test_tampered_provider_identity_fails(tmp_path: Path) -> None:
    service = replace(_service(tmp_path), provider_id="bad provider")

    with pytest.raises(FileProviderError, match="canonical ASCII"):
        _ = service(_request())


@pytest.mark.parametrize("secret_count", [-1, True])
def test_tampered_secret_count_type_fails(
    tmp_path: Path,
    secret_count: int,
) -> None:
    service = replace(_service(tmp_path), secret_count=secret_count)

    with pytest.raises(FileProviderError, match="nonnegative integer"):
        _ = service(_request())


def test_tampered_secret_count_binding_fails(tmp_path: Path) -> None:
    service = replace(_service(tmp_path), secret_count=ONE_ENTRY)

    with pytest.raises(FileProviderError, match="does not match entries"):
        _ = service(_request())


@pytest.mark.parametrize("max_entries", [0, True, MAX_ENTRIES + 1])
def test_tampered_entry_limit_fails(
    tmp_path: Path,
    max_entries: int,
) -> None:
    service = replace(_service(tmp_path), max_entries=max_entries)

    with pytest.raises(FileProviderError, match="maximum secret count"):
        _ = service(_request())


@pytest.mark.parametrize(
    "max_secret_bytes",
    [
        MIN_TELEMETRY_LINEAGE_KEY_BYTES - 1,
        True,
        MAX_TELEMETRY_LINEAGE_KEY_BYTES + 1,
    ],
)
def test_tampered_secret_byte_limit_fails(
    tmp_path: Path,
    max_secret_bytes: int,
) -> None:
    service = replace(_service(tmp_path), max_secret_bytes=max_secret_bytes)

    with pytest.raises(FileProviderError, match="maximum secret bytes"):
        _ = service(_request())


def test_tampered_entry_order_fails(tmp_path: Path) -> None:
    service = _service(tmp_path)
    tampered = replace(service, entries=tuple(reversed(service.entries)))

    with pytest.raises(FileProviderError, match="not canonically ordered"):
        _ = tampered(_request())


def test_tampered_entry_path_fails_before_io(tmp_path: Path) -> None:
    service = _service(tmp_path)
    changed = replace(service.entries[0], secret_path=RELATIVE_PATH)
    tampered = replace(service, entries=(changed, service.entries[1]))

    with pytest.raises(FileProviderError, match="secret path must be absolute"):
        _ = tampered(_request())


def test_tampered_entry_metadata_fails_before_io(tmp_path: Path) -> None:
    service = _service(tmp_path)
    changed = replace(service.entries[0], key_id="bad key")
    tampered = replace(service, entries=(changed, service.entries[1]))

    with pytest.raises(FileProviderError, match="invalid manifest request"):
        _ = tampered(_request())


def test_foreign_request_type_fails_closed(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with pytest.raises(FileProviderError, match="invalid file-provider"):
        _ = service(cast("SecretRequest", object()))


def test_malformed_request_fails_closed(tmp_path: Path) -> None:
    service = _service(tmp_path)
    malformed = replace(_request(), manifest_fingerprint="malformed")

    with pytest.raises(FileProviderError, match="invalid file-provider"):
        _ = service(malformed)


def test_wrong_valid_file_secret_remains_unverified_until_use(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)
    _ = (tmp_path / "old.secret").write_bytes(ROTATED_SECRET)

    resolved = _resolve_service(service)

    assert resolved.trust.keys[0].secret_key == ROTATED_SECRET
    assert resolved.trust.keys[1].secret_key == NEW_SECRET


def test_result_kinds_remain_shared_and_stable() -> None:
    assert tuple(kind.value for kind in SecretKind) == (
        "resolved",
        "unavailable",
        "failed",
    )
