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
import os
from pathlib import Path
import tarfile
from typing import TYPE_CHECKING
from typing import cast
from typing import override
from typing import Self
import zipfile

import pytest
from scripts.bootstrap import cuda_validation
from scripts.bootstrap import project

if TYPE_CHECKING:
    from collections.abc import Callable

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
