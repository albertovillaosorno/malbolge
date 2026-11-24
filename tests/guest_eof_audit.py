# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Exact stage classification of source-C compiler acceptance probes.
# - Must-Not:
#   - Turn Unsupported into layout acceptance or host C execution into guest.
# - Allows:
#   - Inputs: bounded adapter result and isolated target path.
#   - Outputs: classified layout refusal or strict frontend refusal assertions.
#   - Side effects: none.
# - Split-When:
#   - General stage-aware acceptance harness subsumes this boundary.
# - Merge-When:
#   - Source-C suite assertions share a single frontend admission contract.
# - Summary:
#   - Fail-closed frontend refusals never masquerade as backend admission.

"""Differentiate frontend refusal from demonstrated layout reachability."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


def frontend_layout_or_explicit_refusal(
    test: unittest.TestCase,
    result: subprocess.CompletedProcess[bytes],
    target: Path,
) -> None:
    """Require one exact stage failure without treating either as guest success."""
    test.assertEqual(result.returncode, 1, result.stderr)
    if b"normalized frontend rejected: Unsupported" in result.stderr:
        test.assertIn(b"unlowered C", result.stderr)
        test.assertNotIn(b"layout backend exited unsuccessfully", result.stderr)
    else:
        test.assertIn(b"layout backend exited unsuccessfully", result.stderr)
        test.assertNotIn(b"normalized frontend rejected", result.stderr)
    test.assertFalse(target.exists())
