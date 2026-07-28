# File:
#   - bibliography.py
# Path:
#   - scripts/validate/bibliography.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
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
#   - Validate bibliography taxonomy and source-record provenance.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Validate bibliography taxonomy and source-record provenance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Never

ROOT = Path(__file__).resolve().parents[2]
BIBLIOGRAPHY_ROOT = ROOT / "docs" / "bibliography"
CANONICAL_TEMPLATE = (
    BIBLIOGRAPHY_ROOT / "provenance-and-methodology" / "template.md"
)
CATEGORIES = (
    "languages",
    "legal-and-regulatory",
    "libraries",
    "organizations-and-projects",
    "platforms-and-runtimes",
    "provenance-and-methodology",
    "publications",
    "specifications-and-standards",
    "tooling",
)
REQUIRED_HEADINGS = (
    "## Status",
    "## Subject",
    "## Repository Use",
    "## Provenance",
    "## Identity And Version",
    "## License Or Terms",
    "## Evidence",
    "## Sources",
)
BASELINE_RECORDS = (
    "languages/c.md",
    "languages/rust.md",
    "platforms-and-runtimes/aarch64.md",
    "platforms-and-runtimes/accelerators/nvidia-cuda.md",
    "platforms-and-runtimes/accelerators/pytorch.md",
    "platforms-and-runtimes/compiler/clang-libtooling.md",
    "platforms-and-runtimes/compiler/llvm-ir.md",
    "platforms-and-runtimes/rocm.md",
    "platforms-and-runtimes/x86-64.md",
    "provenance-and-methodology/research/acm-artifact-evaluation.md",
    "provenance-and-methodology/research/acm-sigsoft-empirical-standards.md",
    "publications/superoptimization/egg.md",
    "publications/superoptimization/souper.md",
    "publications/superoptimization/stoke.md",
    "publications/verification/alive2.md",
    "specifications-and-standards/citation-file-format.md",
    "specifications-and-standards/commonmark.md",
    "specifications-and-standards/malbolge/malbolge-1998.md",
    "specifications-and-standards/toml.md",
    "tooling/clang-tidy.md",
    "tooling/git.md",
    "tooling/latex.md",
)
DATE_PATTERN = re.compile(r"20\d{2}-\d{2}-\d{2}")
PLACEHOLDERS = (
    "{required}",
    "Open; evidence unverified.",
)
ADR_DIR = "adr"
UNRESOLVED_HEADING = "### Unresolved"
BASELINE_COVERAGE_HEADING = "### Baseline Coverage"
SPECIAL_FILES = frozenset({"README.md", "disclaimer.md", "template.md"})


class BibliographyValidationError(ValueError):
    """Bibliography topology or source provenance violates the contract."""


@dataclass(frozen=True, slots=True)
class BibliographyReport:
    """Validated bibliography coverage summary."""

    categories: tuple[str, ...]
    record_count: int
    required_baseline_count: int


def _fail(message: str) -> Never:
    raise BibliographyValidationError(message)


def _relative(path: Path) -> str:
    return path.relative_to(BIBLIOGRAPHY_ROOT).as_posix()


def _source_record_paths() -> tuple[Path, ...]:
    records: list[Path] = []
    for path in BIBLIOGRAPHY_ROOT.rglob("*.md"):
        relative = path.relative_to(BIBLIOGRAPHY_ROOT)
        if path.name in SPECIAL_FILES or ADR_DIR in relative.parts:
            continue
        records.append(path)
    return tuple(sorted(records))


def _validate_first_level_taxonomy() -> None:
    expected = frozenset((*CATEGORIES, ADR_DIR))
    actual = frozenset(
        path.name for path in BIBLIOGRAPHY_ROOT.iterdir() if path.is_dir()
    )
    if actual != expected:
        _fail(f"bibliography first-level taxonomy mismatch: {sorted(actual)}")


def _validate_directory_catalogs() -> None:
    directories = (
        BIBLIOGRAPHY_ROOT,
        *sorted(path for path in BIBLIOGRAPHY_ROOT.rglob("*") if path.is_dir()),
    )
    for directory in directories:
        if not (directory / "README.md").is_file():
            relative = _relative(directory)
            _fail(f"bibliography directory lacks README.md: {relative}")


def _validate_templates() -> None:
    if not CANONICAL_TEMPLATE.is_file():
        _fail("canonical bibliography source template is missing")
    if (BIBLIOGRAPHY_ROOT / "template.md").exists():
        _fail("duplicate root bibliography template is forbidden")


def _validate_topology() -> None:
    _validate_first_level_taxonomy()
    _validate_directory_catalogs()
    _validate_templates()


def _heading_positions(text: str, label: str) -> tuple[int, ...]:
    positions: list[int] = []
    for heading in REQUIRED_HEADINGS:
        position = text.find(heading)
        if position < 0:
            _fail(f"{label} missing required heading: {heading}")
        positions.append(position)
    if positions != sorted(positions):
        _fail(f"{label} bibliography headings are out of order")
    return tuple(positions)


def _section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    body_start = start + len(heading)
    next_heading = text.find("\n## ", body_start)
    if next_heading < 0:
        return text[body_start:].strip()
    return text[body_start:next_heading].strip()


def _validate_placeholders(text: str, label: str) -> None:
    for placeholder in PLACEHOLDERS:
        if placeholder in text:
            message = (
                f"{label} retains unresolved template placeholder: "
                f"{placeholder}"
            )
            _fail(message)


def _validate_dated_uncertainty(text: str, label: str) -> None:
    if DATE_PATTERN.search(text) is None:
        _fail(f"{label} lacks a dated retrieval/review provenance marker")
    evidence = _section(text, "## Evidence")
    if UNRESOLVED_HEADING not in evidence:
        _fail(f"{label} lacks explicit unresolved/uncertainty evidence")


def _validate_source_entries(text: str, label: str) -> None:
    sources = _section(text, "## Sources")
    source_lines = sources.splitlines()
    if not sources or not any(line.startswith("- ") for line in source_lines):
        _fail(f"{label} Sources section contains no source entries")
    if not _section(text, "## Identity And Version"):
        _fail(f"{label} Identity And Version section is empty")


def validate_source_text(text: str, label: str = "source record") -> None:
    """Validate one bibliography source-record body."""
    _ = _heading_positions(text, label)
    _validate_placeholders(text, label)
    _validate_dated_uncertainty(text, label)
    _validate_source_entries(text, label)


def _validate_records() -> int:
    records = _source_record_paths()
    if not records:
        _fail("bibliography contains no source records")
    for path in records:
        validate_source_text(path.read_text(encoding="utf-8"), _relative(path))
    return len(records)


def _validate_baseline() -> None:
    for relative in BASELINE_RECORDS:
        if not (BIBLIOGRAPHY_ROOT / relative).is_file():
            _fail(f"required bibliography baseline record missing: {relative}")
    ledger = (
        BIBLIOGRAPHY_ROOT
        / "provenance-and-methodology"
        / "repository"
        / "repository-source-verification.md"
    )
    text = ledger.read_text(encoding="utf-8")
    if BASELINE_COVERAGE_HEADING not in text:
        _fail("repository source ledger lacks baseline coverage report")


def validate_repository() -> BibliographyReport:
    """Validate bibliography topology, record schema, and baseline coverage.

    Returns:
        Stable coverage summary for the checked-in bibliography.

    """
    _validate_topology()
    count = _validate_records()
    _validate_baseline()
    return BibliographyReport(
        categories=CATEGORIES,
        record_count=count,
        required_baseline_count=len(BASELINE_RECORDS),
    )


def main() -> int:
    """Validate the bibliography and return process status.

    Returns:
        Zero for valid bibliography state and one for policy failure.

    """
    try:
        report = validate_repository()
    except (BibliographyValidationError, OSError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    message = "".join((
        f"bibliography valid: {report.record_count} records, ",
        f"{report.required_baseline_count} baseline records\n",
    ))
    _ = sys.stdout.write(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
