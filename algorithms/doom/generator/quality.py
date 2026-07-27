# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Generate the DOOM quality transformation from source and local oracle."""

from pathlib import Path

from algorithms.diff import DiffRecipe
from algorithms.diff import TransformMode
from algorithms.diff import write_algorithm

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RECIPE = DiffRecipe(
    source_root=REPOSITORY_ROOT / "doom",
    oracle_root=REPOSITORY_ROOT / "algorithms/doom/quality/in/doom",
    output_algorithm=REPOSITORY_ROOT / "algorithms/doom/quality/main.rs",
    profile="doom-quality-v1",
    mode=TransformMode.COMPATIBLE,
    domain_module=Path(__file__).with_name("doom.py"),
    minimum_source_similarity=0.50,
    minimum_anchor_coverage=0.66,
    minimum_behavior_similarity=0.80,
    source_binding_threshold=0.66,
    source_binding_maximum_anchors=127,
    source_binding_minimum_files=32,
    ignore_comments_for_identity=True,
    ignore_formatting_for_identity=True,
)


def main() -> int:
    """Write the compatible quality algorithm or fail closed.

    Returns:
        Zero after successful compatible generation. The current implementation
        raises before replacing the checked-in scaffold.

    """
    write_algorithm(RECIPE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
