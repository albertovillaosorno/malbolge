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
#   - Exact source-backed arithmetic on protected static C loop counters.
# - Must-Not:
#   - Evaluate guest input on the host or trust forged operators and literals.
# - Allows:
#   - Inputs: pinned Clang, complete source C and runtime binary guest input.
#   - Outputs: genuine Malbolge bytes or refusal before artifact publication.
#   - Side effects: temporary test artifacts only.
# - Split-When:
#   - Generic guest arithmetic replaces compiler-time induction projection.
# - Merge-When:
#   - Induction and constant expression lowering share typed proof rules.
# - Summary:
#   - Verify finite i32 loop arithmetic and branch-dependent guest traces.
# - Description:
#   - Cover break selection, arithmetic operations and forged source or AST.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Overflow, division by zero and unproven ancestry refuse.

"""Source-proven induction arithmetic and actual Malbolge control effects."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
import unittest
from pathlib import Path
from typing import cast, override

from tests import test_guest_byte_total_if_c_pipeline as total
from tests import test_guest_byte_wide_stride_c_pipeline as previous

ROOT = previous.ROOT
COMPILE = previous.COMPILE
RUN = previous.RUN
NORMALIZED = previous.NORMALIZED
PROJECT = previous.PROJECT


def program(guard: str = "position / 12 == 1") -> str:
    """Break on a proven loop counter; keep byte I/O genuinely guest-side."""
    source = previous.program().replace("position % 2 == 0", guard)
    assert "            continue;" in source
    return source.replace("            continue;", "            break;")


class GuestByteInductionArithmeticCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(
            path.is_file()
            for path in (
                total.FRONTEND,
                total.ADAPTER,
                total.LAYOUT,
                total.VM,
            )
        ):
            self.skipTest("pinned Clang and normative guest VM required")

    def test_real_guest_break_depends_on_source_time_division(self) -> None:
        """Second-trip break yields exactly three resident bytes then a read."""
        samples = (
            *(bytes((value, value ^ 255)) for value in (0, 1, 127, 128, 255)),
            *(hashlib.shake_256(bytes((83, index))).digest(2) for index in range(8)),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "division-break.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(program())
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in samples:
                with self.subTest(data=data):
                    vm = RUN(guest, data)
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    self.assertEqual(vm.stdout, bytes((data[0],) * 3 + (data[1],)))
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:7\n")

    def test_multiplication_selected_break_matches_independent_oracle(self) -> None:
        """Same C break point reached through a distinct proven operation."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "multiply-break.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(program("position * 2 == 24"))
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in (b"\0\xff", b"\xff\0", b"\x80\x7f"):
                vm = RUN(guest, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, bytes((data[0],) * 3 + (data[1],)))
                self.assertEqual(vm.stderr, b"malbolge-steps-v1:7\n")

    def test_other_pure_arithmetic_forms_reach_layout(self) -> None:
        """All authentic operations select the C branch without runtime math."""
        cases = (
            "position + 12 == 24",
            "position - 12 == 0",
            "position % 12 == 0",
            "position / 12 != 1",
            "position * 2 >= 24",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, guard in enumerate(cases):
                with self.subTest(guard=guard):
                    source = Path(directory) / f"form-{index}.c"
                    guest = source.with_suffix(".malbolge")
                    _ = source.write_text(program(guard))
                    result = subprocess.run(
                        [
                            str(total.ADAPTER),
                            "--layout-backend",
                            sys.executable,
                            "--output",
                            str(guest),
                            "--source",
                            str(source),
                            "--capsule",
                        ],
                        input=json.dumps(NORMALIZED(source)).encode(),
                        capture_output=True,
                        check=False,
                        timeout=15,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(
                        b"layout backend exited unsuccessfully", result.stderr
                    )
                    self.assertFalse(guest.exists())

    def test_direct_counter_comparison_requires_original_source_tokens(self) -> None:
        """Same-width numeric and comparator edits cannot change a loop exit."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "direct.c"
            original = program("position == 12")
            _ = source.write_text(original)
            normalized = NORMALIZED(source)
            for label, mutated in (
                ("operator", original.replace("position == 12", "position != 12")),
                ("bound", original.replace("position == 12", "position == 13")),
            ):
                with self.subTest(label=label):
                    _ = source.write_text(mutated)
                    guest = Path(directory) / f"direct-forged-{label}.malbolge"
                    result = PROJECT(normalized, guest, source)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())

    def test_zero_division_overflow_and_forgery_refuse_publication(self) -> None:
        """Neither C UB nor modified original-source tokens can pass proof."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "original.c"
            for index, guard in enumerate(
                (
                    "position / 0 == 1",
                    "position % 0 == 0",
                    "position * 2147483647 == 1",
                    "getchar() / 12 == 1",
                )
            ):
                with self.subTest(guard=guard):
                    _ = source.write_text(program(guard))
                    guest = Path(directory) / f"invalid-{index}.malbolge"
                    result = COMPILE(source, guest)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())
            original = program()
            _ = source.write_text(original)
            normalized = NORMALIZED(source)
            for field in (
                "source-operator",
                "source-operand",
                "source-comparator",
                "source-constant",
                "ast-operator",
                "ast-operand",
                "ast-parent",
            ):
                with self.subTest(field=field):
                    forged = copy.deepcopy(normalized)
                    nodes = cast("list[dict[str, object]]", forged["nodes"])
                    division = next(
                        node
                        for node in nodes
                        if node.get("kind") == "binary-expression"
                        and node.get("operation") == "/"
                    )
                    if field == "source-operator":
                        _ = source.write_text(original.replace(" / 12", " % 12"))
                    elif field == "source-operand":
                        _ = source.write_text(original.replace(" / 12", " / 13"))
                    elif field == "source-comparator":
                        _ = source.write_text(original.replace(" == 1", " != 1"))
                    elif field == "source-constant":
                        _ = source.write_text(original.replace(" == 1", " == 2"))
                    elif field == "ast-operator":
                        division["operation"] = "%"
                    elif field == "ast-parent":
                        division["parent"] = 0
                    else:
                        operand = nodes[nodes.index(division) + 3]
                        operand["literal"] = "13"
                        operand["constant_integer"] = "13"
                    guest = Path(directory) / f"forged-{field}.malbolge"
                    result = PROJECT(forged, guest, source)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(guest.exists())
                    _ = source.write_text(original)


if __name__ == "__main__":
    _ = unittest.main()
