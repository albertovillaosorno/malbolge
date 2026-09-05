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
#   - Completion evidence for the bounded superoptimization technique matrix.
# - Must-Not:
#   - Rerun benchmarks, invent missing results, or grant product authority.
# - Allows:
#   - Inputs: retained technique summary and source-pinned evidence directories.
#   - Outputs: exact coverage, artifact-shape, and no-promotion assertions.
#   - Side effects: repository-local evidence reads only.
# - Split-When:
#   - A later research milestone gains a distinct comparative conclusion.
# - Merge-When:
#   - One completion test owns this exact bounded technique matrix.
# - Summary:
#   - Prove every acceptance-required technique has durable retained evidence.
# - Description:
#   - Locks six comparisons and preserves positive, negative, and null results.
# - Usage:
#   - Run before archiving the superoptimization research TODO.
# - Defaults:
#   - No technique is promoted to product architecture by this record.
#

"""Completion checks for the superoptimization comparative conclusion."""

from pathlib import Path
import tomllib
from typing import cast

_ROOT = Path(__file__).resolve().parents[5]
_SUMMARY = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "superoptimization-research-program/comparative-conclusion.toml"
)
_REQUIRED = {
    "decomposition",
    "verified-block-reuse",
    "canonicalization",
    "exact-pruning",
    "heuristic-search",
    "learned-guidance",
}
_COMPLETE = "complete"
_NO_PROMOTION = "none"
_RESEARCH_ONLY = "retain-research-only"
_REQUIRED_EVIDENCE_FILES = (
    "README.md",
    "benchmark.toml",
    "experiment.toml",
    "raw.csv",
    "source-commit.txt",
)


def _document() -> dict[str, object]:
    return cast(
        "dict[str, object]",
        tomllib.loads(_SUMMARY.read_text(encoding="utf-8")),
    )


def test_comparative_conclusion_covers_every_required_technique() -> None:
    """The bounded milestone compares all six acceptance-required techniques."""
    rows = cast("list[dict[str, object]]", _document()["techniques"])
    assert {str(row["id"]) for row in rows} == _REQUIRED
    assert len(rows) == len(_REQUIRED)


def test_every_comparison_resolves_to_complete_retained_evidence() -> None:
    """Each technique points to durable source-pinned raw evidence."""
    rows = cast("list[dict[str, object]]", _document()["techniques"])
    for row in rows:
        evidence = _ROOT / str(row["evidence"])
        assert evidence.is_dir()
        assert all(
            (evidence / name).is_file()
            for name in _REQUIRED_EVIDENCE_FILES
        )


def test_comparative_conclusion_grants_no_product_promotion() -> None:
    """Mixed research evidence cannot silently become product policy."""
    document = _document()
    conclusion = cast("dict[str, object]", document["conclusion"])
    rows = cast("list[dict[str, object]]", document["techniques"])
    assert conclusion["status"] == _COMPLETE
    assert conclusion["product_promotion"] == _NO_PROMOTION
    assert all(row["decision"] == _RESEARCH_ONLY for row in rows)
