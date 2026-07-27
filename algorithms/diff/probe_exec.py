# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Portable bounded process programs for behavior-probe observations."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from enum import StrEnum
import hashlib
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import] - no shell; resolved executables only.
import tempfile

from algorithms.diff.exact import snapshot_tree

_ZERO = 0
_ONE = 1
_DEFAULT_TIMEOUT_MS = 10_000
_DEFAULT_OUTPUT_LIMIT = 1_048_576
_FRAME_LENGTH_BYTES = 8
_BACKSLASH = "\\"
_PARENT = ".."


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
        """Reject absolute, parent-traversing, or non-canonical paths."""
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
        if not self.tool_id:
            message = "probe tool identifier must be non-empty"
            raise ProbeProgramError(message)


@dataclass(frozen=True, slots=True)
class RootedExecutable:
    """Executable artifact produced or stored beneath an authorized root."""

    root: ProbeRoot
    relative_path: str

    def __post_init__(self) -> None:
        """Reject unsafe executable paths."""
        _validate_relative_path(self.relative_path)


ProbeExecutable = ToolExecutable | RootedExecutable


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
        """Reject unbounded or nonsensical process limits.

        Raises:
            ProbeProgramError: Timeout or output limits are invalid.

        """
        if self.timeout_ms < _ONE:
            message = "probe timeout must be positive"
            raise ProbeProgramError(message)
        if self.max_stdout_bytes < _ZERO or self.max_stderr_bytes < _ZERO:
            message = "probe output limits cannot be negative"
            raise ProbeProgramError(message)


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
        if not self.probe_id:
            message = "probe program identifier must be non-empty"
            raise ProbeProgramError(message)
        if not self.commands:
            message = "probe program requires at least one command"
            raise ProbeProgramError(message)


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
        identifiers = tuple(tool_id for tool_id, _ in self.tools)
        if any(not tool_id for tool_id in identifiers):
            message = "probe tool identifiers must be non-empty"
            raise ProbeProgramError(message)
        if identifiers != tuple(sorted(set(identifiers))):
            message = "probe tool bindings must be unique and sorted"
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


def _validate_relative_path(relative_path: str) -> None:
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
        candidate.resolve().relative_to(root)
    except ValueError as exc:
        message = (
            f"probe path escapes authorized root: {argument.relative_path!r}"
        )
        raise ProbeExecutionError(message) from exc
    return candidate


def _tool_map(context: ProbeRunContext) -> dict[str, Path]:
    return {tool_id: path.resolve() for tool_id, path in context.tools}


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
    if not path.is_file():
        message = "probe executable is unavailable"
        raise ProbeExecutionError(message)
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
    hasher: hashlib._Hash,
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
    hasher: hashlib._Hash,
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


def run_probe_programs(
    programs: tuple[ProbeProgram, ...],
    context: ProbeRunContext,
) -> tuple[ProbeTranscript, ...]:
    """Execute a sorted unique probe batch while protecting the source tree.

    Returns:
        Transcripts in probe-id order.

    Raises:
        ProbeProgramError: Program identifiers are duplicate or unsorted.
        ProbeExecutionError: Execution fails or mutates the source tree.

    """
    identifiers = tuple(program.probe_id for program in programs)
    if identifiers != tuple(sorted(set(identifiers))):
        message = "probe programs must have unique sorted identifiers"
        raise ProbeProgramError(message)
    before = (
        snapshot_tree(context.source_root)
        if context.enforce_source_immutable
        else None
    )
    with tempfile.TemporaryDirectory(prefix="diff-probe-batch-") as batch:
        batch_root = Path(batch)
        mirror_root = batch_root / "source"
        shutil.copytree(context.source_root, mirror_root)
        isolated_context = replace(
            context,
            source_root=mirror_root,
            enforce_source_immutable=False,
        )
        mirror_snapshot = snapshot_tree(mirror_root)
        transcripts_list: list[ProbeTranscript] = []
        for program in programs:
            transcript = _run_program(program, isolated_context)
            if snapshot_tree(mirror_root) != mirror_snapshot:
                message = "behavior probe modified its isolated source mirror"
                raise ProbeExecutionError(message)
            transcripts_list.append(transcript)
        transcripts = tuple(transcripts_list)
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
