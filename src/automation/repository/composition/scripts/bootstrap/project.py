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
#   - Checkout initialization and local-toolchain diagnostics.
# - Must-Not:
#   - Claim unsupported CUDA/Linux or native toolchain support.
# - Allows:
#   - Inputs: repository root and explicit optional-component requirements.
#   - Outputs: local directories and component readiness diagnostics.
#   - Side effects: ignored local directories and pinned Python provisioning.
# - Split-When:
#   - Split when native downloads gain an independent manifest lifecycle.
# - Merge-When:
#   - Merge when another bootstrap owns this initialization contract.
# - Summary:
#   - Initialize a Malbolge development checkout.
# - Description:
#   - Prepares local state, Python validation, and tool diagnostics.
# - Usage:
#   - Run as `python -m scripts.bootstrap.project` from the repository root.
# - Defaults:
#   - Python is provisioned; native/CUDA components are diagnostic.
#

"""Initialize a Malbolge development checkout."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
from pathlib import PureWindowsPath
import platform
import sys
import tomllib
from typing import Final
from typing import Never
from typing import cast

from scripts.bootstrap import python_validation
from scripts.repository_root import repository_root

ROOT: Final = repository_root(Path(__file__))
REQUIRED_ROOT_FILES: Final = (
    "Cargo.toml",
    "LICENSE-MIT",
    ".jig/jig.toml",
    "malbolge.json",
    ".jig/version/rust-toolchain.toml",
)
LOCAL_DIRECTORIES: Final = (".cache", ".dependencies", ".logs", ".temp")
WINDOWS_SYSTEM: Final = "windows"
LINUX_SYSTEM: Final = "linux"
MACOS_SYSTEM: Final = "darwin"
X86_64_MACHINES: Final = frozenset(("amd64", "x86_64"))
AARCH64_MACHINES: Final = frozenset(("aarch64", "arm64"))
WINDOWS_CHANNEL_MARKER: Final = "windows"
UNKNOWN_PLATFORM: Final = "unknown"
PARENT_SEGMENT: Final = ".."
PATH_SEPARATORS: Final = frozenset(("/", "\\"))
CUDA_TOOLCHAIN_MANIFEST: Final = (
    Path("src")
    / "optimization"
    / "accelerator"
    / "adapter-outbound"
    / "accelerator"
    / "cuda"
    / "toolchain.json"
)
CUDA_TOOLCHAIN_SCHEMA_VERSION: Final = 1
SYSTEM_NAMES: Final = {
    WINDOWS_SYSTEM: WINDOWS_SYSTEM,
    LINUX_SYSTEM: LINUX_SYSTEM,
    MACOS_SYSTEM: "macos",
}
MACHINE_NAMES: Final = {
    **dict.fromkeys(X86_64_MACHINES, "x86_64"),
    **dict.fromkeys(AARCH64_MACHINES, "aarch64"),
}


class ComponentState(StrEnum):
    """Readiness state for one optional repository component."""

    MISSING = "missing"
    READY = "ready"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class ComponentStatus:
    """One deterministic local component readiness result."""

    detail: str
    name: str
    path: Path | None
    state: ComponentState


@dataclass(frozen=True, slots=True)
class ProjectInitializationReport:
    """Complete initialized checkout and optional-component report."""

    cuda: ComponentStatus
    directories: tuple[Path, ...]
    jig: ComponentStatus
    platform_id: str
    python_environment: Path
    rust: ComponentStatus


class InitializationError(RuntimeError):
    """Deterministic project initialization failure."""


def _fail(message: str) -> Never:
    raise InitializationError(message)


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        _fail(f"{label} must be an object")
    return cast("dict[str, object]", value)


def _required_string(document: dict[str, object], key: str, label: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        _fail(f"{label}.{key} must be a nonempty string")
    return value


def validate_repository(root: Path = ROOT) -> None:
    """Reject a path that is not the expected repository root."""
    missing = tuple(
        name for name in REQUIRED_ROOT_FILES if not (root / name).is_file()
    )
    if missing:
        missing_text = ", ".join(missing)
        _fail(f"repository root is missing: {missing_text}")


def initialize_local_directories(root: Path = ROOT) -> tuple[Path, ...]:
    """Create the ignored repository-local state directories.

    Returns:
        Created or already-existing directory paths in stable order.

    """
    directories = tuple(root / name for name in LOCAL_DIRECTORIES)
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    return directories


def host_platform_id(
    *,
    system: str | None = None,
    machine: str | None = None,
) -> str:
    """Return the normalized host platform identity used by tool manifests.

    Returns:
        Lowercase operating-system and architecture identity.

    """
    observed_system = (system or platform.system()).strip().lower()
    observed_machine = (machine or platform.machine()).strip().lower()
    operating_system = SYSTEM_NAMES.get(
        observed_system,
        observed_system or UNKNOWN_PLATFORM,
    )
    architecture = MACHINE_NAMES.get(
        observed_machine,
        observed_machine or UNKNOWN_PLATFORM,
    )
    return f"{operating_system}-{architecture}"


def _path_segment(value: str, label: str) -> str:
    windows_path = PureWindowsPath(value)
    reserved = value in {".", PARENT_SEGMENT}
    has_separator = any(separator in value for separator in PATH_SEPARATORS)
    windows_anchored = bool(windows_path.drive or windows_path.root)
    if reserved or has_separator or windows_anchored:
        _fail(f"{label} must be one repository-local path segment")
    return value


def _repository_relative_path(value: str, label: str) -> Path:
    path = Path(value)
    windows_path = PureWindowsPath(value)
    native_relative = (
        not path.is_absolute() and PARENT_SEGMENT not in path.parts
    )
    windows_relative = (
        not windows_path.drive
        and not windows_path.root
        and PARENT_SEGMENT not in windows_path.parts
    )
    if not native_relative or not windows_relative:
        _fail(f"{label} must stay within the repository")
    return path


def _reject_duplicate_pairs(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            _fail(f"duplicate bootstrap JSON key: {key}")
        document[key] = value
    return document


def _json_document(path: Path, label: str) -> dict[str, object]:
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


def _toml_document(path: Path, label: str) -> dict[str, object]:
    try:
        parsed = cast("object", tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError) as error:
        _fail(f"cannot read {label}: {error}")
    return _mapping(parsed, label)


def inspect_cuda(root: Path, platform_id: str) -> ComponentStatus:
    """Inspect the tracked hermetic CUDA manifest for this host.

    Returns:
        Ready, missing, or unsupported CUDA bundle status.

    """
    manifest_path = root / CUDA_TOOLCHAIN_MANIFEST
    path: Path | None = manifest_path
    if not manifest_path.is_file():
        detail = "tracked CUDA toolchain manifest is absent"
        state = ComponentState.MISSING
    else:
        document = _json_document(manifest_path, "CUDA toolchain manifest")
        schema_version = document.get("schema_version")
        if (
            type(schema_version) is not int
            or schema_version != CUDA_TOOLCHAIN_SCHEMA_VERSION
        ):
            _fail("unsupported CUDA toolchain manifest schema")
        manifest_platform = _required_string(
            document,
            "platform",
            "CUDA manifest",
        )
        toolkit_root = _required_string(
            document,
            "toolkit_root",
            "CUDA manifest",
        )
        path = root / _repository_relative_path(
            toolkit_root,
            "CUDA manifest.toolkit_root",
        )
        if manifest_platform != platform_id:
            detail = (
                f"manifest targets {manifest_platform}; host is {platform_id}"
            )
            state = ComponentState.UNSUPPORTED
        elif not path.is_dir():
            detail = "matching hermetic CUDA bundle has not been installed"
            state = ComponentState.MISSING
        else:
            detail = "matching hermetic CUDA bundle is present"
            state = ComponentState.READY
    return ComponentStatus(
        detail=detail,
        name="cuda",
        path=path,
        state=state,
    )


def _cargo_candidates(
    root: Path,
    channel: str,
    *,
    windows: bool,
) -> tuple[Path, ...]:
    executable = "cargo.exe" if windows else "cargo"
    return (
        root
        / ".dependencies"
        / "jig"
        / "source"
        / ".dependencies"
        / "rust"
        / channel
        / "bin"
        / executable,
        root / ".dependencies" / "rust" / channel / "bin" / executable,
    )


def inspect_rust(root: Path, platform_id: str) -> ComponentStatus:
    """Inspect the pinned Rust channel and an executable Cargo path.

    Returns:
        Ready, missing, or unsupported Rust toolchain status.

    """
    toolchain_path = root / ".jig/version/rust-toolchain.toml"
    document = _toml_document(toolchain_path, "Rust toolchain manifest")
    toolchain = _mapping(document.get("toolchain"), "rust-toolchain.toolchain")
    channel = _path_segment(
        _required_string(toolchain, "channel", "rust-toolchain.toolchain"),
        "rust-toolchain.toolchain.channel",
    )
    path: Path | None = toolchain_path
    if WINDOWS_CHANNEL_MARKER in channel and not platform_id.startswith(
        WINDOWS_SYSTEM
    ):
        detail = f"pinned channel {channel} is Windows-specific"
        state = ComponentState.UNSUPPORTED
    else:
        windows = platform_id.startswith(WINDOWS_SYSTEM)
        local = next(
            (
                candidate
                for candidate in _cargo_candidates(
                    root,
                    channel,
                    windows=windows,
                )
                if candidate.is_file()
            ),
            None,
        )
        if local is not None:
            path = local
            detail = f"pinned Cargo for {channel} is present"
            state = ComponentState.READY
        else:
            detail = f"Cargo for pinned channel {channel} is absent"
            state = ComponentState.MISSING
    return ComponentStatus(
        detail=detail,
        name="rust",
        path=path,
        state=state,
    )


def inspect_jig(root: Path, platform_id: str) -> ComponentStatus:
    """Inspect the repository-local Jig launcher for this host.

    Returns:
        Ready or missing repository governance tool status.

    """
    executable = "jig.cmd" if platform_id.startswith(WINDOWS_SYSTEM) else "jig"
    path = root / ".dependencies" / "jig" / "bin" / executable
    if path.is_file():
        return ComponentStatus(
            detail="repository-local Jig launcher is present",
            name="jig",
            path=path,
            state=ComponentState.READY,
        )
    return ComponentStatus(
        detail=(
            "repository-local Jig launcher has not been installed for this host"
        ),
        name="jig",
        path=path,
        state=ComponentState.MISSING,
    )


def initialize_project(
    root: Path = ROOT,
    *,
    provision_python: bool = True,
    require_cuda: bool = False,
) -> ProjectInitializationReport:
    """Initialize local state and report optional toolchain readiness.

    Returns:
        Complete checkout initialization report.

    """
    validate_repository(root)
    directories = initialize_local_directories(root)
    layout = (
        python_validation.initialize()
        if provision_python
        else python_validation.validation_layout(root)
    )
    platform_id = host_platform_id()
    cuda = inspect_cuda(root, platform_id)
    rust = inspect_rust(root, platform_id)
    jig = inspect_jig(root, platform_id)
    if require_cuda and cuda.state is not ComponentState.READY:
        _fail(f"CUDA is required but {cuda.state}: {cuda.detail}")
    return ProjectInitializationReport(
        cuda=cuda,
        directories=directories,
        jig=jig,
        platform_id=platform_id,
        python_environment=layout.environment,
        rust=rust,
    )


def render_report(report: ProjectInitializationReport) -> str:
    """Render a stable human-readable initialization report.

    Returns:
        Newline-terminated report text.

    """
    lines = [
        f"project initialized for {report.platform_id}",
        f"python: ready ({report.python_environment})",
    ]
    for component in (report.rust, report.jig, report.cuda):
        location = "" if component.path is None else f" ({component.path})"
        line = f"{component.name}: {component.state} - "
        line += f"{component.detail}{location}"
        lines.append(line)
    return "\n".join((*lines, ""))


def _arguments(argv: list[str] | None) -> tuple[bool, bool]:
    parser = argparse.ArgumentParser(
        description="Initialize repository-local Malbolge development state.",
    )
    _ = parser.add_argument(
        "--skip-python",
        action="store_true",
        help=(
            "report paths without installing the pinned Python validation tools"
        ),
    )
    _ = parser.add_argument(
        "--require-cuda",
        action="store_true",
        help="fail unless a matching hermetic CUDA bundle is present",
    )
    namespace = parser.parse_args(argv)
    values = cast("dict[str, object]", vars(namespace))
    skip_python = values.get("skip_python")
    require_cuda = values.get("require_cuda")
    if type(skip_python) is not bool or type(require_cuda) is not bool:
        _fail("bootstrap arguments did not resolve to booleans")
    return skip_python, require_cuda


def main(argv: list[str] | None = None) -> int:
    """Initialize the current checkout and print component readiness.

    Returns:
        Zero after successful initialization, otherwise one.

    """
    skip_python, require_cuda = _arguments(argv)
    try:
        report = initialize_project(
            provision_python=not skip_python,
            require_cuda=require_cuda,
        )
    except (
        InitializationError,
        OSError,
        python_validation.ProvisionError,
    ) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    _ = sys.stdout.write(render_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
