# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
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


def test_product_algorithm_surface_is_outside_research_roots() -> None:
    """Keep product interoperability algorithms outside the research mirror."""
    assert validator.DOCUMENT_ROOT.name == ALGORITHMS_DIRECTORY
    assert validator.EXECUTABLE_ROOT == validator.ROOT / ALGORITHMS_DIRECTORY
    assert (
        validator.EXECUTABLE_ROOT != validator.ROOT / "interop" / "algorithms"
    )
