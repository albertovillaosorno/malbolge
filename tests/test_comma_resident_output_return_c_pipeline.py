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
#   - Source-proven rebindings from successful outputs of a resident C byte.
# - Must-Not:
#   - Resurrect a stale local, invent a guest read, or skip guest writes.
# - Allows:
#   - Inputs: pinned C frontend, authenticated AST and binary guest input.
#   - Outputs: normative Malbolge parity or fail-closed refusal.
#   - Side effects: isolated temporary compiler artifacts only.
# - Split-When:
#   - General guest SSA replaces source-shape proofs.
# - Merge-When:
#   - All comma effect assignments share a typed value-liveness model.
# - Summary:
#   - Successful putchar(local) return retains the live guest byte.

"""Whole-C and normative VM evidence for live-byte output-return assignment."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_comma_nested_assignment_output_c_pipeline as previous

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
    depth: int = 1,
    expression: str | None = None,
) -> str:
    assignment = "current = " + "putchar(" * depth + "current" + ")" * depth
    actual = expression if expression is not None else assignment + ", current"
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        "        if (i % 2 == 0) {\n"
        f"            putchar(({actual}));\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        "    putchar(current);\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class CommaResidentOutputReturnCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler stages and normative VM required")

    def test_complete_loop_rebinds_successful_resident_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest_path = root / "resident.c", root / "resident.malbolge"
            path.write_text(source(), encoding="utf-8")
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255)),
                bytes((255, 0)),
                *(hashlib.shake_256(bytes((61, i))).digest(2) for i in range(12)),
            ):
                with self.subTest(data=data):
                    guest = RUN(guest_path, data)
                    self.assertEqual(guest.returncode, 0, guest.stderr)
                    self.assertEqual(guest.stdout, bytes((data[0],) * 6 + (data[1],)))
                    self.assertEqual(guest.stderr, b"malbolge-steps-v1:10\n")

    def test_nested_returns_and_final_assignment_do_not_read_again(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for depth, expression, count in (
                (2, None, 8),
                (1, "current, current = putchar(current)", 6),
            ):
                with self.subTest(depth=depth, expression=expression):
                    path = root / f"nested-{depth}-{count}.c"
                    guest_path = root / f"nested-{depth}-{count}.malbolge"
                    path.write_text(
                        source(depth=depth, expression=expression), encoding="utf-8"
                    )
                    compiled = COMPILE(path, guest_path)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in (bytes((0, 255)), bytes((255, 0))):
                        guest = RUN(guest_path, data)
                        self.assertEqual(guest.returncode, 0, guest.stderr)
                        self.assertEqual(
                            guest.stdout, bytes((data[0],) * count + (data[1],))
                        )
                        self.assertEqual(
                            guest.stderr,
                            f"malbolge-steps-v1:{count + 4}\n".encode(),
                        )

    def test_new_read_then_resident_return_preserves_new_binding(self) -> None:
        expression = "current = getchar(), current = putchar(current), current"
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest_path = root / "fresh.c", root / "fresh.malbolge"
            path.write_text(source(expression=expression), encoding="utf-8")
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (
                bytes((0, 255, 128, 1)),
                bytes((255, 0, 1, 128)),
                *(hashlib.shake_256(bytes((62, i))).digest(4) for i in range(12)),
            ):
                guest = RUN(guest_path, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(
                    guest.stdout,
                    bytes((data[1],) * 3 + (data[2],) * 3 + (data[3],)),
                )
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:12\n")

    def test_zero_trip_skips_resident_output_effects(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path, guest_path = root / "zero.c", root / "zero.malbolge"
            path.write_text(source(bound=0), encoding="utf-8")
            compiled = COMPILE(path, guest_path)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255)), bytes((255, 0))):
                guest = RUN(guest_path, data)
                self.assertEqual(guest.returncode, 0, guest.stderr)
                self.assertEqual(guest.stdout, data)
                self.assertEqual(guest.stderr, b"malbolge-steps-v1:5\n")

    def test_unsupported_and_stale_local_effects_refuse(self) -> None:
        expressions = (
            "current = putchar(current + 1), current",
            "current = putchar(getchar()), current = putchar(current + 1)",
            "getchar(), current = putchar(current), current",
            "current = putchar(current) + 1, current",
            "current += putchar(current), current",
            "current == putchar(current), current",
            "current = putchar((current)), current",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, expression in enumerate(expressions):
                with self.subTest(expression=expression):
                    path, guest_path = (
                        root / f"invalid-{index}.c",
                        root / f"invalid-{index}.malbolge",
                    )
                    path.write_text(source(expression=expression), encoding="utf-8")
                    rejected = COMPILE(path, guest_path)
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertFalse(guest_path.exists())

    def test_ast_and_original_c_forgeries_refuse(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            path = root / "original.c"
            path.write_text(source(), encoding="utf-8")
            normalized = NORMALIZED(path)
            nodes = cast(list[dict[str, object]], normalized["nodes"])
            for index, node in enumerate(nodes):
                span = cast(dict[str, dict[str, int]], node["span"])
                if span["begin"]["line"] != 6:
                    continue
                for field in ("parent", "span"):
                    with self.subTest(node=node["id"], field=field):
                        forged = copy.deepcopy(normalized)
                        changed = cast(list[dict[str, object]], forged["nodes"])
                        if field == "parent":
                            changed[index]["parent"] = 2
                        else:
                            extent = cast(
                                dict[str, dict[str, int]], changed[index]["span"]
                            )
                            extent["begin"]["column"] += 1
                        target = root / f"{field}-{index}.malbolge"
                        rejected = PROJECT(forged, target, path)
                        self.assertNotEqual(rejected.returncode, 0)
                        self.assertFalse(target.exists())
            target = root / "missing.malbolge"
            rejected = PROJECT(normalized, target, None)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertFalse(target.exists())
            for index, (original, substitute) in enumerate(
                (
                    ("current = putchar(current)", "current + putchar(current)"),
                    ("current = putchar(current)", "currenz = putchar(current)"),
                    ("putchar(current)", "putchar(currenz)"),
                )
            ):
                alternate = root / f"spoof-{index}.c"
                alternate.write_text(source().replace(original, substitute), encoding="utf-8")
                forged = copy.deepcopy(normalized)
                cast(dict[str, object], forged["source"])["sha256"] = (
                    hashlib.sha256(alternate.read_bytes()).hexdigest()
                )
                target = root / f"spoof-{index}.malbolge"
                rejected = PROJECT(forged, target, alternate)
                self.assertNotEqual(rejected.returncode, 0)
                self.assertFalse(target.exists())
