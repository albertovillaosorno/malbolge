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
#   - Cross-platform checkout bootstrap regression evidence.
# - Must-Not:
#   - Download native toolchains or claim Linux CUDA runtime support.
# - Allows:
#   - Inputs: temporary roots, manifests, and explicit platform identities.
#   - Outputs: deterministic layouts, launchers, and component status.
#   - Side effects: temporary files and directories only.
# - Split-When:
#   - Split when native toolchain provisioning gains executable behavior.
# - Merge-When:
#   - Merge when another test owns this exact bootstrap contract.
# - Summary:
#   - Project bootstrap and platform-layout regressions.
# - Description:
#   - Verifies checkout initialization without requiring optional hardware.
# - Usage:
#   - Runs with the repository Python test suite.
# - Defaults:
#   - Optional components report missing or unsupported instead of guessing.
#

"""Project bootstrap and platform-layout regressions."""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import tarfile
import tempfile
import urllib.request
import zipfile
from contextlib import suppress
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO, Never, Self, TextIO, cast, final, override

import pytest
from scripts.bootstrap import (
    cuda_validation,
    llvm_development_validation,
    llvm_validation,
    project,
    python_validation,
)

if TYPE_CHECKING:
    from collections.abc import Callable

BASEDPYRIGHT_TOOL = "basedpyright"
CUDA_VERSION_ROOT = ".dependencies/cuda/13.3.1/toolkit"
CUDA_TOOLKIT_ROOT_FIELD = "toolkit_root"
CUDA_WINDOWS_MANIFEST_SHA256 = (
    "b8249cc1accf4b0532779c7c42e6505c9840d7208b4ab945e54daa456206b95e"
)
CUDA_LINUX_MANIFEST = "toolchain-linux-x86_64.json"
CUDA_MANIFEST_INDEX = "toolchain-manifests.json"
CUDA_NVRTC_LABEL = "NVRTC"
WINDOWS_PLATFORM = "windows-x86_64"
LINUX_PLATFORM = "linux-x86_64"
LLVM_DEVELOPMENT_COMPONENT = "llvm-development"
CAPTURED_BOOTSTRAP_ARGUMENTS = "captured bootstrap arguments"
RUST_CHANNEL = "1.98.1"
RUST_NIGHTLY_CHANNEL = "nightly-2026-07-14"
RUST_CARGO_BYTES = b"cargo-1.98.1"
RUST_RUSTC_BYTES = b"rustc-1.98.1"
RUST_STD_BYTES = b"rust-std"
RUFF_BYTES = b"ruff"
OUTSIDE_JIG_ALIAS_BYTES = b"retain outside"
EMPTY_JIG_STAGE_BYTES = b""
JIG_BINARY_READ_MODE = "rb"
JIG_BINARY_WRITE_MODE = "wb"
PYTHON_LAUNCHER_NAME = "python"
PYTEST_LAUNCHER_NAME = "pytest"
STALE_LAUNCHER_BYTES = b"stale"
GIT_VERSION = "2.55.0"
GIT_BYTES = b"git-2.55.0"
GIT_COMPONENT = "git"
SYMLINK_SUBSTITUTION = "symlink"
POSIX_NAME = "posix"
CARGO_FILENAME = "cargo"
IMPORT_MANIFEST = "manifest"
IMPORT_SOURCE_MUTATION = "source"
FOREIGN_PARENT_BYTES = b"foreign-parent"
FOREIGN_ROOT_BYTES = b"foreign-root"
FOREIGN_TOOLCHAIN_BYTES = b"foreign-toolchain"
FOREIGN_RUSTLIB_BYTES = b"foreign-rustlib"
FOREIGN_IMPORT_BYTES = b"do not change foreign tree"
GIT_HELPER_BYTES = b"git-helper"
GIT_MARKER_BYTES = b"malbolge-git-import/v1\n"
RUST_MARKER_BYTES = b"malbolge-rust-toolchain-import/v1\n"
MARKER_SHORT = "short"
MARKER_SAME_LENGTH = "same-length"
MARKER_LONG = "long"
IMPORT_MARKER_CASES = (
    (project.GIT_IMPORT_MARKER, GIT_MARKER_BYTES, project.git_import_complete),
    (
        project.RUST_IMPORT_MARKER,
        RUST_MARKER_BYTES,
        project.rust_toolchain_import_complete,
    ),
)
WINDOWS_PYTHON = "python.exe"
WINDOWS_PYTHON_LAUNCHER = "python-jig.cmd"
WINDOWS_PYTEST = "pytest.exe"
WINDOWS_PYTEST_LAUNCHER = "pytest-jig.cmd"
POSIX_PYTHON = "python"
POSIX_PYTHON_LAUNCHER = "python-jig"
POSIX_PYTEST = "pytest"
POSIX_PYTEST_LAUNCHER = "pytest-jig"
POSIX_HEADER = "#!/bin/sh\nset -eu\n"
CACHE_VARIABLE = "PYTHONPYCACHEPREFIX"
POSIX_PYTHON_EXEC = 'exec "$SCRIPT_DIR/python" "$@"'
POSIX_PYTEST_EXEC = 'exec "$SCRIPT_DIR/python" -m pytest "$@"'
POSIX_JIG_BASEDPYRIGHT_EXEC = '../bin/basedpyright" "$@"'
POSIX_JIG_PYTEST_EXEC = '../bin/python" -m pytest "$@"'
POSIX_JIG_PYTEST_PROBE_ARGV = "-m pytest --probe"
LINUX_AARCH64 = "linux-aarch64"
UV_VERSION = "0.12.20"
PIP_REQUIREMENT_PREFIX = "pip=="
VALIDATION_REQUIREMENT_COUNT = 9
BOOTSTRAP_COMPOSITION = "src/automation/repository/composition"
WINDOWS_BOOTSTRAP_COMMAND = "py -3.14 -B -m scripts.bootstrap.project"
LINUX_BOOTSTRAP_COMMAND = "python3.14 -B -m scripts.bootstrap.project"
WINDOWS_UV_ASSET = "uv-x86_64-pc-windows-msvc.zip"


def test_bootstrap_documentation_disables_source_bytecode() -> None:
    """Host bootstrap commands expose imports and disable source bytecode."""
    readme = (project.ROOT / "README.md").read_text(encoding="utf-8")
    assert f'$env:PYTHONPATH = "$PWD/{BOOTSTRAP_COMPOSITION}"' in readme
    assert WINDOWS_BOOTSTRAP_COMMAND in readme
    assert f"export PYTHONPATH={BOOTSTRAP_COMPOSITION}" in readme
    assert LINUX_BOOTSTRAP_COMMAND in readme


def _write_cuda_manifest(root: Path, platform_id: str) -> Path:
    manifest = root / project.CUDA_TOOLCHAIN_MANIFEST
    manifest.parent.mkdir(parents=True)
    _ = manifest.write_text(
        json.dumps({
            "schema_version": project.CUDA_TOOLCHAIN_SCHEMA_VERSION,
            "platform": platform_id,
            "toolkit_root": CUDA_VERSION_ROOT,
        }),
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def _write_cuda_manifest_index(root: Path) -> Path:
    manifest_root = (root / project.CUDA_TOOLCHAIN_MANIFEST).parent
    index = manifest_root / CUDA_MANIFEST_INDEX
    _ = index.write_text(
        json.dumps({
            "schema_version": 1,
            "platforms": {
                WINDOWS_PLATFORM: {
                    "manifest": "toolchain.json",
                    "loader": "windll",
                    "driver_library": "nvcuda.dll",
                    "nvrtc_library": "bin/x64/nvrtc64_130_0.dll",
                },
                LINUX_PLATFORM: {
                    "manifest": CUDA_LINUX_MANIFEST,
                    "loader": "cdll",
                    "driver_library": "libcuda.so.1",
                    "nvrtc_library": "lib/libnvrtc.so.13",
                },
            },
        }),
        encoding="utf-8",
        newline="\n",
    )
    return index


def _write_platform_cuda_manifest(
    root: Path,
    platform_id: str,
    filename: str,
) -> Path:
    manifest = (root / project.CUDA_TOOLCHAIN_MANIFEST).parent / filename
    _ = manifest.write_text(
        json.dumps({
            "schema_version": project.CUDA_TOOLCHAIN_SCHEMA_VERSION,
            "cuda_release": "13.3 Update 1",
            "redistrib_manifest": "redistrib_13.3.1.json",
            "release_date": "2026-06-29",
            "platform": platform_id,
            "toolkit_root": CUDA_VERSION_ROOT,
            "packages": [],
            "redistrib_base_url": (
                "https://developer.download.nvidia.com/compute/cuda/redist/"
            ),
        }),
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def _write_rust_manifest(root: Path, channel: str = RUST_CHANNEL) -> Path:
    manifest = root / ".jig/version/rust-toolchain.toml"
    manifest.parent.mkdir(parents=True)
    _ = manifest.write_text(
        f'[toolchain]\nchannel = "{channel}"\n',
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def test_uv_platform_identity_normalizes_supported_hosts() -> None:
    """Uv bootstrap keys match the tracked host artifact identities."""
    assert (
        python_validation.uv_platform_id(
            system="Windows",
            machine="AMD64",
        )
        == WINDOWS_PLATFORM
    )
    assert (
        python_validation.uv_platform_id(
            system="Linux",
            machine="arm64",
        )
        == LINUX_AARCH64
    )


def test_uv_manifest_pins_exact_windows_artifact(tmp_path: Path) -> None:
    """Tracked uv metadata resolves one exact executable path."""
    artifact = python_validation.uv_artifact(WINDOWS_PLATFORM)
    executable = python_validation.uv_executable(artifact, tmp_path)

    assert artifact.version == UV_VERSION
    assert artifact.asset == WINDOWS_UV_ASSET
    assert artifact.base_url.startswith("https://github.com/astral-sh/uv/")
    assert len(artifact.sha256) == python_validation.SHA256_HEX_LENGTH
    assert executable == (tmp_path / ".dependencies/uv/0.12.20/bin/uv.exe")


def _copy_uv_manifest(tmp_path: Path) -> Path:
    manifest = tmp_path / "uv.json"
    _ = manifest.write_bytes(python_validation.UV_MANIFEST.read_bytes())
    return manifest


def test_uv_manifest_rejects_linked_leaf(tmp_path: Path) -> None:
    """Pinned uv authority must be a physical file, never a redirected alias."""
    manifest = _copy_uv_manifest(tmp_path)
    real = manifest.with_suffix(".real")
    _ = manifest.replace(real)
    _ = manifest.symlink_to(real)
    with pytest.raises(
        python_validation.ProvisionError, match=r"redirect|regular"
    ):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


def test_uv_manifest_rejects_linked_parent(tmp_path: Path) -> None:
    """An alias in the uv authority directory is not a trusted root."""
    real = tmp_path / "real"
    real.mkdir()
    _ = _copy_uv_manifest(real)
    alias = tmp_path / "alias"
    _ = alias.symlink_to(real, target_is_directory=True)
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, alias / "uv.json")


@pytest.mark.parametrize("masked", [False, 0])
def test_uv_manifest_rejects_masked_symlink_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    masked: object,
) -> None:
    """The parent inode, not a falsified host predicate, proves its type."""
    real = tmp_path / "real"
    real.mkdir()
    _ = _copy_uv_manifest(real)
    alias = tmp_path / "alias"
    _ = alias.symlink_to(real, target_is_directory=True)
    native = Path.is_symlink

    def masked_status(path: Path) -> bool:
        if path == alias:
            return cast("bool", masked)
        return native(path)

    monkeypatch.setattr(Path, "is_symlink", masked_status)
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, alias / "uv.json")


@pytest.mark.parametrize("predicate", ["is_symlink", "is_junction"])
def test_uv_manifest_rejects_foreign_leaf_link_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    predicate: str,
) -> None:
    """A false-like nonboolean host link result cannot admit the manifest."""
    manifest = _copy_uv_manifest(tmp_path)
    original = getattr(Path, predicate)

    def foreign_status(path: Path) -> bool:
        if path == manifest:
            return cast("bool", cast("object", 0))
        return cast("bool", original(path))

    monkeypatch.setattr(Path, predicate, foreign_status)
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


def test_uv_manifest_rejects_forged_lstat_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fabricated stat lookalike cannot certify pinned source bytes."""
    manifest = _copy_uv_manifest(tmp_path)
    native = Path.lstat

    class ForgedStatus:
        def __init__(self, observed: os.stat_result) -> None:
            self.st_mode: int = observed.st_mode
            self.st_dev: int = observed.st_dev
            self.st_ino: int = observed.st_ino
            self.st_size: int = observed.st_size
            self.st_mtime_ns: int = observed.st_mtime_ns
            self.st_ctime_ns: int = observed.st_ctime_ns

    def forged_status(path: Path) -> os.stat_result:
        status = native(path)
        if path == manifest:
            return cast("os.stat_result", cast("object", ForgedStatus(status)))
        return status

    monkeypatch.setattr(Path, "lstat", forged_status)
    with pytest.raises(python_validation.ProvisionError, match="native"):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


def test_uv_manifest_rejects_oversized_document(tmp_path: Path) -> None:
    """Uv metadata cannot force an unbounded read before validation."""
    manifest = tmp_path / "uv.json"
    with manifest.open("wb") as stream:
        _ = stream.truncate(python_validation.MAX_UV_MANIFEST_BYTES + 1)
    with pytest.raises(python_validation.ProvisionError, match="byte limit"):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


@pytest.mark.parametrize(
    "receipt_kind",
    ["bytearray", "bytes-subclass", "null"],
)
def test_uv_manifest_rejects_nonnative_read_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt_kind: str,
) -> None:
    """A matching-size stream proxy cannot replace native manifest bytes."""
    manifest = _copy_uv_manifest(tmp_path)
    native = python_validation._open_owned_binary_stream

    @final
    class ProxyStream:
        def __init__(self, descriptor: int) -> None:
            self.stream = native(descriptor)

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, size: int) -> object:
            content = self.stream.read(size)
            if receipt_kind == "bytearray":
                return bytearray(content)
            if receipt_kind == "bytes-subclass":
                return _UvArchiveBytesSubclass(content)
            return None

    def fake_open(descriptor: int) -> ProxyStream:
        return ProxyStream(descriptor)

    monkeypatch.setattr(python_validation, "_open_owned_binary_stream", fake_open)
    with pytest.raises(python_validation.ProvisionError, match="native bytes"):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


def test_uv_manifest_rejects_invalid_utf8(tmp_path: Path) -> None:
    """Uv encoding errors remain typed provisioning failures."""
    manifest = tmp_path / "uv.json"
    _ = manifest.write_bytes(bytes((0xFF,)))
    with pytest.raises(python_validation.ProvisionError, match="cannot read"):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


def test_uv_manifest_rejects_same_byte_inode_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replacing a validated path before open cannot silently switch inodes."""
    manifest = _copy_uv_manifest(tmp_path)
    replacement = tmp_path / "replacement.json"
    _ = replacement.write_bytes(manifest.read_bytes())
    real_open = os.open

    def swap_before_open(path: Path, flags: int) -> int:
        if path == manifest:
            _ = replacement.replace(manifest)
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_before_open)
    with pytest.raises(python_validation.ProvisionError, match="changed"):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


def test_uv_manifest_rejects_fifo_without_blocking(tmp_path: Path) -> None:
    """An existing pipe is rejected instead of waiting for a writer."""
    mkfifo = cast("Callable[[Path], None] | None", getattr(os, "mkfifo", None))
    if mkfifo is None:
        pytest.skip("FIFO unsupported")
    manifest = tmp_path / "uv.json"
    mkfifo(manifest)
    with pytest.raises(python_validation.ProvisionError, match="regular"):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


def test_uv_manifest_rejects_unknown_schema(tmp_path: Path) -> None:
    """Uv provisioning rejects manifests from an unknown schema revision."""
    manifest = tmp_path / "uv.json"
    parsed = cast(
        "object",
        json.loads(python_validation.UV_MANIFEST.read_text(encoding="utf-8")),
    )
    assert isinstance(parsed, dict)
    document = cast("dict[str, object]", parsed)
    document["schema_version"] = 2
    _ = manifest.write_text(
        json.dumps(document), encoding="utf-8", newline="\n"
    )
    with pytest.raises(
        python_validation.ProvisionError,
        match="unsupported uv toolchain manifest schema",
    ):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


def test_uv_manifest_binds_release_url_to_version(tmp_path: Path) -> None:
    """Uv release URL cannot drift independently from its pinned version."""
    manifest = tmp_path / "uv.json"
    parsed = cast(
        "object",
        json.loads(python_validation.UV_MANIFEST.read_text(encoding="utf-8")),
    )
    assert isinstance(parsed, dict)
    document = cast("dict[str, object]", parsed)
    document["base_url"] = (
        "https://github.com/astral-sh/uv/releases/download/0.11.17/"
    )
    _ = manifest.write_text(
        json.dumps(document), encoding="utf-8", newline="\n"
    )
    with pytest.raises(
        python_validation.ProvisionError,
        match="base_url must match the pinned release version",
    ):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


def test_uv_manifest_rejects_redirecting_asset_name(tmp_path: Path) -> None:
    """Uv archive asset cannot add URL path, query, or fragment authority."""
    manifest = tmp_path / "uv.json"
    parsed = cast(
        "object",
        json.loads(python_validation.UV_MANIFEST.read_text(encoding="utf-8")),
    )
    assert isinstance(parsed, dict)
    document = cast("dict[str, object]", parsed)
    artifacts_value = document.get("artifacts")
    assert isinstance(artifacts_value, dict)
    artifacts = cast("dict[str, object]", artifacts_value)
    windows_value = artifacts.get(WINDOWS_PLATFORM)
    assert isinstance(windows_value, dict)
    windows = cast("dict[str, object]", windows_value)
    windows["asset"] = "uv.zip?source=other"
    _ = manifest.write_text(
        json.dumps(document), encoding="utf-8", newline="\n"
    )
    with pytest.raises(
        python_validation.ProvisionError,
        match="asset must be one URL path segment",
    ):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


def test_uv_manifest_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    """Pinned uv identity never uses last-value-wins JSON semantics."""
    manifest = tmp_path / "uv.json"
    _ = manifest.write_text(
        concat := (
            '{"version":"0.12.20",'
            '"version":"0.11.17",'
            '"base_url":"https://github.com/astral-sh/uv/'
            'releases/download/0.12.20/",'
            '"artifacts":{}}'
        ),
        encoding="utf-8",
        newline="\n",
    )
    assert concat
    with pytest.raises(
        python_validation.ProvisionError,
        match="duplicate uv manifest JSON key: version",
    ):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


def test_uv_manifest_rejects_escaping_version_path(tmp_path: Path) -> None:
    """Pinned uv version cannot redirect repository-local provisioning."""
    manifest = tmp_path / "uv.json"
    parsed = cast(
        "object",
        json.loads(python_validation.UV_MANIFEST.read_text(encoding="utf-8")),
    )
    assert isinstance(parsed, dict)
    document = cast("dict[str, object]", parsed)
    document["version"] = "../escape"
    _ = manifest.write_text(
        json.dumps(document),
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(
        python_validation.ProvisionError,
        match="version must be one repository-local path segment",
    ):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


def test_uv_manifest_rejects_drive_relative_version_path(
    tmp_path: Path,
) -> None:
    """Pinned uv version cannot select Windows drive-relative state."""
    manifest = tmp_path / "uv.json"
    parsed = cast(
        "object",
        json.loads(python_validation.UV_MANIFEST.read_text(encoding="utf-8")),
    )
    assert isinstance(parsed, dict)
    document = cast("dict[str, object]", parsed)
    document["version"] = "D:escape"
    _ = manifest.write_text(
        json.dumps(document),
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(
        python_validation.ProvisionError,
        match="version must be one repository-local path segment",
    ):
        _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)


@pytest.mark.parametrize("bad_write_count", [1, None, True, -1, 1_000_000])
def test_uv_staging_rejects_incomplete_or_foreign_write_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_write_count: object,
) -> None:
    """Do not publish a corrupt executable on an invalid staging write."""
    artifact = python_validation.uv_artifact(LINUX_PLATFORM)
    executable = python_validation.uv_executable(artifact, tmp_path)
    temporary = executable.with_name(f"{executable.name}.tmp")
    binary = b"synthetic-uv-binary-payload"
    original_write = os.write

    def incomplete_write(descriptor: int, data: bytes) -> int:
        assert temporary.is_file()
        _ = original_write(descriptor, data[:1])
        return cast("int", bad_write_count)

    def fake_download(selected_artifact: python_validation.UvArtifact) -> bytes:
        assert selected_artifact == artifact
        return binary

    def fake_member(
        archive_data: bytes, selected_artifact: python_validation.UvArtifact
    ) -> bytes:
        assert archive_data == binary
        assert selected_artifact == artifact
        return binary

    def fake_run(command: list[str]) -> str:
        assert command == [str(executable), "--version"]
        return f"uv {artifact.version}"

    monkeypatch.setattr(os, "write", incomplete_write)
    monkeypatch.setattr(
        python_validation, "_download_uv_archive", fake_download
    )
    monkeypatch.setattr(python_validation, "_uv_member_bytes", fake_member)
    monkeypatch.setattr(python_validation, "_run", fake_run)

    with pytest.raises(
        python_validation.ProvisionError, match="short or invalid byte count"
    ):
        _ = python_validation.ensure_uv(tmp_path, platform_id=LINUX_PLATFORM)
    assert not executable.exists()
    assert not temporary.exists()


def test_uv_provisioning_publishes_complete_extracted_binary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exact uv staging write publishes the complete artifact bytes."""
    artifact = python_validation.uv_artifact(LINUX_PLATFORM)
    executable = python_validation.uv_executable(artifact, tmp_path)
    binary = b"synthetic-uv-binary-payload"

    def fake_download(selected_artifact: python_validation.UvArtifact) -> bytes:
        assert selected_artifact == artifact
        return binary

    def fake_member(
        archive_data: bytes, selected_artifact: python_validation.UvArtifact
    ) -> bytes:
        assert archive_data == binary
        assert selected_artifact == artifact
        return binary

    def fake_run(command: list[str]) -> str:
        assert command == [str(executable), "--version"]
        return f"uv {artifact.version}"

    monkeypatch.setattr(
        python_validation, "_download_uv_archive", fake_download
    )
    monkeypatch.setattr(python_validation, "_uv_member_bytes", fake_member)
    monkeypatch.setattr(python_validation, "_run", fake_run)

    provisioned = python_validation.ensure_uv(
        tmp_path, platform_id=LINUX_PLATFORM
    )
    assert provisioned == executable
    assert executable.read_bytes() == binary
    assert not executable.with_name(f"{executable.name}.tmp").exists()


def test_uv_archive_hash_verification_fails_closed() -> None:
    """Standalone uv bytes must match the tracked digest."""
    payload = b"reviewed uv archive"
    digest = hashlib.sha256(payload).hexdigest()
    python_validation.verify_uv_archive(payload, digest)

    with pytest.raises(
        python_validation.ProvisionError,
        match="SHA-256 mismatch",
    ):
        python_validation.verify_uv_archive(b"forged", digest)


def test_uv_download_accepts_native_verified_archive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A normal network response returns the checked native archive bytes."""
    payload = b"verified uv payload"
    artifact = replace(
        python_validation.uv_artifact(LINUX_PLATFORM),
        sha256=hashlib.sha256(payload).hexdigest(),
    )

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int) -> bytes:
            return payload

    def fake_urlopen(*_args: object, **_kwargs: object) -> Response:
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert python_validation._download_uv_archive(artifact) == payload


@pytest.mark.parametrize("oversized", [False, True])
def test_uv_download_bounds_response_body_before_hashing(
    monkeypatch: pytest.MonkeyPatch,
    oversized: bool,
) -> None:
    """A bounded read rejects oversized release data before digest work."""
    bound = 8
    monkeypatch.setattr(python_validation, "MAX_UV_ARCHIVE_BYTES", bound)
    payload = b"largebody" if oversized else b"native"
    artifact = replace(
        python_validation.uv_artifact(LINUX_PLATFORM),
        sha256=hashlib.sha256(payload).hexdigest(),
    )
    requested: list[int] = []

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, size: int) -> bytes:
            requested.append(size)
            return payload[:size]

    def fake_urlopen(*_args: object, **_kwargs: object) -> Response:
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    if oversized:
        with pytest.raises(python_validation.ProvisionError, match="byte limit"):
            _ = python_validation._download_uv_archive(artifact)
    else:
        assert python_validation._download_uv_archive(artifact) == payload
    assert requested == [bound + 1]


class _UvArchiveBytesSubclass(bytes):
    """A bytes lookalike is not native network evidence."""


@pytest.mark.parametrize(
    "archive",
    [
        bytearray(b"uv package"),
        memoryview(b"uv package"),
        _UvArchiveBytesSubclass(b"uv package"),
    ],
)
def test_uv_download_rejects_nonnative_archive_bytes(
    monkeypatch: pytest.MonkeyPatch,
    archive: object,
) -> None:
    """Matching digest alone does not authorize foreign response payloads."""
    artifact = replace(
        python_validation.uv_artifact(LINUX_PLATFORM),
        sha256=hashlib.sha256(b"uv package").hexdigest(),
    )

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int) -> object:
            return archive

    def fake_urlopen(*_args: object, **_kwargs: object) -> Response:
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(python_validation.ProvisionError, match="native bytes"):
        _ = python_validation._download_uv_archive(artifact)


@pytest.mark.parametrize(
    "archive",
    [
        bytearray(b"uv package"),
        memoryview(b"uv package"),
        _UvArchiveBytesSubclass(b"uv package"),
    ],
)
def test_uv_archive_verifier_rejects_nonnative_bytes(archive: object) -> None:
    """Callers cannot bypass native-byte admission by injecting a downloader."""
    digest = hashlib.sha256(b"uv package").hexdigest()
    with pytest.raises(python_validation.ProvisionError, match="native bytes"):
        python_validation.verify_uv_archive(cast("bytes", archive), digest)


class _UvHostError(OSError):
    @override
    def __str__(self) -> str:
        raise AssertionError("host exception formatter must not be evaluated")


@pytest.mark.parametrize(
    "failure",
    [
        _UvHostError("unsafe"),
        ValueError("invalid response"),
        TypeError("malformed response"),
        RuntimeError("response failed"),
    ],
)
def test_uv_download_normalizes_host_faults_without_foreign_formatting(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
) -> None:
    """Network boundary failures retain a typed cause but no foreign message."""
    artifact = python_validation.uv_artifact(LINUX_PLATFORM)

    class Response:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, _size: int) -> bytes:
            raise failure

    def fake_urlopen(*_args: object, **_kwargs: object) -> Response:
        return Response()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(
        python_validation.ProvisionError, match="cannot download pinned uv artifact"
    ) as raised:
        _ = python_validation._download_uv_archive(artifact)
    assert raised.value.__cause__ is failure
    assert type(failure).__name__ in str(raised.value)


@pytest.mark.parametrize("archive_kind", ["zip", "tar"])
@pytest.mark.parametrize("oversized", [False, True])
def test_uv_selected_executable_has_bounded_uncompressed_size(
    monkeypatch: pytest.MonkeyPatch,
    archive_kind: str,
    oversized: bool,
) -> None:
    """An authenticated compressed archive cannot expand without a bound."""
    limit = 8
    monkeypatch.setattr(
        python_validation, "MAX_UV_BINARY_BYTES", limit
    )
    member_name = "uv"
    payload = b"0123456789" if oversized else b"native"
    content = io.BytesIO()
    if archive_kind == "zip":
        with zipfile.ZipFile(content, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr(member_name, payload)
        artifact = replace(
            python_validation.uv_artifact(WINDOWS_PLATFORM),
            member=member_name,
        )
    else:
        with tarfile.open(fileobj=content, mode="w:gz") as t:
            info = tarfile.TarInfo(member_name)
            info.size = len(payload)
            t.addfile(info, io.BytesIO(payload))
        artifact = replace(
            python_validation.uv_artifact(LINUX_PLATFORM),
            member=member_name,
        )
    if oversized:
        with pytest.raises(python_validation.ProvisionError, match="byte limit"):
            _ = python_validation._uv_member_bytes(content.getvalue(), artifact)
    else:
        assert python_validation._uv_member_bytes(content.getvalue(), artifact) == payload


def test_uv_tar_member_rejects_link_to_another_archive_file() -> None:
    """A selected uv executable cannot be a tar member link."""
    archive_bytes = io.BytesIO()
    payload = b"linked-uv-payload"
    with tarfile.open(fileobj=archive_bytes, mode="w:gz") as archive:
        target = tarfile.TarInfo("payload")
        target.size = len(payload)
        archive.addfile(target, io.BytesIO(payload))
        link = tarfile.TarInfo("uv")
        link.type = tarfile.SYMTYPE
        link.linkname = "payload"
        archive.addfile(link)
    artifact = replace(
        python_validation.uv_artifact(LINUX_PLATFORM), member="uv"
    )
    with pytest.raises(python_validation.ProvisionError, match="not a file"):
        _ = python_validation._uv_member_bytes(archive_bytes.getvalue(), artifact)


def test_uv_zip_member_rejects_directory_entry() -> None:
    """A zero-byte zip directory is not an executable payload."""
    archive_bytes = io.BytesIO()
    with zipfile.ZipFile(archive_bytes, "w") as archive:
        archive.writestr("uv/", b"")
    artifact = replace(
        python_validation.uv_artifact(WINDOWS_PLATFORM), member="uv/"
    )
    with pytest.raises(python_validation.ProvisionError, match="regular file"):
        _ = python_validation._uv_member_bytes(archive_bytes.getvalue(), artifact)


def test_uv_member_extraction_does_not_format_host_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Host archive failures keep a typed original cause, not foreign text."""
    failure = _UvHostError("hostile archive format")

    def bad_archive(*_args: object) -> bytes:
        raise failure

    monkeypatch.setattr(python_validation, "_zip_member_bytes", bad_archive)
    artifact = python_validation.uv_artifact(WINDOWS_PLATFORM)
    with pytest.raises(
        python_validation.ProvisionError,
        match="cannot extract pinned uv artifact: _UvHostError",
    ) as caught:
        _ = python_validation._uv_member_bytes(b"fake-zip", artifact)
    assert caught.value.__cause__ is failure


def test_validation_requirements_do_not_install_pip() -> None:
    """The uv-synchronized environment has no pip package requirement."""
    requirements = python_validation.REQUIREMENTS.read_text(encoding="utf-8")
    assert PIP_REQUIREMENT_PREFIX not in requirements
    assert len(requirements.splitlines()) == VALIDATION_REQUIREMENT_COUNT


def test_validation_layout_uses_windows_native_names(tmp_path: Path) -> None:
    """Windows validation paths retain Scripts, EXE, and CMD conventions."""
    layout = python_validation.validation_layout(tmp_path, windows=True)

    assert layout.scripts == layout.environment / "Scripts"
    assert layout.python.name == WINDOWS_PYTHON
    assert layout.python_launcher.name == WINDOWS_PYTHON_LAUNCHER
    assert layout.pytest.name == WINDOWS_PYTEST
    assert layout.pytest_launcher.name == WINDOWS_PYTEST_LAUNCHER
    assert layout.expected_tools == (
        ("basedpyright.exe", "basedpyright 1.40.1"),
        ("pytest.exe", "pytest 9.1.1"),
        ("python-jig.cmd", "Python 3.14.7"),
        ("ruff.exe", "ruff 0.16.9"),
    )


def test_validation_layout_uses_posix_native_names(tmp_path: Path) -> None:
    """POSIX validation paths use bin and extension-free launchers."""
    layout = python_validation.validation_layout(tmp_path, windows=False)

    assert layout.scripts == layout.environment / "bin"
    assert layout.python.name == POSIX_PYTHON
    assert layout.python_launcher.name == POSIX_PYTHON_LAUNCHER
    assert layout.pytest.name == POSIX_PYTEST
    assert layout.pytest_launcher.name == POSIX_PYTEST_LAUNCHER
    assert layout.expected_tools == (
        ("basedpyright", "basedpyright 1.40.1"),
        ("pytest", "pytest 9.1.1"),
        ("python-jig", "Python 3.14.7"),
        ("ruff", "ruff 0.16.9"),
    )


def test_windows_jig_tool_aliases_copy_native_validation_tools(
    tmp_path: Path,
) -> None:
    """Windows Jig aliases retain the provisioned executable bytes."""
    layout = python_validation.validation_layout(tmp_path, windows=True)
    layout.scripts.mkdir(parents=True)
    native = {
        "basedpyright": b"basedpyright-windows",
        "pytest": b"pytest-windows",
        "ruff": b"ruff-windows",
    }
    for name, payload in native.items():
        _ = (layout.scripts / f"{name}.exe").write_bytes(payload)

    aliases = python_validation.write_jig_tool_aliases(layout, windows=True)

    assert tuple(path.name for _, path in aliases) == (
        "basedpyright.bin",
        "pytest.bin",
        "ruff.bin",
    )
    copied = {name: path.read_bytes() for name, path in aliases}
    assert copied == native


def test_posix_jig_tool_aliases_bind_fast_exact_versions(
    tmp_path: Path,
) -> None:
    """POSIX Jig aliases expose exact versions without starting Python tools."""
    layout = python_validation.validation_layout(tmp_path, windows=False)
    layout.scripts.mkdir(parents=True)
    for name in ("basedpyright", "pytest", "ruff"):
        path = layout.scripts / name
        _ = path.write_text(name, encoding="ascii")
        _ = path.chmod(path.stat().st_mode | stat.S_IXUSR)

    aliases = dict(
        python_validation.write_jig_tool_aliases(layout, windows=False)
    )

    assert aliases["ruff"].read_bytes() == RUFF_BYTES
    cases = (
        ("basedpyright", "basedpyright 1.40.1"),
        ("pytest", "pytest 9.1.1"),
    )
    for tool_id, expected in cases:
        # jig-ignore-next-line: reviewed subprocess call needs Ruff policy ID
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [str(aliases[tool_id]), "--version"],
            check=False,
            capture_output=True,
            env={"PATH": ""},
            shell=False,
            text=True,
        )
        assert completed.returncode == os.EX_OK
        assert completed.stdout == f"{expected}\n"
        assert not completed.stderr


def test_posix_jig_tool_aliases_require_unique_version_authority(
    tmp_path: Path,
) -> None:
    """Fast aliases reject missing or duplicate expected-tool authority."""
    layout = python_validation.validation_layout(tmp_path, windows=False)
    layout.scripts.mkdir(parents=True)
    for name in ("basedpyright", "pytest", "ruff"):
        path = layout.scripts / name
        _ = path.write_text(name, encoding="ascii")
        _ = path.chmod(path.stat().st_mode | stat.S_IXUSR)
    without_basedpyright = tuple(
        item for item in layout.expected_tools if item[0] != BASEDPYRIGHT_TOOL
    )
    duplicate_basedpyright = (
        *layout.expected_tools,
        (BASEDPYRIGHT_TOOL, "basedpyright 9.9.9"),
    )

    for expected_tools in (without_basedpyright, duplicate_basedpyright):
        candidate = replace(layout, expected_tools=expected_tools)
        with pytest.raises(
            python_validation.ProvisionError,
            match="requires one version authority: basedpyright",
        ):
            _ = python_validation.write_jig_tool_aliases(
                candidate,
                windows=False,
            )


def test_posix_jig_tool_aliases_delegate_nonexact_version_argv(
    tmp_path: Path,
) -> None:
    """Only the singleton version probe bypasses native Python launchers."""
    layout = python_validation.validation_layout(tmp_path, windows=False)
    layout.scripts.mkdir(parents=True)
    probe = tmp_path / "tool-probe.txt"
    native_probe = """#!/bin/sh
printf "%s\n" "$*" > "$PROBE_OUTPUT"
"""
    _ = layout.python.write_text(native_probe, encoding="ascii")
    _ = layout.python.chmod(layout.python.stat().st_mode | stat.S_IXUSR)
    for name in ("basedpyright", "pytest", "ruff"):
        path = layout.scripts / name
        _ = path.write_text(native_probe, encoding="ascii")
        _ = path.chmod(path.stat().st_mode | stat.S_IXUSR)
    aliases = dict(
        python_validation.write_jig_tool_aliases(layout, windows=False)
    )

    cases = (
        ("basedpyright", "--version --probe"),
        ("pytest", "-m pytest --version --probe"),
    )
    for tool_id, expected_argv in cases:
        # jig-ignore-next-line: reviewed subprocess call needs Ruff policy ID
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [str(aliases[tool_id]), "--version", "--probe"],
            check=False,
            env={"PATH": "", "PROBE_OUTPUT": str(probe)},
            shell=False,
        )
        assert completed.returncode == os.EX_OK
        assert probe.read_text(encoding="utf-8").strip() == expected_argv


def test_posix_jig_pytest_alias_is_cache_bound(tmp_path: Path) -> None:
    """Jig's POSIX pytest alias keeps bytecode under the repository cache."""
    layout = python_validation.validation_layout(tmp_path, windows=False)
    layout.scripts.mkdir(parents=True)
    for name in ("basedpyright", "pytest", "ruff"):
        path = layout.scripts / name
        _ = path.write_text(name, encoding="ascii")
        _ = path.chmod(path.stat().st_mode | stat.S_IXUSR)

    aliases = dict(
        python_validation.write_jig_tool_aliases(layout, windows=False)
    )

    basedpyright_alias = aliases["basedpyright"]
    basedpyright_text = basedpyright_alias.read_text(encoding="ascii")
    assert basedpyright_text.startswith(POSIX_HEADER)
    assert CACHE_VARIABLE not in basedpyright_text
    assert POSIX_JIG_BASEDPYRIGHT_EXEC in basedpyright_text
    assert basedpyright_alias.stat().st_mode & stat.S_IXUSR

    pytest_alias = aliases["pytest"]
    pytest_text = pytest_alias.read_text(encoding="ascii")
    assert pytest_text.startswith(POSIX_HEADER)
    assert CACHE_VARIABLE in pytest_text
    assert POSIX_JIG_PYTEST_EXEC in pytest_text
    assert pytest_alias.stat().st_mode & stat.S_IXUSR


def test_posix_jig_pytest_alias_needs_no_ambient_path(tmp_path: Path) -> None:
    """Jig's pytest wrapper runs with only shell builtins on hermetic PATH."""
    layout = python_validation.validation_layout(tmp_path, windows=False)
    layout.scripts.mkdir(parents=True)
    probe = tmp_path / "pytest-probe.txt"
    probe_script = """#!/bin/sh
printf "%s\n" "$PYTHONPYCACHEPREFIX" > "$PROBE_OUTPUT"
printf "%s\n" "$*" >> "$PROBE_OUTPUT"
"""
    _ = layout.python.write_text(probe_script, encoding="ascii")
    _ = layout.python.chmod(layout.python.stat().st_mode | stat.S_IXUSR)
    for name in ("basedpyright", "pytest", "ruff"):
        path = layout.scripts / name
        _ = path.write_text(name, encoding="ascii")
        _ = path.chmod(path.stat().st_mode | stat.S_IXUSR)
    aliases = dict(
        python_validation.write_jig_tool_aliases(layout, windows=False)
    )

    pytest_alias = aliases["pytest"]
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(pytest_alias), "--probe"],
        check=False,
        env={"PATH": "", "PROBE_OUTPUT": str(probe)},
    )

    assert completed.returncode == os.EX_OK
    cache, argv = probe.read_text(encoding="utf-8").splitlines()
    assert os.path.realpath(cache) == str(tmp_path / ".cache/python/pycache")
    assert argv == POSIX_JIG_PYTEST_PROBE_ARGV


def test_posix_launchers_need_no_ambient_path(tmp_path: Path) -> None:
    """POSIX Python launchers resolve themselves with shell builtins only."""
    layout = python_validation.validation_layout(tmp_path, windows=False)
    layout.scripts.mkdir(parents=True)
    probe = tmp_path / "launcher-probe.txt"
    probe_script = """#!/bin/sh
printf "%s\n" "$PYTHONPYCACHEPREFIX" > "$PROBE_OUTPUT"
printf "%s\n" "$*" >> "$PROBE_OUTPUT"
"""
    _ = layout.python.write_text(probe_script, encoding="ascii")
    _ = layout.python.chmod(layout.python.stat().st_mode | stat.S_IXUSR)
    python_validation.write_launchers(layout, windows=False)

    cases = (
        (layout.python_launcher, "--probe"),
        (layout.pytest_launcher, "-m pytest --probe"),
    )
    for launcher, expected_argv in cases:
        # jig-ignore-next-line: reviewed subprocess call needs Ruff policy ID
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [str(launcher), "--probe"],
            check=False,
            env={"PATH": "", "PROBE_OUTPUT": str(probe)},
            shell=False,
        )

        assert completed.returncode == os.EX_OK
        cache, argv = probe.read_text(encoding="utf-8").splitlines()
        expected_cache = tmp_path / ".cache/python/pycache"
        assert os.path.realpath(cache) == str(expected_cache)
        assert argv == expected_argv


def test_posix_launchers_are_executable_and_cache_bound(tmp_path: Path) -> None:
    """POSIX launchers use the local interpreter and repository cache."""
    layout = python_validation.validation_layout(tmp_path, windows=False)
    layout.scripts.mkdir(parents=True)

    python_validation.write_launchers(layout, windows=False)

    python_text = layout.python_launcher.read_text(encoding="ascii")
    pytest_text = layout.pytest_launcher.read_text(encoding="ascii")
    assert python_text.startswith(POSIX_HEADER)
    assert CACHE_VARIABLE in python_text
    assert POSIX_PYTHON_EXEC in python_text
    assert POSIX_PYTEST_EXEC in pytest_text
    if os.name != python_validation.WINDOWS_OS_NAME:
        assert layout.python_launcher.stat().st_mode & stat.S_IXUSR
        assert layout.pytest_launcher.stat().st_mode & stat.S_IXUSR


def test_platform_identity_normalizes_windows_and_linux() -> None:
    """Host names normalize to manifest-compatible OS/architecture IDs."""
    assert (
        project.host_platform_id(system="Windows", machine="AMD64")
        == WINDOWS_PLATFORM
    )
    assert (
        project.host_platform_id(system="Linux", machine="x86_64")
        == LINUX_PLATFORM
    )
    assert (
        project.host_platform_id(system="Linux", machine="arm64")
        == LINUX_AARCH64
    )


@pytest.mark.parametrize(
    "system,machine",
    [
        ("Windows\n", "AMD64"),
        ("Windows", "AMD64\r"),
        (" Linux", "x86_64"),
        ("Linux", "x86_64 "),
        ("Windows\t", "AMD64"),
    ],
)
def test_platform_identity_rejects_whitespace_host_aliases(
    system: str, machine: str
) -> None:
    """A malformed host receipt cannot select supported native packages."""
    assert project.host_platform_id(system=system, machine=machine) not in {
        WINDOWS_PLATFORM,
        LINUX_PLATFORM,
        LINUX_AARCH64,
    }


def test_platform_identity_rejects_foreign_host_string_hooks() -> None:
    """Host identity discovery cannot invoke foreign string normalizers."""

    class HostString(str):
        @override
        def strip(self, chars: str | None = None) -> Never:
            raise AssertionError("foreign platform identity normalizer invoked")

    observed = project.host_platform_id(
        system=HostString("Windows"), machine="AMD64"
    )
    assert observed not in {WINDOWS_PLATFORM, LINUX_PLATFORM}


def _linux_llvm_observation(
    tmp_path: Path,
) -> llvm_validation.LlvmHostObservation:
    host = tmp_path / "host-llvm"
    bin_dir = host / "bin"
    lib_dir = host / "lib"
    resource_dir = host / "resource"
    bin_dir.mkdir(parents=True)
    lib_dir.mkdir()
    resource_dir.mkdir()
    paths = {
        "clang": bin_dir / "clang",
        "clang_tidy": bin_dir / "clang-tidy",
        "clang_format": bin_dir / "clang-format",
        "llvm": lib_dir / "libLLVM.so.22.1",
        "clang_cpp": lib_dir / "libclang-cpp.so.22.1",
    }
    for path in paths.values():
        path.touch()
    (resource_dir / "stddef.h").touch()
    return llvm_validation.LlvmHostObservation(
        clang=paths["clang"],
        clang_format=paths["clang_format"],
        clang_tidy=paths["clang_tidy"],
        clang_cpp=paths["clang_cpp"],
        llvm=paths["llvm"],
        resource_dir=resource_dir,
        version=llvm_validation.LLVM_VERSION,
    )


def test_linux_llvm_preparation_imports_exact_host_observation(
    tmp_path: Path,
) -> None:
    """Project bootstrap promotes an exact observed Linux LLVM to ready."""
    observation = _linux_llvm_observation(tmp_path)

    status = project.prepare_llvm(
        tmp_path,
        LINUX_PLATFORM,
        linux_observer=lambda: observation,
    )

    assert status.state is project.ComponentState.READY
    assert status.path == (
        tmp_path / llvm_validation.LLVM_ROOT / "jig-bin/clang.bin"
    )


def _recording_llvm_development_provisioner(
    calls: list[Path],
) -> Callable[[Path], Path]:
    def provision(root: Path) -> Path:
        calls.append(root)
        return root / ".dependencies/llvm-dev/22.1.8"

    return provision


def test_llvm_development_provisioning_is_disabled_by_default(
    tmp_path: Path,
) -> None:
    """Ordinary bootstrap never invokes the LLVM development downloader."""
    calls: list[Path] = []

    result = project.provision_llvm_development_if_requested(
        tmp_path,
        LINUX_PLATFORM,
        requested=False,
        provisioner=_recording_llvm_development_provisioner(calls),
    )

    assert result is None
    assert calls == []


def test_explicit_linux_llvm_development_provisioning_is_selected(
    tmp_path: Path,
) -> None:
    """Explicit Linux opt-in invokes only the exact development provisioner."""
    calls: list[Path] = []

    result = project.provision_llvm_development_if_requested(
        tmp_path,
        LINUX_PLATFORM,
        requested=True,
        provisioner=_recording_llvm_development_provisioner(calls),
    )

    assert result == tmp_path / ".dependencies/llvm-dev/22.1.8"
    assert calls == [tmp_path]


def test_explicit_llvm_development_provisioning_rejects_other_platforms(
    tmp_path: Path,
) -> None:
    """Fedora development packages are never applied to another platform."""
    calls: list[Path] = []
    with pytest.raises(
        project.InitializationError,
        match="LLVM development provisioning supports only linux-x86_64",
    ):
        _ = project.provision_llvm_development_if_requested(
            tmp_path,
            WINDOWS_PLATFORM,
            requested=True,
            provisioner=_recording_llvm_development_provisioner(calls),
        )
    assert calls == []


@pytest.mark.parametrize("component", ["llvm", "llvm-dev", "cuda"])
def test_optional_project_tool_failure_does_not_format_foreign_exception(
    tmp_path: Path, component: str
) -> None:
    """A typed component failure retains native details without host hooks."""

    class NoHostFormatting:
        def __str__(self) -> Never:
            raise AssertionError("host error formatter was invoked")

    class ForeignLlvmImport(NoHostFormatting, llvm_validation.LlvmImportError):
        pass

    class ForeignLlvmDevelopment(
        NoHostFormatting, llvm_development_validation.LlvmDevelopmentProvisionError
    ):
        pass

    class ForeignCudaProvision(NoHostFormatting, cuda_validation.CudaProvisionError):
        pass

    if component == "llvm":
        fault = ForeignLlvmImport("pinned LLVM host unavailable")

        def failing_observer() -> Never:
            raise fault

        status = project.prepare_llvm(
            tmp_path, LINUX_PLATFORM, linux_observer=failing_observer
        )
        assert status.state is project.ComponentState.MISSING
        assert "pinned LLVM host unavailable" in status.detail
        return

    if component == "llvm-dev":
        fault = ForeignLlvmDevelopment("pinned LLVM dev unavailable")

        def failing_development(_root: Path) -> Never:
            raise fault

        with pytest.raises(
            project.InitializationError, match="pinned LLVM dev unavailable"
        ) as caught:
            project.provision_llvm_development_if_requested(
                tmp_path, LINUX_PLATFORM, requested=True,
                provisioner=failing_development,
            )
    else:
        fault = ForeignCudaProvision("pinned CUDA unavailable")
        _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)

        def failing_cuda(_root: Path, _manifest: Path, _platform: str) -> Never:
            raise fault

        with pytest.raises(
            project.InitializationError, match="pinned CUDA unavailable"
        ) as caught:
            project.provision_cuda_if_requested(
                tmp_path, LINUX_PLATFORM, requested=True, provisioner=failing_cuda
            )
    assert caught.value.__cause__ is fault


def test_native_exception_detail_ignores_foreign_attribute_hooks() -> None:
    """Error reporting uses native arguments, not foreign getters or text."""

    class ForeignHostOSError(OSError):
        @override
        def __getattribute__(self, name: str) -> object:
            if name == "args":
                raise AssertionError("foreign exception args getter was invoked")
            return super().__getattribute__(name)

        @override
        def __str__(self) -> Never:
            raise AssertionError("foreign exception formatter was invoked")

    safe = ForeignHostOSError("stable native message")
    opaque = ForeignHostOSError({"not": "native text"})
    assert (
        project._native_exception_detail(safe)  # pyright: ignore[reportPrivateUsage]
        == "stable native message"
    )
    assert (
        project._native_exception_detail(opaque)  # pyright: ignore[reportPrivateUsage]
        == "ForeignHostOSError"
    )


@pytest.mark.parametrize("native_args", [(), ({"not": "text"},)])
def test_native_exception_detail_bypasses_hostile_metaclass_name_hook(
    native_args: tuple[object, ...],
) -> None:
    """Fallback class names must not dispatch foreign metaclass getters."""

    class HostileErrorMeta(type):
        def __getattribute__(cls, name: str) -> object:
            if name == "__name__":
                raise AssertionError("foreign metaclass name getter was invoked")
            return super().__getattribute__(name)

    class HostFailure(OSError, metaclass=HostileErrorMeta):
        @override
        def __str__(self) -> Never:
            raise AssertionError("foreign host error formatter was invoked")

    fault = HostFailure(*native_args)
    assert (
        project._native_exception_detail(fault)  # pyright: ignore[reportPrivateUsage]
        == "HostFailure"
    )


def test_initialize_project_provisions_python_at_requested_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Project bootstrap must not provision the default checkout for another root."""
    observed: list[Path] = []

    def admit_repository(_root: Path) -> None:
        pass

    def capture_python_root(root: Path) -> Never:
        observed.append(root)
        raise project.InitializationError("captured requested Python root")

    monkeypatch.setattr(project, "validate_repository", admit_repository)
    monkeypatch.setattr(python_validation, "initialize", capture_python_root)
    with pytest.raises(project.InitializationError, match="captured requested Python root"):
        _ = project.initialize_project(tmp_path)
    assert observed == [tmp_path]


def test_initialize_project_pins_relative_root_across_callbacks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A downloader changing cwd cannot redirect subsequent checkout work."""
    selected = tmp_path / "selected"
    other = tmp_path / "other"
    selected.mkdir()
    other.mkdir()
    monkeypatch.chdir(tmp_path)
    observed: list[Path] = []

    def admit_repository(root: Path) -> None:
        observed.append(root)

    def change_directory(root: Path) -> tuple[Path, ...]:
        observed.append(root)
        monkeypatch.chdir(other)
        return ()

    def capture_layout(root: Path) -> Never:
        observed.append(root)
        raise project.InitializationError("captured canonical checkout root")

    monkeypatch.setattr(project, "validate_repository", admit_repository)
    monkeypatch.setattr(project, "initialize_local_directories", change_directory)
    monkeypatch.setattr(python_validation, "validation_layout", capture_layout)
    with pytest.raises(project.InitializationError, match="captured canonical"):
        _ = project.initialize_project(Path("selected"), provision_python=False)
    assert observed == [selected, selected, selected]


@pytest.mark.parametrize("provision_python", [True, False])
def test_project_report_distinguishes_verified_and_skipped_python(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provision_python: bool,
) -> None:
    """--skip-python reports an unchecked path, never a ready environment."""
    observed: list[Path] = []
    layout = python_validation.validation_layout(tmp_path)
    optional = project.ComponentStatus(
        detail="not installed",
        name="optional",
        path=None,
        state=project.ComponentState.MISSING,
    )

    def provision(root: Path) -> python_validation.ValidationEnvironmentLayout:
        observed.append(root)
        return layout

    def noop_root(_root: Path) -> None:
        pass

    def empty_directories(_root: Path) -> tuple[Path, ...]:
        return ()

    def layout_for_root(_root: Path) -> python_validation.ValidationEnvironmentLayout:
        return layout

    def local_platform() -> str:
        return LINUX_PLATFORM

    def no_optional(*_args: object, **_kwargs: object) -> None:
        pass

    def no_host_git(_platform: str) -> None:
        pass

    def no_rust(_root: Path, _platform: str) -> tuple[Path, ...]:
        return ()

    def missing(*_args: object, **_kwargs: object) -> project.ComponentStatus:
        return optional

    monkeypatch.setattr(project, "validate_repository", noop_root)
    monkeypatch.setattr(project, "initialize_local_directories", empty_directories)
    monkeypatch.setattr(python_validation, "initialize", provision)
    monkeypatch.setattr(python_validation, "validation_layout", layout_for_root)
    monkeypatch.setattr(project, "host_platform_id", local_platform)
    monkeypatch.setattr(project, "provision_llvm_development_if_requested", no_optional)
    monkeypatch.setattr(project, "provision_cuda_if_requested", no_optional)
    monkeypatch.setattr(project, "observe_host_git", no_host_git)
    monkeypatch.setattr(project, "import_host_rust_toolchains", no_rust)
    for method in (
        "inspect_cuda",
        "inspect_rust",
        "inspect_jig",
        "prepare_llvm",
        "inspect_llvm_development",
    ):
        monkeypatch.setattr(project, method, missing)

    report = project.initialize_project(tmp_path, provision_python=provision_python)
    assert report.python_provisioned is provision_python
    assert observed == ([tmp_path] if provision_python else [])
    python_line = project.render_report(report).splitlines()[1]
    if provision_python:
        assert python_line == f"python: ready ({layout.environment})"
    else:
        assert python_line == (
            f"python: skipped (--skip-python; not verified) ({layout.environment})"
        )


def test_python_initializer_routes_layout_to_requested_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Python environment creation and readiness use the requested checkout."""
    created: list[python_validation.ValidationEnvironmentLayout] = []
    verified: list[python_validation.ValidationEnvironmentLayout] = []

    def provision(layout: python_validation.ValidationEnvironmentLayout, *, root: Path) -> None:
        assert root == tmp_path
        created.append(layout)

    def verify(layout: python_validation.ValidationEnvironmentLayout) -> None:
        verified.append(layout)

    monkeypatch.setattr(python_validation, "_check_host_python", lambda: None)
    monkeypatch.setattr(python_validation, "_provision", provision)
    monkeypatch.setattr(python_validation, "_verify", verify)
    result = python_validation.initialize(tmp_path)
    expected = python_validation.validation_layout(tmp_path)
    assert result == expected
    assert created == [expected]
    assert verified == [expected]
    assert result.environment.is_relative_to(tmp_path)


def test_python_provisioner_selects_uv_for_requested_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The uv executable is selected from the same checkout as its venv."""
    observed: list[Path] = []

    def capture_uv(root: Path) -> Never:
        observed.append(root)
        raise python_validation.ProvisionError("captured uv root")

    monkeypatch.setattr(python_validation, "ensure_uv", capture_uv)
    layout = python_validation.validation_layout(tmp_path)
    with pytest.raises(python_validation.ProvisionError, match="captured uv root"):
        python_validation._provision(  # pyright: ignore[reportPrivateUsage]
            layout, root=tmp_path
        )
    assert observed == [tmp_path]


def test_bootstrap_cli_does_not_format_foreign_host_exception(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Bootstrap prints an error without evaluating host-defined __str__."""

    class ForeignHostOSError(OSError):
        @override
        def __str__(self) -> Never:
            raise AssertionError("foreign host error formatter was invoked")

    fault = ForeignHostOSError("physical host filesystem failure")

    def failing_initialize(**_kwargs: object) -> Never:
        raise fault

    monkeypatch.setattr(project, "initialize_project", failing_initialize)
    assert project.main(["--skip-python"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: physical host filesystem failure\n"


def test_bootstrap_cli_ignores_hostile_exception_metaclass(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Opaque host faults produce a native class-name diagnostic."""

    class HostileErrorMeta(type):
        def __getattribute__(cls, name: str) -> object:
            if name == "__name__":
                raise AssertionError("foreign metaclass name getter was invoked")
            return super().__getattribute__(name)

    class HostFailure(OSError, metaclass=HostileErrorMeta):
        pass

    fault = HostFailure({"opaque": True})

    def failing_initialize(**_kwargs: object) -> Never:
        raise fault

    monkeypatch.setattr(project, "initialize_project", failing_initialize)
    assert project.main(["--skip-python"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: HostFailure\n"


@pytest.mark.parametrize("receipt", [0, False, None, -1, 1_000_000])
def test_bootstrap_cli_requires_complete_native_stdout_receipt(
    monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """Truncated or forged report writes must never exit as successful."""
    body = "bootstrap ready\n"
    writes: list[str] = []
    errors: list[str] = []

    class Output:
        def write(self, data: str) -> int:
            writes.append(data)
            return cast("int", receipt)

        def flush(self) -> None:
            pass

    class ErrorOutput:
        def write(self, data: str) -> int:
            errors.append(data)
            return len(data)

    def initialize(**_kwargs: object) -> project.ProjectInitializationReport:
        return cast("project.ProjectInitializationReport", object())

    def render(_report: project.ProjectInitializationReport) -> str:
        return body

    with monkeypatch.context() as isolated:
        isolated.setattr(project, "initialize_project", initialize)
        isolated.setattr(project, "render_report", render)
        isolated.setattr(project.sys, "stdout", cast("TextIO", cast("object", Output())))
        isolated.setattr(project.sys, "stderr", cast("TextIO", cast("object", ErrorOutput())))
        status = project.main(["--skip-python"])
    assert status == 1
    assert writes == [body]
    assert errors == ["error: incomplete bootstrap report output\n"]


@pytest.mark.parametrize("fault_site", ["write", "flush"])
def test_bootstrap_cli_fails_on_report_delivery_host_fault(
    monkeypatch: pytest.MonkeyPatch, fault_site: str
) -> None:
    """A hostile report delivery fault must return nonzero without formatting."""

    class ForeignHostOSError(OSError):
        @override
        def __str__(self) -> Never:
            raise AssertionError("host output fault formatter invoked")

    fault = ForeignHostOSError("host report output failed")
    errors: list[str] = []

    class Output:
        def write(self, data: str) -> int:
            if fault_site == "write":
                raise fault
            return len(data)

        def flush(self) -> None:
            if fault_site == "flush":
                raise fault

    class ErrorOutput:
        def write(self, data: str) -> int:
            errors.append(data)
            return len(data)

    def initialize(**_kwargs: object) -> project.ProjectInitializationReport:
        return cast("project.ProjectInitializationReport", object())

    with monkeypatch.context() as isolated:
        isolated.setattr(project, "initialize_project", initialize)
        isolated.setattr(project, "render_report", lambda _report: "ready\n")
        isolated.setattr(project.sys, "stdout", cast("TextIO", cast("object", Output())))
        isolated.setattr(project.sys, "stderr", cast("TextIO", cast("object", ErrorOutput())))
        status = project.main(["--skip-python"])
    assert status == 1
    assert errors == ["error: cannot write bootstrap report\n"]


def test_bootstrap_cli_flushes_complete_native_stdout_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A complete native report write is flushed and returns success."""
    body = "complete bootstrap report\n"
    writes: list[str] = []
    flushes: list[bool] = []

    class Output:
        def write(self, data: str) -> int:
            writes.append(data)
            return len(data)

        def flush(self) -> None:
            flushes.append(True)

    def initialize(**_kwargs: object) -> project.ProjectInitializationReport:
        return cast("project.ProjectInitializationReport", object())

    with monkeypatch.context() as isolated:
        isolated.setattr(project, "initialize_project", initialize)
        isolated.setattr(project, "render_report", lambda _report: body)
        isolated.setattr(project.sys, "stdout", cast("TextIO", cast("object", Output())))
        status = project.main(["--skip-python"])
    assert status == 0
    assert writes == [body]
    assert flushes == [True]


def test_llvm_development_inspection_reports_exact_marker_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Development readiness is separate from the neutral LLVM runtime."""
    states = iter((False, True))

    def next_state(root: Path) -> bool:
        del root
        return next(states)

    monkeypatch.setattr(
        llvm_development_validation,
        "linux_development_ready",
        next_state,
    )

    missing = project.inspect_llvm_development(tmp_path, LINUX_PLATFORM)
    ready = project.inspect_llvm_development(tmp_path, LINUX_PLATFORM)

    assert missing.state is project.ComponentState.MISSING
    assert ready.state is project.ComponentState.READY
    assert ready.name == LLVM_DEVELOPMENT_COMPONENT


def test_bootstrap_arguments_expose_explicit_llvm_development_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The command-line opt-in is independent from ordinary initialization."""
    observed: dict[str, object] = {}

    def reject_after_capture(
        **keywords: object,
    ) -> project.ProjectInitializationReport:
        observed.update(keywords)
        raise project.InitializationError(CAPTURED_BOOTSTRAP_ARGUMENTS)

    monkeypatch.setattr(project, "initialize_project", reject_after_capture)

    status = project.main(["--skip-python", "--provision-llvm-development"])

    assert status == 1
    assert observed["provision_python"] is False
    provisions = cast("project.ProvisionRequests", observed["provisions"])
    assert provisions.cuda is False
    assert provisions.llvm_development is True


def test_cuda_manifest_index_selects_linux_without_rewriting_windows(
    tmp_path: Path,
) -> None:
    """Platform selection preserves retained Windows manifest identity."""
    manifest_root = (tmp_path / project.CUDA_TOOLCHAIN_MANIFEST).parent
    manifest_root.mkdir(parents=True)
    windows = _write_platform_cuda_manifest(
        tmp_path, WINDOWS_PLATFORM, "toolchain.json"
    )
    linux = _write_platform_cuda_manifest(
        tmp_path, LINUX_PLATFORM, CUDA_LINUX_MANIFEST
    )
    _ = _write_cuda_manifest_index(tmp_path)

    assert (
        project.cuda_toolchain_manifest_path(tmp_path, WINDOWS_PLATFORM)
        == windows
    )
    assert (
        project.cuda_toolchain_manifest_path(tmp_path, LINUX_PLATFORM) == linux
    )


def test_repository_windows_cuda_manifest_sha_is_retained() -> None:
    """Linux enablement never rewrites retained Windows CUDA identity bytes."""
    payload = (project.ROOT / project.CUDA_TOOLCHAIN_MANIFEST).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == CUDA_WINDOWS_MANIFEST_SHA256


def test_cuda_inspection_selects_linux_manifest_and_bundle(
    tmp_path: Path,
) -> None:
    """Fedora readiness follows the indexed Linux manifest toolkit root."""
    manifest_root = (tmp_path / project.CUDA_TOOLCHAIN_MANIFEST).parent
    manifest_root.mkdir(parents=True)
    _ = _write_platform_cuda_manifest(
        tmp_path, WINDOWS_PLATFORM, "toolchain.json"
    )
    linux = _write_platform_cuda_manifest(
        tmp_path, LINUX_PLATFORM, CUDA_LINUX_MANIFEST
    )
    _ = _write_cuda_manifest_index(tmp_path)
    toolkit = tmp_path / CUDA_VERSION_ROOT
    toolkit.mkdir(parents=True)
    missing_runtime = project.inspect_cuda(tmp_path, LINUX_PLATFORM)
    nvrtc = toolkit / "lib/libnvrtc.so.13"
    nvrtc.parent.mkdir(parents=True)
    nvrtc.touch()
    ready = project.inspect_cuda(tmp_path, LINUX_PLATFORM)

    assert linux.is_file()
    assert missing_runtime.state is project.ComponentState.MISSING
    assert CUDA_NVRTC_LABEL in missing_runtime.detail
    assert ready.state is project.ComponentState.READY
    assert ready.path == toolkit


@pytest.mark.parametrize("redirect", ["toolkit", "parent"])
def test_cuda_inspection_rejects_redirected_toolkit_root(
    tmp_path: Path, redirect: str
) -> None:
    """An external directory cannot impersonate a hermetic CUDA bundle."""
    _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    toolkit = tmp_path / CUDA_VERSION_ROOT
    outside = tmp_path / "outside-toolkit"
    outside.mkdir()
    if redirect == "toolkit":
        toolkit.parent.mkdir(parents=True)
        _ = toolkit.symlink_to(outside, target_is_directory=True)
    else:
        _ = (outside / "toolkit").mkdir()
        parent = toolkit.parent
        parent.parent.mkdir(parents=True)
        _ = parent.symlink_to(outside, target_is_directory=True)
    with pytest.raises(project.InitializationError, match="CUDA toolkit"):
        _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)


@pytest.mark.parametrize("redirect", ["library", "lib-directory"])
def test_cuda_inspection_rejects_nvrtc_external_redirect(
    tmp_path: Path, redirect: str
) -> None:
    """A CUDA NVRTC alias outside the package cannot certify readiness."""
    _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    _ = _write_platform_cuda_manifest(
        tmp_path, LINUX_PLATFORM, CUDA_LINUX_MANIFEST
    )
    _ = _write_cuda_manifest_index(tmp_path)
    toolkit = tmp_path / CUDA_VERSION_ROOT
    toolkit.mkdir(parents=True)
    nvrtc = toolkit / "lib/libnvrtc.so.13"
    external = tmp_path / "external-lib"
    external.mkdir()
    _ = (external / "libnvrtc.so.13").write_bytes(b"foreign-library")
    if redirect == "library":
        nvrtc.parent.mkdir()
        _ = nvrtc.symlink_to(external / nvrtc.name)
    else:
        _ = nvrtc.parent.symlink_to(external, target_is_directory=True)
    status = project.inspect_cuda(tmp_path, LINUX_PLATFORM)
    assert status.state is project.ComponentState.MISSING


def test_cuda_inspection_admits_internal_nvrtc_symlink(tmp_path: Path) -> None:
    """NVRTC internal versioned library aliases remain supported."""
    _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    _ = _write_platform_cuda_manifest(
        tmp_path, LINUX_PLATFORM, CUDA_LINUX_MANIFEST
    )
    _ = _write_cuda_manifest_index(tmp_path)
    toolkit = tmp_path / CUDA_VERSION_ROOT
    nvrtc = toolkit / "lib/libnvrtc.so.13"
    nvrtc.parent.mkdir(parents=True)
    _ = (nvrtc.parent / "libnvrtc.so.13.3").write_bytes(b"internal-library")
    _ = nvrtc.symlink_to("libnvrtc.so.13.3")
    assert (
        project.inspect_cuda(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.READY
    )


def test_cuda_inspection_requires_matching_platform_and_bundle(
    tmp_path: Path,
) -> None:
    """A matching manifest is ready only after its exact toolkit root exists."""
    _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    missing = project.inspect_cuda(tmp_path, LINUX_PLATFORM)
    toolkit = tmp_path / CUDA_VERSION_ROOT
    toolkit.mkdir(parents=True)
    ready = project.inspect_cuda(tmp_path, LINUX_PLATFORM)

    assert missing.state is project.ComponentState.MISSING
    assert missing.path == toolkit
    assert ready.state is project.ComponentState.READY
    assert ready.path == toolkit


def test_cuda_inspection_uses_tracked_manifest_path(tmp_path: Path) -> None:
    """CUDA inspection reads the manifest from its tracked source boundary."""
    manifest = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    status = project.inspect_cuda(tmp_path, LINUX_PLATFORM)
    assert manifest == tmp_path / project.CUDA_TOOLCHAIN_MANIFEST
    assert status.state is project.ComponentState.MISSING
    assert status.path == tmp_path / CUDA_VERSION_ROOT


@pytest.mark.parametrize(
    "authority",
    [project.CUDA_TOOLCHAIN_MANIFEST, project.CUDA_TOOLCHAIN_INDEX],
)
def test_bootstrap_cuda_authority_rejects_linked_leaf(
    tmp_path: Path,
    authority: Path,
) -> None:
    """CUDA bootstrap cannot trust a redirect to otherwise valid JSON."""
    _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    if authority == project.CUDA_TOOLCHAIN_INDEX:
        _ = _write_cuda_manifest_index(tmp_path)
    selected = tmp_path / authority
    original = selected.with_suffix(".original")
    _ = selected.replace(original)
    _ = selected.symlink_to(original)
    with pytest.raises(project.InitializationError, match=r"redirect|regular"):
        _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)


def test_bootstrap_cuda_authority_rejects_linked_parent(
    tmp_path: Path,
) -> None:
    """An in-root symlinked ancestor cannot select pinned CUDA metadata."""
    _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    _ = _write_cuda_manifest_index(tmp_path)
    manifest_root = (tmp_path / project.CUDA_TOOLCHAIN_INDEX).parent
    relocated = tmp_path / "real-manifests"
    _ = manifest_root.replace(relocated)
    _ = manifest_root.symlink_to(relocated, target_is_directory=True)
    with pytest.raises(project.InitializationError, match="redirect"):
        _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)


@pytest.mark.parametrize("authority", ["rust", "cuda"])
@pytest.mark.parametrize("masked", [False, 0])
def test_bootstrap_authority_rejects_masked_linked_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    authority: str,
    masked: object,
) -> None:
    """A linked directory is not native authority despite a masked predicate."""
    if authority == "rust":
        source = _write_rust_manifest(tmp_path)
        inspect = lambda: project.inspect_rust(tmp_path, WINDOWS_PLATFORM)
    else:
        source = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
        inspect = lambda: project.inspect_cuda(tmp_path, LINUX_PLATFORM)
    parent = source.parent
    relocated = tmp_path / "real-authority-directory"
    _ = parent.replace(relocated)
    _ = parent.symlink_to(relocated, target_is_directory=True)
    native = Path.is_symlink

    def masked_status(path: Path) -> bool:
        if path == parent:
            return cast("bool", masked)
        return native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "is_symlink", masked_status)
        with pytest.raises(project.InitializationError, match="redirect"):
            _ = inspect()


@pytest.mark.parametrize("authority", ["rust", "cuda"])
def test_bootstrap_authority_rejects_foreign_parent_lstat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    authority: str,
) -> None:
    """Foreign parent metadata cannot certify physical authority ancestry."""
    if authority == "rust":
        source = _write_rust_manifest(tmp_path)
        inspect = lambda: project.inspect_rust(tmp_path, WINDOWS_PLATFORM)
    else:
        source = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
        inspect = lambda: project.inspect_cuda(tmp_path, LINUX_PLATFORM)
    parent = source.parent
    native = Path.lstat

    class ForeignStat:
        def __init__(self, status: os.stat_result) -> None:
            self.status: os.stat_result = status

        def __getattr__(self, name: str) -> object:
            return cast("object", getattr(self.status, name))

    def fake_lstat(path: Path) -> os.stat_result:
        status = native(path)
        if path == parent:
            return cast("os.stat_result", cast("object", ForeignStat(status)))
        return status

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", fake_lstat)
        with pytest.raises(project.InitializationError, match="native|redirect"):
            _ = inspect()


@pytest.mark.parametrize("authority", ["rust", "cuda-manifest", "cuda-index", "git"])
def test_bootstrap_authority_rejects_external_hardlink(
    tmp_path: Path, authority: str
) -> None:
    """Authority metadata cannot be shared with an unrelated host inode alias."""
    if authority == "rust":
        selected = _write_rust_manifest(tmp_path)
    elif authority == "git":
        selected = tmp_path / ".jig/settings/versions.toml"
        selected.parent.mkdir(parents=True)
        _ = selected.write_text(
            '[authority.git]\ncurrent = "2.55.0"\n', encoding="ascii"
        )
    else:
        selected = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
        if authority == "cuda-index":
            selected = _write_cuda_manifest_index(tmp_path)

    def inspect() -> object:
        if authority == "rust":
            return project.inspect_rust(tmp_path, WINDOWS_PLATFORM)
        if authority == "git":
            return project._configured_git_version(  # pyright: ignore[reportPrivateUsage]
                tmp_path
            )
        return project.inspect_cuda(tmp_path, LINUX_PLATFORM)

    outside = tmp_path / "foreign-hardlink"
    try:
        os.link(selected, outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hardlinks unavailable: {error}")
    with pytest.raises(project.InitializationError, match="single-link|hardlink"):
        _ = inspect()
    assert outside.read_bytes() == selected.read_bytes()


def test_bootstrap_authority_rejects_hardlink_added_after_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A link-count increase during the read invalidates the pinned snapshot."""
    selected = _write_rust_manifest(tmp_path)
    outside = tmp_path / "late-hardlink"
    native_fstat = os.fstat
    observed = 0

    def add_link_before_final_fstat(descriptor: int) -> os.stat_result:
        nonlocal observed
        current = native_fstat(descriptor)
        if current.st_ino == selected.stat().st_ino:
            observed += 1
            if observed == 2:
                os.link(selected, outside)
                current = native_fstat(descriptor)
        return current

    monkeypatch.setattr(os, "fstat", add_link_before_final_fstat)
    with pytest.raises(project.InitializationError, match="single-link|hardlink"):
        _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)
    assert observed >= 2
    assert outside.read_bytes() == selected.read_bytes()


def test_bootstrap_rust_authority_rejects_linked_leaf(tmp_path: Path) -> None:
    """Rust toolchain version cannot be borrowed through an alias."""
    original = _write_rust_manifest(tmp_path)
    relocated = original.with_suffix(".original")
    _ = original.replace(relocated)
    _ = original.symlink_to(relocated)
    with pytest.raises(project.InitializationError, match=r"redirect|regular"):
        _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)


@pytest.mark.parametrize(
    "authority",
    [project.CUDA_TOOLCHAIN_MANIFEST, project.CUDA_TOOLCHAIN_INDEX],
)
def test_bootstrap_cuda_authority_rejects_oversized_json(
    tmp_path: Path,
    authority: Path,
) -> None:
    """Manifest and index sizes are bounded before JSON decoding."""
    _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    if authority == project.CUDA_TOOLCHAIN_INDEX:
        _ = _write_cuda_manifest_index(tmp_path)
    selected = tmp_path / authority
    with selected.open("wb") as stream:
        _ = stream.truncate(project.MAX_AUTHORITY_BYTES + 1)
    with pytest.raises(project.InitializationError, match="byte limit"):
        _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)


def test_bootstrap_rust_authority_rejects_invalid_utf8(tmp_path: Path) -> None:
    """Malformed authority encoding produces a stable bootstrap error."""
    rust = _write_rust_manifest(tmp_path)
    _ = rust.write_bytes(b"\xff")
    with pytest.raises(project.InitializationError, match="cannot read"):
        _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)


@pytest.mark.parametrize("document_type", ["json", "toml"])
def test_bootstrap_document_parser_does_not_format_host_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    document_type: str,
) -> None:
    """An unprintable host read failure stays a typed, caused parse failure."""

    class ForeignHostOSError(OSError):
        @override
        def __str__(self) -> str:
            raise AssertionError("host error formatter must not be called")

    filename = "manifest.json" if document_type == "json" else "tool.toml"
    authority = tmp_path / filename
    fault = ForeignHostOSError("host status unavailable")
    native_lstat = Path.lstat

    def failing_lstat(path: Path) -> os.stat_result:
        if path == authority:
            raise fault
        return native_lstat(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", failing_lstat)
        with pytest.raises(
            project.InitializationError, match="cannot read host manifest"
        ) as caught:
            if document_type == "json":
                project._json_document(  # pyright: ignore[reportPrivateUsage]
                    authority, "host manifest"
                )
            else:
                project._toml_document(  # pyright: ignore[reportPrivateUsage]
                    authority, "host manifest"
                )
    assert caught.value.__cause__ is fault


def test_bootstrap_rust_authority_rejects_oversized_toml(
    tmp_path: Path,
) -> None:
    """Rust version pins cannot be parsed from unbounded metadata."""
    rust = _write_rust_manifest(tmp_path)
    with rust.open("wb") as stream:
        _ = stream.truncate(project.MAX_AUTHORITY_BYTES + 1)
    with pytest.raises(project.InitializationError, match="byte limit"):
        _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)


def test_bootstrap_git_authority_rejects_linked_version_source(
    tmp_path: Path,
) -> None:
    """Host Git import cannot follow a rewritten version authority alias."""
    versions = tmp_path / ".jig/settings/versions.toml"
    versions.parent.mkdir(parents=True)
    _ = versions.write_text(
        '[authority.git]\ncurrent = "2.55.0"\n', encoding="utf-8"
    )
    relocated = versions.with_suffix(".original")
    _ = versions.replace(relocated)
    _ = versions.symlink_to(relocated)
    observation = project.GitHostObservation(
        executable=tmp_path / "host-git",
        exec_path=tmp_path / "host-exec",
        version_line="git version 2.55.0",
    )
    with pytest.raises(project.InitializationError, match=r"redirect|regular"):
        _ = project.import_host_git(tmp_path, LINUX_PLATFORM, observation)
    assert not (tmp_path / ".dependencies").exists()


def test_bootstrap_cuda_authority_rejects_inode_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same-byte path replacement cannot swap the admitted CUDA index."""
    _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    selected = _write_cuda_manifest_index(tmp_path)
    replacement = selected.with_suffix(".replacement")
    _ = replacement.write_bytes(selected.read_bytes())
    original_open = os.open

    def swap_before_open(path: Path, flags: int) -> int:
        if path == selected:
            _ = replacement.replace(selected)
        return original_open(path, flags)

    monkeypatch.setattr(os, "open", swap_before_open)
    with pytest.raises(project.InitializationError, match="changed"):
        _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)


@pytest.mark.parametrize("cuda_index", [False, True])
@pytest.mark.parametrize(
    "fault_type", [OSError, ValueError, TypeError, RuntimeError]
)
def test_bootstrap_authority_fdopen_fault_closes_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    cuda_index: bool,
    fault_type: type[Exception],
) -> None:
    """Bootstrap authority readers own and close failed stream descriptors."""
    if cuda_index:
        _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
        authority = _write_cuda_manifest_index(tmp_path)
    else:
        authority = _write_rust_manifest(tmp_path)

    def inspect() -> None:
        if cuda_index:
            _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)
        else:
            _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)

    opened, fault = _inject_binary_source_wrapper_failure(
        monkeypatch, authority, fault_type
    )
    try:
        with pytest.raises(
            project.InitializationError, match="bootstrap authority"
        ) as caught:
            inspect()
        assert caught.value.__cause__ is fault
        assert len(opened) == 1
        with pytest.raises(
            OSError, match=r"Bad file descriptor|Invalid handle"
        ):
            _ = os.fstat(opened[0])
    finally:
        for descriptor in opened:
            with suppress(OSError):
                os.close(descriptor)


def test_bootstrap_authority_rejects_native_stream_on_wrong_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A native-looking stream cannot divert or leak the opened manifest fd."""
    manifest = _write_rust_manifest(tmp_path)
    foreign = tmp_path / "foreign-readable"
    original_foreign = b"foreign content retained"
    _ = foreign.write_bytes(original_foreign)
    real_open = os.open
    real_fdopen = os.fdopen
    tracked: list[int] = []
    foreign_streams: list[BinaryIO] = []

    def tracked_open(path: Path, flags: int) -> int:
        descriptor = real_open(path, flags)
        if path == manifest:
            tracked.append(descriptor)
        return descriptor

    def wrong_fdopen(_descriptor: int, mode: str) -> BinaryIO:
        foreign_fd = real_open(foreign, os.O_RDONLY)
        stream = cast("BinaryIO", real_fdopen(foreign_fd, mode))
        foreign_streams.append(stream)
        return stream

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", tracked_open)
        isolated.setattr(os, "fdopen", wrong_fdopen)
        try:
            with pytest.raises(
                project.InitializationError, match="native stream descriptor"
            ):
                _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)
        finally:
            for stream in foreign_streams:
                stream.close()
    assert len(tracked) == 1
    with pytest.raises(OSError):
        _ = os.fstat(tracked[0])
    assert foreign.read_bytes() == original_foreign


def test_bootstrap_authority_rejects_forged_host_stream_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A foreign os.fdopen wrapper cannot forge valid bytes for corrupt input."""
    manifest = _write_rust_manifest(tmp_path)
    legitimate = manifest.read_bytes()
    corrupted = b"#" + legitimate[1:]
    _ = manifest.write_bytes(corrupted)
    real_fdopen = os.fdopen

    class ForgedStream:
        def __init__(self, stream: BinaryIO) -> None:
            self.stream: BinaryIO = stream

        def __del__(self) -> None:
            self.stream.close()

        def __enter__(self) -> Self:
            _ = self.stream.__enter__()
            return self

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, _limit: int) -> bytes:
            return legitimate

    def forged_fdopen(descriptor: int, mode: str) -> object:
        # The wrapper owns its own duplicate; the reader closes only its fd.
        return ForgedStream(cast("BinaryIO", real_fdopen(os.dup(descriptor), mode)))

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "fdopen", forged_fdopen)
        with pytest.raises(project.InitializationError, match="native buffered stream"):
            _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)
    assert manifest.read_bytes() == corrupted


@pytest.mark.parametrize("form", ["bytearray", "view", "subclass", "none"])
def test_bootstrap_authority_rejects_nonnative_stream_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, form: str
) -> None:
    """Mutable or foreign stream receipts cannot become version authority."""
    _ = _write_rust_manifest(tmp_path)
    real_fdopen = os.fdopen

    class ForeignBytes(bytes):
        pass

    class ReplacedRead:
        def __init__(self, stream: object) -> None:
            self.stream: BinaryIO = cast("BinaryIO", stream)

        def __enter__(self) -> Self:
            _ = self.stream.__enter__()
            return self

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, limit: int) -> object:
            data = self.stream.read(limit)
            return {
                "bytearray": lambda: bytearray(data),
                "view": lambda: memoryview(data),
                "subclass": lambda: ForeignBytes(data),
                "none": lambda: None,
            }[form]()

    def replaced_authority_stream(descriptor: int) -> BinaryIO:
        return cast("BinaryIO", cast("object", ReplacedRead(real_fdopen(descriptor, "rb"))))

    with monkeypatch.context() as isolated:
        isolated.setattr(project, "_open_authority_stream", replaced_authority_stream)
        with pytest.raises(project.InitializationError, match="native bytes"):
            _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_bootstrap_authority_preserves_stream_read_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """An injected host read failure is a typed error with its original cause."""
    _ = _write_rust_manifest(tmp_path)
    real_fdopen = os.fdopen
    fault = fault_type("host stream read failed")

    class FailingRead:
        def __init__(self, stream: BinaryIO) -> None:
            self.stream: BinaryIO = stream

        def __enter__(self) -> Self:
            _ = self.stream.__enter__()
            return self

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, _limit: int) -> bytes:
            raise fault

    def failing_authority_stream(descriptor: int) -> BinaryIO:
        return cast("BinaryIO", cast("object", FailingRead(cast("BinaryIO", real_fdopen(descriptor, "rb")))))

    with monkeypatch.context() as isolated:
        isolated.setattr(project, "_open_authority_stream", failing_authority_stream)
        with pytest.raises(
            project.InitializationError, match="cannot read bootstrap authority"
        ) as caught:
            _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)
    assert caught.value.__cause__ is fault


def test_bootstrap_authority_rejects_foreign_lstat_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Duck-typed file metadata cannot claim native manifest authority."""
    selected = _write_rust_manifest(tmp_path)
    real_lstat = Path.lstat

    class ForeignStat:
        def __init__(self, status: os.stat_result) -> None:
            self.status: os.stat_result = status

        def __getattr__(self, name: str) -> object:
            return cast("object", getattr(self.status, name))

    def forged_lstat(path: Path) -> os.stat_result:
        status = real_lstat(path)
        if path == selected:
            return cast("os.stat_result", cast("object", ForeignStat(status)))
        return status

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", forged_lstat)
        with pytest.raises(project.InitializationError, match="native file status"):
            _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)


@pytest.mark.parametrize("receipt", [None, False, True, -1, 0.5])
def test_bootstrap_authority_rejects_invalid_open_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """Nonnative file handles never reach fdopen and unrelated OS descriptors."""
    selected = _write_rust_manifest(tmp_path)
    real_open = os.open

    def invalid_open(path: Path, flags: int) -> int:
        if path == selected:
            return cast("int", receipt)
        return real_open(path, flags)

    def forbidden_fdopen(*_args: object, **_kwargs: object) -> Never:
        pytest.fail("invalid authority descriptor reached fdopen")

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", invalid_open)
        isolated.setattr(os, "fdopen", forbidden_fdopen)
        with pytest.raises(project.InitializationError, match="native descriptor"):
            _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_bootstrap_authority_preserves_host_open_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Host descriptor-open errors are typed without dropping the cause."""
    selected = _write_rust_manifest(tmp_path)
    real_open = os.open
    fault = fault_type("cannot open host authority")

    def failing_open(path: Path, flags: int) -> int:
        if path == selected:
            raise fault
        return real_open(path, flags)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", failing_open)
        with pytest.raises(
            project.InitializationError, match="cannot open bootstrap authority"
        ) as caught:
            _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)
    assert caught.value.__cause__ is fault


def test_bootstrap_cuda_authority_rejects_nonregular_fifo(
    tmp_path: Path,
) -> None:
    """A named pipe is never interpreted as an absent CUDA index."""
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO unsupported")
    _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    index = tmp_path / project.CUDA_TOOLCHAIN_INDEX
    mkfifo = cast("Callable[[Path], None] | None", getattr(os, "mkfifo", None))
    if mkfifo is None:
        pytest.skip("FIFO unsupported")
    mkfifo(index)
    with pytest.raises(project.InitializationError, match="regular"):
        _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)


def test_cuda_inspection_rejects_unknown_schema(tmp_path: Path) -> None:
    """CUDA readiness rejects manifests from an unknown schema revision."""
    manifest = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    document = {
        "schema_version": 2,
        "platform": LINUX_PLATFORM,
        "toolkit_root": CUDA_VERSION_ROOT,
    }
    _ = manifest.write_text(
        json.dumps(document), encoding="utf-8", newline="\n"
    )
    with pytest.raises(
        project.InitializationError,
        match="unsupported CUDA toolchain manifest schema",
    ):
        _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)


def test_cuda_inspection_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    """CUDA platform identity never uses last-value-wins JSON semantics."""
    manifest = tmp_path / project.CUDA_TOOLCHAIN_MANIFEST
    manifest.parent.mkdir(parents=True)
    _ = manifest.write_text(
        concat := (
            '{"schema_version":1,'
            '"platform":"linux-x86_64",'
            '"platform":"windows-x86_64",'
            f'"toolkit_root":"{CUDA_VERSION_ROOT}"}}'
        ),
        encoding="utf-8",
        newline="\n",
    )
    assert concat
    with pytest.raises(
        project.InitializationError,
        match="duplicate bootstrap JSON key: platform",
    ):
        _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)


def test_cuda_inspection_rejects_escaping_toolkit_root(
    tmp_path: Path,
) -> None:
    """CUDA manifest cannot make an external directory repository-ready."""
    manifest = tmp_path / project.CUDA_TOOLCHAIN_MANIFEST
    manifest.parent.mkdir(parents=True)
    _ = manifest.write_text(
        json.dumps({
            "schema_version": project.CUDA_TOOLCHAIN_SCHEMA_VERSION,
            "platform": LINUX_PLATFORM,
            "toolkit_root": "../escape",
        }),
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(
        project.InitializationError,
        match="toolkit_root must stay within the repository",
    ):
        _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)


def test_cuda_inspection_rejects_drive_relative_toolkit_root(
    tmp_path: Path,
) -> None:
    """CUDA toolkit identity cannot select Windows drive-relative state."""
    manifest = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    document = {
        "schema_version": project.CUDA_TOOLCHAIN_SCHEMA_VERSION,
        "platform": LINUX_PLATFORM,
        "toolkit_root": "D:escape",
    }
    _ = manifest.write_text(
        json.dumps(document),
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(
        project.InitializationError,
        match="toolkit_root must stay within the repository",
    ):
        _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)


@pytest.mark.parametrize("field", [CUDA_TOOLKIT_ROOT_FIELD, "nvrtc_library"])
def test_cuda_bootstrap_rejects_host_dependent_backslash_paths(
    tmp_path: Path,
    field: str,
) -> None:
    """Selected CUDA paths retain identical meaning on Linux and Windows."""
    manifest = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    if field == CUDA_TOOLKIT_ROOT_FIELD:
        document = {
            "schema_version": project.CUDA_TOOLCHAIN_SCHEMA_VERSION,
            "platform": LINUX_PLATFORM,
            "toolkit_root": CUDA_VERSION_ROOT.replace("/", "\\"),
        }
        _ = manifest.write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(
            project.InitializationError, match="must use forward slashes"
        ):
            _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)
        return
    index = _write_cuda_manifest_index(tmp_path)
    platforms = cast(
        "dict[str, object]",
        json.loads(index.read_text(encoding="utf-8"))["platforms"],
    )
    selected = cast("dict[str, object]", platforms[LINUX_PLATFORM])
    selected["nvrtc_library"] = r"lib\libnvrtc.so.13"
    _ = index.write_text(
        json.dumps({"schema_version": 1, "platforms": platforms}),
        encoding="utf-8",
    )
    with pytest.raises(
        project.InitializationError, match="must use forward slashes"
    ):
        _ = project.cuda_toolchain_nvrtc_relative_path(tmp_path, LINUX_PLATFORM)


@pytest.mark.parametrize(
    "toolkit_root",
    [
        ".",
        "./",
        "./.dependencies/cuda/13.3.1/toolkit",
        ".dependencies/cuda/./toolkit",
        ".dependencies//cuda/toolkit",
        ".dependencies/cuda/toolkit/",
    ],
)
def test_cuda_manifest_rejects_noncanonical_toolkit_root(
    tmp_path: Path, toolkit_root: str
) -> None:
    """Manifest toolkit root must not alias checkout or another path spelling."""
    manifest = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["toolkit_root"] = toolkit_root
    _ = manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(project.InitializationError, match="stay within"):
        _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)


@pytest.mark.parametrize(
    "library",
    [".", "./lib/libnvrtc.so.13", "lib/./libnvrtc.so.13", "lib//libnvrtc.so.13", "lib/"],
)
def test_cuda_index_rejects_noncanonical_nvrtc_path(
    tmp_path: Path, library: str
) -> None:
    """Indexed native library paths must be unambiguous across hosts."""
    _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    index = _write_cuda_manifest_index(tmp_path)
    data = json.loads(index.read_text(encoding="utf-8"))
    data["platforms"][LINUX_PLATFORM]["nvrtc_library"] = library
    _ = index.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(project.InitializationError, match="stay within"):
        _ = project.cuda_toolchain_nvrtc_relative_path(tmp_path, LINUX_PLATFORM)


def test_cuda_inspection_rejects_windows_manifest_on_linux(
    tmp_path: Path,
) -> None:
    """The current Windows bundle is explicitly unsupported on Linux."""
    _ = _write_cuda_manifest(tmp_path, WINDOWS_PLATFORM)

    status = project.inspect_cuda(tmp_path, LINUX_PLATFORM)

    assert status.state is project.ComponentState.UNSUPPORTED
    assert WINDOWS_PLATFORM in status.detail
    assert LINUX_PLATFORM in status.detail


def test_rust_inspection_rejects_escaping_channel(tmp_path: Path) -> None:
    """Pinned Rust channel cannot redirect repository-local Cargo lookup."""
    _ = _write_rust_manifest(tmp_path, "../escape")
    with pytest.raises(
        project.InitializationError,
        match="channel must be one repository-local path segment",
    ):
        _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)


def test_rust_inspection_rejects_drive_relative_channel(
    tmp_path: Path,
) -> None:
    """Pinned Rust channel cannot select Windows drive-relative state."""
    _ = _write_rust_manifest(tmp_path, "D:escape")
    with pytest.raises(
        project.InitializationError,
        match="channel must be one repository-local path segment",
    ):
        _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)


@pytest.mark.parametrize(
    "channel",
    ["CON", "nul.txt", "AUX ", "version.", "COM1", "name:stream"],
)
def test_rust_inspection_rejects_windows_reserved_channel(
    tmp_path: Path, channel: str
) -> None:
    """Portable Rust channel names must not alias Windows device paths."""
    _ = _write_rust_manifest(tmp_path, channel)
    with pytest.raises(
        project.InitializationError,
        match="channel must be one repository-local path segment",
    ):
        _ = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)


@pytest.mark.parametrize(
    "selected_path",
    ["CON", "bin/NUL.dll", "bin/COM1.so", "bin/version.", "bin/foo:stream"],
)
@pytest.mark.parametrize("field", ["toolkit_root", "nvrtc_library"])
def test_cuda_paths_reject_windows_reserved_components(
    tmp_path: Path, selected_path: str, field: str
) -> None:
    """CUDA authority paths retain the same meaning on POSIX and Windows."""
    if field == "toolkit_root":
        manifest = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["toolkit_root"] = selected_path
        _ = manifest.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(project.InitializationError, match="stay within"):
            _ = project.inspect_cuda(tmp_path, LINUX_PLATFORM)
    else:
        _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
        index = _write_cuda_manifest_index(tmp_path)
        data = json.loads(index.read_text(encoding="utf-8"))
        data["platforms"][LINUX_PLATFORM]["nvrtc_library"] = selected_path
        _ = index.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(project.InitializationError, match="stay within"):
            _ = project.cuda_toolchain_nvrtc_relative_path(
                tmp_path, LINUX_PLATFORM
            )


@pytest.mark.parametrize("manifest_name", ["CON", "nul.txt", "aux ", "bad."])
def test_cuda_index_rejects_windows_reserved_manifest_name(
    tmp_path: Path, manifest_name: str
) -> None:
    """Manifest selection rejects names that alias on Windows."""
    _ = _write_cuda_manifest(tmp_path, LINUX_PLATFORM)
    index = _write_cuda_manifest_index(tmp_path)
    data = json.loads(index.read_text(encoding="utf-8"))
    data["platforms"][LINUX_PLATFORM]["manifest"] = manifest_name
    _ = index.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(project.InitializationError, match="one repository-local"):
        _ = project.cuda_toolchain_manifest_path(tmp_path, LINUX_PLATFORM)


def _assert_rust_validation_alias(
    alias: Path,
    tool_id: str,
    linker_variable: str,
) -> None:
    alias_text = alias.read_text(encoding="ascii")
    assert f'export {linker_variable}="$tool_dir/cc"' in alias_text
    assert f'exec "$tool_dir/{tool_id}" "$@"' in alias_text
    assert alias.stat().st_mode & stat.S_IXUSR


def test_rust_linker_adapter_binds_explicit_linux_host_linker(
    tmp_path: Path,
) -> None:
    """Linux Rust tools override validator linker through neutral aliases."""
    linker = tmp_path / "host/bin/cc"
    linker.parent.mkdir(parents=True)
    linker.touch()
    stable = tmp_path / ".dependencies/rust/1.98.1"
    nightly = tmp_path / ".dependencies/rust/nightly-2026-07-14"
    stable_bin = stable / "bin"
    nightly_bin = nightly / "bin"
    stable_bin.mkdir(parents=True)
    nightly_bin.mkdir(parents=True)
    for native in (
        stable_bin / "cargo",
        nightly_bin / "cargo-clippy",
        nightly_bin / "cargo-fmt",
    ):
        _ = native.write_text(native.name, encoding="ascii")
        _ = native.chmod(native.stat().st_mode | stat.S_IXUSR)

    adapters = project.write_rust_linker_adapters(
        (stable, nightly),
        LINUX_PLATFORM,
        linker=linker,
    )

    assert adapters == (stable_bin / "cc", nightly_bin / "cc")
    expected_cc = f'#!/bin/sh\nexec {linker.resolve()} "$@"\n'
    assert adapters[0].read_text(encoding="ascii") == expected_cc
    assert adapters[1].read_text(encoding="ascii") == expected_cc
    linker_variable = "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER"
    _assert_rust_validation_alias(
        stable_bin / "cargo.bin",
        "cargo",
        linker_variable,
    )
    _assert_rust_validation_alias(
        nightly_bin / "cargo-clippy.bin",
        "cargo-clippy",
        linker_variable,
    )
    _assert_rust_validation_alias(
        nightly_bin / "cargo-fmt.bin",
        "cargo-fmt",
        linker_variable,
    )


def _linux_adapter_writer_tree(tmp_path: Path) -> tuple[Path, Path]:
    """Create one valid Rust import destination and explicit host cc path.

    Returns:
        Synthetic stable Rust toolchain and observed host linker paths.

    """
    root = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    native = root / "bin/cargo"
    native.parent.mkdir(parents=True)
    _ = native.write_bytes(RUST_CARGO_BYTES)
    linker = tmp_path / "host-cc"
    _ = linker.write_bytes(b"host-linker")
    return root, linker


def test_rust_adapter_writer_rejects_linked_cc_target(tmp_path: Path) -> None:
    """Writing a pinned linker shim must not overwrite an aliased target."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    external = tmp_path / "unrelated-linker"
    original = b"unrelated linker content"
    _ = external.write_bytes(original)
    try:
        _ = (root / "bin/cc").symlink_to(external)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(project.InitializationError, match="redirect"):
        _ = project.write_rust_linker_adapters(
            (root,), LINUX_PLATFORM, linker=linker
        )
    assert external.read_bytes() == original
    assert not (root / project.RUST_LINUX_ADAPTER_MARKER).exists()


@pytest.mark.parametrize("target", ["bin/cc", project.RUST_LINUX_ADAPTER_MARKER])
def test_rust_adapter_writer_rejects_hardlinked_output(
    tmp_path: Path, target: str
) -> None:
    """A wrapper or marker must not rewrite an unrelated hardlinked file."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    external = tmp_path / "unrelated-rust-file"
    original = b"unrelated Rust-adjacent content"
    _ = external.write_bytes(original)
    try:
        os.link(external, root / target)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hardlinks unavailable: {error}")

    with pytest.raises(project.InitializationError, match="hardlink"):
        _ = project.write_rust_linker_adapters(
            (root,), LINUX_PLATFORM, linker=linker
        )

    assert external.read_bytes() == original
    assert (root / target).read_bytes() == original
    if target != "bin/cc":
        assert not (root / "bin/cc").exists()


def test_rust_adapter_replaces_native_hardlinked_alias_without_mutating_tool(
    tmp_path: Path,
) -> None:
    """Imported Cargo aliases are removed before the linker wrapper is written."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    native = root / "bin/cargo"
    alias = root / "bin/cargo.bin"
    try:
        os.link(native, alias)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hardlinks unavailable: {error}")

    adapters = project.write_rust_linker_adapters(
        (root,), LINUX_PLATFORM, linker=linker
    )

    assert adapters == (root / "bin/cc",)
    assert native.read_bytes() == RUST_CARGO_BYTES
    assert alias.stat().st_ino != native.stat().st_ino
    assert alias.read_text(encoding="ascii").startswith("#!/bin/sh\n")


def _patch_rust_adapter_publisher(
    monkeypatch: pytest.MonkeyPatch,
    target: Path,
    *,
    before: Callable[[], None] | None = None,
    writer: Callable[[int, bytes], int] | None = None,
) -> None:
    """Inject a selected directory-bound publication without touching other writes."""
    original = project._write_import_completion_marker_at_parent

    def intercepted(
        path: Path,
        content: str,
        parent_fd: int | None,
        *,
        executable: bool = False,
    ) -> None:
        if path == target:
            if before is not None:
                before()
            if writer is not None:
                with monkeypatch.context() as isolated:
                    isolated.setattr(os, "write", writer)
                    original(path, content, parent_fd, executable=executable)
                return
        original(path, content, parent_fd, executable=executable)

    monkeypatch.setattr(
        project, "_write_import_completion_marker_at_parent", intercepted
    )


@pytest.mark.parametrize("bad_write_count", [1, None, True, -1, 1_000_000])
def test_rust_adapter_marker_requires_complete_staging_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_write_count: object,
) -> None:
    """Do not report linker adapter success after an incomplete marker."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    marker = root / project.RUST_LINUX_ADAPTER_MARKER
    if os.name == "posix":
        original_write = os.write

        def incomplete_write(descriptor: int, data: bytes) -> int:
            _ = original_write(descriptor, data[:1])
            return cast("int", bad_write_count)

        _patch_rust_adapter_publisher(monkeypatch, marker, writer=incomplete_write)
    else:
        original_write = Path.write_bytes

        def incomplete_write_legacy(path: Path, data: bytes) -> int:
            assert path == marker
            _ = original_write(path, data[:1])
            return cast("int", bad_write_count)

        monkeypatch.setattr(Path, "write_bytes", incomplete_write_legacy)
    with pytest.raises(
        project.InitializationError, match="short or invalid byte count"
    ):
        _ = project.write_rust_linker_adapters(
            (root,), LINUX_PLATFORM, linker=linker
        )
    assert not marker.exists()


@pytest.mark.parametrize("target_name", ["cc", "cargo.bin"])
@pytest.mark.parametrize("bad_write_count", [1, None, True, -1, 1_000_000])
def test_rust_adapter_scripts_require_complete_character_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    target_name: str,
    bad_write_count: object,
) -> None:
    """Linker and Cargo wrapper scripts must not publish short writes."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    target = root / "bin" / target_name
    marker = root / project.RUST_LINUX_ADAPTER_MARKER
    if os.name == "posix":
        original_write = os.write

        def incomplete_write(descriptor: int, data: bytes) -> int:
            _ = original_write(descriptor, data[:1])
            return cast("int", bad_write_count)

        _patch_rust_adapter_publisher(monkeypatch, target, writer=incomplete_write)
    else:
        original_write = Path.write_text

        def incomplete_write_legacy(
            path: Path,
            data: str,
            *,
            encoding: str | None = None,
            newline: str | None = None,
        ) -> int:
            selected = data[:1] if path == target else data
            _ = original_write(path, selected, encoding=encoding, newline=newline)
            return cast("int", bad_write_count) if path == target else len(data)

        monkeypatch.setattr(Path, "write_text", incomplete_write_legacy)
    match = (
        "short or invalid byte count"
        if os.name == "posix"
        else "short or invalid character count"
    )
    with pytest.raises(project.InitializationError, match=match):
        _ = project.write_rust_linker_adapters(
            (root,), LINUX_PLATFORM, linker=linker
        )
    assert not marker.exists()
    assert not target.exists()


@pytest.mark.parametrize("target_name", ["cc", "cargo.bin"])
def test_rust_adapter_script_rejects_complete_count_with_corrupt_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_name: str,
) -> None:
    """A full reported character count cannot certify corrupt wrapper text."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    target = root / "bin" / target_name
    marker = root / project.RUST_LINUX_ADAPTER_MARKER
    if os.name == "posix":
        original_write = os.write

        def corrupt_write(descriptor: int, content: bytes) -> int:
            return original_write(descriptor, b"x" * len(content))

        _patch_rust_adapter_publisher(monkeypatch, target, writer=corrupt_write)
    else:
        original_write = Path.write_text

        def corrupt_write_legacy(
            path: Path,
            content: str,
            *,
            encoding: str | None = None,
            newline: str | None = None,
        ) -> int:
            actual = "x" * len(content) if path == target else content
            _ = original_write(path, actual, encoding=encoding, newline=newline)
            return len(content)

        monkeypatch.setattr(Path, "write_text", corrupt_write_legacy)
    with pytest.raises(project.InitializationError, match="(script|marker) content"):
        _ = project.write_rust_linker_adapters(
            (root,), LINUX_PLATFORM, linker=linker
        )
    assert not target.exists()
    assert not marker.exists()


def test_rust_adapter_marker_rejects_complete_count_with_corrupt_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A full reported byte count cannot certify a corrupt readiness marker."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    marker = root / project.RUST_LINUX_ADAPTER_MARKER
    if os.name == "posix":
        original_write = os.write

        def corrupt_write(descriptor: int, content: bytes) -> int:
            return original_write(descriptor, b"x" * len(content))

        _patch_rust_adapter_publisher(monkeypatch, marker, writer=corrupt_write)
    else:
        original_write = Path.write_bytes

        def corrupt_write_legacy(path: Path, content: bytes) -> int:
            actual = b"x" * len(content) if path == marker else content
            _ = original_write(path, actual)
            return len(content)

        monkeypatch.setattr(Path, "write_bytes", corrupt_write_legacy)
    with pytest.raises(project.InitializationError, match="marker content"):
        _ = project.write_rust_linker_adapters(
            (root,), LINUX_PLATFORM, linker=linker
        )
    assert not marker.exists()


def test_rust_adapter_writer_rejects_linked_marker_target(
    tmp_path: Path,
) -> None:
    """Marker publication must not follow a symlink to another file."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    external = tmp_path / "unrelated-marker"
    original = b"original unrelated marker"
    _ = external.write_bytes(original)
    try:
        _ = (root / project.RUST_LINUX_ADAPTER_MARKER).symlink_to(external)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(project.InitializationError, match="redirect"):
        _ = project.write_rust_linker_adapters(
            (root,), LINUX_PLATFORM, linker=linker
        )
    assert external.read_bytes() == original
    assert not (root / "bin/cc").exists()


def test_rust_adapter_writer_rejects_linked_bin_directory(
    tmp_path: Path,
) -> None:
    """A redirected bin parent must not create shims outside toolchain."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    original = root / "bin"
    relocated = tmp_path / "external-bin"
    _ = original.replace(relocated)
    try:
        _ = original.symlink_to(relocated, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(project.InitializationError, match="redirect"):
        _ = project.write_rust_linker_adapters(
            (root,), LINUX_PLATFORM, linker=linker
        )
    assert not (relocated / "cc").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("redirect", ["symlink", "physical"])
def test_rust_adapter_writer_rejects_bin_parent_swap_before_script_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, redirect: str
) -> None:
    """An exchanged bin parent cannot receive a generated cc script."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    bin_dir = root / "bin"
    parked = tmp_path / "parked-rust-bin"
    foreign = tmp_path / "foreign-rust-bin"
    foreign.mkdir()
    _ = (foreign / "cargo").write_bytes(RUST_CARGO_BYTES)
    original = b"foreign linker must survive"
    _ = (foreign / "cc").write_bytes(original)
    swapped = False

    def exchange() -> None:
        nonlocal swapped
        bin_dir.rename(parked)
        if redirect == "symlink":
            bin_dir.symlink_to(foreign, target_is_directory=True)
        else:
            foreign.rename(bin_dir)
        swapped = True

    with monkeypatch.context() as isolated:
        _patch_rust_adapter_publisher(isolated, bin_dir / "cc", before=exchange)
        with pytest.raises(project.InitializationError):
            _ = project.write_rust_linker_adapters(
                (root,), LINUX_PLATFORM, linker=linker
            )
    assert swapped
    injected = foreign if redirect == "symlink" else bin_dir
    assert (injected / "cc").read_bytes() == original
    assert not (parked / "cc").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("redirect", ["symlink", "physical"])
def test_rust_adapter_writer_rejects_root_swap_before_marker_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, redirect: str
) -> None:
    """An exchanged toolchain root cannot receive readiness metadata."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    parked = tmp_path / "parked-rust-root"
    foreign = tmp_path / "foreign-rust-root"
    foreign.mkdir()
    original = b"foreign marker must survive"
    _ = (foreign / project.RUST_LINUX_ADAPTER_MARKER).write_bytes(original)
    swapped = False

    def exchange() -> None:
        nonlocal swapped
        root.rename(parked)
        if redirect == "symlink":
            root.symlink_to(foreign, target_is_directory=True)
        else:
            foreign.rename(root)
        swapped = True

    with monkeypatch.context() as isolated:
        _patch_rust_adapter_publisher(
            isolated, root / project.RUST_LINUX_ADAPTER_MARKER, before=exchange
        )
        with pytest.raises(project.InitializationError):
            _ = project.write_rust_linker_adapters(
                (root,), LINUX_PLATFORM, linker=linker
            )
    assert swapped
    injected = foreign if redirect == "symlink" else root
    assert (injected / project.RUST_LINUX_ADAPTER_MARKER).read_bytes() == original
    assert not (parked / project.RUST_LINUX_ADAPTER_MARKER).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("parent_kind", ["root", "bin"])
def test_rust_adapter_writer_pins_initial_parent_before_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, parent_kind: str
) -> None:
    """An early physical parent exchange cannot replace the admitted toolchain."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    bin_dir = root / "bin"
    parent = root if parent_kind == "root" else bin_dir
    parked = tmp_path / "parked-rust-parent"
    foreign = tmp_path / "foreign-rust-parent"
    injected = foreign / "bin" if parent_kind == "root" else foreign
    injected.mkdir(parents=True)
    _ = (injected / "cargo").write_bytes(RUST_CARGO_BYTES)
    expected = b"do not rewrite this cc"
    _ = (injected / "cc").write_bytes(expected)
    original_admit = project._admit_rust_adapter_write_target
    swapped = False

    def swap_during_admission(path: Path, *, allow_hardlink: bool = False) -> None:
        nonlocal swapped
        if path == bin_dir / "cc" and not swapped:
            parent.rename(parked)
            foreign.rename(parent)
            swapped = True
        original_admit(path, allow_hardlink=allow_hardlink)

    with monkeypatch.context() as isolated:
        isolated.setattr(
            project, "_admit_rust_adapter_write_target", swap_during_admission
        )
        with pytest.raises(project.InitializationError):
            _ = project.write_rust_linker_adapters(
                (root,), LINUX_PLATFORM, linker=linker
            )
    assert swapped
    destination = parent / "bin/cc" if parent_kind == "root" else parent / "cc"
    assert destination.read_bytes() == expected


def test_rust_adapter_writer_replaces_owned_shims_on_rerun(tmp_path: Path) -> None:
    """A second host linker selection updates scripts without touching cargo."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    first = project.write_rust_linker_adapters(
        (root,), LINUX_PLATFORM, linker=linker
    )
    original_cargo = (root / "bin/cargo").read_bytes()
    second_linker = tmp_path / "new-host-cc"
    _ = second_linker.write_bytes(b"another host linker")

    second = project.write_rust_linker_adapters(
        (root,), LINUX_PLATFORM, linker=second_linker
    )

    assert first == second == (root / "bin/cc",)
    assert second[0].read_text(encoding="ascii") == (
        f'#!/bin/sh\nexec {second_linker.resolve()} "$@"\n'
    )
    assert (root / "bin/cargo.bin").stat().st_mode & stat.S_IXUSR
    assert (root / "bin/cargo").read_bytes() == original_cargo
    assert (root / project.RUST_LINUX_ADAPTER_MARKER).read_bytes() == (
        project.RUST_LINUX_ADAPTER_CONTENT
    )


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX file descriptors")
def test_rust_adapter_writer_chmod_fault_cleans_up_open_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An executable-mode failure cannot publish a partial linker adapter."""
    root, linker = _linux_adapter_writer_tree(tmp_path)
    fault = OSError("cannot mark executable")
    opened: list[int] = []

    def fail_chmod(descriptor: int, _mode: int) -> None:
        opened.append(descriptor)
        raise fault

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "fchmod", fail_chmod)
        with pytest.raises(project.InitializationError) as caught:
            _ = project.write_rust_linker_adapters(
                (root,), LINUX_PLATFORM, linker=linker
            )
    assert caught.value.__cause__ is fault
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])
    assert not (root / "bin/cc").exists()
    assert not (root / project.RUST_LINUX_ADAPTER_MARKER).exists()


def test_rust_linker_adapters_leave_windows_aliases_unchanged(
    tmp_path: Path,
) -> None:
    """Linux linker adaptation never rewrites Windows Rust aliases."""
    root = tmp_path / ".dependencies/rust/1.98.1"
    binary = root / "bin/cargo.exe"
    alias = root / "bin/cargo.bin"
    binary.parent.mkdir(parents=True)
    _ = binary.write_bytes(RUST_CARGO_BYTES)
    _ = alias.write_bytes(RUST_CARGO_BYTES)

    adapters = project.write_rust_linker_adapters(
        (root,),
        WINDOWS_PLATFORM,
        linker=tmp_path / "unused-cc.exe",
    )

    assert adapters == ()
    assert alias.read_bytes() == RUST_CARGO_BYTES
    assert not (root / project.RUST_LINUX_ADAPTER_MARKER).exists()


def test_rust_toolchain_import_preserves_native_tree_and_alias(
    tmp_path: Path,
) -> None:
    """Imported Rust keeps its sysroot layout and adds one neutral Jig alias."""
    source = tmp_path / "host-rust"
    source_bin = source / "bin"
    source_lib = source / "lib" / "rustlib"
    source_bin.mkdir(parents=True)
    source_lib.mkdir(parents=True)
    cargo = source_bin / "cargo"
    _ = cargo.write_bytes(RUST_CARGO_BYTES)
    _ = cargo.chmod(cargo.stat().st_mode | stat.S_IXUSR)
    rustc = source_bin / "rustc"
    _ = rustc.write_bytes(RUST_RUSTC_BYTES)
    _ = rustc.chmod(rustc.stat().st_mode | stat.S_IXUSR)
    _ = (source_lib / "manifest").write_bytes(RUST_STD_BYTES)
    destination = tmp_path / ".dependencies" / "rust" / RUST_CHANNEL

    aliases = project.import_rust_toolchain(
        source,
        destination,
        tool_ids=("cargo", "rustc"),
        windows=False,
    )

    cargo_alias = destination / "bin" / "cargo.bin"
    rustc_alias = destination / "bin" / "rustc.bin"
    assert aliases == (cargo_alias, rustc_alias)
    assert cargo_alias.read_bytes() == RUST_CARGO_BYTES
    assert cargo_alias.stat().st_mode & stat.S_IXUSR
    assert rustc_alias.read_bytes() == RUST_RUSTC_BYTES
    assert rustc_alias.stat().st_mode & stat.S_IXUSR
    assert (destination / "bin" / "rustc").read_bytes() == RUST_RUSTC_BYTES
    assert (destination / "lib/rustlib/manifest").read_bytes() == RUST_STD_BYTES
    assert project.rust_toolchain_import_complete(destination)


def test_rust_toolchain_import_aliases_windows_compiler(
    tmp_path: Path,
) -> None:
    """Windows stable imports expose neutral Cargo and rustc aliases."""
    source = tmp_path / "host-rust"
    source_bin = source / "bin"
    source_bin.mkdir(parents=True)
    _ = (source_bin / "cargo.exe").write_bytes(RUST_CARGO_BYTES)
    _ = (source_bin / "rustc.exe").write_bytes(RUST_RUSTC_BYTES)
    (source / "lib/rustlib").mkdir(parents=True)
    destination = tmp_path / ".dependencies" / "rust" / RUST_CHANNEL

    aliases = project.import_rust_toolchain(
        source,
        destination,
        tool_ids=("cargo", "rustc"),
        windows=True,
    )

    cargo_alias = destination / "bin/cargo.bin"
    rustc_alias = destination / "bin/rustc.bin"
    assert aliases == (cargo_alias, rustc_alias)
    assert cargo_alias.read_bytes() == RUST_CARGO_BYTES
    assert rustc_alias.read_bytes() == RUST_RUSTC_BYTES


@pytest.mark.parametrize("injection", ["symlink", "hardlink"])
@pytest.mark.parametrize("link_error", ["exists", "unavailable"])
def test_portable_rust_import_rejects_late_alias_leaf_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    injection: str, link_error: str
) -> None:
    """A copy fallback cannot write through an alias created during hardlink."""
    source = tmp_path / "host-rust"
    (source / "bin").mkdir(parents=True)
    _ = (source / "bin/cargo").write_bytes(RUST_CARGO_BYTES)
    destination = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    alias = destination / "bin/cargo.bin"
    external = tmp_path / "unrelated-binary"
    sentinel = b"external binary must not change"
    _ = external.write_bytes(sentinel)
    original_link = os.link
    collision = False

    def inject_at_alias_link(
        from_path: str | os.PathLike[str],
        to_path: str | os.PathLike[str],
    ) -> None:
        nonlocal collision
        if Path(to_path) == alias and not collision:
            if injection == "symlink":
                _ = alias.symlink_to(external)
            else:
                original_link(external, alias)
            collision = True
            if link_error == "exists":
                raise FileExistsError("late neutral alias collision")
            raise OSError("cross-device link fallback with late collision")
        original_link(from_path, to_path)

    monkeypatch.setattr(
        project, "_supports_pinned_local_state_directories", lambda: False
    )
    monkeypatch.setattr(os, "link", inject_at_alias_link)
    with pytest.raises(project.InitializationError, match="already exists"):
        _ = project.import_rust_toolchain(
            source, destination, tool_ids=("cargo",), windows=False
        )
    assert collision
    assert external.read_bytes() == sentinel
    assert not project.rust_toolchain_import_complete(destination)



def test_portable_rust_import_copy_fallback_preserves_executable_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hardlink-free portable imports retain executable bytes and permissions."""
    source = tmp_path / "host-rust"
    (source / "bin").mkdir(parents=True)
    native = source / "bin/cargo"
    _ = native.write_bytes(RUST_CARGO_BYTES)
    native.chmod(0o700)
    destination = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    original_link = os.link
    fallback = False

    def unsupported_alias_link(
        input_path: str | os.PathLike[str],
        output_path: str | os.PathLike[str],
    ) -> None:
        nonlocal fallback
        if Path(output_path) == destination / "bin/cargo.bin":
            fallback = True
            raise OSError("hardlinks unavailable")
        original_link(input_path, output_path)

    monkeypatch.setattr(
        project, "_supports_pinned_local_state_directories", lambda: False
    )
    monkeypatch.setattr(os, "link", unsupported_alias_link)
    aliases = project.import_rust_toolchain(
        source, destination, tool_ids=("cargo",), windows=False
    )
    assert fallback
    assert aliases == (destination / "bin/cargo.bin",)
    assert aliases[0].read_bytes() == RUST_CARGO_BYTES
    assert stat.S_IMODE(aliases[0].stat().st_mode) == 0o700
    assert project.rust_toolchain_import_complete(destination)


@pytest.mark.parametrize("restored_mtime", [False, True])
def test_portable_import_copy_rejects_in_place_source_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, restored_mtime: bool
) -> None:
    """A copied neutral tool cannot certify a mutating host source inode."""
    source = tmp_path / "host-rust"
    (source / "bin").mkdir(parents=True)
    _ = (source / "bin/cargo").write_bytes(RUST_CARGO_BYTES)
    destination = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    native = destination / "bin/cargo"
    original_link = os.link
    original_copy = cast(
        "Callable[[int, int], None]", vars(project)["_write_import_file_payload"]
    )
    mutated = False

    def refuse_alias_link(
        input_path: str | os.PathLike[str],
        output_path: str | os.PathLike[str],
    ) -> None:
        if Path(output_path) == destination / "bin/cargo.bin":
            raise OSError("hardlinks unavailable")
        original_link(input_path, output_path)

    def copy_then_mutate(input_fd: int, output_fd: int) -> None:
        nonlocal mutated
        original_copy(input_fd, output_fd)
        if not mutated:
            before = native.stat()
            _ = native.write_bytes(b"X" * len(RUST_CARGO_BYTES))
            mtime = (
                before.st_mtime_ns if restored_mtime
                else before.st_mtime_ns + 1_000_000_000
            )
            os.utime(native, ns=(before.st_atime_ns, mtime))
            mutated = True

    monkeypatch.setattr(
        project, "_supports_pinned_local_state_directories", lambda: False
    )
    monkeypatch.setattr(os, "link", refuse_alias_link)
    monkeypatch.setattr(project, "_write_import_file_payload", copy_then_mutate)
    with pytest.raises(project.InitializationError, match="source.*changed"):
        _ = project.import_rust_toolchain(
            source, destination, tool_ids=("cargo",), windows=False
        )
    assert mutated
    assert not project.rust_toolchain_import_complete(destination)


@pytest.mark.parametrize("portable", [False, True])
@pytest.mark.parametrize("alias_bytes", [b"unexpected-cargo", RUST_CARGO_BYTES])
def test_rust_import_rejects_preexisting_physical_host_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    portable: bool,
    alias_bytes: bytes,
) -> None:
    """Host-provided alias bytes must not become a bootstrap-owned neutral tool."""
    source = tmp_path / "host-rust"
    (source / "bin").mkdir(parents=True)
    _ = (source / "bin/cargo").write_bytes(RUST_CARGO_BYTES)
    _ = (source / "bin/cargo.bin").write_bytes(alias_bytes)
    destination = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    if portable:
        monkeypatch.setattr(
            project, "_supports_pinned_local_state_directories", lambda: False
        )

    with pytest.raises(project.InitializationError, match="alias.*already exists"):
        _ = project.import_rust_toolchain(
            source, destination, tool_ids=("cargo",), windows=False
        )
    assert (source / "bin/cargo.bin").read_bytes() == alias_bytes
    assert (destination / "bin/cargo.bin").read_bytes() == alias_bytes
    assert not project.rust_toolchain_import_complete(destination)


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX symlinks")
@pytest.mark.parametrize("alias_source", ["bin-parent", "native", "alias"])
def test_rust_import_never_admits_linked_native_alias_or_parent(
    tmp_path: Path, alias_source: str
) -> None:
    """Copied toolchain links must not create or approve foreign Cargo aliases."""
    source = tmp_path / "host-rust"
    source.mkdir()
    foreign = tmp_path / "foreign-bin"
    foreign.mkdir()
    cargo = foreign / "cargo"
    _ = cargo.write_bytes(RUST_CARGO_BYTES)
    _ = cargo.chmod(0o700)
    original = b"foreign executable must survive"
    foreign_alias = foreign / "cargo.bin"
    _ = foreign_alias.write_bytes(original)
    _ = foreign_alias.chmod(0o700)
    if alias_source == "bin-parent":
        (source / "bin").symlink_to(foreign, target_is_directory=True)
    else:
        source_bin = source / "bin"
        source_bin.mkdir()
        if alias_source == "native":
            (source_bin / "cargo").symlink_to(cargo)
        else:
            _ = (source_bin / "cargo").write_bytes(RUST_CARGO_BYTES)
            (source_bin / "cargo.bin").symlink_to(foreign_alias)
    destination = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    with pytest.raises(project.InitializationError):
        _ = project.import_rust_toolchain(
            source, destination, tool_ids=("cargo",), windows=False
        )
    assert foreign_alias.read_bytes() == original
    assert not project.rust_toolchain_import_complete(destination)


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_rust_import_alias_creation_rejects_exchanged_bin_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late physical replacement cannot receive a neutral Cargo alias."""
    source = tmp_path / "host-rust"
    (source / "bin").mkdir(parents=True)
    _ = (source / "bin/cargo").write_bytes(RUST_CARGO_BYTES)
    destination = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    bin_dir = destination / "bin"
    parked = tmp_path / "parked-bin"
    foreign = tmp_path / "foreign-bin"
    foreign.mkdir()
    _ = (foreign / "cargo").write_bytes(RUST_CARGO_BYTES)
    original_link = os.link
    swapped = False

    def exchange_before_link(
        src: str | os.PathLike[str],
        dst: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal swapped
        if not swapped and (dst == "cargo.bin" or Path(dst) == bin_dir / "cargo.bin"):
            bin_dir.rename(parked)
            foreign.rename(bin_dir)
            swapped = True
        original_link(
            src,
            dst,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", exchange_before_link)
        with pytest.raises(project.InitializationError):
            _ = project.import_rust_toolchain(
                source, destination, tool_ids=("cargo",), windows=False
            )
    assert swapped
    assert not (bin_dir / "cargo.bin").exists()
    assert not project.rust_toolchain_import_complete(destination)


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_rust_import_alias_copy_fallback_keeps_original_tool_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hardlink-restricted filesystems still import a safe executable alias."""
    source = tmp_path / "host-rust"
    (source / "bin").mkdir(parents=True)
    _ = (source / "bin/cargo").write_bytes(RUST_CARGO_BYTES)
    _ = (source / "bin/cargo").chmod(0o700)
    destination = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    native_link = os.link
    fallback_used = False

    def deny_descriptor_link(
        src: str | os.PathLike[str],
        dst: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal fallback_used
        if dst == "cargo.bin" and src_dir_fd is not None:
            fallback_used = True
            raise OSError("hardlink refused")
        native_link(
            src,
            dst,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", deny_descriptor_link)
        aliases = project.import_rust_toolchain(
            source, destination, tool_ids=("cargo",), windows=False
        )
    assert fallback_used
    alias = aliases[0]
    assert alias.read_bytes() == RUST_CARGO_BYTES
    assert alias.stat().st_mode & stat.S_IXUSR
    assert alias.stat().st_ino != (destination / "bin/cargo").stat().st_ino
    assert project.rust_toolchain_import_complete(destination)


@pytest.mark.skipif(os.name != "posix", reason="POSIX import alias identity")
@pytest.mark.parametrize(
    "transport", ["hardlink", "hardlink-restored-mtime", "copy", "copy-restored-mtime"]
)
def test_rust_import_alias_rejects_same_inode_native_tool_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, transport: str
) -> None:
    """A changed imported tool must not certify its neutral Cargo alias."""
    source = tmp_path / "host-rust"
    (source / "bin").mkdir(parents=True)
    _ = (source / "bin/cargo").write_bytes(RUST_CARGO_BYTES)
    destination = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    native = destination / "bin/cargo"
    alias = destination / "bin/cargo.bin"
    original_link = os.link
    original_status = cast(
        "Callable[[Path, int | None], os.stat_result]",
        vars(project)["_rust_import_alias_status"],
    )
    mutated = False

    def link_or_copy(  # ruff: ignore[too-many-arguments]
        source_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        if transport.startswith("copy") and destination_path == "cargo.bin":
            raise OSError("hardlink refused for neutral alias")
        original_link(
            source_path, destination_path, src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd, follow_symlinks=follow_symlinks,
        )

    def change_after_alias_observation(
        path: Path, parent_fd: int | None
    ) -> os.stat_result:
        nonlocal mutated
        result = original_status(path, parent_fd)
        if path == alias and not mutated:
            before = native.stat()
            _ = native.write_bytes(b"X" * len(RUST_CARGO_BYTES))
            changed_mtime = (
                before.st_mtime_ns if transport.endswith("restored-mtime")
                else before.st_mtime_ns + 1_000_000_000
            )
            os.utime(native, ns=(before.st_atime_ns, changed_mtime))
            mutated = True
        return result

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", link_or_copy)
        isolated.setattr(
            project, "_rust_import_alias_status", change_after_alias_observation
        )
        with pytest.raises(project.InitializationError, match="changed"):
            _ = project.import_rust_toolchain(
                source, destination, tool_ids=("cargo",), windows=False
            )
    assert mutated
    assert not project.rust_toolchain_import_complete(destination)


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_rust_import_rejects_native_leaf_replaced_before_hardlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late symlink cannot be promoted to a trusted Cargo alias."""
    source = tmp_path / "host-rust"
    (source / "bin").mkdir(parents=True)
    _ = (source / "bin/cargo").write_bytes(RUST_CARGO_BYTES)
    destination = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    external = tmp_path / "foreign-executable"
    _ = external.write_bytes(b"not a Rust tool")
    native_link = os.link
    swapped = False

    def replace_native_before_link(
        src: str | os.PathLike[str],
        dst: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal swapped
        if dst == "cargo.bin" and src_dir_fd is not None and not swapped:
            native = destination / "bin/cargo"
            native.unlink()
            native.symlink_to(external)
            swapped = True
        native_link(
            src,
            dst,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", replace_native_before_link)
        with pytest.raises(project.InitializationError):
            _ = project.import_rust_toolchain(
                source, destination, tool_ids=("cargo",), windows=False
            )
    assert swapped
    assert (destination / "bin/cargo.bin").is_symlink()
    assert external.read_bytes() == b"not a Rust tool"
    assert not project.rust_toolchain_import_complete(destination)


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_rust_import_rejects_alias_replaced_after_hardlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An injected regular alias must not gain an import-completion marker."""
    source = tmp_path / "host-rust"
    (source / "bin").mkdir(parents=True)
    _ = (source / "bin/cargo").write_bytes(RUST_CARGO_BYTES)
    destination = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    native_link = os.link
    replaced = False

    def replace_linked_alias(
        src: str | os.PathLike[str],
        dst: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal replaced
        native_link(
            src,
            dst,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )
        if dst == "cargo.bin" and dst_dir_fd is not None and not replaced:
            alias = destination / "bin/cargo.bin"
            alias.unlink()
            _ = alias.write_bytes(b"foreign executable")
            replaced = True

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", replace_linked_alias)
        with pytest.raises(project.InitializationError):
            _ = project.import_rust_toolchain(
                source, destination, tool_ids=("cargo",), windows=False
            )
    assert replaced
    assert not project.rust_toolchain_import_complete(destination)


@pytest.mark.parametrize(
    "tool_id", ["../cargo", "cargo/../cargo", "C:cargo", "cargo\\other", "NUL"]
)
def test_rust_import_rejects_nonlocal_tool_ids(
    tmp_path: Path, tool_id: str
) -> None:
    """An imported tool ID must not address a different alias or device."""
    source = tmp_path / "host-rust"
    (source / "bin").mkdir(parents=True)
    _ = (source / "bin/cargo").write_bytes(RUST_CARGO_BYTES)
    destination = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    with pytest.raises(project.InitializationError, match="path segment"):
        _ = project.import_rust_toolchain(
            source, destination, tool_ids=(tool_id,), windows=False
        )
    assert not destination.exists()
    assert not project.rust_toolchain_import_complete(destination)
    assert not (destination / "bin/cargo.bin").exists()


def test_rustup_resolver_never_queries_uninstalled_channel(
    tmp_path: Path,
) -> None:
    """Host resolver calls `which` only for channels already installed."""
    rustup = tmp_path / "rustup"
    stable_cargo = tmp_path / "stable" / "bin" / "cargo"
    stable_cargo.parent.mkdir(parents=True)
    stable_cargo.touch()
    queried: list[str] = []

    def list_runner(observed: Path) -> tuple[str, ...]:
        assert observed == rustup
        return ("1.98.1-x86_64-unknown-linux-gnu",)

    def which_runner(observed: Path, channel: str) -> str:
        assert observed == rustup
        queried.append(channel)
        return str(stable_cargo)

    resolver = project.rustup_toolchain_resolver(
        rustup,
        list_runner=list_runner,
        which_runner=which_runner,
    )

    assert resolver(RUST_CHANNEL) == stable_cargo.parent.parent
    assert resolver(RUST_NIGHTLY_CHANNEL) is None
    assert queried == [RUST_CHANNEL]


@pytest.mark.parametrize("receipt", [None, False, 1, [RUST_CHANNEL], "foreign-tuple", "foreign-item"])
def test_rustup_installed_channels_reject_foreign_inventory(
    receipt: object,
) -> None:
    """Non-native Rustup list receipts cannot authorize a channel query."""

    class ForeignTuple(tuple[str, ...]):
        pass

    class ForeignStr(str):
        @override
        def __eq__(self, _other: object) -> Never:
            raise AssertionError("foreign Rustup channel hook executed")

    if receipt == "foreign-tuple":
        inventory: object = ForeignTuple((RUST_CHANNEL,))
    elif receipt == "foreign-item":
        inventory = (ForeignStr(RUST_CHANNEL + "-forged"),)
    else:
        inventory = receipt
    assert not project.rustup_channel_is_installed(
        RUST_CHANNEL, cast("tuple[str, ...]", inventory)
    )


@pytest.mark.parametrize("receipt", [None, False, 1, [RUST_CHANNEL], "foreign-tuple", "foreign-item"])
def test_rustup_resolver_does_not_probe_foreign_installed_channels(
    tmp_path: Path, receipt: object
) -> None:
    """A forged installed-channel collection never reaches rustup `which`."""

    class ForeignTuple(tuple[str, ...]):
        pass

    class ForeignStr(str):
        @override
        def __eq__(self, _other: object) -> Never:
            raise AssertionError("foreign Rustup channel hook executed")

    if receipt == "foreign-tuple":
        inventory: object = ForeignTuple((RUST_CHANNEL,))
    elif receipt == "foreign-item":
        inventory = (ForeignStr(RUST_CHANNEL + "-forged"),)
    else:
        inventory = receipt

    def unavailable_which(_rustup: Path, _channel: str) -> Never:
        raise AssertionError("forged Rustup inventory queried channel")

    resolver = project.rustup_toolchain_resolver(
        tmp_path / "rustup",
        list_runner=lambda _path: cast("tuple[str, ...]", inventory),
        which_runner=unavailable_which,
    )
    assert resolver(RUST_CHANNEL) is None


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_rustup_resolver_tolerates_host_list_fault(
    tmp_path: Path, fault_type: type[Exception]
) -> None:
    """Optional inventory failures are missing, not fatal bootstrap errors."""
    fault = fault_type("host rustup inventory failed")

    def unavailable_list(_rustup: Path) -> Never:
        raise fault

    def forbidden_which(_rustup: Path, _channel: str) -> Never:
        raise AssertionError("list failure queried Rustup channel")

    resolver = project.rustup_toolchain_resolver(
        tmp_path / "rustup",
        list_runner=unavailable_list,
        which_runner=forbidden_which,
    )
    assert resolver(RUST_CHANNEL) is None


def test_rustup_installed_channel_match_accepts_native_host_suffix() -> None:
    """Pinned channels match installed host-qualified Rustup identities."""
    installed = (
        "1.98.1-x86_64-unknown-linux-gnu",
        "nightly-2026-07-14-x86_64-unknown-linux-gnu",
    )

    assert project.rustup_channel_is_installed(RUST_CHANNEL, installed)
    assert project.rustup_channel_is_installed(RUST_NIGHTLY_CHANNEL, installed)
    assert not project.rustup_channel_is_installed("1.98.0", installed)
    assert not project.rustup_channel_is_installed(
        "nightly-2026-07-13",
        installed,
    )


def test_rustup_toolchain_root_requires_existing_cargo_path(
    tmp_path: Path,
) -> None:
    """Rustup resolution admits only an existing native Cargo executable."""
    cargo = tmp_path / "toolchain" / "bin" / "cargo"
    cargo.parent.mkdir(parents=True)
    cargo.touch()

    rustup = tmp_path / "rustup"

    def resolve(observed_rustup: Path, channel: str) -> str:
        assert observed_rustup == rustup
        assert channel == RUST_CHANNEL
        return str(cargo)

    def resolve_missing(observed_rustup: Path, channel: str) -> str:
        assert observed_rustup == rustup
        assert channel == RUST_CHANNEL
        return str(tmp_path / "missing")

    resolved = project.rustup_toolchain_root(
        rustup,
        RUST_CHANNEL,
        runner=resolve,
    )
    missing = project.rustup_toolchain_root(
        rustup,
        RUST_CHANNEL,
        runner=resolve_missing,
    )

    assert resolved == cargo.parent.parent
    assert missing is None


@pytest.mark.parametrize(
    "case", ["wrong-name", "wrong-parent", "relative", "linked-cargo", "linked-bin"]
)
def test_rustup_toolchain_root_rejects_noncanonical_cargo_path(
    tmp_path: Path, case: str
) -> None:
    """Rustup output must identify a real Cargo inside a physical toolchain bin."""
    toolchain = tmp_path / "toolchain"
    native = toolchain / "bin/cargo"
    native.parent.mkdir(parents=True)
    _ = native.write_bytes(RUST_CARGO_BYTES)
    candidate = native
    if case == "wrong-name":
        candidate = native.with_name("rustc")
        _ = candidate.write_bytes(RUST_CARGO_BYTES)
    elif case == "wrong-parent":
        candidate = toolchain / "other/cargo"
        candidate.parent.mkdir()
        _ = candidate.write_bytes(RUST_CARGO_BYTES)
    elif case == "relative":
        candidate = Path(os.path.relpath(native))
    elif case == "linked-cargo":
        linked = native.with_name("external-cargo")
        _ = native.replace(linked)
        _ = candidate.symlink_to(linked)
    elif case == "linked-bin":
        relocated = tmp_path / "external-bin"
        _ = native.parent.replace(relocated)
        _ = native.parent.symlink_to(relocated, target_is_directory=True)

    def runner(_rustup: Path, _channel: str) -> str:
        return str(candidate)

    assert (
        project.rustup_toolchain_root(tmp_path / "rustup", RUST_CHANNEL, runner=runner)
        is None
    )


@pytest.mark.skipif(os.name != POSIX_NAME, reason="host path control receipt")
@pytest.mark.parametrize("control", ["\n", "\t", "\r"])
def test_rustup_toolchain_root_rejects_hidden_ancestor_controls(
    tmp_path: Path, control: str
) -> None:
    """A printed Rustup Cargo path cannot conceal an altered ancestor."""
    cargo = tmp_path / f"host{control}toolchain" / "bin" / "cargo"
    cargo.parent.mkdir(parents=True)
    _ = cargo.write_bytes(RUST_CARGO_BYTES)
    assert project.rustup_toolchain_root(
        tmp_path / "rustup",
        RUST_CHANNEL,
        runner=lambda _rustup, _channel: str(cargo),
    ) is None


def test_rustup_toolchain_root_accepts_native_windows_cargo_name(
    tmp_path: Path,
) -> None:
    """Rustup can report a canonical .exe binary on Windows hosts."""
    cargo = tmp_path / "windows-toolchain/bin/cargo.exe"
    cargo.parent.mkdir(parents=True)
    _ = cargo.write_bytes(RUST_CARGO_BYTES)

    def runner(_rustup: Path, _channel: str) -> str:
        return str(cargo)

    assert (
        project.rustup_toolchain_root(tmp_path / "rustup", RUST_CHANNEL, runner=runner)
        == cargo.parent.parent
    )


@pytest.mark.parametrize("probe", ["git", "rustup"])
def test_optional_host_executable_resolver_admits_native_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, probe: str
) -> None:
    """An exact native PATH result still selects a real observed tool."""
    resolved = tmp_path / "bin" / ("git" if probe == "git" else "rustup")
    resolved.parent.mkdir()
    resolved.touch()
    monkeypatch.setattr(project, "which", lambda _name: str(resolved))
    if probe == "git":
        monkeypatch.setattr(project, "_run_git_version", lambda _tool: "git version 2.55.0")
        monkeypatch.setattr(project, "_run_git_exec_path", lambda _tool: tmp_path)
        observation = project.observe_host_git(LINUX_PLATFORM)
        assert observation is not None
        assert observation.executable == resolved
        assert observation.exec_path == tmp_path
    else:
        assert project.rustup_executable(LINUX_PLATFORM, home=tmp_path) == resolved


def test_rustup_explicit_relative_home_is_pinned_to_initial_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The explicit home path stays stable when later callbacks alter cwd."""
    expected = tmp_path / "home/.cargo/bin/rustup"
    expected.parent.mkdir(parents=True)
    _ = expected.write_bytes(b"host rustup")
    monkeypatch.chdir(tmp_path)
    assert project.rustup_executable(
        LINUX_PLATFORM, home=Path("home"), search_path=False
    ) == expected


@pytest.mark.parametrize("probe", ["git", "rustup"])
@pytest.mark.parametrize("bad_path", ["relative", "control"])
def test_optional_host_executable_rejects_unstable_which_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    bad_path: str,
) -> None:
    """Optional host tool identities cannot depend on cwd or control bytes."""
    name = "git" if probe == "git" else "rustup"
    candidate = (
        f"bin/{name}" if bad_path == "relative" else str(tmp_path / f"{name}\n")
    )
    monkeypatch.setattr(project, "which", lambda _name: candidate)
    if probe == "git":
        monkeypatch.setattr(project, "_run_git_version", lambda _tool: "git version 2.55.0")
        monkeypatch.setattr(project, "_run_git_exec_path", lambda _tool: tmp_path)
        assert project.observe_host_git(LINUX_PLATFORM) is None
    else:
        assert project.rustup_executable(LINUX_PLATFORM, home=tmp_path) is None


@pytest.mark.parametrize("probe", ["git", "rustup"])
@pytest.mark.parametrize("receipt", [False, 1, "", "subclass", object()])
def test_optional_host_executable_resolver_requires_native_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    receipt: object,
) -> None:
    """A foreign or empty PATH tool result cannot select host binaries."""

    class ForeignStr(str):
        pass

    observed = ForeignStr("/usr/bin/git") if receipt == "subclass" else receipt
    monkeypatch.setattr(project, "which", lambda _name: observed)
    if probe == "git":
        assert project.observe_host_git(LINUX_PLATFORM) is None
    else:
        assert (
            project.rustup_executable(LINUX_PLATFORM, home=tmp_path)
            is None
        )


@pytest.mark.parametrize("probe", ["git", "rustup"])
@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_optional_host_executable_resolver_tolerates_host_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    fault_type: type[Exception],
) -> None:
    """An unavailable PATH resolver does not crash optional host inspection."""
    fault = fault_type("injected host PATH failure")

    def failing_which(_name: str) -> Never:
        raise fault

    monkeypatch.setattr(project, "which", failing_which)
    if probe == "git":
        assert project.observe_host_git(LINUX_PLATFORM) is None
    else:
        assert project.rustup_executable(LINUX_PLATFORM, home=tmp_path) is None


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_rustup_executable_tolerates_home_status_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A failed home-Cargo status observation is optional host absence."""
    rustup = tmp_path / ".cargo/bin/rustup"
    original = Path.is_file
    fault = fault_type("host status unavailable")

    def failing_status(path: Path) -> bool:
        if path == rustup:
            raise fault
        return original(path)

    monkeypatch.setattr(Path, "is_file", failing_status)
    assert project.rustup_executable(
        LINUX_PLATFORM, home=tmp_path, search_path=False
    ) is None


@pytest.mark.parametrize("receipt", [None, 0, 1, "", "subclass"])
def test_rustup_executable_requires_native_home_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """A false-like home Cargo path status is not host executable evidence."""
    root = tmp_path / ".cargo/bin/rustup"
    original = Path.is_file

    def status(path: Path) -> bool:
        if path == root:
            return cast("bool", receipt)
        return original(path)

    monkeypatch.setattr(Path, "is_file", status)
    assert project.rustup_executable(
        LINUX_PLATFORM, home=tmp_path, search_path=False
    ) is None


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_rustup_toolchain_resolver_tolerates_host_fault(
    tmp_path: Path, fault_type: type[Exception]
) -> None:
    """A failed optional Rustup channel probe cannot crash the checkout."""
    fault = fault_type("host rustup which failed")

    def failing_runner(_rustup: Path, _channel: str) -> Never:
        raise fault

    assert project.rustup_toolchain_root(
        tmp_path / "rustup", RUST_CHANNEL, runner=failing_runner
    ) is None


@pytest.mark.parametrize("receipt", [False, 1, "", "subclass", object()])
def test_rustup_toolchain_resolver_rejects_nonnative_path_output(
    tmp_path: Path, receipt: object
) -> None:
    """Injected Rustup `which` output must be a native nonempty string."""

    class ForeignStr(str):
        pass

    cargo = tmp_path / "host/bin/cargo"
    cargo.parent.mkdir(parents=True)
    cargo.touch()
    observed = ForeignStr(str(cargo)) if receipt == "subclass" else receipt
    assert (
        project.rustup_toolchain_root(
            tmp_path / "rustup",
            RUST_CHANNEL,
            runner=lambda _exe, _channel: cast("str", observed),
        )
        is None
    )


def test_rustup_executable_finds_home_cargo_bin_without_path(
    tmp_path: Path,
) -> None:
    """Bootstrap can find Rustup in Cargo home without ambient PATH support."""
    rustup = tmp_path / ".cargo" / "bin" / "rustup"
    rustup.parent.mkdir(parents=True)
    rustup.touch()

    resolved = project.rustup_executable(
        LINUX_PLATFORM,
        home=tmp_path,
        search_path=False,
    )

    assert resolved == rustup


def test_rust_import_orchestration_materializes_stable_and_nightly(
    tmp_path: Path,
) -> None:
    """One host resolver imports the pinned stable and validation channels."""
    _ = _write_rust_manifest(tmp_path)
    sources = tmp_path / "host-rustup"
    stable = sources / RUST_CHANNEL
    nightly = sources / RUST_NIGHTLY_CHANNEL
    for source, tools in (
        (stable, ("cargo", "rustc")),
        (nightly, ("cargo-clippy", "cargo-fmt", "rustc")),
    ):
        source_bin = source / "bin"
        source_bin.mkdir(parents=True)
        for tool in tools:
            path = source_bin / tool
            _ = path.write_text(tool, encoding="ascii")
            _ = path.chmod(path.stat().st_mode | stat.S_IXUSR)
        (source / "lib/rustlib").mkdir(parents=True)

    def resolve(channel: str) -> Path | None:
        sources_by_channel = {
            RUST_CHANNEL: stable,
            RUST_NIGHTLY_CHANNEL: nightly,
        }
        return sources_by_channel.get(channel)

    imported = project.import_installed_rust_toolchains(
        tmp_path,
        LINUX_PLATFORM,
        resolver=resolve,
    )

    stable_root = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    nightly_root = tmp_path / ".dependencies/rust" / RUST_NIGHTLY_CHANNEL
    assert imported == (stable_root, nightly_root)
    assert (stable_root / "bin/cargo.bin").is_file()
    assert (stable_root / "bin/rustc.bin").is_file()
    assert (nightly_root / "bin/cargo-clippy.bin").is_file()
    assert (nightly_root / "bin/cargo-fmt.bin").is_file()
    assert project.rust_toolchain_import_complete(stable_root)
    assert project.rust_toolchain_import_complete(nightly_root)


def test_rust_import_orchestration_backfills_stable_rustc_alias(
    tmp_path: Path,
) -> None:
    """Completed stable imports gain the compiler alias without reimporting."""
    _ = _write_rust_manifest(tmp_path)
    stable_root = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    stable_bin = stable_root / "bin"
    stable_bin.mkdir(parents=True)
    cargo = stable_bin / "cargo"
    rustc = stable_bin / "rustc"
    _ = cargo.write_bytes(RUST_CARGO_BYTES)
    _ = rustc.write_bytes(RUST_RUSTC_BYTES)
    _ = (stable_bin / "cargo.bin").write_bytes(RUST_CARGO_BYTES)
    _ = (stable_root / project.RUST_IMPORT_MARKER).write_text(
        "malbolge-rust-toolchain-import/v1\n",
        encoding="ascii",
    )

    def resolve(channel: str) -> Path | None:
        assert channel == RUST_NIGHTLY_CHANNEL
        return None

    imported = project.import_installed_rust_toolchains(
        tmp_path,
        LINUX_PLATFORM,
        resolver=resolve,
    )

    assert imported == (stable_root,)
    assert (stable_bin / "rustc.bin").read_bytes() == RUST_RUSTC_BYTES


def test_rust_inspection_requires_completed_neutral_alias(
    tmp_path: Path,
) -> None:
    """Completed imported Cargo is host-neutral readiness evidence."""
    _ = _write_rust_manifest(tmp_path)
    toolchain = tmp_path / ".dependencies" / "rust" / RUST_CHANNEL
    cargo = toolchain / "bin" / "cargo.bin"
    cargo.parent.mkdir(parents=True)
    cargo.touch()
    cargo.chmod(0o700)
    _ = (toolchain / project.RUST_IMPORT_MARKER).write_text(
        "malbolge-rust-toolchain-import/v1\n",
        encoding="ascii",
    )

    linux_before_linker = project.inspect_rust(tmp_path, LINUX_PLATFORM)
    windows = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)
    linker = toolchain / "bin" / "cc"
    _ = linker.write_text(
        '#!/bin/sh\nexec /usr/bin/cc "$@"\n', encoding="ascii"
    )
    linker.chmod(0o700)
    linux_before_marker = project.inspect_rust(tmp_path, LINUX_PLATFORM)
    _ = (toolchain / project.RUST_LINUX_ADAPTER_MARKER).write_text(
        "malbolge-rust-linux-adapter/v1\n",
        encoding="ascii",
    )
    linux = project.inspect_rust(tmp_path, LINUX_PLATFORM)

    assert linux_before_linker.state is project.ComponentState.MISSING
    assert linux_before_marker.state is project.ComponentState.MISSING
    assert windows.state is project.ComponentState.READY
    assert windows.path == cargo
    assert linux.state is project.ComponentState.READY
    assert linux.path == cargo


def _linux_rust_inspection_tree(tmp_path: Path) -> Path:
    """Construct a ready synthetic Linux Rust toolchain for mutation tests.

    Returns:
        The version-pinned imported toolchain directory.

    """
    _ = _write_rust_manifest(tmp_path)
    toolchain = tmp_path / ".dependencies/rust" / RUST_CHANNEL
    binary = toolchain / "bin"
    binary.mkdir(parents=True)
    cargo = binary / "cargo.bin"
    _ = cargo.write_bytes(RUST_CARGO_BYTES)
    cargo.chmod(0o700)
    _ = (toolchain / project.RUST_IMPORT_MARKER).write_text(
        "malbolge-rust-toolchain-import/v1\n", encoding="ascii"
    )
    linker = binary / "cc"
    _ = linker.write_text(
        '#!/bin/sh\nexec /usr/bin/cc "$@"\n', encoding="ascii"
    )
    linker.chmod(0o700)
    _ = (toolchain / project.RUST_LINUX_ADAPTER_MARKER).write_text(
        "malbolge-rust-linux-adapter/v1\n", encoding="ascii"
    )
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.READY
    )
    return toolchain


def test_rust_inspection_rejects_nonexecutable_cargo_alias(
    tmp_path: Path,
) -> None:
    """A physical but nonexecutable Linux Cargo shim is not ready."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    cargo = toolchain / "bin/cargo.bin"
    cargo.chmod(0o600)
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )
    assert (
        project.inspect_rust(tmp_path, WINDOWS_PLATFORM).state
        is project.ComponentState.READY
    )


@pytest.mark.parametrize("receipt", [False, 1])
def test_rust_inspection_requires_native_cargo_execute_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """A false or nonboolean Cargo execute check cannot attest Linux readiness."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    cargo = toolchain / "bin/cargo.bin"
    native_access = os.access

    def access(path: str | os.PathLike[str], mode: int) -> bool:
        if Path(path) == cargo and mode == os.X_OK:
            return cast("bool", receipt)
        return native_access(path, mode)

    monkeypatch.setattr(os, "access", access)
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_rejects_linked_cargo_alias(tmp_path: Path) -> None:
    """A redirected Cargo binary cannot complete a pinned Rust import."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    cargo = toolchain / "bin/cargo.bin"
    outside = tmp_path / "outside-cargo"
    _ = outside.write_bytes(RUST_CARGO_BYTES)
    cargo.unlink()
    try:
        cargo.symlink_to(outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")

    assert (
        project.inspect_rust(tmp_path, WINDOWS_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_rejects_linked_cargo_parent(tmp_path: Path) -> None:
    """Rust import readiness must not follow a linked Cargo directory."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    binary = toolchain / "bin"
    relocated = tmp_path / "outside-bin"
    _ = binary.replace(relocated)
    try:
        binary.symlink_to(relocated, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory symlinks unavailable: {error}")

    assert (
        project.inspect_rust(tmp_path, WINDOWS_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_does_not_trust_forged_cargo_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fake Path.is_file receipt cannot replace physical Cargo evidence."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    cargo = toolchain / "bin/cargo.bin"
    cargo.unlink()
    original = Path.is_file

    def fake_is_file(path: Path) -> bool:
        return True if path == cargo else original(path)

    monkeypatch.setattr(Path, "is_file", fake_is_file)
    assert (
        project.inspect_rust(tmp_path, WINDOWS_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_rejects_foreign_cargo_lstat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A nonnative lstat receipt cannot attest an imported Cargo binary."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    cargo = toolchain / "bin/cargo.bin"
    original = Path.lstat

    def foreign_lstat(path: Path) -> os.stat_result:
        if path == cargo:
            return cast("os.stat_result", object())
        return original(path)

    monkeypatch.setattr(Path, "lstat", foreign_lstat)
    assert (
        project.inspect_rust(tmp_path, WINDOWS_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_accepts_hardlinked_native_cargo(tmp_path: Path) -> None:
    """The copied Rust import may hardlink its neutral and native executables."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    cargo = toolchain / "bin/cargo.bin"
    try:
        os.link(cargo, toolchain / "bin/cargo")
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hardlinks unavailable: {error}")

    assert (
        project.inspect_rust(tmp_path, WINDOWS_PLATFORM).state
        is project.ComponentState.READY
    )


def test_rust_inspection_rejects_wrong_linux_adapter_marker(
    tmp_path: Path,
) -> None:
    """An unrelated marker cannot authorize Linux linker readiness."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    _ = (toolchain / project.RUST_LINUX_ADAPTER_MARKER).write_text(
        "other-adapter/v1\n", encoding="ascii"
    )
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_rejects_linked_linux_adapter_marker(
    tmp_path: Path,
) -> None:
    """Matching adapter marker bytes behind a symlink are not evidence."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    marker = toolchain / project.RUST_LINUX_ADAPTER_MARKER
    relocated = marker.with_name("actual-adapter-marker")
    _ = marker.replace(relocated)
    try:
        _ = marker.symlink_to(relocated)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


@pytest.mark.parametrize("artifact", ["marker", "launcher"])
def test_rust_inspection_rejects_hardlinked_linux_adapter_artifact(
    tmp_path: Path, artifact: str
) -> None:
    """A shared adapter inode cannot prove exclusive bootstrap readiness."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    selected = (
        toolchain / project.RUST_LINUX_ADAPTER_MARKER
        if artifact == "marker"
        else toolchain / "bin/cc"
    )
    outside = tmp_path / "outside-adapter"
    try:
        os.link(selected, outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hardlinks unavailable: {error}")
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


@pytest.mark.parametrize("mutation", ["hardlink", "same-content-swap"])
def test_rust_inspection_rejects_linker_mutated_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    """Readiness must bind linker metadata across its content observation."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    linker = toolchain / "bin/cc"
    outside = tmp_path / "outside-cc"
    native_read = project._read_authority_bytes  # pyright: ignore[reportPrivateUsage]
    mutated = False

    def mutate_after_read(path: Path) -> bytes:
        nonlocal mutated
        content = native_read(path)
        if path == linker and not mutated:
            mutated = True
            if mutation == "hardlink":
                os.link(linker, outside)
            else:
                _ = linker.replace(outside)
                replacement = tmp_path / "replacement-cc"
                _ = replacement.write_bytes(content)
                replacement.chmod(0o700)
                _ = replacement.replace(linker)
        return content

    with monkeypatch.context() as isolated:
        isolated.setattr(project, "_read_authority_bytes", mutate_after_read)
        assert (
            project.inspect_rust(tmp_path, LINUX_PLATFORM).state
            is project.ComponentState.MISSING
        )
    assert mutated
    assert outside.read_bytes().startswith(b"#!/bin/sh")


def test_rust_inspection_rejects_linked_linux_adapter_executable(
    tmp_path: Path,
) -> None:
    """An aliased cc launcher cannot masquerade as imported linker glue."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    cc = toolchain / "bin/cc"
    real = cc.with_name("real-cc")
    _ = cc.replace(real)
    try:
        _ = cc.symlink_to(real)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_requires_executable_linux_adapter(
    tmp_path: Path,
) -> None:
    """A nonexecutable cc path is not a ready linker adapter."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    cc = toolchain / "bin/cc"
    cc.chmod(0o600)
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


@pytest.mark.parametrize("receipt", [True, 1])
def test_rust_inspection_rejects_forged_linker_execute_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """An unexecutable adapter cannot be approved by forged access checks."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    linker = toolchain / "bin/cc"
    if receipt is True:
        linker.chmod(0o600)
    native_access = os.access

    def forged_access(path: str | os.PathLike[str], mode: int) -> bool:
        if Path(path) == linker and mode == os.X_OK:
            return cast("bool", receipt)
        return native_access(path, mode)

    monkeypatch.setattr(os, "access", forged_access)
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_rejects_nonadapter_linker_script(
    tmp_path: Path,
) -> None:
    """An arbitrary executable script is not a pinned Linux linker shim."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    _ = (toolchain / "bin/cc").write_text(
        "#!/bin/sh\nexit 0\n", encoding="ascii"
    )
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_rejects_fifo_linux_adapter_marker(
    tmp_path: Path,
) -> None:
    """A pipe cannot become ready by waiting for an external writer."""
    mkfifo = cast("Callable[[Path], None] | None", getattr(os, "mkfifo", None))
    if mkfifo is None:
        pytest.skip("FIFO unsupported")
    toolchain = _linux_rust_inspection_tree(tmp_path)
    marker = toolchain / project.RUST_LINUX_ADAPTER_MARKER
    marker.unlink()
    mkfifo(marker)
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_rejects_replaced_linux_adapter_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-byte inode swap invalidates the admitted marker snapshot."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    marker = toolchain / project.RUST_LINUX_ADAPTER_MARKER
    replacement = marker.with_name("replacement-marker")
    _ = replacement.write_bytes(marker.read_bytes())
    original_open = os.open

    def swap_before_open(path: Path, flags: int) -> int:
        if path == marker:
            _ = replacement.replace(marker)
        return original_open(path, flags)

    monkeypatch.setattr(os, "open", swap_before_open)
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_rejects_linked_adapter_directory(
    tmp_path: Path,
) -> None:
    """All native launcher ancestors must stay within the physical tree."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    binary = toolchain / "bin"
    real = binary.with_name("physical-bin")
    _ = binary.replace(real)
    try:
        _ = binary.symlink_to(real, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_rejects_oversized_adapter_marker(
    tmp_path: Path,
) -> None:
    """Sparse, excessive marker bytes cannot be admitted as ready."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    marker = toolchain / project.RUST_LINUX_ADAPTER_MARKER
    with marker.open("wb") as stream:
        _ = stream.truncate(project.MAX_AUTHORITY_BYTES + 1)
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_rejects_embedded_linker_commands(
    tmp_path: Path,
) -> None:
    """Linker shims must be the generated two-line direct-exec form."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    _ = (toolchain / "bin/cc").write_text(
        '#!/bin/sh\nexec /usr/bin/cc\necho unexpected "$@"\n',
        encoding="ascii",
    )
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


@pytest.mark.parametrize(
    "command",
    [
        '/usr/bin/cc; touch /tmp/hijack',
        '/usr/bin/cc && touch /tmp/hijack',
        '$(touch /tmp/hijack)',
        '/usr/bin/cc $(touch /tmp/hijack)',
        '/usr/bin/cc | tee /tmp/hijack',
        '/usr/bin/cc > /tmp/hijack',
        '/usr/bin/cc # harmless-looking comment',
        '/usr/bin/cc\\evil',
        '/usr/bin/cc ;',
        'sh -c hacked',
    ],
)
def test_rust_inspection_rejects_shell_linker_injection(
    tmp_path: Path, command: str
) -> None:
    """A plausible two-line linker shim cannot include other shell work."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    linker = toolchain / "bin/cc"
    _ = linker.write_text(f'#!/bin/sh\nexec {command} "$@"\n', encoding="ascii")
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_rust_inspection_accepts_canonically_quoted_linker_path(
    tmp_path: Path
) -> None:
    """Generated linker shims may safely quote an absolute path with spaces."""
    toolchain = _linux_rust_inspection_tree(tmp_path)
    linker = toolchain / "bin/cc"
    _ = linker.write_text(
        "#!/bin/sh\nexec '/opt/vendor toolchain/bin/cc' \"$@\"\n",
        encoding="ascii",
    )
    assert (
        project.inspect_rust(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.READY
    )


def test_git_version_match_accepts_portable_and_windows_distribution() -> None:
    """Portable Git version accepts exact upstream and distribution suffixes."""
    assert project.git_version_line_matches(GIT_VERSION, "git version 2.55.0")
    assert project.git_version_line_matches(
        GIT_VERSION,
        "git version 2.55.0.windows.1",
    )
    assert not project.git_version_line_matches(
        GIT_VERSION,
        "git version 2.54.0.windows.1",
    )


@pytest.mark.parametrize(
    "suffix",
    [
        "forged",
        "windowsX.1",
        "windows.01",
        "windows.0",
        "windows.1x",
        "windows.+1",
        "windows.1.rc1",
        "windows.1-unsafe",
    ],
)
def test_host_git_version_rejects_unpinned_distribution_suffix(
    suffix: str,
) -> None:
    """Only Git for Windows release revisions may extend a pinned Git version."""
    assert not project.git_version_line_matches(
        GIT_VERSION, f"git version {GIT_VERSION}.{suffix}"
    )


def test_host_git_version_accepts_later_windows_distribution_revision() -> None:
    """A Windows-specific packaging revision keeps the same upstream Git pin."""
    assert project.git_version_line_matches(GIT_VERSION, "git version 2.55.0.windows.17")


@pytest.mark.parametrize(
    "banner",
    [
        "git version 2.55.0.windows.1\nunexpected diagnostic",
        "git version 2.55.0.windows.1 extra text",
        "git version 2.55.0.windows..1",
        "git version 2.55.0.windows/1",
        "git version 2.55.0.windows:1",
        "git version 2.55.0.windows.1\x00",
        "git version 2.55.0.windows.1\rforged",
        "git version 2.55.0.λ",
        "git version 2.55.0.",
    ],
)
def test_host_git_version_match_rejects_noncanonical_banners(
    banner: str,
) -> None:
    """A pinned Git version cannot be certified by an injected suffix."""
    assert not project.git_version_line_matches(GIT_VERSION, banner)


def test_host_git_import_requires_matching_version_and_exec_path(
    tmp_path: Path,
) -> None:
    """Host Git becomes repository authority only with matching runtime data."""
    versions = tmp_path / ".jig/settings/versions.toml"
    versions.parent.mkdir(parents=True)
    _ = versions.write_text(
        '[authority.git]\ncurrent = "2.55.0"\n',
        encoding="utf-8",
    )
    git = tmp_path / "host/bin/git"
    exec_path = tmp_path / "host/libexec/git-core"
    git.parent.mkdir(parents=True)
    exec_path.mkdir(parents=True)
    _ = git.write_bytes(GIT_BYTES)
    _ = git.chmod(git.stat().st_mode | stat.S_IXUSR)
    _ = (exec_path / "git-remote-http").write_bytes(GIT_HELPER_BYTES)

    observation = project.GitHostObservation(
        executable=git,
        exec_path=exec_path,
        version_line="git version 2.55.0",
    )
    alias = project.import_host_git(
        tmp_path,
        LINUX_PLATFORM,
        observation,
    )

    expected = tmp_path / ".dependencies/git/2.55.0/bin/git.bin"
    assert alias == expected
    assert project.git_import_complete(expected.parent.parent)


@pytest.mark.parametrize("mutation", ["alias-link", "bin-link", "forged-is-file"])
def test_completed_git_import_rejects_unowned_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    """Valid marker bytes cannot authorize a redirected or nonexistent Git."""
    versions = tmp_path / ".jig/settings/versions.toml"
    versions.parent.mkdir(parents=True)
    _ = versions.write_text(
        '[authority.git]\ncurrent = "2.55.0"\n', encoding="utf-8"
    )
    destination = tmp_path / ".dependencies/git" / GIT_VERSION
    destination.mkdir(parents=True)
    _ = (destination / project.GIT_IMPORT_MARKER).write_bytes(GIT_MARKER_BYTES)
    external = tmp_path / "external-git"
    _ = external.write_bytes(GIT_BYTES)
    alias = destination / "bin/git.bin"
    if mutation == "bin-link":
        foreign_bin = tmp_path / "foreign-bin"
        foreign_bin.mkdir()
        _ = (foreign_bin / "git.bin").write_bytes(GIT_BYTES)
        try:
            alias.parent.symlink_to(foreign_bin, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"symlinks unavailable: {error}")
    else:
        alias.parent.mkdir()
        if mutation == "alias-link":
            try:
                alias.symlink_to(external)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"symlinks unavailable: {error}")
        else:
            native_is_file = Path.is_file

            def forged_is_file(path: Path) -> bool:
                return True if path == alias else native_is_file(path)

            monkeypatch.setattr(Path, "is_file", forged_is_file)
    observation = project.GitHostObservation(
        executable=external,
        exec_path=tmp_path,
        version_line="git version 2.55.0",
    )
    with pytest.raises(project.InitializationError, match="incomplete Git import"):
        _ = project.import_host_git(tmp_path, LINUX_PLATFORM, observation)
    assert external.read_bytes() == GIT_BYTES


@pytest.mark.parametrize("platform_id", [LINUX_PLATFORM, WINDOWS_PLATFORM])
@pytest.mark.parametrize("mutation", ["missing", "linked"])
def test_completed_git_import_requires_physical_helper_tree(
    tmp_path: Path, platform_id: str, mutation: str
) -> None:
    """Marker and alias alone cannot certify a missing or redirected Git runtime."""
    versions = tmp_path / ".jig/settings/versions.toml"
    versions.parent.mkdir(parents=True)
    _ = versions.write_text(
        '[authority.git]\ncurrent = "2.55.0"\n', encoding="utf-8"
    )
    destination = tmp_path / ".dependencies/git" / GIT_VERSION
    alias = destination / "bin/git.bin"
    alias.parent.mkdir(parents=True)
    _ = alias.write_bytes(GIT_BYTES)
    alias.chmod(0o700)
    _ = (destination / project.GIT_IMPORT_MARKER).write_bytes(GIT_MARKER_BYTES)
    helper_tree = destination / "libexec/git-core"
    if mutation == "linked":
        outside = tmp_path / "outside-git-core"
        outside.mkdir()
        helper_tree.parent.mkdir()
        try:
            _ = helper_tree.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"symlinks unavailable: {error}")
    observation = project.GitHostObservation(
        executable=tmp_path / "unused-git",
        exec_path=tmp_path,
        version_line=f"git version {GIT_VERSION}",
    )
    with pytest.raises(project.InitializationError, match="incomplete Git import"):
        _ = project.import_host_git(tmp_path, platform_id, observation)


@pytest.mark.parametrize("platform_id", [LINUX_PLATFORM, WINDOWS_PLATFORM])
def test_completed_git_import_rejects_nonexecutable_posix_alias(
    tmp_path: Path, platform_id: str
) -> None:
    """POSIX requires executable Git; Windows keeps native mode semantics."""
    versions = tmp_path / ".jig/settings/versions.toml"
    versions.parent.mkdir(parents=True)
    _ = versions.write_text(
        '[authority.git]\ncurrent = "2.55.0"\n', encoding="utf-8"
    )
    destination = tmp_path / ".dependencies/git" / GIT_VERSION
    binary = destination / "bin"
    binary.mkdir(parents=True)
    alias = binary / "git.bin"
    _ = alias.write_bytes(GIT_BYTES)
    alias.chmod(0o600)
    _ = (destination / project.GIT_IMPORT_MARKER).write_bytes(GIT_MARKER_BYTES)
    (destination / "libexec/git-core").mkdir(parents=True)
    observation = project.GitHostObservation(
        executable=tmp_path / "unused-git",
        exec_path=tmp_path,
        version_line=f"git version {GIT_VERSION}",
    )
    if platform_id == WINDOWS_PLATFORM:
        assert project.import_host_git(tmp_path, platform_id, observation) == alias
    else:
        with pytest.raises(project.InitializationError, match="incomplete Git import"):
            _ = project.import_host_git(tmp_path, platform_id, observation)


def test_portable_import_link_or_copy_rejects_symlink_source(
    tmp_path: Path,
) -> None:
    """A host symlink cannot be installed as a trusted imported binary."""
    outside = tmp_path / "outside"
    _ = outside.write_bytes(b"foreign content")
    source = tmp_path / "host-git"
    try:
        _ = source.symlink_to(outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    target = tmp_path / "git.bin"
    with pytest.raises(project.InitializationError, match="source.*physical"):
        _ = project._link_or_copy(  # pyright: ignore[reportPrivateUsage]
            str(source), str(target)
        )
    assert not target.exists()
    assert outside.read_bytes() == b"foreign content"


def test_portable_import_link_or_copy_rejects_forged_successful_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A positive host link result cannot substitute a foreign output inode."""
    source = tmp_path / "host-git"
    _ = source.write_bytes(GIT_BYTES)
    target = tmp_path / "git.bin"
    injected = False

    def substitute_link(
        _source: str, destination: str, **_kwargs: object
    ) -> None:
        nonlocal injected
        injected = True
        _ = Path(destination).write_bytes(b"untrusted")

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", substitute_link)
        with pytest.raises(project.InitializationError, match="link receipt"):
            _ = project._link_or_copy(  # pyright: ignore[reportPrivateUsage]
            str(source), str(target)
        )
    assert injected
    assert target.read_bytes() == b"untrusted"
    assert source.read_bytes() == GIT_BYTES


@pytest.mark.skipif(os.name != POSIX_NAME, reason="requires native hardlinks")
@pytest.mark.parametrize("pathway", ["portable", "posix"])
def test_git_import_link_rejects_same_inode_mutation_with_restored_mtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pathway: str,
) -> None:
    """A same-inode rewrite must not pass a hardlink's physical receipt."""
    source = tmp_path / "host-git"
    _ = source.write_bytes(GIT_BYTES)
    target = tmp_path / "git.bin"
    native_link = os.link
    mutated = False

    def link_then_mutate(
        source_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal mutated
        native_link(
            source_path,
            destination_path,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )
        before = source.stat()
        _ = source.write_bytes(b"X" * len(GIT_BYTES))
        os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
        mutated = True

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", link_then_mutate)
        with pytest.raises(project.InitializationError, match="link|changed"):
            if pathway == "portable":
                _ = project._link_or_copy(  # pyright: ignore[reportPrivateUsage]
                    str(source), str(target)
                )
            else:
                parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    project._copy_import_file_at_parent(  # pyright: ignore[reportPrivateUsage]
                        source, target, parent_fd
                    )
                finally:
                    os.close(parent_fd)
    assert mutated
    assert source.read_bytes() == b"X" * len(GIT_BYTES)


@pytest.mark.skipif(
    os.name != POSIX_NAME, reason="requires pinned POSIX file descriptors"
)
@pytest.mark.parametrize("pathway", ["portable", "posix"])
def test_git_import_link_rejects_digest_close_rewrite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pathway: str,
) -> None:
    """Close of the last source hash handle cannot authorize changed bytes."""
    source = tmp_path / "host-git"
    _ = source.write_bytes(GIT_BYTES)
    target = tmp_path / "git.bin"
    source_status = source.stat()
    native_close = os.close
    source_closes = 0
    mutated = False

    def mutate_after_second_source_close(fd: int) -> None:
        nonlocal source_closes, mutated
        current = os.fstat(fd)
        is_source = (current.st_dev, current.st_ino) == (
            source_status.st_dev,
            source_status.st_ino,
        )
        native_close(fd)
        if is_source:
            source_closes += 1
        if is_source and source_closes == 2:
            before = source.stat()
            _ = source.write_bytes(b"X" * len(GIT_BYTES))
            os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
            mutated = True

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "close", mutate_after_second_source_close)
        with pytest.raises(project.InitializationError, match="changed|digest|link"):
            if pathway == "portable":
                _ = project._link_or_copy(  # pyright: ignore[reportPrivateUsage]
                    str(source), str(target)
                )
            else:
                parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    project._copy_import_file_at_parent(  # pyright: ignore[reportPrivateUsage]
                        source, target, parent_fd
                    )
                finally:
                    native_close(parent_fd)
    assert mutated
    assert source_closes == 2
    assert source.read_bytes() == b"X" * len(GIT_BYTES)


@pytest.mark.skipif(os.name != POSIX_NAME, reason="requires POSIX write descriptors")
@pytest.mark.parametrize("pathway", ["portable", "posix"])
def test_git_import_copy_rejects_corrupted_complete_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    pathway: str,
) -> None:
    """A same-size destination rewrite must not certify a fallback copy."""
    source = tmp_path / "host-git"
    _ = source.write_bytes(GIT_BYTES)
    target = tmp_path / "git.bin"
    native_copy = project._write_import_file_payload
    corrupted = False

    def deny_link(*_args: object, **_kwargs: object) -> None:
        raise OSError("host does not support hardlinks")

    def copy_then_corrupt(input_fd: int, output_fd: int) -> None:
        nonlocal corrupted
        native_copy(input_fd, output_fd)
        _ = os.pwrite(output_fd, b"X" * len(GIT_BYTES), 0)
        corrupted = True

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", deny_link)
        isolated.setattr(project, "_write_import_file_payload", copy_then_corrupt)
        with pytest.raises(project.InitializationError, match="changed|content|digest"):
            if pathway == "portable":
                _ = project._link_or_copy(  # pyright: ignore[reportPrivateUsage]
                    str(source), str(target)
                )
            else:
                parent_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    project._copy_import_file_at_parent(  # pyright: ignore[reportPrivateUsage]
                        source, target, parent_fd
                    )
                finally:
                    os.close(parent_fd)
    assert corrupted
    assert source.read_bytes() == GIT_BYTES
    assert target.read_bytes() == b"X" * len(GIT_BYTES)


@pytest.mark.parametrize("substitution", ["symlink", "file-swap"])
def test_portable_import_copy_fallback_rejects_substituted_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    substitution: str,
) -> None:
    """A fallback copy cannot follow a source replaced after hardlink denial."""
    source = tmp_path / "host-git"
    _ = source.write_bytes(GIT_BYTES)
    parked = tmp_path / "parked-git"
    outside = tmp_path / "outside-git"
    _ = outside.write_bytes(b"untrusted-host-binary")
    destination = tmp_path / "git.bin"
    swapped = False

    def deny_and_swap(
        _source: str, _destination: str, **_kwargs: object
    ) -> None:
        nonlocal swapped
        if not swapped:
            swapped = True
            _ = source.rename(parked)
            if substitution == "symlink":
                _ = source.symlink_to(outside)
            else:
                _ = outside.rename(source)
        raise OSError("hardlinks not permitted")

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", deny_and_swap)
        with pytest.raises(project.InitializationError, match="source changed"):
            _ = project._link_or_copy(  # pyright: ignore[reportPrivateUsage]
                str(source), str(destination)
            )
    assert swapped
    assert parked.read_bytes() == GIT_BYTES
    assert not destination.exists()
    if substitution == "symlink":
        assert outside.read_bytes() == b"untrusted-host-binary"
    else:
        assert source.read_bytes() == b"untrusted-host-binary"


def test_portable_import_copy_fallback_keeps_physical_source_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No-hardlink hosts still copy trusted bytes and executable mode."""
    source = tmp_path / "host-git"
    _ = source.write_bytes(GIT_BYTES)
    source.chmod(0o700)
    destination = tmp_path / "git.bin"

    def deny_link(_source: str, _destination: str, **_kwargs: object) -> None:
        raise OSError("host lacks hardlink support")

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", deny_link)
        assert project._link_or_copy(  # pyright: ignore[reportPrivateUsage]
            str(source), str(destination)
        ) == str(destination)
    assert destination.read_bytes() == GIT_BYTES
    assert stat.S_IMODE(destination.stat().st_mode) == 0o700


@pytest.mark.parametrize("attack", ["foreign-handle", "name-swap"])
def test_portable_import_fallback_rejects_foreign_named_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, attack: str
) -> None:
    """A copied file must still be the named owned destination at return."""
    source = tmp_path / "host-git"
    _ = source.write_bytes(GIT_BYTES)
    destination = tmp_path / "git.bin"
    outside = tmp_path / "foreign-file"
    _ = outside.write_bytes(b"?" * len(GIT_BYTES))
    parked = tmp_path / "parked-output"
    native_open = Path.open
    native_write = project._write_import_file_payload
    injected = False

    def reject_hardlinks(_source: str, _destination: str) -> None:
        raise OSError("hardlinks prohibited")

    def redirect_output(
        path: Path, mode: str = "r", *args: object, **kwargs: object
    ) -> BinaryIO:
        nonlocal injected
        if path == destination and mode == "xb" and attack == "foreign-handle":
            injected = True
            return native_open(outside, "r+b")
        return native_open(path, mode, *args, **kwargs)

    def replace_after_write(input_fd: int, output_fd: int) -> None:
        nonlocal injected
        native_write(input_fd, output_fd)
        if attack == "name-swap":
            injected = True
            _ = destination.rename(parked)
            _ = destination.write_bytes(b"?" * len(GIT_BYTES))

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", reject_hardlinks)
        isolated.setattr(Path, "open", redirect_output)
        isolated.setattr(
            project, "_write_import_file_payload", replace_after_write
        )
        with pytest.raises(
            project.InitializationError, match="copy fallback output"
        ):
            _ = project._link_or_copy(  # pyright: ignore[reportPrivateUsage]
                str(source), str(destination)
            )
    assert injected
    assert source.read_bytes() == GIT_BYTES
    if attack == "foreign-handle":
        assert not destination.exists()
        assert outside.read_bytes() == b"?" * len(GIT_BYTES)
    else:
        assert destination.read_bytes() == b"?" * len(GIT_BYTES)
        assert parked.read_bytes() == GIT_BYTES


@pytest.mark.skipif(os.name != POSIX_NAME, reason="requires POSIX import root")
@pytest.mark.parametrize("component", ["git", "rust"])
def test_native_toolchain_import_rejects_marker_drift_during_root_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    component: str,
) -> None:
    """A root-descriptor close callback cannot complete a corrupt import."""
    destination = tmp_path / "installed" / component
    name = (
        project.GIT_IMPORT_MARKER if component == "git" else project.RUST_IMPORT_MARKER
    )
    marker = destination / name
    native_close = project._close_local_state_parent
    mutated = False

    def change_marker_on_root_close(fd: int) -> None:
        nonlocal mutated
        original = os.fstat(fd)
        is_root = (
            marker.exists()
            and not mutated
            and (original.st_dev, original.st_ino)
            == (destination.lstat().st_dev, destination.lstat().st_ino)
        )
        native_close(fd)
        if is_root:
            _ = marker.write_bytes(b"X" * marker.stat().st_size)
            mutated = True

    if component == "git":
        source = tmp_path / "host-git"
        _ = source.write_bytes(GIT_BYTES)
        source.chmod(0o700)
        helpers = tmp_path / "host-git-core"
        helpers.mkdir()
    else:
        source = _make_rust_import_source(tmp_path)

    with monkeypatch.context() as isolated:
        isolated.setattr(
            project, "_close_local_state_parent", change_marker_on_root_close
        )
        with pytest.raises(project.InitializationError, match="marker.*changed"):
            if component == "git":
                _ = project.import_git_installation(
                    source, helpers, destination, windows=False
                )
            else:
                _ = project.import_rust_toolchain(
                    source, destination, tool_ids=("cargo",), windows=False
                )
    assert mutated
    assert marker.read_bytes().startswith(b"X")


def test_git_import_preserves_runtime_tree_and_neutral_alias(
    tmp_path: Path,
) -> None:
    """Imported Git keeps helpers beside one platform-neutral Jig alias."""
    git = tmp_path / "host" / "bin" / "git"
    exec_path = tmp_path / "host" / "libexec" / "git-core"
    git.parent.mkdir(parents=True)
    exec_path.mkdir(parents=True)
    _ = git.write_bytes(GIT_BYTES)
    _ = git.chmod(git.stat().st_mode | stat.S_IXUSR)
    helper = exec_path / "git-remote-http"
    _ = helper.write_bytes(GIT_HELPER_BYTES)
    _ = helper.chmod(helper.stat().st_mode | stat.S_IXUSR)
    destination = tmp_path / ".dependencies" / "git" / GIT_VERSION

    alias = project.import_git_installation(
        git,
        exec_path,
        destination,
        windows=False,
    )

    assert alias == destination / "bin/git.bin"
    assert alias.read_bytes() == GIT_BYTES
    assert alias.stat().st_mode & stat.S_IXUSR
    assert (destination / "bin/git").read_bytes() == GIT_BYTES
    assert (
        destination / "libexec/git-core/git-remote-http"
    ).read_bytes() == GIT_HELPER_BYTES
    assert project.git_import_complete(destination)


@pytest.mark.skipif(os.name != POSIX_NAME, reason="POSIX root creation")
def test_git_import_rejects_late_occupied_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory that appears after admission must not receive Git files."""
    source = tmp_path / "host-git"
    _ = source.write_bytes(GIT_BYTES)
    helpers = tmp_path / "helpers"
    helpers.mkdir()
    destination = tmp_path / "git" / GIT_VERSION
    destination.parent.mkdir()
    sentinel = destination / "foreign-sentinel"
    native_mkdir = os.mkdir
    occupied = False

    def occupy_on_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal occupied
        if path == destination.name and dir_fd is not None and not occupied:
            occupied = True
            native_mkdir(path, mode, dir_fd=dir_fd)
            _ = sentinel.write_bytes(b"retain foreign file")
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", occupy_on_mkdir)
        with pytest.raises(FileExistsError):
            _ = project.import_git_installation(
                source, helpers, destination, windows=False
            )
    assert occupied
    assert sentinel.read_bytes() == b"retain foreign file"
    assert not (destination / "bin").exists()


@pytest.mark.parametrize("component", ["git", "rust"])
def test_toolchain_import_rejects_linked_parent_before_copy(
    tmp_path: Path, component: str
) -> None:
    """Import must not write a foreign tree before marker admission fails."""
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    parent = tmp_path / ".dependencies" / component
    parent.parent.mkdir()
    try:
        parent.symlink_to(foreign, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory symlinks unavailable: {error}")
    source = tmp_path / "native"
    source.mkdir()
    destination = parent / GIT_VERSION
    with pytest.raises(project.InitializationError, match="parent path"):
        if component == "git":
            executable = source / "git"
            _ = executable.write_bytes(GIT_BYTES)
            _ = project.import_git_installation(
                executable, source, destination, windows=False
            )
        else:
            source_bin = source / "bin"
            source_bin.mkdir()
            _ = (source_bin / "cargo").write_bytes(RUST_CARGO_BYTES)
            _ = project.import_rust_toolchain(
                source, destination, tool_ids=("cargo",), windows=False
            )
    assert list(foreign.iterdir()) == []


def test_git_import_rejects_occupied_root_with_masked_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A false high-level exists result cannot admit an unowned import root."""
    destination = tmp_path / "imported-git"
    destination.mkdir()
    source = tmp_path / "native-git"
    _ = source.write_bytes(GIT_BYTES)
    helpers = tmp_path / "helpers"
    helpers.mkdir()
    native_exists = Path.exists

    def masked_exists(path: Path) -> bool:
        return False if path == destination else native_exists(path)

    monkeypatch.setattr(Path, "exists", masked_exists)
    with pytest.raises(project.InitializationError, match="destination already exists"):
        _ = project.import_git_installation(
            source, helpers, destination, windows=False
        )
    assert list(destination.iterdir()) == []


@pytest.mark.parametrize("scenario", IMPORT_MARKER_CASES)
@pytest.mark.parametrize(
    "mutation", [MARKER_SHORT, MARKER_SAME_LENGTH, MARKER_LONG]
)
def test_import_completion_rejects_corrupt_marker_bytes(
    tmp_path: Path,
    scenario: tuple[str, bytes, Callable[[Path], bool]],
    *,
    mutation: str,
) -> None:
    """Crash-left or forged marker bytes never imply native import readiness."""
    name, expected, check = scenario
    marker = tmp_path / name
    if mutation == MARKER_SHORT:
        corrupt = expected[:1]
    elif mutation == MARKER_SAME_LENGTH:
        corrupt = b"x" * len(expected)
    else:
        corrupt = expected + b"extra"
    _ = marker.write_bytes(corrupt)
    assert not check(tmp_path)


@pytest.mark.parametrize("scenario", IMPORT_MARKER_CASES)
def test_import_completion_rejects_linked_marker(
    tmp_path: Path,
    scenario: tuple[str, bytes, Callable[[Path], bool]],
) -> None:
    """A linked marker is not evidence of an owned imported toolchain."""
    name, expected, check = scenario
    foreign = tmp_path / "other"
    _ = foreign.write_bytes(expected)
    marker = tmp_path / name
    try:
        marker.symlink_to(foreign)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    assert not check(tmp_path)


@pytest.mark.parametrize("scenario", IMPORT_MARKER_CASES)
def test_import_completion_rejects_hardlinked_marker(
    tmp_path: Path,
    scenario: tuple[str, bytes, Callable[[Path], bool]],
) -> None:
    """Another path to identical bytes cannot attest an owned import marker."""
    name, expected, check = scenario
    outside = tmp_path / "unowned-marker"
    _ = outside.write_bytes(expected)
    try:
        os.link(outside, tmp_path / name)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hardlinks unavailable: {error}")
    assert not check(tmp_path)


@pytest.mark.skipif(os.name != POSIX_NAME, reason="requires POSIX parent close")
@pytest.mark.parametrize(
    "marker_name", [project.GIT_IMPORT_MARKER, project.RUST_IMPORT_MARKER]
)
def test_import_marker_writer_rejects_post_parent_close_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    marker_name: str,
) -> None:
    """A late parent close callback cannot validate an overwritten marker."""
    marker = tmp_path / marker_name
    content = b"malbolge-git-import/v1\n"
    native_open = os.open
    native_close = os.close
    parent_fd: int | None = None
    mutated = False

    def record_parent_open(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal parent_fd
        fd = native_open(path, flags, mode, dir_fd=dir_fd)
        if path == tmp_path:
            parent_fd = fd
        return fd

    def change_marker_on_parent_close(fd: int) -> None:
        nonlocal mutated
        native_close(fd)
        if fd == parent_fd and not mutated and marker.exists():
            _ = marker.write_bytes(b"X" * len(content))
            mutated = True

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", record_parent_open)
        isolated.setattr(os, "close", change_marker_on_parent_close)
        with pytest.raises(project.InitializationError, match="marker.*changed"):
            project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
                marker, content.decode("ascii")
            )
    assert parent_fd is not None
    assert mutated
    assert marker.read_bytes() == b"X" * len(content)


@pytest.mark.parametrize("scenario", IMPORT_MARKER_CASES)
def test_import_completion_rejects_hardlink_created_during_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: tuple[str, bytes, Callable[[Path], bool]],
) -> None:
    """A marker linked after the first lstat cannot become ready."""
    name, expected, check = scenario
    marker = tmp_path / name
    _ = marker.write_bytes(expected)
    outside = tmp_path / "external-marker"
    native_read = project._read_authority_bytes  # pyright: ignore[reportPrivateUsage]
    linked = False

    def link_before_read(path: Path) -> bytes:
        nonlocal linked
        if path == marker and not linked:
            linked = True
            os.link(marker, outside)
        return native_read(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(project, "_read_authority_bytes", link_before_read)
        assert not check(tmp_path)
    assert linked
    assert outside.read_bytes() == expected


@pytest.mark.parametrize("scenario", IMPORT_MARKER_CASES)
def test_import_completion_rejects_same_bytes_swap_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: tuple[str, bytes, Callable[[Path], bool]],
) -> None:
    """A different marker inode with matching content cannot become ready."""
    name, expected, check = scenario
    marker = tmp_path / name
    _ = marker.write_bytes(expected)
    relocated = tmp_path / "moved-marker"
    new_marker = tmp_path / "replacement-marker"
    _ = new_marker.write_bytes(expected)
    native_read = project._read_authority_bytes  # pyright: ignore[reportPrivateUsage]
    swapped = False

    def swap_after_read(path: Path) -> bytes:
        nonlocal swapped
        content = native_read(path)
        if path == marker and not swapped:
            swapped = True
            _ = marker.replace(relocated)
            _ = new_marker.replace(marker)
        return content

    with monkeypatch.context() as isolated:
        isolated.setattr(project, "_read_authority_bytes", swap_after_read)
        assert not check(tmp_path)
    assert swapped
    assert relocated.read_bytes() == expected
    assert marker.read_bytes() == expected


@pytest.mark.parametrize("scenario", IMPORT_MARKER_CASES)
def test_import_completion_rejects_fifo_marker(
    tmp_path: Path,
    scenario: tuple[str, bytes, Callable[[Path], bool]],
) -> None:
    """An import readiness query never blocks opening a named pipe."""
    mkfifo = cast("Callable[[Path], None] | None", getattr(os, "mkfifo", None))
    if mkfifo is None:
        pytest.skip("FIFO unsupported on this platform")
    name, _, check = scenario
    mkfifo(tmp_path / name)
    assert not check(tmp_path)


@pytest.mark.parametrize("scenario", IMPORT_MARKER_CASES)
def test_import_completion_rejects_linked_parent(
    tmp_path: Path,
    scenario: tuple[str, bytes, Callable[[Path], bool]],
) -> None:
    """A redirected toolchain root cannot supply import readiness bytes."""
    name, expected, check = scenario
    real = tmp_path / "actual"
    real.mkdir()
    _ = (real / name).write_bytes(expected)
    alias = tmp_path / "linked"
    try:
        alias.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory symlinks unavailable: {error}")
    assert not check(alias)


@pytest.mark.parametrize("scenario", IMPORT_MARKER_CASES)
def test_import_marker_writer_rejects_complete_count_with_wrong_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: tuple[str, bytes, Callable[[Path], bool]],
) -> None:
    """A forged full byte count cannot publish a corrupt import marker."""
    name, expected, check = scenario
    marker = tmp_path / name
    native_write = os.write

    def corrupt_write(descriptor: int, data: bytes) -> int:
        assert data == expected
        return native_write(descriptor, b"x" * len(data))

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "write", corrupt_write)
        with pytest.raises(project.InitializationError, match="marker content"):
            project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
                marker, expected.decode("ascii")
            )
    assert not marker.exists()
    assert not check(tmp_path)


@pytest.mark.parametrize("alias_kind", ["symlink", "hardlink"])
@pytest.mark.parametrize("marker_name", [project.GIT_IMPORT_MARKER, project.RUST_IMPORT_MARKER])
def test_import_marker_writer_never_overwrites_linked_foreign_file(
    tmp_path: Path, marker_name: str, alias_kind: str
) -> None:
    """A preexisting linked completion marker must not overwrite outsiders."""
    foreign = tmp_path / "protected"
    original = b"foreign marker contents must be retained"
    _ = foreign.write_bytes(original)
    marker = tmp_path / marker_name
    try:
        if alias_kind == "symlink":
            _ = marker.symlink_to(foreign)
        else:
            os.link(foreign, marker)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"file aliases unavailable: {error}")

    with pytest.raises(project.InitializationError, match="marker"):
        project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
            marker, "malbolge-git-import/v1\n"
        )
    assert foreign.read_bytes() == original


@pytest.mark.skipif(os.name != "posix", reason="requires directory descriptors")
@pytest.mark.parametrize("substitution", ["symlink", "physical"])
def test_import_marker_writer_never_creates_in_swapped_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, substitution: str
) -> None:
    """Exclusive marker creation must not follow a late foreign parent."""
    parent = tmp_path / "import-root"
    parent.mkdir()
    marker = parent / project.GIT_IMPORT_MARKER
    parked = tmp_path / "parked-import"
    foreign = tmp_path / "foreign-import"
    foreign.mkdir()
    _ = (foreign / "sentinel").write_bytes(b"external data")
    native_open = os.open
    swapped = False
    foreign_created = False

    def swap_at_marker_create(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped, foreign_created
        if (
            not swapped
            and (path == marker or path == marker.name)
            and flags & os.O_CREAT
        ):
            _ = parent.rename(parked)
            if substitution == "symlink":
                _ = parent.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(parent)
            swapped = True
        if dir_fd is None:
            descriptor = native_open(path, flags, mode)
        else:
            descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        if swapped:
            foreign_root = foreign if substitution == "symlink" else parent
            foreign_created |= (foreign_root / marker.name).exists()
        return descriptor

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", swap_at_marker_create)
        with pytest.raises(project.InitializationError, match="import marker"):
            project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
                marker, "malbolge-git-import/v1\n"
            )
    assert swapped
    assert not foreign_created
    foreign_root = foreign if substitution == "symlink" else parent
    assert (foreign_root / "sentinel").read_bytes() == b"external data"
    assert not (foreign_root / marker.name).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires directory descriptors")
@pytest.mark.parametrize("substitution", ["symlink", "physical"])
def test_import_marker_writer_rejects_parent_swap_during_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, substitution: str
) -> None:
    """A failed marker cannot survive a late parent swap or touch outsiders."""
    parent = tmp_path / "owned-import"
    parent.mkdir()
    marker = parent / project.GIT_IMPORT_MARKER
    parked = tmp_path / "parked-import"
    foreign = tmp_path / "foreign-import"
    foreign.mkdir()
    _ = (foreign / "sentinel").write_bytes(b"external data")
    native_write = os.write
    swapped = False

    def swap_before_write(descriptor: int, content: bytes) -> int:
        nonlocal swapped
        if not swapped:
            _ = parent.rename(parked)
            if substitution == "symlink":
                _ = parent.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(parent)
            swapped = True
        return native_write(descriptor, content)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "write", swap_before_write)
        with pytest.raises(project.InitializationError, match="import marker parent"):
            project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
                marker, "malbolge-git-import/v1\n"
            )
    assert swapped
    foreign_root = foreign if substitution == "symlink" else parent
    assert (foreign_root / "sentinel").read_bytes() == b"external data"
    assert not (foreign_root / marker.name).exists()
    assert not (parked / marker.name).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires directory descriptors")
def test_import_marker_writer_preserves_original_fault_after_parent_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed cleanup close does not mask the original marker rejection."""
    marker = tmp_path / project.GIT_IMPORT_MARKER
    native_open = os.open
    native_close = os.close
    parent_descriptor: int | None = None
    close_fault = RuntimeError("parent descriptor close failed")

    def tracked_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal parent_descriptor
        descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        if path == tmp_path:
            parent_descriptor = descriptor
        return descriptor

    def failing_close(descriptor: int) -> None:
        native_close(descriptor)
        if descriptor == parent_descriptor:
            raise close_fault

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", tracked_open)
        isolated.setattr(os, "close", failing_close)
        with pytest.raises(project.InitializationError, match="requires native text"):
            project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
                marker, cast("str", cast("object", 42))
            )
    assert parent_descriptor is not None
    with pytest.raises(OSError):
        _ = os.fstat(parent_descriptor)
    assert not marker.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires directory descriptors")
def test_import_marker_writer_types_parent_close_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Parent close faults are typed even after complete marker byte receipt."""
    marker = tmp_path / project.GIT_IMPORT_MARKER
    native_open = os.open
    native_close = os.close
    parent_descriptor: int | None = None
    fault = RuntimeError("host marker parent close failure")

    def tracked_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal parent_descriptor
        descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        if path == tmp_path:
            parent_descriptor = descriptor
        return descriptor

    def failing_close(descriptor: int) -> None:
        native_close(descriptor)
        if descriptor == parent_descriptor:
            raise fault

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", tracked_open)
        isolated.setattr(os, "close", failing_close)
        with pytest.raises(
            project.InitializationError, match="import marker parent close failed"
        ) as caught:
            project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
                marker, "malbolge-git-import/v1\n"
            )
    assert caught.value.__cause__ is fault
    assert parent_descriptor is not None
    with pytest.raises(OSError):
        _ = os.fstat(parent_descriptor)
    assert marker.read_bytes() == GIT_MARKER_BYTES


@pytest.mark.parametrize(
    "marker_name", [project.GIT_IMPORT_MARKER, project.RUST_IMPORT_MARKER]
)
def test_import_marker_writer_rejects_nonempty_created_descriptor_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, marker_name: str
) -> None:
    """A forged O_EXCL open must not write or remove an existing marker."""
    marker = tmp_path / marker_name
    original = b"a late-created nonempty marker must remain untouched" * 2
    native_open = os.open
    native_write = os.write
    injected = False
    attempted_write = False

    def forged_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal injected
        if path in (marker, marker.name) and flags & os.O_CREAT:
            injected = True
            _ = marker.write_bytes(original)
            if dir_fd is not None:
                return native_open(marker.name, os.O_WRONLY, dir_fd=dir_fd)
            return native_open(marker, os.O_WRONLY)
        return native_open(path, flags, mode, dir_fd=dir_fd)

    def tracked_write(descriptor: int, content: bytes) -> int:
        nonlocal attempted_write
        attempted_write = True
        return native_write(descriptor, content)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", forged_open)
        isolated.setattr(os, "write", tracked_write)
        with pytest.raises(project.InitializationError, match="marker descriptor"):
            project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
                marker, "malbolge-git-import/v1\n"
            )
    assert injected
    assert not attempted_write
    assert marker.read_bytes() == original


@pytest.mark.parametrize(
    "marker_name", [project.GIT_IMPORT_MARKER, project.RUST_IMPORT_MARKER]
)
def test_import_marker_writer_refuses_preexisting_empty_leaf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, marker_name: str
) -> None:
    """Even a forged exclusive-open receipt must not promote an old empty leaf."""
    marker = tmp_path / marker_name
    marker.touch()
    native_open = os.open
    native_write = os.write
    attempted_write = False

    def forged_open(path: Path, flags: int, mode: int = 0o777) -> int:
        if path == marker and flags & os.O_CREAT:
            return native_open(marker, os.O_WRONLY)
        return native_open(path, flags, mode)

    def tracked_write(descriptor: int, content: bytes) -> int:
        nonlocal attempted_write
        attempted_write = True
        return native_write(descriptor, content)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", forged_open)
        isolated.setattr(os, "write", tracked_write)
        with pytest.raises(project.InitializationError, match="marker"):
            project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
                marker, "malbolge-git-import/v1\n"
            )
    assert not attempted_write
    assert marker.read_bytes() == b""


def test_import_marker_preflight_types_foreign_leaf_status_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unprintable host status faults never invoke formatting or publish markers."""

    class ForeignHostOSError(OSError):
        @override
        def __str__(self) -> Never:
            raise AssertionError("foreign marker status formatter invoked")

    marker = tmp_path / project.GIT_IMPORT_MARKER
    fault = ForeignHostOSError("status unavailable")
    native_lstat = Path.lstat

    def failing_lstat(path: Path) -> os.stat_result:
        if path == marker:
            raise fault
        return native_lstat(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", failing_lstat)
        with pytest.raises(
            project.InitializationError, match="cannot inspect import marker"
        ) as caught:
            project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
                marker, "malbolge-git-import/v1\n"
            )
    assert caught.value.__cause__ is fault
    assert not marker.exists()


def test_import_marker_writer_rejects_leaf_swap_during_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Renaming a new marker away cannot turn a foreign leaf into readiness."""
    marker = tmp_path / project.GIT_IMPORT_MARKER
    relocated = tmp_path / "moved-marker"
    foreign = tmp_path / "external-marker"
    original = b"external bytes cannot be overwritten"
    _ = foreign.write_bytes(original)
    real_write = os.write
    swapped = False

    def swap_before_write(descriptor: int, data: bytes) -> int:
        nonlocal swapped
        if not swapped:
            swapped = True
            _ = marker.replace(relocated)
            _ = marker.symlink_to(foreign)
        return real_write(descriptor, data)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "write", swap_before_write)
        with pytest.raises(project.InitializationError, match="marker"):
            project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
                marker, "malbolge-git-import/v1\n"
            )
    assert swapped
    assert marker.is_symlink()
    assert foreign.read_bytes() == original


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_import_marker_writer_removes_partial_file_on_write_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A host write fault leaves no published import completion marker."""
    marker = tmp_path / project.GIT_IMPORT_MARKER
    fault = fault_type("host marker write failed")

    def failing_write(_descriptor: int, _data: bytes) -> Never:
        raise fault

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "write", failing_write)
        with pytest.raises(
            project.InitializationError, match="import marker write failed"
        ) as caught:
            project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
                marker, "malbolge-git-import/v1\n"
            )
    assert caught.value.__cause__ is fault
    assert not marker.exists()


def test_import_marker_writer_rejects_forged_open_file_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A nonnative fstat result cannot attest a newly created marker."""
    marker = tmp_path / project.GIT_IMPORT_MARKER
    native_fstat = os.fstat
    opened: list[int] = []
    real_open = os.open

    class ForeignStat:
        def __init__(self, native: os.stat_result) -> None:
            self.native: os.stat_result = native

        def __getattr__(self, name: str) -> object:
            return cast("object", getattr(self.native, name))

    def tracked_open(
        path: str | os.PathLike[str], flags: int, mode: int = 0o777,
        *, dir_fd: int | None = None,
    ) -> int:
        descriptor = real_open(path, flags, mode, dir_fd=dir_fd)
        if path in (marker, marker.name):
            opened.append(descriptor)
        return descriptor

    def forged_fstat(descriptor: int) -> os.stat_result:
        result = native_fstat(descriptor)
        if descriptor in opened:
            return cast("os.stat_result", cast("object", ForeignStat(result)))
        return result

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", tracked_open)
        isolated.setattr(os, "fstat", forged_fstat)
        with pytest.raises(project.InitializationError, match="descriptor"):
            project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
                marker, "malbolge-git-import/v1\n"
            )
    assert opened
    with pytest.raises(OSError):
        _ = native_fstat(opened[0])
    assert marker.read_bytes() == b""


def test_import_marker_writer_close_fault_invalidates_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed descriptor close cannot leave a complete import marker."""
    marker = tmp_path / project.GIT_IMPORT_MARKER
    native_open = os.open
    native_close = os.close
    fault = OSError("host marker close failed")
    marker_descriptor: int | None = None

    def tracked_open(
        path: str | os.PathLike[str], flags: int, mode: int = 0o777,
        *, dir_fd: int | None = None,
    ) -> int:
        nonlocal marker_descriptor
        descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        if path in (marker, marker.name) and flags & os.O_CREAT:
            marker_descriptor = descriptor
        return descriptor

    def failing_close(descriptor: int) -> None:
        native_close(descriptor)
        if descriptor == marker_descriptor:
            raise fault

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", tracked_open)
        isolated.setattr(os, "close", failing_close)
        with pytest.raises(
            project.InitializationError, match="import marker close failed"
        ) as caught:
            project._write_import_completion_marker(  # pyright: ignore[reportPrivateUsage]
                marker, "malbolge-git-import/v1\n"
            )
    assert caught.value.__cause__ is fault
    assert not marker.exists()


@pytest.mark.parametrize("bad_write_count", [1, None, True, -1, 1_000_000])
def test_git_import_completion_marker_requires_complete_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_write_count: object,
) -> None:
    """A partial Git import marker cannot make an incomplete tree ready."""
    source = tmp_path / "host-git"
    _ = source.write_bytes(GIT_BYTES)
    exec_path = tmp_path / "git-exec"
    exec_path.mkdir()
    destination = tmp_path / "imported-git"
    marker = destination / project.GIT_IMPORT_MARKER
    original_write = os.write

    def incomplete_write(descriptor: int, data: bytes) -> int:
        _ = original_write(descriptor, data[:1])
        return cast("int", bad_write_count)

    monkeypatch.setattr(os, "write", incomplete_write)
    with pytest.raises(project.InitializationError, match="short or invalid"):
        _ = project.import_git_installation(
            source, exec_path, destination, windows=False
        )
    assert not marker.exists()
    assert not project.git_import_complete(destination)


@pytest.mark.parametrize("bad_write_count", [1, None, True, -1, 1_000_000])
def test_rust_import_completion_marker_requires_complete_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_write_count: object,
) -> None:
    """A partial Rust import marker cannot make an incomplete tree ready."""
    source = tmp_path / "host-rust"
    source_bin = source / "bin"
    source_bin.mkdir(parents=True)
    _ = (source_bin / "cargo").write_bytes(RUST_CARGO_BYTES)
    destination = tmp_path / "imported-rust"
    marker = destination / project.RUST_IMPORT_MARKER
    original_write = os.write

    def incomplete_write(descriptor: int, data: bytes) -> int:
        _ = original_write(descriptor, data[:1])
        return cast("int", bad_write_count)

    monkeypatch.setattr(os, "write", incomplete_write)
    with pytest.raises(project.InitializationError, match="short or invalid"):
        _ = project.import_rust_toolchain(
            source, destination, tool_ids=("cargo",), windows=False
        )
    assert not marker.exists()
    assert not project.rust_toolchain_import_complete(destination)


@pytest.mark.parametrize("name", project.LOCAL_DIRECTORIES)
def test_local_directory_initialization_rejects_linked_state_root(
    tmp_path: Path, name: str
) -> None:
    """Bootstrap must not accept redirected checkout-local state paths."""
    external = tmp_path / "outside"
    external.mkdir()
    linked = tmp_path / name
    try:
        linked.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory symlinks unavailable: {error}")
    with pytest.raises(project.InitializationError, match="local state directory"):
        _ = project.initialize_local_directories(tmp_path)
    assert list(external.iterdir()) == []


def test_local_directory_initialization_rejects_linked_cargo_home(
    tmp_path: Path,
) -> None:
    """Nested Cargo home must remain physically in the checkout state root."""
    external = tmp_path / "outside"
    external.mkdir()
    cargo_home = tmp_path / project.CARGO_HOME_RELATIVE
    cargo_home.parent.mkdir()
    try:
        cargo_home.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory symlinks unavailable: {error}")
    with pytest.raises(project.InitializationError, match="local state directory"):
        _ = project.initialize_local_directories(tmp_path)
    assert list(external.iterdir()) == []


@pytest.mark.parametrize("fault_site", ["parent", "leaf", "mkdir"])
def test_local_directory_initialization_types_host_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault_site: str
) -> None:
    """State creation failures retain their causes without formatting hooks."""

    class ForeignHostOSError(OSError):
        @override
        def __str__(self) -> Never:
            raise AssertionError("foreign state filesystem formatter invoked")

    fault = ForeignHostOSError("state access failed")
    target = tmp_path / ".cache"
    native_lstat = Path.lstat
    native_mkdir = Path.mkdir
    native_os_mkdir = os.mkdir
    triggered = False

    def fault_lstat(path: Path) -> os.stat_result:
        nonlocal triggered
        if (fault_site == "parent" and path == tmp_path) or (
            fault_site == "leaf" and path == target
        ):
            triggered = True
            raise fault
        return native_lstat(path)

    def fault_mkdir(
        path: Path,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        nonlocal triggered
        if fault_site == "mkdir" and path == target:
            triggered = True
            raise fault
        native_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    def fault_os_mkdir(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal triggered
        if fault_site == "mkdir" and path == target.name and dir_fd is not None:
            triggered = True
            raise fault
        if dir_fd is None:
            native_os_mkdir(path, mode)
        else:
            native_os_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", fault_lstat)
        isolated.setattr(Path, "mkdir", fault_mkdir)
        isolated.setattr(os, "mkdir", fault_os_mkdir)
        with pytest.raises(
            project.InitializationError, match="local state directory"
        ) as caught:
            project.initialize_local_directories(tmp_path)
    assert triggered
    assert caught.value.__cause__ is fault
    assert not target.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires directory descriptors")
@pytest.mark.parametrize("replacement", ["symlink", "physical"])
def test_local_directory_initialization_does_not_create_in_swapped_cargo_home_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """A parent substituted during mkdir must not receive a Cargo home."""
    dependencies = tmp_path / ".dependencies"
    cargo_home = dependencies / "cargo-home"
    parked = tmp_path / "parked-dependencies"
    external = tmp_path / "foreign-dependencies"
    external.mkdir()
    _ = (external / "sentinel").write_text("foreign", encoding="ascii")
    native_mkdir = os.mkdir
    swapped = False

    def swap_on_cargo_home_mkdir(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and (path == cargo_home or path == "cargo-home"):
            _ = dependencies.rename(parked)
            if replacement == "symlink":
                _ = dependencies.symlink_to(external, target_is_directory=True)
            else:
                _ = external.rename(dependencies)
            swapped = True
        if dir_fd is None:
            native_mkdir(path, mode)
        else:
            native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", swap_on_cargo_home_mkdir)
        with pytest.raises(project.InitializationError, match="local state directory"):
            _ = project.initialize_local_directories(tmp_path)
    assert swapped
    assert not (parked / "cargo-home").is_symlink()
    foreign = external if replacement == "symlink" else dependencies
    assert (foreign / "sentinel").read_text(encoding="ascii") == "foreign"
    assert not (foreign / "cargo-home").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires directory descriptors")
def test_local_directory_initialization_rejects_swap_before_cargo_home_parent_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nested creation must use the directory first admitted by bootstrap."""
    dependencies = tmp_path / ".dependencies"
    parked = tmp_path / "parked-dependencies"
    external = tmp_path / "foreign-dependencies"
    external.mkdir()
    _ = (external / "sentinel").write_text("foreign", encoding="ascii")
    native_open = os.open
    swapped = False

    def replace_before_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if path == dependencies and not swapped:
            _ = dependencies.rename(parked)
            _ = external.rename(dependencies)
            swapped = True
        return native_open(path, flags, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", replace_before_open)
        with pytest.raises(project.InitializationError, match="local state directory"):
            _ = project.initialize_local_directories(tmp_path)
    assert swapped
    assert (dependencies / "sentinel").read_text(encoding="ascii") == "foreign"
    assert not (dependencies / "cargo-home").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires directory descriptors")
def test_local_directory_initialization_rejects_checkout_swap_before_root_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inserted checkout root cannot receive the ignored state directories."""
    parked = tmp_path.with_name(f"{tmp_path.name}-parked")
    external = tmp_path.with_name(f"{tmp_path.name}-foreign")
    external.mkdir()
    _ = (external / "sentinel").write_text("foreign", encoding="ascii")
    native_open = os.open
    swapped = False

    def replace_root_before_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if path == tmp_path and not swapped:
            _ = tmp_path.rename(parked)
            _ = external.rename(tmp_path)
            swapped = True
        return native_open(path, flags, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", replace_root_before_open)
        with pytest.raises(project.InitializationError, match="local state directory"):
            _ = project.initialize_local_directories(tmp_path)
    assert swapped
    assert (tmp_path / "sentinel").read_text(encoding="ascii") == "foreign"
    assert not any((tmp_path / name).exists() for name in project.LOCAL_DIRECTORIES)



@pytest.mark.skipif(os.name != "posix", reason="requires directory descriptors")
def test_local_state_parent_cleanup_preserves_admission_error_on_close_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cleanup close errors cannot replace the original parent mismatch."""
    alternate = tmp_path / "different-directory"
    alternate.mkdir()
    native_open = os.open
    native_close = os.close
    native_lstat = Path.lstat
    root_descriptor: int | None = None
    closed = False

    class ForeignRuntimeError(RuntimeError):
        @override
        def __str__(self) -> Never:
            raise AssertionError("foreign close fault formatter invoked")

    fault = ForeignRuntimeError("foreign close failure")

    def record_root_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal root_descriptor
        descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        if path == tmp_path:
            root_descriptor = descriptor
        return descriptor

    def replaced_root_status(path: Path) -> os.stat_result:
        if path == tmp_path and root_descriptor is not None:
            return native_lstat(alternate)
        return native_lstat(path)

    def fail_cleanup_close(descriptor: int) -> None:
        nonlocal closed
        native_close(descriptor)
        if descriptor == root_descriptor:
            closed = True
            raise fault

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", record_root_open)
        isolated.setattr(Path, "lstat", replaced_root_status)
        isolated.setattr(os, "close", fail_cleanup_close)
        with pytest.raises(project.InitializationError, match="local state directory"):
            _ = project.initialize_local_directories(tmp_path)
    assert closed
    assert root_descriptor is not None
    with pytest.raises(OSError):
        _ = os.fstat(root_descriptor)


def test_local_directory_initialization_is_idempotent(tmp_path: Path) -> None:
    """Ignored checkout state directories can be initialized repeatedly."""
    first = project.initialize_local_directories(tmp_path)
    second = project.initialize_local_directories(tmp_path)

    assert first == second
    assert tuple(path.name for path in first) == project.LOCAL_DIRECTORIES
    assert all(path.is_dir() for path in first)
    assert (tmp_path / ".dependencies/cargo-home").is_dir()


def test_repository_validation_fails_closed_for_wrong_root(
    tmp_path: Path,
) -> None:
    """Bootstrap refuses a directory without the repository authority files."""
    with pytest.raises(project.InitializationError, match="repository root"):
        project.validate_repository(tmp_path)


def _jig_alias_fixture(
    tmp_path: Path, *, windows: bool
) -> python_validation.ValidationEnvironmentLayout:
    layout = python_validation.validation_layout(tmp_path, windows=windows)
    layout.scripts.mkdir(parents=True)
    suffix = ".exe" if windows else ""
    for tool_id in ("basedpyright", "pytest", "ruff"):
        source = layout.scripts / f"{tool_id}{suffix}"
        _ = source.write_bytes(f"{tool_id}-native".encode("ascii"))
    return layout


def _forge_jig_mkstemp_receipt(
    monkeypatch: pytest.MonkeyPatch,
    foreign: Path,
) -> tuple[list[int], list[Path]]:
    """Return tracked descriptor and actual stage paths for one forged name.

    Returns:
        One list of owned file descriptors and one of actual stage names.

    """
    real_mkstemp = tempfile.mkstemp
    stages: list[Path] = []
    descriptors: list[int] = []

    def forged_mkstemp(**kwargs: object) -> tuple[int, str]:
        descriptor, actual_name = real_mkstemp(
            prefix=cast("str", kwargs["prefix"]),
            dir=cast("Path", kwargs["dir"]),
        )
        stages.append(Path(actual_name))
        descriptors.append(descriptor)
        return descriptor, str(foreign)

    monkeypatch.setattr(tempfile, "mkstemp", forged_mkstemp)
    return descriptors, stages


@pytest.mark.parametrize("windows", [False, True])
@pytest.mark.parametrize("foreign_parent", [False, True])
def test_jig_alias_publisher_rejects_foreign_mkstemp_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    windows: bool,
    foreign_parent: bool,
) -> None:
    """A forged name must never replace or unlink a foreign regular file."""
    layout = _jig_alias_fixture(tmp_path, windows=windows)
    alias_root = layout.environment / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "basedpyright.bin"
    previous = b"original Jig alias"
    foreign_bytes = b"foreign data must survive"
    _ = target.write_bytes(previous)
    foreign = (
        tmp_path / "outside.bin"
        if foreign_parent
        else alias_root / f".{target.name}.foreign"
    )
    _ = foreign.write_bytes(foreign_bytes)
    descriptors, stages = _forge_jig_mkstemp_receipt(monkeypatch, foreign)
    try:
        with pytest.raises(python_validation.ProvisionError, match="temporary"):
            _ = python_validation.write_jig_tool_aliases(
                layout, windows=windows
            )
        assert foreign.read_bytes() == foreign_bytes
        assert target.read_bytes() == previous
        assert len(descriptors) == 1
        with pytest.raises(
            OSError, match=r"Bad file descriptor|Invalid handle"
        ):
            _ = os.fstat(descriptors[0])
    finally:
        for stage in stages:
            stage.unlink(missing_ok=True)


def _hardlink_jig_mkstemp_receipt(
    monkeypatch: pytest.MonkeyPatch, foreign: Path
) -> list[Path]:
    """Create a shared-inode stage for the first Jig alias invocation.

    Returns:
        The actual private stage pathnames for fixture-only cleanup.

    """
    real_mkstemp = tempfile.mkstemp
    stages: list[Path] = []

    def linked_mkstemp(**kwargs: object) -> tuple[int, str]:
        descriptor, name = real_mkstemp(
            prefix=cast("str", kwargs["prefix"]),
            dir=cast("Path", kwargs["dir"]),
        )
        stage = Path(name)
        stages.append(stage)
        if len(stages) == 1:
            try:
                os.link(stage, foreign)
            except OSError as error:
                os.close(descriptor)
                stage.unlink(missing_ok=True)
                pytest.skip(f"hardlinks unavailable: {error}")
        return descriptor, name

    monkeypatch.setattr(tempfile, "mkstemp", linked_mkstemp)
    return stages


@pytest.mark.parametrize("windows", [False, True])
def test_jig_alias_publisher_rejects_hardlinked_staging_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    windows: bool,
) -> None:
    """A private stage must not share its inode with a foreign hardlink."""
    layout = _jig_alias_fixture(tmp_path, windows=windows)
    alias_root = layout.environment / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "basedpyright.bin"
    previous = b"original alias"
    _ = target.write_bytes(previous)
    foreign = tmp_path / "unrelated-hardlink.bin"
    stages = _hardlink_jig_mkstemp_receipt(monkeypatch, foreign)
    try:
        with pytest.raises(python_validation.ProvisionError, match="temporary"):
            _ = python_validation.write_jig_tool_aliases(
                layout, windows=windows
            )
        assert foreign.read_bytes() == EMPTY_JIG_STAGE_BYTES
        assert target.read_bytes() == previous
    finally:
        for stage in stages:
            stage.unlink(missing_ok=True)


def _inject_jig_alias_postwrite_stage_swap(
    monkeypatch: pytest.MonkeyPatch,
    foreign: Path,
    *,
    symlink: bool,
) -> tuple[list[Path], list[Path]]:
    """Swap the admitted stage immediately after writing its payload.

    Returns:
        Original staging pathnames and retained owned inode pathnames.

    """
    native_mkstemp = tempfile.mkstemp
    native_fchmod = os.fchmod
    stages: list[Path] = []
    backups: list[Path] = []

    def capture_mkstemp(**kwargs: object) -> tuple[int, str]:
        descriptor, name = native_mkstemp(
            prefix=cast("str", kwargs["prefix"]),
            dir=cast("Path", kwargs["dir"]),
        )
        stages.append(Path(name))
        return descriptor, name

    def swap_fchmod(descriptor: int, mode: int) -> None:
        if not backups:
            stage = stages[0]
            backup = stage.with_name(f"{stage.name}.owned")
            _ = stage.rename(backup)
            backups.append(backup)
            if symlink:
                _ = stage.symlink_to(foreign)
            else:
                os.link(foreign, stage)
        native_fchmod(descriptor, mode)

    monkeypatch.setattr(tempfile, "mkstemp", capture_mkstemp)
    monkeypatch.setattr(os, "fchmod", swap_fchmod)
    return stages, backups


@pytest.mark.parametrize("symlink", [False, True])
def test_jig_alias_publisher_rejects_swapped_stage_after_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    symlink: bool,
) -> None:
    """Staging receipt must remain bound through publication and cleanup."""
    layout = _jig_alias_fixture(tmp_path, windows=False)
    root = layout.environment / "jig-bin"
    root.mkdir()
    target = root / "basedpyright.bin"
    old_bytes = b"existing valid alias"
    foreign_bytes = b"foreign must remain intact"
    _ = target.write_bytes(old_bytes)
    foreign = tmp_path / "foreign.bin"
    _ = foreign.write_bytes(foreign_bytes)
    stages, backups = _inject_jig_alias_postwrite_stage_swap(
        monkeypatch, foreign, symlink=symlink
    )
    try:
        with pytest.raises(python_validation.ProvisionError, match="temporary"):
            _ = python_validation.write_jig_tool_aliases(layout, windows=False)
        assert foreign.read_bytes() == foreign_bytes
        assert target.read_bytes() == old_bytes
        assert len(stages) == len(backups) == 1
        assert stages[0].exists()
    finally:
        for stage in (*stages, *backups):
            stage.unlink(missing_ok=True)


def _inject_binary_source_wrapper_failure(
    monkeypatch: pytest.MonkeyPatch,
    source: Path,
    fault_type: type[Exception],
) -> tuple[list[int], Exception]:
    """Intercept one binary source descriptor and fail stream wrapping.

    Returns:
        The opened descriptors and the injected host failure identity.

    """
    opened: list[int] = []
    native_open = os.open
    native_fdopen = os.fdopen
    fault = fault_type("injected binary source wrapper failure")

    def capture_open(
        path: str | os.PathLike[str], flags: int, mode: int = 0o777
    ) -> int:
        descriptor = native_open(path, flags, mode)
        if os.fspath(path) == os.fspath(source):
            opened.append(descriptor)
        return descriptor

    def fail_fdopen(descriptor: int, mode: str) -> object:
        if descriptor in opened and mode == JIG_BINARY_READ_MODE:
            raise fault
        return native_fdopen(descriptor, mode)

    monkeypatch.setattr(os, "open", capture_open)
    monkeypatch.setattr(os, "fdopen", fail_fdopen)
    return opened, fault


@pytest.mark.parametrize(
    "fault_type", [OSError, ValueError, TypeError, RuntimeError]
)
def test_uv_manifest_fdopen_fault_closes_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Manifest admission must not leak handles or untyped stream errors."""
    manifest = _copy_uv_manifest(tmp_path)
    opened, fault = _inject_binary_source_wrapper_failure(
        monkeypatch, manifest, fault_type
    )
    try:
        with pytest.raises(
            python_validation.ProvisionError,
            match="cannot read uv toolchain manifest",
        ) as caught:
            _ = python_validation.uv_artifact(WINDOWS_PLATFORM, manifest)
        assert caught.value.__cause__ is fault
        assert len(opened) == 1
        with pytest.raises(
            OSError, match=r"Bad file descriptor|Invalid handle"
        ):
            _ = os.fstat(opened[0])
    finally:
        for descriptor in opened:
            with suppress(OSError):
                os.close(descriptor)


@pytest.mark.parametrize(
    "fault_type", [OSError, ValueError, TypeError, RuntimeError]
)
def test_jig_alias_source_fdopen_fault_closes_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A tool source descriptor cannot leak if its stream wrapper fails."""
    layout = _jig_alias_fixture(tmp_path, windows=True)
    source = layout.scripts / "basedpyright.exe"
    opened, fault = _inject_binary_source_wrapper_failure(
        monkeypatch, source, fault_type
    )
    try:
        with pytest.raises(
            python_validation.ProvisionError, match="source read failed"
        ) as caught:
            _ = python_validation.write_jig_tool_aliases(layout, windows=True)
        assert caught.value.__cause__ is fault
        assert len(opened) == 1
        with pytest.raises(
            OSError, match=r"Bad file descriptor|Invalid handle"
        ):
            _ = os.fstat(opened[0])
    finally:
        for descriptor in opened:
            with suppress(OSError):
                os.close(descriptor)


def _inject_alias_writer_wrapper_failure(
    monkeypatch: pytest.MonkeyPatch, fault_type: type[Exception]
) -> tuple[list[int], list[Path], Exception]:
    """Reject a staged binary stream wrapper while tracking owned descriptors.

    Returns:
        Opened descriptors, stage names and the exact injected host exception.

    """
    native_mkstemp = tempfile.mkstemp
    native_fdopen = os.fdopen
    descriptors: list[int] = []
    stages: list[Path] = []
    fault = fault_type("injected binary write wrapper failure")

    def capture_stage(**kwargs: object) -> tuple[int, str]:
        descriptor, name = native_mkstemp(
            prefix=cast("str", kwargs["prefix"]),
            dir=cast("Path", kwargs["dir"]),
        )
        descriptors.append(descriptor)
        stages.append(Path(name))
        return descriptor, name

    def fail_fdopen(descriptor: int, mode: str) -> object:
        if descriptor in descriptors and mode == JIG_BINARY_WRITE_MODE:
            raise fault
        return native_fdopen(descriptor, mode)

    monkeypatch.setattr(tempfile, "mkstemp", capture_stage)
    monkeypatch.setattr(os, "fdopen", fail_fdopen)
    return descriptors, stages, fault


def _assert_rejected_alias_stage(
    target: Path,
    original_bytes: bytes,
    *,
    descriptors: list[int],
    stages: list[Path],
) -> None:
    """Verify rejection preserves the target and closes the private stage."""
    assert target.read_bytes() == original_bytes
    assert len(descriptors) == len(stages) == 1
    assert not stages[0].exists()
    with pytest.raises(OSError, match=r"Bad file descriptor|Invalid handle"):
        _ = os.fstat(descriptors[0])


@pytest.mark.parametrize(
    "scenario", [(False, False), (False, True), (True, False), (True, True)]
)
@pytest.mark.parametrize(
    "fault_type", [OSError, ValueError, TypeError, RuntimeError]
)
def test_jig_alias_writer_stream_fault_closes_stage_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    scenario: tuple[bool, bool],
    fault_type: type[Exception],
) -> None:
    """A failed output stream wrapper cannot leak or truncate an alias."""
    windows, launcher = scenario
    layout = _jig_alias_fixture(tmp_path, windows=windows)
    alias_root = layout.scripts if launcher else layout.environment / "jig-bin"
    alias_root.mkdir(parents=True, exist_ok=True)
    target = (
        layout.python_launcher if launcher else alias_root / "basedpyright.bin"
    )
    previous = STALE_LAUNCHER_BYTES
    _ = target.write_bytes(previous)
    descriptors, stages, fault = _inject_alias_writer_wrapper_failure(
        monkeypatch, fault_type
    )

    def publish() -> None:
        if launcher:
            python_validation.write_launchers(layout, windows=windows)
        else:
            _ = python_validation.write_jig_tool_aliases(
                layout, windows=windows
            )

    try:
        with pytest.raises(
            python_validation.ProvisionError, match="temporary stream"
        ) as caught:
            publish()
        assert caught.value.__cause__ is fault
        _assert_rejected_alias_stage(
            target, previous, descriptors=descriptors, stages=stages
        )
    finally:
        for descriptor in descriptors:
            with suppress(OSError):
                os.close(descriptor)
        for stage in stages:
            stage.unlink(missing_ok=True)


@pytest.mark.parametrize("windows", [False, True])
def test_jig_alias_writer_rejects_redirected_destination(
    tmp_path: Path, *, windows: bool
) -> None:
    """Alias publication must not overwrite the destination of a file link."""
    layout = _jig_alias_fixture(tmp_path, windows=windows)
    alias_root = layout.environment / "jig-bin"
    alias_root.mkdir()
    outside = tmp_path / "outside.txt"
    _ = outside.write_bytes(OUTSIDE_JIG_ALIAS_BYTES)
    try:
        _ = (alias_root / "basedpyright.bin").symlink_to(outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        _ = python_validation.write_jig_tool_aliases(layout, windows=windows)
    assert outside.read_bytes() == OUTSIDE_JIG_ALIAS_BYTES


@pytest.mark.parametrize("windows", [False, True])
def test_jig_alias_writer_rejects_redirected_output_parent(
    tmp_path: Path, *, windows: bool
) -> None:
    """A redirected jig-bin must not publish executable bytes externally."""
    layout = _jig_alias_fixture(tmp_path, windows=windows)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    try:
        _ = (layout.environment / "jig-bin").symlink_to(
            outside, target_is_directory=True
        )
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        _ = python_validation.write_jig_tool_aliases(layout, windows=windows)
    assert tuple(outside.iterdir()) == ()


@pytest.mark.parametrize("windows", [False, True])
def test_jig_alias_writer_rejects_redirected_native_source(
    tmp_path: Path, *, windows: bool
) -> None:
    """Provisioned executables cannot be supplied through linked leaves."""
    layout = _jig_alias_fixture(tmp_path, windows=windows)
    source = layout.scripts / ("ruff.exe" if windows else "ruff")
    original = tmp_path / "real-ruff"
    _ = source.rename(original)
    try:
        _ = source.symlink_to(original)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        _ = python_validation.write_jig_tool_aliases(layout, windows=windows)


def test_jig_alias_writer_rejects_same_byte_source_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Copying a source inode different from the admitted one is forbidden."""
    layout = _jig_alias_fixture(tmp_path, windows=True)
    source = layout.scripts / "basedpyright.exe"
    replacement = tmp_path / "replacement.exe"
    _ = replacement.write_bytes(source.read_bytes())
    original_open = os.open

    def swap_on_open(
        path: str | os.PathLike[str], flags: int, mode: int = 0o777
    ) -> int:
        if os.fspath(path) == os.fspath(source):
            _ = replacement.replace(source)
        return original_open(path, flags, mode)

    monkeypatch.setattr(os, "open", swap_on_open)
    with pytest.raises(python_validation.ProvisionError, match="changed"):
        _ = python_validation.write_jig_tool_aliases(layout, windows=True)


def test_jig_alias_writer_rejects_later_redirect_without_partial_output(
    tmp_path: Path,
) -> None:
    """All native aliases must pass admission before publishing the first."""
    layout = _jig_alias_fixture(tmp_path, windows=True)
    alias_root = layout.environment / "jig-bin"
    alias_root.mkdir()
    outside = tmp_path / "outside.bin"
    _ = outside.write_bytes(OUTSIDE_JIG_ALIAS_BYTES)
    _ = (alias_root / "ruff.bin").symlink_to(outside)
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        _ = python_validation.write_jig_tool_aliases(layout, windows=True)
    assert outside.read_bytes() == OUTSIDE_JIG_ALIAS_BYTES
    assert not (alias_root / "basedpyright.bin").exists()
    assert not (alias_root / "pytest.bin").exists()


def test_jig_alias_writer_rejects_oversized_native_binary(
    tmp_path: Path,
) -> None:
    """Large native tool inputs fail before an unbounded read or alias write."""
    layout = _jig_alias_fixture(tmp_path, windows=True)
    source = layout.scripts / "basedpyright.exe"
    with source.open("wb") as stream:
        _ = stream.truncate(python_validation.MAX_JIG_TOOL_BINARY_BYTES + 1)
    with pytest.raises(python_validation.ProvisionError, match="byte limit"):
        _ = python_validation.write_jig_tool_aliases(layout, windows=True)
    assert not (layout.environment / "jig-bin").exists()


def test_jig_alias_writer_rejects_same_byte_swap_after_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pathname replacement after descriptor read is never accepted."""
    layout = _jig_alias_fixture(tmp_path, windows=True)
    source = layout.scripts / "basedpyright.exe"
    replacement = tmp_path / "replacement.exe"
    _ = replacement.write_bytes(source.read_bytes())
    original_open = os.open
    original_lstat = source.__class__.lstat
    opened = False
    swapped = False

    def observe_open(
        path: str | os.PathLike[str], flags: int, mode: int = 0o777
    ) -> int:
        nonlocal opened
        descriptor = original_open(path, flags, mode)
        if os.fspath(path) == os.fspath(source):
            opened = True
        return descriptor

    def swap_after_read(path: Path) -> os.stat_result:
        nonlocal swapped
        if path == source and opened and not swapped:
            swapped = True
            _ = replacement.replace(source)
        return original_lstat(path)

    monkeypatch.setattr(os, "open", observe_open)
    monkeypatch.setattr(source.__class__, "lstat", swap_after_read)
    with pytest.raises(python_validation.ProvisionError, match="changed"):
        _ = python_validation.write_jig_tool_aliases(layout, windows=True)


def test_jig_alias_writer_rejects_mutation_during_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An in-place edit changes source identity and invalidates copying."""
    layout = _jig_alias_fixture(tmp_path, windows=True)
    source = layout.scripts / "basedpyright.exe"
    original_fstat = os.fstat
    observations = 0
    second_fstat = 2

    def mutate_source(fd: int) -> os.stat_result:
        nonlocal observations
        observations += 1
        if observations == second_fstat:
            _ = source.write_bytes(b"modified")
        return original_fstat(fd)

    monkeypatch.setattr(os, "fstat", mutate_source)
    with pytest.raises(python_validation.ProvisionError, match="changed"):
        _ = python_validation.write_jig_tool_aliases(layout, windows=True)


def test_jig_alias_writer_preserves_existing_binary_on_publish_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed replacement keeps the old alias and removes the private temp."""
    layout = _jig_alias_fixture(tmp_path, windows=True)
    alias_root = layout.environment / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "basedpyright.bin"
    _ = target.write_bytes(OUTSIDE_JIG_ALIAS_BYTES)
    original_replace = target.__class__.replace

    def failing_replace(path: Path, destination: Path) -> Path:
        if destination == target:
            message = "failed atomic alias publication"
            raise PermissionError(message)
        return original_replace(path, destination)

    monkeypatch.setattr(target.__class__, "replace", failing_replace)
    with pytest.raises(PermissionError, match="atomic alias publication"):
        _ = python_validation.write_jig_tool_aliases(layout, windows=True)
    assert target.read_bytes() == OUTSIDE_JIG_ALIAS_BYTES
    assert tuple(alias_root.iterdir()) == (target,)


@pytest.mark.parametrize("windows", [False, True])
@pytest.mark.parametrize(
    "launcher", [PYTHON_LAUNCHER_NAME, PYTEST_LAUNCHER_NAME]
)
def test_python_jig_launcher_rejects_redirected_leaf(
    tmp_path: Path, *, windows: bool, launcher: str
) -> None:
    """Native launchers never overwrite an external file via a linked leaf."""
    layout = python_validation.validation_layout(tmp_path, windows=windows)
    layout.scripts.mkdir(parents=True)
    target = (
        layout.python_launcher
        if launcher == PYTHON_LAUNCHER_NAME
        else layout.pytest_launcher
    )
    outside = tmp_path / "keep.txt"
    _ = outside.write_bytes(OUTSIDE_JIG_ALIAS_BYTES)
    try:
        _ = target.symlink_to(outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        python_validation.write_launchers(layout, windows=windows)
    assert outside.read_bytes() == OUTSIDE_JIG_ALIAS_BYTES
    if launcher == PYTEST_LAUNCHER_NAME:
        assert not layout.python_launcher.exists()


@pytest.mark.parametrize("windows", [False, True])
def test_python_jig_launcher_rejects_linked_scripts_parent(
    tmp_path: Path, *, windows: bool
) -> None:
    """Native scripts cannot be published through redirected bin/Scripts."""
    layout = python_validation.validation_layout(tmp_path, windows=windows)
    layout.environment.mkdir(parents=True)
    redirected = tmp_path / "elsewhere"
    redirected.mkdir()
    try:
        _ = layout.scripts.symlink_to(redirected, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        python_validation.write_launchers(layout, windows=windows)
    assert tuple(redirected.iterdir()) == ()


@pytest.mark.parametrize("windows", [False, True])
def test_python_jig_launcher_publish_replaces_regular_files(
    tmp_path: Path, *, windows: bool
) -> None:
    """Repeat writes preserve both launcher scripts and native conventions."""
    layout = python_validation.validation_layout(tmp_path, windows=windows)
    layout.scripts.mkdir(parents=True)
    _ = layout.python_launcher.write_text("stale", encoding="ascii")
    _ = layout.pytest_launcher.write_text("stale", encoding="ascii")
    python_validation.write_launchers(layout, windows=windows)
    first = (
        layout.python_launcher.read_bytes(),
        layout.pytest_launcher.read_bytes(),
    )
    python_validation.write_launchers(layout, windows=windows)
    second = (
        layout.python_launcher.read_bytes(),
        layout.pytest_launcher.read_bytes(),
    )
    assert first == second
    assert STALE_LAUNCHER_BYTES not in first
    if windows:
        assert all(payload.startswith(b"@echo off\r\n") for payload in first)
    else:
        assert all(payload.startswith(b"#!/bin/sh\n") for payload in first)
        assert all(
            target.stat().st_mode & stat.S_IXUSR
            for target in (layout.python_launcher, layout.pytest_launcher)
        )


@pytest.mark.parametrize(
    "receipt",
    (
        "wrong-argv",
        "tuple-argv",
        "foreign-argv",
        "foreign-token",
        "boolean-exit",
        "binary-stdout",
        "foreign-stderr",
        "foreign-completion",
        "mutated-argv",
    ),
)
def test_python_bootstrap_rejects_foreign_command_receipts(
    monkeypatch: pytest.MonkeyPatch,
    receipt: str,
) -> None:
    """A forged or mutated uv version probe must not certify a bootstrap."""

    class ForeignArg(str):
        @override
        def __eq__(self, _other: object) -> bool:
            raise AssertionError("foreign command equality hook executed")

    class ForeignArgv(list[str]):
        @override
        def __eq__(self, _other: object) -> bool:
            raise AssertionError("foreign argv equality hook executed")

    class ForeignCompletion(sp.CompletedProcess[str]):
        pass

    command = ["uv", "--version"]

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        if receipt == "mutated-argv":
            args[0] = "foreign-uv"
        received: object = {
            "wrong-argv": ["foreign-uv", "--version"],
            "tuple-argv": tuple(args),
            "foreign-argv": ForeignArgv(args),
            "foreign-token": [ForeignArg(args[0]), *args[1:]],
        }.get(receipt, args)
        exit_code = cast("int", False) if receipt == "boolean-exit" else 0
        stdout = (
            cast("str", cast("object", b"uv 0.12.20"))
            if receipt == "binary-stdout"
            else "uv 0.12.20\n"
        )
        stderr = (
            cast("str", cast("object", True)) if receipt == "foreign-stderr" else ""
        )
        if receipt == "foreign-completion":
            return ForeignCompletion(
                cast("list[str]", received), exit_code, stdout, stderr
            )
        return sp.CompletedProcess(
            cast("list[str]", received), exit_code, stdout, stderr
        )

    monkeypatch.setattr(sp, "run", run)
    with pytest.raises(python_validation.ProvisionError, match="process receipt"):
        _ = python_validation._run(command)  # pyright: ignore[reportPrivateUsage]
    assert command == ["uv", "--version"]


def test_python_bootstrap_accepts_native_command_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A native exact uv response retains its expected version output."""

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(args, 0, stdout="uv 0.12.20\n", stderr="")

    monkeypatch.setattr(sp, "run", run)
    actual = python_validation._run(["uv", "--version"])  # pyright: ignore[reportPrivateUsage]
    assert actual == "uv 0.12.20"


@pytest.mark.parametrize(
    "kind", ("os", "foreign-os", "value", "type", "runtime", "nonzero")
)
def test_python_bootstrap_converts_launch_failures_to_typed_errors(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Bootstrap process host failures retain causes without foreign hooks."""

    class ForeignOSError(PermissionError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign bootstrap exception formatter executed")

    errors: dict[str, Exception] = {
        "os": OSError("launch failed"),
        "foreign-os": ForeignOSError("injected"),
        "value": ValueError("invalid arguments"),
        "type": TypeError("invalid launcher"),
        "runtime": RuntimeError("runner error"),
        "nonzero": sp.CalledProcessError(7, ["uv", "--version"]),
    }
    error = errors[kind]

    def fail(_args: list[str], **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(sp, "run", fail)
    with pytest.raises(
        python_validation.ProvisionError, match="bootstrap command"
    ) as caught:
        _ = python_validation._run(["uv", "--version"])  # pyright: ignore[reportPrivateUsage]
    assert caught.value.__cause__ is error
    assert ("ForeignOSError" in str(caught.value)) == (kind == "foreign-os")


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_optional_host_probe_rejects_oversized_native_output(
    monkeypatch: pytest.MonkeyPatch,
    stream: str,
) -> None:
    """Optional host output is bounded even when the process claims success."""
    command = ["git", "--version"]
    huge = "x" * (project.MAX_AUTHORITY_BYTES + 1)
    stdout = huge if stream == "stdout" else "git version 2.55.0\n"
    stderr = huge if stream == "stderr" else ""

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(args, 0, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(sp, "run", run)
    assert (
        project._optional_host_command_output(command) is None  # pyright: ignore[reportPrivateUsage]
    )


@pytest.mark.parametrize(
    "output",
    [
        " git version 2.55.0\n",
        "git version 2.55.0 \n",
        "git version 2.55.0\n\n",
        "git version 2.55.0\r",
        "git version 2.55.0\n\t",
    ],
)
def test_host_git_probe_rejects_normalized_noncanonical_version_receipt(
    monkeypatch: pytest.MonkeyPatch, output: str
) -> None:
    """Whitespace stripping cannot manufacture a matching pinned banner."""

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(args, 0, stdout=output, stderr="")

    monkeypatch.setattr(sp, "run", run)
    observed = project._run_git_version(  # pyright: ignore[reportPrivateUsage]
        Path("git")
    )
    assert observed is None or not project.git_version_line_matches(
        GIT_VERSION, observed
    )


@pytest.mark.parametrize("terminator", ["", "\n", "\r\n"])
def test_host_git_probe_accepts_canonical_version_line_end(
    monkeypatch: pytest.MonkeyPatch, terminator: str
) -> None:
    """The Git banner accepts only native single-line terminations."""

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(
            args, 0, stdout=f"git version {GIT_VERSION}{terminator}", stderr=""
        )

    monkeypatch.setattr(sp, "run", run)
    assert project._run_git_version(  # pyright: ignore[reportPrivateUsage]
        Path("git")
    ) == f"git version {GIT_VERSION}"


@pytest.mark.parametrize(
    "probe", ("git-version", "git-exec", "rustup-list", "rustup-which")
)
@pytest.mark.parametrize(
    "diagnostic", ("warning: using fallback Git", "\x1b[31mfailed\x1b[0m")
)
def test_optional_host_probes_reject_success_with_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    diagnostic: str,
) -> None:
    """A successful exit cannot certify conflicting host diagnostic output."""
    stdout = {
        "git-version": "git version 2.55.0\n",
        "git-exec": f"{tmp_path}\n",
        "rustup-list": "1.98.1 (default)\n",
        "rustup-which": f"{tmp_path / 'bin/cargo'}\n",
    }[probe]

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(args, 0, stdout=stdout, stderr=diagnostic)

    monkeypatch.setattr(sp, "run", run)
    if probe == "git-version":
        observed: object = project._run_git_version(Path("git"))  # pyright: ignore[reportPrivateUsage]
    elif probe == "git-exec":
        observed = project._run_git_exec_path(Path("git"))  # pyright: ignore[reportPrivateUsage]
    elif probe == "rustup-list":
        observed = project._run_rustup_list(Path("rustup"))  # pyright: ignore[reportPrivateUsage]
    else:
        observed = project._run_rustup_which(Path("rustup"), RUST_CHANNEL)  # pyright: ignore[reportPrivateUsage]
    assert observed == (() if probe == "rustup-list" else None)


@pytest.mark.parametrize(
    "output",
    [
        "1.98.1\r",
        "1.98.1\v",
        "1.98.1 (default)\x00",
        "1.98.1\n\n",
        "1.98.1\n\x00invalid\n",
        " 1.98.1 (default)\n",
        "1.98.1 (default) \n",
    ],
)
def test_rustup_inventory_rejects_hidden_or_padded_members(
    monkeypatch: pytest.MonkeyPatch, output: str
) -> None:
    """Malformed list receipts cannot certify a pinned Rustup channel."""

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(args, 0, stdout=output, stderr="")

    monkeypatch.setattr(sp, "run", run)
    inventory = project._run_rustup_list(  # pyright: ignore[reportPrivateUsage]
        Path("rustup")
    )
    assert not project.rustup_channel_is_installed(RUST_CHANNEL, inventory)


def test_rustup_inventory_accepts_native_multiline_crlf(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """Normal Windows line endings preserve exact installed toolchain names."""
    output = "1.98.1-x86_64-unknown-linux-gnu (default)\r\nnightly-2026-07-14\r\n"

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(args, 0, stdout=output, stderr="")

    monkeypatch.setattr(sp, "run", run)
    inventory = project._run_rustup_list(  # pyright: ignore[reportPrivateUsage]
        Path("rustup")
    )
    assert inventory == ("1.98.1-x86_64-unknown-linux-gnu", RUST_NIGHTLY_CHANNEL)


@pytest.mark.parametrize(
    "probe", ("git-version", "git-exec", "rustup-list", "rustup-which")
)
@pytest.mark.parametrize(
    "mutation",
    ("wrong-argv", "mutated-argv", "false-status", "binary-output", "foreign-receipt"),
)
def test_optional_host_probes_reject_forged_process_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    mutation: str,
) -> None:
    """Git and rustup discovery cannot trust forged native process results."""

    class ForeignCompletion(sp.CompletedProcess[str]):
        pass

    version_output = {
        "git-version": "git version 2.55.0\n",
        "git-exec": f"{tmp_path}\n",
        "rustup-list": "1.98.1-x86_64-unknown-linux-gnu (default)\n",
        "rustup-which": f"{tmp_path / 'bin/cargo'}\n",
    }[probe]

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        if mutation == "mutated-argv":
            args[0] = "foreign-tool"
        argv = ["foreign-tool", *args[1:]] if mutation == "wrong-argv" else args
        status = cast("int", False) if mutation == "false-status" else 0
        stdout = (
            cast("str", cast("object", version_output.encode("utf-8")))
            if mutation == "binary-output"
            else version_output
        )
        if mutation == "foreign-receipt":
            return ForeignCompletion(argv, status, stdout, "")
        return sp.CompletedProcess(argv, status, stdout, "")

    monkeypatch.setattr(sp, "run", run)
    if probe == "git-version":
        observed: object = project._run_git_version(Path("git"))  # pyright: ignore[reportPrivateUsage]
    elif probe == "git-exec":
        observed = project._run_git_exec_path(Path("git"))  # pyright: ignore[reportPrivateUsage]
    elif probe == "rustup-list":
        observed = project._run_rustup_list(Path("rustup"))  # pyright: ignore[reportPrivateUsage]
    else:
        observed = project._run_rustup_which(Path("rustup"), RUST_CHANNEL)  # pyright: ignore[reportPrivateUsage]
    assert observed == (() if probe == "rustup-list" else None)


@pytest.mark.parametrize(
    "probe", ("git-version", "git-exec", "rustup-list", "rustup-which")
)
def test_optional_host_probes_admit_native_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
) -> None:
    """Real success receipts retain host Git and rustup query output."""
    tool_root = tmp_path / "toolchain"
    tool_root.mkdir()
    results: dict[str, tuple[str, object]] = {
        "git-version": ("git version 2.55.0\n", "git version 2.55.0"),
        "git-exec": (f"{tmp_path}\n", tmp_path),
        "rustup-list": (
            "1.98.1 (default)\nnightly-2026-07-14\n",
            ("1.98.1", "nightly-2026-07-14"),
        ),
        "rustup-which": (f"{tool_root / 'bin/cargo'}\n", str(tool_root / "bin/cargo")),
    }

    def run(args: list[str], **kwargs: object) -> sp.CompletedProcess[str]:
        assert kwargs["timeout"] == 15
        return sp.CompletedProcess(args, 0, results[probe][0], "")

    monkeypatch.setattr(sp, "run", run)
    if probe == "git-version":
        observed: object = project._run_git_version(Path("git"))  # pyright: ignore[reportPrivateUsage]
    elif probe == "git-exec":
        observed = project._run_git_exec_path(Path("git"))  # pyright: ignore[reportPrivateUsage]
    elif probe == "rustup-list":
        observed = project._run_rustup_list(Path("rustup"))  # pyright: ignore[reportPrivateUsage]
    else:
        observed = project._run_rustup_which(Path("rustup"), RUST_CHANNEL)  # pyright: ignore[reportPrivateUsage]
    assert observed == results[probe][1]


@pytest.mark.parametrize(
    "probe", ("git-version", "git-exec", "rustup-list", "rustup-which")
)
@pytest.mark.parametrize(
    "fault", ("os", "foreign-os", "value", "type", "runtime", "timeout")
)
def test_optional_host_probes_fail_closed_on_host_exceptions(
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    fault: str,
) -> None:
    """Missing or unresponsive optional tooling cannot crash checkout probes."""

    class ForeignHostOSError(PermissionError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign optional-host formatter invoked")

    faults: dict[str, Exception] = {
        "os": OSError("missing executable"),
        "foreign-os": ForeignHostOSError("missing executable"),
        "value": ValueError("bad query"),
        "type": TypeError("bad runner"),
        "runtime": RuntimeError("runner crashed"),
        "timeout": sp.TimeoutExpired(["git"], 15),
    }
    observed_fault = faults[fault]

    def failed_run(_args: list[str], **kwargs: object) -> None:
        assert kwargs["timeout"] == 15
        raise observed_fault

    monkeypatch.setattr(sp, "run", failed_run)
    if probe == "git-version":
        observed: object = project._run_git_version(Path("git"))  # pyright: ignore[reportPrivateUsage]
    elif probe == "git-exec":
        observed = project._run_git_exec_path(Path("git"))  # pyright: ignore[reportPrivateUsage]
    elif probe == "rustup-list":
        observed = project._run_rustup_list(Path("rustup"))  # pyright: ignore[reportPrivateUsage]
    else:
        observed = project._run_rustup_which(Path("rustup"), RUST_CHANNEL)  # pyright: ignore[reportPrivateUsage]
    assert observed == (() if probe == "rustup-list" else None)


@pytest.mark.parametrize("bad_path", ["relative", "control"])
def test_host_git_exec_path_rejects_ambiguous_directory_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_path: str
) -> None:
    """Git helper roots must be stable absolute printable paths."""
    if bad_path == "control" and os.name != POSIX_NAME:
        pytest.skip("native test filesystem does not support control paths")
    target = (
        Path("relative/git-core")
        if bad_path == "relative"
        else tmp_path / "git\ncore"
    )
    monkeypatch.chdir(tmp_path)
    target.mkdir(parents=True)

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(args, 0, stdout=f"{target}\n", stderr="")

    monkeypatch.setattr(sp, "run", run)
    assert project._run_git_exec_path(  # pyright: ignore[reportPrivateUsage]
        Path("git")
    ) is None


@pytest.mark.parametrize("probe", ("git-helper", "rustup-cargo"))
@pytest.mark.parametrize("receipt", (None, 0, 1, "yes", "foreign-bool"))
def test_optional_host_tool_paths_require_native_status_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    receipt: object,
) -> None:
    """A fake file/dir truthiness result cannot certify imported host tooling."""

    class ForeignBool:
        def __bool__(self) -> Never:
            raise AssertionError("foreign host path truthiness executed")

    candidate = tmp_path / ("git-core" if probe == "git-helper" else "bin/cargo")
    fake: object = ForeignBool() if receipt == "foreign-bool" else receipt
    method = "is_dir" if probe == "git-helper" else "is_file"
    original = getattr(Path, method)

    def fake_status(self: Path) -> object:
        return fake if self == candidate else original(self)

    monkeypatch.setattr(Path, method, fake_status)
    if probe == "git-helper":
        def helper_output(_argv: list[str]) -> str:
            return str(candidate)

        monkeypatch.setattr(project, "_optional_host_command_output", helper_output)
        result: object = project._run_git_exec_path(Path("git"))  # pyright: ignore[reportPrivateUsage]
    else:
        result = project.rustup_toolchain_root(
            Path("rustup"), RUST_CHANNEL, runner=lambda _tool, _channel: str(candidate)
        )
    assert result is None


@pytest.mark.parametrize("probe", ("git-helper", "rustup-cargo"))
@pytest.mark.parametrize("fault_type", (OSError, ValueError, TypeError, RuntimeError))
def test_optional_host_tool_paths_treat_native_stat_failures_as_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    fault_type: type[Exception],
) -> None:
    """Optional host path inspection errors do not crash the checkout."""
    candidate = tmp_path / ("git-core" if probe == "git-helper" else "bin/cargo")
    method = "is_dir" if probe == "git-helper" else "is_file"
    original = getattr(Path, method)
    fault = fault_type("bad host path receipt")

    def fail_status(self: Path) -> object:
        if self == candidate:
            raise fault
        return original(self)

    monkeypatch.setattr(Path, method, fail_status)
    if probe == "git-helper":
        def helper_output(_argv: list[str]) -> str:
            return str(candidate)

        monkeypatch.setattr(project, "_optional_host_command_output", helper_output)
        result: object = project._run_git_exec_path(Path("git"))  # pyright: ignore[reportPrivateUsage]
    else:
        result = project.rustup_toolchain_root(
            Path("rustup"), RUST_CHANNEL, runner=lambda _tool, _channel: str(candidate)
        )
    assert result is None


@pytest.mark.parametrize(
    "platform_id,expected_tool",
    [
        ("windowsfake-x86_64", "jig"),
        ("linuxfake-x86_64", "jig"),
        (WINDOWS_PLATFORM, "jig.cmd"),
        (LINUX_PLATFORM, "jig"),
    ],
)
def test_jig_platform_tool_name_uses_exact_os_token(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    platform_id: str,
    expected_tool: str,
) -> None:
    """An unknown OS prefix cannot impersonate a Windows host."""
    queried: list[str] = []

    def lookup(name: str) -> None:
        queried.append(name)

    monkeypatch.setattr(project, "which", lookup)
    status = project.inspect_jig(tmp_path, platform_id)
    assert status.state is project.ComponentState.MISSING
    assert queried == [expected_tool]


@pytest.mark.parametrize("tool", ["git", "rustup"])
def test_optional_host_discovery_rejects_windows_like_platform_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tool: str
) -> None:
    """Unknown Windows-like prefixes must not select .exe tool variants."""
    queried: list[str] = []

    def lookup(name: str) -> None:
        queried.append(name)

    monkeypatch.setattr(project, "which", lookup)
    if tool == "git":
        assert project.observe_host_git("windowslike-x86_64") is None
    else:
        assert (
            project.rustup_executable("windowslike-x86_64", home=tmp_path)
            is None
        )
    assert queried == [tool]


@pytest.mark.parametrize(
    "receipt", [None, "", "   ", 7, True, "foreign-string"]
)
def test_jig_observation_rejects_foreign_path_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """An optional Jig lookup must supply a native nonblank path."""

    @final
    class ForeignString(str):
        __slots__ = ()

        def __bool__(self) -> Never:
            message = "foreign Jig path truthiness executed"
            raise AssertionError(message)

    observed: object = (
        ForeignString(str(tmp_path / "jig"))
        if receipt == "foreign-string"
        else receipt
    )

    def lookup(_name: str) -> str | None:
        return cast("str | None", observed)

    monkeypatch.setattr(project, "which", lookup)
    assert (
        project.inspect_jig(tmp_path, LINUX_PLATFORM).state
        is project.ComponentState.MISSING
    )


@pytest.mark.parametrize("path_text", ["bin/jig", "../jig", "/tmp/jig\n", "/tmp/jig\t"])
def test_jig_observation_rejects_unstable_launcher_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path_text: str
) -> None:
    """Jig readiness must not trust relative or nonprintable PATH outputs."""
    monkeypatch.setattr(project, "which", lambda _name: path_text)
    status = project.inspect_jig(tmp_path, LINUX_PLATFORM)
    assert status.state is project.ComponentState.MISSING
    assert status.path is None


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_jig_observation_tolerates_optional_discovery_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Jig presence is optional when PATH discovery fails."""

    def fail(_name: str) -> str:
        raise fault_type("cannot discover Jig")

    monkeypatch.setattr(project, "which", fail)
    assert (
        project.inspect_jig(tmp_path, WINDOWS_PLATFORM).state
        is project.ComponentState.MISSING
    )


def test_jig_observation_accepts_native_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A native resolved launcher remains available as diagnostic evidence."""
    executable = tmp_path / "jig"
    _ = executable.write_bytes(b"jig")

    def lookup(_name: str) -> str:
        return str(executable)

    monkeypatch.setattr(project, "which", lookup)
    status = project.inspect_jig(tmp_path, LINUX_PLATFORM)
    assert status.state is project.ComponentState.READY
    assert status.path == executable


def _import_host_component(
    source: Path, destination: Path, component: str
) -> None:
    """Invoke the selected Git or Rust import in hostile-path tests."""
    if component == GIT_COMPONENT:
        _ = project.import_git_installation(
            source / "bin/git", source, destination, windows=False
        )
    else:
        _ = project.import_rust_toolchain(
            source, destination, tool_ids=("cargo",), windows=False
        )


def _make_import_race_source(tmp_path: Path) -> Path:
    """Prepare the same physical host tools for Git and Rust import races.

    Returns:
        Directory containing both host executables.

    """
    source = tmp_path / "host"
    (source / "bin").mkdir(parents=True)
    _ = (source / "bin/git").write_bytes(GIT_BYTES)
    _ = (source / "bin/cargo").write_bytes(RUST_CARGO_BYTES)
    return source


def _prepare_import_root_swap(
    tmp_path: Path, component: str, *, sentinel: bytes = FOREIGN_ROOT_BYTES
) -> tuple[Path, Path, Path, Path]:
    """Prepare import and foreign directories before pathname substitution.

    Returns:
        Host source, import destination, parked root, and foreign root.

    """
    source = _make_import_race_source(tmp_path)
    destination = tmp_path / ".dependencies" / component / GIT_VERSION
    parked = tmp_path / "retained-import"
    foreign = tmp_path / "foreign-import"
    (foreign / "bin").mkdir(parents=True)
    _ = (foreign / "sentinel").write_bytes(sentinel)
    return source, destination, parked, foreign


def _make_rust_import_source(tmp_path: Path) -> Path:
    """Prepare physical Rust tools with sysroot, mode and source symlink.

    Returns:
        Host source root for nested copy and hardlink fallback tests.

    """
    source = tmp_path / "host-rust"
    (source / "bin").mkdir(parents=True)
    (source / "lib/rustlib").mkdir(parents=True)
    cargo = source / "bin/cargo"
    _ = cargo.write_bytes(RUST_CARGO_BYTES)
    cargo.chmod(0o700)
    _ = (source / "lib/rustlib/manifest").write_bytes(RUST_STD_BYTES)
    _ = (source / "lib/rustlib/manifest-link").symlink_to("manifest")
    return source


def _prepare_rust_nested_destination(
    tmp_path: Path, destination: Path
) -> tuple[Path, Path, Path]:
    """Set up the nested destination swap and separate foreign directory.

    Returns:
        Nested import directory, parked directory and foreign directory.

    """
    rustlib = destination / "lib/rustlib"
    parked = tmp_path / "retained-rustlib"
    foreign = tmp_path / "foreign-rustlib"
    foreign.mkdir()
    _ = (foreign / "sentinel").write_bytes(FOREIGN_RUSTLIB_BYTES)
    return rustlib, parked, foreign


def _prepare_foreign_rust_toolchain(tmp_path: Path) -> Path:
    """Prepare a foreign toolchain with its own executable and sentinel.

    Returns:
        A directory that must remain untouched by the import operation.

    """
    foreign = tmp_path / "foreign-toolchain"
    (foreign / "bin").mkdir(parents=True)
    _ = (foreign / "bin/cargo").write_bytes(b"outside-cargo")
    _ = (foreign / "sentinel").write_bytes(FOREIGN_TOOLCHAIN_BYTES)
    return foreign


def _assert_import_copy_swap_state(
    destination: Path, parked: Path, foreign_root: Path, *, component: str
) -> None:
    """Verify import root substitution does not populate the foreign tree."""
    native_name = "git" if component == GIT_COMPONENT else "cargo"
    payload = GIT_BYTES if component == GIT_COMPONENT else RUST_CARGO_BYTES
    assert (foreign_root / "sentinel").read_bytes() == FOREIGN_IMPORT_BYTES
    assert not (foreign_root / "bin" / native_name).exists()
    assert (parked / "bin" / native_name).read_bytes() == payload
    assert not project.git_import_complete(destination)
    assert not project.rust_toolchain_import_complete(destination)


def _prepare_import_parent_swap(
    tmp_path: Path, component: str
) -> tuple[Path, Path, Path, Path, Path]:
    """Create the physical host, absent import and foreign parent for races.

    Returns:
        Host source, import destination, import parent, parked parent, foreign.

    """
    source = _make_import_race_source(tmp_path)
    destination = tmp_path / ".dependencies" / component / GIT_VERSION
    parent = destination.parent
    parent.mkdir(parents=True)
    parked = tmp_path / "retained-parent"
    foreign = tmp_path / "foreign-parent"
    foreign.mkdir()
    _ = (foreign / "sentinel").write_bytes(FOREIGN_PARENT_BYTES)
    return source, destination, parent, parked, foreign


def _assert_import_parent_swap_state(
    foreign_root: Path, destination: Path
) -> None:
    """Verify foreign parent remains inert after attempted import creation."""
    assert (foreign_root / "sentinel").read_bytes() == FOREIGN_PARENT_BYTES
    assert not (foreign_root / GIT_VERSION).exists()
    assert not project.git_import_complete(destination)
    assert not project.rust_toolchain_import_complete(destination)


def _assert_nested_rust_import_state(foreign_root: Path, parked: Path) -> None:
    """Prove the nested replacement was not written and the old tree was."""
    assert (foreign_root / "sentinel").read_bytes() == FOREIGN_RUSTLIB_BYTES
    assert not (foreign_root / "manifest").exists()
    assert (parked / "manifest").read_bytes() == RUST_STD_BYTES


@pytest.mark.skipif(
    os.name != POSIX_NAME, reason="POSIX import descriptor race"
)
@pytest.mark.parametrize("component", ["git", "rust"])
@pytest.mark.parametrize("substitution", ["symlink", "physical"])
def test_import_copy_never_writes_to_replaced_destination_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    component: str,
    *,
    substitution: str,
) -> None:
    """A late imported-root exchange must never populate a foreign bin tree."""
    source, destination, parked, foreign = _prepare_import_root_swap(
        tmp_path, component, sentinel=FOREIGN_IMPORT_BYTES
    )
    native_name = "git" if component == GIT_COMPONENT else "cargo"
    native_link = os.link
    swapped = False

    def exchange_on_copy(  # ruff: ignore[too-many-arguments]
        source_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        target_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal swapped
        if not swapped and Path(os.fsdecode(target_path)).name == native_name:
            _ = destination.rename(parked)
            if substitution == SYMLINK_SUBSTITUTION:
                destination.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(destination)
            swapped = True
        native_link(
            source_path,
            target_path,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", exchange_on_copy)
        with pytest.raises(project.InitializationError, match="parent changed"):
            _import_host_component(source, destination, component)
    assert swapped
    foreign_root = (
        foreign if substitution == SYMLINK_SUBSTITUTION else destination
    )
    _assert_import_copy_swap_state(
        destination, parked, foreign_root, component=component
    )


@pytest.mark.skipif(os.name != POSIX_NAME, reason="POSIX import directory race")
@pytest.mark.parametrize("component", ["git", "rust"])
@pytest.mark.parametrize("substitution", ["symlink", "physical"])
def test_import_root_parent_swap_before_creation_preserves_foreign_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    component: str,
    *,
    substitution: str,
) -> None:
    """Parent replacement after admission cannot create under a foreign root."""
    source, destination, parent, parked, foreign = _prepare_import_parent_swap(
        tmp_path, component
    )
    original_admit = cast(
        "Callable[[Path, str], None]",
        vars(project)["_admit_import_destination"],
    )
    swapped = False

    def exchange_after_admission(path: Path, label: str) -> None:
        nonlocal swapped
        original_admit(path, label)
        if not swapped:
            _ = parent.rename(parked)
            if substitution == SYMLINK_SUBSTITUTION:
                parent.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(parent)
            swapped = True

    with monkeypatch.context() as isolated:
        isolated.setattr(
            project, "_admit_import_destination", exchange_after_admission
        )
        with pytest.raises(project.InitializationError, match="parent changed"):
            _import_host_component(source, destination, component)
    assert swapped
    foreign_root = foreign if substitution == SYMLINK_SUBSTITUTION else parent
    _assert_import_parent_swap_state(foreign_root, destination)


@pytest.mark.skipif(
    os.name != POSIX_NAME, reason="POSIX import descriptor race"
)
@pytest.mark.parametrize("substitution", ["symlink", "physical"])
def test_rust_import_nested_directory_swap_cannot_write_to_foreign_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, substitution: str
) -> None:
    """Descriptor-held nested Rust sysroot imports never follow a new parent."""
    source = _make_rust_import_source(tmp_path)
    destination = tmp_path / ".dependencies/rust" / GIT_VERSION
    rustlib, parked, foreign = _prepare_rust_nested_destination(
        tmp_path, destination
    )
    native_link = os.link
    swapped = False

    def swap_during_nested_copy(  # ruff: ignore[too-many-arguments]
        source_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        target_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal swapped
        if (
            not swapped
            and Path(os.fsdecode(target_path)).name == IMPORT_MANIFEST
        ):
            _ = rustlib.rename(parked)
            if substitution == SYMLINK_SUBSTITUTION:
                _ = rustlib.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(rustlib)
            swapped = True
        native_link(
            source_path,
            target_path,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", swap_during_nested_copy)
        with pytest.raises(project.InitializationError, match="parent changed"):
            _ = project.import_rust_toolchain(
                source, destination, tool_ids=("cargo",), windows=False
            )
    foreign_root = foreign if substitution == SYMLINK_SUBSTITUTION else rustlib
    _assert_nested_rust_import_state(foreign_root, parked)
    assert swapped
    assert not project.rust_toolchain_import_complete(destination)


@pytest.mark.skipif(
    os.name != POSIX_NAME, reason="POSIX import descriptor copy"
)
def test_rust_import_file_copy_fallback_and_source_links(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Restricted hardlinks preserve native executable and symlink semantics."""
    source = _make_rust_import_source(tmp_path)
    alias_source = tmp_path / "source-alias"
    _ = alias_source.symlink_to(source, target_is_directory=True)
    destination = tmp_path / ".dependencies/rust" / GIT_VERSION
    original_link = os.link
    blocked: set[str] = set()

    def deny_import_hardlink(  # ruff: ignore[too-many-arguments]
        from_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        to_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        if Path(os.fsdecode(to_path)).name in {"cargo", "manifest"}:
            blocked.add(Path(os.fsdecode(to_path)).name)
            reason = "host hardlink restricted"
            raise OSError(reason)
        original_link(
            from_path,
            to_path,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", deny_import_hardlink)
        aliases = project.import_rust_toolchain(
            alias_source, destination, tool_ids=("cargo",), windows=False
        )
    assert blocked == {"cargo", "manifest"}
    assert aliases == (destination / "bin/cargo.bin",)
    assert (destination / "bin/cargo").read_bytes() == RUST_CARGO_BYTES
    assert (destination / "bin/cargo").stat().st_mode & stat.S_IXUSR
    assert (destination / "lib/rustlib/manifest").read_bytes() == RUST_STD_BYTES
    assert (destination / "lib/rustlib/manifest-link").is_symlink()
    assert project.rust_toolchain_import_complete(destination)


@pytest.mark.skipif(os.name != POSIX_NAME, reason="POSIX import file identity")
@pytest.mark.parametrize("transport", ["hardlink", "copy", "copy-restored-mtime"])
def test_rust_import_rejects_same_inode_source_byte_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    transport: str,
) -> None:
    """Stable inode numbers cannot certify a changed host tool payload."""
    source = _make_rust_import_source(tmp_path)
    cargo = source / "bin/cargo"
    destination = tmp_path / ".dependencies/rust" / GIT_VERSION
    original_link = os.link
    original_copy = cast(
        "Callable[[int, int], None]", vars(project)["_write_import_file_payload"]
    )
    mutated = False

    def mutate_cargo() -> None:
        nonlocal mutated
        before = cargo.stat()
        _ = cargo.write_bytes(b"X" * len(RUST_CARGO_BYTES))
        changed_mtime = (
            before.st_mtime_ns
            if transport == "copy-restored-mtime"
            else before.st_mtime_ns + 1_000_000_000
        )
        os.utime(cargo, ns=(before.st_atime_ns, changed_mtime))
        mutated = True

    def link_or_rewrite(  # ruff: ignore[too-many-arguments]
        source_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        target_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        if Path(os.fsdecode(target_path)).name == CARGO_FILENAME:
            if transport.startswith("copy"):
                raise OSError("hardlink not supported")
            original_link(
                source_path, target_path, src_dir_fd=src_dir_fd,
                dst_dir_fd=dst_dir_fd, follow_symlinks=follow_symlinks,
            )
            mutate_cargo()
            return
        original_link(
            source_path, target_path, src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd, follow_symlinks=follow_symlinks,
        )

    def copy_then_rewrite(input_fd: int, output_fd: int) -> None:
        original_copy(input_fd, output_fd)
        if transport.startswith("copy") and not mutated:
            mutate_cargo()

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", link_or_rewrite)
        isolated.setattr(project, "_write_import_file_payload", copy_then_rewrite)
        with pytest.raises(project.InitializationError, match="changed during copy"):
            _ = project.import_rust_toolchain(
                source, destination, tool_ids=("cargo",), windows=False
            )
    assert mutated
    assert not project.rust_toolchain_import_complete(destination)


@pytest.mark.skipif(
    os.name != POSIX_NAME, reason="POSIX import hardlink identity"
)
@pytest.mark.parametrize("mutation", ["source", "destination"])
def test_rust_import_rejects_same_size_file_swap_after_hardlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """A forged same-size file cannot pass imported file inode verification."""
    source = tmp_path / "host-rust"
    (source / "bin").mkdir(parents=True)
    cargo = source / "bin/cargo"
    _ = cargo.write_bytes(RUST_CARGO_BYTES)
    destination = tmp_path / ".dependencies/rust" / GIT_VERSION
    native_link = os.link
    swapped = False

    def swap_after_link(  # ruff: ignore[too-many-arguments]
        source_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination_path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal swapped
        native_link(
            source_path,
            destination_path,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )
        if (
            not swapped
            and Path(os.fsdecode(destination_path)).name == CARGO_FILENAME
        ):
            target = (
                cargo
                if mutation == IMPORT_SOURCE_MUTATION
                else destination / "bin/cargo"
            )
            _ = target.unlink()
            _ = target.write_bytes(b"X" * len(RUST_CARGO_BYTES))
            swapped = True

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", swap_after_link)
        with pytest.raises(
            project.InitializationError, match="changed during copy"
        ):
            _ = project.import_rust_toolchain(
                source, destination, tool_ids=("cargo",), windows=False
            )
    assert swapped
    assert not project.rust_toolchain_import_complete(destination)


@pytest.mark.skipif(
    os.name != POSIX_NAME, reason="POSIX import completion race"
)
@pytest.mark.parametrize("component", ["git", "rust"])
@pytest.mark.parametrize("substitution", ["symlink", "physical"])
def test_import_completion_rejects_late_replaced_destination_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    component: str,
    *,
    substitution: str,
) -> None:
    """Late root replacement must not receive a false completion marker."""
    source, destination, parked, foreign = _prepare_import_root_swap(
        tmp_path, component
    )
    original_write = cast(
        "Callable[..., None]",
        vars(project)["_write_import_completion_marker_at_parent"],
    )
    swapped = False

    def swap_before_marker(
        marker: Path,
        content: str,
        parent_fd: int | None,
        *,
        executable: bool = False,
    ) -> None:
        nonlocal swapped
        if not swapped:
            _ = destination.rename(parked)
            if substitution == SYMLINK_SUBSTITUTION:
                _ = destination.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(destination)
            swapped = True
        original_write(marker, content, parent_fd, executable=executable)

    with monkeypatch.context() as isolated:
        isolated.setattr(
            project,
            "_write_import_completion_marker_at_parent",
            swap_before_marker,
        )
        with pytest.raises(
            project.InitializationError,
            match=r"parent changed|must not redirect|marker creation failed",
        ):
            _import_host_component(source, destination, component)
    assert swapped
    foreign_root = (
        foreign if substitution == SYMLINK_SUBSTITUTION else destination
    )
    assert (foreign_root / "sentinel").read_bytes() == FOREIGN_ROOT_BYTES
    assert not (foreign_root / project.GIT_IMPORT_MARKER).exists()
    assert not (foreign_root / project.RUST_IMPORT_MARKER).exists()


@pytest.mark.skipif(os.name != POSIX_NAME, reason="POSIX Rust alias race")
@pytest.mark.parametrize("substitution", ["symlink", "physical"])
def test_rust_import_alias_rejects_replaced_root_before_alias_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, substitution: str
) -> None:
    """Imported Rust bin identity must remain bound through alias creation."""
    source = _make_rust_import_source(tmp_path)
    destination = tmp_path / ".dependencies/rust" / GIT_VERSION
    parked = tmp_path / "retained-toolchain"
    foreign = _prepare_foreign_rust_toolchain(tmp_path)
    native_aliases = cast(
        "Callable[..., tuple[Path, ...]]",
        vars(project)["_ensure_rust_toolchain_aliases"],
    )
    swapped = False

    def exchange_before_aliases(
        root: Path,
        tools: tuple[str, ...],
        *,
        windows: bool,
        expected_bin_identity: tuple[int, int] | None = None,
        require_absent: bool = False,
    ) -> tuple[Path, ...]:
        nonlocal swapped
        if not swapped:
            _ = destination.rename(parked)
            if substitution == SYMLINK_SUBSTITUTION:
                _ = destination.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(destination)
            swapped = True
        return native_aliases(
            root,
            tools,
            windows=windows,
            expected_bin_identity=expected_bin_identity,
            require_absent=require_absent,
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(
            project, "_ensure_rust_toolchain_aliases", exchange_before_aliases
        )
        with pytest.raises(
            project.InitializationError,
            match=r"directory|parent|must not redirect",
        ):
            _ = project.import_rust_toolchain(
                source, destination, tool_ids=("cargo",), windows=False
            )
    assert swapped
    foreign_root = (
        foreign if substitution == SYMLINK_SUBSTITUTION else destination
    )
    assert (foreign_root / "sentinel").read_bytes() == FOREIGN_TOOLCHAIN_BYTES
    assert not (foreign_root / "bin/cargo.bin").exists()
    assert not (foreign_root / project.RUST_IMPORT_MARKER).exists()
