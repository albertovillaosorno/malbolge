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

from scripts.validate import bibliography as validator

ROOT = Path(__file__).resolve().parents[1]
C_RECORD = ROOT / "docs" / "bibliography" / "languages" / "c.md"
EXPECTED_RECORDS = 24
EXPECTED_BASELINE = 22


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


def test_repository_bibliography_taxonomy_and_baseline_are_valid() -> None:
    """Current bibliography satisfies taxonomy and baseline coverage."""
    report = validator.validate_repository()
    assert report.record_count == EXPECTED_RECORDS
    assert report.required_baseline_count == EXPECTED_BASELINE
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
    _expect_failure(text, "lacks a dated retrieval/review provenance marker")


def test_source_record_requires_nonempty_sources() -> None:
    """Verified records require at least one source entry."""
    text = _c_record().replace(
        "- <https://www.iso.org/standard/82075.html> - accessed 2026-07-26.",
        "accessed 2026-07-26.",
        1,
    )
    _expect_failure(text, "Sources section contains no source entries")


def test_source_record_heading_order_is_stable() -> None:
    """Provenance sections cannot silently move ahead of source identity."""
    text = _c_record().replace("## Subject", "## Temporary", 1)
    text = text.replace("## Provenance", "## Subject", 1)
    text = text.replace("## Temporary", "## Provenance", 1)
    _expect_failure(text, "bibliography headings are out of order")
