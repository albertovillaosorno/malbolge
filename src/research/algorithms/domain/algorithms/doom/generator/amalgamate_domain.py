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
#   - Domain preflight for the standalone original-DOOM-to-doom.c transform.
# - Must-Not:
#   - Admit an unpinned upstream source or a multi-file final authoring oracle.
# - Allows:
#   - Inputs: the exact pinned DOOM source and one ignored `doom.c` oracle.
#   - Outputs: deterministic provenance evidence and fail-closed oracle checks.
#   - Side effects: none.
# - Split-When:
#   - Split when another final artifact needs a distinct source/oracle contract.
# - Merge-When:
#   - Merge when quality and final publication use identical oracle surfaces.
# - Summary:
#   - Validate the standalone final DOOM transform's source and oracle.
# - Description:
#   - Reuses the canonical upstream source pin while requiring one `doom.c`.
# - Usage:
#   - Loaded by `amalgamate.py` before generating the final Rust transform.
# - Defaults:
#   - Linked, missing, extra, or non-regular oracle entries fail closed.
#

"""Domain preflight for the standalone final DOOM transform."""

from __future__ import annotations

from stat import S_ISDIR
from stat import S_ISLNK
from stat import S_ISREG
from typing import TYPE_CHECKING

from algorithms.doom.generator import doom as doom_domain

if TYPE_CHECKING:
    from pathlib import Path

    from algorithms.diff.provenance import SourcePinEvidence

build_behavior_probe_context = doom_domain.build_behavior_probe_context
build_behavior_programs = doom_domain.build_behavior_programs
build_compatible_correction_bindings = (
    doom_domain.build_compatible_correction_bindings
)
build_identity_tree = doom_domain.build_identity_tree
map_compatible_file = doom_domain.map_compatible_file


class DoomFinalOracleError(RuntimeError):
    """Raised when the accepted final `doom.c` oracle surface is invalid."""


def validate_source_provenance(source_root: Path) -> SourcePinEvidence:
    """Require the same exact upstream source pin as the quality workflow.

    Returns:
        Exact source-pin evidence from the canonical DOOM domain.

    """
    return doom_domain.validate_source_provenance(source_root)


def _mode(path: Path, description: str) -> int:
    try:
        mode = path.lstat().st_mode
    except OSError as error:
        message = (
            f"DOOM final oracle {description} status failed: {path}: {error}"
        )
        raise DoomFinalOracleError(message) from error
    if S_ISLNK(mode) or path.is_junction():
        message = f"DOOM final oracle {description} must not be linked: {path}"
        raise DoomFinalOracleError(message)
    return mode


def validate_authoring_oracle(oracle_root: Path) -> None:
    """Require an oracle directory containing exactly one regular `doom.c`.

    Raises:
        DoomFinalOracleError: The final oracle surface is not exact and regular.

    """
    if not S_ISDIR(_mode(oracle_root, "root")):
        message = f"DOOM final oracle root must be a directory: {oracle_root}"
        raise DoomFinalOracleError(message)
    try:
        entries = tuple(oracle_root.iterdir())
    except OSError as error:
        message = (
            f"DOOM final oracle enumeration failed: {oracle_root}: {error}"
        )
        raise DoomFinalOracleError(message) from error
    names = tuple(sorted(entry.name for entry in entries))
    if names != ("doom.c",):
        message = f"DOOM final oracle must contain only doom.c: {names!r}"
        raise DoomFinalOracleError(message)
    doom_c = entries[0]
    if not S_ISREG(_mode(doom_c, "doom.c")):
        message = f"DOOM final oracle must be a regular file: {doom_c}"
        raise DoomFinalOracleError(message)
