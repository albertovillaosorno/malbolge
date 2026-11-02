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
#   - Regression tests for bibliography taxonomy and provenance validation.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Regression tests for bibliography taxonomy and provenance validation."""

from __future__ import annotations

import io
import os
import sys
from os import stat_result
from pathlib import Path
from stat import S_IFDIR, S_IFLNK
from typing import TYPE_CHECKING, Self, cast, override

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import BinaryIO, Never

import pytest

from scripts.validate import bibliography as validator

ROOT = Path(__file__).resolve().parents[1]
C_RECORD = ROOT / "docs" / "bibliography" / "languages" / "c.md"
EXPECTED_RECORDS = 55
EXPECTED_BASELINE = 44
EXPECTED_VALIDATION_PACKAGES = 9
EXPECTED_DURABLE_REFERENCES = 22
PYTEST_CACHE_DIRECTORY = ".pytest_cache"
MISSING_COVERAGE_MESSAGE = "lack bibliography coverage"
DUPLICATE_IDENTITY_MESSAGE = "duplicate stable identifier"
VALIDATION_REQUIREMENTS = ROOT / (
    "src/automation/repository/composition/scripts/bootstrap/"
    "python-validation-requirements.txt"
)


class _LinkedPath:
    @staticmethod
    def lstat() -> stat_result:
        return stat_result((S_IFLNK, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    @staticmethod
    def is_junction() -> bool:
        return False


class _JunctionPath:
    @staticmethod
    def lstat() -> stat_result:
        return stat_result((S_IFDIR, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    @staticmethod
    def is_junction() -> bool:
        return True


class _DeniedPath:
    @staticmethod
    def lstat() -> Never:
        message = "blocked entry"
        raise PermissionError(message)


def _expect_failure(text: str, message: str) -> None:
    try:
        validator.validate_source_text(text, "fixture")
    except validator.BibliographyValidationError as error:
        if message not in str(error):
            mismatch = f"unexpected bibliography validation error: {error}"
            raise AssertionError(mismatch) from error
        return
    failure = "invalid bibliography record unexpectedly succeeded"
    raise AssertionError(failure)


def _c_record() -> str:
    return C_RECORD.read_text(encoding="utf-8")


def _expect_requirements_failure(text: str, message: str) -> None:
    try:
        validator.validate_validation_requirements_text(text)
    except validator.BibliographyValidationError as error:
        if message not in str(error):
            mismatch = f"unexpected requirements validation error: {error}"
            raise AssertionError(mismatch) from error
        return
    failure = "invalid validation requirements unexpectedly succeeded"
    raise AssertionError(failure)


def test_repository_bibliography_taxonomy_and_baseline_are_valid() -> None:
    """Current bibliography satisfies taxonomy and baseline coverage."""
    report = validator.validate_repository()
    assert report.record_count == EXPECTED_RECORDS
    assert report.required_baseline_count == EXPECTED_BASELINE
    assert report.required_validation_package_count == EXPECTED_VALIDATION_PACKAGES
    assert report.covered_external_reference_count == EXPECTED_DURABLE_REFERENCES
    assert report.categories == validator.CATEGORIES


@pytest.mark.parametrize(
    "shadow_path",
    ("languages/template.md", "platforms-and-runtimes/compiler/template.md"),
)
def test_bibliography_rejects_nested_shadow_template(
    shadow_path: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A nested template is not an alternative to the sole canonical file."""
    root = tmp_path / "bibliography"
    canonical = root / "provenance-and-methodology" / "template.md"
    shadow = root / shadow_path
    canonical.parent.mkdir(parents=True)
    shadow.parent.mkdir(parents=True)
    _ = canonical.write_text("canonical", encoding="utf-8")
    _ = shadow.write_text("unreviewed second template", encoding="utf-8")
    monkeypatch.setattr(validator, "BIBLIOGRAPHY_ROOT", root)
    monkeypatch.setattr(validator, "CANONICAL_TEMPLATE", canonical)
    with pytest.raises(
        validator.BibliographyValidationError,
        match="duplicate bibliography template",
    ):
        validator._validate_templates()  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("with_adr_template", (False, True))
def test_bibliography_accepts_canonical_and_adr_templates(
    with_adr_template: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The source template and independent ADR template coexist without shadows."""
    root = tmp_path / "bibliography"
    canonical = root / "provenance-and-methodology" / "template.md"
    canonical.parent.mkdir(parents=True)
    _ = canonical.write_text("canonical", encoding="utf-8")
    if with_adr_template:
        adr = root / "adr" / "template.md"
        adr.parent.mkdir()
        _ = adr.write_text("ADR decision template", encoding="utf-8")
    monkeypatch.setattr(validator, "BIBLIOGRAPHY_ROOT", root)
    monkeypatch.setattr(validator, "CANONICAL_TEMPLATE", canonical)
    validator._validate_templates()  # pyright: ignore[reportPrivateUsage]


def test_llvm_banner_url_is_covered_by_existing_clang_tidy_identity() -> None:
    """The pinned LLVM version-banner literal needs its source identity record."""
    version_matcher = ROOT / (
        "src/automation/repository/composition/scripts/bootstrap/llvm_validation.py"
    )
    banner_uri = "http://llvm.org/"
    assert banner_uri in version_matcher.read_text(encoding="utf-8")
    record = ROOT / "docs/bibliography/tooling/clang-tidy.md"
    record_text = record.read_text(encoding="utf-8")
    source_urls = validator._urls_from_text(record_text)  # pyright: ignore[reportPrivateUsage]
    assert (
        validator.validate_external_reference_coverage((banner_uri,), source_urls) == 1
    )


@pytest.mark.parametrize("validator_name", ("source", "requirements", "identity"))
def test_bibliography_public_text_rejects_foreign_splitlines(
    validator_name: str,
) -> None:
    """A str subclass cannot substitute valid record or pinned package text."""

    class ForeignText(str):
        @override
        def splitlines(self, keepends: bool = False) -> list[str]:
            if validator_name == "requirements":
                return VALIDATION_REQUIREMENTS.read_text(encoding="utf-8").splitlines(
                    keepends
                )
            return _c_record().splitlines(keepends)

    invalid = ForeignText("not a valid source or pin set")
    failure = (
        "native source record entry" if validator_name == "identity" else "native text"
    )
    with pytest.raises(validator.BibliographyValidationError, match=failure):
        if validator_name == "source":
            validator.validate_source_text(invalid)
        elif validator_name == "requirements":
            validator.validate_validation_requirements_text(invalid)
        else:
            validator.validate_unique_stable_identifiers((("fixture", invalid),))


def test_source_record_requires_explicit_uncertainty() -> None:
    """Verified source records still state what remains unresolved."""
    text = _c_record().replace("### Unresolved", "### Limits", 1)
    _expect_failure(text, "lacks explicit unresolved/uncertainty evidence")


def test_source_record_rejects_unverified_template_status() -> None:
    """Source records cannot retain template verification status."""
    text = _c_record().replace(
        "Verified; evidence verified.",
        "Open; evidence unverified.",
        1,
    )
    _expect_failure(text, "retains unresolved template placeholder")


def test_source_record_requires_dated_provenance() -> None:
    """External evidence must retain a review or access date."""
    text = _c_record().replace("2026-07-26", "undated")
    text = text.replace("2026-08-08", "undated")
    text = text.replace("2026-08-09", "undated")
    _expect_failure(text, "lacks a dated retrieval/review provenance marker")


@pytest.mark.parametrize(
    "heading",
    (
        "## Status",
        "## Subject",
        "## Repository Use",
        "## Provenance",
        "## License Or Terms",
    ),
)
def test_source_record_requires_substantive_required_sections(heading: str) -> None:
    """Mandatory provenance sections cannot be blank despite present headings."""
    text = _c_record()
    start = text.index(heading) + len(heading)
    end = text.index("\n## ", start)
    text = text[:start] + "\n" + text[end:]
    _expect_failure(text, f"{heading.removeprefix('## ')} section is empty")


def test_source_record_requires_standalone_heading_lines() -> None:
    """An inline heading substring is not a real bibliography section."""
    text = _c_record().replace("## Subject", "Prose mentions ## Subject", 1)
    _expect_failure(text, "missing required heading: ## Subject")


@pytest.mark.parametrize(
    ("opening", "closing"),
    (
        ("```markdown", "```"),
        ("~~~~", "~~~~"),
        ("<!--", "-->"),
    ),
)
def test_source_record_rejects_hidden_required_heading(
    opening: str, closing: str
) -> None:
    """Code and comment text cannot masquerade as source-record sections."""
    text = _c_record().replace("## Subject", f"{opening}\n## Subject", 1)
    text = text.replace("## Repository Use", f"{closing}\n## Repository Use", 1)
    _expect_failure(text, "missing required heading: ## Subject")


@pytest.mark.parametrize(
    ("opening", "closing"),
    (("```", "```"), ("~~~", "~~~"), ("<!--", "-->")),
)
def test_source_record_rejects_hidden_uncertainty(opening: str, closing: str) -> None:
    """An uncertainty marker inside a literal block is not a heading."""
    text = _c_record().replace(
        "### Unresolved", f"{opening}\n### Unresolved\n{closing}", 1
    )
    _expect_failure(text, "lacks explicit unresolved/uncertainty evidence")


@pytest.mark.parametrize(
    ("opening", "closing"),
    (("```", "```"), ("~~~~", "~~~~"), ("<!--", "-->")),
)
def test_source_record_rejects_hidden_source_entry(opening: str, closing: str) -> None:
    """A quoted source bullet inside a literal block is not evidence."""
    text = _c_record().split("## Sources", 1)[0]
    text = text.replace("## Provenance", "## Provenance\n\nReviewed 2026-11-02", 1)
    text += f"## Sources\n\n{opening}\n- <https://example.com/evidence>\n{closing}\n"
    _expect_failure(text, "Sources section contains no source entries")


@pytest.mark.parametrize(
    ("opening", "closing"),
    (("```", "```"), ("~~~", "~~~"), ("<!--", "-->")),
)
def test_source_record_rejects_hidden_review_date(opening: str, closing: str) -> None:
    """Literal examples cannot stand in for source retrieval dates."""
    text = validator.DATE_PATTERN.sub("undated", _c_record())
    text = text.replace(
        "## Provenance", f"## Provenance\n\n{opening}\n2026-11-02\n{closing}", 1
    )
    _expect_failure(text, "lacks a dated retrieval/review provenance marker")


def test_source_record_rejects_indented_code_review_date() -> None:
    """An indented code example is not a dated review marker."""
    text = validator.DATE_PATTERN.sub("undated", _c_record())
    text = text.replace("## Provenance", "## Provenance\n\n    2026-11-02", 1)
    _expect_failure(text, "lacks a dated retrieval/review provenance marker")


def test_source_record_rejects_heading_after_inline_comment() -> None:
    """Removing a leading HTML comment cannot synthesize a Markdown heading."""
    text = _c_record().replace("## Subject", "<!-- example -->## Subject", 1)
    _expect_failure(text, "missing required heading: ## Subject")


def test_source_record_rejects_uncertainty_after_inline_comment() -> None:
    """The uncertainty marker needs its own Markdown heading line."""
    text = _c_record().replace("### Unresolved", "<!-- example -->### Unresolved", 1)
    _expect_failure(text, "lacks explicit unresolved/uncertainty evidence")


def test_source_record_rejects_source_bullet_after_inline_comment() -> None:
    """A bullet cannot be manufactured by deleting its line prefix."""
    text = _c_record().split("## Sources", 1)[0]
    text = text.replace("## Provenance", "## Provenance\n\nReviewed 2026-11-02", 1)
    text += "## Sources\n\n<!-- example -->- <https://example.com/hidden>\n"
    _expect_failure(text, "Sources section contains no source entries")


def test_source_record_rejects_indented_first_source_bullet() -> None:
    """Section trimming must not turn an indented line into a source entry."""
    text = _c_record().split("## Sources", 1)[0]
    text = text.replace("## Provenance", "## Provenance\n\nReviewed 2026-11-02", 1)
    text += "## Sources\n\n  - <https://example.com/indented>\n"
    _expect_failure(text, "Sources section contains no source entries")


def test_source_record_rejects_identifier_after_inline_comment() -> None:
    """A canonical identity must use a genuine list entry."""
    identifier = "- Stable identifier: ISO/IEC 9899:2024"
    text = _c_record().replace(identifier, "<!-- example -->" + identifier)
    with pytest.raises(
        validator.BibliographyValidationError,
        match="must declare exactly one stable identifier",
    ):
        validator.validate_unique_stable_identifiers((("fixture", text),))


def test_source_record_accepts_real_evidence_around_literal_examples() -> None:
    """Quoted Markdown examples cannot duplicate actual record headings."""
    text = _c_record().replace(
        "## Evidence",
        """## Evidence

````markdown
```
## Subject
## Sources
### Unresolved
- <https://example.com/fictional>
```
````

<!--
## Status
### Unresolved
-->
""",
        1,
    )
    validator.validate_source_text(text, "fixture")
    validator.validate_unique_stable_identifiers((("fixture", text),))


def test_hidden_stable_identifier_does_not_satisfy_source_identity() -> None:
    """A code sample cannot become the record's canonical stable ID."""
    identifier = "- Stable identifier: ISO/IEC 9899:2024"
    text = _c_record().replace(identifier, "- Alias: ISO/IEC 9899:2024")
    text = text.replace(
        "## Identity And Version",
        f"## Identity And Version\n\n```\n{identifier}\n```",
        1,
    )
    with pytest.raises(
        validator.BibliographyValidationError,
        match="must declare exactly one stable identifier",
    ):
        validator.validate_unique_stable_identifiers((("fixture", text),))


@pytest.mark.parametrize(
    "hidden",
    (
        "```\nhttps://invalid.example/hidden\n```",
        "~~~\nhttps://invalid.example/hidden\n~~~",
        "<!-- https://invalid.example/hidden -->",
    ),
)
def test_bibliography_hidden_links_cannot_claim_source_coverage(
    hidden: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Catalog coverage counts only public source URLs, not literal examples."""
    monkeypatch.setattr(validator, "_source_record_paths", lambda: (C_RECORD,))

    def hidden_record(_path: Path) -> str:
        return f"## Sources\n{hidden}\n"

    monkeypatch.setattr(validator, "_read_regular_text", hidden_record)
    assert validator._bibliography_source_urls() == ()  # pyright: ignore[reportPrivateUsage]


def test_source_record_rejects_repeated_required_heading() -> None:
    """A second required section cannot be hidden behind the first one."""
    text = _c_record().replace("## Sources", "## Sources\n## Sources", 1)
    _expect_failure(text, "duplicate required heading: ## Sources")


def test_source_record_rejects_impossible_provenance_date() -> None:
    """A date-shaped token must represent an actual calendar day."""
    text = _c_record()
    for value in ("2026-07-26", "2026-08-08", "2026-08-09"):
        text = text.replace(value, "2026-99-99")
    _expect_failure(text, "lacks a dated retrieval/review provenance marker")


def test_source_record_rejects_unrelated_version_date_as_provenance() -> None:
    """A version date cannot stand in for a source review or access date."""
    text = _c_record()
    for value in ("2026-07-26", "2026-08-08", "2026-08-09"):
        text = text.replace(value, "undated")
    text = text.replace(
        "## Identity And Version",
        "## Identity And Version\n\n- Software version: 2026-08-09",
        1,
    )
    _expect_failure(text, "lacks a dated retrieval/review provenance marker")


def test_source_record_requires_standalone_unresolved_heading() -> None:
    """An inline uncertainty mention is not a Markdown evidence heading."""
    text = _c_record().replace("### Unresolved", "Prose mentions ### Unresolved", 1)
    _expect_failure(text, "lacks explicit unresolved/uncertainty evidence")


def test_source_record_rejects_duplicate_unresolved_heading() -> None:
    """Uncertainty evidence must have one unambiguous section boundary."""
    text = _c_record().replace("### Unresolved", "### Unresolved\n### Unresolved", 1)
    _expect_failure(text, "lacks explicit unresolved/uncertainty evidence")


def test_source_record_requires_nonempty_sources() -> None:
    """Verified records require at least one source entry."""
    text = _c_record().replace(
        "- <https://www.iso.org/standard/82075.html> - accessed 2026-07-26.",
        "accessed 2026-07-26.",
        1,
    )
    wg14_source = "- <https://www9.open-std.org/"
    wg14_source += "JTC1/SC22/WG14/issues/c23/log.html> - accessed"
    text = text.replace(wg14_source, "accessed", 1)
    math_source = "- <https://www.open-std.org/"
    math_source += "jtc1/sc22/wg14/www/docs/dr_329.htm> - accessed"
    text = text.replace(math_source, "accessed", 1)
    draft_source = "- <https://www.open-std.org/"
    draft_source += "jtc1/sc22/wg14/www/docs/n3220.pdf> - accessed"
    text = text.replace(draft_source, "accessed", 1)
    _expect_failure(text, "Sources section contains no source entries")


def test_source_record_rejects_empty_source_bullet() -> None:
    """A source marker with no content cannot establish provenance."""
    text = _c_record().split("## Sources", 1)[0]
    text += "## Sources\n\n- \nNo source identity is listed.\n"
    text = text.replace("## Provenance", "## Provenance\n\nReviewed 2026-08-09.", 1)
    _expect_failure(text, "Sources section contains no source entries")


def test_source_record_heading_order_is_stable() -> None:
    """Provenance sections cannot silently move ahead of source identity."""
    text = _c_record().replace("## Subject", "## Temporary", 1)
    text = text.replace("## Provenance", "## Subject", 1)
    text = text.replace("## Temporary", "## Provenance", 1)
    _expect_failure(text, "bibliography headings are out of order")


def test_validation_requirements_have_exact_bibliography_coverage() -> None:
    """Every pinned validation package has one exact canonical record."""
    text = VALIDATION_REQUIREMENTS.read_text(encoding="utf-8")
    validator.validate_validation_requirements_text(text)


def test_validation_requirement_version_drift_fails_closed() -> None:
    """A dependency update requires the bibliography to move in one change."""
    text = VALIDATION_REQUIREMENTS.read_text(encoding="utf-8")
    text = text.replace("ruff==0.16.9", "ruff==0.17.0", 1)
    _expect_requirements_failure(
        text,
        "Python validation requirements mismatch canonical bibliography",
    )


def test_generated_pytest_cache_is_not_durable_evidence() -> None:
    """Pytest's generated cache cannot add bibliography obligations."""
    assert PYTEST_CACHE_DIRECTORY in validator.DURABLE_REFERENCE_EXCLUDED_PARTS


def test_redirected_bibliography_paths_fail_closed() -> None:
    """A symlink-like source entry cannot redirect durable evidence."""
    is_regular_file = cast(
        "Callable[[Path], bool]", vars(validator)["_is_regular_file"]
    )
    for redirected in (_LinkedPath(), _JunctionPath()):
        path = cast("Path", cast("object", redirected))
        with pytest.raises(
            validator.BibliographyValidationError,
            match="must not redirect",
        ):
            _ = is_regular_file(path)


def test_filesystem_status_errors_fail_closed() -> None:
    """File-type checks cannot hide inaccessible bibliography entries."""
    is_regular_file = cast(
        "Callable[[Path], bool]", vars(validator)["_is_regular_file"]
    )
    denied = cast("Path", cast("object", _DeniedPath()))
    with pytest.raises(
        validator.BibliographyValidationError,
        match="filesystem traversal failed",
    ):
        _ = is_regular_file(denied)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
@pytest.mark.parametrize(
    "operation", ("lstat", "junction", "resolve", "open", "fdopen", "fstat", "read")
)
def test_bibliography_evidence_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """Untrusted host file operations cannot escape bibliography admission."""
    source = tmp_path / "evidence.md"
    _ = source.write_text("bibliography evidence", encoding="utf-8")
    if operation == "lstat":
        original_lstat = Path.lstat

        def fail_lstat(path: Path) -> stat_result:
            if path == source:
                raise fault_type("injected evidence lstat fault")
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
    elif operation == "junction":
        original_junction = Path.is_junction

        def fail_junction(path: Path) -> bool:
            if path == source:
                raise fault_type("injected evidence junction fault")
            return original_junction(path)

        monkeypatch.setattr(Path, "is_junction", fail_junction)
    elif operation == "resolve":
        original_resolve = Path.resolve

        def fail_resolve(path: Path, *, strict: bool = False) -> Path:
            if path == source:
                raise fault_type("injected evidence resolution fault")
            return original_resolve(path, strict=strict)

        monkeypatch.setattr(Path, "resolve", fail_resolve)
    elif operation == "open":
        original_open = os.open

        def fail_open(path: Path, flags: int) -> int:
            if path == source:
                raise fault_type("injected evidence open fault")
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", fail_open)
    elif operation == "fdopen":

        def fail_fdopen(_descriptor: int, _mode: str) -> object:
            raise fault_type("injected evidence fdopen fault")

        monkeypatch.setattr(os, "fdopen", fail_fdopen)
    elif operation == "fstat":

        def fail_fstat(_descriptor: int) -> stat_result:
            raise fault_type("injected evidence fstat fault")

        monkeypatch.setattr(os, "fstat", fail_fstat)
    else:

        def fail_read(_stream: BinaryIO, _status: stat_result, _path: Path) -> bytes:
            raise fault_type("injected evidence read fault")

        monkeypatch.setattr(validator, "_read_open_evidence", fail_read)
    expected = (
        "filesystem traversal failed"
        if operation in {"lstat", "junction"}
        else "resolution failed"
        if operation == "resolve"
        else "read failed"
    )
    with pytest.raises(validator.BibliographyValidationError, match=expected):
        _ = validator._read_regular_text(source)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError])
def test_bibliography_fdopen_failure_releases_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A failed evidence stream wrapper must close its opened descriptor."""
    source = tmp_path / "evidence.md"
    _ = source.write_text("bibliography evidence", encoding="utf-8")
    original_open = os.open
    opened: list[int] = []

    def track_open(path: Path, flags: int) -> int:
        descriptor = original_open(path, flags)
        if path == source:
            opened.append(descriptor)
        return descriptor

    def fail_fdopen(_descriptor: int, _mode: str) -> object:
        raise fault_type("injected evidence fdopen fault")

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(os, "fdopen", fail_fdopen)
    with pytest.raises(validator.BibliographyValidationError, match="read failed"):
        _ = validator._read_regular_text(source)  # pyright: ignore[reportPrivateUsage]
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])


def test_filesystem_walk_errors_fail_closed() -> None:
    """Recursive scan failures cannot silently remove durable evidence."""
    handler = cast(
        "Callable[[OSError], Never]",
        vars(validator)["_raise_walk_error"],
    )
    error = PermissionError("blocked directory")
    with pytest.raises(
        validator.BibliographyValidationError,
        match="filesystem traversal failed",
    ) as caught:
        handler(error)
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("forgery", ["outside-root", "duplicate", "foreign-path"])
def test_bibliography_taxonomy_rejects_unbound_first_level_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    """A forged iterdir listing cannot manufacture the closed taxonomy."""
    root = tmp_path / "catalog"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    expected = (*validator.CATEGORIES, "adr")
    for name in expected:
        (outside / name).mkdir()
        (root / name).mkdir()

    class ForeignPath(type(root)):
        @property
        @override
        def name(self) -> str:
            raise AssertionError("foreign pathname property executed")

    original_iterdir = Path.iterdir

    def forged_iterdir(path: Path) -> Iterator[Path]:
        if path != root:
            yield from original_iterdir(path)
            return
        if forgery == "outside-root":
            yield from (outside / name for name in expected)
        elif forgery == "duplicate":
            yield from (root / name for name in expected)
            yield root / "languages"
        else:
            yield ForeignPath(root / "languages")

    monkeypatch.setattr(Path, "iterdir", forged_iterdir)
    monkeypatch.setattr(validator, "BIBLIOGRAPHY_ROOT", root)
    with pytest.raises(
        validator.BibliographyValidationError, match="bibliography.*taxonomy"
    ):
        validator._validate_first_level_taxonomy()  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("scanner", ["catalog", "durable"])
@pytest.mark.parametrize(
    "forgery",
    (
        "outside-root",
        "traversal-name",
        "duplicate-name",
        "foreign-name",
        "unannounced-child",
        "missing-child",
    ),
)
def test_bibliography_walk_rejects_unbound_discovery_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scanner: str,
    forgery: str,
) -> None:
    """A host walk cannot splice in foreign, repeated, or unvisited paths."""
    root = tmp_path / "catalog"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    class ForeignName(str):
        def __fspath__(self) -> str:
            raise AssertionError("foreign name conversion hook executed")

    def forged_walk(
        self: Path, *, on_error: Callable[[OSError], Never] | None = None
    ) -> Iterator[tuple[Path, list[str], list[str]]]:
        del on_error
        assert self == root
        if forgery == "outside-root":
            yield outside, [], ["foreign.md"]
        elif forgery == "traversal-name":
            yield root, [], ["../outside.md"]
        elif forgery == "duplicate-name":
            yield root, [], ["source.md", "source.md"]
        elif forgery == "foreign-name":
            yield root, [], [ForeignName("source.md")]
        elif forgery == "unannounced-child":
            yield root, [], []
            yield root / "phantom", [], ["source.md"]
        else:
            yield root, ["unvisited"], []

    monkeypatch.setattr(Path, "walk", forged_walk)
    with pytest.raises(
        validator.BibliographyValidationError, match="bibliography.*walk"
    ):
        if scanner == "catalog":
            _ = validator._walk_paths(root)  # pyright: ignore[reportPrivateUsage]
        else:
            monkeypatch.setattr(validator, "ROOT", root)
            _ = validator._durable_reference_paths()  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("side", ("references", "sources"))
def test_external_coverage_rejects_foreign_url_containers_before_iteration(
    side: str,
) -> None:
    """A custom iterator cannot manufacture source coverage or obligations."""

    class ForeignUrls(tuple[str, ...]):
        @override
        def __iter__(self) -> Never:
            raise AssertionError("untrusted URL iterator executed")

    foreign = ForeignUrls(("https://example.com/foreign",))
    references = foreign if side == "references" else ("https://example.com/real",)
    sources = foreign if side == "sources" else ("https://example.com/real",)
    with pytest.raises(validator.BibliographyValidationError, match="native URL tuple"):
        _ = validator.validate_external_reference_coverage(references, sources)


@pytest.mark.parametrize("side", ("references", "sources"))
def test_external_coverage_rejects_foreign_url_members_before_normalization(
    side: str,
) -> None:
    """A URL subclass cannot forge a covered identity via string methods."""

    class ForeignUrl(str):
        @override
        def rstrip(self, chars: str | None = None) -> str:
            del chars
            raise AssertionError("foreign URL normalization hook executed")

    foreign = ForeignUrl("https://example.com/foreign")
    references = (foreign,) if side == "references" else ("https://example.com/real",)
    sources = (foreign,) if side == "sources" else ("https://example.com/real",)
    with pytest.raises(validator.BibliographyValidationError, match="non-native URL"):
        _ = validator.validate_external_reference_coverage(references, sources)


@pytest.mark.parametrize("side", ("references", "sources"))
@pytest.mark.parametrize("foreign", (True, None, 0, [], "https://valid.example"))
def test_external_coverage_rejects_non_native_url_receipts(
    side: str, foreign: object
) -> None:
    """Coverage must have exact tuple and string receipts from each side."""
    if type(foreign) is str:
        references = foreign if side == "references" else ()
        sources = foreign if side == "sources" else ()
        expected = "native URL tuple"
    else:
        references = (foreign,) if side == "references" else ()
        sources = (foreign,) if side == "sources" else ()
        expected = "non-native URL"
    with pytest.raises(validator.BibliographyValidationError, match=expected):
        _ = validator.validate_external_reference_coverage(
            cast("tuple[str, ...]", references),
            cast("tuple[str, ...]", sources),
        )


def test_durable_external_reference_requires_canonical_coverage() -> None:
    """A new durable URL cannot bypass the canonical source inventory."""
    with pytest.raises(
        validator.BibliographyValidationError,
        match=MISSING_COVERAGE_MESSAGE,
    ):
        _ = validator.validate_external_reference_coverage(
            ("https://uncovered.example.invalid/source",),
            (),
        )


def test_git_transport_suffix_does_not_split_source_identity() -> None:
    """A Git transport suffix resolves to the canonical repository identity."""
    count = validator.validate_external_reference_coverage(
        ("https://github.com/id-Software/DOOM.git",),
        ("https://github.com/id-Software/DOOM",),
    )
    assert count == 1


def test_unique_identifiers_rejects_foreign_record_list_before_iteration() -> None:
    """A tuple subclass cannot suppress duplicate record identities."""

    class ForeignRecords(tuple[tuple[str, str], ...]):
        @override
        def __iter__(self) -> Never:
            raise AssertionError("foreign bibliography records iterator executed")

    records = ForeignRecords((("fixture", _c_record()),))
    with pytest.raises(
        validator.BibliographyValidationError, match="native source record tuple"
    ):
        validator.validate_unique_stable_identifiers(records)


@pytest.mark.parametrize("forgery", ("list-pair", "label-subclass", "short-pair"))
def test_unique_identifiers_rejects_foreign_pairs_and_labels(forgery: str) -> None:
    """Each admitted identity record has exactly two native string fields."""

    class ForeignLabel(str):
        @override
        def __format__(self, format_spec: str) -> str:
            del format_spec
            raise AssertionError("foreign record label formatter executed")

    if forgery == "list-pair":
        entry: object = ["fixture", _c_record()]
    elif forgery == "label-subclass":
        entry = (ForeignLabel("fixture"), _c_record())
    else:
        entry = ("fixture",)
    with pytest.raises(
        validator.BibliographyValidationError, match="native source record entry"
    ):
        validator.validate_unique_stable_identifiers(
            cast("tuple[tuple[str, str], ...]", (entry,))
        )


def test_duplicate_stable_source_identity_fails_closed() -> None:
    """Two records cannot claim the same canonical source identity."""
    text = _c_record()
    with pytest.raises(
        validator.BibliographyValidationError,
        match=DUPLICATE_IDENTITY_MESSAGE,
    ):
        validator.validate_unique_stable_identifiers(
            (
                ("first", text),
                ("second", text),
            )
        )


def test_source_record_rejects_link_after_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A post-discovery linked leaf cannot replace bibliography source bytes."""
    records = tmp_path / "records"
    records.mkdir()
    source = records / "c.md"
    original = _c_record()
    _ = source.write_text(original, encoding="utf-8")
    outside = tmp_path / "outside.md"
    _ = outside.write_text(original, encoding="utf-8")
    monkeypatch.setattr(validator, "BIBLIOGRAPHY_ROOT", records)

    def replaced_source_records() -> tuple[Path, ...]:
        assert source.is_file()
        source.unlink()
        source.symlink_to(outside)
        return (source,)

    monkeypatch.setattr(validator, "_source_record_paths", replaced_source_records)
    validate_records = cast("Callable[[], int]", vars(validator)["_validate_records"])
    with pytest.raises(
        validator.BibliographyValidationError,
        match=r"bibliography (paths must not redirect|evidence)",
    ):
        _ = validate_records()


def test_durable_reference_rejects_link_to_outside_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Outside symlink targets cannot contribute durable reference URLs."""
    outside = tmp_path / "outside.md"
    _ = outside.write_text("https://foreign.example.invalid/reference")
    link = tmp_path / "reference.md"
    link.symlink_to(outside)
    monkeypatch.setattr(validator, "_durable_reference_paths", lambda: (link,))
    scan = cast(
        "Callable[[], tuple[str, ...]]",
        vars(validator)["_durable_external_references"],
    )
    with pytest.raises(
        validator.BibliographyValidationError,
        match=r"bibliography (paths must not redirect|evidence)",
    ):
        _ = scan()


def test_source_record_rejects_linked_parent_after_discovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A redirected directory cannot supply source evidence after a scan."""
    category = tmp_path / "bibliography" / "languages"
    category.mkdir(parents=True)
    source = category / "c.md"
    _ = source.write_text(_c_record(), encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    _ = (outside / "c.md").write_text(_c_record(), encoding="utf-8")
    monkeypatch.setattr(validator, "BIBLIOGRAPHY_ROOT", category.parent)

    def swapped_parent_records() -> tuple[Path, ...]:
        assert source.is_file()
        source.unlink()
        category.rmdir()
        category.symlink_to(outside, target_is_directory=True)
        return (source,)

    monkeypatch.setattr(validator, "_source_record_paths", swapped_parent_records)
    validate_records = cast("Callable[[], int]", vars(validator)["_validate_records"])
    with pytest.raises(
        validator.BibliographyValidationError,
        match=r"bibliography (paths must not redirect|evidence)",
    ):
        _ = validate_records()


@pytest.mark.parametrize("phase", ["resolve", "read"])
@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_bibliography_host_faults_never_format_foreign_exceptions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
    fault_type: type[Exception],
) -> None:
    """Filesystem error subclasses remain typed without executing __str__."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign bibliography exception formatter executed")

    foreign = type(
        "ForeignBibliographyHostFault", (fault_type,), {"__str__": unsafe_str}
    )
    fault = foreign("unsafe filesystem detail")
    source = tmp_path / "evidence.md"
    _ = source.write_text("bibliography evidence", encoding="utf-8")
    if phase == "resolve":
        original_resolve = Path.resolve

        def fail_resolve(path: Path, *, strict: bool = False) -> Path:
            if path == source:
                raise fault
            return original_resolve(path, strict=strict)

        monkeypatch.setattr(Path, "resolve", fail_resolve)
    else:
        original_open = os.open

        def fail_open(path: Path, flags: int) -> int:
            if path == source:
                raise fault
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", fail_open)
    with pytest.raises(
        validator.BibliographyValidationError,
        match=f"evidence {'resolution' if phase == 'resolve' else 'read'} failed",
    ) as caught:
        _ = validator._read_regular_text(source)  # pyright: ignore[reportPrivateUsage]
    assert caught.value.__cause__ is fault


def test_bibliography_native_host_diagnostic_remains_actionable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exact built-in I/O error still exposes useful host detail."""
    source = tmp_path / "evidence.md"
    _ = source.write_text("bibliography evidence", encoding="utf-8")
    fault = OSError("native bibliography read unavailable")
    original_open = os.open

    def fail_open(path: Path, flags: int) -> int:
        if path == source:
            raise fault
        return original_open(path, flags)

    monkeypatch.setattr(os, "open", fail_open)
    with pytest.raises(
        validator.BibliographyValidationError,
        match="native bibliography read unavailable",
    ) as caught:
        _ = validator._read_regular_text(source)  # pyright: ignore[reportPrivateUsage]
    assert caught.value.__cause__ is fault


def test_bibliography_utf8_failure_preserves_decoder_cause(tmp_path: Path) -> None:
    """An invalid evidence encoding retains the native decoder error."""
    source = tmp_path / "invalid.md"
    _ = source.write_bytes(b"\xff")
    with pytest.raises(
        validator.BibliographyValidationError, match="invalid UTF-8"
    ) as caught:
        _ = validator._read_regular_text(source)  # pyright: ignore[reportPrivateUsage]
    assert type(caught.value.__cause__) is UnicodeDecodeError
    assert "position 0" in str(caught.value)


@pytest.mark.parametrize("fault_type", [OSError, validator.BibliographyValidationError])
def test_bibliography_cli_never_formats_foreign_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """Foreign host or policy failure formatting must not escape the CLI."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign bibliography CLI formatter executed")

    foreign = type(
        "ForeignBibliographyCliFault", (fault_type,), {"__str__": unsafe_str}
    )
    fault = foreign("untrusted detail")

    def fail_validate() -> None:
        raise fault

    monkeypatch.setattr(validator, "validate_repository", fail_validate)
    assert validator.main() == 1
    output = capsys.readouterr()
    assert "ForeignBibliographyCliFault" in output.err
    assert not output.out


@pytest.mark.parametrize(
    "fault_type",
    (AttributeError, IndexError, OverflowError, TypeError, ValueError, RuntimeError),
)
def test_bibliography_cli_contains_ordinary_dependency_failures(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """Unexpected host faults must still produce a nonzero operator status."""

    def fail_repository() -> Never:
        raise fault_type("unavailable bibliography dependency")

    monkeypatch.setattr(validator, "validate_repository", fail_repository)
    assert validator.main() == 1
    assert "error:" in capsys.readouterr().err


def test_bibliography_cli_never_formats_foreign_dependency_faults(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A foreign host exception cannot run its own diagnostic formatter."""

    class ForeignHostError(AttributeError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign diagnostic formatter executed")

    def fail_repository() -> Never:
        raise ForeignHostError("foreign dependency failure")

    monkeypatch.setattr(validator, "validate_repository", fail_repository)
    assert validator.main() == 1
    assert "ForeignHostError" in capsys.readouterr().err


@pytest.mark.parametrize("receipt", [None, True, False, -1, 0, "full"])
def test_bibliography_cli_rejects_unproven_stdout_delivery(
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """A short, foreign, or missing write count cannot report success."""

    class ForgedOutput(io.StringIO):
        @override
        def write(self, text: str) -> int:
            _ = super().write(text)
            return cast("int", receipt)

    report = validator.BibliographyReport(validator.CATEGORIES, 55, 44, 9, 21)
    monkeypatch.setattr(validator, "validate_repository", lambda: report)
    monkeypatch.setattr(sys, "stdout", ForgedOutput())
    errors = io.StringIO()
    monkeypatch.setattr(sys, "stderr", errors)
    assert validator.main() == 1
    assert "output write or flush failed" in errors.getvalue()


@pytest.mark.parametrize("completion", [False, 0, "done"])
def test_bibliography_cli_rejects_unproven_stdout_flush(
    monkeypatch: pytest.MonkeyPatch,
    completion: object,
) -> None:
    """Only a native successful flush permits a valid CLI verdict."""

    class ForgedOutput(io.StringIO):
        @override
        def flush(self) -> None:
            return cast("None", completion)

    report = validator.BibliographyReport(validator.CATEGORIES, 55, 44, 9, 21)
    monkeypatch.setattr(validator, "validate_repository", lambda: report)
    monkeypatch.setattr(sys, "stdout", ForgedOutput())
    assert validator.main() == 1


@pytest.mark.parametrize("stage", ["write", "flush"])
@pytest.mark.parametrize("fault_type", [OSError, ValueError, IndexError, OverflowError])
def test_bibliography_cli_preserves_failure_when_stderr_breaks(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    fault_type: type[Exception],
) -> None:
    """A failed diagnostic must not change a rejected bibliography verdict."""

    class FailedErrorOutput(io.StringIO):
        @override
        def write(self, text: str) -> int:
            if stage == "write":
                raise fault_type("unavailable stderr")
            return super().write(text)

        @override
        def flush(self) -> None:
            if stage == "flush":
                raise fault_type("unavailable stderr")
            return super().flush()

    def invalid_repository() -> Never:
        raise validator.BibliographyValidationError("invalid records")

    monkeypatch.setattr(validator, "validate_repository", invalid_repository)
    monkeypatch.setattr(sys, "stderr", FailedErrorOutput())
    assert validator.main() == 1


def test_bibliography_rejects_foreign_byte_receipt_before_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The evidence decoder cannot invoke untrusted bytes subclass hooks."""

    class ForeignBytes(bytes):
        @override
        def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
            del encoding, errors
            raise AssertionError("foreign bibliography byte decoder executed")

    def foreign_bytes(_path: Path) -> bytes:
        return ForeignBytes(b"valid")

    monkeypatch.setattr(validator, "_read_regular_bytes", foreign_bytes)
    with pytest.raises(
        validator.BibliographyValidationError, match="native byte receipt"
    ):
        _ = validator._read_regular_text(  # pyright: ignore[reportPrivateUsage]
            Path("untrusted.md")
        )


@pytest.mark.parametrize("phase", ["lstat", "opened", "after"])
def test_bibliography_rejects_foreign_stat_receipts_before_field_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    phase: str,
) -> None:
    """Host stat objects must not execute caller-owned property hooks."""
    source = tmp_path / "evidence.md"
    _ = source.write_bytes(b"evidence\n")

    class ForeignStat:
        @override
        def __getattribute__(self, name: str) -> object:
            del self, name
            raise AssertionError("foreign stat hook executed")

    if phase == "lstat":
        native_lstat = Path.lstat

        def forged_lstat(path: Path) -> stat_result:
            if path == source:
                return cast("stat_result", cast("object", ForeignStat()))
            return native_lstat(path)

        monkeypatch.setattr(Path, "lstat", forged_lstat)
    else:
        native_fstat = os.fstat
        observed = 0

        def forged_fstat(descriptor: int) -> stat_result:
            nonlocal observed
            observed += 1
            if (phase == "opened" and observed == 1) or (
                phase == "after" and observed == 2
            ):
                return cast("stat_result", cast("object", ForeignStat()))
            return native_fstat(descriptor)

        monkeypatch.setattr(os, "fstat", forged_fstat)

    with pytest.raises(
        validator.BibliographyValidationError, match="native stat receipt"
    ):
        _ = validator._read_regular_bytes(source)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("junction", [1, 0, "", object()])
def test_bibliography_rejects_nonboolean_junction_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    junction: object,
) -> None:
    """Junction decisions require native bool, not truthiness coercion."""
    source = tmp_path / "evidence.md"
    _ = source.write_bytes(b"evidence\n")
    native_junction = Path.is_junction

    def forged_junction(path: Path) -> bool:
        if path == source:
            return cast("bool", junction)
        return native_junction(path)

    monkeypatch.setattr(Path, "is_junction", forged_junction)
    with pytest.raises(
        validator.BibliographyValidationError, match="native junction receipt"
    ):
        _ = validator._read_regular_bytes(source)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("descriptor", [True, False, -1, 3.0])
def test_bibliography_rejects_foreign_open_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    descriptor: object,
) -> None:
    """An invalid open receipt cannot be wrapped or closed as an owned fd."""
    source = tmp_path / "evidence.md"
    _ = source.write_bytes(b"evidence\n")
    native_open = os.open

    def forged_open(path: Path, flags: int) -> int:
        if path == source:
            return cast("int", descriptor)
        return native_open(path, flags)

    monkeypatch.setattr(os, "open", forged_open)
    with pytest.raises(
        validator.BibliographyValidationError, match="native file descriptor"
    ):
        _ = validator._read_regular_bytes(source)  # pyright: ignore[reportPrivateUsage]


@pytest.fixture
def borrowed_streams() -> Iterator[list[BinaryIO]]:
    """Close only stream handles created by adversarial test fixtures."""
    opened: list[BinaryIO] = []
    yield opened
    for stream in reversed(opened):
        stream.close()


class _ForeignReadStream:
    """Delegate fd ownership but forge just the read receipt."""

    def __init__(self, wrapped: BinaryIO, receipt: object) -> None:
        self.wrapped: BinaryIO = wrapped
        self.receipt: object = receipt

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        del args
        self.wrapped.close()

    def fileno(self) -> int:
        return self.wrapped.fileno()

    def read(self, size: int) -> bytes:
        del size
        return cast("bytes", self.receipt)


def test_bibliography_rejects_forged_native_bytes_from_foreign_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, borrowed_streams: list[BinaryIO]
) -> None:
    """An fdopen stream cannot replace invalid disk bytes with valid evidence."""
    source = tmp_path / "evidence.md"
    expected = b"trusted provenance\n"
    _ = source.write_bytes(b"!" * len(expected))
    native_fdopen = os.fdopen

    def forged_fdopen(descriptor: int, mode: str) -> BinaryIO:
        wrapped = cast("BinaryIO", native_fdopen(os.dup(descriptor), mode))
        borrowed_streams.append(wrapped)
        return cast("BinaryIO", cast("object", _ForeignReadStream(wrapped, expected)))

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    with pytest.raises(validator.BibliographyValidationError, match="native stream"):
        _ = validator._read_regular_bytes(source)  # pyright: ignore[reportPrivateUsage]


def test_bibliography_rejects_native_buffer_with_foreign_raw_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, borrowed_streams: list[BinaryIO]
) -> None:
    """An exact buffered wrapper still needs a real raw file descriptor."""
    source = tmp_path / "evidence.md"
    forged = b"trusted provenance\n"
    _ = source.write_bytes(b"!" * len(forged))
    opened: list[int] = []

    class ForeignRaw(io.RawIOBase):
        def __init__(self, descriptor: int) -> None:
            super().__init__()
            self.descriptor: int = descriptor
            self.position: int = 0

        @override
        def readable(self) -> bool:
            return True

        @override
        def fileno(self) -> int:
            return self.descriptor

        @override
        def readinto(self, data: object) -> int:
            buffer = memoryview(cast("bytearray", data))
            size = min(len(buffer), len(forged) - self.position)
            buffer[:size] = forged[self.position : self.position + size]
            self.position += size
            return size

    def forged_fdopen(descriptor: int, _mode: str) -> BinaryIO:
        opened.append(descriptor)
        stream = cast("BinaryIO", io.BufferedReader(ForeignRaw(descriptor)))
        borrowed_streams.append(stream)
        return stream

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    with pytest.raises(validator.BibliographyValidationError, match="native stream"):
        _ = validator._read_regular_bytes(source)  # pyright: ignore[reportPrivateUsage]
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])


def test_bibliography_rejects_native_reader_of_unowned_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, borrowed_streams: list[BinaryIO]
) -> None:
    """A second native descriptor to the same inode is not the owned open fd."""
    source = tmp_path / "evidence.md"
    _ = source.write_bytes(b"evidence\n")
    native_fdopen = os.fdopen
    opened: list[int] = []

    def substituted_fdopen(descriptor: int, mode: str) -> BinaryIO:
        opened.append(descriptor)
        stream = cast("BinaryIO", native_fdopen(os.dup(descriptor), mode))
        borrowed_streams.append(stream)
        return stream

    monkeypatch.setattr(os, "fdopen", substituted_fdopen)
    with pytest.raises(validator.BibliographyValidationError, match="native stream"):
        _ = validator._read_regular_bytes(source)  # pyright: ignore[reportPrivateUsage]
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])


@pytest.mark.parametrize("receipt_kind", ["text", "subclass", "list"])
def test_bibliography_rejects_foreign_stream_receipt_before_inspection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    borrowed_streams: list[BinaryIO],
    receipt_kind: str,
) -> None:
    """Untrusted stream reads cannot provide provenance bytes."""
    source = tmp_path / "evidence.md"
    _ = source.write_bytes(b"evidence\n")
    native_fdopen = os.fdopen

    class ForeignBytes(bytes):
        @override
        def __len__(self) -> int:
            raise AssertionError("foreign byte length hook executed")

    receipts: dict[str, object] = {
        "text": "evidence\n",
        "subclass": ForeignBytes(b"evidence\n"),
        "list": list(b"evidence\n"),
    }

    def forged_fdopen(descriptor: int, mode: str) -> BinaryIO:
        stream = cast("BinaryIO", native_fdopen(os.dup(descriptor), mode))
        borrowed_streams.append(stream)
        return cast(
            "BinaryIO",
            cast("object", _ForeignReadStream(stream, receipts[receipt_kind])),
        )

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    with pytest.raises(
        validator.BibliographyValidationError, match="native stream receipt"
    ):
        _ = validator._read_regular_bytes(source)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("phase", ["opened", "after"])
@pytest.mark.parametrize("receipt", [True, -1, 2.0])
def test_bibliography_rejects_foreign_stream_descriptor_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    borrowed_streams: list[BinaryIO],
    phase: str,
    receipt: object,
) -> None:
    """A stream cannot use a forged fd during the before/after stat checks."""
    source = tmp_path / "evidence.md"
    _ = source.write_bytes(b"evidence\n")
    native_fdopen = os.fdopen

    class ForeignDescriptorStream(_ForeignReadStream):
        def __init__(self, stream: BinaryIO) -> None:
            super().__init__(stream, b"evidence\n")
            self.calls: int = 0

        @override
        def fileno(self) -> int:
            self.calls += 1
            if (phase == "opened" and self.calls == 1) or (
                phase == "after" and self.calls == 2
            ):
                return cast("int", receipt)
            return self.wrapped.fileno()

    def forged_fdopen(descriptor: int, mode: str) -> BinaryIO:
        stream = cast("BinaryIO", native_fdopen(os.dup(descriptor), mode))
        borrowed_streams.append(stream)
        return cast("BinaryIO", cast("object", ForeignDescriptorStream(stream)))

    monkeypatch.setattr(os, "fdopen", forged_fdopen)
    with pytest.raises(
        validator.BibliographyValidationError, match="native stream receipt"
    ):
        _ = validator._read_regular_bytes(source)  # pyright: ignore[reportPrivateUsage]
