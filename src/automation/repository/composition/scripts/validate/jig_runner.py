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
#   - Repository-scoped Jig validation tool precedence.
# - Must-Not:
#   - Change Jig's validation policy or declared tool versions.
# - Allows:
#   - Inputs: Jig doctor, check, or validate command.
#   - Outputs: Jig process status and untouched diagnostics.
#   - Side effects: repository-local Jig validation state.
# - Split-When:
#   - Other hosts need independent tool-resolution logic.
# - Merge-When:
#   - Jig honors configured paths for all external tool probing.
# - Summary:
#   - Keep the pinned ChkTeX and LaTeXmk ahead of ambient host aliases.
# - Description:
#   - Invoke external Jig with repository-owned validation tool precedence.
# - Usage:
#   - python3.14 -B -m scripts.validate.jig_runner check
# - Defaults:
#   - Missing pinned tools fail closed.
#

"""Invoke Jig with repository-owned Linux validation tool precedence."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
from stat import S_ISREG
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import cast

from scripts.repository_root import repository_root

ROOT = repository_root(Path(__file__))
COMMANDS = ("check", "doctor", "validate")
PINNED_TOOLS = ("chktex", "latexmk")
LINUX_PLATFORM = "linux"


class JigRunnerError(RuntimeError):
    """One required validation tool cannot be used."""


def _unredirected_launcher(path: Path) -> bool:
    """Reject a launcher reached through any filesystem redirect.

    Returns:
        True only for a direct leaf with nonredirecting ancestor paths.

    """
    try:
        return not any(
            component.is_symlink() or component.is_junction()
            for component in (path, *path.parents)
        )
    except OSError, ValueError:
        return False


def _regular_executable(path: Path) -> bool:
    """Check direct regular-file and executable-mode admission.

    Returns:
        True only for a regular file executable by the current process.

    """
    try:
        return S_ISREG(path.lstat().st_mode) and os.access(path, os.X_OK)
    except OSError:
        return False


def jig_environment(root: Path, inherited: dict[str, str]) -> dict[str, str]:
    """Put pinned host tools before ambient executable aliases.

    Returns:
        Fresh environment containing repository-local cache paths.

    Raises:
        JigRunnerError: A pinned tool launcher is missing or non-executable.

    """
    if sys.platform != LINUX_PLATFORM:
        message = "repository Jig runner currently supports Linux only"
        raise JigRunnerError(message)
    pinned_bin = root / ".dependencies/bin"
    for tool in PINNED_TOOLS:
        launcher = pinned_bin / tool
        if not _unredirected_launcher(launcher):
            message = f"redirected Jig validation tool path: {launcher}"
            raise JigRunnerError(message)
        if not _regular_executable(launcher):
            message = f"missing executable Jig validation tool: {launcher}"
            raise JigRunnerError(message)
    environment = dict(inherited)
    # Jig's external-tool discovery also probes PATH. A user-local version
    # may override the configured tool path, so remove ambient aliases.
    environment["PATH"] = f"{pinned_bin}{os.pathsep}{os.defpath}"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["RUFF_CACHE_DIR"] = str(root / ".cache/ruff")
    return environment


def run_jig(command: str, *, root: Path = ROOT) -> int:
    """Run the external validator without command interpolation.

    Returns:
        Jig's unmodified process exit code.

    Raises:
        JigRunnerError: Jig or a required pinned tool is unavailable.

    """
    if command not in COMMANDS:
        message = f"unsupported Jig command: {command}"
        raise JigRunnerError(message)
    executable = shutil.which("jig")
    if executable is None:
        message = "external Jig executable is unavailable"
        raise JigRunnerError(message)
    environment = jig_environment(root, dict(os.environ))
    try:
        result = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [executable, command, "--root", str(root)],
            check=False,
            cwd=root,
            env=environment,
            shell=False,
        )
    except OSError as error:
        message = f"external Jig execution failed: {error}"
        raise JigRunnerError(message) from error
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    """Parse one repository-local Jig command.

    Returns:
        Jig's status or one for unavailable prerequisites.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument("command", choices=COMMANDS)
    arguments = parser.parse_args(argv)
    try:
        return run_jig(cast("str", arguments.command))
    except JigRunnerError as error:
        _ = sys.stderr.write(f"jig runner: {error}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
