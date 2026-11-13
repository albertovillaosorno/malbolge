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
#   - Source-proven live local input replacement in actual guest byte streams.
# - Must-Not:
#   - Substitute host input, discard assignment reads, or admit arbitrary stores.
# - Allows:
#   - Inputs: pinned Clang C, binary stdin, and normalized-node mutations.
#   - Outputs: normative VM byte parity or fail-closed rejection.
#   - Side effects: isolated temporary test files.
# - Split-When:
#   - General guest mutable-variable lowering subsumes this identity binding.
# - Merge-When:
#   - Static finite-control proofs accept general source-bound assignments.
# - Summary:
#   - A live local can be rebound to a new guest read before its next output.

"""Prove C local reassignment reads a new guest byte, not a stale input."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests import test_source_local_alias_c_pipeline as alias_helpers
from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import ADAPTER, FRONTEND, LAYOUT, ROOT, VM


def source(assignment: str = "byte = getchar();") -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        "    current = getchar();\n"
        "    putchar(current);\n"
        "    for (int i = 0; i < 3; ++i) {\n"
        "        int byte = getchar();\n"
        f"        {assignment}\n"
        "        if (i % 2 == 0) {\n"
        "            putchar(byte);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(byte);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class LiveLocalReassignmentCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, compiler, layout and VM required")

    def test_complete_branching_stream_uses_reassigned_guest_byte(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "reassigned.c"
            guest = root / "reassigned.malbolge"
            path.write_text(source(), encoding="utf-8")
            result = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 13, 254, 7, 9)),
                hashlib.shake_256(b"live-byte-reassignment-2026").digest(9),
            ):
                with self.subTest(data=data):
                    run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(
                        run.stdout, data[1:2] + data[3:4] + data[5:6] + data[7:9]
                    )
                    self.assertEqual(run.stderr, b"malbolge-steps-v1:15\n")

    def test_zero_trip_assignment_is_authenticated_without_input(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "zero-trip.c"
            guest = root / "zero-trip.malbolge"
            path.write_text(source().replace("i < 3", "i < 0"), encoding="utf-8")
            result = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (bytes((0, 255, 128)), bytes((17, 42, 0))):
                run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, data[1:3])
                self.assertEqual(run.stderr, b"malbolge-steps-v1:6\n")

    def test_repeated_assignment_reads_each_new_input(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "repeated.c"
            guest = root / "repeated.malbolge"
            path.write_text(
                source("byte = getchar();\n        byte = getchar();"),
                encoding="utf-8",
            )
            result = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = bytes((0, 255, 128, 1, 42, 13, 254, 7, 9, 16, 200, 3))
            run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout, bytes(data[i] for i in (1, 4, 7, 10, 11)))
            self.assertEqual(run.stderr, b"malbolge-steps-v1:18\n")

    def test_unsupported_assignment_sources_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, assignment in enumerate(
                (
                    "byte += getchar();",
                    "byte = getchar() + 1;",
                    "byte = (unsigned char)getchar();",
                    "byte = (getchar(), getchar());",
                    "byte = current;",
                    "byte = 0;",
                )
            ):
                with self.subTest(assignment=assignment):
                    path = root / f"source-{index}.c"
                    guest = root / f"source-{index}.malbolge"
                    path.write_text(source(assignment), encoding="utf-8")
                    result = helpers.StaticForBreakCPipelineTests.compile(path, guest)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_forged_assignment_nodes_and_missing_source_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "reassignment.c"
            path.write_text(source(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            nodes = normalized["nodes"]
            assignment = next(
                n
                for n in nodes
                if n["kind"] == "binary-expression" and n.get("operation") == "="
            )
            node_id = assignment["id"]
            for index, (offset, field, value) in enumerate(
                (
                    (0, "operation", "+"),
                    (0, "type", "u32"),
                    (1, "reference", "other@47"),
                    (1, "parent", 2),
                    (2, "reference", "external:putchar"),
                    (3, "operation", "lvalue-to-rvalue"),
                    (4, "parent", 2),
                    (0, "span", {"begin": {"byte": 1}}),
                )
            ):
                with self.subTest(index=index):
                    altered = copy.deepcopy(normalized)
                    next(n for n in altered["nodes"] if n["id"] == node_id + offset)[
                        field
                    ] = value
                    guest = root / f"forged-{index}.malbolge"
                    result = alias_helpers.SourceLocalAliasCPipelineTests.adapter(
                        altered, guest, path
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())
            guest = root / "missing-source.malbolge"
            result = alias_helpers.SourceLocalAliasCPipelineTests.adapter(
                normalized, guest, None
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(guest.exists())


if __name__ == "__main__":
    unittest.main()
