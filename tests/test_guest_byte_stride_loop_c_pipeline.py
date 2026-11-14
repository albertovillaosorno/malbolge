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
#   - Source-proven finite non-unit C induction with actual guest I/O.
# - Must-Not:
#   - Guess finite inequality loops or trust forged Clang increment values.
# - Allows:
#   - Inputs: pinned Clang AST, original C and binary VM input streams.
#   - Outputs: normative VM parity or refusal without publication.
#   - Side effects: temporary artifacts only.
# - Split-When:
#   - General runtime C induction replaces bounded source replay.
# - Merge-When:
#   - Finite induction proof shares general typed loop semantics.
# - Summary:
#   - Prove finite single-digit strides for source-backed C for loops.
# - Description:
#   - Check guest parity, skipped endpoints, unreachable bounds and forgeries.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Divergent or unproven loops refuse without a guest artifact.

"""End-to-end C strides with real Malbolge VM output and safe refusals."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_guest_byte_inequality_loop_c_pipeline as previous

ROOT = previous.ROOT
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT


def program(start: int, comparator: str, bound: int, step: str) -> str:
    """Use a whole source-C program with byte input, nested if, continue."""
    return previous.program().replace(
        "for (int i = 0; i != 3; ++i)",
        f"for (int i = {start}; i {comparator} {bound}; {step})",
    )


class GuestByteStrideLoopCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(
            path.is_file()
            for path in (
                previous.total.FRONTEND,
                previous.total.ADAPTER,
                previous.total.LAYOUT,
                previous.total.VM,
            )
        ):
            self.skipTest("pinned frontend and normative Malbolge VM required")

    def test_nonunit_inequality_executes_original_c_in_guest(self) -> None:
        """Step-by-two loop terminates exactly at its source-bound endpoint."""
        data = (
            *(bytes((v, v ^ 255)) for v in (0, 1, 127, 128, 254, 255)),
            *(hashlib.shake_256(bytes((61, i))).digest(2) for i in range(8)),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "stride.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(program(0, "!=", 6, "i += 2"))
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for stdin in data:
                with self.subTest(stdin=stdin):
                    run = RUN(guest, stdin)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout, bytes((stdin[0],) * 4 + (stdin[1],)))
                    self.assertEqual(run.stderr, b"malbolge-steps-v1:8\n")

    def test_descending_nonunit_inequality_executes_in_guest(self) -> None:
        """The reverse stride reaches zero without inferring a host byte."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "descending.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(program(6, "!=", 0, "i -= 2"))
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for stdin in (b"\0\xff", b"\xff\0"):
                run = RUN(guest, stdin)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, bytes((stdin[0],) * 4 + (stdin[1],)))

    def test_ordered_strides_and_assignment_forms_reach_layout(self) -> None:
        """Strict/inclusive and zero-trip steps prove the exact C loop."""
        cases = (
            (0, "<", 7, "i = i + 3"),
            (0, "<=", 6, "i += 3"),
            (9, ">", 2, "i = i - 3"),
            (9, ">=", 3, "i -= 3"),
            (3, "!=", 3, "i += 2"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, (start, comparator, bound, step) in enumerate(cases):
                with self.subTest(case=index):
                    source = Path(directory) / f"ordered-{index}.c"
                    guest = source.with_suffix(".malbolge")
                    _ = source.write_text(program(start, comparator, bound, step))
                    result = subprocess.run(
                        [
                            str(previous.ADAPTER),
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
                        timeout=15,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(
                        b"layout backend exited unsuccessfully", result.stderr
                    )
                    self.assertFalse(guest.exists())

    def test_unreachable_inequality_and_large_strides_refuse(self) -> None:
        """Stepping over != cannot be mistaken for C loop termination."""
        invalid = (
            (0, "!=", 5, "i += 2"),
            (5, "!=", 0, "i -= 2"),
            (0, "!=", 6, "i -= 2"),
            (6, "!=", 0, "i += 2"),
            (0, "!=", 34, "i += 2"),
            (0, "!=", 6, "i += 0"),
            (0, "!=", 6, "i += 12"),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, (start, comparator, bound, step) in enumerate(invalid):
                with self.subTest(case=index):
                    source = Path(directory) / f"invalid-{index}.c"
                    guest = source.with_suffix(".malbolge")
                    _ = source.write_text(program(start, comparator, bound, step))
                    result = COMPILE(source, guest)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_forged_stride_literal_and_operator_refuse(self) -> None:
        """Normalized Clang metadata cannot change the original C stride."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "original.c"
            _ = source.write_text(program(0, "!=", 6, "i += 2"))
            normalized = NORMALIZED(source)
            for field in ("literal", "operator", "parent"):
                with self.subTest(field=field):
                    forged = copy.deepcopy(normalized)
                    nodes = cast("list[dict[str, object]]", forged["nodes"])
                    compound = next(
                        node
                        for node in nodes
                        if node.get("kind") == "compound-assignment-expression"
                    )
                    if field == "operator":
                        compound["operation"] = "-="
                    elif field == "parent":
                        compound["parent"] = 0
                    else:
                        index = nodes.index(compound)
                        rhs = nodes[index + 2]
                        rhs["literal"] = "3"
                        rhs["constant_integer"] = "3"
                    guest = Path(directory) / f"forged-{field}.malbolge"
                    result = PROJECT(forged, guest, source)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())


if __name__ == "__main__":
    _ = unittest.main()
