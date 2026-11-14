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
#   - Pure checked arithmetic proof of exact C integer live-byte guards.
# - Must-Not:
#   - Predict guest input, evaluate undefined C, or erase unequal effects.
# - Allows:
#   - Inputs: original source C, pinned Clang and independent binary streams.
#   - Outputs: normative VM parity or closed no-artifact rejection.
#   - Side effects: isolated temporary guest artifacts only.
# - Split-When:
#   - Runtime guest integer evaluation and dynamic branch lowering exist.
# - Merge-When:
#   - General C expression proof replaces the successful-byte enumeration.
# - Summary:
#   - Check pure integer guard arithmetic across every live guest byte.
# - Description:
#   - End-to-end induction/branch streams, UB and forgery refusal.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Effectful and unproven integer predicates fail closed.

"""Full binary C-to-Malbolge streams with source-proven arithmetic guards."""

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

from tests import test_guest_byte_equivalent_if_c_pipeline as equivalent
from tests import test_guest_byte_total_if_c_pipeline as total

ROOT = total.ROOT
ADAPTER = total.ADAPTER
COMPILE = total.COMPILE
RUN = total.RUN
NORMALIZED = total.NORMALIZED
PROJECT = total.PROJECT


class GuestByteArithmeticGuardCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(
            path.is_file()
            for path in (total.FRONTEND, total.ADAPTER, total.LAYOUT, total.VM)
        ):
            self.skipTest("pinned C frontend and normative guest VM required")

    def test_arithmetic_tautology_selects_real_guest_io(self) -> None:
        """The three-trip C loop keeps its runtime byte and I/O effects."""
        guard = "((current * 3 + 1) % 3) == 1"
        # Arithmetic proof covers all 256 values; independently replay a
        # bounded boundary/stratified/seeded VM sample.
        inputs = (
            *(bytes((value, value ^ 255)) for value in (0, 1, 2, 127, 128, 254, 255)),
            *(bytes((value, value ^ 255)) for value in range(0, 256, 16)),
            *(hashlib.shake_256(bytes((47, i))).digest(2) for i in range(12)),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "arithmetic-total.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(total.source(guard, bound=3))
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in inputs:
                with self.subTest(data=data):
                    vm = RUN(guest, data)
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    self.assertEqual(vm.stdout, bytes((data[0],) * 4 + (data[1],)))
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:8\n")

    def test_dependent_arithmetic_preserves_identical_effects(self) -> None:
        """No guest conditional may be fabricated for a dependent modulus."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "arithmetic-dependent.c"
            guest = source.with_suffix(".malbolge")
            _ = source.write_text(equivalent.source("(current + 7) % 5", bound=1))
            result = COMPILE(source, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for value in (0, 1, 4, 5, 127, 128, 254, 255):
                data = bytes((value, value ^ 255))
                vm = RUN(guest, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, bytes((value,) * 2 + (data[1],)))

    def test_arithmetic_undefined_or_unequal_effects_refuse(self) -> None:
        """Undefined arithmetic or unequal runtime effects must refuse."""
        invalid = (
            total.source("(current + 7) % 5", bound=1),
            total.source("(current * 2147483647) == 0", bound=1),
            total.source("(current / (current - current)) == 0", bound=1),
            total.source("(current % (current & 1)) == 0", bound=1),
            total.source("(current << 31) == 0", bound=1),
            total.source("(current >> -1) == 0", bound=1),
            equivalent.source("(current + getchar()) % 3", bound=1),
            equivalent.source("(current % 3) + putchar(9)", bound=1),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, program in enumerate(invalid):
                with self.subTest(index=index):
                    source = Path(directory) / f"invalid-{index}.c"
                    guest = source.with_suffix(".malbolge")
                    _ = source.write_text(program)
                    result = COMPILE(source, guest)
                    self.assertNotEqual(result.returncode, 0, program)
                    self.assertFalse(guest.exists(), program)

    def test_checked_arithmetic_forms_reach_guest_layout(self) -> None:
        """Prove both-sided arithmetic without spending VM search budgets."""
        guards = (
            "((current + 1) - current) == 1",
            "((current ^ 255) + current) == 255",
            "((current << 1) >> 1) == current",
            "(current / 2) <= 127",
            "((current + 7) % 5) < 5",
            "(current * 0) == 0",
            "(current - current) != 1",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, guard in enumerate(guards):
                with self.subTest(guard=guard):
                    source = Path(directory) / f"admitted-{index}.c"
                    guest = source.with_suffix(".malbolge")
                    _ = source.write_text(total.source(guard, bound=1))
                    result = subprocess.run(
                        [
                            str(ADAPTER),
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
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(
                        b"layout backend exited unsuccessfully", result.stderr
                    )
                    self.assertFalse(guest.exists())

    def test_formerly_unproven_integer_xor_now_reaches_layout(self) -> None:
        """Shifts and additions retain exact non-Boolean XOR semantics."""
        guards = (
            "current ^ (current >> 1)",
            "current ^ (current + 1)",
            "(current & 2) | (current >> 1)",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, guard in enumerate(guards):
                with self.subTest(guard=guard):
                    source = Path(directory) / f"xor-{index}.c"
                    guest = source.with_suffix(".malbolge")
                    _ = source.write_text(equivalent.source(guard, bound=1))
                    result = subprocess.run(
                        [
                            str(ADAPTER),
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
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(
                        b"layout backend exited unsuccessfully", result.stderr
                    )
                    self.assertFalse(guest.exists())

    def test_arithmetic_clang_spoofing_refuses(self) -> None:
        """Operators, parents, types and spans must match pinned Clang."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            source = Path(directory) / "authentic.c"
            _ = source.write_text(total.source("((current * 3 + 1) % 3) == 1", bound=1))
            normalized = NORMALIZED(source)
            for field in ("parent", "operation", "type", "span"):
                with self.subTest(field=field):
                    forged = copy.deepcopy(normalized)
                    nodes = cast("list[dict[str, object]]", forged["nodes"])
                    node = next(
                        item
                        for item in nodes
                        if item["kind"] == "binary-expression"
                        and item["operation"] == "%"
                    )
                    if field == "parent":
                        node[field] = 0
                    elif field == "operation":
                        node[field] = "+"
                    elif field == "type":
                        node[field] = "u32"
                    else:
                        span = cast("dict[str, dict[str, int]]", node[field])
                        span["begin"]["column"] += 1
                    guest = Path(directory) / f"forged-{field}.malbolge"
                    result = PROJECT(forged, guest, source)
                    self.assertNotEqual(result.returncode, 0, field)
                    self.assertFalse(guest.exists(), field)
