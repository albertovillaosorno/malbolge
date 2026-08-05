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
#   - DOOM quality-comparison repository/tool path regression evidence.
# - Must-Not:
#   - Measure or mutate a local DOOM corpus.
# - Allows:
#   - Inputs: repository-owned path constants and simulated tool probes.
#   - Outputs: exact path and command assertions.
#   - Side effects: test-local directories and monkeypatches only.
# - Split-When:
#   - Split when report generation gains independent corpus fixtures.
# - Merge-When:
#   - Merge when DOOM quality tests gain one unified owner.
# - Summary:
#   - Proves comparison probes resolve the repository-owned Clang policies.
# - Description:
#   - Prevents duplicated path segments and probes of unrelated default config.
# - Usage:
#   - Auto-discovered by the repository Python test suite.
# - Defaults:
#   - No LLVM process or user-supplied corpus is required.
#

"""DOOM quality-comparison path and tool-probe regressions."""

# ruff: file-ignore[private-member-access]
# pyright: reportPrivateUsage=false

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from algorithms.doom.quality.comparison import generate

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[5]


@dataclass(frozen=True, slots=True)
class _ProbeResult:
    returncode: int = 0
    stdout: str = ""


def test_repository_and_policy_paths_resolve_exactly() -> None:
    """The generator anchors tools and policies at the repository root."""
    assert generate.REPO_ROOT == ROOT
    assert generate.ROOT_TIDY == ROOT / ".jig/lang/cpp/.clang-tidy"
    assert generate.ROOT_FORMAT == ROOT / ".jig/lang/cpp/.clang-format"
    assert generate.ROOT_TIDY.is_file()
    assert generate.ROOT_FORMAT.is_file()


def test_input_probe_validates_the_selected_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tool admission probes the same explicit configs used for measurement."""
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    calls: list[tuple[list[str], Path]] = []

    def fake_run(
        arguments: list[str],
        cwd: Path = generate.REPO_ROOT,
    ) -> _ProbeResult:
        calls.append((arguments, cwd))
        return _ProbeResult()

    monkeypatch.setattr(generate, "_run", fake_run)
    generate._ensure_inputs(before, after)

    assert calls == [
        (
            [
                str(generate.CLANG_FORMAT),
                f"--style=file:{generate.ROOT_FORMAT}",
                "--assume-filename=probe.c",
            ],
            generate.REPO_ROOT,
        ),
        (
            [
                str(generate.CLANG_TIDY),
                "--verify-config",
                f"--config-file={generate.ROOT_TIDY}",
            ],
            generate.REPO_ROOT,
        ),
    ]
