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
import hashlib
import io
import json
import ntpath
import os
import platform
import re
import shlex
import shutil
import stat

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed Rustup argv.
import sys
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PureWindowsPath
from shutil import which
from typing import BinaryIO, Final, Never, Protocol, cast

import tomllib

from scripts.bootstrap import (
    cuda_validation,
    llvm_development_validation,
    llvm_validation,
    python_validation,
)
from scripts.repository_root import repository_root

ROOT: Final = repository_root(Path(__file__))
REQUIRED_ROOT_FILES: Final = (
    "Cargo.toml",
    "LICENSE",
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
RUST_LINUX_ADAPTER_MARKER: Final = ".malbolge-rust-linux-adapter-v1"
RUST_LINUX_ADAPTER_CONTENT: Final = b"malbolge-rust-linux-adapter/v1\n"
RUST_LINUX_ADAPTER_LINE_COUNT: Final = 2
GIT_IMPORT_MARKER: Final = ".malbolge-git-import-v1"
CARGO_HOME_RELATIVE: Final = Path(".dependencies/cargo-home")
UNKNOWN_PLATFORM: Final = "unknown"
PARENT_SEGMENT: Final = ".."
WINDOWS_SEPARATOR: Final = "\\"
PATH_SEPARATORS: Final = frozenset(("/", WINDOWS_SEPARATOR))
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
CUDA_TOOLCHAIN_INDEX: Final = CUDA_TOOLCHAIN_MANIFEST.with_name(
    "toolchain-manifests.json"
)
CUDA_TOOLCHAIN_INDEX_SCHEMA_VERSION: Final = 1
MAX_AUTHORITY_BYTES: Final = 1_048_576
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
    llvm: ComponentStatus
    llvm_development: ComponentStatus
    platform_id: str
    python_environment: Path
    python_provisioned: bool
    rust: ComponentStatus


@dataclass(frozen=True, slots=True)
class ProvisionRequests:
    """Explicit optional repository package provisioning requests."""

    cuda: bool = False
    llvm_development: bool = False


NO_PROVISION_REQUESTS: Final = ProvisionRequests()


class InitializationError(RuntimeError):
    """Deterministic project initialization failure."""


def _fail(message: str) -> Never:
    raise InitializationError(message)


class _NativeExceptionArgsDescriptor(Protocol):
    """Typed view of CPython's built-in BaseException args descriptor."""

    def __get__(
        self, instance: BaseException, owner: type[BaseException]
    ) -> object: ...


def _native_exception_detail(error: BaseException) -> str:
    """Describe a host failure without dispatching an exception formatter."""
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
    name = type.__getattribute__(  # ruff: ignore[unnecessary-dunder-call]
        type(error), "__name__"
    )
    return cast("str", name)


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
    root_identity: tuple[int, int] | None = None
    if _supports_pinned_local_state_directories():
        _admit_local_directory(root)
        opened_root = root.lstat()
        if type(opened_root) is not os.stat_result:
            _fail("local state directory root requires native file status")
        root_identity = opened_root.st_dev, opened_root.st_ino
    directories = tuple(root / name for name in LOCAL_DIRECTORIES)
    state_paths = (*directories, root / CARGO_HOME_RELATIVE)
    for directory in state_paths:
        _admit_local_directory(directory)
    if _supports_pinned_local_state_directories():
        root_descriptor = _open_local_state_parent(
            root, expected_identity=root_identity
        )
        try:
            dependencies_identity: tuple[int, int] | None = None
            for name in LOCAL_DIRECTORIES:
                identity = _create_local_state_child(root, root_descriptor, name)
                if name == ".dependencies":
                    dependencies_identity = identity
            if dependencies_identity is None:
                _fail("local state directory has no dependencies identity")
            dependencies = root / ".dependencies"
            child_descriptor = _open_local_state_parent(
                dependencies, expected_identity=dependencies_identity
            )
            try:
                _ = _create_local_state_child(
                    dependencies, child_descriptor, "cargo-home"
                )
            finally:
                _close_local_state_parent(child_descriptor)
        finally:
            _close_local_state_parent(root_descriptor)
    else:
        for directory in state_paths:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except (OSError, ValueError, TypeError, RuntimeError) as error:
                raise InitializationError(
                    "cannot create local state directory"
                ) from error
            _admit_local_directory(directory)
    return directories


def _platform_family(platform_id: str, system: str) -> bool:
    """Require an exact operating-system token before its architecture suffix."""
    return type(platform_id) is str and platform_id.startswith(f"{system}-")


def _host_identity_token(observed: object) -> str:
    """Reject foreign or whitespace-padded host identity observations."""
    if (
        type(observed) is not str
        or not observed
        or not observed.isprintable()
        or observed != observed.strip()
    ):
        return UNKNOWN_PLATFORM
    return observed.lower()


def host_platform_id(
    *,
    system: str | None = None,
    machine: str | None = None,
) -> str:
    """Return the normalized host platform identity used by tool manifests.

    Returns:
        Lowercase operating-system and architecture identity.

    """
    observed_system = _host_identity_token(
        platform.system() if system is None else system
    )
    observed_machine = _host_identity_token(
        platform.machine() if machine is None else machine
    )
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
    windows_invalid = bool(windows_path.drive or windows_path.root)
    windows_invalid = windows_invalid or ntpath.isreserved(value)
    if reserved or has_separator or windows_invalid:
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
    if not native_relative or not windows_relative or ntpath.isreserved(value):
        _fail(f"{label} must stay within the repository")
    if WINDOWS_SEPARATOR in value:
        _fail(f"{label} must use forward slashes")
    if any(segment in {"", "."} for segment in value.split("/")):
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


def _reject_authority_parent_redirects(path: Path) -> None:
    for parent in path.parents:
        if parent.is_symlink() or parent.is_junction():
            _fail("bootstrap authority parent path must not redirect")
        try:
            physical = parent.lstat()
        except FileNotFoundError:
            continue
        if type(physical) is not os.stat_result:
            _fail("bootstrap authority parent requires native file status")
        if not stat.S_ISDIR(physical.st_mode):
            _fail("bootstrap authority parent path must not redirect")


def _admit_local_directory(directory: Path) -> None:
    """Admit absent or physical checkout-local directories, never aliases."""
    try:
        _reject_authority_parent_redirects(directory)
    except InitializationError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("cannot inspect local state directory") from error
    try:
        physical = directory.lstat()
    except FileNotFoundError:
        return
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("cannot inspect local state directory") from error
    if type(physical) is not os.stat_result or not stat.S_ISDIR(physical.st_mode):
        _fail(f"local state directory must be physical: {directory}")


def _supports_pinned_local_state_directories() -> bool:
    """Use descriptor-relative directory creation on POSIX hosts."""
    return os.name == "posix"


def _require_local_state_parent_identity(parent: Path, descriptor: int) -> None:
    """Ensure a pinned state parent still has its physical checkout name."""
    try:
        _admit_local_directory(parent)
        opened = os.fstat(descriptor)
        named = parent.lstat()
        if (
            type(opened) is not os.stat_result
            or type(named) is not os.stat_result
            or not stat.S_ISDIR(opened.st_mode)
            or not stat.S_ISDIR(named.st_mode)
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("local state directory parent changed during creation")
    except InitializationError as error:
        raise InitializationError(
            "local state directory parent changed during creation"
        ) from error
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("cannot inspect local state directory") from error


def _open_local_state_parent(
    parent: Path, *, expected_identity: tuple[int, int] | None = None
) -> int:
    """Pin a physical directory before any child creation."""
    try:
        _admit_local_directory(parent)
        flags = (
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor = os.open(parent, flags)
    except InitializationError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("cannot open local state directory parent") from error
    if type(descriptor) is not int or descriptor < 0:
        _fail("local state directory parent requires native descriptor")
    try:
        _require_local_state_parent_identity(parent, descriptor)
        if expected_identity is not None:
            opened = os.fstat(descriptor)
            if (
                type(opened) is not os.stat_result
                or (opened.st_dev, opened.st_ino) != expected_identity
            ):
                _fail("local state directory parent changed before opening")
        return descriptor
    except BaseException:
        with suppress(OSError, ValueError, TypeError, RuntimeError):
            os.close(descriptor)
        raise


def _close_local_state_parent(descriptor: int) -> None:
    try:
        os.close(descriptor)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError(
            "cannot close local state directory parent"
        ) from error


def _create_local_state_child(
    parent: Path, descriptor: int, name: str
) -> tuple[int, int]:
    """Create or inspect a state child relative to its pinned physical parent."""
    child = parent / name
    try:
        _require_local_state_parent_identity(parent, descriptor)
        try:
            os.mkdir(name, dir_fd=descriptor)
        except FileExistsError:
            pass
        observed = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
        if type(observed) is not os.stat_result or not stat.S_ISDIR(observed.st_mode):
            _fail("local state directory must be physical")
        _require_local_state_parent_identity(parent, descriptor)
        _admit_local_directory(child)
        named = child.lstat()
        if type(named) is not os.stat_result or (named.st_dev, named.st_ino) != (
            observed.st_dev,
            observed.st_ino,
        ):
            _fail("local state directory changed during creation")
        return observed.st_dev, observed.st_ino
    except InitializationError as error:
        raise InitializationError(
            "local state directory changed during creation"
        ) from error
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("cannot create local state directory") from error


def _authority_present(path: Path) -> bool:
    """Distinguish genuinely absent authority from invalid existing input.

    Returns:
        False only when the authority leaf does not exist.

    """
    _reject_authority_parent_redirects(path)
    try:
        _ = path.lstat()
    except FileNotFoundError:
        return False
    return True


def _authority_identity(status: os.stat_result) -> tuple[int, ...]:
    """Admit a regular authority file and capture its stable identity.

    Returns:
        Device/inode, size and mutation-sensitive timestamps.

    """
    if type(status) is not os.stat_result:
        _fail("bootstrap authority requires native file status")
    if not stat.S_ISREG(status.st_mode):
        _fail("bootstrap authority must be a regular file")
    if status.st_nlink != 1:
        _fail("bootstrap authority must be single-linked")
    if status.st_size > MAX_AUTHORITY_BYTES:
        _fail("bootstrap authority exceeds byte limit")
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _open_authority_stream(descriptor: int) -> BinaryIO:
    """Transfer ownership of an opened authority descriptor to a stream.

    Returns:
        The binary stream owning the descriptor.

    Raises:
        InitializationError: The host cannot wrap the descriptor as a stream.

    """
    try:
        opened = os.fdopen(descriptor, "rb")
    except BaseException as error:
        with suppress(OSError):
            os.close(descriptor)
        if isinstance(error, (OSError, ValueError, TypeError, RuntimeError)):
            message = "cannot open bootstrap authority stream"
            raise InitializationError(message) from error
        raise
    if (
        type(opened) is not io.BufferedReader
        or type(opened.raw) is not io.FileIO
    ):
        with suppress(OSError):
            os.close(descriptor)
        _fail("bootstrap authority requires native buffered stream")
    try:
        wrapped_descriptor = opened.fileno()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        with suppress(OSError):
            os.close(descriptor)
        raise InitializationError("cannot inspect native stream descriptor") from error
    if type(wrapped_descriptor) is not int or wrapped_descriptor != descriptor:
        with suppress(OSError):
            os.close(descriptor)
        _fail("bootstrap authority requires matching native stream descriptor")
    return cast("BinaryIO", opened)


def _read_authority_bytes(path: Path) -> bytes:
    """Read bounded nonredirected authority bytes from one stable inode.

    Returns:
        Exact physical authority content, or a typed rejection.

    """
    _reject_authority_parent_redirects(path)
    admitted = path.lstat()
    expected = _authority_identity(admitted)
    if path.is_symlink() or path.is_junction():
        _fail("bootstrap authority path must not redirect")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        descriptor = os.open(path, flags)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("cannot open bootstrap authority") from error
    if type(descriptor) is not int or descriptor < 0:
        _fail("bootstrap authority requires native descriptor")
    with _open_authority_stream(descriptor) as stream:
        if _authority_identity(os.fstat(stream.fileno())) != expected:
            _fail("bootstrap authority changed before read")
        try:
            content = stream.read(MAX_AUTHORITY_BYTES + 1)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise InitializationError("cannot read bootstrap authority") from error
        if type(content) is not bytes:
            _fail("bootstrap authority stream must return native bytes")
        if (
            len(content) != admitted.st_size
            or _authority_identity(os.fstat(stream.fileno())) != expected
            or _authority_identity(path.lstat()) != expected
        ):
            _fail("bootstrap authority changed during read")
    _reject_authority_parent_redirects(path)
    return content


def _json_document(path: Path, label: str) -> dict[str, object]:
    try:
        parsed = cast(
            "object",
            json.loads(
                _read_authority_bytes(path).decode("utf-8"),
                object_pairs_hook=_reject_duplicate_pairs,
            ),
        )
    except (
        json.JSONDecodeError,
        OSError,
        ValueError,
        UnicodeDecodeError,
        RecursionError,
    ) as error:
        raise InitializationError(f"cannot read {label}") from error
    return _mapping(parsed, label)


def _toml_document(path: Path, label: str) -> dict[str, object]:
    try:
        parsed = cast(
            "object", tomllib.loads(_read_authority_bytes(path).decode("utf-8"))
        )
    except (
        OSError,
        ValueError,
        UnicodeDecodeError,
        RecursionError,
        tomllib.TOMLDecodeError,
    ) as error:
        raise InitializationError(f"cannot read {label}") from error
    return _mapping(parsed, label)


def cuda_toolchain_manifest_path(
    root: Path,
    platform_id: str,
) -> Path | None:
    """Select the tracked CUDA package manifest for one normalized platform.

    Returns:
        Platform manifest path, or ``None`` when the index has no such host.

    """
    index_path = root / CUDA_TOOLCHAIN_INDEX
    if not _authority_present(index_path):
        return root / CUDA_TOOLCHAIN_MANIFEST
    document = _json_document(index_path, "CUDA toolchain manifest index")
    schema_version = document.get("schema_version")
    if (
        type(schema_version) is not int
        or schema_version != CUDA_TOOLCHAIN_INDEX_SCHEMA_VERSION
    ):
        _fail("unsupported CUDA toolchain manifest index schema")
    platforms = _mapping(
        document.get("platforms"),
        "CUDA toolchain manifest index.platforms",
    )
    selected = platforms.get(platform_id)
    if selected is None:
        return None
    entry = _mapping(
        selected,
        f"CUDA toolchain manifest index.platforms.{platform_id}",
    )
    manifest_name = _path_segment(
        _required_string(
            entry,
            "manifest",
            f"CUDA toolchain manifest index.platforms.{platform_id}",
        ),
        f"CUDA toolchain manifest index.platforms.{platform_id}.manifest",
    )
    return index_path.parent / manifest_name


def cuda_toolchain_nvrtc_relative_path(
    root: Path,
    platform_id: str,
) -> Path | None:
    """Return indexed NVRTC path relative to the selected toolkit root.

    Returns:
        Relative NVRTC path, or ``None`` for legacy direct-manifest fixtures.

    """
    index_path = root / CUDA_TOOLCHAIN_INDEX
    if not _authority_present(index_path):
        return None
    document = _json_document(index_path, "CUDA toolchain manifest index")
    platforms = _mapping(
        document.get("platforms"),
        "CUDA toolchain manifest index.platforms",
    )
    selected = platforms.get(platform_id)
    if selected is None:
        return None
    entry = _mapping(
        selected,
        f"CUDA toolchain manifest index.platforms.{platform_id}",
    )
    relative = _required_string(
        entry,
        "nvrtc_library",
        f"CUDA toolchain manifest index.platforms.{platform_id}",
    )
    return _repository_relative_path(relative, "CUDA indexed NVRTC library")


def _cuda_bundle_state(
    root: Path,
    toolkit_path: Path,
    platform_id: str,
) -> tuple[str, ComponentState]:
    if not toolkit_path.is_dir():
        return (
            "matching hermetic CUDA bundle has not been installed",
            ComponentState.MISSING,
        )
    try:
        _reject_authority_parent_redirects(toolkit_path)
        physical = toolkit_path.lstat()
    except (InitializationError, OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("cannot inspect CUDA toolkit root") from error
    if type(physical) is not os.stat_result or not stat.S_ISDIR(physical.st_mode):
        _fail("CUDA toolkit root must be a physical directory")
    nvrtc_relative = cuda_toolchain_nvrtc_relative_path(root, platform_id)
    nvrtc = None if nvrtc_relative is None else toolkit_path / nvrtc_relative
    if nvrtc is not None:
        try:
            resolved = nvrtc.resolve(strict=True)
            in_toolkit = resolved.is_relative_to(toolkit_path.resolve(strict=True))
            native_library = resolved.is_file()
        except (OSError, ValueError, TypeError, RuntimeError):
            in_toolkit = False
            native_library = False
        if not in_toolkit or not native_library:
            return (
                "matching hermetic CUDA NVRTC library is absent",
                ComponentState.MISSING,
            )
    return "matching hermetic CUDA bundle is present", ComponentState.READY


def _inspect_cuda_manifest(
    root: Path,
    manifest_path: Path,
    platform_id: str,
) -> ComponentStatus:
    path = manifest_path
    if not _authority_present(manifest_path):
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
        else:
            detail, state = _cuda_bundle_state(root, path, platform_id)
    return ComponentStatus(
        detail=detail,
        name="cuda",
        path=path,
        state=state,
    )


def inspect_cuda(root: Path, platform_id: str) -> ComponentStatus:
    """Inspect the tracked hermetic CUDA manifest for this host.

    Returns:
        Ready, missing, or unsupported CUDA bundle status.

    """
    manifest_path = cuda_toolchain_manifest_path(root, platform_id)
    if manifest_path is None:
        return ComponentStatus(
            detail=f"no tracked CUDA toolchain manifest for {platform_id}",
            name="cuda",
            path=None,
            state=ComponentState.UNSUPPORTED,
        )
    return _inspect_cuda_manifest(root, manifest_path, platform_id)


def _verified_import_file_digest(
    source: Path | str,
    admitted: os.stat_result,
    *,
    source_fd: int | None = None,
) -> bytes:
    """Hash original physical file bytes through one nonfollowing native handle."""
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    descriptor: int | None = None
    closed_receipt: os.stat_result | None = None

    def matches(observed: object) -> bool:
        return (
            type(observed) is os.stat_result
            and stat.S_ISREG(observed.st_mode)
            and (observed.st_dev, observed.st_ino) == (admitted.st_dev, admitted.st_ino)
            and observed.st_size == admitted.st_size
            and observed.st_mtime_ns == admitted.st_mtime_ns
            and stat.S_IMODE(observed.st_mode) == stat.S_IMODE(admitted.st_mode)
        )

    try:
        descriptor = os.open(source, flags, dir_fd=source_fd)
        if type(descriptor) is not int or descriptor < 0:
            _fail("import physical file digest requires native descriptor")
        if not matches(os.fstat(descriptor)):
            _fail("import physical file changed before digest")
        digest = hashlib.sha256()
        remaining = admitted.st_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1_048_576))
            if type(chunk) is not bytes or not chunk:
                _fail("import physical file digest is incomplete")
            digest.update(chunk)
            remaining -= len(chunk)
        final_byte = os.read(descriptor, 1)
        if type(final_byte) is not bytes or final_byte != b"":
            _fail("import physical file digest changed size")
        named = os.stat(source, dir_fd=source_fd, follow_symlinks=False)
        opened = os.fstat(descriptor)
        if (
            not matches(opened)
            or not matches(named)
            or opened.st_ctime_ns != named.st_ctime_ns
            or opened.st_nlink != named.st_nlink
        ):
            _fail("import physical file changed during digest")
        closed_receipt = opened
        return digest.digest()
    except InitializationError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("import physical file digest failed") from error
    finally:
        if type(descriptor) is int and descriptor >= 0:
            try:
                os.close(descriptor)
            except (OSError, ValueError, TypeError, RuntimeError) as error:
                raise InitializationError(
                    "import physical file digest close failed"
                ) from error
            if closed_receipt is not None:
                try:
                    after_close = os.stat(
                        source, dir_fd=source_fd, follow_symlinks=False
                    )
                except (OSError, ValueError, TypeError, RuntimeError) as error:
                    raise InitializationError(
                        "import physical file post-close status failed"
                    ) from error
                if (
                    not matches(after_close)
                    or after_close.st_ctime_ns != closed_receipt.st_ctime_ns
                    or after_close.st_nlink != closed_receipt.st_nlink
                ):
                    _fail("import physical file changed after descriptor close")


def _link_or_copy(source: str, destination: str) -> str:
    """Import a physical host file with checked hardlink receipts."""
    try:
        admitted = Path(source).lstat()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("import copy source status failed") from error
    if (
        type(admitted) is not os.stat_result
        or not stat.S_ISREG(admitted.st_mode)
    ):
        _fail("import copy source must be physical regular file")
    pinned_digest = _verified_import_file_digest(source, admitted)
    try:
        os.link(source, destination)
    except FileExistsError as error:
        raise InitializationError(
            f"import target already exists: {destination}"
        ) from error
    except OSError:
        try:
            with Path(source).open("rb") as input_stream:
                original = os.fstat(input_stream.fileno())
                if (
                    type(original) is not os.stat_result
                    or not stat.S_ISREG(original.st_mode)
                    or (original.st_dev, original.st_ino)
                    != (admitted.st_dev, admitted.st_ino)
                    or original.st_size != admitted.st_size
                    or original.st_mtime_ns != admitted.st_mtime_ns
                    or original.st_ctime_ns != admitted.st_ctime_ns
                ):
                    _fail("import copy source changed before transfer")
                with Path(destination).open("xb") as output_stream:
                    try:
                        named_before = Path(destination).lstat()
                        opened_before = os.fstat(output_stream.fileno())
                    except (
                        OSError, ValueError, TypeError, RuntimeError
                    ) as error:
                        raise InitializationError(
                            "import copy fallback output preflight failed"
                        ) from error
                    if (
                        type(named_before) is not os.stat_result
                        or type(opened_before) is not os.stat_result
                        or not stat.S_ISREG(named_before.st_mode)
                        or not stat.S_ISREG(opened_before.st_mode)
                        or named_before.st_size != 0
                        or opened_before.st_size != 0
                        or (named_before.st_dev, named_before.st_ino)
                        != (opened_before.st_dev, opened_before.st_ino)
                    ):
                        _fail("import copy fallback output descriptor mismatch")
                    _write_import_file_payload(
                        input_stream.fileno(), output_stream.fileno()
                    )
                    os.fchmod(output_stream.fileno(), stat.S_IMODE(original.st_mode))
                    finished = os.fstat(output_stream.fileno())
                    if (
                        type(finished) is not os.stat_result
                        or finished.st_size != original.st_size
                    ):
                        _fail("import copy fallback content length mismatch")
                    current = os.fstat(input_stream.fileno())
                    if (
                        type(current) is not os.stat_result
                        or not stat.S_ISREG(current.st_mode)
                        or (current.st_dev, current.st_ino)
                        != (original.st_dev, original.st_ino)
                        or current.st_size != original.st_size
                        or current.st_mtime_ns != original.st_mtime_ns
                        or current.st_ctime_ns != original.st_ctime_ns
                        or stat.S_IMODE(current.st_mode)
                        != stat.S_IMODE(original.st_mode)
                    ):
                        _fail("import copy source changed during transfer")
                try:
                    named_output = Path(destination).lstat()
                except (OSError, ValueError, TypeError, RuntimeError) as error:
                    raise InitializationError(
                        "import copy fallback output receipt failed"
                    ) from error
                if (
                    type(named_output) is not os.stat_result
                    or not stat.S_ISREG(named_output.st_mode)
                    or (named_output.st_dev, named_output.st_ino)
                    != (finished.st_dev, finished.st_ino)
                    or named_output.st_size != finished.st_size
                    or named_output.st_mtime_ns != finished.st_mtime_ns
                    or stat.S_IMODE(named_output.st_mode)
                    != stat.S_IMODE(finished.st_mode)
                ):
                    _fail("import copy fallback output changed after write")
                if (
                    _verified_import_file_digest(destination, named_output)
                    != pinned_digest
                    or _verified_import_file_digest(source, admitted) != pinned_digest
                ):
                    _fail("import copy fallback content changed after write")
        except FileExistsError as error:
            raise InitializationError(
                f"import target already exists: {destination}"
            ) from error
        except InitializationError:
            raise
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise InitializationError("import copy fallback failed") from error
    else:
        try:
            copied_source = Path(source).lstat()
            linked = Path(destination).lstat()
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise InitializationError("import link receipt failed") from error
        expected = (
            admitted.st_dev,
            admitted.st_ino,
            admitted.st_size,
            admitted.st_mtime_ns,
            stat.S_IMODE(admitted.st_mode),
        )
        for observed in (copied_source, linked):
            if (
                type(observed) is not os.stat_result
                or not stat.S_ISREG(observed.st_mode)
                or (
                    observed.st_dev,
                    observed.st_ino,
                    observed.st_size,
                    observed.st_mtime_ns,
                    stat.S_IMODE(observed.st_mode),
                ) != expected
            ):
                _fail("import link receipt changed source or destination")
        if _verified_import_file_digest(source, admitted) != pinned_digest:
            _fail("import link receipt changed source or destination content")
    return destination


type GitVersionRunner = Callable[[Path], str | None]
type GitExecPathRunner = Callable[[Path], Path | None]


def _optional_host_command_output(command: list[str]) -> str | None:
    """Admit bounded native process evidence from an optional Git/Rustup host probe.

    Returns:
        Captured nonempty native output only for the exact successful argv.

    """
    try:
        # jig-ignore-next-line: reviewed subprocess suppression is indivisible
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            command.copy(),
            check=False,
            capture_output=True,
            shell=False,
            text=True,
            timeout=15,
        )
    except (OSError, ValueError, TypeError, RuntimeError, subprocess.TimeoutExpired):
        return None
    if type(completed) is not subprocess.CompletedProcess:
        return None
    native = cast("subprocess.CompletedProcess[object]", completed)
    received = cast("object", native.args)
    if type(received) is not list:
        return None
    arguments = cast("list[object]", received)
    if (
        len(arguments) != len(command)
        or any(type(argument) is not str for argument in arguments)
        or arguments != command
        or type(native.returncode) is not int
        or native.returncode != 0
        or type(native.stdout) is not str
        or type(native.stderr) is not str
        or native.stderr
    ):
        return None
    if max(len(native.stdout), len(native.stderr)) > MAX_AUTHORITY_BYTES:
        return None
    output = native.stdout
    if output.endswith("\r\n"):
        output = output[:-2]
    elif output.endswith("\n"):
        output = output[:-1]
    return output or None


def _run_git_version(git: Path) -> str | None:
    return _optional_host_command_output([str(git), "--version"])


def _run_git_exec_path(git: Path) -> Path | None:
    output = _optional_host_command_output([str(git), "--exec-path"])
    if output is None or not output.isprintable():
        return None
    path = Path(output)
    if not path.is_absolute():
        return None
    try:
        directory = path.is_dir()
    except (OSError, ValueError, TypeError, RuntimeError):
        return None
    return path if type(directory) is bool and directory else None


def _configured_git_version(root: Path) -> str:
    path = root / ".jig/settings/versions.toml"
    document = _toml_document(path, "version authority")
    authority = _mapping(
        document.get("authority"),
        "version authority.authority",
    )
    git = _mapping(authority.get("git"), "version authority.authority.git")
    return _path_segment(
        _required_string(
            git,
            "current",
            "version authority.authority.git",
        ),
        "version authority.authority.git.current",
    )


def git_version_line_matches(required: str, version_line: str) -> bool:
    """Match exact upstream Git identity with an optional distribution suffix.

    Returns:
        True for the exact version or a dot-suffixed distribution build.

    """
    prefix = "git version "
    if not version_line.startswith(prefix):
        return False
    observed = version_line.removeprefix(prefix)
    if observed == required:
        return True
    distribution_prefix = f"{required}.windows."
    if not observed.startswith(distribution_prefix):
        return False
    suffix = observed.removeprefix(distribution_prefix)
    return re.fullmatch(r"[1-9][0-9]*", suffix) is not None


def _import_completion_marker_matches(marker: Path, expected: bytes) -> bool:
    """Read an exact owned regular marker, never a symlink or a FIFO.

    Returns:
        True only for bounded, unchanged completion bytes from one inode.

    """
    try:
        observed = marker.lstat()
        if (
            type(observed) is not os.stat_result
            or not stat.S_ISREG(observed.st_mode)
            or observed.st_nlink != 1
            or observed.st_size != len(expected)
        ):
            return False
        identity = _authority_identity(observed)
        matches = _read_authority_bytes(marker) == expected
        current = marker.lstat()
        return (
            matches
            and type(current) is os.stat_result
            and current.st_nlink == 1
            and _authority_identity(current) == identity
        )
    except OSError, ValueError, RuntimeError:
        return False


def _git_helper_tree_ready(git_root: Path) -> bool:
    """Require the completed helper tree to remain physical and in place."""
    helpers = git_root / "libexec/git-core"
    try:
        _reject_authority_parent_redirects(helpers)
        observed = helpers.lstat()
    except (InitializationError, OSError, ValueError, TypeError, RuntimeError):
        return False
    return type(observed) is os.stat_result and stat.S_ISDIR(observed.st_mode)


def git_import_complete(git_root: Path) -> bool:
    """Return whether one imported Git installation reached its final marker.

    Returns:
        True only when a stable, unlinked marker has exact expected bytes.

    """
    return _import_completion_marker_matches(
        git_root / GIT_IMPORT_MARKER,
        b"malbolge-git-import/v1\n",
    )


def _open_import_marker_parent(marker: Path) -> int:
    """Pin an existing physical marker parent before exclusive creation."""
    parent = marker.parent
    try:
        _reject_authority_parent_redirects(marker)
        before = parent.lstat()
        if type(before) is not os.stat_result or not stat.S_ISDIR(before.st_mode):
            _fail("import marker parent must be a physical directory")
        return _open_local_state_parent(
            parent, expected_identity=(before.st_dev, before.st_ino)
        )
    except InitializationError as error:
        raise InitializationError(
            "import marker parent changed before creation"
        ) from error
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("cannot open import marker parent") from error


def _require_import_marker_parent(marker: Path, descriptor: int) -> None:
    """Recheck the opened parent identity, not just its pathname."""
    try:
        _require_local_state_parent_identity(marker.parent, descriptor)
    except InitializationError as error:
        raise InitializationError(
            "import marker parent changed during creation"
        ) from error


def _import_marker_leaf_status(marker: Path, parent_fd: int | None) -> os.stat_result:
    if parent_fd is None:
        return marker.lstat()
    return os.stat(marker.name, dir_fd=parent_fd, follow_symlinks=False)


def _write_import_completion_marker(marker: Path, content: str) -> None:
    """Create a complete physical import marker without following a linked leaf."""
    parent_fd = _open_import_marker_parent(marker) if os.name == "posix" else None
    try:
        _write_import_completion_marker_at_parent(marker, content, parent_fd)
    except BaseException:
        if parent_fd is not None:
            with suppress(OSError, ValueError, TypeError, RuntimeError):
                os.close(parent_fd)
        raise
    if parent_fd is not None:
        try:
            os.close(parent_fd)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise InitializationError("import marker parent close failed") from error
    if not _import_completion_marker_matches(marker, content.encode("ascii")):
        _fail("import marker changed after parent close")


def _write_import_completion_marker_at_parent(
    marker: Path, content: str, parent_fd: int | None, *, executable: bool = False
) -> None:
    """Publish marker bytes through the owned parent descriptor when possible."""
    _reject_authority_parent_redirects(marker)
    if type(content) is not str:
        _fail("import marker requires native text")
    try:
        payload = content.encode("ascii")
    except UnicodeEncodeError as error:
        raise InitializationError("import marker requires ASCII text") from error
    try:
        _ = marker.lstat()
    except FileNotFoundError:
        pass
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("cannot inspect import marker") from error
    else:
        _fail("import marker already exists")
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_BINARY", 0)
    )
    try:
        if parent_fd is None:
            descriptor = os.open(marker, flags, 0o600)
        else:
            _require_import_marker_parent(marker, parent_fd)
            descriptor = os.open(marker.name, flags, 0o600, dir_fd=parent_fd)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("import marker creation failed") from error
    if type(descriptor) is not int or descriptor < 0:
        _fail("import marker returned invalid descriptor")
    owned: tuple[int, int] | None = None
    complete = False
    try:
        try:
            opened = os.fstat(descriptor)
            physical = _import_marker_leaf_status(marker, parent_fd)
            if (
                type(opened) is not os.stat_result
                or type(physical) is not os.stat_result
                or not stat.S_ISREG(opened.st_mode)
                or not stat.S_ISREG(physical.st_mode)
                or opened.st_nlink != 1
                or opened.st_size != 0
                or physical.st_size != 0
                or (opened.st_dev, opened.st_ino) != (physical.st_dev, physical.st_ino)
            ):
                _fail("import marker descriptor does not own physical leaf")
            owned = opened.st_dev, opened.st_ino
            if parent_fd is not None:
                _require_import_marker_parent(marker, parent_fd)
            if executable:
                os.fchmod(descriptor, 0o700)
            written = os.write(descriptor, payload)
            if type(written) is not int or written != len(payload):
                _fail("import marker short or invalid byte count")
            finished = os.fstat(descriptor)
            published = _import_marker_leaf_status(marker, parent_fd)
            if (
                type(finished) is not os.stat_result
                or type(published) is not os.stat_result
                or not stat.S_ISREG(published.st_mode)
                or finished.st_nlink != 1
                or finished.st_size != len(payload)
                or (executable and not finished.st_mode & stat.S_IXUSR)
                or (finished.st_dev, finished.st_ino) != owned
                or (published.st_dev, published.st_ino) != owned
            ):
                _fail("import marker changed during publication")
            if parent_fd is not None:
                _require_import_marker_parent(marker, parent_fd)
            if _read_authority_bytes(marker) != payload:
                _fail("import marker content mismatch")
            if parent_fd is not None:
                _require_import_marker_parent(marker, parent_fd)
            complete = True
        except InitializationError:
            raise
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise InitializationError("import marker write failed") from error
    finally:
        try:
            os.close(descriptor)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            complete = False
            raise InitializationError("import marker close failed") from error
        finally:
            if not complete and owned is not None:
                try:
                    physical = _import_marker_leaf_status(marker, parent_fd)
                    if (
                        type(physical) is os.stat_result
                        and (physical.st_dev, physical.st_ino) == owned
                    ):
                        if parent_fd is None:
                            marker.unlink()
                        else:
                            os.unlink(marker.name, dir_fd=parent_fd)
                except (OSError, ValueError, TypeError, RuntimeError):
                    pass


def _admit_import_destination(destination: Path, component: str) -> None:
    """Require a physically absent import root under nonredirected parents."""
    _reject_authority_parent_redirects(destination)
    try:
        physical = destination.lstat()
    except FileNotFoundError:
        return
    if type(physical) is not os.stat_result:
        _fail(f"{component} import destination requires native file status")
    _fail(f"{component} import destination already exists: {destination}")


def _find_physical_import_ancestor(
    parent: Path,
) -> tuple[Path, list[Path], tuple[int, int]]:
    """Find the first physical ancestor and the absent children below it.

    Returns:
        Ancestor path, absent descendant paths and native directory identity.

    """
    absent: list[Path] = []
    while True:
        try:
            observed = parent.lstat()
        except FileNotFoundError:
            absent.append(parent)
            parent = parent.parent
            continue
        if type(observed) is not os.stat_result or not stat.S_ISDIR(
            observed.st_mode
        ):
            _fail("import destination ancestor must be a physical directory")
        return parent, absent, (observed.st_dev, observed.st_ino)


def _create_posix_import_root(destination: Path, component: str) -> int:
    """Create an absent root via the originally opened physical ancestor.

    Returns:
        Descriptor of the newly created directory, owned by the caller.

    """
    _reject_authority_parent_redirects(destination)
    ancestor, absent, identity = _find_physical_import_ancestor(
        destination.parent
    )
    parent_fd = _open_local_state_parent(ancestor, expected_identity=identity)
    try:
        _admit_import_destination(destination, component)
        for child in reversed(absent):
            _require_local_state_parent_identity(ancestor, parent_fd)
            os.mkdir(child.name, dir_fd=parent_fd)
            _require_local_state_parent_identity(ancestor, parent_fd)
            nested_fd = _open_local_state_parent(child)
            previous_fd = parent_fd
            parent_fd = nested_fd
            _close_local_state_parent(previous_fd)
            ancestor = child
        _require_local_state_parent_identity(ancestor, parent_fd)
        os.mkdir(destination.name, dir_fd=parent_fd)
        _require_local_state_parent_identity(ancestor, parent_fd)
        return _open_local_state_parent(destination)
    finally:
        _close_local_state_parent(parent_fd)


def _pinned_import_root_identity(descriptor: int) -> tuple[int, int]:
    """Retain the physical import root identity across its final close."""
    try:
        opened = os.fstat(descriptor)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("import root descriptor status failed") from error
    if type(opened) is not os.stat_result or not stat.S_ISDIR(opened.st_mode):
        _fail("import root descriptor must be a native directory")
    return opened.st_dev, opened.st_ino


def _require_import_root_after_close(
    destination: Path, expected: tuple[int, int]
) -> None:
    """A replacement root cannot inherit the published completion marker."""
    try:
        _reject_authority_parent_redirects(destination)
        current = destination.lstat()
    except (InitializationError, OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("import root changed after directory close") from error
    if (
        type(current) is not os.stat_result
        or not stat.S_ISDIR(current.st_mode)
        or (current.st_dev, current.st_ino) != expected
    ):
        _fail("import root changed after directory close")


def _write_import_file_payload(input_fd: int, output_fd: int) -> None:
    """Write all source bytes to the opened destination descriptor."""
    while content := os.read(input_fd, 1_048_576):
        remaining = memoryview(content)
        while remaining:
            written = os.write(output_fd, remaining)
            if type(written) is not int or written <= 0:
                _fail("import file copy byte count invalid")
            remaining = remaining[written:]


def _open_verified_import_input(
    source: Path | str, source_fd: int | None, original: os.stat_result
) -> int:
    """Open the same physical regular file observed before hardlink failure.

    Returns:
        File descriptor whose ownership transfers to the caller.

    """
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    input_fd = os.open(source, flags, dir_fd=source_fd)
    try:
        opened = os.fstat(input_fd)
        if type(opened) is not os.stat_result or not stat.S_ISREG(
            opened.st_mode
        ):
            _fail("import source changed before copy")
        if (opened.st_dev, opened.st_ino) != (original.st_dev, original.st_ino):
            _fail("import source changed before copy")
    except BaseException:
        os.close(input_fd)
        raise
    return input_fd


def _copy_import_file_contents(
    input_fd: int, destination: Path, parent_fd: int
) -> tuple[int, int]:
    """Copy opened file bytes to a pinned destination descriptor.

    Returns:
        Native identity of the newly written destination file.

    """
    opened = os.fstat(input_fd)
    output_fd = os.open(
        destination.name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
        dir_fd=parent_fd,
    )
    try:
        _write_import_file_payload(input_fd, output_fd)
        os.fchmod(output_fd, stat.S_IMODE(opened.st_mode))
        copied = os.fstat(output_fd)
        if type(copied) is not os.stat_result:
            _fail("import file copy size mismatch")
        if copied.st_size != opened.st_size:
            _fail("import file copy size mismatch")
        return copied.st_dev, copied.st_ino
    finally:
        os.close(output_fd)


def _verify_import_source_unchanged(
    source: Path | str,
    source_fd: int | None,
    original: os.stat_result,
    *,
    hardlinked: bool,
) -> os.stat_result:
    """Return verified host source status, allowing a hardlink's ctime update."""
    current = os.stat(source, dir_fd=source_fd, follow_symlinks=False)
    if (
        type(current) is not os.stat_result
        or not stat.S_ISREG(current.st_mode)
        or (current.st_dev, current.st_ino) != (original.st_dev, original.st_ino)
        or current.st_size != original.st_size
        or current.st_mtime_ns != original.st_mtime_ns
        or stat.S_IMODE(current.st_mode) != stat.S_IMODE(original.st_mode)
        or (not hardlinked and current.st_ctime_ns != original.st_ctime_ns)
    ):
        _fail("import file changed during copy")
    return current


def _verify_import_destination_unchanged(
    destination: Path,
    parent_fd: int,
    original: os.stat_result,
    *,
    copied_inode: tuple[int, int],
) -> None:
    """Reject an import target whose identity or size changed after copying."""
    observed = os.stat(
        destination.name, dir_fd=parent_fd, follow_symlinks=False
    )
    if type(observed) is not os.stat_result or not stat.S_ISREG(
        observed.st_mode
    ):
        _fail("import file changed during copy")
    if (observed.st_dev, observed.st_ino) != copied_inode:
        _fail("import file changed during copy")
    if observed.st_size != original.st_size:
        _fail("import file changed during copy")


def _link_or_copy_import_file(
    source: Path | str,
    destination: Path,
    parent_fd: int,
    *,
    source_fd: int | None,
) -> None:
    """Copy a regular host file with identity checks on both physical roots."""
    _require_local_state_parent_identity(destination.parent, parent_fd)
    original = os.stat(source, dir_fd=source_fd, follow_symlinks=False)
    if type(original) is not os.stat_result or not stat.S_ISREG(
        original.st_mode
    ):
        _fail("import source file must be physical")
    pinned_digest = _verified_import_file_digest(source, original, source_fd=source_fd)
    copied_inode = original.st_dev, original.st_ino
    hardlinked = True
    try:
        os.link(
            source,
            destination.name,
            src_dir_fd=source_fd,
            dst_dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except OSError:
        hardlinked = False
        input_fd = _open_verified_import_input(source, source_fd, original)
        try:
            copied_inode = _copy_import_file_contents(
                input_fd, destination, parent_fd
            )
        finally:
            os.close(input_fd)
    _ = _verify_import_source_unchanged(
        source, source_fd, original, hardlinked=hardlinked
    )
    _verify_import_destination_unchanged(
        destination, parent_fd, original, copied_inode=copied_inode
    )
    if (
        _verified_import_file_digest(source, original, source_fd=source_fd)
        != pinned_digest
    ):
        _fail("import file changed during copy")
    if not hardlinked:
        copied = os.stat(destination.name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            type(copied) is not os.stat_result
            or (copied.st_dev, copied.st_ino) != copied_inode
            or _verified_import_file_digest(
                destination.name, copied, source_fd=parent_fd
            )
            != pinned_digest
        ):
            _fail("import file changed during copy")
    _require_local_state_parent_identity(destination.parent, parent_fd)


def _copy_import_file_at_parent(
    source: Path | str,
    destination: Path,
    parent_fd: int,
    *,
    source_fd: int | None = None,
) -> None:
    """Copy or hardlink a regular host file into a pinned physical directory.

    Raises:
        InitializationError: If the source or destination ceases to be owned.

    """
    try:
        _link_or_copy_import_file(
            source, destination, parent_fd, source_fd=source_fd
        )
    except InitializationError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        detail = "import file copy failed"
        raise InitializationError(detail) from error


def _copy_import_tree_at_parent(
    source: Path, destination: Path, destination_fd: int
) -> None:
    """Copy a tree through an anchored import root descriptor.

    Raises:
        InitializationError: If the source cannot be opened as a directory.

    """
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        # The source root may be a legitimate host-managed directory alias.
        source_fd = os.open(source, flags & ~getattr(os, "O_NOFOLLOW", 0))
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        detail = "cannot open physical import source tree"
        raise InitializationError(detail) from error
    try:
        _copy_import_members_at_parent(source_fd, destination, destination_fd)
    finally:
        _close_local_state_parent(source_fd)


def _open_posix_import_child(parent: Path, descriptor: int, name: str) -> int:
    """Create and open a new import child through the original parent.

    Returns:
        Native descriptor of the newly created directory.

    """
    _require_local_state_parent_identity(parent, descriptor)
    os.mkdir(name, dir_fd=descriptor)
    _require_local_state_parent_identity(parent, descriptor)
    return _open_local_state_parent(parent / name)


def _copy_import_directory_member(
    source_fd: int,
    destination_fd: int,
    *,
    target: Path,
    original: os.stat_result,
) -> None:
    """Recurse into an identity-checked physical source directory."""
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    os.mkdir(target.name, 0o700, dir_fd=destination_fd)
    nested_source_fd = os.open(target.name, flags, dir_fd=source_fd)
    try:
        nested_destination_fd = _open_local_state_parent(target)
        try:
            actual = os.fstat(nested_source_fd)
            if type(actual) is not os.stat_result or (
                actual.st_dev,
                actual.st_ino,
            ) != (original.st_dev, original.st_ino):
                _fail("import source directory changed")
            _copy_import_members_at_parent(
                nested_source_fd, target, nested_destination_fd
            )
            os.fchmod(nested_destination_fd, stat.S_IMODE(original.st_mode))
        finally:
            _close_local_state_parent(nested_destination_fd)
    finally:
        _close_local_state_parent(nested_source_fd)


def _copy_import_symlink_member(
    source_fd: int,
    destination_fd: int,
    *,
    target: Path,
    original: os.stat_result,
) -> None:
    """Preserve a host symlink only while its source identity is unchanged."""
    link = os.readlink(target.name, dir_fd=source_fd)
    if type(link) is not str:
        _fail("import source link requires native target")
    current = os.stat(target.name, dir_fd=source_fd, follow_symlinks=False)
    if type(current) is not os.stat_result or (
        current.st_dev,
        current.st_ino,
    ) != (original.st_dev, original.st_ino):
        _fail("import source link changed during copy")
    os.symlink(link, target.name, dir_fd=destination_fd)


def _copy_import_tree_member(
    source_fd: int,
    destination_fd: int,
    *,
    target: Path,
    original: os.stat_result,
) -> None:
    """Import one source member without following its destination pathname."""
    if stat.S_ISDIR(original.st_mode):
        _copy_import_directory_member(
            source_fd, destination_fd, target=target, original=original
        )
    elif stat.S_ISLNK(original.st_mode):
        _copy_import_symlink_member(
            source_fd, destination_fd, target=target, original=original
        )
    elif stat.S_ISREG(original.st_mode):
        _copy_import_file_at_parent(
            target.name, target, destination_fd, source_fd=source_fd
        )
    else:
        _fail("import source tree requires regular files and links")


def _copy_scanned_import_member(
    source_fd: int,
    destination: Path,
    destination_fd: int,
    *,
    member: os.DirEntry[str],
) -> None:
    """Validate and copy one native directory entry into an anchored root."""
    if type(member) is not os.DirEntry or type(member.name) is not str:
        _fail("import source requires native directory members")
    name = member.name
    if not name or name in {".", ".."} or os.sep in name:
        _fail("import source has invalid member name")
    original = os.stat(name, dir_fd=source_fd, follow_symlinks=False)
    if type(original) is not os.stat_result:
        _fail("import source requires native member status")
    _require_local_state_parent_identity(destination, destination_fd)
    _copy_import_tree_member(
        source_fd, destination_fd, target=destination / name, original=original
    )
    _require_local_state_parent_identity(destination, destination_fd)


def _copy_import_members_at_parent(
    source_fd: int, destination: Path, destination_fd: int
) -> None:
    """Recurse through descriptor-relative source and destination members.

    Raises:
        InitializationError: If a directory or member changes during copying.

    """
    try:
        _require_local_state_parent_identity(destination, destination_fd)
        with os.scandir(source_fd) as members:
            for member in members:
                _copy_scanned_import_member(
                    source_fd, destination, destination_fd, member=member
                )
    except InitializationError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        detail = "import source tree copy failed"
        raise InitializationError(detail) from error


def _copy_posix_git_binary(
    git: Path, destination: Path, root_fd: int, *, windows: bool
) -> None:
    """Populate Git bin via the descriptor-bound physical root."""
    bin_fd = _open_posix_import_child(destination, root_fd, "bin")
    try:
        native_name = "git.exe" if windows else "git"
        native = destination / "bin" / native_name
        _copy_import_file_at_parent(git, native, bin_fd)
        _copy_import_file_at_parent(
            native.name, destination / "bin/git.bin", bin_fd, source_fd=bin_fd
        )
    finally:
        _close_local_state_parent(bin_fd)


def _copy_posix_git_helpers(
    exec_path: Path, destination: Path, root_fd: int
) -> None:
    """Populate Git helper tree without following an exchanged root path."""
    libexec = destination / "libexec"
    libexec_fd = _open_posix_import_child(destination, root_fd, "libexec")
    try:
        git_core_fd = _open_posix_import_child(
            libexec, libexec_fd, "git-core"
        )
    finally:
        _close_local_state_parent(libexec_fd)
    try:
        _copy_import_tree_at_parent(
            exec_path, libexec / "git-core", git_core_fd
        )
    finally:
        _close_local_state_parent(git_core_fd)


def _import_posix_git_installation(
    git: Path, exec_path: Path, destination: Path, *, windows: bool
) -> None:
    """Use one pinned POSIX destination root for the full Git import."""
    root_fd = _create_posix_import_root(destination, "Git")
    try:
        expected_root = _pinned_import_root_identity(root_fd)
        _copy_posix_git_binary(git, destination, root_fd, windows=windows)
        _copy_posix_git_helpers(exec_path, destination, root_fd)
        _write_import_completion_marker_at_parent(
            destination / GIT_IMPORT_MARKER,
            "malbolge-git-import/v1\n",
            root_fd,
        )
    finally:
        _close_local_state_parent(root_fd)
    _require_import_root_after_close(destination, expected_root)


def _import_portable_git_installation(
    git: Path, exec_path: Path, destination: Path, *, windows: bool
) -> None:
    """Preserve the non-POSIX Git import fallback."""
    _admit_import_destination(destination, "Git")
    destination.mkdir(parents=True, exist_ok=False)
    native_name = "git.exe" if windows else "git"
    native = destination / "bin" / native_name
    native.parent.mkdir(parents=True)
    _ = _link_or_copy(str(git), str(native))
    _ = _link_or_copy(str(native), str(destination / "bin/git.bin"))
    _ = shutil.copytree(
        exec_path,
        destination / "libexec" / "git-core",
        copy_function=_link_or_copy,
        symlinks=True,
    )
    _write_import_completion_marker(
        destination / GIT_IMPORT_MARKER,
        "malbolge-git-import/v1\n",
    )


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
    if _supports_pinned_local_state_directories():
        _import_posix_git_installation(
            git, exec_path, destination, windows=windows
        )
    else:
        _import_portable_git_installation(
            git, exec_path, destination, windows=windows
        )
    if not git_import_complete(destination):
        _fail("Git import marker changed after root close")
    return destination / "bin/git.bin"


def _optional_host_executable(executable_name: str) -> Path | None:
    """Admit only a native nonempty PATH resolver result."""
    try:
        resolved = which(executable_name)
    except (OSError, ValueError, TypeError, RuntimeError):
        return None
    if type(resolved) is not str or not resolved or not resolved.isprintable():
        return None
    executable = Path(resolved)
    return executable if executable.is_absolute() else None


def observe_host_git(platform_id: str) -> GitHostObservation | None:
    """Observe one native Git installation without making it authority.

    Returns:
        Complete host Git observation, otherwise None.

    """
    windows = _platform_family(platform_id, WINDOWS_SYSTEM)
    executable_name = "git.exe" if windows else "git"
    executable = _optional_host_executable(executable_name)
    if executable is None:
        return None
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
    if (
        git_import_complete(destination)
        and _imported_binary_alias_ready(
            alias, windows=_platform_family(platform_id, WINDOWS_SYSTEM)
        )
        and _git_helper_tree_ready(destination)
    ):
        return alias
    if destination.exists():
        _fail(f"incomplete Git import already exists: {destination}")
    admitted = (
        git_version_line_matches(required, observation.version_line)
        and observation.exec_path.is_dir()
    )
    if not admitted:
        return None
    windows = _platform_family(platform_id, WINDOWS_SYSTEM)
    return import_git_installation(
        observation.executable,
        observation.exec_path,
        destination,
        windows=windows,
    )


def rust_toolchain_import_complete(toolchain_root: Path) -> bool:
    """Return whether one imported toolchain reached its final marker.

    Returns:
        True only when a stable, unlinked marker has exact expected bytes.

    """
    return _import_completion_marker_matches(
        toolchain_root / RUST_IMPORT_MARKER,
        b"malbolge-rust-toolchain-import/v1\n",
    )


def _rust_linux_linker_environment(platform_id: str) -> str | None:
    variables = {
        "linux-x86_64": "CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER",
        "linux-aarch64": "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER",
    }
    return variables.get(platform_id)


def _rust_validation_tool_ids(toolchain_root: Path) -> tuple[str, ...]:
    if toolchain_root.name == RUST_NIGHTLY_CHANNEL:
        return ("cargo-clippy", "cargo-fmt")
    return ("cargo",)


def _publish_rust_adapter_file_at_parent(
    path: Path,
    payload: bytes,
    parent_fd: int,
    *,
    executable: bool = False,
    allow_hardlink: bool = False,
) -> None:
    """Replace an admitted adapter leaf through its original physical parent."""
    try:
        _require_local_state_parent_identity(path.parent, parent_fd)
        _admit_rust_adapter_write_target(path, allow_hardlink=allow_hardlink)
        try:
            os.unlink(path.name, dir_fd=parent_fd)
        except FileNotFoundError:
            pass
        _require_local_state_parent_identity(path.parent, parent_fd)
        _write_import_completion_marker_at_parent(
            path, payload.decode("ascii"), parent_fd, executable=executable
        )
        _require_local_state_parent_identity(path.parent, parent_fd)
    except InitializationError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("Rust adapter publication failed") from error


def _write_verified_rust_adapter_script(
    path: Path,
    script: str,
    *,
    parent_fd: int | None = None,
    allow_hardlink: bool = False,
) -> None:
    """Reject incomplete generated Rust wrapper source writes."""
    if parent_fd is not None:
        _publish_rust_adapter_file_at_parent(
            path,
            script.encode("ascii"),
            parent_fd,
            executable=True,
            allow_hardlink=allow_hardlink,
        )
        return
    written = path.write_text(
        script,
        encoding="ascii",
        newline="\n",
    )
    complete_count = type(written) is int and written == len(script)
    if complete_count:
        try:
            verified = _read_authority_bytes(path)
        except (
            InitializationError, OSError, ValueError, TypeError, RuntimeError
        ):
            verified = None
        if verified == script.encode("ascii"):
            return
    message = (
        "Rust adapter script content mismatch"
        if complete_count
        else "Rust adapter short or invalid character count"
    )
    try:
        path.unlink(missing_ok=True)
    except OSError as error:
        _fail(f"{message}; {error}")
    _fail(message)


def _rust_validation_alias_script(tool_id: str, linker_environment: str) -> str:
    """Return deterministic Linux Cargo validation wrapper source."""
    return (
        "\n".join((
            "#!/bin/sh",
            "tool_dir=${0%/*}",
            f'export {linker_environment}="$tool_dir/cc"',
            f'exec "$tool_dir/{tool_id}" "$@"',
        ))
        + "\n"
    )


def _write_rust_validation_alias(
    toolchain_root: Path,
    tool_id: str,
    linker_environment: str,
    *,
    parent_fd: int | None = None,
) -> Path:
    native = toolchain_root / "bin" / tool_id
    if not native.is_file():
        _fail(f"imported Rust validation tool is missing: {native}")
    alias = toolchain_root / "bin" / f"{tool_id}.bin"
    if parent_fd is None:
        alias.unlink(missing_ok=True)
    else:
        _require_local_state_parent_identity(alias.parent, parent_fd)
    script = _rust_validation_alias_script(tool_id, linker_environment)
    _write_verified_rust_adapter_script(
        alias, script, parent_fd=parent_fd, allow_hardlink=True
    )
    if parent_fd is None:
        alias.chmod(alias.stat().st_mode | stat.S_IXUSR)
    return alias


def _admit_rust_adapter_write_target(
    path: Path, *, allow_hardlink: bool = False
) -> None:
    _reject_authority_parent_redirects(path)
    if path.is_symlink() or path.is_junction():
        _fail(f"Rust adapter write target must not redirect: {path}")
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return
    if type(metadata) is not os.stat_result:
        _fail(f"Rust adapter write target requires native file status: {path}")
    if not stat.S_ISREG(metadata.st_mode):
        _fail(f"Rust adapter write target must be regular: {path}")
    if not allow_hardlink and metadata.st_nlink != 1:
        _fail(f"Rust adapter write target must not be hardlinked: {path}")


def _write_verified_rust_adapter_marker(
    marker: Path, *, parent_fd: int | None = None
) -> None:
    """Reject incomplete Linux Rust adapter readiness metadata."""
    if parent_fd is not None:
        _publish_rust_adapter_file_at_parent(
            marker, RUST_LINUX_ADAPTER_CONTENT, parent_fd
        )
        return
    written = marker.write_bytes(RUST_LINUX_ADAPTER_CONTENT)
    complete_count = (
        type(written) is int and written == len(RUST_LINUX_ADAPTER_CONTENT)
    )
    if complete_count:
        try:
            verified = _read_authority_bytes(marker)
        except (
            InitializationError, OSError, ValueError, TypeError, RuntimeError
        ):
            verified = None
        if verified == RUST_LINUX_ADAPTER_CONTENT:
            return
    message = (
        "Rust adapter marker content mismatch"
        if complete_count
        else "Rust adapter marker short or invalid byte count"
    )
    try:
        marker.unlink(missing_ok=True)
    except OSError as error:
        _fail(f"{message}; {error}")
    _fail(message)


def _rust_adapter_parent_identity(parent: Path) -> tuple[int, int]:
    """Capture an admitted physical toolchain directory before leaf validation."""
    try:
        _admit_local_directory(parent)
        observed = parent.lstat()
    except InitializationError as error:
        raise InitializationError("Rust adapter parent must not redirect") from error
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("cannot inspect Rust adapter parent") from error
    if type(observed) is not os.stat_result or not stat.S_ISDIR(observed.st_mode):
        _fail("Rust adapter parent must be physical")
    return observed.st_dev, observed.st_ino


def _rust_adapter_owned_leaf_identity(
    leaf: Path, parent_fd: int | None
) -> tuple[int, int]:
    """Capture a publisher-owned regular inode before closing its parent."""
    try:
        observed = _import_marker_leaf_status(leaf, parent_fd)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("Rust adapter published leaf missing") from error
    if (
        type(observed) is not os.stat_result
        or not stat.S_ISREG(observed.st_mode)
        or observed.st_nlink != 1
    ):
        _fail("Rust adapter published leaf changed during creation")
    return observed.st_dev, observed.st_ino


def _rust_adapter_outputs_ready(
    marker: Path,
    owned_marker: tuple[int, int],
    generated: tuple[tuple[Path, bytes, tuple[int, int]], ...],
) -> bool:
    """Reattest owned script inodes and bytes after closing both parents."""
    if (
        not _import_completion_marker_matches(marker, RUST_LINUX_ADAPTER_CONTENT)
        or _rust_adapter_owned_leaf_identity(marker, None) != owned_marker
    ):
        return False
    for script, payload, owned in generated:
        if not _import_completion_marker_matches(script, payload):
            return False
        try:
            observed = script.lstat()
            if (
                type(observed) is not os.stat_result
                or not observed.st_mode & stat.S_IXUSR
                or (observed.st_dev, observed.st_ino) != owned
            ):
                return False
        except (OSError, ValueError, TypeError, RuntimeError):
            return False
    return True


def _retire_owned_rust_adapter_marker(
    marker: Path,
    owned: tuple[int, int],
    root_identity: tuple[int, int] | None,
) -> None:
    """Invalidate only the original marker, never a swapped foreign leaf."""
    try:
        parent_fd = (
            _open_local_state_parent(marker.parent, expected_identity=root_identity)
            if root_identity is not None
            else None
        )
        try:
            if parent_fd is not None:
                _require_local_state_parent_identity(marker.parent, parent_fd)
            current = _import_marker_leaf_status(marker, parent_fd)
            if (
                type(current) is os.stat_result
                and stat.S_ISREG(current.st_mode)
                and current.st_nlink == 1
                and (current.st_dev, current.st_ino) == owned
            ):
                if parent_fd is None:
                    marker.unlink()
                else:
                    os.unlink(marker.name, dir_fd=parent_fd)
        finally:
            if parent_fd is not None:
                _close_local_state_parent(parent_fd)
    except (InitializationError, OSError, ValueError, TypeError, RuntimeError):
        pass


def _write_rust_toolchain_linker_adapters(
    toolchain_root: Path,
    linker_path: str,
    linker_environment: str,
) -> Path:
    adapter = toolchain_root / "bin" / "cc"
    marker = toolchain_root / RUST_LINUX_ADAPTER_MARKER
    tool_ids = _rust_validation_tool_ids(toolchain_root)
    aliases = tuple(toolchain_root / "bin" / f"{tool_id}.bin" for tool_id in tool_ids)
    adapter_script = f'#!/bin/sh\nexec {linker_path} "$@"\n'
    generated = ((adapter, adapter_script.encode("ascii")),) + tuple(
        (alias, _rust_validation_alias_script(tool_id, linker_environment).encode("ascii"))
        for tool_id, alias in zip(tool_ids, aliases, strict=True)
    )
    root_identity = (
        _rust_adapter_parent_identity(toolchain_root) if os.name == "posix" else None
    )
    bin_identity = (
        _rust_adapter_parent_identity(adapter.parent) if os.name == "posix" else None
    )
    _admit_rust_adapter_write_target(adapter)
    _admit_rust_adapter_write_target(marker)
    for alias in aliases:
        # Imported neutral aliases can hardlink native tools. They are unlinked
        # before writing wrapper scripts, so their source inodes are not edited.
        _admit_rust_adapter_write_target(alias, allow_hardlink=True)
    # Keep both original directory identities through every adapter write.
    # A physical rename/replacement is not detectable by path checks alone.
    root_fd = (
        _open_local_state_parent(toolchain_root, expected_identity=root_identity)
        if root_identity is not None
        else None
    )
    try:
        generated_identities: list[tuple[int, int]] = []
        bin_fd = (
            _open_local_state_parent(adapter.parent, expected_identity=bin_identity)
            if bin_identity is not None
        else None
        )
        try:
            if root_fd is not None:
                _require_local_state_parent_identity(toolchain_root, root_fd)
            _write_verified_rust_adapter_script(
                adapter, adapter_script, parent_fd=bin_fd
            )
            if bin_fd is None:
                adapter.chmod(adapter.stat().st_mode | stat.S_IXUSR)
            generated_identities.append(_rust_adapter_owned_leaf_identity(adapter, bin_fd))
            for tool_id in tool_ids:
                if root_fd is not None:
                    _require_local_state_parent_identity(toolchain_root, root_fd)
                alias = _write_rust_validation_alias(
                    toolchain_root,
                    tool_id,
                    linker_environment,
                    parent_fd=bin_fd,
                )
                generated_identities.append(_rust_adapter_owned_leaf_identity(alias, bin_fd))
            if root_fd is not None:
                _require_local_state_parent_identity(toolchain_root, root_fd)
            _write_verified_rust_adapter_marker(marker, parent_fd=root_fd)
            owned_marker = _rust_adapter_owned_leaf_identity(marker, root_fd)
        finally:
            if bin_fd is not None:
                _close_local_state_parent(bin_fd)
    finally:
        if root_fd is not None:
            _close_local_state_parent(root_fd)

    generated_receipts = tuple(
        (leaf, payload, owned)
        for (leaf, payload), owned in zip(generated, generated_identities, strict=True)
    )
    stable = _rust_adapter_outputs_ready(marker, owned_marker, generated_receipts)
    if root_identity is not None:
        try:
            _require_import_root_after_close(toolchain_root, root_identity)
            if bin_identity is not None:
                _require_import_root_after_close(adapter.parent, bin_identity)
        except InitializationError:
            stable = False
    if not stable:
        _retire_owned_rust_adapter_marker(marker, owned_marker, root_identity)
        _fail("Rust adapter generated outputs changed after parent close")
    return adapter


def write_rust_linker_adapters(
    toolchain_roots: tuple[Path, ...],
    platform_id: str,
    *,
    linker: Path | None = None,
) -> tuple[Path, ...]:
    """Bind imported Linux Rust validation to one explicit host linker.

    Returns:
        Repository-local linker adapter paths, or empty outside Linux.

    """
    linker_environment = _rust_linux_linker_environment(platform_id)
    if linker_environment is None:
        return ()
    selected = linker
    if selected is None:
        resolved = which("cc")
        if resolved is None:
            return ()
        selected = Path(resolved)
    linker_path = shlex.quote(str(selected.resolve()))
    return tuple(
        _write_rust_toolchain_linker_adapters(
            root,
            linker_path,
            linker_environment,
        )
        for root in toolchain_roots
    )


def _admit_rust_import_tool_ids(tool_ids: tuple[str, ...]) -> None:
    """Keep neutral Rust alias names to one unambiguous local path segment."""
    if type(tool_ids) is not tuple:
        _fail("imported Rust tool IDs must be a native tuple")
    for tool_id in tool_ids:
        if type(tool_id) is not str or not tool_id:
            _fail("imported Rust tool ID must be one repository-local path segment")
        _ = _path_segment(tool_id, "imported Rust tool ID")


def _rust_import_alias_status(path: Path, parent_fd: int | None) -> os.stat_result:
    if parent_fd is None:
        return path.lstat()
    return os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)


def _create_rust_import_alias_at_parent(
    native: Path, alias: Path, parent_fd: int, native_status: os.stat_result
) -> None:
    """Create a neutral alias inside the original physical imported bin directory."""
    _require_local_state_parent_identity(native.parent, parent_fd)
    expected = native_status.st_dev, native_status.st_ino
    created: tuple[int, int] | None = None
    complete = False
    source_status = native_status
    try:
        pinned_digest = _verified_import_file_digest(
            native.name, native_status, source_fd=parent_fd
        )
        try:
            os.link(
                native.name,
                alias.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
                follow_symlinks=False,
            )
            source_status = _verify_import_source_unchanged(
                native.name, parent_fd, native_status, hardlinked=True
            )
        except FileExistsError as error:
            raise InitializationError(
                "imported Rust alias appeared during creation"
            ) from error
        except OSError:
            source_fd = os.open(
                native.name,
                os.O_RDONLY
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_NONBLOCK", 0),
                dir_fd=parent_fd,
            )
            try:
                opened = os.fstat(source_fd)
                if (
                    type(opened) is not os.stat_result
                    or not stat.S_ISREG(opened.st_mode)
                    or (opened.st_dev, opened.st_ino) != expected
                ):
                    _fail("imported Rust native tool changed during alias creation")
                flags = (
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
                )
                target_fd = os.open(alias.name, flags, 0o600, dir_fd=parent_fd)
                try:
                    status = os.fstat(target_fd)
                    created = status.st_dev, status.st_ino
                    while content := os.read(source_fd, 1_048_576):
                        remaining = memoryview(content)
                        while remaining:
                            written = os.write(target_fd, remaining)
                            if type(written) is not int or written <= 0:
                                _fail("imported Rust alias short or invalid byte count")
                            remaining = remaining[written:]
                    os.fchmod(target_fd, opened.st_mode & 0o777)
                    finished = os.fstat(target_fd)
                    if (
                        type(finished) is not os.stat_result
                        or finished.st_size != opened.st_size
                    ):
                        _fail("imported Rust alias content length mismatch")
                finally:
                    os.close(target_fd)
                after_source = os.fstat(source_fd)
                if (
                    type(after_source) is not os.stat_result
                    or (after_source.st_dev, after_source.st_ino) != expected
                    or after_source.st_size != opened.st_size
                ):
                    _fail("imported Rust native tool changed during alias creation")
            finally:
                os.close(source_fd)
        if created is None:
            linked = _rust_import_alias_status(alias, parent_fd)
            if (
                type(linked) is not os.stat_result
                or not stat.S_ISREG(linked.st_mode)
                or (linked.st_dev, linked.st_ino) != expected
            ):
                _fail("imported Rust alias changed after hardlink creation")
            created = linked.st_dev, linked.st_ino
        _require_local_state_parent_identity(native.parent, parent_fd)
        observed = _rust_import_alias_status(alias, parent_fd)
        current = _rust_import_alias_status(native, parent_fd)
        if (
            type(observed) is not os.stat_result
            or not stat.S_ISREG(observed.st_mode)
            or (observed.st_dev, observed.st_ino) != created
            or type(current) is not os.stat_result
            or not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != expected
        ):
            _fail("imported Rust alias changed during creation")
        source_status = _verify_import_source_unchanged(
            native.name, parent_fd, source_status, hardlinked=False
        )
        if (
            _verified_import_file_digest(
                native.name, source_status, source_fd=parent_fd
            ) != pinned_digest
            or _verified_import_file_digest(
                alias.name, observed, source_fd=parent_fd
            ) != pinned_digest
        ):
            _fail("imported Rust alias content changed during creation")
        complete = True
    except InitializationError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise InitializationError("imported Rust alias creation failed") from error
    finally:
        if not complete and created is not None:
            try:
                observed = _rust_import_alias_status(alias, parent_fd)
                if (observed.st_dev, observed.st_ino) == created:
                    os.unlink(alias.name, dir_fd=parent_fd)
            except (OSError, ValueError, TypeError, RuntimeError):
                pass


def _ensure_rust_toolchain_aliases(
    toolchain_root: Path,
    tool_ids: tuple[str, ...],
    *,
    windows: bool,
    expected_bin_identity: tuple[int, int] | None = None,
    require_absent: bool = False,
) -> tuple[Path, ...]:
    """Materialize neutral executable aliases for imported Rust tools.

    Returns:
        Alias paths inside the imported native toolchain `bin` directory.

    """
    _admit_rust_import_tool_ids(tool_ids)
    suffix = ".exe" if windows else ""
    parent = toolchain_root / "bin"
    expected = (
        expected_bin_identity or _rust_adapter_parent_identity(parent)
        if _supports_pinned_local_state_directories()
        else None
    )
    parent_fd = (
        _open_local_state_parent(parent, expected_identity=expected)
        if expected is not None
        else None
    )
    aliases: list[Path] = []
    try:
        for tool_id in tool_ids:
            native = parent / f"{tool_id}{suffix}"
            alias = parent / f"{tool_id}.bin"
            _reject_authority_parent_redirects(native)
            if parent_fd is not None:
                _require_local_state_parent_identity(parent, parent_fd)
            try:
                native_status = _rust_import_alias_status(native, parent_fd)
            except FileNotFoundError:
                _fail(f"imported Rust tool is missing: {native}")
            if type(native_status) is not os.stat_result or not stat.S_ISREG(
                native_status.st_mode
            ):
                _fail(f"imported Rust tool must be physical: {native}")
            try:
                alias_status = _rust_import_alias_status(alias, parent_fd)
            except FileNotFoundError:
                if parent_fd is not None:
                    _create_rust_import_alias_at_parent(
                        native, alias, parent_fd, native_status
                    )
                else:
                    _ = _link_or_copy(str(native), str(alias))
                alias_status = _rust_import_alias_status(alias, parent_fd)
            else:
                if require_absent:
                    _fail(f"imported Rust alias already exists: {alias}")
            if type(alias_status) is not os.stat_result or not stat.S_ISREG(
                alias_status.st_mode
            ):
                _fail(f"imported Rust alias must be physical: {alias}")
            if parent_fd is not None:
                _require_local_state_parent_identity(parent, parent_fd)
            aliases.append(alias)
        return tuple(aliases)
    finally:
        if parent_fd is not None:
            _close_local_state_parent(parent_fd)


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
    _admit_rust_import_tool_ids(tool_ids)
    if _supports_pinned_local_state_directories():
        root_fd = _create_posix_import_root(destination, "Rust")
        try:
            expected_root = _pinned_import_root_identity(root_fd)
            _copy_import_tree_at_parent(source, destination, root_fd)
            try:
                bin_status = os.stat(
                    "bin", dir_fd=root_fd, follow_symlinks=False
                )
            except (OSError, ValueError, TypeError, RuntimeError) as error:
                detail = "imported Rust bin missing"
                raise InitializationError(detail) from error
            if (
                type(bin_status) is not os.stat_result
                or not stat.S_ISDIR(bin_status.st_mode)
            ):
                _fail("imported Rust bin must be a physical directory")
            aliases = _ensure_rust_toolchain_aliases(
                destination,
                tool_ids,
                windows=windows,
                expected_bin_identity=(bin_status.st_dev, bin_status.st_ino),
                require_absent=True,
            )
            _write_import_completion_marker_at_parent(
                destination / RUST_IMPORT_MARKER,
                "malbolge-rust-toolchain-import/v1\n",
                root_fd,
            )
        finally:
            _close_local_state_parent(root_fd)
        _require_import_root_after_close(destination, expected_root)
    else:
        _admit_import_destination(destination, "Rust")
        _ = shutil.copytree(
            source,
            destination,
            copy_function=_link_or_copy,
            symlinks=True,
        )
        aliases = _ensure_rust_toolchain_aliases(
            destination, tool_ids, windows=windows, require_absent=True
        )
        _write_import_completion_marker(
            destination / RUST_IMPORT_MARKER,
            "malbolge-rust-toolchain-import/v1\n",
        )
    if not rust_toolchain_import_complete(destination):
        _fail("Rust import marker changed after root close")
    return aliases


type RustToolchainResolver = Callable[[str], Path | None]
type RustupWhichRunner = Callable[[Path, str], str | None]
type RustupListRunner = Callable[[Path], tuple[str, ...]]


def _run_rustup_list(rustup: Path) -> tuple[str, ...]:
    output = _optional_host_command_output([str(rustup), "toolchain", "list"])
    if output is None:
        return ()
    normalized = output.replace("\r\n", "\n")
    if "\r" in normalized:
        return ()
    lines = normalized.split("\n")
    if any(
        not line or not line.isprintable() or line != line.strip()
        for line in lines
    ):
        return ()
    return tuple(line.split(maxsplit=1)[0] for line in lines)


def rustup_channel_is_installed(
    channel: str,
    installed: tuple[str, ...],
) -> bool:
    """Match a pinned channel against installed host-qualified forms.

    Returns:
        True when the exact channel or one host-qualified form is installed.

    """
    if (
        type(channel) is not str
        or type(installed) is not tuple
        or not all(type(item) is str for item in installed)
    ):
        return False
    prefix = f"{channel}-"
    return any(item == channel or item.startswith(prefix) for item in installed)


def _run_rustup_which(rustup: Path, channel: str) -> str | None:
    return _optional_host_command_output([
        str(rustup), "which", "--toolchain", channel, "cargo"
    ])


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
    try:
        raw = runner(rustup, channel)
    except (OSError, ValueError, TypeError, RuntimeError):
        return None
    if type(raw) is not str or not raw or not raw.isprintable():
        return None
    cargo = Path(raw)
    if (
        not cargo.is_absolute()
        or cargo.parent.name != "bin"
        or cargo.name not in {"cargo", "cargo.exe"}
    ):
        return None
    try:
        _reject_authority_parent_redirects(cargo)
        regular_file = cargo.is_file()
        physical = cargo.lstat()
    except (InitializationError, OSError, ValueError, TypeError, RuntimeError):
        return None
    if (
        type(regular_file) is not bool
        or not regular_file
        or type(physical) is not os.stat_result
        or not stat.S_ISREG(physical.st_mode)
    ):
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
    try:
        installed = list_runner(rustup)
    except (OSError, ValueError, TypeError, RuntimeError):
        installed = ()

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
    windows = _platform_family(platform_id, WINDOWS_SYSTEM)
    executable = "rustup.exe" if windows else "rustup"
    cargo_home = (home or Path.home()).absolute() / ".cargo" / "bin" / executable
    try:
        present = cargo_home.is_file()
    except (OSError, ValueError, TypeError, RuntimeError):
        present = False
    if type(present) is bool and present:
        return cargo_home
    if search_path:
        return _optional_host_executable(executable)
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
    windows = _platform_family(platform_id, WINDOWS_SYSTEM)
    requests = (
        (_rust_channel(root), ("cargo", "rustc")),
        (RUST_NIGHTLY_CHANNEL, ("cargo-clippy", "cargo-fmt")),
    )
    imported: list[Path] = []
    for channel, tool_ids in requests:
        destination = root / ".dependencies" / "rust" / channel
        if rust_toolchain_import_complete(destination):
            _ = _ensure_rust_toolchain_aliases(
                destination,
                tool_ids,
                windows=windows,
            )
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
    imported = import_installed_rust_toolchains(
        root,
        platform_id,
        resolver=rustup_toolchain_resolver(rustup),
    )
    _ = write_rust_linker_adapters(imported, platform_id)
    return imported


def _imported_cargo(root: Path, channel: str) -> Path:
    return root / ".dependencies" / "rust" / channel / "bin" / "cargo.bin"


def _imported_binary_alias_ready(alias: Path, *, windows: bool) -> bool:
    """Require a physical and, on POSIX, executable Git/Rust alias.

    Returns:
        False for missing, linked, nonregular, or nonexecutable paths.

    """
    try:
        _reject_authority_parent_redirects(alias)
        physical = alias.lstat()
        if type(physical) is not os.stat_result or not stat.S_ISREG(
            physical.st_mode
        ):
            return False
        if windows:
            return True
        if not physical.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            return False
        executable = os.access(alias, os.X_OK)
    except (InitializationError, OSError, ValueError, TypeError, RuntimeError):
        return False
    return type(executable) is bool and executable


def _canonical_linux_linker_script(content: bytes) -> bool:
    """Require the exact safe shell spelling generated for one absolute linker."""
    prefix = b"#!/bin/sh\nexec "
    suffix = b' "$@"\n'
    if (
        not content.startswith(prefix)
        or not content.endswith(suffix)
        or content.count(b"\n") != RUST_LINUX_ADAPTER_LINE_COUNT
    ):
        return False
    try:
        word = content[len(prefix) : -len(suffix)].decode("ascii")
        tokens = shlex.split(word, posix=True)
    except (UnicodeDecodeError, ValueError):
        return False
    return (
        len(tokens) == 1
        and Path(tokens[0]).is_absolute()
        and shlex.quote(tokens[0]) == word
    )


def _linux_adapter_script_ready(linker: Path) -> bool:
    """Validate one stable, physical and executable Linux linker shim.

    Returns:
        Whether the saved script has the generated direct-exec structure.

    """
    try:
        physical = linker.lstat()
        if (
            type(physical) is not os.stat_result
            or not stat.S_ISREG(physical.st_mode)
            or physical.st_nlink != 1
        ):
            return False
        identity = _authority_identity(physical)
        content = _read_authority_bytes(linker)
        current = linker.lstat()
        if (
            type(current) is not os.stat_result
            or current.st_nlink != 1
            or _authority_identity(current) != identity
        ):
            return False
        executable = os.access(linker, os.X_OK)
    except (InitializationError, OSError, ValueError, TypeError, RuntimeError):
        return False
    return (
        _canonical_linux_linker_script(content)
        and bool(current.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
        and type(executable) is bool
        and executable
    )


def _rust_validation_adapter_ready(
    toolchain_root: Path,
    platform_id: str,
) -> bool:
    if not _platform_family(platform_id, LINUX_SYSTEM):
        return True
    linker = toolchain_root / "bin" / "cc"
    marker = toolchain_root / RUST_LINUX_ADAPTER_MARKER
    return _import_completion_marker_matches(
        marker, RUST_LINUX_ADAPTER_CONTENT
    ) and _linux_adapter_script_ready(linker)


def inspect_rust(root: Path, platform_id: str) -> ComponentStatus:
    """Inspect the pinned Rust channel and imported neutral Cargo alias.

    Returns:
        Ready only for a completed repository-local imported toolchain.

    """
    toolchain_path = root / ".jig/version/rust-toolchain.toml"
    channel = _rust_channel(root)
    cargo = _imported_cargo(root, channel)
    imported_root = cargo.parent.parent
    imported = _imported_binary_alias_ready(
        cargo, windows=_platform_family(platform_id, WINDOWS_SYSTEM)
    ) and rust_toolchain_import_complete(imported_root)
    linker_ready = _rust_validation_adapter_ready(
        imported_root,
        platform_id,
    )
    if imported and linker_ready:
        path: Path | None = cargo
        detail = f"pinned Cargo for {channel} is present"
        state = ComponentState.READY
    else:
        path = toolchain_path
        detail = f"Cargo/linker for pinned channel {channel} is absent"
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
    executable = "jig.cmd" if _platform_family(platform_id, WINDOWS_SYSTEM) else "jig"
    try:
        resolved = which(executable)
    except (OSError, ValueError, TypeError, RuntimeError):
        resolved = None
    if type(resolved) is str and resolved.isprintable():
        path = Path(resolved)
        if path.is_absolute():
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


def _llvm_status(root: Path, platform_id: str) -> ComponentStatus:
    observed = llvm_validation.inspect_llvm(root, platform_id)
    return ComponentStatus(
        detail=observed.detail,
        name="llvm",
        path=observed.path,
        state=(
            ComponentState.READY if observed.ready else ComponentState.MISSING
        ),
    )


def _prepare_linux_llvm(
    root: Path,
    linux_observer: (
        Callable[[], llvm_validation.LlvmHostObservation | None] | None
    ),
) -> None:
    observe = linux_observer or llvm_validation.observe_linux_llvm_host
    observation = observe()
    if observation is not None:
        _ = llvm_validation.import_linux_llvm(root, observation)


def _prepare_windows_llvm(root: Path) -> None:
    llvm_root = root / llvm_validation.LLVM_ROOT
    if (llvm_root / "bin/clang.exe").is_file():
        _ = llvm_validation.write_windows_llvm_aliases(llvm_root)


def _prepare_llvm_platform(
    root: Path,
    platform_id: str,
    linux_observer: (
        Callable[[], llvm_validation.LlvmHostObservation | None] | None
    ),
) -> None:
    if platform_id == llvm_validation.LINUX_PLATFORM:
        _prepare_linux_llvm(root, linux_observer)
    elif platform_id == llvm_validation.WINDOWS_PLATFORM:
        _prepare_windows_llvm(root)


def prepare_llvm(
    root: Path,
    platform_id: str,
    *,
    linux_observer: (
        Callable[[], llvm_validation.LlvmHostObservation | None] | None
    ) = None,
) -> ComponentStatus:
    """Prepare exact neutral LLVM aliases when an admitted host is available.

    Returns:
        Repository-local LLVM readiness after optional exact host import.

    """
    try:
        _prepare_llvm_platform(root, platform_id, linux_observer)
    except llvm_validation.LlvmImportError as error:
        return ComponentStatus(
            detail=f"exact LLVM import failed: {_native_exception_detail(error)}",
            name="llvm",
            path=root / llvm_validation.LLVM_ROOT,
            state=ComponentState.MISSING,
        )
    return _llvm_status(root, platform_id)


def inspect_llvm_development(
    root: Path,
    platform_id: str,
) -> ComponentStatus:
    """Inspect exact Linux native-analysis development package readiness.

    Returns:
        Ready, missing, or unsupported development-kit status.

    """
    if platform_id != llvm_validation.LINUX_PLATFORM:
        return ComponentStatus(
            detail="exact LLVM development provisioning is Linux x86-64 only",
            name="llvm-development",
            path=None,
            state=ComponentState.UNSUPPORTED,
        )
    path = llvm_development_validation.linux_development_root(root)
    ready = llvm_development_validation.linux_development_ready(root)
    return ComponentStatus(
        detail=(
            "exact LLVM development kit is present"
            if ready
            else "exact LLVM development kit is absent"
        ),
        name="llvm-development",
        path=path,
        state=ComponentState.READY if ready else ComponentState.MISSING,
    )


def provision_llvm_development_if_requested(
    root: Path,
    platform_id: str,
    *,
    requested: bool,
    provisioner: Callable[[Path], Path] | None = None,
) -> Path | None:
    """Provision exact Linux LLVM development packages only after opt-in.

    Returns:
        Exact development root, or ``None`` when provisioning was not asked.

    """
    if not requested:
        return None
    if platform_id != llvm_validation.LINUX_PLATFORM:
        _fail("LLVM development provisioning supports only linux-x86_64")
    selected = (
        provisioner or llvm_development_validation.provision_linux_development
    )
    try:
        return selected(root)
    except llvm_development_validation.LlvmDevelopmentProvisionError as error:
        message = "cannot provision LLVM development kit: "
        raise InitializationError(message + _native_exception_detail(error)) from error


def provision_cuda_if_requested(
    root: Path,
    platform_id: str,
    *,
    requested: bool,
    provisioner: Callable[[Path, Path, str], Path] | None = None,
) -> Path | None:
    """Provision the selected CUDA manifest only after explicit opt-in.

    Returns:
        Provisioned toolkit root, or ``None`` when provisioning was not asked.

    """
    if not requested:
        return None
    manifest_path = cuda_toolchain_manifest_path(root, platform_id)
    if manifest_path is None:
        _fail(f"no tracked CUDA toolchain manifest for {platform_id}")
    selected = provisioner or cuda_validation.provision_cuda_manifest
    try:
        return selected(root, manifest_path, platform_id)
    except cuda_validation.CudaProvisionError as error:
        raise InitializationError(
            f"cannot provision CUDA: {_native_exception_detail(error)}"
        ) from error


def initialize_project(
    root: Path = ROOT,
    *,
    provision_python: bool = True,
    require_cuda: bool = False,
    provisions: ProvisionRequests = NO_PROVISION_REQUESTS,
) -> ProjectInitializationReport:
    """Initialize local state and report optional toolchain readiness.

    Returns:
        Complete checkout initialization report.

    """
    # Pin the selected checkout before any provisioner can change process cwd.
    root = root.absolute()
    validate_repository(root)
    directories = initialize_local_directories(root)
    layout = (
        python_validation.initialize(root)
        if provision_python
        else python_validation.validation_layout(root)
    )
    platform_id = host_platform_id()
    _ = provision_llvm_development_if_requested(
        root,
        platform_id,
        requested=provisions.llvm_development,
    )
    _ = provision_cuda_if_requested(
        root,
        platform_id,
        requested=provisions.cuda,
    )
    observation = observe_host_git(platform_id)
    if observation is not None:
        _ = import_host_git(root, platform_id, observation)
    _ = import_host_rust_toolchains(root, platform_id)
    cuda = inspect_cuda(root, platform_id)
    rust = inspect_rust(root, platform_id)
    jig = inspect_jig(root, platform_id)
    llvm = prepare_llvm(root, platform_id)
    llvm_development = inspect_llvm_development(root, platform_id)
    if require_cuda and cuda.state is not ComponentState.READY:
        _fail(f"CUDA is required but {cuda.state}: {cuda.detail}")
    return ProjectInitializationReport(
        cuda=cuda,
        directories=directories,
        jig=jig,
        llvm=llvm,
        llvm_development=llvm_development,
        platform_id=platform_id,
        python_environment=layout.environment,
        python_provisioned=provision_python,
        rust=rust,
    )


def render_report(report: ProjectInitializationReport) -> str:
    """Render a stable human-readable initialization report.

    Returns:
        Newline-terminated report text.

    """
    python_state = (
        "ready" if report.python_provisioned else "skipped (--skip-python; not verified)"
    )
    lines = [
        f"project initialized for {report.platform_id}",
        f"python: {python_state} ({report.python_environment})",
    ]
    for component in (
        report.rust,
        report.jig,
        report.llvm,
        report.llvm_development,
        report.cuda,
    ):
        location = "" if component.path is None else f" ({component.path})"
        line = f"{component.name}: {component.state} - "
        line += f"{component.detail}{location}"
        lines.append(line)
    return "\n".join((*lines, ""))


def _boolean_argument(values: dict[str, object], key: str) -> bool:
    value = values.get(key)
    if type(value) is not bool:
        _fail("bootstrap arguments did not resolve to booleans")
    return value


def _arguments(argv: list[str] | None) -> tuple[bool, bool, bool, bool]:
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
    _ = parser.add_argument(
        "--provision-cuda",
        action="store_true",
        help="download and provision exact tracked CUDA packages for this host",
    )
    _ = parser.add_argument(
        "--provision-llvm-development",
        action="store_true",
        help="download exact tracked Linux LLVM development packages",
    )
    namespace = parser.parse_args(argv)
    values = cast("dict[str, object]", vars(namespace))
    return (
        _boolean_argument(values, "skip_python"),
        _boolean_argument(values, "require_cuda"),
        _boolean_argument(values, "provision_cuda"),
        _boolean_argument(values, "provision_llvm_development"),
    )


def main(argv: list[str] | None = None) -> int:
    """Initialize the current checkout and print component readiness.

    Returns:
        Zero after successful initialization, otherwise one.

    """
    (
        skip_python,
        require_cuda,
        provision_cuda,
        provision_llvm_development,
    ) = _arguments(argv)
    try:
        report = initialize_project(
            provision_python=not skip_python,
            require_cuda=require_cuda,
            provisions=ProvisionRequests(
                cuda=provision_cuda,
                llvm_development=provision_llvm_development,
            ),
        )
    except (
        InitializationError,
        OSError,
        python_validation.ProvisionError,
    ) as error:
        _ = sys.stderr.write(f"error: {_native_exception_detail(error)}\n")
        return 1
    report_text = render_report(report)
    try:
        written = sys.stdout.write(report_text)
        if type(written) is not int or written != len(report_text):
            error_text = "error: incomplete bootstrap report output\n"
        else:
            sys.stdout.flush()
            error_text = None
    except (OSError, ValueError, TypeError, RuntimeError):
        error_text = "error: cannot write bootstrap report\n"
    if error_text is not None:
        _ = sys.stderr.write(error_text)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
