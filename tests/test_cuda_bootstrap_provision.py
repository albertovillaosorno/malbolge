# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Repository-local CUDA package provisioning regression evidence.
# - Must-Not:
#   - Contact NVIDIA or mutate a real checkout toolkit during tests.
# - Allows:
#   - Inputs: synthetic tracked manifests and in-memory CUDA archives.
#   - Outputs: exact SHA/size, extraction, marker, and idempotence assertions.
#   - Side effects: test-local files only.
# - Split-When:
#   - Another package family gains independent bootstrap lifecycle semantics.
# - Merge-When:
#   - Project bootstrap tests own the same CUDA provisioning boundary.
# - Summary:
#   - Proves exact, contained, opt-in CUDA package materialization.
# - Description:
#   - Exercises manifest admission, archive verification, and safe extraction.
# - Usage:
#   - Collected without network access or CUDA hardware.
# - Defaults:
#   - Unverified or escaping archives fail before toolkit publication.
#

"""Repository-local CUDA package provisioning regression evidence."""

from __future__ import annotations

import hashlib
import io
import json
import lzma
import os
import shutil
import sys
import tarfile
import zipfile
import zlib
from pathlib import Path
from typing import TYPE_CHECKING, Self, cast, override

import pytest
from compression import zstd
from scripts.bootstrap import cuda_validation, project

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

LINUX_PLATFORM = "linux-x86_64"
FILE_REDIRECT = "file"
SOURCE_RECHECK = 2
TOOLKIT_ROOT = ".dependencies/cuda/13.3.1/toolkit"
PACKAGE_NAME = "cuda_nvrtc"
PACKAGE_VERSION = "13.3.33"
PACKAGE_PATH = (
    "cuda_nvrtc/linux-x86_64/"
    "cuda_nvrtc-linux-x86_64-13.3.33-archive.tar.xz"
)
ARCHIVE_ROOT = "cuda_nvrtc-linux-x86_64-13.3.33-archive"
NVRTC_MEMBER = f"{ARCHIVE_ROOT}/lib64/libnvrtc.so.13"
BUILTINS_MEMBER = f"{ARCHIVE_ROOT}/lib64/libnvrtc-builtins.so.13.3"
NVRTC_BYTES = b"synthetic-nvrtc"
BUILTINS_BYTES = b"synthetic-builtins"


def _tar_xz(entries: dict[str, bytes]) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:xz") as archive:
        for name, payload in entries.items():
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
    return output.getvalue()


def _manifest(
    tmp_path: Path,
    payload: bytes,
    overrides: dict[str, object] | None = None,
) -> Path:
    manifest = tmp_path / "toolchain-linux-x86_64.json"
    package: dict[str, object] = {
        "name": PACKAGE_NAME,
        "version": PACKAGE_VERSION,
        "relative_path": PACKAGE_PATH,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size": len(payload),
    }
    if overrides is not None:
        package.update(overrides)
    _ = manifest.write_text(
        json.dumps({
            "schema_version": 1,
            "cuda_release": "13.3 Update 1",
            "redistrib_manifest": "redistrib_13.3.1.json",
            "release_date": "2026-06-29",
            "platform": LINUX_PLATFORM,
            "toolkit_root": TOOLKIT_ROOT,
            "packages": [package],
            "redistrib_base_url": cuda_validation.NVIDIA_CUDA_REDIST_BASE,
        }),
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def _payload() -> bytes:
    return _tar_xz({
        NVRTC_MEMBER: NVRTC_BYTES,
        BUILTINS_MEMBER: BUILTINS_BYTES,
    })


def _download_fixture(payload: bytes) -> Callable[[str], bytes]:
    """Return exact synthetic package bytes for the pinned URL.

    Returns:
        A downloader restricted to the expected NVIDIA package URL.

    """
    def download(url: str) -> bytes:
        assert url == cuda_validation.NVIDIA_CUDA_REDIST_BASE + PACKAGE_PATH
        return payload

    return download


def test_cuda_relative_root_manifest_identity_is_cwd_invariant(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loaded manifest identity cannot move after the caller changes cwd."""
    root = tmp_path / "repository"
    root.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    manifest_path = _manifest(root, _payload())
    with monkeypatch.context() as isolated:
        isolated.chdir(tmp_path)
        manifest = cuda_validation.load_cuda_provision_manifest(
            Path("repository"), Path("repository") / manifest_path.name,
            LINUX_PLATFORM,
        )
        isolated.chdir(other)
        assert manifest.toolkit_root == root / TOOLKIT_ROOT
        assert manifest.manifest_path == manifest_path


def test_cuda_relative_root_provisions_under_original_cwd_after_download(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Downloader cwd mutation cannot change the selected CUDA destination."""
    root = tmp_path / "repository"
    root.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    payload = _payload()
    manifest_path = _manifest(root, payload)
    calls = 0

    with monkeypatch.context() as isolated:
        isolated.chdir(tmp_path)

        def download(url: str) -> bytes:
            nonlocal calls
            calls += 1
            assert url == cuda_validation.NVIDIA_CUDA_REDIST_BASE + PACKAGE_PATH
            isolated.chdir(other)
            return payload

        toolkit = cuda_validation.provision_cuda_manifest(
            Path("repository"), Path("repository") / manifest_path.name,
            LINUX_PLATFORM, downloader=download,
        )
    assert calls == 1
    assert toolkit == root / TOOLKIT_ROOT
    assert (toolkit / "lib64/libnvrtc.so.13").read_bytes() == NVRTC_BYTES
    assert not (root / f".temp/cuda-provision-{LINUX_PLATFORM}").exists()
    assert not (other / "repository").exists()


def test_manifest_parses_exact_linux_nvrtc_package(tmp_path: Path) -> None:
    """One Linux manifest binds exact package URL, size, hash, and toolkit."""
    payload = _payload()
    manifest_path = _manifest(tmp_path, payload)

    manifest = cuda_validation.load_cuda_provision_manifest(
        tmp_path,
        manifest_path,
        LINUX_PLATFORM,
    )

    assert manifest.platform_id == LINUX_PLATFORM
    assert manifest.toolkit_root == tmp_path / TOOLKIT_ROOT
    assert len(manifest.packages) == 1
    package = manifest.packages[0]
    assert package.name == PACKAGE_NAME
    assert package.version == PACKAGE_VERSION
    assert package.relative_path == PACKAGE_PATH
    assert package.size == len(payload)
    assert package.sha256 == hashlib.sha256(payload).hexdigest()


@pytest.mark.parametrize("field", ("toolkit_root", "relative_path"))
def test_cuda_provision_manifest_rejects_host_dependent_paths(
    tmp_path: Path,
    field: str,
) -> None:
    """CUDA packages use one portable pathname on Linux and Windows."""
    payload = _payload()
    if field == "relative_path":
        archive_alias = PACKAGE_PATH.replace("-archive.tar.xz", r"\archive.tar.xz")
        manifest = _manifest(tmp_path, payload, {field: archive_alias})
    else:
        manifest = _manifest(tmp_path, payload)
        document = cast("dict[str, object]", json.loads(manifest.read_text(encoding="utf-8")))
        document[field] = TOOLKIT_ROOT.replace("/", "\\")
        _ = manifest.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(
        cuda_validation.CudaProvisionError, match="must use forward slashes"
    ):
        _ = cuda_validation.load_cuda_provision_manifest(
            tmp_path, manifest, LINUX_PLATFORM
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("toolkit_root", ".dependencies/cuda/CON"),
        ("toolkit_root", ".dependencies/cuda/file."),
        ("toolkit_root", ".dependencies/cuda/data:alternate"),
        ("relative_path", "cuda_nvrtc/linux-x86_64/NUL.zip"),
        ("relative_path", "cuda_nvrtc/linux-x86_64/archive:.zip"),
        ("relative_path", "cuda_nvrtc/linux-x86_64/trailing./safe.zip"),
    ],
)
def test_cuda_manifest_rejects_windows_reserved_path_components(
    tmp_path: Path, field: str, value: str
) -> None:
    """A tracked manifest may not target Windows devices or alternate streams."""
    manifest = _manifest(tmp_path, _payload())
    document = cast("dict[str, object]", json.loads(manifest.read_text()))
    if field == "relative_path":
        packages = cast("list[dict[str, object]]", document["packages"])
        packages[0][field] = value
    else:
        document[field] = value
    _ = manifest.write_text(json.dumps(document))
    with pytest.raises(cuda_validation.CudaProvisionError, match="Windows-reserved"):
        _ = cuda_validation.load_cuda_provision_manifest(
            tmp_path, manifest, LINUX_PLATFORM
        )


@pytest.mark.parametrize(
    "relative_path",
    (
        f"{PACKAGE_NAME}/{LINUX_PLATFORM}/%2e%2e/escape.zip",
        f"{PACKAGE_NAME}/{LINUX_PLATFORM}/some%2Farchive.zip",
        f"{PACKAGE_NAME}/{LINUX_PLATFORM}/some%5carchive.zip",
        f"{PACKAGE_NAME}/{LINUX_PLATFORM}/archive;parameter.zip",
        f"{PACKAGE_NAME}/{LINUX_PLATFORM}/user@host.zip",
        f"{PACKAGE_NAME}/{LINUX_PLATFORM}/a//archive.zip",
        f"{PACKAGE_NAME}/{LINUX_PLATFORM}/./archive.zip",
        f"{PACKAGE_NAME}/{LINUX_PLATFORM}/archive file.zip",
        f"{PACKAGE_NAME}/{LINUX_PLATFORM}/archive\u202e.zip",
    ),
)
def test_cuda_manifest_requires_canonical_url_path_segments(
    tmp_path: Path, relative_path: str
) -> None:
    """NVIDIA URL path segments must not admit escapes or reinterpretation."""
    manifest = _manifest(tmp_path, _payload(), {"relative_path": relative_path})
    with pytest.raises(
        cuda_validation.CudaProvisionError, match="canonical URL path"
    ):
        _ = cuda_validation.load_cuda_provision_manifest(
            tmp_path, manifest, LINUX_PLATFORM
        )


def test_package_verification_rejects_size_and_sha_drift(
    tmp_path: Path,
) -> None:
    """Downloaded bytes must satisfy both tracked size and SHA-256 identity."""
    payload = _payload()
    wrong_size = _manifest(tmp_path, payload, {"size": len(payload) + 1})
    size_package = cuda_validation.load_cuda_provision_manifest(
        tmp_path,
        wrong_size,
        LINUX_PLATFORM,
    ).packages[0]
    with pytest.raises(
        cuda_validation.CudaProvisionError,
        match="size mismatch",
    ):
        cuda_validation.verify_cuda_package(payload, size_package)

    wrong_sha = _manifest(tmp_path, payload, {"sha256": "0" * 64})
    sha_package = cuda_validation.load_cuda_provision_manifest(
        tmp_path,
        wrong_sha,
        LINUX_PLATFORM,
    ).packages[0]
    with pytest.raises(
        cuda_validation.CudaProvisionError,
        match="SHA-256 mismatch",
    ):
        cuda_validation.verify_cuda_package(payload, sha_package)


class _NetworkResponse:
    """Minimal closed-on-exit fake for the urllib response contract."""

    def __init__(self, value: object) -> None:
        self.value = value
        self.closed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        self.closed = True

    def read(self, _limit: int) -> bytes:
        if isinstance(self.value, Exception):
            raise self.value
        return cast("bytes", self.value)


class _UnsafeNetworkError(RuntimeError):
    """A host error whose message must never be evaluated."""

    @override
    def __str__(self) -> str:
        raise AssertionError("foreign host error __str__ was evaluated")


@pytest.mark.parametrize("phase", ["open", "read"])
@pytest.mark.parametrize(
    "fault_type", [OSError, TypeError, ValueError, RuntimeError, _UnsafeNetworkError]
)
def test_cuda_download_types_network_host_failures(
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    fault_type: type[Exception],
) -> None:
    """URL-open and body-read faults become typed without stringifying hosts."""
    error = fault_type("injected host failure")
    response = _NetworkResponse(error)
    url = cuda_validation.NVIDIA_CUDA_REDIST_BASE + PACKAGE_PATH

    def open_url(request: object, *, timeout: int) -> _NetworkResponse:
        assert isinstance(request, cuda_validation.urllib.request.Request)
        assert request.full_url == url
        assert timeout == 120
        if phase == "open":
            raise error
        return response

    monkeypatch.setattr(cuda_validation.urllib.request, "urlopen", open_url)
    with pytest.raises(
        cuda_validation.CudaProvisionError, match=type(error).__name__
    ) as caught:
        _ = cuda_validation._download_cuda_package(url)
    assert caught.value.__cause__ is error
    assert response.closed == (phase == "read")


class _HostileCudaErrorMeta(type):
    """Host-supplied exception class that intercepts metadata access."""

    @override
    def __getattribute__(cls, name: str) -> object:
        if name == "__name__":
            raise AssertionError("foreign exception metaclass was evaluated")
        return super().__getattribute__(name)


class _HostileCudaHostError(OSError, metaclass=_HostileCudaErrorMeta):
    """A host failure whose error class must be reported without hooks."""


@pytest.mark.parametrize("phase", ("open", "read"))
def test_cuda_download_does_not_read_foreign_exception_metaclass(
    monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """Host network errors cannot execute their class metadata hooks."""
    failure = _HostileCudaHostError("injected network error")
    response = _NetworkResponse(failure)

    def open_url(_request: object, *, timeout: int) -> _NetworkResponse:
        assert timeout == 120
        if phase == "open":
            raise failure
        return response

    monkeypatch.setattr(cuda_validation.urllib.request, "urlopen", open_url)
    with pytest.raises(
        cuda_validation.CudaProvisionError, match="_HostileCudaHostError"
    ) as caught:
        _ = cuda_validation._download_cuda_package(
            cuda_validation.NVIDIA_CUDA_REDIST_BASE + PACKAGE_PATH
        )
    assert caught.value.__cause__ is failure
    assert response.closed == (phase == "read")


@pytest.mark.parametrize("archive_kind", ("tar", "zip"))
def test_cuda_archive_fault_does_not_read_foreign_exception_metaclass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, archive_kind: str
) -> None:
    """Archive host faults cannot execute custom exception class formatting."""
    failure = _HostileCudaHostError("injected archive error")

    def reject_open(*_args: object, **_kwargs: object) -> None:
        raise failure

    with monkeypatch.context() as isolated:
        if archive_kind == "tar":
            isolated.setattr(cuda_validation.tarfile, "open", reject_open)
            extract = cuda_validation._safe_tar_extract
        else:
            isolated.setattr(cuda_validation.zipfile, "ZipFile", reject_open)
            extract = cuda_validation._safe_zip_extract
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="_HostileCudaHostError"
        ) as caught:
            _ = extract(b"invalid archive", tmp_path)
    assert caught.value.__cause__ is failure


def test_cuda_manifest_fault_does_not_read_foreign_exception_metaclass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Manifest JSON read failures bypass foreign exception class hooks."""
    manifest = _manifest(tmp_path, _payload())
    failure = _HostileCudaHostError("injected JSON error")

    def reject_parse(*_args: object, **_kwargs: object) -> None:
        raise failure

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation.json, "loads", reject_parse)
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="_HostileCudaHostError"
        ) as caught:
            _ = cuda_validation.load_cuda_provision_manifest(
                tmp_path, manifest, LINUX_PLATFORM
            )
    assert caught.value.__cause__ is failure


@pytest.mark.parametrize("phase", ("status", "junction"))
def test_cuda_directory_fault_does_not_read_foreign_exception_metaclass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """Source directory inspection must type host faults without hooks."""
    failure = _HostileCudaHostError("injected directory error")
    original_lstat = Path.lstat
    original_junction = Path.is_junction

    def reject_status(path: Path) -> os.stat_result:
        if path == tmp_path:
            raise failure
        return original_lstat(path)

    def reject_junction(path: Path) -> bool:
        if path == tmp_path:
            raise failure
        return original_junction(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(
            Path,
            "lstat" if phase == "status" else "is_junction",
            reject_status if phase == "status" else reject_junction,
        )
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="_HostileCudaHostError"
        ) as caught:
            cuda_validation._require_physical_directories(tmp_path, "staging")
    assert caught.value.__cause__ is failure


@pytest.mark.parametrize("foreign", [None, "not bytes", bytearray(b"data"), memoryview(b"data")])
def test_cuda_download_rejects_foreign_network_body(
    monkeypatch: pytest.MonkeyPatch,
    foreign: object,
) -> None:
    """HTTP response content must be exact immutable native bytes."""
    response = _NetworkResponse(foreign)
    url = cuda_validation.NVIDIA_CUDA_REDIST_BASE + PACKAGE_PATH

    def open_url(request: object, *, timeout: int) -> _NetworkResponse:
        assert isinstance(request, cuda_validation.urllib.request.Request)
        assert request.full_url == url
        assert timeout == 120
        return response

    monkeypatch.setattr(cuda_validation.urllib.request, "urlopen", open_url)
    with pytest.raises(cuda_validation.CudaProvisionError, match="native bytes"):
        _ = cuda_validation._download_cuda_package(url)
    assert response.closed


def test_cuda_tracked_windows_nvrtc_download_admits_pinned_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The checked-in 312 MB Windows archive must fit the bounded HTTPS read."""
    repository = Path(__file__).resolve().parents[1]
    source = (
        repository
        / "src/optimization/accelerator/adapter-outbound/accelerator/cuda/toolchain.json"
    )
    manifest = cuda_validation.load_cuda_provision_manifest(
        repository, source, "windows-x86_64"
    )
    package = next(item for item in manifest.packages if item.name == PACKAGE_NAME)
    assert package.size == 312_126_196
    observed_limits: list[int] = []

    class _EmptyBoundedResponse:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def read(self, limit: int) -> bytes:
            observed_limits.append(limit)
            return b""

    def open_url(request: object, *, timeout: int) -> _EmptyBoundedResponse:
        assert isinstance(request, cuda_validation.urllib.request.Request)
        assert request.full_url == manifest.base_url + package.relative_path
        assert timeout == 120
        return _EmptyBoundedResponse()

    monkeypatch.setattr(cuda_validation.urllib.request, "urlopen", open_url)
    assert (
        cuda_validation._download_cuda_package(
            manifest.base_url + package.relative_path, max_bytes=package.size
        )
        == b""
    )
    assert observed_limits == [package.size + 1]


def test_cuda_rejects_manifest_package_over_download_limit(tmp_path: Path) -> None:
    """An arbitrary giant manifest size must fail before network allocation."""
    too_big = cuda_validation._MAX_CUDA_DOWNLOAD_BYTES + 1
    manifest = _manifest(tmp_path, _payload(), {"size": too_big})
    with pytest.raises(cuda_validation.CudaProvisionError, match="byte limit"):
        _ = cuda_validation.load_cuda_provision_manifest(
            tmp_path, manifest, LINUX_PLATFORM
        )


def test_cuda_large_archive_members_have_separate_expansion_cap() -> None:
    """Large Windows DLLs fit expansion, but oversized members fail closed."""
    mib = 1024 * 1024
    cuda_validation._validate_cuda_archive_expansion((256 * mib,))
    with pytest.raises(cuda_validation.CudaProvisionError, match="member byte limit"):
        cuda_validation._validate_cuda_archive_expansion((1024 * mib,))


def test_cuda_download_accepts_native_network_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ordinary pinned HTTPS bytes remain supported and close the response."""
    payload = b"verified network bytes"
    response = _NetworkResponse(payload)
    url = cuda_validation.NVIDIA_CUDA_REDIST_BASE + PACKAGE_PATH

    def open_url(request: object, *, timeout: int) -> _NetworkResponse:
        assert isinstance(request, cuda_validation.urllib.request.Request)
        assert request.full_url == url
        assert timeout == 120
        return response

    monkeypatch.setattr(cuda_validation.urllib.request, "urlopen", open_url)
    assert cuda_validation._download_cuda_package(url) == payload
    assert response.closed


class _BytesSubclass(bytes):
    """A digest-matching value with a foreign runtime type."""


@pytest.mark.parametrize("kind", ["mutable", "subclass", "buffer", "string", "missing"])
def test_cuda_package_rejects_foreign_byte_values(
    tmp_path: Path,
    kind: str,
) -> None:
    """Only native bytes may enter the pinned archive verification boundary."""
    payload = _payload()
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, _manifest(tmp_path, payload), LINUX_PLATFORM
    ).packages[0]
    values: dict[str, object] = {
        "mutable": bytearray(payload),
        "subclass": _BytesSubclass(payload),
        "buffer": memoryview(payload),
        "string": "x" * len(payload),
        "missing": None,
    }
    with pytest.raises(cuda_validation.CudaProvisionError, match="native bytes"):
        cuda_validation.verify_cuda_package(cast("bytes", values[kind]), package)


@pytest.mark.parametrize("kind", ["mutable", "subclass", "buffer"])
def test_cuda_provision_rejects_foreign_download_bytes(
    tmp_path: Path,
    kind: str,
) -> None:
    """A custom downloader cannot pass byte-compatible foreign objects."""
    payload = _payload()
    manifest = _manifest(tmp_path, payload)
    values: dict[str, object] = {
        "mutable": bytearray(payload),
        "subclass": _BytesSubclass(payload),
        "buffer": memoryview(payload),
    }

    def download(url: str) -> bytes:
        assert url == cuda_validation.NVIDIA_CUDA_REDIST_BASE + PACKAGE_PATH
        return cast("bytes", values[kind])

    with pytest.raises(cuda_validation.CudaProvisionError, match="native bytes"):
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path, manifest, LINUX_PLATFORM, downloader=download
        )
    assert not (tmp_path / TOOLKIT_ROOT).exists()


def test_tar_extraction_strips_single_archive_root(tmp_path: Path) -> None:
    """Strip the NVIDIA archive root while retaining toolkit-relative files."""
    payload = _payload()
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path,
        _manifest(tmp_path, payload),
        LINUX_PLATFORM,
    ).packages[0]
    destination = tmp_path / "toolkit"
    staging = tmp_path / "staging"

    cuda_validation.extract_cuda_package(
        payload,
        package,
        destination,
        staging=staging,
    )

    assert (destination / "lib64/libnvrtc.so.13").read_bytes() == NVRTC_BYTES
    assert (
        destination / "lib64/libnvrtc-builtins.so.13.3"
    ).read_bytes() == BUILTINS_BYTES


@pytest.mark.parametrize("kind", ["linked-leaf", "linked-parent"])
def test_cuda_extract_rejects_redirected_overlay_destination(
    tmp_path: Path,
    kind: str,
) -> None:
    """Direct extraction cannot overlay verified bytes into a linked target."""
    payload = _payload()
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, _manifest(tmp_path, payload), LINUX_PLATFORM
    ).packages[0]
    external = tmp_path / "outside"
    external.mkdir()
    sentinel = external / "sentinel.txt"
    _ = sentinel.write_bytes(b"unrelated filesystem content")
    if kind == "linked-leaf":
        destination = tmp_path / "toolkit"
        link = destination
        target = external
    else:
        parent = tmp_path / "linked-parent"
        destination = parent / "toolkit"
        link = parent
        target = external
    try:
        _ = link.symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory links unavailable: {error}")

    with pytest.raises(cuda_validation.CudaProvisionError, match="redirect"):
        cuda_validation.extract_cuda_package(
            payload, package, destination, staging=tmp_path / "stage"
        )
    assert sentinel.read_bytes() == b"unrelated filesystem content"
    assert list(external.iterdir()) == [sentinel]
    assert link.is_symlink()


def test_tar_extraction_rejects_parent_escape(tmp_path: Path) -> None:
    """Archive members cannot escape package staging or toolkit roots."""
    payload = _tar_xz({f"{ARCHIVE_ROOT}/../../escape": b"forged"})
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path,
        _manifest(tmp_path, payload),
        LINUX_PLATFORM,
    ).packages[0]

    with pytest.raises(
        cuda_validation.CudaProvisionError,
        match="archive member escapes",
    ):
        cuda_validation.extract_cuda_package(
            payload,
            package,
            tmp_path / "toolkit",
            staging=tmp_path / "staging",
        )

    assert not (tmp_path / "escape").exists()


@pytest.mark.parametrize(
    ("link_target", "error_match"),
    [
        (f"{ARCHIVE_ROOT}/lib64/not-present", "hard link"),
        (f"{ARCHIVE_ROOT}/../../escape", "archive member escapes"),
        ("another-root/lib64/file.so", "hard link outside"),
        ("/tmp/outside.so", "archive member escapes"),
        ("D:/outside.so", "archive member escapes"),
        (f"{ARCHIVE_ROOT}\\..\\escape", "must use forward slashes"),
    ],
)
def test_tar_extraction_rejects_invalid_hardlink_target(
    tmp_path: Path,
    link_target: str,
    error_match: str,
) -> None:
    """Hardlink references need contained target names and resolvable content."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:xz") as archive:
        member = tarfile.TarInfo(f"{ARCHIVE_ROOT}/lib64/alias.so")
        member.type = tarfile.LNKTYPE
        member.linkname = link_target
        archive.addfile(member)
        data = tarfile.TarInfo(BUILTINS_MEMBER)
        data.size = len(BUILTINS_BYTES)
        archive.addfile(data, io.BytesIO(BUILTINS_BYTES))
    payload = output.getvalue()
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, _manifest(tmp_path, payload), LINUX_PLATFORM
    ).packages[0]

    with pytest.raises(cuda_validation.CudaProvisionError, match=error_match):
        cuda_validation.extract_cuda_package(
            payload,
            package,
            tmp_path / "toolkit",
            staging=tmp_path / "staging",
        )
    assert not (tmp_path / "toolkit").exists()


def test_tar_extraction_admits_contained_hardlink(tmp_path: Path) -> None:
    """An in-package hardlink still extracts stable file bytes."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:xz") as archive:
        data = tarfile.TarInfo(NVRTC_MEMBER)
        data.size = len(NVRTC_BYTES)
        archive.addfile(data, io.BytesIO(NVRTC_BYTES))
        link = tarfile.TarInfo(f"{ARCHIVE_ROOT}/lib64/alias.so")
        link.type = tarfile.LNKTYPE
        link.linkname = NVRTC_MEMBER
        archive.addfile(link)
    payload = output.getvalue()
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, _manifest(tmp_path, payload), LINUX_PLATFORM
    ).packages[0]

    cuda_validation.extract_cuda_package(
        payload, package, tmp_path / "toolkit", staging=tmp_path / "staging"
    )
    assert (tmp_path / "toolkit/lib64/alias.so").read_bytes() == NVRTC_BYTES


def test_cuda_tar_hardlink_chain_does_not_lookup_each_member_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Archive-local chain resolution must not repeatedly search the TAR index."""
    output = io.BytesIO()
    chain_length = 200
    with tarfile.open(fileobj=output, mode="w:xz") as archive:
        original = tarfile.TarInfo(NVRTC_MEMBER)
        original.size = len(NVRTC_BYTES)
        archive.addfile(original, io.BytesIO(NVRTC_BYTES))
        previous = NVRTC_MEMBER
        for index in range(chain_length):
            name = f"{ARCHIVE_ROOT}/lib64/alias-{index:03d}.so"
            link = tarfile.TarInfo(name)
            link.type = tarfile.LNKTYPE
            link.linkname = previous
            archive.addfile(link)
            previous = name
    payload = output.getvalue()
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, _manifest(tmp_path, payload), LINUX_PLATFORM,
    ).packages[0]

    def reject_repeated_lookup(_archive: tarfile.TarFile, _name: str) -> None:
        raise AssertionError

    monkeypatch.setattr(tarfile.TarFile, "getmember", reject_repeated_lookup)
    cuda_validation.extract_cuda_package(
        payload, package, tmp_path / "toolkit", staging=tmp_path / "stage",
    )
    if (tmp_path / "toolkit/lib64/alias-199.so").read_bytes() != NVRTC_BYTES:
        pytest.fail("TAR hardlink did not preserve its source bytes")


def test_cuda_tar_hardlink_copies_count_toward_expansion_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every copied link consumes its source bytes in the expansion budget."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:xz") as archive:
        pairs = ((NVRTC_MEMBER, NVRTC_BYTES), (BUILTINS_MEMBER, BUILTINS_BYTES))
        for name, data in pairs:
            member = tarfile.TarInfo(name)
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
        alias = tarfile.TarInfo(f"{ARCHIVE_ROOT}/lib64/alias.so")
        alias.type = tarfile.LNKTYPE
        alias.linkname = NVRTC_MEMBER
        archive.addfile(alias)
    payload = output.getvalue()
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, _manifest(tmp_path, payload), LINUX_PLATFORM,
    ).packages[0]
    monkeypatch.setattr(
        cuda_validation,
        "_MAX_CUDA_EXTRACTED_BYTES",
        len(NVRTC_BYTES) + len(BUILTINS_BYTES),
    )
    with pytest.raises(cuda_validation.CudaProvisionError, match="expanded byte limit"):
        cuda_validation.extract_cuda_package(
            payload, package, tmp_path / "toolkit", staging=tmp_path / "stage",
        )
    if (tmp_path / "toolkit").exists():
        pytest.fail("over-expanded TAR published a toolkit")


@pytest.mark.parametrize(
    "member",
    ("C:/escaped/absolute", "D:drive-relative", "e:/root/escape"),
)
def test_cuda_archive_rejects_windows_drive_members(member: str) -> None:
    """A POSIX archive member may not create a Windows drive path."""
    with pytest.raises(
        cuda_validation.CudaProvisionError, match="escapes package root"
    ):
        _ = cuda_validation._archive_member_path(member)


def test_cuda_archive_extraction_rejects_windows_drive_root(tmp_path: Path) -> None:
    """A forged drive-root archive cannot claim a repository toolkit."""
    payload = _tar_xz({"C:/escape.txt": b"forged"})
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, _manifest(tmp_path, payload), LINUX_PLATFORM
    ).packages[0]
    with pytest.raises(
        cuda_validation.CudaProvisionError, match="escapes package root"
    ):
        cuda_validation.extract_cuda_package(
            payload, package, tmp_path / "toolkit", staging=tmp_path / "staging"
        )


def test_cuda_archive_rejects_host_dependent_backslash_member(
    tmp_path: Path,
) -> None:
    """Windows parent traversal cannot be a literal Linux archive filename."""
    payload = _tar_xz({f"{ARCHIVE_ROOT}/..\\escape": b"forged"})
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, _manifest(tmp_path, payload), LINUX_PLATFORM
    ).packages[0]
    with pytest.raises(
        cuda_validation.CudaProvisionError, match="must use forward slashes"
    ):
        cuda_validation.extract_cuda_package(
            payload, package, tmp_path / "toolkit", staging=tmp_path / "staging"
        )


@pytest.mark.parametrize(
    "stage_kind", ["linked-parent", "linked-stage", "nondirectory-parent"]
)
def test_cuda_provision_rejects_redirected_staging_before_download(
    tmp_path: Path, stage_kind: str
) -> None:
    """Staging must never write outside a physical repository workspace."""
    root = tmp_path / "repository"
    root.mkdir()
    payload = _payload()
    manifest = _manifest(root, payload)
    external = tmp_path / "external"
    external.mkdir()
    sentinel = external / "sentinel.txt"
    _ = sentinel.write_bytes(b"foreign data")
    staging_root = root / ".temp"
    if stage_kind == "linked-parent":
        try:
            staging_root.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")
    elif stage_kind == "linked-stage":
        staging_root.mkdir()
        try:
            (staging_root / f"cuda-provision-{LINUX_PLATFORM}").symlink_to(
                external, target_is_directory=True
            )
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")
    else:
        _ = staging_root.write_bytes(b"not a staging directory")
    downloaded: list[str] = []

    def download(url: str) -> bytes:
        downloaded.append(url)
        return payload

    with pytest.raises(cuda_validation.CudaProvisionError, match="staging"):
        _ = cuda_validation.provision_cuda_manifest(
            root, manifest, LINUX_PLATFORM, downloader=download
        )
    assert not downloaded
    assert sentinel.read_bytes() == b"foreign data"
    assert list(external.iterdir()) == [sentinel]
    assert not (root / TOOLKIT_ROOT).exists()


@pytest.mark.parametrize(
    "target_kind", ["linked-parent", "dangling-leaf", "nondirectory-parent"]
)
def test_cuda_provision_rejects_redirected_destination_before_download(
    tmp_path: Path, target_kind: str
) -> None:
    """The toolkit destination must not follow or replace foreign aliases."""
    root = tmp_path / "repository"
    root.mkdir()
    payload = _payload()
    manifest = _manifest(root, payload)
    external = tmp_path / "external"
    external.mkdir()
    sentinel = external / "sentinel.txt"
    _ = sentinel.write_bytes(b"foreign data")
    if target_kind == "linked-parent":
        try:
            (root / ".dependencies").symlink_to(
                external, target_is_directory=True
            )
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")
    elif target_kind == "nondirectory-parent":
        _ = (root / ".dependencies").write_bytes(b"not a directory")
    else:
        destination = root / TOOLKIT_ROOT
        destination.parent.mkdir(parents=True)
        try:
            destination.symlink_to(external / "not-installed")
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"file links unavailable: {error}")
    downloaded: list[str] = []

    def download(url: str) -> bytes:
        downloaded.append(url)
        return payload

    with pytest.raises(cuda_validation.CudaProvisionError, match="destination"):
        _ = cuda_validation.provision_cuda_manifest(
            root, manifest, LINUX_PLATFORM, downloader=download
        )
    assert not downloaded
    assert sentinel.read_bytes() == b"foreign data"
    assert list(external.iterdir()) == [sentinel]
    if target_kind == "dangling-leaf":
        assert (root / TOOLKIT_ROOT).is_symlink()


def test_cuda_provision_preserves_preexisting_physical_stage(
    tmp_path: Path,
) -> None:
    """A physical staging tree from another owner cannot be erased on entry."""
    payload = _payload()
    manifest = _manifest(tmp_path, payload)
    staging = tmp_path / f".temp/cuda-provision-{LINUX_PLATFORM}"
    staging.mkdir(parents=True)
    sentinel = staging / "foreign-data"
    _ = sentinel.write_bytes(b"preserve unowned staging")
    downloads: list[str] = []

    def download(url: str) -> bytes:
        downloads.append(url)
        return payload

    with pytest.raises(cuda_validation.CudaProvisionError, match="staging"):
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path, manifest, LINUX_PLATFORM, downloader=download
        )
    assert not downloads
    assert sentinel.read_bytes() == b"preserve unowned staging"
    assert not (tmp_path / TOOLKIT_ROOT).exists()


def test_cuda_cleanup_preserves_foreign_staging_replacement(
    tmp_path: Path,
) -> None:
    """Cleanup cannot delete another directory swapped in for owned staging."""
    payload = _payload()
    manifest_path = _manifest(tmp_path, payload)
    staging = tmp_path / ".temp" / f"cuda-provision-{LINUX_PLATFORM}"
    parked = tmp_path / "parked-owned-staging"
    sentinel = staging / "foreign-sentinel"
    foreign_bytes = b"foreign staging must survive cleanup"

    def replace_before_download(_url: str) -> bytes:
        staging.rename(parked)
        staging.mkdir()
        _ = sentinel.write_bytes(foreign_bytes)
        raise RuntimeError("download was canceled")

    with pytest.raises(cuda_validation.CudaProvisionError, match="staging.*changed"):
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path,
            manifest_path,
            LINUX_PLATFORM,
            downloader=replace_before_download,
        )
    assert parked.is_dir()
    assert sentinel.read_bytes() == foreign_bytes
    assert not (tmp_path / TOOLKIT_ROOT).exists()


def test_cuda_never_publishes_swapped_staging_toolkit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign root inserted after marker staging cannot become the toolkit."""
    payload = _payload()
    manifest_path = _manifest(tmp_path, payload)
    staging = tmp_path / ".temp" / f"cuda-provision-{LINUX_PLATFORM}"
    parked = tmp_path / "parked-valid-staging"
    foreign_bytes = b"not a verified CUDA package"
    native_writer = cuda_validation._write_staged_file_exclusively
    inserted = False

    def replace_after_marker(path: Path, content: bytes, label: str) -> tuple[int, int]:
        nonlocal inserted
        receipt = native_writer(path, content, label)
        if label != "CUDA completion marker":
            return receipt
        staging.rename(parked)
        foreign_toolkit = staging / "toolkit"
        foreign_toolkit.mkdir(parents=True)
        _ = (foreign_toolkit / "forged.so").write_bytes(foreign_bytes)
        _ = (foreign_toolkit / cuda_validation.CUDA_PROVISION_MARKER).write_bytes(
            content
        )
        inserted = True
        return receipt

    with monkeypatch.context() as isolated:
        isolated.setattr(
            cuda_validation, "_write_staged_file_exclusively", replace_after_marker
        )
        with pytest.raises(cuda_validation.CudaProvisionError, match="staging.*changed"):
            _ = cuda_validation.provision_cuda_manifest(
                tmp_path,
                manifest_path,
                LINUX_PLATFORM,
                downloader=_download_fixture(payload),
            )
    assert inserted
    assert not (tmp_path / TOOLKIT_ROOT).exists()
    assert (staging / "toolkit/forged.so").read_bytes() == foreign_bytes
    assert (parked / "toolkit/lib64/libnvrtc.so.13").read_bytes() == NVRTC_BYTES


def test_cuda_never_publishes_swapped_toolkit_leaf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced staged toolkit directory cannot carry foreign bytes out."""
    payload = _payload()
    manifest_path = _manifest(tmp_path, payload)
    staging = tmp_path / ".temp" / f"cuda-provision-{LINUX_PLATFORM}"
    staged_toolkit = staging / "toolkit"
    parked = staging / "parked-toolkit"
    native_writer = cuda_validation._write_staged_file_exclusively
    injected = False

    def replace_after_marker(path: Path, content: bytes, label: str) -> tuple[int, int]:
        nonlocal injected
        receipt = native_writer(path, content, label)
        if label != "CUDA completion marker":
            return receipt
        staged_toolkit.rename(parked)
        staged_toolkit.mkdir()
        _ = (staged_toolkit / "forged.so").write_bytes(b"not a verified library")
        _ = (staged_toolkit / cuda_validation.CUDA_PROVISION_MARKER).write_bytes(
            content
        )
        injected = True
        return receipt

    with monkeypatch.context() as isolated:
        isolated.setattr(
            cuda_validation, "_write_staged_file_exclusively", replace_after_marker
        )
        with pytest.raises(cuda_validation.CudaProvisionError, match="staging.*changed"):
            _ = cuda_validation.provision_cuda_manifest(
                tmp_path,
                manifest_path,
                LINUX_PLATFORM,
                downloader=_download_fixture(payload),
            )
    assert injected
    assert not (tmp_path / TOOLKIT_ROOT).exists()


def test_cuda_never_publishes_modified_completion_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-write marker mutation cannot authenticate a published toolkit."""
    payload = _payload()
    manifest = _manifest(tmp_path, payload)
    original_writer = cuda_validation._write_staged_file_exclusively
    tampered = False

    def mutate_after_write(path: Path, content: bytes, label: str) -> tuple[int, int]:
        nonlocal tampered
        receipt = original_writer(path, content, label)
        if label == "CUDA completion marker":
            with path.open("r+b") as stream:
                _ = stream.write(b"!" + content[1:])
            tampered = True
        return receipt

    with monkeypatch.context() as isolated:
        isolated.setattr(
            cuda_validation, "_write_staged_file_exclusively", mutate_after_write
        )
        with pytest.raises(cuda_validation.CudaProvisionError, match="marker"):
            _ = cuda_validation.provision_cuda_manifest(
                tmp_path, manifest, LINUX_PLATFORM, downloader=_download_fixture(payload)
            )
    assert tampered
    assert not (tmp_path / TOOLKIT_ROOT).exists()


def test_cuda_never_publishes_hardlinked_completion_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid-looking marker must not share ownership with an outside file."""
    payload = _payload()
    manifest = _manifest(tmp_path, payload)
    external = tmp_path / "shared-marker"
    original_writer = cuda_validation._write_staged_file_exclusively
    linked = False

    def link_after_write(path: Path, content: bytes, label: str) -> tuple[int, int]:
        nonlocal linked
        receipt = original_writer(path, content, label)
        if label == "CUDA completion marker":
            _ = external.write_bytes(content)
            path.unlink()
            try:
                os.link(external, path)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"hard links unavailable: {error}")
            linked = True
        return receipt

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation, "_write_staged_file_exclusively", link_after_write)
        with pytest.raises(cuda_validation.CudaProvisionError, match="marker"):
            _ = cuda_validation.provision_cuda_manifest(
                tmp_path, manifest, LINUX_PLATFORM, downloader=_download_fixture(payload)
            )
    assert linked
    assert not (tmp_path / TOOLKIT_ROOT).exists()
    assert external.read_bytes().startswith(b'{"manifest_sha256"')


def test_cuda_never_replaces_late_occupied_toolkit_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late-arriving empty destination belongs to a different owner."""
    payload = _payload()
    manifest_path = _manifest(tmp_path, payload)
    destination = tmp_path / TOOLKIT_ROOT
    native_writer = cuda_validation._write_staged_file_exclusively
    occupied = False

    def occupy_destination(path: Path, data: bytes, label: str) -> tuple[int, int]:
        nonlocal occupied
        receipt = native_writer(path, data, label)
        if label == "CUDA completion marker":
            destination.mkdir(parents=True)
            occupied = True
        return receipt

    with monkeypatch.context() as isolated:
        isolated.setattr(
            cuda_validation, "_write_staged_file_exclusively", occupy_destination
        )
        with pytest.raises(cuda_validation.CudaProvisionError, match="destination"):
            _ = cuda_validation.provision_cuda_manifest(
                tmp_path, manifest_path, LINUX_PLATFORM,
                downloader=_download_fixture(payload),
            )
    assert occupied
    assert destination.is_dir()
    assert not list(destination.iterdir())


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux renameat2")
def test_cuda_publication_does_not_follow_late_parent_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late alias cannot redirect the final toolkit rename outside root."""
    payload = _payload()
    manifest = _manifest(tmp_path, payload)
    parent = (tmp_path / TOOLKIT_ROOT).parent
    staged = tmp_path / f".temp/cuda-provision-{LINUX_PLATFORM}/toolkit"
    parked = tmp_path / "parked-toolkit-parent"
    outside = tmp_path / "outside-toolkit"
    outside.mkdir()
    sentinel = outside / "sentinel"
    _ = sentinel.write_bytes(b"external data")
    native_rename = cuda_validation._rename_cuda_toolkit_no_replace  # pyright: ignore[reportPrivateUsage]
    swapped = False

    def race_final_rename(
        source: str,
        destination: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
    ) -> None:
        nonlocal swapped
        if source == staged.name:
            _ = parent.rename(parked)
            _ = parent.symlink_to(outside, target_is_directory=True)
            swapped = True
        native_rename(source, destination, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(
        cuda_validation, "_rename_cuda_toolkit_no_replace", race_final_rename
    )
    with pytest.raises(cuda_validation.CudaProvisionError, match="destination"):
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path,
            manifest,
            LINUX_PLATFORM,
            downloader=_download_fixture(payload),
        )
    assert swapped
    assert sentinel.read_bytes() == b"external data"
    assert not (outside / "toolkit").exists()
    assert (parked / "toolkit/lib64/libnvrtc.so.13").read_bytes() == NVRTC_BYTES


@pytest.mark.skipif(
    os.name != "posix", reason="requires POSIX directory descriptors"
)
def test_cuda_publication_rejects_foreign_parent_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A descriptor for another directory cannot authorize CUDA publication."""
    payload = _payload()
    manifest = _manifest(tmp_path, payload)
    parent = (tmp_path / TOOLKIT_ROOT).parent
    outside = tmp_path / "outside-directory"
    outside.mkdir()
    native_open = os.open
    substituted = False

    def open_foreign_parent(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal substituted
        if Path(path) == parent:
            substituted = True
            return native_open(outside, flags, mode)
        return native_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", open_foreign_parent)
    with pytest.raises(cuda_validation.CudaProvisionError, match="descriptor"):
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path,
            manifest,
            LINUX_PLATFORM,
            downloader=_download_fixture(payload),
        )
    assert substituted
    assert not tuple(outside.iterdir())
    assert not (parent / "toolkit").exists()


def test_cuda_never_publishes_same_content_marker_inode_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An identical marker in a new inode is not the owned staging write."""
    payload = _payload()
    manifest = _manifest(tmp_path, payload)
    original_writer = cuda_validation._write_staged_file_exclusively
    substituted = False

    def replace_marker(path: Path, content: bytes, label: str) -> tuple[int, int]:
        nonlocal substituted
        receipt = original_writer(path, content, label)
        if label == "CUDA completion marker":
            path.unlink()
            _ = path.write_bytes(content)
            substituted = True
        return receipt

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation, "_write_staged_file_exclusively", replace_marker)
        with pytest.raises(cuda_validation.CudaProvisionError, match="marker"):
            _ = cuda_validation.provision_cuda_manifest(
                tmp_path, manifest, LINUX_PLATFORM, downloader=_download_fixture(payload)
            )
    assert substituted
    assert not (tmp_path / TOOLKIT_ROOT).exists()


def test_cuda_rejects_oversized_completion_marker_before_download(
    tmp_path: Path,
) -> None:
    """Known impossible marker size must fail before network or staging."""
    manifest_path = _manifest(tmp_path, _payload())
    document = cast("dict[str, object]", json.loads(manifest_path.read_text()))
    original = cast("list[dict[str, object]]", document["packages"])[0]
    packages: list[dict[str, object]] = []
    for index in range(200):
        name = f"cuda_package_{index:03d}"
        packages.append({
            **original,
            "name": name,
            "relative_path": f"{name}/{LINUX_PLATFORM}/{name}-archive.tar.xz",
        })
    document["packages"] = packages
    _ = manifest_path.write_text(json.dumps(document))
    manifest = cuda_validation.load_cuda_provision_manifest(
        tmp_path, manifest_path, LINUX_PLATFORM
    )
    assert len(cuda_validation._marker_bytes(manifest)) > cuda_validation._MAX_MARKER_BYTES
    contacted: list[str] = []

    def download(url: str) -> bytes:
        contacted.append(url)
        return _payload()

    with pytest.raises(cuda_validation.CudaProvisionError, match="marker exceeds byte limit"):
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path, manifest_path, LINUX_PLATFORM, downloader=download
        )
    assert not contacted
    assert not (tmp_path / ".temp/cuda-provision-linux-x86_64").exists()
    assert not (tmp_path / TOOLKIT_ROOT).exists()


def test_provision_is_idempotent_after_exact_marker(tmp_path: Path) -> None:
    """A completed exact toolkit never redownloads admitted package bytes."""
    payload = _payload()
    manifest_path = _manifest(tmp_path, payload)
    calls: list[str] = []

    def download(url: str) -> bytes:
        calls.append(url)
        return payload

    first = cuda_validation.provision_cuda_manifest(
        tmp_path,
        manifest_path,
        LINUX_PLATFORM,
        downloader=download,
    )
    second = cuda_validation.provision_cuda_manifest(
        tmp_path,
        manifest_path,
        LINUX_PLATFORM,
        downloader=download,
    )

    assert first == second == tmp_path / TOOLKIT_ROOT
    assert len(calls) == 1
    assert calls[0] == cuda_validation.NVIDIA_CUDA_REDIST_BASE + PACKAGE_PATH
    assert (first / cuda_validation.CUDA_PROVISION_MARKER).is_file()
    assert not (tmp_path / ".temp/cuda-provision-linux-x86_64").exists()


def _fixture_selector(root: Path) -> Path:
    manifest_root = (root / project.CUDA_TOOLCHAIN_MANIFEST).parent
    manifest_root.mkdir(parents=True)
    linux_manifest = manifest_root / "toolchain-linux-x86_64.json"
    _ = linux_manifest.write_text(
        json.dumps({
            "schema_version": 1,
            "platform": LINUX_PLATFORM,
            "toolkit_root": TOOLKIT_ROOT,
        }),
        encoding="utf-8",
        newline="\n",
    )
    _ = (root / project.CUDA_TOOLCHAIN_INDEX).write_text(
        json.dumps({
            "schema_version": 1,
            "platforms": {
                LINUX_PLATFORM: {
                    "manifest": linux_manifest.name,
                    "loader": "cdll",
                    "driver_library": "libcuda.so.1",
                    "nvrtc_library": "lib64/libnvrtc.so.13",
                }
            },
        }),
        encoding="utf-8",
        newline="\n",
    )
    return linux_manifest


def _recording_provisioner(
    calls: list[tuple[Path, Path, str]],
) -> Callable[[Path, Path, str], Path]:
    def provision(root: Path, manifest: Path, platform_id: str) -> Path:
        calls.append((root, manifest, platform_id))
        return root / TOOLKIT_ROOT

    return provision


def test_project_cuda_provisioning_is_disabled_by_default(
    tmp_path: Path,
) -> None:
    """Ordinary bootstrap orchestration never invokes a CUDA downloader."""
    manifest = _fixture_selector(tmp_path)
    calls: list[tuple[Path, Path, str]] = []

    result = project.provision_cuda_if_requested(
        tmp_path,
        LINUX_PLATFORM,
        requested=False,
        provisioner=_recording_provisioner(calls),
    )

    assert manifest.is_file()
    assert result is None
    assert calls == []


def test_project_cuda_provisioning_uses_selected_manifest(
    tmp_path: Path,
) -> None:
    """Explicit provisioning passes only the selected host manifest."""
    manifest = _fixture_selector(tmp_path)
    calls: list[tuple[Path, Path, str]] = []

    result = project.provision_cuda_if_requested(
        tmp_path,
        LINUX_PLATFORM,
        requested=True,
        provisioner=_recording_provisioner(calls),
    )

    assert result == tmp_path / TOOLKIT_ROOT
    assert calls == [(tmp_path, manifest, LINUX_PLATFORM)]


@pytest.mark.parametrize("redirect", ["file", "directory"])
def test_provision_manifest_rejects_redirected_source(
    tmp_path: Path,
    redirect: str,
) -> None:
    """Explicit provisioning may not trust linked manifest authority."""
    real = tmp_path / "real"
    real.mkdir()
    source = _manifest(real, _payload())
    if redirect == FILE_REDIRECT:
        alias = tmp_path / "linked.json"
    else:
        alias = tmp_path / "linked-dir"
    try:
        if redirect == FILE_REDIRECT:
            _ = alias.symlink_to(source)
        else:
            _ = alias.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    manifest = alias if redirect == FILE_REDIRECT else alias / source.name
    with pytest.raises(
        cuda_validation.CudaProvisionError, match=r"regular|redirect"
    ):
        _ = cuda_validation.load_cuda_provision_manifest(
            tmp_path, manifest, LINUX_PLATFORM
        )


def test_provision_manifest_rejects_oversized_file(tmp_path: Path) -> None:
    """Large authority documents fail before parsing into package records."""
    manifest = _manifest(tmp_path, _payload())
    with manifest.open("wb") as stream:
        _ = stream.truncate(1024 * 1024 + 1)
    with pytest.raises(cuda_validation.CudaProvisionError, match="byte limit"):
        _ = cuda_validation.load_cuda_provision_manifest(
            tmp_path, manifest, LINUX_PLATFORM
        )


def test_provision_manifest_rejects_directory_and_fifo(tmp_path: Path) -> None:
    """Neither a directory nor writerless FIFO may stand in for JSON."""
    manifest = _manifest(tmp_path, _payload())
    manifest.unlink()
    manifest.mkdir()
    with pytest.raises(cuda_validation.CudaProvisionError, match="regular"):
        _ = cuda_validation.load_cuda_provision_manifest(
            tmp_path, manifest, LINUX_PLATFORM
        )
    manifest.rmdir()
    mkfifo = getattr(os, "mkfifo", None)
    if mkfifo is None:
        pytest.skip("FIFO unavailable on host")
    mkfifo(manifest)
    with pytest.raises(cuda_validation.CudaProvisionError, match="regular"):
        _ = cuda_validation.load_cuda_provision_manifest(
            tmp_path, manifest, LINUX_PLATFORM
        )


def test_provision_manifest_rejects_same_byte_inode_swap_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The manifest descriptor must refer to the admitted named inode."""
    manifest = _manifest(tmp_path, _payload())
    replacement = tmp_path / "replacement.json"
    _ = replacement.write_bytes(manifest.read_bytes())
    real_open = os.open
    swapped = False

    def swap_on_open(path: Path, flags: int) -> int:
        nonlocal swapped
        if path == manifest:
            _ = replacement.replace(manifest)
            swapped = True
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_on_open)
    with pytest.raises(cuda_validation.CudaProvisionError, match="changed"):
        _ = cuda_validation.load_cuda_provision_manifest(
            tmp_path, manifest, LINUX_PLATFORM
        )
    assert swapped


def test_provision_manifest_rejects_in_place_modification_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Content changes under the same inode invalidate package authority."""
    manifest = _manifest(tmp_path, _payload())
    real_lstat = Path.lstat
    observed = 0

    def modify_at_recheck(path: Path) -> os.stat_result:
        nonlocal observed
        if path == manifest:
            observed += 1
            if observed == SOURCE_RECHECK:
                with manifest.open("r+b") as stream:
                    _ = stream.write(b"x")
        return real_lstat(path)

    monkeypatch.setattr(Path, "lstat", modify_at_recheck)
    with pytest.raises(cuda_validation.CudaProvisionError, match="changed"):
        _ = cuda_validation.load_cuda_provision_manifest(
            tmp_path, manifest, LINUX_PLATFORM
        )
    assert observed == SOURCE_RECHECK


def test_provision_manifest_rejects_inode_swap_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The named source must still match the opened descriptor after read."""
    manifest = _manifest(tmp_path, _payload())
    replacement = tmp_path / "replacement.json"
    _ = replacement.write_bytes(manifest.read_bytes())
    real_lstat = Path.lstat
    observed = 0

    def replace_at_recheck(path: Path) -> os.stat_result:
        nonlocal observed
        if path == manifest:
            observed += 1
            if observed == SOURCE_RECHECK:
                _ = replacement.replace(manifest)
        return real_lstat(path)

    monkeypatch.setattr(Path, "lstat", replace_at_recheck)
    with pytest.raises(cuda_validation.CudaProvisionError, match="changed"):
        _ = cuda_validation.load_cuda_provision_manifest(
            tmp_path, manifest, LINUX_PLATFORM
        )
    assert observed == SOURCE_RECHECK


@pytest.mark.parametrize("source_kind", ["manifest", "marker"])
def test_cuda_authority_rejects_external_hardlink(
    tmp_path: Path,
    source_kind: str,
) -> None:
    """External aliases cannot certify a tracked CUDA manifest or marker."""
    payload = _payload()
    manifest = _manifest(tmp_path, payload)
    source = manifest
    if source_kind == "marker":
        toolkit = cuda_validation.provision_cuda_manifest(
            tmp_path,
            manifest,
            LINUX_PLATFORM,
            downloader=_download_fixture(payload),
        )
        source = toolkit / cuda_validation.CUDA_PROVISION_MARKER
    linked = tmp_path / "external-authority"
    try:
        os.link(source, linked)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hard links unavailable: {error}")
    assert source.stat().st_nlink == 2
    if source_kind == "manifest":
        with pytest.raises(cuda_validation.CudaProvisionError, match="linked"):
            _ = cuda_validation.load_cuda_provision_manifest(
                tmp_path, manifest, LINUX_PLATFORM
            )
    else:
        with pytest.raises(cuda_validation.CudaProvisionError, match="exact"):
            _ = cuda_validation.provision_cuda_manifest(
                tmp_path,
                manifest,
                LINUX_PLATFORM,
                downloader=_download_fixture(payload),
            )
    assert linked.read_bytes() == source.read_bytes()


class UnprintableHostOSError(OSError):
    """A host adapter whose diagnostic cannot safely be rendered."""

    @override
    def __str__(self) -> str:
        raise AssertionError("host error text must not be formatted")


class UnprintableHostRuntimeError(RuntimeError):
    """An additional fault family with a hostile message adapter."""

    @override
    def __str__(self) -> str:
        raise AssertionError("host error text must not be formatted")


@pytest.mark.parametrize(
    "fault_type", [UnprintableHostOSError, UnprintableHostRuntimeError]
)
@pytest.mark.parametrize("phase", ["initial-lstat", "final-lstat", "fstat"])
def test_cuda_authority_status_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    phase: str,
) -> None:
    """Native authority receipts fail typed, without formatting host errors."""
    source = _manifest(tmp_path, _payload())
    native_lstat = Path.lstat
    native_fstat = os.fstat
    failure = fault_type("unprintable host status")
    calls = 0

    def lstat_fault(path: Path) -> os.stat_result:
        nonlocal calls
        if path == source:
            calls += 1
            if (phase == "initial-lstat" and calls == 1) or (
                phase == "final-lstat" and calls == SOURCE_RECHECK
            ):
                raise failure
        return native_lstat(path)

    def fstat_fault(descriptor: int) -> os.stat_result:
        if phase == "fstat":
            raise failure
        return native_fstat(descriptor)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", lstat_fault)
        isolated.setattr(os, "fstat", fstat_fault)
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="status"
        ) as caught:
            _ = cuda_validation.load_cuda_provision_manifest(
                tmp_path, source, LINUX_PLATFORM
            )
    assert caught.value.__cause__ is failure



@pytest.mark.parametrize(
    "phase", ["staging-root", "package-root", "destination-parent"]
)
def test_cuda_provision_types_directory_creation_host_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    """Provisioning reports typed directory-creation faults without host text."""
    payload = _payload()
    manifest = _manifest(tmp_path, payload)
    staging = tmp_path / f".temp/cuda-provision-{LINUX_PLATFORM}"
    if phase == "staging-root":
        target = staging
    elif phase == "package-root":
        target = staging / "packages" / PACKAGE_NAME
    else:
        target = (tmp_path / TOOLKIT_ROOT).parent
    native_mkdir = Path.mkdir
    native_os_mkdir = os.mkdir
    failure = UnprintableHostOSError("denied directory creation")
    injected = False

    def fail_mkdir(
        path: Path,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        nonlocal injected
        if path == target:
            injected = True
            raise failure
        native_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    def fail_os_mkdir(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal injected
        if os.name == "posix" and path == target.name and dir_fd is not None:
            injected = True
            raise failure
        native_os_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "mkdir", fail_mkdir)
        isolated.setattr(os, "mkdir", fail_os_mkdir)
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="creation"
        ) as caught:
            _ = cuda_validation.provision_cuda_manifest(
                tmp_path,
                manifest,
                LINUX_PLATFORM,
                downloader=_download_fixture(payload),
            )
    assert injected
    assert caught.value.__cause__ is failure
    assert not (tmp_path / TOOLKIT_ROOT).exists()


def test_cuda_marker_status_host_runtime_fault_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A host status adapter fault cannot reauthorize an installed toolkit."""
    payload = _payload()
    source = _manifest(tmp_path, payload)
    manifest = cuda_validation.load_cuda_provision_manifest(
        tmp_path, source, LINUX_PLATFORM
    )
    root = cuda_validation.provision_cuda_manifest(
        tmp_path, source, LINUX_PLATFORM, downloader=_download_fixture(payload)
    )
    marker = root / cuda_validation.CUDA_PROVISION_MARKER
    native_lstat = Path.lstat
    failure = UnprintableHostRuntimeError("host marker status")

    def fail_marker_status(path: Path) -> os.stat_result:
        if path == marker:
            raise failure
        return native_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_marker_status)
    assert not cuda_validation._completed_toolkit_matches(manifest)


@pytest.mark.parametrize("source_kind", ["manifest", "marker"])
@pytest.mark.parametrize(
    "fault_type",
    [
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        UnprintableHostOSError,
        UnprintableHostRuntimeError,
    ],
)
def test_cuda_source_fdopen_fault_closes_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
    fault_type: type[Exception],
) -> None:
    """A stream-wrapper fault closes authority and completion-marker descriptors."""
    payload = _payload()
    manifest = _manifest(tmp_path, payload)
    source = manifest
    if source_kind == "marker":
        root = cuda_validation.provision_cuda_manifest(
            tmp_path,
            manifest,
            LINUX_PLATFORM,
            downloader=_download_fixture(payload),
        )
        source = root / cuda_validation.CUDA_PROVISION_MARKER
    native_open = os.open
    native_fdopen = os.fdopen
    descriptors: list[int] = []
    fault = fault_type("injected CUDA source wrapper failure")

    def capture_open(path: Path, flags: int) -> int:
        descriptor = native_open(path, flags)
        if path == source:
            descriptors.append(descriptor)
        return descriptor

    def fail_fdopen(descriptor: int, mode: str) -> object:
        if descriptor in descriptors and mode == "rb":
            raise fault
        return native_fdopen(descriptor, mode)

    monkeypatch.setattr(os, "open", capture_open)
    monkeypatch.setattr(os, "fdopen", fail_fdopen)
    try:
        with pytest.raises(cuda_validation.CudaProvisionError) as caught:
            if source_kind == "manifest":
                _ = cuda_validation.load_cuda_provision_manifest(
                    tmp_path, manifest, LINUX_PLATFORM
                )
            else:
                _ = cuda_validation.provision_cuda_manifest(
                    tmp_path, manifest, LINUX_PLATFORM,
                    downloader=_download_fixture(payload),
                )
        if source_kind == "manifest":
            assert "cannot read CUDA provision manifest" in str(caught.value)
            assert "host stream wrapper failed" in str(caught.value)
            assert caught.value.__cause__ is fault
        else:
            assert "exists without the exact provision marker" in str(caught.value)
        assert len(descriptors) == 1
        with pytest.raises(OSError, match=r"Bad file descriptor|Invalid handle"):
            _ = os.fstat(descriptors[0])
    finally:
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass


def test_provision_completion_marker_rejects_linked_source(
    tmp_path: Path,
) -> None:
    """A linked byte-identical marker cannot claim an installed toolkit."""
    payload = _payload()
    manifest_path = _manifest(tmp_path, payload)
    first = cuda_validation.provision_cuda_manifest(
        tmp_path,
        manifest_path,
        LINUX_PLATFORM,
        downloader=_download_fixture(payload),
    )
    marker = first / cuda_validation.CUDA_PROVISION_MARKER
    external = tmp_path / "external-marker.json"
    _ = external.write_bytes(marker.read_bytes())
    marker.unlink()
    try:
        _ = marker.symlink_to(external)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(
        cuda_validation.CudaProvisionError,
        match="exists without the exact provision marker",
    ):
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path,
            manifest_path,
            LINUX_PLATFORM,
            downloader=_download_fixture(payload),
        )


def test_provision_completion_marker_rejects_redirected_parent(
    tmp_path: Path,
) -> None:
    """A linked toolkit root cannot claim completion through a marker."""
    payload = _payload()
    manifest_path = _manifest(tmp_path, payload)
    real_root = tmp_path / "real"
    _ = cuda_validation.provision_cuda_manifest(
        real_root,
        manifest_path,
        LINUX_PLATFORM,
        downloader=_download_fixture(payload),
    )
    fake_root = tmp_path / "fake"
    try:
        _ = fake_root.symlink_to(real_root, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(
        cuda_validation.CudaProvisionError,
        match="exists without the exact provision marker",
    ):
        _ = cuda_validation.provision_cuda_manifest(
            fake_root,
            manifest_path,
            LINUX_PLATFORM,
            downloader=_download_fixture(payload),
        )


_BAD_WRITE_RESULTS = ("short", "overlong", "boolean", "missing")
_TAR_FORMAT = "tar"
_ZIP_FORMAT = "zip"
_ZIP_PACKAGE_PATH = "cuda_nvrtc/linux-x86_64/cuda_nvrtc-fixture.zip"


def _bad_write_count(kind: str, expected: int) -> int:
    """Simulate an invalid host byte write result.

    Returns:
        A short, overstated, boolean, or missing count.

    """
    results: dict[str, object] = {
        "short": expected - 1,
        "overlong": expected + 1,
        "boolean": True,
        "missing": None,
    }
    return cast("int", results[kind])


def _zip_payload() -> bytes:
    """Build a matching synthetic NVIDIA zip archive.

    Returns:
        An in-memory archive containing both required library members.

    """
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode="w") as archive:
        archive.writestr(NVRTC_MEMBER, NVRTC_BYTES)
        archive.writestr(BUILTINS_MEMBER, BUILTINS_BYTES)
    return stream.getvalue()



def test_cuda_tar_rejects_excess_member_count_before_link_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An overpopulated archive cannot trigger unbounded hardlink traversal."""
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w:xz") as archive:
        for index in range(3):
            member = tarfile.TarInfo(f"{ARCHIVE_ROOT}/lib64/link-{index}")
            member.type = tarfile.LNKTYPE
            member.linkname = f"{ARCHIVE_ROOT}/lib64/missing"
            archive.addfile(member)
    payload = stream.getvalue()
    manifest = _manifest(tmp_path, payload)
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, manifest, LINUX_PLATFORM
    ).packages[0]
    monkeypatch.setattr(cuda_validation, "_MAX_CUDA_ARCHIVE_MEMBERS", 2)

    def reject_unbounded_inventory(_archive: tarfile.TarFile) -> None:
        raise AssertionError

    monkeypatch.setattr(tarfile.TarFile, "getmembers", reject_unbounded_inventory)
    with pytest.raises(cuda_validation.CudaProvisionError, match="member count"):
        cuda_validation.extract_cuda_package(
            payload, package, tmp_path / "toolkit", staging=tmp_path / "stage"
        )
    assert not (tmp_path / "toolkit/lib64").exists()


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("nvrtc.dll", "NVRTC.dll"),
        ("subdir/nvrtc.dll", "subdir/./nvrtc.dll"),
        ("subdir/nvrtc.dll", "subdir//nvrtc.dll"),
        ("s\u00e4mple.dll", "sa\u0308mple.dll"),
    ],
)
def test_cuda_tar_rejects_cross_platform_path_aliases(
    tmp_path: Path, first: str, second: str,
) -> None:
    """TAR member spellings cannot collide when installed on Windows."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:xz") as archive:
        for name in (first, second):
            member = tarfile.TarInfo(f"{ARCHIVE_ROOT}/lib64/{name}")
            member.size = len(NVRTC_BYTES)
            archive.addfile(member, io.BytesIO(NVRTC_BYTES))
    payload = output.getvalue()
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, _manifest(tmp_path, payload), LINUX_PLATFORM,
    ).packages[0]
    with pytest.raises(
        cuda_validation.CudaProvisionError, match="TAR member path alias",
    ):
        cuda_validation.extract_cuda_package(
            payload, package, tmp_path / "toolkit", staging=tmp_path / "stage",
        )
    if (tmp_path / "toolkit").exists():
        pytest.fail("aliased TAR members published a toolkit")


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("nvrtc.dll", "NVRTC.dll"),
        ("subdir/nvrtc.dll", "subdir/./nvrtc.dll"),
        ("subdir/nvrtc.dll", "subdir//nvrtc.dll"),
        ("s\u00e4mple.dll", "sa\u0308mple.dll"),
    ],
)
def test_cuda_zip_rejects_cross_platform_path_aliases(
    tmp_path: Path, first: str, second: str
) -> None:
    """Case or lexical aliases must not materialize different Windows files."""
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode="w") as archive:
        archive.writestr(f"{ARCHIVE_ROOT}/lib64/{first}", b"one")
        archive.writestr(f"{ARCHIVE_ROOT}/lib64/{second}", b"two")
    payload = stream.getvalue()
    manifest = _manifest(tmp_path, payload, {"relative_path": _ZIP_PACKAGE_PATH})
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, manifest, LINUX_PLATFORM
    ).packages[0]
    with pytest.raises(cuda_validation.CudaProvisionError, match="ZIP member path alias"):
        cuda_validation.extract_cuda_package(
            payload, package, tmp_path / "toolkit", staging=tmp_path / "stage"
        )
    assert not (tmp_path / "toolkit/lib64").exists()


@pytest.mark.parametrize(
    ("create_system", "external_attr", "name_suffix"),
    [
        (3, (0o120777 << 16), "libnvrtc.so"),
        (3, (0o010644 << 16), "libnvrtc.so"),
        (3, (0o040755 << 16), "libnvrtc.so"),
        (3, (0o100644 << 16), "subdir/"),
        (0, 0x10, "libnvrtc.so"),
        (0, 0x08, "libnvrtc.so"),
    ],
)
def test_cuda_zip_rejects_special_or_conflicting_member_types(
    tmp_path: Path, create_system: int, external_attr: int, name_suffix: str
) -> None:
    """Metadata-signaled links, devices or fake directories fail before writes."""
    payload_stream = io.BytesIO()
    entry = zipfile.ZipInfo(f"{ARCHIVE_ROOT}/lib64/{name_suffix}")
    entry.create_system = create_system
    entry.external_attr = external_attr
    with zipfile.ZipFile(payload_stream, mode="w") as archive:
        archive.writestr(entry, b"" if name_suffix.endswith("/") else b"unsafe member")
    payload = payload_stream.getvalue()
    manifest = _manifest(tmp_path, payload, {"relative_path": _ZIP_PACKAGE_PATH})
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, manifest, LINUX_PLATFORM
    ).packages[0]
    with pytest.raises(cuda_validation.CudaProvisionError, match="ZIP member type"):
        cuda_validation.extract_cuda_package(
            payload, package, tmp_path / "toolkit", staging=tmp_path / "stage"
        )
    assert not (tmp_path / "toolkit/lib64").exists()


@pytest.mark.parametrize("archive_format", [_TAR_FORMAT, _ZIP_FORMAT])
@pytest.mark.parametrize(
    "member_name", ["NUL.txt", "aux", "library:alternate.dll", "folder./module"]
)
def test_cuda_archive_rejects_windows_reserved_member_names(
    tmp_path: Path, archive_format: str, member_name: str
) -> None:
    """Archive paths cannot create Windows devices, aliases or ADS members."""
    name = f"{ARCHIVE_ROOT}/lib64/{member_name}"
    if archive_format == _TAR_FORMAT:
        payload = _tar_xz({name: NVRTC_BYTES})
        package_path = PACKAGE_PATH
    else:
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, mode="w") as archive:
            archive.writestr(name, NVRTC_BYTES)
        payload = stream.getvalue()
        package_path = _ZIP_PACKAGE_PATH
    manifest = _manifest(tmp_path, payload, {"relative_path": package_path})
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, manifest, LINUX_PLATFORM
    ).packages[0]
    with pytest.raises(cuda_validation.CudaProvisionError, match="Windows-reserved"):
        cuda_validation.extract_cuda_package(
            payload, package, tmp_path / "toolkit", staging=tmp_path / "stage"
        )
    assert not (tmp_path / "toolkit/lib64").exists()


@pytest.mark.parametrize("archive_format", [_TAR_FORMAT, _ZIP_FORMAT])
def test_cuda_archive_host_fault_does_not_render_foreign_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    archive_format: str,
) -> None:
    """Tar and ZIP extraction failures keep typed causes, not host messages."""
    is_zip = archive_format == _ZIP_FORMAT
    payload = _zip_payload() if is_zip else _payload()
    manifest = _manifest(
        tmp_path,
        payload,
        {"relative_path": _ZIP_PACKAGE_PATH if is_zip else PACKAGE_PATH},
    )
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, manifest, LINUX_PLATFORM
    ).packages[0]
    native_mkdir = Path.mkdir
    native_os_mkdir = os.mkdir
    failure = UnprintableHostOSError("host extraction failure")
    injected = False

    def fault_mkdir(
        path: Path,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        nonlocal injected
        if os.name != "posix" and path.name == "lib64":
            injected = True
            raise failure
        native_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    def fault_os_mkdir(
        path: str | os.PathLike[str], mode: int = 0o777,
        *, dir_fd: int | None = None,
    ) -> None:
        nonlocal injected
        if os.name == "posix" and path == "lib64" and dir_fd is not None:
            injected = True
            raise failure
        native_os_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "mkdir", fault_mkdir)
        isolated.setattr(os, "mkdir", fault_os_mkdir)
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="destination parent creation"
        ) as caught:
            cuda_validation.extract_cuda_package(
                payload,
                package,
                tmp_path / "toolkit",
                staging=tmp_path / "staging",
            )
    assert injected
    assert caught.value.__cause__ is failure
    assert not (tmp_path / "toolkit").exists()


def _inject_short_write(
    monkeypatch: pytest.MonkeyPatch,
    invalid_count: str,
) -> None:
    native_write = os.write

    def wrong_write(descriptor: int, data: bytes) -> int:
        if data == NVRTC_BYTES:
            _ = native_write(descriptor, data[:-1])
            return _bad_write_count(invalid_count, len(data))
        return native_write(descriptor, data)

    monkeypatch.setattr(os, "write", wrong_write)


@pytest.mark.parametrize("invalid_count", list(_BAD_WRITE_RESULTS))
@pytest.mark.parametrize("archive_format", [_TAR_FORMAT, _ZIP_FORMAT])
def test_package_extraction_rejects_incomplete_member_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    invalid_count: str,
    archive_format: str,
) -> None:
    """Neither tar nor zip archive members may report incomplete writes."""
    is_tar = archive_format == _TAR_FORMAT
    payload = _payload() if is_tar else _zip_payload()
    path = PACKAGE_PATH if is_tar else _ZIP_PACKAGE_PATH
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path,
        _manifest(tmp_path, payload, {"relative_path": path}),
        LINUX_PLATFORM,
    ).packages[0]
    _inject_short_write(monkeypatch, invalid_count)
    destination = tmp_path / "toolkit"
    with pytest.raises(cuda_validation.CudaProvisionError, match="write count"):
        cuda_validation.extract_cuda_package(
            payload, package, destination, staging=tmp_path / "staging"
        )
    assert not destination.exists()


@pytest.mark.parametrize("invalid_count", list(_BAD_WRITE_RESULTS))
def test_provision_rejects_incomplete_toolkit_marker_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_count: str,
) -> None:
    """A toolkit must not publish when its marker write is incomplete."""
    payload = _payload()
    manifest_path = _manifest(tmp_path, payload)
    native_write = os.write

    def invalid_marker_write(descriptor: int, content: bytes) -> int:
        _ = native_write(descriptor, content[:-1])
        return _bad_write_count(invalid_count, len(content))

    monkeypatch.setattr(os, "write", invalid_marker_write)
    with pytest.raises(cuda_validation.CudaProvisionError, match="write count"):
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path,
            manifest_path,
            LINUX_PLATFORM,
            downloader=_download_fixture(payload),
        )
    assert not (tmp_path / TOOLKIT_ROOT).exists()
    assert not (tmp_path / ".temp/cuda-provision-linux-x86_64").exists()


@pytest.mark.parametrize("link_kind", ["symlink", "hardlink"])
@pytest.mark.parametrize("archive_format", [_TAR_FORMAT, _ZIP_FORMAT])
def test_cuda_archive_member_race_does_not_overwrite_external_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    link_kind: str,
    archive_format: str,
) -> None:
    """A package member inserted as a link cannot redirect staged writes."""
    is_zip = archive_format == _ZIP_FORMAT
    payload = _zip_payload() if is_zip else _payload()
    manifest = _manifest(
        tmp_path, payload,
        {"relative_path": _ZIP_PACKAGE_PATH if is_zip else PACKAGE_PATH},
    )
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, manifest, LINUX_PLATFORM
    ).packages[0]
    outside = tmp_path / "external-binary"
    sentinel = b"external file must stay intact"
    _ = outside.write_bytes(sentinel)
    native_write = cuda_validation._write_verified_bytes
    inserted = False

    def link_before_write(path: Path, content: bytes) -> None:
        nonlocal inserted
        if path.name == "libnvrtc.so.13":
            try:
                if link_kind == "symlink":
                    path.symlink_to(outside)
                else:
                    _ = os.link(outside, path)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"{link_kind} unavailable: {error}")
            inserted = True
        native_write(path, content)

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation, "_write_verified_bytes", link_before_write)
        with pytest.raises(cuda_validation.CudaProvisionError):
            cuda_validation.extract_cuda_package(
                payload, package, tmp_path / "toolkit", staging=tmp_path / "stage"
            )
    assert inserted
    assert outside.read_bytes() == sentinel
    assert not (tmp_path / "toolkit").exists()


@pytest.mark.parametrize("link_kind", ["symlink", "hardlink"])
def test_cuda_marker_race_never_overwrites_external_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    link_kind: str,
) -> None:
    """Marker creation must not follow a link inserted after absence check."""
    payload = _payload()
    manifest = _manifest(tmp_path, payload)
    outside = tmp_path / "external-marker.json"
    sentinel = b"outside data must remain intact"
    _ = outside.write_bytes(sentinel)
    original_check = cuda_validation._require_new_completion_marker
    inserted = False

    def insert_link(path: Path) -> None:
        nonlocal inserted
        original_check(path)
        try:
            if link_kind == "symlink":
                path.symlink_to(outside)
            else:
                _ = os.link(outside, path)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"{link_kind} unavailable: {error}")
        inserted = True

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation, "_require_new_completion_marker", insert_link)
        with pytest.raises(cuda_validation.CudaProvisionError):
            _ = cuda_validation.provision_cuda_manifest(
                tmp_path,
                manifest,
                LINUX_PLATFORM,
                downloader=_download_fixture(payload),
            )
    assert inserted
    assert outside.read_bytes() == sentinel
    assert not (tmp_path / TOOLKIT_ROOT).exists()


@pytest.mark.parametrize("target", ["tar-library", "zip-library", "marker"])
def test_cuda_publication_rejects_false_full_write_with_corrupt_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    """An alleged full write cannot publish bytes differing from the archive."""
    is_zip = target == "zip-library"
    payload = _zip_payload() if is_zip else _payload()
    manifest = _manifest(
        tmp_path,
        payload,
        {"relative_path": _ZIP_PACKAGE_PATH if is_zip else PACKAGE_PATH},
    )
    native_write = os.write
    altered = False

    def corrupt_write(descriptor: int, content: bytes) -> int:
        nonlocal altered
        is_marker = content.startswith(b'{"manifest_sha256"')
        is_library = content == NVRTC_BYTES
        if (target == "marker" and is_marker) or (
            target != "marker" and is_library
        ):
            altered = True
            return native_write(descriptor, b"!" + content[1:])
        return native_write(descriptor, content)

    monkeypatch.setattr(os, "write", corrupt_write)
    with pytest.raises(cuda_validation.CudaProvisionError, match="content mismatch"):
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path,
            manifest,
            LINUX_PLATFORM,
            downloader=lambda _url: payload,
        )
    assert altered
    assert not (tmp_path / TOOLKIT_ROOT).exists()
    assert not (tmp_path / f".temp/cuda-provision-{LINUX_PLATFORM}").exists()


def _tar_symlink_payload() -> bytes:
    """Build a synthetic archive with a contained library symlink."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:xz") as archive:
        member = tarfile.TarInfo(f"{ARCHIVE_ROOT}/lib64/libnvrtc.so.13")
        member.type = tarfile.SYMTYPE
        member.linkname = "libnvrtc.so.13.3"
        archive.addfile(member)
        real = tarfile.TarInfo(f"{ARCHIVE_ROOT}/lib64/libnvrtc.so.13.3")
        real.size = len(NVRTC_BYTES)
        archive.addfile(real, io.BytesIO(NVRTC_BYTES))
    return output.getvalue()


def test_cuda_tar_preserves_contained_symlink(tmp_path: Path) -> None:
    """A legitimate archive symlink stays relative and resolves within the kit."""
    payload = _tar_symlink_payload()
    manifest = _manifest(tmp_path, payload)
    toolkit = cuda_validation.provision_cuda_manifest(
        tmp_path, manifest, LINUX_PLATFORM, downloader=_download_fixture(payload)
    )
    library = toolkit / "lib64/libnvrtc.so.13"
    assert library.is_symlink()
    assert os.readlink(library) == "libnvrtc.so.13.3"
    assert library.read_bytes() == NVRTC_BYTES


@pytest.mark.parametrize("substitution", ["external-link", "regular-file"])
def test_cuda_tar_rejects_substituted_symlink_after_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    substitution: str,
) -> None:
    """A staged archive link must retain its exact admitted physical target."""
    payload = _tar_symlink_payload()
    manifest_path = _manifest(tmp_path, payload)
    outside = tmp_path / "external-binary"
    _ = outside.write_bytes(b"do not import this external library")
    native_symlink = os.symlink
    injected = False

    def substitute_link(
        src: str | bytes | os.PathLike[str],
        dst: str | bytes | os.PathLike[str],
        target_is_directory: bool = False,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal injected
        if Path(dst).name == "libnvrtc.so.13":
            injected = True
            if substitution == "external-link":
                native_symlink(outside, dst, dir_fd=dir_fd)
            else:
                descriptor = os.open(
                    dst, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600,
                    dir_fd=dir_fd,
                )
                try:
                    _ = os.write(descriptor, b"not a symlink")
                finally:
                    os.close(descriptor)
            return
        native_symlink(
            src, dst, target_is_directory=target_is_directory, dir_fd=dir_fd
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "symlink", substitute_link)
        with pytest.raises(cuda_validation.CudaProvisionError, match="symlink"):
            _ = cuda_validation.provision_cuda_manifest(
                tmp_path,
                manifest_path,
                LINUX_PLATFORM,
                downloader=_download_fixture(payload),
            )
    assert injected
    assert not (tmp_path / TOOLKIT_ROOT).exists()
    assert outside.read_bytes() == b"do not import this external library"


@pytest.mark.parametrize("marker_kind", ["regular", "symlink", "dangling-symlink"])
def test_provision_rejects_package_owned_completion_marker(
    tmp_path: Path,
    marker_kind: str,
) -> None:
    """Archive-supplied marker leaves must not authorize or redirect publication."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:xz") as archive:
        for name, content in (
            (NVRTC_MEMBER, NVRTC_BYTES),
            (BUILTINS_MEMBER, BUILTINS_BYTES),
        ):
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        marker = tarfile.TarInfo(
            f"{ARCHIVE_ROOT}/{cuda_validation.CUDA_PROVISION_MARKER}"
        )
        if marker_kind == "regular":
            content = b"package-supplied marker"
            marker.size = len(content)
            archive.addfile(marker, io.BytesIO(content))
        else:
            marker.type = tarfile.SYMTYPE
            marker.linkname = (
                "lib64/libnvrtc.so.13"
                if marker_kind == "symlink"
                else "lib64/missing.so"
            )
            archive.addfile(marker)
    payload = output.getvalue()
    manifest = _manifest(tmp_path, payload)

    with pytest.raises(cuda_validation.CudaProvisionError, match="marker"):
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path,
            manifest,
            LINUX_PLATFORM,
            downloader=_download_fixture(payload),
        )
    assert not (tmp_path / TOOLKIT_ROOT).exists()
    assert not (tmp_path / ".temp/cuda-provision-linux-x86_64").exists()


def test_provision_rejects_zip_package_owned_completion_marker(
    tmp_path: Path,
) -> None:
    """ZIP payloads cannot prepopulate the bootstrap-owned marker either."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w") as archive:
        archive.writestr(NVRTC_MEMBER, NVRTC_BYTES)
        archive.writestr(BUILTINS_MEMBER, BUILTINS_BYTES)
        archive.writestr(
            f"{ARCHIVE_ROOT}/{cuda_validation.CUDA_PROVISION_MARKER}",
            b"package-supplied marker",
        )
    payload = output.getvalue()
    manifest = _manifest(
        tmp_path, payload, {"relative_path": _ZIP_PACKAGE_PATH}
    )

    def download(url: str) -> bytes:
        assert url == cuda_validation.NVIDIA_CUDA_REDIST_BASE + _ZIP_PACKAGE_PATH
        return payload

    with pytest.raises(cuda_validation.CudaProvisionError, match="marker"):
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path,
            manifest,
            LINUX_PLATFORM,
            downloader=download,
        )
    assert not (tmp_path / TOOLKIT_ROOT).exists()


def test_provision_types_marker_status_host_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Marker leaf inspection faults fail closed before toolkit publication."""
    payload = _payload()
    manifest = _manifest(tmp_path, payload)
    marker = (
        tmp_path
        / f".temp/cuda-provision-{LINUX_PLATFORM}/toolkit"
        / cuda_validation.CUDA_PROVISION_MARKER
    )
    native = Path.lstat

    def inspect(path: Path) -> os.stat_result:
        if path == marker:
            raise PermissionError("marker status denied")
        return native(path)

    monkeypatch.setattr(Path, "lstat", inspect)
    with pytest.raises(
        cuda_validation.CudaProvisionError,
        match="cannot inspect CUDA completion marker",
    ):
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path,
            manifest,
            LINUX_PLATFORM,
            downloader=_download_fixture(payload),
        )
    assert not (tmp_path / TOOLKIT_ROOT).exists()


@pytest.mark.parametrize("operation", ["is_symlink", "is_junction"])
def test_cuda_directory_status_cannot_mask_physical_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    """Redirected directories need physical metadata despite host predicates."""
    external = tmp_path / "outside"
    external.mkdir()
    link = tmp_path / "linked"
    try:
        _ = link.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory symlinks unavailable: {error}")
    native = getattr(Path, operation)

    def forged(path: Path) -> bool:
        return False if path == link else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, operation, forged)
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="redirect"
        ):
            cuda_validation._require_physical_directories(link, "staging")
    assert link.is_symlink()


@pytest.mark.parametrize("foreign", [None, 0, "", 0.0])
def test_cuda_directory_rejects_foreign_junction_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    foreign: object,
) -> None:
    """Nonbool junction status cannot certify an existing staging directory."""
    root = tmp_path / "root"
    root.mkdir()
    native = Path.is_junction

    def status(path: Path) -> object:
        return foreign if path == root else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "is_junction", status)
        with pytest.raises(cuda_validation.CudaProvisionError, match="native"):
            cuda_validation._require_physical_directories(root, "staging")


@pytest.mark.parametrize("foreign", [None, 0, object()])
def test_cuda_directory_rejects_foreign_stat_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    foreign: object,
) -> None:
    """Foreign lstat status is not proof of a physical staging directory."""
    root = tmp_path / "root"
    root.mkdir()
    native = Path.lstat

    def forged(path: Path) -> os.stat_result:
        if path == root:
            return cast("os.stat_result", foreign)
        return native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", forged)
        with pytest.raises(cuda_validation.CudaProvisionError, match="native"):
            cuda_validation._require_physical_directories(root, "staging")


def test_cuda_directory_types_host_stat_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected file-status faults retain a typed staging failure."""
    root = tmp_path / "root"
    root.mkdir()
    native = Path.lstat
    failure = PermissionError("denied physical status")

    def status(path: Path) -> os.stat_result:
        if path == root:
            raise failure
        return native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", status)
        with pytest.raises(cuda_validation.CudaProvisionError, match="status") as caught:
            cuda_validation._require_physical_directories(root, "staging")
    assert caught.value.__cause__ is failure


def test_cuda_manifest_rejects_masked_linked_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source ancestry must rely on physical metadata, not Path predicates."""
    real = tmp_path / "real"
    real.mkdir()
    source = _manifest(real, _payload())
    alias = tmp_path / "alias"
    try:
        _ = alias.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory links unavailable: {error}")
    native = Path.is_symlink

    def hidden(path: Path) -> bool:
        return False if path == alias else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "is_symlink", hidden)
        with pytest.raises(cuda_validation.CudaProvisionError, match="redirect"):
            _ = cuda_validation.load_cuda_provision_manifest(
                tmp_path, alias / source.name, LINUX_PLATFORM
            )
    assert alias.is_symlink()


def test_cuda_marker_cannot_certify_masked_linked_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A matching marker reached through an alias cannot assert readiness."""
    payload = _payload()
    source = _manifest(tmp_path, payload)
    real = tmp_path / "real"
    _ = cuda_validation.provision_cuda_manifest(
        real, source, LINUX_PLATFORM, downloader=_download_fixture(payload)
    )
    alias = tmp_path / "alias"
    try:
        _ = alias.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory links unavailable: {error}")
    manifest = cuda_validation.load_cuda_provision_manifest(
        alias, source, LINUX_PLATFORM
    )
    native = Path.is_symlink

    def hidden(path: Path) -> bool:
        return False if path == alias else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "is_symlink", hidden)
        assert not cuda_validation._completed_toolkit_matches(manifest)
    assert alias.is_symlink()


def test_cuda_manifest_rejects_foreign_stat_proxy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A duck-typed stat proxy cannot testify to a named authority inode."""
    source = _manifest(tmp_path, _payload())
    native = Path.lstat
    observed = source.lstat()

    class _StatProxy:
        def __getattr__(self, name: str) -> object:
            return getattr(observed, name)

    def fake(path: Path) -> os.stat_result:
        return (
            cast("os.stat_result", cast("object", _StatProxy()))
            if path == source
            else native(path)
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", fake)
        with pytest.raises(cuda_validation.CudaProvisionError, match="native"):
            _ = cuda_validation.load_cuda_provision_manifest(
                tmp_path, source, LINUX_PLATFORM
            )


@pytest.mark.parametrize("source_kind", ["manifest", "marker"])
def test_cuda_authority_rejects_forged_native_stream_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
) -> None:
    """A foreign stream cannot forge trusted bytes over a corrupted file."""
    payload = _payload()
    source = _manifest(tmp_path, payload)
    manifest = cuda_validation.load_cuda_provision_manifest(
        tmp_path, source, LINUX_PLATFORM
    )
    if source_kind == "marker":
        root = cuda_validation.provision_cuda_manifest(
            tmp_path, source, LINUX_PLATFORM, downloader=_download_fixture(payload)
        )
        authority = root / cuda_validation.CUDA_PROVISION_MARKER
    else:
        authority = source
    genuine = authority.read_bytes()
    _ = authority.write_bytes(b"!" + genuine[1:])
    native_fdopen = os.fdopen
    opened: list[io.BufferedReader] = []

    class _ForgedStream:
        def __init__(self, native: io.BufferedReader) -> None:
            self.native: io.BufferedReader = native

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            self.native.close()

        def fileno(self) -> int:
            return self.native.fileno()

        def read(self, _limit: int) -> bytes:
            return genuine

    def forgery(descriptor: int, mode: str) -> io.BufferedReader:
        stream = cast("io.BufferedReader", native_fdopen(descriptor, mode))
        opened.append(stream)
        return cast("io.BufferedReader", cast("object", _ForgedStream(stream)))

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "fdopen", forgery)
        if source_kind == "manifest":
            with pytest.raises(
                cuda_validation.CudaProvisionError, match="native.*stream"
            ):
                _ = cuda_validation.load_cuda_provision_manifest(
                    tmp_path, source, LINUX_PLATFORM
                )
        else:
            assert not cuda_validation._completed_toolkit_matches(manifest)
    assert len(opened) == 1
    assert opened[0].closed
    assert authority.read_bytes() != genuine


@pytest.mark.parametrize("source_kind", ["manifest", "marker"])
def test_cuda_authority_rejects_native_stream_on_different_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
) -> None:
    """Even a native reader cannot replace the originally opened descriptor."""
    payload = _payload()
    source = _manifest(tmp_path, payload)
    manifest = cuda_validation.load_cuda_provision_manifest(
        tmp_path, source, LINUX_PLATFORM
    )
    if source_kind == "marker":
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path, source, LINUX_PLATFORM, downloader=_download_fixture(payload)
        )
    native_fdopen = os.fdopen
    opened_descriptors: list[int] = []
    redirected: list[io.BufferedReader] = []

    def wrap_duplicate(descriptor: int, mode: str) -> io.BufferedReader:
        opened_descriptors.append(descriptor)
        stream = cast("io.BufferedReader", native_fdopen(os.dup(descriptor), mode))
        redirected.append(stream)
        return stream

    try:
        with monkeypatch.context() as isolated:
            isolated.setattr(os, "fdopen", wrap_duplicate)
            if source_kind == "manifest":
                with pytest.raises(
                    cuda_validation.CudaProvisionError, match="native.*descriptor"
                ):
                    _ = cuda_validation.load_cuda_provision_manifest(
                        tmp_path, source, LINUX_PLATFORM
                    )
            else:
                assert not cuda_validation._completed_toolkit_matches(manifest)
        assert len(opened_descriptors) == 1
        with pytest.raises(OSError, match=r"Bad file descriptor|Invalid handle"):
            _ = os.fstat(opened_descriptors[0])
        assert all(stream.closed for stream in redirected)
    finally:
        for descriptor in opened_descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass
        for stream in redirected:
            stream.close()


@pytest.mark.parametrize("kind", ["unmanaged", "native-memory"])
def test_cuda_authority_rejects_non_file_stream_without_descriptor_leak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Invalid stream wrappers cannot orphan the manifest's opened descriptor."""
    source = _manifest(tmp_path, _payload())
    native_open = os.open
    opened_descriptors: list[int] = []
    extra_streams: list[io.IOBase] = []

    def capture_open(path: Path, flags: int) -> int:
        descriptor = native_open(path, flags)
        if path == source:
            opened_descriptors.append(descriptor)
        return descriptor

    def fake_fdopen(_descriptor: int, _mode: str) -> object:
        if kind == "unmanaged":
            return object()
        stream = io.BufferedReader(io.BytesIO(source.read_bytes()))
        extra_streams.append(stream)
        return stream

    try:
        with monkeypatch.context() as isolated:
            isolated.setattr(os, "open", capture_open)
            isolated.setattr(os, "fdopen", fake_fdopen)
            with pytest.raises(
                cuda_validation.CudaProvisionError, match="native.*stream"
            ):
                _ = cuda_validation.load_cuda_provision_manifest(
                    tmp_path, source, LINUX_PLATFORM
                )
        assert len(opened_descriptors) == 1
        with pytest.raises(OSError, match=r"Bad file descriptor|Invalid handle"):
            _ = os.fstat(opened_descriptors[0])
        assert all(stream.closed for stream in extra_streams)
    finally:
        for descriptor in opened_descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass
        for stream in extra_streams:
            stream.close()


@pytest.mark.parametrize("source_kind", ["manifest", "marker"])
@pytest.mark.parametrize("value_kind", ["mutable", "subclass", "string", "missing"])
def test_cuda_source_rejects_foreign_stream_read_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
    value_kind: str,
) -> None:
    """Named marker and manifest authority require exact immutable read bytes."""
    payload = _payload()
    source = _manifest(tmp_path, payload)
    manifest = cuda_validation.load_cuda_provision_manifest(
        tmp_path, source, LINUX_PLATFORM
    )
    if source_kind == "marker":
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path, source, LINUX_PLATFORM, downloader=_download_fixture(payload)
        )
        raw = (manifest.toolkit_root / cuda_validation.CUDA_PROVISION_MARKER).read_bytes()
    else:
        raw = source.read_bytes()
    foreign: dict[str, object] = {
        "mutable": bytearray(raw),
        "subclass": _BytesSubclass(raw),
        "string": "x" * len(raw),
        "missing": None,
    }
    native_fdopen = os.fdopen
    opened: list[io.BufferedReader] = []

    def capture_fdopen(descriptor: int, mode: str) -> io.BufferedReader:
        stream = cast("io.BufferedReader", native_fdopen(descriptor, mode))
        opened.append(stream)
        return stream

    def return_foreign(_stream: object, _limit: int) -> bytes:
        return cast("bytes", foreign[value_kind])

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "fdopen", capture_fdopen)
        isolated.setattr(cuda_validation, "_read_source_bytes", return_foreign)
        if source_kind == "manifest":
            with pytest.raises(cuda_validation.CudaProvisionError, match="native bytes"):
                _ = cuda_validation.load_cuda_provision_manifest(
                    tmp_path, source, LINUX_PLATFORM
                )
        else:
            assert not cuda_validation._completed_toolkit_matches(manifest)
    assert len(opened) == 1
    assert opened[0].closed


@pytest.mark.parametrize("source_kind", ["manifest", "marker"])
@pytest.mark.parametrize(
    "fault_type", [OSError, TypeError, ValueError, UnprintableHostRuntimeError]
)
def test_cuda_source_read_types_host_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
    fault_type: type[Exception],
) -> None:
    """A host read exception preserves its cause and closes the source handle."""
    payload = _payload()
    source = _manifest(tmp_path, payload)
    if source_kind == "marker":
        installed = cuda_validation.provision_cuda_manifest(
            tmp_path, source, LINUX_PLATFORM, downloader=_download_fixture(payload)
        )
        subject = installed / cuda_validation.CUDA_PROVISION_MARKER
    else:
        subject = source
    failure = fault_type("host stream read failure")
    native_fdopen = os.fdopen
    opened: list[io.BufferedReader] = []

    def capture_fdopen(descriptor: int, mode: str) -> io.BufferedReader:
        stream = cast("io.BufferedReader", native_fdopen(descriptor, mode))
        opened.append(stream)
        return stream

    def fail_read(_stream: object, _limit: int) -> bytes:
        raise failure

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "fdopen", capture_fdopen)
        isolated.setattr(cuda_validation, "_read_source_bytes", fail_read)
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="host read failed"
        ) as caught:
            _ = cuda_validation._read_manifest_source(subject, "CUDA authority")
    assert caught.value.__cause__ is failure
    assert len(opened) == 1
    assert opened[0].closed


class _ForeignDescriptor(int):
    """An integer-looking handle that is not a native file descriptor."""


@pytest.mark.parametrize("receipt", [True, _ForeignDescriptor(1), None, -1])
def test_cuda_source_rejects_foreign_open_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """A forged file descriptor cannot authorize or close an unrelated fd."""
    source = _manifest(tmp_path, _payload())
    wrapped: list[object] = []
    closed: list[object] = []

    def fake_open(path: Path, flags: int) -> int:
        assert path == source
        assert flags & os.O_RDONLY == os.O_RDONLY
        return cast("int", receipt)

    def fake_fdopen(descriptor: object, mode: str) -> io.BufferedReader:
        wrapped.append(descriptor)
        raise ValueError("unsafe handle")

    def fake_close(descriptor: object) -> None:
        closed.append(descriptor)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", fake_open)
        isolated.setattr(os, "fdopen", fake_fdopen)
        isolated.setattr(os, "close", fake_close)
        with pytest.raises(cuda_validation.CudaProvisionError, match="native descriptor"):
            _ = cuda_validation._read_manifest_source(source, "CUDA provision manifest")
    assert not wrapped
    assert not closed


@pytest.mark.parametrize(
    "fault_type", [OSError, TypeError, ValueError, UnprintableHostRuntimeError]
)
def test_cuda_source_open_types_host_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """File-open failures retain their cause and avoid foreign diagnostics."""
    source = _manifest(tmp_path, _payload())
    failure = fault_type("host open failure")

    def fake_open(path: Path, flags: int) -> int:
        assert path == source
        assert isinstance(flags, int)
        raise failure

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", fake_open)
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="host open failed"
        ) as caught:
            _ = cuda_validation._read_manifest_source(source, "CUDA provision manifest")
    assert caught.value.__cause__ is failure


@pytest.mark.parametrize("overflow", [False, True])
def test_cuda_network_download_bounded_to_pinned_package_size(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    overflow: bool,
) -> None:
    """HTTPS streaming reads at most pinned size+1 before any extraction."""
    payload = _payload()
    manifest = _manifest(tmp_path, payload)
    observed_limits: list[int] = []
    response_closed = False

    class _BoundedResponse:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            nonlocal response_closed
            response_closed = True

        def read(self, limit: int) -> bytes:
            observed_limits.append(limit)
            assert type(limit) is int
            assert limit == len(payload) + 1
            return payload + b"x" if overflow else payload

    def open_url(request: object, *, timeout: int) -> _BoundedResponse:
        assert isinstance(request, cuda_validation.urllib.request.Request)
        assert request.full_url == cuda_validation.NVIDIA_CUDA_REDIST_BASE + PACKAGE_PATH
        assert timeout == 120
        return _BoundedResponse()

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation.urllib.request, "urlopen", open_url)
        if overflow:
            with pytest.raises(cuda_validation.CudaProvisionError, match="byte limit"):
                _ = cuda_validation.provision_cuda_manifest(
                    tmp_path, manifest, LINUX_PLATFORM
                )
            assert not (tmp_path / TOOLKIT_ROOT).exists()
        else:
            result = cuda_validation.provision_cuda_manifest(
                tmp_path, manifest, LINUX_PLATFORM
            )
            assert (result / "lib64/libnvrtc.so.13").read_bytes() == NVRTC_BYTES
    assert observed_limits == [len(payload) + 1]
    assert response_closed


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_cuda_staged_file_does_not_follow_late_parent_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Late parent redirection must never create a foreign staged file."""
    parent = tmp_path / "owned-stage"
    parent.mkdir()
    target = parent / "payload.bin"
    parked = tmp_path / "parked-stage"
    outside = tmp_path / "foreign-stage"
    outside.mkdir()
    sentinel = outside / "sentinel"
    _ = sentinel.write_bytes(b"preserve foreign contents")
    native_open = os.open
    swapped = False
    foreign_created = False

    def swap_parent_at_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped, foreign_created
        if not swapped and (
            Path(path) == target or (path == target.name and dir_fd is not None)
        ):
            _ = parent.rename(parked)
            _ = parent.symlink_to(outside, target_is_directory=True)
            swapped = True
        result = native_open(path, flags, mode, dir_fd=dir_fd)
        foreign_created |= (outside / target.name).exists()
        return result

    monkeypatch.setattr(os, "open", swap_parent_at_open)
    with pytest.raises(cuda_validation.CudaProvisionError, match="staging"):
        _ = cuda_validation._write_staged_file_exclusively(  # pyright: ignore[reportPrivateUsage]
            target, b"trusted-payload", "CUDA staging payload"
        )
    assert swapped
    assert not foreign_created
    assert sentinel.read_bytes() == b"preserve foreign contents"
    assert not (outside / target.name).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_cuda_staged_file_rejects_replaced_physical_parent_at_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replaced physical parent cannot impersonate the checked stage."""
    parent = tmp_path / "owned-stage"
    parent.mkdir()
    target = parent / "payload.bin"
    parked = tmp_path / "parked-stage"
    outside = tmp_path / "foreign-stage"
    outside.mkdir()
    sentinel = outside / "sentinel"
    _ = sentinel.write_bytes(b"preserve foreign contents")
    native_open = os.open
    swapped = False

    def replace_parent_at_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if not swapped and Path(path) == parent:
            _ = parent.rename(parked)
            _ = outside.rename(parent)
            swapped = True
        return native_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", replace_parent_at_open)
    with pytest.raises(cuda_validation.CudaProvisionError, match="staging"):
        _ = cuda_validation._write_staged_file_exclusively(  # pyright: ignore[reportPrivateUsage]
            target, b"trusted-payload", "CUDA staging payload"
        )
    assert swapped
    assert (parent / "sentinel").read_bytes() == b"preserve foreign contents"
    assert not target.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_cuda_staged_file_rejects_foreign_parent_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An open receipt from another directory must not authorize any write."""
    parent = tmp_path / "owned-stage"
    parent.mkdir()
    target = parent / "payload.bin"
    outside = tmp_path / "foreign-stage"
    outside.mkdir()
    sentinel = outside / "sentinel"
    _ = sentinel.write_bytes(b"preserve foreign contents")
    native_open = os.open
    forged = False

    def open_foreign_parent(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal forged
        if Path(path) == parent:
            forged = True
            return native_open(outside, flags, mode)
        return native_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", open_foreign_parent)
    with pytest.raises(cuda_validation.CudaProvisionError, match="descriptor"):
        _ = cuda_validation._write_staged_file_exclusively(  # pyright: ignore[reportPrivateUsage]
            target, b"trusted-payload", "CUDA staging payload"
        )
    assert forged
    assert sentinel.read_bytes() == b"preserve foreign contents"
    assert not (outside / target.name).exists()
    assert not target.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_cuda_staged_file_types_parent_close_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A host close exception cannot escape the staging error contract."""
    parent = tmp_path / "owned-stage"
    parent.mkdir()
    target = parent / "payload.bin"
    native_open = os.open
    native_close = os.close
    parent_descriptor: int | None = None
    failure = UnprintableHostOSError("denied close")
    closed = False

    def capture_parent(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal parent_descriptor
        descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path) == parent:
            parent_descriptor = descriptor
        return descriptor

    def fail_parent_close(descriptor: int) -> None:
        nonlocal closed
        native_close(descriptor)
        if descriptor == parent_descriptor:
            closed = True
            raise failure

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", capture_parent)
        isolated.setattr(os, "close", fail_parent_close)
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="staging parent close"
        ) as caught:
            _ = cuda_validation._write_staged_file_exclusively(  # pyright: ignore[reportPrivateUsage]
                target, b"trusted-payload", "CUDA staging payload"
            )
    assert closed
    assert caught.value.__cause__ is failure
    assert target.read_bytes() == b"trusted-payload"


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_cuda_staging_mkdir_does_not_follow_late_parent_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A staging-directory race must not create a foreign directory."""
    parent = tmp_path / "owned-parent"
    parent.mkdir()
    stage = parent / "stage-root"
    parked = tmp_path / "parked-parent"
    outside = tmp_path / "foreign-parent"
    outside.mkdir()
    sentinel = outside / "sentinel"
    _ = sentinel.write_bytes(b"preserve foreign contents")
    native_path_mkdir = Path.mkdir
    native_os_mkdir = os.mkdir
    swapped = False
    foreign_created = False

    def race() -> None:
        nonlocal swapped
        if not swapped:
            _ = parent.rename(parked)
            _ = parent.symlink_to(outside, target_is_directory=True)
            swapped = True

    def path_mkdir(
        path: Path, mode: int = 0o777, parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        nonlocal foreign_created
        if path == stage:
            race()
        native_path_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)
        foreign_created |= (outside / stage.name).exists()

    def os_mkdir(
        path: str | os.PathLike[str], mode: int = 0o777, *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal foreign_created
        if path == stage.name and dir_fd is not None:
            race()
        native_os_mkdir(path, mode, dir_fd=dir_fd)
        foreign_created |= (outside / stage.name).exists()

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "mkdir", path_mkdir)
        isolated.setattr(os, "mkdir", os_mkdir)
        with pytest.raises(cuda_validation.CudaProvisionError, match="staging"):
            cuda_validation._prepare_staging(stage)  # pyright: ignore[reportPrivateUsage]
    assert swapped
    assert not foreign_created
    assert sentinel.read_bytes() == b"preserve foreign contents"
    assert not (outside / stage.name).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_cuda_staging_mkdir_rejects_replaced_parent_at_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Creating a stage must verify the original physical parent identity."""
    parent = tmp_path / "owned-parent"
    parent.mkdir()
    stage = parent / "stage-root"
    parked = tmp_path / "parked-parent"
    outside = tmp_path / "foreign-parent"
    outside.mkdir()
    sentinel = outside / "sentinel"
    _ = sentinel.write_bytes(b"preserve foreign contents")
    native_open = os.open
    swapped = False

    def race_parent_open(
        path: str | os.PathLike[str], flags: int,
        mode: int = 0o777, *, dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if Path(path) == parent and not swapped:
            _ = parent.rename(parked)
            _ = outside.rename(parent)
            swapped = True
        return native_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", race_parent_open)
    with pytest.raises(cuda_validation.CudaProvisionError, match="staging"):
        cuda_validation._prepare_staging(stage)  # pyright: ignore[reportPrivateUsage]
    assert swapped
    assert (parent / "sentinel").read_bytes() == b"preserve foreign contents"
    assert not stage.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_cuda_staging_mkdir_rejects_late_physical_parent_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A renamed physical parent must not adopt a different staged directory."""
    parent = tmp_path / "owned-parent"
    parent.mkdir()
    stage = parent / "stage-root"
    parked = tmp_path / "parked-parent"
    outside = tmp_path / "foreign-parent"
    outside.mkdir()
    sentinel = outside / "sentinel"
    _ = sentinel.write_bytes(b"preserve foreign contents")
    native_mkdir = os.mkdir
    swapped = False

    def replace_at_mkdir(
        path: str | os.PathLike[str], mode: int = 0o777, *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if path == stage.name and dir_fd is not None and not swapped:
            _ = parent.rename(parked)
            _ = outside.rename(parent)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "mkdir", replace_at_mkdir)
    with pytest.raises(cuda_validation.CudaProvisionError, match="staging"):
        cuda_validation._prepare_staging(stage)  # pyright: ignore[reportPrivateUsage]
    assert swapped
    assert (parent / "sentinel").read_bytes() == b"preserve foreign contents"
    assert not stage.exists()
    assert (parked / stage.name).is_dir()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_cuda_staging_mkdir_rejects_forged_success_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A false successful mkdir receipt cannot certify missing staging state."""
    parent = tmp_path / "owned-parent"
    parent.mkdir()
    stage = parent / "stage-root"
    native_mkdir = os.mkdir
    forged = False

    def false_success(
        path: str | os.PathLike[str], mode: int = 0o777, *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal forged
        if path == stage.name and dir_fd is not None:
            forged = True
            return
        native_mkdir(path, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "mkdir", false_success)
    with pytest.raises(cuda_validation.CudaProvisionError, match="staging"):
        cuda_validation._prepare_staging(stage)  # pyright: ignore[reportPrivateUsage]
    assert forged
    assert not stage.exists()


@pytest.mark.parametrize(
    "fault", [UnprintableHostOSError, UnprintableHostRuntimeError, ValueError, TypeError]
)
def test_cuda_manifest_json_reader_does_not_render_host_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Manifest JSON parser host exceptions must remain typed and unrendered."""
    source = _manifest(tmp_path, _payload())
    failure = fault("foreign JSON reader failure")

    def fail_parse(_body: str, *, object_pairs_hook: object) -> object:
        assert object_pairs_hook is not None
        raise failure

    monkeypatch.setattr(cuda_validation.json, "loads", fail_parse)
    with pytest.raises(cuda_validation.CudaProvisionError, match="cannot read") as caught:
        _ = cuda_validation.load_cuda_provision_manifest(tmp_path, source, LINUX_PLATFORM)
    assert caught.value.__cause__ is failure


def test_cuda_marker_inspection_does_not_render_host_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hostile OSError message cannot escape marker inspection."""
    parent = tmp_path / "owned-stage"
    parent.mkdir()
    marker = parent / cuda_validation.CUDA_PROVISION_MARKER
    failure = UnprintableHostOSError("foreign marker status failure")
    native_lstat = Path.lstat

    def fail_marker(path: Path) -> os.stat_result:
        if path == marker:
            raise failure
        return native_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_marker)
    with pytest.raises(
        cuda_validation.CudaProvisionError, match="cannot inspect CUDA completion marker"
    ) as caught:
        cuda_validation._require_new_completion_marker(marker)  # pyright: ignore[reportPrivateUsage]
    assert caught.value.__cause__ is failure


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("fault", [UnprintableHostOSError, UnprintableHostRuntimeError])
def test_cuda_publication_types_destination_parent_close_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Final publish close errors must not leak untrusted host exceptions."""
    staged = tmp_path / "owned-staging-toolkit"
    staged.mkdir()
    parent = tmp_path / "toolkit-parent"
    parent.mkdir()
    destination = parent / "toolkit"
    native_open = os.open
    native_close = os.close
    opened_parent: int | None = None
    closed = False
    failure = fault("foreign directory close failure")

    def capture_open(
        path: str | os.PathLike[str], flags: int, mode: int = 0o777,
        *, dir_fd: int | None = None,
    ) -> int:
        nonlocal opened_parent
        descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path) == parent:
            opened_parent = descriptor
        return descriptor

    def fail_close(descriptor: int) -> None:
        nonlocal closed
        native_close(descriptor)
        if descriptor == opened_parent:
            closed = True
            raise failure

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", capture_open)
        isolated.setattr(os, "close", fail_close)
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="destination parent close"
        ) as caught:
            cuda_validation._publish_cuda_toolkit(  # pyright: ignore[reportPrivateUsage]
                staged, destination
            )
    assert closed
    assert caught.value.__cause__ is failure
    assert destination.is_dir()
    assert not staged.exists()


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux renameat2")
@pytest.mark.parametrize("substitution", ["no-rename", "foreign-directory"])
def test_cuda_publication_rejects_false_successful_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    substitution: str,
) -> None:
    """The renamed toolkit must retain the original staged directory inode."""
    staged = tmp_path / "owned-staging-toolkit"
    staged.mkdir()
    payload = staged / "payload.bin"
    _ = payload.write_bytes(b"verified contents")
    parent = tmp_path / "toolkit-parent"
    parent.mkdir()
    destination = parent / "toolkit"
    observed = False

    def fake_success(
        source: str,
        target: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
    ) -> None:
        nonlocal observed
        if source == staged.name and target == destination.name:
            observed = True
            if substitution == "foreign-directory":
                destination.mkdir()
                _ = (destination / "foreign.txt").write_text("foreign contents")
            return
        raise AssertionError("unexpected rename target")

    with monkeypatch.context() as isolated:
        isolated.setattr(
            cuda_validation, "_rename_cuda_toolkit_no_replace", fake_success
        )
        with pytest.raises(cuda_validation.CudaProvisionError, match="publication"):
            cuda_validation._publish_cuda_toolkit(  # pyright: ignore[reportPrivateUsage]
                staged, destination
            )
    assert observed
    assert staged.is_dir()
    assert payload.read_bytes() == b"verified contents"
    if substitution == "no-rename":
        assert not destination.exists()
    else:
        assert (destination / "foreign.txt").read_text() == "foreign contents"


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux renameat2")
def test_cuda_publication_does_not_replace_occupant_after_final_absence_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The final rename cannot erase a directory inserted after the last check."""
    staged = tmp_path / "owned-staging-toolkit"
    staged.mkdir()
    _ = (staged / "verified.bin").write_bytes(b"trusted toolkit")
    parent = tmp_path / "toolkit-parent"
    parent.mkdir()
    destination = parent / "toolkit"
    native_stat = os.stat
    occupied = False

    def occupy_after_absence(
        path: str | os.PathLike[str],
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal occupied
        try:
            return native_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        except FileNotFoundError:
            if path == destination.name and dir_fd is not None and not occupied:
                destination.mkdir()
                occupied = True
            raise

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "stat", occupy_after_absence)
        with pytest.raises(cuda_validation.CudaProvisionError, match="occupied"):
            cuda_validation._publish_cuda_toolkit(  # pyright: ignore[reportPrivateUsage]
                staged, destination
            )
    assert occupied
    assert destination.is_dir()
    assert not tuple(destination.iterdir())
    assert (staged / "verified.bin").read_bytes() == b"trusted toolkit"


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux renameat2")
def test_cuda_publication_rejects_staging_parent_swap_during_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Publication cannot attest a stage whose named source parent changes."""
    source_parent = tmp_path / "owned-source"
    source_parent.mkdir()
    staged = source_parent / "toolkit"
    staged.mkdir()
    _ = (staged / "trusted.bin").write_bytes(b"trusted toolkit")
    parked = tmp_path / "parked-source"
    outside = tmp_path / "foreign-source"
    outside.mkdir()
    foreign_stage = outside / "toolkit"
    foreign_stage.mkdir()
    _ = (foreign_stage / "foreign.bin").write_bytes(b"foreign toolkit")
    destination_parent = tmp_path / "toolkit-parent"
    destination_parent.mkdir()
    destination = destination_parent / "toolkit"
    native_rename = cuda_validation._rename_cuda_toolkit_no_replace  # pyright: ignore[reportPrivateUsage]
    swapped = False

    def replace_named_source(
        source: str, target: str, *, src_dir_fd: int, dst_dir_fd: int
    ) -> None:
        nonlocal swapped
        _ = source_parent.rename(parked)
        _ = outside.rename(source_parent)
        swapped = True
        native_rename(source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(
        cuda_validation, "_rename_cuda_toolkit_no_replace", replace_named_source
    )
    with pytest.raises(cuda_validation.CudaProvisionError, match="staging parent"):
        cuda_validation._publish_cuda_toolkit(  # pyright: ignore[reportPrivateUsage]
            staged, destination
        )
    assert swapped
    assert (source_parent / "toolkit/foreign.bin").read_bytes() == b"foreign toolkit"
    assert not (source_parent / "toolkit/trusted.bin").exists()
    assert (destination / "trusted.bin").read_bytes() == b"trusted toolkit"


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux renameat2")
@pytest.mark.parametrize("fault", [UnprintableHostOSError, UnprintableHostRuntimeError])
def test_cuda_publication_types_staging_source_parent_close_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """An owned source descriptor close fault remains typed after publication."""
    parent = tmp_path / "staging-parent"
    parent.mkdir()
    staged = parent / "toolkit"
    staged.mkdir()
    _ = (staged / "trusted.bin").write_bytes(b"trusted toolkit")
    destination = tmp_path / "published-toolkit"
    native_open = os.open
    native_close = os.close
    source_descriptor: int | None = None
    failure = fault("foreign source close failure")
    closed = False

    def capture_source(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal source_descriptor
        descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path) == parent:
            source_descriptor = descriptor
        return descriptor

    def fail_source_close(descriptor: int) -> None:
        nonlocal closed
        native_close(descriptor)
        if descriptor == source_descriptor:
            closed = True
            raise failure

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", capture_source)
        isolated.setattr(os, "close", fail_source_close)
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="staging source parent close"
        ) as caught:
            cuda_validation._publish_cuda_toolkit(  # pyright: ignore[reportPrivateUsage]
                staged, destination
            )
    assert closed
    assert caught.value.__cause__ is failure
    assert (destination / "trusted.bin").read_bytes() == b"trusted toolkit"
    assert not staged.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("swap_kind", ["symlink", "physical"])
def test_cuda_destination_parent_mkdir_does_not_follow_late_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, swap_kind: str
) -> None:
    """Final parent creation cannot make a child in a substituted directory."""
    root = tmp_path / "repository"
    root.mkdir()
    dependencies = root / ".dependencies"
    dependencies.mkdir()
    payload = _payload()
    manifest = _manifest(root, payload)
    parked = root / "parked-dependencies"
    outside = tmp_path / "foreign-directory"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    _ = sentinel.write_bytes(b"foreign contents")
    native_mkdir = os.mkdir
    swapped = False

    def race_parent_creation(
        path: str | os.PathLike[str], mode: int = 0o777,
        *, dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and (
            (Path(path) == dependencies / "cuda" and dir_fd is None)
            or (path == "cuda" and dir_fd is not None)
        ):
            _ = dependencies.rename(parked)
            if swap_kind == "symlink":
                _ = dependencies.symlink_to(outside, target_is_directory=True)
            else:
                _ = outside.rename(dependencies)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", race_parent_creation)
        with pytest.raises(cuda_validation.CudaProvisionError, match="destination"):
            cuda_validation.provision_cuda_manifest(
                root, manifest, LINUX_PLATFORM, downloader=_download_fixture(payload)
            )
    assert swapped
    foreign_parent = outside if swap_kind == "symlink" else dependencies
    assert (foreign_parent / "sentinel.txt").read_bytes() == b"foreign contents"
    assert not (foreign_parent / "cuda").exists()
    assert not (outside / "13.3.1").exists()
    assert not (root / TOOLKIT_ROOT).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_cuda_destination_parent_rejects_replaced_physical_directory_at_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A foreign physical parent cannot replace the admitted checkout parent."""
    root = tmp_path / "repository"
    root.mkdir()
    dependencies = root / ".dependencies"
    dependencies.mkdir()
    payload = _payload()
    manifest = _manifest(root, payload)
    parked = root / "parked-dependencies"
    outside = tmp_path / "foreign-directory"
    outside.mkdir()
    sentinel = outside / "sentinel.txt"
    _ = sentinel.write_bytes(b"foreign contents")
    native_open = os.open
    swapped = False

    def swap_before_parent_open(
        path: str | os.PathLike[str], flags: int, mode: int = 0o777,
        *, dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if not swapped and Path(path) == dependencies:
            _ = dependencies.rename(parked)
            _ = outside.rename(dependencies)
            swapped = True
        return native_open(path, flags, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", swap_before_parent_open)
        with pytest.raises(cuda_validation.CudaProvisionError, match="destination"):
            cuda_validation.provision_cuda_manifest(
                root, manifest, LINUX_PLATFORM, downloader=_download_fixture(payload)
            )
    assert swapped
    assert (dependencies / "sentinel.txt").read_bytes() == b"foreign contents"
    assert not (dependencies / "cuda").exists()
    assert not (root / TOOLKIT_ROOT).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_cuda_destination_parent_rejects_forged_mkdir_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A false successful mkdir cannot supply a toolkit parent receipt."""
    root = tmp_path / "repository"
    root.mkdir()
    payload = _payload()
    manifest = _manifest(root, payload)
    native_mkdir = os.mkdir
    forged = False

    def report_false_success(
        path: str | os.PathLike[str], mode: int = 0o777,
        *, dir_fd: int | None = None,
    ) -> None:
        nonlocal forged
        if path == "cuda" and dir_fd is not None:
            forged = True
            return
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", report_false_success)
        with pytest.raises(cuda_validation.CudaProvisionError, match="destination"):
            cuda_validation.provision_cuda_manifest(
                root, manifest, LINUX_PLATFORM, downloader=_download_fixture(payload)
            )
    assert forged
    assert not (root / TOOLKIT_ROOT).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("swap_kind", ["symlink", "physical"])
def test_cuda_extract_destination_mkdir_rejects_late_parent_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, swap_kind: str
) -> None:
    """Archive overlays must not create toolkit roots in substituted parents."""
    root = tmp_path / "repository"
    root.mkdir()
    parent = root / "owned-overlay-parent"
    parent.mkdir()
    destination = parent / "toolkit"
    package_data = _payload()
    package = cuda_validation.load_cuda_provision_manifest(
        root, _manifest(root, package_data), LINUX_PLATFORM
    ).packages[0]
    outside = tmp_path / "foreign-overlay-parent"
    outside.mkdir()
    sentinel = outside / "sentinel"
    _ = sentinel.write_bytes(b"foreign content")
    parked = root / "parked-overlay-parent"
    native_mkdir = os.mkdir
    swapped = False

    def race_destination_mkdir(
        path: str | os.PathLike[str], mode: int = 0o777,
        *, dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and (
            (Path(path) == destination and dir_fd is None)
            or (path == destination.name and dir_fd is not None)
        ):
            _ = parent.rename(parked)
            if swap_kind == "symlink":
                _ = parent.symlink_to(outside, target_is_directory=True)
            else:
                _ = outside.rename(parent)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", race_destination_mkdir)
        with pytest.raises(cuda_validation.CudaProvisionError, match="destination"):
            cuda_validation.extract_cuda_package(
                package_data, package, destination, staging=root / "package-stage"
            )
    assert swapped
    foreign_parent = outside if swap_kind == "symlink" else parent
    assert (foreign_parent / "sentinel").read_bytes() == b"foreign content"
    assert not (foreign_parent / "toolkit").exists()
    assert not (root / "toolkit").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("archive_format", [_TAR_FORMAT, _ZIP_FORMAT])
@pytest.mark.parametrize("swap_kind", ["symlink", "physical"])
def test_cuda_archive_member_mkdir_does_not_follow_late_parent_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    archive_format: str,
    swap_kind: str,
) -> None:
    """A staged archive member directory cannot escape through parent substitution."""
    root = tmp_path / "repository"
    root.mkdir()
    payload = _payload() if archive_format == _TAR_FORMAT else _zip_payload()
    package = cuda_validation.load_cuda_provision_manifest(
        root,
        _manifest(
            root, payload,
            {"relative_path": PACKAGE_PATH if archive_format == _TAR_FORMAT else _ZIP_PACKAGE_PATH},
        ),
        LINUX_PLATFORM,
    ).packages[0]
    archive_parent = root / "staging" / PACKAGE_NAME / ARCHIVE_ROOT
    target = archive_parent / "lib64"
    parked = root / "parked-archive-root"
    outside = tmp_path / "foreign-archive-root"
    outside.mkdir()
    _ = (outside / "sentinel").write_bytes(b"foreign data")
    native_mkdir = os.mkdir
    swapped = False

    def swap_before_member_mkdir(
        path: str | os.PathLike[str], mode: int = 0o777,
        *, dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and archive_parent.is_dir() and (
            (Path(path) == target and dir_fd is None)
            or (path == target.name and dir_fd is not None)
        ):
            _ = archive_parent.rename(parked)
            if swap_kind == "symlink":
                _ = archive_parent.symlink_to(outside, target_is_directory=True)
            else:
                _ = outside.rename(archive_parent)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", swap_before_member_mkdir)
        with pytest.raises(cuda_validation.CudaProvisionError):
            cuda_validation.extract_cuda_package(
                payload, package, root / "toolkit", staging=root / "staging"
            )
    assert swapped
    foreign_parent = outside if swap_kind == "symlink" else archive_parent
    assert (foreign_parent / "sentinel").read_bytes() == b"foreign data"
    assert not (foreign_parent / "lib64").exists()
    assert not (root / "toolkit").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("swap_kind", ["symlink", "physical"])
def test_cuda_overlay_copy_does_not_write_through_swapped_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, swap_kind: str
) -> None:
    """Archive overlays must not copy verified members into foreign parents."""
    root = tmp_path / "repository"
    root.mkdir()
    parent = root / "owned-overlay-parent"
    parent.mkdir()
    destination = parent / "toolkit"
    payload = _payload()
    package = cuda_validation.load_cuda_provision_manifest(
        root, _manifest(root, payload), LINUX_PLATFORM
    ).packages[0]
    package_staging = root / "package-stage"
    extraction_root = package_staging / PACKAGE_NAME / ARCHIVE_ROOT
    outside = tmp_path / "foreign-overlay-parent"
    outside.mkdir()
    _ = (outside / "sentinel").write_bytes(b"foreign content")
    parked = root / "parked-overlay-parent"
    native_scandir = os.scandir
    swapped = False

    def swap_during_copy_iteration(path: str | os.PathLike[str] | int) -> object:
        nonlocal swapped
        if not swapped and isinstance(path, (str, os.PathLike)) and Path(path) == extraction_root:
            _ = parent.rename(parked)
            if swap_kind == "symlink":
                _ = parent.symlink_to(outside, target_is_directory=True)
            else:
                _ = outside.rename(parent)
            swapped = True
        return native_scandir(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "scandir", swap_during_copy_iteration)
        with pytest.raises(cuda_validation.CudaProvisionError):
            cuda_validation.extract_cuda_package(
                payload, package, destination, staging=package_staging
            )
    assert swapped
    foreign_parent = outside if swap_kind == "symlink" else parent
    assert (foreign_parent / "sentinel").read_bytes() == b"foreign content"
    assert not (foreign_parent / "toolkit").exists()
    assert not (root / "toolkit").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("swap_kind", ["symlink", "physical"])
def test_cuda_overlay_copy_does_not_write_into_swapped_nested_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, swap_kind: str
) -> None:
    """Nested copy writes remain pinned even when the toolkit root is replaced."""
    root = tmp_path / "repository"
    root.mkdir()
    destination = root / "toolkit"
    payload = _payload()
    package = cuda_validation.load_cuda_provision_manifest(
        root, _manifest(root, payload), LINUX_PLATFORM
    ).packages[0]
    foreign = tmp_path / "foreign-toolkit"
    foreign.mkdir()
    _ = (foreign / "sentinel").write_bytes(b"external data")
    parked = root / "parked-toolkit"
    native_mkdir = os.mkdir
    swapped = False

    def swap_before_nested_mkdir(
        path: str | os.PathLike[str], mode: int = 0o777,
        *, dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and destination.is_dir() and (
            path == "lib64" or (Path(path) == destination / "lib64" and dir_fd is None)
        ):
            _ = destination.rename(parked)
            if swap_kind == "symlink":
                _ = destination.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(destination)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", swap_before_nested_mkdir)
        with pytest.raises(cuda_validation.CudaProvisionError):
            cuda_validation.extract_cuda_package(
                payload, package, destination, staging=root / "stage"
            )
    assert swapped
    foreign_root = foreign if swap_kind == "symlink" else destination
    assert (foreign_root / "sentinel").read_bytes() == b"external data"
    assert not (foreign_root / "lib64").exists()


@pytest.mark.skipif(
    os.name != "posix",  # ruff: ignore[magic-value-comparison]
    reason="requires POSIX directory descriptors",
)
def test_cuda_overlay_rejects_forged_parent_enumeration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged listing must not copy the overlay source's parent."""
    source = tmp_path / "incoming" / "package"
    source.mkdir(parents=True)
    _ = (source.parent / "outside.txt").write_bytes(b"outside the package")
    destination = tmp_path / "outgoing" / "toolkit"
    destination.mkdir(parents=True)
    status = source.stat()
    source_identity = (status.st_dev, status.st_ino)
    native_iterdir = Path.iterdir
    forged = False

    def forge_parent(path: Path) -> object:
        nonlocal forged
        if path == source:
            if not forged:
                forged = True
                return iter((source / "..",))
            return iter(())
        return native_iterdir(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "iterdir", forge_parent)
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="enumeration"
        ):
            # This internal boundary is where untrusted receipts become paths.
            cuda_validation._copy_cuda_overlay(  # ruff: ignore[private-member-access]
                source, destination, source_identity
            )
    assert forged
    assert not (destination.parent / "outside.txt").exists()
    assert not (destination / "outside.txt").exists()


def test_cuda_overlay_copy_allows_identical_existing_verified_members(
    tmp_path: Path,
) -> None:
    """Repeating an identical verified package preserves its content."""
    payload = _payload()
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, _manifest(tmp_path, payload), LINUX_PLATFORM
    ).packages[0]
    destination = tmp_path / "toolkit"
    for _ in range(2):
        cuda_validation.extract_cuda_package(
            payload, package, destination, staging=tmp_path / "stage"
        )
    assert (destination / "lib64/libnvrtc.so.13").read_bytes() == NVRTC_BYTES
    assert (destination / "lib64/libnvrtc-builtins.so.13.3").read_bytes() == BUILTINS_BYTES


def test_cuda_overlay_copy_rejects_mismatched_existing_member(
    tmp_path: Path,
) -> None:
    """A conflicting preexisting overlay leaf is not silently overwritten."""
    payload = _payload()
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, _manifest(tmp_path, payload), LINUX_PLATFORM
    ).packages[0]
    destination = tmp_path / "toolkit"
    cuda_validation.extract_cuda_package(
        payload, package, destination, staging=tmp_path / "stage"
    )
    library = destination / "lib64/libnvrtc.so.13"
    _ = library.write_bytes(b"different toolkit contents")
    with pytest.raises(cuda_validation.CudaProvisionError, match="collision"):
        cuda_validation.extract_cuda_package(
            payload, package, destination, staging=tmp_path / "stage"
        )
    assert library.read_bytes() == b"different toolkit contents"


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("fault", [UnprintableHostOSError, UnprintableHostRuntimeError])
def test_cuda_overlay_copy_types_child_directory_open_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: type[Exception]
) -> None:
    """Overlay child-open failures remain typed without rendering foreign errors."""
    payload = _payload()
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, _manifest(tmp_path, payload), LINUX_PLATFORM
    ).packages[0]
    destination = tmp_path / "toolkit"
    native_open = os.open
    failure = fault("cannot open staging child")
    injected = False
    child_opens = 0

    def fail_child_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal injected, child_opens
        if path == "lib64" and dir_fd is not None:
            child_opens += 1
            if child_opens == 2:
                injected = True
                raise failure
        return native_open(path, flags, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", fail_child_open)
        with pytest.raises(
            cuda_validation.CudaProvisionError, match="overlay directory open"
        ) as caught:
            cuda_validation.extract_cuda_package(
                payload, package, destination, staging=tmp_path / "stage"
            )
    assert injected
    assert caught.value.__cause__ is failure
    assert not (destination / "lib64/libnvrtc.so.13").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("source_level", ["root", "nested"])
def test_cuda_overlay_copy_rejects_replaced_archive_source_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source_level: str
) -> None:
    """A swapped archive source cannot inject files outside the verified package."""
    root = tmp_path / "repository"
    root.mkdir()
    payload = _payload()
    package = cuda_validation.load_cuda_provision_manifest(
        root, _manifest(root, payload), LINUX_PLATFORM
    ).packages[0]
    destination = root / "toolkit"
    package_staging = root / "stage"
    archive_root = package_staging / PACKAGE_NAME / ARCHIVE_ROOT
    source = archive_root if source_level == "root" else archive_root / "lib64"
    parked = root / "parked-archive-source"
    foreign = tmp_path / "foreign-archive-source"
    foreign.mkdir()
    injection = foreign if source_level == "nested" else foreign / "lib64"
    injection.mkdir(exist_ok=True)
    _ = (injection / "untrusted.so").write_bytes(b"foreign bytes")
    native_scandir = os.scandir
    swapped = False

    def swap_during_source_listing(path: str | os.PathLike[str] | int) -> object:
        nonlocal swapped
        if not swapped and not isinstance(path, int) and Path(path) == source:
            _ = source.rename(parked)
            _ = foreign.rename(source)
            swapped = True
        return native_scandir(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "scandir", swap_during_source_listing)
        with pytest.raises(cuda_validation.CudaProvisionError):
            cuda_validation.extract_cuda_package(
                payload, package, destination, staging=package_staging
            )
    assert swapped
    assert not (destination / "lib64/untrusted.so").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_cuda_overlay_copy_rejects_source_directory_swapped_at_member_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An archive source replaced after listing cannot supply foreign library bytes."""
    root = tmp_path / "repository"
    root.mkdir()
    payload = _payload()
    package = cuda_validation.load_cuda_provision_manifest(
        root, _manifest(root, payload), LINUX_PLATFORM
    ).packages[0]
    destination = root / "toolkit"
    archive_root = root / "stage" / PACKAGE_NAME / ARCHIVE_ROOT
    source = archive_root / "lib64"
    target = source / "libnvrtc.so.13"
    parked = root / "parked-archive-source"
    foreign = tmp_path / "foreign-archive-source"
    foreign.mkdir()
    _ = (foreign / "libnvrtc.so.13").write_bytes(b"untrusted library")
    native_lstat = Path.lstat
    swapped = False

    def swap_before_member_status(path: Path) -> os.stat_result:
        nonlocal swapped
        if not swapped and path == target:
            _ = source.rename(parked)
            _ = foreign.rename(source)
            swapped = True
        return native_lstat(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", swap_before_member_status)
        with pytest.raises(cuda_validation.CudaProvisionError):
            cuda_validation.extract_cuda_package(
                payload, package, destination, staging=root / "stage"
            )
    assert swapped
    observed = destination / "lib64/libnvrtc.so.13"
    assert not observed.exists() or observed.read_bytes() != b"untrusted library"


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("swap_kind", ["physical", "symlink"])
def test_cuda_tar_symlink_creation_rejects_swapped_archive_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, swap_kind: str
) -> None:
    """Archive symlink creation must not target a foreign replacement parent."""
    root = tmp_path / "repository"
    root.mkdir()
    payload = _tar_symlink_payload()
    package = cuda_validation.load_cuda_provision_manifest(
        root, _manifest(root, payload), LINUX_PLATFORM
    ).packages[0]
    parent = root / "stage" / PACKAGE_NAME / ARCHIVE_ROOT / "lib64"
    parked = root / "parked-archive-parent"
    foreign = tmp_path / "foreign-archive-parent"
    foreign.mkdir()
    _ = (foreign / "sentinel").write_bytes(b"foreign data")
    native_symlink = os.symlink
    swapped = False

    def swap_at_symlink(
        src: str | bytes | os.PathLike[str],
        dst: str | bytes | os.PathLike[str],
        target_is_directory: bool = False,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and Path(dst).name == "libnvrtc.so.13":
            swapped = True
            _ = parent.rename(parked)
            if swap_kind == "symlink":
                _ = parent.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(parent)
        native_symlink(src, dst, target_is_directory=target_is_directory, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "symlink", swap_at_symlink)
        with pytest.raises(cuda_validation.CudaProvisionError):
            cuda_validation.extract_cuda_package(
                payload, package, root / "toolkit", staging=root / "stage"
            )
    assert swapped
    replacement = foreign if swap_kind == "symlink" else parent
    assert (replacement / "sentinel").read_bytes() == b"foreign data"
    assert not (replacement / "libnvrtc.so.13").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX symlink fixture")
def test_cuda_nonposix_overlay_rejects_linked_destination_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Windows fallback may not copy through existing linked toolkit paths."""
    source = tmp_path / "source"
    (source / "lib64").mkdir(parents=True)
    _ = (source / "lib64" / "nvrtc.dll").write_bytes(b"trusted")
    destination = tmp_path / "destination"
    destination.mkdir()
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    _ = (destination / "lib64").symlink_to(foreign, target_is_directory=True)
    status = source.stat()

    class _NonPosixHost:
        name = "nt"

        def __getattr__(self, name: str) -> object:
            return getattr(os, name)

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation, "os", _NonPosixHost())
        with pytest.raises(cuda_validation.CudaProvisionError, match="redirect"):
            cuda_validation._copy_cuda_overlay(  # noqa: SLF001, RUF100
                source, destination, (status.st_dev, status.st_ino),
            )
    if (foreign / "nvrtc.dll").exists():
        pytest.fail("non-POSIX overlay copied bytes through a destination symlink")


@pytest.mark.skipif(os.name != "posix", reason="requires test host link fixtures")
@pytest.mark.parametrize("link_kind", ("file", "directory", "hardlink"))
def test_cuda_nonposix_overlay_rejects_foreign_source_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, link_kind: str
) -> None:
    """Post-extraction link substitution cannot publish foreign data on Windows."""
    source = tmp_path / "source"
    (source / "lib64").mkdir(parents=True)
    destination = tmp_path / "destination"
    destination.mkdir()
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"outside archive")
    member = source / "lib64" / "unexpected"
    if link_kind == "file":
        _ = member.symlink_to(sentinel)
    elif link_kind == "directory":
        _ = member.symlink_to(foreign, target_is_directory=True)
    else:
        os.link(sentinel, member)
    status = source.stat()

    class _NonPosixHost:
        name = "nt"

        def __getattr__(self, name: str) -> object:
            return getattr(os, name)

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation, "os", _NonPosixHost())
        with pytest.raises(cuda_validation.CudaProvisionError, match="source member"):
            cuda_validation._copy_cuda_overlay(  # noqa: SLF001, RUF100
                source, destination, (status.st_dev, status.st_ino)
            )
    assert sentinel.read_bytes() == b"outside archive"
    assert not (destination / "lib64" / "unexpected").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX symlink fixtures")
@pytest.mark.parametrize("link_kind", ("file", "directory"))
def test_cuda_nonposix_overlay_preserves_contained_source_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, link_kind: str
) -> None:
    """A safe relative source symlink remains eligible in portable overlays."""
    source = tmp_path / "source"
    (source / "lib64" / "real").mkdir(parents=True)
    _ = (source / "lib64" / "real" / "nvrtc.dll").write_bytes(b"trusted")
    link = source / "lib64" / "alias"
    if link_kind == "file":
        link = source / "lib64" / "alias.dll"
        _ = link.symlink_to("real/nvrtc.dll")
    else:
        _ = link.symlink_to("real", target_is_directory=True)
    destination = tmp_path / "destination"
    destination.mkdir()
    status = source.stat()

    class _NonPosixHost:
        name = "nt"

        def __getattr__(self, name: str) -> object:
            return getattr(os, name)

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation, "os", _NonPosixHost())
        cuda_validation._copy_cuda_overlay(  # noqa: SLF001, RUF100
            source, destination, (status.st_dev, status.st_ino)
        )
    copied = destination / link.relative_to(source)
    assert copied.is_symlink()
    if link_kind == "file":
        assert copied.read_bytes() == b"trusted"
    else:
        assert (copied / "nvrtc.dll").read_bytes() == b"trusted"


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX link fixtures")
@pytest.mark.parametrize("link_kind", ("symlink", "hardlink"))
def test_cuda_nonposix_overlay_does_not_write_through_late_file_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, link_kind: str
) -> None:
    """Late target links cannot make portable copytree overwrite outside bytes."""
    source = tmp_path / "source"
    (source / "lib64").mkdir(parents=True)
    _ = (source / "lib64" / "nvrtc.dll").write_bytes(b"trusted archive")
    destination = tmp_path / "destination"
    (destination / "lib64").mkdir(parents=True)
    outside = tmp_path / "outside"
    _ = outside.write_bytes(b"foreign sentinel")
    target = destination / "lib64" / "nvrtc.dll"
    status = source.stat()
    native_copytree = shutil.copytree
    inserted = False

    class _NonPosixHost:
        name = "nt"

        def __getattr__(self, name: str) -> object:
            return getattr(os, name)

    def late_link(
        src: Path, dst: Path, *args: object, **options: object
    ) -> Path:
        nonlocal inserted
        if not inserted:
            if link_kind == "symlink":
                _ = target.symlink_to(outside)
            else:
                os.link(outside, target)
            inserted = True
        return native_copytree(src, dst, *args, **options)

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation, "os", _NonPosixHost())
        isolated.setattr(shutil, "copytree", late_link)
        with pytest.raises(cuda_validation.CudaProvisionError, match="collision"):
            cuda_validation._copy_cuda_overlay(  # noqa: SLF001, RUF100
                source, destination, (status.st_dev, status.st_ino)
            )
    assert inserted
    assert outside.read_bytes() == b"foreign sentinel"


def test_cuda_nonposix_overlay_does_not_rewrite_identical_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Identical archive overlaps must preserve preexisting physical metadata."""
    source = tmp_path / "source"
    (source / "lib64").mkdir(parents=True)
    _ = (source / "lib64" / "nvrtc.dll").write_bytes(b"matching")
    destination = tmp_path / "destination"
    (destination / "lib64").mkdir(parents=True)
    target = destination / "lib64" / "nvrtc.dll"
    _ = target.write_bytes(b"matching")
    os.utime(target, ns=(1234567890000, 1234567890000))
    original = target.stat()
    status = source.stat()

    class _NonPosixHost:
        name = "nt"

        def __getattr__(self, name: str) -> object:
            return getattr(os, name)

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation, "os", _NonPosixHost())
        cuda_validation._copy_cuda_overlay(  # noqa: SLF001, RUF100
            source, destination, (status.st_dev, status.st_ino)
        )
    assert target.read_bytes() == b"matching"
    after = target.stat()
    assert (after.st_dev, after.st_ino, after.st_mtime_ns) == (
        original.st_dev, original.st_ino, original.st_mtime_ns
    )


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX symlink fixtures")
@pytest.mark.parametrize("link_kind", ("file", "directory"))
def test_cuda_nonposix_overlay_rejects_source_link_swapped_during_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, link_kind: str
) -> None:
    """A substituted source link after preflight cannot reach publication."""
    source = tmp_path / "source"
    leaf = source / "lib64" / "real"
    if link_kind == "file":
        leaf = source / "lib64" / "nvrtc.dll"
        leaf.parent.mkdir(parents=True)
        _ = leaf.write_bytes(b"trusted source")
    else:
        leaf.mkdir(parents=True)
        _ = (leaf / "nvrtc.dll").write_bytes(b"trusted source")
    destination = tmp_path / "destination"
    destination.mkdir()
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    _ = (foreign / "nvrtc.dll").write_bytes(b"outside archive")
    original_copytree = shutil.copytree
    swapped = False
    status = source.stat()

    class _NonPosixHost:
        name = "nt"

        def __getattr__(self, name: str) -> object:
            return getattr(os, name)

    def exchange_source(
        src: Path, dst: Path, *args: object, **options: object
    ) -> Path:
        nonlocal swapped
        if not swapped:
            swapped = True
            if leaf.is_dir():
                shutil.rmtree(leaf)
            else:
                leaf.unlink()
            _ = leaf.symlink_to(
                foreign if link_kind == "directory" else foreign / "nvrtc.dll",
                target_is_directory=(link_kind == "directory"),
            )
        return original_copytree(src, dst, *args, **options)

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation, "os", _NonPosixHost())
        isolated.setattr(shutil, "copytree", exchange_source)
        with pytest.raises(cuda_validation.CudaProvisionError, match="source member"):
            cuda_validation._copy_cuda_overlay(  # noqa: SLF001, RUF100
                source, destination, (status.st_dev, status.st_ino)
            )
    assert swapped
    assert (foreign / "nvrtc.dll").read_bytes() == b"outside archive"


def test_cuda_nonposix_overlay_rejects_same_byte_source_inode_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replaced archive member inode cannot pass merely by matching bytes."""
    source = tmp_path / "source"
    (source / "lib64").mkdir(parents=True)
    member = source / "lib64" / "nvrtc.dll"
    _ = member.write_bytes(b"trusted source")
    parked = tmp_path / "parked"
    destination = tmp_path / "destination"
    destination.mkdir()
    identity = source.stat()
    native_copytree = shutil.copytree
    swapped = False

    class _NonPosixHost:
        name = "nt"

        def __getattr__(self, name: str) -> object:
            return getattr(os, name)

    def swap_source(
        src: Path, dst: Path, *args: object, **kwargs: object
    ) -> Path:
        nonlocal swapped
        if not swapped:
            _ = member.rename(parked)
            _ = member.write_bytes(b"trusted source")
            swapped = True
        return native_copytree(src, dst, *args, **kwargs)

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation, "os", _NonPosixHost())
        isolated.setattr(shutil, "copytree", swap_source)
        with pytest.raises(cuda_validation.CudaProvisionError, match="source member"):
            cuda_validation._copy_cuda_overlay(  # noqa: SLF001, RUF100
                source, destination, (identity.st_dev, identity.st_ino)
            )
    assert swapped
    assert parked.read_bytes() == b"trusted source"


def test_cuda_nonposix_overlay_rejects_member_added_during_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """New files after archive preflight cannot enter the verified toolkit."""
    source = tmp_path / "source"
    (source / "lib64").mkdir(parents=True)
    _ = (source / "lib64" / "nvrtc.dll").write_bytes(b"trusted")
    destination = tmp_path / "destination"
    destination.mkdir()
    source_identity = source.stat()
    original_copytree = shutil.copytree
    added = False

    class _NonPosixHost:
        name = "nt"

        def __getattr__(self, name: str) -> object:
            return getattr(os, name)

    def add_member(
        src: Path, dst: Path, *args: object, **kwargs: object
    ) -> Path:
        nonlocal added
        if not added:
            _ = (source / "lib64" / "injected.dll").write_bytes(b"untracked")
            added = True
        return original_copytree(src, dst, *args, **kwargs)

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation, "os", _NonPosixHost())
        isolated.setattr(shutil, "copytree", add_member)
        with pytest.raises(cuda_validation.CudaProvisionError, match="source members changed"):
            cuda_validation._copy_cuda_overlay(  # noqa: SLF001, RUF100
                source, destination, (source_identity.st_dev, source_identity.st_ino)
            )
    assert added


@pytest.mark.parametrize("existing", [b"matching", b"different"])
def test_cuda_nonposix_overlay_preserves_existing_file_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing: bytes,
) -> None:
    """Windows-compatible overlays can merge only byte-identical files."""
    source = tmp_path / "source"
    (source / "lib64").mkdir(parents=True)
    _ = (source / "lib64" / "nvrtc.dll").write_bytes(b"matching")
    destination = tmp_path / "destination"
    (destination / "lib64").mkdir(parents=True)
    target = destination / "lib64" / "nvrtc.dll"
    _ = target.write_bytes(existing)
    status = source.stat()

    class _NonPosixHost:
        name = "nt"

        def __getattr__(self, name: str) -> object:
            return getattr(os, name)

    with monkeypatch.context() as isolated:
        isolated.setattr(cuda_validation, "os", _NonPosixHost())
        if existing != b"matching":
            with pytest.raises(cuda_validation.CudaProvisionError, match="collision"):
                cuda_validation._copy_cuda_overlay(  # noqa: SLF001, RUF100
                    source, destination, (status.st_dev, status.st_ino),
                )
        else:
            cuda_validation._copy_cuda_overlay(  # noqa: SLF001, RUF100
                source, destination, (status.st_dev, status.st_ino),
            )
    expected = existing
    if target.read_bytes() != expected:
        pytest.fail("non-POSIX overlay changed an existing incompatible file")


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("cleanup_kind", ["package", "provision"])
@pytest.mark.parametrize("swap_kind", ["physical", "symlink"])
def test_cuda_cleanup_does_not_delete_replaced_staging_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleanup_kind: str,
    swap_kind: str,
) -> None:
    """Post-validation cleanup cannot recursively remove an exchanged foreign tree."""
    root = tmp_path / "repository"
    root.mkdir()
    payload = _payload()
    manifest = _manifest(root, payload)
    package = cuda_validation.load_cuda_provision_manifest(
        root, manifest, LINUX_PLATFORM
    ).packages[0]
    if cleanup_kind == "package":
        stage = root / "stage" / PACKAGE_NAME
    else:
        stage = root / ".temp" / f"cuda-provision-{LINUX_PLATFORM}"
    parked = root / "parked-stage"
    foreign = tmp_path / "foreign-stage"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"foreign content survives")
    native_open = os.open
    swapped = False

    def swap_at_cleanup_open(
        path: str | os.PathLike[str], flags: int, mode: int = 0o777,
        *, dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        ready = (
            (root / "toolkit/lib64/libnvrtc.so.13").exists()
            if cleanup_kind == "package"
            else (root / TOOLKIT_ROOT).exists()
        )
        if not swapped and ready and Path(path) == stage and dir_fd is None:
            swapped = True
            _ = stage.rename(parked)
            if swap_kind == "symlink":
                _ = stage.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(stage)
        return native_open(path, flags, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", swap_at_cleanup_open)
        with pytest.raises(cuda_validation.CudaProvisionError):
            if cleanup_kind == "package":
                cuda_validation.extract_cuda_package(
                    payload, package, root / "toolkit", staging=root / "stage"
                )
            else:
                cuda_validation.provision_cuda_manifest(
                    root, manifest, LINUX_PLATFORM, downloader=_download_fixture(payload)
                )
    assert swapped
    replacement = stage if swap_kind == "physical" else foreign
    assert (replacement / "sentinel").read_bytes() == b"foreign content survives"


@pytest.mark.parametrize("cleanup_kind", ["package", "provision"])
def test_cuda_cleanup_rejects_false_success_without_removing_owned_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cleanup_kind: str
) -> None:
    """A host cleanup that reports success must actually remove its owned stage."""
    root = tmp_path / "repository"
    root.mkdir()
    payload = _payload()
    manifest = _manifest(root, payload)
    package = cuda_validation.load_cuda_provision_manifest(
        root, manifest, LINUX_PLATFORM
    ).packages[0]
    stage = (
        root / "stage" / PACKAGE_NAME
        if cleanup_kind == "package"
        else root / ".temp" / f"cuda-provision-{LINUX_PLATFORM}"
    )
    native_rmtree = shutil.rmtree
    suppressed = False

    def false_success(path: str | os.PathLike[str], *args: object, **kwargs: object) -> None:
        nonlocal suppressed
        if Path(path) == stage:
            suppressed = True
            return
        native_rmtree(path, *args, **kwargs)

    with monkeypatch.context() as isolated:
        isolated.setattr(shutil, "rmtree", false_success)
        with pytest.raises(cuda_validation.CudaProvisionError, match="cleanup did not remove"):
            if cleanup_kind == "package":
                cuda_validation.extract_cuda_package(
                    payload, package, root / "toolkit", staging=root / "stage"
                )
            else:
                cuda_validation.provision_cuda_manifest(
                    root, manifest, LINUX_PLATFORM, downloader=_download_fixture(payload)
                )
    assert suppressed
    assert stage.is_dir()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("swap_kind", ["physical", "symlink"])
def test_cuda_nonlinux_publication_never_moves_substituted_source_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, swap_kind: str
) -> None:
    """Non-Linux POSIX publication may only rename the admitted staged inode."""
    source_parent = tmp_path / "staging"
    source_parent.mkdir()
    staged = source_parent / "toolkit"
    staged.mkdir()
    _ = (staged / "owned.bin").write_bytes(b"trusted")
    target_parent = tmp_path / "target"
    target_parent.mkdir()
    target = target_parent / "toolkit"
    parked = tmp_path / "parked-staging"
    foreign = tmp_path / "foreign-staging"
    foreign.mkdir()
    foreign_toolkit = foreign / "toolkit"
    foreign_toolkit.mkdir()
    _ = (foreign_toolkit / "foreign.bin").write_bytes(b"untrusted")
    native_replace = os.replace
    swapped = False

    def exchange_source_before_rename(
        src: str | os.PathLike[str], dst: str | os.PathLike[str],
        *, src_dir_fd: int | None = None, dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped:
            swapped = True
            _ = source_parent.rename(parked)
            if swap_kind == "symlink":
                _ = source_parent.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(source_parent)
        native_replace(src, dst, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(sys, "platform", "darwin")
        isolated.setattr(os, "replace", exchange_source_before_rename)
        with pytest.raises(cuda_validation.CudaProvisionError):
            cuda_validation._publish_cuda_toolkit(  # pyright: ignore[reportPrivateUsage]
                staged, target
            )
    assert swapped
    replacement = source_parent if swap_kind == "physical" else foreign
    assert (replacement / "toolkit/foreign.bin").read_bytes() == b"untrusted"
    assert not (target / "foreign.bin").exists()


def test_cuda_nonlinux_posix_publication_preserves_exact_staged_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The portable POSIX path still publishes the verified source directory."""
    source = tmp_path / "staging"
    source.mkdir()
    staged = source / "toolkit"
    staged.mkdir()
    _ = (staged / "owned.bin").write_bytes(b"trusted")
    parent = tmp_path / "destination"
    parent.mkdir()
    target = parent / "toolkit"
    with monkeypatch.context() as isolated:
        isolated.setattr(sys, "platform", "darwin")
        cuda_validation._publish_cuda_toolkit(  # pyright: ignore[reportPrivateUsage]
            staged, target
        )
    assert (target / "owned.bin").read_bytes() == b"trusted"
    assert not staged.exists()


@pytest.mark.parametrize("archive_format", [_TAR_FORMAT, _ZIP_FORMAT])
def test_cuda_rejects_oversized_declared_archive_member_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    archive_format: str,
) -> None:
    """An archive member cannot demand unbounded decompression or allocation."""
    is_zip = archive_format == _ZIP_FORMAT
    payload = _zip_payload() if is_zip else _payload()
    manifest = _manifest(
        tmp_path, payload,
        {"relative_path": _ZIP_PACKAGE_PATH if is_zip else PACKAGE_PATH},
    )
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, manifest, LINUX_PLATFORM
    ).packages[0]
    if is_zip:
        original = zipfile.ZipFile.infolist

        def oversized_zip(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
            members = original(archive)
            members[0].file_size = 1024 * 1024 * 1024
            return members

        monkeypatch.setattr(zipfile.ZipFile, "infolist", oversized_zip)
    else:
        original_tar = tarfile.TarFile.__iter__

        def oversized_tar(archive: tarfile.TarFile) -> Iterator[tarfile.TarInfo]:
            for member in original_tar(archive):
                if member.name == NVRTC_MEMBER:
                    member.size = 1024 * 1024 * 1024
                yield member

        monkeypatch.setattr(tarfile.TarFile, "__iter__", oversized_tar)
    with pytest.raises(cuda_validation.CudaProvisionError, match="member byte limit"):
        cuda_validation.extract_cuda_package(
            payload, package, tmp_path / "toolkit", staging=tmp_path / "stage"
        )
    assert not (tmp_path / "toolkit/lib64/libnvrtc.so.13").exists()


@pytest.mark.parametrize("archive_format", [_TAR_FORMAT, _ZIP_FORMAT])
def test_cuda_rejects_excessive_combined_archive_expansion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, archive_format: str
) -> None:
    """Many individually bounded entries cannot exhaust staging storage."""
    is_zip = archive_format == _ZIP_FORMAT
    payload = _zip_payload() if is_zip else _payload()
    manifest = _manifest(
        tmp_path, payload,
        {"relative_path": _ZIP_PACKAGE_PATH if is_zip else PACKAGE_PATH},
    )
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, manifest, LINUX_PLATFORM
    ).packages[0]
    oversized_size = 128 * 1024 * 1024
    if is_zip:
        original_zip = zipfile.ZipFile.infolist

        def many_zip(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
            members = original_zip(archive)
            for i in range(9):
                extra = zipfile.ZipInfo(f"{ARCHIVE_ROOT}/lib64/fake{i}.so")
                extra.file_size = oversized_size
                members.append(extra)
            return members

        monkeypatch.setattr(zipfile.ZipFile, "infolist", many_zip)
    else:
        original_tar = tarfile.TarFile.__iter__

        def many_tar(archive: tarfile.TarFile) -> Iterator[tarfile.TarInfo]:
            yield from original_tar(archive)
            for i in range(9):
                extra = tarfile.TarInfo(f"{ARCHIVE_ROOT}/lib64/fake{i}.so")
                extra.size = oversized_size
                yield extra

        monkeypatch.setattr(tarfile.TarFile, "__iter__", many_tar)
    with pytest.raises(cuda_validation.CudaProvisionError, match="expanded byte limit"):
        cuda_validation.extract_cuda_package(
            payload, package, tmp_path / "toolkit", staging=tmp_path / "stage"
        )
    assert not (tmp_path / "toolkit/lib64/libnvrtc.so.13").exists()


def test_cuda_corrupted_zip_deflate_is_typed_without_publication(
    tmp_path: Path,
) -> None:
    """A pinned ZIP with invalid Deflate block data cannot publish a toolkit."""
    output = io.BytesIO()
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        archive.writestr(NVRTC_MEMBER, NVRTC_BYTES * 256)
    payload = bytearray(output.getvalue())
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        info = archive.getinfo(NVRTC_MEMBER)
    offset = (
        info.header_offset
        + zipfile.sizeFileHeader
        + len(info.filename.encode("utf-8"))
        + len(info.extra)
    )
    payload[offset] = 0x07  # Reserved Deflate block kind.
    damaged = bytes(payload)
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path,
        _manifest(tmp_path, damaged, {"relative_path": _ZIP_PACKAGE_PATH}),
        LINUX_PLATFORM,
    ).packages[0]
    with pytest.raises(
        cuda_validation.CudaProvisionError,
        match="cannot extract CUDA zip archive",
    ) as caught:
        cuda_validation.extract_cuda_package(
            damaged,
            package,
            tmp_path / "toolkit",
            staging=tmp_path / "stage",
        )
    assert isinstance(caught.value.__cause__, zlib.error)
    assert not (tmp_path / "toolkit").exists()


def test_cuda_corrupted_zip_zstandard_is_typed_without_publication(
    tmp_path: Path,
) -> None:
    """Malformed Zstandard members cannot escape the pinned ZIP boundary."""
    output = io.BytesIO()
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_ZSTANDARD
    ) as archive:
        archive.writestr(NVRTC_MEMBER, NVRTC_BYTES * 256)
    payload = bytearray(output.getvalue())
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        info = archive.getinfo(NVRTC_MEMBER)
    offset = (
        info.header_offset
        + zipfile.sizeFileHeader
        + len(info.filename.encode("utf-8"))
        + len(info.extra)
    )
    payload[offset] = 0xFF  # Invalid Zstandard frame descriptor.
    damaged = bytes(payload)
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path,
        _manifest(tmp_path, damaged, {"relative_path": _ZIP_PACKAGE_PATH}),
        LINUX_PLATFORM,
    ).packages[0]
    with pytest.raises(
        cuda_validation.CudaProvisionError,
        match="cannot extract CUDA zip archive: ZstdError",
    ) as caught:
        cuda_validation.extract_cuda_package(
            damaged,
            package,
            tmp_path / "toolkit",
            staging=tmp_path / "stage",
        )
    assert type(caught.value.__cause__) is zstd.ZstdError
    assert not (tmp_path / "toolkit").exists()


@pytest.mark.parametrize("failure_type", [zlib.error, NotImplementedError])
def test_cuda_zip_decoder_faults_remain_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Corrupt Deflate and unsupported ZIP methods yield typed failures."""
    payload = _zip_payload()
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path,
        _manifest(tmp_path, payload, {"relative_path": _ZIP_PACKAGE_PATH}),
        LINUX_PLATFORM,
    ).packages[0]
    failure = failure_type("corrupt ZIP compressed member")

    def reject_open(*args: object, **kwargs: object) -> object:
        _ = args, kwargs
        raise failure

    with monkeypatch.context() as isolated:
        isolated.setattr(zipfile.ZipFile, "open", reject_open)
        with pytest.raises(
            cuda_validation.CudaProvisionError,
            match="cannot extract CUDA zip archive",
        ) as caught:
            cuda_validation.extract_cuda_package(
                payload,
                package,
                tmp_path / "toolkit",
                staging=tmp_path / "stage",
            )
    assert caught.value.__cause__ is failure
    assert not (tmp_path / "toolkit").exists()


@pytest.mark.parametrize("archive_format", [_TAR_FORMAT, _ZIP_FORMAT])
@pytest.mark.parametrize(
    "failure_type",
    [UnprintableHostRuntimeError, ValueError, EOFError, lzma.LZMAError],
)
def test_cuda_archive_member_open_faults_remain_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    archive_format: str,
    failure_type: type[Exception],
) -> None:
    """Archive stream adapters cannot escape the CUDA provisioning error contract."""
    is_zip = archive_format == _ZIP_FORMAT
    payload = _zip_payload() if is_zip else _payload()
    manifest = _manifest(
        tmp_path, payload,
        {"relative_path": _ZIP_PACKAGE_PATH if is_zip else PACKAGE_PATH},
    )
    package = cuda_validation.load_cuda_provision_manifest(
        tmp_path, manifest, LINUX_PLATFORM
    ).packages[0]
    failure = failure_type("untrusted archive stream failure")

    def reject_open(*_args: object, **_kwargs: object) -> object:
        raise failure

    with monkeypatch.context() as isolated:
        if is_zip:
            isolated.setattr(zipfile.ZipFile, "open", reject_open)
        else:
            isolated.setattr(tarfile.TarFile, "extractfile", reject_open)
        kind = "zip" if is_zip else "tar"
        with pytest.raises(
            cuda_validation.CudaProvisionError, match=f"cannot extract CUDA {kind} archive"
        ) as caught:
            cuda_validation.extract_cuda_package(
                payload, package, tmp_path / "toolkit", staging=tmp_path / "stage"
            )
    assert caught.value.__cause__ is failure
    assert not (tmp_path / "toolkit/lib64/libnvrtc.so.13").exists()
