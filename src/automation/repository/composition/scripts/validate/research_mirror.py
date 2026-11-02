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

import os

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed Git argv, never a shell command.
import sys
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISDIR, S_ISLNK, S_ISREG
from typing import TYPE_CHECKING, Never, cast

from scripts.repository_root import repository_root
from scripts.research_layout import (
    STATE_GRAPH_ID,
    research_algorithm_directories,
    research_algorithm_test_directory,
    research_id_alias_key,
    research_id_is_portable,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TextIO

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


def _host_error_detail(error: Exception) -> str:
    """Keep native host error details without invoking caller-owned hooks.

    Returns:
        Built-in diagnostic text or an untrusted exception type label.

    """
    if type(error) in (OSError, ValueError, TypeError, RuntimeError):
        return str(error)
    return type(error).__name__


def _native_status(receipt: object, context: str) -> os.stat_result:
    """Accept exact native filesystem status before inspecting its fields."""
    if type(receipt) is not os.stat_result:
        _fail(f"{context} requires native stat receipt")
    if type(receipt.st_mode) is not int:
        _fail(f"{context} requires native stat mode")
    return receipt


def _redirected_status(path: Path, status: os.stat_result, context: str) -> bool:
    """Reject foreign junction truthiness even for a native path status."""
    if S_ISLNK(status.st_mode):
        return True
    verdict = path.is_junction()
    if type(verdict) is not bool:
        _fail(f"{context} requires native junction receipt")
    return verdict


def _physical_status(path: Path, context: str) -> os.stat_result:
    """Check every in-root path component without following a redirect."""
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        _fail(f"{context} must be under the repository root: {path}")
    if ".." in relative.parts:
        _fail(f"{context} must not escape the repository root: {path}")
    current = ROOT
    status = None
    for index, component in enumerate(relative.parts):
        current = current / component
        try:
            status = _native_status(current.lstat(), context)
            redirected = _redirected_status(current, status, context)
        except ResearchMirrorError:
            raise
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            detail = _host_error_detail(error)
            raise ResearchMirrorError(f"{context} status failed: {detail}") from error
        if redirected:
            _fail(f"{context} must not redirect: {relative.as_posix()}")
        if index != len(relative.parts) - 1 and not S_ISDIR(status.st_mode):
            _fail(f"{context} ancestor must be a directory: {relative.as_posix()}")
    if status is None:
        _fail(f"{context} cannot be the repository root")
    return status


def _directory_ids(root: Path) -> frozenset[str]:
    _require_directory(root, "research mirror root")
    identifiers: set[str] = set()
    seen_names: set[str] = set()
    try:
        children = tuple(root.iterdir())
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        detail = _host_error_detail(error)
        raise ResearchMirrorError(f"research mirror scan failed: {detail}") from error
    for path in children:
        if type(path) is not type(root) or path.parent != root:
            _fail("research mirror scan requires native immediate directory entry")
        identifier = path.name
        if identifier in seen_names:
            _fail(f"research mirror scan duplicate directory entry: {identifier}")
        seen_names.add(identifier)
        if identifier.startswith("."):
            continue
        try:
            status = _native_status(path.lstat(), "research mirror ID")
            redirected = _redirected_status(path, status, "research mirror ID")
        except ResearchMirrorError:
            raise
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            detail = _host_error_detail(error)
            raise ResearchMirrorError(
                f"research mirror ID status failed: {detail}"
            ) from error
        if redirected:
            _fail(f"research mirror ID must not redirect: {identifier}")
        if S_ISDIR(status.st_mode):
            identifiers.add(identifier)
    return frozenset(identifiers)


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
    casefolded: dict[str, str] = {}
    for identifier in sorted(document_ids):
        if not research_id_is_portable(identifier):
            _fail(f"research ID not portable across hosts: {identifier}")
        previous = casefolded.setdefault(research_id_alias_key(identifier), identifier)
        if previous != identifier:
            message = f"case-insensitive research mirror ID collision: {previous}"
            _fail(f"{message} and {identifier}")
    return tuple(sorted(document_ids))


def executable_research_ids(executable_ids: frozenset[str]) -> frozenset[str]:
    """Remove explicitly classified non-research algorithm-suite IDs.

    Returns:
        Executable IDs that remain subject to the academic mirror contract.

    """
    return executable_ids - NON_RESEARCH_ALGORITHM_IDS


def _entries() -> tuple[MirrorEntry, ...]:
    try:
        discovered = research_algorithm_directories(ROOT)
        if type(discovered) is not tuple:
            _fail("research mirror discovery requires native layout receipt")
        executable_by_id: dict[str, Path] = {}
        for pair in discovered:
            if type(pair) is not tuple or len(pair) != 2:
                _fail("research mirror discovery requires native ID/path pair")
            research_id, directory = pair
            if type(research_id) is not str or type(directory) is not type(ROOT):
                _fail("research mirror discovery requires native ID/path members")
            expected = (
                ROOT / "src/research/algorithms/composition/state-graph"
                if research_id == STATE_GRAPH_ID
                else ROOT / "src/research/algorithms/domain/algorithms" / research_id
            )
            if directory != expected:
                _fail(f"research mirror discovery has noncanonical path: {research_id}")
            if research_id in executable_by_id:
                _fail(f"research mirror discovery has duplicate ID: {research_id}")
            executable_by_id[research_id] = directory
    except ResearchMirrorError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        detail = _host_error_detail(error)
        raise ResearchMirrorError(
            f"research mirror discovery failed: {detail}"
        ) from error
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
    status = _physical_status(path, context)
    if not S_ISDIR(status.st_mode):
        _fail(f"{context} directory not found: {path.relative_to(ROOT)}")


def _require_file(path: Path, context: str) -> None:
    status = _physical_status(path, context)
    if not S_ISREG(status.st_mode):
        _fail(f"{context} file not found: {path.relative_to(ROOT)}")


def _out_directory(entry: MirrorEntry) -> str:
    """Select the complete output directory, not a single probe filename."""
    return (entry.executable / "out").relative_to(ROOT).as_posix() + "/"


def _out_is_ignored(entry: MirrorEntry) -> bool:
    command = [
        GIT,
        "check-ignore",
        "--quiet",
        "--no-index",
        "--",
        _out_directory(entry),
    ]
    # jig-ignore-next-line: indivisible reviewed identifier
    try:
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - fixed Git argv, no shell.
            command.copy(),
            cwd=ROOT,
            check=False,
            shell=False,
            timeout=15,
        )
    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as error:
        detail = _host_error_detail(error)
        raise ResearchMirrorError(f"Git ignore probe failed: {detail}") from error
    if type(completed) is not subprocess.CompletedProcess:
        _fail("malformed Git ignore process receipt")
    native = cast("subprocess.CompletedProcess[object]", completed)
    argv = cast("object", native.args)
    if type(argv) is not list:
        _fail("malformed Git ignore process receipt")
    observed = cast("list[object]", argv)
    if (
        type(native.returncode) is not int
        or len(observed) != len(command)
        or any(type(argument) is not str for argument in observed)
        or observed != command
    ):
        _fail("malformed Git ignore process receipt")
    if native.returncode not in {0, 1}:
        message = (
            "git check-ignore failed for research output probe: "
            f"{entry.research_id} exit={native.returncode}"
        )
        _fail(message)
    return native.returncode == 0


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
    ignored = output_policy(entry)
    if type(ignored) is not bool:
        _fail(f"{entry.research_id} output policy requires native boolean verdict")
    if not ignored:
        message = (
            "research output is not Git ignored: "
            f"{(entry.executable / 'out').relative_to(ROOT).as_posix()}/"
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


def _write_cli_record(stream: TextIO, message: str) -> bool:
    """Require the exact native count and a completed text flush.

    Returns:
        Whether a complete CLI record was written and flushed.

    """
    try:
        written = stream.write(message)
        if type(written) is not int or written != len(message):
            return False
        return stream.flush() is None
    except (
        AttributeError,
        IndexError,
        OSError,
        OverflowError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        return False


def main() -> int:
    """Validate the repository research mirror and return process status.

    Returns:
        Zero for a valid mirror and one for deterministic policy failure.

    """
    try:
        research_ids = validate_repository()
        message = f"research mirror valid: {len(research_ids)} ids\n"
        if not _write_cli_record(sys.stdout, message):
            _fail("research mirror CLI output write or flush failed")
    except (OSError, ResearchMirrorError) as error:
        detail = (
            str(error)
            if type(error) is ResearchMirrorError
            else _host_error_detail(error)
        )
        _ = _write_cli_record(sys.stderr, f"error: {detail}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
