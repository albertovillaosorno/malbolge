# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Provision the repository-local Python validation environment."""

from __future__ import annotations

from pathlib import Path
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed repo-local argv, never a shell command.
import sys
from typing import Never
import venv

ROOT = Path(__file__).resolve().parents[2]
PYTHON_VERSION = (3, 14, 6)
ENVIRONMENT = ROOT / ".dependencies" / "python" / "3.14.6"
REQUIREMENTS = (
    ROOT / "scripts" / "bootstrap" / ("python-validation-requirements.txt")
)
SCRIPTS = ENVIRONMENT / "Scripts"
PYTHON = SCRIPTS / "python.exe"
PYTEST_JIG = SCRIPTS / "pytest-jig.cmd"
PYTHON_JIG = SCRIPTS / "python-jig.cmd"
EXPECTED_TOOLS = {
    "basedpyright.exe": "basedpyright 1.39.9",
    "pytest-jig.cmd": "pytest 9.1.1",
    "python-jig.cmd": "Python 3.14.6",
    "ruff.exe": "ruff 0.16.0",
}


class ProvisionError(RuntimeError):
    """Deterministic local Python provisioning failure."""


def _fail(message: str) -> Never:
    raise ProvisionError(message)


def _check_host_python() -> None:
    observed = sys.version_info[:3]
    if observed != PYTHON_VERSION:
        expected_text = ".".join(str(part) for part in PYTHON_VERSION)
        observed_text = ".".join(str(part) for part in observed)
        _fail(f"bootstrap requires Python {expected_text}; got {observed_text}")


def _run(command: list[str]) -> str:
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - argv is repository-controlled.
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        shell=False,
        text=True,
    )
    return completed.stdout.strip()


def _cache_line() -> str:
    return r'set "PYTHONPYCACHEPREFIX=%~dp0..\..\..\..\.cache\python\pycache"'


def _write_launchers() -> None:
    cache_line = _cache_line()
    python_line = '"%~dp0python.exe" %*'
    python_launcher = f"@echo off\r\n{cache_line}\r\n{python_line}\r\n"
    _ = PYTHON_JIG.write_text(
        python_launcher,
        encoding="ascii",
        newline="",
    )
    pytest_line = '"%~dp0python.exe" -m pytest %*'
    pytest_launcher = f"@echo off\r\n{cache_line}\r\n{pytest_line}\r\n"
    _ = PYTEST_JIG.write_text(
        pytest_launcher,
        encoding="ascii",
        newline="",
    )


def _provision() -> None:
    if not PYTHON.is_file():
        builder = venv.EnvBuilder(with_pip=True, clear=False)
        builder.create(ENVIRONMENT)
    _ = _run([
        str(PYTHON),
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-input",
        "--requirement",
        str(REQUIREMENTS),
    ])
    _write_launchers()


def _verify_tool(executable: str, expected: str) -> None:
    path = SCRIPTS / executable
    if not path.is_file():
        _fail(f"missing provisioned tool: {path}")
    output = _run([str(path), "--version"])
    first_line = output.partition("\n")[0]
    if expected not in first_line:
        _fail(f"unexpected {executable} version: {first_line!r}")


def _verify() -> None:
    for executable, expected in EXPECTED_TOOLS.items():
        _verify_tool(executable, expected)


def main() -> int:
    """Provision and verify the exact repository-local Python tool set.

    Returns:
        Zero after successful provisioning, otherwise one.

    """
    try:
        _check_host_python()
        _provision()
        _verify()
    except (OSError, ProvisionError, subprocess.SubprocessError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    _ = sys.stdout.write(
        f"python validation environment ready: {ENVIRONMENT}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
