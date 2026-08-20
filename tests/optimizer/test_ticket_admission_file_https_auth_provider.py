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
#   - Explicit file-backed HTTPS Authorization provider regressions.
# - Must-Not:
#   - Use discovery, writes outside pytest temporary roots, network, external
#     stores, retries, caches, workers, async plugins, logging, or policy.
# - Allows:
#   - Inputs: explicit temporary files, bindings, requests, and tampering.
#   - Outputs: read, rotation, bounds, secrecy, ordering, and failure checks.
#   - Side effects: pytest-owned temporary file reads and writes only.
# - Split-When:
#   - Split when native async file I/O or hosted credential APIs gain tests.
# - Merge-When:
#   - Merge when another suite owns this exact explicit file-auth behavior.
# - Summary:
#   - Exact bounded file-backed HTTPS Authorization provider regressions.
# - Description:
#   - Proves one matched absolute path is reread without discovery or caching.
# - Usage:
#   - Runs without sockets, external stores, plugins, or accelerator hardware.
# - Defaults:
#   - Uses two explicit files, 64 bindings, and a 4096-byte value limit.
#

"""Explicit bounded file-backed HTTPS Authorization provider tests."""

# ruff: file-ignore[line-too-long,undocumented-public-function]

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from ssl import PROTOCOL_TLS_CLIENT
from ssl import SSLContext
from ssl import TLSVersion
from typing import Self
from typing import cast

from accelerator import (
    # jig-ignore-next-line: indivisible reviewed identifier
    ticket_admission_telemetry_lineage_file_https_auth_provider as file_provider,
)
from accelerator import (
    ticket_admission_telemetry_lineage_https_auth_provider as auth,
)
from accelerator import (
    ticket_admission_telemetry_lineage_https_authorized_fetcher as authorized,
)
from accelerator import (
    ticket_admission_telemetry_lineage_https_bundle_fetcher as https,
)
from accelerator import (
    ticket_admission_telemetry_lineage_public_key_bundle_fetcher as fetch,
)
import pytest

FileAuthError = (
    file_provider.TicketAdmissionTelemetryLineageFileHttpsAuthProviderError
)
FileEntry = file_provider.TicketAdmissionTelemetryLineageFileHttpsAuthorization
FileProvider = (
    file_provider.TicketAdmissionTelemetryLineageFileHttpsAuthProvider
)
AuthRequest = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationRequest
AuthResult = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResult
AuthKind = auth.TicketAdmissionTelemetryLineageHttpsAuthorizationResultKind
HttpsConfig = (
    https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcherConfig
)
FetchRequest = fetch.TicketAdmissionTelemetryLineagePublicKeyBundleFetchRequest
_build = file_provider.build_ticket_admission_file_https_authorization_provider
_validate = (
    file_provider.validate_ticket_admission_file_https_authorization_provider
)
_build_https = https.build_ticket_admission_https_public_key_bundle_fetcher
_resolve = auth.resolve_ticket_admission_https_authorization
_build_authorized = (
    authorized.build_ticket_admission_authorized_https_bundle_fetcher
)

SERVICE_ID = (
    "explicit-file-ticket-admission-lineage-https-authorization-provider-v1"
)
AUTH_PROVIDER_ID = "credential-provider.test.file-authorization"
OTHER_AUTH_PROVIDER_ID = "credential-provider.test.other"
FETCH_PROVIDER_A = "provider.test.file-auth-public-keys-a"
FETCH_PROVIDER_B = "provider.test.file-auth-public-keys-b"
RESOURCE_A = "resource.test.public-key-bundle.a"
RESOURCE_B = "resource.test.public-key-bundle.b"
SOURCE_A = "source.test.file-auth-key-service-a"
SOURCE_B = "source.test.file-auth-key-service-b"
HOST = "keys.example.test"
TARGET = "/v1/public-key-bundles/a.json"
FINGERPRINT_A = (
    "ticket-admission-telemetry-lineage-public-key-bundle-v1:sha256:"
    + ("0" * 64)
)
FINGERPRINT_B = (
    "ticket-admission-telemetry-lineage-public-key-bundle-v1:sha256:"
    + ("1" * 64)
)
AUTHORIZATION_A = "Bearer caller-owned-file-token-a"
AUTHORIZATION_B = "Basic Y2FsbGVyOm93bmVk"
ROTATED_AUTHORIZATION = "Bearer rotated-file-token"
PATH_A = "authorization-a.txt"
PATH_B = "authorization-b.txt"
SHARED_PATH = "authorization-shared.txt"
PATH_FIELD = b"authorization_path"
ENTRIES_FIELD = b"entries=("
AUTHORIZATION_FIELD = b"authorization_value"
DEFAULT_MAX_ENTRIES = 64
MAX_ENTRIES = 4096
DEFAULT_MAX_BYTES = 4096
MAX_BYTES = 16384
ONE_ENTRY = 1
TWO_ENTRIES = 2
HIDDEN_DETAIL = "hidden file-system detail"


class _UnexpectedReadError(AssertionError):
    """A test observed forbidden file I/O."""


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


def _path_a(tmp_path: Path) -> Path:
    return tmp_path / PATH_A


def _path_b(tmp_path: Path) -> Path:
    return tmp_path / PATH_B


def _entry_a(  # ruff: ignore[too-many-arguments]
    authorization_path: Path,
    *,
    bundle_fingerprint: str = FINGERPRINT_A,
    fetch_provider_id: str = FETCH_PROVIDER_A,
    resource_id: str = RESOURCE_A,
    source_id: str = SOURCE_A,
) -> FileEntry:
    return FileEntry(
        authorization_path=str(authorization_path),
        bundle_fingerprint=bundle_fingerprint,
        fetch_provider_id=fetch_provider_id,
        resource_id=resource_id,
        source_id=source_id,
    )


def _entry_b(authorization_path: Path) -> FileEntry:
    return FileEntry(
        authorization_path=str(authorization_path),
        bundle_fingerprint=FINGERPRINT_B,
        fetch_provider_id=FETCH_PROVIDER_B,
        resource_id=RESOURCE_B,
        source_id=SOURCE_B,
    )


def _entries(tmp_path: Path) -> tuple[FileEntry, ...]:
    return (_entry_a(_path_a(tmp_path)), _entry_b(_path_b(tmp_path)))


def _write_default_files(tmp_path: Path) -> None:
    _ = _path_a(tmp_path).write_text(
        AUTHORIZATION_A,
        encoding="ascii",
        newline="",
    )
    _ = _path_b(tmp_path).write_text(
        AUTHORIZATION_B,
        encoding="ascii",
        newline="",
    )


def _service(  # ruff: ignore[too-many-arguments]
    tmp_path: Path,
    entries: tuple[FileEntry, ...] | None = None,
    *,
    provider_id: str = AUTH_PROVIDER_ID,
    max_entries: int = DEFAULT_MAX_ENTRIES,
    max_authorization_bytes: int = DEFAULT_MAX_BYTES,
    write_files: bool = True,
) -> FileProvider:
    if write_files:
        _write_default_files(tmp_path)
    return _build(
        _entries(tmp_path) if entries is None else entries,
        provider_id=provider_id,
        max_entries=max_entries,
        max_authorization_bytes=max_authorization_bytes,
    )


def _request(  # ruff: ignore[too-many-arguments]
    *,
    authorization_provider_id: str = AUTH_PROVIDER_ID,
    bundle_fingerprint: str = FINGERPRINT_A,
    fetch_provider_id: str = FETCH_PROVIDER_A,
    resource_id: str = RESOURCE_A,
    source_id: str = SOURCE_A,
) -> AuthRequest:
    return AuthRequest(
        authorization_provider_id=authorization_provider_id,
        bundle_fingerprint=bundle_fingerprint,
        fetch_provider_id=fetch_provider_id,
        resource_id=resource_id,
        source_id=source_id,
    )


def _tls_context() -> SSLContext:
    context = SSLContext(PROTOCOL_TLS_CLIENT)
    context.minimum_version = TLSVersion.TLSv1_2
    return context


def _https_fetcher() -> (
    https.TicketAdmissionTelemetryLineageHttpsPublicKeyBundleFetcher
):
    return _build_https(
        HttpsConfig(
            host=HOST,
            resource_id=RESOURCE_A,
            source_id=SOURCE_A,
            target=TARGET,
            tls_context=_tls_context(),
        )
    )


def _fetch_request() -> FetchRequest:
    return FetchRequest(
        bundle_fingerprint=FINGERPRINT_A,
        max_bytes=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_BYTES
        ),
        max_entries=(
            fetch.DEFAULT_MAX_TELEMETRY_LINEAGE_PUBLIC_KEY_BUNDLE_FETCH_ENTRIES
        ),
        provider_id=FETCH_PROVIDER_A,
        resource_id=RESOURCE_A,
        source_id=SOURCE_A,
    )


def _forbid_open(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_open(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise _UnexpectedReadError

    monkeypatch.setattr(Path, "open", forbidden_open)


def test_identity_limits_metadata_and_repr_are_stable(tmp_path: Path) -> None:
    service = _service(tmp_path)
    representation = repr(service).encode("utf-8")
    entry_representation = repr(service.entries[0]).encode("utf-8")

    assert (
        file_provider.ticket_admission_file_https_authorization_provider_id()
        == SERVICE_ID
    )
    assert (
        file_provider.DEFAULT_MAX_TELEMETRY_LINEAGE_FILE_HTTPS_AUTHORIZATIONS
        == DEFAULT_MAX_ENTRIES
    )
    assert (
        file_provider.MAX_TELEMETRY_LINEAGE_FILE_HTTPS_AUTHORIZATIONS
        == MAX_ENTRIES
    )
    assert (
        # jig-ignore-next-line: indivisible reviewed identifier
        file_provider.DEFAULT_MAX_TELEMETRY_LINEAGE_FILE_HTTPS_AUTHORIZATION_BYTES
        == DEFAULT_MAX_BYTES
    )
    assert (
        file_provider.MAX_TELEMETRY_LINEAGE_FILE_HTTPS_AUTHORIZATION_BYTES
        == MAX_BYTES
    )
    assert service.service_id == SERVICE_ID
    assert service.provider_id == AUTH_PROVIDER_ID
    assert service.authorization_count == TWO_ENTRIES
    assert service.max_entries == DEFAULT_MAX_ENTRIES
    assert service.max_authorization_bytes == DEFAULT_MAX_BYTES
    assert _validate(service) is service
    assert str(tmp_path).encode() not in representation
    assert PATH_FIELD not in entry_representation
    assert ENTRIES_FIELD not in representation


def test_builder_canonically_orders_entries(tmp_path: Path) -> None:
    service = _service(
        tmp_path,
        (_entry_b(_path_b(tmp_path)), _entry_a(_path_a(tmp_path))),
        write_files=False,
    )

    assert service.entries == _entries(tmp_path)


def test_builder_and_validator_do_not_read_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    entries = _entries(tmp_path)
    _forbid_open(monkeypatch)

    service = _service(tmp_path, entries, write_files=False)

    assert _validate(service) is service


def test_empty_service_is_valid_without_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_open(monkeypatch)
    service = _service(tmp_path, (), write_files=False)

    assert service.authorization_count == 0
    assert service(_request()) == AuthResult(kind=AuthKind.UNAVAILABLE)


def test_exact_request_reads_exact_file_value(tmp_path: Path) -> None:
    result = _service(tmp_path)(_request())

    assert result.kind is AuthKind.RESOLVED
    assert result.authorization_value == AUTHORIZATION_A
    representation = repr(result).encode("utf-8")
    assert AUTHORIZATION_A.encode() not in representation
    assert AUTHORIZATION_FIELD not in representation


def test_second_exact_request_reads_second_file(tmp_path: Path) -> None:
    result = _service(tmp_path)(
        _request(
            bundle_fingerprint=FINGERPRINT_B,
            fetch_provider_id=FETCH_PROVIDER_B,
            resource_id=RESOURCE_B,
            source_id=SOURCE_B,
        )
    )

    assert result.kind is AuthKind.RESOLVED
    assert result.authorization_value == AUTHORIZATION_B


def test_sync_authorization_boundary_resolves_file_value(
    tmp_path: Path,
) -> None:
    resolved = _resolve(
        _https_fetcher(),
        _fetch_request(),
        _service(tmp_path),
        authorization_provider_id=AUTH_PROVIDER_ID,
    )

    assert resolved.authorization_value == AUTHORIZATION_A
    assert resolved.authorization_provider_id == AUTH_PROVIDER_ID
    assert resolved.bundle_fingerprint == FINGERPRINT_A
    assert resolved.fetch_provider_id == FETCH_PROVIDER_A
    assert resolved.resource_id == RESOURCE_A
    assert resolved.source_id == SOURCE_A


def test_resolved_file_value_builds_authorized_fetcher(tmp_path: Path) -> None:
    https_fetcher = _https_fetcher()
    resolved = _resolve(
        https_fetcher,
        _fetch_request(),
        _service(tmp_path),
        authorization_provider_id=AUTH_PROVIDER_ID,
    )

    built = _build_authorized(https_fetcher, resolved)

    assert built.authorization_provider_id == AUTH_PROVIDER_ID
    assert built.bundle_fingerprint == FINGERPRINT_A
    assert built.fetch_provider_id == FETCH_PROVIDER_A
    assert built.resource_id == RESOURCE_A
    assert built.source_id == SOURCE_A


def test_repeated_calls_reread_rotated_file_without_cache(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path)

    first = service(_request())
    _ = _path_a(tmp_path).write_text(
        ROTATED_AUTHORIZATION,
        encoding="ascii",
        newline="",
    )
    second = service(_request())

    assert first.authorization_value == AUTHORIZATION_A
    assert second.authorization_value == ROTATED_AUTHORIZATION


def test_deleted_file_becomes_unavailable_without_cache(tmp_path: Path) -> None:
    service = _service(tmp_path)
    assert service(_request()).kind is AuthKind.RESOLVED
    _path_a(tmp_path).unlink()

    assert service(_request()) == AuthResult(kind=AuthKind.UNAVAILABLE)


def test_exact_configured_byte_limit_is_allowed(tmp_path: Path) -> None:
    value = "X" * 32
    _ = _path_a(tmp_path).write_text(value, encoding="ascii", newline="")
    service = _service(
        tmp_path,
        max_authorization_bytes=32,
        write_files=False,
    )

    result = service(_request())

    assert result.kind is AuthKind.RESOLVED
    assert result.authorization_value == value


def test_file_above_byte_limit_returns_failed(tmp_path: Path) -> None:
    _ = _path_a(tmp_path).write_bytes(b"X" * 33)
    service = _service(
        tmp_path,
        max_authorization_bytes=32,
        write_files=False,
    )

    assert service(_request()) == AuthResult(kind=AuthKind.FAILED)


@pytest.mark.parametrize(
    "value",
    [
        b"",
        b" Bearer token",
        b"Bearer token ",
        b"Bearer\ttoken",
        b"Bearer\ntoken",
        b"Bearer\x7ftoken",
        "Bearer café".encode(),
        b"Bearer\x00token",
    ],
)
def test_invalid_file_value_returns_failed(
    tmp_path: Path,
    value: bytes,
) -> None:
    _ = _path_a(tmp_path).write_bytes(value)
    service = _service(tmp_path, write_files=False)

    assert service(_request()) == AuthResult(kind=AuthKind.FAILED)


def test_missing_matched_file_returns_unavailable(tmp_path: Path) -> None:
    service = _service(tmp_path, write_files=False)

    assert service(_request()) == AuthResult(kind=AuthKind.UNAVAILABLE)


def test_directory_path_returns_failed(tmp_path: Path) -> None:
    directory = tmp_path / "authorization-directory"
    directory.mkdir()
    service = _service(
        tmp_path,
        (_entry_a(directory),),
        write_files=False,
    )

    assert service(_request()) == AuthResult(kind=AuthKind.FAILED)


def test_generic_os_error_returns_failed_without_vendor_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)

    def raising_open(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise OSError(HIDDEN_DETAIL)

    monkeypatch.setattr(Path, "open", raising_open)

    result = service(_request())

    assert result == AuthResult(kind=AuthKind.FAILED)
    assert HIDDEN_DETAIL not in repr(result)


def test_file_not_found_error_returns_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)

    def missing_open(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise FileNotFoundError(HIDDEN_DETAIL)

    monkeypatch.setattr(Path, "open", missing_open)

    assert service(_request()) == AuthResult(kind=AuthKind.UNAVAILABLE)


def test_exact_match_opens_and_reads_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    calls: list[Path] = []
    stream = _TrackedStream(AUTHORIZATION_A.encode("ascii"))

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

    assert result.authorization_value == AUTHORIZATION_A
    assert calls == [_path_a(tmp_path)]
    assert stream.read_sizes == [DEFAULT_MAX_BYTES + 1]


def test_read_uses_configured_limit_plus_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path, max_authorization_bytes=32)
    stream = _TrackedStream(AUTHORIZATION_A.encode("ascii"))

    def tracked_open(
        self: Path,
        *args: object,
        **kwargs: object,
    ) -> _TrackedStream:
        del self, args, kwargs
        return stream

    monkeypatch.setattr(Path, "open", tracked_open)

    _ = service(_request())

    assert stream.read_sizes == [33]


def test_provider_identity_mismatch_returns_failed_without_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    _forbid_open(monkeypatch)

    result = service(_request(authorization_provider_id=OTHER_AUTH_PROVIDER_ID))

    assert result == AuthResult(kind=AuthKind.FAILED)


@pytest.mark.parametrize(
    "auth_request",
    [
        _request(bundle_fingerprint=FINGERPRINT_B),
        _request(fetch_provider_id=FETCH_PROVIDER_B),
        _request(resource_id=RESOURCE_B),
        _request(source_id=SOURCE_B),
    ],
)
def test_well_formed_nonmatch_returns_unavailable_without_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    auth_request: AuthRequest,
) -> None:
    service = _service(tmp_path)
    _forbid_open(monkeypatch)

    assert service(auth_request) == AuthResult(kind=AuthKind.UNAVAILABLE)


def test_unrelated_file_is_not_discovered(tmp_path: Path) -> None:
    _ = (tmp_path / "unrelated.txt").write_text(
        AUTHORIZATION_A,
        encoding="ascii",
        newline="",
    )
    service = _service(tmp_path, write_files=False)

    assert service(_request()) == AuthResult(kind=AuthKind.UNAVAILABLE)


def test_two_bindings_may_share_one_explicit_file(tmp_path: Path) -> None:
    shared = tmp_path / SHARED_PATH
    _ = shared.write_text(AUTHORIZATION_A, encoding="ascii", newline="")
    service = _service(
        tmp_path,
        (_entry_a(shared), _entry_b(shared)),
        write_files=False,
    )

    first = service(_request())
    second = service(
        _request(
            bundle_fingerprint=FINGERPRINT_B,
            fetch_provider_id=FETCH_PROVIDER_B,
            resource_id=RESOURCE_B,
            source_id=SOURCE_B,
        )
    )

    assert first.authorization_value == AUTHORIZATION_A
    assert second.authorization_value == AUTHORIZATION_A


def test_foreign_request_type_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(FileAuthError, match="invalid file-provider"):
        _ = _service(tmp_path)(cast("AuthRequest", object()))


def test_malformed_request_fails_closed(tmp_path: Path) -> None:
    malformed = replace(_request(), bundle_fingerprint="malformed")

    with pytest.raises(FileAuthError, match="invalid file-provider"):
        _ = _service(tmp_path)(malformed)


def test_validator_rejects_foreign_service_type() -> None:
    with pytest.raises(FileAuthError, match="exact file auth"):
        _ = _validate(cast("FileProvider", object()))


def test_tampered_service_identity_fails_closed(tmp_path: Path) -> None:
    tampered = replace(_service(tmp_path), service_id="unsupported")

    with pytest.raises(FileAuthError, match="service identity"):
        _ = tampered(_request())


def test_tampered_provider_identity_fails_closed(tmp_path: Path) -> None:
    tampered = replace(_service(tmp_path), provider_id="bad provider")

    with pytest.raises(FileAuthError, match="provider identity"):
        _ = tampered(_request())


@pytest.mark.parametrize("max_entries", [0, -1, True])
def test_invalid_max_entry_limit_fails_closed(
    tmp_path: Path,
    max_entries: int,
) -> None:
    with pytest.raises(FileAuthError, match="positive integer"):
        _ = _service(
            tmp_path,
            (),
            max_entries=max_entries,
            write_files=False,
        )


def test_max_entry_limit_above_supported_limit_fails_closed(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileAuthError, match="exceeds supported limit"):
        _ = _service(
            tmp_path,
            (),
            max_entries=MAX_ENTRIES + 1,
            write_files=False,
        )


def test_entry_count_above_configured_limit_fails_closed(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileAuthError, match="entry count exceeds"):
        _ = _service(
            tmp_path,
            _entries(tmp_path),
            max_entries=ONE_ENTRY,
            write_files=False,
        )


@pytest.mark.parametrize("max_bytes", [0, -1, True])
def test_invalid_max_byte_limit_fails_closed(
    tmp_path: Path,
    max_bytes: int,
) -> None:
    with pytest.raises(FileAuthError, match="positive integer"):
        _ = _service(
            tmp_path,
            (),
            max_authorization_bytes=max_bytes,
            write_files=False,
        )


def test_max_byte_limit_above_supported_limit_fails_closed(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileAuthError, match="exceeds supported limit"):
        _ = _service(
            tmp_path,
            (),
            max_authorization_bytes=MAX_BYTES + 1,
            write_files=False,
        )


def test_entries_require_exact_tuple(tmp_path: Path) -> None:
    with pytest.raises(FileAuthError, match="exact immutable tuple"):
        _ = _build(
            cast(
                "tuple[FileEntry, ...]",
                cast("object", [_entry_a(_path_a(tmp_path))]),
            ),
            provider_id=AUTH_PROVIDER_ID,
        )


def test_entry_requires_exact_type(tmp_path: Path) -> None:
    with pytest.raises(FileAuthError, match="exact file authorization"):
        _ = _service(
            tmp_path,
            (cast("FileEntry", object()),),
            write_files=False,
        )


@pytest.mark.parametrize(
    "provider_id",
    ["", "bad provider", cast("str", object())],
)
def test_provider_identity_requires_canonical_form(
    tmp_path: Path,
    provider_id: str,
) -> None:
    with pytest.raises(FileAuthError, match="canonical ASCII"):
        _ = _service(
            tmp_path,
            (),
            provider_id=provider_id,
            write_files=False,
        )


@pytest.mark.parametrize(
    "entry",
    [
        _entry_a(Path("C:/absolute"), bundle_fingerprint="malformed"),
        _entry_a(Path("C:/absolute"), fetch_provider_id="bad provider"),
        _entry_a(Path("C:/absolute"), resource_id="bad resource"),
        _entry_a(Path("C:/absolute"), source_id="bad source"),
    ],
)
def test_entry_metadata_requires_shared_canonical_form(
    tmp_path: Path,
    entry: FileEntry,
) -> None:
    del tmp_path
    with pytest.raises(FileAuthError, match="request metadata"):
        _ = _build((entry,), provider_id=AUTH_PROVIDER_ID)


@pytest.mark.parametrize(
    "authorization_path",
    [
        "",
        "relative.txt",
        "relative/path.txt",
        "C:/bad" + chr(0) + "path",
        cast("str", object()),
    ],
)
def test_authorization_path_requires_absolute_nonempty_form(
    tmp_path: Path,
    authorization_path: str,
) -> None:
    entry = replace(
        _entry_a(_path_a(tmp_path)),
        authorization_path=authorization_path,
    )

    with pytest.raises(FileAuthError, match="authorization path"):
        _ = _service(tmp_path, (entry,), write_files=False)


def test_duplicate_request_binding_fails_closed(tmp_path: Path) -> None:
    duplicate = replace(
        _entry_a(_path_a(tmp_path)),
        authorization_path=str(_path_b(tmp_path)),
    )

    with pytest.raises(FileAuthError, match="duplicate request binding"):
        _ = _service(
            tmp_path,
            (_entry_a(_path_a(tmp_path)), duplicate),
            write_files=False,
        )


def test_tampered_service_order_fails_closed(tmp_path: Path) -> None:
    service = _service(tmp_path)
    tampered = replace(service, entries=tuple(reversed(service.entries)))

    with pytest.raises(FileAuthError, match="not canonically ordered"):
        _ = tampered(_request())


def test_service_revalidates_tampered_path_before_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    changed = replace(service.entries[0], authorization_path="relative.txt")
    tampered = replace(service, entries=(changed, service.entries[1]))
    _forbid_open(monkeypatch)

    with pytest.raises(FileAuthError, match="authorization path"):
        _ = tampered(_request())


def test_service_revalidates_tampered_metadata_before_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(tmp_path)
    changed = replace(service.entries[0], bundle_fingerprint="malformed")
    tampered = replace(service, entries=(changed, service.entries[1]))
    _forbid_open(monkeypatch)

    with pytest.raises(FileAuthError, match="request metadata"):
        _ = tampered(_request())


def test_service_revalidates_tampered_entry_limit(tmp_path: Path) -> None:
    tampered = replace(_service(tmp_path), max_entries=0)

    with pytest.raises(FileAuthError, match="positive integer"):
        _ = tampered(_request())


def test_service_revalidates_tampered_byte_limit(tmp_path: Path) -> None:
    tampered = replace(_service(tmp_path), max_authorization_bytes=0)

    with pytest.raises(FileAuthError, match="positive integer"):
        _ = tampered(_request())


@pytest.mark.parametrize("authorization_count", [-1, True])
def test_tampered_authorization_count_type_fails(
    tmp_path: Path,
    authorization_count: int,
) -> None:
    tampered = replace(
        _service(tmp_path),
        authorization_count=authorization_count,
    )

    with pytest.raises(FileAuthError, match="nonnegative integer"):
        _ = tampered(_request())


def test_tampered_authorization_count_binding_fails(tmp_path: Path) -> None:
    tampered = replace(_service(tmp_path), authorization_count=ONE_ENTRY)

    with pytest.raises(FileAuthError, match="does not match entries"):
        _ = tampered(_request())


def test_tampered_entries_type_fails_closed(tmp_path: Path) -> None:
    tampered = replace(
        _service(tmp_path),
        entries=cast(
            "tuple[FileEntry, ...]",
            cast("object", [_entry_a(_path_a(tmp_path))]),
        ),
    )

    with pytest.raises(FileAuthError, match="exact immutable tuple"):
        _ = tampered(_request())


def test_authorization_path_is_not_in_failure_text(tmp_path: Path) -> None:
    hidden_path = "relative-hidden-authorization.txt"
    entry = replace(
        _entry_a(_path_a(tmp_path)),
        authorization_path=hidden_path,
    )

    with pytest.raises(FileAuthError) as caught:
        _ = _service(tmp_path, (entry,), write_files=False)

    assert hidden_path not in str(caught.value)
