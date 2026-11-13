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
#   - Prove assignment of nested successful C output returns to live C bytes.
# - Must-Not:
#   - Infer failed output, EOF, storage, or unchecked AST/source identities.
# - Allows:
#   - Inputs: pinned C AST, original source witness, binary guest input.
#   - Outputs: normative VM byte parity and source/AST refusal tests.
#   - Side effects: isolated temporary guest artifacts.
# - Split-When:
#   - General call-result value lowering supersedes this bounded proof.
# - Merge-When:
#   - Nested output return and assignment-valued output share one grammar.
# - Summary:
#   - Nested putchar returns preserve one real guest byte in a C local.

"""Test whole original C nested output-return assignments in the guest VM."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests import test_source_local_alias_c_pipeline as aliases
from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import ADAPTER, FRONTEND, LAYOUT, ROOT, VM

ASSIGNMENT = "current = putchar(putchar(getchar()));"


def program(assignment: str = ASSIGNMENT, limit: int = 3) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        "    putchar(current);\n"
        f"    for (int i = 0; i < {limit}; ++i) {{\n"
        "        if (i % 2 == 0) {\n"
        f"            {assignment}\n"
        "            putchar(current);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class NestedOutputReturnAssignmentCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C frontend, adapter, layout and VM required")

    def test_full_branch_loop_matches_binary_oracles(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source, target = root / "full.c", root / "full.malbolge"
            source.write_text(program(), encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            streams = (
                bytes((0, 255, 128, 1)),
                bytes((255, 0, 1, 128)),
                *(
                    hashlib.shake_256(b"nested-output-return-" + bytes((seed,))).digest(
                        4
                    )
                    for seed in range(12)
                ),
            )
            for data in streams:
                with self.subTest(data=data):
                    guest = helpers.StaticForBreakCPipelineTests.vm(target, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(
                        guest.stdout,
                        bytes(
                            (
                                data[0],
                                data[1],
                                data[1],
                                data[1],
                                data[1],
                                data[2],
                                data[2],
                                data[2],
                                data[3],
                            )
                        ),
                    )
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:14\n")

    def test_top_level_three_deep_return_and_stale_destination(self) -> None:
        code = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    int older = getchar();\n"
            "    current = putchar(putchar(putchar(getchar())));\n"
            "    putchar(current);\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source, target = root / "triple.c", root / "triple.malbolge"
            source.write_text(code, encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((255, 0, 128, 1)),
                hashlib.shake_256(b"nested-triple-return").digest(4),
            ):
                guest = helpers.StaticForBreakCPipelineTests.vm(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(
                    guest.stdout,
                    bytes((data[2], data[2], data[2], data[2], data[3])),
                )
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:10\n")

    def test_zero_trip_authenticates_but_does_not_read(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source, target = root / "zero.c", root / "zero.malbolge"
            source.write_text(program(limit=0), encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255)),
                hashlib.shake_256(b"nested-zero-return").digest(2),
            ):
                guest = helpers.StaticForBreakCPipelineTests.vm(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:5\n")

    def test_unsupported_source_and_stale_alias_refuse(self) -> None:
        unsupported = (
            "current = putchar(putchar(getchar() + 1));",
            "current += putchar(putchar(getchar()));",
            "current = putchar(putchar(current));",
            "current = putchar(putchar(getchar()), getchar());",
            "current = putchar(getchar()) + putchar(getchar());",
        )
        stale = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    int older = current;\n"
            "    current = putchar(putchar(getchar()));\n"
            "    putchar(older);\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, code in enumerate(
                [*(program(item) for item in unsupported), stale]
            ):
                with self.subTest(index=index):
                    source = root / f"invalid-{index}.c"
                    target = root / f"invalid-{index}.malbolge"
                    source.write_text(code, encoding="utf-8")
                    result = helpers.StaticForBreakCPipelineTests.compile(
                        source, target
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_clang_ancestry_and_spans_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "original.c"
            source.write_text(program(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(source)
            nodes = normalized["nodes"]
            assignment = next(
                node
                for node in nodes
                if node["kind"] == "binary-expression"
                and node["span"]["begin"]["line"] == 7
            )
            at = nodes.index(assignment)
            edits = (
                (0, "operation", "+"),
                (0, "parent", 2),
                (1, "reference", "other@47"),
                (1, "parent", 2),
                (2, "reference", "external:getchar"),
                (2, "parent", 2),
                (3, "operation", "integral-cast"),
                (4, "reference", "external:getchar"),
                (5, "reference", "external:getchar"),
                (5, "parent", 2),
                (6, "operation", "integral-cast"),
                (7, "reference", "external:getchar"),
                (8, "reference", "external:putchar"),
                (8, "parent", 2),
                (9, "operation", "integral-cast"),
                (10, "reference", "external:putchar"),
            )
            for index, (offset, field, value) in enumerate(edits):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    forged["nodes"][at + offset][field] = value
                    target = root / f"forged-{index}.malbolge"
                    result = aliases.SourceLocalAliasCPipelineTests.adapter(
                        forged, target, source
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())
            for offset in (0, 2, 5, 8):
                for edge in ("begin", "end"):
                    forged = copy.deepcopy(normalized)
                    forged["nodes"][at + offset]["span"][edge]["column"] += 1
                    target = root / f"shift-{offset}-{edge}.malbolge"
                    result = aliases.SourceLocalAliasCPipelineTests.adapter(
                        forged, target, source
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_source_witness_and_operator_spoof_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "original.c"
            source.write_text(program(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(source)
            target = root / "missing.malbolge"
            result = aliases.SourceLocalAliasCPipelineTests.adapter(
                normalized, target, None
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())
            changed = root / "modified.c"
            changed.write_text(
                program().replace(ASSIGNMENT, ASSIGNMENT.replace(" = ", " + ")),
                encoding="utf-8",
            )
            forged = copy.deepcopy(normalized)
            forged["source"]["sha256"] = hashlib.sha256(
                changed.read_bytes()
            ).hexdigest()
            result = aliases.SourceLocalAliasCPipelineTests.adapter(
                forged, target, changed
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
