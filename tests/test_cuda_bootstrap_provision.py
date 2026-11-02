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
    filename: str,
    invalid_count: str,
) -> None:
    real_write = Path.write_bytes

    def wrong_write(path: Path, data: bytes) -> int:
        if path.name == filename:
            _ = real_write(path, data[:-1])
            return _bad_write_count(invalid_count, len(data))
        return real_write(path, data)

    monkeypatch.setattr(Path, "write_bytes", wrong_write)


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
    _inject_short_write(monkeypatch, "libnvrtc.so.13", invalid_count)
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
    _inject_short_write(
        monkeypatch, cuda_validation.CUDA_PROVISION_MARKER, invalid_count
    )
    with pytest.raises(cuda_validation.CudaProvisionError, match="write count"):
        _ = cuda_validation.provision_cuda_manifest(
            tmp_path,
            manifest_path,
            LINUX_PLATFORM,
            downloader=_download_fixture(payload),
        )
    assert not (tmp_path / TOOLKIT_ROOT).exists()
    assert not (tmp_path / ".temp/cuda-provision-linux-x86_64").exists()


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
