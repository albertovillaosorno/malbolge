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
#   - Conservative exact pruning used by production CPU search.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Conservative exact pruning used by production CPU search."""

from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExactDuplicatePartition:
    """Stable first-representative partition for exact candidate values."""

    canonical_indices: tuple[int, ...]
    representative_indices: tuple[int, ...]

    def saved_evaluations(self) -> int:
        """Return evaluations removed by exact duplicate pruning.

        Returns:
            Input count minus retained exact representatives.

        """
        return len(self.canonical_indices) - len(self.representative_indices)


def prune_exact_duplicates[CandidateT: Hashable](
    candidates: tuple[CandidateT, ...],
) -> ExactDuplicatePartition:
    """Partition candidate values by exact equality and first occurrence.

    Returns:
        Representative indices and representative mapping for every input.

    """
    first_indices: dict[CandidateT, int] = {}
    representatives: list[int] = []
    canonical: list[int] = []
    for index, candidate in enumerate(candidates):
        representative = first_indices.get(candidate)
        if representative is None:
            first_indices[candidate] = index
            representatives.append(index)
            representative = index
        canonical.append(representative)
    return ExactDuplicatePartition(
        canonical_indices=tuple(canonical),
        representative_indices=tuple(representatives),
    )
