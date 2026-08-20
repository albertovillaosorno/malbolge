# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
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
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

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


def test_corpus_walk_errors_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An inaccessible subtree cannot disappear from comparison evidence."""
    root = tmp_path / "corpus"
    root.mkdir()

    def fail_walk(
        path: Path,
        *,
        top_down: bool = True,
        on_error: Callable[[OSError], object] | None = None,
        follow_symlinks: bool = False,
    ) -> object:
        _ = path, top_down, follow_symlinks
        assert on_error is not None
        _ = on_error(PermissionError("blocked comparison corpus"))
        return iter(())

    monkeypatch.setattr(Path, "walk", fail_walk)
    with pytest.raises(
        generate._ComparisonError, match="corpus traversal failed"
    ):
        _ = generate._corpus_metrics(root)


def test_corpus_entry_status_errors_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A discovered inaccessible file cannot vanish from corpus hashes."""
    root = tmp_path / "corpus"
    blocked = root / "blocked.c"

    def fake_walk(
        path: Path,
        *,
        top_down: bool = True,
        on_error: Callable[[OSError], object] | None = None,
        follow_symlinks: bool = False,
    ) -> object:
        _ = top_down, on_error, follow_symlinks
        return iter(((path, list[str](), [blocked.name]),))

    original_stat = Path.stat

    def fail_stat(path: Path, *args: object, **kwargs: object) -> object:
        if path == blocked:
            message = "blocked comparison entry"
            raise PermissionError(message)
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "walk", fake_walk)
    monkeypatch.setattr(Path, "stat", fail_stat)
    with pytest.raises(generate._ComparisonError, match="entry status failed"):
        _ = generate._corpus_metrics(root)


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
    tools = tmp_path / "tools"
    tools.mkdir()
    clang = tools / "clang"
    clang_tidy = tools / "clang-tidy"
    clang_format = tools / "clang-format"
    for tool in (clang, clang_tidy, clang_format):
        tool.touch()
    monkeypatch.setattr(generate, "CLANG", clang)
    monkeypatch.setattr(generate, "CLANG_TIDY", clang_tidy)
    monkeypatch.setattr(generate, "CLANG_FORMAT", clang_format)

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
