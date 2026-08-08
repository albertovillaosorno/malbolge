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
#   - Binds plugin development to one reviewed LLVM release artifact and roots.
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
SCHEMA_VERSION: Final = 1
LLVM_VERSION: Final = "22.1.8"
RELEASE_TAG: Final = f"llvmorg-{LLVM_VERSION}"
WINDOWS_SYSTEM: Final = "windows"
WINDOWS_PLATFORM: Final = "windows-x86_64"
PARENT_SEGMENT: Final = ".."
WINDOWS_PLUGIN_STRATEGY: Final = "project-host-registry-bridge-v1"
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
        "platform",
        "development_asset",
        "runtime_root",
        "development_root",
        "required_runtime_files",
        "required_development_files",
        "plugin_output_root",
        "windows_plugin_strategy",
        "registry_bridge_export",
        "plugin_checks",
    }
)
ASSET_KEYS: Final = frozenset({"name", "size_bytes", "sha256"})


class ToolchainError(RuntimeError):
    """Tracked LLVM development identity is malformed or unavailable."""


@dataclass(frozen=True, slots=True)
class ToolchainIdentity:
    """Validated immutable LLVM/clang-tidy development identity."""

    asset_name: str
    asset_sha256: str
    asset_size_bytes: int
    development_root: Path
    llvm_version: str
    platform_id: str
    plugin_checks: tuple[str, ...]
    plugin_output_root: Path
    registry_bridge_export: str
    release_tag: str
    required_development_files: tuple[Path, ...]
    required_runtime_files: tuple[Path, ...]
    runtime_root: Path
    windows_plugin_strategy: str

    @property
    def clang(self) -> Path:
        """Pinned Clang frontend executable."""
        return self.runtime_root / "bin" / "clang.exe"

    @property
    def clang_cl(self) -> Path:
        """Pinned MSVC-compatible Clang compiler executable."""
        return self.runtime_root / "bin" / "clang-cl.exe"

    @property
    def clang_tidy(self) -> Path:
        """Upstream pinned clang-tidy executable."""
        return self.runtime_root / "bin" / "clang-tidy.exe"

    @property
    def plugin_host(self) -> Path:
        """Canonical project-owned clang-tidy host path."""
        return self.plugin_output_root / "bin" / "malbolge-clang-tidy.exe"

    @property
    def plugin_library(self) -> Path:
        """Canonical Malbolge clang-tidy plugin path."""
        return self.plugin_output_root / "bin" / "malbolge-tidy.dll"

    @property
    def llvm_readobj(self) -> Path:
        """Pinned COFF inspection executable."""
        return self.runtime_root / "bin" / "llvm-readobj.exe"


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


def _sha256(value: object) -> str:
    digest = "".join(_string_list(value, "development_asset.sha256"))
    if len(digest) != SHA256_HEX_LENGTH or any(
        character not in LOWER_HEX for character in digest
    ):
        _fail("development_asset.sha256 must be lowercase SHA-256")
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
    is_windows = observed_system == WINDOWS_SYSTEM
    is_x86_64 = observed_machine in {"amd64", "x86_64"}
    if is_windows and is_x86_64:
        return WINDOWS_PLATFORM
    return f"{observed_system or 'unknown'}-{observed_machine or 'unknown'}"


@dataclass(frozen=True, slots=True)
class _ReviewedContract:
    llvm_version: str
    release_tag: str
    platform_id: str
    strategy: str
    bridge: str
    checks: tuple[str, ...]


def _reviewed_contract(document: dict[str, object]) -> _ReviewedContract:
    if document.get("schema_version") != SCHEMA_VERSION:
        _fail("unsupported clang-tidy toolchain manifest schema")
    contract = _ReviewedContract(
        llvm_version=_string(document, "llvm_version", "toolchain"),
        release_tag=_string(document, "release_tag", "toolchain"),
        platform_id=_string(document, "platform", "toolchain"),
        strategy=_string(document, "windows_plugin_strategy", "toolchain"),
        bridge=_string(document, "registry_bridge_export", "toolchain"),
        checks=_string_list(document.get("plugin_checks"), "plugin_checks"),
    )
    expected = (
        ("llvm_version", contract.llvm_version, LLVM_VERSION),
        ("release_tag", contract.release_tag, RELEASE_TAG),
        ("platform", contract.platform_id, WINDOWS_PLATFORM),
        ("Windows strategy", contract.strategy, WINDOWS_PLUGIN_STRATEGY),
        ("registry bridge", contract.bridge, REGISTRY_BRIDGE_EXPORT),
    )
    for label, observed, required in expected:
        if observed != required:
            _fail(f"toolchain {label} must be {required}")
    if contract.checks != PLUGIN_CHECKS:
        _fail("toolchain plugin_checks must match the reviewed v1 plugin set")
    return contract


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


def load_identity(
    manifest: Path = MANIFEST,
    *,
    root: Path = ROOT,
) -> ToolchainIdentity:
    """Load and close-validate the tracked clang-tidy toolchain identity.

    Returns:
        Immutable normalized identity rooted below ``root``.

    """
    document = _document(manifest)
    _exact_keys(document, TOP_LEVEL_KEYS, "clang-tidy toolchain manifest")
    contract = _reviewed_contract(document)
    asset = _mapping(document.get("development_asset"), "development_asset")
    _exact_keys(asset, ASSET_KEYS, "development_asset")
    return ToolchainIdentity(
        asset_name=_string(asset, "name", "development_asset"),
        asset_sha256=_sha256(asset.get("sha256")),
        asset_size_bytes=_positive_int(
            asset, "size_bytes", "development_asset"
        ),
        development_root=_manifest_root(document, "development_root", root),
        llvm_version=contract.llvm_version,
        platform_id=contract.platform_id,
        plugin_checks=contract.checks,
        plugin_output_root=_manifest_root(document, "plugin_output_root", root),
        registry_bridge_export=contract.bridge,
        release_tag=contract.release_tag,
        required_development_files=_relative_files(
            document.get("required_development_files"),
            "required_development_files",
        ),
        required_runtime_files=_relative_files(
            document.get("required_runtime_files"),
            "required_runtime_files",
        ),
        runtime_root=_manifest_root(document, "runtime_root", root),
        windows_plugin_strategy=contract.strategy,
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
