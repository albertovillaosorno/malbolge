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

import hashlib
import http.client
import io
import json
import lzma
import ntpath
import os
import platform
import stat
import string

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed repository-local argv.
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import venv
import zipfile
import zlib
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import BinaryIO, Final, Never, Protocol, cast

from compression import zstd

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
MAX_UV_ARCHIVE_BYTES: Final = 128 * 1024 * 1024
MAX_UV_BINARY_BYTES: Final = 128 * 1024 * 1024
MAX_UV_ARCHIVE_MEMBERS: Final = 4096
MAX_JIG_TOOL_BINARY_BYTES: Final = 256 * 1024 * 1024
UV_BINARY_MODE: Final = 0o755
JIG_BINARY_MODE: Final = 0o755
URL_SUFFIX_MARKERS: Final = frozenset(("?", "#"))
URL_UNRESERVED_CHARACTERS: Final = frozenset(
    string.ascii_letters + string.digits + "-._~"
)
BASEDPYRIGHT_TOOL_ID: Final = "basedpyright"
PYTEST_TOOL_ID: Final = "pytest"
JIG_FAST_VERSION_TOOL_IDS: Final = frozenset((
    BASEDPYRIGHT_TOOL_ID,
    PYTEST_TOOL_ID,
))
SHELL_UNSAFE_VERSION_CHARACTERS: Final = frozenset(("'", "\n", "\r"))
VERSION_PROBE_ARGUMENTS: Final = ("--version",)


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


def _native_error_name(error: BaseException) -> str:
    """Read the real class name without foreign metaclass hooks.

    Returns:
        Native exception class name.

    """
    name = type.__getattribute__(  # ruff: ignore[unnecessary-dunder-call]
        type(error), "__name__"
    )
    return cast("str", name)


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
    windows_invalid = bool(windows_path.drive or windows_path.root)
    windows_invalid = windows_invalid or ntpath.isreserved(value)
    # Release URL segments must not carry delimiters, escapes, or bidi text.
    safe_url_segment = all(
        character in URL_UNRESERVED_CHARACTERS for character in value
    )
    unsafe_path = reserved or has_separator or windows_invalid
    if unsafe_path or not safe_url_segment:
        _fail(f"{label}.{key} must be one repository-local path segment")
    return value


def _required_url_asset(
    document: dict[str, object],
    platform_id: str,
) -> str:
    value = _required_string(document, "asset", platform_id)
    if any(marker in value for marker in URL_SUFFIX_MARKERS):
        _fail(f"{platform_id}.asset must be one URL path segment")
    return _required_path_segment(document, "asset", platform_id)


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
            status.st_nlink,
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
    if status.st_nlink != 1:
        _fail("uv toolchain manifest must be single-link")
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
        if type(content) is not bytes:
            _fail("uv toolchain manifest stream must return native bytes")
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
        message = (
            "cannot read uv toolchain manifest: "
            f"{_native_error_name(error)}"
        )
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
    if len(data) > MAX_UV_ARCHIVE_BYTES:
        _fail("uv archive exceeds byte limit")
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
            data = response.read(MAX_UV_ARCHIVE_BYTES + 1)
    except (
        OSError,
        http.client.HTTPException,
        ValueError,
        TypeError,
        RuntimeError,
    ) as error:
        message = (
            "cannot download pinned uv artifact: "
            f"{_native_error_name(error)}"
        )
        raise ProvisionError(message) from error
    verify_uv_archive(data, artifact.sha256)
    return data


def _bounded_uv_member_bytes(content: bytes) -> bytes:
    """Require a physical-size bound on one extracted uv executable."""
    if type(content) is not bytes:
        _fail("uv extracted member requires native bytes")
    if len(content) > MAX_UV_BINARY_BYTES:
        _fail("uv extracted member exceeds byte limit")
    return content


def _zip_member_bytes(data: bytes, member: str) -> bytes:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        inventory = archive.infolist()
        if len(inventory) > MAX_UV_ARCHIVE_MEMBERS:
            _fail("uv archive exceeds member limit")
        info = archive.getinfo(member)
        if sum(item.filename == member for item in inventory) != 1:
            _fail("duplicate uv zip member name")
        if (
            type(info) is not zipfile.ZipInfo
            or type(info.file_size) is not int
            or type(info.external_attr) is not int
        ):
            _fail("uv zip member requires native size and type metadata")
        unix_type = stat.S_IFMT(info.external_attr >> 16)
        dos_nonfile = bool(info.external_attr & 0x18)
        if (
            info.is_dir()
            or dos_nonfile
            or unix_type not in (0, stat.S_IFREG)
        ):
            _fail("uv zip member must be a regular file")
        if info.file_size < 0 or info.file_size > MAX_UV_BINARY_BYTES:
            _fail("uv extracted member exceeds byte limit")
        with archive.open(info) as stream:
            content = _bounded_uv_member_bytes(
                stream.read(MAX_UV_BINARY_BYTES + 1)
            )
        if len(content) != info.file_size:
            _fail("uv zip member length differs from declared size")
        return content


def _tar_member_bytes(data: bytes, member_name: str) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        selected: tarfile.TarInfo | None = None
        for index in range(MAX_UV_ARCHIVE_MEMBERS + 1):
            candidate = archive.next()
            if candidate is None:
                break
            if index == MAX_UV_ARCHIVE_MEMBERS:
                _fail("uv archive exceeds member limit")
            if candidate.name != member_name:
                if (
                    type(candidate) is not tarfile.TarInfo
                    or type(candidate.size) is not int
                ):
                    _fail("uv tar member requires native size metadata")
                if candidate.size < 0 or candidate.size > MAX_UV_BINARY_BYTES:
                    _fail("uv archive member exceeds byte limit")
            if candidate.name == member_name:
                if selected is not None:
                    _fail("duplicate uv tar member name")
                selected = candidate
        if selected is None:
            raise KeyError(member_name)
        info = selected
        if type(info) is not tarfile.TarInfo or type(info.size) is not int:
            _fail("uv tar member requires native size metadata")
        if not info.isfile():
            _fail(f"uv archive member is not a file: {member_name}")
        if info.size < 0 or info.size > MAX_UV_BINARY_BYTES:
            _fail("uv extracted member exceeds byte limit")
        member = archive.extractfile(info)
        if member is None:
            _fail(f"uv archive member is not a file: {member_name}")
        with member:
            return _bounded_uv_member_bytes(member.read(MAX_UV_BINARY_BYTES + 1))


def _uv_member_bytes(data: bytes, artifact: UvArtifact) -> bytes:
    if type(data) is not bytes:
        _fail("uv compressed archive requires native bytes")
    if len(data) > MAX_UV_ARCHIVE_BYTES:
        _fail("uv archive exceeds byte limit")
    try:
        if artifact.asset.endswith(".zip"):
            return _zip_member_bytes(data, artifact.member)
        return _tar_member_bytes(data, artifact.member)
    except ProvisionError:
        raise
    except (
        EOFError,
        KeyError,
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        tarfile.TarError,
        zipfile.BadZipFile,
        lzma.LZMAError,
        zlib.error,
        zstd.ZstdError,
    ) as error:
        message = (
            "cannot extract pinned uv artifact: "
            f"{_native_error_name(error)}"
        )
        raise ProvisionError(message) from error


def _uv_version_matches(output: str, artifact: UvArtifact) -> bool:
    """Admit only the exact pinned uv banner and its artifact target triple."""
    if type(output) is not str:
        return False
    expected = f"uv {artifact.version}"
    if output == expected:
        return True
    if not artifact.asset.startswith("uv-"):
        return False
    if artifact.asset.endswith(".tar.gz"):
        extension = ".tar.gz"
    elif artifact.asset.endswith(".zip"):
        extension = ".zip"
    else:
        return False
    target = artifact.asset[3 : -len(extension)]
    return bool(target) and output == f"{expected} ({target})"


def _uv_physical_provision_status(
    path: Path,
    *,
    required: bool,
) -> os.stat_result | None:
    """Admit native host link and physical-file observations for a uv path."""
    try:
        symlink = path.is_symlink()
        junction = path.is_junction()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = "cannot inspect uv provision path link status"
        raise ProvisionError(message) from error
    if type(symlink) is not bool or type(junction) is not bool:
        _fail(f"uv provision link status must be native: {path}")
    if symlink or junction:
        _fail(f"uv provision path must not redirect: {path}")
    try:
        status = path.lstat()
    except FileNotFoundError:
        if required:
            _fail(f"uv provision path disappeared: {path}")
        return None
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = "cannot inspect uv provision path file status"
        raise ProvisionError(message) from error
    if type(status) is not os.stat_result or any(
        type(field) is not int
        for field in (
            status.st_mode,
            status.st_nlink,
            status.st_dev,
            status.st_ino,
            status.st_size,
        )
    ):
        _fail(f"uv provision file status must be native: {path}")
    return status


def _admit_uv_directory(
    path: Path,
    *,
    required: bool = False,
) -> os.stat_result | None:
    """Require a physical uv provisioning directory if present.

    Returns:
        Physical directory metadata, or None for an optional missing path.

    """
    status = _uv_physical_provision_status(path, required=required)
    if status is None:
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
    return _uv_physical_provision_status(path, required=required)


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


def _open_uv_physical_parent(
    path: Path, *, create: bool = False
) -> int | None:
    """Pin each POSIX directory component without following ancestor aliases.

    Returns:
        Owned physical parent descriptor on POSIX, or None on Windows.

    """
    parent = path.parent.absolute()
    if os.name != "posix":
        _ = _admit_uv_provision_path(parent, directory=True, required=True)
        return None
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    descriptor: int | None = None
    complete = False
    try:
        descriptor = os.open(parent.anchor, flags)
        if type(descriptor) is not int or descriptor < 0:
            _fail("uv parent descriptor requires native handle")
        for component in parent.parts[1:]:
            try:
                child = os.open(component, flags, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(component, mode=0o755, dir_fd=descriptor)
                child = os.open(component, flags, dir_fd=descriptor)
            if type(child) is not int or child < 0:
                _fail("uv parent descriptor requires native handle")
            try:
                os.close(descriptor)
            except (OSError, ValueError, TypeError, RuntimeError):
                # The next component was opened already; it is not the
                # descriptor that the failure path normally closes.
                with suppress(OSError):
                    os.close(child)
                raise
            descriptor = child
        opened = os.fstat(descriptor)
        named = parent.lstat()
        if (
            type(opened) is not os.stat_result
            or type(named) is not os.stat_result
            or any(
                type(field) is not int
                for status in (opened, named)
                for field in (status.st_mode, status.st_dev, status.st_ino)
            )
            or not stat.S_ISDIR(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("uv parent descriptor does not match physical directory")
        _ = _admit_uv_provision_path(parent, directory=True, required=True)
        complete = True
        return descriptor
    except ProvisionError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = "uv parent physical descriptor admission failed"
        raise ProvisionError(message) from error
    finally:
        if not complete and type(descriptor) is int and descriptor >= 0:
            with suppress(OSError):
                os.close(descriptor)


def _close_uv_parent_descriptor(descriptor: int, *, context: str) -> None:
    """Keep descriptor-close faults within the typed uv trust boundary."""
    try:
        os.close(descriptor)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = f"uv {context} parent descriptor close failed"
        raise ProvisionError(message) from error


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
        type(status) is os.stat_result
        and all(
            type(field) is int
            for field in (
                status.st_mode,
                status.st_nlink,
                status.st_dev,
                status.st_ino,
                status.st_size,
            )
        )
        and stat.S_ISREG(status.st_mode)
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
        os.O_RDWR
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    parent_descriptor = _open_uv_physical_parent(temporary)
    descriptor: int | None = None
    try:
        if parent_descriptor is None:
            descriptor = os.open(temporary, flags, 0o600)
        else:
            descriptor = os.open(
                temporary.name, flags, 0o600, dir_fd=parent_descriptor
            )
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = "uv staging descriptor creation failed"
        raise ProvisionError(message) from error
    finally:
        if parent_descriptor is not None:
            try:
                _close_uv_parent_descriptor(parent_descriptor, context="staging")
            except ProvisionError:
                # Exclusive creation may already have opened a new stage.
                # Do not leak that handle or leave an owned half-stage behind.
                if type(descriptor) is int and descriptor >= 0:
                    try:
                        opened = os.fstat(descriptor)
                        if (
                            type(opened) is os.stat_result
                            and type(opened.st_dev) is int
                            and type(opened.st_ino) is int
                            and _uv_stage_is_owned(
                                temporary,
                                (opened.st_dev, opened.st_ino),
                                expected_size=0,
                            )
                        ):
                            temporary.unlink()
                    except (OSError, ValueError, TypeError, RuntimeError):
                        pass
                    finally:
                        with suppress(OSError):
                            os.close(descriptor)
                raise
    if type(descriptor) is not int or descriptor < 0:
        _fail("uv staging descriptor must be native")
    try:
        status = os.fstat(descriptor)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        with suppress(OSError):
            os.close(descriptor)
        message = "uv staging descriptor inspection failed"
        raise ProvisionError(message) from error
    if (
        type(status) is not os.stat_result
        or any(
            type(field) is not int
            for field in (
                status.st_mode,
                status.st_nlink,
                status.st_dev,
                status.st_ino,
                status.st_size,
            )
        )
        or not stat.S_ISREG(status.st_mode)
        or status.st_nlink != 1
        or status.st_size != 0
    ):
        with suppress(OSError):
            os.close(descriptor)
        _fail("uv staging descriptor requires native empty regular file status")
    return descriptor, (status.st_dev, status.st_ino)


def _uv_stage_descriptor_is_owned(
    status: os.stat_result, identity: tuple[int, int], size: int
) -> bool:
    """Require native, stable descriptor metadata for a private uv stage."""
    return (
        type(status) is os.stat_result
        and all(
            type(field) is int
            for field in (
                status.st_mode,
                status.st_nlink,
                status.st_dev,
                status.st_ino,
                status.st_size,
                status.st_mtime_ns,
                status.st_ctime_ns,
            )
        )
        and stat.S_ISREG(status.st_mode)
        and status.st_nlink == 1
        and (status.st_dev, status.st_ino) == identity
        and status.st_size == size
    )


def _verify_uv_stage_descriptor_bytes(
    temporary: Path,
    descriptor: int,
    identity: tuple[int, int],
    binary: bytes,
) -> None:
    """Read back actual bytes from the same admitted physical stage inode."""
    if not _uv_stage_is_owned(temporary, identity, expected_size=len(binary)):
        _fail("uv staging changed before byte verification")
    initial = os.fstat(descriptor)
    if not _uv_stage_descriptor_is_owned(initial, identity, len(binary)):
        _fail("uv staging descriptor changed before byte verification")
    offset = os.lseek(descriptor, 0, os.SEEK_SET)
    if type(offset) is not int or offset != 0:
        _fail("uv staging descriptor seek must return native zero")
    while offset < len(binary):
        observed = os.read(descriptor, min(1_048_576, len(binary) - offset))
        if (
            type(observed) is not bytes
            or not observed
            or observed != binary[offset : offset + len(observed)]
        ):
            _fail("uv staging bytes differ from pinned executable")
        offset += len(observed)
    terminator = os.read(descriptor, 1)
    if type(terminator) is not bytes or terminator:
        _fail("uv staging bytes exceed pinned executable")
    if not _uv_stage_is_owned(temporary, identity, expected_size=len(binary)):
        _fail("uv staging changed during byte verification")
    final = os.fstat(descriptor)
    if (
        not _uv_stage_descriptor_is_owned(final, identity, len(binary))
        or (final.st_mtime_ns, final.st_ctime_ns)
        != (initial.st_mtime_ns, initial.st_ctime_ns)
    ):
        _fail("uv staging descriptor changed during byte verification")


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
    _verify_uv_stage_descriptor_bytes(temporary, descriptor, identity, binary)


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
    if type(binary) is not bytes:
        _fail("uv executable payload requires native bytes")
    if len(binary) > MAX_UV_BINARY_BYTES:
        _fail("uv executable payload exceeds byte limit")
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
        try:
            os.close(descriptor)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            complete = False
            raise ProvisionError("uv staging descriptor close failed") from error
        finally:
            if not complete and _uv_stage_is_owned(temporary, identity):
                with suppress(OSError):
                    temporary.unlink()


def _require_uv_destination_absent(executable: Path) -> None:
    """Reject a destination created by another process during provisioning."""
    if _admit_uv_provision_path(executable) is not None:
        _fail(f"uv executable appeared during provisioning: {executable}")


def _uv_linked_stage_is_owned(
    temporary: Path, executable: Path, identity: tuple[int, int], size: int
) -> bool:
    """Require both names of a pending hardlink publication to be private."""
    try:
        stage = temporary.lstat()
        destination = executable.lstat()
    except (OSError, ValueError, TypeError, RuntimeError):
        return False
    return all(
        type(status) is os.stat_result
        and all(
            type(field) is int
            for field in (
                status.st_mode,
                status.st_nlink,
                status.st_dev,
                status.st_ino,
                status.st_size,
            )
        )
        and stat.S_ISREG(status.st_mode)
        and status.st_nlink == 2
        and (status.st_dev, status.st_ino) == identity
        and status.st_size == size
        for status in (stage, destination)
    )


def _publish_uv_stage(
    temporary: Path,
    executable: Path,
    identity: tuple[int, int],
    *,
    binary: bytes,
) -> None:
    """Publish only a byte-attested private stage into a physical destination."""
    _ = _admit_uv_provision_path(
        executable.parent, directory=True, required=True
    )
    _require_uv_destination_absent(executable)
    if not _uv_stage_is_owned(temporary, identity, expected_size=len(binary)):
        _fail("uv staging changed before publication")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        descriptor = os.open(temporary, flags)
        if type(descriptor) is not int or descriptor < 0:
            _fail("uv staging read descriptor must be native")
        try:
            _verify_uv_stage_descriptor_bytes(
                temporary, descriptor, identity, binary
            )
        finally:
            os.close(descriptor)
    except ProvisionError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = "uv staging publication verification failed"
        raise ProvisionError(message) from error
    # A rename overwrites a late competing destination. Linking is atomic
    # no-replace publication, pinned to one physical POSIX directory.
    parent_descriptor = _open_uv_physical_parent(executable)
    try:
        try:
            if parent_descriptor is None:
                os.link(temporary, executable, follow_symlinks=False)
            else:
                os.link(
                    temporary.name,
                    executable.name,
                    src_dir_fd=parent_descriptor,
                    dst_dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
        except FileExistsError as error:
            message = f"uv executable appeared during provisioning: {executable}"
            raise ProvisionError(message) from error
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            message = "uv staging publication link failed"
            raise ProvisionError(message) from error
        if not _uv_linked_stage_is_owned(
            temporary, executable, identity, len(binary)
        ):
            _fail("uv linked stage changed during publication")
        try:
            if parent_descriptor is None:
                temporary.unlink()
            else:
                os.unlink(temporary.name, dir_fd=parent_descriptor)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            message = "uv staging source removal failed"
            raise ProvisionError(message) from error
        checked = _admit_uv_provision_path(executable, required=True)
        if checked is None or (checked.st_dev, checked.st_ino) != identity:
            _fail("uv executable changed during publication")
        try:
            if parent_descriptor is None:
                descriptor = os.open(executable, flags)
            else:
                descriptor = os.open(
                    executable.name, flags, dir_fd=parent_descriptor
                )
            if type(descriptor) is not int or descriptor < 0:
                _fail("uv published read descriptor must be native")
            try:
                _verify_uv_stage_descriptor_bytes(
                    executable, descriptor, identity, binary
                )
            finally:
                os.close(descriptor)
        except ProvisionError:
            raise
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            message = "uv published executable byte verification failed"
            raise ProvisionError(message) from error
    finally:
        if parent_descriptor is not None:
            _close_uv_parent_descriptor(parent_descriptor, context="publication")


def _provision_uv_binary(
    executable: Path,
    binary: bytes,
    *,
    windows: bool,
) -> None:
    """Provision one new uv executable without following staging aliases."""
    _ = _admit_uv_provision_path(executable.parent, directory=True)
    if os.name == "posix":
        parent_descriptor = _open_uv_physical_parent(executable, create=True)
        if parent_descriptor is None:
            _fail("uv provisioning parent requires native descriptor")
        _close_uv_parent_descriptor(parent_descriptor, context="provisioning")
    else:
        executable.parent.mkdir(parents=True, exist_ok=True)
    _ = _admit_uv_provision_path(
        executable.parent, directory=True, required=True
    )
    _require_uv_destination_absent(executable)
    temporary = executable.with_name(f"{executable.name}.tmp")
    identity = _write_verified_uv_binary(temporary, binary, windows=windows)
    try:
        _publish_uv_stage(
            temporary, executable, identity, binary=binary
        )
    finally:
        if _uv_stage_is_owned(temporary, identity):
            temporary.unlink(missing_ok=True)


def _uv_executable_identity(status: os.stat_result) -> tuple[int, ...]:
    """Bind a version probe to one native executable identity and mutation state."""
    if type(status) is not os.stat_result or any(
        type(field) is not int
        for field in (
            status.st_mode,
            status.st_nlink,
            status.st_dev,
            status.st_ino,
            status.st_size,
            status.st_mtime_ns,
            status.st_ctime_ns,
        )
    ):
        _fail("uv executable requires native file status")
    return (
        status.st_mode,
        status.st_nlink,
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def ensure_uv(
    root: Path = ROOT,
    *,
    platform_id: str | None = None,
) -> Path:
    """Provision and verify the pinned standalone uv executable.

    Returns:
        Verified repository-local uv executable.

    """
    # Freeze relative checkout identity before download or version callbacks.
    # absolute() does not resolve aliases; path admission still rejects them.
    selected_root = root.absolute()
    selected = platform_id or uv_platform_id()
    artifact = uv_artifact(selected)
    executable = uv_executable(artifact, selected_root)
    installed = _admit_uv_provision_path(executable)
    if installed is not None:
        original = _uv_executable_identity(installed)
        output = _run([str(executable), "--version"])
        checked = _admit_uv_provision_path(executable, required=True)
        if checked is None or _uv_executable_identity(checked) != original:
            _fail("uv executable changed during version probe")
        if _uv_version_matches(output, artifact):
            return executable
        _fail(f"unexpected uv version at {executable}: {output!r}")
    data = _download_uv_archive(artifact)
    binary = _uv_member_bytes(data, artifact)
    _provision_uv_binary(
        executable, binary, windows=selected.startswith("windows-")
    )
    installed = _admit_uv_provision_path(executable, required=True)
    if installed is None:
        _fail("uv executable disappeared before version probe")
    original = _uv_executable_identity(installed)
    output = _run([str(executable), "--version"])
    checked = _admit_uv_provision_path(executable, required=True)
    if checked is None or _uv_executable_identity(checked) != original:
        _fail("uv executable changed during version probe")
    if not _uv_version_matches(output, artifact):
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
    # Anchor all tool and interpreter paths without dereferencing aliases.
    selected_root = root.absolute()
    environment = selected_root / ".dependencies" / "python" / "3.14.7"
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
        detail = (
            str(error)
            if type(error) in native_types
            else _native_error_name(error)
        )
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
    if tuple(command[1:]) == VERSION_PROBE_ARGUMENTS:
        if completed.stderr:
            _fail("Python bootstrap version probe emitted stderr diagnostics")
        if completed.stdout.endswith("\r\n"):
            version_output = completed.stdout[:-2]
        else:
            version_output = completed.stdout.removesuffix("\n")
        if version_output != version_output.strip():
            _fail("Python bootstrap version probe stdout is not canonical")
        return version_output
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
    native_nonblank = type(version_line) is str and bool(version_line.strip())
    printable_ascii = (
        native_nonblank
        and version_line == version_line.strip()
        and version_line.isascii()
        and version_line.isprintable()
    )
    if not printable_ascii or any(
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
    _ = _check_jig_alias_path(scripts, directory=True, required=True)
    launchers = (layout.python_launcher, layout.pytest_launcher)
    for target in launchers:
        _ = _check_jig_alias_path(target, directory=False, required=False)
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


def _jig_alias_physical_status(
    path: Path, *, required: bool
) -> os.stat_result | None:
    """Require native, nonredirected host status for a Jig alias component."""
    try:
        symlink = path.is_symlink()
        junction = path.is_junction()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise ProvisionError("cannot inspect Jig alias link status") from error
    if type(symlink) is not bool or type(junction) is not bool:
        _fail(f"Jig alias link status must be native: {path}")
    try:
        observed = path.lstat()
    except FileNotFoundError:
        if required:
            _fail(f"missing provisioned tool for Jig alias: {path}")
        return None
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise ProvisionError("cannot inspect Jig alias file status") from error
    if type(observed) is not os.stat_result or any(
        type(field) is not int
        for field in (
            observed.st_mode,
            observed.st_nlink,
            observed.st_dev,
            observed.st_ino,
            observed.st_size,
            observed.st_mtime_ns,
            observed.st_ctime_ns,
        )
    ):
        _fail(f"Jig alias file status must be native: {path}")
    if symlink or junction or stat.S_ISLNK(observed.st_mode):
        _fail(f"Jig alias path must not redirect: {path}")
    return observed


def _check_jig_alias_parents(path: Path) -> None:
    """Reject a redirected or non-directory ancestor of a Jig alias."""
    for parent in reversed(path.parents):
        observed = _jig_alias_physical_status(parent, required=False)
        if observed is not None and not stat.S_ISDIR(observed.st_mode):
            _fail(f"Jig alias parent must be a directory: {parent}")


def _check_jig_alias_path(
    path: Path,
    *,
    directory: bool,
    required: bool,
) -> os.stat_result | None:
    """Admit native physical Jig alias ancestry and leaf status."""
    _check_jig_alias_parents(path)
    observed = _jig_alias_physical_status(path, required=required)
    if observed is not None:
        expected_type = stat.S_ISDIR if directory else stat.S_ISREG
        if not expected_type(observed.st_mode):
            _fail(f"Jig alias path must be a physical regular artifact: {path}")
    return observed


def _jig_source_identity(source: Path) -> tuple[int, int, int, int, int]:
    """Require one bounded physical source and return its stable identity.

    Returns:
        Device, inode, size and modification/change times.

    """
    status = _check_jig_alias_path(source, directory=False, required=True)
    if status is None:
        _fail(f"missing provisioned tool for Jig alias: {source}")
    if status.st_nlink != 1:
        _fail("Jig alias source must be single-link")
    if status.st_size < 0 or status.st_size > MAX_JIG_TOOL_BINARY_BYTES:
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
    if type(descriptor) is not int or descriptor < 0:
        _fail("bootstrap binary descriptor must be a native nonnegative integer")
    try:
        stream = os.fdopen(descriptor, mode)
    except OSError, ValueError, TypeError, RuntimeError:
        with suppress(OSError):
            os.close(descriptor)
        raise
    required_stream_type = io.BufferedReader if mode == "rb" else io.BufferedWriter
    if not (
        type(stream) is required_stream_type
        and type(stream.raw) is io.FileIO
        and stream.fileno() == descriptor
        and stream.raw.fileno() == descriptor
    ):
        with suppress(OSError):
            os.close(descriptor)
        _fail("bootstrap requires native buffered binary stream on owned descriptor")
    return cast("BinaryIO", stream)


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
        if observed.st_nlink != 1:
            _fail("Jig alias source descriptor must be single-link")
        if _jig_file_identity(observed) != expected:
            _fail("Jig alias source changed before read")
        data = stream.read(MAX_JIG_TOOL_BINARY_BYTES + 1)
        if type(data) is not bytes:
            _fail("Jig alias source read requires native bytes")
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
            "Jig alias source read failed: "
            f"{source}: {_native_error_name(error)}"
        )
        raise ProvisionError(message) from error
    if type(data) is not bytes:
        _fail("Jig alias source read must return native bytes")
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
    if type(descriptor) is not int or descriptor < 0:
        _fail("Jig alias temporary descriptor must be native and nonnegative")
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
    if any(
        type(observed) is not os.stat_result
        or any(
            type(field) is not int
            for field in (
                observed.st_mode,
                observed.st_nlink,
                observed.st_dev,
                observed.st_ino,
                observed.st_size,
            )
        )
        for observed in (descriptor_status, pathname_status)
    ):
        _fail("Jig alias temporary requires native file status")
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
        type(status) is os.stat_result
        and all(
            type(field) is int
            for field in (
                status.st_mode,
                status.st_nlink,
                status.st_dev,
                status.st_ino,
                status.st_size,
            )
        )
        and stat.S_ISREG(status.st_mode)
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
    except ProvisionError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = (
            "Jig alias temporary stream failed: "
            f"{_native_error_name(error)}"
        )
        raise ProvisionError(message) from error


def _jig_stage_descriptor_identity(
    status: os.stat_result, identity: tuple[int, int], size: int
) -> tuple[int, int]:
    """Admit stable native physical metadata for a staged Jig alias."""
    if (
        type(status) is not os.stat_result
        or any(
            type(field) is not int
            for field in (
                status.st_mode,
                status.st_nlink,
                status.st_dev,
                status.st_ino,
                status.st_size,
                status.st_mtime_ns,
                status.st_ctime_ns,
            )
        )
        or not stat.S_ISREG(status.st_mode)
        or status.st_nlink != 1
        or (status.st_dev, status.st_ino) != identity
        or status.st_size != size
    ):
        _fail("Jig alias stage requires stable native descriptor metadata")
    return status.st_mtime_ns, status.st_ctime_ns


def _verify_jig_alias_stage_bytes(
    temporary: Path, identity: tuple[int, int], payload: bytes
) -> None:
    """Require the final private stage bytes to equal the selected alias."""
    if not _jig_alias_stage_is_owned(
        temporary, identity, expected_size=len(payload)
    ):
        _fail("Jig alias stage changed before byte verification")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        descriptor = os.open(temporary, flags)
        if type(descriptor) is not int or descriptor < 0:
            _fail("Jig alias stage read descriptor must be native")
        try:
            initial = _jig_stage_descriptor_identity(
                os.fstat(descriptor), identity, len(payload)
            )
            offset = 0
            while offset < len(payload):
                chunk = os.read(descriptor, min(1_048_576, len(payload) - offset))
                if (
                    type(chunk) is not bytes
                    or not chunk
                    or chunk != payload[offset : offset + len(chunk)]
                ):
                    _fail("Jig alias staged bytes differ from payload")
                offset += len(chunk)
            terminator = os.read(descriptor, 1)
            if type(terminator) is not bytes or terminator:
                _fail("Jig alias staged bytes exceed payload")
            final = _jig_stage_descriptor_identity(
                os.fstat(descriptor), identity, len(payload)
            )
            if final != initial:
                _fail("Jig alias stage metadata changed during byte verification")
        finally:
            os.close(descriptor)
    except ProvisionError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = "Jig alias staged bytes verification failed"
        raise ProvisionError(message) from error
    if not _jig_alias_stage_is_owned(
        temporary, identity, expected_size=len(payload)
    ):
        _fail("Jig alias stage changed during byte verification")


def _replace_jig_alias_stage(
    temporary: Path,
    target: Path,
    identity: tuple[int, int],
    size: int,
    *,
    windows: bool,
) -> None:
    """Replace within the pinned POSIX parent, never a late path redirect."""
    if windows or os.name != "posix":
        _ = temporary.replace(target)
        return
    if temporary.parent != target.parent:
        _fail("Jig alias stage and target require one physical parent")
    # Reuse the descriptor-by-component traversal used by uv publication.
    parent_descriptor = _open_uv_physical_parent(target)
    if parent_descriptor is None:
        _fail("Jig alias publication requires a POSIX parent descriptor")
    try:
        stage = os.stat(temporary.name, dir_fd=parent_descriptor, follow_symlinks=False)
        if (
            type(stage) is not os.stat_result
            or any(
                type(field) is not int
                for field in (
                    stage.st_mode,
                    stage.st_nlink,
                    stage.st_dev,
                    stage.st_ino,
                    stage.st_size,
                )
            )
            or not stat.S_ISREG(stage.st_mode)
            or stage.st_nlink != 1
            or (stage.st_dev, stage.st_ino) != identity
            or stage.st_size != size
        ):
            _fail("Jig alias stage changed before pinned replacement")
        os.replace(
            temporary.name,
            target.name,
            src_dir_fd=parent_descriptor,
            dst_dir_fd=parent_descriptor,
        )
    except ProvisionError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise ProvisionError("Jig alias pinned replacement failed") from error
    finally:
        _close_uv_parent_descriptor(parent_descriptor, context="Jig alias")


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
    _ = _check_jig_alias_path(target.parent, directory=True, required=True)
    _ = _check_jig_alias_path(target, directory=False, required=False)
    if not _jig_alias_stage_is_owned(
        temporary, identity, expected_size=len(payload)
    ):
        _fail("Jig alias temporary changed before publication")
    _verify_jig_alias_stage_bytes(temporary, identity, payload)
    _replace_jig_alias_stage(temporary, target, identity, len(payload), windows=windows)
    _ = _check_jig_alias_path(target, directory=False, required=True)
    _verify_jig_alias_stage_bytes(target, identity, payload)


def _publish_jig_tool_alias(
    target: Path,
    payload: bytes,
    *,
    windows: bool,
) -> None:
    """Atomically replace an admitted alias instead of following its leaf."""
    if type(payload) is not bytes:
        _fail("Jig alias payload requires native bytes")
    if len(payload) > MAX_JIG_TOOL_BINARY_BYTES:
        _fail("Jig alias payload exceeds byte limit")
    alias_root = target.parent
    _ = _check_jig_alias_path(alias_root, directory=True, required=True)
    _ = _check_jig_alias_path(target, directory=False, required=False)
    prefix = f".{target.name}."
    try:
        descriptor, temporary_name = tempfile.mkstemp(prefix=prefix, dir=alias_root)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise ProvisionError("Jig alias temporary creation failed") from error
    if type(descriptor) is not int or descriptor < 0:
        _fail("Jig alias temporary descriptor must be native and nonnegative")
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
    _ = _check_jig_alias_path(alias_root, directory=True, required=False)
    for tool_id in tool_ids:
        source, target = _jig_alias_source_and_target(
            layout, tool_id, windows=windows
        )
        _ = _jig_source_identity(source)
        _ = _check_jig_alias_path(target, directory=False, required=False)
    alias_root.mkdir(parents=True, exist_ok=True)
    _ = _check_jig_alias_path(alias_root, directory=True, required=True)
    aliases: list[tuple[str, Path]] = []
    for tool_id in tool_ids:
        target = _write_jig_tool_alias(layout, tool_id, windows=windows)
        aliases.append((tool_id, target))
    return tuple(aliases)


def _require_python_interpreter_identity(
    path: Path,
    expected: os.stat_result | None,
    *,
    context: str,
) -> os.stat_result | None:
    """Recheck one Python target before following it in a new process.

    Returns:
        Current native interpreter status or None for an absent target.

    """
    observed = _check_jig_alias_path(path, directory=False, required=False)
    if expected is None:
        if observed is not None:
            _fail(f"Python interpreter appeared during {context}")
    elif (
        observed is None
        or observed.st_nlink != 1
        or _jig_file_identity(observed) != _jig_file_identity(expected)
    ):
        _fail(f"Python interpreter changed during {context}")
    return observed


def _python_requirements_identity() -> tuple[int, int, int, int, int]:
    """Require one bounded physical, single-link validation requirements file.

    Returns:
        Original source identity for checks around external pip execution.

    """
    identity = _jig_source_identity(REQUIREMENTS)
    if identity[2] <= 0 or identity[2] > MAX_UV_MANIFEST_BYTES:
        _fail("Python validation requirements exceed supported byte limits")
    return identity


def _provision(
    layout: ValidationEnvironmentLayout,
    *,
    root: Path = ROOT,
) -> None:
    selected_root = root.absolute()
    if type(layout) is not ValidationEnvironmentLayout or layout != validation_layout(
        selected_root
    ):
        _fail("Python provisioning layout must match the selected checkout")
    # uv pip sync can modify the selected Python interpreter and environment.
    # Refuse redirected ancestors, foreign leaves, and externally linked inodes
    # before executing the provisioner or creating a virtual environment.
    _ = _check_jig_alias_path(layout.environment, directory=True, required=False)
    python_status = _check_jig_alias_path(
        layout.python, directory=False, required=False
    )
    if python_status is not None and python_status.st_nlink != 1:
        _fail("Python provisioned interpreter must be single-link")
    requirements_identity = _python_requirements_identity()
    uv = ensure_uv(selected_root)
    # Reject a post-uv redirect or inode substitution before running pip.
    _ = _require_python_interpreter_identity(
        layout.python, python_status, context="uv bootstrap"
    )
    if python_status is None:
        builder = venv.EnvBuilder(with_pip=False, clear=False)
        builder.create(layout.environment)
    # A new venv Python must exist and be physical/private before subprocess use.
    sync_target = _check_jig_alias_path(
        layout.python, directory=False, required=True
    )
    if sync_target is None:
        _fail("Python provisioned interpreter missing before pip sync")
    if sync_target.st_nlink != 1:
        _fail("Python provisioned interpreter must be single-link")
    if _python_requirements_identity() != requirements_identity:
        _fail("Python validation requirements changed before pip sync")
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
    _ = _require_python_interpreter_identity(
        layout.python, sync_target, context="pip sync"
    )
    if _python_requirements_identity() != requirements_identity:
        _fail("Python validation requirements changed during pip sync")
    _ = _run([
        str(uv),
        "pip",
        "uninstall",
        "--no-config",
        "--python",
        str(layout.python),
        "pip",
    ])
    _ = _require_python_interpreter_identity(
        layout.python, sync_target, context="pip uninstall"
    )
    write_launchers(layout, windows=WINDOWS)
    _ = _require_python_interpreter_identity(
        layout.python, sync_target, context="launcher publication"
    )
    _ = write_jig_tool_aliases(layout, windows=WINDOWS)
    _ = _require_python_interpreter_identity(
        layout.python, sync_target, context="Jig alias publication"
    )


def _verify_tool(
    layout: ValidationEnvironmentLayout,
    executable: str,
    expected: str,
) -> None:
    path = layout.scripts / executable
    if not path.is_file():
        _fail(f"missing provisioned tool: {path}")
    original = _jig_source_identity(path)
    output = _run([str(path), "--version"])
    if _jig_source_identity(path) != original:
        _fail(f"provisioned tool changed during version probe: {path}")
    first_line = output.partition("\n")[0]
    if not first_line.isprintable() or (
        first_line != expected and not first_line.startswith(f"{expected} ")
    ):
        _fail(f"unexpected {executable} version: {first_line!r}")


def _verify(layout: ValidationEnvironmentLayout) -> None:
    for executable, expected in layout.expected_tools:
        _verify_tool(layout, executable, expected)


def initialize(root: Path = ROOT) -> ValidationEnvironmentLayout:
    """Provision and verify the exact Python tool set for one checkout.

    Returns:
        Platform-native environment layout after successful verification.

    """
    _check_host_python()
    selected_root = root.absolute()
    layout = LAYOUT if selected_root == ROOT else validation_layout(selected_root)
    _provision(layout, root=selected_root)
    _verify(layout)
    return layout


class _NativeExceptionArgsDescriptor(Protocol):
    """View CPython's base exception arguments without subclass dispatch."""

    def __get__(
        self, instance: BaseException, owner: type[BaseException]
    ) -> object: ...


def _native_exception_detail(error: BaseException) -> str:
    """Read a single native string error without invoking host hooks."""
    descriptor = cast(
        "_NativeExceptionArgsDescriptor", cast("object", BaseException.args)
    )
    native_args = descriptor.__get__(error, BaseException)
    if (
        type(native_args) is tuple
        and len(native_args) == 1
        and type(native_args[0]) is str
    ):
        return cast("str", native_args[0])
    return _native_error_name(error)


def main() -> int:
    """Provision and verify the exact repository-local Python tool set.

    Returns:
        Zero after successful provisioning, otherwise one.

    """
    try:
        layout = initialize()
    except (OSError, ProvisionError, subprocess.SubprocessError) as error:
        _ = sys.stderr.write(f"error: {_native_exception_detail(error)}\n")
        return 1
    report_text = f"python validation environment ready: {layout.environment}\n"
    try:
        written = sys.stdout.write(report_text)
        if type(written) is not int or written != len(report_text):
            error_text = "error: incomplete Python bootstrap report output\n"
        else:
            sys.stdout.flush()
            error_text = None
    except (OSError, ValueError, TypeError, RuntimeError):
        error_text = "error: cannot write Python bootstrap report\n"
    if error_text is not None:
        _ = sys.stderr.write(error_text)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
