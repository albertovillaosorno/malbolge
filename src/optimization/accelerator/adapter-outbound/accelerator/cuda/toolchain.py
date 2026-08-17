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
#   - Exact tracked CUDA platform-toolchain selection.
# - Must-Not:
#   - Load native libraries, download packages, or consult ambient CUDA paths.
# - Allows:
#   - Inputs: repository root, normalized platform ID, tracked JSON manifests.
#   - Outputs: immutable loader/library/toolkit selection.
#   - Side effects: tracked manifest reads only.
# - Split-When:
#   - Package provisioning or runtime library loading needs independent policy.
# - Merge-When:
#   - Another adapter module owns the exact same platform-manifest boundary.
# - Summary:
#   - Selects exact Windows or Linux CUDA runtime metadata from tracked files.
# - Description:
#   - Validates manifest containment, loader identity, and platform agreement.
# - Usage:
#   - Consumed by the CUDA runtime before any native library load.
# - Defaults:
#   - Unknown or malformed platform identity fails closed.
#

"""Exact tracked CUDA platform-toolchain selection."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from pathlib import PureWindowsPath
from typing import Final
from typing import Never
from typing import cast

CUDA_TOOLCHAIN_INDEX: Final = (
    Path("src")
    / "optimization"
    / "accelerator"
    / "adapter-outbound"
    / "accelerator"
    / "cuda"
    / "toolchain-manifests.json"
)
_INDEX_SCHEMA_VERSION: Final = 1
_MANIFEST_SCHEMA_VERSION: Final = 1
_ALLOWED_LOADERS: Final = frozenset(("windll", "cdll"))
_PATH_SEPARATORS: Final = frozenset(("/", "\\"))
_PARENT_SEGMENT: Final = ".."


class CudaToolchainSelectionError(RuntimeError):
    """Tracked CUDA platform/toolchain authority is invalid or unavailable."""


@dataclass(frozen=True, slots=True)
class CudaToolchainSelection:
    """Immutable selected CUDA runtime/toolkit identity."""

    platform_id: str
    manifest_path: Path
    toolkit_root: Path
    loader_kind: str
    driver_library: str
    nvrtc_library: Path
    preload_libraries: tuple[Path, ...]


def _fail(detail: str) -> Never:
    raise CudaToolchainSelectionError(detail)


def _reject_duplicate_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            _fail(f"duplicate CUDA toolchain JSON key: {key}")
        document[key] = value
    return document


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    return cast("dict[str, object]", value)


def _read_document(path: Path, label: str) -> dict[str, object]:
    try:
        parsed = cast(
            "object",
            json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_pairs,
            ),
        )
    except (json.JSONDecodeError, OSError) as error:
        _fail(f"cannot read {label}: {error}")
    return _mapping(parsed, label)


def _required_string(
    document: dict[str, object],
    key: str,
    label: str,
) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        _fail(f"{label}.{key} must be a nonempty string")
    return value


def _schema(document: dict[str, object], expected: int, label: str) -> None:
    value = document.get("schema_version")
    if type(value) is not int or value != expected:
        _fail(f"unsupported {label} schema")


def _windows_anchored(value: str) -> bool:
    windows = PureWindowsPath(value)
    return bool(windows.drive or windows.root)


def _local_filename(value: str, label: str) -> str:
    reserved = value in {".", _PARENT_SEGMENT}
    separated = any(separator in value for separator in _PATH_SEPARATORS)
    if reserved or separated or _windows_anchored(value):
        _fail(f"{label} must be one local filename")
    return value


def _repository_relative(value: str, label: str) -> Path:
    native = Path(value)
    windows = PureWindowsPath(value)
    contains_parent = _PARENT_SEGMENT in {*native.parts, *windows.parts}
    if native.is_absolute() or _windows_anchored(value) or contains_parent:
        _fail(f"{label} must stay within the repository")
    return native


def _repository_relative_paths(
    value: object,
    label: str,
) -> tuple[Path, ...]:
    if not isinstance(value, list):
        _fail(f"{label} must be an array")
    result: list[Path] = []
    for index, candidate in enumerate(cast("list[object]", value)):
        if not isinstance(candidate, str) or not candidate:
            _fail(f"{label}[{index}] must be a nonempty string")
        result.append(_repository_relative(candidate, f"{label}[{index}]"))
    return tuple(result)


def _loader_kind(value: str) -> str:
    if value not in _ALLOWED_LOADERS:
        _fail(f"unsupported CUDA loader kind: {value}")
    return value


def _selected_entry(
    root: Path,
    platform_id: str,
) -> tuple[dict[str, object], Path]:
    index_path = root / CUDA_TOOLCHAIN_INDEX
    index = _read_document(index_path, "CUDA toolchain manifest index")
    _schema(index, _INDEX_SCHEMA_VERSION, "CUDA toolchain manifest index")
    platforms = _mapping(index.get("platforms"), "CUDA manifest platforms")
    candidate = platforms.get(platform_id)
    if candidate is None:
        _fail(f"unsupported CUDA platform: {platform_id}")
    return _mapping(candidate, f"CUDA platform {platform_id}"), index_path


def _selected_manifest(
    root: Path,
    platform_id: str,
) -> tuple[dict[str, object], Path, dict[str, object]]:
    entry, index_path = _selected_entry(root, platform_id)
    manifest_name = _local_filename(
        _required_string(entry, "manifest", "CUDA platform"),
        "manifest",
    )
    manifest_path = index_path.parent / manifest_name
    manifest = _read_document(manifest_path, "CUDA platform manifest")
    _schema(manifest, _MANIFEST_SCHEMA_VERSION, "CUDA platform manifest")
    manifest_platform = _required_string(
        manifest,
        "platform",
        "CUDA platform manifest",
    )
    if manifest_platform != platform_id:
        _fail("selected manifest platform mismatch")
    return entry, manifest_path, manifest


def _runtime_selection_fields(
    root: Path,
    entry: dict[str, object],
    manifest: dict[str, object],
) -> tuple[Path, str, str, Path]:
    toolkit_relative = _repository_relative(
        _required_string(
            manifest,
            "toolkit_root",
            "CUDA platform manifest",
        ),
        "CUDA platform manifest.toolkit_root",
    )
    toolkit_root = root / toolkit_relative
    loader_kind = _loader_kind(
        _required_string(entry, "loader", "CUDA platform")
    )
    driver_library = _local_filename(
        _required_string(entry, "driver_library", "CUDA platform"),
        "driver_library",
    )
    nvrtc_relative = _repository_relative(
        _required_string(entry, "nvrtc_library", "CUDA platform"),
        "nvrtc_library",
    )
    return toolkit_root, loader_kind, driver_library, nvrtc_relative


def select_cuda_toolchain(
    root: Path,
    platform_id: str,
) -> CudaToolchainSelection:
    """Select one exact tracked CUDA runtime/toolchain for a normalized host.

    Returns:
        Immutable platform loader, libraries, manifest, and toolkit paths.

    """
    entry, manifest_path, manifest = _selected_manifest(root, platform_id)
    fields = _runtime_selection_fields(root, entry, manifest)
    toolkit_root, loader_kind, driver_library, nvrtc_relative = fields
    preload_relatives = _repository_relative_paths(
        entry.get("preload_libraries"),
        "CUDA platform.preload_libraries",
    )
    return CudaToolchainSelection(
        platform_id=platform_id,
        manifest_path=manifest_path,
        toolkit_root=toolkit_root,
        loader_kind=loader_kind,
        driver_library=driver_library,
        nvrtc_library=toolkit_root / nvrtc_relative,
        preload_libraries=tuple(
            toolkit_root / relative for relative in preload_relatives
        ),
    )
