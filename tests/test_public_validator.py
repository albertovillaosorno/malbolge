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
#   - Regression evidence for the lightweight external contributor validator.
# - Must-Not:
#   - Invoke Jig, Cargo, TeX, or installed external tools during unit tests.
# - Allows:
#   - Inputs: disposable source trees and mocked fixed command execution.
#   - Outputs: deterministic command/exit-status assertions.
#   - Side effects: temporary test-owned files only.
# - Split-When:
#   - The validator becomes a larger contributor workflow.
# - Merge-When:
#   - The public validator owns an equivalent focused test suite.
# - Summary:
#   - Ensures safe lockfile checks and isolated LaTeX artifact paths.
# - Description:
#   - Mocks developer tools; no local toolchain is needed for these tests.
# - Usage:
#   - pytest -c .jig/lang/python/pytest.ini tests/test_public_validator.py
# - Defaults:
#   - Missing tools and failed commands must fail closed.

"""Offline regression tests for the small public PR validator."""

from importlib.util import module_from_spec
from importlib.util import spec_from_file_location
from pathlib import Path
import subprocess  # ruff: ignore[suspicious-subprocess-import]
from tempfile import TemporaryDirectory
from typing import Protocol
from typing import cast
from unittest.mock import patch


class _Validator(Protocol):
    """Only the public command runner interface needed in these tests."""

    ROOT: Path

    def check(self, command: list[str]) -> None:
        """Execute a fixed local check."""
        ...

    def latex_checks(self) -> None:
        """Validate LaTeX sources."""
        ...

    def tool(self, local: str, name: str) -> str:
        """Resolve an installed tool."""
        ...

    def main(self) -> int:
        """Run the contributor gate."""
        ...


def _validator() -> _Validator:
    """Load only the root script, not the unrelated bootstrap package.

    Returns:
        The contributor validator implementation under test.

    """
    path = Path(__file__).resolve().parents[1] / "scripts/validate.py"
    spec = spec_from_file_location("_public_validator", path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast("_Validator", cast("object", module))


def _tool(_local: str, name: str) -> str:
    """Return a predictable command name in isolated command tests.

    Returns:
        The requested fallback tool name.

    """
    assert _local
    return name


def test_cargo_checks_cannot_rewrite_lockfile() -> None:
    """Contributor Cargo checks refuse lockfile changes."""
    validator = _validator()
    commands: list[list[str]] = []
    with (
        patch.object(validator, "check", side_effect=commands.append),
        patch.object(validator, "latex_checks"),
        patch.object(validator, "tool", side_effect=_tool),
    ):
        assert validator.main() == 0
    assert commands[0] == ["cargo", "fmt", "--all", "--", "--check"]
    assert commands[1] == [
        "cargo",
        "clippy",
        "--locked",
        "--workspace",
        "--all-targets",
        "--",
        "-D",
        "warnings",
    ]
    assert commands[2] == ["cargo", "test", "--locked", "--workspace"]
    assert len(commands) == len([
        "fmt",
        "clippy",
        "test",
        "ruff-check",
        "ruff-format",
        "basedpyright",
        "pytest",
    ])


def test_same_named_latex_documents_have_separate_build_outputs() -> None:
    """Two unrelated report.tex sources cannot share a TeX cache/output."""
    validator = _validator()
    with TemporaryDirectory() as directory:
        root = Path(directory)
        for relative in ("src/one/report.tex", "src/two/report.tex"):
            path = root / relative
            path.parent.mkdir(parents=True)
            assert (
                path.write_text("\\documentclass{article}\n", encoding="utf-8")
                > 0
            )
        assert (root / "src/shared.tex").write_text(
            "plain fragment", encoding="utf-8"
        ) > 0
        commands: list[list[str]] = []
        with (
            patch.object(validator, "ROOT", root),
            patch.object(validator, "check", side_effect=commands.append),
            patch.object(validator, "tool", side_effect=_tool),
        ):
            validator.latex_checks()
        assert len(commands) == len(["chktex", "latexmk-one", "latexmk-two"])
        assert commands[0][:4] == ["chktex", "-q", "-v0", "-g0"]
        assert commands[0][-3:] == [
            "src/one/report.tex",
            "src/shared.tex",
            "src/two/report.tex",
        ]
        outputs = [
            next(arg for arg in command if arg.startswith("-outdir="))
            for command in commands[1:]
        ]
        for command in commands[1:]:
            option = command.index("-r")
            assert command[option + 1] == str(
                root / ".jig/lang/latex/latexmkrc"
            )
        assert outputs == [
            f"-outdir={root / ".validate/latex/src/one"}",
            f"-outdir={root / ".validate/latex/src/two"}",
        ]
        assert (root / ".validate/latex/src/one").is_dir()
        assert (root / ".validate/latex/src/two").is_dir()


def test_missing_tool_fails_without_running_remaining_checks() -> None:
    """No missing development tool may silently pass validation."""
    validator = _validator()
    with (
        patch.object(
            validator, "check", side_effect=FileNotFoundError
        ) as check,
        patch.object(validator, "latex_checks") as latex,
    ):
        assert validator.main() == 1
    assert check.call_count == 1
    latex.assert_not_called()


def test_nonzero_tool_exit_fails_closed() -> None:
    """Failed tools prevent execution of subsequent validation phases."""
    validator = _validator()
    with (
        patch.object(
            validator,
            "check",
            side_effect=subprocess.CalledProcessError(4, ["cargo", "fmt"]),
        ),
        patch.object(validator, "latex_checks") as latex,
    ):
        assert validator.main() == 1
    latex.assert_not_called()
