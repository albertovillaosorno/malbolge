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

from dataclasses import dataclass
from dataclasses import replace
from enum import StrEnum
import hashlib
from pathlib import Path
from pathlib import PurePosixPath
import shutil
from stat import S_ISREG

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - no shell; resolved executables only.
import tempfile
from typing import Protocol
from typing import cast

from algorithms.diff.exact import snapshot_tree

_ZERO = 0
_ONE = 1
_DEFAULT_TIMEOUT_MS = 10_000
_DEFAULT_OUTPUT_LIMIT = 1_048_576
_FRAME_LENGTH_BYTES = 8
_BACKSLASH = "\\"
_PARENT = ".."
_TOOL_BINDING_LENGTH = 2


class _HashUpdater(Protocol):
    """Minimal digest-update boundary used by transcript framing."""

    def update(self, data: bytes, /) -> None:
        """Consume one exact byte fragment."""
        ...


class ProbeProgramError(ValueError):
    """Raised when a portable probe program is malformed."""


class ProbeExecutionError(RuntimeError):
    """Raised when a probe cannot execute deterministically and safely."""


class ProbeRoot(StrEnum):
    """Authorized roots available to structured probe paths."""

    SOURCE = "source"
    REPOSITORY = "repository"
    SCRATCH = "scratch"


@dataclass(frozen=True, slots=True)
class PathArgument:
    """One argv path resolved beneath an authorized probe root."""

    root: ProbeRoot
    relative_path: str

    def __post_init__(self) -> None:
        """Reject foreign roots and unsafe relative paths."""
        _validate_probe_root(self.root)
        _validate_relative_path(self.relative_path)


ProbeArgument = str | PathArgument


@dataclass(frozen=True, slots=True)
class ToolExecutable:
    """Executable resolved through a logical consumer tool identifier."""

    tool_id: str

    def __post_init__(self) -> None:
        """Require a non-empty logical tool identifier.

        Raises:
            ProbeProgramError: The tool identifier is empty.

        """
        if type(self.tool_id) is not str or not self.tool_id:
            message = "probe tool identifier must be a non-empty string"
            raise ProbeProgramError(message)


@dataclass(frozen=True, slots=True)
class RootedExecutable:
    """Executable artifact produced or stored beneath an authorized root."""

    root: ProbeRoot
    relative_path: str

    def __post_init__(self) -> None:
        """Reject foreign roots and unsafe executable paths."""
        _validate_probe_root(self.root)
        _validate_relative_path(self.relative_path)


ProbeExecutable = ToolExecutable | RootedExecutable


def _validate_command_shape(command: ProbeCommand) -> None:
    if type(command.executable) not in {ToolExecutable, RootedExecutable}:
        message = "probe executable must use an exact executable record"
        raise ProbeProgramError(message)
    if type(command.arguments) is not tuple:
        message = "probe arguments must use the exact immutable tuple type"
        raise ProbeProgramError(message)
    if any(
        type(argument) not in {str, PathArgument}
        for argument in command.arguments
    ):
        message = "probe arguments contain a foreign argument record"
        raise ProbeProgramError(message)
    if type(command.stdin) is not bytes:
        message = "probe stdin must use exact bytes"
        raise ProbeProgramError(message)


def _validate_command_integer(
    value: object, context: str, *, positive: bool
) -> None:
    if type(value) is not int:
        message = f"{context} must use the exact integer type"
        raise ProbeProgramError(message)
    minimum = _ONE if positive else _ZERO
    if value < minimum:
        qualifier = "positive" if positive else "non-negative"
        message = f"{context} must be {qualifier}"
        raise ProbeProgramError(message)


def _validate_command_limits(command: ProbeCommand) -> None:
    if command.expected_exit_code is not None:
        _validate_command_integer(
            command.expected_exit_code,
            "probe expected exit code",
            positive=False,
        )
    _validate_command_integer(
        command.timeout_ms, "probe timeout", positive=True
    )
    _validate_command_integer(
        command.max_stdout_bytes, "probe stdout limit", positive=False
    )
    _validate_command_integer(
        command.max_stderr_bytes, "probe stderr limit", positive=False
    )
    if type(command.digest_stdout) is not bool:
        message = "probe stdout digest selector must use an exact boolean"
        raise ProbeProgramError(message)
    if type(command.digest_exit_code) is not bool:
        message = "probe exit digest selector must use an exact boolean"
        raise ProbeProgramError(message)


@dataclass(frozen=True, slots=True)
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

    def __post_init__(self) -> None:
        """Reject unbounded or nonsensical process limits."""
        _validate_command_shape(self)
        _validate_command_limits(self)


@dataclass(frozen=True, slots=True)
class ProbeProgram:
    """Bounded command sequence for one behavior observation."""

    probe_id: str
    commands: tuple[ProbeCommand, ...]

    def __post_init__(self) -> None:
        """Require an identifier and at least one command.

        Raises:
            ProbeProgramError: Program identity or command sequence is empty.

        """
        if type(self.probe_id) is not str or not self.probe_id:
            message = "probe program identifier must be a non-empty string"
            raise ProbeProgramError(message)
        if type(self.commands) is not tuple:
            message = "probe commands must use the exact immutable tuple type"
            raise ProbeProgramError(message)
        if not self.commands:
            message = "probe program requires at least one command"
            raise ProbeProgramError(message)
        if any(type(command) is not ProbeCommand for command in self.commands):
            message = "probe program contains a foreign command record"
            raise ProbeProgramError(message)


def _validate_path(value: object, context: str) -> None:
    if not isinstance(value, Path):
        message = f"{context} must use a pathlib Path value"
        raise ProbeProgramError(message)


def _validate_tool_binding(binding: object) -> tuple[str, Path]:
    if type(binding) is not tuple:
        message = "probe tool binding must be an exact pair"
        raise ProbeProgramError(message)
    pair = cast("tuple[object, ...]", binding)
    if len(pair) != _TOOL_BINDING_LENGTH:
        message = "probe tool binding must be an exact pair"
        raise ProbeProgramError(message)
    tool_id, tool_path = pair
    if type(tool_id) is not str or not tool_id:
        message = "probe tool identifiers must be non-empty strings"
        raise ProbeProgramError(message)
    _validate_path(tool_path, "probe tool path")
    return tool_id, cast("Path", tool_path)


def _validate_tool_bindings(value: object) -> tuple[str, ...]:
    if type(value) is not tuple:
        message = "probe tool bindings must use the exact immutable tuple type"
        raise ProbeProgramError(message)
    bindings = cast("tuple[object, ...]", value)
    identifiers = tuple(
        _validate_tool_binding(binding)[0] for binding in bindings
    )
    if identifiers != tuple(sorted(set(identifiers))):
        message = "probe tool bindings must be unique and sorted"
        raise ProbeProgramError(message)
    return identifiers


@dataclass(frozen=True, slots=True)
class ProbeRunContext:
    """Roots and logical tool bindings used while executing probe programs."""

    source_root: Path
    repository_root: Path
    tools: tuple[tuple[str, Path], ...]
    enforce_source_immutable: bool = True

    def __post_init__(self) -> None:
        """Require deterministic unique tool bindings.

        Raises:
            ProbeProgramError: Tool identifiers are empty, duplicate, or
            unsorted.

        """
        _validate_path(self.source_root, "probe source root")
        _validate_path(self.repository_root, "probe repository root")
        _ = _validate_tool_bindings(self.tools)
        if type(self.enforce_source_immutable) is not bool:
            message = "probe source-immutability flag must use an exact boolean"
            raise ProbeProgramError(message)


@dataclass(frozen=True, slots=True)
class ProbeTranscript:
    """Stable digest of explicitly selected process observations."""

    probe_id: str
    digest: bytes
    digested_commands: int


@dataclass(frozen=True, slots=True)
class _CommandResult:
    stdout: bytes
    returncode: int


def _validate_probe_root(root: object) -> None:
    if type(root) is not ProbeRoot:
        message = "probe root must use the exact ProbeRoot type"
        raise ProbeProgramError(message)


def _validate_relative_path(relative_path: object) -> None:
    if type(relative_path) is not str:
        message = "probe relative path must use the exact string type"
        raise ProbeProgramError(message)
    candidate = PurePosixPath(relative_path)
    unsafe = (
        not relative_path
        or _BACKSLASH in relative_path
        or candidate.is_absolute()
        or _PARENT in candidate.parts
        or candidate.as_posix() != relative_path
    )
    if unsafe:
        message = f"unsafe probe relative path: {relative_path!r}"
        raise ProbeProgramError(message)


def _root_path(
    root: ProbeRoot,
    context: ProbeRunContext,
    scratch_root: Path,
) -> Path:
    if root is ProbeRoot.SOURCE:
        return context.source_root.resolve()
    if root is ProbeRoot.REPOSITORY:
        return context.repository_root.resolve()
    return scratch_root.resolve()


def _rooted_path(
    argument: PathArgument | RootedExecutable,
    context: ProbeRunContext,
    scratch_root: Path,
) -> Path:
    root = _root_path(argument.root, context, scratch_root)
    candidate = root.joinpath(*PurePosixPath(argument.relative_path).parts)
    try:
        _ = candidate.resolve().relative_to(root)
    except ValueError as exc:
        message = (
            f"probe path escapes authorized root: {argument.relative_path!r}"
        )
        raise ProbeExecutionError(message) from exc
    return candidate


def _resolved_tool_path(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError as error:
        message = f"probe tool resolution failed: {path}: {error}"
        raise ProbeExecutionError(message) from error


def _tool_map(context: ProbeRunContext) -> dict[str, Path]:
    return {
        tool_id: _resolved_tool_path(path) for tool_id, path in context.tools
    }


def _require_executable(path: Path) -> None:
    try:
        mode = path.stat().st_mode
    except FileNotFoundError as error:
        message = "probe executable is unavailable"
        raise ProbeExecutionError(message) from error
    except OSError as error:
        message = f"probe executable status failed: {path}: {error}"
        raise ProbeExecutionError(message) from error
    if not S_ISREG(mode):
        message = "probe executable is unavailable"
        raise ProbeExecutionError(message)


def _resolve_executable(
    executable: ProbeExecutable,
    context: ProbeRunContext,
    scratch_root: Path,
) -> Path:
    if isinstance(executable, ToolExecutable):
        path = _tool_map(context).get(executable.tool_id)
        if path is None:
            message = f"unresolved probe tool: {executable.tool_id}"
            raise ProbeExecutionError(message)
    else:
        path = _rooted_path(executable, context, scratch_root)
    _require_executable(path)
    return path


def _resolve_argument(
    argument: ProbeArgument,
    context: ProbeRunContext,
    scratch_root: Path,
) -> str:
    if isinstance(argument, str):
        return argument
    return str(_rooted_path(argument, context, scratch_root))


def _command_argv(
    command: ProbeCommand,
    context: ProbeRunContext,
    scratch_root: Path,
) -> list[str]:
    executable = _resolve_executable(command.executable, context, scratch_root)
    arguments = (
        _resolve_argument(argument, context, scratch_root)
        for argument in command.arguments
    )
    return [str(executable), *arguments]


def _run_command(
    command: ProbeCommand,
    context: ProbeRunContext,
    scratch_root: Path,
) -> _CommandResult:
    argv = _command_argv(command, context, scratch_root)
    try:
        # jig-ignore-next-line: indivisible reviewed identifier
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - explicit argv; shell disabled.
            argv,
            cwd=scratch_root,
            input=command.stdin,
            capture_output=True,
            check=False,
            shell=False,
            timeout=command.timeout_ms / 1000,
        )
    except subprocess.TimeoutExpired as exc:
        message = "probe command exceeded its timeout"
        raise ProbeExecutionError(message) from exc
    if len(completed.stdout) > command.max_stdout_bytes:
        message = "probe command exceeded stdout limit"
        raise ProbeExecutionError(message)
    if len(completed.stderr) > command.max_stderr_bytes:
        message = "probe command exceeded stderr limit"
        raise ProbeExecutionError(message)
    if (
        command.expected_exit_code is not None
        and completed.returncode != command.expected_exit_code
    ):
        message = "probe command returned an unexpected exit code"
        raise ProbeExecutionError(message)
    return _CommandResult(
        stdout=completed.stdout,
        returncode=completed.returncode,
    )


def _update_stdout_digest(
    hasher: _HashUpdater,
    command_index: int,
    stdout: bytes,
) -> None:
    index_bytes = command_index.to_bytes(_FRAME_LENGTH_BYTES, byteorder="big")
    length_bytes = len(stdout).to_bytes(_FRAME_LENGTH_BYTES, byteorder="big")
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
    code_bytes = int(returncode).to_bytes(
        _FRAME_LENGTH_BYTES, byteorder="big", signed=True
    )
    hasher.update(b"E")
    hasher.update(index_bytes)
    hasher.update(code_bytes)


def _run_program(
    program: ProbeProgram,
    context: ProbeRunContext,
) -> ProbeTranscript:
    hasher = hashlib.sha256()
    digested_commands = _ZERO
    with tempfile.TemporaryDirectory(prefix="diff-probe-") as scratch:
        scratch_root = Path(scratch)
        for command_index, command in enumerate(program.commands):
            result = _run_command(command, context, scratch_root)
            selected = False
            if command.digest_stdout:
                _update_stdout_digest(hasher, command_index, result.stdout)
                selected = True
            if command.digest_exit_code:
                _update_exit_digest(hasher, command_index, result.returncode)
                selected = True
            if selected:
                digested_commands += 1
    return ProbeTranscript(
        probe_id=program.probe_id,
        digest=hasher.digest(),
        digested_commands=digested_commands,
    )


def _validate_probe_batch(
    programs: object, context: object
) -> tuple[ProbeProgram, ...]:
    if type(programs) is not tuple:
        message = "probe program batch must use the exact immutable tuple type"
        raise ProbeProgramError(message)
    items = cast("tuple[object, ...]", programs)
    if any(type(program) is not ProbeProgram for program in items):
        message = "probe program batch contains a foreign program record"
        raise ProbeProgramError(message)
    admitted = cast("tuple[ProbeProgram, ...]", programs)
    if type(context) is not ProbeRunContext:
        message = "probe run context must use the exact ProbeRunContext type"
        raise ProbeProgramError(message)
    identifiers = tuple(program.probe_id for program in admitted)
    if identifiers != tuple(sorted(set(identifiers))):
        message = "probe programs must have unique sorted identifiers"
        raise ProbeProgramError(message)
    return admitted


def _run_isolated_batch(
    programs: tuple[ProbeProgram, ...], context: ProbeRunContext
) -> tuple[ProbeTranscript, ...]:
    with tempfile.TemporaryDirectory(prefix="diff-probe-batch-") as batch:
        batch_root = Path(batch)
        mirror_root = Path(
            shutil.copytree(context.source_root, batch_root / "source")
        )
        isolated = replace(
            context, source_root=mirror_root, enforce_source_immutable=False
        )
        baseline = snapshot_tree(mirror_root)
        transcripts: list[ProbeTranscript] = []
        for program in programs:
            transcripts.append(_run_program(program, isolated))
            if snapshot_tree(mirror_root) != baseline:
                message = "behavior probe modified its isolated source mirror"
                raise ProbeExecutionError(message)
        return tuple(transcripts)


def run_probe_programs(
    programs: tuple[ProbeProgram, ...],
    context: ProbeRunContext,
) -> tuple[ProbeTranscript, ...]:
    """Execute a sorted unique probe batch while protecting the source tree.

    Returns:
        Transcripts in probe-id order.

    Raises:
        ProbeExecutionError: Execution mutates the source tree.

    """
    admitted = _validate_probe_batch(programs, context)
    before = (
        snapshot_tree(context.source_root)
        if context.enforce_source_immutable
        else None
    )
    transcripts = _run_isolated_batch(admitted, context)
    if before is not None and snapshot_tree(context.source_root) != before:
        message = "behavior probe modified the candidate source tree"
        raise ProbeExecutionError(message)
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
