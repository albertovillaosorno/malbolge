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

import os
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import] - Git-only fixture.
from collections.abc import Iterator
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


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError])
@pytest.mark.parametrize(
    "operation", ("leaf_lstat", "leaf_junction", "parent_lstat", "parent_junction")
)
def test_mirror_physical_path_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """Malformed path-inspection errors cannot escape the physical contract."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    directory = tmp_path / "documents"
    directory.mkdir()
    evidence = directory / "research.md"
    _ = evidence.write_text("fixture", encoding="utf-8")
    target = directory if operation.startswith("parent_") else evidence
    if operation.endswith("lstat"):
        real_lstat = Path.lstat

        def fail_lstat(path: Path) -> os.stat_result:
            if path == target:
                raise fault_type("injected mirror lstat fault")
            return real_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
    else:
        real_junction = Path.is_junction

        def fail_junction(path: Path) -> bool:
            if path == target:
                raise fault_type("injected mirror junction fault")
            return real_junction(path)

        monkeypatch.setattr(Path, "is_junction", fail_junction)
    with pytest.raises(validator.ResearchMirrorError, match="status failed"):
        _ = validator._physical_status(  # pyright: ignore[reportPrivateUsage]
            evidence, "research evidence"
        )


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
@pytest.mark.parametrize("operation", ("id_lstat", "id_junction", "iterdir"))
def test_mirror_directory_discovery_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """A failed ID scan cannot pretend to enumerate the research mirror."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    documents = tmp_path / "documents"
    documents.mkdir()
    child = documents / "fixture"
    child.mkdir()
    if operation == "id_lstat":
        real_lstat = Path.lstat

        def fail_lstat(path: Path) -> os.stat_result:
            if path == child:
                raise fault_type("injected mirror ID status fault")
            return real_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
    elif operation == "id_junction":
        real_junction = Path.is_junction

        def fail_junction(path: Path) -> bool:
            if path == child:
                raise fault_type("injected mirror ID junction fault")
            return real_junction(path)

        monkeypatch.setattr(Path, "is_junction", fail_junction)
    else:
        real_iterdir = Path.iterdir

        def fail_iterdir(path: Path) -> Iterator[Path]:
            if path == documents:
                raise fault_type("injected mirror directory scan fault")
            return real_iterdir(path)

        monkeypatch.setattr(Path, "iterdir", fail_iterdir)
    expected = "scan failed" if operation == "iterdir" else "ID status failed"
    with pytest.raises(validator.ResearchMirrorError, match=expected):
        _ = validator._directory_ids(documents)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_mirror_shared_layout_failure_is_typed(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Shared layout enumeration errors stay within the mirror error model."""

    def fail_layout(_root: Path) -> tuple[tuple[str, Path], ...]:
        raise fault_type("injected shared layout failure")

    monkeypatch.setattr(validator, "research_algorithm_directories", fail_layout)
    with pytest.raises(validator.ResearchMirrorError, match="discovery failed"):
        _ = validator.validate_repository(_always_ignored)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_mirror_git_output_probe_failure_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A failed Git ignore probe is a typed research policy rejection."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    entry = validator.MirrorEntry(
        document=tmp_path / "docs" / "fixture",
        executable=tmp_path / "algorithms" / "fixture",
        research_id="fixture",
    )

    def fail_git(*_args: object, **_kwargs: object) -> sp.CompletedProcess[str]:
        raise fault_type("injected Git ignore failure")

    monkeypatch.setattr(sp, "run", fail_git)
    with pytest.raises(validator.ResearchMirrorError, match="Git ignore probe failed"):
        _ = validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]


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


@pytest.mark.parametrize("boundary", ["physical", "scan", "id", "discovery", "git"])
@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_mirror_foreign_host_error_formatters_cannot_escape(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    boundary: str,
    fault_type: type[Exception],
) -> None:
    """Host exceptions retain typed causes without caller-owned formatting."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("research mirror foreign exception formatting executed")

    foreign = type("ForeignResearchMirrorFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("dangerous exception text")
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    if boundary in {"physical", "scan", "id"}:
        directory = tmp_path / "documents"
        directory.mkdir()
        child = directory / "fixture"
        _ = child.write_text("fixture", encoding="utf-8")
        original_lstat = Path.lstat
        original_iterdir = Path.iterdir
        if boundary in {"physical", "id"}:

            def fail_lstat(path: Path) -> os.stat_result:
                if path == child:
                    raise fault
                return original_lstat(path)

            monkeypatch.setattr(Path, "lstat", fail_lstat)
        else:

            def fail_iterdir(path: Path) -> Iterator[Path]:
                if path == directory:
                    raise fault
                return original_iterdir(path)

            monkeypatch.setattr(Path, "iterdir", fail_iterdir)
        with pytest.raises(
            validator.ResearchMirrorError,
            match=(
                "status failed"
                if boundary == "physical"
                else "scan failed"
                if boundary == "scan"
                else "ID status failed"
            ),
        ) as caught:
            if boundary == "physical":
                validator._physical_status(  # pyright: ignore[reportPrivateUsage]
                    child, "research document"
                )
            else:
                validator._directory_ids(  # pyright: ignore[reportPrivateUsage]
                    directory
                )
    elif boundary == "discovery":

        def fail_discovery(_root: Path) -> None:
            raise fault

        monkeypatch.setattr(validator, "research_algorithm_directories", fail_discovery)
        with pytest.raises(
            validator.ResearchMirrorError, match="discovery failed"
        ) as caught:
            validator.validate_repository(_always_ignored)
    else:
        entry = validator.MirrorEntry(
            document=tmp_path / "docs/fixture",
            executable=tmp_path / "algorithms/fixture",
            research_id="fixture",
        )

        def fail_git(*_args: object, **_kwargs: object) -> None:
            raise fault

        monkeypatch.setattr(sp, "run", fail_git)
        with pytest.raises(
            validator.ResearchMirrorError, match="Git ignore probe failed"
        ) as caught:
            validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]
    assert caught.value.__cause__ is fault


def test_mirror_native_host_error_diagnostic_remains_actionable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Exact built-in OSError text remains in typed failure diagnostics."""
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    entry = validator.MirrorEntry(
        document=tmp_path / "docs/fixture",
        executable=tmp_path / "algorithms/fixture",
        research_id="fixture",
    )
    fault = OSError("native git executable unavailable")

    def fail_git(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(sp, "run", fail_git)
    with pytest.raises(
        validator.ResearchMirrorError,
        match="native git executable unavailable",
    ) as caught:
        validator._out_is_ignored(entry)  # pyright: ignore[reportPrivateUsage]
    assert caught.value.__cause__ is fault
