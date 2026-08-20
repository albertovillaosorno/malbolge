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

"""Validate bibliography taxonomy and source-record provenance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from stat import S_ISDIR
from stat import S_ISLNK
from stat import S_ISREG
import sys
from typing import Never
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from urllib.parse import urlunsplit

if TYPE_CHECKING:
    from os import stat_result

from scripts.repository_root import repository_root

ROOT = repository_root(Path(__file__))
BIBLIOGRAPHY_ROOT = ROOT / "docs" / "bibliography"
VALIDATION_REQUIREMENTS_FILE = ROOT / (
    "src/automation/repository/composition/scripts/bootstrap/"
    "python-validation-requirements.txt"
)
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
    "languages/python.md",
    "languages/rust.md",
    "libraries/colorama.md",
    "libraries/iniconfig.md",
    "libraries/nodejs-wheel-binaries.md",
    "libraries/packaging.md",
    "libraries/pluggy.md",
    "libraries/pygments.md",
    "platforms-and-runtimes/aarch64.md",
    "platforms-and-runtimes/nodejs-24-16-0.md",
    "platforms-and-runtimes/rust-toolchain-1-97-1.md",
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
    "tooling/basedpyright.md",
    "tooling/clang-tidy.md",
    "tooling/git.md",
    "tooling/latex.md",
    "tooling/uv.md",
    "tooling/pytest.md",
    "tooling/ruff.md",
    "organizations-and-projects/andrew-cooke-malbolge.md",
    "organizations-and-projects/github-linguist.md",
    "organizations-and-projects/internet-archive-wayback-machine.md",
    "organizations-and-projects/nagoya-malbolge-project.md",
    "organizations-and-projects/ninety-nine-bottles-of-beer.md",
    "specifications-and-standards/json-schema-store.md",
    "tooling/cspell.md",
    "tooling/markdownlint-cli2.md",
    "tooling/textmate-language-grammar.md",
)
VALIDATION_REQUIREMENT_RECORDS = (
    ("basedpyright==1.39.9", "tooling/basedpyright.md"),
    ("colorama==0.4.6", "libraries/colorama.md"),
    ("iniconfig==2.3.0", "libraries/iniconfig.md"),
    (
        "nodejs-wheel-binaries==24.16.0",
        "libraries/nodejs-wheel-binaries.md",
    ),
    ("packaging==26.2", "libraries/packaging.md"),
    ("pluggy==1.6.0", "libraries/pluggy.md"),
    ("Pygments==2.20.0", "libraries/pygments.md"),
    ("pytest==9.1.1", "tooling/pytest.md"),
    ("ruff==0.16.0", "tooling/ruff.md"),
)
URL_PATTERN = re.compile(r"https?://[^\s<>\"'`]+")
DURABLE_REFERENCE_SUFFIXES = frozenset((
    ".c",
    ".cff",
    ".cmd",
    ".h",
    ".json",
    ".jsonc",
    ".md",
    ".mdc",
    ".py",
    ".rs",
    ".sh",
    ".toml",
    ".yaml",
    ".yml",
))
DURABLE_REFERENCE_EXCLUDED_PARTS = frozenset((
    ".cache",
    ".dependencies",
    ".git",
    ".pytest_cache",
    ".logs",
    ".temp",
    "target",
))
DURABLE_REFERENCE_EXCLUDED_PREFIXES = (
    "docs/bibliography/",
    "docs/todo/open/",
    "tests/",
)
SELF_OWNED_URLS = frozenset(("https://github.com/albertovillaosorno/malbolge",))
DATE_PATTERN = re.compile(r"20\d{2}-\d{2}-\d{2}")
PLACEHOLDERS = (
    "{required}",
    "Open; evidence unverified.",
)
ADR_DIR = "adr"
UNRESOLVED_HEADING = "### Unresolved"
BASELINE_COVERAGE_HEADING = "### Baseline Coverage"
SPECIAL_FILES = frozenset({"README.md", "disclaimer.md", "template.md"})
SOURCE_RECORD_SUFFIX = ".md"


class BibliographyValidationError(ValueError):
    """Bibliography topology or source provenance violates the contract."""


@dataclass(frozen=True, slots=True)
class BibliographyReport:
    """Validated bibliography coverage summary."""

    categories: tuple[str, ...]
    record_count: int
    required_baseline_count: int
    required_validation_package_count: int
    covered_external_reference_count: int


def _fail(message: str) -> Never:
    raise BibliographyValidationError(message)


def _relative(path: Path) -> str:
    return path.relative_to(BIBLIOGRAPHY_ROOT).as_posix()


def _raise_walk_error(error: OSError) -> Never:
    _ = error
    _fail("bibliography filesystem traversal failed")


def _path_status(path: Path) -> stat_result | None:
    try:
        status = path.lstat()
    except FileNotFoundError:
        return None
    except OSError:
        _fail("bibliography filesystem traversal failed")
    if S_ISLNK(status.st_mode) or path.is_junction():
        _fail("bibliography paths must not redirect")
    return status


def _is_regular_file(path: Path) -> bool:
    status = _path_status(path)
    return status is not None and S_ISREG(status.st_mode)


def _is_directory(path: Path) -> bool:
    status = _path_status(path)
    return status is not None and S_ISDIR(status.st_mode)


def _path_exists(path: Path) -> bool:
    return _path_status(path) is not None


def _walk_paths(root: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for directory, directories, filenames in root.walk(
        on_error=_raise_walk_error
    ):
        paths.extend(directory / name for name in directories)
        paths.extend(directory / name for name in filenames)
    return tuple(paths)


def _source_record_paths() -> tuple[Path, ...]:
    records: list[Path] = []
    for path in _walk_paths(BIBLIOGRAPHY_ROOT):
        if path.suffix != SOURCE_RECORD_SUFFIX or not _is_regular_file(path):
            continue
        relative = path.relative_to(BIBLIOGRAPHY_ROOT)
        if path.name in SPECIAL_FILES or ADR_DIR in relative.parts:
            continue
        records.append(path)
    return tuple(sorted(records))


def _validate_first_level_taxonomy() -> None:
    expected = frozenset((*CATEGORIES, ADR_DIR))
    actual = frozenset(
        path.name for path in BIBLIOGRAPHY_ROOT.iterdir() if _is_directory(path)
    )
    if actual != expected:
        _fail(f"bibliography first-level taxonomy mismatch: {sorted(actual)}")


def _validate_directory_catalogs() -> None:
    directories = (
        BIBLIOGRAPHY_ROOT,
        *sorted(
            path
            for path in _walk_paths(BIBLIOGRAPHY_ROOT)
            if _is_directory(path)
        ),
    )
    for directory in directories:
        if not _is_regular_file(directory / "README.md"):
            relative = _relative(directory)
            _fail(f"bibliography directory lacks README.md: {relative}")


def _validate_templates() -> None:
    if not _is_regular_file(CANONICAL_TEMPLATE):
        _fail("canonical bibliography source template is missing")
    if _path_exists(BIBLIOGRAPHY_ROOT / "template.md"):
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


def _stable_identifier(text: str, label: str) -> str:
    section = _section(text, "## Identity And Version")
    prefix = "- Stable identifier: "
    identifiers = tuple(
        line.removeprefix(prefix).strip()
        for line in section.splitlines()
        if line.startswith(prefix)
    )
    if len(identifiers) != 1 or not identifiers[0]:
        _fail(f"{label} must declare exactly one stable identifier")
    return identifiers[0]


def validate_unique_stable_identifiers(
    records: tuple[tuple[str, str], ...],
) -> None:
    """Reject duplicate canonical source identities across records."""
    seen: dict[str, str] = {}
    for label, text in records:
        identifier = _stable_identifier(text, label)
        previous = seen.get(identifier)
        if previous is not None:
            _fail(
                "".join((
                    f"duplicate stable identifier {identifier!r}: ",
                    f"{previous} and {label}",
                ))
            )
        seen[identifier] = label


def _validate_records() -> int:
    paths = _source_record_paths()
    if not paths:
        _fail("bibliography contains no source records")
    records = tuple(
        (_relative(path), path.read_text(encoding="utf-8")) for path in paths
    )
    for label, text in records:
        validate_source_text(text, label)
    validate_unique_stable_identifiers(records)
    return len(records)


def _validate_baseline() -> None:
    for relative in BASELINE_RECORDS:
        if not _is_regular_file(BIBLIOGRAPHY_ROOT / relative):
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


def validate_validation_requirements_text(text: str) -> None:
    """Validate the exact pinned Python validation dependency set."""
    actual = tuple(line.strip() for line in text.splitlines() if line.strip())
    expected = tuple(
        requirement for requirement, _record in VALIDATION_REQUIREMENT_RECORDS
    )
    if actual != expected:
        _fail(
            "".join((
                (
                    "Python validation requirements mismatch canonical "
                    "bibliography coverage: "
                ),
                f"{actual}",
            ))
        )


def _validate_validation_requirements() -> None:
    requirements_text = VALIDATION_REQUIREMENTS_FILE.read_text(encoding="utf-8")
    validate_validation_requirements_text(requirements_text)
    for requirement, relative in VALIDATION_REQUIREMENT_RECORDS:
        path = BIBLIOGRAPHY_ROOT / relative
        if not _is_regular_file(path):
            _fail(
                "".join((
                    "validation dependency lacks bibliography record: ",
                    f"{requirement} -> {relative}",
                ))
            )
        record = path.read_text(encoding="utf-8")
        if f"`{requirement}`" not in record:
            _fail(
                "".join((
                    "validation dependency record lacks exact pin: ",
                    f"{requirement} -> {relative}",
                ))
            )


def _normalized_url(value: str) -> str:
    cleaned = value.rstrip(".,;:)]}")
    parts = urlsplit(cleaned)
    path = parts.path.rstrip("/").removesuffix(".git")
    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        path,
        parts.query,
        "",
    ))


def _urls_from_text(text: str) -> tuple[str, ...]:
    return tuple(
        _normalized_url(match.group(0)) for match in URL_PATTERN.finditer(text)
    )


def validate_external_reference_coverage(
    references: tuple[str, ...],
    source_urls: tuple[str, ...],
) -> int:
    """Reject durable external references without a canonical source record.

    Returns:
        Count of distinct covered external references.

    """
    normalized_sources = frozenset(_normalized_url(url) for url in source_urls)
    self_owned = frozenset(_normalized_url(url) for url in SELF_OWNED_URLS)
    normalized_references = (
        frozenset(_normalized_url(url) for url in references) - self_owned
    )
    missing = tuple(sorted(normalized_references - normalized_sources))
    if missing:
        _fail(
            "".join((
                "durable external references lack bibliography coverage: ",
                f"{missing}",
            ))
        )
    return len(normalized_references)


def _is_excluded_relative_path(relative: Path) -> bool:
    if any(part in DURABLE_REFERENCE_EXCLUDED_PARTS for part in relative.parts):
        return True
    value = relative.as_posix()
    return any(
        value == prefix.removesuffix("/") or value.startswith(prefix)
        for prefix in DURABLE_REFERENCE_EXCLUDED_PREFIXES
    )


def _is_durable_reference_path(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return (
        not _is_excluded_relative_path(relative)
        and path.suffix in DURABLE_REFERENCE_SUFFIXES
    )


def _durable_reference_paths() -> tuple[Path, ...]:
    paths: list[Path] = []
    for directory, directories, filenames in ROOT.walk(
        on_error=_raise_walk_error
    ):
        directories[:] = [
            name
            for name in directories
            if not _is_excluded_relative_path(
                (directory / name).relative_to(ROOT)
            )
        ]
        paths.extend(
            path
            for name in filenames
            if _is_durable_reference_path(path := directory / name)
        )
    return tuple(sorted(paths))


def _durable_external_references() -> tuple[str, ...]:
    references: set[str] = set()
    for path in _durable_reference_paths():
        references.update(_urls_from_text(path.read_text(encoding="utf-8")))
    return tuple(sorted(references))


def _bibliography_source_urls() -> tuple[str, ...]:
    urls: set[str] = set()
    for path in _source_record_paths():
        urls.update(_urls_from_text(path.read_text(encoding="utf-8")))
    return tuple(sorted(urls))


def _validate_external_references() -> int:
    return validate_external_reference_coverage(
        _durable_external_references(),
        _bibliography_source_urls(),
    )


def validate_repository() -> BibliographyReport:
    """Validate bibliography topology, record schema, and baseline coverage.

    Returns:
        Stable coverage summary for the checked-in bibliography.

    """
    _validate_topology()
    count = _validate_records()
    _validate_baseline()
    _validate_validation_requirements()
    covered_external_reference_count = _validate_external_references()
    return BibliographyReport(
        categories=CATEGORIES,
        record_count=count,
        required_baseline_count=len(BASELINE_RECORDS),
        required_validation_package_count=len(VALIDATION_REQUIREMENT_RECORDS),
        covered_external_reference_count=covered_external_reference_count,
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
        f"{report.required_baseline_count} baseline records, ",
        f"{report.required_validation_package_count} validation packages, ",
        f"{report.covered_external_reference_count} durable references\n",
    ))
    _ = sys.stdout.write(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
