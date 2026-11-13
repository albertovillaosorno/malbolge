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
#   - Whole-C VM parity for source-proven fresh input into stale C locals.
# - Must-Not:
#   - Recover stale guest values or fabricate host-side byte streams.
# - Allows:
#   - Inputs: pinned Clang C, normalized JSON and binary guest stdin.
#   - Outputs: actual guest output or closed compiler refusal.
#   - Side effects: isolated artifacts under .temp.
# - Split-When:
#   - General C runtime storage replaces this accumulator-resident slice.
# - Merge-When:
#   - General C SSA assignment proof covers all byte-input locals.
# - Summary:
#   - A fresh read can overwrite any previously verified local binding.

"""Reassign stale C names from actual guest input without retaining old bytes."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests import test_source_local_alias_c_pipeline as aliases
from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import ADAPTER, FRONTEND, LAYOUT, ROOT, VM


def source() -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        "    int saved = current;\n"
        "    saved = getchar();\n"
        "    current = getchar();\n"
        "    putchar(current);\n"
        "    saved = getchar();\n"
        "    current = saved;\n"
        "    putchar(current);\n"
        "    putchar(saved);\n"
        "    for (int i = 0; i < 3; ++i) {\n"
        "        int byte = getchar();\n"
        "        int copy = byte;\n"
        "        if (i == 1) {\n"
        "            putchar(copy);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(byte);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class StaleLocalInputReassignmentCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned Clang, adapter, layout and VM required")

    def test_compound_source_switches_input_destination_and_runs_guest(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "alternating.c"
            guest = root / "alternating.malbolge"
            program.write_text(source(), encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(program, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 13, 7, 91)),
                hashlib.shake_256(b"alternating-C-local-guest-input").digest(8),
            ):
                with self.subTest(data=data):
                    result = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(
                        result.stdout,
                        data[2:3] + data[3:4] * 2 + data[4:],
                    )
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:16\n")

    def test_fresh_read_recovers_binding_after_discarded_guest_input(self) -> None:
        program_source = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    putchar(getchar());\n"
            "    current = getchar();\n"
            "    putchar(current);\n"
            "    for (int i = 0; i < 2; ++i) {\n"
            "        putchar(getchar());\n"
            "    }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "recover.c"
            guest = root / "recover.malbolge"
            program.write_text(program_source, encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(program, guest)
            self.assertEqual(built.returncode, 0, built.stderr)
            for data in (
                bytes((255, 0, 128, 1, 42)),
                hashlib.shake_256(b"unassigned-guest-input-reset").digest(5),
            ):
                with self.subTest(data=data):
                    result = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, data[1:])
                    self.assertEqual(result.stderr, b"malbolge-steps-v1:10\n")

            # Without the fresh assignment, the first local is still stale.
            program.write_text(
                program_source.replace(
                    "    current = getchar();\n    putchar(current);",
                    "    putchar(current);",
                ),
                encoding="utf-8",
            )
            rejected = root / "stale.malbolge"
            built = helpers.StaticForBreakCPipelineTests.compile(program, rejected)
            self.assertNotEqual(built.returncode, 0)
            self.assertFalse(rejected.exists())

    def test_stale_input_destination_requires_proven_binding(self) -> None:
        variations = (
            "current = getchar() + 0;",
            "current += getchar();",
            "current = (getchar());",
            "current = getc(stdin);",
            "current=getchar();",
            "current = current;",
            "other = getchar();",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, assignment in enumerate(variations):
                with self.subTest(assignment=assignment):
                    program = root / f"invalid-{index}.c"
                    guest = root / f"invalid-{index}.malbolge"
                    program.write_text(
                        source().replace(
                            "    current = getchar();\n",
                            f"    {assignment}\n",
                            1,
                        ),
                        encoding="utf-8",
                    )
                    built = helpers.StaticForBreakCPipelineTests.compile(program, guest)
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_stale_value_still_cannot_be_read_after_new_guest_input(self) -> None:
        modified = source().replace(
            "    current = saved;\n",
            "    putchar(current);\n    current = saved;\n",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "stale-read.c"
            guest = root / "stale-read.malbolge"
            program.write_text(modified, encoding="utf-8")
            built = helpers.StaticForBreakCPipelineTests.compile(program, guest)
            self.assertNotEqual(built.returncode, 0)
            self.assertFalse(guest.exists())

    def test_forged_stale_destination_and_missing_source_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "stale-assignment.c"
            program.write_text(source(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(program)
            assignment = next(
                node
                for node in normalized["nodes"]
                if node["kind"] == "binary-expression"
                and node.get("operation") == "="
                and node["span"]["begin"]["line"] == 6
            )
            first_id = assignment["id"]
            for index, (offset, field, value) in enumerate(
                (
                    (0, "parent", 0),
                    (0, "type", "u32"),
                    (1, "reference", "stale@0"),
                    (1, "type", "u8"),
                    (2, "reference", "other:getchar"),
                    (3, "operation", "integral-cast"),
                    (4, "parent", 0),
                )
            ):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    node = next(
                        item
                        for item in forged["nodes"]
                        if item["id"] == first_id + offset
                    )
                    node[field] = value
                    guest = root / f"forged-{index}.malbolge"
                    built = aliases.SourceLocalAliasCPipelineTests.adapter(
                        forged, guest, program
                    )
                    self.assertNotEqual(built.returncode, 0)
                    self.assertFalse(guest.exists())
            guest = root / "missing-source.malbolge"
            built = aliases.SourceLocalAliasCPipelineTests.adapter(
                normalized, guest, None
            )
            self.assertNotEqual(built.returncode, 0)
            self.assertFalse(guest.exists())


if __name__ == "__main__":
    unittest.main()
