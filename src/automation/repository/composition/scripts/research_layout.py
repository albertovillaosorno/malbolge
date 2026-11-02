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
#   - Stable research IDs mapped to canonical Jig source directories.
# - Must-Not:
#   - Parse experiment contents or classify non-research utility suites.
# - Allows:
#   - Inputs: one canonical repository root.
#   - Outputs: stable ID and physical-directory pairs in deterministic order.
#   - Side effects: read-only directory inspection.
# - Split-When:
#   - Another research family gains an independent physical topology.
# - Merge-When:
#   - Research manifests become the sole source-layout projection.
# - Summary:
#   - Project stable research identities onto canonical Jig parts.
# - Description:
#   - Includes domain experiments and the composition-owned state graph.
# - Usage:
#   - Shared by lifecycle, experiment, and mirror validators.
# - Defaults:
#   - Directories without an experiment manifest are excluded.
#

"""Stable research IDs mapped to canonical Jig source directories."""

from __future__ import annotations

import ntpath
import os
import unicodedata
from stat import S_ISDIR, S_ISLNK, S_ISREG
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

STATE_GRAPH_ID = "self-modification-state-graph-optimizer"


def research_id_is_portable(identifier: str) -> bool:
    """Require one path component with the same identity on every host."""
    return (
        identifier not in {"", ".", ".."}
        and "/" not in identifier
        and "\\" not in identifier
        and ":" not in identifier
        and not ntpath.isreserved(identifier)
    )


def research_id_alias_key(identifier: str) -> str:
    """Fold case and canonical Unicode spelling for host-portable identity."""
    return unicodedata.normalize("NFC", identifier.casefold())


def _native_status(status: object, context: str) -> os.stat_result:
    """Accept exact filesystem status receipts before any field access."""
    if type(status) is not os.stat_result:
        raise OSError(f"{context} requires native stat receipt")
    if type(status.st_mode) is not int:
        raise OSError(f"{context} requires native stat mode")
    return status


def _native_junction(value: object, context: str) -> bool:
    """Accept exact junction flags without invoking foreign truthiness hooks."""
    if type(value) is not bool:
        raise OSError(f"{context} requires native junction receipt")
    return value


def _unlinked_directory(root: Path, directory: Path) -> bool:
    """Check each in-root directory component without following an alias.

    Returns:
        Whether the full directory exists as physical directory entries.

    Raises:
        OSError: The tree has a linked or junction directory component.

    """
    current = root
    for part in directory.relative_to(root).parts:
        current /= part
        try:
            status = _native_status(current.lstat(), "research directory status")
        except FileNotFoundError:
            return False
        junction = _native_junction(current.is_junction(), "research directory status")
        if S_ISLNK(status.st_mode) or junction:
            message = f"research directory must not redirect: {current}"
            raise OSError(message)
        if not S_ISDIR(status.st_mode):
            return False
    return True


def _manifest_is_file(path: Path, root: Path) -> bool:
    if not _unlinked_directory(root, path.parent):
        return False
    try:
        status = _native_status(path.lstat(), "research manifest status")
    except FileNotFoundError:
        return False
    junction = _native_junction(path.is_junction(), "research manifest status")
    if S_ISLNK(status.st_mode) or junction:
        message = f"research manifest path must not redirect: {path}"
        raise OSError(message)
    return S_ISREG(status.st_mode)


def research_algorithm_directories(root: Path) -> tuple[tuple[str, Path], ...]:
    """Return stable research IDs paired with their physical directories.

    Returns:
        Sorted `(research_id, directory)` pairs for every research experiment.

    Raises:
        OSError: The research root is missing or redirects through a link.

    """
    domain_root = root / "src/research/algorithms/domain/algorithms"
    if not _unlinked_directory(root, domain_root):
        message = f"research domain directory missing or not regular: {domain_root}"
        raise OSError(message)
    entries: dict[str, Path] = {}
    seen_names: set[str] = set()
    for directory in domain_root.iterdir():
        if type(directory) is not type(domain_root) or directory.parent != domain_root:
            raise OSError("research scan requires native immediate directory entry")
        identifier = directory.name
        if identifier in seen_names:
            raise OSError(f"research scan duplicate directory entry: {identifier}")
        seen_names.add(identifier)
        if _manifest_is_file(directory / "experiment.toml", root):
            entries[identifier] = directory
    state_graph = root / "src/research/algorithms/composition/state-graph"
    if _manifest_is_file(state_graph / "experiment.toml", root):
        if STATE_GRAPH_ID in entries:
            message = (
                "duplicate research algorithm ID across domain and "
                f"composition experiments: {STATE_GRAPH_ID}"
            )
            raise OSError(message)
        entries[STATE_GRAPH_ID] = state_graph
    casefolded: dict[str, str] = {}
    for identifier in sorted(entries):
        if not research_id_is_portable(identifier):
            raise OSError(f"research ID not portable across hosts: {identifier}")
        previous = casefolded.setdefault(research_id_alias_key(identifier), identifier)
        if previous != identifier:
            message = f"case-insensitive research ID collision: {previous}"
            raise OSError(f"{message} and {identifier}")
    return tuple(sorted(entries.items()))


def research_algorithm_test_directory(root: Path, identifier: str) -> Path:
    """Return the canonical centralized test directory for one research ID.

    Returns:
        Function-oriented test directory corresponding to `identifier`.

    """
    part = "state-graph" if identifier == STATE_GRAPH_ID else identifier
    return root / "tests/function/algorithms/domain" / part
