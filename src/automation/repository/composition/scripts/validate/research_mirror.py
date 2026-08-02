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
#   - Validate the research algorithm semantic mirror and local-output contract.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Validate the research algorithm semantic mirror and local-output contract."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed Git argv, never a shell command.
import sys
from typing import Never
from typing import TYPE_CHECKING

from scripts.repository_root import repository_root
from scripts.research_layout import research_algorithm_directories
from scripts.research_layout import research_algorithm_test_directory

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = repository_root(Path(__file__))
DOCUMENT_ROOT = ROOT / "docs" / "research" / "algorithms"
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
    executable_by_id = dict(research_algorithm_directories(ROOT))
    research_ids = validate_id_sets(
        _directory_ids(DOCUMENT_ROOT),
        executable_research_ids(frozenset(executable_by_id)),
    )
    return tuple(
        MirrorEntry(
            document=DOCUMENT_ROOT / research_id,
            executable=executable_by_id[research_id],
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
    # jig-ignore-next-line: indivisible reviewed identifier
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
        research_algorithm_test_directory(ROOT, entry.research_id),
        f"{entry.research_id} executable tests",
    )
    if not output_policy(entry):
        message = (
            "research output is not Git ignored: "
            f"{(entry.executable / "out").relative_to(ROOT).as_posix()}/"
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
