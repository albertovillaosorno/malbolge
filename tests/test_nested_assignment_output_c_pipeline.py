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
#   - Prove C output-assignment expressions preserve fresh guest byte identity.
# - Must-Not:
#   - Host-fold stdin or infer state from unchecked AST/operator spelling.
# - Allows:
#   - Inputs: verified C source, Clang AST and binary guest stdin.
#   - Outputs: normative VM byte oracle parity and fail-closed refusals.
#   - Side effects: isolated temporary compiler artifacts.
# - Split-When:
#   - General guest assignment expression lowering supersedes this proof.
# - Merge-When:
#   - Source-C assignment/output proof shares one runtime identity evaluator.
# - Summary:
#   - putchar(local = getchar()) writes and retains one actual guest read.

"""Verify assignment-valued putchar calls through the actual guest VM."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests import test_source_local_alias_c_pipeline as aliases
from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import ADAPTER, FRONTEND, LAYOUT, ROOT, VM


def source(*, output: str = "putchar(byte = getchar());", limit: int = 3) -> str:
    """A complete C stream with source-state, selection and counted I/O."""
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        "    putchar(current);\n"
        "    putchar(current = getchar());\n"
        "    if (1) {\n"
        "        putchar(current);\n"
        "    }\n"
        f"    for (int i = 0; i < {limit}; ++i) {{\n"
        "        int byte = getchar();\n"
        f"        {output}\n"
        "        putchar(byte);\n"
        "        if (i % 2 == 0) {\n"
        "            continue;\n"
        "        }\n"
        "        putchar(getchar());\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class NestedAssignmentOutputCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, adapter, layout and VM required")

    def test_full_original_c_matches_binary_guest_oracle(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "full.c", root / "full.malbolge"
            path.write_text(source(), encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 13, 254, 7, 9, 11)),
                hashlib.shake_256(b"nested-C-output-assignment").digest(10),
            ):
                guest_run = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                self.assertEqual(guest_run.returncode, 0, guest_run.stderr)
                expected = bytes(
                    (
                        data[0],
                        data[1],
                        data[1],
                        data[3],
                        data[3],
                        data[5],
                        data[5],
                        data[6],
                        data[8],
                        data[8],
                        data[9],
                    )
                )
                self.assertEqual(guest_run.stdout, expected)
                self.assertEqual(guest_run.stderr, b"malbolge-steps-v1:22\n")

    def test_invalid_source_expressions_never_publish_guest(self) -> None:
        cases = (
            source(output="putchar(byte = getchar() + 1);"),
            source(output="putchar(byte == getchar());"),
            source(output="putchar(byte = putchar(getchar()));"),
            source(output="putchar(byte = getchar(), byte);"),
            source(
                output="putchar(byte = getchar());\n        getchar();\n        putchar(byte);"
            ),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, code in enumerate(cases):
                with self.subTest(index=index):
                    path = root / f"invalid-{index}.c"
                    guest = root / f"invalid-{index}.malbolge"
                    path.write_text(code, encoding="utf-8")
                    compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_selected_outer_loop_keeps_rebound_source_identity(self) -> None:
        """Every loop trip writes the current guest byte, even after continue."""
        program = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    putchar(current);\n"
            "    for (int i = 0; i < 3; ++i) {\n"
            "        if (i % 2 == 0) {\n"
            "            putchar(current = getchar());\n"
            "            continue;\n"
            "        }\n"
            "        putchar(current);\n"
            "    }\n"
            "    putchar(current);\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "outer.c", root / "outer.malbolge"
            path.write_text(program, encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1)),
                hashlib.shake_256(b"source-C-outer-loop-assign").digest(4),
            ):
                with self.subTest(data=data):
                    actual = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                    self.assertEqual(actual.returncode, 0, actual.stderr)
                    self.assertEqual(
                        actual.stdout,
                        bytes((data[0], data[1], data[1], data[2], data[2], data[3])),
                    )
                    self.assertEqual(actual.stderr, b"malbolge-steps-v1:11\n")

    def test_selected_branch_rebind_and_zero_trip_counted_loop(self) -> None:
        """A selected assignment exports C identity, but zero trips do not."""
        program = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    if (1) {\n"
            "        putchar(current = getchar());\n"
            "        putchar(current);\n"
            "    }\n"
            "    for (int i = 0; i < 0; ++i) {\n"
            "        putchar(current = getchar());\n"
            "    }\n"
            "    putchar(current);\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "zero.c", root / "zero.malbolge"
            path.write_text(program, encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128)),
                hashlib.shake_256(b"C-branch-expression").digest(3),
            ):
                actual = helpers.StaticForBreakCPipelineTests.vm(guest, data)
                self.assertEqual(actual.returncode, 0, actual.stderr)
                self.assertEqual(
                    actual.stdout, bytes((data[1], data[1], data[1], data[2]))
                )
                self.assertEqual(actual.stderr, b"malbolge-steps-v1:8\n")

    def test_pinned_assignment_node_mutations_reject(self) -> None:
        """Every nested operator, node identity and source span is checked."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "source.c"
            path.write_text(source(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            nodes = normalized["nodes"]
            assignment = next(
                n
                for n in nodes
                if n["kind"] == "binary-expression" and n["operation"] == "="
            )
            position = nodes.index(assignment)
            mutations = (
                (0, "operation", "+"),
                (0, "parent", 2),
                (0, "type", "u32"),
                (0, "reference", "other@1"),
                (1, "reference", "forged@1"),
                (1, "kind", "cast-expression"),
                (2, "reference", "external:putchar"),
                (2, "parent", 2),
                (3, "operation", "lvalue-to-rvalue"),
                (4, "reference", "external:putchar"),
            )
            for index, (offset, field, value) in enumerate(mutations):
                with self.subTest(index=index, field=field):
                    forged = copy.deepcopy(normalized)
                    forged["nodes"][position + offset][field] = value
                    guest = root / f"mutated-{index}.malbolge"
                    result = aliases.SourceLocalAliasCPipelineTests.adapter(
                        forged, guest, path
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())
            forged = copy.deepcopy(normalized)
            forged["nodes"][position]["span"]["begin"]["column"] += 1
            guest = root / "position.malbolge"
            result = aliases.SourceLocalAliasCPipelineTests.adapter(forged, guest, path)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(guest.exists())

    def test_missing_source_or_sha_adjusted_operator_forgery_refuses(self) -> None:
        """Typed shape alone cannot prove an equals sign in original C."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "source.c"
            program = source()
            path.write_text(program, encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(path)
            guest = root / "missing.malbolge"
            result = aliases.SourceLocalAliasCPipelineTests.adapter(
                normalized, guest, None
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(guest.exists())
            altered = root / "altered.c"
            altered.write_text(
                program.replace("byte = getchar()", "byte + getchar()"),
                encoding="utf-8",
            )
            forged = copy.deepcopy(normalized)
            forged["source"]["sha256"] = hashlib.sha256(
                altered.read_bytes()
            ).hexdigest()
            result = aliases.SourceLocalAliasCPipelineTests.adapter(
                forged, guest, altered
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(guest.exists())

    def test_stale_alias_cannot_be_resurrected_after_loop_rebind(self) -> None:
        """The guest has one resident byte; an old C alias needs storage."""
        program = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    int saved = current;\n"
            "    for (int i = 0; i < 2; ++i) {\n"
            "        putchar(current = getchar());\n"
            "        putchar(saved);\n"
            "    }\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest = root / "stale.c", root / "stale.malbolge"
            path.write_text(program, encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(path, guest)
            self.assertNotEqual(compiled.returncode, 0)
            self.assertFalse(guest.exists())


if __name__ == "__main__":
    unittest.main()
