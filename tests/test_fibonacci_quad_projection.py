# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Check four source-proven C outputs reach the guest layout boundary.
# - Must-Not:
#   - Substitute host-calculated outputs for guest VM effects.
# - Allows:
#   - Inputs: pinned conditional Fibonacci C and compiled compiler tools.
#   - Outputs: exact guest replay or typed layout refusal with no artifact.
#   - Side effects: temporary compile outputs only.
# - Split-When:
#   - General four-output runtime compiler tests own this witness.
# - Merge-When:
#   - The generated C-to-guest oracle matrix subsumes this regression.
# - Summary:
#   - Distinguish source/typed projection from finite guest layout support.
# - Description:
#   - Full C loop and branch must retain distinct SSA/output identities.
# - Usage:
#   - python3.14 -B -m unittest tests.test_fibonacci_quad_projection -v
# - Defaults:
#   - No guest artifact on an unsupported layout.

"""Stateful four-iteration C-to-guest Fibonacci regression."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_compound_c_pipeline import (
    ADAPTER,
    DRIVER,
    FRONTEND,
    LAYOUT,
    ROOT,
    SOURCE,
    VM,
)

STEPS_PATTERN = rb"^malbolge-steps-v1:[1-9][0-9]*\n$"


def four_output_oracle() -> bytes:
    """Independently evaluate the unsigned recurrence and conditional I/O."""
    previous, current = 1, 1
    output = bytearray()
    for _ in range(4):
        following = (previous + current) & 255
        output.append(following if following & 1 == 0 else following ^ 0x3D)
        previous, current = current, following
    return bytes(output)


class FibonacciQuadProjectionTests(unittest.TestCase):
    def test_four_output_source_reaches_layout_or_guest_parity(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler or VM binaries unavailable")
        self.assertEqual(four_output_oracle(), bytes.fromhex("023e3808"))
        original = SOURCE.read_text()
        self.assertIn("i < 12U", original)
        self.assertIn("next ^ 0x5AU", original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as scratch:
            directory = Path(scratch)
            source = directory / "fibonacci-four.c"
            _written = source.write_text(
                original.replace("i < 12U", "i < 4U").replace(
                    "next ^ 0x5AU", "next ^ 0x3DU"
                )
            )
            guest = directory / "fibonacci-four.malbolge"
            result = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(DRIVER),
                    "--repository-tools",
                    "--source-id",
                    "tests/conditional-fibonacci-four-v1",
                    "--capsule",
                    "--output",
                    str(guest),
                    str(source),
                ],
                check=False,
                capture_output=True,
                timeout=60,
            )
            if result.returncode != 0:
                error_stage = (
                    b"canonical typed byte bridge rejected: "
                    + b"Layout(UnsupportedEffectTrace)"
                )
                self.assertIn(error_stage, result.stderr)
                self.assertNotIn(b"UnsupportedTypedIr", result.stderr)
                self.assertFalse(guest.exists(), "guest published on refusal")
                return
            self.assertTrue(guest.is_file())
            for payload in (b"", bytes((255, 0, 128))):
                replay = subprocess.run(
                    [str(VM), str(guest), "--input-stdin", "--report-steps"],
                    input=payload,
                    check=False,
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(replay.returncode, 0, replay.stderr)
                self.assertEqual(replay.stdout, four_output_oracle())
                self.assertRegex(replay.stderr, STEPS_PATTERN)
