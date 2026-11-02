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
#   - Deterministic repository-scoped Jig launcher regression coverage.
# - Must-Not:
#   - Replace external Jig or bypass its validation decisions.
# - Allows:
#   - Inputs: injected host environment, tool aliases, and Jig subprocess.
#   - Outputs: exact command, environment, and error-boundary assertions.
#   - Side effects: pytest temporary executable fixtures only.
# - Split-When:
#   - Jig launcher requires a separate platform adapter.
# - Merge-When:
#   - A shared tooling test owns exact validation invocation behavior.
# - Summary:
#   - Prove pinned tool precedence and unchanged Jig status propagation.
# - Description:
#   - Models conflicting user PATH and missing repository-local tools.
# - Usage:
#   - Run with the repository's strict pytest configuration.
# - Defaults:
#   - No real Jig subprocess executes in unit tests.
#

"""Regression tests for repository-local Jig environment setup."""

from __future__ import annotations

import os
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path
from typing import cast, override

import pytest

from scripts.validate import jig_runner

pytestmark = pytest.mark.skipif(
    sys.platform != jig_runner.LINUX_PLATFORM,
    reason="repository Jig runner uses Linux pinned tools",
)


@pytest.fixture(autouse=True)
def _isolate_external_tool_bin(monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not inherit a live Jig opt-in into default-path unit fixtures."""
    monkeypatch.delenv(jig_runner.EXTERNAL_TOOL_BIN_VARIABLE, raising=False)


def _pinned_launchers(root: Path) -> Path:
    """Create temporary executable aliases for fixture commands.

    Returns:
        Temporary bin directory containing both executable launchers.

    """
    bin_dir = root / ".dependencies/bin"
    bin_dir.mkdir(parents=True)
    for name in jig_runner.PINNED_TOOLS:
        launcher = bin_dir / name
        _ = launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        launcher.chmod(0o700)
    return bin_dir


def test_environment_precedes_ambient_host_tools(tmp_path: Path) -> None:
    """Pinned ChkTeX and LaTeXmk precede unrelated user-local binaries."""
    pinned_bin = _pinned_launchers(tmp_path)
    original = {"PATH": "/host/local/bin:/usr/bin", "MARKER": "preserved"}
    environment = jig_runner.jig_environment(tmp_path, original)
    enabled = "1"
    marker = "preserved"
    assert environment["PATH"] == (f"{pinned_bin}{os.pathsep}{os.defpath}")
    assert environment["PYTHONDONTWRITEBYTECODE"] == enabled
    assert environment["RUFF_CACHE_DIR"] == str(tmp_path / ".cache/ruff")
    assert environment["MARKER"] == marker
    assert original == {
        "PATH": "/host/local/bin:/usr/bin",
        "MARKER": "preserved",
    }


def test_explicit_external_tool_bin_precedes_system_without_shifting_pinned(
    tmp_path: Path,
) -> None:
    """Jig may attest an opt-in native tool outside the repository root."""
    pinned = _pinned_launchers(tmp_path)
    external = tmp_path.parent / "external-jig-native-tool"
    external.mkdir()
    tool = external / "chktex"
    _ = tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    tool.chmod(0o700)
    variable = "MALBOLGE_JIG_EXTERNAL_TOOL_BIN"
    inherited = {"PATH": "/untrusted/bin", variable: str(external)}
    environment = jig_runner.jig_environment(tmp_path, inherited)
    assert environment["PATH"] == (
        f"{pinned}{os.pathsep}{external}{os.pathsep}{os.defpath}"
    )
    assert environment[variable] == str(external)
    assert inherited["PATH"] == "/untrusted/bin"


@pytest.mark.parametrize(
    "invalid", ["relative", "/tmp/first:/tmp/second", "../escape", ""]
)
def test_external_tool_bin_rejects_ambiguous_paths(
    tmp_path: Path, invalid: str
) -> None:
    """The opt-in is exactly one absolute directory, never PATH injection."""
    _ = _pinned_launchers(tmp_path)
    with pytest.raises(jig_runner.JigRunnerError, match="external.*directory"):
        _ = jig_runner.jig_environment(
            tmp_path,
            {"MALBOLGE_JIG_EXTERNAL_TOOL_BIN": invalid},
        )


def test_external_tool_bin_rejects_repository_and_linked_locations(
    tmp_path: Path,
) -> None:
    """Reject linked or in-repository external tool directory authority."""
    _ = _pinned_launchers(tmp_path)
    external = tmp_path.parent / "external-tool-real"
    external.mkdir()
    tool = external / "chktex"
    _ = tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    tool.chmod(0o700)
    linked = tmp_path.parent / "external-tool-linked"
    linked.symlink_to(external, target_is_directory=True)
    variable = "MALBOLGE_JIG_EXTERNAL_TOOL_BIN"
    invalid_locations = (
        tmp_path / ".dependencies/bin",
        linked,
        tmp_path.parent / "absent",
    )
    expected_error = "external.*directory"
    for invalid in invalid_locations:
        with pytest.raises(jig_runner.JigRunnerError, match=expected_error):
            _ = jig_runner.jig_environment(tmp_path, {variable: str(invalid)})
    tool.chmod(0o600)
    with pytest.raises(jig_runner.JigRunnerError, match="external.*directory"):
        _ = jig_runner.jig_environment(tmp_path, {variable: str(external)})


def test_environment_rejects_missing_or_nonexecutable_alias(
    tmp_path: Path,
) -> None:
    """Do not silently select ambient tools when local aliases are absent."""
    bin_dir = _pinned_launchers(tmp_path)
    (bin_dir / "chktex").chmod(0o600)
    with pytest.raises(
        jig_runner.JigRunnerError,
        match="missing executable Jig validation tool",
    ):
        _ = jig_runner.jig_environment(tmp_path, {"PATH": "/usr/bin"})
    (bin_dir / "chktex").chmod(0o700)
    (bin_dir / "latexmk").unlink()
    with pytest.raises(
        jig_runner.JigRunnerError,
        match="missing executable Jig validation tool",
    ):
        _ = jig_runner.jig_environment(tmp_path, {"PATH": "/usr/bin"})


@pytest.mark.parametrize("tool", jig_runner.PINNED_TOOLS)
def test_environment_rejects_linked_pinned_launcher(
    tmp_path: Path,
    tool: str,
) -> None:
    """Valid-looking launcher symlinks must not override pinned tools."""
    bin_dir = _pinned_launchers(tmp_path)
    launcher = bin_dir / tool
    real = bin_dir / f"{tool}-actual"
    _ = launcher.replace(real)
    try:
        _ = launcher.symlink_to(real)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(jig_runner.JigRunnerError, match="redirect"):
        _ = jig_runner.jig_environment(tmp_path, {"PATH": "/usr/bin"})


def test_environment_rejects_linked_pinned_bin_directory(
    tmp_path: Path,
) -> None:
    """An alias to pinned-bin cannot authorize executable precedence."""
    pinned = _pinned_launchers(tmp_path)
    real = pinned.with_name("physical-bin")
    _ = pinned.replace(real)
    try:
        _ = pinned.symlink_to(real, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(jig_runner.JigRunnerError, match="redirect"):
        _ = jig_runner.jig_environment(tmp_path, {"PATH": "/usr/bin"})


def test_environment_rejects_linked_dependency_root(
    tmp_path: Path,
) -> None:
    """The dependencies directory itself may not redirect launcher reads."""
    _ = _pinned_launchers(tmp_path)
    dependencies = tmp_path / ".dependencies"
    real = tmp_path / "physical-dependencies"
    _ = dependencies.replace(real)
    try:
        _ = dependencies.symlink_to(real, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(jig_runner.JigRunnerError, match="redirect"):
        _ = jig_runner.jig_environment(tmp_path, {"PATH": "/usr/bin"})


def test_environment_rejects_nonregular_pinned_fifo(tmp_path: Path) -> None:
    """A named pipe with executable mode must not be a pinned launcher."""
    mkfifo = getattr(os, "mkfifo", None)
    if mkfifo is None:
        pytest.skip("FIFO unsupported")
    pinned = _pinned_launchers(tmp_path)
    launcher = pinned / "chktex"
    launcher.unlink()
    mkfifo(launcher, 0o700)
    with pytest.raises(jig_runner.JigRunnerError, match="missing executable"):
        _ = jig_runner.jig_environment(tmp_path, {"PATH": "/usr/bin"})


ACCESS_OPERATION = "access"


def _inject_access_fault(
    monkeypatch: pytest.MonkeyPatch, target: Path, fault: Exception
) -> None:
    """Replace only executable-mode admission for the selected test path."""
    native_access = os.access

    def fail_access(path: Path, mode: int) -> bool:
        if path == target:
            raise fault
        return native_access(path, mode)

    monkeypatch.setattr(os, ACCESS_OPERATION, fail_access)


def _inject_launcher_status_fault(
    monkeypatch: pytest.MonkeyPatch,
    target: Path,
    *,
    operation: str,
    fault: Exception,
) -> None:
    """Replace one host stat adapter while preserving other path operations."""
    if operation == ACCESS_OPERATION:
        _inject_access_fault(monkeypatch, target, fault)
        return

    methods = {
        "is_symlink": Path.is_symlink,
        "is_junction": Path.is_junction,
        "is_dir": Path.is_dir,
        "resolve": Path.resolve,
        "lstat": Path.lstat,
    }

    def fail_status(path: Path) -> object:
        if path == target:
            raise fault
        return methods[operation](path)

    monkeypatch.setattr(Path, operation, fail_status)


@pytest.mark.parametrize("fault_type", [TypeError, RuntimeError])
@pytest.mark.parametrize(
    "operation", ["is_symlink", "is_junction", "lstat", ACCESS_OPERATION]
)
def test_pinned_launcher_status_fault_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """Unexpected launcher stat errors cannot fall back to ambient Jig tools."""
    pinned = _pinned_launchers(tmp_path)
    launcher = pinned / "chktex"
    fault = fault_type("injected pinned launcher status failure")
    with monkeypatch.context() as isolated:
        _inject_launcher_status_fault(
            isolated, launcher, operation=operation, fault=fault
        )
        with pytest.raises(jig_runner.JigRunnerError, match="Jig validation tool"):
            _ = jig_runner.jig_environment(tmp_path, {"PATH": "/usr/bin"})


@pytest.mark.parametrize("fault_type", [TypeError, RuntimeError])
@pytest.mark.parametrize(
    "operation",
    [
        "is_symlink",
        "is_junction",
        "is_dir",
        "resolve",
        "lstat",
        ACCESS_OPERATION,
    ],
)
def test_external_launcher_status_fault_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """An opted-in binary requires confirmed direct physical file admission."""
    _ = _pinned_launchers(tmp_path)
    external = tmp_path.parent / f"external-jig-{tmp_path.name}"
    external.mkdir()
    executable = external / "chktex"
    _ = executable.write_bytes(b"#!/bin/sh\nexit 0\n")
    executable.chmod(0o700)
    fault = fault_type("injected external launcher status failure")
    target = external if operation in {"is_dir", "resolve"} else executable
    with monkeypatch.context() as isolated:
        _inject_launcher_status_fault(
            isolated, target, operation=operation, fault=fault
        )
        with pytest.raises(jig_runner.JigRunnerError, match=r"external.*directory"):
            _ = jig_runner.jig_environment(
                tmp_path,
                {jig_runner.EXTERNAL_TOOL_BIN_VARIABLE: str(external)},
            )


def test_runner_keeps_exact_jig_command_and_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never use a shell or change the validator's exit status."""
    pinned_bin = _pinned_launchers(tmp_path)
    observed: list[tuple[object, object, object, object]] = []

    executable_name = "jig"
    exit_code = 17

    def resolve(name: str) -> str:
        assert name == executable_name
        return "/host/local/bin/jig"

    def execute(
        args: list[str],
        **options: object,
    ) -> sp.CompletedProcess[str]:
        environment = cast("dict[str, str]", options["env"])
        observed.append(
            (
                args,
                options["cwd"],
                environment["PATH"],
                options["shell"],
            )
        )
        assert options["check"] is False
        return sp.CompletedProcess(args, exit_code)

    monkeypatch.setattr("scripts.validate.jig_runner.shutil.which", resolve)
    monkeypatch.setattr("scripts.validate.jig_runner.sp.run", execute)
    monkeypatch.setenv("PATH", "/host/local/bin")
    assert jig_runner.run_jig("check", root=tmp_path) == exit_code
    assert observed == [
        (
            ["/host/local/bin/jig", "check", "--root", str(tmp_path)],
            tmp_path,
            f"{pinned_bin}{os.pathsep}{os.defpath}",
            False,
        ),
    ]


def test_runner_rejects_unsupported_and_missing_jig(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No unknown command or missing validator is silently tolerated."""
    with pytest.raises(jig_runner.JigRunnerError, match="unsupported"):
        _ = jig_runner.run_jig("repair", root=tmp_path)

    def missing(_name: str) -> None:
        del _name

    monkeypatch.setattr("scripts.validate.jig_runner.shutil.which", missing)
    with pytest.raises(jig_runner.JigRunnerError, match="unavailable"):
        _ = jig_runner.run_jig("check", root=tmp_path)


@pytest.mark.parametrize("command", ["foreign-string", "foreign-object"])
def test_runner_rejects_foreign_command_before_comparison(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
) -> None:
    """A foreign command cannot execute equality or formatter hooks."""

    class ForeignCommand(str):
        @override
        def __eq__(self, _other: object) -> bool:
            raise AssertionError("foreign command equality executed")

        @override
        def __str__(self) -> str:
            raise AssertionError("foreign command formatting executed")

    class ForeignObject:
        @override
        def __eq__(self, _other: object) -> bool:
            raise AssertionError("foreign object equality executed")

        @override
        def __str__(self) -> str:
            raise AssertionError("foreign object formatting executed")

    def discovery(_name: str) -> None:
        pytest.fail("invalid command reached Jig executable discovery")

    monkeypatch.setattr(jig_runner.shutil, "which", discovery)
    untrusted = (
        ForeignCommand("check")
        if command == "foreign-string"
        else cast("str", cast("object", ForeignObject()))
    )
    with pytest.raises(jig_runner.JigRunnerError, match="unsupported Jig command"):
        _ = jig_runner.run_jig(untrusted, root=tmp_path)


def test_main_reports_missing_dependency(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Missing pinned tools produce a nonzero, actionable diagnostic."""
    expected_error = "missing executable Jig validation tool: chktex"

    def fail(command: str) -> int:
        del command
        raise jig_runner.JigRunnerError(expected_error)

    monkeypatch.setattr(jig_runner, "run_jig", fail)
    assert jig_runner.main(["check"]) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert expected_error in captured.err


def test_child_process_sees_pinned_tool_not_user_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    """A real child must never inherit a shadowing user-local ChkTeX."""
    pinned = _pinned_launchers(tmp_path)
    expected_output = "pinned-version\n"
    expected_status = 19
    pinned_chktex = pinned / "chktex"
    _ = pinned_chktex.write_text(
        "#!/bin/sh\nprintf 'pinned-version\\n'\n",
        encoding="utf-8",
    )
    host_bin = tmp_path / "user-local/bin"
    host_bin.mkdir(parents=True)
    ambient_chktex = host_bin / "chktex"
    _ = ambient_chktex.write_text(
        "#!/bin/sh\nprintf 'wrong-version\\n'\n",
        encoding="utf-8",
    )
    ambient_chktex.chmod(0o700)
    fake_jig = host_bin / "jig"
    _ = fake_jig.write_text(
        "#!/bin/sh\nchktex --version\nexit 19\n",
        encoding="utf-8",
    )
    fake_jig.chmod(0o700)
    with monkeypatch.context() as context:
        context.setenv("PATH", f"{host_bin}{os.pathsep}{os.defpath}")
        assert jig_runner.run_jig("check", root=tmp_path) == expected_status
    captured = capfd.readouterr()
    assert captured.out == expected_output
    assert not captured.err


def test_subprocess_launch_failure_stays_actionable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An installed but unstartable Jig must not look like a passing gate."""
    _ = _pinned_launchers(tmp_path)

    expected_name = "jig"

    def resolve(name: str) -> str:
        assert name == expected_name
        return "/unavailable/jig"

    def fail_launch(args: list[str], **options: object) -> None:
        del args, options
        message = "injected Jig process failure"
        raise OSError(message)

    monkeypatch.setattr("scripts.validate.jig_runner.shutil.which", resolve)
    monkeypatch.setattr("scripts.validate.jig_runner.sp.run", fail_launch)
    with pytest.raises(
        jig_runner.JigRunnerError,
        match="external Jig execution failed: injected Jig process failure",
    ):
        _ = jig_runner.run_jig("check", root=tmp_path)


def _resolve_fixture_jig(_name: str) -> str:
    """Supply a deterministic installed Jig path for injected receipts."""
    return "/real/jig"


@pytest.mark.parametrize(
    "invalid_status",
    [None, False, True, "0", 0.0, object()],
    ids=["missing", "false", "true", "string", "float", "foreign"],
)
def test_runner_rejects_malformed_child_exit_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_status: object,
) -> None:
    """A forged success receipt cannot make Jig validation look complete."""
    _ = _pinned_launchers(tmp_path)
    monkeypatch.setattr(
        "scripts.validate.jig_runner.shutil.which", _resolve_fixture_jig
    )

    def execute(args: list[str], **_options: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(args, cast("int", invalid_status))

    monkeypatch.setattr("scripts.validate.jig_runner.sp.run", execute)
    with pytest.raises(jig_runner.JigRunnerError, match="invalid process completion"):
        _ = jig_runner.run_jig("check", root=tmp_path)


@pytest.mark.parametrize("result", [None, object()])
def test_runner_rejects_foreign_child_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    result: object,
) -> None:
    """Only an actual completed process may report validation success."""
    _ = _pinned_launchers(tmp_path)
    monkeypatch.setattr(
        "scripts.validate.jig_runner.shutil.which", _resolve_fixture_jig
    )

    def execute(_args: list[str], **_options: object) -> object:
        return result

    monkeypatch.setattr("scripts.validate.jig_runner.sp.run", execute)
    with pytest.raises(jig_runner.JigRunnerError, match="invalid process completion"):
        _ = jig_runner.run_jig("check", root=tmp_path)


@pytest.mark.parametrize(
    "fault_type", [ValueError, RuntimeError, TypeError, AttributeError]
)
def test_runner_types_host_launch_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Host subprocess failures retain the cause behind a typed error."""
    _ = _pinned_launchers(tmp_path)
    monkeypatch.setattr(
        "scripts.validate.jig_runner.shutil.which", _resolve_fixture_jig
    )
    fault = fault_type("injected launcher host failure")

    def fail_launch(_args: list[str], **_options: object) -> None:
        raise fault

    monkeypatch.setattr("scripts.validate.jig_runner.sp.run", fail_launch)
    with pytest.raises(
        jig_runner.JigRunnerError, match="external Jig execution failed"
    ) as caught:
        _ = jig_runner.run_jig("check", root=tmp_path)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    "fault_type", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_runner_types_executable_discovery_faults(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A broken executable resolver must not leak untyped exceptions."""
    fault = fault_type("injected executable discovery failure")

    def fail_resolve(_name: str) -> None:
        raise fault

    monkeypatch.setattr("scripts.validate.jig_runner.shutil.which", fail_resolve)
    with pytest.raises(jig_runner.JigRunnerError, match="discovery failed") as caught:
        _ = jig_runner.run_jig("check")
    assert caught.value.__cause__ is fault


class _HostileLaunchError(OSError):
    """A caller-owned exception must not execute a diagnostic hook."""

    def __str__(self) -> str:
        message = "foreign launcher diagnostic formatting was called"
        raise AssertionError(message)


def test_runner_preserves_hostile_launch_cause_without_formatting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A launch failure cannot escape typed admission via its __str__."""
    _ = _pinned_launchers(tmp_path)
    fault = _HostileLaunchError("injected launcher failure")

    def fail_launch(_args: list[str], **_options: object) -> None:
        raise fault

    monkeypatch.setattr(
        "scripts.validate.jig_runner.shutil.which", _resolve_fixture_jig
    )
    monkeypatch.setattr("scripts.validate.jig_runner.sp.run", fail_launch)
    with pytest.raises(
        jig_runner.JigRunnerError, match="external Jig execution failed"
    ) as caught:
        _ = jig_runner.run_jig("check", root=tmp_path)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    "malformed",
    [
        "wrong_command",
        "tuple_args",
        "foreign_args",
        "foreign_argument",
        "unexpected_stdout",
        "unexpected_stderr",
        "foreign_stdout",
        "foreign_stderr",
    ],
)
def test_runner_rejects_forged_uncaptured_process_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    malformed: str,
) -> None:
    """An uncaptured Jig success must match exactly the launched argv and IO."""
    _ = _pinned_launchers(tmp_path)
    monkeypatch.setattr(jig_runner.shutil, "which", _resolve_fixture_jig)

    class ForeignArgs(list[str]):
        def __eq__(self, _other: object) -> bool:
            raise AssertionError("foreign args equality executed")

    class ForeignText(str):
        def __str__(self) -> str:
            raise AssertionError("foreign output formatting executed")

    def execute(args: list[str], **_options: object) -> sp.CompletedProcess[str]:
        receipt_args: object = args
        stdout: object = None
        stderr: object = None
        if malformed == "wrong_command":
            receipt_args = [args[0], "doctor", *args[2:]]
        elif malformed == "tuple_args":
            receipt_args = tuple(args)
        elif malformed == "foreign_args":
            receipt_args = ForeignArgs(args)
        elif malformed == "foreign_argument":
            receipt_args = [ForeignText(args[0]), *args[1:]]
        elif malformed == "unexpected_stdout":
            stdout = ""
        elif malformed == "unexpected_stderr":
            stderr = b""
        elif malformed == "foreign_stdout":
            stdout = ForeignText("")
        elif malformed == "foreign_stderr":
            stderr = ForeignText("")
        return sp.CompletedProcess(
            cast("list[str]", cast("object", receipt_args)),
            0,
            stdout=cast("str", stdout),
            stderr=cast("str", stderr),
        )

    monkeypatch.setattr(jig_runner.sp, "run", execute)
    with pytest.raises(jig_runner.JigRunnerError, match="invalid process completion"):
        _ = jig_runner.run_jig("check", root=tmp_path)


@pytest.mark.parametrize("operation", ["is_symlink", "is_junction"])
@pytest.mark.parametrize("malformed", [0, None, object()])
def test_runner_rejects_non_native_redirect_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    malformed: object,
) -> None:
    """Untrusted boolean-like redirect answers cannot admit pinned tools."""
    pinned = _pinned_launchers(tmp_path)
    target = pinned / "chktex"
    original = getattr(Path, operation)

    def forged_status(path: Path) -> object:
        if path == target:
            return malformed
        return original(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, operation, forged_status)
        with pytest.raises(jig_runner.JigRunnerError, match="redirected"):
            _ = jig_runner.jig_environment(tmp_path, {})


@pytest.mark.parametrize("operation", ["lstat", "access"])
def test_runner_rejects_non_native_executable_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    """A forged file-status or executable-mode receipt fails closed."""
    pinned = _pinned_launchers(tmp_path)
    target = pinned / "chktex"
    if operation == "lstat":
        native = Path.lstat

        class ForeignStat:
            @property
            def st_mode(self) -> object:
                raise AssertionError("foreign stat hook executed")

        def forged_lstat(path: Path) -> object:
            return ForeignStat() if path == target else native(path)

        with monkeypatch.context() as isolated:
            isolated.setattr(Path, "lstat", forged_lstat)
            with pytest.raises(jig_runner.JigRunnerError, match="missing executable"):
                _ = jig_runner.jig_environment(tmp_path, {})
    else:
        native_access = os.access

        def forged_access(path: Path, mode: int) -> object:
            return 1 if path == target else native_access(path, mode)

        with monkeypatch.context() as isolated:
            isolated.setattr(os, "access", forged_access)
            with pytest.raises(jig_runner.JigRunnerError, match="missing executable"):
                _ = jig_runner.jig_environment(tmp_path, {})


@pytest.mark.parametrize("external", [False, True])
@pytest.mark.parametrize("mode", ["foreign", "boolean", "negative", "oversized"])
def test_runner_rejects_invalid_native_file_mode_without_host_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    external: bool,
    mode: str,
) -> None:
    """Even an exact stat_result cannot authorize a foreign or invalid mode."""
    pinned = _pinned_launchers(tmp_path)
    target = pinned / "chktex"
    inherited: dict[str, str] = {}
    if external:
        directory = tmp_path.parent / f"jig-mode-{tmp_path.name}"
        directory.mkdir()
        target = directory / "chktex"
        _ = target.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        target.chmod(0o700)
        inherited[jig_runner.EXTERNAL_TOOL_BIN_VARIABLE] = str(directory)
    native_lstat = Path.lstat

    class ForeignMode:
        def __index__(self) -> int:
            raise AssertionError("foreign file-mode index hook executed")

        def __and__(self, _other: object) -> int:
            raise AssertionError("foreign file-mode mask hook executed")

    invalid: object = {
        "foreign": ForeignMode(),
        "boolean": True,
        "negative": -1,
        "oversized": 1 << 100,
    }[mode]

    def forged_lstat(path: Path) -> os.stat_result:
        status = native_lstat(path)
        if path == target:
            return os.stat_result(
                cast("tuple[float, ...]", cast("object", (invalid, *tuple(status)[1:])))
            )
        return status

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "lstat", forged_lstat)
        pattern = "external.*directory" if external else "missing executable"
        with pytest.raises(jig_runner.JigRunnerError, match=pattern):
            _ = jig_runner.jig_environment(tmp_path, inherited)


def test_runner_cli_never_formats_foreign_tool_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A forged runner error must not execute its formatting hooks."""

    class ForeignError(jig_runner.JigRunnerError):
        def __str__(self) -> str:
            raise AssertionError("foreign runner error formatter executed")

    def fail(_command: str) -> int:
        raise ForeignError("unsafe private diagnostic")

    monkeypatch.setattr(jig_runner, "run_jig", fail)
    assert jig_runner.main(["check"]) == 1
    output = capsys.readouterr()
    assert "ForeignError" in output.err
    assert "unsafe private diagnostic" not in output.err
    assert not output.out


@pytest.mark.parametrize("receipt", [object(), b"/real/jig", "subclass"])
def test_runner_rejects_foreign_executable_discovery_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """Only a native executable path may be sent to a Jig subprocess."""
    _ = _pinned_launchers(tmp_path)

    class ForeignPath(str):
        def __fspath__(self) -> str:
            raise AssertionError("foreign executable path hook executed")

    result = ForeignPath("/real/jig") if receipt == "subclass" else receipt
    monkeypatch.setattr(jig_runner.shutil, "which", lambda _: result)

    def forbidden_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("foreign executable reached subprocess")

    monkeypatch.setattr(jig_runner.sp, "run", forbidden_run)
    with pytest.raises(jig_runner.JigRunnerError, match="discovery receipt"):
        _ = jig_runner.run_jig("check", root=tmp_path)


@pytest.mark.parametrize("response", [0, 1, None, object()])
def test_external_runner_rejects_non_native_directory_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    response: object,
) -> None:
    """An external directory must produce a native boolean status."""
    _ = _pinned_launchers(tmp_path)
    external = tmp_path.parent / f"native-bin-{tmp_path.name}"
    external.mkdir()
    tool = external / "chktex"
    _ = tool.write_bytes(b"#!/bin/sh\nexit 0\n")
    tool.chmod(0o700)
    original_is_dir = Path.is_dir

    def forged_is_dir(path: Path) -> object:
        return response if path == external else original_is_dir(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "is_dir", forged_is_dir)
        with pytest.raises(jig_runner.JigRunnerError, match="external.*directory"):
            _ = jig_runner.jig_environment(
                tmp_path,
                {jig_runner.EXTERNAL_TOOL_BIN_VARIABLE: str(external)},
            )


def test_external_runner_rejects_foreign_resolved_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Never invoke a foreign resolved-path method as authority."""
    _ = _pinned_launchers(tmp_path)
    external = tmp_path.parent / f"native-resolved-{tmp_path.name}"
    external.mkdir()
    tool = external / "chktex"
    _ = tool.write_bytes(b"#!/bin/sh\nexit 0\n")
    tool.chmod(0o700)

    class ForeignResolved:
        def is_relative_to(self, _other: object) -> bool:
            raise AssertionError("foreign path membership hook executed")

    native_resolve = Path.resolve

    def forged_resolve(path: Path, strict: bool = False) -> object:
        if path == external:
            return ForeignResolved()
        return native_resolve(path, strict=strict)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "resolve", forged_resolve)
        with pytest.raises(jig_runner.JigRunnerError, match="external.*directory"):
            _ = jig_runner.jig_environment(
                tmp_path,
                {jig_runner.EXTERNAL_TOOL_BIN_VARIABLE: str(external)},
            )
