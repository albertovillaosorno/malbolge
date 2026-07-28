# File:
#   - __init__.py
# Path:
#   - optimizer/__init__.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
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
#   - Deterministic optimizer and search baselines.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Deterministic optimizer and search baselines."""

from optimizer.enumerative import ENUMERATIVE_ALGORITHM_ID
from optimizer.enumerative import EnumerationProblem
from optimizer.enumerative import cpu_enumerative_adapter
from optimizer.enumerative import enumerate_candidates
from optimizer.enumerative import search_and_verify
from optimizer.pruning import ExactDuplicatePartition
from optimizer.pruning import prune_exact_duplicates
from optimizer.rotate_target import ROTATE_TARGET_ALGORITHM_ID
from optimizer.rotate_target import RotateTargetProblem
from optimizer.rotate_target import RotateTargetVerifier
from optimizer.rotate_target import cpu_rotate_target_search_adapter
from optimizer.rotate_target import rotate_target_search_adapter

__all__ = [
    "ENUMERATIVE_ALGORITHM_ID",
    "ROTATE_TARGET_ALGORITHM_ID",
    "EnumerationProblem",
    "ExactDuplicatePartition",
    "RotateTargetProblem",
    "RotateTargetVerifier",
    "cpu_enumerative_adapter",
    "cpu_rotate_target_search_adapter",
    "enumerate_candidates",
    "prune_exact_duplicates",
    "rotate_target_search_adapter",
    "search_and_verify",
]
