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
#   - Exact successful C output-call returns initializing live guest locals.
# - Must-Not:
#   - Assume EOF, failed putchar, old C storage, or guest-dependent control.
# - Allows:
#   - Inputs: pinned Clang, original C, binary guest stdin.
#   - Outputs: normative guest parity and source/AST refusal.
#   - Side effects: isolated temporary guest artifacts only.
# - Split-When:
#   - General source-C expression lowering owns the same semantics.
# - Merge-When:
#   - Return-valued C declarations become a general expression grammar.
# - Summary:
#   - Guest output returns can initialize a new, source-proven live C local.

"""Exercise complete C streams whose declarations capture output returns."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests import test_source_local_alias_c_pipeline as aliases
from tests import test_static_for_break_c_pipeline as helpers
from tests.test_static_for_break_c_pipeline import ADAPTER, FRONTEND, LAYOUT, ROOT, VM


def program(*, initializer: str = "putchar(getchar())", trips: int = 4) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        f"    int current = {initializer};\n"
        f"    for (int i = 0; i < {trips}; ++i) {{\n"
        "        if (i % 3 == 0) {\n"
        "            putchar(current);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "        putchar(current);\n"
        "    }\n"
        "    current = putchar(getchar());\n"
        "    putchar(current);\n"
        "}\n"
    )


def scoped(*, selected: int = 1) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        f"    if ({selected}) {{\n"
        "        int scoped = putchar(putchar(getchar()));\n"
        "        putchar(scoped);\n"
        "    } else {\n"
        "        putchar(current);\n"
        "    }\n"
        "    for (int i = 0; i < 2; ++i) {\n"
        "        int trip = putchar(getchar());\n"
        "        putchar(trip);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class OutputReturnLocalInitializerCPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        if not all(tool.is_file() for tool in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned frontend, adapter, layout and VM required")

    def test_full_branch_continue_loop_binary_guest_parity(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source, target = root / "whole.c", root / "whole.malbolge"
            source.write_text(program(), encoding="utf-8")
            result = helpers.StaticForBreakCPipelineTests.compile(source, target)
            self.assertEqual(result.returncode, 0, result.stderr)
            streams = (
                bytes((0, 255)),
                bytes((255, 0)),
                bytes((128, 1)),
                *(
                    hashlib.shake_256(
                        b"local-output-initializer-" + bytes((seed,))
                    ).digest(2)
                    for seed in range(16)
                ),
            )
            for data in streams:
                with self.subTest(data=data):
                    guest = helpers.StaticForBreakCPipelineTests.vm(target, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(
                        guest.stdout,
                        bytes((*([data[0]] * 7), data[1], data[1])),
                    )
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:12\n")

    def test_nested_successful_returns_and_zero_trip(self) -> None:
        for depth, trips in ((3, 4), (1, 0)):
            with (
                self.subTest(depth=depth, trips=trips),
                tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory,
            ):
                root = Path(directory)
                source, target = root / "nested.c", root / "nested.malbolge"
                initializer = "putchar(" * depth + "getchar()" + ")" * depth
                source.write_text(
                    program(initializer=initializer, trips=trips),
                    encoding="utf-8",
                )
                compiled = helpers.StaticForBreakCPipelineTests.compile(source, target)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                for data in (
                    bytes((0, 255)),
                    hashlib.shake_256(b"nested-declaration").digest(2),
                ):
                    guest = helpers.StaticForBreakCPipelineTests.vm(target, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    first = depth + (6 if trips == 4 else 0)
                    self.assertEqual(
                        guest.stdout,
                        bytes((*([data[0]] * first), data[1], data[1])),
                    )
                    self.assertEqual(
                        guest.stderr,
                        f"malbolge-steps-v1:{first + 5}\n".encode(),
                    )

    def test_scoped_selected_branch_and_counted_loop_guest_parity(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for selected in (0, 1):
                with self.subTest(selected=selected):
                    source = root / f"scoped-{selected}.c"
                    target = root / f"scoped-{selected}.malbolge"
                    source.write_text(scoped(selected=selected), encoding="utf-8")
                    compiled = helpers.StaticForBreakCPipelineTests.compile(
                        source, target
                    )
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    count = 5 if selected else 4
                    for data in (
                        bytes((0, 255, 128, 1, 42))[:count],
                        hashlib.shake_256(
                            b"scoped-output-initializer-" + bytes((selected,))
                        ).digest(count),
                    ):
                        guest = helpers.StaticForBreakCPipelineTests.vm(target, data)
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        oracle = (
                            bytes(
                                (
                                    *([data[1]] * 3),
                                    *([data[2]] * 2),
                                    *([data[3]] * 2),
                                    data[4],
                                )
                            )
                            if selected
                            else bytes(
                                (data[0], *([data[1]] * 2), *([data[2]] * 2), data[3])
                            )
                        )
                        self.assertEqual(guest.stdout, oracle)
                        self.assertEqual(
                            guest.stderr,
                            f"malbolge-steps-v1:{count + len(oracle) + 1}\n".encode(),
                        )

    def test_unproved_initializers_refuse_before_publication(self) -> None:
        unsupported = (
            "putchar(getchar() + 1)",
            "putchar(putchar(getchar()) ^ 1)",
            "putchar(getchar(), getchar())",
            "putchar((unsigned char)getchar())",
            "putchar(putchar(getchar())) + 1",
            "fputc(getchar(), stdout)",
            "(putchar(getchar()), getchar() + 1)",
            "putchar(current)",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(unsupported):
                with self.subTest(expression=expression):
                    source = root / f"invalid-{index}.c"
                    target = root / f"invalid-{index}.malbolge"
                    source.write_text(program(initializer=expression), encoding="utf-8")
                    compiled = helpers.StaticForBreakCPipelineTests.compile(
                        source, target
                    )
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())

    def test_forged_clang_declaration_and_calls_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "original.c"
            source.write_text(program(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(source)
            mutations = (
                (3, "parent", 1),
                (3, "kind", "compound-statement"),
                (3, "operation", "="),
                (4, "reference", "stale@47"),
                (4, "name", "other"),
                (4, "type", "u32"),
                (4, "parent", 2),
                (5, "reference", "external:getchar"),
                (5, "parent", 2),
                (6, "operation", "integral-cast"),
                (6, "type", "ptr(fn()->i32)"),
                (7, "reference", "external:getchar"),
                (8, "parent", 4),
                (8, "reference", "external:putchar"),
                (9, "operation", "integral-cast"),
                (10, "reference", "external:putchar"),
            )
            for index, (node_id, field, value) in enumerate(mutations):
                with self.subTest(index=index):
                    modified = copy.deepcopy(normalized)
                    modified["nodes"][node_id - 1][field] = value
                    target = root / f"forged-{index}.malbolge"
                    compiled = aliases.SourceLocalAliasCPipelineTests.adapter(
                        modified, target, source
                    )
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())

            for index, (node_id, coordinate, amount) in enumerate(
                ((3, "end", 1), (4, "begin", 1), (5, "end", 1), (8, "begin", 1))
            ):
                with self.subTest(span=index):
                    modified = copy.deepcopy(normalized)
                    modified["nodes"][node_id - 1]["span"][coordinate]["byte"] += amount
                    target = root / f"span-{index}.malbolge"
                    compiled = aliases.SourceLocalAliasCPipelineTests.adapter(
                        modified, target, source
                    )
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())

            missing = root / "missing.malbolge"
            result = aliases.SourceLocalAliasCPipelineTests.adapter(
                normalized, missing, None
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(missing.exists())

    def test_source_witness_cannot_reinterpret_output_as_getchar(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "original.c"
            source.write_text(program(), encoding="utf-8")
            normalized = helpers.StaticForBreakCPipelineTests.normalized(source)
            forged = root / "forged.c"
            original = source.read_text(encoding="utf-8")
            altered = original.replace(
                "int current = putchar(getchar());",
                "int current = getchar();         ",
                1,
            )
            self.assertEqual(len(original), len(altered))
            forged.write_text(altered, encoding="utf-8")
            modified = copy.deepcopy(normalized)
            modified["source"]["sha256"] = hashlib.sha256(altered.encode()).hexdigest()
            target = root / "forged.malbolge"
            compiled = aliases.SourceLocalAliasCPipelineTests.adapter(
                modified, target, forged
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
