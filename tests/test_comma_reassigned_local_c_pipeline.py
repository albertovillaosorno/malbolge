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
#   - C comma-valued reassignment with ordered real guest byte effects.
# - Must-Not:
#   - Fold discarded C reads or invent prior C storage after guest input.
# - Allows:
#   - Inputs: authenticated pinned Clang C and binary VM stdin.
#   - Outputs: exact normative guest parity and closed compiler refusals.
#   - Side effects: isolated .temp artifacts only.
# - Split-When:
#   - General C expression lowering subsumes comma-valued assignment.
# - Merge-When:
#   - C local assignment shares a general source-proven expression evaluator.
# - Summary:
#   - Rebinding a source-proven C local retains the final comma result.

"""A comma-valued C reassignment executes its whole guest effect trace."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_source_local_alias_c_pipeline as alias
from tests import test_static_for_break_c_pipeline as pipeline

ADAPTER = pipeline.ADAPTER
FRONTEND = pipeline.FRONTEND
LAYOUT = pipeline.LAYOUT
ROOT = pipeline.ROOT
VM = pipeline.VM
COMPILE = pipeline.StaticForBreakCPipelineTests.compile
RUN = pipeline.StaticForBreakCPipelineTests.vm


def whole_program() -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        "    if (1) {\n"
        "        current = (putchar(getchar()), getchar());\n"
        "        putchar(current);\n"
        "    }\n"
        "    for (int i = 0; i < 3; ++i) {\n"
        "        if (i % 2 == 0) {\n"
        "            putchar(current);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class CommaReassignedLocalCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned Clang, adapter, layout and VM required")

    def test_complete_branch_continue_binary_guest_parity(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source, target = root / "whole.c", root / "whole.malbolge"
            _ = source.write_text(whole_program(), encoding="utf-8")
            compiled = COMPILE(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 3)),
                bytes((255, 0, 128, 42)),
                *(
                    hashlib.shake_256(b"comma-rebind-" + bytes((i,))).digest(4)
                    for i in range(12)
                ),
            ):
                with self.subTest(data=data):
                    guest = RUN(target, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(
                        guest.stdout,
                        bytes(data[index] for index in (1, 2, 2, 2, 2, 3)),
                    )
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:11\n")

    def test_skipped_branch_does_not_consume_comma_inputs(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source, target = root / "skipped.c", root / "skipped.malbolge"
            _ = source.write_text(
                whole_program().replace("if (1) {", "if (0) {"),
                encoding="utf-8",
            )
            compiled = COMPILE(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255)), bytes((255, 128))):
                guest = RUN(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, bytes((data[0],) * 3 + (data[1],)))
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:7\n")

    def test_stale_destination_rebinds_final_successful_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source, target = root / "stale.c", root / "stale.malbolge"
            _ = source.write_text(
                "#include <stdio.h>\n"
                "void stream(void) {\n"
                "    int current = getchar();\n"
                "    int other = getchar();\n"
                "    current = (getchar(), putchar(putchar(getchar())), getchar());\n"
                "    putchar(current);\n"
                "    putchar(getchar());\n"
                "}\n",
                encoding="utf-8",
            )
            compiled = COMPILE(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 3, 7, 42)),
                hashlib.shake_256(b"comma-rebind-stale").digest(6),
            ):
                guest = RUN(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(
                    guest.stdout, bytes((data[3], data[3], data[4], data[5]))
                )
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:11\n")

    def test_unsupported_comma_assignments_refuse_publication(self) -> None:
        variants = (
            "(getchar(), getchar() + 1)",
            "(getchar(), 42)",
            "(getchar(), current)",
            "(putchar(getchar()) + 1, getchar())",
            "(fputc(getchar(), stdout), getchar())",
            "(getchar(), getchar(), current)",
            "((unsigned char)getchar(), getchar())",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(variants):
                with self.subTest(expression=expression):
                    source = root / f"invalid-{index}.c"
                    target = root / f"invalid-{index}.malbolge"
                    _ = source.write_text(
                        whole_program().replace(
                            "(putchar(getchar()), getchar())", expression
                        ),
                        encoding="utf-8",
                    )
                    compiled = COMPILE(source, target)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())

    def test_missing_and_spoofed_c_source_refuse_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "original.c"
            _ = source.write_text(whole_program(), encoding="utf-8")
            normalized = pipeline.StaticForBreakCPipelineTests.normalized(source)
            project = alias.SourceLocalAliasCPipelineTests.adapter
            missing_target = root / "missing.malbolge"
            missing = project(normalized, missing_target, None)
            self.assertNotEqual(missing.returncode, 0)
            self.assertFalse(missing_target.exists())

            altered = whole_program().replace(
                "(putchar(getchar()), getchar())",
                "(getchar()         , getchar())",
            )
            self.assertEqual(len(altered), len(whole_program()))
            forged_source = root / "altered.c"
            _ = forged_source.write_text(altered, encoding="utf-8")
            forged = copy.deepcopy(normalized)
            source_record = cast(dict[str, object], forged["source"])
            source_record["sha256"] = hashlib.sha256(altered.encode()).hexdigest()
            target = root / "sha-adjusted.malbolge"
            result = project(forged, target, forged_source)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())

    def test_forged_clang_comma_assignment_nodes_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "original.c"
            _ = source.write_text(whole_program(), encoding="utf-8")
            original = pipeline.StaticForBreakCPipelineTests.normalized(source)
            nodes = cast(list[dict[str, object]], original["nodes"])
            assignment = next(
                node
                for node in nodes
                if node["kind"] == "binary-expression"
                and node.get("operation") == "="
                and node["span"]["begin"]["line"] == 5
            )
            base = int(assignment["id"])
            mutations: tuple[tuple[int, str, object], ...] = (
                (0, "operation", ","),
                (0, "type", "u8"),
                (1, "reference", "current@0"),
                (1, "parent", 2),
                (2, "parent", 2),
                (2, "kind", "cast-expression"),
                (3, "operation", "+"),
                (3, "parent", 2),
                (4, "reference", "external:getchar"),
                (5, "parent", 2),
                (7, "reference", "external:putchar"),
                (10, "parent", 2),
            )
            for index, (delta, field, value) in enumerate(mutations):
                with self.subTest(delta=delta, field=field):
                    forged = copy.deepcopy(original)
                    forged_nodes = cast(list[dict[str, object]], forged["nodes"])
                    forged_nodes[base + delta - 1][field] = value
                    target = root / f"ast-{index}.malbolge"
                    result = alias.SourceLocalAliasCPipelineTests.adapter(
                        forged, target, source
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())
