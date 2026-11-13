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
#   - Prove original C output calls on both sides of a live-byte assignment.
# - Must-Not:
#   - Infer EOF, failed output, dynamic arithmetic or unproved C bindings.
# - Allows:
#   - Inputs: pinned Clang AST, original source, binary guest stdin.
#   - Outputs: normative VM parity and source/AST refusal.
#   - Side effects: disposable guest artifacts only.
# - Split-When:
#   - General C call-result lowering supersedes bounded source proof.
# - Merge-When:
#   - Successful output returns become one general expression grammar.
# - Summary:
#   - Bilateral successful output-return chains retain one live guest byte.

"""Prove full C output calls both outside and inside a byte assignment."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests import test_source_local_alias_c_pipeline as aliases
from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import ADAPTER, FRONTEND, LAYOUT, ROOT, VM

EXPRESSION = "putchar(putchar(current = putchar(getchar())));"


def program(expression: str = EXPRESSION, *, limit: int = 3) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        "    putchar(current);\n"
        f"    for (int i = 0; i < {limit}; ++i) {{\n"
        "        if (i % 2 == 0) {\n"
        f"            {expression}\n"
        "            putchar(current);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class BilateralOutputAssignmentCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C frontend, adapter, layout and VM required")

    def test_full_branch_loop_matches_seeded_binary_guest_oracles(self) -> None:
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
                    hashlib.shake_256(
                        b"bilateral-output-return-" + bytes((seed,))
                    ).digest(4)
                    for seed in range(16)
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
                                *([data[1]] * 5),
                                *([data[2]] * 4),
                                data[3],
                            )
                        ),
                    )
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:16\n")

    def test_top_level_both_sides_and_varying_call_depths(self) -> None:
        code = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    putchar(current = putchar(getchar()));\n"
            "    putchar(current);\n"
            "    putchar(putchar(current = putchar(putchar(getchar()))));\n"
            "    putchar(current);\n"
            "    putchar(getchar());\n"
            "}\n"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source, target = root / "top.c", root / "top.malbolge"
            source.write_text(code, encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1)),
                hashlib.shake_256(b"bilateral-top").digest(4),
            ):
                guest = helpers.StaticForBreakCPipelineTests.vm(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(
                    guest.stdout,
                    bytes((*([data[1]] * 3), *([data[2]] * 5), data[3])),
                )
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:14\n")

    def test_zero_trip_proves_but_skips_inner_guest_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source, target = root / "zero.c", root / "zero.malbolge"
            source.write_text(program(limit=0), encoding="utf-8")
            compiled = helpers.StaticForBreakCPipelineTests.compile(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255)),
                hashlib.shake_256(b"bilateral-zero").digest(2),
            ):
                guest = helpers.StaticForBreakCPipelineTests.vm(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:5\n")

    def test_unsupported_source_and_stale_c_alias_refuse(self) -> None:
        unsupported = (
            "putchar(putchar(current += putchar(getchar())));",
            "putchar(putchar(current == putchar(getchar())));",
            "putchar(putchar(current = putchar(getchar() + 1)));",
            "putchar(putchar(current = putchar(current)));",
            "putchar(putchar(current = putchar(getchar())) | 1);",
            "putchar(putchar(current = putchar(getchar()), getchar()));",
            "putchar(putchar(current = putchar(getchar())) + 1);",
        )
        stale = (
            "#include <stdio.h>\n"
            "void stream(void) {\n"
            "    int current = getchar();\n"
            "    int older = current;\n"
            f"    {EXPRESSION}\n"
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
                    compiled = helpers.StaticForBreakCPipelineTests.compile(
                        source, target
                    )
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_outer_inner_ancestry_and_spans_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "original.c"
            source.write_text(program(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(source)
            nodes = normalized["nodes"]
            outer = next(
                node
                for node in nodes
                if node["kind"] == "call-expression"
                and node["span"]["begin"]["line"] == 7
            )
            at = nodes.index(outer)
            edits = (
                (0, "parent", 2),
                (0, "reference", "external:getchar"),
                (1, "operation", "integral-cast"),
                (2, "reference", "external:getchar"),
                (3, "parent", 2),
                (4, "type", "ptr(fn()->i32)"),
                (5, "reference", "external:getchar"),
                (6, "operation", "+"),
                (6, "parent", 2),
                (7, "reference", "other@47"),
                (8, "reference", "external:getchar"),
                (9, "parent", 2),
                (10, "operation", "integral-cast"),
                (11, "reference", "external:putchar"),
                (12, "reference", "external:putchar"),
                (13, "operation", "integral-cast"),
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
            for offset in (0, 3, 6, 9, 12):
                for edge in ("begin", "end"):
                    forged = copy.deepcopy(normalized)
                    forged["nodes"][at + offset]["span"][edge]["column"] += 1
                    target = root / f"shift-{offset}-{edge}.malbolge"
                    result = aliases.SourceLocalAliasCPipelineTests.adapter(
                        forged, target, source
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())

    def test_missing_source_and_sha_adjusted_operator_spoof_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source, target = root / "original.c", root / "bad.malbolge"
            source.write_text(program(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(source)
            result = aliases.SourceLocalAliasCPipelineTests.adapter(
                normalized, target, None
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())
            changed = root / "changed.c"
            changed.write_text(
                program().replace("current = putchar", "current + putchar"),
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
