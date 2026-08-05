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
#   - Authored repository-path hygiene regression evidence.
# - Must-Not:
#   - Inspect ignored dependencies, caches, or Jig's own configuration tree.
# - Allows:
#   - Inputs: repository-authored textual source and documentation.
#   - Outputs: exact path/line diagnostics for duplicated Jig root segments.
#   - Side effects: repository reads only.
# - Split-When:
#   - Split when general link or path validation gains a separate authority.
# - Merge-When:
#   - Merge when Jig directly validates authored repository path references.
# - Summary:
#   - Prevents malformed nested `.jig` paths outside the configuration root.
# - Description:
#   - Regresses executable and documentary path corruption found in the tree.
# - Usage:
#   - Runs with the repository Python test suite.
# - Defaults:
#   - Generated, ignored, binary, and Jig-owned paths are excluded.
#

"""Repository-authored Jig path hygiene regressions."""

from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DUPLICATED_JIG_ROOT = re.compile(r"\.jig/[^\s`\"']*/\.jig/")
EXCLUDED_DIRECTORIES = frozenset({
    ".cache",
    ".dependencies",
    ".git",
    ".jig",
    ".temp",
    "node_modules",
    "target",
})
TEXT_SUFFIXES = frozenset({
    ".c",
    ".cmd",
    ".h",
    ".json",
    ".md",
    ".mdc",
    ".ps1",
    ".py",
    ".rs",
    ".sh",
    ".tex",
    ".toml",
    ".yaml",
    ".yml",
})


def _authored_text_paths() -> tuple[Path, ...]:
    paths: list[Path] = []
    for directory, directories, filenames in ROOT.walk():
        directories[:] = [
            name for name in directories if name not in EXCLUDED_DIRECTORIES
        ]
        paths.extend(
            directory / name
            for name in filenames
            if Path(name).suffix.lower() in TEXT_SUFFIXES
        )
    return tuple(paths)


def test_authored_text_has_no_nested_jig_root_paths() -> None:
    """A repository path cannot re-enter `.jig` after already selecting it."""
    violations = [
        f"{path.relative_to(ROOT).as_posix()}:{line_number}: {line.strip()}"
        for path in _authored_text_paths()
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(),
            1,
        )
        if DUPLICATED_JIG_ROOT.search(line)
    ]
    assert not violations, "nested Jig paths:\n" + "\n".join(violations)
