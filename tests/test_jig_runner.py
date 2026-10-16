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
