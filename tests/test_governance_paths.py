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
#   - Authored repository-path and durable-surface hygiene evidence.
# - Must-Not:
#   - Inspect ignored dependencies, caches, or Jig's own configuration tree.
# - Allows:
#   - Inputs: repository-authored textual source and documentation.
#   - Outputs: exact path diagnostics and immutable-source identity checks.
#   - Side effects: repository reads only.
# - Split-When:
#   - Split when general link or path validation gains a separate authority.
# - Merge-When:
#   - Merge when Jig directly validates authored repository path references.
# - Summary:
#   - Prevents malformed Jig paths and retired historical source roots.
# - Description:
#   - Regresses path corruption and immutable authority drift.
# - Usage:
#   - Runs with the repository Python test suite.
# - Defaults:
#   - Generated paths are excluded; governed authority roots are exact.
#

"""Repository-authored Jig path hygiene regressions."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DUPLICATED_JIG_ROOT = re.compile(r"\.jig/[^\s`\"']*/\.jig/")
HISTORICAL_INTERPRETER = ROOT / (
    "src/interoperability/historical-malbolge/adapter-outbound/main.c"
)
HISTORICAL_INTERPRETER_BYTES = 4_738
HISTORICAL_INTERPRETER_SHA256 = (
    "fe29a717f9f684d6cc81d5c63273d446d9c65fec73e62164538514d5737b07a6"
)
RETIRED_HISTORICAL_ROOT = "tools/" + "malbolge/"
FORMAL_SPECIFICATION = ROOT / (
    "src/specification/formal-model/math/specification"
)
FORMAL_SPECIFICATION_MANIFEST = ROOT / (
    "src/specification/formal-model/function.yml"
)
RETIRED_FORMAL_SPECIFICATION_ROOT = re.compile(
    r"(?<!formal-model/)math/" + r"specification/"
)
EXCLUDED_DIRECTORIES = frozenset({
    ".cache",
    ".dependencies",
    ".git",
    ".jig",
    ".temp",
    "node_modules",
    "target",
})
ASCII_CONTROL_LIMIT = 32
ALLOWED_TEXT_CONTROL_BYTES = frozenset({9, 10, 13})
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


def test_authored_text_has_no_binary_control_bytes() -> None:
    """Authored text uses escapes instead of embedded binary controls."""
    violations = [
        f"{path.relative_to(ROOT).as_posix()}:{offset}:0x{byte:02x}"
        for path in _authored_text_paths()
        for offset, byte in enumerate(path.read_bytes())
        if byte < ASCII_CONTROL_LIMIT and byte not in ALLOWED_TEXT_CONTROL_BYTES
    ]
    assert not violations, "binary controls in authored text:\n" + "\n".join(
        violations
    )


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


def test_historical_interpreter_uses_governed_interoperability_root() -> None:
    """Historical source references resolve to the governed immutable file."""
    assert HISTORICAL_INTERPRETER.is_file()
    source = HISTORICAL_INTERPRETER.read_bytes()
    assert len(source) == HISTORICAL_INTERPRETER_BYTES
    assert sha256(source).hexdigest() == HISTORICAL_INTERPRETER_SHA256
    violations = [
        f"{path.relative_to(ROOT).as_posix()}:{line_number}: {line.strip()}"
        for path in _authored_text_paths()
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(),
            1,
        )
        if RETIRED_HISTORICAL_ROOT in line
    ]
    assert not violations, "retired historical roots:\n" + "\n".join(violations)


def test_formal_specification_uses_governed_function_root() -> None:
    """Global math references resolve to the formal-model function."""
    assert FORMAL_SPECIFICATION.is_dir()
    violations = [
        f"{path.relative_to(ROOT).as_posix()}:{line_number}: {line.strip()}"
        for path in _authored_text_paths()
        if path != FORMAL_SPECIFICATION_MANIFEST
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(),
            1,
        )
        if RETIRED_FORMAL_SPECIFICATION_ROOT.search(line)
    ]
    assert not violations, "retired formal roots:\n" + "\n".join(violations)
