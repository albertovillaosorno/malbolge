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
#   - Provision the repository-local Python validation environment.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Provision the repository-local Python validation environment."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import stat

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed repository-local argv.
import sys
from typing import Final
from typing import Never
import venv

from scripts.repository_root import repository_root

ROOT: Final = repository_root(Path(__file__))
PYTHON_VERSION: Final = (3, 14, 6)
REQUIREMENTS: Final = (
    ROOT
    / "src/automation/repository/composition/scripts/bootstrap"
    / "python-validation-requirements.txt"
)
WINDOWS_OS_NAME: Final = "nt"
WINDOWS: Final = os.name == WINDOWS_OS_NAME


@dataclass(frozen=True, slots=True)
class ValidationEnvironmentLayout:
    """Paths for one platform-specific repository validation environment."""

    environment: Path
    expected_tools: tuple[tuple[str, str], ...]
    pytest: Path
    pytest_launcher: Path
    python: Path
    python_launcher: Path
    scripts: Path


class ProvisionError(RuntimeError):
    """Deterministic local Python provisioning failure."""


def validation_layout(
    root: Path = ROOT,
    *,
    windows: bool = WINDOWS,
) -> ValidationEnvironmentLayout:
    """Resolve repository-local validation paths for one host family.

    Returns:
        Exact environment, interpreter, launcher, and tool paths.

    """
    environment = root / ".dependencies" / "python" / "3.14.6"
    scripts = environment / ("Scripts" if windows else "bin")
    executable_suffix = ".exe" if windows else ""
    launcher_suffix = ".cmd" if windows else ""
    return ValidationEnvironmentLayout(
        environment=environment,
        expected_tools=(
            (f"basedpyright{executable_suffix}", "basedpyright 1.39.9"),
            (f"pytest{executable_suffix}", "pytest 9.1.1"),
            (f"python-jig{launcher_suffix}", "Python 3.14.6"),
            (f"ruff{executable_suffix}", "ruff 0.16.0"),
        ),
        pytest=scripts / f"pytest{executable_suffix}",
        pytest_launcher=scripts / f"pytest-jig{launcher_suffix}",
        python=scripts / ("python.exe" if windows else "python"),
        python_launcher=scripts / f"python-jig{launcher_suffix}",
        scripts=scripts,
    )


LAYOUT: Final = validation_layout()
ENVIRONMENT: Final = LAYOUT.environment
SCRIPTS: Final = LAYOUT.scripts
PYTHON: Final = LAYOUT.python
PYTEST: Final = LAYOUT.pytest
PYTEST_JIG: Final = LAYOUT.pytest_launcher
PYTHON_JIG: Final = LAYOUT.python_launcher
EXPECTED_TOOLS: Final = dict(LAYOUT.expected_tools)


def _fail(message: str) -> Never:
    raise ProvisionError(message)


def _check_host_python() -> None:
    observed = sys.version_info[:3]
    if observed != PYTHON_VERSION:
        expected_text = ".".join(str(part) for part in PYTHON_VERSION)
        observed_text = ".".join(str(part) for part in observed)
        _fail(f"bootstrap requires Python {expected_text}; got {observed_text}")


def _run(command: list[str]) -> str:
    # jig-ignore-next-line: indivisible reviewed identifier
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed repository-local argv.
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        shell=False,
        text=True,
    )
    return completed.stdout.strip()


def _windows_cache_line() -> str:
    return r'set "PYTHONPYCACHEPREFIX=%~dp0..\..\..\..\.cache\python\pycache"'


def _windows_launcher_text(*, pytest: bool) -> str:
    cache_line = _windows_cache_line()
    invocation = (
        '"%~dp0python.exe" -m pytest %*' if pytest else '"%~dp0python.exe" %*'
    )
    return f"@echo off\r\n{cache_line}\r\n{invocation}\r\n"


def _posix_launcher_text(*, pytest: bool) -> str:
    invocation = (
        'exec "$SCRIPT_DIR/python" -m pytest "$@"'
        if pytest
        else 'exec "$SCRIPT_DIR/python" "$@"'
    )
    cache = (
        'export PYTHONPYCACHEPREFIX="'
        '$SCRIPT_DIR/../../../../.cache/python/pycache"'
    )
    return (
        "#!/bin/sh\n"
        "set -eu\n"
        'SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        f"{cache}\n"
        f"{invocation}\n"
    )


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    _ = path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def write_launchers(
    layout: ValidationEnvironmentLayout = LAYOUT,
    *,
    windows: bool = WINDOWS,
) -> None:
    """Write platform-native Python and pytest launchers."""
    if windows:
        _ = layout.python_launcher.write_text(
            _windows_launcher_text(pytest=False),
            encoding="ascii",
            newline="",
        )
        _ = layout.pytest_launcher.write_text(
            _windows_launcher_text(pytest=True),
            encoding="ascii",
            newline="",
        )
        return
    _ = layout.python_launcher.write_text(
        _posix_launcher_text(pytest=False),
        encoding="ascii",
        newline="\n",
    )
    _ = layout.pytest_launcher.write_text(
        _posix_launcher_text(pytest=True),
        encoding="ascii",
        newline="\n",
    )
    _make_executable(layout.python_launcher)
    _make_executable(layout.pytest_launcher)


def _provision(layout: ValidationEnvironmentLayout) -> None:
    if not layout.python.is_file():
        builder = venv.EnvBuilder(with_pip=True, clear=False)
        builder.create(layout.environment)
    _ = _run([
        str(layout.python),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        "--requirement",
        str(REQUIREMENTS),
    ])
    write_launchers(layout, windows=WINDOWS)


def _verify_tool(
    layout: ValidationEnvironmentLayout,
    executable: str,
    expected: str,
) -> None:
    path = layout.scripts / executable
    if not path.is_file():
        _fail(f"missing provisioned tool: {path}")
    output = _run([str(path), "--version"])
    first_line = output.partition("\n")[0]
    if expected not in first_line:
        _fail(f"unexpected {executable} version: {first_line!r}")


def _verify(layout: ValidationEnvironmentLayout) -> None:
    for executable, expected in layout.expected_tools:
        _verify_tool(layout, executable, expected)


def initialize() -> ValidationEnvironmentLayout:
    """Provision and verify the exact repository-local Python tool set.

    Returns:
        Platform-native environment layout after successful verification.

    """
    _check_host_python()
    _provision(LAYOUT)
    _verify(LAYOUT)
    return LAYOUT


def main() -> int:
    """Provision and verify the exact repository-local Python tool set.

    Returns:
        Zero after successful provisioning, otherwise one.

    """
    try:
        layout = initialize()
    except (OSError, ProvisionError, subprocess.SubprocessError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    _ = sys.stdout.write(
        f"python validation environment ready: {layout.environment}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
