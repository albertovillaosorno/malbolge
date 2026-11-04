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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Portable bounded process programs for behavior-probe observations.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Portable bounded process programs for behavior-probe observations."""

from __future__ import annotations

import builtins
import os
import pathlib
import shutil
import signal
import stat

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - no shell; resolved executables only.
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256 as _native_sha256
from pathlib import Path, PurePath
from stat import S_ISREG
from sys import getfilesystemencodeerrors as _get_filesystem_encode_errors
from sys import getfilesystemencoding as _get_filesystem_encoding
from types import MemberDescriptorType
from typing import IO, TYPE_CHECKING, Protocol, cast

from algorithms.diff.exact import ExactTreeError, snapshot_tree
from algorithms.diff.model import (
    _file_fields as _native_file_fields,
)
from algorithms.diff.model import (
    _snapshot_files as _native_snapshot_files,
)
from algorithms.diff.model import (
    reserved_windows_component,
)

if TYPE_CHECKING:
    from algorithms.diff.model import TreeSnapshot

_ZERO = 0
_ONE = 1
_DEFAULT_TIMEOUT_MS = 10_000
_DEFAULT_OUTPUT_LIMIT = 1_048_576
_FRAME_LENGTH_BYTES = 8
_SHA256_BYTES = _native_sha256().digest_size
_TOOL_BINDING_LENGTH = 2
_NUL = "\x00"
_READ_CHUNK_BYTES = 16_384
_MAX_NATIVE_FILE_DESCRIPTOR = (1 << 31) - 1
_POLL_SECONDS = 0.005
_CHILD_REAP_SECONDS = 2.0
_POSIX_OS_NAME = "posix"
_MIN_HARDLINK_COUNT = 2
_NATIVE_STAT_RESULT = os.stat_result
_NATIVE_RELATIVE_TO = Path.relative_to
_NATIVE_PATH_RESOLVE = Path.resolve
_NATIVE_HOST_REALPATH = os.path.realpath
# Native PurePath lazily re-parses uncached paths through host parser globals.
_NATIVE_HOST_SPLITROOT = os.path.splitroot
_NATIVE_HOST_SPLITDRIVE = os.path.splitdrive
_NATIVE_HOST_SEP = os.path.sep
_NATIVE_HOST_ALTSEP = os.path.altsep
_NATIVE_HOST_LSTAT = os.lstat
_NATIVE_HOST_READLINK = os.readlink
_NATIVE_HOST_GETCWD = os.getcwd
_NATIVE_HOST_ISLINK = stat.S_ISLNK
# Inode disjointness and executable admission cannot trust late host hooks.
_NATIVE_OS_STAT = os.stat
# Probe output evidence must be read through the original host descriptor API.
_NATIVE_OS_READ = os.read
# Process-group cleanup must not trust a late host signal dispatcher.
_NATIVE_OS_KILL = os.kill
# Process launch must reject substituted host class and pipe sentinels.
_IMPORTED_POPEN = subprocess.Popen
_NATIVE_POPEN = _IMPORTED_POPEN
_NATIVE_SUBPROCESS_PIPE = subprocess.PIPE
_NATIVE_PATH_STRING = Path.__str__
_NATIVE_PATH_WITH_SEGMENTS = Path.with_segments
_NATIVE_PATH_JOINPATH = Path.joinpath
_NATIVE_PATH_NEW = Path.__new__
_NATIVE_PURE_PATH_INIT = PurePath.__init__
_NATIVE_OS_FSPATH = os.fspath
# PurePath.relative_to uses this mutable module alias during containment.
_NATIVE_PATH_CHAIN = pathlib.__dict__["chain"]
# Freeze the host filesystem codec before any consumer module can mutate os.
_FILESYSTEM_ENCODING = _get_filesystem_encoding()
_FILESYSTEM_ERRORS = _get_filesystem_encode_errors()
# Keep mirror creation independent of late consumer library hooks.
_NATIVE_GETTEMPDIR = tempfile.gettempdir
_NATIVE_TEMPORARY_DIRECTORY = tempfile.TemporaryDirectory
_NATIVE_COPYTREE = shutil.copytree
_NATIVE_ANY = builtins.any
_NATIVE_SET = builtins.set
_NATIVE_FROZENSET = builtins.frozenset
_NATIVE_SORTED = builtins.sorted
_NATIVE_TYPE = builtins.type
_NATIVE_LEN = builtins.len
_NATIVE_TUPLE = builtins.tuple
_NATIVE_STR = builtins.str
_NATIVE_BYTES = builtins.bytes
_NATIVE_BOOL = builtins.bool
_NATIVE_OBJECT_NEW = object.__new__
_NATIVE_INT = builtins.int
# A late signal enum alias must not downgrade process-group termination.
_NATIVE_GROUP_SIGNAL = (
    _NATIVE_INT(signal.Signals["SIGKILL"])
    if os.name == _POSIX_OS_NAME
    else _ZERO
)
_NATIVE_ISINSTANCE = builtins.isinstance
_NATIVE_ZIP = builtins.zip
_NATIVE_ALL = builtins.all
_NATIVE_MIN = builtins.min
_NATIVE_MAX = builtins.max
_NATIVE_ENUMERATE = builtins.enumerate
_NATIVE_HASATTR = builtins.hasattr
# Native error classification must not depend on builtin aliases replaced by
# consumer probe/domain callbacks after this module was imported.
_NATIVE_OS_ERROR = builtins.OSError
_NATIVE_VALUE_ERROR = builtins.ValueError
_NATIVE_RUNTIME_ERROR = builtins.RuntimeError
_NATIVE_ATTRIBUTE_ERROR = builtins.AttributeError
_NATIVE_FILE_NOT_FOUND_ERROR = builtins.FileNotFoundError
_NATIVE_UNICODE_ERROR = builtins.UnicodeError
_NATIVE_UNICODE_ENCODE_ERROR = builtins.UnicodeEncodeError
_NATIVE_PROCESS_LOOKUP_ERROR = builtins.ProcessLookupError
_NATIVE_BROKEN_PIPE_ERROR = builtins.BrokenPipeError
_NATIVE_OVERFLOW_ERROR = builtins.OverflowError
_NATIVE_EXCEPTION = builtins.Exception
_NATIVE_SUBPROCESS_TIMEOUT = subprocess.TimeoutExpired
# Preserve delegated tree errors even after consumer module alias changes.
_NATIVE_EXACT_TREE_ERROR = ExactTreeError
# Exact native platform identity must not construct a Path during admission.
_NATIVE_PLATFORM_PATH_TYPE = _NATIVE_TYPE(Path())
# Path.__str__ still reads replaceable Python path metadata, even when its
# method itself was captured at import time. Freeze path metadata hooks and
# constructors inherited or overridden at the native platform class.
_PATH_CACHE_HOOK_NAMES = (
    "__new__",
    "__init__",
    "__getattribute__",
    "__fspath__",
    "_str",
    "_format_parsed_parts",
    "_raw_paths",
    "_raw_path",
    "_drv",
    "_root",
    "_tail_cached",
    "_tail",
    "drive",
    "root",
    "_parse_path",
    "_from_parsed_string",
    "_from_parsed_parts",
    "parser",
)
_NATIVE_PATH_CACHE_HOOKS = tuple(
    (
        cls,
        tuple((name, cls.__dict__.get(name)) for name in _PATH_CACHE_HOOK_NAMES),
    )
    for cls in _NATIVE_PLATFORM_PATH_TYPE.__mro__
    if issubclass(cls, PurePath)
)


# Resolve and command argv need additional dispatch hooks that admission
# intentionally tolerates until execution (for example a late Path.__str__).
_RESOLVER_HOOK_NAMES = (
    "__str__", "with_segments", "joinpath", "parents", "__eq__"
)
_NATIVE_RESOLVER_HOOKS = tuple(
    (
        cls,
        tuple((name, cls.__dict__.get(name)) for name in _RESOLVER_HOOK_NAMES),
    )
    for cls, _ in _NATIVE_PATH_CACHE_HOOKS
)
# Native relative_to reads the mutable _PathParents sequence, not just the
# Path.parents descriptor. Pin its class alias and inherited dispatch chain.
_NATIVE_PATH_PARENTS_TYPE = _NATIVE_TYPE(Path().parents)
_PARENT_SEQUENCE_HOOK_NAMES = (
    "__new__", "__init__", "__getattribute__", "__setattr__",
    "__contains__", "__iter__", "__getitem__", "__len__",
    "_path", "_drv", "_root", "_tail",
)
_NATIVE_PARENT_SEQUENCE_HOOKS = tuple(
    (
        cls,
        tuple((name, cls.__dict__.get(name)) for name in _PARENT_SEQUENCE_HOOK_NAMES),
    )
    for cls in _NATIVE_PATH_PARENTS_TYPE.__mro__
    if cls is not object
)


def _native_path_hooks_changed() -> bool:
    return _NATIVE_ANY(
        cls.__dict__.get(name) is not original
        for cls, hooks in _NATIVE_PATH_CACHE_HOOKS
        for name, original in hooks
    )


def _native_resolver_hooks_changed() -> bool:
    return (
        pathlib.__dict__.get("chain") is not _NATIVE_PATH_CHAIN
        or builtins.enumerate is not _NATIVE_ENUMERATE
        or builtins.hasattr is not _NATIVE_HASATTR
        or _NATIVE_ANY(
            cls.__dict__.get(name) is not original
            for cls, hooks in _NATIVE_RESOLVER_HOOKS
            for name, original in hooks
        )
    )


def _native_parent_hooks_changed() -> bool:
    return (
        pathlib.__dict__.get("_PathParents") is not _NATIVE_PATH_PARENTS_TYPE
        or _NATIVE_ANY(
            cls.__dict__.get(name) is not original
            for cls, hooks in _NATIVE_PARENT_SEQUENCE_HOOKS
            for name, original in hooks
        )
    )


def _native_path_stat(path: Path) -> os.stat_result:
    if (
        _native_path_hooks_changed()
        or _native_resolver_hooks_changed()
        or Path.__str__ is not _NATIVE_PATH_STRING
    ):
        message = "probe native path hooks changed"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    result = _NATIVE_OS_STAT(_NATIVE_PATH_STRING(path))
    if (
        _native_path_hooks_changed()
        or _native_resolver_hooks_changed()
        or Path.__str__ is not _NATIVE_PATH_STRING
    ):
        message = "probe native path hooks changed"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    return result


_NATIVE_PATH_STAT = _native_path_stat
# Native stream adapters can raise non-I/O ordinary exceptions as well.
_PIPE_DEPENDENCY_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    AttributeError,
    IndexError,
    OverflowError,
)


class _HashUpdater(Protocol):
    """Minimal digest-update boundary used by transcript framing."""

    def update(self, data: bytes, /) -> None:
        """Consume one exact byte fragment."""
        ...


class ProbeProgramError(ValueError):
    """Raised when a portable probe program is malformed."""


class ProbeExecutionError(RuntimeError):
    """Raised when a probe cannot execute deterministically and safely."""


# The exported name is writable, but internal errors retain native identity.
_NATIVE_PROBE_EXECUTION_ERROR = ProbeExecutionError


class ProbeRoot(StrEnum):
    """Authorized roots available to structured probe paths."""

    SOURCE = "source"
    REPOSITORY = "repository"
    SCRATCH = "scratch"


@dataclass(frozen=True, slots=True, init=False)
class PathArgument:
    """One argv path resolved beneath an authorized probe root."""

    root: ProbeRoot
    relative_path: str

    def __init__(
        self,
        root: ProbeRoot,
        relative_path: str,
    ) -> None:
        """Admit portable probe evidence with the original validator."""
        _PROBE_RECORD_SLOTS[PathArgument]["root"].__set__(self, root)
        _PROBE_RECORD_SLOTS[PathArgument]["relative_path"].__set__(self, relative_path)
        _PATH_ARGUMENT_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject foreign roots and unsafe relative paths."""
        root, relative = _probe_path_fields(self, PathArgument)
        _validate_probe_root(root)
        _validate_relative_path(relative)


# Generated dataclass init methods consult mutable class post-init hooks.
# Bind the original constructor validator before consumer code can replace it.
_PATH_ARGUMENT_VALIDATOR = cast(
    "Callable[[PathArgument], None]", PathArgument.__dict__["__post_init__"]
)

ProbeArgument = str | PathArgument


def _require_portable_probe_identifier(value: object, context: str) -> str:
    if _NATIVE_TYPE(value) is not _NATIVE_STR or not value:
        message = f"{context} must be a non-empty string"
        raise ProbeProgramError(message)
    if _NUL in value:
        message = f"{context} must not contain NUL bytes"
        raise ProbeProgramError(message)
    _require_portable_utf8_text(value, context)
    return value


def _require_portable_utf8_text(value: str, context: str) -> None:
    try:
        _ = value.encode("utf-8")
    except _NATIVE_UNICODE_ENCODE_ERROR as error:
        message = f"{context} must use portable UTF-8 text"
        raise ProbeProgramError(message) from error


@dataclass(frozen=True, slots=True, init=False)
class ToolExecutable:
    """Executable resolved through a logical consumer tool identifier."""

    tool_id: str

    def __init__(
        self,
        tool_id: str,
    ) -> None:
        """Admit portable probe evidence with the original validator."""
        _PROBE_RECORD_SLOTS[ToolExecutable]["tool_id"].__set__(self, tool_id)
        _TOOL_EXECUTABLE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require a portable logical tool identifier."""
        _ = _require_portable_probe_identifier(
            _probe_field(self, ToolExecutable, "tool_id"),
            "probe tool identifier",
        )


# Generated dataclass init methods consult mutable class post-init hooks.
# Bind the original constructor validator before consumer code can replace it.
_TOOL_EXECUTABLE_VALIDATOR = cast(
    "Callable[[ToolExecutable], None]", ToolExecutable.__dict__["__post_init__"]
)

@dataclass(frozen=True, slots=True, init=False)
class RootedExecutable:
    """Executable artifact produced or stored beneath an authorized root."""

    root: ProbeRoot
    relative_path: str

    def __init__(
        self,
        root: ProbeRoot,
        relative_path: str,
    ) -> None:
        """Admit portable probe evidence with the original validator."""
        _PROBE_RECORD_SLOTS[RootedExecutable]["root"].__set__(self, root)
        _PROBE_RECORD_SLOTS[RootedExecutable]["relative_path"].__set__(
            self, relative_path
        )
        _ROOTED_EXECUTABLE_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject foreign roots and unsafe executable paths."""
        root, relative = _probe_path_fields(self, RootedExecutable)
        _validate_probe_root(root)
        _validate_relative_path(relative)


# Generated dataclass init methods consult mutable class post-init hooks.
# Bind the original constructor validator before consumer code can replace it.
_ROOTED_EXECUTABLE_VALIDATOR = cast(
    "Callable[[RootedExecutable], None]", RootedExecutable.__dict__["__post_init__"]
)

ProbeExecutable = ToolExecutable | RootedExecutable


def _require_fs_encodable(value: str, context: str) -> None:
    try:
        _ = value.encode(_FILESYSTEM_ENCODING, _FILESYSTEM_ERRORS)
    except _NATIVE_UNICODE_ERROR as error:
        message = f"{context} must be filesystem-encodable"
        raise ProbeProgramError(message) from error


def _validate_argv_strings(arguments: tuple[ProbeArgument, ...]) -> None:
    """Reject impossible platform argv bytes at record admission.

    Raises:
        ProbeProgramError: An argument contains a NUL character.

    """
    if _NATIVE_ANY(
        _NUL in item for item in arguments if _NATIVE_TYPE(item) is _NATIVE_STR
    ):
        message = "probe argv strings must not contain NUL bytes"
        raise ProbeProgramError(message)
    for argument in arguments:
        if _NATIVE_TYPE(argument) is _NATIVE_STR:
            _require_fs_encodable(argument, "probe argv string")
            _require_portable_utf8_text(argument, "probe argv string")


def _validate_command_shape(command: ProbeCommand) -> None:
    executable = _probe_field(command, ProbeCommand, "executable")
    arguments = _probe_field(command, ProbeCommand, "arguments")
    stdin = _probe_field(command, ProbeCommand, "stdin")
    if _NATIVE_TYPE(executable) not in {ToolExecutable, RootedExecutable}:
        message = "probe executable must use an exact executable record"
        raise ProbeProgramError(message)
    if _NATIVE_TYPE(arguments) is not _NATIVE_TUPLE:
        message = "probe arguments must use the exact immutable tuple type"
        raise ProbeProgramError(message)
    admitted_arguments = cast("tuple[ProbeArgument, ...]", arguments)
    if _NATIVE_ANY(
        _NATIVE_TYPE(argument) not in {_NATIVE_STR, PathArgument}
        for argument in admitted_arguments
    ):
        message = "probe arguments contain a foreign argument record"
        raise ProbeProgramError(message)
    if _NATIVE_TYPE(stdin) is not _NATIVE_BYTES:
        message = "probe stdin must use exact bytes"
        raise ProbeProgramError(message)
    _validate_argv_strings(admitted_arguments)


def _validate_command_integer(
    value: object, context: str, *, positive: bool
) -> None:
    if _NATIVE_TYPE(value) is not _NATIVE_INT:
        message = f"{context} must use the exact integer type"
        raise ProbeProgramError(message)
    minimum = _ONE if positive else _ZERO
    if value < minimum:
        qualifier = "positive" if positive else "non-negative"
        message = f"{context} must be {qualifier}"
        raise ProbeProgramError(message)


def _validate_command_limits(command: ProbeCommand) -> None:
    expected = _probe_field(command, ProbeCommand, "expected_exit_code")
    if expected is not None:
        _validate_command_integer(
            expected, "probe expected exit code", positive=False
        )
    for field_name, context, positive in (
        ("timeout_ms", "probe timeout", True),
        ("max_stdout_bytes", "probe stdout limit", False),
        ("max_stderr_bytes", "probe stderr limit", False),
    ):
        _validate_command_integer(
            _probe_field(command, ProbeCommand, field_name), context, positive=positive
        )
    if _NATIVE_TYPE(
        _probe_field(command, ProbeCommand, "digest_stdout")
    ) is not _NATIVE_BOOL:
        message = "probe stdout digest selector must use an exact boolean"
        raise ProbeProgramError(message)
    if _NATIVE_TYPE(
        _probe_field(command, ProbeCommand, "digest_exit_code")
    ) is not _NATIVE_BOOL:
        message = "probe exit digest selector must use an exact boolean"
        raise ProbeProgramError(message)


@dataclass(frozen=True, slots=True, init=False)
class ProbeCommand:
    """One bounded no-shell process invocation in a portable probe program."""

    executable: ProbeExecutable
    arguments: tuple[ProbeArgument, ...] = ()
    stdin: bytes = b""
    expected_exit_code: int | None = _ZERO
    timeout_ms: int = _DEFAULT_TIMEOUT_MS
    max_stdout_bytes: int = _DEFAULT_OUTPUT_LIMIT
    max_stderr_bytes: int = _DEFAULT_OUTPUT_LIMIT
    digest_stdout: bool = False
    digest_exit_code: bool = False

    def __init__(
        self,
        executable: ProbeExecutable,
        arguments: tuple[ProbeArgument, ...] = (),
        stdin: bytes = b"",
        expected_exit_code: int | None = _ZERO,
        timeout_ms: int = _DEFAULT_TIMEOUT_MS,
        max_stdout_bytes: int = _DEFAULT_OUTPUT_LIMIT,
        max_stderr_bytes: int = _DEFAULT_OUTPUT_LIMIT,
        digest_stdout: bool = False,
        digest_exit_code: bool = False,
    ) -> None:
        """Admit portable probe evidence with the original validator."""
        _PROBE_RECORD_SLOTS[ProbeCommand]["executable"].__set__(self, executable)
        _PROBE_RECORD_SLOTS[ProbeCommand]["arguments"].__set__(self, arguments)
        _PROBE_RECORD_SLOTS[ProbeCommand]["stdin"].__set__(self, stdin)
        _PROBE_RECORD_SLOTS[ProbeCommand]["expected_exit_code"].__set__(
            self, expected_exit_code
        )
        _PROBE_RECORD_SLOTS[ProbeCommand]["timeout_ms"].__set__(self, timeout_ms)
        _PROBE_RECORD_SLOTS[ProbeCommand]["max_stdout_bytes"].__set__(
            self, max_stdout_bytes
        )
        _PROBE_RECORD_SLOTS[ProbeCommand]["max_stderr_bytes"].__set__(
            self, max_stderr_bytes
        )
        _PROBE_RECORD_SLOTS[ProbeCommand]["digest_stdout"].__set__(self, digest_stdout)
        _PROBE_RECORD_SLOTS[ProbeCommand]["digest_exit_code"].__set__(
            self, digest_exit_code
        )
        _PROBE_COMMAND_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Reject unbounded or nonsensical process limits."""
        _validate_command_shape(self)
        _validate_command_limits(self)


# Generated dataclass init methods consult mutable class post-init hooks.
# Bind the original constructor validator before consumer code can replace it.
_PROBE_COMMAND_VALIDATOR = cast(
    "Callable[[ProbeCommand], None]", ProbeCommand.__dict__["__post_init__"]
)

@dataclass(frozen=True, slots=True, init=False)
class ProbeProgram:
    """Bounded command sequence for one behavior observation."""

    probe_id: str
    commands: tuple[ProbeCommand, ...]

    def __init__(
        self,
        probe_id: str,
        commands: tuple[ProbeCommand, ...],
    ) -> None:
        """Admit portable probe evidence with the original validator."""
        _PROBE_RECORD_SLOTS[ProbeProgram]["probe_id"].__set__(self, probe_id)
        _PROBE_RECORD_SLOTS[ProbeProgram]["commands"].__set__(self, commands)
        _PROBE_PROGRAM_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require an identifier and at least one command.

        Raises:
            ProbeProgramError: Program identity or command sequence is empty.

        """
        _ = _require_portable_probe_identifier(
            _probe_field(self, ProbeProgram, "probe_id"),
            "probe program identifier",
        )
        commands = _probe_field(self, ProbeProgram, "commands")
        if _NATIVE_TYPE(commands) is not _NATIVE_TUPLE:
            message = "probe commands must use the exact immutable tuple type"
            raise ProbeProgramError(message)
        if not commands:
            message = "probe program requires at least one command"
            raise ProbeProgramError(message)
        if _NATIVE_ANY(
            _NATIVE_TYPE(command) is not ProbeCommand
            for command in cast("tuple[object, ...]", commands)
        ):
            message = "probe program contains a foreign command record"
            raise ProbeProgramError(message)


# Generated dataclass init methods consult mutable class post-init hooks.
# Bind the original constructor validator before consumer code can replace it.
_PROBE_PROGRAM_VALIDATOR = cast(
    "Callable[[ProbeProgram], None]", ProbeProgram.__dict__["__post_init__"]
)

def _validate_path(value: object, context: str) -> None:
    # Path subclasses can override conversion, resolution or status checks.
    # The probe execution authority must use an exact native host path.
    if _NATIVE_TYPE(value) is not _NATIVE_PLATFORM_PATH_TYPE:
        message = f"{context} must use exact pathlib Path"
        raise ProbeProgramError(message)
    if _native_path_hooks_changed():
        message = f"{context} native path hooks changed"
        raise ProbeProgramError(message)
    raw = _NATIVE_PATH_STRING(value)
    if _native_path_hooks_changed():
        message = f"{context} native path hooks changed"
        raise ProbeProgramError(message)
    if _NUL in raw:
        message = f"{context} must not contain NUL bytes"
        raise ProbeProgramError(message)
    _require_fs_encodable(raw, context)


def _validate_tool_binding(binding: object) -> tuple[str, Path]:
    if _NATIVE_TYPE(binding) is not _NATIVE_TUPLE:
        message = "probe tool binding must be an exact pair"
        raise ProbeProgramError(message)
    pair = cast("tuple[object, ...]", binding)
    if _NATIVE_LEN(pair) != _TOOL_BINDING_LENGTH:
        message = "probe tool binding must be an exact pair"
        raise ProbeProgramError(message)
    tool_id, tool_path = pair
    tool_id = _require_portable_probe_identifier(
        tool_id, "probe tool identifier"
    )
    _validate_path(tool_path, "probe tool path")
    return tool_id, cast("Path", tool_path)


def _validate_tool_bindings(value: object) -> tuple[str, ...]:
    if _NATIVE_TYPE(value) is not _NATIVE_TUPLE:
        message = "probe tool bindings must use the exact immutable tuple type"
        raise ProbeProgramError(message)
    bindings = cast("tuple[object, ...]", value)
    identifiers = _NATIVE_TUPLE(
        _validate_tool_binding(binding)[0] for binding in bindings
    )
    if identifiers != _NATIVE_TUPLE(_NATIVE_SORTED(_NATIVE_SET(identifiers))):
        message = "probe tool bindings must be unique and sorted"
        raise ProbeProgramError(message)
    return identifiers


@dataclass(frozen=True, slots=True, init=False)
class ProbeRunContext:
    """Roots and logical tool bindings used while executing probe programs."""

    source_root: Path
    repository_root: Path
    tools: tuple[tuple[str, Path], ...]
    enforce_source_immutable: bool = True

    def __init__(
        self,
        source_root: Path,
        repository_root: Path,
        tools: tuple[tuple[str, Path], ...],
        enforce_source_immutable: bool = True,
    ) -> None:
        """Admit portable probe evidence with the original validator."""
        _PROBE_RECORD_SLOTS[ProbeRunContext]["source_root"].__set__(self, source_root)
        _PROBE_RECORD_SLOTS[ProbeRunContext]["repository_root"].__set__(
            self, repository_root
        )
        _PROBE_RECORD_SLOTS[ProbeRunContext]["tools"].__set__(self, tools)
        _PROBE_RECORD_SLOTS[ProbeRunContext]["enforce_source_immutable"].__set__(
            self, enforce_source_immutable
        )
        _PROBE_RUN_CONTEXT_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require deterministic unique tool bindings.

        Raises:
            ProbeProgramError: Tool identifiers are empty, duplicate, or
            unsorted.

        """
        _validate_path(
            _probe_field(self, ProbeRunContext, "source_root"), "probe source root"
        )
        _validate_path(
            _probe_field(self, ProbeRunContext, "repository_root"),
            "probe repository root",
        )
        _ = _validate_tool_bindings(_probe_field(self, ProbeRunContext, "tools"))
        if _NATIVE_TYPE(
            _probe_field(self, ProbeRunContext, "enforce_source_immutable")
        ) is not _NATIVE_BOOL:
            message = "probe source-immutability flag must use an exact boolean"
            raise ProbeProgramError(message)


# Generated dataclass init methods consult mutable class post-init hooks.
# Bind the original constructor validator before consumer code can replace it.
_PROBE_RUN_CONTEXT_VALIDATOR = cast(
    "Callable[[ProbeRunContext], None]", ProbeRunContext.__dict__["__post_init__"]
)

@dataclass(frozen=True, slots=True, init=False)
class ProbeTranscript:
    """Stable digest of explicitly selected process observations."""

    probe_id: str
    digest: bytes
    digested_commands: int

    def __init__(
        self,
        probe_id: str,
        digest: bytes,
        digested_commands: int,
    ) -> None:
        """Admit portable probe evidence with the original validator."""
        _PROBE_RECORD_SLOTS[ProbeTranscript]["probe_id"].__set__(self, probe_id)
        _PROBE_RECORD_SLOTS[ProbeTranscript]["digest"].__set__(self, digest)
        _PROBE_RECORD_SLOTS[ProbeTranscript]["digested_commands"].__set__(
            self, digested_commands
        )
        _PROBE_TRANSCRIPT_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require exact immutable and coherent transcript metadata.

        Raises:
            ProbeProgramError: A transcript field has invalid runtime metadata.

        """
        _ = _require_portable_probe_identifier(
            _probe_field(self, ProbeTranscript, "probe_id"),
            "probe transcript identifier",
        )
        digest = _probe_field(self, ProbeTranscript, "digest")
        if (
            _NATIVE_TYPE(digest) is not _NATIVE_BYTES
            or _NATIVE_LEN(digest) != _SHA256_BYTES
        ):
            message = "probe transcript digest must be exactly 32 bytes"
            raise ProbeProgramError(message)
        selected = _probe_field(self, ProbeTranscript, "digested_commands")
        if _NATIVE_TYPE(selected) is not _NATIVE_INT or selected < _ZERO:
            message = "probe transcript selected count must be non-negative int"
            raise ProbeProgramError(message)


# Generated dataclass init methods consult mutable class post-init hooks.
# Bind the original constructor validator before consumer code can replace it.
_PROBE_TRANSCRIPT_VALIDATOR = cast(
    "Callable[[ProbeTranscript], None]", ProbeTranscript.__dict__["__post_init__"]
)

# Original C-level slot writers protect admitted records from late mutable
# class property setters. Capture all seven record types before consumer code
# can receive any constructor through the completed module import.
_PROBE_RECORD_SLOTS: dict[type, dict[str, MemberDescriptorType]] = {
    owner: {
        name: cast("MemberDescriptorType", owner.__dict__[name])
        for name in owner.__slots__
    }
    for owner in (
        PathArgument,
        ToolExecutable,
        RootedExecutable,
        ProbeCommand,
        ProbeProgram,
        ProbeRunContext,
        ProbeTranscript,
    )
}


_PROBE_TRANSCRIPT_INIT = ProbeTranscript.__init__


def _new_probe_transcript(
    probe_id: str, digest: bytes, digested_commands: int
) -> ProbeTranscript:
    receipt = _NATIVE_OBJECT_NEW(ProbeTranscript)
    _PROBE_TRANSCRIPT_INIT(receipt, probe_id, digest, digested_commands)
    return receipt


def _probe_field(record: object, owner: type, field: str) -> object:
    """Read original native storage instead of post-import class getters."""
    return cast("object", _PROBE_RECORD_SLOTS[owner][field].__get__(record, owner))


def _probe_path_fields(
    record: PathArgument | RootedExecutable,
    owner: type,
) -> tuple[object, object]:
    return (
        _probe_field(record, owner, "root"),
        _probe_field(record, owner, "relative_path"),
    )


@dataclass(frozen=True, slots=True, init=False)
class _CommandResult:
    """Internal process evidence pinned against late Python class hooks."""

    stdout: bytes
    returncode: int

    def __init__(self, stdout: bytes, returncode: int) -> None:
        _COMMAND_RESULT_STDOUT_SLOT.__set__(self, stdout)
        _COMMAND_RESULT_RETURN_CODE_SLOT.__set__(self, returncode)


_COMMAND_RESULT_STDOUT_SLOT = cast(
    "MemberDescriptorType", _CommandResult.__dict__["stdout"]
)
_COMMAND_RESULT_RETURN_CODE_SLOT = cast(
    "MemberDescriptorType", _CommandResult.__dict__["returncode"]
)


_COMMAND_RESULT_INIT = _CommandResult.__init__


def _new_command_result(stdout: bytes, returncode: int) -> _CommandResult:
    result = _NATIVE_OBJECT_NEW(_CommandResult)
    _COMMAND_RESULT_INIT(result, stdout, returncode)
    return result


@dataclass(frozen=True, slots=True, init=False)
class _CapturedProcess:
    """Private process receipt, independent of mutable subprocess classes."""

    stdout: bytes
    stderr: bytes
    returncode: int

    def __init__(self, stdout: bytes, stderr: bytes, returncode: int) -> None:
        for name, value in (
            ("stdout", stdout),
            ("stderr", stderr),
            ("returncode", returncode),
        ):
            _CAPTURED_PROCESS_SLOTS[name].__set__(self, value)


_CAPTURED_PROCESS_SLOTS: dict[str, MemberDescriptorType] = {
    name: cast("MemberDescriptorType", _CapturedProcess.__dict__[name])
    for name in _CapturedProcess.__slots__
}
_CAPTURED_PROCESS_INIT = _CapturedProcess.__init__


def _new_captured_process(
    stdout: bytes, stderr: bytes, returncode: int
) -> _CapturedProcess:
    receipt = _NATIVE_OBJECT_NEW(_CapturedProcess)
    _CAPTURED_PROCESS_INIT(receipt, stdout, stderr, returncode)
    return receipt


def _captured_field(receipt: _CapturedProcess, name: str) -> object:
    return cast(
        "object", _CAPTURED_PROCESS_SLOTS[name].__get__(receipt, _CapturedProcess)
    )


def _command_result_stdout(result: _CommandResult) -> bytes:
    return cast("bytes", _COMMAND_RESULT_STDOUT_SLOT.__get__(result, _CommandResult))


def _command_result_returncode(result: _CommandResult) -> int:
    return cast(
        "int", _COMMAND_RESULT_RETURN_CODE_SLOT.__get__(result, _CommandResult)
    )


def _validate_probe_root(root: object) -> None:
    if _NATIVE_TYPE(root) is not ProbeRoot:
        message = "probe root must use the exact ProbeRoot type"
        raise ProbeProgramError(message)


def _validate_relative_path(relative_path: object) -> None:
    if _NATIVE_TYPE(relative_path) is not _NATIVE_STR:
        message = "probe relative path must use the exact string type"
        raise ProbeProgramError(message)
    if _NUL in relative_path:
        message = "probe relative paths must not contain NUL bytes"
        raise ProbeProgramError(message)
    _require_fs_encodable(relative_path, "probe relative path")
    _require_portable_utf8_text(relative_path, "probe relative path")
    # PureWindowsPath delegates to mutable ntpath helpers. Validate lexical
    # components before consumer-controlled process hooks can spoof drives or
    # route native Windows device / alternate-stream paths outside the tree.
    unsafe = (
        not relative_path
        or _NATIVE_ANY(
            component in ("", ".", "..")
            or reserved_windows_component(component)
            for component in relative_path.split("/")
        )
    )
    if unsafe:
        message = (
            f"unsafe probe relative path (including NUL): {relative_path!r}"
        )
        raise ProbeProgramError(message)


def _native_path_inside(path: Path, root: Path) -> bool:
    """Check native Path containment without a mutable process-global hook."""
    _require_native_host_resolver()
    try:
        _ = _NATIVE_RELATIVE_TO(path, root)
    except _NATIVE_VALUE_ERROR:
        _require_native_host_resolver()
        return False
    _require_native_host_resolver()
    return True


def _native_resolved_path(result: Path, description: str) -> Path:
    """Reject a foreign Path subtype before containment or process use."""
    if _NATIVE_TYPE(result) is not _NATIVE_PLATFORM_PATH_TYPE:
        message = f"probe {description} requires native resolved Path"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    return result


def _require_native_host_resolver() -> None:
    """Reject late host realpath hooks beneath the original Path.resolve."""
    if (
        _native_path_hooks_changed()
        or _native_resolver_hooks_changed()
        or _native_parent_hooks_changed()
        or os.fspath is not _NATIVE_OS_FSPATH
        or Path.__str__ is not _NATIVE_PATH_STRING
        or Path.with_segments is not _NATIVE_PATH_WITH_SEGMENTS
    ):
        message = "probe native path hooks changed"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    if (
        Path.joinpath is not _NATIVE_PATH_JOINPATH
        or Path.__new__ is not _NATIVE_PATH_NEW
        or PurePath.__init__ is not _NATIVE_PURE_PATH_INIT
    ):
        message = "probe native path hooks changed"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    if (
        os.path.realpath is not _NATIVE_HOST_REALPATH
        or os.lstat is not _NATIVE_HOST_LSTAT
        or os.readlink is not _NATIVE_HOST_READLINK
    ):
        message = "probe native host resolver changed"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    if (
        os.getcwd is not _NATIVE_HOST_GETCWD
        or stat.S_ISLNK is not _NATIVE_HOST_ISLINK
        or os.path.splitroot is not _NATIVE_HOST_SPLITROOT
        or os.path.splitdrive is not _NATIVE_HOST_SPLITDRIVE
        or os.path.sep is not _NATIVE_HOST_SEP
        or os.path.altsep is not _NATIVE_HOST_ALTSEP
        or builtins.len is not _NATIVE_LEN
        or builtins.bytes is not _NATIVE_BYTES
        or builtins.isinstance is not _NATIVE_ISINSTANCE
    ):
        message = "probe native host resolver changed"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)


def _resolved_root(path: Path, description: str) -> Path:
    _require_native_host_resolver()
    try:
        resolved = _NATIVE_PATH_RESOLVE(path)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_probe_error_detail(error)
        message = (
            f"probe {description} root resolution failed: {path}: {detail}"
        )
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error
    _require_native_host_resolver()
    return _native_resolved_path(resolved, f"{description} root")


def _root_path(
    root: ProbeRoot,
    context: ProbeRunContext,
    scratch_root: Path,
) -> Path:
    if root is ProbeRoot.SOURCE:
        return _resolved_root(
            cast("Path", _probe_field(context, ProbeRunContext, "source_root")),
            "source",
        )
    if root is ProbeRoot.REPOSITORY:
        return _resolved_root(
            cast("Path", _probe_field(context, ProbeRunContext, "repository_root")),
            "repository",
        )
    return _resolved_root(scratch_root, "scratch")


def _rooted_path(
    argument: PathArgument | RootedExecutable,
    context: ProbeRunContext,
    scratch_root: Path,
) -> Path:
    root_kind, relative_path = cast(
        "tuple[ProbeRoot, str]", _probe_path_fields(argument, _NATIVE_TYPE(argument))
    )
    root = _root_path(root_kind, context, scratch_root)
    _require_native_host_resolver()
    candidate = _NATIVE_PATH_JOINPATH(root, *relative_path.split("/"))
    _require_native_host_resolver()
    try:
        resolved = _NATIVE_PATH_RESOLVE(candidate)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_probe_error_detail(error)
        message = f"probe path resolution failed: {candidate}: {detail}"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error
    _require_native_host_resolver()
    resolved = _native_resolved_path(resolved, "rooted path")
    try:
        _ = _NATIVE_RELATIVE_TO(resolved, root)
    except _NATIVE_VALUE_ERROR as error:
        message = f"probe path escapes authorized root: {relative_path!r}"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error
    _require_native_host_resolver()
    return candidate


def _resolved_tool_path(path: Path) -> Path:
    _require_native_host_resolver()
    try:
        resolved = _NATIVE_PATH_RESOLVE(path)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_probe_error_detail(error)
        message = f"probe tool resolution failed: {path}: {detail}"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error
    _require_native_host_resolver()
    return _native_resolved_path(resolved, "tool")


def _tool_map(context: ProbeRunContext) -> dict[str, Path]:
    return {
        tool_id: _resolved_tool_path(path)
        for tool_id, path in cast(
            "tuple[tuple[str, Path], ...]",
            _probe_field(context, ProbeRunContext, "tools"),
        )
    }


def _native_executable_status(receipt: object) -> os.stat_result:
    """Validate a host tool status before admitting executable file mode.

    Returns:
        An exact native status record.

    Raises:
        ProbeExecutionError: The status is foreign metadata.

    """
    if _NATIVE_TYPE(receipt) is not _NATIVE_STAT_RESULT:
        message = "probe executable requires native filesystem status"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    return receipt


def _require_executable(path: Path) -> None:
    try:
        receipt = _NATIVE_PATH_STAT(path)
    except _NATIVE_PROBE_EXECUTION_ERROR:
        raise
    except _NATIVE_FILE_NOT_FOUND_ERROR as error:
        message = "probe executable is unavailable"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        reason = _safe_probe_error_detail(error)
        message = f"probe executable status failed: {path}: {reason}"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error
    if not S_ISREG(_native_executable_status(receipt).st_mode):
        message = "probe executable is unavailable"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)


def _resolve_executable(
    executable: ProbeExecutable,
    context: ProbeRunContext,
    scratch_root: Path,
) -> Path:
    if _NATIVE_ISINSTANCE(executable, ToolExecutable):
        tool_id = cast("str", _probe_field(executable, ToolExecutable, "tool_id"))
        path = _tool_map(context).get(tool_id)
        if path is None:
            message = f"unresolved probe tool: {tool_id}"
            raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    else:
        path = _rooted_path(executable, context, scratch_root)
    _require_executable(path)
    return path


def _resolve_argument(
    argument: ProbeArgument,
    context: ProbeRunContext,
    scratch_root: Path,
) -> str:
    if _NATIVE_ISINSTANCE(argument, str):
        return argument
    return _NATIVE_STR(_rooted_path(argument, context, scratch_root))


def _command_argv(
    command: ProbeCommand,
    context: ProbeRunContext,
    scratch_root: Path,
) -> list[str]:
    executable = _resolve_executable(
        cast("ProbeExecutable", _probe_field(command, ProbeCommand, "executable")),
        context,
        scratch_root,
    )
    arguments = (
        _resolve_argument(argument, context, scratch_root)
        for argument in cast(
            "tuple[ProbeArgument, ...]",
            _probe_field(command, ProbeCommand, "arguments"),
        )
    )
    return [_NATIVE_STR(executable), *arguments]


@dataclass(slots=True, init=False)
class _PipeCapture:
    """Quota-guarded bytes from one child output pipe."""

    limit: int
    fragments: list[bytes]
    size: int
    exceeded: bool
    error: Exception | None
    finished: bool

    def __init__(
        self,
        limit: int,
        fragments: list[bytes] | None = None,
        size: int = 0,
        exceeded: bool = False,
        error: Exception | None = None,
        finished: bool = False,
    ) -> None:
        """Store quota and worker state without late class setter hooks."""
        slots = _TRANSIENT_SLOTS[_PipeCapture]
        slots["limit"].__set__(self, limit)
        slots["fragments"].__set__(self, [] if fragments is None else fragments)
        slots["size"].__set__(self, size)
        slots["exceeded"].__set__(self, exceeded)
        slots["error"].__set__(self, error)
        slots["finished"].__set__(self, finished)


@dataclass(slots=True, init=False)
class _RunningProbe:
    """One subprocess and its independently monitored pipe workers."""

    process: subprocess.Popen[bytes]
    stdout: _PipeCapture
    stderr: _PipeCapture
    readers: tuple[threading.Thread, threading.Thread]
    writer: threading.Thread | None
    stdin_errors: list[Exception]
    stdin_complete: threading.Event

    def __init__(
        self,
        process: subprocess.Popen[bytes],
        stdout: _PipeCapture,
        stderr: _PipeCapture,
        readers: tuple[threading.Thread, threading.Thread],
        writer: threading.Thread | None,
        stdin_errors: list[Exception],
        stdin_complete: threading.Event,
    ) -> None:
        """Bind worker identities before observation, bypassing late setters."""
        slots = _TRANSIENT_SLOTS[_RunningProbe]
        for name, value in (
            ("process", process),
            ("stdout", stdout),
            ("stderr", stderr),
            ("readers", readers),
            ("writer", writer),
            ("stdin_errors", stdin_errors),
            ("stdin_complete", stdin_complete),
        ):
            slots[name].__set__(self, value)


# Transient process/pipe state is an execution authority: a substituted class
# getter must not relax quotas or turn incomplete worker output into evidence.
_TRANSIENT_SLOTS: dict[type, dict[str, MemberDescriptorType]] = {
    owner: {
        name: cast("MemberDescriptorType", owner.__dict__[name])
        for name in owner.__slots__
    }
    for owner in (_PipeCapture, _RunningProbe)
}


_PIPE_CAPTURE_INIT = _PipeCapture.__init__
_RUNNING_PROBE_INIT = _RunningProbe.__init__


def _new_pipe_capture(limit: int) -> _PipeCapture:
    capture = _NATIVE_OBJECT_NEW(_PipeCapture)
    _PIPE_CAPTURE_INIT(capture, limit)
    return capture


def _new_running_probe(
    process: subprocess.Popen[bytes],
    stdout: _PipeCapture,
    stderr: _PipeCapture,
    readers: tuple[threading.Thread, threading.Thread],
    writer: threading.Thread | None,
    stdin_errors: list[Exception],
    stdin_complete: threading.Event,
) -> _RunningProbe:
    running = _NATIVE_OBJECT_NEW(_RunningProbe)
    _RUNNING_PROBE_INIT(
        running, process, stdout, stderr, readers, writer, stdin_errors, stdin_complete
    )
    return running


def _capture_read(capture: _PipeCapture, name: str) -> object:
    """Read the original output-capture slot."""
    return cast(
        "object", _TRANSIENT_SLOTS[_PipeCapture][name].__get__(capture, _PipeCapture)
    )


def _capture_write(capture: _PipeCapture, name: str, value: object) -> None:
    """Write the original output-capture slot."""
    _TRANSIENT_SLOTS[_PipeCapture][name].__set__(capture, value)


def _running_read(running: _RunningProbe, name: str) -> object:
    """Read the original running-worker slot."""
    return cast(
        "object", _TRANSIENT_SLOTS[_RunningProbe][name].__get__(running, _RunningProbe)
    )


def _capture_fragment(stream: IO[bytes], capture: _PipeCapture) -> bool:
    """Store at most the remaining quota and one overflow sentinel.

    Returns:
        Whether more data can be read from the pipe.

    """
    remaining = cast("int", _capture_read(capture, "limit")) - cast(
        "int", _capture_read(capture, "size")
    )
    amount = _NATIVE_MAX(_ONE, _NATIVE_MIN(_READ_CHUNK_BYTES, remaining + _ONE))
    descriptor = stream.fileno()
    if (
        _NATIVE_TYPE(descriptor) is not _NATIVE_INT
        or descriptor < _ZERO
        or descriptor > _MAX_NATIVE_FILE_DESCRIPTOR
    ):
        message = "probe raw read descriptor must be a native C int"
        raise ValueError(message)
    fragment = _NATIVE_OS_READ(descriptor, amount)
    if _NATIVE_TYPE(fragment) is not _NATIVE_BYTES or _NATIVE_LEN(fragment) > amount:
        message = "probe raw read reported non-native or overlong bytes"
        raise ValueError(message)
    if not fragment:
        return False
    if _NATIVE_LEN(fragment) > remaining:
        _capture_write(capture, "exceeded", True)
        return False
    cast("list[bytes]", _capture_read(capture, "fragments")).append(fragment)
    _capture_write(
        capture,
        "size",
        cast("int", _capture_read(capture, "size")) + _NATIVE_LEN(fragment),
    )
    return True


def _close_probe_pipe(stream: IO[bytes], context: str) -> None:
    """Require native completion from a probe pipe teardown."""
    if stream.close() is not None:
        message = f"probe {context} close reported non-native completion"
        raise ValueError(message)


def _drain_pipe(stream: IO[bytes], capture: _PipeCapture) -> None:
    """Drain within the quota, recording read and close failures."""
    try:
        again = True
        while again:
            again = _capture_fragment(stream, capture)
    except _PIPE_DEPENDENCY_ERRORS as error:
        _capture_write(capture, "error", error)
    finally:
        try:
            _close_probe_pipe(stream, "capture pipe")
        except _PIPE_DEPENDENCY_ERRORS as error:
            original = cast("Exception | None", _capture_read(capture, "error"))
            if original is None:
                _capture_write(capture, "error", error)
            else:
                BaseException.add_note(
                    original,
                    "probe capture pipe close also failed: "
                    + _safe_probe_error_detail(error),
                )
    # A BaseException escaping the worker must remain visibly incomplete.
    _capture_write(capture, "finished", True)


def _write_complete_probe_stdin(stream: IO[bytes], data: bytes) -> None:
    written = stream.write(data)
    if _NATIVE_TYPE(written) is not _NATIVE_INT or written != _NATIVE_LEN(data):
        message = "probe stdin reported short or invalid byte count"
        raise ValueError(message)


def _feed_stdin(
    stream: IO[bytes],
    data: bytes,
    errors: list[Exception],
    *,
    completed: threading.Event,
) -> None:
    """Write stdin and acknowledge only a clean worker completion."""
    wrote = False
    try:
        _write_complete_probe_stdin(stream, data)
        wrote = True
    except _NATIVE_BROKEN_PIPE_ERROR:
        wrote = True
    except _PIPE_DEPENDENCY_ERRORS as error:
        errors.append(error)
    finally:
        try:
            _close_probe_pipe(stream, "stdin")
        except _PIPE_DEPENDENCY_ERRORS as error:
            errors.append(error)
    if wrote and not errors:
        completed.set()


def _signal_probe_group(process: subprocess.Popen[bytes]) -> OSError | None:
    """Report a group signal failure without skipping direct child cleanup.

    Returns:
        The group-signal error, if any.

    """
    try:
        _NATIVE_OS_KILL(-process.pid, _NATIVE_GROUP_SIGNAL)
    except _NATIVE_PROCESS_LOOKUP_ERROR:
        return None
    except _NATIVE_OS_ERROR as error:
        return error
    return None


def _kill_direct_probe_child(
    process: subprocess.Popen[bytes],
) -> OSError | None:
    """Attempt direct termination and preserve any error for later.

    Returns:
        The direct-child kill error, if any.

    """
    if process.poll() is not None:
        return None
    failure: OSError | None = None
    try:
        process.kill()
    except _NATIVE_PROCESS_LOOKUP_ERROR:
        failure = None
    except _NATIVE_OS_ERROR as error:
        failure = error
    return failure


def _stop_child(process: subprocess.Popen[bytes]) -> None:
    """Stop descendants and reap the direct child even if group signal fails.

    Raises:
        ProbeExecutionError: Group cleanup, direct kill, or reaping failed.

    """
    group_error = (
        _signal_probe_group(process) if os.name == _POSIX_OS_NAME else None
    )
    direct_error = (
        _kill_direct_probe_child(process)
        if os.name != _POSIX_OS_NAME or group_error is not None
        else None
    )
    try:
        _ = process.wait(timeout=_CHILD_REAP_SECONDS)
    except (*_PIPE_DEPENDENCY_ERRORS, _NATIVE_SUBPROCESS_TIMEOUT) as error:
        message = (
            "probe direct child reaping failed: "
            + _safe_probe_error_detail(error)
        )
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error
    if direct_error is not None:
        message = (
            "probe direct child termination failed: "
            + _safe_probe_error_detail(direct_error)
        )
        failure = _NATIVE_PROBE_EXECUTION_ERROR(message)
        if group_error is not None:
            BaseException.add_note(
                failure,
                "probe process group cleanup failed: "
                + _safe_probe_error_detail(group_error),
            )
        raise failure from direct_error
    if group_error is not None:
        message = (
            "probe process group cleanup failed: "
            + _safe_probe_error_detail(group_error)
        )
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from group_error


def _spawn_probe(
    argv: list[str], scratch_root: Path
) -> subprocess.Popen[bytes]:
    """Start a no-shell probe, normalizing host launch errors.

    Returns:
        Running binary-mode child with three explicit pipes.

    Raises:
        ProbeExecutionError: The executable could not start.

    """
    if (
        subprocess.Popen is not _IMPORTED_POPEN
        or subprocess.PIPE is not _NATIVE_SUBPROCESS_PIPE
    ):
        message = "probe native subprocess launch aliases changed"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    try:
        return _NATIVE_POPEN(
            argv,
            cwd=scratch_root,
            stdin=_NATIVE_SUBPROCESS_PIPE,
            stdout=_NATIVE_SUBPROCESS_PIPE,
            stderr=_NATIVE_SUBPROCESS_PIPE,
            shell=False,
            start_new_session=os.name == _POSIX_OS_NAME,
        )
    except _PIPE_DEPENDENCY_ERRORS as error:
        message = "probe command launch failed: " + _safe_probe_error_detail(
            error
        )
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error


def _capture_pipes(
    process: subprocess.Popen[bytes],
) -> tuple[IO[bytes], IO[bytes]]:
    """Recover required process pipe handles or reject the probe.

    Returns:
        Standard output and standard error pipe streams.

    Raises:
        ProbeExecutionError: A capture pipe is unavailable.

    """
    if process.stdout is None or process.stderr is None:
        message = "probe subprocess capture pipes are unavailable"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    return process.stdout, process.stderr


def _start_writer(
    process: subprocess.Popen[bytes],
    data: bytes,
    errors: list[Exception],
    *,
    completed: threading.Event,
) -> threading.Thread | None:
    """Close empty stdin immediately or send input asynchronously.

    Returns:
        Optional running writer thread.

    Raises:
        ProbeExecutionError: Stdin was not created.

    """
    stream = process.stdin
    if stream is None:
        message = "probe subprocess stdin pipe is unavailable"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    if not data:
        _close_probe_pipe(stream, "stdin")
        return None
    writer = threading.Thread(
        target=_feed_stdin,
        args=(stream, data, errors),
        kwargs={"completed": completed},
        name="probe-stdin-writer",
        daemon=True,
    )
    writer.start()
    return writer


def _safe_probe_error_detail(error: BaseException) -> str:
    """Describe native host faults without formatting foreign objects.

    Returns:
        A native single-string reason or an exception class name.

    """
    if _NATIVE_TYPE(error) in (
        _NATIVE_OS_ERROR,
        _NATIVE_RUNTIME_ERROR,
        _NATIVE_VALUE_ERROR,
        _NATIVE_EXACT_TREE_ERROR,
        _NATIVE_PROBE_EXECUTION_ERROR,
    ):
        # Exact native error classes can still acquire late class getters.
        # Fetch the BaseException slot without dispatching through those hooks.
        arguments = cast(
            "tuple[object, ...]",
            BaseException.__getattribute__(  # ruff: ignore[unnecessary-dunder-call]
                error, "args"
            ),
        )
        if (
            _NATIVE_LEN(arguments) == 1
            and _NATIVE_TYPE(arguments[0]) is _NATIVE_STR
        ):
            return arguments[0]
    return _NATIVE_TYPE(error).__name__


def _close_unowned_pipe(
    stream: IO[bytes] | None,
    worker: threading.Thread | None,
    failure: Exception,
) -> None:
    """Close only pipes with no live worker to release their descriptors."""
    if stream is None or (worker is not None and worker.is_alive()):
        return
    try:
        _close_probe_pipe(stream, "unused pipe")
    except _PIPE_DEPENDENCY_ERRORS as error:
        BaseException.add_note(
            failure,
            "probe unused pipe close failed: "
            + _safe_probe_error_detail(error),
        )


def _start_capture(
    process: subprocess.Popen[bytes], command: ProbeCommand
) -> _RunningProbe:
    """Start bounded readers and the full-duplex stdin writer.

    Returns:
        Process, stream states and active pipe workers.

    Raises:
        OSError: A pipe worker or stdin stream could not start.
        RuntimeError: A pipe worker could not start.
        ValueError: A pipe worker or stdin stream was invalid.

    """
    stdout_pipe, stderr_pipe = _capture_pipes(process)
    stdout = _new_pipe_capture(
        cast("int", _probe_field(command, ProbeCommand, "max_stdout_bytes"))
    )
    stderr = _new_pipe_capture(
        cast("int", _probe_field(command, ProbeCommand, "max_stderr_bytes"))
    )
    readers = (
        threading.Thread(
            target=_drain_pipe, args=(stdout_pipe, stdout), daemon=True
        ),
        threading.Thread(
            target=_drain_pipe, args=(stderr_pipe, stderr), daemon=True
        ),
    )
    try:
        for reader in readers:
            reader.start()
        stdin_errors: list[Exception] = []
        stdin_complete = threading.Event()
        writer = _start_writer(
            process,
            cast("bytes", _probe_field(command, ProbeCommand, "stdin")),
            stdin_errors,
            completed=stdin_complete,
        )
    except _PIPE_DEPENDENCY_ERRORS as error:
        # Never close a stream underneath a reader still draining it.
        for pipe, reader in _NATIVE_ZIP(
            (stdout_pipe, stderr_pipe), readers, strict=True
        ):
            _close_unowned_pipe(pipe, reader, error)
        _close_unowned_pipe(process.stdin, None, error)
        raise
    return _new_running_probe(
        process, stdout, stderr, readers, writer, stdin_errors, stdin_complete
    )


def _require_healthy_pipes(running: _RunningProbe) -> None:
    """Reject output quotas and pipe errors before consuming more memory.

    Raises:
        ProbeExecutionError: A stream exceeded its quota or failed.

    """
    stdout = cast("_PipeCapture", _running_read(running, "stdout"))
    stderr = cast("_PipeCapture", _running_read(running, "stderr"))
    if cast("bool", _capture_read(stdout, "exceeded")):
        message = "probe command exceeded stdout limit"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    if cast("bool", _capture_read(stderr, "exceeded")):
        message = "probe command exceeded stderr limit"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    if (
        _capture_read(stdout, "error") is not None
        or _capture_read(stderr, "error") is not None
        or cast("list[Exception]", _running_read(running, "stdin_errors"))
    ):
        message = "probe command pipe communication failed"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    _require_finished_workers(running)


def _require_finished_workers(running: _RunningProbe) -> None:
    """Reject capture workers that terminate without clean completion.

    Raises:
        ProbeExecutionError: A worker quit without reporting its outcome.

    """
    captures = (
        cast("_PipeCapture", _running_read(running, "stdout")),
        cast("_PipeCapture", _running_read(running, "stderr")),
    )
    reader_failed = _NATIVE_ANY(
        not reader.is_alive() and not cast("bool", _capture_read(capture, "finished"))
        for reader, capture in _NATIVE_ZIP(
            cast(
                "tuple[threading.Thread, threading.Thread]",
                _running_read(running, "readers"),
            ),
            captures,
            strict=True,
        )
    )
    writer = cast("threading.Thread | None", _running_read(running, "writer"))
    writer_failed = (
        writer is not None
        and not writer.is_alive()
        and not cast(
            "threading.Event", _running_read(running, "stdin_complete")
        ).is_set()
    )
    if reader_failed or writer_failed:
        message = "probe command pipe communication failed"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)


def _capture_complete(running: _RunningProbe) -> bool:
    writer = cast("threading.Thread | None", _running_read(running, "writer"))
    process = cast("subprocess.Popen[bytes]", _running_read(running, "process"))
    readers = cast(
        "tuple[threading.Thread, threading.Thread]", _running_read(running, "readers")
    )
    return (
        process.poll() is not None
        and _NATIVE_ALL(not reader.is_alive() for reader in readers)
        and (writer is None or not writer.is_alive())
    )


def _wait_for_bounded_pipes(running: _RunningProbe, deadline: float) -> None:
    """Monitor pipe quotas against the deadline established before launch.

    Raises:
        ProbeExecutionError: A quota, pipe, or timeout failed.

    """
    while True:
        _require_healthy_pipes(running)
        if time.monotonic() >= deadline:
            message = "probe command exceeded its timeout"
            raise _NATIVE_PROBE_EXECUTION_ERROR(message)
        if _capture_complete(running):
            return
        time.sleep(_POLL_SECONDS)


def _start_capture_checked(
    process: subprocess.Popen[bytes], command: ProbeCommand
) -> _RunningProbe:
    """Normalize worker startup failures to the probe execution boundary.

    Returns:
        Active bounded capture readers and optional stdin writer.

    Raises:
        ProbeExecutionError: Starting stream workers failed.

    """
    try:
        return _start_capture(process, command)
    except _PIPE_DEPENDENCY_ERRORS as error:
        message = "probe worker startup failed: " + _safe_probe_error_detail(
            error
        )
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error


def _close_failed_running_pipes(running: _RunningProbe, failure: Exception) -> None:
    """Reclaim pipes from workers that aborted before their normal close."""
    process = cast("subprocess.Popen[bytes]", _running_read(running, "process"))
    _close_unowned_pipe(
        process.stdin,
        cast("threading.Thread | None", _running_read(running, "writer")),
        failure,
    )
    for pipe, reader in _NATIVE_ZIP(
        (process.stdout, process.stderr),
        cast(
            "tuple[threading.Thread, threading.Thread]",
            _running_read(running, "readers"),
        ),
        strict=True,
    ):
        _close_unowned_pipe(pipe, reader, failure)


def _probe_wall_deadline(timeout_ms: int) -> float:
    """Compute a bounded deadline without leaking integer conversion errors.

    Returns:
        The monotonic wall deadline for process execution and pipe draining.

    Raises:
        ProbeExecutionError: Timeout cannot be represented in host time units.

    """
    try:
        return time.monotonic() + timeout_ms / 1000
    except _NATIVE_OVERFLOW_ERROR as error:
        message = "probe command has an unrepresentable timeout"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error


def _launch_command(
    argv: list[str], command: ProbeCommand, scratch_root: Path
) -> _CapturedProcess:
    """Bound streamed child stdout and stderr before making a transcript.

    Returns:
        Completed process with quota-admitted captured observations.

    """
    deadline = _probe_wall_deadline(
        cast("int", _probe_field(command, ProbeCommand, "timeout_ms"))
    )
    process = _spawn_probe(argv, scratch_root)
    running: _RunningProbe | None = None
    try:
        running = _start_capture_checked(process, command)
        _wait_for_bounded_pipes(running, deadline)
        completed = _new_captured_process(
            returncode=process.wait(),
            stdout=b"".join(
                cast(
                    "list[bytes]",
                    _capture_read(
                        cast("_PipeCapture", _running_read(running, "stdout")),
                        "fragments",
                    ),
                )
            ),
            stderr=b"".join(
                cast(
                    "list[bytes]",
                    _capture_read(
                        cast("_PipeCapture", _running_read(running, "stderr")),
                        "fragments",
                    ),
                )
            ),
        )
    except _NATIVE_EXCEPTION as error:
        try:
            _stop_child(process)
        except _NATIVE_PROBE_EXECUTION_ERROR as cleanup_error:
            BaseException.add_note(
                error,
                "probe child cleanup also failed: "
                + _safe_probe_error_detail(cleanup_error),
            )
        if running is not None:
            _close_failed_running_pipes(running, error)
        raise
    else:
        # A successful leader may have left detached-stdio descendants in its
        # dedicated POSIX process group. Do not let them outlive the probe.
        _stop_child(process)
        return completed


def _run_command(
    command: ProbeCommand,
    context: ProbeRunContext,
    scratch_root: Path,
) -> _CommandResult:
    argv = _command_argv(command, context, scratch_root)
    completed = _launch_command(argv, command, scratch_root)
    stdout = cast("bytes", _captured_field(completed, "stdout"))
    stderr = cast("bytes", _captured_field(completed, "stderr"))
    returncode = cast("int", _captured_field(completed, "returncode"))
    if _NATIVE_LEN(stdout) > cast(
        "int", _probe_field(command, ProbeCommand, "max_stdout_bytes")
    ):
        message = "probe command exceeded stdout limit"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    if _NATIVE_LEN(stderr) > cast(
        "int", _probe_field(command, ProbeCommand, "max_stderr_bytes")
    ):
        message = "probe command exceeded stderr limit"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    if cast(
        "int | None", _probe_field(command, ProbeCommand, "expected_exit_code")
    ) is not None and returncode != cast(
        "int | None", _probe_field(command, ProbeCommand, "expected_exit_code")
    ):
        message = "probe command returned an unexpected exit code"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    return _new_command_result(
        stdout=stdout,
        returncode=returncode,
    )


def _update_stdout_digest(
    hasher: _HashUpdater,
    command_index: int,
    stdout: bytes,
) -> None:
    index_bytes = command_index.to_bytes(_FRAME_LENGTH_BYTES, byteorder="big")
    length_bytes = _NATIVE_LEN(stdout).to_bytes(
        _FRAME_LENGTH_BYTES, byteorder="big"
    )
    hasher.update(b"O")
    hasher.update(index_bytes)
    hasher.update(length_bytes)
    hasher.update(stdout)


def _update_exit_digest(
    hasher: _HashUpdater,
    command_index: int,
    returncode: int,
) -> None:
    index_bytes = command_index.to_bytes(_FRAME_LENGTH_BYTES, byteorder="big")
    code_bytes = _NATIVE_INT(returncode).to_bytes(
        _FRAME_LENGTH_BYTES, byteorder="big", signed=True
    )
    hasher.update(b"E")
    hasher.update(index_bytes)
    hasher.update(code_bytes)


def _temporary_probe_root(
    prefix: str, *, parent: Path
) -> tempfile.TemporaryDirectory[str]:
    try:
        return _NATIVE_TEMPORARY_DIRECTORY(prefix=prefix, dir=parent)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_probe_error_detail(error)
        message = f"probe temporary root failed: {detail}"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error


def _run_program(
    program: ProbeProgram,
    context: ProbeRunContext,
    baseline: TreeSnapshot,
    temporary_parent: Path,
) -> ProbeTranscript:
    hasher = _native_sha256()
    digested_commands = _ZERO
    with _temporary_probe_root(
        "diff-probe-", parent=temporary_parent
    ) as scratch:
        scratch_root = Path(scratch)
        for command_index, command in _NATIVE_ENUMERATE(
            cast(
                "tuple[ProbeCommand, ...]",
                _probe_field(program, ProbeProgram, "commands"),
            )
        ):
            try:
                result = _run_command(command, context, scratch_root)
            finally:
                _require_mirror_unchanged(
                    cast("Path", _probe_field(context, ProbeRunContext, "source_root")),
                    baseline,
                )
            selected = False
            if cast("bool", _probe_field(command, ProbeCommand, "digest_stdout")):
                _update_stdout_digest(hasher, command_index, _command_result_stdout(result))
                selected = True
            if cast("bool", _probe_field(command, ProbeCommand, "digest_exit_code")):
                _update_exit_digest(hasher, command_index, _command_result_returncode(result))
                selected = True
            if selected:
                digested_commands += 1
    return _new_probe_transcript(
        probe_id=cast("str", _probe_field(program, ProbeProgram, "probe_id")),
        digest=hasher.digest(),
        digested_commands=digested_commands,
    )


def _validate_probe_batch(
    programs: object, context: object
) -> tuple[ProbeProgram, ...]:
    if _NATIVE_TYPE(programs) is not _NATIVE_TUPLE:
        message = "probe program batch must use the exact immutable tuple type"
        raise ProbeProgramError(message)
    items = cast("tuple[object, ...]", programs)
    if _NATIVE_ANY(
        _NATIVE_TYPE(program) is not ProbeProgram for program in items
    ):
        message = "probe program batch contains a foreign program record"
        raise ProbeProgramError(message)
    admitted = cast("tuple[ProbeProgram, ...]", programs)
    if _NATIVE_TYPE(context) is not ProbeRunContext:
        message = "probe run context must use the exact ProbeRunContext type"
        raise ProbeProgramError(message)
    # Exact native records can be allocated without their original constructors.
    # Revalidate all nested metadata before any filesystem or process preflight.
    try:
        _PROBE_RUN_CONTEXT_VALIDATOR(cast("ProbeRunContext", context))
        for program in admitted:
            _PROBE_PROGRAM_VALIDATOR(program)
            commands = cast(
                "tuple[ProbeCommand, ...]", _probe_field(program, ProbeProgram, "commands")
            )
            for command in commands:
                _PROBE_COMMAND_VALIDATOR(command)
                executable = _probe_field(command, ProbeCommand, "executable")
                if _NATIVE_TYPE(executable) is ToolExecutable:
                    _TOOL_EXECUTABLE_VALIDATOR(cast("ToolExecutable", executable))
                else:
                    _ROOTED_EXECUTABLE_VALIDATOR(cast("RootedExecutable", executable))
                arguments = cast(
                    "tuple[ProbeArgument, ...]",
                    _probe_field(command, ProbeCommand, "arguments"),
                )
                for argument in arguments:
                    if _NATIVE_TYPE(argument) is PathArgument:
                        _PATH_ARGUMENT_VALIDATOR(cast("PathArgument", argument))
    except _NATIVE_ATTRIBUTE_ERROR as error:
        message = "probe batch contains incomplete native metadata"
        raise ProbeProgramError(message) from error
    identifiers = _NATIVE_TUPLE(
        cast("str", _probe_field(program, ProbeProgram, "probe_id"))
        for program in admitted
    )
    if identifiers != _NATIVE_TUPLE(_NATIVE_SORTED(_NATIVE_SET(identifiers))):
        message = "probe programs must have unique sorted identifiers"
        raise ProbeProgramError(message)
    return admitted


def _snapshot_probe_tree(root: Path, context: str) -> TreeSnapshot:
    """Validate a byte-tree before any probe or source mirror can use it.

    Returns:
        A regular-file-only tree snapshot.

    Raises:
        ProbeExecutionError: The tree is unreadable, linked, or unsafe.

    """
    try:
        return snapshot_tree(root)
    except _NATIVE_EXACT_TREE_ERROR as error:
        detail = _safe_probe_error_detail(error)
        message = f"probe {context} snapshot rejected: {detail}"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error


def _native_inode_status(receipt: object, context: str) -> os.stat_result:
    """Require an OS-provided identity receipt before trusting inode fields."""
    if _NATIVE_TYPE(receipt) is not _NATIVE_STAT_RESULT:
        message = f"probe {context} inode status must be native"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    return receipt


def _source_file_inode_keys(source: Path) -> frozenset[tuple[int, int]]:
    """Read the stat identities of admitted regular source files.

    Returns:
        The filesystem device/inode pairs of admitted files.

    Raises:
        ProbeExecutionError: Source identity changed during preflight.

    """
    files = _native_snapshot_files(_snapshot_probe_tree(source, "source"))
    try:
        return _NATIVE_FROZENSET(
            (status.st_dev, status.st_ino)
            for record in files
            for status in (
                _native_inode_status(
                    _NATIVE_PATH_STAT(
                        source / _native_file_fields(record)[0]
                    ),
                    "source",
                ),
            )
        )
    except _NATIVE_PROBE_EXECUTION_ERROR:
        raise
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_probe_error_detail(error)
        message = f"probe source inode status failed: {detail}"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error


def _repository_inode_status(path: Path) -> os.stat_result | None:
    """Inspect an existing repository file without requiring its existence.

    Returns:
        The status of an existing path, or None when missing.

    Raises:
        ProbeExecutionError: Repository inode status is unavailable.

    """
    try:
        return _native_inode_status(_NATIVE_PATH_STAT(path), "repository")
    except _NATIVE_PROBE_EXECUTION_ERROR:
        raise
    except _NATIVE_FILE_NOT_FOUND_ERROR:
        return None
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_probe_error_detail(error)
        message = f"probe repository path status failed: {detail}"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error


def _require_disjoint_source_inode(source: Path, path: Path) -> None:
    """Reject a repository hardlink to an admitted source file inode.

    Raises:
        ProbeExecutionError: A repository alias shares source file identity.

    """
    status = _repository_inode_status(path)
    if status is None or not S_ISREG(status.st_mode):
        return
    if status.st_nlink < _MIN_HARDLINK_COUNT:
        return
    if (status.st_dev, status.st_ino) in _source_file_inode_keys(source):
        message = "probe repository path aliases original source inode"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)


def _require_repository_argument_disjoint(
    argument: ProbeExecutable | ProbeArgument,
    context: ProbeRunContext,
    original_source: Path,
) -> None:
    """Reject structured repository paths aliasing the original source.

    Raises:
        ProbeExecutionError: The path resolves inside the original source tree.

    """
    if not _NATIVE_ISINSTANCE(argument, (PathArgument, RootedExecutable)):
        return
    if (
        cast("ProbeRoot", _probe_field(argument, _NATIVE_TYPE(argument), "root"))
        is not ProbeRoot.REPOSITORY
    ):
        return
    path = _rooted_path(argument, context, original_source)
    _require_native_host_resolver()
    try:
        resolved = _NATIVE_PATH_RESOLVE(path)
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        detail = _safe_probe_error_detail(error)
        message = f"probe repository argument resolution failed: {detail}"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error
    _require_native_host_resolver()
    resolved = _native_resolved_path(resolved, "repository argument")
    if _native_path_inside(resolved, original_source):
        message = "probe repository path overlaps original source tree"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    _require_disjoint_source_inode(original_source, resolved)


def _require_repository_paths_disjoint(
    programs: tuple[ProbeProgram, ...], context: ProbeRunContext
) -> None:
    """Check structured repo paths before mirroring the admitted source."""
    source = _resolved_root(
        cast("Path", _probe_field(context, ProbeRunContext, "source_root")), "source"
    )
    for program in programs:
        for command in cast(
            "tuple[ProbeCommand, ...]", _probe_field(program, ProbeProgram, "commands")
        ):
            _require_repository_argument_disjoint(
                cast(
                    "ProbeExecutable", _probe_field(command, ProbeCommand, "executable")
                ),
                context,
                source,
            )
            for argument in cast(
                "tuple[ProbeArgument, ...]",
                _probe_field(command, ProbeCommand, "arguments"),
            ):
                _require_repository_argument_disjoint(argument, context, source)


def _snapshots_match_native(left: TreeSnapshot, right: TreeSnapshot) -> bool:
    """Compare native file slots without mutable dataclass equality hooks."""
    left_fields = _NATIVE_TUPLE(
        _native_file_fields(record) for record in _native_snapshot_files(left)
    )
    right_fields = _NATIVE_TUPLE(
        _native_file_fields(record) for record in _native_snapshot_files(right)
    )
    return left_fields == right_fields


def _require_mirror_unchanged(root: Path, baseline: TreeSnapshot) -> None:
    """Reject a persistent mirror change after every executed command.

    Raises:
        ProbeExecutionError: The isolated source mirror no longer matches.

    """
    if not _snapshots_match_native(
        _snapshot_probe_tree(root, "isolated source mirror"), baseline
    ):
        message = "behavior probe modified its isolated source mirror"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)


def _run_isolated_batch(
    programs: tuple[ProbeProgram, ...], context: ProbeRunContext
) -> tuple[ProbeTranscript, ...]:
    source = _snapshot_probe_tree(
        cast("Path", _probe_field(context, ProbeRunContext, "source_root")), "source"
    )
    # A host TMPDIR inside the source would copy the new batch directory into
    # itself recursively. Reject before creating any temporary directories.
    _require_native_host_resolver()
    try:
        temporary_parent = _NATIVE_PATH_RESOLVE(Path(_NATIVE_GETTEMPDIR()))
    except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
        message = "probe temporary parent resolution failed"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error
    _require_native_host_resolver()
    temporary_parent = _native_resolved_path(
        temporary_parent, "temporary parent"
    )
    original_source = _resolved_root(
        cast("Path", _probe_field(context, ProbeRunContext, "source_root")), "source"
    )
    if _native_path_inside(temporary_parent, original_source):
        message = "probe temporary parent overlaps original source tree"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)
    with _temporary_probe_root(
        "diff-probe-batch-", parent=temporary_parent
    ) as batch:
        batch_root = Path(batch)
        try:
            mirror_root = Path(
                _NATIVE_COPYTREE(
                    cast("Path", _probe_field(context, ProbeRunContext, "source_root")),
                    batch_root / "source",
                    symlinks=True,
                )
            )
        except (
        _NATIVE_OS_ERROR, _NATIVE_VALUE_ERROR, _NATIVE_RUNTIME_ERROR
    ) as error:
            detail = _safe_probe_error_detail(error)
            message = f"probe source mirror creation failed: {detail}"
            raise _NATIVE_PROBE_EXECUTION_ERROR(message) from error
        isolated = ProbeRunContext(
            source_root=mirror_root,
            repository_root=cast(
                "Path", _probe_field(context, ProbeRunContext, "repository_root")
            ),
            tools=cast(
                "tuple[tuple[str, Path], ...]",
                _probe_field(context, ProbeRunContext, "tools"),
            ),
            enforce_source_immutable=False,
        )
        baseline = _snapshot_probe_tree(mirror_root, "isolated source mirror")
        if not _snapshots_match_native(baseline, source):
            message = "probe source tree changed while creating its mirror"
            raise _NATIVE_PROBE_EXECUTION_ERROR(message)
        transcripts: list[ProbeTranscript] = []
        for program in programs:
            transcripts.append(
                _run_program(program, isolated, baseline, temporary_parent)
            )
            _require_mirror_unchanged(mirror_root, baseline)
        return _NATIVE_TUPLE(transcripts)


def _require_original_source_unchanged(
    context: ProbeRunContext, baseline: TreeSnapshot | None
) -> None:
    """Verify original source after success and after child execution failure.

    Raises:
        ProbeExecutionError: The original source has changed or is unreadable.

    """
    if baseline is None:
        return
    source_root = cast(
        "Path", _probe_field(context, ProbeRunContext, "source_root")
    )
    if not _snapshots_match_native(
        _snapshot_probe_tree(source_root, "source"), baseline
    ):
        message = "behavior probe modified candidate source tree"
        raise _NATIVE_PROBE_EXECUTION_ERROR(message)


def run_probe_programs(
    programs: tuple[ProbeProgram, ...],
    context: ProbeRunContext,
) -> tuple[ProbeTranscript, ...]:
    """Execute a sorted unique probe batch while protecting the source tree.

    Returns:
        Transcripts in probe-id order.

    """
    admitted = _validate_probe_batch(programs, context)
    _require_repository_paths_disjoint(admitted, context)
    before = (
        _snapshot_probe_tree(
            cast("Path", _probe_field(context, ProbeRunContext, "source_root")),
            "source",
        )
        if cast(
            "bool", _probe_field(context, ProbeRunContext, "enforce_source_immutable")
        )
        else None
    )
    try:
        transcripts = _run_isolated_batch(admitted, context)
    finally:
        _require_original_source_unchanged(context, before)
    return transcripts


def run_probe_program(
    program: ProbeProgram,
    context: ProbeRunContext,
) -> ProbeTranscript:
    """Execute one portable probe program.

    Returns:
        The deterministic selected-stdout transcript digest.

    """
    return run_probe_programs((program,), context)[0]
