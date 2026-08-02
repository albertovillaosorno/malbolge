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
#   - Deterministic discovery of the canonical repository root.
# - Must-Not:
#   - Infer roots from a fixed source depth or mutate repository state.
# - Allows:
#   - Inputs: one file or directory located within the repository.
#   - Outputs: the nearest ancestor carrying all canonical root markers.
#   - Side effects: read-only filesystem inspection.
# - Split-When:
#   - Another repository identity requires an independent marker contract.
# - Merge-When:
#   - Repository callers no longer need shared root discovery.
# - Summary:
#   - Resolve repository identity without depending on source layout depth.
# - Description:
#   - Requires Cargo, Malbolge profile, and Jig configuration markers.
# - Usage:
#   - Call with `Path(__file__)` from any repository-owned Python module.
# - Defaults:
#   - Missing identity fails closed with a deterministic error.
#

"""Canonical repository-root discovery for moved Python modules."""

from __future__ import annotations

from pathlib import Path

_ROOT_MARKERS = (
    Path("Cargo.toml"),
    Path("malbolge.json"),
    Path(".jig/jig.toml"),
)


class RepositoryRootError(RuntimeError):
    """No ancestor satisfies the repository identity contract."""


def repository_root(start: Path) -> Path:
    """Return the nearest ancestor carrying every repository marker.

    Returns:
        Canonical repository root containing Cargo, profile, and Jig markers.

    Raises:
        RepositoryRootError: No ancestor carries every required marker.

    """
    resolved = start.resolve()
    directory = resolved.parent if resolved.is_file() else resolved
    for candidate in (directory, *directory.parents):
        if all((candidate / marker).is_file() for marker in _ROOT_MARKERS):
            return candidate
    message = f"repository root not found from: {start}"
    raise RepositoryRootError(message)
