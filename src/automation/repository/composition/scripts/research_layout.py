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

from stat import S_ISLNK
from stat import S_ISREG
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

STATE_GRAPH_ID = "self-modification-state-graph-optimizer"


def _manifest_is_file(path: Path) -> bool:
    try:
        status = path.lstat()
    except FileNotFoundError:
        return False
    if S_ISLNK(status.st_mode) or path.is_junction():
        message = f"research manifest path must not redirect: {path}"
        raise OSError(message)
    return S_ISREG(status.st_mode)


def research_algorithm_directories(root: Path) -> tuple[tuple[str, Path], ...]:
    """Return stable research IDs paired with their physical directories.

    Returns:
        Sorted `(research_id, directory)` pairs for every research experiment.

    """
    domain_root = root / "src/research/algorithms/domain/algorithms"
    entries = {
        directory.name: directory
        for directory in domain_root.iterdir()
        if _manifest_is_file(directory / "experiment.toml")
    }
    state_graph = root / "src/research/algorithms/composition/state-graph"
    if _manifest_is_file(state_graph / "experiment.toml"):
        entries[STATE_GRAPH_ID] = state_graph
    return tuple(sorted(entries.items()))


def research_algorithm_test_directory(root: Path, identifier: str) -> Path:
    """Return the canonical centralized test directory for one research ID.

    Returns:
        Function-oriented test directory corresponding to `identifier`.

    """
    part = "state-graph" if identifier == STATE_GRAPH_ID else identifier
    return root / "tests/function/algorithms/domain" / part
