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

from pathlib import Path

import pytest
from scripts.validate import bibliography as validator

ROOT = Path(__file__).resolve().parents[1]
C_RECORD = ROOT / "docs" / "bibliography" / "languages" / "c.md"
EXPECTED_RECORDS = 48
EXPECTED_BASELINE = 44
EXPECTED_VALIDATION_PACKAGES = 9
EXPECTED_DURABLE_REFERENCES = 19
MISSING_COVERAGE_MESSAGE = "lack bibliography coverage"
DUPLICATE_IDENTITY_MESSAGE = "duplicate stable identifier"
VALIDATION_REQUIREMENTS = ROOT / (
    "src/automation/repository/composition/scripts/bootstrap/"
    "python-validation-requirements.txt"
)


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
    assert (
        report.required_validation_package_count
        == EXPECTED_VALIDATION_PACKAGES
    )
    assert (
        report.covered_external_reference_count
        == EXPECTED_DURABLE_REFERENCES
    )
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
    text = text.replace("ruff==0.16.0", "ruff==0.16.1", 1)
    _expect_requirements_failure(
        text,
        "Python validation requirements mismatch canonical bibliography",
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


def test_duplicate_stable_source_identity_fails_closed() -> None:
    """Two records cannot claim the same canonical source identity."""
    text = _c_record()
    with pytest.raises(
        validator.BibliographyValidationError,
        match=DUPLICATE_IDENTITY_MESSAGE,
    ):
        validator.validate_unique_stable_identifiers((
            ("first", text),
            ("second", text),
        ))
