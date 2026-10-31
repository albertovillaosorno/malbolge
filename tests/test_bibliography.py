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

import os
from os import stat_result
from pathlib import Path
from stat import S_IFDIR, S_IFLNK
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import BinaryIO, Never

import pytest

from scripts.validate import bibliography as validator

ROOT = Path(__file__).resolve().parents[1]
C_RECORD = ROOT / "docs" / "bibliography" / "languages" / "c.md"
EXPECTED_RECORDS = 55
EXPECTED_BASELINE = 44
EXPECTED_VALIDATION_PACKAGES = 9
EXPECTED_DURABLE_REFERENCES = 21
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


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
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
