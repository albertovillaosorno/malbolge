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
#   - Regression tests for the research algorithm mirror contract.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Regression tests for the research algorithm mirror contract."""

from __future__ import annotations

import subprocess as sp  # ruff: ignore[suspicious-subprocess-import] - Git-only fixture.
from pathlib import Path

import pytest

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
    "superoptimization-research-program",
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
    assert validator.executable_research_ids(executable_ids) == frozenset(EXPECTED_IDS)
    assert frozenset({"diff", "doom"}) == validator.NON_RESEARCH_ALGORITHM_IDS


def test_unknown_executable_algorithm_still_fails_closed() -> None:
    """Do not silently classify unknown algorithm directories as product."""
    executable_ids = validator.executable_research_ids(
        frozenset((*EXPECTED_IDS, "diff", "doom", "mystery"))
    )
    _expect_id_failure(frozenset(EXPECTED_IDS), executable_ids)


@pytest.mark.parametrize(
    "redirect",
    ("research-file", "executable-readme", "document-directory", "test-directory"),
)
def test_mirror_rejects_redirected_evidence(
    redirect: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Outside aliases must not fulfill the physical research mirror contract."""
    documents = tmp_path / "docs/research/algorithms"
    document = documents / "fixture"
    executable = tmp_path / "src/research/algorithms/domain/algorithms/fixture"
    test_directory = tmp_path / "tests/function/algorithms/domain/fixture"
    for directory in (document, executable, test_directory):
        directory.mkdir(parents=True)
    for filename in ("README.md", "research.md"):
        _ = (document / filename).write_text("fixture", encoding="utf-8")
    for filename in ("README.md", "experiment.toml", "lifecycle.toml"):
        _ = (executable / filename).write_text("fixture", encoding="utf-8")
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "DOCUMENT_ROOT", documents)
    assert validator.validate_repository(_always_ignored) == ("fixture",)

    if redirect == "document-directory":
        victim = document
    elif redirect == "test-directory":
        victim = test_directory
    elif redirect == "research-file":
        victim = document / "research.md"
    else:
        victim = executable / "README.md"
    outside = tmp_path / "outside" / victim.name
    outside.parent.mkdir(exist_ok=True)
    _ = victim.rename(outside)
    victim.symlink_to(outside, target_is_directory=outside.is_dir())
    with pytest.raises(validator.ResearchMirrorError, match="redirect"):
        _ = validator.validate_repository(_always_ignored)


def test_mirror_rejects_directory_id_symlink(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A redirected research ID cannot enumerate as a direct physical ID."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    documents = tmp_path / "documents"
    documents.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (documents / "alias").symlink_to(outside, target_is_directory=True)
    with pytest.raises(validator.ResearchMirrorError, match="redirect"):
        _ = validator._directory_ids(documents)  # pyright: ignore[reportPrivateUsage]


def test_output_policy_checks_directory_not_just_one_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ignoring a single probe must not admit trackable research outputs."""
    _ = sp.run(
        ["git", "init", "--quiet", str(tmp_path)],
        check=True,
        capture_output=True,
        shell=False,
    )
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    executable = tmp_path / "algorithms" / "fixture"
    executable.mkdir(parents=True)
    entry = validator.MirrorEntry(
        document=tmp_path / "docs" / "fixture",
        executable=executable,
        research_id="fixture",
    )
    ignore_file = tmp_path / ".gitignore"

    _ = ignore_file.write_text("**/out/.mirror-probe\n", encoding="utf-8")
    assert not validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]

    _ = ignore_file.write_text("**/out/\n", encoding="utf-8")
    assert validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]

    _ = ignore_file.write_text("**/out/*.bin\n", encoding="utf-8")
    assert not validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]

    _ = ignore_file.write_text("**/out/*\n", encoding="utf-8")
    assert validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]
