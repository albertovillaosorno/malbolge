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
#   - Comma operands that output and rebind a proven input local.
# - Must-Not:
#   - Hide guest input, reconstruct stale locals, or forge C semantics.
# - Allows:
#   - Inputs: pinned source C, normalized Clang and binary guest stdin.
#   - Outputs: normative Malbolge parity or fail-closed refusal.
#   - Side effects: isolated temporary artifacts only.
# - Split-When:
#   - General guest C expression evaluation replaces bounded proofs.
# - Merge-When:
#   - Source comma operand effects share a general typed guest SSA.
# - Summary:
#   - A nested comma putchar assignment can rebind the resident byte.
# - Description:
#   - Complete C loop, branch, continue and real guest I/O regression.
# - Usage:
#   - Run test_comma_nested_assignment_output_c_pipeline.
# - Defaults:
#   - No production I/O or filesystem state.

"""C comma-sequenced output assignment executes genuine guest effects."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_comma_output_return_rebinding_c_pipeline as previous

ROOT = previous.ROOT
FRONTEND = previous.FRONTEND
ADAPTER = previous.ADAPTER
LAYOUT = previous.LAYOUT
VM = previous.VM
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT


def source(
    *,
    bound: int = 3,
    expression: str = "current = getchar(), putchar(current = getchar()), current",
) -> str:
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        "        if (i % 2 == 0) {\n"
        f"            putchar(({expression}));\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        "    putchar(current);\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class CommaNestedAssignmentOutputCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler pipeline and normative VM required")

    def test_complete_source_rebinds_inside_comma_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest_path = root / "stream.c", root / "stream.malbolge"
            path.write_text(source(), encoding="utf-8")
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            samples = (
                bytes((0, 255, 128, 1, 42, 0)),
                bytes((255, 0, 1, 128, 0, 255)),
                *(hashlib.shake_256(bytes((51, i))).digest(6) for i in range(12)),
            )
            for data in samples:
                with self.subTest(data=data):
                    actual = RUN(guest_path, data)
                    self.assertEqual(actual.returncode, 0, actual.stderr)
                    self.assertEqual(
                        actual.stdout,
                        bytes(
                            (
                                data[2],
                                data[2],
                                data[2],
                                data[4],
                                data[4],
                                data[4],
                                data[5],
                            )
                        ),
                    )
                    self.assertEqual(actual.stderr, b"malbolge-steps-v1:14\n")

    def test_last_comma_operand_rebinds_after_nested_output(self) -> None:
        expression = "current = getchar(), putchar(current = getchar())"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest_path = root / "last.c", root / "last.malbolge"
            path.write_text(source(expression=expression), encoding="utf-8")
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 0)),
                bytes((255, 0, 1, 128, 0, 255)),
                *(hashlib.shake_256(bytes((52, i))).digest(6) for i in range(4)),
            ):
                with self.subTest(data=data):
                    actual = RUN(guest_path, data)
                    self.assertEqual(actual.returncode, 0, actual.stderr)
                    self.assertEqual(
                        actual.stdout,
                        bytes(
                            (
                                data[2],
                                data[2],
                                data[2],
                                data[4],
                                data[4],
                                data[4],
                                data[5],
                            )
                        ),
                    )
                    self.assertEqual(actual.stderr, b"malbolge-steps-v1:14\n")

    def test_final_comma_output_reuses_the_rebound_byte(self) -> None:
        expression = (
            "current = getchar(), putchar(current = getchar()), putchar(current)"
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest_path = root / "middle.c", root / "middle.malbolge"
            path.write_text(source(expression=expression), encoding="utf-8")
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1, 42, 0)),
                bytes((255, 0, 1, 128, 0, 255)),
                *(hashlib.shake_256(bytes((53, i))).digest(6) for i in range(4)),
            ):
                with self.subTest(data=data):
                    actual = RUN(guest_path, data)
                    self.assertEqual(actual.returncode, 0, actual.stderr)
                    self.assertEqual(
                        actual.stdout,
                        bytes(
                            (
                                data[2],
                                data[2],
                                data[2],
                                data[2],
                                data[4],
                                data[4],
                                data[4],
                                data[4],
                                data[5],
                            )
                        ),
                    )
                    self.assertEqual(actual.stderr, b"malbolge-steps-v1:16\n")

    def test_zero_and_single_trip_have_no_skipped_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for bound, expected, steps in (
                (0, (0, 1), 5),
                (1, (2, 2, 2, 3), 9),
            ):
                with self.subTest(bound=bound):
                    path = root / f"loop-{bound}.c"
                    guest_path = root / f"loop-{bound}.malbolge"
                    path.write_text(source(bound=bound), encoding="utf-8")
                    compiled = COMPILE(path, guest_path)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in (
                        bytes((0, 255, 128, 1)),
                        bytes((255, 0, 1, 128)),
                    ):
                        actual = RUN(guest_path, data)
                        self.assertEqual(actual.returncode, 0, actual.stderr)
                        self.assertEqual(
                            actual.stdout, bytes(data[i] for i in expected)
                        )
                        self.assertEqual(
                            actual.stderr,
                            f"malbolge-steps-v1:{steps}\n".encode(),
                        )

    def test_unsupported_effects_and_stale_local_refuse(self) -> None:
        expressions = (
            "current = getchar(), putchar(current + getchar()), current",
            "current = getchar(), putchar(current == getchar()), current",
            "current = getchar(), putchar(current = getchar() + 1), current",
            "current = getchar(), putchar(current += getchar()), current",
            "current = getchar(), putchar((current = getchar())), current",
            "current = getchar(), putchar(current = getchar()), getchar(), current",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(expressions):
                with self.subTest(expression=expression):
                    path = root / f"invalid-{index}.c"
                    guest_path = root / f"invalid-{index}.malbolge"
                    path.write_text(source(expression=expression), encoding="utf-8")
                    result = COMPILE(path, guest_path)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest_path.exists())

    def test_forged_clang_parentage_and_source_proof_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "valid.c"
            path.write_text(source(), encoding="utf-8")
            normalized = NORMALIZED(path)
            nodes = cast(list[dict[str, object]], normalized["nodes"])
            for index, node in enumerate(nodes):
                span = cast(dict[str, dict[str, int]], node["span"])
                if span["begin"]["line"] != 6:
                    continue
                with self.subTest(parent=node["id"]):
                    forged = copy.deepcopy(normalized)
                    changed = cast(list[dict[str, object]], forged["nodes"])
                    changed[index]["parent"] = 2
                    target = root / f"parent-{index}.malbolge"
                    rejected = PROJECT(forged, target, path)
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertFalse(target.exists())
                with self.subTest(span=node["id"]):
                    forged = copy.deepcopy(normalized)
                    changed = cast(list[dict[str, object]], forged["nodes"])
                    extent = cast(dict[str, dict[str, int]], changed[index]["span"])
                    extent["begin"]["column"] += 1
                    target = root / f"span-{index}.malbolge"
                    rejected = PROJECT(forged, target, path)
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertFalse(target.exists())
            missing = root / "without-source.malbolge"
            rejected = PROJECT(normalized, missing, None)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(missing.exists())
            original = "putchar(current = getchar())"
            for index, replacement in enumerate(
                (
                    "putchar(current + getchar())",
                    "putchar(currenz = getchar())",
                )
            ):
                with self.subTest(replacement=replacement):
                    alternate = root / f"spoof-{index}.c"
                    alternate.write_text(
                        source().replace(original, replacement),
                        encoding="utf-8",
                    )
                    forged = copy.deepcopy(normalized)
                    cast(dict[str, object], forged["source"])["sha256"] = (
                        hashlib.sha256(alternate.read_bytes()).hexdigest()
                    )
                    target = root / f"spoof-{index}.malbolge"
                    rejected = PROJECT(forged, target, alternate)
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertFalse(target.exists())
