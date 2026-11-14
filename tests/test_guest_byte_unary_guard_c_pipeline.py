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
#   - Source-proven unary signed integer C guest-byte predicates.
# - Must-Not:
#   - Guess guest bytes, erase branch effects or evaluate signed overflow.
# - Allows:
#   - Inputs: pinned Clang and original source plus binary guest streams.
#   - Outputs: normative VM parity or refusal without guest publication.
#   - Side effects: isolated temporary guest artifacts only.
# - Split-When:
#   - General runtime C arithmetic and conditional lowering are available.
# - Merge-When:
#   - Source-proven C integer evaluator replaces finite guest-byte proof.
# - Summary:
#   - Prove pure unary integer arithmetic over every successful input byte.
# - Description:
#   - Whole counted C loops with negative-value guards and forgery refusal.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Effectful and overflowed unary expressions fail closed.

"""End-to-end source-C unary integer predicates and normative guest parity."""

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


class GuestByteUnaryGuardCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(
            path.is_file()
            for path in (total.FRONTEND, total.ADAPTER, total.LAYOUT, total.VM)
        ):
            self.skipTest("pinned C frontend and normative guest VM required")

    def test_original_negative_bitwise_guard_matches_guest(self) -> None:
        """Complete C induction and continue stream proves ~x ^ x == -1."""
        guard = "((~current) ^ current) == -1"
        boundary = (0, 1, 2, 127, 128, 254, 255)
        samples = (
            *(bytes((value, value ^ 255)) for value in boundary),
            *(bytes((value, value ^ 255)) for value in range(0, 256, 16)),
            *(hashlib.shake_256(bytes((139, i))).digest(2) for i in range(12)),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            program = Path(directory) / "negative-bitwise.c"
            guest = program.with_suffix(".malbolge")
            _ = program.write_text(total.source(guard, bound=3))
            result = COMPILE(program, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for data in samples:
                with self.subTest(data=data):
                    vm = RUN(guest, data)
                    self.assertEqual(vm.returncode, 0, vm.stderr)
                    expected = bytes((data[0],) * 4 + (data[1],))
                    self.assertEqual(vm.stdout, expected)
                    self.assertEqual(vm.stderr, b"malbolge-steps-v1:8\n")

    def test_negation_and_unary_plus_preserve_guest_effects(self) -> None:
        """C unary +, - and ~ compose on a real resident input byte."""
        guards = (
            "(-current + current) == 0",
            "(+current - current) == 0",
            "~(~current) == current",
            "(~current + current) == -1",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for i, guard in enumerate(guards):
                with self.subTest(guard=guard):
                    program = Path(directory) / f"signed-{i}.c"
                    guest = program.with_suffix(".malbolge")
                    _ = program.write_text(total.source(guard, bound=1))
                    result = COMPILE(program, guest)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    for value in (0, 1, 127, 128, 255):
                        data = bytes((value, value ^ 255))
                        vm = RUN(guest, data)
                        self.assertEqual(vm.returncode, 0, vm.stderr)
                        expected = bytes((value,) * 2 + (data[1],))
                        self.assertEqual(vm.stdout, expected)
                        self.assertEqual(vm.stderr, b"malbolge-steps-v1:6\n")

    def test_dependent_negative_guard_keeps_equivalent_effects(self) -> None:
        """A negative-valued guard may not choose an unequal arm."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            program = Path(directory) / "dependent-unary.c"
            guest = program.with_suffix(".malbolge")
            _ = program.write_text(equivalent.source("~current & 1", bound=1))
            result = COMPILE(program, guest)
            self.assertEqual(result.returncode, 0, result.stderr)
            for value in (0, 1, 2, 127, 128, 254, 255):
                data = bytes((value, value ^ 255))
                vm = RUN(guest, data)
                self.assertEqual(vm.returncode, 0, vm.stderr)
                self.assertEqual(vm.stdout, bytes((value,) * 2 + (data[1],)))
                self.assertEqual(vm.stderr, b"malbolge-steps-v1:6\n")

    def test_undefined_and_effectful_unary_guards_refuse(self) -> None:
        """Cannot fold signed overflow, I/O, mutation or unequal arms."""
        overflow = "-((current - current) - 2147483647 - 1) == 0"
        programs = (
            total.source("~current & 1", bound=1),
            total.source(overflow, bound=1),
            total.source("(~current >> 1) == 0", bound=1),
            total.source("++current == 1", bound=1),
            equivalent.source("~getchar() == current", bound=1),
            equivalent.source("-putchar(current) == 0", bound=1),
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, program_text in enumerate(programs):
                with self.subTest(index=index):
                    program = Path(directory) / f"invalid-{index}.c"
                    guest = program.with_suffix(".malbolge")
                    _ = program.write_text(program_text)
                    result = COMPILE(program, guest)
                    self.assertNotEqual(result.returncode, 0, program_text)
                    self.assertFalse(guest.exists(), program_text)

    def test_unary_guards_reach_layout_admission(self) -> None:
        """Nested unary predicates authenticate without a VM-search budget."""
        guards = (
            "-(-current) == current",
            "(+current + ~current) == -1",
            "!~current == 0",
            "-current <= 0",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            for index, guard in enumerate(guards):
                with self.subTest(guard=guard):
                    program = Path(directory) / f"admitted-{index}.c"
                    guest = program.with_suffix(".malbolge")
                    _ = program.write_text(total.source(guard, bound=1))
                    result = subprocess.run(
                        [
                            str(ADAPTER),
                            "--layout-backend",
                            sys.executable,
                            "--output",
                            str(guest),
                            "--source",
                            str(program),
                            "--capsule",
                        ],
                        input=json.dumps(NORMALIZED(program)).encode(),
                        capture_output=True,
                        check=False,
                        timeout=10,
                    )
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn(
                        b"layout backend exited unsuccessfully", result.stderr
                    )
                    self.assertFalse(guest.exists())

    def test_forged_unary_evidence_refuses(self) -> None:
        """No AST operator/type/span/parent can override original C bytes."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            program = Path(directory) / "authentic.c"
            _ = program.write_text(
                total.source("((~current) ^ current) == -1", bound=1)
            )
            normalized = NORMALIZED(program)
            fields = ("parent", "operation", "type", "span", "constant_integer")
            for field in fields:
                with self.subTest(field=field):
                    forged = copy.deepcopy(normalized)
                    nodes = cast("list[dict[str, object]]", forged["nodes"])
                    unary = "-" if field == "constant_integer" else "~"
                    kind = "unary-expression"
                    unaries = [n for n in nodes if n["kind"] == kind]
                    node = next(n for n in unaries if n["operation"] == unary)
                    if field == "parent":
                        node[field] = 0
                    elif field == "operation":
                        node[field] = "!"
                    elif field == "type":
                        node[field] = "u32"
                    elif field == "constant_integer":
                        node[field] = "0"
                    else:
                        span = cast("dict[str, dict[str, int]]", node[field])
                        span["begin"]["column"] += 1
                    guest = Path(directory) / f"forged-{field}.malbolge"
                    result = PROJECT(forged, guest, program)
                    self.assertNotEqual(result.returncode, 0, field)
                    self.assertFalse(guest.exists(), field)
