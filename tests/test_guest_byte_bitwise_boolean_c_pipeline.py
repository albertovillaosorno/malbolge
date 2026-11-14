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
#   - Source-proven bitwise Boolean C predicates over live guest bytes.
# - Must-Not:
#   - Treat arbitrary integer bits as Boolean or execute C effects on host.
# - Allows:
#   - Inputs: pinned C/Clang and bounded binary guest input.
#   - Outputs: normative VM parity or refusal without guest artifact.
#   - Side effects: isolated temporary guest artifacts only.
# - Split-When:
#   - General C arithmetic and guest control supersede this proof.
# - Merge-When:
#   - General pure C expression analysis provides equivalent evidence.
# - Summary:
#   - Distinguish 0/1 bitwise predicates from arbitrary integer masks.
# - Description:
#   - Exercise compound source C with counted loops and guest input.
# - Usage:
#   - Run with python3.14 -B -m unittest.
# - Defaults:
#   - Rejection on unproven operands, forged nodes or source mismatch.

"""Whole C/VM parity for bitwise combinations of Boolean byte guards."""

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

ROOT = equivalent.ROOT
COMPILE = equivalent.COMPILE
RUN = equivalent.RUN
NORMALIZED = equivalent.NORMALIZED
PROJECT = equivalent.PROJECT
FRONTEND = equivalent.FRONTEND
ADAPTER = equivalent.ADAPTER
LAYOUT = equivalent.LAYOUT
VM = equivalent.VM


class GuestByteBitwiseBooleanCPipelineTests(unittest.TestCase):
    @override
    def setUp(self) -> None:
        if not all(path.is_file() for path in (FRONTEND, ADAPTER, LAYOUT, VM)):
            self.skipTest("pinned compiler, layout and normative VM required")

    def _verify_guest_guards(self, guards: tuple[str, ...]) -> None:
        """Compile each whole C program and independently verify guest bytes."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, guard in enumerate(guards):
                source = root / f"boolean-{index}.c"
                guest = root / f"boolean-{index}.malbolge"
                _ = source.write_text(equivalent.source(guard), encoding="utf-8")
                compiled = COMPILE(source, guest)
                self.assertEqual(compiled.returncode, 0, (guard, compiled.stderr))
                boundaries = (bytes((0, 255)), bytes((1, 254)), bytes((2, 253)))
                seeded = (
                    hashlib.shake_256(bytes((33, value))).digest(2)
                    for value in range(3)
                )
                for data in (*boundaries, *seeded):
                    with self.subTest(guard=guard, data=data):
                        actual = RUN(guest, data)
                        self.assertEqual(actual.returncode, 0, actual.stderr)
                        self.assertEqual(
                            actual.stdout, bytes((data[0],) * 4 + (data[1],))
                        )
                        self.assertEqual(actual.stderr, b"malbolge-steps-v1:8\n")

    def test_xor_and_and_guards_run_in_actual_guest(self) -> None:
        """A live two-bit selector and Boolean conjunction preserve I/O."""
        self._verify_guest_guards(
            (
                "((current & 1) != 0) ^ ((current & 2) != 0)",
                "((current & 1) != 0) & ((current & 2) != 0)",
            )
        )

    def test_or_and_conditional_guards_run_in_actual_guest(self) -> None:
        """Boolean disjunction and ternary composition preserve guest I/O."""
        self._verify_guest_guards(
            (
                "((current & 1) != 0) | ((current & 2) != 0)",
                "(((current & 1) != 0) ^ ((current & 2) != 0)) ? 1 : 0",
            )
        )

    def test_bitwise_boolean_total_predicates_select_pure_arm(self) -> None:
        """XOR of a Boolean predicate with itself has no true input."""
        from tests import test_guest_byte_total_if_c_pipeline as total

        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            cases = (
                "((current & 1) != 0) ^ ((current & 1) != 0)",
                "((current & 3) != 0) | ((current & 3) == 0)",
            )
            for index, guard in enumerate(cases):
                source = root / f"total-{index}.c"
                guest = root / f"total-{index}.malbolge"
                _ = source.write_text(total.source(guard, reverse=(index == 0)))
                compiled = COMPILE(source, guest)
                self.assertEqual(compiled.returncode, 0, (guard, compiled.stderr))
                for data in (bytes((0, 255)), bytes((3, 0)), bytes((255, 4))):
                    actual = RUN(guest, data)
                    self.assertEqual(actual.returncode, 0, actual.stderr)
                    self.assertEqual(actual.stdout, bytes((data[0],) * 4 + (data[1],)))

    def test_impure_or_unproven_integer_xor_do_not_fold(self) -> None:
        """Effectful and unsupported integer operands cannot be erased."""
        invalid = (
            "current ^ (current >> 1)",
            "current ^ (current + 1)",
            "((current & 1) != 0) ^ getchar()",
            "((current & 1) != 0) ^ putchar(65)",
        )
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, guard in enumerate(invalid):
                source = root / f"invalid-{index}.c"
                guest = root / f"invalid-{index}.malbolge"
                _ = source.write_text(equivalent.source(guard))
                result = COMPILE(source, guest)
                self.assertNotEqual(result.returncode, 0, guard)
                self.assertFalse(guest.exists(), guard)

    def test_pure_integer_xor_is_no_longer_boolean_only(self) -> None:
        """Authenticate new integer guards without rerunning guest synthesis."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            for index, guard in enumerate(
                ("(current & 1) ^ (current & 2)", "current ^ current")
            ):
                program = root / f"integer-{index}.c"
                guest = program.with_suffix(".malbolge")
                _ = program.write_text(equivalent.source(guard), encoding="utf-8")
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
                self.assertEqual(result.returncode, 1, (guard, result.stderr))
                self.assertIn(b"layout backend exited unsuccessfully", result.stderr)
                self.assertFalse(guest.exists(), guard)

    def test_forged_boolean_operators_are_not_admitted(self) -> None:
        """Mutated AST edges never replace source-grounded C operators."""
        with tempfile.TemporaryDirectory(dir=ROOT / ".temp") as directory:
            root = Path(directory)
            source = root / "original.c"
            _ = source.write_text(
                equivalent.source("((current & 1) != 0) ^ ((current & 2) != 0)")
            )
            normalized = NORMALIZED(source)
            for field in ("parent", "operation", "type", "span"):
                forged = copy.deepcopy(normalized)
                nodes = cast("list[dict[str, object]]", forged["nodes"])
                node = next(
                    item
                    for item in nodes
                    if item["kind"] == "binary-expression" and item["operation"] == "^"
                )
                if field == "parent":
                    node[field] = 0
                elif field == "operation":
                    node[field] = "|"
                elif field == "type":
                    node[field] = "u32"
                else:
                    span = cast("dict[str, dict[str, int]]", node[field])
                    span["begin"]["column"] += 1
                guest = root / f"forged-{field}.malbolge"
                result = PROJECT(forged, guest, source)
                self.assertNotEqual(result.returncode, 0, field)
                self.assertFalse(guest.exists(), field)
