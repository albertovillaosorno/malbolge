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
#   - Exact repository-local CUDA redistributable provisioning.
# - Must-Not:
#   - Use ambient CUDA toolkits, install host drivers, or weaken package
#     identity.
# - Allows:
#   - Inputs: tracked CUDA manifest, explicit platform, official package bytes.
#   - Outputs: verified repository-local toolkit files and exact completion
#     marker.
#   - Side effects: explicit NVIDIA HTTPS reads and repository-local
#     staging/publication only.
# - Split-When:
#   - Driver installation or another package source needs independent policy.
# - Merge-When:
#   - Another bootstrap module owns this exact CUDA redistributable lifecycle.
# - Summary:
#   - Provision exact CUDA packages from tracked NVIDIA package identity.
# - Description:
#   - Verify size/SHA, extract safely, and publish toolkit state atomically.
# - Usage:
#   - Called only by explicit project bootstrap CUDA provisioning.
# - Defaults:
#   - No implicit download; malformed, mismatched, or partial state fails
#     closed.
#

"""Provision exact repository-local CUDA redistributable packages."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import io
import json
import ntpath
import os
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from stat import S_ISDIR, S_ISLNK, S_ISREG
from typing import TYPE_CHECKING, Final, Never, cast

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import IO, BinaryIO

NVIDIA_CUDA_REDIST_BASE: Final = (
    "https://developer.download.nvidia.com/compute/cuda/redist/"
)
CUDA_PROVISION_MARKER: Final = ".malbolge-cuda-toolkit-provision-v1.json"
CUDA_PROVISION_SCHEMA_VERSION: Final = 1
CUDA_TOOLCHAIN_SCHEMA_VERSION: Final = 1
_MAX_MANIFEST_BYTES: Final = 1024 * 1024
_MAX_MARKER_BYTES: Final = 16 * 1024
_MAX_CUDA_DOWNLOAD_BYTES: Final = 512 * 1024 * 1024
_MAX_CUDA_ARCHIVE_MEMBER_BYTES: Final = 512 * 1024 * 1024
_MAX_CUDA_EXTRACTED_BYTES: Final = 1024 * 1024 * 1024
_MAX_CUDA_ARCHIVE_MEMBERS: Final = 100_000
SHA256_HEX_LENGTH: Final = 64
LOWER_HEX_DIGITS: Final = frozenset("0123456789abcdef")
PARENT_SEGMENT: Final = ".."
URL_SUFFIX_MARKERS: Final = frozenset(("?", "#"))
MIN_PACKAGE_PATH_PARTS: Final = 3
_ALLOWED_ARCHIVE_SUFFIXES: Final = (".tar.xz", ".zip")


class CudaProvisionError(RuntimeError):
    """Pinned CUDA package identity or local publication is invalid."""


@dataclass(frozen=True, slots=True)
class CudaPackageArtifact:
    """One exact NVIDIA CUDA redistributable archive identity."""

    name: str
    version: str
    relative_path: str
    sha256: str
    size: int


@dataclass(frozen=True, slots=True)
class CudaProvisionManifest:
    """Exact selected CUDA platform package and destination identity."""

    manifest_path: Path
    manifest_sha256: str
    platform_id: str
    toolkit_root: Path
    packages: tuple[CudaPackageArtifact, ...]
    base_url: str


def _fail(message: str) -> Never:
    raise CudaProvisionError(message)


def _reject_duplicate_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            _fail(f"duplicate CUDA provision JSON key: {key}")
        document[key] = value
    return document


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    return cast("dict[str, object]", value)


def _required_string(
    document: dict[str, object],
    key: str,
    label: str,
) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        _fail(f"{label}.{key} must be a nonempty string")
    return value


def _manifest_identity(status: os.stat_result, label: str) -> tuple[int, ...]:
    """Admit a physical regular file with a stable identity.

    Returns:
        The device, inode, size, and mutation-sensitive timestamps.

    """
    if type(status) is not os.stat_result:
        _fail(f"{label} must provide native file status")
    if not S_ISREG(status.st_mode):
        _fail(f"{label} must be a regular file")
    if status.st_nlink != 1:
        _fail(f"{label} must remain singly linked")
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _check_manifest_parents(path: Path, label: str) -> None:
    """Admit only physically verified authority-file ancestry."""
    _require_physical_directories(path.parent, label.removeprefix("CUDA "))


def _open_owned_manifest_stream(descriptor: int, label: str) -> BinaryIO:
    """Admit only the native binary stream owning the opened file descriptor.

    Returns:
        An authenticated buffered reader over the original descriptor.

    """
    try:
        stream = os.fdopen(descriptor, "rb")
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        with suppress(OSError):
            os.close(descriptor)
        raise CudaProvisionError(
            f"cannot read {label}: host stream wrapper failed"
        ) from error
    if type(stream) is not io.BufferedReader:
        try:
            with stream:
                pass
        except (OSError, ValueError, TypeError, RuntimeError, AttributeError):
            pass
        with suppress(OSError):
            os.close(descriptor)
        _fail(f"{label} requires native buffered stream")
    try:
        stream_fd = stream.fileno()
        raw = stream.raw
        raw_fd = raw.fileno() if type(raw) is io.FileIO else None
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        with suppress(OSError):
            stream.close()
        with suppress(OSError):
            os.close(descriptor)
        raise CudaProvisionError(
            f"{label} requires native stream descriptor"
        ) from error
    if (
        type(stream_fd) is not int
        or stream_fd != descriptor
        or type(raw_fd) is not int
        or raw_fd != descriptor
    ):
        with suppress(OSError):
            stream.close()
        with suppress(OSError):
            os.close(descriptor)
        _fail(f"{label} requires matching native stream descriptor")
    return cast("BinaryIO", stream)


def _read_source_bytes(stream: BinaryIO, limit: int) -> bytes:
    """Read one bounded descriptor-backed CUDA authority snapshot.

    Returns:
        The bytes read from the admitted native stream.

    """
    return stream.read(limit + 1)


def _source_path_status(path: Path, label: str) -> os.stat_result:
    """Return native source-path metadata or a typed host-status failure."""
    try:
        return path.lstat()
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        raise CudaProvisionError(
            f"cannot read {label}: host status failed ({type(error).__name__})"
        ) from error


def _source_descriptor_status(stream: BinaryIO, label: str) -> os.stat_result:
    """Return descriptor metadata without exposing raw host adapter faults."""
    try:
        return os.fstat(stream.fileno())
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        raise CudaProvisionError(
            f"cannot read {label}: host status failed ({type(error).__name__})"
        ) from error


def _read_manifest_source(
    path: Path,
    label: str,
    *,
    max_bytes: int = _MAX_MANIFEST_BYTES,
) -> bytes:
    """Read exact bounded bytes from one stable physical authority file.

    Returns:
        Bytes whose named inode and timestamps are unchanged after read.

    """
    _check_manifest_parents(path, label)
    admitted = _source_path_status(path, label)
    expected = _manifest_identity(admitted, label)
    if admitted.st_size > max_bytes:
        _fail(f"{label} exceeds byte limit")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        raise CudaProvisionError(
            f"cannot read {label}: host open failed ({type(error).__name__})"
        ) from error
    if type(descriptor) is not int or descriptor < 0:
        _fail(f"{label} must open a native descriptor")
    with _open_owned_manifest_stream(descriptor, label) as stream:
        if (
            _manifest_identity(_source_descriptor_status(stream, label), label)
            != expected
        ):
            _fail(f"{label} changed before read")
        try:
            payload = _read_source_bytes(stream, max_bytes)
        except (OSError, TypeError, ValueError, RuntimeError) as error:
            raise CudaProvisionError(
                f"cannot read {label}: host read failed ({type(error).__name__})"
            ) from error
        if type(payload) is not bytes:
            _fail(f"{label} must return native bytes")
        if len(payload) != admitted.st_size:
            _fail(f"{label} changed during read or exceeds byte limit")
        if (
            _manifest_identity(_source_descriptor_status(stream, label), label)
            != expected
            or _manifest_identity(_source_path_status(path, label), label)
            != expected
        ):
            _fail(f"{label} changed during read")
        _check_manifest_parents(path, label)
        return payload


def _read_document(path: Path, label: str) -> tuple[dict[str, object], bytes]:
    payload = _read_manifest_source(path, label)
    try:
        parsed = cast(
            "object",
            json.loads(
                payload.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_pairs,
            ),
        )
    except CudaProvisionError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, OSError, TypeError, ValueError, RuntimeError) as error:
        raise CudaProvisionError(
            f"cannot read {label}: {type(error).__name__}"
        ) from error
    return _mapping(parsed, label), payload


def _windows_anchored(value: str) -> bool:
    windows = PureWindowsPath(value)
    return bool(windows.drive or windows.root)


def _contains_parent(*parts: tuple[str, ...]) -> bool:
    return PARENT_SEGMENT in {item for group in parts for item in group}


def _repository_relative_path(value: str, label: str) -> Path:
    native = Path(value)
    windows = PureWindowsPath(value)
    contains_parent = _contains_parent(native.parts, windows.parts)
    if native.is_absolute() or _windows_anchored(value) or contains_parent:
        _fail(f"{label} must stay within the repository")
    if "\\" in value:
        _fail(f"{label} must use forward slashes")
    if ntpath.isreserved(value):
        _fail(f"{label} contains a Windows-reserved path component")
    return native


def _archive_relative_path(
    value: str,
    package_name: str,
    platform_id: str,
) -> str:
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    anchored = posix.is_absolute() or _windows_anchored(value)
    contains_parent = _contains_parent(posix.parts, windows.parts)
    if anchored or contains_parent:
        _fail("CUDA package relative_path must stay below the NVIDIA root")
    if "\\" in value:
        _fail("CUDA package relative_path must use forward slashes")
    if ntpath.isreserved(value):
        _fail("CUDA package relative_path contains a Windows-reserved path component")
    if any(marker in value for marker in URL_SUFFIX_MARKERS):
        _fail("CUDA package relative_path cannot contain URL suffix authority")
    package_prefix = (package_name, platform_id)
    if (
        len(posix.parts) < MIN_PACKAGE_PATH_PARTS
        or posix.parts[:2] != package_prefix
    ):
        _fail("CUDA package relative_path must bind package and platform")
    if not value.endswith(_ALLOWED_ARCHIVE_SUFFIXES):
        _fail("CUDA package relative_path uses an unsupported archive format")
    return value


def _sha256(value: object, label: str) -> str:
    if not isinstance(value, str):
        _fail(f"{label} must be lowercase SHA-256")
    if len(value) != SHA256_HEX_LENGTH or any(
        character not in LOWER_HEX_DIGITS for character in value
    ):
        _fail(f"{label} must be lowercase SHA-256")
    return value


def _positive_int(value: object, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be a positive exact integer")
    return value


def _package_artifact(
    value: object,
    platform_id: str,
    index: int,
) -> CudaPackageArtifact:
    label = f"CUDA manifest.packages[{index}]"
    document = _mapping(value, label)
    name = _required_string(document, "name", label)
    version = _required_string(document, "version", label)
    relative_path = _archive_relative_path(
        _required_string(document, "relative_path", label),
        name,
        platform_id,
    )
    size = _positive_int(document.get("size"), f"{label}.size")
    if size > _MAX_CUDA_DOWNLOAD_BYTES:
        _fail(f"{label}.size exceeds CUDA package byte limit")
    return CudaPackageArtifact(
        name=name,
        version=version,
        relative_path=relative_path,
        sha256=_sha256(document.get("sha256"), f"{label}.sha256"),
        size=size,
    )


def _packages(
    document: dict[str, object],
    platform_id: str,
) -> tuple[CudaPackageArtifact, ...]:
    value = document.get("packages")
    if not isinstance(value, list) or not value:
        _fail("CUDA manifest.packages must be a nonempty array")
    raw = cast("list[object]", value)
    packages = tuple(
        _package_artifact(candidate, platform_id, index)
        for index, candidate in enumerate(raw)
    )
    names = tuple(package.name for package in packages)
    if len(set(names)) != len(names):
        _fail("CUDA manifest package names must be unique")
    return packages


def load_cuda_provision_manifest(
    root: Path,
    manifest_path: Path,
    platform_id: str,
) -> CudaProvisionManifest:
    """Load one exact platform CUDA provisioning authority.

    Returns:
        Validated platform package identities and repository-local toolkit root.

    """
    document, payload = _read_document(manifest_path, "CUDA provision manifest")
    schema = document.get("schema_version")
    if type(schema) is not int or schema != CUDA_TOOLCHAIN_SCHEMA_VERSION:
        _fail("unsupported CUDA provision manifest schema")
    manifest_platform = _required_string(document, "platform", "CUDA manifest")
    if manifest_platform != platform_id:
        _fail("CUDA provision manifest platform mismatch")
    base_url = _required_string(document, "redistrib_base_url", "CUDA manifest")
    if base_url != NVIDIA_CUDA_REDIST_BASE:
        _fail("CUDA manifest redistrib_base_url must use the NVIDIA authority")
    toolkit_relative = _repository_relative_path(
        _required_string(document, "toolkit_root", "CUDA manifest"),
        "CUDA manifest.toolkit_root",
    )
    return CudaProvisionManifest(
        manifest_path=manifest_path,
        manifest_sha256=hashlib.sha256(payload).hexdigest(),
        platform_id=platform_id,
        toolkit_root=root / toolkit_relative,
        packages=_packages(document, platform_id),
        base_url=base_url,
    )


def verify_cuda_package(data: bytes, package: CudaPackageArtifact) -> None:
    """Reject package bytes that drift from tracked size or SHA-256 identity."""
    if type(data) is not bytes:
        _fail("CUDA package must be native bytes")
    if len(data) != package.size:
        _fail(
            "".join((
                "CUDA package size mismatch: ",
                f"expected {package.size}; got {len(data)}",
            ))
        )
    observed = hashlib.sha256(data).hexdigest()
    if observed != package.sha256:
        _fail(
            "".join((
                "CUDA package SHA-256 mismatch: ",
                f"expected {package.sha256}; got {observed}",
            ))
        )


def _archive_member_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    windows = PureWindowsPath(value)
    anchored = path.is_absolute() or bool(windows.drive or windows.root)
    if anchored or PARENT_SEGMENT in path.parts:
        _fail(f"CUDA archive member escapes package root: {value}")
    if "\\" in value:
        _fail("CUDA archive member must use forward slashes")
    if ntpath.isreserved(value):
        _fail("CUDA archive member contains a Windows-reserved path component")
    if not path.parts:
        _fail("CUDA archive member path is empty")
    return path


def _common_archive_root(names: tuple[str, ...]) -> str:
    paths = tuple(_archive_member_path(name) for name in names if name)
    if not paths:
        _fail("CUDA archive contains no members")
    roots = {path.parts[0] for path in paths}
    if len(roots) != 1:
        _fail("CUDA archive must contain one package root")
    return roots.pop()


def _validate_cuda_archive_expansion(sizes: tuple[int, ...]) -> None:
    """Bound archive-member count and expanded bytes before any file extraction."""
    if len(sizes) > _MAX_CUDA_ARCHIVE_MEMBERS:
        _fail("CUDA archive member count exceeds limit")
    total = 0
    for size in sizes:
        if type(size) is not int or size < 0 or size > _MAX_CUDA_ARCHIVE_MEMBER_BYTES:
            _fail("CUDA archive member byte limit exceeded")
        total += size
        if total > _MAX_CUDA_EXTRACTED_BYTES:
            _fail("CUDA archive expanded byte limit exceeded")


def _read_bounded_archive_member(stream: IO[bytes], size: int) -> bytes:
    """Reject a decoded member larger than its declared, bounded byte count."""
    try:
        data = stream.read(size + 1)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise CudaProvisionError("CUDA archive member read failed") from error
    if type(data) is not bytes or len(data) != size:
        _fail("CUDA archive member length mismatch")
    return data


def _tar_payload_size(archive: tarfile.TarFile, member: tarfile.TarInfo) -> int:
    """Resolve hard-link chains to the real contained file's declared size."""
    current = member
    seen: set[str] = set()
    while current.islnk():
        if current.name in seen:
            _fail("CUDA archive contains a cyclic hard link")
        seen.add(current.name)
        try:
            current = archive.getmember(current.linkname)
        except KeyError as error:
            raise CudaProvisionError("CUDA archive hard link target missing") from error
    if current.isreg():
        return current.size
    if member.islnk():
        _fail("CUDA archive hard link does not target a regular member")
    return 0


def _tar_members(
    archive: tarfile.TarFile,
) -> tuple[str, tuple[tarfile.TarInfo, ...]]:
    members = tuple(archive.getmembers())
    names = tuple(member.name for member in members)
    root_name = _common_archive_root(names)
    for member in members:
        _ = _archive_member_path(member.name)
        if member.isdev() or member.isfifo():
            _fail("CUDA archive contains an unsupported special member")
        if member.islnk():
            target = _archive_member_path(member.linkname)
            if target.parts[0] != root_name:
                _fail("CUDA archive hard link outside package root")
    _validate_cuda_archive_expansion(
        tuple(_tar_payload_size(archive, member) for member in members)
    )
    return root_name, members


def _write_verified_bytes(path: Path, payload: bytes) -> None:
    """Create one exclusive, descriptor-verified archive member."""
    _write_staged_file_exclusively(path, payload, "CUDA staging payload")


def _write_tar_member(
    archive: tarfile.TarFile,
    member: tarfile.TarInfo,
    staging: Path,
) -> None:
    destination = staging.joinpath(*_archive_member_path(member.name).parts)
    if member.isdir():
        _ensure_toolkit_destination_parent(destination)
        return
    _ensure_toolkit_destination_parent(destination.parent)
    if member.issym():
        target = _archive_member_path(member.linkname).as_posix()
        if os.name != "posix":
            try:
                destination.symlink_to(target)
                status = destination.lstat()
                observed = os.readlink(destination)
            except (OSError, TypeError, ValueError, RuntimeError) as error:
                raise CudaProvisionError("CUDA archive symlink status failed") from error
        else:
            parent_descriptor = _open_staging_parent(destination.parent)
            if parent_descriptor is None:
                _fail("CUDA archive symlink requires native parent descriptor")
            try:
                _ = _require_staging_parent_unchanged(
                    destination.parent, parent_descriptor
                )
                try:
                    os.symlink(target, destination.name, dir_fd=parent_descriptor)
                    _ = _require_staging_parent_unchanged(
                        destination.parent, parent_descriptor
                    )
                    status = os.stat(
                        destination.name, dir_fd=parent_descriptor,
                        follow_symlinks=False,
                    )
                    named = destination.lstat()
                    observed = os.readlink(destination.name, dir_fd=parent_descriptor)
                except CudaProvisionError:
                    raise
                except (OSError, TypeError, ValueError, RuntimeError) as error:
                    raise CudaProvisionError("CUDA archive symlink status failed") from error
                if (
                    type(named) is not os.stat_result
                    or type(status) is not os.stat_result
                    or (status.st_dev, status.st_ino) != (named.st_dev, named.st_ino)
                ):
                    _fail("CUDA archive symlink parent receipt mismatch")
                _ = _require_staging_parent_unchanged(
                    destination.parent, parent_descriptor
                )
            finally:
                try:
                    os.close(parent_descriptor)
                except (OSError, TypeError, ValueError, RuntimeError) as error:
                    raise CudaProvisionError("CUDA archive symlink parent close failed") from error
        if (
            type(status) is not os.stat_result
            or not S_ISLNK(status.st_mode)
            or status.st_nlink != 1
            or type(observed) is not str
            or observed != target
        ):
            _fail("CUDA archive symlink changed during staging")
        return
    if not (member.isreg() or member.islnk()):
        _fail("CUDA archive contains an unsupported member type")
    source = archive.extractfile(member)
    if source is None:
        _fail(f"CUDA archive member is not readable: {member.name}")
    with source:
        _write_verified_bytes(
            destination,
            _read_bounded_archive_member(source, _tar_payload_size(archive, member)),
        )


def _extract_tar_archive(archive: tarfile.TarFile, staging: Path) -> Path:
    root_name, members = _tar_members(archive)
    for member in members:
        _write_tar_member(archive, member, staging)
    extracted = staging / root_name
    if not extracted.is_dir():
        _fail("CUDA archive package root is not a directory")
    return extracted


def _safe_tar_extract(data: bytes, staging: Path) -> Path:
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as archive:
            return _extract_tar_archive(archive, staging)
    except CudaProvisionError:
        raise
    except KeyError as error:
        raise CudaProvisionError("cannot resolve CUDA tar archive hard link") from error
    except (OSError, tarfile.TarError, TypeError, ValueError, RuntimeError) as error:
        raise CudaProvisionError(
            f"cannot extract CUDA tar archive: {type(error).__name__}"
        ) from error


def _extract_zip_archive(archive: zipfile.ZipFile, staging: Path) -> Path:
    infos = tuple(archive.infolist())
    _validate_cuda_archive_expansion(
        tuple(info.file_size if not info.is_dir() else 0 for info in infos)
    )
    root_name = _common_archive_root(tuple(info.filename for info in infos))
    for info in infos:
        relative = _archive_member_path(info.filename)
        destination = staging.joinpath(*relative.parts)
        if info.is_dir():
            _ensure_toolkit_destination_parent(destination)
            continue
        _ensure_toolkit_destination_parent(destination.parent)
        with archive.open(info) as source:
            _write_verified_bytes(
                destination, _read_bounded_archive_member(source, info.file_size)
            )
    extracted = staging / root_name
    if not extracted.is_dir():
        _fail("CUDA archive package root is not a directory")
    return extracted


def _safe_zip_extract(data: bytes, staging: Path) -> Path:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return _extract_zip_archive(archive, staging)
    except CudaProvisionError:
        raise
    except (OSError, zipfile.BadZipFile, TypeError, ValueError, RuntimeError) as error:
        raise CudaProvisionError(
            f"cannot extract CUDA zip archive: {type(error).__name__}"
        ) from error


def _require_physical_directories(path: Path, label: str) -> None:
    """Require native physical directory metadata for every existing ancestor."""
    for component in (path, *path.parents):
        try:
            status = component.lstat()
        except FileNotFoundError:
            continue
        except (OSError, TypeError, ValueError, RuntimeError) as error:
            raise CudaProvisionError(
                f"CUDA {label} path status failed: {type(error).__name__}"
            ) from error
        if type(status) is not os.stat_result:
            _fail(f"CUDA {label} path requires native status: {component}")
        try:
            junction = component.is_junction()
        except (OSError, TypeError, ValueError, RuntimeError) as error:
            raise CudaProvisionError(
                f"CUDA {label} junction status failed: {type(error).__name__}"
            ) from error
        if type(junction) is not bool:
            _fail(f"CUDA {label} path requires native junction status: {component}")
        if S_ISLNK(status.st_mode) or junction:
            _fail(f"CUDA {label} path must not redirect: {component}")
        if not S_ISDIR(status.st_mode):
            _fail(f"CUDA {label} path must be a directory: {component}")


def _require_toolkit_destination(path: Path) -> None:
    _require_physical_directories(path, "toolkit destination")


def _require_unoccupied_toolkit_destination(path: Path) -> None:
    """Reject a newly occupied destination, including empty directories."""
    _require_toolkit_destination(path.parent)
    try:
        _ = path.lstat()
    except FileNotFoundError:
        return
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        raise CudaProvisionError(
            "CUDA toolkit destination status failed"
        ) from error
    _fail("CUDA toolkit destination already occupied")


def _prepare_staging(path: Path) -> None:
    """Create an exclusive stage without redirectable parent-path writes."""
    _require_physical_directories(path, "staging")
    if os.name != "posix":
        try:
            path.mkdir(parents=True)
        except (OSError, TypeError, ValueError, RuntimeError) as error:
            raise CudaProvisionError(
                "CUDA staging directory creation failed"
            ) from error
        _require_physical_directories(path, "staging")
        return

    missing: list[Path] = []
    component = path
    while True:
        try:
            status = component.lstat()
        except FileNotFoundError:
            missing.append(component)
            component = component.parent
        except (OSError, TypeError, ValueError, RuntimeError) as error:
            raise CudaProvisionError("CUDA staging directory status failed") from error
        else:
            if component == path:
                _fail("CUDA staging directory already occupied")
            if type(status) is not os.stat_result or not S_ISDIR(status.st_mode):
                _fail("CUDA staging ancestor requires native directory status")
            break

    for directory in reversed(missing):
        _require_physical_directories(directory.parent, "staging")
        parent_descriptor = _open_staging_parent(directory.parent)
        if parent_descriptor is None:
            _fail("CUDA staging creation requires a physical parent descriptor")
        try:
            try:
                os.mkdir(directory.name, dir_fd=parent_descriptor)
            except (OSError, TypeError, ValueError, RuntimeError) as error:
                raise CudaProvisionError(
                    "CUDA staging directory creation failed"
                ) from error
            _require_staging_parent_unchanged(directory.parent, parent_descriptor)
            _require_physical_directories(directory, "staging")
            try:
                created = os.stat(
                    directory.name, dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                named = directory.lstat()
            except (OSError, TypeError, ValueError, RuntimeError) as error:
                raise CudaProvisionError(
                    "CUDA staging directory receipt failed"
                ) from error
            if (
                type(created) is not os.stat_result
                or type(named) is not os.stat_result
                or not S_ISDIR(created.st_mode)
                or (created.st_dev, created.st_ino)
                != (named.st_dev, named.st_ino)
            ):
                _fail("CUDA staging directory creation receipt mismatch")
        finally:
            try:
                os.close(parent_descriptor)
            except (OSError, TypeError, ValueError, RuntimeError) as error:
                raise CudaProvisionError("CUDA staging parent close failed") from error
    _require_physical_directories(path, "staging")


def _owned_staging_identity(path: Path) -> tuple[int, int]:
    """Admit the native inode of the provision-owned staging root."""
    _require_physical_directories(path, "staging")
    try:
        status = path.lstat()
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        raise CudaProvisionError("CUDA staging directory status failed") from error
    if type(status) is not os.stat_result or not S_ISDIR(status.st_mode):
        _fail("CUDA staging directory requires native directory status")
    return status.st_dev, status.st_ino


def _require_owned_staging(path: Path, identity: tuple[int, int]) -> None:
    """Reject a staging root replaced after this provisioning run created it."""
    if _owned_staging_identity(path) != identity:
        _fail("CUDA staging directory changed during provisioning")


def _cleanup_owned_staging(path: Path, identity: tuple[int, int]) -> None:
    """Reject an exchanged root and type failures from safe recursive cleanup."""
    _require_owned_staging(path, identity)
    try:
        shutil.rmtree(path)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise CudaProvisionError("CUDA owned staging cleanup failed") from error
    try:
        _ = path.lstat()
    except FileNotFoundError:
        return
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise CudaProvisionError("CUDA owned staging cleanup receipt failed") from error
    _fail("CUDA owned staging cleanup did not remove the named directory")


def _read_cuda_overlay_file(
    parent_descriptor: int,
    name: str,
    *,
    max_bytes: int = _MAX_CUDA_DOWNLOAD_BYTES,
    expected_inode: tuple[int, int] | None = None,
) -> bytes:
    """Read an overlay member through its admitted source/destination directory."""
    label = "CUDA staged overlay member"
    try:
        named = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        expected = _manifest_identity(named, label)
        if expected_inode is not None and (named.st_dev, named.st_ino) != expected_inode:
            _fail("CUDA staged overlay member source changed before read")
        if named.st_size > max_bytes:
            _fail(f"{label} exceeds byte limit")
        flags = (
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(name, flags, dir_fd=parent_descriptor)
    except CudaProvisionError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise CudaProvisionError("CUDA staged overlay member open failed") from error
    if type(descriptor) is not int or descriptor < 0:
        _fail("CUDA staged overlay member requires native descriptor")
    with _open_owned_manifest_stream(descriptor, label) as stream:
        if (
            _manifest_identity(_source_descriptor_status(stream, label), label)
            != expected
        ):
            _fail("CUDA staged overlay member changed before read")
        try:
            content = _read_source_bytes(stream, max_bytes)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise CudaProvisionError(
                "CUDA staged overlay member read failed"
            ) from error
        if type(content) is not bytes or len(content) != named.st_size:
            _fail("CUDA staged overlay member changed during read")
        try:
            after = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise CudaProvisionError(
                "CUDA staged overlay member status failed"
            ) from error
        if (
            _manifest_identity(after, label) != expected
            or _manifest_identity(_source_descriptor_status(stream, label), label)
            != expected
        ):
            _fail("CUDA staged overlay member changed during read")
        return content


def _copy_cuda_overlay(
    source: Path, destination: Path, source_identity: tuple[int, int]
) -> None:
    """Copy verified archive members through pinned POSIX source and target directories."""
    if os.name != "posix":
        _ = shutil.copytree(source, destination, dirs_exist_ok=True, symlinks=True)
        return

    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)

    def copy_directory(
        src: Path, dst: Path, src_descriptor: int, dst_descriptor: int
    ) -> None:
        _ = _require_staging_parent_unchanged(src, src_descriptor)
        try:
            members = tuple(src.iterdir())
        except (OSError, TypeError, ValueError, RuntimeError) as error:
            raise CudaProvisionError("CUDA staged overlay traversal failed") from error
        # Path iteration may run through an exchanged physical directory.
        # Its names are safe only if the pinned source is still named here.
        _ = _require_staging_parent_unchanged(src, src_descriptor)
        for member in members:
            target = dst / member.name
            try:
                status = os.stat(
                    member.name, dir_fd=src_descriptor, follow_symlinks=False
                )
                named = member.lstat()
            except (OSError, TypeError, ValueError, RuntimeError) as error:
                raise CudaProvisionError(
                    "CUDA staged overlay member status failed"
                ) from error
            if (
                type(status) is not os.stat_result
                or type(named) is not os.stat_result
                or (status.st_dev, status.st_ino) != (named.st_dev, named.st_ino)
            ):
                _fail("CUDA staged overlay member source identity mismatch")
            _ = _require_staging_parent_unchanged(src, src_descriptor)
            if S_ISDIR(status.st_mode):
                try:
                    src_child = os.open(member.name, flags, dir_fd=src_descriptor)
                except (OSError, TypeError, ValueError, RuntimeError) as error:
                    raise CudaProvisionError(
                        "CUDA staged overlay source directory open failed"
                    ) from error
                if type(src_child) is not int or src_child < 0:
                    _fail(
                        "CUDA staged overlay source directory requires native descriptor"
                    )
                try:
                    opened_source = os.fstat(src_child)
                    if (
                        type(opened_source) is not os.stat_result
                        or not S_ISDIR(opened_source.st_mode)
                        or (opened_source.st_dev, opened_source.st_ino)
                        != (status.st_dev, status.st_ino)
                    ):
                        _fail("CUDA staged overlay source directory receipt mismatch")
                    _ = _require_staging_parent_unchanged(member, src_child)
                    try:
                        os.mkdir(member.name, dir_fd=dst_descriptor)
                    except FileExistsError:
                        pass
                    except (OSError, TypeError, ValueError, RuntimeError) as error:
                        raise CudaProvisionError(
                            "CUDA staged overlay directory creation failed"
                        ) from error
                    try:
                        child = os.open(member.name, flags, dir_fd=dst_descriptor)
                    except (OSError, TypeError, ValueError, RuntimeError) as error:
                        raise CudaProvisionError(
                            "CUDA staged overlay directory open failed"
                        ) from error
                    if type(child) is not int or child < 0:
                        _fail(
                            "CUDA staged overlay directory requires native descriptor"
                        )
                    try:
                        opened = os.fstat(child)
                        named = os.stat(
                            member.name, dir_fd=dst_descriptor, follow_symlinks=False
                        )
                        if (
                            type(opened) is not os.stat_result
                            or type(named) is not os.stat_result
                            or not S_ISDIR(opened.st_mode)
                            or (opened.st_dev, opened.st_ino)
                            != (named.st_dev, named.st_ino)
                        ):
                            _fail("CUDA staged overlay directory receipt mismatch")
                        copy_directory(member, target, src_child, child)
                        observed = os.stat(
                            member.name, dir_fd=dst_descriptor, follow_symlinks=False
                        )
                        if type(observed) is not os.stat_result or (
                            observed.st_dev,
                            observed.st_ino,
                        ) != (opened.st_dev, opened.st_ino):
                            _fail("CUDA staged overlay directory changed during copy")
                    except CudaProvisionError:
                        raise
                    except (OSError, TypeError, ValueError, RuntimeError) as error:
                        raise CudaProvisionError(
                            "CUDA staged overlay directory receipt failed"
                        ) from error
                    finally:
                        try:
                            os.close(child)
                        except (OSError, TypeError, ValueError, RuntimeError) as error:
                            raise CudaProvisionError(
                                "CUDA staged overlay descriptor close failed"
                            ) from error
                finally:
                    try:
                        os.close(src_child)
                    except (OSError, TypeError, ValueError, RuntimeError) as error:
                        raise CudaProvisionError(
                            "CUDA staged overlay source descriptor close failed"
                        ) from error
            elif S_ISLNK(status.st_mode):
                try:
                    link_target = os.readlink(member.name, dir_fd=src_descriptor)
                    if type(link_target) is not str:
                        _fail("CUDA staged overlay symlink must have native target")
                    _ = _archive_member_path(link_target)
                    source_link = os.stat(
                        member.name, dir_fd=src_descriptor, follow_symlinks=False
                    )
                    if (
                        type(source_link) is not os.stat_result
                        or not S_ISLNK(source_link.st_mode)
                        or (source_link.st_dev, source_link.st_ino)
                        != (status.st_dev, status.st_ino)
                    ):
                        _fail("CUDA staged overlay source symlink changed")
                    _ = _require_staging_parent_unchanged(src, src_descriptor)
                    os.symlink(link_target, member.name, dir_fd=dst_descriptor)
                    observed = os.stat(
                        member.name, dir_fd=dst_descriptor, follow_symlinks=False
                    )
                    recorded = os.readlink(member.name, dir_fd=dst_descriptor)
                except CudaProvisionError:
                    raise
                except (OSError, TypeError, ValueError, RuntimeError) as error:
                    raise CudaProvisionError(
                        "CUDA staged overlay symlink creation failed"
                    ) from error
                if (
                    type(observed) is not os.stat_result
                    or not S_ISLNK(observed.st_mode)
                    or type(recorded) is not str
                    or recorded != link_target
                ):
                    _fail("CUDA staged overlay symlink receipt mismatch")
            elif S_ISREG(status.st_mode):
                content = _read_cuda_overlay_file(
                    src_descriptor, member.name,
                    expected_inode=(status.st_dev, status.st_ino),
                )
                _ = _require_staging_parent_unchanged(src, src_descriptor)
                try:
                    existing = os.stat(
                        member.name, dir_fd=dst_descriptor, follow_symlinks=False
                    )
                except FileNotFoundError:
                    _ = _write_staged_file_at_parent(
                        target, content, "CUDA staged overlay member", dst_descriptor
                    )
                except (OSError, TypeError, ValueError, RuntimeError) as error:
                    raise CudaProvisionError(
                        "CUDA staged overlay file status failed"
                    ) from error
                else:
                    if (
                        type(existing) is not os.stat_result
                        or not S_ISREG(existing.st_mode)
                        or existing.st_nlink != 1
                        or _read_cuda_overlay_file(dst_descriptor, member.name)
                        != content
                    ):
                        _fail("CUDA staged overlay member collision")
            else:
                _fail("CUDA staged overlay has unsupported member type")
            _ = _require_staging_parent_unchanged(src, src_descriptor)
            _ = _require_staging_parent_unchanged(dst, dst_descriptor)
        _ = _require_staging_parent_unchanged(src, src_descriptor)
        _ = _require_staging_parent_unchanged(dst, dst_descriptor)

    source_descriptor = _open_staging_parent(source)
    if source_descriptor is None:
        _fail("CUDA staged overlay requires native source descriptor")
    try:
        if (
            _require_staging_parent_unchanged(source, source_descriptor)
            != source_identity
        ):
            _fail("CUDA staged overlay source changed before copy")
        descriptor = _open_staging_parent(destination)
        if descriptor is None:
            _fail("CUDA staged overlay requires native destination descriptor")
        try:
            copy_directory(source, destination, source_descriptor, descriptor)
        finally:
            try:
                os.close(descriptor)
            except (OSError, TypeError, ValueError, RuntimeError) as error:
                raise CudaProvisionError(
                    "CUDA staged overlay descriptor close failed"
                ) from error
    finally:
        try:
            os.close(source_descriptor)
        except (OSError, TypeError, ValueError, RuntimeError) as error:
            raise CudaProvisionError(
                "CUDA staged overlay source descriptor close failed"
            ) from error


def extract_cuda_package(
    data: bytes,
    package: CudaPackageArtifact,
    destination: Path,
    *,
    staging: Path,
) -> None:
    """Overlay one verified CUDA package into a staged toolkit directory."""
    verify_cuda_package(data, package)
    _require_toolkit_destination(destination)
    package_staging = staging / package.name
    _prepare_staging(package_staging)
    package_staging_identity = _owned_staging_identity(package_staging)
    if package.relative_path.endswith(".zip"):
        extracted = _safe_zip_extract(data, package_staging)
    else:
        extracted = _safe_tar_extract(data, package_staging)
    extracted_identity = _owned_staging_identity(extracted)
    _require_toolkit_destination(destination)
    _ensure_toolkit_destination_parent(destination)
    _require_toolkit_destination(destination)
    _copy_cuda_overlay(extracted, destination, extracted_identity)
    _cleanup_owned_staging(package_staging, package_staging_identity)


def _download_cuda_package(
    url: str, *, max_bytes: int = _MAX_CUDA_DOWNLOAD_BYTES
) -> bytes:
    if type(max_bytes) is not int or not 0 < max_bytes <= _MAX_CUDA_DOWNLOAD_BYTES:
        _fail("CUDA network package exceeds pinned byte limit")
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
            data = response.read(max_bytes + 1)
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        raise CudaProvisionError(
            f"cannot download pinned CUDA package: {type(error).__name__}"
        ) from error
    if type(data) is not bytes:
        _fail("CUDA network response must contain native bytes")
    if len(data) > max_bytes:
        _fail("CUDA network response exceeds pinned byte limit")
    return data


def _marker_bytes(manifest: CudaProvisionManifest) -> bytes:
    document = {
        "schema_version": CUDA_PROVISION_SCHEMA_VERSION,
        "manifest_sha256": manifest.manifest_sha256,
        "platform": manifest.platform_id,
        "packages": [
            {
                "name": package.name,
                "sha256": package.sha256,
                "size": package.size,
                "version": package.version,
            }
            for package in manifest.packages
        ],
    }
    rendered = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    return rendered.encode("utf-8")


def _completed_toolkit_matches(manifest: CudaProvisionManifest) -> bool:
    marker = manifest.toolkit_root / CUDA_PROVISION_MARKER
    try:
        observed = _read_manifest_source(
            marker, "CUDA provision marker", max_bytes=_MAX_MARKER_BYTES
        )
    except (OSError, CudaProvisionError):
        return False
    return observed == _marker_bytes(manifest)


def _require_new_completion_marker(path: Path) -> None:
    """Keep the provision marker independent from archive-owned file entries."""
    _require_physical_directories(path.parent, "completion marker")
    try:
        _ = path.lstat()
    except FileNotFoundError:
        return
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        raise CudaProvisionError(
            "cannot inspect CUDA completion marker"
        ) from error
    _fail(f"CUDA completion marker already supplied by a package: {path}")


def _completion_marker_identity(path: Path) -> tuple[int, ...]:
    """Admit an unshared physical completion marker, never an outside alias."""
    try:
        status = path.lstat()
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        raise CudaProvisionError("CUDA completion marker status failed") from error
    identity = _manifest_identity(status, "CUDA completion marker")
    if status.st_nlink != 1:
        _fail("CUDA completion marker must remain singly linked")
    return identity


def _require_staging_parent_unchanged(
    path: Path, descriptor: int
) -> tuple[int, int]:
    """Recheck the pinned directory and return its native inode identity."""
    _require_physical_directories(path, "staging")
    try:
        opened = os.fstat(descriptor)
        named = path.lstat()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise CudaProvisionError("CUDA staging parent status failed") from error
    if (
        type(opened) is not os.stat_result
        or type(named) is not os.stat_result
        or not S_ISDIR(opened.st_mode)
        or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
    ):
        _fail("CUDA staging parent descriptor mismatch")
    return opened.st_dev, opened.st_ino


def _open_staging_parent(path: Path) -> int | None:
    """Pin the admitted staging directory for descriptor-relative writes."""
    if os.name != "posix":
        return None
    try:
        before = path.lstat()
        if type(before) is not os.stat_result or not S_ISDIR(before.st_mode):
            _fail("CUDA staging parent requires native directory status")
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
    except CudaProvisionError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise CudaProvisionError("CUDA staging parent open failed") from error
    if type(descriptor) is not int or descriptor < 0:
        _fail("CUDA staging parent requires native descriptor")
    accepted = False
    try:
        if (before.st_dev, before.st_ino) != _require_staging_parent_unchanged(
            path, descriptor
        ):
            _fail("CUDA staging parent changed during open")
        accepted = True
    except CudaProvisionError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise CudaProvisionError("CUDA staging parent status failed") from error
    finally:
        if not accepted:
            try:
                os.close(descriptor)
            except (OSError, ValueError, TypeError, RuntimeError) as error:
                raise CudaProvisionError("CUDA staging parent close failed") from error
    return descriptor


def _ensure_toolkit_destination_parent(path: Path) -> None:
    """Create absent toolkit ancestors through pinned physical parent handles."""
    _require_toolkit_destination(path)
    if os.name != "posix":
        try:
            path.mkdir(parents=True, exist_ok=True)
        except (OSError, TypeError, ValueError, RuntimeError) as error:
            raise CudaProvisionError(
                "CUDA toolkit destination parent creation failed"
            ) from error
        _require_toolkit_destination(path)
        return

    missing: list[Path] = []
    component = path
    while True:
        try:
            status = component.lstat()
        except FileNotFoundError:
            missing.append(component)
            component = component.parent
        except (OSError, TypeError, ValueError, RuntimeError) as error:
            raise CudaProvisionError(
                "CUDA toolkit destination parent status failed"
            ) from error
        else:
            if type(status) is not os.stat_result or not S_ISDIR(status.st_mode):
                _fail("CUDA toolkit destination parent requires native directory")
            anchored_identity = (status.st_dev, status.st_ino)
            break

    for directory in reversed(missing):
        parent = directory.parent
        _require_toolkit_destination(parent)
        try:
            descriptor = _open_staging_parent(parent)
        except CudaProvisionError as error:
            raise CudaProvisionError(
                "CUDA toolkit destination parent open failed"
            ) from error
        if descriptor is None:
            _fail("CUDA toolkit destination parent requires native descriptor")
        try:
            try:
                admitted = _require_staging_parent_unchanged(parent, descriptor)
            except CudaProvisionError as error:
                raise CudaProvisionError(
                    "CUDA toolkit destination parent changed before creation"
                ) from error
            if admitted != anchored_identity:
                _fail("CUDA toolkit destination parent changed before creation")
            try:
                os.mkdir(directory.name, dir_fd=descriptor)
            except (OSError, TypeError, ValueError, RuntimeError) as error:
                raise CudaProvisionError(
                    "CUDA toolkit destination parent creation failed"
                ) from error
            try:
                _require_staging_parent_unchanged(parent, descriptor)
                _require_toolkit_destination(directory)
                created = os.stat(
                    directory.name, dir_fd=descriptor, follow_symlinks=False
                )
                named = directory.lstat()
            except CudaProvisionError as error:
                raise CudaProvisionError(
                    "CUDA toolkit destination parent changed during creation"
                ) from error
            except (OSError, TypeError, ValueError, RuntimeError) as error:
                raise CudaProvisionError(
                    "CUDA toolkit destination parent receipt failed"
                ) from error
            if (
                type(created) is not os.stat_result
                or type(named) is not os.stat_result
                or not S_ISDIR(created.st_mode)
                or (created.st_dev, created.st_ino) != (named.st_dev, named.st_ino)
            ):
                _fail("CUDA toolkit destination parent creation receipt mismatch")
            anchored_identity = (created.st_dev, created.st_ino)
        finally:
            try:
                os.close(descriptor)
            except (OSError, TypeError, ValueError, RuntimeError) as error:
                raise CudaProvisionError(
                    "CUDA toolkit destination parent close failed"
                ) from error
    _require_toolkit_destination(path)


def _write_staged_file_exclusively(
    path: Path, payload: bytes, label: str
) -> tuple[int, int]:
    """Create an owned staged file and return its native inode identity."""
    _require_physical_directories(path.parent, "staging")
    parent_descriptor = _open_staging_parent(path.parent)
    try:
        return _write_staged_file_at_parent(path, payload, label, parent_descriptor)
    finally:
        if parent_descriptor is not None:
            try:
                os.close(parent_descriptor)
            except (OSError, ValueError, TypeError, RuntimeError) as error:
                raise CudaProvisionError("CUDA staging parent close failed") from error


def _write_staged_file_at_parent(
    path: Path, payload: bytes, label: str, parent_descriptor: int | None
) -> tuple[int, int]:
    """Write through the pinned staging parent, if supported by the host."""
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        if parent_descriptor is None:
            descriptor = os.open(path, flags, 0o600)
        else:
            descriptor = os.open(path.name, flags, 0o600, dir_fd=parent_descriptor)
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        raise CudaProvisionError(f"cannot create exclusive {label}") from error
    if type(descriptor) is not int or descriptor < 0:
        _fail(f"{label} requires native descriptor")
    identity: tuple[int, int] | None = None
    completed = False
    try:
        if parent_descriptor is not None:
            _require_staging_parent_unchanged(path.parent, parent_descriptor)
        admitted = path.lstat()
        receipt = os.fstat(descriptor)
        if (
            _manifest_identity(admitted, label)
            != _manifest_identity(receipt, label)
            or admitted.st_nlink != 1
            or admitted.st_size != 0
        ):
            _fail(f"{label} requires owned empty regular file")
        identity = (admitted.st_dev, admitted.st_ino)
        try:
            written = os.write(descriptor, payload)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise CudaProvisionError(f"cannot write {label}") from error
        if type(written) is not int or written != len(payload):
            _fail(f"CUDA staging write count mismatch: {path.name}")
        after_fd = os.fstat(descriptor)
        after_path = path.lstat()
        if (
            _manifest_identity(after_fd, label)
            != _manifest_identity(after_path, label)
            or (after_fd.st_dev, after_fd.st_ino) != identity
            or after_fd.st_nlink != 1
            or after_fd.st_size != len(payload)
        ):
            _fail(f"{label} changed during write")
        if parent_descriptor is not None:
            _require_staging_parent_unchanged(path.parent, parent_descriptor)
        if _read_manifest_source(path, label, max_bytes=len(payload)) != payload:
            _fail(f"CUDA staging content mismatch: {path.name}")
        completed = True
    finally:
        with suppress(OSError):
            os.close(descriptor)
        if not completed and identity is not None:
            with suppress(OSError):
                if parent_descriptor is None:
                    observed = path.lstat()
                else:
                    observed = os.stat(
                        path.name, dir_fd=parent_descriptor, follow_symlinks=False
                    )
                if (
                    type(observed) is os.stat_result
                    and S_ISREG(observed.st_mode)
                    and (observed.st_dev, observed.st_ino) == identity
                    and observed.st_nlink == 1
                ):
                    if parent_descriptor is None:
                        path.unlink()
                    else:
                        os.unlink(path.name, dir_fd=parent_descriptor)
    if identity is None:
        _fail(f"{label} lacks owned staging identity")
    return identity


def _rename_cuda_toolkit_no_replace(
    source: str, destination: str, *, src_dir_fd: int, dst_dir_fd: int
) -> None:
    """Atomically publish a Linux toolkit without overwriting a late occupant."""
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = libc.renameat2
    except (OSError, ValueError, TypeError, RuntimeError, AttributeError) as error:
        raise CudaProvisionError(
            "CUDA toolkit publication requires native Linux no-replace rename"
        ) from error
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = cast(
        "object",
        renameat2(
            src_dir_fd,
            os.fsencode(source),
            dst_dir_fd,
            os.fsencode(destination),
            1,  # Linux RENAME_NOREPLACE
        ),
    )
    if type(result) is not int:
        _fail("CUDA toolkit publication rename requires native receipt")
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number == errno.EEXIST:
            _fail("CUDA toolkit destination became occupied during publication")
        raise OSError(error_number, "CUDA toolkit no-replace rename failed")


def _publish_cuda_toolkit(staged: Path, destination: Path) -> None:
    """Pin a POSIX destination directory across the final toolkit rename.

    Raises:
        CudaProvisionError: If the destination identity changes or publication fails.

    """
    parent = destination.parent
    _require_physical_directories(parent, "toolkit destination")
    _require_unoccupied_toolkit_destination(destination)
    if os.name != "posix":
        _ = staged.replace(destination)
        return
    staged_identity = _owned_staging_identity(staged)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(parent, flags)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise CudaProvisionError(
            f"CUDA toolkit destination parent open failed: {type(error).__name__}"
        ) from error
    if type(descriptor) is not int or descriptor < 0:
        _fail("CUDA toolkit destination parent requires native descriptor")
    try:
        opened = os.fstat(descriptor)
        named = parent.lstat()
        if (
            type(opened) is not os.stat_result
            or type(named) is not os.stat_result
            or not S_ISDIR(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("CUDA toolkit destination parent descriptor mismatch")
        _require_physical_directories(parent, "toolkit destination")
        try:
            _ = os.stat(destination.name, dir_fd=descriptor, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            _fail("CUDA toolkit destination became occupied before publication")
        source_parent = _open_staging_parent(staged.parent)
        if source_parent is None:
            _fail("CUDA toolkit staging source requires native parent")
        try:
            source_status = os.stat(
                staged.name, dir_fd=source_parent, follow_symlinks=False
            )
            if (
                type(source_status) is not os.stat_result
                or not S_ISDIR(source_status.st_mode)
                or (source_status.st_dev, source_status.st_ino) != staged_identity
            ):
                _fail("CUDA toolkit staging source changed before publication")
            if sys.platform != "linux":
                _ = os.replace(
                    staged.name, destination.name,
                    src_dir_fd=source_parent, dst_dir_fd=descriptor,
                )
            else:
                _rename_cuda_toolkit_no_replace(
                    staged.name,
                    destination.name,
                    src_dir_fd=source_parent,
                    dst_dir_fd=descriptor,
                )
            _ = _require_staging_parent_unchanged(staged.parent, source_parent)
        finally:
            try:
                os.close(source_parent)
            except (OSError, ValueError, TypeError, RuntimeError) as error:
                raise CudaProvisionError(
                    "CUDA toolkit staging source parent close failed"
                ) from error
        received = os.stat(destination.name, dir_fd=descriptor, follow_symlinks=False)
        if (
            type(received) is not os.stat_result
            or not S_ISDIR(received.st_mode)
            or (received.st_dev, received.st_ino) != staged_identity
        ):
            _fail("CUDA toolkit destination publication receipt mismatch")
        _require_physical_directories(parent, "toolkit destination")
        named = parent.lstat()
        if type(named) is not os.stat_result or (opened.st_dev, opened.st_ino) != (
            named.st_dev,
            named.st_ino,
        ):
            _fail("CUDA toolkit destination parent changed during publication")
    except CudaProvisionError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise CudaProvisionError(
            f"CUDA toolkit destination publication failed: {type(error).__name__}"
        ) from error
    finally:
        try:
            os.close(descriptor)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise CudaProvisionError(
                "CUDA toolkit destination parent close failed"
            ) from error


def provision_cuda_manifest(
    root: Path,
    manifest_path: Path,
    platform_id: str,
    *,
    downloader: Callable[[str], bytes] | None = None,
) -> Path:
    """Provision one selected CUDA toolkit only from exact tracked packages.

    Returns:
        Repository-local toolkit root after exact publication or reuse.

    """
    manifest = load_cuda_provision_manifest(root, manifest_path, platform_id)
    # The final marker shape is fully determined by the admitted manifest.
    # Reject impossible publication before staging or expensive package reads.
    marker_content = _marker_bytes(manifest)
    if len(marker_content) > _MAX_MARKER_BYTES:
        _fail("CUDA completion marker exceeds byte limit")
    if _completed_toolkit_matches(manifest):
        return manifest.toolkit_root
    if manifest.toolkit_root.exists():
        _fail("CUDA toolkit exists without the exact provision marker")
    _require_toolkit_destination(manifest.toolkit_root)
    staging = root / ".temp" / f"cuda-provision-{platform_id}"
    staged_toolkit = staging / "toolkit"
    _prepare_staging(staging)
    staging_identity = _owned_staging_identity(staging)
    package_staging = staging / "packages"
    try:
        for package in manifest.packages:
            _require_owned_staging(staging, staging_identity)
            url = manifest.base_url + package.relative_path
            data = (
                _download_cuda_package(url, max_bytes=package.size)
                if downloader is None
                else downloader(url)
            )
            extract_cuda_package(
                data,
                package,
                staged_toolkit,
                staging=package_staging,
            )
        _require_owned_staging(staging, staging_identity)
        toolkit_identity = _owned_staging_identity(staged_toolkit)
        marker = staged_toolkit / CUDA_PROVISION_MARKER
        _require_new_completion_marker(marker)
        marker_written_identity = _write_staged_file_exclusively(
            marker, marker_content, "CUDA completion marker"
        )
        if (
            type(marker_written_identity) is not tuple
            or len(marker_written_identity) != 2
            or any(type(value) is not int for value in marker_written_identity)
        ):
            _fail("CUDA completion marker requires native write receipt")
        _require_owned_staging(staging, staging_identity)
        _require_owned_staging(staged_toolkit, toolkit_identity)
        marker_identity = _completion_marker_identity(marker)
        if marker_identity[:2] != marker_written_identity:
            _fail("CUDA completion marker changed inode after staging write")
        if (
            _read_manifest_source(
                marker, "CUDA completion marker", max_bytes=_MAX_MARKER_BYTES
            )
            != marker_content
            or _completion_marker_identity(marker) != marker_identity
        ):
            _fail("CUDA completion marker changed before publication")
        _require_toolkit_destination(manifest.toolkit_root)
        _ensure_toolkit_destination_parent(manifest.toolkit_root.parent)
        _require_toolkit_destination(manifest.toolkit_root)
        _publish_cuda_toolkit(staged_toolkit, manifest.toolkit_root)
    finally:
        _cleanup_owned_staging(staging, staging_identity)
    return manifest.toolkit_root
