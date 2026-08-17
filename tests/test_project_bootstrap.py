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
RUST_CHANNEL = "1.97.1"
RUST_NIGHTLY_CHANNEL = "nightly-2026-07-14"
RUST_CARGO_BYTES = b"cargo-1.97.1"
RUST_RUSTC_BYTES = b"rustc-1.97.1"
RUST_STD_BYTES = b"rust-std"
GIT_VERSION = "2.55.0"
GIT_BYTES = b"git-2.55.0"
GIT_HELPER_BYTES = b"git-helper"
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


def test_jig_tool_aliases_copy_native_validation_tools(tmp_path: Path) -> None:
    """Jig receives platform-neutral executable aliases with identical bytes."""
    layout = python_validation.validation_layout(tmp_path, windows=False)
    layout.scripts.mkdir(parents=True)
    native = {
        "basedpyright": b"basedpyright-linux",
        "pytest": b"pytest-linux",
        "ruff": b"ruff-linux",
    }
    for name, payload in native.items():
        path = layout.scripts / name
        _ = path.write_bytes(payload)
        _ = path.chmod(path.stat().st_mode | stat.S_IXUSR)

    aliases = python_validation.write_jig_tool_aliases(
        layout,
        windows=False,
    )

    assert tuple(path.name for _, path in aliases) == (
        "basedpyright.bin",
        "pytest.bin",
        "ruff.bin",
    )
    alias_root = layout.environment / "jig-bin"
    assert all(path.parent == alias_root for _, path in aliases)
    assert {name: path.read_bytes() for name, path in aliases} == {
        name: native[name] for name in native
    }
    assert all(path.stat().st_mode & stat.S_IXUSR for _, path in aliases)


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
    stable = tmp_path / ".dependencies/rust/1.97.1"
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


def test_rust_linker_adapters_leave_windows_aliases_unchanged(
    tmp_path: Path,
) -> None:
    """Linux linker adaptation never rewrites Windows Rust aliases."""
    root = tmp_path / ".dependencies/rust/1.97.1"
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
    _ = (source_bin / "rustc").write_bytes(RUST_RUSTC_BYTES)
    _ = (source_lib / "manifest").write_bytes(RUST_STD_BYTES)
    destination = tmp_path / ".dependencies" / "rust" / RUST_CHANNEL

    aliases = project.import_rust_toolchain(
        source,
        destination,
        tool_ids=("cargo",),
        windows=False,
    )

    alias = destination / "bin" / "cargo.bin"
    assert aliases == (alias,)
    assert alias.read_bytes() == RUST_CARGO_BYTES
    assert alias.stat().st_mode & stat.S_IXUSR
    assert (destination / "bin" / "rustc").read_bytes() == RUST_RUSTC_BYTES
    assert (destination / "lib/rustlib/manifest").read_bytes() == RUST_STD_BYTES
    assert project.rust_toolchain_import_complete(destination)


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
        return ("1.97.1-x86_64-unknown-linux-gnu",)

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


def test_rustup_installed_channel_match_accepts_native_host_suffix() -> None:
    """Pinned channels match installed host-qualified Rustup identities."""
    installed = (
        "1.97.1-x86_64-unknown-linux-gnu",
        "nightly-2026-07-14-x86_64-unknown-linux-gnu",
    )

    assert project.rustup_channel_is_installed(RUST_CHANNEL, installed)
    assert project.rustup_channel_is_installed(RUST_NIGHTLY_CHANNEL, installed)
    assert not project.rustup_channel_is_installed("1.97.0", installed)
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
    assert (nightly_root / "bin/cargo-clippy.bin").is_file()
    assert (nightly_root / "bin/cargo-fmt.bin").is_file()
    assert project.rust_toolchain_import_complete(stable_root)
    assert project.rust_toolchain_import_complete(nightly_root)


def test_rust_inspection_requires_completed_neutral_alias(
    tmp_path: Path,
) -> None:
    """Completed imported Cargo is host-neutral readiness evidence."""
    _ = _write_rust_manifest(tmp_path)
    toolchain = tmp_path / ".dependencies" / "rust" / RUST_CHANNEL
    cargo = toolchain / "bin" / "cargo.bin"
    cargo.parent.mkdir(parents=True)
    cargo.touch()
    _ = (toolchain / project.RUST_IMPORT_MARKER).write_text(
        "malbolge-rust-toolchain-import/v1\n",
        encoding="ascii",
    )

    linux_before_linker = project.inspect_rust(tmp_path, LINUX_PLATFORM)
    windows = project.inspect_rust(tmp_path, WINDOWS_PLATFORM)
    linker = toolchain / "bin" / "cc"
    linker.touch()
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


def test_host_git_import_requires_matching_version_and_exec_path(
    tmp_path: Path,
) -> None:
    """Host Git becomes repository authority only with matching runtime data."""
    jig_config = tmp_path / ".jig/jig.toml"
    jig_config.parent.mkdir(parents=True)
    _ = jig_config.write_text(
        '[tool.git]\nversion = "2.55.0"\n',
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
