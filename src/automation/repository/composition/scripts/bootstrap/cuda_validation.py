# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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

from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
from pathlib import PurePosixPath
from pathlib import PureWindowsPath
import shutil
import tarfile
from typing import Final
from typing import Never
from typing import TYPE_CHECKING
from typing import cast
import urllib.error
import urllib.request
import zipfile

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import BinaryIO

NVIDIA_CUDA_REDIST_BASE: Final = (
    "https://developer.download.nvidia.com/compute/cuda/redist/"
)
CUDA_PROVISION_MARKER: Final = ".malbolge-cuda-toolkit-provision-v1.json"
CUDA_PROVISION_SCHEMA_VERSION: Final = 1
CUDA_TOOLCHAIN_SCHEMA_VERSION: Final = 1
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


def _read_document(path: Path, label: str) -> tuple[dict[str, object], bytes]:
    try:
        payload = path.read_bytes()
        parsed = cast(
            "object",
            json.loads(
                payload.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_pairs,
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError, OSError) as error:
        _fail(f"cannot read {label}: {error}")
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
    return CudaPackageArtifact(
        name=name,
        version=version,
        relative_path=relative_path,
        sha256=_sha256(document.get("sha256"), f"{label}.sha256"),
        size=_positive_int(document.get("size"), f"{label}.size"),
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
    if path.is_absolute() or PARENT_SEGMENT in path.parts:
        _fail(f"CUDA archive member escapes package root: {value}")
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
    return root_name, members


def _write_tar_member(
    archive: tarfile.TarFile,
    member: tarfile.TarInfo,
    staging: Path,
) -> None:
    destination = staging.joinpath(*_archive_member_path(member.name).parts)
    if member.isdir():
        destination.mkdir(parents=True, exist_ok=True)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if member.issym():
        target = _archive_member_path(member.linkname)
        destination.symlink_to(target.as_posix())
        return
    if not (member.isreg() or member.islnk()):
        _fail("CUDA archive contains an unsupported member type")
    source = archive.extractfile(member)
    if source is None:
        _fail(f"CUDA archive member is not readable: {member.name}")
    with source:
        _ = destination.write_bytes(source.read())


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
    except (OSError, tarfile.TarError) as error:
        _fail(f"cannot extract CUDA tar archive: {error}")


def _extract_zip_archive(archive: zipfile.ZipFile, staging: Path) -> Path:
    infos = tuple(archive.infolist())
    root_name = _common_archive_root(tuple(info.filename for info in infos))
    for info in infos:
        relative = _archive_member_path(info.filename)
        destination = staging.joinpath(*relative.parts)
        if info.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        _ = destination.write_bytes(archive.read(info))
    extracted = staging / root_name
    if not extracted.is_dir():
        _fail("CUDA archive package root is not a directory")
    return extracted


def _safe_zip_extract(data: bytes, staging: Path) -> Path:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            return _extract_zip_archive(archive, staging)
    except (OSError, zipfile.BadZipFile) as error:
        _fail(f"cannot extract CUDA zip archive: {error}")


def _prepare_staging(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def extract_cuda_package(
    data: bytes,
    package: CudaPackageArtifact,
    destination: Path,
    *,
    staging: Path,
) -> None:
    """Overlay one verified CUDA package into a staged toolkit directory."""
    verify_cuda_package(data, package)
    package_staging = staging / package.name
    _prepare_staging(package_staging)
    if package.relative_path.endswith(".zip"):
        extracted = _safe_zip_extract(data, package_staging)
    else:
        extracted = _safe_tar_extract(data, package_staging)
    destination.mkdir(parents=True, exist_ok=True)
    _ = shutil.copytree(
        extracted, destination, dirs_exist_ok=True, symlinks=True
    )
    shutil.rmtree(package_staging)


def _download_cuda_package(url: str) -> bytes:
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
        _fail(f"cannot download pinned CUDA package: {error}")


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
    if not marker.is_file():
        return False
    try:
        return marker.read_bytes() == _marker_bytes(manifest)
    except OSError:
        return False


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
    if _completed_toolkit_matches(manifest):
        return manifest.toolkit_root
    if manifest.toolkit_root.exists():
        _fail("CUDA toolkit exists without the exact provision marker")
    staging = root / ".temp" / f"cuda-provision-{platform_id}"
    staged_toolkit = staging / "toolkit"
    _prepare_staging(staging)
    download = downloader or _download_cuda_package
    package_staging = staging / "packages"
    try:
        for package in manifest.packages:
            data = download(manifest.base_url + package.relative_path)
            extract_cuda_package(
                data,
                package,
                staged_toolkit,
                staging=package_staging,
            )
        _ = (staged_toolkit / CUDA_PROVISION_MARKER).write_bytes(
            _marker_bytes(manifest)
        )
        manifest.toolkit_root.parent.mkdir(parents=True, exist_ok=True)
        _ = staged_toolkit.replace(manifest.toolkit_root)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return manifest.toolkit_root
