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

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
from pathlib import PureWindowsPath
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from typing import Final
from typing import Never
from typing import TYPE_CHECKING
from typing import cast
import urllib.error
import urllib.request

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


class LlvmDevelopmentProvisionError(RuntimeError):
    """Pinned Linux LLVM development package lifecycle is invalid."""


@dataclass(frozen=True, slots=True)
class _ProvisionFunctions:
    download: Callable[[str], bytes]
    extract: Callable[..., None]


def _fail(message: str) -> Never:
    raise LlvmDevelopmentProvisionError(message)


def verify_development_asset(
    data: bytes,
    asset: tidy_toolchain.DevelopmentAsset,
) -> None:
    """Reject RPM bytes that drift from exact tracked size or SHA-256."""
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
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        arguments,
        cwd=cwd,
        input=stdin,
        check=False,
        capture_output=True,
        shell=False,
    )
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


def _reject_include_symlinks(include_root: Path) -> None:
    for candidate in include_root.rglob("*"):
        if candidate.is_symlink():
            _fail(f"LLVM RPM include tree contains a symlink: {candidate}")


def _extract_rpm_headers(
    data: bytes,
    asset: tidy_toolchain.DevelopmentAsset,
    destination: Path,
    *,
    staging: Path,
) -> None:
    verify_development_asset(data, asset)
    package_staging = staging / asset.name.removesuffix(RPM_SUFFIX)
    package_staging.mkdir(parents=True)
    rpm_path = package_staging / asset.name
    _ = rpm_path.write_bytes(data)
    payload = _cpio_payload(rpm_path)
    _ = _cpio_members(payload)
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
    include_root = package_staging / "usr/include"
    if not include_root.is_dir():
        _fail(f"LLVM development package has no /usr/include: {asset.name}")
    _reject_include_symlinks(include_root)
    _ = shutil.copytree(
        include_root,
        destination / "include",
        dirs_exist_ok=True,
    )
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


def _download_asset(url: str) -> bytes:
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
            return response.read()
    except (OSError, urllib.error.URLError) as error:
        _fail(f"cannot download pinned LLVM development package: {error}")


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
    rendered = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    return rendered.encode("utf-8")


def development_root_matches(
    identity: tidy_toolchain.ToolchainIdentity,
) -> bool:
    """Check whether local development state matches exact tracked identity.

    Returns:
        True only for the exact marker plus every required development file.

    """
    marker = identity.development_root / LLVM_DEVELOPMENT_MARKER
    if not marker.is_file():
        return False
    try:
        marker_matches = marker.read_bytes() == _marker_bytes(identity)
    except OSError:
        return False
    required = all(
        (identity.development_root / relative).is_file()
        for relative in identity.required_development_files
    )
    return marker_matches and required


def _prepare_staging(staging: Path) -> None:
    if staging.exists():
        _fail(f"LLVM development staging already exists: {staging}")
    staging.mkdir(parents=True)


def _stage_development_assets(
    identity: tidy_toolchain.ToolchainIdentity,
    staged_root: Path,
    functions: _ProvisionFunctions,
    *,
    package_staging: Path,
) -> None:
    for asset in identity.development_assets:
        data = functions.download(_asset_url(identity, asset))
        verify_development_asset(data, asset)
        functions.extract(
            data,
            asset,
            staged_root,
            staging=package_staging,
        )
    missing = tuple(
        relative
        for relative in identity.required_development_files
        if not (staged_root / relative).is_file()
    )
    if missing:
        joined = ", ".join(path.as_posix() for path in missing)
        _fail(f"LLVM development publication is missing: {joined}")


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
    if identity.development_root.exists():
        _fail("LLVM development root exists without the exact provision marker")
    staging = root / ".temp" / (
        f"llvm-development-provision-{identity.platform_id}"
    )
    staged_root = staging / "development"
    _prepare_staging(staging)
    staged_root.mkdir()
    functions = _ProvisionFunctions(
        download=downloader or _download_asset,
        extract=extractor or _extract_rpm_headers,
    )
    try:
        _stage_development_assets(
            identity,
            staged_root,
            functions,
            package_staging=staging / "packages",
        )
        _ = (staged_root / LLVM_DEVELOPMENT_MARKER).write_bytes(
            _marker_bytes(identity)
        )
        identity.development_root.parent.mkdir(parents=True, exist_ok=True)
        _ = staged_root.replace(identity.development_root)
    finally:
        if staging.exists():
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
