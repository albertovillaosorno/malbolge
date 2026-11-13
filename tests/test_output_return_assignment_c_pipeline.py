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
#   - Source-checked C assignment from a successful guest putchar return.
# - Must-Not:
#   - Invent guest C storage or model failed output/EOF as a successful byte.
# - Allows:
#   - Inputs: pinned C Clang AST and original source witness.
#   - Outputs: real normative Malbolge binary VM parity and refusal tests.
#   - Side effects: temporary isolated guest files.
# - Split-When:
#   - General C call-result values supersede this bounded identity proof.
# - Merge-When:
#   - Nested byte-return C proofs share the same authenticated grammar.
# - Summary:
#   - Assigning putchar(getchar()) retains the written guest byte.

"""Check whole C output-return assignment against the actual guest VM."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests import test_source_local_alias_c_pipeline as aliases
from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import ADAPTER, FRONTEND, LAYOUT, ROOT, VM


def program(assignment: str = "current = putchar(getchar());") -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        "    putchar(current);\n"
        "    for (int i = 0; i < 3; ++i) {\n"
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


class OutputReturnAssignmentCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(t.is_file() for t in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler and normative guest VM required")

    def test_original_branch_loop_guest_binary_parity(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, target = root / "program.c", root / "program.malbolge"
            path.write_text(program(), encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            streams = (
                bytes((0, 255, 128, 1)),
                bytes((255, 0, 1, 128)),
                *(
                    hashlib.shake_256(b"output-return-" + bytes((seed,))).digest(4)
                    for seed in range(12)
                ),
            )
            for data in streams:
                with self.subTest(data=data):
                    vm = helpers.StaticForBreakCPipelineTests.vm(target, data)
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    self.assertEqual(
                        vm.stdout,
                        bytes(
                            (
                                data[0],
                                data[1],
                                data[1],
                                data[1],
                                data[2],
                                data[2],
                                data[3],
                            )
                        ),
                    )
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:12\n")

    def test_stale_top_level_destination_accepts_fresh_guest_return(self) -> None:
        source = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    int other = getchar();\n"
            "    current = putchar(getchar());\n"
            "    putchar(current);\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, target = root / "stale.c", root / "stale.malbolge"
            path.write_text(source, encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((255, 128, 0, 1)),
                hashlib.shake_256(b"output-return-stale").digest(4),
            ):
                guest = helpers.StaticForBreakCPipelineTests.vm(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, bytes((data[2], data[2], data[3])))
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:8\n")

    def test_zero_trip_authenticates_but_skips_output_return(self) -> None:
        source = program().replace("i < 3", "i < 0")
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, target = root / "zero.c", root / "zero.malbolge"
            path.write_text(source, encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255)),
                hashlib.shake_256(b"output-return-zero").digest(2),
            ):
                guest = helpers.StaticForBreakCPipelineTests.vm(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:5\n")

    def test_stale_identity_after_rebound_return_refuses(self) -> None:
        source = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    int older = current;\n"
            "    current = putchar(getchar());\n"
            "    putchar(older);\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, target = root / "stale.c", root / "stale.malbolge"
            path.write_text(source, encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, target)
            self.assertNotEqual(compiled.returncode, 0)
            self.assertFalse(target.exists())

    def test_unsupported_C_output_return_expressions_refuse(self) -> None:
        variants = (
            "current = putchar(getchar() + 1);",
            "current = putchar(putchar(getchar() + 1));",
            "current += putchar(getchar());",
            "current = getchar() + putchar(getchar());",
            "current = putchar(current);",
            "current = fputc(getchar(), stdout);",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(variants):
                with self.subTest(index=index):
                    path = root / f"unsupported-{index}.c"
                    target = root / f"unsupported-{index}.malbolge"
                    path.write_text(program(expression), encoding="utf-8")
                    compiled = helpers.StaticForBreakCPipelineTests.compile(
                        path, target
                    )
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_output_return_nodes_and_spans_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "source.c"
            path.write_text(program(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
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
                (0, "kind", "call-expression"),
                (0, "parent", 2),
                (0, "type", "u32"),
                (1, "reference", "different@47"),
                (1, "parent", 2),
                (1, "kind", "variable-declaration"),
                (2, "reference", "external:getchar"),
                (2, "parent", 2),
                (2, "type", "u32"),
                (3, "operation", "integral-cast"),
                (4, "reference", "external:getchar"),
                (5, "reference", "external:putchar"),
                (5, "parent", 2),
                (6, "operation", "integral-cast"),
                (7, "reference", "external:putchar"),
            )
            for index, (offset, field, value) in enumerate(edits):
                with self.subTest(index=index):
                    forged = copy.deepcopy(normalized)
                    forged["nodes"][at + offset][field] = value
                    target = root / f"forged-{index}.malbolge"
                    result = aliases.SourceLocalAliasCPipelineTests.adapter(
                        forged, target, path
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())
            for key in ("begin", "end"):
                forged = copy.deepcopy(normalized)
                forged["nodes"][at]["span"][key]["column"] += 1
                target = root / f"shift-{key}.malbolge"
                result = aliases.SourceLocalAliasCPipelineTests.adapter(
                    forged, target, path
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(target.exists())

    def test_source_witness_required_and_coherent_ast_spoof_refuses(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "source.c"
            path.write_text(program(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            target = root / "missing.malbolge"
            missing = aliases.SourceLocalAliasCPipelineTests.adapter(
                normalized, target, None
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertFalse(target.exists())
            changed = root / "changed.c"
            changed.write_text(
                program().replace(
                    "current = putchar(getchar());",
                    "current + putchar(getchar());",
                ),
                encoding="utf-8",
            )
            forged = copy.deepcopy(normalized)
            forged["source"]["sha256"] = hashlib.sha256(
                changed.read_bytes()
            ).hexdigest()
            mismatch = aliases.SourceLocalAliasCPipelineTests.adapter(
                forged, target, changed
            )
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
