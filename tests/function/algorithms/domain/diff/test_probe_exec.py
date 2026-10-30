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
#   - Synthetic tests for portable behavior-probe process programs.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for portable behavior-probe process programs."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import os
from pathlib import Path
import shutil
import sys
from typing import cast

from algorithms.diff.probe_exec import PathArgument
from algorithms.diff.probe_exec import ProbeCommand
from algorithms.diff.probe_exec import ProbeExecutionError
from algorithms.diff.probe_exec import ProbeProgram
from algorithms.diff.probe_exec import ProbeProgramError
from algorithms.diff.probe_exec import ProbeRoot
from algorithms.diff.probe_exec import ProbeRunContext
from algorithms.diff.probe_exec import RootedExecutable
from algorithms.diff.probe_exec import ToolExecutable
from algorithms.diff.probe_exec import run_probe_program
from algorithms.diff.probe_exec import run_probe_programs
import pytest

_PYTHON_TOOL = "python"
_WINDOWS_OS_NAME = "nt"
_ORIGINAL_TEXT = "before"
_EXTERNAL_DATA = b"external-data"
_OUTSIDE_BYTES = b"outside"
_ADMITTED_INPUT = b"admitted"
_STDOUT_NAME = "stdout"
_STDERR_NAME = "stderr"
_LINK_CREATE_CODE = (
    "import pathlib,sys;pathlib.Path(sys.argv[1]).symlink_to(sys.argv[2])"
)
_READ_BYTES_CODE = (
    "import pathlib,sys;"
    "sys.stdout.buffer.write(pathlib.Path(sys.argv[1]).read_bytes())"
)
_MUTATE_CODE = (
    "import pathlib,sys;pathlib.Path(sys.argv[1]).write_text('after')"
)


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _context(source_root: Path, repository_root: Path) -> ProbeRunContext:
    return ProbeRunContext(
        source_root=source_root,
        repository_root=repository_root,
        tools=((_PYTHON_TOOL, Path(sys.executable)),),
    )


def _program(
    probe_id: str, code: str, *, digest_stdout: bool = True
) -> ProbeProgram:
    return ProbeProgram(
        probe_id=probe_id,
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=("-c", code),
                digest_stdout=digest_stdout,
            ),
        ),
    )


def test_selected_stdout_produces_deterministic_transcript(
    tmp_path: Path,
) -> None:
    """Hash only explicitly selected deterministic process stdout."""
    source = tmp_path / "source"
    source.mkdir()
    program = _program("identity", "print('stable')")
    context = _context(source, tmp_path)

    first = run_probe_program(program, context)
    second = run_probe_program(program, context)

    _expect(first == second, "repeated process transcript changed")
    _expect(first.digested_commands == 1, "selected stdout was not digested")


def test_structured_source_path_is_passed_without_shell(tmp_path: Path) -> None:
    """Resolve source paths as argv entries without shell interpolation."""
    source = tmp_path / "source"
    source.mkdir()
    unusual_name = "semi;colon.txt"
    _ = (source / unusual_name).write_bytes(b"payload")
    program = ProbeProgram(
        probe_id="path",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _READ_BYTES_CODE,
                    PathArgument(ProbeRoot.SOURCE, unusual_name),
                ),
                digest_stdout=True,
            ),
        ),
    )

    transcript = run_probe_program(program, _context(source, tmp_path))
    expected = hashlib.sha256()
    expected.update(b"O")
    expected.update((0).to_bytes(8, byteorder="big"))
    expected.update(len(b"payload").to_bytes(8, byteorder="big"))
    expected.update(b"payload")
    _expect(
        transcript.digest == expected.digest(), "structured argv changed bytes"
    )


def _standalone_fixture(tmp_path: Path) -> tuple[Path, tuple[str, ...]]:
    if os.name == _WINDOWS_OS_NAME:
        executable = Path(os.environ.get("COMSPEC", ""))
        arguments = ("/d", "/c", "echo ran")
    else:
        located = shutil.which("echo")
        executable = Path(located) if located is not None else Path()
        arguments = ("ran",)
    if not executable.is_file():
        pytest.skip("no standalone executable fixture is available")
    fixture = tmp_path / f"fixture{executable.suffix}"
    _ = shutil.copy2(executable, fixture)
    return fixture, arguments


def test_scratch_executable_can_be_produced_then_run(tmp_path: Path) -> None:
    """Run an executable artifact produced beneath the scratch root."""
    source = tmp_path / "source"
    source.mkdir()
    fixture, run_arguments = _standalone_fixture(tmp_path)
    scratch_name = f"probe{fixture.suffix}"
    writer = (
        "import pathlib,shutil,sys;"
        "shutil.copy2(pathlib.Path(sys.argv[1]),pathlib.Path(sys.argv[2]))"
    )
    program = ProbeProgram(
        probe_id="scratch-executable",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    writer,
                    PathArgument(ProbeRoot.REPOSITORY, fixture.name),
                    PathArgument(ProbeRoot.SCRATCH, scratch_name),
                ),
            ),
            ProbeCommand(
                executable=RootedExecutable(
                    ProbeRoot.SCRATCH,
                    scratch_name,
                ),
                arguments=run_arguments,
                digest_stdout=True,
            ),
        ),
    )

    transcript = run_probe_program(program, _context(source, tmp_path))
    _expect(transcript.digested_commands == 1, "scratch executable did not run")


def test_repository_root_resolution_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wrap an inaccessible authorized root in the probe execution boundary."""
    source = tmp_path / "source"
    source.mkdir()
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == tmp_path:
            message = "blocked repository root"
            raise PermissionError(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    program = ProbeProgram(
        "root-resolution",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    "pass",
                    PathArgument(ProbeRoot.REPOSITORY, "input.txt"),
                ),
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="repository root resolution"):
        _ = run_probe_program(program, _context(source, tmp_path))


def test_rooted_argument_resolution_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wrap an inaccessible rooted argument before process launch."""
    source = tmp_path / "source"
    source.mkdir()
    candidate = tmp_path / "input.txt"
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == candidate:
            message = "blocked rooted argument"
            raise PermissionError(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    program = ProbeProgram(
        "argument-resolution",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    "pass",
                    PathArgument(ProbeRoot.REPOSITORY, "input.txt"),
                ),
            ),
        ),
    )
    with pytest.raises(
        ProbeExecutionError, match="probe path resolution failed"
    ):
        _ = run_probe_program(program, _context(source, tmp_path))


def test_missing_tool_executable_fails_closed(tmp_path: Path) -> None:
    """A missing tool binding cannot fall through to process launch."""
    source = tmp_path / "source"
    source.mkdir()
    context = ProbeRunContext(
        source_root=source,
        repository_root=tmp_path,
        tools=((_PYTHON_TOOL, tmp_path / "missing-tool.exe"),),
    )

    with pytest.raises(ProbeExecutionError, match="executable is unavailable"):
        _ = run_probe_program(_program("missing-tool", "pass"), context)


def test_tool_executable_status_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preserve an inaccessible executable as a probe status failure."""
    source = tmp_path / "source"
    source.mkdir()
    tool = tmp_path / "tool.exe"
    _ = tool.write_bytes(b"not executed")
    context = ProbeRunContext(source, tmp_path, ((_PYTHON_TOOL, tool),))
    resolved_tool = tool.resolve()
    original_stat = Path.stat

    def fail_stat(path: Path, *args: object, **kwargs: object) -> object:
        if path == resolved_tool:
            message = "blocked tool executable"
            raise PermissionError(message)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fail_stat)
    with pytest.raises(ProbeExecutionError, match="status failed"):
        _ = run_probe_program(_program("blocked-tool", "pass"), context)


def test_tool_resolution_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wrap tool-path resolution failures in the probe execution boundary."""
    source = tmp_path / "source"
    source.mkdir()
    tool = tmp_path / "tool.exe"
    _ = tool.write_bytes(b"not executed")
    context = ProbeRunContext(source, tmp_path, ((_PYTHON_TOOL, tool),))
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == tool:
            message = "blocked tool resolution"
            raise PermissionError(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    with pytest.raises(ProbeExecutionError, match="tool resolution failed"):
        _ = run_probe_program(_program("blocked-resolution", "pass"), context)


def test_exit_code_can_be_observed_instead_of_required(tmp_path: Path) -> None:
    """Allow behavior probes to digest a nonzero process result as evidence."""
    source = tmp_path / "source"
    source.mkdir()
    program = ProbeProgram(
        probe_id="exit-observation",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=("-c", "raise SystemExit(37)"),
                expected_exit_code=None,
                digest_exit_code=True,
            ),
        ),
    )

    transcript = run_probe_program(program, _context(source, tmp_path))
    expected = hashlib.sha256()
    expected.update(b"E")
    expected.update((0).to_bytes(8, byteorder="big"))
    expected.update((37).to_bytes(8, byteorder="big", signed=True))
    _expect(
        transcript.digest == expected.digest(), "exit-code transcript changed"
    )
    _expect(transcript.digested_commands == 1, "exit code was not selected")


def test_unexpected_exit_code_fails_closed(tmp_path: Path) -> None:
    """Reject a process that violates its declared success contract."""
    source = tmp_path / "source"
    source.mkdir()
    program = _program("exit", "raise SystemExit(7)", digest_stdout=False)

    with pytest.raises(ProbeExecutionError, match="unexpected exit code"):
        _ = run_probe_program(program, _context(source, tmp_path))


def test_timeout_fails_closed(tmp_path: Path) -> None:
    """Bound probe execution time rather than permitting a hung transform."""
    source = tmp_path / "source"
    source.mkdir()
    program = ProbeProgram(
        probe_id="timeout",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=("-c", "import time;time.sleep(1)"),
                timeout_ms=20,
            ),
        ),
    )

    with pytest.raises(ProbeExecutionError, match="timeout"):
        _ = run_probe_program(program, _context(source, tmp_path))


def test_output_limit_fails_closed(tmp_path: Path) -> None:
    """Bound captured output before transform-controlled memory growth."""
    source = tmp_path / "source"
    source.mkdir()
    program = ProbeProgram(
        probe_id="output-limit",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=("-c", "print('x' * 1000)"),
                max_stdout_bytes=16,
            ),
        ),
    )

    with pytest.raises(ProbeExecutionError, match="stdout limit"):
        _ = run_probe_program(program, _context(source, tmp_path))


@pytest.mark.parametrize("stream", [_STDOUT_NAME, _STDERR_NAME])
def test_live_pipe_quota_interrupts_unbounded_output(
    tmp_path: Path, stream: str
) -> None:
    """An overflowing child must fail by byte quota, not delayed timeout."""
    source = tmp_path / "source"
    source.mkdir()
    descriptor = 1 if stream == _STDOUT_NAME else 2
    code = f"import os;exec('while True: os.write({descriptor}, bytes(4096))')"
    program = ProbeProgram(
        "live-output-cap",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=("-c", code),
                timeout_ms=600,
                max_stdout_bytes=32,
                max_stderr_bytes=32,
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match=f"{stream} limit"):
        _ = run_probe_program(program, _context(source, tmp_path))


def test_full_duplex_stdin_and_stdout_preserves_transcript(
    tmp_path: Path,
) -> None:
    """Concurrent stdin delivery must not deadlock a writing child."""
    source = tmp_path / "source"
    source.mkdir()
    payload = b"q" * 131_072
    prefix = b"w" * 16_384
    code = (
        "import sys;"
        "sys.stdout.buffer.write(b'w'*16384);"
        "sys.stdout.buffer.flush();"
        "data=sys.stdin.buffer.read();"
        "sys.stdout.buffer.write(data[:8])"
    )
    command = ProbeCommand(
        executable=ToolExecutable(_PYTHON_TOOL),
        arguments=("-c", code),
        stdin=payload,
        timeout_ms=2_000,
        max_stdout_bytes=16_392,
        digest_stdout=True,
    )
    transcript = run_probe_program(
        ProbeProgram("full-duplex", (command,)), _context(source, tmp_path)
    )
    expected_data = prefix + payload[:8]
    expected = hashlib.sha256()
    expected.update(b"O")
    expected.update((0).to_bytes(8, byteorder="big"))
    expected.update(len(expected_data).to_bytes(8, byteorder="big"))
    expected.update(expected_data)
    _expect(
        transcript.digest == expected.digest(), "stdin/stdout transcript drift"
    )


def test_source_mutation_is_isolated_from_user_source(tmp_path: Path) -> None:
    """Run source-mutating probes only against an isolated mirror."""
    source = tmp_path / "source"
    source.mkdir()
    target = source / "input.txt"
    _ = target.write_text(_ORIGINAL_TEXT, encoding="utf-8")
    mutator = ProbeProgram(
        probe_id="mutator",
        commands=(
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _MUTATE_CODE,
                    PathArgument(ProbeRoot.SOURCE, "input.txt"),
                ),
            ),
        ),
    )

    with pytest.raises(ProbeExecutionError, match="isolated source mirror"):
        _ = run_probe_programs((mutator,), _context(source, tmp_path))
    _expect(
        target.read_text(encoding="utf-8") == _ORIGINAL_TEXT,
        "source was mutated",
    )


def test_source_symlink_fails_before_mirror_even_without_immutability(
    tmp_path: Path,
) -> None:
    """Reject external source links before mirroring content."""
    source = tmp_path / "source"
    source.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    _ = secret.write_bytes(_EXTERNAL_DATA)
    linked = source / "linked"
    try:
        linked.symlink_to(outside, target_is_directory=True)
    except OSError, NotImplementedError:
        pytest.skip("directory symlinks unavailable")

    context = replace(
        _context(source, tmp_path), enforce_source_immutable=False
    )
    program = ProbeProgram(
        "linked-input",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _READ_BYTES_CODE,
                    PathArgument(ProbeRoot.SOURCE, "linked/secret.txt"),
                ),
                digest_stdout=True,
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="symlinks"):
        _ = run_probe_program(program, context)
    _expect(secret.read_bytes() == _EXTERNAL_DATA, "external input changed")


def test_probe_created_symlink_is_rejected_inside_execution_boundary(
    tmp_path: Path,
) -> None:
    """Probe-created links are rejected through ProbeExecutionError."""
    source = tmp_path / "source"
    source.mkdir()
    outside = tmp_path / "outside.txt"
    _ = outside.write_bytes(_OUTSIDE_BYTES)
    probe = tmp_path / "probe"
    try:
        probe.symlink_to(outside)
    except OSError, NotImplementedError:
        pytest.skip("file symlinks unavailable")
    probe.unlink()
    program = ProbeProgram(
        "link-mirror",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _LINK_CREATE_CODE,
                    PathArgument(ProbeRoot.SOURCE, "created.txt"),
                    PathArgument(ProbeRoot.REPOSITORY, "outside.txt"),
                ),
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="isolated source mirror"):
        _ = run_probe_program(program, _context(source, tmp_path))
    _expect(outside.read_bytes() == _OUTSIDE_BYTES, "external file changed")


def test_mirror_snapshot_catches_copy_time_source_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not execute a mirror whose bytes differ from the admitted source."""
    source = tmp_path / "source"
    source.mkdir()
    input_file = source / "input.txt"
    _ = input_file.write_bytes(_ADMITTED_INPUT)
    actual_copytree = shutil.copytree

    def mutate_mirror_after_copy(
        source_root: Path, destination_root: Path, *, symlinks: bool = False
    ) -> Path:
        copied = actual_copytree(
            source_root, destination_root, symlinks=symlinks
        )
        _ = (copied / "input.txt").write_bytes(b"injected")
        return copied

    monkeypatch.setattr(shutil, "copytree", mutate_mirror_after_copy)
    context = replace(
        _context(source, tmp_path), enforce_source_immutable=False
    )
    program = ProbeProgram(
        "copy-time-drift",
        (
            ProbeCommand(
                executable=ToolExecutable(_PYTHON_TOOL),
                arguments=(
                    "-c",
                    _READ_BYTES_CODE,
                    PathArgument(ProbeRoot.SOURCE, "input.txt"),
                ),
                digest_stdout=True,
            ),
        ),
    )
    with pytest.raises(ProbeExecutionError, match="changed while creating"):
        _ = run_probe_program(program, context)
    _expect(input_file.read_bytes() == _ADMITTED_INPUT, "source was modified")


def test_missing_source_rejected_before_copy_without_immutability(
    tmp_path: Path,
) -> None:
    """Optional post-run immutability does not disable source admission."""
    missing = tmp_path / "missing"
    context = replace(
        _context(missing, tmp_path), enforce_source_immutable=False
    )
    with pytest.raises(ProbeExecutionError, match="source snapshot rejected"):
        _ = run_probe_program(_program("missing", "pass"), context)


def test_probe_records_reject_foreign_runtime_metadata() -> None:
    """Probe roots, paths, tool IDs, and executable records use exact types."""
    with pytest.raises(ProbeProgramError, match="exact ProbeRoot"):
        _ = PathArgument(cast("ProbeRoot", object()), "input.c")
    with pytest.raises(ProbeProgramError, match="exact string"):
        _ = PathArgument(ProbeRoot.SOURCE, cast("str", object()))
    with pytest.raises(ProbeProgramError, match="non-empty string"):
        _ = ToolExecutable(cast("str", object()))
    with pytest.raises(ProbeProgramError, match="exact ProbeRoot"):
        _ = RootedExecutable(cast("ProbeRoot", object()), "tool.exe")


def test_probe_command_rejects_boolean_aliases_and_mutable_inputs() -> None:
    """Process limits and selectors cannot rely on Python coercions."""
    base = ProbeCommand(executable=ToolExecutable(_PYTHON_TOOL))
    invalid = (
        lambda: replace(base, executable=cast("ToolExecutable", object())),
        lambda: replace(
            base,
            arguments=cast(
                "tuple[str | PathArgument, ...]",
                cast("object", ["-V"]),
            ),
        ),
        lambda: replace(base, arguments=(cast("str", object()),)),
        lambda: replace(base, stdin=cast("bytes", cast("object", bytearray()))),
        lambda: replace(base, expected_exit_code=True),
        lambda: replace(base, timeout_ms=True),
        lambda: replace(base, max_stdout_bytes=True),
        lambda: replace(base, max_stderr_bytes=True),
        lambda: replace(base, digest_stdout=cast("bool", cast("object", 1))),
        lambda: replace(base, digest_exit_code=cast("bool", cast("object", 1))),
    )
    for build in invalid:
        with pytest.raises(ProbeProgramError, match="probe"):
            _ = build()


def test_probe_rejects_nul_command_and_rooted_path_arguments() -> None:
    """Malformed argv must fail at record admission, before process launch."""
    with pytest.raises(ProbeProgramError, match="NUL"):
        _ = ProbeCommand(
            executable=ToolExecutable(_PYTHON_TOOL),
            arguments=("--flag=" + chr(0),),
        )
    with pytest.raises(ProbeProgramError, match="NUL"):
        _ = PathArgument(ProbeRoot.SOURCE, "bad" + chr(0) + "file.txt")
    with pytest.raises(ProbeProgramError, match="NUL"):
        _ = ToolExecutable("bad" + chr(0) + "tool")
    with pytest.raises(ProbeProgramError, match="NUL"):
        _ = ProbeRunContext(
            Path("bad" + chr(0) + "source"),
            Path("repo"),
            (),
        )
    with pytest.raises(ProbeProgramError, match="NUL"):
        _ = ProbeRunContext(
            Path("source"),
            Path("repo"),
            (("bad" + chr(0) + "tool", Path("tool")),),
        )


def test_probe_executable_launch_failure_is_wrapped(tmp_path: Path) -> None:
    """Regular but non-executable tool files remain inside probe errors."""
    source = tmp_path / "source"
    source.mkdir()
    bad_executable = tmp_path / "text-only.exe"
    _ = bad_executable.write_bytes(b"not an executable")
    program = _program("bad-tool", "pass")
    context = ProbeRunContext(
        source_root=source,
        repository_root=tmp_path,
        tools=((_PYTHON_TOOL, bad_executable),),
    )
    with pytest.raises(ProbeExecutionError, match="launch failed"):
        _ = run_probe_program(program, context)


def test_probe_program_and_context_require_immutable_exact_records(
    tmp_path: Path,
) -> None:
    """Batch metadata is validated before filesystem or process work."""
    command = ProbeCommand(executable=ToolExecutable(_PYTHON_TOOL))
    with pytest.raises(ProbeProgramError, match="immutable tuple"):
        _ = ProbeProgram(
            "probe",
            cast("tuple[ProbeCommand, ...]", cast("object", [command])),
        )
    with pytest.raises(ProbeProgramError, match="foreign command"):
        _ = ProbeProgram("probe", (cast("ProbeCommand", object()),))

    source = tmp_path / "source"
    source.mkdir()
    with pytest.raises(ProbeProgramError, match="immutable tuple"):
        _ = ProbeRunContext(
            source,
            tmp_path,
            cast(
                "tuple[tuple[str, Path], ...]",
                cast("object", [(_PYTHON_TOOL, Path(sys.executable))]),
            ),
        )
    with pytest.raises(ProbeProgramError, match="exact boolean"):
        _ = ProbeRunContext(
            source,
            tmp_path,
            ((_PYTHON_TOOL, Path(sys.executable)),),
            enforce_source_immutable=cast("bool", cast("object", 1)),
        )

    context = _context(source, tmp_path)
    program = ProbeProgram("probe", (command,))
    with pytest.raises(ProbeProgramError, match="immutable tuple"):
        _ = run_probe_programs(
            cast("tuple[ProbeProgram, ...]", cast("object", [program])),
            context,
        )
    with pytest.raises(ProbeProgramError, match="foreign program"):
        _ = run_probe_programs((cast("ProbeProgram", object()),), context)
    with pytest.raises(ProbeProgramError, match="exact ProbeRunContext"):
        _ = run_probe_programs((program,), cast("ProbeRunContext", object()))
