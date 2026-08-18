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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Provision the repository-local Python validation environment.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Provision the repository-local Python validation environment."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path
from pathlib import PureWindowsPath
import platform
import stat

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed repository-local argv.
import sys
import tarfile
from typing import BinaryIO
from typing import Final
from typing import Never
from typing import cast
import urllib.error
import urllib.request
import venv
import zipfile

from scripts.repository_root import repository_root

ROOT: Final = repository_root(Path(__file__))
PYTHON_VERSION: Final = (3, 14, 6)
BOOTSTRAP_ROOT: Final = (
    ROOT / "src/automation/repository/composition/scripts/bootstrap"
)
REQUIREMENTS: Final = BOOTSTRAP_ROOT / "python-validation-requirements.txt"
UV_MANIFEST: Final = BOOTSTRAP_ROOT / "uv-toolchain.json"
WINDOWS_OS_NAME: Final = "nt"
WINDOWS: Final = os.name == WINDOWS_OS_NAME
SYSTEM_NAMES: Final = {
    "darwin": "macos",
    "linux": "linux",
    "windows": "windows",
}
MACHINE_NAMES: Final = {
    "aarch64": "aarch64",
    "amd64": "x86_64",
    "arm64": "aarch64",
    "x86_64": "x86_64",
}
SHA256_HEX_LENGTH: Final = 64
LOWER_HEX_DIGITS: Final = frozenset("0123456789abcdef")
PARENT_SEGMENT: Final = ".."
PATH_SEPARATORS: Final = frozenset(("/", "\\"))
UV_RELEASE_BASE: Final = (
    "https://github.com/astral-sh/uv/releases/download/"
)
UV_SCHEMA_VERSION: Final = 1
URL_SUFFIX_MARKERS: Final = frozenset(("?", "#"))
PYTEST_TOOL_ID: Final = "pytest"


@dataclass(frozen=True, slots=True)
class UvArtifact:
    """One pinned standalone uv release artifact."""

    asset: str
    base_url: str
    member: str
    platform_id: str
    sha256: str
    version: str


@dataclass(frozen=True, slots=True)
class ValidationEnvironmentLayout:
    """Paths for one platform-specific repository validation environment."""

    environment: Path
    expected_tools: tuple[tuple[str, str], ...]
    pytest: Path
    pytest_launcher: Path
    python: Path
    python_launcher: Path
    scripts: Path


class ProvisionError(RuntimeError):
    """Deterministic local Python provisioning failure."""


def uv_platform_id(
    *,
    system: str | None = None,
    machine: str | None = None,
) -> str:
    """Return the normalized platform key used by the uv manifest.

    Returns:
        Supported operating-system and architecture identity.

    """
    observed_system = (system or platform.system()).strip().lower()
    observed_machine = (machine or platform.machine()).strip().lower()
    operating_system = SYSTEM_NAMES.get(observed_system)
    architecture = MACHINE_NAMES.get(observed_machine)
    if operating_system is None or architecture is None:
        _fail("".join((
            "unsupported uv bootstrap platform: ",
            f"{observed_system}-{observed_machine}",
        )))
    return f"{operating_system}-{architecture}"


def _required_string(
    document: dict[str, object],
    key: str,
    label: str,
) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        _fail(f"{label}.{key} must be a nonempty string")
    return value


def _required_path_segment(
    document: dict[str, object],
    key: str,
    label: str,
) -> str:
    value = _required_string(document, key, label)
    windows_path = PureWindowsPath(value)
    reserved = value in {".", PARENT_SEGMENT}
    has_separator = any(separator in value for separator in PATH_SEPARATORS)
    windows_anchored = bool(windows_path.drive or windows_path.root)
    if reserved or has_separator or windows_anchored:
        _fail(f"{label}.{key} must be one repository-local path segment")
    return value


def _required_url_asset(
    document: dict[str, object],
    platform_id: str,
) -> str:
    value = _required_path_segment(document, "asset", platform_id)
    if any(marker in value for marker in URL_SUFFIX_MARKERS):
        _fail(f"{platform_id}.asset must be one URL path segment")
    return value


def _reject_duplicate_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            _fail(f"duplicate uv manifest JSON key: {key}")
        document[key] = value
    return document


def _uv_manifest_document(manifest_path: Path) -> dict[str, object]:
    try:
        parsed = cast(
            "object",
            json.loads(
                manifest_path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_pairs,
            ),
        )
    except (json.JSONDecodeError, OSError) as error:
        _fail(f"cannot read uv toolchain manifest: {error}")
    if not isinstance(parsed, dict):
        _fail("uv toolchain manifest must be an object")
    return cast("dict[str, object]", parsed)


def _uv_artifact_document(
    document: dict[str, object],
    platform_id: str,
) -> dict[str, object]:
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, dict):
        _fail("uv manifest.artifacts must be an object")
    artifact_value = cast("dict[str, object]", artifacts).get(platform_id)
    if not isinstance(artifact_value, dict):
        _fail(f"uv manifest has no artifact for {platform_id}")
    return cast("dict[str, object]", artifact_value)


def _validated_uv_sha256(
    artifact: dict[str, object],
    platform_id: str,
) -> str:
    value = artifact.get("sha256")
    if not isinstance(value, list) or not value:
        _fail(f"{platform_id}.sha256 must be a nonempty chunk list")
    raw_chunks = cast("list[object]", value)
    if not all(isinstance(chunk, str) and chunk for chunk in raw_chunks):
        _fail(f"{platform_id}.sha256 chunks must be nonempty strings")
    chunks = cast("list[str]", raw_chunks)
    sha256 = "".join(chunks)
    if len(sha256) != SHA256_HEX_LENGTH or any(
        character not in LOWER_HEX_DIGITS for character in sha256
    ):
        _fail(f"{platform_id}.sha256 must be lowercase SHA-256")
    return sha256


def uv_artifact(
    platform_id: str,
    manifest_path: Path = UV_MANIFEST,
) -> UvArtifact:
    """Load one pinned uv artifact from the tracked manifest.

    Returns:
        Verified platform artifact identity and archive metadata.

    """
    document = _uv_manifest_document(manifest_path)
    schema_version = document.get("schema_version")
    if type(schema_version) is not int or schema_version != UV_SCHEMA_VERSION:
        _fail("unsupported uv toolchain manifest schema")
    version = _required_path_segment(document, "version", "uv manifest")
    base_url = _required_string(document, "base_url", "uv manifest")
    expected_base_url = f"{UV_RELEASE_BASE}{version}/"
    if base_url != expected_base_url:
        _fail("uv manifest.base_url must match the pinned release version")
    artifact = _uv_artifact_document(document, platform_id)
    return UvArtifact(
        asset=_required_url_asset(artifact, platform_id),
        base_url=base_url,
        member=_required_string(artifact, "member", platform_id),
        platform_id=platform_id,
        sha256=_validated_uv_sha256(artifact, platform_id),
        version=version,
    )


def uv_executable(
    artifact: UvArtifact,
    root: Path = ROOT,
) -> Path:
    """Resolve the repository-local executable path for one uv artifact.

    Returns:
        Exact repository-local standalone executable path.

    """
    suffix = ".exe" if artifact.platform_id.startswith("windows-") else ""
    return (
        root
        / ".dependencies"
        / "uv"
        / artifact.version
        / "bin"
        / f"uv{suffix}"
    )


def verify_uv_archive(data: bytes, expected_sha256: str) -> None:
    """Reject uv archive bytes that do not match the tracked SHA-256."""
    observed = hashlib.sha256(data).hexdigest()
    if observed != expected_sha256:
        _fail("".join((
            f"uv archive SHA-256 mismatch: expected {expected_sha256}; ",
            f"got {observed}",
        )))


def _download_uv_archive(artifact: UvArtifact) -> bytes:
    url = f"{artifact.base_url}{artifact.asset}"
    # The manifest restricts this request to the official HTTPS release root.
    request = urllib.request.Request(  # ruff: ignore[suspicious-url-open-usage]
        url,
        headers={"User-Agent": "malbolge-bootstrap/1"},
    )
    try:
        response = cast(
            "BinaryIO",
            # The request URL was validated against the fixed release root.
            urllib.request.urlopen(  # ruff: ignore[suspicious-url-open-usage]
                request,
                timeout=120,
            ),
        )
        with response:
            data = response.read()
    except (OSError, urllib.error.URLError) as error:
        _fail(f"cannot download pinned uv artifact: {error}")
    verify_uv_archive(data, artifact.sha256)
    return data


def _zip_member_bytes(data: bytes, member: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return archive.read(member)


def _tar_member_bytes(data: bytes, member_name: str) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        member = archive.extractfile(member_name)
        if member is None:
            _fail(f"uv archive member is not a file: {member_name}")
        return member.read()


def _uv_member_bytes(data: bytes, artifact: UvArtifact) -> bytes:
    try:
        if artifact.asset.endswith(".zip"):
            return _zip_member_bytes(data, artifact.member)
        return _tar_member_bytes(data, artifact.member)
    except (KeyError, OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        _fail(f"cannot extract pinned uv artifact: {error}")


def _uv_version_matches(output: str, version: str) -> bool:
    expected = f"uv {version}"
    return output == expected or output.startswith(f"{expected} ")


def ensure_uv(
    root: Path = ROOT,
    *,
    platform_id: str | None = None,
) -> Path:
    """Provision and verify the pinned standalone uv executable.

    Returns:
        Verified repository-local uv executable.

    """
    selected = platform_id or uv_platform_id()
    artifact = uv_artifact(selected)
    executable = uv_executable(artifact, root)
    if executable.is_file():
        output = _run([str(executable), "--version"])
        if _uv_version_matches(output, artifact.version):
            return executable
        _fail(f"unexpected uv version at {executable}: {output!r}")
    data = _download_uv_archive(artifact)
    binary = _uv_member_bytes(data, artifact)
    executable.parent.mkdir(parents=True, exist_ok=True)
    temporary = executable.with_name(f"{executable.name}.tmp")
    _ = temporary.write_bytes(binary)
    if not selected.startswith("windows-"):
        _make_executable(temporary)
    _ = temporary.replace(executable)
    output = _run([str(executable), "--version"])
    if not _uv_version_matches(output, artifact.version):
        _fail(f"unexpected provisioned uv version: {output!r}")
    return executable


def validation_layout(
    root: Path = ROOT,
    *,
    windows: bool = WINDOWS,
) -> ValidationEnvironmentLayout:
    """Resolve repository-local validation paths for one host family.

    Returns:
        Exact environment, interpreter, launcher, and tool paths.

    """
    environment = root / ".dependencies" / "python" / "3.14.6"
    scripts = environment / ("Scripts" if windows else "bin")
    executable_suffix = ".exe" if windows else ""
    launcher_suffix = ".cmd" if windows else ""
    return ValidationEnvironmentLayout(
        environment=environment,
        expected_tools=(
            (f"basedpyright{executable_suffix}", "basedpyright 1.39.9"),
            (f"pytest{executable_suffix}", "pytest 9.1.1"),
            (f"python-jig{launcher_suffix}", "Python 3.14.6"),
            (f"ruff{executable_suffix}", "ruff 0.16.0"),
        ),
        pytest=scripts / f"pytest{executable_suffix}",
        pytest_launcher=scripts / f"pytest-jig{launcher_suffix}",
        python=scripts / ("python.exe" if windows else "python"),
        python_launcher=scripts / f"python-jig{launcher_suffix}",
        scripts=scripts,
    )


LAYOUT: Final = validation_layout()
ENVIRONMENT: Final = LAYOUT.environment
SCRIPTS: Final = LAYOUT.scripts
PYTHON: Final = LAYOUT.python
PYTEST: Final = LAYOUT.pytest
PYTEST_JIG: Final = LAYOUT.pytest_launcher
PYTHON_JIG: Final = LAYOUT.python_launcher
EXPECTED_TOOLS: Final = dict(LAYOUT.expected_tools)


def _fail(message: str) -> Never:
    raise ProvisionError(message)


def _check_host_python() -> None:
    observed = sys.version_info[:3]
    if observed != PYTHON_VERSION:
        expected_text = ".".join(str(part) for part in PYTHON_VERSION)
        observed_text = ".".join(str(part) for part in observed)
        _fail(f"bootstrap requires Python {expected_text}; got {observed_text}")


def _run(command: list[str]) -> str:
    # jig-ignore-next-line: indivisible reviewed identifier
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed repository-local argv.
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        shell=False,
        text=True,
    )
    return completed.stdout.strip()


def _windows_cache_line() -> str:
    return r'set "PYTHONPYCACHEPREFIX=%~dp0..\..\..\..\.cache\python\pycache"'


def _windows_launcher_text(*, pytest: bool) -> str:
    cache_line = _windows_cache_line()
    invocation = (
        '"%~dp0python.exe" -m pytest %*' if pytest else '"%~dp0python.exe" %*'
    )
    return f"@echo off\r\n{cache_line}\r\n{invocation}\r\n"


def _posix_script_directory_text() -> str:
    return (
        'case "$0" in\n'
        '    */*) SCRIPT_DIR=${0%/*} ;;\n'
        '    *) SCRIPT_DIR=. ;;\n'
        'esac\n'
        'SCRIPT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR" && pwd)\n'
    )


def _posix_launcher_text(*, pytest: bool) -> str:
    invocation = (
        'exec "$SCRIPT_DIR/python" -m pytest "$@"'
        if pytest
        else 'exec "$SCRIPT_DIR/python" "$@"'
    )
    cache = (
        'export PYTHONPYCACHEPREFIX="'
        '$SCRIPT_DIR/../../../../.cache/python/pycache"'
    )
    return (
        "#!/bin/sh\n"
        "set -eu\n"
        f"{_posix_script_directory_text()}"
        f"{cache}\n"
        f"{invocation}\n"
    )


def _posix_jig_pytest_alias_text() -> str:
    cache = (
        'export PYTHONPYCACHEPREFIX="'
        '$SCRIPT_DIR/../../../../.cache/python/pycache"'
    )
    return (
        "#!/bin/sh\n"
        "set -eu\n"
        f"{_posix_script_directory_text()}"
        f"{cache}\n"
        'exec "$SCRIPT_DIR/../bin/python" -m pytest "$@"\n'
    )


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    _ = path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_launchers(
    layout: ValidationEnvironmentLayout = LAYOUT,
    *,
    windows: bool = WINDOWS,
) -> None:
    """Write platform-native Python and pytest launchers."""
    if windows:
        _ = layout.python_launcher.write_text(
            _windows_launcher_text(pytest=False),
            encoding="ascii",
            newline="",
        )
        _ = layout.pytest_launcher.write_text(
            _windows_launcher_text(pytest=True),
            encoding="ascii",
            newline="",
        )
        return
    _ = layout.python_launcher.write_text(
        _posix_launcher_text(pytest=False),
        encoding="ascii",
        newline="\n",
    )
    _ = layout.pytest_launcher.write_text(
        _posix_launcher_text(pytest=True),
        encoding="ascii",
        newline="\n",
    )
    _make_executable(layout.python_launcher)
    _make_executable(layout.pytest_launcher)


def write_jig_tool_aliases(
    layout: ValidationEnvironmentLayout = LAYOUT,
    *,
    windows: bool = WINDOWS,
) -> tuple[tuple[str, Path], ...]:
    """Copy native validation tools to platform-neutral Jig executable paths.

    Returns:
        Stable tool-ID and repository-local alias pairs.

    """
    alias_root = layout.environment / "jig-bin"
    alias_root.mkdir(parents=True, exist_ok=True)
    executable_suffix = ".exe" if windows else ""
    aliases: list[tuple[str, Path]] = []
    for tool_id in ("basedpyright", "pytest", "ruff"):
        source = layout.scripts / f"{tool_id}{executable_suffix}"
        if not source.is_file():
            _fail(f"missing provisioned tool for Jig alias: {source}")
        target = alias_root / f"{tool_id}.bin"
        if tool_id == PYTEST_TOOL_ID and not windows:
            _ = target.write_text(
                _posix_jig_pytest_alias_text(),
                encoding="ascii",
                newline="\n",
            )
        else:
            _ = target.write_bytes(source.read_bytes())
        if not windows:
            _make_executable(target)
        aliases.append((tool_id, target))
    return tuple(aliases)


def _provision(layout: ValidationEnvironmentLayout) -> None:
    uv = ensure_uv()
    if not layout.python.is_file():
        builder = venv.EnvBuilder(with_pip=False, clear=False)
        builder.create(layout.environment)
    _ = _run([
        str(uv),
        "pip",
        "sync",
        "--no-config",
        "--no-progress",
        "--python",
        str(layout.python),
        str(REQUIREMENTS),
    ])
    _ = _run([
        str(uv),
        "pip",
        "uninstall",
        "--no-config",
        "--python",
        str(layout.python),
        "pip",
    ])
    write_launchers(layout, windows=WINDOWS)
    _ = write_jig_tool_aliases(layout, windows=WINDOWS)


def _verify_tool(
    layout: ValidationEnvironmentLayout,
    executable: str,
    expected: str,
) -> None:
    path = layout.scripts / executable
    if not path.is_file():
        _fail(f"missing provisioned tool: {path}")
    output = _run([str(path), "--version"])
    first_line = output.partition("\n")[0]
    if expected not in first_line:
        _fail(f"unexpected {executable} version: {first_line!r}")


def _verify(layout: ValidationEnvironmentLayout) -> None:
    for executable, expected in layout.expected_tools:
        _verify_tool(layout, executable, expected)


def initialize() -> ValidationEnvironmentLayout:
    """Provision and verify the exact repository-local Python tool set.

    Returns:
        Platform-native environment layout after successful verification.

    """
    _check_host_python()
    _provision(LAYOUT)
    _verify(LAYOUT)
    return LAYOUT


def main() -> int:
    """Provision and verify the exact repository-local Python tool set.

    Returns:
        Zero after successful provisioning, otherwise one.

    """
    try:
        layout = initialize()
    except (OSError, ProvisionError, subprocess.SubprocessError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    _ = sys.stdout.write(
        f"python validation environment ready: {layout.environment}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
