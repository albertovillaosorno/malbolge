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
from typing import TYPE_CHECKING
from typing import cast

import pytest

from scripts.validate import jig_runner

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.skipif(
    sys.platform != jig_runner.LINUX_PLATFORM,
    reason="repository Jig runner uses Linux pinned tools",
)


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
        observed.append((
            args,
            options["cwd"],
            environment["PATH"],
            options["shell"],
        ))
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


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError, TypeError, AttributeError])
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
    with pytest.raises(jig_runner.JigRunnerError, match="external Jig execution failed") as caught:
        _ = jig_runner.run_jig("check", root=tmp_path)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError, TypeError, AttributeError])
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
