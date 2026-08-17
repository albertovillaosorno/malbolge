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
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
import json
import os
from pathlib import Path
from pathlib import PureWindowsPath
import platform
import shutil
from shutil import which

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed Rustup argv.
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
RUST_IMPORT_MARKER: Final = ".malbolge-rust-toolchain-import-v1"
RUST_NIGHTLY_CHANNEL: Final = "nightly-2026-07-14"
GIT_IMPORT_MARKER: Final = ".malbolge-git-import-v1"
CARGO_HOME_RELATIVE: Final = Path(".dependencies/cargo-home")
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
class GitHostObservation:
    """Native Git executable, version banner, and helper directory."""

    executable: Path
    exec_path: Path
    version_line: str


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
    (root / CARGO_HOME_RELATIVE).mkdir(parents=True, exist_ok=True)
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


def _link_or_copy(source: str, destination: str) -> str:
    try:
        os.link(source, destination)
    except OSError:
        _ = shutil.copy2(source, destination)
    return destination


type GitVersionRunner = Callable[[Path], str | None]
type GitExecPathRunner = Callable[[Path], Path | None]


def _run_git_version(git: Path) -> str | None:
    # jig-ignore-next-line: reviewed subprocess suppression is indivisible
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(git), "--version"],
        check=False,
        capture_output=True,
        shell=False,
        text=True,
    )
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    return output or None


def _run_git_exec_path(git: Path) -> Path | None:
    # jig-ignore-next-line: reviewed subprocess suppression is indivisible
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(git), "--exec-path"],
        check=False,
        capture_output=True,
        shell=False,
        text=True,
    )
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    if not output:
        return None
    path = Path(output)
    return path if path.is_dir() else None


def _configured_git_version(root: Path) -> str:
    document = _toml_document(root / ".jig/jig.toml", "Jig configuration")
    tools = _mapping(document.get("tool"), "Jig configuration.tool")
    git = _mapping(tools.get("git"), "Jig configuration.tool.git")
    return _path_segment(
        _required_string(git, "version", "Jig configuration.tool.git"),
        "Jig configuration.tool.git.version",
    )


def git_version_line_matches(required: str, version_line: str) -> bool:
    """Match exact upstream Git identity with an optional distribution suffix.

    Returns:
        True for the exact version or a dot-suffixed distribution build.

    """
    prefix = "git version "
    if not version_line.startswith(prefix):
        return False
    observed = version_line.removeprefix(prefix).strip()
    return observed == required or observed.startswith(f"{required}.")


def git_import_complete(git_root: Path) -> bool:
    """Return whether one imported Git installation reached its final marker.

    Returns:
        True only after the import completion marker is present.

    """
    return (git_root / GIT_IMPORT_MARKER).is_file()


def import_git_installation(
    git: Path,
    exec_path: Path,
    destination: Path,
    *,
    windows: bool,
) -> Path:
    """Import native Git runtime state and add one neutral Jig alias.

    Returns:
        Repository-local platform-neutral Git executable alias.

    """
    if destination.exists():
        _fail(f"Git import destination already exists: {destination}")
    native_name = "git.exe" if windows else "git"
    native = destination / "bin" / native_name
    native.parent.mkdir(parents=True)
    _ = _link_or_copy(str(git), str(native))
    alias = destination / "bin" / "git.bin"
    _ = _link_or_copy(str(native), str(alias))
    _ = shutil.copytree(
        exec_path,
        destination / "libexec" / "git-core",
        copy_function=_link_or_copy,
        symlinks=True,
    )
    _ = (destination / GIT_IMPORT_MARKER).write_text(
        "malbolge-git-import/v1\n",
        encoding="ascii",
        newline="\n",
    )
    return alias


def observe_host_git(platform_id: str) -> GitHostObservation | None:
    """Observe one native Git installation without making it authority.

    Returns:
        Complete host Git observation, otherwise None.

    """
    windows = platform_id.startswith(WINDOWS_SYSTEM)
    executable_name = "git.exe" if windows else "git"
    resolved = which(executable_name)
    if resolved is None:
        return None
    executable = Path(resolved)
    version_line = _run_git_version(executable)
    exec_path = _run_git_exec_path(executable)
    if version_line is None or exec_path is None:
        return None
    return GitHostObservation(executable, exec_path, version_line)


def import_host_git(
    root: Path,
    platform_id: str,
    observation: GitHostObservation,
) -> Path | None:
    """Import matching observed Git into one repository-local portable layout.

    Returns:
        Neutral Git alias when admitted and imported, otherwise None.

    """
    required = _configured_git_version(root)
    destination = root / ".dependencies" / "git" / required
    alias = destination / "bin" / "git.bin"
    if git_import_complete(destination) and alias.is_file():
        return alias
    if destination.exists():
        _fail(f"incomplete Git import already exists: {destination}")
    admitted = (
        git_version_line_matches(required, observation.version_line)
        and observation.exec_path.is_dir()
    )
    if not admitted:
        return None
    windows = platform_id.startswith(WINDOWS_SYSTEM)
    return import_git_installation(
        observation.executable,
        observation.exec_path,
        destination,
        windows=windows,
    )


def rust_toolchain_import_complete(toolchain_root: Path) -> bool:
    """Return whether one imported toolchain reached its final marker.

    Returns:
        True only after the import completion marker is present.

    """
    return (toolchain_root / RUST_IMPORT_MARKER).is_file()


def import_rust_toolchain(
    source: Path,
    destination: Path,
    *,
    tool_ids: tuple[str, ...],
    windows: bool,
) -> tuple[Path, ...]:
    """Import one host Rust tree and add platform-neutral Jig aliases.

    Returns:
        Alias paths inside the imported native toolchain `bin` directory.

    """
    if destination.exists():
        _fail(f"Rust import destination already exists: {destination}")
    _ = shutil.copytree(
        source,
        destination,
        copy_function=_link_or_copy,
        symlinks=True,
    )
    suffix = ".exe" if windows else ""
    aliases: list[Path] = []
    for tool_id in tool_ids:
        native = destination / "bin" / f"{tool_id}{suffix}"
        if not native.is_file():
            _fail(f"imported Rust tool is missing: {native}")
        alias = destination / "bin" / f"{tool_id}.bin"
        _ = _link_or_copy(str(native), str(alias))
        aliases.append(alias)
    _ = (destination / RUST_IMPORT_MARKER).write_text(
        "malbolge-rust-toolchain-import/v1\n",
        encoding="ascii",
        newline="\n",
    )
    return tuple(aliases)


type RustToolchainResolver = Callable[[str], Path | None]
type RustupWhichRunner = Callable[[Path, str], str | None]
type RustupListRunner = Callable[[Path], tuple[str, ...]]


def _run_rustup_list(rustup: Path) -> tuple[str, ...]:
    # jig-ignore-next-line: reviewed subprocess suppression is indivisible
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(rustup), "toolchain", "list"],
        check=False,
        capture_output=True,
        shell=False,
        text=True,
    )
    if completed.returncode != 0:
        return ()
    return tuple(
        line.split(maxsplit=1)[0]
        for line in completed.stdout.splitlines()
        if line.strip()
    )


def rustup_channel_is_installed(
    channel: str,
    installed: tuple[str, ...],
) -> bool:
    """Match a pinned channel against installed host-qualified forms.

    Returns:
        True when the exact channel or one host-qualified form is installed.

    """
    prefix = f"{channel}-"
    return any(item == channel or item.startswith(prefix) for item in installed)


def _run_rustup_which(rustup: Path, channel: str) -> str | None:
    # jig-ignore-next-line: reviewed subprocess suppression is indivisible
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(rustup), "which", "--toolchain", channel, "cargo"],
        check=False,
        capture_output=True,
        shell=False,
        text=True,
    )
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    return output or None


def rustup_toolchain_root(
    rustup: Path,
    channel: str,
    *,
    runner: RustupWhichRunner = _run_rustup_which,
) -> Path | None:
    """Resolve one installed Rustup channel to its native toolchain root.

    Returns:
        Existing toolchain root containing Cargo, otherwise None.

    """
    raw = runner(rustup, channel)
    if raw is None:
        return None
    cargo = Path(raw)
    if not cargo.is_file():
        return None
    return cargo.parent.parent


def rustup_toolchain_resolver(
    rustup: Path,
    *,
    list_runner: RustupListRunner = _run_rustup_list,
    which_runner: RustupWhichRunner = _run_rustup_which,
) -> RustToolchainResolver:
    """Build a resolver that never queries an uninstalled Rustup channel.

    Returns:
        Stable resolver over one local installed-toolchain snapshot.

    """
    installed = list_runner(rustup)

    def resolve(channel: str) -> Path | None:
        if not rustup_channel_is_installed(channel, installed):
            return None
        return rustup_toolchain_root(
            rustup,
            channel,
            runner=which_runner,
        )

    return resolve


def rustup_executable(
    platform_id: str,
    *,
    home: Path | None = None,
    search_path: bool = True,
) -> Path | None:
    """Locate Rustup without requiring Cargo home on ambient PATH.

    Returns:
        Explicit Rustup path when installed, otherwise None.

    """
    windows = platform_id.startswith(WINDOWS_SYSTEM)
    executable = "rustup.exe" if windows else "rustup"
    cargo_home = (home or Path.home()) / ".cargo" / "bin" / executable
    if cargo_home.is_file():
        return cargo_home
    if search_path:
        resolved = which(executable)
        if resolved is not None:
            return Path(resolved)
    return None


def _rust_channel(root: Path) -> str:
    toolchain_path = root / ".jig/version/rust-toolchain.toml"
    document = _toml_document(toolchain_path, "Rust toolchain manifest")
    toolchain = _mapping(document.get("toolchain"), "rust-toolchain.toolchain")
    return _path_segment(
        _required_string(toolchain, "channel", "rust-toolchain.toolchain"),
        "rust-toolchain.toolchain.channel",
    )


def import_installed_rust_toolchains(
    root: Path,
    platform_id: str,
    *,
    resolver: RustToolchainResolver,
) -> tuple[Path, ...]:
    """Import available pinned stable and nightly Rust trees.

    Returns:
        Completed repository-local toolchain roots in stable order.

    """
    windows = platform_id.startswith(WINDOWS_SYSTEM)
    requests = (
        (_rust_channel(root), ("cargo",)),
        (RUST_NIGHTLY_CHANNEL, ("cargo-clippy", "cargo-fmt")),
    )
    imported: list[Path] = []
    for channel, tool_ids in requests:
        destination = root / ".dependencies" / "rust" / channel
        if rust_toolchain_import_complete(destination):
            imported.append(destination)
            continue
        if destination.exists():
            _fail(f"incomplete Rust import already exists: {destination}")
        source = resolver(channel)
        if source is None:
            continue
        _ = import_rust_toolchain(
            source,
            destination,
            tool_ids=tool_ids,
            windows=windows,
        )
        imported.append(destination)
    return tuple(imported)


def import_host_rust_toolchains(
    root: Path,
    platform_id: str,
) -> tuple[Path, ...]:
    """Import already-installed pinned Rustup channels into the repository.

    Returns:
        Completed repository-local imports, or empty when Rustup is absent.

    """
    rustup = rustup_executable(platform_id)
    if rustup is None:
        return ()
    return import_installed_rust_toolchains(
        root,
        platform_id,
        resolver=rustup_toolchain_resolver(rustup),
    )


def _imported_cargo(root: Path, channel: str) -> Path:
    return root / ".dependencies" / "rust" / channel / "bin" / "cargo.bin"


def inspect_rust(root: Path, platform_id: str) -> ComponentStatus:
    """Inspect the pinned Rust channel and imported neutral Cargo alias.

    Returns:
        Ready only for a completed repository-local imported toolchain.

    """
    del platform_id
    toolchain_path = root / ".jig/version/rust-toolchain.toml"
    channel = _rust_channel(root)
    cargo = _imported_cargo(root, channel)
    imported_root = cargo.parent.parent
    if cargo.is_file() and rust_toolchain_import_complete(imported_root):
        path: Path | None = cargo
        detail = f"pinned Cargo for {channel} is present"
        state = ComponentState.READY
    else:
        path = toolchain_path
        detail = f"Cargo for pinned channel {channel} is absent"
        state = ComponentState.MISSING
    return ComponentStatus(
        detail=detail,
        name="rust",
        path=path,
        state=state,
    )


def inspect_jig(root: Path, platform_id: str) -> ComponentStatus:
    """Inspect the standalone Jig launcher resolved from PATH.

    Returns:
        Ready or missing repository governance tool status.

    """
    del root
    executable = "jig.cmd" if platform_id.startswith(WINDOWS_SYSTEM) else "jig"
    resolved = which(executable)
    if resolved is not None:
        path = Path(resolved)
        return ComponentStatus(
            detail="standalone Jig launcher is present on PATH",
            name="jig",
            path=path,
            state=ComponentState.READY,
        )
    return ComponentStatus(
        detail="standalone Jig launcher is unavailable on PATH",
        name="jig",
        path=None,
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
    observation = observe_host_git(platform_id)
    if observation is not None:
        _ = import_host_git(root, platform_id, observation)
    _ = import_host_rust_toolchains(root, platform_id)
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
