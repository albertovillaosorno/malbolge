# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Generate the DOOM quality transformation from source and local oracle."""

from pathlib import Path

from algorithms.diff import DiffRecipe
from algorithms.diff import write_algorithm

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RECIPE = DiffRecipe(
    source_root=REPOSITORY_ROOT / "doom",
    oracle_root=REPOSITORY_ROOT / "algorithms/doom/quality/in/doom",
    output_algorithm=REPOSITORY_ROOT / "algorithms/doom/quality/main.rs",
    profile="doom-quality-v1",
    domain_module=Path(__file__).with_name("doom.py"),
    minimum_source_similarity=0.50,
    minimum_anchor_coverage=0.66,
    minimum_behavior_similarity=0.80,
    ignore_comments_for_identity=True,
    ignore_formatting_for_identity=True,
)


def main() -> int:
    """Write the generated quality algorithm or fail closed.

    Returns:
        Zero after successful generation. The current scaffold raises first.

    """
    write_algorithm(RECIPE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
