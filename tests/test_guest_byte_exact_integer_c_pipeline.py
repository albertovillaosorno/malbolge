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
#   - Source-proven integer predicate values over successful guest bytes.
# - Must-Not:
#   - Fold actual input, erase branch effects or trust forged Clang evidence.
# - Allows:
#   - Inputs: original source, pinned Clang and binary guest data.
#   - Outputs: normative VM parity or no published guest artifact.
#   - Side effects: temporary isolated C and guest files.
# - Split-When:
#   - Real guest-side integer arithmetic and dynamic branches are available.
# - Merge-When:
#   - A general symbolic guest expression evaluator owns this proof.
# - Summary:
#   - Preserve values, not merely truth, through bitwise C operators.
# - Description:
#   - Complete counted C loops with branching, state and guest byte I/O.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Reject unproven source and Clang effects without publication.

"""Exact bounded C integer guards tested against actual guest execution."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast

from tests import test_guest_byte_equivalent_if_c_pipeline as equivalent
from tests import test_guest_byte_total_if_c_pipeline as total

ROOT = equivalent.ROOT
COMPILE = equivalent.COMPILE
RUN = equivalent.RUN
NORMALIZED = equivalent.NORMALIZED
PROJECT = equivalent.PROJECT
ADAPTER = equivalent.ADAPTER


class GuestByteExactIntegerCPipelineTests(unittest.TestCase):
    """Run full C streams against an independently computed binary oracle."""

    def setUp(self) -> None:
        if not all(
            path.is_file()
            for path in (
                equivalent.FRONTEND,
                equivalent.ADAPTER,
                equivalent.LAYOUT,
                equivalent.VM,
            )
        ):
            self.skipTest("pinned compiler and normative guest VM required")

    def test_exact_nonboolean_integer_guard_selects_real_guest_effects(self) -> None:
        """XOR cancellation and disjoint AND yield total C guards."""
        guards = (
            ("((current & 2) ^ (current & 2)) == 0", False),
            ("((current & 2) & (current & 4)) != 0", True),
            ("((current & 2) & (current & 4)) == 0", False),
            ("((current & 2) ^ (current & 2)) != 0", True),
            ("((current & 2) ^ (current & 4)) | 1", False),
        )
        inputs = (
            bytes((0, 255)),
            bytes((2, 4)),
            bytes((4, 2)),
            bytes((255, 0)),
            *(hashlib.shake_256(bytes((63, n))).digest(2) for n in range(14)),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (guard, reverse) in enumerate(guards):
                with self.subTest(guard=guard):
                    source = root / f"total-{index}.c"
                    guest = root / f"total-{index}.malbolge"
                    _ = source.write_text(total.source(guard, reverse=reverse, bound=1))
                    if index >= 2:
                        result = subprocess.run(
                            [
                                str(ADAPTER),
                                "--layout-backend",
                                sys.executable,
                                "--output",
                                str(guest),
                                "--source",
                                str(source),
                                "--capsule",
                            ],
                            input=json.dumps(NORMALIZED(source)).encode(),
                            capture_output=True,
                            check=False,
                            timeout=10,
                        )
                        self.assertEqual(result.returncode, 1, result.stderr)
                        self.assertIn(
                            b"layout backend exited unsuccessfully",
                            result.stderr,
                        )
                        self.assertFalse(guest.exists())
                        continue
                    result = COMPILE(source, guest)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for data in inputs:
                        executed = RUN(guest, data)
                        self.assertEqual(executed.returncode, 0, executed.stderr)
                        self.assertEqual(
                            executed.stdout, bytes((data[0],) * 2 + (data[1],))
                        )
                        self.assertEqual(executed.stderr, b"malbolge-steps-v1:6\n")

    def test_nonboolean_integer_guard_can_remain_guest_dependent(self) -> None:
        """Identical output traces survive a nonconstant XOR guard."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "dependent.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(
                equivalent.source("(current & 2) ^ (current & 4)", bound=1)
            )
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for value in (0, 1, 2, 4, 6, 127, 128, 255):
                data = bytes((value, value ^ 255))
                executed = RUN(guest, data)
                self.assertEqual(executed.returncode, 0, executed.stderr)
                self.assertEqual(executed.stdout, bytes((value,) * 2 + (data[1],)))

    def test_unsafe_effects_and_unproven_integer_expression_refuse(self) -> None:
        """No unequal branch or hidden I/O may disappear."""
        invalid = (
            total.source("(current & 2) ^ (current & 4)"),
            equivalent.source("(current & 2) ^ getchar()"),
            equivalent.source("(current & 2) & putchar(65)"),
            equivalent.source("(current & 2) ^ (current >> 1)"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, program in enumerate(invalid):
                source = Path(directory) / f"invalid-{index}.c"
                guest = source.with_suffix(".malbolge")
                _ = source.write_text(program)
                result = COMPILE(source, guest)
                self.assertNotEqual(result.returncode, 0, program)
                self.assertFalse(guest.exists(), program)

    def test_forged_integer_operator_and_parent_refuse(self) -> None:
        """Exact integer proof retains pinned Clang ancestry."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "authentic.c"
            _ = source.write_text(total.source("((current & 2) ^ (current & 2)) == 0"))
            normalized = NORMALIZED(source)
            for field in ("parent", "operation", "type", "span"):
                forged = copy.deepcopy(normalized)
                nodes = cast("list[dict[str, object]]", forged["nodes"])
                node = next(
                    item
                    for item in nodes
                    if item["kind"] == "binary-expression" and item["operation"] == "^"
                )
                if field == "parent":
                    node[field] = 0
                elif field == "operation":
                    node[field] = "|"
                elif field == "type":
                    node[field] = "u32"
                else:
                    span = cast("dict[str, dict[str, int]]", node[field])
                    span["begin"]["column"] += 1
                guest = Path(directory) / f"forged-{field}.malbolge"
                result = PROJECT(forged, guest, source)
                self.assertNotEqual(result.returncode, 0, field)
                self.assertFalse(guest.exists(), field)
