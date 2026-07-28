# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Conservative exact pruning used by production CPU search."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ExactDuplicatePartition:
    """Stable first-representative partition for exact candidate bytes."""

    canonical_indices: tuple[int, ...]
    representative_indices: tuple[int, ...]

    def saved_evaluations(self) -> int:
        """Return evaluations removed by exact duplicate pruning.

        Returns:
            Input count minus retained exact representatives.

        """
        return len(self.canonical_indices) - len(self.representative_indices)


def prune_exact_duplicates(
    candidates: tuple[bytes, ...],
) -> ExactDuplicatePartition:
    """Partition candidate bytes by exact equality and stable first occurrence.

    Returns:
        Representative indices and representative mapping for every input.

    """
    first_indices: dict[bytes, int] = {}
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
