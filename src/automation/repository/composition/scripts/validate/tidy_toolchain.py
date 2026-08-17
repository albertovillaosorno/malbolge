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
#   - Exact local LLVM development identity used by native-analysis tooling.
# - Must-Not:
#   - Download toolchains or infer plugin ABI compatibility from host LLVM.
# - Allows:
#   - Inputs: tracked manifest and repository-local LLVM installation roots.
#   - Outputs: validated immutable toolchain identity and readiness evidence.
#   - Side effects: optional executable version probes and archive hashing.
# - Split-When:
#   - Split when another LLVM platform gains an independent artifact lifecycle.
# - Merge-When:
#   - Merge when project bootstrap owns identical native-toolchain validation.
# - Summary:
#   - Validate the pinned clang-tidy development toolchain.
# - Description:
#   - Binds plugin development to reviewed LLVM 22.1.8 platform artifacts.
# - Usage:
#   - Run as `python -m scripts.validate.tidy_toolchain` from the repository.
# - Defaults:
#   - Missing, drifted, or malformed toolchain evidence fails closed.
#

"""Validate the exact LLVM development kit used by Malbolge clang-tidy."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from pathlib import PureWindowsPath
import platform
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Final
from typing import Never
from typing import cast

if __package__ in {None, ""}:
    composition_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(composition_root))

from scripts.repository_root import repository_root

ROOT: Final = repository_root(Path(__file__))
MANIFEST: Final = (
    ROOT
    / "src"
    / "tooling"
    / "native-analysis"
    / "contract"
    / "llvm-clang-tidy-toolchain.json"
)
SCHEMA_VERSION: Final = 2
LLVM_VERSION: Final = "22.1.8"
RELEASE_TAG: Final = f"llvmorg-{LLVM_VERSION}"
WINDOWS_SYSTEM: Final = "windows"
LINUX_SYSTEM: Final = "linux"
WINDOWS_PLATFORM: Final = "windows-x86_64"
LINUX_PLATFORM: Final = "linux-x86_64"
PARENT_SEGMENT: Final = ".."
WINDOWS_PLUGIN_STRATEGY: Final = "project-host-registry-bridge-v1"
LINUX_PLUGIN_STRATEGY: Final = "upstream-host-loadable-module-v1"
REGISTRY_BRIDGE_EXPORT: Final = "malbolge_tidy_register_node"
PLUGIN_CHECKS: Final = (
    "malbolge-abi-bit-field",
    "malbolge-abi-packed-layout",
    "malbolge-abi-pragma-pack",
    "malbolge-abi-over-alignment",
    "malbolge-abi-type-surface",
)
SHA256_HEX_LENGTH: Final = 64
LOWER_HEX: Final = frozenset("0123456789abcdef")
TOP_LEVEL_KEYS: Final = frozenset(
    {
        "schema_version",
        "llvm_version",
        "release_tag",
        "runtime_root",
        "development_root",
        "plugin_output_root",
        "plugin_checks",
        "platforms",
    }
)
PLATFORM_KEYS: Final = frozenset(
    {
        "development_provider",
        "development_assets",
        "required_runtime_files",
        "required_development_files",
        "plugin_strategy",
        "registry_bridge_export",
        "clang",
        "clang_cl",
        "clang_tidy",
        "llvm_readobj",
        "plugin_host_root",
        "plugin_host",
        "plugin_library",
    }
)
ASSET_KEYS: Final = frozenset({"name", "size_bytes", "sha256"})
PLUGIN_HOST_RUNTIME: Final = "runtime"
PLUGIN_HOST_OUTPUT: Final = "output"
PLUGIN_HOST_ROOTS: Final = frozenset({PLUGIN_HOST_RUNTIME, PLUGIN_HOST_OUTPUT})


class ToolchainError(RuntimeError):
    """Tracked LLVM development identity is malformed or unavailable."""


@dataclass(frozen=True, slots=True)
class DevelopmentAsset:
    """One exact immutable development-package byte identity."""

    name: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ToolchainIdentity:
    """Validated immutable LLVM/clang-tidy development identity."""

    asset_name: str
    asset_sha256: str
    asset_size_bytes: int
    development_assets: tuple[DevelopmentAsset, ...]
    development_provider: str
    development_root: Path
    llvm_version: str
    platform_id: str
    plugin_checks: tuple[str, ...]
    plugin_host_path: Path
    plugin_library_path: Path
    plugin_output_root: Path
    plugin_strategy: str
    registry_bridge_export: str | None
    release_tag: str
    required_development_files: tuple[Path, ...]
    required_runtime_files: tuple[Path, ...]
    runtime_clang: Path
    runtime_clang_cl: Path
    runtime_clang_tidy: Path
    runtime_llvm_readobj: Path | None
    runtime_root: Path

    @property
    def windows_plugin_strategy(self) -> str:
        """Legacy Windows strategy accessor retained for existing callers."""
        return self.plugin_strategy

    @property
    def clang(self) -> Path:
        """Pinned platform Clang frontend executable."""
        return self.runtime_clang

    @property
    def clang_cl(self) -> Path:
        """Pinned compiler executable used by the platform build."""
        return self.runtime_clang_cl

    @property
    def clang_tidy(self) -> Path:
        """Upstream pinned clang-tidy executable."""
        return self.runtime_clang_tidy

    @property
    def plugin_host(self) -> Path:
        """Canonical clang-tidy process used to load the project plugin."""
        return self.plugin_host_path

    @property
    def plugin_library(self) -> Path:
        """Canonical Malbolge clang-tidy plugin path."""
        return self.plugin_library_path

    @property
    def llvm_readobj(self) -> Path:
        """Pinned COFF inspection executable for the Windows plugin strategy."""
        if self.runtime_llvm_readobj is None:
            _fail("LLVM readobj is unavailable for this platform")
        return self.runtime_llvm_readobj


def _fail(message: str) -> Never:
    raise ToolchainError(message)


def _reject_duplicate_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            _fail(f"duplicate clang-tidy toolchain JSON key: {key}")
        document[key] = value
    return document


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    return cast("dict[str, object]", value)


def _document(path: Path) -> dict[str, object]:
    try:
        parsed = cast(
            "object",
            json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_pairs,
            ),
        )
    except (json.JSONDecodeError, OSError) as error:
        _fail(f"cannot read clang-tidy toolchain manifest: {error}")
    return _mapping(parsed, "clang-tidy toolchain manifest")


def _exact_keys(
    document: dict[str, object],
    expected: frozenset[str],
    label: str,
) -> None:
    observed = frozenset(document)
    if observed == expected:
        return
    missing = sorted(expected - observed)
    unknown = sorted(observed - expected)
    detail: list[str] = []
    if missing:
        detail.append("missing " + ", ".join(missing))
    if unknown:
        detail.append("unknown " + ", ".join(unknown))
    _fail(f"{label} keys are not closed: {'; '.join(detail)}")


def _string(document: dict[str, object], key: str, label: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        _fail(f"{label}.{key} must be a nonempty string")
    return value


def _optional_string(
    document: dict[str, object],
    key: str,
    label: str,
) -> str | None:
    value = document.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        _fail(f"{label}.{key} must be null or a nonempty string")
    return value


def _positive_int(document: dict[str, object], key: str, label: str) -> int:
    value = document.get(key)
    if type(value) is not int or value <= 0:
        _fail(f"{label}.{key} must be a positive integer")
    return value


def _repository_path(value: str, label: str) -> Path:
    native = Path(value)
    windows = PureWindowsPath(value)
    native_escape = native.is_absolute() or PARENT_SEGMENT in native.parts
    windows_escape = bool(
        windows.drive or windows.root or PARENT_SEGMENT in windows.parts
    )
    if native_escape or windows_escape:
        _fail(f"{label} must stay within the repository")
    return native


def _string_list(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        _fail(f"{label} must be a nonempty list")
    items = cast("list[object]", value)
    if not all(isinstance(item, str) and item for item in items):
        _fail(f"{label} entries must be nonempty strings")
    result = tuple(cast("list[str]", items))
    if len(set(result)) != len(result):
        _fail(f"{label} must not contain duplicates")
    return result


def _relative_files(value: object, label: str) -> tuple[Path, ...]:
    return tuple(
        _repository_path(item, f"{label}[{index}]")
        for index, item in enumerate(_string_list(value, label))
    )


def _sha256(value: object, label: str) -> str:
    digest = "".join(_string_list(value, f"{label}.sha256"))
    if len(digest) != SHA256_HEX_LENGTH or any(
        character not in LOWER_HEX for character in digest
    ):
        _fail(f"{label}.sha256 must be lowercase SHA-256")
    return digest


def host_platform_id(
    *,
    system: str | None = None,
    machine: str | None = None,
) -> str:
    """Normalize the host identity used by this toolchain contract.

    Returns:
        Stable host platform identifier for manifest comparison.

    """
    observed_system = (system or platform.system()).strip().lower()
    observed_machine = (machine or platform.machine()).strip().lower()
    is_x86_64 = observed_machine in {"amd64", "x86_64"}
    if is_x86_64 and observed_system == WINDOWS_SYSTEM:
        return WINDOWS_PLATFORM
    if is_x86_64 and observed_system == LINUX_SYSTEM:
        return LINUX_PLATFORM
    return f"{observed_system or 'unknown'}-{observed_machine or 'unknown'}"


def _review_common_contract(document: dict[str, object]) -> None:
    if document.get("schema_version") != SCHEMA_VERSION:
        _fail("unsupported clang-tidy toolchain manifest schema")
    expected = (
        (
            "llvm_version",
            _string(document, "llvm_version", "toolchain"),
            LLVM_VERSION,
        ),
        (
            "release_tag",
            _string(document, "release_tag", "toolchain"),
            RELEASE_TAG,
        ),
    )
    for label, observed, required in expected:
        if observed != required:
            _fail(f"toolchain {label} must be {required}")
    checks = _string_list(document.get("plugin_checks"), "plugin_checks")
    if checks != PLUGIN_CHECKS:
        _fail("toolchain plugin_checks must match the reviewed v1 plugin set")


def _manifest_root(
    document: dict[str, object],
    key: str,
    root: Path,
) -> Path:
    relative = _repository_path(
        _string(document, key, "toolchain"),
        f"toolchain.{key}",
    )
    return root / relative


def _development_assets(value: object) -> tuple[DevelopmentAsset, ...]:
    if not isinstance(value, list) or not value:
        _fail("development_assets must be a nonempty list")
    assets: list[DevelopmentAsset] = []
    for index, item in enumerate(cast("list[object]", value)):
        label = f"development_assets[{index}]"
        asset = _mapping(item, label)
        _exact_keys(asset, ASSET_KEYS, label)
        assets.append(
            DevelopmentAsset(
                name=_string(asset, "name", label),
                sha256=_sha256(asset.get("sha256"), label),
                size_bytes=_positive_int(asset, "size_bytes", label),
            )
        )
    names = tuple(asset.name for asset in assets)
    if len(set(names)) != len(names):
        _fail("development_assets names must be unique")
    return tuple(assets)


def _selected_platform(
    document: dict[str, object],
    platform_id: str,
) -> dict[str, object]:
    platforms = _mapping(document.get("platforms"), "toolchain.platforms")
    entry = platforms.get(platform_id)
    if entry is None:
        _fail(f"unsupported clang-tidy toolchain platform: {platform_id}")
    selected = _mapping(entry, f"toolchain.platforms.{platform_id}")
    _exact_keys(selected, PLATFORM_KEYS, f"platform {platform_id}")
    return selected


def _runtime_path(
    entry: dict[str, object],
    key: str,
    runtime_root: Path,
) -> Path:
    relative = _repository_path(
        _string(entry, key, "platform"),
        f"platform.{key}",
    )
    return runtime_root / relative


def _optional_runtime_path(
    entry: dict[str, object],
    key: str,
    runtime_root: Path,
) -> Path | None:
    value = _optional_string(entry, key, "platform")
    if value is None:
        return None
    return runtime_root / _repository_path(value, f"platform.{key}")


def _plugin_host_path(
    entry: dict[str, object],
    runtime_root: Path,
    output_root: Path,
) -> Path:
    root_kind = _string(entry, "plugin_host_root", "platform")
    if root_kind not in PLUGIN_HOST_ROOTS:
        _fail("platform.plugin_host_root must be runtime or output")
    base = runtime_root if root_kind == PLUGIN_HOST_RUNTIME else output_root
    relative = _repository_path(
        _string(entry, "plugin_host", "platform"),
        "platform.plugin_host",
    )
    return base / relative


def load_identity(
    manifest: Path = MANIFEST,
    *,
    root: Path = ROOT,
    platform_id: str = WINDOWS_PLATFORM,
) -> ToolchainIdentity:
    """Load one close-validated clang-tidy platform identity.

    Returns:
        Immutable normalized identity rooted below ``root``.

    """
    document = _document(manifest)
    _exact_keys(document, TOP_LEVEL_KEYS, "clang-tidy toolchain manifest")
    _review_common_contract(document)
    entry = _selected_platform(document, platform_id)
    runtime_root = _manifest_root(document, "runtime_root", root)
    output_root = _manifest_root(document, "plugin_output_root", root)
    assets = _development_assets(entry.get("development_assets"))
    strategy = _string(entry, "plugin_strategy", "platform")
    if platform_id == WINDOWS_PLATFORM and strategy != WINDOWS_PLUGIN_STRATEGY:
        _fail(f"toolchain Windows strategy must be {WINDOWS_PLUGIN_STRATEGY}")
    if platform_id == LINUX_PLATFORM and strategy != LINUX_PLUGIN_STRATEGY:
        _fail(f"toolchain Linux strategy must be {LINUX_PLUGIN_STRATEGY}")
    bridge = _optional_string(entry, "registry_bridge_export", "platform")
    if platform_id == WINDOWS_PLATFORM and bridge != REGISTRY_BRIDGE_EXPORT:
        _fail(f"toolchain registry bridge must be {REGISTRY_BRIDGE_EXPORT}")
    if platform_id == LINUX_PLATFORM and bridge is not None:
        _fail("toolchain Linux registry bridge must be null")
    primary_asset = assets[0]
    return ToolchainIdentity(
        asset_name=primary_asset.name,
        asset_sha256=primary_asset.sha256,
        asset_size_bytes=primary_asset.size_bytes,
        development_assets=assets,
        development_provider=_string(entry, "development_provider", "platform"),
        development_root=_manifest_root(document, "development_root", root),
        llvm_version=LLVM_VERSION,
        platform_id=platform_id,
        plugin_checks=PLUGIN_CHECKS,
        plugin_host_path=_plugin_host_path(entry, runtime_root, output_root),
        plugin_library_path=output_root / _repository_path(
            _string(entry, "plugin_library", "platform"),
            "platform.plugin_library",
        ),
        plugin_output_root=output_root,
        plugin_strategy=strategy,
        registry_bridge_export=bridge,
        release_tag=RELEASE_TAG,
        required_development_files=_relative_files(
            entry.get("required_development_files"),
            "required_development_files",
        ),
        required_runtime_files=_relative_files(
            entry.get("required_runtime_files"),
            "required_runtime_files",
        ),
        runtime_clang=_runtime_path(entry, "clang", runtime_root),
        runtime_clang_cl=_runtime_path(entry, "clang_cl", runtime_root),
        runtime_clang_tidy=_runtime_path(entry, "clang_tidy", runtime_root),
        runtime_llvm_readobj=_optional_runtime_path(
            entry,
            "llvm_readobj",
            runtime_root,
        ),
        runtime_root=runtime_root,
    )


def _tool_output(path: Path) -> str:
    try:
        # jig-ignore-next-line: indivisible reviewed Ruff rule identifier
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [str(path), "--version"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except OSError as error:
        _fail(f"failed to execute LLVM version query {path}: {error}")
    if completed.returncode != 0:
        _fail(f"LLVM version query failed: {path}")
    return completed.stdout + chr(10) + completed.stderr


def _require_files(root: Path, files: tuple[Path, ...], label: str) -> None:
    missing = [str(path) for path in files if not (root / path).is_file()]
    if missing:
        _fail(f"{label} is missing required files: {', '.join(missing)}")


def validate_installation(
    identity: ToolchainIdentity,
    *,
    observed_platform: str | None = None,
) -> None:
    """Require exact runtime and development files for one host."""
    current_platform = observed_platform or host_platform_id()
    if current_platform != identity.platform_id:
        message = f"toolchain targets {identity.platform_id}; host is "
        _fail(message + current_platform)
    _require_files(
        identity.runtime_root,
        identity.required_runtime_files,
        "LLVM runtime",
    )
    _require_files(
        identity.development_root,
        identity.required_development_files,
        "LLVM development kit",
    )
    clang_version = f"clang version {identity.llvm_version}"
    if clang_version not in _tool_output(identity.clang):
        _fail(f"Clang must report version {identity.llvm_version}")
    if f"LLVM version {identity.llvm_version}" not in _tool_output(
        identity.clang_tidy
    ):
        _fail(f"clang-tidy must report LLVM version {identity.llvm_version}")


def verify_archive(path: Path, identity: ToolchainIdentity) -> None:
    """Verify one downloaded development archive against tracked identity."""
    if not path.is_file():
        _fail(f"LLVM development archive not found: {path}")
    size = path.stat().st_size
    if size != identity.asset_size_bytes:
        prefix = "LLVM development archive size mismatch: expected "
        _fail(f"{prefix}{identity.asset_size_bytes}; observed {size}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    observed = digest.hexdigest()
    if observed != identity.asset_sha256:
        prefix = "LLVM development archive SHA-256 mismatch: expected "
        _fail(f"{prefix}{identity.asset_sha256}; observed {observed}")


def _arguments(argv: list[str] | None) -> Path | None:
    parser = argparse.ArgumentParser(
        description="Validate the pinned clang-tidy development toolchain.",
    )
    _ = parser.add_argument(
        "--archive",
        type=Path,
        help="also verify one explicitly supplied LLVM development archive",
    )
    namespace = parser.parse_args(argv)
    value = vars(namespace).get("archive")
    return value if isinstance(value, Path) else None


def main(argv: list[str] | None = None) -> int:
    """Validate local clang-tidy development evidence.

    Returns:
        Process status for local identity and optional archive validation.

    """
    try:
        archive = _arguments(argv)
        identity = load_identity()
        validate_installation(identity)
        if archive is not None:
            verify_archive(archive, identity)
    except ToolchainError as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    message = (
        "clang-tidy development toolchain ready: LLVM "
         f"{identity.llvm_version} ({identity.platform_id})"
    )
    _ = sys.stdout.write(message + chr(10))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
