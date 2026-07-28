# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Generate the source-bound DOOM single-TU amalgamation transform."""

from pathlib import Path

from algorithms.diff import DiffRecipe
from algorithms.diff import TransformMode
from algorithms.diff import write_algorithm

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RECIPE = DiffRecipe(
    source_root=(
        REPOSITORY_ROOT
        / "algorithms"
        / "doom"
        / "quality"
        / "out"
        / "doom_fixed"
        / "linuxdoom-1.10"
    ),
    oracle_root=(
        REPOSITORY_ROOT / "algorithms" / "doom" / "amalgamate" / "in" / "oracle"
    ),
    output_algorithm=(
        REPOSITORY_ROOT / "algorithms" / "doom" / "amalgamate" / "main.rs"
    ),
    profile="doom-amalgamate-v1",
    mode=TransformMode.EXACT_BASELINE,
    source_binding_threshold=0.66,
    source_binding_maximum_anchors=127,
    source_binding_minimum_files=32,
)


def main() -> int:
    """Write the exact source-bound amalgamation algorithm or fail closed.

    Returns:
        Zero after deterministic transform generation.

    """
    write_algorithm(RECIPE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
