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

from contextlib import suppress
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
import tempfile
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
PYTHON_VERSION: Final = (3, 14, 7)
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
UV_RELEASE_BASE: Final = "https://github.com/astral-sh/uv/releases/download/"
UV_SCHEMA_VERSION: Final = 1
MAX_UV_MANIFEST_BYTES: Final = 1_048_576
MAX_JIG_TOOL_BINARY_BYTES: Final = 256 * 1024 * 1024
UV_BINARY_MODE: Final = 0o755
JIG_BINARY_MODE: Final = 0o755
URL_SUFFIX_MARKERS: Final = frozenset(("?", "#"))
BASEDPYRIGHT_TOOL_ID: Final = "basedpyright"
PYTEST_TOOL_ID: Final = "pytest"
JIG_FAST_VERSION_TOOL_IDS: Final = frozenset((
    BASEDPYRIGHT_TOOL_ID,
    PYTEST_TOOL_ID,
))
SHELL_UNSAFE_VERSION_CHARACTERS: Final = frozenset(("'", "\n", "\r"))


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
        _fail(
            "".join((
                "unsupported uv bootstrap platform: ",
                f"{observed_system}-{observed_machine}",
            ))
        )
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


def _uv_manifest_redirect(path: Path, *, label: str) -> bool:
    """Require native link-status observations for a manifest path component."""
    symlink = path.is_symlink()
    junction = path.is_junction()
    if type(symlink) is not bool or type(junction) is not bool:
        _fail(f"uv toolchain manifest {label} redirect status must be native")
    return symlink or junction


def _reject_uv_parent_redirects(path: Path) -> None:
    for parent in path.parents:
        redirected = _uv_manifest_redirect(parent, label="parent")
        status = parent.lstat()
        if (
            type(status) is not os.stat_result
            or type(status.st_mode) is not int
        ):
            _fail("uv toolchain manifest parent requires native file status")
        if redirected or not stat.S_ISDIR(status.st_mode):
            _fail("uv toolchain manifest parent path must not redirect")


def _uv_manifest_identity(status: os.stat_result) -> tuple[int, ...]:
    """Admit only a bounded physical uv manifest.

    Returns:
        File device/inode, length, and modification metadata.

    """
    if type(status) is not os.stat_result or any(
        type(field) is not int
        for field in (
            status.st_mode,
            status.st_dev,
            status.st_ino,
            status.st_size,
            status.st_mtime_ns,
            status.st_ctime_ns,
        )
    ):
        _fail("uv toolchain manifest requires native file status")
    if not stat.S_ISREG(status.st_mode):
        _fail("uv toolchain manifest must be a regular file")
    if status.st_size < 0 or status.st_size > MAX_UV_MANIFEST_BYTES:
        _fail("uv toolchain manifest exceeds byte limit")
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _read_uv_manifest_bytes(path: Path) -> bytes:
    """Read bounded uv manifest bytes from the admitted, stable file.

    Returns:
        Exact verified physical manifest contents.

    """
    _reject_uv_parent_redirects(path)
    admitted = path.lstat()
    expected = _uv_manifest_identity(admitted)
    if _uv_manifest_redirect(path, label="leaf"):
        _fail("uv toolchain manifest path must not redirect")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = os.open(path, flags)
    with _open_owned_binary_stream(descriptor) as stream:
        if _uv_manifest_identity(os.fstat(stream.fileno())) != expected:
            _fail("uv toolchain manifest changed before read")
        content = stream.read(MAX_UV_MANIFEST_BYTES + 1)
        if (
            len(content) != admitted.st_size
            or _uv_manifest_identity(os.fstat(stream.fileno())) != expected
            or _uv_manifest_identity(path.lstat()) != expected
        ):
            _fail("uv toolchain manifest changed during read")
    _reject_uv_parent_redirects(path)
    return content


def _uv_manifest_document(manifest_path: Path) -> dict[str, object]:
    try:
        parsed = cast(
            "object",
            json.loads(
                _read_uv_manifest_bytes(manifest_path).decode("utf-8"),
                object_pairs_hook=_reject_duplicate_pairs,
            ),
        )
    except ProvisionError:
        raise
    except (
        json.JSONDecodeError,
        OSError,
        ValueError,
        UnicodeDecodeError,
        RecursionError,
        TypeError,
        RuntimeError,
    ) as error:
        message = f"cannot read uv toolchain manifest: {type(error).__name__}"
        raise ProvisionError(message) from error
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
        root / ".dependencies" / "uv" / artifact.version / "bin" / f"uv{suffix}"
    )


def verify_uv_archive(data: bytes, expected_sha256: str) -> None:
    """Require native uv archive bytes with the exact tracked SHA-256."""
    if type(data) is not bytes:
        _fail("uv archive must contain native bytes")
    observed = hashlib.sha256(data).hexdigest()
    if observed != expected_sha256:
        _fail(
            "".join((
                f"uv archive SHA-256 mismatch: expected {expected_sha256}; ",
                f"got {observed}",
            ))
        )


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
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = f"cannot download pinned uv artifact: {type(error).__name__}"
        raise ProvisionError(message) from error
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


def _admit_uv_directory(
    path: Path,
    *,
    required: bool = False,
) -> os.stat_result | None:
    """Reject nonphysical directories in a uv provisioning path.

    Returns:
        Physical directory metadata, or None for an optional missing path.

    """
    if path.is_symlink() or path.is_junction():
        _fail(f"uv provision path must not redirect: {path}")
    try:
        status = path.lstat()
    except FileNotFoundError:
        if required:
            _fail(f"uv provision path disappeared: {path}")
        return None
    if not stat.S_ISDIR(status.st_mode):
        _fail(f"uv provision parent must be a directory: {path}")
    return status


def _uv_leaf_status(
    path: Path,
    *,
    required: bool,
) -> os.stat_result | None:
    """Read one physical uv leaf without following redirected names.

    Returns:
        Physical leaf status, or None when an optional leaf is missing.

    """
    if path.is_symlink() or path.is_junction():
        _fail(f"uv provision path must not redirect: {path}")
    try:
        return path.lstat()
    except FileNotFoundError:
        if required:
            _fail(f"uv provision path disappeared: {path}")
        return None


def _admit_uv_regular_file(
    path: Path,
    *,
    required: bool,
) -> os.stat_result | None:
    """Require a single-link physical regular uv executable or stage.

    Returns:
        Physical regular file status, or None for an optional missing file.

    """
    status = _uv_leaf_status(path, required=required)
    if status is None:
        return None
    if not stat.S_ISREG(status.st_mode):
        _fail(f"uv provision file must be physical and regular: {path}")
    if status.st_nlink != 1:
        _fail(f"uv provision file must not have multiple links: {path}")
    return status


def _admit_uv_provision_path(
    path: Path,
    *,
    directory: bool = False,
    required: bool = False,
) -> os.stat_result | None:
    """Admit physical provisioning ancestry and a single-link target leaf.

    Returns:
        The leaf status, or None when an optional leaf is absent.

    """
    for parent in reversed(path.parents):
        _ = _admit_uv_directory(parent)
    if directory:
        return _admit_uv_directory(path, required=required)
    return _admit_uv_regular_file(path, required=required)


def _uv_stage_is_owned(
    temporary: Path,
    identity: tuple[int, int],
    *,
    expected_size: int | None = None,
) -> bool:
    """Verify a stage still names its original single-link regular inode.

    Returns:
        Whether the stage still has the required private identity and size.

    """
    try:
        status = temporary.lstat()
    except OSError, ValueError, TypeError, RuntimeError:
        return False
    return (
        stat.S_ISREG(status.st_mode)
        and status.st_nlink == 1
        and (status.st_dev, status.st_ino) == identity
        and (expected_size is None or status.st_size == expected_size)
    )


def _create_uv_stage(temporary: Path) -> tuple[int, tuple[int, int]]:
    """Create a private uv staging descriptor using exclusive file creation.

    Returns:
        Open descriptor and device/inode identity of the created stage.

    Raises:
        ProvisionError: The staging path cannot be exclusively admitted.

    """
    if _admit_uv_provision_path(temporary) is not None:
        _fail(f"uv staging path already exists: {temporary}")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        descriptor = os.open(temporary, flags, 0o600)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = "uv staging descriptor creation failed"
        raise ProvisionError(message) from error
    try:
        status = os.fstat(descriptor)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        with suppress(OSError):
            os.close(descriptor)
        message = "uv staging descriptor inspection failed"
        raise ProvisionError(message) from error
    return descriptor, (status.st_dev, status.st_ino)


def _write_uv_stage_descriptor(
    temporary: Path,
    stage: tuple[int, tuple[int, int]],
    binary: bytes,
    *,
    windows: bool,
) -> None:
    """Write and mark only the original uv staging descriptor executable."""
    descriptor, identity = stage
    if not _uv_stage_is_owned(temporary, identity, expected_size=0):
        _fail("uv staging descriptor does not match a private file")
    written = os.write(descriptor, binary)
    if type(written) is not int or written != len(binary):
        _fail("uv staging short or invalid byte count")
    if not windows:
        os.fchmod(descriptor, UV_BINARY_MODE)
    if not _uv_stage_is_owned(temporary, identity, expected_size=len(binary)):
        _fail("uv staging changed during descriptor write")


def _write_verified_uv_binary(
    temporary: Path,
    binary: bytes,
    *,
    windows: bool = WINDOWS,
) -> tuple[int, int]:
    """Write pinned uv bytes through one exclusively created owned descriptor.

    Returns:
        Device and inode identity for the private stage before publication.

    Raises:
        ProvisionError: A stage write or physical identity cannot be admitted.

    """
    descriptor, identity = _create_uv_stage(temporary)
    complete = False
    try:
        _write_uv_stage_descriptor(
            temporary, (descriptor, identity), binary, windows=windows
        )
    except ProvisionError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = "uv staging descriptor write failed"
        raise ProvisionError(message) from error
    else:
        complete = True
        return identity
    finally:
        with suppress(OSError):
            os.close(descriptor)
        if not complete and _uv_stage_is_owned(temporary, identity):
            with suppress(OSError):
                temporary.unlink()


def _require_uv_destination_absent(executable: Path) -> None:
    """Reject a destination created by another process during provisioning."""
    if _admit_uv_provision_path(executable) is not None:
        _fail(f"uv executable appeared during provisioning: {executable}")


def _publish_uv_stage(
    temporary: Path,
    executable: Path,
    identity: tuple[int, int],
    *,
    expected_size: int,
) -> None:
    """Publish only a private stage into an admitted physical destination."""
    _ = _admit_uv_provision_path(
        executable.parent, directory=True, required=True
    )
    _require_uv_destination_absent(executable)
    if not _uv_stage_is_owned(temporary, identity, expected_size=expected_size):
        _fail("uv staging changed before publication")
    _ = temporary.replace(executable)


def _provision_uv_binary(
    executable: Path,
    binary: bytes,
    *,
    windows: bool,
) -> None:
    """Provision one new uv executable without following staging aliases."""
    _ = _admit_uv_provision_path(executable.parent, directory=True)
    executable.parent.mkdir(parents=True, exist_ok=True)
    _ = _admit_uv_provision_path(
        executable.parent, directory=True, required=True
    )
    _require_uv_destination_absent(executable)
    temporary = executable.with_name(f"{executable.name}.tmp")
    identity = _write_verified_uv_binary(temporary, binary, windows=windows)
    try:
        _publish_uv_stage(
            temporary, executable, identity, expected_size=len(binary)
        )
    finally:
        if _uv_stage_is_owned(temporary, identity):
            temporary.unlink(missing_ok=True)


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
    if _admit_uv_provision_path(executable) is not None:
        output = _run([str(executable), "--version"])
        _ = _admit_uv_provision_path(executable, required=True)
        if _uv_version_matches(output, artifact.version):
            return executable
        _fail(f"unexpected uv version at {executable}: {output!r}")
    data = _download_uv_archive(artifact)
    binary = _uv_member_bytes(data, artifact)
    _provision_uv_binary(
        executable, binary, windows=selected.startswith("windows-")
    )
    _ = _admit_uv_provision_path(executable, required=True)
    output = _run([str(executable), "--version"])
    _ = _admit_uv_provision_path(executable, required=True)
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
    environment = root / ".dependencies" / "python" / "3.14.7"
    scripts = environment / ("Scripts" if windows else "bin")
    executable_suffix = ".exe" if windows else ""
    launcher_suffix = ".cmd" if windows else ""
    return ValidationEnvironmentLayout(
        environment=environment,
        expected_tools=(
            (f"basedpyright{executable_suffix}", "basedpyright 1.40.1"),
            (f"pytest{executable_suffix}", "pytest 9.1.1"),
            (f"python-jig{launcher_suffix}", "Python 3.14.7"),
            (f"ruff{executable_suffix}", "ruff 0.16.9"),
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
    """Return exact native output from one authenticated bootstrap command."""
    try:
        # jig-ignore-next-line: indivisible reviewed identifier
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed repository-local argv.
            command.copy(),
            cwd=ROOT,
            check=True,
            capture_output=True,
            shell=False,
            text=True,
        )
    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        subprocess.SubprocessError,
    ) as error:
        native_types = {
            OSError,
            FileNotFoundError,
            PermissionError,
            ValueError,
            TypeError,
            RuntimeError,
        }
        detail = str(error) if type(error) in native_types else type(error).__name__
        if (
            type(error) is subprocess.CalledProcessError
            and type(error.returncode) is int
        ):
            detail = f"exit status {error.returncode}"
        raise ProvisionError(f"Python bootstrap command failed: {detail}") from error
    if (
        type(completed) is not subprocess.CompletedProcess
        or type(completed.args) is not list
        or len(completed.args) != len(command)
        or any(type(argument) is not str for argument in completed.args)
        or completed.args != command
        or type(completed.returncode) is not int
        or completed.returncode != 0
        or type(completed.stdout) is not str
        or type(completed.stderr) is not str
    ):
        _fail("invalid Python bootstrap process receipt")
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
        "    */*) SCRIPT_DIR=${0%/*} ;;\n"
        "    *) SCRIPT_DIR=. ;;\n"
        "esac\n"
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


def _posix_jig_tool_alias_text(
    tool_id: str,
    version_line: str,
) -> str:
    if any(
        character in version_line
        for character in SHELL_UNSAFE_VERSION_CHARACTERS
    ):
        _fail("Jig tool version line is not shell-literal safe")
    if tool_id == PYTEST_TOOL_ID:
        cache = (
            'export PYTHONPYCACHEPREFIX="'
            '$SCRIPT_DIR/../../../../.cache/python/pycache"\n'
        )
        invocation = 'exec "$SCRIPT_DIR/../bin/python" -m pytest "$@"'
    elif tool_id == BASEDPYRIGHT_TOOL_ID:
        cache = ""
        invocation = 'exec "$SCRIPT_DIR/../bin/basedpyright" "$@"'
    else:
        _fail(f"unsupported POSIX Jig tool alias: {tool_id}")
    return (
        "#!/bin/sh\n"
        "set -eu\n"
        'if [ "$#" -eq 1 ] && [ "$1" = "--version" ]; then\n'
        f"    printf '%s\\n' '{version_line}'\n"
        "    exit 0\n"
        "fi\n"
        f"{_posix_script_directory_text()}"
        f"{cache}"
        f"{invocation}\n"
    )


def write_launchers(
    layout: ValidationEnvironmentLayout = LAYOUT,
    *,
    windows: bool = WINDOWS,
) -> None:
    """Publish physical Python and pytest launchers without following links."""
    scripts = layout.scripts
    _check_jig_alias_path(scripts, directory=True, required=True)
    launchers = (layout.python_launcher, layout.pytest_launcher)
    for target in launchers:
        _check_jig_alias_path(target, directory=False, required=False)
    texts = (
        _windows_launcher_text(pytest=False)
        if windows
        else _posix_launcher_text(pytest=False),
        _windows_launcher_text(pytest=True)
        if windows
        else _posix_launcher_text(pytest=True),
    )
    for target, source in zip(launchers, texts, strict=True):
        _publish_jig_tool_alias(target, source.encode("ascii"), windows=windows)


def _expected_jig_tool_version_line(
    layout: ValidationEnvironmentLayout,
    executable: str,
) -> str:
    matches = [
        version_line
        for candidate, version_line in layout.expected_tools
        if candidate == executable
    ]
    if len(matches) != 1:
        _fail(f"Jig tool alias requires one version authority: {executable}")
    return matches[0]


def _check_jig_alias_parents(path: Path) -> None:
    """Reject a redirected ancestor before reading or publishing aliases."""
    for parent in reversed(path.parents):
        if parent.is_symlink() or parent.is_junction():
            _fail(f"Jig alias path must not redirect: {parent}")


def _check_jig_alias_path(
    path: Path,
    *,
    directory: bool,
    required: bool,
) -> None:
    """Reject redirects and nonphysical artifacts along a Jig tool path."""
    _check_jig_alias_parents(path)
    if path.is_symlink() or path.is_junction():
        _fail(f"Jig alias path must not redirect: {path}")
    try:
        observed = path.lstat()
    except FileNotFoundError:
        if required:
            _fail(f"missing provisioned tool for Jig alias: {path}")
        return
    expected_type = stat.S_ISDIR if directory else stat.S_ISREG
    if not expected_type(observed.st_mode):
        _fail(f"Jig alias path must be a physical regular artifact: {path}")


def _jig_source_identity(source: Path) -> tuple[int, int, int, int, int]:
    """Require one bounded physical source and return its stable identity.

    Returns:
        Device, inode, size and modification/change times.

    """
    _check_jig_alias_path(source, directory=False, required=True)
    status = source.lstat()
    if status.st_size > MAX_JIG_TOOL_BINARY_BYTES:
        _fail(f"Jig alias source exceeds byte limit: {source}")
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _jig_file_identity(
    status: os.stat_result,
) -> tuple[int, int, int, int, int]:
    """Return descriptor identity for a source already checked as regular.

    Returns:
        Device, inode, size and mutation timestamps.

    """
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _open_owned_binary_stream(descriptor: int, *, mode: str = "rb") -> BinaryIO:
    """Transfer an owned descriptor to a stream without leaking on failure.

    Returns:
        A binary stream owning the admitted native descriptor.

    Raises:
        OSError: The host rejects stream creation.
        ValueError: The host rejects descriptor arguments.
        TypeError: The host stream adapter rejects an argument type.
        RuntimeError: The host stream adapter cannot create a stream.

    """
    try:
        return cast("BinaryIO", os.fdopen(descriptor, mode))
    except OSError, ValueError, TypeError, RuntimeError:
        with suppress(OSError):
            os.close(descriptor)
        raise


def _read_open_jig_binary(
    source: Path,
    expected: tuple[int, int, int, int, int],
) -> bytes:
    """Read a bounded source descriptor while requiring stable metadata.

    Returns:
        Exact physical tool binary bytes.

    """
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = os.open(source, flags)
    with _open_owned_binary_stream(descriptor) as stream:
        observed = os.fstat(stream.fileno())
        if not stat.S_ISREG(observed.st_mode):
            _fail("Jig alias source must be a regular file")
        if _jig_file_identity(observed) != expected:
            _fail("Jig alias source changed before read")
        data = stream.read(MAX_JIG_TOOL_BINARY_BYTES + 1)
        if (
            len(data) != expected[2]
            or _jig_file_identity(os.fstat(stream.fileno())) != expected
        ):
            _fail("Jig alias source changed during read")
    return data


def _read_jig_binary_source(source: Path) -> bytes:
    """Copy only exact bounded native executable bytes.

    Returns:
        Stable physical source snapshot, excluding replacement and mutation.

    Raises:
        ProvisionError: Tool bytes, host I/O or source identity are invalid.

    """
    expected = _jig_source_identity(source)
    try:
        data = _read_open_jig_binary(source, expected)
    except ProvisionError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = (
            f"Jig alias source read failed: {source}: {type(error).__name__}"
        )
        raise ProvisionError(message) from error
    if _jig_source_identity(source) != expected:
        _fail("Jig alias source changed during read")
    return data


def _admit_jig_alias_temporary(
    descriptor: int,
    temporary_name: object,
    *,
    alias_root: Path,
    prefix: str,
) -> tuple[Path, tuple[int, int]]:
    """Bind one mkstemp pathname to its descriptor and requested directory.

    Returns:
        The admitted native staging name and descriptor inode identity.

    Raises:
        ProvisionError: The receipt is nonnative, foreign, or unverifiable.

    """
    if type(temporary_name) is not str:
        _fail("Jig alias temporary receipt must be a native pathname")
    temporary = Path(temporary_name)
    name = temporary.name
    valid_name = name.startswith(prefix) and name != prefix
    valid_location = temporary == alias_root.resolve() / name
    if not all((valid_name, valid_location, temporary_name == str(temporary))):
        _fail("Jig alias temporary receipt is outside the requested directory")
    try:
        descriptor_status = os.fstat(descriptor)
        pathname_status = temporary.lstat()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = "Jig alias temporary receipt cannot be verified"
        raise ProvisionError(message) from error
    regular = stat.S_ISREG(descriptor_status.st_mode) and stat.S_ISREG(
        pathname_status.st_mode
    )
    same_inode = (descriptor_status.st_dev, descriptor_status.st_ino) == (
        pathname_status.st_dev,
        pathname_status.st_ino,
    )
    single_link = descriptor_status.st_nlink == pathname_status.st_nlink == 1
    if not all((regular, same_inode, single_link)):
        _fail("Jig alias temporary receipt does not match its descriptor")
    return temporary, (descriptor_status.st_dev, descriptor_status.st_ino)


def _jig_alias_stage_is_owned(
    temporary: Path,
    identity: tuple[int, int],
    *,
    expected_size: int | None = None,
) -> bool:
    """Check one still-private stage without following linked names.

    Returns:
        Whether the path still names the original single-link inode.

    """
    try:
        status = temporary.lstat()
    except OSError, ValueError, TypeError, RuntimeError:
        return False
    valid = (
        stat.S_ISREG(status.st_mode)
        and status.st_nlink == 1
        and (status.st_dev, status.st_ino) == identity
    )
    return valid and (expected_size is None or status.st_size == expected_size)


def _open_jig_alias_write_stream(descriptor: int) -> BinaryIO:
    """Transfer a private alias descriptor to a typed writable stream.

    Returns:
        A writable stream owning the unique stage descriptor.

    Raises:
        ProvisionError: Host stream wrapping failed after descriptor creation.

    """
    try:
        return _open_owned_binary_stream(descriptor, mode="wb")
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = f"Jig alias temporary stream failed: {type(error).__name__}"
        raise ProvisionError(message) from error


def _publish_owned_jig_alias_stage(
    stage_receipt: tuple[Path, int, tuple[int, int]],
    target: Path,
    *,
    payload: bytes,
    windows: bool,
) -> None:
    """Write and promote only the descriptor-bound private staging inode."""
    temporary, descriptor, identity = stage_receipt
    with _open_jig_alias_write_stream(descriptor) as stream:
        written = stream.write(payload)
        if type(written) is not int or written != len(payload):
            _fail("Jig alias temporary write count mismatch")
        if not windows:
            os.fchmod(stream.fileno(), JIG_BINARY_MODE)
    _check_jig_alias_path(target.parent, directory=True, required=True)
    _check_jig_alias_path(target, directory=False, required=False)
    if not _jig_alias_stage_is_owned(
        temporary, identity, expected_size=len(payload)
    ):
        _fail("Jig alias temporary changed before publication")
    _ = temporary.replace(target)


def _publish_jig_tool_alias(
    target: Path,
    payload: bytes,
    *,
    windows: bool,
) -> None:
    """Atomically replace an admitted alias instead of following its leaf."""
    alias_root = target.parent
    _check_jig_alias_path(alias_root, directory=True, required=True)
    _check_jig_alias_path(target, directory=False, required=False)
    prefix = f".{target.name}."
    descriptor, temporary_name = tempfile.mkstemp(prefix=prefix, dir=alias_root)
    try:
        temporary, identity = _admit_jig_alias_temporary(
            descriptor,
            temporary_name,
            alias_root=alias_root,
            prefix=prefix,
        )
    except Exception:
        with suppress(OSError):
            os.close(descriptor)
        raise
    try:
        _publish_owned_jig_alias_stage(
            (temporary, descriptor, identity),
            target,
            payload=payload,
            windows=windows,
        )
    finally:
        if _jig_alias_stage_is_owned(temporary, identity):
            temporary.unlink(missing_ok=True)


def _jig_alias_source_and_target(
    layout: ValidationEnvironmentLayout,
    tool_id: str,
    *,
    windows: bool,
) -> tuple[Path, Path]:
    """Map one selected native tool to its neutral Jig alias.

    Returns:
        Native executable and repository-local neutral alias paths.

    """
    suffix = ".exe" if windows else ""
    return (
        layout.scripts / f"{tool_id}{suffix}",
        layout.environment / "jig-bin" / f"{tool_id}.bin",
    )


def _write_jig_tool_alias(
    layout: ValidationEnvironmentLayout,
    tool_id: str,
    *,
    windows: bool,
) -> Path:
    source, target = _jig_alias_source_and_target(
        layout, tool_id, windows=windows
    )
    if windows or tool_id not in JIG_FAST_VERSION_TOOL_IDS:
        payload = _read_jig_binary_source(source)
    else:
        version_line = _expected_jig_tool_version_line(layout, tool_id)
        _ = _jig_source_identity(source)
        payload = _posix_jig_tool_alias_text(tool_id, version_line).encode(
            "ascii"
        )
    _publish_jig_tool_alias(target, payload, windows=windows)
    return target


def write_jig_tool_aliases(
    layout: ValidationEnvironmentLayout = LAYOUT,
    *,
    windows: bool = WINDOWS,
) -> tuple[tuple[str, Path], ...]:
    """Publish physical, stable, neutral Jig executable aliases.

    Returns:
        Stable tool-ID and repository-local alias pairs.

    """
    tool_ids = ("basedpyright", "pytest", "ruff")
    alias_root = layout.environment / "jig-bin"
    _check_jig_alias_path(alias_root, directory=True, required=False)
    for tool_id in tool_ids:
        source, target = _jig_alias_source_and_target(
            layout, tool_id, windows=windows
        )
        _ = _jig_source_identity(source)
        _check_jig_alias_path(target, directory=False, required=False)
    alias_root.mkdir(parents=True, exist_ok=True)
    _check_jig_alias_path(alias_root, directory=True, required=True)
    aliases: list[tuple[str, Path]] = []
    for tool_id in tool_ids:
        target = _write_jig_tool_alias(layout, tool_id, windows=windows)
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
