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
import tarfile
from typing import TYPE_CHECKING

import pytest
from scripts.bootstrap import cuda_validation
from scripts.bootstrap import project

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

LINUX_PLATFORM = "linux-x86_64"
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
