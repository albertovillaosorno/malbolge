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
#   - Exhaustive characterization of the frozen four-word learned holdout.
# - Must-Not:
#   - Alter the preregistered holdout selection or learned/static schedules.
# - Allows:
#   - Inputs: frozen holdout verifier and one known excluded positive extension.
#   - Outputs: no-solution characterization and verifier sanity assertions.
#   - Side effects: exhaustive bounded verifier calls only.
# - Split-When:
#   - A new learned-guidance holdout receives a new experiment identity.
# - Merge-When:
#   - One characterization suite owns this exact frozen holdout.
# - Summary:
#   - Retain the preregistered four-word holdout's zero-solution outcome.
# - Description:
#   - Distinguishes a null holdout from a verifier incapable of acceptance.
# - Usage:
#   - Run before interpreting learned-guidance comparative timing.
# - Defaults:
#   - The observed empty accepted set remains durable negative evidence.
#

"""Characterization evidence for the frozen learned-guidance holdout."""

from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

from algorithms.superoptimization import four_word_holdout as holdout

if TYPE_CHECKING:
    import pytest

_ROOT = Path(__file__).resolve().parents[5]
_EVIDENCE = _ROOT / (
    "benchmarks/research/evidence/"
    "2026-09-04-classic-four-word-learned-guidance-holdout-characterization"
)
_EMPTY_SHA256 = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)
_RAW_HEADER = "ordinal,raw_index,quality,source_hex\n"
_SOURCE_COMMIT = "4cd77739c3bbee222487ab54a34b421bef4881ee"
_KNOWN_POSITIVE_RAW_INDEX = 39_912_591
_KNOWN_POSITIVE_SOURCE = b"Q&%$"
_KNOWN_POSITIVE_QUALITY = 1


def test_retained_characterization_is_empty_and_source_pinned() -> None:
    """The raw accepted output remains the exact retained null observation."""
    assert (_EVIDENCE / "accepted.csv").read_text() == _RAW_HEADER
    source_commit = (_EVIDENCE / "source-commit.txt").read_text().strip()
    assert source_commit == _SOURCE_COMMIT
    assert sha256(b"").hexdigest() == _EMPTY_SHA256


def test_complete_holdout_has_no_verified_candidate() -> None:
    """All 100,000 preregistered candidates reject under exact verification."""
    accepted = tuple(
        candidate
        for candidate in range(holdout.HOLDOUT_CANDIDATE_COUNT)
        if holdout.verified_quality(candidate) is not None
    )
    assert accepted == ()


def test_verifier_accepts_known_excluded_positive_extension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Null holdout is not explained by a verifier unable to accept anything."""
    monkeypatch.setattr(
        holdout,
        "_SELECTED_RAW_INDICES",
        (_KNOWN_POSITIVE_RAW_INDEX,),
    )
    assert holdout.candidate_source(0) == _KNOWN_POSITIVE_SOURCE
    assert holdout.verified_quality(0) == _KNOWN_POSITIVE_QUALITY
