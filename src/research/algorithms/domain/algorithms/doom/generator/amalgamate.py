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
#   - Generate the standalone original-DOOM-to-doom.c transform.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Generate the standalone original-DOOM-to-doom.c transform."""

from pathlib import Path

from algorithms.diff import DiffRecipe
from algorithms.diff import TransformMode
from algorithms.diff import write_algorithm
from scripts.repository_root import repository_root

REPOSITORY_ROOT = repository_root(Path(__file__))
RECIPE = DiffRecipe(
    source_root=REPOSITORY_ROOT / "doom" / "source",
    oracle_root=(
        REPOSITORY_ROOT
        / "src/research/algorithms/domain/algorithms/doom/amalgamate/in/oracle"
    ),
    output_algorithm=(
        REPOSITORY_ROOT
        / "src/research/algorithms/composition/algorithms/doom/amalgamate"
        / "main.rs"
    ),
    profile="doom-final-v1",
    mode=TransformMode.EXACT_BASELINE,
    domain_module=Path(__file__).with_name("amalgamate_domain.py"),
    source_binding_threshold=0.66,
    source_binding_maximum_anchors=127,
    source_binding_minimum_files=32,
)


def main() -> int:
    """Write the exact standalone final DOOM algorithm or fail closed.

    Returns:
        Zero after deterministic transform generation.

    """
    write_algorithm(RECIPE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
