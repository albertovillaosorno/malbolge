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
import json
import os
import stat
from typing import TYPE_CHECKING
from typing import cast

import pytest
from scripts.bootstrap import project
from scripts.bootstrap import python_validation

if TYPE_CHECKING:
    from pathlib import Path

CUDA_VERSION_ROOT = ".dependencies/cuda/13.3.1/toolkit"
WINDOWS_PLATFORM = "windows-x86_64"
LINUX_PLATFORM = "linux-x86_64"
WINDOWS_CHANNEL = "stable-1.97.1-x86_64-pc-windows-gnu"
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
LINUX_AARCH64 = "linux-aarch64"
UV_VERSION = "0.11.16"
PIP_REQUIREMENT_PREFIX = "pip=="
VALIDATION_REQUIREMENT_COUNT = 9
WINDOWS_UV_ASSET = "uv-x86_64-pc-windows-msvc.zip"


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


def _write_rust_manifest(root: Path, channel: str = WINDOWS_CHANNEL) -> Path:
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
    assert executable == (
        tmp_path / ".dependencies/uv/0.11.16/bin/uv.exe"
    )


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
            '{"version":"0.11.16",'
            '"version":"0.11.17",'
            '"base_url":"https://github.com/astral-sh/uv/'
            'releases/download/0.11.16/",'
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
        ("basedpyright.exe", "basedpyright 1.39.9"),
        ("pytest.exe", "pytest 9.1.1"),
        ("python-jig.cmd", "Python 3.14.6"),
        ("ruff.exe", "ruff 0.16.0"),
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
        ("basedpyright", "basedpyright 1.39.9"),
        ("pytest", "pytest 9.1.1"),
        ("python-jig", "Python 3.14.6"),
        ("ruff", "ruff 0.16.0"),
    )


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


def test_rust_inspection_rejects_windows_channel_on_linux(
    tmp_path: Path,
) -> None:
    """A Windows GNU Rust channel never becomes Linux-ready by inference."""
    _ = _write_rust_manifest(tmp_path)

    status = project.inspect_rust(tmp_path, LINUX_PLATFORM)

    assert status.state is project.ComponentState.UNSUPPORTED
    assert WINDOWS_CHANNEL in status.detail


def test_local_directory_initialization_is_idempotent(tmp_path: Path) -> None:
    """Ignored checkout state directories can be initialized repeatedly."""
    first = project.initialize_local_directories(tmp_path)
    second = project.initialize_local_directories(tmp_path)

    assert first == second
    assert tuple(path.name for path in first) == project.LOCAL_DIRECTORIES
    assert all(path.is_dir() for path in first)


def test_repository_validation_fails_closed_for_wrong_root(
    tmp_path: Path,
) -> None:
    """Bootstrap refuses a directory without the repository authority files."""
    with pytest.raises(project.InitializationError, match="repository root"):
        project.validate_repository(tmp_path)
