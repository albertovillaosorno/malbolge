# File:
#   - test_research_mirror.py
# Path:
#   - tests/test_research_mirror.py
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
#   - Regression tests for the research algorithm mirror contract.
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

"""Regression tests for the research algorithm mirror contract."""

from __future__ import annotations

from scripts.validate import research_mirror as validator

ALGORITHMS_DIRECTORY = "algorithms"
EXPECTED_IDS = (
    "adaptive-accelerator-resource-budgeting",
    "compact-guest-bytecode-strategy",
    "malbolge-specific-optimization-mathematics",
    "pytorch-search-orchestration",
    "search-pruning-and-state-canonicalization",
    "self-modification-state-graph-optimizer",
    "stochastic-and-guided-search",
    "template",
)


def _always_ignored(entry: validator.MirrorEntry) -> bool:
    return bool(entry.research_id)


def _expect_id_failure(
    document_ids: frozenset[str],
    executable_ids: frozenset[str],
) -> None:
    try:
        _ = validator.validate_id_sets(document_ids, executable_ids)
    except validator.ResearchMirrorError:
        return
    message = "research mirror ID mismatch unexpectedly succeeded"
    raise AssertionError(message)


def test_repository_research_mirror_is_complete() -> None:
    """Every current research ID satisfies both halves and ignored output."""
    assert validator.validate_repository(_always_ignored) == EXPECTED_IDS


def test_document_only_research_id_fails_closed() -> None:
    """Reject a documentation-only algorithm without executable research."""
    _expect_id_failure(
        frozenset({"alpha", "beta"}),
        frozenset({"alpha"}),
    )


def test_executable_only_research_id_fails_closed() -> None:
    """Executable research without its academic record is rejected."""
    _expect_id_failure(
        frozenset({"alpha"}),
        frozenset({"alpha", "beta"}),
    )


def test_empty_research_mirror_fails_closed() -> None:
    """Deleting both halves cannot turn the mirror contract into a no-op."""
    _expect_id_failure(frozenset(), frozenset())


def test_non_research_algorithm_suites_are_explicitly_excluded() -> None:
    """Keep reusable/product suites in algorithms without academic mirroring."""
    executable_ids = frozenset((*EXPECTED_IDS, "diff", "doom"))
    assert validator.executable_research_ids(executable_ids) == frozenset(
        EXPECTED_IDS
    )
    assert frozenset({"diff", "doom"}) == validator.NON_RESEARCH_ALGORITHM_IDS


def test_unknown_executable_algorithm_still_fails_closed() -> None:
    """Do not silently classify unknown algorithm directories as product."""
    executable_ids = validator.executable_research_ids(
        frozenset((*EXPECTED_IDS, "diff", "doom", "mystery"))
    )
    _expect_id_failure(frozenset(EXPECTED_IDS), executable_ids)
