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
#   - Exact repository-local Linux LLVM development package provisioning.
# - Must-Not:
#   - Install RPMs, use ambient development headers, or provision implicitly.
# - Allows:
#   - Inputs: tracked Linux native-analysis identity and exact Fedora RPM bytes.
#   - Outputs: repository-local development headers and completion marker.
#   - Side effects: explicit Fedora HTTPS reads and repository-local staging.
# - Split-When:
#   - Another development provider needs independent extraction semantics.
# - Merge-When:
#   - LLVM runtime bootstrap owns this exact development-package lifecycle.
# - Summary:
#   - Provision exact Linux LLVM development headers from tracked RPM bytes.
# - Description:
#   - Verify bytes, validate CPIO paths, extract headers, and publish
#     atomically.
# - Usage:
#   - Called only by explicit Linux LLVM development provisioning.
# - Defaults:
#   - No implicit download; partial, drifting, or escaping packages fail closed.
#

"""Provision exact repository-local Linux LLVM development headers."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import urllib.error
import urllib.request
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from stat import S_ISDIR, S_ISREG
from typing import TYPE_CHECKING, Final, Never, cast

from scripts.validate import tidy_toolchain

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import BinaryIO

FEDORA_UPDATES_PACKAGE_BASE: Final = (
    "https://download.fedoraproject.org/pub/fedora/linux/updates/44/"
    "Everything/x86_64/Packages/"
)
LINUX_DEVELOPMENT_PROVIDER: Final = "fedora-rpm-set-v1"
LLVM_DEVELOPMENT_MARKER: Final = ".malbolge-llvm-development-provision-v1.json"
LLVM_DEVELOPMENT_MARKER_SCHEMA: Final = 1
PARENT_SEGMENT: Final = ".."
RPM_SUFFIX: Final = ".rpm"
CPIO_INCLUDE_PATTERN: Final = "./usr/include/*"
MAX_RPM_DOWNLOAD_BYTES: Final = 128 * 1024 * 1024
RPM_TOOL_TIMEOUT_SECONDS: Final = 120


class LlvmDevelopmentProvisionError(RuntimeError):
    """Pinned Linux LLVM development package lifecycle is invalid."""


class _StagingOwnershipChanged(LlvmDevelopmentProvisionError):
    """A foreign staging replacement must never be recursively removed."""


@dataclass(frozen=True, slots=True)
class _ProvisionFunctions:
    download: Callable[[str], bytes] | None
    extract: Callable[..., None]


def _fail(message: str) -> Never:
    raise LlvmDevelopmentProvisionError(message)


def verify_development_asset(
    data: bytes,
    asset: tidy_toolchain.DevelopmentAsset,
) -> None:
    """Reject RPM bytes that drift from exact tracked size or SHA-256."""
    if type(data) is not bytes:
        _fail("LLVM development package requires native bytes")
    if len(data) != asset.size_bytes:
        _fail(
            "".join((
                "LLVM development package size mismatch: expected ",
                f"{asset.size_bytes}; got {len(data)}",
            ))
        )
    observed = hashlib.sha256(data).hexdigest()
    if observed != asset.sha256:
        _fail(
            "".join((
                "LLVM development package SHA-256 mismatch: expected ",
                f"{asset.sha256}; got {observed}",
            ))
        )


def _member_path_escapes(
    posix: PurePosixPath,
    windows: PureWindowsPath,
) -> bool:
    anchored = posix.is_absolute() or bool(windows.drive or windows.root)
    parent = PARENT_SEGMENT in posix.parts or PARENT_SEGMENT in windows.parts
    return anchored or parent


def _safe_member_path(value: str) -> PurePosixPath:
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if _member_path_escapes(posix, windows):
        _fail(f"LLVM RPM member escapes package root: {value}")
    return posix


def validate_rpm_members(members: tuple[str, ...]) -> None:
    """Reject CPIO member names that can escape repository-local staging."""
    if not members:
        _fail("LLVM RPM payload contains no CPIO members")
    for member in members:
        if not member:
            _fail("LLVM RPM payload contains an empty CPIO member")
        _ = _safe_member_path(member)


def _command_bytes(
    arguments: list[str],
    *,
    cwd: Path | None = None,
    stdin: bytes | None = None,
) -> bytes:
    try:
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            arguments.copy(),
            cwd=cwd,
            input=stdin,
            check=False,
            capture_output=True,
            shell=False,
            timeout=RPM_TOOL_TIMEOUT_SECONDS,
        )
    except (OSError, ValueError, TypeError, RuntimeError, sp.SubprocessError) as error:
        # A foreign exception subclass may execute arbitrary formatting hooks.
        detail = (
            str(error)
            if type(error) in (OSError, ValueError, TypeError, RuntimeError)
            else type(error).__name__
        )
        raise LlvmDevelopmentProvisionError(
            f"failed to execute LLVM RPM tool {arguments[0]}: {detail}"
        ) from error
    if (
        type(completed) is not sp.CompletedProcess
        or type(completed.args) is not list
        or len(completed.args) != len(arguments)
        or any(type(argument) is not str for argument in completed.args)
        or completed.args != arguments
        or type(completed.returncode) is not int
        or type(completed.stdout) is not bytes
        or type(completed.stderr) is not bytes
    ):
        _fail(f"invalid LLVM RPM tool process receipt: {arguments[0]}")
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        _fail(f"LLVM RPM tool failed: {arguments[0]}: {detail}")
    return completed.stdout


def _cpio_payload(rpm: Path) -> bytes:
    return _command_bytes(["rpm2cpio", str(rpm)])


def _cpio_members(payload: bytes) -> tuple[str, ...]:
    listing = _command_bytes(["cpio", "-it", "--quiet"], stdin=payload)
    try:
        members = tuple(listing.decode("utf-8").splitlines())
    except UnicodeDecodeError as error:
        _fail(f"LLVM RPM CPIO member names are not UTF-8: {error}")
    validate_rpm_members(members)
    return members


def _reject_include_symlinks(
    include_root: Path, *, require_single_link: bool = False
) -> None:
    """Reject redirected includes and externally writable staged files."""
    _require_physical_directories(include_root, "staging")
    if not _preflight_path_status(include_root, include_root.is_dir, "staging"):
        _fail(f"LLVM RPM include root is not a directory: {include_root}")
    for candidate in include_root.rglob("*"):
        linked = _preflight_path_status(candidate, candidate.is_symlink, "staging")
        junction = _preflight_path_status(candidate, candidate.is_junction, "staging")
        if linked or junction:
            _fail(f"LLVM RPM include tree contains a symlink or junction: {candidate}")
        try:
            physical = candidate.lstat()
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmDevelopmentProvisionError(
                f"LLVM RPM include tree physical member status failed: {candidate}"
            ) from error
        if not (
            _native_regular_status(physical)
            or _native_directory_status(physical)
        ):
            _fail(f"LLVM RPM include tree requires physical member: {candidate}")
        if (
            require_single_link
            and _native_regular_status(physical)
            and physical.st_nlink != 1
        ):
            _fail(f"LLVM staged header has an external hardlink: {candidate}")


def _write_verified_staging_bytes(path: Path, content: bytes) -> None:
    """Create a new physical staging file exclusively and write exact bytes."""
    if type(content) is not bytes:
        _fail(f"LLVM development staging requires native bytes: {path.name}")
    _require_physical_directories(path.parent, "staging")
    linked = _preflight_path_status(path, path.is_symlink, "staging")
    junction = _preflight_path_status(path, path.is_junction, "staging")
    if linked or junction:
        _fail(f"LLVM development staging file must not redirect: {path.name}")
    if _preflight_path_status(path, path.exists, "staging"):
        _fail(f"LLVM development staging file already exists: {path.name}")
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        descriptor = os.open(path, flags, 0o600)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmDevelopmentProvisionError(
            f"LLVM development staging file creation failed: {path.name}"
        ) from error
    if type(descriptor) is not int or descriptor < 0:
        _fail(f"LLVM development staging returned invalid descriptor: {path.name}")
    try:
        try:
            opened = os.fstat(descriptor)
            physical = path.lstat()
            if (
                not _native_regular_status(opened)
                or not _native_regular_status(physical)
                or opened.st_nlink != 1
                or physical.st_nlink != 1
                or opened.st_size != 0
                or physical.st_size != 0
                or (opened.st_dev, opened.st_ino)
                != (physical.st_dev, physical.st_ino)
            ):
                _fail(f"LLVM development staging descriptor mismatch: {path.name}")
            written = os.write(descriptor, content)
        except LlvmDevelopmentProvisionError:
            raise
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmDevelopmentProvisionError(
                f"LLVM development staging file write failed: {path.name}"
            ) from error
        if type(written) is not int or written != len(content):
            _fail(f"LLVM development staging write count mismatch: {path.name}")
        _verify_staging_readback(path, descriptor, content, opened)
    finally:
        try:
            os.close(descriptor)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmDevelopmentProvisionError(
                f"LLVM development staging file close failed: {path.name}"
            ) from error


def _verify_staging_readback(
    path: Path,
    descriptor: int,
    content: bytes,
    opened: os.stat_result,
) -> None:
    """Check staged bytes and ownership through the original write descriptor."""
    try:
        offset = os.lseek(descriptor, 0, os.SEEK_SET)
        if type(offset) is not int or offset != 0:
            _fail(f"LLVM development staging content mismatch: {path.name}")
        for start in range(0, len(content), 1024 * 1024):
            expected = content[start : start + 1024 * 1024]
            observed = os.read(descriptor, len(expected))
            if type(observed) is not bytes or observed != expected:
                _fail(f"LLVM development staging content mismatch: {path.name}")
        tail = os.read(descriptor, 1)
        if type(tail) is not bytes or tail:
            _fail(f"LLVM development staging content mismatch: {path.name}")
        after_opened = os.fstat(descriptor)
        after_physical = path.lstat()
    except LlvmDevelopmentProvisionError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmDevelopmentProvisionError(
            f"LLVM development staging file readback failed: {path.name}"
        ) from error
    if (
        not _native_regular_status(after_opened)
        or not _native_regular_status(after_physical)
        or after_opened.st_nlink != 1
        or after_physical.st_nlink != 1
        or after_opened.st_size != len(content)
        or after_physical.st_size != len(content)
        or (opened.st_dev, opened.st_ino)
        != (after_opened.st_dev, after_opened.st_ino)
        or (opened.st_dev, opened.st_ino)
        != (after_physical.st_dev, after_physical.st_ino)
    ):
        _fail(f"LLVM development staging content mismatch: {path.name}")


def _extract_rpm_headers(
    data: bytes,
    asset: tidy_toolchain.DevelopmentAsset,
    destination: Path,
    *,
    staging: Path,
) -> None:
    verify_development_asset(data, asset)
    _require_physical_directories(staging, "staging")
    package_staging = staging / asset.name.removesuffix(RPM_SUFFIX)
    try:
        package_staging.mkdir(parents=True)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmDevelopmentProvisionError(
            "LLVM development package stage creation failed"
        ) from error
    parent_identity = _staging_directory_identity(staging)
    package_identity = _staging_directory_identity(package_staging)

    def require_owned_package() -> None:
        _assert_owned_staged_child(staging, parent_identity)
        _assert_owned_staged_child(package_staging, package_identity)
        _require_physical_directories(package_staging, "staging")

    require_owned_package()
    try:
        rpm_path = package_staging / asset.name
        _write_verified_staging_bytes(rpm_path, data)
        payload = _cpio_payload(rpm_path)
        require_owned_package()
        _ = _cpio_members(payload)
        require_owned_package()
        _ = _command_bytes(
            [
                "cpio",
                "-idm",
                "--quiet",
                "--no-absolute-filenames",
                CPIO_INCLUDE_PATTERN,
            ],
            cwd=package_staging,
            stdin=payload,
        )
        require_owned_package()
        include_root = package_staging / "usr/include"
        if not _preflight_path_status(include_root, include_root.is_dir, "staging"):
            _fail(f"LLVM development package has no /usr/include: {asset.name}")
        _reject_include_symlinks(include_root)
        _ = shutil.copytree(
            include_root,
            destination / "include",
            dirs_exist_ok=True,
            symlinks=True,
        )
    finally:
        require_owned_package()
    shutil.rmtree(package_staging)


def _asset_url(
    identity: tidy_toolchain.ToolchainIdentity,
    asset: tidy_toolchain.DevelopmentAsset,
) -> str:
    if identity.platform_id != tidy_toolchain.LINUX_PLATFORM:
        _fail("LLVM development RPM provider supports only linux-x86_64")
    if identity.development_provider != LINUX_DEVELOPMENT_PROVIDER:
        _fail("LLVM Linux development provider is not the reviewed Fedora set")
    native = Path(asset.name)
    windows = PureWindowsPath(asset.name)
    if (
        native.name != asset.name
        or bool(windows.drive or windows.root)
        or not asset.name.endswith(RPM_SUFFIX)
    ):
        _fail("LLVM development asset name must be one RPM filename")
    package_bucket = asset.name[0].lower()
    if not package_bucket.isascii() or not package_bucket.isalpha():
        _fail("LLVM development asset name has no Fedora package bucket")
    return FEDORA_UPDATES_PACKAGE_BASE + package_bucket + "/" + asset.name


def _download_asset(url: str, *, expected_size_bytes: int) -> bytes:
    """Bound HTTP response memory to the pinned RPM size plus one byte."""
    if (
        type(expected_size_bytes) is not int
        or not 0 < expected_size_bytes <= MAX_RPM_DOWNLOAD_BYTES
    ):
        _fail("invalid pinned LLVM development package download size")
    request = urllib.request.Request(  # ruff: ignore[suspicious-url-open-usage]
        url,
        headers={"User-Agent": "malbolge-bootstrap/1"},
    )
    try:
        response = cast(
            "BinaryIO",
            urllib.request.urlopen(  # ruff: ignore[suspicious-url-open-usage]
                request,
                timeout=120,
            ),
        )
        with response:
            data = response.read(expected_size_bytes + 1)
    except (OSError, ValueError, TypeError, RuntimeError, urllib.error.URLError) as error:
        detail = (
            str(error)
            if type(error) in (OSError, ValueError, TypeError, RuntimeError)
            else type(error).__name__
        )
        raise LlvmDevelopmentProvisionError(
            f"cannot download pinned LLVM development package: {detail}"
        ) from error
    if type(data) is not bytes:
        _fail("invalid LLVM development package download receipt")
    if len(data) > expected_size_bytes:
        _fail("LLVM development package download exceeds pinned size")
    return data


def _marker_bytes(identity: tidy_toolchain.ToolchainIdentity) -> bytes:
    document = {
        "schema_version": LLVM_DEVELOPMENT_MARKER_SCHEMA,
        "llvm_version": identity.llvm_version,
        "platform": identity.platform_id,
        "provider": identity.development_provider,
        "assets": [
            {
                "name": asset.name,
                "sha256": asset.sha256,
                "size": asset.size_bytes,
            }
            for asset in identity.development_assets
        ],
    }
    rendered = (
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    return rendered.encode("utf-8")


def _native_regular_status(value: object) -> bool:
    """Accept only an exact native regular-file stat with a bounded mode."""
    if type(value) is not os.stat_result:
        return False
    mode = value.st_mode
    return type(mode) is int and 0 <= mode <= 0xFFFF_FFFF and S_ISREG(mode)


def _native_directory_status(value: object) -> bool:
    """Require a native physical directory lstat, never a path predicate alone."""
    if type(value) is not os.stat_result:
        return False
    mode = value.st_mode
    return type(mode) is int and 0 <= mode <= 0xFFFF_FFFF and S_ISDIR(mode)


def _unlinked_component(path: Path) -> bool:
    """Require native symlink and junction decisions for one path component."""
    linked = path.is_symlink()
    junction = path.is_junction()
    return (
        type(linked) is bool
        and type(junction) is bool
        and not linked
        and not junction
    )


def _direct_regular(path: Path) -> bool:
    """Check physical regular-file readiness without following links.

    Returns:
        True only for an unlinked leaf with nonredirecting ancestors.

    """
    try:
        if not _unlinked_component(path):
            return False
        physical = path.lstat()
        return (
            _native_regular_status(physical)
            and physical.st_nlink == 1
            and all(
                _unlinked_component(parent)
                and _native_directory_status(parent.lstat())
                for parent in path.parents
            )
        )
    except (OSError, ValueError, TypeError, RuntimeError):
        return False


def _marker_identity(status: os.stat_result) -> tuple[int, ...]:
    """Capture the exact marker inode and mutation-sensitive metadata.

    Returns:
        Device, inode, link count, size, and modification metadata.

    """
    return (
        status.st_dev,
        status.st_ino,
        status.st_nlink,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _marker_descriptor_matches(
    path: Path,
    identity: tuple[int, ...],
    expected: bytes,
) -> bool:
    """Read only the exact expected marker length from one stable inode.

    Returns:
        True only when the opened descriptor yields unchanged pinned bytes.

    """
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = os.open(path, flags)
    if type(descriptor) is not int or descriptor < 0:
        return False
    try:
        stream = os.fdopen(descriptor, "rb")
    except BaseException:
        with suppress(OSError):
            os.close(descriptor)
        raise
    with stream:
        if type(stream) is not io.BufferedReader:
            return False
        observed_fd = stream.fileno()
        if type(observed_fd) is not int or observed_fd != descriptor:
            return False
        before_stat = os.fstat(observed_fd)
        if not _native_regular_status(before_stat) or before_stat.st_nlink != 1:
            return False
        before = _marker_identity(before_stat)
        contents = stream.read(len(expected) + 1)
        if type(contents) is not bytes:
            return False
        observed_fd = stream.fileno()
        if type(observed_fd) is not int or observed_fd != descriptor:
            return False
        after_stat = os.fstat(observed_fd)
        if not _native_regular_status(after_stat) or after_stat.st_nlink != 1:
            return False
        after = _marker_identity(after_stat)
    return before == identity and after == identity and contents == expected


def _exact_marker_matches(marker: Path, expected: bytes) -> bool:
    """Compare a bounded, nonblocking marker snapshot to pinned identity.

    Returns:
        True only for a stable exact byte match from one physical marker.

    """
    if not _direct_regular(marker):
        return False
    try:
        initial = marker.lstat()
        if not _native_regular_status(initial) or initial.st_nlink != 1:
            return False
        admitted = _marker_identity(initial)
        if (
            initial.st_size != len(expected)
            or not _marker_descriptor_matches(marker, admitted, expected)
            or not _direct_regular(marker)
        ):
            return False
        final = marker.lstat()
        return _native_regular_status(final) and _marker_identity(final) == admitted
    except (OSError, ValueError, TypeError, RuntimeError):
        return False


def development_root_matches(
    identity: tidy_toolchain.ToolchainIdentity,
) -> bool:
    """Check whether local development state matches exact tracked identity.

    Returns:
        True only for the exact marker plus every required development file.

    """
    marker = identity.development_root / LLVM_DEVELOPMENT_MARKER
    if not _exact_marker_matches(marker, _marker_bytes(identity)):
        return False
    return all(
        _direct_regular(identity.development_root / relative)
        for relative in identity.required_development_files
    )


def _preflight_path_status(
    path: Path,
    observation: Callable[[], bool],
    label: str,
) -> bool:
    """Require an exact native path decision before provisioning writes."""
    try:
        observed = observation()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        detail = (
            str(error)
            if type(error) in (OSError, ValueError, TypeError, RuntimeError)
            else type(error).__name__
        )
        raise LlvmDevelopmentProvisionError(
            f"LLVM development {label} path status failed: {path}: {detail}"
        ) from error
    if type(observed) is not bool:
        _fail(f"LLVM development {label} path has invalid status: {path}")
    return observed


def _require_physical_directories(path: Path, label: str) -> None:
    """Admit only native physical directory ancestry before mutations."""
    for component in (path, *path.parents):
        linked = _preflight_path_status(component, component.is_symlink, label)
        junction = _preflight_path_status(component, component.is_junction, label)
        if linked or junction:
            _fail(f"LLVM development {label} path must not redirect: {component}")
        exists = _preflight_path_status(component, component.exists, label)
        if exists and not _preflight_path_status(component, component.is_dir, label):
            _fail(f"LLVM {label} path must be a directory: {component}")
        try:
            physical = component.lstat()
        except FileNotFoundError as error:
            if type(error) is FileNotFoundError and not exists:
                continue
            raise LlvmDevelopmentProvisionError(
                f"LLVM development {label} physical directory status failed: {component}"
            ) from error
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmDevelopmentProvisionError(
                f"LLVM development {label} physical directory status failed: {component}"
            ) from error
        if not exists or not _native_directory_status(physical):
            _fail(f"LLVM development {label} requires physical directory: {component}")


def _require_development_destination(path: Path) -> None:
    """Forbid redirected ancestors or a redirected development root leaf."""
    _require_physical_directories(path.parent, "destination")
    linked = _preflight_path_status(path, path.is_symlink, "destination")
    junction = _preflight_path_status(path, path.is_junction, "destination")
    if linked or junction:
        _fail(f"LLVM development destination must not redirect: {path}")


def _prepare_staging(staging: Path) -> None:
    _require_physical_directories(staging, "staging")
    if _preflight_path_status(staging, staging.exists, "staging"):
        _fail(f"LLVM development staging already exists: {staging}")
    try:
        staging.mkdir(parents=True)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmDevelopmentProvisionError(
            "LLVM development staging creation failed"
        ) from error
    _require_physical_directories(staging, "staging")


def _staging_directory_identity(staging: Path) -> tuple[int, int]:
    """Snapshot the native directory device and inode before cleanup."""
    try:
        physical = staging.lstat()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmDevelopmentProvisionError(
            f"LLVM development staging ownership check failed: {staging}"
        ) from error
    if (
        not _native_directory_status(physical)
        or type(physical.st_dev) is not int
        or type(physical.st_ino) is not int
        or physical.st_dev < 0
        or physical.st_ino < 0
    ):
        _fail(f"LLVM development staging requires native ownership: {staging}")
    return physical.st_dev, physical.st_ino


def _assert_owned_staged_child(
    path: Path,
    original: tuple[int, int],
    *,
    missing_ok: bool = False,
) -> None:
    """Keep a substituted child directory out of publication and cleanup."""
    try:
        physical = path.lstat()
    except FileNotFoundError:
        if missing_ok:
            return
        raise _StagingOwnershipChanged(
            f"LLVM development staging child identity changed: {path}"
        )
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise LlvmDevelopmentProvisionError(
            f"LLVM development staging child identity check failed: {path}"
        ) from error
    if (
        not _native_directory_status(physical)
        or (physical.st_dev, physical.st_ino) != original
    ):
        raise _StagingOwnershipChanged(
            f"LLVM development staging child identity changed: {path}"
        )


def _stage_development_assets(
    identity: tidy_toolchain.ToolchainIdentity,
    staged_root: Path,
    functions: _ProvisionFunctions,
    *,
    package_staging: Path,
) -> None:
    for asset in identity.development_assets:
        _require_physical_directories(package_staging, "staging")
        url = _asset_url(identity, asset)
        data = (
            functions.download(url)
            if functions.download is not None
            else _download_asset(url, expected_size_bytes=asset.size_bytes)
        )
        _require_physical_directories(package_staging, "staging")
        verify_development_asset(data, asset)
        functions.extract(
            data,
            asset,
            staged_root,
            staging=package_staging,
        )
        _require_physical_directories(package_staging, "staging")
        _require_physical_directories(staged_root, "staging")
    _require_physical_directories(staged_root, "staging")
    missing = tuple(
        relative
        for relative in identity.required_development_files
        if not _direct_regular(staged_root / relative)
    )
    if missing:
        joined = ", ".join(path.as_posix() for path in missing)
        _fail(f"LLVM development publication is missing: {joined}")
    _reject_include_symlinks(staged_root / "include", require_single_link=True)


def provision_development_identity(
    root: Path,
    identity: tidy_toolchain.ToolchainIdentity,
    *,
    downloader: Callable[[str], bytes] | None = None,
    extractor: Callable[..., None] | None = None,
) -> Path:
    """Provision one exact Linux LLVM development identity.

    Returns:
        Repository-local development root after atomic publication or reuse.

    """
    if development_root_matches(identity):
        return identity.development_root
    _require_development_destination(identity.development_root)
    if _preflight_path_status(
        identity.development_root,
        identity.development_root.exists,
        "destination",
    ):
        _fail("LLVM development root exists without the exact provision marker")
    staging = (
        root / ".temp" / (f"llvm-development-provision-{identity.platform_id}")
    )
    staged_root = staging / "development"
    _prepare_staging(staging)
    staging_identity = _staging_directory_identity(staging)
    functions = _ProvisionFunctions(
        download=downloader,
        extract=extractor or _extract_rpm_headers,
    )
    child_identity: tuple[int, int] | None = None
    cleanup_permitted = True
    try:
        try:
            staged_root.mkdir()
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmDevelopmentProvisionError(
                "LLVM development stage creation failed"
            ) from error
        child_identity = _staging_directory_identity(staged_root)
        _stage_development_assets(
            identity,
            staged_root,
            functions,
            package_staging=staging / "packages",
        )
        _assert_owned_staged_child(staged_root, child_identity)
        _require_physical_directories(staged_root, "staging")
        _write_verified_staging_bytes(
            staged_root / LLVM_DEVELOPMENT_MARKER, _marker_bytes(identity)
        )
        _require_development_destination(identity.development_root)
        try:
            identity.development_root.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmDevelopmentProvisionError(
                "LLVM development destination parent creation failed"
            ) from error
        _require_development_destination(identity.development_root)
        try:
            _ = identity.development_root.lstat()
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise LlvmDevelopmentProvisionError(
                "LLVM development destination occupancy check failed"
            ) from error
        else:
            _fail("LLVM development destination became occupied before publication")
        _assert_owned_staged_child(staged_root, child_identity)
        _require_physical_directories(staged_root, "staging")
        _reject_include_symlinks(staged_root / "include", require_single_link=True)
        _ = staged_root.replace(identity.development_root)
    except _StagingOwnershipChanged:
        # The package stage can contain an attacker-replaced child. Leave the
        # staging tree intact rather than deleting that foreign directory.
        cleanup_permitted = False
        raise
    finally:
        if cleanup_permitted:
            _require_physical_directories(staging, "staging")
        if cleanup_permitted and _preflight_path_status(
            staging, staging.exists, "staging"
        ):
            if _staging_directory_identity(staging) != staging_identity:
                _fail(f"LLVM development staging ownership changed: {staging}")
            if child_identity is not None:
                _assert_owned_staged_child(
                    staged_root, child_identity, missing_ok=True
                )
            shutil.rmtree(staging)
    return identity.development_root


def linux_development_root(root: Path) -> Path:
    """Resolve the tracked Linux native-analysis development root.

    Returns:
        Repository-local exact Linux development destination.

    """
    identity = tidy_toolchain.load_identity(
        root=root,
        platform_id=tidy_toolchain.LINUX_PLATFORM,
    )
    return identity.development_root


def linux_development_ready(root: Path) -> bool:
    """Check the exact marker and required files for the Linux development kit.

    Returns:
        True only for the exact tracked Linux development identity.

    """
    identity = tidy_toolchain.load_identity(
        root=root,
        platform_id=tidy_toolchain.LINUX_PLATFORM,
    )
    return development_root_matches(identity)


def provision_linux_development(root: Path) -> Path:
    """Provision the tracked Linux x86-64 native-analysis development kit.

    Returns:
        Repository-local exact Linux development root.

    """
    identity = tidy_toolchain.load_identity(
        root=root,
        platform_id=tidy_toolchain.LINUX_PLATFORM,
    )
    return provision_development_identity(root, identity)
