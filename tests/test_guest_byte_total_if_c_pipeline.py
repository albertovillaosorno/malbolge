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
#   - Source-proven successful-byte-total C if-statement selection.
# - Must-Not:
#   - Predict guest input or erase reachable side effects.
# - Allows:
#   - Inputs: pinned C/Clang evidence and successful binary guest input.
#   - Outputs: normative VM parity or fail-closed refusal.
#   - Side effects: isolated temporary guest artifacts only.
# - Split-When:
#   - General dynamic C branches execute under guest semantics.
# - Merge-When:
#   - Typed byte interval analysis owns conditional control flow.
# - Summary:
#   - Prove a total live-byte guard before choosing a C statement arm.
# - Description:
#   - Verify guest branch effects and source/Clang integrity.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Inconclusive guards and forged provenance refuse publication.

"""Whole C-to-Malbolge proof of byte-total conditional statements."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_guest_byte_wide_range_conditional_c_pipeline as previous

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
    guard: str = "current < 256",
    *,
    reverse: bool = False,
    bound: int = 3,
) -> str:
    """Real induction, selected continue, nested branch and binary effects."""
    first = "putchar(getchar());" if reverse else "putchar(current);"
    second = "putchar(current);" if reverse else "putchar(getchar());"
    return (
        "#include <stdio.h>\n"
        "void stream(void) {\n"
        "    int current = getchar();\n"
        f"    for (int i = 0; i < {bound}; ++i) {{\n"
        "        if (i % 2 == 0) {\n"
        f"            if ({guard}) {{\n"
        f"                {first}\n"
        "            } else {\n"
        f"                {second}\n"
        "            }\n"
        "            continue;\n"
        "        }\n"
        "        putchar(current);\n"
        "    }\n"
        "    putchar(current);\n"
        "    putchar(getchar());\n"
        "}\n"
    )


class GuestByteTotalIfCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned C compiler and normative VM tools required")

    def test_nested_branch_and_continue_match_binary_guest(self) -> None:
        """A total guard selects real output and skips the other input."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "live-if.c"
            guest = root / "live-if.malbolge"
            _ = program.write_text(source(), encoding="utf-8")
            compiled = COMPILE(program, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            boundaries = (
                bytes((0, 255)),
                bytes((1, 254)),
                bytes((127, 128)),
                bytes((255, 0)),
            )
            # jig-ignore-next-line: pinned Ruff uses 88-column formatting
            seeded = (hashlib.shake_256(bytes((241, i))).digest(2) for i in range(12))
            for data in (*boundaries, *seeded):
                with self.subTest(data=data):
                    vm = RUN(guest, data)
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    expected = bytes((data[0],) * 4 + (data[1],))
                    self.assertEqual(vm.stdout, expected)
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:8\n")

    def test_false_total_guard_selects_else_with_no_extra_read(self) -> None:
        """The false branch is real C control, not ternary expression data."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "false-if.c"
            guest = root / "false-if.malbolge"
            _ = program.write_text(
                source("current >= 256", reverse=True), encoding="utf-8"
            )
            compiled = COMPILE(program, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255)), bytes((255, 0))):
                vm = RUN(guest, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, bytes((data[0],) * 4 + (data[1],)))
                self.assertEqual(vm.stderr, b"malbolge-steps-v1:8\n")

    def test_false_mask_without_else_skips_guest_input(self) -> None:
        """A fully skipped C statement cannot consume the nested read."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "skipped-if.c"
            guest = root / "skipped-if.malbolge"
            first = (
                "            if (current & 256) {\n"
                "                putchar(current);\n"
                "            } else {\n"
                "                putchar(getchar());\n"
                "            }"
            )
            replacement = (
                "            if (current & 256) {\n"
                "                putchar(getchar());\n"
                "            }"
            )
            original = source("current & 256")
            self.assertIn(first, original)
            _ = program.write_text(
                original.replace(first, replacement), encoding="utf-8"
            )
            compiled = COMPILE(program, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255)), bytes((255, 0)), bytes((33, 89))):
                vm = RUN(guest, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, bytes((data[0],) * 2 + (data[1],)))
                self.assertEqual(vm.stderr, b"malbolge-steps-v1:6\n")

    def test_compound_total_guards_match_binary_guest(self) -> None:
        """Pure C short-circuit conditions choose a full live-byte arm."""
        guards = (
            ("current >= 0 && current <= 255", False),
            ("current < 0 || current >= 256", True),
            ("current & 256 || current < 256", False),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (guard, reverse) in enumerate(guards):
                with self.subTest(guard=guard):
                    program = root / f"compound-{index}.c"
                    guest = root / f"compound-{index}.malbolge"
                    _ = program.write_text(
                        source(guard, reverse=reverse), encoding="utf-8"
                    )
                    compiled = COMPILE(program, guest)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in (
                        bytes((0, 255)),
                        bytes((255, 0)),
                        bytes((1, 254)),
                        *(
                            hashlib.shake_256(bytes((247, i))).digest(2)
                            for i in range(8)
                        ),
                    ):
                        with self.subTest(data=data):
                            vm = RUN(guest, data)
                            self.assertEqual(vm.returncode, 0, vm.stderr)
                            self.assertEqual(
                                vm.stdout, bytes((data[0],) * 4 + (data[1],))
                            )
                            self.assertEqual(vm.stderr, b"malbolge-steps-v1:8\n")

    def test_nested_compound_predicates_match_guest(self) -> None:
        """Precedence must follow pinned C syntax, not host byte guesses."""
        guards = (
            ("current >= 0 && current <= 255 || current > 255", False),
            ("current < 0 || current >= 256 && current <= 255", True),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, (guard, reverse) in enumerate(guards):
                with self.subTest(guard=guard):
                    program = root / f"nested-{index}.c"
                    guest = root / f"nested-{index}.malbolge"
                    _ = program.write_text(
                        source(guard, reverse=reverse), encoding="utf-8"
                    )
                    compiled = COMPILE(program, guest)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    for data in (
                        bytes((0, 255)),
                        bytes((255, 0)),
                        *(
                            hashlib.shake_256(bytes((249, i))).digest(2)
                            for i in range(4)
                        ),
                    ):
                        vm = RUN(guest, data)
                        self.assertEqual(vm.returncode, 0, vm.stderr)
                        self.assertEqual(vm.stdout, bytes((data[0],) * 4 + (data[1],)))
                        self.assertEqual(vm.stderr, b"malbolge-steps-v1:8\n")

    def test_false_compound_if_without_else_skips_input(self) -> None:
        """Short-circuiting cannot consume a skipped C input call."""
        guard = "current < 0 || current >= 256"
        original = source(guard)
        first = (
            f"            if ({guard}) {{\n"
            "                putchar(current);\n"
            "            } else {\n"
            "                putchar(getchar());\n"
            "            }"
        )
        replacement = (
            f"            if ({guard}) {{\n"
            "                putchar(getchar());\n"
            "            }"
        )
        self.assertIn(first, original)
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "no-else.c"
            guest = root / "no-else.malbolge"
            _ = program.write_text(
                original.replace(first, replacement), encoding="utf-8"
            )
            compiled = COMPILE(program, guest)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            for data in (bytes((0, 255)), bytes((255, 0))):
                vm = RUN(guest, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, bytes((data[0],) * 2 + (data[1],)))
                self.assertEqual(vm.stderr, b"malbolge-steps-v1:6\n")

    def test_non_total_and_effectful_compound_guards_refuse(self) -> None:
        """No host-side optimization may discard impure short circuits."""
        invalid = (
            "current > 0 && current <= 255",
            "current < 0 || current == 255",
            "current >= 0 && current <= 254",
            "current >= 0 && getchar() >= 0",
            "current < 0 && getchar() >= 0",
            "putchar(current) >= 0 || current <= 255",
            "current >= 0 || current > 0",
            "current >= 0 & current <= 255",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, guard in enumerate(invalid):
                with self.subTest(guard=guard):
                    program = root / f"invalid-compound-{index}.c"
                    guest = root / f"invalid-compound-{index}.malbolge"
                    _ = program.write_text(source(guard), encoding="utf-8")
                    result = COMPILE(program, guest)
                    self.assertNotEqual(result.returncode, 0, guard)
                    self.assertFalse(guest.exists())

    def test_forged_compound_guards_refuse(self) -> None:
        """Every Clang operand, operator and source byte is authenticated."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "valid-compound.c"
            original = source("current >= 0 && current <= 255")
            _ = program.write_text(original, encoding="utf-8")
            normalized = NORMALIZED(program)
            for field in ("operation", "parent", "span", "literal"):
                with self.subTest(field=field):
                    forged = copy.deepcopy(normalized)
                    nodes = cast("list[dict[str, object]]", forged["nodes"])
                    if field == "operation":
                        node = next(n for n in nodes if n.get("operation") == "&&")
                        node[field] = "||"
                    else:
                        node = next(n for n in nodes if n.get("literal") == "255")
                        if field == "parent":
                            node[field] = 0
                        elif field == "literal":
                            node[field] = "254"
                        else:
                            extent = cast("dict[str, dict[str, int]]", node[field])
                            extent["begin"]["column"] += 1
                    guest = root / f"forged-compound-{field}.malbolge"
                    result = PROJECT(forged, guest, program)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())
            changed = root / "changed-compound.c"
            _ = changed.write_text(original.replace(" && ", " || "), encoding="utf-8")
            forged = copy.deepcopy(normalized)
            record = cast("dict[str, object]", forged["source"])
            record["sha256"] = hashlib.sha256(changed.read_bytes()).hexdigest()
            guest = root / "changed-compound.malbolge"
            self.assertNotEqual(PROJECT(forged, guest, changed).returncode, 0)
            self.assertFalse(guest.exists())
            guest = root / "missing-compound.malbolge"
            self.assertNotEqual(PROJECT(normalized, guest, None).returncode, 0)
            self.assertFalse(guest.exists())

    def test_non_total_and_effectful_conditions_refuse(self) -> None:
        """A guard that can change at a successful byte cannot be folded."""
        invalid = (
            "current < 255",
            "current <= 254",
            "current > 0",
            "current >= 1",
            "current == 0",
            "current & 255",
            "current & 257",
            "getchar() < 256",
            "putchar(current) < 256",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, guard in enumerate(invalid):
                with self.subTest(guard=guard):
                    program = root / f"refuse-{index}.c"
                    guest = root / f"refuse-{index}.malbolge"
                    _ = program.write_text(source(guard), encoding="utf-8")
                    result = COMPILE(program, guest)
                    self.assertNotEqual(result.returncode, 0, guard)
                    self.assertFalse(guest.exists())

    def test_forged_clang_and_original_source_refuse(self) -> None:
        """The guard must bind exact original source and pinned AST nodes."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            program = root / "original.c"
            original = source()
            _ = program.write_text(original, encoding="utf-8")
            normalized = NORMALIZED(program)
            for field, value in (
                ("literal", "255"),
                ("constant_integer", "255"),
                ("operation", ">"),
            ):
                with self.subTest(field=field):
                    forged = copy.deepcopy(normalized)
                    nodes = cast("list[dict[str, object]]", forged["nodes"])
                    if field == "operation":
                        # jig-ignore-next-line: pinned Ruff uses 88 columns
                        node = next(n for n in nodes if n.get("operation") == "<")
                    else:
                        # jig-ignore-next-line: pinned Ruff uses 88 columns
                        node = next(n for n in nodes if n.get("literal") == "256")
                    node[field] = value
                    guest = root / f"forged-{field}.malbolge"
                    result = PROJECT(forged, guest, program)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())
            for field in ("parent", "span"):
                with self.subTest(field=field):
                    forged = copy.deepcopy(normalized)
                    nodes = cast("list[dict[str, object]]", forged["nodes"])
                    node = next(n for n in nodes if n.get("literal") == "256")
                    if field == "parent":
                        node[field] = 0
                    else:
                        extent = cast("dict[str, dict[str, int]]", node[field])
                        extent["begin"]["column"] += 1
                    guest = root / f"forged-{field}.malbolge"
                    result = PROJECT(forged, guest, program)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())
            changed = root / "modified.c"
            _ = changed.write_text(
                original.replace("current < 256", "current < 257"),
                encoding="utf-8",
            )
            forged = copy.deepcopy(normalized)
            record = cast("dict[str, object]", forged["source"])
            record["sha256"] = hashlib.sha256(changed.read_bytes()).hexdigest()
            guest = root / "modified.malbolge"
            self.assertNotEqual(PROJECT(forged, guest, changed).returncode, 0)
            self.assertFalse(guest.exists())
            guest = root / "missing.malbolge"
            self.assertNotEqual(PROJECT(normalized, guest, None).returncode, 0)
            self.assertFalse(guest.exists())


if __name__ == "__main__":
    _ = unittest.main()
