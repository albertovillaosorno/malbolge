#!/usr/bin/env python3
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
#   - Lightweight, public, local prerequisite checks for incoming PRs.
# - Must-Not:
#   - Reimplement Jig, assert semantic proofs, or approve pull requests.
# - Allows:
#   - Inputs: tracked source files and installed development tools.
#   - Outputs: tool diagnostics and a success/failure process exit code.
#   - Side effects: normal tool caches and ignored /.validate/ LaTeX output.
# - Split-When:
#   - A check needs independent policy or project-specific validation logic.
# - Merge-When:
#   - A shared contributor entrypoint replaces this small command runner.
# - Summary:
#   - One-command contributor checks using ordinary developer tools.
# - Description:
#   - Created for https://github.com/DannyBaanks (Malbolge researcher)
#   - And for anyone who wants to send and validate their PRs.
#   - Original implementation; no third-party code has been copied.
# - Usage:
#   - python3.14 -B scripts/validate.py
# - Defaults:
#   - Stop and fail on missing tools or the first failed command.

"""Run ordinary contributor checks without invoking Jig."""

from pathlib import Path
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys

ROOT = Path(__file__).resolve().parent.parent
PYTHON_CONFIG = ".jig/lang/python/ruff.toml"
DOCUMENT_CLASS = "\\documentclass"


def tool(local: str, name: str) -> str:
    """Use a repository bootstrap binary when present.

    Returns:
        The installed tool path or its public PATH command name.

    """
    installed = ROOT / local
    return str(installed) if installed.is_file() else name


def check(command: list[str]) -> None:
    """Run one fixed developer-tool invocation, without a shell."""
    sys.stdout.write(f"\n$ {" ".join(command)}\n")
    sys.stdout.flush()
    subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command, cwd=ROOT, check=True
    )


def latex_checks() -> None:
    """Lint LaTeX sources and compile standalone documents."""
    chktex = tool(".dependencies/bin/chktex", "chktex")
    latexmk = tool(".dependencies/bin/latexmk", "latexmk")
    sources = sorted((ROOT / "src").rglob("*.tex"))
    if not sources:
        return
    check([
        chktex,
        "-q",
        "-v0",
        "-g0",
        "-l",
        ".jig/lang/latex/chktexrc",
        *(str(source.relative_to(ROOT)) for source in sources),
    ])
    for source in sources:
        if DOCUMENT_CLASS in source.read_text(encoding="utf-8"):
            # Preserve source-relative directories: two report.tex documents
            # must not share LaTeXmk cache files or overwrite each other.
            output = (
                ROOT / ".validate" / "latex" / source.parent.relative_to(ROOT)
            )
            output.mkdir(parents=True, exist_ok=True)
            check([
                latexmk,
                "-pdf",
                "-cd",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-outdir={output}",
                str(source),
            ])


def main() -> int:
    """Run all checks in order, stopping at the first error.

    Returns:
        Zero only if every tool, test, and LaTeX document check passes.

    """
    cargo = tool(".dependencies/rust/1.98.1/bin/cargo", "cargo")
    ruff = tool(".dependencies/python/3.14.7/bin/ruff", "ruff")
    pyright = tool(
        ".dependencies/python/3.14.7/bin/basedpyright", "basedpyright"
    )
    pytest = tool(".dependencies/python/3.14.7/bin/pytest", "pytest")
    commands = [
        [cargo, "fmt", "--all", "--", "--check"],
        [
            cargo,
            "clippy",
            "--locked",
            "--workspace",
            "--all-targets",
            "--",
            "-D",
            "warnings",
        ],
        [cargo, "test", "--locked", "--workspace"],
        [ruff, "check", "--config", PYTHON_CONFIG, "."],
        [ruff, "format", "--check", "--config", PYTHON_CONFIG, "."],
        [pyright, "--project", ".jig/lang/python/pyrightconfig.json"],
        [pytest, "-c", ".jig/lang/python/pytest.ini"],
    ]
    try:
        for command in commands:
            check(command)
        latex_checks()
    except (OSError, subprocess.CalledProcessError) as error:
        sys.stderr.write(f"Validation failed: {error}\n")
        return 1
    sys.stdout.write("\nAll contributor checks passed.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
