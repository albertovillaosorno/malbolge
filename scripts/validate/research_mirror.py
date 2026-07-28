# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Validate the research algorithm semantic mirror and local-output contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed Git argv, never a shell command.
import sys
from typing import Never
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_ROOT = ROOT / "docs" / "research" / "algorithms"
EXECUTABLE_ROOT = ROOT / "algorithms"
GIT = "git"
NON_RESEARCH_ALGORITHM_IDS = frozenset({"diff", "doom"})


class ResearchMirrorError(ValueError):
    """Deterministic research-mirror identity or artifact-layout failure."""


@dataclass(frozen=True, slots=True)
class MirrorEntry:
    """One stable research ID and its two repository mirror directories."""

    document: Path
    executable: Path
    research_id: str


def _fail(message: str) -> Never:
    raise ResearchMirrorError(message)


def _directory_ids(root: Path) -> frozenset[str]:
    if not root.is_dir():
        _fail(f"research mirror root not found: {root}")
    return frozenset(
        path.name
        for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def validate_id_sets(
    document_ids: frozenset[str],
    executable_ids: frozenset[str],
) -> tuple[str, ...]:
    """Return stable mirror IDs after exact two-sided identity validation.

    Returns:
        Sorted stable research IDs when both mirror roots contain the same set.

    """
    document_only = sorted(document_ids - executable_ids)
    executable_only = sorted(executable_ids - document_ids)
    if document_only or executable_only:
        message = (
            f"research mirror IDs differ: document_only={document_only}, "
            f"executable_only={executable_only}"
        )
        _fail(message)
    if not document_ids:
        _fail("research mirror contains no algorithm IDs")
    return tuple(sorted(document_ids))


def executable_research_ids(executable_ids: frozenset[str]) -> frozenset[str]:
    """Remove explicitly classified non-research algorithm-suite IDs.

    Returns:
        Executable IDs that remain subject to the academic mirror contract.

    """
    return executable_ids - NON_RESEARCH_ALGORITHM_IDS


def _entries() -> tuple[MirrorEntry, ...]:
    research_ids = validate_id_sets(
        _directory_ids(DOCUMENT_ROOT),
        executable_research_ids(_directory_ids(EXECUTABLE_ROOT)),
    )
    return tuple(
        MirrorEntry(
            document=DOCUMENT_ROOT / research_id,
            executable=EXECUTABLE_ROOT / research_id,
            research_id=research_id,
        )
        for research_id in research_ids
    )


def _require_directory(path: Path, context: str) -> None:
    if not path.is_dir():
        _fail(f"{context} directory not found: {path.relative_to(ROOT)}")


def _require_file(path: Path, context: str) -> None:
    if not path.is_file():
        _fail(f"{context} file not found: {path.relative_to(ROOT)}")


def _out_probe(entry: MirrorEntry) -> str:
    return (
        (entry.executable / "out" / ".mirror-probe")
        .relative_to(ROOT)
        .as_posix()
    )


def _out_is_ignored(entry: MirrorEntry) -> bool:
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed Git argv, no shell.
        [GIT, "check-ignore", "--quiet", "--no-index", _out_probe(entry)],
        cwd=ROOT,
        check=False,
        shell=False,
    )
    if completed.returncode not in {0, 1}:
        message = (
            "git check-ignore failed for research output probe: "
            f"{entry.research_id} exit={completed.returncode}"
        )
        _fail(message)
    return completed.returncode == 0


def _validate_entry(
    entry: MirrorEntry,
    output_policy: Callable[[MirrorEntry], bool],
) -> None:
    _require_file(entry.document / "README.md", f"{entry.research_id} document")
    _require_file(
        entry.document / "research.md",
        f"{entry.research_id} research record",
    )
    _require_file(
        entry.executable / "README.md",
        f"{entry.research_id} executable",
    )
    _require_file(
        entry.executable / "experiment.toml",
        f"{entry.research_id} experiment configuration",
    )
    _require_file(
        entry.executable / "lifecycle.toml",
        f"{entry.research_id} lifecycle configuration",
    )
    _require_directory(
        entry.executable / "tests",
        f"{entry.research_id} executable tests",
    )
    if not output_policy(entry):
        message = (
            "research output is not Git ignored: "
            f"algorithms/{entry.research_id}/out/"
        )
        _fail(message)


def validate_repository(
    output_policy: Callable[[MirrorEntry], bool] | None = None,
) -> tuple[str, ...]:
    """Validate all mirrored research algorithm IDs and required artifacts.

    Args:
        output_policy: Optional deterministic output-ignore predicate. The CLI
            defaults to Git's real `check-ignore`; tests may inject a pure
            oracle.

    Returns:
        Stable sorted research IDs after all mirror invariants pass.

    """
    policy = _out_is_ignored if output_policy is None else output_policy
    entries = _entries()
    for entry in entries:
        _validate_entry(entry, policy)
    return tuple(entry.research_id for entry in entries)


def main() -> int:
    """Validate the repository research mirror and return process status.

    Returns:
        Zero for a valid mirror and one for deterministic policy failure.

    """
    try:
        research_ids = validate_repository()
    except (OSError, ResearchMirrorError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    _ = sys.stdout.write(f"research mirror valid: {len(research_ids)} ids\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
