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
#   - Ordered guest effects in comma rebinding across a counted C loop.
# - Must-Not:
#   - Read a stale outer C byte after an unassigned guest input.
# - Allows:
#   - Inputs: authenticated Clang C, original source, binary VM stdin.
#   - Outputs: exact normative VM parity and closed compiler refusals.
#   - Side effects: isolated temporary test artifacts.
# - Split-When:
#   - General C storage proves these effects without source-time replay.
# - Merge-When:
#   - C loops share a general guest liveness analysis.
# - Summary:
#   - A discarded loop input may precede a proven outer-local rebind.

"""Real guest byte semantics for an outer C local rebound inside a loop."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_source_local_alias_c_pipeline as alias
from tests import test_static_for_break_c_pipeline as pipeline

ROOT = pipeline.ROOT
FRONTEND = pipeline.FRONTEND
ADAPTER = pipeline.ADAPTER
LAYOUT = pipeline.LAYOUT
VM = pipeline.VM
COMPILE = pipeline.StaticForBreakCPipelineTests.compile
RUN = pipeline.StaticForBreakCPipelineTests.vm
NORMALIZED = pipeline.StaticForBreakCPipelineTests.normalized
PROJECT = alias.SourceLocalAliasCPipelineTests.adapter


def original_program(bound: int = 2) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        "        current = (putchar(getchar()), getchar());\n"
        "        if (i % 2 == 0) {\n"
        "            putchar(current);\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class CommaReassignedLoopCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned Clang, adapter, layout and guest VM required")

    def test_outer_c_local_is_rebound_before_each_guest_use(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "outer.c"
            target = root / "outer.malbolge"
            source.write_text(original_program(), encoding="utf-8")
            compiled = COMPILE(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            inputs = (
                bytes((0, 255, 128, 31, 64, 90)),
                bytes((255, 0, 1, 2, 3, 4)),
                *(
                    hashlib.shake_256(b"outer-loop-comma-" + bytes((seed,))).digest(6)
                    for seed in range(16)
                ),
            )
            for data in inputs:
                with self.subTest(data=data):
                    guest = RUN(target, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, bytes(data[1:]))
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:12\n")

    def test_selected_and_skipped_inner_rebinding_keeps_outer_byte(self) -> None:
        program = original_program().replace(
            "        current = (putchar(getchar()), getchar());\n",
            "        if (i % 2 == 0) {\n"
            "            current = (putchar(getchar()), getchar());\n"
            "        }\n",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "selected.c"
            target = root / "selected.malbolge"
            source.write_text(program, encoding="utf-8")
            compiled = COMPILE(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255, 128, 42)), bytes((255, 0, 42, 128))):
                guest = RUN(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(
                    guest.stdout, bytes((data[1], data[2], data[2], data[3]))
                )
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:9\n")

    def test_zero_trip_loop_authenticates_but_skips_all_rebinding(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "zero.c"
            target = root / "zero.malbolge"
            source.write_text(original_program(bound=0), encoding="utf-8")
            compiled = COMPILE(source, target)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255)), bytes((255, 0))):
                guest = RUN(target, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data[1:])
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:4\n")

    def test_unbound_reads_and_unsupported_operands_refuse_publication(self) -> None:
        variants = (
            "current = (getchar(), putchar(current), getchar());",
            "getchar();\n        putchar(current);",
            "current = (getchar(), getchar() + 1);",
            "current = (getchar(), current);",
            "current = (getchar(), putchar(current));",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, statement in enumerate(variants):
                with self.subTest(statement=statement):
                    source = root / f"invalid-{index}.c"
                    target = root / f"invalid-{index}.malbolge"
                    source.write_text(
                        original_program().replace(
                            "current = (putchar(getchar()), getchar());",
                            statement,
                        ),
                        encoding="utf-8",
                    )
                    compiled = COMPILE(source, target)
                    self.assertNotEqual(compiled.returncode, 0)
                    self.assertFalse(target.exists())

    def test_original_source_and_clang_ancestry_are_required(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "outer.c"
            source.write_text(original_program(), encoding="utf-8")
            original = NORMALIZED(source)
            missing_target = root / "missing.malbolge"
            missing = PROJECT(original, missing_target, None)
            self.assertNotEqual(missing.returncode, 0)
            self.assertFalse(missing_target.exists())

            altered = original_program().replace(
                "(putchar(getchar()), getchar())",
                "(getchar()         , getchar())",
            )
            self.assertEqual(len(altered), len(original_program()))
            forged_source = root / "altered.c"
            forged_source.write_text(altered, encoding="utf-8")
            forged = copy.deepcopy(original)
            record = cast(dict[str, object], forged["source"])
            record["sha256"] = hashlib.sha256(altered.encode()).hexdigest()
            target = root / "source-spoof.malbolge"
            result = PROJECT(forged, target, forged_source)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())

            nodes = cast(list[dict[str, object]], original["nodes"])
            comma = next(
                node
                for node in nodes
                if node.get("operation") == "," and node["span"]["begin"]["line"] == 5
            )
            mutations: tuple[tuple[str, object], ...] = (
                ("operation", "+"),
                ("type", "u8"),
                ("parent", 2),
                ("reference", "current@0"),
            )
            for index, (field, value) in enumerate(mutations):
                with self.subTest(index=index):
                    modified = copy.deepcopy(original)
                    changed = cast(list[dict[str, object]], modified["nodes"])
                    changed[int(comma["id"]) - 1][field] = value
                    target = root / f"clang-spoof-{index}.malbolge"
                    result = PROJECT(modified, target, source)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
